# İE-03 · Aşama 0 envanteri (29.09 23:30)

Onay: Lokman 29.09 23:04. Envanter yalnız iki kaynaktan çıkarıldı:
- paylaşımı daha önce onaylanmış depo içeriği (`main` `ae39380`);
- İE-02'nin maskelenmiş örnekleri: depodaki belge ve testler, Mac'teki `21_Kapi_G/` ve `22_Kapi_G2/` çıktıları.

**Yeni veri alınmadı:**
- hosting konuşmaları, bayi yazışmaları ve canlı Postgres okunmadı;
- hiçbir şey LLM'e gönderilmedi;
- kod, paket ve canlı sistem değişmedi.

Yeni veri ihtiyacı ve izin listesi §7'de.

Bu envanterdeki hiçbir öğe `dogrulandi` değildir; hepsi Lokman'ın doğrulamasını bekleyen **aday**dır.

## 1. Özet

| Depo | Depoda bulunan aday | Durum |
|---|---|---|
| A · Şirket bilgisi | 7 kaynak (katalog, pencere ölçü kümesi, P6001 şablonları, varyant ve pafta alanları, terim kuralları, malzeme kataloğu) | Kullanılabilir çekirdek var; hiçbiri Lokman'ca doğrulanmış bilgi olarak işaretli değil |
| B · Bayi tercihleri | Yok. `bayiler.json`'da yalnız PATRON ve üç kurgusal test bayisi (B001–B003) | Gerçek tercih için yeni veri gerekir (§6) |
| C · Doğrulanmış deneyim | 5 aday sınıfı. Hafızaya uygun olan 2; ötekiler kod ya da kuralla çözülmüş | Taslak doğru yorumlar §4'te; doğrulama bekliyor |
| Değerlendirme seti tohumu | 22 harness vakası; `bilinen_hatalar`'da 57, `kalici`'de 27 test tanımı; canlı G (6 adım) ve G yeniden denemesi (8 adım) | T-genel için yeterli tohum; T-tekrar ve T-sızıntı için vaka üretilmeli (§5) |

## 2. Depo A adayları (şirket bilgisi)

| # | Kaynak (depo yolu) | İçerik | Görünürlük önerisi | Not |
|---|---|---|---|---|
| A1 | `beyin/veri/katalog_37_proje.json` | 37 proje: kod, aile (prefabrik/çelik tek kat), m², oda programı (2+1…4+1), kat planları, odalar | Bayiye açık | Katalog PDF'inden çıkarıldı. Satırların Lokman'ca doğrulanması gerekir; çıkarıcının bilinen eksikleri DURUM'da |
| A2 | `beyin/sema.py` (`Pencere.olcu`) | Geçerli pencere ölçüleri: 120x120, 120x180, 60x40, 120x100, 120x160, 160x120, 160x180, 180x180, 80x120, 120x50; işlemler ekle/kaldır/değiştir; duvarlar | Bayiye açık | Şema, LLM'e zaten veriliyor; hafızada tekrar gerekmez, terim sözlüğüne bağlanır |
| A3 | `is_emri/P6001_*.json` (4 dosya) | Canlıdaki tek şablonun (P6001) odaları, pencereleri (YAŞAM ALANI 120x120 ve 120x180, YATAK ODASI 1 120x120, BANYO 60x40, YATAK ODASI 2 120x180), kapılar (dış 90, iç 82), aynalı hâller | Bayiye açık | "Bu modelde yatak odası 1'in penceresi 120x120" gibi bağlam, olumsuz talimatın hangi öğeye ait olduğunu anlamaya yarar |
| A4 | `beyin/sema.py` (`Varyant`, `bina_ozellikleri`), `beyin/prompt.md` kural 5 ve 8 | Varyant türleri (ayna_x/ayna_y, pencere/kapı/veranda/çatı/ölçü değişikliği), pafta tablosu alanları | Bayiye açık | Şu an istemin sabit talimatında; ayrı bir terim sözlüğüne taşınabilir |
| A5 | `beyin/prompt.md` kural 2–4, 7 | Katalog kodu yazımları (P6001, "p6001", "P-6001"), ölçü ve pano ifadeleri, oda programı ("iki oda bir salon" → 2+1), oda adlarının tam yazımı | Bayiye açık | Terim sözlüğünün tohumu. Bayiye özgü terimler (B) buna eklenir |
| A6 | `motor/malzeme_katalogu.json`, `ref_yan/` | Malzeme ve BOM kayıtları, Yan Verandalı yükleme listesi | **İç** | İE-03 kapsamı dışında (fiyat/BOM). Görünürlük filtresinin sınanması için "iç" örnek olarak kullanılabilir |
| A7 | `ref_katalog/*.dxf`, `*.png` | P6001, P7001, P8501 ve tek kat planları çizimleri | Bayiye açık | LLM'e gitmez; A1'in kaynak belgesi |

