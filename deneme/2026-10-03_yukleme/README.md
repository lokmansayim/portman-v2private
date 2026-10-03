# 3 Ekim 2026 · çelik yükleme listesi denemesi

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) B3 adımı için.

Amaç: bir modelin metrajından yükleme listesinin kalemlerini kuralla çıkarmak; kuralları gerçek listelerle karşılaştırmak. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir.

Yöntem, kaynaklar ve bulgular: `docs/sartname/yukleme_listesi_yontemi.md`.

| Dosya | İçerik |
|---|---|
| `kurallar.json` | Katsayılar: zayiat, levha ve parça ölçüleri, bindirme, iniş kuralı, çelik birim ağırlıkları, tavan ve çatı paneli, köşebent, oda başına elektrik kuralı, çatı kaplaması seçenekleri, vida, boya, tesisat. Her birinin kaynağı ve durumu yanında |
| `yukleme.py` | Hesap: metraj girdisinden on bir grubun kalemleri; `--karsilastir` gerçek listeyle karşılaştırır; `--kaplama` çatı kaplaması seçeneğini değiştirir (altı seçenek); `--bayi` bayi kuralını uygular |
| `girdi_uret.py` | Yapı Tanımı taslağından (`../2026-10-02_celik/`) metraj girdisi üretir: oda çevreleri ve iç köşeler, OSB takviyesi duvarları, odaların işlevi; seçenek dosyası alır |
| `bayi_kurallari_ornek.json` | Bayi kuralı örneği: listeye giren gruplar, bayinin çatı yöntemi. Gerçek numara ya da ad içermez |
| `tablo_uret.py` | Şartname belgesindeki tabloları hesap çıktılarından üretir (`sonuc/tablolar.md`) |
| `belge_uret.py` | Şartname belgesini (`docs/sartname/yukleme_listesi_yontemi.md`) tablolardan ve hesap çıktılarından üretir |
| `hepsini_kos.sh` | Bütün hesapları sırayla koşar |
| `sayfa_uret.py` | Ç8201 taslağını okunur tek bir sayfaya çevirir (Lokman'a giden özel artefakt: https://claude.ai/artifact/XkfYhAKG1hb79bY5VEjNV9); çıktı depoya yazılmaz |
| `ornek_90m2_*.json`, `ornek_62m2_*.json`, `ornek_105m2_*.json` | Üç gerçek listenin girdileri ve kalemleri. Kişi, bayi ve firma adı içermez |
| `sonuc/` | Karşılaştırma sonuçları; Ç8201 taslakları (baz, dış 140 mm, altı çatı kaplaması, yöntem B); tablolar |

## Çalıştırma

```
bash hepsini_kos.sh ~/.cache/portman-venv/bin/python

python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
python girdi_uret.py ../2026-10-02_celik/C8201.json
python yukleme.py sonuc/C8201_girdi.json --md sonuc/C8201_yukleme_taslak.md
python yukleme.py sonuc/C8201_girdi.json --kaplama osb_kiremit
python yukleme.py sonuc/C8201_girdi.json --bayi ORNEK-BAYI-2
python belge_uret.py --zaman "3 Ekim 2026 19:12"
```

## Kuralların kaynağı (öncelik sırasıyla)

1. Lokman'ın söyledikleri (3 Ekim 13:27 cevapları ve öncekiler): durum `lokman`.
2. İnşaat mühendisi Ubeydullah'ın 3 Ekim cevapları (Lokman 18:14'te iletti): `muhendis`.
3. Gerçek yükleme listelerinin çalışma kitaplarındaki formüller: `excel`.
4. Excel hesaplama motoru (CTKBF V1.1): çelik birim ağırlıkları, vida, boya ve tesisat formülleri: `motor`.
5. Gerçek listelere uydurulan kurallar (`uydurma`) ve varsayımlar (`varsayim`); teyit bekler.

## Sonuç (3 Ekim 2026 19:12)

