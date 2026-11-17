"""Disk arşivinin mührü ve kodlu dizini (İE-43, D-99): araç ve depodaki kayıt.

Araç geçici bir arşivde denenir (kodlar, ad sızmaması, SHA farkında durma, kaldığı yerden devam, kopya doğrulama).
Depodaki `testler/hdd/muhur.csv` ve `dizin.json` birbirini tutar ve yalnız beklenen biçimde alan taşır (ad yok).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "araclar"))
import hdd_dizin  # noqa: E402

MUHUR = KOK / "testler" / "hdd" / "muhur.csv"
DIZIN = KOK / "testler" / "hdd" / "dizin.json"

ADLAR = ["Zeynep Çağlar 74 m2", "01.04.2019 Ali Veli", "Ömer Şahin REVİZE"]


def _arsiv(tmp_path: Path) -> Path:
    kok = tmp_path / "Portman_HDD_Projeler"
    dosyalar = {
        ADLAR[0]: {"Zeynep Çağlar plan.pdf": b"plan", "liste/Yükleme Listesi.xlsx": b"liste"},
        ADLAR[1]: {"Ali Veli.dwg": b"dwg", "resim.JPG": b"jpg"},
        ADLAR[2]: {"Ömer Şahin sözleşme.xlsx": b"sozlesme"},
    }
    kaynak = {ADLAR[0]: "Monster Masaüstü(30.06.2020)/Prefabrik Müşterilerim/",
              ADLAR[1]: "Monster Masaüstü(30.06.2020)/Çelik Müşterilerim/ali veli/",
              ADLAR[2]: "İKRANUR ORTAK KLASÖR/REVİZELER/"}
    satirlar = [["Proje klasörü", "Dosya (proje klasörü içinde)", "Kaynak yol (Elements diski)", "Boyut (KB)",
                 "Değişiklik tarihi", "Durum", "İçerik özeti (SHA-256)"]]
    projeler = [["Proje klasörü"] + [""] * 8 + ["Ana kaynak klasör (Elements diski)", "Birleştirilen kopya klasörler"]]
    for klasor, icerik in dosyalar.items():
        projeler.append([klasor] + [""] * 8 + [kaynak[klasor] + klasor, ""])
        for ad, veri in icerik.items():
            yol = kok / klasor / ad
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_bytes(veri)
            satirlar.append([klasor, ad, "x/" + ad, "0,1", "09.04.2019", "alındı", hashlib.sha256(veri).hexdigest()])
    satirlar.append([ADLAR[0], "kopya.pdf", "y/kopya.pdf", "0,1", "09.04.2019", "aynı dosya, kopyası atlandı", "0" * 64])
    for ad, tablo in (("_kaynak_listesi.csv", satirlar), ("_projeler.csv", projeler)):
        with open(kok / ad, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, delimiter=";").writerows(tablo)
    return kok


def test_kur_kodlar_ve_ad_sizmaz(tmp_path):
    kok = _arsiv(tmp_path)
    depo = tmp_path / "depo"
    assert hdd_dizin.main(["kur", str(kok), "--depo", str(depo)]) == 0
    muhur = (depo / "testler/hdd/muhur.csv").read_text(encoding="utf-8")
    dizin = json.loads((depo / "testler/hdd/dizin.json").read_text(encoding="utf-8"))
    for parca in ("Zeynep", "Çağlar", "Ali", "Veli", "Ömer", "Şahin", "plan", "Yükleme", "sözleşme", "Monster", "İKRANUR"):
        assert parca not in muhur
        assert parca not in json.dumps(dizin, ensure_ascii=False).replace("Elements diskinin", "")
    satirlar = list(csv.DictReader(muhur.splitlines(), delimiter=";"))
    assert len(satirlar) == 5  # kopyası atlanan sayılmaz
    # düz sıralama: "01.04…" < "Zeynep…" < "Ömer…"
    assert [s["kod"] for s in satirlar] == ["HD-001", "HD-001", "HD-002", "HD-002", "HD-003"]
    assert dizin["projeler"]["HD-001"]["kaynak_bolumu"] == "celik"
    assert dizin["projeler"]["HD-002"]["kaynak_bolumu"] == "prefabrik"
    assert dizin["projeler"]["HD-003"]["kaynak_bolumu"] == "revize"
    assert dizin["projeler"]["HD-003"]["revize"] is True
    assert dizin["projeler"]["HD-002"]["uzantilar"] == {"pdf": 1, "xlsx": 1}
    assert dizin["projeler"]["HD-001"]["tarih_ilk"] == "2019-04-09"
    assert dizin["sayilar"]["dosya"] == 5 and dizin["sayilar"]["proje"] == 3
    esleme = list(csv.DictReader((kok / "_portman_analiz/kod_esleme.csv").read_text(encoding="utf-8-sig").splitlines(),
                                 delimiter=";"))
    assert esleme[0]["proje_klasoru"] == ADLAR[1] and esleme[0]["kod"] == "HD-001"


def test_kur_sha_farkinda_yazmaz(tmp_path):
    kok = _arsiv(tmp_path)
    (kok / ADLAR[1] / "Ali Veli.dwg").write_bytes(b"degisti")
    depo = tmp_path / "depo"
    assert hdd_dizin.main(["kur", str(kok), "--depo", str(depo)]) == 1
    assert not (depo / "testler/hdd/muhur.csv").exists()


def test_kur_sure_bitince_devam(tmp_path):
    kok = _arsiv(tmp_path)
    depo = tmp_path / "depo"
    assert hdd_dizin.main(["kur", str(kok), "--depo", str(depo), "--sure", "-1"]) == 2
    assert not (depo / "testler/hdd/muhur.csv").exists()
    assert hdd_dizin.main(["kur", str(kok), "--depo", str(depo)]) == 0


def test_dogrula_kopya(tmp_path):
    kok = _arsiv(tmp_path)
    depo = tmp_path / "depo"
    assert hdd_dizin.main(["kur", str(kok), "--depo", str(depo)]) == 0
    kopya = tmp_path / "Drive" / "Portman_HDD_Projeler"
    shutil.copytree(kok, kopya)
    esleme = str(kok / "_portman_analiz/kod_esleme.csv")
    arg = ["dogrula", str(kopya), "--depo", str(depo), "--esleme", esleme]
    assert hdd_dizin.main(arg + ["--onbellek", str(tmp_path / "o1.tsv")]) == 0
    (kopya / ADLAR[0] / "Zeynep Çağlar plan.pdf").write_bytes(b"bozuk")
    assert hdd_dizin.main(arg + ["--onbellek", str(tmp_path / "o2.tsv")]) == 1


# --- depodaki kayıt -------------------------------------------------------------------------------------------------

ALAN = {
    "kod": re.compile(r"HD-\d{3}"),
    "sira": re.compile(r"[1-9]\d*"),
    "uzanti": re.compile(r"[0-9a-z_~\-]{0,12}"),
    "bayt": re.compile(r"\d+"),
    "tarih": re.compile(r"(19|20)\d\d-\d\d-\d\d"),
    "sha256": re.compile(r"[0-9a-f]{64}"),
}


@pytest.fixture(scope="module")
def kayit():
    if not MUHUR.exists():
        pytest.skip("mühür henüz yok")
    with open(MUHUR, encoding="utf-8", newline="") as f:
        satirlar = list(csv.DictReader(f, delimiter=";"))
    return satirlar, json.loads(DIZIN.read_text(encoding="utf-8"))


def test_muhur_bicimi_ad_yok(kayit):
    satirlar, _ = kayit
    assert list(satirlar[0]) == hdd_dizin.MUHUR_BASLIK
    for s in satirlar:
        for alan, desen in ALAN.items():
            assert desen.fullmatch(s[alan]), (alan, s[alan])


def test_muhur_dizinle_tutar(kayit):
    satirlar, dizin = kayit
    say = dizin["sayilar"]
    assert len(satirlar) == say["dosya"]
    assert sum(int(s["bayt"]) for s in satirlar) == say["bayt"]
    assert len({s["sha256"] for s in satirlar}) == say["sha256_tekil"]
    kodlar = sorted(dizin["projeler"])
    assert kodlar == [f"HD-{i:03d}" for i in range(1, say["proje"] + 1)]
    for kod, p in dizin["projeler"].items():
        ps = [s for s in satirlar if s["kod"] == kod]
        assert [int(s["sira"]) for s in ps] == list(range(1, p["dosya"] + 1))
        assert sum(int(s["bayt"]) for s in ps) == p["bayt"]
        assert sum(p["uzantilar"].values()) == p["dosya"]
        assert p["kaynak_bolumu"] in {b for b, _ in hdd_dizin.BOLUMLER} | {"diger"}
