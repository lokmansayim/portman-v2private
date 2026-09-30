# Codex devri · kabul raporu (30.09.2026)

**Konu:** Codex'in (Bilge) Lokman'la yaptığı üç model kaynak incelemesi (P9201, P9401, P9501) ve P9401 çatı seçenekleri (A–D). Paket Lokman'ın Mac'inde: `~/Documents/Codex/2026-09-30/merhaba-bilge-ben-lokman-ekledi-im/outputs/Claude_Devir_2026-09-30/` (247 dosya, 421 MB).

**Dal:** `ie-04-codex-devir`, `ie-04`'ten (`2ba4f18`) açıldı. `main`'e ve `ie-04`'e dokunulmadı.

**Sınırlar:** İE-02 açılmadı. Motor, çıkarıcı, 23.09 IFC/Blender kodu ve canlı paket değişmedi. Harcama (LLM, WhatsApp) yapılmadı, sunucuya bağlanılmadı. Depoya büyük veri alınmadı. Mac'te hiçbir dosya değişmedi ve silinmedi.

## 1. Alınanlar

| Ne | Nerede | Durum |
|---|---|---|
| Paketin tamamı | Mac (devir klasörü) | 247/247 dosya manifestteki SHA256 ile aynı (`devri_kontrol_et.py`, bu oturumda Mac'teki Linux kabuğunda koşuldu; Blender/SDK yolları o kabukta görünmediği için "yok" çıkması paketin sorunu değil) |
| 89 dosya: SKP'den türetilmiş JSON'lar, IFC'ler, `.blend`'ler, küçük belgeler | Oturumun çalışma alanı (doğrulama için) | 89/89 manifestle aynı. Videolar, fotoğraflar, özgün SKP/DWG aktarılmadı |
| 41 küçük dosya: devir belgeleri, manifest, kod arşivi | Depo: `deneme/2026-09-30_codex_devir/` | 41/41 manifestle aynı, değiştirilmeden |
| Kaynak kimlikleri | Depo: `kaynak_inceleme/veri/kaynaklar.json` | SKP, JPG, DWG, JSON, IFC, `.blend` SHA256'ları ve revizyon kimlikleri |
| Paketteki depo okuma kopyaları (DURUM, katalog, K02, K04, K16, KARARLAR/README) | — | 6/6 `main` (`e8014e7`) blob'larıyla aynı. Codex `main`'deki DURUM'u okumuş; İE-04'ün güncel DURUM'u `ie-04`'tedir |

Büyük veri (JSON ~95 MB, IFC ~60 MB, `.blend` ~75 MB) depoda değil. Depoya ya da sunucuya alınması yeni veri paylaşımıdır; onay bekler.

## 2. Bu oturumda yeniden doğrulananlar

Codex'in kayıtlı sonuçları (ör. `DEVIR_KONTROLU.json`: "passed") burada yeniden koşulmuş gibi aktarılmadı. Aşağıdakiler bu oturumun kendi koşularıdır. Kanıt: `deneme/2026-09-30_codex_devir/dogrulama/`.

| Kontrol | Sonuç | Nasıl |
|---|---|---|
| Seçimin yeniden kurulması | 3/3 aynı (190, 82, 339 düğüm; ağlar, malzeme adı ve rengi) | `secim.sec`: kalıcı kimlik kaydından sahneden seçim, `selected.json` ile karşılaştırma |
| IFC'nin yeniden üretilmesi | 7/7 aynı (3 model + 4 çatı), tarih damgaları dışında satır satır | `ifc_yaz` (Blender'sız) + `karsilastir` |
| Kayıtlı IFC'lerin bağlayıcı denetimi | 7/7 geçti: şema sorunu 0, nesne kaybı/fazlası/çifti 0, koordinat farkı 0,0 m, topoloji aynı, özellikler doğru, geometri motoru hatasız | `ifc_dogrula` |
| Çatı verisinin yeniden üretilmesi | A–D verisi, `secenekler.js`, `Tasarim_Kaydi.json` bayt bayt aynı | Codex'in `create_variants.py`'si olduğu gibi, Linux/Python 3.11'de |
| Gövde korunumu (A–D) | 4/4: 81 gövde düğümü veri düzeyinde ve IFC'de referans P9401 IFC'siyle birebir | `cati.govde_korunumu`, `_govde_ifc` |
| Kayıtlı `.blend` dosyaları | 7/7 geçti: seçim ve çatı koleksiyonu doğru, dönüşüm köşelere uygulanmış (shear düzeltmesi korunmuş), köşe farkı en çok 2,5 µm (Blender float32 saklar), öneri parçaları eşleşiyor | `blender_dogrula`, bpy 5.2.2 |
| Denetimin hata yakalaması | IFC'de koordinat, nesne, topoloji ve SHA özelliği bozmaları; Blender'da köşe, seçim ve matris bozmaları: hepsi KALDI | Testler (`testler/kaynak_inceleme`, 17 test) ve elle bozma denemesi |
| Gerileme | Bkz. §8 | `bash araclar/ortam_kur.sh --dogrula` |

