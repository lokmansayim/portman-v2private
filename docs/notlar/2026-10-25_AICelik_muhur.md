# AICelik mührü (İE-16 PR-1)

Tarih: 25 Ekim 2026, 09:15–09:40 UTC. Dayanak: D-25 (çelik hattı, pano satır 106) ve Lokman'ın 25 Ekim 09:10 kartı ("Evet, 4 açık + kalanı kör": hedef örnek 90 m², dört proje daha açık, kalanı kör). Kişi, firma ve bayi adı yazılmaz; projeler ÇP kodlarıyla (Drive `AICelik` klasöründeki proje klasörlerinin adlarına göre düz sıra: ÇP-01 ilk klasör; adlı eşleme depoya ve paylaşılan klasöre girmez). Kayıt: `testler/celik/muhur.json`.

## Sonuç

- **21 proje, 118 dosya** (mühendisin 21–22 Ekim yüklemesi): montaj paftası PDF'i (bir projede ayrı pafta sayfaları), DWG, yükleme listesi (Excel ve PDF), çatı kaplama listesi ya da detayı, özel büküm ve profil detayları, bir projede SketchUp modeli ve sundurma listesi.
- **Kör listeler açılmadı ve indirilmedi.** Her kaydın Drive kimliği, baytı ve Drive'daki değiştirme saati mühürde. SHA-256 17 dosyada dolu: 15 montaj paftası ve hedef örneğin iki yükleme listesi (Excel ve PDF). Drive aracı yaklaşık 5 MB'ı geçen dosyayı vermediği için beş projenin paftası (ÇP-02, ÇP-04, ÇP-08, ÇP-09, ÇP-11) ve bütün DWG'lerin SHA'sı ilk indirmede alınır (18 Ekim AIPrefabrik mührünün "İlk kullanımda" kararı gibi): okunmadan önce `ilk_indirmeler`'e ayrı commit'le yazılır; bayt ya da Drive saati mühürdekinden farklıysa dosya kullanılmaz ve Patron'a yazılır.
- **Durumlar:** hedef örnek ÇP-06 ve açık dört proje (ÇP-03, ÇP-07, ÇP-13, ÇP-14); kör 10 proje (ÇP-02, 04, 08, 09, 11, 12, 17, 18, 19, 20; beşinin kat sayısı belirsiz); kapalı 6 çift katlı proje (ÇP-01, 05, 10, 15, 16, 21; D-26: dubleksler canlıdan sonra). Dosyada: açık 15, kör 24, kapalı 14 liste kaydı; 65 kaynak (pafta, DWG, detay, model).
- **Mühürden sonra yalnız ekleme:** birleştikten sonra mühüre yalnız üç bölümde, her biri ayrı commit'le ekleme yapılır: `ilk_indirmeler` (SHA'sı bekleyen dosya), `acilislar` (Patron kararıyla açılan kör ya da kapalı liste), `kat_kayitlari` (kat sayısı belirsiz projenin paftadan okunan katı). Öteki bölümlerin izi testte (`test_muhurun_dondurulmus_bolumleri_degismez`); değişirse hakem değişikliğidir.
- **Planla fark:** planda "kalan yaklaşık 15 kör" yazıyordu. Çift katlılar D-26 gereği pilot dışında kaldığı için kör kümesi 10 projedir; çift katlıların listeleri kapalı kalır, sonraki çift kat işinde kör olarak kullanılabilir.

## Kat ayrımı (listeye bakılmadan, paftadan)

Montaj paftası PDF'inin metninde "1. KAT DUVAR PANELLERİ" ya da "1.KAT TAVAN OMEGA" sayfası olan proje çift katlıdır (ÇP-01, 05, 10, 15, 21). Paftası ayrı sayfalar halinde gelen ÇP-16'nın sayfa adlarında birinci kat duvar ölçüleri, döşeme kirişi ve merdiven planı var: çift. İndirilen paftasında bu sayfa olmayan proje tektir. Paftası indirilemeyen beşinin kat sayısı belirsizdir: ilk kullanımda paftadan belirlenir ve `kat_kayitlari`'na ayrı commit'le yazılır; araç kat kaydı olmayan belirsiz projenin listesini açmaz, çift çıkanın listesini kapalı sayar ve açmaz (D-26). Aramada yalnız kat ve merdiven sözcükleri sayıldı; kör projelerin panel etiketleri (D, K, M, C) okunmadı. ÇP-05 iki evli bir projedir; pafta ve liste 1 numaralı evindir.

## Açık dört projenin seçimi

Kural mühür kurulurken yazıldı ve yalnız mühürdeki alanları kullanır (`muhur.json › secim_kurali`; test aynı kuralı yeniden kurar): hedef örnek dışındaki tek katlı projeler m² bantlarına ayrılır (A ≤ 70, B 71–89, C 100–130, D ≥ 131; 90–99 hedefin bandıdır); her banttan yükleme listesinin Drive saati en yeni olan alınır. Bantta uygun proje yoksa 90–99 bandından en yeni listesi olan alınır.

