"""D-130 · BK-60 · Verandada her açık kenar kendi kirişini alır: aynı yöndeki ikinci yan kenar da (U veranda).

Lokman, karar kartı 19 Kasım 2026 21:43:35 UTC: "Her açık kenara kiriş" (soru: "Verandanın ikinci yan kirişini listeye ekleyelim mi?").
Liste bugün verandada her yönde yalnız bir yan kiriş sayıyordu (`prefabrik_liste.model_motor`, yanlar bloğu). Yeni yol: yönde birden çok
açık kenar varsa her kenar ayrı kiriş, boyu mahalin o çizgideki kenarından; yönde tek kenar bugünkü yoldan aynen (mahalin dış ölçüsü).
Hedef örnek `veri/D130_veranda_yan_kirisi_beklenen.json` (76 m² teklif evi, 80 m² 3+1 havuz evi). Çizim değişmez.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path

from shapely.geometry import LineString

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from motor import geometry as G, prefabrik_liste as PL  # noqa: E402
from test_d107_tavan_kirisi import _prefabrik_girdiler  # noqa: E402

BEKLENEN = json.loads((KOK / "testler" / "motor" / "veri" / "D130_veranda_yan_kirisi_beklenen.json").read_text(encoding="utf-8"))
ALAN = ("grup", "kalem", "olcu", "adet")


def _oku(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _model(ie: dict) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        return PL.model_motor(copy.deepcopy(ie))


def test_kart_dayanagi():
    """Hedef örnek Lokman'ın kartına dayanır (kelimesi kelimesine)."""
    assert "\"Her açık kenara kiriş\"" in BEKLENEN["kaynak"] and "21:43:35" in BEKLENEN["kaynak"]
    assert "D-130" in PL.SURUM.split(";")[1] and PL.SURUM.startswith("1.20 ")


def test_yan_kirisler_ve_liste_satiri():
    """76 m²: sağ yan L 1782,5; 80 m² 3+1: sol yan L 500. Listeye yalnız bu satır eklenir; öteki satırlar aynen (önceki kenar listesiyle
    kurulan liste)."""
    for ad, b in BEKLENEN["evler"].items():
        N = _model(_oku(b["is_emri"]))
        uc = N.get("veranda_kenar_uc_kolonlari") or [1] * len(N["veranda_kenarlari_cm"])
        assert (N["veranda_kenarlari_cm"], uc) == (b["sonra"]["veranda_kenarlari_cm"], b["sonra"]["uc_kolon"]), ad
        sonra = PL.liste(N, PL.kurallari_oku())
        N0 = dict(N, veranda_kenarlari_cm=b["once"]["veranda_kenarlari_cm"])
        N0.pop("veranda_kenar_uc_kolonlari", None)
        if any(n > 1 for n in b["once"]["uc_kolon"]):
            N0["veranda_kenar_uc_kolonlari"] = b["once"]["uc_kolon"]
        once = PL.liste(N0, PL.kurallari_oku())
        yeni = [s for s in sonra["satirlar"] if s not in once["satirlar"]]
        assert [{a: s[a] for a in ALAN} for s in yeni] == b["yeni_satirlar"], ad
        assert all(s["formul"] == "açık kenar dış ölçüsü − 100" and s["dayanak"] == "Liste kuralı" for s in yeni), ad
        assert [s for s in sonra["satirlar"] if s not in yeni] == once["satirlar"], ad


def _ayni_yonde_iki_kenar(ie: dict) -> bool:
    """Planda dikmeli bir açık mahalin aynı yönde iki ayrı açık kenarı var mı (taşan veranda ve dikmesiz niş hariç; liste üreteci gibi)."""
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    if not plan.dikmeler:
        return False
    dis = {v.get("ad") for v in plan.dis_verandalar or []}
    for v in plan.mahaller.values():
        if v.poly is None or not v.acik or v.ad in dis:
            continue
        yon: dict = {}
        for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
            if v.poly.buffer(1.0).contains(LineString([(x0, y0), (x1, y1)])):
                e = "x" if abs(y1 - y0) < 1e-6 else "y"
                yon.setdefault(e, set()).add(round(y0 if e == "x" else x0, 2))
        if any(len(c) > 1 for c in yon.values()):
            return True
    return False


def test_tarama_butun_is_emirleri():
    """Depodaki bütün prefabrik İş Emri'leri: aynı yönde ikinci açık kenarı olan veranda yalnız 76 m² ve 80 m² 3+1'de (kör ölçümün AP-25'i
    aynı İş Emri). Öteki evlerin kenar listesi aynı kalır (yönde tek kenar bugünkü yol)."""
    bulunan = []
    for y in _prefabrik_girdiler() + [KOK / "testler" / "motor" / "veri" / "D127_veranda_76m2.json"]:
        try:
            if _ayni_yonde_iki_kenar(_oku(str(y.relative_to(KOK)))):
                bulunan.append(str(y.relative_to(KOK)))
        except G.IsEmriHatasi:
            continue
    assert sorted(set(bulunan)) == BEKLENEN["tarama"]
