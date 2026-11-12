# Portman Yazım Kuralı · Sade Teknik Türkçe (D-70; Lokman, 8 Kasım 2026)

Bu dosyanın yolu yoktur; her oturumda yüklenir. Codex ve öteki ajanlar bu dosyayı `AGENTS.md` › Yazım kuralı'ndan gelip elle okur. Metin Lokman'ın 8 Kasım 2026 14:20 UTC mesajındaki kuraldır. Tek fark rapor şablonunun dördüncü satırıdır (aşağıda). Karar: `KARARLAR/D-70.md`. Notion: Kurulum Panosu satır 176.

- **Kaynak:** ASD-STE100 (Simplified Technical English, Issue 9, Ocak 2025) ilkelerinden uyarlanmıştır. Resmi metin değildir.
- **Kapsam:** Lokman'a raporlar, bayi mesajları, bayi rehberi, montaj rehberi. Kod ve commit mesajları hariç.

## Kelime

1. Bir kavram = tek terim. Portman Sözlüğü'ndeki terimi kullan; eş anlamlı üretme. Sözlük: `docs/portman_sozlugu.md` (D-81; Lokman'ın seçimleri 11 Kasım 2026). Sözlükte olmayan kavramda mevcut kural dosyalarındaki terimi kullan; yeni terim yalnız Lokman'ın sözüyle girer.
2. Bir kelime = tek anlam. Aynı kelimeyi iki farklı şey için kullanma.
3. Belirsiz kelime yok: "biraz, yaklaşık, uygun şekilde, gerekirse, vb." Yerine sayı, ölçü ve birim yaz.
4. Kısaltmayı ilk geçtiği yerde aç.

## Cümle

5. Bir cümle = bir iş.
6. Talimat cümlesi en fazla 15 kelime; açıklama cümlesi en fazla 20 kelime.
7. Talimatta emir kipi kullan: "Dosyayı aç." Şu değil: "Dosyanın açılması gerekmektedir."
8. Kimin yaptığı belli olsun: "Motor planı çizdi." Şu değil: "Plan çizildi."
9. Ek zinciri yok: "-ıp, -arak, -dıktan sonra, -dığı için" ile cümle uzatma; cümleyi böl.
10. Olumsuzu net yaz; çift olumsuz kullanma.

## Paragraf ve düzen

11. Paragraf tek konu, en fazla 4 cümle.
12. Sıralı işler numaralı liste; her adım tek eylem.
13. Uyarı önce gelir: risk varsa adımdan ÖNCE "DİKKAT:" satırı yaz.
14. Sayılar rakamla ve birimle: 7,50 m · 125,5 cm · 60 m² (brüt oturum).

## Lokman'a rapor şablonu (en fazla 5 satır)

- Ne yapıldı:
- Sonuç (sayıyla):
- Sorun var mı:
- Sizden ne lazım:
- Sonraki tek adım:

"Bitti" veya "geçti" demeden önce sonucu görsel olarak göster ve onay bekle.

Lokman'ın metninde dördüncü satır "Senden ne lazım:" diye geçer. Lokman'a hitap "siz"dir (proje talimatı). CIO proje talimatına da "Sizden ne lazım" diye yazdı.

## Var olan kurallarla ilişki

- Bu kural hiçbir kuralı kaldırmaz. Şu kurallarla birlikte geçerlidir: `CLAUDE.md` › Oturum başında 5 (iki cümle, tek soru), çalışma kuralları 3 ("Geçti" demez), 11 (onay açık sözdür) ve 20 (mesajda kod adı yok).
- `/kapanis` Lokman'a özeti de bu şablonla yazar. Kapanış dosyasında (`.claude/skills/kapanis/SKILL.md`) hâlâ "6 satırlık özet" yazar. Dosya korunan dosyadır; metni Lokman'ın onayıyla ayrı işte değişir. O güne kadar bu şablon geçerlidir.
- Var olan bayi mesajı şablonları, bayi rehberi ve montaj rehberi metinleri 8 Kasım 2026'da bu kurala göre yeniden yazılmadı. Onları çevirmek ayrı iştir. Bayiye giden metin bir çıktıdır: hedef örnek ve harness vakası yalnız Lokman'ın onayıyla değişir (D-02, D-28).
- Portman Sözlüğü `docs/portman_sozlugu.md`'dedir (D-81, 11 Kasım 2026). Sözlükle çelişen bugünkü metinler sözlüğün son bölümündedir; onları çevirmek de ayrı iştir.
