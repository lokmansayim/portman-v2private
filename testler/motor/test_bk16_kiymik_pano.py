"""BK-16 · Odaya ortalanan pencereli panonun derz kıymığı — Motor kilidi.

`dizilim.pencere: oda_ortasi` (D-15) pencereli panoyu odanın net ortasına keser. Panonun ucu bir komşu derze
`G.PENCERE_DERZ_ESIGI_CM`'den (15) az kala bitiyorsa aradaki parça pano olmaz (K21, sessiz yuvarlama yok): derz kalkar, parça derzin
ötesindeki panoya katılır ve `plan.uyarilar`'a yazılır; pencereli pano yerinde kalır. Derzin ötesinde pano yoksa (duvar ucu) ya da o pano
bir kapı / pencere panosuysa açık hata (`IsEmriHatasi`).

Kaynak vaka: İE-22 taslağının CK-01 zemin katı (28.10.2026): salonun sol penceresi odaya ortalanınca Motor sol dış duvarda 0,625 cm'lik pano
üretiyor, doğrulama "Duvar kalınlığı uyuşmuyor" ile düşüyordu. Kilit İş Emri `veri/BK16_CK01_zemin.json` (dizilim arka-sol: sayılar İş Emri
çerçevesinde arkadan, Plan sonda aynalanır). Bugünkü `oda_ortasi` evlerinde (PK-01, AP-01, AP-16, TK-01, PK-02) kural devreye girmez.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
EVLER = KOK / "testler" / "cizim" / "evler"
CK01 = VERI / "BK16_CK01_zemin.json"
BUGUNKU_EVLER = [VERI / "PK01.json", VERI / "TK01.json", EVLER / "AP01.json", EVLER / "AP16.json",
                 KOK / "testler" / "kor" / "projeler" / "PK02" / "is_emri.json"]


def _ie(yol: Path = CK01) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _kur(ie: dict) -> G.Plan:
    return G.kur(copy.deepcopy(ie))


def _sol_dis_duvar(plan: G.Plan) -> G.Duvar:
    return next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.c - G.T_DIS / 2) < 1e-6)


def _boylar(d: G.Duvar) -> list:
    return [round(p.boy, 3) for p in d.panolar]


def _bk16(plan: G.Plan) -> list:
    return [u for u in plan.uyarilar if "BK-16" in u]


def _olcuye_kes(ie: dict, y: float) -> dict:
    """CK-01'in y dış ölçüsünü değiştirir; ön iç yüze (696) dayanan mahaller yeni son aksa çekilir. Salonun net ortası ve pencereli panonun
    ucu kayar, kesilmiş son panonun derzi (574,75) yerinde kalır: kalan parça = 574,75 − (326,75 + (y − 10)) / 2 − 62,75."""
    ie = copy.deepcopy(ie)
    ie["yapi"]["dis_olcu_cm"]["y"] = y
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            if abs(r[3] - 696) < 1e-9:
                r[3] = y - 10
    return ie


def _duvar_ucu_varyanti(ie: dict, son_aks: float) -> dict:
    """Salon ön iç yüze kadar uzar ve ev kısalır (ızgara y 4, ölçüye kesim): pencereli pano duvar ucuna yakın biter, ötesinde pano yok."""
    ie = copy.deepcopy(ie)
    ie["yapi"]["dis_olcu_cm"]["y"] = son_aks + 10
    ie["yapi"]["grid"]["y_pano"] = 4
    ie["mahaller"] = [m for m in ie["mahaller"] if m["ad"] != "BALKON"]
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            if r[3] in (696, 574.75):
                r[3] = son_aks
    return ie


# ---------------- CK-01 zemin kat kilidi (U1)

def test_ck01_zemin_kati_kilidi():
    plan = _kur(_ie())
    assert len(plan.panolar) == 44                                   # kıymıkla 45'ti
    assert not [u for u in plan.uyarilar if "kısa pano" in u]
    assert _bk16(plan) == ["Pencere SALON 120x125: odaya ortalanan pencereli pano (448.625–574.125) derze 0.625 cm kala bitiyordu; "
                           "kalan parça komşu panoya katıldı (ek 574.75 → 574.125, komşu pano 121.875 cm; BK-16)"]
    sol = _sol_dis_duvar(plan)
    assert _boylar(sol) == [121.875, 125.5, 62.125, 125.5, 32.875, 125.5, 92.625]   # Plan aynalı: önden arkaya
    # pencereli pano yerinde: 125,5 ve salonun net ortasında (İş Emri çerçevesinde 511,375 → aynalı 706 − 511,375)
    pencereli = next(p for p in sol.panolar if p.acilim and p.acilim.mahal == "SALON")
    assert abs(pencereli.boy - G.MOD) < 1e-9
    assert abs((pencereli.a0 + pencereli.a1) / 2 - (706 - 511.375)) < 1e-9
    # kesilmiş son pano kalan parçayı aldı: 121,25 → 121,875; ucu pencereli panonun derzinde
    assert abs(sol.panolar[0].boy - 121.875) < 1e-9 and abs(sol.panolar[0].a1 - pencereli.a0) < 1e-9


def test_ck01_dogrulama_gecer_teslim_pdf_var(tmp_path):
    ie = _ie()
    sonuc = dxf_out.uret(ie, tmp_path, pdf_hatada=True)
    assert sonuc["validation_passed"] is True
    pdfler = sorted(p.name for p in tmp_path.glob("*.pdf"))
    assert pdfler == ["Portman_BK16-CK01-ZEMIN_r01.pdf"]             # .HATALI.pdf yok (K23)
    dogrulama = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert dogrulama["passed"] is True and dogrulama["errors"] == [] and dogrulama["panel_count"] == 44
    assert any("BK-16" in u for u in dogrulama["warnings"])


# ---------------- eşik (U2): 15 cm'den az katılır, 15 ve üstü ayrı pano kalır

def test_esigin_altinda_katilir_ustunde_pano_kalir():
    assert G.PENCERE_DERZ_ESIGI_CM == 15.0
    katilan = _kur(_olcuye_kes(_ie(), 677.5))                       # kalan 14,875
    assert len(katilan.panolar) == 44 and len(_bk16(katilan)) == 1 and "derze 14.875 cm kala" in _bk16(katilan)[0]
    assert _boylar(_sol_dis_duvar(katilan))[:3] == [107.625, 125.5, 47.875]
    kalan = _kur(_olcuye_kes(_ie(), 677))                           # kalan 15,125: bugünkü gibi ayrı pano, "çok kısa pano" uyarısı sürer
    assert len(kalan.panolar) == 45 and _bk16(kalan) == []
    assert _boylar(_sol_dis_duvar(kalan))[:4] == [92.25, 15.125, 125.5, 47.625]
    assert [u for u in kalan.uyarilar if "15.125 cm'lik çok kısa pano" in u]


# ---------------- duvar ucu (U3): katılacak pano yoksa açık hata

def test_duvar_ucunda_acik_hata():
    with pytest.raises(G.IsEmriHatasi, match=r"Pencere SALON 120x125: .*duvar ucuna 14\.875 cm kala bitiyor.*`pano` diziniyle"):
        _kur(_duvar_ucu_varyanti(_ie(), 482))
    plan = _kur(_duvar_ucu_varyanti(_ie(), 483))                    # 15,375: eşiğin üstünde, pano kalır
    assert _bk16(plan) == [] and 15.375 in _boylar(_sol_dis_duvar(plan))


# ---------------- yardımcı: iki yan, korunan pano, duvar ucu

def _ac():
    return {"mahal": "SALON", "olcu": "120x125"}


def test_yardimci_sagdaki_derz_kalkar_komsu_uzar():
    u = []
    pts = G._pencere_kiymigi_kat([0.0, 100.0, 225.5, 240.0, 500.0], 100.0, 225.5, [], _ac(), u)
    assert pts == [0.0, 100.0, 225.5, 500.0]
    assert u == ["Pencere SALON 120x125: odaya ortalanan pencereli pano (100–225.5) derze 14.5 cm kala bitiyordu; kalan parça komşu panoya "
                 "katıldı (ek 240 → 225.5, komşu pano 274.5 cm; BK-16)"]


def test_yardimci_soldaki_derz_kalkar():
    u = []
    pts = G._pencere_kiymigi_kat([0.0, 90.0, 100.0, 225.5, 500.0], 100.0, 225.5, [], _ac(), u)
    assert pts == [0.0, 100.0, 225.5, 500.0]
    assert len(u) == 1 and "derze 10 cm kala" in u[0] and "ek 90 → 100, komşu pano 100 cm" in u[0]


def test_yardimci_iki_yan_birden_ve_esik_tam_15_kalir():
    u = []
    pts = G._pencere_kiymigi_kat([0.0, 95.0, 100.0, 225.5, 230.0, 500.0], 100.0, 225.5, [], _ac(), u)
    assert pts == [0.0, 100.0, 225.5, 500.0] and len(u) == 2
    u = []
    pts = G._pencere_kiymigi_kat([0.0, 85.0, 100.0, 225.5, 240.5, 500.0], 100.0, 225.5, [], _ac(), u)
    assert pts == [0.0, 85.0, 100.0, 225.5, 240.5, 500.0] and u == []   # 15 cm: pano kalır


def test_yardimci_korunan_panoya_katilmaz():
    with pytest.raises(G.IsEmriHatasi, match=r"kapı / pencere panosuna 4\.5 cm kala"):
        G._pencere_kiymigi_kat([0.0, 100.0, 225.5, 230.0, 355.5, 500.0], 100.0, 225.5, [(230.0, 355.5)], _ac(), [])
    with pytest.raises(G.IsEmriHatasi, match=r"kapı / pencere panosuna 4\.5 cm kala"):
        G._pencere_kiymigi_kat([0.0, 95.5, 100.0, 225.5, 500.0], 100.0, 225.5, [(0.0, 95.5)], _ac(), [])


def test_yardimci_duvar_ucunda_hata():
    with pytest.raises(G.IsEmriHatasi, match=r"duvar ucuna 9\.5 cm kala"):
        G._pencere_kiymigi_kat([0.0, 100.0, 225.5, 235.0], 100.0, 225.5, [], _ac(), [])
    with pytest.raises(G.IsEmriHatasi, match=r"duvar ucuna 10 cm kala"):
        G._pencere_kiymigi_kat([0.0, 10.0, 135.5, 400.0], 10.0, 135.5, [], _ac(), [])


# ---------------- bugünkü evler (U4): kural devreye girmez, derzler aynı

@pytest.mark.parametrize("yol", BUGUNKU_EVLER, ids=lambda p: p.stem if p.stem != "is_emri" else p.parent.name)
def test_bugunku_oda_ortasi_evlerinde_kural_devreye_girmez(yol, monkeypatch):
    ie = _ie(yol)
    assert (ie["yapi"].get("dizilim") or {}).get("pencere") == "oda_ortasi"
    plan = _kur(ie)
    assert _bk16(plan) == []
    derzler = [(d.id, [round(p.a0, 3) for p in d.panolar]) for d in plan.duvarlar]
    monkeypatch.setattr(G, "PENCERE_DERZ_ESIGI_CM", 0.0)             # kural kapalı
    assert [(d.id, [round(p.a0, 3) for p in d.panolar]) for d in _kur(ie).duvarlar] == derzler
