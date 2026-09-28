"""T10 · İE-02 kabul gösterimi (Astra, 28.09): talep kaydedilir → netleştirme sorusu → servis yeniden başlatılır → cevap doğru
soruya ve projeye bağlanır → doğru revizyondan devam edilir → çıktı gönderilir → aynı mesaj yeniden gelir, ikinci iş oluşmaz.

SİMÜLASYONDUR. Gerçek Postgres 16, gerçek işleyici süreçleri (kanal/kalici.py), gerçek Beyin kuralları ve gerçek Motor
kullanılır. Gelen WhatsApp mesajı webhook biçiminde elle üretilir; gönderim sahte bir WhatsApp göndericisiyle yapılır;
LLM çıkarımı kayıtlıdır (manuel arka uç). Gerçek WhatsApp, gerçek LLM ve hosting PHP tarafı denenmedi.

  PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python testler/kalici/kabul_gosterimi.py [--rapor DOSYA.md]
Çıkış kodu 0: bütün denetimler geçti. Süre ~1 dk (Motor iki plan çizer).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
KANAL_VERI = Path(tempfile.mkdtemp(prefix="pm_kabul_"))
os.environ["PORTMAN_KANAL_DIR"] = str(KANAL_VERI)
for p in (KOK, KOK / "kanal"):
    sys.path.insert(0, str(p))

import psycopg  # noqa: E402

ADMIN = os.environ.get("PORTMAN_TEST_PG", "")
AYAR = {"llm": {"backend": "manuel"}, "patron_teknik_not": False}
BAYI = {"kod": "TSTA", "ad": "Deneme Bayi A", "rol": "bayi"}
NUMARA = "900000000101"                       # gerçek olmayan deneme numarası


def maske(n: str) -> str:
    return n[:3] + "…" + n[-2:]


def webhook_mesaji(metin: str, cikarim: dict, ts: float | None = None) -> dict:
    """feature.php::pm_kanal_capture'ın kuyruğa yazdığı satırın aynısı (imza doğrulaması ve Meta yok)."""
    return {"id": f"wamid.KABUL{uuid.uuid4().hex[:10].upper()}", "sender": NUMARA, "name": "", "role": "bayi", "bayi": BAYI,
            "type": "text", "text": metin, "media_id": None, "filename": None, "timestamp": int(ts or time.time()),
            "received_at": int(time.time()), "phone_number_id": "106000000000001", "source": "Meta imzalı webhook",
            "mode": "patron", "state": "queued", "attempts": 0, "result": None, "error": None, "updated_at": int(time.time()),
            "test_cikarim": cikarim}


def geri_al(depo, numara: str, saat: float) -> None:
    """Zamanın geçmesini taklit eder: konuşmadaki zamanlar geriye çekilir (testler/kalici/conftest.py::geri_al ile aynı)."""
    from psycopg.types.json import Jsonb
    sn = int(saat * 3600)
    with depo.baglan() as c, c.transaction():
        d = c.execute("SELECT durum FROM konusmalar WHERE gonderen = %s FOR UPDATE", (numara,)).fetchone()["durum"]
        for a in ("guncellendi", "taslak_zamani", "bekleyen_zamani"):
            if d.get(a):
                d[a] -= sn
        for g in d.get("gecmis") or []:
            g["t"] -= sn
        c.execute("UPDATE konusmalar SET durum = %s, surum = surum + 1 WHERE gonderen = %s", (Jsonb(d), numara))


_SABLON = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))


def _konum(ie: dict, ad: str):
    m = next((x for x in ie.get("mahaller", []) if x["ad"] == ad), None)
    return [list(map(float, r)) for r in (m or {}).get("konum_pano") or []]


def _aynali(ie) -> bool:
    return bool(ie) and _konum(ie, "YATAK ODASI 1") != _konum(_SABLON, "YATAK ODASI 1")


def _pencere_var(ie, mahal: str, olcu: str) -> bool:
    return bool(ie) and any(a["tur"] == "pencere" and a.get("mahal") == mahal and a.get("olcu") == olcu for a in ie["acikliklar"])


class SahteWhatsApp:
    def __init__(self):
        self.gonderilen = []

    def __call__(self, satir):
        self.gonderilen.append(satir)
        return f"wamid.GIDEN{len(self.gonderilen):03d}"


