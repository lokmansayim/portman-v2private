"""İE-20 PR-2 · Talep formu ve revizyon formu (WhatsApp Flow, uç noktasız; Kurulum Panosu satır 110 ve 61).

Formlar `kanal/formlar/talep.json` ve `revizyon.json` (Flow JSON 7.3). Meta'da bir kez kurulur (WhatsApp Manager › Flows; önce taslak
kipinde, yalnız Patron telefonunda, Lokman'ın onayıyla); kimlikleri ayara yazılır (`talep_formu.talep_flow_id`, `revizyon_flow_id`).
  - Sunuş (`kanal/worker.py`): eksik bilgi sorusu, selam, "anlayamadım" ve "Nasıl çalışır?" cevabı aynı metinle [Talep formu] düğmeli
    gider; "Neyi değiştirelim?" [Revizyon formu] düğmeli. Ek mesaj yok: düğme sorunun kendisinde; yazıyla cevap yolu açık kalır.
    Talep formu bayi kartının varsayılanları (yapı, kat, çatı, veranda; panel) ve açık taslaktaki bilgilerle dolu açılır (`ekran_verisi`).
  - Cevap (`nfm_reply`): webhook `cevap_ozeti` ile kuyruk satırına `form` yazar; satırın metni panel için özettir (`metin`); formdaki
    dosya gelen dosya kaydı olur, gönderici indirir. Talep formu LLM'siz talebe çevrilir (`talep`); dosyası PR-1'in okumasından geçer.
    Revizyon formunun açıklaması bayinin yazısı gibi okunur (bugünkü yol).
Sır ve numara tutmaz; ağ yok. Bayinin notu LLM'e gitmez (talepte özel istek olarak durur, numara maskeli).

İE-20 PR-6 · Prefabrik talep formu (`kanal/formlar/prefabrik.json`, iki ekran; Lokman, 13 Kasım 2026 06:12 ve 21:26 UTC):
  - Yapı tipi, çatı şekli ve veranda sorulmaz (form yalnız prefabrik; çatı plandan sonra seçilir, M-08). İkinci ekranda standart
    özellikler seçili gelir (`STANDART`); bayi değiştirirse seçim talebe `bina_ozellikleri` olarak yazılır (`OZELLIK_ADI`).
  - Ölçü (`olcu_hesabi`): kısa kenar 20 + 62,75 × yarım pano, uzun kenar 10 + 62,75 × yarım pano; en yakın yarım panoya. Bayi tek kenar
    ve m² yazarsa öteki kenarı kod m²'den hesaplar ("bunu motorda kendin hesapla müşteriye bırakma"). Talebe hesaplanan alan yazılır;
    bayiye ölçü `olcu_notu` ile söylenir.
  - Cevabın token'ı `pf:<iz>[:1]`; tür yine `talep`, `form` alanı `prefabrik` (kuyruk satırı ve çözüm yolu aynı).

İE-20 PR-8 · Verandasız talep formu (`kanal/formlar/talep2.json`; D-89; Lokman, 14 Kasım 2026 07:34 ve 07:44 UTC):
  - İlk talep formunun (`talep.json`, yayımlı; değişmez) veranda sorusu olmayan kopyasıdır; öteki alanlar aynı. Veranda ayrıca sorulmaz:
    bir oda gibi sayılır, bayi isterse yazar. Kimliği ayarda varsa (`talep_formu.talep2_flow_id`) ilk formun yerine o sunulur
    (`kanal/worker.py` › `talep_formu_sunusu`); yoksa davranış bugünküyle aynı. Ekran verisi `talep2_ekran_verisi` (veranda yok).
  - Cevabın token'ı ilk formunkiyle aynıdır (`tf:<iz>[:1]`); cevapta veranda olmadığı için talebe veranda yazılmaz.

İE-20 PR-9 · Çelik talep formu (`kanal/formlar/celik.json`, iki ekran; D-93; Lokman, 13 Kasım 2026 21:26 ve 14 Kasım 2026 20:19 UTC;
alan listesi kartı 14 Kasım 2026 20:40 UTC "Evet, bu listeyle kur"):
  - Yapı tipi, çatı şekli ve veranda sorulmaz (form yalnız çelik; çatı plan onayından sonra görselle seçilir). İkinci ekranda çeliğin
    standartları seçili gelir (`C_STANDART`). Çatı rengi her zaman, öteki seçimler standarttan ayrıldıysa talebe `bina_ozellikleri`
    olarak yazılır (`beyin/celik.zarf`: renk pafta tablosuna, ötekiler özel isteğe). Dış duvar 140 mm karkas çizime işlenir
    (`dis140`; `beyin/karar._celik_is_emri_uret`, işlem `dis_karkas_140`).
  - Ölçü pano katına yuvarlanmaz (çelik serbest aks; varsayım, D-93): bayinin ölçüsü kalır. Tek kenar ve m² yazılıysa öteki kenarı kod
    m²'den hesaplar (`celik_olcusu`). Kimliği ayarda varsa (`talep_formu.celik_flow_id`) çelikte ilk formun yerine o sunulur.
  - Cevabın token'ı `cf:<iz>[:1]`; tür yine `talep`, `form` alanı `celik`.
İE-20 PR-12 · Çelik talep formunun ikinci sürümü (`kanal/formlar/celik2.json`; D-102; Lokman, 15 Kasım 2026 05:23 ve 05:28 UTC):
  - Yayımlı form değişmez; `celik2.json` onun kopyasıdır: çatı kaplamasında "Trapez sac" yok (çelikte sunulmaz), shingle satırı
    "OSB + membran + shingle". Kimliği ayarda varsa (`talep_formu.celik2_flow_id`) çelik formun yerine o sunulur
    (`kanal/worker.py` › `talep_formu_sunusu`); yoksa davranış bugünküyle aynı. Token, ekran verisi ve cevabın okunması aynıdır;
    eski formdan gelen "trapez" cevabı okunmaya devam eder (`C_KAPLAMA`)."""
from __future__ import annotations

import json
import re
from pathlib import Path

FORMLAR = Path(__file__).resolve().parent / "formlar"
EKRAN = {"talep": "TALEP", "revizyon": "REVIZYON", "prefabrik": "TALEP_P", "talep2": "TALEP", "celik": "TALEP_C", "celik2": "TALEP_C"}
DUGME = {"talep": "Talep formu", "revizyon": "Revizyon formu", "prefabrik": "Talep formu", "talep2": "Talep formu",
         "celik": "Talep formu", "celik2": "Talep formu"}                 # flow_cta (≤ 20)
