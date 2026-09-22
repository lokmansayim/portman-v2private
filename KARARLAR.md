# KARARLAR — Portman karar günlüğü

Biçim: tarih · karar · gerekçe · kim · (geçersiz kılan karar varsa)

## 2026-09-22
- **VPS: Natro XCloud Pro (4 vCPU / 8 GB / 200 GB, Ubuntu 24.04, aylık 29,99 $).** Gerekçe: hosting LVE 1 GB bellek sınırı (iki Python süreci aynı anda PyMuPDF yükleyince MemoryError); Türkiye'de sunucu → KVKK yurt dışı aktarım sorunu yok; üst segment: paralel iş, MySQL, ileride Blender/görsel için pay. DigitalOcean değerlendirildi: aynı sınıf 2–2,5 kat pahalı ve veri merkezi yurt dışında. — Lokman (öncelik sırası: doğruluk > fiyat > hız)
- **Tek depo: GitHub `lokmansayim/portman` (özel).** Kod, kural sürümü, şema, testler, karar günlüğü burada. — Lokman
- **Mimari (Astra ile uzlaşı): LLM anlar → kod karar verir → Motor çizer → insan onaylar.** Tek/sınırlı LLM çağrısı, yapılandırılmış çıktı, alan başına kaynak; ajan döngüsü yok. Ayrıntı: docs/notlar/2026-09-22_Astra_Elestirisi_Degerlendirme.md
- **Katalog planları çıkarıcıyla okunur, elle kodlanmaz.** `motor/cikarici.py` — aks tanıma; artıklar raporlanır, sessiz yuvarlama yok. P6001 altın test: mahaller 5/5, açıklıklar 7/9 şablonla eşit; 2 fark (menteşe) kaynak çizim lehine (şablon hatalıydı).
- **Bulgu (karar bekliyor):** 16 katalog planının yalnız ~7'si 125,5 modülüne oturuyor (P6001, P6501↻, P6701, P7401↻, P9201↻, P9401, P1051, P1081; ↻ = 90° döndürülerek). Diğerleri (P7001, P7601, P8201, P8501, P9901, P1121, P3701) dış ölçüde 4–23 cm artık; iç bölmeler çoğunda modül dışı. Seçenekler: (a) katalog planlarını modüle uyarlayıp yeniden onaylatmak, (b) Motor'a serbest aks aralığı (ruhsat ölçüsü) eklemek. — Ubeydullah + Lokman
- **Bulgu (kural sorusu):** çizimlerde pencereler oda duvarının ortasında, Motor pano ortasına koyuyor (31–34 cm fark). İç yatay duvarlar çizimde aks+2 cm. Üretim kuralı hangisi? — Ubeydullah
- **Katalog dışı pencere ölçüleri** çizimlerde var: 180×180 (P8501, P1081), 200×200 / 400×200 (P9901), 90×180 (P7601), 105×170 (P8201). Motor v1 yalnız 120×120 / 120×180 / 60×40. Kural tablosuna eklenecek. — Ubeydullah
- **VPS mimarisi: hosting = kontrol düzlemi, VPS = üretici.** VPS ajanı hostinge yalnız dışarıdan bağlanır (`developer/kanal_api.php`, eşleşme anahtarı `kanal/api_token.txt`); WhatsApp anahtarı VPS'e gitmez; gönderim yalnız hosting cron tick'i; `settings.worker` tek anahtarla geri dönüş. Yerel uçtan uca test 19/19. İsteğe bağlı komut kanalı (`settings.vps_komut: true` iken hostingteki `kanal/komutlar/<id>.json` VPS'te `portman` kullanıcısıyla çalışır, sonucu `<id>.sonuc.json`, her adım vps.log'da) — kapalı başlar, Lokman açar. — Claude, Lokman onayı ile kurulacak

## 2026-09-21
- **Dış kapı 90 cm** (kaynak sembol 97/100'den ölçeklendi) — çalışma kabulü. — Claude, onay bekler
- **Kanal v1 canlı, Patron modu** (`mode: patron`, `dry_run: false`); Görev 2 Python cron'u silindi (bellek). — Lokman
- **Öz-testler hiçbir zaman WhatsApp mesajı göndermez; sunucu değişiklikleri yalnız yetkiyle, yedek + geri alma ile.** — Lokman (kalıcı ilke)
- **Sırlar (API anahtarı, parola, erişim anahtarı) koda, sohbete, rapora, günlüğe yazılmaz; numaralar maskelenir.** — Lokman (kalıcı ilke)
