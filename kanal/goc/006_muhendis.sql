-- İE-08 8b · 006: mühendis teknik kontrolü (M1–M3). Bayi çelik planı onaylayınca bir kontrol kaydı açılır; mühendisin kararı,
-- düzeltme notu, geri gönderdiği Excel sürümleri ve hatırlatma sayaçları burada tutulur. Fiyat bu tabloda değildir (İE-13).
-- YALNIZ EKLER (docs/is_emirleri/IE-06.md › Sürüm kuralı; .claude/rules/kanal-vps.md): önceki sürümün kodu bu şemada çalışmaya
-- devam eder (tabloyu bilmez); DROP TABLE / DROP COLUMN, RENAME, tür daraltma ve varsayılansız NOT NULL yok. Her ifade tekrar
-- koşulabilir. Uygulandıktan sonra bu dosya değiştirilmez; sonraki değişiklik 007_… olur.

CREATE TABLE IF NOT EXISTS muhendis_kontrolleri (
    id                       bigserial PRIMARY KEY,
    is_emri_no               text NOT NULL,
    rev                      int  NOT NULL,
    bayi                     text NOT NULL,                 -- bayinin numarası (giden satırları bu konuşmaya bağlanır; günlükte maskeli)
    bayi_kod                 text,
    onay_mesaj_id            text NOT NULL REFERENCES mesajlar(id),   -- bayinin onay mesajı: bildirim ve hatırlatma satırlarının çapası
    muhendis                 text,                          -- bildirimin çözüldüğü mühendis kartı (NULL: aktif mühendis kartı yoktu)
    durum                    text NOT NULL DEFAULT 'bekliyor'
                             CHECK (durum IN ('bekliyor', 'patrona_gonderildi', 'duzeltme', 'kart_yok')),
    olusturuldu              timestamptz NOT NULL DEFAULT now(),
    sure_baslangici          timestamptz NOT NULL DEFAULT now(),   -- 3 saatlik cevap süresi; gece onayında 08:00 (İstanbul)
    dosya_gonderildi         timestamptz,                   -- mühendis "Gönder"e ilk bastığında
    karar_zamani             timestamptz,
    son_hatirlatma           timestamptz,
    hatirlatma_sayisi        int  NOT NULL DEFAULT 0,
    gecikme_bildirildi       timestamptz,                   -- 3 saat dolunca Patron'a bir kez
    bekleyen                 text,                          -- mühendisten beklenen serbest metin: 'duzeltme_notu'
    not_                     text,                          -- mühendisin düzeltme notu (Patron'a ve panele)
    listeler                 jsonb NOT NULL DEFAULT '[]',   -- Excel sürümleri: [{surum, kaynak: sunucu|muhendis, mesaj_id?, dosya?, sha256?, zaman}]
    patron_durum             text NOT NULL DEFAULT 'yok'
                             CHECK (patron_durum IN ('yok', 'bekliyor', 'fiyat_verildi', 'durdu')),
    patron_hatirlatma_sayisi int  NOT NULL DEFAULT 0,
    patron_son_hatirlatma    timestamptz,
    UNIQUE (is_emri_no, rev)
);
CREATE INDEX IF NOT EXISTS muhendis_kontrolleri_acik ON muhendis_kontrolleri (durum, patron_durum);
CREATE INDEX IF NOT EXISTS muhendis_kontrolleri_bayi ON muhendis_kontrolleri (bayi, olusturuldu);
