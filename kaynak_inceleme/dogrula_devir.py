"""Codex devrinin (30.09.2026) kaynak inceleme çıktılarını bağımsız olarak yeniden üretir ve denetler.

Veri klasörü Codex devir klasörünün düzenindedir (tamamı ya da aktarılan kısmı):
    veri/skp/<kod>/{selected.json, scene.json}
    veri/p9401_cati/<A–D>_selected.json
    teslimler/Uc_Model_Sunum/<kod>/<kod>_referans.ifc
    teslimler/P9401_Cati_Alternatifleri/<A–D>/P9401_Cati_<A–D>.ifc, Tasarim_Kaydi.json, secenekler.js
    DOSYA_MANIFESTI.json (varsa: bulunan her dosyanın SHA256'sı denetlenir)

Adımlar (her biri geçti/kaldı; biri kalırsa çıkış 1):
  1. paket      bulunan dosyalar manifestteki SHA256 ile aynı
  2. secim      her model için seçim, kalıcı kimlik kaydından (veri/secim_<kod>.json) sahneden yeniden kurulur = selected.json
  3. ifc_model  üç model IFC'si yeniden yazılır = kaydedilen IFC (tarih damgaları dışında); kaydedilen IFC bağlayıcı kapılardan geçer
  4. cati_veri  Codex'in create_variants.py'si (arşiv kopyası) geçici klasörde koşar = paketteki A–D verisi, secenekler.js, Tasarim_Kaydi.json
  5. cati_govde A–D'de kaynak gövde birebir, öneri parçaları etiketli
  6. ifc_cati   dört çatı IFC'si yeniden yazılır = kaydedilen; kaydedilen bağlayıcı kapılardan geçer; IFC'deki gövde koordinatları
                referans P9401 IFC'siyle aynı

Kullanım (depo kökünde):
    python -m kaynak_inceleme.dogrula_devir --veri <devir klasörü> --cikti <klasör> [--geometri-atla]
Ağ, LLM, canlı sunucu kullanılmaz; veri klasörüne yazılmaz; hiçbir dosya silinmez (yeniden üretilenler --cikti'da kalır).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import ifcopenshell
import numpy as np

from . import cati, secim
from .geometri import dosya_sha256, dugum_guid, secili_oku
from .ifc_dogrula import dogrula, karsilastir
from .ifc_yaz import cati_tanimi, ifc_yaz, model_tanimi

KOK = Path(__file__).resolve().parents[1]
MODELLER = ["P9201", "P9401", "P9501"]
CATILAR = ["A", "B", "C", "D"]
ARSIV = KOK / "deneme" / "2026-09-30_codex_devir" / "kod_arsivi"


def _paket(veri: Path) -> dict:
    m = veri / "DOSYA_MANIFESTI.json"
    if not m.exists():
        return {"gecti": True, "not": "manifest yok; atlandı"}
    satirlar = json.loads(m.read_text(encoding="utf-8"))
    ayni, farkli, yok = 0, [], 0
    for r in satirlar:
        f = veri / r["file"]
        if not f.is_file():
            yok += 1
            continue
        if dosya_sha256(f) == r["sha256"]:
            ayni += 1
        else:
            farkli.append(r["file"])
    return {"gecti": not farkli, "manifest_dosya": len(satirlar), "ayni": ayni, "farkli": farkli, "aktarilmamis": yok,
            "manifest_sha256": dosya_sha256(m)}


def _model(veri: Path, cikti: Path, kod: str, geometri: bool) -> dict:
    secili_yol = veri / "veri" / "skp" / kod / "selected.json"
    secili = secili_oku(secili_yol)
    sonuc: dict = {"model": kod, "selected_sha256": dosya_sha256(secili_yol), "kaynak_sha256": secili["source_sha256"]}
    sahne_yol = veri / "veri" / "skp" / kod / "scene.json"
    if sahne_yol.exists():
        kayit = secim.kayit_oku(KOK / "kaynak_inceleme" / "veri" / f"secim_{kod}.json")
        try:
            sonuc["secim"] = secim.karsilastir(secim.sec(secili_oku(sahne_yol), kayit), secili)
            sonuc["secim"]["gecti"] = sonuc["secim"]["ayni"]
        except secim.SecimHatasi as e:
            sonuc["secim"] = {"gecti": False, "hata": str(e)}
    else:
        sonuc["secim"] = {"gecti": False, "hata": "scene.json yok"}
    tanim = model_tanimi(secili)
    yeni = ifc_yaz(secili, cikti / "ifc" / kod, tanim, zaman=0)
    kayitli = veri / "teslimler" / "Uc_Model_Sunum" / kod / tanim.dosya_adi
    sonuc["yeniden_uretim"] = karsilastir(Path(yeni["ifc"]), kayitli)
    sonuc["yeniden_uretim"]["gecti"] = sonuc["yeniden_uretim"]["ayni"]
    d = dogrula(kayitli, secili, tanim, geometri=geometri)
    sonuc["kayitli_ifc"] = {"gecti": d["gecti"], "ifc_sha256": d["ifc_sha256"],
                            "kapilar": {k: {kk: vv for kk, vv in v.items() if kk not in ("ornek", "hata")} | {"gecti": v["gecti"]}
                                        for k, v in d["kapilar"].items()}}
    sonuc["gecti"] = all(sonuc[k]["gecti"] for k in ("secim", "yeniden_uretim", "kayitli_ifc"))
    return sonuc


def _cati_veri(veri: Path, cikti: Path) -> dict:
    """Arşivdeki create_variants.py'yi Codex'in beklediği düzende `cikti/cati_veri`'de koşar ve çıktıları paketle karşılaştırır."""
    betik = ARSIV / "p9401_cati" / "create_variants.py"
    t = cikti / "cati_veri"
    if t.exists():
        return {"gecti": False, "hata": f"{t} zaten var; boş bir çıktı klasörü verin (üzerine yazılmaz, silinmez)"}
    (t / "work" / "skp_import" / "P9401").mkdir(parents=True)
    (t / "work" / "p9401_cati").mkdir(parents=True)
    (t / "outputs" / "P9401_Cati_Alternatifleri").mkdir(parents=True)
    shutil.copy2(veri / "veri" / "skp" / "P9401" / "selected.json", t / "work" / "skp_import" / "P9401" / "selected.json")
    r = subprocess.run([sys.executable, str(betik)], cwd=t, capture_output=True, text=True)
    if r.returncode:
        return {"gecti": False, "hata": (r.stderr or r.stdout)[-500:]}
    karsi = {}
    for h in CATILAR:
        karsi[f"{h}_selected.json"] = dosya_sha256(t / "work" / "p9401_cati" / f"{h}_selected.json") == \
            dosya_sha256(veri / "veri" / "p9401_cati" / f"{h}_selected.json")
    for ad in ("secenekler.js", "Tasarim_Kaydi.json"):
        p = veri / "teslimler" / "P9401_Cati_Alternatifleri" / ad
        if p.exists():
            karsi[ad] = dosya_sha256(t / "outputs" / "P9401_Cati_Alternatifleri" / ad) == dosya_sha256(p)
    return {"gecti": all(karsi.values()), "bayt_bayt_ayni": karsi, "betik_sha256": dosya_sha256(betik)}


