"""İE-02 kalıcı akış testleri için ortak düzen: gerçek Postgres, kayıtlı LLM çıkarımı (manuel arka uç), sahte WhatsApp.

Postgres adresi PORTMAN_TEST_PG ortam değişkeninden gelir (ör. "host=127.0.0.1 port=55432 user=postgres"); yoksa testler
atlanır. Her test kendi veritabanını, göçleri uygulanmış bir şablondan açar ve sonunda siler. Hiçbir test ağa, LLM'e,
WhatsApp'a ya da canlı sunucuya bağlanmaz.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
KANAL_VERI = Path(tempfile.mkdtemp(prefix="pm_kalici_"))
os.environ["PORTMAN_KANAL_DIR"] = str(KANAL_VERI)          # worker.KANAL: projects/ buraya yazılır
for p in (KOK, KOK / "kanal"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

psycopg = pytest.importorskip("psycopg")
ADMIN = os.environ.get("PORTMAN_TEST_PG", "")
SABLON = "portman_test_sablon"

AYAR = {"llm": {"backend": "manuel"}, "patron_teknik_not": False}
BAYI_A = {"kod": "TSTA", "ad": "Deneme Bayi A", "rol": "bayi"}
BAYI_B = {"kod": "TSTB", "ad": "Deneme Bayi B", "rol": "bayi"}
NUMARA_A = "900000000101"          # gerçek olmayan deneme numaraları
NUMARA_B = "900000000202"
_sayac = itertools.count(1)


def _admin():
    if not ADMIN:
        pytest.skip("PORTMAN_TEST_PG tanımlı değil (gerçek Postgres gerekli)")
    return psycopg.connect(ADMIN + " dbname=postgres", autocommit=True)


def dsn(ad: str) -> str:
    return f"{ADMIN} dbname={ad}"


@pytest.fixture(scope="session")
def sablon():
    from depo import Depo
    with _admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {SABLON} WITH (FORCE)")
        c.execute(f"CREATE DATABASE {SABLON}")
    Depo(dsn(SABLON)).goc_uygula()
    yield SABLON


@pytest.fixture
def depo(sablon):
    from depo import Depo
    ad = "t_" + uuid.uuid4().hex[:12]
    with _admin() as c:
        c.execute(f"CREATE DATABASE {ad} TEMPLATE {sablon}")
    d = Depo(dsn(ad))
    d.ad = ad
    yield d
    with _admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


def talep(niyet="yeni_talep", ozet="", **alanlar) -> dict:
    return {"niyet": niyet, "guven": "yuksek", "ozet": ozet, **alanlar}


def mesaj(metin: str, cikarim: dict, numara: str = NUMARA_A, bayi: dict | None = None, ts: float | None = None,
          mid: str | None = None, context_id: str | None = None, tur: str = "text") -> dict:
    """feature.php::pm_kanal_capture biçiminde kuyruk satırı; test_cikarim = kayıtlı LLM çıkarımı."""
    g = {"id": mid or f"wamid.TEST{next(_sayac):04d}{uuid.uuid4().hex[:6]}", "sender": numara, "name": "",
         "role": "bayi", "bayi": bayi if bayi is not None else BAYI_A, "type": tur, "text": metin, "media_id": None,
         "filename": None, "timestamp": int(ts if ts is not None else time.time()), "received_at": int(time.time()),
         "phone_number_id": "106000000000001", "source": "Meta imzalı webhook", "mode": "patron", "state": "queued",
         "attempts": 0, "result": None, "error": None, "updated_at": int(time.time()), "test_cikarim": cikarim}
    if context_id:
        g["context_id"] = context_id
    return g


class SahteWhatsApp:
    """Gönderici: her satır için bir giden kimliği döner. mod='belirsiz' → istek gitti ama cevap yok (zaman aşımı);
    mod='gonderilmedi' → dış çağrı yapılmadan vazgeçildi."""

    def __init__(self):
        self.gonderilen: list[dict] = []
        self.mod = "tamam"

    def __call__(self, satir: dict) -> str:
        from kalici import Gonderilmedi
        if self.mod == "gonderilmedi":
            raise Gonderilmedi("dosya doğrulanamadı")
        self.gonderilen.append({"id": satir["id"], "alici": satir["alici"], "kind": satir["kind"], "govde": satir["govde"],
                                "dosya": satir["dosya"]})
        if self.mod == "belirsiz":
            raise TimeoutError("WhatsApp cevap vermedi")
        return f"wamid.OUT{len(self.gonderilen):04d}"


@pytest.fixture(autouse=True)
def kanal_dizini(tmp_path, monkeypatch):
    """Her test kendi projects/ klasörünü kullanır (İş Emri numarası saniyeye bağlı: testler arası klasör çakışmasın)."""
    import worker
    d = tmp_path / "kanal"; d.mkdir()
    monkeypatch.setattr(worker, "KANAL", d)
    monkeypatch.setenv("PORTMAN_KANAL_DIR", str(d))
    return d


@pytest.fixture
def wa():
    return SahteWhatsApp()


def sahte_uret(ie: dict, hedef: Path, *a, **k) -> dict:
    """Hızlı Motor yerine geçer (testin konusu Motor değilse): küçük bir PDF ve doğrulama sonucu yazar."""
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    ad = f"Portman_{ie['is_emri_no']}_r{int(ie.get('revizyon', 1)):02d}"
    govde = json.dumps({"no": ie["is_emri_no"], "rev": ie.get("revizyon"), "ayna": ie.get("varyantlar")}, sort_keys=True).encode()
    (hedef / f"{ad}.pdf").write_bytes(b"%PDF-1.4\n% sahte Motor ciktisi\n" + govde)
    (hedef / f"{ad}.dxf").write_bytes(b"0\nEOF\n" + govde)
    (hedef / "validation.json").write_text('{"passed": true, "errors": []}', encoding="utf-8")
    return {"pdf": f"{ad}.pdf", "dxf": f"{ad}.dxf", "pdf_sha256": hashlib.sha256((hedef / f"{ad}.pdf").read_bytes()).hexdigest(),
            "dxf_sha256": hashlib.sha256((hedef / f"{ad}.dxf").read_bytes()).hexdigest(), "warnings": []}


@pytest.fixture
def hizli_motor(monkeypatch):
    from motor import dxf_out
    monkeypatch.setattr(dxf_out, "uret", sahte_uret)


def geri_al(depo, numara: str, saat: float) -> None:
    """Zamanın geçmesini taklit eder: konuşmadaki zamanlar geriye çekilir (test_b1_b2.py::_geri_al ile aynı alanlar)."""
    sn = int(saat * 3600)
    with depo.baglan() as c, c.transaction():
        r = c.execute("SELECT durum FROM konusmalar WHERE gonderen = %s FOR UPDATE", (numara,)).fetchone()
        d = r["durum"]
        for a in ("guncellendi", "taslak_zamani", "bekleyen_zamani"):
            if d.get(a):
                d[a] -= sn
        for g in d.get("gecmis") or []:
            g["t"] -= sn
        from psycopg.types.json import Jsonb
        c.execute("UPDATE konusmalar SET durum = %s, surum = surum + 1 WHERE gonderen = %s", (Jsonb(d), numara))


def sorgu(depo, sql: str, *arg):
    with depo.baglan() as c:
        return c.execute(sql, arg).fetchall()


def tek(depo, sql: str, *arg):
    r = sorgu(depo, sql, *arg)
    return r[0] if r else None


@pytest.fixture
def ajan(depo, tmp_path, monkeypatch):
    """vps/agent.py kalıcı modda, sahte hosting API'sine (sahte_hosting.py) bağlı. Gerçek PHP hattı değildir."""
    import sys
    import worker
    from sahte_hosting import SahteHosting
    sys.path.insert(0, str(KOK / "vps"))
    import agent as A
    tok = os.urandom(32).hex()
    h = SahteHosting(tmp_path / "hosting", tok)
    url = h.basla()
    for ad, deger in {"API": url, "TOKEN": tok, "DATA": worker.KANAL, "APP": KOK / "kanal", "LOGS": tmp_path / "logs",
                      "PKG": tmp_path / "pkg", "PG_DSN": depo.dsn}.items():
        monkeypatch.setattr(A, ad, deger)
    A._kalici.update(depo=None, K=None, son_esitleme=0.0, son_uyari=0.0, teslim_hata={})
    ayar = A.yerel_ayarlar(h.settings())
    yield A, h, ayar
    h.dur()
    A._kalici.update(depo=None, K=None, teslim_hata={})
