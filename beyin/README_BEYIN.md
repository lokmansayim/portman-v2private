# Beyin v0.1 — talep alma katmanı ("talep → İş Emri ya da tek soru")

**Görev 1'in ilk teslimi (21 Eylül 2026).** Canlıya dokunulmadı; Claude çalışma alanında geliştirildi ve test edildi.

## Ne yapar
Kayıtlı bir bayinin WhatsApp mesajını alır → **LLM yalnız çıkarım yapar** (mesajda ne var? → `Talep` JSON, şema zorunlu, varsayım
yok) → **kural katmanı karar verir** (deterministik, gerekçeli): kayıtsız numara → yönlendirme; selam/soru/alakasız → kısa cevap;
katalog kodu → şablon İş Emri + varyantlar (ayna sol-sağ, ayna ön-arka, pencere ölçüsü) → **İş Emri**; m² → katalog önerisi
sorusu; dış ölçü/pano → grid → onaylı örnek şablonu varsa İş Emri, yoksa dürüst yönlendirme; eksik bilgi → **tek soru**
(en fazla 4 soru, 4 revizyon; sonra insana). Gönderen başına konuşma durumu tutulur (taslak, aşama, soru sayısı, revizyon, son İş Emri).

```
WhatsApp mesajı ──► llm.cikar()  ──Talep──►  karar.karar_ver()  ──► Karar {sor | is_emri | yonlendir | cevapla}
                     (LLM, şema)             (kural + konuşma durumu + katalog + varyant)        │
                                                                                     is_emri ──► motor (run.py) ──► DXF/PDF
```

## Dosyalar
| Dosya | İş |
|---|---|
| `sema.py` | `Talep` (LLM çıktı şeması, 21 alan) ve `Karar` (pydantic) — JSON Schema dışa aktarımı |
| `prompt.md` | Çıkarım talimatı (model bağımsız; Türkçe; "olmayanı doldurma") |
| `llm.py` | Adaptör: `openai_chat` (Chat Completions json_schema — hosting varsayılanı), `openai` (Responses), `anthropic` (araç çağrısı), `manuel` (test). Anahtar: parametre → ortam değişkeni → panel ayar dosyası; hiçbir yere yazılmaz. Token/süre ölçümü döner; şema hatasında tek tekrar. **Canlı anahtarla denenmedi (kanal öz-testi dener).** |
| `katalog.py` | 37 model (`veri/katalog_37_proje_v2.json`; kat, kaynak ve doğrulama alanlarıyla, D-07; dondurulmuş `katalog_37_proje.json` referans girdi olarak kalır), kod normalizasyonu (6001 → P6001, C8201 → Ç8201), m²'ye yakın model önerisi (bayi kat söylediyse yalnız o kat), kodlanmış şablonlar (`SABLONLAR`) |
| `varyant.py` | Deterministik varyantlar: `ayna(x|y)` (mahal dikdörtgenleri, pencere duvarı, menteşe, pano indeksi motordan aday sayısıyla), `pencere_degistir` |
| `konusma.py` | Gönderen başına durum (JSON dosyası; canlıda DB tablosu) |
| `karar.py` | Kural katmanı; İş Emri montajı (`talep`, `kunye`, `bina_ozellikleri`, `ozel_istekler`) |
| `harness.py` | Test koşumu: `python3 -m beyin.harness` → `testler/rapor.json` |
| `veri/bayiler.json` | Test bayi kaydı (canlıda panelin kişi/firma kaydı) |

## Test (15 mesaj, çıkarım Claude Haiku ile, kural katmanı deterministik) — 15/15 beklenen eylem
Örnekler: "P6001'in aynalanmış hali" → İş Emri (ayna_x) · "60 m² 2+1 verandalı" → P6001/P6501/P6701 önerisi · "P6001 olsun" → İş Emri ·
"6x8 pano tek katlı 2+1" → onaylı 6×8 şablonu · "fiyat?" → cevap · "onaylıyorum" → onay kaydı · "7x4 m tek oda…" → 3×5,5 pano
(3,96×7,00 m) teyidi + yönlendirme (serbest yerleşim üretici yok) · "P8501 mirror" → katalogda var, şablon kodlanmamış → yönlendirme ·
"P6001, yatak odası 1 penceresi 120x180, dış boya beyaz, çatıya OSB" → İş Emri (pencere değişti, tablo/özel istek dolu) ·
"3+1 istiyorum" → ölçü sorusu · "95 m² çelik" → Ç öneri · kayıtsız numara → yönlendirme · "6001 ön arka ters" → İş Emri (ayna_y).
Üretilen İş Emri'leri (#1 ayna_x, #9 pencere, #14 ayna_y) motor çizdi, doğrulama geçti (`03_Testler/BEYIN_*`).

## Sınırlar (v0.1)
- Şablonu kodlanmış katalog modeli yalnız P6001 (+ onaylı 6×8 ve 6×8,5 örnekleri grid eşleşmesiyle). Diğer 36 model → yönlendirme.
- Varyantlar: ayna_x, ayna_y, pencere_degistir. Ekle/kaldır, ölçü/veranda/çatı değişikliği → yönlendirme.
- Serbest yerleşim üretici yok. Kroki/PDF görseli okunmuyor (yalnız metin).
- Menteşe kuralı: her aynada el değişir (sol↔sağ) — Lokman teyidi bekler.
- Çıkarım kalitesi Haiku ile ölçüldü; üretimde kullanılacak model aynı prompt/şemayla yeniden koşulmalı.
