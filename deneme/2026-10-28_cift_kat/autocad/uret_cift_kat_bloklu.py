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
KATLAR = [("ZEMİN KAT", KOK / "sonuc/zemin_kat/Portman_IE22-CK01-ZEMIN_r01.dxf", 0.0),
          ("1. KAT",    KOK / "sonuc/birinci_kat/Portman_IE22-CK01-KAT1_r01.dxf", 1100.0)]
KUTUPHANE = CIKTI / "sablon_inceleme/sablon_bloklari_yapi_v2.dxf"
ANA = (-160, -120, 900, 960)   # Motor DXF'inde ana (akslı) planın bölgesi, cm

SABLONDA_VAR = {  # Şablon 2024'te bire bir bulunan adlar
    "100'LÜK 125'LİK PANO", "100'LÜK 125'LİK (60x40) VASİSTASLI PANO", "100'LÜK 125'LİK (120x100) PENCERELİ PANO",
    "100'LÜK 125'LİK KAPILI PANO(80'LİK)", "100'LÜK 117'LİK PANO", "60X60 3 LÜ H BAĞLANTI DİREĞİ", "100X100 DIŞ KÖŞE DİREĞİ",
}

def en_yaz(cm: float) -> str:
    if abs(cm - 125.5) < 1e-6: return "125"          # şablonun yazımı
    return f"{cm:.2f}".rstrip("0").rstrip(".")   # AutoCAD blok adında virgül yasak; şablon da nokta kullanır (122.5)

def sablon_adi(bom: str):
    """BOM_D13_1255p0_DIS_P120x125 → ("100'LÜK 125'LİK (120x125) PENCERELİ PANO", "pano")."""
    m = re.match(r"BOM_([DI])\d+_(\d+)p(\d)_(DIS|IC)_(.+)$", bom)
    if m:
        en = int(m.group(2)) / 10 + int(m.group(3)) / 100 * 10 / 10  # 1255p0 → 125.5 ; 627p5 → 62.75
        en = int(m.group(2)) / 10 + int(m.group(3)) / 100
        kal = "100'LÜK" if m.group(4) == "DIS" else "60'LIK"
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
    if bom.startswith("BOM_B01_IC_KOSE"):    return "60X30 İÇ KÖŞE BAĞLANTISI", "profil"
    if bom.startswith("BOM_B03_UCLU_H_60"):  return "60X60 3 LÜ H BAĞLANTI DİREĞİ", "profil"
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


