"""İE-43 PR-4b · disk arşivi Parti 1'in kartları (`testler/havuz/hdd_kartlari.json`) ve paftadan okunan İş Emri'leri: her ev havuz
hakeminden geçer; kart mühürdeki DWG'ye bağlı; kartta ve İş Emri'nde ad yok (yalnız HD kodu)."""
from __future__ import annotations
import csv
import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar import havuz_hakemi as HH  # noqa: E402

KARTLAR = json.loads(HH.HDD_KARTLARI.read_text(encoding="utf-8"))["evler"]
MUHUR = {(r["kod"], int(r["sira"])): r for r in csv.DictReader((KOK / "testler/hdd/muhur.csv").open(encoding="utf-8"), delimiter=";")}


def _ie(kod: str) -> dict:
    return json.loads((KOK / "testler/havuz/is_emirleri" / f"HD{kod[3:]}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("kod", sorted(KARTLAR))
def test_hakemden_gecer(kod):
    assert HH.denetle(_ie(kod), HH.kartlar()[kod])[0] == []


@pytest.mark.parametrize("kod", sorted(KARTLAR))
def test_kart_muhurdeki_dwg(kod):
    k = KARTLAR[kod]
    ad, sira = k["kaynak"]["dosya"].split(";")
    r = MUHUR[(ad, int(sira))]
    assert ad == kod and r["uzanti"] == "dwg" and r["sha256"] == k["kart_sha256"]


@pytest.mark.parametrize("kod", sorted(KARTLAR))
def test_ad_yok(kod):
    ie = _ie(kod)
    assert ie["talep"]["musteri_adi"] == kod and ie["talep"]["bayi"]["kod"] == kod     # kimlik yalnız HD kodu
    metin = json.dumps([ie, KARTLAR[kod]], ensure_ascii=False)
    assert not re.search(r"PREFABR[İI]K\s+[A-ZÇĞİÖŞÜ]{3,}", metin)                   # pafta başlığındaki "… PREFABRİK <ad>" yazısı yok


# Çerçeveli şablonda dış kapının "Çelik" yazısı olmayan pafta (İE-43 PR-8): okuyucu dış ve iç kapıyı ayırmaz, toplam yazar; kartın
# `varsayim`'ında yazılı.
YAZISIZ_CERCEVELI = {"HD-380"}


def test_kapi_ayrimi_yalniz_yazisi_olan_sablonda():
    """Bantlı şablonda (2019–2020) dış kapının "Çelik" yazısı yok: dış ve iç kapı ayrılmaz, toplam yazılır (PR-4). Çerçeveli
    şablonda yazı yoksa da ayrılmaz (`YAZISIZ_CERCEVELI`, PR-8)."""
    for kod, k in KARTLAR.items():
        ayrik = k["dis_kapi_adedi"] is not None
        assert ayrik == (k["kaynak"]["sablon"] == "cerceveli" and kod not in YAZISIZ_CERCEVELI), kod
        assert k["kapi_adedi"] is not None
    for kod in YAZISIZ_CERCEVELI:
        assert KARTLAR[kod]["kaynak"]["sablon"] == "cerceveli"
        assert any("Çelik" in v and "yazısı yok" in v for v in KARTLAR[kod]["varsayim"]), kod
