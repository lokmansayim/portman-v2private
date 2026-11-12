"""İE-35 · CRM stok fiyatları → fiyat defteri (D-72, mühür M-15): tek fiyat kaynağı CRM.

    python3 araclar/crm_fiyat.py defter <anlık.json> <defter.json>       # CRM'in o günkü fiyatıyla defter (fiyatla/teklif --crm de bunu yapar)
    python3 araclar/crm_fiyat.py eksik <anlık.json> [--json <çıktı>]      # fiyatsız kalemler: CRM'de yok, fiyatı 0, birim sorusu
    python3 araclar/crm_fiyat.py denetle <ham.json> [--yaz <anlık.json>] [--onceki <anlık.json>]   # sunucunun günlük çekimi

Lokman, 9 Kasım 2026 13:10: "bunu kural olarak al ve mühürle bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları
çek"; "diğer tüm listeler konu dışı". Pencere de CRM'den fiyatlanır (13:15 kartı "Samet CRM'e eklesin").

- **Anlık görüntü:** CRM'in `POST /api/stok-fiyatlari` yanıtı (`{success, count, currency, generated_at, data: [...]}`). Sunucu her gün
  çeker (`vps/crm_fiyat.sh`, `portman-crm-fiyat.timer`); `denetle` biçimi sınar ve satırda yalnız `ALANLAR`'ı bırakır.
- **Eşleme:** `kurallar/fiyat/crm_esleme.json`. Defterin her kalemi (Motor'un liste anahtarı) bir CRM koduna ve hesaba bağlıdır;
  dosya fiyat yazmaz. Hesaplar: aynı, oran, çarp, boy (anahtardaki L; esas boy metre ya da kutu profilde 6 m, D-75), ağırlıklı
  ortalama, toplam; sonuç kuruşa yarım yukarı (kutu profil tam TL'ye, D-36).
- **Onay:** eşleme `birebir` ya da `kural` ise onaylı; `yakın` ve `birim varsayımı` öneridir (`fiyatla.py --oneri`); `birim sorusu`
  ve `CRM'de yok` fiyatsızdır. Kodun o günkü fiyatı 0 ya da boşsa, kod listede yoksa ya da birden çok satırdaysa kalem fiyatsızdır
  (fiyat uydurulmaz). Çırpı ipi Lokman'ın kararıyla 0 TL (D-65). `bekletme`: Lokman'ın kararıyla şimdilik fiyatsız, CRM'de fiyatı
  olsa da yazılmaz (banyo dolabı, D-75); Samet'e giden eksik listesine girmez.
- **KDV (D-76):** eşlemenin `kdv` bölümü varsa defterin her kaydı KDV oranını ve grubunu taşır (`kdv`, `kdv_grubu`). Grup sırayla:
  kalemin `kdv_grubu`'su, kodun `kdv.kodlar` kaydı, CRM satırının kategorisi (`kdv.kategoriler`). Grubu bulunmayan ya da kodları iki
  ayrı orana düşen kaydın oranı yoktur (None); oran uydurulmaz. CRM fiyatı KDV hariçtir; KDV'yi `araclar/fiyatla.py` hesaplar.
- **Çıktı:** `kurallar/fiyat/defter_2026-11.json` ile aynı şemada defter (`portman.fiyat_defteri/1`); `araclar/fiyatla.py` ve
  `araclar/teklif.py` onu okur. Yalnız standart kütüphane: sunucuda sistem python3'üyle koşar.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
ESLEME = KOK / "kurallar" / "fiyat" / "crm_esleme.json"
ALANLAR = ("id", "urunkodu", "urunadi", "olcu", "birim", "fiyat", "kategori")
ONAYLI = {"birebir", "kural"}
ONERI = {"yakın", "birim varsayımı"}
FIYATSIZ = {"birim sorusu", "CRM'de yok"}
HESAPLAR = {"ayni", "oran", "carp", "boy_m", "ort", "toplam"}
DURUM = {"birebir": "eşleşti", "kural": "hesap", "yakın": "yakın", "birim varsayımı": "birim varsayımı", "birim sorusu": "birim sorusu",
         "CRM'de yok": "kaynakta yok", "karar": "Patron verdi", "bekletme": "Lokman fiyat verecek"}
DUSUS_SINIRI = 0.8              # günlük çekimde kalem sayısı bir öncekinin %80'inin altına düşerse görüntü alınmaz


class CrmHatasi(ValueError):
    """Anlık görüntü ya da eşleme beklenen biçimde değil."""


def oku(p: Path | str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ── anlık görüntü ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _fiyat_mi(v) -> bool:
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0)


def zaman(A: dict) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(str(A.get("generated_at")))
    except ValueError:
        raise CrmHatasi(f"generated_at okunamadı: {A.get('generated_at')!r}") from None


def denetle(A, onceki: dict | None = None) -> dict:
    """Yanıtın biçimi; geçerse satırları yalnız `ALANLAR`'la döndürür (stok gibi başka alan görüntüye girmez). `onceki` verilirse kalem
    sayısı onun %80'inin altına düşmüşse durur (yarım yanıt eski fiyatların yerine geçmesin)."""
    if not isinstance(A, dict) or A.get("success") is not True:
        raise CrmHatasi("yanıtta success true değil")
    data = A.get("data")
    if not isinstance(data, list) or not data:
        raise CrmHatasi("yanıtta data listesi yok ya da boş")
    if A.get("count") is not None and A["count"] != len(data):
        raise CrmHatasi(f"count {A['count']}, data {len(data)} satır")
    if A.get("currency") not in ("TRY", "TL"):
        raise CrmHatasi(f"para birimi TRY değil: {A.get('currency')!r}")
    zaman(A)
    satirlar = []
    for i, x in enumerate(data, 1):
        if not isinstance(x, dict) or not isinstance(x.get("urunkodu"), str) or not x["urunkodu"].strip():
            raise CrmHatasi(f"{i}. satırda ürün kodu yok")
        if not _fiyat_mi(x.get("fiyat")):
            raise CrmHatasi(f"{x['urunkodu']}: fiyat sayı değil ya da eksi: {x.get('fiyat')!r}")
        satirlar.append({k: x.get(k) for k in ALANLAR})
    if onceki is not None and len(satirlar) < DUSUS_SINIRI * len(onceki.get("data") or []):
        raise CrmHatasi(f"kalem sayısı {len(onceki['data'])} → {len(satirlar)}; %{100 - DUSUS_SINIRI * 100:g}'den çok düştü, görüntü alınmadı")
    return {"success": True, "count": len(satirlar), "currency": A["currency"], "generated_at": A["generated_at"], "data": satirlar}


