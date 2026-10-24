# Prefabrik kör testi · protokol (İE-10, 12 Ekim 2026; araç BK-12 PR-3, 23 Ekim 2026)

Kaynak: Lokman, 12 Ekim 2026 23:10: "gerçek yükleme listesi olan tek prefabrik P6001 değil; sıra sıra sana vereceğim; çift kat gerçek yükleme
listesi olanı da vereceğim; kural motorunu doğrulayana kadar kör testi de yaparsın." Çelikteki KT-01/02/03 (`docs/raporlar/2026-10-0x_Kor_Test_KT0x.md`)
nasıl yapıldıysa prefabrikte de öyle yapılır; farklar aşağıda. Karar: D-12 (İE-10 dalında D-10 adıyla yazılmıştı).

## Kod

- Prefabrik kör test projeleri **PK-01, PK-02, …** (çelik KT'den ayrı sayaç; 13 Ekim serisi bayi arşivinden). Tek kat ve çift kat aynı sayaçta;
  kat sayısı tanımda yazar. TS-01 aynı serinin hedef örneğidir.
- AIPrefabrik seti **AP-01…AP-28** (BK-12; mühür `docs/notlar/2026-10-18_AIPrefabrik_muhur.md`). Üç proje iki kümede birden: PK-01 = AP-19,
  PK-07 = AP-08, TS-01 = AP-07.
- Bayiye, belgeye ve depoya adsız: kod, m², oda programı, kat sayısı (çelik KT'lerdeki gibi). Kişi, bayi ve model adı yazılmaz.

## Lokman'dan gelen

Her proje için, elden geldiğince:

1. **Çizim:** plan (DWG/DXF ya da PDF), görünüşler varsa; çift katta her katın planı.
2. **Gerçek yükleme listesi:** uygulanmış projenin listesi (Excel ya da PDF). **Mühürlenir (SHA-256 ve bayt) ve kendi listemiz depoya kaydedilene kadar açılmaz.**
3. **Teknik özellikler:** duvar kalınlığı (standart 100 / 60 değilse), yükseklik, çatı tipi ve kaplaması, pencere/kapı tipleri; bilinmiyorsa "..." (K21: uydurulmaz).
4. Varsa montaj paftası, üretim dosyası, fotoğraf.

Kaynak dosyalar (çizim, gerçek liste, montaj paftası) depoya girmez; Mac'te ve proje klasöründe durur. Depoya yalnız bizim okumamız (adları
maskelenmiş İş Emri ya da pafta okuması), kendi listemiz ve gerçek listeyle **tutan satırların** anahtarı ve adedi girer (Lokman, 23 Ekim kartı
"Yalnız tutanlar": tutan satırın adedi zaten bizim adedimizdir). Tutmayan satırların gerçek değeri raporda, proje klasöründe kalır. Kişisel
veri ve kaynak dosya kuralı D-13 ile gelir (BK-12 PR-K).

## Sıra (her projede aynı)

| # | Adım | Çıktı | Kim |
|---|---|---|---|
| 1 | Çizim okunur; projeden **pano birimli İş Emri** (K02; 125,5 cm aks; standart 100 / 60) ya da montaj paftası varsa pafta okuması kurulur | `testler/kor/projeler/<KOD>/` (`is_emri.json` ya da `yapi_pafta.json` + `pafta_katmani.json`) | Claude |
| 2 | Pano motoru çizer: aksli plan, alanlı kopya, montaj kopyası, görünüşler, IFC. Motor bir şeyi çizemiyorsa **o adım motor genişletme işine düşer**; elle tamamlanmaz | `cikti/` | Motor |
| 3 | **Kendi yükleme listemiz** üretilir ve **depoya commit'lenir**; araç kıyastan önce bunu, proje kaydını ve kalem sözlüğünü denetler (commit'li, çalışma ağacında değişmemiş) | `testler/kor/projeler/<KOD>/bizim_liste.json` | Motor |
| 4 | Gerçek liste **araçla** açılır ve satır satır kıyaslanır: `python3 -m testler.kor.kiyas --proje testler/kor/projeler/<KOD> --kaynak <liste>` (aşağıda › Araç). Her farkın sınıfı: girdi hatası · kural hatası · karar farkı · elle · pafta · liste hatası (KT raporlarındaki tanımlar); sınıf araçtan çıkmaz, `--siniflar` dosyasına gerekçesiyle yazılır | maskeli rapor (md, xlsx) proje klasöründe; `sonuc.json` depoda | araç + Claude |
| 5 | Yalnız **bizim hatalarımız** varsayılan hesabı değiştirir; gerçek listenin farklı yaptıkları ayrı katmanda toplanır, hangilerinin kural olacağına Lokman karar verir. Kural değişikliği ayrı öneren PR'dadır (kör test PR'ı hakemdir) | `kurallar/liste/prefabrik.json` (yeni sürüm) | Lokman |
| 6 | Rapor: nasıl yapıldı, sonuç (kaç satır doğru), hatalar ve düzeltmeler, karar bekleyenler, sorular | proje klasörü | Claude |
| 7 | Önceki PK'lar yeni kuralla **yeniden çözülür**; tutan satır bozulmamalı: `pytest testler/kor` (gerileme kapısı). Bozma bilerek yapılıyorsa sonuç gerekçeyle yeniden yazılır (`--sonuc-yaz`), ayrı PR'da ve Patron onayıyla | `testler/kor/projeler/<KOD>/sonuc.json` | Claude |

