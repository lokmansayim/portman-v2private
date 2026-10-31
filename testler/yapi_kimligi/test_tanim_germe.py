"""İE-23 PR-2a · banka modelinde oda büyütme / küçültme (`beyin/tanim_germe.py`) ve okuma (`beyin/degisiklik_okuyucu.py`, germeli).

Hedef örnekler (`hedef/germe_*.json`, aday; Lokman'ın onayı İE-23 › PR-2a): KT-01 "yatak odası 1'i arkaya 50 cm" (dış kenar, düzey 1:
ev arkaya uzar) ve Ç8201 "yatak odası 2'yi öne 30 cm" (iç duvar kayar, yatak odası 1 küçülür, yolundaki kapı duvarla kayar). Kıyas:
girdi, rapor, gerilmiş tanımın kanonik sha'sı ve değişen duvar, açıklık, mahal özetleri. Yeniden yazma yalnız onayla:
`python testler/yapi_kimligi/test_tanim_germe.py --hedef-yaz`. Olumsuz örnekler gerekçesiyle (oda kuralı, kapı sığmıyor, ana çatı = düzey 3,
ikincil çatı = düzey 2 bu PR'da yok, veranda, kiriş). Germe belirlenimcidir ve `varyant.tanim_uygula` aynı tanımı verir."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import degisiklik_okuyucu as DO  # noqa: E402
from beyin import tanim_germe as TG  # noqa: E402
from beyin import varyant  # noqa: E402
from beyin.celik import tanim_sha_icerik  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
HEDEF = Path(__file__).resolve().parent / "hedef"
HEDEFLER = {
    "germe_KT01_yatak_odasi_1_K50": ("modeller/KT01.json", "Yatak Odası 1", "K", 50, True),
    "germe_C8201_yatak_odasi_2_G30": ("modeller/C8201.json", "Yatak Odası 2", "G", 30, True),
}


def _tanim(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


_ONBELLEK: dict[tuple, tuple] = {}


def _uygula(yol: str, mahal: str, yon: str, cm: int, buyut: bool) -> tuple[dict, dict, dict]:
    a = (yol, mahal, yon, cm, buyut)
    if a not in _ONBELLEK:
        t = _tanim(yol)
        _ONBELLEK[a] = (t, *TG.oda_degistir(t, mahal, yon, cm, buyut, set_yolu=SET))
    return copy.deepcopy(_ONBELLEK[a])


def ozet(ad: str) -> dict:
    """Hedef örneğin kıyaslanan özeti: girdi, rapor, gerilmiş tanımın sha'sı, değişen duvar kutuları, açıklık yerleri, mahal noktaları."""
    yol, mahal, yon, cm, buyut = HEDEFLER[ad]
    t, t2, r = _uygula(yol, mahal, yon, cm, buyut)
    once = {d["ad"]: d["kutu"] for d in t["duvarlar"]}
    ac0 = {a["ad"]: a["bas"] for a in t["acikliklar"]}
    m0 = {m["ad"]: m.get("nokta") for m in t["mahaller"]}
    return {"sema": "portman.yapi_germe_hedef/0.1",
            "girdi": {"tanim": yol, "tanim_sha256": tanim_sha_icerik(t), "op": "oda_buyut" if buyut else "oda_kucult", "mahal": mahal,
                      "yon": yon, "cm": cm, "kural_seti": SET.name},
            "rapor": r, "anlatim": TG.kisa_anlatim(r) + "; " + TG.anlatim(r),
            "sonuc": {"tanim_sha256": tanim_sha_icerik(t2),
                      "duvarlar": {d["ad"]: [once[d["ad"]], d["kutu"]] for d in t2["duvarlar"] if d["kutu"] != once[d["ad"]]},
                      "acikliklar": {a["ad"]: [ac0[a["ad"]], a["bas"]] for a in t2["acikliklar"] if a["bas"] != ac0[a["ad"]]},
                      "mahal_noktalari": {m["ad"]: [m0[m["ad"]], m.get("nokta")] for m in t2["mahaller"] if m.get("nokta") != m0[m["ad"]]},
                      "karkas": t2.get("karkas"), "celik_modeli": "celik_modeli" in t2,
                      "makaslar": (t2["cati"].get("makaslar") or {}).get("tam"),
                      "kalkanlar": [[k["ad"], k["konum"], k["aralik"]] for k in t2["cati"].get("kalkanlar") or []]},
            "onay": {"durum": "aday", "not": "Lokman'ın onayı bekleniyor (İE-23 PR-2a); onaylanınca tarih ve dayanak buraya yazılır"}}


