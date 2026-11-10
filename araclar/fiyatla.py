"""İE-13 · Yükleme listesi × fiyat defteri (Z-10'un liste yöntemi) ve basit yöntemle (alan × m² fiyatı) yan yana fark.

    python3 araclar/fiyatla.py <liste.json> (--crm <CRM anlık görüntüsü.json> | --defter <eski defter.json>) [--hat prefabrik|celik]
        [--oneri] [--duzeltme duzeltmeler.json] [--alan <m²> --m2-fiyat <TL/m²> [--esik <yüzde>]] [--json <çıktı.json>] [--excel <çıktı.xlsx>]

Fiyat kaynağı (D-72, mühür M-15; Lokman 9 Kasım 2026 13:10 "bundan sonra tek fiyat kaynağımız bu api olacak"): yeni fiyat yalnız CRM'den,
`--crm` sunucunun günlük çektiği anlık görüntüyle (`araclar/crm_fiyat.py` onu defter şemasına çevirir). `--defter` yalnız kapanmış teklifi
o günkü defteriyle aynen vermek içindir (TK-04 r08, TK-05: `defter_2026-11.json`). İkisi de yoksa araç durur; varsayılan defter yok.

Liste: prefabrik Motor'un listesi (`motor/prefabrik_liste.py`, satırda `olcu`) ya da genel motorun yükleme listesi
(`python -m motor.genel.uret` → `<kod>_yukleme.json`, satırda `boyut`); hat satırlardan anlaşılır. Anahtar defterdeki gibi
"kalem | ölçü" (çelikte "kalem | boyut"). Önce birebir anahtar, yoksa (prefabrikte) pano eni bandı, o da yoksa boy kuralı (kesilen
profilin ya da panelin tam boyunun fiyatından boyla orantılı; `boy_onerileri`; D-36'ten beri kutu profil ve tek kat çatı paneli
onaylı), o da yoksa makas kuralı (makasın kg'ı saçaktan saçağa boyuyla orantılı × kg fiyatı; `makas_kurali`; D-37). Birimi `kg` olan
kalemde tutar satırın kg'ı × fiyat, öteki kalemlerde adet × fiyat.

KDV (D-76): CRM'den üretilen defter kayıtlarında KDV oranını taşır (`araclar/crm_fiyat.kdv_bul`; defterin `kdv`'si sözlük). O zaman
fiyatlı her satır `kdv_orani`, `kdv_grubu`, `kdv_tutari` (tutar × oran, kuruşa), özet `kdv` (KDV hariç, oranlara göre KDV, KDV dahil, oranı
olmayan satırlar) taşır. Oranı olmayan satırın KDV'si boş kalır, KDV dahil toplam eksik sayılır; oran uydurulmaz. Eski defterle
(`--defter`, KDV'siz) çıktı aynen eskisi gibidir.

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
DEFTER = KOK / "kurallar" / "fiyat" / "defter_2026-11.json"   # son elle defter (r13); D-72'den beri varsayılan değil: kapanmış teklif --defter ile
KAYNAK_YOK = ("DUR: fiyat yalnız CRM'den (D-72, M-15): --crm <CRM anlık görüntüsü> verin; kapanmış teklifi aynen vermek için "
              "--defter <o günkü defter>")


def defter_sec(crm: Path | str | None = None, defter: Path | str | None = None) -> dict:
    """Fiyat kaynağı (D-72, M-15): `crm` verilirse CRM anlık görüntüsünden defter (`araclar/crm_fiyat.defter_uret`), `defter` verilirse
    o dosya (kapanmış teklif). İkisi birden ya da hiçbiri verilmez: varsayılan kaynak yok, yeni teklif sessizce eski listeden fiyatlanmaz."""
    if crm and defter:
        raise SystemExit("DUR: --crm ve --defter birlikte verilmez; yeni teklif --crm, kapanmış teklif --defter")
    if defter:
        return oku(defter)
    if not crm:
        raise SystemExit(KAYNAK_YOK)
    if str(KOK) not in sys.path:
        sys.path.insert(0, str(KOK))
    from araclar import crm_fiyat
    try:
        return crm_fiyat.defter_uret(crm_fiyat.anlik_oku(crm))
    except crm_fiyat.CrmHatasi as e:
        raise SystemExit(f"DUR: CRM anlık görüntüsü: {e}") from None


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
    """Kesilen parçanın boyu (ölçü "L <mm>"): kaydın tam boy fiyatından boyla orantılı birim fiyat (kayıt, fiyat). Kayıt kalemi adıyla
    (`kalem`) ya da adının başıyla (`kalem_baslar`; ör. her çatının tek kat paneli) eşler; yuvarlama `yuvarlama` adımına yarım yukarı
    (varsayılan tam TL). Kaydın `onay`ını çağıran değerlendirir: D-36'ten beri (Lokman 31 Ekim) kutu profil ve tek kat çatı paneli
    kuralı onaylı, her boy için. Kayıt `kapatma_m` taşıyorsa (D-51, trapez sac) fiyat satırın kapatmasıyla da orantılıdır (m² fiyatı
    aynı): satırın `kapatma_m`'si yoksa kural uygulanmaz."""
    olcu = (s.get("olcu") or "").strip()
    if not re.fullmatch(r"L \d+(?:[.,]\d+)?", olcu):
        return None
    n, kalem = _sayilar(olcu)[0], s.get("kalem") or ""
    for b in oneriler:
        if b.get("kalem") == kalem or ("kalem_baslar" in b and kalem.startswith(b["kalem_baslar"])):
            adim = b.get("yuvarlama", 1)
            oran = 1.0
            if "kapatma_m" in b:                                 # D-51 (Lokman 4 Kasım 2026 21:37): kapatması farklı sacın m² fiyatı aynı;
                if not s.get("kapatma_m"):                       # satırın kapatması yoksa fiyat uydurulmaz
                    return None
                oran = s["kapatma_m"] / b["kapatma_m"]
            return b, float(round(int(b["fiyat"] * n / b["boy_mm"] * oran / adim + 0.5) * adim, 2))
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


