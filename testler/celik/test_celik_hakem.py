"""İE-16 PR-1 · çelik hakemi: mühür, açık seçimi, liste ve pafta okuyucuları, kıyasın sırası ve çelik kg kapısı.

Her koşuda: gerçek mühür kaydının yapısı (ad yok, durumlar, çift katlar kapalı), açık dört projenin yazılı kuraldan yeniden kurulması, kör ve
kapalı listelerin açılış kaydı olmadan reddedilmesi; uydurma çelik listesi (Excel ve PDF) ve uydurma pafta ile okuyucular; geçici bir depoda
aracın sırası (bizim yanımız kayıtlı → mühür → açılış) ve kapının sınırı. Kaynak dosya gerekmez.

Tam koşu (`PORTMAN_CELIK_KAYNAK=<klasör>`; dosyalar Drive kimliğiyle adlı, ör. `<drive_id>.xlsx`): hedef örneğin listesi (Excel ve PDF) ve
paftası yeniden okunur, cevap `veri/CP06_hakem_cevabi.json`'la aynı olmalı; bir baytı değiştirilmiş kopya okunmadan durmalı.
Uydurma listedeki ad ve numara uydurmadır; numara çalışma anında kurulur (dosyada düz yazılmaz).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas as K, oku, pafta  # noqa: E402
from testler.kor.kiyas import Durdu  # noqa: E402

MUHUR = KOK / "testler" / "celik" / "muhur.json"
CEVAP = KOK / "testler" / "celik" / "veri" / "CP06_hakem_cevabi.json"
FONT = str(KOK / "motor" / "genel" / "font" / "LiberationSans-Regular.ttf")
UYDURMA_AD = "Deneme Kişisi Uydurma"
UYDURMA_TEL = "0" + "5" + "00 000 07 77"
ACIK = ["ÇP-03", "ÇP-07", "ÇP-13", "ÇP-14"]
CIFT = ["ÇP-01", "ÇP-05", "ÇP-10", "ÇP-15", "ÇP-16", "ÇP-21"]
CELIK = [  # ad, boyut, adet, kg
    ("ÇATI MAKASLARI", "80X45X10X0,8", 6, 240),
    ("KOLON - KİRİŞ PANELLERİ", "80X45X10X1,2", 2, 44),
    ("ÇATI PANELLERİ", "80X45X10X1,2", 1, 60),
    ("DUVAR PANELLERİ", "80X45X10X1,2", 10, 520),
    ("Boy C Profil", "80X45X10X0,8", 2, 10),
]
OTEKI = [  # grup, ad, boyut, adet
    ("METAL AKSAM GRUBU", "KÖŞEBENT", "30*30*2500", 20),
    ("METAL AKSAM GRUBU", "AŞIK", "L:4200", 15),
]


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _git(kok: Path, *args):
    subprocess.run(["git", "-C", str(kok), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


# ------------------------------------------------------------------------------------------------------- uydurma dosyalar

def _liste_xlsx(yol: Path, celik=CELIK, toplam: tuple | None = None) -> None:
    """Çelik şablonu: başlık bloğunda uydurma ad ve numara, 11. satırda çelik grubunun başlığı (KG ile), TOPLAM, sonra öteki grup."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ÇELİK BİNA"
    ws["B1"] = "PORTATİFEV YÜKLEME LİSTESİ"
    ws["B3"], ws["C3"] = "MÜŞTERİ ADI", UYDURMA_AD
    ws["B4"], ws["C4"] = "TELEFON", UYDURMA_TEL
    for c, v in enumerate(("NO", "ÇELİK PANEL GRUBU", "BOYUT/ÖLÇÜ", "ADET", "KG", "MAKİNE"), 1):
        ws.cell(11, c, v)
    n = 12
    for i, (a, b, adet, kg) in enumerate(celik, 1):
        for c, v in enumerate((i, a, b, adet, kg, "DENEME MAKİNE"), 1):
            ws.cell(n, c, v)
        n += 1
    t = toplam or (sum(x[2] for x in celik), sum(x[3] for x in celik))
    ws.cell(n, 1, "TOPLAM"), ws.cell(n, 4, t[0]), ws.cell(n, 5, t[1])
    n += 1
    for c, v in enumerate(("NO", "METAL AKSAM GRUBU", "BOYUT/ÖLÇÜ", "ADET"), 1):
        ws.cell(n, c, v)
    for i, (_, a, b, adet) in enumerate(OTEKI, 1):
        n += 1
        for c, v in enumerate((i, a, b, adet), 1):
            ws.cell(n, c, v)
    ws.cell(n + 2, 2, "SORUMLU ÜRETİM PERSONELİ AD SOYAD"), ws.cell(n + 2, 4, UYDURMA_AD)
    wb.save(str(yol))


