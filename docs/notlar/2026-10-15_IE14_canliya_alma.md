# İE-14 · canlıya alma ve Patron kartıyla deneme (15 Ekim 2026)

Görev 6d. Komutları Lokman Mac'inden, depo klasöründe koşar; çıktılar dosyaya yazılır ve Claude'a verilir. Asistan sunucuya bağlanmaz.
Sırayla gidilir; bir adımın beklenen sonucu gelmezse durulur, çıktı paylaşılır.

## 0 · Önce: `main`'e birleştirme (Lokman'ın onayı)

- `main` `d3c8e58` canlı deneme için eksik. Dalda ondan sonra şu commit'ler var:
  - `f97b47b`: mühendis mesajına doğrulama satırı (karar 1, "canlıdan önce");
  - `44986b2`: revizyonda uygulanamayan istek planı kapatmaz (T4 → T5);
  - `94576eb`: `vps/ie14_kontrol.sh`;
  - `3bc3244`: değmeyen cepheye istenen pencere yalnız kendini düşürür (T3);
  - `ea4b5b9`: şemaya uymayan işlem (ör. çatı "L") yalnız kendini düşürür (T4);
  - `1136f05`: kontrol betiğinde KVKK düzeltmesi;
  - `5827812`: geometri hakemi bulguları — aynı mesajdaki bilgi düşmez, işlemler tek tek denenir (T3).
- `d3c8e58` etiketlenirse T4 "çatı L olsun" konuşmayı yönlendirmeyle kapatır, T5 "Onaylanacak açık bir plan görünmüyor" der.
- Öneri: dalın PR'ı açılır, Lokman birleştirir, etiket birleştirme commit'ine atılır.
- Mac'te depo güncellenir: `git checkout main && git pull`.

## 1 · Ön kontrol (salt okunur; ücret yok)

```
ssh portman-vps 'timeout 120 bash -s' < vps/ie14_kontrol.sh > ie14_1_on_kontrol.txt 2>&1
ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/durum.sh' > ie14_1_durum.txt 2>&1
```

Beklenen (`ie14_1_on_kontrol.txt`):
- kurulu sürüm `v2026.10.14b`, sağlık `200`;
- `şema 6`, `açık iş 0`, `bekleyen giden 0`;
- `plan_uretimleri: yok`, `okuma_kiyaslari: yok`;
- aktif kartlar yalnız iki satır: Patron (`patron · PATRON · …dddd`) ve prova kartı; `aktif kart toplam 2`. Kod `PATRON`, `TEST`
  ya da `B` + 4 hane değilse `(özel kod)` görünür (elle yazılmış kod ad taşıyabilir; KVKK denetimi B1);
- `plan_uretimi: null`, `llm_once_revizyon: null` (bu sürümde anahtar yok).

`durum.sh`'de son yedeğin tarihi görülür. Göçler yalnız ekler (007 tablo ve sütun, 008 tablo); ayrı yedek gerekmez.

## 2 · Canlıya alma (sunucu değişikliği; ücret yok)

Etiket (Mac):

```
git fetch origin && git checkout main && git pull
git tag -a v2026.10.15 -m "İE-14 talepten plana (14a tek kat çelik), D-18; mühendis doğrulama satırı" origin/main
git push origin v2026.10.15
```

Kurulum (`setsid`; `timeout` yok, yarıda kesilirse geri dönüş koşmaz):

```
ssh -n portman-vps "setsid nohup bash -c 'bash /opt/portman/guncel/vps/guncelle.sh v2026.10.15; echo == çıkış \$?' > /root/guncelle_v2026.10.15.txt 2>&1 < /dev/null &"
ssh -n portman-vps 'tail -40 /root/guncelle_v2026.10.15.txt' > ie14_2_surum.txt 2>&1
```

Son satır `== çıkış …` değilse iş sürüyordur; bir dakika sonra ikinci komut yinelenir. Beklenen:
- `genel motor: AYNI …` ([3c]);
- `uygulanan göçler: [7, 8]` ([4/7]);
- `sağlık: sürüm v2026.10.15, Postgres bağlı` ([6/7]);
- `== bitti: v2026.10.15 etkin` ve `== çıkış 0`.

Sonra:

```
ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ie14_kontrol.sh' > ie14_3_sonra.txt 2>&1
```

Beklenen: sürüm `v2026.10.15`, sağlık `200`, `şema 8`, iki tablo `var, 0 satır`, `plan_uretimi: {"acik": false, …}`,
`llm_once_revizyon: {…}` (içinde `mod` yok: kapalı).

## 3 · Ayar (canlı değişiklik; ücret yok)

```
ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh plan_uretimi "{\"acik\": true}"' > ie14_4_ayar.txt 2>&1
```

Servisler ayarı her turda okur; yeniden başlatma gerekmez. Çıktıda `plan_uretimi` içinde `"acik": true` görünmeli.

## 4 · Deneme (ücretli; Patron kartıyla)

Patron kartında bayiye gidecek her mesaj Patron'a gelir, sonuna `— teknik: …` satırı eklenir. Yönlendirme metni
"Bu talep şu an otomatik karşılanamıyor (Patron modu: ayrıca bildirim gönderilmez)." olur; Lokman'a ayrıca bildirim gitmez.

