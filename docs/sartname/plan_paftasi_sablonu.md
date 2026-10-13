# Plan paftası şablonu ve her işte üretilecek çizimler

Kaynak: Lokman, 6 Ekim 2026 19:46. Ekinde "Örnek Şablon" adlı tek sayfalık PDF vardı (AutoCAD çıktısı).
Şablon dosyası kişi adı ve gerçek bir proje kodu taşıdığı için depoya alınmadı; burada yalnız düzeni ve ölçüleri durur.

## Kurallar (Lokman, 6 Ekim 19:46)

1. **Plan paftası bundan sonra "Örnek Şablon"un aynısı olur.** Önceki plan paftasında eksik yoktu, çizim kuralları doğru uygulanmıştı; değişen paftanın biçimidir.
2. **Görünüşler her seferinde üretilir.** Dört cephe: ön, arka, sol, sağ.
3. **Çizim pano pano yapılır.** Görünüşlerde ve 3B modelde her pano ayrı parçadır ve pafta kodunu taşır (Ö1…, A1…, SL1…, SĞ1…).

Bunların dışında kalanlar (yükleme listesi, IFC, Blender dosyası) için "her seferinde" denmedi; istenince üretilir.

## Şablonun düzeni (ölçülen)

Sayfa A4 yatay, 842 × 595 pt. Ölçüler pt; x soldan, y yukarıdan. Köşeler yuvarlak (yarıçap ≈ 4 pt), çizgi 0,72 pt siyah.

| Alan | Sol, üst, sağ, alt | İçerik |
|---|---|---|
| Dış çerçeve | 10,3 · 2,4 · 835,8 · 590,8 | Köşeli, kalın |
| Çizim alanı | 22,9 · 15,0 · 686,8 · 522,3 | Plan, sol yan görünüş, ön görünüş |
| Bina özellikleri | 691,9 · 15,0 · 824,9 · 249,9 | Başlık ve 15 satır; sütun bölmesi x = 761,4 |
| Özel istekler | 691,7 · 255,6 · 824,6 · 521,0 | Numaralı maddeler |
| Antet sol | 22,9 · 528,6 · 277,9 · 578,3 | Şablonda boş |
| Antet orta | 282,4 · 528,6 · 686,8 · 578,3 | 4 satır; sütun bölmesi x = 423,8 |
| Antet sağ | 691,7 · 527,2 · 824,6 · 578,3 | 4 satır; sütun bölmesi x = 760,1 |

Çizim alanının içi:

- **Plan** ortada, üstte. Arka cephe yukarıda, ön cephe aşağıda.
- **Sol yan görünüş** planın solunda, 90° döndürülmüş: zemin solda, çatı plana bakar. Düşeyde planla aynı hizadadır (arka uç yukarıda).
- **Ön görünüş** planın altında, planla aynı x hizasında. Sağında duvar yüksekliği ölçüsü.
- Görünüş başlıkları gri, altı çizili: "SOL YAN GÖRÜNÜŞ" (dikey), "ÖN GÖRÜNÜŞ".

Tablolar:

- **Bina özellikleri** satırları, sırayla: Bina Yüksekliği, Dış Duvarlar, İç Duvarlar, Panel Türü, Çatı Şekli, Çatı Eğimi, Çatı Kaplaması, Çatı Kaplama Rengi, Dış Kapı, İç Kapılar, Pencereler, Vasistaslar, Dış Boya Rengi, İç Boya Rengi, Köşe ve Söveler.
- **Antet orta** satırları: Proje Kodu, İlgili Kişi-Telefon, Sevk Adresi, Proje Adı & M².
- **Antet sağ** satırları: Tarih, Çizen, Kontrol, Onay.
- Bilinmeyen değer "..." yazılır (şablonda da öyle).

Yazı ve renk:

