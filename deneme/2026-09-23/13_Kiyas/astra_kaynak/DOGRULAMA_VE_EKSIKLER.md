# CAD → Blender aktarım kontrolü — R01

**Sonuç: Tanımlı geometri kontrolleri geçti; aşağıdaki temsil sınırları geçerlidir.**

`yeni-2plus1-yan-verandali.dwg`, v1.4.3 ve 7 Eylül pencere etiketi düzeltmeleriyle `model.blend` dosyasına aktarıldı. Başka projeye ait 5×4 m çelik pilot kullanılmadı. Asıl DWG, yerel DXF, kural kayıtları ve Excel BOM’un SHA-256 değerleri değişmedi.

## Kontroller

| Konu | Sonuç |
|---|---|
| Dış ölçü | 773 × 1076,75 cm; gerçek panel geometrisiyle eşleşti |
| Panel | 52 ayrı panel; yerleşim ve toplam sınırlar eşleşti |
| Duvar | Dış 10 cm, iç 6 cm, yükseklik 250 cm |
| Açıklıklar | 7 pencere, 5 kapı, 1 kapısız geçiş; duvar boşlukları gerçekten işlendi |
| Pencereler | 4 × 120×120, 2 × 120×180, 1 × 60×40 cm; alt kotlar 80/20/160 cm, üst bant 50 cm |
| Kapı/geçiş | Kullanıcı onayıyla 200 cm; kapı enleri ve plandaki yönleri korundu |
| Bağlantı/dikme | 13 elemanın plan izleri korundu; kullanıcı onaylı gösterim yüksekliği 250 cm |
| Birim/dönüş | DXF INSUNITS=5 (cm); metreye bir kez 0,01; X/Y korunur, Z yukarı |
| BOM | Mevcut Excel’in özet ve blok sayım sayfaları: 26 kod, 79 adet; aktarım verisiyle eşleşti |
| Tekrar üretim | Bir tekrar sonunda 232 nesne, aynı geometri imzası; çoğalma yok |
| Kaynak eşleştirme | Kaynak eleman → alt nesneler → BOM kodu; açıklık ve sunum nesneleri yeniden sayılmadı |

Blender dosyasındaki gerçek mesh köşeleri ölçüldü. Panel sınırları/kalınlıkları, açıklıkların boş olması, kapı kanadı plan izi, pencere konumu ve kotu ile bağlantı sınırları kaynakla karşılaştırıldı. Bölme yerleşimleri panel sınırlarının ve 1 m yatay kesitin eşleşmesiyle kontrol edildi; oda alan yazıları kaynaktan taşındı, yeni bir alan hesabı sayılmaz.

Sayısal koordinat toleransı **1 mm** olarak seçildi; imalat toleransı veya üretim onayı değildir. 1 m kotundaki panel kesitlerinin simetrik alan farkı yaklaşık **0,00000672 m²**, kontrol eşiği 0,0001 m² altında. Bu karşılaştırma bağlantıların imalat kesiti doğrulaması değildir.

## Temsil sınırları

- Köşe/H bağlantıları ve veranda dikmelerinde **250 cm yalnız 3D gösterim yüksekliğidir**. Kesim, sipariş boyu veya metraj çıkarılmaz. Plan kesitleri kaynakta olduğu gibi taşındı; eksik profil et kalınlığı üretilmedi. H çizgileri yüzey olarak gösterildi.
- İki veranda kenar profilinin düşey kotu ve tam kesiti tanımlı değil. Malzeme bağlantıları korundu; kaynak çizgileri gizli referansta, tam 3D profil olarak gösterilmiyor.
- Kaynakta çatı eğimi/profil çizgileri var; tam çatı montaj geometrisi yok. Bu çizgiler gizlenebilir çatı referans koleksiyonunda korundu. Yeni çatı, kaplama katmanı veya taşıyıcı detay tasarlanmadı.
- Kapılar kaynak planındaki açık kanat izi ve onaylı yükseklikle gösterildi. Pencereler kaynak yanakları ve gerçek açıklık/kotlarıyla gösterildi; cam tek yüzeyli temsildir. Ürünlerin tanımsız 3D aksesuar, başlık ve imalat detayları eklenmedi.
- Alt düzlem, nötr renkler, aydınlatma, oda yazıları ve panel ayrım çizgileri sunum içindir; döşeme reçetesi veya BOM kalemi değildir. Kaynakta olmayan mobilya eklenmedi.
- ANA bina sayıldı; KOPYA/MONTAJ pafta gösterimleri, ölçüler, taramalar ve kapı açılım yayları fiziksel malzeme olarak yükseltilmedi. Bir malzemenin birden fazla alt mesh’i olabilir; 232 nesne, 232 malzeme değildir.

Ayrıntılı ölçü kayıtları `validation.json`, kaynak sınıflandırmaları ve eksikler `model_data.json` içindedir. Tekrar çalıştırma için `CALISTIRMA.md` dosyasını kullanın.