# tf:<iz>[:1] talep · pf:<iz>[:1] prefabrik talep formu · cf:<iz>[:1] çelik talep formu · rv:<İş Emri no>:<rev> revizyon
TOKEN = re.compile(r"^(tf|pf|cf|rv):([^:\s]{1,80})(?::([0-9]{1,3}))?$")
TOKEN_FORMU = {"pf": "prefabrik", "cf": "celik"}  # token öneki → cevabın `form` alanı (ilk form ve verandasız form: alan yok)
FLOW_ID = re.compile(r"^[0-9]{1,40}$")
MEDYA_ID = re.compile(r"^[0-9]{1,40}$")
CEVAP_EN_COK = 64 * 1024                       # response_json (dize) üst sınırı
NOT_EN_COK = 600
YAPI = {"prefabrik": "prefabrik", "celik": "çelik"}
KAT = {"1": "tek kat", "2": "iki kat"}
ODA = ("1+0", "1+1", "2+1", "3+1", "4+1", "5+1")
CATI = {"besik": "beşik çatı", "tek_egimli": "tek eğimli çatı", "kirma": "kırma çatı", "teras": "teras çatı"}
VERANDA = {"on": "önde", "yan": "yanda", "arka": "arkada", "kose": "köşede"}
NEYI = {"oda": "oda yerleşimi", "pencere": "pencere", "kapi": "kapı", "veranda": "veranda", "olcu": "ölçü", "cati": "çatı"}
# Kartta varsayılan yoksa formun seçili geleceği değer (bayi değiştirebilir). Veranda "on": ilk talep formunda (`talep.json`, yayımlı)
# veranda zorunlu sorudur ve "Yok" seçeneği yoktur; bu yüzden bir değer seçili gelir. Bu bir kural değildir: Lokman, 14 Kasım 2026
# 07:34 UTC: "Verandasız teklif olmaz diye bir şey söylemedim veranda ayrıca var mı yok mu belirtilmez verandayı da bir oda gibi kabul
# et". Prefabrik formda veranda sorusu yok (D-88). İlk formdaki soru yeni formla kalkar (yayımlı form değişmez); karar Lokman'da.
SABIT_VARSAYILAN = {"yapi": "prefabrik", "kat": "1", "cati": "besik", "veranda": "on"}
KART_ALANLARI = {"yapi_turu": ("yapi", YAPI), "kat_sayisi": ("kat", KAT), "cati": ("cati", CATI), "veranda": ("veranda", VERANDA)}

# ── Prefabrik talep formu (İE-20 PR-6). Kimlikler formun `data-source` kimlikleridir; yazılar Portman Sözlüğü'nün terimleri. ──
ONCELIK = {"butce": "bütçe", "yasam": "yaşam alanı", "montaj": "kısa montaj", "yok": "fark etmez"}   # `karar` taslağındaki `oncelik` değerleri
KAPLAMA = {"trapez": "trapez sac", "kiremit": "kiremit desen sac + OSB + nem bariyeri", "tek_kat": "tek kat panel",
           "shingle": "shingle + OSB + membran", "sandvic": "sandviç panel"}        # D-74 (M-16): standart trapez sac, dördü opsiyon
CATI_RENGI = {"antrasit": "antrasit gri", "kirmizi": "kırmızı (RAL 3009)"}
YUKSEKLIK = {"250": "250 cm", "280": "280 cm", "300": "300 cm"}                     # pano yüksekliği (D-12, D-14)
DIS_DUVAR = {"100": "100 mm", "160": "160 mm"}
IC_DUVAR = {"60": "60 mm", "100": "100 mm"}
TAVAN = {"asma": "alçıpan asma tavan", "ters": "ters tavan"}
PENCERE_RENGI = {"beyaz": "beyaz", "antrasit": "antrasit gri"}
EK = {"alcipan": "iç duvarlarda alçıpan kaplama", "lata": "H profilde lata, köşelerde yalı baskı", "cift_yun": "çatıda çift kat mineral yün"}
# Formun ikinci ekranındaki seçimler: alan → (izinli değerler, talepteki `bina_ozellikleri` anahtarı). Sıra bayiye okunan sıradır.
OZELLIKLER = {"kaplama": (KAPLAMA, "Çatı Kaplaması"), "cati_rengi": (CATI_RENGI, "Çatı Kaplama Rengi"),
              "yukseklik": (YUKSEKLIK, "Pano Yüksekliği"), "dis_duvar": (DIS_DUVAR, "Dış Duvar"), "ic_duvar": (IC_DUVAR, "İç Duvar"),
              "tavan": (TAVAN, "Tavan"), "pencere_rengi": (PENCERE_RENGI, "Pencere Rengi")}
OZELLIK_ADI = {"kaplama": "çatı kaplaması", "cati_rengi": "çatı rengi", "yukseklik": "pano yüksekliği", "dis_duvar": "dış duvar",
               "ic_duvar": "iç duvar", "tavan": "tavan", "pencere_rengi": "pencere rengi"}
# Formda seçili gelen standartlar (Lokman, 13 Kasım 2026 21:26 UTC: "Çatı rengi standardı Antrasit gri gir, Pencere rengi standardı Beyaz";
# çatı kaplaması D-74; 250 / 100 / 60 `kurallar/teklif/form.json › standart`; asma tavan Patron, 27 Ekim 2026).
STANDART = {"kaplama": "trapez", "cati_rengi": "antrasit", "yukseklik": "250", "dis_duvar": "100", "ic_duvar": "60", "tavan": "asma",
            "pencere_rengi": "beyaz"}
EK_OZELLIK = "Ek İstekler"                                                            # `bina_ozellikleri` anahtarı (EK yazıları, "; " ile)
# ── Çelik talep formu (İE-20 PR-9, D-93). Kimlikler `celik.json`'un `data-source` kimlikleri. Seçenekler: çatı kaplaması kural kitabının
# altı kaplaması (`kurallar/liste/kurallar.json` › cati_kaplamasi); dış duvar `kurallar/model/duvar_tipleri.json` (DIS-80 baz, DIS-140
# seçenek); iç duvar, pencere rengi ve ek istek bayi tekliflerinin taramasından (19 çelik proje). ──
C_KAPLAMA = {"tek_kat": "tek kat panel", "sandvic": "sandviç panel", "kiremit": "kiremit desen sac + OSB", "trapez": "trapez sac",
             "osb_trapez": "trapez sac + OSB", "shingle": "OSB + membran + shingle"}   # "trapez": yalnız eski formun cevabı (D-102)
