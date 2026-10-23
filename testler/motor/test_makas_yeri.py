"""BK-12 PR-R · IFC makas yeri (`motor/ifc_uret.py › cati`, makaslar x'i geçince).

Kural: baş makaslar uç duvarların ekseninde (5 cm ve boy − 5 cm), orta makaslar boydan boya kesintisiz koşan saçak duvarının pano
eklerinde; PK-01'de paftadaki MK01–MK09 ("125,5 c/c"). İki saçak duvarı da kesintisizse ortak ekler alınır, ekler farklıysa uyarı
yazılır. Ekler düzenli olmalı (orta makaslar 125,5 arayla, uç açıklıklar 125,5'ten uzun değil, sayı listeyle aynı); değilse ya da
iki duvar da kesintiliyse eşit aralık kalır (liste sayısında makas, baş makaslar uç duvarların ekseninde), uyarı özete ve IFC'ye
(`PortatifEv_Uyari`) yazılır (K16). Makas sayısı her yolda listeninkiyle aynı: liste makasları kendi kuralıyla sayar
(`prefabrik_liste.py`, saçak duvarının pano koşusu ÷ 125,5 yukarı + 1), IFC aynı sayıyı verir. Düzensiz eklere iki örnek geometri hakeminin (23 Ekim): saçak duvarında 251'lik pencereli pano ve dış duvarın T'de
ızgara dışında bölünmesi.
"""
from __future__ import annotations
import copy
import json
import math
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret as I, prefabrik_liste as PL  # noqa: E402

PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"
YAN = KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json"
YEDI = [KOK / "is_emri" / f for f in ("ALTIN_2plus1_6x8.json", "P6001_2plus1_6x6.json", "P6001_ayna_x.json", "P6001_ayna_y.json")] + \
       [KOK / "is_emri" / "adaylar" / f"TEST0{i}.json" for i in (1, 2, 3)]
PK01_PAFTA = [5, 116.5, 242, 367.5, 493, 618.5, 744, 869.5, 995]          # MK01–MK09: baş makaslar ve sol duvarın pano ekleri
YAN_KAYNAK = [5, 130.5, 256, 381.5, 507, 632.5, 758, 883.5, 1009, 1071.75]  # ref_yan DXF'inin sol duvarındaki pano ekleri


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _cati(G: dict, yol: Path) -> dict:
    u = I.IfcUretici(G, "makas yeri")
    u.calistir(yol)
    return u.cati_ozet


def _esit(Hd: float) -> list[float]:
    """PR-R'den önceki dizilim: 5 … boy − 5 arası eşit aralık."""
    n = math.ceil((Hd - 10) / 125.5) + 1
    return [round(5 + i * (Hd - 10) / (n - 1), 2) for i in range(n)]


def _yedek(G: dict) -> list[float]:
    """Eşit aralık yedeği: liste sayısında makas, uçlar uç duvarların ekseninde (100'lük dış duvarda `_esit` ile aynı)."""
    Hd = _boy(G); td = max(p["kalinlik"] for p in G["panolar"])
    n = math.ceil((Hd - 2 * td) / 125.5 - 1e-6) + 1
    return [round(td / 2 + i * (Hd - td) / (n - 1), 2) for i in range(n)]


def _boy(G: dict) -> float:
    return max(p["rect"][3] for p in G["panolar"])


def _ifc_uyari(yol: Path) -> str | None:
    f = ifcopenshell.open(str(yol))                      # dosya nesnesi açık kalmalı (varlıklar ona bağlı)
    return ue.get_psets(f.by_type("IfcRoof")[0]).get("PortatifEv_Uyari", {}).get("MakasYeri")