def _liste_pdf(yol: Path, celik=CELIK) -> None:
    """Aynı liste PDF olarak (sütun yerleri gerçek şablondaki gibi)."""
    import pymupdf

    doc = pymupdf.open()
    s = doc.new_page(width=595, height=842)

    def yaz(x, y, t):
        s.insert_text((x, y), str(t), fontsize=8, fontname="ls", fontfile=FONT)

    yaz(60, 60, "MÜŞTERİ ADI"), yaz(200, 60, UYDURMA_AD), yaz(60, 72, "TELEFON"), yaz(200, 72, UYDURMA_TEL)
    y = 170
    for x, t in ((54, "NO"), (127, "ÇELİK PANEL GRUBU"), (284, "BOYUT/ÖLÇÜ"), (366, "ADET"), (427, "KG"), (480, "MAKİNE")):
        yaz(x, y, t)
    for i, (a, b, adet, kg) in enumerate(celik, 1):
        y += 11
        yaz(57, y, i), yaz(68, y, a), yaz(285, y, b), yaz(373, y, adet), yaz(426, y, kg), yaz(473, y, "DENEME MAKİNE")
    y += 11
    yaz(185, y, "TOPLAM"), yaz(372, y, sum(x[2] for x in celik)), yaz(424, y, sum(x[3] for x in celik))
    y += 11
    for x, t in ((54, "NO"), (125, "METAL AKSAM GRUBU"), (284, "BOYUT/ÖLÇÜ"), (366, "ADET")):
        yaz(x, y, t)
    for i, (_, a, b, adet) in enumerate(OTEKI, 1):
        y += 11
        yaz(57, y, i), yaz(68, y, a), yaz(292, y, b), yaz(373, y, adet)
    doc.save(str(yol))


