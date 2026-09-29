-- İE-02 · 001: kalıcı konuşma ve iş akışı. Göç çalıştırıcı: kanal/depo.py (Depo.goc_uygula).
-- Bir ortamda uygulandıktan sonra bu dosya değiştirilmez; şema değişikliği 002_… olarak eklenir (28.09: yalnız testlerde uygulandı).
-- Zamanlar timestamptz (UTC). Telefon numarası yalnız yönlendirme anahtarıdır; günlüklere maskeli yazılır.

-- Bayi kimliği WhatsApp numarasıdır (Meta imzalı webhook doğrular). 'kod' yalnız etikettir: panelde kod yoksa feature.php
-- numaranın son 4 hanesinden türetir ('B' + 4 hane), bu yüzden benzersiz değildir ve yetki ayrımında kullanılmaz.
CREATE TABLE bayiler (
    numara       text PRIMARY KEY,
    kod          text,
    ad           text NOT NULL DEFAULT '',
    rol          text NOT NULL DEFAULT 'bayi' CHECK (rol IN ('bayi', 'patron')),
    olusturuldu  timestamptz NOT NULL DEFAULT now(),
    guncellendi  timestamptz NOT NULL DEFAULT now()
);

-- Gelen WhatsApp mesajı. id = WhatsApp mesaj kimliği (wamid): aynı mesaj ikinci kez yazılamaz.
CREATE TABLE mesajlar (
    id           text PRIMARY KEY,
    gonderen     text NOT NULL,
    bayi_kod     text,                          -- etiket (bkz. bayiler)
    tur          text NOT NULL,
    metin        text NOT NULL DEFAULT '',
    alinti_id    text,                          -- bayinin alıntılayarak cevap verdiği mesaj (WhatsApp context.id), varsa
    wa_zamani    timestamptz NOT NULL,          -- WhatsApp'ın verdiği gönderim anı
    alindi       timestamptz NOT NULL DEFAULT now(),
    ham          jsonb NOT NULL                 -- kuyruk satırı olduğu gibi
);
CREATE INDEX mesajlar_gonderen ON mesajlar (gonderen, wa_zamani);

-- Mesaj başına bir iş. Kira (sahip + kira_bitis) dolarsa iş yeniden alınabilir; deneme sınırı depo.py'de.
CREATE TABLE isler (
    id           bigserial PRIMARY KEY,
    mesaj_id     text NOT NULL UNIQUE REFERENCES mesajlar(id),
    gonderen     text NOT NULL,
    durum        text NOT NULL DEFAULT 'sirada' CHECK (durum IN ('sirada', 'isleniyor', 'bitti', 'basarisiz')),
    deneme       int  NOT NULL DEFAULT 0,
    sahip        text,
    kira_bitis   timestamptz,
    cikarim      jsonb,                         -- LLM çıkarımı: yarım iş yeniden alınınca LLM yeniden çağrılmaz
    sonuc        jsonb,
    hata         text,
    olusturuldu  timestamptz NOT NULL DEFAULT now(),
    basladi      timestamptz,
    bitti        timestamptz
);
CREATE INDEX isler_acik ON isler (gonderen, id) WHERE durum IN ('sirada', 'isleniyor');

