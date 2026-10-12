---
paths:
  - "beyin/**"
---

# Beyin kuralları (K05, K18, K21, K22, D-01, Z-08)

- **LLM anlar, kod karar verir.** `beyin/llm.py` yalnız çıkarım yapar; soru mu, İş Emri mi, yönlendirme mi kararı `beyin/karar.py`'de verilir. Mesaj başına tek LLM çağrısı, ajan döngüsü yok (K05).
- Kural, bayinin **kendi mesajını** okur, LLM özetini değil (K18). Belirsizlikte sessizce değiştirmez, sorar (K21); sözcük sınırı korunur ("bekle" ≠ "ekle").
- Harness (`beyin/harness.py`, `beyin/testler/`) eylemin yanında İş Emri içeriğini de sınar: pencere ve kapı sayısı, oda konumu (K22). 22 vaka sırayla ve değişmeden durur; yeni vaka yalnız sona eklenir; kayıtlı LLM çıkarımı olmadan vaka eklenmez. Harness `Katalog()`'u kabul kümesiz kurar: `beyin/veri/adaylar.json`'daki `gecerli` adaylar (İE-08: yedi çelik model) harness'te görünür; 22 vakanın hiçbiri alan + oda programıyla çelik adaya düşmez (vaka 2 60 m², vaka 7 dış ölçü/pano, vaka 12 oda programı yok) — yeni çelik aday eklerken bu denetlenir.
- Taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar (D-01; `beyin/konusma.py`).
- Olumsuz ya da soru biçimli kısa cevaba "Anlayamadım" bilinen pilot sınırlamasıdır; düzeltmesi İE-03'ün kapsamıdır, geçiştirilmez.
- Sırlar LLM'e ve günlüğe gitmez (`llm.py` anahtarları `[GIZLI]` yapar); mesaj metni şu an LLM'e olduğu gibi gidiyor, takma ad (Z-08) açık iştir — yeni kod bunu kötüleştirmez.
- Model geçidi arkasında birincil model Claude Opus 5.5 (Z-05); model değişikliği ücretli deneme sayılır, Lokman'ın onayıyla.
- `beyin/prompt.md` ve `beyin/sema.py` değişince harness tam koşulur; vaka sonuçları değişiyorsa iş emrinde vaka vaka yazılır.
