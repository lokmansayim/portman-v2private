# Hosting'teki panel dosyaları (kayıt için)

Bu klasördeki dosyalar hosting'te canlıdır. Depoya 29.09'daki Opus 5.5 geçişinden sonra, izlenebilirlik için alındı. Portman paketinin parçası değildir; hosting'e elle yüklenir.

Hash'ler Codex'in Mac'e bıraktığı kopyalardan hesaplandı. Hosting'teki canlı dosyaların hash'i yalnız Codex'in geçici betiğinin çıktısında (`19_Devir_Opus/hosting-dogrulama.json`) görüldü; asistan bağımsız okumadı.

| Depo yolu | Hosting yolu | SHA-256 (29.09) |
|---|---|---|
| `developer/ai.php` | `public_html/developer/ai.php` | `9a8af6f27e97fbed85b18abdf4f13ffa3891db6578d5b285e2532fdd125a33a2` |
| `portman_app/claude_api.php` | `portman_app/claude_api.php` | `fe10b695b942356c2b0896e16a5f5072b920040360c4cf7c9f0ae0a9a70a32b8` |

- `ai.php`: bayi sohbet botu. Yalnız `openaiSor` değişti; artık `claude_api.php`'deki `portmanClaudeSor`'u çağırıyor. Önceki sürüm `93111a58…`; yedeği Lokman'ın Mac'inde, `19_Devir_Opus/yedek/ai.before.php`.
- `claude_api.php`: Claude Messages API adaptörü. Model `claude-opus-5-5`, `max_tokens` 4096, `effort` low. Anahtarı web kökünün dışındaki `portman_app/claude_api.json` dosyasından okur (0600).
- **`claude_api.json` depoya girmez; anahtar içerir.**
- `tests/claude_api_test.php`: sahte cevaplarla adaptör testi, API çağrısı yok. `testler/kalici/test_llm_opus.py` bu testi PHP 8.2.30 ve 8.4 ile koşar.
