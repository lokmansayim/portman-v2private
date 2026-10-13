# Prefabrik kör test serisi PK-01…PK-08 · özet (13 Ekim 2026)

Lokman, 13.10:
- 10:37: "tek kat prefabrikleri bul, yükleme listesi montaj paftası olanları kör teste tabi tut, beraber iyileştirelim";
- 10:41: "montaj paftası varsa kesinlikle uygulanmıştır";
- 11:45: "ikisi birden" (kalanlar pafta kipinde; Motor genişletmesi `docs/is_emirleri/IE-13.md` taslağı onay bekliyor) ve "Portatifev varsayılan".

Protokol `docs/sartname/prefabrik_kor_test.md`; mühürler ve açılışlar `MUHUR.md`; üreteç `yukleme_listesi.py` (sürüm 1 → 7.1).

## Projeler

| PK | Proje | Şablon (liste) | Geometri | Doğru toplam | Not |
|---|---|---|---|---|---|
| 01 | Huma 60 (Ubeydullah, 1.10.2026) | Portatifev | Motor (İE-11 PR-1) | 41 + 12 / 97 | panolar 50 / 50 |
| 02 | Mehmet Balaban 58 | Loftev | Motor | 42 + 2 / 95 | iki pano kuralı paftadan farklı (İE-13 madde 1–2) |
| 03 | Doğan 80 (Nimet Bey) | Loftev | pafta | 45 + 5 / 112 | 160/180 iki modüllük pano, çapraz beşik |
| 04 | İsmail Ürün | — | — | — | çelik karkas; seriden çıkarıldı (genel motor kör testine) |
| 05 | Abdullah Yavuz 60 | Loftev | pafta | ≈ 25 / 103 | L plan, tek yön çatı, elektrik planı yok |
| 06 | Sevim Güler 82 + 10 | Loftev | pafta | 45 + 4 + 9 / 100 | paralel veranda beşiği; listede makas / alçıpan / pencere yok |
| 07 | Diamond 70 (Ubeydullah, 4.08.2026) | Portatifev | pafta | 41 + 16 + 11 / 134 | iç duvar 100, fugalı cephe, cumba; H planı ve panolar birebir |
| 08 | Eren Bey 60 (Muhammed Uysal, 2025) | eski Portatif (bayi) | pafta + mimari plan | 15 + 5 + 3 / 70 | montaj DWG; tavan ve pencere varsayımı yanlış; kubbeli cumba |

"Doğru toplam" = varsayılan aynı + ayrım farklı (toplam aynı) + aday / pafta sütunu tuttu.

## Her projede tutan

- **Panolar** (pafta kipinde): boy boy.
- **Sipariş boyu:** net − 2,5 mm, 5'e aşağı; modül katları n × 1250.
- **Kapı menteşesi** (kanat geometrisi, D-13 sözleşmesi): PK-01, 02, 03, 05, 06, 07; PK-08'de dış kapı.
- **Kulaklı H** = makasa denk gelen dış ek. PK-07 paftasının lejantı bunu yazıyor.
- **Köşe direği**, saçak omegası, baş makas betopanı (H5) ve 100'lük alt çerçeve (H4).
- **Dere** ÷ 3,8 ve dere kapağı (J3, J4).
- **Elektrik göz sayımı,** plan varsa.

## Sürümlerle gelen kurallar

