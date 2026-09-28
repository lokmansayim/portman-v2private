# Portman · DURUM

**Son güncelleme: 28 Eylül 2026 (İE-01).** Her oturumun son adımı bu dosyayı güncellemektir.

Canlıda çalışan akış şu: WhatsApp → hosting kanalı → VPS ajanı → Beyin ve Motor → plan PDF'i. Akış yalnız Patron modunda açık. En son 22 Eylülde gerçek mesajla doğrulandı; canlı sunucu 27–28 Eylülde okunmadı. Bu depo o sürümün (v1.1.1, `ec4e9a3`) devridir. Hedefteki "90 m² 3+1, üç seçenek" akışı henüz taslak.

Durumlar: **Taslak** yalnız belgede · **Kodlandı** kod var, testi yok ya da dar · **Test edildi** tekrarlanabilir testten geçti · **Canlıda doğrulandı** gerçek kullanımda (gerçek mesaj ya da planlı koşu) görüldü ve tarihli.

## Bu depoda ne var

| Yol | İçerik |
|---|---|
| Kökteki v1.1.1 ağacı | `lokmansayim/portman` deposunun geçmişiyle birlikte, değiştirilmeden (`ec4e9a3`, 22.09 20:12). Özetleri `SHA256SUMS`'ta. |
| `testler/referans/` | Dondurulmuş referans (`2026-09-28/`) ve `dogrula.py` |
| `testler/bilinen_hatalar/` | B1 ve B2 kırmızı testleri |
| `deneme/2026-09-23/` | 23 Eylül denemeleri ve `yeniden_kos.py` |
| `KARARLAR/` | K01–K25 ve Z-01–Z-10, her karar ayrı dosyada |

## Bileşenler

