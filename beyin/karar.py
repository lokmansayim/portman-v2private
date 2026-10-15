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
from . import secenek as SC
from . import numara                     # BK-08 madde 9: gerekçedeki serbest metin maskelenir
from . import celik                      # İE-08: çelik aday zarfı, D-09 antet bilgisi
from . import celik_okuma as CO          # İE-08 PR-2b: çelik revizyonunda bayinin sözünden pencere / çatı / dış 140 okuması (K18)

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
    k.son_llm = None                                # İE-08 A4: bu mesajın LLM ipuçları (yalnız bu çağrıda; `_karar_ver` doldurur)
    k.rev0 = int(k.d.get("revizyon") or 0)          # G-2: _bitir, plan üretmeyen turda sayacı buna geri alır
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
            return _soru(k, "okuma_metin", "Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120\"); "
                                           "çatı için \"çatı K\" ya da \"çatı L\", dış duvar için \"dışlar 140'lık olsun\" yazabilirsiniz." + ek)
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
    # cevaba verdiği içerik yok sayılır. Prefabrik setler değişmez (A5).
    if k.d.get("son_soru_alani") == "secenek" and _celik_seti_acik(k):
        st = k.d["secenek_seti"]
        no = CO.okuma_cevabi(metin, {"tur": "secim", "adaylar": st.get("adaylar") or []})
        if no and len(no.get("secimler") or []) == 1:
            kod = next((a.get("kod") for a in st.get("adaylar") or [] if a.get("sira") == no["secimler"][0] + 1), None)
            if kod:
                k.not_dus("kural", f"seçenek setine yazılı numara: {no['secimler'][0] + 1} → {kod}")
                metin = f"{kod} olsun"
                t = Talep(niyet="yeni_talep", guven=t.guven, ozet=f"{kod} seçildi", katalog_kodu=kod)

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

    # 1) niyete göre
    if t.niyet == "selam":
        return _bitir(k, Karar(eylem="cevapla", gerekce="selam",
                                mesaj=f"Merhaba{(' ' + hitap) if hitap else ''}. Hangi model ya da ölçü için ön onay planı hazırlayalım? Örnek: \"P6001 aynalı\" veya \"7x4 m, 2+1, ön verandalı\"."))
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
            k.d["son_soru_alani"] = None                       # askıdaki yeni plan sorusu onayla kapanır (soru kaydı açık kalmaz)
            rev = k.d["son_is_emri"].get("revizyon", k.d["revizyon"] + 1)   # gönderilen planın numarası (r01 = 1)
            # İE-08 8b (plan kararı 6, Lokman 14.10): çelik plan onaydan sonra mühendisin teknik kontrolüne gider (kanal/muhendis.py)
            sonraki = ("Plan teknik kontrole gönderildi; sonucu size bildireceğiz." if (k.d["son_is_emri"].get("yapi") or {}).get("sistem") == "celik"
                       else "Teklif aşamasına geçiliyor.")
            return _bitir(k, Karar(eylem="cevapla", gerekce="plan onaylandı", revizyon=rev,
                                    mesaj=f"Onayınız kaydedildi ({k.d['son_is_emri'].get('is_emri_no')}, revizyon {rev}). {sonraki}"))
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
            and not baska_model and _eski_taslak(k) and _model_koduyla_basliyor(metin, katalog):
        return _eski_taslak_sor(k, t, metin)
    k.d.pop("eski_taslak_soru", None)
    if t.niyet == "revizyon" and k.d.get("son_is_emri"):
        k.d["revizyon"] += 1
        if k.d["revizyon"] > MAX_REVIZYON:
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
        k.d["taslak"].pop("pencereler", None); k.d["son_soru_alani"] = None
        dusen_not = "Önceki pencere değişikliğini netleştirmediğiniz için uygulamadım; isterseniz sonra ekleriz. "
    t = _pencere_varyantlarina_soz_isle(t, metin)    # G-3/G-4 (29.09): pencere değişikliği tek yoldan, B1 kurallarıyla
    k.birlestir(t.model_dump())
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
        ts["pencereler"] = [p for p in ts.get("pencereler") or []
                            if _pencere_anahtari(p) in yeni_anahtarlar or varyant._norm(_pencere_anahtari(p)[0]) not in yeni_mahaller]
        for p in ts["pencereler"]:
            if _pencere_anahtari(p) in yeni_anahtarlar and p.get("islem_kaynak") != "bayi cevabı":
                p["soz_niyeti"] = _pencere_soz_niyeti(metin, p.get("mahal"), p.get("olcu"))
    if dusen_not:
        ts["_on_not"] = dusen_not

    # 2a) katalog modeli ya da aday (İE-04: aday kaydındaki şablon; seçim açık seçenek setini kapatır)
    if ts.get("katalog_kodu"):
        aday = _aday_bul(k, katalog, ts["katalog_kodu"])          # İE-14: üretilen plan ("YENI-…") konuşmadaki kayıttan
        model = katalog.bul(ts["katalog_kodu"])
        if aday is None and model is None:
            return _soru(k, "katalog_kodu", f"Katalogda \"{ts['katalog_kodu']}\" kodlu model bulamadım. Kodu kontrol eder misiniz? (örn. P6001, P7401, Ç8201)")
        if aday is not None and aday.get("motor") == "genel":      # İE-08 A2/A3: çelik aday (genel motor): çatı seçenekleri ya da r01
            return _celik_dali(k, bayi, katalog, aday, ts)
        kod = aday["kod"] if aday else model["code"]
        yol = katalog.sablon_yolu(kod)
        if yol is None:
            return _bitir(k, Karar(eylem="yonlendir", gerekce="şablon kodlanmamış",
                                    mesaj=f"{Katalog.kisa(model) if model else kod} katalogda kayıtlı; çizim şablonu sisteme henüz işlenmedi. " + YONLENDIRME))
        _seti_kapat(k, kod)
        return _is_emri_uret(k, bayi, katalog, json.loads(yol.read_text(encoding="utf-8")), kod, ts)

    # 2b) serbest talep — zorunlu: oda programı + (dış ölçü | pano | alan)
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


