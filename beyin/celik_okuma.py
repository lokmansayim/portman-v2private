"""İE-08 8a PR-2b (A4) · Çelik revizyonunda bayinin KENDİ sözünden okuma (K18; LLM özeti değil). LLM yok, motor modülleri yok.

Üç değişiklik türü (Lokman, 12.10.2026): pencere ölçüsü, çatı varyantı (katalog/K/L), dış karkas 140. Mesaj **cümle cümle** okunur
(kapanış incelemesi 13.10: bütün mesajı tek değişiklik saymak ikinci odayı düşürüyor, "dış kapı 140 cm"yi dış 140 sanıyor, "mutfak
kapısı 90x200"ü pencereye yazıyordu). Her cümle tanıdığı sözcüklerle sınıflanır:
  pencere · çatı · dış 140 · boş (selam, "olsun", model kodu) · belirsiz (tanıdık sözcük, açık istek yok) · başka (tanınmayan içerik)
Tanınmayan sözcük taşıyan cümle hiçbir türe zorlanmaz ("veranda L olsun" çatı değildir, "dış kapı 140" dış 140 değildir); revizyonda
kural katmanı onu yönlendirir (K21: sessizce düşmez, yanlış uygulanmaz). Pencere için aday sayısı 0 → soru (pencereli odalar), 1 → uygula,
2 → görselli "1 / 2 / Hiçbiri", 3 ve üstü → numaralı soru. Olumsuz ya da soru biçimli söz ("olmasın", "… mi?") belirsizdir, sorulur.

`oku(metin, t, katalog_aday, ipucu, y)` → {"pencereler": [...], "pencere": ilk|None, "cati", "cati_belirsiz", "dis140", "baska", "belirsiz",
"olumsuz", "ekle_kaldir", "parcalar", "istek"}
`okuma_cevabi(metin, bekleyen)` → "1 / 2 / Hiçbiri" (ya da numaralı) sorusunun cevabı; ölçü sorusunun cevabı.
"""
from __future__ import annotations
import re

_TR =str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")
PENCERE_EN = (30, 400)
PENCERE_YUK = (30, 250)
VASISTAS_ESIK = 60          # kurallar/cizim/pafta_sablonu.json › vasistas_en_cok_yukseklik_cm ile aynı (motor içe aktarılmasın diye kopya; test denetler)
EN_COK_ADAY = 9

ISLEV_SOZ = {"mutfak": ("mutfak",), "salon": ("salon", "oturma", "yasam", "yasam alani", "oturma odasi", "misafir"),
             "yatak_odasi": ("yatak", "yatak odasi", "ebeveyn", "cocuk", "cocuk odasi"), "banyo": ("banyo", "wc", "tuvalet", "dus", "lavabo"),
             "hol": ("hol", "antre", "koridor", "giris holu"), "depo": ("depo", "kiler", "mustemilat")}
CEPHE_AD = {"on": "ön", "arka": "arka", "sol": "sol", "sag": "sağ"}
# ölçü: "120x120", "120 x 180", "120/180", "120*120", "120'ye 120", "80'e 80", "60'a 40" (kapanış incelemesi: "'ye" tek harf sanılıyordu)
_OLCU = re.compile(r"(?<!\d)(\d{2,3})\s*(?:[xX×*/]|\s*'?\s*(?:ye|ya|e|a)\s)\s*(\d{2,3})(?!\d)")
_CEPHE = re.compile(r"\b(on|arka|sol|sag)(?:daki|taki|deki|dan|tan|den|a|e|da|ta|de)?\s*(?:cephe\w*|taraf\w*|duvar\w*|yuz\w*)\b"
                    r"|\b(on|arka|sol|sag)(?:daki|taki|deki)\b")
_KOD = re.compile(r"\b(?:c\s?\d{4}\s?[kl]?|kt\s?\d{2}|p\s?\d{4}|\d{4}\s?[kl])\b")

# ── sözcük sınıfları (normalize sözcük, tam eşleşme) ───────────────────────────────────────────────────────────────────────────────────
_S = lambda *d: re.compile(r"(?:" + "|".join(d) + r")")
_PENCERE_T = _S(r"pencere\w*", r"vasistas\w*", r"cam", r"cami", r"camlar\w*", r"camin\w*", r"camini")
_VASISTAS_T = _S(r"vasistas\w*")
_OLCU_T = _S(r"olcu\w*", r"boyut\w*", r"ebat\w*", r"cm", r"santim\w*", r"x", r"ye", r"ya", r"e", r"a", r"en", r"eni\w*",
             r"boy(?:u|unu|unda|lu)?", r"yukseklig\w*", r"genislig\w*", r"metre\w*")          # "boya" ölçü değil
_SIFAT_T = _S(r"buyu\w*", r"buyuk\w*", r"kucu\w*", r"kucuk\w*", r"genis\w*", r"dar\w*", r"daralt\w*", r"yuksel\w*", r"yuksek\w*", r"alcal\w*",
              r"alcak\w*", r"uzun\w*", r"kisa\w*", r"standart\w*", r"normal\w*", r"ayni\w*", r"esit\w*")   # pencere türü (çift kanat, sürgülü) tanınmaz: başka
_KONUM_T = _S(r"yan\w*", r"ust\w*", r"alt\w*", r"kose\w*", r"orta\w*", r"kuzey\w*", r"guney\w*", r"dogu\w*", r"bati\w*", r"cephe\w*",
              r"taraf\w*", r"yuz\w*", r"duvar\w*", r"on", r"arka\w*", r"sol\w*", r"sag\w*", r"ondeki", r"onden", r"one")
_CATI_T = _S(r"cati\w*", r"katalog\w*", r"versiyon\w*", r"secenek\w*", r"model\w*", r"varyant\w*", r"tip\w*", r"kirma\w*", r"besik\w*", r"cumba\w*")
_HARF_T = _S(r"k", r"l")
_DIS_T = _S(r"dis", r"dislar\w*", r"disi", r"disin\w*", r"disini", r"distaki\w*", r"karkas\w*", r"profil\w*", r"cerceve\w*", r"kalinlig\w*",
            r"kalin\w*", r"duvar\w*")
_140_T = _S(r"140", r"14", r"140lik", r"140luk", r"14luk", r"14luk", r"lik", r"luk", r"mm")
_OLUMSUZ_FIIL = (r"olmasin\w*", r"olmayacak\w*", r"olmaz", r"istemiyor\w*", r"istemem\w*", r"istemeyiz", r"degil\w*",
                 r"degistirme(?:yin|yiniz|yelim|sin|sen)?", r"yapma(?:yin|yiniz|yalim|sin)?", r"ekleme(?:yin|yiniz|yelim|sin)?",
                 r"koyma(?:yin|yiniz|yalim|sin)?", r"dokunma\w*", r"vazgec\w*", r"iptal", r"haric\w*", r"gereksiz\w*",
                 r"\w+m(?:e|a)(?:yelim|yalim|yin|yiniz|sin|sinler|sinlar)",   # "geçmeyelim", "çevirmeyin", "gelmesin" (beşinci tur)
                 r"\w+m(?:e|a)d(?:i|ik|im|in|iniz|iler|ilar)", r"\w+m(?:i|u)yor\w*", r"\w+m(?:e|a)z")   # "beğenmedik", "istemiyoruz",
                                                                                                    # "gerekmez" (altıncı tur)
