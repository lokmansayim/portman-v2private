"""İE-23 PR-2a/2b · banka modelinde oda büyütme / küçültme (`beyin/tanim_germe.py`) ve okuma (`beyin/degisiklik_okuyucu.py`, germeli).

Hedef örnekler (`hedef/germe_*.json`; Lokman onayladı, 31 Ekim 2026, İE-23 › PR-2a): KT-01 "yatak odası 1'i arkaya 50 cm" (dış kenar, düzey 1:
ev arkaya uzar) ve Ç8201 "yatak odası 2'yi öne 30 cm" (iç duvar kayar, yatak odası 1 küçülür, yolundaki ve köşesindeki kapılar duvarla kayar).
PR-2b: KT-04 "salonu sağa 50 cm" (düzey 2: cumba ve önündeki çıkma çatısı ortadan simetrik genişler; girdi `girdi/` altında dondurulmuş kopya,
banka modeli atölyede değişebilir; Lokman onayladı, 1 Kasım 2026). Kıyas:
girdi, rapor, gerilmiş tanımın kanonik sha'sı ve değişen duvar, açıklık, mahal özetleri. Yeniden yazma yalnız onayla:
`python testler/yapi_kimligi/test_tanim_germe.py --hedef-yaz`. Olumsuz örnekler gerekçesiyle (oda kuralı, kapı sığmıyor, ana çatı = düzey 3,
veranda, kiriş). Germe belirlenimcidir ve `varyant.tanim_uygula` aynı tanımı verir."""
from __future__ import annotations

import copy
import json
import re
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
    "germe_KT04_salon_mutfak_D50": ("testler/yapi_kimligi/girdi/KT04_tanim_2026-10-31.json", "Salon - Mutfak", "D", 50, True),
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
    out = {"sema": "portman.yapi_germe_hedef/0.1",
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
            "onay": {"durum": "aday", "not": "Lokman'ın onayı bekleniyor (İE-23); onaylanınca tarih ve dayanak buraya yazılır"}}
    if r.get("ikincil_cati"):                                  # düzey 2: yeniden kurulan çatı düzlemleri ve makas aileleri
        d0 = {d["ad"]: d["plan"] for d in t["cati"]["duzlemler"]}
        out["sonuc"]["cati_duzlemleri"] = {d["ad"]: [d0[d["ad"]], d["plan"]] for d in t2["cati"]["duzlemler"] if d["plan"] != d0[d["ad"]]}
        m0 = t["cati"].get("makaslar") or {}
        out["sonuc"]["makas_aileleri"] = {ad: [{k: m0[ad].get(k) for k in ("x", "y", "adet")}, {k: a.get(k) for k in ("x", "y", "adet")}]
                                          for ad, a in (t2["cati"].get("makaslar") or {}).items() if isinstance(a, dict) and a != m0.get(ad)}
    return out


@pytest.mark.parametrize("ad", sorted(HEDEFLER))
def test_hedef_ornek(ad):
    yol = HEDEF / f"{ad}.json"
    hedef = json.loads(yol.read_text(encoding="utf-8"))
    simdi = json.loads(json.dumps(ozet(ad), ensure_ascii=False))
    hedef.pop("onay", None), simdi.pop("onay", None)
    assert simdi == hedef, f"{ad}: germe çıktısı hedef örnekten farklı (yeniden dondurma yalnız onayla, D-02)"



