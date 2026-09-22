"""Kural katmanı: Talep (LLM çıktısı) + konuşma durumu + bayi kaydı → Karar.

Burada LLM yok. Her karar deterministik ve gerekçeli. Geometri motoru ayrı (İş Emri'ni o çizer).
"""
from __future__ import annotations
import json, math, time
from pathlib import Path

from .sema import Talep, Karar
from .katalog import Katalog
from .konusma import Konusma, MAX_REVIZYON, MAX_SORU
from . import varyant

MOD = 125.5
ROOT = Path(__file__).resolve().parent.parent
BAYI_JSON = Path(__file__).resolve().parent / "veri" / "bayiler.json"
# Onaylı örnek şablonlar: (grid nx, ny, oda programı) → İş Emri dosyası
GRID_SABLON = {(6.0, 8.0, "2+1"): "ALTIN_2plus1_6x8.json", (6.0, 8.5, "2+1"): "YAN_VERANDALI_2plus1_6x8p5.json",
               (6.0, 6.0, "2+1"): "P6001_2plus1_6x6.json"}
YONLENDIRME = "Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak."


def bayileri_yukle() -> dict:
    """Bayi kaydı. Hosting'de PORTMAN_NUMARALAR_JSON (panelin numaralar.json'u: {numara: {ad, ...}}) esas alınır;
    yoksa test kaydı veri/bayiler.json."""
    import os
    yol = os.environ.get("PORTMAN_NUMARALAR_JSON")
    if yol and Path(yol).exists():
        ham = json.loads(Path(yol).read_text(encoding="utf-8"))
        out = {}
        for numara, v in (ham.items() if isinstance(ham, dict) else []):
            if not isinstance(v, dict):
                continue
            ad = str(v.get("ad") or v.get("isim") or numara)
            out[str(numara)] = {"kod": str(v.get("kod") or numara[-4:]), "ad": ad, "firma": str(v.get("firma") or ""),
                                "rol": "patron" if ad.strip().lower() == "patron" else "bayi"}
        return out
    return json.loads(BAYI_JSON.read_text(encoding="utf-8")) if BAYI_JSON.exists() else {}


def pano_sayisi(metre: float, kose_cm: float) -> float:
    """Metre → pano adedi (0,5 adım). kose_cm: o kenardaki toplam köşe payı (20 kısa / 10 uzun)."""
    return round(max(1.0, (metre * 100 - kose_cm) / MOD) * 2) / 2


def dis_olcu_cm(nx: float, ny: float) -> tuple[float, float]:
    return MOD * nx + 20, MOD * ny + 10


def fmt_m(cm: float) -> str:
    return f"{cm / 100:.2f}".replace(".", ",") + " m"