def makas_bul(s: dict, kural: dict | None) -> tuple[dict, float, float] | None:
    """Makas satırının (adı kuralın `kalem_baslar`'ından biriyle başlar) kg'ı ve birim fiyatı: (kural, fiyat, kg). Boy saçaktan saçağa:
    "L <mm>" satırında L, "açıklık <mm>" satırında açıklık + 2 × `sacak_mm`. kg = `kg_m` × boy (kuruşa), fiyat = kg × `kg_fiyat`
    (tam TL'ye yarım yukarı). D-37 (Lokman 31 Ekim): TK-03'ün gerçek listesinden makasın metresine 5,50 kg."""
    if not kural:
        return None
    kalem, olcu = s.get("kalem") or "", (s.get("olcu") or "").strip()
    if not any(kalem.startswith(b) for b in kural["kalem_baslar"]):
        return None
    m = re.fullmatch(r"(L|açıklık) (\d+(?:[.,]\d+)?)", olcu)
    if not m:
        return None
    boy = float(m.group(2).replace(",", ".")) + (2 * kural["sacak_mm"] if m.group(1) == "açıklık" else 0)
    kg = round(int(kural["kg_m"] * boy / 10 + 0.5) / 100, 2)
    return kural, float(int(kg * kural["kg_fiyat"] + 0.5)), kg


# Teklifte yazılan ad ve ölçü (defter kaydında varsa; r09, Lokman 4 Kasım 23:24 "'METAL TAHTA L:2800 (GALVANİZ)' Yaz"): satıra geçer; iç ad
# (`kalem`), ölçü ve anahtar aynı kalır. Fiyatlı liste ve teklif (Excel, PDF) bu ikisini gösterir (`liste_excel`, `teklif_pdf`).
YAZILAN = ("teklif_adi", "teklif_olcu")


