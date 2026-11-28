"""İE-38 (D-87) · Aday havuzu: AIPrefabrik'teki tek katlı evler bayiye giden seçenek setinde. LLM'siz, Postgres'siz.

Lokman, 13 Kasım 2026 21:41 UTC: "AIPrefabrik ve AICelik tüm prefabrik ve çelikleri veri tabanına al … yarın kalktığımızda whatsapp'tan
bayi talebi geldiğinde tüm projeler yer alsın". Bir ev havuza ancak proje kartı hakeminden geçerse girer (`araclar/havuz_hakemi.py`);
hedef değerler proje kartı veri setinden (`testler/havuz/proje_kartlari.json`, PR #145). Kayıt ev başına bir dosya (`beyin/veri/havuz/`);
görünürlük K-A10 kabul kaydıyla (kabulsüz yol, harness dahil, aynen).
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin import secenek as S  # noqa: E402
from beyin.katalog import ADAYLAR_PREFABRIK_JSON, HAVUZ_DIR, SABLON_DIR, Katalog, havuz_kayitlari  # noqa: E402
from test_celik_revizyon_karar import Sohbet  # noqa: E402

D87 = (KOK / "KARARLAR" / "D-87.md").read_text(encoding="utf-8")

# D-87 › Havuza giren prefabrik evler: kod → (proje, kaynak İş Emri, oda programı, brüt m²; D-49 `bina_brut_cm2`, tam sayıya yuvarlı)
EVLER = {
    "PA09": ("AP-02", "testler/kor/projeler/AP02/is_emri.json", "2+1", 64.0),
    "PA10": ("AP-04", "testler/kor/projeler/AP04/is_emri.json", "3+1", 95.0),
    "PA11": ("AP-06", "testler/kor/projeler/AP06/is_emri.json", "3+1", 91.0),
    "PA12": ("AP-11", "testler/kor/projeler/AP11/is_emri.json", "3+1", 85.0),
    "PA13": ("AP-12", "testler/kor/projeler/AP12/is_emri.json", "4+1", 143.0),
    "PA14": ("AP-13", "testler/kor/projeler/AP13/is_emri.json", "2+1", 60.0),
    "PA15": ("AP-16", "testler/kor/projeler/AP16/is_emri.json", "2+1", 70.0),
    "PA16": ("AP-17", "testler/kor/projeler/AP17/is_emri.json", "2+1", 80.0),
    "PA17": ("AP-18", "testler/kor/projeler/AP18/is_emri.json", "3+1", 91.0),
    "PA18": ("AP-19", "testler/motor/veri/PK01.json", "2+1", 60.0),
    "PA19": ("AP-21", "testler/kor/projeler/AP21/is_emri.json", "2+1", 84.0),
    "PA20": ("AP-24", "testler/kor/projeler/AP24/is_emri.json", "2+1", 64.0),
    "PA21": ("AP-25", "testler/kor/projeler/AP25/is_emri.json", "3+1", 80.0),
    "PA22": ("AP-26", "testler/kor/projeler/AP26/is_emri.json", "2+1", 102.0),
    "PA23": ("AP-05", "testler/kor/projeler/AP05/is_emri.json", "2+1", 49.0),     # verandasız (D-87 › Veranda, 14 Kasım)
    "PA24": ("AP-27", "testler/kor/projeler/AP27/is_emri.json", "2+1", 77.0),     # verandasız
    "PA25": ("AP-14", "testler/kor/projeler/AP14/is_emri.json", "2+1", 61.0),     # oda programı Lokman'ın kartından (14 Kasım 07:50)
    "PA26": ("AP-08", "testler/havuz/is_emirleri/AP08.json", "2+1", 71.0),        # Lokman'ın 08:16 düzeltmesi, 08:29 kartı
    "PA27": ("AP-07", "testler/havuz/is_emirleri/AP07_PAFTA.json", "1+1", 45.0),  # sundurma ikinci cumba (PC-38), 08:55 kartı; salonun ön
                                                                                   # dış duvarı paftadaki gibi (15 Kasım 2026 09:42:35 kartı)
}
# D-91 › Havuza giren standart hâller (dış duvardaki özel panolar standart panoya; hakemin standart hâl kipi): ayrıntı test_havuz_standart_pano.py
D91 = (KOK / "KARARLAR" / "D-91.md").read_text(encoding="utf-8")
STANDART_HAL = {
    "PA28": ("AP-07", "testler/havuz/is_emirleri/AP07_STD45.json", "1+1", 46.0),  # en yakın standart, 45,70 m² (Lokman 09:58:53 kartı)
    "PA29": ("AP-07", "testler/havuz/is_emirleri/AP07_STD40.json", "1+1", 40.0),  # kısalt, 39,61 m² (Lokman 10:01:43)
}
# D-92 › Kısa parça silinmiş hâller (BK-31 hakeminin silme hâli kipi; Lokman'ın ev kartları "Doğru, yanına eklensin"): kaynak evin yanına
# yeni numarayla; ayrıntı test_havuz_silme_kayit.py
SILME_HAL = {
    "PA30": ("AP-11", "testler/havuz/is_emirleri/PA12_SILME.json", "3+1", 83.0),  # 85 m² sağ duvar 26,5 cm (20:05:33 kartı)
    "PA31": ("AP-13", "testler/havuz/is_emirleri/PA14_SILME.json", "2+1", 59.0),  # 60 m² ön duvar ve veranda 15 cm (20:09:12)
    "PA32": ("AP-16", "testler/havuz/is_emirleri/PA15_SILME.json", "2+1", 69.0),  # 70 m² ön duvar ve veranda 20 cm (20:14:50)
    "PA33": ("AP-01", "testler/havuz/is_emirleri/PA08_BUYUME.json", "3+1", 142.0),  # 140 m² büyüyen hâl (20:22:14 sözü, 20:25:45)
    "PA34": ("AP-27", "testler/havuz/is_emirleri/PA24_BUYUME.json", "2+1", 78.0),   # 77 m² büyüyen hâl (20:35:43 sözü, 20:38:43)
    "PA35": ("AP-08", "testler/havuz/is_emirleri/PA26_UCLU_H.json", "2+1", 69.0),   # 71 m² üçlü H'lı hâl (20:46:54 sözü, 20:57:28; BK-34)
    "PA36": ("AP-19", "testler/havuz/is_emirleri/PA18_GENIS.json", "2+1", 62.0),   # 60 m² veranda duvarı aksta (15 Kasım 07:24:23; BK-35)
    "PA44": ("AP-05", "testler/havuz/is_emirleri/PA23_BUYUME.json", "2+1", 49.0),  # 49 m² tam panolu hâl, 700 × 700,25 (16 Kasım 06:58:39)
}
# D-96 › Havuza uygulama (İE-40 PR-7): iç duvarı 100'lük evlerin veranda köşesinde üçlü H, ev ev kartla (Lokman 15 Kasım 2026 07:32:42 sözü).
# 91 m² 3+1 yeni numarayla (07:57:38 "Doğru, yanına eklensin"; PA-11 aynen); 143 m² 4+1 paftadaki gibi aynı numarayla (07:57:47 "Evet, havuzda
# yenilensin"). Ayrıntı test_havuz_uclu_h.py
D96 = (KOK / "KARARLAR" / "D-96.md").read_text(encoding="utf-8")
UCLU_H_HAL = {
    "PA37": ("AP-06", "testler/havuz/is_emirleri/AP06_UCLU_H.json", "3+1", 91.0),   # 91 m² üçlü H'lı hâl (07:57:38)
}
UCLU_H_YENI = {"PA13": "testler/havuz/is_emirleri/AP12_UCLU_H.json"}                # 143 m² paftadaki üçlü H (07:57:47)
# D-92 › 95 m²'nin asıl hâli geri döner (İE-40 PR-10): D-103 üzerine PA-10 kör İş Emri'yle ve D-87'yle aynen; tek özel pano anahtarlı hâl
# yeni numarayla (Lokman 15 Kasım 2026 21:56:57 kartı "Evet, yeni hâl yanına girsin"). Ayrıntı test_havuz_tek_pano.py
TEK_PANO_HAL = {
    "PA38": ("AP-04", "testler/havuz/is_emirleri/AP04_D92.json", "3+1", 95.0),     # 95 m² 48 panolu hâl (14 Kasım 20:32:51; 15 Kasım 21:56:57)
}
# İE-43 PR-4b › Disk arşivi Parti 1: İş Emri paftadan kodla okundu (`araclar/hdd_turev/`), kart paftanın yazılarından
# (`testler/havuz/hdd_kartlari.json`); mavi panolar Motor'un aks düzeninde. Lokman'ın kartı karar dosyasında.
KARAR_HDD = "D-111"
DHDD = (KOK / "KARARLAR" / f"{KARAR_HDD}.md").read_text(encoding="utf-8")
HDD_EVLERI = {
    "PA39": ("HD-252", "testler/havuz/is_emirleri/HD252.json", "1+1", 37.0),     # 37 m²; oda adı yok, yatak odası eşyasız kalan oda
    "PA40": ("HD-506", "testler/havuz/is_emirleri/HD506.json", "1+1", 45.0),     # 45 m²
    "PA41": ("HD-431", "testler/havuz/is_emirleri/HD431.json", "2+1", 59.0),     # başlık 63 m², duvarlar 763 × 773 cm (58,98 m²)
    "PA42": ("HD-228", "testler/havuz/is_emirleri/HD228.json", "3+1", 84.0),     # 84 m²
    "PA43": ("HD-143", "testler/havuz/is_emirleri/HD143.json", "3+1", 92.0),     # 92 m²; verandada panel çatı, ikinci çatı PA-43-B (D-111)
}
# İE-43 PR-7 › Disk arşivi Parti 2: dört ev, çatı paftadaki gibi (D-132; 110 ve 120 m² Motor bakımını bekler)
KARAR_HDD2 = "D-132"
DHDD2 = (KOK / "KARARLAR" / f"{KARAR_HDD2}.md").read_text(encoding="utf-8")
HDD2_EVLERI = {
    "PA45": ("HD-596", "testler/havuz/is_emirleri/HD596.json", "1+1", 45.0),     # 45 m²; beşik
    "PA46": ("HD-118", "testler/havuz/is_emirleri/HD118.json", "3+1", 74.0),     # başlık 75 m², duvarlar 888,5 × 835,75 cm (74,26 m²); dörtomuz
    "PA47": ("HD-137", "testler/havuz/is_emirleri/HD137.json", "2+1", 74.0),     # başlık 76 m², duvarlar 888,5 × 835,75 cm; oda adı yok; ön cumba
    "PA48": ("HD-420", "testler/havuz/is_emirleri/HD420.json", "2+1", 80.0),     # 80 m²; verandada sundurma %10
}
# İE-43 PR-8 › Disk arşivi Parti 2'nin beklettiği iki ev: ana çatı ön verandayı da örter, veranda gövdenin açık mahali (D-134;
# Motor bakımı D-129, D-130, D-131)
KARAR_HDD3 = "D-134"
DHDD3 = (KOK / "KARARLAR" / f"{KARAR_HDD3}.md").read_text(encoding="utf-8")
HDD3_EVLERI = {
    "PA49": ("HD-380", "testler/havuz/is_emirleri/HD380.json", "3+1", 110.0),    # 110 m²; beşik, ara kolonlar 340 ve 674 cm
    "PA50": ("HD-251", "testler/havuz/is_emirleri/HD251.json", "3+1", 119.0),    # başlık 120 m², verandayla 888,5 × 1336,75 cm; dörtomuz
}
# İE-43 PR-9 › Disk arşivinin beklettiği 67 m² 2+1: beşik ana çatı ve veranda beşiğiyle (D-165; dörtomuz Motor bakımından sonra ikinci
# çatı seçeneği)
KARAR_HDD4 = "D-165"
DHDD4 = (KOK / "KARARLAR" / f"{KARAR_HDD4}.md").read_text(encoding="utf-8")
HDD4_EVLERI = {
    "PA51": ("HD-259", "testler/havuz/is_emirleri/HD259.json", "2+1", 67.0),     # 67 m²; taşan veranda 240 cm, 1 ara kolon (D-109)
}
# İE-43 PR-9 › Disk arşivinin 70 m² 3+1'i: DWG yok, montaj paftası PDF'inden elle (D-168); beşik + salonun önünde cumba
KARAR_HDD5 = "D-168"
DHDD5 = (KOK / "KARARLAR" / f"{KARAR_HDD5}.md").read_text(encoding="utf-8")
HDD5_EVLERI = {
    "PA52": ("HD-058", "testler/havuz/is_emirleri/HD058.json", "3+1", 69.0),     # paftanın başlığı 70 m², brüt 69,01; veranda gövdede (niş)
}
KARAR_HDD6 = "D-170"
DHDD6 = (KOK / "KARARLAR" / f"{KARAR_HDD6}.md").read_text(encoding="utf-8")
HDD6_EVLERI = {
    "PA53": ("HD-390", "testler/havuz/is_emirleri/HD390.json", "2+1", 69.0),     # Parti 2'nin 70 m²'si (brüt 69,01); veranda gövdede (niş), köşe kolonu sağ önde
}
HAVUZ_EVLERI = {**EVLER, **STANDART_HAL, **SILME_HAL, **UCLU_H_HAL, **TEK_PANO_HAL, **HDD_EVLERI, **HDD2_EVLERI, **HDD3_EVLERI, **HDD4_EVLERI,
                **HDD5_EVLERI, **HDD6_EVLERI}
# D-92 › Havuz evlerine uygulama: 95 m²'nin (PA-10) tek özel pano anahtarlı kaydı 15 Kasım 21:56:57 kartıyla PA-38'e geçti (TEK_PANO_HAL);
# PA-10 asıl hâline döndü (D-87, kör İş Emri). Ayrıntı test_havuz_tek_pano.py.
D92 = (KOK / "KARARLAR" / "D-92.md").read_text(encoding="utf-8")


def _kayit_kaynagi(kod: str) -> tuple[str, str, str]:
    """(kaynak İş Emri, karar, karar metni) kayıttaki gibi: D-92 evleri ve silinmiş hâlleri, D-96 üçlü H evleri, D-91 standart hâlleri,
    öteki D-87 evleri."""
    if kod in HDD_EVLERI:
        return HDD_EVLERI[kod][1], KARAR_HDD, DHDD
    if kod in HDD2_EVLERI:
        return HDD2_EVLERI[kod][1], KARAR_HDD2, DHDD2
    if kod in HDD3_EVLERI:
        return HDD3_EVLERI[kod][1], KARAR_HDD3, DHDD3
    if kod in HDD4_EVLERI:
        return HDD4_EVLERI[kod][1], KARAR_HDD4, DHDD4
    if kod in HDD5_EVLERI:
        return HDD5_EVLERI[kod][1], KARAR_HDD5, DHDD5
    if kod in HDD6_EVLERI:
        return HDD6_EVLERI[kod][1], KARAR_HDD6, DHDD6
    if kod in TEK_PANO_HAL:
        return TEK_PANO_HAL[kod][1], "D-92", D92
    if kod in UCLU_H_YENI:
        return UCLU_H_YENI[kod], "D-96", D96
    if kod in UCLU_H_HAL:
        return UCLU_H_HAL[kod][1], "D-96", D96
    if kod in SILME_HAL:
        return SILME_HAL[kod][1], "D-92", D92
    return HAVUZ_EVLERI[kod][1], *(("D-87", D87) if kod in EVLER else ("D-91", D91))
PREFABRIK = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}

# D-87 › Havuza giren çelik projeler (PR-2): kod → (proje, tanımın kaynağı, oda programı, brüt m²; genel motorun `bina_m2`'si)
CELIK = {
    "KT05": ("ÇP-06", "testler/celik/projeler/CP06/CP06.json", "2+1", 90.0),
    "KT06": ("ÇP-18", "testler/celik/projeler/CP18/CP18.json", "2+1", 90.0),
    "KT07": ("ÇP-19", "testler/celik/projeler/CP19/CP19.json", "2+1", 90.0),
    "KT08": ("ÇP-20", "testler/celik/projeler/CP20/CP20.json", "3+1", 90.0),
    "KT09": ("ÇP-08", "testler/celik/projeler/CP08/CP08.json", "2+1", 81.0),      # antette veranda yok (D-87 › Veranda, 14 Kasım)
    "KT10": ("ÇP-23", "testler/celik/projeler/CP23/CP23.json", "2+1", 82.0),      # ikinci kör küme, yalnız plan olarak (aşağıda)
    "KT11": ("ÇP-22", "testler/celik/projeler/CP22/CP22.json", "1+1", 49.0),      # ikinci kör küme, planın m²'siyle (aşağıda)
    "KT12": ("ÇP-24", "testler/celik/projeler/CP24/CP24.json", "3+1", 130.0),
    "KT13": ("ÇP-25", "testler/celik/projeler/CP25/CP25.json", "3+1", 167.0),
}
# İkinci kör küme (İE-16 PR-7): Lokman'ın 14 Kasım 2026 11:33:07 UTC kartı, çelik kör testi sohbeti; plan hakemden geçerse girer
CELIK2_KART = '"Yalnız plan olarak girsin"'
# Antetteki sayı brüt oturum değil (net, planla çelişen, yuvarlanmış): Lokman'ın 14 Kasım 2026 12:33:58 UTC kartıyla brüt planın m²'siyle
PLAN_M2_KART = '"Planın m²\'siyle girsin"'
PLAN_M2 = {"ÇP-22": (49.0, 43.2), "ÇP-24": (130.0, 140.0), "ÇP-25": (167.0, 166.0)}          # (plan_m2, antet_m2)
CELIK_KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="celik")}
ESKI_CELIK = {"Ç8801", "Ç8801K", "Ç8801L", "Ç8201", "KT01", "KT02", "KT03", "KT04"}
D80 = {f"PA0{i}" for i in range(1, 9)}
TUM_PA = D80 | {"PA06K", "PA06C"} | set(HAVUZ_EVLERI)

# D-87 › Havuza girmeyen projeler: hakemden geçmeyenler ve bulgunun başı
KALANLAR = {
    "AP-23": ("testler/kor/projeler/AP23/is_emri.json", ["oda programı"]),
    "AP-28": ("testler/kor/projeler/AP28/is_emri.json", ["dış ölçü", "brüt oturum"]),
}
# D-87 › Veranda (Lokman, 14 Kasım 2026 07:34 UTC): veranda bir oda gibi sayılır; verandasız ev de havuza girer
VERANDA_SOZU = "veranda ayrıca var mı yok mu belirtilmez verandayı da bir oda gibi kabul et"
VERANDASIZ = {"PA23", "PA24", "PA34", "PA44", "KT09", "KT11"}                   # KT-11 (ÇP-22): antette sundurma, veranda yok; PA-34 77 m² hâli; PA-44 49 m² hâli
# AP-14: paftada oda adı yok; oda programı Lokman'ın karar kartından (14 Kasım 2026 07:50:30 UTC, "Evet, 2+1 olarak girsin")
AP14_SOZU = '"Evet, 2+1 olarak girsin"'
# AP-08: Lokman 14 Kasım 2026 08:16:22 UTC düzeltmesi (hol panoları, sırt sırta kapılar, ortada pencere), 08:29:26 kartı
AP08_SOZU = "wc banyo kapısı ile yatak odası kapısı sırt sırta gelecek"
AP08_KART = '"Evet, bu çizimle girsin"'
# AP-07: Lokman 14 Kasım 2026 08:41:58 UTC ("çapraz cumba çatısını nasıl çiziyorsan öyle çiz"), 08:55:19 kartı; sundurma kartta veranda değil
AP07_SOZU = "çapraz cumba çatısını nasıl çiziyorsan öyle çiz"
AP07_KART = '"Evet, böyle doğru"'


def _standart(ie: dict) -> dict:
    ie = json.loads(json.dumps(ie))
    for anahtar in ("ozellikler", "alici_ait"):
        ie.pop(anahtar, None)
    return ie


def test_havuz_kaydi_bicimi():
    assert set(PREFABRIK) == set(HAVUZ_EVLERI)
    assert sorted(f.stem for f in HAVUZ_DIR.glob("*.json")) == sorted([*HAVUZ_EVLERI, *CELIK])  # ev başına bir dosya, ad = kod
    eski = {str(a["kod"]).upper() for a in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8"))}
    assert not eski & set(HAVUZ_EVLERI) and eski == D80                                      # D-80 kaydı aynen
    for kod, a in PREFABRIK.items():
        proje, _, oda, m2 = HAVUZ_EVLERI[kod]
        kaynak, karar, karar_metni = _kayit_kaynagi(kod)
        if kod in UCLU_H_YENI:
            assert f"| {kod[:2]}-{kod[2:]} | {proje} | `{EVLER[kod][1]}` |" in D87, kod     # havuza girdiği kaynak D-87'de aynen
        g = kod[:2] + "-" + kod[2:]
        assert a["gosterim"] == g == a["referans_model"]
        assert (a["durum"], a["yapi_turu"], a["kat"], a["oda_programi"], a["katalog_m2"]) == ("gecerli", "prefabrik", 1, oda, m2), kod
        assert a["kaynak"]["dosya"] == kaynak and a["kaynak"]["karar"] == karar and a["kaynak"]["standart"] is True
        kk = a["kaynak"]["kart_kiyasi"]
        assert (kk["kart"], kk["sonuc"]) == (proje, "geçti")
        assert kk["kart_sha256"] == HH.kartlar()[proje]["kart_sha256"]
        assert f"| {g} | {proje} | `{kaynak}` |" in karar_metni, kod                 # karar dosyası evi yazar
        disarida = a["ozet"].get("brut_disi_acik_m2", 0)                                 # girintili gövdeden taşan sundurma (PA-27)
        assert abs(a["kapali_m2"] - (a["ozet"]["brut_m2"] - a["veranda_m2"] + disarida)) <= 0.06, kod   # aday_kaydet ham brütle yuvarlar
        assert ((a["veranda_m2"] or 0) > 0) == (kk["olcum"]["veranda"] > 0), kod      # veranda bir oda gibi: kartta ne varsa (D-87 › Veranda)
        assert (SABLON_DIR / a["gorsel"]).stat().st_size > 10_000


@pytest.mark.parametrize("kod", sorted({**EVLER, **TEK_PANO_HAL}))
def test_hakem_gecer(kod):
    """Kayıttaki şablon, kaynak İş Emri'nin standart hâli ve proje kartıyla aynı (hakem yeniden koşar; Motor değişirse düşer). PA-38
    (95 m² tek özel pano anahtarlı hâli) de normal kipte kartla aynı."""
    a = PREFABRIK[kod]
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    bulgular, olc = HH.denetle(sab, HH.kartlar()[HAVUZ_EVLERI[kod][0]])
    assert bulgular == [], (kod, bulgular)
    assert olc == a["kaynak"]["kart_kiyasi"]["olcum"], kod


@pytest.mark.parametrize("kod", sorted(HAVUZ_EVLERI))
def test_sablon_kaynagin_standart_hali(kod):
    """Şablon gerçek projenin İş Emri'sidir: yalnız kimlik, talep, referans kodu ve müşterinin seçimleri (D-74 standart) değişir.
    D-91'in standart hâllerinde kaynak, standart hâlin İş Emri'si (`testler/havuz/is_emirleri/AP07_STD*.json`)."""
    kaynak = _standart(json.loads((KOK / _kayit_kaynagi(kod)[0]).read_text(encoding="utf-8")))
    sab = json.loads((SABLON_DIR / PREFABRIK[kod]["sablon"]).read_text(encoding="utf-8"))
    assert "ozellikler" not in sab and "alici_ait" not in sab
    for d in (kaynak, sab):
        for anahtar in ("is_emri_no", "revizyon", "talep"):
            d.pop(anahtar, None)
        d["yapi"].pop("referans_model", None)
    assert sab == kaynak, kod


def test_brut_alan_tek_kaynaktan():
    from motor import geometry as G, prefabrik_liste as PL
    for kod, a in PREFABRIK.items():
        plan = G.kur(json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8")))
        brut = PL.bina_brut_cm2(plan) / 1e4
        assert round(brut, 2) == a["ozet"]["brut_m2"] and float(round(brut)) == a["katalog_m2"], (kod, brut)
        assert a["veranda_m2"] == round(sum(m.alan_m2 for m in plan.mahaller.values() if m.acik), 2), kod


@pytest.mark.parametrize("proje", sorted(KALANLAR))
def test_hakemden_gecmeyen_havuzda_yok(proje):
    kaynak, kalemler = KALANLAR[proje]
    bulgular, _ = HH.denetle(json.loads((KOK / kaynak).read_text(encoding="utf-8")), HH.kartlar()[proje])
    assert [b.split(":")[0] for b in bulgular] == kalemler, bulgular
    assert proje not in {a["kaynak"]["kart_kiyasi"]["kart"] for a in PREFABRIK.values()}
    assert f"| {proje} | Hakem kaldı" in D87


def test_verandasiz_ev_havuzda():
    """Veranda bir oda gibi (Lokman, 14 Kasım 2026 07:34 UTC): verandasız prefabrik ev ve çelik proje hakemden geçip havuza girer."""
    assert VERANDA_SOZU in D87 and "| Veranda (düzeltme, 14 Kasım 2026) |" in D87 and "Kurallarla çelişen" not in D87
    assert {k for k, a in PREFABRIK.items() if not a["veranda_m2"]} | {k for k, v in CELIK.items() if not HH.celik_kartlari()[v[0]]["veranda"]} \
        == VERANDASIZ
    for kod in ("PA23", "PA24"):
        a = PREFABRIK[kod]
        assert a["veranda_m2"] == 0 and a["kaynak"]["kart_kiyasi"]["olcum"]["veranda"] == 0
        assert HH.kartlar()[EVLER[kod][0]]["veranda_adedi"] == 0
        assert "verandasız" in S.aciklama({**a, "puan": 100})                            # listede "verandasız" yazar, gizlenmez
    k = CELIK_KAYIT["KT09"]
    assert HH.celik_kartlari()["ÇP-08"]["veranda"] is False and k["kaynak"]["kart_kiyasi"]["sonuc"] == "geçti"
    for satir in ("| AP-05 | Verandasız", "| AP-27 | Verandasız", "| ÇP-08 | Antette veranda yok"):
        assert satir not in D87


def test_oda_programi_lokmanin_kartindan():
    """AP-14'ün paftasında oda adı yok: hakem oda programını yalnız Lokman'ın kartla verdiği değerden okur, değer sözüyle ve saatiyle durur."""
    kart = HH.kartlar()["AP-14"]
    ie = json.loads((KOK / EVLER["PA25"][1]).read_text(encoding="utf-8"))
    assert kart["oda_sayisi"] is None and kart["yatak_odasi"] == 0
    assert kart["oda_sayisi_lokman"]["deger"] == "2+1" and AP14_SOZU in kart["oda_sayisi_lokman"]["kaynak"]
    assert "07:50:30" in kart["oda_sayisi_lokman"]["kaynak"] and AP14_SOZU in D87 and "| PA-25 | AP-14 |" in D87
    assert HH.denetle(ie, kart)[0] == []
    sozsuz = {a: v for a, v in kart.items() if a != "oda_sayisi_lokman"}
    assert [b.split(":")[0] for b in HH.denetle(ie, sozsuz)[0]] == ["oda programı"]                 # söz olmadan kalır
    assert [b.split(":")[0] for b in HH.denetle(ie, {**kart, "oda_sayisi_lokman": {"deger": "3+1"}})[0]] == ["oda programı"]
    assert sum("oda_sayisi_lokman" in k for k in HH.kartlar().values()) == 1                           # yalnız AP-14
    assert "| AP-14 | Hakem kaldı" not in D87 and "| AP-10 | Aynı ev havuzda" in D87


def test_ap08_lokmanin_duzeltmesi():
    """AP-08 (Lokman, 14 Kasım 2026 08:16 UTC): hol ile yatak odası/WC arasındaki duvarda giriş kapısından sonra 74,75 + 62,75 + 62,75,
    WC ve yatak odası kapısı WC–yatak bölmesinin iki yanında sırt sırta, yatak odası penceresi odanın ortasında; 785 cm son panosu 74,75."""
    from motor import geometry as G
    assert AP08_SOZU in D87 and AP08_KART in D87 and "| PA-26 | AP-08 |" in D87 and "| AP-08 | İş Emri yok" not in D87
    plan = G.kur(json.loads((SABLON_DIR / PREFABRIK["PA26"]["sablon"]).read_text(encoding="utf-8")))
    hol = next(d for d in plan.duvarlar if d.yon == "y" and d.tur == "ic" and abs(d.c - 512) < 1e-6)
    bolme = next(d for d in plan.duvarlar if d.yon == "x" and d.tur == "ic" and d.p0 > 512 - 1e-6 and abs(d.c - 455.75) < 1e-6)
    boylar = [round(p.boy, 2) for p in hol.panolar]
    assert boylar == [74.75, 62.75, 62.75, 125.5, 125.5, 62.75, 40.75], boylar        # önden (giriş) arkaya
    kapilar = [p for p in hol.panolar if p.acilim is not None and p.acilim.tur == "ic_kapi"]
    assert [round(p.a1, 2) for p in kapilar][:1] == [bolme.c] and round(kapilar[1].a0, 2) == bolme.c   # bölmenin iki yanında
    assert {p.acilim.arasi[1] if p.acilim.arasi[0] == "HOL" else p.acilim.arasi[0] for p in kapilar} == {"WC & BANYO", "YATAK ODASI"}
    on = next(d for d in plan.duvarlar if d.yon == "x" and d.tur == "dis" and abs(d.c - 125) < 1e-6)
    yatak = [p for p in on.panolar if p.a0 >= 512 - 1e-6]
    assert [round(p.boy, 2) for p in yatak] == [71.25, 125.5, 66.25] and yatak[1].acilim.tur == "pencere"
    assert abs((yatak[1].a0 + yatak[1].a1) / 2 - (517 + 775) / 2) < 1e-6                 # odanın iç yüzleri arasında ortada
    arka = next(d for d in plan.duvarlar if d.yon == "x" and d.tur == "dis" and abs(d.c - 895) < 1e-6)
    assert round(arka.panolar[-1].boy, 2) == 74.75 and round(arka.panolar[-2].boy, 2) == 62.75


def test_ap07_sundurma():
    """AP-07 (Lokman, 14 Kasım 2026 08:41–08:55 UTC): sundurma taşan veranda, çatısı ana çatının ikinci cumbası (PC-38). Proje kartında
    sundurma veranda sayılmaz (`veranda_adedi` 0, `sundurma_adedi` 1); hakem açık mahali ikisinin toplamıyla kıyaslar. Brüt gövdenin
    dış çizgisi (45 m², pafta "sundurma hariç"); kapalı alan sundurmayı düşmez."""
    assert AP07_SOZU in D87 and AP07_KART in D87 and "| PA-27 | AP-07 |" in D87 and "| AP-07 | İş Emri yok" not in D87
    kart = HH.kartlar()["AP-07"]
    ie = json.loads((KOK / EVLER["PA27"][1]).read_text(encoding="utf-8"))
    assert (kart["veranda_adedi"], kart["sundurma_adedi"]) == (0, 1) and "08:55:19" in kart["sundurma_kaynagi"]
    assert HH.denetle(ie, kart)[0] == []
    assert [b.split(":")[0] for b in HH.denetle(ie, {a: v for a, v in kart.items() if a != "sundurma_adedi"})[0]] == ["veranda"]
    assert sum("sundurma_adedi" in k for k in HH.kartlar().values()) == 1                              # yalnız AP-07
    a = PREFABRIK["PA27"]
    assert (a["ozet"]["brut_m2"], a["kapali_m2"], a["veranda_m2"], a["ozet"]["brut_disi_acik_m2"]) == (45.0, 45.0, 1.76, 1.76)
    assert a["ozet"]["odalar"]["SUNDURMA"] == 1.76 and [v["cati"]["tip"] for v in ie["verandalar"]] == ["cumba"]
    assert not [k for k, b in PREFABRIK.items() if k not in {"PA27", *STANDART_HAL} and "brut_disi_acik_m2" in b["ozet"]]  # öteki kayıtlar aynen


def test_hakem_kalemleri():
    """Hakem kalem kalem bulur: ölçü 5 cm'yi, brüt 0,5 m²'yi aşınca; pencere ölçüsü, kapı, veranda ve kat farkında."""
    kart = dict(HH.kartlar()["AP-04"])
    ie = json.loads((KOK / EVLER["PA10"][1]).read_text(encoding="utf-8"))
    assert HH.denetle(ie, kart)[0] == []
    bozuk = {**kart, "dis_olcu_cm": [kart["dis_olcu_cm"][0] + 6, kart["dis_olcu_cm"][1]], "brut_oturum_m2": kart["brut_oturum_m2"] + 0.6,
             "dis_kapi_adedi": 2, "veranda_adedi": 0, "kat_adedi": 2, "oda_sayisi": "2+1",
             "acikliklar": {**kart["acikliklar"], "999/999": 1}}
    bas = [b.split(":")[0] for b in HH.denetle(ie, bozuk)[0]]
    assert bas == ["dış ölçü", "brüt oturum", "oda programı", "pencereler", "dis kapi", "veranda", "kat"]


def test_kartlarda_ad_yok():
    """Proje kartı hedef değerleri yalnız kodla durur (CLAUDE.md › soru 15): ad, telefon ve adres alanı yok. Disk arşivinin kartları
    HD kodlu (D-99 madde 3, D-111)."""
    for kod, k in HH.kartlar().items():
        assert re.fullmatch(r"AP-\d{2}|HD-\d{3}", kod) and not {"ad", "musteri", "musteri_adi", "telefon", "adres", "proje_adi"} & set(k), kod
        assert len(k["kart_sha256"]) == 64 and int(k.get("kat_adedi") or 1) in (1, 2)


def test_kabulsuz_yolda_havuz_gorunmez():
    """Harness `Katalog()`'u kabul kümesiz kurar: havuz evi görünmez, 22 vaka değişmez; görünmek K-A10 kaydına bağlı."""
    for kat in (Katalog(), Katalog(test_adaylari=True), Katalog(kabul_edilmis={"Ç8801"}), Katalog(kabul_edilmis=D80)):
        assert not {a["kod"] for a in kat.gorunur_adaylar()} & set(HAVUZ_EVLERI)
        assert kat.aday("PA-13") is None
    assert Katalog(kabul_edilmis={"PA13"}).aday("pa 13")["kod"] == "PA13"
    assert Katalog(havuz_dir=None, kabul_edilmis=set(EVLER)).aday("PA-13") is None