# Form seçeneği → kural kitabının `cati_kaplama` anahtarı (İE-20 PR-11, D-97). Genel motorun hesapladığı kaplama (`beyin/varyant.
# CIZILEN_KAPLAMALAR`) ilk planda çizime işlenir; ötekiler özel isteğe yazılır.
C_KAPLAMA_KITAP = {"tek_kat": "tek_kat_panel", "sandvic": "sandvic_panel", "kiremit": "osb_kiremit", "trapez": "trapez_sac",
                   "osb_trapez": "osb_trapez", "shingle": "osb_shingle"}
C_DIS_DUVAR = {"80": "80 mm karkas", "140": "140 mm karkas"}
C_IC_DUVAR = {"alcipan": "alçıpan + 80 mm karkas", "osb": "OSB'li iç duvar"}
C_EK = {"cift_yalitim": "çatıda çift kat yalıtım"}
# alan → (izinli değerler, talepteki `bina_ozellikleri` anahtarı; None: talebe yazılmaz, çizime işlenir). Sıra bayiye okunan sıradır.
# Anahtarlar çelik pafta tablosunun satır adlarıdır (`beyin/celik.OZELLIK_ALANLARI`): "Çatı Kaplama Rengi" tabloya yazılır; "Çatı
# Kaplaması" ve "İç Duvarlar" çizimden hesaplanan satırlardır, bayinin seçimi özel isteğe gider; "Pencere Rengi" tabloda yoktur, o da.
C_OZELLIKLER = {"kaplama": (C_KAPLAMA, "Çatı Kaplaması"), "cati_rengi": (CATI_RENGI, "Çatı Kaplama Rengi"), "dis_duvar": (C_DIS_DUVAR, None),
                "ic_duvar": (C_IC_DUVAR, "İç Duvarlar"), "pencere_rengi": (PENCERE_RENGI, "Pencere Rengi")}
C_OZELLIK_ADI = {"kaplama": "çatı kaplaması", "cati_rengi": "çatı rengi", "dis_duvar": "dış duvar", "ic_duvar": "iç duvar",
                 "pencere_rengi": "pencere rengi"}
# Formda seçili gelen çelik standartları: çatı kaplaması tek kat panel (Lokman, 4 Ekim 2026 01:42; kitabın `baz_paket_cati_kaplamasi`),
# dış duvar 80 mm karkas ve iç duvar alçıpan + 80 mm karkas (kitabın DIS-80 ve IC-80 tipleri). Çatı rengi antrasit gri ve pencere rengi
# beyaz VARSAYIMDIR (prefabrik standardından alındı; Lokman alan listesi kartıyla kabul etti, 14 Kasım 2026 20:40 UTC; D-93).
C_STANDART = {"kaplama": "tek_kat", "cati_rengi": "antrasit", "dis_duvar": "80", "ic_duvar": "alcipan", "pencere_rengi": "beyaz"}
FORM_SECIMLERI = {"prefabrik": (OZELLIKLER, EK), "celik": (C_OZELLIKLER, C_EK)}     # form → ikinci ekranın (seçimleri, ek istekleri)
C_ISLENEMEZSE = "İşleyemezsem plan mesajında yazarım."                              # dış 140 her plana işlenemez; ön not kesin söz vermez
C_HER_ZAMAN = ("cati_rengi",)                                                       # standart da olsa talebe yazılan seçim (pafta tablosunun satırı)
MODUL_CM = 125.5                                                                    # pano modülü; yarım pano 62,75 cm
KOSE_KISA_CM, KOSE_UZUN_CM = 20.0, 10.0                                             # kısa kenarda 20, uzun kenarda 10 cm köşe payı
KENAR_EN_COK_M = 40.0                                                               # bundan büyük kenar santimetre sayılır (700 → 7 m)


def tanim(tur: str) -> dict:
    return json.loads((FORMLAR / f"{tur}.json").read_text(encoding="utf-8"))


def talep_tokeni(iz: str, taslaktan: bool = False) -> str:
    """Form açık taslağın bilgileriyle dolu sunulduysa `tf:<iz>:1` (cevabı taslağı tamamlar), değilse `tf:<iz>` (cevabı açık taslağı
    kapatır: bayi görmediği bilgiyle plan çizilmez)."""
    return f"tf:{iz}:1" if taslaktan else f"tf:{iz}"


def revizyon_tokeni(no: str, rev: int) -> str:
    return f"rv:{no}:{int(rev)}"


def _dize(v, n: int) -> str:
    return " ".join(str(v if v is not None else "").split())[:n]


def sayi(v) -> float | None:
    """"7,5" / "7.5" / 7.5 → 7.5; boş, sıfır, eksi ya da 1000'den büyükse None (ölçü uydurulmaz)."""
    s = str(v if v is not None else "").strip().replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    return x if 0 < x <= 1000 else None


def _dosyalar(v) -> list[dict]:
    out = []
    for d in (v if isinstance(v, list) else [])[:10]:            # Meta: bir cevapta en çok 10 dosya
        if isinstance(d, dict) and MEDYA_ID.match(str(d.get("id") or "")):
            out.append({"id": str(d["id"]), "file_name": _dize(d.get("file_name"), 200) or None, "mime_type": _dize(d.get("mime_type"), 100) or None,
                        "sha256": _dize(d.get("sha256"), 100) or None})
    return out


