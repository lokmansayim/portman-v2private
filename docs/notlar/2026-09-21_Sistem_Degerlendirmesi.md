# Portman — canlı sistemin değerlendirmesi ve hedef mimari önerisi

Tarih: 21 Eylül 2026, 17:15. Dayanak: bugünkü canlı izleme (hosting kayıtları + OpenAI Platform izleri), 20 Eylül paketi kodları,
21 Eylül raporu. Sohbet botu (`developer/ai.php` → `otomatikYanit`) Lokman'ın talimatıyla **Portman sisteminin parçası sayılmıyor**;
değerlendirme dışında tutuldu (bkz. §4). Canlıda değişiklik yapılmadı.

## 1. Canlı sistem tek cümleyle
Meta WhatsApp → paylaşımlı PHP hosting'de imzalı webhook (kuyruk + üç "görev" modülü + sohbet botu) → dakikalık cron'lar
(PHP orkestratör + Python üretici) → sabit 6×8 çizimi ya hosting'de (Görev 2, 22 sn, 0 token) ya da OpenAI-hosted ortamda
bir LLM ajanına `python3 run_cloud.py` yazdırarak (Görev 3, ~90 sn + 200–300 bin token) → PDF → Meta medya → telefon.

## 2. İyi bir yazılımcı böyle mi kurardı? — dürüst cevap
**Doğru yapılmış olanlar (korunmalı):** imza doğrulama; mesaj kimliğiyle tekrar-önleme; belirsiz POST'u otomatik tekrarlamama;
her modülde kapatma anahtarı, yedek ve geri alma notu; kaynak hash doğrulaması; DXF'i yeniden açıp kontrol etmeden PDF basmama;
uçtan uca kanıt zinciri (wamid → iş → oturum → artifact → media → giden wamid → read); anahtarların koda yazılmaması;
alma (webhook) ile işleme (cron) ayrımı. Bu "tesisat" bir pilot için özenli.

**Yapısal hatalar (bir ürün için taşınamaz):**
1. **LLM yürütme yolunda, karar değeri sıfır.** Görev 3'te gpt-6-astra'nın tek işi hazır komutu çalıştırmak; bunun için ortam
   ayağa kalkıyor, ajan README/manifest/kodu okuyor (54 sn), iki keşif komutu boşa gidiyor, 200 bin token gidiyor. Aynı iş Görev 2'de
   hosting cron'unda 22 sn'de, tokensiz, telefon-onaylı çalışıyor. İyi bir mühendis deterministik üreticiyi düz bir işçiye koyar,
   LLM'i yalnız dil gereken yere (talebi anlama, eksik bilgiyi sorma, açıklama) alır.
2. **Ürün = iki sabit cümle.** Talep modeli yok; birebir eşleşmeyen her şey sohbet botuna düşüyor ("yapamam"). Doğal dil denemesi
   durumsuz webhook'ta netleştirme devamı kurulamadığı için bırakılmış. Gönderen başına konuşma durumu tutan bir kayıt olmadan
   "eksik bilgiyi sor" akışı kurulamaz.
3. **Üretici sabit.** `house.py` onaylı DXF'i yeniden üretir; parametre almaz. 37 model, varyant, serbest yerleşim canlıda yok.
   (Bulut çalışma alanındaki Motor v1.1 bu boşluğun adayı; iki altın test + BOM eşliği geçti.)
4. **Kopyala-yapıştır büyüme.** Üç görev, her biri kendi settings/state/health/lock dosyası ve webhook'ta zincirlenmiş kendi
   `capture` fonksiyonuyla; kapalı doğal dil modülü her dakika yükleniyor. Pilotta kabul edilir; ürün için tek giriş → tek iş
   tablosu → tek işçi → takılabilir üreticiler olmalı.
5. **Durum JSON dosyalarında (flock).** Tek kullanıcı, tek eşzamanlı iş için yeterli; 12 bayi × 15 teklif/gün, sorgu, geçmiş,
   revizyon, onay için değil. Hosting'de 1 veritabanı hakkı var, kullanılmıyor.
6. **Beta API bağımlılığı.** `OpenAI-Beta: agents=v1`; sözleşme değişirse Görev 3 kırılır; her işte yeni oturum + ortam kurulumu.
7. **Gözlemlenebilirlik.** `worker.log` boş, `error_log` hedefi bilinmiyor, uyarı yok; yalnız health dosyaları.
8. **Kimlik.** Patron numarası kodda sabit; panelde kişi/firma modeli var ama görevler kullanmıyor. Çok bayi için bayi kimliği
   → proje → revizyon zinciri kurulmalı.

Not: küçük kusur — `run_cloud.py` `incoming_timestamp`'a mesaj zamanı yerine çalışma zamanı yazıyor.

