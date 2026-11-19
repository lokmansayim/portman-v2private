"""İE-42 · çatı cevabı: havuz + LLM okur, kod karar verir (Lokman, 17 Kasım 2026: kart 04:57:27 "LLM okusun, kod karar versin",
04:58:54 "50 tur koştuğun veriyi havuza al", plan kartı 05:09:29 "Onaylıyorum"). LLM çağrısı yok: LLM'in okuması alan olarak verilir."""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beyin import cati_cevabi as CC  # noqa: E402
from beyin import karar as K  # noqa: E402
from beyin.sema import Talep  # noqa: E402
import test_prefabrik_cati_seti as TP  # noqa: E402
from test_celik_revizyon_karar import Sohbet, onayla as c_onayla  # noqa: E402


def _cc(durum, secilen=None, ek=False) -> dict:
    return {"cati_cevabi": {"durum": durum, "secilen": secilen, "ek_istek": ek}}


def _sinif(s, k) -> str:
    d = s.k.d
    ie = d.get("son_is_emri") or {}
    y = ie.get("yapi") or {}
    kod = y.get("kod") if y.get("sistem") == "celik" else (ie.get("talep") or {}).get("kaynak")
    if k.gerekce == K.PLAN_ONAYI:
        return f"ONAY:r{k.revizyon}"
    if k.eylem == "sor" and (k.mesaj or "").startswith("Hangi çatı olsun?"):
        return "SORU"
    if k.eylem == "is_emri":
        return f"R{k.revizyon}:{kod}"
    st = d.get("secenek_seti") or {}
    if st.get("durum") == "acik" and st.get("tur") == "cati_varyanti" and d.get("cati_adimi"):
        return f"ACIK:{k.eylem}"
    return f"{k.eylem}:{(k.gerekce or '')[:40]}"


@pytest.fixture(scope="module")
def pref(tmp_path_factory):
    s, k = TP._cati_seti(tmp_path_factory.mktemp("pref"))
    assert k.eylem == "secenek", k.mesaj
    return s


@pytest.fixture(scope="module")
def celik(tmp_path_factory):
    s = Sohbet(tmp_path_factory.mktemp("celik"))
    k = s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "is_emri", k.mesaj
    k = c_onayla(s)
    assert k.eylem == "secenek", k.mesaj
    return s


def _yaz(s0, metin, **alan):
    s = copy.deepcopy(s0)
    return s, _sinif(s, s.yaz(metin, **alan))


# --- havuz ve bağlam ---

def test_havuz_olcum_seti_ornege_gitmez():
    ornek, olcum = CC.havuz()
    assert len(ornek) > 7000 and 250 <= len(olcum) <= 400
    olcum_metin = {x["m"] for x in olcum}
    assert not any(x["m"] in olcum_metin for _, x in ornek)
    for x in olcum[:50]:
        assert all(o["m"] not in olcum_metin for o in CC.benzerler(x["m"]))


def test_havuz_okumalari_gecerli():
    for _, x in CC.havuz()[0]:
        assert x["durum"] in ("secti", "kararsiz", "secim_yok")
        assert (x["durum"] == "secti") == (x.get("secilen") in (1, 2, 3))


def test_benzerler_cesitli_ve_on():
    b = CC.benzerler("2 olsun, o da güzel")
    assert len(b) == CC.ORNEK_SAYISI
    assert len({x["m"] for x in b}) == len(b)
    assert all(x["m"] != "2 olsun, o da güzel" for x in b)                 # aynı metin örnek olmaz


def test_baglam_yalniz_acik_cati_setinde(pref, tmp_path):
    s, _ = TP._plan(tmp_path)
    assert CC.baglam(s.k, "2 olsun") == ""                                 # set yok
    b = CC.baglam(pref.k, "2 olsun, o da güzel")
    assert b.startswith("çatı seti açık: bayiye şu çatılar soruldu: 1. PA-06")
    assert "2. PA-06-K (Kırma)" in b and "3. PA-06-C" in b and "benzer örnekler" in b
    assert CC.baglam(pref.k, "   ") == ""


def test_okuma_numarayi_koda_cevirir(pref):
    st = pref.k.d["secenek_seti"]
    assert CC.okuma(None, st) is None
    assert CC.okuma({"durum": "secti", "secilen": 2}, st)["kod"] == "PA06K"
    assert CC.okuma({"durum": "secti", "secilen": 7}, st)["durum"] == "kararsiz"     # listede yok: sorulur
    assert CC.okuma({"durum": "secti", "secilen": None}, st)["durum"] == "kararsiz"
    assert CC.okuma({"durum": "secim_yok"}, st)["kod"] is None


