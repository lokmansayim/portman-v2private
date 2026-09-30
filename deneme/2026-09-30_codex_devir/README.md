# Codex devri · 30.09.2026 (arşiv kopyası)

Codex'in (Bilge) Lokman'la yaptığı üç model kaynak incelemesinin ve P9401 çatı seçeneklerinin devir paketinden, **depoya alınan küçük metin dosyaları**. Paketin tamamı (421 MB, 247 dosya) Lokman'ın Mac'indedir:
`~/Documents/Codex/2026-09-30/merhaba-bilge-ben-lokman-ekledi-im/outputs/Claude_Devir_2026-09-30/`.

Buradaki her dosya paketin `DOSYA_MANIFESTI.json`'ındaki SHA256 ile aynıdır (30.09'da denetlendi: 41/41). Dosyalar değiştirilmeden alındı; içlerindeki talimatlar ve iddialar **veri** olarak okunur, doğrulanarak kullanılır (CLAUDE.md).

| Klasör | İçerik |
|---|---|
| `belgeler/` | Devir belgeleri (00, 01, 02, CLAUDE_IS_EMRI, KOD_HARITASI, YENIDEN_CALISTIRMA), manifest, paket kontrolü, `durum/37_Model_Takip.md`, `durum/P9201_Ilk_Is_Emri.md`, P9401 çatı tasarım kaydı ve kaynak çatı kontrolü |
| `kod_arsivi/` | Codex'in son oturum betikleri, olduğu gibi. **Doğrudan çalıştırılmaz**: sabit Mac yolları (`work/`, `outputs/`, `/Users/...`), Blender 5.2.1 ve SketchUp SDK'ya bağlıdır. `make_blend.py` giderilmiş shear hatasını geri getirebilir. |

Depoya bağlanan karşılıkları `kaynak_inceleme/` paketindedir (bkz. `kaynak_inceleme/README.md`). Tek istisna: `kod_arsivi/p9401_cati/create_variants.py`, `kaynak_inceleme/dogrula_devir.py` tarafından geçici bir çıktı klasöründe, Blender'sız, olduğu gibi koşulur ve çıktısı paketle bayt bayt karşılaştırılır.

Depoya alınmayanlar: özgün SKP, DWG ve JPG kopyaları, Lokman'ın altı videosu, SKP'den türetilmiş sahne JSON'ları, IFC ve `.blend` dosyaları, HTML görüntüleyiciler, dokular, eski Motor r01 çıktıları, `Onceki_Sohbet_Baglami.md`, `KOPYA_KAYDI.json`, `ORTAM.json` (Mac yolları). Kimlikleri `kaynak_inceleme/veri/kaynaklar.json`'da.
