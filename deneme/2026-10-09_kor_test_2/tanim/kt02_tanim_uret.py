#!/usr/bin/env python3
"""KT-02 (ikinci kör test) Yapı Tanımı 0.5: projenin montaj paftasından (müşteri onay paftası: plan, teknik özellikler, açıklama notları;
duvar paneli yerleşimi; makas ve panel yerleşimi; elektrik yerleşimi) ve üretim dosyasından (rulo form makinesinin CSV'leri) okunan değerler.
Yükleme listesi okunmadı. Montaj paftalarındaki adetler (çatı kaplaması, tavan omegası, aşık, dere inişi) ve çatı kaplama malzemesi paftası
girdi olarak kullanılmadı. Müşteri projesinin geometrisidir; ad, telefon ve fiyat içermez.

Kullanım: python kt02_tanim_uret.py KT02.json KT02_profil_boylari.json
    (profil boyları: ../uretim_profil.py <üretim klasörü> --json KT02_profil_boylari.json)

Koordinat: plan (cm). Köken planın sol-alt dış köşesi (verandanın güney dış çizgisi ile batı duvarının dış yüzü); +x doğu, +y kuzey.
Paftada kuzey işareti yok: çizimin üstü kuzey alındı. Karkasın dış yüzü dış çizginin 3 cm içinde (770 → 764; 1170 → 1164).
Ölçüler: duvar, kiriş ve kolon boyları üretim dosyasındaki çerçeve boylarından; yerleri duvar paneli yerleşim paftasından (vektör çizgileri,
duvarlarla ölçeklenerek); açıklıkların yeri ve boyu çerçevelerdeki dikme ve başlıklardan.
"""
import json
import re
import sys
from pathlib import Path

E = 0.32878                      # çatı eğimi: makasların üst başlığı (MKS05: 1351,2 / 4109,8); kırma uçlarındaki paneller de aynı eğimde
KX0, KX1, KY0, KY1 = 3.0, 767.0, 3.0, 1167.0     # karkasın dış çizgisi (veranda dahil)
YG = 240.0                       # kapalı kısmın güney duvarının dış yüzü (veranda 237: kolonların dış yüzüne kadar)
S = 30.0                         # saçak (makas 8240 = 764 + 2 × 30)
r2 = lambda v: round(v, 2)

