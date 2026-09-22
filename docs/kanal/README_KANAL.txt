PORTMAN KANAL v1 (kanal-v1.0) — 21 Eylül 2026, Claude
=====================================================
444 80 56 hattından gelen mesajı al → doğrula → (Beyin) anla ve karar ver → (Motor) çiz ve doğrula → aynı hatta metin + PDF geri gönder.
Bu sürüm PATRON MODU: yalnız panelde adı "Patron" olan numaranın mesajları sahiplenilir; gerçek mesaj gönderilir. Diğer numaralar sohbet botunda kalır.

AKIŞ (hosting üzerinde, OpenAI yalnız çıkarım için — birkaç bin token; bulut CAD yok)
  Meta webhook (imzalı) → developer/webhook.php → kanal/feature.php::pm_kanal_capture
      → kanal/state.json → inbound {queued}         (sohbet botu bu mesaja cevap vermez)
  Cron (dakikada bir, task2/venv Python) → kanal/worker.py
      → beyin.llm (gpt-4o-mini, JSON şeması: "bayi ne dedi?") → beyin.karar (kural: soru | İş Emri | yönlendir | cevapla)
      → outbound {text}  ve İş Emri varsa motor.dxf_out.uret → kanal/projects/<İş Emri>/rNN/*.pdf → outbound {document}
  Cron (dakikada bir, PHP worker.php) → pm_kanal_tick → Meta: metin, medya yükleme + belge → accepted → sent/delivered/read (durum webhook'u)
      → panele yayın (store.json outgoing; panel sohbet kaydı)

DOSYALAR
  feature.php            PHP: yakalama, gönderim, teslimat izleme, tick, panele yayın, preflight (sır yazmaz)
  worker.py              Python: kuyruk → Beyin → Motor → giden satırlar; bağımlılık kurulumu; öz-test (hiç göndermez)
  settings.json          Ana anahtar (enabled), dry_run, mode (patron|kayitli|hepsi), llm, ayarlar_json yolu, ...
  self-test-request.json Kurulum öz-testi girdisi → self-test-result.json
  beyin/                 Beyin v0.1 (sema, prompt, llm, katalog, varyant, konusma, karar, harness, veri/, testler/)
  motor/                 Motor v1.1 (geometry, dxf_out, validate, katalog, malzeme_katalogu.json)
  is_emri/               Onaylı şablonlar: P6001_2plus1_6x6, ALTIN_2plus1_6x8, YAN_VERANDALI_2plus1_6x8p5
  ref_source-6x8.dxf, ref_h-connector.json, DejaVuSans.ttf   Motor referansları (doğrama blokları, H, font)
  install/               KURULUM.md (yarınki adımlar), GERI_ALMA.md, cron.txt, webhook.php.yama.txt, worker.php.yama.txt, *.candidate.php
  tests/                 offline_test.php (PHP, sahte Meta, gerçek lib.php ile), e2e_steps.php + e2e_local.py (PHP→Python→PHP uçtan uca)
  Çalışırken oluşanlar: state.json/state.lock (paylaşılan kuyruk), health.json (PHP), worker-health.json (Python), preflight.json,
  install-report.json, projects/, durum/ (gönderen başına konuşma), checks/ (öz-test çıktıları), worker.log (cron)

GÜVENLİK İLKELERİ (Görev 2/3 ile aynı)
  - Yalnız Meta imzası doğrulanan webhook'tan gelen mesaj işlenir; hedef numara = gelen mesajın göndereni (PATRON bildirimi hariç).
  - Öz-test satırı ya da "wamid." ile başlamayan ebeveyn asla gönderilmez. Belirsiz kalan POST otomatik tekrar edilmez.
  - 15 dakikadan eski (geç tekrar teslim) mesaj kuyruğa alınmaz; 24 saatlik yanıt penceresi dışına gönderilmez (held).
  - API anahtarı yalnız panelin ayar dosyasından okunur; hiçbir dosyaya/loga yazılmaz (hata metinlerinde sk-… maskelenir).
  - Tüm çıktılar 0600/0700; kanal klasörü public_html dışında.

YEREL TESTLER (21.09.2026, Claude çalışma alanı; PHP 8.4 CLI, Python 3.11, ezdxf 1.4.4, PyMuPDF 1.28, shapely 2.1, pydantic 2.13)
  php -l feature.php + install/*.php: hata yok
  php tests/offline_test.php <lib.php>: 30/30 (imza, mod, sahiplenme, dry_run, metin/belge gönderimi, PATRON çözümü, öz-test reddi,
      alıcı uyuşmazlığı, çağrı sırası, panele yayın, teslimat durumları, belirsizlik, takılı satır, kill switch, sır sızmaması)
  python3 tests/e2e_local.py <lib.php>: 12/12 (PHP yakalama → Python worker → PDF 704 KB, doğrulama geçti → PHP tick → 3 Meta çağrısı → onay turu)
  worker.py öz-testi: passed 12,1 s (Beyin 15/15, İş Emri, Motor doğrulaması; LLM adımı anahtar olmadığı için atlandı)
  CANLIDA DENENMEYENLER: gerçek OpenAI çağrısı (openai_chat yolu; öz-test yarın tek çağrıyla dener), gerçek Meta gönderimi,
  hosting Python'unda shapely/pydantic kurulumu, panelin numaralar/ayarlar dosya yolları (preflight.json gösterir).

SINIRLAR (v1)
  Şablonu kodlanmış tek katalog modeli P6001 (+ onaylı 6x8 ve 6x8,5 örnekleri grid eşleşmesiyle). Varyantlar: ayna_x, ayna_y, pencere ölçüsü.
  Diğer 36 model, ekle/kaldır, serbest yerleşim → dürüst yönlendirme mesajı. Görsel/kroki okunmaz (yalnız metin). Pafta biçimi Motor v1.1
  (akslı plan + net alanlar + montaj + ön görünüş + çatı profili + tablo); ön onay pafta formatı (akssız plan, görünüşler, künye) sonraki adım.
