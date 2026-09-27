# Bilinen hatalar · B1 ve B2

Buradaki testler bugünkü kodla (v1.1.1) **başarısız olması beklenen** testlerdir. Hata düzeltildiğinde test geçer. `strict` işaretli olduğu için pytest bunu "XPASS" diye bildirir; o zaman işaret kaldırılır ve test sıradan teste döner.

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
| B2 | 1) "P6001 aynalı olsun" 2) 3,5 saat sonra "P6001 yatak odası 1 penceresi 120x180 olsun" (LLM niyeti `revizyon`) | `degistir` | soru ya da aynasız yeni İş Emri | aynalı İş Emri, revizyon 2 (hata) |

**B1 (kritik).** Kural katmanı bayinin kendi sözüne yalnız LLM "ekle" dediğinde bakıyor (`beyin/karar.py`, pencere döngüsü). İşlem boş ya da "degistir" gelince pencere sessizce değişiyor. Düzeltme İE-02'de yapılacak; iki kontrol vakası düzeltmenin fazla soru sordurmadığını sınar.

**B2 (karar sizde).** Görüşme durumunda zaman aşımı yok (`beyin/konusma.py`). LLM bir mesajı "revizyon" sayarsa eski taslak kaç saat önce kalmış olursa olsun devam ediyor. Seçenekler şunlar: (a) böyle kalsın, (b) taslak N saat sonra düşsün, (c) sistem "önceki taslağın revizyonu mu, yeni talep mi?" diye sorsun. Test (b) ve (c)'nin ortak koşulunu sınar: uzun aradan sonra eski varyant sessizce devralınmaz. (a) seçilirse test silinir.

Kaynak: DURUM.md (23 Eylül 00:35), canlı test 22.09 22:33–38.