duvarlar = [
    # bina dış duvarları (karkas 80 mm). Çerçeveler dışarıdan bakışla saat yönünün tersine numaralı: D01 doğu duvarının güney parçası.
    {"ad": "D01", "sinif": "dis", "kutu": [759.0, YG, 767.0, 790.0], "yukseklik": 270, "not": "doğu duvarı, güney parçası (mutfak ve banyo); güney ucunda KRS01'in yuvası"},
    {"ad": "D02", "sinif": "dis", "kutu": [759.0, 790.0, 767.0, 1167.0], "yukseklik": 270, "not": "doğu duvarı, kuzey parçası (yatak odası 2)"},
    {"ad": "D03", "sinif": "dis", "kutu": [385.5, 1159.0, 759.0, 1167.0], "yukseklik": 270, "not": "kuzey duvarı, doğu parçası"},
    {"ad": "D04", "sinif": "dis", "kutu": [3.0, 1159.0, 385.5, 1167.0], "yukseklik": 270, "not": "kuzey duvarı, batı parçası"},
    {"ad": "D05", "sinif": "dis", "kutu": [3.0, 789.0, 11.0, 1159.0], "yukseklik": 270, "not": "batı duvarı, kuzey parçası (yatak odası 1)"},
    {"ad": "D06", "sinif": "dis", "kutu": [3.0, YG, 11.0, 789.0], "yukseklik": 270, "not": "batı duvarı, güney parçası (giriş kapısı, salon); sundurma kirişlerinin yuvaları"},
    {"ad": "D07", "sinif": "dis", "kutu": [11.0, YG, 584.0, 248.0], "yukseklik": 270, "not": "güney duvarı, batı parçası (300/200 doğrama); KRS06'nın geçtiği yuva"},
    {"ad": "D08", "sinif": "dis", "kutu": [584.0, YG, 759.0, 248.0], "yukseklik": 270, "not": "güney duvarı, doğu parçası"},
    # iç duvarlar
    {"ad": "D101", "sinif": "ic", "kutu": [520.0, 574.5, 759.0, 582.5], "yukseklik": 270, "not": "banyonun güney duvarı (mutfakla arası)"},
    {"ad": "D102", "sinif": "ic", "kutu": [512.0, 574.5, 520.0, 764.0], "yukseklik": 270, "not": "banyonun batı duvarı (banyo kapısı); güney ucunda KRS06'nın yuvası"},
    {"ad": "D103", "sinif": "ic", "kutu": [385.0, 764.0, 759.0, 772.0], "yukseklik": 270, "not": "holün kuzey duvarı, doğu parçası (yatak odası 2 kapısı)"},
    {"ad": "D104", "sinif": "ic", "kutu": [11.0, 764.0, 385.0, 772.0], "yukseklik": 270, "not": "holün kuzey duvarı, batı parçası (yatak odası 1 kapısı)"},
    {"ad": "D105", "sinif": "ic", "kutu": [381.0, 772.0, 389.0, 1159.0], "yukseklik": 270, "not": "iki yatak odasının arası"},
    {"ad": "D106", "sinif": "ic", "kutu": [11.0, 614.5, 512.0, 622.5], "yukseklik": 270, "not": "holün güney duvarı (salon kapısı)"},
    # veranda korkulukları (A01–A04: 80 × 45 × 0,8; yükseklik 84,5 cm; üretim dosyası "VERANDA DUVAR")
    {"ad": "A01", "sinif": "korkuluk", "kutu": [759.0, 11.0, 767.0, YG], "yukseklik": 84.5, "not": "veranda korkuluğu, doğu"},
    {"ad": "A02", "sinif": "korkuluk", "kutu": [531.0, KY0, 737.0, 11.0], "yukseklik": 84.5, "not": "veranda korkuluğu, güney, doğu parçası (KLN02 ile KLN01 arası)"},
    {"ad": "A03", "sinif": "korkuluk", "kutu": [33.0, KY0, 165.0, 11.0], "yukseklik": 84.5, "not": "veranda korkuluğu, güney, batı parçası (KLN04 ile KLN03 arası)"},
    {"ad": "A04", "sinif": "korkuluk", "kutu": [3.0, 11.0, 11.0, YG], "yukseklik": 84.5, "not": "veranda korkuluğu, batı"},
    # kolonlar (sırt 8, genişlik 29,5; 240 cm): verandada dört, sundurmada iki
    {"ad": "KLN01", "sinif": "kolon", "kutu": [737.0, KY0, 767.0, 11.0], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "veranda, güneydoğu köşesi"},
    {"ad": "KLN02", "sinif": "kolon", "kutu": [501.0, KY0, 531.0, 11.0], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "veranda, KRS06'nın altı"},
    {"ad": "KLN03", "sinif": "kolon", "kutu": [165.0, KY0, 195.0, 11.0], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "veranda, KRS04 ile KRS03'ün birleşimi"},
    {"ad": "KLN04", "sinif": "kolon", "kutu": [3.0, KY0, 33.0, 11.0], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "veranda, güneybatı köşesi"},
    {"ad": "KLN05", "sinif": "kolon", "kutu": [-149.7, 603.9, -119.7, 611.9], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "sundurma, güneybatı köşesi"},
    {"ad": "KLN06", "sinif": "kolon", "kutu": [-149.7, 745.9, -119.7, 753.9], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "sundurma, kuzeybatı köşesi"},
]

