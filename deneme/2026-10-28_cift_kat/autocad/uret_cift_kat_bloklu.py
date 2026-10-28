#!/usr/bin/env python3
"""İE-22 · çift kat prefabrik, Şablon 2024 blok adlarıyla tek çizim (AutoCAD'de yeni pencere).

Girdi: Motor'un iki kat taslağı (sonuc/zemin_kat, sonuc/birinci_kat DXF; Astra v1.4.3 BOM_* blokları),
       Şablon 2024 blok kütüphanesi (sablon_inceleme/sablon_bloklari_yapi_v2.dxf; isteğe bağlı, kart için).
Çıktı: Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf + _malzeme_karti.md (aynı klasör).

Kurallar (Lokman, 28.10.2026): çift kat = tek kat kuralları + merdiven; pano dizilimi aynı; köşe direkleri 100×100 sürekli
(R02: 100×100×5320); ara kat R02'den 300 çelik kiriş bölgesi + 20 Betopan (Soru 6, teyit bekler); çatı tek kat gibi beşik %33,
saçak 30, topuk 10, makas kısa kenarı (y) geçer. Blok adları: Güncel Şablon 2024 kuralı
  <kalınlık mm>'LÜK <en cm>'LİK [(ENxBOY) PENCERELİ | (ENxBOY) VASİSTASLI | KAPILI PANO(<kapı cm>'LİK)] PANO
Şablonda bire bir bulunan ad aynen (125,5 → "125'LİK"; ondalık noktayla: 93.12, AutoCAD adda virgül kabul etmez); bulunmayan en/pencere için aynı kuralla yeni ad (kartta "yeni" işaretli).
Geometri Motor'un panolarından (Astra v1.4.3 sembolleri); yalnız ad değişir. Teslim yine Motor'un DXF'idir (K02, D-12); bu dosya
kuralı bulma ve Lokman'la düzeltme içindir.
"""
import re, sys, json, pathlib
from collections import Counter, OrderedDict
import ezdxf
from ezdxf.addons import Importer

KOK = pathlib.Path(__file__).resolve().parents[1]          # deneme/2026-10-28_cift_kat
CIKTI = pathlib.Path(__file__).resolve().parent             # …/autocad
# Kaynak (13:35'ten beri): ck_izgara/ — Motor gövdeyi 753 (= 763 − 10) ve iç duvarı 10 ile üretti (Lokman 13:30/13:32); aşağıda
# `cift_kat_izgara` sol dış duvarı yerinde bırakıp içleri +5, sağ dış duvarı +10 kaydırır → R02 kuralı: akslar köşe kolonunun iç
# yüzünden 10 + 125,5k (cephe = 10 kolon + n × 125,5 + özel + 10 kolon). Motor'da bu kural yok (İE-22 PR-1).
KATLAR = [("ZEMİN KAT", KOK / "ck_izgara/zemin_kat/Portman_IE22-CK01-ZEMIN_r01.dxf", 0.0),
          ("1. KAT",    KOK / "ck_izgara/birinci_kat/Portman_IE22-CK01-KAT1_r01.dxf", 1100.0)]
IC_KAL = "100'LÜK"   # Lokman 13:32: "güncel şablondaki gibi içler 100'lük olacak"
KUTUPHANE = CIKTI / "sablon_inceleme/sablon_bloklari_yapi_v2.dxf"
ANA = (-160, -120, 900, 960)   # Motor DXF'inde ana (akslı) planın bölgesi, cm

SABLONDA_VAR = {  # Şablon 2024'te bire bir bulunan adlar
    "100'LÜK 125'LİK PANO", "100'LÜK 125'LİK (60x40) VASİSTASLI PANO", "100'LÜK 125'LİK (120x100) PENCERELİ PANO",
    "100'LÜK 125'LİK KAPILI PANO(80'LİK)", "100'LÜK 117'LİK PANO", "60X60 3 LÜ H BAĞLANTI DİREĞİ", "100X100 DIŞ KÖŞE DİREĞİ",
    "100X100 3 LÜ H BAĞLANTI DİREĞİ", "2X100X100 İÇ KÖŞE DİREĞİ", "100X100 2 Lİ H DİREĞİ",
}

def pano_boyu(bom: str):
    m = re.search(r"_(\d+)p(\d)_", bom)
    return (int(m.group(1)) / 10 + int(m.group(2)) / 100) if m else None

def boy_kodu(cm: float) -> str:
    return f"{int(round(cm * 10))}p{int(round(cm * 100)) % 10}"

def uzat_blok(doc, ad: str, yeni_boy: float) -> str:
    """Motor'un pano bloğunu (yerel y boyunca dikdörtgenler) uzatır/kısaltır: son dikdörtgenin ucu yeni boya çekilir.
    Yeni blok adı boy koduyla (BOM_I13_1105p0_… → BOM_I13_1155p0_…). Var olan ada dokunmaz."""
    eski = pano_boyu(ad); yeni_ad = ad.replace(boy_kodu(eski), boy_kodu(yeni_boy))
    if yeni_ad in doc.blocks: return yeni_ad
    kb = doc.blocks.get(ad); nb = doc.blocks.new(yeni_ad)
    polys = [e for e in kb if e.dxftype() == "LWPOLYLINE"]
    son = max(polys, key=lambda e: max(y for x, y, *_ in e.get_points())) if polys else None
    for e in kb:
        c = e.copy(); nb.add_entity(c)
        if e is son:
            pts = [(x, (yeni_boy if abs(y - eski) < 1e-6 else y)) for x, y, *_ in e.get_points()]
            c.set_points(pts, format="xy")
    return yeni_ad

def kisalt_bas(doc, ad: str, kes: float) -> str:
    """Pano bloğunun BAŞINDAN (yerel y = 0 ucu) kes cm keser: geometri −kes kaydırılır, 0'ın altına düşen köşeler 0'a çekilir."""
    eski = pano_boyu(ad); yeni_boy = eski - kes
    m_ = re.match(r"BOM_([DI])(\d+)_", ad)                     # ad kalıbı bozulmasın: kod 9x (BOM_I16_ → BOM_I96_), boy kodu yeni
    yeni_ad = (f"BOM_{m_.group(1)}9{int(m_.group(2)) % 10}_" + ad[m_.end():]).replace(boy_kodu(eski), boy_kodu(yeni_boy))
    if yeni_ad in doc.blocks: return yeni_ad
    kb = doc.blocks.get(ad); nb = doc.blocks.new(yeni_ad)
    for e in kb:
        c = e.copy(); nb.add_entity(c)
        if c.dxftype() == "LWPOLYLINE":
            c.set_points([(x, max(0.0, y - kes)) for x, y, *_ in c.get_points()], format="xy")
        else:
            try: c.translate(0, -kes, 0)
            except Exception: pass
    return yeni_ad


def cift_kat_izgara(kaynak, secim):
    """Çift kat ızgarası (Lokman 13:30; Astra R02): Motor 753'lük gövdeyi tek kat kuralıyla (x aksları 5 + 125,5k) üretti.
    Sol dış duvar yerinde (0–10), içler +5 (akslar 10 + 125,5k), sağ dış duvar +10 (753–763). Yatay iç duvarın sol uçtaki
    120,5'lik ilk panosu 125,5 olur (aks artık kolon iç yüzünde), sağ dış duvara dayanan son iç pano +5 uzar (110,5 → 115,5).
    Dik panolar (rot 0) yerleşim x'ine, yatay panolar sol uç (rot 270) / sağ uç (rot 90) yerleşimine göre sınıflanır."""
    def zx(x):                     # nokta kuralı (aks, ölçü, yazı, çizgi)
        if x < 5 - 1e-6: return x                 # sol dış duvar gövdesi
        if x <= 10 + 1e-6: return 10.0            # dış duvar ekseni (5, tek kat aksı) ve iç yüz (10) → kolon iç yüzü 10
        if 313.75 - 1e-6 <= x <= 323.75 + 1e-6: return x          # kova sol duvarı: bant 313,75–323,75 yerinde (iç yüz aksta 323,75)
        if 564.75 - 1e-6 <= x <= 574.75 + 1e-6: return x + 10     # kova sağ duvarı: bant 574,75–584,75 (iç yüz aksta 574,75)
        if x < 743 - 1e-6: return x + 5           # içler
        if x < 748 - 1e-6: return x + 10          # sağ dış duvar iç yüzü 743 → 753
        if x <= 748 + 1e-6: return 753.0          # son aks / kolon yüzü 748 → 753
        return x + 10                             # dış yüz 753 → 763
    for e in secim:
        t = e.dxftype()
        if t == "INSERT":
            x, y = e.dxf.insert.x, e.dxf.insert.y; r = e.dxf.rotation % 360; ad = e.dxf.name
            L = pano_boyu(ad); yk = lambda v, t_: abs(v - t_) < 0.01
            if "UCLU_H" in ad or "IC_KOSE" in ad:                 # H ve iç köşe parçaları: kova duvar eksenleri 318,75 → 318,75; 569,75 → 579,75
                s = 0 if yk(x, 318.75) or yk(x, 313.75) else (10 if yk(x, 569.75) or yk(x, 564.75) else (5 if 5 <= x < 743 else (0 if x < 5 else 10)))
            elif abs(r) < 1e-6:                                    # dik bant
                if yk(x, 313.75): s = 0
                elif yk(x, 564.75): s = 10
                else: s = 0 if x < 5 - 1e-6 else (5 if x < 743 - 1e-6 else 10)
            elif abs(r - 90) < 1e-6:                               # yatay bant, sağ uçtan (başı x − L)
                if x >= 750: s = 10
                elif L and yk(x, 313.75): s = 0; e.dxf.name = uzat_blok(kaynak, ad, L - 5)
                elif L and yk(x, 564.75): s = 10; e.dxf.name = uzat_blok(kaynak, ad, L + 5)
                elif L and yk(x - L, 323.75): s = 5; e.dxf.name = uzat_blok(kaynak, ad, L + 5)
                elif L and yk(x - L, 574.75): s = 5; e.dxf.name = uzat_blok(kaynak, ad, L - 5)
                else: s = zx(x - 10) - (x - 10)
            else:                                                  # 270: yatay bant, sol uçtan
                if abs(x - 10) < 1e-6 and "_IC_" in ad and L and abs(L - 120.5) < 1e-6:
                    s = 0; e.dxf.name = uzat_blok(kaynak, ad, 125.5)
                elif L and yk(x, 323.75): s = 0; e.dxf.name = uzat_blok(kaynak, ad, L + 5)      # kova sol duvarının iç yüzünden başlar
                elif L and yk(x, 574.75): s = 10; e.dxf.name = uzat_blok(kaynak, ad, L - 5)     # kova sağ duvarının dış yüzünden başlar
                elif L and yk(x, 569.75): s = 15; e.dxf.name = kisalt_bas(kaynak, ad, 10)        # sağ duvar ekseninden başlayan kavşak panosu
                elif L and yk(x + L, 313.75): s = 5; e.dxf.name = uzat_blok(kaynak, ad, L - 5)  # kova sol duvarının dış yüzünde biter
                elif L and yk(x + L, 318.75): s = 5; e.dxf.name = uzat_blok(kaynak, ad, L - 10) # sol duvar ekseninde biter
                elif L and yk(x + L, 564.75): s = 5; e.dxf.name = uzat_blok(kaynak, ad, L + 5)  # kova sağ duvarının iç yüzünde biter
                else:
                    s = 0 if x < 5 - 1e-6 else 5
                    if L and "_IC_" in ad and abs(x + L - 743) < 1e-6:
                        e.dxf.name = uzat_blok(kaynak, ad, L + 5)
            e.dxf.insert = (x + s, y, 0)
        elif t == "LINE":
            a, b = e.dxf.start, e.dxf.end
            e.dxf.start = (zx(a.x), a.y, 0); e.dxf.end = (zx(b.x), b.y, 0)
        elif t == "LWPOLYLINE":
            e.set_points([(zx(x), y) for x, y, *_ in e.get_points()], format="xy")
        elif t in ("TEXT", "MTEXT"):
            p_ = e.dxf.insert; e.dxf.insert = (zx(p_.x), p_.y, 0)
            if t == "TEXT" and e.dxf.hasattr("align_point"):
                q = e.dxf.align_point; e.dxf.align_point = (zx(q.x), q.y, 0)
        elif t == "DIMENSION":
            for alan in ("defpoint", "defpoint2", "defpoint3", "text_midpoint"):
                if e.dxf.hasattr(alan):
                    q = e.dxf.get(alan); e.dxf.set(alan, (zx(q.x), q.y, 0))
        elif t in ("CIRCLE", "ARC"):
            c = e.dxf.center; e.dxf.center = (zx(c.x), c.y, 0)
        else:
            print("ızgara kaydırması: tür atlandı", t)

