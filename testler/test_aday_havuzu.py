"""İE-38 (D-87) · Aday havuzu: AIPrefabrik'teki tek katlı evler bayiye giden seçenek setinde. LLM'siz, Postgres'siz.

Lokman, 13 Kasım 2026 21:41 UTC: "AIPrefabrik ve AICelik tüm prefabrik ve çelikleri veri tabanına al … yarın kalktığımızda whatsapp'tan
bayi talebi geldiğinde tüm projeler yer alsın". Bir ev havuza ancak proje kartı hakeminden geçerse girer (`araclar/havuz_hakemi.py`);
hedef değerler proje kartı veri setinden (`testler/havuz/proje_kartlari.json`, PR #145). Kayıt ev başına bir dosya (`beyin/veri/havuz/`);
görünürlük K-A10 kabul kaydıyla (kabulsüz yol, harness dahil, aynen).
"""
from __future__ import annotations
import hashlib
import json
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
    "PA27": ("AP-07", "testler/havuz/is_emirleri/AP07.json", "1+1", 45.0),        # sundurma ikinci cumba (PC-38), 08:55 kartı
}
PREFABRIK = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}

# D-87 › Havuza giren çelik projeler (PR-2): kod → (proje, tanımın kaynağı, oda programı, brüt m²; genel motorun `bina_m2`'si)
CELIK = {
    "KT05": ("ÇP-06", "testler/celik/projeler/CP06/CP06.json", "2+1", 90.0),
    "KT06": ("ÇP-18", "testler/celik/projeler/CP18/CP18.json", "2+1", 90.0),
    "KT07": ("ÇP-19", "testler/celik/projeler/CP19/CP19.json", "2+1", 90.0),
    "KT08": ("ÇP-20", "testler/celik/projeler/CP20/CP20.json", "3+1", 90.0),
    "KT09": ("ÇP-08", "testler/celik/projeler/CP08/CP08.json", "2+1", 81.0),      # antette veranda yok (D-87 › Veranda, 14 Kasım)
    "KT10": ("ÇP-23", "testler/celik/projeler/CP23/CP23.json", "2+1", 82.0),      # ikinci kör küme, yalnız plan olarak (aşağıda)
}
# İkinci kör küme (İE-16 PR-7): Lokman'ın 14 Kasım 2026 11:33:07 UTC kartı, çelik kör testi sohbeti; plan hakemden geçerse girer
CELIK2_KART = '"Yalnız plan olarak girsin"'
# Hakemden geçmeyen ikinci küme projeleri ve bulgunun başı (D-87 › Havuza girmeyen çelik projeler)
KALANLAR_CELIK = {"ÇP-22": "brüt oturum", "ÇP-24": "brüt oturum", "ÇP-25": "brüt oturum"}
CELIK_KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="celik")}
ESKI_CELIK = {"Ç8801", "Ç8801K", "Ç8801L", "Ç8201", "KT01", "KT02", "KT03", "KT04"}
D80 = {f"PA0{i}" for i in range(1, 9)}
TUM_PA = D80 | {"PA06K", "PA06C"} | set(EVLER)