mahaller = [
    {"ad": "Yatak Odası 1", "nokta": [200, 960], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 14.26},
    {"ad": "Yatak Odası 2", "nokta": [570, 960], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 14.26},
    {"ad": "Hol", "nokta": [260, 690], "sinif": "ic", "islev": ["hol"], "etiket_m2": 7.08},
    {"ad": "Banyo", "nokta": [640, 670], "sinif": "ic", "islev": ["banyo"], "islak": True, "etiket_m2": 4.33},
    {"ad": "Yaşama Mekanı", "nokta": [300, 420], "sinif": "ic", "islev": ["salon", "mutfak"], "etiket_m2": 26.42,
     "not": "salon ve mutfak aynı mahalde (mutfak doğu duvarı boyunca; arada KRS06 kirişi var, duvar yok)"},
    {"ad": "Veranda", "poligon": [[KX0, KY0], [KX1, KY0], [KX1, YG], [KX0, YG]], "sinif": "veranda", "islev": ["veranda"], "etiket_m2": 18.4,
     "not": "kolonlu ve korkuluklu açık veranda; giriş KLN03 ile KLN02 arası (korkuluksuz)"},
    {"ad": "Sundurma", "poligon": [[-149.7, 603.9], [KX0, 603.9], [KX0, 753.9], [-149.7, 753.9]], "sinif": "veranda", "islev": ["veranda"], "etiket_m2": 2.25,
     "not": "giriş kapısının önündeki açık sundurma (iki kolon, üç kiriş, kendi çatısı)"},
]


def pencere(ad, duvar, orta, en, yuk, alt, mahal):
    return {"ad": ad, "tur": "pencere", "duvar": duvar, "bas": r2(orta - en / 2), "en": en, "yuk": yuk, "alt": alt, "mahal": mahal, "etiket": f"{en}/{yuk}"}


# Açıklıklar: yer, üretim dosyasındaki çerçevelerin dikme ve başlıklarından (net açıklığın ortası); ölçü etiketteki doğrama ölçüsü.
# Denizlik ve başlık: 180'lik pencerede 19,5–200,5; 120'likte 79,5–200,5; 100'lükte 99,5–200,5; 40'lıkta 159,5–200,5; 300/200'de 19,5–220,5 (net açıklık 1 cm geniş).
acikliklar = [
    pencere("P1", "D05", 969.63, 120, 180, 20, "Yatak Odası 1"),
    pencere("P2", "D02", 969.63, 120, 120, 80, "Yatak Odası 2"),
    pencere("P3", "D06", 431.25, 120, 180, 20, "Yaşama Mekanı"),
    pencere("P4", "D01", 415.01, 120, 100, 100, "Yaşama Mekanı"),
    pencere("P5", "D01", 723.39, 60, 40, 160, "Banyo"),
    pencere("P6", "D07", 345.0, 300, 200, 20, "Yaşama Mekanı"),
    {"ad": "K1", "tur": "dis_kapi", "duvar": "D06", "bas": r2(685.33 - 47.5), "en": 95, "yuk": 210, "mentese": "son", "acilim": "sag", "mahal": "Hol",
     "not": "giriş kapısı (sundurmadan hole); çerçevede net açıklık 96,2 × 210; teknik özellikler: dış kapı çelik standart"},
    {"ad": "K2", "tur": "ic_kapi", "duvar": "D104", "bas": r2(321.44 - 45), "en": 90, "yuk": 214, "mentese": "son", "acilim": "ust", "kanat": [80, 200], "mahal": "Yatak Odası 1"},
    {"ad": "K3", "tur": "ic_kapi", "duvar": "D103", "bas": r2(448.18 - 45), "en": 90, "yuk": 214, "mentese": "bas", "acilim": "ust", "kanat": [80, 200], "mahal": "Yatak Odası 2"},
    {"ad": "K4", "tur": "ic_kapi", "duvar": "D102", "bas": r2(704.59 - 45), "en": 90, "yuk": 214, "mentese": "son", "acilim": "sag", "kanat": [80, 200], "mahal": "Banyo",
     "not": "banyo kapısı; çerçevede net açıklık 91,2 (KT-01'de 80'di)"},
    {"ad": "K5", "tur": "ic_kapi", "duvar": "D106", "bas": r2(448.08 - 45), "en": 90, "yuk": 214, "mentese": "son", "acilim": "alt", "kanat": [80, 200], "mahal": "Yaşama Mekanı"},
]