def _govde_ifc(referans_ifc: Path, secenek_ifc: Path, kaynak: dict, rev: str) -> dict:
    """Seçenek IFC'sindeki gövde nesnelerinin saklanan köşe ve üçgenleri referans P9401 IFC'siyle aynı mı."""
    a, b = ifcopenshell.open(str(referans_ifc)), ifcopenshell.open(str(secenek_ifc))
    sha, farkli, sayi = kaynak["source_sha256"], [], 0
    for n in kaynak["nodes"]:
        if n["roof"]:
            continue
        oa, ob = a.by_guid(dugum_guid(sha, kaynak["code"], n["id"])), b.by_guid(dugum_guid(sha, rev, n["id"]))
        ia, ib = oa.Representation.Representations[0].Items, ob.Representation.Representations[0].Items
        ca, cb = np.array(ia[0].Coordinates.CoordList), np.array(ib[0].Coordinates.CoordList)
        if ca.shape != cb.shape or not np.array_equal(ca, cb) or [i.CoordIndex for i in ia] != [i.CoordIndex for i in ib]:
            farkli.append(n["id"])
        sayi += 1
    return {"gecti": not farkli, "govde_nesnesi": sayi, "farkli": farkli[:20]}


def _cati(veri: Path, cikti: Path, harf: str, kaynak: dict, geometri: bool) -> dict:
    secili = secili_oku(veri / "veri" / "p9401_cati" / f"{harf}_selected.json")
    tanim = cati_tanimi(secili, harf)
    sonuc: dict = {"secenek": harf, "revizyon": secili["revision"], "govde": cati.govde_korunumu(kaynak, secili, harf)}
    yeni = ifc_yaz(secili, cikti / "ifc" / f"P9401_{harf}", tanim, zaman=0)
    kayitli = veri / "teslimler" / "P9401_Cati_Alternatifleri" / harf / tanim.dosya_adi
    sonuc["yeniden_uretim"] = karsilastir(Path(yeni["ifc"]), kayitli)
    sonuc["yeniden_uretim"]["gecti"] = sonuc["yeniden_uretim"]["ayni"]
    d = dogrula(kayitli, secili, tanim, geometri=geometri)
    sonuc["kayitli_ifc"] = {"gecti": d["gecti"], "ifc_sha256": d["ifc_sha256"],
                            "kapilar": {k: {kk: vv for kk, vv in v.items() if kk not in ("ornek", "hata")} | {"gecti": v["gecti"]}
                                        for k, v in d["kapilar"].items()}}
    sonuc["ifc_govde"] = _govde_ifc(veri / "teslimler" / "Uc_Model_Sunum" / "P9401" / "P9401_referans.ifc", kayitli, kaynak,
                                    secili["revision"])
    sonuc["gecti"] = all(sonuc[k]["gecti"] for k in ("govde", "yeniden_uretim", "kayitli_ifc", "ifc_govde"))
    return sonuc