def fiyatla(L: dict, defter: dict, hat: str | None = None, oneri: bool = False) -> dict:
    """Her satıra fiyat, tutar ve kaynak; özet (toplam, grup toplamları, fiyatsız satırlar). Listeyi değiştirmez."""
    hat = hat or hat_bul(L)
    H = defter["hatlar"][hat]
    kalemler, atla = H["kalemler"], set(H.get("atla") or [])
    satirlar, gruplar, fiyatsiz = [], {}, []
    toplam = onayli = oneri_toplam = 0.0
    kdv_kip = isinstance(defter.get("kdv"), dict)              # D-76: CRM defteri kayıtta oran taşır
    bekleyen = {"satir": 0, "tutar": 0.0}                       # uygulanmayan öneriler (toplama girmez)
    for i, s in enumerate(L["satirlar"], 1):
        if s.get("kalem") in atla:
            continue
        k = anahtar(s, hat)
        g = kalemler.get(k)
        fiyat = tutar = oneri_fiyat = kayit = None
        durum, kaynak, birim = "fiyat yok", None, (g or {}).get("birim") or s.get("birim")
        if g is not None:                                          # defterde kaydı olan anahtar kendi kaydıyla; banda düşmez
            if g.get("fiyat") is not None and (g["onay"] or oneri):
                fiyat, kaynak, durum, kayit = g["fiyat"], g["kaynak"], ("onaylı" if g["onay"] else "öneri"), g
            elif g.get("fiyat") is not None:
                durum, oneri_fiyat = "öneri, onay bekliyor", g["fiyat"]
        elif hat == "prefabrik" and (b := bant_bul(s, H.get("bantlar") or [])):
            if b[1]["onay"] or oneri:
                fiyat, kaynak, durum, kayit = b[1]["fiyat"], b[0]["kaynak"], ("onaylı bant" if b[1]["onay"] else "öneri bant"), b[1]
            else:
                durum, oneri_fiyat = "öneri bant, onay bekliyor", b[1]["fiyat"]
        elif hat == "prefabrik" and (bo := boy_onerisi_bul(s, H.get("boy_onerileri") or [])):
            if bo[0]["onay"] or oneri:
                fiyat, kaynak, durum, kayit = bo[1], bo[0]["kaynak"], ("onaylı boy" if bo[0]["onay"] else "öneri boy"), bo[0]
            else:
                durum, oneri_fiyat = "öneri boy, onay bekliyor", bo[1]
        elif hat == "prefabrik" and (mk := makas_bul(s, H.get("makas_kurali"))):
            if mk[0]["onay"] or oneri:
                fiyat, kaynak, durum, kayit = mk[1], mk[0]["kaynak"], ("onaylı makas kuralı" if mk[0]["onay"] else "öneri makas kuralı"), mk[0]
            else:
                durum, oneri_fiyat = "öneri makas kuralı, onay bekliyor", mk[1]
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
                         **({"oneri_fiyat": oneri_fiyat} if oneri_fiyat is not None else {}),
                         **{a: g[a] for a in YAZILAN if g and g.get(a)}})
        if kdv_kip:                                                # D-76: oran yalnız fiyatı olan satırda; yoksa boş
            oran = (kayit or {}).get("kdv") if tutar is not None else None
            satirlar[-1] |= {"kdv_orani": oran, "kdv_grubu": (kayit or {}).get("kdv_grubu") if oran is not None else None,
                             "kdv_tutari": round(tutar * oran, 2) if oran is not None else None}
    ozet = {"toplam": round(toplam, 2), "onayli_fiyatlarla": round(onayli, 2), "onerilerle": round(oneri_toplam, 2),
            "satir": len(satirlar), "fiyatli": sum(1 for x in satirlar if x["tutar"] is not None),
            "fiyatsiz": fiyatsiz, "oneri_bekleyen": {"satir": bekleyen["satir"], "tutar": round(bekleyen["tutar"], 2)}, "gruplar": gruplar}
    if kdv_kip:
        ozet["kdv"] = kdv_ozeti(satirlar, ozet["toplam"], defter["kdv"].get("dayanak"))
    return {"hat": hat, "defter_surumu": defter.get("surum"), "oneri_dahil": oneri, "satirlar": satirlar, "ozet": ozet}