- **v2 (PK-01):** sipariş boyu, makas ve aşık sayımı (P1–P3).
- **v3 (PK-02):** H1–H9.
- **v4 (PK-03):** J1–J8 (n × 1250, 100'lük duvar omegası, dere ÷ 3,8, kapak / iniş, trapez mahyası, ters mahya, duvar alçıpanı, yavru makas).
- **v5 (PK-05):** L1–L5 (özel pencere panosu, tek yön saçak, tek kat panel 0,87, çelik kapı 90 × 200, 5,5 × 76).
- **v6 (PK-06):** N1–N3 (açık çatı parçası, veranda omegası tek satır, aday sütunları); kulaklı H okuyucuda.
- **v7 (PK-07):** O1–O19 (fugalı cephe ve latalar, özel köşe D, iç duvar 100'de omega ve alt çerçeve, yüz başına kaplama, mahya toplam,
  kanopi deresiz, şablon formüllerinden köşebent 7 / Z / kapama / Boardex / vidalar / dübel / karkas, tesisat takımı, boya, buat).
- **v7.1 (PK-08 okuması):** pencere sınıfları (120 genişlik standart, vasistas en ve boy ≤ 60), `dere_yok`, vitrifiye alıcıya ait.

## Sorular → Lokman'ın cevapları (13.10 14:35–14:42)

Soru kartlarıyla alındı. Kanıt: AIPrefabrik inceleme seti E1–E5 (`deneme/2026-10-13_aiprefabrik/INCELEME.md`). Kayıt: `KARAR_NOTU.md`.

| # | Soru | Cevap | Sürüm 7.2'de |
|---|---|---|---|
| 1 | PK-01'in sıfırları | Standart pakette köşebent, Z, dübel, RYSB ve vidalar her zaman var; sıfırlar boş hücre. Dörtomuz çatıda baş makas Z'si olmaz. Pencere karkası projeye bağlı. | değişiklik yok (7 zaten dolduruyor); dörtomuzda kalkan 0 |
| 2 | Loftev ↔ Portatifev | Saçak ve alın 2500 / 2800 sac durumuna göre, en güncel liste esas (2500). Alt çerçeve her zaman L 3750, 60'lık da. İniş borusu L 2000. | R1, R2 |
| 3 | Islak hacim | Yalnız banyo ve WC | `ISLAK` zaten böyle |
| 4 | Orta iniş | 4 köşe + iki saçak ortası; ek çatı parçası +2 | R3 |
| 5 | PK-06 eksik gruplar | Makas düşemez (mühendisin atlaması). Pencere ve alçıpanı müşteri istemeyebilir (alçıpan %95 standart). | kıyasta "liste hatası" |
| 6 | Fugalı H latası | Dış 100'lük duvar H'ları + 3 yedek | R5 (PK-07 30 ✓) |
| 7 | W otomat | Portatifev 8, Loftev 9 | R4 |
| 8 | PK-08 bayisi | Eski şablon, eksik doldurulmuş | kural değil |
| 9 | Kubbeli cumba | Abdulselam takımı | R6 (`kubbe: true`) |
| 10 | İE-13 | Önce test setinde kör test | sırada |
| 11 | Yeni Loftev şablonu (yeni soru) | Tek şablon Portatifev | değişiklik yok |

**Sürüm 7.2'nin PK-01…08'e geri uygulanışı** (karalama klasöründe; kör listeler yerinde, yeniden yazılmadı):

| Proje | İniş | Gerçek | Not |
|---|---|---|---|
| PK-07 | 7 → 8 | 8 | ✓; H latası 27 → 30 ✓ |
| PK-01 | 6 | 6 | değişmedi ✓ |
| PK-02 | 4 → 6 | 4 | 2025 listesi |
| PK-03 | 7 → 8 | 6 | 2025 listesi |
| PK-05 | 4 → 5 | 4 | 2025 listesi |
| PK-08 | 4 → 6 | 4 | 2025 listesi |

Ayrıca:
- **PK-08:** kubbe takımı 8 satır geldi; kubbe trapez satırı düştü. Kubbenin saçak hattı sayılmayınca saçak omegası 8 → 7 oldu (gerçek 8).
- **60'lık alt çerçeve:** her projede ÷ 3,75 oldu. Gerçek listeler ÷ 2,5 yazıyordu; Lokman'a göre 3750 doğru.
- **W otomat:** artık 8; Loftev için 9 aday sütununda.

## Sıradaki

- **Test setinde kör test** (Lokman 14:42, İE-13'ten önce). Test seti: AIPrefabrik'in kalan 23 klasörü, mühür `deneme/2026-10-13_aiprefabrik/test_seti/MUHUR.md`.
  Huma 60 ve Diamond 70 görülmüş, kör değil. Doğan 80 m2 muhtemelen PK-03.
- İE-13 (madde 1–3, PK-02 tam eşleşme) kör test sonuçlarından sonra.
- Kural adaylarının `kurallar/liste/kurallar.json`'a ayrı katman olarak taşınması (yeni kural seti sürümü, altın çıktı değişmez).
- Montajı DWG olan projeler PDF'e çevrilirse seriye eklenir (Doğan 61 / 60, Kenan Karabiber 74, Altan Bey 135, Sibel Akar 87).
- KT-03 Örnek Şablon'un prefabriğe uyarlanması (öteki sohbetin entegrasyon talimatından sonra).
