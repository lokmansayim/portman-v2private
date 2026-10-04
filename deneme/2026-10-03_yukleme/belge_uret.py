#!/usr/bin/env python3
"""Şartname belgesini (`docs/sartname/yukleme_listesi_yontemi.md`) hesap çıktılarından üretir.

Belgedeki tablolar ve sayılar `sonuc/` altındaki çıktılardan okunur; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Metin bu dosyanın içindedir: kural ya da kaynak değişince burada düzeltilir, belge yeniden üretilir.

Kullanım:
    python belge_uret.py --zaman "4 Ekim 2026 02:00"
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from motor_formul import BESIK_10, SABLON, motor_kaplama

BURADA = Path(__file__).resolve().parent
S = BURADA / "sonuc"
BELGE = BURADA.parents[1] / "docs" / "sartname" / "yukleme_listesi_yontemi.md"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--zaman", required=True, help="belgenin başındaki tarih ve saat")
A = ap.parse_args()
T = (S / "tablolar.md").read_text(encoding="utf-8")
K = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))


def oku(ad: str) -> dict:
    return json.loads((S / ad).read_text(encoding="utf-8"))


def tr(x, n=0) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def bolum(baslik: str) -> str:
    a = T.index("## " + baslik)
    b = T.find("\n## ", a + 3)
    govde = T[a:(b if b != -1 else len(T))]
    return "\n".join(govde.split("\n")[2:]).strip()


def satir(v: dict, kalem: str) -> dict:
    return next(s for s in v["satirlar"] if s["kalem"] == kalem)


def adet(v: dict, kalem: str):
    return satir(v, kalem)["adet"]


def kg(v: dict, kalem: str) -> float:
    return satir(v, kalem)["kg"]


baz, d140, yb = oku("C8201_yukleme_taslak.json"), oku("C8201_dis_karkas_140_yukleme_taslak.json"), oku("C8201_yontem_B.json")
gb, g140 = oku("C8201_girdi.json"), oku("C8201_dis_karkas_140_girdi.json")
TOPLAM = "Toplam (adedi ve kg'ı bilinenler)"
tutmayan = bolum("Adedi tutmayan kalemler")
tam = bolum("Üç gerçek listeyle karşılaştırma")
ozet = next(x for x in tam.split("\n") if x.startswith("Özet:"))
ck = [x for x in tam.split("\n") if x.startswith(("| Çelik (kg)", "| Dış duvar |", "| İç duvar |", "| Duvar toplamı |", "| Kiriş ve kolon |", "| Çatı |", "| Toplam |"))]
celik_kg = "\n".join([ck[0], "|---|---|---|---|"] + ck[1:])
taslak = bolum("Ç8201 taslak: baz ve dış 140")
kaplama = bolum("Ç8201: çatı kaplaması seçenekleri")
kosebent = bolum("Köşebent: mühendisin formülü")
elektrik_sinama = bolum("Elektrik kuralının sınaması (105 m² liste)")
elektrik_oda = bolum("Ç8201: elektrik, oda oda")

ozetler = [oku(f"ornek_{n}m2_karsilastirma.json")["karsilastirma_ozeti"] for n in (90, 62, 105)]
kars_top, kars_ayni = sum(x["karsilastirilan"] for x in ozetler), sum(x["ayni"] for x in ozetler)
kg_m = K["celik"]["duvar_kg_m"]["deger"]
dis_boy, ic_boy, ic_boy_140 = gb["celik"]["dis"]["boy_m"], gb["celik"]["ic"]["boy_m"], g140["celik"]["ic"]["boy_m"]
kb = baz["ara"]["kosebent"]
ot = gb["osb_takviye"]
osb_s = satir(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)")
tp, cp = satir(baz, "Tavan paneli (makas arası)"), satir(baz, "Çatı paneli (makas üstü, sırt 80 mm)")
dz = baz["ara"]["kirma_dizilim"]     # kırma çatıda kaplama dizilimi (baz kaplama)
dizilim_tablo = bolum("Kırma çatıda kaplama dizilimi")
# Excel motorunun köşebent formülü, Ç8201'in ölçüleriyle (kapalı kısım): (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5
uzun, kisa = gb["kapali_olcu_m"]
motor_kosebent = math.ceil((uzun * 6 + kisa * 6 + 9 * 4 * 2.7) / 2.5 - 1e-9)
pk_tavan, pk_cati = K["celik"]["tavan_paneli"]["deger"], K["celik"]["cati_paneli"]["deger"]
oturum = gb["celik"]["cati"]["oturum_m2"]
dz_H = min(gb["cati"]["plan_m"]) / 2 * math.sqrt(1 + gb["cati"]["egim"] ** 2)     # eğimli boy (m)
BAZ_KAPLAMA = {"tek_kat_panel": "Tek kat panel", "sandvic_panel": "Sandviç panel"}[K["baz_paket_cati_kaplamasi"]["deger"]]
kaplama_s = satir(baz, BAZ_KAPLAMA)


def secenek(kod: str, kalem: str) -> dict:
    return satir(oku(f"C8201_kaplama_{kod}.json"), kalem)


sandvic_s, trapez_s, kiremit_s = secenek("sandvic_panel", "Sandviç panel"), secenek("trapez_sac", "Trapez sac"), secenek("osb_kiremit", "Metal kiremit (kiremit desen sac)")
k62 = oku("ornek_62m2_karsilastirma.json")["karsilastirma"]["Sandviç panel"]
dis140_ince = dis_boy * kg_m["dis"]["140x45x0,8"]      # 0,8 mm olsaydı (3 Ekim varsayımı)
ic140_ince = ic_boy_140 * kg_m["ic"]["80x45x0,8"]
bant_s = satir(baz, "Mahya bandı")
# mahya bandının 01:24 uygulaması: mahya uzunluğu ÷ rulo boyu (üçüncü cevaplarla yerini parça adedi × parça boyu aldı)
onceki_bant = math.ceil(gb["cati"]["mahya_hatti_m"] / K["mahya_bandi"]["deger"]["rulo_m"] - 1e-9)
boardex_s = satir(baz, "Dış cephe Boardex")
boardex_15 = math.ceil(boardex_s["olcu"] * 1.15 / K["levha_m2"]["boardex"]["deger"] - 1e-9)      # önceki zayiatla (%15)
zb = K["zayiat"]["boardex"]["deger"]
tasma_cm = K["cati_kaplama_tasma_m"]["deger"] * 100
DZ_KR = K["kirma_cati_dizilim"]["deger"]
kesim_mm = DZ_KR["kesim_payi_m"] * 1000
dis_kose = sum(o["dis_kose"] for o in gb["odalar"])
boyle = [oku(f"ornek_{n}m2_karsilastirma.json")["karsilastirma"]["Dış cephe Boardex"] for n in (90, 62, 105)]     # Boardex: hesap / liste
YAYIMLANAN = {"kosebent": 51, "boardex": 33, "mahya_bandi": 3, "panel_boyu_mm": 4300, "sandvic": 24, "trapez": 30}      # 4 Ekim 02:58 sürümü (commit 61d1996)


def dz_oku(kod: str) -> dict:
    return oku(f"C8201_kaplama_{kod}.json")["ara"]["kirma_dizilim"]


dz_s, dz_t, dz_k = dz_oku("sandvic_panel"), dz_oku("trapez_sac"), dz_oku("osb_kiremit")
assert dz["tasma_cm"] == tasma_cm and dz["kesim_payi_mm"] == kesim_mm, "belge taşmayı ve kesim payını kuraldaki değerle anlatıyor"
assert not dz_k["artan_parca_karsi_yuzde"] and dz["artan_parca_karsi_yuzde"], "belge: artan parça yalnız kiremit desen sacda kullanılmaz"


def aralik(den: dict) -> str:
    a, b = min(den.values()), max(den.values())
    return str(a) if a == b else f"{a}–{b}"


def dizilim_okuma(ad: str, z: dict) -> str:
    """Bir kaplamanın dizilim sonucunu ve neye duyarlı olduğunu hesap çıktısından yazar."""
    den = z["baslangica_gore"]
    p = [f"{z['adet']} adet ({z['tam_boy']} tam boy + {z['kesilen']} kesilen)"]
    if len(set(den.values())) > 1:
        p.append(f"dizilim {z['baslangic_adi']} başlıyor (en az paneli veren başlangıç); her yüzde sol köşeden başlanırsa {den['sol']}, altı başlangıçla {aralik(den)}")
    else:
        p.append("altı başlangıcın hepsinde aynı")
    if z["paysiz_adet"] != z["adet"] or z["bir_cm_payla_adet"] != z["adet"]:
        p.append(f"kesim payı sıfır alınırsa {z['paysiz_adet']}, 1 cm alınırsa {z['bir_cm_payla_adet']}")
    else:
        p.append("kesim payı sıfır da olsa 1 cm de olsa aynı")
    if not z["artan_parca_karsi_yuzde"]:
        p.append("artan parça kullanılmıyor (desen ters gelir: mühendis, 4 Ekim 12:14)")
    return f"- **{ad}.** " + "; ".join(p) + "."


def onceki_kural(kapatma: float) -> int:
    """Açılımdan önceki kural: yüzey × 1,10 ÷ (panel boyu × kapatma genişliği)."""
    return math.ceil(gb["cati"]["yuzey_m2"] * 1.10 / (gb["cati"]["panel_boyu_m"] * kapatma) - 1e-9)


# Excel motorunun kaplama formülü (`motor_formul.py`): şablondaki kayıtlı örnek, mühendisin 10 × 10 m beşik çatısı ve Ç8201'in ölçüleri.
# Ç8201'de K10 kapalı kısmın uzun kenarı, K11 kısa kenar, K17 verandanın kısa kenarı.
mk_ornek, mk_besik = SABLON, BESIK_10
mk_c = motor_kaplama(uzun, kisa, gb["dis_olcu_m"][0] - uzun, "kirma")
assert mk_c["sac_boyu_mm"] == round(gb["cati"]["panel_boyu_m"] * 1000), "belge: motorun sac boyu listedeki panel boyuyla aynı"

D = f"""# Çelik yükleme listesi: yöntem ve taslak (3–4 Ekim 2026)

