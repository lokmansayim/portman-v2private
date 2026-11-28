"""BK-92 (D-169) · Kılavuzdaki Portman mesajlarını main'deki karar koduyla üretir (D-28).

Üç örnek sohbet `beyin.karar.karar_ver` ile yürür (LLM yok, Postgres yok, WhatsApp yok): bayinin sözü elle kurulmuş `Talep`tir, düğmeler
`kanal/etkilesim.coz` ile çözülür (worker'daki gibi; `testler/test_celik_revizyon_karar.py` › Sohbet ile aynı yol). Katalog canlının kabul
kümesiyle kurulur. Çizimden plan bölümü `beyin.gorsel_okuma`'nın teyit metniyle ve worker'ın teyit düğmeleri ve standart form metniyle
yürür. Dönen: {anahtar: {"metin", "butonlar": [{"id", "baslik"}], "pdf"}}; `gorseller=<klasör>` verilirse resimler de çizilir.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

DEPO = Path(__file__).resolve().parents[2]
for _y in (DEPO, DEPO / "kanal"):
    if str(_y) not in sys.path:
        sys.path.insert(0, str(_y))

from beyin import gorsel_okuma as GO, karar as K, katalog as KT  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402
from kanal import etkilesim as ET  # noqa: E402

BAYI = {"kod": "B01", "ad": "Örnek Bayi", "rol": "bayi", "numara": "900000000101"}       # gerçek olmayan numara (kuru koşu kartı gibi)
KABUL = {"PA01", "PA02", "PA03", "PA04", "PA05", "PA06", "PA07", "PA08", "PA06K", "PA06C",
         "KT01", "KT02", "KT03", "KT04", "Ç8201", "Ç8801", "Ç8801K", "Ç8801L"}          # canlının kabul kümesi (K-A10, 12 Kasım 2026)
OKUMA = DEPO / "testler" / "gorsel" / "veri" / "TK01_okuma.json"                        # bölüm 3: örnek çizimin kayıtlı okuması
CIZIM = Path(__file__).with_name("girdi") / "ornek_cizim.jpeg"                         # aynı çizimin resmi (bayinin göndereceği gibi)


class KilavuzHatasi(RuntimeError):
    """Sohbet kılavuzun beklediği yoldan gitmedi: kod değişmiş, kılavuz metni yeniden bakılmalı."""


class _Sohbet:
    def __init__(self, kok: Path):
        self.k = Konusma(BAYI["numara"], kok=kok)
        self.kat = Katalog(kabul_edilmis=KABUL)

    def yaz(self, metin: str, **alan):
        alan.setdefault("niyet", "revizyon" if self.k.d.get("son_is_emri") else "yeni_talep")
        return K.karar_ver(Talep(guven="yuksek", ozet=alan.pop("ozet", metin[:80]), **alan), self.k, BAYI, self.kat, metin)

    def dugme(self, kimlik: str):
        etk = ET.coz({"reply_id": kimlik, "type": "interactive"}, self.k.d)
        if not etk.get("gecerli"):
            raise KilavuzHatasi(f"düğme çözülmedi: {kimlik}: {etk}")
        return K.karar_ver(Talep.model_validate(etk["talep"]), self.k, BAYI, self.kat, etk["metin"])

    @property
    def plan(self) -> dict:
        return self.k.d.get("son_is_emri") or {}

    @property
    def set_id(self) -> str:
        return str((self.k.d.get("secenek_seti") or {}).get("id"))


def _kayit(k, eylem: str | None = None, pdf: dict | None = None) -> dict:
    if eylem and k.eylem != eylem:
        raise KilavuzHatasi(f"{eylem} beklenirdi, karar {k.eylem}: {k.gerekce} · {k.mesaj[:200]}")
    d = {"metin": k.mesaj, "butonlar": [{"id": b["id"], "baslik": b["baslik"]} for b in (k.butonlar or [])]}
    if pdf:
        d["pdf"] = f"Portman_{pdf['is_emri_no']}_r{int(pdf['revizyon']):02d}.pdf"      # motor/dxf_out.uret'in dosya adı
    return d


def _plan_butonlari(ie: dict) -> list[dict]:
    """worker: çizim geçince plan mesajının düğmeleri (Onayla, Revize et)."""
    no, rev = ie["is_emri_no"], ie["revizyon"]
    return [{"id": f"o:{no}:{rev}", "baslik": "Onayla"}, {"id": f"r:{no}:{rev}", "baslik": "Revize et"}]


def _set_gorseli(s: _Sohbet, yol: Path, baslik: str, cati: bool = False) -> None:
    from motor import bayi_gorseli as BG
    ad = (s.k.d.get("secenek_seti") or {}).get("adaylar") or []
    BG.bilesik_gorsel([dict(a, gorsel_yolu=KT.SABLON_DIR / a["gorsel"], **({"cati_karti": True} if cati else {})) for a in ad[:3]],
                      yol, baslik=baslik)


def uret(gorseller: Path | None = None) -> dict:
    from motor import bayi_gorseli as BG
    m: dict[str, dict] = {}
    g = (lambda ad: Path(gorseller) / ad) if gorseller else None
    with tempfile.TemporaryDirectory(prefix="kilavuz_") as d:
        # Bölüm 1: talep → öncelik → seçenek seti → plan → "tamam" → Onayla → çatı
        s = _Sohbet(Path(d) / "b1")
        talep = "Tek kat prefabrik, 2+1, 85 m²"
        m["b1.talep"] = _kayit(s.yaz(talep, yapi_turu="prefabrik", oda_programi="2+1", alan_m2=85), "sor")
        m["b1.set"] = _kayit(s.dugme("q:oncelik:yasam"), "secenek")
        if g:
            _set_gorseli(s, g("set.png"), talep)
        k = s.dugme(f"s:{s.set_id}:PA06")
        m["b1.plan"] = {**_kayit(k, "is_emri", s.plan), "butonlar": _plan_butonlari(s.plan)}
        if g:
            BG.plan_gorseli(s.plan, g("plan.png"))
        m["b1.tamam"] = _kayit(s.yaz("tamam", niyet="onay"))
        k = s.dugme(f"o:{s.plan['is_emri_no']}:{s.plan['revizyon']}")
        m["b1.onayla"] = _kayit(k, "secenek")
        if g:
            _set_gorseli(s, g("cati.png"), "Çatı seçin: plan aynı, fark çatıda", cati=True)
        m["b1.cati"] = _kayit(s.dugme(f"s:{s.set_id}:PA06"))

        # Bölüm 2: kod → Revize et → pencere → hangi pencere → r02 → otomatik yapılamayan istek → teşekkür → onay
        s = _Sohbet(Path(d) / "b2")
        m["b2.kod"] = {**_kayit(s.yaz("PA-06", katalog_kodu="PA06", yapi_turu="prefabrik"), "is_emri", s.plan), "butonlar": _plan_butonlari(s.plan)}
        m["b2.revize"] = _kayit(s.dugme(f"r:{s.plan['is_emri_no']}:{s.plan['revizyon']}"))
        k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[{"mahal": "mutfak", "islem": "degistir", "olcu": "120x120"}])
        m["b2.pencere"] = _kayit(k)
        if not m["b2.pencere"]["butonlar"]:
            raise KilavuzHatasi("mutfakta iki pencere sorusu beklenirdi")
        k = s.dugme(m["b2.pencere"]["butonlar"][0]["id"])
        m["b2.r02"] = {**_kayit(k, "is_emri", s.plan), "butonlar": _plan_butonlari(s.plan)}
        if g:
            BG.plan_gorseli(s.plan, g("r02.png"))
        m["b2.veranda"] = _kayit(s.yaz("verandayı kaldır", varyantlar=[{"tur": "veranda_kaldir", "aciklama": "verandayı kaldır", "parametreler": {}}]))
        m["b2.tesekkur"] = _kayit(s.yaz("teşekkürler", niyet="diger"))
        m["b2.onay"] = _kayit(s.yaz("onaylıyorum", niyet="onay"), "secenek")

        # Bölüm 3: çizimin okuması (teyit) → standart formu → "Doğru" → plan
        import worker as W
        o = json.loads(OKUMA.read_text(encoding="utf-8"))
        den = GO.denetle(o)
        metin, _ = GO.teyit_metni(o, den, gorsel_var=True)
        m["b3.okuma"] = {"metin": metin, "butonlar": [{"id": "c:ornek:d", "baslik": "Doğru"}, {"id": "c:ornek:z", "baslik": "Düzelt"}]}
        m["b3.form"] = {"metin": W.STANDART_FORM_METNI, "butonlar": [{"id": "form", "baslik": "Standartlar"}]}
        if g:
            GO.yerlesim_gorseli(o, den, g("yerlesim.png"))
        s = _Sohbet(Path(d) / "b3")
        kan = den["kanonik"]
        ts = {"ozet": f"Çiziminizdeki plan ({GO._m(kan['W'])} × {GO._m(kan['H'])} m, {o.get('oda_programi') or '3+1'}).", "varyantlar": [],
              "pencereler": [], "oda_programi": "3+1", "yapi_turu": den["yapi_turu"]}
        s.k.d["taslak"] = {"ozet": ts["ozet"], "oda_programi": "3+1", "yapi_turu": den["yapi_turu"]}
        k = K._is_emri_uret(s.k, BAYI, s.kat, den["cevrim"]["is_emri"], GO.KAYNAK, ts, on_bilgi="")
        m["b3.plan"] = {**_kayit(k, "is_emri", k.is_emri), "butonlar": _plan_butonlari(k.is_emri)}
        if g:
            BG.plan_gorseli(k.is_emri, g("plan3.png"))
    return m
