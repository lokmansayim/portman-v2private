"""Aşama 2 · 90 m² civarı 3+1 adaylarının kaynak–geometri karşılaştırmasını yeniden üretir (30.09.2026).

Rapor: docs/raporlar/2026-09-30_Asama2_3arti1_Aday_Karsilastirmasi.md

Depo koduna dokunmaz. Her aday için:
  1. çıkarıcı → İş Emri → Motor v1.1 (plan DXF/PDF, BOM, validation.json), bugünkü zincir değiştirilmeden;
  2. kaynak görseli: katalog DXF'inde planın paftası, çıkarıcıyla aynı bölge (<kod>_kaynak.png)
     ve çıkarıcının tanı görseli (<kod>_tani.png);
  3. --ifc ile verilen adaylar için aynı İş Emri'nden IFC4. 23.09 deneme kodu (deneme/2026-09-23) geçici bir
     klasörde tek `cozumleyici` paketinde birleştirilir; Motor yamasızdır (serbest aks YOK).

Kaynaktaki kapı ve pencere sayıları görüntüden elle sayıldı (rapor §2) ve kaynak_sayimlari.json'da duruyor.
Betik Motor'un çizdiğini bu kaynak sayılarıyla yan yana yazar (kaynak_karsilastirma.txt). Yalnız farkı gösterir,
"geçerli" demez: eşikler K-A9 kararıyla konur. Motor'un "passed" sonucu kaynağa uygunluk DEĞİLDİR.

Kullanım (depo kökünde):
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör>
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör> --kodlar P9401 --ifc P9401

Dışarıdan gelen bir çizim (ör. Astra'nın DXF'i) aynı zincirden geçer ve katalog kaynağıyla kıyaslanır:
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör> --dxf <çizim.dxf> --kodlar P9401 [--secici <etiket>] [--ifc P9401]
Dışarıdan gelen bir İş Emri (JSON, şema v0.1; bkz. docs/is_emirleri/IE-04-aday-teslimi.md) çıkarıcı olmadan Motor'a girer:
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör> --is-emri <is_emri.json> --kodlar P9401 [--ifc P9401]
  Motor planı, PDF, IFC ve kaynak kıyası aynı dosyadan üretilir; İş Emri'nin `eksikler` ve `varsayimlar` listeleri rapora yazılır.
  --kodlar tek aday olmalı: kıyasın yapılacağı katalog adayı. Çizimde pafta başlığı ("PORT - P9401" gibi) varsa betik onu
  kendisi bulur ve çıkarıcıya seçici olarak verir; katalogdaki paftayla aynı bölge okunur (5 adayda sınandı, İş Emri
  katalogdakiyle aynı). Başlık yoksa bütün dosya okunur; duvar gövdesi parçalıysa çıkarıcı "uzak duvar parçası" atabilir
  (P9201'de görüldü) ve betik uyarır. --secici ile başlık elle verilebilir.
  Çizimin çıkarıcıda okunması için: birim cm; duvar katmanı "0" ya da "DUVAR", pencere "Pencere", kapı "Kapı",
  veranda "Veranda"; dış kutu 125,5·nx + 20 × 125,5·ny + 10 cm (±2,5); oda adı ve m² odanın içinde MTEXT.

Gerekenler: Python 3.11, ezdxf 1.4.4, matplotlib, shapely, numpy, pillow, pymupdf; IFC için ifcopenshell 0.8.5.
Ağ, LLM, WhatsApp ya da canlı sunucu kullanılmaz.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
D23 = KOK / "deneme" / "2026-09-23"
DXF = KOK / "ref_katalog" / "TEK_KAT_PREFABRIK_PLANLARI.dxf"
PY = sys.executable
ADAYLAR = ["P9401", "P9201", "P9501", "P1051", "P1121"]
KAYNAK = json.loads((Path(__file__).resolve().parent / "kaynak_sayimlari.json").read_text(encoding="utf-8"))["adaylar"]


def kos(komut: list[str], cwd: Path, gunluk: Path | None = None) -> int:
    env = {**os.environ, "PYTHONPATH": str(cwd)}
    r = subprocess.run(komut, cwd=cwd, env=env, capture_output=True, text=True)
    if gunluk:
        gunluk.write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode:
        print(f"   HATA ({r.returncode}): {' '.join(komut[:4])} …\n{(r.stderr or r.stdout)[-1500:]}")
    return r.returncode


def kaynak_gorseli(kodlar: list[str], cikti: Path, dxf: Path = DXF, secici: str | None = "") -> None:
    """Katalog DXF'indeki paftayı (ham çizgi, kapı yayları, yazılar) ve çıkarıcının tanı görselini PNG'ye çizer."""
    sys.path.insert(0, str(KOK))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
    from motor.cikarici import Cikarici, tani_png
    for kod in kodlar:
        cik = Cikarici(str(dxf), plan_secici=(kod if secici == "" else secici))
        ie = cik.calistir(kod)
        tani_png(cik, ie, cikti / f"{kod}_tani.png")
        bolge = cik._plan_bolgesi()               # seçici yoksa (tek planlık dış çizim) None döner: bütün çizim
        if bolge is None:
            from ezdxf import bbox
            e = bbox.extents(cik.msp)
            bolge = (e.extmin.x, e.extmin.y, e.extmax.x, e.extmax.y)
        x0, y0, x1, y1 = bolge
        fig = plt.figure(figsize=(12, 12 * (y1 - y0) / (x1 - x0)))
        ax = fig.add_axes([0, 0, 1, 1])
        # Beyaz zemin şart: renk 7 (beyaz/siyah) çizgiler aksi hâlde beyaz üstüne beyaz çıkar (P9201'de duvarlar görünmüyordu).
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, min_lineweight=0.4)
        Frontend(RenderContext(cik.doc), MatplotlibBackend(ax), config=cfg).draw_layout(cik.msp, finalize=False)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")
        fig.savefig(cikti / f"{kod}_kaynak.png", dpi=110, facecolor="white"); plt.close(fig)


def ifc_paketi(t: Path) -> Path:
    """23.09 betiklerini depo kopyasında tek `cozumleyici` paketinde birleştirir (yeniden_kos.py ile aynı düzen, yamasız)."""
    W = t / "is"
    atla = {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}
    shutil.copytree(KOK, W, ignore=lambda d, a: [x for x in a if (Path(d).resolve() == KOK and x in atla) or x in {"__pycache__", ".git"}])
    pk = W / "cozumleyici"; pk.mkdir()
    for kaynak in ["10_Cozumleyici/kod/cozumleyici", "11_Blender/kod", "13_Kiyas/kod"]:
        for f in (D23 / kaynak).glob("*.py"):
            shutil.copy(f, pk / f.name)
    return W


def ozet(kod: str, klasor: Path) -> str:
    v = json.loads((klasor / "motor" / "validation.json").read_text(encoding="utf-8"))
    odalar = ", ".join(f"{k} {round(m, 2)}" for k, m in (v.get("rooms_m2") or {}).items())
    return (f"{kod}: Motor doğrulaması {'geçti' if v.get('passed') else 'GEÇMEDİ'} (kaynağa uygunluk değil) · dış {v.get('outer_cm')} cm · "
            f"pano {v.get('panel_count')} · pencere {v.get('windows')} · kapı {v.get('doors')} · odalar: {odalar}")


def karsilastir(kod: str, klasor: Path) -> str:
    """Motor'un çizdiğini kaynak sayılarıyla yan yana yazar. Hüküm vermez (K-A9 eşikleri yok)."""
    k = KAYNAK.get(kod)
    if not k:
        return f"{kod}: kaynak sayımı yok (kaynak_sayimlari.json)"
    v = json.loads((klasor / "motor" / "validation.json").read_text(encoding="utf-8"))
    oda = {a: m for a, m in (v.get("rooms_m2") or {}).items()}
    s = [f"{kod}: pencere kaynak {k['pencere']} → çizilen {v.get('windows')} · kapı kaynak {k['kapi']} → çizilen {v.get('doors')}"]
    for ad, m2 in k["etiketler"].items():
        c = oda.pop(ad, None)
        s.append(f"   {ad}: etiket {m2} ↔ Motor " + ("YOK" if c is None else f"{round(c, 2)} ({(c - m2) / m2 * 100:+.1f}%)"))
    if k["etiketler"]:
        e = sum(m for a, m in k["etiketler"].items() if a != "VERANDA")
        c = sum(m for a, m in (v.get("rooms_m2") or {}).items() if a != "VERANDA")
        s.append(f"   net oda toplamı (verandasız): etiket {round(e, 2)} ↔ Motor {round(c, 2)} ({(c - e) / e * 100:+.1f}%)")
        if oda:
            s.append("   kaynakta etiketi olmayan Motor mahalleri: " + ", ".join(f"{a} {round(m, 2)}" for a, m in oda.items()))
    else:
        s.append("   oda etiketleri: eşleme elle doğrulanmadı, kıyas yok")
    s.append(f"   not: {k['not']}")
    return "\n".join(s)


