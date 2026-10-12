#!/usr/bin/env python3
"""KT-03 (üçüncü kör test) Yapı Tanımı 0.5: projenin montaj paftasından (yedi sayfa: müşteri onay paftası, duvar paneli yerleşimi,
makas ve dere yerleşimi, tavan omegası, aşık, çatı, elektrik) okunan değerler. Üretim dosyası yok: çelik ağırlığı motorun proje
ortalamalarından (katalog yolu), panel adetleri paftadaki yerleşimden. Yükleme listesi okunmadı. Paftalardaki adetler (çatı
kaplaması, tavan omegası, aşık, dere inişi) girdi olarak kullanılmadı. Müşteri projesinin geometrisidir; ad, telefon ve fiyat içermez.

Kullanım: python kt03_tanim_uret.py KT03.json

Koordinat: plan (cm). Köken: verandanın batı dış çizgisi (kolonların dış yüzü); binanın ve verandanın güney dış yüzü y = 0,2
(paftanın vektörlerinden; ölçüler duvar paneli yerleşim paftasındaki ölçü zincirleriyle ±0,5 cm içinde). +x doğu, +y kuzey; paftada
kuzey işareti yok, çizimin üstü kuzey alındı. Duvar kutuları karkas: dış duvar 14,0 cm (teknik özellikler: 140 mm), iç duvar 8,0 cm.
"""
import json
import sys
from pathlib import Path

r2 = lambda v: round(v, 2)
E = 0.33                     # ana çatının eğimi (dört yüz de aynı; makas ve çatı paftasındaki açılımdan)
S = 30.0                     # saçak (makas paftası: "Saçaklar ve alın çıkmaları 30 cm olacaktır")