_OLUMSUZ_T = _S(*_OLUMSUZ_FIIL, r"yok", r"hayir")
_OLUMSUZ_FIIL_T = _S(*_OLUMSUZ_FIIL)          # çatı seçimini engelleyen olumsuzluk ("yok"/"hayır" değil: "Ç8801K olsun başka değişiklik yok")
_KALSIN_T = _S(r"kalsin", r"kalabilir", r"kalacak", r"dursun")
_SORU_T = _S(r"mi", r"mu", r"misiniz", r"musunuz", r"miyiz", r"muyuz", r"midir", r"mudur", r"mismiz", r"musun", r"misin", r"nasil", r"neden",
             r"niye", r"hangisi", r"ne", r"kac")
_EKLE_T = _S(r"ekle\w*", r"ilave\w*", r"fazladan", r"kaldir\w*", r"sil\w*", r"kapat\w*", r"acalim", r"acin", r"aciniz", r"acilsin", r"acilacak",
             r"acmak", r"acar\w*")
_DOLGU_T = _S(r"olsun", r"olsa", r"olacak", r"olmali\w*", r"olabilir", r"olur", r"olursa", r"olarak", r"yapalim", r"yapin", r"yapiniz", r"yap",
              r"yapar\w*", r"yapilsin", r"yapilmali", r"yapilabilir", r"yapacag\w*", r"yapilacak", r"degistir", r"degistirin\w*",
              r"degistirelim", r"degistirilsin", r"degistirmek", r"degistirebilir\w*", r"degissin", r"guncelle\w*", r"duzelt\w*", r"ayarla\w*",
              r"cevir\w*", r"getir\w*", r"edelim", r"edin", r"ediniz", r"edilsin", r"edilmeli", r"et", r"etsin", r"etmek", r"edebilir\w*",
              r"ederseniz", r"lutfen", r"rica", r"ederim", r"ederiz", r"tesekkur\w*", r"sagol\w*", r"bir", r"de", r"da", r"ve",
              r"ile", r"icin", r"bu", r"su", r"o", r"olan", r"yerine", r"iken", r"idi", r"di", r"den", r"dan", r"ten", r"tan", r"dir", r"simdi",
              r"artik", r"tamam", r"ok", r"okey", r"evet", r"merhaba", r"selam\w*", r"slm", r"mrb", r"hocam", r"abi", r"abla", r"bey", r"hanim",
              r"usta\w*", r"kardesim", r"efendim", r"bunu", r"onu", r"sunu", r"bunlari", r"onlari", r"hem", r"daha", r"biraz", r"cok", r"az",
              r"gibi", r"kadar", r"sekilde", r"istiyorum", r"istiyoruz", r"isteriz", r"isterim", r"istiyor", r"istedig\w*", r"lazim",
              r"gerek\w*", r"mumkun\w*", r"eger", r"ise", r"sadece", r"yalniz", r"tane", r"adet", r"her", r"iki\w*", r"uc\w*", r"mevcut\w*",
              r"eski\w*", r"yeni", r"simdiki\w*", r"suanki\w*", r"var", r"olan\w*", r"oldugu", r"bence", r"bizim", r"benim", r"musteri\w*",
              r"istegi", r"talep\w*", r"plan\w*", r"cizim\w*", r"pafta\w*", r"revize", r"revizyon\w*", r"sey\w*", r"hepsi\w*", r"tum\w*",
              r"butun", r"ayrica", r"ama", r"fakat", r"ancak", r"yine", r"tekrar", r"son", r"ilk", r"birinci", r"ikinci", r"ucuncu",
              r"guzel\w*", r"harika", r"super", r"iyi", r"gayet", r"olmus", r"oldu", r"begen\w*",          # beğeni sözü istek değildir
              r"degisiklik\w*", r"aynen", r"aynisi", r"boyle", r"soyle",                                 # "değişiklik yok", "böyle kalsın"
              r"yapabil\w*", r"donustur\w*", r"gec(?:elim|sin|in|iniz|ilsin|ebilir\w*)",                # "140'lık yapabilir miyiz?", "L'ye geçelim"
              r"geri", r"gerisi", r"kalan\w*", r"diger\w*", r"oteki\w*", r"oyle")                     # "gerisi aynı kalsın" (altıncı tur)
_ODA_GENEL = re.compile(r"\b(?:oda\w*|mahal\w*)\b")
_SAYI_SOZ = {"bir": 1, "birinci": 1, "ilk": 1, "ilki": 1, "iki": 2, "ikinci": 2, "ikincisi": 2, "uc": 3, "ucuncu": 3, "dort": 4, "dorduncu": 4,
             "bes": 5, "besinci": 5, "alti": 6, "altinci": 6, "yedi": 7, "yedinci": 7, "sekiz": 8, "sekizinci": 8, "dokuz": 9, "dokuzuncu": 9}
# numaralı oda sözü yalnız sıra sayısıyla: "bir yatak odasının penceresi" (herhangi biri; kapanış incelemesi) ve "iki yatak odası" (iki oda)
# numara değildir
_ODA_SAYI = {k: v for k, v in _SAYI_SOZ.items() if re.search(r"(inci|nci|uncu|unci|ncisi|incisi)$", k) or k in ("ilk", "ilki")}
_EKLE_IFADE = re.compile(r"\bbir\s+(?:tane\s+)?(?:(?:pencere|vasistas)\w*\s+)?daha\b|\byeni\s+(?:bir\s+)?(?:pencere|vasistas)\w*"
                         r"|\bfazla(?:dan)?\s+(?:bir\s+)?(?:pencere|vasistas)\w*")
# "salona pencere yapabilir misiniz?", "mutfağa bir pencere yapalım": odaya pencere yapmak eklemedir (beşinci tur; ölçü değişikliği sanılıyordu)
_EKLE_ODA = re.compile(r"(?:^|\s)(\w+[ae])\s+(?:bir\s+)?(?:pencere|vasistas)\s+(?:yap|koy)\w*")     # yalın "pencere": "pencereyi" var olandır
# çatı cümlesi bilgi mi: renk ve malzeme sözü bilgi ("çatı rengi kırmızı", "çatı kaplaması shingle"); şekil, eğim, yön sözü değişiklik
# isteğidir ("çatı şekli kırma olsun", "çatı eğimi dik olsun", "çatı düz olsun"; beşinci tur: bilgi sayılıp tablo çizimle çelişiyordu)
_RENK_T = _S(r"renk\w*", r"rengi\w*", r"kaplama\w*", r"malzeme\w*", r"kiremit\w*", r"shingle\w*", r"membran\w*", r"boya\w*", r"ton\w*",
             r"kirmizi\w*", r"gri\w*", r"beyaz\w*", r"siyah\w*", r"antrasit\w*", r"kahve\w*", r"yesil\w*", r"mavi\w*", r"bordo\w*", r"krem\w*",
             r"lacivert\w*", r"bej\w*", r"turuncu\w*", r"sari\w*", r"mat", r"parlak\w*", r"metalik\w*", r"sandvic\w*", r"trapez\w*", r"sac",
             r"eternit\w*", r"onduline\w*")