def en_yaz(cm: float) -> str:
    if abs(cm - 125.5) < 1e-6: return "125"          # şablonun yazımı
    return f"{cm:.2f}".rstrip("0").rstrip(".")   # AutoCAD blok adında virgül yasak; şablon da nokta kullanır (122.5)

def sablon_adi(bom: str):
    """BOM_D13_1255p0_DIS_P120x125 → ("100'LÜK 125'LİK (120x125) PENCERELİ PANO", "pano")."""
    m = re.match(r"BOM_([DI])\d+_(\d+)p(\d)_(DIS|IC)_(.+)$", bom)
    if m:
        en = int(m.group(2)) / 10 + int(m.group(3)) / 100 * 10 / 10  # 1255p0 → 125.5 ; 627p5 → 62.75
        en = int(m.group(2)) / 10 + int(m.group(3)) / 100
        kal = "100'LÜK" if m.group(4) == "DIS" else IC_KAL
        tur = m.group(5)
        if tur == "DOLU":
            return f"{kal} {en_yaz(en)}'LİK PANO", "pano"
        if tur == "P02":  return f"{kal} {en_yaz(en)}'LİK (120x180) PENCERELİ PANO", "pano"
        if tur == "P03":  return f"{kal} {en_yaz(en)}'LİK (60x40) VASİSTASLI PANO", "pano"
        pm = re.match(r"P(\d+)x(\d+)$", tur)
        if pm: return f"{kal} {en_yaz(en)}'LİK ({pm.group(1)}x{pm.group(2)}) PENCERELİ PANO", "pano"
        km = re.match(r"K01(?:_(SAG|SOL)_(UST|ALT))?$", tur)
        if km:
            ek = f" [{km.group(1)} {km.group(2).replace('UST','ÜST')}]" if km.group(1) else ""
            return f"{kal} {en_yaz(en)}'LİK KAPILI PANO(82'LİK){ek}", "pano"
        km = re.match(r"K02(?:_(SAG|SOL))?$", tur)
        if km:
            ek = f" [{km.group(1)}]" if km.group(1) else ""
            return f"{kal} {en_yaz(en)}'LİK KAPILI PANO(90'LIK){ek}", "pano"
        return f"{kal} {en_yaz(en)}'LİK {tur} PANO", "pano"
    if bom.startswith("BOM_B02_DIS_KOSE"):   return "100X100 SÜREKLİ DIŞ KÖŞE DİREĞİ (5320)", "profil"
    if bom.startswith("BOM_B02_IC_KOSE"):    return "2X100X100 İÇ KÖŞE DİREĞİ", "profil"
    if bom.startswith("BOM_B01_IC_KOSE"):    return ("2X100X100 İÇ KÖŞE DİREĞİ" if IC_KAL == "100'LÜK" else "60X30 İÇ KÖŞE BAĞLANTISI"), "profil"
    if bom.startswith("BOM_B03_UCLU_H_60"):  return "60X60 3 LÜ H BAĞLANTI DİREĞİ", "profil"
    if bom.startswith("BOM_B05_UCLU_H_100"): return "100X100 3 LÜ H BAĞLANTI DİREĞİ", "profil"
    if bom.startswith("BOM_B04_VERANDA_DIKME"): return "100X100 VERANDA DİKMESİ", "profil"
    vm = re.match(r"BOM_V\d+_VERANDA_(ON|YAN)_(\d+)p(\d)$", bom)
    if vm:
        return f"100'LÜK VERANDA PROFİLİ {en_yaz(int(vm.group(2))/10 + int(vm.group(3))/100)} ({'ÖN' if vm.group(1)=='ON' else 'YAN'})", "profil"
    return bom, "diger"

def kart_adi(ad: str) -> str:
    """Kanat yönü eki malzeme adına girmez."""
    return re.sub(r"\s*\[[^\]]*\]$", "", ad)

hedef = ezdxf.new("R2018"); hedef.header["$INSUNITS"] = 5; hedef.header["$LTSCALE"] = 1.0
H = hedef.modelspace()
for ad, renk in [("CIFT_KAT_NOT", 1), ("CIFT_KAT_CERCEVE", 8), ("KESIT", 7), ("KESIT_KIRIS", 30), ("KESIT_BETOPAN", 3),
                 ("KESIT_CATI", 1), ("KOSE_SUREKLI_100", 6), ("MALZEME_KARTI", 7), ("SABLON_KARTI", 9),
                 ("MERDIVEN", 4), ("MERDIVEN_DUVAR", 7)]:
    hedef.layers.add(ad, color=renk)
if "DASHED" not in hedef.linetypes:
    hedef.linetypes.add("DASHED", pattern=[20.0, 12.5, -7.5])
kut = ezdxf.readfile(str(KUTUPHANE)) if KUTUPHANE.exists() else None
ESKI_KOSE, SABLON_KOSE = "100X100 SÜREKLİ DIŞ KÖŞE DİREĞİ (5320)", "100X100 DIŞ KÖŞE DİREĞİ"
if kut is not None and SABLON_KOSE in kut.blocks:          # şablonun köşe direği bloğu baştan hedefte (çıkma köşeleri de kullanır)
    _i = Importer(kut, hedef); _i.import_block(SABLON_KOSE); _i.finalize()
    hedef.blocks.get(SABLON_KOSE).base_point = (0, 0, 0)
for _ad, _renk in [("DIS_DUVAR_100", 7), ("IC_DUVAR_100", 7), ("KOSE_PROFIL_100", 1)]:
    if _ad not in hedef.layers: hedef.layers.add(_ad, color=_renk)


def pano_blogu(ad: str, boy: float, kal: float = 10.0) -> str:
    """Şablon adlı dolu pano bloğu yoksa kurar (Motor'un bloğu gibi: yerel y boyunca boy, x'te kalınlık)."""
    if ad not in hedef.blocks:
        b = hedef.blocks.new(ad); b.add_lwpolyline([(0, 0), (kal, 0), (kal, boy), (0, boy)], close=True)
        if ad not in SABLONDA_VAR: yeni_adlar.add(kart_adi(ad))
    return ad