def karar_ver(talep: Talep, k: Konusma, bayi: dict | None, katalog: Katalog) -> Karar:
    t = talep
    k.not_dus("gelen", t.ozet, {"niyet": t.niyet, "guven": t.guven})

    # 0) yalnız kayıtlı bayiler
    if bayi is None:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="kayıtsız numara",
                                mesaj="Bu hat PortatifEv'in kayıtlı bayilerine hizmet verir. Kayıt ve bilgi için lütfen Lokman Bey ile iletişime geçin."))
    ad = bayi.get("ad", "")

    # 1) niyete göre
    if t.niyet == "selam":
        return _bitir(k, Karar(eylem="cevapla", gerekce="selam",
                                mesaj=f"Merhaba {ad}. Hangi model ya da ölçü için ön onay planı hazırlayalım? Örnek: \"P6001 aynalı\" veya \"7x4 m, 2+1, ön verandalı\"."))
    if t.niyet == "soru":
        ek = " Açık bir plan talebiniz devam ediyor; ölçü/model bilgisini yazınca planı hazırlarım." if k.d["asama"] == "topluyor" else ""
        return _bitir(k, Karar(eylem="cevapla", gerekce="genel soru",
                                mesaj="Fiyat, süre ve teslim bilgisi ön onaylı planın ardından teklifle gelir. Plan için model kodu ya da ölçü/oda programı yazmanız yeterli." + ek))
    if t.niyet == "diger":
        return _bitir(k, Karar(eylem="cevapla", gerekce="anlaşılmadı",
                                mesaj="Anlayamadım. Ön onay planı için model kodu (örn. P6001) ya da ölçü ve oda programı (örn. 7x4 m, 2+1) yazabilirsiniz."))
    if t.niyet == "onay":
        if k.d["asama"] == "onay_bekliyor" and k.d.get("son_is_emri"):
            k.d["asama"] = "onaylandi"
            return _bitir(k, Karar(eylem="cevapla", gerekce="plan onaylandı", revizyon=k.d["revizyon"],
                                    mesaj=f"Onayınız kaydedildi ({k.d['son_is_emri'].get('is_emri_no')}, revizyon {k.d['revizyon']}). Teklif aşamasına geçiliyor."))
        return _bitir(k, Karar(eylem="cevapla", gerekce="onaylanacak plan yok",
                                mesaj="Onaylanacak açık bir plan görünmüyor. Yeni plan için model kodu ya da ölçü yazabilirsiniz."))
    if t.niyet == "red":
        if k.d["asama"] in ("onay_bekliyor", "uretildi"):
            k.d["asama"] = "revizyon"
            return _bitir(k, Karar(eylem="sor", soru_alani="revizyon_ne", gerekce="plan reddedildi",
                                    mesaj="Anladım. Neyi değiştirelim? (pencere, kapı, veranda, oda yerleşimi, ölçü…)"))
        k.sifirla()
        return _bitir(k, Karar(eylem="cevapla", gerekce="iptal", mesaj="Talep kapatıldı. Yeni bir plan istediğinizde yazmanız yeterli."))

    # 2) yeni_talep / revizyon
    if t.niyet == "revizyon" and k.d.get("son_is_emri"):
        k.d["revizyon"] += 1
        if k.d["revizyon"] > MAX_REVIZYON:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="revizyon sınırı",
                                    mesaj=f"Bu plan için {MAX_REVIZYON} revizyon hakkı doldu. " + YONLENDIRME))
    elif t.niyet == "yeni_talep" and k.d["asama"] in ("uretildi", "onay_bekliyor", "onaylandi", "yonlendirildi"):
        k.sifirla()  # önceki proje kapandı ya da insana devredildi; yeni talep
    elif t.niyet == "yeni_talep" and t.katalog_kodu and k.d["taslak"].get("katalog_kodu") \
            and Katalog.kod_normalize(t.katalog_kodu) != Katalog.kod_normalize(k.d["taslak"]["katalog_kodu"]):
        k.sifirla()  # başka bir modele geçti
    # askıda kalan pencere sorusu cevaplanmadan başka bir istek geldiyse: pencere değişikliğini düşür, bayiye söyle
    dusen_not = ""
    if k.d.get("son_soru_alani") in ("pencere_mahal", "pencere_olcu") and not t.pencereler \
            and not any(v.tur.startswith("pencere") for v in t.varyantlar):
        k.d["taslak"].pop("pencereler", None); k.d["son_soru_alani"] = None
        dusen_not = "Önceki pencere değişikliğini netleştirmediğiniz için uygulamadım; isterseniz sonra ekleriz. "
    k.birlestir(t.model_dump())
    k.d["asama"] = "topluyor"
    ts = k.d["taslak"]
    if dusen_not:
        ts["_on_not"] = dusen_not

    # 2a) katalog modeli
    if ts.get("katalog_kodu"):
        model = katalog.bul(ts["katalog_kodu"])
        if model is None:
            return _soru(k, "katalog_kodu", f"Katalogda \"{ts['katalog_kodu']}\" kodlu model bulamadım. Kodu kontrol eder misiniz? (örn. P6001, P7401, Ç8201)")
        yol = katalog.sablon_yolu(model["code"])
        if yol is None:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="şablon kodlanmamış",
                                    mesaj=f"{Katalog.kisa(model)} katalogda kayıtlı; çizim şablonu sisteme henüz işlenmedi. " + YONLENDIRME))
        return _is_emri_uret(k, bayi, katalog, json.loads(yol.read_text(encoding="utf-8")), model["code"], ts)

    # 2b) serbest talep — zorunlu: oda programı + (dış ölçü | pano | alan)
    if not ts.get("oda_programi"):
        return _soru(k, "oda_programi", "Kaç oda istiyorsunuz? (örn. 2+1, 3+1, tek oda)")
    nx = ny = None
    if ts.get("pano") and ts["pano"].get("nx") and ts["pano"].get("ny"):
        nx, ny = float(ts["pano"]["nx"]), float(ts["pano"]["ny"])
    elif ts.get("dis_olcu") and ts["dis_olcu"].get("en_m") and ts["dis_olcu"].get("boy_m"):
        en, boy = sorted([float(ts["dis_olcu"]["en_m"]), float(ts["dis_olcu"]["boy_m"])])
        nx, ny = pano_sayisi(en, 20), pano_sayisi(boy, 10)
    elif ts.get("alan_m2"):
        adaylar = katalog.yakin_modeller(float(ts["alan_m2"]), ts["oda_programi"], ts.get("yapi_turu"))
        if adaylar:
            liste = ", ".join(Katalog.kisa(m) for m in adaylar)
            return _soru(k, "model_veya_olcu", f"{ts['alan_m2']:g} m² {ts['oda_programi']} için katalog önerilerim: {liste}. Birini seçin ya da dış ölçü verin (örn. 8x7,5 m).")
        return _soru(k, "dis_olcu", "Dış ölçüyü verir misiniz? (kısa kenar x uzun kenar, metre; örn. 7,5x9)")
    else:
        return _soru(k, "dis_olcu", "Dış ölçü (kısa x uzun, metre) ya da yaklaşık m² verir misiniz?")

    W, H = dis_olcu_cm(nx, ny)
    anahtar = (nx, ny, ts["oda_programi"])
    if anahtar in GRID_SABLON:
        ie = json.loads((ROOT / "is_emri" / GRID_SABLON[anahtar]).read_text(encoding="utf-8"))
        ts.setdefault("belirsizlikler", []).append(f"Grid {nx:g}x{ny:g} pano → onaylı örnek şablonu kullanıldı ({GRID_SABLON[anahtar]}).")
        return _is_emri_uret(k, bayi, katalog, ie, f"GRID-{nx:g}x{ny:g}", ts, on_bilgi=f"Dış ölçü {fmt_m(W)} x {fmt_m(H)} ({nx:g}x{ny:g} pano). ")
    # yerleşim üretici henüz yok → dürüst yönlendirme, ölçü teyidiyle
    return _bitir(k, Karar(eylem="yonlendir", gerekce="serbest yerleşim üretici v0.1'de yok",
                            mesaj=f"Anladım: {ts['oda_programi']}, dış ölçü {fmt_m(W)} x {fmt_m(H)} ({nx:g}x{ny:g} pano). Bu ölçüde hazır yerleşim şablonu yok; " + YONLENDIRME))