-- Gönderen başına konuşma durumu (beyin/konusma.py'nin sözlüğü). surum: okunan sürümle yazılır, sessiz ezme olmaz.
CREATE TABLE konusmalar (
    gonderen     text PRIMARY KEY,
    bayi_kod     text,
    durum        jsonb NOT NULL,
    surum        bigint NOT NULL DEFAULT 1,
    guncellendi  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE projeler (
    id              bigserial PRIMARY KEY,
    gonderen        text NOT NULL,
    bayi_kod        text,
    ilk_is_emri_no  text NOT NULL,
    olusturuldu     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX projeler_gonderen ON projeler (gonderen, id);

CREATE TABLE revizyonlar (
    id              bigserial PRIMARY KEY,
    proje_id        bigint NOT NULL REFERENCES projeler(id),
    rev             int NOT NULL,
    is_emri_no      text NOT NULL,
    gonderen        text NOT NULL,
    bayi_kod        text,
    kaynak_mesaj_id text NOT NULL REFERENCES mesajlar(id),
    is_emri         jsonb NOT NULL,
    pdf_yolu        text,
    pdf_sha256      text,
    dxf_sha256      text,
    dogrulandi      boolean NOT NULL,
    durum           text NOT NULL CHECK (durum IN ('onay_bekliyor', 'onaylandi', 'yerini_aldi', 'dogrulanmadi')),
    onay_mesaj_id   text REFERENCES mesajlar(id),
    onaylandi       timestamptz,
    uretildi        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (is_emri_no, rev)                    -- PDF yolu projects/<no>/rNN: aynı yol iki revizyona yazılamaz
);
CREATE INDEX revizyonlar_proje ON revizyonlar (proje_id, id);

-- Bekleyen soru kaydı (B1/B2 ve eksik bilgi soruları). Kural katmanı konuşma durumunu okur; bu tablo aynı işlemde yazılır ve
-- hangi mesajın hangi soruyu doğurduğunu, hangisinin cevapladığını tutar.
CREATE TABLE sorular (
    id               bigserial PRIMARY KEY,
    gonderen         text NOT NULL,
    proje_id         bigint REFERENCES projeler(id),
    alan             text NOT NULL,             -- son_soru_alani: yeni_mi_degisiklik, pencere_islem, pencere_mahal, …
    kaynak_mesaj_id  text REFERENCES mesajlar(id),   -- boş: soru dosya düzeninden geçişte geldi, doğuran mesaj bilinmiyor
    bekletilen_talep jsonb,                     -- D-01: bekletilen mesajın talebi
    bekletilen_metin text,
    pencere_satiri   jsonb,                     -- B1: sorulan pencere satırı
    deneme           int NOT NULL DEFAULT 1,
    soruldu          timestamptz NOT NULL,
    son_soruldu      timestamptz NOT NULL,
    gecerlilik_sonu  timestamptz,
    durum            text NOT NULL DEFAULT 'acik' CHECK (durum IN ('acik', 'cevaplandi', 'dustu', 'devredildi')),
    cevap_mesaj_id   text REFERENCES mesajlar(id),
    kapandi          timestamptz
);
CREATE UNIQUE INDEX sorular_tek_acik ON sorular (gonderen) WHERE durum = 'acik';

-- Gönderim niyeti: işle aynı işlemde yazılır. id = worker.satir_id(mesaj, sira): aynı satır iki kez yazılamaz.
CREATE TABLE giden (
    id               text PRIMARY KEY,
    is_id            bigint NOT NULL REFERENCES isler(id),
    mesaj_id         text NOT NULL REFERENCES mesajlar(id),
    sira             int NOT NULL,
    alici            text NOT NULL,             -- gönderen numarası ya da 'PATRON'
    tur              text NOT NULL,             -- cevap, belge, bildirim
    kind             text NOT NULL CHECK (kind IN ('text', 'document')),
    govde            text NOT NULL,
    dosya            text,
    sha256           text,
    revizyon_id      bigint REFERENCES revizyonlar(id),
    durum            text NOT NULL DEFAULT 'bekliyor'
                     CHECK (durum IN ('bekliyor', 'gonderiliyor', 'iletildi', 'belirsiz', 'gonderilmedi')),
    deneme           int NOT NULL DEFAULT 0,
    dis_id           text,                      -- WhatsApp'ın verdiği giden mesaj kimliği
    -- 'iletildi' ve iletildi zamanı: WhatsApp API'nin gönderimi KABUL ETTİĞİ an (Cloud API 'accepted'); bayiye teslim değildir.
    hata             text,
    olusturuldu      timestamptz NOT NULL DEFAULT now(),
    gonderim_basladi timestamptz,
    iletildi         timestamptz,
    UNIQUE (mesaj_id, sira)
);
CREATE INDEX giden_bekleyen ON giden (olusturuldu, mesaj_id, sira) WHERE durum = 'bekliyor';
CREATE INDEX giden_dis_id ON giden (dis_id);
