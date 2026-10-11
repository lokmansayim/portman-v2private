# Meta şablon başvurusu · İE-07 (11 Ekim 2026)

Lokman WhatsApp Manager'dan gönderir (Meta Business Suite → WhatsApp Manager → Account tools → Message templates → Create template). İki şablon; metinler Lokman'ın 11 Ekim 2026 kararı (Karar 2), aynen. Onaylanınca adlar sunucuya `vps/ayar.sh` ile girilir (canlı kapı; ayrı onay):

```
ssh portman-vps 'bash /opt/portman/guncel/vps/ayar.sh sablon_patron_bildirim portman_patron_bekliyor_v1'
ssh portman-vps 'bash /opt/portman/guncel/vps/ayar.sh sablon_bayi_dosyalar_hazir portman_dosyalar_hazir_v1'
```

Ad Meta'da farklı verilirse `ayar.sh`'ye o ad yazılır (küçük harf, rakam, alt çizgi). Ad girilene kadar kanal şablon satırını `gonderilmedi: sablon_yok` olarak tutar; panelde "şablon tanımsız" diye görünür, günlüğe yazılır.

Her iki şablon için ortak alanlar: **Kategori: Utility** · **Dil: Turkish (tr)** · Başlık (header) yok · Alt bilgi (footer) yok. Meta kuralı: gövde değişkenle başlayamaz ve bitemez; her değişken için örnek değer istenir; değişkenler sırayla `{{1}}`, `{{2}}`. Kod her değişkeni dolu gönderir (boş değişken Meta'da reddedilir).

## 1 · Patron'a bildirim — `portman_patron_bekliyor_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_patron_bekliyor_v1` |
| Gövde (aynen) | `Portman: {{1}} kodlu bayinin {{2}} numaralı talebi sizi bekliyor. Ayrıntıyı panelden görebilirsiniz.` |
| `{{1}}` örnek | `B1234` (bayi kodu) |
| `{{2}}` örnek | `PM-B1234-20261011-1` (İş Emri no; yoksa `T-1A2B3C4D` biçiminde talep kimliği; asla boş) |
| Düğme | **Call to action → Visit website**, metin `Panele git`, URL türü **Dynamic**: `https://portman.portatifev.com/panel/{{1}}`; örnek sonek `konusma/905000000000` (kod `konusma/<bayi numarası>` gönderir; sayfa doğrudan konuşma) |
| Ne zaman gider | Portman bir talebi çizemeyince (yönlendirme), çıkarım ya da beklenmeyen hata olunca, bayi "Dosyaları gönder"e basınca. Yalnız Patron'un 24 saat penceresi kapalıysa; pencere açıksa metin gider, şablon gitmez (ücret boşa gitmez). |

## 2 · Bayiye "dosyalarınız hazır" — `portman_dosyalar_hazir_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_dosyalar_hazir_v1` |
| Gövde (aynen) | `Merhaba {{1}}, {{2}} numaralı projenizin dosyaları hazır. Bu mesaja yanıt verirseniz dosyaları buradan gönderebiliriz.` |
| `{{1}}` örnek | `Ahmet Bey` (bayi kartındaki hitap; boşsa ad; o da boşsa `Sayın Bayimiz`) |
| `{{2}}` örnek | `PM-B1234-20261011-1` (bayinin son İş Emri no'su) |
| Düğme | **Quick reply**, metin `Dosyaları gönder` (kod düğmeye `dosya:<İş Emri no>` payload'u koyar; bayi basınca Meta tarafında 24 saat penceresi açılır, Portman LLM çağırmadan "Teşekkürler, dosyalarınızı bu sohbetten iletiyoruz." der ve Patron'a bildirir) |
| Ne zaman gider | Patron panelde konuşma sayfasından düğmeye basınca; pencere kapalıyken de gider (ücretli). Bayinin İş Emri kaydı yoksa düğme kapalıdır. |

## Eski şablon

Hosting döneminden kalan `portman_proje_hazir_v1` adlı şablon depoda yok, Meta hesabında olabilir; yapı tipine bağlı metniyle kullanılmaz. Silinmesi Meta'da Lokman'ın kararı (silme kapısı); kod ona başvurmaz.

## Onaydan sonra denemeler (ücretli; her biri ayrı onayla; İE-07 › Kabul koşulu "canlı kapı deneme listesi")

1. Patron'un penceresi kapalıyken (Patron 24 saattir yazmamışken) bir bayi çizilemeyen bir model ister → Patron'a şablon gelir, düğme konuşma sayfasını açar.
2. Panelden bir bayiye "dosyalar hazır" → bayide şablon ve düğme; düğmeye basınca sabit cevap; ardından panelden PDF gönderimi.
