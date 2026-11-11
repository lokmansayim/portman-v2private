"""Montaj sırası hakemi · rehberde örten parça örttüğünün üstündedir (Lokman, 10 Kasım 2026 20:16: "önce trapez sac ve mahya gelir sonra
alın sacı üzerini örter"; 20:17: "en küçük adımlarla gidelim çizgi çizgi gidelim").

Kurallar `kurallar/rehber/montaj_sirasi.json`'da, her biri tek ilişki (MS-01: alın sacı trapez sacı ve mahyayı örter). Hakem
`araclar/paket/rehber/sira.py` (`sira.js`): üst parçanın içinden 2 cm arayla noktalar, her noktadan çatı yüzüne dik doğrultuda 50 cm yukarı
ışın; ışın alt parçaya çarparsa bulgu. Geometriyi değiştirmez.

Cırcır: her evin bulguları `montaj_sirasi/acik.json`'daki bugünkü açık yerlerle birebir aynı olmalı. Yeni yer kırmızıdır (bir düzeltme başka
yeri bozdu). Düzelen yer de kırmızıdır: satır listeden çıkarılır, düzelme Lokman'a resimle gösterilir. Hakemin kör olmadığı iki yolla
sınanır: her kalkanın iki alın sacı da denetlenir, ve 16:22 sayfasının şablonu (git geçmişinden) 62 m²'de kurulunca hakem 6 mahya
ucunun 6'sını bulur. Düz mahya da alın sacının altındadır (Lokman, 10 Kasım 21:01). Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz, sira  # noqa: E402

ACIK = json.loads((KOK / "testler" / "paket" / "montaj_sirasi" / "acik.json").read_text(encoding="utf-8"))["evler"]
HAZIR = pytest.mark.skipif(iz.hazir() is not None, reason=f"montaj sırası hakemi: {iz.hazir()}")


def _veri(ev: str, girdi: str, tmp: Path) -> dict:
    """Evin rehber verisi: 62 m² hedef örneğin verisinden; teklif evleri İş Emri'nden (`veri.kur`, `uret.rehber` ile aynı yol)."""
    p = KOK / girdi
    if p.name == "veri.json":
        return json.loads(p.read_text(encoding="utf-8"))
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie, kod = json.loads(p.read_text(encoding="utf-8")), ev.replace("-", "")
    kart_model.uret(copy.deepcopy(ie), tmp, kod)
    return veri.kur(copy.deepcopy(ie), tmp, kod, PL.is_emrinden(copy.deepcopy(ie))["satirlar"], ev)


def _denetle(d: dict, tmp: Path) -> dict:
    from araclar.paket.rehber import sayfa
    s = sira.denetle(d, sayfa.yaz(d, tmp / "rehber.html"))
    assert s["hatalar"] == [], s["hatalar"][:3]
    return s


def test_kural_kitabi():
    ks = sira.kurallar()
    assert [k["no"] for k in ks] == [f"MS-{i:02d}" for i in range(1, len(ks) + 1)]   # sıralı, boşluksuz
    for k in ks:
        assert k["kural"] and k["soz"].startswith("Lokman, ") and k["ust"]["ad"] and k["ust"]["adim"] and k["alt"]["adim"], k["no"]
    # MS-01'in alt parçaları kaplama adımının hepsi: mahya türü ne olursa olsun alın sacının altına girer (Lokman, 10 Kasım 21:01)
    assert ks[0]["ust"] == {"adim": "alin", "ad": "Alın sacı", "bu_icerir": "üst kıvrım"} and ks[0]["alt"] == {"adim": "kaplama"}


def test_acik_listesi_bicimi():
    no = {k["no"] for k in sira.kurallar()}
    for ev, e in ACIK.items():
        assert (KOK / e["girdi"]).exists(), ev
        for a, neden in e["acik"].items():
            assert a.split(" · ")[0] in no and a.endswith(("· mahya üstünde", "· kaplama üstünde")) and neden, (ev, a)


@HAZIR
@pytest.mark.parametrize("ev", list(ACIK))
def test_montaj_sirasi(ev, tmp_path):
    d = _veri(ev, ACIK[ev]["girdi"], tmp_path)
    s = _denetle(d, tmp_path)
    for k in s["kurallar"]:   # hakem kör değil: her kalkanın iki yüzünün alın sacı ve örtülen parçalar denetlendi
        assert k["ust_parca"] == 2 * len(d["kalkan"]) and k["alt_parca"] > 0 and k["nokta"] > 1000 * k["ust_parca"], (ev, k["no"], k["ust_parca"])
    bul, acik = sira.anahtarlar(s), ACIK[ev]["acik"]
    yeni = {a: n for a, n in bul.items() if a not in acik}
    duzelen = [a for a in acik if a not in bul]
    assert not yeni, f"{ev}: montaj sırası bozuldu, {len(yeni)} yeni yer (nokta sayısıyla): {yeni}"
    assert not duzelen, f"{ev}: {len(duzelen)} yer düzeldi; montaj_sirasi/acik.json'dan çıkarın ve Lokman'a resimle gösterin: {duzelen}"


ESKI = "4c15f54b"   # main, 10 Kasım 2026 16:13 (PR #149): 16:22 sayfalarının şablonu; düz mahya kalkan ucuna kadar sürer, alın sacının üstüne biner


def _git(yol: str) -> str | None:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ESKI}:{yol}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


@HAZIR
def test_hakem_eski_hatayi_yakalar(tmp_path, monkeypatch):
    """Hakem kör değil: 16:22 sayfasının hatası (Lokman, 10 Kasım 20:15: "trapez sacı alın sacının üzerine koymuşsun"). O günkü şablon
    (`sahne.js`) ve 62 m² verisi git geçmişinden alınır (CI tam geçmişle koşar); hakem 6 mahya ucunun 6'sını bulur."""
    from araclar.paket.rehber import sayfa
    sahne, veri_ = _git("araclar/paket/rehber/sahne.js"), _git("testler/paket/rehber62/veri.json")
    if sahne is None or veri_ is None:
        pytest.skip(f"{ESKI} git geçmişinde yok (sığ klon: git fetch --unshallow)")
    eski = tmp_path / "sablon"
    eski.mkdir()
    (eski / "kabuk.html").write_text((sayfa.D / "kabuk.html").read_text(encoding="utf-8"), encoding="utf-8")
    (eski / "sahne.js").write_text(sahne, encoding="utf-8")
    monkeypatch.setattr(sayfa, "D", eski)
    d = json.loads(veri_)
    bul = sira.anahtarlar(_denetle(d, tmp_path))
    mahya = sorted(a for a in bul if a.endswith("mahya üstünde"))
    assert len(mahya) == 2 * len(d["kalkan"]) == 6, bul
    assert all(bul[a] > 50 for a in mahya), bul


@HAZIR
def test_duz_mahya_da_alin_sacinin_altinda(tmp_path):
    """Lokman, 10 Kasım 21:01: "mahya ne olursa olsun alın sacının altına girecek". 62 m²'nin verisinde hadveli mahya kapatılınca rehber
    düz mahya yolundan çizer (TK-03'ün metal kiremit mahyası gibi; PR #157): hiçbir mahya ucu alın sacının üstünde değildir."""
    d = json.loads((KOK / ACIK["62 m²"]["girdi"]).read_text(encoding="utf-8"))
    d["kaplama"]["mahya_hadveli"] = False
    bul = sira.anahtarlar(_denetle(d, tmp_path))
    assert not [a for a in bul if a.endswith("mahya üstünde")], bul
