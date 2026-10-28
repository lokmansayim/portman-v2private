# Altın set (İE-19)

Bayinin cümlesinden Portman'ın ne anladığını (okuma) ve ne yaptığını (karar) sabit vakalarla ölçer. Pano satırı 51 (bağlı 22 ve 92);
iş emri `docs/is_emirleri/IE-19.md`. Kabul satırı: her sürüm öncesi kör dilim koşar, okuma doğruluğu raporlanır.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `kos.py` | araç: karar, okuma, uçtan uca, güvenlik sayacı; kör dilim; baz çizgisi; ücretli kayıt (onaylı) |
| `vakalar.json` | açık dilim: 58 yeni vaka (konuşmalar halinde) + harness'in 22 vakasının beklenen okuması |
| `baz.json` | açık 80 vakanın bugünkü sonucu (gerileme kapısı) |
| `kor_muhur.json` | kör dilimin mührü (SHA-256, bayt, vaka sayısı, adım dağılımı); dilimin kendisi depoda yok |
| `kayitlar/` | açık 53 mesajın kayıtlı LLM okuması (`<id>.json`; claude-opus-5-5, 27 Ekim 2026 ücretli kayıt) |
| `test_altin_set.py` | pytest: biçim, dağılım, gerileme kapısı, harness'le tutarlılık, kör mühür kuralı, ücretli kaydın freni |

Harness'in 22 vakası (`beyin/testler/`) olduğu gibi okunur, kopyalanmaz ve değişmez; `vakalar.json` yalnız onların beklenen okumasını
tutar. Kör dilim (20 vaka) proje klasöründedir: `Portman_Proje_Dosyalari/Altin_Set/kor/vakalar.json`.

## Vaka

Bir senaryo bir konuşmadır; adımları sırayla ve aynı konuşma durumuyla koşar. Adım bir bayi mesajı (`mesaj`) ya da düğmedir (`dugme`,
`s:{set}:<kod>`, `o:{is_emri}:{rev}`, `o:{is_emri}:{rev_onceki}`, `r:{is_emri}:{rev}`; yer tutucular o anki durumdan doldurulur).

| Alan | Anlamı |
|---|---|
| `id`, `adim`, `kaynak` | kimlik; rehberdeki adım (`selam_soru`, `kayitsiz_kapsam`, `eksik_bilgi`, `bilgi_tam`, `katalog_kodu`, `secim`, `revizyon`, `onay_eski`); cümlenin kaynağı (canlı kayıt, rehber, depo, yazılmış) |
| `okuma` | beklenen okuma (`Talep` şeması; yalnız cümlede olan); `okuma_kabul` istemin iki okumaya izin verdiği alanda öteki kabul |
| `karar` | beklenen karar: `eylem` (liste = biri), `soru_alani` (liste = biri), `gerekce` (içinde geçer), `secenek` (sunulan üç), `secenek_icerir`, `plan_kodu`, `revizyon`, `degisiklikler`, `plan_uretimi`, `mesaj_icerir`, `mesaj_icermez` |
| `gonderen` | yoksa `BAYI-TEST-1`; kayıtsız numara için kayıtta olmayan bir ad |
| `hazirlik` | vakadan önce konuşmayı kuran adım (ör. bir plan açmak): puanlanmaz, her kipte beklenen okumayla koşar |
| `anlam`, `not` | onay tablosu için kısa açıklama |

Beklenen değerler rehberden ("Portman Bayi Rehberi ve Süreç Taslağı") ve canlıda kabul edilen denemelerden yazılır; ikisi ayrışırsa
rehber esastır (D-27) ve not düşülür. Beklenen değeri Lokman onaylar (onay tabloları, proje klasöründe).

## Ölçüler

- **Karar (her koşuda, ücretsiz):** beklenen okuma kural katmanına (`karar_ver`) verilir; düğmeler `kanal/etkilesim.coz`'dan geçer.
  LLM, Postgres ve çizim yok. LLM-önce revizyon kapalı, plan üretimi açık (canlı ayar). Plan üretiminde karar "yeni plan üretilecek"te
  biter; üretim worker'dadır ve burada oynatılmaz.