def anlik_oku(p: Path | str) -> dict:
    return denetle(oku(p))


# ── hesap ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _yuvarla(x: Decimal, adim: float | int = 0.01) -> float:
    a = Decimal(str(adim))
    return float((x / a).quantize(Decimal(1), ROUND_HALF_UP) * a)


def _boy(anahtar: str) -> Decimal:
    m = re.search(r"\| L (\d+(?:[.,]\d+)?)", anahtar)
    if not m:
        raise CrmHatasi(f"boy hesabı ister, anahtarda 'L <mm>' yok: {anahtar}")
    return Decimal(m.group(1).replace(",", "."))


def satir_bul(dizin: dict, kod: str, icerir: str | None = None) -> tuple[dict | None, str | None]:
    """(satır, None) ya da (None, durum). Kod listede yoksa ya da `icerir` süzgecinden sonra birden çok satırdaysa "CRM'de kod yok";
    fiyatı 0 ya da boşsa "CRM'de fiyat 0"."""
    adaylar = dizin.get(kod) or []
    if icerir:
        adaylar = [x for x in adaylar if icerir.lower() in (x.get("urunadi") or "").lower()]
    if len(adaylar) != 1:
        return None, "CRM'de kod yok"
    if not adaylar[0].get("fiyat"):
        return adaylar[0], "CRM'de fiyat 0"
    return adaylar[0], None