Önemli teknik bulgu: Codex'in IFC koordinatları Blender'ın 32 bit matris hesabıyla yazılmış. Bu hesap numpy ile birebir taklit edildi (P9401'de 82/82 düğüm bayt bayt). IFC tarafı artık Mac'e ve Blender'a bağlı değil.

## 3. Eşleme tablosu

Sınıflar: **alındı** · **yeniden üretilebilir** (bu oturumda Mac'siz yeniden üretildi) · **uyarlama gerekli** · **kaynak kararı gerekli**.

| Model / revizyon | Kaynak SHA256 | Sınıf | Açık fark | Lokman kabulü | Teknik kontrol | Entegrasyon |
|---|---|---|---|---|---|---|
| P9201 · SKP-inceleme-01 | SKP `31fc08e9…` · JPG `00721a42…` | alındı · yeniden üretilebilir (seçim, IFC) · kaynak kararı gerekli | F01 hol/yaşam sınırı (1,5/6,60 m²); F02 veranda JPG 15,7 / DXF 16,5 / r01 18,9; F03 dış ölçü 1140×836 / 1139,5×835,75; F04 açıklık kaymaları; F05 kapı 80/100 → 82/90 (K04); F06–F08 (`belgeler/durum/P9201_Ilk_Is_Emri.md`). İE-04 raporuyla uyumlu | Bekliyor | Aktarım bütünlüğü geçti. Kaynak ve üretim kabulü yok | `kaynak_inceleme`'ye bağlandı (yerel aday). Motor'a bağlanmadı |
| P9401 · SKP-inceleme-01 | SKP `57ea5920…` · JPG `d30ff88e…` | alındı · yeniden üretilebilir · kaynak kararı gerekli | SKP'de iki yapı kopyası (soldaki seçildi; sağdaki 52 kök grup dışarıda, kural kayıtlı); veranda derinliği, çatı eğimi ve saçak (§5) | Bekliyor | geçti; kaynak/üretim kabulü yok | bağlandı (yerel aday) |
| P9501 · SKP-inceleme-01 | SKP `395085dc…` · JPG `3f0495dd…` | alındı · yeniden üretilebilir · kaynak kararı gerekli | r01'de 9 → 5 pencere, 7 → 3 kapı; cumba; SKP çatı ve veranda biçimi katalogdan farklı; ayrı çamaşır mahalli yalnız DXF'te. İE-04'te geçersiz aday | Bekliyor | geçti; kaynak/üretim kabulü yok | bağlandı (yerel aday) |
| P9401-CATI-A-01 · kaynak çatı | `57ea5920…` | alındı · yeniden üretilebilir | Kaynak beşik + veranda beşik kolu; katalog uyumu açık | Bekliyor | Gövde korunumu geçti | bağlandı (inceleme) |
| P9401-CATI-B-01 · sade kırma | `57ea5920…` | alındı · yeniden üretilebilir · seçilirse uyarlama gerekli | Öneri: eğim %30,7, veranda örtüsü yatay taslak. Taşıyıcı ve drenaj tasarımı yok | **Seçilmedi** | Gövde korunumu geçti; teknik tasarım yok | bağlandı (inceleme); ürün kuralı değil |
| P9401-CATI-C-01 · tek eğim | `57ea5920…` | aynı | Öneri: 1,00 m yükselme, eğim %10,7, 6 yeni üst kapama | **Seçilmedi** | aynı | aynı |
| P9401-CATI-D-01 · parapetli | `57ea5920…` | aynı | Öneri: 0,45 m parapet; iç eğim, drenaj ve katman çözümü yok | **Seçilmedi** | aynı | aynı |
| Blender sunumları, PNG, HTML görüntüleyiciler | — | alındı (Mac) · uyarlama gerekli | `.blend` dosyaları denetlendi. Yeniden üretimleri (render, sahne kurma) Blender 5.2 ve Mac yollarına bağlı | Görsel kabul bekliyor | `.blend` 7/7 geçti | Bağlanmadı. Görüntüleyici kaynak incelemesidir; Motor kaydı değildir |
| SKP okuma (`read_skp.py`) | — | uyarlama gerekli | SketchUp SDK (macOS) gerekiyor. Kaydedilmiş `scene.json` esas alındı | — | — | Bağlanmadı |

Tam SHA256'lar `kaynak_inceleme/veri/kaynaklar.json`'dadır.

## 4. Depodaki karşılıklar ve bağlanan aday

| Codex betiği | Depodaki karşılık | Yapılan |
|---|---|---|
| `export_ifc.py` + `export_variants.py` (metni değiştirip exec eden sarmalayıcı) | Yok. Üretim IFC'si İş Emri'nden gelir (`deneme/2026-09-23/13_Kiyas/kod/ifc_uret.py`) | `kaynak_inceleme/ifc_yaz.py`: tek, açık parametreli yazıcı. Üretim IFC'sine dokunulmadı |
| `verify_saved.py`, `verify_ifc.py` | Yok | `kaynak_inceleme/ifc_dogrula.py`: bağlayıcı kapılar, çıkış 1 |
| `prepare_viewer_data.py` seçim listeleri | Yok | `kaynak_inceleme/secim.py` + `veri/secim_<kod>.json`: kalıcı kimlik ve SHA koruması |
| `render_variants.py` gövde kontrolü, `verify_world.py`, `check_saved_blend.py` | `deneme/2026-09-23/11_Blender` (İş Emri'nden pano modeli; başka iş) | `kaynak_inceleme/cati.py`, `blender_dogrula.py` |
| `devri_kontrol_et.py` | — | `kaynak_inceleme/dogrula_devir.py`: hash kontrolüyle yetinmez, yeniden üretir |
| `create_variants.py` | — | Arşivde. `dogrula_devir` olduğu gibi koşup karşılaştırıyor |
| `read_skp.py`, `make_blend.py`, `correct_blend_transforms.py`, `finalize_blend.py`, `render_variants.py` (render), `.cjs` testleri, `contact.py` | — | Arşivde. Mac'e bağlı; bağlanmadı |

İkinci bir doğruluk kaydı kurulmadı. `kaynaklar.json` yalnız köken tutar. Kabul ve durum bilgisi DURUM.md'de ve bu raporda. Adayların üretim kaydı (İE-04 göç 003, Postgres) ileride bu SHA'lara başvurur.

## 5. P9401: ilk karşılaştırma

**Kaynak model + dört çatı.** Gövdenin 81 düğümü dört seçenekte de birebir korunuyor. A, kaynak çatıyı (tek kök grup: sıra 223, kalıcı kimlik 111297) aynen taşıyor. B'de 2, C'de 8, D'de 4 öneri parçası var. Hepsi `proposal` işaretli ve hiçbiri kaynak kimliği taşımıyor. B/C/D'nin ölçüleri öneridir; genel katalog kuralı ya da üretim onayı değildir.

**SKP kaynağı ↔ Motor İş Emri** (İE-04, 30.09 `kos.py` çıktısı). Değerler bu oturumda SKP geometrisinden ölçüldü. Bu karşılaştırma bilgi içindir, hüküm değildir:

| Ölçü | SKP kaynak | İş Emri / Motor | Not |
|---|---|---|---|
| Dış duvar kutusu | 10,24 × 8,885 m | 8 × 7 pano = 1024 × 888,5 cm | Aynı |
| Duvar yüksekliği | 2,50 m (döşeme üstü 0,6017 → duvar üstü 3,1017) | 250 cm | Aynı |
| Veranda girintisi derinliği | 1,8825 m: sağ bölümün ön duvarı y = 2,50, sol bölümünkü y = 0,6175 | 1 pano = 1,255 m (veranda 7,9 m²) | Fark 0,6275 m. İE-04 raporundaki "çizilmeyen 62 cm" ile aynı büyüklükte. K-A2/K-A3 için somut veri |
| Çatı | Beşik; mahya z = 4,640, y = 5,06; eğim %30,65; saçak taşması 25 cm | Beşik, %33, saçak 30 cm (kural) | Kaynak kuraldan farklı; kural değiştirilmedi |

Hangi kaynağın esas olduğu (JPG, katalog DXF'i, SKP) K-A2 kararıdır. Kaynakta olmayan bir ölçü eklenmedi.

## 6. Yeniden üretim engelleri

| Engel (KOD_HARITASI) | Durum |
|---|---|
| Eski `make_blend.py` / shear | **Açık, etkisiz.** Kaydedilmiş, düzeltilmiş `source.blend` esas. `blender_dogrula` matris kapısı dönüşüm nesneye geri dönerse kalır (bozma denemesinde kaldı). SKP'den sıfırdan Blender zinciri Mac'e bağlı |
| Yerel shader adı | `render_variants.py` `node.type` kullanıyor. `make_blend.py`'de açık (kullanılmıyor) |
| Sabit yollar | IFC, denetim ve seçim tarafında **çözüldü** (parametre). Blender üretim betiklerinde açık |
| Sıra numaralı seçimler | **Çözüldü**: kalıcı kimlik ve SHA koruması. Kalan: IFC GUID tohumunda hâlâ düğüm sıra numarası var (aynı SHA ve okuyucuyla kararlı). Değiştirmek mevcut GUID'leri değiştirir; karar |
| IFC metin-replace sarmalayıcısı | **Çözüldü** (`ifc_yaz`) |
| Başarısızlıkta durmayan raporlayıcılar | **Çözüldü**: `ifc_dogrula`, `blender_dogrula`, `dogrula_devir` kalınca çıkış 1 |

Ek bulgular:
- Öneri parçalarında IFC `Tag` ve `SKP_Nesne` alanına "None" yazılıyor (kaynak kimliği yok). Yeniden üretim birebir olsun diye aynen korundu. Düzeltmesi tek satır; onaydan sonra.
- Codex'in P9201 iş emrindeki açık soru kapandı: r01 manifestindeki `reference_dxf_sha256` (`22cc9304…`) depodaki `kanal/ref_source-6x8.dxf`'tir (Motor'un 6×8 referansı), katalog DXF'i (`709dfe94…`) değil.
- Eski r01 çıktıları Motor v1.1'in `geometry.py`, `katalog.py` ve `validate.py`'siyle (depodakiyle aynı) ama farklı bir `dxf_out.py` ile üretilmiş. Bu yüzden tarihsel sayılır; güncel karşılaştırma İE-04'ün 30.09 koşusudur.
- Ortak DWG (`f4a55a73…`) açılmadı. Depodaki katalog DXF'iyle ilişkisi doğrulanmadı.
- Kurallar v1.4.3 (`prefabrik-cizim-kurallari.md`, `KURALLAR.json`, Blender kuralları) depoda yok; SHA'ları `kaynaklar.json`'da. `MALZEME_KATALOGU.json` depodaki `motor/malzeme_katalogu.json` ile aynı.

## 7. Açık kararlar

| Karar | Kim | Not |
|---|---|---|
| Büyük verinin (JSON, IFC, `.blend`) depoya ya da sunucuya alınması | Lokman | Yeni veri paylaşımı. Öneri: şimdilik Mac'te kalsın; depo SHA ile bağlı |
| Adayın `ie-04`'e alınması | Lokman | `main` değil. Ayrı dalda bekliyor |
| P9401 çatı seçimi (A–D); seçilirse teknik tasarım | Lokman, Ubeydullah | B/C/D modele özgü öneri |
| Kaynak önceliği (JPG / DXF / SKP) | Lokman | K-A2. P9401 veranda derinliği somut örnek |
| K04 kapı ölçüsü, K16 | Lokman, Ubeydullah | Açık kaldı; bu devir değiştirmedi |
| GUID tohumu ve "None" etiketi | Claude önerir, Lokman onaylar | Küçük; mevcut çıktıların kimliğini etkiler |

## 8. Gerileme

Bu dalda, 30.09 07:27–07:40:
- `bash araclar/ortam_kur.sh --dogrula`: harness 22/22. Referansta DXF ve PDF parmak izleri 18/18 AYNI; beklenen "2 kontrolde fark" (sır taraması `vps/kapi_d_dogrula.sh:25`, bilinen yanlış pozitif).
- Bütün testler, yerel Postgres 16 ile: 345 geçti, 1 atlandı. Atlanan, gerçek devir verisini isteyen test; `PORTMAN_KAYNAK_VERI` ile ayrıca koşuldu ve geçti. Önceki koşu 328'di; fark yeni 17 test.
- Yeni dosyalarda sır taraması bulgusu 0.

Not: ortam turlar arasında yeniden başlatıldığı için betiğin ilk denemesinde yerel Postgres geç açıldı ve kalıcı akış testleri atlandı. Testler Postgres açıldıktan sonra yeniden koşuldu; yukarıdaki sayı o koşudur.

## 9. Sonraki somut işlem

Aday kabul edilirse: İE-04'ün kararlardan bağımsız ilk yerel işi, yani İş Emri'nden IFC üretimini Motor hattına modül olarak almak. `ifc_dogrula`'nın bağlayıcı kapı düzeni üretim IFC'sine de uygulanır. P9401'de SKP kaynağıyla Motor IFC'si yan yana konur; bu, K-A9 iskeletinin 3D ayağı olur.

İE-04 ilerlemesi (A1–A6) değişmedi. A5 hâlâ **Kısmen**: bu aday kaynak incelemesidir, seçilen adayın revizyonundan üretilen 3D değildir.
