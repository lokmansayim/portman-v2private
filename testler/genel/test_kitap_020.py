"""İE-16 PR-3c · kural kitabı 0.20-taslak (`kurallar/liste/kurallar.json`): Lokman'ın 27 Ekim 2026 cevapları listede.

Duvar izolasyonu (mineral yün) yeniden listede, yalıtılan duvarı olmayan işte satır yok (C1.1); çatı şiltesi İzocam 80 mm rulosu, 9,00 m²
(C1.6); ters mahya kenar kutusunun listedeki adı 'Metal tahta' (C1.9); 2026 listelerinin adları ve renk adın başında (C3). Adet ve iç ad
(`kalem`) değişmez. Altın pim 0.19: eski set eski listeyi verir (aynı tanım iki setle).
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, excel_liste, girdi_genel, yapi, yukleme  # noqa: E402

PROJELER = KOK / "testler" / "celik" / "projeler"
K20 = json.loads((KOK / "kurallar" / "liste" / "kurallar.json").read_text(encoding="utf-8"))
K19 = json.loads((KOK / "kurallar" / "liste" / "setler" / "0.19.json").read_text(encoding="utf-8"))
ADLAR = {"Ters mahya kenar kutusu": "Metal tahta", "Tekli anahtar": "Tekli anahtar takım", "Çiftli anahtar": "Çiftli anahtar takım",
         "Tekli priz": "Tekli priz takım", "Çiftli priz": "Çiftli priz takım", "Uydu prizi": "Uydu prizi takım",
         "NYM kablo (3 × 2,5)": "NYM kablo 3 × 2,5", "NYM kablo (2 × 1,5)": "NYM kablo 2 × 1,5",
         "W otomat (sigorta)": "W otomat sigorta 16 A", "Kaçak akım rölesi": "Kaçak akım rölesi ikili"}


def _liste(tanim: Path, kur: dict, renk: dict | None = None) -> tuple[dict, dict]:
    t = json.loads(tanim.read_text(encoding="utf-8"))
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    g = girdi_genel.girdi(y, c, girdi_genel.metraj(y, c, kur), kur, "test")
    if renk is not None:
        g["renk"] = renk
    return g, yukleme.hesapla(g, kur)


@pytest.fixture(scope="module")
def cp06():
    return {s: _liste(PROJELER / "CP06" / "CP06_kural.json", k) for s, k in (("0.19", K19), ("0.20", K20))}


def _satir(L: dict, kalem: str) -> dict | None:
    return next((s for s in L["satirlar"] if s["kalem"] == kalem), None)


def test_duvar_izolasyonu_listede(cp06):
    """C1.1: mineral yün gönderilir (7 Ekim kararının yerine); hesap aynı (dış duvar × kat + iç duvar − boşluk, ÷ 8,64). Yalıtılan duvarı
    olmayan iş (ÇP-03: liste yalnız çelik karkas) satır yazmaz (`bos_yazilmaz`); 0.19'da satır yok."""
    assert K20["duvar_izolasyonu"]["deger"] == {"listede": True, "bos_yazilmaz": True}
    s = _satir(cp06["0.20"][1], "Duvar izolasyonu")
    assert s and s["boyut"] == "paket 8,64 m²" and s["adet"] == math.ceil(s["olcu"] / 8.64 - 1e-9) and s["adet"] > 0
    assert _satir(cp06["0.19"][1], "Duvar izolasyonu") is None
    g, L = _liste(PROJELER / "CP03" / "CP03.json", K20)
    assert g["yalitim"]["dis_brut_m2"] == 0 and _satir(L, "Duvar izolasyonu") is None


def test_cati_siltesi_izocam_80(cp06):
    """C1.6: İzocam Çatı Şiltesi 80 mm, 120 × 750 cm = 9,00 m²; 0.19'da 9,6. Adet = alan ÷ paket, yukarı."""
    yeni, eski = _satir(cp06["0.20"][1], "Çatı şiltesi 80 mm"), _satir(cp06["0.19"][1], "Çatı şiltesi 80 mm")
    assert (yeni["boyut"], eski["boyut"]) == ("9,0 m²/adet", "9,6 m²/adet")
    assert yeni["formul"].endswith("÷ 9,0") and eski["formul"].endswith("÷ 9,6")
    assert yeni["adet"] == math.ceil(yeni["olcu"] / 9.0 - 1e-9) and eski["adet"] == math.ceil(eski["olcu"] / 9.6 - 1e-9)


def test_liste_adlari_2026(cp06):
    """C1.9 ve C3: listede yazılan ad (`liste_adi`) 2026 listelerindeki gibi; iç ad ve adet aynı. 0.19'da bu satırlarda yazılan ad yok."""
    L20, L19 = cp06["0.20"][1], cp06["0.19"][1]
    for kalem, ad in ADLAR.items():
        s20, s19 = _satir(L20, kalem), _satir(L19, kalem)
        assert s20 and s20["liste_adi"] == ad and s20["adet"] == s19["adet"], kalem
        assert "liste_adi" not in s19, kalem


def test_renk_adin_basinda(cp06, tmp_path):
    """C3: renk adın başında ('Antrasit gri metal dere'), parantezde yinelenmez (Markdown ve Excel). 0.19'da adın sonunda parantezle."""
    openpyxl = pytest.importorskip("openpyxl")
    L20, L19 = cp06["0.20"][1], cp06["0.19"][1]
    renkli = [s for s in L20["satirlar"] if s.get("renk")]
    assert renkli and all(s["renk_adda"] and s["liste_adi"].startswith("Antrasit gri ") for s in renkli)
    assert _satir(L20, "Metal dere")["liste_adi"] == "Antrasit gri metal dere"
    assert not any(s.get("renk_adda") for s in L19["satirlar"])
    md20, md19 = yukleme.md_yaz(L20, "CP06"), yukleme.md_yaz(L19, "CP06")
    assert "| Antrasit gri metal dere |" in md20 and "(antrasit gri)" not in md20
    assert "| Metal dere (antrasit gri) |" in md19
    ws = openpyxl.load_workbook(excel_liste.xlsx_yaz(L20, tmp_path / "CP06.xlsx"))["YÜKLEME"]
    hucre = [str(c.value) for c in ws["B"] if c.value]
    assert "Antrasit gri metal dere" in hucre and not any("(antrasit gri)" in h for h in hucre)


def test_renk_basta_turkce_harf_ve_kisaltma():
    """Renk adın başına gelirken Türkçe harf doğru küçülür ve büyür (ı → I, İ → i); kısaltmayla başlayan ad (OUTWEAR) küçülmez."""
    k = json.loads(json.dumps(K20))
    k["renkli_kalemler"]["deger"]["cati"] += ["İniş kelepçesi", "Dış cephe Boardex"]
    _, L = _liste(PROJELER / "CP06" / "CP06_kural.json", k, renk={"cati": "ıhlamur yeşili", "sacak_alin": "ıhlamur yeşili"})
    assert _satir(L, "İniş kelepçesi")["liste_adi"] == "Ihlamur yeşili iniş kelepçesi"
    assert _satir(L, "Dış cephe Boardex")["liste_adi"] == "Ihlamur yeşili OUTWEAR Dış Cephe Levhası"