def calistir(veri: Path, cikti: Path, geometri: bool = True) -> dict:
    cikti.mkdir(parents=True, exist_ok=True)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=KOK, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    r: dict = {"tarih": time.strftime("%Y-%m-%d %H:%M:%S"), "depo_commit": commit, "ifcopenshell": ifcopenshell.version,
               "adimlar": {}}
    r["adimlar"]["paket"] = _paket(veri)
    r["adimlar"]["modeller"] = {kod: _model(veri, cikti, kod, geometri) for kod in MODELLER}
    kaynak = secili_oku(veri / "veri" / "skp" / "P9401" / "selected.json")
    r["adimlar"]["cati_veri"] = _cati_veri(veri, cikti)
    r["adimlar"]["catilar"] = {h: _cati(veri, cikti, h, kaynak, geometri) for h in CATILAR}
    a = r["adimlar"]
    r["gecti"] = (a["paket"]["gecti"] and a["cati_veri"]["gecti"] and all(m["gecti"] for m in a["modeller"].values())
                  and all(c["gecti"] for c in a["catilar"].values()))
    return r


def ozet_metni(r: dict) -> str:
    a = r["adimlar"]
    t = lambda b: "GEÇTİ" if b else "KALDI"  # noqa: E731
    s = [f"Codex devri yeniden doğrulama · {r['tarih']} · commit {r['depo_commit'][:7]} · IfcOpenShell {r['ifcopenshell']}",
         f"SONUÇ: {t(r['gecti'])}", "",
         f"paket: {t(a['paket']['gecti'])} · manifestte {a['paket'].get('manifest_dosya')} · aktarılan ve aynı "
         f"{a['paket'].get('ayni')} · farklı {len(a['paket'].get('farkli', []))}", ""]
    for kod, m in a["modeller"].items():
        k = m["kayitli_ifc"]["kapilar"]
        s.append(f"{kod}: {t(m['gecti'])} · seçim yeniden kuruldu {t(m['secim']['gecti'])} "
                 f"({m['secim'].get('dugum', ['?'])[0]} düğüm) · IFC yeniden üretim {t(m['yeniden_uretim']['gecti'])} · "
                 f"kayıtlı IFC kapıları {t(m['kayitli_ifc']['gecti'])} (nesne {k['nesne']['bulunan']}, üçgen "
                 f"{k['topoloji']['saklanan_ucgen']}, koordinat farkı {k['koordinat']['en_buyuk_fark_m']} m)")
    s.append("")
    cv = a["cati_veri"]
    s.append(f"çatı verisi yeniden üretim: {t(cv['gecti'])} · {cv.get('bayt_bayt_ayni')}")
    for h, c in a["catilar"].items():
        s.append(f"P9401-CATI-{h}-01: {t(c['gecti'])} · gövde korunumu {t(c['govde']['gecti'])} "
                 f"({c['govde']['govde_dugumu']} düğüm; öneri parçası {c['govde']['oneri_parcasi']}) · IFC yeniden üretim "
                 f"{t(c['yeniden_uretim']['gecti'])} · kayıtlı IFC kapıları {t(c['kayitli_ifc']['gecti'])} · IFC gövde = "
                 f"referans {t(c['ifc_govde']['gecti'])}")
    s += ["", "Kapsam: aktarım bütünlüğü ve yeniden üretilebilirlik. Kaynak plana (JPG/DWG) uygunluk, BIM/BOM, Lokman seçimi "
          "ve üretim kabulü DEĞİLDİR."]
    return "\n".join(s) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--veri", required=True, type=Path)
    ap.add_argument("--cikti", required=True, type=Path)
    ap.add_argument("--geometri-atla", action="store_true")
    a = ap.parse_args(argv)
    r = calistir(a.veri, a.cikti, geometri=not a.geometri_atla)
    (a.cikti / "devir_dogrulama.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    metin = ozet_metni(r)
    (a.cikti / "devir_dogrulama.txt").write_text(metin, encoding="utf-8")
    print(metin)
    return 0 if r["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
