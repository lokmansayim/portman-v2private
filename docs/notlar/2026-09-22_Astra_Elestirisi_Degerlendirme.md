# Astra'nın (GPT-6) eleştirisine değerlendirme — 22 Eylül 2026, 00:40

Girdi: Astra'nın 21 Eylül araştırma raporuma yazdığı eleştiri + Astra'nın 21 Eylül teknik devir raporu. Amaç: iki görüşü tek plana indirmek.
İlke: hangisinin "en yüksek model" olduğu değil, hangi iddianın kanıtı olduğu sayılır. Aşağıda her madde için kabul / düzeltme ve ne değiştiği.

## 1. Kabul ettiklerim (planı değiştirir)

| Astra'nın noktası | Kararım | Ne değişiyor |
|---|---|---|
| "Anormal değil" ile "sorun değil" aynı şey değil; 7 çağrı × 22 bin önek bir rekonstrüksiyondur | **Doğru.** Raporda rekonstrüksiyon olduğu yazılıydı; "normal" kelimesi "gerekli" gibi okunabilir. | Metin: "mimarinin öngörülebilir sonucu; üretim için gereksiz". Ham iz istenirse Platform'daki 21 Eyl oturumundan çıkarılabilir (salt okunur). |
| Karşılaştırma birimi iş başına olmalı | **Kısmen.** Aynı iş (tek mesaj → PDF) için ölçüm birebir: Astra 200–300 bin, bu akşam **3.068 token** (21:43 mesajı, tek çağrıda PDF çıktı) → 65–98×. Altı mesajlık görüşme (~20 bin) için 10–15×. İkisi de rapora girer; biri diğerini yalanlamıyor. | KPI: "teslim edilen plan başına toplam token/maliyet" (Astra'nın önerisi) — state.json zaten mesaj başına token tutuyor; toplama eklenir. |
| "Her zaman tek çağrı" değil, "gerektiği kadar sınırlı çağrı" | **Doğru.** | Buton/liste cevabı (ID ile) → LLM çağrısı **sıfır**; revizyon açıklaması gerekirse ikinci sınırlı çağrı; ajan döngüsü yok. |
| Astra fiyatlarındaki iki okuma farklı hizmet katmanı (Standard / Flex-Batch) | **Muhtemelen doğru** (tam 2× fark bunu destekliyor). | Rapor notu: $10/$1/$50 Standard varsayılır; hesap katmana bağlanır. |
| Her alanın yanında kaynağı (hangi mesaj) ve "bayi söyledi / sistem varsaydı" ayrımı | **Doğru ve ucuz.** Beyin zaten "olmayanı doldurma" + `belirsizlikler` tutuyor; alan başına kaynak mesaj kimliği yok. | Talep şemasına `kaynak` (mesaj id) alanı; taslağa "beyan / varsayım" etiketi. |
| Structured Outputs ≠ doğru yorum; `confidence` tek başına izin değil | **Doğru; zaten böyle.** Kural katmanı her alanı katalog/kurala karşı doğruluyor; `guven` yalnız soru sormaya etki ediyor. | Değişiklik yok; belgeye yazılır. |
| Şirket hafızası şimdi, ürün satın almadan; 5 mantıksal alan; bayi beyanı ≠ şirket kuralı (Ubeydullah teknik, Lokman kapsam onayı) | **Doğru; benim "3 tablo"mun genişletilmiş hali.** | DB şeması: onaylı bilgi / bayi-müşteri / proje-revizyon / **karar (gerekçe, istisna, geçersiz kılan)** / iyileştirme kayıtları (aday → değerlendirme). Kural değişikliği yalnız onayla. |
| RAG = "kaynaklı getirme"; katalog özeti prompt'a sığar ama bilgi varlığı 37 satır değil | **Doğru; raporla çelişmiyor.** Raporda "fiyat/BOM anahtarla, belge bölümleri, vektör sonra" deniyordu. | Getirilen her teknik bilgi: belge adı + sürüm + kapsam + onay durumu. Vektör DB: Türkçe anlam kaçırma ölçülürse. |
| Fine-tuning kararı takvimle değil ölçülen hatayla | **Doğru.** | "6. ay" ifadesi kalkar; koşul: regresyon setinde kalıcı bir hata sınıfı. |
| 37 planı önce 3–5 temsilci projede doğrula, sonra yay | **Doğru sıralama.** | Pilot: sade dikdörtgen + verandalı + farklı iç bölünme + özel bağlantı örneği. |
| 37 planı yeniden üretmek genellemenin kanıtı değil | **Doğru.** | Görülmemiş talep/revizyon test seti ayrı tutulur. |
| "Yeni plan çiz" kadar "şu kısmı değiştir, kararlarımı koru"; değişmeyen katalog çıktısı yeniden çizilmez | **Doğru; varyant sistemi bunun çekirdeği.** | Oda kilitleme + fark gösterimi; onaylı katalog çıktıları önbellekten (P6001 r01 gibi). |
| Plan, BOM ve fiyat aynı sürümlü proje tanımından; kapılı pano tek eleman | **Doğru; Motor BOM'u blok sayımıyla bunu yapıyor** (kapı/pencere panosu tek BOM bloğu, doğrama ayrı sayılır). | Fiyat zinciri: doğrulanmış miktar → tarihli malzeme fiyatı → işçilik kuralı → bayi koşulu → teklif sürümü. |
| Gecikmeyi aşama aşama ölç; hosting teşhisini tek hataya bağlama | **Kısmen.** MemoryError kaydı gerçek (task2/worker.log, 21:19–21:28) ve LVE belgesiyle uyumlu; ama tek olay kapasite çalışması değildir. | state.json'daki aşama zaman damgaları (received/started/finished/accepted/delivered) raporlanır; VPS kararı ölçülen bellek/eşzamanlılıkla teyit edilir — ancak €5–8/ay'lık adım düşük riskli. |
| İşlem güvenliği: mükerrer mesaj, çift onay, üretim sırasında revizyon, "üretildi" ≠ "teslim edildi" | **Çoğu var, belgelenmeli.** Gelen satır wamid ile tekil; giden durumları pending→accepted→sent/delivered/read ayrı; belirsiz POST tekrar edilmez. Eksik: üretim sürerken gelen revizyonun etiketlenmesi ve çift onay senaryosunun test seti. | Test setine bu 6 senaryo eklenir. |
| KVKK: takma adlaştırma ≠ anonimleştirme; sözleşme düzeni hukuk danışmanıyla | **Doğru.** | Veri minimizasyonu + saklama süresi tasarımı; hukuki değerlendirme dışarıdan. |
| Takvim yerine kabul ölçütleri; geliştirme ekibi ile üretim sistemi ayrı; tek depoda karar/kural/şema/test | **Doğru.** | Özel Git deposu + `KARARLAR.md`; iki modelin uzlaşması test yerine geçmez. |

## 2. Düzeltmelerim (kanıtla)

**a) "Pano ızgarası ile üretim geometrisi aynı değil" — deneyi ve sistemi karıştırıyor.**
Eleştirilen sayılar (8×6 → 10,04 × 7,53 m) araştırmacının **yerleşim deneyinin** özetidir; deney yalnız "odalar modül gridine nasıl dağılır" sorusunu çözer ve bunu raporda da böyle tanımladım. Astra'nın "üç ayrı temsil" önerisi (mekân düzeni / ölçülü mimari / imalat geometrisi) **bu akşam canlıda çalışan sistemin zaten yapısıdır**:
- Mekân düzeni: İş Emri JSON — mahaller modül (ve yarım modül) biriminde dikdörtgen. Motor yarım pano adımını zorunlu kılar (`geometry.py`: "Mahal koordinatı yarım pano adımında değil" hatası; `hat` = yarım pano aks indeksi).
- Ölçülü mimari: `karar.py: dis_olcu_cm(nx, ny) = 125,5·nx + 20, 125,5·ny + 10` → 6×8 için **773 × 1014 cm**; duvarlar 10/6 cm; 62,75 yuvarlanmaz (float cm).
- İmalat geometrisi: `dxf_out.py` — pano blokları, köşe profilleri (100/60), üçlü H, standart dışı pano boyları mor ve ölçülü, kapılı/pencereli pano tek `BOM_` bloğu; doğrulama kaydedilen DXF yeniden açılarak yapılır (bu akşamki 3 canlı üretimde geçti).
Yani CP-SAT çıktısı Motor'a **girdi** olacak; imalat geometrisini çözücü değil mevcut Motor + doğrulayıcı üretecek. Astra'nın "OPTIMAL = bizim amaç fonksiyonumuza göre" ve "UNKNOWN ≠ yapılamaz" notları doğru ve zaten raporun sınır maddesiydi. Deneyin kodu şeffaflık için klasöre konuldu: `arastirma_notlari_2026-09-21/cpsat_grid_layout.py` (142 satır; Astra "kodu yok" demişti — artık var).