def is_emri_motor(kod: str, ie_yolu: Path, klasor: Path, gunluk: Path) -> int:
    """Dış İş Emri'ni çıkarıcı olmadan Motor'a verir; klasör düzeni çıkarıcınınkiyle aynı (is_emri.json + motor/)."""
    klasor.mkdir(parents=True, exist_ok=True)
    ie = json.loads(ie_yolu.read_text(encoding="utf-8"))
    (klasor / "is_emri.json").write_text(json.dumps(ie, ensure_ascii=False, indent=1), encoding="utf-8")
    kimlik = [f"is_emri_no {ie.get('is_emri_no')} · revizyon {ie.get('revizyon')} · referans_model {(ie.get('yapi') or {}).get('referans_model')}"
              f" · kaynak: {((ie.get('talep') or {}).get('metin') or '-')[:100]}"]
    if (ie.get("yapi") or {}).get("referans_model") != kod:
        kimlik.append(f"UYARI: yapi.referans_model ({(ie.get('yapi') or {}).get('referans_model')}) ile --kodlar ({kod}) farklı")
    kimlik += [f"varsayım: {v}" for v in ie.get("varsayimlar") or []] + [f"EKSİK (kaynakta belirsiz; onaylanmış sayılmaz): {e}" for e in ie.get("eksikler") or []]
    (klasor / "kimlik.txt").write_text("\n".join(kimlik) + "\n", encoding="utf-8")
    print("   " + "\n   ".join(kimlik))
    kod_py = ("import json, sys; from pathlib import Path; from motor import dxf_out; ie = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); "
              "m = dxf_out.uret(ie, Path(sys.argv[2])); print(json.dumps(m, ensure_ascii=False, default=str)[:600])")
    return kos([PY, "-c", kod_py, str(klasor / "is_emri.json"), str(klasor / "motor")], KOK, gunluk)


