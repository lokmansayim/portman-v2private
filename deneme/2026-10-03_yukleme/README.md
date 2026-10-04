# 3 Ekim 2026 · çelik yükleme listesi denemesi

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) B3 adımı için.

Amaç: bir modelin metrajından yükleme listesinin kalemlerini kuralla çıkarmak; kuralları gerçek listelerle karşılaştırmak. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir.

Yöntem, kaynaklar ve bulgular: `docs/sartname/yukleme_listesi_yontemi.md`.

| Dosya | İçerik |
|---|---|
| `kurallar.json` | Katsayılar: zayiat, levha ölçüleri ve kalınlıkları, parça ölçüleri, bindirme, iniş kuralı, çelik birim ağırlıkları ve et kalınlığı kuralı, tavan ve çatı paneli, köşebent, oda başına elektrik kuralı, çatı kaplaması seçenekleri ve baz kaplama, kırma çatıda dizilim kuralı (taşma, kesim payı, başlangıç sırası), mahya bandı, vida, boya, tesisat. Her birinin kaynağı ve durumu yanında |
| `yukleme.py` | Hesap: metraj girdisinden on bir grubun kalemleri; `--karsilastir` gerçek listeyle karşılaştırır; `--kaplama` çatı kaplaması seçeneğini değiştirir (altı seçenek); `--bayi` bayi kuralını uygular |
| `cati_acilim.py` | Kırma çatının açılımı ve kaplama dizilimi (Lokman, 4 Ekim 01:42): dört yüz gerçek boyutuyla açılır, şeritlere bölünür; çapraz kesimden artan parça karşı yüzde kullanılır. Kaplama saçaktan 5 cm taşar (mühendis, 4 Ekim 12:14); altı başlangıç denenir, en az paneli veren alınır; kesim payı kurallardan. Kaplama adedini verir; açılım ve kesim planı çizimlerini üretir |
| `cati_acilim_saglama.py` | Dizilimin geometrik sağlaması (çokgenlerle): parçalar yüzü tam örtüyor mu, panele sığıyor mu, üst üste biniyor mu, yüzdeki yerine oturuyor mu; rastgele kırma çatılarda da dener |
| `motor_formul.py` | Excel motorundaki (CTKBF V1.1) kaplama adedi formülü: yazıldığı gibi ve payda parantezi düzeltilince. Liste bu formülü kullanmaz; belge ve sayfa örnekleri buradan yazar |
| `girdi_uret.py` | Yapı Tanımı taslağından (`../2026-10-02_celik/`) metraj girdisi üretir: oda çevreleri ve iç köşeler, veranda tavanının çevresi, OSB takviyesi duvarları, odaların işlevi; panel boyu (eğimli boy + taşma); seçenek dosyası alır |
| `bayi_kurallari_ornek.json` | Bayi kuralı örneği: listeye giren gruplar, bayinin çatı yöntemi. Gerçek numara ya da ad içermez |
| `tablo_uret.py` | Şartname belgesindeki tabloları hesap çıktılarından üretir (`sonuc/tablolar.md`) |
| `belge_uret.py` | Şartname belgesini (`docs/sartname/yukleme_listesi_yontemi.md`) tablolardan ve hesap çıktılarından üretir |
| `hepsini_kos.sh` | Bütün hesapları sırayla koşar |
| `sayfa_uret.py` | Ç8201 taslağını okunur tek bir sayfaya çevirir (Lokman'a giden artefakt: https://claude.ai/artifact/XkfYhAKG1hb79bY5VEjNV9); plan ve çatı açılımı görsellerini içine gömer; sayfa bağlantıyla paylaşılabildiği için kişi adı yazmaz; çıktı depoya yazılmaz |
| `ornek_90m2_*.json`, `ornek_62m2_*.json`, `ornek_105m2_*.json` | Üç gerçek listenin girdileri ve kalemleri. Kişi, bayi ve firma adı içermez |
| `sonuc/` | Karşılaştırma sonuçları; Ç8201 taslakları (baz, dış 140 mm, altı çatı kaplaması, yöntem B); çatı açılımı (çizim, kesim planı, döküm); tablolar |

## Çalıştırma

```
bash hepsini_kos.sh ~/.cache/portman-venv/bin/python

python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
python girdi_uret.py ../2026-10-02_celik/C8201.json
python yukleme.py sonuc/C8201_girdi.json --md sonuc/C8201_yukleme_taslak.md
python yukleme.py sonuc/C8201_girdi.json --kaplama osb_kiremit
python yukleme.py sonuc/C8201_girdi.json --bayi ORNEK-BAYI-2
python cati_acilim.py sonuc/C8201_girdi.json --acilim-png sonuc/C8201_cati_acilim.png --kesim-png sonuc/C8201_cati_kesim.png
python motor_formul.py
python belge_uret.py --zaman "4 Ekim 2026 13:22"
```

## Kuralların kaynağı (öncelik sırasıyla)

1. Lokman'ın söyledikleri (3 Ekim 13:27 cevapları, 4 Ekim 01:24 ve 01:42 düzeltmeleri ve öncekiler): durum `lokman`.
2. İnşaat mühendisi Ubeydullah'ın üç tur cevabı (Lokman 3 Ekim 18:14'te, 4 Ekim 01:24'te ve 4 Ekim 12:14'te iletti): `muhendis`. İkinci turun iki cevabını (baz kaplama, kırma çatıda kaplama adedi) Lokman düzeltti.
3. Gerçek yükleme listelerinin çalışma kitaplarındaki formüller: `excel`.
4. Excel hesaplama motoru (CTKBF V1.1): çelik birim ağırlıkları, vida, boya ve tesisat formülleri: `motor`.
5. Gerçek listelere uydurulan kurallar (`uydurma`) ve varsayımlar (`varsayim`); teyit bekler.

