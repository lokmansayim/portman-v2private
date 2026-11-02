"""Katalog İş Emri'ne deterministik varyant uygulama. v0.1: ayna_x, ayna_y, pencere_degistir.

Aynalama pano biriminde yapılır; LLM geometriye dokunmaz. Pano indeksleri motorun aday listesinden
(kur() hata mesajındaki 'aday N') hesaplanır; menteşe her aynada ters döner (el değişimi).
"""
from __future__ import annotations
import copy, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G  # noqa: E402

DUVAR_X = {"sol": "sag", "sag": "sol"}
DUVAR_Y = {"on": "arka", "arka": "on"}
MENTESE = {"sol": "sag", "sag": "sol"}
KONUM = {"on": "arka", "arka": "on"}


class VaryantHatasi(Exception):
    pass


def _aday_sayisi(is_emri: dict, idx_aciklik: int) -> int:
    """Belirli açıklığın aday pano sayısını motordan öğren (kasıtlı aralık dışı indeksle)."""
    ie = copy.deepcopy(is_emri)
    ie["acikliklar"][idx_aciklik]["pano"] = 999
    try:
        G.kur(ie)
    except G.IsEmriHatasi as e:
        m = re.search(r"\(aday (\d+)\)", str(e))
        if m:
            return int(m.group(1))
        raise VaryantHatasi(f"aday sayısı okunamadı: {e}")
    raise VaryantHatasi("aday sayısı belirlenemedi")


def ayna(is_emri: dict, eksen: str) -> dict:
    """eksen 'x': sol-sağ ayna (x' = nx - x). eksen 'y': ön-arka ayna (y' = ny - y)."""
    if eksen not in ("x", "y"):
        raise VaryantHatasi("eksen x veya y olmalı")
    ie = copy.deepcopy(is_emri)
    nx, ny = ie["yapi"]["grid"]["x_pano"], ie["yapi"]["grid"]["y_pano"]

    # 1) aday pano sayıları (özgün geometride) — yalnız indeksi verilmiş ve yönü tersine dönecek açıklıklar için
    ters_donen = {}
    for i, ac in enumerate(ie["acikliklar"]):
        if ac.get("pano") is None:
            continue
        duvar_yonu = _aciklik_duvar_yonu(is_emri, ac)   # 'x' yatay duvar, 'y' dikey duvar
        if (eksen == "x" and duvar_yonu == "x") or (eksen == "y" and duvar_yonu == "y"):
            ters_donen[i] = _aday_sayisi(is_emri, i)

    # 2) mahaller
    for m in ie["mahaller"]:
        yeni = []
        for x0, y0, x1, y1 in m["konum_pano"]:
            if eksen == "x":
                yeni.append([nx - x1, y0, nx - x0, y1])
            else:
                yeni.append([x0, ny - y1, x1, ny - y0])
        m["konum_pano"] = yeni

    # 3) açıklıklar
    for i, ac in enumerate(ie["acikliklar"]):
        if "duvar" in ac:
            ac["duvar"] = (DUVAR_X if eksen == "x" else DUVAR_Y).get(ac["duvar"], ac["duvar"])
        if "mentese" in ac:
            ac["mentese"] = MENTESE.get(ac["mentese"], ac["mentese"])
        if i in ters_donen:
            ac["pano"] = ters_donen[i] - 1 - ac["pano"]

    # 4) açık sınırlar (mahal çiftleri) — yön bilgisi taşıyorsa çevir
    for s in ie.get("acik_sinirlar", []):
        if isinstance(s, dict) and "duvar" in s:
            s["duvar"] = (DUVAR_X if eksen == "x" else DUVAR_Y).get(s["duvar"], s["duvar"])

    # 5) dikmeler (cm): özgün plan ölçüleriyle
    plan = G.kur(is_emri) if (ie.get("dikmeler") or ie.get("verandalar")) else None   # verandanın konumu da bu planla (geçersiz girdi burada düşer)
    if ie.get("dikmeler"):
        W, H = plan.W, plan.H
        ie["dikmeler"] = [([W - x - 10.0, y] if eksen == "x" else [x, H - y - 10.0]) for x, y in ie["dikmeler"]]

    # 5b) gövdeden taşan verandalar (BK-14; cm, gerçek çerçeve): cephe aynalanır, cephe boyunca konum mahaller ve dikmeler gibi planın
    # ölçüsüne göre çevrilir (x → W − x; ayak izine göre değil: ızgara içi veranda bir kenarı boydan boya kaplarsa ayak izi dar kalır)
    if ie.get("verandalar"):
        for v in ie["verandalar"]:
            boyuna = v.get("cephe") in ("on", "arka")              # konum x boyunca
            if (eksen == "x") == boyuna:
                L = plan.W if boyuna else plan.H
                v["bas_cm"], v["bit_cm"] = L - float(v["bit_cm"]), L - float(v["bas_cm"])
            v["cephe"] = (DUVAR_X if eksen == "x" else DUVAR_Y).get(v.get("cephe"), v.get("cephe"))

    # 6) giriş cephesi / varsayımlar / no
    if eksen == "y":
        ie["yapi"]["giris_cephesi"] = KONUM.get(ie["yapi"].get("giris_cephesi", "on"), "on")
    ie.setdefault("varsayimlar", []).append(f"Varyant: ayna_{eksen} uygulandı (pano biriminde deterministik dönüşüm).")
    ie["is_emri_no"] = ie.get("is_emri_no", "PM") + f"-AYNA{eksen.upper()}"
    return ie