# ── duvarlar ───────────────────────────────────────────────────────────────────────────────────────────────────────────
# Panel adları duvar paneli yerleşim paftasındaki gibi (D01–D26). Her kutu bir panel.
duvarlar = [
    # bina dış duvarları (karkas 140 mm)
    {"ad": "D01", "sinif": "dis", "kutu": [309.8, 14.2, 323.8, 134.2], "yukseklik": 270, "not": "mutfağın batı duvarı, güney parçası (verandaya bakar)"},
    {"ad": "D02", "sinif": "dis", "kutu": [309.8, 134.2, 323.8, 424.3], "yukseklik": 270, "not": "mutfağın batı duvarı, kuzey parçası (200/220 sürgülü)"},
    {"ad": "D03", "sinif": "dis", "kutu": [47.4, 410.3, 309.8, 424.3], "yukseklik": 270, "not": "salonun güney duvarı (verandaya bakar)"},
    {"ad": "D04", "sinif": "dis", "kutu": [47.4, 424.3, 61.4, 544.2], "yukseklik": 270, "not": "salonun batı duvarı, güney parçası"},
    {"ad": "D05", "sinif": "dis", "kutu": [47.4, 544.2, 61.4, 950.7], "yukseklik": 270, "not": "salonun batı duvarı, kuzey parçası (200/220 sürgülü)"},
    {"ad": "D06", "sinif": "dis", "kutu": [47.4, 950.7, 369.8, 964.7], "yukseklik": 270, "not": "kuzey duvarı, salon"},
    {"ad": "D07", "sinif": "dis", "kutu": [369.8, 950.7, 735.8, 964.7], "yukseklik": 270, "not": "kuzey duvarı, yatak odası"},
    {"ad": "D08", "sinif": "dis", "kutu": [735.8, 950.7, 1039.1, 964.7], "yukseklik": 270, "not": "kuzey duvarı, çocuk odası"},
    {"ad": "D09", "sinif": "dis", "kutu": [1025.1, 769.8, 1039.1, 950.7], "yukseklik": 270, "not": "doğu duvarı, kuzey parçası (çocuk odası)"},
    {"ad": "D10", "sinif": "dis", "kutu": [1025.1, 540.5, 1039.1, 769.8], "yukseklik": 270, "not": "doğu duvarı, güney parçası (çocuk odası)"},
    {"ad": "D11", "sinif": "dis", "kutu": [900.2, 540.5, 1025.1, 554.5], "yukseklik": 270, "not": "çocuk odasının güney duvarı, doğu parçası (sundurmaya bakar)"},
    {"ad": "D12", "sinif": "dis", "kutu": [900.2, 256.1, 914.2, 540.5], "yukseklik": 270, "not": "holün ve banyonun doğu duvarı (giriş kapısı; sundurmaya bakar)"},
    {"ad": "D13", "sinif": "dis", "kutu": [900.2, 14.2, 914.2, 256.1], "yukseklik": 270, "not": "banyonun doğu duvarı (50/50)"},
    {"ad": "D14", "sinif": "dis", "kutu": [611.1, 0.2, 914.2, 14.2], "yukseklik": 270, "not": "güney duvarı, doğu parçası (banyo ve mutfak)"},
    {"ad": "D15", "sinif": "dis", "kutu": [309.8, 0.2, 611.1, 14.2], "yukseklik": 270, "not": "güney duvarı, batı parçası (mutfak; 100/70)"},
    # iç duvarlar (karkas 80 mm)
    {"ad": "D16", "sinif": "ic", "kutu": [679.0, 14.2, 687.0, 194.85], "yukseklik": 270, "not": "mutfak ile banyo arası, güney parçası"},
    {"ad": "D17", "sinif": "ic", "kutu": [679.0, 194.85, 687.0, 421.3], "yukseklik": 270, "not": "mutfak ile banyo ve hol arası, kuzey parçası; kuzey ucunda K01 kirişinin yuvası"},
    {"ad": "D18", "sinif": "ic", "kutu": [687.0, 339.3, 900.2, 347.3], "yukseklik": 270, "not": "banyonun kuzey duvarı (banyo kapısı)"},
    {"ad": "D19", "sinif": "ic", "kutu": [443.8, 413.3, 679.0, 421.3], "yukseklik": 270, "not": "mutfağın kuzey duvarı, doğu parçası (mutfak kapısı)"},
    {"ad": "D20", "sinif": "ic", "kutu": [323.8, 413.3, 443.8, 421.3], "yukseklik": 270, "not": "mutfağın kuzey duvarı, batı parçası"},
    {"ad": "D21", "sinif": "ic", "kutu": [380.9, 421.3, 388.9, 724.35], "yukseklik": 270, "not": "salon ile hol ve yatak odası arası, güney parçası (salon kapısı)"},
    {"ad": "D22", "sinif": "ic", "kutu": [380.9, 724.35, 388.9, 950.7], "yukseklik": 270, "not": "salon ile yatak odası arası, kuzey parçası (iki yanında baca)"},
    {"ad": "D23", "sinif": "ic", "kutu": [388.9, 541.5, 679.0, 549.5], "yukseklik": 270, "not": "yatak odasının güney duvarı (yatak odası kapısı)"},
    {"ad": "D24", "sinif": "ic", "kutu": [679.0, 541.5, 900.2, 549.5], "yukseklik": 270, "not": "çocuk odasının güney duvarı, batı parçası (çocuk odası kapısı)"},
    {"ad": "D25", "sinif": "ic", "kutu": [707.0, 549.5, 715.0, 730.35], "yukseklik": 270, "not": "yatak odası ile çocuk odası arası, güney parçası"},
    {"ad": "D26", "sinif": "ic", "kutu": [707.0, 730.35, 715.0, 950.7], "yukseklik": 270, "not": "yatak odası ile çocuk odası arası, kuzey parçası"},
    # kolonlar (sırt 8, genişlik 30): verandada üç, sundurmada bir. Yükseklik kesit detayından (çatı panelinin altı)
    {"ad": "K02", "sinif": "kolon", "kutu": [0.0, 0.2, 8.0, 30.2], "yukseklik": 224.6, "kaplama_yuksekligi": 224.6, "not": "veranda, güneybatı köşesi"},
    {"ad": "K03", "sinif": "kolon", "kutu": [155.2, 0.2, 163.2, 30.2], "yukseklik": 238.3, "kaplama_yuksekligi": 238.3, "not": "veranda, güney orta (K05 kirişinin altı)"},
    {"ad": "K06", "sinif": "kolon", "kutu": [0.0, 380.3, 8.0, 410.3], "yukseklik": 224.6, "kaplama_yuksekligi": 224.6, "not": "veranda, kuzeybatı köşesi"},
    {"ad": "K07", "sinif": "kolon", "kutu": [1031.1, 378.4, 1039.1, 408.4], "yukseklik": 240, "kaplama_yuksekligi": 240, "not": "sundurma, güneydoğu köşesi"},
    # bacalar (açıklama 4: "Baca olacak. (Karkas ve içi de olacak.)"); 38 × 38, kuzey duvarının iç yüzünde, D22'nin iki yanında
    {"ad": "BACA1", "sinif": "baca", "kutu": [342.9, 912.7, 380.9, 950.7], "yukseklik": 270, "ust_kot": 381.4, "not": "salonun kuzeydoğu köşesi"},
    {"ad": "BACA2", "sinif": "baca", "kutu": [388.9, 912.7, 426.9, 950.7], "yukseklik": 270, "ust_kot": 381.4, "not": "yatak odasının kuzeybatı köşesi"},
]

