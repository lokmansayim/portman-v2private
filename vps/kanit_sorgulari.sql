-- PORTMAN · canlı kabul gösteriminin kanıt sorguları (İE-02). SALT OKUNUR: hiçbir şey yazmaz.
-- VPS'te:  sudo -u portman psql -d portman -f /opt/portman/app/kanit_sorgulari.sql
-- Telefon numaraları maskeli yazılır (ilk 3 + son 2 hane); mesaj metni ve bayinin sözünü içerebilecek alan (gerekçe) yazılmaz.
-- WhatsApp mesaj kimlikleri (wamid) karşı tarafın numarasını base64 olarak içerir; yalnız özetleri yazılır: left(md5(kimlik), 10)
-- (ajan günlüğündeki ve tekrar_dene.py'deki 'iz' ile aynı). Anahtar ya da sır yoktur.
\pset pager off
\echo '== 1. Son gelen mesajlar ve işleri (tekrar gelen mesaj ikinci iş açmaz: mesaj başına bir iş)'
SELECT left(md5(m.id), 10) AS mesaj_izi, left(m.gonderen, 3) || '…' || right(m.gonderen, 2) AS gonderen, m.tur,
       to_char(m.wa_zamani, 'HH24:MI:SS') AS yazildi, j.id AS is_id, j.durum, j.deneme,
       j.sonuc->>'eylem' AS eylem, j.sonuc->>'niyet' AS niyet, left(md5(m.alinti_id), 10) AS alinti_izi
FROM mesajlar m LEFT JOIN isler j ON j.mesaj_id = m.id ORDER BY m.alindi DESC LIMIT 20;

\echo '== 2. Mesaj başına iş sayısı (hepsi 1 olmalı)'
SELECT count(*) AS mesaj, count(j.id) AS is_, max(n) AS mesaj_basina_en_cok_is
FROM mesajlar m LEFT JOIN isler j ON j.mesaj_id = m.id
LEFT JOIN (SELECT mesaj_id, count(*) n FROM isler GROUP BY mesaj_id) k ON k.mesaj_id = m.id;

\echo '== 3. Sorular: hangi mesaj doğurdu, hangisi kapattı'
SELECT s.id, s.alan, left(md5(s.kaynak_mesaj_id), 10) AS kaynak_izi, s.deneme, s.durum, left(md5(s.cevap_mesaj_id), 10) AS cevap_izi, s.proje_id,
       to_char(s.soruldu, 'HH24:MI:SS') AS soruldu, to_char(s.kapandi, 'HH24:MI:SS') AS kapandi
FROM sorular s ORDER BY s.id DESC LIMIT 10;

\echo '== 4. Onay zinciri: revizyon → PDF mesaj kimliği → API kabulü (hosting saati) → Meta gönderdi / teslim etti → onay mesajı ve alıntısı'
SELECT proje_id, is_emri_no, rev, revizyon_durumu, left(md5(pdf_wamid), 10) AS pdf_izi, gonderim_durumu,
       to_char(kabul_zamani, 'HH24:MI:SS') AS api_kabul, to_char(gonderildi_zamani, 'HH24:MI:SS') AS meta_gonderdi,
       teslim_durumu, to_char(teslim_zamani, 'HH24:MI:SS') AS teslim,
       left(md5(onay_mesaj_id), 10) AS onay_mesaj_izi, left(md5(onay_alintisi), 10) AS onay_alinti_izi
FROM onay_zinciri ORDER BY revizyon_id DESC LIMIT 10;

\echo '== 5. Onay denemeleri: alıntılanan revizyon ve sonuç (eski revizyona verilen onay reddedilir)'
SELECT left(md5(mesaj_id), 10) AS mesaj_izi, to_char(wa_zamani, 'HH24:MI:SS') AS yazildi, alintilanan_is_emri_no, alintilanan_rev,
       onay->>'kabul' AS kabul, onay->>'rev' AS denetlenen_rev, onay->>'sinir' AS sinir, left(onay->>'neden', 50) AS neden
FROM cevap_baglari WHERE onay IS NOT NULL ORDER BY wa_zamani DESC LIMIT 10;

\echo '== 6. Giden satırlar (hosting durumu; kabul = API kabulü, teslim = Meta bildirimi; gonderilmedi/belirsiz = uyarı)'
SELECT left(g.id, 12) AS satir, g.is_id, g.sira, g.kind, g.durum, left(md5(g.dis_id), 10) AS wamid_izi, g.teslim_durumu,
       to_char(g.hostinge_verildi, 'HH24:MI:SS') AS hostinge, left(g.hata, 50) AS hata
FROM giden g ORDER BY g.olusturuldu DESC, g.sira LIMIT 20;