def _aciklik_duvar_yonu(is_emri: dict, ac: dict) -> str:
    """Açıklığın oturduğu duvar yatay mı ('x') dikey mi ('y')? Pencerede duvar adı; kapıda iki mahalin komşuluğu."""
    if "duvar" in ac:
        return "x" if ac["duvar"] in ("on", "arka") else "y"
    a, b = ac["arasi"]
    ra = _rects(is_emri, a); rb = _rects(is_emri, b)
    for x0, y0, x1, y1 in ra:
        for u0, v0, u1, v1 in rb:
            if (abs(x1 - u0) < 1e-9 or abs(u1 - x0) < 1e-9) and min(y1, v1) - max(y0, v0) > 1e-9:
                return "y"
            if (abs(y1 - v0) < 1e-9 or abs(v1 - y0) < 1e-9) and min(x1, u1) - max(x0, u0) > 1e-9:
                return "x"
    raise VaryantHatasi(f"{a}–{b} komşu değil")


def _rects(is_emri: dict, ad: str):
    for m in is_emri["mahaller"]:
        if m["ad"] == ad:
            return m["konum_pano"]
    raise VaryantHatasi(f"mahal yok: {ad}")


def pencere_degistir(is_emri: dict, mahal: str | None, eski: str | None, yeni: str) -> dict:
    """Mahal (ve varsa eski ölçü) eşleşen pencerelerin ölçüsünü değiştirir. Eşleşme yoksa hata."""
    ie = copy.deepcopy(is_emri)
    n = 0
    for ac in ie["acikliklar"]:
        if ac["tur"] != "pencere": continue
        if mahal and _norm(ac["mahal"]) != _norm(mahal): continue
        if eski and ac["olcu"] != eski: continue
        ac["olcu"] = yeni; n += 1
    if n == 0:
        raise VaryantHatasi(f"Değiştirilecek pencere bulunamadı (mahal={mahal}, eski={eski})")
    ie.setdefault("varsayimlar", []).append(f"Varyant: {n} pencere {yeni} yapıldı (mahal={mahal or 'tümü'}).")
    return ie


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c"))