def _is_emri_uret(k: Konusma, bayi: dict, katalog: Katalog, sablon: dict, kaynak: str, ts: dict, on_bilgi: str = "") -> Karar:
    ie = json.loads(json.dumps(sablon))
    notlar = []
    for v in ts.get("varyantlar") or []:
        tur = v.get("tur")
        try:
            if tur == "ayna_x":
                ie = varyant.ayna(ie, "x"); notlar.append("sol-sağ aynalandı")
            elif tur == "ayna_y":
                ie = varyant.ayna(ie, "y"); notlar.append("ön-arka aynalandı")
            elif tur == "pencere_degistir":
                p = v.get("parametreler") or {}
                acik = v.get("aciklama", "")
                yeni = p.get("yeni") or p.get("olcu") or p.get("yeni_olcu") or _olcu_bul(acik)
                if not yeni:
                    return _soru(k, "pencere_olcu", "Pencereyi hangi ölçüye değiştirelim? (120x120, 120x180, 60x40 …)")
                mahal = p.get("mahal")
                eslesen = _mahal_eslestir(ie, mahal) if mahal else _mahal_eslestir_metinde(ie, acik)
                if len(eslesen) != 1:
                    secenek = ", ".join(m["ad"] for m in ie["mahaller"] if any(a.get("mahal") == m["ad"] for a in ie["acikliklar"] if a["tur"] == "pencere"))
                    return _soru(k, "pencere_mahal", f"Hangi odanın penceresini {yeni} yapalım? Seçenekler: {secenek}.")
                ie = varyant.pencere_degistir(ie, eslesen[0], p.get("eski"), yeni); notlar.append(f"{eslesen[0]} penceresi {yeni}")
            else:
                return _bitir(k, Karar(eylem="yonlendir", gerekce=f"varyant desteklenmiyor: {tur}",
                                        mesaj=f"\"{v.get('aciklama','')}\" değişikliği otomatik yapılamıyor. " + YONLENDIRME))
        except varyant.VaryantHatasi as e:
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"varyant hatası: {e}", mesaj=f"Değişiklik uygulanamadı ({e}). " + YONLENDIRME))
    # pencere listesi: 'degistir' → şablondaki mahalle eşleştirip ölçü değiştir; 'ekle'/'kaldir' → v0.1'de yönlendirme
    for p in ts.get("pencereler") or []:
        if p.get("islem") == "ekle" and p.get("olcu") and p.get("mahal"):
            # "yatak odası 1 penceresi 120x180" → LLM bazen 'ekle' der; mahalde zaten TEK pencere varsa bu ölçü değişikliğidir
            eslesen = _mahal_eslestir(ie, p.get("mahal"))
            if len(eslesen) == 1 and sum(1 for a in ie.get("acikliklar", []) if a["tur"] == "pencere" and a.get("mahal") == eslesen[0]) == 1 \
                    and not _ekleme_acik(p.get("aciklama") or ts.get("ozet")):
                p = {**p, "islem": "degistir"}
                notlar.append(f"{eslesen[0]} mevcut penceresi ölçü değişikliği sayıldı (ekleme değil)")
        if p.get("islem") in ("ekle", "kaldir"):
            return _bitir(k, Karar(eylem="yonlendir", gerekce="pencere ekle/kaldır v0.1'de yok",
                                    mesaj="Pencere ekleme/kaldırma otomatik yapılamıyor. " + YONLENDIRME))
        if p.get("islem") == "degistir" or (p.get("olcu") and ie.get("acikliklar")):
            if not p.get("olcu"):
                return _soru(k, "pencere_olcu", "Pencereyi hangi ölçüye değiştirelim? (120x120, 120x180, 60x40 …)")
            eslesen = _mahal_eslestir(ie, p.get("mahal"))
            if len(eslesen) != 1:
                secenek = ", ".join(m["ad"] for m in ie["mahaller"] if any(a.get("mahal") == m["ad"] for a in ie["acikliklar"] if a["tur"] == "pencere"))
                return _soru(k, "pencere_mahal", f"Hangi odanın penceresi? Seçenekler: {secenek}.")
            try:
                ie = varyant.pencere_degistir(ie, eslesen[0], None, p["olcu"]); notlar.append(f"{eslesen[0]} penceresi {p['olcu']}")
            except varyant.VaryantHatasi as e:
                return _bitir(k, Karar(eylem="yonlendir", gerekce=f"pencere hatası: {e}", mesaj=f"Pencere değişikliği uygulanamadı ({e}). " + YONLENDIRME))
    seq = int(time.time()) % 100000
    ie["is_emri_no"] = f"PM-{bayi.get('kod','BAYI')}-{time.strftime('%Y%m%d')}-{seq}"
    ie["revizyon"] = k.d["revizyon"] + 1
    ie["talep"] = {"bayi": {"kod": bayi.get("kod"), "ad": bayi.get("ad")}, "kaynak": kaynak,
                   "musteri_adi": (ts.get("musteri") or {}).get("ad") or "", "metin": ts.get("ozet", "")}
    ie["kunye"] = {"proje_kodu": ie["is_emri_no"], "ilgili_kisi_telefon": f"{bayi.get('ad','')} / {k.gonderen}",
                   "sevk_adresi": (ts.get("musteri") or {}).get("sevk_adresi") or "", "tarih": time.strftime("%d/%m/%Y"),
                   "cizen": "Portman", "kontrol": "", "onay": ""}
    ie["bina_ozellikleri"] = {**ie.get("bina_ozellikleri", {}), **(ts.get("bina_ozellikleri") or {})}
    ie["ozel_istekler"] = list(ts.get("ozel_istekler") or [])
    ie.setdefault("eksikler", [])
    k.d["son_is_emri"] = ie
    k.d["asama"] = "is_emri_hazir"
    ozet = ts.get("ozet", "")
    ek = f" ({', '.join(notlar)})" if notlar else ""
    on_not = ts.pop("_on_not", "")
    return _bitir(k, Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=f"şablon {kaynak}" + ek,
                            mesaj=f"{on_not}{on_bilgi}{ozet}{ek} Ön onay planını hazırlıyorum; birkaç dakika içinde PDF olarak göndereceğim."))


