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

## Kabul gösterimi

`kabul_gosterimi.py` şu sırayı koşar ve her adımı veritabanından denetler:

1. Bayinin açık bir projesi var: r01 üretilmiş ve gönderilmiş.
2. WhatsApp talebi gelir ve kaydedilir.
3. Portman netleştirme sorusu sorar (D-01).
4. İşleyici süreci durdurulur ve yeniden başlatılır.
5. Cevap doğru soruya ve projeye bağlanır; r02 r01'den devam eder.
6. PDF gönderilir.
7. Aynı mesaj yeniden gelir; ikinci iş oluşmaz.