- **Okuma (kayıtlı LLM okumasıyla, oynatma ücretsiz):** alan alan; dolu alanın doğruluğu ve boş kalması gereken alanın boş kalması ayrı.
  Pencere değişikliği iki yoldan sayılır (pencere satırı ya da `pencere_*` varyantının `parametreler`i); varyant türleri penceresiz.
- **Uçtan uca:** kayıtlı okuma → karar; senaryonun bütün mesajlarının kaydı varsa.
- **Güvenlik sayacı:** soru, yönlendirme ya da cevap beklenirken plan üretilen (İş Emri, seçenek seti ya da yeni plan üretimi) vaka.

Harness'in 22 vakasının kaydı Eylül'den (`beyin/testler/`); yeni vakaların okuması 27 Ekim 2026'da canlı modelle (claude-opus-5-5)
ücretli kayıtla geldi (pano 22; Lokman'ın onayıyla): açık 53 mesaj `kayitlar/`da (depoda), kör 20 mesaj `<KLASÖR>/kayitlar/`da.
Baz çizgisi kayıtlarla yeniden yazıldı; pytest de aynı kayıtları okur. Model kıyası (pano 92, Sonnet 5.5) proje klasöründe
(`Altin_Set/model_kiyas/`), depoya girmez. Yeni vaka eklenince kaydı aynı komutla alınır (var olan kayıt yeniden çağrılmaz). Karar katmanı bayinin ham metnini alır (worker ve harness gibi); LLM'e giden metin numarası maskeli.

## Komutlar

```
python3 -m testler.altin.kos                                   # açık set: özet
python3 -m testler.altin.kos --rapor R.md --json R.json        # vaka vaka (cümleler maskeli)
python3 -m testler.altin.kos --kor <KLASÖR>                    # kör dilim: yalnız sayılar
pytest -q testler/altin                                        # kapı (kör dilim: PORTMAN_ALTIN_KOR=<KLASÖR>)
```

## Kurallar

- **Gerileme kapısı.** Bugün uyumlu vaka uyumlu kalır, güvenlik sayacı büyümez, kayıtlı okumanın sayıları düşmez. Bugün uyumsuz vaka
  "rehberde var, bugün çalışmıyor" listesidir; beklenen değer gevşetilmez. Bir düzeltme vakayı geçirirse `--baz-yaz` ile baz yeniden
  yazılır, gerekçesi iş emrine. Vaka eklenince ya da çıkınca da (test bunu ister).
- **Kör dilim.** Depoya girmez; araç mühür tutmazsa koşmaz; çıktı yalnız sayıdır. Kör vakaya bakılarak kural ya da istem değiştirilmez.
  Bir kör vaka açılacaksa Lokman'ın kararıyla açığa alınır, yerine yenisi konur ve `--muhurle <KLASÖR> --onay "<karar>"` ile yeniden
  mühürlenir.
- **Sürüm öncesi.** Sürüm etiketi açılmadan önce (Kapı M) kör dilim koşar: `python3 -m testler.altin.kos --kor
  /mnt/project-files/Portman_Proje_Dosyalari/Altin_Set/kor/`; sayılar etiket açıklamasına ve DURUM'daki sürüm satırına yazılır.
- **Ücretli kayıt.** `--kaydet` gerçek arka uçla yalnız `--ucretli` ve `--tavan N` ile çalışır; Lokman'ın açık onayı ve anahtar
  gerekir. Tavan en kötü duruma göre uygulanır (mesaj başına iki çağrı: şema hatasında tek tekrar); hata koşuyu durdurur ve sayımı
  yazar. Var olan kayıt yeniden çağrılmaz; bağlam worker'daki gibi (bayinin hitabı, konuşma özeti; numara yok).
- **Baz çizgisi** yalnız depodaki vakalar ve kayıtlarla yazılır (`--baz-yaz`, `--vakalar` ve `--kayit-dizini` olmadan).
