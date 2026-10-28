"""İE-17 · Köşe ve ızgara kuralı, kapı yeri ve tam ızgara — Motor kilidi.

Bunlar Motor kilididir (bugünkü davranışı sabitler); paftaya uygunluk `testler/cizim/test_pafta_kiyasi.py`'de, paftadan ölçülen değerlerle.
Anahtarsız İş Emri'nin bayt bayt aynı kaldığını `testler/referans/dogrula.py` söyler; burada varsayılan yolun değerleri (köşe 10 × 5, kapı
menteşe ucunda) ayrıca kilitlenir.

- `yapi.kisa_kenar: y` (makas y'yi geçer): x ızgarası dış duvarın ekseninden (5 + 125,5k), y ızgarası iç yüzden (10 + 125,5k); dış köşe
  parçası 5 × 10. Varsayılan x: tersi (PK-01).
- `dizilim.son_pano: son_aks`: kesilmiş son pano ızgaranın sondan bir önceki aksından başlar.
- `dizilim.hiza: tam_izgara`: ekler yalnız tam akslarda, iç duvar T'de bölünmez.
- `dizilim.kapi_yeri: ortada` (ya da kapının kendi `kapi_yeri`'si): oda kapısı panoda ortada; varsayılan menteşe ucunda 11,5.
- `acikliklar[].duvar_ucu`: kapının panosu ortak duvarın o ucundaki kavşaktan başlayan tam pano.
- K21: `kisa_kenar: y` makas y'siz hata, makas y + `kisa_kenar` x uyarı; `dizilim` kapalı küme; `kapi_yeri` yalnız oda kapısında.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"


def _ie(ad: str) -> dict:
    return json.loads(((PK01 if ad == "PK01" else EVLER / f"{ad}.json")).read_text(encoding="utf-8"))


def _kur(ie: dict) -> G.Plan:
    return G.kur(copy.deepcopy(ie))


def _duvar(plan, yon, c, m=None):
    """Ekseni c olan duvar (aynı eksende birden çoksa m noktasını içeren)."""
    return next(d for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 1e-6 and (m is None or d.p0 <= m <= d.p1))


def _derz(plan, yon, c, m=None):
    return [round(p.a1, 2) for p in _duvar(plan, yon, c, m).panolar[:-1]]


def _kapi(plan, a, b):
    for d in plan.duvarlar:
        for p in d.panolar:
            if p.acilim and p.acilim.tur in ("ic_kapi", "dis_kapi") and set(p.acilim.arasi) == {a, b}:
                return d, p
    raise AssertionError((a, b))


# ---------------- köşe ve ızgara

def test_varsayilan_kisa_kenar_x_degismedi():
    plan = _kur(_ie("PK01"))
    assert G.KISA_KENAR == "x" and G.ilk_aks("x") == 10.0 and G.ilk_aks("y") == 5.0
    assert (G.X(0), G.Y(0)) == (10.0, 5.0)
    assert (0.0, 0.0, 10.0, 5.0) in [tuple(k.rect) for k in plan.koseler]        # dış köşe 10 (x) × 5 (y)


@pytest.mark.parametrize("ad, W, H", [("AP13", 763.0, 788.0), ("AP16", 763.0, 918.5), ("AP01", 1400.0, 1000.0)])
def test_kisa_kenar_y_izgara_ve_dis_kose(ad, W, H):
    plan = _kur(_ie(ad))
    assert G.KISA_KENAR == "y" and (G.ilk_aks("x"), G.ilk_aks("y")) == (5.0, 10.0) and (G.X(0), G.Y(0)) == (5.0, 10.0)
    assert (plan.W, plan.H) == (W, H)
    kose = {tuple(k.rect) for k in plan.koseler}
    assert {(0.0, 0.0, 5.0, 10.0), (0.0, H - 10, 5.0, H)} <= kose                  # dış köşe 5 (x) × 10 (y): ön ve arka duvar köşeden geçer
    on = _duvar(plan, "x", 5.0)                                                       # ön dış duvar köşeden başlar, ekleri eksenden 125,5
    assert on.p0 == 5.0 and _derz(plan, "x", 5.0)[:2] == [130.5, 256.0]
    sol = _duvar(plan, "y", 5.0)                                                      # sol duvar araya girer: iç yüzden
    assert (sol.p0, sol.p1) == (10.0, H - 10)


def test_kisa_kenar_makasi_izler():
    # köşe makasın oturduğu duvarlarda (on pafta): kisa_kenar y makas y'siz hata; makas y + kisa_kenar x (eski İş Emri'leri) uyarı
    ie = _ie("AP13")
    ie["cati"]["makas_ekseni"] = "x"
    with pytest.raises(G.IsEmriHatasi, match="kisa_kenar: y yalnız makas y'yi geçerken"):
        _kur(ie)
    assert G.KISA_KENAR == "x"
    p6 = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    assert not any("kisa_kenar x" in u for u in _kur(p6).uyarilar)
    p6["cati"]["makas_ekseni"] = "y"
    assert any(u.startswith("Makas y'yi geçiyor ama kisa_kenar x") for u in _kur(p6).uyarilar)
    assert not any("kisa_kenar x" in u for u in _kur(_ie("AP13")).uyarilar)


def test_kisa_kenar_geometri_anahtari():
    ie = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    assert ie["yapi"]["kisa_kenar"] == "x" and not G.geometri_anahtari_var(ie)
    ie["yapi"]["kisa_kenar"] = "y"
    assert G.geometri_anahtari_var(ie)                                                # ızgara değişir: doğrulama yeni yolun kuralıyla


@pytest.mark.parametrize("degis, mesaj", [
    (lambda ie: ie["yapi"]["dizilim"].update(sonpano="son_aks"), "dizilim'de bilinmeyen anahtar: sonpano"),
    (lambda ie: ie["yapi"]["dizilim"].update(kisa_kenar="y"), "dizilim'de bilinmeyen anahtar: kisa_kenar"),
    (lambda ie: ie["yapi"].update(son_pano=ie["yapi"]["dizilim"].pop("son_pano")), "son_pano yapi.dizilim altında yazılır"),
    (lambda ie: ie["yapi"].update(kapi_yeri="ortada"), "kapi_yeri yapi.dizilim altında yazılır"),
])
def test_dizilim_anahtari_yerinde(degis, mesaj):
    # K21: bilinmeyen ya da bir düzey kayık dizilim anahtarı sessizce varsayılana düşmez
    ie = _ie("AP16")
    degis(ie)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        _kur(ie)


def test_kisa_kenar_bilinmeyen_hata_ve_sifirlanir():
    ie = _ie("AP13")
    ie["yapi"]["kisa_kenar"] = "z"
    with pytest.raises(G.IsEmriHatasi, match="kisa_kenar bilinmiyor"):
        _kur(ie)
    _kur(_ie("AP13"))
    with pytest.raises(G.IsEmriHatasi):
        _kur(ie)
    assert G.KISA_KENAR == "x"                                                        # hatalı kurulumdan sonra varsayılana döner


def test_son_pano_son_aks():
    # AP-16 sol duvarı (arka-sol: arkadan dizilir): kesilmiş son pano (82,75) önde, sondan bir önceki yarım aksından; önünde yarım pano
    ie = _ie("AP16")
    assert _derz(_kur(ie), "y", 5.0)[:2] == [92.75, 155.5]
    ie["yapi"]["dizilim"]["son_pano"] = "kosu"
    assert _derz(_kur(ie), "y", 5.0)[:1] == [30.0]                                  # koşu: son parça 20 cm
    ie["yapi"]["dizilim"]["son_pano"] = "yok"
    with pytest.raises(G.IsEmriHatasi, match="son_pano bilinmiyor"):
        _kur(ie)


def test_tam_izgara_t_bolmez():
    # AP-01 salonun duvarı (önden 430,25): genel banyonun duvarı x 318,75'te T yapar; tam ızgarada ek yalnız tam akslarda (paftadaki gibi)
    ie = _ie("AP01")
    assert _derz(_kur(ie), "x", 430.25) == [130.5, 256.0, 381.5, 507.0]
    ie["yapi"]["dizilim"]["hiza"] = "kosu"
    for a in ie["acikliklar"]:
        a.pop("duvar_ucu", None)
    assert 318.75 in _derz(_kur(ie), "x", 430.25)                                     # koşu: iç duvar T'de bölünür (eski)
    ie["yapi"]["dizilim"]["hiza"] = "yok"
    with pytest.raises(G.IsEmriHatasi, match="tam_izgara"):
        _kur(ie)


# ---------------- kapı yeri

def test_kapi_yeri_ortada_ve_varsayilan():
    plan = _kur(_ie("AP13"))
    kapilar = [p.acilim for d in plan.duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "ic_kapi"]
    assert kapilar and all(a.kayma == 0.0 for a in kapilar)
    ie = _ie("AP13")
    del ie["yapi"]["dizilim"]["kapi_yeri"]                                            # varsayılan: menteşe ucunda 11,5 (PK-01)
    plan = _kur(ie)
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if a and a.tur == "ic_kapi" and a.kayma:
                s = (p.boy - a.genislik) / 2
                assert abs(a.kayma) == pytest.approx(s - G.KAPI_YASLAMA_CM)
    assert any(p.acilim.kayma for d in plan.duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "ic_kapi")


def test_kapinin_kendi_yeri_dizilimi_ezer():
    # AP-01: iki banyo kapısı paftada menteşe ucunda, öteki kapılar ortada
    plan = _kur(_ie("AP01"))
    for a, b, kayik in [("YATAK ODASI 2", "EBV BANYO 2", True), ("YATAK ODASI 3", "EBV BANYO 3", True), ("HOL VE KORİDOR", "SALON", False)]:
        d, p = _kapi(plan, a, b)
        assert (abs(p.acilim.kayma) == pytest.approx((p.boy - 82) / 2 - G.KAPI_YASLAMA_CM)) if kayik else p.acilim.kayma == 0.0, (a, b)


@pytest.mark.parametrize("degis, mesaj", [
    (lambda ie: ie["yapi"]["dizilim"].update(kapi_yeri="sag"), "kapi_yeri bilinmiyor"),
    (lambda ie: ie["yapi"]["dizilim"].update(kapi="is_emri"), "yalnız dizilim.kapi: mantik"),
    (lambda ie: ie["acikliklar"][0].update(kapi_yeri="ortada"), "yalnız kapıda"),
    (lambda ie: next(a for a in ie["acikliklar"] if a["tur"] == "ic_kapi").update(kapi_yeri="yarim"), "mentese_ucu \\| ortada"),
    (lambda ie: next(a for a in ie["acikliklar"] if a["tur"] == "dis_kapi").update(kapi_yeri="mentese_ucu"), "yalnız oda kapısında"),
])
def test_kapi_yeri_hatalari(degis, mesaj):
    ie = _ie("AP13")
    degis(ie)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        _kur(ie)


# ---------------- kapının duvar ucu

def test_duvar_ucu_kapi_panosu_kavsaktan():
    # AP-16: salon ile yatak odası 1 arasındaki kapı ve banyo 1'in kapısı şeridin ön ucunda (önden 469,25 kavşağı): pano 469,25–594,75
    plan = _kur(_ie("AP16"))
    for a, b, c in [("SALON", "YATAK ODASI 1", 381.5), ("YATAK ODASI 1", "BANYO 1", 256.0)]:
        d, p = _kapi(plan, a, b)
        assert d.c == c and round(p.a1, 2) == 594.75 and 469.25 <= p.a0 <= 472.25, (a, b, p.a0, p.a1)
    assert _derz(plan, "y", 381.5, 600) == [594.75, 657.5, 783.0]                           # kapı panosunun içindeki ızgara eki kalktı
    ie = _ie("AP16")
    for x in ie["acikliklar"]:
        if x.get("duvar_ucu") == "on":
            x["duvar_ucu"] = "arka"
    d, p = _kapi(_kur(ie), "SALON", "YATAK ODASI 1")
    assert round(p.a0, 2) == 532.0                                                    # arka uç: 532–657,5


@pytest.mark.parametrize("degis, mesaj", [
    (lambda k, ie: k.update(duvar_ucu="ust"), "on \\| arka \\| sol \\| sag"),
    (lambda k, ie: k.update(pano=0), "pano dizini olmadan"),
    (lambda k, ie: ie["acikliklar"][0].update(duvar_ucu="on"), "iki mahal arasındaki kapıda"),
    (lambda k, ie: k.update(duvar_ucu="sol"), "sol–sağ uzanan ortak duvar yok"),
])
def test_duvar_ucu_hatalari(degis, mesaj):
    ie = _ie("AP16")
    k = next(a for a in ie["acikliklar"] if a.get("duvar_ucu"))
    degis(k, ie)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        _kur(ie)


def test_duvar_ucu_kisa_ortak_duvar_hata():
    # ortak duvar tam panodan kısaysa açık hata (sessizce başka panoya düşmez): AP-01'de ebeveyn banyosu 1 ile yatak odası 1'in ön–arka
    # uzanan ortak duvarı 62,75 (x 130,5; önden 613,5–676,25); kapıları sol–sağ uzanan duvarda
    ie = _ie("AP01")
    k = next(a for a in ie["acikliklar"] if a.get("arasi") == ["YATAK ODASI 1", "EBV BANYO 1"])
    k["duvar_ucu"] = "sol"
    d, p = _kapi(_kur(ie), "YATAK ODASI 1", "EBV BANYO 1")
    assert d.yon == "x" and d.c == 676.25
    k["duvar_ucu"] = "on"
    with pytest.raises(G.IsEmriHatasi, match="tam panoya kısa"):
        _kur(ie)


def test_geometri_anahtari():
    ie = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    assert not G.geometri_anahtari_var(ie)
    ie["acikliklar"][-1]["duvar_ucu"] = "on"
    assert G.geometri_anahtari_var(ie)
