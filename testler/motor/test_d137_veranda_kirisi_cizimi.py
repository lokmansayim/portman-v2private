"""D-137 (Lokman, 20 Kasım 2026 08:04:02 UTC, kart "Eskizdeki gibi, iki evde"; BK-63; PC-49): yükleme listesinde kiriş alan açık kenar ön
onay çiziminde de veranda profilidir (kiriş), gövdenin dış çizgisinde olmasa da.

Soru: "Listede olan veranda kirişi ön onay çizimine de girsin mi?" Eskiz PF `Tavan_Kirisi/2026-11-20_veranda_cizim/
veranda_kirisi_cizim_once_sonra.png`: 80 m² 3+1'in (PA21, kör AP25) 60 cm'lik sol yanı (listede L 500) ve 91 m² 3+1'in (PA17, kör AP18)
502 cm'lik önü (listede L 4920) bugün listede var, çizimde yok. Liste ve çizim aynı kenarı aynı koddan okur
(`prefabrik_liste.kirisli_acik_kenarlar`, D-28 madde 1). Yalnız profil: D-58'in aks ve dış parça ölçüsü ekleri `girinti_kirisi` anahtarıyla
kalır (`test_d58.test_girinti_kenarinda_profil`).
"""
from __future__ import annotations

import copy
import io
import contextlib
import json
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path

import ezdxf
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from motor import dxf_out, geometry as G, prefabrik_liste as PL  # noqa: E402
from test_d107_tavan_kirisi import _prefabrik_girdiler  # noqa: E402

BEKLENEN = json.loads((KOK / "testler" / "motor" / "veri" / "D137_veranda_kirisi_cizimi_beklenen.json").read_text(encoding="utf-8"))

# Gövdenin dış çizgisinde olmayan profiller: D-58 (`girinti_kirisi` anahtarı) ve D-137 (listede kirişi olan kenar). Depodaki bütün
# prefabrik İş Emri'leri (`_tum_girdiler`) tarandı (20 Kasım 2026); başka evde iç kenar profili yok.
IC_PROFILLER = {
    "is_emri/adaylar/PA04.json": [("D-58", (386.5, 37.5, 888.5, 37.5))],
    "testler/motor/veri/TK04_r07.json": [("D-58", (386.5, 37.5, 888.5, 37.5))],
    "testler/motor/veri/TK04_r08.json": [("D-58", (386.5, 37.5, 888.5, 37.5))],
    "is_emri/adaylar/PA17.json": [("D-137", (386.5, 225.0, 888.5, 225.0))],
    "testler/kor/projeler/AP18/is_emri.json": [("D-137", (386.5, 225.0, 888.5, 225.0))],
    "testler/motor/veri/BK64_PA17_kirma.json": [("D-137", (386.5, 225.0, 888.5, 225.0))],   # BK-64: aynı ev, kenar yöntemli kırma
    "is_emri/adaylar/PA21.json": [("D-137", (386.5, 0.0, 386.5, 60.0))],
    "testler/kor/projeler/AP25/is_emri.json": [("D-137", (386.5, 0.0, 386.5, 60.0))],
}