# Kirişler (29,5 cm; alt 240, üst 270). Açık: duvarın içinde kalmayan kısım (planda, kirişin ekseni boyunca).
kirisler = [
    {"ad": "KRS01", "kutu": [759.0, KY0, 767.0, 280.0], "alt": 240, "ust": 270, "acik": [[11.0, YG]], "bolge": "veranda", "not": "veranda kirişi, doğu; 240–280 arası D01'in içinde"},
    {"ad": "KRS02", "kutu": [520.0, KY0, 759.0, 11.0], "alt": 240, "ust": 270, "acik": [[520.0, 759.0]], "bolge": "veranda", "not": "veranda kirişi, güney, doğu parçası"},
    {"ad": "KRS03", "kutu": [179.9, KY0, 512.0, 11.0], "alt": 240, "ust": 270, "acik": [[179.9, 512.0]], "bolge": "veranda", "not": "veranda kirişi, güney, orta parça (veranda girişinin üstü)"},
    {"ad": "KRS04", "kutu": [11.0, KY0, 179.9, 11.0], "alt": 240, "ust": 270, "acik": [[11.0, 179.9]], "bolge": "veranda", "not": "veranda kirişi, güney, batı parçası"},
    {"ad": "KRS05", "kutu": [3.0, KY0, 11.0, 280.0], "alt": 240, "ust": 270, "acik": [[11.0, YG]], "bolge": "veranda", "not": "veranda kirişi, batı; 240–280 arası D06'nın içinde"},
    {"ad": "KRS06", "kutu": [512.0, KY0, 520.0, 614.5], "alt": 240, "ust": 270, "acik": [[11.0, YG], [248.0, 574.5]], "acik_bolgeler": ["veranda", "Yaşama Mekanı"],
     "bolge": "veranda", "celik_grubu": "kiris_15",
     "not": "verandayı geçip salon ile mutfağın arasından banyo duvarına (D102) giden kiriş; 80 × 45 × 1,5 (üretim dosyası); 240–248 arası D07'nin içinde, 574,5–614,5 arası D102'nin üstünde"},
    {"ad": "KRS07", "kutu": [-141.7, 603.9, 11.0, 611.9], "alt": 240, "ust": 270, "acik": [[-141.7, KX0]], "bolge": "veranda", "not": "sundurma kirişi, güney; 3–11 arası D06'nın içinde"},
    {"ad": "KRS08", "kutu": [-149.7, 603.9, -141.7, 753.9], "alt": 240, "ust": 270, "acik": [[603.9, 753.9]], "bolge": "veranda", "not": "sundurma kirişi, batı"},
    {"ad": "KRS09", "kutu": [-141.7, 745.9, 11.0, 753.9], "alt": 240, "ust": 270, "acik": [[-141.7, KX0]], "bolge": "veranda", "not": "sundurma kirişi, kuzey; 3–11 arası D06'nın içinde"},
]

