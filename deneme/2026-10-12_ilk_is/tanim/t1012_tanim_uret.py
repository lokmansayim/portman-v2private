#!/usr/bin/env python3
"""Bayi talebi (12 Ekim 2026): tek kat çelik, 2+1, dış ölçü 747 × 1012 (75,6 m²), verandasız. Yapı Tanımı 0.5.

Kaynak: bayinin WhatsApp'tan gönderdiği plan fotoğrafı (ölçülü: 747 ve 1012; "TOPLAM 75.5 M2"; mahal etiketleri) ve bir görsel.
Lokman, 12 Ekim 12:49: "yapı çelik olarak çizilecek". İmarlı oturum 76 m²: dış ölçü sabit, kaplama dahil en dış yüz 747 × 1012.
İç ölçüler fotoğraftan perspektif düzeltmesiyle okundu (dört dış köşeden homografi; ±5 cm). Ad, telefon ve fiyat içermez; depoya girmez.

Koordinat (cm): köken binanın sol-alt (güneybatı) dış köşesi; +x doğu (sağ), +y kuzey. Güney = ön cephe (iki 200/200 sürgülü ve giriş kapısı),
kuzey = arka (banyonun 60/40 penceresi). Duvarlar baz paketin katmanlarıyla (Ç8801 ile aynı): dış yüzde 1,25 cm kaplama, 8 cm karkas,
1,25 cm iç kaplama; dış duvarın dış yüzü planın dış çizgisinde, iç duvarın karkası planın duvar ekseninde.

Çatılar (--cati): besik (sade beşik; mahya ön–arka, üçgen önde ve arkada; %33, saçak 30, saçak kotu 280 — kör test projeleriyle aynı).
Kullanım: python t1012_tanim_uret.py <çıktı.json> [--cati besik]
"""
import argparse
import json
import math
from pathlib import Path

K, D = 1.25, 8.0          # kaplama, karkas
GEN, DER = 747.0, 1012.0  # dış ölçü: ön cephe (doğu–batı) ve derinlik (güney–kuzey)
r2 = lambda v: round(v, 2)

# ── dış duvarlar ────────────────────────────────────────────────────────────────
duvarlar = [
    {"ad": "DG", "sinif": "dis", "kutu": [K, K, GEN - K, K + D], "yukseklik": 270, "not": "güney (ön) dış duvar"},
    {"ad": "DK", "sinif": "dis", "kutu": [K, DER - K - D, GEN - K, DER - K], "yukseklik": 270, "not": "kuzey (arka) dış duvar"},
    {"ad": "DB", "sinif": "dis", "kutu": [K, K + D, K + D, DER - K - D], "yukseklik": 270, "not": "batı (sol) dış duvar"},
    {"ad": "DD", "sinif": "dis", "kutu": [GEN - K - D, K + D, GEN - K, DER - K - D], "yukseklik": 270, "not": "doğu (sağ) dış duvar; mutfak tezgâhı bu duvarda"},
]


def ic(ad, yon, eksen, a0, a1, notu):
    kutu = [eksen - D / 2, a0, eksen + D / 2, a1] if yon == "y" else [a0, eksen - D / 2, a1, eksen + D / 2]
    return {"ad": ad, "sinif": "ic", "kutu": [r2(v) for v in kutu], "yukseklik": 270, "not": notu}


# Eksenler (fotoğraftan; arka dış yüzden ölçülenler y = 1012 − ölçü): bölme 456 → y 556; banyonun alt duvarı 276 → y 736;
# banyonun batı duvarı x 280; holün batı duvarı x 361; banyo ve holün doğu duvarı x 462.
YB, YBA, XBB, XHB, XHD = 556.0, 736.0, 280.0, 361.0, 462.0
ic_ust, ic_bati, ic_dogu = DER - K - D, K + D, GEN - K - D
duvarlar += [
    ic("I1", "x", YB, ic_bati, ic_dogu, "yatak odaları ve hol ile yaşam alanı arası (TV ünitesi bu duvarda)"),
    ic("I2", "y", XHD, YB + D / 2, ic_ust, "banyo ve hol ile yatak odası 2 arası"),
    ic("I3", "y", XBB, YBA + D / 2, ic_ust, "yatak odası 1 ile banyo arası"),
    ic("I4", "x", YBA, XBB - D / 2, XHD - D / 2, "banyo ile hol ve yatak odası 1 arası"),
    ic("I5", "y", XHB, YB + D / 2, YBA - D / 2, "hol ile yatak odası 1 arası"),
]
mahaller = [
    {"ad": "Yatak Odası 1", "nokta": [140, 780], "islev": ["yatak_odasi"], "sinif": "ic", "etiket_m2": 13.3},
    {"ad": "Banyo", "nokta": [370, 870], "islev": ["banyo"], "sinif": "ic", "islak": True, "etiket_m2": 4.4},
    {"ad": "Hol", "nokta": [411, 645], "islev": ["hol"], "sinif": "ic", "etiket_m2": 1.79},
    {"ad": "Yatak Odası 2", "nokta": [604, 780], "islev": ["yatak_odasi"], "sinif": "ic", "etiket_m2": 11.0},
    {"ad": "Yaşam Alanı", "nokta": [300, 300], "islev": ["salon", "mutfak"], "sinif": "ic", "etiket_m2": 38.0},
]


