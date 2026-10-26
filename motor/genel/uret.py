#!/usr/bin/env python3
"""Genel motorun tek çağrısı (İE-08 GM1): Yapı Tanımı → çizim seti (plan, görünüşler, pafta PNG; IFC4 + özet; perspektifler) +
yükleme listesi (girdi + liste JSON/MD) + bayiye gidenler (etiketli plan görseli, Örnek Şablon paftası PDF) + validation/manifest.

    python -m motor.genel.uret modeller/C8801.json <çıktı klasörü> [--set kurallar/liste/setler/0.19.json] [--yontem panel|omega_asik]
                               [--perspektifsiz] [--is-emri-no PM-…] [--revizyon 1]

Deneme betiği `deneme/2026-10-06_kor_test/cizim_seti_kos.sh`'nin Python karşılığıdır: aynı modüller aynı argümanlarla çağrılır
(`ciz_genel.main`, `ifc_genel.main`, `girdi_genel.main`, `yukleme.main`; argv ile), çıktı baytları değişmez. Perspektif ayrı süreçte
koşar (VTK, OSMesa yokken çökebilir; çökmesi işi düşürmez: `validation.json › perspektif`). Kural seti `--set` ile (yoksa güncel
`kurallar/liste/kurallar.json`; `PORTMAN_KURALLAR` ortam değişkeni de geçerlidir).

Manifest, canlı Motor'un (`motor/dxf_out.uret`) worker'a verdiği anahtarları taşır: `pdf`, `pdf_sha256`, `warnings`; ek olarak
`ifc`, `ifc_sha256`, `preview`, `plan_bayi`, `yukleme_json`, `ciktilar`, `duzenlenebilir_dxf`. `validation.json`: `passed` (zorunlu
çıktılar tam ve IFC şema hatası 0), `errors`, `eksik`, `ifc`, `liste_satir`, `perspektif`.

D-11 (Lokman, 13 Ekim 2026): `kurallar/cizim/duzenlenebilir.json › dxf` varsa çizim setinin düzenlenebilir kopyası `<kod>_cizim.dxf`
(plan + dört görünüş, katmanlı, cm; `dxf_genel.py`) da yazılır. Çıktıdır, kaynak değil; bayiye gitmez; üretilemezse uyarı, iş düşmez.
Çizim setinin dosya listesine (`cizim_seti.json`) girmez: `ciktilar` sayısı ve öteki çıktıların baytları değişmez.
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)
import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]           # uret.py → parents[0] motor/genel, [1] motor, [2] depo kökü
PERSPEKTIF_ZAMAN_ASIMI_S = 240
ZORUNLU = ("{kod}_plan.png", "{kod}_gorunusler.png", "{kod}_pafta.png", "{kod}.ifc", "{kod}.ozet.json")
PERSPEKTIFLER = ("{kod}_perspektif_on_sag.png", "{kod}_perspektif_on_sol.png", "{kod}_perspektif_arka_sol.png", "{kod}_perspektif_arka_sag.png",
                 "{kod}_catisiz.png", "{kod}_makasli.png", "{kod}_geometri.json")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def kod_govde(t: dict) -> str:
    return t["kod"].replace("Ç", "C").replace("-", "")


def _bilgisiz(metin: str, bilgi: dict | None) -> str:
    """Hata iletisinde zarfın `bilgi` değerleri (bayi adı, kart numarası) geçmesin (D-09, K09): geçen her değer `[bilgi]` olur."""
    for v in (bilgi or {}).values():
        if isinstance(v, str) and len(v) >= 4 and v in metin:
            metin = metin.replace(v, "[bilgi]")
    return metin


def _main(mod, argv: list[str], gunluk: io.StringIO) -> int:
    """Modülün main()'ini argv ile, stdout'u günlüğe yönlendirerek çağırır; SystemExit kodunu döner."""
    eski = sys.argv
    sys.argv = [mod.__name__] + [str(a) for a in argv]
    try:
        with contextlib.redirect_stdout(gunluk):
            try:
                r = mod.main()
            except SystemExit as e:
                r = e.code if isinstance(e.code, int) else 1
                if not isinstance(e.code, int) and e.code:
                    print(e.code, file=gunluk)
            except Exception as e:                   # geçersiz tanım vb.: adım düşer, kayıt yine yazılır; uret() çağırana istisna fırlatmaz
                print(f"{mod.__name__}: {type(e).__name__}: {str(e)[:300]}", file=gunluk)
                r = 1
        return int(r or 0)
    finally:
        sys.argv = eski


def kural_seti(set_yolu: Path | None):
    """Kural seti seçimi; tek yer `kural.secili` (bayi görseli ve şablon paftası da onu kullanır)."""
    from . import kural
    return kural.secili(set_yolu)


@contextlib.contextmanager
def karkas_kurali(karkas_yolu: Path | None):
    """Blok boyunca karkas kuralının dosyasını seçer (`PORTMAN_KARKAS`; İE-16 PR-3a); çıkışta eski değeri geri koyar. `None` ise dokunmaz."""
    eski = os.environ.get("PORTMAN_KARKAS")
    if karkas_yolu is not None:
        os.environ["PORTMAN_KARKAS"] = str(Path(karkas_yolu).expanduser().resolve())
    try:
        yield
    finally:
        if karkas_yolu is not None:
            if eski is None:
                os.environ.pop("PORTMAN_KARKAS", None)
            else:
                os.environ["PORTMAN_KARKAS"] = eski


def perspektif_kos(ifc: Path, hedef: Path, kod: str, zaman_asimi: int = PERSPEKTIF_ZAMAN_ASIMI_S) -> dict:
    """VTK çizimini ayrı süreçte koşar: çökme (sinyal), zaman aşımı ya da içe aktarma hatası işi düşürmez."""
    try:
        from importlib.util import find_spec
        if find_spec("vtk") is None:
            return {"durum": "ÇİZİLEMEDİ", "neden": "VTK kurulu değil"}
    except Exception as e:  # pragma: no cover
        return {"durum": "ÇİZİLEMEDİ", "neden": f"VTK denetlenemedi: {e}"}
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-m", "motor.genel.perspektif", str(ifc), str(hedef), kod], cwd=str(KOK), capture_output=True, text=True, timeout=zaman_asimi)
    except subprocess.TimeoutExpired:
        return {"durum": "ÇİZİLEMEDİ", "neden": f"zaman aşımı ({zaman_asimi} s)", "sure_s": round(time.time() - t0, 1)}
    if r.returncode == 0:
        return {"durum": "TAMAM", "sure_s": round(time.time() - t0, 1)}
    neden = f"süreç çöktü, sinyal {-r.returncode}" if r.returncode < 0 else f"çıkış {r.returncode}"
    return {"durum": "ÇİZİLEMEDİ", "neden": f"{neden}: {(r.stderr or '').strip()[-300:]}", "sure_s": round(time.time() - t0, 1)}


def matplotlib_sabitle() -> None:
    """Çizim baytları ortamdan bağımsız olsun: matplotlib yalnız kendi varsayılanlarıyla (DejaVu Sans, varsayılan hinting) çizer.
    Bulut çalışma alanında /etc/matplotlib/matplotlibrc (MATPLOTLIBRC) yazı tipini Inter yapıyor ve 'tight' kırpma yüzünden
    görsel boyutu bile değişiyordu (İE-08 Adım 2 bulgusu, 12.10.2026); ie-05'in çizim setleri matplotlib varsayılanlarıyla üretildi."""
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcdefaults()                      # matplotlib'in KENDİ varsayılanları (rc_file_defaults ortamın rc dosyasını geri yüklerdi)
    matplotlib.rcParams["font.family"] = ["sans-serif"]
    matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans"] + [f for f in matplotlib.rcParamsDefault["font.sans-serif"] if f != "DejaVu Sans"]
    # ie-05'in depodaki çizim setleri FreeType'ın kendi hinting'iyle ("default"; "native" ile aynı sonuç) üretilmiş: ana set ve ie-05 setiyle
    # Ç8801'in plan, görünüşler ve pafta PNG'leri yalnız bu ayarla bayt bayt aynı çıkıyor (no_hinting, auto ve force_autohint farklı).
    matplotlib.rcParams["text.hinting"] = "default"