# ── çatı ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
XB, XD, YS, YN = KX0 - S, KX1 + S, KY0 - S, KY1 + S        # ana çatının saçak uçları: −27, 797, −27, 1197 (makas paftası: makaslar 211,2–615,2 pt)
XM = (XB + XD) / 2                                         # mahya 385; dört omuz, bütün yüzler aynı eğimde: mahya 385–785
YM0, YM1 = YS + (XD - XB) / 2, YN - (XD - XB) / 2
SX0 = -149.7 - S                                           # sundurmanın batı saçağı
SY0, SY1 = 603.9 - S, 753.9 + S                            # sundurmanın güney ve kuzey saçağı (makas MKS29: 2100 = 150 + 2 × 30)
SYM = (SY0 + SY1) / 2
SXA = SX0 + (SY1 - SY0) / 2                                # sundurmanın kırma ucu
duzlemler = [
    {"ad": "batı", "plan": [[XB, YS], [XM, YM0], [XM, YM1], [XB, YN]], "yukari": [1, 0], "egim": E, "sacak_kotu": 280.0, "sacak": {"x": XB}, "not": "ana çatının batı yüzü"},
    {"ad": "doğu", "plan": [[XD, YS], [XD, YN], [XM, YM1], [XM, YM0]], "yukari": [-1, 0], "egim": E, "sacak_kotu": 280.0, "sacak": {"x": XD}, "not": "ana çatının doğu yüzü"},
    {"ad": "güney", "plan": [[XB, YS], [XD, YS], [XM, YM0]], "yukari": [0, 1], "egim": E, "sacak_kotu": 280.0, "sacak": {"y": YS},
     "not": "ana çatının güney kırma ucu (verandanın üstü); makas paftasında PNL01–03 panelleri"},
    {"ad": "kuzey", "plan": [[XD, YN], [XB, YN], [XM, YM1]], "yukari": [0, -1], "egim": E, "sacak_kotu": 280.0, "sacak": {"y": YN},
     "not": "ana çatının kuzey kırma ucu; makas paftasında PNL04–06 panelleri"},
    {"ad": "sundurma güney", "plan": [[SX0, SY0], [XB, SY0], [XB, SYM], [SXA, SYM]], "yukari": [0, 1], "egim": E, "sacak_kotu": 280.0, "sacak": {"y": SY0},
     "not": "sundurma çatısı; doğu ucu ana çatının saçak ucunda biter"},
    {"ad": "sundurma kuzey", "plan": [[XB, SY1], [SX0, SY1], [SXA, SYM], [XB, SYM]], "yukari": [0, -1], "egim": E, "sacak_kotu": 280.0, "sacak": {"y": SY1},
     "not": "sundurma çatısı"},
    {"ad": "sundurma batı", "plan": [[SX0, SY0], [SXA, SYM], [SX0, SY1]], "yukari": [1, 0], "egim": E, "sacak_kotu": 280.0, "sacak": {"x": SX0},
     "not": "sundurmanın kırma ucu (MKS31–33)"},
]
for d in duzlemler:
    d["plan"] = [[r2(x), r2(y)] for x, y in d["plan"]]
kalkanlar = [
    {"ad": "sundurma alnı", "eksen": "x", "konum": XB, "aralik": [r2(SY0), r2(SY1)], "ic": "bati", "ust": ["sundurma güney", "sundurma kuzey"], "alt": ["batı"],
     "not": "sundurma çatısının, ana çatının saçak ucunun üstünde kalan üçgeni (üretim dosyasında PNL027 çerçevesi bu yüzde)"},
]
# makas yerleri: makas paftasındaki çift çizgilerin ortası (MKS10 kuzeyde 1156,2 … MKS01 güneyde 14,1). Çizim için yalnız mahya altındaki
# tam makaslar; öteki makaslar adetle.
makaslar = {
    "tam": {"x": [XB, XD], "y": [389.1, 518.6, 651.6, 781.2], "kalinlik": 8, "adet": 4, "not": "MKS04–07"},
    "diger": {"adet": 29, "not": "kırma makasları MKS01–03 ve MKS08–10 (üstü kesik), kırma uçlarının saçak makasları MKS11–28, sundurma makasları MKS29–33"},
}

