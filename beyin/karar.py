"""Kural katmanı: Talep (LLM çıktısı) + konuşma durumu + bayi kaydı → Karar.

Burada LLM yok. Her karar deterministik ve gerekçeli. Geometri motoru ayrı (İş Emri'ni o çizer).
"""
from __future__ import annotations
import json, math, re, time
from pathlib import Path

from .sema import Talep, Karar
from .katalog import Katalog
from .konusma import Konusma, MAX_REVIZYON, MAX_SORU, ESKI_TASLAK_SN
from . import varyant

MOD = 125.5
ROOT = Path(__file__).resolve().parent.parent
BAYI_JSON = Path(__file__).resolve().parent / "veri" / "bayiler.json"
# Onaylı örnek şablonlar: (grid nx, ny, oda programı) → İş Emri dosyası
GRID_SABLON = {(6.0, 8.0, "2+1"): "ALTIN_2plus1_6x8.json", (6.0, 8.5, "2+1"): "YAN_VERANDALI_2plus1_6x8p5.json",
               (6.0, 6.0, "2+1"): "P6001_2plus1_6x6.json"}
YONLENDIRME = "Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak."
ESKI_TASLAK_SORUSU = "yeni_mi_degisiklik"      # D-01
ESKI_TASLAK_EN_COK = 3                         # cevapsız kalırsa en çok bu kadar sorulur, sonra insana devredilir
ESKI_SORU_SN = 24 * 3600                       # D-01 sorusu bu süreden sonra cevaplanırsa yok sayılır, mesaj normal işlenir


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


def karar_ver(talep: Talep, k: Konusma, bayi: dict | None, katalog: Katalog, metin: str | None = None) -> Karar:
    """metin: bayinin kendi mesajı (ham). Kurallar "bayi ne dedi" sorusunu LLM'in özetinden değil bu metinden okur.
    Kural katmanı bu mesajın yerine bekletilen bir mesajı işlediyse (D-01), o talep Karar.kullanilan_talep'te döner."""
    k.kullanilan_talep, k.bekleyen_not = None, ""
    karar = _karar_ver(talep, k, bayi, katalog, metin)
    if k.kullanilan_talep is not None:
        karar.kullanilan_talep = k.kullanilan_talep.model_dump(mode="json")
    if k.bekleyen_not:              # D-01: bekletilen mesaj işlenmeden düştüyse bayi bunu bu cevapta öğrenir
        karar.mesaj = k.bekleyen_not + karar.mesaj
    return karar