@pytest.mark.parametrize("ad", sorted(HEDEFLER))
def test_hedef_germe_ciktisinda_yazi_cakismaz(ad, tmp_path):
    # PR-2a'nın kabul koşulu (ayar `banka_germe.acik` bundan önce açılmaz): bayiye giden dört figür (plan görseli, kartın alt sırası, şablon
    # paftasının iki sayfası) germe çıktısında da yazı çakışmasız (D-16). KT-01 ve KT-04'te karkas kurala geçilir; duvar panelleri ve makas
    # paftaları dosya adıyla ayrı sayılır, bayi paftası denetlenir (PR-2b'ye kadar onların sayfaları "pafta_sayfa" sanılıyordu)
    from araclar.atolye import _yazi_bulgulari, yazi_denetimi
    from motor.genel import uret
    _, t2, _ = _uygula(*HEDEFLER[ad])
    g = tmp_path / "girdi.json"
    g.write_text(json.dumps(t2, ensure_ascii=False), encoding="utf-8")
    rap: dict = {}
    bilgi = {"bayi_adi": "Deneme Bayi", "sevk_adresi": "Deneme Mah. Deneme Sok. No 1 Deneme İlçesi / Deneme İli",
             "ozel_istekler": ["çatı antrasit"], "ozellikler": {"Dış Boya Rengi": "krem"}}
    with yazi_denetimi(rap):
        m = uret.uret(g, tmp_path / "c", is_emri_no="PM-TEST-20261031-1", revizyon=2, set_yolu=SET, yontem="panel", perspektif=False,
                      bayi=True, bilgi=bilgi)
    assert m["passed"], m.get("warnings")
    assert _yazi_bulgulari(rap, uret.kod_govde(t2)) == []
    assert (t2.get("karkas") == "kural") == any(k.endswith("_duvar_panelleri.pdf#1") for k in rap), sorted(rap)

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
    # büyüyen yandaki köşeye bağlı kapı da duvarla kayar, köşeye 11,5 cm uzaklığı korunur (Lokman 31.10 19:40: "kapıyı da kaydırman lazımdı")
    assert next(a for a in t2["acikliklar"] if a["ad"] == "K11")["bas"] == 360.5
    assert r["dis_olcu"][0] == r["dis_olcu"][1] and r["kapali_m2"][0] == r["kapali_m2"][1]
    assert r["degisen"] == {"Yatak Odası 2": [11.92, 12.91], "Yatak Odası 1": [11.92, 10.92]}
    assert TG.kisa_anlatim(r) == "Yatak Odası 2 öne 30 cm büyütüldü"
    # kayan kapı bayiye yazılır (K21; geometri hakemi 31.10 bulgu 5)
    assert r["kayan_acikliklar"] == [{"ad": "K10", "tur": "kapı", "mahaller": ["Hol", "Yatak Odası 1"], "cm": 30, "yon": "G"},
                                     {"ad": "K11", "tur": "kapı", "mahaller": ["Hol", "Yatak Odası 2"], "cm": 30, "yon": "G"}]
    assert TG.anlatim(r).endswith("; Hol ile Yatak Odası 1 arasındaki kapı 30 cm öne kaydı; Hol ile Yatak Odası 2 arasındaki kapı 30 cm öne kaydı")