tanim = {
    "sema": "portman.yapi_tanimi/0.5-taslak",
    "kod": "KT-02",
    "ad": "Tek kat çelik, 2+1, verandalı ve sundurmalı, dört omuz çatı, 90 m² (ikinci kör test projesi)",
    "aile": "tek_kat_celik",
    "paket": "proje",
    "birim": "cm",
    "kat": "zemin",
    "kaynak": {
        "cizim": ("Projenin montaj paftası (PDF, sekiz pafta: müşteri onay paftası, duvar paneli yerleşimi, makas ve panel yerleşimi, dere, tavan omegası, aşık, "
                  "çatı kaplaması, elektrik) ve üretim dosyası (rulo form makinesinin CSV'leri, 101 çerçeve); 9 Ekim 2026'da okundu. Girdi: müşteri onay paftası "
                  "(plan, teknik özellikler, açıklama notları), duvar paneli ile makas ve panel yerleşimi (yerler), üretim dosyası (boylar, açıklıklar, et kalınlığı)."),
        "okunmayanlar": ("Klasördeki yükleme listesi (PDF ve Excel) bu tanım ve liste üretilip kaydedilene kadar açılmadı. Montaj paftalarındaki adetler (çatı kaplaması, "
                         "tavan omegası, aşık, dere inişi) ve çatı kaplama malzemesi paftası girdi olarak kullanılmadı; dere paftasına yalnız sundurma çatısının biçimi için bakıldı."),
        "koordinat": "Köken planın sol-alt dış köşesi; +x doğu, +y kuzey (paftada kuzey işareti yok; çizimin üstü kuzey alındı). Ön cephe güney (veranda); giriş batıda, sundurmadan.",
    },
    "kat_yuksekligi": 270,
    "teknik_ozellikler": {
        "Bina yüksekliği": "2700 mm", "Dış duvarlar": "80 mm", "İç duvarlar": "80 mm", "Panel türü": "galvanizli yapısal çelik", "Çatı şekli": "dört omuz çatı",
        "Çatı kaplaması": "sandviç panel", "Çatı kaplama rengi": "antrasit gri", "Dış kapı": "çelik standart", "İç kapılar": "melamin panel kapı",
        "Dış cephe boya": "alıcıya ait", "İç cephe boya": "alıcıya ait", "Pencere rengi": "alıcıya ait", "Tavan": "ters tavan", "Saçak ve alın rengi": "antrasit gri",
        "Pencere detay": "alıcıya ait",
    },
    "aciklama_notlari": [
        "1- Dış cephe panelleri: dıştan içe: Boardex + 80 mm çelik karkas + OSB + alçıpan",
        "2- İç cephe panelleri: alçıpan + OSB + 80 mm çelik karkas + OSB + alçıpan",
        "3- Pencere alıcıya ait.", "4- Vitrifiye alıcıya ait.", "5- Boya alıcıya ait.", "6- Prizler antrasit renk.",
    ],
    "kapsam": {"dis_kapi": True, "pencere": False, "boya": False, "vitrifiye": False, "sihhi_tesisat": True, "elektrik": True,
               "kaynak": "teknik özellikler (dış kapı çelik standart; dış ve iç cephe boyası, pencere: alıcıya ait) ve açıklama notları 3–5 (pencere, vitrifiye, boya: "
                         "alıcıya ait). Tesisat için not yok: listede. Boya: not 5 bütün boyayı alıcıya bırakıyor (KT-01'de yalnız cephe boyaları yazıyordu)"},
    "renk": {"cati": "antrasit gri", "sacak_alin": "antrasit gri", "kaynak": "teknik özellikler"},
    "yuz_kaplamalari": {
        "dis": {"kalinlik": 3.0, "malzeme": ["boardex"],
                "not": "Planda karkasın dış yüzü ile dış ölçü arası 3 cm (764 → 770). Açıklama 1: Boardex + çelik karkas + OSB + alçıpan; nem bariyeri yazmıyor"},
        "ic": {"kalinlik": 2.35, "malzeme": ["osb", "alcipan"], "not": "OSB 11 mm + alçıpan 12,5 mm (açıklama 1 ve 2)"},
    },
    "duvar_siniflari": {
        "dis": {"ad": "bina dış duvarı", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
        "ic": {"ad": "iç duvar", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}},
        "korkuluk": {"ad": "veranda korkuluğu", "profil": "80x45x0,8", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}},
        "kolon": {"ad": "veranda ve sundurma kolonu", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}},
    },
    "duvarlar": duvarlar,
    "mahaller": mahaller,
    "acikliklar": acikliklar,
    "kirisler": kirisler,
    "lento": 70,
    "cati": {
        "tip": "kirma", "tip_kaynak": "teknik özellikler: çatı şekli 'Dört Omuz Çatı'; sundurmanın kendi küçük çatısı var",
        "yontem": "omega_asik", "yontem_kaynak": "montaj paftasında tavan omegası ve aşık paftaları var (yöntem B)",
        "kaplama": "sandvic_panel", "kaplama_kaynak": "teknik özellikler: sandviç panel",
        "sacak": S, "topuk": 10, "duvar_ustu": 270,
        "duzlemler": duzlemler, "kalkanlar": kalkanlar, "makaslar": makaslar,
    },
}