mahaller = [
    {"ad": "Salon", "nokta": [220, 700], "sinif": "ic", "islev": ["salon"], "etiket_m2": 17.13},
    {"ad": "Yatak Odası", "nokta": [550, 750], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 12.84},
    {"ad": "Çocuk Odası", "nokta": [870, 750], "sinif": "ic", "islev": ["yatak_odasi"], "etiket_m2": 12.6},
    {"ad": "Hol", "nokta": [600, 480], "sinif": "ic", "islev": ["hol"], "etiket_m2": 7.73,
     "not": "L biçimli: salon kapısından giriş kapısına, güneyde banyo kapısının önüne; K01 kirişinin altından geçer"},
    {"ad": "Mutfak", "nokta": [500, 200], "sinif": "ic", "islev": ["mutfak"], "etiket_m2": 14.39},
    {"ad": "Banyo", "nokta": [800, 180], "sinif": "ic", "islev": ["banyo"], "islak": True, "etiket_m2": 7.08},
    {"ad": "Veranda", "poligon": [[0.0, 0.2], [309.8, 0.2], [309.8, 410.3], [0.0, 410.3]], "sinif": "veranda", "islev": ["veranda"], "etiket_m2": 14.84,
     "not": "kolonlu, korkuluksuz açık veranda; paftadaki 14,84 m² çatının saçağıyla (362 × 410)"},
    {"ad": "Sundurma", "poligon": [[914.2, 378.4], [1039.1, 378.4], [1039.1, 540.5], [914.2, 540.5]], "sinif": "veranda", "islev": ["veranda"], "etiket_m2": 2.0,
     "not": "giriş kapısının önündeki açık sundurma (açıklama 6); bir kolon, kendi tek eğimli çatısı"},
]


def pencere(ad, duvar, orta, en, yuk, alt, mahal, etiket=None):
    return {"ad": ad, "tur": "pencere", "duvar": duvar, "bas": r2(orta - en / 2), "en": en, "yuk": yuk, "alt": alt, "mahal": mahal,
            "etiket": etiket or f"{en}/{yuk}"}


# Açıklıklar: yer duvar paneli paftasındaki dikme ve başlıklardan (karkas boşluğunun ortası); ölçü müşteri onay paftasındaki etiketten.
# Pencereler Winsa, antrasit (pencere detayı: 150/130 üç, 200/220 sürgülü iki, 100/70 bir, 50/50 bir). Başlık altı 200 (sürgülüler 220).
acikliklar = [
    pencere("P1", "D06", 225.5, 150, 130, 70, "Salon"),
    pencere("P2", "D07", 554.0, 150, 130, 70, "Yatak Odası"),
    pencere("P3", "D08", 872.0, 150, 130, 70, "Çocuk Odası"),
    pencere("P4", "D05", 688.0, 200, 220, 0, "Salon"),
    pencere("P5", "D02", 272.0, 200, 220, 0, "Mutfak"),
    pencere("P6", "D15", 523.0, 100, 70, 130, "Mutfak"),
    pencere("P7", "D13", 130.0, 50, 50, 150, "Banyo"),
    {"ad": "K1", "tur": "dis_kapi", "duvar": "D12", "bas": 430.5, "en": 95, "yuk": 210, "mentese": "son", "acilim": "sol", "mahal": "Hol",
     "not": "giriş kapısı (sundurmadan hole); teknik özellikler: dış kapı çelik standart"},
    {"ad": "K2", "tur": "ic_kapi", "duvar": "D21", "bas": 432.0, "en": 90, "yuk": 214, "mentese": "bas", "acilim": "sol", "kanat": [80, 200], "mahal": "Salon"},
    {"ad": "K3", "tur": "ic_kapi", "duvar": "D23", "bas": 577.0, "en": 90, "yuk": 214, "mentese": "son", "acilim": "ust", "kanat": [80, 200], "mahal": "Yatak Odası"},
    {"ad": "K4", "tur": "ic_kapi", "duvar": "D24", "bas": 725.0, "en": 90, "yuk": 214, "mentese": "bas", "acilim": "ust", "kanat": [80, 200], "mahal": "Çocuk Odası"},
    {"ad": "K5", "tur": "ic_kapi", "duvar": "D19", "bas": 579.0, "en": 90, "yuk": 214, "mentese": "son", "acilim": "alt", "kanat": [80, 200], "mahal": "Mutfak"},
    {"ad": "K6", "tur": "ic_kapi", "duvar": "D18", "bas": 697.0, "en": 80, "yuk": 214, "mentese": "bas", "acilim": "alt", "kanat": [70, 200], "mahal": "Banyo",
     "not": "banyo kapısı: karkas boşluğu 80 (paftadan)"},
]

