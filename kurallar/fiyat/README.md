# Fiyat defteri (İE-13)

Yükleme listesi × birim fiyat: Z-10'un liste yöntemi. Araç `araclar/fiyatla.py`, test `testler/test_fiyat_defteri.py`.

## Tek fiyat kaynağı: CRM (D-72, mühür M-15; 9 Kasım 2026)

Lokman, 9 Kasım 2026 13:10: "bunu kural olarak al ve mühürle bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları çek";
"diğer tüm listeler konu dışı". 13:15 kartı: pencere de CRM'den ("Samet CRM'e eklesin").

- **Kaynak.** Yeni teklifin ve fiyatlı listenin her fiyatı CRM stok fiyatları API'sinden gelir. Aşağıdaki elle defterler (`EKIM87`, `HAZ`,
  `L45`, `CTKB`, `PATRON`) yeni teklifte kullanılmaz; yalnız kapanmış teklifi aynen vermek için yerinde durur. İstisna D-65: çırpı ipi 0 TL.
- **Günlük görüntü.** Sunucu her gün 06:15'te çeker (`vps/crm_fiyat.sh`, `portman-crm-fiyat.timer`): sunucuda `data/crm/`, Drive'da
  `Portman-Fiyat/`. Oturum teklifi o günün en yeni görüntüsüyle üretir.
- **Eşleme** `crm_esleme.json`: defterin kalemi (Motor'un liste anahtarı) → CRM kodu ve hesap (aynı, oran, çarp, boy, ağırlıklı ortalama,
  toplam). Fiyat yazmaz. `kaynak` bölümü mühürlü; kalemler PR'la değişir (yeni kalem, Lokman'ın birim cevabı, Samet'in eklediği ürün).
  Defter D-72'den sonra kapandı: Motor'un yeni anahtarı yalnız eşlemeye, hattın kalemlerinin sonuna girer (r05: TK-06'nın 15 kalemi;
  OSB, duvar alçıpanı, kiriş, pencere panelleri, nem bariyeri, alçıpan destek straforu, pencere karkası ve PVC pencereler).
- **Onay.** Eşleme `birebir` ya da `kural` ise onaylı; `yakın` ve `birim varsayımı` öneri (`--oneri`); `birim sorusu` ve `CRM'de yok`
  fiyatsız. O gün fiyatı 0 ya da boş olan kod, listede olmayan kod ve birden çok satırdaki kod fiyatsız. `bekletme`: Lokman'ın kararıyla şimdilik
  fiyatsız, CRM'de fiyatı olsa da yazılmaz (banyo dolabı, D-75).
- **Lokman'ın hesap kuralları (D-75, 10 Kasım).** Kutu profilin (kiriş ve kolon) CRM fiyatı 6 metrelik boyun fiyatıdır; parça fiyatı
  boyla orantılı, tam TL. Pencere üst paneli tam panonun (100 × 1250 × 2500) 1/5'i, alt paneli 1/3'ü.
