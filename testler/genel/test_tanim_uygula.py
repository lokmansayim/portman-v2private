"""İE-08 8a PR-2b (A4) · `beyin/varyant.tanim_uygula`: Yapı Tanımı 0.5'e deterministik değişiklikler (pencere ölçüsü, çatı varyantı,
dış karkas 140). Ç8201 sağlaması kapıdır (Lokman, 13 Ekim 2026: tutmazsa dış 140 ertelenir): `docs/sartname/modeller/C8201.md` › "Seçenek: dış
duvar karkası 140 mm" tablosu — kapalı net 58,37 → 56,54 m² (odalar 11,92/11,92/4,30/6,75/23,48 → 11,51/11,51/4,19/6,66/22,67), dış ölçü
1094 × 750 ve brüt oturum 82,05 değişmez, dış duvar 16,5 cm (karkas 14), iç duvar aksları aynı. Kural seti 0.19 pimiyle; altın izlere dokunmaz
(değişmiş tanımlar yalnız geçici klasörde çizilir)."""
from __future__ import annotations
import copy
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import varyant as V  # noqa: E402
from motor.genel import cati_genel, girdi_genel, kural, yapi  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
MODEL = KOK / "modeller"


@pytest.fixture(scope="module", autouse=True)
def kural_seti():
    eski = os.environ.get("PORTMAN_KURALLAR")
    os.environ["PORTMAN_KURALLAR"] = str(SET)
    try:
        yield
    finally:
        if eski is None:
            os.environ.pop("PORTMAN_KURALLAR", None)
        else:
            os.environ["PORTMAN_KURALLAR"] = eski


def tanim(kod: str) -> dict:
    return json.loads((MODEL / f"{kod}.json").read_text(encoding="utf-8"))


def metraj(t: dict) -> dict:
    kur = kural.oku()
    y = yapi.kur(t); c = cati_genel.cati_kur(t["cati"], kur); m = girdi_genel.metraj(y, c, kur)
    g = girdi_genel.girdi(y, c, m, kur, "x.json")
    odalar = {ad: round(b["alan_m2"], 2) for ad, b in y["bolgeler"].items() if b["sinif"] == "ic"}
    return {"odalar": odalar, "kapali_net": round(sum(odalar.values()), 2), "oturum_m2": round(m["oturum_m2"], 2), "dis_olcu_m": g["dis_olcu_m"],
            "bina_m2": g["bina_m2"], "karkas_mm": g["dis"]["karkas_mm"], "kalinlik": {d["ad"]: round(d["kalinlik"], 2) for d in y["duvarlar"]},
            "ic_akslar": {d["ad"]: ((d["kutu"][0] + d["kutu"][2]) / 2 if d["yon"] == "y" else (d["kutu"][1] + d["kutu"][3]) / 2)
                          for d in y["duvarlar"] if d["sinif"] == "ic"}}