**b) "DXF'teki bütün noktaları 125,5'e yuvarlama" — öneri bu değildi.**
Raporda "k×125,5'e yuvarla, artık birkaç mm'yi aşarsa el temizliği için işaretle" deniyordu; doğru uygulama daha da dar: çıkarıcı **aks/duvar orta çizgilerini** okur, izinli değerler {k×125,5, k×62,75}, özel uçlar (122,5 / 120,5) ve bağlantı parçaları **öznitelik** olarak kaydedilir, yuvarlanmaz. Shapely'nin hassasiyet uyarısı geçerli; bu yüzden geometri "snap" değil "aks tanıma" ile çıkarılır. Astra ile hemfikiriz; ifade düzeltildi.

**c) "37 planla hiçbir model eğitilmez" — kapsamı belirtmeliydim.**
Kastım **üretici (generatif) kat planı modeli**: kanıt RPLAN 80 bin, Higharc 3.500, en küçük test rejimi 1.000 plan. Benzer plan bulma, sıralama, tercih öğrenme için 37 plan + revizyon geçmişi kullanılabilir (küçük modeller, gömme, kural puanlama). Astra'nın "hangi modeli hangi amaçla" ayrımı doğru.

**d) WhatsApp 1 Ekim 2026 ücretlendirmesi.** Araştırmacı Meta'nın "non-template messages pricing" sayfasına atıf yaptı; Astra resmî sayfada göremedi. İkisi de "teyit et" diyor; bütçeye etkisi her durumda ayda birkaç dolar. BSP'den teyit alınır; karar değişmez.