def _karar_ver(talep: Talep, k: Konusma, bayi: dict | None, katalog: Katalog, metin: str | None) -> Karar:
    t = talep
    k.not_dus("gelen", t.ozet, {"niyet": t.niyet, "guven": t.guven})
    # Askıdaki "ölçü mü değiştirelim, pencere mi ekleyelim?" sorusunun cevabı: kısa ve açık bir "değiştir"/"ekle" ise
    # LLM'in niyet sınıflandırmasından bağımsız olarak taslaktaki pencere satırına işlenir ve akış devam eder.
    if metin and k.d.get("son_soru_alani") == "pencere_islem" and len(metin.split()) <= 6:
        cevap = _pencere_niyeti(metin)
        if cevap in ("ekle", "degistir"):
            for p in k.d["taslak"].get("pencereler") or []:
                if p.get("islem") == "ekle":
                    p["islem"] = cevap; p["islem_kaynak"] = "bayi cevabı"
            k.d["son_soru_alani"] = None
            k.not_dus("kural", f"pencere_islem cevabı: {cevap}")
            t = t.model_copy(update={"niyet": "yeni_talep", "pencereler": []})

    # D-01: askıda "yeni talep mi, önceki taslağın değişikliği mi?" sorusu varken gelen mesaj. Yalnız kısa ve saf bir cevap
    # ("yeni", "değişiklik", "önceki taslağın değişikliği") cevap sayılır; o zaman soruyu doğuran mesaj (bekletilen talep ve
    # bayinin o mesajdaki sözü) seçilen yola göre işlenir, LLM'in bu kısa cevaba verdiği niyete bakılmaz.
    eski_taslak_cevabi = None
    if k.d.get("son_soru_alani") == ESKI_TASLAK_SORUSU and k.d.get("bekleyen_talep") and bayi is not None:
        kodlar, kalan_metin = _model_kodlari_ve_kalan(metin, katalog)
        bekleyen_kod = Katalog.kod_normalize(k.d["bekleyen_talep"].get("katalog_kodu") or k.d["taslak"].get("katalog_kodu"))
        if time.time() - (k.d.get("bekleyen_zamani") or 0) > ESKI_SORU_SN or t.niyet in ("red", "onay"):
            _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)          # iptal, onay ya da çok eski soru: normal akış
        elif any(Katalog.kod_normalize(c) != bekleyen_kod for c in kodlar):
            k.bekleyen_not = _dusen_not(_bekleyeni_birak(k))                # başka model kodlu yeni mesaj: normal akış
        else:
            # aynı model kodu cevabın parçası olabilir ("P6001 yeni", "P6001 değişiklik"): kod çıkarılıp kalan değerlendirilir
            cevap, saf, deneme = _eski_taslak_cevabi(kalan_metin)
            if cevap and saf:
                eski_taslak_cevabi = cevap
                bekleyen_metin = k.d.get("bekleyen_metin")
                t = Talep.model_validate(k.d["bekleyen_talep"])
                metin = bekleyen_metin or metin
                _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)
                if cevap == "yeni":
                    k.sifirla()
                    t = t.model_copy(update={"niyet": "yeni_talep"})
                else:
                    t = t.model_copy(update={"niyet": "revizyon" if k.d.get("son_is_emri") else "yeni_talep"})
                k.kullanilan_talep = t
                k.not_dus("kural", f"eski taslak sorusunun cevabı: {cevap}")
            elif not deneme and (_icerikli(t) or len((metin or "").split()) > 6):
                k.bekleyen_not = _dusen_not(_bekleyeni_birak(k))            # cevap denemesi yok, yeni bir istek: normal akış
            else:
                return _eski_taslak_sor(k)          # anlaşılmadı, olumsuz, iki cevap birden ya da cevap + ek istek: yinele

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
    kapanmis = t.niyet == "yeni_talep" and k.d["asama"] in ("uretildi", "onay_bekliyor", "onaylandi", "yonlendirildi")
    baska_model = bool(t.niyet == "yeni_talep" and t.katalog_kodu and k.d["taslak"].get("katalog_kodu")
                       and Katalog.kod_normalize(t.katalog_kodu) != Katalog.kod_normalize(k.d["taslak"]["katalog_kodu"]))
    # D-01: mesaj eski bir taslağa eklenecekse ve taslak ESKI_TASLAK_SN'den eskiyse, model koduyla başlayan mesajda tahmin
    # edilmez, sorulur (22.09: 3,5 saat sonra gelen "P6001 …" eski aynalı taslağın revizyonu sayılmıştı).
    if eski_taslak_cevabi is None and t.niyet in ("yeni_talep", "revizyon") and k.d["taslak"] and not kapanmis \
            and not baska_model and _eski_taslak(k) and _model_koduyla_basliyor(metin, katalog):
        return _eski_taslak_sor(k, t, metin)
    k.d.pop("eski_taslak_soru", None)
    if t.niyet == "revizyon" and k.d.get("son_is_emri"):
        k.d["revizyon"] += 1
        if k.d["revizyon"] > MAX_REVIZYON:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="revizyon sınırı",
                                    mesaj=f"Bu plan için {MAX_REVIZYON} revizyon hakkı doldu. " + YONLENDIRME))
    elif kapanmis:
        k.sifirla()  # önceki proje kapandı ya da insana devredildi; yeni talep
    elif baska_model:
        k.sifirla()  # başka bir modele geçti
    # askıda kalan pencere sorusu cevaplanmadan başka bir istek geldiyse: pencere değişikliğini düşür, bayiye söyle
    dusen_not = ""
    if k.d.get("son_soru_alani") in ("pencere_mahal", "pencere_olcu") and not t.pencereler \
            and not any(v.tur.startswith("pencere") for v in t.varyantlar):
        k.d["taslak"].pop("pencereler", None); k.d["son_soru_alani"] = None
        dusen_not = "Önceki pencere değişikliğini netleştirmediğiniz için uygulamadım; isterseniz sonra ekleriz. "
    k.birlestir(t.model_dump())
    k.d["asama"] = "topluyor"
    k.d["son_metin"] = (metin or "").strip()      # sıfırlama(lar)dan SONRA: kurallar bayinin bu mesajdaki sözünü okur
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
        if p.get("islem") == "ekle" and p.get("olcu") and p.get("mahal") and p.get("islem_kaynak") != "bayi cevabı":
            # "yatak odası 1 penceresi 120x180" → LLM bazen 'ekle' der. Mahalde zaten TEK pencere varsa bayinin KENDİ sözlerine bakılır
            # (k.d["son_metin"]; LLM özeti ölçüt değildir — özet "eklenmesini" diye kendi kararını tekrar eder, 22.09 canlı hata):
            #   açık değiştirme sözü → ölçü değişikliği; açık ekleme sözü → ekleme (v0.1'de yönlendirme); ikisi de yoksa → SORULUR.
            eslesen = _mahal_eslestir(ie, p.get("mahal"))
            mevcut = [a for a in ie.get("acikliklar", []) if a["tur"] == "pencere" and a.get("mahal") == (eslesen[0] if len(eslesen) == 1 else None)]
            if len(eslesen) == 1 and len(mevcut) == 1:
                niyet = _pencere_niyeti(k.d.get("son_metin") or p.get("aciklama") or "")
                if niyet == "degistir":
                    p = {**p, "islem": "degistir"}
                    notlar.append(f"{eslesen[0]} mevcut penceresi ölçü değişikliği sayıldı (ekleme değil)")
                elif niyet == "belirsiz":
                    return _soru(k, "pencere_islem", f"{eslesen[0]} odasında zaten bir pencere var ({mevcut[0].get('olcu', '?')}). "
                                 f"Ölçüsünü {p['olcu']} yapalım mı, yoksa ikinci bir pencere mi ekleyelim? \"değiştir\" ya da \"ekle\" yazmanız yeterli.")
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


