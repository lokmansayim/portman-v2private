#!/usr/bin/env python3
"""Ç8801 (katalog modeli: tek kat çelik, 2+1, 88 m²) için Yapı Tanımı 0.5; katalog çatısı ve iki çatı varyantı.

Kaynaklar (PortatifEv arşivi, `Arşiv/TEK KAT ÇELİK/`):
- Plan: tek kat çelik modellerin planlar DWG'sindeki Ç8801 planı (LibreDWG ile DXF'e çevrildi, ezdxf ile okundu: duvar çizgileri,
  pencere ve kapı blokları, ölçüler) ve katalog paftası `Ç8801/PORT-Ç8801.jpg` (aynı plan, ölçü zinciri, mahal alanları).
- Veranda: katalog görselleri `Ç8801/ç_8801_1_R_Photo - 1, 2, 5.jpg`. Verandanın üstünde çatı yok: ahşap pergola ve ahşap korkuluk.
- Çatı: Lokman. 10 Ekim 2026 13:33: "cumba arkaya doğru uzanmıyor uzun kenardaki çatıya girip kalıyor yani kısa kenardaki çatı devam
  ediyor". İki okuma çizilip soruldu; 14:46: "3 modelin de gayet güzel hatta çatı olarak 3'üde olur ... ben 1. versiyonu beğendim ama asıl
  katalogdaki model 2. versiyon". Katalog görseli 2'de doğu cephede saçak kesintisiz görünüyor (1. versiyon gibi); tanım Lokman'ın cevabına göre.
Arşivde bu modelin karkas modeli (SKP), montaj paftası ve yükleme listesi yok. Ad, telefon ve fiyat içermez.

Çatılar (--cati; üçü de aynı plan, saçak 30 cm, saçak kotu 280):
- katalog (2. versiyon; varsayılan, kod Ç8801): ana çatı doğu–batı, iki ucunda kalkan (batı ve doğu); doğu kanadın güney ucu (cumba) güneye
  bakan kalkanla biter, mahyası kuzeye doğru ana çatının güney yüzüne girip biter (iki vadi). Bütün yüzler %33; cumbanın mahyası ana mahyadan
  40 cm alçak.
- K (1. versiyon, kod Ç8801-K): ana çatının batı ucu kalkan, doğu ucu kırma; cumbanın doğu yüzü ile doğu kırması aynı düzlem: doğu cephede
  saçak boydan boya. Bütün yüzler %33.
- L (ilk varsayım, 10 Ekim 13:00; kod Ç8801-L): doğu kanadın mahyası kuzey–güney boydan boya (güneyde ve kuzeyde kalkan), batı bloğun mahyası
  ona aynı kotta bağlanır (iki vadi). Açıklıklar farklı (640 ve 400 cm): batı blok %33, kanat %50,2.
Varyant adları (K, L) geçicidir; model bankasında Lokman verir.

Kullanım: python c8801_tanim_uret.py <çıktı.json> [--cati katalog|K|L]

Koordinat: plan (cm). Köken binanın sol-alt dış köşesi (verandanın güneybatı köşesi); +x doğu, +y kuzey (çizimin üstü kuzey alındı).
DWG'deki koordinattan (60, 29) düşülür. Duvarlar baz paketin katmanlarıyla: dış yüzde 1,25 cm kaplama, 8 cm karkas, 1,25 cm iç kaplama
(çizimde dış 13, iç 11 cm). Dış duvarın dış yüzü çizimin dış çizgisinde; iç duvarın karkası çizimdeki duvarın ekseninde.
"""
import argparse
import json
import math
from pathlib import Path

K = 1.25            # kaplama
D = 8.0             # karkas
r2 = lambda v: round(v, 2)
tr1 = lambda v: f"{v:.1f}".replace(".", ",").replace(",0", "")      # %33 · %50,2 · %21,7