def _altin_iki_tam() -> dict:
    """ALTIN'ın sol saçak duvarı verandada kesik (256'dan başlar); 5–256 arası iki 125,5'lik panoyla kapanınca iki duvar da
    kesintisiz ve ekleri sağınkiyle aynı olur (bugünkü dokuz evin hiçbirinde iki saçak duvarı birden kesintisiz değil)."""
    G = I.hazirla(_oku(KOK / "is_emri" / "ALTIN_2plus1_6x8.json"))
    sol = [p for p in G["panolar"] if p["yon"] == "y" and p["tur"] == "dis" and p["rect"][0] == 0]
    assert min(p["rect"][1] for p in sol) == 256
    for y0, y1 in ((5.0, 130.5), (130.5, 256.0)):
        ek = copy.deepcopy(min(sol, key=lambda p: p["rect"][1]))
        ek["rect"][1], ek["rect"][3], ek["boy"], ek["acikliklar"] = y0, y1, y1 - y0, []
        ek["id"] = max(q["id"] for q in G["panolar"]) + 1
        G["panolar"].append(ek)
    return G


def _bol(G: dict, x: float, y0: float, orta: float) -> None:
    """x'teki saçak duvarının y0'da başlayan panosunu orta'da ikiye böler (duvar kesintisiz kalır, araya bir ek girer)."""
    p = next(q for q in G["panolar"] if q["yon"] == "y" and q["tur"] == "dis" and q["rect"][1] == y0
             and (q["rect"][0] == 0 if x == 0 else q["rect"][2] == x))
    a, b = copy.deepcopy(p), copy.deepcopy(p)
    a["rect"][3] = b["rect"][1] = orta; a["boy"], b["boy"] = orta - y0, p["rect"][3] - orta
    b["id"] = max(q["id"] for q in G["panolar"]) + 1
    G["panolar"] = [q for q in G["panolar"] if q is not p] + [a, b]


def test_pk01_makaslari_paftadaki_eklerde(tmp_path):
    oz = I.uret(_oku(PK01), tmp_path / "pk01.ifc")
    assert oz["sema_hatasi"] == 0
    assert oz["cati"]["makas"] == 9 and oz["cati"]["makas_y_cm"] == PK01_PAFTA and "uyari" not in oz["cati"]
    assert _ifc_uyari(tmp_path / "pk01.ifc") is None
    assert {round(b - a, 2) for a, b in zip(PK01_PAFTA[1:-1], PK01_PAFTA[2:-1])} == {125.5}


def test_yan_verandali_kaynagin_pano_eklerinde(tmp_path):
    c = I.uret(_oku(YAN), tmp_path / "yan.ifc")["cati"]
    assert c["makas"] == 10 and c["makas_y_cm"] == YAN_KAYNAK and "uyari" not in c
    # orta makaslar 125,5 arayla; son açıklık 1009'da başlayan 62,75'lik pano (yarım pano), baş makas uç duvarın ekseninde
    assert {round(b - a, 2) for a, b in zip(c["makas_y_cm"][1:-1], c["makas_y_cm"][2:-1])} == {125.5}
    assert round(c["makas_y_cm"][-1] - c["makas_y_cm"][-2], 2) == 62.75


@pytest.mark.parametrize("yol", YEDI, ids=lambda p: p.stem)
def test_yedi_evde_yer_eskisiyle_ayni(yol, tmp_path):
    ie = _oku(yol)
    c = I.uret(ie, tmp_path / "ev.ifc")["cati"]
    assert c["makas_y_cm"] == _esit(_boy(I.hazirla(copy.deepcopy(ie)))) and "uyari" not in c


@pytest.mark.parametrize("yol", [PK01, YAN] + YEDI, ids=lambda p: p.stem)
def test_makas_sayisi_listeyle_ayni(yol, tmp_path):
    ie = _oku(yol)
    assert I.uret(ie, tmp_path / "ev.ifc")["cati"]["makas"] == PL.liste(PL.model_motor(ie))["girdi_ozeti"]["makas"]