def merdiven_ciz(dx: float, kat1: bool, eklenen: list, kat_adi: str):
    """Merdiven kovası pano aksında (Lokman 13:30 "merdiven kovası ile oda duvarlarını da şaşırmışsın"): kova = Motor'un
    MERDİVEN mahali, 2 pano (akslar 323,75 / 574,75 → 10'luk duvarlarla iç 241), gövdede derinlik 570,5–696 (önü HOL'e açık,
    `acik_sinirlar`); arkaya çıkma 1 pano (dış 706–831,5; duvarlar akslara ortalı). Merdiven planın aynısı (13:00): çift kollu U,
    kol 120,5; sağ kol 5 düz basamak (25: 570,5 → 695,5), çıkmada 6 dönel (180°, merkez gövde dış yüz hizası 706, kova ortası
    449,25), sol kol 5 düz → 16 rıht; başlangıç dairesi sağ kolda önde, varış oku sol kolda önde. 1. katta çıkmanın arka duvarında
    120/125 pencereli pano (plan). Çıkma panoları şablon adlı bloklar; gövde arka duvarının kova açıklığına düşen panoları kalkar,
    yanlar 57,75'lik kesik panoyla kapanır (ek yerinde H simgesi yok — not). Kat kartına sayılır."""
    L, D = "MERDIVEN", "MERDIVEN_DUVAR"
    XA, XB = dx + 323.75, dx + 574.75            # kova aksları = kova duvarlarının İÇ yüzleri (Lokman 14:42: dıştan dışa 271 = 10 + 2 × 125,5 + 10)
    XI0, XI1 = XA, XB                            # kova iç 251 (tam 2 pano); duvar bantları XA−10..XA ve XB..XB+10
    YON, YARKA = 570.5, 696.0                    # kovanın önü (HOL'e açık sınır) ve gövde arka iç yüzü
    YC0, YC1 = 706.0, 841.5                      # çıkma: yan pano net 125,5 (706–831,5) + arka köşe profili 10 → dış 841,5 (Lokman 14:48)
    # --- gövde arka duvarı: kova açıklığına düşen panolar kalkar, yanlar kesik pano
    sil = []
    for e in eklenen:
        if e.is_alive and e.dxftype() == "INSERT" and abs(e.dxf.rotation % 360 - 270) < 1e-6 and abs(e.dxf.insert.y - YC0) < 1e-6:
            x = e.dxf.insert.x; Lp = pano_boyu_ad(e.dxf.name)
            if Lp and x < XB + 5 - 1e-6 and x + Lp > XA - 5 + 1e-6: sil.append(e)
    for e in sil:
        say(kart_adi(e.dxf.name), kat_adi, -1); H.delete_entity(e)
    kesik = pano_blogu("100'LÜK 52.75'LİK PANO", 52.75)          # arka duvar yan parçaları: 261→313,75 ve 584,75→637,5
    for x in (dx + 261.0, XB + 10):
        H.add_blockref(kesik, (x, YC0), dxfattribs={"rotation": 270, "layer": "DIS_DUVAR_100"}); say(kesik, kat_adi, 1)
    # --- çıkma duvarları (dış pano, 10): yanlar 115,5 dik, arka 125,5 + 115,5 yatay; 1. katta arka solda 120/125 pencereli
    yan = pano_blogu("100'LÜK 125'LİK PANO", 125.5)              # yan duvar: köşe direkleri hariç net 125,5 (Lokman 14:48)
    for x in (XA - 10, XB):                                        # yan duvar bantları XA−10..XA ve XB..XB+10 (dış 271)
        H.add_blockref(yan, (x, YC0), dxfattribs={"layer": "DIS_DUVAR_100"}); say(yan, kat_adi, 1)
    arka1 = "100'LÜK 125'LİK (120x125) PENCERELİ PANO" if kat1 else "100'LÜK 125'LİK PANO"
    if arka1 not in hedef.blocks: arka1 = pano_blogu("100'LÜK 125'LİK PANO", 125.5)
    arka2 = pano_blogu("100'LÜK 125'LİK PANO", 125.5)              # çıkma arka duvarı: tam 2 pano (251 iç)
    H.add_blockref(arka1, (XA, YC1), dxfattribs={"rotation": 270, "layer": "DIS_DUVAR_100"}); say(arka1, kat_adi, 1)
    H.add_blockref(arka2, (XA + 125.5, YC1), dxfattribs={"rotation": 270, "layer": "DIS_DUVAR_100"}); say(arka2, kat_adi, 1)
    # --- çıkma köşe direkleri (şablon bloğu; iki kat boyu sürekli varsayımı, Soru 5/8)
    if SABLON_KOSE in hedef.blocks:
        H.add_blockref(SABLON_KOSE, (XA - 10, YC1 - 12.5), dxfattribs={"layer": "KOSE_PROFIL_100"})                      # arka-sol: aşağı, sağa
        H.add_blockref(SABLON_KOSE, (XB + 10, YC1 - 12.5), dxfattribs={"xscale": -1, "layer": "KOSE_PROFIL_100"})        # arka-sağ: aşağı, sola
        # Lokman 13:57 (planda kırmızı kareler, "Profil"): çıkma yan duvarlarının gövde arka duvarıyla birleştiği iki noktaya 100×100 profil
        H.add_blockref(SABLON_KOSE, (XA, YC0 + 2.5), dxfattribs={"xscale": -1, "yscale": -1, "layer": "KOSE_PROFIL_100"})       # sol birleşim (XA−10..XA): yukarı, sola
        H.add_blockref(SABLON_KOSE, (XA - 10, YC0 + 2.5), dxfattribs={"yscale": -1, "layer": "KOSE_PROFIL_100"})                 # sol birleşim: yukarı, sağa
        H.add_blockref(SABLON_KOSE, (XB, YC0 + 2.5), dxfattribs={"yscale": -1, "layer": "KOSE_PROFIL_100"})                      # sağ birleşim (XB..XB+10): yukarı, sağa
        H.add_blockref(SABLON_KOSE, (XB + 10, YC0 + 2.5), dxfattribs={"xscale": -1, "yscale": -1, "layer": "KOSE_PROFIL_100"})  # sağ birleşim: yukarı, sola
    # --- merdiven çizgileri
    def cz(x0, y0, x1, y1): H.add_line((x0, y0), (x1, y1), dxfattribs={"layer": L})
    XM = (XI0 + XI1) / 2                          # kol ayırıcı (449,25 + dx)
    cz(XM, YON, XM, YC1 - 10)
    for i in range(1, 6): cz(XI0, YON + 25 * i, XI1, YON + 25 * i)        # 5 düz basamak (695,5 ≈ arka iç yüz)
    cz(XI0, YC0, XI1, YC0)                                                  # dönel basamakların başlangıcı (gövde dış yüz hizası)
    yarka = YC1 - 10
    for x, y in ((XI0, YC0 + 60), (XI0 + 40, yarka), (XM, yarka), (XI1 - 40, yarka), (XI1, YC0 + 60)):
        cz(XM, YC0, x, y)                                                   # 6 dönel basamak
    XR, XL = (XM + XI1) / 2, (XI0 + XM) / 2
    H.add_circle((XR, YON + 15), 12, dxfattribs={"layer": L})
    ytop = YON + 0.8 * (yarka - YON)
    cz(XR, YON + 27, XR, ytop); cz(XR, ytop, XL, ytop); cz(XL, ytop, XL, YON + 30)
    H.add_lwpolyline([(XL - 15, YON + 30), (XL + 15, YON + 30), (XL, YON), (XL - 15, YON + 30)], dxfattribs={"layer": L})
    H.add_text(f"MERDİVEN KOVASI dıştan dışa 271 = 10 profil + 2 × 125,5 + 10 profil (Lokman 14:42); iç {XI1 - XI0:.1f}; çıkma geriye net 125,5 pano + 10 profil (14:48) → dış 271 × 135,5 · çift kollu U, kol {(XI1 - XI0) / 2:.2f}, "
               "5 + 6 dönel + 5 = 16 rıht (282/16 = 17,6), basamak 25 — düzen Lokman'ın planından (13:00), ölçüler pano aksından (13:30)",
               height=4.5, dxfattribs={"layer": L}).set_placement((XA - 10, YC1 + 20))
    H.add_text("Çıkma duvarları akslara ortalı 10'luk dış pano; arka duvar ek yerlerinde (261→318,75 ve 579,75→637,5 kesik panolar) H simgesi yok · "
               "zeminde kovaya giriş: önü açık (Motor `acik_sinirlar`; planda ön duvar çizili → Soru 2b)",
               height=4.5, dxfattribs={"layer": L}).set_placement((XA - 10, YC1 + 12))


def balkon_kirisi(dx: float, eklenen: list, kat_adi: str, tasma: float = 40.0):
    """Lokman 14:43/14:50: balkonun KİRİŞ çizgileri (Motor'un veranda profilleri) 40 cm dışarı — ayrı çizgi değil, kirişin kendisi.
    Ön kiriş y = −40..−30 (454,25 → 763), yan kiriş x = 753..763 (−40 → 126,25), köşe dikmesi (753, −40). Motor'un veranda bloklarının
    yerine aynı adlandırmayla yeni boyda bloklar (ön 308,75 — gövde sağ yüzüne kadar; yan 166,25)."""
    sil = [e for e in eklenen if e.is_alive and e.dxftype() == "INSERT" and ("VERANDA PROFİLİ" in e.dxf.name or "VERANDA DİKMESİ" in e.dxf.name)]
    for e in sil:
        say(kart_adi(e.dxf.name), kat_adi, -1); H.delete_entity(e)
    on_ad, yan_ad, dikme = f"100'LÜK VERANDA PROFİLİ {en_yaz(308.75)} (ÖN)", f"100'LÜK VERANDA PROFİLİ {en_yaz(126.25 + tasma)} (YAN)", "100X100 VERANDA DİKMESİ"
    if on_ad not in hedef.blocks:
        b = hedef.blocks.new(on_ad); b.add_lwpolyline([(0, 0), (308.75, 0), (308.75, 10), (0, 10)], close=True); yeni_adlar.add(on_ad)
    if yan_ad not in hedef.blocks:
        b = hedef.blocks.new(yan_ad); b.add_lwpolyline([(0, 0), (10, 0), (10, 126.25 + tasma), (0, 126.25 + tasma)], close=True); yeni_adlar.add(yan_ad)
    if dikme not in hedef.blocks:
        b = hedef.blocks.new(dikme); b.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True)
    H.add_blockref(on_ad, (dx + 454.25, -tasma), dxfattribs={"layer": "VERANDA_PROFIL_100"}); say(on_ad, kat_adi, 1)
    H.add_blockref(yan_ad, (dx + 753.0, -tasma), dxfattribs={"layer": "VERANDA_PROFIL_100"}); say(yan_ad, kat_adi, 1)
    H.add_blockref(dikme, (dx + 753.0, -tasma), dxfattribs={"layer": "VERANDA_DIKME"}); say(dikme, kat_adi, 1)


def kapiyi_yasla(insert_xy, rot, pay: float = 11.5, kat_adi: str = ""):
    """Lokman 14:58 "mutfak kapısını da sola yasla": Motor 'dayanak yok' deyip kapıyı panoda ortada bıraktı (İE-22 bulgu 9).
    Verilen yerleşimdeki kapılı pano bloğunun açıklığı yerel 0 ucuna (rot 270'te sol uç) `pay` cm kala kaydırılır: jamb'lar
    [0, pay] ve [pay + kapı, boy]; iç kapı sembolü aynı miktarda kayar. Yeni blok adı "… [SOLA YASLI]"."""
    for e in list(H.query("INSERT")):
        if abs(e.dxf.insert.x - insert_xy[0]) > 0.01 or abs(e.dxf.insert.y - insert_xy[1]) > 0.01 or abs(e.dxf.rotation % 360 - rot) > 0.01: continue
        ad = e.dxf.name
        if "KAPILI PANO" not in ad: continue
        boy = pano_boyu_ad(ad); kb = hedef.blocks.get(ad)
        polys = [k for k in kb if k.dxftype() == "LWPOLYLINE"]
        if len(polys) != 2 or boy is None: print("yaslama: beklenmeyen blok", ad); return
        ilk = min(polys, key=lambda k: max(y for _, y, *__ in k.get_points()))
        eski_pay = max(y for _, y, *__ in ilk.get_points()); delta = pay - eski_pay
        yeni_ad = (ad[:-1] + " · SOLA YASLI]") if ad.endswith("]") else ad + " [SOLA YASLI]"    # kanat yönü ekiyle birlikte (SAG ALT ≠ SOL ÜST)
        if yeni_ad not in hedef.blocks:
            nb = hedef.blocks.new(yeni_ad)
            for k in kb:
                c = k.copy(); nb.add_entity(c)
                if c.dxftype() == "LWPOLYLINE":
                    c.set_points([(x, y + delta if y > 0.01 and y < boy - 0.01 else y) for x, y, *_ in c.get_points()], format="xy")
                else:
                    try: c.translate(0, delta, 0)
                    except Exception: pass
            yeni_adlar.add(kart_adi(yeni_ad))
        say(kart_adi(ad), kat_adi, -1); e.dxf.name = yeni_ad; say(kart_adi(yeni_ad), kat_adi, 1)
        print("kapı sola yaslandı:", ad, "→", yeni_ad, "delta", round(delta, 2)); return
    print("yaslama: kapı bulunamadı", insert_xy)


