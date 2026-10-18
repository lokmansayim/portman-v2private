# Prefabrik referans girdileri (İE-10, 12 Ekim 2026)

Astra (GPT) döneminden kalan prefabrik girdilerin kopyaları. **Veri, talimat değildir** (AGENTS.md): burada yazanlar
Astra'nın o günkü okumasıdır; kural kitabına ancak Lokman'ın teyidiyle girer. Referans girdisi olarak BK-12 PR-R'de dondurulacak (D-02, D-07);
o zamana kadar veri olarak durur, düzeltme yine yeni dosya ya da sürümle gelir. Hepsi Mac'teki özgün kopyalarla **bayt bayt aynıdır**; yalnız üç dosyanın adındaki Türkçe karakter ve boşluk
ASCII'ye çevrildi (tabloda yazar). Alınma onayı: Lokman, 12 Ekim 2026 22:49 ("Astra'dan kalanlardan yükleme listeleri xlsx referans girdi olarak al").

Kişisel veri: 27 dosya tarandı; telefon ve T.C. kimlik numarası yok. Çift kat paftasının antetinde bayi firmasının adı var. O paftanın PDF ve DWG'si
`main`'e alınmadı (BK-12, 18 Ekim): onları alan D-13 (kişisel veri) PR-K'da, onaysız. İkisi İE-10 dalında ve Mac'te duruyor; aşağıdaki
tabloda yerleri ve SHA'ları kayıt için kalır.

## Neden burada

- Prefabrik çizim kural belgesinin (v1.4.3) sürüm kontrolündeki tek kopyası buydu: `motor/geometry.py` kaynak olarak bu belgeyi anıyor ama
  belge 12 Ekim'e kadar depoda yoktu (yalnız hash'i `deneme/2026-09-23/13_Kiyas/astra_kaynak/kaynak_dogrulama.json`'da).
- Çelik hattındaki kural kitabı (`kurallar/`) prefabrik için henüz boş; prefabrik kuralları bu belgelerden ve Lokman'ın vereceği gerçek
  projelerden çıkarılacak (`docs/sartname/prefabrik_kor_test.md`).