Bir PK, kıyastan sonra düzeltilmiş İş Emri'yle **`is_emri/PK<NN>.json`** olarak referans girdisine girebilir (pano motorunun girdileri `is_emri/`dedir;
`modeller/` genel motorun Yapı Tanımı klasörüdür, karıştırılmaz — D-12); kaynak ve doğrulama durumu dosyada yazar (D-07).

## Araç (`testler/kor/`, BK-12 PR-3)

Sıra her koşuda aynı; bir adım tutmazsa araç durur, nedenini yazar ve sonrakine geçmez:

1. **Bizim yanımız kayıtlı mı?** `bizim_liste.json`, `proje.json` ve kalem sözlüğü (`sozluk.json`) depoda commit'li ve değişmemiş olmalı:
   gerçek liste okunmadan önce bizim yanımız sabittir.
2. **Mühür tutuyor mu?** `testler/kor/muhur.json` depoda değişmemiş; kaynak dosyanın baytı ve SHA-256'sı bir kayıtla aynı; kayıt bu projenin ve bir
   yükleme listesinin. Tutmazsa dosyanın içeriği **okunmaz** (bir baytı değiştirilmiş, eksik ya da boş kopya durur).
3. **Açılabilir mi?** Kaydın durumu `acik` olmalı. `kor` ya da `kapali` kayıt, ancak Patron'un açılış kaydı varsa, kayıt bu dosyanın SHA-256'sını ve
   kendi listemizin commit'ini taşıyorsa açılır; kayıttaki sözlük commit'i bugünkünden farklıysa (sözlük açılıştan sonra değişmiş) sonuç ve rapor
   bunu yazar (› Kör 19 ve açılış kaydı).
4. **Okuma** (`oku.py`): PDF'in iki şablonu ve Portatifev Excel şablonu. Başlık bloğu (müşteri, temsilci, hazırlayan, sevkiyat yeri, tarih), telefon,
   sayfa ve dosya adları, personel ve imza satırları okunmaz; adı bir başlık etiketiyle başlayan satır (etiket yalnız, iki noktayla, ek
   sözcükle, tarihle ya da numarayla; Türkçe ya da ASCII) sütun başlığından sonra da okunmaz. Okunmayan satırların sayısı rapora, adedi sayı
   olanların sayısı sonuca da yazılır: paydaya girmezler.
5. **Eşleme** (`esle.py`, kalem sözlüğü `sozluk.json`): her gerçek satır bizim satırlarımızla grup, kalem ve ölçüyle eşlenir. Sonuç: varsayılan
   adetle aynı · toplam aynı, ayrım farklı · pafta sütunu tuttu · aday sütunu tuttu · adet ya da ölçü farklı · bizde yok · bizde fazla.
   **Doğru = aynı + ayrım + pafta + aday** (13 Ekim raporlarının tanımı). Ölçü: ölçüyle eşlenen gruplarda ölçüsü tutmayan satır adet tutsa da
   "farklı"; farklı bölünen kalemlerin toplandığı gruplarda toplamla birlikte ölçü kümesi kıyaslanır (iki yanda sayılı ölçü varsa her birinin
   öbür yanda eşi olmalı; gerçek yanın bütün satırları ve bizim yanın adedi dolu bütün satırları sayılı ölçülüyse ölçü başına toplam da), ayrı kalemler arasındaki dağılım kıyaslanmaz; bir yanda sayılı ölçü yoksa ("ADET") yalnız adet kıyaslanır. Ölçünün
   kıyaslanmadığı grup sözlükte gerekçesiyle yazar (`olcu_serbest`, ör. makas: bizde açıklık, gerçek listede boy). Bizim satırların sırası
   eşlemeyi değiştirmez.
6. **Sınıf:** proje başına sınıf dosyası (proje klasöründe); sınıfı yazılmamış fark "sınıflanmadı" sayılır.
7. **Rapor:** md ve xlsx; kod, m² ve satırlar. Ad, bayi adı ve dosya adı yazılmaz; telefona benzeyen her şey maskelenir.