_CATI_GEO_OZEL = (r"sekl\w*", r"sekil\w*", r"egim\w*", r"egik\w*", r"kirma\w*", r"besik\w*", r"mahya\w*", r"sundurma\w*", r"sacak\w*",
                  r"cumba\w*", r"piramit\w*", r"mansard\w*", r"tonoz\w*", r"kubbe\w*", r"kelebek\w*")
_CATI_GEO_OZEL_T = _S(*_CATI_GEO_OZEL)        # çatıya özgü şekil sözü: "çatı" sözü ayrı cümlede kalsa da işarettir ("çatı gri olsun, eğimi dik olsun")
_CATI_GEO_T = _S(*_CATI_GEO_OZEL, r"duz", r"duzlem\w*", r"yon\w*", r"dik\w*", r"yatik\w*", r"aci\w*", r"yuksek\w*", r"alcak\w*",
                 r"teras\w*", r"kot\w*", r"yuksel\w*")
_DONUSUM_T = _S(r"donustur\w*", r"cevir\w*")           # odayla birlikte: oda dönüşümü ("salonu yatak odasına çevirelim") otomatik yapılamaz
# yüklem (istek fiili): "ve" parçasını kendi cümlesi yapar ("odalar geniş olsun"); yüklemsiz "büyük banyo" oda tarifidir
_YUKLEM_T = _S(r"ol(?:sun\w*|sa\w*|acak\w*|mali\w*|abilir\w*|ur|ursa)", r"yap\w*", r"degis\w*", r"cevir\w*", r"donustur\w*", r"getir\w*",
               r"ed(?:elim|in|iniz|ilsin|ilmeli|ebilir\w*)", r"et(?:sin)?", r"iste\w*", r"buyut\w*", r"buyusun\w*", r"kucult\w*", r"genislet\w*",
               r"daralt\w*", r"yukselt\w*", r"alcalt\w*", r"uzat\w*", r"kisalt\w*", r"kalsin\w*", r"lazim", r"gerek\w*")
_HICBIRI = re.compile(r"\b(?:hicbiri\w*|hic biri\w*|hicbirini|ikisi de degil|ikiside degil|hicbir\w*|baska)\b")
_HEPSI = re.compile(r"\b(?:ikisi de|ikiside|ikisini de|her ikisi\w*|hepsi\w*|tumu|tamami)\b")
_CEVAP_DOLGU = {"olsun", "pencere", "penceresi", "numara", "numarali", "nolu", "no", "tane", "olan", "o", "su", "bu", "ve", "ile", "sorun",
                "yok", "hayir", "evet", "tamam", "lutfen", "ok", "inci", "nci", "uncu", "unci", "incisi", "ncisi", "lu", "li", "secenek", "secim"}


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (s or "").translate(_TR).lower())).strip()


def _capa(parca: str) -> bool:
    """Parçada değişiklik çapası var mı: pencere ölçüsü, pencere sözü, "dış" + 140, katalog sözü, çatı sözüyle çatı harfi ("çatı L") ya da
    varyant kodu, ekleme/kaldırma sözü. Tek başına "K"/"L" harfi çapa değildir (geometri hakemi üçüncü tur: "çatı K ve L'yi görelim"
    bölünüp K seçiliyordu); harfsiz "çatı" sözü de değildir (dördüncü tur: "çatı ve dış cephe gri olsun" bir bilgi cümlesidir)."""
    if olculer(parca):
        return True
    q = norm(_olcusuz(parca))
    kodlar = _KOD.findall(q)
    soz = _KOD.sub(" ", q).split()
    return (any(_PENCERE_T.fullmatch(w) for w in soz) or any(_EKLE_T.fullmatch(w) for w in soz)
            or (any(w.startswith("dis") and _DIS_T.fullmatch(w) for w in soz) and any(w in ("140", "14") for w in soz))
            or any(w.startswith("katalog") for w in soz)
            or (any(w.startswith("cati") for w in soz) and any(_HARF_T.fullmatch(w) for w in soz))
            or any(re.search(r"[kl]$", re.sub(r"\s", "", k)) for k in kodlar))


def _bagimsiz(parca: str, mahaller: list[dict] | None) -> bool:
    """Çapasız ama kendi başına bir istek olan parça kendi cümlesidir; çapalı parçaya eklenirse ondaki isteği bilgi ya da başka cümle içinde
    saklar. Bağımsız: tanınmayan içerik ("dış cephe gri olsun", "banyoya havlupan koyalım", "oda kapıları beyaz olsun"; geometri hakemi
    üçüncü tur) ya da tanınan sözlerle yüklemli bir oda isteği ("odalar geniş olsun", "salonu büyütelim"; beşinci tur: "dışlar 140'lık olsun
    ve odalar geniş olsun" birleşip dış 140 ilk planda sessizce düşüyordu). Bağımsız değil: yalın oda adı ("çalışma odası ve mutfak
    pencereleri"; dördüncü tur), yüklemsiz oda tarifi ("büyük banyo ve mutfak pencereleri 120x120": banyo pencere cümlesine aittir), çatı
    harfi ya da model kodu taşıyan parça ("çatı K ile L arasındaki fark nedir?": "L arasındaki fark" çatı cümlesine aittir)."""
    q0 = norm(_olcusuz(parca))
    if _KOD.search(q0) or any(_HARF_T.fullmatch(w) for w in q0.split()):
        return False
    soz = [w for w in q0.split() if w not in ("ve", "ile", "de", "da")]
    if re.fullmatch(r"(?:\w+ ){0,2}(?:oda\w*|mahal\w*)", " ".join(soz)):
        return False                                        # yalın oda adı: oda listesinin parçası
    q1 = _odalar(q0, mahaller or [])[1]
    if any(_sinifla(w) == "bilinmeyen" for w in _ODA_GENEL.sub(" ", q1).split()):
        return True                                         # tanınmayan içerik
    # tanınan sözlerle "başka": yalnız oda + yüklem ("odalar geniş olsun", "salonu büyütelim"); oda ya da yüklem yoksa tarif ya da ölçü
    # devamıdır ("salonun sol duvarı ve arka duvarındaki pencereler", "eni 120 ve boyu 180 olsun"; altıncı tur: bölünüp yanlış odaya
    # uygulanıyor ya da düşüyordu)
    if not any(_YUKLEM_T.fullmatch(w) or _OLUMSUZ_FIIL_T.fullmatch(w) for w in q0.split()):
        return False
    oda = q1.split() != q0.split() or bool(_ODA_GENEL.search(q0))
    tur = parca_oku(parca, {"mahaller": mahaller or []})["tur"]
    # "kalsın"/olumsuz yüklemli, değişiklik bildirmeyen cümle de kendi cümlesidir ("salon aynı kalsın ve mutfak penceresi 120x120 olsun",
    # "… ve gerisi aynı kalsın"): pencere cümlesine eklenirse onu "kalsın"lı (olumsuz) yapar. "… 120x120 ile değiştirelim" tek cümledir.
    sabit = any(_KALSIN_T.fullmatch(w) or _OLUMSUZ_T.fullmatch(w) for w in q0.split())
    return (tur == "bos" and sabit) or (oda and tur == "baska")