def pencere(ad, duvar, bas, en, yuk, alt, mahal, notu=None):
    p = {"ad": ad, "tur": "pencere", "duvar": duvar, "bas": bas, "en": en, "yuk": yuk, "alt": alt, "etiket": f"{en}/{yuk}", "mahal": mahal, "acilim": "ust"}
    if notu:
        p["not"] = notu
    return p


# Açıklıklar: yer fotoğraftan (pencere ve kapı sembolleri), ölçü plandaki etiketten. Başlık altı 200 (Ç8801 ile aynı).
acikliklar = [
    pencere("P1", "DB", 712, 120, 180, 20, "Yatak Odası 1", "çift açılır"),
    pencere("P2", "DB", 110, 150, 180, 20, "Yaşam Alanı", "çift açılır"),
    pencere("P3", "DD", 718, 120, 180, 20, "Yatak Odası 2", "çift açılır"),
    pencere("P4", "DD", 236, 120, 100, 100, "Yaşam Alanı", "çift açılır; mutfak tezgâhının üstünde"),
    pencere("P5", "DK", 396, 60, 40, 160, "Banyo"),
    pencere("P6", "DG", 89, 200, 200, 0, "Yaşam Alanı", "sürgülü"),
    pencere("P7", "DG", 452, 200, 200, 0, "Yaşam Alanı", "sürgülü"),
    {"ad": "K1", "tur": "dis_kapi", "duvar": "DG", "bas": 345, "en": 95, "yuk": 210, "giris": True, "mentese": "bas", "acilim": "ust",
     "not": "planda kanat ≈ 82; dış kapı boşluğu 95 × 210 (mühendis, 4 Ekim 2026)"},
    {"ad": "K2", "tur": "ic_kapi", "duvar": "I5", "bas": 562, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yatak Odası 1", "acilim": "sol"},
    {"ad": "K3", "tur": "ic_kapi", "duvar": "I2", "bas": 562, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yatak Odası 2", "acilim": "sag"},
    {"ad": "K4", "tur": "ic_kapi", "duvar": "I1", "bas": 366, "en": 90, "yuk": 214, "mentese": "bas", "kanat": [80, 200], "not": "Yaşam Alanı", "acilim": "alt"},
    {"ad": "K5", "tur": "ic_kapi", "duvar": "I4", "bas": 366, "en": 90, "yuk": 214, "mentese": "son", "kanat": [80, 200], "not": "Banyo", "acilim": "ust"},
]

# ── çatı ─────────────────────────────────────────────────────────────────────────
S, SK, E, PANEL = 30.0, 280.0, 0.33, 8.0
XB, XD, YG, YK = -S, GEN + S, -S, DER + S
XM = GEN / 2


def duzlem(ad, plan, yukari, sacak, notu):
    return {"ad": ad, "plan": [[r2(x), r2(y)] for x, y in plan], "yukari": yukari, "egim": E, "sacak_kotu": SK, "sacak": sacak,
            "ust_pay": round(PANEL * math.sqrt(1 + E ** 2), 3), "not": notu}


# cumba (KT-01'in çatısı; Lokman, 12 Ekim 13:05: "KT-01 müştemilatlı model aynı bu çatıdan oradan örnek alabilirsin"):
# ana beşiğin batı yüzü güneye cumbanın üstüne uzanır; cumbanın doğu yüzü öne bakan küçük üçgeni yapar; sağda alçak çatı (KT-01'de veranda
# sundurması; burada altı kapalı: yaşam alanı) ana çatının geri çekilmiş güney kalkan duvarına dayanır. Ön cephe düz (oturum 75,6 m² kalır).
E_SUN = (329.5 - 280.0) / 278.0   # alçak çatının eğimi: KT-01'deki veranda sundurmasıyla aynı (%17,8)
XS = 350.0                        # cumbanın doğu saçağı (cumba 0–≈330: sol sürgülü cumbanın altında, giriş kapısı alçak çatının altında)
XC = (XB + XS) / 2                # cumbanın mahyası (batı yüzü ana çatının batı yüzüyle aynı düzlem)
YD = 250.0                        # ana çatının güney kalkan duvarı (KT-01'de 251); altında duvar yok: alçak çatıların taşıyıcısına oturur
YGC, YC = YD - S, -S              # ana çatının güney kalkan ucu; cumbanın ve alçak çatının saçak ucu
ORAN = E_SUN / E
kirma_x = lambda y: XD - ORAN * (y - YC)     # ana çatının doğu yüzü ile alçak çatının kesişimi (kırma)
vadi_x = lambda y: XS - ORAN * (y - YC)      # cumbanın doğu yüzü ile alçak çatının kesişimi (vadi)


def cati(secim):
    if secim == "cifte":
        return cati_cifte()
    if secim == "besik":
        d = [duzlem("batı", [[XB, YG], [XM, YG], [XM, YK], [XB, YK]], [1, 0], {"x": XB}, "batı yüzü; batı cephede saçak boydan boya"),
             duzlem("doğu", [[XM, YG], [XD, YG], [XD, YK], [XM, YK]], [-1, 0], {"x": XD}, "doğu yüzü; doğu cephede saçak boydan boya")]
        k = [{"ad": "ön kalkan", "eksen": "y", "konum": 0.0, "aralik": [0.0, GEN], "ic": "kuzey", "ust": ["batı", "doğu"], "not": "güney (ön) alın: cephenin üçgeni"},
             {"ad": "arka kalkan", "eksen": "y", "konum": DER, "aralik": [0.0, GEN], "ic": "guney", "ust": ["batı", "doğu"], "not": "kuzey (arka) alın"}]
        return d, k, [], "besik", "beşik: mahya ön–arka, üçgen önde ve arkada", "Excel hesaplama motorunun çatı tiplerinden 'beşik'"
    assert secim == "cumba"
    sun = dict(duzlem("ön sundurma", [[XS, YC], [XD, YC], [kirma_x(YD), YD], [vadi_x(YD), YD]], [0, 1], {"y": YC},
                      "alçak çatı (KT-01'de veranda sundurması): altı kapalı, yaşam alanı; ana çatının güney kalkan duvarına dayanır"),
               egim=round(E_SUN, 5), ust_pay=round(PANEL * math.sqrt(1 + E_SUN ** 2), 3))
    d = [duzlem("batı", [[XB, YC], [XC, YC], [XC, YGC], [XM, YGC], [XM, YK], [XB, YK]], [1, 0], {"x": XB},
                "ana çatının batı yüzü; güneyde cumbanın batı yüzüyle aynı düzlem"),
         duzlem("doğu", [[XM, YGC], [kirma_x(YGC), YGC], [XD, YC], [XD, YK], [XM, YK]], [-1, 0], {"x": XD},
                "ana çatının doğu yüzü; güneydoğuda alçak çatıyla kırma yapar"),
         duzlem("cumba doğu", [[XC, YC], [XS, YC], [vadi_x(YD), YD], [XC, YD]], [-1, 0], {"x": XS},
                "cumbanın doğu yüzü (öne bakan küçük üçgen); alçak çatıyla vadi yapar"),
         sun]
    kenar = [{"duzlem": "ön sundurma", "p": [r2(kirma_x(YD)), YD], "q": [r2(vadi_x(YD)), YD], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
             {"duzlem": "cumba doğu", "p": [r2(vadi_x(YD)), YD], "q": [r2(XC), YD], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
             {"duzlem": "ön sundurma", "p": [r2(kirma_x(YGC)), YGC], "q": [r2(kirma_x(YD)), YD], "tur": "gizli",
              "not": "kırmanın, ana çatının güney saçağının altında kalan 30 cm'lik kısmı"},
             {"duzlem": "cumba doğu", "p": [r2(XC), YD], "q": [r2(XC), YGC], "tur": "gizli",
              "not": "cumba mahyasının, ana çatının güney saçağının altında kalan 30 cm'lik kısmı"}]
    k = [{"ad": "kuzey kalkanı", "eksen": "y", "konum": DER, "aralik": [0.0, GEN], "ic": "guney", "ust": ["batı", "doğu"], "not": "ana çatı; arka duvarın üstü"},
         {"ad": "cumba kalkanı", "eksen": "y", "konum": 0.0, "aralik": [0.0, XS], "ic": "kuzey", "ust": ["batı", "cumba doğu", "ön sundurma"],
          "not": "cumbanın güney alnı: ön cephenin solundaki küçük üçgen"},
         {"ad": "güney kalkanı (alçak çatıların üstü)", "eksen": "y", "konum": YD, "aralik": [0.0, GEN], "ic": "kuzey", "ust": ["batı", "doğu"],
          "alt": ["cumba doğu", "ön sundurma"], "not": "ana çatının geri çekilmiş güney kalkanı; altında duvar yok (taşıyıcıyı mühendis belirler)"}]
    return (d, k, kenar, "besik_cumba", "beşik + cumba (KT-01'in çatısı): ana beşik, solda öne bakan cumba, sağda alçak çatı; ön cephe düz",
            "Lokman, 12 Ekim 2026 13:05: görseldeki çatı KT-01'inkiyle aynı. Excel hesaplama motorunun çatı tiplerinden 'beşik + cumba'")


# ── çift cumba + veranda (Lokman, 12 Ekim 13:49: 1 m; 15:11: 50 cm) ───────────────────────────────────────────────────────────────
# Bayi 13:32: "çift cumba istiyor ... birebir aynı görünüm"; Lokman 13:33: "göstermelik 100 cm [veranda] koyalım mı", bayi: "olur".
# Lokman 13:49: cumbada öne doğru 30 cm çıkıntı (ortak firmanın modelindeki gibi), pencerenin ortası cumba makasının ortasında, 1 m veranda.
# Hepsi 747 × 1012'nin içinde: bina alanına veranda girer (Lokman, 9 Ekim 22:22), imarlı oturum 76.
#   y −30    çıkıntı çatısının ön saçağı (çıkıntının kendi 30 cm saçağı)
#   y 0      pencere çıkıntısının ön duvarı (x 35–285) ile cumba ve veranda saçakları: aynı hatta
#   y 0–30   pencere çıkıntısı: önünde pencere, üstünde küçük üçgen çatı (ikinci cumba)
#   y 30     cumbanın ön duvarı (x 0–320) ve verandanın ön çizgisi (dikme, kiriş): aynı hatta
#   y 80     verandanın arkası: ana ön duvar (x 320–747; giriş kapısı, sağ sürgülü) ve ana çatının güney kalkanı (KT-01'deki gibi duvarın üstünde)
# Lokman 15:11: "veranda derinliğini 100 cm yapmıştık 50 cm'e düşürebilir misin?" → verandanın önü cumbayla aynı hatta kalır (14:46),
# ana ön duvar 50 cm öne gelir (y 130 → 80); salon büyür, oturum değişmez
# Lokman 14:46: "veranda ve cumba aynı seviyede/hatta kalacak, çıkıntı ileride kalacak; yani veranda saçağı ile cumba saçağı aynı hizada,
# çıkıntı önde 30 cm, kendi 30 cm saçağı" → cumbanın ön saçağı 30 (y 0); çıkıntının saçağı önde ve yanlarda 30 (önceki: cumbada saçak yok, çıkıntıda 15)
WC, YAN, EC, KX0, KX1, SK2 = 30.0, 80.0, 320.0, 35.0, 285.0, 30.0
XS2 = EC + S                      # cumbanın doğu saçağı (verandanın üstünde)
XC2 = (XB + XS2) / 2              # cumba makasının ortası (mahya): 160; pencere ve çıkıntı buna ortalanır
YD2, YG2, YCS = YAN, YAN - S, WC - S
vx = lambda y: XS2 - ORAN * (y - YCS)        # cumbanın doğu yüzü ile veranda çatısının vadisi
kx = lambda y: XD - ORAN * (y - YCS)         # ana çatının doğu yüzü ile veranda çatısının kırması
assert (XC2, KX0 + KX1) == (160.0, 2 * XC2)
# Lokman 14:06: "cumba makası ile çıkıntının makası arasında 30 cm boşluk olsun" → çıkıntının makası cumbanınkine paralel, 30 cm aşağıda (makas üstü, düşey)
BOSLUK = 30.0
SK_K = SK + E * ((KX0 - SK2) - XB) - BOSLUK                      # çıkıntı çatısının saçak kotu (x 5 ve 315'te): 261,55
kot_k = lambda x: SK_K + E * (min(x, 2 * XC2 - x) - (KX0 - SK2))  # çıkıntı çatısının makas üstü (x boyunca; tepe x 160'ta 312,7)
# Lokman 14:05: "pencerenin eğimi de aynı çıkıntı gibi olacak"; 14:19: "pencere ile çıkıntı makası arasında da 30 cm olsun ve pencere görünüşünü
# aynı yüklediğim resimdeki gibi yap" → üst kenar çıkıntı makasına paralel, 30 cm altında; görseldeki gibi eşiği döşemenin 10 cm üstünde,
# ortada dikey kayıt (iki kanadın birleştiği yer) ve yan yüksekliğin %38 ile %77,5'inde iki yatay kayıt (görselden ölçüldü)
PAY_P, ALT_P = 30.0, 10.0
assert abs(SK_K - 261.55) < 1e-9 and abs(kot_k(XC2) - 312.7) < 1e-9
assert YCS == 0.0 and -SK2 == YCS - 30      # cumba ve veranda saçağı çıkıntının ön yüzüyle aynı hatta (y 0); çıkıntının saçağı 30 cm önde


def plan(secim):
    """(duvarlar, mahaller, açıklıklar, kirişler, ek duvar sınıfları)"""
    if secim != "cifte":
        return duvarlar, mahaller, acikliklar, [], {}
    dis = [
        {"ad": "KBO1", "sinif": "dis", "kutu": [KX0 + K, K, XC2, K + D], "yukseklik": {"bas": r2(kot_k(KX0 + K)), "son": r2(kot_k(XC2))},
         "not": "pencere çıkıntısının önü, batı yarısı; üstü çıkıntı çatısının eğiminde"},
        {"ad": "KBO2", "sinif": "dis", "kutu": [XC2, K, KX1 - K, K + D], "yukseklik": {"bas": r2(kot_k(XC2)), "son": r2(kot_k(KX1 - K))},
         "not": "pencere çıkıntısının önü, doğu yarısı; üstü çıkıntı çatısının eğiminde"},
        {"ad": "KBB", "sinif": "dis", "kutu": [KX0 + K, K + D, KX0 + K + D, WC + K + D], "yukseklik": r2(kot_k(KX0 + K)), "not": "pencere çıkıntısının batı yanı"},
        {"ad": "KBD", "sinif": "dis", "kutu": [KX1 - K - D, K + D, KX1 - K, WC + K + D], "yukseklik": r2(kot_k(KX1 - K)), "not": "pencere çıkıntısının doğu yanı"},
        {"ad": "DGC1", "sinif": "dis", "kutu": [K, WC + K, KX0 + K, WC + K + D], "yukseklik": 270, "not": "cumbanın ön duvarı, çıkıntının batısı"},
        {"ad": "DGC2", "sinif": "dis", "kutu": [KX1 - K, WC + K, EC - K, WC + K + D], "yukseklik": 270, "not": "cumbanın ön duvarı, çıkıntının doğusu"},
        {"ad": "DCD", "sinif": "dis", "kutu": [EC - K - D, WC + K + D, EC - K, YAN + K + D], "yukseklik": 270, "not": "cumbanın doğu duvarı (verandaya bakar)"},
        {"ad": "DGS", "sinif": "dis", "kutu": [EC - K, YAN + K, GEN - K, YAN + K + D], "yukseklik": 270,
         "not": "ana ön duvar, verandanın arkası (giriş kapısı ve sağ sürgülü); üstünde ana çatının güney kalkanı"},
        {"ad": "DB", "sinif": "dis", "kutu": [K, WC + K + D, K + D, DER - K - D], "yukseklik": 270, "not": "batı (sol) dış duvar"},
        {"ad": "DD", "sinif": "dis", "kutu": [GEN - K - D, YAN + K + D, GEN - K, DER - K - D], "yukseklik": 270,
         "not": "doğu (sağ) dış duvar; mutfak tezgâhı bu duvarda"},
        {"ad": "DK", "sinif": "dis", "kutu": [K, DER - K - D, GEN - K, DER - K], "yukseklik": 270, "not": "kuzey (arka) dış duvar"},
        # dikme KT-01'deki gibi: 30 × 8, ön cepheye paralel; kaplaması ön çizgide (y 30) ve doğu çizgisinde (x 747) biter
        {"ad": "VK1", "sinif": "kolon", "kutu": [GEN - K - 30, WC + K, GEN - K, WC + K + D], "yukseklik": 240, "not": "veranda dikmesi (sağ ön köşe)"},
    ]
    d = dis + [x for x in duvarlar if x["sinif"] == "ic"]
    m = mahaller + [{"ad": "Veranda", "sinif": "veranda", "islev": ["veranda"], "poligon": [[EC, WC], [GEN, WC], [GEN, YAN], [EC, YAN]],
                     "nokta": [533, 55], "etiket_yeri": [640, -24], "etiket_m2": round((GEN - EC) * (YAN - WC) / 1e4, 2),
                     "not": "50 cm veranda (Lokman, 12 Ekim 15:11; önce bayi ile Lokman 13:33–13:34: 'göstermelik 100 cm')"}]
    ust_a, ust_t = r2(kot_k(XC2 - 100) - PAY_P), r2(kot_k(XC2) - PAY_P)        # 249,7 ve 282,7 (döşemeden)
    h_a, h_t = r2(ust_a - ALT_P), r2(ust_t - ALT_P)                             # pencere yüksekliği: yanlarda 239,7, ortada 272,7
    kayit = {"yatay": [round(ALT_P + 0.382 * h_a), round(ALT_P + 0.775 * h_a)]}
    et = f"100/{round(h_a)}–{round(h_t)}"
    p6a = dict(pencere("P6", "KBO1", XC2 - 100, 100, h_a, ALT_P, "Yaşam Alanı",
                       "çıkıntının penceresi, batı yarısı: üst kenarı çıkıntı makasına paralel, 30 cm altında; ortası cumba makasının ortasında (x 160)"),
               etiket=et, plan_etiketi=f"200/{round(h_a)}–{round(h_t)} (2 kanat)", tepe_kot={"bas": ust_a, "son": ust_t}, kayit=kayit)
    p6b = dict(pencere("P6B", "KBO2", XC2, 100, h_a, ALT_P, "Yaşam Alanı", "çıkıntının penceresi, doğu yarısı"),
               etiket=et, etiket_gizle=True, tepe_kot={"bas": ust_t, "son": ust_a}, kayit=kayit)
    orta_y = (YB + D / 2 + DER - K - D) / 2                                   # yatak odalarının yan duvarlarının ortası: 781,4
    yeni = {"P6": p6a,
            # Lokman 14:07: "verandadaki pencereyi sağ taraf ile çelik kapı arasında eşit olsun" (kapının sağ kenarı 440 ile sağ köşe 747 arasında ortada)
            "P7": pencere("P7", "DGS", r2((440 + GEN) / 2 - 100), 200, 200, 0, "Yaşam Alanı", "sürgülü; çelik kapı ile sağ köşe arasında ortada"),
            "K1": dict({x["ad"]: x for x in acikliklar}["K1"], duvar="DGS"),
            # simetri kuralı (Lokman, 14:07): yatak odası pencereleri odanın yan duvarının ortasında (bayinin planında ±10 cm)
            "P1": dict({x["ad"]: x for x in acikliklar}["P1"], bas=r2(orta_y - 60)),
            "P3": dict({x["ad"]: x for x in acikliklar}["P3"], bas=r2(orta_y - 60))}
    a = [yeni.get(x["ad"], x) for x in acikliklar]
    a.insert(a.index(p6a) + 1, p6b)
    m = [dict(x, tavan="egimli") if x["ad"] == "Yaşam Alanı" else x for x in m]     # Lokman 14:05: "salon içten bakınca eğimli tavan olacak"
    kr = [{"ad": "KR1", "kutu": [EC - K - D, WC + K, GEN - K, WC + K + D], "alt": 240, "ust": 270, "acik": [[EC, GEN - K]], "bolge": "veranda",
           "not": "veranda kirişi, ön; batı ucu cumbanın köşesinde, doğu ucu dikmenin üstünde (KT-01 gibi)"},
          {"ad": "KR2", "kutu": [GEN - K - D, WC + K, GEN - K, YAN + K + D], "alt": 240, "ust": 270, "acik": [[WC + K, YAN + K]], "bolge": "veranda",
           "not": "veranda kirişi, doğu; dikmenin üstünden ön duvara"},
]
    # dikmenin yüzleri KT-01'deki gibi dış kaplamalı: görünüşlerde çizilir (Lokman 15:10: "görünüşlerde kolonu unutmuşsun"). Liste dikme kaplamasını
    # kuraldaki çevreyle ayrıca sayar; girdi dikme yüzlerini dış duvar toplamına katmaz
    return d, m, a, kr, {"kolon": {"ad": "veranda dikmesi", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}}}


def cati_cifte():
    # Cumba ve veranda saçağı aynı hatta (y 0, cumba duvarından ve veranda dikmesinden 30 cm önde); çıkıntı 30 cm önde, kendi saçağı 30 cm (y −30).
    # Lokman 14:46: "veranda saçağı ile cumba saçağı aynı hizada çıkıntı önde 30 cm kendi 30 cm saçağı". Çıkıntı çatısının arka 30 cm'si cumba saçağının altında.
    sun = dict(duzlem("veranda", [[vx(YCS), YCS], [XD, YCS], [kx(YD2), YD2], [vx(YD2), YD2]], [0, 1], {"y": YCS},
                      "veranda çatısı (KT-01'deki veranda sundurması gibi %17,8); ana ön duvara ve güney kalkanına dayanır; ön saçağı cumbanınkiyle aynı hatta"),
               egim=round(E_SUN, 5), ust_pay=round(PANEL * math.sqrt(1 + E_SUN ** 2), 3))
    d = [duzlem("batı", [[XB, YCS], [XC2, YCS], [XC2, YG2], [XM, YG2], [XM, YK], [XB, YK]], [1, 0], {"x": XB},
                "ana çatının batı yüzü; güneyde cumbanın batı yüzüyle aynı düzlem (cumbanın ön saçağı 30)"),
         duzlem("doğu", [[XM, YG2], [kx(YG2), YG2], [XD, YCS], [XD, YK], [XM, YK]], [-1, 0], {"x": XD},
                "ana çatının doğu yüzü; güneydoğuda veranda çatısıyla kırma yapar"),
         duzlem("cumba doğu", [[XC2, YCS], [vx(YCS), YCS], [vx(YD2), YD2], [XC2, YD2]], [-1, 0], {"x": XS2},
                "cumbanın doğu yüzü; veranda çatısıyla vadi yapar; ön saçağı 30, veranda saçağıyla aynı hatta"),
         sun,
         dict(duzlem("çıkıntı batı", [[KX0 - SK2, -SK2], [XC2, -SK2], [XC2, WC], [KX0 - SK2, WC]], [1, 0], {"x": KX0 - SK2},
                     "pencere çıkıntısının küçük üçgen çatısı (ikinci cumba), batı yüzü; cumba makasının 30 cm altında; cumba kalkanına dayanır; saçak 30"),
              sacak_kotu=SK_K),
         dict(duzlem("çıkıntı doğu", [[XC2, -SK2], [KX1 + SK2, -SK2], [KX1 + SK2, WC], [XC2, WC]], [-1, 0], {"x": KX1 + SK2},
                     "pencere çıkıntısının küçük üçgen çatısı, doğu yüzü; cumba makasının 30 cm altında; cumba kalkanına dayanır; saçak 30"),
              sacak_kotu=SK_K)]
    kenar = [{"duzlem": "veranda", "p": [r2(kx(YD2)), YD2], "q": [r2(vx(YD2)), YD2], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
             {"duzlem": "cumba doğu", "p": [r2(vx(YD2)), YD2], "q": [r2(XC2), YD2], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
             {"duzlem": "veranda", "p": [r2(kx(YG2)), YG2], "q": [r2(kx(YD2)), YD2], "tur": "gizli", "not": "kırmanın, ana çatının güney saçağı altındaki 30 cm'si"},
             {"duzlem": "cumba doğu", "p": [r2(XC2), YD2], "q": [r2(XC2), YG2], "tur": "gizli", "not": "cumba mahyasının, ana çatının güney saçağı altındaki 30 cm'si"},
             {"duzlem": "çıkıntı batı", "p": [KX0 - SK2, WC], "q": [XC2, WC], "tur": "duvar_dibi", "not": "cumba kalkanı"},
             {"duzlem": "çıkıntı doğu", "p": [XC2, WC], "q": [KX1 + SK2, WC], "tur": "duvar_dibi", "not": "cumba kalkanı"}]
    k = [{"ad": "kuzey kalkanı", "eksen": "y", "konum": DER, "aralik": [0.0, GEN], "ic": "guney", "ust": ["batı", "doğu"], "not": "ana çatı; arka duvarın üstü"},
         # cumbanın güney alnı üç parça: çıkıntı çatısının iki yanında duvar üstünden başlar, ortada çıkıntı çatısının üstünden (görünüşteki boşluk düzeltmesi,
         # Lokman 14:31: "cumba ve çıkıntı olan yerde görünüşlerde boşluk oluşmuş"). Cumba saçağının 30 cm altında (14:46). Levha 4 mm içeride:
         # çıkıntı çatısının arka ucuyla aynı yüze düşmesin
         {"ad": "cumba kalkanı (batı ucu)", "eksen": "y", "konum": WC + 0.4, "aralik": [0.0, KX0 - SK2], "ic": "kuzey", "ust": ["batı"], "not": "cumbanın güney alnı, batı ucu"},
         {"ad": "cumba kalkanı", "eksen": "y", "konum": WC + 0.4, "aralik": [KX0 - SK2, KX1 + SK2], "ic": "kuzey", "ust": ["batı", "cumba doğu"],
          "alt": ["çıkıntı batı", "çıkıntı doğu"], "not": "cumbanın güney alnı; ortasında pencere çıkıntısının küçük çatısı (30 cm aşağıda)"},
         {"ad": "cumba kalkanı (doğu ucu)", "eksen": "y", "konum": WC + 0.4, "aralik": [KX1 + SK2, EC], "ic": "kuzey", "ust": ["cumba doğu"], "not": "cumbanın güney alnı, doğu ucu"},
         {"ad": "güney kalkanı (alçak çatıların üstü)", "eksen": "y", "konum": YD2, "aralik": [0.0, GEN], "ic": "kuzey", "ust": ["batı", "doğu"],
          "alt": ["cumba doğu", "veranda"], "not": "ana çatının güney kalkanı; doğu kısmı ana ön duvarın üstünde, batı kısmı cumbanın üstünde"},
         # Duvarlar 270'te biter; veranda çatısı arkada 303'te, cumbanın doğu duvarının üstünde 290–303'te. Aradaki şerit boştu: ön görünüşte
         # cumbanın doğu saçağının altından evin içi görünüyordu. Duvar üstünden üstteki alçak çatıya kadar kapatılır (kalkan gibi Boardex).
         {"ad": "veranda arkası (ön duvarın üstü)", "eksen": "y", "konum": YAN, "aralik": [EC, r2(kx(YAN - 0.5))], "ic": "kuzey", "ust": ["veranda"],
          "ust_disarida": True, "not": "ana ön duvarın üstü ile veranda çatısı arası"},
         {"ad": "veranda arkası (doğu ucu)", "eksen": "y", "konum": YAN, "aralik": [r2(kx(YAN - 0.5)), GEN], "ic": "kuzey", "ust": ["doğu"],
          "ust_disarida": True, "not": "ana ön duvarın doğu ucu ile ana çatının doğu yüzü arası"},
         {"ad": "cumbanın doğu duvarının üstü", "eksen": "x", "konum": EC, "aralik": [WC + 3.4, YAN], "ic": "bati", "ust": ["cumba doğu", "veranda"],
          "not": "cumbanın doğu duvarı ile üstündeki cumba ve veranda çatısı arası (ön ucu cumba kalkanının arkasından başlar)"}]
    return (d, k, kenar, "besik_cumba", "beşik + çift cumba, 50 cm veranda (KT-01'in çatı biçimi; cumbada 30 cm pencere çıkıntısı ve küçük üçgen çatı)",
            "Lokman, 12 Ekim 2026 13:05 (KT-01'in çatısı), 13:49 (30 cm çıkıntı, pencere cumba makasının ortasında, 1 m veranda) ve 14:46 "
            "(cumba ve veranda saçağı aynı hatta; çıkıntının saçağı 30 cm önde); 15:11 veranda 50 cm. "
            "Excel hesaplama motorunun çatı tiplerinden 'beşik + cumba'")


KODLAR = {"besik": ("T1012", "Tek kat çelik, 2+1, 75,6 m² · Seçenek 1: sade beşik"),
          "cumba": ("T1012-C", "Tek kat çelik, 2+1, 75,6 m² · beşik + cumba (verandasız)"),
          "cifte": ("T1012-CV", "Tek kat çelik, 2+1 · beşik + çift cumba, 50 cm veranda")}


def tanim(secim="besik"):
    duzlemler, kalkanlar, kenar_ozel, tip, tip_adi, tip_kaynak = cati(secim)
    p_duvar, p_mahal, p_aciklik, p_kiris, p_sinif = plan(secim)
    kod, ad = KODLAR[secim]
    cati_kaynak = {"besik": "Sade beşik; mahya ön–arka (görseldeki büyük üçgen önde). Eğim, saçak ve kot kör test projeleriyle aynı.",
                   "cumba": ("KT-01'in çatı biçimi (Lokman, 12 Ekim 13:05): ana beşik %33, cumba %33, alçak çatı KT-01'in veranda sundurması gibi %17,8; "
                             "ana çatının güney kalkanı önden 250 cm geride. Verandasız: alçak çatının altı yaşam alanı, ön cephe düz."),
                   "cifte": ("KT-01'in çatı biçimi; Lokman, 12 Ekim 13:49: cumbada öne doğru 30 cm pencere çıkıntısı (küçük üçgen çatısıyla: çift cumba), "
                             "pencerenin ortası cumba makasının ortasında, 1 m veranda. 14:46: cumba ve veranda saçağı aynı hatta, çıkıntı 30 cm önde ve "
                             "kendi saçağı 30 cm. 15:11: veranda 50 cm. Ana çatının güney kalkanı verandanın arka duvarında (önden 80 cm). "
                             "Duvarlar ve veranda 747 × 1012'nin içinde; saçaklar bütün cephelerde 30 cm dışarıda.")}[secim]
    veranda_notu = "50 cm veranda (Lokman, 12 Ekim 15:11; önce 1 m)." if secim == "cifte" else "Verandasız (bayi)."
    cati_blok = {"tip": tip, "tip_adi": tip_adi, "tip_kaynak": tip_kaynak, "sacak": int(S), "topuk": 10, "duvar_ustu": 270,
                 "panel_kalinligi": int(PANEL), "duzlemler": duzlemler, "kalkanlar": kalkanlar}
    if kenar_ozel:
        cati_blok["kenar_ozel"] = kenar_ozel
    return {
        "sema": "portman.yapi_tanimi/0.5-taslak", "kod": kod, "ad": ad, "aile": "tek_kat_celik", "paket": "baz", "birim": "cm", "kat": "zemin",
        "kaynak": {"cizim": ("Bayinin gönderdiği plan fotoğrafı (12 Ekim 2026; 747 × 1012, TOPLAM 75.5 M2): iç ölçüler perspektif düzeltmesiyle "
                             "okundu (±5 cm); açıklık ölçüleri plandaki etiketlerden. " + veranda_notu + " Yapı çelik (Lokman, 12 Ekim 12:49)."),
                   "koordinat": "Köken binanın güneybatı dış köşesi; +x doğu, +y kuzey; güney ön cephe.",
                   "cati": cati_kaynak},
        "kat_yuksekligi": 270, "duvar_panelleri": "tahmin",
        "yuz_kaplamalari": {"dis": {"kalinlik": K, "malzeme": ["boardex"]}, "ic": {"kalinlik": K, "malzeme": ["alcipan"]}},
        "duvar_siniflari": {"dis": {"ad": "dış duvar (DIS-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
                            "ic": {"ad": "iç duvar (IC-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}}, **p_sinif},
        "duvarlar": p_duvar, "mahaller": p_mahal, "acikliklar": p_aciklik, "kirisler": p_kiris, "lento": 70,
        "osb_takviye": {"duvarlar": [{"mahal": "Yaşam Alanı", "duvar": "DD", "duvar_adi": "doğu dış duvar", "neden": "mutfak dolabı ve eviye"},
                                     {"mahal": "Yaşam Alanı", "duvar": "I1", "duvar_adi": "yatak odaları ile yaşam alanı arası duvar", "neden": "TV ünitesi"}],
                        "teyit": "plan (bayinin planındaki mutfak tezgâhı ve TV ünitesi)"},
        "cati": cati_blok,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Bayi talebi (12 Ekim 2026) Yapı Tanımı")
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--cati", choices=list(KODLAR), default="besik")
    a = ap.parse_args()
    t = tanim(a.cati)
    a.cikti.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", a.cikti, "|", t["kod"], "| duvar", len(t["duvarlar"]), "| mahal", len(t["mahaller"]), "| açıklık", len(t["acikliklar"]),
          "| kiriş", len(t["kirisler"]),
          "| düzlem", len(t["cati"]["duzlemler"]), "| kalkan", len(t["cati"]["kalkanlar"]))
