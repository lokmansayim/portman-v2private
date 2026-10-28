"""İE-13 · Yükleme listesi × fiyat defteri (Z-10'un liste yöntemi) ve basit yöntemle (alan × m² fiyatı) yan yana fark.

    python3 araclar/fiyatla.py <liste.json> [--defter kurallar/fiyat/defter_2026-10.json] [--hat prefabrik|celik] [--oneri]
        [--duzeltme duzeltmeler.json] [--alan <m²> --m2-fiyat <TL/m²> [--esik <yüzde>]] [--json <çıktı.json>] [--excel <çıktı.xlsx>]

Liste: prefabrik Motor'un listesi (`motor/prefabrik_liste.py`, satırda `olcu`) ya da genel motorun yükleme listesi
(`python -m motor.genel.uret` → `<kod>_yukleme.json`, satırda `boyut`); hat satırlardan anlaşılır. Anahtar defterdeki gibi
"kalem | ölçü" (çelikte "kalem | boyut"). Önce birebir anahtar, yoksa (prefabrikte) pano eni bandı, o da yoksa boy önerisi (kesilen
profilin tam boyunun fiyatından boyla orantılı; `boy_onerileri`). Birimi `kg` olan kalemde tutar satırın kg'ı × fiyat, öteki kalemlerde
adet × fiyat.

Fiyat uydurulmaz: defterde `onay: false` olan fiyat (yedek kaynaktan öneri) yalnız `--oneri` ile uygulanır ve "öneri" diye
işaretlenir; fiyatı olmayan satır boş kalır, özette sayılır. Uygulanmayan önerinin birim fiyatı satırda `oneri_fiyat` olarak durur
(toplama girmez; teklif sarı gösterir, özette `oneri_bekleyen`). Defterde kaydı olan anahtar yalnız kendi kaydıyla fiyatlanır, banda
düşmez. Basit yöntemin m² fiyatı defterde henüz yok: `--alan` ve `--m2-fiyat` ile verilir; verilmezse fark hesaplanmaz. `--esik` verilirse fark eşiği aşınca UYARI yazar (Z-10: eşik dışında mühendis inceler; eşik henüz
kararla konmadı, varsayılan yok).
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
DEFTER = KOK / "kurallar" / "fiyat" / "defter_2026-10.json"


def oku(p: Path | str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def hat_bul(L: dict) -> str:
    return "celik" if any("boyut" in s for s in L.get("satirlar", [])) else "prefabrik"


def anahtar(s: dict, hat: str) -> str:
    return f"{s['kalem']} | {s['boyut'] if hat == 'celik' else s['olcu']}"


def _sayilar(olcu: str) -> list[float]:
    return [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", olcu or "")]


def bant_bul(s: dict, bantlar: list[dict]) -> tuple[dict, dict] | None:
    """Pano eni bandı: "<kalınlık> × <en> × <yükseklik>" ölçüsünde en, kalemin aralıklarından birine düşerse (bant, aralık).
    Onaya bakmaz; aralığın `onay`ını çağıran değerlendirir."""
    n = _sayilar(s.get("olcu", ""))
    if len(n) != 3:
        return None
    for b in bantlar:
        if b["kalem"] != s.get("kalem") or n[0] != b["kalinlik_mm"] or n[2] != b["yukseklik_mm"]:
            continue
        for a in b["araliklar"]:
            alt, ust = a["en_mm"]
            if (n[1] > alt if a.get("alt_haric") else n[1] >= alt) and n[1] <= ust:
                return b, a
    return None


def boy_onerisi_bul(s: dict, oneriler: list[dict]) -> tuple[dict, float] | None:
    """Kesilen profilin boyu (ölçü "L <mm>"): kaydın tam boy fiyatından boyla orantılı birim fiyat, tam TL'ye yarım yukarı (kayıt, fiyat).
    Defterdeki onaylı kiriş boyları (1200, 1710, 2510, 3760) bu yöntemle hesaplanmıştı; kaydı olmayan boy için yalnız öneridir."""
    olcu = (s.get("olcu") or "").strip()
    if not re.fullmatch(r"L \d+(?:[.,]\d+)?", olcu):
        return None
    n = _sayilar(olcu)[0]
    for b in oneriler:
        if b["kalem"] == s.get("kalem"):
            return b, float(int(b["fiyat"] * n / b["boy_mm"] + 0.5))
    return None


def duzelt(L: dict, duzeltmeler: list[dict], hat: str) -> dict:
    """Patron'un adet düzeltmeleri (teklif çalışmasının duzeltmeler.json biçimi: [{"anahtar", "adet", ...}]) listenin kopyasına."""
    L = json.loads(json.dumps(L))
    for d in duzeltmeler:
        hedef = [s for s in L["satirlar"] if anahtar(s, hat) == d["anahtar"]]
        if len(hedef) != 1:
            raise SystemExit(f"DUR: düzeltme anahtarı listede {len(hedef)} satıra denk geliyor: {d['anahtar']}")
        hedef[0]["adet"] = d["adet"]
    return L


