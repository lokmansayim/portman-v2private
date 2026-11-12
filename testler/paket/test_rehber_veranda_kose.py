"""D-73 › Açık kalan, ilk adım · Arka veranda köşesinde alın sacı verandanın trapez sacının üstünde (TK-01; 10 Kasım 2026).

Lokman, 10 Kasım 2026 20:47: "alın sacları Trapez sacının altında kalıyor bahsettiğim hata bu modelde"; kural 20:16: "önce trapez sac
ve mahya gelir sonra alın sacı üzerini örter". Önce/sonra eskizine (`Bayiye_Rehber/D74_alin_veranda_kose/`) 21:17 kartı "Doğru, böyle yap".

TK-01'in arka verandasının sol yüzü ana çatının sol yüzünün devamıdır; sağ yüzü ana kalkanın saçağının altından gövdeye gider. Ana
arka kalkanın alın sacının alt kolu (tırnak ve saçak altı) bu yüzün sacının altında kalıyor, verandanın yavru makasına giriyordu.
Düzeltme `araclar/paket/rehber/sahne.js` › `rake(..., komsu)`: dereyle bitmeyen uçta başka bir çatının yüzü ana saçağın altından
geçiyorsa alın sacı o yüzün hadve tepelerinin düzleminde kesilir, sacın üstüne oturur. 62 m² değişmez (`test_rehber.py`).

Denetim `araclar/paket/rehber/cakisma.js` (D-73). Alın sacı hiçbir parçaya girmez. Aynı köşede baş makas Z'si verandanın yavru
makasına giriyor: açık, ayrı adım (eskizle sorulacak). Açık yerin listesi cırcırdır: yeni çakışan parça kırmızı, düzelen listeden çıkar.
Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
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
from araclar.paket.rehber import iz  # noqa: E402

JS = KOK / "araclar" / "paket" / "rehber" / "cakisma.js"
IE = KOK / "testler" / "motor" / "veri" / "TK01_r08.json"
# açık: baş makas Z'si arka veranda köşesinde verandanın yavru makasına giriyor (D-73 › Açık kalan; ayrı adım)
ACIK = {("Baş makas Z'si", "arka kalkan (MKS08) · ön/sol yüz · 1/2. parça · L 280 cm")}


@pytest.fixture(scope="module")
def cakisma(tmp_path_factory):
    if iz.hazir() is not None:
        pytest.skip(f"rehber denetimi: {iz.hazir()}")
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import sayfa, veri
    ie = json.loads(IE.read_text(encoding="utf-8"))
    gec = tmp_path_factory.mktemp("tk01_kose")
    try:
        kart_model.uret(copy.deepcopy(ie), gec / "kart", "TK01")
        L = PL.is_emrinden(copy.deepcopy(ie), ozellikler={"Tavan": "Asma"})["satirlar"]
        d = veri.kur(copy.deepcopy(ie), gec / "kart", "TK01", L, "TK-01")
    finally:
        G.lento_ayarla({})                               # lento modül durumudur (BK-23): öteki testlere sızmaz
    html = sayfa.yaz(d, gec / "TK-01.html")
    r = subprocess.run(["node", str(JS), str(html.resolve()), str(gec / "c.json")], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads((gec / "c.json").read_text(encoding="utf-8"))


def test_alin_saci_hicbir_parcaya_girmez(cakisma):
    """Önce: arka kalkanın alın sacı (L 333 cm) verandanın sacına (12 nokta) ve yavru makasına (46 nokta) giriyordu."""
    assert cakisma["hatalar"] == []
    alin = [p for p in cakisma["parcalar"] if p["ad"] == "Alın sacı"]
    assert len(alin) == 16
    cakisan = [(p["bu"], p["cakisan"], p["yer"]) for p in alin if p["cakisan"]]
    assert not cakisan, f"{len(cakisan)} alın sacı başka parçaya giriyor; ilk: {cakisan[:2]}"


def test_acik_yer_listesi(cakisma):
    """Kalkan kenarında çakışan parçalar yalnız bilinen açık yer (cırcır)."""
    cakisan = {(p["ad"], p["bu"]) for p in cakisma["parcalar"] if p["cakisan"]}
    assert cakisan - ACIK == set(), f"yeni çakışan parça: {sorted(cakisan - ACIK)}"
    assert ACIK - cakisan == set(), f"düzelen açık yer listeden çıkarılır: {sorted(ACIK - cakisan)}"