def test_kt04_salon_saga_50_kucuk_cati_ortadan_simetrik_genisler():
    """PR-2b (düzey 2): KT-04 salonu sağa 50 cm. Ev sağa uzar; salonun önündeki cumba ve çıkma çatısı ortadan simetrik genişler (sırtın
    iki yanında 25'er cm kesit): sırt yeni ortada, vadilerin buluştuğu tepe düzlemlerin kesişiminden, saçak taşmaları aynı, çıkmanın
    penceresi ortada kalır."""
    t, t2, r = _uygula(*HEDEFLER["germe_KT04_salon_mutfak_D50"])
    assert r["tur"] == "germe" and r["eksen"] == "x" and len(r["kesit_cm"]) == 2
    assert r["ikincil_cati"] == ["doğu cumba batı", "doğu cumba doğu", "doğu çıkma batı", "doğu çıkma doğu"]
    assert TG.kisa_anlatim(r) == "Salon - Mutfak sağa 50 cm büyütüldü" and r["kapali_m2"] == [106.28, 110.29]
    D = {d["ad"]: d["plan"] for d in t2["cati"]["duzlemler"]}
    assert D["doğu cumba batı"] == [[1112.0, 50.0], [1374.0, 50.0], [1374.0, 491.0], [1112.0, 229.0]]
    assert D["doğu cumba doğu"] == [[1374.0, 50.0], [1636.0, 50.0], [1636.0, 229.0], [1374.0, 491.0]]
    assert [1374.0, 491.0] in D["güney"] and [1349.0, 466.0] not in D["güney"]                    # vadilerin tepesi 45° (eğimler eşit)
    assert D["doğu çıkma batı"][1][0] == D["doğu çıkma doğu"][0][0] == 1374.0
    w = {d["ad"]: d["kutu"] for d in t2["duvarlar"]}
    w0 = {d["ad"]: d["kutu"] for d in t["duvarlar"]}
    assert (w["W13"][0] + w["W15"][2]) / 2 == 1374.0                                                # çıkmanın ortası = sırt
    p11 = next(a for a in t2["acikliklar"] if a["ad"] == "P11")
    assert p11["bas"] + p11["en"] / 2 == 1373.8 and next(a for a in t["acikliklar"] if a["ad"] == "P11")["bas"] + 100 == 1348.8   # pencere ortada
    assert 1636.0 - w["W03"][2] == 1586.0 - w0["W03"][2] == 30                                    # saçak taşmaları aynı
    assert 1571.0 - w["W15"][2] == 1521.0 - w0["W15"][2] == 30 and w["W13"] == w0["W13"]
    m = t2["cati"]["makaslar"]
    assert m["dogu_cumba"]["x"] == [1112.0, 1636.0] and m["dogu_cumba_vadi"]["x"] == [1228.6, 1520.2] and m["dogu_cikma"]["x"] == [1177.4, 1571.3]
    a, a0 = sorted(m["ana"]["x"]), sorted(t["cati"]["makaslar"]["ana"]["x"])
    assert max(y - x for x, y in zip(a, a[1:])) <= max(y - x for x, y in zip(a0, a0[1:])) + 0.01   # ana makas aralığı tanımdakini aşmaz



def _kt04_bozuk(fn) -> str:
    """KT-04 sağa 50'nin çıktısını bozar, yalnız çatı hakemine verir (öneren koddan bağımsız; geometri hakemi 31.10, PR-2b 1. tur bulgu 2)."""
    from motor.genel import cati_genel, kural as MK
    t, t2, _ = _uygula(*HEDEFLER["germe_KT04_salon_mutfak_D50"])
    fn(t2)
    with pytest.raises(TG.GermeHatasi) as e:
        TG._cati_hakemi(t, cati_genel.cati_kur(t["cati"], MK.oku()), t2, cati_genel.cati_kur(t2["cati"], MK.oku()))
    return str(e.value)


def _nokta_degistir(t2, eski, yeni, ad_basi=""):
    for d in t2["cati"]["duzlemler"]:
        if d["ad"].startswith(ad_basi):
            for p in d["plan"]:
                if p == eski:
                    p[:] = yeni


def test_hakem_kucuk_catinin_bozuklugunu_yakalar():
    # öneren kod düzey 2'de tepeyi yeniden hesaplamasaydı, sırtı ortaya almasaydı, saçağı kısaltsaydı hakem `cati_kur`un kurabildiği çatıyı
    # kabul ediyordu. Şimdi: yüzlerin birleşimi (kotu tutmayan yüzler ortak kenar sayılmaz), saçak taşması, mahyanın ortasındaki pencere,
    # vadideki makas ucu değişmez
    oturmuyor = "çatı yüzleri birbirine oturmuyor"
    assert oturmuyor in _kt04_bozuk(lambda t2: _nokta_degistir(t2, [1374.0, 491.0], [1374.0, 466.0]))          # tepe eski yükseklikte
    assert oturmuyor in _kt04_bozuk(lambda t2: (_nokta_degistir(t2, [1374.0, 50.0], [1349.0, 50.0], "doğu cumba"),
                                                 _nokta_degistir(t2, [1374.0, 491.0], [1349.0, 466.0])))         # sırt ortada değil

    def duvar_kayar(t2):                                                                          # çatı tutarlı, altındaki duvar kayık
        w = next(d for d in t2["duvarlar"] if d["ad"] == "W03")
        w["kutu"] = [w["kutu"][0] - 25, w["kutu"][1], w["kutu"][2] - 25, w["kutu"][3]]
    assert _kt04_bozuk(duvar_kayar) == "çatının saçak taşması değişiyor"

    def pencere_kayar(t2):
        next(a for a in t2["acikliklar"] if a["ad"] == "P11")["bas"] += 25
    assert _kt04_bozuk(pencere_kayar) == "Salon - Mutfak penceresi çatının ortasında kalmıyor"

    def vadi_makasi(t2):
        t2["cati"]["makaslar"]["dogu_cumba_vadi"]["x"][1] += 25
    assert _kt04_bozuk(vadi_makasi) == "küçük çatının makası vadiye oturmuyor"

    def yerinde_mahyanin_penceresi(t2):                                                           # batı çıkmanın mahyası bu istekte yerinde
        next(a for a in t2["acikliklar"] if a["ad"] == "P10")["bas"] += 15                       # (2. tur not 2: istisna yalnız kaymada)
    assert _kt04_bozuk(yerinde_mahyanin_penceresi).endswith("penceresi çatının ortasında kalmıyor")


