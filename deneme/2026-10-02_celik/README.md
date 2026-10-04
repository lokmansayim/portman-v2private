# 2 Ekim 2026 · çelik deneme çizicisi (Ç8201)

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) ilk denemesi.

Amaç: tek kat çelik bir modeli, pano ızgarası olmadan, bir tanım dosyasından ve duvar tiplerinden kurmak; alanları ve Boardex metrajını hesaplamak; planı çizmek.

| Dosya | İçerik |
|---|---|
| `duvar_tipleri.json` | Baz paket duvar tipleri (katman listesi). Duvar kalınlığı katmanların toplamıdır |
| `C8201.json` | Ç8201'in tanımı: dış kutu, iç duvar aksları, mahaller ve işlevleri, açıklıklar (arşivdeki çizimden); veranda çerçevesi, çatı yöntemi ve kaplaması; OSB takviyesi gelen duvarlar |
| `ciz.py` | Hesap ve plan çizimi |
| `gorunus.py` | Çatı hesabı, çatı planı, dört görünüş ve tek pafta |
| `secenekler/` | Seçenekler (değişiklik operatörleri): model tanımını değiştirmeden paket farkını uygular. İlk örnek: `dis_karkas_140.json` |
| `cikti/` | Koşu çıktıları (depoya girmez) |
| `sonuc/` | Son koşunun kanıtları (4 Ekim 2026 13:22): plan, pafta, raporlar; `C8201_plan_cizim_kalinligi.png` arşiv çiziminin duvar kalınlıklarıyla (12 / 11 cm) çizilen karşılaştırma planı |

## Çalıştırma

```
python ciz.py C8201.json                    # baz paketin katmanlarıyla (10,5 cm duvar)
python ciz.py C8201.json --cizim-kalinligi  # arşiv çiziminin kalınlıklarıyla (12 / 11 cm); etiketlerle karşılaştırır
python gorunus.py C8201.json                # çatı + görünüşler + pafta
python ciz.py C8201.json --secenek secenekler/dis_karkas_140.json      # dış duvar karkası 140 mm
python gorunus.py C8201.json --secenek secenekler/dis_karkas_140.json
```

## Sonuç (2–3 Ekim 2026)

