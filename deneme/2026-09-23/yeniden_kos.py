"""23 Eylül denemelerini depodaki v1.1.1 üzerinde yeniden koşar ve sonuçları o günkü dosyalarla karşılaştırır.

Depo koduna dokunmaz: geçici bir klasöre v1.1.1 ağacını kopyalar, serbest aks yamasını orada uygular ve
23 Eylülde tek bir `cozumleyici` paketinde duran betikleri orada birleştirir (masaüstünde 10–13 klasörlerine
bölünmüş hâlleri doğrudan çalışmaz).

Kullanım (depo kökünde):
    python3 deneme/2026-09-23/yeniden_kos.py [--bpy <bpy kurulu python>] [--sakla <klasör>]

Gerekenler: Python 3.11, ezdxf==1.4.4, pymupdf, shapely, pydantic, numpy, pillow, ifcopenshell==0.8.5.
Blender adımı için bpy==5.0.1 kurulu bir Python (ayrı sanal ortam önerilir); verilmezse adım atlanır.
Ağ, LLM, WhatsApp ya da canlı sunucu kullanılmaz.
"""
from __future__ import annotations
import argparse, csv, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
PY = sys.executable
ZAMAN = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}( UTC)?")
ATLA = {"duration_s", "sure_s", "dxf_sha256", "pdf_sha256", "olusturma", "tarih", "zaman"}



def _yoksay(dizin, adlar):
    """Kökte yalnız v1.1.1 dışındaki klasörler atlanır; beyin/testler gibi alt klasörler kopyalanır."""
    if Path(dizin).resolve() == KOK:
        return [a for a in adlar if a in {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}]
    return [a for a in adlar if a in {"__pycache__", ".git"}]

def norm(x, basamak=3):
    if isinstance(x, dict):
        return {k: norm(v, basamak) for k, v in x.items() if k not in ATLA}
    if isinstance(x, list):
        return [norm(v, basamak) for v in x]
    if isinstance(x, float):
        return round(x, basamak)
    if isinstance(x, str):
        return ZAMAN.sub("<zaman>", x)
    return x


def json_ayni(a: Path, b: Path) -> bool:
    return norm(json.loads(a.read_text(encoding="utf-8"))) == norm(json.loads(b.read_text(encoding="utf-8")))


def csv_satirlar(p: Path, baslik=True):
    with open(p, newline="", encoding="utf-8") as h:
        r = list(csv.reader(h))
    return r if baslik else r[1:]