| Öğe | Yazı | Renk |
|---|---|---|
| Tablo ve antet | Comic Sans MS, 7,3 pt | Siyah |
| "BİNA ÖZELLİKLERİ" başlığı | Comic Sans MS, 10,9 pt | Koyu kırmızı `#991B1E` |
| Özel istekler | Comic Sans MS, 7,6 pt | Koyu kırmızı `#991B1E` |
| Ölçü yazısı | Arial, 10,7 pt | Siyah |
| Ölçü çizgisi ve çentiği | — | Açık mavi `#6EC2DD` |
| Mahal adı ve m² | Arial, 8,4 ve 8,6 pt | Gri `#939598` |
| Pencere etiketi (120x120, V.60x40) | Comic Sans MS, 5,0 pt | Siyah |
| Kapı eni | Comic Sans MS, 3,6 pt | Gri |
| Tefriş (tezgah, eviye, ocak, klozet, lavabo, duş) | — | Turuncu `#DDA56E` |
| Açık mahal (veranda) kenarı | Kesik çizgi | Kırmızı `#FF0000` |
| Görünüş başlığı | Comic Sans MS, 8,0 pt, altı çizili | Gri |

Plan çizimi:

- Duvarlar çift çizgi; pano ekleri duvarı kesen kısa çizgiyle görünür. Köşe ve birleşim parçaları açık mavi küçük kutu.
- Mahal adı büyük harf, altında tam sayıya yuvarlanmış m². Yaşam alanı "SALON+MUTFAK" diye yazılır.
- Kapı: kanat açık mavi kalın çizgi, açılma yayı siyah kesik çizgi, yanında eni.
- Pencere: duvar içinde açık mavi çerçeve, etiketi dış yüzde.
- Ölçü zinciri dört yanda: içte oda bölmeleri, dışta toplam dış ölçü. Ölçüler cm, tam sayı; parçaların toplamı dış ölçüye eşittir.
- Şablonun ölçeği 0,2975 pt/cm (yaklaşık 1:95). Yapı büyüdükçe ölçek çizim alanına sığacak kadar küçülür; şablondakinden büyük tutulmaz.

Görünüş çizimi:

- Duvar beyaz, pano ekleri düşey çizgi; köşe dikmeleri gri.
- Çatı kaplaması, "Çatı Kaplama Rengi" satırındaki renkle boyanır ve trapez çizgileri taşır. Renk bilinmiyorsa gri çizilir.
- Pencerede açılan kanat kırmızı kesik üçgenle, sabit cam eğik çizgilerle gösterilir. Dış kapı kahverengi, yatay çizgili.
- Altta gri taş desenli subasman şeridi.

## Ana koddaki karşılığı (İE-08, 12 Ekim 2026)

