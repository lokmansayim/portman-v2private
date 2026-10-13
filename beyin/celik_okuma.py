"""İE-08 8a PR-2b (A4) · Çelik revizyonunda bayinin KENDİ sözünden okuma (K18; LLM özeti değil). LLM yok, motor modülleri yok.

Üç değişiklik türü (Lokman, 12.10.2026): pencere ölçüsü, çatı varyantı (katalog/K/L), dış karkas 140. Kural belirsizlikte sessizce
değiştirmez, sorar (K21): pencere için aday sayısı 0 → soru (pencereli odalar), 1 → uygula, 2 → görselli "1 / 2 / Hiçbiri" sorusu,
3 ve üstü → numaralı metin sorusu. Olumsuz ya da soru biçimli söz ("olmasın", "… mi?") pencere için belirsizdir, sorulur.

`oku(metin, t, katalog_aday, ipucu)` → {"pencere": {...} | None, "cati": kod | None, "dis140": bool, "istek": bool}
`okuma_cevabi(metin, bekleyen)` → "1 / 2 / Hiçbiri" (ya da numaralı) sorusunun cevabı; ölçü sorusunun cevabı.
"""
from __future__ import annotations
import re

from . import celik

_TR = str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")
PENCERE_EN = (30, 400)
PENCERE_YUK = (30, 250)
VASISTAS_ESIK = 60          # kurallar/cizim/pafta_sablonu.json › vasistas_en_cok_yukseklik_cm ile aynı (motor içe aktarılmasın diye kopya; test denetler)
EN_COK_ADAY = 9

ISLEV_SOZ = {"mutfak": ("mutfak",), "salon": ("salon", "oturma", "yasam", "yasam alani", "oturma odasi", "misafir"),
             "yatak_odasi": ("yatak", "yatak odasi", "ebeveyn", "cocuk", "cocuk odasi"), "banyo": ("banyo", "wc", "tuvalet", "dus", "lavabo"),
             "hol": ("hol", "antre", "koridor", "giris holu"), "depo": ("depo", "kiler", "mustemilat")}
CEPHE_AD = {"on": "ön", "arka": "arka", "sol": "sol", "sag": "sağ"}
_OLCU = re.compile(r"(?<!\d)(\d{2,3})\s*(?:[xX×*/]|'?[ye]\s)\s*(\d{2,3})(?!\d)")
_CEPHE = re.compile(r"\b(on|arka|sol|sag)(?:daki|taki|deki|dan|tan|den|a|e)?\s*(?:cephe\w*|taraf\w*|duvar\w*|yuz\w*)\b|\b(on|arka|sol|sag)(?:daki|taki|deki)\b")
_PENCERE_SOZ = re.compile(r"\b(pencere\w*|vasistas\w*|cam\w*)\b")
_VASISTAS = re.compile(r"\bvasistas\w*")
_DIS140 = re.compile(r"\bdis(?:lar|lari|lerin|larin|in)?\b(?:\s+duvar\w*|\s+karkas\w*|\s+cerceve\w*)?[^.;,]{0,25}?\b(?:140|14)\b|\b(?:140|14)\s*(?:lik|luk|mm)?\s+dis\b")
_OLUMSUZ = re.compile(r"\b(olmasin\w*|olmayacak|istemiyor\w*|istemem|degil\w*|yok|degistirme\w*|yapma\w*|ekleme\w*|koyma\w*|kalsin|dokunma\w*)\b")
_SORU_EKI = re.compile(r"\b(mi|mu|misiniz|musunuz|miyiz|muyuz|midir|mudur)\b")
_ESKI_YENI = re.compile(r"\b(yerine|olan|iken|idi|di|den|dan|dir)\b")
_EKLE = re.compile(r"\b(ekle\w*|ilave\w*|fazladan|bir tane daha|bir de|yeni (?:bir )?pencere|ikinci (?:bir )?pencere|kaldir\w*|iptal|sil\w*|kapat\w*)\b")
_SAYI_SOZ = {"bir": 1, "birinci": 1, "ilk": 1, "ilki": 1, "iki": 2, "ikinci": 2, "ikincisi": 2, "uc": 3, "ucuncu": 3, "dort": 4, "dorduncu": 4,
             "bes": 5, "besinci": 5, "alti": 6, "altinci": 6, "yedi": 7, "yedinci": 7, "sekiz": 8, "sekizinci": 8, "dokuz": 9, "dokuzuncu": 9}