def cevap_ozeti(rj) -> dict:
    """nfm_reply.response_json (dize ya da sözlük) → {tur: talep | revizyon | bilinmiyor, token, alanlar, dosyalar}. Tanınmayan alan atılır."""
    if isinstance(rj, str):
        try:
            rj = json.loads(rj[:CEVAP_EN_COK]) if len(rj) <= CEVAP_EN_COK else None
        except ValueError:
            rj = None
    rj = rj if isinstance(rj, dict) else {}
    token = _dize(rj.get("flow_token"), 120)
    m = TOKEN.match(token)
    tur = {"tf": "talep", "pf": "talep", "cf": "talep", "rv": "revizyon"}.get(m.group(1)) if m else "bilinmiyor"
    a: dict = {}
    if tur == "talep" and m.group(1) in TOKEN_FORMU:
        form = TOKEN_FORMU[m.group(1)]
        return {"tur": tur, "form": form, "token": token, "alanlar": _form_alanlari(rj, form), "dosyalar": _dosyalar(rj.get("dosya"))}
    if tur == "talep":
        for ad, izinli in (("yapi", YAPI), ("kat", KAT), ("oda", ODA), ("cati", CATI), ("veranda", VERANDA)):
            v = _dize(rj.get(ad), 20)
            if v in izinli:
                a[ad] = v
        for ad in ("alan", "en", "boy"):
            if sayi(rj.get(ad)) is not None:
                a[ad] = sayi(rj.get(ad))
        if _dize(rj.get("not"), NOT_EN_COK):
            a["not"] = str(rj.get("not")).strip()[:NOT_EN_COK]
    elif tur == "revizyon":
        neyi = rj.get("neyi") if isinstance(rj.get("neyi"), list) else []
        a["neyi"] = [x for x in NEYI if x in {str(y) for y in neyi}]
        if _dize(rj.get("aciklama"), NOT_EN_COK):
            a["aciklama"] = str(rj.get("aciklama")).strip()[:NOT_EN_COK]
    return {"tur": tur, "token": token, "alanlar": a, "dosyalar": _dosyalar(rj.get("dosya"))}


def _form_alanlari(rj: dict, form: str) -> dict:
    """İki ekranlı talep formunun (prefabrik, çelik) cevabı → tanınan alanlar. İzinli olmayan değer atılır; boş seçim standart sayılmaz
    (alan yazılmaz). İkinci ekranın seçimleri forma göre (`FORM_SECIMLERI`)."""
    ozellikler, ekler = FORM_SECIMLERI[form]
    a: dict = {}
    for ad, izinli in (("kat", KAT), ("oda", ODA), ("oncelik", ONCELIK), *((ad, v[0]) for ad, v in ozellikler.items())):
        v = _dize(rj.get(ad), 20)
        if v in izinli:
            a[ad] = v
    for ad in ("alan", "en", "boy"):
        if sayi(rj.get(ad)) is not None:
            a[ad] = sayi(rj.get(ad))
    ek = rj.get("ek") if isinstance(rj.get("ek"), list) else []
    if [x for x in ekler if x in {str(y) for y in ek}]:
        a["ek"] = [x for x in ekler if x in {str(y) for y in ek}]
    for ad, n in (("musteri", 80), ("il", 40), ("ilce", 40)):
        if _dize(rj.get(ad), n):
            a[ad] = _dize(rj.get(ad), n)
    if _dize(rj.get("not"), NOT_EN_COK):
        a["not"] = str(rj.get("not")).strip()[:NOT_EN_COK]
    return a


def pano(metre: float, kose_cm: float) -> float:
    """Metre → pano adedi, en yakın yarım panoya (`beyin/karar.pano_sayisi` ile aynı hesap; burada Motor içe aktarılmaz)."""
    return round(max(1.0, (float(metre) * 100 - kose_cm) / MODUL_CM) * 2) / 2


def _kenar(v) -> float | None:
    """Formdaki kenar (metre). 40'tan büyük değer santimetre sayılır (700 → 7 m); yine büyükse ölçü yok sayılır (uydurulmaz)."""
    x = sayi(v)
    if x is not None and x > KENAR_EN_COK_M:
        x = x / 100
    return x if x is not None and 1 <= x <= KENAR_EN_COK_M else None


def olcu_hesabi(en=None, boy=None, alan=None) -> dict | None:
    """Formdaki ölçü → pano katındaki dış ölçü (Lokman, 13 Kasım 2026 21:26 UTC). Kısa kenar 20 + 62,75 × yarım pano, uzun kenar
    10 + 62,75 × yarım pano; en yakın yarım panoya. İki kenar yazılıysa ikisi yuvarlanır; tek kenar ve m² yazılıysa öteki kenar m²'den
    hesaplanır (7 m + 70 m² → 710,25 × 1014 cm, 5,5 × 8 pano, 72 m²). Yalnız m² ya da yalnız tek kenar varsa None (ölçü uydurulmaz).
    Dönen {nx, ny, en_cm, boy_cm, alan_m2, hesaplanan: "uzun" | "kisa" | None}; nx kısa kenarın, ny uzun kenarın pano adedi."""
    kenarlar = sorted(x for x in (_kenar(en), _kenar(boy)) if x is not None)
    alan = sayi(alan)
    hesaplanan = None
    if len(kenarlar) == 2:
        nx, ny = pano(kenarlar[0], KOSE_KISA_CM), pano(kenarlar[1], KOSE_UZUN_CM)
    elif len(kenarlar) == 1 and alan is not None:
        nx = pano(kenarlar[0], KOSE_KISA_CM)                                        # yazılan kenar kısa kenar sayılır
        ny = pano(alan / ((MODUL_CM * nx + KOSE_KISA_CM) / 100), KOSE_UZUN_CM)
        hesaplanan = "uzun"
        if ny < nx:                                                                 # m² küçük: yazılan kenar uzun kenarmış
            ny = pano(kenarlar[0], KOSE_UZUN_CM)
            nx = min(ny, pano(alan / ((MODUL_CM * ny + KOSE_UZUN_CM) / 100), KOSE_KISA_CM))
            hesaplanan = "kisa"
    else:
        return None
    en_cm, boy_cm = MODUL_CM * nx + KOSE_KISA_CM, MODUL_CM * ny + KOSE_UZUN_CM
    return {"nx": nx, "ny": ny, "en_cm": en_cm, "boy_cm": boy_cm, "alan_m2": round(en_cm * boy_cm / 1e4, 2), "hesaplanan": hesaplanan}


def _tr(x: float, hane: int = 2) -> str:
    return f"{x:.{hane}f}".replace(".", ",")


def _pano_yazisi(n: float) -> str:
    return f"{n:g}".replace(".", ",")


def olcu_yazisi(o: dict) -> str:
    """"7,10 × 10,14 m (5,5 × 8 pano), 72 m²" (metre iki hane; alan tam m²)."""
    return (f"{_tr(o['en_cm'] / 100)} × {_tr(o['boy_cm'] / 100)} m ({_pano_yazisi(o['nx'])} × {_pano_yazisi(o['ny'])} pano), "
            f"{round(o['alan_m2']):d} m²")