`motor/genel/sablon_pafta.py`: aynı düzen ve kurallar (sayfa, tablolar, yazı ve renkler, ölçek), geometri genel motordan (Yapı Tanımı 0.5,
cm, serbest aks: duvarlar, mahaller ve açıklıklar `yapi.kur`, sol yan ve ön görünüş `sahne` izdüşümü, çatı profili `cati_genel`).
Çıktı `<kod>_pafta.pdf` (A4 yatay, 2 sayfa: 1. sayfa şablonun aynısı, 2. sayfa dört görünüş ve çatı planı) ve `<kod>_pafta_sablon.png`
önizleme; `python -m motor.genel.uret` her modelde üretir, bayiye giden paftadır (A3). Çelikte pano eki çizilmez (kural yok; 8a dışı).
Antet ve tablolar İş Emri zarfından ve tanımdan: Proje Kodu = İş Emri no, Proje Adı & M² = model kodu ve m², Tarih = üretim günü
(`time.gmtime`; referans koşusunda sabit), Çizen, Kontrol ve Onay "Portman" (12 Ekim 14:53), İlgili Kişi-Telefon = bayinin adı ve
kart numarası (zarf `bilgi`; D-09, PR-2), antetin üstünde küçük "TASLAK · üretim projesi değildir" (8b mühendis kabulüne kadar;
`pafta_sablonu.json › taslak_ibaresi`, D-10); Bina özellikleri tanım ve kural kitabından
(yükseklik, duvarlar, çatı şekli/eğimi/kaplaması, kapı ve pencere sayım ve ölçüleri), gerisi "..."; Özel istekler = bayinin değişiklik
cümleleri, yoksa "...". Yazı tipleri `motor/genel/font/` (Comic Relief ve Arial'in ölçüdeş eşi Liberation Sans; ikisi de OFL, depodan okunur:
çıktı makinedeki yazı tiplerine bağlı değil). M² brüt oturumdur (dış duvar dış yüzleri, veranda ve sundurma dahil; listedeki `bina_m2` ile
aynı; sınır kutusu değil). Müşteri projeleri (KT) adsız: kod ve m². Koda bağlı seçimler (vasistas eşiği 60 cm, çatı tipi adları, özellik
yazı boyu 7,3→5,2 pt küçülme) `kurallar/cizim/pafta_sablonu.json` anahtarlarında (üçü Lokman'ın 12 Ekim 14:53 kabulüyle `lokman`;
`zincir_en_kisa_parca_cm` 15 cm 12 Ekim akşam kararıyla `lokman`: "Çelikte 15 cm parça çıkmaz", katılan parçalar `pafta_ozet.json ›
kontrol_notlari`'na mühendis notu olarak yazılır (D-10); `taslak_ibaresi` 1. sayfa TASLAK; `genel_olcu_yuvarlama` şablon kuralının
kaydı). Mahal adı tanımda `etiket_yeri` varsa oraya basılır (KT-01 "Salon - Mutfak" kapı simgesine biniyordu, rehber 12 Ekim); arkada
kalan baca önündeki çatı düzleminin altına çizilir (KT-01'de baca eğimin üstünde, çizim setiyle aynı). `pafta_ozet.json` ayrıca
`mahal_etiket_cm` taşır. Doğrulama
geçmeyen işte teslim adıyla PDF yazılmaz (`.HATALI.pdf`, K23). Genel motorun kendi `pafta.png`'si (mühendis paftası, açıklama satırlarıyla)
çizim setinde kalır, baytları değişmedi. Bayiye giden üçüncü çıktı `<kod>_bayi_gorsel.png`: plan + çatı planı + ön-sağ ve arka-sağ
perspektif tek görselde (`motor/genel/bayi_gorseli.bayi_gorsel`; VTK yoksa ön ve sağ görünüş; Lokman 12 Ekim akşam).

## Denemedeki karşılığı

`deneme/2026-10-06_kalinlik_160_100/sablon_pafta.py`, İş Emri'nden bu düzende PDF ve PNG üretir (pano birimli Motor'un deneme kopyası; tarih kaydı).

- Yazı tipi: Comic Sans MS lisanslı olduğu için eşi Comic Relief (SIL OFL; Türkçe harfleri tam) kullanıldı. Arial yerine Liberation Sans. Lokman aslını isterse yazı tipi dosyası gerekir.
- Çizime girmeyen bilgiler İş Emri'nin `pafta` bloğundan gelir: proje adı, ilgili kişi, sevk adresi, tarih, çizen, kontrol, onay, özellik satırları, özel istekler, mahal adı karşılıkları. Tefriş `tefris` listesinden gelir ve şematiktir.
- Dar mahalde (banyo) ad odaya sığmazsa yazı küçülür; yeri `pafta.etiket_yeri_cm` ile verilebilir.
- Ön ve sağ zincirde ölçü yazısı duvarla çizgi arasına düştüğü için zincir 8 pt dışarı alındı; şablonda bu yazılar pencere etiketine değiyor.

## Kararlar (Lokman, 12 Ekim 2026 14:53; önce açık sorulardı)

