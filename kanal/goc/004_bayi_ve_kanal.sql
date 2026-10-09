-- İE-06 · 004: tek sunucu kanalı (Meta webhook, gönderim ve medya VPS'te) ve bayi kimlik kartı.
-- YALNIZ EKLER. Sürüm geri dönüşü kuralı (docs/is_emirleri/IE-06.md): önceki sürümün kodu bu şemada çalışmaya devam eder;
-- DROP TABLE / DROP COLUMN, RENAME, tür daraltma ve varsayılansız NOT NULL yok; CHECK genişletme serbest. Her ifade tekrar
-- koşulabilir (IF NOT EXISTS). Uygulandıktan sonra bu dosya değiştirilmez; sonraki değişiklik 005_… olur.

-- Bayi kimlik kartı (bayi rehberi §9): ad, hitap, firma, numara, bölge, rol, kod, aktif. Standartlar, proje sonucu ve notlar
-- sonraki işlerde AYRI tablolar olarak gelir; bu tablo o zaman değişmez. Kaynak artık bu tablodur (hosting kaydı değil).
ALTER TABLE bayiler ADD COLUMN IF NOT EXISTS hitap  text NOT NULL DEFAULT '';
ALTER TABLE bayiler ADD COLUMN IF NOT EXISTS firma  text NOT NULL DEFAULT '';
ALTER TABLE bayiler ADD COLUMN IF NOT EXISTS bolge  text NOT NULL DEFAULT '';
ALTER TABLE bayiler ADD COLUMN IF NOT EXISTS aktif  boolean NOT NULL DEFAULT true;
ALTER TABLE bayiler ADD COLUMN IF NOT EXISTS kaynak text NOT NULL DEFAULT 'kanal';      -- panel | kanal
ALTER TABLE bayiler DROP CONSTRAINT IF EXISTS bayiler_rol_check;
ALTER TABLE bayiler ADD CONSTRAINT bayiler_rol_check CHECK (rol IN ('bayi', 'patron', 'muhendis'));

-- Gelen mesaj: hangi yoldan geldi, sahiplenildi mi (kayıtsız gönderenin mesajı da yazılır; iş açılmaz, panelde görünür).
ALTER TABLE mesajlar ADD COLUMN IF NOT EXISTS kaynak       text NOT NULL DEFAULT 'vps';
ALTER TABLE mesajlar ADD COLUMN IF NOT EXISTS sahiplenildi boolean NOT NULL DEFAULT true;
CREATE INDEX IF NOT EXISTS mesajlar_alindi ON mesajlar (alindi DESC);

-- Giden satır: yüklenen medyanın kimliği (yeniden denemede yeniden yüklenmez) ve çözülen alıcı ('PATRON' → numara).
ALTER TABLE giden ADD COLUMN IF NOT EXISTS medya_id      text;
ALTER TABLE giden ADD COLUMN IF NOT EXISTS alici_cozuldu text;

-- Gelen medya (görsel, belge, ses, video): gönderici servisi indirir, data/gelen_medya/ altına yazar; panel buradan sunar.
CREATE TABLE IF NOT EXISTS gelen_dosyalar (
    id           bigserial PRIMARY KEY,
    mesaj_id     text NOT NULL REFERENCES mesajlar(id),
    medya_id     text NOT NULL,
    dosya_adi    text,
    mime         text,
    yol          text,                          -- indirilince dolar
    boyut        bigint,
    sha256       text,
    deneme       int NOT NULL DEFAULT 0,
    hata         text,
    olusturuldu  timestamptz NOT NULL DEFAULT now(),
    indirildi    timestamptz,
    UNIQUE (mesaj_id, medya_id)
);
CREATE INDEX IF NOT EXISTS gelen_dosyalar_bekleyen ON gelen_dosyalar (olusturuldu) WHERE yol IS NULL AND deneme < 3;

-- Webhook olaylarının tekilleştirilmesi: Meta aynı olayı yeniden gönderebilir. anahtar = wamid (mesaj) ya da
-- sha256(wamid|durum|zaman) (durum bildirimi). Ham gövde saklanmaz.
CREATE TABLE IF NOT EXISTS webhook_olaylar (
    anahtar      text PRIMARY KEY,
    tur          text NOT NULL,
    alindi       timestamptz NOT NULL DEFAULT now()
);

-- Kayıtsız (ya da modun işlemediği) gönderene giden sabit cevap: gönderen başına 24 saatte bir.
CREATE TABLE IF NOT EXISTS kayitsiz_cevaplar (
    gonderen     text PRIMARY KEY,
    son          timestamptz NOT NULL,
    sayi         int NOT NULL DEFAULT 1
);

-- Panel girişleri: deneme sınırı için (IP yalnız özetle).
CREATE TABLE IF NOT EXISTS panel_girisler (
    id           bigserial PRIMARY KEY,
    zaman        timestamptz NOT NULL DEFAULT now(),
    sonuc        text NOT NULL CHECK (sonuc IN ('basarili', 'basarisiz', 'kilitli')),
    ip_ozeti     text
);
CREATE INDEX IF NOT EXISTS panel_girisler_zaman ON panel_girisler (zaman DESC);
