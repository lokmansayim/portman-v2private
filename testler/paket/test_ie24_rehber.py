"""İE-24 · TK-03 montaj rehberi (A4): girintili gövdenin rehberi 62 m² şablonundan, çatısı çizimdeki ve listedeki çatının aynısından
(`araclar/paket/rehber/girinti.py`: `cati_serit.tanim`, kart modelinin aşık ve inişleri). Ana çatının makasları "Çatı makası (baş/orta)"
kartıyla, cumbanınkiler "Cumba makası" (kartı henüz yok; Lokman, 30 Ekim 2026 13:49). Balkon gövdenin köşesinde, iki yanı açık:
köşesine Motor kolon koyar, kirişler kolonu gövdeye bağlar (Lokman, 31 Ekim 15:08: kirişler askıda kalmaz; D-38). Girintisiz evlerin rehberi değişmez (`test_paket.py`, `test_rehber.py`)."""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tk03(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(VERI / "TK03.json")
    kart = tmp_path_factory.mktemp("tk03_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, "TK03")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return veri.kur(copy.deepcopy(ie), kart, "TK03", L, "TK-03"), _oku(kart / "TK03_kart_sayim.json"), L


def test_adimlar(tk03):
    d, _, _ = tk03
    ad = [a.get("ad") for a in d["adimlar"]]
    assert d["N"] == 21 and len(d["panels"]) == 65
    assert "Balkon" in ad and "Ana çatı ve cumba makasları" in ad and "Giriş nişi" not in ad
    assert d["kabuk"]["spec"][0].startswith("girintili, dış ölçü 1236,7 × 873,3") and d["kabuk"]["spec"][5] == "köşede balkon"


def test_makaslar_paftadaki_yerde(tk03):
    """12 makas: ana çatıda 2 baş + 1 orta (MA-01/MA-02), sol cumbada 5, sağ cumbada 4 (kartsız, adı listeden). Yerleri paftanın makas
    planıyla aynı (baş makas duvarın 3,7 cm içinde, öteki makaslar eksende)."""
    d, _, L = tk03
    m = d["makas"]
    assert Counter((x["aile"], x["R"]) for x in m) == {("cumba", "C1"): 5, ("ana", "AN"): 3, ("cumba", "C2"): 4}
    assert all(x.get("kod") is None and x["kart_ad"] == "Cumba makası" for x in m if x["aile"] == "cumba")
    assert all("kod" not in x for x in m if x["aile"] == "ana") and sum(x["rol"] == "bas" for x in m if x["aile"] == "ana") == 2
    pafta = _oku(VERI / "TK03_pafta.json")["cati"]["makaslar_x"]
    x = sorted(y["konum"] for y in m)
    beklenen = sorted(v for k in ("sol cumba", "ana çatı", "sağ cumba") for v in pafta[k])
    assert len(x) == 12 and all(abs(a - b) < 1.5 for a, b in zip(x, beklenen)), (x, beklenen)
    satir = next(a for a in d["adimlar"] if a.get("ad") == "Ana çatı ve cumba makasları")["extra"]
    assert [r[1:3] for r in satir if r[3:] == ["liste"]] == [[s["kalem"] + " " + s["olcu"], f"{s['adet']} adet"] for s in L
                                                             if s["kalem"].startswith(("Makas (", "Cumba makası"))]


def test_kalkan_ve_yuzler(tk03):
    """Dört kalkan (iki cumbanın dış ucu, ana çatının iki ucu); ana çatının kalkanında cumbanın örttüğü uç kapalı. Dört yüz: önde ana çatı
    ve sağ cumba, arkada ana çatı ve sol cumba aynı düzlemde tek yüz (içbükey; kaplama yüzün kendisiyle kırpılır)."""
    d, _, _ = tk03
    k = {x["ad"].split(" (")[0]: x for x in d["kalkan"]}
    assert set(k) == {"sol cumba sol kalkanı", "ana çatı sol kalkanı", "ana çatı sağ kalkanı", "sağ cumba sağ kalkanı"}
    assert k["ana çatı sol kalkanı"]["ucKapali"] == {"B": True} and k["ana çatı sağ kalkanı"]["ucKapali"] == {"A": True}
    assert k["sol cumba sol kalkanı"].get("ucKapali") is None and k["sağ cumba sağ kalkanı"].get("ucKapali") is None
    y = {v["ad"]: v for v in d["yuz"].values()}
    assert set(y) == {"sol cumba ön yüzü", "sağ cumba arka yüzü", "ana çatı ve sağ cumba ön yüzü", "ana çatı ve sol cumba arka yüzü"}
    assert [a for a, v in y.items() if v.get("icbukey")] == ["ana çatı ve sağ cumba ön yüzü", "ana çatı ve sol cumba arka yüzü"]


def test_asik_dere_ve_inisler_kart_modeliyle_ayni(tk03):
    """Aşıklar kart modelinin aşıkları (yüz ve sıra): 71 parça, 207,14 m; dört dere hattı ve sekiz iniş (DR-02)."""
    d, say, _ = tk03
    kart = {k["kod"]: k for k in say["kartlar"]}
    Y = d["asik"]["yuzler"]
    assert set(Y) == {"Y1", "Y2", "Y3", "Y4"}
    parca = [x for v in Y.values() for p in v["pafta"] for x in p]
    assert len(parca) == kart["AS-01"]["adet"] == 71 and abs(sum(parca) / 100 - kart["AS-01"]["metre"]) < 0.01
    assert len(d["dere"]["hatlar"]) == 4 and len(d["dere"]["inisler"]) == kart["DR-02"]["adet"] == 8


def test_kose_balkonu(tk03):
    """Balkon köşede (313,75 × 193,25), iki açık kenarında birer kiriş, dış köşede kolon (D-38: kirişler askıda kalmaz). Kolonun ve kirişin
    kartı listedeki satırı okur: kiriş açık kenarın dış ölçüsü − 10 (kolonlu verandanın kuralı; L 3037,5 ve 1832,5, yarım milimetre
    listenin yazımıyla)."""
    d, _, _ = tk03
    v = d["verandalar"]
    assert len(v) == 1 and len(v[0]["kolon"]) == 1 and len(v[0]["kiris"]) == 2
    assert v[0]["kolon"][0]["rect"] == [0, 863.3, 10, 873.3] and v[0]["kolon"][0]["liste"] == "Özel kutu profil (kolon) 100 × 100 L 2500 · 1 adet"
    assert sorted(k["bu"].split(":")[0] for k in v[0]["kiris"]) == ["balkon · arka kiriş · L 303,75 cm", "balkon · sol yan kiriş · L 183,25 cm"]
    assert sorted(k["liste"] for k in v[0]["kiris"]) == ["Kutu profil (kiriş) 100 × 100 L 1832,5 · 1 adet", "Kutu profil (kiriş) 100 × 100 L 3037,5 · 1 adet"]
    p = next(a for a in d["adimlar"] if a.get("ad") == "Balkon")["p"]
    assert p.startswith("Balkon gövdenin köşesinde (313,75 × 193,25 cm), iki yanı açık") and "Dış köşeye 1 kolon" in p and "askıda kalmaz" in p
    yer = [o["yer"] for o in d["omega_duvar"]]
    assert yer.count("balkona bakan gövde duvarı") == 2 and any(y.endswith("ve balkon kirişi") for y in yer)
