#!/usr/bin/env python3
"""KT-01 (kör test) Yapı Tanımı 0.5: projenin DWG'sinden (zemin kat planı, teknik özellikler, açıklama notları) ve SKP modelinden
(duvar panellerinin kutuları, açıklık çerçeveleri, makas üstü çatı yüzeyleri) okunan değerler. Yükleme listesi ve paftalardaki
adetler okunmadı. Müşteri projesinin geometrisidir; Lokman'ın onayıyla depoda (8 Ekim 2026 07:23). Ad, telefon ve fiyat içermez.

Kullanım: python kt01_tanim_uret.py KT01.json

Koordinat: plan (cm). Köken, DWG'deki planın sol-alt dış köşesi; +x doğu, +y kuzey. SKP dünya koordinatı = plan + (0; 365,6).
"""
import json
import sys
from pathlib import Path

DY = 365.6                       # SKP y − plan y
E_ANA = (436.8 - 280.0) / 477.0  # ana çatı eğimi (makas üstü: saçak ucunda 280, mahyada 436,8; yarı açıklık 477)
E_VER = (329.5 - 280.0) / 278.0  # veranda sundurması
E_MUS = (250.3 - 223.8) / 336.0  # müştemilat çatısı

def skp(x0, y0, x1, y1):
    return [x0, round(y0 - DY, 2), x1, round(y1 - DY, 2)]

