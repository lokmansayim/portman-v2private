# Portman

PortatifEv bayi talebi → **Beyin** (LLM anlar, kod karar verir) → **Motor** (İş Emri → DXF/PDF, doğrulama) → ön onay → (sonra) BOM / fiyat / teklif.
Kanal: WhatsApp (444 80 56) üzerinden; hosting PHP webhook kuyruğa alır, Python işçisi üretir, PHP gönderir.

Uzlaşılan mimari (22 Eylül 2026): **LLM anlar → kod karar verir → Motor çizer → insan onaylar.** Ayrıntı: `docs/notlar/`.

## Dizinler
| Dizin | İçerik |
|---|---|
| `motor/` | Geometri çekirdeği (`geometry.py`: 125,5 cm pano aksı, duvar/pano/açıklık), çizim (`dxf_out.py`), doğrulama (`validate.py`), katalog/BOM, **`cikarici.py`** (katalog DXF → İş Emri) |
| `beyin/` | LLM çıkarım (`llm.py`), şema (`sema.py`), görüşme durumu (`konusma.py`), kural/karar katmanı (`karar.py`), varyantlar (`varyant.py`), katalog (`veri/katalog_37_proje.json`), test koşumu (`harness.py`, `testler/`) |
| `is_emri/` | Elle kodlanmış İş Emri şablonları (P6001, ALTIN 6×8, Yan Verandalı 6×8,5) |
| `kanal/` | Canlı kanal: `feature.php` (webhook yakalama + gönderim), `worker.py` (Python üretici), `api.php` (VPS işçisi için hosting API'si), `install/`, `tests/` |
| `ref_katalog/` | Kaynak katalog çizimleri: `TEK_KAT_PREFABRIK_PLANLARI.dxf` (16 plan), P6001/P7001/P8501 tek dosyalar + PNG |
| `ref_yan/` | Yan verandalı 6×8,5 referans projesi (DXF, BOM sayımı, yükleme listesi) |
| `docs/` | Araştırma raporu, Astra değerlendirmesi, yol haritası, kanal kurulum/geri alma ve canlı kanıt |
| `KARARLAR.md` | Karar günlüğü (tarih, karar, gerekçe, geçersiz kılan) |

Depoda **olmayanlar**: sırlar (API anahtarı, WhatsApp erişim anahtarı, telefon numaraları), `kanal/state.json`, `kanal/durum/`, üretilen çıktılar (`cikti/`), 150 MB'lık `Guncel_Sablon_2024.dxf` (Lokman'ın klasöründe).

## Çalıştırma (yerel)
```
python3 -m venv venv && venv/bin/pip install ezdxf==1.4.4 pymupdf==1.26.0 shapely pydantic numpy pillow
venv/bin/python -m beyin.harness                      # Beyin kural katmanı: 15 mesaj
venv/bin/python -m motor.cikarici ref_katalog/P6001.dxf --kod P6001 --sablon is_emri/P6001_2plus1_6x6.json --motor
venv/bin/python -m motor.cikarici ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf --secici P9401 --motor
php kanal/tests/offline_test.php <lib.php yolu>       # kanal PHP tarafı (30 test)
```

## Sürüm / ortam
Hosting: PHP 8.2, Python 3.11 (venv), LVE 1 GB. VPS (Natro XCloud Pro, Ubuntu 24.04): Python işçisi (`kanal/api.php` üzerinden iş alır).
Kural kaynağı: prefabrik çizim kuralları v1.4.3 (Ubeydullah ile kural tablosu çıkarılacak).
