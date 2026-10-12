# Kural kitabı

Portman'ın kural kitabı tektir; bütün modeller için geçerlidir. Kurallar veridir: kod onları okur ve uygular. LLM kural uygulamaz, saymaz, çizmez (K05: LLM anlar, kod karar verir). Her kuralın yanında kaynağı (Lokman'ın cümlesi ve tarihi; mühendis; gerçek liste; Excel motoru) ve durumu yazar. Kural değişince sürüm artar. Eski sürümler `liste/setler/` altında durur ve o günkü listeyi bayt bayt yeniden üretir.

Lokman, 10 Ekim 2026 10:18: "artık bu çizim kurallarına her seferinde nasıl çağıracaksan ona göre klasörle". Klasörler bu yüzden, her talepte okundukları sıraya göre ayrıldı (10 Ekim 2026). Kurallar önce deneme klasörlerinde duruyordu (`deneme/2026-10-03_yukleme/kurallar.json` ve öteki üç dosya). İçerikleri değişmeden buraya taşındılar; taşımadan sonra bütün çıktılar bayt bayt aynı.

## Kural kitabı ve model

**Kural**, her modelde aynı geçerli olan cümledir. Örnekler: "çelikte veranda tavanı Boardex", "her saçak köşesine bir iniş".

**Model** (Yapı Tanımı) ise bir projenin kendisidir: duvarlar, mahaller, kapı ve pencereler, çatı düzlemleri. Her model ayrı bir dosyadır. Kod, aynı kural kitabını hangi tanıma uygularsa o modelin çizimini ve listesini çıkarır.

Bugün modeller deneme klasörlerinde duruyor:
- Ç8201: `deneme/2026-10-02_celik/C8201.json`; aynı modelin 0.5 sürümü `deneme/2026-10-06_kor_test/C8201_05.json`.
- Kör test projeleri: `deneme/2026-10-0x_kor_test*/tanim/`.
- Ç8801 (katalog; kural kitabının yeni bir modelde sınanması, 10 Ekim 2026): `deneme/2026-10-10_c8801/tanim/`. Katalog çatısı (Lokman, 10 Ekim 14:46: "2. versiyon") ve aynı plana iki çatı varyantı (K, L; "çatı olarak 3'üde olur").

Tanımda o projenin teknik özelliklerinden gelen birkaç seçim de yazılıdır: duvar profili, kaplama kalınlığı, saçak. Hedef şu: tanım yalnız standarttan farklı olanı yazsın, standart bu kitaptan okunsun.

## Her talepte çağrı sırası

| # | Adım | Kim | Okunan | Çıktı |
|---|---|---|---|---|
| 1 | Bayinin mesajını anlamak | Beyin (LLM) | konuşma ve katalog | iş emri: model, seçenekler, değişiklikler; anlaşılmayan yer bayiye sorulur |
| 2 | Modeli kurmak | Motor (kod) | model tanımı, `model/duvar_tipleri.json`, `model/secenekler/` | duvarlar, kaplamalar, açıklıklar, çatı |
| 3 | Çizim seti | Motor | `cizim/cizim_seti.json` | plan, çatı planı, dört görünüş, pafta, IFC, perspektifler |
| 4 | Metraj ve yükleme listesi | Motor | `liste/kurallar.json` | yükleme listesi (çelikte yöntem A, prefabrikte yöntem B) |
| 5 | Bayinin standardı | Motor | `bayi/<bayi>.json` | bayinin standardına göre süzülmüş liste |
| 6 | Bayiye cevap | Beyin (LLM) | 2–5'in çıktıları | mesaj ve dosyalar; sayılar koddan |

`model/duvar_tipleri.json` bugün Ç8201'in çiziminde ve metrajında okunuyor (`deneme/2026-10-02_celik/`, `deneme/2026-10-03_yukleme/girdi_uret.py`). Genel motor (`deneme/2026-10-06_kor_test/`) duvar sınıflarını şimdilik tanımdan okuyor.

## Klasörler

