-- İE-14 · 007: talepten plana — yeni plan üretimlerinin kaydı (D-18; geri bildirim döngüsü ve test seti). Her üretim (geçerli, geçersiz
-- ya da hata) bir satırdır: yapısal talep (müşteri adı ve numara yok), LLM denemelerinin taslakları ve denetçinin ihlalleri, çağrı ve
-- token sayıları. Bayi yeni planı seçip r01 alınca is_emri_no bağlanır; revizyonlar ve mühendis düzeltmesi o İş Emri üzerinden izlenir.
-- YALNIZ EKLER (.claude/rules/kanal-vps.md): DROP / RENAME / daraltma / varsayılansız NOT NULL yok; her ifade tekrar koşulabilir.
-- Uygulandıktan sonra bu dosya değiştirilmez; sonraki değişiklik 008_… olur.

CREATE TABLE IF NOT EXISTS plan_uretimleri (
    id            bigserial PRIMARY KEY,
    mesaj_id      text NOT NULL REFERENCES mesajlar(id),   -- üretimi doğuran bayi mesajı
    gonderen      text NOT NULL,                           -- bayinin numarası (günlükte maskeli)
    bayi_kod      text,
    durum         text NOT NULL CHECK (durum IN ('gecerli', 'gecersiz', 'hata')),
    plan_kodu     text,                                    -- 'YENI-…' (geçerliyse)
    talep         jsonb NOT NULL DEFAULT '{}',             -- yapısal talep (alan, oda programı, çatı, veranda, özel istekler; maskeli)
    denemeler     jsonb NOT NULL DEFAULT '[]',             -- [{plan, gecerli, ihlaller, girdi_token, cikti_token, sure_ms}]
    cagri         int  NOT NULL DEFAULT 0,
    girdi_token   int  NOT NULL DEFAULT 0,
    cikti_token   int  NOT NULL DEFAULT 0,
    model         text,
    hata          text,
    is_emri_no    text,                                    -- bayi yeni planı seçince (r01)
    olusturuldu   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (mesaj_id)
);
CREATE INDEX IF NOT EXISTS plan_uretimleri_zaman ON plan_uretimleri (olusturuldu);
CREATE INDEX IF NOT EXISTS plan_uretimleri_kod ON plan_uretimleri (plan_kodu);

-- İE-14 r3 (14.10.2026; 007 canlıya uygulanmadan, yalnız ekler): üretim yolu (uyarlama / çözücü / LLM programı), puan, süre, program,
-- adaylar (her biri: kod, yol, puan, iç kaynak kodu, işlemler, doğrulama raporu) ve programdan değişenler (son basamak).
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS yol       text;
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS puan      real;
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS sure_ms   int;
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS program   jsonb;
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS adaylar   jsonb NOT NULL DEFAULT '[]';
ALTER TABLE plan_uretimleri ADD COLUMN IF NOT EXISTS degisen   jsonb NOT NULL DEFAULT '[]';
