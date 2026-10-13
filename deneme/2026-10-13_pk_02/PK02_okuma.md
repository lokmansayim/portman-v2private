# PK-02 · Mehmet Balaban 58 m² (Loftev) · montaj paftası okuması (kör test adım 1–3)

13 Ekim 2026. Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/…/Mehmet Balaban 58 m²` montaj seti, `kaynak/` altında 7 PDF
(montaj ve elektrik, aşık, çatı kaplaması, makas ve dere, tavan omega, müşteri onay; `PK02_111.pdf` daha eski bir plan, kullanılmadı).
Çizen Büşra Nur Gürgün, satış temsilcisi Lokman Sayım. Gerçek yükleme listesi **açılmadı** (mühür `9081e5e1…961f28`,
`deneme/2026-10-13_kor_test_seri/MUHUR.md`).

## Okuma (vektörden; `pafta_oku.py` → `pafta_montaj.json`)

- **Dış ölçü 773 × 739,25.** Paftadaki "745" yazısı panolarla uyuşmuyor: ön/arka sıra 6 × 125,5; yan duvarlar köşe 5 + 62,75 + 3 × 125,5 + 39 + 2 × 125,5 + köşe 5.
  745, müşteri onay paftasındaki eski sürümün (68,5'lik parçalar) toplamı; montajda parçalar 62,75'e inmiş ama ölçü yazısı, mutfak ve salon alanı
  (11,62 / 16,32 = 745 ile) ve çatı planı (805 = 745 + 60) güncellenmemiş. Panolar esas alındı. Gerçek listede yan duvarın ön parçası 625 mi 680 mi, bu ayrımı gösterecek.
- **Odalar** (arka-sol çerçeve, y arkadan): banyo 10–261 × 5–295, yatak 261–763 × 5–295, hol 10–386,5 × 295–420,5, mutfak 10–386,5 × 420,5–734,25,
  salon 386,5–763 × 295–734,25. Ek akslar y 295 ve 420,5. Motor alanları: banyo 6,99 (7), yatak 14,07 (14,07), hol 4,46 (4,46), mutfak 11,42 (11,62*), salon 16,11 (16,32*); * pafta 745 ile.
- **Pencereler:** 60/40 banyo arka 1. pano; 120/180 mutfak ve salon ön; 120/120 yatak ve salon sağ. Uçlarda camgöbeği karkas işaretleri.
- **Kapılar** (kanat yayları): dış kapı 100 (sol duvar, hol panosunda ortalı, menteşe arka uçta), salon kapısı 100, banyo / yatak / mutfak 80'lik kanat.
- **Çatı:** beşik, makaslar derinliği geçer (açıklık 805 saçakla), 7 makas (ön ve arka duvarın pano eklerinde), yükselme 143, eğik 424 → eğim %35,5.
  Aşık 16 sıra (yüz başına 8) × (410 + 410 + 13); sandviç panel 430 × 100, 17 adet (bir panel iki yüze paylaşılmış).
- **Tavan:** asma tavan, omegalar 125 cm'de bir (paftanın notu); 13 oda içi hat + 5 duvar üstü parça, toplam 55,55 m.
- **Elektrik planı** var (göz sayımı, `pafta_katmani.json`): tavan armatürü 4, banyo glopu 1, dış aplik 7, anahtar 5 + çift 1, priz 14 + çift 1, uydu 1, zil 1, sigorta kutusu 1.
- **Özellikler:** Press Panel, sandviç panel 4 cm antrasit, dış kapı çelik, iç kapılar Amerikan panel, boya Sandeco (alıcıya ait değil), asma tavan, metal dere ve iniş.

## Motor ↔ pafta (`pafta_kiyas.py` → `pafta_kiyas.json`; liste açılmadan)

43 Motor panosunun 36'sı paftayla aynı yerde aynı boyda; 4 köşenin 4'ü tutuyor. Farklar iki kuraldan:

1. **Sağ duvar arka koşusu (yatak penceresi):** pafta 82,25 + 125,5 (pencere) + 82,25; Motor 39 + 42,25 + 125,5 + 83,25. D-13 pencereyi odaya
   ortalarken eski ızgara ekini (483,25) bırakıyor ve odanın net içini (447,25–729,25) ortalıyor; pafta pencere panosunu koşunun ortasına koyup iki eşit
   uç parça bırakıyor (bir özel boy az). **Kural adayı:** ortalanan pencere panosunun iki yanında koşu bölünmez, iki eşit parça kalır.
2. **x 261 iç duvarı (banyo | yatak):** pafta arka duvarın iç yüzünden 2 tam pano + T ucunda 31; Motor arka aksından ızgara ile 120,5 + 125,5 + 36.
   PK-01'de (Huma, ızgara) kesik pano dış duvar ucundaydı; bu çizimde (Loftev, koşu) iç yüzden tam pano başlıyor. **Karar adayı (Lokman):** koşu hizasında
   iç duvar dış duvarın iç yüzünden başlasın mı?

Kapı mantığı (D-13) iki kapıda paftadan ayrıldı; İş Emri'nde paftaya sabitlendi (`pano`, `mentese`), bulgu olarak duruyor:
banyo kapısı (kural 1. pano, pafta 2. pano: yatak kapısıyla 261 duvarında buluşuyor), mutfak kapısı (kural 1. pano, pafta 3. pano: hol–salon kapısının
yanında), dış kapı menteşesi (kural ön uç, pafta arka uç). Ortak nokta: paftada iç kapılar holün dış kapıdan uzak ucunda toplanıyor.
Oda kapısı yaslama paftada 13–15 cm, Motor 11,5.

Bilinen sınır: Motor'un 2B çatı profili ve ön görünüşü makasın x'i geçtiğini varsayıyor (makas_ekseni y yalnız IFC'de); bu projede ön cephe saçak tarafı.

## Liste (adım 3)

`deneme/2026-10-13_kor_test_seri/yukleme_listesi.py` sürüm 2 (PK-01 dersleri 1–10 + liste açılmadan paftadan P1–P3): `sonuc/PK02_liste.json` / `.xlsx`.
Sütunlar: **adet** (varsayılan), **pafta** (bu projenin paftası), **aday** (karar bekleyen: fabrika şablonu formülü ve PK-01 hipotezleri).
Sürüm 2'nin PK-01'e geri uygulanışı (kalibrasyon, kör değil): paneller 50 / 50, H kulaklı / dübelli hipotezi 12 / 7 ve 2 / 3, betopan 4, makas 2 + 7.
