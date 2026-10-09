# İE-04 · Aday teslim biçimi (çizim çalışması → Portman) · 30.09.2026

İlke: **tek geometri.** Çizim çalışmasından gelen aday, zincire kaynak veri olarak girer. WhatsApp'ta gösterilen plan görseli, seçilince gelen ölçülü PDF ve 3D bağlantısı aynı İş Emri revizyonundan Motor ve IFC ile üretilir. Plan ile 3D ayrı düzenlenemez; iki tarafta iki ayrı geometri oluşmaz. Yeni şema ve ayrı motor yok: şema İş Emri v0.1'dir.

## Her aday için teslim

Klasör: `24_Astra_Cizimler/gelen/<kod>_r<NN>/` (ör. `P9401_r01/`).

| # | Dosya | Zorunlu | İçerik |
|---|---|---|---|
| 1 | `is_emri.json` **ya da** `<kod>.dxf` | Evet | Kaynak veri. JSON: İş Emri v0.1; örnek `is_emri/P6001_2plus1_6x6.json` (elle kodlanmış), `deneme/2026-09-30_asama2/sonuc/P9401/is_emri.json` (çıkarıcıdan). DXF: `ASTRA_BRIEF.md` kuralları; İş Emri'ni çıkarıcı üretir, çıkarım raporu birlikte onaylanır |
| 2 | `plan.png` ya da `plan.pdf` | Evet | Üstten, ölçülü kat planı: oda adları ve m², dış ölçüler, kapı ve pencereler, veranda. Perspektif ya da çatısı kaldırılmış 3D plan sayılmaz. Görsel geri bildirim bunun üstünden verilir |
| 3 | `not.md` | Evet | Kaynak (katalog sayfası, DXF paftası), kaynaktan her sapma ve nedeni, belirsiz kalan ölçüler |
| 4 | 3D | Hayır | Aşama 2'nin basit 3D'si aynı İş Emri'nden IFC ile üretilir. Çizim tarafının etkileşimli 3D'si 4. adım sunumu için saklanır; aynı İş Emri revizyonundan üretilmediyse aday teslimine sayılmaz |

Teslim sırası aday başına: kaynak veri → plan görseli → (seçilince) ölçülü PDF → (aynı revizyondan) 3D. İlk ikisi çizim tarafından gelir; PDF ve 3D bizim zincirden çıkar.

## İş Emri'nde zorunlu alanlar (JSON teslimde)

- **Kimlik:** `is_emri_no` = `PM-ADAY-<kod>` (ör. `PM-ADAY-P9401`); `revizyon` 1'den başlar, her düzeltilmiş teslimde +1; `yapi.referans_model` = katalog kodu.
- **Kaynak:** `talep.bayi` = `{"kod": "ASTRA", "ad": "Astra çizim"}`; `talep.musteri_adi` = `ADAY <kod>`; `talep.metin` = katalog sayfa numarası, DXF pafta adı, tarih.
- **Birim ve ızgara:** cm; pano modülü 125,5; dış ölçü 125,5·nx + 20 × 125,5·ny + 10; `yapi.grid` yarım pano adımında; `kisa_kenar` `"x"`; öteki `yapi` alanları örnekteki gibi.
- **Mahaller:** her oda `konum_pano` dikdörtgenleriyle (pano birimi); ızgara boşluksuz bölünmüş; `tur` listeden (yatak_odasi, salon, mutfak, banyo, hol, veranda, sundurma, depo, …).
- **Açıklıklar:** pencere `olcu` ∈ {120x120, 120x180, 60x40}, `mahal`, `duvar` ∈ {sol, sag, on, arka}, `pano`; kapı `tur` ∈ {ic_kapi, dis_kapi, gecis}, `arasi` [oda A, oda B], `mentese`, **`olcu` her kapıda yazılır** (çizimdeki genişlik; varsayılan bırakılmaz).
- **Açık sınırlar:** duvarsız geçişler `acik_sinirlar`da (`[["HOL", "SALON"]]`).
- **Sapmalar ve belirsizlik:** `varsayimlar` = kaynaktan her sapma; `eksikler` = kaynakta belirsiz ölçü ve bilgiler. **Belirsiz ölçü tahmin edilip onaylanmış sayılmaz; `eksikler`e yazılır.**

## Geldiğinde kontrol

```
python3 deneme/2026-09-30_asama2/kos.py --cikti 24_Astra_Cizimler/denetim/<kod>_r<NN> --is-emri <gelen/…/is_emri.json> --kodlar <kod>
python3 deneme/2026-09-30_asama2/kos.py --cikti 24_Astra_Cizimler/denetim/<kod>_r<NN> --dxf <gelen/…/<kod>.dxf> --kodlar <kod>
```

Çıktı: Motor planı ve PDF'i, IFC, kaynakla kıyas (pencere ve kapı sayısı, oda alanları, dış ölçü), `eksikler` listesi. Yalnız somut eksik bildirilir.

## Üç kayıt ayrı tutulur

| Kayıt | Kim | Nerede |
|---|---|---|
| Kaynak ve teknik kontrol (sayılar, kıyas, Motor ve IFC sonucu) | Geliştirici | `24_Astra_Cizimler/denetim/<kod>_r<NN>/` |
| Görsel geri bildirim | Lokman | `not.md`'ye cevap; düzeltilmiş teslim yeni revizyon |
| Teknik değerlendirme ve kabul (açıklık konumu, kapı genişliği, aks; K-A5–K-A7, K-A10) | Yapı mühendisi | Kabul notu İş Emri'nin yanında, `kabul.md` |

Aday "hazır" sayılır: Motor İş Emri'ni çizer, kaynak kıyası eşik içinde (K-A9), görsel geri bildirim kapanmış, mühendis kabulü kayıtlı.

## Çizim yöntemi ne olursa olsun gereken kararlar

Çizimi etkileyenler model çalışmasına bağlıdır ve orada kapanır: alan tanımı (K-A1), kutu dışı veranda ve sundurma (K-A3), açıklık konumu (K-A5), kapı genişlikleri (K-A6), iç duvar ekseni (K-A7). Bunlar üretim kararıdır; JSON ya da DXF fark etmez.

Yalnız çıkarıcıya özgü olanlar, JSON teslimde ortadan kalkar: duvarsız bölgenin etikete göre bölünmesi (K-A4'ün çıkarıcı yanı), eşya yazısının oda sanılması, kasa çentiğinden pencere çıkarımı. K-A4'ün üretim yanı (açık geçişte sınır nerede) yine karardır.
