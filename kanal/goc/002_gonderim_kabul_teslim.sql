-- İE-02 · 002: gönderim durumları ayrılır ve hosting'e bağlanır.
--   * WhatsApp API'nin gönderimi KABUL etmesi (kabul_edildi, kabul_zamani) ile bayinin telefonuna TESLİM (teslim_durumu,
--     teslim_zamani: Meta'nın imzalı durum bildiriminden) ayrı tutulur; kabul teslim sayılmaz.
--   * hostingte: satır hosting'e devredildi, gönderimi hosting (feature.php) yapıyor; sonucu giden_durum ile okunur.
--   * satir: worker'ın ürettiği giden satırı, hosting'in beklediği biçimde (result çağrısı bunu olduğu gibi taşır).
--   * onay_zinciri ve cevap_baglari: gönderilen mesaj kimliği → revizyon → proje → gelen cevap bağlantısı.
--   * gonderildi_zamani: Meta'nın ilk 'sent' bildirimi (Meta saati). Onay denetiminde teslim bildirimi yoksa kabul anından
--     (hosting saati) önce buna bakılır.
-- Bu dosya hiçbir canlı veritabanına uygulanmadan önce son hâlini aldı (28.09); uygulandıktan sonra değiştirilmez.

ALTER TABLE giden DROP CONSTRAINT giden_durum_check;
UPDATE giden SET durum = 'kabul_edildi' WHERE durum = 'iletildi';
ALTER TABLE giden RENAME COLUMN iletildi TO kabul_zamani;
ALTER TABLE giden ADD CONSTRAINT giden_durum_check
    CHECK (durum IN ('bekliyor', 'gonderiliyor', 'hostingte', 'kabul_edildi', 'belirsiz', 'gonderilmedi'));
ALTER TABLE giden
    ADD COLUMN hostinge_verildi timestamptz,
    ADD COLUMN teslim_durumu    text CHECK (teslim_durumu IN ('sent', 'delivered', 'read', 'failed')),
    ADD COLUMN teslim_zamani    timestamptz,     -- Meta bildirimindeki ilk 'delivered' ya da 'read' anı
    ADD COLUMN gonderildi_zamani timestamptz,    -- Meta bildirimindeki ilk 'sent' (ya da sonraki) anı
    ADD COLUMN satir            jsonb;
CREATE INDEX giden_esitlenecek ON giden (olusturuldu DESC) WHERE hostinge_verildi IS NOT NULL
    AND (durum IN ('hostingte', 'belirsiz') OR (durum = 'kabul_edildi' AND teslim_zamani IS NULL));

-- Her revizyon: PDF'in giden satırı ve WhatsApp kimliği, kabul ve teslim, onay mesajı ve alıntıladığı mesaj.
CREATE VIEW onay_zinciri AS
SELECT r.gonderen, r.proje_id, r.id AS revizyon_id, r.is_emri_no, r.rev, r.durum AS revizyon_durumu,
       g.id AS pdf_satiri, g.dis_id AS pdf_wamid, g.durum AS gonderim_durumu, g.kabul_zamani, g.gonderildi_zamani, g.teslim_durumu, g.teslim_zamani,
       r.onay_mesaj_id, om.wa_zamani AS onay_yazildi, om.alinti_id AS onay_alintisi, r.onaylandi
FROM revizyonlar r
LEFT JOIN giden g ON g.revizyon_id = r.id AND g.kind = 'document'
LEFT JOIN mesajlar om ON om.id = r.onay_mesaj_id;

-- Her gelen mesaj: alıntıladığı giden mesaj (varsa) ve onun revizyonu/projesi; işin sonucu.
CREATE VIEW cevap_baglari AS
SELECT m.id AS mesaj_id, m.gonderen, m.wa_zamani, m.alinti_id,
       g.id AS alintilanan_satir, rv.id AS alintilanan_revizyon, rv.is_emri_no AS alintilanan_is_emri_no, rv.rev AS alintilanan_rev,
       rv.proje_id AS alintilanan_proje, j.durum AS is_durumu, j.sonuc->>'eylem' AS eylem, j.sonuc->>'gerekce' AS gerekce,
       j.sonuc->'onay' AS onay
FROM mesajlar m
LEFT JOIN giden g ON g.dis_id = m.alinti_id AND g.alici = m.gonderen
LEFT JOIN revizyonlar rv ON rv.gonderen = m.gonderen
                        AND (rv.id = g.revizyon_id OR (g.revizyon_id IS NULL AND rv.kaynak_mesaj_id = g.mesaj_id))
LEFT JOIN isler j ON j.mesaj_id = m.id;
