# Aşama 2 · Yaklaşık 90 m² 3+1 adaylarının kaynak–geometri karşılaştırması (30.09.2026)

Amaç: Aşama 2'nin kabul vakası (yaklaşık 90 m² 3+1) için katalogdaki adayların, bugünkü çıkarıcı ve Motor'la kaynağa uygun çizilip çizilemediğini göstermek. Eksik kapı ve pencereleri, alan tanımını ve açık teknik kararları tek pakette toplamak.

Kod değişmedi; canlıya dokunulmadı; yeni veri kullanılmadı. Kaynaklar yalnız depodakiler:
- katalog DXF'i: `ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf`;
- katalog PDF'inden çıkarılmış veri: `beyin/veri/katalog_37_proje.json`.

## Sonuç

**Üç geçerli aday yok; seçenekler hazır sayılmaz.**
- **Koşullu uygun, 2 aday:** P9401 ve P9201. Bütün kapı ve pencereler çizildi; kapalı odaların alanları kaynakla uyuşuyor. Koşullar verandanın ve açık plan sınırının doğru çizilmesi, ayrıca aşağıdaki kural kararları.
- **Geçersiz, 2 aday:** P9501 ve P1051. Oda yerleşimi yanlış çıkıyor; kapıların çoğu düşüyor. İç duvarlar 125,5 cm modülüne oturmuyor.
- **Ek aday P1121 geçersiz ve aralık dışı:** çizimdeki alanı 127 m²; iki cumbası (çokgen çıkıntı) var; 12 pencerenin 4'ü okunuyor.
- **Üçüncü aday için bir karar gerekiyor:** K16, yani modüle uyarlama mı, serbest aks mı (§4, K-A8).

**Önemli bulgu:** Motor'un kendi doğrulaması beş adayın beşinde "geçti" dedi; oda yerleşimi tamamen yanlış olan P9501 ve P1051 dahil. Bugünkü doğrulama çizimin kendi içinde tutarlı olup olmadığını ölçüyor, kaynağa uygunluğunu ölçmüyor. Bu yüzden adayların geçerliliği için yeni bir kaynak uygunluk denetimi öneriliyor (K-A9).

## 1. Nasıl karşılaştırıldı

- **Kaynak.** Katalog DXF'inde her planın paftası ayrı ayrı çizdirildi. Kapı ve pencereler görüntüden tek tek sayıldı; çıkarıcının kendi raporuna dayanılmadı. Oda etiketleri ve m² değerleri çizimdeki yazılardan alındı. Katalog PDF'indeki toplam m² ve oda listesi yanına kondu.
- **Geometri.** Bugünkü zincir değiştirilmeden koşuldu: çıkarıcı → İş Emri → Motor v1.1 (plan, BOM, doğrulama).
- **3D.** İki koşullu aday için 23 Eylül denemesindeki IFC üreticisi (`deneme/2026-09-23/13_Kiyas/kod`) aynı İş Emri'nden koşuldu.
- **Görseller:** `docs/raporlar/gorseller/asama2/<kod>_kaynak_motor.png`. Solda katalog çizimi, sağda Motor'un net alan planı.

## 2. Aday tablosu

| Aday | Katalog m² | Kapalı alan (dış ölçü, verandasız) | Pencere (kaynak → çizilen) | Kapı (kaynak → çizilen) | Oda alanları (çizim etiketi ↔ Motor) | IFC | Durum |
|---|---|---|---|---|---|---|---|
| **P9401** | 94 | 83,1 m² (1024 × 888,5; veranda boşluğu 7,9) | **7 → 7** | **5 → 5** | 3 yatak odası, banyo, yaşam alanı %2,4 içinde (ör. yaşam 41,6 ↔ 41,61). **Veranda 12,0 ↔ 7,9**: 62 cm'lik dışa taşan kısım çizilmiyor | 49 duvar, 7 pencere, 5 kapı, 6 mahal; şema hatası 0 | **Koşullu uygun** |
| **P9201** | 92 | 76,3 m² (1139,5 × 835,75; veranda boşluğu 18,9) | **6 → 6** | **5 → 5** | 3 yatak odası ve banyo %1,8 içinde. **Hol 1,47 ↔ 6,60, salon + mutfak 32,72 ↔ 27,55**: açık geçişte sınır farklı; toplam aynı (34,19 ↔ 34,15). **Veranda 16,5 ↔ 18,9** | 48 duvar, 6 pencere, 5 kapı, 7 mahal; şema hatası 0 | **Koşullu uygun** |
| P9501 | 95 | hesaplanmadı (yerleşim geçersiz) | 9 → 5 (cumbanın 3 penceresi ve mutfak penceresi yok) | 7 → 3 (4'ü düştü, 1'i yanlış odada) | Yanlış: çamaşır makinesi yazısı oda sayıldı; banyo 5,20 ↔ 2,18; mutfak 9,50 ↔ 12,22; salon 20,50 ↔ 23,49 | — | Geçersiz |
| P1051 | 105,6 | 84,8 m² (836 × 1014) | 8 → 8 ama yanlış odalarda | 5 → 0 | Yanlış: banyo 4,5 ↔ 12,28; yatak odası 11,1 ↔ 8,34; yaşam 38,1 ↔ 31,43. Veranda (19,1) ve sundurma (1,5) kutunun dışında, çizilmiyor | — | Geçersiz |
| P1121 (ek) | 112 (çizimde **127,0**) | hesaplanmadı | 12 → 4 (iki cumbanın 6 penceresi dahil 8 eksik) | 6 → 6 | Yanlış: bir yatak odası 12,4 ↔ 18,0 | — | Geçersiz, aralık dışı |