def merdiven_ciz(dx: float, kat1: bool):
    """Lokman'ın planındaki merdiven, bire bir (28.10 13:00 "Aynı buradaki gibi çiz"; zemin ve 1. kat planları aynı çizim).
    Kutu: iç 200 × (125 gövdede + 10 duvar bandı + 115 çıkma) = 250 iç [planda 260 yazılı; 125'lik çıkma dışla ölçülmüş: 10 cm fark not],
    dış 220, duvar 10; sol duvar x 337–347, sağ 547–557 (ODA 327 + 10; WC 196 + 10 = 763 ✓); ön duvar y 561–571 (hol 152, WC 125 ile aynı hiza);
    çıkma 706–831 (dış). Merdiven: çift kollu U, kol 100; sağ kol 5 düz basamak (25), çıkmada 6 dönel basamak (180°), sol kol 5 düz → 16 rıht;
    başlangıç dairesi sağ kolda önde, yürüme çizgisi 150 → 200 → 50 → ok önde (üst kata önden varır).
    1. kat: ön açık (holle birleşir), çıkmanın arka duvarında 120/125 standart pencere (plan)."""
    L, D = "MERDIVEN", "MERDIVEN_DUVAR"
    X0, Y0, W, DER = dx + 347.0, 571.0, 200.0, 250.0
    def duvar(x0, y0, x1, y1):
        H.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], dxfattribs={"layer": D})
    duvar(X0 - 10, Y0 - 10, X0, Y0 + DER + 10)            # sol duvar (561 → 831)
    duvar(X0 + W, Y0 - 10, X0 + W + 10, Y0 + DER + 10)    # sağ duvar
    duvar(X0 - 10, Y0 + DER, X0 + W + 10, Y0 + DER + 10)  # çıkmanın arka duvarı (821–831)
    if not kat1:
        duvar(X0 - 10, Y0 - 10, X0 + W + 10, Y0)          # ön duvar: planda zeminde çizili (giriş açıklığı planda yok → soru)
    def cz(x0, y0, x1, y1):
        H.add_line((X0 + x0, Y0 + y0), (X0 + x1, Y0 + y1), dxfattribs={"layer": L})
    cz(100, 0, 100, DER)                                   # kol ayırıcı orta çizgi
    for y in (25, 50, 75, 100, 125):                       # 5 düz basamak (iki kol üst üste görünür: tam genişlik)
        cz(0, y, 200, y)
    cz(0, 135, 200, 135)                                   # gövde dış yüz hizası (706): dönel basamakların başlangıcı
    for x, y in ((0, 195), (35, DER), (100, DER), (165, DER), (200, 195)):   # 6 dönel basamak, merkez (100, 135)
        cz(100, 135, x, y)
    H.add_circle((X0 + 150, Y0 + 15), 12, dxfattribs={"layer": L})          # başlangıç (sağ kol)
    cz(150, 27, 150, 200); cz(150, 200, 50, 200); cz(50, 200, 50, 30)        # yürüme çizgisi
    H.add_lwpolyline([(X0 + 35, Y0 + 30), (X0 + 65, Y0 + 30), (X0 + 50, Y0), (X0 + 35, Y0 + 30)], dxfattribs={"layer": L})  # ok (varış)
    if kat1:
        H.add_lwpolyline([(X0 + 40, Y0 + DER), (X0 + 160, Y0 + DER), (X0 + 160, Y0 + DER + 10), (X0 + 40, Y0 + DER + 10), (X0 + 40, Y0 + DER)],
                         dxfattribs={"layer": "CIFT_KAT_NOT"})
        H.add_text("120/125 STANDART PENCERE (plan, 1. kat)", height=4.5, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((X0 + 42, Y0 + DER + 14))
    H.add_text("MERDİVEN · plan bire bir (Lokman 13:00): iç 200 × 250 (planda 260 yazılı), dış 220, çıkma 125 · çift kollu U, kol 100, "
               "5 + 6 dönel + 5 = 16 rıht (282/16 = 17,6), basamak 25", height=4.5, dxfattribs={"layer": L}).set_placement((X0 - 10, Y0 + DER + 28))
    H.add_text("Duvarlar planda 337/557 (220 dış); pano aksı 318,75/569,75 (245 iç) → Motor'a işlerken karar (Soru 9 ile)", height=4.5,
               dxfattribs={"layer": L}).set_placement((X0 - 10, Y0 + DER + 20))


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
    # 1) kaynaktaki blokları Şablon 2024 adıyla yeniden adlandır
    esleme = {}
    for b in list(kaynak.blocks):
        if not b.name.startswith("BOM_"): continue
        yeni, tur = sablon_adi(b.name)
        if yeni == b.name:          # ad değişmiyorsa (kapı/pencere sembolleri) dokunma
            continue
        esleme[b.name] = yeni
        if yeni not in SABLONDA_VAR and tur == "pano": yeni_adlar.add(kart_adi(yeni))
        if yeni in kaynak.blocks:      # aynı ada iki geometri (ör. kanat yönü eklerinden sonra olmamalı)
            yeni = yeni + f" {{{b.name[4:7]}}}"; esleme[b.name] = yeni
        kaynak.blocks.rename_block(b.name, yeni)
    for e in msp.query("INSERT"):
        if e.dxf.name in esleme: e.dxf.name = esleme[e.dxf.name]
    for b in kaynak.blocks:            # iç içe INSERT'ler (MNT_* kopyaları vs.)
        for e in b.query("INSERT"):
            if e.dxf.name in esleme: e.dxf.name = esleme[e.dxf.name]
    # 2) ana plan bölgesindeki varlıkları al
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
    merdiven_ciz(dx, kat1=(dx > 0))
    H.add_lwpolyline([(dx+444.25, 0), (dx+763, 0), (dx+763, -30), (dx+444.25, -30), (dx+444.25, 0)],
                     dxfattribs={"layer": "CIFT_KAT_NOT", "linetype": "DASHED"})
    H.add_text("BALKON TAŞMASI 30 (Motor'da yok · Soru 7)", height=6, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((dx+446, -44))

# 4b) Giriş kapısı (Lokman 28.10 12:34, Soru 1): sağ cephe, WC HOLÜ, 90'lık, içeri açılır. Motor bunu kendisi çiziyor:
#     BOM_D18_1255p0_DIS_K02 @ (763, 445) rot 90, iç sembol BOM_K03_DIS_KAPI_ACIKLIK900 (sınır kutusu 668,8–764,1 × 445–570,5).
#     12:45'te "Motor sembolü çizmedi (bulgu 7)" diye elle kırmızı kapı çizilmişti; yanlıştı — ad değiştirme iç sembolü bozduğu için
#     görünmüyordu (A023'te düzeltildi). Elle kapı 13:05'te kaldırıldı.
# 4c) Dış kapı çizimi Güncel Şablon 2024'ten (Lokman 13:02 "dış kapıda güncel şablon 2024'te var"): dış kapılı pano bloklarının
#     içeriği Motor'un Astra sembolü yerine şablonun kapılı pano çizimi (90'a ve pano enine uyarlanmış). Adlar aynı kalır.
for blok, kapi, en, mentese in [("100'LÜK 125'LİK KAPILI PANO(90'LIK)", 90, 125.5, "SAG"),
                                 ("100'LÜK 116.25'LİK KAPILI PANO(90'LIK) [SOL]", 90, 116.25, "SOL")]:
    if sablon_kapili_pano(blok, kapi, en, mentese): print("şablon kapılı pano uygulandı:", blok)
H.add_text("GİRİŞ 90 · Şablon 2024 kapılı pano çizimi (Lokman 13:02); kanat ve kasa şablondan, 90'a uyarlandı", height=5,
           dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((763.0 - 150, 445.0 + 17.75 - 12))

# 4d) Köşeler 100×100 kutu profil (Lokman 12:09 ve 13:13 "köşeler 100*100 kutu profil olacak demiştim"): Motor'un 5×10 köşe
#     parçası yerine Güncel Şablon 2024'ün "100X100 DIŞ KÖŞE DİREĞİ" bloğu (10×10 kırmızı kutu + pano başlangıç çıkıntıları);
#     blok köşe yönüne göre aynalanır (şablon bloğunun varsayılan yönü: kutu (0,2.5)–(10,12.5), çıkıntılar aşağı ve sağa).
ESKI_KOSE, SABLON_KOSE = "100X100 SÜREKLİ DIŞ KÖŞE DİREĞİ (5320)", "100X100 DIŞ KÖŞE DİREĞİ"
if kut is not None and SABLON_KOSE in kut.blocks and ESKI_KOSE in hedef.blocks:
    i3 = Importer(kut, hedef); i3.import_block(SABLON_KOSE); i3.finalize()
    hedef.blocks.get(SABLON_KOSE).base_point = (0, 0, 0)
    KOSELER = {(0.0, 0.0): (0.0, 12.5, 1, -1),            # ön-sol: duvarlar yukarı ve sağa
               (0.0, 696.0): (0.0, 693.5, 1, 1),          # arka-sol: aşağı ve sağa
               (758.0, 696.0): (763.0, 693.5, -1, 1),     # arka-sağ: aşağı ve sola
               (758.0, 126.25): (763.0, 138.75, -1, -1),  # sağ duvar – balkon arka duvarı: yukarı ve sola
               (439.25, 126.25): (439.25, 123.75, 1, 1),  # salon sağ duvarı – balkon arka duvarı: aşağı ve sağa
               (444.25, 0.0): (449.25, 12.5, -1, -1)}     # salon sağ duvarı – ön duvar: yukarı ve sola
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
H.add_text("ORTAK: 100X100 DIŞ KÖŞE DİREĞİ (şablon bloğu; kutu profil, sürekli iki kat boyu 5320 R02) — kat kat sayılmaz: 6 köşe → 6 adet", height=5.5,
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
L.append("| ORTAK · 100X100 DIŞ KÖŞE DİREĞİ (kutu profil, sürekli iki kat boyu 5320; Lokman 12:09/13:13) | — | — | 6 | var (şablon bloğu; '2X100X100 DIŞ KÖŞE DİREĞİ' varyantı da var) |")
L.append("\nMotor'da olmayıp çizimde elle olanlar: merdiven kutusu ve merdiven (Lokman'ın planı bire bir, 13:00: iç 200 × 250, çıkma 125, "
         "çift kollu U kol 100, 5+6+5 = 16 rıht; katman MERDIVEN/MERDIVEN_DUVAR, blok değil), balkon taşması 30 (kesik çizgi). "
         "Dış kapılı panoların çizimi Güncel Şablon 2024'ün kapılı pano bloğundan (13:02); iç kapılar henüz Motor'un Astra sembolü.")
(CIKTI / "Portman_IE22-CK01_CIFT_KAT_malzeme_karti.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("kart yazıldı;", len(satirlar), "satır")