def test_iki_sacak_duvari_kesintiliyse_esit_aralik_ve_uyari(tmp_path):
    """PK-01'in sağ saçak duvarı verandada kesik (205'ten başlar); sol duvardan bir pano çıkınca iki duvar da kesintili."""
    G = I.hazirla(_oku(PK01))
    G["panolar"] = [p for p in G["panolar"] if not (p["yon"] == "y" and p["tur"] == "dis" and p["rect"][0] == 0 and p["rect"][1] == 367.5)]
    c = _cati(G, tmp_path / "kesik.ifc")
    assert c["makas_y_cm"] == _yedek(G) == _esit(_boy(G)) and c["makas"] == 9
    assert c["uyari"] == ["makas yeri: boydan boya kesintisiz saçak duvarı yok; eşit aralıklı 9 makas"]
    assert _ifc_uyari(tmp_path / "kesik.ifc") == c["uyari"][0]


def test_iki_sacak_duvari_kesintisiz_ekler_ayni(tmp_path):
    G = _altin_iki_tam()
    c = _cati(G, tmp_path / "iki_tam.ifc")
    assert c["makas_y_cm"] == _esit(_boy(G)) and c["makas"] == 9 and "uyari" not in c


def test_iki_sacak_duvarinin_ekleri_farkliysa_ortak_ekler_ve_uyari(tmp_path):
    """Sağ duvarın bir panosu ikiye bölünür: yeni ek solda yok, ortak değildir, makas almaz; ortak ekler düzenli."""
    G = _altin_iki_tam()
    Wd = max(p["rect"][2] for p in G["panolar"])
    _bol(G, Wd, 256.0, 318.75)
    c = _cati(G, tmp_path / "farkli.ifc")
    assert c["makas_y_cm"] == _esit(_boy(G)) and 318.75 not in c["makas_y_cm"]
    assert c["uyari"] == ["makas yeri: iki saçak duvarının pano ekleri farklı; ortak ekler alındı"]
    assert _ifc_uyari(tmp_path / "farkli.ifc") == c["uyari"][0]


def test_ortak_ekler_duzensizse_esit_aralik_ve_uyari(tmp_path):
    """Sol duvarın 5–256 arası tek bir 251'lik panoyla kapanınca 130,5'teki ek ortak değildir; ortak eklerde 251'lik açıklık kalır."""
    G = I.hazirla(_oku(KOK / "is_emri" / "ALTIN_2plus1_6x8.json"))
    sol = [p for p in G["panolar"] if p["yon"] == "y" and p["tur"] == "dis" and p["rect"][0] == 0]
    ek = copy.deepcopy(min(sol, key=lambda p: p["rect"][1]))
    ek["rect"][1], ek["rect"][3], ek["boy"], ek["acikliklar"] = 5.0, 256.0, 251.0, []
    ek["id"] = max(q["id"] for q in G["panolar"]) + 1
    G["panolar"].append(ek)
    c = _cati(G, tmp_path / "duzensiz.ifc")
    assert c["makas_y_cm"] == _yedek(G) == _esit(_boy(G)) and c["makas"] == 9
    assert c["uyari"][0] == "makas yeri: iki saçak duvarının pano ekleri farklı; ortak ekler alındı"
    assert c["uyari"][1].startswith("makas yeri: saçak duvarının pano ekleri düzensiz (8 makas, listede 9; aralıklar 251, 125.5")
    assert c["uyari"][1].endswith("); eşit aralıklı 9 makas") and len(c["uyari"]) == 2


@pytest.mark.parametrize("olcu", ["200x120", "240x120"])
def test_sacak_duvarinda_genis_pencere_esit_aralik_ve_uyari(olcu, tmp_path):
    """BK-13: saçak duvarındaki geniş pencere 251'lik panoda; panonun ortasında ek yok. Makas sayısı listeyle aynı kalır."""
    ie = _oku(PK01)
    a = next(a for a in ie["acikliklar"] if a["tur"] == "pencere" and a["mahal"] == "YATAK ODASI 1" and a["duvar"] == "sol")
    a["olcu"] = olcu
    oz = I.uret(ie, tmp_path / "genis.ifc")
    c = oz["cati"]
    assert oz["sema_hatasi"] == 0 and c["makas"] == 9 == PL.liste(PL.model_motor(ie))["girdi_ozeti"]["makas"]
    assert c["makas_y_cm"] == _esit(1000) and len(c["uyari"]) == 1 and "düzensiz (8 makas, listede 9;" in c["uyari"][0]
    assert _ifc_uyari(tmp_path / "genis.ifc") == c["uyari"][0]