def _ve_bol(parca: str, mahaller: list[dict] | None = None) -> list[str]:
    """"ve"/"ile" ile bağlanmış istekler ayrı cümledir — ama yalnız iki yanında da çapa varsa ("mutfak penceresi 120x120 ve dışlar 140'lık
    olsun" iki istek; "mutfak ve salon pencereleri 120x120" tek istek, "120x120 ile değiştirelim" tek istek). Çapasız parça sonraki çapalı
    parçaya (sonda kalırsa öncekine) eklenir (geometri hakemi ikinci tur, 13.10: ikinci istek sessizce düşüyordu)."""
    bolum = re.split(r"(\s+(?:ve|ile)\s+)", parca)
    parcalar, ayraclar = bolum[0::2], bolum[1::2]
    gruplar: list[list[int]] = []
    bas = 0
    for i, x in enumerate(parcalar):
        if _capa(x) or _bagimsiz(x, mahaller):
            gruplar.append([bas, i]); bas = i + 1
    if not gruplar:
        return [parca]
    gruplar[-1][1] = len(parcalar) - 1                       # sondaki çapasız parça son gruba
    out = []
    for g0, g1 in gruplar:
        t = parcalar[g0]
        for j in range(g0 + 1, g1 + 1):
            t += ayraclar[j - 1] + parcalar[j]
        out.append(t)
    return out


def _parcalar(metin: str | None, mahaller: list[dict] | None = None) -> list[str]:
    """Cümleler: noktalama ve satır sonu; "ama", "fakat", "ayrıca" da ayırır; "ve"/"ile" yalnız iki yanında da istek çapası (ya da tanınmayan
    içerik) varsa (`_ve_bol`; `mahaller` modelin oda adlarını tanıtır)."""
    out = []
    metin = re.sub(r"(?<![\w/×*'])(\d{1,2})\.(?=\s)", r"\1 ", metin or "")      # sıra noktası ("1. yatak odası") cümle sonu değil
    for p in re.findall(r"[^;,.!?\n]+[;,.!?\n]*", metin):
        for x in re.split(r"\s+(?=(?:ama|fakat|ayrıca|ayrica)\s)", p):
            if x.strip():
                out.extend(_ve_bol(x, mahaller))
    return out


def olculer(metin: str | None) -> list[tuple[int, int]]:
    """Metindeki pencere ölçüleri (en, yük; cm). "120x120", "120 x 180", "120/180", "120*120", "120'ye 120", "80'e 80"."""
    out = []
    for m in _OLCU.finditer(metin or ""):
        en, yuk = int(m.group(1)), int(m.group(2))
        if PENCERE_EN[0] <= en <= PENCERE_EN[1] and PENCERE_YUK[0] <= yuk <= PENCERE_YUK[1]:
            out.append((en, yuk))
    return out


def _olcusuz(metin: str) -> str:
    """Geçerli pencere ölçülerini metinden çıkarır (sözcük sınıflaması ölçü rakamlarını görmesin)."""
    def bosalt(m):
        en, yuk = int(m.group(1)), int(m.group(2))
        return " " if (PENCERE_EN[0] <= en <= PENCERE_EN[1] and PENCERE_YUK[0] <= yuk <= PENCERE_YUK[1]) else m.group(0)
    return _OLCU.sub(bosalt, metin or "")


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
        merkez = None
        if d is not None:
            x0, y0, x1, y1 = d["kutu"]
            yatay = (x1 - x0) >= (y1 - y0)
            merkez = (a["bas"] + a["en"] / 2, (y0 + y1) / 2) if yatay else ((x0 + x1) / 2, a["bas"] + a["en"] / 2)
        out.append({"aciklik": a["ad"], "mahal": mahal, "en": a["en"], "yuk": a["yuk"], "etiket": et, "cephe": c, "vasistas": vas, "_merkez": merkez,
                    "aciklama": f"{mahal + ' ' if mahal else ''}{'vasistası' if vas else 'penceresi'} {et}" + (f" ({CEPHE_AD[c]} cephe)" if c else "")})
    # aynı tarifli pencereler (aynı oda, ölçü ve cephe) konumla ayrılır: yan cephede öne/arkaya, ön ve arka cephede sola/sağa yakın (planda)
    gruplar: dict[str, list[dict]] = {}
    for p in out:
        gruplar.setdefault(p["aciklama"], []).append(p)
    for tarif, ps in gruplar.items():
        if len(ps) < 2 or any(p["_merkez"] is None or p["cephe"] is None for p in ps):
            continue
        yan = ps[0]["cephe"] in ("sol", "sag")
        ps = sorted(ps, key=lambda p: p["_merkez"][1] if yan else p["_merkez"][0])
        adlar = (["öne yakın", "arkaya yakın"] if yan else ["sola yakın", "sağa yakın"]) if len(ps) == 2 else \
                [f"{'önden' if yan else 'soldan'} {i}." for i in range(1, len(ps) + 1)]
        for p, ek in zip(ps, adlar):
            p["aciklama"] = tarif[:-1] + f", {ek})"
    for p in out:
        p.pop("_merkez", None)
    return out


def _kok(s: str) -> str:
    """Normalize sözcük(ler) → ek alabilen gövde deseni: son sözcük ek alır ("alani" → "alaninin"), sondaki k yumuşar ("mutfak" → "mutfagin")."""
    soz = s.split()
    out = []
    for i, w in enumerate(soz):
        g = re.escape(w[:-1]) + "[kg]" if w.endswith("k") else re.escape(w)
        out.append(g + (r"\w*" if i == len(soz) - 1 else ""))
    return r"\b" + r"\s+".join(out)


def _oda_desenleri(mahaller: list[dict]) -> list[tuple[str, list[str]]]:
    """(desen, odalar): adın kendisi (ekli/yumuşamış), numaralı biçimler ("1. yatak odası", "ikinci yatak odasının", "yatak odası 2"),
    işlev eşanlamları (birden çok oda: iki yatak odası) ve eşi modelde olmayan işlev sözleri (oda yok, sözcük tanınır: "kiler")."""
    out: list[tuple[str, list[str]]] = []
    for m in mahaller:
        nm = norm(m["ad"])
        out.append((_kok(nm) + (r"(?!\s*\d)" if not re.search(r"\d$", nm) else r"\b"), [m["ad"]]))
        mm = re.fullmatch(r"(.+?) (\d)", nm)
        if mm:
            govde, no = mm.group(1), mm.group(2)
            sayilar = "|".join(k for k, v in _ODA_SAYI.items() if v == int(no))
            out.append((rf"\b(?:{no}\s*(?:inci|nci|uncu|unci|nolu|no lu|numarali)?|{sayilar})\s+{_kok(govde)[2:]}", [m["ad"]]))
    for islev, sozler in ISLEV_SOZ.items():
        odalar = [m["ad"] for m in mahaller if islev in (m.get("islev") or [])]
        for s in sozler:
            out.append((_kok(s), odalar))
    return out


