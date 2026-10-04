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
- Beklenen tek fark: sır taramasında `vps/kapi_d_dogrula.sh:25`. Başka FARKLI varsa iş kapanmaz; kaynağını bul.
- Harness sonucu (22/22), referans (AYNI), pytest (N geçti) sayılarını not et.

## 3. Bağımsız inceleme (iki hakem + hazır inceleme)
- `/code-review` koş; bulguları doğruluk etkisine göre ayır (düzeltilecek / isteğe bağlı).
- `motor/`, `is_emri/` ya da `beyin/varyant.py` değiştiyse **geometri-hakemi** subagent'ını diff üstünde koştur.
- Her kapanışta **kvkk-denetcisi** subagent'ını diff ve yeni dosyalar üstünde koştur; bulgu varsa maskele.
- Düzeltme gerekiyorsa yap, 2. adımı tekrarla.

## 4. Kanıt ve belge
- İş emri belgesinin **Kanıt** bölümüne tarih-saat, komut ve sonuç satırlarını yaz (BK-01 biçimi). "Çalışıyor" yalnız bu satırlarla yazılır.
- `DURUM.md`: dosyanın başına tarihli bir ek paragraf (dal, iş kodu, yapılan, gerileme sonucu, sınırlar, bekleyen onay). Bu dal `main` dışındaysa "ie-NN birleşirken bu paragraf elle taşınır" notunu koru.
- Pencere dolmak üzereyse `docs/devir/<tarih>_<kod>.md` devir notu yaz (nerede kalındı, sıradaki adım, bilinen tuzaklar).

## 5. Commit ve push
- Kimlik: `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit`. Mesaj Türkçe, ilk satır `<KOD>: <ne yapıldı>`; sonuna oturumun verdiği Co-Authored-By ve Claude-Session satırları.
- Kanıt commit'i ayrı olabilir ("<KOD> kanıtı ve DURUM").
- `git push -u origin <iş dalı>`. **main'e push ve merge yok.**

## 6. PR ve özet
- `gh` varsa taslak PR aç: `gh pr create --draft --base main --title "<KOD> · <başlık>" --body-file <geçici dosya>`; yoksa karşılaştırma bağlantısını yaz (`https://github.com/lokmansayim/portman-v2private/compare/main...<dal>`).
- Lokman'a 6 satırlık özet: ne değişti, kanıt sayıları, inceleme bulguları, kalan riskler, onayını bekleyen şeyler, sıradaki iş. Son cümle: **"main'e birleştirme senin onayınla."**