class Gosterim:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.satirlar: list[str] = []
        self.denetim: list[tuple[bool, str]] = []
        self.surec = None
        self.ayar = KANAL_VERI / "ayar.json"
        self.ayar.write_text(json.dumps(AYAR), encoding="utf-8")

    def yaz(self, s: str = ""):
        print(s, flush=True); self.satirlar.append(s)

    def denetle(self, kosul: bool, ne: str):
        self.denetim.append((bool(kosul), ne)); self.yaz(("  ✓ " if kosul else "  ✗ ") + ne)

    def q(self, sql, *a):
        with psycopg.connect(self.dsn, row_factory=psycopg.rows.dict_row) as c:
            return c.execute(sql, a).fetchall()

    def isleyici_baslat(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "ANTHROPIC"))}
        env.update(PORTMAN_PG_DSN=self.dsn, PORTMAN_KANAL_DIR=str(KANAL_VERI))
        self.surec = subprocess.Popen([sys.executable, str(KOK / "kanal" / "kalici.py"), "isle", "--ayar", str(self.ayar), "--bos-bekle", "0.3"],
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.yaz(f"  işleyici süreci başladı (pid {self.surec.pid})")

    def isleyici_durdur(self):
        self.surec.send_signal(signal.SIGTERM); self.surec.wait(20)
        self.yaz(f"  işleyici süreci durduruldu (pid {self.surec.pid}, SIGTERM)")

    def is_bitene_dek(self, mesaj_id: str, sn: float = 180) -> dict:
        son = time.time() + sn
        while time.time() < son:
            r = self.q("SELECT * FROM isler WHERE mesaj_id = %s", mesaj_id)
            if r and r[0]["durum"] in ("bitti", "basarisiz"):
                return r[0]
            time.sleep(0.3)
        raise TimeoutError(mesaj_id)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapor")
    ns = ap.parse_args(argv)
    if not ADMIN:
        print("PORTMAN_TEST_PG tanımlı değil"); return 2
    from depo import Depo
    import kalici
    ad = "kabul_" + uuid.uuid4().hex[:8]
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        c.execute(f"CREATE DATABASE {ad}")
    dsn = f"{ADMIN} dbname={ad}"
    depo = Depo(dsn); depo.goc_uygula()
    G = Gosterim(dsn); wa = SahteWhatsApp()
    G.yaz("# İE-02 kabul gösterimi (simülasyon)")
    G.yaz(f"Tarih: {time.strftime('%Y-%m-%d %H:%M')} · Postgres: {G.q('SHOW server_version')[0]['server_version']} · veritabanı: {ad}")
    G.yaz("Gerçek: Postgres, işleyici süreçleri, Beyin kuralları, Motor. Simüle: WhatsApp gelen/giden, LLM çıkarımı (kayıtlı).")
    try:
        G.yaz("\n## 0. Başlangıç: bayinin açık bir projesi var (P6001 aynalı, r01 gönderildi)")
        G.isleyici_baslat()
        ilk = webhook_mesaji("P6001 aynalı olsun", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P6001 aynalı", "katalog_kodu": "P6001",
                                                    "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]})
        depo.mesaj_kaydet(ilk); G.is_bitene_dek(ilk["id"]); kalici.gonder(depo, wa)
        r01 = G.q("SELECT * FROM revizyonlar")[0]
        G.denetle(r01["rev"] == 1 and r01["dogrulandi"], f"r01 üretildi ve gönderildi: {r01['is_emri_no']} (proje {r01['proje_id']})")
        geri_al(depo, NUMARA, 3.5)
        G.yaz("  (3,5 saat geçmiş gibi: konuşmadaki zamanlar geriye alındı; D-01 eşiği 2 saat)")

        G.yaz("\n## 1. WhatsApp talebi geldi ve kaydedildi")
        talep_m = webhook_mesaji("P6001 yatak odası 1 penceresi 120x180 olsun",
                                 {"niyet": "revizyon", "guven": "yuksek", "ozet": "P6001 yatak odası 1 penceresi 120x180", "katalog_kodu": "P6001",
                                  "pencereler": [{"mahal": "Yatak Odası 1", "olcu": "120x180", "islem": "degistir"}]})
        yeni = depo.mesaj_kaydet(talep_m)
        m = G.q("SELECT id, gonderen, metin FROM mesajlar WHERE id = %s", talep_m["id"])[0]
        G.denetle(yeni and m["metin"] == talep_m["text"], f"mesaj {m['id'][:18]}… ({maske(m['gonderen'])}) kaydedildi, iş sırada")

        G.yaz("\n## 2. Portman netleştirme sorusu sordu")
        j1 = G.is_bitene_dek(talep_m["id"]); kalici.gonder(depo, wa)
        soru = G.q("SELECT * FROM sorular WHERE durum = 'acik'")
        G.denetle(j1["sonuc"]["eylem"] == "sor" and soru and soru[0]["alan"] == "yeni_mi_degisiklik",
                  f"soru: «{wa.gonderilen[-1]['govde'][:110]}…»")
        G.denetle(soru and soru[0]["kaynak_mesaj_id"] == talep_m["id"] and soru[0]["proje_id"] == r01["proje_id"]
                  and soru[0]["bekletilen_talep"]["pencereler"][0]["olcu"] == "120x180",
                  f"soru kaydı: kaynak mesaj bu talep, proje {soru[0]['proje_id'] if soru else '?'}, bekletilen talep saklı")

        G.yaz("\n## 3. Servis yeniden başlatıldı")
        G.isleyici_durdur()
        G.isleyici_baslat()

        G.yaz("\n## 4. Bayinin cevabı doğru soruya ve projeye bağlandı; doğru revizyondan devam edildi")
        cevap = webhook_mesaji("değişiklik", {"niyet": "diger", "guven": "orta", "ozet": "değişiklik"})
        depo.mesaj_kaydet(cevap)
        j2 = G.is_bitene_dek(cevap["id"])
        s = G.q("SELECT * FROM sorular WHERE id = %s", soru[0]["id"])[0]
        G.denetle((s["durum"], s["cevap_mesaj_id"]) == ("cevaplandi", cevap["id"]), "soru bu cevapla kapandı (cevaplandi)")
        r02 = G.q("SELECT * FROM revizyonlar WHERE kaynak_mesaj_id = %s", cevap["id"])
        G.denetle(j2["sonuc"]["eylem"] == "is_emri" and r02 and r02[0]["proje_id"] == r01["proje_id"] and r02[0]["rev"] == 2,
                  f"aynı projede r02: {r02[0]['is_emri_no'] if r02 else '?'}")
        G.denetle(r02 and _aynali(r02[0]["is_emri"]) and _pencere_var(r02[0]["is_emri"], "YATAK ODASI 1", "120x180"),
                  "r02 = r01 (aynalı) + bekletilen istek (yatak odası 1 penceresi 120x180)")
        G.denetle([x["durum"] for x in G.q("SELECT durum FROM revizyonlar ORDER BY rev")] == ["yerini_aldi", "onay_bekliyor"],
                  "r01 yerini r02'ye bıraktı; r02 onay bekliyor")

        G.yaz("\n## 5. Çıktı gönderildi")
        say = kalici.gonder(depo, wa)
        pdf = [x for x in wa.gonderilen if x["kind"] == "document"][-1]
        veri = Path(pdf["dosya"]).read_bytes()
        G.denetle(say["iletildi"] == 2 and veri[:5] == b"%PDF-" and hashlib.sha256(veri).hexdigest() == pdf["sha256"],
                  f"metin + PDF gönderildi: {Path(pdf['dosya']).name} ({len(veri)} B, sha256 {pdf['sha256'][:12]}…)")

        G.yaz("\n## 6. Aynı mesaj yeniden geldi: ikinci iş oluşmadı")
        n_is, n_giden = G.q("SELECT count(*) n FROM isler")[0]["n"], G.q("SELECT count(*) n FROM giden")[0]["n"]
        tekrar = depo.mesaj_kaydet(cevap)
        time.sleep(1.5)
        say2 = kalici.gonder(depo, wa)
        G.denetle(tekrar is False and G.q("SELECT count(*) n FROM isler")[0]["n"] == n_is
                  and G.q("SELECT count(*) n FROM giden")[0]["n"] == n_giden and say2["iletildi"] == 0,
                  f"iş sayısı {n_is}, giden satır {n_giden}: değişmedi; yeni gönderim yok")
        G.isleyici_durdur()
    finally:
        if G.surec and G.surec.poll() is None:
            G.surec.kill()
        with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")
    gecen = sum(k for k, _ in G.denetim)
    G.yaz(f"\nSONUÇ: {gecen}/{len(G.denetim)} denetim geçti. Gerçek WhatsApp ve gerçek LLM denenmedi; bu bir simülasyondur.")
    if ns.rapor:
        Path(ns.rapor).write_text("\n".join(G.satirlar) + "\n", encoding="utf-8")
    return 0 if gecen == len(G.denetim) else 1


if __name__ == "__main__":
    sys.exit(main())