def _odalar(metin_n: str, mahaller: list[dict]) -> tuple[list[str], str]:
    """Metinde geçen odalar ve oda sözleri çıkarılmış metin. Örtüşen eşleşmelerde uzun olan kazanır ("yatak odası 2" > "yatak")."""
    q = " " + metin_n + " "
    eslesme = []
    for desen, odalar in _oda_desenleri(mahaller):
        for m in re.finditer(desen, q):
            eslesme.append((m.start(), m.end(), odalar))
    eslesme.sort(key=lambda e: (-(e[1] - e[0]), e[0]))
    secilen: list[tuple[int, int, list[str]]] = []
    for e in eslesme:
        if all(e[1] <= s[0] or e[0] >= s[1] for s in secilen):
            secilen.append(e)
    bulunan: list[str] = []
    for _, _, odalar in sorted(secilen):
        for o in odalar:
            if o not in bulunan:
                bulunan.append(o)
    for s0, s1, _ in sorted(secilen, reverse=True):
        q = q[:s0] + " " + q[s1:]
    return bulunan, q


def _mahaller(metin_n: str, t: dict) -> list[str]:
    return _odalar(metin_n, t.get("mahaller", []))[0]


def _cepheler(metin_n: str) -> list[str]:
    q = " " + metin_n + " "
    return sorted({(m.group(1) or m.group(2)) for m in _CEPHE.finditer(q)})


def _yonelme_odasi(w: str, mahaller: list[dict] | None) -> bool:
    """`w` bir odanın yönelme hâli mi ("salona", "mutfağa", "banyoya", "odasına")? Bulunma hâli ("mutfakta", "odasında") ve yalın oda adı
    ("antre", "oda") değildir (altıncı tur: "mutfakta pencereyi 120x120 yapalım" ekleme sanılıyordu)."""
    if re.search(r"[dt][ae]$", w):
        return False
    yalin = {x for m in mahaller or [] for x in norm(m.get("ad")).split()} | {x for ss in ISLEV_SOZ.values() for s in ss for x in s.split()} | {"oda"}
    if w in yalin:
        return False
    return bool(_ODA_GENEL.fullmatch(w)) or _odalar(w, mahaller or [])[1].split() != [w]


def _sinifla(sozcuk: str) -> str:
    for ad, rx in (("olumsuz", _OLUMSUZ_T), ("kalsin", _KALSIN_T), ("ekle", _EKLE_T), ("pencere", _PENCERE_T), ("cati", _CATI_T),
                   ("harf", _HARF_T), ("dis", _DIS_T), ("d140", _140_T), ("olcu", _OLCU_T), ("sifat", _SIFAT_T), ("konum", _KONUM_T),
                   ("soru", _SORU_T), ("dolgu", _DOLGU_T)):
        if rx.fullmatch(sozcuk):
            return ad
    if re.fullmatch(r"\d+", sozcuk):
        return "sayi"
    return "bilinmeyen"


# ── çatı seçenekleri (geometri hakemi dördüncü tur, 13.10) ─────────────────────────────────────────────────────────────────────────────
# Seçenek: "k", "l" (tek harf ya da varyant kodunun harfi) ve "katalog" (katalog çatısı). Değişimin kaynağı ("K'dan L'ye", "Ç8801K yerine
# Ç8801L", "katalogdan K'ya") seçenek değildir; kalan tek seçenek seçimdir, iki ve daha çok seçenek kararsızlıktır (sorulur ya da set sunulur).
_SECIM_SOZ = re.compile(r"\b(?:mi|mu|ya da|yada|veya|yoksa|hangisi\w*|arasinda\w*|kararsiz\w*)\b")
_SEKIL_T = re.compile(r"(?:tip\w*|sekl\w*|sekil\w*|bicim\w*)")
_AYRILMA = ("dan", "den", "tan", "ten")


def _parca_secenekleri(q: str, taban: str | None = None) -> tuple[set[str], set[str]]:
    """Bir cümlenin (normalize, ölçüsüz) çatı seçenekleri ve değişim kaynağı olan kodlar ("c8801k", "c8801"). "katalog" sözü yalnız çatı
    sözüyle ya da seçim sorusunda seçenektir ("katalog çatısı", "K mı katalog mu?"; "katalogdaki Ç8801K" değil); taban kod yalnız seçim
    sorusunda başka bir seçenekle ("Ç8801L mi Ç8801 mi?"; "Ç8801 çelik ev" değil). Şekil sözlü tek harf çatı sözü yoksa seçenek değildir
    ("L tipi mutfak"). `taban` ("c8801") verilirse başka modelin varyant kodu seçenek sayılmaz."""
    soz = _KOD.sub(lambda m: re.sub(r"\s", "", m.group(0)) + " ", q).split()     # "c8801 k" → "c8801k" (kod sonundaki boşluk korunur)
    cati = any(w.startswith("cati") for w in soz)
    secim = bool(_SECIM_SOZ.search(" " + " ".join(soz) + " "))
    sec: set[str] = set()
    kaynak_kod: set[str] = set()
    taban_var = False
    for i, w in enumerate(soz):
        ard = soz[i + 1:i + 3]
        if re.fullmatch(r"(?:c\d{4}|\d{4})[kl]", w):
            if taban and re.sub(r"[kl]$", "", w).lstrip("c") != taban.lstrip("c"):
                continue
            s = w[-1]
        elif w in ("k", "l"):
            s = w
        elif re.fullmatch(r"c\d{4}", w):
            s = "taban"
        elif w.startswith("katalog"):
            s = "katalog"
        else:
            continue
        kaynak = ((s == "katalog" and w.endswith(_AYRILMA)) or (bool(ard) and (ard[0] in _AYRILMA or ard[0] == "yerine"))
                  or (bool(ard) and ard[0] in ("nin", "nun", "in", "un") and ard[1:2] == ["yerine"])
                  or (bool(ard) and ard[0].startswith("cati") and (ard[0].endswith(_AYRILMA) or ard[1:2] == ["yerine"])))
        if kaynak:
            if re.fullmatch(r"(?:c\d{4}|\d{4})[kl]?", w):
                kaynak_kod.add(w)                           # karar katmanı bu kodu seçim saymaz
            continue
        if s in ("k", "l") and w in ("k", "l") and ard and _SEKIL_T.fullmatch(ard[0]) and not cati:
            continue                                        # "L tipi mutfak": şekil sözü, çatı değil
        if s == "katalog" and not (cati or secim):
            continue
        if s == "taban":
            taban_var = True
            continue
        sec.add(s)
    if taban_var and secim and sec:
        sec.add("katalog")
    return sec, kaynak_kod


def cati_secenekleri(metin: str | None, mahaller: list[dict] | None = None, taban: str | None = None) -> set[str]:
    """Mesajda cümle cümle geçen çatı seçenekleri ({"k", "l", "katalog"}); kaynaklar düşülmüş. İkiden çoksa seçim değil kararsızlıktır."""
    out: set[str] = set()
    for p in _parcalar(metin, mahaller):
        out |= _parca_secenekleri(norm(_olcusuz(p)), taban)[0]
    return out


