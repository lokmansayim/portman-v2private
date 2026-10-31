"""BK-12 PR-2e · 100'lük duvar omegası (Lokman, 21 Ekim 16:22, E5 paftasıyla: "yeşil çizgi çizgi profili gördün mü? onun üzerine geliyor";
kartlar 22 Ekim: "Uygula", PK-01'in 0'ı "Stoktan", kirişsiz verandasız 60'lık evde 0 "Doğru").

Kural: ⌈(çatı kenarına gelmeyen dış duvarlar + çatı kenarında olmayan kirişler + 100'lük iç duvarlar) ÷ 2,5⌉. Paftadaki yeşil kesikli profil
kutu profil kiriştir; çatı kenarındaki duvar ve kiriş saçak ya da baş makas omegası alır.
- Motor kipi: çatı kenarına gelmeyen dış duvar = kapalı kısmın veranda ile ortak sınırı (PK-01 3,34 + 2,00 = 5,34 m → 3). Değer
  `ic_kalan_dis_duvar_m` olarak yazılır, pafta biçimine taşınınca aynı adet çıkar. İş Emri'ndeki duvarsız sınır (`acik_sinirlar`, ör.
  salon–mutfak) kiriştir (Lokman, kart 22 Ekim 05:26 "Evet, gelir"): aynı hattaki parçaları bir kiriş, `ic_kirisler_cm` olarak yazılır.
- Pafta kipi: verandalı girdide `ic_kalan_dis_duvar_m` okunmuş olmalı; `ic_kirisler_cm` kiriş satırı da yazar, yoksa formül uyarıyla başlar.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
OMEGA = "100'lük duvar omegası"
KIRIS = "Kutu profil (kiriş) 100 × 100"
UYARI = "UYARI: kenarda olmayan kiriş okunmadı (ic_kirisler_cm yok); paftada çatı kenarında olmayan yeşil kesikli profil varsa eksik. "
SIFIR = "çatı kenarına gelmeyen duvar ve kiriş yok (bütün dış duvarlar saçak ya da baş makas omegası alır)"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(VERI / "PK01.json"))


def _satir(L: dict, kalem: str) -> dict:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, len(s))
    return s[0]


def _pafta(N: dict, **d) -> dict:
    """Motor'un geometrisi `yapi_pafta` biçiminde (`test_pafta_kipi_motor_kipiyle_ayni` gibi)."""
    yp = {k: v for k, v in copy.deepcopy(N).items() if k not in ("kaynak", "veranda_kenarlari_cm", "sigorta_en_uzak")}
    yp["veranda_kirisleri_cm"] = [x - 10 for x in N["veranda_kenarlari_cm"]]
    yp.update(d)
    return yp


