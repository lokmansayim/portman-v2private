"""D-73 · Montaj rehberinde kalkan kenarının parçaları birbirine girmez (Lokman, 9 Kasım 2026 15:16: "B yi seçiyorum ama bir şartım var
çakışma olmasın tame değme olsun ama çakışma olmasın").

Hedef örnek 62 m² rehberinde baş makas Z'si, alın sacı ve C kapama başka hiçbir parçanın içine girmez; yüzleri değer. Denetim
`araclar/paket/rehber/cakisma.js`: parçanın içinden 0,1 mm içeride, 2 cm arayla noktalar; nokta başka bir parçanın içindeyse çakışmadır.
Veranda ya da cumba çatısının ana çatının kalkanına değdiği köşe (TK-01, TK-03, TK-04) açık konudur (D-73 › Açık kalan); burada sınanmaz.
Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

JS = KOK / "araclar" / "paket" / "rehber" / "cakisma.js"


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")
def test_62_kalkan_kenari_cakismasiz(tmp_path):
    from araclar.paket.rehber import sayfa
    html = sayfa.yaz(json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8")), tmp_path / "62.html")
    r = subprocess.run(["node", str(JS), str(html.resolve()), str(tmp_path / "c.json")], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    d = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == []
    parcalar = d["parcalar"]
    assert {p["ad"] for p in parcalar} == {"Baş makas Z'si", "Alın sacı", "C kapama"}
    assert len(parcalar) == 24 and sum(p["nokta"] for p in parcalar) > 100_000
    cakisan = [(p["ad"], p["bu"], p["cakisan"], p["yer"]) for p in parcalar if p["cakisan"]]
    assert not cakisan, f"{len(cakisan)} parça başka parçaya giriyor; ilk: {cakisan[:2]}"
