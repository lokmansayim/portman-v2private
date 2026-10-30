"""İE-09 · Model bankası (D-20): `modeller/banka/` altındaki her model kendi kontrol dosyasına karşı denetlenir; referans zincirine girmez.

- Kartlar geçerli şemada ve bilinen durumda; `kabul` kartların hepsi yükleyiciden (`beyin/banka.py`) geçer (tanım özeti, kontrol dosyası,
  aday kartı görseli, kod çakışması yok).
- Hızlı denetim (her koşuda, model başına ≈ 1 sn): tanımın özeti ve kural seti pimi aynı; yapı, çatı, metraj ve yükleme listesi kanonik
  özeti kontrol dosyasıyla aynı.
- Tam denetim (çizim setinin içerik izleri, model başına ≈ 10 sn): `PORTMAN_BANKA_TAM=1` ile ya da `python3 araclar/atolye.py kontrol --tam`.
- Referans girdi kalıpları (`testler/referans/dogrula.py › GIRDI_KALIPLARI`) bankanın dosyalarını kapsamaz: yeni model referansı değiştirmez.

Kontrol dosyası yalnız motor ya da kural değişince, ayrı PR'da, gerekçe ve kararla yeniden dondurulur (`atolye.py dondur`; D-02, D-20)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar import atolye as A  # noqa: E402
from beyin import banka as B  # noqa: E402

KARTLAR = [k for k in B.kartlar() if not k.get("_hata")]
KABUL = [k for k in KARTLAR if k.get("durum") == "kabul"]


def test_kartlar_gecerli_ve_yukleyiciden_gecer():
    assert [k["_klasor"].name for k in B.kartlar() if k.get("_hata")] == []
    for k in KARTLAR:
        assert k["sema"] == B.KART_SEMASI and k["durum"] in A.DURUMLAR, k["_klasor"].name
        assert k["_klasor"].name == B.dosya_adi(k["kod"]) and (k["_klasor"] / "tanim.json").is_file()
        assert all(d["tur"] in A.DUZELTME_TURLERI for d in k.get("duzeltmeler") or [])
        assert (k.get("metraj_testi") or {}).get("durum") in ("yok", "gecti", "beklemede", "hesaplanmadi")
        if k["durum"] == "kabul":
            assert k["metraj_testi"]["durum"] in ("yok", "gecti"), "metraj kapısını geçmeyen model kabul edilmez"
            # gerçek bankada kapısı geçmemiş (harness + pytest atlanmış ya da yarıda kalmış) ya da izsiz (çizim izleri donmamış) kabul
            # olmaz; "kosuyor" yalnız o modelin kendi kabul kapısının içinde (atolye.KAPI_ORTAMI) geçerli
            kapi = "gecti" if os.environ.get(A.KAPI_ORTAMI) == k["kod"] and k["kabul"].get("kapi") == "kosuyor" else k["kabul"].get("kapi")
            assert kapi == "gecti" and not k["kabul"].get("izsiz"), k["kod"]
            assert "tam" in json.loads((k["_klasor"] / "kontrol.json").read_text(encoding="utf-8")), k["kod"]
    assert B.denetle() == []
    assert sorted(a["kod"] for a in B.kayitlar()) == sorted(k["kod"] for k in KABUL)


def test_referans_kaliplari_bankaya_inmez():
    sys.path.insert(0, str(KOK / "testler" / "referans"))
    import dogrula
    girdiler = {p.resolve() for kalip in dogrula.GIRDI_KALIPLARI for p in KOK.glob(kalip)}
    assert not [p for p in girdiler if (KOK / "modeller" / "banka") in p.parents]


@pytest.mark.parametrize("kart", KABUL, ids=[k["kod"] for k in KABUL])
def test_kabul_model_kontrol_dosyasiyla_ayni(kart):
    k = json.loads((kart["_klasor"] / "kontrol.json").read_text(encoding="utf-8"))
    assert k["sema"] == B.KONTROL_SEMASI and k["kod"] == kart["kod"]
    tam = os.environ.get("PORTMAN_BANKA_TAM") == "1"
    assert A._kontrol_farki(kart, k, kart["_klasor"] / "tanim.json", tam=tam) == []