def hesapla(g: dict, dizin: dict, anahtar: str = "") -> dict:
    """Eşleme kaydının o günkü fiyatı: {fiyat, durum, kodlar, adlar, yontem}. Fiyatsızsa fiyat None, durum nedeni."""
    kodlar = g["kod"] if isinstance(g["kod"], list) else [g["kod"]]
    satirlar, sorun = [], None
    for k in kodlar:
        s, d = satir_bul(dizin, k, g.get("icerir"))
        sorun = sorun or d
        if s:
            satirlar.append(s)
    sonuc = {"kodlar": kodlar, "adlar": [s.get("urunadi") or "" for s in satirlar]}
    if sorun:
        return dict(sonuc, fiyat=None, durum=sorun)
    p = [Decimal(str(s["fiyat"])) for s in satirlar]
    h = g["hesap"]
    if h == "ayni":
        x = p[0]
    elif h == "oran":
        x = p[0] * Decimal(str(g["pay"])) / Decimal(str(g["payda"]))
    elif h == "carp":
        x = p[0] * Decimal(str(g["carpan"]))
    elif h == "boy_m":                                           # esas boy: metre (1000) ya da kutu profilde 6 m (6000, D-75)
        x = p[0] * _boy(anahtar) / Decimal(str(g.get("esas_boy_mm", 1000)))
    elif h == "ort":
        w = [Decimal(str(a)) for a in g["agirlik"]]
        x = sum(a * b for a, b in zip(p, w)) / sum(w)
    elif h == "toplam":
        x = sum(p)
    else:
        raise CrmHatasi(f"bilinmeyen hesap {h!r}: {anahtar}")
    return dict(sonuc, fiyat=_yuvarla(x, g.get("yuvarlama", 0.01)), durum=None)


def kdv_bul(K: dict | None, g: dict, dizin: dict) -> tuple[float | None, str | None]:
    """Kaydın KDV oranı ve grubu (D-76): (oran, grup) ya da (None, None). Grup sırayla kaydın `kdv_grubu`'su, kodun `K.kodlar` kaydı
    (null: grubu bilinmiyor), CRM satırının kategorisi (`K.kategoriler`). Kodları ayrı orana düşen kaydın oranı yok; kodsuz kaydın grubu
    yalnız `kdv_grubu`'ndan."""
    if not K:
        return None, None
    grup = g.get("kdv_grubu")
    if grup is None:
        kodlar = g.get("kod") if isinstance(g.get("kod"), list) else [g.get("kod")]
        bulunan: set = set()
        for k in kodlar:
            if not k:
                return None, None
            if k in K["kodlar"]:
                bulunan.add(K["kodlar"][k])
                continue
            satirlar = [x for x in dizin.get(k) or [] if not g.get("icerir") or g["icerir"].lower() in (x.get("urunadi") or "").lower()]
            kat = {x.get("kategori") for x in satirlar}
            bulunan.add(K["kategoriler"].get(kat.pop()) if len(kat) == 1 else None)
        if None in bulunan or len({K["gruplar"][b] for b in bulunan}) != 1:
            return None, None
        grup = " + ".join(sorted(bulunan))
        return K["gruplar"][next(iter(bulunan))], grup
    return K["gruplar"][grup], grup