| Adım | Patron yazar | Gelmesi gereken | LLM |
|---|---|---|---|
| T1 | `95 m² 3+1 tek kat çelik` | Önce tek satır: "95 m² 3+1 çelik için bankamızda uyan hazır model yok. Sizin için yeni bir plan taslağı hazırlıyorum; birkaç dakika sürebilir." Sonra seçenek seti: "2 yeni plan taslağı çizdim; bankadaki en yakın model de yanında…" — 1. Yeni plan ve 2. Yeni plan (TASLAK, programdan çözüldü; yerelde 8,6 × 11,05 m ve 10,45 × 9,1 m, beşik çatı, Salon - Mutfak + 3 yatak + banyo + hol), 3. bankadan en yakın (yerelde KT-03, 94 m², 2+1) ve düğmeler | 1 (çıkarım; plan üretimi LLM'siz) |
| T2 | düğme **1. Yeni plan** | r01: plan görseli, TASLAK PDF, "Ön onay planınız hazır…" ve düğmeler | 0 |
| T3 | `salonu 50 cm büyüt, mutfağa 120x120 pencere ekle` | r02: "Uygulanan: dış ölçü … → …; Salon - Mutfak 31,8 → 34,4 m² (ya da 35,3); … ; pencere eklendi: Salon - Mutfak 120/120." Önce–sonra görseli ve PDF | 2 (çıkarım + işlem okuması) |
| T4 | `çatı L olsun` | "\"çatı L olsun\" isteğini otomatik uygulayamadım; planınız aynen geçerli. Başka bir değişiklik isterseniz yazın; planı onaylıyorsanız Onayla'ya basın." Yeni çizim yok | 2 |
| T5 | düğme **Onayla** | "Onayınız kaydedildi (…, revizyon 2). Plan teknik kontrole gönderildi; sonucu size bildireceğiz." | 0 |

T3'te salonun hangi yana büyüyeceğini mesaj söylemiyor; yönü LLM seçer. Olasılıklar (T1'in 1. planında yerelde denendi):
- ön ya da sol: ikisi de uygulanır (beklenen);
- arka: büyütme "komşu başka hizada … otomatik büyütemedim" diye yazılır, pencere uygulanır;
- sağ: salon o yanda iç duvara bakıyor; büyütme Hol ile Yatak Odası 3 arasındaki kapıyı sığmaz kılar. İşlemler tek tek denenir: pencere uygulanır, mesajda "\"salonu 50 cm büyüt: Hol ile Yatak Odası 3 arasındaki ortak duvar kapıya yetmiyor\" isteğini otomatik uygulayamadım." yazar; konuşma açık kalır.
- Pencere salonun değmediği bir cepheye yazılırsa o istek "… cepheye değmiyor" diye yazılır, büyütme uygulanır. LLM'e giden tabloda salonun dış cepheleri (ön, sol) yazılı.
- İki istek de uygulanamazsa: "… isteğini otomatik uygulayamadım; planınız aynen geçerli." T4 ve T5 yine çalışır. Konuşmayı kapatan tek yol, tek tek denendiğinde de hiçbir işlemin kurallara uymaması: "İsteğinizi kurallara uyan bir plana otomatik çeviremedim…". O zaman T4–T5 için T1'den yeniden başlanır (+1 LLM).

Mühendis doğrulama satırı (karar 1) Patron kartında koşmaz: onay kancası yalnız bayi ve prova kartında çalışır. Canlıda görmek için ayrı
bir deneme gerekir: prova kartı, aktif mühendis kartı ve ücretli bir şablon mesajı.

### Gölge okuma (tek mesaj; ücretli)

Gölge okuma yalnız banka modelinin revizyonunda koşar; T5'ten sonra bir banka planı açılır:

1. Patron yazar: `Ç8801K` → r01 (1 LLM).
2. Gölge açılır:
   `ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh llm_once_revizyon "{\"mod\": \"golge\"}"' > ie14_6_golge_ac.txt 2>&1`
3. Patron yazar: `dış duvarlar 140 olsun` → r02, "Uygulanan: dış duvarlar 140'lık …". Karar kuralındır; LLM okuması yalnız
   kayda gider, bayiye bir şey eklemez. 2 LLM (çıkarım + gölge).
4. Gölge kapanır:
   `ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ayar.sh llm_once_revizyon "{\"mod\": \"kapali\"}"' > ie14_7_golge_kapat.txt 2>&1`

### Ücret (tahmin)

- LLM: yaklaşık 8 çağrı (T1 1, T3 2, T4 2, Ç8801K 1, gölge 2). Onay ve seçim düğmeyle yapılırsa 0; yazıyla yapılırsa her biri +1.
- WhatsApp: yaklaşık 15–18 giden mesaj (T1 2–3, T2 3, T3 3, T4 1, T5 1, Ç8801K 3, gölge 3). 1 Ekim'den beri servis mesajları da ücretli; tutar
  o günkü Meta Türkiye utility tarifesinden okunur.

## 5 · Son kontrol ve karar

```
ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ie14_kontrol.sh deneme 90' > ie14_5_deneme.txt 2>&1
```

Beklenen:
- işler `bitti`;
- T1 satırında `plan 0`, T3 ve T4 satırlarında `düzenleme 1`, gölge satırında `gölge 1`;
- `plan_uretimleri` 1 satır: `gecerli · cozucu · … · YENI-… · PE-…`;
- `okuma_kiyaslari` 1 satır: `Ç8801K · r1 · aynı · 1`; sınıf `aynı` değilse not alınır, hata değildir;
- `açık iş 0`, `bekleyen giden 0`.

Sonra birlikte karar: `plan_uretimi.acik` açık mı kalsın (pilot bayiler bundan sonra uyan modeli olmayan talepte yeni plan alır;
LLM yalnız revizyonda ve son basamakta), `llm_once_revizyon` kapalı kalsın mı (karar 2: pilotla ve ücret onayıyla açılır).
