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
| [K06](K06.md) | Kanal v1 hosting'de: PHP imzalı webhook yakalar → kuyruk → Python cron üretir → PHP gönderir (21.09) · **D-05 ile kapandı (9.10): kanal VPS'te, Python; PHP kalktı** |
| [K07](K07.md) | Patron modu + önce kuru çalışma, sonra gerçek gönderim; kill switch'ler (21.09) |
| [K08](K08.md) | Görev 2 Python cron'u silindi (21.09) |
| [K09](K09.md) | Kalıcı ilkeler (21.09, Lokman): öz-test asla WhatsApp'a göndermez; sunucu değişikliği yalnız yetkiyle, yedek + geri alma ile; sırlar koda/sohbete/rapora/günlüğe yazılmaz; numaralar maskelenir |
| [K10](K10.md) | Beyin çıkarım arka ucu: OpenAI Chat Completions, gpt-4o-mini, anahtar panelin `ayarlar.json`'undan yalnız okunur (21.09) · **29.09'dan beri canlıda Claude Opus 5.5** (Portman ve bayi botu) |
| [K11](K11.md) | VPS: Natro XCloud Pro, aylık 29,99 $ (22.09) |
| [K12](K12.md) | Hibrit mimari: hosting = kontrol düzlemi (Meta webhook, kuyruk, gönderim, WhatsApp anahtarı, görüşme durumu); VPS = üretici; ajan yalnız dışarıdan bağlanır (22.09) · **D-05 ile kapandı (9.10): tek sunucu, dışa açık 443** |
| [K13](K13.md) | Eşleşme anahtarı modeli: VPS'te üretilen 64-hex anahtar, hosting'te `api_token.txt`; `hash_equals`; OpenAI anahtarı hosting'ten HTTPS ile ajana gider, VPS diskine yazılmaz (22.09) · **D-05 ile kapandı (9.10): eşleşme anahtarı yok; anahtarlar VPS'te root 0600 dosyalarda, hepsi yeni** |
| [K14](K14.md) | Paket dağıtımı hosting kanalıyla (`kanal/package/current.zip` sha değişince ajan kendini günceller, öz-test koşar); komut kanalı (`vps_komut`) kapalı başlar (22.09) · **D-05 ile kapandı (9.10): salt okunur dağıtım anahtarı ve onaylı etiket (`guncelle.sh`); komut kanalı kodu silindi** |
| [K15](K15.md) | Tek depo: GitHub `lokmansayim/portman` (özel); kod, kural sürümü, şema, testler, KARARLAR.md (22.09) |
| [K16](K16.md) | Katalog planları çıkarıcıyla okunur, elle kodlanmaz; artıklar raporlanır, sessiz yuvarlama yok (22.09) · **Açık (a/b) kararı D-08 ile kapandı (12.10): modül dışı ve çelik planlar serbest aksla genel motorda** |
| [K17](K17.md) | Sızan eşleşme anahtarı yenilenecek: `rm /etc/portman/agent.env` + bootstrap tekrar + yeni anahtar `api_token.txt`'e (22.09, **uygulanmadı**) · **28.09'da kapı C'de başka yoldan uygulandı** (eşleşme ve OpenAI anahtarı yenilendi, eskileri 401; bkz. K17 › Uygulanış) |
| [K18](K18.md) | Beyin kuralı (22.09, iki adım): odada tek pencere varken "penceresi 120x180" ölçü değişikliğidir; ölçüt **bayinin kendi mesajı**, LLM özeti değil |
| [K19](K19.md) | NumPy < 2 sabitlemesi (VPS) (22.09) · **10.10'da yeni sunucuda yeniden doğrulandı:** sunucu paketleri `vps/gereksinimler.txt` ile tam sabit (numpy 1.26.4); işlemci x86-64-v2 sunana kadar numpy 1.x (K19 › Uygulanış) · **12.10 (BK-07, Lokman 11.10):** işlemci "host" oldu, koşul oluştu; numpy 2.x ve güncel paketler, tam sabit; `guncelle.sh` numpy hesabı güvenlik ağı (K19 › Uygulanış 2) |
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
| [Z-05](Z-05.md) | Birincil model Claude Opus 5.5, model geçidi arkasında (29.09'dan beri canlıda) | Başka bir model (açık ya da yerel dahil) PortmanBench'te aynı skoru daha ucuza alırsa |
| [Z-06](Z-06.md) | Tek sunucu, GPU yok | Ölçülen render süresi ya da kuyruk beklemesi işi tıkarsa ya da günlük talep 50'yi geçerse |
| [Z-07](Z-07.md) | BIM çıktısı IFC4 (açık ISO standardı) | Bir araç ya da müşteri başka bir IFC sürümü gerektirirse |
| [Z-08](Z-08.md) | Kişisel veri sunucuda, LLM'e takma adla · **D-06 ile daraltıldı (11.10): bayi adı ve hitabı istisna** | Hukuki görüş başka bir şey söylerse |
| [Z-09](Z-09.md) | Ayda bir alan taraması: BenchCAD, Text2CAD-Bench, plan üretimi, IFC ve görsel modeller; her ayın 1'inde planlı görev | Süreç kararı; bir varsayımı bozan gelişme ilgili kararı açar |
| [Z-10](Z-10.md) | Çift doğrulama: her teklif iki bağımsız yöntemle hesaplanır, modelden kesin metraj (IFC) ve CTKBF mantığıyla parametrik tahmin (Python); kalem grubu eşik dışındaysa ön onay durur, mühendis inceler | İki yöntem gerçek yükleme listelerinde aynı hatayı paylaşırsa; eşikler PortmanBench ile ayarlanır |

## D-01 ve sonrası · Bu depoda alınan kararlar

| No | Karar | Tarih |
|---|---|---|
| [D-01](D-01.md) | B2: taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar (yeni talep mi, değişiklik mi) | 28.09 |
| [D-02](D-02.md) | Referans PDF'in içeriğini de izler (bütün çizimler, sabit üretim zamanı); yeniden dondurma bir karara dayanır | 28.09 |
| [D-03](D-03.md) | Kalıcı akışta yarım kalan iş, ilk deneme dâhil en çok üç kez alınır; yalnız geçici teknik hatada (süreç düştü, kira doldu). Gönderim ve kayıtlı sonuç üreten durumlar tekrarlanmaz | 28.09 |
| [D-04](D-04.md) | Postgres mevcut VPS'te; konuşma ve iş durumunun asıl kaydı Postgres; tek etkin işleyici `settings.worker` ile (K12'nin görüşme durumu bölümünü değiştirir) · D-05 ile hosting tarafı ve `settings.worker` kalktı; "Postgres asıl kayıt" kalır | 28.09 |
| [D-05](D-05.md) | Kanal tek sunucuda (VPS): hosting'ten taşınma, sıfırdan kurulum, boş veritabanı, bütün sırlar yeni, dışa açık yalnız 443, sürüm düzeni (`guncelle.sh`/`geri_don.sh`) ve yalnız ekleyen göçler, şifreli dış yedek (age + Drive), iki uyarı yolu, hosting'te yalnız web sitesi; K06, K12, K13, K14 kapandı | 09.10 |
| [D-06](D-06.md) | Bayi adı ve hitabı bayiye giden mesajlarda kullanılır ve LLM'e gönderilebilir (Z-08'in bu iki alan için gevşetilmesi; numara ve öteki alanlar için Z-08 aynen). İE-07'de yalnız şablon hitabı; LLM bağlamı sonraki iş | 07/10.10, kayıt 11.10 |
| [D-07](D-07.md) | Katalogda doğru kaynak doğrulanmış çizimdir; katalog PDF'i yalnız fikir kaynağı; her model kaydında kaynak ve doğrulama durumu yazar; dondurulmuş `katalog_37_proje.json` değişmez, düzeltme yeni sürüm dosyasıyla (D-02'ye uygun) | 11.10 |
| [D-08](D-08.md) | K16 = (b): çelik ve modül dışı planlar serbest aksla genel motorda (`motor/genel/`, ana kodda); P6001 ve prefabrik katalog pano birimli Motor'da (K02); kural kitabı ve modeller sürümle dosya olarak; perspektif VTK ekransız; yedi aday (Ç8201, Ç8801, Ç8801-K/L, KT-01/02/03), KT'ler bayiye adsız; K-A1 ±%10 brüt oturum; bayi paftası "Örnek Şablon"; genel motor çıktıları altın test, referans bu kararla yeniden donduruldu (D-02); K16 kapandı | 11.10 (Lokman), kayıt 12.10 |
| [D-09](D-09.md) | Bayi paftasının antetinde bayinin adı ve bayi kartındaki telefonu yazılır (D-06'nın genişletilmesi); başka kimsenin numarası yazılmaz; LLM'e gitmez (Z-08), günlükte maskeli (K09); PR-2'de yalnız o bayinin kartındaki numara kabul edilir | 12.10 14:53 |
| [D-10](D-10.md) | Bayi paftasının 1. sayfasında 8b mühendis kabulüne kadar antet üstünde "TASLAK" (`pafta_sablonu.json › taslak_ibaresi`); 15 cm kuralı: "Çelikte 15 cm parça çıkmaz", kısa parça komşusuna katılır ve mühendise kontrol notu düşer (`pafta_ozet.json › kontrol_notlari`); yedi aday `gecerli` kayıtta, bayiye sunulma mühendisin K-A10 kabulüyle; KT-01 etiket yeri ve baca derinliği; `bayi_gorsel.png` (plan + çatı planı + iki perspektif); referans bu kararla yeniden donduruldu | 12.10 akşam |
| [D-11](D-11.md) | Geliştirme döneminde çelik adayların bayiye sunulma kabulünü (K-A10) Lokman verir (kabul kaydında kim = Lokman, dayanak D-11; metinlerde "kabul eden"); 8b mühendis teknik kontrolü aynen; genel motor düzenlenebilir DXF üretir (plan + dört görünüş, katmanlı, cm), yükleme listesi Excel'i yalnız kabul paketinde (openpyxl sunucuda yok); DXF ve Excel çıktıdır, kaynak değil: düzeltme tanıma (D-07) ya da kural kitabına işlenir, yeniden üretilir | 13.10 sabah |
| [D-12](D-12.md) | Prefabrik hattı: çelikten ayrı pano motoru (125,5 aks; genişletilecek olan bu), standart duvar 100 / 60 mm (160 / 100 yalnız müşteri seçeneği), P6001 gerileme çapasıdır doğruluk kanıtı değil (bilinen hata: veranda ve salon penceresi; doğru kaynakla yeni dosyada yeniden çizilir), referanslar gerçek yükleme listeli projelerden kör testle, Astra R02 referans model değil | 12.10 22:49 / 23:10 |
| [D-14](D-14.md) | Prefabrik pano yüksekliği yalnız 250 / 280 / 300 cm (%80 / %19 / %1); Motor başka değeri reddeder (K21); 250 dışı yükseklik yeni kod yolundan (pano kodu 2800/3000, lento h − 200 çıkarımı), 250'lik çıktılar bayt bayt aynı; doğrulama kuralını değiştirmez | 13.10 07:28 |
| [D-15](D-15.md) | Prefabrikte kapı ve pencere yerleşimi mantıkla: pencere odaya ortalı (ızgara ≤ ¼ pano kaçıyorsa kalır), oda kapıları bölmeye yaslı ve kanatları birbirine doğru, menteşe dayanaklı uçta; PK-01 paftasıyla ölçülü; LLM değil kod | 13.10 08:53 |
| [D-16](D-16.md) | BK-09 çizim düzeltmeleri: kapı yayını kesen mahal etiketi oda içinde kaydırılır; pafta 2. sayfada TASLAK ayrı yazı; KT başlığında ve liste adında m² koddan (brüt oturum, model dosyası aynen); G1 ölçü zinciri eşiği `max(12,5; dış kaplama + en kalın dış duvar + 1)`; çentiğe değen dar sayı zincirin dış yanında; yazı denetimi kapı yayı ve sayfa dışı; referans `2026-10-14` bu kararla yeniden donduruldu | 14.10 (Lokman, BK-09 planı) |
| [D-17](D-17.md) | Yükleme listesi Excel'i her çelik çizimde sunucuda üretilir (`kanal/worker.liste_exceli`, `uret` dışında; altın değişmez), bayi onaylayınca mühendise gider, bayiye gitmez; `openpyxl` + `et-xmlfile` sunucu listesinde; D-11'in "yalnız kabul paketinde" maddesi değişti | 14.10 (Lokman, Görev 4b ve 8b planı) |

## Numara defteri (14 Ekim 2026, BK-08; CIO planı › Görev 3)

Karar (D) ve iş emri (İE, BK) numaraları dallar arasında çakışmasın diye burada ayrılır. `/is-emri` yalnız o dalın `docs/is_emirleri/` klasörüne bakar; yeni numara almadan önce bu tabloya bakılır, alınan numara aynı commit'te buraya yazılır.

| Seri | Numara | Sahibi | Durum |
|---|---|---|---|
| D | D-01–D-11 | bu depo (`main`); D-10 ve D-11 İE-08'in | yazıldı |
| D | D-12, D-14, D-15 | prefabrik hattının kararları (dallarda D-10, D-12, D-13 adıyla yazılmıştı): ayrı pano motoru (100 / 60, P6001 çapa), pano yüksekliği 250 / 280 / 300, kapı ve pencere yerleşimi | yazıldı (BK-12 PR-1; `bk-12-prefabrik-main`) |
| D | D-13 | kişisel veri esnetme (dalda D-11; Lokman 12.10 23:10) | ayrıldı (BK-12 PR-K, Patron onayıyla; AGENTS.md ve `kvkk-denetcisi` ile birlikte) |
| D | D-16 | BK-09 PR-2: çizim düzeltmeleri (KT-02 kapı yayı, 2. sayfa TASLAK, KT başlığında m², G1) ve referansın yeniden dondurulması | yazıldı (14.10) |
| D | D-17 | İE-08 8b: yükleme listesi Excel'i sunucuda üretilir ve mühendise gider (D-11'in "yalnız kabul paketinde" maddesini değiştirir) | yazıldı (14.10; `ie-08-8b-muhendis`) |
| D | D-18 | İE-14: yeni üretilen çelik plan bayiye TASLAK gider; plan üretimi ve revizyon için ek LLM çağrısı (K05 istisnası) | yazıldı (14.10; `ie-14-talepten-plana`) |
| D | D-19 | 24 saat kapanış kuralı (BK-10; Patron, 14.10 23:56); ayrıntısı (zaman aşımı, Patron'a tek bildirim) CIO yorumu ve Patron teyidini bekliyor | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 15); `KARARLAR/`'da dosyası yok |
| D | D-20 | İE-09 model atölyesi (Görev 6e, 16.10); defterde ayrı karar metni yok | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda; `KARARLAR/`'da dosyası yok |
| D | D-21 | atölye sırası "AIPrefabrik + mühendis" (17.10 07:00, kart); D-22 değiştirdi | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 97); `KARARLAR/`'da dosyası yok |
| D | D-22 | atölye sırası "Önce mühendis" (17.10 08:01, kart; D-21'i değiştirir); D-23 değiştirdi | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 98); `KARARLAR/`'da dosyası yok |
| D | D-23 | atölye prefabrikle başlar, yol "Önce motor" (17.10 09:30 ve kart 09:39; D-22'yi değiştirir); uygulaması BK-12 | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 99); `KARARLAR/`'da dosyası yok |
| D | D-24 | kimlik kartı işi PK-01 ile başlar (19.10 04:04, kart; PR #28 birleşince, BK-12 PR-3'ü beklemez); İE-15'in sırası | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 102); `KARARLAR/`'da dosyası yok |
| D | D-25 | çelik hattı prefabrikle yan yana başlar (25.10 08:42 ve 08:43; "çakışma ve bozulma olmayacak ise"); uygulaması İE-16 | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 106); `KARARLAR/`'da dosyası yok |
| D | D-26 | pilot kapsamı: tek katlı prefabrik ve tek katlı çelik ikisi birden kesin çalışır; dubleks ve çift kat canlıdan sonra (25.10 08:58) | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 107); `KARARLAR/`'da dosyası yok |
| D | D-27 | canlıya geçiş şartı: başlangıçta kurulan rehberdeki her şey çalışır duruma gelir, sonra canlı (pilot); teklif ve fiyat dahil (25.10 09:09); "rehber"in "Portman Bayi Rehberi ve Süreç Taslağı" (6 Ekim) olduğu CIO çıkarımı, Patron teyidini bekliyor | kaydı CIO'nun Notion defterinde ve Kurulum Panosu'nda (satır 109); `KARARLAR/`'da dosyası yok |
| D | **D-28** | — | **sıradaki boş** |
| İE | İE-01–İE-08 | bu depo (`main`) | yazıldı |
| İE | İE-09 | model bankası ve yeni model üretimi; P6001 güncellemesi | ayrıldı (pilottan sonra) |
| İE | İE-10, İE-11, İE-12 | prefabrik hattı (PR #12, PR #14, `ie-12-prefabrik-bayi-paftasi`) | `main`'e BK-12 ile (PR-1: motor ve bayi paftası; liste ve mühür kıyası sonraki PR'larda) |
| İE | İE-13 | onaydan teklife: fiyat, Patron onayı, özellik formu, hitap (eski adıyla İE-10) | ayrıldı (pilottan sonra) |
| İE | — | `ie-11-pr2-kor-test` dalındaki onaysız İE-13 / İE-14 taslak planları | numarasız; planlanınca bu defterden numara alır |
| İE | İE-14 | talepten plana (14a: tek kat çelik; LLM-önce üretim ve revizyon) | alındı (14.10; `ie-14-talepten-plana`) |
| İE | İE-15 | kimlik kartlı model: yerleşim planları ve adetler aynı modelden (D-24; KH-1, K1, KH-2, K2, KH-3, K3; eski `ie-11-pr2-kor-test` dalındaki "İE-15 · LLM'li katman" o dal birleşmeden önce yeni numara alır) | alındı (19.10; `claude/project-thread-far6rz`) |
| İE | İE-16 | çelik hattı: çelik projeleri ve çelik çizim kuralları (D-25; PR-1 hakem ve mühür, PR-2 hedef örnek, PR-3 çizim kuralları, PR-4 kör ölçüm) | alındı (25.10; `claude/project-thread-1ff0ou`) |
| İE | İE-17 | prefabrik evlerin çatısı ve dört görünüşü (28 ev çizim yol haritasının 1. adımı; PR-1 çapraz cumba ve kırma, PR-2 paralel cumba) | alındı (27.10; CIO ayırdı; `claude/project-thread-wwx1p0`) |
| İE | İE-18, İE-19 | montaj rehberleri, altın set (CIO'nun Notion defteri; başka dallarda) | alındı (27.10) |
| İE | İE-20 | görsel ve PDF ile talep, talep ve revizyon formu (WhatsApp Flow); pano satır 83, 110, 61 | alındı (27.10; `claude/project-thread-l5mh7r`) |
| İE | **İE-21** | — | **sıradaki boş** |
| BK | BK-01–BK-08 | bu depo; BK-08 8a sonrası temizlik (`bk-08-8a-temizlik`) | yazıldı |
| BK | BK-09 | metin ve çizim düzeltmeleri, G1 (`bk-09-metin-cizim`, `bk-09-cizim-g1`) | alındı (14.10) |
| BK | BK-10 | 8b sonrası düzeltmeler (DXF `.txt` notu, geç gelen Excel, Patron'a Excel bağlantısı, çelikte kapı değişikliği; `docs/devir/2026-10-14_IE-08_8b_Devri.md` › Sıradaki; CIO'nun Notion defterinde D-19 ile: 24 saat kapanış kuralı) | ayrıldı |
| BK | BK-11 | `ortam_kur.sh` Postgres'i kurtarma bitene kadar dener (`bk-11-postgres-bekleme`) | alındı (16.10) |
| BK | BK-12 | prefabrik hattını `main`'e alma (D-23; `bk-12-prefabrik-main`; PR-1, PR-R, PR-K, PR-2, PR-3, PR-4) | alındı (17.10) |
| BK | BK-13 | Pano Motor'unun pencere kataloğu (`bk-13-pencere-katalogu`; T76 ve açık evlerin ölçüleri, eşik, panodan geniş pencere) | alındı (23.10) |
| BK | **BK-14** | — | **sıradaki boş** |

## 27 Eylülde Lokman'ın verdiği kararlar

1. **Sunucu:** Elindeki Natro VPS ile başlanıyor; kurulum taşınabilir (K11 ile aynı yönde).
2. **Eski kod:** Yeni repo açılıyor; önce çalışan sürüm (v1.1.1) ve referans çıktıları kayda alınıyor, sonra testi geçen parçalar taşınıyor. Bu depo o kararın uygulamasıdır (İE-01).
3. **Hafıza:** Sıfırlanmıyor; projenin doğrusu repoya ve veritabanına taşınıyor.
4. **Alan taraması:** Her ayın 1'inde planlı görev (Z-09).
5. **Çift doğrulama:** İlke olarak kabul edildi (Z-10).

## Açık kararlar (sahibi Lokman)

- ~~**K16:** Modül dışı katalog planları için (a) modüle uyarlama ya da (b) serbest aks. 23 Eylül önerisi: bayi planlarında (b).~~ **Kapandı:** Lokman 11.10 15:01, (b): çelik ve modül dışı planlar serbest aksla genel motorda; P6001 ve prefabrik katalog pano birimli Motor'da (D-08, İE-08).
- **K3 ve K4:** Güncel Şablon 2024 blok adlarına geçiş; kapı genişlikleri.
- **Z-03 ve Z-06 eşikleri:** %98 ve günde 50 talep öneridir.
- ~~**Anahtar yenileme (K17):** 27 Eylülde yeniden ertelendi; bayilere açılmadan önce şart.~~ **Kapandı:** 28.09'da kapı C'de yapıldı (K17 › Uygulanış; 4 Ekim'de işaretlendi, BK-03). Claude anahtarının 29.10.2026 son kullanma tarihi ayrı bir risktir (`DURUM.md`).