# Bütün havuz kabul edilince seçenek seti: düğme ve görsel en çok 3, liste en çok 10 satır, satır başlığı ≤ 24, açıklama ≤ 72
SETLER = {
    (50, "2+1"): ["PA23", "PA44"],                                                    # bugünkü 49 m² ve tam panolu hâli (PA-44, 49,02 m²)
    (40, "1+1"): ["PA29", "PA39"],                                                    # D-91 kısalt (39,61 m²); PA-39: disk arşivinin 37 m²'si (D-111)
    (45, "1+1"): ["PA27", "PA40", "PA45", "PA28"],                                    # eski hâl ve en yakın standart (D-91); PA-40, PA-45: disk arşivinin 45 m²'leri (D-111, D-132)
    (60, "2+1"): ["PA01", "PA14", "PA18", "PA25", "PA31", "PA41", "PA36", "PA02", "PA09", "PA20"],  # PA-31 silinmiş hâl (59 m²); PA-36 geniş hâl (62 m²); PA-41 disk arşivi (59 m², D-111)
    (65, "2+1"): ["PA02", "PA09", "PA20", "PA51", "PA36", "PA25", "PA32", "PA35", "PA53", "PA01"],  # PA-51 disk arşivinin 67 m²'si (D-165) dördüncü; PA-36 (62 m²) beşinci; PA-53 (70 m², D-170) dokuzuncu, PA-03 düştü; liste 10
    (71, "2+1"): ["PA26", "PA03", "PA15", "PA32", "PA35", "PA53", "PA47", "PA51", "PA24", "PA02"],  # PA-35: 71 m²'nin üçlü H'lı hâli (69 m²); PA-53 disk arşivi (70 m², D-170) altıncı; PA-47 disk arşivi (74 m², D-132); PA-51 disk arşivi (67 m², D-165); PA-04, PA-34, PA-20, PA-09 10 sınırıyla düştü
    (77, "2+1"): ["PA24", "PA04", "PA34", "PA16", "PA47", "PA48", "PA05", "PA26", "PA03", "PA15"],  # PA-34: 77 m²'nin büyüyen hâli (D-92); PA-47, PA-48 disk arşivi (D-132); PA-19 10 sınırıyla düştü
    (80, "2+1"): ["PA16", "PA48", "PA04", "PA05", "PA34", "PA24", "PA19", "PA47", "PA06"],  # PA-48 disk arşivinin 80 m²'si, PA-47 74 m² (D-132)
    (75, "2+1"): ["PA47", "PA24", "PA04", "PA34", "PA26", "PA03", "PA15", "PA16", "PA48", "PA32"],  # PA-47 disk arşivinin 76 m² başlıklı evi (74 m², D-132)
    (75, "3+1"): ["PA46", "PA21", "PA52"],                                            # PA-46 disk arşivinin 75 m² başlıklı evi (74 m², D-132); PA-52 70 m² 3+1 (69 m², D-168)
    (80, "3+1"): ["PA21", "PA30", "PA42", "PA12", "PA46"],                            # PA-30: 85 m²'nin silinmiş hâli (83 m², D-92); PA-42 disk arşivi (84 m², D-111); PA-46 (74 m², D-132)
    (90, "3+1"): ["PA07", "PA11", "PA17", "PA37", "PA43", "PA10", "PA12", "PA38", "PA42", "PA30"],  # PA-37: 91 m² üçlü H'lı hâl (D-96); PA-38: 95 m² 48 panolu; PA-43, PA-42 disk arşivi (D-111)
    (100, "2+1"): ["PA22"],
    (110, "3+1"): ["PA49", "PA50"],                                                   # disk arşivinin 110 ve 120 m²'si, ana çatı verandayı da örter (D-134)
    (120, "3+1"): ["PA50", "PA49"],                                                   # PA-50 120 m² başlıklı ev (119 m², D-134)
    (140, "3+1"): ["PA08", "PA33"],                                                   # PA-33: 140 m²'nin büyüyen hâli (142 m², D-92)
    (140, "4+1"): ["PA13"],
}