def prefabrik_olcusu(oz: dict) -> dict | None:
    a = oz.get("alanlar") or {}
    return olcu_hesabi(a.get("en"), a.get("boy"), a.get("alan")) if oz.get("form") == "prefabrik" else None


def standart_disi(oz: dict) -> list[str]:
    """Bayinin standarttan ayırdığı seçimler, bayiye okunacak yazılarıyla ("pano yüksekliği 280 cm", "iç duvar 100 mm", ek istekler)."""
    a = oz.get("alanlar") or {}
    out = [f"{OZELLIK_ADI[ad]} {izinli[a[ad]]}" for ad, (izinli, _) in OZELLIKLER.items() if a.get(ad) and a[ad] != STANDART[ad]]
    return out + [EK[x] for x in a.get("ek") or []]


def olcu_notu(oz: dict, olcu: bool = True) -> str:
    """Prefabrik formun cevabından sonra bayiye gidecek ön not: pano katına yuvarlanan dış ölçü ve standart dışı seçimler. Ölçü ve
    seçim yoksa boş. `olcu` False ise ölçü cümlesi yazılmaz (yönlendirme metni ölçüyü kendisi söyler). Dış duvar 160 mm hazır planlarda
    çizilmez (`beyin/form_ozellik`): bayiye açıkça söylenir. Sade Teknik Türkçe (D-70): bir cümle bir iş."""
    if oz.get("form") != "prefabrik":
        return ""
    o, p = prefabrik_olcusu(oz), []
    if o and olcu:
        ek = {"uzun": " Uzun kenarı m²'den hesapladım.", "kisa": " Kısa kenarı m²'den hesapladım."}.get(o["hesaplanan"], "")
        p.append(f"Ölçüyü pano katına yuvarladım: {olcu_yazisi(o)}.{ek}")
    sd = standart_disi(oz)
    if sd:
        p.append("Standart dışı seçimleriniz talebe yazıldı: " + ", ".join(sd) + ".")
    if (oz.get("alanlar") or {}).get("dis_duvar") == "160":
        p.append("Dış duvar 160 mm çizimde gösterilmez; çizim 100 mm duvarla hazırlanır.")
    return " ".join(p)


def set_basligi(oz: dict) -> str:
    """Seçenek görselinin başlığı (≤ 60): "Prefabrik, tek kat, 2+1, 72 m²"; çelik formda "Çelik, tek kat, 2+1, 88 m²"."""
    a = oz.get("alanlar") or {}
    if oz.get("form") == "celik":
        m2 = celik_alani(oz)
        return ", ".join(x for x in ("Çelik", KAT.get(a.get("kat")), a.get("oda"), f"{_olcu(m2)} m²" if m2 else None) if x)[:60]
    o = prefabrik_olcusu(oz)
    m2 = f"{round(o['alan_m2']):d} m²" if o else (f"{_olcu(a['alan'])} m²" if a.get("alan") else None)
    return ", ".join(x for x in ("Prefabrik", KAT.get(a.get("kat")), a.get("oda"), m2) if x)[:60]


# ── Çelik talep formu (İE-20 PR-9, D-93) ──
def celik_olcusu(oz: dict) -> dict | None:
    """Çelik formdaki ölçü → {en_m, boy_m, hesaplanan: "uzun" | "kisa" | None}. Pano katına yuvarlanmaz (çelik serbest aks; D-93,
    varsayım 1): bayinin yazdığı kenar aynen kalır. İki kenar yazılıysa ikisi; tek kenar ve m² yazılıysa öteki kenar m² ÷ kenar
    (santimetreye yuvarlanır). Yalnız m² ya da yalnız tek kenar varsa None (ölçü uydurulmaz)."""
    if oz.get("form") != "celik":
        return None
    a = oz.get("alanlar") or {}
    kenarlar = sorted(x for x in (_kenar(a.get("en")), _kenar(a.get("boy"))) if x is not None)
    alan = sayi(a.get("alan"))
    if len(kenarlar) == 2:
        return {"en_m": kenarlar[0], "boy_m": kenarlar[1], "hesaplanan": None}
    if len(kenarlar) == 1 and alan is not None:
        oteki = round(alan / kenarlar[0], 2)
        if not 1 <= oteki <= KENAR_EN_COK_M:
            return None
        return {"en_m": min(kenarlar[0], oteki), "boy_m": max(kenarlar[0], oteki), "hesaplanan": "uzun" if oteki >= kenarlar[0] else "kisa"}
    return None


def celik_alani(oz: dict) -> float | None:
    """Çelik formun alanı (m²): iki kenar yazılıysa kenarların çarpımı (bir ondalık), yoksa bayinin yazdığı m²."""
    o = celik_olcusu(oz)
    if o and o["hesaplanan"] is None:
        return round(o["en_m"] * o["boy_m"], 1)
    return sayi((oz.get("alanlar") or {}).get("alan"))


def celik_standart_disi(oz: dict) -> list[str]:
    """Bayinin çelik standardından ayırdığı seçimler, bayiye okunacak yazılarıyla ("dış duvar 140 mm karkas", ek istekler)."""
    a = oz.get("alanlar") or {}
    out = [f"{C_OZELLIK_ADI[ad]} {izinli[a[ad]]}" for ad, (izinli, _) in C_OZELLIKLER.items() if a.get(ad) and a[ad] != C_STANDART[ad]]
    return out + [C_EK[x] for x in a.get("ek") or []]


def celik_dis140(oz: dict) -> bool:
    """Çelik formda dış duvar 140 mm karkas seçildi mi (çizime işlenir: `beyin/karar._celik_is_emri_uret`, işlem `dis_karkas_140`)."""
    return oz.get("form") == "celik" and (oz.get("alanlar") or {}).get("dis_duvar") == "140"