duvarlar = [
    # bina dış duvarları (karkas 80 mm; kutular SKP'deki karkas panelleri)
    {"ad": "D1", "sinif": "dis", "kutu": skp(324, 368.6, 332, 760.6), "yukseklik": 270, "not": "batı duvarı, güney parçası"},
    {"ad": "D2", "sinif": "dis", "kutu": skp(324, 760.6, 332, 1272.6), "yukseklik": 270, "not": "batı duvarı, kuzey parçası (müştemilata bakar)"},
    {"ad": "D3", "sinif": "dis", "kutu": skp(332, 1264.6, 702, 1272.6), "yukseklik": 270, "not": "kuzey duvarı, batı parçası"},
    {"ad": "D4", "sinif": "dis", "kutu": skp(702, 1264.6, 1218, 1272.6), "yukseklik": 270, "not": "kuzey duvarı, doğu parçası"},
    {"ad": "D5", "sinif": "dis", "kutu": skp(1210, 894.6, 1218, 1264.6), "yukseklik": 270, "not": "doğu duvarı, kuzey parçası"},
    {"ad": "D6", "sinif": "dis", "kutu": skp(1210, 608.6, 1218, 894.6), "yukseklik": 270, "not": "doğu duvarı, güney parçası"},
    {"ad": "D7", "sinif": "dis", "kutu": skp(700, 608.6, 1210, 616.6), "yukseklik": 270, "not": "verandanın arka duvarı (giriş kapısı)"},
    {"ad": "D8", "sinif": "dis", "kutu": skp(692, 376.6, 700, 616.6), "yukseklik": 270, "not": "salon ile veranda arası"},
    {"ad": "D9", "sinif": "dis", "kutu": skp(332, 368.6, 700, 376.6), "yukseklik": 270, "not": "güney duvarı (salon)"},
    # iç duvarlar
    {"ad": "D10", "sinif": "ic", "kutu": skp(332, 916.6, 692, 924.6), "yukseklik": 270, "not": "salon ile yatak odası 1 arası (TV ünitesi bu duvarda)"},
    {"ad": "D11", "sinif": "ic", "kutu": skp(692, 916.6, 700, 1034.6), "yukseklik": 240, "kaplama_yuksekligi": 270,
     "not": "hol ile yatak odası 1 arası; üstünde KRS3 kirişi (240–270)"},
    {"ad": "D12", "sinif": "ic", "kutu": skp(640, 1034.6, 820, 1042.6), "yukseklik": 270, "not": "banyonun güney duvarı"},
    {"ad": "D13", "sinif": "ic", "kutu": skp(632, 1034.6, 640, 1264.6), "yukseklik": 270, "not": "banyo ile yatak odası 1 arası"},
    {"ad": "D14", "sinif": "ic", "kutu": skp(820, 916.6, 828, 1264.6), "yukseklik": 270, "not": "hol ve banyo ile yatak odası 2 arası"},
    {"ad": "D15", "sinif": "ic", "kutu": skp(828, 916.6, 1210, 924.6), "yukseklik": 270, "not": "mutfak ile yatak odası 2 arası"},
    # müştemilat duvarları (ek yapı; üst kotları çatı eğiminde)
    {"ad": "MD1", "sinif": "ek", "kutu": skp(3, 756.6, 324, 764.6), "yukseklik": {"bas": 225.0, "son": 250.3}, "not": "müştemilatın güney duvarı (kapı)"},
    {"ad": "MD2", "sinif": "ek", "kutu": skp(3, 764.6, 11, 1264.6), "yukseklik": 225, "not": "müştemilatın batı duvarı"},
    {"ad": "MD3", "sinif": "ek", "kutu": skp(3, 1264.6, 324, 1272.6), "yukseklik": {"bas": 225.0, "son": 250.3}, "not": "müştemilatın kuzey duvarı (vasistas)"},
    # veranda: korkuluk duvarları, kapı çerçevesi, dikme
    {"ad": "VD1", "sinif": "korkuluk", "kutu": skp(830, 368.6, 1188, 376.6), "yukseklik": 70, "not": "veranda korkuluğu, güney"},
    {"ad": "VD2", "sinif": "korkuluk", "kutu": skp(1210, 376.6, 1218, 608.6), "yukseklik": 70, "not": "veranda korkuluğu, doğu"},
    {"ad": "VD3", "sinif": "korkuluk", "kutu": skp(700, 368.6, 830, 376.6), "yukseklik": 240,
     "not": "veranda girişi çerçevesi (90 × 200 geçit); üstünde KRS1 kirişi (kirişin kaplaması kirişlerde sayılır)"},
    {"ad": "KLN1", "sinif": "kolon", "kutu": skp(1188, 368.6, 1218, 376.6), "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "veranda dikmesi (sırt 8, genişlik 30)"},
    # baca (salonun güneybatı köşesinde; dört dar panel; kütlesi tek kutu)
    {"ad": "BACA", "sinif": "baca", "kutu": skp(332, 376.6, 368, 412.6), "yukseklik": 270, "ust_kot": 436.8, "not": "baca: dış karkas yapılacak, içi alıcıya ait (açıklama 7)"},
]

mahaller = [
    {"ad": "Yatak Odası 1", "nokta": [480, 780], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 10.80},
    {"ad": "Banyo", "nokta": [730, 790], "sinif": "ic", "islev": ["banyo"], "islak": True, "etiket_m2": 3.90},
    {"ad": "Yatak Odası 2", "nokta": [1020, 730], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 13.00},
    {"ad": "Salon - Mutfak", "nokta": [500, 300], "sinif": "ic", "islev": ["salon", "mutfak", "hol"], "etiket_m2": 36.35, "etiket_yeri": [980, 420],
     "not": "Hol aynı mahalde: salon ile mutfak arasında duvar yok (KRS3 kirişi), hol mutfağa açık"},
    {"ad": "Müştemilat", "nokta": [160, 650], "sinif": "ek", "islev": ["depo"], "etiket_m2": 15.90},
    {"ad": "Veranda", "nokta": [950, 120], "sinif": "veranda", "islev": ["veranda"], "etiket_m2": 12.43},
]

# Açıklıklar: yer duvarın uzun ekseninde (plan koordinatı). Pencereler çizimdeki etiket ölçüsüyle (180/180, 120/120, 60/40), çizimdeki ortasına göre;
# denizlik ve başlık kotları SKP'deki çerçeveden (denizlik üstü 20 / 80 / 160, başlık altı 200). Kapı boşlukları SKP'deki çerçeveden.
def pencere(ad, duvar, a, b, en, yuk, alt, mahal):
    orta = (a + b) / 2
    return {"ad": ad, "tur": "pencere", "duvar": duvar, "bas": round(orta - en / 2, 2), "en": en, "yuk": yuk, "alt": alt, "mahal": mahal, "etiket": f"{en}/{yuk}"}

acikliklar = [
    pencere("P1", "D1", 132.2, 311.0, 180, 180, 20, "Salon - Mutfak"),
    pencere("P2", "D9", 435.0, 613.8, 180, 180, 20, "Salon - Mutfak"),
    pencere("P3", "D7", 885.0, 1063.8, 180, 180, 20, "Salon - Mutfak"),
    pencere("P4", "D3", 414.0, 534.0, 120, 120, 80, "Yatak Odası 1"),
    pencere("P5", "D4", 740.0, 800.0, 60, 40, 160, "Banyo"),
    pencere("P6", "D4", 968.0, 1088.0, 120, 120, 80, "Yatak Odası 2"),
    pencere("P7", "MD3", 117.9, 177.9, 60, 40, 160, "Müştemilat"),
    {"ad": "K1", "tur": "dis_kapi", "duvar": "D7", "bas": 715.0, "en": 95, "yuk": 210, "mentese": "bas", "acilim": "ust", "mahal": "Salon - Mutfak",
     "not": "giriş kapısı; SKP'de çerçeve boşluğu 95,2 × 210; kapı alıcıya ait"},
    {"ad": "K2", "tur": "dis_kapi", "duvar": "MD1", "bas": 21.0, "en": 95, "yuk": 210, "mentese": "bas", "acilim": "ust", "mahal": "Müştemilat",
     "not": "müştemilat kapısı; SKP'de çerçeve boşluğu 95,2; planda kanat 80 çizilmiş (21–101); kapı alıcıya ait"},
    {"ad": "K3", "tur": "ic_kapi", "duvar": "D11", "bas": round(930.2 - DY, 2), "en": 90, "yuk": 214, "mentese": "bas", "acilim": "sol", "kanat": [80, 200], "mahal": "Yatak Odası 1"},
    {"ad": "K4", "tur": "ic_kapi", "duvar": "D14", "bas": round(934.6 - DY, 2), "en": 90, "yuk": 214, "mentese": "bas", "acilim": "sag", "kanat": [80, 200], "mahal": "Yatak Odası 2"},
    {"ad": "K5", "tur": "ic_kapi", "duvar": "D12", "bas": 725.2, "en": 80, "yuk": 214, "mentese": "son", "acilim": "ust", "kanat": [70, 200], "mahal": "Banyo",
     "not": "banyo kapısı: çerçeve boşluğu 80 (SKP 80,2; planda 79,6); kural 90 der"},
    {"ad": "G1", "tur": "gecit", "duvar": "VD3", "bas": 720.7, "en": 90, "yuk": 200, "mahal": "Veranda", "giris": True, "not": "veranda girişi; kapı yok"},
]

kirisler = [
    {"ad": "KRS1", "kutu": skp(660, 368.6, 1210, 376.6), "alt": 240, "ust": 270, "acik": [[700, 1210]], "bolge": "veranda", "not": "veranda kirişi, güney; 660–700 arası D9'un içinde"},
    {"ad": "KRS2", "kutu": skp(1210, 368.6, 1218, 648.6), "alt": 240, "ust": 270, "acik": [[3, 243]], "bolge": "veranda", "not": "veranda kirişi, doğu; 243–283 arası D6'nın içinde"},
    {"ad": "KRS3", "kutu": skp(692, 576.6, 700, 1034.6), "alt": 240, "ust": 270, "acik": [[251, 551]], "bolge": "Salon - Mutfak",
     "not": "salon ile mutfak arasındaki açıklığın kirişi; 211–251 arası D8'in, 551–669 arası D11'in üstünde"},
]

# ── çatı: makas üstü yüzeyler (SKP'deki çatı yüzleri); plan koordinatı ─────────────────────────────────────────────────────
XB, XD = 294.0, 1248.0            # batı ve doğu saçak uçları (karkasın dış yüzünden 30 cm)
YK, YG, YC = 1302.6 - DY, 586.6 - DY, 338.6 - DY     # kuzey kalkan ucu 937; ana çatının güney kalkan ucu 221; cumbanın ve verandanın güney ucu −27
YD = 616.6 - DY                   # ana çatının güney kalkan duvarı 251: alçak çatılar buraya dayanır
XM, XC, XS = 771.0, 512.0, 730.0  # ana mahya; cumba mahyası; cumbanın doğu saçağı = veranda sundurmasının batı ucu
oran = E_VER / E_ANA              # kırma ve vadi çizgilerinin planda x/y oranı
def kirma_x(y): return XD - oran * (y - YC)      # doğu yüzü ile veranda sundurmasının kesişimi (kırma)
def vadi_x(y): return XS - oran * (y - YC)       # cumbanın doğu yüzü ile veranda sundurmasının kesişimi (vadi)
r2 = lambda v: round(v, 2)
duzlemler = [
    {"ad": "batı", "plan": [[XB, YC], [XC, YC], [XC, YG], [XM, YG], [XM, YK], [XB, YK]], "yukari": [1, 0], "egim": round(E_ANA, 5), "sacak_kotu": 280.0, "sacak": {"x": XB},
     "not": "ana çatının batı yüzü; güneyde cumbanın batı yüzüyle aynı düzlem"},
    {"ad": "doğu", "plan": [[XM, YG], [r2(kirma_x(YG)), YG], [XD, YC], [XD, YK], [XM, YK]], "yukari": [-1, 0], "egim": round(E_ANA, 5), "sacak_kotu": 280.0, "sacak": {"x": XD},
     "not": "ana çatının doğu yüzü; güneydoğuda veranda sundurmasıyla kırma yapar"},
    {"ad": "cumba doğu", "plan": [[XC, YC], [XS, YC], [r2(vadi_x(YD)), YD], [XC, YD]], "yukari": [-1, 0], "egim": round(E_ANA, 5), "sacak_kotu": 280.0, "sacak": {"x": XS},
     "not": "cumbanın doğu yüzü; veranda sundurmasıyla vadi yapar; 221–251 arası ana çatının saçağının altında"},
    {"ad": "veranda", "plan": [[XS, YC], [XD, YC], [r2(kirma_x(YD)), YD], [r2(vadi_x(YD)), YD]], "yukari": [0, 1], "egim": round(E_VER, 5), "sacak_kotu": 280.0, "sacak": {"y": YC},
     "not": "veranda sundurması; ana çatının güney kalkan duvarına dayanır"},
    {"ad": "müştemilat", "plan": [[-12.0, 741.6 - DY], [324.0, 741.6 - DY], [324.0, 1287.6 - DY], [-12.0, 1287.6 - DY]], "yukari": [1, 0], "egim": round(E_MUS, 5),
     "sacak_kotu": 223.8, "sacak": {"x": -12.0}, "ust_yapi": "cati_paneli", "panel_kalinligi": 8.0,
     "not": "müştemilat çatısı: çatı paneli + üstüne sandviç panel (açıklama 9); bina duvarına dayanır"},
]
for d in duzlemler:
    d["plan"] = [[r2(x), r2(y)] for x, y in d["plan"]]
# kenar türü koddan çıkmayanlar: bir duvara dayanan üst kenarlar
kenar_ozel = [
    {"duzlem": "veranda", "p": [r2(kirma_x(YD)), r2(YD)], "q": [r2(vadi_x(YD)), r2(YD)], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
    {"duzlem": "cumba doğu", "p": [r2(vadi_x(YD)), r2(YD)], "q": [XC, r2(YD)], "tur": "duvar_dibi", "not": "ana çatının güney kalkan duvarı"},
    {"duzlem": "müştemilat", "p": [324.0, r2(741.6 - DY)], "q": [324.0, r2(1287.6 - DY)], "tur": "duvar_dibi", "not": "binanın batı duvarı"},
    {"duzlem": "veranda", "p": [r2(kirma_x(YG)), r2(YG)], "q": [r2(kirma_x(YD)), r2(YD)], "tur": "gizli", "not": "kırmanın, ana çatının güney saçağının altında kalan 30 cm'lik kısmı"},
    {"duzlem": "cumba doğu", "p": [XC, r2(YD)], "q": [XC, r2(YG)], "tur": "gizli", "not": "cumba mahyasının, ana çatının güney saçağının altında kalan 30 cm'lik kısmı"},
]
# kalkanlar (alın duvarları): dış kaplama alır. Çizgi: kalkanın planda durduğu yer; aralık: duvarın uçları (dış yüzler)
kalkanlar = [
    {"ad": "kuzey kalkanı", "eksen": "y", "konum": 910.0, "aralik": [321.0, 1221.0], "ic": "guney", "ust": ["batı", "doğu"], "not": "ana çatı; kuzey duvarının üstü"},
    {"ad": "cumba kalkanı", "eksen": "y", "konum": 0.0, "aralik": [321.0, 730.0], "ic": "kuzey", "ust": ["batı", "cumba doğu", "veranda"], "not": "cumbanın güney alnı; 703–730 arası verandanın üstünde"},
    {"ad": "güney kalkanı (alçak çatıların üstü)", "eksen": "y", "konum": 251.0, "aralik": [321.0, 1221.0], "ic": "kuzey", "ust": ["batı", "doğu"], "alt": ["cumba doğu", "veranda"],
     "not": "ana çatının güney kalkanı; cumbanın ve veranda sundurmasının üstünde kalan kısmı"},
]
# makaslar (SKP; çizim ve IFC için): tam açıklıklı 7, cumba 3, veranda 4 + 1 çapraz + 1 yarım
makaslar = {
    "tam": {"x": [XB, XD], "y": [r2(v - DY) for v in (1264.6, 1139.6, 1014.6, 940.6, 866.6, 741.6, 616.6)], "kalinlik": 8, "adet": 7},
    "cumba": {"x": [XB, XS], "y": [r2(v - DY) for v in (608.6, 493.6, 368.6)], "kalinlik": 8, "adet": 3},
    "veranda": {"y": [r2(YC), r2(YD)], "x": [730.0, 855.0, 980.0, 1088.6], "kalinlik": 8, "adet": 4},
    "diger": {"adet": 2, "not": "MKS15 (kırma boyunca çapraz), MKS16 (yarım)"},
}

tanim = {
    "sema": "portman.yapi_tanimi/0.5-taslak",
    "kod": "KT-01",
    "ad": "Tek kat çelik, 2+1, müştemilatlı, 98,65 m² (kör test projesi)",
    "aile": "tek_kat_celik",
    "paket": "proje",
    "birim": "cm",
    "kat": "zemin",
    "kaynak": {
        "cizim": "Projenin DWG'si (zemin kat planı, teknik özellikler ve açıklama notları) ve SKP karkas modeli; 6 Ekim 2026'da okundu.",
        "okunmayanlar": "Klasördeki yükleme listesi ve Excel hesaplama motoru bu tanım ve liste üretilip kaydedilene kadar açılmadı. Montaj paftalarındaki adetler (kaplama, omega, aşık, iniş) girdi olarak kullanılmadı.",
        "koordinat": "Köken planın sol-alt dış köşesi; +x doğu, +y kuzey. Ön cephe güney (veranda ve giriş).",
    },
    "kat_yuksekligi": 270,
    "teknik_ozellikler": {
        "Bina yüksekliği": "2700 mm", "Dış duvarlar": "80 mm", "İç duvarlar": "80 mm", "Panel türü": "galvanizli yapısal çelik", "Çatı şekli": "beşik + cumba",
        "Çatı kaplaması": "4 cm poliüretan sandviç panel", "Çatı kaplama rengi": "antrasit gri", "Dış kapı": "alıcıya ait", "İç kapılar": "melamin panel kapı",
        "Dış cephe boya": "alıcıya ait", "İç cephe boya": "alıcıya ait", "Pencere": "alıcıya ait (pencere rengi ve pencere detayı kutularında)", "Tavan": "ters tavan",
        "Saçak ve alın rengi": "antrasit gri",
    },
    "aciklama_notlari": [
        "1- Dış cephe panelleri, dıştan içe: Boardex + nem bariyeri + çelik karkas + OSB + alçıpan",
        "2- İç cephe panelleri: alçıpan + OSB + çelik karkas + OSB + alçıpan",
        "3- Çatı izolasyon Knauf Earthwool",
        "4- Vitrifiye alıcıya ait.", "5- Tesisat alıcıya ait.", "6- Bataryalar alıcıya ait.",
        "7- Baca dış karkas yapılacak. İçi alıcıya ait.",
        "8- Müştemilat dış duvarları 80x45x08 olacak. Mineral yün olmayacak. Bina duvarı boardex + nem bariyeri olacak.",
        "9- Müştemilat çatısı çatı paneli ile kapatılıp üzerine sandviç panel yapılacak.",
        "10- Veranda etrafına korkuluk yapılacak.",
    ],
    "kapsam": {"dis_kapi": False, "pencere": False, "boya": False, "vitrifiye": False, "sihhi_tesisat": False, "elektrik": True,
               "kaynak": "teknik özellikler ve açıklama notları 4–6: alıcıya ait olanlar listeye girmez"},
    "yuz_kaplamalari": {
        "dis": {"kalinlik": 3.0, "malzeme": ["boardex", "nem_bariyeri"],
                "not": "Çizimde ve SKP'de karkasın dış yüzü ile dış ölçü arası 3 cm. Malzeme Boardex 12,5 mm + nem bariyeri; kalan pay çizimin."},
        "dis_ek": {"kalinlik": 1.25, "malzeme": ["boardex", "nem_bariyeri"], "not": "bina duvarının müştemilata bakan yüzü (açıklama 8)"},
        "ic": {"kalinlik": 2.35, "malzeme": ["osb", "alcipan"], "not": "OSB 11 mm + alçıpan 12,5 mm (açıklama 1 ve 2)"},
    },
    "duvar_siniflari": {
        "dis": {"ad": "bina dış duvarı", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis", "ek": "dis_ek"}},
        "ic": {"ad": "iç duvar", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}},
        "ek": {"ad": "müştemilat dış duvarı", "profil": "80x45x0,8", "yalitim": False, "yuz": {"ek": "ic", "dis": "dis"},
               "not": "açıklama 8: 80x45x08, mineral yün yok. İç yüzü açıklama 1'e göre OSB + alçıpan sayıldı (varsayım)"},
        "korkuluk": {"ad": "veranda korkuluğu ve giriş çerçevesi", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}},
        "kolon": {"ad": "veranda dikmesi", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}},
        "baca": {"ad": "baca", "profil": "80x45x1,2", "yalitim": False, "yuz": {"ic": "ic"}},
    },
    "duvarlar": duvarlar,
    "mahaller": mahaller,
    "acikliklar": acikliklar,
    "kirisler": kirisler,
    "lento": 70,
    "cati": {
        "tip": "besik_cumba", "tip_kaynak": "teknik özellikler: çatı şekli 'beşik + cumba'",
        "yontem": "omega_asik", "yontem_kaynak": "projenin DWG'sinde tavan omegası ve aşık paftaları var (yöntem B)",
        "kaplama": "sandvic_panel", "kaplama_kaynak": "teknik özellikler: 4 cm poliüretan sandviç panel",
        "sacak": 30, "topuk": 10, "duvar_ustu": 270,
        "duzlemler": duzlemler, "kenar_ozel": kenar_ozel, "kalkanlar": kalkanlar, "makaslar": makaslar,
        "izolasyon": "Knauf Earthwool (açıklama 3)",
    },
}

if __name__ == "__main__":
    yol = Path(sys.argv[1])
    yol.write_text(json.dumps(tanim, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", yol, "| duvar", len(duvarlar), "| mahal", len(mahaller), "| açıklık", len(acikliklar), "| düzlem", len(duzlemler))
    for d in duzlemler:
        print("  ", d["ad"], d["plan"], "eğim", d["egim"])
