# Meta şablon başvurusu · İE-08 8b (14 Ekim 2026)

Görev 5'in ilk teslimi. Lokman WhatsApp Manager'dan başvurur (Meta Business Suite → WhatsApp Manager → Account tools → Message templates → Create template); onay süresi kodu bekletmez. Metinler Code'un taslağıdır; karşılama şablonunun gövdesi Lokman'ın 14 Ekim düzeltmesidir (plan onayı, madde 2). Lokman başvururken metni değiştirirse bu belge ve `kanal/sablonlar.py` aynı commit'te güncellenir.

Onaylanınca adlar sunucuya `vps/ayar.sh` ile girilir (canlı kapı, Görev 6; ayrı onay). Ad girilene kadar kanal satırı `gonderilmedi: sablon_yok` olarak tutar; panelde "şablon tanımsız" diye görünür (İE-07 ile aynı):

```
ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh sablon_muhendis_kontrol portman_muhendis_kontrol_v1'
ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh sablon_muhendis_hatirlatma portman_hatirlatma_v1'
ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh sablon_bayi_karsilama portman_karsilama_v1'
ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh sablon_bayi_bilgi_hazir portman_bilgi_hazir_v1'
```

Ad Meta'da farklı verilirse `ayar.sh`'ye o ad yazılır (küçük harf, rakam, alt çizgi). Ayar anahtarları 8b kodu canlıya çıkınca tanınır; o sürümden önce `ayar.sh` bu anahtarları reddeder.

**Ortak alanlar (dördü için):** Kategori **Utility** · Dil **Turkish (tr)** · Başlık (header) yok · Alt bilgi (footer) yok · Değişkenler sıra numaralı (`{{1}}`, `{{2}}`). Meta kuralı: gövde değişkenle başlayamaz ve bitemez; her değişken için örnek değer istenir. Kod her değişkeni dolu gönderir. Meta bir şablonu "Marketing" sayarsa (ücret farklı) Lokman bildirir; metin sadeleştirilip `_v2` ile yeniden başvurulur.

