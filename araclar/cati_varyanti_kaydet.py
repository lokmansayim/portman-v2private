"""İE-37 (D-83) · Prefabrik evin çatı seçenekleri: aday kaydındaki evin şablonu → her çatı için şablon (yalnız `cati` değişir) → Motor
koşumu (doğrulama geçmeli, K23) → çatı görseli (ön ve sol görünüş) → kayıt `beyin/veri/cati_varyantlari/<taban>.json`.

    python3 araclar/cati_varyanti_kaydet.py --taban PA-06 --karar D-83 --cati-adi "Beşik, kalkan önde" \\
        --varyant K "Kırma" '{"tip": "kirma", ...}' --varyant C "Beşik + salonda cumba" '{"tip": "besik_cumba", ...}' [--kaynak "…"]

Yazdıkları: is_emri/adaylar/<taban>_cati.png (evin kendi çatısı), is_emri/adaylar/<taban><harf>.json (şablon; is_emri_no PM-ADAY-<kod>,
yapi.referans_model bayinin gördüğü kod), is_emri/adaylar/<taban><harf>.png (çatı görseli), beyin/veri/cati_varyantlari/<taban>.json.
Ev başına bir dosya: evin kaydı (`adaylar_prefabrik.json`, referans girdi) değişmez; Katalog seçenekleri evin kaydına bellekte bağlar.
Seçenek `gecerli` yazılır, yalnız Lokman'ın kararıyla (`--karar D-NN`; karar dosyası her seçeneğin kodunu yazar, İE-36 kuralı). Bayiye
sunulma yine K-A10 kabul kaydına bağlıdır (her kod ayrı). Plan aynı kalmalı: Motor'un brüt alanı ve pano sayısı evinkiyle aynı değilse durur.
LLM, ağ ve sunucu yok.
"""
from __future__ import annotations
import argparse, copy, json, re, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

VARYANT_DIR = KOK / "beyin" / "veri" / "cati_varyantlari"
ADAY_DIR = KOK / "is_emri" / "adaylar"
EVDEN = ("yapi_turu", "kat", "oda_programi", "katalog_m2", "kapali_m2", "veranda_m2", "ozet")   # plan aynı: evin kaydından


def ciz(ie: dict, png: Path) -> dict:
    """Motor'u geçici klasörde koşar (doğrulama geçmezse durur), PDF'in ön ve sol görünüşünden çatı görselini yazar; özet döner."""
    from motor import dxf_out, bayi_gorseli as BG, geometry as G, prefabrik_liste as PL
    with tempfile.TemporaryDirectory() as tmp:
        yerler: dict = {}
        m = dxf_out.uret(ie, Path(tmp), bolge_yerleri=yerler)
        if not m.get("validation_passed") or not m.get("pdf"):
            raise SystemExit(f"DUR: {ie.get('is_emri_no')} Motor doğrulamasından geçmedi (K23); uyarılar: {m.get('warnings')}")
        BG.cati_gorseli(Path(tmp) / m["pdf"], yerler, png)
        plan = G.kur(ie)
        return {"brut_cm2": round(PL.bina_brut_cm2(plan)), "pano": len(plan.panolar), "uyarilar": list(m.get("warnings") or [])}