| Bant | Uygun (tek katlı) | Seçilen |
|---|---|---|
| A ≤ 70 | ÇP-03 | ÇP-03 (69 m², liste 18 Eylül) |
| B 71–89 | ÇP-07 | ÇP-07 (80 m², liste 23 Eylül) |
| C 100–130 | ÇP-14 | ÇP-14 (120 m², liste 3 Nisan) |
| D ≥ 131 | yok (dördü çift, ÇP-11 belirsiz) | 90–99'dan ÇP-13 (99 m², liste 28 Eylül) |

Planda "m² ve çatı tipi farklı" yazıyordu; çatı tipi ancak her projenin makas sayfası okunarak bilinir, bu yüzden kural yalnız m² kullanır. Açık projelerin çatı tipleri PR-2 ve PR-3'te yazılır.

## Projeler

| Kod | m² | Bant | Kat | Liste tarihi (Drive) | Durum | Liste kaydı | Kaynak | SHA dolu |
|---|---|---|---|---|---|---|---|---|
| ÇP-01 | 160 | ≥ 131 | çift | 2026-08-14 | kapalı (çift kat) | 2 | 3 | 1 |
| ÇP-02 | 123 | 100–130 | belirsiz | 2026-01-16 | kör | 2 | 2 | 0 |
| ÇP-03 | 69 | ≤ 70 | tek | 2026-09-18 | açık | 2 | 3 | 1 |
| ÇP-04 | 55 | ≤ 70 | belirsiz | 2026-05-20 | kör | 2 | 3 | 0 |
| ÇP-05 | 197 | ≥ 131 | çift | 2026-09-23 | kapalı (çift kat) | 2 | 3 | 1 |
| ÇP-06 | 90 | 90–99 | tek | 2026-09-17 | hedef örnek (açık) | 6 | 3 | 3 |
| ÇP-07 | 80 | 71–89 | tek | 2026-09-23 | açık | 3 | 3 | 1 |
| ÇP-08 | 81 | 71–89 | belirsiz | 2026-02-23 | kör | 2 | 2 | 0 |
| ÇP-09 | 82 | 71–89 | belirsiz | 2026-03-18 | kör | 2 | 2 | 0 |
| ÇP-10 | 123 | 100–130 | çift | 2026-09-14 | kapalı (çift kat) | 3 | 3 | 1 |
| ÇP-11 | 150 | ≥ 131 | belirsiz | 2026-08-25 | kör | 3 | 2 | 0 |
| ÇP-12 | 99,7 | 90–99 | tek | 2026-08-02 | kör | 3 | 2 | 1 |
| ÇP-13 | 99 | 90–99 | tek | 2026-09-28 | açık | 2 | 3 | 1 |
| ÇP-14 | 120 | 100–130 | tek | 2026-04-03 | açık | 2 | 3 | 1 |
| ÇP-15 | 125 | 100–130 | çift | 2026-03-17 | kapalı (çift kat) | 2 | 2 | 1 |
| ÇP-16 | 160 | ≥ 131 | çift | 2026-01-14 | kapalı (çift kat) | 2 | 13 | 0 |
| ÇP-17 | 90 | 90–99 | tek | 2026-08-07 | kör | 3 | 2 | 1 |
| ÇP-18 | 90 | 90–99 | tek | 2026-04-11 | kör | 2 | 3 | 1 |
| ÇP-19 | 90 | 90–99 | tek | 2026-04-19 | kör | 2 | 3 | 1 |
| ÇP-20 | 92 | 90–99 | tek | 2026-05-21 | kör | 3 | 3 | 1 |
| ÇP-21 | 138 | ≥ 131 | çift | 2026-06-05 | kapalı (çift kat) | 3 | 2 | 1 |

## Ne okundu

- **Hedef örnek ÇP-06:** yükleme listesi Excel'i 25 Ekim sabahı, hedef örnek önerisi için, Lokman'ın 09:10 kartından ve bu mühürden önce açıldı (`muhur.json › acilislar`); listenin PDF'i ve montaj paftası aynı gün hakemin okuyucularını kurmak için okundu. Kör sayılmaz.
- **Açık dört proje:** listeleri henüz indirilmedi; PR-3'te ilk indirme kaydıyla açılır.
- **Kör ve kapalı projeler:** paftalarında yalnız kat sözcükleri arandı (yukarıda); liste, panel etiketi ve ölçü okunmadı.

## Bilinen sınırlar

- Drive aracı dosya özeti (md5) vermiyor; indirilmemiş kayıtların kimliği bayt ve Drive saatidir, SHA-256 ilk indirmede. Mühendis bir dosyayı yerinde değiştirirse Drive saati değişir ve araç dosyayı kullanmaz.
- Aynı m² ve aynı markadan birden çok proje var (90–99 bandında yedi). Bir kör proje açık bir projeyle aynı planı taşıyorsa (dış ölçüler ve oda dizilimi aynı) kör ölçümde (PR-4) "açık kardeşi var" diye ayrı satırda yazılır.
- Kör projelerde panel etiketleri cevap tarafıdır: Yapı Tanımı yazılırken paftanın yalnız plan ölçüleri okunur, panel sayfaları hakemin kıyasında okunur (İE-16 › Kör ölçüm).