| Klasör | İçerik |
|---|---|
| `model/duvar_tipleri.json` | Baz paketin duvar tipleri: katmanlar, karkas 80 ve 140 mm, kaplamalar. Duvar kalınlığı katmanların toplamı |
| `model/secenekler/` | Değişiklik operatörleri: model tanımı değişmeden paket farkını uygular. Örnek `dis_karkas_140.json` (Lokman, 3 Ekim 2026 11:49: "dışlar 140'lık") |
| `cizim/cizim_seti.json` | Çizim setinin içeriği (Lokman onayladı, 7 Ekim 2026 07:45). Anlatımı `docs/sartname/cizim_seti.md` |
| `cizim/pafta_sablonu.json` | Örnek Şablon paftasının koda bağlı seçimleri (İE-08, 12 Ekim 2026; durum `varsayim`, Lokman'ın onayı bekleniyor): vasistas eşiği, çatı tipi adları, özellik yazı boyu. `motor/genel/sablon_pafta.py` okur; anahtar yoksa koddaki varsayılan sürer |
| `liste/kurallar.json` | Metraj ve yükleme listesi kuralları; her anahtarda `deger`, `durum`, `kaynak`. Sürümü `sema` alanında (bugün 0.19-taslak) |
| `liste/setler/` | Dondurulmuş sürümler (0.12–0.19; aşağıda). Bir set `PORTMAN_KURALLAR` ortam değişkeniyle ya da `python -m motor.genel.uret --set` ile seçilir (`motor/genel/kural.py`; deneme kopyası `deneme/2026-10-03_yukleme/kural.py`) |
| `bayi/ornek.json` | Bayi standardı örneği: listeye giren gruplar, çatı yöntemi. Gerçek bayi, numara ya da ad yok |

**Sıradaki:** pafta kuralları `cizim/` altına girecek: makas, dere ve panel yerleşimi, kesim planı. Lokman, 10 Ekim 2026: "Zaten üretim dosyası vermeyeceğiz sen kendin oluşturacaksın paftayı bunları sana örnek olarak eğitimin için atıyorum". Kurallar örnek projelerden çıkarılacak; o projelerin paftaları kuralların sınavı olacak.

## Sürümler

| Sürüm | Hangi cevaplarla | O günkü çıktıları bayt bayt veren commit |
|---|---|---|
| 0.12 | Kör test KT-01'den önceki kurallar | `eff6a74` (7 Ekim 03:46) |
| 0.13 | Lokman, 7 Ekim 07:45 ve 08:02 (KT-01'in on iki sorusu) | `021c277` (7 Ekim 10:55) |
| 0.14 | Lokman, 8 Ekim 00:45 | `4251345` (8 Ekim 03:15) |
| 0.15 | Lokman, 8 Ekim 07:23 ve 07:41 | `b5ff4cf` (9 Ekim 22:10) |
| 0.16 | Lokman, 9 Ekim 22:22 (KT-02) | `6b265c8` (9 Ekim 22:40) |
| 0.17 | Lokman, 9 Ekim 22:44 (korkuluk) | `c939fe2` (10 Ekim 10:47) |
| 0.18 | Lokman, 10 Ekim 10:18–10:39 (KT-03; beş fotoğraf): tek eğimli çatı panelli çatının kenarları (`panel_cati_kenarlari`), alçak çatının üstüne düşen köşede iniş yok, taharet musluğu, çatı çıkış kapağı ve bacanın içi listede yok | `8fca288` (10 Ekim 11:21) |
| 0.19 | Lokman, 10 Ekim 11:39: kısa derede (4 m'ye kadar) tek iniş; alçak çatının üstüne düşen köşede iniş var (dere 15 cm içeride biter, su o çatıya iner), yalnız tek inişli küçük çatıda (sundurma) yok | `setler/0.19.json` (İE-08, 12 Ekim 2026; `kurallar.json`un o günkü bayt bayt kopyası). **Altın testin pimi:** `denetim/kos.py` genel adımları ve `modeller/altin.json` bu setle üretilir; ana koddaki paket `python -m motor.genel.uret --set kurallar/liste/setler/0.19.json` |
| 0.20-taslak (güncel) | Henüz yeni cevap yok; 0.19'un aynısı, yalnız sürüm numarası. Lokman (12 Ekim 2026 14:53): 0.20'den itibaren `kaynak`/`aciklama` alanlarında mühendisin adı yerine yalnız "mühendis" yazılır; eski setlerdeki ad şirket içi kayıt olarak kalır | `liste/kurallar.json` (canlı akış bunu okur; yeni kural geldiğinde buraya yazılır, 0.20 dondurulunca `setler/`e kopyalanır) |

## Kural nasıl eklenir

1. **Kaynak:** Lokman'ın cevabı, ya da kör testte gerçek listeyle çıkan bir fark.
2. **Yazım:** Kural dosyasına bir anahtar olarak yazılır: değer, durum ve kaynak. Kaynakta cevap yazıldığı gibi, tarih ve saatiyle durur.
3. **Kod:** Yeni davranış o anahtara bağlanır. Anahtar yoksa eski davranış sürer; böylece eski setler eski çıktıları verir.
4. **Sürüm:** Sürüm artar; önceki set `liste/setler/` altına dondurulur.
5. **Sınav:** Kör test projeleri yeniden çözülür. Önce tutan satır bozulmamalıdır; bozuluyorsa nedeni Lokman'ın bir kararıdır ve satırın notunda yazar (0.18'de KT-01'in müştemilatına gelen dere: gerçek listede yoktu). Eski setler eski çıktıları bayt bayt vermelidir.

Örnek projeler LLM'i eğitmez. LLM sohbetten sonra hiçbir şey hatırlamaz. Kalıcı olan bu kitaptır ve testlerdir: her örnekten kural çıkar, örnek de teste dönüşür.

**Durum değerleri:**
- `lokman`: Lokman söyledi.
- `muhendis`: mühendis söyledi.
- `excel`: yükleme listesi çalışma kitabındaki formül.
- `motor`: Excel hesaplama motorundaki formül.
- `liste`: gerçek listeden okundu.
- `uydurma`: listeye uyduruldu; teyit bekliyor.
- `varsayim`: varsayım.
- `soru`: cevap bekliyor.

Ayrıntısı ve bütün cevaplar `docs/sartname/yukleme_listesi_yontemi.md`'dedir.

## Canlıya alınırken (ayrı onay gerekir)

Kurallar sunucudaki veritabanında bir tabloya taşınacak; her değer kaynağı ve durumuyla gidecek. Sunucu kendi kopyasını okur, her talepte GitHub'dan kural çekmez. GitHub kitabın deposu ve geçmişidir.

Kural değişince kod değişmez; yeni sürüm kurulur. Bugün hiçbiri canlıda değil.
