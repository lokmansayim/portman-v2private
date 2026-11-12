"""İE-36 (D-80) · Bayiye üç seçenek: sekiz prefabrik ev aday kaydında (PA-01 … PA-08). LLM'siz, Postgres'siz.

Lokman 11 Kasım 2026: 20:42 kart "5 ev ve mühürlü 3 ev", 20:47 önizleme onayı ("Onaylıyorum, PR'a geç"), 20:58 kod serisi
("Yeni seri: PA-01 ... PA-08"). Kıyas: önizlemede onaylanan seçenek sayıları (65, 75, 80, 85 m² 2+1 → 3; 60, 70, 90 → 2) ve bu
kararla yazılan sıra. Kabul kümesi verilmeyen yol (harness) prefabrik adayı görmez: canlıda görünmek K-A10 kaydına bağlıdır.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beyin import secenek as S  # noqa: E402
from beyin.katalog import ADAYLAR_PREFABRIK_JSON, SABLON_DIR, Katalog  # noqa: E402
from test_celik_revizyon_karar import Sohbet  # noqa: E402

KODLAR = {f"PA0{i}" for i in range(1, 9)}
KAYIT = json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8"))

# D-80: kod → (kaynak İş Emri, oda programı, brüt m²; D-49 tek kaynak `prefabrik_liste.bina_brut_cm2`, tam sayıya yuvarlı)
EVLER = {
    "PA01": ("testler/cizim/evler/AP15.json", "2+1", 60.0),
    "PA02": ("testler/cizim/evler/AP03.json", "2+1", 64.0),
    "PA03": ("testler/cizim/evler/AP09.json", "2+1", 70.0),
    "PA04": ("testler/motor/veri/TK04_r08.json", "2+1", 78.0),
    "PA05": ("testler/cizim/evler/AP22.json", "2+1", 82.0),
    "PA06": ("testler/motor/veri/TK06_r02.json", "2+1", 87.0),
    "PA07": ("testler/motor/veri/TK01_r08.json", "3+1", 90.0),
    "PA08": ("testler/cizim/evler/AP01.json", "3+1", 140.0),
}

# m² → seçenek setindeki sıra (fark etmez önceliğiyle); önizlemedeki sayılar aynı
SIRA_2P1 = {
    60: ["PA01", "PA02"],
    65: ["PA02", "PA01", "PA03"],
    70: ["PA03", "PA02"],
    75: ["PA04", "PA03", "PA05"],
    80: ["PA04", "PA05", "PA06"],
    85: ["PA06", "PA05", "PA04"],
    90: ["PA06", "PA05"],
}


def _set(tmp_path: Path, m2: float, oda: str = "2+1", kabul=frozenset(KODLAR)):
    s = Sohbet(tmp_path, kabul=set(kabul) if kabul is not None else None)
    k = s.yaz(f"{m2:g} m2 {oda} prefabrik ev", alan_m2=m2, oda_programi=oda, yapi_turu="prefabrik")
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    return s, k


def test_kayit_bicimi():
    assert [a["kod"] for a in KAYIT] == sorted(KODLAR)
    for a in KAYIT:
        kaynak, oda, m2 = EVLER[a["kod"]]
        assert a["gosterim"] == a["kod"][:2] + "-" + a["kod"][2:] == a["referans_model"]
        assert (a["durum"], a["yapi_turu"], a["kat"], a["oda_programi"], a["katalog_m2"]) == ("gecerli", "prefabrik", 1, oda, m2)
        assert a["kaynak"]["dosya"] == kaynak and a["kaynak"]["karar"] == "D-80"
        assert abs(a["ozet"]["brut_m2"] - m2) < 1 and a["kapali_m2"] == round(a["ozet"]["brut_m2"] - a["veranda_m2"], 1)
        sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
        assert sab["is_emri_no"] == f"PM-ADAY-{a['kod']}" and sab["revizyon"] == 1
        assert sab["talep"]["bayi"] == {"kod": "ADAY", "ad": "Aday kaydı"} and sab["yapi"]["referans_model"] == a["gosterim"]
        assert (SABLON_DIR / a["gorsel"]).stat().st_size > 10_000


def test_sablon_kaynak_is_emriyle_ayni():
    """Şablon kaynak İş Emri'nin kendisidir: yalnız kimlik, talep ve referans kodu değişir (D-28: elle düzeltme yok)."""
    for a in KAYIT:
        kaynak = json.loads((KOK / EVLER[a["kod"]][0]).read_text(encoding="utf-8"))
        sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
        for d in (kaynak, sab):
            for anahtar in ("is_emri_no", "revizyon", "talep"):
                d.pop(anahtar, None)
            d["yapi"].pop("referans_model", None)
        assert sab == kaynak, a["kod"]


def test_brut_alan_tek_kaynaktan():
    """Aday m²'si ön onay antedindeki brüt alanla aynı sayı (D-49, K-A1; `prefabrik_liste.bina_brut_cm2`); Motor değişip brüt kayarsa düşer."""
    from motor import geometry as G, prefabrik_liste as PL
    for a in KAYIT:
        sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
        plan = G.kur(sab)
        brut = PL.bina_brut_cm2(plan) / 1e4
        assert round(brut, 2) == a["ozet"]["brut_m2"] and float(round(brut)) == a["katalog_m2"], (a["kod"], brut)
        # veranda = Motor'un açık mahalleri (antetteki net alanın dışı; geometri hakemi: adla ikinci sınıflama yok)
        assert a["veranda_m2"] == round(sum(m.alan_m2 for m in plan.mahaller.values() if m.acik), 2), a["kod"]