# Kirişler. Açık: duvarın içinde kalmayan kısım (planda, kirişin ekseni boyunca). Veranda kirişlerinin üstü çatı panelinin altında (kesit detayı);
# derinliği 30 alındı (paftada yazmıyor; KT-02'de 29,5).
kirisler = [
    {"ad": "K01", "kutu": [679.0, 401.3, 687.0, 549.2], "alt": 240, "ust": 270, "acik": [[421.3, 541.5]], "bolge": "Hol",
     "not": "holün iki kolu arasındaki açıklığın kirişi; 401,3–421,3 arası D17'nin, 541,5–549,2 arası D23 ile D24'ün üstünde"},
    {"ad": "K04", "kutu": [0.0, 30.2, 8.0, 380.3], "alt": 194.6, "ust": 224.6, "acik": [[30.2, 380.3]], "bolge": "veranda",
     "not": "veranda kirişi, batı (K02 ile K06 arası); üstü 224,6 (kesit)"},
    {"ad": "K05", "kutu": [155.2, 30.2, 163.2, 424.3], "alt": 208.3, "ust": 238.3, "acik": [[30.2, 410.3]], "bolge": "veranda",
     "not": "veranda kirişi, orta (K03'ten salonun güney duvarına); üstü 238,3 (kesit); 410,3–424,3 arası D03'ün içinde"},
]

# ── çatı ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Ana çatı: kırma (dört yüz aynı eğimde), güneyde bir kanat; saçak çizgileri karkasın dış yüzünden 30 cm. Yüzler saçak çizgilerinin düz iskeleti:
# kırma ve vadi çizgileri 45°.
W, N, E_, S1 = 47.4 - S, 964.7 + S, 1039.1 + S, 410.3 - S          # batı, kuzey, doğu saçağı; salonun güneyindeki saçak
WW, SW, WE, S2 = 309.8 - S, 0.2 - S, 914.2 + S, 540.5 - S         # kanadın batı, güney, doğu saçağı; çocuk odasının güneyindeki saçak
hw = (N - S1) / 2                     # batı kısmın yarı açıklığı: mahya y = S1 + hw
hk = (WE - WW) / 2                    # kanadın yarı açıklığı: mahya x = WW + hk
he = (N - S2) / 2                     # doğu kısmın yarı açıklığı: mahya y = S2 + he
MYB, MXK, MYD = S1 + hw, WW + hk, S2 + he
J1 = (MXK, N + WW - MXK)              # kanadın mahyasının kuzey ucu (kuzey yüz ile kanadın iki yüzünün buluştuğu nokta)
V1 = (WW + hw, MYB)                   # salonun güneyindeki vadinin üst ucu
V2 = (WE + S2 - MYD, MYD)             # çocuk odasının güneyindeki vadinin üst ucu
assert abs(V2[1] - (V2[0] + N - WE)) < 1e-6 and abs(J1[1] - (N - (J1[0] - WW))) < 1e-6
duzlemler = [
    {"ad": "kuzey", "plan": [[W, N], [E_, N], [E_ - he, MYD], list(V2), list(J1), list(V1), [W + hw, MYB]], "yukari": [0, -1], "sacak": {"y": N},
     "not": "ana çatının kuzey yüzü (bütün kuzey saçağı)"},
    {"ad": "batı", "plan": [[W, S1], [W + hw, MYB], [W, N]], "yukari": [1, 0], "sacak": {"x": W}, "not": "batı kırma ucu (salonun üstü)"},
    {"ad": "batı güney", "plan": [[W, S1], [WW, S1], list(V1), [W + hw, MYB]], "yukari": [0, 1], "sacak": {"y": S1},
     "not": "salonun güneyindeki yüz; doğuda kanatla vadi yapar"},
    {"ad": "kanat batı", "plan": [[WW, SW], [MXK, SW + hk], list(J1), list(V1), [WW, S1]], "yukari": [1, 0], "sacak": {"x": WW},
     "not": "güney kanadın batı yüzü (mutfağın ve verandanın doğu kenarının üstü)"},
    {"ad": "kanat güney", "plan": [[WW, SW], [WE, SW], [MXK, SW + hk]], "yukari": [0, 1], "sacak": {"y": SW}, "not": "güney kanadın kırma ucu"},
    {"ad": "kanat doğu", "plan": [[WE, SW], [WE, S2], list(V2), list(J1), [MXK, SW + hk]], "yukari": [-1, 0], "sacak": {"x": WE},
     "not": "güney kanadın doğu yüzü (banyonun ve sundurmanın üstü); kuzeyde doğu kısımla vadi yapar"},
    {"ad": "doğu güney", "plan": [[WE, S2], [E_, S2], [E_ - he, MYD], list(V2)], "yukari": [0, 1], "sacak": {"y": S2},
     "not": "çocuk odasının güneyindeki yüz"},
    {"ad": "doğu", "plan": [[E_, S2], [E_, N], [E_ - he, MYD]], "yukari": [-1, 0], "sacak": {"x": E_}, "not": "doğu kırma ucu (çocuk odasının üstü)"},
]
for d in duzlemler:
    d.update({"egim": E, "sacak_kotu": 280.0})
