"""D-130 · BK-60 · Verandada her açık kenar kendi kirişini alır: aynı yöndeki ikinci yan kenar da (U veranda).

Lokman, karar kartı 19 Kasım 2026 21:43:35 UTC: "Her açık kenara kiriş" (soru: "Verandanın ikinci yan kirişini listeye ekleyelim mi?").
Liste bugün verandada her yönde yalnız bir yan kiriş sayıyordu (`prefabrik_liste.model_motor`, yanlar bloğu). Yeni yol: yönde birden çok
açık kenar varsa her kenar ayrı kiriş, boyu mahalin o çizgideki kenarından; yönde tek kenar bugünkü yoldan aynen (mahalin dış ölçüsü).
Hedef örnek `veri/D130_veranda_yan_kirisi_beklenen.json` (76 m² teklif evi, 80 m² 3+1 havuz evi). Çizim değişmez: 76 m²'de üç yan kiriş
çizimde zaten var; 80 m² 3+1'in 60 cm'lik sol yan kenarı (girintiye bakan iç kenar, `girinti_kirisi` yazılı değil) çizimde bugün de
kirişsiz. Lokman kartı 19 Kasım 2026 22:16:13 "Listede kalsın, çizim sonra": liste L 500'ü sayar, çizim ayrı adımda eskizle.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Polygon, box as kutu

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
    assert "D-130" in PL.SURUM.split("1.21, ")[1].split(";")[1]   # 1.22 (D-133) üstüne geldi; 1.21 geçmişte


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
    aynı İş Emri) ve disk arşivinin 110 ve 120 m²'sinde (PA-49, PA-50; D-134, İE-43 PR-8: ana çatının örttüğü ön verandanın iki yanı).
    Öteki evlerin kenar listesi aynı kalır (yönde tek kenar bugünkü yol)."""
    bulunan = []
    for y in _prefabrik_girdiler() + [KOK / "testler" / "motor" / "veri" / "D127_veranda_76m2.json"]:
        try:
            if _ayni_yonde_iki_kenar(_oku(str(y.relative_to(KOK)))):
                bulunan.append(str(y.relative_to(KOK)))
        except G.IsEmriHatasi:
            continue
    assert sorted(set(bulunan)) == BEKLENEN["tarama"]


KILIT = KOK / "testler" / "motor" / "veri" / "D130_kenar_kilidi.json"


def _kenar_tablosu() -> dict:
    """Depodaki bütün prefabrik İş Emri'lerinde dikmeli her açık mahalin (taşan veranda hariç) kirişleri, `acik_mahal_kirisleri`'nden:
    {İş Emri: {mahal: [[dış ölçü, uçtaki kolon], ...]}}. Giriş nişi de tabloda (liste nişi bu fonksiyona sormaz; tablo yalnız kodu sabitler)."""
    tablo = {}
    for y in _prefabrik_girdiler() + [KOK / "testler" / "motor" / "veri" / "D127_veranda_76m2.json"]:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                plan = G.kur(copy.deepcopy(_oku(str(y.relative_to(KOK)))))
        except G.IsEmriHatasi:
            continue
        if not plan.dikmeler:
            continue
        dis = {v.get("ad") for v in plan.dis_verandalar or []}
        d = {}
        for ad, m in plan.mahaller.items():
            if not m.acik or m.poly is None or ad in dis:
                continue
            try:
                d[ad] = [[round(b, 2), u] + (["ara"] if a else []) for b, u, a in PL.acik_mahal_kirisleri(plan, m)]
            except PL.ListeYazilmaz as e:
                d[ad] = f"ListeYazilmaz: {e}"
        if d:
            tablo[str(y.relative_to(KOK))] = d
    return tablo