Son güncelleme: {A.zaman}. Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar ve sayılar hesap çıktılarından üretilir (`belge_uret.py`; tablolar `sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda), 4 Ekim 01:24'teki düzeltmesi (tavan ve çatı panelinin ağırlığı), 4 Ekim 01:42'deki düzeltmesi (baz kaplama; kırma çatıda kaplama adedinin çatı açılımından bulunması) ve önceki kurallar.
2. **Mühendisin cevapları.** PortatifEv'in inşaat mühendisi Ubeydullah'ın üç tur cevabı: 3 Ekim 14:50 sürümündeki yedi soruya (Lokman 3 Ekim 18:14'te iletti), 19:12 sürümündeki yedi soruya (Lokman 4 Ekim 01:24'te iletti) ve 4 Ekim 02:58 sürümündeki on iki soruya (Lokman 4 Ekim 12:14'te iletti). Üçü de aşağıda. Kurallarda durumu `muhendis`. İkinci turun iki cevabını (baz kaplama; kırma çatıda kaplama adedi) Lokman 01:42'de düzeltti. Üçüncü turun mesajında cevapların kimden olduğu yazmıyor; 11. cevaptaki anlatım mühendisin olduğu için on iki cevap da mühendisin sayıldı.
3. **Gerçek yükleme listeleri.** Lokman'ın bağladığı klasördeki çalışma kitapları. Üçü hesap sayfalarıyla okundu. Üçünde de çatı yöntem B ile (tavan omegası, aşık, saçak sacı) hazırlanmış: PortatifEv bugüne kadar çelikte de bu yöntemi uygulamış. Şimdi baz alınan yöntem A için karşılaştırılacak gerçek liste yok.
   - **90 m²**, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (30 Eylül 2025).
   - **62 m²**, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (19 Eylül 2025). Ç8201'e en yakın örnek.
   - **105 m²**, beşik + cumba çatı, tek kat panel, dış karkas 140 mm (dosya tarihi 26 Kasım 2025; 11 Kasım tarihli önceki sürümüne de bakıldı).
4. **Excel hesaplama motoru** (`CTKBF V1.1`). Lokman, 13:27: "biz Excel'de hesaplama motoru kullanırken…". Sayfaları: müşteri talebi (girdiler), proje detayları, dış ve iç duvar tonajı, çatı tonajı, çatı kaplama malzemesi, pencere, malzemeler (formüller), notlar. Buradan çelik birim ağırlıkları ile listede elle yazılan kalemlerin formülleri alındı. Fiyatlar alınmadı.
5. **Mühendisin 10 × 10 m çatı metrajı** (aynı klasörde; beşik ve dört omuz, yöntem B). Kuralları sınamak için kullanıldı; fiyatlar alınmadı.

Bayi, müşteri ve öteki personel adları alınmadı. Çalışma kitapları depoda değil; Lokman'ın Mac'inde.

## Lokman'ın cevapları (3 Ekim 13:27) ve uygulanışı

| # | Konu | Cevap (özet) | Uygulama |
|---|---|---|---|
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "şimdilik" notuyla (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"). Tavan ve çatı paneli 100 m² için verilen ağırlıktan, alana oranla (ağırlıklar Lokman'ın 4 Ekim düzeltmesiyle). |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Baz pakette tek kat panel (Lokman, 4 Ekim 01:42); motordaki altı kaplama da hesaplanıyor. |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | Hesap değişmedi; kural teyitli. |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Yerini mühendisin plandan hesaplayan formülü aldı (18:14): Ç8201'de {adet(baz, "Köşebent")} (m² ÷ 2,5 ile 33'tü; veranda tavanı eklenmeden önce {YAYIMLANAN["kosebent"]}). m² ÷ 2,5 kurallarda yedek olarak duruyor. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. Mühendis: iniş plana bakarak yerleştirilir (18:14); elle yerleştirilirse o sayı kullanılır. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | Mahya (L 2800) ÷ 2,5 → 11. Yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım). Dere sayılmadı: 20 cm'de kaldı (soru). |
| 8 | Saçak altı | İki yöntem birlikte kullanılmaz; saçak sacı varsa Boardex kaplanmaz. Ç8201 Boardex kaplamalı, çatı ve tavan panelli. | Baz listede saçak sacı yok; saçaklar için Boardex var. Saçak yüzü de Boardex; saçak omegası yok (mühendis, 18:14). |
| 9 | İç duvarda OSB | İçlerde OSB yoksa mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye gönderilen ürün; "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". | Mühendisin cevabıyla (18:14): yalnız dolap ve TV ünitesi gelen duvarlar. Ç8201: {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha (önce bütün Yaşam Alanı: 42,5 m², 15 levha). Duvar seçimini mühendis doğruladı (4 Ekim). |
| 10 | İç kapı | Boşluk en 90, yükseklik 214; kasa sağda, solda, üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke; kanat 200'e düşer. | Dört iç kapı da 90 × 214 (banyo dahil); kanat 200. Kanat eni 80: listelerdeki "80'lik kanat"tan ve 90 − 2 × 5'ten. |
| 11 | Vida, boya, elektrik, tesisat | Bütün paketlerde var; bayilerle paylaşılan katalog ve fiyat listelerinde de. Bayi kuralı olarak ele alınacak (örnek: bir bayi için çelikte standart ne, bir başkası için prefabrikte standart ne); canlıda bayi numaraları birincil anahtar, liste mesajı atana göre. | Dört grup varsayılan olarak listede; bayi kuralıyla kapatılır. |

## Mühendisin ilk cevapları (Lokman 3 Ekim 18:14'te iletti) ve uygulanışı

Sorular 14:50 sürümündeki yedi soruydu. "Denetim" sütunu, cevabın elimizdeki kaynaklarla karşılaştırmasıdır. Sonradan değişenler "Uygulama" sütununda belirtildi.

| # | Soru | Cevap | Denetim | Uygulama |
|---|---|---|---|---|
| 1 | Et kalınlığı neye göre seçiliyor? | Duvarların kg/m değerleri: 80 × 0,8 iç 13; 80 × 1,2 dış 20,33 ve iç 19,75; 140 × 0,8 dış 18,20 ve iç 12,06; 140 × 1,2 dış 29,04. "140x0,8 duvarı 80x1,2 duvarına göre daha hafif olduğunu görebiliriz." | Değerler motorun duvar tonajı sayfasındakilerle aynı. Seçim ölçütü cevapta yok. 12,06 tek bir projenin 80 × 0,8 iç duvarı; 13,00 iki projenin ortalaması. Motorun verisinde 140 × 0,8 dış duvar yalnız iki katlı iki projenin üst katında; tek katlı 140'lık örnekte (55 m²) dış duvar 1,2 mm. | Birim ağırlıklar değişmedi; iç duvar 80 × 0,8 için 13,00. Seçim ölçütü ikinci cevaplarla geldi (aşağıda): tek katta ve zemin katta 1,2 mm. |
| 2 | Tavan ve çatı panelinin ölçüsü, adedi, kg'ı? Saçak omegası gerekiyor mu? Saçak yüzü Boardex mi? | Motor çatıları dört grupta (beşik, beşik + cumba, beşik + 2 cumba, dört omuz) ortalama ağırlıkla hesaplıyor; çatıdaki Boardex kaplaması motorda henüz hesaplanmıyor. "10 m x 10 m (100 m2) bir binada tavan paneli koyduğumuzu düşünürsek (8 adet) tavan paneli ağırlığı 429,83 kg, çatı paneli (12 parça) koyduğumuzda 561,6 kg geliyor. Saçak omegası gerekmiyor. Saçak yüzü de boardex ile kaplanıyor." | 429,83 ve 561,6 okunan çalışma kitaplarında bulunamadı; mühendisin beyanı olarak kayıtlı. Hangi çatı tipi, saçak ve eğim için olduğu yazılmadı. Motorda "saçaklar için Boardex" satırı gerçekten 0. | kg ve adet çatının örttüğü oturum alanına oranlandı: o gün Ç8201'de tavan paneli 353 kg, çatı paneli 461 kg; çelik toplamı 1902 → 2716 kg. Ağırlıkları Lokman 4 Ekim'de düzeltti (aşağıda). Saçak omegası satırı kalktı. Saçak yüzü için Boardex teyitli. |
| 3 | Baz pakette hangi çatı kaplaması var? | Motordaki kaplamalar: OSB + membran + shingle; OSB + nem bariyeri + trapez sac; trapez sac; tek kat panel; sandviç panel; OSB + membran + metal kiremit. | Motorun seçenek listesi aynı. Baz paket cevapta yok. Motorun trapez sac ve metal kiremit adedi formülü hatalı görünüyor (aşağıda "Excel motoruyla ilgili gözlemler"). | Altı seçenek hesaplanıyor. Lokman'ın "OSB + nem bariyeri + kiremit desen sac"ı motorun "OSB + membran + metal kiremit"iyle eşlendi (motor o seçenekte nem bariyeri hesaplıyor, membran hesaplamıyor). Baz paket: mühendis ikinci cevaplarda sandviç panel yazdı; Lokman tek kat panel diye düzeltti (4 Ekim 01:42). |
| 4 | OSB takviyesi bütün oda mı, yalnız o duvarlar mı? | "Bütün oda değil sadece dolap ve TV ünitesi gelen duvar metrajı alınır." | Gerçek listelerdeki alanlar (35 ve 39 m²) bütün odadan (72 ve 112 m²) küçük: cevapla aynı yönde. | Modelin tanımına dolap ve TV duvarları yazılır. Ç8201'de katalog görselinden üç duvar: {"; ".join(f"{x['duvar_adi']} {tr(x['boy_m'], 2)} m ({x['neden']})" for x in ot["duvarlar"])}. Net {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha. Duvar seçimini mühendis ikinci cevaplarda doğruladı. |
| 5 | Köşebent: m² ÷ 2,5 gerçek listelerin yarısını veriyor. | "Köşebent hesabı bina içerisinde bulunan bütün odaların tavan çevresi uzunluğu ile bütün oda iç köşe uzunlukları (standart kat yüksekliğimiz 2,7 metre alınır) toplamının 2,5 metreye bölünmesiyle bulunur." | Motordaki formül aynı yapıda ama plansız: (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5. Üç gerçek listede iç köşe sayısı bilinmiyor (planları yok); aşağıdaki tablo. | Ç8201 (planından): ({tr(kb["tavan_cevresi_m"], 2)} + veranda tavanı {tr(kb["veranda_tavan_cevresi_m"], 2)} + {kb["ic_kose"]} × 2,7) ÷ 2,5 → {adet(baz, "Köşebent")}. Yalnız iç köşeler sayılır. Veranda tavanının çevresi üçüncü cevaplarla eklendi (önce {YAYIMLANAN["kosebent"]}). |
| 6 | İniş sayısı iki listede kuraldan bir fazla. | "Dere inişi plana bakarak yerleştirilmesi doğru olur. Normalde düz bir saçakta ortalama 5 metrede bir dere inişi yazılır." | Mühendisin 10 × 10 m metrajında dört omuz çatıda 8, beşik çatıda 6 iniş var: Lokman'ın kuralı ikisini de veriyor. Motorun formülü farklı (dere adedi ÷ 5 + 6). | Kural değişmedi (Ç8201: {adet(baz, "Dere iniş borusu")}). Tanımda iniş yerleri elle verilirse (`cati.inis_noktalari`) o sayı kullanılır. Listelerdeki 7'ler plana göre yerleşimle açıklanıyor. |
| 7 | Elektrik sayıları paftadan mı, oda başına kuraldan mı? | Oda başına kural; "%75 lik bir doğruluk payı olacağı düşünülerek" (aşağıda). | 105 m² listenin pafta sayımıyla sınandı (aşağıda): kural 41, sayım 48 parça. | Pafta sayımı varsa o; yoksa kural. Ç8201: duy {adet(baz, "Tijli duy")}, glop {adet(baz, "Yuvarlak glop")}, tekli anahtar {adet(baz, "Tekli anahtar")}, çiftli anahtar {adet(baz, "Çiftli anahtar")}, tekli priz {adet(baz, "Tekli priz")}, çiftli priz {adet(baz, "Çiftli priz")}, uydu prizi {adet(baz, "Uydu prizi")}, sigorta {adet(baz, "W otomat (sigorta)")}. Yaşam Alanı'nda salon ve mutfak kuralları birlikte uygulandı (mühendis ikinci cevaplarda doğruladı). |

### Elektrik kuralı (mühendis)

| Oda | Duy | Glop | Tekli anahtar | Çiftli anahtar | Tekli priz | Çiftli priz | Uydu prizi |
|---|---|---|---|---|---|---|---|
| Yatak odası | 1 | | 1 | | 3 | | |
| Banyo | | 1 | 1 | | 2 | | |
| Salon | 2 | | | 1 | 3 | 1 | 1 |
| Mutfak | 1 | | 1 | | 5 | 1 | |
| Hol | 1 | | 1 | | | | |
| Veranda | | 2 | | 1 | | | |

- Her duy ve glop için bir ampul.
- Bina başına (cevapta holün altında): 12'li sigorta kutusu 1, sigorta 9, besleme kablosu 5 m, zil 1, kaçak akım rölesi 1; salonda 25 m uydu kablosu.
- Buat kasa = anahtar + priz + oda sayısı.
- 3 × 2,5 kablo = sigorta adedi × sigortadan evin en uzak mesafesi + (tekli priz + 2 × çiftli priz) × 2. 2 × 1,5 kablo = sigorta adedi × en uzak mesafe + (tekli anahtar + 2 × çiftli anahtar) × 2.
- Okuma: cevaptaki "anahtar" tekli anahtar, "priz" tekli priz sayıldı. "En uzak mesafe" motordaki gibi kapalı kısmın köşegeni alındı (Ç8201: {tr((uzun ** 2 + kisa ** 2) ** 0.5, 2)} m); motor 3 × 2,5 kabloda uydu prizini de sayıyor, hesap öyle yapıldı (fark 2 m). Buat için oda sayısı planın mahal sayısı alındı (Ç8201: {gb["oda_sayisi"]}). Mühendis üçüncü cevaplarda ikisini de teyit etti: "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli."

Ç8201'de oda oda:

{elektrik_oda}

Kuralın sınaması: 105 m² gerçek listede pafta sayımı var. O listenin odalarına kural uygulanınca ("oda" yatak odası sayıldı; veranda bilgisi yok):

{elektrik_sinama}

Toplamda kural sayımın %85'ini veriyor; kalem kalem farklar büyük (çiftli anahtar 1 / 5, glop 2 / 4). Bu, mühendisin söylediği %75'lik doğruluk payıyla uyumlu. Tek liste; kanıt sayılmaz.

### Köşebent kuralının gerçek listelerle karşılaştırması

{kosebent}

Listelerdeki adetler, her odada ortalama 6–7 iç köşe varsa formülle çıkar. Salon, mutfak ve holün tek mahal olduğu planlarda bu olabilir; planlar elde olmadığı için sınanamadı. Ç8201'in planı sade: beş mahal, {kb["ic_kose"]} iç köşe. Veranda tavanının çevresi (üçüncü cevaplar) örneklerde bilinmediği için bu tabloya eklenmedi; verandalı projede eklenince fark azalır.

## Lokman'ın düzeltmesi ve mühendisin ikinci cevapları (4 Ekim 01:24) ve uygulanışı

**Düzeltme (Lokman).** 100 m² için "Tavan paneli ağırlık: 354,84 kg · Çatı paneli ağırlık: 440,32 kg"; "yine 82 m² ye oranlama yapabilirsin". Önceki değerler 429,83 ve 561,6 kg'dı. Ç8201'de (oturum {tr(oturum, 2)} m²) tavan paneli 353 → {tr(tp["kg"])} kg, çatı paneli 461 → {tr(cp["kg"])} kg; çelik toplamı 2716 → {tr(kg(baz, TOPLAM))} kg. Oranlama böylece Lokman'ın onayıyla. Adetler (100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]}) mühendisin ilk cevabından; düzeltmede adet verilmedi.

Sorular 19:12 sürümündeki yedi soruydu. 1. ve 6. cevabı Lokman 01:42'de düzeltti; öteki beşi geçerli.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Baz pakette altı seçenekten hangi çatı kaplaması var? | "Baz paket sandviç panel olarak al." | **Lokman düzeltti (01:42):** baz kaplama tek kat panel. Sandviç panel öteki dört kaplamayla birlikte seçenek olarak hesaplanıyor. |
| 2 | Tek katta dış 140'lık duvarın et kalınlığı 0,8 mi, 1,2 mi? | Tek katlı binada zemin kattaki çelik 140x45x12 ya da 80x45x12. İki katlı binada zemin kat yine böyle; 1. kat 140x45x0,8 ya da 80x45x0,8. İki katlıda "1. Katta büyük pencereler varsa mesela 200 cm ve daha geniş pencere varsa ozaman o duvarı 1,2 mm et kalınlığında alırız. Genelde 1. Katta 1 veya 2 adet duvar bu şekilde 1,2 mm et kalınlığı olacak şekilde tasarlanıyor." | Okuma: cevaptaki "12 mm" ve "8 mm", 1,2 ve 0,8 mm'dir. Tek katta ve zemin katta dış ve iç duvarlar 1,2 mm; üst katta 0,8 mm. Dış 140 seçeneği: dış 140 × 1,2 ve iç 80 × 1,2 → çelik {tr(kg(d140, TOPLAM))} kg, baz paketten {tr(kg(d140, TOPLAM) - kg(baz, TOPLAM))} kg ağır (3 Ekim'de 0,8 mm varsayılmış, daha hafif çıkmıştı). Üst katta geniş pencereli duvar kuralı kayıtlı; çift kat modeli gelince uygulanacak. 2025 tarihli iki tek katlı listede dış 140'lık duvarların çoğu 0,8 mm'di: kuralla uyuşmuyor. Mühendis üçüncü cevaplarda kuralı yineledi: tek katta 1,2 mm. |
| 3 | OSB takviyesi için seçilen üç duvar doğru mu? | "Evet doğru yeri almışsın. Ancak bunun yeri en doğru şekilde genel mimari planda mutfak tezgahı ve TV ünitesi yeri gösterilirse o kısımlar alınarak bulunabilir." | Seçim teyitli; satırdaki "teyit bekliyor" notu kalktı. Kural: yer, mimari plandaki tezgâh ve TV ünitesi yerinden alınır. "O kısımlar" sözü duvarın yalnız o bölümü diye de okunabiliyordu; üçüncü cevaplarla kapandı: "Duvarın tamamını al." |
| 4 | Yaşam Alanı'nda salon ve mutfak kuralları birlikte mi uygulanır? | "Evet doğru ikisini de uygulamamız gerekiyor. Çünkü mutfak eşyaları ayrı, salon eşyaları ayrı." | Teyitli; hesap değişmedi. |
| 5 | Makas ve kiriş ölçüsü gelene kadar çatı çeliği motorun ortalamasıyla; panel adedi alana oranlandı. | "Tamamdır." | Çatı çeliği motorun ortalamasıyla kalıyor (makas ölçüsü verilince değişecek; üçüncü cevaplar: "şimdilik Excel hesaplama motoruna uy"). Panel adedi alana oranlanıyor. |
| 6 | Kırma çatıda kaplama adedi yerleşimle mi bulunsun? | "Kırma çatıda çatı kaplama malzemesi hesabı sağlıklı olarak autocad üzerinden hesaplanarak yapılması daha sağlıklı. Ancak yüzeysel olarak çatı yüzey alanı m2 belirtilerek (%10 luk pay alınabilir) bu m2 olacak şekilde çatı kaplama malzemesi sipariş edilmeli şeklinde not edilebilir." | **Lokman düzeltti (01:42):** adet AutoCAD'e bırakılmaz; çatı açılımından ve dizilimden çıkar (aşağıda). %10 pay ve "sipariş bu m² olacak şekilde" notu listeden kalktı; pay kurallarda kayıt olarak duruyor. |
| 7 | Çatı müdahale kapağı ve mahya bandı listeye girsin mi? | "Çatı müdahale kapağı müşterinin talebine göre ekleniyor. Herhangi bir detay belirtilmemişse yani standart bir pakette çatı müdahale kapağı göndermiyoruz. Mahya bandını ekle." | Mahya bandı eklendi. O gün mahya uzunluğundan hesaplandı (Ç8201'de {onceki_bant} rulo); üçüncü cevaplardaki formülle {bant_s["adet"]} rulo. Çatı müdahale kapağı standart listede yok; müşteri isterse eklenir (`--mudahale-kapagi`; kat adedi kadar). |

## Lokman'ın ikinci düzeltmesi (4 Ekim 01:42): baz kaplama ve çatı açılımı

Lokman: "mühendis 2 cevapta hata yapmış onları düzeltmem gerekiyor".

1. **Baz kaplama.** "çatıda baz model Tek Kat panel olarak geçiyor". Uygulama: baz paketin çatı kaplaması tek kat panel (87 cm kapatır); Ç8201'in tanımı ve listesi buna göre. Sandviç panel seçenek.
2. **Kırma çatıda kaplama adedi.** "biz AutoCAD bulaşmak istemiyoruz"; "sen eğime göre 82 m² olduğu gibi çatıyı çizip sonra çatıyı açman lazım zarfı açar gibi yüzeye dizilimini bulmak için". "çatı formunun çapraz kesimleri diğer tarafa kullanabilirsin": sol taraftaki üçgende kullanılan panel sağ tarafa aynı açıyla; ön taraftaki yamuktan çıkan açılı kesilmiş parçalar arka taraftaki aynı biçimdeki açılı yere.

Uygulama (`deneme/2026-10-03_yukleme/cati_acilim.py`). Taşma, kesim payı ve başlangıç seçimi mühendisin üçüncü cevaplarından sonra eklendi (aşağıdaki bölüm):

- **Açılım.** Çatının dört yüzü gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ). Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Ç8201'de {tr(dz_H * 100, 1)} cm; saçaklar {tr(gb["cati"]["plan_m"][0] * 100)} ve {tr(gb["cati"]["plan_m"][1] * 100)} cm, mahya {tr((gb["cati"]["plan_m"][0] - gb["cati"]["plan_m"][1]) * 100)} cm. Kırma çizgisi açılımda dört yüzde de aynı açıdadır.
- **Dizilim.** Her yüz, saçağa dik, kaplamanın kapattığı genişlikte şeritlere bölünür. Mahyanın altındaki şeritler tam boydur; kırmaya gelen şeritler çapraz kesilir.
- **Taşma** (mühendis, 4 Ekim 12:14). Kaplama saçaktan {tr(tasma_cm)} cm dışarı uzatılır. Panel boyu = eğimli boy + {tr(tasma_cm)} cm, mm'ye yukarı: Ç8201'de L {round(gb["cati"]["panel_boyu_m"] * 1000)}. Açılımda her parçanın boyu {tr(tasma_cm)} cm artar. Excel motorundaki sac boyu da aynı: eğimli boy + 0,05. Panel boyu gerçek listeden geliyorsa ve kısaysa taşma panelin yettiği kadar alınır (62 m² örnekte 3,8 cm).
- **Artan parça.** Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır. Alt parça olduğu gibi kullanılır. Üst parça, düz ucu saçağa gelecek biçimde karşı yüze konur; orada aynı açılı yere oturur (ön yüzün sol kırması ↔ arka yüzün sol kırması, dışarıdan bakışla; planda çapraz köşeler). Parça ters yüz edilmez. Kiremit desen sacda artan parça kullanılmaz: desen ters gelir (mühendis, 4 Ekim 12:14).
- **Eşleme.** En uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır. İki parçanın birlikte istediği boy: uzun kenarlarının toplamı − bir şeritlik boy farkı + kesim payı.
- **Kesim payı** (varsayım; soruldu, cevap gelmedi). {tr(kesim_mm)} mm: çapraz kesimde iki parçanın arasına ve aynı panelden çıkan dikdörtgenlerin arasına. Birkaç milimetrelik paya güvenilmesin diye kondu.
- **Dizilimin başladığı yer** (varsayım; soruldu, cevap gelmedi). Altı başlangıç denenir: her yüzde sol köşeden · uzun yüzlerde sol köşeden, kısa yüzlerde ortadan · uzun yüzlerde ortadan, kısa yüzlerde sol köşeden · her yüzde ortadan · her yüzde sağ köşeden · karşılıklı yüzlerde planda aynı uçtan. En az paneli veren ilk başlangıç listeye girer. "Ortadan": yüzün ortasına bir ek yeri gelir, şeritler iki yana eşit dağılır; köşe hep dışarıdan bakışla.
- **Yok sayılanlar.** Boy bindirmesi yok (panel tek boyda); yedek panel eklenmez.

Ç8201, tek kat panel: **{kaplama_s["adet"]} adet L {round(gb["cati"]["panel_boyu_m"] * 1000)}** ({dz["tam_boy"]} tam boy + {dz["kesilen"]} kesilen; kesilen her panelden iki parça çıkıyor: biri bir yüze, öteki karşı yüze). Dizilim {dz["baslangic_adi"]} başlıyor. Çizimler: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_acilim.png` (açılım; her parçada panel numarası) ve `C8201_cati_kesim.png` (her panelin kesimi); döküm `C8201_cati_acilim.json`.

{dizilim_tablo}

Okuma:

- **Sağlama.** Aynı kural, bu koda bakmadan ayrıca hesaplandı (bağımsız denetim, 4 Ekim; taşma ve kesim payı eklendikten sonra yeniden): beş örnek (Ç8201'in dört kaplaması ve 62 m² liste) × altı başlangıç × üç kesim payı (0, 5 mm, 1 cm) = 90 adedin hepsi aynı çıktı; her birinin o dizilim için en az olduğu gösterildi. Her paneldeki parçaların panele sığdığı, üst üste binmediği ve yüzdeki yerine tam oturduğu çokgenlerle sınanıyor (`cati_acilim_saglama.py`; rastgele 120 kırma çatıda, 1440 dizilimde sorun çıkmadı; kural bilerek bozulunca sınama yakalıyor).
{dizilim_okuma("Tek kat panel (baz paket)", dz)} En dar kesimde {tr(dz["en_dar_pay_cm"], 1)} cm pay kalıyor.
{dizilim_okuma("Sandviç panel", dz_s)}
{dizilim_okuma("Trapez sac", dz_t)}
{dizilim_okuma("Kiremit desen sac", dz_k)}
- **Taşmanın ve kesim payının etkisi.** 02:58 sürümünde (taşma ve kesim payı yok; L {YAYIMLANAN["panel_boyu_mm"]}) tek kat panel 28, sandviç panel {YAYIMLANAN["sandvic"]}, trapez sac {YAYIMLANAN["trapez"]}, kiremit desen sac 26'ydı; şimdi {dz["adet"]}, {dz_s["adet"]}, {dz_t["adet"]} ve {dz_k["adet"]}. Taşma her parçayı {tr(tasma_cm)} cm uzatır; iki parçalı kesim {tr(2 * tasma_cm)} cm fazla boy ister. Sandviç panelde ve trapez sacda bazı eşler artık aynı panele sığmıyor.
- **Önceki kural** (yüzey + %10, aynı panel boyuyla): tek kat panelde {onceki_kural(K["tek_kat_panel_kapatma_m"]["deger"])}, sandviç panelde {onceki_kural(K["sandvic_panel_kapatma_m"]["deger"])}, trapez sacda {onceki_kural(K["trapez_sac_kapatma_m"]["deger"])}, kiremit desen sacda {onceki_kural(K["kiremit_kapatma_m"]["deger"])} verir.
- **62 m² gerçek liste** (kırma çatı, sandviç panel L 3200): listede {k62["liste"]} adet (ayrıca 2 adet L 1000); dizilim {k62["hesap"]} veriyor (02:58 sürümünde, taşmasız, 26'ydı). Listedeki {k62["liste"]} uzun ve 2 kısa panel alan olarak {tr(k62["liste"] + 2 * 1.0 / 3.2, 1)} panel eder. Kısa panellerin köşe parçaları için gönderilip gönderilmediği bilinmiyor.
- **Mühendisin 10 × 10 m dört omuz metrajı** (trapez sac L 5900): metrajda 36 adet var; dizilim tablonun son satırındaki adedi veriyor. Çatı planı saçak dahil 10,6 × 10,6 m ve eğim %33 alındı; yüzey metrajdaki 118 m²'yi tutuyor.
- **Dar yerler** (bağımsız denetimin notları; kesim payı taramasıyla doğrulandı). Kesim payı 2,8 mm ya da daha az alınırsa sandviç panel {dz_s["paysiz_adet"]}, trapez sac {dz_t["paysiz_adet"]} olur; 2,9 mm'den 3 cm'ye kadar adetler değişmiyor. Tam boy parçada pay yok: panel boyu tam eğimli boy + taşma. İki saçağın taşmalarının kesiştiği köşe (yaklaşık 5 × 5 cm) örtülmez: parçalar uzuyor, genişlemiyor. Kesim payı panel boyu yönünde ölçülüyor.
- **Sınır.** Yalnız dikdörtgen planlı, dört yanı eşit eğimli kırma çatı. Cumbalı çatıda (ters mahya) dizilim henüz yok.

## Mühendisin üçüncü cevapları (Lokman 4 Ekim 12:14'te iletti) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 02:58 sürümündeki on iki soruydu ("Sizden beklenenler"). Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Makas ve kiriş ölçüsü | "şimdilik Excel hesaplama motoruna uy" | Çatı çeliği, veranda dikmeleri ve kirişleri motorun ortalamasıyla kalıyor: {tr(kg(baz, "Çatı makas panelleri"))}, {tr(kg(baz, "Veranda dikmeleri (kolon paneli)"))} ve {tr(kg(baz, "Veranda kirişleri (kiriş paneli)"))} kg. Hesap değişmedi; makas ölçüsü verilirse değişir. |
| 2 | Tek katta et kalınlığı: kural mı, 2025 listelerindeki uygulama mı? | "Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz." | Kural geçerli; hesap değişmedi (baz {tr(kg(baz, TOPLAM))} kg, dış 140 {tr(kg(d140, TOPLAM))} kg). 2025 listelerindeki 0,8 mm eski uygulama olarak kayıtlı. |
| 3 | Çatı açılımı: başlangıç köşesi, kesim payı, yedek, kiremit desen sac | "5 cm çatı yüzeyinin dışında kalacak şekilde uzatıyoruz çatı kaplamalarını. Kiremit desen sacda artan parça karşı yüzde desen ters geldiğinden kullanılmaz." | Taşma {tr(tasma_cm)} cm eklendi: panel boyu L {YAYIMLANAN["panel_boyu_mm"]} → L {round(gb["cati"]["panel_boyu_m"] * 1000)}; tek kat panel yine {kaplama_s["adet"]} adet. Sandviç panel {YAYIMLANAN["sandvic"]} → {dz_s["adet"]}, trapez sac {YAYIMLANAN["trapez"]} → {dz_t["adet"]}. Kiremit desen sacda artan parçanın kullanılmaması teyitli ({dz_k["adet"]} adet). Başlangıç köşesi, kesim payı ve yedek cevaplanmadı: yukarıdaki varsayımlarla. |
| 4 | Tavan ve çatı panelinin adedi; hangi çatı tipi için? | "Genelde dörtomuz çatı tipinde tavan paneli ve çatı panelini kullanıyoruz. 100m2 için bu adetler üzerinden ilerleyebilrsin." | 100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]} adet geçerli; alana oranla Ç8201'de {tp["adet"]} ve {cp["adet"]}. Hesap değişmedi. |
| 5 | OSB takviyesi: duvarın tamamı mı, yalnız tezgâhın ve TV ünitesinin arkası mı? Klima duvarı? | "Duvarın tamamını al." | Hesap değişmedi ({osb_s["adet"]} levha). Klima duvarı cevaplanmadı; sayılmıyor. |
| 6 | Köşebent: çıkıntı yapan köşeler ve veranda tavanı sayılır mı? | "Odaya doğru çıkıntı yapan köşeler sayılmıyor. Veranda tavan çevresi sayılır." | Veranda tavanının çevresi ({tr(kb["veranda_tavan_cevresi_m"], 2)} m; brüt ölçüyle) eklendi: {YAYIMLANAN["kosebent"]} → {adet(baz, "Köşebent")}. Çıkıntı yapan {dis_kose} köşe sayılmıyor. Verandada köşe boyu eklenmedi. Buna bağlı trapez vida (5,5 × 25) 1000 → {adet(baz, "Trapez vida (5,5 × 25)")}. |
| 7 | Elektrik: buat için hangi odalar? Yatak odası ve banyodaki prizler tekli mi? | "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli." | İkisi de zaten öyleydi: oda sayısı {gb["oda_sayisi"]}, buat kasa {adet(baz, "Buat kasa")}. Hesap değişmedi. |
| 8 | Mahya bandı: mahya uzunluğundan mı, parça adedinden mi? | "Mahya bandı şu şekilde hesaplanır: “(Mahya Adedi * 2,8 (metre) + Ters Mahya Adedi * 2,8 (metre) + Damlalık adedi * 2,5 (metre))/10” şeklinde bulunur." | ({adet(baz, "Metal kiremit mahyası")} × 2,8 + 0 + 0) ÷ 10 → {onceki_bant} yerine {bant_s["adet"]} rulo. Damlalık okunan listelerde yok; sıfır alındı (açık soru). Trapez sac seçeneklerinde motordaki gibi trapez sac mahyası × 0,8 m toplanır. |
| 9 | Dış kapı: 100 mü, 95 mi? | "Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır." | Tanımda dış kapı boşluğu 100 → 95 cm (ekseni yerinde kaldı); plan ve paftalar yeniden çizildi. Liste hesabı zaten 95 × 210 ile yapılıyordu. |
| 10 | Boardex ve OSB kalınlığı; Boardex zayiatı | "Boardex 12.5 mm. OSB 11 mm. Boardex zayiatı %8." | Satırların boyutu 12,5 × 1200 × 2400 ve 11 × 1220 × 2440 oldu. Boardex zayiatı %15 → %{tr(zb * 100)}: dış cephe Boardex {YAYIMLANAN["boardex"]} → {boardex_s["adet"]}; saçak altı ve saçak yüzü aynı ({adet(baz, "Saçaklar için Boardex")} ve {adet(baz, "Saçak yüzü için Boardex")}). 2025 listelerindeki adetler %15'e uyuyor (aşağıda). |
| 11 | Excel motorundaki trapez sac formülü | Formülü yapıştırdı ve açıkladı: "Eğer K24 hücresi Trapez saç ise yüzey alanını ve trapez saç uzunluğunu hesaplayıp trapez saç uzunluğuyla trapez saç genişliği olan 0,8 metre ile çarpıyor." Yeniden kontrol edilmesini istedi: "Hangi hücreden neyi çekiyorum formül nasıl işliyor". | Formül yeniden okundu (aşağıda). Bulgu aynı: 0,8 paydanın parantezinin dışında. |
| 12 | Bayi standartları | "Şimdilik standartlarımız tam oturmadı. Tek tük bayilerin standartları var ancak bunu ileriki zamanlarda daha net söyleyebiliriz." | Bütün gruplar listede kalıyor; bayi kuralı örnek dosyasıyla duruyor. |

### Excel motorundaki çatı kaplaması formülü: hangi hücre ne, formül nasıl işliyor (11. cevap üzerine)

Motorun (`CTKBF V1.1`) MALZEMELER sayfası 4 Ekim'de yeniden okundu. Mühendisin yapıştırdığı formül 61. satırdaki (trapez sac) formüldür; aynı uzun ifade 58, 59, 61, 64, 67 ve 72. satırlarda da var. Her satırın başındaki EĞER, o satırın kaplaması seçili değilse 0 verir.

| Hücre | Ne |
|---|---|
| K10 | Bina dış uzun kenar (m) |
| K11 | Bina dış kısa kenar (m) |
| K13, K14 | Sundurma dış uzun ve kısa kenar |
| K17 | Oturum dışı veranda dış kısa kenar |
| K23 | Çatı tipi |
| K24 | Çatı kaplama |

Hepsi MUSTERI TALEP sayfasının C sütunundan gelir.

Formülün parçaları:

- **Çatı yüzeyi** = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14. Kısa kenara iki saçak (0,6 m) eklenir, %33 eğimle eğimli genişliğe çevrilir, uzun kenarla (veranda dahil) çarpılır; sundurma düz alanıyla eklenir.
- **Sac boyu** = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05: saçaktan mahyaya eğimli boy + 5 cm taşma. B sütunu bunu mm olarak gösterir.
- **Adet** = yüzey ÷ sac boyu × kaplama katsayısı × çatı katsayısı, yukarı yuvarlanır. Kaplama katsayısı: trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05. Çatı katsayısı: beşik 1 · beşik + cumba 1,14 · beşik + 2 cumba 1,27 · dört omuz 1,06.

Bulgular:

1. **Parantez (işlem sırası).** Formülde `yüzey / (sac boyu) * 0,8` yazıyor. Excel bölmeyi ve çarpmayı soldan sağa yapar: sonuç (yüzey ÷ sac boyu) × 0,8'dir. Mühendisin anlattığı hesap (sac boyu × 0,8 = bir sacın kapattığı alan; yüzey ÷ o alan) için 0,8'in paydanın parantezi içinde olması gerekir: `yüzey / ((sac boyu) * 0,8)`. Şimdiki haliyle trapez sacda adet olması gerekenin 0,64 katı çıkar (0,8 × 0,8). Metal kiremitte 1,05 de aynı yerde: adet %10 fazla çıkar. Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok.
2. **Uzun kenarda saçak yok.** Yüzeyde kısa kenara 0,6 eklenmiş, uzun kenara (K10 + K17) eklenmemiş. Aynı sayfadaki çatı izolasyonu satırı (84) uzun kenara da 0,6 ekliyor. 10 × 10 m binada formülün yüzeyi {tr(mk_besik["yuzey_m2"], 1)} m²; mühendisin kendi metrajında 118 m².
3. **Kapatma genişlikleri.** Motorda tek kat panel "100 cm kapatır", metal kiremit "105 cm kapatır" yazıyor. Gerçek listelerde ve montaj paftasında tek kat panel 87 cm, kiremit desen sac 110 cm. Tek kat panelde motor bu yüzden %13 az verir.
4. **Sac boyu hücresi (B61).** Yalnız "Trapez Saç" seçiliyken hesaplıyor; "OSB+Nem Bariyeri+Trapez Saç" seçiliyken 0 gösteriyor. Trapez vida (5,5 × 60) formülü (129. satır) sac boyunu bu hücreden aldığı için o seçenekte sacın vidası hesaba girmez.
5. **Sundurma.** Bu formülde sundurma alanı eğimle çarpılmıyor (K13 × K14); OSB ve nem bariyeri satırlarında (79, 81) çarpılıyor.

Örnekler (formül yazıldığı gibi → parantez düzeltilince):

| Örnek | Yüzey ÷ sac boyu | Trapez sac | Metal kiremit | Not |
|---|---|---|---|---|
| Motorun şablonundaki kayıtlı örnek (9,74 × 7,44; veranda 2,12; dört omuz) | {tr(mk_ornek["yuzey_m2"], 2)} ÷ {tr(mk_ornek["sac_boyu_m"], 3)} = {tr(mk_ornek["oran"], 2)} | {mk_ornek["yazilan"]["trapez"]} → {mk_ornek["duzeltilmis"]["trapez"]} | {mk_ornek["yazilan"]["kiremit"]} → {mk_ornek["duzeltilmis"]["kiremit"]} | Şablonda metal kiremit seçili; hücrede kayıtlı değer {mk_ornek["yazilan"]["kiremit"]} |
| Mühendisin 10 × 10 m beşik çatısı | {tr(mk_besik["yuzey_m2"], 2)} ÷ {tr(mk_besik["sac_boyu_m"], 3)} = {tr(mk_besik["oran"], 2)} | {mk_besik["yazilan"]["trapez"]} → {mk_besik["duzeltilmis"]["trapez"]} | {mk_besik["yazilan"]["kiremit"]} → {mk_besik["duzeltilmis"]["kiremit"]} | Metrajda 28 trapez sac var (her saçakta 10,6 ÷ 0,8 → 14). Düzeltilmiş formül 25 veriyor; kalan fark uzun kenara eklenmeyen saçaktan ve her saçağın ayrı yuvarlanmasından |
| Ç8201 (K10 {tr(uzun, 2)}; K11 {tr(kisa, 2)}; K17 {tr(gb["dis_olcu_m"][0] - uzun, 2)}; dört omuz) | {tr(mk_c["yuzey_m2"], 2)} ÷ {tr(mk_c["sac_boyu_m"], 3)} = {tr(mk_c["oran"], 2)} | {mk_c["yazilan"]["trapez"]} → {mk_c["duzeltilmis"]["trapez"]} | {mk_c["yazilan"]["kiremit"]} → {mk_c["duzeltilmis"]["kiremit"]} | Çatı açılımı trapez sacda {dz_t["adet"]}, kiremit desen sacda {dz_k["adet"]} veriyor. Motor tek kat panelde {mk_c["yazilan"]["panel"]} verir (87 cm ile {mk_c["tek_kat_87"]}); açılım {dz["adet"]} |

Motorun sac boyu Ç8201'de {mk_c["sac_boyu_mm"]} mm: listedeki L {round(gb["cati"]["panel_boyu_m"] * 1000)} ile aynı. Yükleme listesi kaplama adedini bu formülden almıyor; kırma çatıda çatı açılımından alıyor. Bulgular motorun kendisi için.

## Listenin grupları ve bayi kuralı

105 m² listedeki ve Excel motorundaki sırayla: Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Elektrik · Vida · Sıhhi tesisat · Boya.

- Bir grubun listeye girip girmeyeceği bayinin standardına bağlıdır. Örnek: 90 m² gerçek listede vida, elektrik ve sıhhi tesisat yok; 62 ve 105 m² listelerde var.
- Denemede: `bayi_kurallari_ornek.json` ve `yukleme.py --bayi <anahtar>`. Anahtar canlıda bayinin telefon numarası olacak; dosyada gerçek numara ya da ad yok. Kural grupları açıp kapatır; boya kovası ve vitrifiyeyi dahil eder ya da etmez; çatı yöntemini ve kaplamasını bayinin standardına çevirir.
- Hangi bayinin standardının ne olduğu soruldu. Mühendis (4 Ekim 12:14): standartlar henüz oturmadı; tek tük bayinin standardı var, ileride netleşecek. O zamana kadar bütün gruplar listede.

## Çelik: birim ağırlıklar (Excel motorundan)

Motor, gerçek projelerin tonajını duvar uzunluğuna bölerek ortalama almış (kat yüksekliği 2,70 m):

| Profil (sırt × başlık × et) | Dış duvar kg/m | İç duvar kg/m | Dikme kg/m | Kiriş kg/m |
|---|---|---|---|---|
| 80 × 45 × 0,8 | — | 13,00 | — | — |
| 80 × 45 × 1,2 | 20,33 | 19,75 | 6,42 | 6,55 |
| 140 × 45 × 0,8 | 18,20 | — | — | — |
| 140 × 45 × 1,2 | 29,04 | — | 8,26 | 8,27 |
| 140 × 45 × 1,5 | — | — | — | 11,04 |

Mühendisin tablosunda 140 × 0,8 satırında iç duvar 12,06 yazıyor: motorun sayfasında o değer, dışı 140 × 0,8 olan bir projenin 80 × 0,8 iç duvarı. Hesapta iç duvar kendi profiliyle aranır (80 × 0,8 → 13,00).

Çatı çeliği (80 × 45 × 0,8), saçak dahil çatı planının m²'si başına: beşik 5,70 · dört omuz 7,55 · beşik + cumba 5,65 · beşik + 2 cumba 6,08 kg/m². Dört omuz değeri üç projenin ortalaması (9,46 · 6,86 · 6,33).

- Hesap: duvar kg = duvar boyu × birim ağırlık. Dış duvar boyu = dış çevre; iç duvar boyu plandan (iç duvarların toplam boyu).
- Motor girdi olarak yalnız dikdörtgenin kenarlarını ve bölme sayısını alıyor; iç duvar boyunu (uzun + kısa) × (0,1543 × bölme sayısı + 0,756) diye tahmin ediyor. Planımız olduğu için gerçek boylar kullanıldı.
- Dikme = adet × 2,40 m × birim ağırlık; kiriş = boy × birim ağırlık; çatı = çatı planı × kg/m². Bunlar şimdilik böyle (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"); Lokman kiriş ve makasları bir makas ölçüsünden verirse değişir.
- **Tavan paneli ve çatı paneli** (yöntem A). 100 m² binada tavan paneli {tr(pk_tavan["kg_100m2"], 2)} kg, çatı paneli {tr(pk_cati["kg_100m2"], 2)} kg (Lokman'ın 4 Ekim düzeltmesi; mühendisin ilk cevabında 429,83 ve 561,6 kg'dı). Adet 100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]} (mühendisin ilk cevabı; üçüncü cevaplarda teyit etti: bu adetlerle ilerlenir, paneller genelde dört omuz çatıda kullanılır). Hesap: çatının örttüğü oturum alanı ÷ 100 × bu değerler; adet yukarı yuvarlanır. Ç8201 ({tr(oturum, 2)} m²): {tr(tp["kg"])} kg / {tp["adet"]} adet ve {tr(cp["kg"])} kg / {cp["adet"]} adet. Oranlamayı Lokman onayladı; kesin adet panel yerleşiminden gelir.

