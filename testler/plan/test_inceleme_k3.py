"""İE-14 kapanış incelemesi · K3 (15.10.2026): geometri ve çatı.

G3 kırma mahyası 15 cm ve daha kısa olamaz (D-10) · G4 prefabrik sözleşmede yarım pano ızgarası · G5 L kanat eğimi aralıkta, cumba uzun
kenarda · G7 sözleşme çekirdeği ondalığı kesmez, çelik yazma denetçiden geçer · G8 mahya yönü tek yerde · G9 beşik/kırmaya tek dikdörtgen ·
G10 dış büyütme köşe verandayı büyütmez, 50 cm varsayımı yazılır · G11 dönüşüm notları çevirir. LLM çağrısı yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_adaptor as A, plan_islem as PI, plan_uretici as PU  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402
from beyin.plan_sema import cekirdek, sozlesme  # noqa: E402
from motor.genel import cati_ortak, cati_uretici as CU  # noqa: E402
from motor.geometry import MOD  # noqa: E402


# ── G3 · kırma mahyası ──────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("en,boy", [(1070, 1075), (1000, 1015), (1085, 1075)])
def test_g3_kisa_kirma_mahyasi_reddedilir(en, boy):
    with pytest.raises(CU.CatiHatasi, match="kırma mahyası"):
        CU.uret((0, 0, en, boy), "kirma")


@pytest.mark.parametrize("en,boy", [(1000, 1000), (1000, 1020), (1095, 750)])
def test_g3_kare_ya_da_uzun_mahya_kurulur(en, boy):
    c = CU.uret((0, 0, en, boy), "kirma")
    assert CU.denetle(c, (0, 0, en, boy)) == []


def test_g3_besikte_sinir_yok():
    assert CU.denetle(CU.uret((0, 0, 1070, 1075), "besik"), (0, 0, 1070, 1075)) == []


@pytest.mark.parametrize("talep", [{"alan_m2": 115, "oda_programi": "3+1", "cati": {"tip": "kirma"}},
                                   {"alan_m2": 115, "oda_programi": "4+1", "cati": {"tip": "kirma"}}])
def test_g3_hakemin_talepleri_kisa_mahyasiz(talep):
    # önceden ilk aday 1070 × 1075 (mahya 5 cm) ve 1085 × 1060 (25 cm, kurala uygun) idi
    s = PU.uret(talep, ayar={"acik": False})
    assert s["durum"] == "gecerli"
    for a in s["adaylar"]:
        W, H = a["plan"]["dis_olcu"]["en"], a["plan"]["dis_olcu"]["boy"]
        assert abs(W - H) == 0 or abs(W - H) > 15, (W, H)


def test_g3_g8_denetci_tek_ihlal_verir():
    # kısa mahyalı kırma planı denetçide "çatı:" ihlaliyle düşer; W × H'ye bakan ikinci mahya kontrolü yok
    p = json.loads((KOK / "testler" / "plan" / "ornekler" / "T95_3p1_kirma.json").read_text(encoding="utf-8")) \
        if (KOK / "testler" / "plan" / "ornekler" / "T95_3p1_kirma.json").exists() else None
    if p is None:
        p = PU.uret({"alan_m2": 95, "oda_programi": "3+1", "cati": {"tip": "kirma"}}, ayar={"acik": False})["plan"]
    p = copy.deepcopy(p)
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    p["cati"] = {**(p.get("cati") or {}), "tip": "kirma", "mahya_yonu": "y" if W > H else "x"}
    d = denetle(p, {})
    assert not d["gecerli"] and sum("mahya" in x for x in d["ihlaller"]) == 1, d["ihlaller"]


# ── G4 · prefabrik yarım pano ızgarası ─────────────────────────────────────────────────────────────────────────────────
def test_g4_prefabrik_izgara_disi_olcu_reddedilir():
    s = A.prefabrik_oku(json.loads((KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json").read_text(encoding="utf-8")))
    assert A.denetle(s, "2+1")["gecerli"]
    eski = 2.5 * MOD
    bozuk = copy.deepcopy(s)
    for m in bozuk["mahaller"]:
        for r in m["dikdortgenler"]:
            for i, v in enumerate(r):
                if abs(v - eski) < 1e-6:
                    r[i] = 320.0                                            # hakemin denemesi: 313,75 → 320
    d = A.denetle(bozuk, "2+1")
    assert not d["gecerli"] and any("ızgara dışı" in x for x in d["kalemler"]["sozlesme"])


def test_g4_pano_tek_kaynaktan():
    assert A.PANO is MOD or A.PANO == MOD == 125.5


# ── G5 · L ve cumba biçimi ─────────────────────────────────────────────────────────────────────────────────────────────
def test_g5_l_kanat_egimi_araligi_asarsa_red():
    with pytest.raises(CU.CatiHatasi, match="aralık dışı"):
        CU.uret([[0, 0, 600, 640], [600, 0, 800, 640]], "l")               # hakemin örneği: kanat %88,8


def test_g5_cumba_kisa_kenarda_red():
    with pytest.raises(CU.CatiHatasi, match="uzun kenarına"):
        CU.uret([[0, 0, 1000, 600], [1000, 200, 1200, 400]], "cumba")


# ── G7 · sözleşme çekirdeği ve çelik yazma ─────────────────────────────────────────────────────────────────────────────
def _soz(p):
    return sozlesme(p, "tek_kat_celik", {"yol": "cozucu"})


def test_g7_cekirdek_ondaligi_kesmez():
    p = PU.uret({"alan_m2": 80, "oda_programi": "2+1"}, ayar={"acik": False})["plan"]
    s = _soz(p)
    s["mahaller"][0]["dikdortgenler"][0][2] += 0.9
    with pytest.raises(ValueError, match="tam cm"):
        cekirdek(s)


def test_g7_celik_yaz_denetciden_gecer_ve_dis_140():
    p = PU.uret({"alan_m2": 80, "oda_programi": "2+1"}, ayar={"acik": False})["plan"]
    t = A.celik_yaz({**_soz(p), "dis_karkas": 140})
    assert t["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2"          # önceden derleyici 80'lik yazıyordu


# ── G9 · beşik/kırmaya tek dikdörtgen ──────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("tip", ["besik", "kirma"])
def test_g9_birden_cok_dikdortgen_hata(tip):
    with pytest.raises(CU.CatiHatasi, match="tek dikdörtgen"):
        CU.uret([[0, 0, 1000, 700], [1000, 0, 1200, 300]], tip)
    assert CU.uret([[0, 0, 1000, 700]], tip)["duzlemler"]                  # tek dikdörtgenli liste geçerli


# ── G10 · revizyon işlemleri ───────────────────────────────────────────────────────────────────────────────────────────
def _kose_verandali():
    s = PU.uret({"alan_m2": 140, "oda_programi": "4+1", "cati": {"tip": "kirma"}, "veranda": {"istiyor": True, "konum": "kose"}},
                ayar={"acik": False})
    assert s["durum"] == "gecerli"
    return s["plan"]


def test_g10_dis_buyutme_kose_verandayi_buyutmez():
    p = _kose_verandali()
    ver = next(m for m in p["mahaller"] if m["islev"] == "veranda")
    vr = ver["dikdortgenler"][0]
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    for m in p["mahaller"]:
        if m["islev"] == "veranda":
            continue
        r = max(m["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
        for yon, k, kenar, ust in (("D", 0, r[2], W), ("K", 1, r[3], H), ("B", 0, r[0], 0), ("G", 1, r[1], 0)):
            if kenar != (ust if yon in ("D", "K") else 0):
                continue
            q, neden = PI._oda_kenari(p, m["ad"], yon, 50)
            if q is None:
                continue
            v2 = next(x for x in q["mahaller"] if x["islev"] == "veranda")["dikdortgenler"][0]
            assert (v2[2] - v2[0], v2[3] - v2[1]) == (vr[2] - vr[0], vr[3] - vr[1]), (m["ad"], yon)


def test_g10_elli_cm_varsayimi_yazilir():
    p = PU.uret({"alan_m2": 80, "oda_programi": "2+1"}, ayar={"acik": False})["plan"]
    salon = next(m for m in p["mahaller"] if m["islev"] == "salon")
    r = max(salon["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    yon = "D" if r[2] == W else "K" if r[3] == H else "B" if r[0] == 0 else "G"
    s = PI.duzenle(p, "salonu büyütelim", {"oda_programi": "2+1"},
                   hazir={"islemler": [{"op": "oda_buyut", "mahal": salon["ad"], "yon": yon, "alinti": "salonu büyütelim"}], "uygulanamayan": []})
    assert s["durum"] == "gecerli" and "ölçü söylenmediği için 50 cm alındı" in s["fark"], s


# ── G11 · dönüşümde notlar ─────────────────────────────────────────────────────────────────────────────────────────────
def test_g11_ayna_ve_devrik_notlari_cevirir():
    c = {"duzlemler": [{"ad": "güney", "plan": [[0, 0], [10, 0], [10, 5]], "yukari": [0, 1], "sacak": {"y": 0}, "not": "cumbanın güney alnı"}],
         "kalkanlar": [{"ad": "güney kalkanı", "eksen": "y", "konum": 0, "aralik": [0, 10], "ic": "kuzey", "ust": ["güney"], "not": "güney alnı"}]}
    y = cati_ortak.ayna_y(c, 5)
    assert y["duzlemler"][0]["not"] == "cumbanın kuzey alnı" and y["kalkanlar"][0]["not"] == "kuzey alnı"
    d = cati_ortak.devrik(c)
    assert d["duzlemler"][0]["not"] == "cumbanın batı alnı" and d["kalkanlar"][0]["not"] == "batı alnı"
