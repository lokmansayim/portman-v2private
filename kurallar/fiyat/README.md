# Fiyat defteri (İE-13)

Yükleme listesi × birim fiyat: Z-10'un liste yöntemi. Araç `araclar/fiyatla.py`, test `testler/test_fiyat_defteri.py`.

## Dosya

`defter_2026-10.json` (sürüm `2026-10-31-r05`; r03 kiriş boy önerisini ekledi; r04'te TK-01'in onay bekleyen dört önerisi Patron'un onayıyla (28 Ekim 13:27, "ne varsa onaylıyorum") kalem olarak onaylı: kiriş L 3860, L 2610, L 1255 ve ikili kaçak akım rölesi; r05'te Lokman'ın 31 Ekim fiyat kuralları (D-36): 100'lük iç eleman dıştakiyle aynı, 100'lük 3'lü H 60'lık karşılığının fiyatı, kutu profil ve tek kat çatı paneli boyla orantılı ve onaylı, besleme kablo borusu ve kenar boyası hesapla; öteki fiyatların hiçbiri değişmedi). Fiyatlar TL. KDV durumu kaynak listelerde yazmıyor.

| Alan | İçerik |
|---|---|
| `kaynaklar` | Her kaynağın `kisa` adı (liste ve tarih) aracın çıktısında Kaynak sütununa yazılır. `EKIM87`: 87 m² yükleme listesi, 14 Ekim 2026. `HAZ`: malzeme listesi, 16 Haziran 2026. Patron ikisini 27 Ekim'de verdi (`patron_verdi`). `CTKB`: Eylül 2026 çelik tablosu; yalnız öneri kaynağı. |
| `hatlar.prefabrik.kalemler` | Anahtar `kalem \| olcu`, `motor/prefabrik_liste.py`'nin satırı. Örnek proje TK-01'dir: asma ve ters tavan listelerinin birleşimi, 133 kalem (r04'te İş Emri r06'nın üç kiriş boyu eklendi). |
| `hatlar.prefabrik.bantlar` | Pano eni bandı. Birebir anahtar yoksa en, Ekim listesinde görülen aralığa düşerse o fiyat alınır. 627,5 mm tam/yarım sınırı Patron'un 27 Ekim 22:08 onayıdır. 100'lük karkaslı pano (iç kapı panosu ve dış çelik kapı panosu) en 1070–1250 2.200 (D-36). |
| `hatlar.prefabrik.boy_onerileri` | Kesilen parçanın kaydı olmayan boyu (ölçü "L <mm>") için boy kuralı: tam boyun fiyatından boyla orantılı, `yuvarlama` adımına yarım yukarı (varsayılan tam TL). Kayıt kalemi adıyla (`kalem`) ya da adının başıyla (`kalem_baslar`) eşler. r05'te (D-36, Lokman 31 Ekim) kutu profil kiriş ve kolon (6 m 5.000 TL) ile her çatının tek kat paneli (L 5450 1.650 TL, kuruşa) `onay: true`: her boy toplama girer. `onay: false` olan kural yalnız `--oneri` ile toplama girer; girmezse satırda `oneri_fiyat` olarak durur ve teklif onu sarı gösterir. |
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