_TR = str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")
_EKLE_RX = re.compile(r"\b(ekle\w*|ilave\w*|fazladan|ek (bir )?pencere|yeni (bir )?pencere|ikinci (bir )?pencere|bir tane daha|bir de\b"
                      r"|(bir|1) (tane )?pencere (koy\w*|ac\w*|olsun|istiyor\w*|lazim|gerek\w*)|pencere koy\w*)")
_DEGISTIR_RX = re.compile(r"\b(degis\w*|yap\w*|olsun|olacak|olmali|penceresi\w*|olcusu\w*|buyut\w*|kucult\w*|yerine|cevir\w*|genislet\w*)\b")


def _sozcuk_norm(metin: str) -> str:
    """Küçük harf, Türkçe harfler sadeleştirilmiş, noktalama boşluk; SÖZCÜK SINIRLARI KORUNUR ('bekle' ≠ 'ekle')."""
    q = (metin or "").translate(_TR).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", q)).strip()


def _pencere_niyeti(metin: str | None) -> str:
    """Bayinin sözünde pencere için ne var: 'ekle' (açık ekleme sözü), 'degistir' (açık ölçü değiştirme sözü), 'belirsiz' (ikisi de yok
    ya da ikisi de var). Sözcük sınırıyla arar: 'bekle' ekleme değildir; 'bir pencere koy' eklemedir; 'penceresi 120x180 olsun' değişikliktir."""
    q = " " + _sozcuk_norm(metin) + " "
    ekle = bool(_EKLE_RX.search(q)); degistir = bool(_DEGISTIR_RX.search(q))
    if ekle and not degistir:
        return "ekle"
    if degistir and not ekle:
        return "degistir"
    return "belirsiz"


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


def _eski_taslak(k: Konusma) -> bool:
    """Taslağın son değiştiği an (selam ya da genel soru cevabı saymaz); eski durum dosyasında yoksa son kayıt anı."""
    son = k.d.get("taslak_zamani") or k.d.get("guncellendi") or 0
    return son > 0 and time.time() - son > ESKI_TASLAK_SN


_SELAM = {"merhaba", "merhabalar", "selam", "selamlar", "slm", "sa", "gunaydin", "iyi", "gunler", "aksamlar", "hayirli",
          "isler", "kolay", "gelsin", "lokman", "bey", "beyefendi", "hocam", "abi", "abim", "hanim", "tesekkurler"}


