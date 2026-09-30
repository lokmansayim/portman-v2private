"""Kaydedilmiş Blender inceleme dosyalarını (Codex devri) yeniden açıp BAĞLAYICI kapılarla denetler.

bpy ile koşar (Blender 5.2 dosyaları için bpy 5.2.x; Python 3.13). Codex'teki verify_world.py, check_saved_blend.py ve
render_variants.py'nin gövde denetiminin yerine geçer; sonuç geçti/kaldı verir, kalırsa çıkış 1.

Model dosyası (<kod>_inceleme.blend):
  koleksiyon   SKP_KAYNAK, CATI_AC_KAPAT, KAYNAK_DIGER_KOPYALAR_GIZLI var
  secim        SKP_KAYNAK ∪ CATI_AC_KAPAT'taki skp_node kümesi = selected.json düğümleri; kayıp, fazla, çift yok
  cati         CATI_AC_KAPAT'taki düğümler = selected.json'daki çatı düğümleri
  dunya        her nesnenin dünya köşeleri scene.json'dan hesaplanan köşelerle ≤ eşik (Blender float32 saklar; eşik 10 µm)
  matris       dönüşüm köşelere uygulanmış: matrix_world birim (Codex'in shear düzeltmesi korunmuş mu)
Çatı seçeneği dosyası (P9401_Cati_<harf>.blend) ayrıca:
  cati_gorunum CATI_AC_KAPAT yalnız A'da görünür
  oneri        CATI_ONERISI_<harf> nesneleri = seçenek verisindeki öneri parçaları (kimlik, köşeler ≤ 1 µm), işaretleri doğru
  revizyon     sahnedeki revizyon = seçenek revizyonu
Eşikler aktarım bütünlüğü içindir; üretim toleransı değildir. Sunum malzemeleri ve görseller denetlenmez.

Kullanım:
    <bpy python> -m kaynak_inceleme.blender_dogrula --veri <devir klasörü> --cikti <klasör>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np

from .geometri import dosya_sha256, dunya_koseleri, secili_oku

ESIK_DUNYA_M = 1e-5
ESIK_ONERI_M = 1e-6
MODELLER = ["P9201", "P9401", "P9501"]
CATILAR = ["A", "B", "C", "D"]


def _ac(yol: Path) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(yol), load_ui=False)


def _dunya(o) -> np.ndarray:
    co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    mw = np.array(o.matrix_world, dtype=np.float64)
    return co @ mw[:3, :3].T + mw[:3, 3]


def _govde_ve_secim(sahne: dict, secili_dugum: set[int], cati_dugum: set[int]) -> tuple[dict, list[str]]:
    hatalar: list[str] = []
    k = {ad: bpy.data.collections.get(ad) for ad in ("SKP_KAYNAK", "CATI_AC_KAPAT", "KAYNAK_DIGER_KOPYALAR_GIZLI")}
    eksik_kol = [ad for ad, c in k.items() if c is None]
    if eksik_kol:
        hatalar.append(f"koleksiyon eksik: {eksik_kol}")
        return {"eksik_koleksiyon": eksik_kol}, hatalar
    obler = [o for ad in ("SKP_KAYNAK", "CATI_AC_KAPAT") for o in k[ad].objects if "skp_node" in o]
    dugumler = [int(o["skp_node"]) for o in obler]
    cift = len(dugumler) - len(set(dugumler))
    eksik, fazla = sorted(secili_dugum - set(dugumler)), sorted(set(dugumler) - secili_dugum)
    cati_bulunan = {int(o["skp_node"]) for o in k["CATI_AC_KAPAT"].objects if "skp_node" in o}
    if cift or eksik or fazla:
        hatalar.append(f"seçim: eksik {eksik[:10]} fazla {fazla[:10]} çift {cift}")
    if cati_bulunan != cati_dugum:
        hatalar.append(f"çatı koleksiyonu {sorted(cati_bulunan)} ≠ {sorted(cati_dugum)}")
    en_buyuk, sayi_hata, matris_hata, kose = 0.0, [], [], 0
    for o in obler:
        n = sahne["nodes"][int(o["skp_node"])]
        g = sahne["meshes"][n["geometry"]]
        if len(o.data.vertices) != len(g["vertices"]):
            sayi_hata.append(n["id"])
            continue
        if not np.allclose(np.array(o.matrix_world), np.eye(4), atol=1e-9):
            matris_hata.append(n["id"])
        if g["vertices"]:
            fark = np.abs(_dunya(o) - dunya_koseleri(n["world_transform"], g["vertices"], "float64")).max()
            en_buyuk = max(en_buyuk, float(fark))
            kose += len(g["vertices"])
    if sayi_hata:
        hatalar.append(f"köşe sayısı farklı: {sayi_hata[:10]}")
    if matris_hata:
        hatalar.append(f"matrix_world birim değil: {matris_hata[:10]}")
    if en_buyuk > ESIK_DUNYA_M:
        hatalar.append(f"dünya köşe farkı {en_buyuk} m > {ESIK_DUNYA_M}")
    return {"nesne": len(obler), "beklenen": len(secili_dugum), "cati_nesnesi": len(cati_bulunan),
            "arsivdeki_nesne": sum(1 for o in k["KAYNAK_DIGER_KOPYALAR_GIZLI"].objects if "skp_node" in o),
            "denetlenen_kose": kose, "en_buyuk_dunya_farki_m": en_buyuk, "esik_m": ESIK_DUNYA_M}, hatalar


def model_blend(blend: Path, sahne: dict, secili: dict) -> dict:
    _ac(blend)
    ozet, hatalar = _govde_ve_secim(sahne, {n["id"] for n in secili["nodes"]}, {n["id"] for n in secili["nodes"] if n["roof"]})
    return {"blend": blend.name, "blend_sha256": dosya_sha256(blend), "blender": bpy.app.version_string,
            "gecti": not hatalar, "hatalar": hatalar, **ozet}


def cati_blend(blend: Path, sahne: dict, kaynak: dict, secenek: dict, harf: str) -> dict:
    _ac(blend)
    govde = {n["id"] for n in kaynak["nodes"] if not n["roof"]}
    cati = {n["id"] for n in kaynak["nodes"] if n["roof"]}
    ozet, hatalar = _govde_ve_secim(sahne, govde | cati, cati)
    kc = bpy.data.collections.get("CATI_AC_KAPAT")
    if kc is not None and kc.hide_render != (harf != "A"):
        hatalar.append(f"kaynak çatı görünürlüğü yanlış (hide_render={kc.hide_render})")
    oneriler = {n["id"]: n for n in secenek["nodes"] if n.get("proposal")}
    oc = bpy.data.collections.get(f"CATI_ONERISI_{harf}")
    obler = list(oc.objects) if oc else []
    if oneriler and oc is None:
        hatalar.append(f"CATI_ONERISI_{harf} koleksiyonu yok")
    bulunan, oneri_fark = {}, 0.0
    for o in obler:
        pid = o.get("proposal_id")
        if not (o.get("proposal") and o.get("roof") and o.get("variant") == harf and o.get("revision") == secenek["revision"]):
            hatalar.append(f"öneri işareti eksik: {o.name}")
        if pid in bulunan or pid not in oneriler:
            hatalar.append(f"öneri kimliği tutarsız: {o.name} ({pid})")
            continue
        bulunan[pid] = o
        v = np.asarray(secenek["meshes"][oneriler[pid]["geometry"]]["vertices"], dtype=np.float64)
        d = _dunya(o)
        if d.shape != v.shape:
            hatalar.append(f"öneri köşe sayısı farklı: {o.name}")
            continue
        oneri_fark = max(oneri_fark, float(np.abs(d - v).max()))
    if set(bulunan) != set(oneriler):
        hatalar.append(f"öneri parçaları eksik/fazla: {sorted(set(oneriler) - set(bulunan))}")
    if oneri_fark > ESIK_ONERI_M:
        hatalar.append(f"öneri köşe farkı {oneri_fark} m > {ESIK_ONERI_M}")
    rev = bpy.context.scene.get("revision")
    if rev != secenek["revision"]:
        hatalar.append(f"sahne revizyonu {rev} ≠ {secenek['revision']}")
    return {"blend": blend.name, "blend_sha256": dosya_sha256(blend), "blender": bpy.app.version_string,
            "secenek": harf, "gecti": not hatalar, "hatalar": hatalar, "oneri_parcasi": len(bulunan),
            "en_buyuk_oneri_farki_m": oneri_fark, **ozet}


def calistir(veri: Path) -> dict:
    r: dict = {"blender": bpy.app.version_string, "modeller": {}, "catilar": {}}
    sahneler = {}
    for kod in MODELLER:
        sahneler[kod] = secili_oku(veri / "veri" / "skp" / kod / "scene.json")
        r["modeller"][kod] = model_blend(veri / "teslimler" / "Uc_Model_Sunum" / kod / f"{kod}_inceleme.blend", sahneler[kod],
                                         secili_oku(veri / "veri" / "skp" / kod / "selected.json"))
    kaynak = secili_oku(veri / "veri" / "skp" / "P9401" / "selected.json")
    for h in CATILAR:
        r["catilar"][h] = cati_blend(veri / "teslimler" / "P9401_Cati_Alternatifleri" / h / f"P9401_Cati_{h}.blend",
                                     sahneler["P9401"], kaynak, secili_oku(veri / "veri" / "p9401_cati" / f"{h}_selected.json"), h)
    r["gecti"] = all(v["gecti"] for v in [*r["modeller"].values(), *r["catilar"].values()])
    return r


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--veri", required=True, type=Path)
    ap.add_argument("--cikti", required=True, type=Path)
    a = ap.parse_args(argv)
    r = calistir(a.veri)
    a.cikti.mkdir(parents=True, exist_ok=True)
    (a.cikti / "blender_dogrulama.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    t = lambda b: "GEÇTİ" if b else "KALDI"  # noqa: E731
    print(f"Blender dosyaları · bpy {r['blender']} · SONUÇ: {t(r['gecti'])}")
    for kod, m in r["modeller"].items():
        print(f"  {kod}_inceleme.blend: {t(m['gecti'])} · nesne {m.get('nesne')}/{m.get('beklenen')} · çatı {m.get('cati_nesnesi')} · "
              f"dünya farkı {m.get('en_buyuk_dunya_farki_m', 0):.2e} m {m['hatalar'][:2]}")
    for h, c in r["catilar"].items():
        print(f"  P9401_Cati_{h}.blend: {t(c['gecti'])} · gövde+çatı nesnesi {c.get('nesne')} · öneri {c['oneri_parcasi']} · "
              f"dünya farkı {c.get('en_buyuk_dunya_farki_m', 0):.2e} m · öneri farkı {c['en_buyuk_oneri_farki_m']:.2e} m {c['hatalar'][:2]}")
    return 0 if r["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
