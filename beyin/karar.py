"""Kural katmanı: Talep (LLM çıktısı) + konuşma durumu + bayi kaydı → Karar.

Burada LLM yok. Her karar deterministik ve gerekçeli. Geometri motoru ayrı (İş Emri'ni o çizer).
"""
from __future__ import annotations
import json, math, re, time
from pathlib import Path

from .sema import Talep, Karar, Musteri
from .katalog import Katalog
from .konusma import Konusma, MAX_REVIZYON, MAX_SORU, ESKI_TASLAK_SN, _tekillestir
from . import varyant
from . import secenek as SC
from . import numara                     # BK-08 madde 9: gerekçedeki serbest metin maskelenir
from . import celik                      # İE-08: çelik aday zarfı, D-09 antet bilgisi
from . import celik_okuma as CO          # İE-08 PR-2b: çelik revizyonunda bayinin sözünden pencere / çatı / dış 140 okuması (K18)
from . import form_ozellik               # İE-20 PR-6: prefabrik talep formundaki standart dışı seçimler İş Emri'ne
from . import yarim_pano as YP            # İE-39 (D-90): havuz evinde dış duvar yarım pano kayar
from . import yarim_pano_okuma as YPO     # İE-39 PR-2: bayinin "sağa yarım pano uzat" sözü (K18; ayar `yarim_pano.acik`)

MOD = 125.5
ROOT = Path(__file__).resolve().parent.parent
BAYI_JSON = Path(__file__).resolve().parent / "veri" / "bayiler.json"
# Onaylı örnek şablonlar: (grid nx, ny, oda programı) → İş Emri dosyası
GRID_SABLON = {(6.0, 8.0, "2+1"): "ALTIN_2plus1_6x8.json", (6.0, 8.5, "2+1"): "YAN_VERANDALI_2plus1_6x8p5.json",
               (6.0, 6.0, "2+1"): "P6001_2plus1_6x6.json"}
YONLENDIRME = "Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak."
# BK-28 (pano 196): bayiye giden örnek talepler. İkisi de canlıdaki modellerle seçenek setine gider (hedef: testler/bayi_metinleri/);
# eski "7x4 m, 2+1, ön verandalı" örneği hazır plana gitmiyordu (yönlendirme).
ORNEK_PREFABRIK = "Tek kat prefabrik, 2+1, 85 m²"
ORNEK_CELIK = "Tek kat çelik, 2+1, 88 m²"
ORNEK_METNI = f"\"{ORNEK_PREFABRIK}\" veya \"{ORNEK_CELIK}\""
ESKI_TASLAK_SORUSU = "yeni_mi_degisiklik"      # D-01
ESKI_TASLAK_EN_COK = 3                         # cevapsız kalırsa en çok bu kadar sorulur, sonra insana devredilir
ESKI_SORU_SN = 24 * 3600                       # D-01 sorusu bu süreden sonra cevaplanırsa yok sayılır, mesaj normal işlenir
_ODA_PROGRAMI = re.compile(r"\d\s*\+\s*\d")    # "2+1", "3 + 1": set numarası değil (İE-25)


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


def _form_izi(k: Konusma, t: Talep, metin: str = "") -> None:
    """İE-20 PR-6: prefabrik talep formundan gelen talebin izi taslakta. Form mesajında (`k.prefabrik_formu`; `kanal/worker` yazar):
    `form = "prefabrik"` (formdaki seçimler İş Emri'ne işlenir, `form_ozellik`), öncelik taslağa yazılır (sohbette sorulmaz; plan başka
    bir mesajda çıksa da), ölçü "formdan" diye işaretlenir (pano + m² birlikte: hazır planlar m²'ye göre). Sonraki bir mesajda bayi
    ölçüyü sohbette yazarsa ölçü izi kalkar; plan henüz çıkmadıysa formun hesapladığı öteki değer de düşer: bayinin son sözü bugünkü
    yoldan okunur (pano ya da dış ölçü yazdıysa m², m² yazdıysa pano).
    İE-20 PR-9 (D-93): çelik talep formunun mesajında (`k.celik_formu`) `form = "celik"`; öncelik taslağa yazılır (çelikte öncelik
    sohbette sorulmaz; formda seçilen bütçe ya da yaşam alanı seti sıralar), dış duvar 140 mm karkas seçimi `form_dis140` olarak durur
    (`_celik_is_emri_uret` ilk planda çizime işler). Çelikte ölçü yuvarlanmaz: ölçü izi yok.
    İE-20 PR-11 (D-97): formda seçilen ve genel motorun hesapladığı çatı kaplaması `form_kaplama` olarak durur; ilk planda tanıma yazılır
    (pafta tablosu ve yükleme listesi o kaplamayla çıkar)."""
    ts = k.d["taslak"]
    cf = getattr(k, "celik_formu", None)
    k.celik_formu = None                          # yalnız bu mesaj için
    if cf is None and ts.get("form_kaplama_once") and ts.get("form_kaplama"):
        # Formdan önce yazılmış kaplama sözü formdan sonra yeniden yazıldı: artık son sözdür. Yalnız bayinin bu mesajındaki cümle bir
        # çatı malzemesi anıyorsa (K18: LLM'in bağlamdan yinelediği satır bayinin sözü değildir).
        # LLM cümleyi yeniden yazmasa da (söz taslakta zaten durur) bayinin metni aynı malzemeyi anıyorsa işaret kalkar (hakem, 4. tur).
        bu = {f"{a}: {v}" for a, v in (t.bina_ozellikleri or {}).items()} | set(t.ozel_istekler or [])
        anilan = _kap_oteki_malzemeler(metin, ts["form_kaplama"], baglam=_kaplama_istegi_mi(metin))
        if anilan:
            ts["form_kaplama_once"] = [x for x in ts["form_kaplama_once"]
                                       if not (x in bu or anilan & _kap_oteki_malzemeler(x, ts["form_kaplama"]))]
            if not ts["form_kaplama_once"]:
                ts.pop("form_kaplama_once")
    if cf is not None:
        ts["form"] = "celik"
        ts.pop("olcu_formdan", None)
        ts.pop("yazilan_kaplama", None)           # D-106: formdan önce yazılmış kaplama sözü son söz değildir (son söz form)
        if cf.get("oncelik"):
            ts["oncelik"] = cf["oncelik"]
        if cf.get("dis140"):
            ts["form_dis140"] = True
        else:
            ts.pop("form_dis140", None)
        if cf.get("kaplama"):                     # İE-20 PR-11 (D-97): çizime işlenen çatı kaplaması (kural kitabının anahtarı)
            ts["form_kaplama"] = cf["kaplama"]
            ts["form_kaplama_yazi"] = (t.bina_ozellikleri or {}).get(_KAPLAMA_SATIRI)   # formun özellik satırına yazdığı değer
            # Formdan önce sohbette yazılmış başka kaplama (taslaktan doldurulan formda taslak durur): son söz formdur. O sözler silinmez
            # (içinde başka bilgi olabilir: "kiremit, çift kat yalıtım"), "formdan önce" diye işaretlenir: ilk planda form seçimini
            # durdurmaz, özel istekte kalır. Formun bu cevapta yazdığı satırlar ve notu aynı mesajdır: işaretlenmez.
            bu = {f"{a}: {v}" for a, v in (t.bina_ozellikleri or {}).items()} | set(t.ozel_istekler or [])
            once = [x for x in _kaplama_sozleri(ts, cf["kaplama"], hepsi=True)[1] if x not in bu]
            ts["form_kaplama_once"] = once
            if not once:
                ts.pop("form_kaplama_once")
        else:
            ts.pop("form_kaplama", None); ts.pop("form_kaplama_yazi", None); ts.pop("form_kaplama_once", None)
        # Form yeniden geldiyse (aynı taslak) formun yazdığı satırlarda son form geçerli: bu cevapta olmayan satırın eski değeri kalkar
        # (`Konusma.birlestir` özellikleri üst üste ekler; standarda dönen seçim eski standart dışı değeri plana taşımasın).
        bo, bu = ts.get("bina_ozellikleri"), t.bina_ozellikleri or {}
        if isinstance(bo, dict):
            for a in cf.get("anahtarlar") or ():
                if a in bo and not bu.get(a):
                    del bo[a]
            if not bo:
                ts.pop("bina_ozellikleri", None)
        return
    form = getattr(k, "prefabrik_formu", None)
    k.prefabrik_formu = None                      # yalnız bu mesaj için (aynı konuşma nesnesi sonraki mesajda da kullanılırsa kalmasın)
    if form is not None:
        ts["form"] = "prefabrik"
        ts.pop("form_dis140", None)
        ts.pop("form_kaplama", None); ts.pop("form_kaplama_yazi", None); ts.pop("form_kaplama_once", None)
        ts.pop("yazilan_kaplama", None)
        ts["olcu_formdan"] = True
        if form.get("oncelik"):
            ts["oncelik"] = form["oncelik"]
        return
    if not ts.get("olcu_formdan"):
        return
    yeni_pano = t.pano is not None
    yeni_olcu = t.dis_olcu is not None and bool(t.dis_olcu.en_m or t.dis_olcu.boy_m)
    if not (yeni_pano or yeni_olcu or t.alan_m2 is not None):
        return
    ts.pop("olcu_formdan", None)
    if (k.d.get("son_is_emri") or {}).get("is_emri_no"):
        return                                    # plan çıktıktan sonra taslağa dokunulmaz (revizyon bugünkü yoldan)
    if not yeni_pano:
        ts.pop("pano", None)
    if (yeni_pano or yeni_olcu) and t.alan_m2 is None:
        ts.pop("alan_m2", None)


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
    k.son_llm = None                                # İE-08 A4: bu mesajın LLM ipuçları (yalnız bu çağrıda; `_karar_ver` doldurur)
    k.rev0 = int(k.d.get("revizyon") or 0)          # G-2: _bitir, plan üretmeyen turda sayacı buna geri alır
    k.bu_mesaj_mahalleri, k.pencere_hicbiri = set(), False   # BK-29 PR-2: bu mesajın pencere satırlarının odaları; "Hangi pencere?" → hiçbiri
    k.degismedi_notu = ""                           # D-86: aynı değişiklik yeniden istendi ("YATAK ODASI 1 penceresi zaten 100x140")
    k.cati_secimi, k.cati_metni, k.cati_adi = None, "", ""          # İE-42 (D-94): onaydan sonraki çatı setinde bu mesajın seçimi ve plan metninin başı
    k.cati_adimi_secimi, k.cati_adimi_metni = None, None      # İE-42 (hakem tur 1, bulgu 6, 8): onaydan sonraki çatı setinde bu mesajın seçimi
    k.cati_sorusu_notu = ""                         # İE-42: "Hangi çatı olsun?" sorusunda aynı mesajın uygulanmayan isteği
    k.cati_ek, k.cati_icerik, k.cati_on_not = False, [], ""   # İE-42 (hakem tur 2, 3): çatıyla aynı mesajdaki istek cümleleri; cevabın başı
    k.degismedi_tam = False                         # İE-42 (hakem tur 3, 4): bu mesajın her istek cümlesi D-86 notunda (planda zaten var)
    k.cati_fiyat_sorusu = False                     # İE-42 (hakem tur 4, D-E): çatı setinde seçimle birlikte fiyat, süre ya da teslim sorusu
    d0 = json.loads(json.dumps(k.d))                # BK-29 (pano 200): geri çevrilen istek açık planı kapatmaz; konuşma buna döner
    karar = _karar_ver(talep, k, bayi, katalog, metin)
    secim, ca0 = k.cati_adimi_secimi, d0.get("cati_adimi") or {}
    if secim and ca0 and karar.eylem != "is_emri" and karar.gerekce != PLAN_ONAYI and not _cati_soruyla_bekler(k, karar, secim):
        # İE-42 (hakem tur 1, bulgu 6): çatı seçildi ama aynı mesajdaki istek plan çizdirmedi. Evin çatısı + bu mesajın her istek cümlesi
        # planda zaten var (her cümle bayinin yazdığı bir D-86 notuyla tümüyle açıklanır; hakem tur 3, 4): r01 onaylanır. Öteki sonuç
        # (yönlendirme, okunamayan istek sorusu, Motor'un uygulamadığı istek; hakem tur 2, Y1): plan değişmez, set açık kalır, çatı seçimi
        # kaydedilmez ve bayiye yazılır (seçim ve istek sessizce düşmez, onaylanmamış çatı "seçildi" sayılmaz).
        if karar.gerekce == PLAN_DEGISMEDI and str(secim).upper() == str(ca0.get("kod") or "").upper() \
                and k.degismedi_notu and k.degismedi_tam:
            karar = _cati_degismedi_onayi(k, d0, katalog, secim)
        else:
            if karar.eylem not in ("yonlendir", "cevapla"):
                karar = Karar(eylem="cevapla", gerekce=f"çatı seçimi kaydedilmedi: {karar.gerekce}", mesaj=karar.mesaj)
            _plani_acik_tut(k, d0, karar, cati_secimi=secim)
    elif karar.eylem == "yonlendir" or karar.gerekce == PLAN_DEGISMEDI:
        _plani_acik_tut(k, d0, karar)
    if k.cati_on_not:                # İE-42 (hakem tur 2, O1): çatı seçimi talebin değişikliğiyle kaydedilmedi; bayiye yazılır
        karar.mesaj = k.cati_on_not + karar.mesaj
    elif ca0 and karar.gerekce != "iptal":
        # İE-42 (hakem tur 3): çatı seti açıkken konuşma başka bir eve ya da talebe geçti (başka model, yeni talep, başka müşteri: plan
        # kapandı ya da yeni plan r01). Set mesajı "Planınız onaylandı (r01)" demişti; onay çatı seçilmeden kaydedilmez, bayiye yazılır.
        no0, rev0 = ca0.get("is_emri_no"), int(ca0.get("rev") or 1)
        if no0 and (not (k.d.get("son_is_emri") or {}).get("is_emri_no") or (karar.eylem == "is_emri" and int(karar.revizyon or 0) <= 1)):
            karar.mesaj = f"Önceki planınızın ({no0} r{rev0:02d}) onayı kaydedilmedi; çatısı seçilmemişti. " + (karar.mesaj or "")
    if k.cati_fiyat_sorusu and secim and FIYAT_SORUSU_CEVABI not in (karar.mesaj or ""):
        karar.mesaj = f"{(karar.mesaj or '').rstrip()} {FIYAT_SORUSU_CEVABI}".strip()   # hakem tur 4, D-E: soru cevapsız kalmaz
    if k.kullanilan_talep is not None:
        karar.kullanilan_talep = k.kullanilan_talep.model_dump(mode="json")
    if k.bekleyen_not:              # D-01: bekletilen mesaj işlenmeden düştüyse bayi bunu bu cevapta öğrenir
        karar.mesaj = k.bekleyen_not + karar.mesaj
    return karar


_UNVANLAR = {"bey", "hanim", "sayin", "usta", "abi", "abla", "hoca", "hocam"}


def _ad_sozcukleri(s) -> list[str]:
    """Adın sözcükleri: küçük harf, Türkçe harfler sade, unvan ("Bey", "Hanım") sayılmaz."""
    return [w for w in (varyant._norm(x) for x in re.split(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", str(s or ""))) if w and w not in _UNVANLAR]


def _bayi_adi_musteri_degil(k: Konusma, t: Talep, bayi: dict | None, metin: str | None) -> Talep:
    """BK-29 tur 7 (canlı bulgu, 14–15 Kasım 2026): LLM bağlamında "bayinin adı/hitabı" yazar (D-06, `worker.bayi_tanimi`); LLM bunu
    bazen `musteri.ad`'a yazıyor ve bayinin adı İş Emri'nin `talep.musteri_adi`'sına, PDF başlığına ve çelik antetine çıkıyor. Müşteri
    adı bayinin kendi mesajından okunur (K18; şema: "Mesajda OLMAYAN hiçbir alan doldurulmaz"): LLM'in verdiği ad bayinin kartındaki
    adın ya da hitabın sözcüklerinden oluşuyorsa ve bu mesajda yazmıyorsa düşer (taslağa girmez; sevk adresi ve öteki alanlar aynen).
    Bayi kendi adını mesajına yazdıysa (kendi evi) ad kalır. Bayi kaydı ya da ham mesaj yoksa dokunulmaz."""
    ad = (t.musteri.ad if t.musteri else None) or ""
    sozcukler = _ad_sozcukleri(ad)
    if not sozcukler or not bayi or metin is None:
        return t
    bayinin = set(_ad_sozcukleri(bayi.get("ad"))) | set(_ad_sozcukleri(bayi.get("hitap")))
    if not set(sozcukler) <= bayinin:
        return t
    mesajdaki = _ad_sozcukleri(metin)
    if all(any(m.startswith(w) for m in mesajdaki) for w in sozcukler):      # "Lokman'ın evi", "müşteri Lokman": bayi kendi yazdı
        return t
    k.not_dus("kural", "müşteri adı bayinin adıyla aynı ve mesajda yok: alınmadı")
    return t.model_copy(update={"musteri": t.musteri.model_copy(update={"ad": None})})


def _karar_ver(talep: Talep, k: Konusma, bayi: dict | None, katalog: Katalog, metin: str | None) -> Karar:
    t = talep
    k.not_dus("gelen", t.ozet, {"niyet": t.niyet, "guven": t.guven})
    # Askıdaki "ölçü mü değiştirelim, pencere mi ekleyelim?" sorusunun cevabı: kısa ve açık bir "değiştir"/"ekle" ise
    # LLM'in niyet sınıflandırmasından bağımsız olarak taslaktaki pencere satırına işlenir ve akış devam eder.
    # Cevap yalnız kısa ve saf bir "değiştir"/"ekle" ise sayılır ("aynalı olsun" cevap değildir); yalnız sorulan pencere satırı
    # çözülür (B1 incelemesi, 28.09). Saf metin ("değiştir", "ekle" ve dolgu sözcükleri) yeni içerik taşıyamaz: LLM'in bu kısa
    # cevaba bağlamdan yinelediği oda, ölçü ya da model (29.09 G-1: Opus 5.5 böyle yaptı ve soru 'dustu' kapandı) yok sayılır.
    if metin and k.d.get("son_soru_alani") == "pencere_islem" and len(metin.split()) <= 6 and _pencere_cevabi_saf(metin):
        cevap = _pencere_niyeti(metin)
        if cevap in ("ekle", "degistir"):
            sorulan = k.d.get("pencere_islem_satiri")
            for p in k.d["taslak"].get("pencereler") or []:
                if p.get("islem_kaynak") == "bayi cevabı":
                    continue
                if (list(_pencere_anahtari(p)) == sorulan) if sorulan else (p.get("islem") == "ekle" or p.get("soz_niyeti") == "belirsiz"):
                    p["islem"] = cevap; p["islem_kaynak"] = "bayi cevabı"
            k.d.pop("pencere_islem_satiri", None)
            k.d["son_soru_alani"] = None
            k.not_dus("kural", f"pencere_islem cevabı: {cevap}")
            t = Talep(niyet="yeni_talep", guven=t.guven, ozet=t.ozet)      # LLM'in bu kısa cevaba verdiği içerik yok sayılır
        elif _olumsuz_ya_da_soru(metin):
            # 29.09 (Astra): "değiştirme", "eklemeyin" gibi olumsuz ya da soru biçimli kısa cevap hiçbir işleme çevrilmez; LLM ne
            # derse desin (boş, bağlamdan doldurulmuş ya da "red") soru yinelenir: pencere değişmez, eklenmez, talep kapanmaz.
            k.not_dus("kural", "pencere_islem cevabı olumsuz ya da soru biçimli: soru yinelendi")
            return _soru(k, "pencere_islem", "Anlayamadım. " + (k.d.get("pencere_islem_sorusu") or
                         "Mevcut pencerenin ölçüsünü mü değiştirelim, yoksa ikinci bir pencere mi ekleyelim? \"değiştir\" ya da \"ekle\" yazmanız yeterli."))

    # BK-29 PR-2 (pano 201, 210; 13 Kasım 2026 denetimi): askıdaki "Hangi odanın penceresi?" ve "Hangi pencere?" sorularının cevabı.
    # Düğme (q:pencere_mahal:<n> → "seçenek <n>", q:pencere_secim:<n> → "<n>") ya da kısa yazı ("Oda 1", "soldaki", "120x100", "ikisi de")
    # bekleyen pencere isteğine işlenir; LLM'in bu kısa cevaba verdiği içerik yok sayılır (K18). İçerikli yeni istek soruyu düşürür (bayiye
    # söylenir); kısa ama anlaşılmayan cevap soruyu yineler.
    if k.d.get("son_soru_alani") == "pencere_mahal" and k.d.get("pencere_mahal_sorusu"):
        ps = k.d["pencere_mahal_sorusu"]
        ad = _oda_cevabi(metin, ps.get("odalar") or [])
        if ad and _pencere_odasi_yaz(k.d["taslak"], ps.get("hedef") or {}, ad):
            k.d.pop("pencere_mahal_sorusu", None); k.d["son_soru_alani"] = None
            k.not_dus("kural", f"pencere_mahal cevabı: {ad}")
            t = Talep(niyet="yeni_talep", guven=t.guven, ozet="")
        elif not _icerikli(t) and len((metin or "").split()) <= 4 and not _olcu_bul(metin or ""):
            k.not_dus("kural", "pencere_mahal cevabı anlaşılmadı: soru yinelendi")
            return _soru(k, "pencere_mahal", "Anlayamadım. " + ps.get("metin", ""), ps.get("butonlar"))
    if k.d.get("son_soru_alani") == "pencere_olcu":
        # BK-29 tur 4 (B4): "Pencereyi hangi ölçüye değiştirelim?" sorusunun cevabı ("120x150", "120x150 olsun") ölçüsü bekleyen pencere
        # isteğine yazılır; LLM'in bu kısa cevaba verdiği içerik yok sayılır (şema listede olmayan ölçüyü taşımıyor). Canlıda soru yineleniyordu.
        # Yalnız ölçüden oluşan cevap: oda ya da başka söz taşıyan mesaj ("mutfak penceresi 120x150 olsun") bugünkü yoldan gider.
        o = _yalniz_olcu(metin)
        if o and _bekleyen_olcuyu_yaz(k.d["taslak"], o):
            k.d["son_soru_alani"] = None
            k.not_dus("kural", f"pencere_olcu cevabı: {o}")
            t = Talep(niyet="yeni_talep", guven=t.guven, ozet="")
    if k.d.get("son_soru_alani") == "pencere_secim" and k.d.get("pencere_secim"):
        ps = k.d["pencere_secim"]
        secim = _pencere_secim_cevabi(metin, ps.get("secenekler") or [])
        if secim is not None:
            for p in k.d["taslak"].get("pencereler") or []:
                if list(_pencere_anahtari(p)) == ps.get("satir") and p.get("pencere_sira") is None:
                    if secim == "hicbiri":
                        p["_dusur"] = True
                    else:
                        p["pencere_sira"] = sorted({i for j in secim for i in ps["secenekler"][j]["sira"]})
                        p["islem"] = "degistir"               # hakem 1: soru değiştirme sözünden doğdu; LLM'in "ekle"si kalmaz
            dusen = [p for p in k.d["taslak"].get("pencereler") or [] if p.get("_dusur")]
            k.d["taslak"]["pencereler"] = [p for p in k.d["taslak"].get("pencereler") or [] if not p.get("_dusur")]
            k.d.pop("pencere_secim", None); k.d["son_soru_alani"] = None
            if secim == "hicbiri":
                k.pencere_hicbiri = True
                k.bekleyen_not = "Tamam, o pencereyi değiştirmedim. "
                _pencere_kopyalarini_dusur(k, {p["olcu"] for p in dusen if p.get("olcu")})
            k.not_dus("kural", "pencere_secim cevabı: " + ("hiçbiri" if secim == "hicbiri" else ", ".join(str(j + 1) for j in secim)))
            t = Talep(niyet="yeni_talep", guven=t.guven, ozet="")
        elif len(ps.get("secenekler") or []) == 1 and _BIRI.search(" " + CO.norm(metin or "") + " ") \
                and len((metin or "").split()) <= 6 and not _olcu_bul(metin or ""):
            # "İkisini de … yapalım mı?" sorusuna "sadece biri": aynı ölçü ve duvardaki pencereyi bayi ayırt edemez, kod da seçemez
            # (soru döngüye girmesin; hakem ikinci tur 2). Plan açık kalır (`_plani_acik_tut`), Patron'a bildirim gider.
            k.not_dus("kural", "pencere_secim: aynı duvardaki pencerelerden yalnız biri istendi")
            return _bitir(k, Karar(eylem="yonlendir", gerekce="aynı ölçü ve duvardaki pencerelerden biri seçilemiyor",
                                   mesaj="Aynı duvardaki aynı ölçülü pencerelerden yalnız birini otomatik seçemiyorum. " + YONLENDIRME))
        elif not _icerikli(t) and len((metin or "").split()) <= 6 and not _olcu_bul(metin or ""):
            k.not_dus("kural", "pencere_secim cevabı anlaşılmadı: soru yinelendi")
            return _soru(k, "pencere_secim", "Anlayamadım. " + ps.get("metin", ""), ps.get("butonlar"))
        else:
            k.d["taslak"]["pencereler"] = [p for p in k.d["taslak"].get("pencereler") or []
                                           if not (list(_pencere_anahtari(p)) == ps.get("satir") and p.get("pencere_sira") is None)]
            k.d.pop("pencere_secim", None); k.d["son_soru_alani"] = None
            ayni_oda = varyant._norm(ps.get("mahal") or "") in {varyant._norm(x.mahal or "") for x in t.pencereler} | \
                {varyant._norm(str((v.parametreler or {}).get("mahal") or "")) for v in t.varyantlar if v.tur == "pencere_degistir"}
            if not ayni_oda:                                  # aynı odanın penceresini yeniden yazdıysa bu mesaj sorunun yerine geçer
                k.bekleyen_not = "Önceki pencere sorumu cevaplamadığınız için o değişikliği uygulamadım; bu mesajınızı işliyorum. "
            k.not_dus("kural", "pencere_secim sorusu cevaplanmadan yeni istek geldi: soru düştü")

    # İE-04: askıdaki öncelik sorusunun cevabı ("bütçe", "yaşam alanı", "kısa montaj", "fark etmez"; buton kimliği q:oncelik:<deger>
    # aynı metne çevrilir). Kısa ve açık cevap taslağa yazılır; LLM'in bu kısa cevaba verdiği içerik yok sayılır. Cevap değilse
    # soru bir daha sorulmaz (öncelik "yok"), mesaj normal işlenir: "söylenen bilgi tekrar sorulmaz".
    if k.d.get("son_soru_alani") == "oncelik":
        cevap = _oncelik_cevabi(metin)
        k.d["son_soru_alani"] = None
        k.d["taslak"]["oncelik"] = cevap or "yok"
        if cevap:
            k.not_dus("kural", f"öncelik cevabı: {cevap}")
            t = Talep(niyet="yeni_talep", guven=t.guven, ozet=t.ozet)
        else:
            k.not_dus("kural", "öncelik sorusuna cevap yok: öncelik belirtilmedi sayıldı, mesaj normal işlendi")

    # İE-08 PR-2b (A4): askıdaki çelik okuma sorusunun cevabı — "1 / 2 / Hiçbiri" (buton q:okuma:<n> aynı metne çevrilir; numaralı
    # metin sorusunda "3" gibi) ya da ölçü sorusunun cevabı ("120x120"). Cevapsa LLM'in bu kısa mesaja verdiği içerik yok sayılır ve
    # seçilen değişiklik aynı projenin yeni revizyonu olarak uygulanır. "Hiçbiri" bir kez "Neyi değiştirelim?" sorusu açar, ikincisi
    # yönlendirir. Cevap değilse: içerikli yeni istek soruyu düşürür (bayiye söylenir), kısa anlaşılmaz cevap soruyu yineler.
    # Kapanış incelemesi (13.10): soru ilk planda (r01) da sorulabilir — cevap son plan olmadan da işlenir; cevaptan sonra niyet r01'de
    # yeni talep, sonra revizyondur. Aynı mesajda okunup sorudan önce hazırlanan değişiklikler (`hazir`: dış 140, başka bir pencere) ve
    # henüz sorulmamış pencere cümleleri (`kalan`) soruyla birlikte bekler; cevap gelince hepsi birlikte uygulanır. Bekleyen cümlenin
    # özeti ("kısa cevap: 2") taslağa yazılmaz (plan mesajına ve PDF başlığına sızıyordu).
    if k.d.get("son_soru_alani") in ("okuma", "okuma_olcu") and k.d.get("okuma_bekleyen"):
        ob = k.d["okuma_bekleyen"]
        cevap = CO.okuma_cevabi(metin, ob)
        sonraki = "revizyon" if k.d.get("son_is_emri") else "yeni_talep"
        if cevap is None:
            if _icerikli(t) or len((metin or "").split()) > 6 or CO.hizli_istek(metin):
                k.d.pop("okuma_bekleyen", None); k.d["son_soru_alani"] = None
                cok = bool(ob.get("hazir") or ob.get("kalan") or _bekleyen_cati(k, ob))
                k.bekleyen_not = ("Önceki pencere sorumu cevaplamadığınız için " + ("o mesajdaki değişiklikleri" if cok else "o değişikliği")
                                  + " uygulamadım; bu mesajınızı işliyorum. ")
                k.not_dus("kural", "okuma sorusu cevaplanmadan yeni istek geldi: soru düştü")
            else:
                return _okuma_sor(k, ob, yinele=True)
        elif cevap.get("hicbiri"):
            k.d.pop("okuma_bekleyen", None); k.d["son_soru_alani"] = None
            n = int(k.d.get("okuma_hicbiri") or 0) + 1; k.d["okuma_hicbiri"] = n
            k.not_dus("kural", f"okuma cevabı: hiçbiri ({n})")
            if n > 1:
                return _bitir(k, Karar(eylem="yonlendir", gerekce="okuma sorusuna iki kez 'hiçbiri' (PR-2b)",
                                       mesaj="Değişikliği netleştiremedim. " + YONLENDIRME))
            ek = (" Bu mesajdaki öteki değişiklikleri de uygulamadım; hepsini birlikte yazabilirsiniz."
                  if ob.get("hazir") or ob.get("kalan") or _bekleyen_cati(k, ob) else "")
            return _soru(k, "okuma_metin", _celik_neyi(k, katalog) + ek)
        elif "olcu" in cevap:
            en, yuk = cevap["olcu"]
            adaylar = list(ob.get("adaylar") or [])
            k.d.pop("okuma_bekleyen", None); k.d["son_soru_alani"] = None
            k.not_dus("kural", f"okuma cevabı: ölçü {en}x{yuk}")
            if len(adaylar) == 1:
                k.d["okuma_secilen"] = {**_bekleyen_devri(ob), "hazir": list(ob.get("hazir") or []) + [_pencere_op(adaylar[0], en, yuk)]}
                t = Talep(niyet=sonraki, guven=t.guven, ozet="")
            else:
                return _okuma_sor(k, {**ob, "tur": "secim", "olcu": [en, yuk]})
        else:
            secilen = [ob["adaylar"][i] for i in cevap["secimler"]]
            k.d["okuma_secilen"] = {**_bekleyen_devri(ob), "hazir": list(ob.get("hazir") or []) + [_pencere_op(a, *ob["olcu"]) for a in secilen]}
            k.d.pop("okuma_bekleyen", None); k.d["son_soru_alani"] = None
            k.not_dus("kural", "okuma cevabı: " + ", ".join(f"{i + 1} ({a.get('aciklik')})" for i, a in zip(cevap["secimler"], secilen)))
            t = Talep(niyet=sonraki, guven=t.guven, ozet="")
    # "Neyi değiştirelim?" sorusunun cevabı çelik isteği taşıyorsa (ölçü, pencere, çatı K/L, dış 140) LLM niyeti ne olursa olsun revizyondur
    # (ilk planda sorulduysa yeni talep)
    if k.d.get("son_soru_alani") == "okuma_metin" and t.niyet not in ("onay", "red") and CO.hizli_istek(metin):
        k.d["son_soru_alani"] = None
        t = t.model_copy(update={"niyet": "revizyon" if k.d.get("son_is_emri") else "yeni_talep"})
        k.not_dus("kural", "okuma_metin cevabı: çelik revizyon isteği")
    # İE-08 A2 (kapanış incelemesi 13.10): açık çelik seçenek setine yazılı numara ("3", "üçüncü") düğmeyle aynıdır; LLM'in bu kısa
    # cevaba verdiği içerik yok sayılır. İE-25 (geometri hakemi üçüncü tur 2): oda programı ("1+1 olsun", "3+1") numara değildir; talep
    # değişikliğidir, aşağıda okunur. BK-29 PR-3 (pano 208; 13 Kasım 2026 denetimi A6): prefabrik sette de ("3" aynı listeyi yeniden
    # getiriyordu; İE-08 A5'in "prefabrik setler değişmez" sınırı kalktı).
    # İE-42 (hakem tur 8): onaydan sonraki çatı setinde mesajı `_cati_adimi` okur (numara, sıra sözü ve aynı mesajın isteği birlikte);
    # burada koda çevrilirse mesajın öteki isteği sessizce düşüyordu ("2 olsun pencere 2 tane" → "PA06K olsun").
    if k.d.get("son_soru_alani") == "secenek" and _set_acik(k) and not _ODA_PROGRAMI.search(metin or "") and not k.d.get("cati_adimi"):
        st = k.d["secenek_seti"]
        no = CO.okuma_cevabi(metin, {"tur": "secim", "adaylar": st.get("adaylar") or []})
        if no and len(no.get("secimler") or []) == 1:
            kod = next((a.get("kod") for a in st.get("adaylar") or [] if a.get("sira") == no["secimler"][0] + 1), None)
            if kod:
                k.not_dus("kural", f"seçenek setine yazılı numara: {no['secimler'][0] + 1} → {kod}")
                metin = f"{kod} olsun"
                t = Talep(niyet="yeni_talep", guven=t.guven, ozet=f"{kod} seçildi", katalog_kodu=kod)
    # BK-29 PR-3 (pano 208; denetim A5, A7): bayinin yalnız model kodu yazdığı kısa mesaj ("PA-04", "PA-04 olsun") LLM kodu vermese de o
    # modelin seçimidir (K18: kural bayinin kendi sözünü okur). Açık sette "PA-04 olsun" aynı listeyi yeniden getiriyor, boş sohbette
    # "PA-04" "Anlayamadım" alıyordu. Yalnız açık set ya da açık plan olmayan konuşma; açık planın üstüne yazılan kod bugünkü yoldan gider.
    if t.katalog_kodu is None and (_set_acik(k) or not _acik_plan_var(k)):
        kod = _yalniz_kod(metin, katalog)
        if kod:
            k.not_dus("kural", f"mesajda yalnız model kodu: {kod}")
            t = t.model_copy(update={"niyet": "yeni_talep", "katalog_kodu": kod, "belirsizlikler": []})
    # BK-29 tur 9 (v2026.11.15b canlı, adım 5): kodun yanında müşteri adı da yazılınca ("PA-04, müşteri Ayşe Kaya", "PA-04 olsun,
    # müşteri Ayşe Kaya") LLM mesajı "diğer" ya da "onay" okuyor, plan gelmiyordu ("Anlayamadım", "Onaylanacak açık bir plan
    # görünmüyor"). Mesaj yalnız bir model kodu, seçim sözcükleri ve "müşteri <ad>" parçasıysa o modelin seçimidir ve ad müşteri adıdır
    # (K18). LLM kodu ve adı doğru okuyup "yeni talep" dediyse dokunulmaz. Açık planın üstüne yazılan mesaj bugünkü yoldan gider.
    if (_set_acik(k) or not _acik_plan_var(k)) and not (t.niyet == "yeni_talep" and t.katalog_kodu and t.musteri and t.musteri.ad):
        kod, ad = _kod_ve_musteri(metin, katalog, t.musteri.ad if t.musteri else None)
        if kod and t.katalog_kodu and str(Katalog.kod_normalize(t.katalog_kodu) or "").upper() != kod:
            kod = None                                           # LLM başka bir kod okudu: karışmaz, bugünkü yol
        if kod:
            k.not_dus("kural", f"mesajda model kodu ve müşteri adı: {kod}")
            t = t.model_copy(update={"niyet": "yeni_talep", "katalog_kodu": kod, "belirsizlikler": [],
                                     "musteri": (t.musteri or Musteri()).model_copy(update={"ad": ad})})

    # D-01: askıda "yeni talep mi, önceki taslağın değişikliği mi?" sorusu varken gelen mesaj. Yalnız kısa ve saf bir cevap
    # ("yeni", "değişiklik", "önceki taslağın değişikliği") cevap sayılır; o zaman soruyu doğuran mesaj (bekletilen talep ve
    # bayinin o mesajdaki sözü) seçilen yola göre işlenir, LLM'in bu kısa cevaba verdiği niyete bakılmaz.
    eski_taslak_cevabi = None
    if k.d.get("son_soru_alani") == ESKI_TASLAK_SORUSU and k.d.get("bekleyen_talep") and bayi is not None:
        kodlar, kalan_metin = _model_kodlari_ve_kalan(metin, katalog)
        bekleyen_kod = Katalog.kod_normalize(k.d["bekleyen_talep"].get("katalog_kodu") or k.d["taslak"].get("katalog_kodu"))
        if time.time() - (k.d.get("bekleyen_zamani") or 0) > ESKI_SORU_SN:
            _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)          # çok eski soru: normal akış
        elif t.niyet == "onay":
            return _eski_taslak_sor(k)       # "tamam/onay" bu sorunun cevabı değil; eski plan onaylanmaz, bekletilen mesaj düşmez
        elif t.niyet == "red":               # iptal yalnız bekletilen mesajı iptal eder; eski taslağa dokunulmaz
            bekleyen = _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)
            return _bitir(k, Karar(eylem="cevapla", gerekce="bekletilen mesaj iptal edildi (D-01)",
                                   mesaj=f"Bekleyen mesajınızı («{_kisalt(bekleyen)}») iptal ettim; önceki taslağınız olduğu gibi duruyor."))
        elif any(Katalog.taban_kod(c) != Katalog.taban_kod(bekleyen_kod) for c in kodlar):   # İE-08: aynı tabanlı varyant başka model değil
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
    # İE-08 8b M5 (D-06): selamda önce kartın hitabı; ad numaraya düşmüşse (kanal gelen_bayisi) numara yazılmaz
    hitap = str(bayi.get("hitap") or "").strip() or ("" if (not ad or str(ad) == str(bayi.get("numara") or "") or str(ad).isdigit()) else str(ad))

    # İE-42 (D-94): plan onaylandı, çatı seti açık. Çatı seçimi okunur (evin çatısı → onay; başka çatı → aynı plan yeni çatıyla);
    # çatı sözü olmayan istek seti kapatır ve bugünkü yoldan gider.
    t, cati_karari = _cati_adimi(k, t, metin, katalog)
    if cati_karari is not None:
        return cati_karari
    if getattr(k, "cati_adimi_metni", None):          # onay ya da soru sözüyle çatı seçimi: revizyon yalnız çatıyı okur
        metin = k.cati_adimi_metni

    # 1) niyete göre
    if t.niyet == "selam":
        return _bitir(k, Karar(eylem="cevapla", gerekce="selam",
                                mesaj=f"Merhaba{(' ' + hitap) if hitap else ''}. Hangi model ya da ölçü için ön onay planı hazırlayalım? Örnek: {ORNEK_METNI}."))
    if t.niyet in ("diger", "soru", "red") and k.d["asama"] in ("onay_bekliyor", "uretildi", "revizyon") and k.d.get("son_is_emri") \
            and _iptal_olumsuz_sozu(metin):
        # BK-29 tur 6 (tur 5 canlı madde 10): "iptal etmeyin" canlıda "diğer" okunuyor, "Anlayamadım" ve [Talep formu] gidiyordu.
        # Niyet "red" gelince verilen cevabın aynısı (tur 5): talep kapanmaz, değişiklik sorulur. "Neyi değiştirelim?" açıkken
        # niyet "red" okunan "iptal etmeyin" de talebi kapatmaz (olumsuz söz iptal değildir, K21).
        k.d["asama"] = "revizyon"
        return _bitir(k, Karar(eylem="sor", soru_alani="revizyon_ne", gerekce="plan reddedildi",
                                mesaj="Anladım. " + _neyi_degistirelim(k, katalog)))
    if t.niyet == "soru":
        plan_cevabi = _plan_durumu_cevabi(k)                    # BK-29 tur 6 (pano 212, C7): açık ya da onaylı planı olan bayiye planı söylenir
        if plan_cevabi:
            return _bitir(k, Karar(eylem="cevapla", gerekce="genel soru: plan durumu", mesaj=plan_cevabi))
        ek = " Açık bir plan talebiniz devam ediyor; ölçü/model bilgisini yazınca planı hazırlarım." if k.d["asama"] == "topluyor" else ""
        return _bitir(k, Karar(eylem="cevapla", gerekce="genel soru",
                                mesaj="Fiyat, süre ve teslim bilgisi ön onaylı planın ardından teklifle gelir. Plan için model kodu ya da ölçü/oda programı yazmanız yeterli." + ek))
    if t.niyet == "diger":
        return _bitir(k, Karar(eylem="cevapla", gerekce="anlaşılmadı",
                                mesaj=f"Anlayamadım. Ön onay planı için model kodu (örn. P6001) ya da ölçü ve oda programı (örn. \"{ORNEK_PREFABRIK}\") yazabilirsiniz."))
    if t.niyet == "onay":
        if k.d["asama"] == "onay_bekliyor" and k.d.get("son_is_emri"):
            cati = _onay_cati_seti(k, katalog)                 # İE-42 (D-94): çatı seçenekli evde onaydan sonra çatı seti
            if cati is not None:
                return cati
            return _onay_kaydet(k, katalog)
        return _bitir(k, Karar(eylem="cevapla", gerekce="onaylanacak plan yok",
                                mesaj="Onaylanacak açık bir plan görünmüyor. Yeni plan için model kodu ya da ölçü yazabilirsiniz."))
    if t.niyet == "red":
        if k.d["asama"] in ("onay_bekliyor", "uretildi") and not _iptal_sozu(metin):
            k.d["asama"] = "revizyon"
            return _bitir(k, Karar(eylem="sor", soru_alani="revizyon_ne", gerekce="plan reddedildi",
                                    mesaj="Anladım. " + _neyi_degistirelim(k, katalog)))
        k.sifirla()
        return _bitir(k, Karar(eylem="cevapla", gerekce="iptal", mesaj="Talep kapatıldı. Yeni bir plan istediğinizde yazmanız yeterli."))

    # 2) yeni_talep / revizyon
    kapanmis = t.niyet == "yeni_talep" and k.d["asama"] in ("uretildi", "onay_bekliyor", "onaylandi", "yonlendirildi")
    # Bayi açıkça yeni talep dediyse ("yeni talep", "yeni bir ev", "başka müşteri için") süre ne olursa olsun eski taslak kapanır.
    if eski_taslak_cevabi is None and t.niyet in ("yeni_talep", "revizyon") and k.d["taslak"] and _acik_yeni_talep(metin):
        k.sifirla(); k.not_dus("kural", "açık yeni talep sözü: önceki taslak kapandı")
        t = t.model_copy(update={"niyet": "yeni_talep"}); kapanmis = False
    # İE-08: aynı tabandaki varyant (Ç8801 → Ç8801K, çatı seçeneği) başka model değildir; seçenek setinden seçim konuşmayı sıfırlamaz
    baska_model = bool(t.niyet == "yeni_talep" and t.katalog_kodu and k.d["taslak"].get("katalog_kodu")
                       and Katalog.taban_kod(t.katalog_kodu) != Katalog.taban_kod(k.d["taslak"]["katalog_kodu"]))
    # D-01: mesaj eski bir taslağa eklenecekse ve taslak ESKI_TASLAK_SN'den eskiyse, model koduyla başlayan mesajda tahmin
    # edilmez, sorulur (22.09: 3,5 saat sonra gelen "P6001 …" eski aynalı taslağın revizyonu sayılmıştı).
    if eski_taslak_cevabi is None and t.niyet in ("yeni_talep", "revizyon") and k.d["taslak"] and not kapanmis \
            and not baska_model and not getattr(k, "cati_secimi", None) and _eski_taslak(k) and _model_koduyla_basliyor(metin, katalog):
        return _eski_taslak_sor(k, t, metin)
    k.d.pop("eski_taslak_soru", None)
    if t.niyet == "revizyon" and k.d.get("son_is_emri"):
        k.d["revizyon"] += 1
        if k.d["revizyon"] > MAX_REVIZYON and not (getattr(k, "cati_secimi", None) and not getattr(k, "cati_ek", False)):
            # İE-42: onaydan sonraki çatı seçimi revizyon hakkına takılmaz; çatıyla gelen öteki istek takılır (hakem tur 6, D3)
            celik_mi = ((k.d["son_is_emri"].get("yapi") or {}).get("sistem") == "celik")      # İE-08 PR-2b (Lokman, 12.10): mühendis incelemesi
            return _bitir(k, Karar(eylem="yonlendir", gerekce="revizyon sınırı",
                                    mesaj=f"Bu plan için {MAX_REVIZYON} revizyon hakkı doldu" + ("; plan mühendis incelemesine alındı. " if celik_mi else ". ") + YONLENDIRME))
    elif kapanmis:
        k.sifirla()  # önceki proje kapandı ya da insana devredildi; yeni talep
    elif baska_model:
        k.sifirla()  # başka bir modele geçti
    # askıda kalan pencere sorusu cevaplanmadan başka bir istek geldiyse: pencere değişikliğini düşür, bayiye söyle
    dusen_not = ""
    if k.d.get("son_soru_alani") in ("pencere_mahal", "pencere_olcu") and not t.pencereler \
            and not any(v.tur.startswith("pencere") for v in t.varyantlar):
        # BK-29 PR-2: planı üreten taslak varsa yalnız askıdaki istek düşer (eski revizyonların pencereleri kalır); odası sorulan
        # pencere varyantı da düşer (kalınca her mesajda aynı soru yineleniyordu: 13 Kasım denetimi, "Oda 1")
        pt = k.d.get("plan_taslagi")
        if isinstance(pt, dict):
            k.d["taslak"]["pencereler"] = json.loads(json.dumps(pt.get("pencereler") or []))
        else:
            k.d["taslak"].pop("pencereler", None)
        k.d["taslak"]["varyantlar"] = [v for v in k.d["taslak"].get("varyantlar") or [] if v.get("tur") != "pencere_degistir"]
        k.d.pop("pencere_mahal_sorusu", None); k.d["son_soru_alani"] = None
        dusen_not = "Önceki pencere değişikliğini netleştirmediğiniz için uygulamadım; isterseniz sonra ekleriz. "
    # İE-25 (geometri hakemi bulgu 5; ikinci tur 1–2): çatı seti açıkken gelen m², dış ölçü, oda, kat ya da yapı türü değişikliği sessizce
    # düşmez: çatı seti "eskidi" kapanır (eski düğmesi geçmez), seçilen model bırakılır, talep yeni bilgisiyle yeniden okunur (yeni set, soru
    # ya da plan üretimi). Çatı seçimi ve bayinin yazdığı model kodu bunun dışında. Üçüncü tur: LLM'in bağlamdan yinelediği kod (mesajda
    # yazılı değil; K18, `_celik_dali` ilkesi) değişikliği gizlemez ve taslağa geri yazılmaz (1); değişimin kaynağı ya da olumsuz cümledeki
    # kod da seçim değildir ("Ç8801 yerine 100 m² olsun", "Ç8801 olmasın, 3+1 olsun"; dördüncü tur); yeni dış ölçü taslaktaki eski m²'nin,
    # yeni m² eski dış ölçünün yerine geçer (3); tek kenar da değişikliktir (4).
    st0 = k.d.get("secenek_seti") or {}
    if st0.get("durum") == "acik" and st0.get("tur") == "cati_varyanti" and t.niyet in ("yeni_talep", "revizyon") \
            and not _secim_kodlari(metin, katalog):
        taban0 = katalog.aday(next((a.get("kod") for a in st0.get("adaylar") or [] if a.get("sira") == 1), None))
        if _talep_bilgisi_degisti(k.d["taslak"], t, taban0):
            st0["durum"] = "eskidi"
            k.d.setdefault("eski_setler", []).append(st0)
            k.d["eski_setler"] = k.d["eski_setler"][-5:]
            ts0 = k.d["taslak"]
            ts0.pop("katalog_kodu", None)
            yeni_olcu = t.dis_olcu is not None and bool(t.dis_olcu.en_m or t.dis_olcu.boy_m)
            if yeni_olcu and t.alan_m2 is None:
                ts0.pop("alan_m2", None)
            elif t.alan_m2 is not None and not yeni_olcu:
                ts0.pop("dis_olcu", None)
            t = t.model_copy(update={"katalog_kodu": None})
            k.not_dus("kural", "çatı seti açıkken talep bilgisi değişti: set eskidi, talep yeniden okundu")
    if not getattr(k, "cati_secimi", None):           # İE-42: çatı setinden seçilen kod bayinin seçimidir (sıra sözü, etiket, numara)
        t = _yinelenen_kodu_birak(k, t, metin, katalog)
    t = _secim_kopyasini_birak(k, t, katalog)
    t = _pencere_varyantlarina_soz_isle(t, metin)    # G-3/G-4 (29.09): pencere değişikliği tek yoldan, B1 kurallarıyla
    yp_komut = []
    if getattr(k, "yarim_pano", False):              # İE-39 PR-2 (D-90): ayar `yarim_pano.acik`; kapalıyken bugünkü yol
        yp = _yarim_pano_sozu(k, t, metin, katalog)
        if isinstance(yp, Karar):
            return yp
        if yp is not None:
            t, yp_komut = yp
    t = _bayi_adi_musteri_degil(k, t, bayi, metin)   # BK-29 tur 7: LLM'in bağlamdan aldığı bayi adı müşteri adı değildir (K18)
    t = _kaplama_cumlesini_talebe_yaz(k, t, metin)   # İE-20 PR-11 eki (canlı K7): formdan sonra yazılan başka çatı kaplaması düşmez
    k.birlestir(t.model_dump())
    if yp_komut:
        k.d["taslak"]["yarim_pano"] = list(k.d["taslak"].get("yarim_pano") or []) + yp_komut
    _form_izi(k, t, metin or "")                  # İE-20 PR-6: prefabrik talep formunun önceliği ve ölçü izi taslakta
    k.d["asama"] = "topluyor"
    k.d["son_metin"] = (metin or "").strip()      # sıfırlama(lar)dan SONRA: kurallar bayinin bu mesajdaki sözünü okur
    # İE-08 A4 (kapanış incelemesi 13.10): çelik okuması yalnız BU mesajın LLM ipuçlarına bakar; taslakta biriken eski pencere/varyant
    # satırları (düşen, "hiçbiri" denen ya da cevapsız soru) sonraki isteği yönlendirmez. Konuşma kaydına yazılmaz (yalnız bu çağrıda;
    # müşteri bilgisi ikinci kez saklanmasın): bilgi alanları revizyonda tanınmayan cümlenin antet/tablo bilgisi olup olmadığını söyler.
    m = t.musteri.model_dump() if t.musteri else {}
    k.son_llm = {"pencere": bool(t.pencereler) or any(v.tur.startswith("pencere") for v in t.varyantlar),
                 "varyantlar": [v.model_dump(mode="json") for v in t.varyantlar],
                 "bilgi": {**{a: str(b) for a, b in (t.bina_ozellikleri or {}).items() if b},
                           **{a: str(m[a]) for a in ("ad", "sevk_adresi") if m.get(a)}}}
    ts = k.d["taslak"]
    # B1: bu mesajdan gelen pencere satırlarına bayinin BU mesajdaki sözü işlenir (değiştir / ekle / belirsiz). Kural sonraki
    # mesajlarda da bu kayda bakar; "ayna olsun" gibi sonraki bir revizyonun sözü eski pencere satırını yeniden yorumlamaz.
    # Aynı oda için yeni bir satır gelince o odanın eski satırları düşer: son söz geçerli (eski belirsiz satır yeniden sorulmaz).
    if t.pencereler:
        yeni_anahtarlar = {_pencere_anahtari(p) for p in t.model_dump()["pencereler"]}
        yeni_mahaller = {varyant._norm(a[0]) for a in yeni_anahtarlar}
        k.bu_mesaj_mahalleri = set(yeni_mahaller)
        ts["pencereler"] = [p for p in ts.get("pencereler") or []
                            if _pencere_anahtari(p) in yeni_anahtarlar or p.get("pencere_sira") is not None
                            or varyant._norm(_pencere_anahtari(p)[0]) not in yeni_mahaller]   # BK-29 PR-2: seçilmiş pencere kalır
        for p in ts["pencereler"]:
            if _pencere_anahtari(p) in yeni_anahtarlar and p.get("islem_kaynak") != "bayi cevabı" and p.get("pencere_sira") is None:
                p["soz_niyeti"] = _pencere_soz_niyeti(metin, p.get("mahal"), p.get("olcu"))
                p["soz"] = (metin or "").strip()[:300]   # BK-29 PR-2: "Hangi pencere?" bu sözden okunur (sonraki cevap mesajından değil)
    if dusen_not:
        ts["_on_not"] = dusen_not

    # 2a) katalog modeli ya da aday (İE-04: aday kaydındaki şablon; seçim açık seçenek setini kapatır)
    if ts.get("katalog_kodu"):
        aday = _aday_bul(k, katalog, ts["katalog_kodu"])          # İE-14: üretilen plan ("YENI-…") konuşmadaki kayıttan
        model = katalog.bul(ts["katalog_kodu"])
        if aday is None and model is None:
            return _soru(k, "katalog_kodu", f"Katalogda \"{ts['katalog_kodu']}\" kodlu model bulamadım. Kodu kontrol eder misiniz? (örn. P6001, Ç8201, Ç8801)")
        if aday is not None and aday.get("motor") == "genel":      # İE-08 A2/A3: çelik aday (genel motor): çatı seçenekleri ya da r01
            return _celik_dali(k, bayi, katalog, aday, ts)
        kod = aday["kod"] if aday else model["code"]
        cati_istegi = None
        if aday is not None and aday.get("motor") != "genel":
            cati_istegi = getattr(k, "cati_secimi", None)           # İE-42: onaydan sonraki çatı setinden seçim; söz yeniden okunmaz
            if cati_istegi:
                ts["varyantlar"] = [v for v in ts.get("varyantlar") or [] if v.get("tur") != "cati_degistir"]
            else:
                cati_istegi = _prefabrik_cati_istegi(k, katalog, aday, ts)  # İE-37 (hakem): çatı sözü ve açık çatı seti bayinin sözünden
            if isinstance(cati_istegi, Karar):
                return cati_istegi
            if cati_istegi:
                aday, kod = katalog.aday(cati_istegi), cati_istegi
                ts["katalog_kodu"] = kod
        # İE-42 (D-94; Lokman 14 Kasım 2026): çatı seçenekli evde çatı yazılmadıysa plan evin kendi çatısıyla çizilir; çatı seti plan
        # onaylanınca gelir (`_onay_cati_seti`). İE-37'deki "plan seçilince çatı seti" kalktı.
        yol = katalog.sablon_yolu(kod)
        if yol is None:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="şablon kodlanmamış",
                                    mesaj=f"{Katalog.kisa(model) if model else kod} katalogda kayıtlı; çizim şablonu sisteme henüz işlenmedi. " + YONLENDIRME))
        _seti_kapat(k, kod)
        return _is_emri_uret(k, bayi, katalog, json.loads(yol.read_text(encoding="utf-8")), kod, ts)

    # 2b) serbest talep — zorunlu: oda programı + (dış ölçü | pano | alan)
    cok_kat = _cok_katli_prefabrik(k, katalog, ts)             # BK-29 tur 6 (pano 213, A12): iki kat prefabrikte soru sorulmaz, ilk cevapta söylenir
    if cok_kat is not None:
        return cok_kat
    if not ts.get("oda_programi"):
        return _soru(k, "oda_programi", "Kaç oda istiyorsunuz? (örn. 2+1, 3+1, tek oda)")
    nx = ny = None
    if ts.get("yapi_turu") == "celik":
        # İE-08 A2: çelikte pano ızgarası ve GRID_SABLON yok (serbest aks, D-08); dış ölçü verildiyse alana çevrilir, aday kaydından
        # (yedi çelik model; kat süzgeci) seçenek seti; uyan yoksa bugünkü davranış (katalog önerisi metinle)
        alan = ts.get("alan_m2")
        if alan is None and ts.get("dis_olcu") and ts["dis_olcu"].get("en_m") and ts["dis_olcu"].get("boy_m"):
            alan = round(float(ts["dis_olcu"]["en_m"]) * float(ts["dis_olcu"]["boy_m"]), 1)
        if alan is None:
            return _soru(k, "dis_olcu", "Dış ölçü (kısa x uzun, metre) ya da yaklaşık m² verir misiniz?")
        saklandi = _celik_istek_sakla(k)                # set sunulurken mesajdaki değişiklik isteği seçilen modele işlenir (düşmez)
        secenek = _secenekler(k, katalog, {**ts, "alan_m2": alan, "pano": None}, ek_not=CELIK_ISTEK_NOTU if saklandi else "")
        if secenek is not None:
            return secenek
        if getattr(k, "plan_uretimi", False) and plan_uretimi_uygun(ts):
            # İE-14 (D-18): uyan banka modeli yok → yeni plan üretimi. Karar saf kalır: istek konuşmaya yazılır, LLM'i worker çağırır
            # (`kanal/worker.py`), sonucu `plan_sonucu` seçenek setine (yeni plan + bankadan en yakınlar) ya da "uygulayamadım"a çevirir.
            k.d["plan_istegi"] = {"talep": plan_talebi(ts, alan), "mesaj_id": getattr(k, "son_mesaj_id", None)}
            k.not_dus("kural", f"uyan çelik model yok: yeni plan üretimi istendi ({ts['oda_programi']}, {alan:g} m²)")
            return _bitir(k, Karar(eylem="cevapla", gerekce=PLAN_URETIMI,
                                   mesaj=f"{alan:g} m² {ts['oda_programi']} çelik için bankamızda uyan hazır model yok. Sizin için yeni bir "
                                         "plan taslağı hazırlıyorum; birkaç dakika sürebilir."))
        adaylar = katalog.yakin_modeller(float(alan), ts["oda_programi"], "celik", kat=ts.get("kat_sayisi"))
        if adaylar:
            liste = ", ".join(Katalog.kisa(m) for m in adaylar)
            return _soru(k, "model_veya_olcu", f"{alan:g} m² {ts['oda_programi']} çelik için katalog önerilerim: {liste}. Birini seçin ya da dış ölçü verin (örn. 8x7,5 m).")
        return _bitir(k, Karar(eylem="yonlendir", gerekce="çelikte uyan aday ve katalog modeli yok",
                                mesaj=f"Anladım: {ts['oda_programi']}, yaklaşık {alan:g} m² çelik. Bu tanıma uyan hazır model bulamadım; " + YONLENDIRME))
    if ts.get("pano") and ts["pano"].get("nx") and ts["pano"].get("ny"):
        nx, ny = float(ts["pano"]["nx"]), float(ts["pano"]["ny"])
    elif ts.get("dis_olcu") and ts["dis_olcu"].get("en_m") and ts["dis_olcu"].get("boy_m"):
        en, boy = sorted([float(ts["dis_olcu"]["en_m"]), float(ts["dis_olcu"]["boy_m"])])
        nx, ny = pano_sayisi(en, 20), pano_sayisi(boy, 10)
    elif ts.get("alan_m2"):
        # İE-04: aday kaydında uyan aday varsa seçenekler sunulur (öncelik sorusu bir kez); yoksa bugünkü davranış.
        secenek = _secenekler(k, katalog, ts)
        if secenek is not None:
            return secenek
        adaylar = katalog.yakin_modeller(float(ts["alan_m2"]), ts["oda_programi"], ts.get("yapi_turu"), kat=ts.get("kat_sayisi"))
        if adaylar:
            liste = ", ".join(Katalog.kisa(m) for m in adaylar)
            return _soru(k, "model_veya_olcu", f"{ts['alan_m2']:g} m² {ts['oda_programi']} için katalog önerilerim: {liste}. Birini seçin ya da dış ölçü verin (örn. 8x7,5 m).")
        return _soru(k, "dis_olcu", "Dış ölçüyü verir misiniz? (kısa kenar x uzun kenar, metre; örn. 7,5x9)")
    else:
        return _soru(k, "dis_olcu", "Dış ölçü (kısa x uzun, metre) ya da yaklaşık m² verir misiniz?")

    W, H = dis_olcu_cm(nx, ny)
    anahtar = (nx, ny, ts["oda_programi"])
    if anahtar not in GRID_SABLON:
        if ts.get("olcu_formdan") and ts.get("alan_m2") and ts.get("pano"):
            # İE-20 PR-6 (Lokman, 13 Kasım 2026 21:26 UTC): prefabrik talep formu ölçüyü pano katına yuvarlar, alanı da yazar. Bu ölçüyle
            # birebir hazır plan çoğu ölçüde yoktur: seçenekler alana göre sunulur (bayi ölçüyü ön notta görür, `talep_formu.olcu_notu`).
            # Yalnız formdan gelen ölçüde (`_form_izi`); sohbette yazılan pano ölçüsü bugünkü gibi pano ızgarasıyla aranır.
            secenek = _secenekler(k, katalog, {**ts, "pano": None})
        else:
            secenek = _secenekler(k, katalog, {**ts, "alan_m2": None, "pano": {"nx": nx, "ny": ny}})     # İE-04: pano ızgarasıyla aday
        if secenek is not None:
            return secenek
    if anahtar in GRID_SABLON:
        ie = json.loads((ROOT / "is_emri" / GRID_SABLON[anahtar]).read_text(encoding="utf-8"))
        ts.setdefault("belirsizlikler", []).append(f"Grid {nx:g}x{ny:g} pano → onaylı örnek şablonu kullanıldı ({GRID_SABLON[anahtar]}).")
        return _is_emri_uret(k, bayi, katalog, ie, f"GRID-{nx:g}x{ny:g}", ts, on_bilgi=f"Dış ölçü {fmt_m(W)} x {fmt_m(H)} ({nx:g}x{ny:g} pano). ")
    # yerleşim üretici henüz yok → dürüst yönlendirme, ölçü teyidiyle
    return _bitir(k, Karar(eylem="yonlendir", gerekce="serbest yerleşim üretici v0.1'de yok",
                            mesaj=f"Anladım: {ts['oda_programi']}, dış ölçü {fmt_m(W)} x {fmt_m(H)} ({nx:g}x{ny:g} pano). Bu ölçüde hazır yerleşim şablonu yok; " + YONLENDIRME))


KAT_ADI = {2: "İki", 3: "Üç"}


def _cok_katli_prefabrik(k: Konusma, katalog: Katalog, ts: dict) -> Karar | None:
    """BK-29 tur 6 (pano 213; kabul seti A12): iki katlı prefabrik planı çizilmiyor (şablon ve aday tek kat). Bot eskiden oda ve dış ölçü
    sorup sonra yönlendiriyordu; dış ölçü verilince tek katlı ızgara şablonuna da düşebiliyordu. Talep ilk cevapta PortatifEv'e iletilir.
    Katalogda bu kata uyan model varsa (alan ve oda programıyla) bugünkü öneri yolu kalır. Çelik bu kurala girmez (kat süzgeci ve
    yönlendirme `2b` çelik dalında); yapı tipi yazılmamış talep de girmez."""
    try:
        kat = int(ts.get("kat_sayisi") or 1)
    except (TypeError, ValueError):
        return None
    if kat < 2 or ts.get("yapi_turu") != "prefabrik":         # yapı tipi yazılmadıysa bugünkü yol (yapı tipi sorusu: pano 209)
        return None
    if ts.get("alan_m2") and ts.get("oda_programi") and \
            katalog.yakin_modeller(float(ts["alan_m2"]), ts["oda_programi"], ts.get("yapi_turu"), kat=kat):
        return None
    ad = KAT_ADI.get(kat, str(kat))
    return _bitir(k, Karar(eylem="yonlendir", gerekce=f"{kat} katlı prefabrik: plan çizilmiyor",
                            mesaj=f"{ad} katlı ev planını henüz çizemiyorum. Talebinizi PortatifEv'e iletiyorum; size dönüş yapılacak."))


def _celik_dali(k: Konusma, bayi: dict, katalog: Katalog, aday: dict, ts: dict) -> Karar:
    """İE-08 A2/A3 · çelik aday (genel motor). Açık seçenek setinden seçim ya da bayinin metninde çatı seçimi → r01; katalog modelinin
    çatı varyantları varsa ve çatı seçilmemişse numaralı çatı seti (katalog çatısı, K, L; tek görsel, 3 düğme; öncelik sorusu yok)."""
    st = k.d.get("secenek_seti")
    kod = str(aday["kod"]).upper()
    metin = k.d.get("son_metin")
    if str(getattr(k, "cati_secimi", None) or "").upper() == kod:   # İE-42: onaydan sonraki çatı setinden seçim; söz yeniden okunmaz
        k.d["taslak"]["katalog_kodu"] = aday["kod"]
        _seti_kapat(k, aday["kod"])
        return _celik_is_emri_uret(k, bayi, katalog, aday, ts)
    if aday.get("uretilen"):                                   # İE-14: yeni plan çatı varyantı taşımaz; setten seçim ya da revizyon → plan
        _seti_kapat(k, aday["kod"])
        k.d["uretilen_plan"] = aday                            # r3: setteki iki yeni plandan seçilen; revizyon ondan sürer
        return _celik_is_emri_uret(k, bayi, katalog, aday, ts)
    taban = katalog.aday(aday.get("referans_model")) if aday.get("referans_model") and not aday.get("varyantlar") else None
    kat_aday = taban if (taban and taban.get("varyantlar")) else aday
    # Kapanış incelemesi (13.10): seçim ve çatı yalnız BU mesajın sözünden (bayinin yazdığı kod, düğme metni, çatı cümlesi). Taslakta kalan
    # eski kod ("Ç8801" set açılırken yazılmıştı) ya da LLM'in bağlamdan yinelediği kod seçim sayılmaz: set açıkken "L olsun" ya da setin
    # kendi örneği "çatı K olsun" katalog çatısını seçiyordu. "veranda L olsun" çatı değildir (celik_okuma.cati_okumasi).
    # Geometri hakemi dördüncü tur: değişimin kaynağı olan kod ("Ç8801K yerine Ç8801L") seçim değildir; mesajda iki ayrı çatı seçeneği
    # (katalog çatısı dahil: "Ç8801K mi katalog çatısı mı?") ya da setten iki kod geçiyorsa seçim yoktur (kararsızlık; set yeniden sunulur).
    # Beşinci tur: çatı seçeneği taşıyan olumsuz cümle ("Ç8801L olmasın", "Ç8801K'dan Ç8801L'ye geçmeyelim") ve LLM'in seçtiği kodun
    # mesajda değişimin kaynağı olması ("Ç8801K'dan farklı bir çatı olsun") da kararsızlıktır: koddan çatı seçilmez.
    kaynak = {str(Katalog.kod_normalize(c) or "").upper() for c in CO.cati_kaynak_kodlari(metin)}
    mesaj_kodlari = [c for c in (str(Katalog.kod_normalize(x) or "").upper() for x in _model_kodlari_ve_kalan(metin, katalog)[0]) if c not in kaynak]
    mahaller = _aday_mahalleri(aday)
    secenekler = CO.cati_secenekleri(metin, mahaller, CO.norm(str(kat_aday.get("kod") or "")) or None)
    cati = CO.cati_okumasi(metin, kat_aday, mahaller)
    kararsiz = len(secenekler) > 1 or CO.cati_olumsuz(metin, mahaller) or (kod in kaynak and not cati)
    son0 = (k.d.get("son_is_emri") or {}).get("yapi") or {}
    if (getattr(k, "llm_degisiklik", None) or {}).get("durum") == "tamam" and son0.get("sistem") == "celik" \
            and Katalog.taban_kod(son0.get("kod")) == Katalog.taban_kod(kod):            # hata dönen okuma kural okumasını ezmez
        cati, kararsiz = _llm_cati(k, katalog, aday), False      # İE-14 PR-3: revizyonda çatı LLM-önce okumadan (kod denetler)
    if st and st.get("durum") == "acik" and _celik_seti_acik(k):
        set_kodlari = {str(a.get("kod")).upper() for a in st.get("adaylar") or []}
        secimler = list(dict.fromkeys(c for c in mesaj_kodlari if c in set_kodlari))
        secim = None if (kararsiz or len(secimler) > 1) else \
            (cati.upper() if cati and cati.upper() in set_kodlari else None) or next(iter(secimler), None)
        if secim:
            secilen = aday if secim == kod else _aday_bul(k, katalog, secim)
            if secilen is not None and st.get("tur") != "cati_varyanti" and secilen.get("varyantlar"):
                # İE-25 (Lokman 1.11.2026): plan setten seçildi, çatı sonra. Bu mesaj (ya da set sunulurken saklanan istek) çatıyı
                # açıkça seçtiyse ("Ç8801 çatı K olsun", "88 m² 2+1 çelik, çatı L") o çatı; yoksa modelin çatı seti (katalog çatısı, K, L)
                istek_metni = (k.d.get("celik_istek") or {}).get("metin")
                cati0 = cati or (None if not istek_metni or CO.cati_olumsuz(istek_metni, mahaller)
                                 or len(CO.cati_secenekleri(istek_metni, mahaller)) > 1 else CO.cati_okumasi(istek_metni, secilen, mahaller))
                c0 = katalog.aday(cati0) if cati0 and Katalog.taban_kod(cati0) == Katalog.taban_kod(secilen["kod"]) else None
                istek_llm = (k.d.get("celik_istek") or {}).get("llm") or {}
                if c0 is None and ((istek_metni and (CO.cati_olumsuz(istek_metni, mahaller) or len(CO.cati_secenekleri(istek_metni, mahaller)) > 1
                                                     or _celik_cati_sozu(istek_metni, mahaller)))
                                   or any(v.get("tur") == "cati_degistir" for v in istek_llm.get("varyantlar") or [])
                                   or (not cati and _celik_cati_sozu(metin, mahaller, k))):
                    # kararsız ya da seçimsiz çatı sözü ("kırma çatı olsun", "çatı seçeneklerini görelim") planla geldi: set plandan önce
                    # (bugünkü gibi; İE-42 hakem tur 1, bulgu 4: plan katalog çatısıyla çiziliyor, istek düşüyordu)
                    return _cati_varyant_seti(k, bayi, katalog, secilen, ts)
                if c0 is not None:
                    k.not_dus("kural", f"plan ve çatı aynı istekte: {c0['kod']}")
                    _cati_secildi(k, c0["kod"])
                    secilen = c0
                # İE-42 (D-94): çatı yazılmadıysa plan katalog çatısıyla; çatı seti plan onaylanınca (`_onay_cati_seti`)
            if secilen is not None:
                k.d["taslak"]["katalog_kodu"] = secilen["kod"]
                _seti_kapat(k, secilen["kod"])                 # setten seçim (düğme, kod, çatı sözü ya da numara)
                return _celik_is_emri_uret(k, bayi, katalog, secilen, ts)
        if not mesaj_kodlari or kararsiz or len(secimler) > 1:  # seçim yok ya da kararsız: istek saklanır, set yeniden sunulur
            saklandi = _celik_istek_sakla(k)
            uygun = [{**x, **{kk: a.get(kk) for kk in ("sira", "puan", "hesap")}}
                     for a in sorted(st.get("adaylar") or [], key=lambda a: a.get("sira") or 0) for x in [_aday_bul(k, katalog, a.get("kod"))] if x]
            if len(uygun) >= 2:
                return _secenekler(k, katalog, ts, uygun=SC.cati_seti(uygun) if st.get("tur") == "cati_varyanti" else uygun,
                                   tur=st.get("tur") or "alan", referans=uygun[0],
                                   ek_not="Önce listeden seçin (numara ya da düğme)." + (" " + CELIK_ISTEK_NOTU if saklandi else ""))
    son = (k.d.get("son_is_emri") or {}).get("yapi") or {}
    ayni = son.get("sistem") == "celik" and Katalog.taban_kod(son.get("kod")) == Katalog.taban_kod(kod)
    hedef, sozden = None, False
    varyant_kodlari = [c for c in mesaj_kodlari if c != Katalog.taban_kod(c) and Katalog.taban_kod(c) == Katalog.taban_kod(kod)]
    # mesajda iki ayrı çatı ("Ç8801K ve Ç8801L arasında kararsızım", "çatı K mı L mi", "Ç8801L mi Ç8801 mi?") seçim değildir (geometri
    # hakemi üçüncü ve dördüncü tur)
    sozdeki = [c for c in varyant_kodlari if c[-1].lower() in secenekler]
    bekleyen = str((k.d.get("okuma_secilen") or {}).get("kod") or "").upper()
    if cati:
        hedef, sozden = cati.upper(), True
    elif sozdeki and not kararsiz:                             # yazılan varyant kodu ("Ç8801L") çatı seçimidir; taban kod ("Ç8801") değildir
        hedef, sozden = sozdeki[0], True
    elif bekleyen and Katalog.taban_kod(bekleyen) == Katalog.taban_kod(kod):
        hedef = bekleyen                                       # okuma sorusunun cevabı: soru turunda okunan çatı (son planınkine dönülmez; beşinci tur)
    elif ayni:
        hedef = str(son.get("kod")).upper()                    # revizyon: son planın çatısı (kapanmış setin eski seçimi değil; CR7)
    elif st and st.get("durum") == "secildi" and Katalog.taban_kod(st.get("secilen_kod")) == Katalog.taban_kod(kod):
        hedef = str(st.get("secilen_kod")).upper()
    if hedef and hedef != kod:
        secilen = katalog.aday(hedef)
        if secilen is None and sozden:                         # istenen çatı görünmüyor (K-A10 kabul kaydı yok): sessizce eskisi çizilmez
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"istenen çatı varyantı sunulamıyor: {hedef}",
                                    mesaj=f"{hedef} seçeneği şu an sunulamıyor. " + YONLENDIRME))
        if secilen is not None:
            if sozden:
                k.not_dus("kural", f"bayinin sözünden çatı seçimi: {secilen['kod']}")
                _cati_secildi(k, secilen["kod"])
            k.d["taslak"]["katalog_kodu"] = secilen["kod"]
            _seti_kapat(k, secilen["kod"])
            return _celik_is_emri_uret(k, bayi, katalog, secilen, ts)
    if cati and hedef == kod:                                  # yazılan çatı planın kendi çatısı ("katalog çatısı olsun"): seçildi
        _cati_secildi(k, kod)
    # İE-42 (D-94): çatısız seçimde (taban kod) plan katalog çatısıyla çizilir, çatı seti onaydan sonra; kararsız ya da seçimsiz çatı sözü
    # ("kırma çatı olsun", "çatı nasıl olacak?", "çatı seçeneklerini görelim"; hakem tur 1, bulgu 4) planla gelirse set plandan önce (bugünkü gibi)
    if not hedef and kat_aday.get("varyantlar") and (kararsiz or _celik_cati_sozu(metin, mahaller, k)) and not ayni:
        varyantlar = [katalog.aday(v) for v in kat_aday["varyantlar"]]
        uygun = [kat_aday] + [v for v in varyantlar if v is not None]
        if len(uygun) >= 2:
            saklandi = _celik_istek_sakla(k)
            return _secenekler(k, katalog, ts, uygun=SC.cati_seti(uygun), tur="cati_varyanti", referans=kat_aday,
                               ek_not=CELIK_ISTEK_NOTU if saklandi else "")
    _seti_kapat(k, kod)
    return _celik_is_emri_uret(k, bayi, katalog, aday, ts)


CELIK_ISTEK_NOTU = "Mesajınızdaki değişiklik isteğini seçtiğiniz plana işleyeceğim."


def _celik_cati_sozu(metin: str | None, mahaller: list[dict] | None = None, k: Konusma | None = None) -> bool:
    """İE-42 (hakem tur 1, bulgu 4): çelik mesajında seçim yapmayan çatı sözü var mı? Çatının şekli ya da eğimi ("kırma çatı olsun", "çatı
    şekli farklı olsun"), renk ve malzeme dışında "çatı" sözü ("çatı nasıl olacak?", "çatı seçeneklerini görelim"; `celik_okuma` cümle
    işareti `cati_sekil`) ya da LLM'in bu mesajda okuduğu çatı değişikliği (`k.son_llm`). Renk ve malzeme cümlesi bilgidir ("çatı rengi
    kırmızı"); tek ve olumlu çatı seçimi ("çatı K olsun") bu sözden önce okunur (`cati_okumasi`). Hakem tur 2 (D3): LLM okuması renk
    cümlesinde de seti getirir. Bilerek bırakıldı: okunmamış LLM çatı değişikliği planla gelirse çelik kuralı onu yönlendirir (13.10 kuralı,
    `_celik_degisiklikler` madde 1); set yönlendirmeden yumuşaktır, seçimi bayiye bırakır, tahmin etmez (K21)."""
    for p in CO._parcalar(metin, mahaller):
        if (CO.parca_oku(p, {"mahaller": mahaller or []}, None).get("isaret") or {}).get("cati_sekil"):
            return True
    llm = (getattr(k, "son_llm", None) or {}) if k is not None else {}
    return any(v.get("tur") == "cati_degistir" for v in llm.get("varyantlar") or [])


def _secim_kodlari(metin: str | None, katalog: Katalog) -> list[str]:
    """Bayinin bu mesajda seçim olarak yazdığı model kodları (`_celik_dali` ilkesi): değişimin kaynağı olan kod ("Ç8801 yerine …") ve
    olumsuz çatı cümlesindeki kod ("Ç8801 olmasın") seçim değildir."""
    if CO.cati_olumsuz(metin):
        return []
    kaynak = {str(Katalog.kod_normalize(c) or "").upper() for c in CO.cati_kaynak_kodlari(metin)}
    return [c for c in (str(Katalog.kod_normalize(x) or "").upper() for x in _model_kodlari_ve_kalan(metin, katalog)[0]) if c not in kaynak]


def _secim_kopyasini_birak(k: Konusma, t: Talep, katalog: Katalog) -> Talep:
    """İE-20 PR-10 (15 Kasım 2026 canlı denemesi, çelik formu C6 ve C7): bayi planı yazıyla seçince ("KT-02 olsun") LLM seçim cümlesini
    özel istek diye de yazıyordu; cümle paftanın özel isteklerine giriyordu (düğmeyle seçimde özel istek boş). Yalnız bir model kodu ve
    seçim sözcüğü taşıyan özel istek (`_yalniz_kod`) istek değildir: taslağa yazılmaz. Başka söz taşıyan istek ("KT-02 olsun, zemin
    laminat") aynen kalır."""
    ozel = [s for s in t.ozel_istekler if _yalniz_kod(s, katalog) is None]
    if len(ozel) == len(t.ozel_istekler):
        return t
    k.not_dus("kural", f"seçim cümlesi özel istek sayılmadı ({len(t.ozel_istekler) - len(ozel)} satır)")
    return t.model_copy(update={"ozel_istekler": ozel})


def _yinelenen_kodu_birak(k: Konusma, t: Talep, metin: str | None, katalog: Katalog) -> Talep:
    """BK-29 tur 5 (tur 4 canlı A18, 14 Kasım 00:02): LLM revizyon mesajında evin kodunu bağlamdan yineler ("mutfak penceresi 120x120 olsun"
    → katalog_kodu "PA-06"). Taslağa yazılınca seçilmiş çatı (PA06K) sessizce evin kendi çatısına dönüyordu; "hiçbiri" de planı "değişti"
    sayıp r02 çiziyordu. Çizilmiş prefabrik planın aynı tabandaki başka kodu, bayi bu mesajda kod yazmadıysa (K18, `_secim_kodlari`) taslağa
    yazılmaz; plan kendi koduyla kalır. Çatıyı sözle değiştirmek (`_prefabrik_cati_istegi`) ve kodu yazmak bugünkü gibi. Çelik ayrı yoldan."""
    yeni = str(Katalog.kod_normalize(t.katalog_kodu) or "").upper()
    eski = str(Katalog.kod_normalize(k.d["taslak"].get("katalog_kodu")) or "").upper()
    son = str(Katalog.kod_normalize(((k.d.get("son_is_emri") or {}).get("talep") or {}).get("kaynak")) or "").upper()
    if not (yeni and eski and yeni != eski and son == eski and Katalog.taban_kod(yeni) == Katalog.taban_kod(eski)):
        return t
    a = katalog.aday(eski)
    if a is None or a.get("motor") == "genel" or _secim_kodlari(metin, katalog):
        return t
    k.not_dus("kural", f"LLM'in yinelediği kod {t.katalog_kodu} taslağa yazılmadı; plan {eski} kalır")
    return t.model_copy(update={"katalog_kodu": None})


def _talep_bilgisi_degisti(ts: dict, t: Talep, model: dict | None) -> bool:
    """Bu mesajın okuması talebi değiştiriyor mu (çatı seti açıkken): m², dış ölçü, oda, kat ya da yapı türü yeni bir değer taşıyor. Kıyas
    taslaktaki değerle; taslakta yoksa seçilen modelinkiyle (Ç8801: 88 m², 2+1, tek kat, çelik), m² modelin setteki toleransıyla (±%10).
    LLM'in bağlamdan yinelediği aynı değer değişiklik değildir ("Ç8801 olsun" → "K olsun", oda 2+1, kat 1)."""
    model = model or {}
    km2 = model.get("katalog_m2") if isinstance(model.get("katalog_m2"), (int, float)) else None

    def m2_farkli(v: float) -> bool:
        e = ts.get("alan_m2")
        if isinstance(e, (int, float)):
            return abs(float(v) - float(e)) > 1e-6
        return km2 is not None and abs(float(v) - km2) > SC.ALAN_TOLERANS * float(v)

    if isinstance(t.alan_m2, (int, float)) and m2_farkli(t.alan_m2):
        return True
    beklenen = {"oda_programi": ts.get("oda_programi") or model.get("oda_programi"), "kat_sayisi": ts.get("kat_sayisi") or model.get("kat"),
                "yapi_turu": ts.get("yapi_turu") or model.get("yapi_turu")}
    for a, e in beklenen.items():
        v = getattr(t, a, None)
        if v not in (None, "") and e not in (None, "") and str(v) != str(e):
            return True
    d = t.dis_olcu.model_dump() if getattr(t, "dis_olcu", None) is not None else {}
    if d.get("en_m") or d.get("boy_m"):
        e = ts.get("dis_olcu") or {}
        yeni = [d.get("en_m") or e.get("en_m"), d.get("boy_m") or e.get("boy_m")]     # tek kenar taslaktakiyle birleşir (`birlestir`)
        if e.get("en_m") and e.get("boy_m"):
            return sorted(map(float, yeni)) != sorted([float(e["en_m"]), float(e["boy_m"])])
        if all(yeni):
            return m2_farkli(float(yeni[0]) * float(yeni[1]))
        return True                     # m²'yle başlayan talepte tek kenar: alan bilinmez, talep yeniden okunur (eksik kenar sorulur)
    return False


def _cati_varyant_seti(k: Konusma, bayi: dict, katalog: Katalog, taban: dict, ts: dict) -> Karar:
    """İE-25 · çatı varyantlı banka modeli alan setinden (ya da yeni plan setinden) seçildi, set sunulurken kararsız çatı sözü yazıldı
    (İE-42'den beri yalnız bu durumda; çatı yazılmadıysa plan katalog çatısıyla, set onaydan sonra): modelin çatı seti (katalog
    çatısı, K, L; İE-08 A2'nin seti, tek görsel). Seçilen set kayıtta "seçildi" kapanır (yeni set onu eskitmez, `depo._set_kaydi`); set
    sunulurken saklanan istek seçilen çatıya işlenir. Varyantı görünmüyorsa (K-A10 kabul kaydı yok) plan katalog çatısıyla çizilir."""
    uygun = [taban] + [v for v in (katalog.aday(x) for x in taban.get("varyantlar") or []) if v is not None]
    _seti_kapat(k, taban["kod"])
    k.d["taslak"]["katalog_kodu"] = taban["kod"]
    if len(uygun) < 2:
        return _celik_is_emri_uret(k, bayi, katalog, taban, ts)
    eski = k.d.get("secenek_seti")
    if eski and eski.get("durum") == "secildi":
        k.d.setdefault("eski_setler", []).append(eski)
        k.d["eski_setler"] = k.d["eski_setler"][-5:]
    saklandi = _celik_istek_sakla(k)
    k.not_dus("kural", f"plan seçildi, çatı sonra: {taban['kod']} çatı seti")
    k.d["soru_sayisi"] = max(0, int(k.d.get("soru_sayisi") or 0) - 1)   # çatı seti planın seçimiyle aynı soru (hakem ikinci tur 3: MAX_SORU)
    return _secenekler(k, katalog, ts, uygun=SC.cati_seti(uygun), tur="cati_varyanti", referans=taban,
                       ek_not=CELIK_ISTEK_NOTU if saklandi else "")


# ── İE-42 (D-94; Lokman, 14 Kasım 2026 20:33:41 kartı "Onaydan sonra, eskizdeki gibi") · çatı plan onayından sonra ─────────────────────
# Çatı seçenekli evde (bugün PA-06 ve Ç8801) plan evin kendi çatısıyla çizilir. Bayi planı onaylayınca onay hemen kaydedilmez: "Çatı seçin"
# seti gelir (`_onay_cati_seti`; görsel, düğmeler ve liste İE-25/İE-37'nin seti, ilk cümle yeni). Set açıkken (`cati_adimi`) evin kendi
# çatısı seçilirse onay o an kaydedilir (`_onay_kaydet`: prefabrikte Patron'a bildirim, çelikte mühendisin teknik kontrolü); başka çatı
# seçilirse plan aynı kalır, Motor yeni revizyonu o çatıyla çizer, bayi onu onaylar. Çatı sözü olmayan istek seti kapatır ve bugünkü
# yoldan gider (plan değişirse "r01 onayınızı geçersiz kıldı"). Talepte ya da plandan önce çatı seçildiyse (`cati_secilen`) set gelmez.
PLAN_ONAYI = "plan onaylandı"                          # kanal: onay denetimi, mühendis ve Patron kancaları bu gerekçeye bakar


def _cati_secildi(k: Konusma, kod: str) -> None:
    """Bu projede çatı seçildi (kodla, çatı setinden ya da çatı sözüyle): onayda çatı seti yeniden sunulmaz."""
    k.d["cati_secilen"] = str(kod)


def _cati_adi(a: dict | None) -> str:
    return str((a or {}).get("cati_adi") or ((a or {}).get("sunum") or {}).get("cati_adi") or "")


def _plan_cati_secenekleri(katalog: Katalog, ie: dict) -> tuple[dict, list[dict]] | None:
    """Planın evi çatı seçenekli mi ve plan evin kendi çatısıyla mı çizildi? Öyleyse (taban, [taban + görünür çatı seçenekleri]); görünür
    seçenek yoksa (K-A10 kabul kaydı yok), plan bir çatı seçeneğiyle çizildiyse ya da yeni çizilen plansa (İE-14) None."""
    celik_mi = (ie.get("yapi") or {}).get("sistem") == "celik"
    kod = str(((ie.get("yapi") or {}).get("kod") if celik_mi else (ie.get("talep") or {}).get("kaynak")) or "")
    plan = katalog.aday(kod) if kod else None
    if plan is None or plan.get("uretilen"):
        return None
    taban = katalog.aday(Katalog.taban_kod(plan["kod"]))
    if taban is None or not taban.get("varyantlar") or str(taban["kod"]).upper() != str(plan["kod"]).upper():
        return None
    uygun = [taban] + [v for v in (katalog.aday(x) for x in taban["varyantlar"]) if v is not None]
    return (taban, uygun) if len(uygun) >= 2 else None


def _onay_cati_seti(k: Konusma, katalog: Katalog) -> Karar | None:
    """Bayi planı onayladı: plan çatı seçenekli bir evin kendi çatısıyla çizildiyse ve bu projede çatı seçilmediyse çatı seti (onay henüz
    kaydedilmez; aşama "onay_bekliyor" kalır). Yoksa None: onay bugünkü gibi kaydedilir."""
    ie = k.d.get("son_is_emri") or {}
    sec = _plan_cati_secenekleri(katalog, ie)
    if sec is None:
        return None
    taban, uygun = sec
    secilen = str(Katalog.kod_normalize(k.d.get("cati_secilen")) or "").upper()
    if secilen and secilen == str(Katalog.kod_normalize(taban["kod"]) or "").upper():
        return None                                           # bayi bu evin kendi çatısını seçti (kodla, sözle ya da setten)
    if secilen:                                               # hakem tur 2, O3: seçilen çatı bu planda yok (seçim çizilmeden önce
        k.d.pop("cati_secilen", None)                         # yazıldı, sonra başka istek planı evin çatısıyla çizdi): seçim eskidi
        k.not_dus("kural", f"çatı seçimi ({secilen}) onaylanan planda yok: çatı seti yeniden")
    if taban.get("motor") != "genel":                         # prefabrik: kartın görseli çatının ön ve sol görünüşü (İE-37)
        uygun = [{**a, "sunum": {**(a.get("sunum") or {}), "cati_adi": a.get("cati_adi")}, "gorsel": a.get("cati_gorsel") or a.get("gorsel")}
                 for a in uygun]
    no, rev = ie.get("is_emri_no"), int(ie.get("revizyon") or 1)
    eski = k.d.get("secenek_seti")
    if eski and eski.get("durum") == "secildi":
        k.d.setdefault("eski_setler", []).append(eski)
        k.d["eski_setler"] = k.d["eski_setler"][-5:]
    k.d["cati_adimi"] = {"is_emri_no": no, "rev": rev, "kod": taban["kod"]}
    k.d["son_soru_alani"] = None
    k.not_dus("kural", f"plan onaylandı ({no} r{rev:02d}), çatı sonra: {taban['kod']} çatı seti (D-94)")
    bas = (f"Planınız onaylandı (r{rev:02d}). Şimdi çatıyı seçin. Bu eve {len(uygun)} çatı uygulanır. "
           "Plan aynı kalır; yalnız çatı değişir.")
    return _secenekler(k, katalog, k.d.get("taslak") or {}, uygun=SC.cati_seti(uygun), tur="cati_varyanti", referans=uygun[0], bas=bas,
                       gerekce_on="plan onayından sonra çatı seti; ")


def _onay_kaydet(k: Konusma, katalog: Katalog, cati: str | None = None, not_: str = "") -> Karar:
    """Onay bekleyen planın onayı kaydedilir (`PLAN_ONAYI`; kanal onayı bayinin gördüğü revizyona bağlar). `cati`: onaydan sonraki çatı
    setinde evin kendi çatısı seçildi; plan aynen kalır, mesajın başına çatı yazılır. `not_`: aynı mesajın planda zaten olan isteği (D-86)."""
    k.d["asama"] = "onaylandi"
    k.d["son_soru_alani"] = None                               # askıdaki yeni plan sorusu onayla kapanır (soru kaydı açık kalmaz)
    rev = k.d["son_is_emri"].get("revizyon", k.d["revizyon"] + 1)   # gönderilen planın numarası (r01 = 1)
    k.d["onaylanan"] = [k.d["son_is_emri"].get("is_emri_no"), int(rev)]   # BK-29: geri çevrilen sonraki istek onayı geri getirir
    # İE-08 8b (plan kararı 6, Lokman 14.10): çelik plan onaydan sonra mühendisin teknik kontrolüne gider (kanal/muhendis.py)
    sonraki = ("Plan teknik kontrole gönderildi; sonucu size bildireceğiz." if (k.d["son_is_emri"].get("yapi") or {}).get("sistem") == "celik"
               else "Teklif aşamasına geçiliyor.")
    a = katalog.aday(cati) if cati else None
    on = f"Çatı: {_cati_adi(a)} ({SC.gosterim(a)}). Plan r{int(rev):02d} aynen kalır{'; ' + not_ if not_ else ''}. " if a else ""
    return _bitir(k, Karar(eylem="cevapla", gerekce=PLAN_ONAYI, revizyon=rev,
                           mesaj=f"{on}Onayınız kaydedildi ({k.d['son_is_emri'].get('is_emri_no')}, revizyon {rev}). {sonraki}"))


def _cati_soruyla_bekler(k: Konusma, karar: Karar, secim: str) -> bool:
    """Onaydan sonraki çatı setinden seçilen çatı, aynı mesajın pencere sorusuyla bekliyor mu? Çelikte okuma sorusu çatıyı taşır
    (`okuma_bekleyen.kod`), prefabrikte pencere soruları taslaktaki kodla (çatı seçenekli şablon) cevaplanır: cevap çatının revizyonunu çizer."""
    if karar.eylem != "sor":
        return False
    if karar.soru_alani in ("okuma", "okuma_olcu"):
        return str((k.d.get("okuma_bekleyen") or {}).get("kod") or "").upper() == str(secim).upper()
    return (karar.soru_alani in ("pencere_mahal", "pencere_secim", "pencere_islem", "pencere_olcu")
            and str((k.d.get("taslak") or {}).get("katalog_kodu") or "").upper() == str(secim).upper())


def _cati_degismedi_onayi(k: Konusma, d0: dict, katalog: Katalog, secim: str) -> Karar:
    """İE-42 (hakem tur 1, bulgu 6): onaydan sonraki çatı setinde evin kendi çatısı seçildi, aynı mesajdaki istek planda zaten var (D-86:
    plan değişmedi). Konuşma mesajdan önceki hâline döner (planı üreten taslak), çatı seçilir ve plan r01'in onayı kaydedilir; bayiye çatı,
    planın aynen kaldığı ve zaten olan istek yazılır. Çatı seçimi sessizce düşmez."""
    gecmis = k.d.get("gecmis") or []
    k.d = json.loads(json.dumps(d0))
    k.d["gecmis"] = gecmis
    if isinstance(d0.get("plan_taslagi"), dict):
        k.d["taslak"] = json.loads(json.dumps(d0["plan_taslagi"]))
    for a in ("okuma_bekleyen", "okuma_secilen", "okuma_hicbiri", "celik_istek", "pencere_islem_satiri", "pencere_islem_sorusu",
              "pencere_mahal_sorusu", "pencere_secim"):
        k.d.pop(a, None)
    _seti_kapat(k, secim)
    _cati_secildi(k, secim)
    k.d.pop("cati_adimi", None)
    k.d.pop("cati_onayi_dustu", None)
    k.not_dus("kural", f"onaydan sonraki çatı setinde evin çatısı: {secim}; istek planda zaten var, plan onaylandı")
    return _onay_kaydet(k, katalog, cati=secim, not_=getattr(k, "degismedi_notu", "") or "")


def _cati_adimini_kapat(k: Konusma, st: dict, neden: str) -> None:
    """Onaydan sonraki çatı seti seçim yapılmadan kapanır (plan değişikliği, yeni istek): set "eskidi", plan onayı düşer (yeni çizilen
    revizyonun mesajı "r01 onayınızı geçersiz kıldı" der)."""
    ca = k.d.pop("cati_adimi", None) or {}
    st["durum"] = "eskidi"
    k.d.setdefault("eski_setler", []).append(st)
    k.d["eski_setler"] = k.d["eski_setler"][-5:]
    k.d["son_soru_alani"] = None
    if ca.get("rev"):
        k.d["cati_onayi_dustu"] = int(ca["rev"])
    k.not_dus("kural", f"onaydan sonraki çatı seti kapandı: {neden}")


# İE-42 (hakem tur 4, D-D): onaydan sonraki çatı setinde numara cümlesinin hitap, teşekkür ve yeterlik sözü ("1 olsun abi", "1 numaralı çatı
# olsun hocam", "1 olsun saol", "ilk çatı yeterli", "1 yeter") ve ekli sıra sözü ("birinciyi seçiyoruz", "ilkini alalım")
_SECIM_NEZAKET = {"abi", "abim", "abla", "hocam", "hoca", "kardes", "kardesim", "usta", "ustam", "reis", "efendim", "hanimefendi", "bey",
                  "beyefendi", "hanim", "saol", "sagol", "sagolun", "sagolasin", "tesekkurler", "tesekkur", "tsk", "tskler", "eyv", "eyw",
                  "eyvallah", "yeter", "yeterli", "tmm", "tm", "ok", "okey", "peki", "simdilik", "artik", "hadi", "haydi", "alalim", "aliyoruz",
                  "uygun", "uygundur", "iyi", "guzel",
                  # hakem tur 5 (D1): devam ve alma sözü ("K ile devam edelim", "2'yi alın", "K'da kalalım", "kendi çatısıyla devam")
                  "devam", "edelim", "ediyoruz", "edin", "alin", "alinsin", "kalalim", "kaliyoruz", "gelsin", "isleme",
                  # hakem tur 6 (O2): hitap, teşekkür ve yüklemin WhatsApp yazımı ("2 olsun aga", "2 olsun eline sağlık", "2 olsn", "K kalsın")
                  "aga", "kanka", "saolasin", "saolun", "eline", "ellerine", "saglik", "olsn", "olcak", "kalsin", "kalacak"}


def _nezaket(w: str) -> bool:
    """Numara cümlesinde seçimi bozmayan söz: hitap, teşekkür, yeterlik, "olduğu gibi", ek ("1'i seçtik" → "1 i")."""
    return w in _SECIM_NEZAKET or w in _KALSIN_BAGLAM or w in _CATI_EKLERI


def _kendi_catisi_cumlesi(sozler: list[str]) -> bool:
    """Onaydan sonraki çatı setinde evin kendi çatısını söyleyen cümle ("evin kendi çatısı olsun", "aynı çatı kalsın", "olduğu gibi kalsın",
    "mevcut çatı iyi"): planın r01'deki çatısı (hakem tur 4, D-D). Başka sözcük (çatı adı, pencere, istek) varsa değil. Hakem tur 5 (Y1):
    "başka", "farklı" sözü ("mevcut çatıdan farklı olsun") ve olumsuz söz ("evin kendi çatısı olmasın") evin çatısı değildir. Hakem tur 7
    (O2): çatı sözü olmadan planı anan söz ("plan aynı kalsın", "plan olduğu gibi kalsın") iki türlü okunur ("değişiklik yok" ya da "evin
    çatısı"; set mesajı "Plan aynı kalır" der): evin çatısı değildir, sorulur."""
    if any(w in _BASKA_SOZU or CO._OLUMSUZ_FIIL_T.fullmatch(w) for w in sozler):
        return False
    if any(w.startswith("plan") for w in sozler) and not any(w.startswith("cati") for w in sozler):
        return False
    return bool(sozler) and any(w in ("kendi", "mevcut", "ayni", "eski", "oldugu") for w in sozler) and all(
        w in _CATI_BAGLAM or _nezaket(w) or w.startswith("cati") or CO._KALSIN_T.fullmatch(w) or w in ("ayni", "evin", "ev")
        for w in sozler)
_SIRA_EKI = ("i", "yi", "ni", "ini", "u", "yu", "nu", "unu", "in", "nin", "nun", "yle", "yla", "le", "la", "de", "da", "te", "ta", "den",
             "dan", "ye", "ya")                                # hakem tur 5: "ikinciyle devam", "birincide kalalım"


def _sira_kok(w: str, sira: dict) -> str | None:
    """Sıra sözü ekiyle de ("birinciyi", "ilkini", "sonuncuyu"): sözlükteki karşılığı; değilse None."""
    if w in sira:
        return w
    return next((s for s in sorted(sira, key=len, reverse=True) if w.startswith(s) and w[len(s):] in _SIRA_EKI), None)


# İE-42 (hakem tur 8, Y3): sıra sözünden sonra bu sözler gelirse sıra sözü çatı numarası değildir ("son haliyle onaylıyoruz", "son
# olarak", "ilk olarak", "ikinci kez", "son plan", "ilk çizim")
_SIRA_DISI_SONRA = ("hal", "olarak", "kez", "defa", "sefer", "plan", "ciz", "pdf", "gorsel", "versiyon", "surum", "revizyon", "durum",
                    "teklif", "mesaj", "karar")


def _sira_baglami(sozler: list[str], sira: dict) -> list[str]:
    """Çatı numarası olmayan sıra sözü boş sözcüğe çevrilir (`_SIRA_DISI_SONRA`); öteki sözcükler aynen. Boş sözcük dolgudur."""
    return ["" if _sira_kok(w, sira) and i + 1 < len(sozler) and sozler[i + 1].startswith(_SIRA_DISI_SONRA) else w
            for i, w in enumerate(sozler)]


def _celik_cati_adimi_okumasi(k: Konusma, katalog: Katalog, taban: dict, metin: str | None, st: dict,
                              cati_istegi: bool = False) -> str | Karar | None:
    """Çelik çatı setinde (onaydan sonra) bu mesajın çatı seçimi, bayinin sözünden (`_celik_dali` ilkeleri): yazılı kod (düğme ve numara
    koda çevrilmiş gelir) ya da çatı cümlesi ("çatı K olsun", "katalog çatısı"); tek ve olumlu ise kod. Hakem tur 2 (O7): yalnız numara ya
    da sıra sözünden oluşan cümle ("2 olsun", "ikinci çatı olsun") başka cümleyle birlikte de setin numarasıdır (prefabrik okumasıyla aynı);
    o cümle revizyon metninde koda çevrilir (`k.cati_numara_metni`). İki çatı, olumsuz çatı cümlesi ya da seçimsiz çatı sözü (çatı kökü:
    "kırma olsun"; ya da LLM'in `cati_degistir` okuması) "Hangi çatı olsun?"; çatı sözü yoksa None."""
    set_kodlari = {str(a.get("kod")).upper() for a in st.get("adaylar") or []}
    son_sira = str(max([int(a.get("sira") or 0) for a in st.get("adaylar") or []] or [0]))
    sira = {**_SIRA_SOZU, "son": son_sira, "sonuncu": son_sira}
    harfler, _ = _set_etiketleri(taban, st)
    numaralar, kalan = set(), []
    for ham in _cumleler(metin):
        sozler = CO.norm(ham).split()
        if _eksiltili(ham):                                    # hakem tur 8 (Y1): "2 de", "ikinciye de" seçim değil
            kalan.append(ham)
            continue
        etiket = [w for w in sozler if w in harfler]
        # hakem tur 5 (D1): devam ve alma sözlü etiket cümlesi ("K ile devam edelim", "K'yı alın", "K'da kalalım"); şekil sözü ("L tipi")
        # ve başka/farklı sözü olan cümle değil (çelik okuması bakar)
        if len(etiket) == 1 and not any(w in _BASKA_SOZU or w in ("tip", "tipi", "seklinde", "sekli") for w in sozler) and all(
                w in harfler or w in _CATI_BAGLAM or w.startswith("cati") or w in _SECIM_NEZAKET or w in _CATI_EKLERI for w in sozler):
            numaralar.add(harfler[etiket[0]])
            continue
        sozler = _sira_baglami(sozler, sira)                   # hakem tur 8 (Y3): "son haliyle", "son olarak" çatı numarası değil
        sayi = [w for w in sozler if w.isdigit()] + [sira[_sira_kok(w, sira)] for w in sozler if _sira_kok(w, sira)]
        if sozler and len(sayi) == 1 and all(w.isdigit() or _sira_kok(w, sira) or w in _CATI_BAGLAM or w.startswith("cati") or w in _NUMARA
                                             or _nezaket(w) for w in sozler):
            numaralar |= {str(a["kod"]).upper() for a in st.get("adaylar") or [] if str(a.get("sira")) == sayi[0]}
            continue
        if _kendi_catisi_cumlesi(sozler):                      # "evin kendi çatısı olsun", "aynı çatı kalsın" (hakem tur 4)
            numaralar.add(str(taban.get("kod")).upper())
            continue
        kalan.append(ham)
    k.cati_numara_metni = ", ".join(_cumle_temiz(h) for h in kalan) if numaralar else None
    metin_k = ", ".join(_cumle_temiz(h) for h in kalan) if numaralar else metin    # numara cümlesi kod okumasına girmez
    mahaller = _aday_mahalleri(taban)
    kodlar = {c for c in _secim_kodlari(metin_k, katalog) if c in set_kodlari} | numaralar
    cati = CO.cati_okumasi(metin_k, taban, mahaller)
    if cati and str(cati).upper() in set_kodlari:
        kodlar.add(str(cati).upper())
    secenekler = CO.cati_secenekleri(metin_k, mahaller, CO.norm(str(taban.get("kod") or "")) or None)
    olumsuz = CO.cati_olumsuz(metin_k, mahaller)
    if len(kodlar) == 1 and not olumsuz and len(secenekler) <= 1:
        return next(iter(kodlar))
    n = CO.norm(metin or "")
    if kodlar or secenekler or olumsuz or cati_istegi or any(re.search(rf"\b{kok}", n) for kok in _CATI_KOKLERI):
        k.not_dus("kural", "onaydan sonraki çatı setinde seçim yok ya da kararsız: soru")
        return _cati_sorusu(k, st)
    return None


def _cumleler(metin: str | None) -> list[str]:
    """Mesajın cümle parçaları, sonlarındaki noktalama işaretiyle ("PA-06-K nasıl bir çatı?" → soru işareti parçada kalır). İki rakamın
    arasındaki virgül ve nokta bölmez ("85,5 m2", "7,5x11,5", "1,20x1,20"; hakem tur 3)."""
    korunan = re.sub(r"(?<=\d)([.,])(?=\d)", lambda m: "\x00" if m.group(1) == "," else "\x01", metin or "")
    return [h.replace("\x00", ",").replace("\x01", ".") for h in re.findall(r"[^.,;:!?\n]+[.,;:!?\n]*", korunan) if h.strip()]


def _cumle_temiz(h: str) -> str:
    return h.strip().rstrip(".,;:!\n").strip()


# İE-42 (hakem tur 2, O2 ve D4; tur 3): çatıyı yalnız soru olmayan cümle seçer (her niyette); onay sözü cümleden çıkar.
_SORU_SOZU = {"ne", "neden", "niye", "nedir", "nasil", "nasildir", "kac", "kaca", "hangi", "hangisi", "mi", "mu", "misiniz", "musunuz",
              "midir", "mudur", "misin", "musun", "miyiz", "muyuz"}
_NE_UNLEM = {"guzel", "hos", "iyi", "harika", "guzelmis", "hosmus", "iyiymis"}       # "ne güzel olmuş" soru değil
_ONAY_SOZU = re.compile(r"\b(?:onay\w*|tamam\w*|evet)\b", re.IGNORECASE)
# hakem tur 4: iki sözcüklü nezaket kalıbı ("sağ olun", "kolay gelsin", "iyi günler") seçim ve istek değildir; "sağ" tek başına yöndür
# hakem tur 5: "sağ olsun" teşekkür değildir ("kalkan sağ olsun" yön sözüdür, Y2); "başka değişiklik yok", "başka bir isteğimiz yok", "başka
# değişiklik istemiyoruz" istek değildir (O2); tur 7 (D3): "eline sağlık" teşekkürdür ("K olsun, eline sağlık mutfak penceresi …")
_NEZAKET_SOZU = re.compile(r"\bsa[gğ]\s*ol(?:un|as[ıi]n)?\b|\b(?:eline|ellerine|eme[gğ]ine)\s*sa[gğ]l[ıi]k\b|\bkolay\s*gelsin\b|\biyi\s*(?:g[üu]nler|ak[şs]amlar|[çc]al[ıi][şs]malar)\b"
                           r"|\bhay[ıi]rl[ıi]\s*i[şs]ler\b|\bbu\s*[şs]ekilde\b"
                           r"|\b(?:ba[şs]ka|ekstra|ilave)\s+(?:[^\s,.;:!?]+\s+){0,2}?(?:yok\w*|istemiyor\w*|istemeyiz|gerek\s*yok\w*)(?=$|[\s,.;:!?])"
                           r"|\bba[şs]ka\s+(?:bir\s+)?(?:[şs]ey|iste[gğ]\w*|de[gğ]i[şs]iklik\w*)\s+(?:yok\w*|istemiyor\w*)(?=$|[\s,.;:!?])",
                           re.IGNORECASE)


def _soru_cumlesi(ham: str) -> bool:
    """Cümle soru mu: soru işareti ya da soru sözcüğü ("PA-06-K nasıl bir çatı", "K mi C mi"). "ne güzel" ünlemdir, soru değil."""
    if "?" in ham:
        return True
    w = CO.norm(ham).split()
    return any((x in _SORU_SOZU and not (x == "ne" and i + 1 < len(w) and w[i + 1] in _NE_UNLEM)) or _BITISIK_SORU.fullmatch(x)
               for i, x in enumerate(w))                       # tur 26 (Y4): "1 olsun tamammı"


def _cati_adimi_secim_metni(metin: str | None) -> str:
    """Çatı setinde mesajın çatı seçimi ve plan isteği okunan kısmı: soru cümleleri ("PA-06-K nasıl bir çatı?", "Ç8801K'nın fiyatı ne
    kadar?", "100 m2 olur mu?") çıkar, onay sözü ("onaylıyorum", "tamam", "evet") cümleden silinir ("2 olsun onaylıyorum" → "2 olsun").
    Soru seçim ve istek değildir (K21); soru cümlesindeki istek bayiye "uygulayamadım" diye yazılır (`_cati_icerik_cumleleri` sayar)."""
    parcalar = []
    for ham in _cumleler(metin):
        if _soru_cumlesi(ham):
            continue
        parca = _cumle_temiz(_ONAY_SOZU.sub(" ", _NEZAKET_SOZU.sub(" ", ham)))
        if CO.norm(parca):
            parcalar.append(re.sub(r"\s+", " ", parca))
    return ", ".join(parcalar)


# İE-42 (hakem tur 3, Y1): çatı setinde seçim cümlesini kuran sözcükler. Bu sözcüklerin dışında bir sözcük taşıyan cümle istek ya da bilgidir.
_SECIM_DOLGU = {"evet", "ok", "okey", "peki", "anladim", "anlasildi", "tabi", "tabii", "super", "guzel", "harika", "cok", "olmus",
                "gorunuyor", "begendik", "begendim", "kalsin", "olmasin", "istemiyoruz", "istemiyorum", "istemeyiz", "degil", "yerine",
                "vazgectik", "vazgectim", "daha", "simdi", "artik", "hemen", "bence", "bizce", "yani", "icin", "dedik", "dedim", "diyoruz",
                "diyelim", "lazim", "yok", "degisiklik", "degismesin", "ayni", "aynen", "calismalar", "ederiz", "ederim", "sagolun",
                "kolay", "rica", "hos", "iyi",
                # onay ve devam sözü ("onay veriyoruz", "devam edelim", "işleme alın", "müşteri beğendi", "PA-06'da kalalım"; hakem tur 4, O-B)
                "veriyoruz", "veriyorum", "verdik", "verdim", "verildi", "devam", "edelim", "ediyoruz", "edin", "ediniz", "edebilirsiniz",
                "uygundur", "boyle", "kalalim", "kaliyoruz", "isleme", "alin", "alinsin", "alabilirsiniz", "saygilar", "saygilarimla",
                "begendi", "begendiler", "begeniyor", "begeniyoruz", "begenildi", "lik", "luk", "yeter", "yeterli", "saol", "sagolasin",
                "bekliyoruz", "bekliyorum", "bekleriz", "sorun", "devami", "gelsin",
                # kararsızlık sözü ("çatı K mı L mi bilemedim"): seçim yok, istek de yok → "Hangi çatı olsun?"
                "bilemedim", "bilemedik", "bilmiyorum", "bilmiyoruz", "karar", "veremedim", "veremedik", "kararsiz", "kararsizim",
                "kaldik", "kaldim", "arasinda", "dusunuyoruz", "dusunuyorum", "emin", "degilim", "degiliz",
                # hitap, kısaltma ve dua sözleri ("1 olsun kardeşim", "tmm 2", "Allah razı olsun")
                "kardes", "kardesim", "usta", "ustam", "reis", "abla", "abi", "abim", "hocam", "hoca", "efendim", "hanimefendi", "tmm", "tm",
                "tsk", "tskler", "eyv",
                "eyw", "eyvallah", "allah", "razi", "insallah", "hepsi", "en", "iyisi", "guzeli", "uygun", "pdf", "gorsel", "gorseli",
                "cizim", "cizimi", "sonra", "ayrica", "halini", "haline", "halinde", "halde",
                "ise",                                 # hakem tur 7 (Y4): "… olsun çatı ise 2"
                "neyse", "oyleyse", "boyleyse",        # tur 12 (D): "Neyse 1 olsun", "Öyleyse 2 olsun"
                # tur 28: bildirilmiş onay ve teklifin gönderilmesi ("müşteri kabul etti", "onay verdi", "teklifi mail atın", "whatsapptan
                # atın"); "kabul etmedi", "fiyatı kabul etti" değil
                "kabul", "etti", "ettiler", "verdi", "verdiler", "atin", "atiniz", "atar", "atarsiniz", "atarmisin", "atarmisiniz",
                "atabilir", "atabilirsiniz", "mail", "maile", "mailden", "maille", "whatsapp", "whatsapptan", "wp", "wpden", "hazirlarsiniz",
                "hazirlayin", "hazirlar", "hazirlayabilir", "hazirlayabilirsiniz", "iletin", "iletirsiniz"}
_SECIM_KOKU = ("cati", "onay", "tamam", "tesekkur", "sagol", "besik", "kirma", "kalkan", "cumba", "katalog", "numara", "sira", "model",
               "sec", "tercih", "plan", "ilk", "birinci", "ikinci", "ucuncu", "sonuncu", "musteri", "gonder", "teklif")
# İE-42 (hakem tur 6, O2): seçimi bize bırakan ("fark etmez", "siz seçin", "hangisi iyiyse", "standart olsun") ve seçimi erteleyen söz
# ("müşteriye soralım, sonra döneriz") çatı setinde istek değildir: seçim yoksa "Hangi çatı olsun?" (set açık kalır; K21). Erteleyen söz
# seçimle gelse de seçim kaydedilmez, sorulur (`_ERTELEME_SOZU`, `_cati_atiflari`).
_DEVIR_SOZU = {"fark", "etmez", "farketmez", "siz", "size", "secin", "secebilirsiniz", "hangisi", "iyiyse", "uygunsa", "olursa", "ikisi",
               "biraktik", "birakiyoruz", "birakiyorum", "standart", "normal", "ucuzu", "ucuz", "degistirmeyin", "dokunmayin",
               "soralim", "sorup", "sorariz", "soracagiz", "doneriz", "donecegiz", "donus", "yapacagiz", "yapariz", "bakip", "dusunelim",
               "dusunup", "dusunecegiz", "henuz", "haber", "verecegiz", "veririz",
               # hakem tur 8 (O1): "müşteri karar verince haber vereceğiz", "konuşup bildiririz"
               "verelim", "bildiririz", "bildirecegiz", "bildirelim", "konusup", "gorusup", "danisip", "netlesince", "verince"}
# hakem tur 7 (D2), tur 8 (O1): haber verme sözü ("haber veririz", "bildiririz") erteleme sözüdür; aynı cümle başka bir konuyu anıyorsa
# ("montaj tarihini haber veririz") değildir (`_HABER_KONU`)
# hakem tur 11 (Y-1): zaman bağı her fiilde zaman bağıdır ("kabul edince", "evet deyince", "kapora yatınca", "kredi çıkınca"; tur 10'un fiil
# listesi bunları kaçırıyordu); zaman bildirmeyen ekli sözler sayılmaz (`_ZAMAN_DISI`: "boyunca", "süresince", "gereğince", "yeterince",
# "kalınca", "olabildiğince", "mümkün olduğunca"). Zaman ve koşul kalıpları da: "-dığında", "-dıktan sonra", "-madan önce", "takdirde"
_ZAMAN_BAGI_DESEN = r"\w{2,}(?:ince|inca|unce|unca)"
_ZAMAN_DISI = re.compile(r"\w*(?:boyunca|suresince|gerekince|geregince|yeterince|kalinca|derince|uzunca)|\w*[dt][iu]g(?:ince|inca|unca|unce)")
_ERTELEME_SOZU = re.compile(r"\b(?:soralim|sorup|sorariz|soracagiz|doneriz|donecegiz|donus\s+yap\w*|bakip|dusunelim|dusunup|dusunecegiz"
                            r"|henuz|haber\s+ver\w*|bildir\w*|konusup|gorusup|danisip|netlesince|verince"
                            # hakem tur 9: "karar vereceğiz", "müşteri karar verecek"; zaman bağı ("fiyatı öğrenince", "ödeme yapınca");
                            # tur 10: "siz karar verin", "ona göre", "bekliyoruz" kararı erteler ya da bize bırakır (bağlamı
                            # `_erteleme_var`'da); tur 11: "-dığında", "-dıktan sonra", "-madan önce", "takdirde"
                            r"|karar\s+ver(?:ecek|ece[gk]|ir|elim|sin|in)\w*|ona\s+gore|buna\s+gore|bekl\w*|" + _ZAMAN_BAGI_DESEN
                            + r"|\w+[dt][iu]g(?:inda|unda|inde|unde)|\w+[dt][iu]k(?:tan|ten)\s+sonra|\w+m[ae]d[ae]n\s+once"
                            r"|takdirde|durumunda|sartiyla|kosuluyla)\b")
# tur 12 (O-3), tur 13 (Orta-3), tur 14 (Orta-2, Orta-5): planın bir yerini anan istekte zaman sözü yalnız o yere giren, geçen, gelen ya da
# o yeri açan, gören hareketin zamanıysa isteğin betimidir ("kapıdan girince soldaki …", "salona girdikten sonra sağdaki …", "mutfağa
# girmeden önce …", "kapı açıldığında", "pencereye gelince"); öteki zaman ("kapora yatınca", "tapu alındığında", "havale yapıldığında",
# "teklif kabul edildiğinde") seçimin zamanı da olabilir: sorulur (`_betim_zamani`). Tur 15 (O-2): yer sözü yön eki almış oda, kapı ya da
# pencere olmalı ("kapıdan", "salona", "yatak odasına", "yatak odası 1'e"; "eve", "kapılar", "ölçü", "usta" değil); kapı ve pencerenin
# açılıp kapanması yalın da olur ("kapı açıldığında"). Bakma ve görme fiili ("salona bakınca söyleriz") ve bizim kararımızı anan fiil
# ("bakarız", "söyleriz", "sevinirim") betim değildir
_HAREKET_KOKU = ("gir", "gec", "gel", "cik", "don", "yuru", "ac", "kapa", "ilerle")
_YON_EKI = {"e", "a", "ye", "ya", "ne", "na", "den", "dan", "ten", "tan", "nden", "ndan"}
_BIZ_FIILI = ("riz", "ruz", "rim", "rum", "giz", "cegim", "cagim", "elim", "alim", "ayim", "eyim")   # tur 19: "bir sorayım"
# tur 16: zaman sözünün hemen ardından gelen konum sözü ("soldaki", "sağdaki", "karşıdaki") ve onun ardındaki oda, kapı ya da pencere
# hareketi betim yapar ("eve girince soldaki yatak odası", "salondan bakınca soldaki …", "salona oturunca karşıdaki …"); konum sözü yoksa
# "eve gelince", "eve dönünce" seçimin zamanıdır
_KONUM_SOZU = re.compile(r"(?:sol|sag|karsi|on|arka|yan|orta|kose|ust|alt|ic|dis|iceri|disari|ilk|son)(?:da|de|ta|te)ki")
_KONUM_FIILI = _HAREKET_KOKU + ("bak", "otur")
# tur 16 (O-B): betimi bozan bizim fiilimiz yalnız kararı erteleyen ya da bize bırakan fiildir ("bakarız", "söyleriz", "döneriz",
# "karar veririz"); isteğin kendi fiili ("istiyoruz", "yapalım", "ekleyelim", "rica ederiz", "seviniriz") betimi bozmaz
_BIZ_ERTELEME_KOKU = ("bak", "soyle", "dusun", "karar", "haber", "bildir", "konus", "gorus", "danis", "sor", "don", "ilet", "yaz", "ara",
                      "kontrol", "incele", "degerlendir", "netles", "kesinles", "sec", "belirle", "goster", "anlas", "ver",
                      "gor", "anla", "halle", "teyit", "ogren", "olc", "tespit", "hesapla",   # tur 17 (O-K): "görürüz", "anlarız"
                      "ayarla")                                                               # tur 18: "sonra ayarlarız"
# tur 17 (O-B): istek kipi ("120x180 yazalım", "verelim", "seçelim") isteğin kendi fiilidir; yalnız düşünme ve konuşma fiili ya da "karar"dan
# sonra ("bakalım", "konuşalım", "karar verelim") ertelemedir
_BIZ_ISTEK_KIPI = ("elim", "alim", "ayim", "eyim")
_BIZ_ISTEK_ERTELEME = ("bak", "dusun", "konus", "gorus", "danis", "bekle", "gor", "anla", "degerlendir", "incele", "netlestir",
                       "kesinlestir", "sor")
# tur 19 (O1), tur 20 (O2): sonraki zamanla istek kipi ertelemedir ("sonra seçelim", "sonra değiştirelim", "yarın tekrar yazalım"); yalnız
# işin kendisi ("yarın imzalayalım", "haftaya başlayalım", "sonra gönderelim", "yarın uğrayalım") değil (`_SONRA_IS_KOKU`)
_SONRA_IS_KOKU = ("imza", "basla", "gonder", "ode", "gel", "ugra", "yatir", "devam", "kur", "sevk", "getir", "yukle", "tasi", "teslim",
                  "cik", "yola", "bulus")
_SONRA_ERTELEME_KOKU = ("sec", "belirle", "karar", "netles", "kesinles", "degerlendir", "incele", "konus", "gorus", "danis", "dusun",
                        "bak", "gor", "kontrol", "teyit", "hesapla", "olc", "ayarla", "halle", "sor", "don", "anlas", "ara", "ogren",
                        "tespit", "bildir", "haber", "soyle")
# tur 18 (Orta 6): "sonra", "ileride" gibi sonraki zamanla istek kipi de ertelemedir ("… 120x180 olsun sonra seçelim")
_SONRAKI_ZAMAN = ("sonra", "ileride", "sonradan", "yarin", "haftaya", "sonraki")
# tur 17: kararın sonra belli olacağını söyleyen söz ("netlik kazanır", "belli olur", "anlaşılır") betim değildir
_BELLI_OLMA_KOKU = ("netlik", "netles", "kesinles", "belli", "anlasil", "belirginles")


def _belli_olma(sozler: list[str]) -> bool:
    """Kararın sonra belli olacağını söyleyen söz ("netlik kazanır", "belli olur", "ortaya çıkar"; "ortaya bakan pencere" değil)."""
    return any(w.startswith(_BELLI_OLMA_KOKU) or (w == "ortaya" and i + 1 < len(sozler) and sozler[i + 1].startswith("cik"))
               for i, w in enumerate(sozler))
# tur 17 (O-K): "kontrol ederiz", "teyit ederiz" de ertelemedir
_ERTELEME_ADI = ("kontrol", "teyit", "tespit", "karar", "olcum", "hesap", "revize", "gozden")   # tur 20: "sonra revize edelim"


_ERTELEME_DOLGU = {"ele", "yeniden", "bastan",                                  # tur 20: "sonra yeniden ele alalım"
                   "sonra", "bir", "de", "da", "biz", "bunu", "onu", "sunu", "bunlari", "hepsini", "tekrar", "yine", "beraber",
                   "birlikte", "musteriyle", "musteriye", "musteri", "musterimiz", "musterimizle", "ile", "once", "daha", "hele",
                   "simdilik", "ilk", "kez", "yerinde", "sahada", "ama", "ve", "ancak", "fakat", "yalniz", "tabi", "tabii", "bence",
                   "olarak", "kesin", "ayrica", "bi", "bakalim", "hemen", "en", "son", "gec", "ki", "o", "zaman", "simdi", "ondan",
                   "ardindan", "sonrasinda", "sizinle", "size", "siz", "sizlerle", "esimle", "hanimla", "ustayla", "ekiple"}


def _yalin_erteleme(sozler: list[str]) -> bool:
    """Cümle yalnız bizim ertelememizden mi kurulmuş (tur 18 kalanı, Orta 6): "sonra kontrol edelim", "bir bakalım", "teyit ederiz",
    "ölçüm yaparız", "müşteriye teyit ettirelim". Konusu olan cümle ("rengini sonra seçeriz") o konunun ertelemesidir."""
    if not sozler or not _biz_ertelemesi(sozler) or _veda(sozler) or _karar_bildirimi(sozler):
        return False                                           # "görüşürüz" vedalaşmadır; "kararı veriyoruz" karar bildirimidir
    return all(w in _ERTELEME_DOLGU or w.startswith(_ERTELEME_ADI + _SONRAKI_ZAMAN + _KARAR_ZAMANI) or w.endswith(_BIZ_FIILI)
               for w in sozler)


def _ertelemeli(sozler: list[str]) -> bool:
    """Cümle yalın erteleme mi ya da seçimin yükleminden sonrası yalın erteleme mi ("1 olsun bir bakalım", "Ç8801 olsun sonra bir
    bakalım"; tur 19, Y3). Soru eki atılır ("müşteriye soralım mı?", "bir düşünelim mi?")."""
    ws = [w for w in sozler if not _SORU_EKI.fullmatch(w)]
    j = max((n for n, w in enumerate(ws) if w in _YUKLEM_SOZU), default=-1)
    return _yalin_erteleme(ws) or (j >= 0 and _yalin_erteleme(ws[j + 1:]))


def _biz_ertelemesi(sozler: list[str]) -> bool:
    """Cümlede kararı erteleyen ya da bize bırakan bizim fiilimiz var mı (tur 16, O-B; tur 17, O-K, O-B)."""
    sonraki_zaman = any(w.startswith(_SONRAKI_ZAMAN) for w in sozler)
    for i, w in enumerate(sozler):
        if not w.endswith(_BIZ_FIILI):
            continue
        o = sozler[i - 1] if i else ""
        if w.endswith(_BIZ_ISTEK_KIPI):
            if w.startswith(_BIZ_ISTEK_ERTELEME) or o.startswith(("karar",) + _ERTELEME_ADI) \
                    or (sonraki_zaman and not w.startswith(_SONRA_IS_KOKU)):
                return True                                    # tur 18: "kontrol edelim", "… sonra seçelim"
            continue
        if w.startswith(_BIZ_ERTELEME_KOKU) or (w.startswith(("ed", "yap", "eyle")) and o.startswith(_ERTELEME_ADI)):
            return True
    return False
# tur 16 (O-C): "içeriden/dışarıdan bakınca", "içeri girince" bakışın yeridir
_DIS_IC = ("iceri", "disari", "iceriye", "disariya", "iceriden", "disaridan")
# tur 16 (O-G): yer sözünün önünde yalnız yerin parçası ya da dolgu olabilir ("yatak odasına", "lütfen kapıdan"); özne ya da zaman ("usta
# eve", "akşam eve", "hanım evine", "malzeme eve") seçimin zamanıdır
_YER_ONEKI = {"yatak", "oturma", "misafir", "cocuk", "ebeveyn", "calisma", "ana", "on", "arka", "ic", "dis", "buyuk", "kucuk", "ilk",
              "son", "sag", "sol", "ust", "alt", "bu", "su", "o", "lutfen", "ayrica", "bir", "de", "da", "ve", "peki", "ama"}
# tur 12 (Y-2, O-4), tur 13 (Orta-4): emirle biten zaman bağı yalnız bizim işimizin zamanıysa o emrin zamanıdır: öznesiz ya da işimizi
# anan "bitince", "tamamlanınca", "hazırlanınca", "çizince" ("çizim bitince gönderin"), öznesiz ya da işimizi anan "hazır/müsait
# olunca" ("hazır olunca haber verin"), "vaktiniz olunca", "sıra gelince". Müşterinin, paranın ya da işin öteki tarafının zamanı
# ("netleşince", "kapora yatınca", "ödeme bitince", "sözleşme tamamlanınca", "kapora hazır olunca", "inşaat bitince") seçimin zamanıdır
_IS_SOZU = {"cizim", "cizimi", "cizimler", "cizimleri", "plan", "plani", "proje", "projesi", "pdf", "teklif", "teklifi", "gorsel",
            "gorseli", "dosya", "dosyasi", "is", "isiniz", "isimiz", "siz", "sizin"}
# müşterinin kararı dışında seçimi bağlayabilen konu (para, belge, iş yeri): bu sözü anan koşul ve zaman istekte de seçimin olabilir
_BAGLI_KONU = ("kapora", "avans", "odeme", "kredi", "sozlesme", "fiyat", "stok", "banka", "butce", "imza", "evrak", "insaat",
               "arsa", "ruhsat", "izin", "maas", "taksit", "pesinat", "senet", "nakit", "tapu", "havale", "tutar")
_PARA_SOZU = {"para", "parasi", "parayi", "parasini", "paramiz", "paraniz", "paramizi", "paranizi", "paralar", "paralari", "parayla",
              "paranin", "paraya", "parada", "paradan", "parasal"}   # tur 14: "paravan" değil
_HABER_SOZU = re.compile(r"haber\s+ver\w*|bildir\w*")
_ZAMAN_BAGI = re.compile(_ZAMAN_BAGI_DESEN)
# hakem tur 9 (D-1): emir kipi ("haber verin", "bize bildirin") bayinin bizden istediğidir, erteleme değildir
_HABER_EMRI = re.compile(r"haber\s+verin(?:iz)?|bildirin(?:iz)?")
# hakem tur 9 (Y-4): koşul kipi ("onaylarsa", "olursa", "isterse", "uygunsa", "iyiyse"): seçim koşula bağlıdır, sorulur
# tur 11 (Y-2, Y-3): koşul eki ünsüzden sonra "-sa/-se" her sözde koşuldur ("stok varsa", "fiyat makulse", "düşükse", "kabul etmişse");
# "-sa/-se" ile biten ad ("Bursa", "terse", "Ayşe") koşul değildir (`_KOSUL_DISI`). "varsa" ardından cümle bize bir emirle biterse
# ("sorun varsa arayın", "yer varsa banyoya pencere ekleyin") o emrin koşuludur, çatının değil (`_kosul_var`)
_KOSUL_SOZU = re.compile(r"\w+[bcdfghjklmnprstvyz]s[ae]|\w+rs(?:eniz|aniz|ek|ak|en|an)|\w+m[ae]zs(?:ak|ek|am|em|an|en|aniz|eniz)")
_KOSUL_DISI = {"bursa", "terse", "ayse", "arsa", "dansa", "kursa", "pense", "elsa", "salsa",
               "neyse", "oyleyse", "boyleyse", "fransa"}                 # tur 12 (O-1, D): "Neyse 2 olsun", "Öyleyse 2 olsun", "Fransa'da"
# tur 12 (O-5): "varsa" + emir yalnız sorun sözüyle emrin koşuludur ("sorun varsa arayın"); "stok varsa gönderin", "imkan varsa çizin",
# "müşteri onayı varsa çizin" seçimin koşuludur: sorulur
_VARSA_KONU = ("sorun", "problem", "soru", "eksik", "hata", "sikinti", "takil", "yanlis", "aksilik", "merak")
# tur 13 (Orta-3): planın bir yerini anan istekte yalnız bu koşullar isteğindir ("mümkünse yatak odası 2 penceresi …", "isterseniz …",
# "yer varsa banyoya pencere ekleyin"); "fiyatı uygunsa yatak odası …" seçimin koşulu da olabilir: sorulur
_ISTEK_KOSULU = {"mumkunse", "isterseniz", "istersen", "isterseydiniz"}
_ISTEK_VARSA = ("yer", "alan", "imkan", "olanak", "bosluk", "mesafe")
# tur 14 (Orta-1): istekteki koşuldan hemen sonra nezaket sözü gelirse ("… yapabilirseniz sevinirim", "… olursa iyi olur") koşul isteğin
# ricasıdır, seçimin koşulu değildir (cümle müşteriyi ya da parayı anmıyorsa)
_RICA_SOZU = ("sevinir", "memnun", "makbule", "minnettar")
# tur 15 (O-1): yalnız isteğin kendi fiili ("yap", "et", "ol", "koy" …) ve hemen önünde ölçü ya da planın bir yeri ("120x180 yapabilirseniz
# sevinirim", "120x180 olursa iyi olur"); "hanım beğenirse iyi olur", "patron kabul ederse", "ucuz olursa" seçimin koşuludur
_RICA_FIILI = ("yap", "ed", "ol", "koy", "cevir", "degistir", "ekle", "kaldir", "tasi", "buyut", "kucult", "genislet", "uzat", "kisalt",
               "ver", "yaz", "sec", "belirle", "ciz")            # tur 17 (O-B): "120x180 verirseniz seviniriz"
# tur 16: koşulla nezaket sözü arasındaki pekiştirme ("120x180 olursa çok iyi olur", "yaparsanız çok sevinirim", "yapabilirseniz bizi
# memnun edersiniz") atlanır
_RICA_ARASI = ("cok", "pek", "gercekten", "cidden", "bizi", "beni", "bizleri", "hepimizi", "daha")
# tur 16 (O-H): olumsuz koşul ("olmazsa", "yapmasanız") ve olumsuz nezaket ("memnun olmayız", "iyi olmaz") rica değildir
_RICA_OLUMSUZ = ("olmaz", "olmay", "kalmaz", "kalmay", "degil")
# tur 13 (Orta-2): "-rsen/-rsan" ile biten fiil (koşul) adla karışmaz; ad sayılmaz
_FIIL_RSEN = ("ister", "eder", "der", "olur", "secer", "bakar", "alir", "verir", "yapar", "gelir", "onaylar", "begenir", "kalir",
              "gorur", "bulur", "sorar", "dusunur", "uyar", "kabul")
# tur 12 (Y-1, Y-3): onay kökünün olumsuz biçimi ("onaylamadı", "onaylayamadık", "onaylatmadık", "onaylatamadık", "onaylanamaz"; "-mış",
# "-mak" değil) ve onay sözünden sonra üç söz içinde "yok", "değil" ya da olumsuz fiil ("onay yok", "onaylamak istemiyoruz", "onay
# vermedi", "onay alamadık") olumsuz onaydır; "onaylıyoruz, sorun yok" değildir (`_OLUMSUZ_DISI`)
# tur 12 (O-2): soru cümlesinde ilgi eki alan çatı ("2'nin fiyatı ne olacak?", "PA-06-K'nın teslimi", "2 numaranın montajı") sorunun
# konusudur, seçim sorusu değildir
# tur 13 (Yüksek-1): yalnız fiyat, teslim, süre, montaj gibi konu sözü izlerse; "2'nin çatısı mı olsa?", "2'nin mi olsun?" seçim
# sorusudur. Sorunun konusu olan çatı seçilen çatı değilse ("1 olsun, 2'nin fiyatı ne olacak?") iki okuma vardır: sorulur
# tur 14 (Orta-3): ilgi eki yalnız seçim sözü izlerse ("mı", "-ki", çatı, çatının adı, "olsa", "olsun", "seç", "tercih") seçim sorusudur;
# öteki ilgi eki sorunun konusudur ("2'nin rengi, eğimi, sacı, de fiyatı, toplam fiyatı ne olacak?"). Oda programı ("2+1'in fiyatı")
# çatı numarası değildir
_IYELIK = re.compile(r"(?:\S+?['’`´]\s*(?:n[ıiuü]n|[ıiuü]n|y[ıiuü]n)|\b\d+\s*(?:n[ıiuü]n|[ıiuü]n)|\b\d+\s+numara(?:n[ıi]n|s[ıi]n[ıi]n))"
                     r"(?!\s*(?:m[ıiuü]\b|ki\b|[çc]at|k[ıi]rma|be[şs]ik|cumba|kalkan|ol(?:s|ac|ur|ma)|se[çc]|tercih))",
                     re.IGNORECASE)
# tur 15 (Y-1), tur 16 (O-A): kıyas sorusunda ilgi ekinden sonra ad ve soru eki ("2'nin şekli mi daha iyi?") de kıyastır; yüklemli soruda
# ("2'nin rengi mi olacak?") sorunun konusudur
_IYELIK_KIYAS = re.compile(_IYELIK.pattern[:-2] + r"|\S+\s+m[ıiuü]\b))", re.IGNORECASE)
# tur 16 (O-A): birimli sayı ("teslim 3 hafta mı?", "montaj 3 gün mü?") setin numarası değildir
_BIRIM_KOKU = ("hafta", "gun", "yil", "sene", "saat", "dakika", "metre", "adet", "tane", "kat", "kisi", "lira", "bin", "milyon", "derece",
               "kilo", "oda", "pencere", "kapi", "banyo", "yatak", "ayda", "ayl", "aylik", "taksit", "tir", "parca", "parti", "sefer", "kez",
               "defa", "arac", "kamyon", "senet", "usta", "ekip", "isci", "milim", "mili", "salon", "tuvalet", "balkon", "teras",
               "kanat", "metrekare", "litre")
_BIRIM_SOZU = {"ay", "aya", "ayi", "ayin", "aydan", "m", "tl", "kg", "mt", "cm", "mm", "m2", "ton", "dk", "yuz", "wc", "lt"}
# tur 17: birim öneki başka sözü yutmaz ("katalog", "kışın"); sayı aralığı ("2-3 hafta", "2,5 ay", "2 ila 3 hafta") ve "iş günü" de birimlidir
_BIRIM_DISI = ("katalog", "katki", "katil", "kisin")
_ARALIK_SOZU = {"ila", "veya", "ya", "yada", "yahut", "ile", "ve"}


def _birimli(ws: list[str], i: int) -> bool:
    """`ws[i]` (sayı) bir birimle mi geliyor ("3 hafta", "2-3 hafta", "2,5 ay", "3 iş günü"; tur 16, O-A; tur 17)."""
    j = i + 1
    while j < len(ws) and j < i + 4 and (ws[j].isdigit() or ws[j] in _ARALIK_SOZU):
        j += 1
    x = ws[j] if j < len(ws) else ""
    if x == "is" and j + 1 < len(ws) and ws[j + 1].startswith("gun"):
        return True
    return x in _BIRIM_SOZU or (x.startswith(_BIRIM_KOKU) and not x.startswith(_BIRIM_DISI))
# tur 16 (Y-A): kıyas sorusunda sıra sözü ("ikincisi daha mı iyi?") çatı numarasıdır; "hangisi", "diğeri" seçimi açar
_SORU_SIRASI = re.compile(r"(ilk|birinci|ikinci|ucuncu|sonuncu)(?:s[iu]|i)?")
# tur 17 (Y-A', O-M): sorudaki setin zamiri ("hangisi olsun?", "en iyisi hangisi?", "hangisini önerirsiniz?", "ilki salona daha mı
# uygun?", "diğeri", "öbürü") ve çatıyı anan sıfat ("başka çatı", "diğer ikisi", "hangi çatı") seçimi açar: sorulur. Başka bir şeyin
# çoğulundan seçen zamir ("kapılardan hangisi") ve sıfat sıra sözü ("ilk taksit", "birinci kalite", "öteki evin teslimi") sorunun konusudur
_SET_ZAMIRI = re.compile(r"hangisi\w*|(?:ilk|birinci|ikinci|ucuncu|sonuncu)(?:s[iu]\w*|i|in|ini|ine|inden|nden|y[iuea]"
                         r"|n[iu]n|d[ea]n)|digeri\w*|digerleri\w*"
                         r"|oburu\w*|oburleri\w*|otekisi\w*|otekiler\w*|oteki(?:n\w*|ne|nde|nden)|baskasi\w*")
_SET_SIFATI = ("diger", "obur", "oteki", "baska", "hangi", "ilk", "birinci", "ikinci", "ucuncu", "son", "sonuncu")
_SET_ADI = ("cati", "ikisi", "ucu", "ikisinden", "ucunden", "secenek", "alternatif")
# tur 18 (Yüksek 1, Orta 1): zamir gibi kullanılan sıfat ("ikinci daha mı iyi?", "öteki daha mı iyi?", "ikinci de olur mu?", "ikinci numara",
# "ikinci olsa"): ardından kıyas, dolgu, yüklem ya da "numara" gelir
# tur 20 (Y1): sıfattan sonraki söz önekle okunur ("olabilir", "olursa", "tercihimiz", "numaraya"); istisna `_sira_sifati`
_SIFAT_ZAMIR_ONEK = ("daha", "numara", "olsa", "olsun", "olur", "olabil", "olacak", "olmas", "iyi", "guzel", "uygun", "mantik", "secenek",
                     "tercih", "sira", "yapil", "secil", "alin", "gecel", "nasil")   # tur 20 kalanı: "1 olsun, ikinci nasıl?"
# tur 19 (O3), tur 20 (Y1): sıra sözünden sonra sayma ve derece sözü ("ilk defa", "son derece", "son dakika", "ikinci kez")
# tur 21 (O5): "ilk önce", "ilk başta", "ilk hafta", "ilk gün", "ilk sorum", "ilk adım"; tam söz: "ilk ay", "ilk iş", "ikinci el"
_SIRA_DISI_ARDI = ("defa", "kez", "sefer", "derece", "dakika", "saniye", "kadar", "olarak", "hal", "elden", "agizdan",
                   "once", "basta", "bastan", "hafta", "gun", "yil", "sene", "soru", "adim")
_SIRA_DISI_TAM = {"ay", "ayi", "ayda", "is", "isi", "isimiz", "el", "eli", "islem", "islemi", "islemler", "islemimiz"}   # tur 22 (O6)
_SIFAT_FIIL = re.compile(r"\w+(?:[ae]c[ae]k|[ae]n|d[iu]g[iu]|t[iu]g[iu]|m[ae]s[iu])")   # tur 22 (O6): "yapılması gereken"
# tur 22 (Y1): sıfat-fiil, "nasıl" ve değer sözünden sonra "bir" + setin adı ("başka nasıl bir çatı", "ikinci seçilen bir çatı", "başka
# seçilecek bir seçenek") setin seçeneğidir
_SET_ADI_KOKU = ("cati", "secene", "alternatif", "opsiyon", "kirma", "besik", "cumba", "kalkan", "model", "tip", "marka", "cins", "cesit")


_GENEL_SET_ADI = ("model", "tip", "marka", "cins", "cesit", "opsiyon")


def _genel_ad_konulu(ad: str, ardi: list[str]) -> bool:
    """Genel set adı ("model", "tip", "marka", "opsiyon") ardından üç söz içinde çatı dışı konu geliyor mu ("nasıl bir marka boya",
    "nasıl bir opsiyon var ödemede"; tur 23, O8): o konunun adıdır."""
    return ad.startswith(_GENEL_SET_ADI) and any(_konu_adi(a) for a in ardi[:3])


def _sira_sifati(w: str, x: str, x2: str = "", x3: str = "", ardi: list[str] | None = None) -> bool:
    """Sıra sözü (`w`) ardındaki sözle (`x`, `x2`) sıfat mı (çatı numarası değil): çatı dışı konu ("ilk taksit", "birinci kalite", "ikinci
    kapı"), sayma ya da derece sözü ("ilk defa", "ikinci kez", "ilk önce", "ilk iş"), "ilk/son" + plan ("ilk planda", "son plan": zamanın
    planı), ya da sıfat-fiil ya da "nasıl" + belirsiz ad ya da konu ("başka yapılacak bir şey", "ilk yapılacak iş", "başka olması gereken",
    "başka nasıl ödeme"; tur 21, O6)."""
    if _konu_adi(x) or x.startswith(_SIRA_DISI_ARDI) or x in _SIRA_DISI_TAM or (w in ("ilk", "son") and x.startswith("plan")):
        return True
    return bool(_SIFAT_FIIL.fullmatch(x) or x.startswith(("nasil", "olmas", "uygun", "farkli"))) and bool(x2) and (
        (x2 in ("bir", "bi") and not (x3.startswith(_SET_ADI_KOKU) and not _genel_ad_konulu(x3, ardi or [])))
        or x2.startswith(("sey", "bisey", "gerek")) or x2 in _SIRA_DISI_TAM
        or _konu_adi(x2) or (x2.startswith(_SIRA_DISI_ARDI) and not x.startswith(("nasil", "olmas"))))   # tur 22: "başka uygun gün"


def _set_adina_varir(ws: list[str], i: int) -> bool:
    """`i`'deki sıra ya da set sıfatı sıfat-fiil, "nasıl", "farklı" ya da "bir" üstünden setin adına mı varıyor ("ikinci olan çatı",
    "başka nasıl bir çatı", "başka seçilecek bir seçenek"; tur 22, Y1)."""
    j = i + 1
    while j < len(ws) and j <= i + 3 and (ws[j] in ("bir", "bi") or _SIFAT_FIIL.fullmatch(ws[j])
                                          or ws[j].startswith(("nasil", "farkli", "degisik", "uygun"))):
        j += 1
    return i + 1 < j < len(ws) and ws[j].startswith(_SET_ADI_KOKU) and not _soru_konu_adi(ws[j + 1] if j + 1 < len(ws) else "") \
        and not _genel_ad_konulu(ws[j], ws[j + 1:])           # tur 23 (O8): "başka nasıl bir marka boya var?"


_SIFAT_ZAMIR_ARDI = {"daha", "de", "da", "en", "numara", "numarali", "numaradaki", "olsa", "olsun", "olur", "iyi", "iyidir", "guzel",
                     "uygun", "mantikli", "secenek", "secenegi", "tercih", "tercihi", "sira", "siradaki"}   # tur 19 (O3): tam söz
_KIYAS_ARDI = {"daha", "mi", "mu", "de", "da", "iyi", "guzel", "uygun", "olsun", "olsa", "olur", "en"}
# tur 18 (Orta 2): zamirden ya da sıfattan önce çatı dışı bir konu ("kapıların hangisi", "kapı rengi hangisi", "renk seçeneklerinden
# hangisi", "taksitlerin birincisi", "kapı için başka seçenek") sorunun konusudur; sıfattan sonra çatı ve konu ("hangi çatı malzemesi",
# "başka çatı rengi") da
_SORU_KONU_ADI = ("renk", "reng", "malzeme", "taksit", "odeme", "montaj", "nakliye", "teslim", "kaplama", "klima", "dolap", "boya",
                  "fiyat", "kapora", "sozlesme", "etap", "asama", "kalite", "sinif", "sac", "oluk", "olug", "vida", "ekip", "usta", "kat",
                  "model", "tip", "marka", "cins")


def _soru_konu_adi(w: str) -> bool:
    """Çatı dışı bir konunun adı mı (planın yeri ya da `_SORU_KONU_ADI`; tur 18, Orta 2)."""
    return bool(_yer_koku(w)) or (w.startswith(_SORU_KONU_ADI) and not w.startswith(("katalog", "katil", "katki", "tipki"))
                                  and w not in ("ustam", "ustacim", "ustamcim"))   # tur 24 (Y1): "ustam" hitaptır


# tur 19 (Y1): "model", "tip", "marka", "çeşit" setin seçeneğini de anar ("modellerden hangisi", "hangi tip daha iyi?")
_KONU_DISI_AD = ("model", "tip", "marka", "cins", "cesit", "tur")
_EKLI_AD = re.compile(r"\w+(?:n?[iu]n|d[ae]n|t[ae]n)")


def _konu_adi(w: str) -> bool:
    """Çatı dışı bir konunun adı mı (çatı, çatı adı, model ve tip sözü değil; tur 19)."""
    return _soru_konu_adi(w) and not w.startswith(("cati",) + _CATI_AD_KOKU + _KONU_DISI_AD)


# tur 19 ara gerileme: yalın konu adı ("Kapı hangisi olacak?", "Montaj ve nakliye hangisi önce?") konudur; "usta" hitaptır, "kat",
# "model", "tip" setin seçeneğini de anar
_YALIN_KONU = ("renk", "malzeme", "taksit", "odeme", "montaj", "nakliye", "teslim", "teslimat", "kaplama", "klima", "dolap", "boya",
               "fiyat", "kapora", "sozlesme", "etap", "asama", "kalite", "sinif", "sac", "oluk", "vida", "ekip")


def _yalin_konu(w: str) -> bool:
    """Ekisiz (yalnız çoğul ekli) çatı dışı konu adı mı ("kapı", "kapılar", "nakliye", "renkler")."""
    k = _yer_koku(w)
    if k:
        return w in (k, k + "lar", k + "ler")
    return w in _YALIN_KONU or (w.endswith(("lar", "ler")) and w[:-3] in _YALIN_KONU)


# tur 20 (Y2, O7): ölçüt sözü ve ölçüt adı ("fiyat açısından", "fiyat için hangi …") seçimin ölçütüdür, sorunun konusu değil
_OLCUT_SOZU = ("acisindan", "acidan", "bakimindan", "yonunden", "yonuyle", "olarak", "itibariyle")
_OLCUT_KOKU = ("fiyat", "maliyet", "butce", "montaj", "nakliye", "teslim", "kalite", "dayanik", "saglam", "yalitim", "isi", "ekonomi",
               "para", "sure", "zaman")
_OLCUT_SURECI = ("montaj", "nakliye", "teslim")   # tur 22 (O3): "montaj için başka seçenek var mı?" işin sorusu; "fiyat için" ölçüt


def _var_sorusu(ws: list[str], i: int) -> bool:
    """`i`'deki zamir ya da sıfattan sonra varlık sorusu, kıyas ve çatı sözü olmadan ("hangi seçenekler var?", "başka seçenek var mı?";
    tur 21, O7): konunun seçeneklerini sorar."""
    ardi = ws[i + 1:]
    return any(x in ("var", "varmi", "mevcut") for x in ardi) and not any(
        x.startswith(("daha", "en", "cati") + _CATI_AD_KOKU) or (x.startswith(_KIYAS_SIFATI) and x not in ("son", "ilk")) for x in ardi)


def _konu_oncesi(ws: list[str], i: int, sifat: bool = False) -> bool:
    """`i`'deki zamir ya da sıfat çatı dışı bir konunun mu (tur 18; tur 19, Y1): hemen önünde ilgi ya da ayrılma ekli konu ("kapıların
    hangisi", "kapılardan hangisi", "renk seçeneklerinden hangisi", "taksitlerin birincisi"), iyelikli konu ("kapı rengi hangisi") ya da
    sıfattan önce "X için" ("kapı için başka seçenek"); yalın konu adı ("Kapı hangisi olacak?"; kıyas sözü izlemedikçe, yer adında her
    zaman). Öteki söz ölçüttür, seçimi kapatmaz ("fiyat olarak hangisi", "fiyat hangisi daha uygun", "montaj için hangisi", "salona
    hangisi", "usta hangisi")."""
    o = ws[i - 1] if i > 0 else ""
    oo = ws[i - 2] if i > 1 else ""
    nx = ws[i + 1] if i + 1 < len(ws) else ""
    if not o or o[0].isdigit():
        return False
    if o in _OLCUT_SOZU:
        return _konu_adi(oo) and (not oo.startswith(_OLCUT_KOKU) or oo.startswith(_OLCUT_SURECI)) and _var_sorusu(ws, i)
        # tur 20 (O7): "fiyat açısından hangisi" ölçüttür; tur 21 (O7): "ödeme açısından hangi seçenekler var?" konunun sorusudur; tur 22
        # (O3): "fiyat açısından başka seçenek var mı?" ölçüttür, "montaj bakımından hangi seçenekler var?" işin sorusu
    if o == "icin":
        return sifat and _konu_adi(oo) and (not oo.startswith(_OLCUT_KOKU) or (oo.startswith(_OLCUT_SURECI) and _var_sorusu(ws, i))) \
            and not nx.startswith(("cati",) + _CATI_AD_KOKU + _KONU_DISI_AD)   # tur 20 (Y2): "fiyat için hangi çatı daha iyi?"; tur 21
                                                                               # (O7): "montaj için başka seçenek var mı?"
    if _EKLI_AD.fullmatch(o) and (_konu_adi(o) or _konu_adi(oo)):
        return True
    if not sifat and _yalin_konu(o):
        s = ws[i + 1] if i + 1 < len(ws) else ""
        return bool(_yer_koku(o)) or not (s.startswith(("daha", "en")) or s.startswith(_KIYAS_SIFATI) or s in ("mantikli", "makul"))
    return _konu_adi(o) and bool(re.fullmatch(r"\w+s?[iu]", o)) and _konu_adi(oo)   # "kapı rengi hangisi"


# tur 19 (Y2): ayrık soruda konum ("soldaki mi sağdaki mi"), gösterme ("bu mu o mu"), kıyas ("ucuz mu pahalı mı") ve sayı sözü setin
# seçeneklerini anar
_AYRIK_SET_SOZU = {"bu", "su", "o", "bunu", "sunu", "onu", "bunlar", "sunlar", "onlar", "biri", "birisi", "obur", "oteki", "diger"}
_KIYAS_SIFATI = ("ikisi", "ucuz", "pahali", "duz", "egim", "dik", "yatik", "iyi", "guzel", "uygun", "buyuk", "kucuk", "yuksek", "alcak", "genis", "dar", "kisa", "uzun", "sade",
                                  "sik", "modern", "klasik", "hafif", "agir", "saglam", "basit", "yeni", "eski", "ilk", "son",
                                  # tur 20 (O7): "montaj hangisi kolay?", "sivri mi basık mı?", "saçaklı mı saçaksız mı?"
                                  "kolay", "zor", "hesapli", "dayanik", "hizli", "yavas", "sivri", "basik", "sacak", "sicak", "serin",
                                  "ekonomik", "kaliteli", "pratik")
# tur 20 (düşük): ayrık soruda bulunma ekli konum sözü setin seçeneğidir ("solda mı sağda mı"); "salonda mı mutfakta mı" değil
_SIRA_KOKU = ("birinci", "ikinci", "ucuncu", "dorduncu", "sonuncu")
_KONUM_DA = {"solda", "sagda", "ortada", "sonda", "basta", "ilkte", "onde", "arkada", "ustte", "altta", "yanda"}


def _ayrik_secenek(ws: list[str], set_sozu) -> bool:
    """Soruda çatı dışı iki seçenek ayrık soruyla sayılıyor mu ("PVC mi alüminyum mu?"; tur 18 kalanı): "hangisi" onlardandır. Konum,
    gösterme, kıyas, sıra ve sayı sözü ("soldaki mi sağdaki mi", "bu mu o mu", "ucuz mu pahalı mı") setin seçeneğidir (tur 19, Y2)."""
    def setin(w):
        return set_sozu(w) or w[:1].isdigit() or w in _AYRIK_SET_SOZU or w.startswith(_KIYAS_SIFATI + _SIRA_KOKU) \
            or w.endswith(("daki", "deki", "taki", "teki")) or w in _KONUM_DA or w in ("yazin", "kisin") \
            or (w.endswith(("da", "de", "ta", "te")) and not _yer_koku(w) and not _soru_konu_adi(w)) \
            or bool(_SET_ZAMIRI.fullmatch(w)) or w in _SET_SIFATI
    for i in range(len(ws) - 3):
        a, m1, b, m2 = ws[i:i + 4]
        if not (_SORU_EKI.fullmatch(m1) and _SORU_EKI.fullmatch(m2)) or _SORU_EKI.fullmatch(a) or _SORU_EKI.fullmatch(b):
            continue
        konulu = i + 4 < len(ws) and _konu_adi(ws[i + 4]) and all(
            x.endswith(("da", "de", "ta", "te")) and not set_sozu(x) and not x.startswith(_KIYAS_SIFATI + _SIRA_KOKU) for x in (a, b))
        if konulu or (not setin(a) and not setin(b)):
            return True                                        # tur 22 (O7): "kasımda mı aralıkta mı teslim?"
    return False


def _set_zamiri(ws: list[str]) -> bool:
    """Soru cümlesi setin bir seçeneğini zamirle ya da çatı sıfatıyla mı anıyor (tur 17, Y-A', O-M; tur 18). Zamirden ya da sıfattan
    önce çatı dışı bir konunun adı geçiyorsa o konunun sorusudur."""
    for i, w in enumerate(ws):
        x = ws[i + 1] if i + 1 < len(ws) else ""
        x2 = ws[i + 2] if i + 2 < len(ws) else ""
        zamir = bool(_SET_ZAMIRI.fullmatch(w)) and x != "kadar"                     # tur 19 (O3): "ikinciye kadar"
        sifat = w in _SET_SIFATI and (
            (x.startswith(_SET_ADI + _CATI_AD_KOKU) and not _soru_konu_adi(x2))      # "başka çatı" ("başka çatı rengi" değil)
            or (x.startswith(_KONU_DISI_AD) and w != "son" and not _konu_adi(x2))    # tur 19 (Y1), tur 20 (Y2): "hangi tip daha iyi?",
                                                                                     # "hangi modeli seçelim?" ("hangi model kapı", "son
                                                                                     # model mi?" değil)
            or (x.startswith("plan") and w not in ("ilk", "son"))                    # "ikinci planı da gönderir misiniz?" ("son plan bu mu?" değil)
            or not x or bool(_SORU_EKI.fullmatch(x))
            or (x in ("de", "da", "en") and not x2.startswith(("bir", "bi", "sey", "bisey", "ne")))    # "başka da bir şey lazım mı?" değil
            or (x.startswith(_SIFAT_ZAMIR_ONEK) and not _sira_sifati(w, x, x2, ws[i + 3] if i + 3 < len(ws) else "", ws[i + 4:]))
            or x == "icin"                                                           # tur 21 (Y3): "ikinci için fiyat ne olur?"
            or _set_adina_varir(ws, i))                                              # tur 22 (Y1): "başka nasıl bir çatı olabilir?"
        if not (zamir or sifat):
            continue
        if _konu_oncesi(ws, i, sifat=sifat and not zamir):
            continue                                           # "kapıların hangisi", "kapı için başka seçenek", "taksitlerin birincisi"
        return True
    return False


def _soru_numaralari(ws: list[str], numaralar: dict, harfler: dict) -> set[str]:
    """Soru cümlesindeki setin numarası ve harfi; birimli sayı değil (tur 16, O-A)."""
    son = set()
    for i, w in enumerate(ws):
        if (w in numaralar and _birimli(ws, i)) or not (numaralar.get(w) or harfler.get(w)):
            continue
        son.add(numaralar.get(w) or harfler.get(w))
    return son
_ODA_PROGRAMI = re.compile(r"\d\s*\+\s*\d")
_ODA_BOSLUGU = re.compile(r"(\d)\s*\+\s*(\d)")
_ODA_PROGRAMI_SOZ = re.compile(r"\d\+\d\S*")
# tur 15 (Y-1): seçimi karşılaştıran soru ("1 olsun. 2 mi daha iyi?", "K mı daha iyi?", "2'nin şekli mi daha iyi?"): soru eki ya da "daha"
_SORU_EKI = re.compile(r"m[iu](?:dir|dur|ydi|ydu|yiz|yuz|sin|sun|siniz|sunuz)?")
# tur 13 (Yüksek-2): "-maktan/-makta" ("onaylamaktan vazgeçtik", "onaylamakta tereddüt ediyoruz") da; "onaylamaktayız" değil
_ONAY_OLUMSUZ = re.compile(r"(?!onayla(?:t|n)?maya$)onayla(?:t|n|s)?(?:y?a)?m(?!is|ak|ek)\w*"   # "onaylamaya hazırız" değil
                           r"|onayla(?:t|n)?mak(?:tan|ta(?!y[iı][mz]|dir))\w*")
_OLUMSUZ_FIIL = re.compile(r"\w+?m[ae](?:d[iu]|y[aei](?!n)|m[iu]s)\w*|\w+?m[iu]yor\w*|\w+?m[ae]z|\w*[^a\W]m[ae]m")   # "vermez", "veremem"
_CEKINCE_KOKU = ("vazgec", "tereddut", "cekin", "zorlan", "zor", "erken", "imkansiz")
_OLUMSUZ_DISI = ("sorun", "problem", "soru", "itiraz", "sikinti", "mahzur", "engel", "degisiklik", "eksik", "hata", "isteg", "istek",
                 "talep", "baska", "diyecek", "diyece", "soyleyece", "isteyece", "sey", "ek")
# tur 14: `_OLUMSUZ_DISI` yalnız yokluk bildiren olumsuzla ("sorun yok", "sorun olmaz", "değişiklik istemiyoruz") onayı olumsuzlamaz;
# "onay sorunu çözülmedi" olumsuz onaydır. "onaylamak zorundayız", "onaylıyoruz erkenden gönderin" çekince değildir
_YOKLUK_SOZU = ("yok", "olmaz", "olmay", "olmad", "istemiy", "istemey", "istemez", "gerekmiy", "gerekmez", "cikmad", "cikmaz", "yasamad",
                "yasamay", "degil")
_CEKINCE_DISI = ("zorunda", "erkenden", "zorunlu")   # tur 23 (O2): "zorunlu olarak pencere eklensin"
# hakem tur 10 (Y-1), tur 11 (O-1): onay kökünün yalnız olumsuz ("onaylamadı"), gelecek ("onaylayacak"), zaman ("onaylayınca", "onayından sonra") ve koşul
# ("onaylarsa") biçimleri ile "onay alalım", "onayını bekliyoruz", "onayı gelince" ertelenmiş onaydır; öteki biçimler onaydır
# ("onayımızdır", "onayımızı veriyoruz", "onaylanmış"; tur 10'un onay listesi bunları soruyordu)
_ONAY_ERTELEME = re.compile(r"\bonay\w*\s+(?:sonra|once|al(?:alim|acagiz|iriz|ip|in|sin|inca)|bekl\w*|gel\w*|cik\w*)\b")
# tur 10 (O-3): istekte "ikisi"yi pencere yapan ölçü ("120x180"); başka rakam ("3 gün içinde") değil
_OLCU_DESENI = re.compile(r"\d+\s*[x×*/]\s*\d+")
# tur 10 (O-2): devrik sayıdan önce bu kökler gelirse sayı o şeyindir ("pencere 1 olsun", "kapı 3 olsun", "yükseklik 3 olsun")
_EV_ADI_EK = ("yuksek", "kat", "boy", "genis", "derin", "sayi", "adet", "tane", "olcu", "kalin", "kanat", "kapi", "pencere")
_EV_ADI_DISI = ("katalog", "katil", "boya")                    # tur 11 (O-3): "katalogdaki 3 olsun", "Katılıyorum 2 olsun" çatı numarasıdır
# tur 11 (O-2): "bekliyoruz" yalnız müşterinin kararını beklerken ertelemedir ("müşterinin cevabını bekliyoruz"; "teklifi bekliyoruz" değil)
_KARAR_KONU = ("musteri", "karar", "cevap", "yanit", "donus", "fikir", "onay", "esi", "esinin", "sahib")
_BEKLEME_KONU = _KARAR_KONU + ("haber",)
# hakem tur 9 (O-1): istekte "ikisi" bu köklerle gelirse oda ya da pencere sayısıdır
# hakem tur 9 (D-2 eşi): sayıdan sonra seçim fiili ("Biz de 2 diyoruz", "müşteri 2 dedi", "2'yi seçtik") çatı numarasına atıftır
_SECIM_FIILI = ("diyor", "dedi", "dedik", "secti", "secelim", "seciyor", "tercih", "istiyor", "istedi")
_SAYI_EKI = {"yi", "i", "u", "yu", "ni", "nu"}                 # "2'yi seçtik" → "2 yi sectik"
_ODA_PENCERE_KOKU = ("pencere", "kapi", "oda", "yatak", "banyo", "mutfak", "salon", "wc", "duvar", "vasistas")
# tur 15 (O-2, O-5): planın yeri olan sözler (ölçü, metre değil); "mutfağa" için "mutfa"
_YER_KOKU = _ODA_PENCERE_KOKU + ("mutfa", "veranda", "balkon", "teras", "giris", "antre", "koridor", "tuvalet", "lavabo", "kiler", "hol",
                                 "merdiven")


def _yer_koku(w: str) -> str | None:
    """Planın yeri olan sözün kökü (`_YER_KOKU`). Tur 16 (O-E, O-G): "Hollanda" ("hol" yalnız ekiyle), "kapıcı", "mutfakçı", "banyocu" yer
    değildir."""
    k = next((k for k in _YER_KOKU if w.startswith(k)), None)
    if k is None or (k == "hol" and w[3:] not in ("", "e", "de", "den", "da", "dan", "u", "un", "deki", "a")):
        return None
    return None if re.match(re.escape(k) + r"[a-z]{0,2}c[iu]", w) else k
# tur 12 (O-1, O-3): koşul ve zaman sözü yalnız planın bir yerini anan istekte ("mümkünse yatak odası 2 penceresi 120x180 olsun", "kapıdan
# girildiğinde solda kalsın", "yer varsa banyoya pencere ekleyin") o isteğindir; öteki cümlede ("stok varsa gönderin", "itiraz yoksa
# gönderin", "kapora yatınca gönderin") seçimindir
_PLAN_ICERIK_KOKU = _ODA_PENCERE_KOKU + ("veranda", "balkon", "teras", "giris", "antre", "koridor", "tuvalet", "lavabo", "kiler", "bolme",
                                         "olcu", "metre", "cm")
_HABER_KONU = ("montaj", "teslim", "tarih", "fiyat", "odeme", "nakliye", "adres", "sevk", "kargo", "randevu", "kesif", "kapora", "avans",
               "zemin", "arsa")
# hakem tur 7 (O1): ikisini, ucuzu ya da pahalıyı anan söz istek cümlesi dışında seçimi bize bırakır ya da seçimle çelişir ("1 olsun, daha
# ucuz olsun", "1 olsun, ikisi de olsun"): seçim kaydedilmez, sorulur. Tur 8 (O4): istek cümlesinde "ikisi" ("2 olsun, ikisinden biri";
# fiyat sözü yoksa) ve soru biçimli devir ("1 olsun, hangisi ucuzsa", "hangisi uygunsa") de
_KARARSIZ_KOKU = ("ikisi", "ucuz", "pahali")
# tur 14 (Yüksek-1): seçimle gelen kararsızlık sözü ("1 olsun, bilemedik", "karar veremedik", "emin değiliz", "kararsızız") seçimi
# olumsuzlar: sorulur. "emin" ardından iki söz içinde "değil" ya da olumsuz fiil ("emin olamadık"); "karar" ardından "değil" ya da karar
# vermenin olumsuzu ("karar vermedik", "karara varamadık"). Tur 15 (O-5): "kararımız değişmez", "kararsızlık yok" kesinliktir; çatı
# sözü olmadan odayı, kapıyı ya da pencereyi anan kararsızlık ("iç kapı modelinde kararsızız") o konunundur
_KARAR_FIILI = ("ver", "kil", "var", "al", "netles", "kesinles", "ol")
_KARARSIZLIK_KOKU = ("bilemed", "bilemiy", "bilmiyor", "veremed", "veremiy", "kararsiz", "secemed", "secemiy", "netlestiremed",
                     "netlesemed", "anlasamad", "anlasamiy")
# soru cümlesinde fiyat, teslim ve süre sorusu planın isteği değildir ("1 olsun, fiyatı ne olur?"): cevabın sonuna "Fiyat, süre ve teslim
# bilgisi teklifle gelir." eklenir (`karar_ver`; hakem tur 4, D-E). Önek yalnız konu sözlerinde ("paravan olur mu?" fiyat sorusu değildir).
_SORU_KONU_KOKU = ("fiyat", "ucret", "tutar", "teslim", "nakliye", "odeme", "kdv", "pahali", "ucuz", "maliyet")
_SORU_KONU = {"para", "parasi", "sure", "suresi", "termin"}
_SORU_DOLGU = {"kadar", "zaman", "olur", "gun", "gunde", "hafta", "haftada", "ay", "dahil", "toplam", "olacak", "verir", "verirsiniz"}
FIYAT_SORUSU_CEVABI = "Fiyat, süre ve teslim bilgisi teklifle gelir."


def _soru_konusu(w: str) -> bool:
    return w.startswith(_SORU_KONU_KOKU) or w in _SORU_KONU


# başka bir şey isteyen söz ("bir de başka model gönderin"): çatı sözü olmayan cümlede seçim değil, istektir (hakem tur 4, O-C)
_BASKA_SOZU = {"baska", "farkli", "diger", "yeni", "ekstra"}          # "ayrıca" bağlaçtır ("ayrıca teşekkürler"; hakem tur 5, O2)
# evin kendi kat ve yapı sözü ("tek katlı prefabrik, 1 olsun") talebin bilgisidir; öteki kat ve yapı sözü istektir (hakem tur 4, B2)
_TEK_KAT_SOZU = re.compile(r"\b(?:tek|1)\s*kat(?:l[ıi])?\b(?!\s*(?:daha|ekle|ilave|[çc][ıi]k))", re.IGNORECASE)   # "1 kat daha" değil
_KAT_EKLE_SOZU = re.compile(r"\b(?:1|bir)\s*kat\s*(?:daha|ekle\w*|ilave\w*|[çc][ıi]k\w*)|\b(?:[üu]st\s*kat|kat\s*ilave\w*|kat\s*ekle\w*)",
                            re.IGNORECASE)                     # hakem tur 5: "üstüne 1 kat daha", "kat ilavesi" kat sayısını artırır
_COK_KAT_SOZU = re.compile(r"\b(?:([2-4])|(iki|üç|uc|çift|cift))\s*katl[ıi]\b|\bdubleks\b|\btripleks\b", re.IGNORECASE)
_KAT_DISI = re.compile(r"yal[ıi]t|izol|\bcam|boya|\bsac|kaplama|al[çc][ıi]pan|osb|panel|membran|kar[ıi]?ton|kontrplak", re.IGNORECASE)
_YAPI_SOZU = {"celik": re.compile(r"\b[çc]elik\b", re.IGNORECASE), "prefabrik": re.compile(r"\bprefabrik\b", re.IGNORECASE)}
_TALEP_OLUMSUZ = re.compile(r"olmas[ıi]n|olmayacak|olmamal[ıi]|istem(?:iyor|eyiz|ez)|de[gğ]il|vazge[çc]", re.IGNORECASE)   # "2 katlı olmasın"
_YAPI_DISI = re.compile(r"\b(?:kap[ıi]|pencere|do[gğ]rama|kolon|kiri[sş]|profil|[çc]atı|[çc]ati)", re.IGNORECASE)


def _set_etiketleri(taban: dict, st: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Açık çatı setinin etiket harfleri ("k" → PA06K, "l" → Ç8801L) ve numaraları ("2" → PA06K)."""
    tk = str((taban or {}).get("kod") or "").upper()
    kodlar = [str(a.get("kod") or "").upper() for a in st.get("adaylar") or []]
    harfler = {c[len(tk):].lower(): c for c in kodlar if tk and c != tk and c.startswith(tk) and len(c) == len(tk) + 1}
    numaralar = {str(a.get("sira")): str(a.get("kod") or "").upper() for a in st.get("adaylar") or [] if a.get("sira") is not None}
    return harfler, numaralar


def _secim_sozcugu(w: str, adlar: set[str], harfler: set[str] | None = None, n: int = 9) -> bool:
    """Çatı setinde seçim ya da dolgu sözcüğü. Tek rakam yalnız setin numarasıdır ("85 değil 95 olsun" istektir, hakem tur 4; "5 numaralı
    modele geçelim" üç çatılı sette istektir, hakem tur 5); tek harf yalnız setin etiketi ya da ektir (`harfler`; "L tipi olsun" PA-06'da
    istektir)."""
    if len(w) == 1 and not w.isdigit():
        return harfler is None or w in harfler or w in _CATI_EKLERI
    return (w in _CATI_BAGLAM or w in _NUMARA or w in _SIRA_SOZU or w in ("son", "sonuncu") or w in _KALSIN_BAGLAM or w in _SELAM
            or w in _KOD_DOLGU or w in _CATI_EKLERI or w in _SORU_SOZU or w in _SECIM_DOLGU or w in _DEVIR_SOZU or w in _SECIM_NEZAKET
            or w in adlar
            or (w.isdigit() and 1 <= int(w) <= n) or w.startswith(_SECIM_KOKU))


def _talep_sozu_cikar(h: str, kendi_yapi: str) -> str:
    """Çatı setindeki cümleden talebin bilgisi çıkar (küçük harfle): evin m²'si, oda programı ve dış ölçüsü (değiştiyse
    `_cati_adiminda_talep_degisti` okur, aynıysa "85 m2 2+1 olsun" istek değildir; oda, veranda ya da arsa m²'si içerik kalır), "tek
    katlı", evin kendi yapı türü ve nezaket kalıbı. Soru cümlesindeki m², oda ve ölçü sorudur ("100 m2 olur mu?"): içerik kalır."""
    def ev_olcusu(m: re.Match) -> str:                         # evin dış ölçüsü (3–30 m); pencere ölçüsü ("120x120") içeriktir
        a, b = (float(x.replace(",", ".")) for x in m.groups())
        return " " if 3 <= a <= 30 and 3 <= b <= 30 else m.group(0)
    q = h.lower()
    h2 = q if _soru_cumlesi(h) else _OLCU_SOZU.sub(ev_olcusu, _ODA_SOZU.sub(" ", _M2_SOZU.sub(
        lambda m: " " if _ev_m2_mi(q, m) else m.group(0), q)))
    return _NEZAKET_SOZU.sub(" ", _YAPI_SOZU[kendi_yapi].sub(" ", _TEK_KAT_SOZU.sub(" ", h2)))


_SAYI_ARALIGI = re.compile(r"\b(\d+)\s*(?:[-–,]|\bila\b|\bveya\b|\bya\s+da\b|\byahut\b)\s*\d+\b", re.IGNORECASE)


_KARAR_BILDIRIMI = re.compile(r"ver(?:ebil)?(?:dik|dim|di|iyoruz|iyorum|mis\w*)|kararlastirdik|netlestirdik|netlesti|kesinlesti"
                              r"|kesinlestirdik|aldik|verildi|kesin(?:dir|tir)?|net(?:tir|iz)?|belli(?:dir)?|degismez|degismeyecek")
# vedalaşma ("sonra görüşürüz", "görüşmek üzere") istek de erteleme de değildir
_VEDA_SOZU = {"sonra", "gorusuruz", "gorusmek", "uzere", "kolay", "gelsin", "iyi", "calismalar", "hayirli", "isler", "tesekkurler",
              "tesekkur", "ederiz", "ederim", "saygilar", "saygilarimla", "selamlar", "simdilik", "hoscakalin", "yine", "tekrar",
              "yarin", "haftaya", "aksam", "sabah", "aksamlar", "geceler", "gunler", "pazartesi", "sali", "carsamba", "persembe", "cuma",
              "cumartesi", "pazar", "bayramda", "insallah", "o", "zaman", "hadi", "haydi", "peki"}   # tur 19 (O1): "yarın görüşürüz"


def _veda(sozler: list[str]) -> bool:
    """Cümle vedalaşma mı ("sonra görüşürüz", "görüşmek üzere, kolay gelsin")."""
    return any(w in ("gorusuruz", "gorusmek") for w in sozler) and all(w in _VEDA_SOZU for w in sozler)
_KARAR_BILDIRIM_DOLGU = {"sonunda", "nihayet", "artik", "biz", "musteriyle", "musterimizle", "musteri", "ile", "birlikte", "beraber",
                         "de", "da", "olarak", "kesin", "son", "ve", "hep", "esimle", "ailecek", "ortak", "bugun", "simdi", "tamam",
                         "evet", "nihai", "boylece", "iste", "en", "sonunda"}


def _karar_bildirimi(sozler: list[str]) -> bool:
    """Cümle yalnız kararın verildiğini mi söylüyor (tur 18 kalanı, Orta 3): "Kararımızı verebildik sonunda", "kararı veriyoruz",
    "kararımızı müşteriyle birlikte verdik". İstek ya da bilgi değildir; seçimin yanında dolgudur."""
    return any(w.startswith("karar") and not w.startswith("kararsiz") for w in sozler) \
        and any(_KARAR_BILDIRIMI.fullmatch(w) for w in sozler) \
        and all((w.startswith("karar") and not w.startswith("kararsiz")) or _KARAR_BILDIRIMI.fullmatch(w) or w in _KARAR_BILDIRIM_DOLGU
                for w in sozler)


def _cati_icerik_cumleleri(metin: str | None, katalog: Katalog, taban: dict, st: dict, fiyat_sorulari: list | None = None) -> list[str]:
    """İE-42 (hakem tur 3, Y1): çatı setinde bu mesajın çatı seçimi dışındaki cümleleri, bayinin kendi sözünden (K18). LLM'in alanlarına
    bakılmaz: LLM bağlamdan değer yineler ("tamam" → kartın 87 m²'si, eski pencere), sözsüz isteği de hiç yazmayabilir ("kapılar ahşap
    olsun", "çatı kaplaması kiremit olsun"). Cümle yalnız setin kodları, etiket harfi, numara ya da sıra sözü, çatı ve seçim sözcükleri,
    setteki çatıların adları, onay, selam, teşekkür ve soru sözcüklerinden kurulmuşsa seçimdir ya da dolgudur ("PA-06-K nasıl bir çatı?",
    "teşekkürler"). Öteki her cümle istek ya da bilgidir: pencere, yükseklik, kapı, kaplama, renk, müşteri, fiyat sorusu, başka evin kodu.
    Bu cümleler varsa evin kendi çatısı seçilse de onay o an kaydedilmez (istek sessizce düşmez; Lokman, 13 Ekim). Hakem tur 4: evin kendi
    kat ve yapı sözü bilgidir ("tek katlı", çelik evde "çelik"), öteki ("2 katlı", prefabrikte "çelik") istektir; "başka", "farklı" çatı
    sözü olmayan cümlede istektir; yalnız fiyat, süre ve teslim soran soru cümlesi `fiyat_sorulari`'na yazılır (cevabı teklif verir)."""
    tk = Katalog.taban_kod(taban.get("kod"))
    kendi_yapi = "celik" if str(tk or "").upper().startswith(("Ç", "C")) else "prefabrik"
    harfler, numaralar = _set_etiketleri(taban, st)
    adlar: set[str] = set()                                    # setteki çatıların adları ("kalkan önde"); oda adı ("salonda cumba") yalnız
    oda_adlari: set[str] = set()                               # çatı sözüyle aynı cümlede ("salonda pencere" istektir)
    for x in st.get("adaylar") or []:
        a = katalog.aday(x.get("kod"))
        for w in CO.norm(_cati_adi(a) if a else "").split():
            (oda_adlari if _alan_disi(w) or _alan_disi(_cati_govdesi(w)) else adlar).add(w)
    out = []
    for h in _cumleler(metin):
        h2 = _talep_sozu_cikar(h, kendi_yapi)
        soru = _soru_cumlesi(h)
        if soru:                                               # tur 17 (O-A): "teslim 2,5 ay mı?", "2 ila 3 hafta mı?" süre sorusudur
            h2 = _SAYI_ARALIGI.sub(r"\1", h2)
        sozler = CO.norm(h2).split()
        if not soru and (_karar_bildirimi(sozler) or _veda(sozler)):
            continue                                           # tur 18 kalanı: "Kararımızı verebildik sonunda, 1 olsun", "sonra görüşürüz"
        cati_sozu = any(w.startswith(("cati", "cumba", "kirma", "besik", "kalkan")) for w in sozler)
        izinli = adlar | (oda_adlari if cati_sozu else set())
        icerik, konu = False, False
        for _, soz, kod in _sozcukler(h2, katalog):
            if kod and Katalog.taban_kod(kod) == tk:
                continue                                       # bu evin ve setin kodu (başka evin kodu istektir)
            for w in CO.norm(soz).split():
                if soru and (_soru_konusu(w) or w in _SORU_DOLGU):
                    konu = konu or _soru_konusu(w)
                    continue
                if (w in _BASKA_SOZU and not cati_sozu) or not _secim_sozcugu(w, izinli, set(harfler), len(numaralar) or 9):
                    icerik = True
                    break
            if icerik:
                break
        if icerik:
            out.append(_cumle_temiz(h))
        elif konu and fiyat_sorulari is not None:
            fiyat_sorulari.append(_cumle_temiz(h))
    return out


# İE-42 (hakem tur 6, Y1; tur 7, Y3, Y4, D3): cümlenin yüklemi ("K olsun ama yatak odası 2 penceresi …"); soru eki ("K olsun mu?") sınır
# değildir. Yüklemden sonraki bağlaç atılır, hitap ve teşekkür ("K olsun eline sağlık …") yüklemin yanında kalır.
_YUKLEM = re.compile(r"\b(?:olsun|olsn|olcak|olacak|kals[ıi]n|kalacak)\b(?![ \t]*m[ıiuü]\b)", re.IGNORECASE)
_YUKLEM_SOZU = {"olsun", "olsn", "olcak", "olacak", "kalsin", "kalacak", "olmasin", "alinsin", "olmali"}
_ISTEK_FIILI = ("yap", "ekle", "eklen", "koy", "konul", "konsun", "konacak", "degis", "buyu", "kucul", "kaldir", "kalksin", "iste",
                "isti", "lazim", "gerek", "cikar", "tasi", "uzat", "kisalt", "genislet", "daralt")
_YUKLEM_BAGLACI = re.compile(r"[ \t]+(?:ama|fakat|ancak|ve|ayr[ıi]ca|bir[ \t]+de)\b", re.IGNORECASE)
_SIRA_NUMARASI = re.compile(r"\s*\d{1,2}\s*\.\s*")          # tek başına "2." parçası: numaralı liste ya da sıra sayısı


def _secim_sozleri(h: str, katalog: Katalog, taban: dict, st: dict) -> tuple[bool, list[str], dict, dict, dict]:
    """Cümlenin setteki kodu var mı ve kod dışındaki sözcükleri (sıra bağlamı süzülmüş), etiket harfleri, numaralar, sıra sözlüğü."""
    harfler, numaralar = _set_etiketleri(taban, st)
    set_kodlari = set(numaralar.values()) | {str(taban.get("kod") or "").upper()}
    kod = any(c in set_kodlari for c in _secim_kodlari(h, katalog))
    son_sira = str(max([int(a.get("sira") or 0) for a in st.get("adaylar") or []] or [0]))
    sira = {**_SIRA_SOZU, "son": son_sira, "sonuncu": son_sira}
    sozler = [w for _, soz, k in _sozcukler(h, katalog) if not k for w in CO.norm(soz).split()]
    return kod, _sira_baglami(sozler, sira), harfler, numaralar, sira


def _secim_belirteci(h: str, katalog: Katalog, taban: dict, st: dict) -> bool:
    """Cümlede çatıyı seçebilecek söz var mı: setin kodu, yalın numarası, etiket harfi ya da sıra sözü (eksiz: "ikinciye" değil; hakem
    tur 8), çatı sözü ya da evin kendi çatısı sözü."""
    kod, sozler, harfler, numaralar, sira = _secim_sozleri(h, katalog, taban, st)
    return kod or any(w in numaralar or w in harfler or w in sira or w.startswith("cati") for w in sozler) or _kendi_catisi_cumlesi(sozler)


def _eksiltili(h: str) -> bool:
    """Eksiltili devam ("2 de", "2'nin de", "ikinciye de", "3 de olsun", "ilki gibi"): önceki isteğin devamıdır, çatı seçimi değildir
    (hakem tur 8, Y1). Ayrı yazılan "de/da" bağlacına bakılır; "çatı da 2 olsun"daki "da" çatı sözünün eşliğidir, "K'da kalalım"daki ek
    bağlaç değildir; "olduğu gibi" eksiltili değildir."""
    sozler = [CO.norm(x) for x in (h or "").lower().split()]
    for i, w in enumerate(sozler):
        onceki = sozler[i - 1] if i > 0 else ""
        if w in ("de", "da") and i > 0 and not onceki.startswith("cati"):
            return True
        if w == "gibi" and re.fullmatch(r"\d+\w*|(?:ilk|birinci|ikinci|ucuncu|son)\w*", onceki.replace(" ", "")):
            return True
    return False


def _ozel_adlar(h: str) -> set[str]:
    """Cümlede kişi ya da yer adı olan sözler (tur 12, O-1): cümle başı dışında büyük harfle başlayan söz ("müşteri Nursen Kaya", "müşteri
    Fransa'da"; "-rsa/-rse", "-ysa/-yse", "-ssa/-sse" ile biten değil: "İsterse"), "müşteri"den sonraki "-rsen/-rsan" adı ("müşteri nursen
    kaya") ve "bey/hanım"dan önceki söz. Ad koşul eki taşımaz."""
    out: set[str] = set()
    for n, t in enumerate((h or "").split()):
        t = t.strip("\"'’`.,;:!?()")
        if n > 0 and t[:1].isupper():                         # tur 13 (Orta-2): "Fiyat Uygunsa", "İsterse" koşuldur, ad değil
            out.update(x for x in CO.norm(t).split() if _rsen_adi(x))
    w = CO.norm(h or "").split()
    for i, x in enumerate(w):
        if x.startswith("musteri"):
            out.update(y for y in w[i + 1:i + 3] if _rsen_adi(y))
        if x in ("bey", "hanim", "beye", "hanima", "beyin", "hanimin") and i > 0:
            out.add(w[i - 1])
    return out


def _rsen_adi(w: str) -> bool:
    """"-rsen/-rsan" ile biten ad mı ("nursen", "ersan"; "istersen", "olursan" fiildir)."""
    return bool(re.fullmatch(r"\w+rs[ae]n", w)) and not w.startswith(_FIIL_RSEN)


def _bagli_konu(sozler: list[str]) -> bool:
    """Cümle müşterinin kararını ya da seçimi bağlayabilen başka bir konuyu (kapora, ödeme, fiyat, stok …) anıyor mu."""
    return any(w.startswith(_KARAR_KONU + _BAGLI_KONU) or w in _PARA_SOZU for w in sozler)


# tur 17 (O-J): yer sözünün önünde yalnız özne ya da zaman betimi bozar ("usta eve", "akşam eve", "hanım evine", "malzeme eve", "biz eve");
# hitap, dolgu ve kapının türü ("abi", "yalnız", "sürgülü kapıdan", "evin girişinden", "2 numaralı kapıdan") bozmaz
_BETIM_OZNE_KOKU = ("usta", "ekip", "isci", "montajci", "musteri", "hanim", "patron", "bayi", "aksam", "sabah", "ogle", "yarin", "bugun",
                    "hafta", "sonra", "once", "malzeme", "kamyon", "arac", "tir", "nakliye", "sevkiyat", "teslim", "kargo", "kapora",
                    "odeme", "insaat", "mimar", "muhendis", "komsu", "misafirler", "cocuklar", "annem", "babam", "kayinvalide")
_BETIM_OZNE = {"biz", "siz", "onlar", "ben", "sen", "es", "esim", "esimiz", "kizim", "oglum", "gece", "gun", "ay", "yil", "mal",
               "bey", "hanimefendi", "beyefendi"}


# tur 18 (Orta 4): kapalı özne listesi her özneyi tutmuyor ("arkadaş", "cumartesi", "taşeron", "montaj ekibi"): yerin önünde yalnız yerin
# parçası, hitap, dolgu, evin ve kapının türü olabilir (izin listesi; tur 16 `_YER_ONEKI` + tur 17 O-J)
_BETIM_ONEKI = _YER_ONEKI | {"yalniz", "sadece", "abi", "abla", "hocam", "usta", "simdi", "hem", "ek", "olarak", "tek", "istegimiz",
                             "bunun", "yaninda", "surgulu", "celik", "pvc", "ahsap", "aluminyum", "cam", "evde", "eve", "evin", "ev",
                             "evimizde", "evimize", "evimizin", "girisinden", "girisindeki", "kapisindan", "bizim", "numarali", "numara",
                             "sizin", "tamam", "evet", "tabi", "tabii", "yani", "sonra", "once", "ilk", "olarak", "sey", "su", "sunu",
                             "ekleyelim", "isteyelim", "rica", "lutfen", "acaba", "mesela", "ornegin"}
_BETIM_ONEKI |= {"efendim", "abicim", "bi", "disinda", "sey", "daha", "yan", "diger", "bahce", "ikinci", "birinci", "ucuncu",
                 "kapisi", "kapisindan", "giris", "servis"}                  # tur 19 (O4)
_BETIM_HITAP = {"kardesim", "kardes", "abim", "reis"}                                # tur 19 (O4): "eve" yolunda "abim eve gelince" öznedir
_BETIM_OZNE_KESIN = ("usta",)                                  # "usta eve gelince": hitap değil, öznedir (`_BETIM_OZNE_KOKU`)


def _betim_oncesi(sozler: list[str], hitap: bool = True) -> bool:
    """Yer sözünün önündeki sözler yalnız yerin parçası, hitap ya da dolgu mu ve özne ya da zaman yok mu (tur 16, O-G; tur 17, O-J;
    tur 18, Orta 4; `_BETIM_ONEKI`, `_BETIM_OZNE_KOKU`, `_BETIM_OZNE`)."""
    for w in sozler:
        if w.isdigit() or _yer_koku(w):
            continue
        if hitap and w in _BETIM_HITAP:
            continue
        if w in _BETIM_OZNE or w.startswith(_BETIM_OZNE_KOKU) or w not in _BETIM_ONEKI:
            return False
    return True


def _betim_zamani(g: str, once: list[str], sozler: list[str], sonra: list[str] = ()) -> bool:
    """Planın bir yerini anan istekteki zaman sözü (`g`; önündeki sözler `once`, ardındakiler `sonra`) o yerin betimi mi (tur 14, tur 15,
    tur 16; `_HAREKET_KOKU`): hareket fiili ve önünde yön eki almış oda, kapı ya da pencere ("kapıdan girince", "salona girdikten sonra",
    "yatak odası 1'e gelince"; "kapı açıldığında" yalın da) ya da ardında konum sözüyle oda ("eve girince soldaki yatak odası")."""
    if _bagli_konu(sozler) or _biz_ertelemesi(sozler) or _belli_olma(sozler):
        return False                                           # tur 17: "odaya girince netlik kazanır", "salona girince belli olur"
    yer = [w for w in once if not w.isdigit()]
    if not yer:
        return False
    sonra = list(sonra)
    if g.startswith(_KONUM_FIILI) and yer[-1] in _DIS_IC and _betim_oncesi(yer[:-1]):
        return True                                            # tur 16 (O-C): "dışarıdan bakınca", "içeri girince"
    if g.startswith(_KONUM_FIILI) and sonra and _KONUM_SOZU.fullmatch(sonra[0]) and any(_yer_koku(w) for w in sonra[1:3]) \
            and (yer[-1].startswith("ev") or _yer_koku(yer[-1])) and yer[-1].endswith(("e", "a", "den", "dan", "ten", "tan")) \
            and _betim_oncesi(yer[:-1], hitap=not yer[-1].startswith("ev")):
        return True                                            # tur 16: "eve girince soldaki yatak odası"
    if not g.startswith(_HAREKET_KOKU):
        return False
    if yer[-1] in _YON_EKI:                                    # "yatak odası 1'e" → "odasi", "e"
        return len(yer) > 1 and bool(_yer_koku(yer[-2])) and _betim_oncesi(yer[:-2])
    kok = _yer_koku(yer[-1])
    if kok is None or not _betim_oncesi(yer[:-1]):
        return False
    if g.startswith(("acil", "acin", "kapan")):               # "kapı açıldığında", "pencere kapanınca"
        return True
    ek = yer[-1][len(kok):]
    return ek.endswith(("a", "e", "dan", "den", "tan", "ten"))


_KARARSIZLIK_ARASI = {"karar", "emin", "tam", "hala", "henuz", "pek", "cok", "kesin", "biraz"}


# tur 17 (Y-B'): "karar" ile sahibi arasındaki dolgu ("karar yine müşterinin", "karar tamamen müşteriye ait")
_KARAR_DOLGU = {"yine", "gene", "tamamen", "hep", "artik", "simdi", "tabi", "tabii", "de", "da", "ise", "zaten", "yani", "biraz",
                "daha", "tam", "hala", "henuz", "en", "son", "kesin", "nihai", "asil"}
# sahibin ardından gelince kararın sahipliğini söyleyen söz ("müşterinin elinde"); başka söz gelirse ("müşterinin onayıyla verildi",
# "sonunda netleşti") tamlama ya da zarftır (tur 17, O-N)
_SAHIP_ARDI = {"", "elinde", "elindedir", "uzerinde", "takdirinde", "takdiri", "tercihinde", "tercihi", "inisiyatifinde", "dir", "tir",
               "artik", "simdilik", "su", "an", "olacak", "kalacak", "kaldi", "kalsin"}
_SAHIP_FIILI = ("kal", "birak", "devret", "havale", "ait")
# tur 18 (Yüksek 3): ekli sahip ancak ardından kararın verildiğini söyleyen söz ("netleşti", "kesinleşti", "verildi", "alındı", "oldu") ya
# da sahibin ad tamlaması ("müşterinin onayıyla", "müşterinin isteği", "müşterinin dediği") gelirse sahip değildir; dolgu ve yüklem
# ("karar müşteride tabi", "müşterinin bence", "müşteride olsun") sahipliği bozmaz
_KARAR_VERILDI = ("netles", "kesinles", "veril", "verdi", "alindi", "aldi", "oldu", "belli", "kararlastir", "bitti", "tamam", "vermis",
                  "almis")


def _verildi(ham: list[str], j: int) -> bool:
    """`ham[j]` kararın verildiğini mi söylüyor (tur 21, O11): geçmiş ("netleşti", "vermiştik", "belli oldu"); gelecek ve geniş zaman
    ("netleşecek", "kesinleşir", "verilecek", "belli olur") değil."""
    v, s = ham[j], ham[j + 1] if j + 1 < len(ham) else ""
    if not v.startswith(_KARAR_VERILDI) or re.search(r"[ae]c[ae][kg]", v) \
            or re.fullmatch(r"(?:netles|kesinles|veril|kararlastir)[iu]r\w*", v):
        return False
    if v.startswith("belli") and s.startswith("ol") and not s.startswith(("oldu", "olmus")):
        return False
    if re.search(r"[iu]yor", v) or (v == "belli" and not s.startswith(("oldu", "olmus"))) \
            or (re.fullmatch(r"\w+m[iu]s", v) and s.startswith(("olur", "olacak"))):
        return False                                           # tur 22: "karar yarın netleşiyor", "karar yarın belli", "netleşmiş olur"
    return True
_TAMLAMA_ADI = re.compile(r"\w+(?:s?[iu](?:yla|yle|na|ne|nda|nde|ndan|nden|n)?|ig[iu]|dig[iu]\w*)")
# tur 18 (Orta 1, önceden var): "karar"dan sonra zaman ("kesin karar haftaya", "karar pazartesi") kararın sonra verileceğidir
_KARAR_ZAMANI = ("haftaya", "yarin", "pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi", "pazar", "sonra", "aksam",
                 "hafta", "ileride", "bayram", "yilbasi")
_KARAR_AYI = {"ay", "aya", "ayin", "ayda", "aybasi", "aybasinda", "aysonu", "ay sonu"}
# tur 19 (O5): karardan sonra kesinlik ("karar sonra değişmez", "sonradan değiştirmeyiz") ya da verilmiş karar ("ayın 5'inde verildi")
_KARAR_KESIN = re.compile(r"degis\w*m(?:ez|az|eyiz|ayiz|em|am|eyecek\w*|ayacak\w*|eyeceg\w*|ayacag\w*)")   # tur 20 (O3): mastar değil
# tur 18 (Orta 1, Orta 3): kararı başkasının vereceği fiil ("verecek", "verir", "versin", "verilecek", "söyleyecek", "belirleyecek",
# "seçer"); birinci kişinin geçmişi ve şimdisi ("verdik", "verebildik", "veriyoruz", "verirken", "veren") değil
_KARAR_VERECEK = re.compile(r"(?:ver|soyle|belirle|sec|bildir|netlestir|kesinlestir)(?:il|n)?y?"
                            r"(?:ecek|acak|eceg|acag|ir(?!ken)|er(?!ken)|r(?!ken)|sin|iyor(?!uz|um)|[ae]bil(?:ir|ecek|acak))\w*"
                            r"|(?:soyl[u]|belirl[i])yor(?!uz|um)\w*")   # tur 18 kalanı: "söyleyecek", "belirleyecek", "söyler", "verebilir"
# tur 18 kalanı: kararı ikinci kişiye bırakan emir ("kararı siz verin", "karar verin"); "kararı verin" sözünün arasında yalnız "siz"
_KARAR_EMRI = ("verin", "veriniz", "verirsiniz", "verebilirsiniz", "verseniz", "versene")
# tur 20 (O5): karar fiilinin penceresi (5 söz) başka bir işin nesnesinde biter ("kararımızı verdik kaporayı müşteri yarın verecek")
_KARAR_DISI_IS = ("kapora", "imza", "odeme", "para", "avans", "sozlesme", "pesinat", "teslim", "fatura", "taksit", "senet")
# tur 26 sonrası (önceden var): müşterinin danıştığı kişi konu değildir ("müşteri ustasına / mimarına soracak")
_DANISILAN_KISI = re.compile(r"(?:usta|mimar|muhendis|danisman|avukat)\w*[ae]")


_KARAR_VERDIK = ("verdi", "verildi", "vermis", "aldi", "alindi", "almis", "netlesti", "kesinlesti", "kararlastir", "sectik", "sectim",
                 "secildi")
_IS_ZAMANI_ARDI = ("gun", "sira", "esna", "tarih", "zaman", "once", "sonra", "hafta")


def _karar_penceresi(ham: list[str], i: int) -> list[str]:
    p, pen = [], ham[i + 1:i + 6]
    for j, v in enumerate(pen):
        s = pen[j + 1] if j + 1 < len(pen) else ""
        if v.startswith(_KARAR_VERDIK):
            break                                              # tur 22 (O8): "kararımızı verdik teslim tarihini siz söyleyeceksiniz"
        if v.startswith(_KARAR_DISI_IS) and not v.endswith(("dan", "den", "tan", "ten", "da", "de", "ta", "te")) \
                and not (s in ("an", "ani", "aninda") or s.startswith(_IS_ZAMANI_ARDI)):
            break                                              # tur 21 (O4): zaman sözü ("kapora günü", "imza sırasında") pencereyi bitirmez
        p.append(v)
    return p


# tur 20 (O6, Y3): müşterinin ileride bakacağı, düşüneceği ya da diyeceği söz ("müşteri bakacak", "bakalım müşteri ne diyecek") kararı erteler
_ERTELEYEN_KISI = ("musteri", "esi", "esim", "hanim", "sahib", "aile")
_MUSTERI_ERTELEME = re.compile(r"(?:bak|dusun|incele|degerlendir|danis|konus|sor|karar|di|soyle|gor|sec|belirle|onayla)\w*"
                               r"(?:[ae]c[ae]k|[ae]c[ae]g)\w*")   # tur 23 (Y2): "çatıyı müşteri seçecek"


_MUSTERI_ISTEGI = re.compile(r"(?:bak|dusun|incele|degerlendir|gor|danis|sec|belirle|onayla)(?:s[iu]n(?:l[ae]r)?|[ae]r|[iu]r)"
                             r"|(?:onayla|belirle)r|(?:sec|bak|incele|degerlendir)[iu]yor|belirliyor|onayliyor")   # tur 24 (Y3): "müşteri
                                                               # onaylar", "çatıyı müşteri belirler", "müşteri seçiyor"   # tur 21:
                                                               # "eşi de görsün"; tur 23 (Y2): "müşteri onaylasın", "müşteri seçsin"
# tur 23 (Y2): müşterinin bakması, görmesi ya da onayı gerekiyor ("karar için müşterinin bir daha bakması lazım", "eşinin de görmesi lazım")
_MUSTERI_GEREGI = re.compile(r"(?:bak|dusun|incele|degerlendir|gor|danis|sec|belirle|onayla|karar)\w*m[ae]s[iu]")
_GEREK_SOZU = ("lazim", "lazimdir", "gerek", "gerekli", "gerekiyor", "gerekir", "sart", "sarttir")   # tur 24 (O5): tam söz ("gereken" değil)


def _gerek_ardi(ham: list[str], j: int) -> bool:
    """`ham[j]`'den sonra gerek sözü geliyor mu (tur 25, O3, Y3): "lazım", "gerekecek", "gerekebilir", "gerekiyormuş", "lazımdı"; araya
    `_GEREK_DOLGU` girebilir ("onayı da lazım", "onayı ayrıca lazım"); "ihtiyaç var" da. "gereken", "gerekmez", "lazım değil", "gerek
    yok" ve ardından alınmış onay ("gerekiyordu aldık") değil."""
    k = j + 1
    while k < len(ham) and ham[k] in _GEREK_DOLGU:
        k += 1
    if k >= len(ham):
        return False
    w, s = ham[k], (ham[k + 1] if k + 1 < len(ham) else "")
    return w.startswith(("lazim", "gerek", "sart", "ihtiyac")) \
        and not w.startswith(("gereken", "gerektig", "sartname", "sartli", "sartla")) \
        and not re.match(r"gerekm(?:ez|iyor|edi|eyecek)", w) and not s.startswith(("degil", "yok")) \
        and not any(_ALINMIS_ONAY.fullmatch(y) and ham[k + 2 + n:k + 3 + n] not in (["mi"], ["mu"]) for n, y in enumerate(ham[k + 1:k + 4]))
                                                               # tur 26 (O4); tur 27 (O6): yalnız geçmiş zaman, soru değil ("alınacak",
                                                               # "alınmadı", "onayladı mı" değil)
                                                               # "onayı gerekiyordu aldık" alınmış onaydır


_ALINMIS_ONAY = re.compile(r"(?:ald[iu]|alindi|aldirdi|verd[iu]|verildi|geld[iu]|onaylad[iu]|onaylandi)(?:k|m|lar|ler)?")
# tur 26 (Y5): gerek sözünden önceki dolgu ("onayı ayrıca / mutlaka / kesin lazım")
_GEREK_DOLGU = ("de", "da", "bir", "daha", "yine", "ayrica", "mutlaka", "kesin", "kesinlikle", "muhakkak", "illa", "illaki", "hala",
                "sizden", "bizden")
# tur 23 (O4): kişiden sonra başka bir özne ("müşterinin arsasına ustamız yarın bakacak", "müşteri için ekip zemine bakacak") ya da başka
# bir cümle ("müşteri kaporayı yatırdı ekip yarın bakacak", "müşteri memnun ve ustalar gelip bakacak") gelirse fiil onundur
# tur 24 (O6): yalın hâlde ("ustamız", "ekip", "ustalar"); ekli hâli ("ustayla birlikte", "mühendisine danışacak") müşterinin fiilidir
_BASKA_OZNE = re.compile(r"(?:usta|ekip|ekib|eleman|montajci|firma|muhendis|elektrikci|tesisatci|sofor|nakliyeci|taseron|muhasebe"
                         r"|muhasebeci|personel|isci)(?:lar|ler)?(?:[iu]?m[iu]z|[iu]n[iu]z|[iu]?m|s?[iu])?(?:lar|ler)?"
                         r"|(?:cocuk|arkadas)(?:lar|ler)(?:[iu]m[iu]z|[iu]m)?|arkadasim|kardesim|oglum|biz|ben"   # tur 25 (O8)
                         r"|mimar(?:lar)?(?:[iu]m[iu]z|[iu]m)?|ortag[iu]m(?:[iu]z)?|ortaklar[iu]m(?:[iu]z)?|abim|ablam|babam|annem|amcam|dayim|enistem|yegenim"
                         r"|kuzenim")   # tur 25 sonrası: "müşteri onayladı abim / ortağım / mimar bakacak"
# tur 25 (O7): kişiye bırakılan şeyin adı yoksa çatının kararıdır ("müşteriye kalsın", "çatı seçimi müşteriye kalsın"); "temel müşteriye
# kalsın", "fayans müşterinin tercihine kalsın", "bundan sonrası müşteriye kalsın" o işin sözüdür. Tur 26 (Y2): kara liste; hitap ve dolgu
# ("abi müşteriye kalsın", "en iyisi müşteriye kalsın", "valla müşteriye kalsın") çatının kararını bırakır
_KISIYE_IS_KOKU = ("temel", "zemin", "mobilya", "dekor", "tesisat", "elektrik", "iskele", "depo", "kombi", "perde", "peyzaj", "bahce",
                   "esya", "fayans", "seramik", "parke", "dolap", "malzeme", "sonrasi", "geris", "kalan", "diger", "oteki", "obur", "detay",
                   "ayrinti", "isler", "isleri", "dogalgaz", "aydinlatma", "lamba", "priz", "tente", "korkuluk", "merdiven", "beton",
                   # tur 27 (O5): yapının öteki işleri
                   "somine", "laminat", "panjur", "sineklik", "gunes", "panel", "kamera", "alarm", "sofben", "termosifon", "hafriyat",
                   "kazi", "ruhsat", "dizayn", "tasarim", "cit", "dusakabin", "izolasyon", "yalitim", "vinc", "avize", "baglanti",
                   "kanalizasyon", "fosseptik", "arac", "ankraj", "siva", "alci", "boya", "badana", "kartonpiyer", "tavan", "doseme",
                   "cini", "mermer", "granit", "tezgah", "lavabo", "klozet", "batarya", "musluk", "petek", "radyator", "soba", "isitma",
                   "havalandirma", "aspirator", "davlumbaz", "ankastre", "stor", "jaluzi", "kepenk", "kilit", "guvenlik", "interkom",
                   "diafon", "uydu", "anten", "internet", "sigorta", "kablo", "spot", "cim", "agac", "cicek", "havuz", "pergola",
                   "kamelya", "cardak", "barbeku", "otopark", "garaj", "kaldirim", "bordur", "duvar", "istinat", "bariyer", "harc",
                   "vergi", "abone", "forklift", "kurulum", "iscilik", "nakliye", "klima", "oluk", "drenaj", "cephe", "kaplama",
                   "veranda", "teras", "balkon", "sundurma", "parmaklik")
_KISIYE_IS_SOZU = ("tel", "teller", "sap", "suyu", "is", "isi", "isin")   # tam sözle ("şu" ve "telefon" değil)


def _kisiye_birakilan_cati(ham: list[str], i: int) -> bool:
    """Kişiden (`ham[i]`) önce başka bir işin adı yok mu (tur 25, O7; tur 26, Y2: kara liste)."""
    if i > 0 and ham[i - 1] == "ev" and ham[i].startswith("sahib"):
        i -= 1                                                 # "ev sahibine kalsın"
    return not any(not _hitap_yeri(ham, k, i) and (_konu_adi(a) or _yer_koku(a) or a.startswith(_KISIYE_IS_KOKU) or a in _KISIYE_IS_SOZU)
                   for k, a in enumerate(ham[:i]))             # tur 27 (Y1): "usta müşteriye kalsın" hitaptır


def _hitap_yeri(ham: list[str], k: int, son: int | None = None) -> bool:
    """`ham[k]` hitap mı: hitap sözü ve ardından (`son`'dan önce) iyelikli ad gelmiyor; "usta ücreti", "usta parası" işin adıdır (tur 28,
    O5); "usta bey", "usta müşteriye", "usta seçim" hitaptır."""
    son = len(ham) if son is None else son
    s = ham[k + 1] if k + 1 < son else ""
    return ham[k] in _HITAP_SOZU and not (len(s) > 3 and re.fullmatch(r"\w+[iu]", s) and s not in _HITAP_SOZU
                                          and s not in _HITAP_ZAMIRI
                                          and not s.startswith(_ERTELEYEN_KISI + _KISI_KARARI + ("sonuc",)))
                                                               # "usta seçimi müşteriye kalsın"; tur 29 (Y2, O7): "usta bunu müşteri
                                                               # seçecek", "usta sonucu müşteriye kalsın" hitaptır


_HITAP_ZAMIRI = {"bunu", "sunu", "onu", "bunun", "sunun", "onun", "bizi", "sizi", "beni", "seni", "kendisi", "kendileri", "hepsi",
                 "ikisi", "birisi", "hangisi", "digeri", "oburu", "bunlari", "onlari"}


# tur 26 (Y1): "müşteriye bıraktık" kararın müşteride beklediğini söyler; ardından müşterinin seçimi gelirse ("o da 2 dedi", "2'yi
# seçti") karar verilmiştir
_SECIM_BILDIRIMI = re.compile(r"(?:sec|onayla|begen)(?:t[iu]|d[iu]|m[iu]s)(?:k|m|ler|lar)?|kabul|razi")
_SOZ_BILDIRIMI = re.compile(r"(?:ded[iu]|demis|isted[iu]|istemis|verd[iu]|vermis|kild[iu]|kilmis)(?:k|m|ler|lar)?")
_GECMIS_ETTI = re.compile(r"et(?:t[iu]|mis)(?:k|m|ler|lar)?")          # "kabul etti", "tercih etmiş"; "etmedi", "edecek" değil
_GORDU = re.compile(r"(?:gord[iu]|gormus)(?:k|m|ler|lar)?")            # "uygun gördü"


def _secim_bildirildi(sozler: list[str]) -> bool:
    """Müşterinin seçimi bildirildi mi (tur 26, Y1; tur 27, Y2): "2'yi seçti", "onayladı", "o da 2 dedi", "karar verdi"; sıfat-fiil
    ("seçtiği olsun", "onayladığı zaman"), olasılık ("seçmiş olabilir"), soru ("onayladı mı") ve çatıyı anmayan söz ("düşünürüm dedi",
    "zaman istedi") değil."""
    for n, a in enumerate(sozler):
        s = sozler[n + 1] if n + 1 < len(sozler) else ""
        if s in ("mi", "mu") or s.startswith(("olabil", "olmali", "olur")) or (a == "kabul" and not _GECMIS_ETTI.fullmatch(s)) \
                or (a == "razi" and (s.startswith(("degil", "olmad", "olmaz", "olmay", "olac", "olsa", "olmas")))):
            continue                                           # tur 28 (Y5): "razı değil", "razı olacak"
        if _SECIM_BILDIRIMI.fullmatch(a):
            return True
        once = sozler[max(0, n - 2):n]

        def atif(xs):
            return any(x[:1].isdigit() or len(x) == 1 or x.startswith(("cati", "karar", "onay") + _CATI_AD_KOKU)
                       or x in ("bu", "bunu", "onu", "tamam", "evet", "olur", "ok", "okey") for x in xs)
        if _SOZ_BILDIRIMI.fullmatch(a) and atif(once):
            return True                                        # tur 28: "2'de karar kıldı"
        if a == "tercih" and _GECMIS_ETTI.fullmatch(s) and atif(once):
            return True                                        # tur 28: "2'yi tercih etti"
        if _GORDU.fullmatch(a) and once[-1:] in (["uygun"], ["makul"], ["mantikli"]) and atif(sozler[max(0, n - 3):n - 1]):
            return True                                        # tur 28: "o da 2'yi uygun gördü"
    return False


_GECMIS_FIIL = re.compile(r"\w*(?:d|t)[iu](?:k|m|n|niz|nuz|ler|lar)?|\w*m[iu]s(?:t[iu]k|t[iu]m|t[iu])?")   # "bıraktık", "bırakıldı", "kalmış"
# tur 24 (Y3): kararı kişiye bırakan tamlama ("çatı müşterinin kararı", "müşterinin tercihine kalsın")
_BAKILAN_IS = ("zemin", "arsa", "arazi", "temel", "montaj", "stati", "saha", "olcu", "kazi", "hafriyat", "beton", "iskele", "nakliye",
               "tesisat", "elektrik", "ankraj")
_KISI_KARARI = ("karar", "tercih", "secim", "onay", "takdir", "inisiyatif", "insiyatif")


def _musteri_ertelemesi(ham: list[str], ardi: list[str] | tuple = ()) -> bool:
    """Müşteri ya da yakını kararı ileride verecek mi ("müşteri bakacak", "bakalım müşteri ne diyecek", "eşi de görsün", "müşteri bir
    bakar"); fiil başka bir konunun nesnesini alıyorsa ("müşteri teslim tarihini soracak", "fiyatı soracak") ya da gelip görmekse ("müşteri
    de gelip görecek") o işin sözüdür (tur 21, O10). `ardi`: sonraki cümlenin sözleri ("müşteriye bıraktık, 2'yi seçti")."""
    cati = any(a.startswith(("cati",) + _CATI_AD_KOKU) for a in ham)
    konulu = any(_konu_adi(a) and not _hitap_yeri(ham, k) for k, a in enumerate(ham)) and not cati   # tur 27 (Y1): "usta müşteriye
                                                               # kalsın"; tur 28 (O5): "usta ücreti müşteriye kalsın" değil
    for i, x in enumerate(ham):
        if not x.startswith(_ERTELEYEN_KISI):
            continue
        tamlayan = bool(re.fullmatch(r"\w+(?:n[iu]n|[iu]m[iu]n|[iu]m[iu]z[iu]n|l[ae]r[iu]n)", x))   # "müşterinin", "müşterimin" (tur 25, Y3)
        yonelme = bool(re.fullmatch(r"\w+(?:y[ae]|[iu]m[ae]|[iu]m[iu]z[ae]|l[ae]r[ae]|[iu]n[ae])", x))   # "müşteriye", "müşterime",
                                                               # "müşterilere", "ev sahibine", "eşine"
        s1, s2 = (ham[i + 1:i + 3] + ["", ""])[:2]
        bildirildi = _secim_bildirildi(list(ham[i + 2:]) + list(ardi))
        if not konulu and _kisiye_birakilan_cati(ham, i) and (
                (yonelme and s1.startswith(("kal", "birak")) and not (_GECMIS_FIIL.fullmatch(s1) and bildirildi))
                or (tamlayan and s1.startswith(_KISI_KARARI) and (not s2 or (s2.startswith(("kal", "birak", "bagli"))
                                                                              and not (_GECMIS_FIIL.fullmatch(s2) and bildirildi))))):
            return True                                        # tur 24 (Y3): "müşteriye kalsın", "müşterinin tercihine kalsın", "çatı
                                                               # müşterinin kararı"; tur 25 (O7): "temel müşteriye kalsın", "müşteriye
                                                               # bıraktık o da 2 dedi" değil; tur 26 (Y1): "müşteriye bıraktık" ertelemedir
        for j in range(max(0, i - 2), min(len(ham), i + 10)):
            v = ham[j]
            if j > i and not konulu and _MUSTERI_GEREGI.fullmatch(v) and _gerek_ardi(ham, j):
                return True                                    # tur 23 (Y2): "müşterinin bir daha bakması lazım"; tur 24 (O4): konulu değil
            if j > i and re.fullmatch(r"onay(?:[iu]|[iu]n[iu]|[iu]n[ae]|lar[iu])?", v) and _gerek_ardi(ham, j):
                return True                                    # tur 23 (Y2): "karar için müşterinin onayı lazım"
            if j == i or not (_MUSTERI_ERTELEME.fullmatch(v) or _MUSTERI_ISTEGI.fullmatch(v)) or _OLUMSUZ_FIIL.fullmatch(v) \
                    or re.search(r"[ae]c[ae]g[iu]z$", v):
                continue                                       # "bakacağız" bizim işimizdir
            ara = ham[i + 1:j] if j > i else []
            if ham[i + 1:i + 2] == ["icin"] or (ara[:1] not in (["ve"], ["ile"], ["la"], ["le"]) and any(
                    _BASKA_OZNE.fullmatch(a) and ara[n2 + 1:n2 + 2] not in (["ile"], ["birlikte"], ["beraber"])
                    and not (n2 == 0 and tamlayan)                                   # tur 26 (O3): "müşterinin ustası bakacak"
                    and not (ara[:1] == ["hem"] or (ara[:1] in (["de"], ["da"]) and ara[n2 + 1:n2 + 2] in (["de"], ["da"])))   # "hem
                                                                                     # müşteri hem usta", "müşteri de usta da" ortaktır
                    and not re.fullmatch(r"\w+y?l[ae]", ara[n2 + 1] if n2 + 1 < len(ara) else "")   # "mimar arkadaşıyla"
                    for n2, a in enumerate(ara))):
                continue                                       # tur 23 (O4), tur 24 (O6): yalın başka özne ("ustamız yarın bakacak")
            if v.startswith(("sec", "belirle")) and konulu:
                continue
            nesne = next((a for a in reversed(ara) if a not in ("de", "da", "bir", "yarin", "bugun", "haftaya", "tekrar", "gelip")), "")
            if v.startswith(("bak", "incele")) and re.fullmatch(r"\w+(?:y?[ae]|n[ae]|y?[iu]|n[iu])", nesne) and nesne not in _HITAP_SOZU \
                    and not re.fullmatch(r"\w+[dt][ae]", nesne) \
                    and not any(x.startswith(("haber", "donus", "donecek", "doner", "bildir", "karar", "onay")) for x in ham[j + 1:]) \
                    and not (any(x.startswith("cati") for x in ardi) and any(x.startswith(("bak", "incele", "karar", "sec")) for x in ardi)) \
                    and (_yer_koku(nesne) or nesne.startswith(_BAKILAN_IS)):   # tur 28 (O3): "müşteri arsada bakacak", "arsaya bakacak
                                                               # sonra haber verecek", "temele bakacak, çatıya da bakacak" ertelemedir
                continue                                       # tur 27 (O10): "müşterinin ustası zemine bakacak" o işin sözüdür                                       # tur 23 (Y2): "rengi müşteri seçecek" o konunundur
            if v.startswith(("sor", "soyle", "konus")) and any((_soru_konu_adi(a) or a.startswith(_KARAR_DISI_IS + ("tarih",)))
                                                                and not _DANISILAN_KISI.fullmatch(a) for a in ara):
                continue                                       # tur 22 (O4): "müşteri kapora günü bakacak" ertelemedir
            if ara and ara[-1] == "gelip" and ara[0] in ("de", "da") and re.fullmatch(r"gor[ue]c[ae][kg]\w*", v):
                continue                                       # "müşteri de gelip görecek"; "yarın gelip bakacak", "eşi de gelip görsün" değil
            return True
    return False


def _karar_sahibi(x: str, ardi: str = "", ardi2: str = "") -> bool:
    """"karar"dan sonraki söz kararın başkasında olduğunu mu söylüyor ("karar müşterinin", "müşteride", "sizin", "müşterinindir",
    "müşteriye kaldı", "müşteriye bıraktık", "müşteriye ait"; tur 16, Y-B; tur 17, Y-B', O-N)."""
    if not x or x[0].isdigit() or len(x) < 4 or x in ("bizim", "benim", "bizde", "bende", "kesin", "sonunda", "konusunda", "hakkinda", "icin",
                                                      "dogrultusunda", "sonucunda", "aslinda", "bizce", "bence") \
            or x.startswith(("ev", "cati", "kendi", "bu", "su")) or x.startswith(_CATI_AD_KOKU) or _yer_koku(x) \
            or x in _KARAR_AYI or x.startswith(_KARAR_ZAMANI):
        return False                                           # tur 19: zaman sözü sahip değil ("karar ayın 5'inde verildi")
    if x.endswith(("nindir", "nundur", "dedir", "dadir", "tedir", "tadir")):
        return True
    if x.endswith(("ye", "ya", "e", "a")) and (ardi.startswith(_SAHIP_FIILI) or ardi2.startswith(_SAHIP_FIILI)):
        return True                                            # tur 17 (Y-B'): "karar müşteriye kaldı", "kararı müşteriye bıraktık"
    if not x.endswith(("nin", "nun", "in", "un", "de", "da", "te", "ta")):
        return False
    if ardi in _SAHIP_ARDI or ardi.startswith(_SAHIP_FIILI) or ardi2.startswith(_SAHIP_FIILI):
        return True                                            # "müşterinin elinde", "müşterinin onayına kaldı"
    if ardi.startswith(_KARAR_VERILDI) or ardi2.startswith(_KARAR_VERILDI):
        return False                                           # tur 17 (O-N): "kararımız toplantıda kesinleşti", "müşterinin onayıyla verildi"
    if x.endswith(("nin", "nun", "in", "un")) and re.fullmatch(r"\w+[iu]nd[ae](?:dir)?", ardi):
        return True                                            # tur 18 kalanı: "karar müşterinin eşinde", "müşterinin kendisinde"
    if x.endswith(("nin", "nun", "in", "un")) and _TAMLAMA_ADI.fullmatch(ardi) and ardi not in _KARAR_DOLGU \
            and ardi not in ("bence", "bizce", "galiba", "herhalde", "olur", "olsun", "tabi", "tabii", "yani", "ama", "fakat"):
        return False                                           # tur 17 (O-N): "kararımız müşterinin isteği doğrultusunda"
    return True                                                # tur 18 (Yüksek 3): "karar müşteride tabi", "müşterinin bence", "müşteride olsun"


# tur 23 (Y1): kapanış sözü önekle değil kökün kendisiyle ("görüşümüz", "sağlam" kapanış değil); müşterinin geçici rızası ("müşteri
# şimdilik razı", "kabul etti", "ikna", "memnun", "sağlam görünüyor") seçimin sözüdür
_SIMDILIK_KAPANIS = ("baska", "tesekkur", "hosca", "sagol", "saol", "saglicak", "saygi", "gorusuruz", "gorusmek", "kolay", "bukadar",
                     "eyvallah", "tsk", "tesekur", "selam")
_SIMDILIK_SECIM = ("olsun", "kalsin", "sec", "cati", "karar", "kesin", "net", "belli", "emin", "tercih", "bu", "bunu", "boyle", "oyle",
                   "tamam", "uygun", "iyi", "olur", "dusun", "bil", "gecici", "idare", "plan", "razi", "kabul", "ikna", "memnun", "evet",
                   "olumlu", "onay", "gorun", "sagla", "guzel", "begen", "harika", "mutlu", "sicak")


def _simdilik_secimde(ham: list[str], i: int) -> bool:
    """"şimdilik" (`ham[i]`) seçimi geçici kılıyor mu ("Şimdilik 1 olsun", "1 olsun, şimdilik", "şimdilik iyi", "şimdilik tamam"; tur 21,
    Y1); kapanış ("şimdilik bu kadar", "şimdilik sağ olun", "şimdilik hepsi bu"), "yok" ya da olumsuz istek ("şimdilik sorumuz yok",
    "şimdilik değişiklik istemiyoruz") ve başka bir öznenin durumu ("müşteri şimdilik yurt dışında") değil (tur 22, O5, Y4)."""
    ardi = ham[i + 1:]
    if not ardi:
        return True
    if ardi[0].startswith(_SIMDILIK_KAPANIS) or (ardi[0] == "sag" and ardi[1:2] and ardi[1].startswith("ol")) \
            or (ardi[0] == "bu" and ardi[1:2] and ardi[1].startswith("kadar")) \
            or ardi[:2] == ["hepsi", "bu"] or (ardi[0] == "iyi" and ardi[1:2] and ardi[1].startswith(("gun", "aksam", "calisma", "hafta"))):
        return False
    secim = any(x[:1].isdigit() or x.startswith(_SIMDILIK_SECIM) for x in ham[:i] + ardi)
    if not secim and any(x in ("yok", "yoktur") or re.fullmatch(r"\w+m[iu]yor(?:uz|um)", x) for x in ardi):
        return False
    return i == 0 or secim


_DEGISEN_DOLGU = {"ama", "fakat", "ancak", "ve", "sonra", "sonradan", "belki", "yine", "de", "da", "ileride", "yarin", "haftaya", "tabi",
                  "tabii", "her", "zaman", "hala", "bile", "gerekirse", "istenirse", "olarak", "verildi",
                  "verdik", "alindi", "aldik", "kesin", "simdilik", "mi", "mu", "miyiz", "muyuz", "misiniz", "musunuz", "ki", "anda",
                  "son", "zamanla", "yakinda", "obur"}   # tur 25 (O2): "tabi ki", "son anda", "yarın öbür gün"
_DEGISEN_OZNE = ("karar", "cati", "secim", "tercih", "bu", "o", "su", "hepsi", "sey", "fikir", "fikr", "dusunce", "niyet",
                 "gorusu", "gorusum", "kanaat", "istek", "istegi", "akl", "kafa")   # "fikrimiz / aklımız değişebilir"


def _degisenin_oznesi(ham: list[str], k: int) -> bool:
    """"değişebilir" (`ham[k]`) seçimi mi anlatıyor (tur 24, O2): öznesi yok ("2 olsun, değişebilir", "karar verildi ama değişebilir"),
    karar, çatı, seçim ya da kişi; "tarih değişebilir", "randevu değişebilir" o şeyin değişmesidir."""
    j = k - 1
    while j >= 0 and (ham[j] in _DEGISEN_DOLGU or (ham[j] == "gun" and j > 0 and ham[j - 1] == "obur")):
        j -= 1                                                 # "yarın öbür gün değişebilir"; "gün değişebilir" günün değişmesidir
    return j < 0 or ham[j][:1].isdigit() or ham[j].startswith(_DEGISEN_OZNE + _CATI_AD_KOKU + _ERTELEYEN_KISI) \
        or ham[j] in ("olsun", "kalsin")


_GECICI_ATLA = {"evin", "kendi", "mevcut", "eski", "ayni", "su", "anki", "var", "olan", "orijinal", "standart", "birinci", "ikinci",
                "ucuncu", "dorduncu", "besinci", "ilk", "son", "sonuncu", "numara", "numarali", "nolu", "secenek", "secenegi", "hali",
                "haliyle", "simdiki", "ilki", "ikincisi", "sonuncusu"}   # tur 27 (O9): "geçici olarak ikinci / mevcut çatı kalsın"


def _degis_olasiligi(ham: list[str], m: int) -> bool:
    """"değiş…"ten sonraki söz (`ham[m]`) olasılık mı (tur 25; tur 26, O1; tur 27, O7): "isteyebilir", "düşünebiliriz", "olabilir",
    "gerekebilir", "zorunda kalabiliriz", "tercih edebilir", "değişiklik yapabiliriz"; bize rica ("yapabilir misiniz?", "gönderebilir
    misiniz?", "yapabilirsiniz") değil."""
    w, s = ham[m], (ham[m + 1] if m + 1 < len(ham) else "")
    if _OLUMSUZ_FIIL.fullmatch(w) or re.fullmatch(r"m[iu]s[iu]n(?:[iu]z)?", s) or re.search(r"s[iu]n(?:[iu]z)?$", w):
        return False
    return bool(re.fullmatch(r"(?:iste[iy]?ebil|dusunebil|olabil|gerekebil|kalabil|edebil)\w*|yapabilir(?:iz|im|ler)?", w))


def _gecici_secim(ham: list[str], j: int) -> bool:
    """"geçici olarak"tan sonra (`ham[j]`; süre atlanır: "6 ay") seçimin sözü mü geliyor ("geçici olarak 6 ay bu çatı kalsın"); "ev
    geçici olarak depoda kalsın", "kapı geçici olarak tek kanat olsun" değil (tur 26, O4)."""
    if j + 1 < len(ham) and ham[j][:1].isdigit() and not _birimsiz_sayi(ham, j):
        j += 2
    while j < len(ham) and (len(ham[j]) <= 2 or any(c.isdigit() for c in ham[j]) or ham[j] in _GECICI_ATLA):
        j += 1                                                 # numara, kod ya da etiket: "geçici bir süre Ç8801 / PA-06-K / 1 olsun"
        if j < len(ham) and ham[j] in ("olsun", "kalsin"):
            return True
    return j < len(ham) and (ham[j] in ("olsun", "kalsin", "boyle", "oyle", "yeterli", "yeter")
                             or ham[j].startswith(("bu", "cati", "secenek") + _CATI_AD_KOKU))


def _birimsiz_sayi(ham: list[str], j: int) -> bool:
    """`ham[j]` sayı ve ardından birim gelmiyor mu ("geçici 1 olsun"; "geçici olarak 6 ay" değil; tur 24, O3)."""
    if j >= len(ham) or not ham[j][:1].isdigit():
        return False
    return not (j + 1 < len(ham) and ham[j + 1].startswith(("ay", "yil", "sene", "hafta", "gun", "saat", "kisi", "metre", "m2", "ton")))


def _konulu_soru_sozu(ham: list[str], i: int) -> bool:
    """`ham[i]`'deki "bilmiyoruz / emin değiliz" bir bilgi sorusunun tümleci mi: ondan önceki son soru sözünün sorusunda (önceki soru
    sözünden sonra) bir konu var ("teslim ne zaman olur bilmiyoruz", "ne kadar sürede teslim olur emin değiliz"). Tur 25 (Y1): "ne
    yapalım bilemedik fiyat ne kadar?" seçimin kararsızlığıdır (konu kararsızlık sözünden sonra), "fiyat ne kadar ne yapalım bilemedik"
    de öyle (konu öteki sorunun)."""
    q = max((k for k in range(i) if ham[k] in _SORU_SOZU), default=-1)
    if q < 0:
        return False
    p = max((k for k in range(q) if ham[k] in _SORU_SOZU), default=-1)
    return any(_konu_adi(x) for x in ham[p + 1:i])


_DEVIR_KALIBI = {"size", "sana", "sizlere", "bize", "bana", "ben", "biz", "benim", "bizim", "icin", "de", "da", "hangisi", "hangisini",
                 "hangisinin", "ikisi", "ikisinden", "biri", "birini", "olsa", "olur", "olursa", "cok", "pek", "hic", "aslinda", "yani",
                 "valla", "vallahi", "etmez", "etmiyor", "artik", "tamamen", "o", "onu", "bunu", "bu", "su", "ama", "ve", "zaten",
                 "olsun", "kalsin", "numara", "numarali", "nolu", "evin", "kendi"}
_TAHMIN_SOZU = {"herhalde", "galiba", "sanirim", "saniyorum", "sanki", "muhtemelen", "galba", "heralde", "olabilir"}   # tur 29 (Y6):
                                                               # "1 olsun olabilir"


def _ucret_ardi(ham: list[str], k: int) -> bool:
    """"değişiklik ücreti", "değişiklik için ücret": değişmenin ücreti sorulur, değişme olasılığı değil (tur 28, O6). Tur 29 (O8): "sonra
    değiştirmek isterse ücret olabilir mi?" değişme olasılığıdır."""
    a = ham[k + 1:k + 2] + (ham[k + 2:k + 3] if ham[k + 1:k + 2] == ["icin"] else [])
    return bool(a) and a[-1].startswith(("ucret", "fiyat", "masraf", "bedel", "para", "zam"))


def _kararsizlik_var(ham: list[str], soru: bool = False, ardi: list[str] | tuple = ()) -> bool:
    """Cümlede seçimin kararsızlık sözü var mı (tur 14, Yüksek-1; tur 15, O-5; `_KARARSIZLIK_KOKU`). Soru cümlesinde (`soru`) "şimdilik"
    ve "geçici" sayılmaz ("şimdilik ne yapmamız gerekiyor?")."""
    if _musteri_ertelemesi(ham, ardi):
        return True                                            # tur 20 (O6): "müşteri bakacak"
    if any(w in _TAHMIN_SOZU for w in ham) and all(
            w in _TAHMIN_SOZU or w in _YUKLEM_SOZU or w[:1].isdigit() or len(w) == 1 or w.startswith(("cati",) + _CATI_AD_KOKU)
            or w in _HITAP_SOZU or w in ("bu", "o", "su", "ya", "de", "da", "ki", "yani", "numara", "numarali", "nolu", "evin", "kendi")
            for w in ham):
        return True                                            # tur 28: "2 olsun herhalde", "galiba 1 olsun" tahmindir; "sanırım teklif
                                                               # yarın gelir" değil
    def secim_sozu_mu(x: str) -> bool:                       # tur 29 (O5): devrin konusu seçim olmalı ("gerisini size bırakıyorum",
        return x in _DEVIR_KALIBI or x in _HITAP_SOZU or x in _YUKLEM_SOZU or (len(x) == 1 and not x.isdigit()) \
            or x.startswith(("cati", "fark", "birak", "secim", "secen", "karar", "tercih") + _CATI_AD_KOKU) \
            or (x[:1].isdigit() and not _birimli(ham, ham.index(x)))   # "nakit ya da kart fark etmez", "belki 2 ay sonra" değil
    if not any(_konu_adi(x) or _yer_koku(x) for x in ham) and (
            ((any(a == "fark" and b.startswith(("etmez", "etmiyor")) for a, b in zip(ham, ham[1:])) or "farketmez" in ham
              or any(a in ("size", "sana", "sizlere") and b.startswith("birak") for a, b in zip(ham, ham[1:])))
             and all(secim_sozu_mu(x) for x in ham))
            or any(a == "belki" and ((b[:1].isdigit() and not _birimli(ham, k + 1)) or (len(b) == 1 and not b.isdigit())
                                     or b.startswith(("cati",) + _CATI_AD_KOKU))
                   for k, (a, b) in enumerate(zip(ham, ham[1:])))):
        return True                                            # tur 28: "1 olsun, fark etmez", "size bırakıyorum", "2 olsun belki 3"
                                                               # seçimi bize bırakır ya da öteki çatıyı anar; "renk fark etmez" değil
    cati = any(x.startswith("cati") for x in ham)
    konulu = any(_konu_adi(x) for x in ham) and not any(x.startswith(("cati",) + _CATI_AD_KOKU) for x in ham)
    if not konulu and not any(_yer_koku(x) for x in ham) and any(
            (re.fullmatch(r"degis\w*[ae]bil\w*", x) or ("belki" in ham and x.startswith("degis") and not _OLUMSUZ_FIIL.fullmatch(x))
             or (x.startswith("degis") and any(_degis_olasiligi(ham, m) and not any(
                 _konu_adi(a) for a in ham[k + 1:m]) and not _ucret_ardi(ham, k)
                 for m in range(k + 1, min(len(ham), k + 4)))))   # tur 28 (O6): "değişiklik ücreti olabilir mi?"   # tur 25: "müşteri sonra değiştirmek isteyebilir"; tur 26 (O1):
                                                               # "değiştirip gönderebilir misiniz?" istektir
            and _degisenin_oznesi(ham, k) for k, x in enumerate(ham)):
        return True                                            # tur 23 (O9): "karar verildi ama değişebilir", "2 olsun, belki değişir";
                                                               # tur 24 (O2): "tarih değişebilir" değil
    for i, w in enumerate(ham):
        j = i - 1
        while j > 0 and ham[j] in _KARARSIZLIK_ARASI:
            j -= 1                                             # "pencere renginde karar veremedik", "iç kapıda hâlâ emin değiliz"
        if not cati and j >= 0 and (ham[j].endswith(("de", "da", "te", "ta")) or ham[j] in ("konusunda", "hakkinda", "icin")) \
                and any(_yer_koku(x) for x in ham[max(0, j - 2):j + 1]):
            continue                                           # "iç kapı modelinde kararsızız": o konunun kararsızlığı; tur 16 (O-D):
                                                               # "mutfak tamam ama kararsızız" seçimin kararsızlığıdır
        sonraki = ham[i + 1] if i + 1 < len(ham) else ""
        dolayli = soru and konulu and _konulu_soru_sozu(ham, i)    # tur 23 (O1), tur 24 (Y1): "teslim ne zaman olur bilmiyoruz" bilgi
                                                                   # sorusudur; "karar veremedik teslim ne zaman?" değil; tur 25 (Y1)
        if w.startswith(_KARARSIZLIK_KOKU) and not sonraki.startswith(("yok", "degil")) \
                and not (dolayli and w.startswith(("bilmiyor", "bilemiy", "bilemed"))):
            return True
        sonraki2 = ham[i + 2] if i + 2 < len(ham) else ""
        if not soru and ((w == "simdilik" and _simdilik_secimde(ham, i))
                         or (w.startswith("gecici") and (
                             (i == 0 and (w != "gecici" or _birimsiz_sayi(ham, i + 1) or sonraki.startswith(("cati", "bu", "boyle", "oyle", "secene"))))
                             or sonraki in ("", "olsun", "kalsin") or sonraki.startswith(("secim", "secil", "karar", "cozum", "tercih"))
                             or (sonraki == "bir" and sonraki2.startswith(("sure", "zaman"))
                                 and (i + 3 >= len(ham) or ham[i + 3] == "icin" or (not konulu and _gecici_secim(ham, i + 3))))
                             # tur 25 (O4): "geçici bir süre böyle kalsın"; tur 26 (O4): "ev geçici bir süre depoda kalsın" değil
                             or (sonraki == "olarak" and not konulu and _gecici_secim(ham, i + 2))   # tur 28 (O4): "pencereler
                                                               # geçici olarak aynı kalsın" pencerelerin sözüdür
                             or (sonraki == "olarak" and (_birimsiz_sayi(ham, i + 2) or sonraki2 in (
                                 "", "olsun", "kalsin", "secelim", "sectik", "secildi", "secilsin", "dusunuyoruz", "bu", "boyle")))))):
            return True                                        # tur 21 (Y1, Y2): "Şimdilik 1 olsun", "2 olsun, geçici olarak"; tur 22 (O5):
                                                               # "ev geçici olarak kullanılacak", "şimdilik sorumuz yok" değil
        if w == "emin" and sonraki.startswith("degil") and dolayli:
            continue                                           # tur 23 (O1): "ne kadar sürede teslim olur emin değiliz"
        if w in ("belli", "net", "kesin") and sonraki.startswith("degil") and not konulu:
            return True                                        # tur 22: "çatı ne olacak henüz belli değil"; tur 23 (O1): "montaj tarihi
                                                               # belli değil" o konunundur
        karar = (w.startswith("karar") and not w.startswith("kararsiz")
                 and not (w.endswith(("dan", "den")) and sonraki.startswith("sonra"))
                 and not sonraki.startswith("sonrasi")
                 and not (soru and sonraki.startswith("asama")
                          and not re.fullmatch(r"asama\w*d[ae](?:y[iu][zm]|l[ae]r|ym[iu]s(?:l[ae]r)?)", sonraki))) \
            or (w.startswith("soz") and i > 0 and ham[i - 1] == "son")        # tur 16 (D-B): "kararsız değiliz"; tur 17: "son söz"; tur 23
                                                                              # (O1): "karar sonrası", "karardan sonra", "karar aşamasında"
        if karar:
            k = i + 1
            while k < len(ham) and k < i + 4 and ham[k] in _KARAR_DOLGU:
                k += 1                                         # tur 17 (Y-B'): "karar yine müşterinin", "karar tamamen müşteriye ait"
            x, ardi, ardi2 = (ham[k:k + 3] + ["", "", ""])[:3]
            zaman = (x.startswith(_KARAR_ZAMANI) or x in _KARAR_AYI or (x == "o" and ardi.startswith("zaman"))) and not any(
                _verildi(ham, m) or _KARAR_KESIN.fullmatch(ham[m]) for m in range(k + 1, min(len(ham), k + 5)))
            if x.startswith("yok") or _karar_sahibi(x, ardi, ardi2) or "ait" in ham[i + 1:i + 4] or zaman \
                    or re.fullmatch(r"asama(?:s[iu]n)?d[ae](?:y[iu][zm]|l[ae]r|ym[iu]s(?:l[ae]r)?|d[iu]r)?", x):   # tur 26 (O4):
                                                               # "aşamasından çıktık" değil; tur 27 (O8): "aşamasındalar", "-ymış"
                return True                                    # tur 16 (Y-B): "karar yok", "son karar müşterinin", "karar müşteride";
                                                               # tur 25: "karar aşamasındayız"
            if any((_KARAR_VERECEK.fullmatch(v) and not (soru and re.fullmatch(r"(?:bildir|soyle|ilet)\w*(?:[ae]c[ae]g[iu]z|[iu]r[iu]z|[ae]l[iu]m)", v)))
                   or re.fullmatch(r"degis\w*[ae]bil\w*", v) for v in _karar_penceresi(ham, i)) \
                    or (ham[i + 1:i + 2] and ham[i + 1] in _KARAR_EMRI) \
                    or (ham[i + 1:i + 2] in (["siz"], ["sizler"]) and ham[i + 2:i + 3] and ham[i + 2] in _KARAR_EMRI):
                return True                                    # tur 17 (Y-B'), tur 18: "kararı müşteri verecek", "son karar yarın verilecek",
                                                               # "kararı müşteri söyleyecek"; "kararımızı verebildik", "veriyoruz" değil
        for x in ham[i + 1:i + 3] if (w == "emin" or karar) else ():
            if x.startswith("degil") or (_OLUMSUZ_FIIL.fullmatch(x) and (w == "emin" or x.startswith(_KARAR_FIILI))):
                return True
    return False


# tur 16 (O-F, O-I): "<-e> göre/bağlı/bakarak" seçimi başka bir şeye bağlar; plana, çizime, ölçüye, planın bir yerine ya da bize göre
# ("bana göre") ve ardından değer sözü ("fiyata göre en uygunu bu") gelen bağ gerekçedir; "ona/buna göre" `_ERTELEME_SOZU`'nda
_GORE_DISI = ("plan", "cizim", "olcu", "gorsel", "resim", "eskiz", "proje", "katalog", "sekil", "pdf", "bana", "bize", "ona", "buna",
              "suna", "bence", "bizce", "sizce", "kural", "standar",
              # tur 17 (O-O): evin ve yerin değişmeyen bir özelliğine göre ("manzaraya göre 120x180", "oluk rengi çatıya göre", "duvar
              # rengine göre") gerekçedir; bekleyen bir şeye (fiyat, bütçe, müşteri, durum, cevap) göre değil
              "cati", "duvar", "renk", "reng", "manzara", "gunes", "egim", "yon", "yola", "yolun", "arazi", "zemin", "iklim", "ruzgar",
              "deprem", "yonetmelik", "cephe", "bahce", "isig", "isik", "golge", "oner", "tavsiye", "taslag", "taslak", "ornek")
_GORE_DEGER = ("en", "daha", "uygun", "iyi", "mantik", "makul", "dogru", "guzel")
# tur 17 (O-L): değer sözünden sonra zaman ("fiyata göre daha sonra", "en geç", "en son") ya da olasılık ve bizim fiilimiz ("daha uygun
# olabilir", "en uygun olanı seçeriz") bağı gerekçe yapmaz
_GORE_ZAMAN = ("sonra", "gec", "son", "once", "erken", "yarin", "ileri")
# tur 18 (Orta 5): ölçülü istekte gerekçe yalnız evin ve yerin değişmeyen özelliği; öteki her söz ("duruma", "cevaba", "hanıma göre
# 120x180") koşuldur. Geçmiş seçim fiili yalnız seçmeyi anlatırsa kesindir ("seçtik", "karar verdik"; "dedik", "düşündük", "artık" değil)
_GORE_SABIT = ("cati", "duvar", "renk", "reng", "manzara", "gunes", "egim", "yon", "yola", "yolun", "arazi", "zemin", "iklim", "ruzgar",
               "deprem", "yonetmelik", "cephe", "bahce", "isig", "isik", "golge", "standar", "kural", "olcu", "plan")
_SECTIK = re.compile(r"(?:sec|belirle|kararlastir|tercih|ver|ett|al|yap|kil|anlas|uzlas|bul)\w*(?:tik|dik|tuk|duk|tim|dim)")


# tur 20: setin seçeneğini de anan konu adları ("modeli sonra seçeriz" çatının da seçimi olabilir); göre bağında kesin konu sayılmaz
_SET_ANAN_KONU = ("model", "tip", "marka", "cins", "kat", "usta", "ekip")
# tur 22 (O1): "isteriz"in sabit gerekçesi ("kar yüküne göre güçlendirme isteriz"); bekleyen şey (fiyat, bütçe, durum, cevap) değil
_ISTEK_GEREKCESI = ("yuk", "sicaklik", "soguk", "sogug", "nem", "deniz", "kullanim", "hava")
# tur 23 (O5): belirsiz ad ("başka", "değişik bir şey", "ek", "ilave"); ardından somut ad gelen "ek / ekstra / farklı" ("ek kolon",
# "farklı profil") isteğin kendisidir


def _belirsiz_istek(ardi: list[str]) -> bool:
    for j, x in enumerate(ardi):
        s = ardi[j + 1] if j + 1 < len(ardi) else ""
        if x.startswith(("degisik", "baska", "sey", "bisey")) \
                or (x in ("ek", "ilave", "ekstra", "farkli") and (s in ("", "bir", "bi") or s.startswith(("sey", "bisey", "iste")))):
            return True
    return False


def _gore_bagi(ham: list[str]) -> bool:
    """"<-e> göre", "<-e> bağlı", "<-e> bakarak" ("paranın gelmesine göre", "fiyata göre", "bütçeye bağlı", "duruma bakarak"): seçim
    başka bir şeye bağlıdır (tur 15, O-6; tur 16, O-I; istisnalar `_GORE_DISI`, `_GORE_DEGER`)."""
    for i, w in enumerate(ham[1:], 1):
        if not (w == "gore" or w.startswith("bagli") or w == "bakarak"):
            continue
        o, oo = ham[i - 1], ham[i - 2] if i > 1 else ""
        sonraki = ham[i + 1] if i + 1 < len(ham) else ""
        sonraki2 = ham[i + 2] if i + 2 < len(ham) else ""
        ardi = ham[i + 1:]
        konu = any(x.startswith(_SORU_KONU_ADI) and not x.startswith(("katalog", "katil", "katki", "tipki")) for x in ardi)
        set_ardi = any(x.startswith(("cati", "secene", "alternatif", "opsiyon") + _CATI_AD_KOKU + _SET_ANAN_KONU) for x in ardi)
        konu_kesin = any(x.startswith(_SORU_KONU_ADI) and not x.startswith(_SET_ANAN_KONU) for x in ardi) \
            and not set_ardi                                   # tur 21 (O2): "rengi ve çatıyı"; tur 22: "rengi ve seçeneği"
        olcu = any(re.fullmatch(r"\d+x\d+", x) for x in ardi)
        icerik = any(_yer_koku(x) or x.startswith(_PLAN_ICERIK_KOKU) for x in ardi)
        istek_temeli = (olcu or icerik or o.startswith(_GORE_SABIT + _ISTEK_GEREKCESI) or oo.startswith(_ISTEK_GEREKCESI)
                        or o in ("kar", "kara")) and not set_ardi and not _belirsiz_istek(ardi)   # tur 23 (O5): "nem oranına göre"
        biz = any(x.endswith(_BIZ_FIILI) and not x.endswith(_BIZ_ISTEK_KIPI)
                  and not (j and ardi[j - 1] in ("rica", "talep"))
                  and not (x.startswith("iste") and istek_temeli and not (j and re.fullmatch(r"\w+m[ae]k", ardi[j - 1])))
                  for j, x in enumerate(ardi))                 # tur 21 (O9); tur 22 (O1): "fiyata göre değişiklik isteriz" erteler
        istek_fiili = istek_temeli and any(x.startswith("iste") and x.endswith(_BIZ_FIILI) and j
                                           and not re.fullmatch(r"\w+m[ae]k", ardi[j - 1]) for j, x in enumerate(ardi))
        ertele = (sonraki2.startswith(_GORE_ZAMAN) and not konu_kesin) or any(re.fullmatch(r"(?:ol|degis)\w*[ae]bil\w*", x) for x in ardi) \
            or ((any(x.startswith(_SONRAKI_ZAMAN) for x in ardi) or _biz_ertelemesi(ardi) or (biz and not olcu and not icerik))
                and not konu)                                  # tur 20 (O4): "tavsiyenize göre değiştirmek isteriz"
        # tur 19 (O2): isteğin kendi fiili ("120x180 yapalım", "isteriz", "rica ederiz") ertelemez; konulu erteleme ("oluk rengini sonra
        # seçeriz") o konunundur; ölçüsüz ve konusuz bizim geniş zaman ya da gelecek fiilimiz ("tavsiyenize göre değiştiririz") erteler
        if ertele and not o[0].isdigit() and o.endswith(("a", "e")):
            return True                                        # tur 18 (Orta 5): "eğime göre sonra bakarız", "eğime göre en uygunu bu olabilir"
        deger = sonraki.startswith(_GORE_DEGER)
        if o[0].isdigit() or o.startswith(_GORE_DISI) or _yer_koku(o) or deger \
                or re.fullmatch(r"\w+[dt][iu]g[iu](?:m|n)(?:[iu]z)?[ae]", o) \
                or (re.fullmatch(r"\w+m[ae]s[iu]n[ae]", o) and _yer_koku(oo)):
            continue                                           # tur 16 (O-F): "plana göre", "fiyata göre en uygunu", "kapının açılmasına göre"
        if any(_SECTIK.fullmatch(x) for x in ham[i + 1:]) \
                or (o.startswith(_GORE_SABIT) and any(re.fullmatch(r"\d+x\d+", x) for x in ham[i + 1:])):
            continue                                           # tur 17 (O-O): "manzaraya göre 120x180 olsun", "eğime göre seçtik"; bekleyen
                                                               # konu ("paranın gelmesine göre 120x180") seçimin koşuludur
        if istek_fiili and not ertele:
            continue                                           # tur 21 (O9): "manzaraya göre geniş cam isteriz" isteğin fiilidir
        if konu_kesin and (biz or any(x.startswith(_SONRAKI_ZAMAN) for x in ardi) or _biz_ertelemesi(ardi)):
            continue                                           # tur 20 ara gerileme: "eğime göre oluğu sonra seçeriz" (bağ oluğun)
        if o.endswith(("a", "e")):
            return True                                        # tur 16 (O-I): "müşterinin cevabına göre", "bütçeye bağlı", "duruma bakarak"
    return False


def _is_zamani(g: str, once: list[str], sozler: list[str]) -> bool:
    """Zaman bağı (`g`; önündeki sözler `once`) bizim işimizin zamanı mı (tur 12, tur 13; `_IS_SOZU`)."""
    if _bagli_konu(sozler):
        return False
    o1 = once[-1] if once else ""
    o2 = once[-2] if len(once) > 1 else ""
    if g.startswith(("bit", "tamamlan", "hazirlan", "cizil", "uretil")) or g in ("cizince", "bitirince"):
        return o1 == "" or o1 in _IS_SOZU or o1 in _YUKLEM_SOZU
    if o1 in ("hazir", "musait"):
        return o2 == "" or o2 in _IS_SOZU or o2 in _YUKLEM_SOZU
    return o1.startswith(("vakit", "vaktin", "firsat")) or (g == "gelince" and o1.startswith("sira"))


def _karar_konusu(sozler: list[str]) -> bool:
    """Cümle müşterinin ya da bayinin kararını anıyor mu ("müşteri", "karar", "onay", "cevap"…)."""
    return any(w.startswith(_KARAR_KONU) for w in sozler)


def _kosul_var(ham: list[str], istek: bool = False, ozel: set[str] | frozenset = frozenset()) -> bool:
    """Cümlede seçimi koşula bağlayan söz var mı (`_KOSUL_SOZU`; hakem tur 9, tur 10, tur 11, tur 12). Sorun sözüyle "varsa"dan sonra cümle
    bize bir emirle biterse ("sorun varsa arayın") koşul o emrindir; planın bir yerini anan istekte yalnız "mümkünse", "isterseniz" ve yer
    sözüyle "varsa" ("yer varsa banyoya pencere ekleyin") isteğindir, cümle müşteriyi ya da parayı anmıyorsa (`_bagli_konu`); değiştirme sözü ("itirazı varsa değiştiririz"), öteki "varsa" + emir ("stok
    varsa gönderin") ve emirsiz son ("2 olsun, stok varsa") seçimin koşuludur. Kişi ve yer adı koşul değildir (`_ozel_adlar`)."""
    for i, w in enumerate(ham):
        if not _KOSUL_SOZU.fullmatch(w) or w in _KOSUL_DISI or w in ozel:
            continue
        if istek and not _bagli_konu(ham) and (w in _ISTEK_KOSULU or (w == "varsa" and i > 0 and ham[i - 1].startswith(_ISTEK_VARSA))
                                                or _rica_kosulu(ham, i)):
            continue                                           # tur 12 (O-1), tur 13: istekteki koşul isteğindir ("mümkünse yatak odası 2 …");
                                                               # tur 14 (Orta-1), tur 15 (O-1): "… 120x180 yapabilirseniz sevinirim"
        if w == "varsa" and 0 < i < len(ham) - 1 and _emirle_biter(ham) and ham[i - 1].startswith(_VARSA_KONU) \
                and not any(x.startswith("degis") for x in ham[i + 1:]):
            continue
        if (w == "olsa" and i > 0 and ham[i - 1] in ("da", "de")) or (i + 1 < len(ham) and ham[i + 1] in ("desin", "olsun", "bile")
                                                                       and ham[i + 1][:2] == w[:2]):
            continue                                           # ödünleme: "pahalı da olsa", "ne derse desin", "ne olursa olsun"
        return True
    return False


_IS_KOSULU_FIILI = ("degis", "kesinles", "netles", "sec", "donebil", "doner", "gecebil", "geceri")
_IS_KOSULU_KONUSU = _KARAR_DISI_IS + ("tarih", "gun", "siparis", "renk", "reng", "montaj", "nakliye", "teslim")
_IS_ARASI = ("ne", "zaman", "nasil", "sonra", "de", "da", "yine", "hala", "bir", "daha", "tekrar", "mi", "mu")


def _zaman_siniri_disi(ws: list[str]) -> list[str]:
    """Zaman sınırı düşülmüş sözler (tur 25, O6): "teslime kadar", "montaj gününe kadar" (tamlamanın başı da), "teslimden önce",
    "montajdan sonra", "sipariş sonrası" sınırdır; yalın "sonra", "daha sonra", "sonradan" zarftır."""
    out: list[str] = []
    for n, a in enumerate(ws):
        s = ws[n + 1] if n + 1 < len(ws) else ""
        if a in ("kadar", "sonra", "once", "sonradan", "daha", "sonrasi", "oncesi"):
            continue
        if (s == "kadar" and re.search(r"[ae]$", a)) or (s in ("sonra", "once") and re.search(r"[dt][ae]n$", a)) \
                or s in ("sonrasi", "oncesi"):
            if re.search(r"s?[iu]n(?:[ae]|d[ae]n)$", a) and out:
                out.pop()                                      # "montaj gününe kadar": tamlamanın başı
            continue
        out.append(a)
    return out


def _is_kosulu_disi(ham: list[str]) -> bool:
    """İş koşullu soru çatıya ya da seçime mi dokunuyor (tur 22, O2; tur 23, O3): çatının kendisi ("imzalarsak çatıyı değiştirebilir
    miyiz?"; "çatı malzemesi ne zaman gelir?" değil), vazgeçme ya da öznesi konu olmayan değişiklik ("plan değişir mi?"; "teslim tarihi
    değişir mi?", "montaj tarihini seçebilir miyiz?", "hangi ödeme seçenekleri var?", "bize ne zaman dönersiniz?" değil)."""
    for k, x in enumerate(ham):
        s = ham[k + 1] if k + 1 < len(ham) else ""
        if x.startswith(("cati",) + _CATI_AD_KOKU) and not _konu_adi(s):
            return True
        if x.startswith(("vazgec", "iptal", "cayma")):
            return True
        if not x.startswith(_IS_KOSULU_FIILI) or x.startswith("secene") or re.search(r"(?:s[iu]n[iu]z|s[iu]n|n[iu]z)$", x):
            continue
        bas = max([m + 1 for m in range(k) if re.fullmatch(r"\w+s[ae]k", ham[m])] + [0])
        onu = [a for a in _zaman_siniri_disi(ham[bas:k]) if a not in _IS_ARASI][-2:]   # koşulun kendi nesnesi ("kaporayı yatırırsak")
                                                                                       # sayılmaz; tur 24 (O7), tur 25 (O6): zaman sınırı
        if not any(_konu_adi(a) or a.startswith(_IS_KOSULU_KONUSU) for a in onu):
            return True
    return False


def _is_kosulu(ham: list[str]) -> bool:
    """Cümledeki her koşul birinci çoğul kişinin işimizdeki adımı mı ("kapora yatırırsak", "ödemeyi taksitle yaparsak", "sözleşmeyi
    imzalarsak"; tur 21, O8): süreç sorusudur, seçimin koşulu değildir."""
    kosul = [x for x in ham if _KOSUL_SOZU.fullmatch(x) and x not in _KOSUL_DISI]
    return bool(kosul) and all(re.fullmatch(r"\w+s[ae]k", x) for x in kosul) and any(x.startswith(_KARAR_DISI_IS) for x in ham) \
        and not _is_kosulu_disi(ham)                         # tur 22 (O2): "imzalarsak çatıyı değiştirebilir miyiz?"


def _rica_kosulu(ham: list[str], i: int) -> bool:
    """Koşul (`ham[i]`) isteğin ricası mı (tur 14, tur 15; `_RICA_FIILI`, `_RICA_SOZU`): isteğin kendi fiili, önünde ölçü ya da planın
    bir yeri, ardından (pekiştirme atlanır, `_RICA_ARASI`) nezaket sözü ("120x180 yapabilirseniz sevinirim", "120x180 olursa çok iyi olur")."""
    w, onceki = ham[i], ham[i - 1] if i > 0 else ""
    kok = next((k for k in _RICA_FIILI if w.startswith(k)), None)
    if kok is None or re.search(r"m[ae]z?s[ae]", w[len(kok):]):
        return False                                           # tur 16 (O-H): "120x180 olmazsa iyi olur"
    j = i + 1
    while j < len(ham) and j < i + 3 and ham[j] in _RICA_ARASI:
        j += 1
    sonraki, sonraki2 = (ham[j:j + 2] + ["", ""])[:2]
    rica = sonraki.startswith(_RICA_SOZU) or (sonraki in ("iyi", "hos", "guzel") and sonraki2.startswith("ol"))
    if any(x.startswith(_RICA_OLUMSUZ) or _OLUMSUZ_FIIL.fullmatch(x) for x in ham[j + 1:j + 3]):
        return False                                           # tur 16 (O-H): "memnun olmayız", "iyi olmaz"
    return rica and (any(c.isdigit() for c in onceki) or bool(_yer_koku(onceki)))


def _emirle_biter(sozler: list[str]) -> bool:
    """Cümle bize bir emirle mi bitiyor ("… arayın", "… haber verin", "… ekleyin"; "olsun" değil)."""
    son = sozler[-1] if sozler else ""
    return son.endswith(("in", "iniz", "un", "unuz")) and not son.endswith(("sin", "sun"))


def _onay_ertelenmis(ham: list[str]) -> bool:
    """Onay kökü taşıyan söz ertelenmiş ya da olumsuz mu (hakem tur 10 Y-1, tur 11 O-1): "onaylamadı", "onaylanmadı", "onaylayacak",
    "onaylayınca", "onayladıktan sonra", "onayından sonra", "onaylarsa", "onay alalım", "onayını bekliyoruz", "onayı gelince"."""
    for i, w in enumerate(ham):
        if not w.startswith("onay"):
            continue
        if _ONAY_OLUMSUZ.fullmatch(w):
            return True                                        # tur 12 (Y-1): "onaylayamadık", "onaylatmadık", "onaylanamaz"
        if re.fullmatch(r"onayl[ae]s[iu]n\w*", w) or (re.fullmatch(r"onay(?:[iu]|[iu]n[iu]|lar[iu])?", w) and _gerek_ardi(ham, i)):
            return True                                        # tur 23 (Y2): "müşteri onaylasın", "müşterinin onayı lazım"
        for j in range(i + 1, min(i + 4, len(ham))):
            x = ham[j]
            if x.startswith(("gerek", "lazim", "sart")) and re.fullmatch(r"onay(?:[iu]|[iu]n[ae]|[iu]n[iu]|lar[iu])?", w):
                break                                          # tur 25 sonrası: "müşterinin onayı gerekmiyor", "onayına gerek yok"
                                                               # gerekmeyen onaydır, verilmeyen onay değil ("onaylamaya gerek yok" değil)
            if x.startswith(_CEKINCE_KOKU) and not x.startswith(_CEKINCE_DISI):
                return True                                    # tur 13 (Yüksek-2): "onaydan vazgeçtik", "onaylamakta tereddüt ediyoruz"
            if (x == "yok" or x.startswith("degil") or _OLUMSUZ_FIIL.fullmatch(x)) \
                    and not (any(y.startswith(_OLUMSUZ_DISI) for y in ham[i + 1:j]) and x.startswith(_YOKLUK_SOZU)):
                return True                                    # tur 12 (Y-1, Y-3): "onay yok", "onaylamak istemiyoruz", "onay vermedi";
                                                               # tur 13 (Orta-1): "onaylıyoruz başka değişiklik istemiyoruz" onaydır;
                                                               # tur 14 (Düşük): "onaylamaya hazır değiliz", "onay isteğimize cevap vermediler"
        if any(x in w for x in ("acak", "ecek", "acag", "eceg")) or (_ZAMAN_BAGI.fullmatch(w) and not _ZAMAN_DISI.fullmatch(w)) \
                or (_KOSUL_SOZU.fullmatch(w) and w not in _KOSUL_DISI):
            return True
    return bool(_ONAY_ERTELEME.search(" ".join(ham)))


def _haber_bilgisi(sozler: list[str], zaman: bool = False) -> bool:
    """"Haber veririz" bilgi mi (konusu montaj, teslim, tarih, fiyat …) erteleme mi. Hakem tur 9 (Y-3): çatı ya da karar da
    bildirilecekse ("montaj tarihi ve çatıyı haber veririz", "kesin çatıyı …") ya da haber bir koşula bağlıysa ("fiyatına göre")
    erteleme. Tur 10: zaman bağı ("kesinleşince") fiyata bağlıysa ("fiyatı gelince haber veririz") erteleme, montaj ya da tarihe
    bağlıysa ("montaj tarihini kesinleşince bildiririz") bilgi."""
    return any(w.startswith(_HABER_KONU) for w in sozler) and not any(w.startswith(("cati", "karar", "gore")) for w in sozler) \
        and not (zaman and any(w.startswith(("fiyat", "ucret", "tutar", "maliyet", "teklif")) for w in sozler))


def _erteleme_var(sozler: list[str], istek: bool = False) -> bool:
    """Cümlede kararı erteleyen ya da bize bırakan söz var mı (`_ERTELEME_SOZU`). Bilgi veren haber ("montaj tarihini haber veririz"),
    emir kipi ("bize bildirin"; çatı sözüyle değil: "Çatıyı siz bildirin" bize bırakır) ve "çatıya gelince" ("çatı konusunda") sayılmaz
    (hakem tur 9, tur 10)."""
    metin = " ".join(sozler)
    haber = bool(_HABER_SOZU.search(metin))
    cati = any(w.startswith("cati") for w in sozler)
    for e in _ERTELEME_SOZU.finditer(metin):
        g = e.group(0)
        if _HABER_EMRI.fullmatch(g) and not cati:
            continue
        if _HABER_SOZU.fullmatch(g) and _haber_bilgisi(sozler):
            continue
        if g.startswith("bekl") and (g.startswith(("beklemeden", "beklenen", "bekletme"))
                                     or not any(w.startswith(_BEKLEME_KONU)
                                                and not re.fullmatch(r"onayl\w*(?:[iu]yor[iu][zm]|d[iu][km]|nd[iu])", w) for w in sozler)):
            continue                                           # tur 11 (O-2): "teklifi bekliyoruz", "beklemeden çizin"; tur 28:
                                                               # "onaylıyoruz, teklif bekliyoruz" onaydır
        if g in ("ona gore", "buna gore") and not any(
                w.endswith(("riz", "ruz", "rim", "rum", "cegiz", "cagiz", "ecek", "acak", "elim", "alim")) for w in metin[e.end():].split()):
            continue                                           # tur 11 (O-2): "ona göre fiyat verin" emirdir; "ona göre seçeriz" ertelemedir
        if istek and _betim_zamani(g, metin[:e.start()].split(), sozler, metin[e.end():].split()):
            continue                                           # tur 12 (O-3), tur 13, tur 14: istekteki betim ("kapıdan girince soldaki …")
        if _ZAMAN_BAGI.fullmatch(g):
            once = metin[:e.start()].split()
            onceki = once[-1:]
            if _ZAMAN_DISI.fullmatch(g) or (_emirle_biter(sozler) and _is_zamani(g, once, sozler)):
                continue                                       # tur 11, 12, 13: "hazır olunca haber verin" bizden istenen işin zamanıdır
            if g == "gelince" and onceki and onceki[0].startswith("cati"):
                continue
            if haber and _haber_bilgisi(sozler, zaman=True):
                continue
        return True
    return False


# tur 29 (Y4, Y5): seçimi erteleyen kısa söz ("sonra", "şimdi değil", "bekliyoruz", "acele yok") ve bekleyip görme sözü ("bakalım",
# "görelim", "ona göre"): seçim kaydedilmez, sorulur
_BEKLE_GOR = {"bakalim", "gorelim", "bakariz", "goruruz", "konusuruz", "konusalim", "bakacagiz", "gorecegiz", "bakarsiniz"}
_ERTELE_KALIBI = {"sonra", "sonraya", "sonrasi", "degil", "simdi", "simdilik", "acele", "yok", "yarin", "aksam", "aksama", "haftaya",
                  "ona", "gore", "daha", "biraz", "bir", "bi", "ama", "fakat", "ancak", "ve", "hele", "hadi", "bakalim", "olsun", "kalsin",
                  "evin", "kendi", "cati", "catisi", "numara", "numarali", "nolu"}
_ERTELE_IPUCU = ("sonra", "degil", "acele", "yarin", "aksam", "haftaya", "bekl")
_RAZI_KOSULU = ("olmasi", "olmali", "olacak", "olacaklar", "olursa", "olsa", "olmazsa", "olacagini", "degil", "olmadi", "olmaz", "olmuyor",
                "edecek", "ederse")


_BEKLE_DISI_KOKU = ("diger", "baska", "konu", "detay", "ayrinti", "kalan")
_FIYAT_KOKU = ("fiyat", "ucret", "masraf", "bedel")


def _bekle_disi(w: str) -> bool:
    """Bekleyip görme sözünü seçimden ayıran öteki konu (tur 30 ara gerileme): "diğer konuları sonra konuşuruz", "montajı konuşuruz".
    Fiyat konu sayılmaz: "fiyatına bakalım" seçimi bekletir."""
    return (_konu_adi(w) and not w.startswith(_FIYAT_KOKU)) or w.startswith(_KARAR_DISI_KONU + _BEKLE_DISI_KOKU) or bool(_yer_koku(w))


def _bekle_gor(ham: list[str], secim, tum: list[str] = ()) -> bool:
    """Cümle seçimi erteliyor mu (tur 29): yalnız erteleme sözüyle kurulmuş kısa söz ("sonra", "ama sonra", "şimdi değil", "bekliyoruz",
    "acele yok"), bekleyip görme sözü ("teklif gelsin bakalım", "teklifi görelim") ya da koşullu rıza ("müşteri razı olması lazım").
    "Teklif bekliyoruz", "sonra teklifi gönderin" değil. Tur 30 ara gerileme: öteki konuyu ("diğer konuları sonra konuşuruz") ya da
    mesajda bildirilmiş onayı ("müşteri onayladı, ekibimizle bakacağız") bekleyen söz seçimi bekletmez; karşıtlık ya da fiyat sözü varsa
    ("beğendi ama fiyatına bakalım") bekletir."""
    if (any(w in _BEKLE_GOR for w in ham) or ham[-2:] in (["ona", "gore"], ["buna", "gore"])) and not any(map(_bekle_disi, ham)) \
            and not (_secim_bildirildi(list(tum) or ham)
                     and not any(w in ("ama", "fakat", "ancak") or w.startswith(_FIYAT_KOKU) for w in ham)):
        return True                                            # "teklif gelsin ona göre"; "ona göre fiyat verin" değil
    if any(w == "razi" and n + 1 < len(ham) and ham[n + 1].startswith(_RAZI_KOSULU) for n, w in enumerate(ham)):
        return True
    kalan = [w for w in ham if not (secim(w) or w in _HITAP_SOZU or w in _YUKLEM_SOZU)]
    return bool(kalan) and all(w in _ERTELE_KALIBI or re.fullmatch(r"bekl\w*", w) for w in kalan) \
        and any(w.startswith(_ERTELE_IPUCU) for w in kalan)


def _plan_cumlesi(h: str) -> bool:
    """Çatı sözü olmadan planı anan, kendi yüklemi olan söz ("plan aynı kalsın", "planı değiştirmeyin"; hakem tur 8, D1): seçim cümlesine
    virgülsüz bağlanırsa ("Plan aynı kalsın çatı K olsun") yüklemden sonra ayrılır; plan sözü çatının adını taşımaz."""
    sozler = CO.norm(h).split()
    return any(w.startswith("plan") for w in sozler) and not any(w.startswith("cati") for w in sozler) \
        and any(w in _YUKLEM_SOZU or CO._KALSIN_T.fullmatch(w) for w in sozler)


def _acik_secim(h: str, katalog: Katalog, taban: dict, st: dict) -> bool:
    """Cümle tek başına açık bir çatı seçimi mi (hakem tur 8, Y2): yalnız seçim sözcüklerinden kurulmuş (setin kodu, yalın numarası,
    etiket harfi, sıra sözü, çatı ve bağlam sözü, hitap) ve kodu, etiketi ya da çatı sözü, yoksa yüklemi var ("K olsun", "Çatı K", "2
    olsun", "Çatı 2.", "PA-06-K"). "Son olarak teşekkürler", "PA-06 müşterisi", tek başına "2" ve eksiltili devam açık seçim değildir."""
    kod, sozler, harfler, numaralar, sira = _secim_sozleri(h, katalog, taban, st)
    if _eksiltili(h) or not all(w in numaralar or w in harfler or w in sira or w in _CATI_BAGLAM or w.startswith("cati") or w in _NUMARA
                                or _nezaket(w) for w in sozler):
        return False
    secim = kod or any(w in numaralar or w in harfler or w in sira for w in sozler)
    guclu = kod or any(w in harfler or w.startswith("cati") or w in _YUKLEM_SOZU for w in sozler)
    return (secim and guclu) or (_kendi_catisi_cumlesi(sozler) and any(w.startswith("cati") for w in sozler))


def _kendi_yuklemi(h: str) -> bool:
    """İstek cümlesinin kendi yüklemi ya da kendi sayısı, ölçüsü var mı ("yatak odası 2 penceresi 120x180", "dışlar 140'lık", "banyoya
    pencere ekleyin"). "banyo", "yatak odası sayısı" gibi yüklemsiz ve sayısız söz önceki sayının devrik cümlesidir ("2 olsun banyo"):
    ayrılmaz. Adet sayısı ("banyo 2 tane", "pencere 2 adet") kendi sayısı değildir (hakem tur 8, O3)."""
    sozler = CO.norm(h).split()
    return any(w[:1].isdigit() and not (i + 1 < len(sozler) and sozler[i + 1].startswith(("tane", "adet"))) for i, w in enumerate(sozler)) \
        or any(w in _YUKLEM_SOZU or w.startswith(_ISTEK_FIILI) for w in sozler)


def _cati_adimi_on_okuma(metin: str | None, katalog: Katalog, taban: dict, st: dict) -> str:
    """İE-42 (hakem tur 6, tur 7): onaydan sonraki çatı setinde mesaj okunmadan önce bayinin yazımı düzenlenir (sözcük eklenmez):
    - setin çatı kodu tire ya da boşlukla yazılmışsa ("PA-06K", "pa 06k", "PA06-K") gösterimine çevrilir ("PA-06-K"; tur 6, O1);
    - tek başına "N." ve ardından istek, mesajda ayrı bir seçim cümlesi varsa maddeye katılır ("2 olsun. 2. yatak odası penceresi …" → "2
      yatak odası penceresi …"); seçim cümlesi yoksa katılmaz, `_cati_atiflari` sorar (tur 7, Y1, Y2: numaralı listede çatı yanlış
      okunuyordu; tur 6'nın oda sözüne bakan birleştirmesi kalktı);
    - seçim cümlesi istek cümlesine virgülsüz bağlanmışsa yüklemden sonra ayrılır ("K olsun ama yatak odası 2 penceresi 120x180 olsun" →
      "K olsun, yatak odası 2 penceresi 120x180 olsun"; tur 6, Y1). Sol yan istek değil ve seçim sözü taşıyor; sağ yan istek, kendi
      yüklemi, sayısı ya da ölçüsü var ve çatı adı taşımıyor (tur 7, Y3: "2 olsun banyo", "3 olsun yatak odası sayısı" devrik cümledir;
      "3 olsun yalnız cumba yatak odasının üstünde olsun" koşullu seçimdir: ayrılmaz, sorulur);
    - istek cümlesinden sonra virgülsüz gelen seçim de ayrılır ("yatak odası 2 penceresi 120x180 olsun 2 olsun"; tur 7, Y4);
    - yüklemden sonraki hitap ve teşekkür seçim cümlesinde kalır ("K olsun eline sağlık mutfak …"; tur 7, D3). Soru cümlesi ayrılmaz.
    Virgüllü yazımla aynı okuma: çatı seçilir, istek aynı revizyonda uygulanır."""
    m = metin or ""
    b = _BASTAKI_SELAM.match(m)
    if b:
        m = m[b.end():]                                        # tur 28: "Merhaba hocam 1 olsun" → "1 olsun"; tur 29: baştaki selam
                                                               # atılır ("Abi nasılsın 1 olsun" selamı istek sanıyordu)
    # tur 28: konuşma dilinde gelecek zaman ("soracam", "bakıcaz", "gelicem") yazı diline çevrilir ("soracağım", "bakacağız", "geleceğim")
    m = re.sub(r"\b(bak|sor|gel|g[öo]r|d[öo]n|kal|ver|bil|de[ğg]i[şs]tir)c([ae])(k|m|z)\b",
               lambda x: x.group(1) + x.group(2) + "c" + x.group(2) + ("k" if x.group(3) == "k" else "ğ" + ("ı" if x.group(2) == "a" else "i")
                                                                    + x.group(3)), m, flags=re.IGNORECASE)   # "bakcak", "sorcam"
    m = re.sub(r"\b(\w{2,}?)[aıeiuü]c([ae])k\b", lambda x: x.group(1) + x.group(2) + "c" + x.group(2) + "k", m)   # "bakıcak"
    m = re.sub(r"\b(\w{2,}?)[aıeiuü]c([ae])(m|z)\b",
               lambda x: x.group(1) + x.group(2) + "c" + x.group(2) + "ğ" + ("ı" if x.group(2) == "a" else "i") + x.group(3), m)
    # hakem tur 11 (D-1): "Çatıya gelince" ("çatı konusunda") söylem sözüdür; istek ya da zaman bağı değildir, atılır
    m = re.sub(r"\b[çc]at[ıi](?:ya|\s+konusuna|\s+kısmına|\s+tarafına)\s+gelince\b[\s,:;-]*", "", m, flags=re.IGNORECASE)
    # hakem tur 13 (Düşük, önceden var): "değişiklik istemiyoruz", "değişiklik gerekmiyor" "değişiklik yok" demektir; olumsuz fiil seçimi
    # olumsuzlamaz ("1 olsun, onaylıyoruz, değişiklik istemiyoruz" soruluyordu)
    # tur 15 (O-3): "çatıda değişiklik istemiyoruz" da çevrilir; çatıya bağlı "değişiklik yok" evin kendi çatısıdır (`_cati_atiflari`)
    m = re.sub(r"\b((?:ba[şs]ka\s+)?(?:bir\s+)?de[ğg]i[şs]iklik)\s+(?:istemiyoru[mz]|istemeyiz|gerekmiyor|gerekmez)\b", r"\1 yok", m,
               flags=re.IGNORECASE)
    for x in st.get("adaylar") or []:
        kod = str(x.get("kod") or "").upper()
        p = re.fullmatch(r"([A-ZÇ]+)(\d+)([A-Z])", kod)
        a = katalog.aday(kod)
        if p is None or a is None:
            continue
        on = r"[\s\-_.]*".join("[çc]" if c == "Ç" else re.escape(c.lower()) for c in p.group(1))
        desen = rf"(?<!\w){on}[\s\-_.]*0*{p.group(2).lstrip('0') or '0'}[\s\-_.]*{p.group(3).lower()}(?!\w)"
        m = re.sub(desen, SC.gosterim(a), m, flags=re.IGNORECASE)

    def istek(x: str) -> bool:
        return bool(_cati_icerik_cumleleri(x, katalog, taban, st))

    # tek başına "N." parçası ardından istek geliyorsa ve mesajda ayrı bir seçim cümlesi varsa ("2 olsun. 2. yatak odası penceresi …",
    # "K olsun\n1. yatak odası 2 penceresi …\n2. kapılar ahşap") "N." maddenin ya da odanın sıra sayısıdır: maddeye katılır. Seçim cümlesi
    # yoksa ("1. yatak odası …\n2. mutfak …") katılmaz; `_cati_atiflari` sorar (hakem tur 7, Y1, Y2; tur 6 Y2).
    parcalar = _cumleler(m)
    numara = [bool(_SIRA_NUMARASI.fullmatch(x)) and n + 1 < len(parcalar) and istek(parcalar[n + 1]) for n, x in enumerate(parcalar)]
    if any(numara) and any(not _SIRA_NUMARASI.fullmatch(x) and not _soru_cumlesi(x) and not istek(x)
                           and _acik_secim(x, katalog, taban, st) for x in parcalar):
        m = "".join(x.strip().rstrip(".") + " " if numara[n] else x for n, x in enumerate(parcalar))

    def bol(h: str, soru: bool = False) -> str:
        for y in _YUKLEM.finditer(h):
            sol, i = h[:y.end()], y.end()
            karsitlik = False
            while True:                                        # bağlaç atılır, hitap ve teşekkür sol yanda kalır
                b = _YUKLEM_BAGLACI.match(h, i)
                if b:
                    karsitlik = karsitlik or CO.norm(b.group(0)).split()[0] in ("ama", "fakat", "ancak")
                    i = b.end()
                    continue
                z = re.compile(r"[ \t]+(\S+)").match(h, i)
                if z and (CO.norm(z.group(1)) in _SECIM_NEZAKET or not CO.norm(z.group(1))):
                    sol, i = sol + z.group(0), z.end()
                    continue
                break
            sag = h[i:]
            if not CO.norm(sol) or not CO.norm(sag):
                continue
            sol_istek, sag_istek = istek(sol), istek(sag)
            sag_sozler = CO.norm(sag).split()
            ilk = (sag_sozler or [""])[0]
            plan_istegi = sag_istek and (soru is False) and any(_konu_adi(w) or _yer_koku(w) or w[:1].isdigit() for w in sag_sozler)
            if not sol_istek and not plan_istegi and not karsitlik and _bitisik_secim(sol, katalog, taban, st) and not _eksiltili(sol) \
                    and not (_SORU_EKI.fullmatch(ilk) or ilk in _BITISIK_DEVAM or ilk.startswith(("diye", "ded", "diy", "der", "dem"))) \
                    and _bitisik_olumlu(sag_sozler):
                return f"{sol}, {bol(sag.lstrip(), soru)}"     # tur 28: virgülsüz seçim + çatı dışı söz ("1 olsun teklifi gönderin", "1
                                                               # olsun ne zaman gelir", "2 olsun müşteri onu beğendi"); virgüllü gibi okunur.
                                                               # Tur 29 (Y1, O1): yalnız olumlu söz ayrılır (`_bitisik_olumlu`); "1 olsun
                                                               # ama sonra", "2 olsun eşine soruyor" ayrılmaz, sorulur
            if soru:
                continue
            # çatı adı taşıyan istek seçimden ayrılmaz ("3 olsun yalnız cumba yatak odasının üstünde olsun"): koşullu seçimdir, sorulur
            cati_istegi = any(w.startswith(_CATI_AD_KOKU) for w in CO.norm(sag).split())
            if (not sol_istek and sag_istek and not cati_istegi and _secim_belirteci(sol, katalog, taban, st) and _kendi_yuklemi(sag)) \
                    or (sol_istek and not sag_istek and not _eksiltili(sag) and _secim_belirteci(sag, katalog, taban, st)) \
                    or (not sol_istek and not sag_istek and ((_plan_cumlesi(sol) and _secim_belirteci(sag, katalog, taban, st))
                                                              or (_plan_cumlesi(sag) and _secim_belirteci(sol, katalog, taban, st)))):
                return f"{sol}, {bol(sag.lstrip())}"
        return h

    return "".join(bol(h, soru=True) if _soru_cumlesi(h) else bol(h) for h in _cumleler(m))


def _bitisik_secim(sol: str, katalog: Katalog, taban: dict, st: dict) -> bool:
    """Virgülsüz yazımın sol yanı açık bir seçim mi: `_acik_secim` ya da sıra zamiri ve yüklem ("ilki kalsın", "ikincisi olsun")."""
    if _acik_secim(sol, katalog, taban, st):
        return True
    sozler = CO.norm(sol).split()
    return any(_SORU_SIRASI.fullmatch(w) for w in sozler) and any(w in _YUKLEM_SOZU for w in sozler) \
        and all(_SORU_SIRASI.fullmatch(w) or w in _YUKLEM_SOZU or w in _CATI_BAGLAM or w.startswith("cati") or _nezaket(w) for w in sozler)


# tur 28: selam ve hitapla başlayan virgülsüz seçim ("Merhaba hocam 1 olsun", "Hocam iyi misiniz 1 olsun"): selamdan sonra ayrılır
_BASTAKI_SELAM = re.compile(
    r"^(\s*(?:(?:merhabalar|merhaba|selamlar|selam|slm|mrb|g[üu]nayd[ıi]n|iyi\s+(?:g[üu]nler|ak[şs]amlar|[çc]al[ıi][şs]malar)"
    r"|kolay\s+gelsin|selam[üu]n\s+aleyk[üu]m)(?:\s+(?:hocam|hoca|abi|abim|abla|usta|ustam|karde[şs]im|reis|bey|efendim))*"
    r"(?:\s+(?:iyi\s*mi(?:siniz|sin)|iyimi(?:siniz|sin)|nas[ıi]ls[ıi]n(?:[ıi]z)?))?"
    r"|(?:hocam|hoca|abi|abim|abla|usta|ustam|karde[şs]im|reis|efendim)\s+(?:iyi\s*mi(?:siniz|sin)|iyimi(?:siniz|sin)|nas[ıi]ls[ıi]n(?:[ıi]z)?)))"
    r"(?:[ \t]*[,.!?]+)?[ \t]+(?=\S)(?!(?:hocam|hoca|abi|abim|abla|usta|ustam|karde[şs]im|reis|bey|efendim|iyi|nas[ıi]l)\b)", re.IGNORECASE)


# tur 29 (hakem Y1, O1, O2): virgülsüz seçimden sonra ayrılan söz yalnız olumludur: teklif isteği ("teklifi gönderin", "teklif atar
# mısınız", "teklif ne zaman gelir"), müşterinin bildirilmiş onayı ("müşteri kabul etti", "onu seçti", "onay verdi"), selam, teşekkür ve
# veda. Öteki her söz (erteleme, bekleme, kararsızlık, başkasına soru, soru biçimli istek) ayrılmaz; cümle bütün olarak okunur, sorulur.
_BITISIK_OLUMLU = {"tamam", "tmm", "evet", "ok", "okey", "olur", "kesin", "kesinlikle", "insallah", "hayirli", "hayirlisi", "olsun",
                   "hayirlara", "musteri", "musterimiz", "musterim", "musteriye", "o", "onu", "bunu", "de", "da", "ve", "onayladi",
                   "onayladilar", "onaylandi", "onayladik", "onayladim", "onayliyoruz", "onayliyorum", "onaylariz", "begendi",
                   "begendiler", "begendik", "secti", "sectiler", "sectik", "istedi", "istediler", "kabul", "etti", "ettiler", "ettik",
                   "edildi", "anlastik", "anlasildi", "son", "karar", "selam", "selamlar", "saygilar", "saygilarimla", "gorusuruz",
                   "gorusmek", "uzere", "tesekkurler", "tesekkur", "ederim", "ederiz", "sagolun", "sagol", "saol", "lutfen", "rica",
                   "simdiden", "mail", "maile", "mailden", "maille", "mailine", "eposta", "whatsapp", "whatsapptan", "wp", "wpden",
                   "watsap", "buradan", "buraya", "bize", "bana", "hemen", "cok", "gercekten", "bayagi", "pek", "onay", "onayi",
                   "onayini", "onayimiz", "onayimizi", "ne", "zaman", "nezaman", "gelir", "gelecek", "teslim"}
_BITISIK_TEKLIF = ("teklif", "pdf", "cizim", "proje", "dosya", "liste", "fiyat")
_BITISIK_TEKLIFLE = {"bekliyoruz", "bekliyorum", "bekleriz", "ne", "zaman", "nezaman", "gelir", "gelsin", "gelecek", "kac", "gunde",
                     "simdi"}
_BITISIK_AT = {"at", "atin", "atiniz", "atar", "atarsiniz", "atarsin", "atarmisin", "atarmisiniz", "atabilir", "atabilirsiniz",
               "atabilirmisiniz", "atabilirmisin", "atsaniz", "atarmsn"}


def _bitisik_olumlu(ws: list[str]) -> bool:
    """Virgülsüz seçimin sağ yanı yalnız olumlu sözden mi kurulmuş (tur 29): teklif isteği, bildirilmiş onay, selam, teşekkür, veda."""
    if not ws:
        return False
    teklif = any(w.startswith(_BITISIK_TEKLIF + ("gonder", "ilet", "yolla", "hazirla")) or w in _BITISIK_AT for w in ws)
    for n, w in enumerate(ws):
        onceki, sonraki = (ws[n - 1] if n else ""), (ws[n + 1] if n + 1 < len(ws) else "")
        istek_fiili = w in _BITISIK_AT or (w.startswith(("gonder", "ilet", "yolla", "hazirla"))
                                           and not re.match(r"(?:gonder|ilet|yolla|hazirla)m[ae]", w))
        if w in _BITISIK_OLUMLU or w in _HITAP_SOZU or istek_fiili or w.startswith(_BITISIK_TEKLIF):
            continue
        if teklif and w in _BITISIK_TEKLIFLE:
            continue
        if w in ("verdi", "verdik", "verdiler", "verildi", "veriyoruz", "veriyorum", "verdim", "veriyor", "veriyorlar") \
                and onceki.startswith(("karar", "onay")):
            continue
        if _SORU_EKI.fullmatch(w) or w in ("misin", "musun"):
            if onceki in _BITISIK_AT or onceki.startswith(("gonder", "ilet", "yolla", "hazirla")):
                continue
            return False
        if (w == "iyi" and sonraki in ("aksamlar", "gunler", "calismalar", "geceler")) or (w == "kolay" and sonraki == "gelsin") \
                or (w in ("aksamlar", "gunler", "calismalar", "geceler", "gelsin") and onceki in ("iyi", "kolay")):
            continue
        return False
    return True


# tur 28: virgülsüz seçimden sonra ayrılmayan devam ("1 olsun da teklif gelsin", "1 olsun ki", "1 olsun veya 2", "1 olsun diye düşündük")
_BITISIK_DEVAM = {"de", "da", "ki", "veya", "yada", "ya", "yoksa", "ile", "gibi", "degil", "mi", "mu", "miyiz", "muyuz", "misiniz",
                  "musunuz", "dersek", "dersin", "dersiniz", "derim", "deriz", "demek", "olmaz", "olmazsa", "olursa", "ise", "ancak"}


# İE-42 (hakem tur 5, Y1, Y3): çatı adı kökleri ve evin kendi çatısını anan söz
_CATI_AD_KOKU = ("kirma", "besik", "cumba", "kalkan")
_KENDI_SOZU = {"kendi", "mevcut", "eski", "oldugu", "ayni"}


def _set_cati_adlari(katalog: Katalog, st: dict) -> dict[str, set[str]]:
    """Açık çatı setinde her seçeneğin adının sözcükleri (kart adı ve şablonun çatı tipi; "Beşik + salonda cumba" → besik, salon, cumba)."""
    out: dict[str, set[str]] = {}
    for x in st.get("adaylar") or []:
        kod = str(x.get("kod") or "").upper()
        a = katalog.aday(x.get("kod"))
        tip = ""
        try:
            yol = katalog.sablon_yolu(a["kod"]) if a is not None else None
            tip = str(((json.loads(yol.read_text(encoding="utf-8")) if yol else {}).get("cati") or {}).get("tip") or "")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            tip = ""
        ad = _cati_adi(a) or str((x.get("sunum") or {}).get("cati_adi") or x.get("cati_adi") or "")
        out[kod] = set(CO.norm(tip.replace("_", " ") + " " + ad).split())
    return out


_PARCA_SECIM_FIILI = ("olsun", "kalsin", "olacak", "sectik", "sectim", "secelim", "secildi", "secilsin")


def _plan_istegi_parcasi(h: str) -> bool:
    """Parça planın bir yerini ya da ölçüsünü anan istek mi ("yatak odası 2 penceresi 120x180 olsun"; tur 21, Y1)."""
    return bool(_OLCU_DESENI.search(h)) or any(w.startswith(_PLAN_ICERIK_KOKU) or _yer_koku(w) for w in CO.norm(h).split())


def _baglac_ardi(parcalar: list[str], n: int) -> list[str]:
    """Bağlaçla biten parçanın (`n`) ardındaki parça; o parça isteği haber veriyorsa ("bir isteğimiz var:", "ricamız şu:") bir sonraki de
    (tur 21 ara gerileme)."""
    ardi = parcalar[n + 1:n + 2]
    if ardi and (ardi[0].rstrip().endswith(":") or any(w.startswith(("istek", "isteg", "rica", "talep")) for w in CO.norm(ardi[0]).split())):
        ardi += parcalar[n + 2:n + 3]
    return ardi


_BAGLAC_CEKINCE_KOKU = ("sonra", "ileride", "belki", "henuz", "bilmem", "insallah")   # tur 23: "1 olsun ama, çatı olacak inşallah"


def _cekince_sozu(ws: list[str], plan: bool, haber: bool) -> bool:
    """Parçada çekince sözü var mı (tur 22, Y2). Planın sırasını anlatan istekte "sonra" ("salondan sonra mutfak gelsin", "girişten sonraki
    oda", "kapının sonrasında", "penceresi sonra açılır olsun") ve "zor" ("penceresi zor açılıyor") çekince değil; isteği haber veren
    parçada ("bunu belki söylemiştik:") olasılık sözü de (tur 23, O2)."""
    son = ws[-1] if ws else ""
    istek_kipi = (son.endswith(("sin", "sun", "in", "un", "iniz", "unuz")) or son in ("olsun", "kalsin")) \
        and not son.startswith(("netles", "belirle", "belirl", "kesinles", "konus", "degis", "karar", "sec", "bak", "dusun", "gorus"))
                                                               # tur 24 (O8): "odalar sonra netleşsin", "banyo sonra konuşulsun"
    for k, w in enumerate(ws):
        o = ws[k - 1] if k else ""
        if w.startswith(_CEKINCE_DISI):
            continue
        if plan and w.startswith("zor") and not w.startswith("zorlan"):
            continue
        if plan and w.startswith("sonra") and (w.startswith(("sonraki", "sonrasi")) or re.fullmatch(r"\w+(?:d[ae]n|t[ae]n|n[iu]n)", o)
                                                or istek_kipi):
            continue
        if haber and w.startswith(_BAGLAC_CEKINCE_KOKU):
            continue
        if w.startswith(_CEKINCE_KOKU + _BAGLAC_CEKINCE_KOKU) or re.fullmatch(r"(?:ol|degis)\w*[ae]bil\w*", w):
            return True
    return False


def _cekincesiz(h: str, haber: bool = False) -> bool:
    """Bağlacın ardındaki parça çekincesiz mi (tur 22, Y2): soru ("çatı olsun mu bilmiyoruz", "çatı ne olacak?"), kararsızlık, koşul,
    erteleme ("çatıyı sonra seçelim", "verandayı sonra konuşuruz") ya da olasılık ("mutfak yeri değişebilir", "isteğimiz olabilir",
    "belki 120x180 olur") taşımaz."""
    ws = CO.norm(h).split()
    return not _soru_cumlesi(h) and not _kararsizlik_var(ws) and not _gore_bagi(ws) and not _erteleme_var(ws, _plan_istegi_parcasi(h)) \
        and not _ertelemeli(ws) and not _biz_ertelemesi(ws) and not _kosul_var(ws, True) and not _onay_ertelenmis(ws) \
        and not _cati_ertelemesi(ws) and not _cekince_sozu(ws, _plan_istegi_parcasi(h), haber)


def _secim_parcasi(h: str, katalog: Katalog, numaralar: dict, harfler: dict, sira: dict) -> bool:
    """Parça setin bir seçeneğini seçim fiiliyle mi anıyor ("2 olsun", "evin kendi çatısı kalsın"; tur 21, Y1)."""
    ws = CO.norm(h).split()
    ref = any(w in numaralar or w in harfler or w in sira or w.startswith(("cati",) + _CATI_AD_KOKU) for w in ws) \
        or bool(_secim_kodlari(h, katalog))
    return ref and any(w.startswith(_PARCA_SECIM_FIILI) for w in ws)


_CATI_ERTELEME_FIILI = re.compile(r"(?:ol|sec|belirle|netles|kesinles|degis)\w*?(?:[ae]c[ae][kg]|[iu]r|[ae]r|[ae]l[iu]m|[ae]bil)\w*")
# tur 23 (Y2): çatının sonra belli olacağı ("çatı kesinleşecek", "çatı müşteriyle netleşecek", "çatı seçilecek") ya da kişinin yapacağı
# seçim ("çatı seçimini müşteri yapacak")
_CATI_BELIRLENECEK = re.compile(r"(?:netles|kesinles|belirlen|secil|netlestir|kesinlestir)\w*[ae]c[ae][kg]\w*")
_KISI_SECIMI = re.compile(r"(?:yap|sec|belirle|netlestir|kesinlestir|onayla)\w*(?:[ae]c[ae][kg]\w*|s[iu]n(?:l[ae]r)?)")


def _cati_ertelemesi(ham: list[str], ardi: list[str] | tuple = ()) -> bool:
    """Çatıyı anan parçada bizim ertelememiz ya da sonraki zamanla seçim fiili var mı ("çatıyı sonra seçelim", "çatı sonra olacak", "çatı
    sonra değişebilir"; tur 22, Y2, Y3); çatının konusu ("çatı rengini sonra seçeriz") değil."""
    if not any(w.startswith(("cati",) + _CATI_AD_KOKU) for w in ham) or any(_konu_adi(w) for w in ham):
        return False
    for k, x in enumerate(ham):
        s = ham[k + 1] if k + 1 < len(ham) else ""
        if x.startswith(_ERTELEYEN_KISI) and ((re.fullmatch(r"\w+(?:y[ae]|[ae])", x) and s.startswith(_SAHIP_FIILI)
                                              and not (_GECMIS_FIIL.fullmatch(s) and _secim_bildirildi(ham[k + 2:] + list(ardi))))
                                             or (re.fullmatch(r"\w+(?:n[iu]n|n[iu]nd[iu]r|d[ae]|t[ae])", x) and s in _SAHIP_ARDI)):
            return True                                        # tur 23 (Y2): "çatı müşteriye kalsın", "çatı seçimi müşterinin"
        if (x == "belli" and s.startswith(("olacak", "olur"))) or _CATI_BELIRLENECEK.fullmatch(x):
            return True                                        # tur 23 (Y2): "çatı belli olacak", "çatı kesinleşecek"
    if any(x.startswith(_ERTELEYEN_KISI) for x in ham) and any(_KISI_SECIMI.fullmatch(x) and not _OLUMSUZ_FIIL.fullmatch(x) for x in ham):
        return True                                            # tur 23 (Y2): "çatı seçimini müşteri yapacak", "çatıyı müşteri seçsin"
    return _biz_ertelemesi([w for w in ham if w not in ("gorusuruz", "gorusmek")]) \
        or (any(w.startswith(_SONRAKI_ZAMAN) for w in ham)
            and any(_CATI_ERTELEME_FIILI.fullmatch(w) and not _OLUMSUZ_FIIL.fullmatch(w) for w in ham))   # "görüşürüz" vedadır; tur 23 (O7):
                                                                                                          # "çatı sonradan değişmeyecek"


# tur 24 (Y2, O1): sayısız seçim sorusu yalnız bu sözlerle (ve setin sözüyle) kurulur; başka ad ("fatura", "PDF", "adres", "randevu")
# taşıyan soru o şeyin sorusudur
_SECIM_SORUSU_SOZU = {
    "mi", "mu", "miyiz", "muyuz", "misiniz", "musunuz", "midir", "mudur", "misin", "musun", "ki", "acaba", "sizce", "bence", "sence",
    "bizce", "bu", "bunu", "buna", "bunlar", "su", "sunu", "boyle", "oyle", "simdilik", "de", "da", "daha", "en", "bir", "iyi", "iyidir",
    "tamam", "uygun", "olur", "olabilir", "olsun", "olsa", "kalsin", "kalsa", "secelim", "secsek", "secsem", "alalim", "alsak", "kalalim",
    "yapalim", "yapsak", "gidelim", "emin", "eminiz", "dogru", "yeterli", "guzel", "mantikli", "degil", "ne", "dersiniz", "dersin",
    "saglam", "dayanikli", "guvenli",
    "diyorsunuz", "evin", "kendi", "kendisi", "secim", "secimi", "secimimiz", "sonra", "sonradan", "ileride", "degistirsek",
    "degistirebilir", "degisebilir", "degistirebiliriz", "gecici", "olarak", "karar", "kararimiz", "kararimizi", "karari", "karardan",
    "musteri", "musterimiz", "esi", "esim", "der", "diyecek", "begenir", "begenecek", "razi", "kabul", "eder", "edecek", "onaylar",
    "onaylayacak", "ister", "sever", "yapiyoruz", "secimimizi", "yine", "hala", "boylece", "boylesi", "hangisi",
    # tur 24 sonrası: hitap ve dolgu ("olur mu abi?", "tamam mı hocam?", "peki olur mu?"), kişiye uygunluk ("bize uygun mu?", "müşteri
    # için iyi mi?") ve ekli yüklem ("uygundur değil mi?")
    "abi", "abim", "abicim", "abla", "ablacim", "hocam", "hocacim", "ustam", "ustacim", "ustamcim", "kardesim", "kardes", "efendim",
    "bey", "beyim", "beyefendi", "hanim", "hanimefendi", "reis", "sef", "dostum", "patron", "patronum", "ya", "yahu", "peki", "hani",
    "yani", "bize", "bizim", "size", "sizin", "icin", "musteriye", "musterinin", "musterimize", "musterimizin", "uyar", "uygundur",
    "tamamdir", "dogrudur", "yeterlidir", "mantiklidir", "guzeldir", "yav", "sorun", "problem", "olmaz", "makul", "duser",
    # tur 25 (Y2, O1, O5): hitap ("olur mu usta?", "aga", "kanka"), yeterlik ve beğeni ("yeter mi?", "en iyisi bu mu?", "hoş mu?"), onay
    # arama ("değil mi?", "sorun yok değil mi?"), seçimin ve kararın kökü ("iyi bir tercih mi?", "onaylayalım mı?"), kişinin görüşü ("ev
    # sahibi beğenir mi?", "müşterim razı olur mu?")
    "usta", "aga", "agam", "kanka", "hoca", "yeter", "iyisi", "olmus", "hos", "super", "cok", "harika", "tabi", "tabii", "evet", "yok",
    "sikinti", "sakinca", "sakincasi", "var", "isabetli", "kotu", "yanlis", "plan", "plani", "edelim", "olmali", "ev", "begenirler",
    "diyor", "dediniz",
    # tur 25 sonrası kendi yoklamamız: "nasıl olur?", "iyi fikir mi?", "müşteri sever mi?", "onaylıyor musunuz?"
    "nasil", "fikir", "fikirdir", "sevecek", "hoslanir", "hoslanacak", "itiraz", "kizar", "dayi", "dayim", "ustat", "ustadim", "haci",
    "amca", "amcam", "is", "gorur",
    # tur 26 (Y3): onay arama ("okey mi?", "tmm mı?"), seçim fiili ("diyelim mi?", "geçelim mi?", "kullanılsın mı?"), kalma ("haliyle mi
    # kalsın?", "mevcut hali mi?"), kıyas ("ikisi de olur mu?", "ucuz mu?"), süreç ("devam mı?"), görüş ("ne düşünüyorsun?", "tavsiye
    # eder misiniz?"), hitap ("kral")
    "okey", "ok", "tmm", "farketmez", "fark", "etmez", "diyelim", "gecelim", "kullanalim", "verelim", "gecsin", "olacak", "uygulansin",
    "kullanilsin", "yapilsin", "alinsin", "haliyle", "aynen", "mevcut", "hali", "eski", "normal", "standart", "ikisi", "ucuz", "pahali",
    "devam", "kral", "dusunuyorsun", "dusunuyorsunuz", "dusunursun", "dusunursunuz", "tavsiye",
    "kolay", "zor", "ikisinden"}                               # tur 28 (Y3): "nakliye için daha mı kolay?"
_HITAP_SOZU = {"abi", "abim", "abicim", "abla", "ablacim", "hocam", "hocacim", "ustam", "ustacim", "ustamcim", "kardesim", "kardes",
               "efendim", "bey", "beyim", "beyefendi", "hanimefendi", "reis", "sef", "dostum", "patron", "patronum", "usta", "aga",
               "agam", "kanka", "hoca", "dayi", "dayim", "ustat", "ustadim", "haci", "amca", "amcam", "kral"}
# tur 26 (Y4): bitişik soru eki ("tamammı", "olsunmu", "onaylıyormusunuz")
_BITISIK_SORU = re.compile(r"(?:tamam|olur|uygun|iyi|yeter|yeterli|dogru|ok|okey|guzel|olmaz|olsun|kalsin|onayliyor|onayli|onaylar)"
                           r"m[iu](?:d[iu]r|y[iu]z)?|(?:onayliyor|onayli|onaylar)m[iu]s[iu]n(?:[iu]z)?")   # tur 27 (O2): "iyimisiniz"
                                                                                                        # selamdır
_SELAM_SORUSU = re.compile(r"(?:iyi|nasil)m[iu]s[iu]n(?:[iu]z)?|nasilsin(?:iz)?|naber|nbr|ne\s?haber")


def _selam_sorusu(ws: list[str]) -> bool:
    """Hal hatır sorusu mu ("iyi misiniz?", "iyimisin", "nasılsınız"; tur 27, O2): ikinci kişiye "iyi" seçimin sorusu değildir."""
    return any(_SELAM_SORUSU.fullmatch(w) or (w == "iyi" and n + 1 < len(ws) and re.fullmatch(r"m[iu]s[iu]n(?:[iu]z)?", ws[n + 1]))
               for n, w in enumerate(ws))


_SELAM_SOZU = {"merhaba", "merhabalar", "mrb", "selam", "selamlar", "slm", "gunaydin", "kolay", "gelsin", "tesekkurler", "tesekkur",
               "ederim", "sagolun", "sagol", "aksamlar", "gunler", "hayirli", "isler", "ellerinize", "saglik", "siz", "sen", "de", "da",
               "ya", "peki"}


def _selamsiz(ws: list[str]) -> list[str]:
    """Hal hatır sorusu ve selam çıkarılmış cümle (tur 28, Y2): "hocam iyi misiniz bu çatı olur mu" → "hocam bu çatı olur mu"; yalnız
    selamsa hitap ve selam sözlerinden başka söz kalmaz."""
    out, n = [], 0
    while n < len(ws):
        if ws[n] == "iyi" and n + 1 < len(ws) and re.fullmatch(r"m[iu]s[iu]n(?:[iu]z)?", ws[n + 1]):
            n += 2
            continue
        if not _SELAM_SORUSU.fullmatch(ws[n]):
            out.append(ws[n])
        n += 1
    return out


def _yalniz_selam(ws: list[str]) -> bool:
    """Cümle selamdan ibaret mi ("Hocam iyi misiniz", "siz iyi misiniz?", "abi iyimisin")."""
    return _selam_sorusu(ws) and all(w in _HITAP_SOZU or w in _SELAM_SOZU for w in _selamsiz(ws))
_OLCUT_ADI_RX = re.compile(r"(?:kar|kis|ruzgar|butce|para|fiyat|deprem|yagmur|sicak|soguk|hava|nem|bolge|iklim)"
                           r"(?:[ae]|y[ae]|n[iu]n|[iu]n|d[ae]|t[ae]|l[ae]r)?")   # tur 26 (O2): "kargo", "karavan", "kişi", "havale" değil
_KISI_SOZU_RX = re.compile(r"musteri\w*|es(?:i|im|imiz|iniz|in|ine|ime|inin|imin|imizin)|hanim\w*|sahib\w*|aile\w*")   # "eşik" değil
_SECIM_SORUSU_CAPA = ("olsun", "kalsin", "kalsa", "olsa", "secelim", "secsek", "secsem", "alalim", "alsak", "kalalim", "yapalim",
                      "yapsak", "iyi", "tamam", "uygun", "olur", "olabilir", "emin", "dogru", "yeterli", "guzel", "mantikli", "begen",
                      "saglam", "dayanikli", "guvenli",
                      "razi", "kabul", "onaylar", "dersiniz", "dersin", "diyorsunuz", "der", "diyecek", "degistir", "degisebilir",
                      "bu", "bunu", "boyle", "oyle", "uyar", "olmaz", "makul", "duser", "yeter", "iyisi", "olmus", "hos", "super",
                      "harika", "evet", "tercih", "sec", "onayl", "tamamla", "degil", "sorun", "sikinti", "sakinca", "isabetli", "kotu",
                      "yanlis", "sever", "sevecek", "ister", "hoslan", "itiraz", "kizar", "gorur",
                      "okey", "ok", "tmm", "farketmez", "diyelim", "gecelim", "kullanalim", "verelim", "gecsin", "olacak", "uygulansin",
                      "kullanilsin", "yapilsin", "alinsin", "haliyle", "aynen", "mevcut", "standart", "normal", "ikisi", "ucuz", "pahali",
                      "devam", "dusun", "tavsiye", "kolay", "zor")
_OLCUT_SOZU = ("acisindan", "bakimindan", "yonunden", "olarak", "icin")
_SECIM_SORUSU_KOKU = ("tercih", "secti", "secil", "secim", "onayl", "tamamla")   # "tercihimiz", "seçtiğimiz", "müşterim"
_HITAP_ARDI = ("bey", "beyim", "hanim", "abi", "abla", "usta", "hocam", "hoca", "kardes", "kardesim")   # "olur mu Ahmet bey?"
_OLCUT_ADI = ("kar", "kis", "ruzgar", "butce", "para", "fiyat", "deprem", "yagmur", "sicak", "soguk", "hava", "nem", "bolge", "iklim")


_SUREC_KOKU = ("plan", "cizim", "proje", "gonder", "teklif", "pdf", "gorsel", "katalog", "zaman", "kadar", "gun", "hafta", "toplam",
               "dahil", "hemen", "simdi", "kac", "fiyat", "ucret", "odeme", "teslim", "fatura", "model", "numara", "gel", "bekle",
               "yapiyor", "yapacag", "sonra")


_KARAR_SORUSU_KOKU = ("onay", "dusun", "sec", "karar", "tercih", "bekle")   # "_KARAR_FIILI" başkadır
_KARAR_DISI_KONU = ("renk", "reng", "tarih", "montaj", "seramik", "fayans", "parke", "teslim", "odeme", "fatura", "kapora", "taksit",
                    "nakliye", "boya", "model", "desen", "ebat", "olcu")
_SUREC_KONUSU = ("plan", "cizim", "proje", "teklif", "pdf", "gorsel", "katalog", "fatura", "odeme", "teslim", "fiyat", "ucret")
_ZAMAN_SOZU = {"hemen", "simdi", "simdilik", "sonra", "bugun", "yarin", "artik", "once", "direkt", "direk", "boyle", "yani"}
_TEYIT_SOZU = {"tamam", "olur", "uygun", "iyi", "yeter", "yeterli", "dogru", "ok", "okey", "tmm", "emin", "olmaz", "peki"}


def _dilek_fiili(w: str) -> bool:
    """İstek ya da gelecek kipiyle birinci çoğul ya da üçüncü tekil emir: "yapalım", "onaylayalım", "yapacağız", "olsun", "gelsin",
    "onaylansın"; "gönderirsin", "gönderiyorsun", "misin" değil."""
    return bool(re.fullmatch(r"\w+(?:[ae]l[iu]m|[ae]c[ae]g[iu]z)", w)
                or (re.fullmatch(r"\w+s[iu]n", w) and not re.fullmatch(r"\w*(?:[aeiu]r|yor|m[iu])s[iu]n", w)))


def _karar_sorusu(ws: list[str]) -> bool:
    """Soru onayın, seçimin ya da ertelemenin kendisini mi soruyor (tur 28, Y1): "hemen onaylayalım mı?", "2 gün düşünelim mi?",
    "şimdi mi seçelim?", "onayı hafta sonu verelim mi?", "hemen mi onaylansın?", "şimdi mi onaylıyoruz?", "onaylayıp gönderelim mi?".
    "onay gönderir misiniz?", "teklifi bekleyelim mi?" ve "onaylıyoruz, teklif ne zaman?" değil."""
    konu = any(w.startswith(_SUREC_KONUSU) for w in ws)
    if not any(w.startswith(("cati",) + _CATI_AD_KOKU) for w in ws) \
            and any((_konu_adi(w) or _yer_koku(w) or w.startswith(_KARAR_DISI_KONU))
                    and not w.startswith(("plan", "cizim", "proje", "teklif", "pdf", "gorsel", "katalog", "onay")) for w in ws):
        return False                                           # tur 29 (O3): "kapı rengini sonra mı seçelim?", "montaj tarihini ne zaman
                                                               # seçelim?" başka konunun kararıdır
    for n, w in enumerate(ws):
        o, s = (ws[n - 1] if n else ""), (ws[n + 1] if n + 1 < len(ws) else "")
        kok = w.startswith(_KARAR_SORUSU_KOKU) and not w.startswith(("secenek", "secim", "kararli")) and not (w.startswith("bekle") and konu)
        ad = (w.startswith(("ver", "yap")) and any(re.fullmatch(r"(?:onay|karar|secim|tercih)(?:[iu]|[iu]n[iu]|[iu]m[iu]z[iu]?|l[ae]r[iu])?", x)
                                                    for x in ws[max(0, n - 3):n]))   # "onayı verelim mi?"; "onayladı ne yapalım?" değil
        if not (kok or ad):
            continue
        if _dilek_fiili(w) or (re.fullmatch(r"\w+yor(?:[iu]z)?", w) and (_SORU_EKI.fullmatch(o) or _SORU_EKI.fullmatch(s)
                                                                          or re.fullmatch(r"m[iu]y[iu]z", s))):
            return True
        if re.fullmatch(r"\w+[iu]p", w) and any(_dilek_fiili(x) for x in ws[n + 1:]):
            return True                                        # "onaylayıp gönderelim mi?"
    return False


def _surec_sorusu(ws: list[str]) -> bool:
    """Soru sürecin, planın ya da selamın sorusu mu (tur 27, O1): "ne zaman?", "kaç gün?", "teklifi gönderir misiniz?", "son plan bu
    mu?", "iyi misiniz?", "2 ve 3 ay mı?"; "ne der / ne düşünüyorsun" kişinin görüşüdür, sürecin değil. Tur 28 (Y1): onayın, seçimin
    ya da ertelemenin sorusu ("hemen onaylayalım mı?", "2 gün düşünelim mi?"), gösterme ("model bu mu?", "bu çatıyla mı gönderelim?"),
    konusuz dilek ("ne yapalım?", "ne olsun?", "gelsin mi?"), teyit ("şimdi tamam mı?"), numara ("1 numara mı?") ve yalnız zaman sözü
    ("şimdi mi?") sürecin sorusu değildir."""
    if _yalniz_selam(ws):
        return True
    if _selam_sorusu(ws):
        ws = _selamsiz(ws)                                     # tur 28 (Y2): "hocam iyi misiniz onaylayalım mı?"
    if _karar_sorusu(ws):
        return False
    konu = any(w.startswith(_SUREC_KONUSU) for w in ws)
    cati = any(w.startswith(("cati",) + _CATI_AD_KOKU) for w in ws)
    zamanli = any((w == "ne" and s in ("zaman", "kadar")) or (w == "kac" and (_birimli(ws, n) or not s))
                  for n, (w, s) in enumerate(zip(ws, ws[1:] + [""])))
    for n, w in enumerate(ws):
        s = ws[n + 1] if n + 1 < len(ws) else ""
        if w in ("bu", "bunu", "buna", "bunla", "bununla", "bunlar", "su", "sunu", "suna", "sunla", "bunun") \
                and (cati or (not konu and (_SORU_EKI.fullmatch(s) or not any(x.startswith(_SUREC_KOKU) for x in ws)))):
            return False                                       # "model bu mu?"; "son plan bu mu?" planın sorusudur (tur 19); tur 29 (O4):
                                                               # "bunu ne zaman gönderirsiniz?", "bu kaça olur?" sürecin sorusudur
        if _dilek_fiili(w) and not konu and not zamanli and not _SORU_EKI.fullmatch(w):
            return False                                       # "ne yapalım?", "kaç numara olsun?"; "ne zaman gelsin?" değil
        if w in _TEYIT_SOZU and (_SORU_EKI.fullmatch(s) or s in ("misin", "musun")) and not konu:
            return False                                       # "şimdi tamam mı?", "hemen olur mu?"
        if w.isdigit() and not _birimli(ws, n) and (not s or s.startswith(("numara", "nolu")) or _SORU_EKI.fullmatch(s)):
            return False                                       # "1 numara mı?"; "2 ve 3 ay mı?", "2+1 ne kadar?", "2. etap" değil
    if all(w in _ZAMAN_SOZU or _SORU_EKI.fullmatch(w) or w in _HITAP_SOZU for w in ws):
        return False                                           # "şimdi mi?", "hemen mi?"
    for n, w in enumerate(ws):
        s = ws[n + 1] if n + 1 < len(ws) else ""
        if w == "ne" and s.startswith(("der", "diye", "dus")):
            continue
        if w.startswith(_SUREC_KOKU) or w in ("ne", "neler", "nedir") or (w[:1].isdigit() and s and not _birimsiz_sayi(ws, n)):
            return True
    return False


def _secim_sorusu(ws: list[str]) -> bool:
    """Sayısız seçim sorusu mu (tur 23, Y3; tur 24, Y2 ve O1: yalnız `_SECIM_SORUSU_SOZU` ile kurulmuş soru): soru ekiyle seçim
    fiili ("kalsın mı?", "bu mu olsun?", "evin kendi çatısı mı kalsın?", "geçici olarak mı seçsek?"), "olur mu?", "tamam mı?", "emin
    miyiz?", "doğru mu?", sonraki değişiklik ("sonra değiştirsek olur mu?"), çatının olurluğu ("çatı olur mu ki?") ya da kişinin görüşü
    ("müşteri ne der acaba?", "ne dersiniz?"). Başka ad ("fatura şirkete mi olsun?", "adres doğru mu?"), konu ya da ölçü taşıyan soru
    ("salon penceresi büyük mü olsun?", "montaj ne zaman olsun?") seçimin değil o konunun sorusudur."""
    if _OLCU_DESENI.search(" ".join(ws)) or _yalniz_selam(ws):
        return False                                           # tur 27 (O2): "Hocam iyi misiniz?" selamdır
    if _selam_sorusu(ws):
        ws = [w for w in _selamsiz(ws) if w not in _SELAM_SOZU or w in ("de", "da")]   # tur 28 (Y2): "Hocam iyi misiniz bu çatı olur mu"
    def olcut(k: int, w: str) -> bool:                    # tur 24 (Y2), tur 25 (O5): "fiyat açısından", "bütçeye göre", "kar için"
        s = ws[k + 1] if k + 1 < len(ws) else ""
        return s in ("acisindan", "bakimindan", "yonunden", "gore") \
            or (s in ("icin", "olarak") and (_konu_adi(w) or bool(_OLCUT_ADI_RX.fullmatch(w))) and w != "kisi")
    for k, w in enumerate(ws):                             # tur 26 (O2): hitap yalnız başta, sonda ya da soru ekinden sonra ("olur mu
        if w in _HITAP_SOZU and not (k == 0 or k == len(ws) - 1 or _SORU_EKI.fullmatch(ws[k - 1]) or ws[k - 1] in _HITAP_SOZU
                                     or ws[k - 1] in ("acaba", "ya", "peki", "ki", "sizce", "sence", "bence", "bizce")
                                     or ws[k - 1].startswith("cati") or _KISI_SOZU_RX.fullmatch(ws[k - 1])):   # usta?"); "montajda
            return False                                       # usta olur mu?" değil; tur 27 (O3): "sizce abi olur mu?", "bu çatı hocam"
    kalan = [w for k, w in enumerate(ws) if not olcut(k, w) and w not in ("acisindan", "bakimindan", "yonunden", "gore")]
    konulu_olcut = any(olcut(k, w) and not _OLCUT_ADI_RX.fullmatch(w) and ws[k + 1] in ("icin", "olarak") for k, w in enumerate(ws))
    if konulu_olcut and not any(w in ("bu", "bunu", "buna", "su", "sunu", "boyle", "oyle", "olsun", "kalsin", "kalsa", "olsa",
                                      "daha", "ikisi", "ikisinden", "en", "iyisi", "mantikli", "uygun", "iyi", "olur", "ucuz", "pahali",
                                      "kolay", "zor")
                                or w[:1].isdigit() or w.startswith(("cati", "sec", "tercih", "hangi") + _CATI_AD_KOKU) for w in kalan):
        return False                                           # tur 27 (O4): "montaj için ne düşünüyorsunuz?" montajın sorusudur;
                                                               # "montaj için bu mu olsun?" seçimin; tur 28 (Y3, O2): kıyas ve değer-
                                                               # lendirme ("nakliye için daha mı ucuz?", "montaj için olur mu?") seçimin
    if kalan and all(w in ("sence", "sizce", "nasil") for w in kalan):
        return True                                            # tur 26 (Y3): "1 olsun, sence?", "1 olsun, nasıl?"
    for k, w in enumerate(kalan):
        if not (w in _SECIM_SORUSU_SOZU or w[:1].isdigit() or len(w) == 1 or w.startswith(("cati",) + _CATI_AD_KOKU + _SECIM_SORUSU_KOKU)
                or _KISI_SOZU_RX.fullmatch(w) or _BITISIK_SORU.fullmatch(w)
                or (k + 2 == len(kalan) and kalan[k + 1] in _HITAP_ARDI) or (w == "sahibi" and kalan[k - 1:k] == ["ev"])):
            return False                                       # tur 24 (O1): "fatura şirkete mi olsun?", "adres doğru mu?"
        if w == "nasil" and not (k + 1 < len(kalan) and kalan[k + 1] in ("olur", "olsun", "olacak", "olmus")):
            return False                                       # tur 26 (O2): "nasıl yapalım?" sürecin sorusudur
        if w == "is" and not (kalan[k - 1:k] in (["bu"], ["su"], ["o"]) or kalan[k + 1:k + 2] == ["gorur"]):
            return False                                       # tur 26 (O2): "iş nasıl olur?"; "bu iş olur mu?", "iş görür mü?" değil
    ek = any(_SORU_EKI.fullmatch(w) or _BITISIK_SORU.fullmatch(w) for w in kalan) or "acaba" in kalan or "nasil" in kalan \
        or any(a == "ne" and b in ("der", "diyecek", "dersin", "dersiniz", "diyorsunuz", "diyor", "dusunuyorsun", "dusunuyorsunuz",
                                   "dusunursun", "dusunursunuz") for a, b in zip(kalan, kalan[1:]))
    return ek and any(w.startswith(_SECIM_SORUSU_CAPA) or _BITISIK_SORU.fullmatch(w) for w in kalan)   # tur 25 (O1): "müşteri ne der?"


_DUZELTME_SOZU = {"pardon", "hayir", "yanlis", "yanlislikla", "ozur", "pardn", "duzeltme", "duzeltiyorum", "veya", "yada", "yahut",
                  "aslinda", "yok"}
_DUZELTME_ARDI = {"olsun", "kalsin", "numara", "numarali", "nolu", "cati", "catisi", "yi", "i", "u", "yu", "olacak", "dedim", "demek",
                  "istedim", "yazdim", "olarak", "ile", "devam", "secenek", "secenegi", "secelim", "sectik", "evet", "tamam"}


def _cati_atiflari(metin: str | None, katalog: Katalog, taban: dict, st: dict) -> tuple[bool, set[str], list[set[str]]]:
    """İE-42 (hakem tur 5, Y1, Y3): onaydan sonraki çatı setinde bu mesajın çatıya atıfları, bayinin sözünden. Seçim okuması (`oku`) yalnız
    tanıdığı cümleyi okur; öteki cümledeki çatı sözü ("1 olsun, kırmayı alın", "1 olsun, K ile devam edelim", "teklifte 2 de olsun",
    "mevcut çatıdan farklı olsun") seçimle çelişebilir. Bu işlev her cümleye bakar (soru cümlesi hariç):
    - istek olmayan cümlede kod, etiket harfi, numara, sıra sözü (yalnız seçim sözcükleriyle kurulmuş cümlede) ve evin kendi çatısı sözü
      seçimin hedefidir; başka/farklı ya da olumsuz sözle birlikte çatı sözü, setin dışındaki numara ya da kod kararsızlıktır;
    - her cümlede çatı adı kökü ("kırma", "beşik", "cumba", "kalkan"; ekli de) adında o kök geçen seçenekleri gösterir.
    Dönen (kararsız, hedefler, ad kümeleri): seçim hedeflerin tek elemanı olmalı ve her ad kümesinde bulunmalı."""
    harfler, numaralar = _set_etiketleri(taban, st)
    tk = str(taban.get("kod") or "").upper()
    son_sira = str(max([int(a.get("sira") or 0) for a in st.get("adaylar") or []] or [0]))
    sira = {**_SIRA_SOZU, "son": son_sira, "sonuncu": son_sira}
    set_kodlari = set(numaralar.values()) | {tk}
    adlar_kod = _set_cati_adlari(katalog, st)
    kendi_yapi = "celik" if tk.startswith(("Ç", "C")) else "prefabrik"
    kararsiz, hedefler, ad_kumeleri, soru_hedefleri, soru_secim, soru_adlari = False, set(), [], set(), set(), []
    secim_dili_sorusu = False
    parcalar = _cumleler(metin)
    tum = CO.norm(metin or "").split()

    def tum_atif(j: int) -> bool:
        x = tum[j]
        return (x in numaralar and not _birimli(tum, j)) or x in harfler or x.startswith(_CATI_AD_KOKU) or bool(_secim_kodlari(x, katalog))
    for n, w in enumerate(tum):                                # tur 29 (Y7): "2 olsun pardon 1", "2 olsun, yanlış yazdım 1", "2 olsun veya
        if (w in _DUZELTME_SOZU or (w == "ya" and n + 1 < len(tum) and tum[n + 1] == "da")) \
                and any(tum_atif(j) for j in range(n)):        # 1": iki numara, hangisi belli değil; "Hayır, 2 olsun" değil
            for j in range(n + 1, len(tum)):
                if tum_atif(j):
                    if all(y in _YUKLEM_SOZU or y in _HITAP_SOZU or y in _DUZELTME_ARDI for y in tum[j + 1:]):
                        kararsiz = True
                    break
    for n, h in enumerate(parcalar):
        if _soru_cumlesi(h):
            w0 = CO.norm(h).split()
            konu_sorusu: list[str] = []
            if _karar_sorusu(_selamsiz(w0)):
                kararsiz = True                                # tur 28 (Y1): "2 olsun, 2 gün düşünelim mi?", "hemen onaylayalım mı?"
            if not _cati_icerik_cumleleri(h, katalog, taban, st, konu_sorusu) and not konu_sorusu and not _surec_sorusu(w0):
                                                               # "son plan bu mu?" planın sorusudur (tur 19); tur 27 (O1): "ne zaman?",
                                                               # "teklifi gönderir misiniz?", "iyi misiniz?" sürecin ve selamın sorusudur
                secim_dili_sorusu = True                       # tur 26 (Y3): "1 olsun, okey mi?", "diyelim mi?", "mevcut hali mi kalsın?"

            def set_sozu(w):
                return w in numaralar or w in harfler or w in sira or w.startswith(("cati",) + _CATI_AD_KOKU) \
                    or bool(_secim_kodlari(w, katalog))
            ayrik = any(_ayrik_secenek(CO.norm(x).split(), set_sozu) for x in parcalar[n:n + 2])
            rica = [w for w in w0 if re.fullmatch(r"(?:degis|cevir|gec|al|kullan|yap)\w*[ae]bil\w*", w)]

            def rica_atfi(k: int, w: str) -> bool:             # tur 28 (O1): oda numarası ("yatak odası 2 penceresini"), birimli sayı
                once, sonra = (w0[k - 1] if k else ""), (w0[k + 1] if k + 1 < len(w0) else "")   # ("3 taksit", "1 hafta") ve sıra
                if w in numaralar:                             # sıfatı ("son olarak", "ilk oda") çatı numarası değildir
                    return not _birimli(w0, k) and not (_konu_adi(once) or _yer_koku(once) or once.startswith("oda")) \
                        and not (_konu_adi(sonra) or _yer_koku(sonra))
                if w in sira:
                    return sonra.startswith(("cati", "secenek", "model"))
                return w in harfler or w.startswith(_CATI_AD_KOKU) or bool(_secim_kodlari(w, katalog))
            def guclu_atif(k: int, w: str) -> bool:            # tur 29 (Y3, Y8): "2'yi aynı fiyata yapabilir misiniz?", "Kırma çatıyı
                sonra = w0[k + 1] if k + 1 < len(w0) else ""   # kaporayla alabilir miyiz?" çatının ricasıdır; "kapıları 2'ye" değil
                if w in numaralar:
                    return not _birimli(w0, k) and (sonra in ("yi", "i", "yu", "u") or sonra.startswith(("numaray", "numarali", "nolu")))
                return w in harfler or w.startswith(_CATI_AD_KOKU) or bool(_secim_kodlari(w, katalog))
            if rica and (any(guclu_atif(k, w) for k, w in enumerate(w0)) or (any(rica_atfi(k, w) for k, w in enumerate(w0))
                    and not any((_konu_adi(w) or _yer_koku(w) or w.startswith(("odeme", "teslim", "tarih", "fatura", "kapora", "taksit")))
                                and not w.startswith(("cati",) + _CATI_AD_KOKU) for w in w0))):
                kararsiz = True                                # tur 27 (Y3): "Çatıyı 2 ile değiştirebilir misiniz?" çatı isteğidir: seti
                                                               # düşürmez, sorulur; tur 28 (Y4): "2'yi yapabilir misiniz?", "Kırma
                                                               # alabilir miyiz?"; başka konunun ricası değil
            if "hangisi" in w0 and not ayrik and not _konu_oncesi(w0, w0.index("hangisi")) \
                    and any(w.endswith(("sa", "se")) or w.startswith(_KARARSIZ_KOKU) for w in w0):
                kararsiz = True                                # hakem tur 8 (O4): "hangisi ucuzsa", "hangisi uygunsa" seçimi bize bırakır
            h = _ODA_BOSLUGU.sub(r"\1+\2", h)                  # tur 15 (D-2): "2 + 1'in" oda programıdır
            h = _ODA_PROGRAMI_SOZ.sub(" ", h)                  # tur 16: "3+1'in fiyatı mı daha yüksek?" çatı numarası değildir
            hq = _IYELIK.sub(" ", h)                           # tur 12 (O-2): "2'nin fiyatı ne olacak?" seçim sorusu değildir
            wq = CO.norm(hq).split()
            hk = _IYELIK_KIYAS.sub(" ", h)
            wk = CO.norm(hk).split()
            if (_karar_konusu(w0) or _bagli_konu(w0)) \
                    and ((_kosul_var(w0, False, _ozel_adlar(h)) and not _is_kosulu(w0)) or _onay_ertelenmis(w0)) \
                    or _musteri_ertelemesi(w0) or _kararsizlik_var(w0, soru=True) or _secim_sorusu(w0):
                kararsiz = True                                # tur 20 (Y3): "1 olsun, müşteri onaylayınca teslim ne zaman olur?"; tur 22
                                                               # (Y3): "çatı ne olacak bilmiyoruz", "müşteri beğenir mi bilmiyoruz"
            if (_set_zamiri(w0) and not ayrik) or _ertelemeli(w0):
                kararsiz = True                                # tur 19 (Y3): "1 olsun, müşteriye soralım mı?", "bir düşünelim mi?"                                # tur 17 (Y-A'): "1 olsun, hangisi olsun?", "2 olsun, başka çatı daha mı iyi?"
            if any(_SORU_EKI.fullmatch(w) or w == "daha" for w in wk):
                soru_secim |= _soru_numaralari(wk, numaralar, harfler)
                soru_secim |= set(_secim_kodlari(hk, katalog)) & set_kodlari   # tur 15 (Y-1): "1 olsun. 2 mi daha iyi?"
                if not any(_yer_koku(w) for w in wk):        # tur 16 (Y-A): "hangisi daha iyi?", "ikincisi daha mı iyi?"
                    soru_secim |= {numaralar.get(sira.get(m.group(1), "")) for n2, w in enumerate(wk)
                                   if (m := _SORU_SIRASI.fullmatch(w))
                                   and not (w == m.group(1) and n2 + 1 < len(wk)
                                            and _sira_sifati(w, wk[n2 + 1], wk[n2 + 2] if n2 + 2 < len(wk) else "",
                                                             wk[n2 + 3] if n2 + 3 < len(wk) else "", wk[n2 + 4:]))} - {None}
                                                       # tur 17 (O-M), tur 18 (Yüksek 1), tur 20 (Y1): eksiz sıra sözü çatı numarasıdır
                                                       # ("ikinci daha mı iyi?", "ikinci olabilir mi?"); yalnız ardından çatı dışı konu,
                                                       # sayma ya da derece sözü gelirse sıfattır ("ilk taksit", "ilk defa mı")
                for w in wk:                                   # "Evin kendi çatısı olsun, kırma mı daha iyi?"
                    kok = next((x for x in _CATI_AD_KOKU if w.startswith(x)), None)
                    kume = {c for c, g in adlar_kod.items() if kok and any(a.startswith(kok) for a in g)}
                    if 0 < len(kume) < len(adlar_kod):
                        soru_adlari.append(kume)
            else:                                              # tur 28: soru eksiz soru da çatıyı anar ("1 olsun, kırma ne zaman olur?",
                                                               # "2 ne kadar?", "3 numara ne kadar?", "kırmanın fiyatı ne?"): seçilen
                                                               # çatı değilse iki okuma vardır (tur 13 gibi), sorulur
                for i2, w in enumerate(wq):
                    s2 = wq[i2 + 1] if i2 + 1 < len(wq) else ""
                    s3 = wq[i2 + 2] if i2 + 2 < len(wq) else ""
                    if (numaralar.get(w) or harfler.get(w)) and not _birimli(wq, i2) \
                            and (not s2 or s2 in ("ne", "neler", "nedir", "nasil", "hangi", "icin", "de", "da", "ise")
                                 or (s2.startswith(("kac", "numara", "nolu"))
                                     and not (_konu_adi(s3) or _yer_koku(s3) or s3.startswith("oda")))):   # tur 29 (O6): "1 numaralı
                                                                                                        # oda nerede?" değil
                        soru_secim.add(numaralar.get(w) or harfler.get(w))
                soru_secim |= set(_secim_kodlari(hq, katalog)) & set_kodlari
                for w in wq:
                    kok = next((x for x in _CATI_AD_KOKU if w.startswith(x)), None)
                    kume = {c for c, g in adlar_kod.items() if kok and any(a.startswith(kok) for a in g)}
                    if 0 < len(kume) < len(adlar_kod):
                        soru_adlari.append(kume)
            yuklem = any(w in _YUKLEM_SOZU or w.startswith(("alsak", "secsek", "olsa")) for w in w0)
            for iy in _IYELIK.finditer(h) if yuklem else ():   # tur 13: sorunun konusu olan çatı seçimle karşılaştırılır
                if _ODA_PROGRAMI.search(iy.group(0)):
                    continue                                   # tur 14 (Orta-3): "2+1'in fiyatı" oda programıdır
                soru_hedefleri |= {numaralar.get(w) or harfler.get(w) for w in CO.norm(iy.group(0)).split()} - {None}
                soru_hedefleri |= set(_secim_kodlari(iy.group(0), katalog)) & set_kodlari
            if yuklem and (_soru_numaralari(wq, numaralar, harfler) or set(_secim_kodlari(hq, katalog)) & set_kodlari):
                kararsiz = True                                # hakem tur 11 (Y-3): seçim sorusu ("PA-06-K mı olsun, müşteri Ayşe Kaya",
                                                               # "2 mi olsun, …") seçim değildir; istekle gelince set kapanıyor, soru
                                                               # cümlesindeki kod plana gidiyordu: sorulur
            continue
        istek = bool(_cati_icerik_cumleleri(h, katalog, taban, st))
        if not istek and _eksiltili(h) and any(w in numaralar or w in harfler or _sira_kok(w, sira) for w in CO.norm(h).split()):
            # hakem tur 8 (Y1): eksiltili devam ("…, 2 de", "…, ikinciye de") istekten sonra o isteğin devamıdır (çatı seçimi değil);
            # öteki yerde ("1 olsun, 2 de olabilir", tek başına "2 de olur") seçimle çelişir ya da kararsızdır: sorulur. Hakem tur 9 (Y-1,
            # O-2): çatı sözü ya da etiket harfi taşıyan eksiltili söz ("…, çatı 2 de olsun", "…, K da olabilir") istekten sonra da çatıya
            # atıftır: iki okuma (seçim ya da "o da olur"), sorulur (önce çatı sessizce düşüyor ya da K seçiliyordu); "… de olur", "…
            # de olabilir" ve eksiz sıra sözü ("sonuncu da olur") seçeneği anar: sorulur
            w_h = CO.norm(h).split()
            if not (n > 0 and _cati_icerik_cumleleri(parcalar[n - 1], katalog, taban, st)) \
                    or any(w.startswith(("cati", "olur", "olabilir")) or w in harfler or w in sira for w in w_h):
                kararsiz = True
            continue
        if _SIRA_NUMARASI.fullmatch(h) and any(_cati_icerik_cumleleri(x, katalog, taban, st) for x in parcalar[n + 1:n + 2]):
            # hakem tur 7 (Y1, Y2): istekten önce tek başına "N." (numaralı liste maddesi ya da sıra sayısı: "1. yatak odası penceresi …",
            # "2. mutfak …") çatı numarası mı belli değil: seçim kaydedilmez, sorulur (çalışma kuralı 15)
            kararsiz = True
            continue
        ham = CO.norm(h).split()
        plan_istegi = istek and (bool(_OLCU_DESENI.search(h)) or any(w.startswith(_PLAN_ICERIK_KOKU) for w in ham))
        if _kosul_var(ham, plan_istegi, _ozel_adlar(h)):
            kararsiz = True                                    # hakem tur 9 (Y-4): "1 olsun, müşteri onaylarsa" koşullu: onay kaydedilmez
        if not plan_istegi and (_bekle_gor(ham, lambda w: w in numaralar or w in harfler or w in sira or bool(_secim_kodlari(w, katalog)),
                                           [w for x in parcalar for w in CO.norm(x).split()])
                                or any(a.startswith("teklif") and b.startswith(("verdi", "vermis")) for a, b in zip(ham, ham[1:]))):
            kararsiz = True                                    # tur 29 (Y4, Y5, Y6): "1 olsun, sonra", "Ç8801 olsun ama şimdi değil", "1
                                                               # olsun, bekliyoruz", "teklif gelsin bakalım", "müşteri razı olması lazım";
                                                               # "müşteri teklif verdi" (Y1b: onay mı, başka teklif mi belli değil)
        if _onay_ertelenmis(ham):
            kararsiz = True                                    # hakem tur 10 (Y-1): "müşteri onaylayınca", "onayından sonra", "onay alalım"
        if _kararsizlik_var(ham, ardi=CO.norm(parcalar[n + 1]).split() if n + 1 < len(parcalar) else ()) or _gore_bagi(ham):
            kararsiz = True                                    # tur 14 (Yüksek-1): "1 olsun, bilemedik", "emin değiliz", "karar veremedik"
        if _erteleme_var(ham, plan_istegi) or _ertelemeli(ham) \
                or (ham and ham[-1] in ("ama", "fakat", "ancak")
                    and not ((ardi_b := _baglac_ardi(parcalar, n))
                             and all(_cekincesiz(x, haber=len(ardi_b) == 2 and k == 0) for k, x in enumerate(ardi_b))
                             and any(_plan_istegi_parcasi(x) or _secim_parcasi(x, katalog, numaralar, harfler, sira) for x in ardi_b))) \
                or _cati_ertelemesi(ham, CO.norm(parcalar[n + 1]).split() if n + 1 < len(parcalar) else ()):
            kararsiz = True                                    # tur 20 (O1), tur 21 (Y1): "Tamam ama, 2 olsun" ve "2 olsun ama, yatak
                                                               # odası 2 penceresi 120x180 olsun" değil; "1 olsun ama, şimdilik" kararsız
                                                               # hakem tur 6 (O2): "müşteriye soralım, sonra döneriz" seçim değildir; tur 11:
                                                               # onay ve "evet" sözü silinmeden önce ("müşteri evet deyince")
        temiz = _ONAY_SOZU.sub(" ", _talep_sozu_cikar(h, kendi_yapi))     # evin m²'si, oda programı, ölçüsü sayı değildir
        sozler, kodlar = [], []
        for _, soz, kod in _sozcukler(temiz, katalog):
            if kod:
                kodlar.append(str(Katalog.kod_normalize(kod) or kod).upper())
            else:
                sozler += CO.norm(soz).split()
        secilen = set(_secim_kodlari(temiz, katalog))          # değişimin kaynağı seçim değildir ("Ç8801K yerine Ç8801L", "K'dan L'ye")
        kodlar = [c for c in kodlar if c in secilen]
        kaynak = {i for i, w in enumerate(sozler) if (i + 1 < len(sozler) and sozler[i + 1] in ("dan", "den", "tan", "ten", "yerine"))
                  or (w.startswith(_CATI_AD_KOKU) and w.endswith(("dan", "den")))}
        sozler = _sira_baglami([w for i, w in enumerate(sozler) if i not in kaynak], sira)   # hakem tur 8 (Y3): "son haliyle"
        adli = [w for w in sozler if w.startswith(_CATI_AD_KOKU)]
        for w in adli:
            kok = next(x for x in _CATI_AD_KOKU if w.startswith(x))
            kume = {c for c, g in adlar_kod.items() if any(n.startswith(kok) for n in g)}
            if not istek or 0 < len(kume) < len(adlar_kod):    # istek cümlesinde yalnız seçenekleri ayıran ad ("kırma çatıya pencere")
                ad_kumeleri.append(kume)
        if any(w.startswith(_KARARSIZ_KOKU) for w in sozler) if not istek else \
                (any(w.startswith("ikisi") for w in sozler) and not _OLCU_DESENI.search(h)
                 and not any(w.startswith(_ODA_PENCERE_KOKU) for w in sozler)):
            kararsiz = True                                    # hakem tur 7 (O1), tur 8 (O4): "1 olsun, daha ucuz olsun", "ikisinden biri",
                                                               # "2 olsun, ikisinin fiyatını da gönderin" (iki çatının fiyatı: karar verilmedi);
                                                               # tur 9 (O-1): ölçülü ya da odalı istekte "ikisi" pencerelerdir ("yatak
                                                               # odalarının ikisinin de penceresi 120x180 olsun"): kararsızlık değil
        if istek:
            # istek cümlesinde sayı ve harf isteğindir ("yatak odası 1 penceresi"); hakem tur 6 (Y1): setin çatı kodu, çatı sözüne bitişik
            # numara ya da etiket ("çatı 2 …", "2 numaralı çatıyla …", "K çatısıyla …") ve tek başına etiket harfi ("… 120x180 K olsun")
            # çatıya atıftır: seçim okunmadıysa sorulur (istek sessizce düşmez, çatı da)
            hedef = {c for c in kodlar if c in set_kodlari and c != tk}
            for i in range(len(sozler) - 1):
                j = i + 1                                      # "2 numara olsun banyo 2 tane", "2'yi seçtik", "2 numarayı seçtik"
                while j + 1 < len(sozler) and (sozler[j] in _SAYI_EKI or sozler[j].startswith("numara")):
                    j += 1
                if (sozler[j] in _YUKLEM_SOZU or sozler[j].startswith(_SECIM_FIILI)) \
                        and (i == 0 or not sozler[i - 1].startswith(_ALAN_DISI_KOK + _EV_ADI_EK)
                             or sozler[i - 1].startswith(_EV_ADI_DISI)) and \
                        (r0 := sozler[i] if sozler[i] in numaralar else (sira.get(_sira_kok(sozler[i], sira) or "") or None)) in numaralar:
                    hedef.add(numaralar[r0])                   # hakem tur 7 (Y3): devrik sayı cümlesi ("2 olsun banyo", "3 olsun yatak odası
                                                               # sayısı") çatı numarası mı oda sayısı mı belli değil: sorulur; tur 9 (Y-2):
                                                               # önünde söz olsa da ("Peki 2 olsun banyo 2 tane", "Müşteri 2 olsun dedi …");
                                                               # "pencere sayısı 2 olsun" sayıdır; "Biz de 2 diyoruz",
                                                               # "müşteri 2 diyor" seçim sözüdür
            for i, w in enumerate(sozler):
                if w in harfler and not (i + 1 < len(sozler) and sozler[i + 1] in ("tip", "tipi", "seklinde", "sekli")):
                    hedef.add(harfler[w])
                if not w.startswith("cati"):
                    continue
                for j in (i - 1, i - 2, i + 1, i + 2):
                    if not 0 <= j < len(sozler) or (abs(j - i) == 2 and sozler[(i + j) // 2] not in _NUMARA):
                        continue
                    v = sozler[j]
                    sonraki = sozler[j + 1] if j + 1 < len(sozler) else ""
                    if v in numaralar and not sonraki.startswith(("pencere", "oda", "kapi", "adet", "tane", "derece", "metre", "cm")):
                        hedef.add(numaralar[v])
                    elif v in harfler:
                        hedef.add(harfler[v])
            hedefler |= hedef
            continue
        hedef = {c for c in kodlar if c in set_kodlari}
        kararsiz = kararsiz or any(c not in set_kodlari and Katalog.taban_kod(c) == Katalog.taban_kod(tk) for c in kodlar)
        hedef |= {harfler[w] for w in sozler if w in harfler}
        for w in sozler:
            if w.isdigit():
                if w in numaralar:
                    hedef.add(numaralar[w])
                else:
                    kararsiz = True
        if all(w.isdigit() or _sira_kok(w, sira) or w in harfler or w in _CATI_BAGLAM or w in _NUMARA or w.startswith("cati")
               or _nezaket(w) for w in sozler):
            hedef |= {numaralar.get(sira[r], "") for w in sozler if (r := _sira_kok(w, sira))} - {""}
        if not _plan_cumlesi(h) and any(w in _KENDI_SOZU for w in sozler) and (any(w.startswith("cati") for w in sozler)
                                                                              or _kendi_catisi_cumlesi(sozler)
                                                      or any(w in _KENDI_SOZU for w in sozler if w in ("kendi", "mevcut", "oldugu"))):
            hedef.add(tk)
        degismez = any(w.startswith("cati") for w in sozler) and any(w.startswith("degisiklik") for w in sozler) \
            and not any(w in _BASKA_SOZU or w in ("haric", "disinda") for w in sozler) \
            and any(w == "yok" or CO._OLUMSUZ_FIIL_T.fullmatch(w) for w in sozler)   # tur 16: "çatı hariç değişiklik yok" değil
        if degismez:
            hedef.add(tk)                                      # tur 14 (Orta-4): "çatıda değişiklik istemiyoruz/yok" evin kendi çatısıdır
        cati_sozu = bool(hedef or adli or any(w.startswith("cati") or w in _KENDI_SOZU for w in sozler))
        if cati_sozu and not degismez and any(w in _BASKA_SOZU or CO._OLUMSUZ_FIIL_T.fullmatch(w) for w in sozler):
            kararsiz = True                                    # "mevcut çatıdan farklı olsun", "evin kendi çatısı olmasın"
        hedefler |= hedef
    if soru_hedefleri - hedefler or (hedefler and (soru_secim - hedefler or any(not (a & hedefler) for a in soru_adlari))):
        kararsiz = True                                        # tur 13: "1 olsun, 2'nin fiyatı ne olacak?" (1 mi, fiyata göre 2 mi): sorulur
    if secim_dili_sorusu and hedefler <= {tk}:
        kararsiz = True                                        # tur 26 (Y3): evin çatısı onaylanacakken yalnız seçim sözleriyle kurulan
                                                               # konusuz soru ("1 olsun, okey mi?") seçimin sorusudur: onay kaydedilmez
    return kararsiz, hedefler, ad_kumeleri


_M2_SOZU = re.compile(r"(?<![\d.,x×])(\d{2,3}(?:[.,]\d+)?)\s*(?:m2|m²|mt2|metre\s*kare|metrekare)", re.IGNORECASE)
_ODA_SOZU = re.compile(r"(?<![\d.,])(\d)\s*\+\s*(\d)(?![\d.,])")
_OLCU_SOZU = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d+)?)\s*(?:m\s*|metre\s*)?[x×*]\s*(\d{1,2}(?:[.,]\d+)?)(?![\d.,])", re.IGNORECASE)
_KENAR_SOZU = re.compile(r"(?<![\d.,x×])(\d{1,2}(?:[.,]\d+)?)\s*(?:m|mt|metre)(?![a-z0-9²])", re.IGNORECASE)
# m² sözünün evin alanı olmadığını gösteren sözcükler: oda, veranda, arsa, çatı, pencere ("salon 25 m2", "veranda 12 m2", "arsa 500 m2")
_ALAN_DISI_KOK = ("salon", "oturma", "yatak", "mutfa", "banyo", "wc", "tuvalet", "antre", "hol", "koridor", "veranda", "teras", "balkon",
                  "arsa", "bahce", "parsel", "depo", "kiler", "giyinme", "cati", "ofis", "dukkan", "garaj", "odasi", "odanin", "odaya",
                  "odalar", "pencere", "kapi", "vasistas", "cam", "sundurma", "giris", "kamelya", "pergole", "otopark", "havuz",
                  "bodrum", "camasir", "cocuk", "misafir", "ebeveyn", "calisma", "kisim", "bolum",
                  # hakem tur 5 (O3): evin yanındaki başka yapı ("4x5 sera", "yanına 3x4 kulübe")
                  "sera", "kulube", "cardak", "gazebo", "kumes", "ahir", "barinak", "konteyner", "yanina", "yaninda")


def _alan_disi(w: str) -> bool:
    return w == "oda" or w.startswith(_ALAN_DISI_KOK)


def _ev_m2_mi(q: str, m: re.Match) -> bool:
    """Cümledeki m² sözü evin alanı mı: önündeki beş sözcükte ya da hemen ardında oda, veranda, arsa ya da çatı sözü olan m² evin alanı
    değildir ("salon 25 m2", "veranda kısmının alanı da 12 m2", "12 m2 veranda", "15 m2'lik teras", "arsa 500 m2"); "85 m2 verandalı",
    "verandalı 85 m2" evin alanıdır (hakem tur 4, B1)."""
    sahip = lambda w: bool(re.search(r"l[iu]$", w))
    once = CO.norm(q[:m.start()]).split()[-5:]
    sonra = []                                                 # hakem tur 5 (O3): ardındaki üç sözcük ("15 m2 kadar veranda", "15
    for w in CO.norm(q[m.end():]).split():                     # metrekarelik bir veranda", "12 m2 kapalı teras"); yüklemde durur
        if w in _YAPI_DUR:                                     # ("85 m2 olsun, veranda kalsın" evin alanıdır)
            break
        if w not in ("lik", "luk", "li", "lu"):
            sonra.append(w)
        if len(sonra) == 3:
            break
    return not (any(_alan_disi(w) and not sahip(w) for w in once) or any(_alan_disi(w) and not sahip(w) for w in sonra))


def _ev_m2_sozleri(metin: str | None) -> list[float]:
    """Bayinin yazdığı evin m²'leri (`_ev_m2_mi`)."""
    out = set()
    for h in _cumleler(metin):
        q = h.lower()
        out |= {float(m.group(1).replace(",", ".")) for m in _M2_SOZU.finditer(q) if _ev_m2_mi(q, m)}
    return sorted(out)


def _m2_sozle_destekli(metin: str | None, deger: float) -> bool:
    """LLM'in okuduğu m² bayinin sözünde var mı ("alanı 100 olsun", "yüz metrekare"): oda, veranda, arsa ya da pencere sözü olmayan bir
    cümlede sayının kendisi ya da m²/alan sözü. Bağlamdan yinelenen değer ("tamam" → 87) sözde yoktur."""
    sayilar = {f"{deger:g}", f"{deger:g}".replace(".", ",")}
    for h in _cumleler(metin):
        if any(_alan_disi(w) for w in CO.norm(h).split()):
            continue
        ham = h.lower()
        if re.search(r"m2|m²|mt2|metre\s*kare|metrekare|\balan", ham) or any(
                re.search(rf"(?<![\d.,x×]){re.escape(s)}(?![\d.,x×])", ham) for s in sayilar):
            return True
    return False


def _dis_olcu_sozu(metin: str | None, t: Talep) -> dict | None:
    """Bayinin yazdığı dış ölçü (metre): iki kenar ("8x11", "7,5 x 11,5 m"; her kenar 3–30 m, pencere ya da kapı sözü olmayan cümlede)
    ya da LLM'in okuduğu bir kenarla aynı tek kenar ("boyu 8 metre"). Pencere ölçüsü ("60x40", "1,20x1,20") dış ölçü değildir."""
    def uygun(h: str) -> bool:                                 # hakem tur 4, B8: oda sözü olan cümle ("mutfak 3x4 olsun") de değil
        n = CO.norm(h).split()
        return "cm" not in n and not any(w.startswith(("pencere", "kapi", "vasistas", "cam", "dolap"))
                                         or (_alan_disi(w) and not w.startswith("cati") and not re.search(r"l[iu]$", w)) for w in n)
    llm = t.dis_olcu.model_dump() if t.dis_olcu is not None else {}
    for h in _cumleler(metin):
        if not uygun(h):
            continue
        for a, b in _OLCU_SOZU.findall(h.lower()):
            en, boy = sorted((float(a.replace(",", ".")), float(b.replace(",", "."))))
            if 3 <= en <= 30 and 3 <= boy <= 30:
                return {"en_m": en, "boy_m": boy}
    kenarlar = [float(v) for v in (llm.get("en_m"), llm.get("boy_m")) if v]
    for h in _cumleler(metin):
        if not uygun(h):
            continue
        for x in _KENAR_SOZU.findall(_M2_SOZU.sub(" ", h.lower())):
            v = float(x.replace(",", "."))
            if 3 <= v <= 30 and any(abs(v - e) <= 0.05 for e in kenarlar):
                return {a: v for a, v in llm.items() if v}
    return None


def _cati_adiminda_talep_degisti(k: Konusma, t: Talep, metin: str | None, taban: dict) -> dict:
    """İE-42 (hakem tur 2, O1, O4, O8; tur 3): çatı seti açıkken bu mesaj talebi değiştiriyor mu? Bayinin kendi sözünden okunur (K18;
    `metin` soru cümleleri çıkmış metindir: "100 m2 olur mu?" talep değildir): evin m²'si (`_ev_m2_sozleri`; LLM'in m²'si yalnız sözde
    varsa, `_m2_sozle_destekli`), oda programı ("3+1"), dış ölçü (`_dis_olcu_sozu`), kat ve yapı türü (yalnız sözü geçerse). Kıyas
    taslaktaki ve evin kartındaki değerle; ikisinden de farklı (m²'de 0,5 m²'den çok) olan değer değişikliktir. Dönen sözlük değişen
    alanlar (yoksa boş)."""
    ts, model = k.d.get("taslak") or {}, taban or {}
    q = (metin or "").lower()
    n = CO.norm(metin)
    yeni: dict = {}
    m2_ref = [float(v) for v in (ts.get("alan_m2"), model.get("katalog_m2")) if isinstance(v, (int, float))]
    farkli = lambda v: not m2_ref or all(abs(v - r) > 0.5 for r in m2_ref)
    m2ler = [v for v in _ev_m2_sozleri(metin) if farkli(v)]
    llm_m2 = float(t.alan_m2) if isinstance(t.alan_m2, (int, float)) else None
    if m2ler:
        yeni["alan_m2"] = llm_m2 if llm_m2 in m2ler else m2ler[0]
    elif llm_m2 is not None and farkli(llm_m2) and _m2_sozle_destekli(metin, llm_m2):
        yeni["alan_m2"] = llm_m2
    oda_ref = {str(v) for v in (ts.get("oda_programi"), model.get("oda_programi")) if v}
    odalar = [f"{a}+{b}" for a, b in _ODA_SOZU.findall(q)]
    farkli_oda = [o for o in odalar if o not in oda_ref]
    if farkli_oda:
        yeni["oda_programi"] = t.oda_programi if t.oda_programi in farkli_oda else farkli_oda[0]
    olcu = _dis_olcu_sozu(metin, t)
    if olcu:
        e = ts.get("dis_olcu") or {}
        if not (e.get("en_m") and e.get("boy_m") and olcu.get("en_m") and olcu.get("boy_m")
                and sorted(map(float, (olcu["en_m"], olcu["boy_m"]))) == sorted(map(float, (e["en_m"], e["boy_m"])))):
            yeni["dis_olcu"] = olcu
    kat_ref = {int(v) for v in (ts.get("kat_sayisi"), model.get("kat")) if isinstance(v, (int, float)) or str(v or "").isdigit()} or {1}
    kat_soz = None                                             # hakem tur 4, B2: "2 katlı", "iki katlı", "dubleks" (LLM kat yazmasa da)
    for h in _cumleler(q):                                     # malzeme katı ("çift kat yalıtım") değil; olumsuzlanan kat sözü ("2 katlı
        if _KAT_DISI.search(h):                                # olmasın") değil, "tek katlı olmasın 2 katlı olsun" 2 kattır (hakem tur 5)
            continue
        mk = next((m for m in _COK_KAT_SOZU.finditer(h) if not _sonra_olumsuz(h[m.end():])), None)
        if mk:
            kat_soz = int(mk.group(1)) if mk.group(1) else {"iki": 2, "çift": 2, "cift": 2, "üç": 3, "uc": 3}.get((mk.group(2) or "").lower(), 2)
            break
    if not kat_soz:
        for h in _cumleler(q):
            if _KAT_EKLE_SOZU.search(h) and not _KAT_DISI.search(h) and not _TALEP_OLUMSUZ.search(h):
                kat_soz = max(kat_ref) + 1
                break
    if t.kat_sayisi and re.search(r"\b(?:kat|katli|dubleks|tripleks)\b", n) and int(t.kat_sayisi) not in kat_ref:
        yeni["kat_sayisi"] = int(t.kat_sayisi)
    elif kat_soz and kat_soz not in kat_ref:
        yeni["kat_sayisi"] = kat_soz
    yapi_ref = {str(v) for v in (ts.get("yapi_turu"), model.get("yapi_turu")) if v} or \
        {"celik" if ((k.d.get("son_is_emri") or {}).get("yapi") or {}).get("sistem") == "celik" else "prefabrik"}
    for h in _cumleler(metin):                                 # yapı sözü bayinin cümlesinde (kapı, pencere, kolon, çatı sözü değil)
        if _YAPI_DISI.search(h):
            continue
        sozdeki = _olumlu_yapi_sozleri(h)                      # "çelik olmasın" istek değil; "prefabrik değil çelik olsun",
        if len(sozdeki) == 1 and sozdeki[0] not in yapi_ref:   # "prefabrik istemiyoruz çelik olsun" istektir (hakem tur 5, O1)
            yeni["yapi_turu"] = t.yapi_turu if t.yapi_turu == sozdeki[0] else sozdeki[0]
            break
    return yeni


_YAPI_DUR = {"olsun", "olacak", "olmali", "istiyoruz", "istiyorum", "isteriz", "yapin", "yapalim", "yapilsin", "ama", "fakat", "ve"}


def _sonra_olumsuz(kalan: str) -> bool:
    """Sözün ardındaki üç sözcükte, olumlu yükleme ya da başka yapı sözüne gelmeden olumsuz söz var mı ("… olmasın", "… istemiyoruz")."""
    for z in CO.norm(kalan).split()[:3]:
        if z.startswith(("celik", "prefabrik")) or z in _YAPI_DUR or re.fullmatch(r"\d|tek|iki|uc|cift", z):
            return False
        if CO._OLUMSUZ_FIIL_T.fullmatch(z):
            return True
    return False


def _olumlu_yapi_sozleri(h: str) -> list[str]:
    """Cümlede olumsuzlanmamış yapı türü sözleri (hakem tur 5, O1): yapı sözünden sonraki üç sözcükte, başka yapı sözüne ya da olumlu
    yükleme ("olsun") gelmeden olumsuz söz ("olmasın", "istemiyoruz", "değil") varsa o söz olumsuzdur."""
    w = CO.norm(h).split()
    out = []
    for i, x in enumerate(w):
        y = "celik" if x.startswith("celik") else "prefabrik" if x.startswith("prefabrik") else None
        if y is not None and not _sonra_olumsuz(" ".join(w[i + 1:])) and y not in out:
            out.append(y)
    return out


def _yeni_musteri(k: Konusma, t: Talep, metin: str | None) -> bool:
    """Bu mesaj başka bir müşterinin talebi mi: LLM'in okuduğu müşteri adı bayinin sözünde geçiyor ve adı taslaktaki müşterinin adından
    farklı ("Mehmet Deneme için 60 m2 1+1 lazım"; taslakta Ayşe Deneme). Taslakta müşteri yoksa ad bu planın bilgisidir; ilk adı aynı olan
    ad düzeltmedir ("Ayşe Deneme Yılmaz") (hakem tur 3, O5, O6)."""
    unvan = {"bey", "beye", "beyin", "hanim", "hanima", "bay", "bayan", "sayin", "musteri", "musterimiz"}
    yeni = [w for w in CO.norm(t.musteri.ad if t.musteri is not None and t.musteri.ad else "").split() if w not in unvan]
    eski = [w for w in CO.norm(((k.d.get("taslak") or {}).get("musteri") or {}).get("ad")).split() if w not in unvan]
    if not yeni or not eski or yeni[0] == eski[0]:
        return False
    sozler = CO.norm(metin).split()
    if any(w in ("adi", "ismi", "isim", "adini", "ismini") for w in sozler) and any(
            w.startswith(("yanlis", "duzelt", "hatali", "degis")) for w in sozler):
        return False                                           # "müşteri adı yanlış, Fatma Deneme olacak": adın düzeltmesi (hakem tur 4);
                                                               # "müşterinin adını Zeynep Deneme olarak değiştirin" (tur 5)
    # ekli ad da adın kendisidir ("Mehmet Yılmazın evi", "Mehmet beye"; hakem tur 4, B6)
    return all(any(s == w or (len(w) >= 3 and s.startswith(w) and len(s) - len(w) <= 3) for s in sozler) for w in yeni if len(w) >= 2)


def _cati_adiminda_istek_yok(k: Konusma, t: Talep, metin: str | None, secim_metni: str = "") -> bool:
    """Çatı sözü olmayan mesaj bir istek taşımıyor mu ("tamam", "bakalım", "teşekkürler"; LLM'in bağlamdan yinelediği kod, m², oda, ölçü,
    veranda, yükseklik sayılmaz: hakem tur 3, O4)? Öyleyse çatı sorulur, set açık kalır. İstek ya da bilgi taşıyan mesaj (bayinin sözünde
    istek cümlesi, `k.cati_ek`; iptal, pano komutu, açık yeni talep sözü) seti kapatır ve bugünkü yoldan gider: değişiklik isteği sessizce
    düşmez (Lokman, 13 Ekim). Hızlı istek ve pano komutu soru cümlesinde aranmaz ("Ç8801K mi Ç8801L mi olsun?" kararsızlıktır)."""
    if _iptal_sozu(metin) or _acik_yeni_talep(metin) or CO.hizli_istek(secim_metni) or any(YPO.oku(secim_metni)):
        return False
    if t.niyet not in ("diger", "revizyon", "yeni_talep"):
        return False
    return not getattr(k, "cati_ek", False)


def _sozdeki_pencere_alanlari(t: Talep, icerik: list[str]) -> dict:
    """İE-42 (hakem tur 4, Y5): çatı setinde LLM'in pencere okuması bayinin sözünde yoksa (cümlelerde pencere sözü ya da o ölçü yok) bağlamdan
    yinelemedir ("1 olsun, verandayı kaldırın" → eski SALON 120x120): talebe girmez, pencere sorusu açmaz (K18). Dönen: güncellenecek alanlar."""
    soz = any(_PENCERE_SOZU.search(CO.norm(h)) for h in icerik)
    if soz:
        return {}
    olculer = {_cm_olcu(a, b) for h in icerik for a, b in _PENCERE_OLCUSU.findall(h)}
    return {"pencereler": [p for p in t.pencereler if p.olcu and p.olcu in olculer],
            "varyantlar": [v for v in t.varyantlar if not v.tur.startswith("pencere")]}


def _cati_adimi_yeni_talep(k: Konusma, t: Talep, taban: dict, degisen: dict, yeni_musteri: bool = False) -> Talep:
    """Hakem tur 1 bulgu 9 ve tur 2 (O1, O6): çatı seti açıkken talep değişti (m², dış ölçü, oda, kat ya da yapı türü). Talep yeni talep olarak
    okunur; önceki mesajların bilgisi düşmez: müşteri (birleşir), özel istekler (birleşir), bina özellikleri (birleşir), oda programı, kat ve
    yapı türü (yazılmadıysa taslaktan, yoksa evin kartından; yapı türü yoksa planın sisteminden). Yeni dış ölçü eski m²'nin, yeni m² eski dış
    ölçünün yerine geçer. Pencereler bu mesajınkiler (eski evin pencereleri yeni eve taşınmaz). Hakem tur 3 (O6): talep başka bir müşterinin
    (`_yeni_musteri`) ise eski müşterinin adı, sevk adresi, özel istekleri ve bina özellikleri taşınmaz."""
    ts, model = k.d.get("taslak") or {}, taban or {}
    sistem = ((k.d.get("son_is_emri") or {}).get("yapi") or {}).get("sistem")
    bu_musteri = {a: v for a, v in (t.musteri.model_dump() if t.musteri else {}).items() if v}
    eski_ozel = list(ts.get("ozel_istekler") or [])
    m = bu_musteri if yeni_musteri else {**(ts.get("musteri") or {}), **bu_musteri}
    yeni_olcu = "dis_olcu" in degisen
    if "alan_m2" in degisen:
        alan = degisen["alan_m2"]
    elif yeni_olcu:
        alan = None
    else:
        alan = ts.get("alan_m2") if ts.get("alan_m2") is not None else model.get("katalog_m2")
    d = t.model_dump(mode="json")
    d.update({
        "niyet": "yeni_talep", "katalog_kodu": None, "alan_m2": alan,
        "dis_olcu": degisen.get("dis_olcu") if yeni_olcu else (None if "alan_m2" in degisen else ts.get("dis_olcu")),
        "oda_programi": degisen.get("oda_programi") or ts.get("oda_programi") or model.get("oda_programi"),
        "kat_sayisi": degisen.get("kat_sayisi") or ts.get("kat_sayisi") or model.get("kat"),
        "yapi_turu": degisen.get("yapi_turu") or ts.get("yapi_turu") or model.get("yapi_turu")
                     or ("celik" if sistem == "celik" else "prefabrik"),
        "musteri": m or None,
        "ozel_istekler": ([s for s in t.ozel_istekler if s not in eski_ozel] if yeni_musteri
                          else list(dict.fromkeys(eski_ozel + list(t.ozel_istekler)))),
        "bina_ozellikleri": ({**(t.bina_ozellikleri or {})} if yeni_musteri
                             else {**(ts.get("bina_ozellikleri") or {}), **(t.bina_ozellikleri or {})}),
    })
    if d["kat_sayisi"] is not None and not isinstance(d["kat_sayisi"], int):
        d["kat_sayisi"] = int(d["kat_sayisi"]) if str(d["kat_sayisi"]).isdigit() else None
    return Talep.model_validate(d)


def _cati_adimi(k: Konusma, t: Talep, metin: str | None, katalog: Katalog) -> tuple[Talep, Karar | None]:
    """Onaydan sonraki çatı seti açıkken gelen mesaj. Dönen (talep, karar): karar varsa o; yoksa talep bugünkü yoldan işlenir.
    - selam: bugünkü cevap, set açık kalır. Ret ("Revize et"): set kapanır.
    - Mesaj bayinin sözünden okunur (K18; hakem tur 3): soru cümlesi seçim ve istek değildir (`_cati_adimi_secim_metni`, her niyette),
      seçim dışındaki cümleler istek ya da bilgidir (`_cati_icerik_cumleleri`; LLM'in alanlarına bakılmaz).
    - Talep değişti (m², oda, dış ölçü, kat, yapı türü; `_cati_adiminda_talep_degisti`, her niyette): çatı seçiminden önce gelir. Set
      kapanır, talep önceki bilgisiyle yeni talep olur (başka müşterininse bilgisi taşınmaz); bayiye r01 onayının geçersiz kaldığı ve aynı
      mesajın çatı seçiminin kaydedilmediği yazılır (hakem tur 2, O1, O6; tur 3).
    - Çatı seçimi (düğme, numara, sıra sözü, kod, etiket; prefabrikte `_prefabrik_cati_istegi`, çelikte `_celik_cati_adimi_okumasi`):
      evin kendi çatısı ve istek cümlesi yok → onay kaydedilir, plan aynen; başka çatı (ya da istekle birlikte) → talep o çatının revizyonu
      olur (`k.cati_secimi`; revizyon hakkına takılmaz), metni soru cümlesiz söz (`k.cati_adimi_metni`), LLM'in talep alanları (m², oda,
      ölçü, kat, yapı) taşınmaz; istek cümlesi yoksa LLM'in pencere, varyant ve özel istek yinelemesi de taşınmaz. Mesajın başı "Çatı: …
      (kod)." İstek geri çevrilir ya da plan değişmezse `karar_ver` çatı seçimini ayrıca ele alır (`k.cati_adimi_secimi`).
    - Onay ve soru (hakem tur 1, bulgu 8; tur 2, O2 ve D4): seçim yoksa onay "Hangi çatı olsun?", soru bugünkü cevap.
    - Niyet "diğer" ya da "yeni talep" okunan istek ve bilgi revizyondur (hakem tur 2, O5); başka müşterinin talebi değildir (tur 3).
    - Çatı sözü olmayan mesaj: istek taşımıyorsa soru (`_cati_adiminda_istek_yok`); taşıyorsa set kapanır, mesaj bugünkü yoldan
      (planın değişikliği; onay düşer, "r01 onayınızı geçersiz kıldı")."""
    ca = k.d.get("cati_adimi")
    if not ca:
        return t, None
    st = k.d.get("secenek_seti") or {}
    ie = k.d.get("son_is_emri") or {}
    taban = katalog.aday(ca.get("kod"))
    if not (st.get("durum") == "acik" and st.get("tur") == "cati_varyanti" and k.d.get("asama") == "onay_bekliyor" and taban is not None
            and ie.get("is_emri_no") == ca.get("is_emri_no") and int(ie.get("revizyon") or 1) == ca.get("rev")):
        k.d.pop("cati_adimi", None)
        return t, None
    if t.niyet == "selam":
        return t, None
    if t.niyet == "red":
        _cati_adimini_kapat(k, st, "plan değişikliği istendi")
        return t, None
    if metin:                                                  # hakem tur 6: kod yazımı, sıra sayısı, virgülsüz seçim + istek
        metin = _cati_adimi_on_okuma(metin, katalog, taban, st)
    son_metin0 = k.d.get("son_metin")
    celik_mi = (ie.get("yapi") or {}).get("sistem") == "celik"
    onay_soru = t.niyet in ("onay", "soru")
    secim_metni = _cati_adimi_secim_metni(metin)
    k.d["son_metin"] = secim_metni.strip()
    k.cati_numara_metni = None
    fiyat_sorulari: list[str] = []
    icerik = _cati_icerik_cumleleri(metin, katalog, taban, st, fiyat_sorulari)
    k.cati_fiyat_sorusu = bool(fiyat_sorulari)
    ek = bool(icerik) or any(YPO.oku(metin))
    k.cati_icerik, k.cati_ek = icerik, ek
    baska = [c for c in _secim_kodlari(metin, katalog) if Katalog.taban_kod(c) != Katalog.taban_kod(taban["kod"])]   # bayinin yazdığı başka ev
    baska_llm = bool(t.katalog_kodu and Katalog.taban_kod(t.katalog_kodu) != Katalog.taban_kod(taban["kod"]))
    yeni_soz = _iptal_sozu(metin) or _acik_yeni_talep(metin)
    yeni_musteri = _yeni_musteri(k, t, metin)
    if t.niyet in ("diger", "yeni_talep") and ek and not baska and not baska_llm and not yeni_soz and not yeni_musteri:
        # hakem tur 2, O5: "diğer" ya da "yeni talep" okunan istek ve bilgi (başka ev, başka müşteri, iptal ve açık yeni talep sözü yok)
        # planın değişikliğidir; yalnız müşteri bilgisi konuşmayı sıfırlamaz. Talebin kendisi değiştiyse aşağıda yeni talep olur.
        t = t.model_copy(update={"niyet": "revizyon"})
    if ek:
        # çatı sözü kararsızsa "Hangi çatı olsun?" sorulur; aynı mesajın öteki isteği bu soruyla uygulanmaz, bayiye yazılır (sessiz düşmez)
        k.cati_sorusu_notu = "Mesajınızdaki öteki isteği uygulamadım. Önce çatıyı seçin, sonra o isteği yeniden yazın."
    rev = int(ca.get("rev") or 1)

    def oku():
        if celik_mi:
            return _celik_cati_adimi_okumasi(k, katalog, taban, secim_metni, st,
                                             cati_istegi=bool(CO.norm(secim_metni)) and any(v.tur == "cati_degistir" for v in t.varyantlar))
        vary = [v.model_dump(mode="json") for v in t.varyantlar] if CO.norm(secim_metni) else []   # soru cümlesinin LLM okuması seçim değil
        return _prefabrik_cati_istegi(k, katalog, taban, {"varyantlar": vary}, bos_ise_yok=True)

    def izsiz_oku():                                            # okumanın izi kalmaz (durum, notlar, son metin)
        yedek, notlar = json.loads(json.dumps(k.d)), len(getattr(k, "yeni_notlar", None) or [])
        s = oku()
        k.d = yedek
        if isinstance(getattr(k, "yeni_notlar", None), list):
            del k.yeni_notlar[notlar:]
        return s

    if not yeni_soz and not baska:
        degisen = _cati_adiminda_talep_degisti(k, t, secim_metni, taban)
        if degisen:
            # Hakem tur 1 bulgu 9, tur 2 O1, tur 3 (İE-25 kuralı: çatı seti açıkken m², dış ölçü, oda, kat ya da yapı türü değişikliği sessizce
            # düşmez): istek bu evin planı değil, başka bir ev ister. Talep değişikliği çatı seçiminden önce gelir (onay ve soru sözüyle de):
            # set kapanır, talep yeni talep olarak okunur; r01 onayının geçersiz kaldığı ve aynı mesajın çatı seçiminin kaydedilmediği yazılır.
            s = izsiz_oku()
            k.d["son_metin"] = son_metin0
            on = f"Talebiniz değişti; bu değişiklik r{rev:02d} onayınızı geçersiz kıldı. "
            if isinstance(s, str) and s:
                a = katalog.aday(s)
                on += f"Çatı seçiminizi ({SC.gosterim(a) if a else s}) kaydetmedim. "
            elif isinstance(s, Karar):
                on += "Çatı isteğinizi uygulamadım. "
            k.cati_on_not = on + "Önce yeni plan seçilir. "
            _cati_adimini_kapat(k, st, f"talep bilgisi değişti ({', '.join(degisen)})")
            k.d.pop("cati_onayi_dustu", None)
            k.not_dus("kural", "onaydan sonraki çatı setinde talep bilgisi değişti: yeni talep olarak okundu"
                      + (" (başka müşteri)" if yeni_musteri else ""))
            return _cati_adimi_yeni_talep(k, t, taban, degisen, yeni_musteri), None

    kararsiz, hedefler, ad_kumeleri = (False, set(), []) if (yeni_soz or baska or yeni_musteri) else \
        _cati_atiflari(metin, katalog, taban, st)              # yeni talep, başka ev ya da müşteri: çatı sözü okunmaz
    yedek, notlar = json.loads(json.dumps(k.d)), len(getattr(k, "yeni_notlar", None) or [])

    def geri_al():                                             # okumanın izi kalmaz
        k.d = yedek
        if isinstance(getattr(k, "yeni_notlar", None), list):
            del k.yeni_notlar[notlar:]
        k.d["son_metin"] = son_metin0

    secim = oku()
    acik = isinstance(secim, str) and bool(secim)
    if acik:
        # hakem tur 5 (Y1, Y3): mesajın öteki çatı sözü seçimle çelişiyor ("1 olsun, kırmayı alın", "1 olsun, K ile devam edelim",
        # "1 olsun, mevcut çatıdan farklı olsun"): seçim yok, "Hangi çatı olsun?"
        celiski = kararsiz or bool(hedefler - {secim.upper()}) or any(secim.upper() not in a for a in ad_kumeleri)
    else:                                                      # okunamayan çatı sözü ("teklifte 2 de olsun") sessizce düşmez
        celiski = not isinstance(secim, Karar) and t.niyet != "soru" and (kararsiz or bool(hedefler) or bool(ad_kumeleri))
    if celiski:
        geri_al()
        k.not_dus("kural", "onaydan sonraki çatı setinde çatı sözü seçimle çelişiyor ya da okunamadı: soru")
        return t, _cati_sorusu(k, st)
    if onay_soru:
        if not acik:                                           # açık çatı seçimi yok: okumanın izi kalmaz
            geri_al()
            if t.niyet == "onay":
                k.not_dus("kural", "çatı seti açıkken onay: plan zaten onaylandı, çatı bekleniyor")
                return t, _cati_sorusu(k, st)
            return t, None
        k.not_dus("kural", f"çatı seti açıkken {'onay' if t.niyet == 'onay' else 'soru'} sözüyle çatı seçimi: {secim}")
    if isinstance(secim, Karar):
        return t, secim
    if not secim:
        k.d["son_metin"] = son_metin0
        if _cati_adiminda_istek_yok(k, t, metin, secim_metni):
            k.not_dus("kural", "onaydan sonraki çatı setinde seçim ve istek yok: soru")
            return t, _cati_sorusu(k, st)
        _cati_adimini_kapat(k, st, "çatı seçimi yerine başka istek")
        if yeni_musteri:                                       # hakem tur 4, B7: eski müşterinin özel isteği ve bina özelliği (LLM'in
            ts0 = k.d.get("taslak") or {}                      # bağlamdan yinelemesi) başka müşterinin talebine taşınmaz
            eski_bo = ts0.get("bina_ozellikleri") or {}
            t = t.model_copy(update={
                "ozel_istekler": [x for x in t.ozel_istekler if x not in (ts0.get("ozel_istekler") or [])],
                "bina_ozellikleri": {a: v for a, v in (t.bina_ozellikleri or {}).items() if eski_bo.get(a) != v}})
        if not (baska or yeni_soz or yeni_musteri):
            # hakem tur 3: talep bayinin sözünde değişmedi (yukarıda okundu); LLM'in m², oda, ölçü, kat ve yapı okuması ("salon 25 m2" →
            # evin alanı 25) ya da bağlamdan yinelemesi taslağa yazılmaz; tur 4: sözde olmayan pencere okuması da
            t = t.model_copy(update={"alan_m2": None, "oda_programi": None, "dis_olcu": None, "kat_sayisi": None, "yapi_turu": None,
                                     **_sozdeki_pencere_alanlari(t, icerik)})
        return t, None
    secim = str(secim)
    a0 = katalog.aday(secim)
    gosterim = SC.gosterim(a0) if a0 else secim
    if celik_mi and k.cati_numara_metni is not None:           # çelik: numara cümlesi revizyonda koda çevrilir (hakem tur 2, O7)
        k.cati_adimi_metni = f"{gosterim} olsun" + (f", {k.cati_numara_metni}" if ek and k.cati_numara_metni else "")
    else:                                                      # soru cümlesi ve onay sözü revizyona girmez (hakem tur 3)
        k.cati_adimi_metni = secim_metni if ek else f"{gosterim} olsun"
    _seti_kapat(k, secim)
    _cati_secildi(k, secim)
    k.d.pop("cati_adimi", None)
    k.cati_adimi_secimi = secim                                # `karar_ver`: istek geri çevrilir ya da plan değişmezse çatı seçimi düşmez
    if secim.upper() == str(ca["kod"]).upper() and not ek:
        k.not_dus("kural", f"onaydan sonraki çatı setinde evin çatısı: {secim}; plan r{rev:02d} onaylandı")
        return t, _onay_kaydet(k, katalog, cati=secim)
    k.cati_secimi = secim
    k.cati_adi = _cati_adi(a0) if a0 else ""
    k.cati_metni = f"Çatı: {k.cati_adi} ({gosterim})." if a0 else ""
    if ek:
        k.d["cati_onayi_dustu"] = rev                          # çatıyla birlikte plan da değişiyor: onay düşer (yalnız çatı değişirse
                                                               # `_is_emri_uret`/`_celik_is_emri_uret` bu notu kaldırır: "Plan aynı.")
    k.not_dus("kural", f"onaydan sonraki çatı setinden seçim: {secim}" + (" (mesajda başka istek ya da bilgi de var)" if ek else ""))
    # hakem tur 3: çatı seçiminin revizyonu LLM'in talep alanlarını taşımaz (talep değişikliği yukarıda bayinin sözünden okundu); istek
    # cümlesi yoksa LLM'in bağlamdan yinelediği pencere, varyant ve özel istek de taşınmaz
    temiz = {"niyet": "revizyon", "katalog_kodu": secim, "alan_m2": None, "oda_programi": None, "dis_olcu": None, "kat_sayisi": None,
             "yapi_turu": None}
    if not ek:
        temiz.update({"pencereler": [], "varyantlar": [v for v in t.varyantlar if v.tur == "cati_degistir"], "ozel_istekler": []})
    else:                                                      # hakem tur 4, Y5: sözde olmayan pencere okuması taşınmaz
        temiz.update(_sozdeki_pencere_alanlari(t, icerik))
    return t.model_copy(update=temiz), None


def _prefabrik_cati_seti(k: Konusma, katalog: Katalog, taban: dict, ts: dict) -> Karar | None:
    """İE-37 (D-83): prefabrik ev alan setinden (ya da kodla) seçildi, çatı yazılmadı → evin çatı seti (evin kendi çatısı ve kayıtlı çatı
    seçenekleri; tek görsel, numara ve düğme; öncelik sorusu yok). Kartın görseli çatının ön ve sol görünüşü (`cati_gorsel`), adı
    `cati_adi`. Görünür seçenek yoksa (K-A10 kabul kaydı yok) None: plan evin kendi çatısıyla çizilir (bugünkü yol)."""
    uygun = [taban] + [v for v in (katalog.aday(x) for x in taban.get("varyantlar") or []) if v is not None]
    if len(uygun) < 2:
        return None
    _seti_kapat(k, taban["kod"])
    k.d["taslak"]["katalog_kodu"] = taban["kod"]
    eski = k.d.get("secenek_seti")
    if eski and eski.get("durum") == "secildi":
        k.d.setdefault("eski_setler", []).append(eski)
        k.d["eski_setler"] = k.d["eski_setler"][-5:]
    k.not_dus("kural", f"plan seçildi, çatı sonra: {taban['kod']} çatı seti (prefabrik)")
    k.d["soru_sayisi"] = max(0, int(k.d.get("soru_sayisi") or 0) - 1)   # çatı seti planın seçimiyle aynı soru (İE-25 gibi)
    sunulan = [{**a, "sunum": {**(a.get("sunum") or {}), "cati_adi": a.get("cati_adi")}, "gorsel": a.get("cati_gorsel") or a.get("gorsel")}
               for a in uygun]
    return _secenekler(k, katalog, ts, uygun=SC.cati_seti(sunulan), tur="cati_varyanti", referans=sunulan[0])


# İE-37 (geometri hakemi, üç tur): prefabrik evde bayinin çatı cümlesi. Bu köklerden birini taşıyan cümle çatı cümlesidir. Çatıyı yalnız
# seçeneğin kodu seçer ("PA-06-K olsun"); çatının adı ("kırma", "cumbalı") seçtirmez, çatı setini getirir: ek ve kuruluş ("cumbasız",
# "kırmadan farklı") okunmaz, tahmin yok (K21). Cümle yalnız seçeneklerin adı, model kodu ve bağlam sözcükleriyle kurulmamışsa (eğim,
# saçak, kaplama, renk, başka oda ya da cephe, sayı) istek seçeneklerin dışındadır: bugünkü gibi yönlendirilir (13.10 kuralı).
_CATI_KOKLERI = ("cati", "sacak", "mahya", "kiremit", "trapez", "shingle", "kalkan", "makas", "cumba", "kirma", "besik")
_CATI_ZAYIF = ("egim", "kaplama", "sandvic", "membran", "oluk", "dere", "osb")     # yalnız LLM çatı isteği okuduysa çatı sözü
_CATI_BAGLAM = {"olsun", "olacak", "olur", "olabilir", "olsa", "olmali", "mu", "mi", "misiniz", "musunuz", "yapin", "yapiniz", "yapalim",
                "yapilsin", "yapilabilir", "yapar", "istiyoruz", "isteriz", "istiyorum", "isterim", "istiyor", "tercih", "ediyoruz", "ediyorum",
                "edelim", "secelim", "sectik", "seciyoruz", "secin", "da", "de", "ile", "ve", "bir", "bu", "su", "o", "zaman", "ev", "evin",
                "evde", "model", "modeli", "plan", "plani", "olarak", "tipi", "tip", "seklinde", "sekli", "farkli", "baska", "ustunde",
                "ustune", "uzerinde", "uzerine", "lutfen", "tamam", "evet", "seciyorum", "sectim", "rica", "ederim", "ederiz", "olan",
                "olani", "olsun", "onu", "bunu", "ilk", "birinci", "ikinci", "ucuncu", "son", "sonuncu", "ortadaki", "sondaki",
                "gorelim", "bakalim", "olmasi", "yapilmasi", "istek", "istegi", "isteniyor", "ama", "fakat", "yap", "yapalim", "yapsin",
                "yapiyoruz", "yapacagiz", "gecelim", "gecin", "gecsin", "gecilsin", "gecis", "alalim", "alacagiz", "aliyoruz",
                "secildi", "secilsin", "secilen", "secim", "secimi", "kullanalim", "kullanilsin", "uygulayin", "uygulansin"}
_NUMARA = {"numarali", "numara", "nolu", "no", "sira", "sirada", "secenek", "secenegi"}
_SIRA_SOZU = {"ilk": "1", "birinci": "1", "ikinci": "2", "ucuncu": "3"}            # açık sette sıra sözü numaradır ("ikinci çatı olsun")
_KALSIN_BAGLAM = {"simdilik", "oldugu", "gibi", "hali", "haliyle", "mevcut", "kendi", "eski"}  # "çatı olduğu gibi kalsın"
_CATI_DISI = ("zemin", "doseme", "duvar", "rampa", "merdiven", "parke", "laminat", "seramik", "fayans")   # zayıf kökün çatı dışı öznesi
_CATI_EKLERI = {"", "i", "a", "e", "u", "si", "su", "yi", "yu", "ya", "ye", "ni", "nu", "da", "de", "ta", "te", "in", "un", "nin", "nun",
                "dan", "den", "nda", "nde", "ndan", "nden", "li", "lu", "siz", "suz", "sini", "sinin", "sina", "sinda", "ler", "lar"}


def _cati_govdesi(w: str) -> str:
    """Kart adındaki sözcüğün gövdesi ("salonda" → "salon"); gövde en az 4 harf kalır."""
    return w[:-2] if w.endswith(("da", "de")) and len(w) >= 6 else w


def _cati_adi_mi(w: str, adlar: set[str]) -> bool:
    """Sözcük bir seçeneğin adının gövdesi, yalın ya da bilinen bir ekle ("salonun", "cumbalı", "kırmadan")."""
    return any(w.startswith(g) and w[len(g):] in _CATI_EKLERI for g in adlar)


def _kodlari_ayir(sozler: list[str], adlar: dict) -> tuple[list[str], set[str]]:
    """Cümleden model kodlarını çıkarır ("pa 06 k", "pa06k", kesme ekiyle "pa 06 k yi"): kalan sözler ve yazılı kodlar. Harf yalnız
    seçeneğin kodu olunca koda katılır ("PA-06 e" evin kodu)."""
    i, kalan, yazili = 0, [], set()
    while i < len(sozler):
        w = sozler[i]
        if re.fullmatch(r"pa\d{2}[a-z]?", w):
            yazili.add(w.upper()); i += 1
        elif w == "pa" and i + 1 < len(sozler) and re.fullmatch(r"\d{2}", sozler[i + 1]):
            harf = sozler[i + 2] if i + 2 < len(sozler) and len(sozler[i + 2]) == 1 else ""
            harf = harf if harf and f"PA{sozler[i + 1]}{harf.upper()}" in adlar else ""
            yazili.add(f"PA{sozler[i + 1]}{harf.upper()}"); i += 3 if harf else 2
        else:
            kalan.append(w); i += 1
            continue
        if i < len(sozler) and sozler[i] and sozler[i] in _CATI_EKLERI:
            i += 1                                             # kesme eki ("PA-06-K'yı")
    return kalan, yazili


def _okundu_mu(w: str, okunan: set[str]) -> bool:
    """LLM'in çatı isteğindeki söz bu mesajda okunan bir cümlede ya da bağlamda var (ilk 4 harfi aynı: "yapılsın" ~ "yapılması")."""
    return any(w == o or (len(w) >= 4 and len(o) >= 4 and w[:4] == o[:4] and (w.startswith(o) or o.startswith(w) or w[:5] == o[:5]))
               for o in okunan | _CATI_BAGLAM)


def _cati_sorusu(k: Konusma, st: dict) -> Karar:
    """Açık çatı setinde seçim yapılmadı: "Hangi çatı olsun?" (set açık kalır; numara, kod ya da düğme seçer)."""
    satirlar = "\n".join(f"{a.get('sira')}. {SC.gosterim(a)}" + (f" ({ad})" if (ad := (a.get("sunum") or {}).get("cati_adi")) else "")
                         for a in st.get("adaylar") or [])
    notu = getattr(k, "cati_sorusu_notu", "")
    return _soru(k, "secenek", f"Hangi çatı olsun?\n\n{satirlar}\n\nNumarasını ya da kodunu yazın." + (f"\n\n{notu}" if notu else ""))


def _prefabrik_cati_istegi(k: Konusma, katalog: Katalog, aday: dict, ts: dict, bos_ise_yok: bool = False) -> str | Karar | None:
    """İE-37 (geometri hakemi, 12 Kasım 2026; sekiz tur): çatı seçenekli prefabrik evde bayinin bu mesajı cümle cümle okunur (K18).
    - Çatıyı yalnız kod seçer: seçeneğin kodu ("PA-06-K olsun"), açık çatı setinde evin kodu ya da etiket harfi ("çatı K olsun"), düğme,
      numara. Tek kod, olumsuz söz yok ve aynı mesajdaki çatı adları o seçeneğin adıysa kod döner; kod ile çelişen ad ("PA-06-K olsun,
      cumbalı olsun"), iki kod ya da olumsuz söz kararsızlıktır: çatı seti (set açıksa soru). Tahmin yok (K21).
    - Çatının adı ("kırma", "salonun üstünde cumba"; bilinen eklerle) seçim yapmaz, çatı setini getirir; ek ve kuruluş okunmaz.
    - Seçeneklerin dışında bir şey isteyen çatı cümlesi (eğim, saçak, kaplama, renk, başka oda ya da cephe, sayı) ve önceki mesajdan kalan
      çatı isteği (LLM `cati_degistir`, bu mesajda çatı cümlesi yok) bugünkü gibi yönlendirilir; mesaj isteği ve seçilebilecek çatıları yazar
      (13.10 kuralı: istek sessizce düşmez).
    - Çatı seti açıkken seçim yoksa plan evin çatısıyla çizilmez: "Hangi çatı olsun?" (aynı mesajdaki pencere isteği taslakta bekler).
    Çatı içeriği yoksa ve set açık değilse ya da evin görünür seçeneği yoksa None: bugünkü yol. İE-42: `bos_ise_yok` (onaydan sonraki
    çatı seti) set açıkken de çatı içeriği olmayan mesajda None döner (mesaj planın değişikliğidir, set kapanır)."""
    taban = katalog.aday(Katalog.taban_kod(aday.get("kod")))
    if taban is None or not taban.get("varyantlar"):
        return None
    uygun = [taban] + [v for v in (katalog.aday(x) for x in taban["varyantlar"]) if v is not None]
    if len(uygun) < 2:
        return None
    st = k.d.get("secenek_seti") or {}
    set_acik = st.get("durum") == "acik" and st.get("tur") == "cati_varyanti"
    istekler = [v for v in ts.get("varyantlar") or [] if v.get("tur") == "cati_degistir"]
    metin = k.d.get("son_metin") or ""
    adlar: dict[str, set[str]] = {}                       # seçeneğin adı: çatı tipinin ve kart adının gövdeleri
    for a in uygun:
        yol = katalog.sablon_yolu(a["kod"])
        tip = str(((json.loads(yol.read_text(encoding="utf-8")) if yol else {}).get("cati") or {}).get("tip") or "")
        adlar[a["kod"]] = {_cati_govdesi(w) for w in CO.norm(tip.replace("_", " ") + " " + str(a.get("cati_adi") or "")).split() if len(w) >= 4}
    tum_ad = set().union(*adlar.values())
    harfler = {c[len(taban["kod"]):].lower(): c for c in adlar if c != taban["kod"]}       # etiket harfi: k → PA06K
    olumsuz, uygulanamaz, cati_cumlesi, kodlar, ad_sozleri, yazili = False, [], False, set(), [], set()
    kalsin_adlari, okunan = [], set()                          # "cumba kalsın" adları yalnız kodla çelişki için; okunan: LLM isteğinin kıyası
    son_sira = str(max([int(a.get("sira") or 0) for a in st.get("adaylar") or []] or [0]))
    for ham in re.split(r"[.,;:!?\n]+", metin):
        kalan, kod_sozu = _kodlari_ayir(CO.norm(ham).split(), adlar)   # seçimi `_secim_kodlari` da okur
        yazili |= kod_sozu
        olumsuz = olumsuz or any(CO._OLUMSUZ_FIIL_T.fullmatch(w) for w in kalan)
        etiket = [w for w in kalan if w in harfler]
        baska_yok = not (bos_ise_yok and any(w in _BASKA_SOZU for w in kalan))   # İE-42 (hakem tur 5): "farklı K olsun" seçim değil
        if bos_ise_yok and _eksiltili(ham):
            baska_yok = False                                  # İE-42 (hakem tur 8, Y1): "2 de", "ikinciye de" seçim değil
        # İE-42 (hakem tur 5, D1): onaydan sonraki sette devam ve alma sözü de etiket cümlesidir ("K ile devam edelim", "K'yı alın")
        if etiket and baska_yok and all(w in harfler or w in _CATI_BAGLAM or w.startswith("cati")
                                        or (bos_ise_yok and (w in _SECIM_NEZAKET or w in _CATI_EKLERI)) for w in kalan):
            kodlar |= {harfler[w] for w in etiket}             # "çatı K olsun", "K olsun": set mesajının etiketi
            okunan |= set(kalan)
            continue
        sira = {**_SIRA_SOZU, "son": son_sira, "sonuncu": son_sira}
        # İE-42 (hakem tur 4, D-D): onaydan sonraki sette (`bos_ise_yok`) ekli sıra sözü ve hitap, teşekkür sözü de numara cümlesidir
        sira_kok = (lambda w: _sira_kok(w, sira)) if bos_ise_yok else (lambda w: w if w in sira else None)
        if set_acik:
            kalan = _sira_baglami(kalan, sira)                 # İE-42 (hakem tur 8, Y3): "son haliyle", "son olarak" çatı numarası değil
        sayi = [w for w in kalan if w.isdigit()] + [sira[sira_kok(w)] for w in kalan if sira_kok(w)]
        if set_acik and baska_yok and len(sayi) == 1 and all(w.isdigit() or sira_kok(w) or w in _CATI_BAGLAM or w.startswith("cati")
                                                             or w in _NUMARA or (bos_ise_yok and _nezaket(w)) for w in kalan):
            kodlar |= {a["kod"] for a in st.get("adaylar") or [] if str(a.get("sira")) == sayi[0]}   # "2 numaralı", "ikinci çatı olsun"
            okunan |= set(kalan) | set(sayi)
            continue
        if bos_ise_yok and set_acik and _kendi_catisi_cumlesi(kalan):
            kodlar.add(taban["kod"])                           # İE-42 (hakem tur 4): "evin kendi çatısı olsun", "olduğu gibi kalsın"
            okunan |= set(kalan)
            continue
        if any(CO._KALSIN_T.fullmatch(w) or w == "ayni" for w in kalan) and all(
                CO._KALSIN_T.fullmatch(w) or w == "ayni" or w in _KALSIN_BAGLAM or w in _CATI_BAGLAM or w.startswith("cati")
                or _cati_adi_mi(w, tum_ad) for w in kalan):
            kalsin_adlari += [w for w in kalan if _cati_adi_mi(w, tum_ad)]   # "PA-06-K olsun, cumba kalsın": kodla çelişir (hakem yedinci tur)
            okunan |= set(kalan)
            continue                                           # "çatı aynı kalsın", "kırma kalsın": istek değil (13.10 kuralı); "cumba yatak
                                                               # odasının üstünde kalacak" bir istektir, aşağıda okunur (hakem altıncı tur)
        guclu = any(w.startswith(c) for w in kalan for c in _CATI_KOKLERI)
        zayif = istekler and any(w.startswith(c) for w in kalan for c in _CATI_ZAYIF) and not any(w.startswith(_CATI_DISI) for w in kalan)
        if not (guclu or zayif):
            continue                                           # çatı cümlesi değil (pencere, oda, zemin, rampa …): kendi yolundan
        if not all(w in _CATI_BAGLAM or w.startswith(("cati", "degis")) or _cati_adi_mi(w, tum_ad)
                   or CO._OLUMSUZ_FIIL_T.fullmatch(w) for w in kalan):
            if istekler:                                       # LLM çatı isteği okudu: seçeneklerin dışında, yönlendirilir
                uygulanamaz.append(ham.strip())
            continue                                           # okumadıysa bugünkü yol (cümle prefabrikte okunmuyordu)
        cati_cumlesi = True
        okunan |= set(kalan)
        ad_sozleri += [w for w in kalan if _cati_adi_mi(w, tum_ad)]
    yazili |= set(_secim_kodlari(metin, katalog))
    kodlar |= {c for c in yazili if c in adlar and (c != taban["kod"] or set_acik)}
    if taban["kod"] in yazili and any(c in adlar and c != taban["kod"] for c in yazili):
        olumsuz = True                                         # evin kodu ve bir çatı kodu birlikte ("şimdilik PA-06, PA-06-K'yı da görelim")
    if istekler and not cati_cumlesi and not kodlar:
        uygulanamaz += [str(v.get("aciklama") or "çatı değişikliği") for v in istekler]   # önceki mesajın isteği: bugünkü gibi
    for v in istekler:                                         # hakem yedinci tur: LLM'in okuduğu istek ("yağmur oluğu", "baca") okunan
        soz, _ = _kodlari_ayir(CO.norm(str(v.get("aciklama") or "")).split(), adlar)     # cümlelerde yoksa kodla da düşmez: yönlendirilir
        if any(not (_okundu_mu(w, okunan) or w.startswith(("cati", "degis")) or _cati_adi_mi(w, tum_ad) or w == "ayni"
                    or CO._OLUMSUZ_FIIL_T.fullmatch(w) or CO._KALSIN_T.fullmatch(w)) for w in soz):
            uygulanamaz.append(str(v.get("aciklama")))
    if uygulanamaz:
        secenek = ", ".join(SC.gosterim(a) + (f" ({a['cati_adi']})" if a.get("cati_adi") else "") for a in uygun)
        return _bitir(k, Karar(eylem="yonlendir", gerekce="prefabrik çatı isteği seçeneklerin dışında",
                                mesaj=f"\"{_kisalt(uygulanamaz[0])}\" isteği otomatik yapılamıyor; bu evde çatı için şunlar seçilebilir: {secenek}. "
                                      + YONLENDIRME))
    if not (kodlar or ad_sozleri or istekler or cati_cumlesi or (set_acik and not bos_ise_yok)):
        return None                                            # çatı içeriği yok: bugünkü yol (plan evin çatısıyla; İE-42)
    ts["varyantlar"] = [v for v in ts.get("varyantlar") or [] if v.get("tur") != "cati_degistir"]
    if len(kodlar) == 1 and not olumsuz:
        secilen = next(iter(kodlar))
        if all(_cati_adi_mi(w, adlar[secilen]) for w in ad_sozleri + kalsin_adlari):
            _seti_kapat(k, secilen)
            _cati_secildi(k, secilen)
            k.not_dus("kural", f"çatı seçimi kodla: {secilen}")
            return secilen
    k.not_dus("kural", "çatı seçimi yok ya da kararsız: çatı seti")
    if set_acik:
        return _cati_sorusu(k, st)
    return _prefabrik_cati_seti(k, katalog, taban, ts)


def _aday_mahalleri(aday: dict) -> list[dict]:
    """Çelik adayın oda adları (cümle bölme oda adlarını tanısın); tanım okunamazsa boş (zarf aşaması tanımı ayrıca doğrular)."""
    try:
        return list(celik.tanim_oku(aday).get("mahaller") or [])
    except (KeyError, OSError, ValueError):
        return []


# ── İE-14 · talepten plana (D-18) ─────────────────────────────────────────────────────────────────────────────────────
PLAN_URETIMI = "plan üretimi: uyan çelik model yok"
YENI_ONEK = "YENI-"


KURALA_UYMADI = "yeni plan: istek kurallara uymadı"         # Lokman 16.10 (G): gerekçede bu söz varsa worker Patron'a bilgi verir


def _istekler(liste) -> str:
    """Bayiye adıyla yazılan istekler: en çok üç, maskeli ve 80 karakter; kalanı sayıyla ("ve 2 istek daha"; hakem 16.10, sessiz düşmez)."""
    liste = [str(x) for x in liste or []]
    return "; ".join(f"\"{numara.maskele(x)[:80]}\"" for x in liste[:3])


def _istek_fazlasi(liste) -> str:
    n = len(list(liste or [])) - 3
    return f" (ve {n} istek daha)" if n > 0 else ""


def _m2(x) -> str:
    """Bayiye giden m²: Türkçe, bir ondalık ("95,1"; "95,03" → "95"; "88.0" → "88"); plan kartıyla aynı (`motor/bayi_gorseli._tr`,
    Lokman 12.10). Canlı deneme 16.10 (E): mesaj "95.03 m²", kart "95 m²" yazıyordu."""
    try:
        t = f"{float(x):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(x)
    return t[:-2] if t.endswith(",0") else t


def plan_uretimi_uygun(ts: dict) -> bool:
    """Üretim yalnız tek kat çelikte ve çözülebilen oda programıyla (14a): '3+1' gibi. Çift kat ve tanınmayan program bugünkü yolda kalır."""
    from .plan_denetim import program_coz
    return program_coz(ts.get("oda_programi")) is not None and (ts.get("kat_sayisi") in (None, 1))


def plan_talebi(ts: dict, alan: float) -> dict:
    """Üreticiye giden talep (yapısal; müşteri adı, numara ve adres yok — LLM'e gerekmez)."""
    return {"alan_m2": float(alan), "oda_programi": ts.get("oda_programi"), "yapi_turu": "celik", "kat_sayisi": 1,
            "cati": {"tip": (ts.get("cati") or {}).get("tip")}, "veranda": {a: (ts.get("veranda") or {}).get(a) for a in ("istiyor", "konum", "alan_m2")},
            "dis_olcu": ts.get("dis_olcu"), "ozel_istekler": [numara.maskele(str(x)) for x in ts.get("ozel_istekler") or []]}
    # KVKK (kapanış): LLM'in serbest özeti (ad, adres taşıyabilir) üreticiye gitmez; yapısal alanlar yeter (Z-08 açık iş)


def _aday_bul(k: Konusma, katalog: Katalog, kod: str | None) -> dict | None:
    """Banka adayı ya da bu konuşmada üretilen plan (`k.d['uretilen_plan']`; r3: setteki öteki üretilen plan `uretilen_planlar`'da). Seçilen
    üretilen plan `_celik_dali`'da `uretilen_plan` olur (revizyon ondan sürer); burada yan etki yok (set galerisi her adayı arar)."""
    if kod:
        for u in [k.d.get("uretilen_plan")] + list(k.d.get("uretilen_planlar") or []):
            if u and str(kod).strip().upper() == str(u.get("kod")).upper():
                return u
    return katalog.aday(kod)


YOL_ADI = {"uyarlama": "bankadaki bir modelden uyarlandı", "cozucu": "programdan çözüldü", "llm_program": "programdan çözüldü"}


def uretilen_aday(sonuc: dict, istek: dict, kart: str | None, sira: int = 1) -> dict:
    """Üretim sonucu (ya da r3'te tek aday) → aday kaydı biçiminde (tanım gömülü, durum 'uretilen'; banka adayı değil, K-A10 dışında; D-18).
    Uyarlamanın kaynak modeli bayiye yazılmaz (adsız; Lokman 14.10, 5. madde)."""
    import hashlib
    tanim = sonuc["tanim"]
    tohum = str(istek.get("mesaj_id") or json.dumps(istek.get("talep"), sort_keys=True)) + ("" if sira == 1 else f":{sira}")
    kod = YENI_ONEK + hashlib.sha256(tohum.encode()).hexdigest()[:6].upper()
    tanim = {**tanim, "kod": kod}
    oz = sonuc.get("ozet") or {}
    ver = 0.0
    for m in tanim["mahaller"]:
        if m.get("sinif") == "veranda" and m.get("poligon"):
            q = m["poligon"]
            ver += abs(sum(q[i][0] * q[(i + 1) % len(q)][1] - q[(i + 1) % len(q)][0] * q[i][1] for i in range(len(q)))) / 2 / 1e4
    from .plan_denetim import program_coz
    p = program_coz(istek["talep"].get("oda_programi"))
    return {"kod": kod, "gosterim": "Yeni plan" if sira == 1 else f"Yeni plan {sira}", "durum": "uretilen", "uretilen": True, "motor": "genel",
            "yapi_turu": "celik", "kat": 1, "yol": sonuc.get("yol"), "dogrulama": sonuc.get("dogrulama"),
            "tanim": tanim, "tanim_sha256": celik.tanim_sha_icerik(tanim), "gorsel": kart, "plan": sonuc.get("plan"),
            "oda_programi": f"{p[0]}+{p[1]}" if p else istek["talep"].get("oda_programi"), "katalog_m2": oz.get("brut_m2"),
            "kapali_m2": round(sum((oz.get("odalar_m2") or {}).values()), 2) or None, "veranda_m2": round(ver, 2) if ver else None,
            "sunum": {"ad": "Yeni plan (TASLAK)", "cati_adi": tanim["cati"].get("tip_adi")}, "referans_model": None, "varyantlar": [],
            "ozet": {"dis_olcu_cm": oz.get("dis_olcu_cm"), "odalar": oz.get("odalar_m2")}}


def plan_sonucu(k: Konusma, katalog: Katalog, sonuc: dict, kart=None) -> Karar:
    """İE-14 · worker'ın üretim sonucu → karar. Geçerliyse seçenek seti: üretilen planlar (r3: en çok 2; uyarlama ve çözücü puanla), ardından
    bankadan brüt alanı en yakın çelik modeller; görsel ve düğme en çok 3 (`SC.EN_COK_GORSEL`). Son basamakta (LLM programı) programdan
    değişen her şey bayiye yazılır. Geçersizse "uygulayamadım" ve Patron'a (yönlendirme; köprü sürer). `kart`: tek yol ya da liste."""
    istek = k.d.pop("plan_istegi", None) or {}
    talep = istek.get("talep") or {}
    alan = talep.get("alan_m2")
    uretilen = [a for a in (sonuc.get("adaylar") or ([sonuc] if sonuc.get("tanim") else [])) if a.get("tanim")]
    if sonuc.get("durum") != "gecerli" or not uretilen:
        neden = sonuc.get("hata") and "üretim hatası" or "kurallara uyan yerleşim çıkmadı"
        k.not_dus("kural", f"yeni plan üretilemedi: {neden}")
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"yeni plan üretilemedi ({neden})",
                                mesaj=f"{alan:g} m² {talep.get('oda_programi')} çelik için kurallara uyan yeni bir planı otomatik çizemedim. " + YONLENDIRME
                                if isinstance(alan, (int, float)) else "Kurallara uyan yeni bir planı otomatik çizemedim. " + YONLENDIRME))
    kartlar = list(kart) if isinstance(kart, (list, tuple)) else [kart]
    yeniler = [uretilen_aday(a, istek, kartlar[i] if i < len(kartlar) else None, i + 1) for i, a in enumerate(uretilen[:SC.EN_COK_GORSEL - 1])]
    k.d["uretilen_plan"] = yeniler[0]
    k.d["uretilen_planlar"] = yeniler
    varyant_kodlari = {v for a in katalog.gorunur_adaylar() for v in (a.get("varyantlar") or [])}
    banka = sorted((a for a in katalog.gorunur_adaylar() if a.get("motor") == "genel" and a.get("yapi_turu") == "celik"
                    and a["kod"] not in varyant_kodlari and isinstance(a.get("katalog_m2"), (int, float))),
                   key=lambda a: (abs(a["katalog_m2"] - (alan or 0)), a["kod"]))[:max(1, SC.EN_COK_GORSEL - len(yeniler))]
    uygun = [{**y, "tanim": None, "plan": None, "sira": i, "puan": None, "hesap": "yeni plan"} for i, y in enumerate(yeniler, 1)] + \
            [{**a, "sira": i, "puan": None, "hesap": "bankadan en yakın"} for i, a in enumerate(banka, len(yeniler) + 1)]
    kaynak_id = istek.get("mesaj_id") or f"{k.gonderen}:{int(time.time())}"
    st = SC.set_kaydi(kaynak_id, uygun, {"alan_m2": alan, "oda_programi": talep.get("oda_programi")}, tur="yeni_plan")
    eski = k.d.get("secenek_seti")
    if eski and eski.get("durum") == "acik" and eski.get("id") != st["id"]:
        eski["durum"] = "eskidi"
        k.d.setdefault("eski_setler", []).append(eski)
        k.d["eski_setler"] = k.d["eski_setler"][-5:]
    k.d["secenek_seti"] = st
    k.d["son_soru_alani"] = "secenek"
    satirlar = [f"{y['sira']}. {y['gosterim']} · {_m2(y['katalog_m2'])} m² · {y['oda_programi']} · TASLAK, {YOL_ADI.get(y.get('yol'), 'yeni')}"
                + "".join(f" ({d})" for d in (uretilen[i].get("degisen") or [])[:2]) for i, y in enumerate(uygun[:len(yeniler)])]
    satirlar += [f"{a['sira']}. {SC.gosterim(a)} · {_m2(a['katalog_m2'])} m² · {a.get('oda_programi') or ''} (bankadan en yakın)" for a in uygun[len(yeniler):]]
    degisen = list(sonuc.get("degisen") or [])
    not_ = (f"\n\nİsteğinizi olduğu gibi sığdıramadım; şunları değiştirdim: {'; '.join(degisen)}.") if degisen else ""
    olmayan = [numara.maskele(str(x))[:80] for x in (sonuc.get("okunamayan") or []) + ((sonuc.get("program") or {}).get("uygulanamayan") or [])]
    if olmayan:
        not_ += "\n" + "; ".join(f"\"{x}\"" for x in olmayan[:3]) + " isteğini otomatik uygulayamadım; plan okuyabildiklerimle çizildi."
    notlar = [str(x) for x in sonuc.get("notlar") or []]                 # kodun varsayımları da bayiye yazılır (sessiz değişiklik yok; G1, G2)
    if notlar:
        not_ += "\nNot: " + "; ".join(notlar[:3]) + "."
    bas = "yeni bir plan taslağı" if len(yeniler) == 1 else f"{len(yeniler)} yeni plan taslağı"
    son = "\n\nBirini seçin (düğme ya da numara)."
    mesaj = (f"{_m2(alan)} m² {talep.get('oda_programi')} çelik için {bas} çizdim; bankadaki en yakın model de yanında. Mühendis kontrolü "
             f"onayınızdan sonra.\n\n" + "\n".join(satirlar) + not_)[:1024 - len(son)] + son
    butonlar = [{"id": f"s:{st['id']}:{a['kod']}", "baslik": (f"{a['sira']}. {a['gosterim']}" if a.get("uretilen") else f"{a['sira']}. {SC.gosterim(a)}")[:20]}
                for a in uygun[:SC.EN_COK_GORSEL]]
    k.not_dus("kural", f"yeni plan üretildi: {', '.join(y['kod'] for y in yeniler)} ({sonuc.get('yol') or 'yeni'})")
    return _bitir(k, Karar(eylem="secenek", soru_alani="secenek", mesaj=mesaj, secenek_seti=st, butonlar=butonlar,
                           gerekce=f"seçenek seti {st['id']}: yeni plan {' + '.join(y['kod'] for y in yeniler)} + bankadan {len(banka)}"))


def _set_acik(k: Konusma) -> bool:
    """Açık bir seçenek seti var mı (alan seti ya da çatı seti; prefabrik ya da çelik)?"""
    return (k.d.get("secenek_seti") or {}).get("durum") == "acik"


def _acik_plan_var(k: Konusma) -> bool:
    """Konuşmada bayiye gitmiş ve kapanmamış bir plan var mı (onay bekleyen, revizyondaki ya da onaylı)?"""
    return bool(k.d.get("son_is_emri")) and k.d.get("asama") in ACIK_PLAN_ASAMALARI


# BK-29 PR-3: model kodunun yanında seçim anlamı taşıyan sözcükler (normalize). Başka sözcük varsa (istek, olumsuz söz) mesaj LLM'in
# okumasıyla gider: "PA-04 olmasın", "PA-04 ile PA-05 farkı ne?", "PA-04'te mutfak penceresi 120x120" yalnız kod değildir.
_KOD_DOLGU = {"olsun", "olur", "istiyorum", "istiyoruz", "isterim", "isteriz", "seciyorum", "seciyoruz", "sectim", "sectik", "secelim",
              "alalim", "alayim", "lutfen", "tamam", "evet", "ok", "bu", "model", "modeli", "modelini", "plan", "plani", "planini",
              "secenek", "secenegi", "secenegini", "uygun", "iyi", "guzel", "hazirlayin", "hazirlar", "misiniz", "musunuz", "cizin", "gonderin"}


def _yalniz_kod(metin: str | None, katalog: Katalog) -> str | None:
    """Mesaj yalnız bir model kodu (ve seçim sözcükleri) taşıyorsa o kod (katalogda ya da aday kaydında görünür olmalı); değilse None."""
    kodlar, kalan = _model_kodlari_ve_kalan(metin, katalog)
    kodlar = list(dict.fromkeys(str(Katalog.kod_normalize(c) or "").upper() for c in kodlar))
    if len(kodlar) != 1 or any(w not in _KOD_DOLGU for w in CO.norm(kalan).split()):
        return None
    return kodlar[0]


_MUSTERI_SOZU = {"musteri", "musterisi", "musterimiz", "musterim"}
_AD_SOZU = {"adi", "ismi", "ad", "isim"}


def _kod_ve_musteri(metin: str | None, katalog: Katalog, llm_adi: str | None = None) -> tuple[str | None, str | None]:
    """Mesaj bir model kodu, seçim sözcükleri ve "müşteri <ad>" parçasından oluşuyorsa (kod, ad); değilse (None, None).
    Ad bayinin kendi sözünden alınır (K18): "müşteri" sözünden sonraki 1–4 sözcük, yalnız harf. Ad sayılması için sözcüklerin hepsi
    büyük harfle başlar ("Ayşe Kaya") ya da LLM'in okuduğu müşteri adıyla aynıdır ("müşteri adı ayşe kaya"). Başka söz taşıyan mesaj
    ("PA-04, müşteri salonu büyük istiyor", "PA-04 müşteri Ayşe Kaya, mutfak penceresi 120x120") bu kurala girmez; LLM'in okumasıyla gider."""
    kodlar, kalan = _model_kodlari_ve_kalan(metin, katalog)
    kodlar = list(dict.fromkeys(str(Katalog.kod_normalize(c) or "").upper() for c in kodlar))
    sozler = kalan.split()
    i = next((j for j, w in enumerate(sozler) if CO.norm(w) in _MUSTERI_SOZU), None)
    if len(kodlar) != 1 or i is None or any(CO.norm(w) not in _KOD_DOLGU for w in sozler[:i]):
        return None, None
    ad = sozler[i + 1:]
    if ad and CO.norm(ad[0]) in _AD_SOZU:
        ad = ad[1:]
    while ad and ad[-1][:1].islower() and CO.norm(ad[-1]) in _KOD_DOLGU:          # "… Ayşe Kaya olsun": sondaki seçim sözcüğü ad değil
        ad = ad[:-1]
    if not 1 <= len(ad) <= 4 or any(not w.isalpha() for w in ad):
        return None, None
    buyuk = all(w[:1].isupper() for w in ad)
    llm_ayni = bool(llm_adi) and _ad_sozcukleri(llm_adi) == _ad_sozcukleri(" ".join(ad))
    return (kodlar[0], " ".join(ad)) if (buyuk or llm_ayni) else (None, None)


def _celik_seti_acik(k: Konusma) -> bool:
    """Açık seçenek seti çelik mi (çatı seti ya da çelik adaylı alan seti)? Prefabrik setler bu kurallara girmez (A5)."""
    st = k.d.get("secenek_seti") or {}
    return st.get("durum") == "acik" and (st.get("tur") == "cati_varyanti" or any(a.get("motor") == "genel" for a in st.get("adaylar") or []))


def _celik_istek_sakla(k: Konusma) -> bool:
    """Set sunulurken (ya da set açıkken seçim yerine) gelen mesaj çelik değişiklik isteği taşıyorsa metni ve LLM ipuçları saklanır;
    seçimden sonra `_celik_degisiklikler` önce bunu okur (ilk mesajdaki "mutfak penceresi 120x120" düşmez, başka pencereye yazılmaz).
    Dönen: set mesajına "isteğinizi seçtiğiniz plana işleyeceğim" notu yazılsın mı (yalnız gerçek değişiklik isteğinde)."""
    m = k.d.get("son_metin") or ""
    llm = getattr(k, "son_llm", None) or {}
    if not (CO.hizli_istek(m) or llm.get("pencere") or llm.get("varyantlar")):
        return False
    notlu = CO.degisiklik_var(m) or bool(llm.get("pencere"))  # not yalnız gerçek değişiklik isteğinde (çatı sorusunda değil)
    eski = k.d.get("celik_istek") or {}
    eski_llm = eski.get("llm") or {}
    k.d["celik_istek"] = {"metin": "\n".join(x for x in (eski.get("metin"), m) if x)[-1000:],      # üst sınır (KVKK ikinci tur): son 1000 karakter
                          "llm": {"pencere": bool(eski_llm.get("pencere") or llm.get("pencere")),
                                  "varyantlar": list(eski_llm.get("varyantlar") or []) + list(llm.get("varyantlar") or [])}}
    k.not_dus("kural", "set sunulurken çelik değişiklik isteği saklandı")
    return notlu


def _bekleyen_devri(ob: dict) -> dict:
    """Okuma sorusu cevaplanınca sorudan önce hazırlanan değişiklikler, sorulmamış pencere cümleleri ve soru turunda okunan çatı (planın
    kodu; beşinci tur: cevapta son planın çatısına dönülüyor, çatı isteği sessizce düşüyordu) bir sonraki adıma geçer."""
    return {"kalan": list(ob.get("kalan") or []), "okunan": list(ob.get("okunan") or []), "kod": ob.get("kod")}


def _bekleyen_cati(k: Konusma, ob: dict) -> str | None:
    """Soru turunda okunup soruyla bekleyen çatı değişikliği (son planla aynı taban, başka varyant) varsa kodu."""
    son = str(((k.d.get("son_is_emri") or {}).get("yapi") or {}).get("kod") or "").upper()
    kod = str(ob.get("kod") or "").upper()
    return kod if (son and kod and kod != son and Katalog.taban_kod(kod) == Katalog.taban_kod(son)) else None


def _pencere_op(a: dict, en: int, yuk: int) -> dict:
    return {"op": "pencere_olcu", "aciklik": a["aciklik"], "en": int(en), "yuk": int(yuk), "aciklama": f"{a.get('aciklama', a['aciklik'])} → {int(en)}/{int(yuk)}"}


def _hazir_notu(ops: list[dict]) -> str:
    return ("Not aldım: " + "; ".join(CO.aciklama(d) for d in ops) + ". ") if ops else ""


def _okuma_sor(k: Konusma, ob: dict, yinele: bool = False) -> Karar:
    """İE-08 PR-2b: pencere okuması belirsiz. Seçim sorusu: iki adayda düğmeli "1 / 2 / Hiçbiri" (görseli worker `okuma_bekleyen`den
    çizer ve görsel gidiyorsa "Görselde 1 ve 2 ile işaretledim" der), üç ve daha çok adayda numaralı metin sorusu. Ölçü sorusu (tur 'olcu').
    Yinelenen soru aynı türdedir (kapanış incelemesi 13.10: yinelenen ölçü sorusu seçim sorusuna dönüyor, cevabı kabul edilmiyordu).
    Soruyla bekleyen hazır değişiklikler soruda söylenir. Soru sayacına girer (MAX_SORU)."""
    adaylar = list(ob.get("adaylar") or [])[:CO.EN_COK_ADAY]
    ob = {**ob, "adaylar": adaylar}
    k.d["okuma_bekleyen"] = ob
    cati = _bekleyen_cati(k, ob)
    bas = ("Anlayamadım. " if yinele else "") + _hazir_notu(([{"op": "cati_varyanti", "kod": cati}] if cati else []) + list(ob.get("hazir") or []))
    if ob.get("tur") == "olcu":
        odalar = {a.get("mahal") for a in adaylar}
        tarif = adaylar[0]["aciklama"] if len(adaylar) == 1 else (f"{next(iter(odalar))} penceresini" if len(odalar) == 1 and None not in odalar and "" not in odalar
                                                                  else "Pencereyi")
        return _soru(k, "okuma_olcu", f"{bas}{tarif} hangi ölçüye değiştirelim? (120x120, 120x180, 60x40 …)")
    en, yuk = ob.get("olcu") or (None, None)
    olcu = f" {en}x{yuk}" if en else ""
    if len(adaylar) == 2:
        mesaj = (f"{bas}Hangi pencereyi{olcu} yapalım? 1) {adaylar[0]['aciklama']}, 2) {adaylar[1]['aciklama']}. "
                 "\"1\", \"2\", \"ikisi de\" ya da \"hiçbiri\" yazmanız yeterli.")
        butonlar = [{"id": "q:okuma:1", "baslik": "1"}, {"id": "q:okuma:2", "baslik": "2"}, {"id": "q:okuma:0", "baslik": "Hiçbiri"}]
        return _soru(k, "okuma", mesaj, butonlar=butonlar)
    liste = "; ".join(f"{i}) {a['aciklama']}" for i, a in enumerate(adaylar, 1))
    return _soru(k, "okuma", f"{bas}Hangi pencereyi{olcu} yapalım? {liste}. Numarasını yazın (birden çoksa \"1 ve 3\", hepsi için \"hepsi\"; "
                             "ya da \"hiçbiri\").")


_BILGI_ETIKET = {"ad": "müşteri adı ismi isim", "sevk_adresi": "sevk adresi adres teslimat teslim"}


def _bilgi_cumlesi(p: dict, llm: dict) -> bool:
    """Revizyonda tanınmayan cümle antet ya da bina özellikleri bilgisi mi (renk, malzeme, müşteri adı, sevk adresi; LLM `bina_ozellikleri`,
    `musteri`)? Evet, ancak cümlenin tanınmayan **bütün** sözcükleri bu mesajın bilgi alanlarının adında ya da değerinde geçiyorsa ve
    cümle oda, ölçü ya da sayı taşımıyorsa (geometri hakemi ikinci tur: tek sözcük örtüşmesi "salonu büyütelim dış cephe gri olsun"u bütünüyle
    bilgi sayıp büyütmeyi düşürüyordu). Bilgi zarfa ve paftaya gider (sessiz düşme yok); sayılı cümle ("dış kapı 140 cm") bilgi değildir:
    çizimle çelişen bir değer tabloya yazılmasın."""
    metin = p.get("metin") or ""
    if re.search(r"\d", metin) or p.get("odalar") or any((p.get("isaret") or {}).values()):
        return False                                           # değişiklik işareti (çatı, pencere, dış 140, ekleme) taşıyan cümle bilgi değildir
    havuz: set[str] = set()
    for a, d in (llm.get("bilgi") or {}).items():
        if celik.satir_adi(a) in celik.GEOMETRI_SATIRLARI:
            continue                                           # çizimin geometrisi ya da sayısı ("Çatı Eğimi", "Dış Kapı"): değişiklik isteğidir (altıncı tur)
        havuz |= set(CO.norm(f"{_BILGI_ETIKET.get(a, a)} {d}").split())
    bilinmeyen = [w for w in p.get("bilinmeyen") or [] if len(w) >= 3]
    return bool(bilinmeyen) and all(w in havuz for w in bilinmeyen)


_NEYI_DEGISTIRELIM = ("Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120\"); çatı için \"çatı K\" ya da "
                      "\"çatı L\", dış duvar için \"dışlar 140'lık olsun\" yazabilirsiniz.")


_NEYI_DEGISTIRELIM_YALIN = "Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120\")"


def _dis140_uygulanir(t: dict, onceki: list[dict]) -> bool:
    """Dış 140 bu plana otomatik uygulanabilir mi: zaten 140 değil ve `dis_karkas_140` işlemi tanıma uygulanıyor (karkas modeli yok)."""
    if _zaten_140(t, onceki):
        return False
    try:
        varyant.tanim_uygula(t, {"op": "dis_karkas_140"})
        return True
    except varyant.VaryantHatasi:
        return False


def dis140_onerilir(yapi: dict | None) -> bool:
    """Çelik İş Emri'nin `yapi`sından: "dışlar 140'lık olsun" bu planda örnek gösterilir mi (`kanal/worker.form_cikarimi`, boş revizyon
    formu). Tanım okunamıyorsa False (yapılabildiği bilinmeyen örnek gösterilmez)."""
    y = yapi or {}
    onceki = [d for d in (y.get("degisiklikler") or []) if d.get("op") != "cati_varyanti"]
    try:
        t = celik.tanim_oku(y)
        for d in onceki:
            t = varyant.tanim_uygula(t, d)
        return _dis140_uygulanir(t, onceki)
    except Exception:                                          # kayıttaki tanım okunamadı ya da uygulanamadı: örnek gösterilmez, iş düşmez
        return False


def _celik_ornekleri(katalog: Katalog, aday: dict, t: dict, onceki: list[dict]) -> str:
    """Çelik planda "Neyi değiştirelim?" metni: yalnız bu planda otomatik yapılabilen örnekler (BK-29 pano 210 ilkesi; İE-20 PR-10,
    15 Kasım 2026 canlı denemesi: KT-03'te çatı seçeneği yok ve dış duvar zaten 140'lık, metin ikisini de öneriyordu). Çatı örneği
    yalnız çatı seçeneği olan modelde; dış 140 örneği yalnız bu plana uygulanabiliyorsa (zaten 140 değil, karkas modeli yok). İkisi de
    varsa metin `_NEYI_DEGISTIRELIM` ile aynıdır."""
    ek = []
    if _cati_kodlari(katalog, aday):
        ek.append("çatı için \"çatı K\" ya da \"çatı L\"")
    if _dis140_uygulanir(t, onceki):
        ek.append("dış duvar için \"dışlar 140'lık olsun\"")
    return _NEYI_DEGISTIRELIM_YALIN + ("; " + ", ".join(ek) + " yazabilirsiniz." if ek else ".")


def _celik_neyi(k: Konusma, katalog: Katalog) -> str:
    """`_celik_ornekleri`, konuşmadaki çelik plandan (son İş Emri; yoksa taslaktaki kod). Plan bulunamazsa genel metin."""
    y = (k.d.get("son_is_emri") or {}).get("yapi") or {}
    kod = y.get("kod") or (k.d.get("taslak") or {}).get("katalog_kodu")
    aday = _aday_bul(k, katalog, kod) if kod else None
    if aday is None or aday.get("motor") != "genel" or not celik.tanim_dogrula(aday):
        return _NEYI_DEGISTIRELIM
    onceki = [d for d in (y.get("degisiklikler") or []) if d.get("op") != "cati_varyanti"]
    try:
        t = celik.tanim_oku(aday)
        for d in onceki:
            t = varyant.tanim_uygula(t, d)
    except varyant.VaryantHatasi:
        return _NEYI_DEGISTIRELIM
    return _celik_ornekleri(katalog, aday, t, onceki)


_NEYI_DEGISTIRELIM_YENI = ("Planda neyi değiştirelim? Örneğin \"salonu 50 cm büyüt\", \"mutfağa 120x120 pencere ekle\", \"çatı kırma olsun\" ya da "
                           "\"dış duvarlar 140 olsun\" yazabilirsiniz; planı onaylıyorsanız Onayla'ya basın.")


_BASKA_DEGISIKLIK = "Başka bir değişiklik isterseniz yazın; planı onaylıyorsanız Onayla'ya basın."


def _bilgi_disi_cumle(k: Konusma, t: dict, aday: dict) -> bool:
    """Mesajda müşteri/antet bilgisi dışında bir cümle var mı (oda büyüt, kapı, çatı, pencere, belirsiz…)? Banka yolunun bilgi denetimi
    (`_bilgi_cumlesi`) cümle cümle; boş cümle sayılmaz (kod incelemesi üçüncü tur A: `degisiklik_var` oda ve kapı isteklerini tanımıyordu)."""
    try:
        y = varyant._kur(t)
    except varyant.VaryantHatasi:
        y = None
    r = CO.oku(k.d.get("son_metin") or "", t, aday, y=y)
    llm = getattr(k, "son_llm", None) or {}
    return any(p["tur"] != "bos" and not (p["tur"] == "baska" and _bilgi_cumlesi(p, llm)) for p in r["parcalar"])


def _yeni_plan_sorusu(k: Konusma, metin: str, gerekce: str = "yeni plan: değişiklik okunmadı") -> Karar:
    """Yeni plan revizyonunda soru: soru bütçesi işler, okuma alanı bırakılmaz ve plan bayide kalır (aşama `onay_bekliyor`): sonraki
    cevap yine LLM düzenleyicisine gider, bayi doğrudan onaylayabilir (ikinci tur bulgu 1)."""
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = "yeni_plan_degisiklik"
    k.d["asama"] = "onay_bekliyor"
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani="yeni_plan_degisiklik", mesaj=metin, gerekce=gerekce))


def _celik_degisiklikler(k: Konusma, katalog: Katalog, aday: dict, t: dict, onceki: list[dict], ayni_proje: bool,
                         kap_cumle: list[str] | tuple = ()) -> tuple[list[dict], set[str]] | Karar:
    """Bu mesajın (ve set sunulurken saklanan isteğin) çelik değişiklikleri, bayinin sözünden cümle cümle (K18). Dönen: ([op, …], okunan
    türler) ya da sorulacak/yönlendirilecek Karar. Sıra (kapanış incelemesi 13.10): önce desteklenmeyen LLM varyantı ve revizyonda tanınmayan
    cümle yönlendirilir (soru sormadan: sorulan soru öteki isteği düşürmesin), sonra ekleme/kaldırma, sonra revizyonda olumsuz ya da
    belirsiz cümle sorulur, en son pencere cümleleri sırayla çözülür (belirsiz olan için soru; öteki değişiklikler soruyla bekler).
    İlk planda (r01) tanınmayan cümle talep bilgisidir (bina özellikleri, özel istekler; zarfa gider)."""
    sec = k.d.pop("okuma_secilen", None)
    if sec:                                                     # okuma sorusu cevaplandı: hazır değişiklikler + kalan pencere cümleleri
        return _pencereleri_coz(k, aday, t, onceki, list(sec.get("hazir") or []), list(sec.get("kalan") or []), set(sec.get("okunan") or []))
    lo = getattr(k, "llm_degisiklik", None)
    if lo and lo.get("durum") == "tamam" and ayni_proje:      # İE-14 PR-3: LLM-önce revizyon okuması (ayar açıkken; worker hesaplar)
        return _llm_degisiklikler(k, katalog, aday, t, onceki, lo)
    istek = k.d.pop("celik_istek", None)
    metin = "\n".join(x for x in ((istek or {}).get("metin"), k.d.get("son_metin")) if x)
    llm = dict(getattr(k, "son_llm", None) or {})
    if istek:
        il = istek.get("llm") or {}
        llm = {**llm, "pencere": bool(il.get("pencere") or llm.get("pencere")),
               "varyantlar": list(il.get("varyantlar") or []) + list(llm.get("varyantlar") or [])}
    taban = katalog.aday(aday.get("referans_model")) if aday.get("referans_model") else None
    kat_aday = taban if (taban and taban.get("varyantlar")) else aday
    try:
        y = varyant._kur(t)                                     # cephe yüzlerden (L planda ortaya göre tahmin yanılabilir; geometri hakemi 13.10)
    except varyant.VaryantHatasi:
        y = None
    r = CO.oku(metin, t, kat_aday, ipucu=bool(llm.get("pencere")), y=y)
    # 0) çatı seçeneği olmayan modele (Ç8201, KT'ler) K/L çatı isteği sessizce düşmez (altıncı tur; PR-2a'dan kalma): revizyonda
    #    yönlendirilir, ilk planda plan katalog çatısıyla çizilir ve bu söylenir
    if not kat_aday.get("varyantlar") and any(p["tur"] == "cati" and not p["olumsuz"] and CO.cati_secenekleri(p["metin"]) & {"k", "l"}
                                              for p in r["parcalar"]):
        ad = aday.get("gosterim") or aday["kod"]
        if ayni_proje:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="çatı seçeneği olmayan modelde çatı isteği",
                                    mesaj=f"{ad} modelinin çatı seçeneği yok (yalnız katalog çatısı); çatı değişikliği otomatik yapılamıyor. " + YONLENDIRME))
        k.bekleyen_not = (k.bekleyen_not or "") + f"{ad} modelinin çatı seçeneği yok; plan katalog çatısıyla çizilir. "
    # 0b) "uygulayamadım" güvenlik ağı (Lokman, 13.10: ilk planda da revizyonda da değişiklik isteği taşıyan hiçbir cümle sessizce düşmez;
    #     okunamayan istek bayiye açıkça yazılır ya da yönlendirilir). Revizyonda okunamayan cümle aşağıda yönlendirilir; ilk planda
    #     pencere, dış 140, ekleme, çatı şekli ya da oda isteği taşıyan okunamayan cümle bayiye yazılır (cümle bölme yanılsa da istek görünür
    #     kalır). Çatı seçimi (kod, K/L, katalog) sayılmaz: onu kod ya da set belirler ("Ç8801L müşterimiz için" çatıyı uygular). Soru ve
    #     olumsuz cümlede uygulanacak bir şey yoktur (olumsuz pencere/dış 140 aşağıda sorulur).
    if not ayni_proje:
        def _istek(p: dict) -> bool:
            i = p.get("isaret") or {}
            degisiklik = i.get("pencere") or i.get("dis140") or i.get("ekle") or i.get("cati_sekil") or p.get("oda_istegi")
            return not p["olumsuz"] and ((p["tur"] == "baska" and bool(degisiklik))
                                         or (p["tur"] == "belirsiz" and p.get("neden") == "genel" and bool(p.get("sifat"))))
        okunamayan = [p["metin"].strip(" ,.;") for p in r["parcalar"] if _istek(p)]
        if okunamayan:
            k.bekleyen_not = (k.bekleyen_not or "") + "".join(
                f"\"{_kisalt(m)}\" isteğini otomatik uygulayamadım; plan okuyabildiklerimle çizilir. " for m in okunamayan[:3])
    # 1) desteklenmeyen LLM varyantı (ayna, oda, kapı, veranda …): soru sormadan yönlendirme. Pencere ve "diger" metinden okunur.
    for v in llm.get("varyantlar") or []:
        tur = str(v.get("tur") or "")
        if tur.startswith("pencere") or tur == "diger":
            continue
        if tur == "cati_degistir":
            if r["cati"]:
                continue                                        # çatı cümlesi okundu (katalog/K/L); `_celik_dali` seçti
            if kap_cumle and not any((p.get("isaret") or {}).get("cati") or (p.get("isaret") or {}).get("cati_sekil") for p in r["parcalar"]):
                continue                                        # LLM kaplama cümlesini çatı değişikliği okudu (canlı K8): kaplama kuralı işledi
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelikte varyant henüz desteklenmiyor: {tur}",
                                    mesaj=f"\"{v.get('aciklama', '')}\" değişikliği çelik modelde otomatik yapılamıyor"
                                          + ("; çatı için katalog çatısı, K ya da L seçilebilir. " if kat_aday.get("varyantlar") else ". ") + YONLENDIRME))
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelikte varyant henüz desteklenmiyor: {tur}",
                                mesaj=f"\"{v.get('aciklama', '')}\" değişikliği çelik modelde henüz otomatik yapılamıyor. " + YONLENDIRME))
    # 2) revizyonda tanınmayan içerik: bina özelliği (renk, malzeme) değilse yönlendirme (K21: yanlış uygulanmaz, sessizce düşmez)
    if ayni_proje:
        baska = [p["metin"] for p in r["parcalar"] if p["tur"] == "baska" and not _bilgi_cumlesi(p, llm) and p["metin"] not in kap_cumle]
        if baska:
            # gerekçe günlüğe yazılır (vps/agent.py): bayinin cümlesi yalnız bayiye giden mesajda (mesaj metni günlüğe yazılmaz)
            return _bitir(k, Karar(eylem="yonlendir", gerekce="çelik revizyonunda otomatik yapılamayan istek (cümle bayiye söylendi)",
                                    mesaj=f"\"{_kisalt(baska[0].strip(' ,.;'))}\" isteği çelik modelde otomatik yapılamıyor (otomatik yapabildiklerim: "
                                          "pencere ölçüsü, çatı katalog/K/L, dış duvarlar 140'lık). " + YONLENDIRME))
    # 3) pencere ekleme ya da kaldırma: 8a'da yalnız ölçü (ölçü yazılmış olsa da mevcut pencere değiştirilmez). Pencere sözü taşımayan ekleme
    #    cümlesi oda eklemedir ("bir yatak odası daha ekleyelim"; BK-15): gerekçe ve mesaj odayı söyler, pencereyi değil
    if r["ekle_kaldir"]:
        ek = [p for p in r["parcalar"] if p["tur"] == "ekle_kaldir"]
        oda = any(not (p.get("isaret") or {}).get("pencere") for p in ek)
        pencere = any((p.get("isaret") or {}).get("pencere") for p in ek)
        if oda:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="çelik katalog modelinde oda ekleme/kaldırma otomatik yapılamıyor"
                                                               + (" (pencere ekleme/kaldırma da: 8a yalnız ölçü)" if pencere else ""),
                                    mesaj="Oda ekleme ya da kaldırma " + ("ve pencere ekleme ya da kaldırma " if pencere else "")
                                          + "çelik modelde otomatik yapılamıyor. " + YONLENDIRME))
        return _bitir(k, Karar(eylem="yonlendir", gerekce="çelikte pencere ekleme/kaldırma otomatik yapılamıyor (8a: yalnız ölçü)",
                                mesaj="Pencere ekleme ya da kaldırma çelik modelde otomatik yapılamıyor; mevcut pencerenin ölçüsünü değiştirebilirim. " + YONLENDIRME))
    # 4) olumsuz/soru biçimli ya da belirsiz cümle, okunamayan çatı isteği → sor (K21). İlk planda yalnız gerçek değişiklik soruları:
    #    pencere/dış 140 cümlesi olumsuz ya da soru biçimliyse ("… olabilir mi?") ve belirsizlik bir değişiklikten geliyorsa (karma, ölçü
    #    dışı sayı, üç ölçü, "duvarlar 140"); oda listesi, çatı sorusu ("Ç8801K olur mu?", "çatı K mı L mi?") ilk planda talep
    #    bilgisidir — çatıyı set ya da kod belirler (geometri hakemi ikinci ve üçüncü tur). Duvar cümlesi soru biçimliyse yalnız 140 değeri
    #    taşıyorsa sorulur ("duvarlar 140 olabilir mi?" değişiklik isteğidir; "dış duvar kalınlığı ne kadar?" bilgi sorusudur; dördüncü tur).
    if ayni_proje:
        sor = bool(r["olumsuz"] or r["belirsiz"] or r["cati_belirsiz"])
    else:
        sor = any((p["olumsuz"] and p["tur"] in ("pencere", "dis140")) or (p["tur"] == "belirsiz" and p.get("neden") in ("karma", "sayi", "olcu"))
                  or (p["tur"] == "belirsiz" and p.get("neden") == "dis" and (not p["olumsuz"] or p.get("d140")))
                  for p in r["parcalar"])
    if sor:
        return _soru(k, "okuma_metin", "Anlayamadım. " + _celik_ornekleri(katalog, aday, t, onceki))
    if llm.get("pencere") and not r["pencereler"]:
        return _soru(k, "okuma_metin", "Hangi odanın penceresini hangi ölçüye değiştirelim? (örn. \"mutfak penceresi 120x120\")")
    # 5) değişiklikler
    okunan: set[str] = set()
    ops: list[dict] = []
    if r["cati"]:
        okunan.add("cati")                                      # aday zaten o çatı (`_celik_dali` seçti); op zarfta
    if r["dis140"]:
        okunan.add("dis140")
        if _zaten_140(t, onceki):                               # üretilen plan ilk mesajdaki istekle zaten 140 çizilmiş olabilir (inceleme C1)
            k.not_dus("kural", "dış 140 zaten uygulanmış; yinelenmedi")
        else:
            ops.append({"op": "dis_karkas_140", "aciklama": "dış duvarlar 140'lık karkas (16,5 cm)"})
    pencereler = [p for p in r["pencereler"] if not p.get("olumsuz") and not p.get("ekle_kaldir")]
    if pencereler:
        okunan.add("pencere")
    return _pencereleri_coz(k, aday, t, onceki, ops, pencereler, okunan)


def _zaten_140(t: dict, onceki: list[dict]) -> bool:
    """Dış karkas zaten 140 mı: önceki revizyonda uygulanmış ya da tanımın dış sınıfı 140 (KT-03; ilk mesajdaki istekle üretilen plan)."""
    return any(o.get("op") == "dis_karkas_140" for o in onceki) or \
        bool(re.match(r"\s*140", str(((t.get("duvar_siniflari") or {}).get("dis") or {}).get("profil") or "")))


def _cati_kodlari(katalog: Katalog, aday: dict) -> set[str]:
    taban = katalog.aday(aday.get("referans_model")) if aday.get("referans_model") else None
    kat = taban if (taban and taban.get("varyantlar")) else aday
    return {kat["kod"], *(kat.get("varyantlar") or [])} if kat.get("varyantlar") else set()


def _llm_cati(k: Konusma, katalog: Katalog, aday: dict) -> str | None:
    """İE-14 PR-3: LLM-önce okumada çatı işlemi (kod denetler: bu modelin varyantı mı)."""
    from . import degisiklik_okuyucu as DO
    lo = getattr(k, "llm_degisiklik", None)
    if not lo or lo.get("durum") != "tamam":
        return None
    d = DO.denetle(lo, [], _cati_kodlari(katalog, aday))
    return next((o["kod"] for o in d["ops"] if o["op"] == "cati_varyanti"), None)


def _llm_degisiklikler(k: Konusma, katalog: Katalog, aday: dict, t: dict, onceki: list[dict], lo: dict) -> tuple[list[dict], set[str]] | Karar:
    """İE-14 PR-3 · LLM-önce okuma: LLM'in işlemleri kodla ayıklanır (`degisiklik_okuyucu.denetle`); çatı `_celik_dali`da seçildi. Çevrilemeyen
    istek revizyonda yönlendirilir, bayinin sözüyle ("… otomatik uygulayamadım"; sessiz düşme yok); iki aday "1 / 2 / Hiçbiri"."""
    from . import degisiklik_okuyucu as DO
    try:
        y = varyant._kur(t)
    except varyant.VaryantHatasi:
        y = None
    pencereler = CO.pencere_adaylari(t, y)
    germe = bool(lo.get("germe"))                               # İE-23 PR-2a: okuma germeli yapıldıysa (ayar banka_germe) oda işlemleri
    d = DO.denetle(lo, pencereler, _cati_kodlari(katalog, aday), odalar=[m["ad"] for m in t.get("mahaller", [])] if germe else None)
    k.not_dus("kural", f"LLM-önce okuma: {len(d['ops'])} işlem, {len(d['uygulanamaz'])} uygulanamaz" + (", soru" if d["sor"] else ""))
    if d["uygulanamaz"]:
        alinti = "; ".join(f"\"{numara.maskele(x)[:80]}\"" for x in d["uygulanamaz"][:3])
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"LLM-önce okuma: {len(d['uygulanamaz'])} istek otomatik uygulanamıyor",
                                mesaj=f"{alinti} isteğini otomatik uygulayamadım. Otomatik yapabildiklerim: pencere ölçüsü, çatı seçeneği, dış duvarlar "
                                      "140'lık karkas" + (", oda büyütme ve küçültme" if germe else "") + ". " + YONLENDIRME))
    if d.get("yon_sor"):                                        # İE-23 PR-2a: oda büyütmede yön yok; plan bayide kalır, soru sorulur
        soz = numara.maskele(str(d["yon_sor"][0]))[:80]
        return _yeni_plan_sorusu(k, f"\"{soz}\" için yönü yazar mısınız: öne, arkaya, sola ya da sağa? (örn. \"salonu sağa 50 cm büyüt\") "
                                    + _BASKA_DEGISIKLIK, "banka germe: yön yok")
    zaten140 = _zaten_140(t, onceki)
    ops = [o for o in d["ops"] if o["op"] != "cati_varyanti" and not (o["op"] == "dis_karkas_140" and zaten140)]   # kural yoluyla aynı: yinelenmez
    okunan = {{"pencere_olcu": "pencere", "dis_karkas_140": "dis140"}.get(o["op"], o["op"]) for o in ops}
    if d["sor"]:
        ortak = {"hazir": ops, "kalan": [], "okunan": sorted(okunan), "tanim": aday.get("tanim"), "kod": aday["kod"], "degisiklikler": onceki,
                 "mahaller_t": [{"ad": m["ad"], "islev": m.get("islev") or []} for m in t.get("mahaller", [])]}
        tur = "secim" if d["sor"].get("olcu") else "olcu"
        return _okuma_sor(k, {**ortak, "tur": tur, "adaylar": d["sor"]["adaylar"], **({"olcu": d["sor"]["olcu"]} if d["sor"].get("olcu") else {})})
    return ops, okunan


def _pencereleri_coz(k: Konusma, aday: dict, t: dict, onceki: list[dict], ops: list[dict], kalan: list[dict], okunan: set[str]) -> tuple[list[dict], set[str]] | Karar:
    """Pencere cümlelerini sırayla çözer: tek aday + ölçü → değişiklik; ölçü yok → ölçü sorusu; iki ve daha çok aday → seçim sorusu.
    Soru sorulunca hazır değişiklikler (`hazir`) ve sorulmamış cümleler (`kalan`) soruyla bekler; cevapta hepsi birlikte uygulanır."""
    kalan = list(kalan)
    while kalan:
        p = kalan.pop(0)
        adaylar = p.get("adaylar") or []
        ortak = {"hazir": ops, "kalan": kalan, "okunan": sorted(okunan), "tanim": aday.get("tanim"), "kod": aday["kod"], "degisiklikler": onceki,
                 "mahaller_t": [{"ad": m["ad"], "islev": m.get("islev") or []} for m in t.get("mahaller", [])]}
        if not adaylar:
            ek = " Bu mesajdaki öteki değişiklikleri de uygulamadım; hepsini birlikte yazabilirsiniz." if ops or kalan else ""
            return _soru(k, "okuma_metin", f"O odada pencere bulamadım. Pencereli odalar: {', '.join(p.get('odalar') or [])}. "
                                           f"Hangi odanın penceresi, hangi ölçü?{ek}")
        if not p.get("olcu"):
            return _okuma_sor(k, {**ortak, "tur": "olcu", "adaylar": adaylar})
        if len(adaylar) == 1:
            ops = ops + [_pencere_op(adaylar[0], *p["olcu"])]
            continue
        return _okuma_sor(k, {**ortak, "tur": "secim", "olcu": list(p["olcu"]), "adaylar": adaylar})
    return ops, okunan


_KAPLAMA_SATIRI = "Çatı Kaplaması"                            # çelik pafta tablosunun satırı; formun `bina_ozellikleri` anahtarı


# ── İE-20 PR-11 (D-97; geometri hakemi, üç tur) · bayinin yazdığı çatı kaplaması, çizime işlenen form seçimine göre ──
# Desen geniş, istisna dar: sözcük kökleriyle (Türkçe harfsiz, küçük harf) bakılır; kalınlık, ek ve sıra fark etmez.
_KAP_KOK = {"sandvic_panel": ("sandvic", "sandwic", "sandvij"), "osb_kiremit": ("kiremit", "kiremid", "marsilya"), "trapez_sac": ("trapez",),
            "osb_trapez": ("trapez",), "osb_shingle": ("shingle", "shingil", "shingl", "singil", "singl")}
#   "kiremid": ünsüz yumuşaması ("çatı kiremidi olsun"); "kiremit" kökü bu yazımı yakalamıyordu (BK-33 geometri hakemi, 15 Kasım 2026)
_KAP_KESIN = ("ondulin", "eternit")                            # kitapta olmayan ama yalnız çatı örtüsü olan malzemeler
_KAP_BAGLAMLI = ("sac", "galvaniz", "aluminyum", "bakir", "cinko")   # yalnız çatı / kaplama sözüyle birlikte çatı kaplamasıdır
_KAP_KENDI_BAGLAMLI = {"osb_kiremit": ("sac",), "osb_trapez": ("sac",), "trapez_sac": ("sac",)}   # kaplamanın kendi adındaki sözcük: yalnız
#   adın içinde, kendi kökünün hemen ardında ("kiremit desen sac", "kiremit desenli sac", "kiremit sac"); "kiremit istemiyorum sac olsun"
#   ve "çatı düz sac olsun" başka malzemedir (geometri hakemi, 5. tur B1)
_KAP_RENK = ("kirmizi", "reng", "renk", "tonu")                # "kiremit kırmızısı", "kiremit rengi": renk adı, kaplama değil
_KAP_BASKA_YER = ("cephe", "duvar", "zemin", "tavan", "kapi", "doseme")
_KAP_CATI_PARCASI = ("oluk", "olug", "pencere", "sacak", "sacag", "baca")   # "çatı oluğu galvaniz": çatının parçası, örtüsü değil


def _bas_harf(s: str) -> str:
    return s[:1].upper() + s[1:]                               # `capitalize` kalanı küçültür ("… + osb")


def _kap_sozcukleri(metin) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", str(metin).replace("İ", "i").replace("I", "ı").lower().translate(celik._TR)) if w]


def _kaplama_istegi_mi(metin) -> bool:
    """Serbest metin çatı kaplamasından mı söz ediyor ("çatı kiremit olsun", "kaplama shingle")? Cephe, duvar, zemin ve tavan kaplaması değil."""
    ws = _kap_sozcukleri(metin)
    return any(w.startswith("cati") for w in ws) or (any(w.startswith("kaplama") for w in ws)
                                                     and not any(w.startswith(_KAP_BASKA_YER) for w in ws))


def _kap_oteki_malzemeler(deger, kap: str, baglam: bool = True) -> set[str]:
    """Metinde anılan, `kap` dışındaki çatı malzemelerinin kökleri ("kiremit", "galvaniz", "tekkat"). "kiremit kırmızısı" renk adıdır.
    `baglam` False ise yalnız çatıya özgü malzemeler sayılır ("sac" cephe de olabilir). Çatının bir parçasına yazılan metal ("çatı oluğu
    galvaniz", "alüminyum çatı penceresi") çatı örtüsü değildir."""
    ws = _kap_sozcukleri(deger)
    ws = [w for i, w in enumerate(ws) if not (w.startswith(("kiremit", "kiremid")) and i + 1 < len(ws) and ws[i + 1].startswith(_KAP_RENK))]
    kendi_kok = _KAP_KOK.get(kap, ())
    oteki_kok = tuple({x for a, ks in _KAP_KOK.items() if a != kap for x in ks} - set(kendi_kok)) + _KAP_KESIN
    bulunan = {kok for w in ws for kok in oteki_kok if w.startswith(kok)}
    bitisik = "".join(ws)
    if kap != "tek_kat_panel" and (any(x in bitisik for x in ("tekkatpanel", "tekkatlipanel", "tekkatsac")) or bitisik == "tekkat"):
        bulunan.add("tekkat")
    if kap in _KAP_KENDI_BAGLAMLI and any(w.startswith(kendi_kok) for w in ws):
        baglam = True                                          # kendi adını anan söz çatıdan söz eder ("kiremit istemiyorum sac olsun")
    if baglam:
        parca = lambda n: 0 <= n < len(ws) and ws[n].startswith(_KAP_CATI_PARCASI)
        for i, w in enumerate(ws):
            sonraki = parca(i + 1) or (i + 1 < len(ws) and ws[i + 1].startswith("cati") and parca(i + 2))
            if w.startswith(_KAP_CATI_PARCASI) or parca(i - 1) or (sonraki and not (i and ws[i - 1].startswith("cati"))):
                continue                                       # "oluğu galvaniz", "alüminyum çatı penceresi"; "çatı galvaniz, pencere …" değil
            adinda = bool(kendi_kok) and i > 0 and (ws[i - 1].startswith(kendi_kok)
                                                    or ws[i - 1].startswith("desen") and i > 1 and ws[i - 2].startswith(kendi_kok))
            bulunan |= {kok for kok in _KAP_BAGLAMLI if w.startswith(kok) and not (adinda and kok in _KAP_KENDI_BAGLAMLI.get(kap, ()))}
    return bulunan


def _kaplama_kiyasi(deger, kap: str, adlar=(), satir: bool = False, baglam: bool = True) -> str:
    """Bayinin yazdığı değer, çizime işlenen kaplamaya (`kap`, kural kitabının anahtarı) göre nedir:
    "ayni"  yalnız o kaplamanın adı (formun yazdığı değer, kitaptaki ad ya da adın ilk sözcüğü): tablo gösterir, ayrıca yazılmaz;
    "baska" başka bir çatı malzemesini anıyor ("kiremit", "galvaniz sac", "sandviç yerine shingle"), ya da tablonun "Çatı Kaplaması"
            satırına (`satir`) seçilen kaplamayı anmayan bir değer yazılmış ("onduline"): bayinin son sözü form seçimiyle çelişir;
    "ek"    başka malzeme anmıyor ("sandviç panel 5 cm", "çift kat yalıtım"): seçim işlenir, söz özel istekte kalır (bilgi düşmez).
    `baglam` False ise (çatıdan söz etmeyen satır ya da istek) yalnız çatıya özgü malzemeler sayılır ("sac" cephe de olabilir)."""
    d = varyant._norm(str(deger))
    if d in {varyant._norm(x) for ad in (*adlar, varyant.kaplama_adi(kap)) if ad for x in (str(ad), str(ad).split()[0])} \
            or d == varyant._norm(varyant.kaplama_kitap_adi(kap)):       # pafta tablosunun yazdığı ad da aynı kaplamadır (hakem 5. tur B3)
        return "ayni"
    ws = _kap_sozcukleri(deger)
    kendi_kok = _KAP_KOK.get(kap, ())
    kendi = any(w.startswith(kendi_kok) for w in ws) if kendi_kok else False
    if kap == "tek_kat_panel":
        bitisik = "".join(ws)
        kendi = kendi or any(x in bitisik for x in ("tekkatpanel", "tekkatlipanel", "tekkatsac")) or bitisik == "tekkat"
    return "baska" if _kap_oteki_malzemeler(deger, kap, baglam) or (satir and not kendi) else "ek"


def _kaplama_satiri_mi(anahtar) -> bool:
    """Özellik satırının adı çatı kaplamasını mı anlatıyor? Tablonun "Çatı Kaplaması" satırı ve LLM'in başka yazdığı adlar ("Kaplama",
    "Çatı kaplama", "Çatı Malzemesi", "Çatı"); tablonun öteki satırları (renk, çatı şekli, eğim) değil."""
    ad = celik.satir_adi(anahtar)
    if ad:
        return ad == _KAPLAMA_SATIRI
    ws = _kap_sozcukleri(anahtar)
    return (any(w.startswith("cati") for w in ws) or bool(ws) and ws[0].startswith("kaplama")) \
        and not any(w.startswith(("renk", "reng") + _KAP_CATI_PARCASI) for w in ws)


# D-106 (Lokman, kart 15 Kasım 2026 10:08:33 UTC "Üç cümle"): çelik formda kaplama seçilmeden, formdan sonra mesajla yazılan çatı kaplaması
# çizime işlenmez; söz talebe (özel istek) yazılır ve bayiye bu üç cümle söylenir. Metin kartta onaylandı; harfi harfine.
YAZILAN_KAPLAMA_NOTU = ("Mesajınızda çatı kaplaması yazdınız. Planı modelin kendi çatı kaplamasıyla çizdim. "
                        "Yazdığınız kaplamayı talebe yazdım. ")


def _baska_kaplama_sozu(soz: str, kap: str, adlar=()) -> bool:
    """Serbest söz (özel istek ya da bayinin cümlesi) `kap` dışında bir çatı kaplaması mı anıyor? Çatıdan söz etmeyen cephe, duvar, zemin
    sözü sayılmaz ("dış cephe trapez sac"); "çatı" demeyen sözde yalnız çatıya özgü malzeme sayılır ("kiremit olsun")."""
    cati = _kaplama_istegi_mi(soz)
    if not cati and any(w.startswith(_KAP_BASKA_YER) for w in _kap_sozcukleri(soz)):
        return False
    return _kaplama_kiyasi(soz, kap, adlar, baglam=cati) == "baska"


def _mesajin_kaplama_cumleleri(k: Konusma, aday: dict, kap: str, adlar=()) -> list[str]:
    """Bayinin BU mesajında, çizime işlenmiş kaplamadan (`kap`) başka bir çatı kaplaması isteyen cümleler (K18: kural bayinin kendi
    sözünü okur; LLM cümleyi özellik satırına, özel isteğe ya da çatı değişikliğine yazmış olabilir, hiç yazmamış da olabilir). Cümle
    `celik_okuma` ile bölünür. Yalnız yalın kaplama cümlesi sayılır: olumsuz ve soru biçimi ("… olabilir mi?"), oda, pencere, dış 140,
    ekleme ve çatı şekli işareti taşıyan cümle sayılmaz (onlar bugünkü yoldan sorulur ya da yönlendirilir; K21)."""
    metin = k.d.get("son_metin") or ""
    if not metin.strip():
        return []
    try:
        t0 = celik.tanim_oku(aday)
        try:
            y = varyant._kur(t0)
        except varyant.VaryantHatasi:
            y = None
        parcalar = CO.oku(metin, t0, aday, y=y)["parcalar"]
    except Exception:                                          # okuma düşerse kural susar: bugünkü yol (yönlendirme) işler
        return []
    return [p["metin"] for p in parcalar
            if p["tur"] == "baska" and not p.get("olumsuz") and not p.get("odalar") and not any((p.get("isaret") or {}).values())
            and _baska_kaplama_sozu(p["metin"], kap, adlar)]


def _kaplama_cumlesini_talebe_yaz(k: Konusma, t: Talep, metin: str | None) -> Talep:
    """İE-20 PR-11 eki (canlı deneme K7, 15 Kasım 2026, v2026.11.15d). Çelik formda çatı kaplaması seçildi, plan henüz çizilmedi; bayi
    sohbette başka bir çatı kaplaması yazdı ("çatı kiremit olsun"). Canlıda LLM cümleyi hiçbir alana yazmadı: plan form seçimiyle çizildi,
    söz talebe yazılmadı, bayiye söylenmedi (sessiz düşme). Kural bayinin kendi cümlesini okur (K18):
    - LLM bu mesajda kaplamayı bir özellik satırına ya da özel isteğe yazmadıysa cümle özel isteğe yazılır. İlk planda `_kaplama_sozleri`
      onu bayinin son sözü sayar: form seçimi çizime işlenmez, bayiye söylenir (`_celik_is_emri_uret`).
    - LLM cümleyi çatı değişikliği (`cati_degistir`) okuduysa ve mesajda çatı seçimi (katalog, K, L) ya da çatı şekli sözü yoksa o
      varyant düşer: kaplama isteği çatı şekli isteği değildir, plan onun yüzünden geri çevrilmez.
    Açık plan varken (revizyon) dokunulmaz: zarftaki kaplama işlemini `_celik_is_emri_uret` bayinin cümlesiyle çıkarır. Form mesajının
    kendisi bugünkü yoldan gider.
    D-106 (Lokman, kart 15 Kasım 2026 10:06:51 UTC "Evet, talebe yazılsın"): formda kaplama standart kaldıysa da bayinin formdan sonra
    yazdığı çatı kaplaması cümlesi aynı yoldan talebe yazılır; cümleler `taslak.yazilan_kaplama`'da durur, plan kesinleşince bayiye
    `YAZILAN_KAPLAMA_NOTU` söylenir (yazılan kaplama modelin kendi kaplamasıysa söylenmez)."""
    ts = k.d["taslak"]
    kap = ts.get("form_kaplama") or ""            # "": formda kaplama standart kaldı (D-106): her çatı kaplaması sözü sayılır
    if getattr(k, "celik_formu", None) is not None or ts.get("form") != "celik" or not (metin or "").strip() or _acik_plan_var(k):
        return t
    adlar = (ts.get("form_kaplama_yazi"),) if kap else ()
    cumleler = [c.strip(" ,") for c in re.split(r"[\n.!?;]+", metin) if c.strip(" ,") and _baska_kaplama_sozu(c, kap, adlar)]
    if not kap:                                   # D-106: soru ve olumsuz cümle kaplama isteği değildir (revizyondaki kuralla aynı; K21)
        soru = {c.strip(" ,") for c in re.findall(r"([^\n.!?;]+)\?", metin)}
        cumleler = [c for c in cumleler if c not in soru
                    and not any(CO._SORU_T.fullmatch(w) or CO._OLUMSUZ_T.fullmatch(w) for w in CO.norm(c).split())]
    if not cumleler:
        return t
    if not kap:                                   # D-106: plan kesinleşince bayiye söylenir (`YAZILAN_KAPLAMA_NOTU`)
        ts["yazilan_kaplama"] = [*(ts.get("yazilan_kaplama") or []), *(c for c in cumleler if c not in (ts.get("yazilan_kaplama") or []))]
    degisen: dict = {}
    bu = {"bina_ozellikleri": dict(t.bina_ozellikleri or {}), "ozel_istekler": list(t.ozel_istekler or []), "form_kaplama_yazi": next(iter(adlar), None)}
    if not _kaplama_sozleri(bu, kap, hepsi=True)[1]:           # LLM kaplamayı hiçbir alana yazmadı: bayinin cümlesi talebe
        degisen["ozel_istekler"] = list(t.ozel_istekler or []) + [c for c in cumleler if c not in (t.ozel_istekler or [])]
        k.not_dus("kural", "çelik formu: bayinin yazdığı başka çatı kaplaması özel isteğe yazıldı (LLM alan doldurmadı)")
    sekil = CO.cati_secenekleri(metin) or any(CO._CATI_GEO_T.fullmatch(w) for w in CO.norm(metin).split())
    if not sekil and any(v.tur == "cati_degistir" for v in t.varyantlar):
        degisen["varyantlar"] = [v for v in t.varyantlar if v.tur != "cati_degistir"]
        k.not_dus("kural", "çelik formu: kaplama cümlesinden okunan çatı değişikliği düştü (çatı seçimi ya da şekli yok)")
    return t.model_copy(update=degisen) if degisen else t


def _kaplama_sozleri(ts: dict, kap: str, hepsi: bool = False) -> tuple[list[str], list[str]]:
    """Taslakta çizime işlenen kaplamayla (`kap`) ilgili sözler: (tabloda zaten görünen "ayni" satırların adları, bayinin yazdığı başka
    kaplamalar). Özellik satırı "ad: değer" biçiminde, serbest istek kendi metniyle döner. Tablonun öteki satırlarına (dış duvar, renk)
    bakılmaz. Formdan önce yazılmış söz (`form_kaplama_once`) `hepsi` False iken sayılmaz: son söz formdur."""
    bo = ts.get("bina_ozellikleri") if isinstance(ts.get("bina_ozellikleri"), dict) else {}
    adlar, ayni, baska = (ts.get("form_kaplama_yazi"),), [], []
    for a, v in bo.items():
        if v in (None, ""):
            continue
        tablo = celik.satir_adi(a)
        if tablo and tablo != _KAPLAMA_SATIRI:
            continue
        aw = _kap_sozcukleri(a)
        if not tablo and any(w.startswith(_KAP_BASKA_YER) for w in aw) and not any(w.startswith("cati") for w in aw):
            continue                                           # "Dış Cephe Kaplaması: trapez sac": çatı değil (hakem, 4. tur)
        s = _kaplama_kiyasi(v, kap, adlar, satir=tablo == _KAPLAMA_SATIRI, baglam=_kaplama_satiri_mi(a))
        if s == "ayni" and tablo == _KAPLAMA_SATIRI:
            ayni.append(a)
        elif s == "baska":
            baska.append(f"{a}: {v}")
    for x in ts.get("ozel_istekler") or []:
        if isinstance(x, str) and _baska_kaplama_sozu(x, kap, adlar):
            baska.append(x)
    if not hepsi:
        once = set(ts.get("form_kaplama_once") or [])
        baska = [x for x in baska if x not in once]
    return ayni, baska


def _celik_is_emri_uret(k: Konusma, bayi: dict, katalog: Katalog, aday: dict, ts: dict) -> Karar:
    """İE-08 A3/A4 · çelik İş Emri zarfı (`beyin/celik.zarf`): tanım gömülmez (yol + sha256), antet bilgisi bayi kartından (D-09).
    A4 (PR-2b): değişiklikler bayinin sözünden okunur (`celik_okuma`, cümle cümle), aynı projede birikir (`yapi.degisiklikler`), tanıma
    uygulanabildiği burada denenir (`varyant.tanim_uygula`; uygulanamazsa yönlendirme, çizim düşmez). Desteklenmeyen LLM varyantı ve
    revizyonda okunamayan cümle yönlendirilir: sessizce düşmez (K21). Revizyonda hiçbir şey değişmiyorsa aynı plan yeniden çizilmez,
    sorulur. Taslağın pencere/varyant listeleri tüketilir (sonraki revizyon yeniden okumaz)."""
    if not celik.tanim_dogrula(aday):                          # İE-14: üretilen planda tanım gömülü (kanonik sha)
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"model tanımı yok ya da değişmiş: {aday.get('tanim') if not celik.tanim_gomulu(aday) else aday['kod']}",
                                mesaj=f"{celik.kaynak_notu(aday)} modelinin tanımı sistemde doğrulanamadı. " + YONLENDIRME))
    son = k.d.get("son_is_emri") or {}
    son_y = son.get("yapi") or {}
    ayni_proje = son_y.get("sistem") == "celik" and Katalog.taban_kod(son_y.get("kod")) == Katalog.taban_kod(aday["kod"])
    onceki = [d for d in (son_y.get("degisiklikler") or []) if d.get("op") != "cati_varyanti"] if ayni_proje else []
    # İE-20 PR-11 (D-97, geometri hakemi): formdan çizilmiş kaplama zarfta dururken bayi revizyonda başka bir kaplama yazarsa işlem
    # zarftan çıkar (plan modelin kendi kaplamasına döner), yazdığı kaplama özel isteğe gider, bayiye söylenir. Liste bayinin son sözüne
    # karşın eski seçimi saymaz. Taslak değişmez: erken dönüşlerde bir şey kaybolmaz.
    # Canlı deneme K8 (15 Kasım 2026, v2026.11.15d): LLM "çatı kaplaması kiremit olsun" cümlesini çatı değişikliği (`cati_degistir`) diye
    # okudu, özellik satırı yazmadı; istek kaplama kuralına gelmeden geri çevrildi. Kural bayinin kendi cümlesine de bakar (K18):
    # `kap_cumle` bu mesajın başka kaplama isteyen cümleleridir; `_celik_degisiklikler` onları yönlendirmez, söz özel isteğe yazılır.
    kap_notu, kap_cumle = "", []
    kap_op = next((d for d in onceki if d.get("op") == "cati_kaplamasi"), None)
    if kap_op is not None:
        kap_cumle = _mesajin_kaplama_cumleleri(k, aday, kap_op.get("kaplama"), (ts.get("form_kaplama_yazi"),))
        if kap_cumle and not _kaplama_sozleri(ts, kap_op.get("kaplama"))[1]:
            # LLM cümleyi hiçbir alana yazmadı: söz taslağa (özel istek) yazılır. Araya soru girse de (pencere sorusu) cevapta kural onu
            # bulur; "Yazdığınız kaplamayı talebe yazdım" doğru olur. Geri çevrilen istekte konuşma önceki hâline döner (BK-29).
            ts["ozel_istekler"] = list(ts.get("ozel_istekler") or []) + [c.strip(" ,.;") for c in kap_cumle]
    if kap_op is not None and _kaplama_sozleri(ts, kap_op.get("kaplama"))[1]:
        k.not_dus("kural", f"çelik revizyonu: çatı kaplaması {kap_op.get('kaplama')} zarftan çıktı, bayi başka kaplama yazdı")
        onceki = [d for d in onceki if d is not kap_op]
        kap_notu = (f"Mesajınızda başka bir çatı kaplaması yazdınız. {_bas_harf(varyant.kaplama_adi(kap_op.get('kaplama')))} seçiminizi "
                    "plandan çıkardım. Planı modelin kendi çatı kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım. ")
    t = celik.tanim_oku(aday)
    try:
        for d in onceki:
            t = varyant.tanim_uygula(t, d)
    except varyant.VaryantHatasi as e:
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"önceki değişiklikler yeni tanıma uygulanamadı: {e}",
                                mesaj=f"Önceki değişiklikleriniz bu modele taşınamadı ({e}). " + YONLENDIRME))
    if ayni_proje and kap_op is None and ts.get("form") == "celik" and not aday.get("uretilen"):
        # D-106: çelik formla açılmış planın revizyonunda, zarfta kaplama işlemi yokken bayi başka bir çatı kaplaması yazdı. Kaplama
        # çizime işlenmez; cümle taslağa özel istek olarak yazılır (LLM bu mesajda bir kaplama satırı yazdıysa o satır yeter), plan aynı
        # çizimle yeni revizyon olur ve bayiye söylenir. İstek geri çevrilmez (`kap_cumle`). Yeni çizilen plan (İE-14) bugünkü yoldan.
        kap_cumle = _mesajin_kaplama_cumleleri(k, aday, varyant.kaplama_oku(t))
        if kap_cumle:
            satirlar = {a: v for a, v in ((getattr(k, "son_llm", None) or {}).get("bilgi") or {}).items() if a not in ("ad", "sevk_adresi")}
            yazilan = [c.strip(" ,.;") for c in kap_cumle]
            if not _kaplama_sozleri({"bina_ozellikleri": satirlar}, varyant.kaplama_oku(t), hepsi=True)[1]:
                ts["ozel_istekler"] = [*(ts.get("ozel_istekler") or []), *(c for c in yazilan if c not in (ts.get("ozel_istekler") or []))]
            ts["yazilan_kaplama"] = [*(ts.get("yazilan_kaplama") or []), *(c for c in yazilan if c not in (ts.get("yazilan_kaplama") or []))]
    ly = getattr(k, "llm_yeni_plan", None)
    bilgi = bool((getattr(k, "son_llm", None) or {}).get("bilgi"))
    kod_metni = ""                                              # yeni plan + bilgi: istek notu (mesajın başı ve PDF başlığı; LLM özeti değil)
    if aday.get("uretilen") and ayni_proje and ly is not None:  # İE-14 PR-3 (T3): yeni planın revizyonu LLM'in yeniden planıyla
        # plan değişmedi (inceleme C2 ve ikinci tur): konuşma kapanmaz. Soru, sonraki cevap yine LLM düzenleyicisine gitsin diye
        # okuma alanı bırakmaz ("okuma_metin" LLM-önce yolu kapatıp cevabı kural yoluna, oradan Patron'a düşürüyordu). Aynı mesajda
        # bilgi (müşteri, antet) varsa soru yerine plan antetle yeniden çizilir, not başa yazılır: bilgi sessiz düşmez (geometri hakemi 15.10)
        if ly.get("durum") == "uygulanamadi":                  # Lokman 15.10 (karar 3): "otomatik uygulayamadım", plan aynen ve onaylanabilir
            uy = ly.get("uygulanamayan") or []
            olmayan = _istekler(uy)
            # Lokman 16.10 (canlı deneme G): kurallara uymayan istek de buradan; konuşma açık, Patron'a bilgiyi worker verir (KURALA_UYMADI)
            kurala = bool(ly.get("kurala_uymayan"))
            gerekce = f"{KURALA_UYMADI}, plan aynen" if kurala else "yeni plan: istek uygulanamadı, plan aynen"
            k.not_dus("kural", f"{gerekce} (revizyon)")
            if not bilgi:
                return _yeni_plan_sorusu(k, f"{olmayan} isteğini otomatik uygulayamadım{_istek_fazlasi(uy)}; planınız aynen geçerli. "
                                         + _BASKA_DEGISIKLIK, gerekce)
            kod_metni = f"{olmayan} isteğini otomatik uygulayamadım{_istek_fazlasi(uy)}; bilgileriniz plana işlendi."
        elif ly.get("durum") != "bos":
            return _yeni_plan_revizyonu(k, bayi, aday, ts, son, son_y, ly)
        elif ly.get("islemler"):                                # işlem okundu ama plan zaten öyle (ör. dış 140'lık planda "dışlar 140")
            if not bilgi:
                return _yeni_plan_sorusu(k, "İstediğiniz değişiklik planda zaten var. " + _BASKA_DEGISIKLIK)
            kod_metni = "İstediğiniz değişiklik planda zaten var; bilgileriniz plana işlendi."
        elif not bilgi:
            return _yeni_plan_sorusu(k, _NEYI_DEGISTIRELIM_YENI)
        elif _bilgi_disi_cumle(k, t, aday):                     # bilgiyle birlikte istek var ama LLM işlem çıkarmadı: sessiz düşmez
            k.not_dus("kural", "yeni plan revizyonu: değişiklik isteği okunamadı")
            return _bitir(k, Karar(eylem="yonlendir", gerekce="yeni plan revizyonu üretilemedi (istek okunamadı)",
                                   mesaj="İsteğinizi kurallara uyan bir plana otomatik çeviremedim; önceki planınız geçerli. " + YONLENDIRME))
        sonuc: tuple[list[dict], set[str]] | Karar = ([], set())   # yalnız bilgi: banka yoluyla aynı, plan antet bilgisiyle yeniden
    else:
        sonuc = _celik_degisiklikler(k, katalog, aday, t, onceki, ayni_proje, kap_cumle=kap_cumle)
    if isinstance(sonuc, Karar):
        return sonuc
    yeni, okunan = sonuc
    # İE-20 PR-9 (D-93): çelik talep formunun dış duvar seçimi ilk planda. Karar burada, işlem öteki değişikliklerden sonra (aşağıda).
    form_ilk = not ayni_proje and ts.get("form") == "celik"
    form_140 = form_ilk and bool(ts.get("form_dis140")) and not _zaten_140(t, onceki) \
        and not any(d.get("op") == "dis_karkas_140" for d in yeni)
    form_notu = "Bu planın dış duvarı 140 mm karkastır. " if form_ilk and not ts.get("form_dis140") and _zaten_140(t, []) else ""
    form_notu += kap_notu
    # İE-20 PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC "Plana ve listeye işlensin"): formda seçilen çatı kaplaması ilk planda
    # tanıma yazılır. Model zaten o kaplamadaysa işlem yok. VARSAYIM (Lokman'ın sözü değil): formda kaplama standart kaldıysa plan modelin
    # kendi kaplamasıyla çizilir (KT-01 … KT-10 kendi paftasında sandviç panel; bugünkü davranış, değişmedi).
    form_kap = ts.get("form_kaplama") if form_ilk else None
    kendi_kap = varyant.kaplama_oku(t)
    tekil: dict[str, dict] = {}
    for d in yeni:                                             # aynı pencereye iki değişiklik (saklanan istek + seçim mesajı): sonuncusu geçerli
        tekil[f"{d.get('op')}:{d.get('aciklik') or ''}:{d.get('mahal') or ''}:{d.get('yon') or ''}"] = d   # İE-23: oda işlemi odası ve yönüyle
    yeni = list(tekil.values())
    if ayni_proje and str(son_y.get("kod")).upper() != str(aday["kod"]).upper():          # çatı varyantı değişti: zarf tanım dosyasını değiştirir
        yeni.append({"op": "cati_varyanti", "kod": aday["kod"], "aciklama": f"çatı {aday.get('gosterim') or aday['kod']}"}); okunan.add("cati")
    if ayni_proje and not yeni and not bilgi and not kap_notu and not ts.get("yazilan_kaplama"):
        if "dis140" in okunan and _zaten_140(t, onceki):      # KT-03 gibi hazır 140'lık modelde aynı öneriyle geri sorulmaz (ikinci tur)
            kr = _soru(k, "okuma_metin", "Bu planda dış duvarlar zaten 140'lık karkas. " + _BASKA_DEGISIKLIK)
            if kr.eylem == "sor":
                k.d["asama"] = "onay_bekliyor"                 # plan değişmedi, bayide: mesajın dediği gibi Onayla çalışır (dördüncü tur)
            return kr
        return _soru(k, "okuma_metin", _celik_ornekleri(katalog, aday, t, onceki))   # aynı plan yeniden çizilip revizyon hakkı harcanmaz
    from . import tanim_germe as TG
    try:
        for d in yeni:
            if d.get("op") in ("oda_buyut", "oda_kucult"):        # İE-23 PR-2a: kodun hesapladığı fark bayiye ve görsele
                t, rapor = TG.oda_degistir(t, d.get("mahal"), d.get("yon"), d.get("cm"), buyut=d["op"] == "oda_buyut")
                d["aciklama"] = TG.kisa_anlatim(rapor)
                d["fark"] = TG.anlatim(rapor) + (" (ölçü yazılmadığı için 50 cm aldım)" if d.get("cm_varsayilan") else "")
            else:
                t = varyant.tanim_uygula(t, d)
    except TG.GermeHatasi as e:                                # Lokman 15.10 (karar 3) kuralı: plan aynen, onaylanabilir; sessiz düşme yok
        istek = next((x for x in yeni if x.get("op") in ("oda_buyut", "oda_kucult") and not x.get("fark")), {})
        ne = TG.istek_sozu(istek) if istek else "değişiklik"
        obur = " Bu mesajdaki öteki değişiklikleri de uygulamadım." if len(yeni) > 1 else ""
        k.not_dus("kural", f"banka germe uygulanamadı: {e}")
        return _yeni_plan_sorusu(k, f"{ne} isteğinizi otomatik uygulayamadım: {e}.{obur} Planınız aynen geçerli. " + _BASKA_DEGISIKLIK,
                                 "banka germe: hakem geçirmedi, plan aynen")
    except varyant.VaryantHatasi as e:
        k.not_dus("kural", f"değişiklik uygulanamadı: {e}")
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelik değişikliği uygulanamadı: {e}",
                                mesaj=f"Bu değişiklik otomatik uygulanamadı ({e}). " + YONLENDIRME))
    if form_140:
        # Formda dış duvar 140 mm karkas seçildi: sohbette yazılan "dışlar 140" ile aynı işlem, bayinin öteki değişikliklerinden sonra
        # (onların üstüne) denenir. Bu modele uygulanamıyorsa plan öteki değişikliklerle ve modelin kendi dış duvarıyla çizilir, seçim
        # özel isteğe yazılır ve bayiye söylenir (sessiz düşmez; form seçimi yüzünden plan yönlendirilmez). Taslak yalnız burada, plan
        # kesinleşince değişir (yukarıdaki erken dönüşlerde dokunulmaz).
        d140 = {"op": "dis_karkas_140", "aciklama": "dış duvarlar 140'lık karkas (16,5 cm)"}
        try:
            t = varyant.tanim_uygula(t, d140)
            yeni = yeni + [d140]
        except varyant.VaryantHatasi as e:
            k.not_dus("kural", f"çelik formu: dış 140 bu modele uygulanamadı: {e}")
            ts["ozel_istekler"] = list(ts.get("ozel_istekler") or []) + ["Dış duvar: 140 mm karkas (formdan; çizime işlenemedi)"]
            ts.pop("form_dis140", None)
            form_notu = ("Dış duvar 140 mm karkası bu plana otomatik işleyemedim. Planı modelin kendi dış duvarıyla çizdim. "
                         "İsteğinizi talebe yazdım. ")
    if form_kap:
        # Seçilen kaplama tanıma yazılır (bayinin öteki değişikliklerinden ve dış 140'tan sonra; geometri değişmez). Pafta tablosu seçimi
        # gösterdiği için özel istekte ayrıca yazılmaz. Uygulanamazsa plan modelin kendi kaplamasıyla çizilir, seçim özel isteğe yazılır
        # ve bayiye söylenir (dış 140'taki kural: sessiz düşmez, form seçimi yüzünden plan yönlendirilmez).
        ad = varyant.kaplama_adi(form_kap)
        ayni, baska = _kaplama_sozleri(ts, form_kap)
        yazilan = baska[-1] if baska else None
        for a in ayni:                                         # formun kendi satırı: tablo gösterir (ya da bayinin sonraki sözü yerini aldı)
            ts["bina_ozellikleri"].pop(a)
        if "bina_ozellikleri" in ts and not ts["bina_ozellikleri"]:
            ts.pop("bina_ozellikleri")
        if yazilan:
            # Bayi formdan sonra başka bir kaplama yazdı (özellik satırı ya da serbest istek; K18: son söz bayinin kendi cümlesi). Form
            # seçimi çizime işlenmez; yazdığı kaplama bugünkü gibi özel isteğe gider ve bayiye söylenir (ön not "işleyemezsem plan
            # mesajında yazarım" demişti; sessiz düşmez, tabloyla çelişmez). Sohbetteki kaplama isteğini çizmek D-97'nin dışında.
            k.not_dus("kural", f"çelik formu: çatı kaplaması {ad} işlenmedi, bayi başka kaplama yazdı ({yazilan})")
            ts.pop("form_kaplama", None); ts.pop("form_kaplama_yazi", None); ts.pop("form_kaplama_once", None)
            form_notu += (f"Formda çatı kaplaması {ad} seçtiniz. Mesajınızda başka bir kaplama yazdınız. Planı modelin kendi çatı "
                          "kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım. ")
            form_kap = None
    if form_kap:
        if form_kap != kendi_kap:
            dk = {"op": "cati_kaplamasi", "kaplama": form_kap, "aciklama": f"çatı kaplaması {ad}"}
            try:
                t = varyant.tanim_uygula(t, dk)
                yeni = yeni + [dk]
            except varyant.VaryantHatasi as e:
                k.not_dus("kural", f"çelik formu: çatı kaplaması bu modele uygulanamadı: {e}")
                ts["ozel_istekler"] = list(ts.get("ozel_istekler") or []) + [f"Çatı kaplaması: {ad} (formdan; çizime işlenemedi)"]
                ts.pop("form_kaplama", None); ts.pop("form_kaplama_yazi", None); ts.pop("form_kaplama_once", None)
                form_notu += (f"Çatı kaplaması {ad} seçiminizi bu plana otomatik işleyemedim. Planı modelin kendi çatı kaplamasıyla çizdim. "
                              "İsteğinizi talebe yazdım. ")
    yk = ts.pop("yazilan_kaplama", None)                       # D-106: formda seçilmeden mesajla yazılan çatı kaplaması (taslak burada değişir)
    if yk and any(_baska_kaplama_sozu(c, kendi_kap) for c in yk):
        k.not_dus("kural", "çelik: bayinin mesajla yazdığı çatı kaplaması çizime işlenmedi, özel isteğe yazıldı")
        form_notu += YAZILAN_KAPLAMA_NOTU
    ts.pop("pencereler", None); ts["varyantlar"] = []          # tüketildi: sonraki revizyon bunları yeniden okumaz (değişiklikler zarfta birikir)
    ie = celik.zarf(aday, bayi, k.gonderen, ts, son, onceki + yeni, kaynak=f"aday {aday['kod']}")
    ie["yapi"]["bu_revizyon"] = [{**d} for d in yeni]
    ie["yapi"]["uygulanan"] = [CO.aciklama(d) for d in onceki + yeni]
    ie["yapi"]["onceki"] = ({"kod": son_y.get("kod"), "tanim": son_y.get("tanim"), "tanim_sha256": son_y.get("tanim_sha256"),
                             "degisiklikler": list(son_y.get("degisiklikler") or []), "revizyon": son.get("revizyon")} if ayni_proje else None)
    k.d["revizyon"] = ie["revizyon"] - 1                       # G-2: sayaç plan sayısıyla eşitlenir (prefabrikle aynı kural)
    k.d["son_is_emri"] = ie
    k.d["asama"] = "is_emri_hazir"
    k.d.pop("okuma_hicbiri", None)
    k.d["soru_sayisi"] = 0                                     # A4: çelikte soru sınırı (MAX_SORU) revizyon başına; yeni plan bütçeyi açar (prefabrik aynen)
    ozet = (ts.get("ozet") or "").strip()
    if ozet and ozet[-1] not in ".!?":
        ozet += "."
    on_not = ts.pop("_on_not", "")                             # düşen pencere sorusu notu (prefabrikle aynı)
    on_bilgi = f"{celik.kaynak_notu(aday)}" + (f" · {_m2(aday.get('katalog_m2'))} m², {aday.get('oda_programi')}" if isinstance(aday.get("katalog_m2"), (int, float)) else "") + ". "
    uyg = ("Uygulanan: " + "; ".join(CO.aciklama(d) for d in yeni) + ". ") if yeni else ""
    fark = [d["fark"] for d in yeni if d.get("fark")]
    if fark:                                                   # İE-23 PR-2a: kodun hesapladığı fark; ölçü değişti, plan taslak
        uyg += " ".join(f[0].upper() + f[1:] + "." for f in fark) + " Ölçüler değiştiği için plan taslaktır; mühendis kontrolünde kesinleşir. "
    if yeni:                                                   # BK-09 M1: kod değişiklik uyguladıysa LLM özeti yazılmaz (K18); özetin
        ozet = ""                                              # "teyit etmemiz gerekiyor" sorusu "Uygulanan"la çelişiyordu (14.10 canlı)
        ie["talep"]["metin"] = uyg.strip()                     # PDF açıklaması da kodun okuması (`worker`, `ozet_baslik`)
        if form_ilk:                                           # İE-20 PR-10 (canlı C5): çelik formdan gelen ilk planda PDF başlığından
            ie["talep"]["metin"] = (on_bilgi + uyg).strip()    # model adı ve m² düşmez ("Ç8801-K (…) · 88 m², 2+1. Uygulanan: …")
    elif kod_metni:                                            # bilgi + uygulanamayan/zaten olan istek: LLM özeti isteği taşır ("çatı L tipi
        ozet = kod_metni                                       # olsun"), plan değişmedi (geometri hakemi ikinci tur, K18): mesaj ve PDF
        ie["talep"]["metin"] = kod_metni                       # başlığı kodun metni
        ie["talep"]["metin_koddan"] = True
    else:                                                      # BK-10: ilk planda da LLM özeti yazılmaz (K18); Ç8801K r01'de "netleştirmeniz
        ozet = ""                                              # gerekiyor" mesaja ve PDF başlığına giriyordu, düğme seçiminde iç kod
        ie["talep"]["metin"] = on_bilgi.strip().rstrip(".")    # ("YENI-… seçildi"). PDF başlığı kodun okuması: model, çatı, m², oda programı
        ie["talep"]["metin_koddan"] = True
    gerekce = f"çelik aday {aday['kod']} (genel motor)" + (f"; değişiklik: {', '.join(d['op'] for d in yeni)}" if yeni else "")
    if kod_metni and aday.get("uretilen") and ly is not None and ly.get("durum") == "uygulanamadi" and ly.get("kurala_uymayan"):
        gerekce += f"; {KURALA_UYMADI}, plan aynen"            # bilgiyle yeniden çizimde de Patron'a bilgi (plan geometrisi aynen)
    # BK-08 madde 4: çelik planda görsel ve PDF bu metinle birlikte gider (çizim düşerse bu metin gitmez, `worker._cizim_hatasi`)
    mesaj = f"{on_not}{on_bilgi}{ozet} {uyg}{form_notu}Ön onay planınız hazır; plan görseli ve PDF ektedir.".replace("  ", " ")
    cati_metni = getattr(k, "cati_metni", "")
    if cati_metni:                                             # İE-42 (D-94): onaydan sonraki çatı setinden seçim
        if yeni and any(d.get("op") == "cati_varyanti" for d in yeni):
            # PDF başlığı: çatısı seçilen plan, eski akışın (İE-25) r01'i gibi model adı, m² ve çatı dışında planın bütün değişiklikleriyle
            # (İE-20 PR-10, canlı C5: "model adı ve m² düşmez"; hakem tur 6, D1 ve D2: ölçü farkı ve taslak notu da, çatıyla gelen istek de)
            obur = [d for d in onceki + yeni if d.get("op") != "cati_varyanti"]
            baslik = on_bilgi + ("Uygulanan: " + "; ".join(CO.aciklama(d) for d in obur) + ". " if obur else "")
            farklar = [d["fark"] for d in obur if d.get("fark")]
            if farklar:
                baslik += (" ".join(f[0].upper() + f[1:] + "." for f in farklar)
                           + " Ölçüler değiştiği için plan taslaktır; mühendis kontrolünde kesinleşir. ")
            ie["talep"]["metin"] = baslik.strip() if obur else baslik.strip().rstrip(".")
            ie["talep"]["metin_koddan"] = True
        if yeni and all(d.get("op") == "cati_varyanti" for d in yeni):
            k.d.pop("cati_onayi_dustu", None)                  # hakem tur 1, bulgu 7: yalnız çatı değişti, "onayınızı geçersiz kıldı" yazılmaz
            # hakem tur 2 ve 3: mesajın istek cümlesi (bayinin sözü) planı değiştirmedi ve bilgi de değil: sessiz düşmez
            uyg_yok = "; isteğinizi plana uygulayamadım" if getattr(k, "cati_ek", False) and not bilgi and not kod_metni else ""
            mesaj = f"{on_not}{cati_metni} Plan aynı{uyg_yok}. Ön onay planınız hazır (r{ie['revizyon']:02d})."
        else:
            mesaj = f"{on_not}{cati_metni} " + mesaj[len(on_not):]
    return _bitir(k, Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=gerekce, mesaj=mesaj))


def _yeni_plan_revizyonu(k: Konusma, bayi: dict, aday: dict, ts: dict, son: dict, son_y: dict, ly: dict) -> Karar:
    """İE-14 PR-3 · yeni planın revizyonu: LLM mevcut planı istekle yeniden yazdı (`plan_uretici.duzenle`, worker), denetçi geçirdi. Zarfta
    yeni tanım gömülü, değişiklik listesi boş (tanım değişiklikleri içerir); önce–sonra görseli önceki gömülü tanımla. Uygulanamayan istek
    bayiye yazılır (sessiz düşmez). Geçmediyse plan değişmez, yönlendirme (hak düşmez: revizyon sayacı `_bitir` ile geri alınır)."""
    if ly.get("durum") != "gecerli" or not ly.get("tanim"):
        k.not_dus("kural", "yeni plan revizyonu kurallara uymadı")
        return _bitir(k, Karar(eylem="yonlendir", gerekce="yeni plan revizyonu üretilemedi",
                                mesaj="İsteğinizi kurallara uyan bir plana otomatik çeviremedim; önceki planınız geçerli. " + YONLENDIRME))
    yeni_t = {**ly["tanim"], "kod": aday["kod"]}
    oz = ly.get("ozet") or {}
    sunum = {**(aday.get("sunum") or {}), "cati_adi": (yeni_t.get("cati") or {}).get("tip_adi") or (aday.get("sunum") or {}).get("cati_adi")}
    guncel = {**aday, "sunum": sunum,                          # çatı adı revizyondaki plandan (canlı deneme 16.10, A: kırmaya "beşik" yazıyordu)
              "tanim": yeni_t, "tanim_sha256": celik.tanim_sha_icerik(yeni_t), "plan": ly.get("plan"), "katalog_m2": oz.get("brut_m2"),
              "kapali_m2": round(sum((oz.get("odalar_m2") or {}).values()), 2) or None,
              "ozet": {"dis_olcu_cm": oz.get("dis_olcu_cm"), "odalar": oz.get("odalar_m2")}}
    k.d["uretilen_plan"] = guncel
    fark = list(ly.get("fark") or []) or ["plan isteğinize göre yeniden düzenlendi"]
    ie = celik.zarf(guncel, bayi, k.gonderen, ts, son, [], kaynak=f"yeni plan {aday['kod']} (revizyon)")
    ie["yapi"]["bu_revizyon"] = [{"op": "plan_duzenleme", "aciklama": f} for f in fark]
    ie["yapi"]["uygulanan"] = fark
    ie["yapi"]["onceki"] = {"kod": son_y.get("kod"), "tanim": son_y.get("tanim"), "tanim_sha256": son_y.get("tanim_sha256"),
                            "degisiklikler": list(son_y.get("degisiklikler") or []), "revizyon": son.get("revizyon")}
    uyg = "Uygulanan: " + "; ".join(fark) + ". "
    ie["talep"]["metin"] = uyg.strip()
    uy = ly.get("uygulanamayan") or []
    not_ = f"{_istekler(uy)} isteğini otomatik uygulayamadım{_istek_fazlasi(uy)}. " if uy else ""
    k.d["revizyon"] = ie["revizyon"] - 1
    k.d["son_is_emri"] = ie
    k.d["asama"] = "is_emri_hazir"
    k.d["soru_sayisi"] = 0
    on_bilgi = f"{celik.kaynak_notu(guncel)}" + (f" · {_m2(guncel['katalog_m2'])} m², {guncel.get('oda_programi')}" if isinstance(guncel.get("katalog_m2"), (int, float)) else "") + ". "
    return _bitir(k, Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=f"yeni plan revizyonu {aday['kod']} (LLM-önce)",
                            mesaj=f"{on_bilgi}{uyg}{not_}Ön onay planınız hazır; plan görseli ve PDF ektedir."))


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
                    return _oda_sorusu(k, ie, f"Hangi odanın penceresini {yeni} yapalım?", {"tur": "varyant", "aciklama": acik}, eslesen)
                # G-3/G-4 (29.09): oda ve ölçü belli; değişikliği satır yolu B1 kurallarıyla uygular. Bu mesajda aynı odanın satırı varsa
                # varyant düşer (not iki kez yazılmaz); yoksa varyant, geldiği mesajdaki sözle satıra çevrilir. Oda parametrede değil yalnız
                # açıklamada yazılı olsa da (Astra) söz belirsizse B1 sorar: pencere varyant yoluyla sessizce değişmez. BK-29 PR-2: önceki
                # revizyonun aynı oda satırı varyantı düşürmez (yeni ölçü sessizce düşüyordu); son söz geçerli, seçilmiş pencere kalır.
                # BK-29 tur 4 (canlı B5, 13 Kasım): LLM aynı isteği hem odasız pencere satırı hem varyant olarak yazabiliyor ("pencere
                # 120x120 olsun"). Odası bulunan varyant aynı ölçülü odasız satırı da karşılar: oda ikinci kez sorulmaz, not iki kez yazılmaz.
                ts["pencereler"] = [r for r in ts.get("pencereler") or []
                                    if r.get("pencere_sira") is not None or r.get("mahal") or r.get("islem") not in (None, "degistir")
                                    or r.get("olcu") not in (None, yeni)]
                if varyant._norm(eslesen[0]) not in getattr(k, "bu_mesaj_mahalleri", set()):
                    ts["pencereler"] = [r for r in ts.get("pencereler") or []
                                        if r.get("pencere_sira") is not None or varyant._norm(r.get("mahal") or "") != varyant._norm(eslesen[0])]
                    satir = {"mahal": eslesen[0], "olcu": yeni, "adet": None, "duvar": None, "islem": "degistir"}
                    if p.get("soz_niyeti"):
                        satir["soz_niyeti"] = p["soz_niyeti"]
                    ts.setdefault("pencereler", []).append(satir)
                ts["varyantlar"] = [x for x in ts.get("varyantlar") or [] if x is not v]
            else:
                return _bitir(k, Karar(eylem="yonlendir", gerekce=f"varyant desteklenmiyor: {tur}",
                                        mesaj=f"\"{v.get('aciklama','')}\" değişikliği otomatik yapılamıyor. " + YONLENDIRME))
        except varyant.VaryantHatasi as e:
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"varyant hatası: {e}", mesaj=f"Değişiklik uygulanamadı ({e}). " + YONLENDIRME))
    if ts.get("yarim_pano"):                          # İE-39 PR-2 (D-90): bayinin yarım pano komutları, şablondan sırayla
        yp = _yarim_pano_uygula(k, ie, ts)
        if isinstance(yp, Karar):
            return yp
        ie, yp_notlar = yp
        notlar += yp_notlar
    # pencere listesi: 'degistir' → şablondaki mahalle eşleştirip ölçü değiştir; 'ekle'/'kaldir' → v0.1'de yönlendirme
    ie_pencere0 = json.loads(json.dumps(ie))          # BK-29 PR-2: seçilmiş pencerelerin notu şablondaki adlarıyla (son satırlardan)
    for p0 in list(ts.get("pencereler") or []):
        if p0.get("pencere_sira") is None and p0.get("soz") and p0.get("islem") != "kaldir":
            # BK-29 tur 4 (B4): ölçü bayinin sözünden. LLM ölçü vermediyse ya da verdiği ölçü sözde hiç geçmiyorsa (listedeki bir ölçüye
            # kaymış) sözdeki yeni ölçü geçerlidir; söz satırın geldiği mesajdır (`soz`), ölçü kayda yazılır (sonraki revizyonlar da görür).
            o = _odanin_yeni_olcusu(p0["soz"], ie, p0.get("mahal"))
            if o and o != p0.get("olcu") and (not p0.get("olcu") or p0["olcu"] not in _olculer_metin(p0["soz"])):
                k.not_dus("kural", f"pencere ölçüsü bayinin sözünden: {o}" + (f" (LLM: {p0['olcu']})" if p0.get("olcu") else ""))
                p0["olcu"] = o
        p = {**p0, "islem": "degistir"} if p0.get("pencere_sira") is not None else p0    # seçilmiş pencere: ölçü değişikliği (hakem 1)
        if p.get("islem") in (None, "degistir", "ekle") and p.get("olcu") and p.get("mahal") and p.get("islem_kaynak") != "bayi cevabı" \
                and p.get("pencere_sira") is None:
            # Mahalde zaten TEK pencere varsa ölçüt bayinin KENDİ sözüdür, LLM'in işlem alanı ya da özeti değil (K18, K21; 22.09 canlı
            # hata: LLM 'ekle' dedi; B1: LLM boş ya da 'degistir' verince belirsiz söz sessizce değişiklik sayılıyordu):
            #   açık değiştirme sözü → ölçü değişikliği; açık ekleme sözü → ekleme (v0.1'de yönlendirme); ikisi de yoksa → SORULUR.
            # Söz, pencere satırının geldiği mesajdan kaydedilir (soz_niyeti); eski kayıtlarda son mesaja bakılır.
            eslesen = _mahal_eslestir(ie, p.get("mahal"))
            mevcut = [a for a in ie.get("acikliklar", []) if a["tur"] == "pencere" and a.get("mahal") == (eslesen[0] if len(eslesen) == 1 else None)]
            niyet = p.get("soz_niyeti")
            if niyet is None:   # v1.1.1'den kalan kayıt: İş Emri'ne girmiş satır değişiklik sayılır, yoksa son mesaja bakılır
                niyet = "degistir" if k.d.get("son_is_emri") else _pencere_soz_niyeti(k.d.get("son_metin") or p.get("aciklama") or "",
                                                                                     p.get("mahal"), p.get("olcu"))
            if len(eslesen) == 1 and len(mevcut) > 1:
                # BK-29 PR-2 (pano 201): birden çok pencereli oda. Açık ekleme sözü → ekleme; açık değiştirme sözü → hangi pencere olduğu
                # aşağıda bayinin sözünden (duvar, eski ölçü) okunur ya da düğmeyle sorulur; söz belirsizse önce "değiştir mi, ekle mi?"
                if niyet == "ekle":
                    p = {**p, "islem": "ekle"}
                elif niyet == "degistir":
                    p = {**p, "islem": "degistir"}
                else:
                    olculer = ", ".join(a.get("olcu", "?") for a in mevcut)
                    k.d["pencere_islem_satiri"] = list(_pencere_anahtari(p))
                    k.d["pencere_islem_sorusu"] = (f"{eslesen[0]} odasında {len(mevcut)} pencere var ({olculer}). Birinin ölçüsünü {p['olcu']} "
                                                   "yapalım mı, yoksa yeni bir pencere mi ekleyelim? \"değiştir\" ya da \"ekle\" yazmanız yeterli.")
                    return _soru(k, "pencere_islem", k.d["pencere_islem_sorusu"])
            if len(eslesen) == 1 and len(mevcut) == 1:
                if niyet == "degistir":
                    if p.get("islem") == "ekle":
                        notlar.append(f"{eslesen[0]} mevcut penceresi ölçü değişikliği sayıldı (ekleme değil)")
                    p = {**p, "islem": "degistir"}
                elif niyet == "ekle":
                    p = {**p, "islem": "ekle"}
                else:
                    k.d["pencere_islem_satiri"] = list(_pencere_anahtari(p))
                    k.d["pencere_islem_sorusu"] = (f"{eslesen[0]} odasında zaten bir pencere var ({mevcut[0].get('olcu', '?')}). "
                                                   f"Ölçüsünü {p['olcu']} yapalım mı, yoksa ikinci bir pencere mi ekleyelim? \"değiştir\" ya da \"ekle\" yazmanız yeterli.")
                    return _soru(k, "pencere_islem", k.d["pencere_islem_sorusu"])
        if p.get("islem") in ("ekle", "kaldir"):
            return _bitir(k, Karar(eylem="yonlendir", gerekce="pencere ekle/kaldır v0.1'de yok",
                                    mesaj="Pencere ekleme/kaldırma otomatik yapılamıyor. " + YONLENDIRME))
        if p.get("islem") == "degistir" or (p.get("olcu") and ie.get("acikliklar")):
            if not p.get("olcu"):
                return _soru(k, "pencere_olcu", "Pencereyi hangi ölçüye değiştirelim? (120x120, 120x180, 60x40 …)")
            eslesen = _mahal_eslestir(ie, p.get("mahal"))
            if len(eslesen) != 1:
                return _oda_sorusu(k, ie, "Hangi odanın penceresi?", {"tur": "satir", "anahtar": list(_pencere_anahtari(p0))}, eslesen)
            oda = _oda_pencereleri(ie, eslesen[0])
            sira = p0.get("pencere_sira")
            if sira is None and len(oda) > 1:                  # BK-29 PR-2: hangi pencere? sözden ya da soruyla (pencere_sira kayda yazılır)
                secim = _pencere_secimi(k, ie, eslesen[0], p0)
                if isinstance(secim, Karar):
                    return secim
                p0["pencere_sira"] = sira = list(secim)
                p0["islem"] = "degistir"
            try:
                ie = varyant.pencere_degistir(ie, eslesen[0], None, p["olcu"], sira=sira if len(oda) > 1 else None)
                if len(oda) == 1:
                    notlar.append(f"{eslesen[0]} penceresi {p['olcu']}")
                else:
                    p0["_oda"] = eslesen[0]                 # not aşağıda, örtüşmeler ayrıldıktan sonra
            except varyant.VaryantHatasi as e:
                return _bitir(k, Karar(eylem="yonlendir", gerekce=f"pencere hatası: {e}", mesaj=f"Pencere değişikliği uygulanamadı ({e}). " + YONLENDIRME))
    if ts.get("pencereler"):
        ts["pencereler"] = _tekillestir(_secilenleri_ayir(ts["pencereler"]), "pencereler")   # seçilen pencerenin eski satırı düşer
        for r in ts["pencereler"]:
            oda_adi = r.pop("_oda", None)
            if oda_adi and r.get("pencere_sira"):
                gruplar = [_onceki_olcuyle(g, k.d.get("son_is_emri"), ie_pencere0, oda_adi, r["pencere_sira"], r["olcu"])
                           for g in _pencere_gruplari(ie_pencere0, oda_adi) if set(g["sira"]) & set(r["pencere_sira"])]
                notlar.append(f"{oda_adi} " + ", ".join(_grup_adi(g, kisa=True) for g in gruplar) + f" penceresi {r['olcu']}")
    notlar = list(dict.fromkeys(notlar))              # BK-29 tur 4: aynı değişiklik iki kez yazılmaz (canlı B5: "ODA 1 …, ODA 1 …")
    seq = int(time.time()) % 100000
    ie["is_emri_no"] = f"PM-{bayi.get('kod','BAYI')}-{time.strftime('%Y%m%d')}-{seq}"
    # G-2 (29.09): numara, gönderilmiş son planın numarasından (konuşma sıfırlandıysa 1); sayaç plan sayısıyla eşitlenir.
    ie["revizyon"] = int((k.d.get("son_is_emri") or {}).get("revizyon") or 0) + 1
    k.d["revizyon"] = ie["revizyon"] - 1
    ie["talep"] = {"bayi": {"kod": bayi.get("kod"), "ad": bayi.get("ad")}, "kaynak": kaynak,
                   "musteri_adi": (ts.get("musteri") or {}).get("ad") or "", "metin": ts.get("ozet", "")}
    ie["kunye"] = {"proje_kodu": ie["is_emri_no"], "ilgili_kisi_telefon": f"{bayi.get('ad','')} / {k.gonderen}",
                   "sevk_adresi": (ts.get("musteri") or {}).get("sevk_adresi") or "", "tarih": time.strftime("%d/%m/%Y"),
                   "cizen": "Portman", "kontrol": "", "onay": ""}
    ie["bina_ozellikleri"] = {**ie.get("bina_ozellikleri", {}), **(ts.get("bina_ozellikleri") or {})}
    # İE-20 PR-6: prefabrik talep formundaki standart dışı seçimler (pano yüksekliği, iç duvar, çatı kaplaması …) İş Emri'ne
    if ts.get("form") == "prefabrik":
        notlar += form_ozellik.uygula(ie, ts.get("bina_ozellikleri"), k.d.get("son_is_emri"))
    ie["ozel_istekler"] = list(ts.get("ozel_istekler") or [])
    ie.setdefault("eksikler", [])
    son = k.d.get("son_is_emri") or {}
    if son and (son.get("talep") or {}).get("kaynak") == kaynak and _plan_ozu(ie) == _plan_ozu(son):
        # BK-29 PR-2: "Hangi pencere?" sorusuna "hiçbiri" dendi ve mesajda başka değişiklik yok: aynı plan yeniden çizilmez, revizyon
        # hakkı harcanmaz; plan açık kalır (karar_ver → _plani_acik_tut). D-86 (Lokman 13 Kasım 21:36 kartı "Değişmedi desin"; tur 4 canlı
        # gözlem 3, …4303 r03 → …4342 r04): aynı değişiklik yeniden istenince de aynı plan yeni numarayla çizilmez; bayiye "Planınız (… rNN)
        # değişmedi; YATAK ODASI 1 penceresi zaten 100x140." gider (altın set D03 bu kararla değişti).
        bu = getattr(k, "bu_mesaj_mahalleri", set())   # yalnız bu mesajın odaları yazılır (önceki revizyonların notları değil)
        eslesen = [n for n in notlar if any(varyant._norm(n).startswith(m) for m in bu if m)]
        if getattr(k, "cati_adimi_secimi", None):
            # İE-42 (hakem tur 3, 4): çatı setinde önceki revizyonun notu ve LLM'in yinelediği pencere bu mesajın isteği sayılmaz: not
            # yalnız bayinin yazdığı ölçüden; onayı ancak her istek cümlesi bir notla tümüyle açıklanırsa kaydettirir (`_zaten_kapsar`)
            icerik = list(getattr(k, "cati_icerik", None) or [])
            eslesen = _sozdeki_notlar(eslesen, icerik)
            k.degismedi_tam = _zaten_kapsar(icerik, eslesen)
            k.degismedi_notu = _zaten_notu(eslesen)
        else:
            k.degismedi_notu = _zaten_notu(eslesen or notlar)
            icerik = list(getattr(k, "cati_icerik", None) or [])
            if icerik:                                 # İE-42 (hakem tur 4): çatı seti bu mesajın isteğiyle kapandı; plan değişmediyse
                k.degismedi_tam = _zaten_kapsar(icerik, _sozdeki_notlar(eslesen or notlar, icerik))   # istek sessiz düşmez
        return _bitir(k, Karar(eylem="cevapla", gerekce=PLAN_DEGISMEDI, mesaj=ts.pop("_on_not", "").strip()))
    k.d["son_is_emri"] = ie
    k.d["asama"] = "is_emri_hazir"
    ek = f" ({', '.join(notlar)})" if notlar else ""
    on_not = ts.pop("_on_not", "")
    # BK-29 tur 5 (pano 202; Lokman'ın metin onayı): plan görseli ve PDF bu metinle birlikte gider. Metin planın hazır olduğunu söyler
    # ("hazırlıyorum" demez); LLM'in talep özeti bayiye gitmez. Kodu bayinin gördüğü biçimde ("PA-06-K"), değişikliği kodun notuyla yazar.
    # PDF başlığı da aynı metin (`worker`, `ozet_baslik`). Çelik metniyle aynı kalıp ("… Ön onay planınız hazır; plan görseli ve PDF ektedir.").
    bas = _plan_basi(katalog, kaynak, ie["revizyon"], ts.get("ozet") or "")
    degisiklik = f"Değişiklik: {', '.join(notlar)}" if notlar else ""
    ie["talep"]["metin"] = " · ".join(x for x in (bas or on_bilgi.strip().rstrip("."), degisiklik) if x)
    ie["talep"]["metin_koddan"] = True
    mesaj = f"{on_not}{on_bilgi}" + "".join(f"{x}. " for x in (bas, degisiklik) if x) + "Ön onay planınız hazır; plan görseli ve PDF ektedir."
    cati_metni = getattr(k, "cati_metni", "")
    yalniz_cati = bool(son and _cati_disi_ozu(ie) == _cati_disi_ozu(son))
    if not cati_metni and k.d.get("cati_onayi_dustu") and yalniz_cati and kaynak != (son.get("talep") or {}).get("kaynak"):
        a = katalog.aday(kaynak)                      # hakem tur 2, D2: çatı seçimi pencere sorusuyla bekledi, cevap ("hiçbiri") yalnız çatıyı değiştirdi
        if a is not None:
            cati_metni = f"Çatı: {_cati_adi(a)} ({SC.gosterim(a)})."
            k.cati_adi = _cati_adi(a)
    if cati_metni:                                    # İE-42 (D-94): onaydan sonraki çatı setinden seçim; plan yalnız çatıda değiştiyse "Plan aynı."
        if yalniz_cati:
            cati_adi = SC._kucuk(getattr(k, "cati_adi", "") or "yeni")          # eskiz: "PDF'teki 4 görünüş kırma çatıyı gösterir"
            k.d.pop("cati_onayi_dustu", None)                  # hakem tur 1, bulgu 7: yalnız çatı değişti, "onayınızı geçersiz kıldı" yazılmaz
            bu = getattr(k, "bu_mesaj_mahalleri", set())       # aynı mesajın planda zaten olan isteği (D-86 gibi); yalnız bu mesajın odaları
            eslesen = [n for n in notlar if any(varyant._norm(n).startswith(m) for m in bu if m)]   # (hakem tur 2, D1)
            icerik = list(getattr(k, "cati_icerik", None) or [])
            eslesen = _sozdeki_notlar(eslesen, icerik)         # hakem tur 4, Y-A: yalnız bayinin yazdığı ölçü
            zaten = _zaten_notu(eslesen)
            if not _zaten_kapsar(icerik, eslesen):             # hakem tur 2, 3, 4: bayinin istek cümlesi planı değiştirmedi
                zaten = f"{zaten}; öteki isteğinizi plana uygulayamadım" if zaten else "isteğinizi plana uygulayamadım"
            mesaj = (f"{on_not}{cati_metni} Plan aynı{'; ' + zaten if zaten else ''}. Ön onay planınız hazır (r{ie['revizyon']:02d}); "
                     f"PDF'teki 4 görünüş {cati_adi} çatıyı gösterir.")
        else:
            mesaj = f"{on_not}{cati_metni} " + mesaj[len(on_not):]
    return _bitir(k, Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=f"şablon {kaynak}" + ek, mesaj=mesaj))


# ── İE-39 PR-2 (D-90) · havuz evinde bayinin "sağa yarım pano uzat" komutu ────────────────────────────────────────────────────────
# Kural bayinin kendi sözünü okur (`yarim_pano_okuma`, K18); LLM'in bu cümleden yazdığı değişiklik ve özel istek kopyası taslağa girmez.
# Komut taslakta birikir (`taslak.yarim_pano`) ve her revizyonda şablondan sırayla uygulanır (duvar başına toplam). Kural tutmazsa komut
# durur, bayiye gerekçe gider ve plan açık kalır (`_plani_acik_tut`). Ayar kapalıyken (varsayılan) bugünkü yol: LLM'in değişikliği.
_YP_NEDEN = {
    "dilim": "bugün yalnız sağ ve ön duvar uzatılıp kısaltılabiliyor",
    "muhur": "bu evin planı sabit, değiştirilemiyor",
    "sistem": "bu komut yalnız prefabrik evde çalışıyor",
    "motor": "yeni plan kurulamadı",
    "cizim": "yeni plan kurulamadı",
    "konum": "evin planı bu komuta uygun değil",
    "veranda": "veranda bu duvara değiyor; veranda uzamaz",
    "karkasli": "bu duvarda karkaslı pano var",
    "girinti": "bu duvarda girinti var",
    "kubbe": "bu duvarda kubbe var",
    "cumba": "bu duvarda cumba var",
    "aciklik": "kapı ya da pencere yerinde kalmıyor",
    "cati": "çatının açıklığı değişiyor",
    "olcu": "dış ölçü yarım panoya uymuyor",
    "dizilim": "öteki duvarlardaki panolar da değişiyor",
}
_YP_HARIC_TUR = ("ayna_x", "ayna_y", "pencere_degistir", "pencere_ekle", "pencere_kaldir", "cati_degistir")


def _yp_miktar(adim: int) -> str:
    """Yarım pano sayısının bayinin sözüyle yazılışı: 1 → "yarım pano", 2 → "1 pano", 3 → "3 yarım pano"."""
    n = abs(int(adim))
    return "yarım pano" if n == 1 else (f"{n // 2} pano" if n % 2 == 0 else f"{n} yarım pano")


def _yp_istek(cephe: str, adim: int) -> str:
    return f"{YP.CEPHE_ADI[cephe].capitalize()} duvarı {_yp_miktar(adim)} {'uzatma' if adim > 0 else 'kısaltma'}"


def _yarim_pano_sozu(k: Konusma, t: Talep, metin: str | None, katalog: Katalog):
    """Bu mesajdaki yarım pano sözü. Komut yoksa ya da ev seçilmemişse (çelik ev dahil) None: bugünkü yol. Komut varsa (Talep, komutlar):
    LLM'in aynı cümleden yazdığı değişiklik ve özel istek kopyası düşer. Açık planda okunamayan pano isteği bayiye söylenir (K21)."""
    komutlar, belirsiz = YPO.oku(metin)
    if not komutlar and not belirsiz:
        return None
    kod = t.katalog_kodu or k.d["taslak"].get("katalog_kodu")
    aday = _aday_bul(k, katalog, kod) if kod else None
    if aday is None or aday.get("motor") == "genel":
        return None
    if belirsiz:
        if not k.d.get("son_is_emri") or k.d.get("asama") not in ACIK_PLAN_ASAMALARI:
            return None                               # ilk plan: bugünkü yol (ev seçimi düşmez)
        b = belirsiz[0]
        k.not_dus("kural", f"İE-39: yarım pano sözü komut sayılmadı ({b.neden})")
        if b.neden.startswith("oda adı"):
            return _bitir(k, Karar(eylem="yonlendir", gerekce="yarım pano: oda büyütme",
                                    mesaj=f"\"{b.soz}\" isteği otomatik yapılamıyor: yarım pano komutu evin dış duvarını kaydırır, odayı "
                                          "büyütmez. " + YONLENDIRME))
        ornek = "Örnek: \"sağa yarım pano uzat\" ya da \"öne 1 pano kısalt\"."
        return _bitir(k, Karar(eylem="cevapla", gerekce=PLAN_DEGISMEDI,
                                mesaj=f"\"{b.soz}\" isteğini uygulamadım: {b.neden}. {ornek}"))
    varyantlar = [v for v in t.varyantlar if v.tur in _YP_HARIC_TUR or not YPO.soz_komut_mu(v.aciklama, komutlar)]
    ozel = [s for s in t.ozel_istekler if not YPO.soz_komut_mu(s, komutlar)]
    if len(varyantlar) != len(t.varyantlar) or len(ozel) != len(t.ozel_istekler):
        k.not_dus("kural", f"İE-39: yarım pano sözünün LLM kopyası düştü ({len(t.varyantlar) - len(varyantlar)} değişiklik, "
                           f"{len(t.ozel_istekler) - len(ozel)} özel istek)")
    t = t.model_copy(update={"varyantlar": varyantlar, "ozel_istekler": ozel})
    k.not_dus("kural", "İE-39: yarım pano komutu " + ", ".join(f"{c.cephe} {c.adim:+d}" for c in komutlar))
    return t, [{"cephe": c.cephe, "adim": c.adim, "soz": c.soz[:200]} for c in komutlar]


def _yarim_pano_uygula(k: Konusma, ie: dict, ts: dict):
    """Taslaktaki komutlar şablondan sırayla (duvar başına toplam). Dönüş (İş Emri, notlar) ya da yönlendirme Karar'ı (K21)."""
    notlar = []
    toplam = YPO.birlestir(ts.get("yarim_pano") or [])
    for cephe in dict.fromkeys(c["cephe"] for c in ts.get("yarim_pano") or []):
        if cephe not in {c["cephe"] for c in toplam}:     # uzatıp kısaltınca duvar ilk yerine döner; bayi bunu da okur
            notlar.append(f"{YP.CEPHE_ADI[cephe]} duvar ilk yerine döndü")
    for c in toplam:
        try:
            s = YP.uygula(ie, c["cephe"], c["adim"])
        except YP.KomutDurdu as e:
            k.not_dus("kural", f"İE-39: komut durdu ({e.kod}): {e.neden}")
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"yarım pano komutu durdu: {e.kod}",
                                    mesaj=f"{_yp_istek(c['cephe'], c['adim'])} isteği bu evde otomatik yapılamıyor: "
                                          f"{_YP_NEDEN.get(e.kod, 'kural tutmuyor')}. " + YONLENDIRME))
        ie = s["is_emri"]
        (W0, H0), (W1, H1) = s["dis_olcu"]["once"], s["dis_olcu"]["sonra"]
        odalar = "; ".join(f"{u['ad']} {_m2(u['once_m2'])} → {_m2(u['sonra_m2'])} m²" for u in s["uzayan"])
        birikti = sum(1 for x in ts.get("yarim_pano") or [] if x["cephe"] == c["cephe"]) > 1     # notlar evin ilk hâline göre
        notlar.append(f"{YP.CEPHE_ADI[c['cephe']]} duvar {'toplam ' if birikti else ''}{_yp_miktar(c['adim'])} "
                      f"{'uzadı' if c['adim'] > 0 else 'kısaldı'} ("
                      + (f"uçtaki {YP._tr(s['silinen'])} cm özel pano kaldırıldı; " if s.get("silinen") else "")    # kart 14:57:40
                      + f"dış ölçü {YP._tr(W0)} × {YP._tr(H0)} → {YP._tr(W1)} × {YP._tr(H1)} cm" + (f"; {odalar}" if odalar else "") + ")")
    return ie, notlar


_ADDAKI_OLCU = re.compile(r" \d{2,3}x\d{2,3}(?= |$)")
_PENCERE_OLCUSU = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:cm\s*)?[x×*]\s*(\d{1,3}(?:[.,]\d{1,2})?)(?![\d.,])", re.IGNORECASE)
_PENCERE_KOKU = ("pencere", "vasistas", "cam", "olcu", "ebat", "boyut")


def _cm_olcu(a: str, b: str) -> str:
    """Bayinin yazdığı pencere ölçüsü santimetreyle ("120x120", "1,20x1,20" → "120x120")."""
    f = lambda v: float(v.replace(",", ".")) * (100 if float(v.replace(",", ".")) < 10 else 1)
    return f"{round(f(a))}x{round(f(b))}"


def _notun_olcusu(n: str) -> str | None:
    m = re.fullmatch(r"(.+?) penceresi (\d{2,3}x\d{2,3})", n)
    return m.group(2) if m else None


def _sozdeki_notlar(notlar: list[str], cumleler: list[str]) -> list[str]:
    """İE-42 (hakem tur 4, Y-A): D-86 notlarından bayinin bu mesajda yazdığı ölçüyü taşıyanlar. LLM'in bağlamdan yinelediği eski pencere
    ("1 olsun, iç kapılar ahşap olsun" → YATAK ODASI 1 120x120) bayinin sözü değildir; notu cevaba girmez, onayı kaydettirmez."""
    olculer = {_cm_olcu(a, b) for h in cumleler for a, b in _PENCERE_OLCUSU.findall(h)}
    return [n for n in notlar if _notun_olcusu(n) in olculer]


# D-86 notunu açıklayan cümlenin dolgusu (hakem tur 5, Y4): "bir", "daha", "hepsi", oda ve alan sözü dolgu değildir
_ZATEN_DOLGU = {"olsun", "olacak", "olmali", "olarak", "kalsin", "yapin", "yapiniz", "yapalim", "yapilsin", "istiyoruz", "istiyorum",
                "isteriz", "isterim", "lutfen", "de", "da", "ve", "ile", "icin", "tamam", "evet", "bu", "su", "boyle", "ayni", "aynen",
                "cm", "santim", "olcusu", "olculeri", "ebadi", "zaten"}


def _ortak_kok(w: str, n: str) -> bool:
    """Bayinin sözcüğü notun sözcüğüyle aynı kökten mi ("mutfağın" ~ MUTFAK, "odası" ~ ODASI, "sol" = sol, "1" = 1)."""
    if w == n:
        return True
    if w.isdigit() or n.isdigit() or len(w) < 3 or len(n) < 3:
        return False
    i = next((j for j, (a, b) in enumerate(zip(w, n)) if a != b), min(len(w), len(n)))
    return i >= 4 or (i >= 3 and w.startswith("oda") and n.startswith("oda"))


def _zaten_kapsar(cumleler: list[str], notlar: list[str]) -> bool:
    """İE-42 (hakem tur 4, Y-A; tur 5, Y4): bu mesajın her istek cümlesi bir D-86 notuyla tümüyle açıklanıyor mu? Cümlede notun ölçüsü
    olmalı; ölçü, pencere sözü ve dolgu (`_ZATEN_DOLGU`, hitap) çıkınca kalan her sözcük ölçüsü cümlede geçen notun odasının sözcüğüdür
    ("yatak odası 1 penceresi 120x120 olsun" evet; "… ve veranda olsun", "… ve bir oda daha olsun", "yatak odası 1 ve salon penceresi
    120x120", "mutfak penceresi 120x120" (not YATAK ODASI 1), "… 120x120 ve yükseklik 260 olsun", "iç kapılar ahşap olsun" hayır). Çoğul
    oda sözü ("yatak odaları") en az iki not ister; "hepsi", "bütün" kapsamaz. Pencere notu olmayan D-86 notu sözle denetlenemez."""
    olculer = {_notun_olcusu(n) for n in notlar} - {None}
    if not cumleler or not olculer:
        return not cumleler
    for h in cumleler:
        sozdeki = {_cm_olcu(a, b) for a, b in _PENCERE_OLCUSU.findall(h)} & olculer
        if not sozdeki:
            return False                                       # cümlede notun ölçüsü yok
        kalan = _PENCERE_OLCUSU.sub(lambda m: " " if _cm_olcu(*m.groups()) in olculer else m.group(0), h.lower())
        eslesen = [n for n in notlar if _notun_olcusu(n) in sozdeki]
        oda = set()
        for n in eslesen:
            oda |= set(CO.norm(_ADDAKI_OLCU.sub("", re.sub(r" penceresi \d{2,3}x\d{2,3}$", "", n))).split())
        for w in CO.norm(kalan).split():
            if w.startswith(_PENCERE_KOKU) or w in _ZATEN_DOLGU or w in _SECIM_NEZAKET or w in _CATI_EKLERI:
                continue
            if not any(_ortak_kok(w, x) for x in oda):
                return False
            if re.search(r"l[ae]r(?:i|in|ini|a|e|da|de|dan|den)?$", w) and len(eslesen) < 2:
                return False                                   # çoğul oda sözü tek notla kapsanmaz
    return True


def _zaten_notu(notlar: list[str]) -> str:
    """D-86: istenen değişiklik planda zaten var. Pencere notu "… penceresi zaten 100x140" olur (seçilmiş pencerenin önceki ölçüsü yazılmaz:
    "MUTFAK 120x120 sol penceresi 120x120" → "MUTFAK sol penceresi zaten 120x120"); başka not genel cümleyle; not yoksa boş."""
    parcalar = []
    for n in notlar:
        if "sayıldı" in n:                              # "… mevcut penceresi ölçü değişikliği sayıldı (ekleme değil)": açıklama notu
            continue
        m = re.fullmatch(r"(.+?) penceresi (\d{2,3}x\d{2,3})", n)
        if not m:
            return "istediğiniz değişiklik planda zaten var"
        ad = _ADDAKI_OLCU.sub("", m.group(1))
        parcalar.append(f"{ad} penceresi zaten {m.group(2)}")
    return ", ".join(parcalar)


_CIZIM_OKUMA = "cizim-okuma"                           # `gorsel_okuma.KAYNAK`: plan bayinin çiziminden okundu (İE-20)


def _plan_basi(katalog: Katalog, kaynak: str, rev: int, ozet: str) -> str:
    """D-85: prefabrik plan metninin başı, kodun metni. Model: "PA-06 seçildi" / "PA-06 r02". Çizimden okunan plan: r01'de okumanın
    kod metni ("Çiziminizdeki plan (7,73 × 8,88 m, 2+1)", `worker`), sonra "Çiziminizdeki plan r02". Dış ölçüden kurulan plan (GRID):
    r01'de baş yok ("Dış ölçü … pano)." ön bilgisi yeter), sonra "Plan r02"."""
    if kaynak == _CIZIM_OKUMA:
        ad = "Çiziminizdeki plan"
        return (ozet.strip().rstrip(".") if ozet.startswith(ad) else ad) if rev == 1 else f"{ad} r{rev:02d}"
    if str(kaynak).startswith("GRID-"):
        return "" if rev == 1 else f"Plan r{rev:02d}"
    ad = _gorunen_kod(katalog, kaynak)
    return f"{ad} seçildi" if rev == 1 else f"{ad} r{rev:02d}"


def _gorunen_kod(katalog: Katalog, kod: str) -> str:
    """Bayinin gördüğü kod: aday kaydının gösterimi ("PA06K" → "PA-06-K"); katalog modeli kendi kodu ("P6001")."""
    a = (getattr(katalog, "adaylar", None) or {}).get(Katalog.kod_normalize(kod) or "")
    return SC.gosterim(a) if a else str(kod)


_TR = str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")
_EKLE_RX = re.compile(r"\b(ekle\w*|ilave\w*|fazladan|ek (bir )?pencere|yeni (bir )?pencere|ikinci (bir )?pencere|bir tane daha|bir de\b"
                      r"|(bir|1) (tane )?pencere (koy\w*|ac\w*|olsun|istiyor\w*|lazim|gerek\w*)|pencere koy\w*)")
_DEGISTIR_RX = re.compile(r"\b(degis\w*|yap\w*|olsun|olacak|olmali|penceresi\w*|olcusu\w*|buyut\w*|kucult\w*|yerine|cevir\w*|genislet\w*)\b")


def _sozcuk_norm(metin: str) -> str:
    """Küçük harf, Türkçe harfler sadeleştirilmiş, noktalama boşluk; SÖZCÜK SINIRLARI KORUNUR ('bekle' ≠ 'ekle')."""
    q = (metin or "").translate(_TR).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", q)).strip()


_PENCERE_CEVAP_SOZ = re.compile(r"degis\w*|ekle\w*|ilave\w*|yap\w*|olsun|olcu\w*|pencere\w*|ikinci|tane|daha|sadece|onu")


def _pencere_cevabi_saf(metin: str | None) -> bool:
    """Kısa cevapta "değiştir"/"ekle" ve dolgu sözcükleri dışında sözcük yok mu? ("aynalı olsun" saf değildir.)"""
    return all(_PENCERE_CEVAP_SOZ.fullmatch(w) or w in _DOLGU or w in _SELAM for w in _sozcuk_norm(metin).split())


def _pencere_anahtari(p: dict) -> tuple:
    """Konuşma taslağındaki pencere satırının kimliği (konusma._anahtar ile aynı: mahal, işlem, duvar)."""
    return (str(p.get("mahal") or "").strip().lower(), p.get("islem"), p.get("duvar"))


_OLUMSUZ_PENCERE = re.compile(r"\b(olmasin\w*|olmayacak|istemiyor\w*|istemem|degil\w*|yok|degistirme\w*|yapma\w*|ekleme\w*|koyma\w*)\b")
_SORU_EKI = re.compile(r"\b(mi|mu|misiniz|musunuz|miyiz|muyuz|midir|mudur|mismiz)\b")
_ACIK_YENI = re.compile(r"\b(yeni (bir )?(talep|proje|ev|siparis|musteri|teklif)\w*|baska (bir )?(talep|proje|ev|musteri|siparis)\w*|sifirdan)\b")


def _acik_yeni_talep(metin: str | None) -> bool:
    """Bayi açıkça yeni bir talep mi diyor? ("yeni talep", "yeni bir ev", "başka müşteri için", "sıfırdan"; "yeni pencere"
    ve hemen ardından olumsuzlanan "yeni talep değil" sayılmaz)"""
    q = " " + _sozcuk_norm(metin) + " "
    return any(not re.match(r"\s*(degil|yok)\b", q[m.end():]) for m in _ACIK_YENI.finditer(q))


def _olcu_norm(s: str | None) -> str | None:
    m = re.search(r"(\d{2,3})\s*[xX×*]\s*(\d{2,3})", s or "")
    return f"{m.group(1)}x{m.group(2)}" if m else None


def _pencere_soz_niyeti(metin: str | None, mahal: str | None, olcu: str | None) -> str:
    """Bir pencere satırı için bayinin sözü. Yalnız o satırı anan bölümler okunur (oda adı, ölçü ya da "pencere" geçen);
    "çatı beşik olsun"daki "olsun" pencereye sayılmaz. Bu bölümlerde olumsuzluk ("olmasın", "değiştirmeyin") ya da soru
    ("… yapsak değişir mi?") varsa söz belirsizdir: pencere sessizce değişmez, sorulur."""
    parcalar = re.findall(r"[^;,.!?\n]+[;,.!?\n]*", metin or "")
    mahal_n = varyant._norm(mahal or "") if mahal else ""
    olcu_n = _olcu_norm(olcu) if olcu else None
    ilgili = []
    for parca in parcalar:
        q = _sozcuk_norm(parca)
        bitisik = q.replace(" ", "")
        if (olcu_n and _olcu_norm(parca) == olcu_n) or (mahal_n and mahal_n in bitisik) or re.search(r"\bpencere\w*", q):
            ilgili.append(parca)
    if not ilgili:
        return _pencere_niyeti(metin)
    for parca in ilgili:
        q = " " + _sozcuk_norm(parca) + " "
        if "?" in parca or _SORU_EKI.search(q) or _OLUMSUZ_PENCERE.search(q):
            return "belirsiz"
    return _pencere_niyeti(" ".join(ilgili))


def _olumsuz_ya_da_soru(metin: str | None) -> bool:
    q = " " + _sozcuk_norm(metin) + " "
    return "?" in (metin or "") or bool(_SORU_EKI.search(q)) or bool(_OLUMSUZ_PENCERE.search(q))


def _pencere_niyeti(metin: str | None) -> str:
    """Bayinin sözünde pencere için ne var: 'ekle' (açık ekleme sözü), 'degistir' (açık ölçü değiştirme sözü), 'belirsiz' (ikisi de yok
    ya da ikisi de var). Sözcük sınırıyla arar: 'bekle' ekleme değildir; 'bir pencere koy' eklemedir; 'penceresi 120x180 olsun' değişikliktir."""
    q = " " + _sozcuk_norm(metin) + " "
    if _olumsuz_ya_da_soru(metin):      # 29.09 (Astra): "değiştirme", "eklemeyin", "olmasın", "… mi?" hiçbir işlem sayılmaz
        return "belirsiz"
    ekle = bool(_EKLE_RX.search(q)); degistir = bool(_DEGISTIR_RX.search(q))
    if ekle and not degistir:
        return "ekle"
    if degistir and not ekle:
        return "degistir"
    return "belirsiz"


def _pencere_varyantlarina_soz_isle(t: Talep, metin: str | None) -> Talep:
    """Bu mesajdan gelen her "pencere_degistir" varyantına bayinin bu mesajdaki sözü (soz_niyeti) işlenir. Varyant İş Emri
    üretilirken odası bulunursa pencere satırına çevrilir ve B1 kuralları uygulanır (bkz. _is_emri_uret): söz belirsizse sorulur."""
    if not any(v.tur == "pencere_degistir" for v in t.varyantlar):
        return t
    from .sema import Varyant
    yeni = []
    for v in t.varyantlar:
        if v.tur == "pencere_degistir":
            prm = dict(v.parametreler or {})
            olcu = prm.get("yeni") or prm.get("olcu") or prm.get("yeni_olcu") or _olcu_bul(v.aciklama)
            prm["soz_niyeti"] = _pencere_soz_niyeti(metin, prm.get("mahal"), olcu)
            v = Varyant(tur=v.tur, aciklama=v.aciklama, parametreler=prm)
        yeni.append(v)
    return t.model_copy(update={"varyantlar": yeni})


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
        elif a.upper() in ("KT", "PA") and i + 1 < len(toks) and re.fullmatch(r"\d{2}", toks[i + 1]):        # İE-08: "KT-01", "KT 01"; İE-36: "PA-04"
            a = a + toks[i + 1]; i += 1
        # İE-08: varyant harfi ayrı belirteçse ("Ç8801-K", "Ç8801 K") ve o aday kayıtlıysa birleşir; LLM'siz, yalnız kayıtlı kodlar
        # İE-37: prefabrik çatı seçeneği de ("PA-06-K", "PA 06 K"; yalnız kayıtlı ve görünür kod)
        if re.fullmatch(r"[PÇC]\d{4}|PA\d{2}", a.upper()) and i + 1 < len(toks) and re.fullmatch(r"[A-Za-z]", toks[i + 1]) and katalog.aday(a + toks[i + 1].upper()):
            a = a + toks[i + 1].upper(); i += 1
        m = katalog.bul(a)
        ad = katalog.aday(a) if m is None else None
        out.append((sira, a, m["code"] if m else (ad["kod"] if ad else None)))
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
        # BK-08 madde 9: gerekçe günlüğe gider; bayinin cümlesi yazılmaz, yalnız bekleyen talebin kodu (metin konuşma kaydında ve panelde)
        kod = (k.d.get("bekleyen_talep") or {}).get("katalog_kodu") or "kodsuz"
        _bekleyeni_birak(k); k.d.pop("eski_taslak_soru", None)
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"eski taslak sorusu cevapsız (D-01); bekleyen mesaj: {numara.maskele(str(kod))} talebi",
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


_ONCELIK_SOZ = {"butce": re.compile(r"\b(butce|ucuz|ekonomik|fiyat|maliyet)\w*"),
                "yasam": re.compile(r"\b(yasam|salon|genis|ferah|buyuk oda)\w*"),
                "montaj": re.compile(r"\b(montaj|hizli|cabuk|kisa sure|erken)\w*"),
                "yok": re.compile(r"\b(fark etmez|farketmez|hepsi|yok|onemli degil|onemsiz|gecin|atla)\w*")}


def _oncelik_cevabi(metin: str | None) -> str | None:
    """Kısa öncelik cevabı: 'butce' | 'yasam' | 'montaj' | 'yok' | None (cevap değil ya da iki öncelik birden)."""
    q = " " + _sozcuk_norm(metin) + " "
    if len(q.split()) > 8:
        return None
    eslesen = [ad for ad, rx in _ONCELIK_SOZ.items() if rx.search(q)]
    return eslesen[0] if len(eslesen) == 1 else None


def _seti_kapat(k: Konusma, kod: str) -> None:
    """Açık seçenek seti varsa seçimle kapanır (setteki ya da set dışı bir aday kodu)."""
    st = k.d.get("secenek_seti")
    if st and st.get("durum") == "acik":
        st["durum"] = "secildi"; st["secilen_kod"] = kod
        st["set_disi"] = kod not in {a["kod"] for a in st.get("adaylar") or []}
        if st.get("tur") == "cati_varyanti":
            _cati_secildi(k, kod)                     # İE-42: çatı seçildi; onayda çatı seti yeniden sunulmaz
        k.not_dus("kural", f"seçenek setinden seçim: {kod}" + (" (set dışı)" if st["set_disi"] else ""))


def _secenekler(k: Konusma, katalog: Katalog, ts: dict, uygun: list[dict] | None = None, tur: str = "alan", referans: dict | None = None,
                ek_not: str = "", bas: str | None = None, gerekce_on: str = "") -> Karar | None:
    """İE-04: aday kaydından uyan aday varsa seçenek seti. Önce (bir kez) öncelik sorulur; sonra set sunulur. Hiç aday yoksa None
    (çağıran bugünkü davranışa döner). Set kaydı konuşmadadır; kimlikler s:<set>:<kod>; eski set 'eskidi' olur.
    İE-08: `uygun` verilirse (çatı seti, tur 'cati_varyanti') sıra hazırdır, puanlanmaz; çelikte öncelik sorusu hiç sorulmaz (Lokman, 12.10.2026).
    `ek_not` (yalnız çelik): set mesajının sonuna (saklanan değişiklik isteği, yeniden sunum)."""
    hazir = uygun is not None
    uygun = SC.tek_plan(SC.uygun_adaylar(katalog, ts)) if uygun is None else uygun     # İE-25: çatı varyantı plan seçilince
    if not uygun:
        return None
    celik_mi = ts.get("yapi_turu") == "celik" or SC.celik_seti_mi(uygun)
    if ts.get("oncelik") is None and len(uygun) >= 2 and not celik_mi and tur != "cati_varyanti":   # İE-37: çatı setinde öncelik yok
        k.d["taslak"]["oncelik_soruldu"] = True
        return _soru(k, "oncelik", "Sıralamada ne öne çıksın: bütçe mi, yaşam alanı mı, kısa montaj mı? Fark etmezse \"fark etmez\" yazın.",
                     butonlar=[{"id": "q:oncelik:butce", "baslik": "Bütçe önce"}, {"id": "q:oncelik:yasam", "baslik": "Yaşam alanı önce"},
                               {"id": "q:oncelik:montaj", "baslik": "Kısa montaj"}])
    sirali = uygun if hazir else SC.puanla(uygun, ts)
    kaynak_id = getattr(k, "son_mesaj_id", None) or f"{k.gonderen}:{int(time.time())}"   # worker.isle verir: aynı mesaj → aynı set kimliği
    st = SC.set_kaydi(kaynak_id, sirali, ts, tur=tur)
    eski = k.d.get("secenek_seti")
    if eski and eski.get("durum") == "acik" and eski.get("id") != st["id"]:
        eski["durum"] = "eskidi"
        k.d.setdefault("eski_setler", []).append(eski)
        k.d["eski_setler"] = k.d["eski_setler"][-5:]
    k.d["secenek_seti"] = st
    test_var = any(a.get("durum") == "test" for a in st["adaylar"])
    mesaj = SC.cati_mesaji(sirali, referans or sirali[0], bas) if tur == "cati_varyanti" else SC.mesaj_metni(sirali, ts)
    if test_var:
        mesaj = "[TEST VERİSİ — gerçek seçenek değildir] " + mesaj
    if ek_not:
        mesaj = f"{mesaj}\n\n{ek_not}"
    butonlar = [{"id": f"s:{st['id']}:{a['kod']}", "baslik": f"{a['sira']}. {SC.gosterim(a)}"[:20]} for a in sirali[:SC.EN_COK_GORSEL]]
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = "secenek"
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="secenek", soru_alani="secenek", mesaj=mesaj, secenek_seti=st, butonlar=butonlar,
                           gerekce=f"{gerekce_on}seçenek seti {st['id']}: {len(sirali)} aday" + (" (test verisi)" if test_var else "")))


def _soru(k: Konusma, alan: str, metin: str, butonlar: list[dict] | None = None) -> Karar:
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = alan
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani=alan, mesaj=metin, gerekce=f"eksik: {alan}", butonlar=butonlar))


# ───────────────────────── BK-29 PR-2 (pano 201, 210): oda ve pencere soruları, plan değişmedi ─────────────────────────
# 13 Kasım 2026 WhatsApp denetimi: iki pencereli odada bot soru sormadan yönlendiriyordu ("mutfak penceresi 120x120 olsun", PA-06);
# "salonun sol penceresi" sözündeki "sol" okunmuyordu; "Hangi odanın penceresi?" sorusuna "Oda 1" cevabı anlaşılmıyordu.
PLAN_DEGISMEDI = "plan değişmedi"
_DUVAR_ADI = {"sol": "sol", "sag": "sağ", "on": "ön", "arka": "arka"}
_DUVAR_SOZ = {"sol": re.compile(r"\bsol(da|daki|u|unda|undaki)?\b"),
              "sag": re.compile(r"\bsag(da|daki|i|inda|indaki)?\b"),
              "arka": re.compile(r"\barka(da|daki|si|sinda|sindaki)?\b"),
              "on": re.compile(r"\b(onde|ondeki|onunde|onundeki)\b|\bon (duvar|cephe|taraf)\w*")}
_ON_HAM = re.compile(r"(?<!\w)(ön|önde|öndeki|önü|önünde|önündeki)(?!\w)(?!\s+onay)")    # "ön onay planı" duvar değil (hakem 4)
# BK-29 tur 5 (pano 216; tur 3 canlı gözlem 1): onay bekleyen planda "iptal" ilk yazışta "Anladım. Neyi değiştirelim?" alıyordu, talep
# ikinci "iptal"le kapanıyordu. Bayinin açık iptal sözü (K18) talebi ilk yazışta kapatır; "beğenmedim", "olmadı", "hayır" revizyon sorusu alır.
_IPTAL_SOZU = re.compile(r"(?:(?:bu |o )?(?:talebi|talep|plani|siparisi|isi) )?(?:iptal(?: e[td]\w*| olsun)?"
                         r"|vazgec\w*)(?: lutfen| ltf)?$")
_IPTAL_OLUMSUZ = re.compile(r"\b(?:e[td]|vazgec)\w*?m[ei](?:y|z|s|d|$|\s)")    # "iptal etmeyin", "etme", "edilmesin", "vazgeçmedim"


def _iptal_sozu(metin: str | None) -> bool:
    """Mesaj yalnız açık iptal sözü mü ("iptal", "iptal edin", "talebi iptal et", "vazgeçtik")? Olumsuz ve soru biçimi değil."""
    q = _sozcuk_norm(metin or "")
    return bool(_IPTAL_SOZU.match(q)) and not _IPTAL_OLUMSUZ.search(q)


def _iptal_olumsuz_sozu(metin: str | None) -> bool:
    """Mesaj yalnız iptal sözünün olumsuz biçimi mi ("iptal etmeyin", "iptal etme", "vazgeçmedim")? Açık planı kapatmaz."""
    q = _sozcuk_norm(metin or "")
    return bool(_IPTAL_SOZU.match(q)) and bool(_IPTAL_OLUMSUZ.search(q))


_NEYI_DEGISTIRELIM_PREFABRIK = "Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120 olsun\")."


def _neyi_degistirelim(k: Konusma, katalog: Katalog) -> str:
    """"Revize et" cevabı: yalnız otomatik yapılabilen değişiklikler örnek gösterilir (pano 210; kapı, veranda, oda yerleşimi yok)."""
    ie = k.d.get("son_is_emri") or {}
    if str((k.d.get("taslak") or {}).get("katalog_kodu") or "").startswith(YENI_ONEK):
        return _NEYI_DEGISTIRELIM_YENI
    if (ie.get("yapi") or {}).get("sistem") == "celik":
        return _celik_neyi(k, katalog)                # İE-20 PR-10: yalnız bu planda yapılabilen örnekler
    return _NEYI_DEGISTIRELIM_PREFABRIK


def _olculer_metin(metin: str | None) -> list[str]:
    return [f"{a}x{b}" for a, b in re.findall(r"(\d{2,3})\s*[xX×*]\s*(\d{2,3})", metin or "")]


# BK-29 tur 4 (pano 201, canlı B4): LLM şeması pencere ölçüsünü listeden seçer (`sema.Pencere.olcu`); listede olmayan ölçü ("120x150") null
# döner ya da listedeki bir ölçüye kayar, bot ölçüyü yeniden sorar, "120x150" cevabını da almaz. Kayıtta olmayan ölçü kurulur (İE-27
# madde 11; Lokman 3 Kasım 09:52 "hangisi geldiyse onu uygula"): yeni ölçüyü kod bayinin sözünden okur (K18).
_YENI_OLCU_FIILI = re.compile(r"(olsun|olacak|olmali\w*|yap\w*|cevir\w*|degis\w*|buyut\w*|kucult\w*|ile|istiyor\w*|isteriz|lazim|gerek\w*)$")
_OLCU_EKI = {"lik", "luk", "e", "a", "ye", "ya", "olarak", "cm"}


def _pencere_olcusu_mu(o: str) -> bool:
    en, yuk = (int(x) for x in o.split("x"))
    return varyant.PENCERE_EN[0] <= en <= varyant.PENCERE_EN[1] and varyant.PENCERE_YUK[0] <= yuk <= varyant.PENCERE_YUK[1]


def _sozdeki_yeni_olcu(metin: str | None) -> str | None:
    """Sözdeki yeni pencere ölçüsü: ardından değiştirme sözü gelen ölçü ("120x150 olsun", "120x150'ye çevir", "120x150 yapın"); böyle
    ölçü yoksa sözdeki tek ölçü. Eski ölçü sayılmaz: "pencere", "yerine" ya da "olan"dan önceki ölçü ("120x100 pencere", "120x100 olan").
    Birden çok aday kalırsa okunmaz (soru gelir; K21). Pencere ölçüsü aralığı dışındaki sayı ("700x400" dış ölçü) ölçü sayılmaz."""
    q = CO.norm(re.sub(r"(\d{2,3})\s*[xX×*]\s*(\d{2,3})", r" \1x\2 ", metin or ""))
    toks = q.split()
    yeni, eski, hepsi = set(), set(), set()
    for i, t in enumerate(toks):
        if not re.fullmatch(r"\d{2,3}x\d{2,3}", t) or not _pencere_olcusu_mu(t):
            continue
        hepsi.add(t)
        j = i + 1
        while j < len(toks) and toks[j] in _OLCU_EKI:
            j += 1
        sonraki = toks[j] if j < len(toks) else ""
        if sonraki in ("yerine", "olan", "olani", "olanin") or sonraki.startswith("pencere"):
            eski.add(t)
        elif _YENI_OLCU_FIILI.match(sonraki):
            yeni.add(t)
    kalan = hepsi - eski
    if yeni:                                          # "120x150 ve 120x180 olsun": sınıflanmayan ölçü varken okunmaz
        return yeni.pop() if len(yeni) == 1 and kalan == yeni else None
    return kalan.pop() if len(kalan) == 1 else None


_OLCU_CEVABI_DOLGU = {"lik", "luk", "olsun", "olacak", "olmali", "olsa", "yap", "yapin", "yapiniz", "yapalim", "yapar", "misiniz", "cm",
                      "lutfen", "olarak", "ebatinda", "olcusunde", "olcude", "tamam", "evet", "e", "a", "ye", "ya"}


def _yalniz_olcu(metin: str | None) -> str | None:
    """Ölçü sorusunun cevabı yalnız bir pencere ölçüsüyse ("120x150", "120 x 150 olsun", "120x150'lik yapın lütfen") o ölçü; değilse None."""
    q = CO.norm(re.sub(r"(\d{2,3})\s*[xX×*]\s*(\d{2,3})", r" \1x\2 ", metin or "")).split()
    olcu = [t for t in q if re.fullmatch(r"\d{2,3}x\d{2,3}", t)]
    if len(olcu) != 1 or not _pencere_olcusu_mu(olcu[0]) or any(t not in _OLCU_CEVABI_DOLGU for t in q if t != olcu[0]):
        return None
    return olcu[0]


def _odanin_yeni_olcusu(soz: str | None, ie: dict, mahal: str | None) -> str | None:
    """Pencere satırının yeni ölçüsü bayinin sözünden; söz birden çok odayı anıyorsa yalnız bu odanın parçası okunur ("Yatak odası 1
    penceresi 120x150, salon 160x180 olsun" → yatak odası 1 için 120x150). Oda tek bir odayla eşleşmiyorsa bütün söz."""
    odalar = [m["ad"] for m in ie.get("mahaller") or []]
    eslesen = _mahal_eslestir(ie, mahal) if mahal else []
    if len(eslesen) != 1:
        return _sozdeki_yeni_olcu(soz)
    oda, oteki = eslesen[0], [o for o in odalar if o != eslesen[0]]
    parcalar = [x for x in re.split(r"[;,.!?\n]+", soz or "") if x.strip()]
    ilgili = [_oda_parcasi(x, oda, oteki) for x in parcalar if _odayi_aniyor(x, oda)] \
        or [x for x in parcalar if not any(_odayi_aniyor(x, o) for o in oteki)]
    adaylar = {o for x in ilgili for o in [_sozdeki_yeni_olcu(x)] if o}
    return adaylar.pop() if len(adaylar) == 1 else None


def _duvarlar_metin(metin: str | None) -> set[str]:
    """Bayinin sözündeki duvar: "sol", "soldaki", "sağ duvarındaki", "ön cephedeki", "arkadaki" (İş Emri: sol, sag, on, arka)."""
    q = " " + _sozcuk_norm(metin or "") + " "
    out = {d for d, rx in _DUVAR_SOZ.items() if rx.search(q)}
    if _ON_HAM.search((metin or "").lower()):
        out.add("on")
    return out


def _oda_pencereleri(ie: dict, mahal: str) -> list[dict]:
    return [a for a in ie.get("acikliklar", []) if a["tur"] == "pencere" and a.get("mahal") == mahal]


def _pencere_gruplari(ie: dict, mahal: str) -> list[dict]:
    """Odanın pencereleri, bayinin ayırt edebildiği gibi: aynı ölçü ve aynı duvardakiler tek seçenek. sira: odadaki pencere sırası (0'dan)."""
    gruplar: list[dict] = []
    for i, a in enumerate(_oda_pencereleri(ie, mahal)):
        g = next((g for g in gruplar if (g["olcu"], g["duvar"]) == (a.get("olcu"), a.get("duvar"))), None)
        if g is None:
            gruplar.append({"olcu": a.get("olcu"), "duvar": a.get("duvar"), "sira": [i]})
        else:
            g["sira"].append(i)
    return gruplar


def _grup_adi(g: dict, kisa: bool = False) -> str:
    d, n = _DUVAR_ADI.get(g.get("duvar") or "", ""), len(g.get("sira") or [])
    if kisa:                                          # düğme başlığı (en çok 20 karakter): "120x100 sol", "120x120 arka (2)"
        return (f"{g['olcu']} {d}".strip() + (f" ({n})" if n > 1 else ""))[:20]
    return str(g["olcu"]) + (f", {d} duvar" if d else "") + (f" ({n} pencere)" if n > 1 else "")


def _onceki_olcuyle(g: dict, onceki: dict | None, ie0: dict, oda: str, sira: list[int], yeni: str) -> dict:
    """Değişiklik notundaki pencere adı, bayinin önceki planda gördüğü ölçüyle (BK-29 tur 4, canlı gözlem 4: r02'de 120x120 olan sol
    pencere r03'ün notunda "120x100 sol" anılıyordu). Pencere önceki planda zaten yeni ölçüdeyse (önceki revizyonun değişikliği sürer)
    ya da önceki plan bu odada başka sayıda pencere taşıyorsa şablondaki ölçü kalır. Sıra şablonla aynıdır (`varyant.pencere_degistir`
    pencereyi yerinde değiştirir)."""
    p0, p1 = _oda_pencereleri(ie0, oda), _oda_pencereleri(onceki or {"acikliklar": []}, oda)
    if len(p1) != len(p0):
        return g
    olculer = {p1[i].get("olcu") for i in set(g["sira"]) & set(sira) if i < len(p1)}
    if len(olculer) == 1 and None not in olculer and yeni not in olculer:
        return {**g, "olcu": olculer.pop()}
    return g


# çoğul söz: aynı ölçü ve duvardaki pencerelerin hepsi. Tekil kısıt ("biri", "sadece", "diğer pencereler kalsın") varsa çoğul değildir
# (hakem ikinci tur 1: "arka pencerelerinden biri" ikisini birden değiştiriyordu)
_COGUL = re.compile(r"\b(pencereler|pencereleri|pencerelerin|pencerelerini|pencerelerinin|ikisi de|ikiside|ikisini de|her ikisi\w*|"
                    r"hepsi|hepsini|tumu|tumunu|butun pencere\w*|tum pencere\w*)\b")
# "İkisini de … yapalım mı?" sorusuna "yalnız biri" anlamı taşıyan cevap (yönlendirilir); "diğer her şey kalsın", "tek kanat" değil
_BIRI = re.compile(r"\b(biri|birini|birisi|birisini|bir tane\w*|1 tane\w*|tek tane\w*|tekini|sadece bir\w*|yalniz bir\w*|yalnizca bir\w*|"
                   r"sadece 1|yalniz 1|ilki\w*|ilkini|birinci\w*|ikinci\w*|sonuncu\w*|soldaki\w*|sagdaki\w*)\b")
_TEKIL = re.compile(r"\b(biri|birini|birinin|birisi|birisini|tek|tekini|sadece|yalniz|yalnizca|diger\w*|kalsin|haric|\w+den biri)\b")


def _govde(w: str) -> str:
    """Oda adı sözcüğünün eksiz gövdesi: "mutfak" → "mutfa" ("mutfağın"), "yatak" → "yata" ("yatağın"); sayı olduğu gibi."""
    return w[:-1] if len(w) > 3 and not w.isdigit() and w[-1] in "kptc" else w


def _odayi_aniyor(parca: str, mahal: str) -> bool:
    """Cümle bu odayı anıyor mu (eklerle: "mutfağın", "salonun", "yatak odası 1'in")? "SALON+MUTFAK" parçalarından biri yeter; öteki
    adlarda bütün sözcükler (numara dahil) geçmeli."""
    soz = CO.norm(parca).split()
    if not soz:
        return False
    adlar = [CO.norm(x).split() for x in str(mahal).split("+")] if "+" in str(mahal) else [CO.norm(mahal).split()]
    for ad in adlar:
        if ad and all(any((t == w) if w.isdigit() else t.startswith(_govde(w)) for t in soz) for w in ad):
            return True
    return False


def _oda_parcasi(parca: str, mahal: str, oteki: list[str]) -> str:
    """Cümle birden çok odayı anıyorsa bu odanın kendi parçası: odanın adından öteki bir odanın adına kadar ("Salonun ön penceresi ile
    mutfak penceresi 120x180 olsun" → mutfak için "mutfak penceresi 120x180 olsun"). Duvar ve eski ölçü odanın adından sonra yazılır
    ("mutfağın sol penceresi"); adından önce yazılan söz okunmaz, soru gelir (güvenli yön)."""
    if not any(_odayi_aniyor(parca, o) for o in oteki):
        return parca
    toks = parca.split()

    def basi(ad: str) -> set[int]:
        out = set()
        for parca_ad in str(ad).split("+"):
            w = CO.norm(parca_ad).split()
            if w:
                out |= {i for i, t in enumerate(toks) if any(x.startswith(_govde(w[0])) for x in CO.norm(t).split())}
        return out

    bu = sorted(basi(mahal))
    if not bu:
        return parca
    obur = sorted(set().union(*(basi(o) for o in oteki)) - set(bu))
    son = next((i for i in obur if i > bu[0]), len(toks))
    if son < len(toks):
        # öteki odanın adından önceki sıfat ("ile öndeki salon", "ve ön cephedeki salon") o odanındır: parça bağlaçta biter
        # (hakem üçüncü tur 2); bağlaç yoksa iki odanın sözü ayrılamaz, yalnız oda adı kalır (duvar okunmaz, soru gelir)
        # öteki odaya en yakın bağlaç: odanın kendi içindeki "sol ve ön pencereleri" bölünmez (hakem dördüncü tur)
        baglac = next((i for i in range(son - 1, bu[0], -1) if CO.norm(toks[i]) in ("ile", "ve", "veya", "ya", "yada")), None)
        son = baglac if baglac is not None else bu[0] + 1
    return " ".join(toks[bu[0]:son])


def _sozle_daralt(metin: str | None, yeni: str | None, gruplar: list[dict], mahal: str = "", odalar: list[str] | None = None) \
        -> tuple[list[int], bool]:
    """Bayinin sözünde pencereyi ayıran eski ölçü ve duvar (K18): "Mutfağın sol duvarındaki 120x100 pencere 120x120 olsun",
    "salonun sol penceresi 120x180 olsun". Okunan cümleler (hakem 3: başka odanın cümlesi okunmaz): yeni ölçünün geçtiği ve bu odayı anan
    cümle; yoksa yeni ölçünün geçtiği ve hiçbir odayı anmayan cümle; yoksa bu odayı anan cümle. Döner: (kalan grupların sırası, çoğul söz
    var mı: "pencereleri", "ikisi de"). Söylenen ölçü ya da duvar odada yoksa o ipucu daraltmaz (soru gelir)."""
    parcalar = [x for x in re.split(r"[;,.!?\n]+", metin or "") if x.strip()]
    oteki = [o for o in odalar or [] if o != mahal]
    olculu = [x for x in parcalar if yeni and yeni in _olculer_metin(x)]
    ilgili = [x for x in olculu if _odayi_aniyor(x, mahal)] \
        or [x for x in olculu if not any(_odayi_aniyor(x, o) for o in oteki)] \
        or [x for x in parcalar if _odayi_aniyor(x, mahal)]
    ilgili = [_oda_parcasi(x, mahal, oteki) for x in ilgili]       # hakem ikinci tur 3: cümlede öteki odanın sözü okunmaz
    eski = {o for x in ilgili for o in _olculer_metin(x)} - ({yeni} if yeni else set())
    duvarlar: set[str] = set()
    for x in ilgili:
        duvarlar |= _duvarlar_metin(x)
    kalan = list(range(len(gruplar)))
    if eski:
        kalan = [i for i in kalan if gruplar[i]["olcu"] in eski] or kalan
    if duvarlar:
        kalan = [i for i in kalan if gruplar[i]["duvar"] in duvarlar] or kalan
    q = [" " + CO.norm(x) + " " for x in ilgili]
    return kalan, any(_COGUL.search(x) for x in q) and not any(_TEKIL.search(x) for x in q)


def _secilenleri_ayir(satirlar: list[dict]) -> list[dict]:
    """Aynı odada seçilmiş pencere satırları örtüşmez: bir pencere en son hangi satırla değiştiyse o satırda kalır, eski satırdan çıkar;
    penceresi kalmayan eski satır düşer (hakem 2: r03 "ikisi de" [0, 1], r04 ön [1]; sonraki revizyonda ön pencere r03'ün ölçüsüne
    dönüyordu). Sıra korunur; seçilmemiş satırlar olduğu gibi."""
    alinan: dict[str, set[int]] = {}
    out: list[dict] = []
    for r in reversed(satirlar):
        if r.get("pencere_sira") is None:
            out.append(r); continue
        oda = varyant._norm(r.get("mahal") or "")
        kalan = [i for i in r["pencere_sira"] if i not in alinan.setdefault(oda, set())]
        if not kalan:
            continue
        alinan[oda] |= set(kalan)
        out.append({**r, "pencere_sira": kalan} if kalan != list(r["pencere_sira"]) else r)
    return list(reversed(out))


def _pencere_secimi(k: Konusma, ie: dict, mahal: str, p0: dict) -> list[int] | Karar:
    """Birden çok pencereli odada değişecek pencere: bayinin sözü ayırıyorsa o, ayırmıyorsa "Hangi pencere?" (her pencereye bir düğme;
    3'ten çoksa liste). Aynı ölçü ve aynı duvardaki pencereler bayi için ayırt edilemez, birlikte değişir. Döner: odadaki pencere sırası."""
    gruplar = _pencere_gruplari(ie, mahal)
    kalan, cogul = _sozle_daralt(p0.get("soz") or k.d.get("son_metin"), p0.get("olcu"), gruplar, mahal,
                                 [m["ad"] for m in ie.get("mahaller") or []])
    if kalan and (cogul or (len(kalan) == 1 and len(gruplar[kalan[0]]["sira"]) == 1)):
        # tek pencere ya da çoğul söz ("mutfak pencereleri", "sol ve ön pencereleri", "arka pencereleri"): sözün kapsadığı hepsi
        k.not_dus("kural", f"BK-29: {mahal} penceresi bayinin sözünden seçildi ({'; '.join(_grup_adi(gruplar[i]) for i in kalan)})")
        return sorted(i for j in kalan for i in gruplar[j]["sira"])
    n = len(_oda_pencereleri(ie, mahal))
    if len(kalan) == 1:
        # hakem 5: aynı ölçü ve aynı duvardaki pencereleri bayi ayırt edemez; tekil sözle hepsi sessizce değişmez, sorulur
        g = gruplar[kalan[0]]
        m = len(g["sira"])
        yer = f"{_DUVAR_ADI[g['duvar']]} duvarında" if g.get("duvar") in _DUVAR_ADI else "aynı duvarda"
        hepsi = "İkisini de" if m == 2 else "Hepsini"
        secenekler = [g]
        metin = f"{mahal} odasının {yer} {m} adet {g['olcu']} pencere var. {hepsi} {p0['olcu']} yapalım mı?"
        butonlar = [{"id": "q:pencere_secim:1", "baslik": "İkisi de" if m == 2 else "Hepsi"},
                    {"id": "q:pencere_secim:0", "baslik": "Hiçbiri"}]
    else:
        secenekler = [gruplar[i] for i in kalan][:10]
        liste = "; ".join(f"{i}) {_grup_adi(g)}" for i, g in enumerate(secenekler, 1))
        metin = f"{mahal} odasında {n} pencere var. Hangisini {p0['olcu']} yapalım? {liste}."
        butonlar = [{"id": f"q:pencere_secim:{i}", "baslik": _grup_adi(g, kisa=True)} for i, g in enumerate(secenekler, 1)]
    k.d["pencere_secim"] = {"mahal": mahal, "olcu": p0["olcu"], "satir": list(_pencere_anahtari(p0)), "secenekler": secenekler,
                            "metin": metin, "butonlar": butonlar}
    return _soru(k, "pencere_secim", metin, butonlar)


# tek seçenekli onay sorusunun cevabı yalnız bu sözcüklerden oluşursa onaydır; "evet sadece biri", "olur mu", "tamam ama birini" değildir
# (hakem ikinci tur 2): soru yinelenir
_ONAY_OLUMLU = {"evet", "olur", "tamam", "ok", "ikisi", "ikiside", "ikisini", "ikisinide", "hepsi", "hepsini", "tumu", "tumunu", "yapalim", "yapin",
                "degistir", "degistirin", "degistirelim"}
_ONAY_SOZ = _ONAY_OLUMLU | {"de", "da", "her", "olsun", "lutfen", "evet,", "aynen"}


def _pencere_secim_cevabi(metin: str | None, secenekler: list[dict]) -> list[int] | str | None:
    """"Hangi pencere?" sorusunun cevabı: numara ("1", "ikinci", "1 ve 2"), "ikisi de"/"hepsi", "hiçbiri", eski ölçü ("120x100") ya da
    duvar ("soldaki"). Döner: seçeneklerin sırası (0'dan), "hicbiri" ya da None (cevap değil)."""
    if not metin or not secenekler:
        return None
    c = CO.okuma_cevabi(metin, {"tur": "secim", "adaylar": secenekler})
    soz = CO.norm(metin).split()
    if len(secenekler) == 1:
        # "İkisini de … yapalım mı?": düğme ("1", "hiçbiri"), olumsuz cevap ya da yalın onay ("evet", "ikisi de", "olur"). Sayı
        # ayrıştırması yok: "bir tane", "ilki" tek pencere ister, onay değildir (hakem üçüncü tur 1)
        if c is not None and c.get("hicbiri"):
            return "hicbiri"
        if soz == ["1"] or (soz and set(soz) <= _ONAY_SOZ and set(soz) & _ONAY_OLUMLU):
            return [0]
        return None
    if c is not None and (c.get("hicbiri") or c.get("secimler")):
        return "hicbiri" if c.get("hicbiri") else list(c["secimler"])
    if len(metin.split()) > 6:
        return None
    olc = _olculer_metin(metin)
    if olc and not set(olc) <= {g["olcu"] for g in secenekler}:
        return None                                   # yeni ölçü taşıyan cevap yeni istektir
    duvarlar = _duvarlar_metin(metin)
    if not olc and not duvarlar:
        return None
    kalan = [i for i, g in enumerate(secenekler) if (not olc or g["olcu"] in olc) and (not duvarlar or g["duvar"] in duvarlar)]
    return kalan if len(kalan) == 1 else None


def _oda_sorusu(k: Konusma, ie: dict, soru: str, hedef: dict, eslesen: list[str] | None = None) -> Karar:
    """"Hangi odanın penceresi?" sorusu; seçenekler pencereli odalar (bayinin sözü birkaç odaya uyuyorsa yalnız onlar), her odaya bir
    düğme (3'ten çoksa liste; q:pencere_mahal:<n>). hedef: cevabın yazılacağı bekleyen istek (varyant ya da pencere satırı)."""
    odalar = [m["ad"] for m in ie["mahaller"] if any(a.get("mahal") == m["ad"] for a in ie["acikliklar"] if a["tur"] == "pencere")]
    if eslesen and len(eslesen) > 1:
        odalar = [o for o in odalar if o in eslesen] or odalar
    metin = f"{soru} Seçenekler: {', '.join(odalar)}."
    butonlar = [{"id": f"q:pencere_mahal:{i}", "baslik": ad[:20]} for i, ad in enumerate(odalar[:10], 1)]
    k.d["pencere_mahal_sorusu"] = {"odalar": odalar[:10], "hedef": hedef, "metin": metin, "butonlar": butonlar}
    return _soru(k, "pencere_mahal", metin, butonlar)


def _oda_cevabi(metin: str | None, odalar: list[str]) -> str | None:
    """Oda sorusunun kısa cevabı: düğme ("seçenek 2") ya da oda adı ("Oda 1", "ODA 1", "salon"). Yalnız numara yazılırsa oda adındaki
    numarayla karışır ("2" → "ODA 2" mi ikinci seçenek mi?): cevap sayılmaz, soru yinelenir (K21)."""
    if not metin or not odalar or len(metin.split()) > 4 or _olcu_bul(metin):
        return None
    m = re.fullmatch(r"\s*se[cç]enek\s+(\d{1,2})\s*", metin, re.IGNORECASE)
    if m:
        i = int(m.group(1))
        return odalar[i - 1] if 1 <= i <= len(odalar) else None
    q = varyant._norm(metin)
    if not q or q.isdigit():
        return None
    tam = [o for o in odalar if varyant._norm(o) == q]
    if len(tam) == 1:
        return tam[0]
    icinde = [o for o in odalar if varyant._norm(o) and varyant._norm(o) in q]
    if icinde:
        en_uzun = max(len(varyant._norm(o)) for o in icinde)
        aday = [o for o in icinde if len(varyant._norm(o)) == en_uzun]
        return aday[0] if len(aday) == 1 else None
    kapsayan = [o for o in odalar if q in varyant._norm(o)]
    return kapsayan[0] if len(kapsayan) == 1 else None


def _pencere_odasi_yaz(ts: dict, hedef: dict, ad: str) -> bool:
    """Oda sorusunun cevabını bekleyen isteğe yazar (pencere varyantının odası ya da pencere satırının odası)."""
    if hedef.get("tur") == "varyant":
        for v in ts.get("varyantlar") or []:
            if v.get("tur") == "pencere_degistir" and (v.get("aciklama") or "") == (hedef.get("aciklama") or ""):
                v["parametreler"] = {**(v.get("parametreler") or {}), "mahal": ad}
                return True
    elif hedef.get("tur") == "satir":
        for p in ts.get("pencereler") or []:
            if list(_pencere_anahtari(p)) == hedef.get("anahtar") and p.get("pencere_sira") is None:
                p["mahal"] = ad
                return True
    return False


_PENCERE_SOZU = re.compile(r"\b(pencere\w*|cam|cami|camin\w*|camlar\w*|vasistas\w*)\b")   # "çamaşır" değil


def _pencere_kopyalarini_dusur(k: Konusma, olculer: set[str] | None = None) -> None:
    """"Hangi pencere?" sorusuna "hiçbiri" (BK-29 tur 4; tur 3 canlı gözlem 2): LLM pencere isteğini serbest istek ya da pafta alanı olarak
    da yazabiliyor ("Mutfak penceresi 120x120 olsun"). Planı üreten taslakta olmayan ve pencereyi anan bu kopyalar da düşer; kalınca plan
    "değişti" sayılıyor, aynı plan yeni revizyon numarasıyla çiziliyordu (revizyon hakkı harcanıyordu). Mesajın başka değişikliği kalır.
    Tur 5 (tur 4 canlı A18): "pencere" sözü olmayan kopya da pencereyi anar: cam, vasistas ya da reddedilen ölçü ("Salon: 120x180")."""
    ts, pt = k.d["taslak"], k.d.get("plan_taslagi")
    if not isinstance(pt, dict):
        return
    olculer = set(olculer or ())

    def pencereyi_anar(x: str) -> bool:
        return bool(_PENCERE_SOZU.search(CO.norm(x)) or olculer & set(_olculer_metin(x)))

    eski = pt.get("ozel_istekler") or []
    ts["ozel_istekler"] = [x for x in ts.get("ozel_istekler") or [] if x in eski or not pencereyi_anar(str(x))]
    eski_bo = pt.get("bina_ozellikleri") or {}
    ts["bina_ozellikleri"] = {a: b for a, b in (ts.get("bina_ozellikleri") or {}).items()
                              if eski_bo.get(a) == b or not pencereyi_anar(f"{a} {b}")}


def _bekleyen_olcuyu_yaz(ts: dict, olcu: str) -> bool:
    """Ölçü sorusunun cevabını ölçüsü olmayan bekleyen pencere isteğine yazar (pencere satırı ya da "pencere_degistir" varyantı)."""
    yazildi = False
    for p in ts.get("pencereler") or []:
        if not p.get("olcu") and p.get("pencere_sira") is None and p.get("islem") in (None, "degistir"):
            p["olcu"] = olcu; yazildi = True
    for v in ts.get("varyantlar") or []:
        prm = v.get("parametreler") or {}
        if v.get("tur") == "pencere_degistir" and not (prm.get("yeni") or prm.get("olcu") or prm.get("yeni_olcu") or _olcu_bul(v.get("aciklama") or "")):
            v["parametreler"] = {**prm, "yeni": olcu}; yazildi = True
    return yazildi


def _plan_ozu(ie: dict) -> str:
    """Planın bayinin gördüğü içeriği (numara, tarih, varsayım notları ve talep metni hariç): aynıysa plan değişmemiştir."""
    o = {a: b for a, b in ie.items() if a not in ("is_emri_no", "revizyon", "talep", "kunye", "varsayimlar")}
    o["_musteri"] = (ie.get("talep") or {}).get("musteri_adi") or ""
    o["_sevk"] = (ie.get("kunye") or {}).get("sevk_adresi") or ""
    return json.dumps(o, sort_keys=True, ensure_ascii=False)


def _cati_disi_ozu(ie: dict) -> str:
    """İE-42: planın çatısı dışındaki içeriği (çatı ve çatının adını taşıyan referans model hariç): aynıysa yalnız çatı değişmiştir."""
    o = json.loads(json.dumps(ie))
    o.pop("cati", None)
    (o.get("yapi") or {}).pop("referans_model", None)
    return _plan_ozu(o)


ACIK_PLAN_ASAMALARI = ("onay_bekliyor", "revizyon", "topluyor", "onaylandi")


def _plan_durumu_cevabi(k: Konusma) -> str:
    """BK-29 tur 6 (pano 212; kabul seti C7): fiyat, süre ya da teklif sorusuna cevap bayinin planını bilir. Onaylı plan: teklifi
    PortatifEv hazırlıyor (çelikte plan önce teknik kontrolde). Onay bekleyen plan: teklif onaydan sonra. Planı olmayan bayiye
    bugünkü genel cevap gider (boş dize)."""
    ie = k.d.get("son_is_emri") or {}
    no = ie.get("is_emri_no")
    if not no:
        return ""
    etiket = f"{no} r{int(ie.get('revizyon') or 1):02d}"
    celik = (ie.get("yapi") or {}).get("sistem") == "celik"
    if k.d.get("asama") == "onaylandi":
        if celik:
            return (f"Onayladığınız plan ({etiket}) teknik kontrolde. Kontrol bitince teklifi PortatifEv hazırlar ve bu sohbete gönderir. "
                    "Fiyat ve teslim süresi teklifte yazar.")
        return (f"Onayladığınız plan ({etiket}) için teklifi PortatifEv hazırlıyor. Teklif bu sohbete gönderilir. "
                "Fiyat ve teslim süresi teklifte yazar.")
    if k.d.get("asama") == "onay_bekliyor" and k.d.get("cati_adimi"):        # İE-42: plan onaylandı, çatı bekleniyor
        return (f"Planınız ({etiket}) onaylandı; çatı seçiminizi bekliyor. "
                + ("Çatı seçilince plan teknik kontrole gider. " if celik else "Teklifi PortatifEv, çatı seçildikten sonra hazırlar. ")
                + "Fiyat ve teslim süresi teklifte yazar.")
    if k.d.get("asama") == "onay_bekliyor":
        return (f"Planınız ({etiket}) onayınızı bekliyor. Teklifi PortatifEv, planı onayladıktan sonra hazırlar. "
                "Fiyat ve teslim süresi teklifte yazar.")
    return ""


def _plani_acik_tut(k: Konusma, d0: dict, karar: Karar, cati_secimi: str | None = None) -> None:
    """BK-29 (pano 200; 13 Kasım 2026 WhatsApp denetimi): açık bir planın üstüne gelen istek geri çevrilince (yönlendirme) plan ölmez.
    Konuşma bu mesajdan önceki hâline döner (taslak, revizyon sayacı, plan); askıdaki soru, saklanan istek ve açık set kapanır, soru hakkı
    yenilenir. Plan onay bekliyorsa yine onay bekler (Onayla düğmesi ve "onaylıyorum" çalışır), onaylıysa onaylı kalır. Bayiye planın
    durduğu söylenir; Patron'a bildirim bugünkü gibi gider (eylem değişmez). Konuşma bu mesajda sıfırlandıysa (yeni talep, başka model)
    ya da plan zaten yoksa bugünkü yol: taslak kapanır. İE-42: onaydan sonraki çatı seti açıkken istek geri çevrildiyse set kapanır, plan
    onay bekler ("Onayla" seti yeniden getirir); aynı mesajda çatı seçildiyse (`cati_secimi`; hakem tur 1, bulgu 6) set açık kalır, bayiye
    seçimin kaydedilmediği yazılır ve setin düğmeleri yeniden gider (çatı seçimi sessizce düşmez)."""
    ie0 = d0.get("son_is_emri") or {}
    ie = k.d.get("son_is_emri") or {}
    no, rev = ie0.get("is_emri_no"), int(ie0.get("revizyon") or 1)
    if not no or d0.get("asama") not in ACIK_PLAN_ASAMALARI or (ie.get("is_emri_no"), ie.get("revizyon")) != (no, ie0.get("revizyon")):
        return
    gecmis = k.d.get("gecmis") or []
    k.d = json.loads(json.dumps(d0))
    k.d["gecmis"] = gecmis
    if isinstance(d0.get("plan_taslagi"), dict):
        k.d["taslak"] = json.loads(json.dumps(d0["plan_taslagi"]))   # askıdaki sorunun isteği (ör. odası sorulan pencere) taslakta kalmaz
    onayli = k.d.get("onaylanan") == [no, rev]
    st0 = k.d.get("secenek_seti") or {}
    cati_acik = bool(cati_secimi and k.d.get("cati_adimi") and st0.get("durum") == "acik" and st0.get("tur") == "cati_varyanti")
    if not cati_acik and k.d.pop("cati_adimi", None):  # İE-42: onaydan sonraki çatı seti kapanır; plan onay bekler (Onayla seti yeniden getirir)
        onayli = False
    k.d["asama"] = "onaylandi" if onayli else "onay_bekliyor"
    k.d["bekleyen_onay"] = no
    k.d["son_soru_alani"] = "secenek" if cati_acik else None
    k.d["soru_sayisi"] = 0
    for a in ("okuma_bekleyen", "okuma_secilen", "okuma_hicbiri", "celik_istek", "pencere_islem_satiri", "pencere_islem_sorusu",
              "eski_taslak_soru", "bekleyen_talep", "bekleyen_metin", "bekleyen_zamani", "pencere_mahal_sorusu", "pencere_secim"):
        k.d.pop(a, None)
    st = k.d.get("secenek_seti")
    if st and st.get("durum") == "acik" and not cati_acik:
        st["durum"] = "dustu"
    etiket = f"{no} r{rev:02d}"
    zaten = f"; {getattr(k, 'degismedi_notu', '')}" if getattr(k, "degismedi_notu", "") else ""     # D-86
    if cati_acik:
        a = next((x for x in st0.get("adaylar") or [] if str(x.get("kod")).upper() == str(cati_secimi).upper()), None)
        uygulanmadi = ""                               # hakem tur 2, Y1: Motor'un uygulamadığı istek (yükseklik, kapı, veranda) sessiz düşmez
        if karar.gerekce == PLAN_DEGISMEDI:
            uygulanmadi = "; öteki isteğinizi plana uygulayamadım" if zaten else "; isteğinizi plana uygulayamadım"
        cumle = (f"Planınız ({etiket}) değişmedi{zaten}{uygulanmadi}. Çatı seçiminizi ({SC.gosterim(a) if a else cati_secimi}) "
                 "kaydetmedim; çatıyı yeniden seçin.")
        karar.butonlar = [{"id": f"s:{st0['id']}:{x['kod']}", "baslik": f"{x['sira']}. {SC.gosterim(x)}"[:20]}
                          for x in sorted(st0.get("adaylar") or [], key=lambda x: x.get("sira") or 0)[:SC.EN_COK_GORSEL]]
    elif onayli:
        cumle = f"Onaylı planınız ({etiket}) değişmedi{zaten}."
    elif karar.gerekce == "revizyon sınırı":
        cumle = f"Planınız ({etiket}) değişmedi; onaylayabilirsiniz."
        karar.butonlar = [{"id": f"o:{no}:{rev}", "baslik": "Onayla"}]
    else:
        uyg = ""                                       # İE-42 (hakem tur 4): çatı setini kapatan istek planı değiştirmedi; bayiye yazılır
        if karar.gerekce == PLAN_DEGISMEDI and getattr(k, "cati_icerik", None) and not getattr(k, "degismedi_tam", False):
            uyg = "; öteki isteğinizi plana uygulayamadım" if zaten else "; isteğinizi plana uygulayamadım"
        cumle = f"Planınız ({etiket}) değişmedi{zaten}{uyg}. Onaylayabilir ya da başka bir değişiklik yazabilirsiniz."
        karar.butonlar = [{"id": f"o:{no}:{rev}", "baslik": "Onayla"}, {"id": f"r:{no}:{rev}", "baslik": "Revize et"}]
    karar.mesaj = f"{karar.mesaj} {cumle}".strip()
    neden = "plan değişmedi" if karar.gerekce == PLAN_DEGISMEDI else "istek geri çevrildi"
    k.not_dus("kural", f"BK-29: {neden}; plan {etiket} açık kaldı ({k.d['asama']})")
    k.kaydet()


def _bitir(k: Konusma, karar: Karar) -> Karar:
    if karar.eylem in ("is_emri", "yonlendir"):
        k.d["son_soru_alani"] = None                  # plan çıktı ya da insana devredildi: askıda soru kalmaz
        k.d.pop("celik_istek", None)                  # İE-08 A4: set sunulurken saklanan çelik isteği planla tüketildi ya da insana devredildi
    st = k.d.get("secenek_seti")
    if st and st.get("durum") == "acik" and karar.eylem == "yonlendir":
        st["durum"] = "dustu"                         # insana devredildi: açık set seçim yapmaz
    if k.d.get("son_soru_alani") != ESKI_TASLAK_SORUSU:
        k.d.pop("eski_taslak_soru", None)             # D-01 sorusu askıda değilse sayaç da kalmaz
    if k.d.get("son_soru_alani") != "pencere_islem":
        k.d.pop("pencere_islem_satiri", None)         # B1: sorulan pencere satırı yalnız soru askıdayken tutulur
        k.d.pop("pencere_islem_sorusu", None)
    if k.d.get("son_soru_alani") not in ("okuma", "okuma_olcu"):
        k.d.pop("okuma_bekleyen", None)               # PR-2b: okuma adayları yalnız soru askıdayken tutulur
        k.d.pop("okuma_secilen", None)
    if k.d.get("son_soru_alani") != "pencere_mahal":
        k.d.pop("pencere_mahal_sorusu", None)         # BK-29 PR-2: oda ve pencere sorularının seçenekleri yalnız soru askıdayken
    if k.d.get("son_soru_alani") != "pencere_secim":
        k.d.pop("pencere_secim", None)
    if karar.eylem == "is_emri":
        onayli = k.d.pop("onaylanan", None)            # BK-29 tur 6 (pano 212, C8): onaylı planın üstüne yeni revizyon geldi; onay düşer, bayiye söylenir
        dusen = k.d.pop("cati_onayi_dustu", None)      # İE-42: "Planınız onaylandı" denmişti, çatı seti açıkken plan değişti
        yeni_rev = int((karar.is_emri or {}).get("revizyon") or 1)
        onceki = int(onayli[1]) if onayli else (int(dusen) if dusen else None)
        if onceki and yeni_rev > 1 and onceki < yeni_rev:
            karar.mesaj = (f"{karar.mesaj} Bu değişiklik r{onceki:02d} onayınızı geçersiz kıldı. "
                           f"r{yeni_rev:02d} için yeniden onay gerekir.").strip()
        k.d["bekleyen_onay"] = karar.is_emri.get("is_emri_no") if karar.is_emri else None
        k.d["asama"] = "onay_bekliyor"
        k.d["soru_sayisi"] = 0      # BK-29: soru hakkı (MAX_SORU) her planda yenilenir; prefabrikte talebin soruları revizyonda tükeniyordu
        k.d["plan_taslagi"] = json.loads(json.dumps(k.d.get("taslak") or {}))   # BK-29: planı üreten taslak; geri çevrilen istekten sonra buna dönülür
    elif karar.eylem == "yonlendir":
        k.d["asama"] = "yonlendirildi"; k.d["taslak"] = {}; k.d["soru_sayisi"] = 0   # insana devredildi; taslak kapanır
    rev0 = getattr(k, "rev0", None)
    if karar.eylem != "is_emri" and rev0 is not None and int(k.d.get("revizyon") or 0) > rev0:
        k.d["revizyon"] = rev0      # G-2 (29.09): soru soran ya da yönlendiren revizyon turu revizyon numarası tüketmez
    k.not_dus("giden", karar.mesaj, {"eylem": karar.eylem, "gerekce": karar.gerekce})
    k.kaydet()
    return karar
