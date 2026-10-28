# Fiyat defteri (İE-13)

Yükleme listesi × birim fiyat: Z-10'un liste yöntemi. Araç `araclar/fiyatla.py`, test `testler/test_fiyat_defteri.py`.

## Dosya

`defter_2026-10.json` (sürüm `2026-10-27-r02`). Fiyatlar TL. KDV durumu kaynak listelerde yazmıyor.

| Alan | İçerik |
|---|---|
| `kaynaklar` | Her kaynağın `kisa` adı (liste ve tarih) aracın çıktısında Kaynak sütununa yazılır. `EKIM87`: 87 m² yükleme listesi, 14 Ekim 2026. `HAZ`: malzeme listesi, 16 Haziran 2026. Patron ikisini 27 Ekim'de verdi (`patron_verdi`). `CTKB`: Eylül 2026 çelik tablosu; yalnız öneri kaynağı. |
| `hatlar.prefabrik.kalemler` | Anahtar `kalem \| olcu`, `motor/prefabrik_liste.py`'nin satırı. Örnek proje TK-01'dir: asma ve ters tavan listelerinin birleşimi, 130 kalem. |
| `hatlar.prefabrik.bantlar` | Pano eni bandı. Birebir anahtar yoksa en, Ekim listesinde görülen aralığa düşerse o fiyat alınır. 627,5 mm tam/yarım sınırı Patron'un 27 Ekim 22:08 onayıdır. |
| `hatlar.celik.kalemler` | Anahtar `kalem \| boyut`, genel motorun yükleme listesi satırı. Ç8201 ile Ç8801'in birleşimidir, 99 kalem. Birimi `kg` olan kalemde tutar satırın kg'ı × fiyat. |
| `hatlar.celik.atla` | Listedeki özet satırı ("Toplam …"). Fiyatlanmaz, iki kez sayılmaz. |
| `m2_yontemi` | Basit yöntemin (alan × m² fiyatı) fiyatları. Henüz yok, araç `--m2-fiyat` ile alır. |

Her kalemde şu alanlar var: `fiyat`, `birim`, `kaynak`, `kaynak_satir` (Ekim dosyasında satır numarası; Haziran'da TK-01 satırlarında satır numarası, çelik satırlarında ürün kodu), `kaynak_kalem`, `durum`, `onay` ve `not`.

## Kurallar

- **Fiyat uydurulmaz.** Kaynağı olmayan kalemde `fiyat` boştur. Araç o satırı "fiyatsız" diye sayar.
- **`onay: true`:** fiyat Patron'un verdiği listeden ya da onayladığı öneriden gelir.
  - Onay kalemin kendisi içindir. Çelikte TK-01'dekiyle aynı ürün "TK-01 onaylı kalemle aynı" diye onaylı sayılır.
  - Patron'un 27 Ekim 22:00 kararı ("son listeler") genel kaynaktır. Bu yüzden çelikte iki listeden birebir eşleşen kalem de onaylıdır (`durum: eşleşti`; r02).
- **`onay: false`:** öneridir. Yakın ürün, hesap ya da Patron'un vermediği kaynak (CTKB) olabilir. `fiyatla.py` bunları yalnız `--oneri` ile uygular ve "öneri" diye işaretler.
- **Kaynak sırası** (Patron, TK-01'de 22:01 ve 22:11):
  1. Önce `EKIM87`.
  2. Orada yoksa `HAZ`.
  3. İkisinde de yoksa `CTKB`.
  - Birebir eşleşme yakın eşleşmeden önce gelir.
- **Kişisel veri girmez.** Kaynak dosyalardaki müşteri, hazırlayan, telefon ve banka bilgisi deftere alınmaz; deftere yalnız kalem ve fiyat girer. Test bunu desenle denetler.
- **Yeni fiyat yeni sürümle girer.** Eski defter eski teklifi aynen verir. Yeni fiyat listesi gelince yeni dosya açılır (`defter_<yıl>-<ay>.json`) ve aracın varsayılanı ona çevrilir.

## Kullanım

```
python3 araclar/fiyatla.py <liste.json> [--oneri] [--duzeltme duzeltmeler.json] \
    [--alan 80 --m2-fiyat <TL/m²> --esik 15] [--json çıktı.json] [--excel çıktı.xlsx]
```
