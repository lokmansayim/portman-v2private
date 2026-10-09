"""İE-04 · Seçenek üretimi: aday kaydından talebe uyan adayları süzer, sabit ağırlıkla puanlar, hesabı yazar.

LLM yok. Sayılar aday kaydındaki özetten gelir (Motor çıktısından kaydedilmiş); LLM sayı üretmez.
Eşikler ve ağırlıklar GEÇİCİDİR: alan tanımı K-A1, sıralama ağırlıkları İE-04 açık kararı. Karar gelince yalnız bu dosyadaki
sabitler değişir; mesaj katmanı ve kayıt biçimi değişmez.
"""
from __future__ import annotations
import hashlib

ALAN_TOLERANS = 0.10          # K-A1 bekliyor: bayinin m²'si katalog m²'siyle ±%10 içinde eşleşir
EN_COK_SUNUM = 10             # WhatsApp liste mesajı en çok 10 satır
EN_COK_GORSEL = 3             # bileşik görselde ve butonlarda en çok 3 aday
GEREKEN_ADAY = 3              # A2: üç geçerli aday yoksa sayı tamamlanmaz, sistem durumu söyler
AGIRLIKLAR = {"alan_puan_basi_yuzde": 2.0, "alan_en_cok_kesinti": 40.0, "veranda_yok": 15.0, "oncelik_ikramiyesi": 10.0}
ONCELIKLER = {"butce": "bütçe", "yasam": "yaşam alanı", "montaj": "kısa montaj"}


def set_id(kaynak_mesaj_id: str) -> str:
    """Seçenek seti kimliği: buton kimlikleri s:<set>:<kod> bunu taşır; veritabanı sırası gerekmez."""
    return "ss_" + hashlib.sha256(str(kaynak_mesaj_id).encode()).hexdigest()[:16]


