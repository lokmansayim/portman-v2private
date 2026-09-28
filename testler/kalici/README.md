# Kalıcı akış testleri (İE-02)

Postgres üzerinde kalıcı konuşma ve iş akışının kabul testleri. İş emri: `docs/is_emirleri/IE-02.md`. Kod: `kanal/depo.py`, `kanal/kalici.py`, `kanal/depo_aktar.py`, `kanal/goc/`.

## Koşum

Gerçek bir Postgres gerekir (16 ile sınandı). Adres ortam değişkeniyle verilir; yoksa testler atlanır. Her test kendi veritabanını açar ve siler.

```
PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici -q
PORTMAN_TEST_PG="…" python testler/kalici/kabul_gosterimi.py --rapor kabul.md
```

## Neyin gerçek, neyin simülasyon olduğu

| Gerçek | Simülasyon |
|---|---|
| Postgres 16; göçler; işlemler; kilitler | Gelen WhatsApp mesajı: `feature.php`'nin kuyruğa yazdığı satır elle üretilir (imza ve Meta yok) |
| Beyin kural katmanı (`karar_ver`), `worker.isle` | LLM çıkarımı kayıtlıdır (manuel arka uç) |
| Motor: `test_yeniden_baslatma.py` ve `kabul_gosterimi.py`'de gerçek; öteki testlerde hızlı sahte üretici | Gönderim sahte bir WhatsApp göndericisiyle yapılır; hosting PHP tarafı yok (`portman/lib.php` depoda değil) |
| Ayrı işleyici süreçleri; süreç öldürme (SIGKILL) ve yeniden başlatma (SIGTERM) | Zamanın geçmesi, konuşmadaki zamanlar geriye alınarak taklit edilir (D-01'in 2 saati) |

Gerçek WhatsApp ve gerçek LLM ile denenmedi. Bu testler canlı doğrulama değildir.

## Testler

| # | Test | Dosya |
|---|---|---|
| T1 | Aynı mesaj tekrar ya da eşzamanlı gelir (8 iş parçacığı): tek iş; D-01 sorusu askıdayken tekrar gelen mesaj sayacı artırmaz | `test_kalici.py` |
| T2 | D-01 sorusu ("yeni" ve "değişiklik"), B1 pencere sorusu, eksik bilgi sorusu: soru bir süreçte sorulur, cevap yeni bir süreçte doğru soruya ve projeye bağlanır | `test_kalici.py` |
| T3 | Yarım iş: süreç Motor sırasında öldürülür, yeniden başlayan işleyici bitirir; LLM yeniden çağrılmaz; üç denemede bitmeyen iş başarısız sayılır, bayiye ve Patron'a bildirim yazılır | `test_yeniden_baslatma.py` (gerçek süreç ve Motor), `test_kalici.py` |
| T4 | Eski sürümle yazma reddedilir; kirası devredilen işin geç sonucu atılır; üç işleyici eşzamanlı çalışırken art arda iki değişiklik sırayla işlenir ve ikisi de son revizyonda olur | `test_kalici.py` |
| T5 | Sonucu belirsiz gönderim yeniden gönderilmez; yarıda kalan gönderim belirsiz sayılır; kesin gönderilmeyen satır işaretlenir | `test_kalici.py` |
| T6 | Başka numaranın revizyonu ve çıktısı okunamaz; bir bayinin onayı ya da cevabı ötekinin kaydını değiştirmez | `test_kalici.py`, `test_inceleme.py` |
| T7 | Yeni revizyon iletilmeden yazılan onay, eski revizyonu alıntılayan onay ve iletimi belirsiz revizyona gelen onay kaydedilmez | `test_kalici.py` |
| T8 | `pg_dump` yedeği ayrı bir veritabanına `pg_restore` ile yüklenir; bütün tablolar aynı; askıdaki soru oradan doğru cevapla sürer; asıl veritabanı etkilenmez | `test_kalici.py` |
| T9 | Dosya düzeni (`durum/*.json`, `state.json`) → Postgres → dosya düzeni kayıpsız; askıdaki D-01 sorusu geçişten sonra cevaplanır; işlenmiş mesaj yeniden işlenmez | `test_kalici.py` |
| T10 | Kabul gösterimi (aşağıda) | `kabul_gosterimi.py`, `test_kabul.py` |
| İnceleme | Bağımsız incelemenin (28.09) bulguları ve yakalanmayan mutasyonlar. İşin bitişi yazılamazsa hiçbir sonuç kalmaz; mesaj ve iş birlikte yazılır (ikisi de tetikleyiciyle sınanır). İlk yazmada da sessiz ezme olmaz. Kirası devredilen işin eski sahibi yazamaz. Süresi dolan D-01 sorusundan sonra gelen onay da denetlenir. Soru kaydı cevaplandı, düştü ya da devredildi diye doğru kapanır. Aynı bayi kodlu iki numara birbirinin kaydını göremez ve aynı İş Emri numarası üretilse de dosya ezilmez. Değişmiş PDF gönderilmez. Geç gelen gönderim teyidi kaybolmaz. İşlenmekte olan mesaj varken geçiş yapılmaz. SIGTERM'de eldeki iş bitirilir. İkinci tur: PDF yolu kayıtta ve satırda yerinde, hazırlık klasörü temiz; çakışmada taşınan dosya silinir; kayıt yazıldıktan sonra bağlantı koparsa PDF yerinde kalır; hiçbir şey sorulmadıysa soru kaydı açılmaz. | `test_inceleme.py` |

## Bağlantı turu (`test_baglanti.py`)

- **Göç 002:** 001'den yükseltme; API kabulü ile Meta teslimi ayrı alanlarda.
- **Onay zinciri:** gönderilen PDF'in mesaj kimliği → revizyon → proje → gelen cevap ve alıntısı. Eski revizyona verilen onayın reddi ve güncel revizyonun doğru onayının kabulü aynı akışta gösterilir. Kabul edilmiş ama teslim edilmemiş plana yazılan onay reddedilir; Meta "failed" bildirdiyse onay kaydedilmez.
- **D-03 kapsamı:** yetkisiz numara, soru, geçersiz ya da hatalı LLM çıktısı, yazısız mesaj ve beklenmeyen hata bir kez yazılır, tekrar edilmez. Belirsiz gönderim işi yeniden açmaz.
- **Ajan kalıcı modu** (`vps/agent.py`), **sahte hosting** ile (`sahte_hosting.py`): claim → Postgres → hosting'e devir → durum eşitleme. Ayrıca şunlar sınanır:
  - cevabı kaybolan devir yeniden denenir;
  - aynı kanal mesajı ikinci iş açmaz;
  - yeniden başlayan ajan ölü sürecin işini hemen alır;
  - hosting satırı bırakmışsa satırlar "gönderilmedi" olur;
  - eski API ya da eksik göçle ajan çalışmaz;
  - canlı kabul gösteriminin yedi adımı provadan geçer.
- **Sahte hosting PHP değildir.** Gerçek PHP hattı `kanal/tests/baglanti_test.php` ve `kanal/tests/e2e_kalici.py` ile sınanır; ikisi de `portman/lib.php` ister (`docs/is_emirleri/IE-02-canli.md`, kapı B). Sahte hostingin neyi taklit ettiği ve etmediği `sahte_hosting.py`'nin başında yazılı.

## Hosting'e devir (`test_hosting_devri.py`, dördüncü inceleme)

- **Postgres kesintisi:** Postgres'e ulaşılamıyorsa hosting'ten mesaj alınmaz; alınıp yazılamayan mesaj diske alınır, Postgres dönünce yazılır ve işlenir.
- **Hosting'in 600 sn'si:** uzun bir kesintiden sonra bekleyen cevap claim'den (süpürmeden) önce verilir. D-03'ün üç denemesi (3 × 120 sn) `feature.php`'deki `PM_KANAL_STALE`'e sığar; tükenen işin ve başarısız işin bildirimi hosting'e verilir.
- **Hata sınıfları:** 401, 403, 429, 5xx ve geçici 422 yeniden denenir; bilinen kesin retler (yol, PDF biçimi, satır uyuşmazlığı, 413) hemen "gönderilmedi" olur ve sağlık uyarısına düşer; geçici hata 15 dakikayı aşarsa da öyle.
- **Tek etkin işleyici ve boşaltma:** `worker=off` iken ajanın ana döngüsü claim çağırmaz, açık işi bitirip hosting'e verir; `worker=hosting` iken hiçbir şey yapmaz. İçe aktarma yalnız boş veritabanına; canlı geçişte kuyruktakiler iş olmaz. Ölü kira yalnız bu makinedeki süreçler için düşer.
- **Eşitleme ve onay sınırı:** belirsiz satır sonradan kabul görürse işlenir ve onay kabul edilir; iş işlenmeden önce durum okunur; en yeni 200 satır önce, metin satırlarının teslimi beklenmez; Meta'nın "sent" anı hosting saatinden önce gelir; aynı saniyede yazılan onay reddedilir, bir saniye sonrası kabul edilir; hosting durumlarının her biri; teslim durumu geri gitmez, ilk teslim anı kalır.
- **Tekrar gelen mesaj:** ilk işin hosting'e verilemeyen ya da bekleyen cevabı bu alımla verilir; hosting'in tuttuğu satır yeniden verilmez; kayıttan sonra değişen PDF hosting'e verilmez.
- `test_vps_betikleri.py`: anahtar yenileme ve API denetimi betikleri anahtar değerini yazdırmaz, dosya iznini korur.

## Kabul gösterimi

`kabul_gosterimi.py` şu sırayı koşar ve her adımı veritabanından denetler:

1. Bayinin açık bir projesi var: r01 üretilmiş ve gönderilmiş.
2. WhatsApp talebi gelir ve kaydedilir.
3. Portman netleştirme sorusu sorar (D-01).
4. İşleyici süreci durdurulur ve yeniden başlatılır.
5. Cevap doğru soruya ve projeye bağlanır; r02 r01'den devam eder.
6. PDF gönderilir.
7. Aynı mesaj yeniden gelir; ikinci iş oluşmaz.