def esleme_denetle(E: dict) -> list[str]:
    """Eşleme dosyasının tutarlılığı (testler ve `defter_uret` çağırır): boş liste beklenir."""
    sorun = []
    if (E.get("kaynak") or {}).get("tek_kaynak") != "CRM":
        sorun.append("kaynak.tek_kaynak CRM değil (D-72, M-15)")

    K = E.get("kdv")
    if K is not None:                                           # D-76
        G = K.get("gruplar") or {}
        if not K.get("dayanak") or not G or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v < 1 for v in G.values()):
            sorun.append("kdv: dayanak ve gruplar (0 ile 1 arası oran) olur")
        for yer in ("kategoriler", "kodlar"):
            for k, v in (K.get(yer) or {}).items():
                if v is not None and v not in G or v is None and yer == "kategoriler":
                    sorun.append(f"kdv › {yer} › {k}: bilinmeyen grup {v!r}")

    def kayit(yer: str, g: dict, anahtar: str = "") -> None:
        if "kdv_grubu" in g and (K is None or g["kdv_grubu"] not in (K.get("gruplar") or {})):
            sorun.append(f"{yer}: bilinmeyen KDV grubu {g['kdv_grubu']!r}")
        tur = g.get("esleme")
        if tur not in E["esleme_turleri"]:
            sorun.append(f"{yer}: bilinmeyen eşleme türü {tur!r}")
        if tur == "karar":
            if g.get("kod") is not None or g.get("sabit") is None or not g.get("dayanak"):
                sorun.append(f"{yer}: karar kaydı kodsuz, sabit ve dayanaklı olur")
            return
        if tur == "CRM'de yok":
            if g.get("kod") is not None:
                sorun.append(f"{yer}: CRM'de yok ama kodu var")
            return
        if tur == "bekletme":
            if g.get("kod") is not None or not g.get("dayanak"):
                sorun.append(f"{yer}: bekletme kaydı kodsuz ve dayanaklı olur")
            return
        kodlar = g.get("kod") if isinstance(g.get("kod"), list) else [g.get("kod")]
        if not kodlar or not all(isinstance(k, str) and k for k in kodlar):
            sorun.append(f"{yer}: kod yok")
        h = g.get("hesap")
        gerek = {"oran": ("pay", "payda"), "carp": ("carpan",), "ort": ("agirlik",)}.get(h, ())
        if h not in HESAPLAR or any(g.get(a) in (None, 0) for a in gerek):
            sorun.append(f"{yer}: hesap {h!r} eksik")
        if h in ("ort", "toplam") and len(kodlar) < 2 or h not in ("ort", "toplam") and len(kodlar) != 1:
            sorun.append(f"{yer}: {h} için kod sayısı {len(kodlar)}")
        if h == "ort" and len(g.get("agirlik") or []) != len(kodlar):
            sorun.append(f"{yer}: ağırlık sayısı kod sayısıyla aynı değil")
        if h == "boy_m":
            try:
                _boy(anahtar)
            except CrmHatasi as e:
                sorun.append(f"{yer}: {e}")
        if "esas_boy_mm" in g and (h != "boy_m" or not isinstance(g["esas_boy_mm"], (int, float)) or g["esas_boy_mm"] <= 0):
            sorun.append(f"{yer}: esas_boy_mm yalnız boy hesabında ve sıfırdan büyük olur")

    for hat, H in E["hatlar"].items():
        for k, g in H["kalemler"].items():
            kayit(f"{hat} › {k}", g, k)
        for b in H.get("bantlar") or []:
            for a in b["araliklar"]:
                kayit(f"{hat} › bant {b['kalem']} {a['en_mm']}", a)
        for b in H.get("boy_onerileri") or []:
            kayit(f"{hat} › boy {b.get('kalem') or b.get('kalem_baslar')}", b)
            if "boy_adim_mm" in b and (isinstance(b["boy_adim_mm"], bool) or not isinstance(b["boy_adim_mm"], (int, float))
                                       or b["boy_adim_mm"] <= 0):
                sorun.append(f"{hat} › boy {b.get('kalem') or b.get('kalem_baslar')}: boy_adim_mm sıfırdan büyük sayı olur")
        if H.get("makas_kurali"):
            kayit(f"{hat} › makas", H["makas_kurali"])
    return sorun


# ── defter ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _gun(t: datetime.datetime) -> str:
    return t.strftime("%d.%m.%Y")