def test_tek_kesit_cumba_ekseninde_ic_kapiyi_kaydirmaz():
    # yalnız cumba alnındaki (dış duvardaki) açıklık sırtla kayar; cumbanın ekseninde duran iç kapı çatıya bağlı değil
    # (geometri hakemi 31.10, PR-2b 2. tur not 1: Ç8801'de banyo–yatak odası 2 kapısı cumba ortasına alınınca 25 cm kayıyordu)
    t = _tanim("modeller/C8801.json")
    k5 = next(a for a in t["acikliklar"] if a["ad"] == "K5")
    p9 = next(a for a in t["acikliklar"] if a["ad"] == "P9")
    k5["bas"] = p9["bas"] + p9["en"] / 2 - k5["en"] / 2                                           # kapının ortası = cumba sırtı
    t2, r = TG.oda_degistir(t, "Banyo", "D", 50, True, set_yolu=SET)
    assert [a["ad"] for a in r["kayan_acikliklar"]] == ["P9"]
    assert next(a for a in t2["acikliklar"] if a["ad"] == "K5")["bas"] == k5["bas"]


def test_c8801_banyo_saga_tek_kesit_cumbanin_penceresi_ortada_kalir():
    # tek kesitli düzey 2 (banyo cumbanın bir yanında: iki yarım kesit banyodan geçmez): cumba tek yandan genişler, sırt 25 cm sağa gider;
    # cumba alnındaki pencere de 25 cm kayar, sırtın altında kalır ve bayiye yazılır (geometri hakemi 31.10, PR-2b 1. tur not 5)
    from motor.genel import cati_genel, kural as MK
    t = _tanim("modeller/C8801.json")
    t2, r = TG.oda_degistir(t, "Banyo", "D", 50, True, set_yolu=SET)
    assert isinstance(r["kesit_cm"], float) and r["ikincil_cati"] == ["cumba batı", "cumba doğu"]
    assert r["kayan_acikliklar"] == [{"ad": "P9", "tur": "pencere", "mahaller": ["Yatak Odası 2"], "cm": 25.0, "yon": "D"}]
    p9 = next(a for a in t2["acikliklar"] if a["ad"] == "P9")
    mahya = [e for e in cati_genel.cati_kur(t2["cati"], MK.oku())["kenarlar"] if e["tur"] == "mahya" and e["p"][0] == e["q"][0]]
    assert p9["bas"] + p9["en"] / 2 == mahya[0]["p"][0] == 849.0 and next(a for a in t["acikliklar"] if a["ad"] == "P9")["bas"] == 764
    assert TG.anlatim(r).endswith("; cumba genişledi, çatısı yeni ölçüye göre kuruldu; Yatak Odası 2 penceresi 25 cm sağa kaydı (ortada kaldı)")