@pytest.mark.parametrize("ad", sorted(HEDEFLER))
def test_hedef_ornek(ad):
    yol = HEDEF / f"{ad}.json"
    hedef = json.loads(yol.read_text(encoding="utf-8"))
    simdi = json.loads(json.dumps(ozet(ad), ensure_ascii=False))
    hedef.pop("onay", None), simdi.pop("onay", None)
    assert simdi == hedef, f"{ad}: germe çıktısı hedef örnekten farklı (yeniden dondurma yalnız onayla, D-02)"


def test_kt01_yatak_odasi_arkaya_50_ev_uzar():
    t, t2, r = _uygula(*HEDEFLER["germe_KT01_yatak_odasi_1_K50"])
    assert r["tur"] == "germe" and r["eksen"] == "y" and 682 < r["kesit_cm"] < 894
    assert r["dis_olcu"] == [[1221.0, 910.0], [1221.0, 960.0]]
    assert set(r["degisen"]) == {"Yatak Odası 1", "Banyo", "Yatak Odası 2", "Müştemilat"}
    assert all(b > a for a, b in r["degisen"].values())
    k = {k["ad"]: k for k in t2["cati"]["kalkanlar"]}
    assert k["kuzey kalkanı"]["konum"] == 960.0 and k["cumba kalkanı"]["konum"] == 0.0          # kesitin berisi yerinde
    tam = t2["cati"]["makaslar"]["tam"]
    assert tam["adet"] == len(tam["y"]) == 8 and tam["y"][0] == 949.0                             # açılan aralığa makas eklendi
    aralik = [a - b for a, b in zip(tam["y"], tam["y"][1:])]
    eski = [a - b for a, b in zip(t["cati"]["makaslar"]["tam"]["y"], t["cati"]["makaslar"]["tam"]["y"][1:])]
    assert max(aralik) <= max(eski) + 0.01
    assert "celik_modeli" not in t2 and t2["karkas"] == "kural" and r["karkas_kurala"]           # SKP modeli gerilmiş eve uymaz
    assert all("etiket_m2" not in m for m in t2["mahaller"] if m["ad"] in r["degisen"])
    assert TG.anlatim(r).startswith("ev arkaya 50 cm uzadı (uzayan öteki odalar: Banyo, Müştemilat, Yatak Odası 2); kapalı alan ")


def test_c8201_yatak_odasi_2_one_30_duvar_kayar_kapi_birlikte():
    t, t2, r = _uygula(*HEDEFLER["germe_C8201_yatak_odasi_2_G30"])
    assert r["tur"] == "kayma" and r["duvarlar"] == ["P"] and r["kayma_cm"] == -30
    p = next(d for d in t2["duvarlar"] if d["ad"] == "P")
    assert p["kutu"] == [9.25, 341, 343.5, 349]
    k10 = next(a for a in t2["acikliklar"] if a["ad"] == "K10")
    assert k10["bas"] == 239.5                                                                    # yolundaki kapı duvarla kaydı
    assert next(a for a in t2["acikliklar"] if a["ad"] == "K11")["bas"] == 390.5                 # büyüyen yandaki kapı yerinde
    assert r["dis_olcu"][0] == r["dis_olcu"][1] and r["kapali_m2"][0] == r["kapali_m2"][1]
    assert r["degisen"] == {"Yatak Odası 2": [11.92, 12.91], "Yatak Odası 1": [11.92, 10.92]}
    assert TG.kisa_anlatim(r) == "Yatak Odası 2 öne 30 cm büyütüldü"