# ───────────────────────── dış karkas 140 ─────────────────────────
def test_c8201_dis_140_saglamasi():
    """Kapı: şartname tablosuyla ±0,05 m²."""
    t = tanim("C8201"); t0 = copy.deepcopy(t)
    t2 = V.tanim_uygula(t, {"op": "dis_karkas_140"})
    assert t == t0, "girdi değişmemeli"
    a, b = metraj(t), metraj(t2)
    assert a["kapali_net"] == pytest.approx(58.37, abs=0.05) and b["kapali_net"] == pytest.approx(56.54, abs=0.05)
    for ad, deger in {"Yatak Odası 1": 11.51, "Yatak Odası 2": 11.51, "Banyo": 4.19, "Hol": 6.66, "Yaşam Alanı": 22.67}.items():
        assert b["odalar"][ad] == pytest.approx(deger, abs=0.05), ad
    assert a["dis_olcu_m"] == b["dis_olcu_m"] == [10.94, 7.5] and a["oturum_m2"] == b["oturum_m2"] == pytest.approx(82.05, abs=0.01)
    assert a["bina_m2"] == b["bina_m2"] and a["karkas_mm"] == 80 and b["karkas_mm"] == 140
    assert all(b["kalinlik"][ad] == 14 for ad in ("DA", "DU", "DL", "DR")) and all(b["kalinlik"][ad] == 8 for ad in ("A", "P", "Bb", "R", "B"))
    assert a["ic_akslar"] == b["ic_akslar"], "iç duvar aksları değişmez"
    kutu = {d["ad"]: d["kutu"] for d in t2["duvarlar"]}
    assert kutu["DA"] == [1.25, 1.25, 848.75, 15.25] and kutu["DU"] == [1.25, 734.75, 848.75, 748.75]
    assert kutu["DL"] == [1.25, 15.25, 15.25, 734.75] and kutu["DR"] == [834.75, 15.25, 848.75, 734.75]       # uçlar dayandığı yüzle kaydı
    assert kutu["A"][1] == 15.25 and kutu["A"][3] == 734.75 and kutu["P"][0] == 15.25                       # iç duvarlar yeni yüze kısaldı
    assert kutu["K1"] == [1086, 0, 1094, 30]                                                                 # veranda dikmeleri, kirişler aynı
    assert t2["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2" and "DIS-140" in t2["duvar_siniflari"]["dis"]["ad"]
    assert t2["duvar_siniflari"]["ic"] == t["duvar_siniflari"]["ic"] and t2["cati"] == t["cati"] and t2["acikliklar"] == t["acikliklar"]


def test_c8801_dis_140_l_kosede_dis_duvar_ucu_uzar():
    t = tanim("C8801")
    t2 = V.tanim_uygula(t, {"op": "dis_karkas_140"})
    b = metraj(t2)
    assert b["karkas_mm"] == 140 and all(b["kalinlik"][ad] == 14 for ad in ("DK", "DB", "DG", "DKB", "DKG", "DD"))
    assert b["dis_olcu_m"] == metraj(t)["dis_olcu_m"] and b["oturum_m2"] == metraj(t)["oturum_m2"]
    kutu = {d["ad"]: d["kutu"] for d in t2["duvarlar"]}
    assert kutu["DKB"] == [625.25, 15.25, 639.25, 235.25], "L köşe: DKB'nin ucu DG'nin yeni iç yüzüne uzar (köşe açık kalmaz)"
    assert kutu["DG"] == [1.25, 221.25, 625.25, 235.25] and kutu["DB"] == [1.25, 235.25, 15.25, 844.75]
    assert V.tanim_uygula(t, {"op": "dis_karkas_140"}) == t2                                                # deterministik


@pytest.mark.parametrize("kod, neden", [("KT01", "celik_modeli"), ("KT02", "celik_modeli"), ("KT03", "zaten 140")])
def test_dis_140_karkas_modeli_ve_zaten_140_hata(kod, neden):
    with pytest.raises(V.VaryantHatasi, match=neden):
        V.tanim_uygula(tanim(kod), {"op": "dis_karkas_140"})
    with pytest.raises(V.VaryantHatasi, match="zaten 140"):
        V.tanim_uygula(V.tanim_uygula(tanim("C8201"), {"op": "dis_karkas_140"}), {"op": "dis_karkas_140"})       # iki kez uygulanmaz


# ───────────────────────── pencere ölçüsü ─────────────────────────
@pytest.mark.parametrize("aciklik, en, yuk, bas, alt", [("P5", 120, 120, 436, 80), ("P7", 60, 60, 343, 140), ("P2", 120, 180, 501, 20), ("P1", 160, 180, 104, 20)])
def test_pencere_olcu_merkez_korunur_alt_lentodan(aciklik, en, yuk, bas, alt):
    # Ç8801'de bütün pencerelerin üstü 200 (270 − lento 70): "üst kot korunur" kuralı (geometri hakemi 13.10) burada aynı alt kotu verir
    t = tanim("C8801"); t0 = copy.deepcopy(t)
    t2 = V.tanim_uygula(t, {"op": "pencere_olcu", "aciklik": aciklik, "en": en, "yuk": yuk})
    assert t == t0
    a = next(x for x in t2["acikliklar"] if x["ad"] == aciklik)
    assert (a["bas"], a["en"], a["yuk"], a["alt"], a["etiket"]) == (bas, en, yuk, alt, f"{en}/{yuk}")
    assert [x for x in t2["acikliklar"] if x["ad"] != aciklik] == [x for x in t["acikliklar"] if x["ad"] != aciklik]
    assert t2["duvarlar"] == t["duvarlar"] and t2["mahaller"] == t["mahaller"]


@pytest.mark.parametrize("aciklik, en, yuk, neden", [("P6", 400, 120, "taşıyor|sığmıyor"), ("P1", 120, 220, "sığmıyor"), ("X9", 120, 120, "pencere yok"),
                                                     ("P2", 300, 180, "çakışıyor"), ("K1", 120, 120, "pencere yok"), ("P1", 20, 120, "aralık dışı"),
                                                     ("P1", "yüz", 120, "okunamadı")])
def test_pencere_olcu_hatalari(aciklik, en, yuk, neden):
    with pytest.raises(V.VaryantHatasi, match=neden):
        V.tanim_uygula(tanim("C8801"), {"op": "pencere_olcu", "aciklik": aciklik, "en": en, "yuk": yuk})


def test_pencere_odanin_duvarina_sigmali():
    # Ç8201 P4 banyo vasistası (60/40, DU 363–423, merkez 393); banyonun DU yüzü ≈ 352,75–533,25 (A ve R duvarları arası):
    # 120 cm en (333–453) A duvarını keser → hata (duvar boyuna sığsa da); 80 cm (353–433) sığar
    with pytest.raises(V.VaryantHatasi, match="sığmıyor"):
        V.tanim_uygula(tanim("C8201"), {"op": "pencere_olcu", "aciklik": "P4", "en": 120, "yuk": 100})
    t2 = V.tanim_uygula(tanim("C8201"), {"op": "pencere_olcu", "aciklik": "P4", "en": 80, "yuk": 100})
    a = next(x for x in t2["acikliklar"] if x["ad"] == "P4")
    assert (a["bas"], a["alt"], a["etiket"]) == (353, 100, "80/100")


# ───────────────────────── çatı varyantı, sıra ve bilinmeyen işlem ─────────────────────────
def test_cati_varyanti_tanimla_teyit():
    t = tanim("C8801L")
    assert V.tanim_uygula(t, {"op": "cati_varyanti", "kod": "Ç8801L"}) == t
    assert V.tanim_uygula(t, {"op": "cati_varyanti", "kod": "c8801-l"}) == t
    with pytest.raises(V.VaryantHatasi, match="uygulanamaz"):
        V.tanim_uygula(t, {"op": "cati_varyanti", "kod": "Ç8801K"})
    with pytest.raises(V.VaryantHatasi, match="bilinmeyen"):
        V.tanim_uygula(t, {"op": "ayna_x"})


def test_degisiklikler_sirayla_birikir():
    t = tanim("C8801K")
    liste = [{"op": "pencere_olcu", "aciklik": "P5", "en": 120, "yuk": 120}, {"op": "dis_karkas_140"}, {"op": "cati_varyanti", "kod": "Ç8801K"}]
    t2 = t
    for d in liste:
        t2 = V.tanim_uygula(t2, d)
    a = next(x for x in t2["acikliklar"] if x["ad"] == "P5")
    assert a["etiket"] == "120/120" and metraj(t2)["karkas_mm"] == 140 and V._kod_norm(t2["kod"]) == "Ç8801K"
    t3 = t
    for d in reversed(liste):
        t3 = V.tanim_uygula(t3, d)
    assert t3 == t2, "sıra sonucu değiştirmez"


# ───────────────────────── değişmiş tanım genel motordan geçer ─────────────────────────
@pytest.mark.parametrize("kod, liste", [("C8201", [{"op": "dis_karkas_140"}]),
                                        ("C8801", [{"op": "pencere_olcu", "aciklik": "P5", "en": 120, "yuk": 120}, {"op": "dis_karkas_140"}])])
def test_degismis_tanim_uret_gecer(tmp_path, kod, liste):
    from motor.genel import uret as U
    t = tanim(kod)
    for d in liste:
        t = V.tanim_uygula(t, d)
    yol = tmp_path / "tanim.json"
    yol.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    m = U.uret(yol, tmp_path / "cikti", is_emri_no="PM-TEST-20261013-2", revizyon=2, set_yolu=SET, perspektif=False, bayi=True)
    v = json.loads((tmp_path / "cikti" / "validation.json").read_text(encoding="utf-8"))
    assert m.get("pdf") and v["passed"] is True and v["errors"] == [], v
    assert (tmp_path / "cikti" / m["pdf"]).is_file() and (tmp_path / "cikti" / m["bayi_gorsel"]).is_file()
    oz = json.loads((tmp_path / "cikti" / m["pafta_ozet"]).read_text(encoding="utf-8")) if m.get("pafta_ozet") else {}
    if oz:
        assert "140" in oz["ozellikler"]["Dış Duvarlar"]                                  # paftada "140x45x1,2 çelik profil"


# ── Geometri hakemi (13.10) bulguları: sıra bağımsızlığı, üst kot, iki yanlı açıklık denetimi, ikinci derece birleşim ──────────────────
@pytest.mark.parametrize("kod", ["C8201", "C8801", "C8801K", "C8801L", "KT01", "KT02", "KT03"])
def test_ozgun_modeller_acik_denetiminden_gecer_pencere_ayni_olcuyle_degismez(kod):
    """Yeni iki yanlı denetim yedi modelin bütün açıklıklarını kabul eder; pencereyi kendi ölçüsüyle yeniden uygulamak hiçbir şeyi
    değiştirmez (bas, alt, en, yük aynı)."""
    t = tanim(kod)
    V.aciklik_denetimi(t, yapi.kur(t))
    for a in [x for x in t["acikliklar"] if x["tur"] == "pencere"]:
        t2 = V.tanim_uygula(t, {"op": "pencere_olcu", "aciklik": a["ad"], "en": a["en"], "yuk": a["yuk"]})
        b = next(x for x in t2["acikliklar"] if x["ad"] == a["ad"])
        assert (b["bas"], b["alt"], b["en"], b["yuk"]) == (a["bas"], a.get("alt", 0), a["en"], a["yuk"]), a["ad"]


def test_genis_pencere_ve_dis_140_sira_bagimsiz():
    """Önce genişleyen pencere sonra dış 140, köşe karkasına giriyor ve geçiyordu; ters sırada reddediliyordu. İkisi de reddedilir."""
    t = tanim("C8201")
    t1 = V.tanim_uygula(t, {"op": "pencere_olcu", "aciklik": "P1", "en": 330, "yuk": 180})
    with pytest.raises(V.VaryantHatasi):
        V.tanim_uygula(t1, {"op": "dis_karkas_140"})
    with pytest.raises(V.VaryantHatasi):
        V.tanim_uygula(V.tanim_uygula(t, {"op": "dis_karkas_140"}), {"op": "pencere_olcu", "aciklik": "P1", "en": 330, "yuk": 180})
    c = tanim("C8801")
    for p, en in (("P1", 340), ("P9", 375)):
        with pytest.raises(V.VaryantHatasi):
            V.tanim_uygula(V.tanim_uygula(c, {"op": "pencere_olcu", "aciklik": p, "en": en, "yuk": 180}), {"op": "dis_karkas_140"})


def test_pencere_ust_kotu_korunur_kt():
    """Üst kot korunur: KT-02 P6 (300/200, alt 20) yalnız en değişince denizlik 20'de kalır; KT-03 P4/P5 kendi 220'siyle kabul edilir
    (önce "kat − lento − yük" denizliği 0'a indiriyor ve 220'yi reddediyordu)."""
    k2 = V.tanim_uygula(tanim("KT02"), {"op": "pencere_olcu", "aciklik": "P6", "en": 250, "yuk": 200})
    assert next(a for a in k2["acikliklar"] if a["ad"] == "P6")["alt"] == 20
    for p in ("P4", "P5"):
        k3 = V.tanim_uygula(tanim("KT03"), {"op": "pencere_olcu", "aciklik": p, "en": 200, "yuk": 220})
        assert next(a for a in k3["acikliklar"] if a["ad"] == p)["alt"] == 0


def test_pencere_dis_yanda_dayanan_duvari_kesmez():
    """KT-01 P1 346 cm: oda yanında sığsa da dışarıdan dayanan MD1'e biner (önce yalnız oda yanı denetleniyordu)."""
    with pytest.raises(V.VaryantHatasi):
        V.tanim_uygula(tanim("KT01"), {"op": "pencere_olcu", "aciklik": "P1", "en": 346, "yuk": 120})


@pytest.mark.parametrize("kod", ["C8201", "C8801", "C8801K", "C8801L"])
def test_dis_140_sonrasi_duvarlar_ortusmez(kod):
    """İkinci derece birleşim: Ç8801'de uzayan DKB'nin üstüne oturan I6 kısalır (önce 8 × 6 cm üst üste biniyordu: IFC'de iki duvar)."""
    t2 = V.tanim_uygula(tanim(kod), {"op": "dis_karkas_140"})
    d = t2["duvarlar"]
    for i in range(len(d)):
        for j in range(i + 1, len(d)):
            a, b = d[i]["kutu"], d[j]["kutu"]
            assert not (min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and min(a[3], b[3]) - max(a[1], b[1]) > 0.01), (d[i]["ad"], d[j]["ad"])
    if kod.startswith("C8801"):
        assert next(w for w in t2["duvarlar"] if w["ad"] == "I6")["kutu"] == [627.5, 235.25, 635.5, 331.5]
