# Ürün platformu şartnamesi (taslak)

Çizim ve üretim kurallarının kaydı. İş emri: `docs/is_emirleri/IE-05.md` (taslak; Lokman'ın onayını bekliyor).

Kurallar Lokman'ın ve Ubeydullah'ın anlattıklarından yazılır. Her madde kaynağı ve tarihiyle durur.
"Çıkarım" diye işaretlenen maddeler Claude'un hesabı ya da yorumudur; teyit edilene kadar kural sayılmaz.
Astra dönemindeki kurallar (v1.4.3) kanıt olarak alınır; buraya ancak tek tek onaylanarak taşınır.

| Dosya | İçerik |
|---|---|
| `aileler.md` | Beş kural ailesi ve ürün kategorilerinin bu ailelerden nasıl kurulduğu |
| `celik_duvar.md` | Çelik (LGF) duvar sistemi: paketler, katmanlar, kaplama düzeni, karkas, et kalınlığı kuralı, metraj |
| `prefabrik_duvar.md` | Prefabrik panel duvar: panel, aks, köşe dikmeleri |
| `cati.md` | Çatı: kırma (dört omuz) kuralları, saçak, iki çatı işleme yöntemi, altı kaplama seçeneği ve baz kaplama, kaplamaların kapatma genişliği (ürüne göre), kırma çatıda kaplama adedinin çatı açılımından bulunması (dizilim her yüzde köşeden, kesim payı, yedek yok), kaplamanın saçaktan taşması, panel boyunun adet düşüyorsa uzatılması, tavan ve çatı paneli, mahya bandı, dere inişi, veranda çerçevesi, Ç8201'e uygulama; Lokman'ın 7 Ekim cevapları (çelikte her zaman çatı ve tavan paneli, bindirme 20 cm, iniş kuralı, panel boyunun 10 mm'ye yukarı yuvarlanması, kapama, kenar kutusu) |
| `yukleme_listesi_celik.md` | Gerçek bir çelik yükleme listesinin grupları ve kalemleri; kurallarla tutmayan noktalar |
| `yukleme_listesi_yontemi.md` | Yükleme listesinin yöntemi: Lokman'ın 3 Ekim 13:27 cevapları, 4 Ekim düzeltmeleri (01:24, 01:42), 4 Ekim 15:18, 16:18 ve 17:46 cevapları, 7 Ekim 07:45 cevapları ve 08:02 düzeltmeleri (kör testin on iki sorusu; kural seti 0.13), mühendisin üç tur cevabı ve denetimi (3 Ekim 18:14, 4 Ekim 01:24 ve 12:14), çatı açılımı ve kaplama dizilimi, kesim planının ölçüleri, panel boyu uzatma kuralı, montaj paftalarının üç gerçek listeyle karşılaştırması, Excel motorundaki kaplama formülünün hücreleri ve bulgular, gerçek listelerin çalışma kitapları ve Excel hesaplama motoru; çelik kg; köşebent ve elektrik kuralı; üç gerçek listeyle karşılaştırma; Ç8201 taslağı; bayi kuralı; Excel motoruyla ilgili gözlemler; kör test (KT-01) ve kararlardan sonraki durumu; açık sorular. `deneme/2026-10-03_yukleme/belge_uret.py` üretir |
| `cizim_seti.md` | Çizim seti standardı (Lokman, 7 Ekim 07:45: "bunları kurala ekle"): plan, dört görünüş, pafta, IFC4, perspektifler; setin tek komutla üretilmesi ve denetimi; paftadaki açıklama satırları (Lokman'la birlikte düzeltilecek) |
| `montaj_paftasi.md` | Montaj paftası: klasörlerdeki örnekler (13 klasör, 84 PDF, ana DWG'ler), setteki paftalar ve çerçeve, kırma çatıda bugünkü uygulama, paftaların yükleme listesiyle bağı, pafta üretimi için gereken veri. Pafta işi yükleme listesinden sonra, ayrı (Lokman, 4 Ekim 17:46) |
| `modeller/C8201.md` | İlk çalışılan model: tek kat çelik, 82 m² |
| `katalog_denetimi_tek_kat_celik.md` | Tek kat çelik on modelde çizim ile katalog kaydının karşılaştırması |
| `skp_olcumleri.md` | Üç çelik projenin SketchUp modelinden ölçülenler; kurallarla tutan ve tutmayan yerler |
| `../../deneme/2026-10-02_celik/` | İlk deneme: Ç8201'in tanım dosyası, duvar tipleri, hesap; plan, çatı planı ve dört görünüşlü pafta |
| `../../deneme/2026-10-02_skp/` | SKP okuma denemesi: betikler ve üç modelin ölçü özeti |
| `../../deneme/2026-10-03_yukleme/` | Yükleme listesi denemesi: kurallar (sürümlü kural setleri), hesap, üç gerçek listeyle karşılaştırma, Ç8201 taslağı (baz, dış 140, altı kaplama seçeneği, yöntem B), çatı açılımı (çizim, kesim planı ve kesim ölçüleri), Excel motorunun kaplama formülü, bayi kuralı örneği |
| `../../deneme/2026-10-06_kor_test/` | Kör test (KT-01) ve genel model motoru: Yapı Tanımı 0.5, çok düzlemli çatı, tanımdan metraj ve liste girdisi, plan, görünüşler, pafta, IFC4 ve perspektifler; gerçek listeyle kıyas (7 Ekim 03:46) ve Lokman'ın kararlarından sonraki durum; çizim seti standardı ve betiği |
| `../raporlar/2026-10-07_Kor_Test_KT01.md` | Kör testin raporu: yöntem, sonuç, bizim hatalarımız, Eylül 2026 listesinin farklı yaptıkları, on iki soru; 13. bölüm: Lokman'ın cevapları ve kararlardan sonra durum |

Kapsam (2 Ekim 2026): çalışma tek kat çelik üzerine. 7 Ekim 2026: çelikte çatı her zaman çatı ve tavan paneliyle; omega ve aşıklı yöntem prefabrikle birlikte, sırası gelince çalışılacak (Lokman). Kat döşemesi ve merdiven çift kat konusudur; şimdilik kapsam dışı.