## Sonuç (4 Ekim 2026 13:22)

- Mühendisin üçüncü cevapları (4 Ekim 12:14) işlendi: kaplama saçaktan 5 cm taşar (panel boyu L 4300 → L 4315); köşebentte veranda tavanının çevresi sayılır (51 → 59); Boardex zayiatı %8 (dış cephe 33 → 31); mahya bandı mahya adedinden (3 → 4 rulo); dış kapı boşluğu 95 × 210; Boardex 12,5 mm, OSB 11 mm; kiremit desen sacda artan parça kullanılmaz. Teyit edilenler: tek katta 1,2 mm; tavan ve çatı paneli adetleri; OSB takviyesinde duvarın tamamı; buat için veranda hariç odalar ve tekli prizler; makas ve kirişte şimdilik Excel motoru.
- Excel motorundaki kaplama formülü yeniden okundu (mühendisin isteği; `motor_formul.py`): 0,8 ve 1,05 paydanın parantezi dışında, yani formül kapatma genişliğine bölmek yerine çarpıyor; uzun kenara saçak eklenmemiş; tek kat panel 100 cm, metal kiremit 105 cm yazıyor (listelerde 87 ve 110). Hücreler ve örnekler şartname belgesinde.
- Lokman'ın 4 Ekim düzeltmeleri işlendi: 100 m² için tavan paneli 354,84 kg ve çatı paneli 440,32 kg (alana oranla); baz kaplama tek kat panel; kırma çatıda kaplama adedi çatı açılımından (`cati_acilim.py`).
- Mühendisin ikinci cevapları işlendi: et kalınlığı kuralı (tek katta ve zemin katta 1,2 mm; üst katta 0,8 mm, 200 cm ve daha geniş pencereli duvarda 1,2 mm); OSB takviyesi duvarlarının ve salon + mutfak kuralının teyidi; mahya bandı listede; çatı müdahale kapağı yalnız müşteri isterse.
- Mühendisin ilk cevapları (3 Ekim): köşebent formülü, OSB takviyesinin yalnız dolap ve TV duvarlarına verilmesi, oda başına elektrik kuralı, saçak yüzü Boardex ve saçak omegasının kalkması, altı çatı kaplaması, inişin plana göre elle verilebilmesi.
- Üç gerçek listeyle karşılaştırma (adet): 90 m² 29 kalemin 15'i, 62 m² 41 kalemin 28'i, 105 m² 49 kalemin 31'i aynı; toplam 119 karşılaştırmanın 74'ü (Boardex zayiatı %8 olmadan önce 75'ti: dış cephe Boardex üç listede de 2–3 levha az çıkıyor). Adedi doğrudan listeden alınan satırlar sayılmadı. 45 farkın 10'u tek bir farktan: iniş sayısı kuralı iki listede 6 veriyor, listelerde 7. Köşebent yeni formülle de tutmuyor (57 / 70, 39 / 50, 70 / 85): örneklerin planı yok, oda başına 4 iç köşe sayıldı. 62 m² listede sandviç panel 27 (ayrıca 2 kısa panel); çatı açılımı taşmayla 28 veriyor (taşmasız 26'ydı; önceki kural 27'yi tutturuyordu ama o listeye uydurulmuştu).
- Çelik kg, motorun birim ağırlıklarıyla: iki listede toplam +%0,5 ve +%3,7; duvarlar %5–13 eksik, çatı %10–30 fazla.
- Ç8201 taslağı: on bir grup, 89 satır. Çelik 2555 kg (tavan ve çatı paneli dahil); dış 140 seçeneğinde 2828 kg (duvarlar kuralla 1,2 mm). Tek kat panel 28 adet L 4315 (10 tam boy + 18 kesilen; dizilim uzun yüzlerde sol köşeden, kısa yüzlerde ortadan; her yüzde sol köşeden başlanırsa 29); mahya bandı 4 rulo; köşebent 59; dış cephe Boardex 31; OSB takviyesi 9 levha; elektrik sayıları kuraldan.
- Çatı yöntemi A (çatı ve tavan paneli) baz; yöntem B (tavan omegası, aşık, saçak sacı) bayi kuralıyla seçilebiliyor. Üç gerçek liste de yöntem B'de: yöntem A'nın karşılaştırılacak gerçek listesi yok.
- Bağımsız sağlama (3 Ekim): oda çevreleri ve iç köşeler, köşebent, OSB takviyesi, elektrik, tavan ve çatı paneli, iki vida satırı kodu ve çıktıları görmeyen ayrı bir Claude oturumunda tanım ve kurallardan yeniden hesaplandı; hepsi aynı çıktı.
- Bağımsız sağlama (4 Ekim): çatı açılımı, kodu görmeyen ayrı bir Claude oturumunda kuraldan yeniden hesaplandı. Ç8201'in dört kaplaması ve 62 m² örneği aynı adetleri verdi (28, 24, 30, 24 ve artan parça kullanılmadan 26; 62 m²'de 26). Adetlerin bu dizilim için en az olduğu gösterildi; parçaların panele sığdığı ve yüzdeki yerine oturduğu çokgenlerle sınandı. Taşma ve kesim payı eklendikten sonra yeniden: beş örnek × altı başlangıç × üç kesim payı (0, 5 mm, 1 cm) = 90 adedin hepsi aynı çıktı (Ç8201: tek kat panel 28, sandviç panel 26, trapez sac 32, kiremit desen sac 26; 62 m²'de 28).

## Sınırlar

- `uydurma` durumundaki katsayılar 90 ve 62 m² listelere bakılarak seçildi; o listelerle tutması kanıt değildir. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi ve onun çatı planı yok. Hiçbiri kör sınama değil.
- Örnek girdilerde çatı uzunlukları ve tavan alanları listelerde yazan değerlerdir; 105 m² örnekte iniş sayısı ve elektrik sayımı da öyle.
- Ç8201'in kendi gerçek listesi yok; taslak yalnız kurallardan çıkıyor.
- Yöntem A'nın tavan ve çatı panelinin kg'ı, Lokman'ın 100 m² için verdiği ağırlığın alana oranı (oranlamayı Lokman onayladı); adedi mühendisin 100 m² adedinden aynı oranla: tahmin. Duvar paneli adedi de tahmin.
- Et kalınlığı mühendisin kuralıyla; 2025 tarihli iki tek katlı 140'lık gerçek liste kurala uymuyor (0,8 mm ağırlıklı). Örnek karşılaştırmaları o listelerdeki kalınlıklarla yapılıyor.
- Elektrik sayıları pafta sayımı değil, oda başına kural (doğruluk payı yaklaşık %75). Tek bir gerçek listeyle sınandı: kural 41, sayım 48 parça.
- OSB takviyesinin duvarları ve odaların işlevi modelin tanımına elle yazılır; Ç8201'de katalog görselinden.
- Çatı kaplamasında altı seçenek var; trapez sac ve shingle seçenekleri gerçek listeyle karşılaştırılmadı. Dekoratif sıva, betopan, yalıpan yok.
- Çatı açılımı yalnız dikdörtgen planlı, dört yanı eşit eğimli kırma çatı için; cumbalı çatıda (ters mahya) yok. Varsayımlar (üçü de soruldu, cevaplanmadı): altı başlangıçtan en az paneli veren alınır (tek kat panelde her yüzde sol köşeden başlanırsa 1 panel fazla); kesim payı 5 mm (2,8 mm ve altında sandviç panel 25, trapez sac 30 olur); yedek panel yok. Boy bindirmesi yok; panel tek boyda. Kiremit desen sacda artan parça kullanılmaz (mühendis, 4 Ekim 12:14).
- Excel motorunda olup okunan listelerde olmayan kalemler: mahya bandı listeye eklendi; çatı müdahale kapağı yalnız müşteri isterse (`--mudahale-kapagi`); ters mahya kenar kutuları ve damlalık hesapta yok (damlalık mahya bandı formülünde sıfır alınıyor).
- Boardex zayiatı %8 (mühendis): 2025 tarihli üç gerçek listedeki adetler %15'e uyuyor; %8 ile 2–3 levha az çıkıyor.
- Köşebentte veranda tavanının çevresi brüt ölçüyle alındı; verandada köşe boyu eklenmedi (okuma).
- Çift kat, döşeme, merdiven yok.
- Gerçek listelerin çalışma kitapları ve Excel motoru depoda değil; Lokman'ın Mac'inde.