## 3. Token sorunu — teşhis ve tavsiye
Kanıt: 5 oturum ≈ 1,31 M token; bugünkü iş 200.536 = 198.888 girdi (157.577 önbellekli) + 1.648 çıktı. Yani maliyet düşünme
değil, **bağlam**: ortam dosya listeleri, ajanın `cat` ettiği README/manifest/kod, araç çıktıları, tekrarlanan sistem talimatı.
- **Tavsiye A (asıl çözüm):** LLM'i çizimden çıkar. Üretici (bugün `house.py`, yarın Motor) düz bir işçide koşar — Görev 2 yolu
  hazır ve kanıtlı. LLM yalnız "metin → İş Emri JSON veya soru" adımında, dar şemayla, dosya/kabuk erişimi olmadan: talep başına
  **3–8 bin token** (≈ %97 azalma), süre 1–3 sn. OpenAI ajanı silinmez; kapatılıp yedek olarak durur.
- **Tavsiye B (geçici yama, önerilmez):** ajan talimatını "yalnız şu komutu çalıştır, dosya okuma" diye sıkılaştırıp reasoning'i
  düşürmek; iz gösteriyor ki ajan yine keşif yapıyor; en iyi ihtimalle 50–100 bin'e iner, sorun kalır.
- Motorun koşacağı yer: **(1)** hosting Python cron (kanıtlı, ücretsiz; günde ≤15 iş için yeter; dakikalık cron gecikmesi var,
  Blender yok) → **(2)** küçük VPS/konteyner (≈ €5–10/ay; kuyruk + veritabanı + Blender headless + eşzamanlılık). Başlangıç (1),
  3D/BOM aşamasında (2).

## 4. Sohbet botu
Bugün 444 80 56'ya yazan herkese `otomatikYanit` otomatik cevap veriyor; Portman'ın sahiplenmediği her mesaj oraya düşüyor.
Hedef mimaride bot yok: kayıtlı bayiden gelen her mesaj **talep alımına** gider (İş Emri'ni doldur / eksikse sor), kayıtsız
numara Lokman'a yönlendirilir (kural: "sadece kayıtlı olanlar; bilinmeyenlere benimle iletişime geçsin"). Bugünkü bot, alım katmanı
canlıya çıkana kadar hattı "cevapsız bırakmama" işlevi görüyor; kapatma kararı Lokman'ın (ayar değişikliği — istenirse yapılır).

## 5. Kurmaya çalıştığımız sistem — benim anladığım (doğrula)
PortatifEv'in **kayıtlı bayilerinin** WhatsApp'tan gönderdiği talebi (metin, kroki fotoğrafı, PDF; katalog modeli ya da alan/ölçü
tarifi) **doğrulanmış bir İş Emri'ne** çeviren (eksikse soran, en fazla 4 revizyon, sonra mühendise); **kurallı, deterministik
geometri motoruyla** pano gridinde planı üretip **ön onay paftasını** (2D ölçülü plan + alanlar + görünüş; ileride 3D/Blender
görseli) bayiye dakikalar içinde geri gönderen; bayi onayından sonra **aynı modelden** BOM/yükleme listesi (12 grup, İkranur
biçimi), tarihli fiyat anlık görüntüsü ve teklif üreten; her adımı kayıtlı, onay kapılı, çok bayili bir **CPQ**. Yerel
bilgisayar/AutoCAD günlük işte yok; LLM yalnız anlama/soru/açıklama, hesap ve geometri kodda; kurallar sürümlü ve insan onaylı;
prefabrik önce, çelik ayrı kurallarla sonra; katalog kopyası değil üretici (5×20'den 10×10'a kadar kat planları).
**Emin olmadıklarım:** ön onay paketinin tam içeriği (3D görsel şart mı, fiyat aralığı verilecek mi); Sezgisel CRM ile ilişkisi
(Portman modül mü, ayrı ürün mü — bayi/proje/revizyon kayıtları nerede yaşayacak); bayiye özel kurallar; motorun koşacağı yer.

## 6. Hedef mimari v1 (sade, kurulabilir) — sırayla
1. **Alım:** mevcut imzalı webhook → tek iş tablosu (bayi, proje, revizyon, durum) — DB (hosting'in 1 veritabanı hakkı yeter).
2. **Anlama:** LLM, dar şema (İş Emri) + gönderen başına konuşma durumu; çıktı ya İş Emri ya WhatsApp'tan tek bir soru.
3. **Motor:** deterministik üretici (Motor v1.1 çizgisi) → İş Emri → DXF+PDF (+ 3D) → yeniden aç, doğrula, kaydet.
4. **Teslim:** mevcut medya göndericisi + sent/delivered/read izi (zaten var).
5. **Onay:** bayi "onay" → revizyon kilidi → BOM/fiyat/teklif aşaması (aynı modelden).
Beklenen: talep → pafta 1 dk altı, talep başına birkaç bin token, eşzamanlı işler DB kuyruğuyla.