def mutfak_ust_duvari(dx: float, kat_adi: str):
    """Lokman 14:56 + 14:58: mutfak kapısı balkon kapısıyla aynı hizada VE sola (salon/mutfak duvarına) yaslı → kapılı pano
    512–637,5 (hol tarafı; HOL–WC HOLÜ açık olduğundan tek hol), açıklık 11,5 payla; kalan 637,5–753 dolu 115,5.
    Motor bunu yapamıyor: HOL–MUTFAK ortak duvar parçası 57,75 (kapı sığmıyor), WC HOLÜ–MUTFAK parçası 584,75'ten başlıyor (bulgu 9)."""
    y = 387.25
    for e in list(H.query("INSERT")):
        if abs(e.dxf.insert.y - y) < 0.01 and abs(e.dxf.rotation % 360 - 270) < 0.01 and dx + 512 - 0.01 <= e.dxf.insert.x <= dx + 753 and pano_boyu_ad(e.dxf.name):
            say(kart_adi(e.dxf.name), kat_adi, -1); H.delete_entity(e)
    for e in list(H.query("DIMENSION")):                     # Motor'un bu duvara ait özel pano ölçüleri (eski diziliş) kalkar
        q = e.dxf.defpoint
        if 370 <= q.y <= 400 and dx + 505 <= q.x <= dx + 760 and e.dxf.layer == "OZEL_PANEL_OLCU_CM": H.delete_entity(e)
    kapi_kaynak = "100'LÜK 125'LİK KAPILI PANO(82'LİK) [SAG ALT]"      # mutfağa (−y) açılır, menteşe batı ucunda
    if kapi_kaynak not in hedef.blocks: print("mutfak üst duvarı: kapı bloğu yok", kapi_kaynak); return
    H.add_blockref(kapi_kaynak, (dx + 512.0, y), dxfattribs={"rotation": 270, "layer": "IC_DUVAR_100"}); say(kart_adi(kapi_kaynak), kat_adi, 1)
    kapiyi_yasla((dx + 512.0, y), 270, 11.5, kat_adi)
    dolu = pano_blogu("100'LÜK 115.5'LİK PANO", 115.5)
    H.add_blockref(dolu, (dx + 637.5, y), dxfattribs={"rotation": 270, "layer": "IC_DUVAR_100"}); say(dolu, kat_adi, 1)


def pano_boyu_ad(ad: str):
    """Şablon adından pano boyu: 100'LÜK 115.5'LİK PANO → 115.5; 125'LİK → 125.5."""
    m = re.match(r"(?:100'LÜK|60'LIK) ([\d.]+)'LİK", ad)
    if not m: return None
    v = float(m.group(1)); return 125.5 if abs(v - 125) < 1e-6 else v


def say(ad: str, kat_adi: str, n: int = 1):
    sayim.setdefault(ad, Counter())[kat_adi] += n
    if sayim[ad][kat_adi] <= 0: del sayim[ad][kat_adi]


def sablon_kapili_pano(hedef_blok: str, kapi: float = 90.0, en: float = 125.5, mentese: str = "SAG"):
    """Güncel Şablon 2024'ün '100'LÜK 125'LİK KAPILI PANO(80'LİK)' çizimini (10'luk pano bandı, H profilli kasa, kanat, yay)
    kapı genişliğine ve pano enine uyarlayıp hedef bloğun içeriği yapar (Lokman 13:02: "dış kapıda güncel şablon 2024'te var").
    Kapı genişlemesi: açıklık kenarları ±(kapi−80)/2, kanat ve yay +(kapi−80); pano kısalması uçlardan (t = (125,5 − en)/2); SOL: ayna."""
    KAYNAK = "100'LÜK 125'LİK KAPILI PANO(80'LİK)"
    if kut is None or KAYNAK not in kut.blocks or hedef_blok not in hedef.blocks:
        print("şablon kapılı pano uygulanamadı:", hedef_blok); return False
    tmp = ezdxf.new("R2018"); i1 = Importer(kut, tmp); i1.import_block(KAYNAK); i1.finalize()
    hb = hedef.blocks.get(hedef_blok)
    for e in list(hb): hb.delete_entity(e)
    i2 = Importer(tmp, hedef); i2.import_entities(list(tmp.blocks.get(KAYNAK)), hb); i2.finalize()
    hb.base_point = (0, 0, 0)
    d, t, uz = (kapi - 80) / 2, (125.5 - en) / 2, kapi - 80
    def xk(x):
        if x < 62.75: return (x - d if x > 0.01 else t) - t
        return (x + d if x < 125.49 else 125.5 - t) - t
    def ay(x): return en - x if mentese == "SOL" else x
    for e in hb:
        tt = e.dxftype()
        if tt == "LINE":
            s, b = e.dxf.start, e.dxf.end; ys, yb = s.y - 1, b.y - 1
            if e.dxf.layer == "KAPI-PLAN":
                if ys > 50: ys += uz
                if yb > 50: yb += uz
            e.dxf.start = (ay(xk(s.x)), ys, 0); e.dxf.end = (ay(xk(b.x)), yb, 0)
        elif tt == "ARC":
            c = e.dxf.center; e.dxf.center = (ay(xk(c.x)), c.y - 1, 0)
            if e.dxf.radius > 30: e.dxf.radius += uz
            if mentese == "SOL":
                sa, ea = e.dxf.start_angle, e.dxf.end_angle
                e.dxf.start_angle, e.dxf.end_angle = 180 - ea, 180 - sa
        elif tt == "CIRCLE":
            c = e.dxf.center; e.dxf.center = (ay(xk(c.x)), c.y - 1, 0)
        elif tt == "LWPOLYLINE":
            e.set_points([(ay(xk(x)), y - 1) for x, y, *_ in e.get_points()], format="xy")
    return True

sayim = OrderedDict()   # kart adı → {kat: adet}
yeni_adlar = set(); aciklamalar = []

