---
name: kapanis
description: İş emrini kapatır — doğrulama, kanıt, DURUM.md, commit/push, bağımsız inceleme ve PR özeti. Merge etmez; main'e birleştirme Lokman'ın onayıyla.
disable-model-invocation: true
argument-hint: [KOD]
---

# İş emri kapanışı: $ARGUMENTS

Kapanış, "çalışıyor" demenin kanıtını üretir. Sıra sabittir; bir adım geçmezse sonrakine geçme, nedenini söyle ve dur.

## 1. Çalışma ağacı
- `git status --porcelain`: hangi dosyalar değişti, izlenmeyen dosya var mı. İş emrinin "Değişiklik" bölümüyle karşılaştır; listede olmayan bir değişiklik varsa açıkla ya da geri al.
- Dal doğru mu (`git rev-parse --abbrev-ref HEAD` = iş dalı; `main` ise dur).

## 2. Doğrulama
- `motor/`, `beyin/` ya da `kanal/` değiştiyse **tam**: `bash araclar/ortam_kur.sh --dogrula` (~9 dk; arka planda koşturup bekleyebilirsin).
- Yalnız belge/ayar/`.claude/` değiştiyse **hızlı**: `python3 testler/referans/dogrula.py --hizli` (~45 sn) ve `bash -n` / `py_compile` zaten hook'ta.
- Beklenen fark yok: `dogrula.py` "SONUÇ: fark yok" demeli (İE-08, 12.10'dan beri `kapi_d_dogrula.sh:25` yanlış pozitifi `kos.py`'de beklenen). Herhangi bir FARKLI varsa iş kapanmaz; kaynağını bul.
- Harness sonucu (22/22), referans (AYNI), pytest (N geçti) sayılarını not et.

## 3. Bağımsız inceleme (hakem + hazır inceleme)
- `/code-review` koş; bulguları doğruluk etkisine göre ayır (düzeltilecek / isteğe bağlı).
- `motor/`, `is_emri/` ya da `beyin/varyant.py` değiştiyse **geometri-hakemi** subagent'ını diff üstünde koştur.
- Sır taraması ajanla değil, iki frenle: `sir_koruma.py` hook'u (yazımda anahtar, token, parola engeli) ve 2. adımdaki `dogrula.py` sır taraması (beklenmeyen 0). KVKK denetimi (`kvkk-denetcisi`) 28 Ekim 2026'da kaldırıldı (Patron; D-13, BK-17): kişisel veri bulgusu aranmaz, raporlanmaz.
- Düzeltme gerekiyorsa yap, 2. adımı tekrarla.

## 4. Kanıt ve belge
- İş emri belgesinin **Kanıt** bölümüne tarih-saat, komut ve sonuç satırlarını yaz (BK-01 biçimi). "Çalışıyor" yalnız bu satırlarla yazılır.
- **Üretim kuralı (D-28):** iş bir çıktıyı (çizim, liste, rehber, teklif) üretiyor ya da değiştiriyorsa üç soruyu yanıtla: çıktı `main`'e girecek tek bir komutla mı üretildi (oturum betiği ya da elle düzeltme yok); Lokman'ın onayladığı hedef örnek depoda nerede; hangi test onu CI'da kıyaslıyor. Biri "yok"sa iş kapanmaz ya da açık `KARARLAR/D-28.md` › "Bugünkü açıklar" tablosuna satır olarak yazılır.
- Durum eki: yeni dosya `docs/durum/<YYYY-MM-DD>_<HHMM>_<KOD>.md` (UTC saat; dal, iş kodu, yapılan, gerileme sonucu, sınırlar, bekleyen onay). Aynı işin önceki ekini güncelleyebilirsin; başka işin ekine ve `DURUM.md`'ye dokunma (ortak satırlar her birleşmede çakışıyordu, 28 Ekim 2026).
- Pencere dolmak üzereyse `docs/devir/<tarih>_<kod>.md` devir notu yaz (nerede kalındı, sıradaki adım, bilinen tuzaklar).

## 5. Commit ve push
- Kimlik: `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit`. Mesaj Türkçe, ilk satır `<KOD>: <ne yapıldı>`; sonuna oturumun verdiği Co-Authored-By ve Claude-Session satırları.
- Kanıt commit'i ayrı olabilir ("<KOD> kanıtı ve DURUM").
- `git push -u origin <iş dalı>`. **main'e push ve merge yok.**

## 6. PR ve özet
- Taslak PR aç: `gh pr create --draft --base main --title "<KOD> · <başlık>" --body-file <geçici dosya>` ya da GitHub MCP `create_pull_request` (`draft: true`); ikisi de yoksa karşılaştırma bağlantısını yaz (`https://github.com/lokmansayim/portman-v2private/compare/main...<dal>`). GitHub doğrulaması taslakta koşmaz (dakika, `AGENTS.md` › Değişiklik disiplini).
- Birleştirme onayı alınınca (ya da onay sorulmadan hemen önce): güncel `main`'i dala al, PR'ı hazır yap (`gh pr ready` ya da MCP `update_pull_request`, `draft: false`), "Doğrulama sonucu" yeşil olunca birleştir; kırmızıysa düzelt, birleştirme yok.
- Lokman'a 6 satırlık özet: ne değişti, kanıt sayıları, inceleme bulguları, kalan riskler, onayını bekleyen şeyler, sıradaki iş. Son cümle: **"main'e birleştirme senin onayınla."**