# ───────────────────────── İE-08 PR-2b (A4) · genel motor: Yapı Tanımı 0.5 değişiklikleri ─────────────────────────
# Çelik İş Emri zarfı tanımı gömmez; `yapi.degisiklikler` listesindeki işlemler `modeller/<kod>.json`'a sırayla uygulanır
# (`kanal/worker.cizim_genel`). Her işlem saf ve deterministiktir: girdi değişmez, yeni tanım döner; geçersiz sonuç (`yapi.kur`'un
# SystemExit'i) VaryantHatasi olur, çizim düşmez, kural katmanı sorar ya da yönlendirir. 8a'da üç işlem (Lokman, 12.10.2026):
#   {"op": "pencere_olcu", "aciklik": "P5", "en": 120, "yuk": 120}   pencere ölçüsü (merkez ve üst kot korunur)
#   {"op": "cati_varyanti", "kod": "Ç8801L"}                          çatı varyantı: zarf tanım dosyasını değiştirir; burada yalnız teyit
#   {"op": "dis_karkas_140"}                                          dış duvar karkası 140 (kurallar/model/secenekler/dis_karkas_140.json)
# İE-23 PR-2a (banka germe; ayar `banka_germe.acik` arkasında okunur):
#   {"op": "oda_buyut" | "oda_kucult", "mahal": "Yatak Odası 1", "yon": "K", "cm": 50}   dış kenar: ev o yöne uzar; iç kenar: duvar kayar
KARKAS_140_CM = 14.0
LENTO_VARSAYILAN = 70          # bilgi: Ç8801/Ç8201'de pencere üstü 270 − 70 = 200; pencere_olcu üst kotu tanımdan korur
_TOL = 0.01
PENCERE_EN = (30, 400)        # cm; bayinin söyleyebileceği makul aralık (daha büyüğü otomatik yapılmaz, mühendise)
PENCERE_YUK = (30, 250)


def _kod_norm(s) -> str:
    """Tanımdaki "Ç8801-L" ile zarf/bayi kodu "Ç8801L", "c8801l" aynı sayılır (`Katalog.kod_normalize` ile aynı kural: C → Ç)."""
    q = re.sub(r"[\s\-]", "", str(s or "")).upper()
    return re.sub(r"^C(?=\d{4})", "Ç", q)


def _kur(t: dict):
    """`yapi.kur`; tanım geçersizse VaryantHatasi (SystemExit yakalanır: ajan süreci düşmez)."""
    from motor.genel import yapi
    try:
        return yapi.kur(t)
    except SystemExit as e:
        raise VaryantHatasi(f"tanım geçersiz: {e}") from None


def tanim_uygula(t: dict, d: dict) -> dict:
    """Tek bir değişikliği uygular; yeni tanım döner. Her işlemden sonra bütün açıklıklar yeniden denetlenir (`aciklik_denetimi`):
    sonuç değişikliklerin sırasına bağlı olmaz (geometri hakemi 13.10: önce genişleyen pencere, sonra dış 140 köşe karkasına giriyordu)."""
    op = (d or {}).get("op")
    if op == "pencere_olcu":
        t2 = pencere_olcu(t, d.get("aciklik"), d.get("en"), d.get("yuk"))
    elif op == "cati_varyanti":
        return cati_varyanti(t, d.get("kod"))
    elif op == "dis_karkas_140":
        t2 = dis_karkas_140(t)
    elif op in ("oda_buyut", "oda_kucult"):                  # İE-23 PR-2a: germe / iç duvar kaydırma; hakemi kendi içinde (tanim_germe.denetle)
        from beyin import tanim_germe
        t2 = tanim_germe.uygula(t, d)
    else:
        raise VaryantHatasi(f"bilinmeyen değişiklik: {op}")
    aciklik_denetimi(t2, _kur(t2))
    return t2