### Üç gerçek listeyle karşılaştırma (kg)

{celik_kg}

- Toplamlar %0,5 ve %3,7 farkla tutuyor; ama parçalar tek tek tutmuyor: duvarlar %5–13 eksik, çatı %10–30 fazla. Toplamın tutması, farkların birbirini götürmesinden.
- 140 mm dış karkaslı iki listede dış duvarların çoğu 0,8 mm, üçer paneli 1,2 mm; bu iki örnekte hesap listedeki gibi 0,8 mm ile yapıldığı için dış duvar %8,5 ve %8,6 eksik çıkıyor. O iki listede dış duvar 19,9 kg/m'ye geliyor (577 kg ÷ 28,98 m ve 1055 kg ÷ 53,04 m).
- Üç liste de yöntem B'de: tavan ve çatı paneli bu karşılaştırmada yok.

### Et kalınlığı (mühendisin kuralı, 4 Ekim)

Kural: tek katlı binada ve iki katlının zemin katında duvarlar 1,2 mm (dış 140 × 45 × 1,2 ya da 80 × 45 × 1,2; iç 80 × 45 × 1,2). İki katlının üst katında 0,8 mm; üst katta 200 cm ve daha geniş pencereli duvar 1,2 mm (genelde bir ya da iki duvar). Dikme ve kiriş 1,2 mm, makas 0,8 mm: bunlar listelerden çıkarım.