# Veranda ve sundurma çatıları (açıklama 7: "tek eğimli panel olacak"): çatı paneli, üstü sandviç panel. Eğim ve kotlar duvar paneli paftasındaki
# kesit detayından: veranda çatı panelinin altı dış kolonda 224,6, orta kolonda 238,32, bina duvarında 251,97 (eğim 27,37 / 309,8); saçak dış
# kolondan 51,92 (eğik). Sundurma: bina duvarında 260, kolonda 240, açıklık 117 (eğim 20 / 117); saçak kolonun dış yüzünden 30 (ana çatının doğu
# saçağıyla aynı çizgide). Panel adetleri makas ve dere paftasındaki yerleşimden (Ç13–Ç15 veranda, Ç16 sundurma).
EV = (251.97 - 224.6) / 309.8
XV = -51.92 / (1 + EV ** 2) ** 0.5
ES = (260.0 - 240.0) / 117.0
duzlemler += [
    {"ad": "veranda", "plan": [[XV, 0.2], [309.8, 0.2], [309.8, 410.3], [47.4, 410.3], [W, 410.3], [XV, 410.3]], "yukari": [1, 0], "egim": EV,
     "sacak_kotu": 224.6 + EV * XV, "sacak": {"x": XV}, "ust_yapi": "cati_paneli", "panel_kalinligi": 8.0, "cati_paneli_adedi": 3,
     "not": "veranda çatısı: tek eğimli çatı paneli, üstü sandviç panel; bina duvarına (D01, D02, D03) dayanır"},
    {"ad": "sundurma", "plan": [[914.2, 378.4], [E_, 378.4], [E_, 540.5], [1039.1, 540.5], [914.2, 540.5]], "yukari": [-1, 0], "egim": ES,
     "sacak_kotu": 240.0 - ES * (E_ - 1031.1), "sacak": {"x": E_}, "ust_yapi": "cati_paneli", "panel_kalinligi": 8.0, "cati_paneli_adedi": 1,
     "not": "sundurma çatısı: tek eğimli çatı paneli, üstü sandviç panel; bina duvarına (D12, D11) dayanır"},
]
for d in duzlemler:
    d["plan"] = [[r2(x), r2(y)] for x, y in d["plan"]]
    d["egim"], d["sacak_kotu"] = round(d["egim"], 5), r2(d["sacak_kotu"])
    d["sacak"] = {k: r2(v) for k, v in d["sacak"].items()}