def cati_kaynak_kodlari(metin: str | None) -> set[str]:
    """Değişimin kaynağı olarak geçen model kodları ("Ç8801K yerine …", "Ç8801'den …"; normalize: "c8801k", "c8801"). Seçim sayılmaz."""
    out: set[str] = set()
    for p in _parcalar(metin):
        out |= _parca_secenekleri(norm(_olcusuz(p)))[1]
    return out


def cati_olumsuz(metin: str | None, mahaller: list[dict] | None = None) -> bool:
    """Çatı seçeneği (harf, model kodu, katalog sözü) taşıyan bir cümle olumsuz mu ("Ç8801L olmasın", "Ç8801L istemiyoruz", "Ç8801K'dan
    Ç8801L'ye geçmeyelim", "… Ç8801L değil")? Öyleyse mesajdaki koddan çatı seçilmez, kararsızlık gibi sorulur ya da set sunulur (geometri
    hakemi beşinci tur: ters çatı sorulmadan seçiliyordu). "yok" yalnız çatı sözünün ya da "gerek/ihtiyaç"ın hemen ardındaysa olumsuzdur
    ("Ç8801L yok", "Ç8801L'ye gerek yok"; altıncı tur), değilse sayılmaz ("Ç8801K olsun başka değişiklik yok")."""
    for p in _parcalar(metin, mahaller):
        soz = _KOD.sub(lambda m: re.sub(r"\s", "", m.group(0)) + " ", norm(_olcusuz(p))).split()
        secenek = [i for i, w in enumerate(soz) if re.fullmatch(r"(?:c\d{4}|\d{4})[kl]?", w) or w in ("k", "l") or w.startswith("katalog")]
        if not secenek:
            continue
        if any(_OLUMSUZ_FIIL_T.fullmatch(w) for w in soz):
            return True
        for i, w in enumerate(soz):
            if w == "yok" and i > 0 and (i - 1 in secenek or i - 2 in secenek and soz[i - 1] in ("ye", "ya", "e", "a", "ne", "na")
                                       or soz[i - 1].startswith(("gerek", "ihtiyac", "lazim"))):
                return True
    return False


def _secenek_kodu(s: str, katalog_aday: dict | None) -> str | None:
    """Tek çatı seçeneğinin aday kodu: "katalog" → katalog modeli, "k"/"l" → o harfle biten varyant."""
    if not katalog_aday or not katalog_aday.get("varyantlar"):
        return None
    if s == "katalog":
        return str(katalog_aday["kod"]).upper()
    return next((str(v).upper() for v in katalog_aday["varyantlar"] if str(v).upper().endswith(s.upper())), None)


def parca_oku(parca: str, t: dict, katalog_aday: dict | None = None, y: dict | None = None) -> dict:
    """Tek cümlenin okuması: {"metin", "tur", "olumsuz", "bilinmeyen", ...}; tur pencere ise pencere okuması alanları da."""
    olc = olculer(parca)
    q0 = norm(_olcusuz(parca))
    kodlar = [re.sub(r"\s", "", k) for k in _KOD.findall(q0)]
    q1 = _KOD.sub(" ", q0)
    odalar, q2 = _odalar(q1, t.get("mahaller", []))
    genel_oda = bool(_ODA_GENEL.search(q2))
    q3 = _ODA_GENEL.sub(" ", q2)
    ceph = _cepheler(q3)
    soz = q3.split()
    sinif: dict[str, list[str]] = {}
    for s in soz:
        sinif.setdefault(_sinifla(s), []).append(s)
    has = lambda *a: any(sinif.get(x) for x in a)
    soru = "?" in parca or has("soru")
    olumsuz = has("olumsuz") or soru
    r = {"metin": parca.strip(), "tur": "bos", "olumsuz": olumsuz, "bilinmeyen": sinif.get("bilinmeyen", []), "odalar": odalar, "olcu": None,
         "neden": None}
    sayilar = [int(s) for s in sinif.get("sayi", [])]
    pencere_soz = has("pencere")
    d140 = [s for s in sinif.get("d140", []) if s not in ("lik", "luk", "mm")]
    varyant_kodu = any(re.search(r"[kl]$", k) for k in kodlar)
    cati_soz = any(s.startswith(("cati", "katalog")) for s in sinif.get("cati", []))
    m_pencere = pencere_soz or bool(olc)
    m_dis140 = has("dis") and bool(d140) and any(s.startswith("dis") for s in sinif.get("dis", []))
    m_cati = cati_soz or has("harf")
    ekle_oda = next((m for m in _EKLE_ODA.finditer(q1) if _yonelme_odasi(m.group(1), t.get("mahaller", []))), None)
    m_ekle = has("ekle") or bool(_EKLE_IFADE.search(" " + q0 + " ")) or ekle_oda is not None
    # bilgi cümlesi denetimi için çatı işareti: harf, varyant kodu, katalog sözü ya da renk/malzeme sözü olmayan "çatı" sözü. "çatı rengi
    # kırmızı olsun" bilgi cümlesidir (dördüncü tur); "çatı şekli kırma olsun", "çatı eğimi dik olsun" değildir (beşinci tur)
    tum = q0.split()
    geo_ozel = any(_CATI_GEO_OZEL_T.fullmatch(w) for w in tum)
    renk = any(_RENK_T.fullmatch(w) for w in tum) and not any(_CATI_GEO_T.fullmatch(w) for w in tum)
    r["isaret"] = {"pencere": m_pencere, "dis140": m_dis140, "ekle": m_ekle,
                   "cati": has("harf") or varyant_kodu or geo_ozel or any(s.startswith("katalog") for s in sinif.get("cati", []))
                   or (any(s.startswith("cati") for s in sinif.get("cati", [])) and not renk)}
    r["d140"] = bool(d140)
    if sinif.get("bilinmeyen"):
        r["tur"] = "baska"
        return r
    if m_ekle and (m_pencere or odalar):
        r["tur"] = "ekle_kaldir"
        return r
    if m_pencere + m_dis140 + m_cati >= 2:                  # bölünemeyen iki istek ("dışlar 140 ve L olsun"): sorulur, düşmez
        r["tur"] = "belirsiz"; r["neden"] = "karma"
        return r
    # dış 140: "dış" + 140/14 (ve yalnız duvar/karkas/kalınlık sözleri); oda ve başka sayı yok (model kodu olabilir: "Ç8801K dışlar 140")
    if m_dis140 and not (odalar or genel_oda) and not [n for n in sayilar if n not in (14, 140)]:
        r["tur"] = "dis140"
        return r
    if has("olcu") and (sayilar or has("d140")) and not m_pencere:
        r["tur"] = "baska"                                 # pencere dışı bir ölçü ("dış ölçü 14 x 8"): otomatik yapılamaz
        return r
    # çatı: çatı/katalog sözü, tek harf (k/l) ya da varyant kodu; pencere ve oda yok ("model", "versiyon" tek başına çatı değil). Seçim
    # cümlenin çatı seçeneklerinden: tek seçenek seçimdir ("çatıyı K'dan L'ye çevirelim" → L), iki seçenek ("çatı K mı L mi", "Ç8801K mi
    # katalog çatısı mı") seçim değildir.
    if (m_cati or varyant_kodu) and not (m_pencere or odalar or genel_oda or has("dis", "d140")):
        taban = norm(str(katalog_aday["kod"])) if katalog_aday and katalog_aday.get("kod") else None
        sec = _parca_secenekleri(q0, taban)[0]
        r["tur"] = "cati"
        r["kod"] = _secenek_kodu(next(iter(sec)), katalog_aday) if len(sec) == 1 else None
        r["neden"] = "iki_cati" if len(sec) > 1 else None
        r["olumsuz"] = has("olumsuz") or soru            # "katalog çatısı kalsın" seçimdir (kalsın olumsuz değil)
        return r
    if m_pencere:
        if has("kalsin") and not olc:
            r["tur"] = "bos"                               # "mutfak penceresi kalsın": değişiklik yok
            return r
        if olc and sayilar:
            r["tur"] = "belirsiz"; r["neden"] = "sayi"     # ölçü dışı sayı ("yatak odası 1 ve 2 pencereleri", "2 tane"): sorulur
            return r
        r["tur"] = "pencere"
        r["olumsuz"] = olumsuz or (has("kalsin") and bool(olc))
        r["olcu_sayisi"] = len(olc)
        r["_olc"] = olc
        r["vasistas_soz"] = has("pencere") and all(_VASISTAS_T.fullmatch(s) for s in sinif["pencere"])
        r["cepheler"] = ceph
        r["genel_oda"] = genel_oda
        return r
    if odalar or genel_oda:
        # "salon aynı kalsın": değişiklik yok (altıncı tur: "aynı" sıfat sayılıp yönlendiriliyordu)
        degismez = has("kalsin") and all(re.match(r"(?:ayni|esit|standart|normal)", s) for s in sinif.get("sifat", []))
        if any(_DONUSUM_T.fullmatch(w) for w in soz):
            r["tur"] = "baska"                             # oda dönüşümü ("salonu yatak odasına çevirelim"): otomatik yapılamaz (beşinci tur)
        elif has("kalsin", "olumsuz") and not (has("harf", "olcu", "cati", "dis", "d140") or sayilar) and (degismez or not has("sifat")):
            r["tur"] = "bos"                               # "banyo kalsın": değişiklik yok
        elif has("harf", "sifat", "olcu", "cati", "dis", "d140") or sayilar:
            r["tur"] = "baska"                             # odanın kendisine istek ("veranda L olsun", "mutfak büyük olsun"): otomatik yapılamaz
        else:
            r["tur"] = "belirsiz"; r["neden"] = "oda"      # yalnız oda adı (oda listesi): ilk planda talep bilgisidir
        return r
    if has("dis", "d140"):
        r["tur"] = "bos" if (has("kalsin", "olumsuz") and not has("d140")) else "belirsiz"
        r["neden"] = "dis" if r["tur"] == "belirsiz" else None      # "duvarlar 140 olsun", "dış duvarlar kalın olsun"
        return r
    if has("cati", "harf", "sifat", "olcu"):
        r["tur"] = "bos" if has("kalsin", "olumsuz") else "belirsiz"
        r["neden"] = "genel" if r["tur"] == "belirsiz" else None   # "büyük olsun", "modeli": revizyonda sorulur
        return r
    r["tur"] = "bos"
    return r