def _celik_dali(k: Konusma, bayi: dict, katalog: Katalog, aday: dict, ts: dict) -> Karar:
    """İE-08 A2/A3 · çelik aday (genel motor). Açık seçenek setinden seçim ya da bayinin metninde çatı seçimi → r01; katalog modelinin
    çatı varyantları varsa ve çatı seçilmemişse numaralı çatı seti (katalog çatısı, K, L; tek görsel, 3 düğme; öncelik sorusu yok)."""
    st = k.d.get("secenek_seti")
    kod = str(aday["kod"]).upper()
    metin = k.d.get("son_metin")
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
            k.d["taslak"]["katalog_kodu"] = secilen["kod"]
            _seti_kapat(k, secilen["kod"])
            return _celik_is_emri_uret(k, bayi, katalog, secilen, ts)
    if not hedef and kat_aday.get("varyantlar") and (aday.get("varyantlar") or (kararsiz and not ayni)):
        varyantlar = [katalog.aday(v) for v in kat_aday["varyantlar"]]
        uygun = [kat_aday] + [v for v in varyantlar if v is not None]
        if len(uygun) >= 2:
            saklandi = _celik_istek_sakla(k)
            return _secenekler(k, katalog, ts, uygun=SC.cati_seti(uygun), tur="cati_varyanti", referans=kat_aday,
                               ek_not=CELIK_ISTEK_NOTU if saklandi else "")
    _seti_kapat(k, kod)
    return _celik_is_emri_uret(k, bayi, katalog, aday, ts)


CELIK_ISTEK_NOTU = "Mesajınızdaki değişiklik isteğini seçtiğiniz plana işleyeceğim."