def _tum_girdiler() -> list[Path]:
    """`_prefabrik_girdiler()` ve depodaki öteki prefabrik İş Emri'leri (havuz kaynakları, Motor test verisi, teklif, yarım pano, görsel,
    paket girdisi, denemeler); aynı dosya bir kez."""
    yollar = list(_prefabrik_girdiler())
    for kalip in ("testler/havuz/is_emirleri/*.json", "testler/motor/veri/*.json", "testler/teklif/**/*.json", "testler/yarim_pano/**/*.json",
                  "testler/gorsel/veri/**/*.json", "araclar/paket/girdi/**/*.json", "deneme/**/*.json"):
        yollar += sorted(KOK.glob(kalip))
    out, gor = [], set()
    for y in yollar:
        if y in gor:
            continue
        gor.add(y)
        try:
            ie = json.loads(y.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(ie, dict) and isinstance(ie.get("yapi"), dict) and ie["yapi"].get("sistem", "prefabrik") == "prefabrik" and "mahaller" in ie:
            out.append(y)
    return out


def _uret(ie: dict):
    with tempfile.TemporaryDirectory() as td:
        with contextlib.redirect_stdout(io.StringIO()):
            m = dxf_out.uret(copy.deepcopy(ie), Path(td))
        assert m["validation_passed"], m
        return ezdxf.readfile(Path(td) / m["dxf"])


def _oku(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def test_karar_dayanagi():
    karar = (KOK / "KARARLAR" / "D-137.md").read_text(encoding="utf-8")
    assert "08:04:02" in karar and "Eskizdeki gibi, iki evde" in karar and "Listede olan veranda kirişi ön onay çizimine de girsin mi?" in karar
    assert "08:04:02" in BEKLENEN["aciklama"]


@pytest.mark.parametrize("kod", ["PA21", "PA17"])
def test_iki_evde_profil(kod):
    """Hedef örnek (eskizin taslağıyla piksel piksel aynı çıktı): yeni profil ana planda, ikinci kopyada ve saha montaj planında; dış yüz
    kenarda, iç çizgi 10 cm verandanın içinde, iki uçta 10 cm kısa (öteki profiller gibi). Öteki bütün katmanlar aynı sayıda."""
    b = BEKLENEN["evler"][kod]
    doc = _uret(_oku(b["is_emri"]))
    msp = doc.modelspace()
    assert dict(sorted(Counter(e.dxf.layer for e in msp).items())) == b["sonra_katmanlar"]
    assert sum(b["katman_farki"].values()) == b["sonra_toplam"] - b["once_toplam"] == 3
    eklenen = []
    for e in msp.query("INSERT"):
        if e.dxf.name.endswith("_GIRINTI"):
            cizgiler = sorted([[round(l.dxf.start.x, 2), round(l.dxf.start.y, 2), round(l.dxf.end.x, 2), round(l.dxf.end.y, 2)]
                               for l in doc.blocks[e.dxf.name].query("LINE")])
            eklenen.append({"blok": e.dxf.name, "katman": e.dxf.layer, "nokta": [round(e.dxf.insert.x, 2), round(e.dxf.insert.y, 2)],
                            "cizgiler": cizgiler})
    assert eklenen == b["eklenen"]


def test_listede_olmayan_kenar_cizilmez():
    """Aynı biçimli iki evde (82 m² 2+1, M-07'nin AP-22'si; kör AP-12) verandanın kısa yanı listede kirişsiz (açık kenar mahalin dışına
    taşar; gerçek AP-22 listesinde de yok): çizim aynen, iç kenar profili yok."""
    for yol in ("testler/cizim/evler/AP22.json", "testler/kor/projeler/AP12/is_emri.json"):
        doc = _uret(_oku(yol))
        assert not [e for e in doc.modelspace().query("INSERT") if e.dxf.name.endswith("_GIRINTI")], yol


def test_tarama_butun_is_emirleri():
    """Depodaki bütün prefabrik İş Emri'lerinde gövdenin dış çizgisinde olmayan profiller `IC_PROFILLER` kadar. Kenar seçimi çizimin kendi
    işlevleriyle (`Cizici._girinti_acik_kenari`, `_kirisli_acik_kenarlar`, `_listede_kirisli`); döngü `ciz_plan`'ın veranda profili
    bölümünün kopyası, DXF üretilmez (iki evin DXF'i `test_iki_evde_profil`'de)."""
    bulunan = {}
    girdiler = _tum_girdiler()
    assert len(girdiler) >= 190, len(girdiler)
    for y in girdiler:
        ie = json.loads(y.read_text(encoding="utf-8"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                plan = G.kur(copy.deepcopy(ie))
        except Exception:                                   # kurulamayan İş Emri çizilmez (öteki testlerin işi)
            continue
        W, H = plan.W, plan.H
        dis = {v["ad"] for v in plan.dis_verandalar}
        gk = {x.get("ad") for x in ie.get("mahaller", []) if x.get("girinti_kirisi")}
        c = types.SimpleNamespace(plan=plan, _acik_ag=None)
        for ad, m in plan.mahaller.items():
            if not m.acik or ad in dis:
                continue
            kirisli = dxf_out.Cizici._kirisli_acik_kenarlar(c, m)
            ring = list(m.poly.simplify(0.0).exterior.coords)
            for (ax, ay), (bx, by) in zip(ring, ring[1:]):
                if (abs(ax - bx) < 1e-9 and (abs(ax) < 1e-9 or abs(ax - W) < 1e-9)) or (abs(ay - by) < 1e-9 and (abs(ay) < 1e-9 or abs(ay - H) < 1e-9)):
                    continue
                seg = tuple(round(v, 2) for v in (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)))
                if ad in gk and plan.girintili and dxf_out.Cizici._girinti_acik_kenari(c, ax, ay, bx, by):
                    bulunan.setdefault(str(y.relative_to(KOK)), []).append(("D-58", seg))
                elif dxf_out.Cizici._listede_kirisli(kirisli, ax, ay, bx, by):
                    bulunan.setdefault(str(y.relative_to(KOK)), []).append(("D-137", seg))
    assert bulunan == IC_PROFILLER


def test_liste_ve_cizim_ayni_kenar():
    """80 m² 3+1: çizimin profil çizdiği 60 cm'lik kenar listenin L 500'ünü veren kenardır (aynı işlev; D-28 madde 1)."""
    ie = _oku("is_emri/adaylar/PA21.json")
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    v = plan.mahaller["VERANDA"]
    kenarlar = [tuple(round(c, 2) for c in k[:4]) for k in PL.kirisli_acik_kenarlar(plan, v)]
    assert (386.5, 20.0, 386.5, 5.0) in kenarlar and (386.5, 65.0, 386.5, 20.0) not in kenarlar   # mahalin dışına taşan parça sayılmaz
    with contextlib.redirect_stdout(io.StringIO()):
        assert (60.0, 1, False) in PL.acik_mahal_kirisleri(plan, v)
    c = types.SimpleNamespace(plan=plan)
    assert dxf_out.Cizici._listede_kirisli(dxf_out.Cizici._kirisli_acik_kenarlar(c, v), 386.5, 60.0, 386.5, 0.0)


def test_dikmesiz_planda_kiris_yok():
    """Liste dikmesiz planda açık mahale kiriş saymaz (`model_motor`); çizim de o mahalin iç kenarına profil koymaz."""
    ie = _oku("is_emri/adaylar/PA21.json")
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    c = types.SimpleNamespace(plan=types.SimpleNamespace(dikmeler=[], acik_kenarlar=plan.acik_kenarlar))
    assert dxf_out.Cizici._kirisli_acik_kenarlar(c, plan.mahaller["VERANDA"]) == []
    assert not dxf_out.Cizici._listede_kirisli([], 386.5, 60.0, 386.5, 0.0)
