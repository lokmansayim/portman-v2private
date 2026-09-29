# Referans testleri · 28 Eylül 2026

v1.1.1 çekirdeği (`ec4e9a3`) temiz ortamda üç ayrı koşuda aynı sonucu verdi. `2026-09-28/` klasörü o sonucu dondurur; bundan sonra yazılan her parça `dogrula.py`'yi geçmek zorundadır.

## Nasıl doğrulanır

```
python3 testler/referans/dogrula.py                        # ~4,5 dk: kos.py --planlar + karşılaştırma
python3 testler/referans/dogrula.py --hizli                # ~45 sn: 16 katalog planı hariç
python3 testler/referans/dogrula.py --referans 2026-09-28  # belirli bir referansla
```

Betik ilk satırda koşulan kodu (commit ve kaydedilmemiş değişiklikler) yazar; her zaman çalışma ağacındaki güncel kodu koşar. Bu ağacı geçici bir klasöre kopyalar (`deneme/`, `testler/`, `KARARLAR/` hariç) ve `denetim/kos.py`'yi orada koşar; depoya yazmaz. `PORTMAN_*` ortam değişkenleri (başka referans klasörü, bayi kaydı, durum dizini) ve LLM anahtarları alt sürece geçmez. Ağ, LLM, WhatsApp ya da canlı sunucu kullanmaz. Karşılaştırma en yeni tarihli referans klasörüyle yapılır. Çıkış kodu 0 referansla aynı, 1 fark var, 2 referans bozuk ya da koşu sonuç vermedi demektir.