def _set(tmp_path: Path, m2: float, oda: str):
    s = Sohbet(tmp_path, kabul=set(TUM_PA))
    k = s.yaz(f"{m2:g} m2 {oda} prefabrik ev", alan_m2=m2, oda_programi=oda, yapi_turu="prefabrik")
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    return s, k


@pytest.mark.parametrize("m2,oda", sorted(SETLER))
def test_tum_havuzla_secenek_seti(tmp_path, m2, oda):
    s, k = _set(tmp_path, m2, oda)
    beklenen = SETLER[(m2, oda)]
    assert k.eylem == "secenek", k.mesaj
    st = s.k.d["secenek_seti"]
    assert [a["kod"] for a in st["adaylar"]] == beklenen[:S.EN_COK_SUNUM]
    assert len(k.butonlar) == min(len(beklenen), S.EN_COK_GORSEL)
    assert [b["baslik"] for b in k.butonlar] == [f"{i}. PA-{c[2:]}" for i, c in enumerate(beklenen[:3], 1)]
    assert len(k.mesaj) <= 1024
    kat = Katalog(kabul_edilmis=set(TUM_PA))
    for kod in beklenen:
        a = {**kat.aday(kod), "puan": 100}
        assert len(S.kisa_ad(a)) <= 24 and len(S.aciklama(a)) <= 72