for kat_adi, yol, dx in KATLAR:
    kaynak = ezdxf.readfile(str(yol))
    msp = kaynak.modelspace()
    # 0) ana plan bölgesindeki varlıkları seç ve çift kat ızgarasına kaydır (BOM adlarıyla; ad değişiminden önce)
    x0, y0, x1, y1 = ANA
    secim = []
    for e in msp:
        p = None
        for alan in ("insert", "start", "defpoint", "center"):
            if e.dxf.hasattr(alan): p = e.dxf.get(alan); break
        if p is None and e.dxftype() == "LWPOLYLINE":
            pts = list(e.get_points()); p = pts[0] if pts else None
        if p is None: continue
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1: secim.append(e)
    cift_kat_izgara(kaynak, secim)      # 5 cm aks kayması (Lokman 13:30; R02)
    # 1) kaynaktaki blokları Şablon 2024 adıyla yeniden adlandır
    esleme = {}; silinecek = []
    for b in list(kaynak.blocks):
        if not b.name.startswith("BOM_"): continue
        yeni, tur = sablon_adi(b.name)
        if yeni == b.name:          # ad değişmiyorsa (kapı/pencere sembolleri) dokunma
            continue
        esleme[b.name] = yeni
        if yeni not in SABLONDA_VAR and tur == "pano": yeni_adlar.add(kart_adi(yeni))
        if yeni in kaynak.blocks:      # aynı ada iki blok: iç/dış dolu pano aynı dikdörtgen → birleştir; değilse ek tak
            from ezdxf import bbox as _bb
            b1, b2 = _bb.extents(kaynak.blocks.get(yeni), fast=True), _bb.extents(b, fast=True)
            if (b1.size - b2.size).magnitude < 1e-6 and len(kaynak.blocks.get(yeni)) == len(b):
                esleme[b.name] = yeni; silinecek.append(b.name); continue
            yeni = yeni + f" {{{b.name[4:7]}}}"; esleme[b.name] = yeni
        kaynak.blocks.rename_block(b.name, yeni)
    for e in msp.query("INSERT"):
        if e.dxf.name in esleme: e.dxf.name = esleme[e.dxf.name]
    for b in kaynak.blocks:            # iç içe INSERT'ler (MNT_* kopyaları vs.)
        for e in b.query("INSERT"):
            if e.dxf.name in esleme: e.dxf.name = esleme[e.dxf.name]
    for ad_ in silinecek:
        try: kaynak.blocks.delete_block(ad_, safe=True)
        except Exception as ex: print("birleştirilen blok silinemedi", ad_, str(ex)[:60])
    # ölçü stili: Importer DIMSTYLE taşımıyor, elle kopyala (ölçüler sonra yeniden render edilir)
    for sd in kaynak.dimstyles:
        if sd.dxf.name not in hedef.dimstyles:
            td = hedef.dimstyles.new(sd.dxf.name)
            from ezdxf.render.arrows import ARROWS
            for k, v in sd.dxfattribs().items():
                if k in ("handle", "owner", "name") or k.endswith("_handle"): continue
                if k in ("dimblk", "dimblk1", "dimblk2", "dimldrblk") and v:
                    try: ARROWS.create_block(hedef.blocks, v)
                    except Exception: pass
                if k == "dimrnd": continue      # Motor'da 0.0 yazılı; ezdxf 0'ı "tam sayıya yuvarla" sayıyor (125,5 → 126)
                try: td.dxf.set(k, v)
                except Exception as ex: print("dimstyle alanı atlandı", k, v, str(ex)[:60])
            td.dxf.discard("dimrnd")
            td.dxf.dimdec, td.dxf.dimzin, td.dxf.dimdsep = 2, 0, 44   # Lokman 13:15: virgülden sonra iki basamak (125,50), ayraç virgül
    for st in kaynak.styles:
        if st.dxf.name not in hedef.styles:
            try: hedef.styles.new(st.dxf.name, dxfattribs={"font": st.dxf.font})
            except Exception: pass
    imp = Importer(kaynak, hedef)
    imp.import_entities(secim, H)
    imp.finalize()
    # az önce eklenenleri kaydır (kaynak ile aynı sırada eklenir); ölçüleri yeniden render et
    eklenen = list(H)[-len(secim):]
    for e in eklenen:
        if e.dxftype() == "TEXT" and "753 × 706" in e.dxf.text:
            e.dxf.text = e.dxf.text.replace("753 × 706", "763 × 706 (10 + 5 × 125,5 + 115,5 + 10)")
        try: e.translate(dx, 0, 0)
        except Exception as ex: print("kaydırılamadı", e.dxftype(), ex)
        if e.dxftype() == "DIMENSION":
            try: e.render()
            except Exception as ex: print("ölçü render edilemedi", ex)
    # 2b) aynı adlı bloğun "…0" kopyasını (Importer çakışma adı) asıl bloğa birleştir — aynı malzeme, aynı geometri
    kopyalar = [b.name for b in hedef.blocks if b.name.endswith("0") and b.name[:-1] in hedef.blocks and not b.name.startswith("*")]
    for k in kopyalar:
        asil = k[:-1]
        for e in H.query("INSERT"):
            if e.dxf.name == k: e.dxf.name = asil
        for b in hedef.blocks:
            for e in b.query("INSERT"):
                if e.dxf.name == k: e.dxf.name = asil
        hedef.blocks.delete_block(k, safe=False)
    # 3) sayım (yalnız ana plandaki INSERT'ler)
    for e in eklenen:
        if e.dxftype() == "INSERT":
            k = kart_adi(e.dxf.name)
            sayim.setdefault(k, Counter())[kat_adi] += 1
    # 4) kat başlığı ve çerçeve
    H.add_text(f"{kat_adi} · 763 × 706 · Şablon 2024 blok adlarıyla · İE-22 (28.10.2026)", height=12,
               dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((dx, 945))
    # merdiven kutusu + merdiven, Lokman'ın planı bire bir (13:00); balkon taşması (Motor'da yok) kesik çizgi — y önden
    merdiven_ciz(dx, kat1=(dx > 0), eklenen=eklenen, kat_adi=kat_adi)
    balkon_kirisi(dx, eklenen, kat_adi)
    H.add_text("BALKON KİRİŞLERİ 40 DIŞARIDA (Lokman 14:43/14:50; Motor'un veranda profilleri taşındı; Motor'da kural yok)", height=6, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((dx+456, -64))


# 4b) Giriş kapısı (Lokman 28.10 12:34, Soru 1): sağ cephe, WC HOLÜ, 90'lık, içeri açılır. Motor bunu kendisi çiziyor:
#     BOM_D18_1255p0_DIS_K02 @ (763, 445) rot 90, iç sembol BOM_K03_DIS_KAPI_ACIKLIK900 (sınır kutusu 668,8–764,1 × 445–570,5).
#     12:45'te "Motor sembolü çizmedi (bulgu 7)" diye elle kırmızı kapı çizilmişti; yanlıştı — ad değiştirme iç sembolü bozduğu için
#     görünmüyordu (A023'te düzeltildi). Elle kapı 13:05'te kaldırıldı.
# 4c) Dış kapı çizimi Güncel Şablon 2024'ten (Lokman 13:02 "dış kapıda güncel şablon 2024'te var"): dış kapılı pano bloklarının
#     içeriği Motor'un Astra sembolü yerine şablonun kapılı pano çizimi (90'a ve pano enine uyarlanmış). Adlar aynı kalır.
for blok in [b_.name for b_ in hedef.blocks if "KAPILI PANO(90'LIK)" in b_.name and b_.name.startswith("100'LÜK")]:
    en_ = pano_boyu_ad(blok); mentese = "SOL" if "[SOL]" in blok else "SAG"
    if en_ and sablon_kapili_pano(blok, 90, en_, mentese): print("şablon kapılı pano uygulandı:", blok)
H.add_text("GİRİŞ 90 · Şablon 2024 kapılı pano çizimi (Lokman 13:02); kanat ve kasa şablondan, 90'a uyarlandı", height=5,
           dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((763.0 - 150, 445.0 + 17.75 - 12))

# 4d) Köşeler 100×100 kutu profil (Lokman 12:09 ve 13:13 "köşeler 100*100 kutu profil olacak demiştim"): Motor'un 5×10 köşe
#     parçası yerine Güncel Şablon 2024'ün "100X100 DIŞ KÖŞE DİREĞİ" bloğu (10×10 kırmızı kutu + pano başlangıç çıkıntıları);
#     blok köşe yönüne göre aynalanır (şablon bloğunun varsayılan yönü: kutu (0,2.5)–(10,12.5), çıkıntılar aşağı ve sağa).
if SABLON_KOSE in hedef.blocks and ESKI_KOSE in hedef.blocks:
    KOSELER = {(0.0, 0.0): (0.0, 12.5, 1, -1),            # ön-sol: duvarlar yukarı ve sağa
               (0.0, 696.0): (0.0, 693.5, 1, 1),          # arka-sol: aşağı ve sağa
               (758.0, 696.0): (763.0, 693.5, -1, 1),     # arka-sağ: aşağı ve sola
               (758.0, 126.25): (763.0, 138.75, -1, -1),  # sağ duvar – balkon arka duvarı: yukarı ve sola
               (444.25, 126.25): (444.25, 123.75, 1, 1),  # salon sağ duvarı (444,25–454,25, kaymış) – balkon arka duvarı: aşağı ve sağa
               (449.25, 0.0): (454.25, 12.5, -1, -1)}     # salon sağ duvarı – ön duvar: yukarı ve sola
    n_kose = 0
    for e in list(H.query("INSERT")):
        if e.dxf.name != ESKI_KOSE: continue
        kat_dx = 1100.0 if e.dxf.insert.x >= 1000 else 0.0
        key = (round(e.dxf.insert.x - kat_dx, 2), round(e.dxf.insert.y, 2))
        if key not in KOSELER: print("köşe eşlenemedi:", key); continue
        ix, iy, xs, ys = KOSELER[key]
        H.add_blockref(SABLON_KOSE, (kat_dx + ix, iy), dxfattribs={"xscale": xs, "yscale": ys, "layer": e.dxf.layer})
        H.delete_entity(e); n_kose += 1
    print("köşe direği şablon bloğuyla değiştirildi:", n_kose)
    sayim.pop(kart_adi(ESKI_KOSE), None)
    try: hedef.blocks.delete_block(ESKI_KOSE, safe=True)
    except Exception as ex: print("eski köşe bloğu silinemedi (başka yerde kullanılıyor):", str(ex)[:80])

# 4g) ZEMİN KAT — DİZİLİMDEN (Lokman 15:18 arka sıra, 15:22 sol taraf, 15:23 balkon 40 serbest). Verilen kenarlar Lokman'ın
#     dizilimiyle, verilmeyenler (sağ, ön, iç) Motor'un dizilimine yakın; hepsi 100'lük pano + 10 köşe profili. Motor'un zemin planı
#     (akslar hariç) silinir ve bu veriden yeniden kurulur. Dizilim listeleri: ("pano", boy, blok adı) | ("profil",) | ("acik", boy).
DOLU = lambda L: ("pano", L, f"100'LÜK {en_yaz(L)}'LİK PANO")
PRF = ("profil",)
ZEMIN = {
  # dış duvarlar: (başlangıç x, y, yön, dizi); yön "+x": bant y..y+10, x artar; "+y": bant x..x+10, y artar
  "sol":   (0.0, 0.0, "+y", [PRF, DOLU(125.5), ("pano", 125.5, "100'LÜK 125'LİK (120x125) PENCERELİ PANO"), DOLU(125.5),       # 10 + 3 pano (SALON)
                             DOLU(125.5), ("pano", 125.5, "100'LÜK 125'LİK (120x125) PENCERELİ PANO"), DOLU(58.5), PRF]),       # + 2 pano + 58,5 (ODA) + 10 = 706
  "arka":  (0.0, 696.0, "+x", [PRF, DOLU(125.5), DOLU(125.5), DOLU(62.75), PRF, ("acik", 188.25), PRF,                           # 10 + 2,5 pano | 10 + 1,5 pano kova + 10
                             ("pano", 125.5, "100'LÜK 125'LİK (60x40) VASİSTASLI PANO"), DOLU(95.5), PRF]),                     # | 1 pano + 95,5 + 10 = 763
  "sag":   (753.0, 706.0, "-y", [PRF, DOLU(125.5), ("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(90'LIK)"), DOLU(125.5), DOLU(125.5),  # Motor dizilimi (arkadan)
                             DOLU(57.75), PRF]),                                                                                   # … 136,25'te balkon duvarı profili
  "on":    (0.0, 0.0, "+x", [PRF, DOLU(125.5), ("pano", 125.5, "100'LÜK 125'LİK (120x180) PENCERELİ PANO"), DOLU(125.5), DOLU(57.75), PRF]),  # 444,25'te salon sağ duvarı profili
  "salon_sag": (444.25, 10.0, "+y", [DOLU(116.25)]),                                                                              # salon sağ dış duvarı 10→126,25
  "balkon_arka": (454.25, 126.25, "+x", [DOLU(57.75), ("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(90'LIK) [SOL]"),
                             ("pano", 115.5, "100'LÜK 115.5'LİK (60x125) PENCERELİ PANO")]),                                    # 454,25→753; 753'te sağ profil
  # iç duvarlar (100'lük)
  "oda_salon": (10.0, 381.5, "+x", [DOLU(125.5), DOLU(125.5), DOLU(62.75), PRF, ("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(82'LİK) [SAG ÜST]"),
                             DOLU(47.75), ("acik", 10.0), ("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(82'LİK) [SAG ALT]"), DOLU(110.5)]),  # 10→753; kova sol profili 323,75; T 507–517
  "salon_mutfak": (507.0, 136.25, "+y", [DOLU(125.5), DOLU(119.75)]),                                                              # 136,25→381,5
  "kova_sol": (323.75, 391.5, "+y", [("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(82'LİK) [SOL ALT]"), DOLU(179.0), PRF, DOLU(125.5), PRF]),  # 391,5→696, profil, çıkma 706→831,5, profil
  "kova_sag": (522.0, 565.5, "+y", [PRF, DOLU(120.5), PRF, DOLU(125.5), PRF]),                                                     # 565,5 profil, 575,5→696, profil, çıkma, profil
  "wc_on":  (532.0, 565.5, "+x", [("pano", 125.5, "100'LÜK 125'LİK KAPILI PANO(82'LİK) [SOL ÜST]"), DOLU(95.5)]),     # 532→753
  "cikma_arka": (333.75, 831.5, "+x", [DOLU(125.5), DOLU(62.75)]),                                                                  # 333,75→522
}
ODA_ADLARI = {"ODA": (165, 540), "SALON": (220, 200), "HOL": (427, 480), "MERDİVEN": (427, 640), "WC": (642, 640), "WC HOLÜ": (642, 470),
              "MUTFAK": (635, 260), "BALKON": (600, 60)}

def zemin_dizilimden(kat_adi="ZEMİN KAT"):
    dx = 0.0
    # --- 1) Motor'un zemin planını sil (akslar, aks yazıları ve başlık kalır)
    for e in list(H):
        if not e.is_alive: continue
        t = e.dxftype(); lay = e.dxf.layer
        p_ = None
        for alan in ("insert", "start", "defpoint", "center"):
            if e.dxf.hasattr(alan): p_ = e.dxf.get(alan); break
        if p_ is None and t == "LWPOLYLINE": pts = list(e.get_points()); p_ = pts[0] if pts else None
        if p_ is None or p_[0] > 1000 or p_[0] < -200 or p_[1] < -200 or p_[1] > 960: continue
        if lay in ("AKS", "AKS_YAZI"): continue
        if t in ("TEXT", "MTEXT") and p_[1] > 900 and "KAT PLANI" not in e.dxf.text: continue       # başlık (Motor'un "KAT PLANI" yazısı silinir)
        if t == "INSERT" and not (("PANO" in e.dxf.name) or ("DİREĞİ" in e.dxf.name) or ("H BAĞLANTI" in e.dxf.name) or ("VERANDA" in e.dxf.name) or ("DİKME" in e.dxf.name)):
            continue
        if t == "INSERT": say(kart_adi(e.dxf.name), kat_adi, -1)
        H.delete_entity(e)
    for k in list(sayim):                      # negatif kalanları temizle
        if sayim[k].get(kat_adi, 0) <= 0: sayim[k].pop(kat_adi, None)
    # --- 2) kur
    def profil(x, y, xs, ys):
        ix = x if xs == 1 else x + 10; iy = (y - 2.5) if ys == 1 else (y + 12.5)
        H.add_blockref(SABLON_KOSE, (ix, iy), dxfattribs={"xscale": xs, "yscale": ys, "layer": "KOSE_PROFIL_100"})
    def blok(ad, L):
        if ad not in hedef.blocks:
            if "VASİSTASLI" in ad and "100'LÜK 115.5'LİK (60x40) VASİSTASLI PANO" in hedef.blocks:     # 115,5'lik vasistaslıyı 125,5'e uzat
                kb = hedef.blocks.get("100'LÜK 115.5'LİK (60x40) VASİSTASLI PANO"); nb = hedef.blocks.new(ad)
                polys = [k for k in kb if k.dxftype() == "LWPOLYLINE"]
                son = max(polys, key=lambda k: max(y for _, y, *__ in k.get_points()))
                for k in kb:
                    c = k.copy(); nb.add_entity(c)
                    if k is son: c.set_points([(x, (L if abs(y - 115.5) < 1e-6 else y)) for x, y, *_ in k.get_points()], format="xy")
                yeni_adlar.add(ad); return ad
            if "KAPILI" in ad or "PENCERELİ" in ad or "VASİSTAS" in ad: print("  blok yok, dolu kondu:", ad)
            return pano_blogu(f"100'LÜK {en_yaz(L)}'LİK PANO", L)
        return ad
    X_YONLU = lambda ad: "KAPILI PANO(90'LIK)" in ad          # şablon tarzı dış kapı: geometri yerel x boyunca (bant y 0–10)
    ON_YUZLU = {"on", "balkon_arka"}                            # ön cepheye bakan yatay duvarlar: sembol dışa baksın (rot 90, Motor gibi)
    zincirler = {}
    for ad, (x0, y0, yon, dizi) in ZEMIN.items():
        x, y = x0, y0; noktalar = [x0 if yon in ("+x",) else y0]
        dis = ad in ("sol", "arka", "sag", "on", "salon_sag", "balkon_arka", "cikma_arka") or ad.startswith("kova")
        kat = {"layer": "DIS_DUVAR_100" if dis else "IC_DUVAR_100"}
        for el in dizi:
            if el[0] == "profil":
                if yon == "+x":   profil(x, y, 1, 1); x += 10
                elif yon == "+y": profil(x, y, 1, 1); y += 10
                else:             profil(x, y - 10, 1, 1); y -= 10          # -y: yukarıdan aşağı
            elif el[0] == "acik":
                if yon == "+x": x += el[1]
                elif yon == "+y": y += el[1]
                else: y -= el[1]
            else:
                _, L, bad = el; bad = blok(bad, L)
                if yon == "+x":
                    if X_YONLU(bad):      H.add_blockref(bad, (x, y), dxfattribs=kat)                                   # bant y..y+10, kanat +y (içeri)
                    elif ad in ON_YUZLU:  H.add_blockref(bad, (x + L, y), dxfattribs={"rotation": 90, **kat})
                    else:                 H.add_blockref(bad, (x, y + 10), dxfattribs={"rotation": 270, **kat})
                    x += L
                elif yon == "+y":
                    H.add_blockref(bad, (x, y), dxfattribs=kat); y += L
                else:   # -y (sağ dış duvar, arkadan öne)
                    if X_YONLU(bad):      H.add_blockref(bad, (x + 10, y - L), dxfattribs={"rotation": 90, **kat})      # bant x..x+10, kanat −x (içeri)
                    else:                 H.add_blockref(bad, (x, y - L), dxfattribs=kat)
                    y -= L
                say(kart_adi(bad), kat_adi, 1)
            noktalar.append(x if yon == "+x" else y)
        zincirler[ad] = noktalar
    # sola yaslı kapı varyantları (açıklık 11,5 payla) — bloklar yoksa üretici yaslar
    kapiyi_yasla((517.0, 391.5), 270, 11.5, kat_adi); kapiyi_yasla((532.0, 575.5), 270, 11.5, kat_adi)
    # balkon kirişleri 40 dışarıda (serbest ölçü — Lokman 15:23) ve köşe dikmesi
    on_ad, yan_ad = f"100'LÜK VERANDA PROFİLİ {en_yaz(308.75)} (ÖN)", f"100'LÜK VERANDA PROFİLİ {en_yaz(166.25)} (YAN)"
    for ad_, L_, dik_ in ((on_ad, 308.75, False), (yan_ad, 166.25, True)):
        if ad_ not in hedef.blocks:
            b_ = hedef.blocks.new(ad_)
            b_.add_lwpolyline([(0, 0), (10, 0), (10, L_), (0, L_)] if dik_ else [(0, 0), (L_, 0), (L_, 10), (0, 10)], close=True); yeni_adlar.add(ad_)
    if "100X100 VERANDA DİKMESİ" not in hedef.blocks:
        hedef.blocks.new("100X100 VERANDA DİKMESİ").add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True)
    H.add_blockref(on_ad, (454.25, -40), dxfattribs={"layer": "VERANDA_PROFIL_100"}); say(on_ad, kat_adi, 1)
    H.add_blockref(yan_ad, (753.0, -40), dxfattribs={"layer": "VERANDA_PROFIL_100"}); say(yan_ad, kat_adi, 1)
    H.add_blockref("100X100 VERANDA DİKMESİ", (753.0, -40), dxfattribs={"layer": "VERANDA_DIKME"}); say("100X100 VERANDA DİKMESİ", kat_adi, 1)
    profil(753.0, 126.25, -1, 1)                                             # sağ duvar – balkon arka duvarı köşesi
    # merdiven (kova iç 333,75→522 × 570,5→696 + çıkma 706→831,5)
    L_ = "MERDIVEN"; XI0, XI1 = 333.75, 522.0; XM = (XI0 + XI1) / 2; YON, YC0, YC1 = 570.5, 706.0, 831.5
    def cz(x0_, y0_, x1_, y1_): H.add_line((x0_, y0_), (x1_, y1_), dxfattribs={"layer": L_})
    cz(XM, YON, XM, YC1)
    for i in range(1, 6): cz(XI0, YON + 25 * i, XI1, YON + 25 * i)
    cz(XI0, YC0, XI1, YC0)
    for xx, yy in ((XI0, YC0 + 60), (XI0 + 30, YC1), (XM, YC1), (XI1 - 30, YC1), (XI1, YC0 + 60)): cz(XM, YC0, xx, yy)
    XR, XL = (XM + XI1) / 2, (XI0 + XM) / 2
    H.add_circle((XR, YON + 15), 10, dxfattribs={"layer": L_})
    ytop = YON + 0.8 * (YC1 - YON); cz(XR, YON + 25, XR, ytop); cz(XR, ytop, XL, ytop); cz(XL, ytop, XL, YON + 30)
    H.add_lwpolyline([(XL - 12, YON + 30), (XL + 12, YON + 30), (XL, YON), (XL - 12, YON + 30)], dxfattribs={"layer": L_})
    H.add_line((XI0, YON), (XI1, YON), dxfattribs={"layer": "ACIK_SINIR", "linetype": "DASHED"})   # kova önü açık
    # oda adları
    for ad_, (x_, y_) in ODA_ADLARI.items():
        H.add_text(ad_, height=16, dxfattribs={"layer": "ODA_ADLARI", "style": "ARIAL_TR"}).set_placement((x_, y_))
    # akslı pafta zincirleri (pano pano)
    _zincir(zincirler["arka"] + [763.0], 866, True, kat="OLCULER"); _zincir([0.0, 763.0], 900, True, kat="OLCULER")
    _zincir(zincirler["sol"], -45, False, kat="OLCULER")
    _zincir(sorted(set(zincirler["sag"])), 763 + 45, False, kat="OLCULER")
    _zincir(zincirler["on"], -60, True, kat="OLCULER"); _zincir([454.25, 763.0], -95, True, kat="OLCULER")
    _zincir([-40.0, 0.0], 454.25 - 30, False, kat="OLCULER")
    H.add_text("ZEMİN KAT · DİZİLİMDEN (Lokman 15:18 arka: 10|2,5p|10|1,5p|10|1p+95,5|10 · 15:22 sol: 10|3p|2p|58,5|10 · balkon 40 serbest) · sağ ve ön Motor dizilimi",
               height=6, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((0, 925))
    print("zemin dizilimden kuruldu; arka:", [round(v, 2) for v in zincirler["arka"]], "sol:", [round(v, 2) for v in zincirler["sol"]])

# 4e) KIYAS KOPYASI (Lokman 14:00 "çizimi sağa kaydır, dış ölçüleri ver; planı pano yerleşiminin dışında tekrar yana al, asıl planla
#     kıyaslayalım"): her katın planı x = 3300 / 4400'e kopyalanır (Motor'un aks ve pano ölçüleri olmadan); plandaki gibi dış ve oda
#     ölçü zincirleri (duvar yüzünden yüzüne) ve "PLAN ↔ ÇİZİM" listesi eklenir. Zincirler duvar bantlarından otomatik ölçülür.
hedef.layers.add("KIYAS_OLCU", color=5) if "KIYAS_OLCU" not in hedef.layers else None
KIYAS_X = {"ZEMİN KAT": 3300.0, "1. KAT": 4400.0}
PLAN_DEGERLERI = {   # Lokman'ın planındaki ölçüler (28.10 görseli), zincir sırasıyla
    "ZEMİN KAT": [("Arka sıra (ODA | kova | WC)", "327 | 200 | 196"), ("Üst dış (sol | çıkma | sağ)", "337 | 220 | 206"),
                  ("Sol: ODA / SALON derinliği", "287 / 389"), ("Sağ: WC / WC holü / MUTFAK / BALKON", "125 / 152 / 254 / 165"),
                  ("Orta sıra (SALON | MUTFAK)", "457 | 276"), ("Ön (SALON | BALKON)", "406 | 337"), ("Dış", "763 × 706")],
    "1. KAT":    [("Arka sıra (ODA 1 | kova | BANYO)", "327 | 200 | 196"), ("Üst dış (sol | çıkma | sağ)", "337 | 220 | 206"), ("Dış", "763 × 706")],
}

def _bantlar(kopya):
    """Kopyadaki pano bloklarından duvar bantları: (x0, y0, x1, y1)."""
    from ezdxf import bbox as _bb
    out = []
    for e in kopya:
        if e.dxftype() != "INSERT": continue
        ad = e.dxf.name; L = pano_boyu_ad(ad); x, y = e.dxf.insert.x, e.dxf.insert.y; r = e.dxf.rotation % 360
        if L is None: continue                                   # köşe direği, H, veranda: bant değil
        if abs(r) < 1e-6:        out.append((x, y, x + 10, y + L))          # dik bant
        elif abs(r - 270) < 1e-6: out.append((x, y - 10, x + L, y))         # yatay, sol uçtan
        elif abs(r - 90) < 1e-6:  out.append((x - L, y, x, y + 10))         # yatay, sağ uçtan
    return out

def _zincir(noktalar, taban, yatay, kat="KIYAS_OLCU"):
    """Ardışık noktalar arasında ölçü zinciri (yatay: x listesi, taban y; dikey: y listesi, taban x)."""
    for a_, b_ in zip(noktalar, noktalar[1:]):
        if b_ - a_ < 0.5: continue
        if yatay: dim = H.add_linear_dim(base=(a_, taban), p1=(a_, taban), p2=(b_, taban), dimstyle="PORTMAN", dxfattribs={"layer": kat})
        else:     dim = H.add_linear_dim(base=(taban, a_), p1=(taban, a_), p2=(taban, b_), angle=90, dimstyle="PORTMAN", dxfattribs={"layer": kat})
        dim.render()

def _kesen_noktalar(bantlar, sabit, yatay, lo, hi):
    """Yatay probe (y = sabit): dik bantların x aralıkları; dikey probe (x = sabit): yatay bantların y aralıkları → sıralı sınır noktaları."""
    ar = []
    for x0, y0, x1, y1 in bantlar:
        if yatay and y0 - 1e-6 <= sabit <= y1 + 1e-6 and (x1 - x0) <= 10.01: ar.append((x0, x1))
        if not yatay and x0 - 1e-6 <= sabit <= x1 + 1e-6 and (y1 - y0) <= 10.01: ar.append((y0, y1))
    ar.sort(); birles = []
    for a_, b_ in ar:
        if birles and a_ <= birles[-1][1] + 1e-6: birles[-1] = (birles[-1][0], max(birles[-1][1], b_))
        else: birles.append((a_, b_))
    pts = [lo] + [v for ab in birles for v in ab] + [hi]
    pts = sorted(set(round(v, 2) for v in pts if lo - 1e-6 <= v <= hi + 1e-6))
    return pts

zemin_dizilimden()      # 4g (zincir yardımcıları tanımlandıktan sonra)

for kat_adi, _, dx in KATLAR:
    kx = KIYAS_X[kat_adi]; kay = kx - dx
    kopya = []
    for e in list(H):
        if e.dxftype() == "DIMENSION" or e.dxf.layer in ("AKS", "AKS_YAZI", "OLCULER", "OZEL_PANEL_OLCU_CM", "MALZEME_KARTI", "SABLON_KARTI",
                                                          "KESIT", "KESIT_KIRIS", "KESIT_BETOPAN", "KESIT_CATI", "KOSE_SUREKLI_100", "KIYAS_OLCU"):
            continue
        p = None
        for alan in ("insert", "start", "center"):
            if e.dxf.hasattr(alan): p = e.dxf.get(alan); break
        if p is None and e.dxftype() == "LWPOLYLINE":
            pts = list(e.get_points()); p = pts[0] if pts else None
        if p is None or not (dx - 160 <= p[0] <= dx + 900 and -120 <= p[1] <= 960): continue
        if e.dxftype() in ("TEXT", "MTEXT") and p[1] > 838: continue     # başlık ve notlar kopyaya girmez (ölçülerle çakışır)
        c = e.copy(); H.add_entity(c)
        try: c.translate(kay, 0, 0)
        except Exception: pass
        kopya.append(c)
    bant = _bantlar(kopya)
    # dış zincirler (üst: gövde | çıkma | gövde; alt: ön duvar | balkon) ve toplam
    # yalnız DIŞ ölçüler (Lokman 14:36 "iç ölçüleri boş ver"): dış yüzden dış yüze, her kenar ayrı ayrı; çıkma 251 × 125,5
    XA_, XB_ = kx + 323.75, kx + 532.0                             # kova/çıkma dış yüzleri (Lokman 15:18: 10 + 1,5 pano + 10 = 208,25)
    _zincir([kx, XA_, XB_, kx + 763], 876, True)                   # üst: sol gövde | çıkma 271 | sağ gövde
    _zincir([kx, kx + 763], 910, True)                             # toplam 763
    _zincir([kx, kx + 454.25, kx + 763], -90, True)                # alt: ön duvar | balkon (kiriş dış yüzüne kadar)
    _zincir([0, 706], kx - 40, False)                              # sol: 706
    _zincir([0, 706], kx + 763 + 40, False)                        # sağ: 706
    _zincir([706, 831.5], XB_ + 40, False)                         # çıkma: net pano 125,5 (10'luk kolonlar ölçülenmez — Lokman 14:55)
    _zincir([706, 831.5], XA_ - 40, False)
    _zincir([0, 841.5], kx + 763 + 80, False)                      # çıkmayla toplam 841,5
    _zincir([-40, 0], kx + 454.25 - 40, False)                     # balkon kiriş çizgisi 40 dışarıda (Lokman 14:43)
    H.add_text(f"{kat_adi} · DIŞ ÖLÇÜLER (dış yüzden dış yüze) · Lokman 14:36: iç ölçüler yok, sıra sıra",
               height=9, dxfattribs={"layer": "KIYAS_OLCU"}).set_placement((kx, 945))
    yy = 930
    for ad_, deger in PLAN_DEGERLERI.get(kat_adi, []):
        H.add_text(f"PLAN · {ad_}: {deger}", height=6, dxfattribs={"layer": "KIYAS_OLCU"}).set_placement((kx + 790, yy)); yy -= 10
    H.add_text("Çizim değerleri zincirlerde (pano aksından: 125,5 ızgarası + 100'lük duvarlar). Fark = ızgaraya oturtma.", height=6,
               dxfattribs={"layer": "KIYAS_OLCU"}).set_placement((kx + 790, yy - 4))

# 5) kesit / kat kotları (kısa kenar y=706; makas y'yi geçer → beşik profil bu kesitte)
KX, KY = 0.0, -900.0
derinlik = 706.0
for y0, y1, kat, renk in [(0, 250, "KESIT", 7), (250, 280, "KESIT_KIRIS", 30), (280, 282, "KESIT_BETOPAN", 3), (282, 532, "KESIT", 7)]:
    H.add_lwpolyline([(KX, KY+y0), (KX+derinlik, KY+y0), (KX+derinlik, KY+y1), (KX, KY+y1), (KX, KY+y0)], dxfattribs={"layer": kat})
# sürekli köşe direkleri 100×100 (iki kat boyu 532)
for x in (KX, KX+derinlik-10):
    H.add_lwpolyline([(x, KY), (x+10, KY), (x+10, KY+532), (x, KY+532), (x, KY)], dxfattribs={"layer": "KOSE_SUREKLI_100"})
# çatı: beşik %33, saçak 30, topuk 10
sacakli = derinlik + 60; mahya = 10 + sacakli/2*0.33
H.add_lwpolyline([(KX-30, KY+532), (KX-30, KY+542), (KX+derinlik/2, KY+532+mahya), (KX+derinlik+30, KY+542), (KX+derinlik+30, KY+532)],
                 dxfattribs={"layer": "KESIT_CATI"})
for kot, yazi in [(0, "±0,00 zemin"), (250, "+2,50 zemin duvar üstü"), (280, "+2,80 çelik kiriş bölgesi (300 mm, R02; Soru 6)"),
                  (282, "+2,82 Betopan 20 mm (R02)"), (532, "+5,32 üst duvar üstü"), (532+mahya, f"+{(532+mahya)/100:.2f} mahya (%33, saçaklı açıklık {sacakli:.0f})")]:
    H.add_line((KX+derinlik+40, KY+kot), (KX+derinlik+80, KY+kot), dxfattribs={"layer": "KESIT"})
    H.add_text(yazi, height=7, dxfattribs={"layer": "KESIT"}).set_placement((KX+derinlik+85, KY+kot-3))
H.add_text("KISA KENAR KESİTİ / KAT KOTLARI — döşeme tek katla aynı (Lokman 28.10); ara kat R02 verisi, kural değil", height=9,
           dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((KX, KY-30))
H.add_text("Köşe direkleri 100×100 sürekli, iki kat boyu (Lokman 28.10 12:09; R02 100×100×5320; et kalınlığı Soru 8)", height=7,
           dxfattribs={"layer": "KOSE_SUREKLI_100"}).set_placement((KX, KY-48))

# 6) malzeme kartı
MX, MY = 2300.0, 940.0
H.add_text("MALZEME KARTI — blok adı = malzeme adı (Güncel Şablon 2024 kuralı)", height=10, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX, MY))
H.add_text("Blok / malzeme", height=6, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX, MY-18))
for i, (kat_adi, _, _) in enumerate(KATLAR):
    H.add_text(kat_adi, height=6, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+430+i*70, MY-18))
H.add_text("Toplam", height=6, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+580, MY-18))
H.add_text("Şablon", height=6, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+650, MY-18))
satirlar = []
y = MY - 32
for ad in sorted(sayim, key=lambda s: (0 if s.startswith("100'L") else 1 if s.startswith("60'L") else 2, s)):
    c = sayim[ad]; top = sum(c.values())
    durum = "var" if ad in SABLONDA_VAR else ("yeni (kural)" if ad in yeni_adlar else "yeni")
    H.add_text(ad, height=5.5, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX, y))
    for i, (kat_adi, _, _) in enumerate(KATLAR):
        H.add_text(str(c.get(kat_adi, 0)), height=5.5, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+430+i*70, y))
    H.add_text(str(top), height=5.5, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+580, y))
    H.add_text(durum, height=5.5, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX+650, y))
    satirlar.append((ad, c, top, durum)); y -= 11