def _pencere_okumasi(p: dict, t: dict, y: dict | None, onceki_adaylar: list[dict] | None = None) -> dict:
    """Pencere cümlesinin adayları ve ölçüsü: oda, cephe, vasistas ve eski ölçü süzgeçleri; iki ölçüde eski → yeni."""
    adaylar = list(onceki_adaylar if onceki_adaylar is not None else pencere_adaylari(t, y))
    suzgec = []
    if p.get("vasistas_soz"):
        adaylar = [a for a in adaylar if a["vasistas"]]; suzgec.append("vasistas")
    if p["odalar"]:
        adaylar = [a for a in adaylar if a["mahal"] in p["odalar"]]; suzgec.append("oda")
    if p.get("cepheler"):
        adaylar = [a for a in adaylar if a["cephe"] in p["cepheler"]]; suzgec.append("cephe")
    olc = p.get("_olc") or []
    yeni = None
    belirsiz = False
    if len(olc) == 2:
        eski, yeni = olc[0], olc[1]
        if not any((a["en"], a["yuk"]) == eski for a in adaylar) and any((a["en"], a["yuk"]) == olc[1] for a in adaylar) \
                and not re.search(r"\b(yerine|olan|iken|idi|di|den|dan|dir)\b", norm(p["metin"])):
            eski, yeni = olc[1], olc[0]
        adaylar = [a for a in adaylar if (a["en"], a["yuk"]) == eski] or adaylar; suzgec.append("eski_olcu")
    elif len(olc) == 1:
        yeni = olc[0]
    elif len(olc) > 2:
        belirsiz = True                                         # üç ve daha çok ölçü: hangisi hangisi, sorulur
    return {"istek": True, "metin": p["metin"], "olcu": yeni, "adaylar": adaylar, "suzgec": suzgec, "mahaller": p["odalar"],
            "cepheler": p.get("cepheler") or [], "olumsuz": bool(p["olumsuz"]), "ekle_kaldir": False, "belirsiz": belirsiz,
            "odalar": sorted({a["mahal"] for a in pencere_adaylari(t) if a["mahal"]})}


def oku(metin: str | None, t: dict, katalog_aday: dict | None = None, ipucu: bool = False, y: dict | None = None) -> dict:
    """Bayinin mesajından çelik revizyon okumaları, cümle cümle. `katalog_aday`: çatı varyantları olan katalog modeli kaydı (`varyantlar`).
    `ipucu`: LLM pencere değişikliği gördü (yalnız bayrak; okuma yine bayinin sözünden). Dönen sözlükte `pencere` ilk pencere okumasıdır."""
    parcalar = [parca_oku(p, t, katalog_aday, y) for p in _parcalar(metin, t.get("mahaller"))]
    r = {"parcalar": parcalar, "pencereler": [], "pencere": None, "cati": None, "cati_belirsiz": False, "dis140": False,
         "baska": [], "belirsiz": [], "olumsuz": [], "ekle_kaldir": [], "ipucu": bool(ipucu), "istek": False}
    catilar = []
    for p in parcalar:
        if p["tur"] == "baska":
            r["baska"].append(p["metin"])
        elif p["tur"] == "belirsiz":
            r["belirsiz"].append(p["metin"])
        elif p["tur"] == "ekle_kaldir":
            r["ekle_kaldir"].append(p["metin"])
            r["pencereler"].append({**_pencere_okumasi({**p, "_olc": olculer(p["metin"])}, t, y), "ekle_kaldir": True})
        elif p["tur"] in ("pencere", "cati", "dis140") and p["olumsuz"]:
            r["olumsuz"].append(p["metin"])
            if p["tur"] == "pencere":
                r["pencereler"].append({**_pencere_okumasi(p, t, y), "olumsuz": True})
        elif p["tur"] == "dis140":
            r["dis140"] = True
        elif p["tur"] == "cati":
            if p.get("kod"):
                catilar.append(p["kod"])
            else:
                r["cati_belirsiz"] = True
        elif p["tur"] == "pencere":
            po = _pencere_okumasi(p, t, y)
            if po["belirsiz"]:
                p["tur"], p["neden"] = "belirsiz", "olcu"      # üç ve daha çok ölçü
                r["belirsiz"].append(p["metin"])
            else:
                r["pencereler"].append(po)
    taban = norm(str(katalog_aday["kod"])) if katalog_aday and katalog_aday.get("kod") else None
    if len(set(catilar)) == 1 and len(cati_secenekleri(metin, t.get("mahaller"), taban)) <= 1:
        r["cati"] = catilar[0]
    elif catilar:
        r["cati_belirsiz"] = True                               # iki ayrı çatı ("çatı L olsun, katalog çatısı mı olsa?"): seçim değil
    # (geometri hakemi dördüncü tur: burada `cati_belirsiz` yeniden False yazılıyordu; iki harfli çatı cümlesi başka bir değişiklikle
    # birlikte gelince sessizce düşüyordu. Döngünün koyduğu belirsizlik silinmez.)
    r["pencere"] = r["pencereler"][0] if r["pencereler"] else None
    r["istek"] = bool(r["pencereler"] or r["cati"] or r["dis140"] or r["ekle_kaldir"] or r["olumsuz"] or r["cati_belirsiz"])
    return r


