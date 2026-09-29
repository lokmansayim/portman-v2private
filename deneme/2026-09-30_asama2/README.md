# 30 Eylül · Aşama 2 aday karşılaştırmasının çalışma kodu

Rapor: `docs/raporlar/2026-09-30_Asama2_3arti1_Aday_Karsilastirmasi.md`. İş emri: `docs/is_emirleri/IE-04.md`.

Bu klasör raporun sayılarını ve görsellerini yeniden üreten betiği ve küçük çıktıları taşır. Depo koduna ve canlıya dokunmaz. Kod v1.1.1 dışındadır; K-A9 (kaynak uygunluk denetimi) kodlanırken asıl yerine alınacak.

## Yeniden koşmak

```
python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör>
```

- Beş aday için (P9401, P9201, P9501, P1051, P1121): çıkarıcı → İş Emri → Motor v1.1 (DXF, PDF, BOM, `validation.json`).
- Kaynak görseli (`<kod>_kaynak.png`, katalog DXF'indeki pafta) ve çıkarıcının tanı görseli (`<kod>_tani.png`).
- P9401 ve P9201 için aynı İş Emri'nden IFC4 ve IFC özeti. 23.09 kodu geçici klasörde tek `cozumleyici` paketinde birleştirilir; Motor yamasızdır.
- Özet: `<klasör>/ozet.txt`. Süre yaklaşık 2,5 dk.

Gerekenler: Python 3.11, ezdxf 1.4.4, matplotlib, shapely, numpy, pillow, pymupdf, ifcopenshell 0.8.5.

Raporun yan yana görselleri (`docs/raporlar/gorseller/asama2/`) kaynak görseliyle Motor'un `preview.png`'sinin elle birleştirilmesiyle yapıldı. Birleştirme betiği yok.

## 30.09 yeniden koşum sonucu

Betik depoya alınırken bir kez daha koşuldu:
- beş adayın `is_emri.json`'ı ve iki adayın `motor_girdi.json`'ı ilk koşumla bayt bayt aynı;
- IFC sayıları rapordakiyle aynı: P9401 49 duvar, 7 pencere, 5 kapı, 6 mahal; P9201 48 duvar, 6 pencere, 5 kapı, 7 mahal;
- iki IFC'de şema hatası 0.

Çıktılar `sonuc/`'ta:
- aday başına `is_emri.json`, `cikarim_raporu.md` ve `motor_validation.json`;
- `ozet.txt`.

Motor PDF'leri, DXF'ler, IFC'ler ve görseller depoya alınmadı; betik yeniden üretir. İnsan kabulü için PDF'ler ve IFC'ler Mac'teki çalışma klasöründe (`23_Asama2_Adaylar/`).

## Dikkat

- Motor'un `passed` sonucu kaynağa uygunluk değildir. Beş adayın beşi "geçti"; P9501 ve P1051'in oda yerleşimi yanlış. Kaynaktaki kapı ve pencere sayıları görüntüden elle sayıldı (rapor §2).
- `ifc_uret.py`'ye başlık verilmeli. Varsayılan başlık 23.09'daki bayi planının adını taşır.
- Kaynak görseli beyaz zeminle çizilir. Aksi hâlde renk 7 çizgiler görünmez (P9201'de duvarlar kaybolmuştu).

## Kişisel veri

Girdi yalnız katalog DXF'i. Çıktılarda ad, telefon ya da adres yok (30.09'da tarandı).