@pytest.mark.parametrize("yol,mahal,yon,cm,buyut,gerekce", [
    ("modeller/C8201.json", "Yatak Odası 2", "G", 50, True, "Yatak Odası 1 10,26 m²'ye iner (yatak odası için en az 10,5 m²)"),
    ("modeller/C8201.json", "Yatak Odası 1", "K", 30, True, "Yatak Odası 2 kapısı yeni duvar düzenine sığmıyor"),
    ("modeller/C8801.json", "Yaşam Alanı", "D", 50, True, "Mutfak 8,12 m²'ye iner (mutfak için en az 9,5 m²)"),
    ("modeller/C8801.json", "Mutfak", "D", 50, True, "Yatak Odası 1 kapısı yeni duvar düzenine sığmıyor"),
    ("modeller/KT01.json", "Yatak Odası 1", "K", 50, False, "Yatak Odası 1 9,06 m²'ye iner"),
    ("modeller/KT01.json", "Veranda", "G", 50, True, "veranda ve çatısı otomatik değişmiyor"),
    ("modeller/KT01.json", "Salon - Mutfak", "D", 50, True, "ana çatının genişliğini ve mahya yüksekliğini"),
    ("modeller/KT02.json", "Yaşama Mekanı", "K", 20, True, "Hol dar kenarda 117 cm kalır (hol için en az 130 cm)"),
    ("modeller/KT03.json", "Mutfak", "D", 30, True, "duvarın hizasında kiriş var"),
    ("modeller/banka/KT04/tanim.json", "Yatak Odası 2", "K", 50, True, "ana çatının genişliğini ve mahya yüksekliğini"),
    ("modeller/banka/KT04/tanim.json", "Salon - Mutfak", "D", 50, True, "küçük çatıyı (cumba ya da çıkma çatısı)"),
    ("modeller/C8201.json", "Yatak Odası 1", "K", 301, True, "5–300 cm arasında tam sayı"),
    ("modeller/C8201.json", "Mutfak", "K", 30, True, "planda Mutfak adlı oda yok"),
])
def test_olumsuz_ornekler_gerekceli(yol, mahal, yon, cm, buyut, gerekce):
    t = _tanim(yol)
    with pytest.raises(TG.GermeHatasi) as e:
        TG.oda_degistir(t, mahal, yon, cm, buyut, set_yolu=SET)
    assert gerekce in str(e.value), str(e.value)
    assert "İE-" not in str(e.value) and "duzey" not in str(e.value)                            # bayinin okuyacağı dil


def test_belirlenimci_ve_varyant_ayni_tanim():
    yol, mahal, yon, cm, buyut = HEDEFLER["germe_C8201_yatak_odasi_2_G30"]
    t = _tanim(yol)
    a, _ = TG.oda_degistir(t, mahal, yon, cm, buyut)
    b = varyant.tanim_uygula(t, {"op": "oda_buyut", "mahal": mahal, "yon": yon, "cm": cm})
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert t == _tanim(yol)                                                                       # girdi değişmez
    with pytest.raises(varyant.VaryantHatasi):
        varyant.tanim_uygula(t, {"op": "oda_buyut", "mahal": mahal, "yon": yon, "cm": 50})


def test_kucultme_buyutmenin_tersi():
    """Dış kenarda 50 büyütüp aynı yandan 50 küçültmek geometriyi geri verir (şerit kesitin olduğu yerde boş)."""
    t, t2, _ = _uygula(*HEDEFLER["germe_KT01_yatak_odasi_1_K50"])
    t3, r3 = TG.oda_degistir(t2, "Yatak Odası 1", "K", 50, False, set_yolu=SET)
    assert r3["tur"] == "germe"
    assert [d["kutu"] for d in t3["duvarlar"]] == [d["kutu"] for d in t["duvarlar"]]
    assert [a["bas"] for a in t3["acikliklar"]] == [a["bas"] for a in t["acikliklar"]]
    assert [dz["plan"] for dz in t3["cati"]["duzlemler"]] == [dz["plan"] for dz in t["cati"]["duzlemler"]]


# ── okuma (germeli) ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _islem(**k):
    return {"tur": k.pop("tur"), "aciklik": None, "adaylar": [], "en": None, "yuk": None, "cati_kodu": None, "alinti": "", **k}


