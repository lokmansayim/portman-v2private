"""İE-15 K6 · TK-04'ün çatısı kart modelinde ve montaj rehberinde (D-53; İş Emri r04 `testler/motor/veri/TK04_r04.json`).

Beşik + çıkıntısız çapraz cumba (AP-06 gibi, D-47): ana çatının mahyası x yönünde, cumba önde 0–386,5. Çatı çatı tanımından
(`motor/cati_capraz.py`; liste üreteci, çizim ve bugünkü IFC aynı tanımı okur). Kart modelinde çatı kartları "kural yok" değil, listeyle
aynı: yerleşen adetle sayılanlar (makaslar, tek kat panel, iniş) adet adet, boyla alınanlar kesim stoğuyla. Saçak omegası (M-01, D-41;
D-53 ile beşik + cumbada da) saçak duvarının üstünde duvar boyunca, listedeki gibi 6. Rehber 62 m² şablonunun cumbasıyla: ana çatının 8
makası, cumbanın baş makası ve ana çatının üstündeki yavru makası (MA-05), derelerde kırpılan yüzler, ters mahya adımı, iki boy kaplama;
mahya x yönünde olduğu için asma tavanın omegaları x boyunca, H'ları dik. Beşik evlerin rehberi değişmez (`test_rehber.py`, `test_paket.py`).
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
IE = KOK / "testler" / "motor" / "veri" / "TK04_r04.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tk04(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(IE)
    kart = tmp_path_factory.mktemp("tk04_k6")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return {"d": veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04"), "say": _oku(kart / "TK04_kart_sayim.json"), "L": L, "ie": ie}


def _liste(L: list[dict], ad: str) -> int:
    """Listedeki satırın adedi (`veri.kiyas` gibi: ad aynen ya da ardından " ·" / " (" ile; "Metal dere" inişi saymaz)."""
    return sum(s["adet"] or 0 for s in L if s["kalem"] == ad or s["kalem"].startswith((ad + " ·", ad + " (")))


def test_cati_capraz_cumba(tk04):
    c = tk04["ie"]["cati"]
    assert c["tip"] == "besik_cumba" and c["makas_ekseni"] == "y" and c["cumbalar"] == [{"cephe": "on", "bas_cm": 0, "bit_cm": 386.5, "cikinti_cm": 0}]


def test_kart_modeli_listeyle_ayni(tk04):
    say, L = tk04["say"], tk04["L"]
    assert say["cati_tipi"] == "besik_cumba" and say["kural_yok"] == [] and say["sema_hatasi"] == {"bugunku_ifc": 0, "kart_modeli": 0}
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    yerlesen = {"MA-01": "Makas (baş)", "MA-02": "Makas (orta)", "MA-05": "Yavru makas · cumba", "KP-02": "Tek kat çatı paneli",
                "BT-01": "Baş makas betopanı", "DR-02": "Metal dere inişi aparatı"}
    assert {k: adet[k] for k in yerlesen} == {k: _liste(L, on) for k, on in yerlesen.items()} == {
        "MA-01": 2, "MA-02": 6, "MA-05": 2, "KP-02": 25, "BT-01": 9, "DR-02": 5}
    stok = {k: say["kesim_plani"][k]["stok"] for k in ("AS-01", "DR-01", "CK-01", "CK-02", "CK-03", "CK-04", "CK-06")}
    boyla = {"AS-01": "Aşık", "DR-01": "Metal dere", "CK-01": "100'lük saçak omegası", "CK-02": "Saçak sacı", "CK-03": "Alın sacı",
             "CK-04": "Baş makas Z'si", "CK-06": "Metal kiremit mahyası"}
    assert stok == {k: _liste(L, on) for k, on in boyla.items()} == {"AS-01": 43, "DR-01": 4, "CK-01": 6, "CK-02": 7, "CK-03": 11, "CK-04": 10,
                                                                      "CK-06": 5}
    assert adet["MA-03"] == adet["MA-04"] == 0                             # taşan verandanın ve paralel cumbanın makası yok


def test_sacak_omegasi_duvar_boyunca(tk04):
    """M-01 (D-41, D-53): saçak omegası saçak duvarının üstünde, duvar boyunca; saçağa uzamaz. TK-04'te saçak duvarları ana çatının önü
    (cumbanın sağı, veranda kirişi dahil) ve arkası; cumbanın saçağı yok (yüzleri derelerle ana çatıya iner)."""
    d = tk04["d"]
    W, DY = d["dis"]
    om = sorted((o["perp"], o["a0"], o["a1"]) for o in d["omega_duvar"] if o["tur"] == "sacak")
    assert om == [(5, 416.5, W), (DY - 5, 0, W)]
    assert sorted(o["yer"] for o in d["omega_duvar"] if o["tur"] == "bas") == [
        "sağ duvar ve veranda kirişi (MKS08 altı)", "sol duvar (MKS01 altı)", "ön duvar ve veranda kirişi, cumbanın altı (MKS09 altı)"]


def test_rehber_adimlari(tk04):
    d = tk04["d"]
    ad = [a.get("ad") for a in d["adimlar"]]
    assert d["N"] == 21 and len(d["panels"]) == 50
    i = ad.index("Dere ve inişler")
    assert ad[i + 1:i + 3] == ["Ters mahya", "Tek kat panel ve mahya"] and d["S"]["tersmahya"] == i + 1
    assert "Ana çatı ve cumba makasları" in ad and d["cati_adim"] == list(range(d["S"]["makas"], d["S"]["alin"] + 1))
    tm = d["adimlar"][i + 1]
    assert [r[1:3] for r in tm["rows"]] == [["Ters mahya (dere içi) L 2800", "3 adet"], ["Ters mahya kenar kutusu L 21 × 40 × 21 × 2800", "6 adet"]]
    assert d["kabuk"]["spec"][3].startswith("beşik + çapraz cumba %33")


def test_makaslar(tk04):
    """Ana çatı 8 makas (MA-01/MA-02, y boyunca), cumbanın baş makası dış uçtaki kalkan duvarının üstünde ve ana çatının üstündeki yavru
    makas (ikisi de MA-05, x boyunca); yavru makas sayısı kart modeliyle ve listedeki "Yavru makas · cumba" ile aynı."""
    d, say, L = tk04["d"], tk04["say"], tk04["L"]
    m = d["makas"]
    assert Counter((x["aile"], x["R"], x["yon"]) for x in m) == {("ana", "AN", "y"): 8, ("cumba", "CU", "x"): 1, ("ara", "CU", "x"): 1}
    assert all("kod" not in x for x in m if x["aile"] == "ana") and all(x["kod"] == "MA-05" for x in m if x["aile"] != "ana")
    n05 = next(k["adet"] for k in say["kartlar"] if k["kod"] == "MA-05")
    assert sum(x["aile"] != "ana" for x in m) == n05 == _liste(L, "Yavru makas · cumba")
    ana = sorted(x["konum"] for x in m if x["aile"] == "ana")
    assert ana[0] == 3.7 and ana[-1] == round(d["dis"][0] - 3.7, 2) and all(abs(b - a - 125.5) < 0.01 for a, b in zip(ana[1:-1], ana[2:-1]))
    ara = next(x for x in m if x["aile"] == "ara")
    assert ara["zR"] == "AN" and ara["dereler_arasi"][0] < ara["bas"] < ara["son"] < ara["dereler_arasi"][1]
    assert d["cards"]["MA-05"]["ad"] == "Yavru makas (çapraz cumba)"


def test_yuzler_dere_ve_kaplama(tk04):
    d, L = tk04["d"], tk04["L"]
    Y = d["yuz"]
    assert set(Y) == {"MFL", "MFR", "MB", "CL", "CR"} and {k for k, y in Y.items() if "dere" in y} == {"MFL", "MFR", "CL", "CR"}
    assert [h["ad"] for h in d["dere"]["hatlar"]] == ["ana çatı ön (cumbanın sağı)", "ana çatı arka"]
    assert len(d["dere"]["inisler"]) == next(k["adet"] for k in tk04["say"]["kartlar"] if k["kod"] == "DR-02")
    assert sorted(k["ad"] for k in d["kalkan"]) == ["ana çatı sağ kalkanı (MKS08)", "ana çatı sol kalkanı (MKS01)", "cumba kalkanı (MKS09)"]
    assert {k: y["serit"]["ad"] for k, y in Y.items()} == {"MFL": "L 5100 (ana çatı)", "MFR": "L 5100 (ana çatı)", "MB": "L 5100 (ana çatı)",
                                                          "CL": "L 2410 (cumba)", "CR": "L 2410 (cumba)"}
    assert _liste(L, "Tek kat çatı paneli · ana çatı") == 20 and _liste(L, "Tek kat çatı paneli · cumba") == 5


def test_asiklar_kart_modelinden(tk04):
    """Aşık sıraları ve parçaları kart modelinden; ana çatının cumbalı yüzü derelerin birleştiği yerden ikiye bölünür, bölme çizgisini geçen
    parça iki yüzde de gerçek boyuyla (410) yazılır: rehberdeki parçalar, bölünen parçalar bir sayılınca, kart modelinin aşıklarıyla aynı."""
    d, say = tk04["d"], tk04["say"]
    A = d["asik"]["yuzler"]
    bolunen = sum(1 for p in A["MFL"]["pafta"] if p == [410.0])
    assert bolunen == 5 and all(p[-1] == 410.0 for p in A["MFR"]["pafta"][-bolunen:])
    assert sum(len(p) for a in A.values() for p in a["pafta"]) - bolunen == say["kesim_plani"]["AS-01"]["parca"] == 61


def test_asma_tavan_mahyaya_paralel(tk04):
    """Mahya x yönünde: oda içi tavan omegaları x boyunca, tavan H'ları onlara dik (y boyunca); gözler odaların içinde."""
    d = tk04["d"]
    assert d["tavan"]["tip"] == "asma" and {o["yon"] for o in d["omega"] if o["oda"] != "veranda"} == {"x"}
    assert d["tavan"]["h"] and {h["o"] for h in d["tavan"]["h"]} == {"v"}
    assert d["tavan"]["acik"] == [{"ad": "Veranda", "yon": "x", "rects": [[386.5, 10, 878.5, 193.25]]}]