## 3. Uzlaşılan mimari (iki görüşün kesişimi)
LLM anlar (tek/sınırlı çağrı, yapılandırılmış çıktı, alan başına kaynak) → kod karar verir (durum makinesi, katalog/kural doğrulama, onay kapıları) → Motor çizer (modül düzeni → ölçülü → imalat; doğrulama) → insan onaylar (bayi ön onayı, mühendis teknik onayı, ticari onay). Hafıza: tek veritabanında 5 alan, sürümlü ve onaylı. Kaynaklı getirme evet; vektör DB ölçüm gerektirirse. Fine-tuning ölçülen hataya karşı. LangGraph gerekirse. Canlı hat ile araştırma hattı ayrı. Sürüm/karar/test tek depoda.

## 4. Sıradaki tek iş (kabul ölçütüyle)
**Aşama 1 — canlı hattı güvenceye al (bu hafta):** mesaj id tekilliği, çift onay, üretim sırasında revizyon, eski PDF'in yeni diye gitmemesi, aşama zaman damgaları ve iş başına token toplamı için test seti (30 mesaj + 6 senaryo) ve Python işçisinin VPS'e taşınması. Geçiş ölçütü: aynı test talebi tekrarlanabilir sonuç veriyor; mükerrer iş ve yanlış sürüm teslimi testte engelleniyor. Ardından Aşama 2: 3–5 pilot projede DXF → aks tanıma → İş Emri çıkarımı, kaynakla karşılaştırma.