def _pafta_pdf(yol: Path, sayfalar: list[list[str]]) -> None:
    import pymupdf

    doc = pymupdf.open()
    for sozcukler in sayfalar:
        s = doc.new_page(width=842, height=595)
        s.insert_text((40, 40), "DUVAR PANELLERİ YERLEŞİM PLANI", fontsize=10, fontname="ls", fontfile=FONT)
        for i, w in enumerate(sozcukler):
            s.insert_text((60 + (i % 10) * 70, 100 + (i // 10) * 30), w, fontsize=9, fontname="ls", fontfile=FONT)
    doc.save(str(yol))


# ------------------------------------------------------------------------------------------------------------ gerçek mühür

@pytest.fixture(scope="module")
def muhur():
    return K.muhur_oku(MUHUR)


IZINLI_ALAN = {"kod", "tur", "uzanti", "bayt", "drive_id", "drive_degisme", "sha256", "durum"}


def test_muhur_kaydinda_ad_yok(muhur):
    """Kayıtlarda yalnız izinli alanlar ve biçimli değerler: dosya ya da klasör adı, kişi ya da bayi adı giremez."""
    for r in muhur["dosyalar"]:
        assert set(r) == IZINLI_ALAN
        assert re.fullmatch(r"ÇP-\d{2}", r["kod"]) and r["kod"] in muhur["projeler"]
        assert re.fullmatch(r"[A-Za-z0-9_-]{25,60}", r["drive_id"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", r["drive_degisme"])
        assert r["sha256"] is None or re.fullmatch(r"[0-9a-f]{64}", r["sha256"])
        assert re.fullmatch(r"\.[a-z]{3,4}", r["uzanti"]) and isinstance(r["bayt"], int) and r["bayt"] > 0
    for k, p in muhur["projeler"].items():
        assert set(p) == {"m2", "kat", "liste_tarihi", "drive_klasor", "durum"}
        assert re.fullmatch(r"[A-Za-z0-9_-]{25,60}", p["drive_klasor"])
    assert len({r["drive_id"] for r in muhur["dosyalar"]}) == len(muhur["dosyalar"]) == 118


def test_projeler_ve_durumlar(muhur):
    P = muhur["projeler"]
    assert list(P) == [f"ÇP-{i:02d}" for i in range(1, 22)]
    assert sorted(k for k, p in P.items() if p["durum"] == "acik") == ACIK
    assert [k for k, p in P.items() if p["durum"] == "hedef"] == ["ÇP-06"]
    assert sorted(k for k, p in P.items() if p["kat"] == "çift") == CIFT
    assert all(P[k]["durum"] == "kapali" for k in CIFT), "çift katlılar kapalı (D-26)"
    assert sum(p["durum"] == "kor" for p in P.values()) == 10
    for r in muhur["dosyalar"]:
        pd = P[r["kod"]]["durum"]
        if r["tur"] in K.LISTELER:
            assert r["durum"] == ("acik" if pd in ("hedef", "acik") else pd), r["drive_id"]
        else:
            assert r["durum"] == "kaynak"
    assert "ÇP-06" in muhur["acilislar"]
    say = muhur["sayilar"]
    assert say["dosyalar"] == {"acik": 15, "kapali": 14, "kaynak": 65, "kor": 24}
    assert say["sha256_dolu"] == sum(1 for r in muhur["dosyalar"] if r["sha256"]) == 17


EKLENEBILIR = ("acilislar", "ilk_indirmeler", "kat_kayitlari")
MUHUR_IZI = "e3ac28faeea8d55acc3d4ad99f9ee1084f2fdedf6eae3df852d0b1e389b65efb"


def _iz(m: dict) -> str:
    donmus = {k: v for k, v in m.items() if k not in EKLENEBILIR}
    return hashlib.sha256(json.dumps(donmus, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def test_muhurun_dondurulmus_bolumleri_degismez(muhur):
    """Mühür birleştikten sonra yalnız `acilislar`, `ilk_indirmeler` ve `kat_kayitlari`'na ekleme yapılır (her biri ayrı commit'le);
    öteki bölümlerden biri değişirse iz tutmaz: hakem değişikliğidir, beyanla ve Patron'un onayıyla gelir."""
    assert set(muhur) == {"aciklama", "kaynaklar", "kat_ayrimi", "secim_kurali", "secim", "sayilar", "projeler", "dosyalar",
                          *EKLENEBILIR}
    assert _iz(muhur) == MUHUR_IZI


def test_eklenen_kayitlar_kurala_uygun(muhur):
    """İlk indirme yalnız SHA'sı bekleyen kayda, mühürdeki bayt ve Drive saatiyle; açılış yalnız kör ya da kapalı listeye, o dosyanın
    özetiyle; kat kaydı yalnız kat sayısı belirsiz projeye."""
    D = {r["drive_id"]: r for r in muhur["dosyalar"]}
    P = muhur["projeler"]
    for did, k in muhur["ilk_indirmeler"].items():
        r = D[did]
        assert set(k) == {"sha256", "bayt", "drive_degisme", "tarih"} and re.fullmatch(r"[0-9a-f]{64}", k["sha256"])
        assert r["sha256"] is None and (k["bayt"], k["drive_degisme"]) == (r["bayt"], r["drive_degisme"])
    assert set(muhur["acilislar"]["ÇP-06"]) == {"tarih", "dayanak"}
    for kod, a in muhur["acilislar"].items():
        if kod == "ÇP-06":
            continue
        assert P[kod]["durum"] in ("kor", "kapali") and set(a) == {"karar", "tarih", "sha256", "liste_commit"}
        assert any(K.kayit_ozeti(r, muhur) == a["sha256"] for r in muhur["dosyalar"] if r["kod"] == kod and r["tur"] in K.LISTELER)
    for kod, k in muhur["kat_kayitlari"].items():
        assert P[kod]["kat"] == "belirsiz" and set(k) == {"kat", "tarih", "dayanak"} and k["kat"] in ("tek", "çift")


def test_kor_ve_kapali_listelerin_sha_si_yok(muhur):
    """Kör ve kapalı listeler indirilmedi: SHA'ları ilk indirmede (açılışta) alınır."""
    for r in muhur["dosyalar"]:
        if r["durum"] in ("kor", "kapali"):
            assert r["sha256"] is None, r["drive_id"]


def test_acik_secimi_yazili_kuraldan(muhur):
    """`secim_kurali` mühürdeki alanlarla yeniden kurulur: aynı dört proje."""
    P = muhur["projeler"]

    def bant(m2):
        return "A" if m2 <= 70 else "B" if m2 < 90 else "H" if m2 < 100 else "C" if m2 <= 130 else "D"

    uygun = {k: p for k, p in P.items() if p["durum"] != "hedef" and p["kat"] == "tek"}
    sira = lambda b: sorted((k for k, p in uygun.items() if bant(p["m2"]) == b), key=lambda k: (uygun[k]["liste_tarihi"], k))  # noqa: E731
    secim = {b: (sira(b) or [None])[-1] for b in "ABCD"}
    for b in "ABCD":
        if secim[b] is None:
            secim[b] = next(k for k in reversed(sira("H")) if k not in secim.values())
    assert secim == muhur["secim"]
    assert sorted(secim.values()) == ACIK


@pytest.mark.parametrize("liste", [None, {"commit": "0" * 40}])
def test_kor_ve_kapali_acilis_kaydi_olmadan_reddedilir(muhur, liste):
    n = 0
    for r in muhur["dosyalar"]:
        if r["durum"] in ("kor", "kapali"):
            with pytest.raises(Durdu) as e:
                K.acilabilir_mi(r, muhur, r["kod"], liste)
            assert e.value.adim == 3
            n += 1
    assert n == 38


def test_hedef_cevabi_mühürle_ve_kendi_icinde_tutarli(muhur):
    c = _oku(CEVAP)
    kayit = {r["sha256"]: r for r in muhur["dosyalar"] if r["sha256"]}
    assert kayit[c["liste_sha256"]]["kod"] == "ÇP-06" and kayit[c["liste_sha256"]]["tur"] == K.LISTE
    assert kayit[c["pafta_sha256"]]["kod"] == "ÇP-06" and kayit[c["pafta_sha256"]]["tur"] == K.PAFTA
    s = c["celik"]["satirlar"]
    assert c["celik"]["toplam"] == {"adet": sum(x["adet"] for x in s), "kg": sum(x["kg"] for x in s)} == {"adet": 51, "kg": 2122}
    assert {h: x["adet"] for h, x in c["pafta"].items()} == {"D": 26, "K": 4, "M": 13, "C": 2}
    assert c["pafta_liste"] == {"duvar_paneli": "aynı", "kolon_kiris": "aynı", "makas": "aynı", "cati_paneli": "aynı"}
    assert c["pafta_uyarilari"] == []


# ----------------------------------------------------------------------------------------------------------- okuyucular

@pytest.mark.parametrize("ad,beklenen", [
    ("DUVAR PANELLERİ", "duvar_paneli"), ("KOLON - KİRİŞ PANELLERİ", "kolon_kiris"), ("ÇATI MAKASLARI", "makas"),
    ("ÇATI PANELLERİ", "cati_paneli"), ("TAVAN PANELLERİ", "tavan_paneli"), ("Boy C Profil", "c_profil"), ("Duvar paneli", "duvar_paneli"),
])
def test_tur(ad, beklenen):
    assert oku.tur(ad) == beklenen


@pytest.mark.parametrize("ad", ["ÇELİK KUTU", "DUVAR MAKAS PANELİ"])
def test_tur_bilinmiyor_ya_da_belirsizse_durur(ad):
    with pytest.raises(oku.OkumaHatasi):
        oku.tur(ad)


def _beklenen_celik():
    return {"duvar_paneli": (10, 520), "kolon_kiris": (2, 44), "makas": (6, 240), "cati_paneli": (1, 60), "c_profil": (2, 10)}


@pytest.mark.parametrize("bicim", ["xlsx", "pdf"])
def test_liste_okuyucu(tmp_path, bicim):
    yol = tmp_path / f"liste.{bicim}"
    (_liste_xlsx if bicim == "xlsx" else _liste_pdf)(yol)
    sayac = {}
    r = oku.oku(yol, f".{bicim}", sayac=sayac)
    assert {t: (x["adet"], x["kg"]) for t, x in r["celik"]["turler"].items()} == _beklenen_celik()
    assert r["celik"]["toplam"] == {"adet": 21, "kg": 874}
    metin = json.dumps(r, ensure_ascii=False)
    assert UYDURMA_AD not in metin and UYDURMA_TEL not in metin, "başlık bloğu ve personel satırı okunmaz"
    assert [(s["malzeme"], s["adet"]) for s in r["satirlar"] if not oku.celik_grubu_mu(s["grup"])] == [("KÖŞEBENT", 20), ("AŞIK", 15)]
    assert all(oku.katla(s["malzeme"]) != "TOPLAM" for s in r["satirlar"])


def test_toplam_satiri_tutmazsa_durur(tmp_path):
    yol = tmp_path / "liste.xlsx"
    _liste_xlsx(yol, toplam=(21, 900))
    with pytest.raises(oku.OkumaHatasi, match="TOPLAM"):
        oku.oku(yol, ".xlsx")


def test_bilinmeyen_celik_satiri_durur(tmp_path):
    yol = tmp_path / "liste.xlsx"
    _liste_xlsx(yol, celik=[*CELIK, ("ÇELİK KUTU", "40X40", 1, 5)])
    with pytest.raises(oku.OkumaHatasi, match="türü bilinmiyor"):
        oku.oku(yol, ".xlsx")


def test_pafta_etiketleri(tmp_path):
    yol = tmp_path / "pafta.pdf"
    _pafta_pdf(yol, [["D01", "D02", "D03", "D05", "K01", "DN01", "D1", "AD01", "D01A", "M01"], ["M01", "M02", "C01", "C02"]])
    e = pafta.etiketler(yol)
    T = e["turler"]
    assert {h: x["adet"] for h, x in T.items()} == {"D": 4, "K": 1, "M": 2, "C": 2}
    assert T["D"]["eksik"] == [4] and T["D"]["en_buyuk"] == 5
    assert T["M"]["yinelenen"] == ["M01"] and T["M"]["sayfalar"] == [1, 2]
    assert e["uyarilar"] == ["D: eksik numara D04", "M: birden çok yerde geçen etiket M01"]


# ------------------------------------------------------------------------------------------------------- sıra ve kapı

BIZIM = [
    {"grup": "Çelik panel", "malzeme": "Duvar paneli", "boyut": "80X45X10X1,2", "adet": 10, "kg": 530.0},
    {"grup": "Çelik panel", "malzeme": "Kolon-kiriş paneli", "boyut": "80X45X10X1,2", "adet": 2, "kg": 44.0},
    {"grup": "Çelik panel", "malzeme": "Makas", "boyut": "80X45X10X0,8", "adet": 7, "kg": 250.0},
    {"grup": "Çelik panel", "malzeme": "Çatı paneli", "boyut": "80X45X10X1,2", "adet": 1, "kg": 60.0},
    {"grup": "Çelik panel", "malzeme": "Boy C profil", "boyut": "80X45X10X0,8", "adet": 2, "kg": 10.0},
    {"grup": "Çelik panel", "malzeme": "Toplam (adedi ve kg'ı bilinenler)", "adet": 22, "kg": 894.0},
    {"grup": "Metal aksam", "malzeme": "Köşebent", "boyut": "30 × 30 × 2500", "adet": 20},
    {"grup": "Metal aksam", "malzeme": "Aşık", "boyut": "L 4200", "adet": 14},
    {"grup": "Metal aksam", "malzeme": "Alın sacı", "boyut": "2500", "adet": 3},
]


@pytest.fixture
def depo(tmp_path):
    """Geçici depo: uydurma mühür (açık liste, kör liste, pafta, SHA'sı bekleyen liste) ve kendi listemiz; kaynaklar depo dışında."""
    kok = tmp_path / "depo"
    cel = kok / "testler" / "celik"
    pd = cel / "projeler" / "DN01"
    pd.mkdir(parents=True)
    dis = tmp_path / "disari"
    dis.mkdir()
    acik, kor, pf, bek = dis / "acik.xlsx", dis / "kor.xlsx", dis / "pafta.pdf", dis / "bekleyen.xlsx"
    _liste_xlsx(acik)
    _liste_xlsx(kor, celik=CELIK[:-1])
    _pafta_pdf(pf, [["D01", "D02", "K01", "M01"]])
    _liste_xlsx(bek, celik=CELIK[1:])

    def kayit(kod, tur, yol, durum, sha=True):
        return {"kod": kod, "tur": tur, "uzanti": yol.suffix, "bayt": yol.stat().st_size, "drive_id": "x" * 20 + yol.stem.ljust(13, "_"),
                "drive_degisme": "2026-09-17T05:54:42.192Z", "sha256": _sha(yol) if sha else None, "durum": durum}

    muhur = {"aciklama": "uydurma", "projeler": {k: {"m2": 50, "kat": "tek", "liste_tarihi": "2026-09-17", "drive_klasor": "y" * 33,
                                                      "durum": d} for k, d in (("DN-01", "acik"), ("DN-02", "kor"), ("DN-03", "acik"))},
             "acilislar": {}, "ilk_indirmeler": {}, "kat_kayitlari": {},
             "dosyalar": [kayit("DN-01", "yükleme listesi", acik, "acik"), kayit("DN-01", "montaj paftası", pf, "kaynak"),
                          kayit("DN-02", "yükleme listesi", kor, "kor"), kayit("DN-03", "yükleme listesi", bek, "acik", sha=False)]}
    (cel / "muhur.json").write_text(json.dumps(muhur, ensure_ascii=False), encoding="utf-8")
    for kod, ad in (("DN-01", "DN01"), ("DN-02", "DN02"), ("DN-03", "DN03")):
        (cel / "projeler" / ad).mkdir(exist_ok=True)
        (cel / "projeler" / ad / "bizim_liste.json").write_text(json.dumps({"kod": kod, "satirlar": BIZIM}, ensure_ascii=False),
                                                               encoding="utf-8")
    _git(kok, "init", "-q")
    _git(kok, "add", ".")
    _git(kok, "commit", "-q", "-m", "uydurma")
    return {"kok": kok, "cel": cel, "muhur": cel / "muhur.json", "acik": acik, "kor": kor, "pafta": pf, "bekleyen": bek,
            "bizim": lambda ad: cel / "projeler" / ad / "bizim_liste.json"}


def _muhur_degistir(depo, f):
    m = _oku(depo["muhur"])
    f(m)
    depo["muhur"].write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    _git(depo["kok"], "commit", "-q", "-am", "mühür")


@pytest.fixture
def okunmaz(monkeypatch):
    """Okuyucu çağrılırsa test düşer: mühür ya da açılış tutmadığında dosya içeriği okunmamalı."""
    def dur(*a, **k):
        raise AssertionError("dosya okundu")
    monkeypatch.setattr(K.oku, "oku", dur)
    monkeypatch.setattr(K.pafta, "etiketler", dur)


def test_kiyas_acik_liste(depo, tmp_path):
    k = K.kiyasla(depo["bizim"]("DN01"), depo["acik"], depo["pafta"], kok=depo["kok"])
    assert k["kapi"] == {"sonuc": "geçti", "fark_yuzde": round(100 * (894 - 874) / 874, 2), "pay_yuzde": 3.0}
    T = {r["tur"]: r for r in k["tablo"]}
    assert (T["makas"]["gercek_adet"], T["makas"]["bizim_adet"], T["makas"]["pafta_etiket"]) == (6, 7, 1)
    assert T["duvar_paneli"]["pafta_liste"] == "farklı"
    assert k["satir"]["sayilar"] == {"aynı": 1, "farklı": 1, "bizde yok": 0, "bizde fazla": 1}
    s = K.sonuc_kaydi(k)
    assert s["tutanlar"] == [{"grup": "METAL AKSAM", "ad": "KOSEBENT", "olcu": [30.0, 30.0, 2500.0], "adet": 20}]
    assert {x["tur"] for x in s["celik_turleri_tutan"]} == {"duvar_paneli", "kolon_kiris", "cati_paneli", "c_profil"}
    assert "15" not in json.dumps(s["tutanlar"]), "tutmayan satırın gerçek adedi kayda girmez"
    K.rapor_md(k, tmp_path / "r.md")
    metin = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "geçti" in metin and UYDURMA_AD not in metin and "acik.xlsx" not in metin


@pytest.mark.parametrize("bizim_kg,sonuc", [(874 * 1.03, "geçti"), (874 * 0.97, "geçti"), (874 * 1.0301, "geçmedi"),
                                            (874 * 0.9699, "geçmedi"), (None, "koşulmadı")])
def test_kg_kapisi_siniri(bizim_kg, sonuc):
    assert K.kg_kapisi(bizim_kg, 874)["sonuc"] == sonuc


def test_bizim_kg_eksikse_kapi_kosulmaz():
    b = K.bizim_celik([{**BIZIM[0], "kg": None}, *BIZIM[1:5]])
    assert b["toplam"]["kg"] is None and K.kg_kapisi(b["toplam"]["kg"], 874)["sonuc"] == "koşulmadı"


def test_bir_bayti_degisen_liste_okunmadan_durur(depo, tmp_path, okunmaz):
    bozuk = tmp_path / "bozuk.xlsx"
    b = bytearray(depo["acik"].read_bytes())
    b[len(b) // 2] ^= 1
    bozuk.write_bytes(bytes(b))
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN01"), bozuk, kok=depo["kok"])
    assert e.value.adim == 2 and "hiçbir kayıtta yok" in e.value.neden


def test_baska_projenin_listesi_okunmaz(depo, okunmaz):
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN01"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 2 and "DN-02" in e.value.neden


def test_pafta_mühürsüzse_okunmaz(depo, tmp_path, okunmaz):
    p = tmp_path / "baska.pdf"
    _pafta_pdf(p, [["D01"]])
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN01"), depo["acik"], p, kok=depo["kok"])
    assert e.value.adim == 2


def test_kendi_listemiz_kayitli_degilse_acilmaz(depo, okunmaz):
    y = depo["bizim"]("DN01")
    y.write_text(y.read_text(encoding="utf-8").replace('"adet": 10', '"adet": 11'), encoding="utf-8")
    with pytest.raises(Durdu) as e:
        K.kiyasla(y, depo["acik"], kok=depo["kok"])
    assert e.value.adim == 1


def test_muhur_degismisse_durur(depo, okunmaz):
    depo["muhur"].write_text(depo["muhur"].read_text(encoding="utf-8").replace("uydurma", "uydurma "), encoding="utf-8")
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN01"), depo["acik"], kok=depo["kok"])
    assert e.value.adim == 2 and "değişmiş" in e.value.neden


def test_kor_liste_acilis_kaydi_olmadan_reddedilir_ve_cevabi_cikmaz(depo, okunmaz):
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3
    with pytest.raises(Durdu) as e:
        K.cevap("DN-02", depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3 and "kıyastan önce" in e.value.neden


def test_kor_liste_acilis_kaydiyla_acilir(depo):
    liste_commit = subprocess.run(["git", "-C", str(depo["kok"]), "log", "-1", "--format=%H", "--", "testler/celik/projeler/DN02"],
                                  capture_output=True, text=True).stdout.strip()

    def ac(m, sha=_sha(depo["kor"]), c=liste_commit):
        m["acilislar"]["DN-02"] = {"karar": "uydurma karar", "tarih": "2026-10-25", "sha256": sha, "liste_commit": c[:7]}

    _muhur_degistir(depo, lambda m: ac(m, sha="0" * 64))
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3 and "bu dosya için değil" in e.value.neden
    _muhur_degistir(depo, lambda m: ac(m, c="1234567"))
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3 and "commit" in e.value.neden
    _muhur_degistir(depo, ac)
    k = K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert k["acilis"]["durum"] == "kor" and k["celik"]["toplam"] == {"adet": 19, "kg": 864}


def test_kati_belirsiz_kor_liste_kat_kaydi_olmadan_acilmaz(depo):
    liste_commit = subprocess.run(["git", "-C", str(depo["kok"]), "log", "-1", "--format=%H", "--", "testler/celik/projeler/DN02"],
                                  capture_output=True, text=True).stdout.strip()

    def ac(m):
        m["projeler"]["DN-02"]["kat"] = "belirsiz"
        m["acilislar"]["DN-02"] = {"karar": "uydurma karar", "tarih": "2026-10-25", "sha256": _sha(depo["kor"]),
                                   "liste_commit": liste_commit[:7]}

    _muhur_degistir(depo, ac)
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3 and "kat sayısı belirsiz" in e.value.neden
    _muhur_degistir(depo, lambda m: m["kat_kayitlari"].update({"DN-02": {"kat": "çift", "tarih": "2026-10-26", "dayanak": "uydurma"}}))
    with pytest.raises(Durdu) as e:
        K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])
    assert e.value.adim == 3 and "çift katlı" in e.value.neden
    _muhur_degistir(depo, lambda m: m["kat_kayitlari"]["DN-02"].update(kat="tek"))
    assert K.kiyasla(depo["bizim"]("DN02"), depo["kor"], kok=depo["kok"])["acilis"]["durum"] == "kor"


def test_sha_si_bekleyen_kayit_ilk_indirmeyle_okunur(depo):
    bizim = depo["bizim"]("DN03")
    with pytest.raises(Durdu) as e:
        K.kiyasla(bizim, depo["bekleyen"], kok=depo["kok"])
    assert e.value.adim == 2 and "ilk indirmede" in e.value.neden
    m = K.muhur_oku(depo["muhur"])
    with pytest.raises(Durdu) as e:
        K.ilk_indirme("DN-03", depo["bekleyen"], "2026-10-01T00:00:00Z", m)
    assert "değişmiş" in e.value.neden
    kayit = K.ilk_indirme("DN-03", depo["bekleyen"], "2026-09-17T05:54:42.192Z", m)
    (did, ilk), = kayit.items()
    assert ilk["sha256"] == _sha(depo["bekleyen"]) and ilk["bayt"] == depo["bekleyen"].stat().st_size
    _muhur_degistir(depo, lambda m: m["ilk_indirmeler"].update({did: {**ilk, "drive_degisme": "2026-10-01T00:00:00Z"}}))
    with pytest.raises(Durdu) as e:
        K.kiyasla(bizim, depo["bekleyen"], kok=depo["kok"])
    assert e.value.adim == 2 and "Drive saati" in e.value.neden
    _muhur_degistir(depo, lambda m: m["ilk_indirmeler"].update(kayit))
    k = K.kiyasla(bizim, depo["bekleyen"], kok=depo["kok"])
    assert k["ozet"] == ilk["sha256"] and k["celik"]["toplam"]["adet"] == 15


def test_cevap_acik_listede(depo, tmp_path):
    c = K.cevap("DN-01", depo["acik"], depo["pafta"], kok=depo["kok"])
    j = K.cevap_json(c)
    assert j["celik"]["toplam"] == {"adet": 21, "kg": 874} and j["pafta"]["D"]["adet"] == 2
    K.cevap_md(c, tmp_path / "c.md")
    metin = (tmp_path / "c.md").read_text(encoding="utf-8")
    assert "KÖŞEBENT" not in metin, "öteki grupların içeriği cevap sayfasına yazılmaz"
    assert "| METAL AKSAM GRUBU | 2 |" in metin


# --------------------------------------------------------------------------------------------------------------- tam koşu

KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
@pytest.mark.parametrize("uzanti", [".xlsx", ".pdf"])
def test_tam_kosu_hedef_cevabi(muhur, uzanti, tmp_path):
    hedef = [r for r in muhur["dosyalar"] if r["kod"] == "ÇP-06" and r["sha256"]]
    liste = next(Path(KAYNAK) / f"{r['drive_id']}{r['uzanti']}" for r in hedef if r["tur"] == K.LISTE and r["uzanti"] == uzanti)
    pf = next(Path(KAYNAK) / f"{r['drive_id']}{r['uzanti']}" for r in hedef if r["tur"] == K.PAFTA)
    j = K.cevap_json(K.cevap("ÇP-06", liste, pf))
    beklenen = {k: v for k, v in _oku(CEVAP).items() if k not in ("aciklama", "tarih")}
    assert {**j, "liste_sha256": None} == {**beklenen, "liste_sha256": None}
    bozuk = tmp_path / f"bozuk{uzanti}"
    b = bytearray(liste.read_bytes())
    b[-10] ^= 1
    bozuk.write_bytes(bytes(b))
    with pytest.raises(Durdu) as e:
        K.cevap("ÇP-06", bozuk, pf)
    assert e.value.adim == 2