| Kaynak | Dış karkas | Dış duvar | İç duvar | Kuralla |
|---|---|---|---|---|
| 90 m² liste (2025), tek kat | 80 mm | hepsi 1,2 mm | 1,2 mm | uyuyor |
| 62 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 7 panel 0,8 mm | 0,8 mm | uymuyor |
| 105 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 20 panel 0,8 mm | 0,8 mm | uymuyor |
| Motorun verisi: tek katlı 140'lık örnek (55 m²) | 140 mm | 1,2 mm | 1,2 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin üst katı | 140 mm | 0,8 mm | 0,8 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin zemin katı | 140 mm | 1,2 mm | 1,2 mm | uyuyor |

3 Ekim'de dış 140 için 0,8 mm varsayılmıştı (2025 listelerindeki gibi); kuralla 1,2 mm oldu. Bu yüzden Ç8201'de dış 140 seçeneği artık baz paketten ağır. 2025 tarihli iki tek katlı liste kurala uymuyor; mühendis üçüncü cevaplarda kuralı yineledi ("Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz."). O listeler eski uygulama olarak kayıtlı; üç gerçek listeyle karşılaştırma o listelerdeki kalınlıklarla yapılıyor.

| Ç8201 | Baz (dış 80) | Dış 140 |
|---|---|---|
| Dış duvar ({tr(dis_boy, 1)} m) | 80 × 1,2: {tr(dis_boy * kg_m["dis"]["80x45x1,2"])} kg | 140 × 1,2: {tr(dis_boy * kg_m["dis"]["140x45x1,2"])} kg (0,8 mm olsaydı {tr(dis140_ince)} kg) |
| İç duvar | {tr(ic_boy, 2)} m · 80 × 1,2: {tr(ic_boy * kg_m["ic"]["80x45x1,2"])} kg | {tr(ic_boy_140, 2)} m · 80 × 1,2: {tr(ic_boy_140 * kg_m["ic"]["80x45x1,2"])} kg (0,8 mm olsaydı {tr(ic140_ince)} kg) |
| Çelik toplamı | {tr(kg(baz, TOPLAM))} kg | {tr(kg(d140, TOPLAM))} kg |

