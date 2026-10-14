"""İE-14: gerçek LLM cevaplarının kayıtları (`testler/plan/kayitlar/<etiket>.json`, `araclar/plan_dene.py` yazar) LLM'siz oynatılır.
Kaydedilen sonuç (geçerli/geçersiz, deneme sayısı) bugünkü denetçiyle aynı çıkmalı: denetçi ya da derleyici değişirse fark burada görünür
(gevşetme değil; bir kaydın sonucu değişiyorsa gerekçesi iş emrine yazılır). Kayıt yoksa atlanır."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_uretici as PU  # noqa: E402

KAYITLAR = sorted(p for p in (KOK / "testler" / "plan" / "kayitlar").glob("*.json") if p.name != "cagri_defteri.json") \
    if (KOK / "testler" / "plan" / "kayitlar").exists() else []


@pytest.mark.skipif(not KAYITLAR, reason="henüz LLM kaydı yok (araclar/plan_dene.py --ucretli)")
@pytest.mark.parametrize("yol", KAYITLAR, ids=[p.stem for p in KAYITLAR])
def test_kayit_ayni_sonucu_verir(yol):
    k = json.loads(yol.read_text(encoding="utf-8"))
    if not k["denemeler"]:
        pytest.skip(f"kayıtta deneme yok ({k.get('hata')})")
    s = PU.uret(k["talep"], hazir=[d["plan"] for d in k["denemeler"]])
    assert [d["gecerli"] for d in s["denemeler"]] == [d["gecerli"] for d in k["denemeler"]]
    assert [d["ihlaller"] for d in s["denemeler"]] == [d["ihlaller"] for d in k["denemeler"]]
