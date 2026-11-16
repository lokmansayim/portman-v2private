"""D-92 › Havuz evlerine uygulama (İE-40 PR-2): tek özel pano anahtarı havuz evinin İş Emri'sinde. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC: kart 14:05:21 "Okuma 2: duvar boyunca"; 14:27:09 "Montaj köşesinden uzak uçta"; 14:55:45 "A: Yerinde kalsın";
19:39:46 kısa parça kartı "Kısa parça silinsin" (her ev ayrıca gösterilir; silinen hâl bu dosyanın konusu değil). Kısa parça bırakmayan iki
evden 95 m² 3+1 (PA-10) ev kartıyla anahtarlı kaydoldu (20:32:51 "Doğru, havuzda yenilensin"); 77 m² 2+1 (PA-24) bugünkü gibi kaldı
(20:38:43 "Doğru, yanına eklensin": 773 × 1014 hâli ayrı numarayla). Öteki havuz şablonlarına anahtar yazılmadı. 15 Kasım 2026: D-103
(asıl proje kalır) üzerine 95 m²'nin asıl hâli PA-10'a döndü, anahtarlı hâl yeni numarayla PA-38 (kart 21:56:57 "Evet, yeni hâl yanına
girsin"; D-92 › 95 m²'nin asıl hâli).

Kaynak: kör ölçümün İş Emri'si değişmez; anahtarlı kopyası `testler/havuz/is_emirleri/<proje>_D92.json` (yalnız anahtar farklı).
"""
from __future__ import annotations

import copy
import glob
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin.katalog import SABLON_DIR, havuz_kayitlari  # noqa: E402
from motor import geometry as G  # noqa: E402

D92 = (KOK / "KARARLAR" / "D-92.md").read_text(encoding="utf-8")
TABLO = json.loads((KOK / "testler/motor/veri/D92_tek_ozel_pano_beklenen.json").read_text(encoding="utf-8"))
# kod → (proje, kör ölçümün İş Emri'si, anahtarlı kaynak, pano önce → sonra, asıl hâlin kodu (eskiz tablosunun anahtarı))
EVLER = {
    "PA38": ("AP-04", "testler/kor/projeler/AP04/is_emri.json", "testler/havuz/is_emirleri/AP04_D92.json", (50, 48), "PA10"),
}
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _anahtarsiz(ie: dict) -> dict:
    ie = copy.deepcopy(ie)
    ie["yapi"]["dizilim"].pop("tek_ozel_pano", None)
    return ie


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_kaynak_kor_is_emri_arti_anahtar(kod):
    """Anahtarlı kaynak kör ölçümün İş Emri'sinin aynısı; tek fark `yapi.dizilim.tek_ozel_pano: "dizilim_sonu"`."""
    _, kor, kaynak, _, _ = EVLER[kod]
    ie = _ie(kaynak)
    assert ie["yapi"]["dizilim"]["tek_ozel_pano"] == "dizilim_sonu"
    assert _anahtarsiz(ie) == _ie(kor)


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_kayit_ve_sablon(kod):
    """Kayıt D-92 ile ve anahtarlı kaynaktan; şablonda anahtar; Motor'un değişikliği eskiz tablosuyla aynı (kart seçiminin gördüğü)."""
    proje, _, kaynak, (once, sonra), asil = EVLER[kod]
    a = KAYIT[kod]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"], a["kaynak"]["kart_kiyasi"]["kart"]) == (kaynak, "D-92", proje)
    assert f"| {kod[:2]}-{kod[2:]} | {proje} | `{kaynak}` |" in D92
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    assert sab["yapi"]["dizilim"]["tek_ozel_pano"] == "dizilim_sonu"
    p1, p0 = G.kur(sab), G.kur(_anahtarsiz(sab))
    assert p1.tek_ozel_pano == TABLO["evler"][asil]["degisiklik"]
    assert (len(p0.panolar), len(p1.panolar)) == (once, sonra) and a["ozet"]["pano"] == sonra
    assert (p0.W, p0.H) == (p1.W, p1.H) and a["ozet"]["dis_olcu_cm"] == [p1.W, p1.H]
    assert HH.denetle(sab, HH.kartlar()[proje])[0] == []                          # proje kartı hakemi normal kipte geçer


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_asil_hal_aynen(kod):
    """D-103: asıl hâl kör ölçümün İş Emri'siyle, D-87 kararıyla ve anahtarsız havuzda; anahtarlı hâlle aynı ev (dış ölçü, oda, açıklık)."""
    proje, kor, _, (once, _), asil = EVLER[kod]
    a, b = KAYIT[asil], KAYIT[kod]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"], a["kaynak"]["kart_kiyasi"]["kart"]) == (kor, "D-87", proje)
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    assert "tek_ozel_pano" not in sab["yapi"]["dizilim"] and a["ozet"]["pano"] == once and len(G.kur(sab).panolar) == once
    yapi = lambda ie: {k: v for k, v in _anahtarsiz(ie)["yapi"].items() if k != "referans_model"}  # noqa: E731  (kayıt kodunu yazar)
    assert yapi(sab) == yapi(_ie(kor))
    ozet = lambda k: {x: v for x, v in k["ozet"].items() if x != "pano"}  # noqa: E731
    assert ozet(a) == ozet(b) and a["oda_programi"] == b["oda_programi"] and a["katalog_m2"] == b["katalog_m2"]
    assert HH.denetle(sab, HH.kartlar()[proje])[0] == []
    assert '21:56:57 UTC, Lokman kartta seçti: **"Evet, yeni hâl yanına girsin"**' in D92
    assert f"| {asil[:2]}-{asil[2:]} | {proje} | `{kor}` |" in D92


