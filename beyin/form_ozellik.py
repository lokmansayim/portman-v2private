"""İE-20 PR-6 · Prefabrik talep formundaki standart dışı seçimlerin İş Emri'ne işlenmesi (LLM yok; kod karar verir).

Girdi taslağın `bina_ozellikleri`'dir; anahtarlar ve değerler formun kendi yazılarıdır (`kanal/talep_formu.OZELLIKLER`; ikisinin aynı
olduğunu `testler/kalici/test_prefabrik_formu.py` denetler). Yalnız birebir tanınan değer işlenir: LLM'in serbest yazdığı özellik
(ör. "Çatı Kaplaması: kiremit") bugünkü gibi yalnız kayıtta kalır.
  - Plana işlenen: pano yüksekliği 280 / 300 cm (`yapi.duvar_yuksekligi_cm`; D-14), iç duvar 100 mm (`yapi.duvar_kalinligi_cm.ic`; BK-18).
  - Teknik özelliklere yazılan (`ozellikler`; yükleme listesi ve kart modeli çatı kaplamasını buradan okur, D-74): çatı kaplaması
    opsiyonu, çatı rengi, ters tavan, iç cephede alçıpan.
  - Yalnız kayıtta kalan (`bina_ozellikleri`): dış duvar 160 mm (hazır planların aksları 100 mm duvara göre; Motor çizmez), pencere
    rengi, lata ve yalı baskı, çift kat mineral yün.
Formdaki seçim hazır planın kendi özelliğinden önce gelir (bayinin sözü): standart seçilmişse ve hazır planın şablonunda o satır standart
dışıysa (ör. PA-06: OSB + nem bariyeri + trapez, ters tavan, alçıpan) satır standarda döner. Şablonda satır yoksa ya da zaten standartsa
standart seçim hiçbir şeyi değiştirmez: o formun İş Emri bugünkü İş Emri'yle aynıdır.
"""
from __future__ import annotations

YUKSEKLIK_CM = {"280 cm": 280, "300 cm": 300}
IC_DUVAR_CM = {"100 mm": 10}
# formun yazısı → İş Emri'nin teknik özelliği (yükleme listesi "trapez", "kiremit", "osb", "sandviç" sözcüklerine bakar: prefabrik_liste)
CATI_KAPLAMASI = {"trapez sac": "Trapez Sac", "kiremit desen sac + OSB + nem bariyeri": "Kiremit Desen Sac + OSB + Nem Bariyeri",
                  "tek kat panel": "Tek Kat Panel", "shingle + OSB + membran": "Shingle + OSB + Membran", "sandviç panel": "Sandviç Panel"}
CATI_RENGI = {"antrasit gri": "Antrasit Gri", "kırmızı (RAL 3009)": "Kırmızı (RAL 3009)"}
TAVAN = {"alçıpan asma tavan": "Asma", "ters tavan": "Ters"}
SATIRLAR = {"Çatı Kaplaması": CATI_KAPLAMASI, "Çatı Kaplama Rengi": CATI_RENGI, "Tavan": TAVAN}
STANDART = {"Çatı Kaplaması": "trapez sac", "Çatı Kaplama Rengi": "antrasit gri", "Tavan": "alçıpan asma tavan"}      # D-74, D-88
# şablondaki satır standart mı: (geçmesi gereken sözcük, geçmemesi gerekenler); ör. "Trapez Saç" standart, "OSB + Nem Bariyeri + Trapez Saç" değil
STANDART_SOZCUK = {"Çatı Kaplaması": ("trapez", ("osb", "kiremit", "shingle", "sandvi", "panel", "membran", "bariyer")),
                   "Çatı Kaplama Rengi": ("antrasit", ()), "Tavan": ("asma", ("ters",))}
ALCIPAN = "iç duvarlarda alçıpan kaplama"
IC_CEPHE = "İç Cephe Kaplaması"


def _standart_mi(satir: str, deger) -> bool:
    var, yok = STANDART_SOZCUK[satir]
    d = str(deger or "").lower()
    return var in d and not any(x in d for x in yok)


def uygula(ie: dict, bina_ozellikleri: dict | None, onceki: dict | None = None) -> list[str]:
    """Formdaki seçimleri İş Emri'ne (yerinde) işler; dönen: plana işlenenlerin notları ("pano yüksekliği 280 cm").
    Prefabrik olmayan İş Emri'ne dokunmaz. `onceki` gönderilmiş son plandır: onda zaten olan değer yeniden not edilmez (revizyonda
    "değişiklik" diye okunmasın)."""
    bo = bina_ozellikleri or {}
    yapi = ie.get("yapi") or {}
    if yapi.get("sistem", "prefabrik") != "prefabrik":
        return []
    eski = (onceki or {}).get("yapi") or {}
    notlar = []
    h = YUKSEKLIK_CM.get(bo.get("Pano Yüksekliği"))
    if h and float(yapi.get("duvar_yuksekligi_cm", 250)) != h:
        yapi["duvar_yuksekligi_cm"] = h
        if float(eski.get("duvar_yuksekligi_cm", 250)) != h:
            notlar.append(f"pano yüksekliği {h} cm")
    ic = IC_DUVAR_CM.get(bo.get("İç Duvar"))
    kal = yapi.get("duvar_kalinligi_cm") or {}
    if ic and float(kal.get("ic", 6)) != ic:
        yapi["duvar_kalinligi_cm"] = {"dis": kal.get("dis", 10), **kal, "ic": ic}
        if float((eski.get("duvar_kalinligi_cm") or {}).get("ic", 6)) != ic:
            notlar.append(f"iç duvar {ic * 10} mm")
    mevcut = dict(ie.get("ozellikler") or {})
    oz = dict(mevcut)
    for satir, sozluk in SATIRLAR.items():
        v = bo.get(satir)
        if v not in sozluk:
            continue
        if v != STANDART[satir] or (mevcut.get(satir) and not _standart_mi(satir, mevcut[satir])):
            oz[satir] = sozluk[v]
    formdan = all(bo.get(satir) in sozluk for satir, sozluk in SATIRLAR.items())          # form üç seçimi de hep yazar
    if ALCIPAN in str(bo.get("Ek İstekler") or "").split("; "):
        oz[IC_CEPHE] = "Alçıpan"
    elif formdan and "alçıpan" in str(mevcut.get(IC_CEPHE) or "").lower():
        oz.pop(IC_CEPHE)                                                                 # formda alçıpan seçilmedi; şablonunki kalmaz
    if oz != mevcut:
        ie["ozellikler"] = oz
    return notlar