Motor doğrulaması beşinde de "geçti"; bu yüzden tabloda sütun olarak yer almıyor.

### Adaylara göre ayrıntı

**P9401 (en temiz aday).**
- İç bölmeleri modüle oturan üç katalog planından biri (öteki ikisi P6001 ve P6701).
- Açık plan: salon ve mutfak holle birlikte tek "yaşam alanı"; katalog da öyle diyor (41,6 m²).
- Eksik: verandanın bina kutusunun 62 cm dışına taşan kısmı. Motor v1 yalnız kutunun içini çiziyor.
- Konum farkları:
  - yaşam alanının iki penceresi 51 ve 57 cm, banyo penceresi 55 cm, bir yatak odası penceresi 34 cm kaymış;
  - 3. yatak odasının kapısı 62,5 cm kaymış.

  Nedeni: Motor açıklığı pano ortasına koyuyor (K-A5).
- İç duvarlar çizimde aksın 3 cm dışında; Motor aksa aldı (K-A7).

**P9201.**
- Kapalı odalar doğru.
- Hol ile salon arasında duvar yok. Çıkarıcı bölgeyi en yakın etikete göre bölüyor: hol 6,60 m² (çizimde 1,47), salon 27,55 m² (çizimde 32,72) (K-A4).
- Veranda kutunun içindeki boşlukta. Motor bütün boşluğu (502 × 376,5 = 18,9 m²) veranda sayıyor. Çizimde veranda 502 × 314; altında 63 cm'lik boş şerit var. Katalog 15,7, çizim yazısı 16,5 diyor (K-A2).
- İki pencere 62,75 cm, banyo penceresi 80,5 cm kaymış (K-A5).

**P9501.**
- İç duvarlar modülden 28 cm'ye kadar sapıyor.
- Salonda cumba var (üç pencereli çokgen çıkıntı); Motor v1'de çokgen duvar yok.
- Çıkarıcı "çamaşır makinesi" yazısını oda sandı; 5 etiketli bir bölgeyi yanlış böldü.
- Tasarımı değiştirmeden bugünkü zincirle çizilemez.

**P1051.**
- Dış kabuk modüler (6,5 × 8 pano); iç duvarlar değil: yatak odaları 418 cm genişlikte, 287 ve 314 cm derinlikte.
- Çıkarıcı odaları merdiven biçimli bölgelere böldü; bütün iç kapılar düştü.
- Dış kapı sundurmaya açılıyor; çıkarıcı onu "dışa açılan kapı" sayıp atladı (çizimde kanat yönü ayrıca kontrol edilmeli).
- Veranda 229 cm ve sundurma kutunun dışında.
- Serbest aks (K16 b) ile tasarım değişmeden çizilebilecek aday bu.

## 3. Alan tanımı: katalogdaki m² neyi anlatıyor

| Aday | Katalog m² | Kapalı alan | Veranda (çizim) | Kapalı alan + veranda | Net oda toplamı (verandasız, çizim) |
|---|---|---|---|---|---|
| P9201 | 92 | 76,3 | 15,8 (502 × 314) | **92,1** | 71,3 |
| P9401 | 94 | 83,1 | 12,0 | **95,1** | 77,8 |
| P1051 | 105,6 | 84,8 | 19,1 + sundurma 1,5 | **105,4** | 78,7 |

- **Tanım.** Katalogdaki m², kapalı alana verandanın eklenmesiyle ±1,1 m² içinde tutuyor. Yani bayinin katalogda gördüğü "92 m²" verandayı da içeriyor. Kapalı alanlar 76–85 m².
- **Kaynaklar ayrışıyor.** Katalog PDF'i ile DXF bazı yerlerde farklı:
  - P1121: katalogda 112, çizimde 127,0 m²;
  - P9201 verandası: 15,7 ↔ 16,5;
  - P9501'de ±0,2 m²'lik farklar;
  - P9201'in katalog oda listesinde salon + mutfak satırı eksik.
- Bayi "90 m² 3+1" yazdığında bunun kapalı alan mı, katalog m²'si mi olduğu belli değil. Bu, adayların seçimini doğrudan değiştiriyor (K-A1).

## 4. Kararlar