def celik_kaplamasi(oz: dict) -> str | None:
    """Çelik formda standart dışı seçilen ve çizime işlenen çatı kaplaması (kural kitabının anahtarı; bugün yalnız sandviç panel).
    Standart seçim (tek kat panel) ve genel motorun hesaplamadığı dört kaplama None: plan modelin kendi kaplamasıyla çizilir, standart
    dışı seçim özel isteğe yazılır (İE-20 PR-11, D-97; `beyin/karar._celik_is_emri_uret`, işlem `cati_kaplamasi`)."""
    from beyin import varyant
    v = (oz.get("alanlar") or {}).get("kaplama") if oz.get("form") == "celik" else None
    k = C_KAPLAMA_KITAP.get(v)
    return k if v != C_STANDART["kaplama"] and k in varyant.CIZILEN_KAPLAMALAR else None


def celik_notu(oz: dict, cizim: bool = True) -> str:
    """Çelik formun cevabından sonra bayiye gidecek ön not: m²'den hesaplanan kenar, standart dışı seçimler ve bunlardan hangisinin
    çizime işlendiği (dış duvar 140 mm karkas ve genel motorun hesapladığı çatı kaplaması; İE-20 PR-11), kısa montaj önceliğinin çelikte
    sıralama ölçüsü olmadığı. Söylenecek şey yoksa boş. `cizim` False ise (talep yönlendirildi ya da plan bu mesajda çıktı) çizim cümlesi
    yazılmaz. Not yazılırken plan henüz seçilmemiştir ve dış 140 her plana işlenemez (KT-01, KT-02): not kesin söz vermez, sonucu plan
    mesajı söyler (İE-20 PR-10, 15 Kasım 2026 canlı denemesi C6). Sade Teknik Türkçe (D-70): bir cümle bir iş."""
    if oz.get("form") != "celik":
        return ""
    a, o, p = oz.get("alanlar") or {}, celik_olcusu(oz), []
    if o and o["hesaplanan"]:
        p.append(f"{'Uzun' if o['hesaplanan'] == 'uzun' else 'Kısa'} kenarı m²'den hesapladım: {_olcu(o['en_m'])} × {_olcu(o['boy_m'])} m.")
    sd = celik_standart_disi(oz)
    d140, kap = celik_dis140(oz), celik_kaplamasi(oz)
    islenen = (["dış duvar 140 mm karkası"] if d140 else []) + (["çatı kaplamasını"] if kap else [])
    if sd and cizim and len(sd) == 1 and islenen:
        p.append(("Dış duvar 140 mm karkas" if d140 else f"Çatı kaplaması {C_KAPLAMA[a['kaplama']]}") + " seçtiniz. Çizime işlerim. "
                 + C_ISLENEMEZSE)
    elif sd:
        p.append("Standart dışı seçimlerinizi aldım: " + ", ".join(sd) + ".")
        if cizim:
            p.append(("Çizime işlerim. " if len(islenen) == len(sd) else f"Çizime yalnız {' ve '.join(islenen)} işlerim. ") + C_ISLENEMEZSE
                     if islenen else "Bu seçimler çizimi değiştirmez.")
    if a.get("oncelik") == "montaj":
        p.append("Çelik planlarda kısa montaj sıralaması yok.")
    return " ".join(p)


def celik_anahtarlari() -> tuple[str, ...]:
    """Çelik formun talebe yazdığı `bina_ozellikleri` anahtarları. Form yeniden gelince bu anahtarların eski değeri taslakta kalmaz
    (`beyin/karar._form_izi`): seçim standarda döndüyse eski standart dışı değer plana taşınmaz."""
    return tuple(anahtar for _, anahtar in C_OZELLIKLER.values() if anahtar) + (EK_OZELLIK,)


def celik_cizim_notu(oz: dict) -> str:
    """Formla gelen dosya plan olarak okunduysa (çizim esas) çelik formun standart dışı seçimleri plana işlenmez; bayiye söylenir
    (sessiz düşmez). Standart dışı seçim yoksa boş."""
    sd = celik_standart_disi(oz) if oz.get("form") == "celik" else []
    return ("Formdaki standart dışı seçimlerinizi plana işlemedim: " + ", ".join(sd) + ". "
            "Planı gördükten sonra değişiklik olarak yazabilirsiniz.") if sd else ""


def celik_onceligi(oz: dict) -> str | None:
    """Çelik formda seçilen sıralama önceliği: butce | yasam; kısa montaj ve "fark etmez" → yok (çelik adaylarda pano sayısı yoktur,
    kısa montajın ölçüsü yok; bayiye `celik_notu` söyler). Form çelik değilse ya da seçim yoksa None."""
    v = (oz.get("alanlar") or {}).get("oncelik") if oz.get("form") == "celik" else None
    return None if v is None else (v if v in ("butce", "yasam") else "yok")


