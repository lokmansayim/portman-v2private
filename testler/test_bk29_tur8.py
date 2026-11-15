"""BK-29 tur 8 · bayiye giden onay reddi cümlesinde İş Emri numarasının ilk harfi küçülüyordu ("pM-…").

`kanal/kalici.py` › `onay_denetimi`: onay, plan bayiye ulaşmadan yazıldıysa cevap "… Planı inceledikten sonra <no> rNN planını
onaylıyorsanız lütfen yeniden "onaylıyorum" yazın." cümlesiyle biter. Kod cümlenin ilk harfini küçültüyordu; cümle numarayla
başladığı için bayiye "pM-B01-…" gidiyordu. Numara bayiye her yerde yazıldığı gibi gider. Postgres yok: depo sahtedir.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
from kanal import kalici  # noqa: E402

NO = "PM-B01-20261115-45151"


class SahteDepo:
    def __init__(self, **iletim):
        self.iletim = {"pdf_wamid": "wamid.PDF", "pdf_durum": "gonderildi", "teslim_durumu": None,
                       "teslim": None, "gonderildi": None, "kabul": 100.0, **iletim}

    def revizyon_iletimi(self, gonderen, no, rev):
        return self.iletim

    def alintinin_revizyonu(self, gonderen, context_id):
        return {"is_emri_no": NO, "rev": 1}


def _denet(depo, ts, rev=2, **gelen):
    d = {"asama": "onay_bekliyor", "son_is_emri": {"is_emri_no": NO, "revizyon": rev}}
    return kalici.onay_denetimi(depo, {"sender": "900000000101", "timestamp": ts, **gelen}, d)


def test_plan_ulasmadan_yazilan_onayda_numara_yazildigi_gibi():
    r = _denet(SahteDepo(), ts=50)
    assert r["kabul"] is False and r["neden"] == "onay, plan ulaşmadan yazılmış"
    assert r["mesaj"] == (f"Onay mesajınız {NO} r02 planı size ulaşmadan yazılmış görünüyor; onayınızı kaydetmedim. "
                          f"Planı inceledikten sonra {NO} r02 planını onaylıyorsanız lütfen yeniden \"onaylıyorum\" yazın.")
    assert "pM-" not in r["mesaj"]


@pytest.mark.parametrize("r", [
    _denet(SahteDepo(), ts=50),                                                   # plan ulaşmadan yazılmış
    _denet(SahteDepo(), ts=200, context_id="wamid.ESKI"),                         # alıntı başka revizyona ait
    _denet(SahteDepo(pdf_durum="belirsiz"), ts=200),                              # PDF gönderimi teyitsiz
])
def test_onay_reddi_cumlelerinde_numara_her_yerde_ayni(r):
    """Üç red cümlesinde de numara büyük "PM-" ile geçer; küçülmüş biçim yok."""
    assert r["kabul"] is False and NO in r["mesaj"] and NO.lower() not in r["mesaj"] and "pM-" not in r["mesaj"]


def test_plan_ulastiktan_sonra_yazilan_onay_bugunku_gibi():
    r = _denet(SahteDepo(), ts=200)
    assert r["kabul"] is True and "mesaj" not in r
