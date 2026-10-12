# 2 Ekim 2026 · SketchUp (.skp) modellerini okuma denemesi

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) bir parçası.

Amaç: Lokman'ın arşivindeki SKP modellerini, SketchUp ya da Blender eklentisi olmadan, ölçülebilir veriye çevirmek.

Neden bu yol: Lokman'ın Mac'indeki Blender 5.2.1'in "İçe Aktar" listesinde SKP yok; resmi eklenti deposunda da SKP içe aktarıcı bulunmuyor (2 Ekim 2026). Var olan eklentiler üçüncü kişilerin derlenmiş paketleri; Mac'e kurulmadı. Dosyalar bulut çalışma alanında, açık kaynak `openskp` kütüphanesiyle okundu.

## Bağımlılık

- `openskp==1.3.0` (PyPI, MIT, saf Python). Kurulmadan önce paket açılıp kodu tarandı: ağ, alt süreç, `eval/exec` çağrısı yok; yalnız verilen dosyayı okuyup verilen yola yazıyor. İncelenen tekerin SHA-256'sı: `0a50c54fec2fa6049b213c736053df6fe20e3bfc2a8379b93aa76385791a17a3`.
- Ayrı bir sanal ortama kurulur (Portman'ın ortamına değil): `numpy`, `trimesh`, `shapely`, `mapbox_earcut`, `matplotlib`.
- Çözme adımı ağ kapalıyken koşuldu (`unshare -n`).

## Dosyalar

| Dosya | İçerik |
|---|---|
| `skp_oku.py` | SKP'yi çözer; bileşen ağacını açıp bütün yüzleri ve kenarları dünya uzayında cm olarak verir |
| `kaydet.py` | Çözülen modeli ara dosyaya yazar (`ara/<ad>.pkl`) |
| `uyeler.py` | Üye tipleri katman adıyla gelen çerçevede (81 m² model) üyeleri çıkarır: panel, tip, kutu, boy |
| `cati_olc.py` | Çatı düzlemleri: eğim, saçak ucu kotu, mahya kotu |
| `yatay_kot.py`, `dikme.py` | Üye tipi olmayan çerçevelerde yatay profil kotları ve dış duvar dikme aralıkları |
| `ciz3b.py` | İzometrik, plan, ön ve yan görünüş |
| `aktar.py` | Teslim dosyaları: GLB (metre), `_model.json`, `_yuzler.json.gz`, `_gorunus.png` |
| `sonuc/` | Üç modelin ölçü özeti (`_model.json`). Kişi ve bayi adı içermez |

`kaynak/` (SKP'ler), `ara/` ve `teslim/` depoya girmez: müşteri dosyaları ve onlardan üretilen geometri. Teslim dosyaları Lokman'ın Mac'inde: `Claude Portman Çalışması/28_SKP_Aktarim/`.

## Çalıştırma

```
python kaydet.py kaynak/08_81m2.skp ara/08_81m2.pkl
python uyeler.py                      # yalnız 81 m² model
python cati_olc.py 08_81m2
python aktar.py                       # üç model için teslim dosyaları
```

## Sonuç (2 Ekim 2026)

Ölçüler ve kurallarla karşılaştırma: `docs/sartname/skp_olcumleri.md`.

- Okunan üç model (SketchUp 2024): 81 m² (imalat onay modeli), 90 m² ve 62 m² çelik karkas.
- Doğrulama: 90 m² modelde okunan ölçüler aynı projenin montaj paftasındaki ölçü yazılarıyla aynı (1357, 588, 648, 1523, 270, 30 cm). GLB dosyaları Khronos glTF doğrulayıcısından hatasız geçti.
- Denenen yedi dosyadan dördü okundu (SketchUp 2023 ve 2024). 2019 biçimindeki üç dosya okunamadı (`LegacyParseError`).
- Klasörlerdeki 75 tekil SKP'nin 48'i yeni biçimde (2023–2025), 27'si eski biçimde (2015–2019).

## Sınırlar

- Okuyucu resmi SketchUp yazılımı değil; biçim tersine mühendislikle çözülmüş. Her yeni dosyada ölçüler bir kaynağa (çizim, pafta) karşı denetlenmeli.
- Döndürülmüş bileşenler: 81 m² modelde 1246 düğümün 1029'u döndürülmüş ve bina tutarlı kuruldu (paneller köşede buluşuyor, dikme aralıkları düzenli). 90 ve 62 m² modellerde döndürülmüş bileşen yok. Ayna alınmış bileşen bu üç modelde yok; o durum denenmedi.
- `aktar.py` içindeki model listesi ve 81 m² modele özgü ayrımlar elle yazıldı; genel bir araç değil.
- GLB'ler Blender'da açılıp bakılmadı (arka planda Blender'a klavye kısayolu gönderilemedi).
