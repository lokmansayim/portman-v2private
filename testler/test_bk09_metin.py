"""BK-09 PR-1 · 14 Ekim canlı denemesinin üç metin kusuru (LLM'siz, Postgres'siz).

M1: kod bir değişiklik uyguladıysa bayi mesajına ve PDF açıklamasına (`talep.metin`) LLM özeti yazılmaz; "Uygulanan: …" yazılır.
M2: çelik seçenek listesinde örnek bir çelik kodudur; prefabrikte "P9401" aynen.
M3: sıfır kesinti ("alan farkı %0 → −0") yazılmaz; puan hesabı aynı.
"""
from __future__ import annotations
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beyin import secenek as S  # noqa: E402
from test_celik_revizyon_karar import Sohbet, r01_k, var  # noqa: E402

SORU_OZETI = "Bayi çatının L olmasını istiyor; L çatıyla ne kastettiğinizi teyit etmemiz gerekiyor"


def test_m1_uygulanan_degisiklikte_llm_ozeti_yazilmaz(tmp_path):
    s = Sohbet(tmp_path)
    r01_k(s)
    k = s.yaz("çatı L olsun", ozet=SORU_OZETI, varyantlar=[var("cati_degistir", "çatı L")])
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801L", k
    assert "teyit" not in k.mesaj and "Uygulanan: çatı" in k.mesaj, k.mesaj
    assert k.is_emri["talep"]["metin"].startswith("Uygulanan: çatı") and "teyit" not in k.is_emri["talep"]["metin"]
    assert k.mesaj.endswith("Ön onay planınız hazır; plan görseli ve PDF ektedir.")


def test_m1_degisiklik_yoksa_ozet_durur(tmp_path):
    s = Sohbet(tmp_path)
    k = s.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik", ozet="Bayi Ç8801K modelini istiyor")
    assert k.eylem == "is_emri" and "Bayi Ç8801K modelini istiyor." in k.mesaj and "Uygulanan" not in k.mesaj
    assert k.is_emri["talep"]["metin"] == "Bayi Ç8801K modelini istiyor"


def _aday(kod, m2, yapi="celik", **ek):
    return {"kod": kod, "gosterim": kod, "katalog_m2": m2, "yapi_turu": yapi, **ek}


def test_m3_sifir_kesinti_yazilmaz_puan_ayni():
    [a, b] = S.puanla([_aday("Ç8801", 88.0), _aday("KT-03", 80.0)], {"alan_m2": 88})
    assert (a["kod"], a["puan"], a["hesap"]) == ("Ç8801", 100, "kesinti yok")
    assert (b["kod"], b["puan"], b["hesap"]) == ("KT-03", 82, "alan farkı %9 → −18")


def test_m2_celik_setinde_ornek_celik_kodu():
    sira = S.puanla([_aday("Ç8801", 88.0), _aday("Ç8801K", 88.0), _aday("Ç8801L", 88.0)], {"alan_m2": 88, "oda_programi": "2+1"})
    m = S.mesaj_metni(sira, {"alan_m2": 88, "oda_programi": "2+1"})
    assert 'örn. "Ç8801 olsun"' in m and "P9401" not in m and "%0" not in m, m


def test_m2_prefabrik_ornek_aynen():
    sira = S.puanla([_aday("P8801", 88, "prefabrik"), _aday("P9401", 94, "prefabrik"), _aday("P7201", 72, "prefabrik")],
                    {"alan_m2": 88, "oda_programi": "2+1"})
    assert 'örn. "P9401 olsun"' in S.mesaj_metni(sira, {"alan_m2": 88, "oda_programi": "2+1"})


def test_m3_kucuk_fark_yuvarlanip_sifir_yazilmaz():
    """İnceleme bulgusu: fark %0,34 iken kesinti 1 puan; "%0 → −1" değil "%0,3 → −1"."""
    [a] = S.puanla([_aday("Ç8801", 88.3)], {"alan_m2": 88})
    assert a["hesap"] == "alan farkı %0,3 → −1", a["hesap"]


def test_m1_cati_bayinin_gordugu_gosterimle(tmp_path):
    """İnceleme bulgusu: "Uygulanan" metni artık tek açıklama; çatı iç koduyla (Ç8801L) değil gösterimle (Ç8801-L) yazılır."""
    s = Sohbet(tmp_path)
    r01_k(s)
    k = s.yaz("çatı L olsun", varyantlar=[var("cati_degistir", "çatı L")])
    assert "Uygulanan: çatı Ç8801-L" in k.mesaj and "Ç8801L" not in k.mesaj, k.mesaj