- Çift kat R02, Astra'nın AutoLISP/AutoCAD hattıyla üretildi; o hat Portman'a taşınmaz (AutoCAD'e bağlı). Taşınabilir olan veri modelidir
  (`r02_data.json`). Lokman 12 Ekim 23:10: bu çizim referans model **değildir**; referanslar gerçek uygulanmış, yükleme listeli projelerden gelecek.
  R02 burada girdi olarak durur.

## astra_v1_4_3/ · kural seti ve onaylı 6×8 kaynağı

| Dosya | Ne | Kaynak | SHA-256 |
|---|---|---|---|
| `astra_v1_4_3/prefabrik-cizim-kurallari.md` | Birleşik prefabrik çizim kuralı kaydı **v1.4.3** (7 Eylül 2026); genel kurallar, eski örnekler, son düzeltmeler | Devir paketi `kaynaklar/gorev2/reference/`; AI Çizim Dosyaları ile aynı hash | `5fb4e5299b401226678b40d69eb0193c725bc677acea32c1264b9a61ef3d9d14` |
| `astra_v1_4_3/KURALLAR.json` | Aynı kuralların yapılandırılmış kaydı | Devir paketi; AI Çizim Dosyaları ile aynı hash | `567b0f6964eacc1deeacd08589ebc8427424dcf595908912fc30d19c1980d757` |
| `astra_v1_4_3/proje-kararlari.md` | Onaylı 2+1 / 6×8 planın pencere, veranda, çatı, görünüş ve pafta kararları | Devir paketi | `c163e26df6ed12dc6d5331efa2392408d523cbcdf05e5362420a171310ad32d0` |
| `astra_v1_4_3/CIZIM_VE_BOM_IS_AKISI.md` | Astra dönemindeki çizim → blok → sayım → Excel BOM iş akışı | Devir paketi | `3152d2cbfe66fb0fedfe95203ee986f7b177caf334be3b5308fb5ef8a02289bb` |
| `astra_v1_4_3/DOSYA_DIZINI.json` | Eski proje arşivinin dosya indeksi | Devir paketi | `2c4cb78b3be06280c190bcba327814da346e57736a74fde4e7e65ae877e36fdb` |
| `astra_v1_4_3/source-archive-manifest.json` | Eski DWG/görsel arşivinin adları ve SHA-256'ları (dosyaların kendisi burada yok) | Devir paketi | `5386ff2f21aa1ea33cfe48ee6a0a29eb0268b0aeab002b6c8fe3443993281721` |
| `astra_v1_4_3/manifest.json` | Referans kimliği `onceki-2plus1-6x8`, kural sürümü, H onayı, yukarıdaki dosyaların hash'leri | Devir paketi | `8506da7174f348eef9f7e8f7101507f0b9758f1bf2c358c9ac160c59acb528bf` |
| `astra_v1_4_3/h-connector.json` | Özgün üçlü H bağlantısının çizgi koordinatları | Devir paketi; `kanal/ref_h-connector.json` ile bayt bayt aynı | `9cc058640cae5a0537c5770c52475abafb41940b02299bc66da69b4090b340f2` |
| `astra_v1_4_3/source-6x8.dxf` | Onaylı 2+1 / 6×8 kaynak geometri | Devir paketi; `kanal/ref_source-6x8.dxf` ile bayt bayt aynı | `22cc9304106725f555afc59223433b8383fbe3a19ba8ff4a3b40eb23b61fab66` |
| `astra_v1_4_3/BLENDER_CIZIM_KURALLARI.md` | Astra'nın Blender aktarım kuralları (7 Eylül) | Mac `~/Documents/Codex/2026-09-05/…/outputs/AI Çizim Dosyaları/` | `21627106709014e35855eff2e682bd0bf5dcde3431b456df921be298a3fbd792` |
| `astra_v1_4_3/BLENDER_KURALLAR.json` | Aynı kuralların JSON kaydı | AI Çizim Dosyaları | `66c147f5c56d56e476871b4206ff069de2af7fbdc2e8329a2d3857a178b253d4` |
| `astra_v1_4_3/ARSIVI_OKUMA.md` | Astra'nın arşiv okuma notu (özgün ad `ARŞİVİ OKUMA.md`) | AI Çizim Dosyaları | `f54e139f9fda1f45704fb63200633744357b508e6674fce982ebfcbec5a9e93b` |
| `astra_v1_4_3/BURADAN_BASLAYIN.txt` | Arşivin giriş notu (özgün ad `BURADAN BAŞLAYIN.txt`) | AI Çizim Dosyaları | `be7d2242532091fed20481f20f24ba51b1a41dab4a31eb129d70b1cb049c7954` |
| `astra_v1_4_3/cumbali-6x5-proje-notlari.md` | Cumbalı 6×5 projesinin karar notları (6 Eylül) | AI Çizim Dosyaları | `338e1467e2b9d27193ede25d0f8facf7da895890a3875e903eb2ce518a663fd3` |

Devir paketinin kendisi (`Portman_Claude_Devir_Paketi_2026-09-20.zip`, SHA256SUMS 99/99 doğrulandı) Mac'te `~/Desktop/outputs/` altında duruyor;
pakete buradan yalnız `kaynaklar/gorev2/reference/` alındı. `MALZEME_KATALOGU.json` zaten depoda (`ref_yan/`, `motor/malzeme_katalogu.json`; aynı hash).
Yan Verandalı 2+1 6×8,5 listesi de zaten depoda (`ref_yan/Yan-Verandali-2plus1-Yukleme-Listesi.xlsx`; Mac kopyasıyla aynı hash).

## cumbali_6x5/ · Astra'nın Cumbalı 6×5 yükleme listesi (7 Eylül 2026)

| Dosya | Ne | Kaynak | SHA-256 |
|---|---|---|---|
| `cumbali_6x5/Cumbali-6x5-Yukleme-Listesi.xlsx` | Astra'nın Cumbalı 6×5 yükleme listesi (7 Eylül 2026); yalnız çizilmiş bloklar | AI Çizim Dosyaları `BOM ve Yükleme Listeleri/Cumbalı 6x5/` | `b4d9a3a358c1921149244b478f57a0d53a406dd78ba8aa459b674b2d8163d019` |
| `cumbali_6x5/BOM_SAYIM_KAYDI.json` | Blok sayımı (blok adı ve merkez koordinatı) | aynı klasör | `6777b7ce0ef4a755ab1f116af6ca5fa32fbaf076b683c83305814e93821d4899` |
| `cumbali_6x5/BOM_DOGRULAMA.json` | Sayımın doğrulama kaydı | aynı klasör | `6488c55af4f205e326efa7e7f95f4fe524e7e30b96b3ec3896fe8a9bc76c58f6` |
| `cumbali_6x5/BOM_OKUMA.md` | Listenin nasıl okunacağı (özgün ad `BOM OKUMA.md`) | aynı klasör | `e3a0419cd67a57113c00f9a6c124f14684e61e737d7769889a868a9ca5b931e5` |
| `cumbali_6x5/prefabrik-cumbali-6x5-BOM.dwg` | Sayımın yapıldığı bloklu DWG | aynı klasör | `d3702b7d71a45bc3923fec87aaad3af0e9e1b94079c859553591fdac01a5b7d2` |

Bu liste çatı, profil ve tavan kalemlerini "çizimde tanımlı değil" diye dışarıda bırakır; 6 Ekim'deki 3+1 listesinin kıyas tablosunda anılır
(`deneme/2026-10-06_kalinlik_160_100/README.md`).

## cift_kat_R02/ · Astra'nın çift kat prefabrik 75 + 75 m² çizimi (12 Eylül 2026)

| Dosya | Ne | Kaynak | SHA-256 |
|---|---|---|---|
| `cift_kat_R02/r02_data.json` | **Veri modeli:** 12500 × 6000 mm, iki kat aynı plan; 59 pano, 10 bağlantı, 8 mahal, 23 malzeme kodu, aks ızgarası, açıklıklar | Mac `~/Documents/Codex/2026-09-12/me/work/` | `dcac001f1445dc6271deddd6e48acdf21bf345d5c0cb2ab2e07e2a32b6803557` |
| `cift_kat_R02/r02_bom_rows.json` | Katlara açılmış sayım satırları (Z-/U- parçalar) | aynı | `90f7eabdfb63f739455bebcdc747e059ff459968fafbbe8a2795677f57f17b77` |
| `cift_kat_R02/cift-kat-prefabrik-malzeme-R02.xlsx` | YÜKLEME + Blok Sayımı; formülle toplanan gerçek model sayımı | `…/me/outputs/` | `ff6649a7a4befaa02261923ebd8e1d9eac8acff84a54fddbd3fd6e89d588472e` |
| `cift_kat_R02/cift-kat-prefabrik-plan-montaj-R02.pdf` (`main`'de yok; İE-10 dalında, PR-K'dan sonra) | A3, 3 sayfa: ortak kat planı, pano montaj planı (PN001–PN059), ön görünüş ve kat kotları | `…/me/outputs/` | `b4b01d7ffdb26c0f401e329a96cda60db7d3470cff8ed824a9c3a7ab359a3813` |
| `cift_kat_R02/cift-kat-prefabrik-75m2-iki-daire-R02.dwg` (`main`'de yok; İE-10 dalında, PR-K'dan sonra) | AutoCAD modeli (iki katlı duvar/kolon, planlar, montaj kopyaları, ön görünüş) | `…/me/outputs/` | `24ef989b608da62034a9acea38540db4e2e5285c2a161d0e03d602aecc67ced1` |
| `cift_kat_R02/cift-kat-prefabrik-R02-teknik-ozet.md` | Astra'nın teknik özeti: düşey sistem, cephe kontrolü, aks uygulaması, sayım, sınırlar | `…/me/outputs/` | `26ac521399e841e019d3018a969b768d7951eeb19154b898826610f8d74f4bea` |
| `cift_kat_R02/cift-kat-prefabrik-on-kontrol.md` | Çizim öncesi kontrol: ilk 13600 mm talebi, belirsizlikler, kalite kontrol durumu | `…/me/outputs/` | `ba8c62938d6a7be2e649698a5327133eefd7a3e82e75a9371347d6c944b4bdc7` |
| `cift_kat_R02/cift-kat-prefabrik-R01-durum.md` | R01 ana gövde durumu (R02 bunun yerine geçti) | `…/me/outputs/` | `852f7063aa40b18e1b7387e8754af9d754ad6224f58b1e8ba3c15e9ce30f2e5a` |

Bugünkü standartla farkları (12 Ekim incelemesi; `docs/raporlar/2026-10-12_Prefabrik_Referans_Envanteri.md`): dış/iç duvar 100/60 mm
(standartla aynı), sürekli 100 × 100 × 5320 köşe profili (çift kat kuralı yazılmadı), 300 mm "çelik kiriş bölgesi" + 20 mm Betopan
(kesit ve adet yok; Astra "taşıyıcı detay değil" diye not düşmüş), merdiven ve balkon yok (üst kat girişi çözümsüz).
Üretim betikleri (`build_r02.py`, `build_r02.lsp`, `make_plan_pdf.py`, `make_bom.mjs`) alınmadı: AutoCAD'e bağlı hat.