_HICBIRI = re.compile(r"\b(hicbiri|hic biri|hicbirisi|ikisi de degil|ikisi de|hayir|baska|yok)\b")


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (s or "").translate(_TR).lower())).strip()


def _parcalar(metin: str | None) -> list[str]:
    return re.findall(r"[^;,.!?\n]+[;,.!?\n]*", metin or "")


def olumsuz_ya_da_soru(parca: str) -> bool:
    q = " " + norm(parca) + " "
    return "?" in parca or bool(_SORU_EKI.search(q)) or bool(_OLUMSUZ.search(q))


def olculer(metin: str | None) -> list[tuple[int, int]]:
    """Metindeki pencere ölçüleri (en, yük; cm). "120x120", "120 x 180", "120/180", "120*120", "120'ye 120"."""
    out = []
    for m in _OLCU.finditer(metin or ""):
        en, yuk = int(m.group(1)), int(m.group(2))
        if PENCERE_EN[0] <= en <= PENCERE_EN[1] and PENCERE_YUK[0] <= yuk <= PENCERE_YUK[1]:
            out.append((en, yuk))
    return out


def cephe(y_duvar: dict, yuzler: list[dict]) -> str | None:
    """Dış duvarın cephesi: dışa bakan uzun kenarının yönünden (sahne.py: +y kuzey, ön cephe planda altta). İç yüzü 'ust' olan duvarın
    dışı 'alt'a (−y) bakar → ön."""
    ic = {f["kenar"] for f in yuzler if f["duvar"] == y_duvar["ad"] and f["uzun"] and f["bolge_sinifi"] in ("ic", "ek")}
    dis = {f["kenar"] for f in yuzler if f["duvar"] == y_duvar["ad"] and f["uzun"] and f["bolge_sinifi"] in ("dis", "veranda")}
    kn = next(iter(dis - ic), None) or next(iter(dis), None)
    if kn is None:
        kn = {"ust": "alt", "alt": "ust", "sol": "sag", "sag": "sol"}.get(next(iter(ic), ""))
    return {"alt": "on", "ust": "arka", "sol": "sol", "sag": "sag"}.get(kn)


def pencere_adaylari(t: dict, y: dict | None = None) -> list[dict]:
    """Tanımdaki pencereler okuma adayı olarak: {aciklik, mahal, en, yuk, etiket, cephe, vasistas, aciklama}. `y` (`yapi.kur` sonucu)
    verilirse cephe yüzlerden; verilmezse duvarın bina ortasına göre konumundan (motor içe aktarılmadan)."""
    duvar = {d["ad"]: d for d in t.get("duvarlar", [])}
    xs = [v for d in duvar.values() for v in (d["kutu"][0], d["kutu"][2])]; ys = [v for d in duvar.values() for v in (d["kutu"][1], d["kutu"][3])]
    mx, my = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2) if xs else (0, 0)
    out = []
    for a in t.get("acikliklar", []):
        if a.get("tur") != "pencere":
            continue
        d = duvar.get(a.get("duvar"))
        c = None
        if d is not None:
            if y is not None:
                c = cephe(y["adli"][d["ad"]], y["yuzler"])
            else:
                x0, y0, x1, y1 = d["kutu"]
                yatay = (x1 - x0) >= (y1 - y0)
                c = ("on" if (y0 + y1) / 2 < my else "arka") if yatay else ("sol" if (x0 + x1) / 2 < mx else "sag")
        et = a.get("etiket") or f"{a['en']}/{a['yuk']}"
        vas = a["yuk"] <= VASISTAS_ESIK
        mahal = a.get("mahal") or ""
        out.append({"aciklik": a["ad"], "mahal": mahal, "en": a["en"], "yuk": a["yuk"], "etiket": et, "cephe": c, "vasistas": vas,
                    "aciklama": f"{mahal + ' ' if mahal else ''}{'vasistası' if vas else 'penceresi'} {et}" + (f" ({CEPHE_AD[c]} cephe)" if c else "")})
    return out


