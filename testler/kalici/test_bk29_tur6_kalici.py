"""BK-29 tur 6 · kalıcı akış (gerçek Postgres, sahte WhatsApp, kayıtlı okuma; LLM yok, hızlı Motor).

D3 (pano 206): yazıyla "Nasıl çalışır?" düğmenin cevabını alır; LLM çağrılmaz, konuşma değişmez. Yeni form açıksa (İE-20 PR-6) cevap
[Prefabrik] [Çelik] düğmeli gelir (komut dosyası P16 ile aynı satırlar).
E2 (pano 222; tur 5 canlı madde 10): açık planda "iptal etmeyin" niyeti "diğer" okunsa da "Anladım. Neyi değiştirelim?" gider;
[Talep formu] düğmeli "Anlayamadım" gitmez, plan açık kalır.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_bk29_tur6_kalici.py -q
"""
from __future__ import annotations

from conftest import NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import sablonlar as S
import worker as W
from test_prefabrik_formu_akisi import dugmeli, pf_ayar
from test_talep_formu_akisi import BAYI_KART, ayar, bayiye, form_satiri, isle_hepsi, plan_al, son_sonuc


def _govde(x: dict) -> str:
    s = x["satir"]
    return (s.get("interactive") or {}).get("body", {}).get("text") or s.get("body") or s.get("text") or ""


def _dugmeyle(depo, s) -> list[tuple[str, str]]:
    g = mesaj("Nasıl çalışır?", None, bayi=BAYI_KART, tur="button")
    g["reply_id"] = S.BILGI_NASIL; g["reply_kind"] = "button"
    assert depo.mesaj_kaydet(g)
    isle_hepsi(depo, s)
    return [(x["kind"], _govde(x)) for x in bayiye(depo)]


def test_yaziyla_nasil_calisir_dugmenin_cevabi_llmsiz(depo, wa, tmp_path):
    s = ayar(tmp_path)
    assert depo.mesaj_kaydet(mesaj("Nasıl çalışır?", None, bayi=BAYI_KART))        # kayıtlı LLM çıkarımı yok: LLM çağrılsa hata kaydı düşerdi
    [r] = isle_hepsi(depo, s)
    j = tek(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC LIMIT 1")
    assert j["cikarim"] == {"talep": None, "meta": {"backend": "kural", "kural": "nasil_calisir"}}
    assert j["sonuc"]["gerekce"] == "şablon cevabı: nasıl çalışır", r
    yazili = [(x["kind"], _govde(x)) for x in bayiye(depo)]
    assert [k for k, _ in yazili] == ["document", "interactive"]
    satir, _ = form_satiri(depo, wa)
    assert satir["body"].startswith("Talebinizi bu sohbete yazabilir ya da formu doldurabilirsiniz")
    assert depo.konusma_oku(NUMARA_A)[0] in (None, {}) or not (depo.konusma_oku(NUMARA_A)[0] or {}).get("taslak")   # konuşma değişmedi
    assert _dugmeyle(depo, s) == yazili                                           # düğmeyle aynı satırlar


def test_yaziyla_nasil_calisir_yeni_form_acikken_yapi_dugmeleri(depo, wa, tmp_path):
    """İE-20 PR-6 komut dosyası P16: cevapta [Prefabrik] [Çelik] düğmeleri. Yazıyla da aynı."""
    s = pf_ayar(tmp_path)
    assert depo.mesaj_kaydet(mesaj("nasıl çalışıyor", None, bayi=BAYI_KART))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["gerekce"] == "şablon cevabı: nasıl çalışır"
    assert [x["kind"] for x in bayiye(depo)] == ["document", "interactive"]
    x = dugmeli(depo)
    assert [b["reply"]["title"] for b in x["satir"]["interactive"]["action"]["buttons"]] == ["Prefabrik", "Çelik"]
    assert x["satir"]["body"].endswith(W.YAPI_SORUSU)


def test_baska_soz_tasiyan_nasil_calisir_llm_yolunda(depo, wa, tmp_path):
    """"bu pencere nasıl çalışır" yalnız bu soru değildir: bugünkü yoldan (LLM çıkarımı) gider."""
    s = ayar(tmp_path)
    assert depo.mesaj_kaydet(mesaj("bu pencere nasıl çalışır", talep("soru", "Pencerenin nasıl çalıştığını soruyorsunuz."), bayi=BAYI_KART))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["gerekce"] == "genel soru"
    assert "document" not in [x["kind"] for x in bayiye(depo)]


def test_acik_planda_iptal_etmeyin_kalici(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    no, _ = plan_al(depo, wa, tmp_path, s)
    assert depo.mesaj_kaydet(mesaj("iptal etmeyin", talep("diger", '"iptal etmeyin" yazdınız, ne istediğinizi anlayamadık.'), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor", r
    metin = " ".join(_govde(x) for x in bayiye(depo))
    assert metin.startswith("Anladım. Neyi değiştirelim?") and "Anlayamadım" not in metin
    assert son_sonuc(depo).get("form_sunuldu") != "talep"                          # [Talep formu] düğmeli yeni talep önerisi gitmez
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "revizyon" and d["son_is_emri"]["is_emri_no"] == no
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1]