def test_koddan_secim_havuz_evi(tmp_path):
    """Bayi kodu yazarsa (LLM 'PA-13' okur) plan şablondan gelir."""
    s, _ = _set(tmp_path, 140, "4+1")
    k = s.yaz("PA-13 olsun", katalog_kodu="pa 13")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA13", k.mesaj
    sab = json.loads((SABLON_DIR / "adaylar/PA13.json").read_text(encoding="utf-8"))
    assert k.is_emri["mahaller"] == sab["mahaller"] and k.is_emri["acikliklar"] == sab["acikliklar"]


def test_kabul_betigi_havuzu_tanir():
    """K-A10 kabul kaydı (`vps/ie08_adaylar.sh` → `aday_kabul.py`): PA kodlarıyla prefabrik koşusu havuz evlerini de tanır."""
    arac = [sys.executable, str(KOK / "araclar/aday_kabul.py"), "--tarih", "2026-11-14", "--kuru",
            "--adaylar", str(ADAYLAR_PREFABRIK_JSON)]
    r = subprocess.run(arac + ["--kodlar", ",".join(f"PA-{k[2:]}" for k in sorted(HAVUZ_EVLERI))], capture_output=True, text=True, cwd=KOK)
    assert r.returncode == 0 and f"KURU: {len(HAVUZ_EVLERI)} kayıt yazılacak" in r.stdout, r.stdout + r.stderr
    r = subprocess.run(arac[:-2] + ["--adaylar", str(KOK / "beyin/veri/adaylar.json"), "--kodlar", "PA-13"], capture_output=True,
                       text=True, cwd=KOK)
    assert r.returncode == 2 and "olmayan kod: PA13" in r.stdout, r.stdout             # prefabrik çelik koşusuna karışmaz


