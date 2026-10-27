"""İE-16 PR-4 · kör ve kapalı projelerin listeleri (`projeler/*/bizim_liste.json`; plan `Celik_Cizim_Kurallari/PR-4/plan.md`, adım 6).

- Her liste ya açık beşin (ve hedef örneğin) listesidir (`test_listeler.py`) ya da mühürde kör veya kapalı olan bir projenindir.
- Kör listenin kural seti, karkas kuralı ve yazılış sözlüğü listeyle birlikte içerik adresli kopyasıyla donar (`setler/`); açılmadan önce
  liste bu kopyalarla girdilerinden yeniden üretilir (elle yazılmadı).
- Açıldıktan sonra liste yeniden üretilmez: ölçüm o günün kuralının ölçümüdür. Listemiz ve tanımı, Patron'un açılış kaydındaki commit'teki
  (`acilislar › liste_commit`) baytlarla aynı kalır.
- Donan sözlük de açık beşin sözlüğüyle aynı kurallardan geçer (adet taşımaz, ölçüye sabit sayı yazmaz, iki kalem bir satırı tutmaz).
- Kör tanım paftadan okunmuş makas yeri ve panel bölmesi taşımaz (karkas kuralından; kör kural yalnız 1. sayfa).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas  # noqa: E402
from testler.celik.projeler import liste_yap  # noqa: E402

BURADA = Path(__file__).resolve().parent
ACIK_BES = ["CP03", "CP06", "CP07", "CP13", "CP14"]
MUHUR = json.loads(kiyas.MUHUR.read_text(encoding="utf-8"))
HEPSI = sorted(BURADA.glob("*/bizim_liste.json"))
KOR = [p for p in HEPSI if p.parent.name not in ACIK_BES]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_her_liste_acik_bes_ya_da_kor():
    assert sorted(p.parent.name for p in HEPSI if p.parent.name in ACIK_BES) == ACIK_BES
    for p in KOR:
        kod = oku(p)["kod"]
        assert kiyas.kod_klasoru(kod) == p.parent.name and liste_yap.sozluk_donar_mi(kod), p
        assert MUHUR["projeler"][kod]["durum"] in liste_yap.DONAN_SOZLUK


def _kopya(kayit: dict) -> Path:
    k = KOK / kayit["kopya"]
    assert k.parent == liste_yap.SETLER and k.name == kayit["sha256"][:16] + ".json" and sha(k) == kayit["sha256"], kayit
    return k


def _git_show(commit: str, yol: Path) -> bytes:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{commit}:{yol.relative_to(KOK).as_posix()}"], capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    return r.stdout


@pytest.mark.parametrize("yol", KOR, ids=[p.parent.name for p in KOR])
def test_kor_liste_donar(yol, tmp_path):
    b = oku(yol)
    tanim = KOK / b["tanim"]["yol"]
    assert tanim.parent == yol.parent and b["tanim"]["sha256"] == sha(tanim), "tanım değişti"
    kopya, sozluk = _kopya(b["kural_seti"]), _kopya(b["sozluk"])
    assert oku(kopya).get("sema") == b["kural_seti"]["sema"] and oku(sozluk)["surum"] == b["sozluk"]["surum"]
    kk = b.get("karkas_kurali")
    assert kk and oku(tanim).get("karkas") == "kural"
    kk_kopya = _kopya(kk)
    acilis = (MUHUR.get("acilislar") or {}).get(b["kod"])
    if acilis:                       # açıldı: yeniden üretilmez; açılış kaydındaki commit'in baytları
        c = acilis["liste_commit"]
        assert re.fullmatch(r"[0-9a-f]{40}", c), c
        assert _git_show(c, yol) == yol.read_bytes(), "açılıştan sonra listemiz değişti"
        assert _git_show(c, tanim) == tanim.read_bytes(), "açılıştan sonra tanım değişti"
        return
    yukleme = liste_yap.motor(tanim, tmp_path, b["yontem"]["kod"], kopya, kk_kopya)
    assert liste_yap.liste(tanim, yukleme, b["yontem"]["kod"], b["kural_seti"], karkas_kaydi=kk, sozluk_donmus=b["sozluk"]) == b


@pytest.mark.parametrize("yol", KOR, ids=[p.parent.name for p in KOR])
def test_donan_sozluk_kurallari(yol):
    b = oku(yol)
    s = oku(KOK / b["sozluk"]["kopya"])
    izinli = {"bizim", "ad", "olcu", "grup", "renkli", "not"}
    for k in s["kalemler"]:
        assert set(k) <= izinli, k
        olcu = k.get("olcu", "")
        assert set(re.findall(r"\{([^}]*)\}", olcu)) <= {"0", "1", "2", "a0", "a1"}, k
        assert not re.search(r"\d", re.sub(r"\{a?\d\}", "", olcu)), f"ölçü yazılışında sabit sayı: {k}"
        assert not re.search(r"\d", k.get("grup", "")), k
    assert not any(re.search(r"\d", g) for g in s["gruplar"].values())
    for satir in b["satirlar"]:
        assert sum(1 for k in s["kalemler"] if re.search(k["bizim"], satir["kalem"])) <= 1, satir["kalem"]


@pytest.mark.parametrize("yol", KOR, ids=[p.parent.name for p in KOR])
def test_kor_tanim_paftanin_cevabini_tasimaz(yol):
    t = oku(KOK / oku(yol)["tanim"]["yol"])
    assert t["karkas"] == "kural" and "celik_modeli" not in t and "makaslar" not in t["cati"]
    assert not any(k in w for w in t["duvarlar"] for k in ("paneller", "bolme", "eklemler"))
    assert "1. sayfa" in t["kaynak"]["cizim"]