A için kullanılmayanlar:
- `KARARLAR/`: sistem kuralları; hafıza değil, kod.
- `docs/notlar/`: araştırma ve tasarım notları; plan girdisi.
- `deneme/`: IFC/Blender denemeleri; korunur, dokunulmaz.

## 3. Depo B (bayi tercihleri)

- `beyin/veri/bayiler.json`: PATRON (Lokman) ve üç kurgusal test bayisi. İçlerinde ad ve firma var (kurgusal); tercih yok. Numara tutmuyor.
- Depoda gerçek bir bayinin tercihi yok. Canlıdaki 25 Patron mesajı Lokman'ın deneme mesajlarıdır; bayi tercihi sayılmaz.
- Kurgusal B001–B003, bayi ayrımı testlerinde (T-sızıntı) kullanılabilir: gerçek kişi değiller, yeni veri gerekmez.

## 4. Depo C adayları (İE-02'nin maskelenmiş örnekleri)

Mesaj metinleri Lokman'ın kendi deneme mesajlarıdır ve `IE-02-canli.md`'de zaten kayıtlıdır; numara ve kimlik yalnız iz olarak geçer. Taslak doğru yorumları sistem hazırladı; Lokman'ın rolü doğrulamaktır.

| # | Kaynak | Mesaj ve bağlam | Sistemin yorumu | Taslak doğru yorum | Hata sınıfı | Hafızaya uygun mu |
|---|---|---|---|---|---|---|
| C1 | G yeniden denemesi, iş 22 (`7e9fbfb5fd`); testler `test_a1_*` | Bekleyen soru: YATAK ODASI 1 için "değiştirelim mi, ekleyelim mi?" (istenen 120x180). Cevap: "değiştirmeyin" | LLM: `red/dusuk`, yalnız katalog kodu. Kural: soru yinelendi ("Anlayamadım.") | Bekleyen YATAK ODASI 1 değişikliği iptal; pencere 120x120 kalır; soru `cevaplandi` (sonuç: iptal); proje ve öteki öğeler etkilenmez; yeni revizyon yok | `olumsuz_kisa_cevap` | **Evet (genel).** Ama önce kural katmanı kapsamlı olumsuzluğu tanımalı (plan §4.3). Hafıza yalnız yorumu destekler |
| C2 | Testler `test_a1_*` ("değiştirme", "ekleme", "eklemeyin") | Aynı bekleyen soru; üç LLM biçimi (boş, bağlamdan doldurulmuş, red) | Kural: soru yinelenir | "değiştirme" → C1 gibi. "ekleme/eklemeyin" → Lokman'ın kararına bağlı (plan §10.5): ya iptal ya da istenen ölçü mevcut pencereye uygulanır | `olumsuz_kisa_cevap` | Evet (genel); karar sonrası |
| C3 | Harness 16 (canlı 22.09; B1) | Tek pencereli odaya "… yapın" | LLM: `islem=ekle` | `islem=degistir` (odada tek pencere; ekleme sözü yok) | `islem_yanlis` | Hayır: B1 kuralı çözüyor. T-genel vakası |
| C4 | G, iş 17 (`cafb202ad1`) | Bekleyen soruya kısa "değiştir" | Opus alanları bağlamdan doldurdu; eski kodda soru `dustu`, r03 | Soruya bağlı cevap; aynı projede r02 | `kisa_cevap_baglam` | Hayır: kodla düzeltildi (G-1…G-3). T-genel vakası |
| C5 | Test `test_a2_*` | Varyantta oda yalnız açıklamada ("yatak odası 1, 120x180") | Eski yol B1'e bakmadan değiştiriyordu | Belirsiz söz: soru | `varyant_oda_aciklamada` | Hayır: kodla düzeltildi. T-genel vakası |

**Koddan bulgu (canlıda görülmedi):** `beyin/karar.py`'de bekleyen soru yokken LLM bir olumsuz cümleyi `red` okursa, aşama `topluyor` ise `k.sifirla()` bütün talebi kapatıyor ("Talep kapatıldı").
- Örnek: plan toplanırken yazılan "pencereyi değiştirmeyin" bütün taslağı düşürebilir.
- Bu, "bütün proje etkilenmesin" ilkesine aykırı. Plan §4.3'te kapsamlı olumsuzluk kuralına alındı.
- Test edilecek; henüz düzeltilmedi.

## 5. Değerlendirme seti tohumu

| Bölüm | Depodan gelen | Eksik |
|---|---|---|
| T-genel | Harness 22 vaka (`beyin/testler/mesajlar.json`, kayıtlı çıkarımlar `cikarim_a/b.json`). `bilinen_hatalar` 57 test tanımı (B1 20, B2 23, G 8, A1 3, A2 3; parametreli olanlar tek sayıldı). `kalici` 27 test tanımı (G sırası ve A1 dahil). Canlı G (6 adım) ve G yeniden denemesi (8 adım) | Vaka 1'in takma adla yeniden dondurulması (İE-01'den açık) |
| T-tekrar | C1 ve C2'nin sınıfı (`olumsuz_kisa_cevap`) | Benzer ama aynı olmayan yeni vakalar gerekli: başka oda, başka ölçü, başka olumsuzluk ("kalsın", "dokunmayın", "istemiyorum"). Bunlar yeni veri değil, kurgusal üretimdir. Sistem taslak üretir, Lokman onaylar |
| T-sızıntı | Kurgusal B001–B003 | Her test bayisine bir "tuzak" tercih; kurgusal |

