"""İE-20 PR-6 (D-88) · prefabrik talep formunun karar katmanındaki izi (`karar._form_izi`): formdan gelen ölçüde hazır planlar m²'ye göre,
öncelik formdan (plan başka mesajda çıksa da sorulmaz), sohbette yazılan ölçü bugünkü yoldan, formdaki seçimler yalnız form talebinde
İş Emri'ne işlenir. LLM yok, Postgres yok, çizim yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_celik_revizyon_karar import Sohbet  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
import talep_formu as TF  # noqa: E402

STD = {"kat": "1", "oda": "2+1", "oncelik": "butce", **TF.STANDART}


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


def form(s: Sohbet, **alanlar):
    """Bayi prefabrik formu gönderir: worker'ın yaptığı gibi (`k.prefabrik_formu`, LLM'siz talep)."""
    import json
    oz = TF.cevap_ozeti(json.dumps({"flow_token": "pf:abc123", **STD, **alanlar}, ensure_ascii=False))
    t = TF.talep(oz)
    s.k.prefabrik_formu = {"oncelik": TF.oncelik(oz)}
    k = s.yaz(TF.metin(oz), **{a: b for a, b in t.items() if a not in ("guven",)})
    assert s.k.prefabrik_formu is None            # iz yalnız o mesaj için
    return k


def kodlar(s: Sohbet) -> list[str]:
    return [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]]


def test_formdan_gelen_olcu_m2_ye_gore_set_oncelik_sorulmaz(s):
    k = form(s, alan="70", en="7")                                             # Lokman'ın örneği: 5,5 × 8 pano, 72 m²
    assert k.eylem == "secenek", k.mesaj
    ts = s.k.d["taslak"]
    assert ts["form"] == "prefabrik" and ts["olcu_formdan"] is True and ts["oncelik"] == "butce"
    assert ts["pano"] == {"nx": 5.5, "ny": 8.0} and ts["alan_m2"] == 72.0
    assert "PA03" in kodlar(s) and "Öncelik: bütçe." in k.mesaj               # 70 m² plan 72 m² ± %10 içinde
    k = s.dugme("s:{set}:PA03")
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA03"


def test_sohbette_yazilan_pano_olcusu_bugunku_yoldan(s, tmp_path):
    """Formdan gelmeyen talepte pano ve m² birlikteyse bugünkü gibi pano ızgarasıyla aranır (m² yok sayılır)."""
    k1 = s.yaz("5,5 x 8 pano, 72 m², 2+1", yapi_turu="prefabrik", oda_programi="2+1", pano={"nx": 5.5, "ny": 8}, alan_m2=72)
    s2 = Sohbet(tmp_path / "b", kabul=KABUL)
    k2 = s2.yaz("5,5 x 8 pano, 2+1", yapi_turu="prefabrik", oda_programi="2+1", pano={"nx": 5.5, "ny": 8})
    assert (k1.eylem, k1.gerekce) == (k2.eylem, k2.gerekce) and "olcu_formdan" not in s.k.d["taslak"] and "form" not in s.k.d["taslak"]


def test_oncelik_plan_baska_mesajda_ciksa_da_sorulmaz(s):
    k = form(s)                                                                # ölçü yazılmadı
    assert k.eylem == "sor" and k.gerekce == "eksik: dis_olcu", k.mesaj
    k = s.yaz("70 m² olsun", niyet="yeni_talep", alan_m2=70)
    assert k.eylem == "secenek" and "Öncelik: bütçe." in k.mesaj, k.mesaj       # öncelik formda seçilmişti
    assert "olcu_formdan" not in s.k.d["taslak"] and s.k.d["taslak"]["form"] == "prefabrik"


def test_formdan_sonra_sohbette_olcu_son_soz(s):
    k = form(s, oda="1+1", alan="45", en="5")                                  # hazır plan yok: yönlendirme; konuşma kapanır
    assert k.eylem == "yonlendir", k.mesaj
    form(s, alan="70", en="7")
    ts = s.k.d["taslak"]
    assert ts["olcu_formdan"] is True
    # bayi m²'yi sohbette değiştirir: formun hesapladığı pano düşer, yeni m² ile aranır
    s.k.d["secenek_seti"] = None
    k = s.yaz("90 m² olsun", niyet="yeni_talep", alan_m2=90)
    ts = s.k.d["taslak"]
    assert "olcu_formdan" not in ts and "pano" not in ts and ts["alan_m2"] == 90


def test_formdaki_secim_yalniz_form_talebinde_is_emrine(s, tmp_path):
    # sohbette yazılan talep: LLM formun kelimesini yazsa da İş Emri bugünkü gibi (özellik yalnız kayıtta)
    k = s.yaz("7,73 x 10,14 2+1 yükseklik 280", yapi_turu="prefabrik", oda_programi="2+1", dis_olcu={"en_m": 7.73, "boy_m": 10.14},
              bina_ozellikleri={"Pano Yüksekliği": "280 cm", "İç Duvar": "100 mm"})
    assert k.eylem == "is_emri", k.mesaj
    assert s.plan["yapi"].get("duvar_yuksekligi_cm", 250) == 250 and s.plan["bina_ozellikleri"]["Pano Yüksekliği"] == "280 cm"
    # aynı ölçü formdan: 280 cm ve iç duvar 100 mm plana işlenir, bayiye yazılır
    s2 = Sohbet(tmp_path / "b", kabul=KABUL)
    k = form(s2, en="7,73", boy="10,14", yukseklik="280", ic_duvar="100")
    assert k.eylem == "is_emri", k.mesaj
    assert s2.plan["yapi"]["duvar_yuksekligi_cm"] == 280 and s2.plan["yapi"]["duvar_kalinligi_cm"]["ic"] == 10
    assert "pano yüksekliği 280 cm" in k.mesaj and "iç duvar 100 mm" in k.mesaj