def ifc_ozet(kod: str, yol: Path) -> str:
    """IFC sınıf sayıları ve şema doğrulaması (şema doğrulaması üretim doğruluğu değildir)."""
    import ifcopenshell, ifcopenshell.validate
    m = ifcopenshell.open(str(yol))
    say = {s: len(m.by_type(s)) for s in ("IfcWall", "IfcWindow", "IfcDoor", "IfcSpace", "IfcOpeningElement")}
    kayit = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(m, kayit)
    hata = sum(1 for s in kayit.statements if str(s.get("level")).lower() == "error")   # 0.8.5: düzey "error"
    return f"{kod} IFC: " + " · ".join(f"{k} {v}" for k, v in say.items()) + f" · şema hatası {hata}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", required=True, type=Path)
    ap.add_argument("--kodlar", nargs="+", default=ADAYLAR)
    ap.add_argument("--ifc", nargs="*", default=None, help="IFC üretilecek adaylar (varsayılan: katalogda P9401 P9201, dış çizimde yok)")
    ap.add_argument("--dxf", type=Path, default=DXF, help="çizim (varsayılan: katalog DXF'i)")
    ap.add_argument("--secici", default=None, help="dış çizimde plan etiketi (tek plan varsa verilmez)")
    ap.add_argument("--is-emri", dest="is_emri", type=Path, default=None, help="dış İş Emri (JSON); çıkarıcı atlanır, Motor doğrudan çizer")
    a = ap.parse_args()
    dis = a.dxf.resolve() != DXF.resolve() or a.is_emri is not None
    if a.is_emri is not None and a.dxf.resolve() != DXF.resolve():
        print("DUR: --is-emri ile --dxf birlikte verilmez"); return 2
    if dis and len(a.kodlar) != 1:
        print("DUR: dış çizimde --kodlar tek aday olmalı (kıyasın yapılacağı katalog adayı)"); return 2
    if a.ifc is None:
        a.ifc = [] if dis else ["P9401", "P9201"]
    secici = a.secici if dis else ""          # "": kod ile aynı (katalogda)
    if a.is_emri is not None:
        kod = a.kodlar[0]; c = a.cikti.resolve(); c.mkdir(parents=True, exist_ok=True); k = c / "cikarici" / kod
        print(f"-- {kod}: dış İş Emri → Motor · {a.is_emri.name}")
        if is_emri_motor(kod, a.is_emri.resolve(), k, c / f"{kod}.log"):
            return 1
        satirlar, kiyas = [ozet(kod, k)], [karsilastir(kod, k)]
        kiyas.append("   (kaynak görseli çizilmedi: dış İş Emri'nde çizim yok; katalog paftası için katalog koşumuna bakın)")
        return _ifc_ve_yaz(a, c, satirlar, kiyas, f"dış İş Emri {a.is_emri.name}")
    if dis and secici is None:
        sys.path.insert(0, str(KOK))
        from motor.cikarici import Cikarici, CikarimHatasi
        try:
            Cikarici(str(a.dxf.resolve()), plan_secici=a.kodlar[0])._plan_bolgesi()
            secici = a.kodlar[0]
            print(f"-- çizimde pafta başlığı bulundu ({secici}); katalogdaki gibi başlığın paftası okunacak")
        except CikarimHatasi:
            print("-- UYARI: çizimde pafta başlığı yok; bütün dosya okunacak (parçalı duvar gövdesinde uzak parçalar atılabilir)")
    c = a.cikti.resolve(); c.mkdir(parents=True, exist_ok=True)
    satirlar, kiyas = [], []
    for kod in a.kodlar:
        k = c / "cikarici" / kod
        print(f"-- {kod}: çıkarıcı → İş Emri → Motor" + (f" · çizim {a.dxf.name}" if dis else ""))
        komut = [PY, "-m", "motor.cikarici", str(a.dxf.resolve()), "--kod", kod, "--cikti", str(k), "--motor"]
        sec = kod if secici == "" else secici
        if sec:
            komut[4:4] = ["--secici", sec]
        if kos(komut, KOK, c / f"{kod}.log"):
            return 1
        satirlar.append(ozet(kod, k))
        kiyas.append(karsilastir(kod, k))
        rapor = (k / "cikarim_raporu.md").read_text(encoding="utf-8") if (k / "cikarim_raporu.md").exists() else ""
        if "uzak duvar parçası yok sayıldı" in rapor:
            kiyas.append(f"   UYARI: çıkarıcı uzak duvar parçalarını attı (cikarim_raporu.md); pafta başlığıyla (--secici) yeniden koşun")
    print("-- kaynak ve tanı görselleri")
    kaynak_gorseli(a.kodlar, c, a.dxf.resolve(), secici)
    return _ifc_ve_yaz(a, c, satirlar, kiyas, f"dış çizim {a.dxf.name}" if dis else "katalog DXF")


