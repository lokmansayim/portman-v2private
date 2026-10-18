# AIPrefabrik mühür denetimi (BK-12 adım 0)

Tarih: 18 Ekim 2026, 05:05–05:10 UTC. Dayanak: BK-12 planı, adım 0 (Patron onayı 17 Ekim 09:48). Kişi, firma ve bayi adı yazılmaz; projeler AP kodlarıyla (13 Ekim mühür kaydındaki klasör adlarının düz sırası: AP-01 ilk klasör; adlı eşleme yalnız Mac'te).

## Sonuç

- **Mac'teki klasör 13 Ekim mührüyle bayt bayt aynı.** 28 klasör, 61 dosya (58 PDF, 3 Excel); SHA'sı değişen 0, eksik 0, yeni 0. Klasör ve dosya adları da 13 Ekim'deki gibi.
- Hiçbir dosya açılmadı. Mac'te yalnız `sha256sum` ve `stat` koşuldu; dosya içeriği ekrana, buluta ya da depoya gelmedi.
- **Kör test kümesi değişmedi:** kör 19 (AP-06, AP-09, AP-11…18, AP-20…28), listesi kapalı ama kör sayılmayan AP-10 (≈ PK-03). Listesi açık 8: AP-01…05, AP-07 (TS-01), AP-08 (PK-07), AP-19 (PK-01).
- **AP-22:** Drive'daki kopyada klasör adı Mac'tekinden farklı; Mac'teki ad 13 Ekim'deki gibi. Dosyalar aynı; AP kodu değişmez.
- **Yeni: 28 DWG yalnız Drive'da.** 17 Ekim 08:40–09:26 UTC arasında Drive'daki `AIPrefabrik` klasörüne her projeye birer R10 montaj DWG'si eklendi (mühendisin hesabından; başka dosya türü eklenmedi). Mac'te ve 13 Ekim mühründe yoklar. Bunlar liste değil çizimdir (montaj paftasının kaynağı).
  - Patron'un kararı (18 Ekim 05:09, kart "İlk kullanımda"): DWG'ler şimdi Drive kimliği, bayt ve yükleme saatiyle kaydedilir. SHA-256, her DWG model için ilk indirildiğinde alınır ve bu dosyaya eklenir. Bayt ya da Drive'daki değiştirme saati tutmazsa dosya kullanılmaz, Patron'a yazılır.

## Yöntem ve sağlama

1. Patron klasörü 18 Ekim 05:03'te Mac'te bağlı `Claude Portman Çalışması` altına taşıdı.
2. Mac'te her dosya için `sha256sum` ve `stat -c %s`; adlı liste Mac'te kalır, depoya ve paylaşılan klasöre girmez. Oturumlara açık klasörün dışına taşınması Patron'a önerildi (18 Ekim, CIO kıyası).
3. İki özet iki yanda ayrı hesaplandı ve aynı çıktı:
   - yol + SHA (NFC, sıralı `sha\tyol` satırları): `c1b773edbb07d6bcd0b2d59efc9ed7857fbaeda948ae00ee163ef97f7d95e6a0`
   - yalnız SHA (sıralı): `edbc9844fcdbeecd3838deecff4eb7a0e842153a811662fb50670c704eb8d85c`
4. Aşağıdaki maskeli tablo Mac'te üretildi (özet `b8f7b980…`, 12 haneli SHA önekiyle), bulutta 13 Ekim mührünün tam SHA'larıyla birleştirildi; 61 önekin her biri tek bir mühür satırına denk geldi, AP kodu 61/61 tuttu.

Patron'a öneri (05:08): mühür bittiği için klasörü Masaüstüne geri taşımak; listesi kapalı projeler yeniden bütün oturumların dışında kalır.

## Dosyalar (Mac, 61)

| AP | # | Tür | Uzantı | Bayt | SHA-256 | 13 Ekim'le |
|---|---|---|---|---|---|---|
| AP-01 | 1 | detay | .pdf | 169.762 | `28e22eecf1968171438fd380a776fc1c0bc7c88bc7874d0ed5bf3a47a85eae7c` | aynı |
| AP-01 | 2 | detay | .pdf | 162.678 | `f6d8d10d1a54c1d7773b077f2699d6f6ef1b3ea74a1eadba18206ae6bb66c981` | aynı |
| AP-01 | 3 | montaj paftası | .pdf | 1.409.307 | `517871cb77e2d4d7d673935f9976dba343d124bce823ef51d59458025e69c831` | aynı |
| AP-01 | 4 | yükleme listesi | .pdf | 192.433 | `042fab25db1f856370997bcb39d36835e2becb6ecaa55c3c767380cfd0be9c8e` | aynı |
| AP-01 | 5 | yükleme listesi | .xlsx | 29.728 | `2daaf8cb9e86bf351c0b693162a6f1aeb55bdd7e9ec3da30d1b59c217257b9ae` | aynı |
| AP-02 | 1 | montaj paftası | .pdf | 1.395.976 | `3f55b892434052fdfca8360cabe168db6919ec83da68d7920259e3f9034f0c49` | aynı |
| AP-02 | 2 | yükleme listesi | .pdf | 238.790 | `b2174de293292b5bf9b1a1562655115d7314e8bb012ffcecf3f866e58f4bedaf` | aynı |
| AP-03 | 1 | montaj paftası | .pdf | 1.372.866 | `f9174ddf3ff27e972f2c0e31417a088edaacbe101079b6859244b46ad02072c8` | aynı |
| AP-03 | 2 | yükleme listesi | .pdf | 233.027 | `6af9731912e0653fb286be0574d814131134806ccd7e6e2739bd9628a6890b88` | aynı |
| AP-04 | 1 | montaj paftası | .pdf | 1.695.946 | `d5918f3916e587d26900982a34057226e33817a3d44592ef65638fa54466af88` | aynı |
| AP-04 | 2 | yükleme listesi | .pdf | 239.957 | `11c49f7853adf6862c62b063c399311adc679f9618667c02dce30b2d766e722f` | aynı |
| AP-05 | 1 | montaj paftası | .pdf | 1.350.592 | `5ef593d3e43e32cbed349f7cf173564a3c4964b1983c37b687c0a38c37fbdd40` | aynı |
| AP-05 | 2 | yükleme listesi | .pdf | 223.320 | `2f037a78e30fdca9e5b99ad3f607a700f04b25e208aee46de0d3427d2121c6ae` | aynı |
| AP-06 | 1 | montaj paftası | .pdf | 1.795.627 | `b41deeb521ff559413874d60c656ccac23d5f8c82c3bb39d9b3f2ac22856398e` | aynı |
| AP-06 | 2 | yükleme listesi | .pdf | 232.767 | `8104f0298e6d80f6c639c9367a1e42cf35e248971179c1d0c03c38cfd7745691` | aynı |
| AP-07 | 1 | montaj paftası | .pdf | 1.515.620 | `631976212db7a4ae6d353c815aff82b06a4cfe7670caac522bf92100915860b7` | aynı |
| AP-07 | 2 | yükleme listesi | .pdf | 234.421 | `dcfd289b1db17ff9ada64309b27e28569bcf503ac7defe964d34fbaafd8c20b4` | aynı |
| AP-08 | 1 | montaj paftası | .pdf | 1.572.896 | `a819c0f1c0bdd150930b71d2762773c8a6513f19f6bf1539407dab1077441b71` | aynı |
| AP-08 | 2 | yükleme listesi | .pdf | 240.638 | `985c3a209bd736eb68fe46cab9964569ca85b41ab7cb8cfb68fe29af7ce78086` | aynı |
| AP-09 | 1 | montaj paftası | .pdf | 1.634.746 | `24faae19f68bf2728bb0b74a83393f73ae9588113ad4f721914a47fbd5344520` | aynı |
| AP-09 | 2 | yükleme listesi | .pdf | 176.407 | `b51874749775ee07d5ebab5fda596eb9c704db49fda7185d6918d0cc299c8da5` | aynı |
| AP-10 | 1 | montaj paftası | .pdf | 1.410.723 | `d4ec815ea6293383cefeb0a2e71bbf905d9207ec0b93a44957c962c75691a713` | aynı |
| AP-10 | 2 | yükleme listesi | .pdf | 200.798 | `4d55b361c2bbc97eef777d03a068c1cc5edb4e55d2e3b1c6565e3debabb2a812` | aynı |
| AP-11 | 1 | montaj paftası | .pdf | 1.296.197 | `39080728d4059d360cb454f5fc306f34c604e72a0ae8d07e427afc4528dd8947` | aynı |
| AP-11 | 2 | yükleme listesi | .pdf | 192.733 | `317f6a74387aa9a576c0c050960fbf513c7de1f7a88111c35cfb101698ad9c7d` | aynı |
| AP-12 | 1 | montaj paftası | .pdf | 1.187.013 | `370703cf5b861019b05f14587050caee9bbdea28bececbd23149c9203dcea797` | aynı |
| AP-12 | 2 | yükleme listesi | .pdf | 232.344 | `89fe8d529aef5a8dcb2b0ed25678663d3eafbac05069585e69267dd6d0f87060` | aynı |
| AP-13 | 1 | montaj paftası | .pdf | 1.563.033 | `8476c6c529f63f3d64621f5eb12876e3ace6e997018b12a91416434cab2e495a` | aynı |
| AP-13 | 2 | yükleme listesi | .pdf | 245.860 | `f676aa3f1dcaad04654bbaeb084fb6dfc74bfcb1e9048fad9d04521567906fe1` | aynı |
| AP-14 | 1 | montaj paftası | .pdf | 1.270.458 | `c46b277bdd3874ebd8475d2620278d1e440198ea40009a00b4dc99b2394f3b1a` | aynı |
| AP-14 | 2 | yükleme listesi | .pdf | 236.890 | `a55033adbf63642d5a5a47eac19724f51766f53554a7a2fd16edb7d561ace2fd` | aynı |
| AP-15 | 1 | montaj paftası | .pdf | 1.250.141 | `88a02fcd1c9a2a1b3e2be894950f62c1509acc0c664de61193f4ff23457fb47d` | aynı |
| AP-15 | 2 | yükleme listesi | .pdf | 250.892 | `a8fb316b2e8aac04bba8f897ea9f7402f03432c2ef2f16486c49286d63ae8724` | aynı |
| AP-16 | 1 | montaj paftası | .pdf | 1.254.646 | `ce7c05acb09eeaf3eadf3da645c5c24a75c2f02157bd06679ef1c2d4f347e5fd` | aynı |
| AP-16 | 2 | yükleme listesi | .pdf | 239.623 | `3e8ad249871f4e495d460e2d93c54faec9770b6456c9d79760601659e025cd8c` | aynı |
| AP-17 | 1 | montaj paftası | .pdf | 2.483.506 | `ed75e88727d2fa45c6d4e0e8f263db33d615dff2e43b6808a24e13446ad73d2a` | aynı |
| AP-17 | 2 | yükleme listesi | .pdf | 222.642 | `4aa3c0e2f0f765830505768bcfcf1302ed9bf6c3d9f2107439d7bd9d6b9f8afa` | aynı |
| AP-18 | 1 | montaj paftası | .pdf | 1.383.036 | `daa7b84ca5456de3d239b3fe67bfc9cb8fc69816442f56e476692f9dc4eed0a1` | aynı |
| AP-18 | 2 | yükleme listesi | .pdf | 229.567 | `52a6494c673e9adba86269f1fa360ad95eb2187e443b4f12a38bd6af60c8c010` | aynı |
| AP-19 | 1 | detay | .pdf | 103.696 | `6b481fbc2387aa172a955da960d44c15a8d0fd196fac9357120750e293b2700e` | aynı |
| AP-19 | 2 | detay | .pdf | 84.506 | `a380647080280982bbede9cd72725eeb9e4101badacbb64d1606bb0f2addc3f1` | aynı |
| AP-19 | 3 | montaj paftası | .pdf | 1.272.880 | `492c76133da0e66a6dce82ebaa67e3f9da9949eb314c1034445d223faaac658d` | aynı |
| AP-19 | 4 | yükleme listesi | .xlsx | 196.855 | `17e43b888bd1a5dd5bfb06ebb38b620b1b0c3708c176a35d7ea576f1e948d106` | aynı |
| AP-20 | 1 | montaj paftası | .pdf | 1.835.051 | `18d3f654c207a18df2184681bdd9ce9a714da9fbcd76b8e9e37eabbfacba9d23` | aynı |
| AP-20 | 2 | yükleme listesi | .xlsx | 45.641 | `29caed98c826c241055a6be8c3d9168aefe21800621f44a1feb807478e567477` | aynı |
| AP-21 | 1 | montaj paftası | .pdf | 1.282.128 | `98b0c0acae5d1b550294cbc233d29cc8b3806a9fd7a3a3036bfcc7387a6a1522` | aynı |
| AP-21 | 2 | yükleme listesi | .pdf | 233.771 | `71d0f698ae51cd7f9257374b0c91d44657be2763cef0d170fe2b480863dcd737` | aynı |
| AP-22 | 1 | montaj paftası | .pdf | 1.311.519 | `c0df06e23fb4866cff686ef5251b477101a9050cb1a1ccd7c695d55045058530` | aynı |
| AP-22 | 2 | yükleme listesi | .pdf | 232.216 | `379c4fb14d4abaa04c780a1148fb4652c2b42b4a6989e55063ee3bf18959f981` | aynı |
| AP-23 | 1 | montaj paftası | .pdf | 933.403 | `d9ce06538c17ac8c70835d1f999622dcc03f480265cc6d3ac39fd5319cd65dfc` | aynı |
| AP-23 | 2 | yükleme listesi | .pdf | 145.195 | `7abb57e4ea90bd7e242bd593b2c793cdf96d717507af7ec5f896c4b022b08223` | aynı |
| AP-24 | 1 | montaj paftası | .pdf | 889.870 | `d3ff0cb4bd52cbef6863aba9135b3c708c4c580f94ad46c3f8c46ff8cfe034df` | aynı |
| AP-24 | 2 | yükleme listesi | .pdf | 159.213 | `40934fd0cec22709119bf1c558f52be1e4093aaba81f3603745c5df05c715e56` | aynı |
| AP-25 | 1 | montaj paftası | .pdf | 1.397.844 | `4e272f02243e46459b93dd9c29b869b25070dcb73cb10dde3a342bcd8cd851ed` | aynı |
| AP-25 | 2 | yükleme listesi | .pdf | 230.427 | `1fb37530d24494cbc56c183ac11c6105d81ca68bdaa25530e3d343e93cdbc430` | aynı |
| AP-26 | 1 | montaj paftası | .pdf | 1.554.594 | `a2546b338839b51f0249cb42002c7496f0773aa483b6e117de088a28764a735e` | aynı |
| AP-26 | 2 | yükleme listesi | .pdf | 246.526 | `6d9b40e64634aa11beed47269642b61d1a6fe04c5958ada7bcb1e8a7e50302dc` | aynı |
| AP-27 | 1 | montaj paftası | .pdf | 2.248.093 | `8446af572368a1ad96007f40c865f26903de07130d4f0340835c7d75c575e2b6` | aynı |
| AP-27 | 2 | yükleme listesi | .pdf | 236.224 | `dc0ebc6924a41c4a566112cf195667544c3ff944fa1db5b0a05a30d6fb0787dc` | aynı |
| AP-28 | 1 | montaj paftası | .pdf | 1.501.639 | `d958ed0b9433ace76be6f4340ad10faffb7591f81ce2ed3c2338d57c5d37cd7d` | aynı |
| AP-28 | 2 | yükleme listesi | .pdf | 230.923 | `169b60a7087f8cc2db4835b38640a40b35e76ed3cda19989e784a4cca04491a6` | aynı |

## Yeni DWG'ler (Drive, 28; SHA ilk indirmede)

Yükleme saati 17 Ekim 2026, UTC. Drive kimliği yalnız sahibinin oturumuyla açılır.

| AP | Tür | Bayt | Drive'a yükleme | Drive kimliği | SHA-256 |
|---|---|---|---|---|---|
| AP-01 | montaj DWG (R10) | 2.718.647 | 08:40:14 | `16uRm-4G2wcLDBdHUXBMJ_sjL57-uVp5U` | ilk indirmede |
| AP-02 | montaj DWG (R10) | 2.035.408 | 08:43:02 | `1ZLv6NWczFfC0OvCiREgqmXzS_WmmoXHU` | ilk indirmede |
| AP-03 | montaj DWG (R10) | 1.424.355 | 08:44:00 | `1g9zllLH-XA7r3BGM5d6M1r96U0e3ZQj5` | ilk indirmede |
| AP-04 | montaj DWG (R10) | 2.201.072 | 08:44:56 | `14JS7G4mz1wNSJUi2Y15I0yJyVeqt9dAs` | ilk indirmede |
| AP-05 | montaj DWG (R10) | 2.947.482 | 08:46:02 | `1QpotaibSf95iG_WIwrQ-IsThs1J2q_t5` | ilk indirmede |
| AP-06 | montaj DWG (R10) | 2.531.052 | 08:46:58 | `1aUjKNZKDH9kEYp4xw2UrAYtvE3czkGAm` | ilk indirmede |
| AP-07 | montaj DWG (R10) | 3.054.198 | 08:48:35 | `1FZ567pVMGTYL1y7BZCU3Ih3VPWENqisI` | ilk indirmede |
| AP-08 | montaj DWG (R10) | 3.594.901 | 08:49:26 | `18JJHEduzg-xLKmlYnAyg1CZp0rzYNsVo` | ilk indirmede |
| AP-09 | montaj DWG (R10) | 5.080.662 | 08:52:01 | `1_FIIjdQcq1I_EF0sPBPAVsd1O6KpC3HG` | ilk indirmede |
| AP-10 | montaj DWG (R10) | 2.259.674 | 08:53:32 | `1TykQZEOvE8NeUte5iPAu7x9egTNr5DWj` | ilk indirmede |
| AP-11 | montaj DWG (R10) | 3.619.012 | 08:54:39 | `1GdSliUgUlsSFRM8_FPslelU6mK_6we6o` | ilk indirmede |
| AP-12 | montaj DWG (R10) | 4.045.331 | 09:12:36 | `1dc_dYO98UnswmWGnxu-boqv3kjN3Di3p` | ilk indirmede |
| AP-13 | montaj DWG (R10) | 8.340.446 | 08:56:41 | `1KzFIfIL-0BAh4e1hVvIA5nZHkyd3QrUp` | ilk indirmede |
| AP-14 | montaj DWG (R10) | 3.371.819 | 08:58:03 | `1pPX1qIysAbUzK_LfAD40ajumUpIXTsu9` | ilk indirmede |
| AP-15 | montaj DWG (R10) | 8.755.678 | 08:59:07 | `1mawirnxYi-w2ZdWbzxt3-_ccLPqkQjmW` | ilk indirmede |
| AP-16 | montaj DWG (R10) | 5.297.182 | 09:00:09 | `1xZokHaQREIw15FrzpYNno4mcOeyxvy8M` | ilk indirmede |
| AP-17 | montaj DWG (R10) | 2.674.423 | 09:08:47 | `1RausG57OgVU7Ogt313vYGGy04sh_MLcu` | ilk indirmede |
| AP-18 | montaj DWG (R10) | 2.862.973 | 09:11:16 | `10eDNValLl4dMB2xz3eqfNjdmniMJ4hO7` | ilk indirmede |
| AP-19 | montaj DWG (R10) | 2.121.217 | 09:13:38 | `1N5ybAQMNFJziQbIucL1w65_4HZQ9ODTv` | ilk indirmede |
| AP-20 | montaj DWG (R10) | 2.452.494 | 09:14:29 | `1ZmH-ZSoNKZRfxqv-1ejFiIO52MCO9IDI` | ilk indirmede |
| AP-21 | montaj DWG (R10) | 2.695.535 | 09:16:41 | `1wcLhw3IhMxm8gedhqHGujlARnzuWCY2l` | ilk indirmede |
| AP-22 | montaj DWG (R10) | 2.779.302 | 09:17:40 | `1g2Q-KMkJNiiNuzg5QEwLB0HQjFdkTfIL` | ilk indirmede |
| AP-23 | montaj DWG (R10) | 2.609.507 | 09:20:36 | `1hOOajoUq-5WHp6INoZwoxCgyeDa8ItRX` | ilk indirmede |
| AP-24 | montaj DWG (R10) | 1.953.080 | 09:21:17 | `1_5jzJ8B2hReqAe5rhW6fjCa9ubWSe7SB` | ilk indirmede |
| AP-25 | montaj DWG (R10) | 2.773.679 | 09:22:16 | `1VPF5iNIXhcaxUYliXbZJHWR1alfu7leM` | ilk indirmede |
| AP-26 | montaj DWG (R10) | 9.679.182 | 09:25:07 | `1mDEP4a4LEMr0PPUw7TFYxeqW1mmrMRbG` | ilk indirmede |
| AP-27 | montaj DWG (R10) | 10.539.165 | 09:24:19 | `1cAez_jiOgoOy1e71E2Uej50GWwEP3TvM` | ilk indirmede |
| AP-28 | montaj DWG (R10) | 8.555.109 | 09:25:53 | `1QrEiCidGkrd3TjL0H5BmKSzModVWAWKz` | ilk indirmede |