# ortak parçalar
H.add_text("ORTAK: 100X100 DIŞ KÖŞE DİREĞİ (şablon bloğu; kutu profil, sürekli iki kat boyu 5320 R02) — kat kat sayılmaz: 6 gövde köşesi + 2 çıkma arka köşesi + 2 çıkma–gövde birleşimi (Lokman 13:57) = 10", height=5.5,
           dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX, y-6))
H.add_text("Not: kapılı panolarda [SAĞ ÜST] vb. ek kanat yönüdür, malzeme adına girmez; 'yeni (kural)' = şablonda yok, şablonun ad kuralıyla türetildi.",
           height=5, dxfattribs={"layer": "MALZEME_KARTI"}).set_placement((MX, y-20))

# 7) Şablon 2024 blok kartı (varsa) — isimleriyle referans
if KUTUPHANE.exists():
    kut = ezdxf.readfile(str(KUTUPHANE))
    adlar = sorted([b.name for b in kut.blocks if not b.name.startswith("*") and b.name not in ("$MODEL_SPACE", "$PAPER_SPACE")], key=str.lower)
    # hedefte aynı adlı (Motor'dan gelen, taban noktası uzak) blok varsa şablon kopyasını ayrı adla al
    for n in list(adlar):
        if n in hedef.blocks:
            kut.blocks.rename_block(n, n + " (ŞABLON)")
            for e in kut.modelspace().query("INSERT"):
                if e.dxf.name == n: e.dxf.name = n + " (ŞABLON)"
            for b in kut.blocks:
                for e in b.query("INSERT"):
                    if e.dxf.name == n: e.dxf.name = n + " (ŞABLON)"
    adlar = [n + " (ŞABLON)" if n in hedef.blocks else n for n in adlar]
    imp = Importer(kut, hedef)
    hedef_adi = {}
    for n in adlar:
        try: hedef_adi[n] = imp.import_block(n, rename=True)
        except Exception as ex: print("kütüphane bloğu alınamadı", n, ex)
    imp.finalize()
    adlar = [n for n in adlar if n in hedef_adi]
    for n in adlar: hedef.blocks[hedef_adi[n]].base_point = (0, 0, 0)
    SX, SY = 0.0, -1100.0
    H.add_text("GÜNCEL ŞABLON 2024 · yapı blokları (ad [en × boy], cm) — kaynak sablon_inceleme/sablon_bloklari_yapi_v2.dxf", height=10,
               dxfattribs={"layer": "SABLON_KARTI"}).set_placement((SX, SY+40))
    from ezdxf import bbox
    for i, n in enumerate(adlar):
        x = SX + (i % 8) * 280; yy = SY - (i // 8) * 150
        H.add_blockref(hedef_adi[n], (x, yy), dxfattribs={"layer": "SABLON_KARTI"})
        bb = bbox.extents(hedef.blocks[hedef_adi[n]], fast=True)
        boy = f" [{bb.size.x:.1f} x {bb.size.y:.1f}]" if bb.has_data else ""
        H.add_text(n + boy, height=4.5, dxfattribs={"layer": "SABLON_KARTI"}).set_placement((x, yy-14))

# Akslar silik ve seyrek tireli (Lokman 13:53 "aksları daha belirsiz, tireleri daha aralıklı çiz"): Motor AKS katmanı cyan + CENTER
# (LTSCALE 1'de sık). Burada katman koyu gri (ACI 8), çizgi tipi AKS_SEYREK: 50 çizgi – 25 boşluk – nokta – 25 boşluk; aks yazıları da gri.
if "AKS_SEYREK" not in hedef.linetypes:
    hedef.linetypes.add("AKS_SEYREK", pattern=[100.0, 50.0, -25.0, 0.0, -25.0], description="Aks: ____ . ____ . (seyrek)")
for ad_, lt_ in (("AKS", "AKS_SEYREK"), ("AKS_YAZI", "Continuous")):
    if ad_ in hedef.layers:
        L_ = hedef.layers.get(ad_); L_.color = 8; L_.dxf.linetype = lt_
for e in H.query('LINE[layer=="AKS"]'):
    e.dxf.linetype = "BYLAYER"; e.dxf.color = 256; e.dxf.ltscale = 1.0

# Türkçe harfler: AutoCAD'in txt.shx'i İ/Ş/—'yi "?" basar → bütün yazılar Arial (TrueType) stiline
if "ARIAL_TR" not in hedef.styles:
    hedef.styles.new("ARIAL_TR", dxfattribs={"font": "arial.ttf"})
for e in H.query("TEXT MTEXT"):
    e.dxf.style = "ARIAL_TR"
for b in hedef.blocks:
    for e in b.query("TEXT MTEXT"):
        e.dxf.style = "ARIAL_TR"
for ds in hedef.dimstyles:
    try: ds.dxf.dimtxsty = "ARIAL_TR"
    except Exception: pass
print("audit öncesi DIMENSION:", len(H.query("DIMENSION")))
aud = hedef.audit()
print("audit hata", len(aud.errors), "düzeltme", len(aud.fixes))
for f in aud.fixes[:4]: print("  düzeltme:", f.code, f.message[:160])
print("audit sonrası DIMENSION:", len(H.query("DIMENSION")))
cikti = CIKTI / "Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf"
hedef.saveas(str(cikti))
print("yazıldı", cikti.name, cikti.stat().st_size // 1024, "KB; blok", len([b for b in hedef.blocks if not b.name.startswith('*')]), "varlık", len(H))

# malzeme kartı md
L = ["# Malzeme kartı · İE-22 çift kat, Şablon 2024 blok adları (28 Ekim 2026)\n",
     "Blok adı = malzeme adı. Geometri Motor'un panoları (Astra v1.4.3), adlar Güncel Şablon 2024 kuralı. Kaynak: `uret_cift_kat_bloklu.py`.\n",
     "| Blok / malzeme | " + " | ".join(k for k, _, _ in KATLAR) + " | Toplam | Şablonda |", "|---|---:|---:|---:|---|"]
for ad, c, top, durum in satirlar:
    L.append(f"| {ad} | " + " | ".join(str(c.get(k, 0)) for k, _, _ in KATLAR) + f" | {top} | {durum} |")
L.append("| ORTAK · 100X100 DIŞ KÖŞE DİREĞİ (kutu profil, sürekli iki kat boyu 5320; Lokman 12:09/13:13) — 6 gövde köşesi + 2 çıkma arka köşesi + 2 çıkma–gövde birleşimi (13:57) | — | — | 10 | var (şablon bloğu; '2X100X100 DIŞ KÖŞE DİREĞİ' varyantı da var) |")
L.append("\nÇift kat ızgarası (Lokman 13:30; Astra R02): akslar köşe kolonunun iç yüzünden 10 + 125,5k; cephe 10 + 5 × 125,5 + 115,5 + 10 = 763. "
         "Motor 753'lük gövdeyle üretti, üretici sol dış duvarı yerinde bırakıp içleri +5, sağ dış duvarı +10 kaydırdı (Motor'da kural yok, İE-22 PR-1). "
         "İç duvarlar 100'lük (13:32); Motor 'iç = dış kalınlık' sınırını deneme betiği atladı (bulgu). Merdiven kovası pano aksında (2 pano, iç 241) + çıkma 1 pano; "
         "çıkma panoları ve kesik panolar elle (yukarıda sayılı); merdiven çizgileri MERDIVEN katmanı. Dış kapılar şablonun kapılı pano çizimi (13:02); "
         "köşeler şablonun 100X100 DIŞ KÖŞE DİREĞİ bloğu (13:13); iç kapılar henüz Motor'un Astra sembolü. "
         "Sağ dış duvara komşu mahallerin m² yazıları Motor'un (753'e göre): 5 cm dar, yaklaşık.")
(CIKTI / "Portman_IE22-CK01_CIFT_KAT_malzeme_karti.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("kart yazıldı;", len(satirlar), "satır")