def _olcu(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def ozet(oz: dict) -> str:
    """Talep formunun tek cümlelik özeti ("Talep formu: prefabrik, tek kat, 2+1, 7 × 9 m, beşik çatı, veranda önde")."""
    a = oz.get("alanlar") or {}
    if oz.get("form") == "prefabrik":
        o = prefabrik_olcusu(oz)
        p = ["prefabrik", KAT.get(a.get("kat")), a.get("oda"), f"istenen dış ölçü {olcu_yazisi(o)}" if o else None,
             f"yaklaşık {_olcu(a['alan'])} m²" if a.get("alan") and not o else None, *standart_disi(oz)]
        return "Talep formu: " + ", ".join(x for x in p if x)
    if oz.get("form") == "celik":
        o, m2 = celik_olcusu(oz), celik_alani(oz)
        p = ["çelik", KAT.get(a.get("kat")), a.get("oda"), f"{_olcu(o['en_m'])} × {_olcu(o['boy_m'])} m" if o else None,
             f"yaklaşık {_olcu(m2)} m²" if m2 else None, *celik_standart_disi(oz)]
        return "Talep formu: " + ", ".join(x for x in p if x)
    p = [YAPI[a["yapi"]] if a.get("yapi") else None, KAT.get(a.get("kat")) if a.get("kat") else None, a.get("oda")]
    if a.get("en") and a.get("boy"):
        p.append(f"{_olcu(a['en'])} × {_olcu(a['boy'])} m")
    if a.get("alan"):
        p.append(f"yaklaşık {_olcu(a['alan'])} m²")
    p += [CATI.get(a.get("cati")) if a.get("cati") else None, f"veranda {VERANDA[a['veranda']]}" if a.get("veranda") else None]
    return "Talep formu: " + (", ".join(x for x in p if x) or "boş")


def metin(oz: dict) -> str:
    """Kuyruk satırının metni (panelde görünür; çizim okumasında bayinin sözü). Revizyonda açıklama bayinin yazısıdır."""
    a = oz.get("alanlar") or {}
    dosya = " Dosya eklendi." if oz.get("dosyalar") else ""
    if oz.get("tur") == "talep":
        return ozet(oz) + "." + (f" Not: {a['not']}" if a.get("not") else "") + dosya
    if oz.get("tur") == "revizyon":
        neyi = ", ".join(NEYI[x] for x in a.get("neyi") or [])
        if a.get("aciklama"):
            return a["aciklama"] + (f" (değişecek: {neyi})" if neyi else "") + dosya
        return "Revizyon formu" + (f": {neyi}." if neyi else ".") + dosya
    return "Form cevabı."


def talep(oz: dict) -> dict:
    """Talep formu → Talep (beyin/sema.py) sözlüğü; LLM'siz. Formda olmayan alan boş kalır (karar eksik olanı sorar)."""
    from beyin import numara
    a = oz.get("alanlar") or {}
    t: dict = {"niyet": "yeni_talep", "guven": "yuksek", "ozet": ozet(oz)}
    if oz.get("form") == "prefabrik":
        return _prefabrik_talebi(oz, {**t, "ozet": set_basligi(oz)})   # kısa özet: plan metni ve PDF başlığı; ayrıntı ön notta ve panelde
    if oz.get("form") == "celik":
        return _celik_talebi(oz, {**t, "ozet": set_basligi(oz)})
    if a.get("yapi"):
        t["yapi_turu"] = a["yapi"]
    if a.get("kat"):
        t["kat_sayisi"] = int(a["kat"])
    if a.get("oda"):
        t["oda_programi"] = a["oda"]
    if a.get("alan"):
        t["alan_m2"] = float(a["alan"])
    if a.get("en") and a.get("boy"):
        en, boy = sorted([float(a["en"]), float(a["boy"])])
        t["dis_olcu"] = {"en_m": en, "boy_m": boy}
    if a.get("cati"):
        t["cati"] = {"tip": a["cati"]}
    if a.get("veranda"):
        t["veranda"] = {"istiyor": True, "konum": a["veranda"]}
    if a.get("not"):
        t["ozel_istekler"] = [numara.maskele(a["not"])]
    return t


def _prefabrik_talebi(oz: dict, t: dict) -> dict:
    """Prefabrik talep formu → Talep. Ölçü pano katına yuvarlanır; talebe pano adedi ve o ölçünün alanı yazılır (`beyin/karar`: ikisi
    birlikteyse hazır planlar alana göre sunulur, uyan yoksa ölçüyle yönlendirilir); bayiye ölçü `olcu_notu` ile söylenir. Seçimlerin hepsi `bina_ozellikleri`'ne yazılır
    (standart da: bayi formda gördü ve onayladı; İş Emri'ne `beyin/form_ozellik` işler). Müşteri adı ve teslim yeri `musteri`."""
    from beyin import numara
    a = oz.get("alanlar") or {}
    t["yapi_turu"] = "prefabrik"
    if a.get("kat"):
        t["kat_sayisi"] = int(a["kat"])
    if a.get("oda"):
        t["oda_programi"] = a["oda"]
    o = prefabrik_olcusu(oz)
    if o:
        t["pano"] = {"nx": o["nx"], "ny": o["ny"]}
        t["alan_m2"] = float(round(o["alan_m2"]))
    elif a.get("alan"):
        t["alan_m2"] = float(a["alan"])
    bo = {anahtar: izinli[a[ad]] for ad, (izinli, anahtar) in OZELLIKLER.items() if a.get(ad)}
    if a.get("ek"):
        bo[EK_OZELLIK] = "; ".join(EK[x] for x in a["ek"])
    if bo:
        t["bina_ozellikleri"] = bo
    yer = ", ".join(x for x in (a.get("ilce"), a.get("il")) if x)
    if a.get("musteri") or yer:
        t["musteri"] = {**({"ad": numara.maskele(a["musteri"])} if a.get("musteri") else {}),
                        **({"sevk_adresi": numara.maskele(yer)} if yer else {})}
    if a.get("not"):
        t["ozel_istekler"] = [numara.maskele(a["not"])]
    return t


def _celik_talebi(oz: dict, t: dict) -> dict:
    """Çelik talep formu → Talep. Ölçü yuvarlanmaz: iki kenar (yazılan ya da m²'den hesaplanan) `dis_olcu`, alan `alan_m2` (iki kenar
    yazılıysa çarpımları, yoksa bayinin m²'si). Çatı rengi her zaman, öteki seçimler standarttan ayrıldıysa `bina_ozellikleri`'ne yazılır;
    dış duvar 140 mm karkas talebe yazılmaz, çizime işlenir (`celik_dis140`). Müşteri adı ve teslim yeri `musteri`."""
    from beyin import numara
    a = oz.get("alanlar") or {}
    t["yapi_turu"] = "celik"
    if a.get("kat"):
        t["kat_sayisi"] = int(a["kat"])
    if a.get("oda"):
        t["oda_programi"] = a["oda"]
    o, m2 = celik_olcusu(oz), celik_alani(oz)
    if o:
        t["dis_olcu"] = {"en_m": o["en_m"], "boy_m": o["boy_m"]}
    if m2:
        t["alan_m2"] = float(m2)
    bo = {anahtar: izinli[a[ad]] for ad, (izinli, anahtar) in C_OZELLIKLER.items()
          if anahtar and a.get(ad) and (ad in C_HER_ZAMAN or a[ad] != C_STANDART[ad])}
    if a.get("ek"):
        bo[EK_OZELLIK] = "; ".join(C_EK[x] for x in a["ek"])
    if bo:
        t["bina_ozellikleri"] = bo
    yer = ", ".join(x for x in (a.get("ilce"), a.get("il")) if x)
    if a.get("musteri") or yer:
        t["musteri"] = {**({"ad": numara.maskele(a["musteri"])} if a.get("musteri") else {}),
                        **({"sevk_adresi": numara.maskele(yer)} if yer else {})}
    if a.get("not"):
        t["ozel_istekler"] = [numara.maskele(a["not"])]
    return t


def oncelik(oz: dict) -> str | None:
    """Prefabrik formda seçilen sıralama önceliği (butce | yasam | montaj); seçilmediyse None (soru sohbette sorulur)."""
    return (oz.get("alanlar") or {}).get("oncelik") if oz.get("form") == "prefabrik" else None


def kart_varsayilanlari(bayi: dict | None) -> dict:
    """Bayi kartının form varsayılanları ({yapi, kat, cati, veranda}; panelden, `bayi_varsayilanlari` tablosu); geçersiz değer atılır."""
    v = (bayi or {}).get("varsayilanlar") or {}
    out = {}
    for kolon, (ad, izinli) in KART_ALANLARI.items():
        x = str(v.get(kolon) if v.get(kolon) is not None else "")
        if x in izinli:
            out[ad] = x
    return out


def ekran_verisi(bayi: dict | None, taslak: dict | None) -> dict:
    """TALEP ekranının verisi: açık taslaktaki bilgi > kartın varsayılanı > sabit varsayılan. Değerler dize (Flow JSON `string`)."""
    ts = taslak or {}
    kart = kart_varsayilanlari(bayi)
    d = {**SABIT_VARSAYILAN, **kart, "oda": "", "alan": "", "en": "", "boy": ""}
    if ts.get("yapi_turu") in YAPI:
        d["yapi"] = ts["yapi_turu"]
    if str(ts.get("kat_sayisi") or "") in KAT:
        d["kat"] = str(ts["kat_sayisi"])
    if ts.get("oda_programi") in ODA:
        d["oda"] = ts["oda_programi"]
    if (ts.get("cati") or {}).get("tip") in CATI:
        d["cati"] = ts["cati"]["tip"]
    if (ts.get("veranda") or {}).get("konum") in VERANDA:
        d["veranda"] = ts["veranda"]["konum"]
    if ts.get("alan_m2"):
        d["alan"] = f"{float(ts['alan_m2']):g}"
    o = ts.get("dis_olcu") or {}
    if o.get("en_m") and o.get("boy_m"):
        d["en"], d["boy"] = f"{float(o['en_m']):g}", f"{float(o['boy_m']):g}"
    bilinen = [x for x in (d["oda"] or None, f"{_olcu(float(d['en']))} × {_olcu(float(d['boy']))} m" if d["en"] else None,
                           f"yaklaşık {_olcu(float(d['alan']))} m²" if d["alan"] else None) if x]
    d["bilinen"] = ("Bildiklerim: " + ", ".join(bilinen) + ". " if bilinen else "") + \
        "Bildiğiniz kadarını doldurmanız yeterli; eksik kalanı sohbette sorarım."
    return d


def talep2_ekran_verisi(bayi: dict | None, taslak: dict | None) -> dict:
    """Verandasız talep formunun (`talep2.json`) ekran verisi: `ekran_verisi` ile aynı, veranda yok (formun veri modelinde de yok)."""
    return {k: v for k, v in ekran_verisi(bayi, taslak).items() if k != "veranda"}


def prefabrik_tokeni(iz: str, taslaktan: bool = False) -> str:
    return f"pf:{iz}:1" if taslaktan else f"pf:{iz}"


def prefabrik_ekran_verisi(bayi: dict | None, taslak: dict | None) -> dict:
    """TALEP_P ekranının verisi: açık taslaktaki bilgi > kartın kat varsayılanı > tek kat. Standart özellikler formun kendisinde seçilidir
    (ikinci ekran; `STANDART` ile aynı olduğunu test denetler). Değerler dize."""
    ts = taslak or {}
    d = {"kat": kart_varsayilanlari(bayi).get("kat") or SABIT_VARSAYILAN["kat"], "oda": "", "alan": "", "en": "", "boy": ""}
    if str(ts.get("kat_sayisi") or "") in KAT:
        d["kat"] = str(ts["kat_sayisi"])
    if ts.get("oda_programi") in ODA:
        d["oda"] = ts["oda_programi"]
    if ts.get("alan_m2"):
        d["alan"] = f"{float(ts['alan_m2']):g}"
    o = ts.get("dis_olcu") or {}
    if o.get("en_m") and o.get("boy_m"):
        d["en"], d["boy"] = (f"{float(x):g}" for x in sorted((o["en_m"], o["boy_m"])))
    bilinen = [x for x in (d["oda"] or None, f"{_olcu(float(d['en']))} × {_olcu(float(d['boy']))} m" if d["en"] else None,
                           f"yaklaşık {_olcu(float(d['alan']))} m²" if d["alan"] else None) if x]
    d["bilinen"] = ("Bildiklerim: " + ", ".join(bilinen) + ". " if bilinen else "") + \
        "Bildiğiniz kadarını doldurmanız yeterli; eksik kalanı sohbette sorarım."
    return d


def celik_tokeni(iz: str, taslaktan: bool = False) -> str:
    return f"cf:{iz}:1" if taslaktan else f"cf:{iz}"


def celik_ekran_verisi(bayi: dict | None, taslak: dict | None) -> dict:
    """TALEP_C ekranının verisi: prefabrik formun ilk ekranıyla aynı alanlar (kat, oda, alan, kısa ve uzun kenar; açık taslaktaki bilgi >
    kartın kat varsayılanı > tek kat). Çeliğin standartları formun kendisinde seçilidir (`C_STANDART`)."""
    return prefabrik_ekran_verisi(bayi, taslak)


def etkilesim(tur: str, govde: str, flow_id: str, token: str, veri: dict, taslak_kipi: bool) -> dict:
    """Flow mesajının `interactive` gövdesi (hosting biçimi; kanal/meta_api.etkilesim_yuku yeniden denetler)."""
    p = {"flow_message_version": "3", "flow_token": token, "flow_id": str(flow_id), "flow_cta": DUGME[tur], "flow_action": "navigate",
         "flow_action_payload": {"screen": EKRAN[tur], "data": veri}}
    if taslak_kipi:
        p["mode"] = "draft"                    # Meta: yayımlanmamış (taslak) form; yalnız WhatsApp Manager'daki test numaralarında açılır
    return {"type": "flow", "body": {"text": govde}, "action": {"name": "flow", "parameters": p}}


def satir_tokeni(satir: dict | None) -> str | None:
    """Giden satırın (hosting biçimi) flow_token'ı; flow mesajı değilse None."""
    i = (satir or {}).get("interactive") or {}
    if i.get("type") != "flow":
        return None
    return str(((i.get("action") or {}).get("parameters") or {}).get("flow_token") or "") or None
