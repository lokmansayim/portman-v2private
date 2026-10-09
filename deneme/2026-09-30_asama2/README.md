# 30 Eylül · Aşama 2 aday karşılaştırmasının çalışma kodu

Rapor: `docs/raporlar/2026-09-30_Asama2_3arti1_Aday_Karsilastirmasi.md`. İş emri: `docs/is_emirleri/IE-04.md`.

Bu klasör üç şey taşır:
- raporun sayılarını ve görsellerini yeniden üreten betik;
- dışarıdan gelen bir çizimi (ör. Astra'nın DXF'i) aynı zincirden geçirip katalog kaynağıyla kıyaslayan yol;
- küçük çıktılar.

Depo koduna ve canlıya dokunmaz. Kod v1.1.1 dışındadır; K-A9 (kaynak uygunluk denetimi) kodlanırken asıl yerine alınacak.

## Dosyalar

| Dosya | Ne yapar |
|---|---|
| `kos.py` | Çıkarıcı → İş Emri → Motor v1.1; kaynak ve tanı görseli; IFC4 ve şema doğrulaması. Motor'un çizdiğini kaynak sayılarıyla yan yana yazar (`kaynak_karsilastirma.txt`); hüküm vermez |
| `kaynak_sayimlari.json` | Adayların kaynak sayıları: pencere ve kapı (katalog paftasında elle sayıldı) ve P9401 ile P9201'in oda etiketleri |
| `pafta_ayir.py` | Katalog DXF'inden bir adayın paftasını tek başına bir DXF'e çıkarır. Katmanlar, bloklar, ölçüler ve başlık korunur |
| `sonuc/` | 30.09 koşumunun küçük çıktıları (aday başına `is_emri.json`, `cikarim_raporu.md`, `motor_validation.json`; `ozet.txt`) |

## Katalog adaylarını yeniden koşmak

```
python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör>
```

- **Adaylar:** Beş aday koşulur: P9401, P9201, P9501, P1051, P1121. Motor her biri için DXF, PDF, BOM ve `validation.json` üretir.
- **Görseller:** Kaynak görseli (`<kod>_kaynak.png`) ve çıkarıcının tanı görseli (`<kod>_tani.png`).
- **IFC:** P9401 ve P9201 için aynı İş Emri'nden IFC4 üretilir, özetiyle birlikte. 23.09 kodu geçici klasörde tek `cozumleyici` paketinde birleştirilir; Motor yamasızdır.
- **Çıktı:** `ozet.txt` (Motor tarafı) ve `kaynak_karsilastirma.txt` (kaynakla kıyas).
- **Süre:** yaklaşık 2,5 dakika.

## Dışarıdan gelen bir çizimi denetlemek

```
python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör> --dxf <çizim.dxf> --kodlar P9401 [--ifc P9401]
```

- **`--kodlar`:** Tek aday olmalı. Kıyasın yapılacağı katalog adayıdır.
- **Pafta başlığı:** Çizimde "PORT - P9401" gibi bir başlık varsa betik onu kendisi bulur ve çıkarıcıya seçici olarak verir. Böylece katalogdaki paftayla aynı bölge okunur.
  - Başlık yoksa bütün dosya okunur.
  - Duvar gövdesi parçalıysa çıkarıcı "uzak duvar parçası" atabilir; betik bu durumda uyarır. P9201'de başlıksız kopyada 6 pencereden 1'i okundu.
  - `--secici` ile başlık elle verilebilir.
- **Okunabilen çizim** (`motor/cikarici.py`'den):
  - birim cm;
  - duvarlar `0` ya da `DUVAR` katmanında, pencereler `Pencere`, kapılar `Kapı`, veranda `Veranda`;
  - dış kutu 125,5·nx + 20 × 125,5·ny + 10 cm (±2,5);
  - iç duvarlar aksta (±10,5 cm);
  - oda adı ve m² odanın içinde MTEXT olarak; pencere ölçüsü "120/120" biçiminde;
  - eşya yazılarında oda adı sözcüğü yok (P9501'de "çamaşır makinesi" oda sanıldı).
- **Yol sınandı (30.09):** `pafta_ayir.py` ile beş adayın paftası ayrı DXF'e çıkarıldı ve bu yoldan geçirildi. Beşinin İş Emri'si katalog koşumuyla aynı çıktı; fark yalnız dosya adında. Başlığı silinmiş P9201 kopyasında uyarı doğru verildi.

```
python3 deneme/2026-09-30_asama2/pafta_ayir.py --cikti <klasör> P9401 P9201 P9501 P1051 P1121
```

## 30.09 yeniden koşum sonucu

- Beş adayın `is_emri.json`'ı ve iki adayın `motor_girdi.json`'ı ilk koşumla bayt bayt aynı.
- IFC sayıları rapordakiyle aynı:
  - P9401: 49 duvar, 7 pencere, 5 kapı, 6 mahal;
  - P9201: 48 duvar, 6 pencere, 5 kapı, 7 mahal.
- İki IFC'de şema hatası 0.
- Kaynakla kıyas rapordakiyle aynı. P9401'de odalar %2,4 içinde, veranda 12,0 ↔ 7,88. P9201'de hol 1,47 ↔ 6,6, salon 32,72 ↔ 27,55, net oda toplamı %0,0.

Motor PDF'leri, DXF'ler, IFC'ler ve görseller depoya alınmadı; betik yeniden üretir.
- İnsan kabulü için PDF'ler ve IFC'ler Mac'te: `23_Asama2_Adaylar/`.
- Adayların tek paftalık kaynak DXF'leri Mac'te: `24_Astra_Cizimler/kaynak_dxf/`.

## Dikkat

- **Motor doğrulaması kaynağa uygunluk değildir.** Motor'un `passed` sonucu beş adayın beşinde "geçti"; P9501 ve P1051'in oda yerleşimi yanlış.
- **Kıyas hüküm vermez.** Geçerlilik eşikleri K-A9 kararıyla konur.
- **`ifc_uret.py`'ye başlık verilmeli.** Varsayılan başlık 23.09'daki bayi planının adını taşır.
- **Kaynak görseli beyaz zeminle çizilir.** Aksi hâlde renk 7 çizgiler görünmez (P9201'de duvarlar kaybolmuştu).

## Kişisel veri

Girdi yalnız katalog DXF'i. Çıktılarda ad, telefon ya da adres yok (30.09'da tarandı).