| Bileşen | Durum | Kanıt (tarih) | Kapsam sınırı |
|---|---|---|---|
| Kanal v1.1.1: WhatsApp → hosting webhook → kuyruk → gönderim | Canlıda doğrulandı | 21.09 (v1.0): 3 mesaj, 1'i bekletildi, 2 PDF okundu · 22.09 22:31: v1.1.1 paketi (`bd1ca27c…`), öz-test geçti · 22.09 22:33–38: 3 Patron mesajı yanıtlandı | Yalnız Patron modu; kuyruk hostingte bir JSON dosyası (`state.json`) |
| VPS ajanı (Natro, portman-agent v1.1.1) | Canlıda doğrulandı | 22.09 19:06: ilk gerçek İş Emri, 27 sn · 22.09 22:14: v1.1.1, `vps-health.json` | ufw etkin ama kuralları okunmadı; root parolayla SSH'ye girebiliyor (22.09 23:59) |
| Beyin: LLM çıkarımı (gpt-4o-mini), kural katmanı, varyant | Test edildi | Harness 22/22 (sabit girdiler; 28.09'da yeniden) · 22.09 22:33–38 canlı davranış testi 2/3 (B1) | B1 ve B2 açık (kırmızı test var); yalnız P6001 şablonu canlı |
| Motor v1.1.1: İş Emri → DXF → doğrulama → PDF | Test edildi | Altın testler 6×8 (41 pano, 0 cm²) ve Yan Verandalı 6×8,5 (BOM 26 kod); P6001 katalog testi (773 × 763) · 28.09: üç temiz koşuda içerik parmak izi aynı | Plan PDF'i üretir, ön onay paftası değil; canlı PDF içeriği insan gözüyle doğrulanmadı |
| Çıkarıcı: katalog DXF → İş Emri | Kodlandı | 16 planın 15'i Motor doğrulamasından geçti (22.09 ve 28.09) | P1051'de kapılar, P8501, P9501 ve P1081'de bazı açıklıklar düşüyor; P9901 desteklenmiyor; insan kabulü yok |
| Serbest aks (Motor yaması) | Kodlandı | 23.09: Tatar 80 m²'de denendi · 28.09: `yeniden_kos.py` ile yeniden koşuldu, sonuçlar aynı | Test dar: tek plan. `deneme/` altında ayrı yama; ana kodda ve canlıda değil; K16'ya bağlı |
| Vektör PDF plan okuyucu | Kodlandı | 23.09 Tatar 80: ölçek iki yöntemle %0,05 tutarlı · 28.09: `yeniden_kos.py` ile aynı | Test dar: tek plan. Deneme sürümü; el çizimi okumuyor |
| IFC4 üretimi (IfcOpenShell) | Kodlandı | 28.09 yeniden koşum (`yeniden_kos.py`): şema 0 hata, çift sayım 35/35, hacim farkı %0,0 · Yan Verandalı: Astra modeliyle 65/67 eleman, açıklık 13/13 | Tekrarlanabilir test var ama dar: iki plan. Şema doğrulaması üretim doğruluğu değildir |
| Blender modeli | Kodlandı | 28.09: `yeniden_kos.py` ile bpy 5.0.1'de yeniden kuruldu, 65 pano, BOM aynı | Test dar: tek plan; sunum içindir, hesap burada yapılmaz |
| Depo | Kodlandı | 28.09: `portman-v2private` açıldı; v1.1.1 geçmişiyle alındı; İE-01 dalı | Eski depo `lokmansayim/portman` yalnız okunuyor |
| Yapı Tanımı şeması | Taslak | Zemin, 27.09; temeli İş Emri şeması v0.1 (21.09) | Ölçü anlamları ve ürün ailesi ayrımı eksik |
| Veritabanı (Postgres + pgvector) | Taslak | — | Kurulmadı (İE-02) |
| RAG | Taslak | Araştırma notu, 21.09 | Aşama 2 sonrası |
| Model geçidi | Kodlandı | `llm.py`'de OpenAI ve Anthropic yolları var; canlıda gpt-4o-mini · 23.09 kıyas: gpt-4o-mini 6/7, gpt-6-sol 4/7 | Anthropic yolu canlı anahtarla denenmedi; hosting ayarı VPS'e yalnız arka uç, model ve zaman aşımını geçiriyor (B4) |
| PortmanBench | Taslak | Tohum: `testler/referans/` (28.09) | Uçtan uca ölçüm ve kritik hata türleri yok |
| Ön onay paketi | Taslak | Hedef format notu, 21.09 | Motor PDF'inde çalışma ön görünüşü ve basit özellik tablosu var; yan görünüş, Güncel Şablon 2024 düzeni, fiyat ve onay durumları yok |
| BOM'dan fiyat | Taslak | Fiyat MVP Excel'i · CTKBF V1.1 27.09'da incelendi, 19 bulgu | Canlı akışta fiyat yok |
| Çift doğrulama | Taslak | Tasarım, 27.09 (Z-10) | Prefabrikte ikinci motor yok |
| Kişisel veri: takma ad | Taslak | Günlüklerde numara maskeli; mesaj metni LLM'e olduğu gibi gidiyor (`llm.py`); Patron modunda yalnız Patron'un mesajları işleniyor | Takma ad ve saklama süresi yok |
| Aylık alan taraması | Canlıda doğrulandı | 27.09: ilk koşu başarılı, rapor üretildi | Sonraki koşu 1 Ekim |

## Açık riskler

- **Sızan eşleşme anahtarı (ertelendi).** Anahtar 22 Eylülde bir ekran görüntüsüyle sohbete girdi. Bilen biri OpenAI anahtarını alabilir, bekleyen işleri çekebilir ve bir işin göndericisine metin ya da PDF gönderebilir. 27 Eylülde yeniden ertelendi (Lokman): OpenAI hesabında ciddi bakiye ve otomatik ödeme yok; anahtar yeni API anahtarıyla birlikte yenilenecek. Bayilere açılmadan önce yenilenmesi şart (K17).
- **B1.** Belirsiz bir pencere isteğinde sistem soru sormak yerine İş Emri üretiyor. Kanal yalnız Patron modunda olduğu için bayiye ulaşmıyor.
- **B2.** Görüşmede zaman aşımı yok; eski taslak sessizce devralınabiliyor. Seçenekler: (a) böyle kalsın, (b) taslak N saat sonra kapansın, (c) model koduyla başlayan mesaj yeni talep sayılsın. Karar Lokman'ın.
- **Sunucu erişimi.** root parolayla SSH girişi açık; ufw kuralları okunmadı. Anahtarla girişe geçmek canlı değişikliktir, onayla yapılır.
- **İmzasız paket kanalı.** Hostinge dosya yazabilen biri VPS'te kod çalıştırabilir (K14, K25).
- **Test verisinde olası kişisel veri.** `beyin/testler/mesajlar.json` vaka 1 (bkz. `testler/referans/README.md`).

## Sıradaki iş: İE-02 · Kalıcı akış

Mesaj, bayi, proje, revizyon ve iş tabloları (Postgres ve göç altyapısı). Tekrar gelen mesaj, yarım iş, yeniden başlatma, başka bayinin proje kimliği ve eski revizyon butonu testleri. B1 düzeltmesi ve B2 kararı. `kos.py` sır taramasındaki telefon kalıbının sınırlanması (bugün `deneme/` altındaki IFC koordinatlarını numara sanıyor). Test verisindeki olası müşteri adının takma adla değiştirilmesi. Kabul şartı: `testler/referans/dogrula.py` referansla aynı kalır (kod değişikliği serbest; referans girdiler, dondurulan 22 Beyin vakası, Motor sayıları ve parmak izleri aynı; yeni Beyin vakası sona eklenebilir). Vaka 1'deki takma ad gibi bilerek yapılan bir değişiklik referansı değiştirirse `dogrula.py --dondur` ile gerekçeli, tarihli yeni referans alınır; eskisi silinmez.

Lokman'ın açık kararları: B2 (a/b/c), K16 (a/b), K3 ve K4, Z-03 ve Z-06 eşikleri. Ayrıntı: `KARARLAR/README.md`.

## Kaynaklar

- Zemin belgesi (sekmeler: Zemin, Güncel durum, Düzeltme kaydı, İlk iş emri, CTKBF): https://claude.ai/code/artifact/65844cef-e6c5-4a5d-b714-ee003c57fe5b
- Masaüstündeki "Claude Portman Çalışması" klasörü: DURUM.md (23.09 00:35), `07_Denetim/` (22.09 20:30), `08_VPS/hosting_paket/`, 10–13 numaralı klasörler (23.09).