def _aday_mahalleri(aday: dict) -> list[dict]:
    """Çelik adayın oda adları (cümle bölme oda adlarını tanısın); tanım okunamazsa boş (zarf aşaması tanımı ayrıca doğrular)."""
    try:
        return list(celik.tanim_oku(aday).get("mahaller") or [])
    except (KeyError, OSError, ValueError):
        return []


# ── İE-14 · talepten plana (D-18) ─────────────────────────────────────────────────────────────────────────────────────
PLAN_URETIMI = "plan üretimi: uyan çelik model yok"
YENI_ONEK = "YENI-"


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
    satirlar = [f"{y['sira']}. {y['gosterim']} · {y['katalog_m2']:g} m² · {y['oda_programi']} · TASLAK, {YOL_ADI.get(y.get('yol'), 'yeni')}"
                + "".join(f" ({d})" for d in (uretilen[i].get("degisen") or [])[:2]) for i, y in enumerate(uygun[:len(yeniler)])]
    satirlar += [f"{a['sira']}. {SC.gosterim(a)} · {a['katalog_m2']:g} m² · {a.get('oda_programi') or ''} (bankadan en yakın)" for a in uygun[len(yeniler):]]
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
    mesaj = (f"{alan:g} m² {talep.get('oda_programi')} çelik için {bas} çizdim; bankadaki en yakın model de yanında. Mühendis kontrolü "
             f"onayınızdan sonra.\n\n" + "\n".join(satirlar) + not_)[:1024 - len(son)] + son
    butonlar = [{"id": f"s:{st['id']}:{a['kod']}", "baslik": (f"{a['sira']}. {a['gosterim']}" if a.get("uretilen") else f"{a['sira']}. {SC.gosterim(a)}")[:20]}
                for a in uygun[:SC.EN_COK_GORSEL]]
    k.not_dus("kural", f"yeni plan üretildi: {', '.join(y['kod'] for y in yeniler)} ({sonuc.get('yol') or 'yeni'})")
    return _bitir(k, Karar(eylem="secenek", soru_alani="secenek", mesaj=mesaj, secenek_seti=st, butonlar=butonlar,
                           gerekce=f"seçenek seti {st['id']}: yeni plan {' + '.join(y['kod'] for y in yeniler)} + bankadan {len(banka)}"))


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


def _yeni_plan_sorusu(k: Konusma, metin: str) -> Karar:
    """Yeni plan revizyonunda soru: soru bütçesi işler, okuma alanı bırakılmaz ve plan bayide kalır (aşama `onay_bekliyor`): sonraki
    cevap yine LLM düzenleyicisine gider, bayi doğrudan onaylayabilir (ikinci tur bulgu 1)."""
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = "yeni_plan_degisiklik"
    k.d["asama"] = "onay_bekliyor"
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani="yeni_plan_degisiklik", mesaj=metin, gerekce="yeni plan: değişiklik okunmadı"))


