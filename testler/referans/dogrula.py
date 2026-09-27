"""Dondurulmuş referansa karşı doğrulama: v1.1.1 çekirdeği (Beyin kuralları, Motor, çıkarıcı) bugün de aynı sonucu
veriyor mu?

Depo koduna dokunmaz: v1.1.1 ağacını geçici bir klasöre kopyalar (deneme/, testler/, KARARLAR/ hariç),
`denetim/kos.py --planlar` koşar ve sonucu dondurulmuş kayıtlarla karşılaştırır (28 Eylül 2026, üç ayrı temiz koşuda aynı):
  denetim_kosum_2026-09-28.json  adım durumları, sayılar, BOM sayımları, girdi özetleri, 16 plan sonucu
  dxf_parmak_izleri.txt          18 DXF çıktısının içerik parmak izi (parmak_izi.py; zaman damgası ve kimlikler hariç)
  pdf_parmak_izleri.txt          18 PDF çıktısının sayfa sayısı ve ölçüsü

Kurallar:
  - Referans girdiler (İş Emri şablonları, ref_* çizimleri, Beyin test mesajları ve kayıtlı LLM çıkarımları) değişmemeli.
    Kod dosyalarının özeti yalnız bilgi olarak raporlanır; kod değişikliği tek başına farka sayılmaz.
  - Beyin harness'inde tüm vakalar uyumlu olmalı; vaka sayısı referanstan az olamaz (yeni vaka eklenebilir).
  - Motor sayıları, BOM sayımları, çıkarıcı sonuçları ve içerik parmak izleri referansla aynı olmalı. Bilerek yapılan
    bir değişiklik bunları değiştirirse referans gerekçesiyle ve yeni tarihle yeniden dondurulur; eskisi silinmez.

Kullanım (depo kökünde):  python3 testler/referans/dogrula.py [--hizli]
    --hizli: 16 katalog planını atlar (~45 sn yerine ~4,5 dk)
Çıkış kodu 0 = referansla aynı. Fark varsa listelenir; düzeltilmez.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF))
from parmak_izi import ozet  # noqa: E402

HIZLI = {"altin_6x8", "altin_yan", "p6001"}  # --hizli koşuda üretilen çıktılar (+ çıkarıcı P6001)
SAYILAR = {
    "motor_altin_6x8": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_altin_yan_6x8p5_bom": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "altin", "dis_olcu"],
    "motor_p6001": ["pano", "kose", "aciklik", "ucluH", "ayak_izi_fark_cm2", "dis_olcu", "dis_olcu_ok"],
}



def _yoksay(dizin, adlar):
    """Kökte yalnız v1.1.1 dışındaki klasörler atlanır; beyin/testler gibi alt klasörler kopyalanır."""
    if Path(dizin).resolve() == KOK:
        return [a for a in adlar if a in {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}]
    return [a for a in adlar if a in {"__pycache__", ".git"}]

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--hizli", action="store_true"); a = ap.parse_args()
    ref = json.loads((REF / "denetim_kosum_2026-09-28.json").read_text(encoding="utf-8"))
    oku = lambda f: dict(reversed(l.split("  ", 1)) for l in (REF / f).read_text().splitlines() if l.strip())
    ref_pi, ref_pdf = oku("dxf_parmak_izleri.txt"), oku("pdf_parmak_izleri.txt")
    satir, kotu = [], 0

    def yaz(ad, ok, ek=""):
        nonlocal kotu
        kotu += not ok
        satir.append((ad, ("AYNI" if ok else "FARKLI") + (f" · {ek}" if ek else "")))

    with tempfile.TemporaryDirectory() as t:
        W = Path(t) / "is"
        shutil.copytree(KOK, W, ignore=_yoksay)
        komut = [sys.executable, "denetim/kos.py"] + ([] if a.hizli else ["--planlar"])
        r = subprocess.run(komut, cwd=W, capture_output=True, text=True)
        yol = W / "cikti/denetim/sonuc.json"
        if not yol.exists():
            print(r.stdout[-2000:], r.stderr[-2000:]); return 2
        yeni = json.loads(yol.read_text(encoding="utf-8"))
        ra, ya = ref["adimlar"], yeni["adimlar"]
        for adim, v in ya.items():
            yaz(f"{adim}: durum", v.get("durum") == "passed", v.get("durum"))
        def duz(d, on=""):
            out = {}
            for k, v in d.items():
                out.update(duz(v, on + k + "/") if isinstance(v, dict) else {on + k: v})
            return out
        yh, rh = duz(ya["girdi_hashleri"]["hashler"]), duz(ra["girdi_hashleri"]["hashler"])
        kod = lambda y: y.endswith((".py", ".php"))
        veri_fark = sorted(k for k in set(yh) | set(rh) if not kod(k) and yh.get(k) != rh.get(k))
        kod_fark = sorted(k for k in set(yh) | set(rh) if kod(k) and yh.get(k) != rh.get(k))
        yaz("referans girdiler (şablon, çizim, test verisi)", not veri_fark, ", ".join(veri_fark) if veri_fark else f"{sum(not kod(k) for k in rh)} dosya")
        satir.append(("kod dosyaları (bilgi)", ("değişti: " + ", ".join(kod_fark)) if kod_fark else "değişmedi"))
        yb, rb = ya["beyin_harness"]["sayilar"], ra["beyin_harness"]["sayilar"]
        yaz("beyin_harness", yb["uyumlu"] == yb["toplam"] and yb["toplam"] >= rb["toplam"], f"{yb['uyumlu']}/{yb['toplam']} (referans {rb['toplam']} vaka)")
        for adim, alanlar in SAYILAR.items():
            ys, rs = ya[adim]["sayilar"], ra[adim]["sayilar"]
            yaz(f"{adim}: sayılar", all(ys.get(k) == rs.get(k) for k in alanlar), f"pano {ys.get('pano')}, dış ölçü {ys.get('dis_olcu')}")
            yaz(f"{adim}: BOM sayımı", ya[adim].get("bom_sayim") == ra[adim].get("bom_sayim"))
        ys, rs = ya["cikarici_p6001_altin"]["sayilar"], ra["cikarici_p6001_altin"]["sayilar"]
        yaz("cikarici_p6001_altin: sayılar", {k: ys.get(k) for k in ("grid_esit", "mahal_esit", "aciklik_esit")}
            == {k: rs.get(k) for k in ("grid_esit", "mahal_esit", "aciklik_esit")}, f"mahal {ys.get('mahal_esit')}, açıklık {ys.get('aciklik_esit')}")
        yaz("sir_taramasi", ya["sir_taramasi"]["sayilar"] == ra["sir_taramasi"]["sayilar"])
        if not a.hizli:
            ys, rs = ya["cikarici_16_plan"], ra["cikarici_16_plan"]
            yaz("cikarici_16_plan: özet", ys["sayilar"] == rs["sayilar"], f"{ys['sayilar']['motor_passed']}/{ys['sayilar']['toplam']}")
            plan = lambda d: {k: (v.get("cikis_kodu"), v.get("motor_passed")) for k, v in d["planlar"].items()}
            yaz("cikarici_16_plan: plan plan", plan(ys) == plan(rs))
        for tur, ref_d in (("DXF", ref_pi), ("PDF", ref_pdf)):
            beklenen = [k for k in ref_d if a.hizli is False or k.split("/")[2] in HIZLI or k.startswith("cikti/denetim/cikarici/P6001/")]
            eksik = [k for k in beklenen if not (W / k).exists()]
            fark = [k for k in beklenen if (W / k).exists() and ozet(W / k) != ref_d[k]]
            ek = f"{len(beklenen) - len(eksik)}/{len(beklenen)} dosya"
            if eksik: ek += f", eksik: {eksik}"
            if fark: ek += f", fark: {fark}"
            yaz(f"{tur} içerik parmak izleri" if tur == "DXF" else "PDF sayfa sayısı ve ölçüsü", not eksik and not fark, ek)

    g = max(len(x) for x, _ in satir)
    for x, s in satir:
        print(f"{x:<{g}}  {s}")
    print("SONUÇ:", "referansla aynı" if not kotu else f"{kotu} kontrolde fark var")
    return 0 if not kotu else 1


if __name__ == "__main__":
    raise SystemExit(main())
