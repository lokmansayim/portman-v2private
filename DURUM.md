# Portman · DURUM

**Son güncelleme: 28 Eylül 2026 (İE-01 birleştirildi; İE-02 sürüyor: B1, B2 ve Postgres kalıcı akışı `ie-02` dalında).** Her oturumun son adımı bu dosyayı güncellemektir.

Canlıda çalışan akış şu: WhatsApp → hosting kanalı → VPS ajanı → Beyin ve Motor → plan PDF'i. Akış yalnız Patron modunda açık. En son 22 Eylülde gerçek mesajla doğrulandı; canlı sunucu 27–28 Eylülde okunmadı. Bu depo o sürümün (v1.1.1, `ec4e9a3`) devridir. Hedefteki "90 m² 3+1, üç seçenek" akışı henüz taslak.

Durumlar: **Taslak** yalnız belgede · **Kodlandı** kod var, testi yok ya da dar · **Test edildi** tekrarlanabilir testten geçti · **Canlıda doğrulandı** gerçek kullanımda (gerçek mesaj ya da planlı koşu) görüldü ve tarihli.

## Bu depoda ne var

| Yol | İçerik |
|---|---|
| Kökteki v1.1.1 ağacı | `lokmansayim/portman` deposunun geçmişiyle birlikte, değiştirilmeden (`ec4e9a3`, 22.09 20:12). Özetleri `SHA256SUMS`'ta. |
| `testler/referans/` | Dondurulmuş referanslar (`2026-09-28/`, `2026-09-28b/`) ve `dogrula.py` |
| `testler/kalici/` | İE-02 kalıcı akış testleri (gerçek Postgres; T1–T10) ve kabul gösterimi |
| `docs/is_emirleri/` | İE-02 iş emri |
| `testler/bilinen_hatalar/` | B1 ve B2 testleri (ikisi de `ie-02` dalında düzeltildi) |
| `deneme/2026-09-23/` | 23 Eylül denemeleri ve `yeniden_kos.py` |
| `KARARLAR/` | K01–K25 ve Z-01–Z-10, her karar ayrı dosyada |

## Bileşenler

| Bileşen | Durum | Kanıt (tarih) | Kapsam sınırı |
|---|---|---|---|
| Kanal v1.1.1: WhatsApp → hosting webhook → kuyruk → gönderim | Canlıda doğrulandı | 21.09 (v1.0): 3 mesaj, 1'i bekletildi, 2 PDF okundu · 22.09 22:31: v1.1.1 paketi (`bd1ca27c…`), öz-test geçti · 22.09 22:33–38: 3 Patron mesajı yanıtlandı | Yalnız Patron modu; kuyruk hostingte bir JSON dosyası (`state.json`) |
| VPS ajanı (Natro, portman-agent v1.1.1) | Canlıda doğrulandı | 22.09 19:06: ilk gerçek İş Emri, 27 sn · 22.09 22:14: v1.1.1, `vps-health.json` | ufw etkin ama kuralları okunmadı; root parolayla SSH'ye girebiliyor (22.09 23:59) |
| Beyin: LLM çıkarımı (gpt-4o-mini), kural katmanı, varyant | Test edildi | Harness 22/22 (sabit girdiler; 28.09'da yeniden) · 22.09 22:33–38 canlı davranış testi 2/3 (B1) | B1 ve B2 `ie-02` dalında düzeltildi (B2: D-01), canlıda değil; yalnız P6001 şablonu canlı |
| Motor v1.1.1: İş Emri → DXF → doğrulama → PDF | Test edildi | Altın testler 6×8 (41 pano, 0 cm²) ve Yan Verandalı 6×8,5 (BOM 26 kod); P6001 katalog testi (773 × 763) · 28.09: üç temiz koşuda içerik parmak izi aynı | Plan PDF'i üretir, ön onay paftası değil; canlı PDF içeriği insan gözüyle doğrulanmadı |
| Çıkarıcı: katalog DXF → İş Emri | Kodlandı | 16 planın 15'i Motor doğrulamasından geçti (22.09 ve 28.09) | P1051'de kapılar, P8501, P9501 ve P1081'de bazı açıklıklar düşüyor; P9901 desteklenmiyor; insan kabulü yok |
| Serbest aks (Motor yaması) | Kodlandı | 23.09: Tatar 80 m²'de denendi · 28.09: `yeniden_kos.py` ile yeniden koşuldu, sonuçlar aynı | Test dar: tek plan. `deneme/` altında ayrı yama; ana kodda ve canlıda değil; K16'ya bağlı |
| Vektör PDF plan okuyucu | Kodlandı | 23.09 Tatar 80: ölçek iki yöntemle %0,05 tutarlı · 28.09: `yeniden_kos.py` ile aynı | Test dar: tek plan. Deneme sürümü; el çizimi okumuyor |
| IFC4 üretimi (IfcOpenShell) | Kodlandı | 28.09 yeniden koşum (`yeniden_kos.py`): şema 0 hata, çift sayım 35/35, hacim farkı %0,0 · Yan Verandalı: Astra modeliyle 65/67 eleman, açıklık 13/13 | Tekrarlanabilir test var ama dar: iki plan. Şema doğrulaması üretim doğruluğu değildir |
| Blender modeli | Kodlandı | 28.09: `yeniden_kos.py` ile bpy 5.0.1'de yeniden kuruldu, 65 pano, BOM aynı | Test dar: tek plan; sunum içindir, hesap burada yapılmaz |
| Depo | Kodlandı | 28.09: `portman-v2private` açıldı; v1.1.1 geçmişiyle alındı; İE-01, Lokman'ın onayıyla `main`'e birleştirildi | Eski depo `lokmansayim/portman` yalnız okunuyor |
| Yapı Tanımı şeması | Taslak | Zemin, 27.09; temeli İş Emri şeması v0.1 (21.09) | Ölçü anlamları ve ürün ailesi ayrımı eksik |
| Veritabanı: kalıcı konuşma ve iş akışı (Postgres) | Test edildi | 28.09: `testler/kalici/`, gerçek Postgres 16'da 135 test geçti. Kabul gösterimi 10/10 (simülasyon: WhatsApp ve LLM sahte). Ajanın kalıcı modu sahte hosting ile sınandı (600 sn süpürme ve hata enjeksiyonu dahil). | Yalnız izole ortamda; canlıda yok. Gerçek PHP hattı (`feature.php` `context_id`, `api.php` v1.2) `portman/lib.php` olmadan koşulamadı. Yer: mevcut VPS (D-04). Canlıya bağlama planı ve onay kapıları: `docs/is_emirleri/IE-02-canli.md`. pgvector yok (RAG'la gelir). |
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
- **B1.** Belirsiz bir pencere isteğinde sistem soru sormak yerine İş Emri üretiyor. Kanal yalnız Patron modunda olduğu için bayiye ulaşmıyor. Düzeltme `ie-02` dalında, testleri geçiyor; canlıda değil.
- **B2.** Görüşmede zaman aşımı yok; eski taslak sessizce devralınabiliyor. Karar verildi (D-01, 28.09): taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar. Düzeltme `ie-02` dalında, testleri geçiyor; canlıda değil.
- **Sunucu erişimi.** root parolayla SSH girişi açık; ufw kuralları okunmadı. Anahtarla girişe geçmek canlı değişikliktir, onayla yapılır.
- **İmzasız paket kanalı.** Hostinge dosya yazabilen biri VPS'te kod çalıştırabilir (K14, K25).
- **Test verisinde olası kişisel veri.** `beyin/testler/mesajlar.json` vaka 1 (bkz. `testler/referans/README.md`).