def kos(komut: list[str], cwd: Path, env_ek: dict | None = None) -> subprocess.CompletedProcess:
    import os
    env = {**os.environ, "PYTHONPATH": str(cwd), **(env_ek or {})}
    return subprocess.run(komut, cwd=cwd, env=env, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bpy", help="bpy==5.0.1 kurulu python yolu (Blender adımı için)")
    ap.add_argument("--sakla", help="geçici çalışma klasörünü bu yola kopyala")
    arg = ap.parse_args()
    sonuc: list[tuple[str, str]] = []

    def kaydet(ad, ok, ek="", etiket=("AYNI", "FARKLI")):
        sonuc.append((ad, (etiket[0] if ok else etiket[1]) + (f" · {ek}" if ek else "")))

    with tempfile.TemporaryDirectory() as t:
        W = Path(t) / "is"
        shutil.copytree(KOK, W, ignore=_yoksay)
        r = subprocess.run(["git", "apply", str(D / "10_Cozumleyici/kod/motor_serbest_aks.patch")], cwd=W, capture_output=True, text=True)
        if r.returncode:
            print("yama uygulanamadı:", r.stderr); return 2
        pk = W / "cozumleyici"; pk.mkdir()
        for kaynak in ["10_Cozumleyici/kod/cozumleyici", "11_Blender/kod", "13_Kiyas/kod"]:
            for f in (D / kaynak).glob("*.py"):
                shutil.copy(f, pk / f.name)
        shutil.copy(D / "12_IFC/kod/ifc_uret.py", pk / "ifc_uret_tatar.py")   # Tatar IFC'si 12_IFC sürümüyle üretildi
        T80 = D / "10_Cozumleyici/tatar80"

        # 1) Bayi PDF'i → Ölçülü Kroki
        c = W / "cikti/tatar"; c.mkdir(parents=True)
        r = kos([PY, "-m", "cozumleyici.pdf_vektor", str(T80 / "Tatar_80m2_2026-09-16.pdf"), "--cikti", str(c)], W)
        modul = re.search(r"pano modülü.*?(\d\.\d{5}) cm/pt", r.stdout)
        yazi = re.search(r"Kullanılan ölçek: ölçü yazılarından (\d\.\d{5}) cm/pt", r.stdout)
        kaydet("PDF okuyucu: kroki.json", r.returncode == 0 and json_ayni(c / "kroki.json", T80 / "kroki.json"),
               f"ölçek modülden {modul.group(1) if modul else '?'}, yazılardan {yazi.group(1) if yazi else '?'} cm/pt")

        # 2) Kroki → serbest akslı İş Emri → yamalı Motor
        r = kos([PY, "-m", "cozumleyici.kroki_is_emri", str(c / "kroki.json"), "--kod", "TATAR-80M2-1609",
                 "--cikti", str(c / "serbest"), "--motor"], W)
        s = c / "serbest"
        kaydet("Serbest aks: is_emri.json", r.returncode == 0 and json_ayni(s / "is_emri.json", T80 / "is_emri.json"))
        kaydet("Serbest aks: donusum_raporu.json", json_ayni(s / "donusum_raporu.json", T80 / "donusum_raporu.json"))
        kaydet("Motor: validation.json", json_ayni(s / "motor/validation.json", T80 / "motor/validation.json"))
        kaydet("Motor: bom.json + bom.csv", json_ayni(s / "motor/bom.json", T80 / "motor/bom.json")
               and csv_satirlar(s / "motor/bom.csv") == csv_satirlar(T80 / "motor/bom.csv"))

        # 3) Blender girdisi → IFC → hacim denetimi
        b = W / "cikti/b3d"; b.mkdir(parents=True)
        r = kos([PY, "-m", "cozumleyici.blender_hazirla", str(T80 / "Tatar_80m2_2026-09-16.pdf"), str(b / "blender_girdi.json")], W)
        kaydet("Blender girdisi: blender_girdi.json", r.returncode == 0 and json_ayni(b / "blender_girdi.json", D / "11_Blender/blender_girdi.json"))
        r = kos([PY, str(pk / "ifc_uret_tatar.py"), str(b / "blender_girdi.json"), str(b / "model.ifc")], b)
        import ifcopenshell, ifcopenshell.validate
        from collections import Counter
        yeni, eski = ifcopenshell.open(str(b / "model.ifc")), ifcopenshell.open(str(D / "12_IFC/Tatar_80m2_bayi_plani.ifc"))
        sy, se = Counter(e.is_a() for e in yeni.by_type("IfcProduct")), Counter(e.is_a() for e in eski.by_type("IfcProduct"))
        kaydet("IFC: sınıf sayıları", sy == se, f"IfcWall {sy['IfcWall']}, IfcOpeningElement {sy['IfcOpeningElement']}")
        log = ifcopenshell.validate.json_logger(); ifcopenshell.validate.validate(yeni, log)
        kaydet("IFC: şema doğrulaması", len(log.statements) == 0, f"{len(log.statements)} hata", ("GEÇTİ", "KALDI"))
        kaydet("IFC: ifc_bom.csv", csv_satirlar(b / "ifc_bom.csv") == csv_satirlar(D / "12_IFC/ifc_bom.csv"))
        kaydet("Çift sayım: IFC ↔ Blender BOM", csv_satirlar(b / "ifc_bom.csv", False) == csv_satirlar(D / "11_Blender/blender_bom.csv", False),
               f"{len(csv_satirlar(b / 'ifc_bom.csv', False))} kalem")
        r = kos([PY, "-m", "cozumleyici.ifc_gorsel", str(b / "model.ifc"), str(b / "gorsel")], W)
        g = next((b / "gorsel").glob("*.json"), None)
        kaydet("IFC: geometri hacim denetimi", g is not None and json_ayni(g, D / "12_IFC/ifc_geometri_denetimi.json"),
               f"fark %{json.loads(g.read_text())['fark_yuzde'] if g else '?'}")

        # 4) Blender modeli (isteğe bağlı: bpy)
        if arg.bpy:
            r = kos([arg.bpy, str(pk / "blender_ciz.py"), str(b / "blender_girdi.json"), str(b / "blender")], W)
            kaydet("Blender: blender_bom.csv + blender_ozet.json",
                   r.returncode == 0 and csv_satirlar(b / "blender/blender_bom.csv") == csv_satirlar(D / "11_Blender/blender_bom.csv")
                   and json.loads((b / "blender/blender_ozet.json").read_text()) == json.loads((D / "11_Blender/blender_ozet.json").read_text()))
        else:
            sonuc.append(("Blender modeli", "ATLANDI · --bpy verilmedi"))

        # 5) Yan Verandalı: İş Emri → IFC → Astra modeliyle kıyas
        k = W / "cikti/kiyas_yan"; k.mkdir(parents=True)
        r = kos([PY, str(pk / "motor_girdi.py"), "is_emri/YAN_VERANDALI_2plus1_6x8p5.json", str(k / "motor_girdi.json")], W)
        kaydet("Kıyas: motor_girdi.json", r.returncode == 0 and json_ayni(k / "motor_girdi.json", D / "13_Kiyas/kiyas_sonuc/motor_girdi.json"))
        kos([PY, "-m", "cozumleyici.ifc_uret", str(k / "motor_girdi.json"), str(k / "bizim.ifc")], W)
        r = kos([PY, "-m", "cozumleyici.kiyas_astra", str(D / "13_Kiyas/astra_detay.json"), str(D / "13_Kiyas/astra_kaynak/model_data.json"),
                 str(k / "bizim.ifc"), str(k / "sonuc")], W)
        ok = r.returncode == 0 and json_ayni(k / "sonuc/kiyas.json", D / "13_Kiyas/kiyas_sonuc/kiyas.json") \
            and (k / "sonuc/kiyas_tablosu.csv").read_text(encoding="utf-8") == (D / "13_Kiyas/kiyas_sonuc/kiyas_tablosu.csv").read_text(encoding="utf-8")
        oz = json.loads((k / "sonuc/kiyas.json").read_text())["ozet"] if (k / "sonuc/kiyas.json").exists() else {}
        kaydet("Kıyas: kiyas.json + kiyas_tablosu.csv", ok,
               f"eleman {oz.get('eleman', {}).get('eslesen_AYNI')}/{oz.get('eleman', {}).get('astra')}, "
               f"açıklık {oz.get('aciklik', {}).get('AYNI')}/{oz.get('aciklik', {}).get('astra')}")

        if arg.sakla:
            shutil.copytree(W, arg.sakla, dirs_exist_ok=True)

    genis = max(len(a) for a, _ in sonuc)
    for a, s in sonuc:
        print(f"{a:<{genis}}  {s}")
    farkli = [a for a, s in sonuc if s.startswith(("FARKLI", "KALDI"))]
    print("SONUÇ:", "23 Eylül sayıları yeniden üretildi" if not farkli else f"{len(farkli)} adımda fark var")
    return 0 if not farkli else 1


if __name__ == "__main__":
    raise SystemExit(main())