- Antetin sol kutusu **şimdilik boş**; ileride her bayiye kendi logosuyla antet gider (sonraki iş).
- Çizen, Kontrol, Onay satırlarının **üçünde de "Portman"** ("Portman her yerde geçsin").
- Dört görünüş ve çatı planı **aynı PDF'in 2. sayfasında** kalır.
- Panel Türü ve Çatı Kaplaması **modelden**; Çatı Kaplama Rengi, boya renkleri, Köşe ve Söveler bayi söylediyse onunki, söylemediyse "..."; uydurulmaz (K21).
- "İLGİLİ KİŞİ-TELEFON": **bayinin adı ve bayi kartındaki kayıtlı telefonu** yazılır; numara belgeyle dolaşır (D-09; başka kimsenin numarası yazılmaz, LLM'e gitmez, günlükte maskeli). Uygulama PR-2'de; katalog ve altın üretimde "...".
- "Pano pano" kuralı çelikte **uygulanmaz** (8a): kural kitabında ve bu klasörde çelik duvar panelini plana/görünüşe bölen bir kural yok (yalnız listenin panel adedi tahmini: en uzun panel 569 cm); Lokman'a bildirildi.
- Ölçüler **dış yüzden** (mühendis planı ve görünüşlerle aynı), parçaların toplamı genel ölçüye eşit; 15 cm ve daha kısa parçalar bayi paftasında komşusuna katılır (`kurallar/cizim/pafta_sablonu.json`, `lokman`). Bina özellikleri değeri sığmazsa küçülür, en küçük boyda da sığmazsa iki satıra sarılır (satır sonunda virgül; iki satır satır yüksekliğine sığacak en büyük boyda), iki satıra da sığmazsa en küçük boyda üç satır; kesilmez.

## Kararlar (Lokman, 12 Ekim 2026 akşam; D-10)

- **13 Ekim 2026 (göz denetimi; D-10 ek 9):** yazı kutuları birbirine binmez (mürekkep kutusu; `testler/genel/test_yazi_cakismasi.py`): Bina Özellikleri'nde sarılan satırların aralığı mürekkep ölçüsüyle; `en_az` 5,2 pt'de sığmayan değer `ozellik_yazi_pt_mutlak` (4,0 pt, varsayım) sınırına kadar küçülür (KT-02 Pencereler ≈ 4,4 pt; bilgi kesilmez); dar zincir parçasının sayısı içeri (plana doğru) sıraya; 2. sayfada görünüş ölçü şeritleri ölçeğe göre, çatı planı yazıları çakışmasız. "..." hücreleri, antetteki "95"/"ÇELİK" ve ÖZEL İSTEKLER satırları yalnız yerleşim kutusuyla örtüşür: yanlış alarm.
- **Soru 25: evet.** 8b mühendis kabulüne kadar 1. sayfada da, antetin üstünde küçük "TASLAK · üretim projesi değildir" (`taslak_ibaresi`; 8b'de `sayfa1: false`).
- **"Çelikte 15 cm parça çıkmaz."** (20:01) `zincir_en_kisa_parca_cm` 15, durum `lokman`. Rehberin denetimi (yedi model, ≤ 15 cm zincir parçaları): Ç8801 yok; Ç8201 8 cm ve 15+15 cm; KT-02 3 ve 11 cm; KT-03 1,1 / 1,9 / 3 / 11 / 14 cm — gerçek parça değil: dış yüz–aks farkı, kaplama ya da tanımda 1–2 cm kayma (KT-03). Karar (rehberin önerisi): parça paftada komşusuna katılır **ve** mühendise "bu ölçüyü kontrol et" notu düşer: `pafta_ozet.json › kontrol_notlari` `[{zincir, konum_cm, parca_cm, not}]`, 8b'de mühendise gösterilir.
- **KT-01 göz denetimi:** "SALON - MUTFAK" yazısı kapı simgesine biniyordu → mahal adı tanımdaki `etiket_yeri`'ne basılır (mühendis planı gibi). Sol yan görünüş gözden geçirildi: KT-01'de çizim setindeki SOL GÖRÜNÜŞ ile tutarlı (baca batı eğiminin üstünde, düzlemin önünde; yan görünüşte eğimin üstünde beyaz kutu olarak okunur); arkada kalan baca için çizim sırası derinliğe bağlandı (bugünkü modellerde çıktı değişmez).