def test_kt04_kucuk_cati_ana_cati_mahyasini_asamaz():
    t = _tanim("testler/yapi_kimligi/girdi/KT04_tanim_2026-10-31.json")
    TG.oda_degistir(t, "Salon - Mutfak", "D", 120, True, set_yolu=SET)                             # tepe 526 < mahya 527,5
    with pytest.raises(TG.GermeHatasi, match="ana çatının mahyasını aşıyor"):
        TG.oda_degistir(t, "Salon - Mutfak", "D", 150, True, set_yolu=SET)


def test_kose_kurali_buyuyen_ve_kuculen_yanda_aciklik_duvarla_kayar():
    """Lokman 31.10 19:40 ("kapıyıda kaydırman lazımdı"): iç duvar kayınca köşesine bağlı açıklık (kenarı duvar yüzüne 50 cm'den yakın,
    en yakın duvar o) iki yanda da duvarla kayar, köşeye uzaklığı korunur. KT-01 yatak odası 2 soldan 30 küçülür: büyüyen banyonun
    penceresi ve kapısı duvarla sağa kayar; köşeye uzak açıklıklar yerinde."""
    t = _tanim("modeller/KT01.json")
    t2, r = TG.oda_degistir(t, "Yatak Odası 2", "B", 30, False, set_yolu=SET)
    assert [a["ad"] for a in r["kayan_acikliklar"]] == ["P5", "K5"]
    assert TG.anlatim(r).endswith("; Banyo penceresi 30 cm sağa kaydı; Banyo ile Salon - Mutfak arasındaki kapı 30 cm sağa kaydı")
    once = {a["ad"]: a["bas"] for a in t["acikliklar"]}
    for a in t2["acikliklar"]:
        assert a["bas"] == (once[a["ad"]] + 30 if a["ad"] in ("P5", "K5") else once[a["ad"]]), a["ad"]
    ay0, ay1 = TG._ayaklar(t), TG._ayaklar(t2)
    assert ay1["P5"] == ay0["P5"] and ay1["K5"] == ay0["K5"]                                      # köşeye uzaklık korunur


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
    ("modeller/C8201.json", "Yatak Odası 1", "K", 301, True, "5–300 cm arasında tam sayı"),
    ("modeller/C8201.json", "Mutfak", "K", 30, True, "planda Mutfak adlı oda yok"),
    # geometri hakemi 31.10: 15 cm parça (D-10; B ve R duvar eksenleri 10 cm arayla) ve karkas kuralında kurulamayan liste (KT-02 kiris_15)
    ("modeller/C8201.json", "Hol", "D", 30, True, "duvarlar arasında 10 cm'lik bir kırık çıkıyor (çelikte 15 cm ve daha kısa parça yapılmaz)"),
    ("modeller/KT02.json", "Yatak Odası 1", "K", 50, True, "bu modelin çelik listesi değişen ölçülere otomatik uyarlanamıyor"),
    ("modeller/KT02.json", "Banyo", "G", 20, True, "bu modelin çelik listesi değişen ölçülere otomatik uyarlanamıyor"),
    # geometri hakemi ikinci tur: kayan duvarla kayan kapının öbür ayağı birleşen duvara 10 cm'den yakın kalmaz (`plan_derle` payı)
    ("modeller/C8801K.json", "Mutfak", "D", 20, True, "Yatak Odası 1 kapısı duvar köşesine 1,5 cm kalıyor (en az 10 cm olmalı)"),
    ("modeller/C8801.json", "Yatak Odası 2", "K", 20, True, "Banyo kapısı duvar köşesine 1,5 cm kalıyor (en az 10 cm olmalı)"),
    # geometri hakemi üçüncü tur: küçültme gerekçesi isteği doğru anar
    ("modeller/KT01.json", "Salon - Mutfak", "D", 50, False, "sağdan küçülmek ana çatının genişliğini ve mahya yüksekliğini değiştirir"),
    # PR-2b: düzey 2 açıldıktan sonra KT-01 müştemilatın sol yanındaki kesit üstü eğimli duvardan geçer (gerekçede duvar kodu yok)
    ("modeller/KT01.json", "Müştemilat", "B", 30, True, "kesit üstü eğimli bir duvardan geçiyor"),
    # PR-2b: küçük çatı ortadan simetrik daralır (sırtın iki yanında 25'er cm şerit); çıkmanın içinde o kadar yer yok
    ("modeller/banka/KT04/tanim.json", "Salon - Mutfak", "D", 50, False, "odanın içinden kesit geçecek boş yer yok (50 cm genişliğinde)"),
    # köşe kuralı (Lokman 31.10): kayınca kendi duvarının dışına taşacak köşe kapısı (Çocuk Odası K4) yerinde kalır; gerekçe oda kuralı
    ("modeller/KT03.json", "Yatak Odası", "D", 50, False, "Yatak Odası 10,30 m²'ye iner (yatak odası için en az 10,5 m²)"),
])
def test_olumsuz_ornekler_gerekceli(yol, mahal, yon, cm, buyut, gerekce):
    t = _tanim(yol)
    with pytest.raises(TG.GermeHatasi) as e:
        TG.oda_degistir(t, mahal, yon, cm, buyut, set_yolu=SET)
    assert gerekce in str(e.value), str(e.value)
    assert "İE-" not in str(e.value) and "duzey" not in str(e.value)                            # bayinin okuyacağı dil
    assert not re.search(r"\b[A-ZÇĞİÖŞÜ]{1,4}\d+\b|_", str(e.value)), str(e.value)               # duvar, açıklık, makas kodu yok