# kenar türü koddan çıkmayanlar: bina duvarına dayanan kenarlar ve ana çatının saçağının altında kalan parçalar
kenar_ozel = [
    {"duzlem": "veranda", "p": [309.8, 0.2], "q": [309.8, 410.3], "tur": "duvar_dibi", "not": "mutfağın batı duvarı (D01, D02)"},
    {"duzlem": "veranda", "p": [309.8, 410.3], "q": [47.4, 410.3], "tur": "duvar_dibi", "not": "salonun güney duvarı (D03)"},
    {"duzlem": "veranda", "p": [47.4, 410.3], "q": [r2(W), 410.3], "tur": "gizli", "not": "ana çatının batı saçağının altında kalan 30 cm"},
    {"duzlem": "sundurma", "p": [914.2, 540.5], "q": [914.2, 378.4], "tur": "duvar_dibi", "not": "holün ve banyonun doğu duvarı (D12)"},
    {"duzlem": "sundurma", "p": [1039.1, 540.5], "q": [914.2, 540.5], "tur": "duvar_dibi", "not": "çocuk odasının güney duvarı (D11) ve D10'un ucu"},
    {"duzlem": "sundurma", "p": [r2(E_), 540.5], "q": [1039.1, 540.5], "tur": "gizli", "not": "ana çatının güney saçağının altında kalan 30 cm"},
]
# makaslar: makas ve dere yerleşim paftasından (MK01–MK36). Çizim ve IFC için üç grup yerleriyle (makasın üstü çatı düzlemlerinden; kırma
# uçlarında üstü kesik); öteki makaslar adetle.
makaslar = {
    "bati": {"eksen": "y", "y": [r2(S1), r2(N)], "x": [127.5, 207.0, 328.5, 453.5, 583.0], "kalinlik": 8, "adet": 5,
             "not": "batı kısmın kuzey–güney makasları (MK09, MK08, MK03, MK11, MK04)"},
    "dogu": {"eksen": "y", "y": [r2(S2), r2(N)], "x": [698.0, 823.0, 948.0], "kalinlik": 8, "adet": 3, "not": "doğu kısmın makasları (MK02, MK12, MK10)"},
    "kanat": {"eksen": "x", "x": [r2(WW), r2(WE)], "y": [85.0, 185.0, 306.0], "kalinlik": 8, "adet": 3, "not": "güney kanadın doğu–batı makasları (MK07, MK06, MK05)"},
    "diger": {"adet": 25, "not": "kırma uçlarının, köşelerin ve vadilerin makasları (MK01, MK13–MK36)"},
}