def cati_okumasi(metin: str | None, katalog_aday: dict | None, mahaller: list[dict] | None = None) -> str | None:
    """Mesajda tek ve olumsuz olmayan bir çatı cümlesi varsa onun varyant kodu ("çatı L olsun", "Ç8801 L", "katalog çatısı", "çatıyı K'dan
    L'ye çevirelim"); "veranda L olsun" çatı değildir (tanınmayan sözcük). Mesajda iki ayrı çatı seçeneği geçiyorsa seçim yok (katalog
    çatısı da seçenektir: "Ç8801K mi katalog çatısı mı?"). Model tanımı gerekmez (yalnız varyant listesi; `mahaller` cümle bölmeyi tanıtır)."""
    if not katalog_aday or not katalog_aday.get("varyantlar"):
        return None
    if len(cati_secenekleri(metin, mahaller, norm(str(katalog_aday.get("kod") or "")) or None)) > 1:
        return None                                             # mesajda iki ayrı çatı geçiyor: seçim değil (sorulur ya da set sunulur)
    t = {"mahaller": mahaller or []}
    kodlar = {p.get("kod") for p in (parca_oku(x, t, katalog_aday) for x in _parcalar(metin, mahaller))
              if p["tur"] == "cati" and p.get("kod") and not p["olumsuz"]}
    return next(iter(kodlar)) if len(kodlar) == 1 else None


def degisiklik_var(metin: str | None) -> bool:
    """Metinde pencere, dış 140 ya da ekleme/kaldırma cümlesi var mı (çatı sorusu ya da seçimi değil)? Set sunulurken "isteğinizi seçtiğiniz
    plana işleyeceğim" notu yalnız bunda yazılır (geometri hakemi üçüncü tur: "çatı nasıl olacak?" için de yazılıyordu)."""
    return any(parca_oku(x, {}, None)["tur"] in ("pencere", "dis140", "ekle_kaldir") for x in _parcalar(metin))


def hizli_istek(metin: str | None) -> bool:
    """LLM niyeti ne derse desin, metin çelik revizyon isteği taşıyor mu (ölçü, pencere sözü, çatı K/L, dış 140)? Model tanımı olmadan
    (oda adları bilinmeden) cümle sınıflaması: pencere, çatı, dış 140, ekleme/kaldırma ya da olumsuz pencere cümlesi."""
    if olculer(metin):
        return True
    return any(parca_oku(x, {}, None)["tur"] in ("pencere", "dis140", "ekle_kaldir", "cati") for x in _parcalar(metin))


def _cevap_odalari(metin_n: str, bekleyen: dict) -> list[str]:
    return _odalar(metin_n, bekleyen.get("mahaller_t") or [])[0] if bekleyen.get("mahaller_t") else []


def okuma_cevabi(metin: str | None, bekleyen: dict) -> dict | None:
    """Askıdaki okuma sorusunun cevabı.
    bekleyen.tur == "secim": {"secimler": [i, …]} (0 tabanlı; "1", "ikinci", "1 ve 3", "ikisi de", "hepsi") | {"hicbiri": True} | None.
    bekleyen.tur == "olcu": {"olcu": (en, yük)} | {"hicbiri": True} | None (başka odanın adı geçiyorsa cevap değildir, yeni istektir).
    Buton kimliği q:okuma:<n> aynı metne çevrilir ("1", "2", "hiçbiri"). Sayı, "yok/hayır" sözünden önce okunur ("2 olsun sorun yok")."""
    q = norm(metin)
    if not q:
        return None
    soz = q.split()
    n = len(bekleyen.get("adaylar") or [])
    if bekleyen.get("tur") == "olcu":
        olc = olculer(metin)
        odalar = _cevap_odalari(q, bekleyen)
        bekleyen_odalar = {a.get("mahal") for a in bekleyen.get("adaylar") or [] if isinstance(a, dict)}
        if odalar and not set(odalar) <= bekleyen_odalar:
            return None                                         # başka oda: yeni istek ("yok yok, banyo penceresi 120x50")
        if len(olc) == 1:
            return {"olcu": olc[0]}
        if len(olc) == 2:                                       # "120x180 yerine 120x120": biri bekleyen pencerenin ölçüsüyse öteki yenidir
            mevcut = {(a.get("en"), a.get("yuk")) for a in bekleyen.get("adaylar") or [] if isinstance(a, dict)}
            yeni = [o for o in olc if o not in mevcut]
            return {"olcu": yeni[0]} if len(yeni) == 1 else None
        if not olc and len(soz) <= 4 and (_HICBIRI.search(" " + q + " ") or any(_OLUMSUZ_T.fullmatch(s) for s in soz)):
            return {"hicbiri": True}
        return None
    if len(soz) > 6 or olculer(metin):
        return None                                             # ölçü taşıyan cevap yeni istektir ("hepsi 120x180 olsun")
    if _HICBIRI.search(" " + q + " "):
        return {"hicbiri": True}
    if _HEPSI.search(" " + q + " ") and n >= 2 and not re.search(r"\bdegil", q):
        if re.search(r"\biki", q) and n != 2:
            return None                                         # "ikisi de" ama aday iki değil
        return {"secimler": list(range(n))}
    secim: list[int] = []
    for w in soz:
        m = re.fullmatch(r"(\d)(?:inci|nci|uncu|unci|incisi|ncisi|lu|li)?", w)
        if m:
            secim.append(int(m.group(1)) - 1)
        elif w in _SAYI_SOZ:
            secim.append(_SAYI_SOZ[w] - 1)
        elif w not in _CEVAP_DOLGU:
            return None
    secim = sorted(set(secim))
    if secim and all(0 <= i < n for i in secim):
        return {"secimler": secim}
    if not secim and any(w in ("yok", "hayir") for w in soz):
        return {"hicbiri": True}
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
