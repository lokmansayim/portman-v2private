"""İE-44 · toplu çatı seçenekleri aracı (`araclar/cati_secenekleri_toplu.py`): kural onaylı çatıları birebir verir, mühürlü ev ayrılır,
araç kayda yazmaz, kayıt komutu yalnız kararla. Motor'u yalnız plan kurmak için çağırır (çizim yok, hızlı)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from araclar import cati_secenekleri_toplu as T
from motor import geometry as G

KOK = Path(__file__).resolve().parents[1]


def _ie(kod: str) -> dict:
    return json.loads((KOK / "is_emri" / "adaylar" / f"{kod}.json").read_text(encoding="utf-8"))


def test_kural_87m2nin_onayli_cati_secenekleri_ile_ayni():
    """D-83: Lokman'ın 87 m²'de (PA-06) onayladığı kırma ve salon cumbası, kuralın PA-06'ya kurduğu seçeneklerle aynı."""
    ie = _ie("PA06")
    s = {x["harf"]: x for x in T.secenekler(ie, G.kur(json.loads(json.dumps(ie))))}
    assert set(s) == {"K", "C"}                                   # evin çatısı beşik: B kurulmaz
    assert s["K"]["cati"] == _ie("PA06K")["cati"]
    assert s["C"]["cati"] == _ie("PA06C")["cati"]


@pytest.mark.parametrize("kod", ["PA04", "PA11", "PA15", "PA32", "PA37"])
def test_salon_cumbasi_paftadaki_cumbayla_ayni(kod):
    """Salonun ön duvarı kuralı, paftadan okunmuş (ya da onaylı) çıkıntısız cumbaların yerini birebir verir."""
    ie = _ie(kod)
    u = ie["cati"]["cumbalar"][0]
    ara, neden = T._salon_cumbasi(G.kur(json.loads(json.dumps(ie))))
    assert neden == "" and ara == [u["bas_cm"], u["bit_cm"]]


def test_salon_on_cepheye_degmiyorsa_cumba_kurulmaz():
    ara, neden = T._salon_cumbasi(G.kur(_ie("PA14")))
    assert ara is None and "ön cepheye değmiyor" in neden


def test_girintili_ve_veranda_catili_evde_neden_yazilir():
    s = {x["harf"]: x for x in T.secenekler(_ie("PA01"), G.kur(_ie("PA01")))}  # girintili gövde
    assert s["K"]["cati"] is None and "girintili" in s["K"]["neden"]
    s = {x["harf"]: x for x in T.secenekler(_ie("PA02"), G.kur(_ie("PA02")))}  # verandanın tek eğimli çatısı
    assert s["K"]["cati"] is None and "verandanın kendi çatısı" in s["K"]["neden"]


def test_kirma_evde_besik_ve_cumba_seceneği():
    ie = _ie("PA08")
    s = {x["harf"]: x for x in T.secenekler(ie, G.kur(json.loads(json.dumps(ie))))}
    assert set(s) == {"C", "B"}
    assert s["B"]["cati"]["tip"] == "besik" and s["B"]["cati"]["makas_ekseni"] == ie["cati"]["makas_ekseni"]
    for k in T.CATI_ALANLARI:                                      # eğim, saçak, topuk evin çatısından
        assert s["B"]["cati"][k] == ie["cati"][k] == s["C"]["cati"][k]


def test_muhurlu_evler_ve_secenekli_ev():
    ev = {e["gosterim"]: e for e in T.evler()}
    assert {k for k, e in ev.items() if e["muhur"]} == {"PA-01", "PA-02", "PA-03", "PA-05", "PA-07", "PA-22"}
    assert ev["PA-01"]["muhur"] == "M-07" and ev["PA-22"]["muhur"] == "M-12" and ev["PA-07"]["muhur"] == "M-16"
    assert ev["PA-06"]["secenekli"] and not ev["PA-01"]["secenekli"]                       # mühürlü evin seçeneği yok


def test_kayit_komutu_yalniz_kararla_ve_gecen_secenekle():
    sonuc = [{"gosterim": "PA-12", "cati_adi": "Beşik, kalkan yanda", "muhur": None,
              "secenekler": [{"harf": "K", "gosterim": "PA-12-K", "ad": "Kırma", "durum": "gecti", "cati": {"tip": "kirma"}},
                             {"harf": "C", "gosterim": "PA-12-C", "ad": "Beşik + salonda cumba", "durum": "cizilemedi", "cati": None}]},
             {"gosterim": "PA-01", "cati_adi": "Beşik", "muhur": "M-07",
              "secenekler": [{"harf": "B", "gosterim": "PA-01-B", "ad": "Beşik", "durum": "gecti", "cati": {"tip": "besik"}}]}]
    k = T.kaydet_komutlari(sonuc, "D-999")
    assert len(k) == 1 and "--taban PA-12" in k[0] and "--karar D-999" in k[0] and "--varyant K" in k[0] and "--varyant C" not in k[0]
    assert T.kaydet_komutlari(sonuc, "D-999", {"PA-01-B"})[0].count("--taban PA-01") == 1   # mühürlü ev yalnız açık onayla
    assert T.main(["--cikti", "/tmp/yok", "--kaydet-komutlari", "--karar", "yok"]) == 2


def test_neden_yazisi_sade():
    assert "3D modelde kırma çatı beşik" in T.neden_yazisi({"durum": "denetimden_gecmedi", "neden": "HD-10 3D'deki ana çatı …"})
    assert "HD-" not in T.neden_yazisi({"durum": "denetimden_gecmedi", "neden": "HD-08 …; HD-03 …"})