- **KDV (D-76, 10 Kasım).** CRM fiyatı KDV hariçtir. Oran malzeme grubundan (Lokman'ın listesi): %20 metal aksam, betopan, EPS, kiremit
  desen sac, Boardex, alçıpan, OSB, Knauf, pencereler, vida, su tesisatı, boya grubu, dereler, mahya bandı, membran, PVC iniş, çelik
  paneller, shingle, çatı izolasyonu; KDV'siz iç kapı, dış (çelik) kapı, elektrik, vitrifiye; %10 trapez, sandviç panel, kutu profil.
  Listede olmayan 8 kalem %20 (Lokman'ın kartı, 10 Kasım 18:01): yapıştırma pano, kapı panoları, tek kat panel, tavan H'ı, PVC omega
  kapak, PVC betopan H'ı, acil müdahale kapağı, baca. Listede adı geçmeyen yerler de kuraldır (Lokman 18:05 "hepsini kural olarak
  kayda geç"): mahya, damlalık, panel kapaması metal aksam; uç, taş, dübel, şase pul, çırpı ipi vida; mastik, dayson, köpük boya
  grubu; duşakabin, banyo dolabı, batarya vitrifiye.
  Eşlemenin `kdv` bölümü: grup sırayla kalemin `kdv_grubu`'su, kodun `kodlar` kaydı, CRM satırının kategorisi (`kategoriler`).
  Grubu olmayan kalemin oranı yoktur (uydurulmaz): fiyatlı listede "KDV oranı yok", KDV dahil toplam eksik. Fiyatlı liste ve teklif
  satırda KDV oranı ve tutarı, toplamda KDV hariç, KDV ve KDV dahil yazar. Bayi formu (M-14) bu oranları okumaz.
- **Araç.** `araclar/crm_fiyat.py defter <görüntü> <defter.json>` görüntüyü bu şemada deftere çevirir; `fiyatla.py` ve `teklif.py`
  `--crm <görüntü>` ile aynısını yapar. Varsayılan defter yoktur: kaynak verilmezse araç durur. Kapanmış teklif: `--defter <o günkü defter>`
  (TK-04 r08 ve TK-05 `defter_2026-11.json`, TK-01 `defter_2026-10.json`). Fiyatsız kalemler: `crm_fiyat.py eksik <görüntü>`.

## Dosya

**Son elle defter `defter_2026-11.json` (D-72'den beri yalnız kapanmış teklif için; aşağıdaki "varsayılan" sözleri D-72'ye kadardır) (sürüm `2026-11-07-r13`; r11 D-62, r12 D-65, r13 D-67).** r13: TK-05'in hesaplanan 280 / 160 kalemleri (panolar, H'ler, 160'lık pencere karkası ve alt çerçeve, sandviç panel metre fiyatı ve kapaması) Patron onaylı (Lokman 7 Kasım 13:39 "tamamdır fiyatları kontrol ettim onaylıyorum"); fiyatlar aynı. r12: çırpı ipi prefabrikte ve çelikte 0 TL, hediye (`PATRON`, Lokman 6 Kasım 21:29 "çırpı ipini hediye veriyoruz ona değer 0 yaz"); fiyat 0 yalnız Patron'un sözüyle. r11: Araçların (`araclar/fiyatla.py`, `araclar/teklif.py`) varsayılanı. r10'un kopyası, prefabrik fiyatlar 45. hafta listesinden (`L45`, 3 Kasım 2026; Lokman 5 Kasım 23:00 "fiyatları buradan al", 23:10 yakın eşleşmeler için "Hepsini al"): TK-04 r08'in listede karşılığı olan bütün kalemleri onaylı (`durum` eşleşti, hesap ya da yakın; notunda dayanağı ve önceki fiyatı), aynı kalemin öteki boyları (pano eni, kiriş boyu, sağ kapı) ve D-36 eşdeğerleri; pano eni bandı listenin tam ve yarım pano fiyatıyla (çeyrek pano listede yok, dörtte biri öneri); kutu profil, trapez sac ve trapez mahya boy kuralları listenin fiyatıyla (SHS100x4 L 6000 2.892,25; trapez sacın metresi 299,56, 100 cm kapatır; mahya L 1000 167,54); TK-05'in r10'da hesaplanan 280 / 160 kalemleri aynı yöntemle yeni tabandan (r11'de öneri, r13'te onaylı). Listede karşılığı olmayanlar (makas kuralı, pencere karkası, metal tahta, mahya bandı, elektrikte birkaç kalem) ve TK-04'te olmayan, henüz eşlenmeyen kalemler (tek kat çatı paneli, metal kiremit mahyası, 5,5 × 76 vida, 60'lık tavan omegası, sandviç panel kapaması) önceki kaynağında. Çelik hattı r10'la aynı. Eski teklif eski defterle: `--defter kurallar/fiyat/defter_2026-10.json` (TK-01'in teklif testleri bu dosyayla). Test `testler/test_fiyat_defteri_45.py`.

