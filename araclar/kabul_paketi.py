"""İE-08 Adım 8 · Kabul paketi (Lokman, 12 Ekim 2026; D-11, 13 Ekim): kabul eden yedi modeli tek oturumda görür, sonra yalnız kabul
ettiği kodlar `araclar/aday_kabul.py` ile Postgres'e yazılır. Geliştirme döneminde kabul eden Lokman'dır (D-11); bayi onayından sonraki
teknik kontrol (8b mühendis adımı) ayrıdır. Paket depoya girmez; Lokman'ın Mac'ine gider (33_IE08/).

    python3 araclar/kabul_paketi.py <çıktı klasörü> [--kodlar Ç8801,…] [--perspektifsiz] [--set <kural seti>]

Her model için `<klasör>/<kod>/`: bayi paftası PDF (`*_pafta.pdf`; antet "..." — paket kişi adı taşımaz), çizim seti (plan, görünüşler,
pafta PNG, perspektifler), bayi görseli (aday kartı), yükleme listesi (`*_yukleme.json` ve `.md`), IFC, `KISA_PARCALAR.md` (bayi
paftasında komşusuna katılan 15 cm ve daha kısa parçalar: `pafta_ozet.json › kontrol_notlari`; KT-03'ün 1–2 cm kaymaları dahil) ve
D-11'in (13 Ekim 2026) iki düzenlenebilir biçimi: `*_cizim.dxf` (plan + dört görünüş, katmanlı, cm; genel motor üretir) ve
`*_yukleme.xlsx` (yükleme listesi; openpyxl yalnız yerelde, sunucuda yok). İkisi de çıktıdır, kaynak değil: düzeltme tanıma ya da kural
kitabına işlenir, paket yeniden üretilir.
Üstte `README.md`: model indeksi, kısa parça sayıları, kabul formu (kod listesi + not). Tanımlar `beyin/veri/adaylar.json`'dan
(yoksa `modeller/`). Çizim kural setiyle (`--set`; yoksa güncel `kurallar.json`)."""
from __future__ import annotations
import argparse, json, shutil, sys, time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

TUTULAN = ("_plan.png", "_gorunusler.png", "_pafta.png", "_pafta.pdf", "_bayi_gorsel.png", "_plan_bayi.png", "_yukleme.json", "_yukleme.md", "_cizim.dxf",
           ".ifc", "_perspektif_on_sag.png", "_perspektif_on_sol.png", "_perspektif_arka_sag.png", "_perspektif_arka_sol.png", "_catisiz.png", "_makasli.png",
           "_pafta_ozet.json")


