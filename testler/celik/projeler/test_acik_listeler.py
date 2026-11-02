"""İE-16 PR-6b · açılan projelerin yeniden ölçümü (`projeler/<CPnn>/acik/`; hakemin kuralı İE-16 PR-6a).

- `acik/` yalnız açılış kaydı ve kör sonucu yazılmış projede durur; açık beşte yoktur (açık liste kendi klasöründe yeniden üretilir).
- `acik/bizim_liste.json` elle yazılmaz: projenin tanımından (bir üst klasörde, kör listeyle aynı dosya ve aynı baytlar) araçla yeniden
  üretilir; kural seti, karkas kuralı ve sözlük listeyle donan içerik adresli kopyalarından okunur.
- Kör ölçüm donar: projenin kendi listesi, tanımı ve `sonuc.json`'u değişmez (`test_kor_listeler.py`, `test_sonuclar.py`); `sonuc.json`
  geçmişinde tek sürümlüdür.
- `acik/sonuc.json` hakemin çıktısıdır: durumu `acildi`, kayıttaki durumu mühürdeki (kör ya da kapalı); fark yalnız kapı geçtiyse yazılı;
  kaynaklı koşuda (`PORTMAN_CELIK_KAYNAK`) hakem yeniden koşunca tarih ve kıyas commit'i dışında aynı kayıt çıkar.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas  # noqa: E402
from testler.celik.projeler import liste_yap  # noqa: E402
from testler.celik.projeler.test_kor_listeler import ACIK_BES, _kopya  # noqa: E402
from testler.celik.projeler.test_listeler import kural_kopyalari, sha, sozluk_kurallari  # noqa: E402
from testler.celik.projeler.test_sonuclar import kiyas_listesi, muhur_commit_denetle  # noqa: E402
from testler.kor.kiyas import kayitli_mi  # noqa: E402

BURADA = Path(__file__).resolve().parent
KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")
MUHUR = json.loads(kiyas.MUHUR.read_text(encoding="utf-8"))
LISTELER = sorted(BURADA.glob(f"*/{kiyas.YENIDEN}/bizim_liste.json"))
IDS = [p.parents[1].name for p in LISTELER]


def oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_acik_klasoru_yalniz_acilan_projede():
    """Açılan beşte (ÇP-04, 17, 18, 19, 20) var; ÇP-08'in listesinde kg yok, kör sonucu yazılmadı (yeniden ölçülmez); açık beşte yok."""
    assert IDS == ["CP04", "CP17", "CP18", "CP19", "CP20"]
    assert not any((BURADA / k / kiyas.YENIDEN).exists() for k in ACIK_BES + ["CP08"])
    for p in LISTELER:
        kod = oku(p)["kod"]
        assert kiyas.kod_klasoru(kod) == p.parents[1].name and kod in MUHUR["acilislar"], p
        assert MUHUR["projeler"][kod]["durum"] in liste_yap.DONAN_SOZLUK
        assert (p.parents[1] / "sonuc.json").exists() and (p.parent / "sonuc.json").exists()


@pytest.mark.parametrize("yol", LISTELER, ids=IDS)
def test_acik_liste_girdilerinden_yeniden_uretilir(yol, tmp_path):
    """Tanım projenin klasöründe (kör listenin tanımıyla aynı yol ve özet); liste donan kopyalarla yeniden üretilir."""
    b = oku(yol)
    tanim = KOK / b["tanim"]["yol"]
    assert tanim.parent == yol.parents[1] and b["tanim"]["sha256"] == sha(tanim), "tanım değişti"
    assert b["tanim"] == oku(yol.parents[1] / "bizim_liste.json")["tanim"]
    kopya, kk_kopya = kural_kopyalari(b, tanim)
    assert kk_kopya is not None and _kopya(b["sozluk"]) and oku(_kopya(b["sozluk"]))["surum"] == b["sozluk"]["surum"]
    yukleme = liste_yap.motor(tanim, tmp_path, b["yontem"]["kod"], kopya, kk_kopya)
    assert liste_yap.liste(tanim, yukleme, b["yontem"]["kod"], b["kural_seti"], karkas_kaydi=b["karkas_kurali"],
                           sozluk_donmus=b["sozluk"]) == b
    sozluk_kurallari(oku(_kopya(b["sozluk"])), [yol])


@pytest.mark.parametrize("yol", LISTELER, ids=IDS)
def test_kor_sonuc_tek_surumlu(yol):
    """Projenin kör `sonuc.json`'u geçmişinde bir kez yazılmış (hakem de denetler; burada her koşuda)."""
    s = yol.parents[1] / "sonuc.json"
    r = subprocess.run(["git", "-C", str(KOK), "log", "--format=%H", "--", s.relative_to(KOK).as_posix()], capture_output=True, text=True)
    sig = subprocess.run(["git", "-C", str(KOK), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True)
    if sig.stdout.strip() == "true":
        pytest.skip("sığ klon: geçmiş eksik olabilir")
    assert len(r.stdout.split()) == 1, r.stdout


@pytest.mark.parametrize("yol", LISTELER, ids=IDS)
def test_acik_sonuc_kaydinin_kendisi(yol):
    s = oku(yol.parent / "sonuc.json")
    kod = s["kod"]
    liste = kayitli_mi(yol, KOK, 1)
    assert s["bizim_liste"] == {"yol": liste["yol"], "commit": liste["commit"]}, "sonuç acik/ listesinin bugünkü commit'ine bağlı değil"
    kayit = kiyas_listesi(kod)
    assert s["muhur"]["sha256"] == kiyas.kayit_ozeti(kayit, MUHUR) and s["muhur"]["bayt"] == kayit["bayt"]
    assert (s["muhur"]["durum"], s["muhur"]["kayit_durumu"]) == ("acildi", kayit["durum"])
    assert MUHUR["acilislar"][kod]["sha256"] == s["muhur"]["sha256"]
    kapi = s["celik_kg_kapisi"]
    assert kapi["sonuc"] in ("geçti", "geçmedi") and kapi["pay_yuzde"] == 3.0
    assert (kapi["fark_yuzde"] is None) == (kapi["sonuc"] != "geçti"), "fark yalnız kapı geçtiyse yazılır"
    assert s["sayilar"]["aynı"] == len(s["tutanlar"])
    assert all(set(t) == {"grup", "ad", "olcu", "adet"} for t in s["tutanlar"])
    assert all(set(t) == {"tur", "adet"} for t in s["celik_turleri_tutan"])


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
@pytest.mark.parametrize("yol", LISTELER, ids=IDS)
def test_acik_sonuc_hakemin_ciktisi(yol):
    s = oku(yol.parent / "sonuc.json")
    kayit = kiyas_listesi(s["kod"])
    k = kiyas.kiyasla(yol, Path(KAYNAK) / f"{kayit['drive_id']}{kayit['uzanti']}")
    yeni, kayitli = kiyas.sonuc_kaydi(k), oku(yol.parent / "sonuc.json")
    for d in (yeni, kayitli):
        d.pop("tarih"), d.pop("kiyas_commit")
    muhur_commit_denetle(yeni, kayitli)
    assert yeni == kayitli