def _e5(**d) -> dict:
    """E5 biçiminde verandasız pafta girdisi: 7 × 7 m beşik, iç duvarsız; salonla mutfak arasındaki duvarsız açıklıkta yeşil kesikli profil."""
    return dict({"H0": 250.0, "W": 700.0, "D": 700.0, "t_dis": 10.0, "panolar": [], "ekler": [], "koseler": {"dis": 4}, "dikmeler": 0,
                 "veranda_kirisleri_cm": [], "kapali": [], "acik": [], "ozellikler": {}, "alici_ait": {},
                 "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 700.0, "boy_cm": 700.0, "egim_yuzde": 33.0, "sacak_cm": 30.0}]}, **d)


def test_motor_pk01(N, kurallar):
    """PK-01: verandaya bakan iki duvar 3,34 + 2,00 m (Motor'un veranda çokgeni 266–600 × 0–200; İş Emri'nde veranda 261–590, eni 3,29;
    5,29 ile 5,44 arası hep 3). Gerçek listedeki 0 stoktan düşme (Lokman, kart 22 Ekim "Stoktan"). Kiriş satırları yalnız açık kenarlardan."""
    assert N["ic_kalan_dis_duvar_m"] == 5.34
    L = PL.liste(copy.deepcopy(N), kurallar)
    s = _satir(L, OMEGA)
    assert (s["adet"], s["olcu"], s["formul"]) == (3, "100 × 2500", "çatı kenarına gelmeyen dış duvarlar 5,34 m ÷ 2,5")
    assert "PK-01" not in s["kaynak"] and "PK-03" not in s["kaynak"]
    assert sum(x["kalem"] == KIRIS for x in L["satirlar"]) == len(N["veranda_kenarlari_cm"])


def test_motor_duvarsiz_sinir_kiris(N, kurallar):
    """ALTIN 6×8'de salonla mutfak arası duvarsız, L biçimli (125,5 + 125,5 cm): iki kiriş satırı ve duvar omegası 3 → 4. TEST02'de hol–salon
    üç düz parça (5,02 m). PK-01'de duvarsız sınır yok. Pafta biçimine taşınınca aynı adet, uyarı yok. Kolonsuz köşe verandasının iki kirişi
    (D-35, 31 Ekim: L 3815 ve 2510) çatının kenarında: duvar omegasına girmez."""
    N6 = PL.model_motor(_oku(KOK / "is_emri" / "ALTIN_2plus1_6x8.json"))
    L = PL.liste(copy.deepcopy(N6), kurallar)
    s = _satir(L, OMEGA)
    assert N6["ic_kirisler_cm"] == [125.5, 125.5]
    assert (s["adet"], s["formul"]) == (4, "çatı kenarına gelmeyen dış duvarlar 6,33 m + çatı kenarında olmayan kirişler 2,51 m ÷ 2,5")
    ic = [x for x in L["satirlar"] if x["kalem"] == KIRIS and x["formul"].startswith("duvarsız sınırın boyu")]
    assert [(x["olcu"], x["adet"]) for x in ic] == [("L 1255", 1), ("L 1255", 1)]
    assert N6["kose_kirisleri_cm"] == [381.5, 251.0]
    assert sum(x["kalem"] == KIRIS for x in L["satirlar"]) == len(N6["veranda_kenarlari_cm"]) + len(N6["kose_kirisleri_cm"]) + 2
    sp = _satir(PL.liste(PL.model_pafta(_pafta(N6)), kurallar), OMEGA)
    assert (sp["adet"], sp["formul"]) == (4, s["formul"])
    N2 = PL.model_motor(_oku(KOK / "is_emri" / "adaylar" / "TEST02.json"))
    assert (len(N2["ic_kirisler_cm"]), round(sum(N2["ic_kirisler_cm"]), 2)) == (3, 502.0)
    assert N["ic_kirisler_cm"] == []


def test_motor_iki_acik_mahal_arasi_kiris_degil(N, kurallar):
    """Motor iki açık mahalin arasına da sınır çizgisi koyar (`geometry.py`: ikisi açıksa `acik_sinir`). O sınır iki oda arası değil; kiriş
    satırı ve duvar omegası terimi yazılmaz (geometri hakemi 3. tur; Lokman'ın 22 Ekim 05:26 kartı "iki oda arası"). PK-01'in verandası ikiye
    bölünür: 2,00 m'lik sınır sayılmaz, liste bölünmemiş PK-01'inkiyle aynı adet."""
    ie = _oku(VERI / "PK01.json")
    v = next(m for m in ie["mahaller"] if m["tur"] == "veranda")
    v["konum_cm"] = [[261, 795, 386.5, 995]]
    ie["mahaller"].append(dict(copy.deepcopy(v), ad="VERANDA 2", konum_cm=[[386.5, 795, 590, 995]]))
    Nb = PL.model_motor(ie)
    assert (Nb["ic_kirisler_cm"], Nb["ic_kalan_dis_duvar_m"]) == ([], N["ic_kalan_dis_duvar_m"])
    L = PL.liste(Nb, kurallar)
    assert (_satir(L, OMEGA)["adet"], _satir(L, OMEGA)["formul"]) == (3, "çatı kenarına gelmeyen dış duvarlar 5,34 m ÷ 2,5")
    assert not [x for x in L["satirlar"] if x["kalem"] == KIRIS and x["formul"].startswith("duvarsız sınırın boyu")]

def test_motor_veranda_kenar_boyunca(kurallar):
    """Verandası bir kenar boyunca uzanan türev (`test_t76_cevaplari`'ndaki gibi): ortak sınır kenar boyu, 6,00 m → 3."""
    ie = _oku(VERI / "PK01.json")
    for m in ie["mahaller"]:
        if m["tur"] == "veranda":
            m["konum_cm"] = [[10, 795, 590, 995]]
        if m["tur"] == "mutfak":
            m["konum_cm"] = [[10, 381.5, 261, 795]]
    ie["dikmeler"] = [[590, 0], [0, 0]]
    Nv = PL.model_motor(ie)
    assert (Nv["ic_kalan_dis_duvar_m"], Nv["W"]) == (6.0, 600.0)
    assert (_satir(PL.liste(Nv, kurallar), OMEGA)["adet"]) == 3


def test_motor_cati_parcasi_ve_girdideki_deger(N, kurallar):
    """Motor kipinde istisna yok: verandası ayrı açık çatı parçası olan sentetik türev (tekyon) de 3 (CIO 21 Ekim 16:56: istisna PK-06'da
    tutmuyordu). Girdide başka bir `ic_kalan_dis_duvar_m` verilirse o kullanılır (ters100 türevi 3,00)."""
    ana = N["cati"][0]
    veranda = dict(ana, ad="veranda", acik=True, makas_yok=True, aciklik_cm=200.0, boy_cm=300.0, kalkan=0, makas_kosu_cm=280.0)
    assert _satir(PL.liste(dict(copy.deepcopy(N), cati=[dict(ana, tip="tek_yon"), veranda]), kurallar), OMEGA)["adet"] == 3
    s = _satir(PL.liste(dict(copy.deepcopy(N), ic_kalan_dis_duvar_m=3.0), kurallar), OMEGA)
    assert (s["adet"], s["formul"]) == (2, "çatı kenarına gelmeyen dış duvarlar 3,00 m ÷ 2,5")


def test_pafta_motordan_tasinir(N, kurallar):
    """Motor'un değeri pafta biçimine taşınınca aynı adet; `ic_kirisler_cm` okunmamışsa formül uyarıyla başlar, `[]` ise uyarı yok."""
    sm = _satir(PL.liste(copy.deepcopy(N), kurallar), OMEGA)
    s0 = _satir(PL.liste(PL.model_pafta({k: v for k, v in _pafta(N).items() if k != "ic_kirisler_cm"}), kurallar), OMEGA)
    s1 = _satir(PL.liste(PL.model_pafta(_pafta(N)), kurallar), OMEGA)
    assert sm["adet"] == s0["adet"] == s1["adet"] == 3
    assert s0["formul"] == UYARI + sm["formul"] and s1["formul"] == sm["formul"]
    assert s0["formul"].endswith("÷ 2,5")


def test_pafta_verandali_okunmali(N):
    """Verandalı pafta girdisinde çatı kenarına gelmeyen dış duvar boyu okunmamışsa liste üretilmez. Dış duvar boyunun denetimi önce gelir
    (`test_t76_cevaplari` mesajında "dış duvar boyu" arar)."""
    with pytest.raises(ValueError, match="çatı kenarına gelmeyen dış duvar boyu"):
        PL.model_pafta({k: v for k, v in _pafta(N).items() if k != "ic_kalan_dis_duvar_m"})
    with pytest.raises(ValueError, match="`dis_cevre_m`"):
        PL.model_pafta({k: v for k, v in _pafta(N).items() if k not in ("ic_kalan_dis_duvar_m", "dis_cevre_m")})
    assert PL.model_pafta({k: v for k, v in _pafta(N, acik=[], dikmeler=0).items() if k != "ic_kalan_dis_duvar_m"})["ic_kalan_dis_duvar_m"] == 0.0


def test_pafta_e5_bicimi(kurallar):
    """E5: verandasız, duvarsız açıklıkta 3255'lik kiriş (gerçek listede kiriş 3255, duvar omegası 2). Kiriş okunmamışsa 0 ve uyarı; kirişsiz
    verandasız evde 0 (PK-05; Lokman, kart 22 Ekim "Doğru")."""
    L = PL.liste(PL.model_pafta(_e5(ic_kirisler_cm=[325.5])), kurallar)
    s = _satir(L, OMEGA)
    assert (s["adet"], s["formul"]) == (2, "çatı kenarında olmayan kirişler 3,25 m ÷ 2,5")
    assert [(x["olcu"], x["adet"]) for x in L["satirlar"] if x["kalem"] == KIRIS] == [("L 3255", 1)]
    assert [(x["adet"], x["formul"]) for x in (_satir(PL.liste(PL.model_pafta(_e5(**d)), kurallar), OMEGA) for d in ({}, {"ic_kirisler_cm": []}))] == [
        (0, UYARI + SIFIR), (0, SIFIR)]


def test_pafta_kiris_ve_ic_duvar_toplanir(kurallar):
    """Üç terim birlikte: yazı sıfır olmayan terimleri sırayla yazar, bölen sonda."""
    yp = _e5(ic_kirisler_cm=[280.0], ic_kalan_dis_duvar_m=1.5)
    s = _satir(PL.liste(PL.model_pafta(yp), kurallar), OMEGA)
    assert (s["adet"], s["formul"]) == (2, "çatı kenarına gelmeyen dış duvarlar 1,50 m + çatı kenarında olmayan kirişler 2,80 m ÷ 2,5")


@pytest.mark.parametrize("ik", [[0], [-5.0], "325", [None]])
def test_ic_kirisler_gecersiz(ik):
    with pytest.raises(ValueError, match="ic_kirisler_cm"):
        PL.model_pafta(_e5(ic_kirisler_cm=ik))


def test_kaynak_yazilari(kurallar):
    """CIO notu (PR #32 kıyası): baş makas omegasının kaynağı "kalkan" demez; duvar omegasının kaynağı kiriş terimini ve dayanağını söyler.
    D-32 (Lokman, 29 Ekim 13:12): baş makas omegası saçak ucundan saçak ucuna; kaynağın başı "altı"ndan "boyu"na döndü."""
    k = kurallar["prefabrik"]["kurallar"]
    assert k["bas_makas_omegasi_bolen_m"]["kaynak"].startswith("Baş makasların boyu saçak ucundan saçak ucuna ÷ 2,5")
    assert "kalkan" not in k["bas_makas_omegasi_bolen_m"]["kaynak"] and "13:12" in k["bas_makas_omegasi_bolen_m"]["kaynak"]
    assert "kirişler" in k["duvar_omegasi_100_bolen_m"]["kaynak"] and "16:22" in k["duvar_omegasi_100_bolen_m"]["kaynak"]
    assert k["duvar_omegasi_100_bolen_m"]["deger"] == 2.5
