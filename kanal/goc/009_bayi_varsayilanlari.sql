-- İE-20 PR-2 · 009: bayi kartının talep formu varsayılanları (Kurulum Panosu satır 61). Talep formu (WhatsApp Flow) bu değerlerle
-- seçili açılır; bayi değiştirebilir. Panelden (bayi kartı) yazılır. Kartın kendisi (bayiler) değişmez: göç 004'teki ilke, standartlar
-- ayrı tabloda. Boş alan = varsayılan yok (formda sabit varsayılan: prefabrik, tek kat, beşik çatı, veranda önde).
-- YALNIZ EKLER; her ifade tekrar koşulabilir. Uygulandıktan sonra bu dosya değiştirilmez.

CREATE TABLE IF NOT EXISTS bayi_varsayilanlari (
    numara       text PRIMARY KEY REFERENCES bayiler(numara),
    yapi_turu    text CHECK (yapi_turu IN ('prefabrik', 'celik')),
    kat_sayisi   int  CHECK (kat_sayisi IN (1, 2)),
    cati         text CHECK (cati IN ('besik', 'tek_egimli', 'kirma', 'teras')),
    veranda      text CHECK (veranda IN ('on', 'yan', 'arka', 'kose')),
    guncellendi  timestamptz NOT NULL DEFAULT now()
);