def _f(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def uygun_adaylar(katalog, ts: dict) -> list[dict]:
    """Talep taslağına (oda_programi + alan_m2 | dis_olcu | pano) uyan görünür adaylar. Alan eşleşmesi katalog m²'ye göre (K-A1)."""
    oda = ts.get("oda_programi")
    alan = _f(ts.get("alan_m2"))
    nx = ny = None
    if ts.get("pano") and ts["pano"].get("nx") and ts["pano"].get("ny"):
        nx, ny = float(ts["pano"]["nx"]), float(ts["pano"]["ny"])
    yapi = ts.get("yapi_turu")
    out = []
    for a in katalog.gorunur_adaylar():
        if oda and a.get("oda_programi") and a["oda_programi"] != oda:
            continue
        if yapi == "celik" and a.get("yapi_turu", "prefabrik") != "celik":
            continue
        if yapi == "prefabrik" and a.get("yapi_turu", "prefabrik") != "prefabrik":
            continue
        km2 = _f(a.get("katalog_m2"))
        if alan is not None:
            if km2 is None or abs(km2 - alan) > ALAN_TOLERANS * alan:
                continue
        elif nx is not None:
            g = (a.get("ozet") or {}).get("grid") or {}
            if abs(float(g.get("x_pano") or 0) - nx) > 0.5 or abs(float(g.get("y_pano") or 0) - ny) > 0.5:
                continue
        else:
            continue
        out.append(a)
    return out


def puanla(adaylar: list[dict], ts: dict) -> list[dict]:
    """Sabit ağırlıkla puan; her adayda hesap satırı. Sıralama puana, eşitlikte alan yakınlığına göre."""
    alan = _f(ts.get("alan_m2"))
    oncelik = ts.get("oncelik")
    veranda_ist = bool((ts.get("veranda") or {}).get("istiyor"))
    W = AGIRLIKLAR
    if oncelik == "butce":
        hedef = min((_f(a.get("kapali_m2")) for a in adaylar if _f(a.get("kapali_m2")) is not None), default=None)
        ikramiye = lambda a: _f(a.get("kapali_m2")) == hedef
    elif oncelik == "yasam":
        salon = lambda a: max((_f(v) or 0) for k, v in ((a.get("ozet") or {}).get("odalar") or {}).items()
                              if any(x in k.upper() for x in ("SALON", "YASAM", "YAŞAM", "OTURMA"))) if (a.get("ozet") or {}).get("odalar") else 0
        hedef = max((salon(a) for a in adaylar), default=None)
        ikramiye = lambda a: salon(a) == hedef
    elif oncelik == "montaj":
        hedef = min((int((a.get("ozet") or {}).get("pano") or 10**6) for a in adaylar), default=None)
        ikramiye = lambda a: int((a.get("ozet") or {}).get("pano") or 10**6) == hedef
    else:
        ikramiye = lambda a: False
    sonuc = []
    for a in adaylar:
        puan, hesap = 100.0, []
        km2 = _f(a.get("katalog_m2"))
        if alan is not None and km2 is not None and alan > 0:
            fark = abs(km2 - alan) / alan * 100
            kes = min(W["alan_puan_basi_yuzde"] * fark, W["alan_en_cok_kesinti"])
            puan -= kes; hesap.append(f"alan farkı %{fark:.0f} → −{kes:.0f}")
        if veranda_ist and not (_f(a.get("veranda_m2")) or 0) > 0:
            puan -= W["veranda_yok"]; hesap.append(f"veranda yok → −{W['veranda_yok']:.0f}")
        if oncelik in ONCELIKLER and ikramiye(a):
            puan += W["oncelik_ikramiyesi"]; hesap.append(f"{ONCELIKLER[oncelik]} önceliği → +{W['oncelik_ikramiyesi']:.0f}")
        sonuc.append({**a, "puan": int(round(max(0.0, min(100.0, puan)))), "hesap": "; ".join(hesap) or "kesinti yok"})
    sonuc.sort(key=lambda a: (-a["puan"], abs((_f(a.get("katalog_m2")) or 0) - (alan or 0)), str(a["kod"])))
    for i, a in enumerate(sonuc, 1):
        a["sira"] = i
    return sonuc


def set_kaydi(kaynak_mesaj_id: str, siralanmis: list[dict], ts: dict) -> dict:
    """Konuşma durumuna ve secenek_setleri tablosuna yazılan set (şablon yolu ve büyük alanlar hariç)."""
    return {"id": set_id(kaynak_mesaj_id), "durum": "acik", "kaynak_mesaj_id": kaynak_mesaj_id,
            "oncelik": ts.get("oncelik"), "agirliklar": dict(AGIRLIKLAR),
            "adaylar": [{k: a.get(k) for k in ("kod", "sira", "puan", "hesap", "referans_model", "oda_programi", "katalog_m2",
                                                 "kapali_m2", "veranda_m2", "durum", "gorsel")} for a in siralanmis[:EN_COK_SUNUM]]}


def kisa_ad(a: dict) -> str:
    """Liste satırı başlığı (≤24): 'P9401 · 94 m²'."""
    m2 = a.get("katalog_m2")
    return f"{a['kod']} · {m2} m²"[:24] if m2 is not None else str(a["kod"])[:24]


def aciklama(a: dict) -> str:
    """Liste satırı açıklaması (≤72): oda programı, kapalı alan, veranda, puan."""
    p = [a.get("oda_programi") or ""]
    if a.get("kapali_m2") is not None:
        p.append(f"kapalı {a['kapali_m2']} m²")
    p.append(f"veranda {a['veranda_m2']} m²" if (_f(a.get("veranda_m2")) or 0) > 0 else "verandasız")
    p.append(f"puan {a.get('puan')}")
    return " · ".join(x for x in p if x)[:72]


def mesaj_metni(siralanmis: list[dict], ts: dict, gerekli: int = GEREKEN_ADAY) -> str:
    """Seçenek mesajının gövdesi: ilk üç aday puan ve hesabıyla; üçten az geçerli aday varsa durum açıkça yazılır."""
    n = len(siralanmis)
    satirlar = []
    for a in siralanmis[:EN_COK_GORSEL]:
        satirlar.append(f"{a['sira']}. {a['kod']} · {a.get('katalog_m2')} m² katalog"
                        + (f", kapalı {a['kapali_m2']}" if a.get("kapali_m2") is not None else "")
                        + (f", veranda {a['veranda_m2']}" if (_f(a.get("veranda_m2")) or 0) > 0 else "")
                        + f" · puan {a['puan']} ({a['hesap']})")
    bas = f"{ts.get('alan_m2'):g} m² civarı {ts.get('oda_programi')}" if _f(ts.get("alan_m2")) is not None else (ts.get("oda_programi") or "talebiniz")
    onc = f" Öncelik: {ONCELIKLER.get(ts.get('oncelik'), 'belirtilmedi')}." if ts.get("oncelik") in ONCELIKLER else ""
    if n < gerekli:
        durum = (f"Bugün bu tanıma uyan doğrulanmış aday sayısı {n} (hedef {gerekli}); sayı tamamlanınca liste genişleyecek."
                 if n else f"Bugün bu tanıma uyan doğrulanmış aday yok.")
    else:
        durum = f"Kurallardan geçen {n} seçenek var."
    govde = f"{bas} için seçenekler.{onc} {durum}"
    if satirlar:
        govde += "\n\n" + "\n".join(satirlar) + "\n\nBirini seçin ya da yazın (örn. \"P9401 olsun\"); ölçü değişikliği de yazabilirsiniz."
    return govde[:1024]