def _celik_degisiklikler(k: Konusma, katalog: Katalog, aday: dict, t: dict, onceki: list[dict], ayni_proje: bool) -> tuple[list[dict], set[str]] | Karar:
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
            return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelikte varyant henüz desteklenmiyor: {tur}",
                                    mesaj=f"\"{v.get('aciklama', '')}\" değişikliği çelik modelde otomatik yapılamıyor"
                                          + ("; çatı için katalog çatısı, K ya da L seçilebilir. " if kat_aday.get("varyantlar") else ". ") + YONLENDIRME))
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelikte varyant henüz desteklenmiyor: {tur}",
                                mesaj=f"\"{v.get('aciklama', '')}\" değişikliği çelik modelde henüz otomatik yapılamıyor. " + YONLENDIRME))
    # 2) revizyonda tanınmayan içerik: bina özelliği (renk, malzeme) değilse yönlendirme (K21: yanlış uygulanmaz, sessizce düşmez)
    if ayni_proje:
        baska = [p["metin"] for p in r["parcalar"] if p["tur"] == "baska" and not _bilgi_cumlesi(p, llm)]
        if baska:
            # gerekçe günlüğe yazılır (vps/agent.py): bayinin cümlesi yalnız bayiye giden mesajda (mesaj metni günlüğe yazılmaz)
            return _bitir(k, Karar(eylem="yonlendir", gerekce="çelik revizyonunda otomatik yapılamayan istek (cümle bayiye söylendi)",
                                    mesaj=f"\"{_kisalt(baska[0].strip(' ,.;'))}\" isteği çelik modelde otomatik yapılamıyor (otomatik yapabildiklerim: "
                                          "pencere ölçüsü, çatı katalog/K/L, dış duvarlar 140'lık). " + YONLENDIRME))
    # 3) pencere ekleme ya da kaldırma: 8a'da yalnız ölçü (ölçü yazılmış olsa da mevcut pencere değiştirilmez)
    if r["ekle_kaldir"]:
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
        return _soru(k, "okuma_metin", "Anlayamadım. " + _NEYI_DEGISTIRELIM)
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
    d = DO.denetle(lo, pencereler, _cati_kodlari(katalog, aday))
    k.not_dus("kural", f"LLM-önce okuma: {len(d['ops'])} işlem, {len(d['uygulanamaz'])} uygulanamaz" + (", soru" if d["sor"] else ""))
    if d["uygulanamaz"]:
        alinti = "; ".join(f"\"{numara.maskele(x)[:80]}\"" for x in d["uygulanamaz"][:3])
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"LLM-önce okuma: {len(d['uygulanamaz'])} istek otomatik uygulanamıyor",
                                mesaj=f"{alinti} isteğini otomatik uygulayamadım. Otomatik yapabildiklerim: pencere ölçüsü, çatı seçeneği, dış duvarlar "
                                      "140'lık karkas. " + YONLENDIRME))
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
    t = celik.tanim_oku(aday)
    try:
        for d in onceki:
            t = varyant.tanim_uygula(t, d)
    except varyant.VaryantHatasi as e:
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"önceki değişiklikler yeni tanıma uygulanamadı: {e}",
                                mesaj=f"Önceki değişiklikleriniz bu modele taşınamadı ({e}). " + YONLENDIRME))
    ly = getattr(k, "llm_yeni_plan", None)
    bilgi = bool((getattr(k, "son_llm", None) or {}).get("bilgi"))
    kod_metni = ""                                              # yeni plan + bilgi: istek notu (mesajın başı ve PDF başlığı; LLM özeti değil)
    if aday.get("uretilen") and ayni_proje and ly is not None:  # İE-14 PR-3 (T3): yeni planın revizyonu LLM'in yeniden planıyla
        # plan değişmedi (inceleme C2 ve ikinci tur): konuşma kapanmaz. Soru, sonraki cevap yine LLM düzenleyicisine gitsin diye
        # okuma alanı bırakmaz ("okuma_metin" LLM-önce yolu kapatıp cevabı kural yoluna, oradan Patron'a düşürüyordu). Aynı mesajda
        # bilgi (müşteri, antet) varsa soru yerine plan antetle yeniden çizilir, not başa yazılır: bilgi sessiz düşmez (geometri hakemi 15.10)
        if ly.get("durum") == "uygulanamadi":                  # Lokman 15.10 (karar 3): "otomatik uygulayamadım", plan aynen ve onaylanabilir
            olmayan = "; ".join(f"\"{numara.maskele(str(x))[:80]}\"" for x in (ly.get("uygulanamayan") or [])[:3])
            k.not_dus("kural", "yeni plan revizyonu: istek uygulanamadı, plan aynen")
            if not bilgi:
                return _yeni_plan_sorusu(k, f"{olmayan} isteğini otomatik uygulayamadım; planınız aynen geçerli. " + _BASKA_DEGISIKLIK)
            kod_metni = f"{olmayan} isteğini otomatik uygulayamadım; bilgileriniz plana işlendi."
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
        sonuc = _celik_degisiklikler(k, katalog, aday, t, onceki, ayni_proje)
    if isinstance(sonuc, Karar):
        return sonuc
    yeni, okunan = sonuc
    tekil: dict[str, dict] = {}
    for d in yeni:                                             # aynı pencereye iki değişiklik (saklanan istek + seçim mesajı): sonuncusu geçerli
        tekil[f"{d.get('op')}:{d.get('aciklik') or ''}"] = d
    yeni = list(tekil.values())
    if ayni_proje and str(son_y.get("kod")).upper() != str(aday["kod"]).upper():          # çatı varyantı değişti: zarf tanım dosyasını değiştirir
        yeni.append({"op": "cati_varyanti", "kod": aday["kod"], "aciklama": f"çatı {aday.get('gosterim') or aday['kod']}"}); okunan.add("cati")
    if ayni_proje and not yeni and not bilgi:
        if "dis140" in okunan and _zaten_140(t, onceki):      # KT-03 gibi hazır 140'lık modelde aynı öneriyle geri sorulmaz (ikinci tur)
            kr = _soru(k, "okuma_metin", "Bu planda dış duvarlar zaten 140'lık karkas. " + _BASKA_DEGISIKLIK)
            if kr.eylem == "sor":
                k.d["asama"] = "onay_bekliyor"                 # plan değişmedi, bayide: mesajın dediği gibi Onayla çalışır (dördüncü tur)
            return kr
        return _soru(k, "okuma_metin", _NEYI_DEGISTIRELIM)   # aynı plan yeniden çizilip revizyon hakkı harcanmaz
    try:
        for d in yeni:
            t = varyant.tanim_uygula(t, d)
    except varyant.VaryantHatasi as e:
        k.not_dus("kural", f"değişiklik uygulanamadı: {e}")
        return _bitir(k, Karar(eylem="yonlendir", gerekce=f"çelik değişikliği uygulanamadı: {e}",
                                mesaj=f"Bu değişiklik otomatik uygulanamadı ({e}). " + YONLENDIRME))
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
    on_bilgi = f"{celik.kaynak_notu(aday)}" + (f" · {aday.get('katalog_m2'):g} m², {aday.get('oda_programi')}" if isinstance(aday.get("katalog_m2"), (int, float)) else "") + ". "
    uyg = ("Uygulanan: " + "; ".join(CO.aciklama(d) for d in yeni) + ". ") if yeni else ""
    if yeni:                                                   # BK-09 M1: kod değişiklik uyguladıysa LLM özeti yazılmaz (K18); özetin
        ozet = ""                                              # "teyit etmemiz gerekiyor" sorusu "Uygulanan"la çelişiyordu (14.10 canlı)
        ie["talep"]["metin"] = uyg.strip()                     # PDF açıklaması da kodun okuması (`worker`, `ozet_baslik`)
    elif kod_metni:                                            # bilgi + uygulanamayan/zaten olan istek: LLM özeti isteği taşır ("çatı L tipi
        ozet = kod_metni                                       # olsun"), plan değişmedi (geometri hakemi ikinci tur, K18): mesaj ve PDF
        ie["talep"]["metin"] = kod_metni                       # başlığı kodun metni
        ie["talep"]["metin_koddan"] = True
    gerekce = f"çelik aday {aday['kod']} (genel motor)" + (f"; değişiklik: {', '.join(d['op'] for d in yeni)}" if yeni else "")
    # BK-08 madde 4: çelik planda görsel ve PDF bu metinle birlikte gider (çizim düşerse bu metin gitmez, `worker._cizim_hatasi`)
    return _bitir(k, Karar(eylem="is_emri", is_emri=ie, revizyon=ie["revizyon"], gerekce=gerekce,
                            mesaj=f"{on_not}{on_bilgi}{ozet} {uyg}Ön onay planınız hazır; plan görseli ve PDF ektedir.".replace("  ", " ")))


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
    guncel = {**aday, "tanim": yeni_t, "tanim_sha256": celik.tanim_sha_icerik(yeni_t), "plan": ly.get("plan"), "katalog_m2": oz.get("brut_m2"),
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
    olmayan = [numara.maskele(str(x))[:80] for x in ly.get("uygulanamayan") or []]
    not_ = ("; ".join(f"\"{x}\"" for x in olmayan) + " isteğini otomatik uygulayamadım. ") if olmayan else ""
    k.d["revizyon"] = ie["revizyon"] - 1
    k.d["son_is_emri"] = ie
    k.d["asama"] = "is_emri_hazir"
    k.d["soru_sayisi"] = 0
    on_bilgi = f"{celik.kaynak_notu(guncel)}" + (f" · {guncel['katalog_m2']:g} m², {guncel.get('oda_programi')}" if isinstance(guncel.get("katalog_m2"), (int, float)) else "") + ". "
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
                    secenek = ", ".join(m["ad"] for m in ie["mahaller"] if any(a.get("mahal") == m["ad"] for a in ie["acikliklar"] if a["tur"] == "pencere"))
                    return _soru(k, "pencere_mahal", f"Hangi odanın penceresini {yeni} yapalım? Seçenekler: {secenek}.")
                # G-3/G-4 (29.09): oda ve ölçü belli; değişikliği satır yolu B1 kurallarıyla uygular. Aynı odanın satırı varsa varyant
                # düşer (not iki kez yazılmaz); yoksa varyant, geldiği mesajdaki sözle satıra çevrilir. Oda parametrede değil yalnız
                # açıklamada yazılı olsa da (Astra) söz belirsizse B1 sorar: pencere varyant yoluyla sessizce değişmez.
                if not any(varyant._norm(r.get("mahal") or "") == varyant._norm(eslesen[0]) for r in ts.get("pencereler") or []):
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
    # pencere listesi: 'degistir' → şablondaki mahalle eşleştirip ölçü değiştir; 'ekle'/'kaldir' → v0.1'de yönlendirme
    for p in ts.get("pencereler") or []:
        if p.get("islem") in (None, "degistir", "ekle") and p.get("olcu") and p.get("mahal") and p.get("islem_kaynak") != "bayi cevabı":
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
                if niyet == "ekle":
                    p = {**p, "islem": "ekle"}
                else:           # hangi pencere? otomatik seçilmez (v0.1'de soru yerine devir)
                    olculer = ", ".join(a.get("olcu", "?") for a in mevcut)
                    return _bitir(k, Karar(eylem="yonlendir", gerekce=f"{eslesen[0]}: {len(mevcut)} pencere, hangisi belirsiz",
                                           mesaj=f"{eslesen[0]} odasında {len(mevcut)} pencere var ({olculer}); hangisinin {p['olcu']} "
                                                 "olacağını otomatik seçemiyorum. " + YONLENDIRME))
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
                secenek = ", ".join(m["ad"] for m in ie["mahaller"] if any(a.get("mahal") == m["ad"] for a in ie["acikliklar"] if a["tur"] == "pencere"))
                return _soru(k, "pencere_mahal", f"Hangi odanın penceresi? Seçenekler: {secenek}.")
            try:
                ie = varyant.pencere_degistir(ie, eslesen[0], None, p["olcu"]); notlar.append(f"{eslesen[0]} penceresi {p['olcu']}")
            except varyant.VaryantHatasi as e:
                return _bitir(k, Karar(eylem="yonlendir", gerekce=f"pencere hatası: {e}", mesaj=f"Pencere değişikliği uygulanamadı ({e}). " + YONLENDIRME))
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
        elif a.upper() == "KT" and i + 1 < len(toks) and re.fullmatch(r"\d{2}", toks[i + 1]):        # İE-08: "KT-01", "KT 01"
            a = a + toks[i + 1]; i += 1
        # İE-08: varyant harfi ayrı belirteçse ("Ç8801-K", "Ç8801 K") ve o aday kayıtlıysa birleşir; LLM'siz, yalnız kayıtlı kodlar
        if re.fullmatch(r"[PÇC]\d{4}", a.upper()) and i + 1 < len(toks) and re.fullmatch(r"[A-Za-z]", toks[i + 1]) and katalog.aday(a + toks[i + 1].upper()):
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
        k.not_dus("kural", f"seçenek setinden seçim: {kod}" + (" (set dışı)" if st["set_disi"] else ""))


def _secenekler(k: Konusma, katalog: Katalog, ts: dict, uygun: list[dict] | None = None, tur: str = "alan", referans: dict | None = None,
                ek_not: str = "") -> Karar | None:
    """İE-04: aday kaydından uyan aday varsa seçenek seti. Önce (bir kez) öncelik sorulur; sonra set sunulur. Hiç aday yoksa None
    (çağıran bugünkü davranışa döner). Set kaydı konuşmadadır; kimlikler s:<set>:<kod>; eski set 'eskidi' olur.
    İE-08: `uygun` verilirse (çatı seti, tur 'cati_varyanti') sıra hazırdır, puanlanmaz; çelikte öncelik sorusu hiç sorulmaz (Lokman, 12.10.2026).
    `ek_not` (yalnız çelik): set mesajının sonuna (saklanan değişiklik isteği, yeniden sunum)."""
    hazir = uygun is not None
    uygun = SC.uygun_adaylar(katalog, ts) if uygun is None else uygun
    if not uygun:
        return None
    celik_mi = ts.get("yapi_turu") == "celik" or SC.celik_seti_mi(uygun)
    if ts.get("oncelik") is None and len(uygun) >= 2 and not celik_mi:
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
    mesaj = SC.cati_mesaji(sirali, referans or sirali[0]) if tur == "cati_varyanti" else SC.mesaj_metni(sirali, ts)
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
                           gerekce=f"seçenek seti {st['id']}: {len(sirali)} aday" + (" (test verisi)" if test_var else "")))


