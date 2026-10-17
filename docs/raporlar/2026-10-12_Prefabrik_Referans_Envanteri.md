# Prefabrik referans envanteri · 12 Ekim 2026 (İE-10)

Lokman'ın 12 Ekim akşamı verdiği dört dosya/klasör incelendi; prefabrik tarafında neyin nerede olduğu, depoda ne olup ne olmadığı çıkarıldı.
Sohbet: "Portman 3B sayfası ve Astra arşivi incelemesi". Mac'teki hiçbir dosya değiştirilmedi, silinmedi, taşınmadı.

## 1. 3+1 1150 × 1050 3D sayfası (`~/Downloads/Portman_PM-DENEME-3ARTI1-1150x1050_r01_3B_3.html`, 6 Ekim)

- Tek dosya, 1,07 MB, dışarıya çağrı yok: three.js 603 KB + model verisi 236 KB (104 gövde parçası, 6 çatı seti) + plan JPEG 150 KB.
- Headless Chromium'da sınandı (1500 × 950 ve 390 × 844): sayfa hatası 0, WebGL açıldı, 6 çatı kartı geçiş yaptı, çatı aç/iskelet/pano renkleri/oda adları/oluşum sürgüsü çalıştı, telefonda yatay kayma yok.
- Sayımlar tutuyor: dış pano 36 (32 tam + 4 kesilmiş), iç pano 30 (16 tam + 14 özel), pencere 8, kapı 6. Çatı rakamları elle yeniden hesaplandı: A mahya 12,10 m, örtü 141,4 m²; D üst kot 4,01 m; E döşeme 113,8 m² — tutuyor.
- Eksikler (gelişmiş sürüm için): sağ tablolar elle yazılmış HTML (veriden üretilmiyor); pencere/kapı parçaları aynı adı taşıyor (kasa + cam); brüt 121 m² ile net 110,76 m² ayrımı yazılmıyor; telefonda düğmeler modelin önüne geçiyor; seçim kaydedilmiyor; kuralsız çatılar (D, E, F) seçilebiliyor.
- Depodaki kopya `deneme/2026-10-06_kalinlik_160_100/sonuc/PM-DENEME-3ARTI1-1150x1050/ifc/…_3B.html` ile **bayt bayt aynı** (`ae61feb1…`). Plan PDF'i de aynı; yükleme listesi 4 sayfa 1681 hücre 0 fark; IFC içerik aynı (yalnız GUID ve küme sırası).
- Lokman: 160 / 100 kalınlık standart değil, müşteri örneğiydi (D-12).

## 2. Masaüstü `outputs/` klasörü (Astra dönemi, 13–20 Eylül)

- `Portman_Devir_2026-09-20/` + aynı içerikli zip: Astra'nın Claude'a devir paketi (44 KB rapor, `DEVIR_DURUMU.json`, PHP/Python kaynaklar, kural v1.4.3, kanıtlar). SHA256SUMS **99/99 doğrulandı**.
- `Portman_Gorev3/`, `Portman_OpenAI_Bulut/`, `Portman_Gorev_1_Sonuc.txt`: 13–14 Eylül görev kayıtları; devir paketinin içinde de var (üç kopya).
- Eskidi: hosting PHP akışı, OpenAI ajan/ortam kimlikleri, `house.py`'nin sabit 6×8 yeniden üretimi, Görev 3 telefon kabulü. Devir raporunun 9 açık işi İE-02…İE-08 ile aşıldı.
- **Hâlâ değerli ve 12 Ekim'e kadar depoda olmayan:** `kaynaklar/gorev2/reference/` — prefabrik kural seti v1.4.3 (8 dosya). Repoda yalnız `h-connector.json` ve `source-6x8.dxf` vardı (`kanal/ref_*`); kural belgelerinin hash'i `deneme/2026-09-23/13_Kiyas/astra_kaynak/kaynak_dogrulama.json`'da anılıyor ama dosyalar yoktu. → `ref_prefabrik/astra_v1_4_3/`.
- Klasör silinmemeli; zip + SHA256SUMS kanıt niteliğinde.

## 3. Hash karşılaştırması (paket ↔ depo, 12 Ekim 22:19)