def test_kayitli_secenek_yeniden_kurulmaz(monkeypatch, tmp_path):
    """D-115'ten sonra (bakımlar birleşince yeniden koşu): kayıtlı harf yeniden kurulmaz, evin öteki seçeneği kurulur; kayıt komutu
    kayıtlı evde `--ekle` yazar. Çizim ve denetim burada sahte (yalnız seçenek süzgeci denenir)."""
    ev = {e["gosterim"]: e for e in T.evler()}
    assert ev["PA-06"]["kayitli"] == ["C", "K"] and "C" in ev["PA-08"]["kayitli"] and ev["PA-01"]["kayitli"] == []
    monkeypatch.setattr(T, "ciz", lambda ie, png: {"gecti": True, "brut_cm2": 1, "pano": 1, "uyarilar": []})
    monkeypatch.setattr(T, "denetle", lambda ie: {"dur": []})
    s = T.ev_isle({**ev["PA-08"], "kayitli": ["C"]}, tmp_path)                              # D-115'teki hâli: yalnız C kayıtlı
    assert [x["harf"] for x in s["secenekler"]] == ["B"] and s["kayitli"] == ["C"]          # evin çatısı kırma, C kayıtlı
    k = T.kaydet_komutlari([{**s, "cati_adi": "Kırma"}], "D-999")
    assert len(k) == 1 and "--varyant B" in k[0] and k[0].endswith("--ekle")


def _cv_argv(*ek):
    return ["cati_varyanti_kaydet.py", "--taban", "PA-06", "--karar", "D-83", "--cati-adi", "Beşik",
            "--varyant", "K", "Kırma", json.dumps(_ie("PA06K")["cati"]), *ek]


def test_kayitli_secenek_dusurulmez(monkeypatch, capsys):
    """`cati_varyanti_kaydet.py` kayıtlı seçeneği düşürecek yeniden yazımı durdurur; `--ekle` kayıtlı harfi yeniden yazmaz. Dosya değişmez."""
    import sys
    from araclar import cati_varyanti_kaydet as CV, havuz_denetimi as HD
    monkeypatch.setattr(HD, "denetle_prefabrik", lambda ie, kart=None: {"bulgular": []})
    yol = KOK / "beyin/veri/cati_varyantlari/PA06.json"
    once = yol.read_bytes()
    monkeypatch.setattr(sys, "argv", _cv_argv())
    assert CV.main() == 2 and "PA06C" in capsys.readouterr().out                           # yalnız K ile yazılsa C düşerdi
    monkeypatch.setattr(sys, "argv", _cv_argv("--ekle"))
    assert CV.main() == 2 and "zaten kayıtlı: PA06K" in capsys.readouterr().out
    assert yol.read_bytes() == once


def test_ekle_eski_secenekleri_aynen_tutar(monkeypatch, tmp_path, capsys):
    """`--ekle`: yeni seçenek dosyanın sonuna; eski seçenekler, evin adı ve ilk karar aynen; yeni karar `ek_kararlar`'da; evin görseli
    yeniden yazılmaz. Geçici klasörde (Motor sahte)."""
    import sys
    from araclar import cati_varyanti_kaydet as CV, havuz_denetimi as HD
    (tmp_path / "KARARLAR").mkdir()
    (tmp_path / "KARARLAR" / "D-999.md").write_text("PA-08-B", encoding="utf-8")
    vd, ad = tmp_path / "beyin/veri/cati_varyantlari", tmp_path / "is_emri/adaylar"
    vd.mkdir(parents=True); ad.mkdir(parents=True)
    e = json.loads((KOK / "beyin/veri/cati_varyantlari/PA08.json").read_text(encoding="utf-8"))   # D-115'teki hâli: yalnız PA08C
    e = {**{k: v for k, v in e.items() if k != "ek_kararlar"}, "varyantlar": [v for v in e["varyantlar"] if v["kod"] == "PA08C"]}
    eski = json.dumps(e, ensure_ascii=False, indent=1) + "\n"
    (vd / "PA08.json").write_text(eski, encoding="utf-8")
    monkeypatch.setattr(CV, "KOK", tmp_path); monkeypatch.setattr(CV, "VARYANT_DIR", vd); monkeypatch.setattr(CV, "ADAY_DIR", ad)
    monkeypatch.setattr(CV, "ciz", lambda ie, png: {"brut_cm2": 1, "pano": 1, "uyarilar": []})
    monkeypatch.setattr(HD, "denetle_prefabrik", lambda ie, kart=None: {"bulgular": []})
    besik = {**_ie("PA08")["cati"], "tip": "besik"}
    monkeypatch.setattr(sys, "argv", ["cati_varyanti_kaydet.py", "--taban", "PA-08", "--karar", "D-999", "--cati-adi", "başka ad",
                                      "--varyant", "B", "Beşik", json.dumps(besik), "--ekle"])
    assert CV.main() == 0, capsys.readouterr().out
    yeni, e = json.loads((vd / "PA08.json").read_text(encoding="utf-8")), json.loads(eski)
    assert [v["kod"] for v in yeni["varyantlar"]] == ["PA08C", "PA08B"] and yeni["varyantlar"][0] == e["varyantlar"][0]
    assert (yeni["cati_adi"], yeni["karar"], yeni["ek_kararlar"]) == (e["cati_adi"], "D-115", ["D-999"])
    assert yeni["varyantlar"][1]["kaynak"]["karar"] == "D-999" and not (ad / "PA08_cati.png").exists()
