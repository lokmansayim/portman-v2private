# Ürün kimlik kartları

Her ürünün kimlik kartı burada, `kartlar.json`'da yazılır (İE-15, D-24). Kart bir ürünü tanımlar: listedeki adı ve grubu, ölçüsü, birimi, nerede durduğu, nasıl sayıldığı, IFC tür sınıfı, montaj paftasında hangi anahtarla sayıldığı, kaynağı ve durumu. Fiyat kartta yoktur.

## Modelde kart

`python -m motor.kart_model <İş Emri.json> <klasör>` bugünkü IFC'yi (`motor.ifc_uret`) üretir ve kopyasında her parçayı kartına bağlar:

- Kart IFC'de bir tür nesnesidir (`IfcWallType`, `IfcMemberType`, `IfcDoorType`…). Kartın alanları türde `PortatifEv_Kart` setinde durur.
- Parçaya özgü alanlar örnekte `PortatifEv_Parca` setindedir: kart kodu, paftadaki anahtarı (`PaftaAnahtari`), bugünkü katalog kodu (`KatalogKodu`), uygulanan kural.
- Çıktılar: `<kod>_model.ifc` (Bonsai'de açılır), `<kod>_kart_sayim.json`, `<kod>_kart_katalogu.xlsx`. Bugünkü `<kod>.ifc` değişmez; kart modeli onun parçalarını aynı kimlik, yer ve geometriyle taşır.

Bonsai bakma yeridir: sayı bizim kodumuzdan gelir, Bonsai'de yapılan değişiklik geri okunmaz. Kartı düzeltmek için bu dosya düzeltilir ve model yeniden üretilir.

## Kurallar

- **Kod kalıcıdır.** Bir kod başka ürüne verilmez; kilidi `testler/kimlik/veri/kart_kodlari.json`'dadır. Yeni kart kilide de eklenir.
- **Kart kodu katalog kodundan ayrıdır.** Bugünkü malzeme kataloğunun kodu (D01, D09…) boya göre verilir ve projede yeni boy çıktıkça yenisi eklenir. Kart kodu ürünü gösterir, boyla değişmez, bu yüzden tirelidir (D-01). Aile harfleri katalogla aynıdır.
- **Kartı olmayan parça sayılmaz.** Bir parça tam bir karta uyar. İki karta uyarsa model üretilmez; hiçbirine uymazsa "kural yok" yazar.
- **Ayrıca listelenen parçalar.** Görünüm (üçlü H'nin yüz görünümü), bileşen (makasın çubukları) ve kartsız parçalar sayılmaz, ayrı listelenir. Kartsız olanlar bu dosyada nedeniyle yazılıdır: çatı yüzü, alın, zemin betonu, boşluk.
- **Yerleşim kuralı başka dosyadadır.** Kartı parçaya bağlayan yerleşim kuralı (ör. H türü) `kurallar/yerlesim/prefabrik.json`'dadır. Liste kurallarındaki değerler (makas aralığı) `kurallar/liste/prefabrik.json`'dan okunur, iki yerde yazılmaz.
