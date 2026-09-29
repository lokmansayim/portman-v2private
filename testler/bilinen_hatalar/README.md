# Bilinen hatalar · B1 ve B2

İkisi de `ie-02` dalında düzeltildi (28.09): B2 karar D-01 ile, B1 K18 ve K21 ilkesiyle. Testler artık sıradan test; v1.1.1'de başarısız, `ie-02`'de geçiyor.

Testler v1.1.1'de başarısız olan davranışları sabitler; `main`'e birleştirilince de geçmeleri gerekir. B2'nin ön koşulu (ilk taslağın aynalı olması) ayrı bir testte sınanır.

```
python3 -m pytest testler/bilinen_hatalar -v
python3 testler/bilinen_hatalar/test_b1_b2.py     # pytest yoksa: vakaların bugünkü sonucu
```

Testler ağa, LLM'e, WhatsApp'a ya da canlı sunucuya bağlanmaz. LLM'in çıkarımı elle verilir; konuşma durumu geçici klasörde tutulur.

## 28 Eylül sonucu

| Vaka | Bayinin sözü | LLM pencere işlemi | Beklenen | Bugün |
|---|---|---|---|---|
| B1 | "P6001, yatak odası 1, 120x180" | boş | soru | v1.1.1: İş Emri (hata) · `ie-02`: soru |
| B1 | aynı | `degistir` | soru | v1.1.1: İş Emri (hata) · `ie-02`: soru |
| B1 | "… bir tane daha 120x180 pencere ekle" | `degistir` | ekleme: Lokman'a devir | v1.1.1: pencere değişti (hata) · `ie-02`: devir |
| B1 | "P6001, yaşam alanı, 120x180" (odada 2 pencere) | boş | hangisi olduğu otomatik seçilmez: devir | v1.1.1: iki pencere birden değişti (hata) · `ie-02`: devir |
| Kontrol | aynı | `ekle` | soru | soru |
| Kontrol | "P6001 yatak odası 1 penceresi 120x180 olsun" | boş | İş Emri | İş Emri |
| B2 | 1) "P6001 aynalı olsun" 2) 3,5 saat sonra "P6001 yatak odası 1 penceresi 120x180 olsun" (LLM niyeti `revizyon`) | `degistir` | soru: yeni mi, değişiklik mi | v1.1.1: aynalı İş Emri, revizyon 2 (hata) · `ie-02`: soru |
| B2 cevabı | 2)'den sonra "yeni" | — | aynasız İş Emri, revizyon 1 | `ie-02`: aynı |
| B2 cevabı | 2)'den sonra "değişiklik" | — | aynalı İş Emri, revizyon 2 | `ie-02`: aynı |
| B2 cevabı | 2)'den sonra üç anlaşılmayan cevap | — | soru yinelenir, sonra Lokman'a devredilir | `ie-02`: aynı |
| Kontrol | 2) 1 saat sonra | `degistir` | taslağın devamı (aynalı, revizyon 2) | aynı |
| Kontrol | 2) 3,5 saat sonra ama model kodu yok: "yatak odası 1 penceresi 120x180 olsun" | `degistir` | taslağın devamı | aynı |

B2 için toplam 44 test var. Tablodakilere ek olarak şunlar sınanır: cevap biçimleri ("yeni talep", "yenisi", "önceki", "aynı proje", "P6001 yeni"); olumsuz, iki cevaplı ya da ek istekli cevapta sorunun yinelenmesi; araya giren selamdan sonra da sorulması; model kodu biçimleri ("*P6001*", "P 6001", "6001"); soru askıdayken başka model, uzun mesaj, genel soru ya da iptal gelmesi; 24 saatten eski sorunun yok sayılması. 35'i eski kodda başarısız; kalan 9'u bugünkü davranışın korunduğunu sınar.

**B1 (düzeltildi).** v1.1.1 bayinin kendi sözüne yalnız LLM "ekle" dediğinde bakıyordu; işlem boş ya da "degistir" gelince pencere sessizce değişiyordu. Artık odada tek pencere varsa LLM ne derse desin ölçüt bayinin sözüdür: değiştir → ölçü değişikliği, ekle → ekleme (v0.1'de Lokman'a devir), belirsiz → soru. Söz, pencere satırının geldiği mesajdan kaydedilir (`soz_niyeti`); sonraki bir revizyonun sözü ("ayna") eski satırı yeniden yorumlamaz. Odada birden çok pencere varsa hangisinin değişeceği otomatik seçilmez. Pencere sorusuna yalnız kısa ve saf bir "değiştir"/"ekle" cevap sayılır ve yalnız sorulan satırı çözer. Aynı oda için yeni satır gelince eski satırlar düşer (son söz geçerli). Kod `beyin/karar.py`. B1 için 23 test var; bağımsız inceleme iki tur.

**B2 (düzeltildi, D-01).** Görüşme durumunda zaman aşımı yoktu (`beyin/konusma.py`); LLM bir mesajı "revizyon" sayınca eski taslak kaç saat önce kalmış olursa olsun devam ediyordu. Karar D-01 (`KARARLAR/D-01.md`): taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar. Kod `beyin/karar.py` (`_eski_taslak_sor`), süre `beyin/konusma.py` (`ESKI_TASLAK_SN`). Testler artık sıradan test; eski kodda başarısız, yeni kodda geçiyor. İki kontrol testi fazla soru sorulmadığını sınar.

Kaynak: DURUM.md (23 Eylül 00:35), canlı test 22.09 22:33–38.
