"""İE-16 PR-4b · hakemin sonuç kayıtları (`projeler/*/sonuc.json`; plan `Celik_Cizim_Kurallari/PR-4/plan.md`, adım 11, PR-2'nin açık
sorusu).

- `sonuc.json` elle yazılmaz: kaynaklı koşuda (`PORTMAN_CELIK_KAYNAK`) hakem mühürdeki kıyas listesiyle yeniden koşturulur, tarih ve kıyas
  commit'i dışında aynı kayıt çıkar. PR-2'den beri yalnız ÇP-06'da vardı (`test_cp06.py`); burada bütün projelerde.
- Mühüre yalnız ekleme yapılır (ilk indirme, kat ve açılış kayıtları), her biri ayrı commit: sonucun mühür commit'i bugünkünden eski
  olabilir. O commit mühürün geçmişinde olmalı; eklemeler projenin kaydını değiştirmez (hakem eklenebilir bölümlerde değişmeyi durdurur),
  kalan alanlar aynı olmalı (`muhur_commit_denetle`).
- Kaynaksız koşuda kaydın kendisi denetlenir: listemizin bugünkü commit'ine bağlı, mühürdeki kıyas listesinin özetini taşıyor, kör ya da
  kapalı projede `main`'e giren açılış kaydı var, fark yalnız kapı geçtiyse yazılı, tutanlar yalnız bizim adedimizi taşıyor.
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
from testler.kor.kiyas import kayitli_mi  # noqa: E402

BURADA = Path(__file__).resolve().parent
KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")
MUHUR = json.loads(kiyas.MUHUR.read_text(encoding="utf-8"))
SONUCLAR = sorted(BURADA.glob("*/sonuc.json"))
IDS = [p.parent.name for p in SONUCLAR]


def oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def kiyas_listesi(kod: str) -> dict:
    drive_id = MUHUR["projeler"][kod]["kiyas_listesi"]
    (r,) = [r for r in MUHUR["dosyalar"] if r["kod"] == kod and r["drive_id"] == drive_id]
    return r


def muhur_commit_denetle(yeni: dict, kayitli: dict) -> None:
    """Kayıttaki mühür commit'i mühürün geçmişinde (o commit'ten sonra mühüre yalnız ekleme yapıldı); sonra iki kayıttan da çıkarılır."""
    c = kayitli["muhur"].pop("muhur_commit")
    gecmis = subprocess.run(["git", "-C", str(KOK), "rev-list", "HEAD", "--", "testler/celik/muhur.json"], capture_output=True, text=True)
    if c not in gecmis.stdout.split():
        sig = subprocess.run(["git", "-C", str(KOK), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True)
        if sig.stdout.strip() == "true":
            pytest.skip(f"sığ klon: {c[:7]} yok")
        raise AssertionError(f"sonucun mühür commit'i ({c[:7]}) mühürün geçmişinde değil")
    yeni["muhur"].pop("muhur_commit")


def test_her_sonucun_listemiz_var():
    assert SONUCLAR
    for p in SONUCLAR:
        s = oku(p)
        assert kiyas.kod_klasoru(s["kod"]) == p.parent.name and (p.parent / "bizim_liste.json").exists(), p


@pytest.mark.parametrize("yol", SONUCLAR, ids=IDS)
def test_sonuc_kaydinin_kendisi(yol):
    s = oku(yol)
    kod = s["kod"]
    liste = kayitli_mi(yol.parent / "bizim_liste.json", KOK, 1)
    assert s["bizim_liste"] == {"yol": liste["yol"], "commit": liste["commit"]}, "sonuç listemizin bugünkü commit'ine bağlı değil"
    kayit = kiyas_listesi(kod)
    assert s["muhur"]["sha256"] == kiyas.kayit_ozeti(kayit, MUHUR) and s["muhur"]["bayt"] == kayit["bayt"], "mühürdeki kıyas listesi değil"
    assert s["muhur"]["kayit_durumu"] == kayit["durum"]
    if kayit["durum"] != "acik":                 # kör ya da kapalı: açılış kaydı bu dosyanın ve listemizin
        acilis = MUHUR["acilislar"][kod]
        assert acilis["sha256"] == s["muhur"]["sha256"] and acilis["liste_commit"] == liste["commit"]
        assert s["muhur"]["durum"] == kiyas.etkin_durum(kayit, MUHUR, kod)
    kapi = s["celik_kg_kapisi"]
    assert kapi["sonuc"] in ("geçti", "geçmedi") and kapi["pay_yuzde"] == 3.0
    assert (kapi["fark_yuzde"] is None) == (kapi["sonuc"] != "geçti"), "fark yalnız kapı geçtiyse yazılır"
    assert s["sayilar"]["aynı"] == len(s["tutanlar"])
    assert all(set(t) == {"grup", "ad", "olcu", "adet"} for t in s["tutanlar"])
    assert all(set(t) == {"tur", "adet"} for t in s["celik_turleri_tutan"])


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
@pytest.mark.parametrize("yol", SONUCLAR, ids=IDS)
def test_sonuc_hakemin_ciktisi(yol):
    """Hakem bugünkü listemizle ve mühürdeki kıyas listesiyle yeniden koşunca tarih ve kıyas commit'i dışında aynı kayıt çıkar."""
    kod = oku(yol)["kod"]
    kayit = kiyas_listesi(kod)
    k = kiyas.kiyasla(yol.parent / "bizim_liste.json", Path(KAYNAK) / f"{kayit['drive_id']}{kayit['uzanti']}")
    yeni, kayitli = kiyas.sonuc_kaydi(k), oku(yol)
    for d in (yeni, kayitli):
        d.pop("tarih"), d.pop("kiyas_commit")
    muhur_commit_denetle(yeni, kayitli)
    assert yeni == kayitli
