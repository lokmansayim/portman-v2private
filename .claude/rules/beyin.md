---
paths:
  - "beyin/**"
---

# Beyin kuralları (K05, K18, K21, K22, D-01, Z-08)

- **LLM anlar, kod karar verir.** `beyin/llm.py` yalnız çıkarım yapar; soru mu, İş Emri mi, yönlendirme mi kararı `beyin/karar.py`'de verilir. Mesaj başına tek LLM çağrısı, ajan döngüsü yok (K05).
- Kural, bayinin **kendi mesajını** okur, LLM özetini değil (K18). Belirsizlikte sessizce değiştirmez, sorar (K21); sözcük sınırı korunur ("bekle" ≠ "ekle").
- Harness (`beyin/harness.py`, `beyin/testler/`) eylemin yanında İş Emri içeriğini de sınar: pencere ve kapı sayısı, oda konumu (K22). 22 vaka sırayla ve değişmeden durur; yeni vaka yalnız sona eklenir; kayıtlı LLM çıkarımı olmadan vaka eklenmez. Harness `Katalog()`'u kabul kümesiz kurar: `beyin/veri/adaylar.json`'daki `gecerli` adaylar (İE-08: yedi çelik model) harness'te görünür; 22 vakanın hiçbiri alan + oda programıyla çelik adaya düşmez (vaka 2 60 m², vaka 7 dış ölçü/pano, vaka 12 oda programı yok) — yeni çelik aday eklerken bu denetlenir. Ayrıca `secenek.uygun_adaylar` yapı türü "çelik" denmedikçe çelik adayı süzer: "88 m² 2+1" (tür yok) prefabrik dalında kalır, çelik seti yalnız "çelik" sözüyle ya da kodla (Ç8801, KT-01) açılır (geometri hakemi 12.10; `test_celik_akisi.py`).
- Taslak 2 saatten eskiyse ve mesaj model koduyla başlıyorsa sistem sorar (D-01; `beyin/konusma.py`).
- **Çelik revizyonu (İE-08 A4):** değişiklik bayinin kendi sözünden okunur (`beyin/celik_okuma.py`; LLM'in pencere/varyant alanları yalnız ipucu); pencere için aday 0 → soru, 1 → uygula, 2 → görselli "1 / 2 / Hiçbiri", ≥ 3 → numaralı soru; olumsuz/soru biçimi belirsizdir. Değişiklik tanıma uygulanabildiği karar anında denenir (`varyant.tanim_uygula`; olmazsa yönlendirme), aynı projede birikir (`yapi.degisiklikler`). Çelikte soru bütçesi (MAX_SORU) revizyon başınadır; prefabrik B1 makinesi çelikte koşmaz. `prompt.md` ve `sema.py` değişmedi (harness 22/22).
- Olumsuz ya da soru biçimli kısa cevaba "Anlayamadım" bilinen pilot sınırlamasıdır; düzeltmesi İE-03'ün kapsamıdır, geçiştirilmez.
- Sırlar LLM'e ve günlüğe gitmez (`llm.py` anahtarları `[GIZLI]` yapar); mesaj metni şu an LLM'e olduğu gibi gidiyor, takma ad (Z-08) açık iştir — yeni kod bunu kötüleştirmez.
- Model geçidi arkasında birincil model Claude Opus 5.5 (Z-05); model değişikliği ücretli deneme sayılır, Lokman'ın onayıyla.
- `beyin/prompt.md` ve `beyin/sema.py` değişince harness tam koşulur; vaka sonuçları değişiyorsa iş emrinde vaka vaka yazılır.
