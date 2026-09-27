# Bilinen hatalar · B1 ve B2

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
| B2 | 1) "P6001 aynalı olsun" 2) 3,5 saat sonra "P6001 yatak odası 1 penceresi 120x180 olsun" (LLM niyeti `revizyon`) | `degistir` | aynasız yeni İş Emri ya da soru | aynalı İş Emri, revizyon 2 (hata) |

**B1 (kritik).** Kural katmanı bayinin kendi sözüne yalnız LLM "ekle" dediğinde bakıyor (`beyin/karar.py`, pencere döngüsü). İşlem boş ya da "degistir" gelince pencere sessizce değişiyor. Düzeltme İE-02'de yapılacak; iki kontrol vakası düzeltmenin fazla soru sordurmadığını sınar.

**B2 (karar Lokman'ın).** Görüşme durumunda zaman aşımı yok (`beyin/konusma.py`). LLM bir mesajı "revizyon" sayarsa eski taslak kaç saat önce kalmış olursa olsun devam ediyor. Seçenekler (DURUM.md, 23.09): (a) böyle kalsın, (b) taslak N saat sonra kapansın, (c) model koduyla başlayan mesaj yeni talep sayılsın. Test (b) ve (c)'nin ortak sonucunu sınar: uzun aradan sonra, model koduyla başlayan mesajda eski varyant sessizce devralınmaz. Sistemin sorması da kabul edilir. (a) seçilirse test silinir.

Kaynak: DURUM.md (23 Eylül 00:35), canlı test 22.09 22:33–38.
