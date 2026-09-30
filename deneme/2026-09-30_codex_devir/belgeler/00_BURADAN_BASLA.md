# Claude için Portman çalışma devri

**30.09.2026 · Aynı Mac üzerinde yerel teslim · Ana geliştirici/entegrasyon sorumlusu Claude**

Bu klasör, Lokman ile yapılan üç model kaynak incelemesini ve P9401 çatı seçeneklerini devretmek için hazırlandı. Mevcut `lokmansayim/portman-v2private` deposunun yerine geçmez. Depoya, sunucuya veya Claude sohbetine otomatik gönderim yapılmadı.

## İlk okunacaklar

1. `01_KARARLAR_VE_KURAL_DURUMU.md`: kullanıcı kararları, tarihli kurallar, açık onaylar.
2. `02_MODEL_DURUMU_VE_ACIK_FARKLAR.md`: hangi model/revizyon ne durumda.
3. `KOD_HARITASI.md`: çalıştırılabilir adımlar ile tarihsel betiklerin ayrımı.
4. `YENIDEN_CALISTIRMA.md`: bağımlılıklar, dosya düzeni, güvenli tekrar sırası.
5. `CLAUDE_IS_EMRI.md`: mevcut sisteme devralma görevi ve teslim beklentisi.

Önce `python3 devri_kontrol_et.py` ile paket bütünlüğünü kontrol et. Bu komut yalnız yerel dosya okur; üretim yapmaz, ağ/kurulum/silme/dağıtım işlemi yapmaz. Paketlenmiş tarihli kontrol: `DEVIR_KONTROLU.json`.

## Ne devrediliyor?

| Konum | İçerik |
|---|---|
| `kaynaklar/uc_model/` | P9201/P9401/P9501 özgün SKP ve JPG kopyaları, ortak DWG, hash/yol kaydı |
| `kaynaklar/eski_motor_r01/` | Önceki motor PDF/DXF/JSON/BOM çıktıları; karşılaştırma içindir, kabul edilmedi |
| `kaynaklar/videolar/` | Lokman'ın verdiği altı video; sunum/biçim referansı |
| `kurallar/yerel_2026-09-07/` | Prefabrik v1.4.3, Blender v1.0, ilişkili BOM/ürün başvuru dosyaları |
| `kurallar/depo_okuma_2026-09-30/` | Bu devirde yeniden okunan DURUM, katalog, K02/K04/K16 ve karar dizini; Git blob kimlikleri kayıtlı |
| `teslimler/Uc_Model_Sunum/` | Üç modelin yerel HTML incelemesi, PNG, Blender, geometrik IFC4, raporlar |
| `teslimler/P9401_Cati_Alternatifleri/` | A kaynak çatı, B/C/D öneriler; HTML, IFC, Blender, görseller ve tasarım değerleri |
| `veri/skp/` | Normalize edilmiş scene/selected JSON, düzeltilmiş source.blend ve kaynak dokular |
| `veri/p9401_cati/` | Her çatı seçeneğinin tam geometri girdisi |
| `kod_arsivi/` | Okuyucu, dönüşüm, IFC, Blender, çatı üretimi, paketleme ve kontrol kodlarının son oturum kopyaları |
| `kanit/` | Bağımsız kontroller ve dönüşüm hatalarının teşhis/son kontrol kayıtları |
| `durum/` | Güncel 37 model takibi, P9201 ilk iş emri, önceki sohbet bağlamı |

Kod arşivinin tümünü sırayla çalıştırma: tarihsel yama/deneme betikleri de bilgi kaybı olmaması için saklandı. Özellikle `make_blend.py` eski başlangıç yolu olarak işaretlidir; tek başına çalıştırıldığında giderilmiş eğik dönüşüm hatasını geri getirebilir. Mevcut son source.blend ve normalize veri üzerinden doğrulanmış sıra ayrı belgede verildi.

## Teslimin sınırı

Üç SKP inceleme modeli ve dört P9401 çatı görünümü hazırdır; 37 üretim modeli tamamlanmış değildir. IFC dosyaları geometri referansıdır (`IfcBuildingElementProxy`); semantik BIM, pano hesabı ve BOM tamamlandı diye yorumlanmaz. Kullanıcının en yeni kararı: IFC şimdi, BIM/BOM ayrıntıları sonra.

JPG–DWG/DXF–SKP revizyon uyumu, ölçülü 2D düzeltmeleri ve Lokman kabulü açıktır. P9401 B/C/D çatıları seçilmemiş tasarım önerileridir. Üretime serbest bırakma veya canlı Portman'a entegrasyon yapılmadı.

Paketin içindeki alt teslim klasörleri önceki teslimlerin aynen korunmuş kopyalarıdır; içlerindeki eski takip belgeleri o teslim tarihindeki durumu anlatır. Bu devrin güncel takibi `durum/37_Model_Takip.md` ve `02_MODEL_DURUMU_VE_ACIK_FARKLAR.md` dosyalarındadır.