def test_tk06_r02_proje_dosyasindaki_onayli_plan():
    ie = json.loads((KOK / "testler/motor/veri/TK06_r02.json").read_text(encoding="utf-8"))
    assert (ie["is_emri_no"], ie["revizyon"]) == ("PM-TK06-87M2", 2)
    assert ie["talep"]["bayi"] == {"kod": "TK06", "ad": "Bayi TK-06"}


def test_kabulsuz_yolda_prefabrik_aday_gorunmez():
    """Harness `Katalog()`'u kabul kümesiz kurar: prefabrik aday görünmez, 22 vaka değişmez (vaka 2 '60 metrekare 2+1' soru kalır)."""
    for kat in (Katalog(), Katalog(test_adaylari=True), Katalog(kabul_edilmis={"Ç8801"})):
        assert not {a["kod"] for a in kat.gorunur_adaylar()} & KODLAR
        assert kat.aday("PA-04") is None
    assert {a["kod"] for a in Katalog().gorunur_adaylar()} >= {"Ç8801", "KT01"}          # çelik adaylar aynen (İE-08)
    tum = Katalog(kabul_edilmis=set(KODLAR))
    assert {a["kod"] for a in tum.gorunur_adaylar()} == KODLAR
    assert Katalog(kabul_edilmis={"PA04"}).aday("pa-04")["kod"] == "PA04"


@pytest.mark.parametrize("girdi", ["PA-04", "pa04", "PA 04", "Pa-04"])
def test_kod_normalize(girdi):
    assert Katalog.kod_normalize(girdi) == "PA04"


@pytest.mark.parametrize("m2", sorted(SIRA_2P1))
def test_uc_secenek_2p1(tmp_path, m2):
    s, k = _set(tmp_path, m2)
    st = s.k.d.get("secenek_seti") or {}
    assert k.eylem == "secenek", k.mesaj
    assert [a["kod"] for a in st["adaylar"]] == SIRA_2P1[m2]
    beklenen = SIRA_2P1[m2]
    assert [b["baslik"] for b in k.butonlar] == [f"{i}. PA-{c[2:]}" for i, c in enumerate(beklenen, 1)]
    ilk = "PA-" + beklenen[0][2:]
    assert f'örn. "{ilk} olsun"' in k.mesaj and "P9401" not in k.mesaj
    assert ("Kurallardan geçen 3 seçenek var." in k.mesaj) == (len(beklenen) == 3)


def test_3p1(tmp_path):
    s, k = _set(tmp_path, 90, "3+1")
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA07"]
    s, k = _set(tmp_path / "b", 140, "3+1")
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA08"]


def test_kabulsuz_set_acilmaz(tmp_path):
    s, k = _set(tmp_path, 80, kabul=None)
    assert k.eylem != "secenek" and not s.k.d.get("secenek_seti"), k.mesaj


def test_dugmeyle_secim_is_emri(tmp_path):
    s, _ = _set(tmp_path, 80)
    k = s.dugme("s:{set}:PA05")
    assert k.eylem == "is_emri", k.mesaj
    ie = k.is_emri
    assert ie["talep"]["kaynak"] == "PA05" and ie["yapi"]["referans_model"] == "PA-05" and ie["revizyon"] == 1
    sab = json.loads((SABLON_DIR / "adaylar/PA05.json").read_text(encoding="utf-8"))
    assert ie["mahaller"] == sab["mahaller"] and ie["acikliklar"] == sab["acikliklar"]
    assert (s.k.d["secenek_seti"]["durum"], s.k.d["secenek_seti"]["secilen_kod"]) == ("secildi", "PA05")


def test_yaziyla_kod_secim(tmp_path):
    """LLM 'PA-06' kodunu okursa (katalog_kodu) seçim yapılır; kod tire, boşluk ve küçük harfle de tanınır."""
    s, _ = _set(tmp_path, 80)
    k = s.yaz("PA-06 olsun", katalog_kodu="pa 06")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj


@pytest.mark.parametrize("tur", ["ayna_x", "ayna_y"])
def test_ayna_istegi_yonlendirilir(tmp_path, tur):
    """Geometri hakemi (İE-36): PA şablonları cm konumlu; pano birimli ayna uygulanmaz. İstek hata değil yönlendirme olur (K21)."""
    s, _ = _set(tmp_path, 80)
    k = s.yaz("PA-06 olsun, simetriği olsun", katalog_kodu="PA-06",
              varyantlar=[{"tur": tur, "aciklama": "simetriği olsun", "parametreler": {}}])
    assert k.eylem == "yonlendir" and "simetri otomatik uygulanamıyor" in k.mesaj, k.mesaj


def test_aday_kaydet_karar_ister(tmp_path):
    arac = [sys.executable, str(KOK / "araclar/aday_kaydet.py"), str(KOK / EVLER["PA04"][0]), "--kod", "PA-99", "--durum", "gecerli",
            "--test-dosyasi"]
    for ek in ([], ["--karar", "D-999"], ["--karar", "yok"], ["--karar", "D-02"], ["--karar", "D-80"]):   # D-80 PA-99'u yazmaz
        r = subprocess.run(arac + ek, capture_output=True, text=True, cwd=tmp_path)
        assert r.returncode == 2 and "yalnız Lokman'ın kararıyla" in r.stdout, r.stdout + r.stderr
    assert not (KOK / "is_emri/adaylar/PA99.json").exists()