def oran_yazi(oran: float) -> str:
    return f"%{oran * 100:g}"


def kdv_ozeti(satirlar: list[dict], haric: float, dayanak: str | None = None) -> dict:
    """D-76: KDV hariç toplam (fiyatlı satırlar), oranlara göre matrah ve KDV (satır KDV'lerinin toplamı), KDV dahil. Tutarı olup oranı
    olmayan satır (0 TL'lik satır hariç) `oransiz`'da sayılır; KDV'si yoktur, KDV dahil toplam o satırlar için eksiktir (`eksik`)."""
    oranlar: dict[str, dict] = {}
    oransiz = []
    for s in satirlar:
        if not s.get("tutar"):
            continue
        if s.get("kdv_orani") is None:
            oransiz.append({"sira": s["sira"], "kalem": s["kalem"], "olcu": s.get("olcu"), "tutar": s["tutar"]})
            continue
        o = oranlar.setdefault(oran_yazi(s["kdv_orani"]), {"oran": s["kdv_orani"], "matrah": 0.0, "kdv": 0.0, "satir": 0})
        o["matrah"] += s["tutar"]; o["kdv"] += s["kdv_tutari"]; o["satir"] += 1
    for o in oranlar.values():
        o["matrah"], o["kdv"] = round(o["matrah"], 2), round(o["kdv"], 2)
    kdv = round(sum(o["kdv"] for o in oranlar.values()), 2)
    return {"dayanak": dayanak, "haric": round(haric, 2), "kdv": kdv, "dahil": round(haric + kdv, 2),
            "oranlar": dict(sorted(oranlar.items(), key=lambda x: -x[1]["oran"])),
            "oransiz": {"satir": len(oransiz), "tutar": round(sum(x["tutar"] for x in oransiz), 2), "satirlar": oransiz},
            "eksik": bool(oransiz)}


def kdv_yazi(k: dict) -> str:
    """Özetin KDV satırı (komut, teklif Özet'i, PDF): oranlara göre KDV ve oranı olmayan satırlar."""
    def tl(x: float) -> str:                                    # Türkçe yazım: 1.234,50
        return f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    parca = [f"{a} KDV {tl(o['kdv'])} TL ({o['satir']} satır)" for a, o in k["oranlar"].items()]
    if k["oransiz"]["satir"]:
        parca.append(f"{k['oransiz']['satir']} satırın KDV oranı yok ({tl(k['oransiz']['tutar'])} TL), KDV dahil toplam eksik")
    return "; ".join(parca)


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
    a.add_argument("liste"); a.add_argument("--hat", choices=["prefabrik", "celik"])
    a.add_argument("--crm", help="CRM anlık görüntüsü (sunucunun günlük çekimi; D-72 tek fiyat kaynağı)")
    a.add_argument("--defter", help="kapanmış teklifin o günkü defteri (ör. kurallar/fiyat/defter_2026-11.json)")
    a.add_argument("--oneri", action="store_true"); a.add_argument("--alan", type=float); a.add_argument("--m2-fiyat", type=float)
    a.add_argument("--esik", type=float); a.add_argument("--json"); a.add_argument("--excel"); a.add_argument("--duzeltme")
    o = a.parse_args(argv)
    L, D = oku(o.liste), defter_sec(o.crm, o.defter)
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
    if oz.get("kdv"):
        k = oz["kdv"]
        print(f"  KDV ({k['dayanak']}): KDV hariç {k['haric']:,.2f} + KDV {k['kdv']:,.2f} = KDV dahil {k['dahil']:,.2f} TL · {kdv_yazi(k)}")
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