if __name__ == "__main__":
    yol, boylar_yolu = Path(sys.argv[1]), Path(sys.argv[2])
    boylar = json.loads(boylar_yolu.read_text(encoding="utf-8"))

    def grup(desen, haric=()):
        sec = {ad: v for ad, v in boylar.items() if re.fullmatch(desen, ad) and ad not in haric}
        etler = {v["et_mm"] for v in sec.values()}
        assert sec and len(etler) == 1 and None not in etler, (desen, etler)
        return {"paneller": {ad: v["boy_m"] for ad, v in sec.items()}, "profil": "80x45x" + f"{etler.pop():g}".replace(".", ",")}

    tanim["celik_modeli"] = {
        "kaynak": "üretim dosyası (rulo form makinesinin CSV'leri): her çerçevedeki üyelerin boylarının toplamı (m) ve üyelerin et kalınlığı (`../uretim_profil.py`)",
        "gruplar": {
            "dis": grup(r"D0\d"), "ic": grup(r"D1\d\d"), "korkuluk": grup(r"A\d+"), "kolon": grup(r"KLN\d+"),
            "kiris": grup(r"KRS\d+", haric={"KRS06"}), "kiris_15": grup(r"KRS06"),
            "makas": grup(r"MKS\d+"), "cati_panelleri": grup(r"PNL\d+"), "veranda_destek": grup(r"B\d+"),
        },
        "ek_satirlar": [
            {"grup": "kiris_15", "ad": "Kirişler (kiriş paneli, 1,5 mm)", "not": "üretim dosyasında ayrı klasör (80 × 45 × 1,5); panel adedi ve profil boyu modelden"},
            {"grup": "cati_panelleri", "ad": "Çatı panelleri (kırma uçları, saçak ve sundurma)",
             "not": "üretim dosyasında makaslardan ayrı klasör (PANEL): kırma uçlarının yüzleri (PNL01–06), saçak panelleri, sundurmanın panelleri; panel adedi ve profil boyu modelden"},
            {"grup": "veranda_destek", "ad": "Veranda destekleri", "not": "üretim dosyasında 'VERANDA DESTEK' (B01–B04); panel adedi ve profil boyu modelden"},
        ],
    }
    gr = tanim["celik_modeli"]["gruplar"]
    sayilan = {ad for g in gr.values() for ad in g["paneller"]}
    assert sayilan == set(boylar), sorted(set(boylar) ^ sayilan)
    assert len(gr["makas"]["paneller"]) == sum(v["adet"] for v in makaslar.values())
    yol.write_text(json.dumps(tanim, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", yol, "| duvar", len(duvarlar), "| mahal", len(mahaller), "| açıklık", len(acikliklar), "| kiriş", len(kirisler), "| düzlem", len(duzlemler))
    for ad, g in gr.items():
        print(f"   {ad:16s} {len(g['paneller']):2d} çerçeve · profil boyu {sum(g['paneller'].values()):7.2f} m · {g['profil']}")
