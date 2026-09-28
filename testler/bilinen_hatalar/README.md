# Bilinen hatalar · B1 ve B2

B2, `ie-02` dalında düzeltildi (karar D-01, 28.09); B1 açık.

Buradaki testler bugünkü kodla (v1.1.1) **başarısız olması beklenen** testlerdir. Hata düzeltildiğinde test geçer. `strict` işaretli olduğu için pytest bunu "XPASS" diye bildirir; o zaman işaret kaldırılır ve test sıradan teste döner. İşaretler yalnız beklenen davranış farkını (AssertionError) kabul eder; kurulum hatası testi düşürür. B2'nin ön koşulu (ilk taslağın aynalı olması) ayrı bir testte sınanır.

```
python3 -m pytest testler/bilinen_hatalar -v     # xfail = hata sürüyor
python3 testler/bilinen_hatalar/test_b1_b2.py     # pytest yoksa: vakaların bugünkü sonucu
```

Testler ağa, LLM'e, WhatsApp'a ya da canlı sunucuya bağlanmaz. LLM'in çıkarımı elle verilir; konuşma durumu geçici klasörde tutulur.

## 28 Eylül sonucu

| Vaka | Bayinin sözü | LLM pencere işlemi | Beklenen | Bugün |
|---|---|---|---|---|
| B1 | "P6001, yatak odası 1, 120x180" | boş | soru | İş Emri (hata) |
| B1 | aynı | `degistir` | soru | İş Emri (hata) |
| Kontrol | aynı | `ekle` | soru | soru |
| Kontrol | "P6001 yatak odası 1 penceresi 120x180 olsun" | boş | İş Emri | İş Emri |
| B2 | 1) "P6001 aynalı olsun" 2) 3,5 saat sonra "P6001 yatak odası 1 penceresi 120x180 olsun" (LLM niyeti `revizyon`) | `degistir` | soru: yeni mi, değişiklik mi | v1.1.1: aynalı İş Emri, revizyon 2 (hata) · `ie-02`: soru |
| B2 cevabı | 2)'den sonra "yeni" | — | aynasız İş Emri, revizyon 1 | `ie-02`: aynı |
| B2 cevabı | 2)'den sonra "değişiklik" | — | aynalı İş Emri, revizyon 2 | `ie-02`: aynı |
| B2 cevabı | 2)'den sonra üç anlaşılmayan cevap | — | soru yinelenir, sonra Lokman'a devredilir | `ie-02`: aynı |
| Kontrol | 2) 1 saat sonra | `degistir` | taslağın devamı (aynalı, revizyon 2) | aynı |
| Kontrol | 2) 3,5 saat sonra ama model kodu yok: "yatak odası 1 penceresi 120x180 olsun" | `degistir` | taslağın devamı | aynı |

B2 için toplam 44 test var. Tablodakilere ek olarak şunlar sınanır: cevap biçimleri ("yeni talep", "yenisi", "önceki", "aynı proje", "P6001 yeni"); olumsuz, iki cevaplı ya da ek istekli cevapta sorunun yinelenmesi; araya giren selamdan sonra da sorulması; model kodu biçimleri ("*P6001*", "P 6001", "6001"); soru askıdayken başka model, uzun mesaj, genel soru ya da iptal gelmesi; 24 saatten eski sorunun yok sayılması. 35'i eski kodda başarısız; kalan 9'u bugünkü davranışın korunduğunu sınar.

**B1 (kritik).** Kural katmanı bayinin kendi sözüne yalnız LLM "ekle" dediğinde bakıyor (`beyin/karar.py`, pencere döngüsü). İşlem boş ya da "degistir" gelince pencere sessizce değişiyor. Düzeltme İE-02'de yapılacak; iki kontrol vakası düzeltmenin fazla soru sordurmadığını sınar.

**B2 (düzeltildi, D-01).** Görüşme durumunda zaman aşımı yoktu (`beyin/konusma.py`); LLM bir mesajı "revizyon" sayınca eski taslak kaç saat önce kalmış olursa olsun devam ediyordu. Karar D-01 (`KARARLAR/D-01.md`): taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar. Kod `beyin/karar.py` (`_eski_taslak_sor`), süre `beyin/konusma.py` (`ESKI_TASLAK_SN`). Testler artık sıradan test; eski kodda başarısız, yeni kodda geçiyor. İki kontrol testi fazla soru sorulmadığını sınar.

Kaynak: DURUM.md (23 Eylül 00:35), canlı test 22.09 22:33–38.
