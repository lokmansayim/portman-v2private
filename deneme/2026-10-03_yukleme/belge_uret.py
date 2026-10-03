#!/usr/bin/env python3
"""Şartname belgesini (`docs/sartname/yukleme_listesi_yontemi.md`) hesap çıktılarından üretir.

Belgedeki tablolar ve sayılar `sonuc/` altındaki çıktılardan okunur; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Metin bu dosyanın içindedir: kural ya da kaynak değişince burada düzeltilir, belge yeniden üretilir.

Kullanım:
    python belge_uret.py --zaman "3 Ekim 2026 19:30"
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

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
yerlesim = baz["ara"]["kirma_kaplama_yerlesim_adedi"]
# Excel motorunun köşebent formülü, Ç8201'in ölçüleriyle (kapalı kısım): (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5
uzun, kisa = gb["kapali_olcu_m"]
motor_kosebent = math.ceil((uzun * 6 + kisa * 6 + 9 * 4 * 2.7) / 2.5 - 1e-9)

D = f"""# Çelik yükleme listesi: yöntem ve taslak (3 Ekim 2026)

Son güncelleme: {A.zaman}. Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar ve sayılar hesap çıktılarından üretilir (`belge_uret.py`; tablolar `sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda) ve önceki kurallar.
2. **Mühendisin cevapları.** PortatifEv'in inşaat mühendisi Ubeydullah'ın, 14:50 sürümündeki yedi soruya yazdığı cevaplar; Lokman 3 Ekim 18:14'te iletti (aşağıda). Kurallarda durumu `muhendis`.
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
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "geçici" notuyla. Tavan ve çatı paneli mühendisin 100 m² için verdiği değerden (18:14). |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Motordaki altı kaplama da hesaplanıyor (18:14). |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | Hesap değişmedi; kural teyitli. |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Yerini mühendisin plandan hesaplayan formülü aldı (18:14): Ç8201'de {adet(baz, "Köşebent")} (m² ÷ 2,5 ile 33'tü). m² ÷ 2,5 kurallarda yedek olarak duruyor. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. Mühendis: iniş plana bakarak yerleştirilir (18:14); elle yerleştirilirse o sayı kullanılır. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | Mahya (L 2800) ÷ 2,5 → 11. Yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım). Dere sayılmadı: 20 cm'de kaldı (soru). |
| 8 | Saçak altı | İki yöntem birlikte kullanılmaz; saçak sacı varsa Boardex kaplanmaz. Ç8201 Boardex kaplamalı, çatı ve tavan panelli. | Baz listede saçak sacı yok; saçaklar için Boardex var. Saçak yüzü de Boardex; saçak omegası yok (mühendis, 18:14). |
| 9 | İç duvarda OSB | İçlerde OSB yoksa mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye gönderilen ürün; "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". | Mühendisin cevabıyla (18:14): yalnız dolap ve TV ünitesi gelen duvarlar. Ç8201: {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha (önce bütün Yaşam Alanı: 42,5 m², 15 levha). |
| 10 | İç kapı | Boşluk en 90, yükseklik 214; kasa sağda, solda, üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke; kanat 200'e düşer. | Dört iç kapı da 90 × 214 (banyo dahil); kanat 200. Kanat eni 80: listelerdeki "80'lik kanat"tan ve 90 − 2 × 5'ten. |
| 11 | Vida, boya, elektrik, tesisat | Bütün paketlerde var; bayilerle paylaşılan katalog ve fiyat listelerinde de. Bayi kuralı olarak ele alınacak (örnek: bir bayi için çelikte standart ne, bir başkası için prefabrikte standart ne); canlıda bayi numaraları birincil anahtar, liste mesajı atana göre. | Dört grup varsayılan olarak listede; bayi kuralıyla kapatılır. |

## Mühendisin cevapları (3 Ekim; Lokman 18:14'te iletti) ve uygulanışı

Sorular 14:50 sürümündeki yedi soruydu. "Denetim" sütunu, cevabın elimizdeki kaynaklarla karşılaştırmasıdır.

| # | Soru | Cevap | Denetim | Uygulama |
|---|---|---|---|---|
| 1 | Et kalınlığı neye göre seçiliyor? | Duvarların kg/m değerleri: 80 × 0,8 iç 13; 80 × 1,2 dış 20,33 ve iç 19,75; 140 × 0,8 dış 18,20 ve iç 12,06; 140 × 1,2 dış 29,04. "140x0,8 duvarı 80x1,2 duvarına göre daha hafif olduğunu görebiliriz." | Değerler motorun duvar tonajı sayfasındakilerle aynı. Seçim ölçütü cevapta yok. 12,06 tek bir projenin 80 × 0,8 iç duvarı; 13,00 iki projenin ortalaması. Motorun verisinde 140 × 0,8 dış duvar yalnız iki katlı iki projenin üst katında; tek katlı 140'lık örnekte (55 m²) dış duvar 1,2 mm. | Birim ağırlıklar değişmedi; iç duvar 80 × 0,8 için 13,00. Dış 140'ta 0,8 mm varsayımı sürüyor; soru açık. |
| 2 | Tavan ve çatı panelinin ölçüsü, adedi, kg'ı? Saçak omegası gerekiyor mu? Saçak yüzü Boardex mi? | Motor çatıları dört grupta (beşik, beşik + cumba, beşik + 2 cumba, dört omuz) ortalama ağırlıkla hesaplıyor; çatıdaki Boardex kaplaması motorda henüz hesaplanmıyor. "10 m x 10 m (100 m2) bir binada tavan paneli koyduğumuzu düşünürsek (8 adet) tavan paneli ağırlığı 429,83 kg, çatı paneli (12 parça) koyduğumuzda 561,6 kg geliyor. Saçak omegası gerekmiyor. Saçak yüzü de boardex ile kaplanıyor." | 429,83 ve 561,6 okunan çalışma kitaplarında bulunamadı; mühendisin beyanı olarak kayıtlı. Hangi çatı tipi, saçak ve eğim için olduğu yazılmadı. Motorda "saçaklar için Boardex" satırı gerçekten 0. | kg ve adet çatının örttüğü oturum alanına oranlandı (oran çıkarım): Ç8201'de tavan paneli {tr(tp["kg"])} kg, {tp["adet"]} adet; çatı paneli {tr(cp["kg"])} kg, {cp["adet"]} adet. Saçak omegası satırı kalktı. Saçak yüzü için Boardex teyitli. Çelik toplamı 1902 → {tr(kg(baz, TOPLAM))} kg. |
| 3 | Baz pakette hangi çatı kaplaması var? | Motordaki kaplamalar: OSB + membran + shingle; OSB + nem bariyeri + trapez sac; trapez sac; tek kat panel; sandviç panel; OSB + membran + metal kiremit. | Motorun seçenek listesi aynı. Baz paket cevapta yok. Motorun trapez sac ve metal kiremit adedi formülü hatalı görünüyor (aşağıda "Excel motoruyla ilgili gözlemler"). | Altı seçenek hesaplanıyor. Lokman'ın "OSB + nem bariyeri + kiremit desen sac"ı motorun "OSB + membran + metal kiremit"iyle eşlendi (motor o seçenekte nem bariyeri hesaplıyor, membran hesaplamıyor). Baz paket sorusu açık. |
| 4 | OSB takviyesi bütün oda mı, yalnız o duvarlar mı? | "Bütün oda değil sadece dolap ve TV ünitesi gelen duvar metrajı alınır." | Gerçek listelerdeki alanlar (35 ve 39 m²) bütün odadan (72 ve 112 m²) küçük: cevapla aynı yönde. | Modelin tanımına dolap ve TV duvarları yazılır. Ç8201'de katalog görselinden üç duvar: {"; ".join(f"{x['duvar_adi']} {tr(x['boy_m'], 2)} m ({x['neden']})" for x in ot["duvarlar"])}. Net {tr(ot["net_m2"], 1)} m² → {osb_s["adet"]} levha. Duvar seçimi teyit bekliyor. |
| 5 | Köşebent: m² ÷ 2,5 gerçek listelerin yarısını veriyor. | "Köşebent hesabı bina içerisinde bulunan bütün odaların tavan çevresi uzunluğu ile bütün oda iç köşe uzunlukları (standart kat yüksekliğimiz 2,7 metre alınır) toplamının 2,5 metreye bölünmesiyle bulunur." | Motordaki formül aynı yapıda ama plansız: (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5. Üç gerçek listede iç köşe sayısı bilinmiyor (planları yok); aşağıdaki tablo. | Ç8201 (planından): ({tr(kb["tavan_cevresi_m"], 2)} + {kb["ic_kose"]} × 2,7) ÷ 2,5 → {adet(baz, "Köşebent")}. Yalnız iç köşeler sayıldı. |
| 6 | İniş sayısı iki listede kuraldan bir fazla. | "Dere inişi plana bakarak yerleştirilmesi doğru olur. Normalde düz bir saçakta ortalama 5 metrede bir dere inişi yazılır." | Mühendisin 10 × 10 m metrajında dört omuz çatıda 8, beşik çatıda 6 iniş var: Lokman'ın kuralı ikisini de veriyor. Motorun formülü farklı (dere adedi ÷ 5 + 6). | Kural değişmedi (Ç8201: {adet(baz, "Dere iniş borusu")}). Tanımda iniş yerleri elle verilirse (`cati.inis_noktalari`) o sayı kullanılır. Listelerdeki 7'ler plana göre yerleşimle açıklanıyor. |
| 7 | Elektrik sayıları paftadan mı, oda başına kuraldan mı? | Oda başına kural; "%75 lik bir doğruluk payı olacağı düşünülerek" (aşağıda). | 105 m² listenin pafta sayımıyla sınandı (aşağıda): kural 41, sayım 48 parça. | Pafta sayımı varsa o; yoksa kural. Ç8201: duy {adet(baz, "Tijli duy")}, glop {adet(baz, "Yuvarlak glop")}, tekli anahtar {adet(baz, "Tekli anahtar")}, çiftli anahtar {adet(baz, "Çiftli anahtar")}, tekli priz {adet(baz, "Tekli priz")}, çiftli priz {adet(baz, "Çiftli priz")}, uydu prizi {adet(baz, "Uydu prizi")}, sigorta {adet(baz, "W otomat (sigorta)")}. Yaşam Alanı'nda salon ve mutfak kuralları birlikte uygulandı (okuma). |

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
- Okuma: cevaptaki "anahtar" tekli anahtar, "priz" tekli priz sayıldı. "En uzak mesafe" motordaki gibi kapalı kısmın köşegeni alındı (Ç8201: {tr((uzun ** 2 + kisa ** 2) ** 0.5, 2)} m); motor 3 × 2,5 kabloda uydu prizini de sayıyor, hesap öyle yapıldı (fark 2 m). Buat için oda sayısı planın mahal sayısı alındı (Ç8201: {gb["oda_sayisi"]}).

Ç8201'de oda oda:

{elektrik_oda}

Kuralın sınaması: 105 m² gerçek listede pafta sayımı var. O listenin odalarına kural uygulanınca ("oda" yatak odası sayıldı; veranda bilgisi yok):

{elektrik_sinama}

Toplamda kural sayımın %85'ini veriyor; kalem kalem farklar büyük (çiftli anahtar 1 / 5, glop 2 / 4). Bu, mühendisin söylediği %75'lik doğruluk payıyla uyumlu. Tek liste; kanıt sayılmaz.

### Köşebent kuralının gerçek listelerle karşılaştırması

{kosebent}

Listelerdeki adetler, her odada ortalama 6–7 iç köşe varsa formülle çıkar. Salon, mutfak ve holün tek mahal olduğu planlarda bu olabilir; planlar elde olmadığı için sınanamadı. Ç8201'in planı sade: beş mahal, 21 iç köşe.

## Listenin grupları ve bayi kuralı

105 m² listedeki ve Excel motorundaki sırayla: Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Elektrik · Vida · Sıhhi tesisat · Boya.

- Bir grubun listeye girip girmeyeceği bayinin standardına bağlıdır. Örnek: 90 m² gerçek listede vida, elektrik ve sıhhi tesisat yok; 62 ve 105 m² listelerde var.
- Denemede: `bayi_kurallari_ornek.json` ve `yukleme.py --bayi <anahtar>`. Anahtar canlıda bayinin telefon numarası olacak; dosyada gerçek numara ya da ad yok. Kural grupları açıp kapatır; boya kovası ve vitrifiyeyi dahil eder ya da etmez; çatı yöntemini ve kaplamasını bayinin standardına çevirir.
- Hangi bayinin standardının ne olduğu bilinmiyor; sorulacak.

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
- Dikme = adet × 2,40 m × birim ağırlık; kiriş = boy × birim ağırlık; çatı = çatı planı × kg/m². Bunlar geçici: Lokman kiriş ve makasları bir makas ölçüsünden verecek.
- **Tavan paneli ve çatı paneli** (yöntem A; mühendis, 3 Ekim): 100 m² binada tavan paneli 8 adet 429,83 kg, çatı paneli 12 parça 561,6 kg. Hesap: çatının örttüğü oturum alanı ÷ 100 × bu değerler; adet yukarı yuvarlanır. Ç8201 ({tr(gb["celik"]["cati"]["oturum_m2"], 2)} m²): {tr(tp["kg"])} kg / {tp["adet"]} adet ve {tr(cp["kg"])} kg / {cp["adet"]} adet. Oran çıkarımdır; adet panel yerleşiminden gelir.

### Üç gerçek listeyle karşılaştırma (kg)

{celik_kg}

- Toplamlar %0,5 ve %3,7 farkla tutuyor; ama parçalar tek tek tutmuyor: duvarlar %5–13 eksik, çatı %10–30 fazla. Toplamın tutması, farkların birbirini götürmesinden.
- 140 mm dış karkaslı iki listede dış duvarların çoğu 0,8 mm, üçer paneli 1,2 mm; hesapta hepsi 0,8 alındığı için dış duvar %8,5 ve %8,6 eksik çıkıyor. O iki listede dış duvar 19,9 kg/m'ye geliyor (577 kg ÷ 28,98 m ve 1055 kg ÷ 53,04 m).
- Üç liste de yöntem B'de: tavan ve çatı paneli bu karşılaştırmada yok.

### Et kalınlığı (teyit bekliyor)

| Kaynak | Dış karkas | Dış duvar | İç duvar |
|---|---|---|---|
| 90 m² liste (2025), tek kat | 80 mm | hepsi 1,2 mm | 1,2 mm |
| 62 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 7 panel 0,8 mm | 0,8 mm |
| 105 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 20 panel 0,8 mm | 0,8 mm |
| Motorun verisi: tek katlı 140'lık örnek (55 m²) | 140 mm | 1,2 mm | 1,2 mm |
| Motorun verisi: iki katlı iki projenin üst katı | 140 mm | 0,8 mm | 0,8 mm |
| Motorun verisi: iki katlı iki projenin zemin katı | 140 mm | 1,2 mm | 1,2 mm |

Hesapta varsayılan: dış karkas 80 mm ise duvarlar 1,2 mm; 140 mm ise dış ve iç duvarlar 0,8 mm (2025 listelerindeki gibi). Bu yüzden Ç8201'de dış 140 seçeneği baz paketten daha hafif çıkıyor. Mühendis 140 × 0,8'in 80 × 1,2'den hafif olduğunu teyit etti; seçim ölçütünü yazmadı. Motorun verisi tek katta 1,2 mm gösteriyor: soru açık.

| Ç8201 | Baz (dış 80) | Dış 140 |
|---|---|---|
| Dış duvar ({tr(dis_boy, 1)} m) | 80 × 1,2: {tr(dis_boy * kg_m["dis"]["80x45x1,2"])} kg | 140 × 0,8: {tr(dis_boy * kg_m["dis"]["140x45x0,8"])} kg · 140 × 1,2: {tr(dis_boy * kg_m["dis"]["140x45x1,2"])} kg · listelerdeki karışımla (19,9 kg/m): {tr(dis_boy * 19.9)} kg |
| İç duvar | {tr(ic_boy, 2)} m · 80 × 1,2: {tr(ic_boy * kg_m["ic"]["80x45x1,2"])} kg · 80 × 0,8: {tr(ic_boy * kg_m["ic"]["80x45x0,8"])} kg | {tr(ic_boy_140, 2)} m · 80 × 0,8: {tr(ic_boy_140 * kg_m["ic"]["80x45x0,8"])} kg · 80 × 1,2: {tr(ic_boy_140 * kg_m["ic"]["80x45x1,2"])} kg |
| Çelik toplamı | {tr(kg(baz, TOPLAM))} kg | 0,8 mm ile {tr(kg(d140, TOPLAM))} kg · 1,2 mm ile {tr(kg(d140, TOPLAM) + dis_boy * (kg_m["dis"]["140x45x1,2"] - kg_m["dis"]["140x45x0,8"]) + ic_boy_140 * (kg_m["ic"]["80x45x1,2"] - kg_m["ic"]["80x45x0,8"]))} kg |

## Öteki kurallar

Durum: `lokman` Lokman söyledi · `muhendis` mühendis söyledi · `excel` yükleme listesi çalışma kitabındaki formül · `motor` Excel motorundaki formül ya da not · `uydurma` gerçek listelerdeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor · `bekliyor` değer henüz yok (sorulacak ya da paftadan gelecek) · `model` modeldeki açıklıklardan ya da plandan · `liste` örnekte gerçek listeden alınan sayı. Katsayılar ve kaynakları: `deneme/2026-10-03_yukleme/kurallar.json`.

- **Terim.** PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür (alın sacı, çatı alnı). Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü" diye geçer; önceki kayıtlarda ve kodun içinde "alın" denmişti.
- **Dış cephe** (excel). Net alan = çevre × kat yüksekliği + dikme ve kiriş kaplaması (adet × çevre × boy) + çatı alnı (kalkan) alanları − kapı ve pencere boşlukları. Boardex = net × 1,15 ÷ (1,2 × 2,4). Motorda ve bir hesap sayfasında zayiat %8 yazıyor; ama üç listedeki adetlere %15 yakın düşüyor (hesap / liste: 32 / 32, 45 / 46, 52 / 51); %8 ile 2–3 levha eksik kalıyor.
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0.
- **OSB takviyesi** (muhendis). Yalnız dolap ve TV ünitesi gelen duvarlar: modelin tanımında yazılır. Her duvarın o odaya bakan yüzünün boyu × kat yüksekliği − o yüzdeki boşluklar; × 1,05 ÷ 2,98. Duvarın tamamı alındı (Lokman: "tüm yüzeyini"). Tanımda duvar yazmıyorsa kalem hesaplanmaz.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (excel: 90 ve 105 m² listeler; 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (uydurma). Dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64. 105 m² listenin hesap sayfasında "dış × 2" diye yazıyor.
- **Çatı kaplaması** (uydurma). Kırma çatıda panel ve sac adedi = çatı yüzeyi × 1,10 ÷ (boy × kapatma genişliği); beşik çatıda saçak boyu ÷ kapatma genişliği. Kapatma: sandviç panel 100, tek kat panel 87, kiremit desen sac 110, trapez sac 80 cm. Motorun notu: gerçek adet AutoCAD'de yerleşim yapılarak bulunur. Kırma çatıda satırın notunda bir sağlama var: şerit şerit yerleşim (parçalar dikdörtgen kesilir, artıklar yüzler arasında paylaşılmazsa). Ç8201 sandviç panelde kural {adet(baz, "Sandviç panel")}, sağlama {yerlesim} veriyor; 62 m² gerçek listede kural 27, sağlama 30, liste 27 adet L 3200 ve 2 adet L 1000.
- **Shingle ve membran** (motor). Adet = çatı yüzeyi × çatı katsayısı ÷ 8 ("adet / 8 m²"). Çatı katsayısı: beşik 1; beşik + cumba 1,14; beşik + 2 cumba 1,27; dört omuz 1,06. Gerçek listeyle karşılaştırılmadı.
- **Mahya** (lokman). Mahya hattı ÷ (2,8 − 0,30). Kırma çatıda hat = tepe + dört kırma. Trapez sac mahyası L 800: mahya hattı ÷ (0,8 − 0,20) (motor).
- **Dere** (motor). Metal dere = saçak boyu ÷ (4,0 − 0,20); Lokman'ın 30 cm kuralında dere sayılmadı. Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2. İniş sayısı Lokman'ın kuralıyla; plana elle yerleştirilmişse o sayı (muhendis).
- **Köşebent** (muhendis). (Odaların tavan çevresi + iç köşe sayısı × 2,7 m) ÷ 2,5. İç köşe: iki duvarın odanın içinde buluştuğu köşe. Odaya doğru çıkıntı yapan köşeler ve veranda tavanı sayılmadı (okuma). Planı olmayan örnekte oda başına 4 iç köşe sayılır.
- **Saçak altı ve saçak yüzü.** Yöntem A'da saçak altı Boardex (lokman); adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × 1,15 ÷ 2,88. Saçak yüzü de Boardex (muhendis): saçak ucu çevresi × yüz yüksekliği × 1,15 ÷ 2,88. Yöntem A'da saçak omegası yok (muhendis).
- **Yöntem B kalemleri.** Saçak sacı ve alın sacı = boy ÷ (2,5 − 0,30): 30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (÷ 2,2 çıkarım). Saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu; değişmedi.
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40; OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = aşık × 10 + omega × 10 ya da 6 + çelik panel × 10 + köşebent × 6; trapez (5,5 × 60) = m² × 2,5 + sac boyu ÷ 200 × sac adedi; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15; inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06; köpük 2; mastik = pencere adedi. Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu.
- **Elektrik.** Pafta sayımı varsa o kullanılır (motorun notu: sayılar "montaj paftasından sayılır"). Yoksa mühendisin oda başına kuralı (yukarıda). Kablo, buat, besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi ve izole bant motorun formülleriyle.

## Üç gerçek listeyle karşılaştırma (adet)

{ozet}

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani {kars_top - kars_ayni} farkın 10'u oradan.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok. Mühendisin cevaplarıyla gelen kurallardan (tavan ve çatı paneli, OSB takviyesinin duvarları, saçak yüzü) hiçbiri bu üç listeyle sınanamıyor; köşebent ve elektrik kuralı yukarıda sınandı.

Adedi tutmayan kalemler:

{tutmayan}

Okuma:

- **Köşebent.** Mühendisin formülü, oda başına 4 iç köşeyle listelerin altında kalıyor (57 / 70, 39 / 50, 70 / 85); önceki kural (m² ÷ 2,5) yarısını veriyordu. Gerçek iç köşe sayıları bilinmiyor.
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. Mühendis: iniş plana bakarak yerleştirilir. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı.
- **Saçak sacı.** L 2500 parça ve 30 cm bindirme (÷ 2,2) en yeni listeyi (Kasım 2025) tutturuyor; Eylül 2025 listelerinde birer fazla veriyor. Excel motorundaki 20 cm (÷ 2,3) üç listeyi de tutturuyor (14, 17, 18).
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Levhalar** (Boardex, alçıpan, OSB, izolasyon). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant, mastik). Motorun m² formülleri listelerdeki sayıları vermiyor. Mastik üç listede de 8.
- **Tutanlar.** Beyaz tavan alçıpanı, mahya, dere, dere kelepçesi, sıhhi tesisat (105 m²'de yedi kalemin yedisi), uçlar ve kesme taşı.

## Ç8201 taslak

Girdi: `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json` (geometri Yapı Tanımı taslağından; varsayımlar dosyanın içinde). Çatı yöntemi A; çatı kaplaması örnek olarak sandviç panel. "Dış 140" sütunu yalnız değişenleri gösterir. Bu modelin gerçek listesi yok: taslak yalnız kurallardan çıkıyor.

Not: saçaklar için Boardex'te alan liste yöntemiyle saçak boyu × 0,30 = 11,8 m² (köşeler iki kez sayılır); gerçek saçak altı 11,4 m². İkisi de 5 levha.

{taslak}

### Çatı kaplaması seçenekleri

Baz paketin kaplaması söylenmedi. Altı seçenekte değişen kalemler (son üç seçenek gerçek listeyle karşılaştırılmadı):

{kaplama}

### Aynı model yöntem B ile

Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı {adet(yb, "Saçak sacı (30'luk)")}, saçak omegası {adet(yb, "Saçak omegası")}, tavan omegası {adet(yb, "Tavan omegası (60'lık)")}, aşık {adet(yb, "Aşık")} girer. Çelik {tr(kg(yb, TOPLAM))} kg, trapez vida (5,5 × 25) {adet(yb, "Trapez vida (5,5 × 25)")} olur.

## Excel motoruyla ilgili gözlemler (mühendise sorulacak)

- **Trapez sac adedi.** Motorun formülü: çatı yüzeyi ÷ sac boyu × 0,8. Kapatma genişliğine (0,8 m) bölmesi gerekirken çarpıyor görünüyor. 10 × 10 m beşik çatıda motor 16 verir; mühendisin kendi metrajında 28 var (her saçakta 10,6 ÷ 0,8 → 14). Metal kiremitte de × 1,05 var (÷ 1,05 olmalı; fark yaklaşık %10). Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok. Bu yüzden trapez sacda motorun formülü kullanılmadı.
- **Kırma çatıda kaplama payı.** Mühendisin 10 × 10 m dört omuz metrajında 118 m² yüzey için 36 adet L 5900 trapez sac var (yüzeyin 1,44 katı). 62 m² gerçek listede pay %15 (27 adet L 3200 ve 2 adet L 1000 sandviç panel). Kuralımız %10 alıyor; şerit yerleşimi sağlaması daha fazlasını veriyor (Ç8201: {adet(baz, "Sandviç panel")} yerine {yerlesim}).
- **Köşebent.** Motor plansız hesaplıyor: oda çevrelerini bina kenarlarının altı katı, iç köşeyi 36 sayıyor. Ç8201'in ölçüleriyle {motor_kosebent} verir; plandan {adet(baz, "Köşebent")}.
- **Elektrik.** Motorda sayılar sabit: duy 7, glop 3, tekli anahtar 9, çiftli anahtar 2, tekli priz 22, çiftli priz 3, uydu prizi 1, sigorta 9; buat = anahtar + priz + 9.
- **İniş borusu.** Motorda dere adedi ÷ 5 + 6; mühendisin 10 × 10 m metrajındaki sayıları (8 ve 6) vermiyor (9 ve 8 verir).
- **Motorda olup listede olmayan kalemler.** Çatı müdahale kapağı (kat adedi kadar), mahya bandı (rulo / 10 m), ters mahya kenar kutuları (ters mahya × 2). Okunan üç gerçek listeden çıkarılan kalemlerde yoklar; hesaba alınmadılar.

## Açık sorular

1. **Baz paketin çatı kaplaması** altı seçenekten hangisi?
2. **Et kalınlığı.** Tek katta dış 140'lık duvar 0,8 mm mi (2025 listeleri), 1,2 mm mi (motordaki 55 m² örnek)? 80'lik karkasta hep 1,2 mi? Ç8201 dış 140'ta fark yaklaşık {tr(dis_boy * (kg_m["dis"]["140x45x1,2"] - kg_m["dis"]["140x45x0,8"]) + ic_boy_140 * (kg_m["ic"]["80x45x1,2"] - kg_m["ic"]["80x45x0,8"]))} kg.
3. **Makas ve kiriş.** Lokman bir makas ölçüsünden verecek. Tavan ve çatı panelinin adedi ve kg'ı 100 m² değerinden oranlandı: oran doğru mu, değerler hangi çatı tipi için?
4. **OSB takviyesi.** Ç8201'de seçilen üç duvar doğru mu? Duvarın tamamı mı, yalnız dolabın ve TV'nin arkası mı? Klima duvarı da sayılacak mı (listelerde kalemin adı "TV, klima ve mutfak dolabı arkası")?
5. **Elektrik.** Salon ile mutfak aynı mahaldeyse iki kural birlikte mi uygulanır? Buat için "oda sayısı" hangi odalar? Yatak odası ve banyodaki prizler tekli mi?
6. **Kırma çatıda kaplama adedi.** Yüzeyin %10 fazlası mı, yerleşimle mi? (Yukarıdaki gözlem.)
7. **Motorda olup listede olmayan kalemler.** Çatı müdahale kapağı ve mahya bandı listeye girsin mi?
8. **Köşebent.** Odaya doğru çıkıntı yapan köşeler ve veranda tavanının çevresi sayılır mı?
9. **Bindirme.** Örnekte saçak sacı L 2800; listelerde L 2500. Saçak sacının boyu hangisi? Eylül 2025 listeleri 20 cm ile tutuyor. Derede ve L 800 trapez mahyasında bindirme de 30 cm mi (motorda 20 cm)?
10. **Dış kapı.** Katalog çiziminde 100 cm; listelerde boşluk 95 × 210 (bir listede 95 × 200), kapı 90 × 210.
11. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
12. **Kalınlıklar.** Boardex: 2 Ekim'de 12,5 mm denildi; listelerde ve motorda 8 mm. OSB: listelerde 9 mm; motorda ve 2 Ekim kaydında 11 mm.
13. **Zayiat.** Boardex %15 mi, %8 mi (motor)? OSB %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
14. **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var. O Boardex nereye gidiyor?
15. **Yöntem B.** Tavan omegası ve aşık aralığı 60 cm mi (sandviç panelde de)?
16. **Bayi standartları.** Hangi bayide hangi gruplar, hangi çatı yöntemi ve kaplaması standart?

Kapananlar (mühendisin 3 Ekim cevaplarıyla): yöntem A'da tavan ve çatı panelinin kg'ı; saçak omegası (gerekmiyor); saçak yüzünün malzemesi (Boardex); OSB takviyesinin kapsamı (yalnız dolap ve TV duvarları); köşebent formülü; iniş sayısındaki fark (plana göre yerleşim); elektrik sayıları (oda başına kural); çatı kaplaması seçenekleri (altı).

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: `kurallar.json`'daki her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Modelin tanımı listenin girdisidir: odaların işlevi (elektrik kuralı), dolap ve TV duvarları (OSB takviyesi), elle yerleştirilmiş iniş yerleri tanımda durur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05).
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
"""
BELGE.write_text(D, encoding="utf-8")
print("yazıldı:", BELGE.relative_to(BURADA.parents[1]), "·", len(D.split("\n")), "satır")
