"""İE-16 PR-3a · açık projelerin karkas kuralıyla tanımları.

- Bölmesiz yazılan tanımlar (`kaynak.bolmesiz`; ÇP-06'nın kural sürümü, ÇP-07 = KT-03, ÇP-13 = KT-01) elle düzeltilmez: araç
  (`bolmesiz.py`) kaynağından yeniden koşunca dosyayla bayt bayt aynı çıkar.
- Beş projenin tanımı karkas kuralını ister (ÇP-06'nın PR-2 tanımı istemez, olduğu gibi durur).
- `sonuc.json` elle düzenlenmez: hakem bugünkü listemizle yeniden koşunca tarih ve kıyas commit'i dışında aynı kayıt çıkar (tam koşu:
  `PORTMAN_CELIK_KAYNAK=<klasör>`, dosyalar Drive kimliğiyle adlı; ÇP-06'nınki `test_cp06.py`'de).
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas  # noqa: E402
from testler.celik.projeler import bolmesiz  # noqa: E402

BURADA = Path(__file__).resolve().parent
KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")
TANIMLAR = {"CP03": "CP03.json", "CP06": "CP06_kural.json", "CP07": "CP07.json", "CP13": "CP13.json", "CP14": "CP14.json"}
BOLMESIZ = [BURADA / p / ad for p, ad in TANIMLAR.items() if "bolmesiz" in json.loads((BURADA / p / ad).read_text(encoding="utf-8"))["kaynak"]]
# mühürdeki açık kaynaklar (liste, montaj paftası); Drive kimlikleri
KAYNAKLAR = {
    "CP03": ("17qvD40WCNSHabqbHCNas-WrM5nDnb7aK.xlsx", "1yRGfHY18Kzffkk69e-tQTDtvfFCD29pl.pdf"),
    "CP07": ("1hJ3M-Q3jBx9KybZQmVErnS8rpUW0w43M.xlsx", "1CVJUWmGfMNSEFYYHpzo1l3DGojDaCx3q.pdf"),
    "CP13": ("1Ke9lTQBm1npBncK-AvYHLpIcvNkVvIa4.xlsx", "1toPZLJRp6gP0sjKygqS2W9AG3RyXo6rW.pdf"),
    "CP14": ("1aEw_NPj-rIpIl_v6f0ing0qJUKHn4y3e.xlsx", "1MwW29JQUltT628nNdeZby-V98QbcaYCK.pdf"),
}


def test_bolmesiz_yazimlar_var():
    assert [p.parent.name for p in BOLMESIZ] == ["CP06", "CP07", "CP13"]


@pytest.mark.parametrize("yol", BOLMESIZ, ids=[p.parent.name for p in BOLMESIZ])
def test_bolmesiz_yazim_aractan_yeniden_uretilir(yol):
    t = json.loads(yol.read_text(encoding="utf-8"))
    kaynak_yolu = t["kaynak"]["bolmesiz"].split(" tanımının bölmesiz yazımı", 1)[0]
    assert (KOK / kaynak_yolu).is_file(), kaynak_yolu
    kaynak = json.loads((KOK / kaynak_yolu).read_text(encoding="utf-8"))
    assert "karkas" not in kaynak
    out = bolmesiz.bolmesiz(kaynak, kaynak_yolu, t["kod"], t["ad"], t["kaynak"]["cizim"])
    assert json.dumps(out, ensure_ascii=False, indent=1) + "\n" == yol.read_text(encoding="utf-8")


@pytest.mark.parametrize("proje", sorted(TANIMLAR))
def test_tanim_karkas_kuralini_ister(proje):
    t = json.loads((BURADA / proje / TANIMLAR[proje]).read_text(encoding="utf-8"))
    assert t["karkas"] == "kural" and "celik_modeli" not in t
    b = json.loads((BURADA / proje / "bizim_liste.json").read_text(encoding="utf-8"))
    assert b["tanim"]["yol"] == f"testler/celik/projeler/{proje}/{TANIMLAR[proje]}" and b["karkas_kurali"]


def test_pr2_tanimi_karkassiz_durur():
    t = json.loads((BURADA / "CP06" / "CP06.json").read_text(encoding="utf-8"))
    assert "karkas" not in t and "celik_modeli" not in t        # PR-2: çelik ağırlığı motorun ortalamasından


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
@pytest.mark.parametrize("proje", sorted(KAYNAKLAR))
def test_sonuc_hakemin_ciktisi(proje):
    liste, pafta = KAYNAKLAR[proje]
    k = kiyas.kiyasla(BURADA / proje / "bizim_liste.json", Path(KAYNAK) / liste, Path(KAYNAK) / pafta)
    yeni, kayitli = kiyas.sonuc_kaydi(k), json.loads((BURADA / proje / "sonuc.json").read_text(encoding="utf-8"))
    for d in (yeni, kayitli):
        d.pop("tarih"), d.pop("kiyas_commit")
    assert yeni == kayitli