## Öteki kurallar

Durum: `lokman` Lokman söyledi · `muhendis` mühendis söyledi · `excel` yükleme listesi çalışma kitabındaki formül · `motor` Excel motorundaki formül ya da not · `uydurma` gerçek listelerdeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor · `bekliyor` değer henüz yok (sorulacak ya da paftadan gelecek) · `model` modeldeki açıklıklardan ya da plandan · `liste` örnekte gerçek listeden alınan sayı. Katsayılar ve kaynakları: `deneme/2026-10-03_yukleme/kurallar.json`.

- **Terim.** PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür (alın sacı, çatı alnı). Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü" diye geçer; önceki kayıtlarda ve kodun içinde "alın" denmişti.
- **Dış cephe** (excel; zayiat muhendis). Net alan = çevre × kat yüksekliği + dikme ve kiriş kaplaması (adet × çevre × boy) + çatı alnı (kalkan) alanları − kapı ve pencere boşlukları. Boardex = net × {tr(1 + zb, 2)} ÷ (1,2 × 2,4): zayiat %{tr(zb * 100)} (mühendis, 4 Ekim 12:14; motorda ve bir hesap sayfasında da %8). Listelerin çalışma kitabındaki formül %15'ti ve üç listedeki adetler %15'e uyuyor (hesap / liste, 90 · 62 · 105 m²: 45 / 46, 32 / 32, 52 / 51); %8 ile {" · ".join(f"{b['hesap']} / {b['liste']}" for b in boyle)}. Ç8201'de %8 ile {boardex_s["adet"]}, %15 ile {boardex_15} levha.
- **Kalınlıklar** (muhendis, 4 Ekim 12:14). Boardex 12,5 mm; OSB 11 mm. 2025 listelerinde Boardex 8 mm, OSB 9 mm yazıyor; motorda Boardex 8 mm, OSB 11 mm.
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0.
- **OSB takviyesi** (muhendis). Yalnız dolap ve TV ünitesi gelen duvarlar: modelin tanımında yazılır. Her duvarın o odaya bakan yüzünün boyu × kat yüksekliği − o yüzdeki boşluklar; × 1,05 ÷ 2,98. Duvarın tamamı alınır (Lokman: "tüm yüzeyini"; mühendis, 4 Ekim 12:14: "Duvarın tamamını al."). Tanımda duvar yazmıyorsa kalem hesaplanmaz.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (muhendis, 4 Ekim 12:14; 90 ve 105 m² listelerde de böyle, 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (uydurma). Dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64. 105 m² listenin hesap sayfasında "dış × 2" diye yazıyor.
- **Çatı kaplaması.** Baz pakette tek kat panel (lokman). Kırma çatıda panel ve sac adedi çatı açılımından (lokman; yukarıda "Lokman'ın ikinci düzeltmesi"): yüzler şerit şerit dizilir, çapraz kesimden artan parça karşı yüzde kullanılır. Kaplama saçaktan 5 cm taşar: panel boyu = eğimli boy + 5 cm (muhendis, 4 Ekim 12:14). Çatı planı girdide yoksa yüzey × 1,10 ÷ (boy × kapatma genişliği) (uydurma). Beşik çatıda saçak boyu ÷ kapatma genişliği (uydurma). Kapatma: sandviç panel 100, tek kat panel 87, kiremit desen sac 110, trapez sac 80 cm.
- **Shingle ve membran** (motor). Adet = çatı yüzeyi × çatı katsayısı ÷ 8 ("adet / 8 m²"). Çatı katsayısı: beşik 1; beşik + cumba 1,14; beşik + 2 cumba 1,27; dört omuz 1,06. Gerçek listeyle karşılaştırılmadı.
- **Mahya** (lokman). Mahya hattı ÷ (2,8 − 0,30). Kırma çatıda hat = tepe + dört kırma. Trapez sac mahyası L 800: mahya hattı ÷ (0,8 − 0,20) (motor).
- **Mahya bandı** (muhendis, 4 Ekim 12:14). (Mahya adedi × 2,8 m + ters mahya adedi × 2,8 m + damlalık adedi × 2,5 m) ÷ 10 m (rulo / 10 m), yukarı. Excel motorundaki formül aynı; motorda trapez sac mahyası × 0,8 m de toplanır, OSB mahyası ve özel mahya toplanmaz. Damlalık (L 2500) motorda adedi elle girilen bir kalem; okunan listelerde yok, sıfır alınır. Ç8201: {adet(baz, "Metal kiremit mahyası")} × 2,8 ÷ 10 → {bant_s["adet"]} rulo. 01:24'teki uygulama mahya uzunluğundandı ({onceki_bant} rulo; açıklamalı prefabrik yükleme listesi çalışma kitabındaki formül).
- **Çatı müdahale kapağı** (muhendis). Standart pakette gönderilmez; müşteri isterse kat adedi kadar eklenir.
- **Dere** (motor). Metal dere = saçak boyu ÷ (4,0 − 0,20); Lokman'ın 30 cm kuralında dere sayılmadı. Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2. İniş sayısı Lokman'ın kuralıyla; plana elle yerleştirilmişse o sayı (muhendis).
- **Köşebent** (muhendis). (Odaların tavan çevresi + veranda tavanının çevresi + iç köşe sayısı × 2,7 m) ÷ 2,5. İç köşe: iki duvarın odanın içinde buluştuğu köşe. Odaya doğru çıkıntı yapan köşeler sayılmaz; veranda tavanının çevresi sayılır (4 Ekim 12:14). Veranda çevresi brüt ölçüyle alınır; verandada köşe boyu eklenmez (okuma). Planı olmayan örnekte oda başına 4 iç köşe sayılır.
- **Saçak altı ve saçak yüzü.** Yöntem A'da saçak altı Boardex (lokman); adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × {tr(1 + zb, 2)} ÷ 2,88. Saçak yüzü de Boardex (muhendis): saçak ucu çevresi × yüz yüksekliği × {tr(1 + zb, 2)} ÷ 2,88. Zayiat Boardex'in %{tr(zb * 100)}'i (62 m² listenin formülünde %15'ti). Yöntem A'da saçak omegası yok (muhendis).
- **Yöntem B kalemleri.** Saçak sacı ve alın sacı = boy ÷ (2,5 − 0,30): 30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (÷ 2,2 çıkarım). Saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu; değişmedi.
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40; OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = aşık × 10 + omega × 10 ya da 6 + çelik panel × 10 + köşebent × 6; trapez (5,5 × 60) = m² × 2,5 + sac boyu ÷ 200 × sac adedi; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15; inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06; köpük 2; mastik = pencere adedi. Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu.
- **Elektrik.** Pafta sayımı varsa o kullanılır (motorun notu: sayılar "montaj paftasından sayılır"). Yoksa mühendisin oda başına kuralı (yukarıda). Kablo, buat, besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi ve izole bant motorun formülleriyle.