def uret(tanim_yolu: Path, hedef: Path, is_emri_no: str | None = None, revizyon: int | None = 1, set_yolu: Path | None = None,
         yontem: str | None = None, perspektif: bool = True, bayi: bool = True, kaynak: str | None = None,
         elektrik_sayimi: Path | None = None, yalniz_liste: bool = False, bilgi: dict | None = None, karkas_yolu: Path | None = None) -> dict:
    """Bir Yapı Tanımı'ndan çizim setini, IFC'yi, yükleme listesini ve bayi çıktılarını üretir; manifest döner.
    `elektrik_sayimi`: elektrik paftasından sayım (JSON); verilirse listede priz/anahtar/duy satırları oda kuralı yerine sayımdan gelir
    (kör testlerin listeleri böyle üretildi: `sonuc/KT0x_pafta_sayimi.json`). Katalog modellerinde yok.
    `yalniz_liste`: yalnız girdi ve yükleme listesi (çizim, IFC, perspektif ve bayi çıktıları yok; eski kural setleriyle altın liste matrisi).
    `bilgi`: bayi paftasının antet, özellik ve özel istek alanları (İş Emri zarfından: `bayi_adi`, `bayi_telefonu` (D-09), `sevk_adresi`,
    `ozellikler`, `ozel_istekler`); verilmezse "..." (katalog ve altın üretim). Değerleri manifest'e ve günlüğe yazılmaz (yalnız `bilgi_var`).
    `karkas_yolu`: karkas kuralının dosyası (İE-16 PR-3a; yalnız tanım `karkas: kural` isterse okunur; verilmezse kurallar/karkas/celik_karkas.json)."""
    matplotlib_sabitle()
    from . import ciz_genel, girdi_genel, ifc_genel, yukleme
    t0 = time.time()
    tanim_yolu, hedef = Path(tanim_yolu), Path(hedef)
    hedef.mkdir(parents=True, exist_ok=True)
    t = json.loads(tanim_yolu.read_text(encoding="utf-8"))
    kod = kod_govde(t)
    gunluk = io.StringIO(); hatalar: list[str] = []; uyarilar: list[str] = []
    ek = ["--yontem", yontem] if yontem else []
    with kural_seti(set_yolu), karkas_kurali(karkas_yolu):
        from . import kural
        set_kullanilan = str(kural.yol())
        ifc = hedef / f"{kod}.ifc"; ozet: dict = {}
        karkas_paftasi: dict | None = None
        makas_paftasi: dict | None = None
        dxf_yol: Path | None = None
        if not yalniz_liste:
            # 1) çizimler (plan, pafta, görünüşler)
            if _main(ciz_genel, [tanim_yolu, "--cikti", hedef] + ek, gunluk):
                hatalar.append("ciz_genel başarısız")
            # 2) IFC + özet
            r = _main(ifc_genel, [tanim_yolu, ifc] + ek, gunluk)
            ozet = json.loads((hedef / f"{kod}.ozet.json").read_text(encoding="utf-8")) if (hedef / f"{kod}.ozet.json").exists() else {}
            if r:                                   # çıkış kodu sıfır değilse eski bir özet dosyası başarıyı maskelemesin
                hatalar.append("ifc_genel başarısız")
            elif ozet.get("sema_hatasi"):
                hatalar.append(f"IFC şema hatası {ozet['sema_hatasi']}")
            # 2b) düzenlenebilir DXF (D-11; kural anahtarı yoksa üretilmez): plan + dört görünüş. Çıktıdır, kaynak değil; bayiye gitmez,
            # üretilemezse ya da yeniden açılıp denetlenince hata verirse uyarı (iş düşmez)
            from . import dxf_genel
            dxf_kural = dxf_genel.kurallar()
            if dxf_kural.get("dxf"):
                dxf_yol = hedef / dxf_genel.dosya_adi(dxf_kural, kod)
                if _main(dxf_genel, [tanim_yolu, "--cikti", hedef] + ek, gunluk):
                    uyarilar.append("düzenlenebilir DXF üretilemedi ya da denetimden geçmedi (dxf_genel; uret.log)")
                    if dxf_yol.exists():                     # denetimden geçmeyen DXF teslim adıyla kalmaz (K23'ün amacı; kod incelemesi 13.10)
                        dxf_yol.replace(dxf_yol.with_name(dxf_yol.stem + ".HATALI.dxf"))
                    dxf_yol = None
            # 2c) duvar panelleri yerleşim planı (İE-16 PR-3a): yalnız tanım karkas kuralını isterse; istemeyenin çizim seti aynı
            if t.get("karkas") == "kural":
                try:
                    from . import karkas_pafta
                    karkas_paftasi = karkas_pafta.ciz(t, hedef, kod)
                except (Exception, SystemExit) as e:
                    hatalar.append(f"duvar panelleri paftası: {type(e).__name__}: {str(e)[:200]}")
                # 2d) makas yerleşim planı (İE-16 PR-3b): aynı koşulla; çatısız tanımda ve çatı kuralı (`makas`) olmayan eski kural kopyasında
                # (PR-3a'nın listesi o günkü kopyayla yeniden üretilirken) çizilmez
                if t.get("cati"):
                    try:
                        from . import karkas, makas_pafta
                        if "makas" in karkas.oku():
                            makas_paftasi = makas_pafta.ciz(t, hedef, kod, yontem=yontem)
                    except (Exception, SystemExit) as e:
                        hatalar.append(f"makas yerleşim paftası: {type(e).__name__}: {str(e)[:200]}")
        # 3) yükleme listesi (girdi + liste)
        girdi = hedef / f"{kod}_girdi.json"; liste = hedef / f"{kod}_yukleme.json"
        if _main(girdi_genel, [tanim_yolu, "--dosya", girdi, "--uzerine-yaz", "--kaynak", kaynak or f"Yapı Tanımı 0.5 ({tanim_yolu.name})"] + ek, gunluk):
            hatalar.append("girdi_genel başarısız")
        elif _main(yukleme, [girdi, "--cikti", liste, "--md", liste.with_suffix(".md")]
                   + (["--elektrik-sayimi", Path(elektrik_sayimi)] if elektrik_sayimi else []), gunluk):
            hatalar.append("yukleme başarısız")
    liste_satir = len(json.loads(liste.read_text(encoding="utf-8")).get("satirlar", [])) if liste.exists() else 0
    # 4) perspektifler (ayrı süreç; isteğe bağlı)
    pers = perspektif_kos(ifc, hedef, kod) if (perspektif and not yalniz_liste and ifc.exists()) else {"durum": "ATLANDI"}
    if pers["durum"] != "TAMAM":
        uyarilar.append(f"perspektif: {pers['durum']}" + (f" ({pers.get('neden', '')})" if pers.get("neden") else ""))
    # 5) bayiye gidenler (etiketli plan görseli, Örnek Şablon paftası, bayi görseli) — modüller varsa
    bayi_png = hedef / f"{kod}_plan_bayi.png"; pafta_pdf = hedef / f"{kod}_pafta.pdf"; bayi_gorsel = hedef / f"{kod}_bayi_gorsel.png"
    bayi = bayi and not yalniz_liste
    if bayi:
        try:
            from . import bayi_gorseli
            bayi_gorseli.plan_bayi(t, hedef, kod, is_emri_no=is_emri_no, revizyon=revizyon, set_yolu=set_yolu, yontem=yontem)
        except ImportError:
            uyarilar.append("bayi görseli modülü yok")
        except (Exception, SystemExit) as e:        # yapi.kur geçersiz tanımda SystemExit fırlatır; kayıt yine yazılsın
            hatalar.append(f"bayi görseli: {type(e).__name__}: {str(e)[:200]}")
        try:
            from . import sablon_pafta
            # antet, özellik ve özel istek alanları zarftan (`bilgi`; D-09 ad + kart numarası); hata iletisine `bilgi` değerleri girmez
            sablon_pafta.pafta_pdf(t, hedef, kod, is_emri_no=is_emri_no, revizyon=revizyon, set_yolu=set_yolu, yontem=yontem, bilgi=bilgi)
        except ImportError:
            uyarilar.append("şablon pafta modülü yok")
        except (Exception, SystemExit) as e:
            hatalar.append(f"şablon pafta: {type(e).__name__}: {_bilgisiz(str(e), bilgi)[:200]}")
        if bayi_png.exists():                        # bayi görseli: plan + çatı planı + iki perspektif (yoksa iki görünüş) tek görselde
            try:
                from . import bayi_gorseli
                bayi_gorseli.bayi_gorsel(t, hedef, kod, set_yolu=set_yolu, yontem=yontem, perspektif=pers["durum"] == "TAMAM")   # bu koşunun perspektifleri; eski dosya girmez
            except (Exception, SystemExit) as e:    # kart üretilemezse iş düşmez: worker plan görseline döner (uyarı)
                uyarilar.append(f"bayi görseli (kart): {type(e).__name__}: {str(e)[:200]}")
    # 6) çizim seti denetimi (kurallar/cizim/cizim_seti.json) ve kayıtlar
    seti = json.loads((KOK / "kurallar" / "cizim" / "cizim_seti.json").read_text(encoding="utf-8"))
    beklenen = [c["dosya"].format(kod=kod) for c in seti["ciktilar"]] if not yalniz_liste else [girdi.name, liste.name]
    var = {d: (hedef / d).is_file() and (hedef / d).stat().st_size > 0 for d in beklenen}
    eksik = [d for d, v in var.items() if not v]
    zorunlu = ZORUNLU if not yalniz_liste else (f"{kod}_girdi.json", f"{kod}_yukleme.json")
    zorunlu_eksik = [d.format(kod=kod) for d in zorunlu if not var.get(d.format(kod=kod), (hedef / d.format(kod=kod)).is_file())]
    if zorunlu_eksik:
        hatalar.append("zorunlu çıktı eksik: " + ", ".join(zorunlu_eksik))
    if bayi and not pafta_pdf.exists():
        hatalar.append("bayi paftası (PDF) üretilmedi")
    passed = not hatalar
    hatali_pdf = hedef / f"{kod}_pafta.HATALI.pdf"
    if not passed:                                   # K23: doğrulama geçmezse bayiye giden hiçbir dosya teslim adıyla kalmaz; tanı için .HATALI.*
        if pafta_pdf.exists():
            pafta_pdf.replace(hatali_pdf)
        for p in (bayi_png, hedef / f"{kod}_pafta_sablon.png", bayi_gorsel):
            if p.exists():
                p.replace(p.with_name(p.stem + ".HATALI" + p.suffix))
    validation = {"passed": passed, "errors": hatalar, "warnings": uyarilar, "kod": t["kod"], "set": set_kullanilan, "yontem": yontem or t.get("cati", {}).get("yontem"),
                  "ciktilar": {"beklenen": len(beklenen), "var": sum(var.values()), "eksik": eksik, "zorunlu_eksik": zorunlu_eksik}, "ifc": ozet,
                  "liste_satir": liste_satir, "elektrik_sayimi": str(elektrik_sayimi) if elektrik_sayimi else None,
                  "perspektif": pers, "sure_s": round(time.time() - t0, 1)}
    (hedef / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (hedef / "uret.log").write_text(gunluk.getvalue(), encoding="utf-8")
    manifest = {"motor": "genel", "kod": t["kod"], "is_emri_no": is_emri_no, "revizyon": revizyon, "passed": passed, "warnings": uyarilar,
                "pdf": pafta_pdf.name if pafta_pdf.exists() else None, "pdf_sha256": sha256(pafta_pdf) if pafta_pdf.exists() else None,
                "hatali_pdf": hatali_pdf.name if hatali_pdf.exists() else None,
                "ifc": ifc.name if ifc.exists() else None, "ifc_sha256": sha256(ifc) if ifc.exists() else None,
                "preview": f"{kod}_plan.png" if (hedef / f"{kod}_plan.png").exists() else None, "plan_bayi": bayi_png.name if bayi_png.exists() else None,
                "bayi_gorsel": bayi_gorsel.name if bayi_gorsel.exists() else None, "bilgi_var": bool(bilgi),
                "duzenlenebilir_dxf": dxf_yol.name if dxf_yol is not None and dxf_yol.exists() else None,
                "yukleme_json": liste.name if liste.exists() else None, "ciktilar": {d: v for d, v in var.items()}, "set": set_kullanilan,
                **({"duvar_panelleri": karkas_paftasi} if karkas_paftasi else {}),       # İE-16 PR-3a; karkas istemeyen tanımın manifest'i aynı
                **({"makaslar": makas_paftasi} if makas_paftasi else {})}                 # İE-16 PR-3b
    (hedef / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path); ap.add_argument("cikti", type=Path)
    ap.add_argument("--set", type=Path, default=None, help="kural seti dosyası (varsayılan: kurallar/liste/kurallar.json ya da PORTMAN_KURALLAR)")
    ap.add_argument("--yontem", choices=("panel", "omega_asik"))
    ap.add_argument("--perspektifsiz", action="store_true"); ap.add_argument("--bayisiz", action="store_true", help="bayi görseli ve şablon paftası üretme")
    ap.add_argument("--is-emri-no", default=None); ap.add_argument("--revizyon", type=int, default=1)
    ap.add_argument("--elektrik-sayimi", type=Path, default=None, help="elektrik paftasından sayım (JSON; kör testlerin listeleri için)")
    ap.add_argument("--karkas", type=Path, default=None, help="karkas kuralı (yalnız tanım `karkas: kural` isterse; varsayılan: kurallar/karkas/celik_karkas.json)")
    a = ap.parse_args()
    m = uret(a.tanim, a.cikti, is_emri_no=a.is_emri_no, revizyon=a.revizyon, set_yolu=a.set, yontem=a.yontem, perspektif=not a.perspektifsiz, bayi=not a.bayisiz,
             elektrik_sayimi=a.elektrik_sayimi, karkas_yolu=a.karkas)
    v = json.loads((a.cikti / "validation.json").read_text(encoding="utf-8"))
    print(f"{m['kod']}: {'geçti' if m['passed'] else 'GEÇMEDİ'} · çıktılar {v['ciktilar']['var']}/{v['ciktilar']['beklenen']} · IFC şema hatası {v['ifc'].get('sema_hatasi', '?')} · "
          f"liste {v['liste_satir']} satır · perspektif {v['perspektif']['durum']} · {v['sure_s']} s" + (f" · HATA: {'; '.join(m and v['errors'])}" if v["errors"] else "")
          + (f" · uyarı: {'; '.join(v['warnings'])}" if v["warnings"] else ""))
    return 0 if m["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