def _kok(s: str) -> str:
    """Normalize sözcük(ler) → ek alabilen gövde deseni: son sözcük ek alır ("alani" → "alaninin"), sondaki k yumuşar ("mutfak" → "mutfagin")."""
    soz = s.split()
    out = []
    for i, w in enumerate(soz):
        g = re.escape(w[:-1]) + "[kg]" if w.endswith("k") else re.escape(w)
        out.append(g + (r"\w*" if i == len(soz) - 1 else ""))
    return r"\b" + r"\s+".join(out)


def _mahaller(metin_n: str, t: dict) -> list[str]:
    """Metinde geçen mahal(ler): önce ad (en uzun eşleşme; ekli ve yumuşamış biçimler: "mutfağın", "yaşam alanının"), sonra numaralı
    oda biçimleri ("1. yatak odası", "ikinci yatak odasının"), sonra işlev eşanlamları (birden çok oda dönebilir: iki yatak odası)."""
    q = " " + metin_n + " "
    adlar = [m["ad"] for m in t.get("mahaller", [])]
    tam = [ad for ad in adlar if re.search(_kok(norm(ad)) + (r"(?!\s*\d)" if not re.search(r"\d$", norm(ad)) else ""), q)]
    if tam:
        en_uzun = max(len(norm(a)) for a in tam)
        return [a for a in tam if len(norm(a)) == en_uzun]
    for m in t.get("mahaller", []):
        nm = norm(m["ad"])
        mm = re.fullmatch(r"(.+?) (\d)", nm)
        if mm:
            govde, no = mm.group(1), mm.group(2)
            sayilar = "|".join(k for k, v in _SAYI_SOZ.items() if v == int(no))
            kalip = rf"\b(?:{no}\s*(?:\.|inci|nci|nolu|no lu|numarali)?|{sayilar})\s+{_kok(govde)[2:]}|{_kok(govde)[:-3]}\s+{no}\b"
            if re.search(kalip, q):
                tam.append(m["ad"])
    if tam:
        return tam
    bulunan = []
    for m in t.get("mahaller", []):
        for islev in m.get("islev", []):
            if any(re.search(_kok(s), q) for s in ISLEV_SOZ.get(islev, ())):
                bulunan.append(m["ad"]); break
    return bulunan


def _cepheler(metin_n: str) -> list[str]:
    q = " " + metin_n + " "
    return sorted({(m.group(1) or m.group(2)) for m in _CEPHE.finditer(q)})