## Üç gerçek listeyle karşılaştırma (adet)

{ozet}

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani {kars_top - kars_ayni} farkın 10'u oradan.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok. Mühendisin cevaplarıyla gelen kurallardan (tavan ve çatı paneli, OSB takviyesinin duvarları, saçak yüzü) hiçbiri bu üç listeyle sınanamıyor; köşebent ve elektrik kuralı yukarıda sınandı. Çatı açılımı tek bir gerçek listeyle (62 m²) karşılaştırılabildi.

Adedi tutmayan kalemler:

{tutmayan}

Okuma:

- **Köşebent.** Mühendisin formülü, oda başına 4 iç köşeyle listelerin altında kalıyor (57 / 70, 39 / 50, 70 / 85); önceki kural (m² ÷ 2,5) yarısını veriyordu. Gerçek iç köşe sayıları bilinmiyor.
- **Sandviç panel (62 m², kırma çatı).** Liste {k62["liste"]} adet L 3200 (ayrıca 2 adet L 1000); açılım dizilimi taşmayla {k62["hesap"]} veriyor (taşmasız 26'ydı). Önceki kural (yüzey + %10) 27'yi tutturuyordu, ama o listeye uydurulmuştu.
- **Dış cephe Boardex.** Zayiat %{tr(zb * 100)} olunca üç listede de 2–3 levha az: {" · ".join(f"{b['hesap']} / {b['liste']}" for b in boyle)}. %15 ile 45 / 46 · 32 / 32 · 52 / 51'di. Karşılaştırmadaki bir eksilme buradan ({kars_ayni} / {kars_top}; önce 75).
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. Mühendis: iniş plana bakarak yerleştirilir. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı.
- **Saçak sacı.** L 2500 parça ve 30 cm bindirme (÷ 2,2) en yeni listeyi (Kasım 2025) tutturuyor; Eylül 2025 listelerinde birer fazla veriyor. Excel motorundaki 20 cm (÷ 2,3) üç listeyi de tutturuyor (14, 17, 18).
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Öteki levhalar** (alçıpan, OSB, izolasyon, saçak Boardex'i). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant, mastik). Motorun m² formülleri listelerdeki sayıları vermiyor. Mastik üç listede de 8.
- **Tutanlar.** Beyaz tavan alçıpanı, mahya, dere, dere kelepçesi, sıhhi tesisat (105 m²'de yedi kalemin yedisi), uçlar ve kesme taşı.

## Ç8201 taslak

Girdi: `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json` (geometri Yapı Tanımı taslağından; varsayımlar dosyanın içinde). Çatı yöntemi A; çatı kaplaması baz paketteki tek kat panel. "Dış 140" sütunu yalnız değişenleri gösterir. Bu modelin gerçek listesi yok: taslak yalnız kurallardan çıkıyor.

Not: saçaklar için Boardex'te alan liste yöntemiyle saçak boyu × 0,30 = 11,8 m² (köşeler iki kez sayılır); gerçek saçak altı 11,4 m². İkisi de 5 levha.

{taslak}

### Çatı kaplaması seçenekleri

Baz pakette tek kat panel (Lokman, 4 Ekim 01:42). Altı seçenekte değişen kalemler (son üç seçenek gerçek listeyle karşılaştırılmadı):

{kaplama}

### Aynı model yöntem B ile

Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı {adet(yb, "Saçak sacı (30'luk)")}, saçak omegası {adet(yb, "Saçak omegası")}, tavan omegası {adet(yb, "Tavan omegası (60'lık)")}, aşık {adet(yb, "Aşık")} girer. Çelik {tr(kg(yb, TOPLAM))} kg, trapez vida (5,5 × 25) {adet(yb, "Trapez vida (5,5 × 25)")} olur.

## Excel motoruyla ilgili gözlemler (mühendise iletilecek)

- **Trapez sac ve metal kiremit adedi.** Formülde 0,8 ve 1,05 paydanın parantezi dışında: kapatma genişliğine bölmek yerine çarpıyor. Hücreler, formülün işleyişi, örnekler ve öteki dört bulgu yukarıda ("Excel motorundaki çatı kaplaması formülü"). Mühendis 11. cevabında formülü yeniden kontrol etmemizi istedi; bulgu ona iletilecek. Trapez sacda motorun formülü kullanılmıyor.
- **Kırma çatıda kaplama adedi.** Motor yüzeyden hesaplıyor; notunda gerçek adedin AutoCAD'de yerleşimle bulunacağı yazıyor. Mühendisin 10 × 10 m dört omuz metrajında 118 m² yüzey için 36 adet L 5900 trapez sac var (yüzeyin 1,44 katı). 62 m² gerçek listede 27 adet L 3200 ve 2 adet L 1000 sandviç panel var (yüzeyin 1,15 katı). Lokman'ın 4 Ekim 01:42 kuralıyla adet artık çatı açılımından çıkıyor; karşılaştırma yukarıdaki tabloda.
- **Köşebent.** Motor plansız hesaplıyor: oda çevrelerini bina kenarlarının altı katı, iç köşeyi 36 sayıyor. Ç8201'in ölçüleriyle {motor_kosebent} verir; plandan {adet(baz, "Köşebent")}.
- **Elektrik.** Motorda sayılar sabit: duy 7, glop 3, tekli anahtar 9, çiftli anahtar 2, tekli priz 22, çiftli priz 3, uydu prizi 1, sigorta 9; buat = anahtar + priz + 9.
- **İniş borusu.** Motorda dere adedi ÷ 5 + 6; mühendisin 10 × 10 m metrajındaki sayıları (8 ve 6) vermiyor (9 ve 8 verir).
- **Motorda olup listede olmayan kalemler.** Mühendisin ikinci cevaplarıyla: mahya bandı listeye eklendi; çatı müdahale kapağı standart pakette yok, müşteri isterse eklenir. Ters mahya kenar kutuları (ters mahya × 2) cumbalı çatı çalışılınca sorulacak; hesapta yok. Damlalık (L 2500): motorda adedi elle giriliyor (şablonda 0), mahya bandı formülünde geçiyor; okunan listelerde yok.

## Açık sorular

1. **Çatı dizilimi.** Dizilim nereden başlar? Listeye en az paneli veren başlangıç giriyor: Ç8201'de {dz["baslangic_adi"]}, {dz["adet"]} panel; her yüzde sol köşeden başlanırsa {dz["baslangica_gore"]["sol"]}. Montaj ekibi dizilim şemasına uyar mı? Kesim payı {tr(kesim_mm)} mm uygun mu? Dizilimden çıkan adede yedek eklenir mi (62 m² listede {k62["liste"]} uzun ve 2 kısa panel; dizilim {k62["hesap"]})? Üçüncü tur bu üçünü cevaplamadı.
2. **Excel motorundaki kaplama formülü.** Beş bulgu mühendise iletilecek (yukarıda): parantez, uzun kenardaki saçak, kapatma genişlikleri, B61, sundurma. Kapatma genişliği sorusu listeyi de ilgilendiriyor: tek kat panel 87 cm mi (listeler, montaj paftası), 100 cm mi (motor)? Kiremit desen sac 110 mu, 105 mi? Liste 87 ve 110 ile hesaplıyor.
3. **Boardex zayiatı.** %{tr(zb * 100)} ile 2025 listelerinden 2–3 levha az çıkıyor (Ç8201: {boardex_s["adet"]}; %15 ile {boardex_15}). Bilerek mi?
4. **Damlalık.** Mahya bandı formülünde geçiyor; okunan listelerde yok, motorda adedi elle giriliyor. Hangi durumda listeye girer, adedi nasıl bulunur?
5. **Klima duvarı.** OSB takviyesinde sayılır mı (listelerde kalemin adı "TV, klima ve mutfak dolabı arkası")? Cevaplanmadı; sayılmıyor.
6. **Makas ve kiriş.** Şimdilik motorun ortalamasıyla (mühendis, 4 Ekim 12:14). Lokman bir makas ölçüsünden verirse çatı çeliği, dikme ve kiriş değişir.
7. **Bindirme.** Örnekte saçak sacı L 2800; listelerde L 2500. Saçak sacının boyu hangisi? Eylül 2025 listeleri 20 cm ile tutuyor. Derede ve L 800 trapez mahyasında bindirme de 30 cm mi (motorda 20 cm)?
8. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
9. **OSB zayiatı.** %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
10. **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var. O Boardex nereye gidiyor?
11. **Yöntem B.** Tavan omegası ve aşık aralığı 60 cm mi (sandviç panelde de)?
12. **Bayi standartları.** Henüz oturmadı (mühendis, 4 Ekim 12:14). Netleşince hangi bayide hangi gruplar, hangi çatı yöntemi ve kaplaması standart: bayi kuralı tablosuna yazılacak.
13. **Sırası gelince.** Çift kat modeli: üst katta 200 cm ve daha geniş pencereli duvarın 1,2 mm alınması (kural kayıtlı, uygulanmadı). Cumbalı çatı: ters mahya kenar kutuları ve cumbalı çatının açılımı.

Kapananlar:

- **Mühendisin 3 Ekim cevaplarıyla:** saçak omegası (gerekmiyor); saçak yüzünün malzemesi (Boardex); OSB takviyesinin kapsamı (yalnız dolap ve TV duvarları); köşebent formülü; iniş sayısındaki fark (plana göre yerleşim); elektrik sayıları (oda başına kural); çatı kaplaması seçenekleri (altı).
- **Lokman'ın 4 Ekim düzeltmeleri ve mühendisin ikinci cevaplarıyla:** tavan ve çatı panelinin ağırlığı ve alana oranlanması; baz paketin çatı kaplaması (tek kat panel; Lokman); kırma çatıda kaplama adedi (çatı açılımı ve dizilim; Lokman); et kalınlığı kuralı; OSB takviyesi için seçilen duvarlar; salon ile mutfak kurallarının birlikte uygulanması; mahya bandı (listede) ve çatı müdahale kapağı (yalnız müşteri isterse).
- **Mühendisin üçüncü cevaplarıyla (4 Ekim 12:14):** tek katta et kalınlığı (1,2 mm ile devam; 2025 listeleri eski uygulama); tavan ve çatı panelinin adedi (100 m²'de {pk_tavan["adet_100m2"]} ve {pk_cati["adet_100m2"]}); OSB takviyesinde duvarın tamamı; köşebentte çıkıntı yapan köşeler (sayılmaz) ve veranda tavanı (sayılır); buat için oda sayısı (veranda hariç) ve tekli prizler; mahya bandı formülü; dış kapı boşluğu (95 × 210); Boardex 12,5 mm, OSB 11 mm, Boardex zayiatı %8; kaplamanın saçaktan 5 cm taşması; kiremit desen sacda artan parçanın kullanılmaması.

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: `kurallar.json`'daki her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Modelin tanımı listenin girdisidir: odaların işlevi (elektrik kuralı), dolap ve TV duvarları (OSB takviyesi), elle yerleştirilmiş iniş yerleri tanımda durur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05). Çatı açılımı da öyle: aynı çatı ve kaplama her zaman aynı dizilimi verir.
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
"""
BELGE.write_text(D, encoding="utf-8")
print("yazıldı:", BELGE.relative_to(BURADA.parents[1]), "·", len(D.split("\n")), "satır")