# Kısa parça silinmiş ya da büyümüş hâller (İE-40 PR-3, ev kartları "Doğru, yanına eklensin"): anahtarlı, yeni numarayla; kaynak evleri anahtarsız
SILINMIS = {"PA30": "PA12", "PA31": "PA14", "PA32": "PA15", "PA33": "PA08", "PA34": "PA24", "PA35": "PA26",
            "PA36": "PA18", "PA44": "PA23"}  # ayrıntı test_havuz_silme_kayit.py; PA-44: 49 m² tam panolu hâl (16 Kasım 06:58:39, D-30 gibi)
# Anahtarlı evin çatı seçenekleri (D-115, İE-44; Lokman kartı 16 Kasım 08:46:30 "9'u girsin, bekleyenler size gelsin"): plan evinkiyle
# aynı, yalnız `cati` değişir; şablon evin İş Emri'sini anahtarıyla taşır. Ayrıntı test_cati_secenekleri_toplu.py.
CATI_SECENEKLERI = {"PA31B": "PA31", "PA33C": "PA33", "PA34C": "PA34"}


def test_anahtar_yalniz_95m2_evde():
    """Kısa parça bırakan yedi ev (silme kartı 19:39:46; ev ev gösterilir), 77 m² (kart 20:38:43), 49 m² (D-30), paftalı 60 m² (PK-01) ve
    mühürlü iki ev anahtarsız. Anahtar yalnız bu dosyanın evlerinde ve kısa parçası silinmiş ya da büyümüş hâllerde (yeni numara; bugünkü ev
    aynen); anahtarlı evin çatı seçeneği evin anahtarını taşır (D-115);
    yeni ev eklenirse bilinçli olarak buraya yazılır."""
    anahtarli, anahtar = set(), {}
    for f in sorted(glob.glob(str(SABLON_DIR / "adaylar" / "*.json"))):
        ie = json.loads(Path(f).read_text(encoding="utf-8"))
        anahtar[Path(f).stem] = ((ie.get("yapi") or {}).get("dizilim") or {}).get("tek_ozel_pano")
        if anahtar[Path(f).stem]:
            anahtarli.add(Path(f).stem)
    assert anahtarli == set(EVLER) | set(SILINMIS) | set(CATI_SECENEKLERI)
    for secenek, ev in CATI_SECENEKLERI.items():
        kayit = json.loads((KOK / "beyin/veri/cati_varyantlari" / f"{ev}.json").read_text(encoding="utf-8"))
        assert ev in SILINMIS and anahtar[secenek] == anahtar[ev] and kayit["karar"] == "D-115"
        assert [v["sablon"] for v in kayit["varyantlar"] if v["kod"] == secenek] == [f"adaylar/{secenek}.json"]
    assert not set(SILINMIS.values()) & anahtarli and not {e[4] for e in EVLER.values()} & anahtarli
    for kod in ("PA08", "PA21", "PA26", "PA12", "PA14", "PA15", "PA27", "PA24", "PA23", "PA18", "PA03", "PA22"):
        assert kod in TABLO["evler"] and kod not in anahtarli


def test_karar_dosyasi_bekleyenleri_yazar():
    assert "19:39:46 UTC, Lokman kartta seçti: **\"Kısa parça silinsin\"**" in D92
    assert "20:32:51 UTC, Lokman kartta seçti: **\"Doğru, havuzda yenilensin\"**" in D92        # 95 m² ev kartı
    assert "20:38:43 UTC, Lokman kartta seçti: **\"Doğru, yanına eklensin\"**" in D92            # 77 m² bugünkü gibi
    assert "| PA-24 |" not in D92
    for metin in ("PA-08 (140 m²", "PA-21 (80 m²", "PA-26 (71 m²", "PA-12 (85 m²", "PA-14 (60 m²", "PA-15 (70 m²", "PA-27 (45 m²",
                  "PA-23 (49 m²", "PA-18 (60 m² paftalı", "Mühürlü PA-03 (M-07) ve PA-22 (M-12): yazılmaz"):
        assert metin in D92, metin
