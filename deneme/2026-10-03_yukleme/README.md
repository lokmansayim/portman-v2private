# 3 Ekim 2026 · çelik yükleme listesi denemesi

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) B3 adımı için.

Amaç: bir modelin metrajından yükleme listesinin kalemlerini kuralla çıkarmak; kuralları gerçek listelerle karşılaştırmak. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir.

Yöntem, kaynaklar ve bulgular: `docs/sartname/yukleme_listesi_yontemi.md`.

| Dosya | İçerik |
|---|---|
| `kurallar.json` | Katsayılar: zayiat, levha ve parça ölçüleri, bindirme, iniş kuralı, çelik birim ağırlıkları, vida, boya, tesisat. Her birinin kaynağı ve durumu yanında |
| `yukleme.py` | Hesap: metraj girdisinden on bir grubun kalemleri; `--karsilastir` gerçek listeyle karşılaştırır; `--kaplama` çatı kaplaması seçeneğini değiştirir; `--bayi` bayi kuralını uygular |
| `girdi_uret.py` | Yapı Tanımı taslağından (`../2026-10-02_celik/`) metraj girdisi üretir; seçenek dosyası alır |
| `bayi_kurallari_ornek.json` | Bayi kuralı örneği: listeye giren gruplar, bayinin çatı yöntemi. Gerçek numara ya da ad içermez |
| `tablo_uret.py` | Şartname belgesindeki tabloları hesap çıktılarından üretir (`sonuc/tablolar.md`) |
| `hepsini_kos.sh` | Bütün hesapları sırayla koşar |
| `ornek_90m2_*.json`, `ornek_62m2_*.json`, `ornek_105m2_*.json` | Üç gerçek listenin girdileri ve kalemleri. Kişi, bayi ve firma adı içermez |
| `sonuc/` | Karşılaştırma sonuçları; Ç8201 taslakları (baz, dış 140 mm, üç çatı kaplaması); tablolar |

## Çalıştırma

```
bash hepsini_kos.sh ~/.cache/portman-venv/bin/python

python yukleme.py ornek_62m2_girdi.json --karsilastir ornek_62m2_gercek_liste.json
python girdi_uret.py ../2026-10-02_celik/C8201.json
python yukleme.py sonuc/C8201_girdi.json --md sonuc/C8201_yukleme_taslak.md
python yukleme.py sonuc/C8201_girdi.json --kaplama osb_kiremit
python yukleme.py sonuc/C8201_girdi.json --bayi ORNEK-BAYI-2
```

## Kuralların kaynağı (öncelik sırasıyla)

1. Lokman'ın söyledikleri (3 Ekim 13:27 cevapları ve öncekiler): durum `lokman`.
2. Gerçek yükleme listelerinin çalışma kitaplarındaki formüller: `excel`.
3. Excel hesaplama motoru (CTKBF V1.1): çelik birim ağırlıkları, vida, boya ve tesisat formülleri: `motor`.
4. Gerçek listelere uydurulan kurallar (`uydurma`) ve varsayımlar (`varsayim`); teyit bekler.

## Sonuç (3 Ekim 2026, 15:10)

- Üç gerçek listeyle karşılaştırma (adet): 90 m² 29 kalemin 15'i, 62 m² 41 kalemin 30'u, 105 m² 49 kalemin 31'i aynı; toplam 119 karşılaştırmanın 76'sı. Adedi doğrudan listeden alınan satırlar sayılmadı. 43 farkın 10'u tek bir farktan: iniş sayısı kuralı iki listede 6 veriyor, listelerde 7.
- Çelik kg, motorun birim ağırlıklarıyla: iki listede toplam +%0,5 ve +%3,7; duvarlar %5–13 eksik, çatı %10–30 fazla.
- Ç8201 taslağı: on bir grup. Çelik 1902 kg (tavan ve çatı paneli hariç); dış 140 seçeneğinde 1697 kg (et kalınlığı varsayımı yüzünden daha hafif).
- Çatı yöntemi A (çatı ve tavan paneli) baz; yöntem B (tavan omegası, aşık, saçak sacı) bayi kuralıyla seçilebiliyor. Üç gerçek liste de yöntem B'de: yöntem A'nın karşılaştırılacak gerçek listesi yok.

## Sınırlar

- `uydurma` durumundaki katsayılar 90 ve 62 m² listelere bakılarak seçildi; o listelerle tutması kanıt değildir. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi ve onun çatı planı yok. Hiçbiri kör sınama değil.
- Örnek girdilerde çatı uzunlukları ve tavan alanları listelerde yazan değerlerdir; 105 m² örnekte iniş sayısı ve elektrik sayımı da öyle.
- Ç8201'in kendi gerçek listesi yok; taslak yalnız kurallardan çıkıyor.
- Yöntem A'nın tavan ve çatı panelinin adedi ve kg'ı hesaplanmıyor (ölçüsü bilinmiyor). Duvar paneli adedi ve çelik et kalınlığı tahmin.
- Elektrik sayımı yok: duy, glop, anahtar, priz, sigorta, buat ve kablo hesaplanmıyor.
- Çatı kaplamasında üç seçenek var: sandviç panel, tek kat panel, OSB + nem bariyeri + kiremit desen sac. Shingle, trapez, dekoratif sıva, betopan, yalıpan yok.
- Çift kat, döşeme, merdiven yok.
- Gerçek listelerin çalışma kitapları ve Excel motoru depoda değil; Lokman'ın Mac'inde.
