"""İE-13 PR-2 · Teklif: İş Emri → Motor'un yükleme listesi → fiyat defteri → teklif Excel ve JSON. D-28: teklif yalnız bu komutla üretilir.

    python3 araclar/teklif.py <İş Emri.json> <çıktı klasörü> [--tavan asma,ters] [--kosullar <json>] [--defter <json>] [--oneri]

Liste dosyası almaz: listeyi İş Emri'nden Motor'la kendisi üretir (`motor/prefabrik_liste.is_emrinden`, paket üreteciyle ortak). Elle
düzeltilmiş liste giremez, adet düzeltmesi yoktur: düzeltme kural kitabına ya da İş Emri'ne işlenir (D-28). Fiyat `araclar/fiyatla.py`
ile defterden; fiyat uydurulmaz, fiyatı olmayan satır boş kalır ve sayılır. LLM yok, ağ yok.

- Proje kararları İş Emri'ndedir (D-28): isteğe bağlı `teklif` bölümü, `{"tavan": ["asma", "ters"], "kosullar": {...}}`. Motor bu
  bölümü okumaz.
- Seçenekler: İş Emri'nin `teklif.tavan`'ı ya da `--tavan asma,ters` (komut satırı İş Emri'nin üstüne yazar) her seçenekte İş Emri'nin
  tavanını değiştirir (TK-01: Patron 27 Ekim 13:49, asma tavanla fiyat, ters tavanla da); ikisi de yoksa İş Emri'nin kendi tavanıyla tek
  seçenek.
- Teklif koşulları (teslim süresi, ödeme şekli): genel değer `kurallar/teklif/kosullar.json`, üstüne İş Emri'nin `teklif.kosullar`'ı, onun
  üstüne `--kosullar` dosyası. Değer yoksa hücre sarı kalır ve "Patron'dan" yazar; değer uydurulmaz (Patron 28 Ekim 06:51: bayiye süre ve
  ödeme "teklifle birlikte bildirilir").
- Excel düzeni Patron'un yükleme listesinin düzeni (28 Ekim 06:40–06:41): grup adı sütun değil, grubun üstünde başlık satırı ve altında
  ara toplam; tek "Adet" sütunu; ölçüsü birim olan satırda (adet, metre, kova …) ölçü boş, birim o. Sayfalar: Özet, her seçenek bir
  sayfa, Fiyat kaynağı. Liste sayfasının yazıcısı `araclar/liste_excel.py`; `fiyatla.py --excel` de onu kullanır (tek yazıcı).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from araclar import fiyatla as F  # noqa: E402
from araclar.liste_excel import RENK, TL, _stil, buyuk, eksik, gorunen, liste_sayfasi, tl_yazi  # noqa: E402,F401
from motor import prefabrik_liste as PL  # noqa: E402

KOSULLAR = KOK / "kurallar" / "teklif" / "kosullar.json"
TAVAN = {"asma": "Asma", "ters": "Ters"}


def kaynak_durumu(s: dict, defter: dict, hat: str) -> tuple[str, dict | None]:
    """Satırın fiyatının defterdeki yeri: (durum, kayıt). Durum defterin `durum`'u (eşleşti, bant, öneri onaylı, ikinci kaynak, kaynakta
    yok, …), defterin bandıyla bulunduysa "bant", hiç yoksa "defterde yok"."""
    H = defter["hatlar"][hat]
    g = H["kalemler"].get(F.anahtar(s, hat))
    if g is not None:
        return g["durum"], g
    if hat == "prefabrik" and (b := F.bant_bul(s, H.get("bantlar") or [])):
        alt, ust = b[1]["en_mm"]
        return "bant", {"fiyat": b[1]["fiyat"], "kaynak": b[0]["kaynak"], "kaynak_satir": b[0].get("kaynak_satir"),
                        "kaynak_kalem": b[0].get("kaynak_kalem"), "onay": b[1]["onay"], "not": f"pano eni bandı {alt:g}–{ust:g} mm"}
    if hat == "prefabrik" and (bo := F.boy_onerisi_bul(s, H.get("boy_onerileri") or [])):
        return "boy önerisi", {"fiyat": bo[1], "kaynak": bo[0]["kaynak"], "kaynak_satir": bo[0].get("kaynak_satir"),
                               "kaynak_kalem": bo[0].get("kaynak_kalem"), "onay": bo[0]["onay"], "not": bo[0].get("dayanak")}
    return "defterde yok", None


def secenekler(ie: dict, tavan: list[str] | None) -> list[tuple[str, dict]]:
    tavan = tavan or (ie.get("teklif") or {}).get("tavan")
    if isinstance(tavan, str):                                  # İş Emri'nde "asma,ters" de olur (komut satırı gibi)
        tavan = [t.strip() for t in tavan.split(",") if t.strip()]
    if not tavan:                                               # Motor özellik adını küçük harfle okur; etiket de öyle
        t = next((v for k, v in (ie.get("ozellikler") or {}).items() if PL._kucuk(k) == "tavan"), None)
        return [(f"{t} tavan" if t else "Teklif", {})]
    bilinmeyen = [t for t in tavan if t not in TAVAN]
    if bilinmeyen or len(set(tavan)) != len(tavan):
        raise SystemExit(f"DUR: tavan seçeneği {tavan}; bilinenler {sorted(TAVAN)}, her biri bir kez")
    return [(f"{TAVAN[t]} tavan", {"Tavan": TAVAN[t]}) for t in tavan]


def kosullari_oku(ek: Path | str | None = None, ie: dict | None = None) -> dict:
    """Genel koşullar, üstüne İş Emri'nin `teklif.kosullar`'ı, onun üstüne `ek` dosyası. Genel dosyada olmayan koşul adı durur (yazım
    hatası yeni satır açmasın)."""
    K = dict(json.loads(KOSULLAR.read_text(encoding="utf-8"))["kosullar"])
    katmanlar = [((ie or {}).get("teklif") or {}).get("kosullar") or {}]
    if ek:
        d = json.loads(Path(ek).read_text(encoding="utf-8"))
        if not isinstance(d, dict) or not isinstance(d.get("kosullar"), dict):
            raise SystemExit(f'DUR: {ek}: koşullar {{"kosullar": {{...}}}} biçiminde verilir (kurallar/teklif/kosullar.json gibi)')
        katmanlar.append(d["kosullar"])
    for k in katmanlar:
        if bilinmeyen := sorted(set(k) - set(K)):
            raise SystemExit(f"DUR: bilinmeyen teklif koşulu {bilinmeyen}; bilinenler {sorted(K)}")
        K.update(k)
    return K


def uret(ie: dict, defter: dict, secim: list[tuple[str, dict]], kosullar: dict, oneri: bool = False) -> dict:
    """Her seçenek için Motor'un listesi ve fiyatı; teklifin JSON'u (zaman damgası yok: aynı girdi aynı çıktıyı verir)."""
    sec, kod = [], None
    for ad, oz in secim:
        L = PL.is_emrinden(ie, ozellikler=oz)
        kod = kod or L.get("kod")
        R = F.fiyatla(L, defter, "prefabrik", oneri)
        sec.append({"ad": ad, "ozellikler": oz, "liste": {k: L[k] for k in ("uretici_surum", "kural_seti", "girdi_ozeti", "ozet")}, "fiyat": R})
    return {"sema": "portman.teklif/1", "kod": kod or ie.get("is_emri_no"),
            "is_emri_no": ie.get("is_emri_no"), "revizyon": ie.get("revizyon"), "defter_surumu": defter.get("surum"),
            "oneri_dahil": oneri, "kosullar": kosullar, "secenekler": sec}


# ── Excel ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def uyari(o: dict) -> str:
    """Özet'te toplamın yanındaki uyarı (CIO, 28 Ekim): fiyatsız satır varsa toplam eksiktir; onay bekleyen önerilerin tutarı ayrıca."""
    if not o["fiyatsiz"]:
        return ""
    b = o.get("oneri_bekleyen") or {}
    return (f"{len(o['fiyatsiz'])} satır fiyatsız, toplam eksik"
            + (f"; {b['satir']} satırda onay bekleyen öneri var, onaylanırsa +{tl_yazi(b['tutar'])} TL" if b.get("satir") else ""))


