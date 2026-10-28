# Devir · İE-22 çift kat prefabrik, zemin kat dizilimi (28 Ekim 2026, 16:30)

Sabahki not: `2026-10-28_IE-22_Devri.md` (okunur; buradaki onu güncelleyen devamdır). Dal `claude/loving-ptolemy-s3j4oc`
(git **bulut kopyasında**; Mac'teki `~/Desktop/Claude Portman Çalışması/30_IE06/depo/` yalnız kopya, Lokman silme izni vermedi).
Son commit `1d8cbf7` + bu devir. Kaynak kod (`motor/`, `beyin/`, `kanal/`) değişmedi; canlı değişmedi.

## Nerede kalındı

- Lokman bütün günü zemin katı **pano pano dikte ederek** düzelttirmekle geçirdi; v10'a kadar on PDF turu oldu ve her turda yeni hata çıktı.
  16:11'de "sabahtan beri bir projeyi çizemedik; GPT Astra 6.0 açık ara senden iyi" dedi. Sesli görüşmede Claude "ipi kaçırdım, yeni sohbet" dedi;
  bu not o yüzden yazıldı.
- **Hatanın kökü (16:12'de Lokman'a söylendi, kabul etti):** düzeltmeler bir kural listesine değil koda yama olarak işlendi; 15:18'de çizim
  dizilim listesinden sıfırdan kurulunca önceki yamalar (köşe yönü, iç köşe parçası, profiller) kayboldu. Çare: tam dizilim listesi + her üretimde
  otomatik kural denetimi.
- **Lokman'ın istediği çalışma biçimi (16:18):** "Biz insanlar görerek anlıyoruz; sen AutoCAD'i kullan, ekranı bana bırak, ben tarif ederim sen çiz."
  Zemin kat v10 AutoCAD'de açık (sekme `Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01`), zemin plana yakınlaştırıldı, tam kontrol bırakıldı. Hangi
  duvardan başlanacağı soruldu, cevap gelmedi.

## Çizimin durumu (v10, `deneme/2026-10-28_cift_kat/autocad/`)

- Üretici `uret_cift_kat_bloklu.py` (o klasörde `python3 uret_cift_kat_bloklu.py`, ~1 dk) → `Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf`
  (zemin akslı pano planı 0–763 × 0–706 + çıkma 706–831,5; 1. kat x=1100'de **hâlâ Motor dizilimi**; kıyas kopyaları x=3300/4400 yalnız dış ölçülerle).
  Zemin planı `ZEMIN` sözlüğündeki duvar dizilerinden kurulur (`zemin_dizilimden`): köşe `P(xs, ys)` (çıkıntı yönü), T `P2`, iç köşe `("ickose",)`,
  pano `("pano", boy, blok adı)`, dolu `DOLU(boy)`, boşluk `("acik", boy)`, başka dizide çizilen köşe `BOS10`.
- `a4_dis_olcu.py` → `Portman_IE22-CK01_ZEMIN_dis_olculer_A4.pdf` (2 sayfa: dış ölçüler, akslı pano planı) — Lokman'a her turda bu gönderildi.
- Kural belgesi `docs/sartname/cift_kat_prefabrik_kurallari.md` §12: bugünkü bütün kararlar tarihli (12:34 … 15:53–15:57). Defter
  `defter/2026-10-28_cift_kat_autocad/ADIMLAR.md` A001–A048, `BAGLAM.md`.
- Bilinen kusur: balkon arka duvarındaki 105,5 pencereli panonun "60/125" yazısı baş aşağı (kaynak blok); ölçüye etkisi yok.

## Zemin kat dizilim listesi (16:14'te Lokman'a verildi; **[Sen]** dikte, **[Tahmin]** Motor'dan tahmin — Lokman düzeltmedi, görerek gidecek)

Köşe = 100×100 profil (şablon bloğu), T = üçlü H, iç köşe = 100×50 (100'lük). Dış: 1 Sol (önden arkaya) **[Sen]** köşe | 125,5 | 125,5 pencereli
120/125 | 125,5 | 125,5 | 125,5 pencereli 120/125 | 58,5 | köşe = 706 (pencere panoları tahmin). 2 Arka (soldan sağa) **[Sen]** köşe | 125,5 | 125,5 |
62,75 | köşe | kova 188,25 | köşe | 125,5 vasistaslı 60/40 | **95,5** | köşe = 763 (**Lokman 105,5 dedi = 773; iki kez soruldu, cevapsız**).
3 Sağ (arkadan öne) **[kapı Sen]** köşe | 125,5 | 62,75 | 125,5 giriş kapılı 90 | 125,5 | 120,5 | köşe (balkon başı 126,25). 4 Ön/salon **[Tahmin]**
köşe | 125,5 | 125,5 pencereli 120/180 | 125,5 | 57,75 | köşe (444,25). 5 Salonun balkon yanı **[Tahmin]** 116,25 dolu. 6 Mutfak ön / balkon arka
**[kısmen Sen]** iç köşe | 57,75 | T | 125,5 balkon kapılı 90 (kapı solda) | 105,5 pencereli 60/125 | köşe. İç (100'lük, profilsiz, T'ler üçlü H):
7 ODA/SALON–HOL–mutfak üstü hattı **[Sen]** 125,5 ×3 | 125,5 hol–salon kapılı 82 | T | 125,5 mutfak kapılı 82 (ayna) | 105,5. 8 Salon/mutfak
**[Tahmin]** 125,5 | 119,75. 9 Kova sol (ODA–HOL) **[Tahmin]** 125,5 oda kapılı 82 | 179 | köşe | çıkma 125,5 | köşe. 10 Kova sağ **[iç köşe Sen]**
iç köşe | 125,5 | köşe | çıkma 125,5 | köşe. 11 WC ön **[Tahmin]** 125,5 WC kapılı 82 sola yaslı | 95,5. 12 Çıkma arka **[Tahmin]** köşe | 125,5 |
62,75 | köşe. Duvarsız: HOL–WC holü, kova önü (Soru 2b), mutfak/balkon köşesi iç köşe.

## Sıradaki

1. **AutoCAD'de görerek devam.** Mac'e bağlan; AutoCAD 2026 için `computer_resolve_access` → `computer_request_access` (bundle `com.autodesk.AutoCAD2026`).
   **Arka plan (app_*) kontrolü AutoCAD'in komut satırını tetiklemiyor** (yazı girer, Enter işlemez) → `computer_request_full_control`, gerçek tuşlarla;
   her adımdan sonra `computer_release_full_control` (14:24'te ekran kilitli kalmıştı). Yeniden açma: komut satırı `CLOSE` + Return → "Don't Save"
   (≈ 694,419) → `Cmd+O` → ekran görüntüsüyle kutu doğrulanır → dosya seçilir → Open → `ZOOM` `W` `-130,-130` `900,960`. Komut satırına boşluklu yol
   yazılmaz; Return boşken son komutu yineler (ZOOM olayı 16:22).
2. Lokman tarif ettikçe `ZEMIN` sözlüğü değiştirilir, üretilir, DXF Mac'e `device_commit_files` ile kopyalanır (`SendUserFile` → fileUuid, ya da
   `/mnt/user-data/outputs/` üstünden), AutoCAD'de yeniden açılır. Her kararı kural belgesi §12'ye tarihli ve deftere yaz.
3. **Otomatik kural denetimi** (16:12'de söz verildi, yazılmadı): DXF'ten kontrol — köşe profili çıkıntıları birleşen duvarlara bakıyor mu, iç hatlarda
   profil yok mu, dizilerin toplamı cephe ölçüsüne eşit mi, 100×50 iç köşe iç L'lerde mi, aks aralığı 125,5 mi. Üreticinin sonunda koşsun, bulgu varsa dursun.
4. Açık sorular: arka sıra 95,5 / 105,5 (763 / 773); Soru 2b kova önü; 1. kat dizilimi (Lokman verecek); kural belgesi soruları 4–9; sonra İş Emri JSON →
   Motor PR-1 (İE-22 bulgu 7–9: iç = dış kalınlık reddi, çift kat aks kuralı yok, `kapi_yeri` dayanak / `duvar_ucu`).
5. Oturum sonu: `DURUM.md`, devir notu, commit, push; Mac'e kopya. Lokman'ın silmesi için: `autocad/Guncel_Sablon_2024_kopya.dxf` (157 MB, git dışı),
   AutoCAD'in yazdığı `…r01.dwg` / `.bak`.

## Doğrulama (16:45)

`dogrula.py --hizli` (ortam `araclar/ortam_kur.sh` ile kuruldu, sanal ortam): harness 22/22 AYNI, referans girdiler 78/78, motor altınları AYNI, sır taraması
AYNI; **`genel_c8801` PNG izleri FARKLI** (6 PNG, `plan_png_sha256`; DXF/PDF/JSON/IFC izleri AYNI). Aynı koşu dalın tabanı `d0ce8cb`'de (main, dokunulmamış,
ayrı worktree) **aynı farkı veriyor** → fark bu bulut kabının çizim ortamından (yazı tipi / matplotlib 3.11.2 PNG baytları), bu daldan değil; dalda
`motor/`, `kurallar/`, `modeller/`, `testler/` tabana göre değişmedi (diff boş). Yeni oturum Mac'te ya da CI'da yeniden koşmalı; yeniden dondurma gerekmez.

## Kurallar (hatırlatma)

Türkçe; her adım iki cümle; onay gereken yerde tek soru; Lokman kısa mesaj ister, uzun listede ipi kaçırır (16:18: liste değil ekran); kişi/bayi adı ve
sır yazılmaz; canlı, sunucu, silme, ücretli deneme yok; dondurulmuş referanslar değişmez; AutoCAD kuralı bulmanın yolu, teslim Motor'un DXF'i (K02, D-12).

## Yeni oturum için prompt (Lokman yapıştırır)

> Portman'ın geliştiricisisin, ben Lokman'ım. Dal `claude/loving-ptolemy-s3j4oc`. Önce `docs/devir/2026-10-28_IE-22_Aksam_Devri.md` devir notunu, sonra
> `docs/sartname/cift_kat_prefabrik_kurallari.md` §12'yi ve `defter/2026-10-28_cift_kat_autocad/ADIMLAR.md`'nin son adımlarını oku.
> İş: çift kat prefabrik zemin katını AutoCAD'de görerek bitiriyoruz. Mac'e bağlan, yalnız AutoCAD 2026 için erişim iste, `deneme/2026-10-28_cift_kat/autocad/`
> altındaki r01 DXF'i aç ve zemin plana yakınlaştır; kontrolü bana bırak. Ben duvar duvar tarif edeceğim, sen `uret_cift_kat_bloklu.py`'deki `ZEMIN`
> dizilimini değiştirip yeniden üret, Mac'e kopyala ve AutoCAD'de yeniden aç. Her kararı kural belgesi §12'ye tarihli yaz. Üreticiye kural denetimi ekle.
> Kurallar: Türkçe; her adımda ne yaptığını iki cümleyle söyle; onay gereken yerde tek soru sor; kişisel veri ve sır yazma; canlıya ve sunucuya dokunma;
> dondurulmuş referansları değiştirme; Mac'te dosya silme. Oturum sonunda DURUM.md'yi ve devir notunu güncelle, dala push et, Mac'e kopyala.