def test_sema_alani_istege_bagli():
    t = Talep(niyet="onay", guven="yuksek", ozet="x")
    assert t.cati_cevabi is None
    t = Talep(niyet="onay", guven="yuksek", ozet="x", **_cc("secti", 2))
    assert t.cati_cevabi.secilen == 2


# --- kodun kararı ---

@pytest.mark.parametrize("niyet", [None, "revizyon", "diger", "soru", "onay"])
def test_prefabrik_karar(pref, niyet):
    ny = {"niyet": niyet} if niyet else {}
    assert _yaz(pref, "1 olsun", **ny, **_cc("secti", 1))[1] == "ONAY:r1"
    assert _yaz(pref, "Kırma olsun", **ny, **_cc("secti", 2))[1] == "R2:PA06K"
    assert _yaz(pref, "cumbalı olsun", **ny, **_cc("secti", 3))[1] == "R2:PA06C"
    assert _yaz(pref, "2 olsun, o da güzel", **ny, **_cc("kararsiz"))[1] == "SORU"
    # LLM "2" okudu ama mesajda başka set kodu yazılı: sorulur (K21)
    assert _yaz(pref, "PA-06-C olsun", **ny, **_cc("secti", 2))[1] == "SORU"


def test_prefabrik_llm_okumasi_kurali_yener(pref):
    # kural yolunun kararsız saydığı söz: LLM açık seçim okursa çizilir; kural yolunda sorulur
    m = "2 olsun, kaporayı yarın yatıracağız, o da tamam"
    assert _yaz(pref, m, **_cc("secti", 2))[1] == "R2:PA06K"
    assert _yaz(pref, "1 olsun, yarın onaylarız", **_cc("kararsiz"))[1] == "SORU"


def test_prefabrik_secim_yok(pref):
    assert _yaz(pref, "Teşekkürler", niyet="onay", **_cc("secim_yok"))[1] == "SORU"    # onay sözü, çatı yok
    assert _yaz(pref, "Nakliye ne kadar?", niyet="soru", **_cc("secim_yok"))[1].startswith("ACIK:")


def test_prefabrik_ek_istek_sessiz_dusmez(pref):
    # evin çatısı + LLM'in okuduğu pencere isteği: onay kaydedilmez (istek sessiz düşmez)
    s, c = _yaz(pref, "1 olsun, yatak odası 2 penceresi 120x180 olsun",
                pencereler=[{"mahal": "yatak odası 2", "olcu": "120x180", "islem": "degistir"}], **_cc("secti", 1))
    assert c != "ONAY:r1"


def test_celik_karar(celik):
    assert _yaz(celik, "K olsun", **_cc("secti", 2))[1] == "R2:Ç8801K"
    assert _yaz(celik, "katalogdaki olsun", **_cc("secti", 1))[1] == "ONAY:r1"
    assert _yaz(celik, "K mı L mi bilemedik", **_cc("kararsiz"))[1] == "SORU"


def test_alan_yoksa_kural_yolu(pref):
    # LLM alanı yoksa (LLM hatası, eski kayıt) bugünkü kural yolu
    assert _yaz(pref, "2 olsun")[1] == "R2:PA06K"
    assert _yaz(pref, "1 mi 2 mi bilemedik")[1] == "SORU"


def test_havuz_kahini(pref, celik):
    """LLM havuzdaki okumayı yazsaydı kod hakemin beklediğini verir (rastgele 80 satır, sabit tohum; "başka müşteri" ve iptal sözü kural
    yolunda kalır, onlar atlanır)."""
    sat = [x for _, x in CC.havuz()[0] if "müşteri" not in x["m"].lower() and "iptal" not in x["m"].lower()]
    random.Random(42).shuffle(sat)
    kotu = []
    for x in sat[:80]:
        s0 = pref if x["yapi"] == "prefabrik" else celik
        c = _yaz(s0, x["m"], **_cc(x["durum"], x.get("secilen")))[1]
        if x["durum"] == "secti":
            ilk = s0.k.d["secenek_seti"]["adaylar"][x["secilen"] - 1]["kod"]
            ok = c == ("ONAY:r1" if x["secilen"] == 1 else f"R2:{ilk}")
        else:
            ok = c == "SORU" or c.startswith(("ACIK:", "cevapla:", "sor:"))
        if not ok:
            kotu.append((x["m"], x["durum"], c))
    assert not kotu, kotu