- `--cizim-kalinligi`: beş mahalin alanı çizimdeki etiketlerle aynı (11,8 · 11,8 · 4,3 · 6,7 · 23,3). Çıkış kodu 0.
- Katmanlardan: 11,9 · 11,9 · 4,3 · 6,7 · 23,5; kapalı net 58,4 m². Dış ölçü 850 × 750 (veranda dahil 1094 × 750).
- Dış Boardex (yalnız duvarlar): 32,0 m × 2,70 m − 19,6 m² = 66,8 m²; fire hariç 24 levha. Yükleme listesi hesabı `../2026-10-03_yukleme/`'de.
- Çatı (kırma, %33, saçak 30): plan 1154 × 810, mahya 344 cm, yüzey 98,4 m². Makas üstü: saçak ucunda 280, mahyada 414 cm. 8 cm çatı paneliyle çatı üst yüzü: saçak ucunda 288,4, mahyada 422 cm.
- Saçak yüzü (saçak kaplaması; önceki kayıtlarda "alın") 18,4 cm = topuk 10 + panelin eğimdeki düşey ölçüsü 8,4; kaplaması 39,28 m × 18,4 cm = 7,2 m².
- Mahya malzemesi tepeye ve dört kırmaya konur: 344 + 4 × 588 = 2697 cm; 2,8 m'lik parça ve 30 cm bindirmeyle 11 adet.
- Düzeltmeler: 21:50 topuk saçak ucunda (SKP ölçümü; önceki mahya kotu 404'tü); 22:05 çatı paneli ve saçak kaplaması (Lokman); 3 Ekim 11:57 kırmalarda mahya (Lokman).
- Pencere üst kotu 200 cm (lento 70).
- Dış 140 mm seçeneği (3 Ekim 11:49): dış duvar 16,5 cm, iç 10,5 cm; dış ölçü aynı; kapalı net 58,4 → 56,5 m²; Boardex ve çatı aynı. Karşılaştırma tablosu: `docs/sartname/modeller/C8201.md`.

## 3 Ekim 13:27 cevaplarıyla değişenler

- İç kapı boşluğu 90 × 214, kanat 200 (eni 80 listelerden); banyo kapısı da 90 (çizimde 80'di). Dış kapı 210 yüksekliğinde çizildi (modeller ve listeler; boşluk 95 × 210 mühendisin 4 Ekim 12:14 cevabıyla teyit edildi).
- Veranda çerçevesi: sırt 8, genişlik 30 cm; kirişler üç açık kenarda (12,38 m); dikme 3 adet, 240 cm. Planda ve görünüşlerde çizildi. Önceki 20 × 20 kolon varsayımı kalktı.
- Çatı: yöntem A (çatı ve tavan paneli); saçak altı Boardex; kaplama seçenek.
- Dere inişi 6 adet; çatı planında sarı noktalar.
- Alanlar değişmedi; `--cizim-kalinligi` karşılaştırması yine AYNI.

## 3 Ekim 18:14 (mühendisin cevapları) ile değişenler

- Tanıma her mahalin işlevi yazıldı (`islev`; Yaşam Alanı salon + mutfak, veranda ayrı): yükleme listesindeki elektrik kuralının girdisi.
- Tanıma OSB takviyesi gelen duvarlar yazıldı (`osb_takviye.duvarlar`; katalog görselinden): banyo ile mutfak arası duvar, üst dış duvar, hol ile yaşam alanı arası duvar. Planda turuncu çizgi; boşluklarda kesilir. Net 24,5 m².
- Rapor her mahalin iç çevresini, iç ve dış köşe sayısını da veriyor (köşebent hesabının girdisi): çevreler toplamı 69,725 m, iç köşe 21, dış köşe 1.
- İç duvarların L birleşimi dolduruldu (banyonun alt duvarı ile banyo–mutfak duvarının köşesi): Yaşam Alanı'nda 5 × 5 cm'lik çentik kalktı; alanlar iki ondalıkta aynı, `--cizim-kalinligi` karşılaştırması yine AYNI.
- Çatı: saçak yüzü Boardex (teyitli), saçak omegası yok. Dere inişi tanımda elle verilebilir (`cati.inis_noktalari`); verilmediği için kuraldan 6.
- Çatı kaplaması adları altı seçeneğe çıkarıldı.

## 4 Ekim 01:24 ve 01:42 ile değişenler

- Baz paketin çatı kaplaması tek kat panel (Lokman, 01:42): tanımda `cati.kaplama`; paftadaki yazı ve çatı raporu buna göre. Plan görseli bayt bayt aynı.
- Tanıma OSB takviyesi duvarlarının teyidi yazıldı (mühendis doğruladı).
- Dış 140 seçeneğinin açıklaması: et kalınlığı mühendisin kuralıyla 1,2 mm (çizim değişmedi).
- Çatı açılımı ve kaplama dizilimi yükleme listesi denemesinde: `../2026-10-03_yukleme/cati_acilim.py`.

## 4 Ekim 12:14 (mühendisin üçüncü cevapları) ile değişenler

- Dış kapı boşluğu 95 × 210 ("Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır."): tanımda genişlik 100 → 95 cm, başlangıç 383 → 385,5 (kapının ekseni yerinde). Plan ve paftalar yeniden çizildi (dört görsel).
- Alanlar ve dış Boardex metrajı değişmedi (metraj zaten 0,95 × 2,10 boşlukla hesaplanıyordu); `--cizim-kalinligi` karşılaştırması yine AYNI. Karşılaştırma planı `sonuc/C8201_plan_cizim_kalinligi.png` olarak eklendi.
- OSB takviyesi: duvarın tamamı alınır (teyit); tanımdaki kaynak notuna yazıldı.
- Yükleme listesindeki değişiklikler (taşma, köşebent, Boardex zayiatı, mahya bandı): `../2026-10-03_yukleme/`.

## Sınırlar

- Yalnız dikdörtgen kapalı kutu ve eksenlere paralel iç duvarlar.
- Yalnız kırma çatı; 3B ve yükleme listesinin öteki kalemleri yok.
- Varsayım: veranda dikmelerinin sayısı ve yeri (katalog görsellerinden); panelin ucu şakülünde kesilir (gönyesinde kesilirse saçak yüzü 17,6 cm). Topuk 10 cm modellerden ölçüldü, Lokman teyit etti. Subasman, merdiven ve cephe kaplaması çizilmiyor.
- Kaynak çizim (DWG) depoda değil; tanım dosyası elle, çizimden okunarak yazıldı.