def _ifc_ve_yaz(a, c: Path, satirlar: list[str], kiyas: list[str], kaynak_adi: str) -> int:
    if a.ifc:
        with tempfile.TemporaryDirectory() as t:
            W = ifc_paketi(Path(t))
            for kod in a.ifc:
                print(f"-- {kod}: aynı İş Emri'nden IFC4")
                ie = c / "cikarici" / kod / "is_emri.json"
                if kos([PY, "-m", "cozumleyici.motor_girdi", str(ie), str(c / f"{kod}.motor_girdi.json")], W):
                    return 1
                # Başlık verilmeli: ifc_uret.py'nin varsayılan başlığı 23.09 bayi planının adını taşır.
                if kos([PY, "-m", "cozumleyici.ifc_uret", str(c / f"{kod}.motor_girdi.json"), str(c / f"{kod}.ifc"),
                        f"Portman — {kod} (Aşama 2 adayı; {kaynak_adi})"], W, c / f"{kod}.ifc.log"):
                    return 1
                satirlar.append(ifc_ozet(kod, c / f"{kod}.ifc"))
    (c / "ozet.txt").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    baslik = f"Kaynakla kıyas · çizim: {kaynak_adi} · hüküm yok (K-A9 eşikleri bekleniyor)"
    (c / "kaynak_karsilastirma.txt").write_text(baslik + "\n" + "\n".join(kiyas) + "\n", encoding="utf-8")
    print("\n".join(satirlar)); print(baslik); print("\n".join(kiyas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