def _soru(k: Konusma, alan: str, metin: str, butonlar: list[dict] | None = None) -> Karar:
    k.d["soru_sayisi"] += 1
    k.d["son_soru_alani"] = alan
    if k.d["soru_sayisi"] > MAX_SORU:
        return _bitir(k, Karar(eylem="yonlendir", gerekce="soru sınırı", mesaj="Talebi netleştiremedim. " + YONLENDIRME))
    return _bitir(k, Karar(eylem="sor", soru_alani=alan, mesaj=metin, gerekce=f"eksik: {alan}", butonlar=butonlar))


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
    if karar.eylem == "is_emri":
        k.d["bekleyen_onay"] = karar.is_emri.get("is_emri_no") if karar.is_emri else None
        k.d["asama"] = "onay_bekliyor"
    elif karar.eylem == "yonlendir":
        k.d["asama"] = "yonlendirildi"; k.d["taslak"] = {}; k.d["soru_sayisi"] = 0   # insana devredildi; taslak kapanır
    rev0 = getattr(k, "rev0", None)
    if karar.eylem != "is_emri" and rev0 is not None and int(k.d.get("revizyon") or 0) > rev0:
        k.d["revizyon"] = rev0      # G-2 (29.09): soru soran ya da yönlendiren revizyon turu revizyon numarası tüketmez
    k.not_dus("giden", karar.mesaj, {"eylem": karar.eylem, "gerekce": karar.gerekce})
    k.kaydet()
    return karar
