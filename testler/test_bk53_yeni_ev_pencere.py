"""BK-53 · yeni bayi talebinde pencere ortalama kuralı kendiliğinden açık (D-121 V5).

Lokman, kart 17 Kasım 2026 04:52:24 UTC, "Yeni bayi talebinde pencere ortalama kuralı kendiliğinden açılsın mı?" → "Evet, ayrı işte
açılsın" ("Yeni talepten çizilen her prefabrik evde pencere odaya ortalanır."). Kapsam kartı 16 Kasım 21:38:12 "Yalnız yeni çizilen
evlere" ("Havuzdaki ve onaylı evler bugünkü gibi kalır."; D-103).

Beyin'de prefabrik İş Emri'nin üç kaynağı var (`karar._is_emri_uret`): seçilen havuz/katalog evinin şablonu, onaylı ızgara şablonu
(`karar.GRID_SABLON`) ve bayinin çiziminden okunan ev (`gorsel_okuma.is_emri_prefabrik`, İE-20). Yeni çizilen ev yalnız üçüncüsüdür:
anahtar orada yazılır, öteki ikisinde yazılmaz. LLM yok, Postgres yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import gorsel_okuma as GO, karar as K  # noqa: E402
from motor import geometry as G  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402

GORSEL = KOK / "testler" / "gorsel" / "veri"
ANAHTAR = "dik_duvar_pencere"


def _okuma(ad: str) -> dict:
    return {a: v for a, v in json.loads((GORSEL / ad).read_text(encoding="utf-8")).items() if not a.startswith("_")}


def _cizimden(ad: str) -> dict:
    d = GO.denetle(_okuma(ad), bk14=True)
    assert d["sorular"] == [] and d["cizilemez"] == [], (d["sorular"], d["cizilemez"])
    return d["cevrim"]["is_emri"]


def _dizilim(plan) -> dict:
    return {f"{d.tur} {d.yon} {d.c:g}": [[round(q.a0, 3), round(q.boy, 3), q.acilim.tur if q.acilim else ""] for q in d.panolar]
            for d in plan.duvarlar}


@pytest.mark.parametrize("ad", ["TK01_okuma.json", "BASIT_2p1_okuma.json"])
def test_cizimden_okunan_evde_anahtar_yazilir(ad):
    ie = _cizimden(ad)
    assert ie["yapi"]["dizilim"][ANAHTAR] == "tam_orta" == GO.DIK_DUVAR_PENCERE
    G.kur(ie)                                                         # Motor anahtarı tanır, plan kurulur


def test_cizimden_okunan_90m2_banyo_vasistasi_yerinde():
    """90 m² hedef evin (TK-01) bayi çizimi. Makasa dik duvardaki tek ortalanacak pencere banyonun vasistasıydı (125,5 + 62,75 →
    31,375 + 125,5 + 31,375). Lokman, 17 Kasım 2026 08:35:02 (D-124): "banyo ebeveyn banyo wc tuvalet yani vasistas pencresi ne varsa onlar
    kendi konumlarında kalacak ortalamıyacaksın". Anahtarlı plan anahtarsızla pano pano aynı; uyarı eklenmez. Kuru odanın ortalanması
    D-121 testlerinde (`testler/motor/test_d121_dik_duvar_pencere.py`)."""
    ie = _cizimden("TK01_okuma.json")
    eski = copy.deepcopy(ie)
    del eski["yapi"]["dizilim"][ANAHTAR]
    p1, p0 = G.kur(ie), G.kur(eski)
    assert p1.dik_duvar_pencere == [] and _dizilim(p1) == _dizilim(p0)
    assert [u for u in p1.uyarilar if u not in p0.uyarilar] == []


def test_havuz_evi_anahtarsiz_r01_ve_revizyon(tmp_path):
    """Havuzdan seçilen ev (PA-04) yeni çizilen ev değildir: r01'de ve bayinin pencere revizyonunda (r02) anahtar yok (D-103)."""
    s = Sohbet(tmp_path, kabul=KABUL)
    k = _plan(s, "PA04")
    assert ANAHTAR not in (k.is_emri["yapi"].get("dizilim") or {})
    k = s.yaz("Yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("YATAK ODASI 1", "120x180")])
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2, k.mesaj
    assert ANAHTAR not in (s.plan["yapi"].get("dizilim") or {})


def test_sablonlarda_anahtar_yok():
    """Havuz, katalog ve onaylı ızgara şablonları anahtarsız (kart 21:38:12): Beyin bu kaynaklara anahtar eklemez."""
    # Katalog evlerinin yeni revizyonları (ör. `is_emri/P8501_r0*.json`) anahtarı kendi sohbetlerinde, Lokman'ın onayıyla taşır; Beyin
    # onları olduğu gibi okur. Burada denetlenen havuz ve aday şablonları ile onaylı ızgara şablonlarıdır.
    yollar = [KOK / "is_emri" / f for f in K.GRID_SABLON.values()]
    yollar += sorted((KOK / "is_emri" / "adaylar").rglob("*.json")) + sorted((KOK / "beyin" / "veri").rglob("*.json"))
    assert len(yollar) > 50
    bulunan = [str(y.relative_to(KOK)) for y in yollar if f'"{ANAHTAR}"' in y.read_text(encoding="utf-8")]
    assert bulunan == []
    assert ANAHTAR not in (KOK / "beyin" / "karar.py").read_text(encoding="utf-8")
