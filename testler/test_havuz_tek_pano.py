"""D-92 › Havuz evlerine uygulama (İE-40 PR-2): tek özel pano anahtarı havuz evinin İş Emri'sinde. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC: kart 14:05:21 "Okuma 2: duvar boyunca"; 14:27:09 "Montaj köşesinden uzak uçta"; 14:55:45 "A: Yerinde kalsın";
19:39:46 kısa parça kartı "Kısa parça silinsin" (her ev ayrıca gösterilir; silinen hâl bu dosyanın konusu değil). Kısa parça bırakmayan iki ev
(95 m² 3+1 PA-10, 77 m² 2+1 PA-24) anahtarla kaydoldu; öteki havuz şablonlarına anahtar yazılmadı.

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
# kod → (proje, kör ölçümün İş Emri'si, anahtarlı kaynak, pano önce → sonra)
EVLER = {
    "PA10": ("AP-04", "testler/kor/projeler/AP04/is_emri.json", "testler/havuz/is_emirleri/AP04_D92.json", (50, 48)),
    "PA24": ("AP-27", "testler/kor/projeler/AP27/is_emri.json", "testler/havuz/is_emirleri/AP27_D92.json", (52, 52)),
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
    _, kor, kaynak, _ = EVLER[kod]
    ie = _ie(kaynak)
    assert ie["yapi"]["dizilim"]["tek_ozel_pano"] == "dizilim_sonu"
    assert _anahtarsiz(ie) == _ie(kor)


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_kayit_ve_sablon(kod):
    """Kayıt D-92 ile ve anahtarlı kaynaktan; şablonda anahtar; Motor'un değişikliği eskiz tablosuyla aynı (kart seçiminin gördüğü)."""
    proje, _, kaynak, (once, sonra) = EVLER[kod]
    a = KAYIT[kod]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"], a["kaynak"]["kart_kiyasi"]["kart"]) == (kaynak, "D-92", proje)
    assert f"| {kod[:2]}-{kod[2:]} | {proje} | `{kaynak}` |" in D92
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    assert sab["yapi"]["dizilim"]["tek_ozel_pano"] == "dizilim_sonu"
    p1, p0 = G.kur(sab), G.kur(_anahtarsiz(sab))
    assert p1.tek_ozel_pano == TABLO["evler"][kod]["degisiklik"]
    assert (len(p0.panolar), len(p1.panolar)) == (once, sonra) and a["ozet"]["pano"] == sonra
    assert (p0.W, p0.H) == (p1.W, p1.H) and a["ozet"]["dis_olcu_cm"] == [p1.W, p1.H]
    assert HH.denetle(sab, HH.kartlar()[proje])[0] == []                          # proje kartı hakemi normal kipte geçer


def test_anahtar_yalniz_iki_evde():
    """Kısa parça bırakan yedi ev (silme kartı 19:39:46; ev ev gösterilecek), 49 m² (D-30), paftalı 60 m² (PK-01) ve mühürlü iki ev anahtarsız.
    Anahtar yalnız bu dosyanın evlerinde; yeni ev eklenirse bilinçli olarak buraya yazılır."""
    anahtarli = set()
    for f in sorted(glob.glob(str(SABLON_DIR / "adaylar" / "*.json"))):
        ie = json.loads(Path(f).read_text(encoding="utf-8"))
        if ((ie.get("yapi") or {}).get("dizilim") or {}).get("tek_ozel_pano"):
            anahtarli.add(Path(f).stem)
    assert anahtarli == set(EVLER)
    for kod in ("PA08", "PA21", "PA26", "PA12", "PA14", "PA15", "PA27", "PA23", "PA18", "PA03", "PA22"):
        assert kod in TABLO["evler"] and kod not in anahtarli


def test_karar_dosyasi_bekleyenleri_yazar():
    assert "19:39:46 UTC, Lokman kartta seçti: **\"Kısa parça silinsin\"**" in D92
    for metin in ("PA-08 (140 m²", "PA-21 (80 m²", "PA-26 (71 m²", "PA-12 (85 m²", "PA-14 (60 m²", "PA-15 (70 m²", "PA-27 (45 m²",
                  "PA-23 (49 m²", "PA-18 (60 m² paftalı", "Mühürlü PA-03 (M-07) ve PA-22 (M-12): yazılmaz"):
        assert metin in D92, metin