# ── dış duvarlar (dış yüz → karkas kutusu) ──────────────────────────────────────
#   batı blok: x 0..624, y 220..860 (güneyi verandaya bakar); doğu kanat: x 624..1024, y 0..860; veranda: x 0..624, y 0..220 (çatısız)
duvarlar = [
    {"ad": "DK", "sinif": "dis", "kutu": [K, 860 - K - D, 1024 - K, 860 - K], "yukseklik": 270, "not": "kuzey dış duvar"},
    {"ad": "DB", "sinif": "dis", "kutu": [K, 220 + K + D, K + D, 860 - K - D], "yukseklik": 270, "not": "batı dış duvar"},
    {"ad": "DG", "sinif": "dis", "kutu": [K, 220 + K, 624 + K, 220 + K + D], "yukseklik": 270, "not": "batı bloğun güney dış duvarı (verandaya bakar)"},
    {"ad": "DKB", "sinif": "dis", "kutu": [624 + K, K + D, 624 + K + D, 220 + K + D], "yukseklik": 270, "not": "doğu kanadın batı dış duvarı (verandaya bakar)"},
    {"ad": "DKG", "sinif": "dis", "kutu": [624 + K, K, 1024 - K, K + D], "yukseklik": 270, "not": "doğu kanadın güney dış duvarı"},
    {"ad": "DD", "sinif": "dis", "kutu": [1024 - K - D, K + D, 1024 - K, 860 - K - D], "yukseklik": 270, "not": "doğu dış duvar"},
]


# ── iç duvarlar (çizimdeki eksen → 8 cm karkas) ─────────────────────────────────
def ic(ad, yon, eksen, a0, a1, notu):
    kutu = [eksen - D / 2, a0, eksen + D / 2, a1] if yon == "y" else [a0, eksen - D / 2, a1, eksen + D / 2]
    return {"ad": ad, "sinif": "ic", "kutu": kutu, "yukseklik": 270, "not": notu}


ust_ic, alt_ic = 860 - K - D, 220 + K + D             # kuzey ve güney dış duvarın karkas iç yüzleri (batı blok)
duvarlar += [
    ic("I1", "y", 360.5, alt_ic, ust_ic, "yaşam alanı ile mutfak ve hol arası (TV ve mutfak dolabı bu duvarda)"),
    ic("I2", "x", 458.5, 364.5, 758.5, "hol ile mutfak ve yatak odası 1 arası"),
    ic("I3", "y", 631.5, 462.5, ust_ic, "mutfak ile yatak odası 1 arası"),
    ic("I4", "x", 327.5, 635.5, 1024 - K - D, "hol ve banyo ile yatak odası 2 arası"),
    ic("I5", "y", 762.5, 331.5, 532.5, "hol ile banyo arası"),
    ic("I6", "y", 631.5, alt_ic, 331.5, "hol ile yatak odası 2 arası"),
    ic("I7", "x", 528.5, 766.5, 1024 - K - D, "banyo ile yatak odası 1 arası"),
]
mahaller = [
    {"ad": "Yaşam Alanı", "nokta": [180, 540], "islev": ["salon"], "sinif": "ic", "etiket_m2": 21.0},
    {"ad": "Mutfak", "nokta": [495, 650], "islev": ["mutfak"], "sinif": "ic", "etiket_m2": 10.0},
    {"ad": "Hol", "nokta": [495, 340], "islev": ["hol"], "sinif": "ic", "etiket_m2": 7.3},
    {"ad": "Yatak Odası 1", "nokta": [830, 700], "islev": ["yatak_odasi"], "sinif": "ic", "etiket_m2": 12.6},
    {"ad": "Yatak Odası 2", "nokta": [830, 170], "islev": ["yatak_odasi"], "sinif": "ic", "etiket_m2": 11.6},
    {"ad": "Banyo", "nokta": [890, 430], "islev": ["banyo"], "sinif": "ic", "islak": True, "etiket_m2": 4.7},
    {"ad": "Veranda", "sinif": "veranda", "islev": ["veranda"], "poligon": [[0, 0], [624, 0], [624, 220], [0, 220]], "nokta": [312, 110], "etiket_m2": 13.8,
     "ortu": "pergola", "not": "çatısız: üstünde ahşap pergola, kenarında ahşap korkuluk (katalog görselleri); ikisi de modelde ve listede yok (Lokman'a soruldu)"},
]