| Paket dosyası | Depoda (12 Ekim öncesi) |
|---|---|
| `h-connector.json` 9cc05864… | `kanal/ref_h-connector.json` aynı; SHA256SUMS ve 7 `referans_girdiler.json`'da |
| `source-6x8.dxf` 22cc9304… | `kanal/ref_source-6x8.dxf` aynı; SHA256SUMS'ta; 3 `manifest.json`'da anılıyor |
| `prefabrik-cizim-kurallari.md` 5fb4e529… | dosya yok; hash yalnız `kaynak_dogrulama.json`'da |
| `KURALLAR.json` 567b0f69… | dosya yok; hash yalnız `kaynak_dogrulama.json`'da |
| `proje-kararlari.md`, `CIZIM_VE_BOM_IS_AKISI.md`, `DOSYA_DIZINI.json`, `source-archive-manifest.json` | iz yok |
| `MALZEME_KATALOGU.json` 8de0e995… (AI Çizim Dosyaları) | `ref_yan/MALZEME_KATALOGU.json` ve `motor/malzeme_katalogu.json` aynı |
| `Yan-Verandali-2plus1-Yukleme-Listesi.xlsx` | `ref_yan/` aynı |

## 4. Çift kat prefabrik 75 + 75 m² (Astra, 12 Eylül; `~/Documents/Codex/2026-09-12/me/`)

- Lokman'ın yüklediği PDF (`cift-kat-prefabrik-plan-montaj-R02.pdf`) Mac'teki `outputs/` kopyasıyla bayt bayt aynı (`b4b01d7f…`); ikinci kopya `work/portman-contacts/upload-backend/proje-gonderim-R02/` (panelden gönderim paketi).
- Hat: `build_r02.py` (Python veri modeli) → `build_r02.lsp` (AutoLISP, AutoCAD for Mac) → DWG; `native-r02.json` (DWG geri okuma) → `check_r02.py`; `make_plan_pdf.py` (ReportLab) → PDF; `make_bom.mjs` → xlsx. AutoCAD'e bağlı; Portman'a taşınmaz.
- Veri modeli `r02_data.json`: 12500 × 6000 mm, iki kat aynı plan, 59 pano, 10 bağlantı, 8 mahal, 23 malzeme; cephe zincirleri 100 + 9 × 1255 + 1005 + 100 = 12500 ve 100 + 4 × 1255 + 780 + 100 = 6000.
- Bugünkü standartla: duvar 100 / 60 (aynı); sürekli 100 × 100 × 5320 köşe profili (çift kat kuralı yazılmadı); 300 mm "çelik kiriş bölgesi" + 20 mm Betopan (kesit yok; Astra "taşıyıcı detay değil"); merdiven ve balkon yok.
- Lokman (23:10): referans model değil; referanslar gerçek uygulanmış, yükleme listeli projelerden gelecek. → `ref_prefabrik/cift_kat_R02/` girdi olarak.

## 5. Astra'nın öteki prefabrik girdileri (`~/Documents/Codex/2026-09-05/…/outputs/AI Çizim Dosyaları/`)

- Kural seti (aynı hash'ler), `BLENDER_CIZIM_KURALLARI.md` + `.json`, `ARŞİVİ OKUMA.md`, `cumbali-6x5-proje-notlari.md`, Cumbalı 6×5 BOM seti (xlsx, sayım, doğrulama, DWG). → `ref_prefabrik/`.
- Codex altındaki 14 xlsx'in 11'i Yan Verandalı listesinin kopyası; özgün olanlar Cumbalı 6×5 (7 Eylül) ve çift kat R02 (12 Eylül).

## 6. Sonuç

- Prefabrik tarafının 12 Ekim resmi: kurallar v1.4.3 Astra'nın (artık depoda), P6001 bilinen hatasıyla gerileme çapası, 3+1 1150 × 1050 müşteri varyantı `deneme/`'de, çift kat R02 girdi. Referans modeller Lokman'ın vereceği gerçek projelerden kör testle kurulacak (`docs/sartname/prefabrik_kor_test.md`).
- Kararlar: D-12 (ayrı pano motoru, 100 / 60, P6001, referanslar), D-13 (ad-soyad esnetme).