T-tekrar'ın 20 vakası ve T-sızıntı yerel olarak, gerçek veri olmadan kurulabilir. Gerçek bayi dilinin çeşitliliği ise §6'daki verilerle gelir.

## 6. Kişisel veri bulguları

- **Numara ve e-posta:** Depo metin dosyalarında telefon ve e-posta taraması yapıldı. Bulunanların hepsi test dosyalarındaki sahte ya da örnek numaralardı; gerçek numara yok.
- **`beyin/testler/mesajlar.json` vaka 1:** Gerçek olabilecek bir müşteri adı ve sevk yeri içeriyor (İE-01'den açık). Takma adla yeniden dondurulana dek T-genel'de yalnız kayıtlı çıkarımıyla kullanılır; metni LLM'e gönderilmez.
- **`deneme/2026-09-23/`:** Dosya adlarında bir bayinin adı ve bir bayi planı PDF'i var. İE-03'te kullanılmaz; korunur.
- **Mac'teki İE-02 çıktıları (`21_Kapi_G/`, `22_Kapi_G2/`):** Numara maskeli, mesaj metni yok, kimlikler iz olarak. Envanterde yalnız bu biçimde kullanıldı.

## 7. Yeni veri: ihtiyaç ve izin listesi (hiçbiri alınmadı)

| # | Veri | Neden (depo / ölçüm) | En az hangi alanlar | Maskeleme | Nerede işlenir | LLM'e gider mi | Onay |
|---|---|---|---|---|---|---|---|
| V1 | 12 gerçek bayinin listesi (kod, firma, rol) | B'nin iskeleti; bayi ayrımı | `bayi_kod`, firma kısa adı, rol. Numaralar yalnız VPS'te | Kişi adı yok, `bayi_kod` | VPS Postgres | Hayır | Veri paylaşımı |
| V2 | Onaylanmış eski teklifler ve projeler (bayi başına model, varyant, pencere ve kapı seçimleri) | B'deki tercihlerin kanıtı | Bayi kodu, katalog kodu, varyantlar, açıklık ölçüleri, tarih | Müşteri adı, adres ve fiyat çıkarılır | VPS ya da bu çalışma alanı (maskeli kopya) | Yalnız doğrulanmış tercih özeti | Veri paylaşımı |
| V3 | Bayilerin eski WhatsApp yazışmaları (talep ve düzeltme örnekleri) | C adayları ve T-tekrar'ın gerçek dil çeşitliliği | Mesaj metni, bağlam, sonuç | Numara, kişi adı, adres, müşteri bilgisi maskelenir; yalnız talep cümleleri | Önce Mac'te maskeleme, sonra VPS | Doğrulanmış örnekler ve ölçüm vakaları gider (Anthropic) | Veri paylaşımı; ölçüm için ayrıca ücretli deneme |
| V4 | Hosting `durum/` ve `state.json`'daki eski konuşmalar (21–29.09) | C adayları. İçerik büyük ölçüde Patron denemesi | Konuşma adımları, eylem, soru-cevap | Numara maskeli | VPS | Yalnız doğrulanmış örnekler | Veri paylaşımı (hosting'ten okuma) |
| V5 | Hosting bayi botu kayıtları (`ai.php` sohbetleri) | Bayilerin genel soru dili (C'nin kapsamı dışında; İE-03b adayı) | Soru metni | Tam maskeleme | — | — | Şimdilik gerekmez |
| V6 | Canlı Postgres'teki İE-02 mesaj metinleri | C1'in metin kaynağı. Metin zaten belgede var | `mesajlar.ham` metni | Numara maskeli | VPS | Hayır | Salt okunur canlı okuma. Gerekirse |
| V7 | Katalog ve ürün kurallarının doğrulanmış sürümü: katalog PDF sürümü, standart pencere ve kapı ölçüleri, terim sözlüğü | A'nın `dogrulandi` olması | Belge adı, sürüm, bölüm | Kişisel veri yok | Depo ve Postgres | Evet (bayiye açık kısım) | Lokman'ın doğrulaması |
| V8 | Kurgusal ölçüm vakaları (T-tekrar, T-sızıntı) | Ölçüm | Sistemin ürettiği taslaklar | Kurgusal | Bu çalışma alanı | Ölçümde evet | Ücretli ölçüm onayı |

Öncelik önerisi: V7 ve V8 yeni kişisel veri gerektirmez; önce onlar. Sonra V1 ve V2 (B için). V3 ve V4 gerçek dil çeşitliliği için, maskeleme kuralı onaylandıktan sonra.
