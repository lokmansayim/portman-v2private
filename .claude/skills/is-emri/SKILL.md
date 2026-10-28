---
name: is-emri
description: Yeni iş emri açar — dal, docs/is_emirleri/<KOD>.md belgesi ve plan; onay için durur. Kullanım /is-emri <KOD> <başlık> (ör. /is-emri BK-03 Hook sertleştirme).
disable-model-invocation: true
argument-hint: <KOD> <başlık>
---

# İş emri aç: $ARGUMENTS

Sen Portman'ın geliştiricisisin; sahibi Lokman kod yazmaz. Bu komut yeni bir iş emrini **planlar**, uygulamaz. Hiçbir kaynak dosyayı değiştirme; yalnız iş emri belgesini yaz.

## Adımlar

1. **Kodu ve dalı belirle.** `$ARGUMENTS`'ın ilk sözcüğü koddur: `İE-NN` ürün işi, `BK-NN` bakım. Dal adı küçük harf ve tire ile: `ie-NN-kisa-ad` ya da `bk-NN-kisa-ad`. Kod daha önce kullanılmışsa (`ls docs/is_emirleri` ve `KARARLAR/README.md › Numara defteri`; öteki dallardaki numaralar yalnız defterde görünür) dur ve sor. Alınan kod deftere aynı commit'te yazılır.
2. **Temeli seç.** Varsayılan `main`. Üstüne kurulacağı açık bir iş dalı varsa (`docs/durum/`'daki en yeni eklerde yazan aktif iş) onu söyle ve nedenini yaz; `git fetch` sonrası `git checkout -b <dal> origin/<temel>`.
3. **Kapsamı oku.** `docs/durum/`'daki en yeni ekler (açık iş dallarındakiler dahil), `KARARLAR/README.md`'nin "Açık kararlar" bölümü ve ilgili `.claude/rules/` dosyası. Bu iş bir açık karara dayanıyorsa önce o kararın Lokman tarafından verilmesi gerekir; belgede "Önce karar gerekir" diye yaz ve dur.
4. **Belgeyi yaz:** `docs/is_emirleri/<KOD>.md`, `docs/is_emirleri/BK-01.md` biçiminde:
   - Başlık: `# <KOD> · <başlık>`; dal, temel commit, onay satırı ("Onay: Lokman, <tarih> (plan)").
   - **Amaç** — neyi, neden; neyin değişmeyeceği.
   - **Kullanıcı adımları** — Lokman'ın gözüyle ne değişecek, tablo (#, adım, beklenen). Durum sözcükleri: Çalışmıyor / Kısmen / Yerelde çalışıyor / Canlıda çalışıyor.
   - **Değişiklik** — dosya dosya, kısa.
   - **Kapsam dışı** — bilerek yapılmayacaklar.
   - **Sınırlar** — canlı, veri, sunucu, ücret, silme: her biri için "yok" ya da "Lokman'ın onayıyla".
   - **Kabul koşulu** — hangi test/kanıt geçince kapanır (harness, referans, pytest, insan kabulü).
   - **Kanıt** — şimdilik boş; `/kapanis` doldurur.
5. **Planı sun.** Belgeyi özetle (5–8 satır, Türkçe), riskleri ve senin kararını bekleyen noktaları ayrı listele. Şu cümleyle bitir: **"Plan hazır, onayını bekliyorum."** Onay gelmeden uygulamaya geçme.

## Kurallar

- Belgede sır (anahtar, parola, token) olmaz.
- Plan 1 oturumda bitmeyecek kadar büyükse ikiye böl ve ikinci parçayı "sonraki iş emri" diye yaz.
- Lokman'ın onayı "evet/başla/onaylıyorum" gibi açık bir cümledir; sessizlik onay değildir.