def test_kenar_kilidi():
    """Öteki evler aynen (BK-60 A3): kenar tablosu kilitle aynı. Kilit D-130'un kodundan yazıldı (124 İş Emri). `main`'le (50aad0bc)
    farkı yalnız 76 m² (+188,25), 80 m² 3+1 (PA21 ve kör AP25, +60) ve 160/100 denemesi (+251; `deneme/` tarama dışında) (geometri
    hakemi, 19 Kasım 2026: 180 İş Emri'nin yükleme listesi `main`'le kıyaslandı). Kilit bilinçli yazılır:
    `python testler/motor/test_d130_veranda_yan_kirisi.py --kilit`, gerekçesi iş emrine. İE-43 PR-8 (D-134): havuza giren 110 ve 120 m²
    (PA-49, PA-50) eklendi, 126 İş Emri; var olan 124'ü aynen."""
    assert _kenar_tablosu() == json.loads(KILIT.read_text(encoding="utf-8"))


def test_l_verandanin_ic_kosesi():
    """Bulgu A (hakem): iç köşedeki açık kenarın çizgisi mahalin ön kenarını da keser; o iz kiriş sayılmaz, kiriş yalnız açık kenarın
    parçası (125,5)."""
    poly = Polygon([(0, 0), (800, 0), (800, 188.25), (256, 188.25), (256, 313.75), (0, 313.75)])
    assert PL.yan_kenar_araliklari(poly, "y", 256.0, [(188.25, 313.75)]) == [(188.25, 313.75)]


def test_ayni_cizgide_iki_acik_kenar_sorulur():
    """Bulgu B: aynı çizgide arası kapalı iki açık kenar; kirişlerin ucu mahalin çizgisinden okunmaz, liste yazılmaz (K21). Aradaki
    boşluğu kolon örtüyorsa (ara kolon) kenar tek parça sayılır."""
    poly = kutu(0, 0, 800, 300)
    with pytest.raises(PL.ListeYazilmaz, match="kapalı aralık"):
        PL.yan_kenar_araliklari(poly, "x", 300.0, [(0, 200), (600, 800)], "VERANDA")
    assert PL.yan_kenar_araliklari(poly, "x", 300.0, [(0, 395), (405, 800)], "VERANDA", [(395, 295, 405, 305)]) == [(0, 800)]


def test_kenar_cizgisi_bir_santim_icinde():
    """Bulgu C: açık kenarın çizgisi mahalin kenarından 0,8 cm uzakta; kiriş o kenarın boyu (mahalin dış ölçüsüne düşmez)."""
    poly = Polygon([(0, 0), (800, 0), (800, 188.25), (600, 188.25), (600, 313.75), (0, 313.75)])
    assert PL.yan_kenar_araliklari(poly, "y", 800.8, [(0, 188.25)]) == [(0, 188.25)]


def test_kenar_bulunamazsa_sorulur():
    """Açık kenarla örtüşen parça yoksa kiriş boyu uydurulmaz (K21)."""
    with pytest.raises(PL.ListeYazilmaz, match="bulunamadı"):
        PL.yan_kenar_araliklari(kutu(0, 0, 800, 300), "y", 500.0, [(0, 300)], "VERANDA")


def test_bir_santimden_yakin_iki_cizgi_tek_kenar():
    """Bulgu D: aynı yan kenarın iki parçası 0,01 cm kayık; tek kenar (çift kiriş yok)."""
    plan = SimpleNamespace(acik_kenarlar=[(0, 0, 800, 0), (800, 0, 800, 100), (800.01, 100, 800.01, 200), (0, 200, 0, 0)], dikmeler=[])
    v = SimpleNamespace(poly=kutu(0, 0, 800, 200), ad="VERANDA")
    assert PL.acik_mahal_kirisleri(plan, v) == [(800, 0, False), (200, 0, False), (200, 0, False)]


if __name__ == "__main__" and "--kilit" in sys.argv:
    KILIT.write_text(json.dumps(_kenar_tablosu(), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("yazıldı:", KILIT.relative_to(KOK))