def fiyatla(L: dict, defter: dict, hat: str | None = None, oneri: bool = False) -> dict:
    """Her satıra fiyat, tutar ve kaynak; özet (toplam, grup toplamları, fiyatsız satırlar). Listeyi değiştirmez."""
    hat = hat or hat_bul(L)
    H = defter["hatlar"][hat]
    kalemler, atla = H["kalemler"], set(H.get("atla") or [])
    satirlar, gruplar, fiyatsiz = [], {}, []
    toplam = onayli = oneri_toplam = 0.0
    bekleyen = {"satir": 0, "tutar": 0.0}                       # uygulanmayan öneriler (toplama girmez)
    for i, s in enumerate(L["satirlar"], 1):
        if s.get("kalem") in atla:
            continue
        k = anahtar(s, hat)
        g = kalemler.get(k)
        fiyat = tutar = oneri_fiyat = None
        durum, kaynak, birim = "fiyat yok", None, (g or {}).get("birim") or s.get("birim")
        if g is not None:                                          # defterde kaydı olan anahtar kendi kaydıyla; banda düşmez
            if g.get("fiyat") is not None and (g["onay"] or oneri):
                fiyat, kaynak, durum = g["fiyat"], g["kaynak"], ("onaylı" if g["onay"] else "öneri")
            elif g.get("fiyat") is not None:
                durum, oneri_fiyat = "öneri, onay bekliyor", g["fiyat"]
        elif hat == "prefabrik" and (b := bant_bul(s, H.get("bantlar") or [])):
            if b[1]["onay"] or oneri:
                fiyat, kaynak, durum = b[1]["fiyat"], b[0]["kaynak"], ("onaylı bant" if b[1]["onay"] else "öneri bant")
            else:
                durum, oneri_fiyat = "öneri bant, onay bekliyor", b[1]["fiyat"]
        elif hat == "prefabrik" and (bo := boy_onerisi_bul(s, H.get("boy_onerileri") or [])):
            if bo[0]["onay"] or oneri:
                fiyat, kaynak, durum = bo[1], bo[0]["kaynak"], ("onaylı boy" if bo[0]["onay"] else "öneri boy")
            else:
                durum, oneri_fiyat = "öneri boy, onay bekliyor", bo[1]
        else:
            durum = "defterde yok"
        miktar = s.get("kg") if birim == "kg" else s.get("adet")
        if fiyat is not None and miktar is None:                    # fiyat var, miktar yok: satır onaylı görünmesin
            durum = f"{durum}; {'kg' if birim == 'kg' else 'adet'} yok"
        if fiyat is not None and miktar is not None:
            tutar = round(miktar * fiyat, 2)
            toplam += tutar
            if durum.startswith("onaylı"):
                onayli += tutar
            else:
                oneri_toplam += tutar
            grup = f"{s['grup']} {s['grup_adi']}" if s.get("grup_adi") else str(s.get("grup"))
            gruplar[grup] = round(gruplar.get(grup, 0.0) + tutar, 2)
        elif miktar != 0:                                          # adedi 0 olan satır sessiz geçer; adedi yok (kural yok) olan sayılır
            if miktar is None and fiyat is None:
                durum = f"{durum}; {'kg' if birim == 'kg' else 'adet'} yok"
            fiyatsiz.append({"sira": i, "anahtar": k, "miktar": miktar, "durum": durum, **({"oneri_fiyat": oneri_fiyat} if oneri_fiyat is not None else {})})
            if oneri_fiyat is not None and miktar is not None:
                bekleyen["satir"] += 1
                bekleyen["tutar"] += miktar * oneri_fiyat
        satirlar.append({"sira": i, "grup": s.get("grup"), "grup_adi": s.get("grup_adi"), "kalem": s["kalem"], "olcu": s.get("boyut") if hat == "celik" else s.get("olcu"),
                         "birim": birim, "adet": s.get("adet"), "kg": s.get("kg"), "birim_fiyat": fiyat, "tutar": tutar,
                         "durum": durum, "kaynak": kaynak, "kaynak_adi": (defter["kaynaklar"].get(kaynak) or {}).get("kisa") if kaynak else None,
                         **({"oneri_fiyat": oneri_fiyat} if oneri_fiyat is not None else {})})
    return {"hat": hat, "defter_surumu": defter.get("surum"), "oneri_dahil": oneri, "satirlar": satirlar,
            "ozet": {"toplam": round(toplam, 2), "onayli_fiyatlarla": round(onayli, 2), "onerilerle": round(oneri_toplam, 2),
                     "satir": len(satirlar), "fiyatli": sum(1 for x in satirlar if x["tutar"] is not None),
                     "fiyatsiz": fiyatsiz, "oneri_bekleyen": {"satir": bekleyen["satir"], "tutar": round(bekleyen["tutar"], 2)}, "gruplar": gruplar}}