def _not(g: dict, h: dict | None, ek: str = "") -> str:
    parca = [g.get("not") or ""]
    if h and h.get("kodlar") and h["kodlar"] != [None]:
        parca.append("CRM " + " + ".join(h["kodlar"]))
    if ek:
        parca.append(ek)
    return "; ".join(p for p in parca if p)


def defter_uret(A: dict, E: dict | None = None) -> dict:
    """Anlık görüntü (A, `denetle`'den geçmiş) ve eşleme (E) → defter (`defter_2026-11.json` şeması). Bant, boy ve makas kuralının
    o günkü fiyatı yoksa kural deftere girmez (satır fiyatsız kalır) ve `crm.fiyatsiz_kurallar`'da sayılır."""
    E = E if E is not None else oku(ESLEME)
    if sorun := esleme_denetle(E):
        raise CrmHatasi("eşleme dosyası tutarsız: " + "; ".join(sorun[:5]))
    t = zaman(A)
    dizin: dict[str, list[dict]] = {}
    for x in A["data"]:
        dizin.setdefault(x["urunkodu"].strip(), []).append(x)
    kaynaklar = {
        "CRM": {"ad": "CRM stok fiyatları API (POST /api/stok-fiyatlari)", "kisa": f"CRM stok fiyatları, {_gun(t)}",
                "tarih": t.date().isoformat(), "patron_verdi": True,
                "not": f"D-72: tek fiyat kaynağı (Lokman 9 Kasım 2026 13:10, mühür M-15); anlık görüntü {A['generated_at']}, {len(A['data'])} kalem"},
        "PATRON": {"ad": "Lokman'ın kararı", "kisa": "Lokman'ın kararı, 06.11.2026", "tarih": "2026-11-06", "patron_verdi": True,
                   "not": "D-65: çırpı ipi hediye, 0 TL"},
    }
    sayim: dict[str, int] = {}
    fiyatsiz_kurallar: list[dict] = []
    K = E.get("kdv")

    def kalem(k: str, g: dict) -> dict:
        tur = g["esleme"]
        if tur == "karar":
            d = {"fiyat": g["sabit"], "birim": g["birim"], "kaynak": "PATRON", "kaynak_satir": None, "kaynak_kalem": None,
                 "durum": DURUM[tur], "onay": True, "not": _not(g, None, g["dayanak"])}
        elif tur == "CRM'de yok":
            d = {"fiyat": None, "birim": g["birim"], "kaynak": None, "kaynak_satir": None, "kaynak_kalem": None,
                 "durum": DURUM[tur], "onay": False, "not": _not(g, None, "CRM'e eklenmeli (D-72)")}
        elif tur == "bekletme":
            d = {"fiyat": None, "birim": g["birim"], "kaynak": None, "kaynak_satir": None, "kaynak_kalem": None,
                 "durum": DURUM[tur], "onay": False, "not": _not(g, None, g["dayanak"])}
        else:
            h = hesapla(g, dizin, k)
            fiyatsiz = tur in FIYATSIZ or h["fiyat"] is None
            d = {"fiyat": None if fiyatsiz else h["fiyat"], "birim": g["birim"], "kaynak": None if fiyatsiz else "CRM",
                 "kaynak_satir": h["kodlar"], "kaynak_kalem": " + ".join(h["adlar"]) or None,
                 "durum": h["durum"] if h["fiyat"] is None else DURUM[tur], "onay": not fiyatsiz and tur in ONAYLI,
                 "not": _not(g, h)}
        if K:                                                   # D-76: oran ve grup (fiyatsız kalemde de; fiyat gelince geçerli)
            d["kdv"], d["kdv_grubu"] = kdv_bul(K, g, dizin)
        sayim[d["durum"]] = sayim.get(d["durum"], 0) + 1
        return d

    def kural(yer: str, g: dict, anahtar: str = "") -> dict | None:
        h = hesapla(g, dizin, anahtar)
        if h["fiyat"] is None:
            fiyatsiz_kurallar.append({"hat": hat, "yer": yer, "kodlar": h["kodlar"], "durum": h["durum"]})
            return None
        return {"fiyat": h["fiyat"], "onay": g["esleme"] in ONAYLI, "kaynak_satir": h["kodlar"], "kaynak_kalem": " + ".join(h["adlar"]),
                "dayanak": _not(g, h), **(dict(zip(("kdv", "kdv_grubu"), kdv_bul(K, g, dizin))) if K else {})}

    hatlar = {}
    for hat, H in E["hatlar"].items():
        cikti: dict = {"anahtar": H["anahtar"]}
        if H.get("kg_notu"):
            cikti["kg_notu"] = H["kg_notu"]
        cikti["kalemler"] = {k: kalem(k, g) for k, g in H["kalemler"].items()}
        bantlar = []
        for b in H.get("bantlar") or []:
            araliklar = []
            for a in b["araliklar"]:
                f = kural(f"bant {b['kalem']} {a['en_mm']}", a)
                if f:
                    araliklar.append({"en_mm": a["en_mm"], "alt_haric": a["alt_haric"], "fiyat": f["fiyat"], "onay": f["onay"],
                                      "dayanak": f["dayanak"], **{x: f[x] for x in ("kdv", "kdv_grubu") if x in f}})
            if araliklar:
                bantlar.append({k: b[k] for k in ("kalem", "kalinlik_mm", "yukseklik_mm")} | {"kaynak": "CRM", "araliklar": araliklar})
        cikti["bantlar"] = bantlar
        if "boy_onerileri" in H:
            boy = []
            for b in H["boy_onerileri"]:
                f = kural(f"boy {b.get('kalem') or b.get('kalem_baslar')}", b)
                if f:
                    boy.append({a: b[a] for a in ("kalem", "kalem_baslar") if a in b}
                               | {"boy_mm": b["boy_mm"], "fiyat": f["fiyat"], **{a: b[a] for a in ("yuvarlama", "kapatma_m", "boy_adim_mm") if a in b},
                                  "kaynak": "CRM", "kaynak_satir": f["kaynak_satir"], "kaynak_kalem": f["kaynak_kalem"], "onay": f["onay"],
                                  "dayanak": f["dayanak"], **{x: f[x] for x in ("kdv", "kdv_grubu") if x in f}})
            cikti["boy_onerileri"] = boy
        if H.get("makas_kurali"):
            m = H["makas_kurali"]
            f = kural("makas", m)
            if f:
                cikti["makas_kurali"] = {"kalem_baslar": m["kalem_baslar"], "kg_m": m["kg_m"], "kg_fiyat": f["fiyat"], "sacak_mm": m["sacak_mm"],
                                         "kaynak": "CRM", "kaynak_satir": f["kaynak_satir"], "kaynak_kalem": f["kaynak_kalem"],
                                         "onay": f["onay"], "dayanak": f["dayanak"], **{x: f[x] for x in ("kdv", "kdv_grubu") if x in f}}
        cikti["atla"] = H.get("atla") or []
        hatlar[hat] = cikti
    return {
        "sema": "portman.fiyat_defteri/1",
        "surum": f"CRM {t.strftime('%d.%m.%Y %H:%M')}",
        "aciklama": ("CRM stok fiyatlarından üretilen defter (İE-35, D-72): `araclar/crm_fiyat.py`, eşleme "
                     f"`kurallar/fiyat/crm_esleme.json` ({E.get('surum')}). Elle düzeltilmez; düzeltme eşlemeye ya da CRM'e girer."),
        "para_birimi": "TL",
        "kdv": ({"dayanak": K["dayanak"], "not": "CRM fiyatı KDV hariç; kaydın oranı `kdv`, grubu `kdv_grubu` (None: oran yok, uydurulmaz)",
                 "gruplar": K["gruplar"]} if K else "CRM yanıtında KDV yazmıyor"),
        "onay_kurali": ("Tek kaynak CRM (D-72, M-15). onay true: eşleme birebir ya da Lokman'ın onaylı hesap kuralı. onay false: yakın "
                        "ürün ya da birim varsayımı; araclar/fiyatla.py bunları yalnız --oneri ile uygular. Fiyatı 0 olan, CRM'de "
                        "bulunmayan ve birimi anlaşılmayan kalem fiyatsız."),
        "kaynaklar": kaynaklar,
        "hatlar": hatlar,
        "m2_yontemi": {"fiyatlar": [], "not": "Basit yöntemin m² fiyatları yok; araç --m2-fiyat ile alır."},
        "crm": {"generated_at": A["generated_at"], "kalem": len(A["data"]), "esleme_surumu": E.get("surum"),
                "durumlar": dict(sorted(sayim.items())), "fiyatsiz_kurallar": fiyatsiz_kurallar},
    }


