# Mevcut CAD’den Blender’a aktarım — R01

Kaynak: `yeni-2plus1-yan-verandali.dwg`, yan verandalı 2+1, 6×8,5 modül. Kural: **v1.4.3 ve 7 Eylül 2026 montaj pencere etiketleri**. Hedef: aynı klasördeki `model.blend` (Blender 5.2.1 LTS).

Orijinal DWG, kurallar ve Excel BOM değiştirilmedi. `kaynaklar/` içinde bu revizyonun doğrulanmış kopyaları; `kaynak_dogrulama.json` içinde asıl yollar ve SHA-256 kayıtları var. Kaynak DXF, kayıtlı DWG ile eşleştirilmiş yerel AutoCAD dışa aktarımıdır. Bu araç açık AutoCAD oturumundaki kaydedilmemiş değişiklikleri okumaz.

## Teslim dosyaları

- `model.blend`: düzenlenebilir panel, doğrama, bağlantı ve dikme nesneleri.
- `plan_2D.png`: aynı kayıtlı modelin üstten ortografik görünüşü. Duvarlar tam yükseklikte olduğu için lentolar altlarındaki açıklıkları üstten örter; bu görüntü kesit değildir.
- `plan_3D.png`: çatısız perspektif.
- `CAD_Blender_karsilastirma.png`: 1 m kotunda CAD ve gerçek Blender panel kesitlerinin aynı koordinatta karşılaştırması.
- `model_data.json`: gerçek CAD geometrisi, ürün kodları, koordinatlar, kotlar, onaylar ve temsil sınırları.
- `cad_blender_mapping.json`: kaynak CAD kimliği → ortak eleman kimliği → Blender nesneleri → mevcut BOM kodu.
- `validation.json`: kaynak bütünlüğü, geometri, tekrar üretim ve mevcut Excel karşılaştırması.
- `DOGRULAMA_VE_EKSIKLER.md`: kontrollerin ve sınırların kısa açıklaması.
- `kod/`: dışa aktarım okuma, model oluşturma, kontrol ve görüntü üretme kodları.

## Aynı revizyonu tekrar üretmek

Bu klasörde terminal açıp aşağıdaki komutu çalıştırın. Mevcut kurulu Python, openpyxl ve Pillow kullanılır; paket yüklenmez ve yapay zekâ çağrısı yapılmaz.

```sh
/Users/lokmansayim/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 kod/run_transfer.py
```

Kod kaynakların özetlerini doğrular, JSON’u oluşturur, Blender modelini üretir, aynı modelde bir kez tekrar üretir, gerçek geometriyi denetler, kayıtlı modelden iki görüntüyü alır ve raporu yazar. Blender’ın grafik aygıtına erişimi gerekir. Hata olduğunda işlem durur.

Bu komut bu revizyon klasöründeki üretilmiş `model.blend`, JSON, kontrol raporları ve PNG’leri yeniler. Elle değiştirilmiş teslim modelini korumak için önce ayrı adla kaydedin. Orijinal CAD/BOM arşivine yazmaz.

Tek model oluşturma adımı yalnız `PEV-YAN-VERANDALI-2PLUS1/BLENDER-R01` sahiplik işaretli nesneleri yeniler; diğer nesneleri silmez. Tam tekrar üretim komutu başlangıçta temiz Blender sahnesi kullanır. Aynı revizyonun tekrarında nesne sayısı 232 kalır; sunum nesneleri malzeme adedi değildir.

## Yeni kaynak revizyonu

Yeni DWG için bu klasörü kaynakların üzerine yazarak kullanmayın. Yeni revizyon klasörü açılmalı; AutoCAD’den aynı kaydedilmiş çizimin yerel DXF çıktısı ve ilişkili BOM alınmalı, geometri ve dosya özetleri birlikte doğrulanmalıdır. Kod kaynak değiştiğinde sessizce devam etmez. CAD handle tabanlı yan kimlik eşleştirmesi bu doğrulanmış revizyon için geçerlidir; başka dışa aktarımdaki kimlikler yeniden uzlaştırılır.

Blender koleksiyonlarında `PEV_Roof_reference` ve `PEV_CAD_profile_references` başlangıçta gizlidir. Tam tanımlanmamış çatı ve profil çizgileri burada kaynak referansı olarak tutulur.