# D-87 › Havuza girmeyen projeler: hakemden geçmeyenler ve bulgunun başı
KALANLAR = {
    "AP-23": ("testler/kor/projeler/AP23/is_emri.json", ["oda programı"]),
    "AP-28": ("testler/kor/projeler/AP28/is_emri.json", ["dış ölçü", "brüt oturum"]),
}
# D-87 › Veranda (Lokman, 14 Kasım 2026 07:34 UTC): veranda bir oda gibi sayılır; verandasız ev de havuza girer
VERANDA_SOZU = "veranda ayrıca var mı yok mu belirtilmez verandayı da bir oda gibi kabul et"
VERANDASIZ = {"PA23", "PA24", "KT09"}
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
    assert set(PREFABRIK) == set(EVLER)
    assert sorted(f.stem for f in HAVUZ_DIR.glob("*.json")) == sorted([*EVLER, *CELIK])  # ev başına bir dosya, ad = kod
    eski = {str(a["kod"]).upper() for a in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8"))}
    assert not eski & set(EVLER) and eski == D80                                      # D-80 kaydı aynen
    for kod, a in PREFABRIK.items():
        proje, kaynak, oda, m2 = EVLER[kod]
        g = kod[:2] + "-" + kod[2:]
        assert a["gosterim"] == g == a["referans_model"]
        assert (a["durum"], a["yapi_turu"], a["kat"], a["oda_programi"], a["katalog_m2"]) == ("gecerli", "prefabrik", 1, oda, m2), kod
        assert a["kaynak"]["dosya"] == kaynak and a["kaynak"]["karar"] == "D-87" and a["kaynak"]["standart"] is True
        kk = a["kaynak"]["kart_kiyasi"]
        assert (kk["kart"], kk["sonuc"]) == (proje, "geçti")
        assert kk["kart_sha256"] == HH.kartlar()[proje]["kart_sha256"]
        assert f"| {g} | {proje} | `{kaynak}` |" in D87, kod                         # karar dosyası evi yazar
        disarida = a["ozet"].get("brut_disi_acik_m2", 0)                                 # girintili gövdeden taşan sundurma (PA-27)
        assert abs(a["kapali_m2"] - (a["ozet"]["brut_m2"] - a["veranda_m2"] + disarida)) <= 0.06, kod   # aday_kaydet ham brütle yuvarlar
        assert ((a["veranda_m2"] or 0) > 0) == (kk["olcum"]["veranda"] > 0), kod      # veranda bir oda gibi: kartta ne varsa (D-87 › Veranda)
        assert (SABLON_DIR / a["gorsel"]).stat().st_size > 10_000


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_hakem_gecer(kod):
    """Kayıttaki şablon, kaynak İş Emri'nin standart hâli ve proje kartıyla aynı (hakem yeniden koşar; Motor değişirse düşer)."""
    a = PREFABRIK[kod]
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    bulgular, olc = HH.denetle(sab, HH.kartlar()[EVLER[kod][0]])
    assert bulgular == [], (kod, bulgular)
    assert olc == a["kaynak"]["kart_kiyasi"]["olcum"], kod


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_sablon_kaynagin_standart_hali(kod):
    """Şablon gerçek projenin İş Emri'sidir: yalnız kimlik, talep, referans kodu ve müşterinin seçimleri (D-74 standart) değişir."""
    kaynak = _standart(json.loads((KOK / EVLER[kod][1]).read_text(encoding="utf-8")))
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
    assert not [k for k, b in PREFABRIK.items() if k != "PA27" and "brut_disi_acik_m2" in b["ozet"]]  # öteki kayıtlar aynen


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
    """Proje kartı hedef değerleri yalnız kodla durur (CLAUDE.md › soru 15): ad, telefon ve adres alanı yok."""
    for kod, k in HH.kartlar().items():
        assert kod.startswith("AP-") and not {"ad", "musteri", "musteri_adi", "telefon", "adres", "proje_adi"} & set(k), kod
        assert len(k["kart_sha256"]) == 64 and int(k.get("kat_adedi") or 1) in (1, 2)


def test_kabulsuz_yolda_havuz_gorunmez():
    """Harness `Katalog()`'u kabul kümesiz kurar: havuz evi görünmez, 22 vaka değişmez; görünmek K-A10 kaydına bağlı."""
    for kat in (Katalog(), Katalog(test_adaylari=True), Katalog(kabul_edilmis={"Ç8801"}), Katalog(kabul_edilmis=D80)):
        assert not {a["kod"] for a in kat.gorunur_adaylar()} & set(EVLER)
        assert kat.aday("PA-13") is None
    assert Katalog(kabul_edilmis={"PA13"}).aday("pa 13")["kod"] == "PA13"
    assert Katalog(havuz_dir=None, kabul_edilmis=set(EVLER)).aday("PA-13") is None


# Bütün havuz kabul edilince seçenek seti: düğme ve görsel en çok 3, liste en çok 10 satır, satır başlığı ≤ 24, açıklama ≤ 72
SETLER = {
    (50, "2+1"): ["PA23"],                                                            # tek aday: öncelik sorulmaz
    (45, "1+1"): ["PA27"],
    (60, "2+1"): ["PA01", "PA14", "PA18", "PA25", "PA02", "PA09", "PA20"],
    (65, "2+1"): ["PA02", "PA09", "PA20", "PA25", "PA01", "PA03", "PA14", "PA15", "PA18", "PA26"],
    (71, "2+1"): ["PA26", "PA03", "PA15", "PA24", "PA02", "PA04", "PA09", "PA20"],
    (77, "2+1"): ["PA24", "PA04", "PA16", "PA05", "PA26", "PA03", "PA15", "PA19"],
    (80, "2+1"): ["PA16", "PA04", "PA05", "PA24", "PA19", "PA06"],
    (80, "3+1"): ["PA21", "PA12"],
    (90, "3+1"): ["PA07", "PA11", "PA17", "PA10", "PA12"],
    (100, "2+1"): ["PA22"],
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
    r = subprocess.run(arac + ["--kodlar", ",".join(f"PA-{k[2:]}" for k in sorted(EVLER))], capture_output=True, text=True, cwd=KOK)
    assert r.returncode == 0 and f"KURU: {len(EVLER)} kayıt yazılacak" in r.stdout, r.stdout + r.stderr
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
    İkinci kümede brüt oturumu antetten farklı üç proje (ÇP-22, 24, 25) girmez; ÇP-26 çift kat, kartı yok."""
    kart = HH.celik_kartlari()
    assert {k for k, v in kart.items() if not v["oda_programi"]} == {"ÇP-03", "ÇP-04"}
    assert {k for k, v in kart.items() if not v["veranda"]} == {"ÇP-08", "ÇP-13", "ÇP-22"}
    assert {k: v["havuzda"] for k, v in kart.items() if v["havuzda"]} == {"ÇP-07": "KT-03", "ÇP-13": "KT-01", "ÇP-14": "KT-04", "ÇP-17": "KT-02"}
    gecen = {CELIK[k][0] for k in CELIK}
    assert gecen == {k for k, v in kart.items() if v["oda_programi"] and not v["havuzda"]} - set(KALANLAR_CELIK)
    assert "ÇP-26" not in kart and CELIK2_KART in D87 and "| ÇP-26 | Çift kat" in D87
    for satir in ("| ÇP-07, ÇP-13, ÇP-14, ÇP-17 |", "| ÇP-03 | Hakem kaldı", "| ÇP-04 | Hakem kaldı", "| ÇP-22 | Hakem kaldı: brüt oturum",
                  "| ÇP-24 | Hakem kaldı: brüt oturum", "| ÇP-25 | Hakem kaldı: brüt oturum"):
        assert satir in D87


@pytest.mark.parametrize("proje", sorted(KALANLAR_CELIK))
def test_celik_ikinci_kume_kalanlar(proje):
    """Hakem yeniden koşar: genel motor çizer ve doğrular, oda programı tutar; brüt oturum antetten 0,5 m²'den çok sapar (zorla girmez)."""
    k = HH.celik_kartlari()[proje]
    bulgular, olc = HH.celik_denetle(KOK / k["tanim"], k)
    assert [b.split(":")[0] for b in bulgular] == [KALANLAR_CELIK[proje]], bulgular
    assert olc["gecti"] and olc["oda_programi"] == k["oda_programi"]


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
    r = subprocess.run(arac + ["--adaylar", str(KOK / "beyin/veri/adaylar.json"), "--kodlar", "KT-05,KT-06,KT-07,KT-08,KT-09,KT-10"],
                       capture_output=True, text=True, cwd=KOK)
    assert r.returncode == 0 and "KURU: 6 kayıt yazılacak" in r.stdout, r.stdout + r.stderr
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