def eksikler(A: dict, E: dict | None = None) -> dict:
    """CRM'e eklenecek ya da fiyatı girilecek kalemler (Samet'e liste): CRM'de yok, fiyatı 0, kod bulunamadı, birim sorusu. Lokman'ın
    beklettiği kalem (`bekletme`, D-75) Samet'in işi değil, listeye girmez."""
    D = defter_uret(A, E)
    gruplar: dict[str, list[dict]] = {}
    for hat, H in D["hatlar"].items():
        for k, g in H["kalemler"].items():
            if g["fiyat"] is None and g["durum"] != DURUM["bekletme"]:
                gruplar.setdefault(g["durum"], []).append({"hat": hat, "kalem": k, "kodlar": g["kaynak_satir"], "not": g["not"]})
    for r in D["crm"]["fiyatsiz_kurallar"]:
        gruplar.setdefault(r["durum"], []).append({"hat": r["hat"], "kalem": r["yer"], "kodlar": r["kodlar"], "not": "kural"})
    return {"generated_at": A["generated_at"], "surum": D["surum"], "gruplar": gruplar}


# ── komut ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _yaz(yol: Path | str, veri: dict) -> None:
    p = Path(yol)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="ne", required=True)
    a = alt.add_parser("defter"); a.add_argument("anlik"); a.add_argument("cikti")
    a = alt.add_parser("eksik"); a.add_argument("anlik"); a.add_argument("--json")
    a = alt.add_parser("denetle"); a.add_argument("ham"); a.add_argument("--yaz"); a.add_argument("--onceki")
    o = ap.parse_args(argv)
    try:
        if o.ne == "denetle":
            A = denetle(oku(o.ham), oku(o.onceki) if o.onceki else None)
            sifir = sum(1 for x in A["data"] if not x["fiyat"])
            print(f"CRM {A['generated_at']}: {A['count']} kalem, {sifir} kalemde fiyat 0")
            if o.yaz:
                _yaz(o.yaz, A)
            return 0
        A = anlik_oku(o.anlik)
        if o.ne == "defter":
            D = defter_uret(A)
            _yaz(o.cikti, D)
            print(f"defter {D['surum']}: " + ", ".join(f"{k} {v}" for k, v in D["crm"]["durumlar"].items())
                  + (f"; fiyatsız kural {len(D['crm']['fiyatsiz_kurallar'])}" if D["crm"]["fiyatsiz_kurallar"] else ""))
            return 0
        X = eksikler(A)
        for durum, satirlar in sorted(X["gruplar"].items()):
            print(f"== {durum} ({len(satirlar)})")
            for s in satirlar:
                print(f"   {s['hat']} · {s['kalem']}" + (f" · CRM {' + '.join(s['kodlar'])}" if s["kodlar"] else ""))
        if o.json:
            _yaz(o.json, X)
        return 0
    except (CrmHatasi, json.JSONDecodeError, OSError) as e:
        print(f"DUR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
