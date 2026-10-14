"""İE-14 r3 · P1: ortak plan sözleşmesi (`portman.plan/0.1`), motor adaptörleri ve çok durumlu doğrulama raporu (LLM'siz).

İki motor birleşmez: prefabrik İş Emri'nden okuma prototipi P6001 ve iki altın İş Emri'ni sözleşmeye çevirir (motor/ ve İş Emri dosyaları
değişmez); çelikte sözleşme ↔ Yapı Tanımı iki yönlü. Doğrulama raporu kalemleri ayrı durumlarla yazar.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_adaptor as A, plan_dogrulama as D  # noqa: E402
from beyin.plan_denetim import denetle as plan_denetle  # noqa: E402
from beyin.plan_sema import PlanSozlesmesi, cekirdek  # noqa: E402

PREFABRIK = {"P6001_2plus1_6x6": (753.0, 753.0), "ALTIN_2plus1_6x8": (753.0, 1004.0), "YAN_VERANDALI_2plus1_6x8p5": (753.0, 1066.75)}


def _json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# ── prefabrik okuma prototipi ─────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ad", sorted(PREFABRIK))
def test_prefabrik_is_emri_sozlesmeye_cevrilir_ve_denetimden_gecer(ad):
    yol = KOK / "is_emri" / f"{ad}.json"
    once = hashlib.sha256(yol.read_bytes()).hexdigest()
    s = A.prefabrik_oku(_json(yol))
    assert s["aile"] == "tek_kat_prefabrik" and s["olcu_kaynagi"] == "pano_aksi" and s["izgara_cm"] == 125.5
    assert (s["dis_olcu"]["en"], s["dis_olcu"]["boy"]) == PREFABRIK[ad]
    d = A.denetle(s, "2+1")
    assert d["gecerli"], d["kalemler"]
    assert hashlib.sha256(yol.read_bytes()).hexdigest() == once            # dondurulmuş girdi değişmez


def test_prefabrik_acik_sinir_erisime_sayilir():
    s = A.prefabrik_oku(_json(KOK / "is_emri" / "ALTIN_2plus1_6x8.json"))
    assert s["acik_sinirlar"] == [["SALON", "MUTFAK"]]
    s2 = dict(s, acik_sinirlar=[])
    assert any("MUTFAK" in x for x in A.denetle(s2, "2+1")["kalemler"]["erisim"])


def test_prefabrik_yazma_yonu_yok():
    s = A.prefabrik_oku(_json(KOK / "is_emri" / "P6001_2plus1_6x6.json"))
    with pytest.raises(ValueError):
        A.celik_yaz(s)


# ── çelik iki yönlü ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_celik_okuma_yazma_c8201():
    s = A.celik_oku(_json(KOK / "modeller" / "C8201.json"))
    assert s["aile"] == "tek_kat_celik" and s["kaynak"]["kod"] == "Ç8201" and A.denetle(s, "2+1")["gecerli"]
    t = A.celik_yaz(s, kod="SOZ-C8201")
    assert {m["ad"] for m in t["mahaller"]} == {m["ad"] for m in s["mahaller"]}
    assert plan_denetle(cekirdek(s), {"oda_programi": "2+1"})["gecerli"]


def test_kt02_ham_cevirisi_dikdortgen_degil_dosemede_yakalanir():
    s = A.celik_oku(_json(KOK / "modeller" / "KT02.json"))
    assert any("boşluk" in x for x in A.denetle(s)["kalemler"]["doseme"])     # sundurma: dış hat dikdörtgen değil (uyarlamada atılır)


@pytest.mark.parametrize("bozuk", [{"aile": "cift_kat_celik"}, {"kat": 2}, {"birim": "mm"}])
def test_sozlesme_semasi_disindaki_reddedilir(bozuk):
    s = A.celik_oku(_json(KOK / "modeller" / "C8201.json"))
    assert not A.denetle({**s, **bozuk})["gecerli"]
    with pytest.raises(Exception):
        PlanSozlesmesi.model_validate({**s, **bozuk})


# ── doğrulama raporu ──────────────────────────────────────────────────────────────────────────────────────────────────
def _gecerli_plan():
    return _json(KOK / "testler" / "plan" / "ornekler" / "gecerli_3arti1_100.json")


def test_denetci_kalem_kalem_doner():
    p = _gecerli_plan()
    d = plan_denetle(p, {"oda_programi": "3+1", "alan_m2": 100})
    assert d["gecerli"] and not any(d["kalemler"].values()) and {"cati_tam", "olcu_program_tam"} <= set(d["kosan"])
    d = plan_denetle(p, {"oda_programi": "2+1", "alan_m2": 100})
    assert d["kalemler"]["olcu_program"] and not d["kalemler"]["geometri"]


def test_rapor_gecerli_plan_cizimsiz():
    p = _gecerli_plan()
    r = D.rapor(plan_denetle(p, {"oda_programi": "3+1", "alan_m2": 100}))
    k = r["kalemler"]
    assert [k[a]["durum"] for a in ("sozlesme", "geometri", "olcu_program", "cati")] == [D.GECTI] * 4
    assert k["cizim"]["durum"] == D.DOGRULANMADI and k["yukleme_listesi"]["durum"] == D.DOGRULANMADI
    assert k["yapisal"]["durum"] == D.YAPILMADI and k["muhendis_kabulu"]["durum"] == D.YAPILMADI
    assert r["ozet"].startswith("Sözleşme: geçti · Geometri: geçti")


def test_rapor_derleme_dusunce_sonraki_kalemler_dogrulanmadi():
    p = _gecerli_plan()
    p["dis_olcu"] = {"en": 1200, "boy": 800}                                  # mahaller taşar
    r = D.rapor(plan_denetle(p, {"oda_programi": "3+1"}))["kalemler"]
    assert r["geometri"]["durum"] == D.KALDI
    assert r["olcu_program"]["durum"] == D.DOGRULANMADI and r["cati"]["durum"] == D.DOGRULANMADI


def test_rapor_cizim_manifestten(tmp_path):
    d = plan_denetle(_gecerli_plan(), {"oda_programi": "3+1"})
    for ad in ("a.pdf", "a.ifc", "a_plan_bayi.png", "a_yukleme.json"):
        (tmp_path / ad).write_text("x")
    man = {"passed": True, "pdf": "a.pdf", "ifc": "a.ifc", "plan_bayi": "a_plan_bayi.png", "yukleme_json": "a_yukleme.json",
           "duzenlenebilir_dxf": "a.dxf", "warnings": ["perspektif: ATLANDI"]}
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    assert D.rapor(d, cikti=tmp_path)["kalemler"]["cizim"]["durum"] == D.GECTI
    (tmp_path / "manifest.json").write_text(json.dumps({**man, "passed": False}))
    assert D.rapor(d, cikti=tmp_path)["kalemler"]["cizim"]["durum"] == D.KALDI
    (tmp_path / "a.ifc").unlink()
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    assert D.rapor(d, cikti=tmp_path)["kalemler"]["cizim"]["durum"] == D.KALDI


def test_rapor_liste_kiyasi_olcum_tasir_hedefsiz():
    d = plan_denetle(_gecerli_plan(), {"oda_programi": "3+1"})
    k = D.rapor(d, liste_kiyasi={"eslesme": 0.7})["kalemler"]["yukleme_listesi"]
    assert k["durum"] == D.DOGRULANMADI and k["olcum"] == {"eslesme": 0.7}
