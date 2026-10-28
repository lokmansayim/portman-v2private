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
    "100'LÜK 125'LİK KAPILI PANO(80'LİK)", "100'LÜK 117'LİK PANO", "60X60 3 LÜ H BAĞLANTI DİREĞİ",
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
                 ("KESIT_CATI", 1), ("KOSE_SUREKLI_100", 6), ("MALZEME_KARTI", 7), ("SABLON_KARTI", 9)]:
    hedef.layers.add(ad, color=renk)
if "DASHED" not in hedef.linetypes:
    hedef.linetypes.add("DASHED", pattern=[20.0, 12.5, -7.5])

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
                try: td.dxf.set(k, v)
                except Exception as ex: print("dimstyle alanı atlandı", k, v, str(ex)[:60])
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
    # merdiven çıkması ve balkon taşması (Motor'da yok) — konumlar İş Emri'nden, y önden
    H.add_lwpolyline([(dx+318.75, 706), (dx+569.75, 706), (dx+569.75, 831.5), (dx+318.75, 831.5), (dx+318.75, 706)],
                     dxfattribs={"layer": "CIFT_KAT_NOT", "linetype": "DASHED"})
    H.add_text("MERDİVEN ÇIKMASI 125,5 (Motor'da yok · Soru 2/5)", height=6, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((dx+322, 838))
    H.add_lwpolyline([(dx+444.25, 0), (dx+763, 0), (dx+763, -30), (dx+444.25, -30), (dx+444.25, 0)],
                     dxfattribs={"layer": "CIFT_KAT_NOT", "linetype": "DASHED"})
    H.add_text("BALKON TAŞMASI 30 (Motor'da yok · Soru 7)", height=6, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((dx+446, -44))

# 4b) Giriş kapısı (Lokman 28.10 12:34, Soru 1): sağ cephe, WC HOLÜ, 90'lık, içeri açılır. Motor bunu kendisi çiziyor:
#     BOM_D18_1255p0_DIS_K02 @ (763, 445) rot 90, iç sembol BOM_K03_DIS_KAPI_ACIKLIK900 (sınır kutusu 668,8–764,1 × 445–570,5).
#     12:45'te "Motor sembolü çizmedi (bulgu 7)" diye elle kırmızı kapı çizilmişti; yanlıştı — ad değiştirme iç sembolü bozduğu için
#     görünmüyordu (A023'te düzeltildi). Elle kapı 13:05'te kaldırıldı; yalnız kısa bir not kalır.
H.add_text("GİRİŞ 90 (Lokman 28.10 · Motor çizdi: BOM_D18 K02)", height=5, dxfattribs={"layer": "CIFT_KAT_NOT"}).set_placement((763.0 - 150, 445.0 + 17.75 - 12))

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
H.add_text("ORTAK: 100X100 SÜREKLİ DIŞ KÖŞE DİREĞİ (5320) — kat kat sayılmaz, bir kez: planda 6 köşe (L gövde) → 6 adet", height=5.5,
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
L.append("| ORTAK · 100X100 SÜREKLİ DIŞ KÖŞE DİREĞİ (5320) | — | — | 6 | yeni (R02 CK-B01) |")
L.append("\nMotor'da olmayıp çizimde kesik çizgiyle işaretlenenler: merdiven çıkması (arkaya 125,5), balkon taşması (30). Merdivenin kendisi: Soru 3.")
(CIKTI / "Portman_IE22-CK01_CIFT_KAT_malzeme_karti.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("kart yazıldı;", len(satirlar), "satır")