def test_aday_kaydet_hakemsiz_yazmaz(tmp_path):
    """Hakemden geçmeyen ev kaydedilmez: AP-28'in İş Emri'si `--kart AP-28` ile DUR, şablon ve kayıt yazılmaz."""
    r = subprocess.run([sys.executable, str(KOK / "araclar/aday_kaydet.py"), str(KOK / KALANLAR["AP-28"][0]), "--kod", "PA-98",
                        "--durum", "test", "--kart", "AP-28", "--standart", "--havuz"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 1 and "proje kartı hakemi geçmedi (AP-28)" in r.stdout, r.stdout + r.stderr
    assert not (KOK / "is_emri/adaylar/PA98.json").exists() and not (HAVUZ_DIR / "PA98.json").exists()


def test_kart_veri_seti():
    """Veri seti AIPrefabrik'in tek katlı ve çift katlı projelerini kodla tutar (AP-01 … AP-28; AP-20'nin kartı yok, çift kat)."""
    veri = json.loads((KOK / "testler/havuz/proje_kartlari.json").read_text(encoding="utf-8"))
    assert veri["kaynak"].startswith("Proje_Karti")
    assert sorted(veri["evler"]) == [f"AP-{i:02d}" for i in range(1, 29) if i != 20]


# ── Çelik (PR-2) ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_celik_kaydi_bicimi():
    assert set(CELIK_KAYIT) == set(CELIK)
    for kod, a in CELIK_KAYIT.items():
        proje, kaynak, oda, m2 = CELIK[kod]
        g = kod[:2] + "-" + kod[2:]
        assert (a["gosterim"], a["referans_model"], a["motor"], a["yapi_turu"], a["kat"]) == (g, kod, "genel", "celik", 1)
        assert (a["durum"], a["oda_programi"], a["katalog_m2"], a["musteri_projesi"]) == ("gecerli", oda, m2, True), kod
        assert a["sunum"]["ad"] == ""                                                    # KT müşteri projesi: bayiye adsız (D-08, D-33)
        assert a["tanim"] == f"modeller/havuz/{kod}.json"
        assert a["tanim_sha256"] == hashlib.sha256((KOK / a["tanim"]).read_bytes()).hexdigest()
        kk = a["kaynak"]["kart_kiyasi"]
        assert (a["kaynak"]["karar"], kk["kart"], kk["tanim"], kk["sonuc"]) == ("D-87", proje, kaynak, "geçti")
        assert kk["tanim_sha256"] == hashlib.sha256((KOK / kaynak).read_bytes()).hexdigest() == HH.celik_kartlari()[proje]["tanim_sha256"]
        assert f"| {g} | {proje} | `{kaynak}` |" in D87, kod
        assert a["veranda_m2"] == kk["olcum"]["veranda_m2"] and (SABLON_DIR / a["gorsel"]).stat().st_size > 10_000


@pytest.mark.parametrize("kod", sorted(CELIK))
def test_celik_tanim_kaynakla_ayni(kod):
    """Havuzun tanımı İE-16 tanımının aynısı; yalnız kod ve ad farklı (KT-04 = ÇP-14 örneği gibi)."""
    t = json.loads((KOK / CELIK_KAYIT[kod]["tanim"]).read_text(encoding="utf-8"))
    k = json.loads((KOK / CELIK[kod][1]).read_text(encoding="utf-8"))
    assert t["kod"] == kod[:2] + "-" + kod[2:] and CELIK[kod][0] in t["ad"]
    assert {x: v for x, v in t.items() if x not in ("kod", "ad")} == {x: v for x, v in k.items() if x not in ("kod", "ad")}


@pytest.mark.parametrize("kod", sorted(CELIK))
def test_celik_hakem_gecer(kod):
    """Genel motor çizer ve doğrular; brüt oturum antet m²'sinden en çok 0,5 m²; oda ve veranda antetle aynı (hakem yeniden koşar)."""
    a = CELIK_KAYIT[kod]
    bulgular, olc = HH.celik_denetle(KOK / a["tanim"], HH.celik_kartlari()[CELIK[kod][0]])
    assert bulgular == [], (kod, bulgular)
    assert olc == a["kaynak"]["kart_kiyasi"]["olcum"], kod


def test_celik_disarida_kalanlar():
    """Antette oda programı yok (ÇP-03, ÇP-04), aynı proje havuzda (ÇP-07, 13, 14, 17): hakem girdisi bunu söyler. Verandasız ÇP-08 girer.
    İkinci kümede antetteki sayısı brüt olmayan üç proje (ÇP-22, 24, 25) planın m²'siyle girer; ÇP-26 çift kat, kartı yok."""
    kart = HH.celik_kartlari()
    assert {k for k, v in kart.items() if not v["oda_programi"]} == {"ÇP-03", "ÇP-04"}
    assert {k for k, v in kart.items() if not v["veranda"]} == {"ÇP-08", "ÇP-13", "ÇP-22"}
    assert {k: v["havuzda"] for k, v in kart.items() if v["havuzda"]} == {"ÇP-07": "KT-03", "ÇP-13": "KT-01", "ÇP-14": "KT-04", "ÇP-17": "KT-02"}
    gecen = {CELIK[k][0] for k in CELIK}
    assert gecen == {k for k, v in kart.items() if v["oda_programi"] and not v["havuzda"]}
    assert "ÇP-26" not in kart and CELIK2_KART in D87 and "| ÇP-26 | Çift kat" in D87
    for satir in ("| ÇP-07, ÇP-13, ÇP-14, ÇP-17 |", "| ÇP-03 | Hakem kaldı", "| ÇP-04 | Hakem kaldı"):
        assert satir in D87
    assert not [p for p in PLAN_M2 if f"| {p} | Hakem kaldı" in D87]


@pytest.mark.parametrize("proje", sorted(PLAN_M2))
def test_celik_plan_m2(proje):
    """Lokman 14 Kasım 2026 12:33:58 kartı: brüt oturum planın m²'siyle (`plan_m2`), sınır aynı 0,5 m²; `antet_m2` paftadaki sayı kalır.
    Söz kartta yoksa ya da `plan_m2` yoksa hakem yine "brüt oturum" der (kural yalnız bu üç projede, Lokman'ın sözüyle)."""
    k = HH.celik_kartlari()[proje]
    assert (k["plan_m2"], k["antet_m2"]) == PLAN_M2[proje]
    assert "12:33:58" in k["plan_m2_kaynagi"] and PLAN_M2_KART in k["plan_m2_kaynagi"] and PLAN_M2_KART in D87
    bulgular, olc = HH.celik_denetle(KOK / k["tanim"], k)
    assert bulgular == [] and olc["gecti"] and olc["oda_programi"] == k["oda_programi"]
    assert abs(olc["oturum_m2"] - k["plan_m2"]) <= HH.TOL_BRUT_M2 < abs(olc["oturum_m2"] - k["antet_m2"])
    antetle = {a: v for a, v in k.items() if a not in ("plan_m2", "plan_m2_kaynagi")}
    assert [b.split(":")[0] for b in HH.celik_denetle(KOK / k["tanim"], antetle)[0]] == ["brüt oturum"]
    sozsuz = {a: v for a, v in k.items() if a != "plan_m2_kaynagi"}
    assert [b for b in HH.celik_denetle(KOK / k["tanim"], sozsuz)[0] if "kaynağı" in b]
    assert sorted(p for p, v in HH.celik_kartlari().items() if "plan_m2" in v) == sorted(PLAN_M2)


def test_celik_kabulsuz_gorunmez():
    """Kabulsüz yolda (harness) çelik adaylar görünür (İE-08); havuzun çelik kaydı görünmez: harness'in 22 vakası aynen."""
    gor = {a["kod"] for a in Katalog().gorunur_adaylar()}
    assert gor == ESKI_CELIK - {"KT04"} and not gor & set(CELIK)
    assert Katalog(kabul_edilmis={"KT06"}).aday("KT-06")["kod"] == "KT06"


SETLER_CELIK = {
    (80, "2+1"): ["KT09", "KT10", "Ç8201", "Ç8801"],
    (82, "2+1"): ["KT10", "Ç8201", "KT09", "Ç8801", "KT05", "KT06", "KT07"],
    (90, "2+1"): ["KT05", "KT06", "KT07", "KT02", "Ç8801", "KT03", "KT10", "Ç8201", "KT01", "KT09"],
    (88, "2+1"): ["Ç8801", "KT05", "KT06", "KT07", "KT02", "KT03", "KT10", "Ç8201", "KT09"],
    (90, "3+1"): ["KT08"],
    (49, "1+1"): ["KT11"],                                                            # planın m²'siyle (12:33:58 kartı); tek aday
    (130, "3+1"): ["KT12"],
    (167, "3+1"): ["KT13"],
}


@pytest.mark.parametrize("m2,oda", sorted(SETLER_CELIK))
def test_tum_havuzla_celik_seti(tmp_path, m2, oda):
    s = Sohbet(tmp_path, kabul=ESKI_CELIK | set(CELIK))
    k = s.yaz(f"{m2} m2 {oda} çelik ev", alan_m2=m2, oda_programi=oda, yapi_turu="celik")
    beklenen = SETLER_CELIK[(m2, oda)]
    assert k.eylem == "secenek", k.mesaj
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == beklenen
    assert len(k.butonlar) == min(len(beklenen), S.EN_COK_GORSEL) and len(k.mesaj) <= 1024


def test_kabul_betigi_celik_havuzu_tanir():
    """Çelik kodlarıyla koşu (`adaylar.json`) havuzun çelik kayıtlarını tanır; prefabrik koşusu tanımaz."""
    arac = [sys.executable, str(KOK / "araclar/aday_kabul.py"), "--tarih", "2026-11-14", "--kuru"]
    r = subprocess.run(arac + ["--adaylar", str(KOK / "beyin/veri/adaylar.json"), "--kodlar", "KT-05,KT-06,KT-07,KT-08,KT-09,KT-10,KT-11,KT-12,KT-13"],
                       capture_output=True, text=True, cwd=KOK)
    assert r.returncode == 0 and "KURU: 9 kayıt yazılacak" in r.stdout, r.stdout + r.stderr
    r = subprocess.run(arac + ["--adaylar", str(ADAYLAR_PREFABRIK_JSON), "--kodlar", "KT-05"], capture_output=True, text=True, cwd=KOK)
    assert r.returncode == 2 and "olmayan kod: KT05" in r.stdout, r.stdout


def test_koddan_secim_celik_havuz(tmp_path):
    """Bayi çelik setten kodu yazarsa (LLM 'KT-06' okur) İş Emri havuzun tanımını taşır; tanımın sha'sı tutar."""
    from beyin import celik as C
    s = Sohbet(tmp_path, kabul=ESKI_CELIK | set(CELIK))
    k = s.yaz("90 m2 2+1 çelik ev", alan_m2=90, oda_programi="2+1", yapi_turu="celik")
    assert k.eylem == "secenek", k.mesaj
    k = s.yaz("KT-06 olsun", katalog_kodu="kt 06", yapi_turu="celik")
    assert k.eylem == "is_emri", k.mesaj
    y = k.is_emri["yapi"]
    assert (y["kod"], y["tanim"], y["sistem"]) == ("KT06", "modeller/havuz/KT06.json", "celik") and C.tanim_dogrula(y)


# Lokman, 14 Kasım 2026 13:08:54 UTC kartı "Kendi adıyla yazılsın": açık alan planda sundurma ya da giriş ise seçenek satırı ve mesajı
# "veranda" yerine o adı yazar. Ad, planın odaları içinde `veranda_m2`'ye eşit tek alandan okunur; toplamda (KT-12) "veranda" kalır.
ACIK_ALAN_KART = '"Kendi adıyla yazılsın"'
ACIK_ALAN = {"PA27": "sundurma", "KT11": "sundurma", "KT09": "giriş",
             "PA28": "sundurma", "PA29": "sundurma"}                              # PA-28, PA-29: aynı evin standart hâlleri (D-91)


def test_acik_alan_kendi_adiyla():
    assert ACIK_ALAN_KART in D87 and "13:08:54" in D87
    kat = Katalog(kabul_edilmis=set(TUM_PA) | ESKI_CELIK | set(CELIK))
    adaylar = kat.gorunur_adaylar()
    assert {a["kod"] for a in adaylar} >= {"PA27", "KT11", "KT09", "KT12", "PA13", "PA26"}
    for a in adaylar:
        ad = S.acik_alan_adi(a)
        assert ad == ACIK_ALAN.get(a["kod"], "veranda"), a["kod"]
        satir = S.aciklama({**a, "puan": 100})
        if (S._f(a.get("veranda_m2")) or 0) > 0:
            assert f"· {ad} {a['veranda_m2']} m² ·" in satir, (a["kod"], satir)
        else:
            assert "verandasız" in satir and "sundurma" not in satir and "giriş" not in satir, (a["kod"], satir)


def test_acik_alan_set_kaydinda(tmp_path):
    """Liste satırı set kaydından yazılır (`ozet` yok): ad `acik_alan` ile taşınır; öteki evlerin set kaydı aynı kalır."""
    s, k = _set(tmp_path, 45, "1+1")
    a = s.k.d["secenek_seti"]["adaylar"][0]
    assert a["kod"] == "PA27" and a["acik_alan"] == "sundurma"
    satir = next(x for x in k.mesaj.splitlines() if "PA-27" in x)             # D-111'den beri sette verandalı PA-40 da var
    assert ", sundurma 1.76 ·" in satir and "veranda" not in satir, k.mesaj
    assert "· sundurma 1.76 m² ·" in S.aciklama(a)
    s, k = _set(tmp_path / "71", 71, "2+1")
    assert all("acik_alan" not in a for a in s.k.d["secenek_seti"]["adaylar"])
    assert "veranda" in k.mesaj and "sundurma" not in k.mesaj
    for m2, oda, kod, ad in ((49, "1+1", "KT11", "sundurma"), (80, "2+1", "KT09", "giriş")):
        s = Sohbet(tmp_path / f"c{m2}", kabul=ESKI_CELIK | set(CELIK))
        k = s.yaz(f"{m2} m2 {oda} çelik ev", alan_m2=m2, oda_programi=oda, yapi_turu="celik")
        st = s.k.d["secenek_seti"]["adaylar"]
        assert {x["kod"]: x.get("acik_alan") for x in st if "acik_alan" in x} == {kod: ad}, st
        assert f", {ad} " in k.mesaj, k.mesaj
