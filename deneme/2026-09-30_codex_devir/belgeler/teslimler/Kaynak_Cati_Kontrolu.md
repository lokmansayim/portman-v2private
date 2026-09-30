# P9401 çatı seçenekleri için kaynak kontrolü

Salt okunur inceleme. Kaynak: `work/skp_import/P9401/scene.json`, `selected.json` ve mevcut `outputs/Uc_Model_Sunum/P9401/P9401_inceleme.blend`. Tüm koordinatlar normalize edilmiş kaynak dünya koordinatında metre. Aşağıdaki sayılar mevcut SKP geometrisinden okunmuştur; yeni alternatiflere verilmiş üretim ölçüleri değildir.

## Kaynak çatı formu

**Ana çatı beşik; ön veranda üzerinde ona dik bir beşik kol birleşiyor. Kırma çatı değil.** Ana mahya x=-0,25 ile x=10,49 arasındaki iki uç alınlığa kadar kesintisiz uzanır: y=5,06, z=4,640014176. Kırmızı ana örtü yüzleri 112347/112349/112350; iki uç alınlık yüzleri 112264/112334. Ön kol mahyası x=6,9775, z=4,2017 olup y=-1,515'ten ana birleşim y=3,63'e uzanır. Ön birleşimin kırmızı yüzleri 112523/112525'tir.

## Sabit kaynak kotları ve sınırları

| Parça | Kaynaktaki koordinat/sınır |
|---|---|
| Gövde node1 duvar üstü | z=3,1017 |
| Döşeme / veranda üstü | z=0,6017 |
| Kaynak gövde duvar yüksekliği | 2,50 m |
| Ana örtü yatay kutusu | x=[-0,25;10,49], y=[0,3675;9,7525] |
| Saçak altı / üstü | z=3,1017 / 3,2017; 0,10 m **düşey geometrik fark** |
| Ana mahya altı / üstü | z=4,540014176 / 4,640014176 |
| Tüm node223 kutusu | x=[-0,25;10,49], y=[-1,515;9,7525], z=[3,1017;4,640014176] |
| Ön veranda örtü kolu | x=[3,715;10,49], y=-1,515 ön kenarı; birleşim y=3,63'e kadar |
| Veranda kol mahya altı / üstü | z=4,1017 / 4,2017 |
| Dikme node2 | x=[4,065;4,145], y=[-1,235;-1,155], z=[0,6017;3,1017] |
| Dikme node3 | x=[7,0625;7,1425], y=[-1,235;-1,155], z=[0,6017;3,1017] |
| Dikme node4 | x=[10,06;10,14], y=[-1,235;-1,155], z=[0,6017;3,1017] |
| Veranda ön platform dış kenarı | y=-1,335; x=3,715..10,49; z üst=0,6017 |
| Merdiven dahil kaide kutusu | x=[-0,25;10,49], y=[-1,935;9,7525], z=[0,0017;0,6017] |

Duvarların üst dış konturu, z=3,1017'de:

`(0;0,6175) → (3,965;0,6175) → (3,965;2,5) → (10,24;2,5) → (10,24;9,5025) → (0;9,5025)`.

Node1'in genel kutusundaki y=0, döşeme/veranda yüzeyinden gelir; y=0'ı kapalı gövdenin ön duvarı saymamak gerekir. Öndeki kapalı gövde L biçiminde geri çekilir. Veranda alanını yeni alınlık üretirken kapalı duvara dönüştürmemek gerekir.

Node223 üst örtüsünün dış izdüşümü yaklaşık L konturdur:

`(-0,25;0,3675) → (3,715;0,3675) → (3,715;-1,515) → (10,49;-1,515) → (10,49;9,7525) → (-0,25;9,7525)`.

Kaynağın kol birleşiminde ayrıca y=0,365211 kullanılmıştır; ana saçak y=0,3675'ten yaklaşık 2,289 mm farklıdır. Bu kaynak farkı yeni bir üretim ölçüsü gibi yayılmamalı, kaynak veride sessizce düzeltilmemelidir.

## Önerileri üretirken parça kapsamı

- `roof=true` yalnız node223'tür. Ana örtü, veranda örtüsü, üst alınlıklar, saçak altı/kenar yüzeyleri aynı node223 içinde. Yeni çatı seçilince bu nesnenin tamamını gizlemek eski üçgen alınlıkları da kaldırır; duvar gövdesini kesmek gerekmez.
- **Sade kırma öneri:** çevre saçak altı aynı duvar üstünde tutulursa yükselen uç üçgen alınlık gerektirmez. Ana gövde ve öndeki veranda kolunun birlikte mi ayrı örtüyle mi çözüldüğü yeni öneride açık olmalı; kaynak üç dikmenin üzerindeki örtü sürekliliği kontrol edilmeli.
- **Tek eğim öneri:** yeni çatı düzlemi ile z=3,1017 duvar üstü arasında yüksek cephede dikdörtgen, eğim doğrultusuna paralel iki yanda üçgen/trapez kapama gerekir. Eğim +y'ye doğru yükselirse x=0 ve x=10,24 yanları eğimli kapanır; y=9,5025 arka cephe en yüksek kapama olur. L gövdenin ön y=0,6175 ve y=2,5 duvarları ayrı sınırdır. Veranda önünü duvarla kapatmak yerine dikmeler/örtü ilişkisi ayrıca gösterilmeli.
- **Parapetli düz görünüş önerisi:** yükselen üçgen alınlık yok; yatay örtü çevresinde parapet öneri geometrisi gerekir. Kaynaktaki 0,10 m saçak bant farkı, yeni döşeme/parapet kalınlığının üretim ölçüsü olarak kullanılamaz. Yeni parapet yüksekliği, iç eğim, su tahliyesi ve kaplama kalınlığı kaynakta doğrulanmış değildir.
- Node223 dışındaki mevcut oluk elemanları korunmuş durumdadır: node45–59 yaklaşık x=-0,263..3,69945, y=0,23904..0,3675, z=3,04234..3,16434; node60 iniş elemanı x=-0,08833..-0,03133, y=0,28671..0,6475. Yalnız node223 gizlenince bunlar kalır. Yeni saçak hattıyla uyumları görsel olarak kontrol edilmeli; yeni bir çatıya mevcut oluk çözümünün uygun olduğu varsayılmamalı.

## Aktarım kontrolü

Kaydedilmiş Blender'da node1/2/3/4/5/223 nesne matrisleri identity; dönüşüm köşelere uygulanmış. Kaynakla dünya koordinatı farkları node223'te 0,000954 mm, kontrol edilen altı parça içinde en çok 0,001349 mm. Kaynak geometriyle eşleşiyor. Ölçü onayı / üretim uygunluğu / statik değerlendirme yapılmadı.

Ham ayrıntılar: `source_geometry.json`; Blender karşılaştırması: `blend_source_check.json`.