def aciklik_denetimi(t: dict, y: dict) -> None:
    """Her açıklık (pencere ve kapı) duvarının iki yanında da tek bir yüz aralığının içinde kalmalı: oda yanında iç duvar birleşimini,
    dış yanda dıştan dayanan duvarı (KT-01 MD1) kesmez. Yüz aralığı kaplamalı yüzeydedir; açıklık dik duvarın kaplamasına girebilir,
    karkasına giremez: aralık, o yüzün kendi kaplama kalınlığı kadar uzatılır (geometri hakemi 13.10: önceki pay iç ve dış kaplamanın
    büyüğüydü, KT'de karkasa 0,65 cm giriyordu). Aynı yandaki bitişik aralıklar (veranda ile açık hava) birleşir. Hata: VaryantHatasi."""
    kap = t.get("yuz_kaplamalari") or {}
    for ac in t.get("acikliklar", []):
        yanlar: dict[str, list] = {}
        for f in y["yuzler"]:
            if f["duvar"] != ac.get("duvar") or not f["uzun"]:
                continue
            pay = float((kap.get(f.get("kaplama")) or {}).get("kalinlik", 0) or 0) + _TOL
            yanlar.setdefault(f["kenar"], []).extend((lo - pay, hi + pay) for lo, hi in f["araliklar"])
        a0, a1 = ac["bas"], ac["bas"] + ac["en"]
        for kn, aral in sorted(yanlar.items()):
            birlesik: list[list[float]] = []
            for lo, hi in sorted(aral):
                if birlesik and lo <= birlesik[-1][1] + _TOL:
                    birlesik[-1][1] = max(birlesik[-1][1], hi)
                else:
                    birlesik.append([lo, hi])
            if not any(lo - _TOL <= a0 and a1 <= hi + _TOL for lo, hi in birlesik):
                ne = "penceresi" if ac.get("tur") == "pencere" else "kapısı"
                raise VaryantHatasi(f"{(ac['mahal'] + ' ') if ac.get('mahal') else ''}{ne} ({ac.get('ad')}, {ac['en']:g} cm) "
                                    f"duvar birleşimine biniyor")


def pencere_olcu(t: dict, aciklik: str | None, en, yuk) -> dict:
    """Pencerenin ölçüsü (en × yük, cm). Merkez korunur (bas = merkez − en/2); **üst kot korunur** (alt = alt₀ + yük₀ − yük): Ç8801 ve
    Ç8201'de pencere üstü 200 (kat 270 − lento 70; 120/180 → 20, 120/120 → 80, 60/40 → 160), KT-02/KT-03'teki 220 üstlü pencereler de
    kendi kotunda kalır (geometri hakemi 13.10: "kat − lento − yük" KT-02 P6'nın denizliğini sessizce 0'a indiriyor, KT-03 P4/P5'in
    kendi 220'sini reddediyordu). Etiket "en/yük". Aynı duvardaki başka açıklıkla çakışırsa, duvar yüzüne sığmazsa
    (`aciklik_denetimi`, iki yan) ya da duvarın dışına taşarsa hata."""
    try:
        en, yuk = int(en), int(yuk)
    except (TypeError, ValueError):
        raise VaryantHatasi(f"pencere ölçüsü okunamadı: {en} × {yuk}") from None
    if not (PENCERE_EN[0] <= en <= PENCERE_EN[1] and PENCERE_YUK[0] <= yuk <= PENCERE_YUK[1]):
        raise VaryantHatasi(f"pencere ölçüsü {en}×{yuk} aralık dışı ({PENCERE_EN[0]}–{PENCERE_EN[1]} × {PENCERE_YUK[0]}–{PENCERE_YUK[1]} cm)")
    t2 = copy.deepcopy(t)
    ac = next((a for a in t2.get("acikliklar", []) if a.get("ad") == aciklik), None)
    if ac is None or ac.get("tur") != "pencere":
        raise VaryantHatasi(f"pencere yok: {aciklik}")
    ust = float(ac.get("alt", 0) or 0) + float(ac["yuk"])          # üst kot korunur
    alt = ust - yuk
    alt = int(alt) if float(alt).is_integer() else round(alt, 2)
    if alt < 0:
        raise VaryantHatasi(f"{aciklik}: {yuk} cm yükseklik sığmıyor (pencere üstü {ust:g} cm; en çok {ust:g})")
    merkez = ac["bas"] + ac["en"] / 2
    bas = merkez - en / 2
    bas = int(bas) if float(bas).is_integer() else round(bas, 2)
    for b in t2["acikliklar"]:
        if b is ac or b.get("duvar") != ac.get("duvar"):
            continue
        if min(b["bas"] + b["en"], bas + en) - max(b["bas"], bas) > _TOL:
            raise VaryantHatasi(f"{aciklik} {en}×{yuk} olunca {b.get('ad')} ile çakışıyor")
    ac.update(bas=bas, en=en, yuk=yuk, alt=alt, etiket=f"{en}/{yuk}")
    y = _kur(t2)                                              # duvar boyu denetimi (taşarsa SystemExit → VaryantHatasi)
    try:
        aciklik_denetimi(t2, y)                               # iki yanda da tek yüz aralığında (iç duvar birleşimini, dıştan dayanan duvarı kesmez)
    except VaryantHatasi:
        raise VaryantHatasi(f"{aciklik} {en} cm eninde {ac.get('mahal') or ac.get('duvar')} duvarına sığmıyor") from None
    return t2