Kurallar:
- Referans girdiler değişmemeli: İş Emri şablonları (`is_emri/`), referans çizim ve kayıtlar (`ref_katalog/`, `ref_yan/`, `kanal/ref_*`), katalog verisi ve test bayi kaydı (`beyin/veri/`); toplam 23 dosya. Dondurulan dosya silinemez; yeni dosya bilgi olarak raporlanır.
- Beyin test vakaları vaka vaka izlenir. Vakanın özeti harness'in okuduğu her şeyi kapsar: mesaj kaydı (beklenen eylem ve içerik kontrolü dahil) ve kayıtlı LLM çıkarımı. Çıkarımın kaynağı olan grup kaydı da özete girer; harness onu okumaz. Kimlikler tamsayı olmalı; çıkarım, harness'teki gibi kimliğin kendisiyle eşlenir. Dondurulan 22 vaka aynı sırayla ve değişmeden durmalı. Yeni vaka yalnız sona eklenebilir, çünkü aynı göndericinin vakaları konuşma durumunu paylaşır ve sıra sonucu etkiler.
- v1.1.1 ağacındaki değişiklikler (`SHA256SUMS`'a göre değişen, eksik ve yeni dosyalar) yalnız bilgi olarak raporlanır; kod değişikliği tek başına fark sayılmaz.
- Beyin harness'inde tüm vakalar uyumlu olmalı; vaka sayısı 22'den az olamaz.
- Motor sayıları, BOM sayımları, çıkarıcı sonuçları ve içerik parmak izleri aynı kalmalı.

## Yeniden dondurma

Bilerek yapılan bir değişiklik referansı değiştirirse (örneğin vaka 1'deki adın takma adla değiştirilmesi) yeni referans alınır:

```
python3 testler/referans/dogrula.py --dondur --gerekce "neyin neden değiştiği"   # tam koşu, ~5 dk
```

Betik bugünün tarihiyle yeni bir klasör açar (`--ad` ile geçmiş bir tarih verilebilir; aynı gün ikincisi için sonda bir harf, örneğin `2026-10-02b`). Var olan klasöre yazmaz; eski referans silinmez. Bir adım geçmiyorsa ya da test verisi okunamıyorsa dondurmaz. Yeni referans öncekinden farklıysa dayandığı karar `--karar` ile verilmelidir (`KARARLAR/` altında var olan bir dosya); yalnız testi geçirmek için referans güncellenmez. Önceki referansa göre bir şey kaldırılıyor ya da azalıyorsa (girdi dosyası, vaka, çıktı, vaka sayısı, Motor'dan geçen plan) `--kaldirmaya-izin` ister. Gerekçe, dondurulduğu commit, ortam, önceki referansa göre değişenler ve dört dosyanın özeti klasördeki `GEREKCE.md`'ye yazılır. Yeni klasör ayrı bir commit'le kaydedilir ve birleştirmeden önce incelenir; `git diff` eski ve yeni referansı yan yana gösterir.

Referans dosyaları elle değiştirilmez. `dogrula.py` her koşuda `GEREKCE.md`'deki özetleri sınar ve her referansı bir öncekine göre denetler: izinsiz kaldırma, önceki referansla aynı gerekçe ya da ileri tarih varsa "REFERANS BOZUK" yazar ve 2 ile çıkar. Bu denetim kazara ya da yarım kalmış değişikliği yakalar; özetleri de yeniden hesaplanmış, kasıtlı olarak elle yazılmış bir referansı yakalamaz. Onu inceleme yakalar: yeni klasör `git diff`'te görünür ve `dogrula.py` her koşuda hangi referansla, hangi gerekçeyle karşılaştırdığını ve önceki referansa göre neyin değiştiğini en üstte yazar. Bir vakanın değişmesi (örneğin beklenen eylemin genişletilmesi ya da içerik kontrolünün silinmesi) izin istemez, yalnız bu listede görünür; incelemede özellikle bakılacak yer burasıdır.

**Dikkat:** `denetim/kos.py`'yi depo kökünde doğrudan koşmayın. Sır taraması `deneme/` altındaki IFC dosyasındaki ondalık koordinatları telefon numarası sanıyor ve adım "failed" dönüyor (9 yanlış bulgu). `kos.py`'yi `dogrula.py` üzerinden koşun; o, `deneme/` olmadan geçici bir kopyada koşar. Kalıbın düzeltilmesi İE-02'de.

Ortam (28.09, pip ile kurulan sürümler): Python 3.11.15, ezdxf 1.4.4, pymupdf 1.26.0, shapely 2.1.2, pydantic 2.13.5, numpy 2.4.6. `kos.py`'nin kaydı pymupdf için sürüm yerine "(64-bit)." yazıyor.

## Dondurulan sonuç

| Adım | Sonuç |
|---|---|
| Referans girdiler | 23 dosya ve 22 Beyin vakası (`referans_girdiler.json`); dosya özetleri `SHA256SUMS` ile aynı |
| Beyin kural katmanı (harness) | 22/22 beklenen eylemle uyumlu. LLM çıkarımı kayıtlı dosyalardan gelir, gerçek API çağrılmaz. |
| Motor altın testi 6×8 | 41 pano, dış ölçü 773 × 1014 cm, ayak izi farkı 0 cm² |
| Motor altın testi Yan Verandalı 6×8,5 | 52 pano, dış ölçü 773 × 1076,75 cm, BOM 26 kod referans sayımla birebir |
| Motor P6001 katalog testi | 36 pano, dış ölçü 773 × 763 cm. Altın beklenti yok; kural doğrulaması. |
| Çıkarıcı P6001 altın testi | Izgara eşit, mahal 5/5, açıklık 7/9. İki fark menteşe yorumu; insan kararı bekliyor. |
| Çıkarıcı, 16 katalog planı | 15/16 Motor doğrulamasından geçti. P9901 desteklenmiyor (artı biçimli taban). P1051'de kapılar düşüyor. |
| Sır taraması | 4 bulgu, hepsi beklenen: 3'ü PHP testlerindeki sahte sabit, 1'i `kos.py`'nin kendi arama kalıbı. `dogrula.py` beklenmeyen bulgu sayısını (bulgu − beklenen) karşılaştırır, 0 olmalı; `kanal/tests`'e sahte sabitli yeni test dosyası eklemek ham sayıyı artırır ama fark sayılmaz (İE-02: `baglanti_test.php` ile 5) |
| DXF içerik parmak izi | 18 çıktı, üç ayrı temiz koşuda birebir aynı (`dxf_parmak_izleri.txt`) |
| PDF içerik parmak izi | 18 çıktı: sayfa ölçüsü ve bütün çizimler (2026-09-28b'den beri, D-02; önce yalnız sayfa ölçüsü) |

Dosyalar, `2026-09-28/` altında:
- `GEREKCE.md`: neden ve hangi kodla donduruldu; diğer dört dosyanın özeti.
- `referans_girdiler.json`: 23 girdi dosyasının özeti ve 22 Beyin vakasının vaka özeti.
- `denetim_kosum.json`: `kos.py --planlar` sonucu.
- `dxf_parmak_izleri.txt`: 18 DXF'in içerik parmak izi.
- `pdf_parmak_izleri.txt`: 18 PDF'in sayfa ölçüsü ve bütün çizimlerinin özeti (`2026-09-28b/`'de; `2026-09-28/`'de yalnız sayfa ölçüsü).

Araçlar, bu klasörde:
- `dogrula.py`: referansa karşı doğrulama ve yeniden dondurma (`--girdi-dokumu` bugünkü girdi özetini yalnız yazdırır).
- `parmak_izi.py`: parmak izi aracı.
- `paket_karsilastir.py`: canlıya giden paketleri depo koduyla karşılaştırır.

## 22 Eylül koşusuyla karşılaştırma

Girdi özetleri (20 dosya), adım sonuçları, BOM sayımları ve 16 planın plan plan sonucu 22 Eylüldeki koşuyla aynı.

DXF ve PDF dosyalarının özetleri ise her koşuda değişiyor. DXF'te değişenler: oluşturma ve güncelleme zamanı (`$TDCREATE`, `$TDUPDATE`), rastgele kimlikler (`$FINGERPRINTGUID`, `$VERSIONGUID`), ezdxf'in üst veri zamanları, OBJECTS bölümündeki nesne sırası (Python karma tohumuna bağlı; `PYTHONHASHSEED=0` ile sabitlenir) ve Motor'un PORTMAN_INFO katmanına yazdığı "Üretim: … UTC" metni. Bu yüzden referans, dosya özeti değil içerik parmak izidir. Parmak izi model alanı, kâğıt alanları ve blok tanımlarındaki her varlığın tüm özniteliklerini, köşe noktalarını ve eğimlerini kapsar; yalnız tutamaç, sahip ve metinlerdeki tarih-saat dışarıda kalır. Bir blok içi çizgiyi 0,1 cm kaydırmak, bir yazıyı döndürmek ya da bir ölçü noktasını oynatmak parmak izini değiştiriyor (28.09 deneme). PDF'te metin katmanı yok; Motor bütün yazıları çizgi olarak basıyor. İki koşu arasında 18.493 çizimden yalnız biri, "Üretim: … UTC" yazısı değişiyor. Bu yüzden `dogrula.py` koşularında üretim zamanı sabitlenir (`sabit_zaman/sitecustomize.py`, yalnız `TEST_SABIT_ZAMAN` varken; canlı koda dokunmaz) ve PDF parmak izi sayfa ölçüsüyle birlikte her çizimin konumunu, rengini, kalınlığını ve yol noktalarını kapsar (D-02). Sayfa ölçüsü aynı kalırken özet şu durumlarda değişir: yalnız revizyon numarası, yalnız proje kodu ya da bir pencerenin ölçüsü değiştiğinde, plandan çizgi silindiğinde. Aynı İş Emri iki kez aynı özeti verir (`test_pdf_izi.py`, Motor'u koşar, ~80 sn). Yeniden dondurmanın zincir denetimi `test_dogrula_zincir.py`'de; Motor koşulmaz.

## Canlı paketlerle karşılaştırma

`python3 testler/referans/paket_karsilastir.py <hosting_guncelleme_2011.zip>` ile yapıldı. Paketler depoda değil, Lokman'ın masaüstü klasöründe (`08_VPS/hosting_paket/`). Bunlar canlıya giden paketlerin kopyalarıdır; sunucudaki dosyalar 28.09'da okunmadı.

| Paket | sha256 | Sonuç |
|---|---|---|
| `hosting_guncelleme_2011.zip` | `bf22a83a…` | Karşılaştırılan 37 dosyanın hepsi depoyla aynı. Paketin kendi 3 dosyası (`current.zip`, `current.sha256`, `SURUM.txt`) ayrıca incelendi. |
| `kanal/package/current.zip` (VPS, `kanal-v1.1.1-20260922-2011`) | `bd1ca27c…` | 36 aynı. 6 farklı ve 5 yalnız pakette olan dosyanın hepsi Beyin test çıktısı. Kod farkı yok. |

## Açık not

`beyin/testler/mesajlar.json` dosyasının 1. vakasında gerçek olabilecek bir müşteri adı ve sevk yeri var. Gerçekse takma adla değiştirilmeli. v1.1.1 ağacı dondurulduğu için İE-01'de dokunulmadı; iş İE-02'ye bırakıldı. Değişiklik vaka 1'in özetini değiştirir; bu yüzden gerekçeli yeniden dondurmayla birlikte yapılır.
