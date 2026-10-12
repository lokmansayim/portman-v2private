# Prefabrik kör testi · protokol (İE-10, 12 Ekim 2026)

Kaynak: Lokman, 12 Ekim 2026 23:10: "gerçek yükleme listesi olan tek prefabrik P6001 değil; sıra sıra sana vereceğim; çift kat gerçek yükleme
listesi olanı da vereceğim; kural motorunu doğrulayana kadar kör testi de yaparsın." Çelikteki KT-01/02/03 (`docs/raporlar/2026-10-0x_Kor_Test_KT0x.md`)
nasıl yapıldıysa prefabrikte de öyle yapılır; farklar aşağıda. Karar: D-10.

## Kod

Prefabrik kör test projeleri **PK-01, PK-02, …** (çelik KT'den ayrı sayaç). Tek kat ve çift kat aynı sayaçta; kat sayısı tanımda yazar.
Bayiye adsız sunulur (kod, m², oda programı, kat sayısı) — çelik KT'lerdeki gibi.

## Lokman'dan gelen

Her proje için, elden geldiğince:

1. **Çizim:** plan (DWG/DXF ya da PDF), görünüşler varsa; çift katta her katın planı.
2. **Gerçek yükleme listesi:** uygulanmış projenin listesi (Excel ya da PDF). **Kendi listemiz depoya kaydedilene kadar açılmaz.**
3. **Teknik özellikler:** duvar kalınlığı (standart 100 / 60 değilse), yükseklik, çatı tipi ve kaplaması, pencere/kapı tipleri; bilinmiyorsa "..." (K21: uydurulmaz).
4. Varsa montaj paftası, üretim dosyası, fotoğraf.

Dosyalar depoya alınabilir (D-11: ad sorun değil; telefon ve T.C. kimlik numarası yok). Yer: `deneme/<tarih>_pk_<NN>/kaynak/`.

## Sıra (her projede aynı)

| # | Adım | Çıktı | Kim |
|---|---|---|---|
| 1 | Çizim okunur; projeden **pano birimli İş Emri** kurulur (K02; 125,5 cm aks; standart 100 / 60; ölçüye kesim gerekiyorsa son pano kesilir) | `deneme/<tarih>_pk_<NN>/tanim/PK<NN>.json` | Claude |
| 2 | Pano motoru çizer: aksli plan, alanlı kopya, montaj kopyası, görünüşler, IFC. Motor bir şeyi çizemiyorsa (çift kat, ölçüye kesim) **o adım bu projede motor genişletme işine düşer**; elle tamamlanmaz | `cikti/` | Motor |
| 3 | **Kendi yükleme listemiz** yöntem B ile çıkarılır ve **depoya kaydedilir** (commit zamanı yazılır) | `sonuc/PK<NN>_liste.json` + xlsx | Motor |
| 4 | Gerçek liste açılır; satır satır karşılaştırılır. Her farkın sınıfı: girdi hatası · kural hatası · karar farkı · elle · pafta (KT raporlarındaki tanımlar) | `sonuc/PK<NN>_kiyas.md` | Claude |
| 5 | Yalnız **bizim hatalarımız** varsayılan hesabı değiştirir; gerçek listenin farklı yaptıkları ayrı katmanda toplanır, hangilerinin kural olacağına Lokman karar verir | `kurallar/liste/kurallar.json` (yeni sürüm) | Lokman |
| 6 | Rapor: nasıl yapıldı, sonuç (kaç satır aynı), hatalar ve düzeltmeler, karar bekleyenler, sorular | `docs/raporlar/<tarih>_Kor_Test_PK<NN>.md` | Claude |
| 7 | Önceki PK'lar yeni kuralla **yeniden çözülür**; tutan satır bozulmamalı (kural kitabı "Kural nasıl eklenir" §5) | `dogrula.py` | Claude |

Bir PK, kıyastan sonra düzeltilmiş İş Emri'yle **`is_emri/PK<NN>.json`** olarak referans girdisine girer (pano motorunun girdileri `is_emri/`dedir;
`modeller/` genel motorun Yapı Tanımı klasörüdür, karıştırılmaz — D-10); kaynak ve doğrulama durumu dosyada yazar (D-07). Kör tanım `deneme/` altında
tarih kaydı olarak kalır.

## Çelik KT'den farklar

- Motor **pano motorudur**, genel motor değil (D-10). Tanım İş Emri biçimindedir (`is_emri/*.json` gibi: `grid`, `konum_pano`, `acikliklar`), Yapı Tanımı 0.5 değil.
- Liste yöntemi **B** (tavan omegası, aşık, saçak ve alın sacı, baş makas Z'si); çelikte yöntem A. Yöntem B kalemlerinin kuralları şu an iki listeye uydurulmuş
  (`uydurma`); PK'lar bunları `liste`/`lokman` durumuna çıkaracak.
- Pano sayımı: her pano tek parça (açıklık dahil), kesilmiş panolar ayrı kod; köşe parçası, üçlü H, iç köşe (30 × 60) ayrı kalemler (Astra v1.4.3 ve 6 Ekim; teyit Lokman).
- Çift katta: alt kat karkaslı (A3), üst kat A2 ile aynı (Lokman, 2 Ekim). Ara kat, döşeme ve merdiven (A4) kuralı yok; ilk çift kat PK'sında bu kalemler
  "kural yok" diye ayrı sayılır, uydurulmaz.

## Ne zaman biter

Kural motoru doğrulanmış sayılır: ardışık iki PK'da bizim hatamızdan kaynaklanan fark sıfır ve karar bekleyen madde kalmamışsa.
O zamana kadar her yeni proje kör testtir; sonra katalog modellerine geçilir (Lokman, 12 Ekim: "sonra katalog modellerine geçebiliriz").

## Bekleyen

- **PK-01 geldi (12 Ekim 23:52): Huma 60 m² tek kat** (`deneme/2026-10-13_pk_01/`). Okuma yapıldı (`PK01_okuma.md`), İş Emri taslağı yazıldı; gerçek liste **mühürlü** (SHA kaydedildi, açılmadı). Pano motoru bu projeyi çizemiyor: aks dışı ön duvar (795), kesim önde (111,5), panoyu aşan pencere, alıcıya ait kapı → 2–3. adımlar motor genişletme işini bekliyor.
- P6001'in yeniden çizimi: Lokman'ın vereceği doğru kaynakla (`docs/sartname/modeller/P6001.md`).
- Pano motorunun genişletilmesi: ölçüye kesim, kalınlık seçeneği, çift kat — PK-01'in ihtiyacına göre ayrı iş emri.