def test_dis_duvar_t_de_izgara_disinda_bolunurse_esit_aralik_ve_uyari(tmp_path):
    """PK-01 `dis_duvar_t_bolme`: YATAK ODASI 1 ile MUTFAK'ın sınırı ek aksa (440) çekilince sol duvar T'de ızgara dışında bölünür."""
    ie = _oku(PK01)
    ie["yapi"]["ek_akslar_cm"]["y"] = [440, 795]
    for m in ie["mahaller"]:
        if m["ad"] == "YATAK ODASI 1":
            m["konum_cm"] = [[10, 5, 198.25, 256], [10, 256, 261, 440]]
        if m["ad"] == "MUTFAK":
            m["konum_cm"] = [[10, 440, 261, 995]]
    c = I.uret(ie, tmp_path / "t.ifc")["cati"]
    assert c["makas"] == 9 == PL.liste(PL.model_motor(ie))["girdi_ozeti"]["makas"]
    assert c["makas_y_cm"] == _esit(1000) and len(c["uyari"]) == 1 and "düzensiz (10 makas, listede 9;" in c["uyari"][0]


def test_sacak_duvarinda_izgara_disi_ek_esit_aralik(tmp_path):
    """Aynı mekanizma, doğrudan: sol duvarın bir panosu ızgara dışında ikiye bölünür (tek kesintisiz duvar)."""
    G = I.hazirla(_oku(PK01))
    _bol(G, 0, 367.5, 440.0)
    c = _cati(G, tmp_path / "bolunmus.ifc")
    assert c["makas_y_cm"] == _yedek(G) == _esit(_boy(G)) and c["makas"] == 9 and "düzensiz (10 makas, listede 9;" in c["uyari"][0]


@pytest.mark.parametrize("boy", [1016, 1018, 1020])
def test_160_100_duvarda_yedek_liste_sayisinda_ve_uc_duvar_ekseninde(boy, tmp_path):
    """Geometri hakemi 2. tur: 160 / 100 duvarlı PK-01 türevi (D-12 müşteri seçeneği), saçak duvarında 200x120. Yedek, eski
    sabitlerle (boy − 10, uçlar 5) listeden bir fazla makas veriyordu; artık liste sayısında ve baş makaslar 8'de (uç duvar ekseni)."""
    ie = _oku(PK01)
    X = {10: 16, 590: 584, 198.25: 204.25, 261: 267, 386.5: 392.5}
    Y = {5: 8, 995: boy - 8, 256: 259, 381.5: 384.5, 795: 798}
    ie["yapi"]["duvar_kalinligi_cm"] = {"dis": 16, "ic": 10}; ie["yapi"]["ek_akslar_cm"]["y"] = [798]; ie["yapi"]["dis_olcu_cm"]["y"] = boy
    for m in ie["mahaller"]:
        m["konum_cm"] = [[X.get(a, a), Y.get(b, b), X.get(c, c), Y.get(e, e)] for a, b, c, e in m["konum_cm"]]
    next(a for a in ie["acikliklar"] if a["tur"] == "pencere" and a["mahal"] == "YATAK ODASI 1" and a["duvar"] == "sol")["olcu"] = "200x120"
    c = I.uret(ie, tmp_path / "kalin.ifc")["cati"]
    assert c["makas"] == PL.liste(PL.model_motor(ie))["girdi_ozeti"]["makas"] == len(c["makas_y_cm"])
    assert c["makas_y_cm"][0] == 8 and c["makas_y_cm"][-1] == boy - 8
    assert len({round(b - a, 2) for a, b in zip(c["makas_y_cm"], c["makas_y_cm"][1:])}) == 1          # eşit aralık
    assert c["uyari"][-1].endswith(f"; eşit aralıklı {c['makas']} makas")