| No | Karar | Neden gerekli | Öneri | Kim |
|---|---|---|---|---|
| K-A1 | Bayinin "~90 m²"si hangi alan; tolerans ne? | Katalog m²'ye göre P9201 (92), P9401 (94), P9501 (95) aralıkta. Kapalı alana göre hepsi 90'ın altında (76–85) | Eşleşme katalog m²'ye göre ±%10. Her seçenekte kapalı alan, veranda ve net oda toplamı ayrı gösterilir | Lokman |
| K-A2 | Katalog PDF'i ile DXF farklıysa hangisi esas? | P1121 112 ↔ 127; P9201 verandası 15,7 ↔ 16,5 | Geometri DXF'ten. Bayiye gösterilen m² katalogdan. Fark %2'yi aşarsa işaretlenir; Lokman düzeltir | Lokman |
| K-A3 | Bina kutusunun dışına taşan veranda ve sundurma | P9401'de veranda 12,0 yerine 7,9 görünüyor; P1051'de veranda ve sundurma hiç yok | Motor'a kutu dışı veranda/sundurma desteği (plan, alan, BOM, IFC). Yapılmadan P9401 geçerli sayılmaz | Lokman (Motor değişikliği) |
| K-A4 | Açık geçişli mahallerin sınırı (P9201 hol–salon) | Motor holü 6,60 m² gösteriyor, çizim 1,47 diyor | Duvarsız bölgede sınır, katalog etiketlerinin alanlarını verecek biçimde çizilir. Olmuyorsa bölge tek mahal gösterilir ("Salon + Mutfak + Hol") | Lokman |
| K-A5 | Pencere ve kapının konumu: pano ortası mı, çizimdeki yer mi? | Farklar 34–80 cm; bir pencere başka panoya düşüyor | Üretimdeki kural ne ise o. Pano ortası doğruysa kayma raporlanır ve kabul edilir; değilse Motor'un konum kuralı değişir (22.09 bulgu 2) | Ubeydullah |
| K-A6 | Kapı genişlikleri | Çizimde iç 80 / dış 100; İş Emri standardı 82 / 90 (21.09). K3/K4 hâlâ açık | K3/K4 kararı; o güne kadar standart kalır, farkı raporda görünür | Lokman, Ubeydullah |
| K-A7 | İç duvar ekseni | Çizimde aks + 3–5 cm, kural aks ortalı (22.09 bulgu 3) | Kural onaylanır; sapma raporda kalır | Ubeydullah |
| K-A8 | Üçüncü aday: K16 (a) modüle uyarlama ya da (b) serbest aks | P9501 ve P1051'in iç duvarları modül dışı; ikisi bugünkü zincirle geçersiz | **(b) P1051 için.** Katalog tasarımı değişmez; dış kabuk zaten modüler; 23.09 önerisiyle aynı yön. Motor'un çekirdeğine dokunduğu için P6001 ve altın testler gerileme olarak korunur. P9501 cumba yüzünden ikinci sırada | Lokman |
| K-A9 | Kaynak uygunluk denetimi (yeni geçerlilik kapısı) | Motor doğrulaması yanlış çizilmiş planı da geçiriyor | Aday ancak şu koşullarla "geçerli": her kaynak odası doğru türde; net alan çizim etiketine %5 içinde (açık plan grup olarak); her kapı ve pencere doğru oda ve duvarda, konumu K-A5 kuralı içinde; veranda K-A3'e göre; Motor ve IFC aynı İş Emri'nden; Ubeydullah kabulü. Denetim kodlanır; sonucu adayın kaydında (Postgres) tutulur | Lokman |
| K-A10 | İnsan kabulü | Bugün hiçbir katalog planının İş Emri'nde insan kabulü yok | Ubeydullah Bey her adayın İş Emri'ni ve Motor PDF'ini onaylar; onay kayda geçer | Ubeydullah |

## 5. Kararlardan sonra sıra

1. K-A9'un denetimi kodlanır. Bu tablo her koşumda kendiliğinden üretilir; "geçerli" yalnız denetimden ve insan kabulünden sonra.
2. K-A3 (kutu dışı veranda) ve K-A4 (açık plan sınırı) yapılır. K-A5–K-A7 cevaplanınca P9401 ve P9201 geçerli olabilir.
3. K-A8 (b) seçilirse serbest aks Motor'a alınır; P1051 üçüncü aday olur. Gerileme: P6001 ve altın testler.
4. Ubeydullah kabulüyle üç geçerli aday olur. Seçenekler ancak o zaman hazır sayılır.

P6001 referans ve gerileme testi olarak kalır; yeni teslim onun tekrarı değildir.

## 6. Yeniden üretmek

```
python -m motor.cikarici ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf --secici P9401 --kod P9401 --cikti <klasör> --motor
```

Kaynak görseli ve yan yana görseller, 30.09 çalışma betiğiyle üretildi. Betik, K-A9 denetimiyle birlikte depoya alınacak. IFC için `deneme/2026-09-23/13_Kiyas/kod/motor_girdi.py` ve `ifc_uret.py` kullanıldı (`deneme/2026-09-23/README.md`'deki paket düzeniyle).