def _model_kodlari_ve_kalan(metin: str | None, katalog: Katalog) -> tuple[list[str], str]:
    """Mesajdaki katalog kodları ve kodlar çıkarılınca kalan metin (başa gelen selamlaşma sözcükleri dahil edilmez)."""
    kodlar, kalan = [], []
    for sira, soz, kod in _sozcukler(metin, katalog):
        (kodlar.append(kod) if kod else kalan.append(soz))
    return kodlar, " ".join(kalan)


def _sozcukler(metin: str | None, katalog: Katalog) -> list[tuple[int, str, str | None]]:
    """(sözcük sırası, sözcük, katalog kodu ya da None). WhatsApp biçim işaretleri (*_~) atlanır; "P 6001", "p-6001",
    "6001", "P6001'i", "P6001/aynalı" kod olarak tanınır. Baştaki selamlaşma sözcükleri atlanır, sıra onlardan sonra başlar."""
    toks = [x for x in re.split(r"[\s,.;:!?'’/()*_~\-]+", metin or "") if x]
    out, i, sira = [], 0, 0
    while i < len(toks):
        a = toks[i]
        if sira == 0 and _sozcuk_norm(a) in _SELAM:
            i += 1; continue
        if a.upper() in ("P", "Ç", "C") and i + 1 < len(toks) and re.fullmatch(r"\d{4}", toks[i + 1]):
            a = a + toks[i + 1]; i += 1
        m = katalog.bul(a)
        out.append((sira, a, m["code"] if m else None))
        sira += 1; i += 1
    return out


def _model_koduyla_basliyor(metin: str | None, katalog: Katalog) -> str | None:
    """Bayinin mesajı (selamlaşma sözcüklerinden sonra) katalogdaki bir model koduyla mı başlıyor? Öyleyse kodu döner."""
    ilk = [kod for sira, _soz, kod in _sozcukler(metin, katalog) if sira == 0 and kod]
    return ilk[0] if ilk else None


_YENI_SOZ = re.compile(r"yeni(si|sini)?|sifirdan|baska")
_DEGISIKLIK_SOZ = re.compile(r"degisikli[kg]\w*|degistir\w*|revizyon\w*|revize|onceki\w*|devam\w*|ayni(si|sina)?|eski(si|sinin|sine|sini)?")
_OLUMSUZ = {"degil", "yok", "hayir", "olmasin", "istemiyorum", "istemem"}
_DOLGU = {"ve", "ama", "evet", "tamam", "lutfen", "bu", "o", "su", "bir", "talep", "talebi", "talebim", "olsun", "proje", "projesi",
          "taslak", "taslagin", "taslagi", "taslaga", "mesaj", "mesajim", "benim", "is", "isi", "plan", "plani", "planin"}


def _eski_taslak_cevabi(metin: str | None) -> tuple[str | None, bool, bool]:
    """(cevap, saf, deneme). cevap: 'yeni' | 'degisiklik' | None (yok, ikisi birden ya da olumsuzlanmış). saf: cevap ve
    dolgu sözcükleri dışında sözcük yok. deneme: mesajda cevap sözcüğü ya da olumsuzluk var (bayi cevap vermeye çalışmış).
    "yeni değil", "değişiklik yok" anlaşılmadı sayılır; "yeniden" yeni sayılmaz."""
    soz = _sozcuk_norm(metin).split()
    yeni = [w for w in soz if _YENI_SOZ.fullmatch(w)]
    degis = [w for w in soz if _DEGISIKLIK_SOZ.fullmatch(w)]
    olumsuz = [w for w in soz if w in _OLUMSUZ]
    kalan = [w for w in soz if w not in yeni and w not in degis and w not in olumsuz and w not in _DOLGU and w not in _SELAM]
    deneme = bool(yeni or degis or olumsuz)
    if olumsuz or bool(yeni) == bool(degis):
        return None, False, deneme
    return ("yeni" if yeni else "degisiklik"), not kalan, deneme


def _icerikli(t: Talep) -> bool:
    """LLM çıkarımında plan içeriği var mı (model, ölçü, oda, pencere, varyant, özel istek…)?"""
    d = t.model_dump(exclude={"niyet", "guven", "ozet", "belirsizlikler", "musteri"})
    return any(v not in (None, [], {}, "") for v in d.values())


def _kisalt(metin: str | None, n: int = 60) -> str:
    m = " ".join((metin or "").split())
    return m if len(m) <= n else m[:n - 1] + "…"