## Sıradaki iş: İE-02 · Kalıcı akış

Dal: `ie-02`. İş emri: `docs/is_emirleri/IE-02.md`.

Yapıldı:
- B2 düzeltmesi (D-01) ve B1 düzeltmesi;
- referansın PDF içeriğini izlemesi (D-02, `2026-09-28b`);
- Postgres üzerinde kalıcı akış (D-03, D-04);
- ajanın kalıcı modu, hosting bağlantısı (`api.php` v1.2, `feature.php` `context_id`), göç 002 (kabul ve teslim ayrı, onay zinciri), VPS kurulum betiği;
- dördüncü bağımsız incelemenin düzeltmeleri: Postgres kesintisinde mesaj kaybı yok, sonuç claim'den önce verilir, D-03 hosting'in 600 sn'sine sığar, hosting hata sınıfları, `worker=off` ile boşaltma, eşitleme ve onay sınırı, yeniden girişte boş veritabanı (`test_hosting_devri.py`);
- beşinci bağımsız incelemenin düzeltmeleri: bir işin devir hatası ötekini bekletmez, geçici hatada cevap atılmaz (uyarı), Postgres'e yazılamayan mesaj kuyruğu tıkamaz, açık iş varken yeni mesaj alınmaz, Meta'nın iletemediği metin uyarıya düşer, WhatsApp kimliği (numarayı içerir) günlüğe ve kanıt çıktısına yalnız özetiyle yazılır.

Kalan (sırayla, her biri ayrı onayla; `docs/is_emirleri/IE-02-canli.md`):
- A: canlı sürümün salt okunur doğrulanması;
- B: `lib.php` kopyasıyla gerçek PHP testleri;
- C: sızan anahtarın yenilenmesi;
- D: VPS'e Postgres;
- E: PHP ve paket yüklemesi;
- F: kalıcı moda geçiş;
- G: gerçek WhatsApp ve LLM ile kabul gösterimi.

G tamamlanınca İE-02 kapanır.

Canlı dışı kalan: `kos.py` sır taramasındaki telefon kalıbı; test verisinde takma ad.

Sonraki iş adayı (İE-03): küçük, kaynaklı, sürüm ve yetki ayrımlı RAG.

Lokman'ın açık kararları: K16 (a/b), K3 ve K4, Z-03 ve Z-06 eşikleri. Ayrıntı: `KARARLAR/README.md`.

## Kaynaklar

- Zemin belgesi (sekmeler: Zemin, Güncel durum, Düzeltme kaydı, İlk iş emri, CTKBF): https://claude.ai/code/artifact/65844cef-e6c5-4a5d-b714-ee003c57fe5b
- Masaüstündeki "Claude Portman Çalışması" klasörü: DURUM.md (23.09 00:35), `07_Denetim/` (22.09 20:30), `08_VPS/hosting_paket/`, 10–13 numaralı klasörler (23.09).
