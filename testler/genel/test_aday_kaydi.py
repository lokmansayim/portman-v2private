"""İE-08 Adım 8 · `beyin/veri/adaylar.json`: yedi çelik aday (D-08 madde 4, D-10) — alanlar, tanım sha'sı, kart görseli, kod biçimi
(`Katalog.kod_normalize` ile aynı), alanlar K-A1 (brüt oturum = listedeki bina_m2), varyantlar yalnız katalog modelinde, KT'ler adsız."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin.katalog import Katalog  # noqa: E402

ADAYLAR = json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8"))
KAYIT = {a["kod"]: a for a in ADAYLAR}


def test_yedi_aday_alanlari():
    assert sorted(KAYIT) == ["KT01", "KT02", "KT03", "Ç8201", "Ç8801", "Ç8801K", "Ç8801L"]
    for kod, a in KAYIT.items():
        assert a["durum"] == "gecerli" and a["motor"] == "genel" and a["yapi_turu"] == "celik" and a["kat"] == 1 and a["oda_programi"] == "2+1"
        tanim = KOK / a["tanim"]
        assert tanim.exists() and a["tanim"].startswith("modeller/") and hashlib.sha256(tanim.read_bytes()).hexdigest() == a["tanim_sha256"]
        assert Katalog.kod_normalize(json.loads(tanim.read_text(encoding="utf-8"))["kod"]) == kod == Katalog.kod_normalize(a["gosterim"])
        gorsel = KOK / "is_emri" / a["gorsel"]
        assert gorsel.exists() and 0 < gorsel.stat().st_size <= 5 * 1024 * 1024 and a["gorsel"] == f"adaylar/{kod.replace('Ç', 'C')}.png"   # dosya adı ASCII
        # katalog_m2 listedeki bina_m2 (tam sayıya yuvarlı brüt oturum); kapalı = yuvarlanmamış oturum − net veranda (K16; geometri hakemi 12.10)
        assert a["katalog_m2"] > 0 and abs(a["ozet"]["oturum_m2"] - a["kapali_m2"] - a["veranda_m2"]) < 0.02
        assert abs(a["katalog_m2"] - a["ozet"]["oturum_m2"]) <= 0.5 and a["katalog_m2"] == round(a["ozet"]["oturum_m2"])
        assert a["ozet"]["kural_seti"] == "kurallar.json" and a["ozet"]["liste_satir"] > 50
        assert a["kaynak"]["dogrulama"].startswith("çizim seti")


def test_varyantlar_ve_adsiz_kt():
    assert KAYIT["Ç8801"]["varyantlar"] == ["Ç8801K", "Ç8801L"] and KAYIT["Ç8801"]["referans_model"] == "Ç8801"
    for kod in ("Ç8801K", "Ç8801L"):
        assert KAYIT[kod]["varyantlar"] == [] and KAYIT[kod]["referans_model"] == "Ç8801" and KAYIT[kod]["gosterim"] == f"Ç8801-{kod[-1]}"
    for kod in ("KT01", "KT02", "KT03"):
        assert KAYIT[kod]["musteri_projesi"] is True and KAYIT[kod]["sunum"]["ad"] == "" and KAYIT[kod]["gosterim"] == f"KT-0{kod[-1]}"
    assert KAYIT["Ç8801"]["musteri_projesi"] is False and KAYIT["Ç8801"]["sunum"]["ad"]
    # alanlar (brüt oturum, listedeki bina_m2): Ç8801 ailesi 88, Ç8201 82, KT'ler 99/92/94 (D-08 K-A1; geometri hakemi 12.10)
    assert {k: round(v["katalog_m2"]) for k, v in KAYIT.items()} == {"Ç8801": 88, "Ç8801K": 88, "Ç8801L": 88, "Ç8201": 82, "KT01": 99, "KT02": 92, "KT03": 94}


def test_katalogda_gorunurluk_kabul_kumesine_bagli():
    hepsi = Katalog()                                      # harness ve yerel koşum: kabul kümesi yok → gecerli adaylar görünür
    assert {a["kod"] for a in hepsi.gorunur_adaylar() if a.get("motor") == "genel"} == set(KAYIT)
    hic = Katalog(kabul_edilmis=set())                     # kalıcı akış: kabul kaydı yoksa hiçbiri sunulmaz (K-A10)
    assert [a for a in hic.gorunur_adaylar() if a.get("motor") == "genel"] == [] and hic.aday("Ç8801") is None
    uc = Katalog(kabul_edilmis={"Ç8801", "Ç8801K", "Ç8801L"})
    assert {a["kod"] for a in uc.gorunur_adaylar()} == {"Ç8801", "Ç8801K", "Ç8801L"} and uc.aday("c8801-k")["kod"] == "Ç8801K"


def test_kod_bicimi_celik_varyant_prefabrik_degismez():
    # çelik varyant harfi ve KT kodu normalize olur; prefabrik kodda harf eki yoktur, bugünkü davranış aynen (geometri hakemi 12.10)
    assert Katalog.kod_normalize("Ç8801-K") == "Ç8801K" == Katalog.kod_normalize("c8801 k") and Katalog.kod_normalize("KT-01") == "KT01"
    assert Katalog.kod_normalize("6001") == "P6001" and Katalog.kod_normalize("P6001-A") == "P6001-A"
    assert Katalog.taban_kod("Ç8801L") == "Ç8801" and Katalog.taban_kod("P6001") == "P6001" and Katalog.taban_kod("KT01") == "KT01"
    assert Katalog.taban_kod("P6001") != Katalog.taban_kod("P7401")