def _dusen_not(bekleyen_metin: str) -> str:
    return f"Sorumu cevaplamadan yeni mesaj yazdığınız için önceki mesajınızı («{_kisalt(bekleyen_metin)}») işlemedim; gerekirse yeniden yazın. "


def _sure_metni(saniye: float) -> str:
    saat = int(saniye // 3600)
    return f"{saat // 24} gün" if saat >= 48 else f"{max(saat, 1)} saat"


def _bekleyeni_birak(k: Konusma) -> str:
    """Askıdaki D-01 sorusunu kapatır; bekletilen mesajın metnini döner. Soru sayacı (eski_taslak_soru) kalır."""
    k.d.pop("bekleyen_talep", None); k.d.pop("bekleyen_zamani", None)
    if k.d.get("son_soru_alani") == ESKI_TASLAK_SORUSU:
        k.d["son_soru_alani"] = None
    return k.d.pop("bekleyen_metin", "") or ""


def _eski_taslak_sor(k: Konusma, t: Talep | None = None, metin: str | None = None) -> Karar:
    """D-01: mesaj bekletilir, bayiye yeni mi değişiklik mi diye sorulur. t verilmezse bekleyen mesaj korunur ve soru
    yinelenir. Soru, eksik bilgi sorularının sınırına (MAX_SORU) sayılmaz; ESKI_TASLAK_EN_COK kez sorulduktan sonra
    talep insana devredilir."""
    n = k.d.get("eski_taslak_soru", 0) + 1
    if t is not None:
        k.d["bekleyen_talep"] = t.model_dump(mode="json")
        k.d["bekleyen_metin"] = (metin or "").strip()
    if n > ESKI_TASLAK_EN_COK:
        bekleyen = _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"eski taslak sorusu cevapsız (D-01); bekleyen mesaj: «{_kisalt(bekleyen, 200)}»",
                               mesaj="Önceki taslakla ilgili sorumu netleştiremedim. " + YONLENDIRME))
    k.d["bekleyen_zamani"] = int(time.time())
    k.d["son_soru_alani"] = ESKI_TASLAK_SORUSU
    k.d["eski_taslak_soru"] = n
    if n == 1:
        ts = k.d["taslak"]
        ie_no = (k.d.get("son_is_emri") or {}).get("is_emri_no")
        ne = ts.get("ozet") or ts.get("katalog_kodu") or "açık taslak"
        son = k.d.get("taslak_zamani") or k.d.get("guncellendi") or time.time()
        mesaj = (f"Önceki taslağınız ({_kisalt(ne)}{', ' + ie_no if ie_no else ''}) {_sure_metni(time.time() - son)} önce kaldı. "
                 "Bu mesaj yeni bir talep mi, yoksa o taslağın değişikliği mi? \"yeni\" ya da \"değişiklik\" yazmanız yeterli.")
    else:
        mesaj = ("Anlayamadım: bu yeni bir talep mi, yoksa önceki taslağınızın değişikliği mi? Lütfen yalnız \"yeni\" ya da "
                 "\"değişiklik\" yazın; ek isteğinizi sonra yazabilirsiniz.")
    return _bitir(k, Karar(eylem="sor", soru_alani=ESKI_TASLAK_SORUSU, mesaj=mesaj,
                           gerekce="eski taslak: yeni mi değişiklik mi (D-01)" + (" · yinelendi" if n > 1 else "")))


def _soru(k: Konusma, alan: str, metin: str) -> Karar:
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = alan
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani=alan, mesaj=metin, gerekce=f"eksik: {alan}"))


def _bitir(k: Konusma, karar: Karar) -> Karar:
    if k.d.get("son_soru_alani") != ESKI_TASLAK_SORUSU:
        k.d.pop("eski_taslak_soru", None)             # D-01 sorusu askıda değilse sayaç da kalmaz
    if karar.eylem == "is_emri":
        k.d["bekleyen_onay"] = karar.is_emri.get("is_emri_no") if karar.is_emri else None
        k.d["asama"] = "onay_bekliyor"
    elif karar.eylem == "yonlendir":
        k.d["asama"] = "yonlendirildi"; k.d["taslak"] = {}; k.d["soru_sayisi"] = 0   # insana devredildi; taslak kapanır
    k.not_dus("giden", karar.mesaj, {"eylem": karar.eylem, "gerekce": karar.gerekce})
    k.kaydet()
    return karar