def _ekleme_acik(metin: str | None) -> bool:
    """Metinde açıkça ekleme/ilave/bir tane daha geçiyor mu? (o zaman gerçekten 'ekle')"""
    q = varyant._norm(metin or "")
    return any(x in q for x in ("ekle", "ilave", "bir tane daha", "ek pencere", "yeni pencere", "fazladan"))


def _olcu_bul(metin: str) -> str | None:
    import re
    m = re.search(r"(\d{2,3})\s*[xX×]\s*(\d{2,3})", metin or "")
    return f"{m.group(1)}x{m.group(2)}" if m else None


def _mahal_eslestir_metinde(ie: dict, metin: str) -> list[str]:
    """Serbest metinde geçen mahal adını şablon mahalleriyle eşleştir; en uzun (en özgül) eşleşmeyi tercih et."""
    q = varyant._norm(metin or "")
    adaylar = [m["ad"] for m in ie["mahaller"] if varyant._norm(m["ad"]) in q]
    if not adaylar:
        return []
    en_uzun = max(len(varyant._norm(a)) for a in adaylar)
    return [a for a in adaylar if len(varyant._norm(a)) == en_uzun]


def _mahal_eslestir(ie: dict, mahal: str | None) -> list[str]:
    """LLM'in yazdığı mahal adını şablondaki mahallerle eşleştir (normalize alt dize). Birden çok eşleşme → belirsiz."""
    if not mahal:
        return []
    q = varyant._norm(mahal)
    adlar = [m["ad"] for m in ie["mahaller"]]
    tam = [a for a in adlar if varyant._norm(a) == q]
    if tam:
        return tam
    return [a for a in adlar if q in varyant._norm(a) or varyant._norm(a) in q]


def _soru(k: Konusma, alan: str, metin: str) -> Karar:
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = alan
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani=alan, mesaj=metin, gerekce=f"eksik: {alan}"))


def _bitir(k: Konusma, karar: Karar) -> Karar:
    if karar.eylem == "is_emri":
        k.d["bekleyen_onay"] = karar.is_emri.get("is_emri_no") if karar.is_emri else None
        k.d["asama"] = "onay_bekliyor"
    elif karar.eylem == "yonlendir":
        k.d["asama"] = "yonlendirildi"; k.d["taslak"] = {}; k.d["soru_sayisi"] = 0   # insana devredildi; taslak kapanır
    k.not_dus("giden", karar.mesaj, {"eylem": karar.eylem, "gerekce": karar.gerekce})
    k.kaydet()
    return karar