def m2_kiyasi(liste_toplami: float, alan: float, m2_fiyat: float, esik: float | None = None) -> dict:
    """Basit yöntem alan × m² fiyatı; fark liste yönteminin basitten sapması (yüzde)."""
    basit = round(alan * m2_fiyat, 2)
    fark = round((liste_toplami - basit) / basit * 100, 1) if basit else None
    return {"alan_m2": alan, "m2_fiyat": m2_fiyat, "basit_toplam": basit, "liste_toplam": round(liste_toplami, 2),
            "fark_yuzde": fark, "esik_yuzde": esik, "uyari": bool(esik is not None and fark is not None and abs(fark) > esik)}


def excel_yaz(R: dict, yol: Path, baslik: str) -> None:
    """Fiyatlı liste, teklifin liste sayfasıyla aynı yazıcıdan (`araclar/liste_excel.liste_sayfasi`; tek düzen, İE-13 PR-2) ve Durum,
    Kaynak sütunlarıyla. Birim fiyatı öneri ya da fiyatsız olan satırın birim fiyat hücresi sarı."""
    from openpyxl import Workbook
    if str(KOK) not in sys.path:
        sys.path.insert(0, str(KOK))
    from araclar.liste_excel import liste_sayfasi
    wb = Workbook(); ws = wb.active; ws.title = "Fiyatlı liste"
    liste_sayfasi(ws, R, baslik, f"Defter {R['defter_surumu']}; fiyatı boş satır toplama girmez.",
                  lambda s: "sari" if s["tutar"] is None or not s["durum"].startswith("onaylı") else None, kaynak_sutunu=True)
    if R.get("m2"):
        m = R["m2"]
        ws.append([f"Basit yöntem: {m['alan_m2']} m² × {m['m2_fiyat']} = {m['basit_toplam']:,.2f} TL · liste yönteminin farkı %{m['fark_yuzde']}"])
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("liste"); a.add_argument("--defter", default=str(DEFTER)); a.add_argument("--hat", choices=["prefabrik", "celik"])
    a.add_argument("--oneri", action="store_true"); a.add_argument("--alan", type=float); a.add_argument("--m2-fiyat", type=float)
    a.add_argument("--esik", type=float); a.add_argument("--json"); a.add_argument("--excel"); a.add_argument("--duzeltme")
    o = a.parse_args(argv)
    L, D = oku(o.liste), oku(o.defter)
    if o.duzeltme:
        L = duzelt(L, json.loads(Path(o.duzeltme).read_text(encoding="utf-8")), o.hat or hat_bul(L))
    R = fiyatla(L, D, o.hat, o.oneri)
    if o.alan and o.m2_fiyat:
        R["m2"] = m2_kiyasi(R["ozet"]["toplam"], o.alan, o.m2_fiyat, o.esik)
    oz = R["ozet"]
    ad = L.get("kod") or L.get("ad") or Path(o.liste).stem
    print(f"{ad} · {R['hat']} · defter {R['defter_surumu']}{' · öneriler dahil' if o.oneri else ''}")
    print(f"  toplam {oz['toplam']:,.2f} TL (onaylı fiyatlarla {oz['onayli_fiyatlarla']:,.2f}, önerilerle {oz['onerilerle']:,.2f}) · "
          f"{oz['fiyatli']}/{oz['satir']} satır fiyatlı, {len(oz['fiyatsiz'])} satır fiyatsız")
    for f in oz["fiyatsiz"]:
        print(f"  fiyatsız: {f['anahtar']} ({f['durum']}, miktar {f['miktar']})")
    if R.get("m2"):
        m = R["m2"]
        print(f"  basit yöntem: {m['alan_m2']} m² × {m['m2_fiyat']:,.2f} = {m['basit_toplam']:,.2f} · liste yöntemi farkı %{m['fark_yuzde']}"
              + (f" · UYARI: eşik %{m['esik_yuzde']} aşıldı, mühendis incelemeli" if m["uyari"] else ""))
    else:
        print("  basit yöntem: alan ve m² fiyatı verilmedi (defterde m² fiyatı yok), fark hesaplanmadı")
    if o.json:
        Path(o.json).parent.mkdir(parents=True, exist_ok=True)
        Path(o.json).write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if o.excel:
        excel_yaz(R, Path(o.excel), f"{ad} · fiyatlı yükleme listesi · TASLAK · defter {R['defter_surumu']} · sarı satır: öneri ya da fiyatsız")
    return 0


if __name__ == "__main__":
    sys.exit(main())
