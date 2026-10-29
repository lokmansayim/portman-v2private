-- İE-22 · 010: WhatsApp'tan bayi kaydı (Kurulum Panosu satır 111; bayi rehberi §9 "Bayi nasıl eklenir"). Kartı olmayan numara yazınca
-- Portman adını ve firmasını sorar (kanal/kayit.py, LLM yok); Patron [Onayla] [Reddet] der; onayla kart (bayiler) açılır. Talep bu tabloda,
-- kart her zamanki gibi bayiler'de (göç 004'teki ilke: kartın kendisi değişmez).
-- YALNIZ EKLER; her ifade tekrar koşulabilir. Uygulandıktan sonra bu dosya değiştirilmez.

CREATE TABLE IF NOT EXISTS kayit_talepleri (
    id             bigserial PRIMARY KEY,
    numara         text NOT NULL,                       -- kartın anahtarı olacak numara (kart onayla açılır; FK yok)
    durum          text NOT NULL CHECK (durum IN ('ad', 'firma', 'onay_bekliyor', 'onaylandi', 'reddedildi', 'zaman_asimi')),
    ad             text NOT NULL DEFAULT '',
    firma          text NOT NULL DEFAULT '',
    ilk_mesaj_id   text NOT NULL REFERENCES mesajlar(id),
    son_mesaj_id   text NOT NULL REFERENCES mesajlar(id),   -- bayinin son mesajı: karşılama ve red cevabı buna bağlanır (alıcı = gönderen)
    karar_kaynagi  text CHECK (karar_kaynagi IN ('whatsapp', 'panel')),
    karar_mesaj_id text,                                -- Patron'un düğme mesajı (WhatsApp'tan karar verildiyse)
    olusturuldu    timestamptz NOT NULL DEFAULT now(),
    guncellendi    timestamptz NOT NULL DEFAULT now(),
    karar_zamani   timestamptz
);
-- Numara başına tek açık talep (iki eşzamanlı mesaj ikinci talep açamaz).
CREATE UNIQUE INDEX IF NOT EXISTS kayit_talepleri_acik ON kayit_talepleri (numara) WHERE durum IN ('ad', 'firma', 'onay_bekliyor');
CREATE INDEX IF NOT EXISTS kayit_talepleri_numara ON kayit_talepleri (numara, id DESC);
CREATE INDEX IF NOT EXISTS kayit_talepleri_olusturuldu ON kayit_talepleri (olusturuldu DESC);