**Önceki defter** `defter_2026-10.json` (sürüm `2026-11-05-r10`; r03 kiriş boy önerisini ekledi; r04'te TK-01'in onay bekleyen dört önerisi Patron'un onayıyla (28 Ekim 13:27, "ne varsa onaylıyorum") kalem olarak onaylı: kiriş L 3860, L 2610, L 1255 ve ikili kaçak akım rölesi; r05'te Lokman'ın 31 Ekim fiyat kuralları (D-36): 100'lük iç eleman dıştakiyle aynı, 100'lük 3'lü H 60'lık karşılığının fiyatı, kutu profil ve tek kat çatı paneli boyla orantılı ve onaylı, besleme kablo borusu ve kenar boyası hesapla; r06'da makas kuralı (D-37): makasın kg'ı saçaktan saçağa boyuyla orantılı, TK-03'ün gerçek listesinden 5,50 kg/m × 59 TL/kg; r07'de İE-27'nin yeni satırı "Trapez vida 5,5 × 25 (aşık ve omega)" 87 m² listesinden birebir, 3 TL; r08'de cumbalı prefabrik çatının (TK-04) ters mahyası Haziran listesinden birebir, 189 TL (çelikteki kayıtla aynı), kenar kutusu fiyatsız (iki listede de yok), trapez çatının vidası (5,5 × 60) 87 m² listesinden birebir 3 TL ve trapez sac mahyası L 1000 Haziran listesinden birebir 189 TL (D-50, M-11: prefabrikte sac ve mahya standart 100 cm kapatır); trapez sac Haziran'daki 80 cm kapatan sacın m² fiyatıyla, boy ve kapatmayla orantılı (D-51, Lokman 4 Kasım 21:37), mahyanın öteki boyları boyla orantılı; öteki fiyatların hiçbiri değişmedi; r09'da 120 × 180 özel pencere karkası Patron'dan 700 TL, Lokman 4 Kasım 23:20, ve ters mahya kenar kutusu 100 TL, teklifte "Metal tahta (galvaniz) · L 2800", 23:24; kaynak `PATRON`; r10'da TK-05'in (160'lık dış duvar, 280, sandviç panel çatı; D-60, BK-25) iki listede olmayan kalemleri 45. hafta listesinden (`L45`, Lokman 5 Kasım 12:37): birebir olan 160'lık ve 280'lik profil onaylı, pano (280 = 250 × 1,12; 160 = 100'lük + strafor farkı), kulaklı / dübelli H ortalaması, 160'lık pencere karkası, alt çerçeve ve sandviç panel metre fiyatı hesapla öneri; sağ çelik kapı solla aynı Haziran satırı, sandviç panel vidası 87 m² listesinden; var olan fiyatların hiçbiri değişmedi). Fiyatlar TL. KDV durumu kaynak listelerde yazmıyor.

| Alan | İçerik |
|---|---|
| `kaynaklar` | Her kaynağın `kisa` adı (liste ve tarih) aracın çıktısında Kaynak sütununa yazılır. `EKIM87`: 87 m² yükleme listesi, 14 Ekim 2026. `HAZ`: malzeme listesi, 16 Haziran 2026. Patron ikisini 27 Ekim'de verdi (`patron_verdi`). `CTKB`: Eylül 2026 çelik tablosu; yalnız öneri kaynağı. `PATRON` (r09): Patron'un thread'de kendi sözüyle verdiği fiyat, listede olmayan kalem için; kalemin notunda sözü, saati ve mesaj numarası (r12'de çırpı ipi 0 TL, hediye; D-65). `L45` (r10): 45. hafta malzeme satış listesi, 3 Kasım 2026; Patron 5 Kasım'da TK-05 için verdi. Yalnız iki listede olmayan kalemler için; listenin pano fiyatı yalnız dış 100 / iç 60 / 2500 seçimi için. |
| `hatlar.prefabrik.kalemler` | Anahtar `kalem \| olcu`, `motor/prefabrik_liste.py`'nin satırı. Örnek proje TK-01'dir: asma ve ters tavan listelerinin birleşimi, 134 kalem (r04'te İş Emri r06'nın üç kiriş boyu eklendi, r07'de İE-27'nin trapez vidası); r08'de TK-04'ün cumbalı çatısından iki kalem, trapez vidası ve trapez sac mahyası L 1000 (138). |
| `hatlar.prefabrik.bantlar` | Pano eni bandı. Birebir anahtar yoksa en, Ekim listesinde görülen aralığa düşerse o fiyat alınır. 627,5 mm tam/yarım sınırı Patron'un 27 Ekim 22:08 onayıdır. 100'lük karkaslı pano (iç kapı panosu ve dış çelik kapı panosu) en 1070–1250 2.200 (D-36). |
| `hatlar.prefabrik.boy_onerileri` | Kesilen parçanın kaydı olmayan boyu (ölçü "L <mm>") için boy kuralı: tam boyun fiyatından boyla orantılı, `yuvarlama` adımına yarım yukarı (varsayılan tam TL). Kayıt kalemi adıyla (`kalem`) ya da adının başıyla (`kalem_baslar`) eşler. r05'te (D-36, Lokman 31 Ekim) kutu profil kiriş ve kolon (6 m 5.000 TL) ile her çatının tek kat paneli (L 5450 1.650 TL, kuruşa) `onay: true`: her boy toplama girer. r08'de (D-51) trapez sac (L 2550 625 TL, `kapatma_m` 0,8: fiyat satırın `kapatma_m`'siyle de orantılı, m² fiyatı aynı; satırda kapatma yoksa uygulanmaz) ve trapez sac mahyası (L 1000 189 TL) onaylı. `onay: false` olan kural yalnız `--oneri` ile toplama girer; girmezse satırda `oneri_fiyat` olarak durur ve teklif onu sarı gösterir. |
| `hatlar.prefabrik.makas_kurali` | Makas satırının (adı `kalem_baslar`'dan biriyle başlar: ana çatının baş ve orta makası, yavru makas, cumba makası) birim fiyatı = kg × `kg_fiyat`; kg = `kg_m` × saçaktan saçağa boy. Boy "L <mm>" satırında L, "açıklık <mm>" satırında açıklık + 2 × `sacak_mm`. kg kuruşa, fiyat tam TL'ye yarım yukarı. r06 (D-37, Lokman 31 Ekim 16:00): 5,50 kg/m (TK-03'ün 12 makası 514,72 kg ÷ 93,60 m), 59 TL/kg (87 m² listesi), saçak 300 mm. Birebir kaydı olan anahtar kurala düşmez. Kubbe makası girmez. |
| `hatlar.celik.kalemler` | Anahtar `kalem \| boyut`, genel motorun yükleme listesi satırı. Ç8201 ile Ç8801'in birleşimidir, 99 kalem. Birimi `kg` olan kalemde tutar satırın kg'ı × fiyat. |
| `hatlar.celik.atla` | Listedeki özet satırı ("Toplam …"). Fiyatlanmaz, iki kez sayılmaz. |
| `m2_yontemi` | Basit yöntemin (alan × m² fiyatı) fiyatları. Henüz yok, araç `--m2-fiyat` ile alır. |

Her kalemde şu alanlar var: `fiyat`, `birim`, `kaynak`, `kaynak_satir` (Ekim dosyasında satır numarası; Haziran'da TK-01 satırlarında satır numarası, çelik satırlarında ürün kodu), `kaynak_kalem`, `durum`, `onay` ve `not`. İsteğe bağlı `teklif_adi` ve `teklif_olcu` (r09): teklifte ve fiyatlı listede satırın yazılan adı ve ölçüsü; Motor'un iç adı ve anahtar aynı kalır.

## Kurallar

- **Fiyat uydurulmaz.** Kaynağı olmayan kalemde `fiyat` boştur. Araç o satırı "fiyatsız" diye sayar.
- **`onay: true`:** fiyat Patron'un verdiği listeden ya da onayladığı öneriden gelir.
  - Onay kalemin kendisi içindir. Çelikte TK-01'dekiyle aynı ürün "TK-01 onaylı kalemle aynı" diye onaylı sayılır.
  - Patron'un 27 Ekim 22:00 kararı ("son listeler") genel kaynaktır. Bu yüzden çelikte iki listeden birebir eşleşen kalem de onaylıdır (`durum: eşleşti`; r02).
- **`onay: false`:** öneridir. Yakın ürün, hesap ya da Patron'un vermediği kaynak (CTKB) olabilir. `fiyatla.py` bunları yalnız `--oneri` ile uygular ve "öneri" diye işaretler.
- **Kaynak sırası** (Patron, TK-01'de 22:01 ve 22:11):
  1. r11'den (`defter_2026-11.json`, D-62) prefabrikte önce `L45` (45. hafta listesi; Patron 5 Kasım 23:00).
  2. `L45`'le henüz eşlenmeyen kalem önceki kaynağında: `EKIM87`, orada yoksa `HAZ`, Patron'un verdiği fiyat `PATRON`.
  3. Hiçbirinde yoksa `CTKB`.
  - r10'a kadar (`defter_2026-10.json`): önce `EKIM87`, sonra `HAZ`, sonra `L45` (r10, 160'lık ve 280'lik kalemler), sonra `CTKB`.
  - Birebir eşleşme yakın eşleşmeden önce gelir.
- **Kişisel veri girmez.** Kaynak dosyalardaki müşteri, hazırlayan, telefon ve banka bilgisi deftere alınmaz; deftere yalnız kalem ve fiyat girer. Test bunu desenle denetler.
- **Yeni fiyat yeni sürümle girer** (D-72'ye kadar). Eski defter eski teklifi aynen verir. D-72'den beri yeni elle defter açılmaz; fiyat her gün CRM'den gelir (yukarıda).

## Kullanım

```
python3 araclar/fiyatla.py <liste.json> (--crm <CRM görüntüsü.json> | --defter <kapanmış teklifin defteri>) [--oneri] [--duzeltme duzeltmeler.json] \
    [--alan 80 --m2-fiyat <TL/m²> --esik 15] [--json çıktı.json] [--excel çıktı.xlsx]
```
