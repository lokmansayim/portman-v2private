# Portman · DURUM

**Son güncelleme: 29 Eylül 2026 20:05 (İE-02 kapı G yapıldı, AÇIK: 7 adımın 6'sı geçti; B1 cevabı Opus'la soruya bağlanmadı ve r03 numarası çıktı. Düzeltme önerisi onay bekliyor).** Her oturumun son adımı bu dosyayı güncellemektir.

Canlıda çalışan akış şu: WhatsApp → hosting kanalı → VPS ajanı → Beyin ve Motor → plan PDF'i. Akış yalnız Patron modunda açık. En son 22 Eylülde gerçek mesajla doğrulandı. 28–29 Eylülde canlıya v1.2 kuruldu (dosya modu) ve LLM Claude Opus 5.5'e geçti; 29.09 01:16'da gerçek bir Patron mesajıyla denendi (r01 PDF'i telefona geldi). 29.09 18:59'dan beri ajan kalıcı modda: konuşma ve iş durumu Postgres'te (kapı F); 29.09 19:27–19:56'da kalıcı modda 5 gerçek Patron mesajı işlendi (kapı G). Depo, v1.1.1'in (`ec4e9a3`) devridir. Hedefteki "90 m² 3+1, üç seçenek" akışı henüz taslak.

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
| Kanal v1.1.1: WhatsApp → hosting webhook → kuyruk → gönderim | Canlıda doğrulandı | 21.09 (v1.0): 3 mesaj, 1'i bekletildi, 2 PDF okundu · 22.09 22:31: v1.1.1 paketi (`bd1ca27c…`), öz-test geçti · 22.09 22:33–38: 3 Patron mesajı yanıtlandı · 28.09 (kapı A, salt okunur): VPS'teki uygulama (48/48 dosya), hosting'in dağıttığı paket ve hosting'teki `feature.php` ile `api.php` v1.1.1 ile birebir (tam hash); servis 25.09'dan beri kesintisiz · 28.09 23:31 (kapı E): hosting `feature.php` ve `api.php` v1.2, paket v1.2; 29.09 00:47: Opus paketi `f2bff20a…`, öz-test geçti · 29.09 01:16: 1 Patron mesajı → iş emri r01, 25,9 sn, metin + PDF telefona ulaştı | Yalnız Patron modu; kuyruk hostingte bir JSON dosyası (`state.json`) |
| VPS ajanı (Natro, portman-agent; 28.09'dan beri v1.2) | Canlıda doğrulandı | 22.09 19:06: ilk gerçek İş Emri, 27 sn · 22.09 22:14: v1.1.1, `vps-health.json` · 29.09 00:57: v1.2, dosya modunda, 50/50 dosya paketle aynı · 29.09 18:59: kalıcı mod (Postgres), 19:09'da sağlıklı | ufw etkin ama kuralları okunmadı; root parolayla SSH'ye girebiliyor (22.09 23:59) |
| Beyin: LLM çıkarımı (29.09'dan beri Claude Opus 5.5; önce gpt-4o-mini), kural katmanı, varyant | Test edildi | Harness 22/22 (sabit girdiler; 28.09'da yeniden) · 22.09 22:33–38 canlı davranış testi 2/3 (B1) | B1 ve B2 `ie-02` dalında düzeltildi (B2: D-01), canlıda değil; yalnız P6001 şablonu canlı |
| Motor v1.1.1: İş Emri → DXF → doğrulama → PDF | Test edildi | Altın testler 6×8 (41 pano, 0 cm²) ve Yan Verandalı 6×8,5 (BOM 26 kod); P6001 katalog testi (773 × 763) · 28.09: üç temiz koşuda içerik parmak izi aynı | Plan PDF'i üretir, ön onay paftası değil; canlı PDF içeriği insan gözüyle doğrulanmadı |
| Çıkarıcı: katalog DXF → İş Emri | Kodlandı | 16 planın 15'i Motor doğrulamasından geçti (22.09 ve 28.09) | P1051'de kapılar, P8501, P9501 ve P1081'de bazı açıklıklar düşüyor; P9901 desteklenmiyor; insan kabulü yok |
| Serbest aks (Motor yaması) | Kodlandı | 23.09: Tatar 80 m²'de denendi · 28.09: `yeniden_kos.py` ile yeniden koşuldu, sonuçlar aynı | Test dar: tek plan. `deneme/` altında ayrı yama; ana kodda ve canlıda değil; K16'ya bağlı |
| Vektör PDF plan okuyucu | Kodlandı | 23.09 Tatar 80: ölçek iki yöntemle %0,05 tutarlı · 28.09: `yeniden_kos.py` ile aynı | Test dar: tek plan. Deneme sürümü; el çizimi okumuyor |
| IFC4 üretimi (IfcOpenShell) | Kodlandı | 28.09 yeniden koşum (`yeniden_kos.py`): şema 0 hata, çift sayım 35/35, hacim farkı %0,0 · Yan Verandalı: Astra modeliyle 65/67 eleman, açıklık 13/13 | Tekrarlanabilir test var ama dar: iki plan. Şema doğrulaması üretim doğruluğu değildir |
| Blender modeli | Kodlandı | 28.09: `yeniden_kos.py` ile bpy 5.0.1'de yeniden kuruldu, 65 pano, BOM aynı | Test dar: tek plan; sunum içindir, hesap burada yapılmaz |
| Depo | Kodlandı | 28.09: `portman-v2private` açıldı; v1.1.1 geçmişiyle alındı; İE-01, Lokman'ın onayıyla `main`'e birleştirildi | Eski depo `lokmansayim/portman` yalnız okunuyor |
| Yapı Tanımı şeması | Taslak | Zemin, 27.09; temeli İş Emri şeması v0.1 (21.09) | Ölçü anlamları ve ürün ailesi ayrımı eksik |
| Veritabanı: kalıcı konuşma ve iş akışı (Postgres) | Canlıda (işlem yok) | 29.09 kapı F: canlı VPS'te göçler 1–2; hosting'ten 1 konuşma, 14 mesaj/iş aktarıldı, kaynak ↔ Postgres 15/15 aynı; ajan 18:59'dan beri kalıcı modda, `worker` vps. 28.09: `testler/kalici/`, gerçek Postgres 16'da 185 test geçti. Kabul gösterimi 10/10 (simülasyon: WhatsApp ve LLM sahte). Ajanın kalıcı modu sahte hosting ile sınandı (600 sn süpürme ve hata enjeksiyonu dahil). | Kalıcı modda henüz gerçek mesaj işlenmedi (G'de görülür). Geçişten önceki planlar `projeler`/`revizyonlar`'da yok (tasarım gereği; onayları eski yoldan). İlk canlı veri yedeği 30.09 03:17 cron'u. Yer: mevcut VPS (D-04). Canlıya bağlama planı ve onay kapıları: `docs/is_emirleri/IE-02-canli.md`. pgvector yok (RAG'la gelir). |
| RAG | Taslak | Araştırma notu, 21.09 | Aşama 2 sonrası |
| Model geçidi | Canlıda | `llm.py`'de OpenAI ve Anthropic yolları var; 29.09'dan beri canlıda `claude-opus-5-5` (K10), öz-test geçti (5.309 + 488 token, ~0,031 $) · 23.09 kıyas: gpt-4o-mini 6/7, gpt-6-sol 4/7 | 29.09 01:16'da tek gerçek Patron mesajında 5.280 + 337 token, ~0,028 $; B1 vakasında ölçülmedi. Claude anahtarı VPS `agent.env`'de ve hosting `claude_api.json`'da; bilinen son kullanma 29.10. Hosting ayarı VPS'e yalnız arka uç, model ve zaman aşımını geçiriyor (B4) |
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
- altıncı tur (aynı inceleyicinin yeniden denetimi): devir hatasında hosting'e ulaşılabiliyor mu diye sorulur; işe özgü hatada aralıklı yeniden deneme (öteki işler beklemez), süpürme sınırına yaklaşan sonuç claim'den önce denenir, süpürme ancak hosting'e sorularak kabul edilir; yeniden kuyruğa konan mesajın süresi yeniden başlar.
- kapı D'nin ön koşulları (28.09 akşam, Lokman): yedeklerin otomatik silinmesi ayrı tercih, varsayılanı kapalı; geri yükleme denemesi yalnız kendi açıp işaretlediği veritabanını siler; yerel bağlantı şartı sağlanmıyorsa kurulum durur (`test_pg_kurulum.py`, 27 test);
- kapı A (28.09, salt okunur): canlı sürüm v1.1.1, beklenenle fark yok (VPS'teki uygulama, hosting paketi, hosting `feature.php` ve `api.php` tam hash'le); eşleşme anahtarı iki tarafta aynı; sızan anahtar büyük olasılıkla hâlâ etkin, kanıtlanmadı.
- kapı B (28.09): gerçek `lib.php`'nin temiz kopyasıyla (7. satırdaki iki numara sahte rakamlarla değiştirildi; orijinal Mac'ten çıkmadı) dört PHP takımı PHP 8.2.30'da ve 8.4'te 30/30, 16/16, 19/19, 18/18; ağsız ortamda, PHP ağ işlevleri kapalıyken de aynı.
- kuralı (Lokman, 28.09): dışarı aktarımda kişi adları da maskelenir; B'nin sınırlamaları kayıtta: medya indirme yolu sınanmadı, temiz kopyada bir ön ad kaldı.
- kapı C (28.09): eşleşme anahtarı (`3173020445c2` → `9238aa8aadce`) ve OpenAI anahtarı (`0acef17e0f05` → `4cf00ec74492`) yenilendi; eskileri hosting'te ve OpenAI'de 401; eski anahtarların kopyası kalmadı (`vps/kapi_c.py`, adımları Lokman yürüttü).
- kapı D (28.09): VPS'e PostgreSQL 16.15, yalnız yerel bağlantı; `portman` rolü ve veritabanı (parolasız peer); psycopg 3.3.6; günlük yedek 03:17, otomatik silme kapalı; yedek ve geri yükleme denemesi geçti; ajan yeniden başlamadı, dosya modunda.
- kapı E (28–29.09, kapandı):
  - `feature.php` ve `api.php` v1.2 ile paket yüklendi; ajan `vps-agent-v1.2`, dosya modunda.
  - Öz-test OpenAI'de kredi bitince (429) geçmedi. Lokman Claude'a geçişi istedi ve Opus 5.5'i seçti.
  - Geçişi başka bir ajan (Codex) yaptı; Portman çıkarımı ve bayi botu Opus 5.5'te. Asistan dosyalardan doğruladı; canlı `llm.py`, `ai.php` ve `claude_api.php` depoda (`hosting/`).
  - Öz-test Opus'la geçti. Opus maliyeti bildirildikten sonra Lokman'ın gönderdiği tek Patron mesajı ("Yeni talep: P6001 aynalı olsun") iş emri r01 üretti; metin + PDF telefona ulaştı. Sayaç: LLM 5/6, WhatsApp 2/6; Claude toplamı ~0,090 $.