Testler (`testler/kor/test_kor_kiyas.py`) her koşuda aracın sırasını ve ölçü kurallarını uydurma satırlarla, gerçek mühür kaydının kör ve kapalı
kayıtları reddettiğini ve durumların değişmediğini, açık sekiz projenin gerileme kapısını dener; kaynak liste gerekmez. Kapı tutan her satırın
bugünkü listede kayıttaki (kalem, ölçü) çiftlerini (ölçü yazısı ve sayılarıyla; grupta aynı yazıya inen iki farklı ölçü varsa ya da en büyük sayıyla eşlenen grupta aynı en büyük sayıyla yeni bir satır gelirse durur) ve kayıttaki sonucun sütununda aynı adedi ister; eşdeğer, tolerans ve kalan eşlemesinde
grubun ölçüleri, toplanan ve her satır gruplarında (bizde iki ya da daha çok sayılı ölçü ya da adedi boş ya da 0 olan sayılı ölçülü satır varsa)
grubun bütün bizim satırlarının değerleri (kalem, ölçü, varsayılan, pafta, aday) de kayıttaki gibi olmalı. Tam koşu `PORTMAN_KOR_TAM=1` ve depo dışındaki kaynak klasörüyle
(`PORTMAN_KOR_KAYNAK`): sayılar ve tutan satırlar gerçek listeden yeniden hesaplanır ve kayıtla aynı olmalı.

## Kör 19 ve açılış kaydı

- **Kör 19:** AP-06, AP-09, AP-11…18, AP-20…28. Listeleri `muhur.json`'da `kor`; hiçbir PR liste açmaz. Montaj paftaları ve DWG'ler kaynak olarak
  açılabilir, liste açılamaz.
- **AP-10** (≈ PK-03): listesi `kapali`, kör sayılmaz ama o da açılmaz. Açılmamış öteki mühürlü dosyalar da (`kapali`) aynı kuraldadır.
- **Yakın adlar:** AP-09, AP-08 (PK-07) ile; AP-17, AP-10 ile aynı adı ve m²'yi taşıyor. Bu ikisi kör test sayılmadan önce montaj paftaları
  karşılaştırılır; tasarım aynıysa o proje kör test listesinden çıkar (BK-12 planı).
- **Açılış:** her proje ayrı Patron kararıdır. Sıra: (1) kendi listemiz ve sözlük commit'lenir; (2) Patron kararıyla `muhur.json › acilislar`'a o
  projenin açılış kaydı eklenir: `{"karar": <Patron kararı ve saati>, "tarih": …, "sha256": <açılacak listenin özeti>, "liste_commit": <kendi
  listemizin commit'i>, "sozluk_commit": <sözlüğün commit'i>}` (ayrı commit); (3) araç koşar. Kayıttaki özet ya da liste commit'i tutmazsa araç açmaz;
  kayıt yalnız o dosyayı açar (projenin öteki mühürlü listeleri kapalı kalır).
- Açık sekiz projenin (PK-01…03, PK-05…08, TS-01) açılışları 13 Ekim'de bu sırayla yapıldı; saatleri `acilislar`'da. AP-01…05'in listeleri
  13 Ekim'de örnek olarak okundu (E1–E5); kör test değildir.

## Çelik KT'den farklar

- Motor **pano motorudur**, genel motor değil (D-12). Tanım İş Emri biçimindedir (`is_emri/*.json` gibi: `grid`, `konum_pano`, `acikliklar`) ya da
  montaj paftasından okunmuş geometridir (`yapi_pafta.json`), Yapı Tanımı 0.5 değil.
- Liste üreteci `motor/prefabrik_liste.py`, kuralları `kurallar/liste/prefabrik.json` (BK-12 PR-2…2f). Pafta kipinde paftanın kendi sayısı
  "pafta" sütununda, kuralın sonucu ayrıca "aday" sütununda yazar; kıyas üçüne de bakar.
- Pano sayımı: her pano tek parça (açıklık dahil), kesilmiş panolar ayrı kod; köşe parçası, üçlü H, iç köşe (30 × 60) ayrı kalemler (Astra v1.4.3 ve 6 Ekim; teyit Lokman).
- Çift katta: alt kat karkaslı (A3), üst kat A2 ile aynı (Lokman, 2 Ekim). Ara kat, döşeme ve merdiven (A4) kuralı yok; ilk çift kat PK'sında bu kalemler
  "kural yok" diye ayrı sayılır, uydurulmaz.

## Ne zaman biter

Kural motoru doğrulanmış sayılır: ardışık iki PK'da bizim hatamızdan kaynaklanan fark sıfır ve karar bekleyen madde kalmamışsa.
O zamana kadar her yeni proje kör testtir; sonra katalog modellerine geçilir (Lokman, 12 Ekim: "sonra katalog modellerine geçebiliriz").

## Durum (23 Ekim 2026)

- PK-01…03, PK-05…08 ve TS-01 açık (13 Ekim); girdileri, kendi listelerimiz ve tutan satırları `testler/kor/projeler/`. PK-01'in gerçek listesi
  stoktan düşülmüş (Lokman, 18 Ekim): sonucu bilgi içindir, gerileme kapısına girmez. PK-04 seriden çıktı (çelik karkas).
- Bugünkü Motor'la doğru toplam ve TS-01'in satır satır raporu proje klasöründe (`IE-09_atolye/BK-12_PR-3/`).
- Kör 19 kapalı; açılışları ayrı Patron kararı. AP-01…05'in paftaları okunmadı (BK-12 PR-4, hedef AP-01).