**Patron için yeni şablon yok.** "Mühendis onayladı, fiyat sizde" bildirimi ve Patron hatırlatmaları onaylı `portman_patron_bekliyor_v1` şablonuyla gider (Patron'un penceresi kapalıysa; açıksa yalnız metin).

## 1 · Mühendis bildirimi — `portman_muhendis_kontrol_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_muhendis_kontrol_v1` |
| Gövde (aynen) | `Portman: {{1}} numaralı işin {{2}} revizyonu bayi tarafından onaylandı ve teknik kontrolünüzü bekliyor. Dosyaları almak için Gönder'e basın.` |
| `{{1}}` örnek | `PM-B1234-20261014-1` (İş Emri no) |
| `{{2}}` örnek | `r03` (bayinin onayladığı revizyon) |
| Düğme | **Quick reply**, metin `Gönder` (kod payload'a `muh:gonder:<İş Emri no>:<rev>` koyar) |
| Ne zaman gider | Bayi çelik planda Onayla'ya basınca ve onay revizyona bağlanınca (onay denetimi geçince), aktif mühendis kartına; her zaman şablon (mühendisin penceresi açık olsa da: ilk temas ve düğme). Aktif mühendis kartı yoksa gitmez; Patron'a "mühendis kartı yok" metni gider, iş durmaz. |
| Basınca | Mühendisin penceresi açılır; Portman LLM çağırmadan sırayla gönderir: bayinin onayladığı revizyonun görseli, görünüşlü pafta PDF'i (TASLAK), yükleme listesi Excel, DXF; ardından **[Patron'a gönder] [Düzeltme iste]** düğmeli mesaj. |

## 2 · Mühendis hatırlatması — `portman_hatirlatma_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_hatirlatma_v1` |
| Gövde (aynen) | `Hatırlatma: {{1}} numaralı işin teknik kontrolü {{2}} saattir sizi bekliyor. Dosyaları yeniden almak için Gönder'e basın.` |
| `{{1}}` örnek | `PM-B1234-20261014-1` |
| `{{2}}` örnek | `2` (bildirimden bu yana geçen saat; tam sayı) |
| Düğme | **Quick reply**, metin `Gönder` (payload şablon 1 ile aynı) |
| Ne zaman gider | Mühendis karar verene kadar (Patron'a gönder ya da Düzeltme iste), bildirimden 1 saat sonra ve sonra saat başı; yalnız 08:00–20:00 (İstanbul) arasında. Gece onaylanan işte bildirim hemen gider, süre ve hatırlatmalar 08:00'de başlar. 3 saat dolunca Patron'a bir kez "mühendis cevap vermedi" bildirimi gider (metin; penceresi kapalıysa `portman_patron_bekliyor_v1`). Mühendisin penceresi açıksa da şablon gider (düğme yeniden dosya ister). **Her hatırlatma ücretlidir** (utility). |

## 3 · Karşılama — `portman_karsilama_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_karsilama_v1` |
| Gövde (aynen; Lokman 14 Ekim) | `Merhaba {{1}}, Portman bayi kaydınız onaylandı. Plan taleplerinizi bu sohbete yazabilirsiniz; nasıl çalıştığını görmek için aşağıdaki düğmeye basın.` |
| `{{1}}` örnek | `Ahmet Bey` (bayi kartındaki hitap; boşsa ad; o da boşsa `Sayın Bayimiz`; D-06) |
| Düğme | **Quick reply**, metin `Nasıl çalışır?` (payload `bilgi:nasil`) |
| Ne zaman gider | Patron panelde kartın sayfasından "Karşılama gönder"e basınca; yalnız hiç yazmamış aktif karta (İE-07 bulgusu b: ilk teması biz başlatırız). Pencere kapalıyken gider (ücretli). |
| Basınca | Portman LLM çağırmadan "Nasıl çalışır?" PDF'ini (bayi rehberi §1–3, tek sayfa; metni Görev 9'dan) belge olarak gönderir. |

## 4 · Bilgi hazır (plansız) — `portman_bilgi_hazir_v1`

| Alan | Değer |
|---|---|
| Ad | `portman_bilgi_hazir_v1` |
| Gövde (aynen) | `Merhaba {{1}}, talebinizle ilgili bilgi hazır. Bu mesaja yanıt verirseniz bilgiyi buradan iletebiliriz.` |
| `{{1}}` örnek | `Ahmet Bey` (hitap; şablon 3 ile aynı sıra) |
| Düğme | **Quick reply**, metin `Bilgiyi gönder` (payload `bilgi:hazir`) |
| Ne zaman gider | Patron panelden basınca, her aktif karta; bayinin planı olmasa da (İE-07 bulgusu a: yönlendirilen talepte pencere kapanınca bayiye ulaşılamıyordu). Pencere kapalıyken gider (ücretli). |
| Basınca | Portman LLM çağırmadan "Teşekkürler, bilgiyi bu sohbetten iletiyoruz." der ve Patron'a bildirir (metin; penceresi kapalıysa `portman_patron_bekliyor_v1`); Patron panelden yazar ya da PDF gönderir. |

## Onaydan sonra denemeler (ücretli; Görev 6; her biri ayrı onayla)

1. Prova kartı çelik planda Onayla → mühendis kartında şablon 1 → Gönder → görsel, PDF, Excel, DXF ve iki düğme. DXF WhatsApp'ın belge türlerinden değildir: düz metin olarak yüklenir, görünen adı `Portman_<no>_rNN.dxf`; Meta reddederse ad `.dxf.txt` olur (plan kararı 2).
2. Mühendis Excel'i düzeltip gönderir, "Patron'a gönder" → Patron'a bildirim ve son Excel.
3. "Düzeltme iste" + not → Patron'a not, bayiye "kontrol sürüyor".
4. Bir hatırlatma (bildirimden 1 saat sonra, 08:00–20:00 içinde).
5. Panelden prova kartına karşılama → "Nasıl çalışır?" → PDF; bilgi hazır → "Bilgiyi gönder" → sabit cevap.