- kapı F (29.09 18:14–19:10, kapandı):
  - `worker` off → boşalma → hosting ve VPS yedekleri (Mac kopyaları aynı özette) → göç ve içe aktarma (1 konuşma, 14 mesaj/iş) → kaynak ↔ Postgres 15/15 aynı → kalıcı mod (18:59) → kuyruk boş → `worker` vps.
  - E projesinin r01'i konuşma durumunda, iş sonucunda ve PDF'te korundu. Hosting yedeğinde E'nin iki mesajının Meta durumu `read`.
  - Model, anahtar ve paket değişmedi; LLM ya da WhatsApp çağrısı yapılmadı.
  - İki betik sorunu (sudo'nun girdiyi yutması; karşılaştırmanın PDF'i taşınmayan klasörde araması) veriye dokunmadı; düzeltildi, testlendi.
  - Kişisel veri içeren geçici kopyalar VPS'te, hosting'te ve Mac'te duruyor; silinmeleri ayrı onayla.

Kalan (sırayla, her biri ayrı onayla; `docs/is_emirleri/IE-02-canli.md`):
- G (29.09 19:25–19:59, açık): 5 Patron mesajı; 5 LLM çağrısı, 26.731 + 1.381 token, 0,1345 $; 7 giden mesaj, hepsi okundu. Kabul: yeniden başlatmadan sonra soru kayıtlı, eski revizyon onayı reddedildi, güncel onay kabul edildi, tekrar gelen mesaj ikinci iş açmadı. Açık: G-1 kısa "değiştir" cevabı soruya bağlanmadı (`dustu`), G-2 r02 yerine r03, G-3 gerekçede yinelenen not. Pencere değişikliği çizimde doğru (Lokman). Yedekler öncesi ve sonrası Mac'te.

G tamamlanınca İE-02 kapanır.

Canlı dışı kalan: `kos.py` sır taramasındaki telefon kalıbı; test verisinde takma ad.

Sonraki iş adayı (İE-03): küçük, kaynaklı, sürüm ve yetki ayrımlı RAG.

Lokman'ın açık kararları: K16 (a/b), K3 ve K4, Z-03 ve Z-06 eşikleri. Ayrıntı: `KARARLAR/README.md`.

## Kaynaklar

- Zemin belgesi (sekmeler: Zemin, Güncel durum, Düzeltme kaydı, İlk iş emri, CTKBF): https://claude.ai/code/artifact/65844cef-e6c5-4a5d-b714-ee003c57fe5b
- Masaüstündeki "Claude Portman Çalışması" klasörü: DURUM.md (23.09 00:35), `07_Denetim/` (22.09 20:30), `08_VPS/hosting_paket/`, 10–13 numaralı klasörler (23.09).