def test_okuyucu_ayar_kapaliyken_istem_ve_tablo_aynen():
    assert "oda büyütme/küçültme" in DO.PROMPT and "oda_buyut" not in DO.PROMPT
    assert "oda_buyut" in DO.PROMPT_GERME and "oda büyütme/küçültme" not in DO.PROMPT_GERME
    assert "oda_buyut" not in json.dumps(DO.DegisiklikListesi.model_json_schema())
    assert DO.tablo_metni([], [], False) == "## Açık planın tablosu\nPencereler:\nDış karkas: 80'lik"
    odalar = [{"ad": "Yatak Odası 1", "islev": ["yatak_odasi"], "olcu_cm": [355.3, 335.3], "cepheler": ["K"], "verandaya": []}]
    assert DO.tablo_metni([], [], False, odalar).endswith("- Yatak Odası 1 (yatak odasi): 355 × 335 cm; dış cepheler: arka")


def test_okuyucu_hazir_cevapla_germeli_sonuc():
    odalar = [{"ad": "Yaşam Alanı", "islev": ["salon", "mutfak"], "olcu_cm": [344.8, 619.0], "cepheler": ["K", "B"], "verandaya": []}]
    s = DO.oku("salonu sağa 50 cm büyütelim", [], [], False, hazir={"islemler": [_islem(tur="oda_buyut", mahal="Yaşam Alanı", yon="D", cm=50)]},
               odalar=odalar)
    assert s["durum"] == "tamam" and s["germe"] is True and s["islemler"][0]["yon"] == "D"
    s2 = DO.oku("salonu sağa 50 cm büyütelim", [], [], False, hazir={"islemler": [_islem(tur="oda_buyut", mahal="Yaşam Alanı", yon="D", cm=50)]})
    assert s2["durum"] == "hata" and "germe" not in s2                                           # ayar kapalı: şema oda işlemini almaz


def test_denetle_oda_islemleri():
    odalar = ["Yaşam Alanı", "Mutfak", "Yatak Odası 1"]
    lo = {"islemler": [_islem(tur="oda_buyut", mahal="yaşam alanı", yon="D", cm=None, alinti="salonu sağa büyüt"),
                       _islem(tur="oda_kucult", mahal="Mutfak", yon="K", cm=30)]}
    d = DO.denetle(lo, [], set(), odalar=odalar)
    assert d["ops"] == [{"op": "oda_buyut", "mahal": "Yaşam Alanı", "yon": "D", "cm": 50, "aciklama": "Yaşam Alanı sağa 50 cm büyütme",
                         "cm_varsayilan": True},
                        {"op": "oda_kucult", "mahal": "Mutfak", "yon": "K", "cm": 30, "aciklama": "Mutfak arkaya 30 cm küçültme"}]
    assert d["uygulanamaz"] == [] and d["yon_sor"] == []
    d = DO.denetle({"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon=None, cm=40, alinti="mutfağı büyüt")]}, [], set(), odalar=odalar)
    assert d["ops"] == [] and d["yon_sor"] == ["mutfağı büyüt"]
    d = DO.denetle({"islemler": [_islem(tur="oda_buyut", mahal="Kiler", yon="D", cm=40, alinti="kileri büyüt"),
                                 _islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=42.5, alinti="mutfağı 42,5"),
                                 _islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=400, alinti="mutfağı 4 metre")]}, [], set(), odalar=odalar)
    assert d["ops"] == [] and len(d["uygulanamaz"]) == 3 and "ondalıklı" in d["uygulanamaz"][1] and "5–300" in d["uygulanamaz"][2]
    d = DO.denetle({"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=40, alinti="mutfağı büyüt")]}, [], set())
    assert d["ops"] == [] and d["uygulanamaz"] == ["mutfağı büyüt"]                                # okuma germesiz yapıldıysa işlem yok


if __name__ == "__main__" and "--hedef-yaz" in sys.argv:          # yalnız onayla (D-02): aday hedefleri yazar
    for ad in sorted(HEDEFLER):
        (HEDEF / f"{ad}.json").write_text(json.dumps(ozet(ad), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("yazıldı:", ad)