def oneri_nedeni(f: dict, kayit: dict) -> str | None:
    """Fiyatı olmayan satırın Neden'i, onay bekleyen öneri varsa (sarı; toplama girmez): önerinin dayanağı defterdeki kaydın notu, boy
    önerisinde yöntem, bantta bant."""
    if f.get("oneri_fiyat") is None:
        return None
    yol = (kayit.get("not") or "defterdeki öneri") if kayit else ("tam boyun fiyatından boyla orantılı" if f["durum"].startswith("öneri boy")
                                                                  else "pano eni bandı")
    return f"öneri birim fiyat {tl_yazi(f['oneri_fiyat'])} TL ({yol}); onay bekliyor, toplama girmedi"


def excel_yaz(T: dict, defter: dict, yol: Path) -> None:
    from openpyxl import Workbook
    Alignment, Border, Font, dolgu, Side = _stil()
    B = Font(bold=True)
    kaynak_kisa = {k: v.get("kisa") for k, v in defter["kaynaklar"].items()}
    _kd: dict[str, tuple[str, dict | None]] = {}
    def kd(s: dict) -> tuple[str, dict | None]:             # defterdeki yeri, anahtar başına bir kez
        a = F.anahtar(s, "prefabrik")
        if a not in _kd:
            _kd[a] = kaynak_durumu(s, defter, "prefabrik")
        return _kd[a]
    def durum_renk(s: dict) -> str | None:
        if s["birim_fiyat"] is None:
            return "sari" if s.get("oneri_fiyat") is not None else "gri"   # onay bekleyen öneri: sarı, toplama girmez
        if s["durum"].startswith("öneri"):                  # onaysız öneri (yalnız --oneri ile)
            return "öneri"
        d = kd(s)[0]
        return d if d in ("öneri onaylı", "ikinci kaynak") else None
    wb = Workbook(); oz = wb.active; oz.title = "Özet"
    kimlik = f"{T['is_emri_no']} r{T['revizyon']:02d}" if isinstance(T.get("revizyon"), int) else str(T.get("is_emri_no"))
    acik = (f"İş Emri {kimlik}; liste Motor'dan, fiyat defterden ({T['defter_surumu']}"
            + ("; onaysız öneriler dahil" if T["oneri_dahil"] else "") + "). Fiyatı boş satır toplama girmez. "
            "Birim fiyat rengi: turuncu onaylı öneri, mavi Haziran malzeme listesi, sarı onay bekleyen öneri (Not'ta; toplama girmez), gri fiyat yok. "
            "Gri satır: Motor'da kuralı yok.")
    for sec in T["secenekler"]:
        liste_sayfasi(wb.create_sheet(sec["ad"]), sec["fiyat"], f"{T['kod']} · teklif · {sec['ad']} · TASLAK", acik, durum_renk)

    # Özet
    oz.append([f"{T['kod']} · teklif · TASLAK"]); oz["A1"].font = Font(bold=True, size=13)
    oz.append([acik]); oz["A2"].alignment = Alignment(wrap_text=True, vertical="top"); oz.merge_cells("A2:D2"); oz.row_dimensions[2].height = 32
    oz.append([])
    oz.append(["Seçenek", "Toplam", "Fiyatsız satır", "Satır", "Uyarı"])
    for c in oz[oz.max_row]: c.font = B
    for sec in T["secenekler"]:
        o = sec["fiyat"]["ozet"]
        oz.append([sec["ad"], o["toplam"], len(o["fiyatsiz"]), f"{o['satir']} satır, {o['fiyatli']} fiyatlı", uyari(o)])
        oz.cell(oz.max_row, 2).number_format = TL; oz.cell(oz.max_row, 2).font = B
        if o["fiyatsiz"]:                                   # CIO, 28 Ekim: toplamın eksik olduğu toplamın yanında belirgin
            oz.cell(oz.max_row, 5).font = Font(bold=True, color="C00000"); oz.cell(oz.max_row, 5).fill = dolgu["sari"]
    if len(T["secenekler"]) == 2:
        a, b = (s["fiyat"]["ozet"]["toplam"] for s in T["secenekler"])
        oz.append([f"Fark ({T['secenekler'][1]['ad']} − {T['secenekler'][0]['ad']})", round(b - a, 2)]); oz.cell(oz.max_row, 2).number_format = TL
    oz.append(["Toplam yalnız fiyatı olan satırların toplamıdır; fiyatı olmayan satırlar aşağıda."])
    oz.append([])
    oz.append(["Teklif koşulları", "Değer", "", "Açıklama"])
    for c in oz[oz.max_row]: c.font = B
    for k, v in T["kosullar"].items():
        oz.append([k, v or "", "", "" if v else "Patron'dan"])
        if not v: oz.cell(oz.max_row, 2).fill = dolgu["sari"]
    oz.append([])
    oz.append(["Fiyatın kaynağı"] + [s["ad"] for s in T["secenekler"]])
    for c in oz[oz.max_row]: c.font = B
    sayim = [{} for _ in T["secenekler"]]
    for i, sec in enumerate(T["secenekler"]):
        for s in sec["fiyat"]["satirlar"]:
            d = kd(s)[0]
            sayim[i][d] = sayim[i].get(d, 0) + 1
    for d in sorted({d for c in sayim for d in c}, key=lambda d: (d in ("kaynakta yok", "defterde yok"), d)):
        oz.append([d] + [c.get(d, 0) for c in sayim])
        if d in RENK: oz.cell(oz.max_row, 1).fill = dolgu[d]
    oz.append([])
    bos = [""] * (3 - len(T["secenekler"]))                 # Neden hep E sütununda (en çok üç seçenek)
    oz.append(["Fiyatı olmayan satırlar"] + [f"{s['ad']} adedi" for s in T["secenekler"]] + bos + ["Neden"])
    for c in oz[oz.max_row]: c.font = B
    adet = [{F.anahtar(s, "prefabrik"): s["adet"] for s in sec["fiyat"]["satirlar"]} for sec in T["secenekler"]]
    goruldu = set()
    for sec in T["secenekler"]:
        satir = {x["sira"]: x for x in sec["fiyat"]["satirlar"]}
        for f in sec["fiyat"]["ozet"]["fiyatsiz"]:
            if f["anahtar"] in goruldu: continue
            goruldu.add(f["anahtar"])
            kayit = defter["hatlar"]["prefabrik"]["kalemler"].get(f["anahtar"]) or {}
            neden = eksik(satir[f["sira"]]) or oneri_nedeni(f, kayit) or kayit.get("not") or f["durum"]
            oz.append([f["anahtar"].replace(" | ", " · ")] + [a.get(f["anahtar"]) for a in adet] + bos + [neden])
            oz.cell(oz.max_row, 1).fill = dolgu["sari" if f.get("oneri_fiyat") is not None else "gri"]
    oz.append([])
    oz.append(["Kaynaklar: " + "; ".join(v["kisa"] for v in defter["kaynaklar"].values() if v.get("patron_verdi")) + " (Patron'un verdiği listeler)."])
    for col, w in zip("ABCDE", (58, 16, 16, 22, 90)): oz.column_dimensions[col].width = w
    for row in oz.iter_rows(min_row=4):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=c.column in (1, 5))

    # Fiyat kaynağı: seçeneklerin anahtarları bir arada, defterdeki kaydıyla
    fk = wb.create_sheet("Fiyat kaynağı")
    fk.append(["Fiyatın defterdeki kaydı (kurallar/fiyat). Satır numarası kaynak listedeki Excel satırıdır."]); fk["A1"].font = B
    fk.append(["Kalem", "Ölçü"] + [f"{s['ad']} adedi" for s in T["secenekler"]] + ["Durum", "Birim fiyat", "Kaynak", "Kaynaktaki satır", "Kaynaktaki kalem", "Not"])
    for c in fk[2]: c.font = B
    sira: dict[str, dict] = {}                              # anahtar ilk göründüğü sırada
    for sec in T["secenekler"]:
        for s in sec["fiyat"]["satirlar"]:
            sira.setdefault(F.anahtar(s, "prefabrik"), s)
    for a, s in sira.items():
        d, g = kd(s); g = g or {}
        fk.append([s["kalem"], s["olcu"]] + [x.get(a) for x in adet] + [d, g.get("fiyat"), kaynak_kisa.get(g.get("kaynak")) or "",
                   ", ".join(map(str, g.get("kaynak_satir") or [])), g.get("kaynak_kalem") or "", g.get("not") or ""])
        if d in RENK: fk.cell(fk.max_row, len(T["secenekler"]) + 3).fill = dolgu[d]
        fk.cell(fk.max_row, len(T["secenekler"]) + 4).number_format = TL
    for col, w in zip("ABCDEFGHIJK", [52, 20] + [10] * len(T["secenekler"]) + [14, 12, 30, 12, 50, 60]): fk.column_dimensions[col].width = w
    fk.freeze_panes = "C3"
    oz.page_setup.orientation = fk.page_setup.orientation = "landscape"
    oz.sheet_properties.pageSetUpPr.fitToPage = True; oz.page_setup.fitToWidth, oz.page_setup.fitToHeight = 1, 0
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("is_emri", type=Path); a.add_argument("cikti", type=Path)
    a.add_argument("--tavan", help="seçenekler, virgülle: asma,ters")
    a.add_argument("--kosullar", type=Path, help="projeye özel teklif koşulları (kurallar/teklif/kosullar.json biçimi)")
    a.add_argument("--defter", type=Path, default=F.DEFTER); a.add_argument("--oneri", action="store_true")
    o = a.parse_args(argv)
    ie = json.loads(o.is_emri.read_text(encoding="utf-8"))
    secim = secenekler(ie, [t.strip() for t in o.tavan.split(",")] if o.tavan else None)
    defter = F.oku(o.defter)
    try:
        T = uret(ie, defter, secim, kosullari_oku(o.kosullar, ie), o.oneri)
    except PL.ListeYazilmaz as e:
        print(f"teklif: {e.neden}", file=sys.stderr)
        return 1
    kod = str(T["kod"]).replace("-", "")
    o.cikti.mkdir(parents=True, exist_ok=True)
    (o.cikti / f"{kod}_teklif.json").write_text(json.dumps(T, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    excel_yaz(T, defter, o.cikti / f"{kod}_teklif.xlsx")
    for sec in T["secenekler"]:
        oz = sec["fiyat"]["ozet"]
        print(f"{T['kod']} · {sec['ad']}: {oz['toplam']:,.2f} TL · {oz['fiyatli']}/{oz['satir']} satır fiyatlı, {len(oz['fiyatsiz'])} fiyatsız")
    print("koşullar:", ", ".join(f"{k} {v or 'yok (Patron’dan)'}" for k, v in T["kosullar"].items()))
    print("→", o.cikti / f"{kod}_teklif.xlsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
