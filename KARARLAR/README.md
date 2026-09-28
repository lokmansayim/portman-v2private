# Karar defteri

Portman'ın kararları üç seride tutulur. Numaralar çakışmasın diye ayrıdır: **K01–K25**, 20–22 Eylül karar kaydıdır; **Z-01–Z-10**, 27 Eylül Zemin kararlarıdır; **D-01'den** sonrası, bu depoda alınan kararlardır. Kökteki `KARARLAR.md`, v1.1.1 ağacının tarihli karar günlüğüdür ve değiştirilmedi.

Her kararda şu alanlar aranır: gerekçe, kapsam, tarih, kanıt, yeniden değerlendirme koşulu ve geri dönüş yolu. Kaynağında olmayan alan uydurulmadı; dosyanın sonunda "kayıtta olmayan alanlar" diye yazılıdır. Bir karar yeni kanıtla açılır; kritik hata ve güvenlik sorunu tetik beklemez. Eski kayıt silinmez, yeni sürüm eklenir.

## K01–K25 · 20–22 Eylül karar kaydı (sürüm 2)

Biçim: karar · gerekçe · reddedilen seçenekler · geri alma yolu · kim ve kanıt. "Lokman onayladı" ifadesi yalnız sohbette açık bir onay varsa yazılmıştır. Bir alan kendi etiketiyle ya da metin içinde açıkça geçiyorsa var sayılır: kim, başlıkta ya da imzada ("— Claude") adı geçen kişidir; kanıt, kararın dayanağının ya da uygulamasının denetlenebileceği bir kaynağa (belge, commit, kod, ekran, denetim bulgusu) yapılan atıftır. Karar günlüğüne (kökteki `KARARLAR.md`) ya da başka bir karara yapılan atıf kanıt sayılmaz; bunlar kararın kaydıdır, dayanağı değil. Alan kararın yalnız bir kısmı için varsa dipnotta "kısmen" diye yazılır. Atıf yapılan kaynakların bir kısmı depoda değil, Lokman'ın masaüstü klasöründedir (`07_Denetim/`).

| No | Karar |
|---|---|
| [K01](K01.md) | Kapsam: önce katalog modelleri + basit varyantlar; serbest yerleşim sonra (20–21.09) |
| [K02](K02.md) | Motor: koordinatsız, pano birimli İş Emri; kural v1.4.3; "DXF yeniden açılıp doğrulanmadan PDF yok" (21.09) |
| [K03](K03.md) | BOM blok şeması Astra v1.4.3 (`BOM_*`); Güncel Şablon 2024 blok adlarına geçiş **beklemede** (21.09) |
| [K04](K04.md) | Dış kapı 90 cm (sembol 97'den x'te ölçekli), iç kapı 82 cm — çalışma kabulü (21.09) |
| [K05](K05.md) | Mimari: LLM anlar → kod karar verir → Motor çizer → insan onaylar; ajan döngüsü yok (21–22.09, Astra ile uzlaşı) |
| [K06](K06.md) | Kanal v1 hosting'de: PHP imzalı webhook yakalar → kuyruk → Python cron üretir → PHP gönderir (21.09) |
| [K07](K07.md) | Patron modu + önce kuru çalışma, sonra gerçek gönderim; kill switch'ler (21.09) |
| [K08](K08.md) | Görev 2 Python cron'u silindi (21.09) |
| [K09](K09.md) | Kalıcı ilkeler (21.09, Lokman): öz-test asla WhatsApp'a göndermez; sunucu değişikliği yalnız yetkiyle, yedek + geri alma ile; sırlar koda/sohbete/rapora/günlüğe yazılmaz; numaralar maskelenir |
| [K10](K10.md) | Beyin çıkarım arka ucu: OpenAI Chat Completions, gpt-4o-mini, anahtar panelin `ayarlar.json`'undan yalnız okunur (21.09) |
| [K11](K11.md) | VPS: Natro XCloud Pro, aylık 29,99 $ (22.09) |
| [K12](K12.md) | Hibrit mimari: hosting = kontrol düzlemi (Meta webhook, kuyruk, gönderim, WhatsApp anahtarı, görüşme durumu); VPS = üretici; ajan yalnız dışarıdan bağlanır (22.09) |
| [K13](K13.md) | Eşleşme anahtarı modeli: VPS'te üretilen 64-hex anahtar, hosting'te `api_token.txt`; `hash_equals`; OpenAI anahtarı hosting'ten HTTPS ile ajana gider, VPS diskine yazılmaz (22.09) |
| [K14](K14.md) | Paket dağıtımı hosting kanalıyla (`kanal/package/current.zip` sha değişince ajan kendini günceller, öz-test koşar); komut kanalı (`vps_komut`) kapalı başlar (22.09) |
| [K15](K15.md) | Tek depo: GitHub `lokmansayim/portman` (özel); kod, kural sürümü, şema, testler, KARARLAR.md (22.09) |
| [K16](K16.md) | Katalog planları çıkarıcıyla okunur, elle kodlanmaz; artıklar raporlanır, sessiz yuvarlama yok (22.09) |
| [K17](K17.md) | Sızan eşleşme anahtarı yenilenecek: `rm /etc/portman/agent.env` + bootstrap tekrar + yeni anahtar `api_token.txt`'e (22.09, **uygulanmadı**) |
| [K18](K18.md) | Beyin kuralı (22.09, iki adım): odada tek pencere varken "penceresi 120x180" ölçü değişikliğidir; ölçüt **bayinin kendi mesajı**, LLM özeti değil |
| [K19](K19.md) | NumPy < 2 sabitlemesi (VPS) (22.09) |
| [K20](K20.md) | Yol haritası kabul ölçütleriyle ilerler, takvim tahmindir; Lokman'ın açık kararları: pilot planlar, pafta örneği, K16(a/b), K3 (22.09) |
| [K21](K21.md) | Kural belirsizlikte sessizce değiştirmez, sorar (22.09 20:00, denetim F03 üzerine) |
| [K22](K22.md) | Harness eylemin yanında İş Emri içeriğini sınar (22.09 20:05) |
| [K23](K23.md) | Motor doğrulama geçmezse teslim PDF'i üretmez (22.09 20:08, F08) |
| [K24](K24.md) | Denetim tek komutla tekrarlanır (`denetim/kos.py`), dağıtım hash'i manifestten okunur (22.09 20:15, F04/F05) |
| [K25](K25.md) | Kabul edilip ertelenen: imzalı paket (ed25519), yetki ayrımı (claim/result/settings), eşzamanlı failover testi, çıkarıcının düşen kapıyı hata sayması (v0.2) |