def test_ayni_duvarda_aciklik_ortusmesi_gecmez():
    """Geometri hakemi 31.10 (bulgu 4): kayan açıklık aynı duvardaki öteki açıklığın üstüne binerse hakem geçirmez. Banka modellerinde
    bugün çıkmıyor; Ç8201'in sol dış duvarına iki pencere eklenerek kurulur (140–240, 250–350; yatak odası 1'in yanındaki kayar)."""
    t = _tanim("modeller/C8201.json")
    t["acikliklar"] += [{"ad": "PX1", "tur": "pencere", "duvar": "DL", "bas": 140, "en": 100, "yuk": 120, "alt": 90, "mahal": "Yatak Odası 1"},
                        {"ad": "PX2", "tur": "pencere", "duvar": "DL", "bas": 250, "en": 100, "yuk": 120, "alt": 90, "mahal": "Yatak Odası 1"}]
    with pytest.raises(TG.GermeHatasi) as e:
        TG.oda_degistir(t, "Yatak Odası 2", "G", 30, set_yolu=SET)
    assert str(e.value) == "Yatak Odası 1 penceresi ile Yatak Odası 1 penceresi aynı duvarda üst üste biniyor"


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
    # makaslar: aralık tanımdaki en büyük aralığı aşmaz, en küçüğünden dar kalmaz (adet en az olmayabilir: 7 yerine 8; İE-23 › Sınırlar)
    for ad, aile in t["cati"]["makaslar"].items():
        if not isinstance(aile, dict) or not isinstance(aile.get("y"), list):
            continue
        a0, a3 = sorted(aile["y"]), sorted(t3["cati"]["makaslar"][ad]["y"])
        g0, g3 = [b - a for a, b in zip(a0, a0[1:])], [b - a for a, b in zip(a3, a3[1:])]
        assert (a3[0], a3[-1]) == (a0[0], a0[-1]) and max(g3) <= max(g0) + 0.01 and min(g3) >= min(g0) - 0.5, (ad, a0, a3)


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
                        {"op": "oda_kucult", "mahal": "Mutfak", "yon": "K", "cm": 30, "aciklama": "Mutfak arkadan 30 cm küçültme"}]
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
        yol, yeni = HEDEF / f"{ad}.json", ozet(ad)
        if yol.exists():                                                # içeriği aynı kalan hedefin onayı korunur
            eski = json.loads(yol.read_text(encoding="utf-8"))
            onay = eski.pop("onay", None)
            if eski == {k: v for k, v in json.loads(json.dumps(yeni, ensure_ascii=False)).items() if k != "onay"}:
                print("aynı:", ad)
                continue
        yol.write_text(json.dumps(yeni, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("yazıldı:", ad)
