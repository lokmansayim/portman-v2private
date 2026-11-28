"""İkinci döngü (el çizimi; Lokman kart 28 Kasım 2026 05:33:45 UTC "Standart + en çok 3 ücretli tur"): çizilmemiş kapı ve pencere
sorulmaz, kod standartla tamamlar. Girdi: 4×5 krokinin sunucu okuması (tur 4, 28 Kasım)."""
import json
from pathlib import Path

from beyin import gorsel_okuma as g

OKUMA = json.loads((Path(__file__).parent / "veri" / "DONGU2_kroki_4x5_okuma.json").read_text(encoding="utf-8"))


def test_cizilmemis_kapi_pencere_dograma_sorulmaz():
    assert len(OKUMA["emin_olunamayanlar"]) == 4
    den = g.denetle(OKUMA)
    assert not any(k in s.lower() for s in den["sorular"] for k in ("kapı", "pencere", "doğrama"))
    n = " ".join(den["notlar"])
    assert "açık mutfak" in n and "standart kapı" in n and "60x40 vasistas" in n and "sürgülü cam kapı" in n


def test_tamamlanan_plan():
    den = g.denetle(OKUMA)
    assert den["sorular"] == []
    ie = den["cevrim"]["is_emri"]
    assert [m["ad"] for m in ie["mahaller"]] == ["WC", "SALON+MUTFAK"]
    ac = ie["acikliklar"]
    assert {"tur": "ic_kapi", "olcu": 82, "arasi": ["SALON+MUTFAK", "WC"]} in ac
    assert any(a["tur"] == "pencere" and a["olcu"] == "60x40" and a["mahal"] == "WC" for a in ac)
    giris = next(a for a in ac if a.get("acilis") == "surgulu")
    assert giris["olcu"] == "300x200" and [b["tur"] for b in giris["bolmeler"]] == ["sabit", "surgulu"]
    assert not any(a["tur"] == "dis_kapi" for a in ac)


def test_kapili_islak_hacme_dokunulmaz():
    ok = json.loads(json.dumps(OKUMA))
    ok["kapilar"].append({"arasinda": ["SALON", "WC"]})
    _, nt, yap = g.cizilmemisleri_tamamla(ok)
    assert yap["islak_kapi"] == [] and not any("standart kapı" in x for x in nt)


def test_soru_suzgeci_yalniz_tamamlanana():
    yap = {"islak_kapi": ["WC"], "genis_giris": False, "islak_pencere": [], "pencere_istek": False}
    assert g.cizilmemis_sorusu("WC kapısı çizilmemiş: kapı WC'nin hangi duvarında?", yap)
    assert not g.cizilmemis_sorusu("Salon ile mutfak arasında kapı var mı?", yap)
    assert not g.cizilmemis_sorusu("Alt cephedeki doğrama tek parça mı?", yap)


def test_islak_hacim_bir_sonraki_aksa_buyur():
    """Lokman kart 28 Kasım 2026 05:50:20 UTC "Bir sonraki aksa büyüsün (B)": WC derinliği 1 m → 0,63 değil 1,26 m (bir pano)."""
    den = g.denetle(OKUMA)
    wc = next(m for m in den["cevrim"]["is_emri"]["mahaller"] if m["ad"] == "WC")
    assert wc["konum_cm"] == [[318.75, 10.0, 495.0, 135.5]]
    assert any("bir sonraki pano aksına oturdu" in n for n in den["notlar"])