def cati_varyanti(t: dict, kod: str | None) -> dict:
    """Çatı varyantı tanım düzeyinde işlem değildir: İş Emri zarfı tanım dosyasını (katalog/K/L) değiştirir; duvarlar ve açıklıklar
    üçünde aynıdır. Burada yalnız tanımın o varyant olduğu teyit edilir (zarfla uyuşmazsa hata)."""
    if _kod_norm(t.get("kod")) != _kod_norm(kod):
        raise VaryantHatasi(f"çatı varyantı {kod} bu tanıma uygulanamaz (tanım {t.get('kod')})")
    return copy.deepcopy(t)


def dis_karkas_140(t: dict) -> dict:
    """Dış duvar karkası 140 mm (kurallar/model/secenekler/dis_karkas_140.json): yalnız `dis` sınıfı duvarlar; dış ölçü değişmez, duvar
    içeri doğru kalınlaşır (8 → 14 cm karkas; kaplamalarla 10,5 → 16,5 cm); iç duvar aksları değişmez. Yöntem: `yapi.kur`'un yüzlerinden
    her dış duvarın içe bakan uzun kenarı bulunur ve 6 cm içeri alınır; o yüze dayanan (dik) duvar uçları yüzle birlikte kayar (iç
    duvarlar kısalır; L köşede dış duvarın ucu uzayıp köşeyi kapatır). Sınıf profili 140×45×1,2, adı DIS-140. Karkas modeli taşıyan
    tanımda (KT-01/02 `celik_modeli`) ve zaten 140 olanda (KT-03) hata: mühendise."""
    t2 = copy.deepcopy(t)
    if t2.get("celik_modeli"):
        raise VaryantHatasi("modelin çelik karkas modeli var (celik_modeli); dış 140 seçeneği karkas modeliyle uyuşmaz, mühendis bakmalı")
    sinif = (t2.get("duvar_siniflari") or {}).get("dis")
    if not sinif:
        raise VaryantHatasi("tanımda dış duvar sınıfı yok")
    if re.match(r"\s*140", str(sinif.get("profil") or "")):
        raise VaryantHatasi("dış karkas zaten 140")
    y = _kur(t)                                               # özgün geometri: yüzler ve uçlar buradan okunur
    hamleler = []
    for d in y["duvarlar"]:
        if d["sinif"] != "dis":
            continue
        delta = KARKAS_140_CM - d["kalinlik"]
        if delta <= _TOL:
            raise VaryantHatasi(f"{d['ad']}: karkas zaten {d['kalinlik']:g} cm")
        ic = sorted({f["kenar"] for f in y["yuzler"] if f["duvar"] == d["ad"] and f["uzun"] and f["bolge_sinifi"] in ("ic", "ek")})
        if len(ic) != 1:
            raise VaryantHatasi(f"{d['ad']}: dış duvarın iç yüzü belirlenemedi ({', '.join(ic) or 'iç yüz yok'})")
        kn = ic[0]
        x0, y0, x1, y1 = d["kutu"]
        if kn == "ust":
            eski, yeni, eks, span = y1, y1 + delta, "y", (x0, x1)
        elif kn == "alt":
            eski, yeni, eks, span = y0, y0 - delta, "y", (x0, x1)
        elif kn == "sag":
            eski, yeni, eks, span = x1, x1 + delta, "x", (y0, y1)
        else:
            eski, yeni, eks, span = x0, x0 - delta, "x", (y0, y1)
        hamleler.append((d["ad"], kn, eks, eski, yeni, span))
    if not hamleler:
        raise VaryantHatasi("tanımda dış duvar yok")
    adli = {w["ad"]: w for w in t2["duvarlar"]}
    ozgun = {w["ad"]: list(w["kutu"]) for w in t["duvarlar"]}
    for ad, kn, eks, eski, yeni, span in hamleler:            # 1) dış duvarın iç kenarı içeri
        adli[ad]["kutu"][{"alt": 1, "ust": 3, "sol": 0, "sag": 2}[kn]] = yeni
    for ad, kn, eks, eski, yeni, span in hamleler:            # 2) o yüze dayanan dik duvar uçları yüzle birlikte
        for w in t2["duvarlar"]:
            if w["ad"] == ad or y["adli"][w["ad"]]["yon"] != eks:
                continue
            kutu, orij = w["kutu"], ozgun[w["ad"]]
            lo_i, hi_i, b_i, s_i = ((0, 2, 1, 3) if eks == "y" else (1, 3, 0, 2))   # dik duvarın enine aralığı ve uçları
            if min(orij[hi_i], span[1]) - max(orij[lo_i], span[0]) < -_TOL:         # dış duvarın boyuna değmiyor
                continue
            if abs(orij[b_i] - eski) < _TOL:
                kutu[b_i] = yeni
            if abs(orij[s_i] - eski) < _TOL:
                kutu[s_i] = yeni
    # 3) kayan dış duvara ucuyla giren duvar o duvarın yeni yüzüne kısalır (ikinci derece birleşim: Ç8801 L köşesinde DKB'nin ucu uzar,
    #    üstüne oturan I6 6 cm içine giriyordu — geometri hakemi 13.10). Uçtan değil ortadan kesişme hatadır.
    tasinan = {ad for ad, *_ in hamleler}
    for w in t2["duvarlar"]:
        if w["ad"] in tasinan:
            continue
        for o in t2["duvarlar"]:
            if o["ad"] not in tasinan:
                continue
            k, ok = w["kutu"], o["kutu"]
            ix = min(k[2], ok[2]) - max(k[0], ok[0]); iy = min(k[3], ok[3]) - max(k[1], ok[1])
            if ix <= _TOL or iy <= _TOL:
                continue
            yon = y["adli"][w["ad"]]["yon"]
            b_i, s_i, lo_i, hi_i = (1, 3, 1, 3) if yon == "y" else (0, 2, 0, 2)
            if ok[lo_i] <= k[b_i] + _TOL and k[b_i] < ok[hi_i] < k[s_i]:      # w'nin başı o'nun içinde
                k[b_i] = ok[hi_i]
            elif ok[hi_i] >= k[s_i] - _TOL and k[b_i] < ok[lo_i] < k[s_i]:    # w'nin sonu o'nun içinde
                k[s_i] = ok[lo_i]
            else:
                raise VaryantHatasi(f"{w['ad']}: dış 140 ile {o['ad']} duvarını ortadan kesiyor")
    for w in t2["duvarlar"]:
        x0, y0, x1, y1 = w["kutu"]
        if x1 - x0 <= _TOL or y1 - y0 <= _TOL:
            raise VaryantHatasi(f"{w['ad']}: duvar dış 140 ile sıfır boya düşüyor")
    duv = t2["duvarlar"]
    for i in range(len(duv)):                                 # hiçbir duvar çifti alan olarak örtüşmez (özgün modellerde örtüşme yok)
        for j in range(i + 1, len(duv)):
            a, b = duv[i]["kutu"], duv[j]["kutu"]
            if min(a[2], b[2]) - max(a[0], b[0]) > _TOL and min(a[3], b[3]) - max(a[1], b[1]) > _TOL:
                raise VaryantHatasi(f"dış 140 ile {duv[i]['ad']} ve {duv[j]['ad']} üst üste biniyor")
    sinif["profil"] = re.sub(r"^\s*\d+", "140", str(sinif.get("profil") or "80x45x1,2"))
    sinif["ad"] = re.sub(r"\b80\b", "140", str(sinif.get("ad") or "")) if re.search(r"\b80\b", str(sinif.get("ad") or "")) else f"{sinif.get('ad') or 'dış duvar'} (DIS-140)"
    _kur(t2)
    return t2