def kisa_parcalar_md(kod: str, gosterim: str, ozet: dict) -> str:
    n = ozet.get("kontrol_notlari") or []
    s = [f"# {gosterim} · bayi paftasında komşusuna katılan kısa parçalar", "",
         "Kural (Lokman, 12 Ekim 2026): \"Çelikte 15 cm parça çıkmaz.\" Bayi paftasının ölçü zincirinde 15 cm ve daha kısa parçalar komşusuna",
         "katılır; çizim seti (plan ve pafta PNG'si, DXF) tam zinciri taşır. Aşağıdakiler gerçek parça değil, dış yüz–aks farkı, kaplama",
         "ya da tanımdaki 1–2 cm kayma olabilir: lütfen ölçüyü kontrol edin.", ""]
    if not n:
        s.append("Bu modelde 15 cm ve daha kısa parça yok.")
    else:
        s += ["| Zincir | Parçanın bitiş konumu (zincir başından, cm) | Parça (cm) |", "|---|---|---|"]
        s += [f"| {x['zincir']} | {x['konum_cm']:g} | {x['parca_cm']:g} |" for x in n]
    s += ["", f"Bayi paftasındaki zincirler (cm): " + "; ".join(f"{k}: {v}" for k, v in (ozet.get("zincirler_cm") or {}).items()),
          f"Dış ölçü (dış yüzden): {ozet.get('dis_olcu_cm')} · brüt oturum {ozet.get('oturum_m2')} m²", ""]
    return "\n".join(s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cikti", type=Path); ap.add_argument("--kodlar", default="", help="yalnız bu kodlar (virgülle); yoksa adaylar.json'daki hepsi")
    ap.add_argument("--perspektifsiz", action="store_true"); ap.add_argument("--set", type=Path, default=None)
    a = ap.parse_args(argv)
    from motor.genel import uret as U
    from motor.genel import dxf_genel
    duz = dxf_genel.kurallar()                                             # D-11: kurallar/cizim/duzenlenebilir.json
    excel = (duz.get("excel") or {}).get("deger") or {}
    if excel:
        try:
            import openpyxl  # noqa: F401  (yalnız yerel; araclar/gereksinimler.txt)
        except ImportError:
            print("DUR: openpyxl yok; Excel yükleme listesi üretilemez (yerel: pip install -r araclar/gereksinimler.txt)"); return 2
    adaylar_yolu = KOK / "beyin" / "veri" / "adaylar.json"
    adaylar = [x for x in json.loads(adaylar_yolu.read_text(encoding="utf-8")) if x.get("motor") == "genel"] if adaylar_yolu.exists() else []
    from beyin.katalog import Katalog
    istenen = {Katalog.kod_normalize(k) for k in a.kodlar.split(",") if k.strip()}
    if istenen:
        adaylar = [x for x in adaylar if str(x["kod"]).upper() in istenen]
    if not adaylar:
        print("DUR: çelik aday kaydı yok (araclar/aday_kaydet.py --motor genel)"); return 2
    cikti = a.cikti; cikti.mkdir(parents=True, exist_ok=True)
    satirlar = []
    for x in adaylar:
        kod = str(x["kod"]); gosterim = x.get("gosterim") or kod
        klasor = kod.replace("Ç", "C")                                      # klasör adı ASCII (Mac/zip uyumu)
        tanim = KOK / x["tanim"]
        gecici = cikti / f".calisma_{klasor}"
        if gecici.exists():
            shutil.rmtree(gecici)
        t0 = time.time()
        m = U.uret(tanim, gecici, is_emri_no=None, revizyon=None, set_yolu=a.set, yontem="panel", perspektif=not a.perspektifsiz, bayi=True,
                   kaynak=f"Yapı Tanımı 0.5 ({tanim.name})")          # revizyon None: kartta "TASLAK" (seçimden önce r01 yok)
        v = json.loads((gecici / "validation.json").read_text(encoding="utf-8"))
        hedef = cikti / klasor; hedef.mkdir(parents=True, exist_ok=True)
        gk = U.kod_govde(json.loads(tanim.read_text(encoding="utf-8")))
        for p in sorted(gecici.iterdir()):
            if p.is_file() and any(p.name == f"{gk}{son}" for son in TUTULAN):
                shutil.copyfile(p, hedef / p.name)
        liste_yolu = gecici / f"{gk}_yukleme.json"
        xlsx = None
        if excel and liste_yolu.exists():                                   # D-11: yükleme listesinin Excel'i (yalnız kabul paketinde)
            from motor.genel import excel_liste
            xlsx = excel_liste.xlsx_yaz(json.loads(liste_yolu.read_text(encoding="utf-8")), hedef / str(excel.get("dosya") or "{kod}_yukleme.xlsx").format(kod=gk),
                                        kaynak=liste_yolu.name, set_adi=Path(str(m.get("set") or "")).name or None)
        dxf = hedef / m["duzenlenebilir_dxf"] if m.get("duzenlenebilir_dxf") else None
        ozet_yolu = gecici / f"{gk}_pafta_ozet.json"
        ozet = json.loads(ozet_yolu.read_text(encoding="utf-8")) if ozet_yolu.exists() else {}
        (hedef / "KISA_PARCALAR.md").write_text(kisa_parcalar_md(kod, gosterim, ozet), encoding="utf-8")
        shutil.rmtree(gecici)
        n_kisa = len(ozet.get("kontrol_notlari") or [])
        satirlar.append((kod, gosterim, x, v, n_kisa, round(time.time() - t0, 1), m))
        print(f"{gosterim}: {'geçti' if m.get('passed') else 'GEÇMEDİ'} · liste {v.get('liste_satir')} satır · perspektif {v.get('perspektif', {}).get('durum')} · kısa parça {n_kisa}"
              f" · DXF {'var' if dxf is not None and dxf.exists() else 'YOK'} · Excel {'var' if xlsx is not None and xlsx.exists() else 'YOK'} · {round(time.time() - t0, 1)} s")
    tarih = time.strftime("%Y-%m-%d")
    try:                                                                   # çatı tipi okunur adı (kural anahtarı); yoksa anahtar
        cati_adi = (json.loads((KOK / "kurallar" / "cizim" / "pafta_sablonu.json").read_text(encoding="utf-8")).get("cati_tipi_adi") or {}).get("deger") or {}
    except Exception:
        cati_adi = {}
    r = [f"# Çelik model bankası · kabul paketi ({tarih})", "",
         "İE-08 8a (D-08 madde 4, D-10). Yedi model genel motorla (Yapı Tanımı 0.5, kural kitabı) çizildi. Her klasörde: bayi paftası PDF",
         "(`*_pafta.pdf`, 2 sayfa; 8b kabulüne kadar TASLAK), çizim seti (plan, görünüşler, pafta, perspektifler), bayi görseli (`*_bayi_gorsel.png`),",
         "yükleme listesi (`*_yukleme.md/.json`), IFC ve `KISA_PARCALAR.md` (bayi paftasında komşusuna katılan ≤ 15 cm parçalar; kontrol notu).",
         "Düzenlenebilir iki biçim (D-11): `*_cizim.dxf` (plan + dört görünüş; katmanlar DUVAR, ACIKLIK, OLCU, YAZI, CATI; birim cm; AutoCAD'de açılır)",
         "ve `*_yukleme.xlsx` (yükleme listesi; renkli satırlar teyit bekliyor). İkisi de çıktıdır, kaynak değil: bir düzeltmeyi DXF ya da Excel'de",
         "gösterebilirsiniz, ama düzeltme dosyada kalmaz; tanıma (`modeller/*.json`, yeni sürüm, D-07) ya da kural kitabına (`kurallar/`) işlenir ve paket yeniden üretilir.",
         "Çizimler taslaktır, üretim projesi değildir. Paket bayi ve müşteri adı ya da numara taşımaz (antet \"...\").",
         "Kabul eden: geliştirme döneminde Lokman (D-11, 13 Ekim 2026); bayi onayından sonraki teknik kontrol (8b mühendis adımı) ayrıdır, bu paket onun yerine geçmez.", "",
         "| Kod | Model | Oda | Brüt oturum (m²) | Kapalı (m²) | Veranda (m²) | Çatı | Liste satırı | Kısa parça notu | Doğrulama |", "|---|---|---|---|---|---|---|---|---|---|"]
    for kod, gosterim, x, v, n_kisa, sure, m in satirlar:
        ad = "" if x.get("musteri_projesi") else (x.get("sunum") or {}).get("ad", "")
        cati = (x.get("sunum") or {}).get("cati_adi") or x.get("ozet", {}).get("cati") or ""
        cati = cati_adi.get(cati, cati)
        r.append(f"| {kod} (klasör {kod.replace('Ç', 'C')}) | {gosterim}{(' · ' + ad) if ad else ' (müşteri projesi; bayiye adsız)'} | {x.get('oda_programi')} | {x.get('katalog_m2'):g} | {x.get('kapali_m2')} | "
                 f"{x.get('veranda_m2')} | {cati} | {v.get('liste_satir')} | {n_kisa} | {'geçti' if m.get('passed') else 'GEÇMEDİ'} |")
    r += ["", "## Kabul formu", "",
          "Kabul edilen kodları (virgülle) ve notunuzu yazın; Lokman sunucuda `vps/ie08_adaylar.sh` ile kaydeder (yalnız kabul edilen kodlar bayiye sunulur):", "",
          "```", f"KABUL EDİLEN KODLAR: {', '.join(k for k, *_ in satirlar)}", "NOT:", "```", "",
          "Ç8801'in üç çatısı (katalog, K, L) aynı planın varyantlarıdır: bayiye tek görselde üç seçenek olarak gider; KT-01/02/03 bayiye kod, m² ve oda programıyla, adsız sunulur.", ""]
    (cikti / "README.md").write_text("\n".join(r), encoding="utf-8")
    print(f"paket: {cikti} · {len(satirlar)} model · README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
