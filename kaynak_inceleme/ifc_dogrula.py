"""Kaydedilmiş kaynak inceleme IFC'sini yeniden açıp BAĞLAYICI kapılarla denetler.

Codex devrindeki verify_saved.py ve verify_ifc.py rapora alan ekliyor, başarısızlıkta durmuyordu. Burada her kapı
geçti/kaldı verir; biri kalırsa sonuç kalır ve komut 1 ile çıkar.

Kapılar:
  sema       IfcOpenShell şema doğrulaması: sorun 0
  nesne      Beklenen GUID kümesi (kaynak SHA256 / anahtar / düğüm) ile dosyadaki proxy'ler aynı: kayıp, fazla, çift yok
  koordinat  Saklanan köşeler ile girdiden yeniden hesaplanan köşeler arasındaki en büyük fark ≤ eşik (varsayılan 1 µm)
  topoloji   Saklanan üçgen bağlantıları (çoklu küme) girdidekiyle aynı
  ozellik    Portman_Kaynak: Model, Revizyon, KaynakSHA256 girdiyle; çatı seçeneğinde Secenek ve ParcaDurumu tutarlı
  geometri   Geometri motoru her nesneyi kurar; dünya sınır kutusu farkı ≤ eşik (--geometri-atla ile atlanabilir)

Eşikler aktarım bütünlüğü içindir; üretim toleransı değildir. Geçmek kaynak plana (JPG/DWG) uygunluk ya da üretim kabulü
anlamına gelmez.

Kullanım:
    python -m kaynak_inceleme.ifc_dogrula --ifc <dosya.ifc> --secili <selected.json> [--cati B] [--rapor r.json]
    python -m kaynak_inceleme.ifc_dogrula ... --karsilastir <öteki.ifc>   # tarih damgaları dışında aynı mı
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.validate
import numpy as np

from .geometri import dosya_sha256, dugum_guid, dunya_koseleri, secili_oku
from .ifc_yaz import Tanim, cati_tanimi, model_tanimi

ESIK_M = 1e-6


def dogrula(ifc_yolu: Path, secili: dict, tanim: Tanim, *, kip: str = "blender32", esik_m: float = ESIK_M,
            geometri: bool = True) -> dict:
    f = ifcopenshell.open(str(ifc_yolu))
    sha = secili["source_sha256"]
    kapilar: dict[str, dict] = {}

    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log)
    kapilar["sema"] = {"gecti": not log.statements, "sorun": len(log.statements),
                       "ornek": [str(s)[:200] for s in log.statements[:5]]}

    beklenen = {dugum_guid(sha, tanim.kimlik_anahtari, n["id"]): n for n in secili["nodes"]}
    proxy = f.by_type("IfcBuildingElementProxy")
    guidler = [p.GlobalId for p in proxy]
    eksik = [beklenen[g]["id"] for g in beklenen if g not in set(guidler)]
    fazla = sorted(set(guidler) - set(beklenen))
    cift = len(guidler) - len(set(guidler))
    kapilar["nesne"] = {"gecti": not eksik and not fazla and not cift, "beklenen": len(beklenen), "bulunan": len(proxy),
                        "eksik_dugum": eksik[:20], "fazla": len(fazla), "cift": cift}

    en_buyuk, uz_uyusmaz, topo_uyusmaz, saklanan_ucgen, kaynak_ucgen = 0.0, [], [], 0, 0
    oz_hata: list[str] = []
    beklenen_kutu = {}
    guid_nesne = {p.GlobalId: p for p in proxy}
    for g, n in beklenen.items():
        mesh = secili["meshes"][n["geometry"]]
        kaynak_ucgen += len(mesh["triangles"])
        ob = guid_nesne.get(g)
        if ob is None:
            continue
        ogeler = ob.Representation.Representations[0].Items
        saklanan = np.array(ogeler[0].Coordinates.CoordList, dtype=np.float64)
        hesap = dunya_koseleri(n["world_transform"], mesh["vertices"], kip)
        beklenen_kutu[g] = (hesap.min(axis=0), hesap.max(axis=0)) if len(hesap) else None
        if saklanan.shape != hesap.shape or len({o.Coordinates.id() for o in ogeler}) != 1:
            uz_uyusmaz.append(n["id"])
        else:
            en_buyuk = max(en_buyuk, float(np.abs(saklanan - hesap).max()) if len(hesap) else 0.0)
        istenen = collections.Counter(tuple(i + 1 for i in tri) for tri in mesh["triangles"])
        bulunan = collections.Counter(tuple(tri) for o in ogeler for tri in o.CoordIndex)
        saklanan_ucgen += sum(bulunan.values())
        if istenen != bulunan:
            topo_uyusmaz.append(n["id"])
        ps = ifcopenshell.util.element.get_psets(ob).get("Portman_Kaynak", {})
        bek = {"Model": tanim.model, "Revizyon": secili["revision"], "KaynakSHA256": sha}
        if tanim.secenek:
            bek["Secenek"] = tanim.secenek
            bek["ParcaDurumu"] = "Yeni tasarım önerisi" if n.get("proposal") else "Kaynak SKP geometrisi"
        for k, v in bek.items():
            if ps.get(k) != v:
                oz_hata.append(f"{n['id']}:{k}")
    kapilar["koordinat"] = {"gecti": not uz_uyusmaz and en_buyuk <= esik_m, "en_buyuk_fark_m": en_buyuk,
                            "esik_m": esik_m, "kip": kip, "uyusmayan_dugum": uz_uyusmaz[:20]}
    kapilar["topoloji"] = {"gecti": not topo_uyusmaz and saklanan_ucgen == kaynak_ucgen, "saklanan_ucgen": saklanan_ucgen,
                           "kaynak_ucgen": kaynak_ucgen, "uyusmayan_dugum": topo_uyusmaz[:20]}
    kapilar["ozellik"] = {"gecti": not oz_hata, "hata": oz_hata[:20]}

    if geometri:
        ayar = ifcopenshell.geom.settings()
        ayar.set(ayar.USE_WORLD_COORDS, True)
        hatalar, kutu_fark, motor_ucgen = [], 0.0, 0
        for ob in proxy:
            try:
                sekil = ifcopenshell.geom.create_shape(ayar, ob)
                vs = np.array(sekil.geometry.verts, dtype=np.float64).reshape(-1, 3)
                motor_ucgen += len(sekil.geometry.faces) // 3
                bk = beklenen_kutu.get(ob.GlobalId)
                if bk is not None and len(vs):
                    kutu_fark = max(kutu_fark, float(np.abs(vs.min(axis=0) - bk[0]).max()),
                                    float(np.abs(vs.max(axis=0) - bk[1]).max()))
            except Exception as exc:  # geometri motoru hatası kapıyı düşürür
                hatalar.append({"guid": ob.GlobalId, "hata": str(exc)[:200]})
        kapilar["geometri"] = {"gecti": not hatalar and kutu_fark <= esik_m, "hata": hatalar[:10],
                               "sinir_kutusu_farki_m": kutu_fark, "motor_ucgen": motor_ucgen,
                               "not": "Motorun yeniden üçgenlemesi kaynak üçgen sayısından farklı olabilir; sayı kapı değildir."}

    return {"ifc": str(ifc_yolu), "ifc_sha256": dosya_sha256(ifc_yolu), "model": tanim.model,
            "revizyon": secili["revision"], "secenek": tanim.secenek, "kaynak_sha256": sha,
            "gecti": all(k["gecti"] for k in kapilar.values()), "kapilar": kapilar,
            "kapsam": "Aktarım bütünlüğü. Kaynak plana uygunluk, BIM/BOM ya da üretim kabulü değildir."}


_ZAMAN = re.compile(r"^(#\d+=IFCOWNERHISTORY\(.*,)(\d+)\);$")


def _govde(yol: Path) -> tuple[list[str], dict[str, str]]:
    satirlar = Path(yol).read_text(encoding="utf-8", errors="strict").splitlines()
    bas = {s.split("(")[0]: s for s in satirlar if s.startswith(("FILE_DESCRIPTION", "FILE_NAME", "FILE_SCHEMA"))}
    i, j = satirlar.index("DATA;"), len(satirlar) - 1 - satirlar[::-1].index("ENDSEC;")
    veri = [_ZAMAN.sub(r"\1<ZAMAN>);", s) for s in satirlar[i + 1:j]]
    return veri, bas


def karsilastir(a: Path, b: Path) -> dict:
    """İki IFC'yi IfcOwnerHistory.CreationDate ve FILE_NAME (tarih, üretici sürümü) dışında satır satır karşılaştırır."""
    va, ba = _govde(a)
    vb, bb = _govde(b)
    farkli = [k for k, (x, y) in enumerate(zip(va, vb)) if x != y]
    return {"ayni": va == vb and ba.get("FILE_DESCRIPTION") == bb.get("FILE_DESCRIPTION")
            and ba.get("FILE_SCHEMA") == bb.get("FILE_SCHEMA"),
            "veri_satiri": [len(va), len(vb)], "farkli_satir": len(farkli) + abs(len(va) - len(vb)),
            "ilk_farklar": [(va[k][:120], vb[k][:120]) for k in farkli[:3]],
            "baslik_ayni": {k: ba.get(k) == bb.get(k) for k in ("FILE_DESCRIPTION", "FILE_SCHEMA", "FILE_NAME")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ifc", required=True, type=Path)
    ap.add_argument("--secili", required=True, type=Path)
    ap.add_argument("--cati", help="P9401 çatı seçeneği harfi (A–D)")
    ap.add_argument("--kip", default="blender32", choices=["blender32", "float64"])
    ap.add_argument("--esik", type=float, default=ESIK_M)
    ap.add_argument("--geometri-atla", action="store_true")
    ap.add_argument("--karsilastir", type=Path, help="tarih damgaları dışında aynı olması beklenen öteki IFC")
    ap.add_argument("--rapor", type=Path)
    a = ap.parse_args(argv)
    secili = secili_oku(a.secili)
    tanim = cati_tanimi(secili, a.cati) if a.cati else model_tanimi(secili)
    rapor = dogrula(a.ifc, secili, tanim, kip=a.kip, esik_m=a.esik, geometri=not a.geometri_atla)
    if a.karsilastir:
        rapor["karsilastirma"] = karsilastir(a.ifc, a.karsilastir)
        rapor["gecti"] = rapor["gecti"] and rapor["karsilastirma"]["ayni"]
    if a.rapor:
        a.rapor.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"gecti": rapor["gecti"], **{k: v["gecti"] for k, v in rapor["kapilar"].items()}}, ensure_ascii=False))
    return 0 if rapor["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
