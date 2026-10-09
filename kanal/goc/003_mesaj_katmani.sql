-- İE-04 · 003: WhatsApp mesaj katmanı (kanal v1.3). Yalnız EKLER; mevcut satırlar ve görünümler değişmez.
-- Tasarım: docs/is_emirleri/IE-04-mesaj-katmani.md. Canlıya uygulanması ayrı onaydır; uygulandıktan sonra bu dosya değiştirilmez.

-- Giden satır türleri: plan görseli (image) ve etkileşimli mesaj (buton, liste, bağlantı butonu).
ALTER TABLE giden DROP CONSTRAINT IF EXISTS giden_kind_check;
ALTER TABLE giden ADD CONSTRAINT giden_kind_check CHECK (kind IN ('text', 'document', 'image', 'interactive'));

-- Her revizyonun aynı İş Emri'nden türetilmiş öteki dosyaları: {"gorsel": {yol, sha256}, "ifc": {...}, "ucb": {yol, sha256, url}}.
-- PDF için mevcut sütunlar (pdf_yolu, pdf_sha256) esas kalır; burası PDF'i tekrarlamaz.
ALTER TABLE revizyonlar ADD COLUMN ekler jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Bayiye sunulan seçenek seti. id ajan üretir: 'ss_' + sha256(kaynak mesaj id)[:16] (buton kimlikleri s:<id>:<kod>).
-- Bir göndericinin aynı anda tek açık seti olur; yeni set açılınca eskisi 'eskidi' olur ve eski butonlar seçim yapmaz.
CREATE TABLE secenek_setleri (
    id               text PRIMARY KEY,
    gonderen         text NOT NULL,
    proje_id         bigint REFERENCES projeler(id),
    kaynak_mesaj_id  text NOT NULL REFERENCES mesajlar(id),
    adaylar          jsonb NOT NULL,             -- [{kod, puan, gerekce, sira, katalog_m2, ...}] sunulduğu sırayla
    agirliklar       jsonb,                      -- puanın hesaplandığı ağırlıklar (geçici; karar bekliyor)
    durum            text NOT NULL DEFAULT 'acik' CHECK (durum IN ('acik', 'secildi', 'eskidi', 'dustu')),
    secilen_kod      text,
    secim_mesaj_id   text REFERENCES mesajlar(id),
    olusturuldu      timestamptz NOT NULL DEFAULT now(),
    kapandi          timestamptz
);
CREATE UNIQUE INDEX secenek_setleri_tek_acik ON secenek_setleri (gonderen) WHERE durum = 'acik';

-- Aday kaydı: şablon pakette (is_emri/adaylar/<kod>.json), kaynak ve kabul burada. durum: test (yalnız yerel), kosullu, gecerli.
-- Kalıcı modda 'gecerli' bir aday ancak muhendis_kabulu dolu ise bayiye sunulur (K-A10).
CREATE TABLE adaylar (
    kod              text PRIMARY KEY,
    durum            text NOT NULL CHECK (durum IN ('test', 'kosullu', 'gecerli')),
    referans_model   text,                       -- katalog kodu
    kaynak           jsonb,                      -- {katalog_sayfa, dxf_pafta, teslim: "24_Astra_Cizimler/gelen/<kod>_r01", revizyon}
    ozet             jsonb,                      -- {katalog_m2, kapali_m2, veranda_m2, oda_programi, pencere, kapi, pano, odalar}
    denetim          jsonb,                      -- K-A9 kaynak uygunluk sonucu (kos.py kaynak_karsilastirma)
    muhendis_kabulu  jsonb,                      -- {kim, tarih, not} — K-A10
    not_             text,
    olusturuldu      timestamptz NOT NULL DEFAULT now(),
    guncellendi      timestamptz NOT NULL DEFAULT now()
);