tanim = {
    "sema": "portman.yapi_tanimi/0.5-taslak",
    "kod": "KT-03",
    "ad": "Tek kat çelik, 2+1, verandalı ve sundurmalı, kırma çatı, 80 m² (üçüncü kör test projesi)",
    "aile": "tek_kat_celik",
    "paket": "proje",
    "birim": "cm",
    "kat": "zemin",
    "kaynak": {
        "cizim": ("Projenin montaj paftası (PDF, yedi sayfa: müşteri onay paftası, zemin kat duvar panelleri yerleşimi, makas ve dere yerleşimi, "
                  "tavan omegası yerleşimi, aşık yerleşimi, çatı, elektrik); 9 Ekim 2026'da okundu. Girdi: müşteri onay paftası (plan, teknik "
                  "özellikler, açıklama notları, pencere detayı), duvar paneli yerleşimi (yerler, ölçü zincirleri, veranda ve sundurma kesitleri), "
                  "makas ve dere yerleşimi (makasların ve çatı panellerinin yeri, çatının biçimi), elektrik yerleşimi (sayılar). Üretim dosyası yok."),
        "okunmayanlar": ("Klasördeki yükleme listesi (PDF ve Excel) bu tanım ve liste üretilip kaydedilene kadar açılmadı. Montaj paftalarındaki adetler "
                         "(çatı kaplaması, tavan omegası, aşık, dere inişi) girdi olarak kullanılmadı."),
        "koordinat": ("Köken verandanın batı dış çizgisi; binanın güney dış yüzü y = 0,2. +x doğu, +y kuzey (paftada kuzey işareti yok; çizimin üstü "
                      "kuzey alındı). Veranda batıda, salonun güneyinde; giriş doğuda, sundurmadan."),
    },
    "kat_yuksekligi": 270,
    "teknik_ozellikler": {
        "Bina yüksekliği": "2700 mm", "Dış duvarlar": "140 mm", "İç duvarlar": "80 mm", "Panel türü": "galvanizli yapısal çelik", "Çatı şekli": "kırma çatı",
        "Çatı kaplaması": "6 cm poliüretan sandviç panel", "Çatı kaplama rengi": "antrasit gri", "Dış kapı": "çelik standart", "İç kapılar": "alıcıya ait",
        "Dış cephe boya": "Polisan", "İç cephe boya": "Polisan", "Pencere rengi": "antrasit", "Tavan": "ters tavan", "Saçak ve alın rengi": "antrasit gri",
        "Pencere detayı": "Winsa (pafta: 'pencereler Winsa marka olacak')",
    },
    "aciklama_notlari": [
        "1- Dış cephe panelleri, dıştan içe: Boardex + çelik karkas + OSB + alçıpan",
        "2- İç cephe panelleri: alçıpan + OSB + çelik karkas + OSB + alçıpan",
        "3- Çatı izolasyon Knauf Earthwool",
        "4- Baca olacak. (Karkas ve içi de olacak.)",
        "5- İç kapılar, vitrifiye alıcıya aittir.",
        "6- Sundurma eklenecek.",
        "7- Veranda ve sundurma çatıları tek eğimli panel olacak.",
        "Duvar paneli paftası: 1- Duvar birleşimleri köşebent ile birleştirilecektir. 2- Dış duvarlarda çift kat izolasyon malzemesi kullanılacaktır.",
    ],
    "kapsam": {"dis_kapi": True, "pencere": True, "boya": True, "vitrifiye": False, "sihhi_tesisat": True, "elektrik": True, "ic_kapi": False,
               "kaynak": ("teknik özellikler (dış kapı çelik standart; dış ve iç cephe boyası Polisan; pencere rengi antrasit, Winsa; iç kapılar alıcıya ait) "
                          "ve açıklama 5 (iç kapılar, vitrifiye alıcıya ait). Tesisat için not yok: listede")},
    "renk": {"cati": "antrasit gri", "sacak_alin": "antrasit gri", "kaynak": "teknik özellikler"},
    "yuz_kaplamalari": {
        "dis": {"kalinlik": 3.0, "malzeme": ["boardex"],
                "not": "Plandaki dış ölçü karkastan 3'er cm büyük (991 → 997). Açıklama 1: Boardex + çelik karkas + OSB + alçıpan; nem bariyeri yazmıyor"},
        "ic": {"kalinlik": 2.35, "malzeme": ["osb", "alcipan"], "not": "OSB 11 mm + alçıpan 12,5 mm (açıklama 1 ve 2)"},
    },
    "duvar_siniflari": {
        "dis": {"ad": "bina dış duvarı", "profil": "140x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
        "ic": {"ad": "iç duvar", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}},
        "kolon": {"ad": "veranda ve sundurma kolonu", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}},
        "baca": {"ad": "baca", "profil": "80x45x0,8", "yalitim": False, "yuz": {"ic": "ic"},
                 "not": "et kalınlığı KT-01'in karkas modelinden ve gerçek listesinden (baca 80 × 45 × 0,8)"},
    },
    "duvarlar": duvarlar,
    "mahaller": mahaller,
    "acikliklar": acikliklar,
    "kirisler": kirisler,
    "lento": 70,
    "cati": {
        "tip": "kirma", "tip_kaynak": "teknik özellikler: çatı şekli 'Kırma Çatı'; güneyde kanat; veranda ve sundurmanın kendi tek eğimli çatıları",
        "yontem": "omega_asik", "yontem_kaynak": "montaj paftasında tavan omegası ve aşık yerleşim paftaları var (yöntem B)",
        "kaplama": "sandvic_panel", "kaplama_kaynak": "teknik özellikler: 6 cm poliüretan sandviç panel",
        "sacak": S, "topuk": 10, "duvar_ustu": 270,
        "duzlemler": duzlemler, "kenar_ozel": kenar_ozel, "makaslar": makaslar,
        "izolasyon": "Knauf Earthwool (açıklama 3)",
    },
}

if __name__ == "__main__":
    yol = Path(sys.argv[1])
    assert sum(v["adet"] for v in makaslar.values()) == 36
    yol.write_text(json.dumps(tanim, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", yol, "| duvar", len(duvarlar), "| mahal", len(mahaller), "| açıklık", len(acikliklar), "| kiriş", len(kirisler), "| düzlem", len(duzlemler))
    for d in duzlemler:
        print("  ", d["ad"], d["plan"], "eğim", d["egim"], "saçak kotu", d["sacak_kotu"])