def oku(metin: str | None, t: dict, katalog_aday: dict | None = None, ipucu: bool = False, y: dict | None = None) -> dict:
    """Bayinin mesajından çelik revizyon okumaları. `katalog_aday`: çatı varyantları olan katalog modeli kaydı (`varyantlar`).
    `ipucu`: LLM pencere değişikliği gördü (okuma yine bayinin sözünden; ipucu yalnız "pencere isteniyor" bayrağıdır)."""
    q = norm(metin)
    r = {"pencere": None, "cati": None, "dis140": False, "istek": False}
    # çatı: varyant kodu, "çatı K/L", "katalog çatısı" (beyin/celik.cati_secimi)
    if katalog_aday:
        r["cati"] = celik.cati_secimi(metin, katalog_aday)
    # dış 140 (kurallar/model/secenekler/dis_karkas_140.json › bayi_ifadeleri)
    r["dis140"] = bool(_DIS140.search(q)) and not any(olumsuz_ya_da_soru(p) for p in _parcalar(metin) if _DIS140.search(norm(p)))
    # pencere
    olc = olculer(metin)
    pencere_soz = bool(_PENCERE_SOZ.search(q))
    if pencere_soz or olc or ipucu:
        ilgili = [p for p in _parcalar(metin) if _PENCERE_SOZ.search(norm(p)) or olculer(p) or _mahaller(norm(p), t)] or _parcalar(metin)
        adaylar = pencere_adaylari(t, y)
        suzgec = []
        if _VASISTAS.search(q) and not re.search(r"\bpencere", q):
            adaylar = [a for a in adaylar if a["vasistas"]]; suzgec.append("vasistas")
        mahaller = _mahaller(q, t)
        if mahaller:
            adaylar = [a for a in adaylar if a["mahal"] in mahaller]; suzgec.append("oda")
        ceph = _cepheler(q)
        if ceph:
            adaylar = [a for a in adaylar if a["cephe"] in ceph]; suzgec.append("cephe")
        eski = yeni = None
        if len(olc) >= 2:
            eski, yeni = olc[0], olc[-1]
            if not any((a["en"], a["yuk"]) == eski for a in adaylar) and any((a["en"], a["yuk"]) == olc[-1] for a in adaylar) and not _ESKI_YENI.search(q):
                eski, yeni = olc[-1], olc[0]
            adaylar = [a for a in adaylar if (a["en"], a["yuk"]) == eski] or adaylar; suzgec.append("eski_olcu")
        elif olc:
            yeni = olc[0]
        r["pencere"] = {"istek": True, "olcu": yeni, "adaylar": adaylar, "suzgec": suzgec, "mahaller": mahaller, "cepheler": ceph,
                        "olumsuz": any(olumsuz_ya_da_soru(p) for p in ilgili), "ekle_kaldir": bool(_EKLE.search(q)) and not olc,
                        "odalar": sorted({a["mahal"] for a in pencere_adaylari(t) if a["mahal"]})}
    r["istek"] = bool(r["pencere"] or r["cati"] or r["dis140"])
    return r


def hizli_istek(metin: str | None) -> bool:
    """LLM niyeti ne derse desin, metin çelik revizyon isteği taşıyor mu (ölçü, pencere sözü, çatı K/L, dış 140)?"""
    q = norm(metin)
    return bool(olculer(metin) or _PENCERE_SOZ.search(q) or _DIS140.search(q) or celik._CATI_SOZ.search(" " + q + " "))


def okuma_cevabi(metin: str | None, bekleyen: dict) -> dict | None:
    """Askıdaki okuma sorusunun cevabı. bekleyen.tur == "secim": {"secim": i} (0 tabanlı) | {"hicbiri": True} | None (cevap değil).
    bekleyen.tur == "olcu": {"olcu": (en, yük)} | {"hicbiri": True} | None. Buton kimliği q:okuma:<n> aynı metne çevrilir ("1", "2", "hiçbiri")."""
    q = norm(metin)
    if not q:
        return None
    if _HICBIRI.search(" " + q + " ") and len(q.split()) <= 4:
        return {"hicbiri": True}
    if bekleyen.get("tur") == "olcu":
        olc = olculer(metin)
        return {"olcu": olc[-1]} if olc else None
    n = len(bekleyen.get("adaylar") or [])
    soz = q.split()
    if len(soz) > 4:
        return None
    m = re.fullmatch(r"(\d)(?:\s*(?:\.|inci|nci|uncu|incisi|ncisi|numara|nolu|no|olsun|lu|li))?(?:\s+(?:olsun|numara|numarali|pencere))?", q)
    if m:
        i = int(m.group(1)) - 1
        return {"secim": i} if 0 <= i < n else None
    for w in soz:
        if w in _SAYI_SOZ:
            i = _SAYI_SOZ[w] - 1
            if 0 <= i < n and all(x in _SAYI_SOZ or x in ("olsun", "pencere", "numara", "numarali", "tane", "olan", "o", "su", "bu") for x in soz):
                return {"secim": i}
    return None


def aciklama(op: dict, adaylar: list[dict] | None = None) -> str:
    """Değişikliğin bayiye ve bağlam özetine giden kısa, numarasız anlatımı."""
    if op.get("op") == "pencere_olcu":
        return op.get("aciklama") or f"{op.get('aciklik')} penceresi {op.get('en')}/{op.get('yuk')}"
    if op.get("op") == "cati_varyanti":
        return f"çatı {op.get('kod')}"
    if op.get("op") == "dis_karkas_140":
        return "dış duvarlar 140'lık karkas (16,5 cm)"
    return str(op.get("op"))
