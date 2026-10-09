# Portman

PortatifEv bayi talebi → **Beyin** (LLM anlar, kod karar verir) → **Motor** (İş Emri → DXF/PDF, doğrulama) → ön onay → (sonra) BOM / fiyat / teklif.
Kanal: WhatsApp (444 80 56) üzerinden; tek sunucuda (VPS) Python: webhook kuyruğa alır (Postgres), ajan üretir, gönderici gönderir, panel gösterir (İE-06, D-05). Canlıdaki akış Kapı 8'e kadar eski yol (hosting PHP + eski VPS, v1.3): `DURUM.md`.

Uzlaşılan mimari (22 Eylül 2026): **LLM anlar → kod karar verir → Motor çizer → insan onaylar.** Ayrıntı: `docs/notlar/`.

## Dizinler
| Dizin | İçerik |
|---|---|
| `motor/` | Geometri çekirdeği (`geometry.py`: 125,5 cm pano aksı, duvar/pano/açıklık), çizim (`dxf_out.py`), doğrulama (`validate.py`), katalog/BOM, **`cikarici.py`** (katalog DXF → İş Emri) |
| `beyin/` | LLM çıkarım (`llm.py`), şema (`sema.py`), görüşme durumu (`konusma.py`), kural/karar katmanı (`karar.py`), varyantlar (`varyant.py`), katalog (`veri/katalog_37_proje.json`), test koşumu (`harness.py`, `testler/`) |
| `is_emri/` | Elle kodlanmış İş Emri şablonları (P6001, ALTIN 6×8, Yan Verandalı 6×8,5) |
| `kanal/` | Kanal (VPS, Python): `webhook.py` (Meta webhook, `/saglik`), `meta_api.py` (imza, Graph API), `gonderici.py` (gönderim, medya), `panel.py` (yönetim paneli), `worker.py` + `kalici.py` (işleme, Postgres kuyruğu), `depo.py`, `goc/` (yalnız ekleyen göçler), `ayarlar.py`, `tests/e2e_vps_kanal.py` |
| `vps/` | Sunucu betikleri: `kurulum.sh`, `guncelle.sh`/`geri_don.sh` (etiketli sürüm, geri dönüş), `agent.py`, `sir_koy.py`, `panel_parola.py`, `yedek*.sh`, `nabiz.sh`, `durum.sh`, `kuru_kosu.sh`, `ayar.sh`; `systemd/`, `nginx/`, `sshd/`, `fail2ban/`. `kapi_*` ve `pg_kurulum.sh` tarihli kayıttır |
| `ref_katalog/` | Kaynak katalog çizimleri: `TEK_KAT_PREFABRIK_PLANLARI.dxf` (16 plan), P6001/P7001/P8501 tek dosyalar + PNG |
| `ref_yan/` | Yan verandalı 6×8,5 referans projesi (DXF, BOM sayımı, yükleme listesi) |
| `docs/` | Araştırma raporu, Astra değerlendirmesi, yol haritası, kanal kurulum/geri alma ve canlı kanıt |
| `KARARLAR.md` | Karar günlüğü (tarih, karar, gerekçe, geçersiz kılan) |

Depoda **olmayanlar**: sırlar (API anahtarları, WhatsApp erişim belirteci ve app secret, panel parolası, telefon numaraları; VPS'te `/etc/portman/*.env`), üretilen çıktılar (`cikti/`, VPS'te `/opt/portman/data`), 150 MB'lık `Guncel_Sablon_2024.dxf` (Lokman'ın klasöründe).

## Çalıştırma (yerel)
```
bash araclar/ortam_kur.sh                             # sanal ortam + paketler + yerel Postgres 16 (--dogrula: harness, referans, bütün testler)
venv/bin/python -m beyin.harness                      # Beyin kural katmanı: 22 vaka (kayıtlı LLM çıkarımlarıyla; LLM çağrısı yok)
venv/bin/python -m motor.cikarici ref_katalog/P6001.dxf --kod P6001 --sablon is_emri/P6001_2plus1_6x6.json --motor
venv/bin/python -m motor.cikarici ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf --secici P9401 --motor
PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python3 kanal/tests/e2e_vps_kanal.py   # uçtan uca: sahte Meta, gerçek Motor
```

## Sürüm / ortam
VPS (Natro, Ubuntu 24.04, tek sunucu): nginx 443 → gunicorn (webhook 8081, panel 8082), systemd servisleri (webhook, agent, gonderici, panel), Postgres 16 yerel, sürümler `/opt/portman/surumler/<etiket>`; kurulum ve güncelleme `vps/kurulum.sh`, `vps/guncelle.sh` (`docs/is_emirleri/IE-06.md`). Hosting'te yalnız web sitesi (Kapı 13'ten sonra).
Kural kaynağı: prefabrik çizim kuralları v1.4.3 (Ubeydullah ile kural tablosu çıkarılacak).
