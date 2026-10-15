-- İE-14 r3 · 008: LLM-önce okuma gölgede (P4; Lokman 14.10.2026, 4. madde). `llm_once_revizyon.mod = "golge"` iken çelik banka
-- modelinin revizyon mesajı iki yoldan okunur: kural (celik_okuma; karar verir) ve LLM (degisiklik_okuyucu; yalnız kayıt). Bayiye bir şey
-- gitmez. Satır: iki okuma (ortak biçim, beyin/okuma_kiyas.py), sınıf, insan etiketi (Lokman ya da mühendis panelden/elle doldurur).
-- Mesaj metni ve cümle parçası burada TUTULMAZ (mesajlar tablosunda; dışa aktarımda maskeli): okumaların yalnız yapısal öğeleri ve
-- okunamayan/olumsuz cümle SAYISI yazılır (beyin/okuma_kiyas.kayit_ozeti; İE-14 kapanış incelemesi KV1). YALNIZ EKLER; her ifade
-- tekrar koşulabilir.

CREATE TABLE IF NOT EXISTS okuma_kiyaslari (
    id            bigserial PRIMARY KEY,
    mesaj_id      text NOT NULL REFERENCES mesajlar(id),
    gonderen      text NOT NULL,                           -- bayinin numarası (günlükte maskeli)
    is_emri_no    text,
    rev           int,
    model         text,                                    -- açık planın kodu
    kural         jsonb NOT NULL DEFAULT '{}',             -- {ogeler, okunamayan_n, olumsuz_n}
    llm           jsonb NOT NULL DEFAULT '{}',             -- {ogeler, okunamayan_n[, hata: true]}
    sinif         text NOT NULL,                           -- aynı | farklı | yalnız_llm | yalnız_kural | ikisi_de_okuyamadi | ikisi_de_bos
    cagri         int  NOT NULL DEFAULT 0,
    girdi_token   int  NOT NULL DEFAULT 0,
    cikti_token   int  NOT NULL DEFAULT 0,
    etiket        text,                                    -- insan: kural | llm | ikisi | hicbiri
    olusturuldu   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (mesaj_id)
);
CREATE INDEX IF NOT EXISTS okuma_kiyaslari_zaman ON okuma_kiyaslari (olusturuldu);
