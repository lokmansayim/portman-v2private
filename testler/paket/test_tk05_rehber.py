"""TK-05 r07'nin montaj rehberi açılır (9 Kasım 2026; İş Emri `testler/motor/veri/TK05_r07.json`, dış duvar 160 / iç 100, D-12, D-60).

Hata: rehber sayfası açılmıyordu; sahnenin parça listesi (`cardRows`) adı boş bir parçada durdu ("Cannot read properties of null (reading
'localeCompare')") ve 3B sahne kurulmadı. Kök neden: D-60 listeye 160'lık dış duvarın profillerini koydu ("3'lü H 160 × 160 × 100 (dış
duvar T'si)"), kimlik kartı kitabı koymadı (H-04/05/08/09 100'lük dış duvarın); kart modeli iki dış duvar T'sini "kural yok" bırakır.
Rehberin verisi (`rehber/veri.py`) kartsız dış H'ı iç H yoluna soktu: kartı ve adı boş, yazısı "iç duvar T'si".

Düzeltme verinin kaynağında: kartsız dış duvar T'si dış H kalır (dübelli; makasa denkliği kartsız okunmaz), adı ve "Liste" satırı
yükleme listesinden (D-28 madde 1; kartsız panonun adı gibi). Kartı ve adı olmayan pano, H ya da köşe direği üretimde durur
(`Desteklenmiyor`): bayiye açılmayan sayfa gitmez. Sıralama değişmedi. 100'lük dış duvarlı evlerin rehberi değişmez (`test_rehber.py`,
`test_paket.py`).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

IE = KOK / "testler" / "motor" / "veri" / "TK05_r07.json"
UCLU = "3'lü H 160 × 160 × 100 (dış duvar T'si)"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tk05(tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(IE)
    kart = tmp_path_factory.mktemp("tk05_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, "TK05")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, "TK05", L, "TK-05")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    yield {"d": d, "ie": ie, "kart": kart, "L": L, "say": _oku(kart / "TK05_kart_sayim.json")}
    G.lento_ayarla({})


def test_kok_neden_kart_modelinde_kartsiz(tk05):
    """İki dış duvar T'sinin kartı yok (160'lık üçlü H'ın kimlik kartı yok); listede satırı var."""
    ky = {x["parca"] for x in tk05["say"]["kural_yok"]}
    gor = {g["parca"]: g["asil"] for g in tk05["say"]["gorunum"]}
    assert sorted(gor) == ["H_UCLU_DIS_001", "H_UCLU_DIS_010"] and set(gor.values()) <= ky
    assert sum(s["adet"] or 0 for s in tk05["L"] if s["kalem"] == UCLU) == 2


def test_her_parca_kartli_ya_da_adli(tk05):
    d = tk05["d"]
    assert [x for x in d["panels"] + d["hs"] + d["posts"] if not (x.get("card") or x.get("ad"))] == []


def test_dis_duvar_tsi_dis_h(tk05):
    """Kartsız dış duvar T'si: dış H (dübelli), adı ve satırı listeden; "iç duvar T'si" değil."""
    kartsiz = [h for h in tk05["d"]["hs"] if not h["card"]]
    assert len(kartsiz) == 2
    for h in kartsiz:
        assert h["tur"] == "uclu_dubelli" and h["t"] == 16 and h["ad"] == UCLU
        assert h["liste"] == f"{UCLU} L 2800 · 2 adet"
    assert not [h for h in tk05["d"]["hs"] if h["t"] == 16 and h["tur"].startswith(("standart", "uclu_standart"))]


def test_listede_satiri_yoksa_uretim_durur(tk05):
    """Ad boş kalmaz: listede satır yoksa sayfa üretilmez (sessizce adsız parça yazılmaz)."""
    from araclar.paket.rehber import veri
    L = [s for s in tk05["L"] if s["kalem"] != UCLU]
    with pytest.raises(veri.Desteklenmiyor, match="kartsız dış duvar T'si"):
        veri.kur(copy.deepcopy(tk05["ie"]), tk05["kart"], "TK05", L, "TK-05")


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber izi: {iz.hazir()}")
def test_sayfa_acilir(tk05, tmp_path):
    """Sayfa hatasız açılır; 2. adımda (yatak odası) iki dış duvar T'si listedeki adıyla."""
    from araclar.paket.rehber import sayfa
    html = sayfa.yaz(tk05["d"], tmp_path / "TK-05.html")
    z = iz.al(html, tmp_path / "iz.json")
    assert z["hatalar"] == []
    t = [p for p in z["parts"] if UCLU in json.dumps(p, ensure_ascii=False)]
    assert len(t) == 2