### Reddedilen ama bilinmesi gereken öneriler
- Webmaster'ın DigitalOcean önerisi (fiyat/KVKK gerekçesiyle Natro).
- "Hosting'i tamamen bırakıp tek makine" (Aşama 2.0'a ertelendi; Lokman "yolu uzatmıyor muyuz" diye sordu, hibrit gerekçesini kabul etti).
- Fine-tuning / vektör RAG / LangGraph (araştırma raporu, kaynaklı).

## Z-01–Z-10 · Zemin kararları (27 Eylül 2026)

| No | Karar | Yeniden açılır, eğer |
|---|---|---|
| [Z-01](Z-01.md) | Doğru tek yerde: repo + Postgres | Veri bütünlüğünü bozan bir kanıt çıkarsa |
| [Z-02](Z-02.md) | Önce Yapı Tanımı; çıktılar ondan türetilir | Tanım bir çıktının ihtiyacını taşıyamazsa |
| [Z-03](Z-03.md) | Öneren ve hakem ayrı; bağlayıcı karar tekrar üretilebilir, sürümlü ve testli | Bir model PortmanBench geometri görevlerinde %98'i geçerse birincil öneren o olur; kuralların anlamı ve onay izi korunur |
| [Z-04](Z-04.md) | Tek veritabanı: Postgres + pgvector, ayrı vektör veritabanı yok | Arama süresi ya da vektör sayısı sorun olursa |
| [Z-05](Z-05.md) | Birincil model Claude Opus 5.5, model geçidi arkasında (canlıda bugün gpt-4o-mini) | Başka bir model (açık ya da yerel dahil) PortmanBench'te aynı skoru daha ucuza alırsa |
| [Z-06](Z-06.md) | Tek sunucu, GPU yok | Ölçülen render süresi ya da kuyruk beklemesi işi tıkarsa ya da günlük talep 50'yi geçerse |
| [Z-07](Z-07.md) | BIM çıktısı IFC4 (açık ISO standardı) | Bir araç ya da müşteri başka bir IFC sürümü gerektirirse |
| [Z-08](Z-08.md) | Kişisel veri sunucuda, LLM'e takma adla | Hukuki görüş başka bir şey söylerse |
| [Z-09](Z-09.md) | Ayda bir alan taraması: BenchCAD, Text2CAD-Bench, plan üretimi, IFC ve görsel modeller; her ayın 1'inde planlı görev | Süreç kararı; bir varsayımı bozan gelişme ilgili kararı açar |
| [Z-10](Z-10.md) | Çift doğrulama: her teklif iki bağımsız yöntemle hesaplanır, modelden kesin metraj (IFC) ve CTKBF mantığıyla parametrik tahmin (Python); kalem grubu eşik dışındaysa ön onay durur, mühendis inceler | İki yöntem gerçek yükleme listelerinde aynı hatayı paylaşırsa; eşikler PortmanBench ile ayarlanır |

## D-01 ve sonrası · Bu depoda alınan kararlar

| No | Karar | Tarih |
|---|---|---|
| [D-01](D-01.md) | B2: taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar (yeni talep mi, değişiklik mi) | 28.09 |
| [D-02](D-02.md) | Referans PDF'in içeriğini de izler (bütün çizimler, sabit üretim zamanı); yeniden dondurma bir karara dayanır | 28.09 |
| [D-03](D-03.md) | Kalıcı akışta yarım kalan iş en çok üç kez yeniden alınır; LLM yeniden çağrılmaz, gönderim tekrarlanmaz (**önerildi, canlıdan önce Lokman onayı**) | 28.09 |

## 27 Eylülde Lokman'ın verdiği kararlar

1. **Sunucu:** Elindeki Natro VPS ile başlanıyor; kurulum taşınabilir (K11 ile aynı yönde).
2. **Eski kod:** Yeni repo açılıyor; önce çalışan sürüm (v1.1.1) ve referans çıktıları kayda alınıyor, sonra testi geçen parçalar taşınıyor. Bu depo o kararın uygulamasıdır (İE-01).
3. **Hafıza:** Sıfırlanmıyor; projenin doğrusu repoya ve veritabanına taşınıyor.
4. **Alan taraması:** Her ayın 1'inde planlı görev (Z-09).
5. **Çift doğrulama:** İlke olarak kabul edildi (Z-10).

## Açık kararlar (sahibi Lokman)

- **K16:** Modül dışı katalog planları için (a) modüle uyarlama ya da (b) serbest aks. 23 Eylül önerisi: bayi planlarında (b).
- **K3 ve K4:** Güncel Şablon 2024 blok adlarına geçiş; kapı genişlikleri.
- **Z-03 ve Z-06 eşikleri:** %98 ve günde 50 talep öneridir.
- **Anahtar yenileme (K17):** 27 Eylülde yeniden ertelendi; bayilere açılmadan önce şart.