def pencere(ad, duvar, bas, en, yuk, mahal):
    return {"ad": ad, "tur": "pencere", "duvar": duvar, "bas": bas, "en": en, "yuk": yuk, "alt": 200 - yuk, "etiket": f"{en}/{yuk}", "mahal": mahal, "acilim": "ust"}


acikliklar = [
    pencere("P1", "DG", 124, 120, 180, "Yaşam Alanı"),
    pencere("P2", "DG", 521, 80, 180, "Hol"),
    pencere("P3", "DB", 633.5, 120, 120, "Yaşam Alanı"),
    pencere("P4", "DB", 326.5, 120, 120, "Yaşam Alanı"),
    pencere("P5", "DK", 436, 120, 180, "Mutfak"),
    pencere("P6", "DD", 633.5, 120, 120, "Yatak Odası 1"),
    pencere("P7", "DD", 343, 60, 40, "Banyo"),
    pencere("P8", "DD", 107.5, 120, 120, "Yatak Odası 2"),
    pencere("P9", "DKG", 764, 120, 180, "Yatak Odası 2"),
    {"ad": "K1", "tur": "dis_kapi", "duvar": "DG", "bas": 398.5, "en": 95, "yuk": 210, "giris": True, "mentese": "son", "acilim": "ust",
     "not": "çizimde 100 cm; dış kapı boşluğu 95 × 210 (mühendis, 4 Ekim 2026)"},
    {"ad": "K2", "tur": "ic_kapi", "duvar": "I1", "bas": 243, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yaşam Alanı", "acilim": "sol"},
    {"ad": "K3", "tur": "ic_kapi", "duvar": "I2", "bas": 526, "en": 90, "yuk": 214, "mentese": "son", "kanat": [80, 200], "not": "Mutfak", "acilim": "ust"},
    {"ad": "K4", "tur": "ic_kapi", "duvar": "I2", "bas": 647, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yatak Odası 1", "acilim": "ust"},
    {"ad": "K5", "tur": "ic_kapi", "duvar": "I4", "bas": 647, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yatak Odası 2", "acilim": "alt"},
    {"ad": "K6", "tur": "ic_kapi", "duvar": "I5", "bas": 343, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Banyo", "acilim": "sag"},
]

# ── çatı (bkz. üstteki açıklama) ───────────────────────────────────────────────────────────────────────
S = 30.0                                  # saçak (Lokman, 7 Ekim 2026: saçaklar 30'ar cm)
SK = 280.0                                # saçak kotu, makas üstü: duvar üstü 270 + topuk 10 (kör test projeleriyle aynı)
E = 0.33                                  # standart eğim (Excel hesaplama motoru, Ç8201, kör test projeleri)
PANEL = 8.0                               # çatı paneli (makas üstü, sırt 80 mm)
YM, XM = 540.0, 824.0                     # ana çatının (batı blok) mahyası (y 220–860'ın ortası), kanadın (cumbanın) mahyası (x 624–1024'ün ortası)
YG, YK, XB = 220 - S, 860 + S, 0 - S      # ana çatının güney ve kuzey saçak çizgileri, batı kalkanın saçak ucu
XKB, XKD, YKG = 624 - S, 1024 + S, 0 - S  # kanadın batı (veranda üstü) ve doğu saçak çizgileri, cumbanın güney kalkanının saçak ucu
YC = YG + (XM - XKB)                      # katalog ve K: cumbanın mahyasının ana çatının güney yüzüne girdiği yer (%33'te 230 cm → y 420)
XH = XKD - (YM - YG)                      # K: doğu kırmasında ana mahyanın bittiği yer (1054 − 350 = 704)
assert (YC, XH) == (420.0, 704.0)
CATILAR = {
    "katalog": ("Ç8801", "Tek kat çelik, 2+1, 88 m² (katalog)"),
    "K": ("Ç8801-K", "Tek kat çelik, 2+1, 88 m² (Ç8801'in çatı varyantı K: doğu ucu kırma)"),
    "L": ("Ç8801-L", "Tek kat çelik, 2+1, 88 m² (Ç8801'in çatı varyantı L: kanadın mahyası boydan boya)"),
}


def duzlem(ad, plan, yukari, egim, sacak, notu):
    return {"ad": ad, "plan": [[r2(x), r2(y)] for x, y in plan], "yukari": yukari, "egim": round(egim, 5), "sacak_kotu": SK, "sacak": sacak,
            "ust_pay": round(PANEL * math.sqrt(1 + egim ** 2), 3), "not": notu}


def bati_kalkani(ust):
    return {"ad": "batı kalkanı", "eksen": "x", "konum": 0.0, "aralik": [220.0, 860.0], "ic": "dogu", "ust": ust, "not": "batı bloğun (ana çatının) batı alnı"}


def cumba_kalkani(ust):
    return {"ad": "cumbanın güney kalkanı", "eksen": "y", "konum": 0.0, "aralik": [624.0, 1024.0], "ic": "kuzey", "ust": ust, "not": "doğu kanadın (cumbanın) güney alnı"}


def cati(secim):
    """(düzlemler, kalkanlar, tip_adi, tip_kaynak, kaynak metni)"""
    cumba_bati = duzlem("cumba batı", [[XKB, YKG], [XM, YKG], [XM, YC], [XKB, YG]], [1, 0], E, {"x": XKB},
                        "cumbanın batı yüzü; saçağı verandanın üstünde; ana çatının güney yüzüyle vadi")
    if secim == "katalog":
        d = [duzlem("ana güney", [[XB, YG], [XKB, YG], [XM, YC], [XKD, YG], [XKD, YM], [XB, YM]], [0, 1], E, {"y": YG},
                    "ana çatının güney yüzü; saçağı batıda verandanın, doğuda cumbanın arkasında; cumbayla iki vadi"),
             duzlem("ana kuzey", [[XB, YM], [XKD, YM], [XKD, YK], [XB, YK]], [0, -1], E, {"y": YK}, "ana çatının kuzey yüzü; kuzey cephede saçak boydan boya"),
             duzlem("cumba doğu", [[XM, YKG], [XKD, YKG], [XKD, YG], [XM, YC]], [-1, 0], E, {"x": XKD},
                    "cumbanın doğu yüzü; doğu cephede kısa saçak; ana çatının güney yüzüyle vadi"),
             cumba_bati]
        k = [bati_kalkani(["ana güney", "ana kuzey"]),
             {"ad": "doğu kalkanı", "eksen": "x", "konum": 1024.0, "aralik": [0.0, 860.0], "ic": "bati", "ust": ["ana güney", "ana kuzey"],
              "not": "ana çatının doğu alnı; doğu duvarı boydan boya, kalkan cumbanın saçağının arkasından başlar"},
             cumba_kalkani(["cumba batı", "cumba doğu"])]
        return (d, k, "beşik + cumba: ana çatı doğu–batı, iki ucunda kalkan; cumba (doğu kanadın güney ucu) ana çatıya girip biter",
                "Lokman, 10 Ekim 2026: cumba ana çatıya girip biter (13:33); katalogdaki model 2. versiyon (14:46). Excel hesaplama motorunun çatı "
                "tiplerinden 'beşik + cumba' (bir beşiğe dik bağlanan ikinci beşik)",
                "Lokman, 10 Ekim 2026 14:46: katalogdaki model 2. versiyon: ana çatı doğu–batı, iki ucunda kalkan; cumba ana çatıya girip biter; "
                "bütün yüzler %33.")
    if secim == "K":
        d = [duzlem("ana güney", [[XB, YG], [XKB, YG], [XM, YC], [XH, YM], [XB, YM]], [0, 1], E, {"y": YG},
                    "ana çatının güney yüzü; doğuda cumbayla vadi, doğu yüzüyle kırma"),
             duzlem("ana kuzey", [[XB, YM], [XH, YM], [XKD, YK], [XB, YK]], [0, -1], E, {"y": YK}, "ana çatının kuzey yüzü; kuzey cephede saçak boydan boya"),
             duzlem("doğu", [[XM, YKG], [XKD, YKG], [XKD, YK], [XH, YM], [XM, YC]], [-1, 0], E, {"x": XKD},
                    "doğu yüzü: ana çatının doğu kırması ve cumbanın doğu yüzü aynı düzlem; doğu cephede saçak boydan boya"),
             cumba_bati]
        k = [bati_kalkani(["ana güney", "ana kuzey"]), cumba_kalkani(["cumba batı", "doğu"])]
        return (d, k, "beşik + cumba, doğu ucu kırma: batıda kalkan; doğu cephede saçak boydan boya; cumba ana çatıya girip biter",
                "Lokman'ın 10 Ekim 13:33 düzeltmesinin öteki okuması (1. versiyon); 14:46: \"3 modelin de gayet güzel ... ben 1. versiyonu beğendim\". "
                "Excel hesaplama motorunda karşılığı yok; en yakını 'beşik + cumba'",
                "Çatı varyantı (Lokman, 10 Ekim 2026 14:46: üç çatı da olur): ana çatı batıda kalkan, doğu ucu kırma; bütün yüzler %33.")
    assert secim == "L"
    # mahyalar aynı kotta: eğim × (mahyanın saçak çizgisine uzaklığı) iki kısımda eşit (batı blok 350 cm, kanat 230 cm); batı blok %33, kanat %50,2
    EB, EK = E, E * (YM - YG) / (XM - XKB)
    d = [duzlem("batı blok güney", [[XB, YG], [XKB, YG], [XM, YM], [XB, YM]], [0, 1], EB, {"y": YG},
                "batı bloğun güney yüzü; saçağı verandanın üstünde; doğuda kanadın batı yüzüyle vadi"),
         duzlem("batı blok kuzey", [[XB, YM], [XM, YM], [XKB, YK], [XB, YK]], [0, -1], EB, {"y": YK},
                "batı bloğun kuzey yüzü; doğuda kanadın batı yüzüyle vadi"),
         duzlem("kanat batı güney", [[XKB, YKG], [XM, YKG], [XM, YM], [XKB, YG]], [1, 0], EK, {"x": XKB},
                "kanadın batı yüzünün güney parçası; saçağı verandanın üstünde"),
         duzlem("kanat batı kuzey", [[XM, YM], [XM, YK], [XKB, YK]], [1, 0], EK, {"x": XKB},
                "kanadın batı yüzünün kuzey parçası (güney parçasıyla aynı düzlem; batı bloğun kuzey yüzüyle vadi)"),
         duzlem("kanat doğu", [[XM, YKG], [XKD, YKG], [XKD, YK], [XM, YK]], [-1, 0], EK, {"x": XKD},
                "kanadın doğu yüzü; doğu cephede boydan boya saçak")]
    k = [bati_kalkani(["batı blok güney", "batı blok kuzey"]),
         {"ad": "kanadın güney kalkanı", "eksen": "y", "konum": 0.0, "aralik": [624.0, 1024.0], "ic": "kuzey", "ust": ["kanat batı güney", "kanat doğu"],
          "not": "doğu kanadın güney alnı"},
         {"ad": "kanadın kuzey kalkanı", "eksen": "y", "konum": 860.0, "aralik": [0.0, 1024.0], "ic": "guney", "ust": ["kanat batı kuzey", "kanat doğu"],
          "not": ("doğu kanadın kuzey alnı. Kuzey duvarı boydan boya: kalkan, vadinin duvar çizgisini kestiği yerden (x ≈ 614) başlar")}]
    return (d, k, "L beşik (beşik + cumba): batıda kalkan, doğu kanatta güneyde ve kuzeyde kalkan",
            "İlk varsayım (10 Ekim 2026 13:00); Lokman, 14:46: üç çatı da olur. Excel hesaplama motorunun çatı tiplerinden 'beşik + cumba'",
            f"Çatı varyantı (Lokman, 10 Ekim 2026 14:46: üç çatı da olur): kanadın mahyası boydan boya (güneyde ve kuzeyde kalkan), batı bloğun mahyası "
            f"ona aynı kotta bağlanır; batı blok %{tr1(EB * 100)}, kanat %{tr1(EK * 100)}.")


def tanim(secim="katalog"):
    duzlemler, kalkanlar, tip_adi, tip_kaynak, cati_kaynak = cati(secim)
    kod, ad = CATILAR[secim]
    return {
        "sema": "portman.yapi_tanimi/0.5-taslak", "kod": kod, "ad": ad, "aile": "tek_kat_celik", "paket": "baz", "birim": "cm",
        "kat": "zemin",
        "kaynak": {"cizim": ("PortatifEv arşivi: TEK KAT ÇELİK planlar DWG'sindeki Ç8801 planı ve katalog paftası PORT-Ç8801.jpg; çatı ve veranda üstü "
                             "katalog görsellerinden (ç_8801_1_R_Photo 1, 2, 5). Karkas modeli, montaj paftası ve yükleme listesi arşivde yok."),
                   "koordinat": "Köken binanın sol-alt dış köşesi (verandanın güneybatı köşesi); +x doğu, +y kuzey; DWG'den (60, 29) düşülür.",
                   "cati": cati_kaynak},
        "kat_yuksekligi": 270, "duvar_panelleri": "tahmin",
        "yuz_kaplamalari": {"dis": {"kalinlik": K, "malzeme": ["boardex"]}, "ic": {"kalinlik": K, "malzeme": ["alcipan"]}},
        "duvar_siniflari": {"dis": {"ad": "dış duvar (DIS-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
                            "ic": {"ad": "iç duvar (IC-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}}},
        "duvarlar": duvarlar, "mahaller": mahaller, "acikliklar": acikliklar, "kirisler": [], "lento": 70,
        "osb_takviye": {"duvarlar": [{"mahal": "Yaşam Alanı", "duvar": "I1", "duvar_adi": "yaşam alanı ile mutfak arası duvar", "neden": "TV ünitesi"},
                                     {"mahal": "Mutfak", "duvar": "I1", "duvar_adi": "yaşam alanı ile mutfak arası duvar", "neden": "mutfak dolabı ve eviye"}],
                        "teyit": "plan (katalog paftasındaki TV ünitesi ve mutfak dolabı)"},
        "cati": {
            "tip": "besik_cumba", "tip_adi": tip_adi, "tip_kaynak": tip_kaynak,
            "sacak": int(S), "topuk": 10, "duvar_ustu": 270, "panel_kalinligi": int(PANEL),
            "duzlemler": duzlemler, "kalkanlar": kalkanlar,
        },
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ç8801 Yapı Tanımı (katalog çatısı ya da çatı varyantı)")
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--cati", choices=list(CATILAR), default="katalog")
    a = ap.parse_args()
    t = tanim(a.cati)
    a.cikti.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = t["cati"]
    print("yazıldı", a.cikti, "|", t["kod"], "| duvar", len(duvarlar), "| mahal", len(mahaller), "| açıklık", len(acikliklar),
          "| düzlem", len(c["duzlemler"]), "| kalkan", len(c["kalkanlar"]))
    for d in c["duzlemler"]:
        print("  ", d["ad"], d["plan"], "eğim", d["egim"])