def main() -> int:
    from beyin.katalog import Katalog, ADAYLAR_PREFABRIK_JSON, SABLON_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--taban", required=True, help="evin kodu (ör. PA-06)")
    ap.add_argument("--karar", required=True, help="Lokman'ın kararı (KARARLAR/<D-NN>.md; her seçeneğin kodunu yazar)")
    ap.add_argument("--cati-adi", required=True, help="evin kendi çatısının adı (bayinin kartında)")
    ap.add_argument("--varyant", nargs=3, action="append", metavar=("HARF", "AD", "CATI_JSON"), required=True)
    ap.add_argument("--kaynak", default="")
    a = ap.parse_args()
    taban = Katalog.kod_normalize(a.taban)
    ev = next((x for x in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8")) if str(x.get("kod")).upper() == taban), None)
    if ev is None or not ev.get("sablon"):
        print(f"DUR: {a.taban} prefabrik aday kaydında yok"); return 2
    karar_yolu = KOK / "KARARLAR" / f"{a.karar}.md" if re.fullmatch(r"D-\d{2,3}", a.karar) else None
    karar_metni = karar_yolu.read_text(encoding="utf-8").upper() if karar_yolu and karar_yolu.exists() else ""
    gosterim_taban = str(ev.get("gosterim") or ev["kod"])
    harfler = [h.upper() for h, _ad, _c in a.varyant]
    if len(set(harfler)) != len(harfler) or not all(re.fullmatch(r"[A-Z]", h) for h in harfler):
        print("DUR: her seçeneğin harfi tek büyük harf ve farklı olur"); return 2
    for h in harfler:
        if f"{gosterim_taban}-{h}".upper() not in karar_metni:
            print(f"DUR: {a.karar} {gosterim_taban}-{h} kodunu yazmıyor (seçenek yalnız Lokman'ın kararıyla; İE-36 kuralı)"); return 2
    sablon = json.loads((SABLON_DIR / ev["sablon"]).read_text(encoding="utf-8"))
    ev_png = ADAY_DIR / f"{taban}_cati.png"
    ev_ozet = ciz(sablon, ev_png)
    print(f"{gosterim_taban}: evin çatısı {sablon.get('cati', {}).get('tip')}, brüt {ev_ozet['brut_cm2']} cm², {ev_ozet['pano']} pano → {ev_png.relative_to(KOK)}")
    varyantlar = []
    for h, ad, cati_json in a.varyant:
        h = h.upper(); kod = f"{taban}{h}"; gosterim = f"{gosterim_taban}-{h}"
        ie = copy.deepcopy(sablon)
        ie["cati"] = json.loads(cati_json)
        ie["is_emri_no"] = f"PM-ADAY-{kod}"
        ie.setdefault("yapi", {})["referans_model"] = gosterim
        png = ADAY_DIR / f"{kod}.png"
        oz = ciz(ie, png)
        if (oz["brut_cm2"], oz["pano"]) != (ev_ozet["brut_cm2"], ev_ozet["pano"]):
            print(f"DUR: {gosterim} planı evinkinden farklı (brüt {oz['brut_cm2']} ↔ {ev_ozet['brut_cm2']} cm², pano {oz['pano']} ↔ "
                  f"{ev_ozet['pano']}); çatı seçeneği planı değiştirmez"); return 2
        (ADAY_DIR / f"{kod}.json").write_text(json.dumps(ie, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        varyantlar.append({"kod": kod, "gosterim": gosterim, "durum": "gecerli", "taban": taban, "sablon": f"adaylar/{kod}.json",
                           "gorsel": f"adaylar/{kod}.png", "cati_adi": ad, "referans_model": gosterim,
                           **{k: copy.deepcopy(ev[k]) for k in EVDEN if k in ev},
                           "uyarilar": [u for u in oz["uyarilar"] if u not in ev_ozet["uyarilar"]],
                           "kaynak": {"metin": a.kaynak, "karar": a.karar, "ev": gosterim_taban}})
        print(f"{gosterim}: {ad} ({ie['cati'].get('tip')}) → {png.relative_to(KOK)}; yeni uyarı: {varyantlar[-1]['uyarilar'] or 'yok'}")
    kayit = {"taban": taban, "cati_adi": a.cati_adi, "cati_gorsel": f"adaylar/{taban}_cati.png", "karar": a.karar, "varyantlar": varyantlar}
    VARYANT_DIR.mkdir(parents=True, exist_ok=True)
    yol = VARYANT_DIR / f"{taban}.json"
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"kayıt: {yol.relative_to(KOK)} ({len(varyantlar)} seçenek)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