- Mühendisin yedi cevabı işlendi: tavan ve çatı paneli (100 m² değerinden, alana oranla), köşebent formülü, OSB takviyesinin yalnız dolap ve TV duvarlarına verilmesi, oda başına elektrik kuralı, saçak yüzü Boardex ve saçak omegasının kalkması, altı çatı kaplaması, inişin plana göre elle verilebilmesi.
- Üç gerçek listeyle karşılaştırma (adet): 90 m² 29 kalemin 15'i, 62 m² 41 kalemin 30'u, 105 m² 49 kalemin 31'i aynı; toplam 119 karşılaştırmanın 76'sı. Adedi doğrudan listeden alınan satırlar sayılmadı. 43 farkın 10'u tek bir farktan: iniş sayısı kuralı iki listede 6 veriyor, listelerde 7. Köşebent yeni formülle de tutmuyor (57 / 70, 39 / 50, 70 / 85): örneklerin planı yok, oda başına 4 iç köşe sayıldı.
- Çelik kg, motorun birim ağırlıklarıyla: iki listede toplam +%0,5 ve +%3,7; duvarlar %5–13 eksik, çatı %10–30 fazla.
- Ç8201 taslağı: on bir grup, 88 satır. Çelik 2716 kg (tavan ve çatı paneli dahil); dış 140 seçeneğinde 2511 kg (et kalınlığı 0,8 mm varsayımıyla; 1,2 mm ile 2989 kg). Köşebent 51, OSB takviyesi 9 levha, elektrik sayıları kuraldan.
- Çatı yöntemi A (çatı ve tavan paneli) baz; yöntem B (tavan omegası, aşık, saçak sacı) bayi kuralıyla seçilebiliyor. Üç gerçek liste de yöntem B'de: yöntem A'nın karşılaştırılacak gerçek listesi yok.
- Bağımsız sağlama: yeni satırlar (oda çevreleri ve iç köşeler, köşebent, OSB takviyesi, elektrik, tavan ve çatı paneli, altı kaplama, iki vida satırı) kodu ve çıktıları görmeyen ayrı bir Claude oturumunda tanım ve kurallardan yeniden hesaplandı; hepsi aynı çıktı.

## Sınırlar

- `uydurma` durumundaki katsayılar 90 ve 62 m² listelere bakılarak seçildi; o listelerle tutması kanıt değildir. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi ve onun çatı planı yok. Hiçbiri kör sınama değil.
- Örnek girdilerde çatı uzunlukları ve tavan alanları listelerde yazan değerlerdir; 105 m² örnekte iniş sayısı ve elektrik sayımı da öyle.
- Ç8201'in kendi gerçek listesi yok; taslak yalnız kurallardan çıkıyor.
- Yöntem A'nın tavan ve çatı panelinin kg'ı ve adedi, 100 m² bina için verilen değerin alana oranı: tahmin. Duvar paneli adedi ve çelik et kalınlığı da tahmin.
- Elektrik sayıları pafta sayımı değil, oda başına kural (doğruluk payı yaklaşık %75). Tek bir gerçek listeyle sınandı: kural 41, sayım 48 parça.
- OSB takviyesinin duvarları ve odaların işlevi modelin tanımına elle yazılır; Ç8201'de katalog görselinden.
- Çatı kaplamasında altı seçenek var; trapez sac ve shingle seçenekleri gerçek listeyle karşılaştırılmadı. Kırma çatıda kaplama adedi yüzeyin %10 fazlası (62 m² listeye uyduruldu); şerit yerleşimi sağlaması daha fazlasını veriyor. Dekoratif sıva, betopan, yalıpan yok.
- Excel motorunda olup okunan listelerde olmayan kalemler (çatı müdahale kapağı, mahya bandı) hesapta yok.
- Çift kat, döşeme, merdiven yok.
- Gerçek listelerin çalışma kitapları ve Excel motoru depoda değil; Lokman'ın Mac'inde.
