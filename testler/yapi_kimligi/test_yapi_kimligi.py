"""İE-23 PR-1 · yapı kimliği (`beyin/yapi_kimligi.py`).

Aday hedef örnek: Ç8801'in kimliği (`hedef/C8801.json`; kural seti 0.19 pimli). Kimliği üreten kod değişince bununla kıyaslanır (D-28 m.3);
bilerek değişirse yeniden dondurma İE-23 belgesindeki onayla, testi geçirmek için değil. Ayrıca: yedi banka modelinde bütün kapılar ve
pencereler kimliğe girer ve her mahal girişten ulaşılır; imza addan ve aynadan bağımsızdır; plan sözleşmesinin kayıpsız olduğu modellerde
tanım ve sözleşme aynı grafiği verir, kayıplı olduğu modellerde (dikdörtgene yaslanırken kısa bir duvar komşuluğu düşer) fark görünür
(İE-23 › Amaç); germe bandı açıklıktan ve duvar kalınlığından geçmez; çatı parçaları ve kenar kuralları (geometri hakemi, 30 Ekim 2026);
Ç8801'in ön bilgileri elle bakılmış değerlerle."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import yapi_kimligi as YK  # noqa: E402
from beyin.celik import tanim_sha_icerik  # noqa: E402
from beyin.plan_adaptor import celik_oku  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
HEDEF = Path(__file__).resolve().parent / "hedef"
MODELLER = ("C8201", "C8801", "C8801K", "C8801L", "KT01", "KT02", "KT03")
KAPI = ("dis_kapi", "ic_kapi", "gecit")


def _tanim(kod: str) -> dict:
    return json.loads((KOK / "modeller" / f"{kod}.json").read_text(encoding="utf-8"))


_ONBELLEK: dict[str, dict] = {}


def _kimlik(kod: str) -> dict:
    if kod not in _ONBELLEK:
        _ONBELLEK[kod] = YK.tanimdan(_tanim(kod), SET)
    return copy.deepcopy(_ONBELLEK[kod])


def _farklar(a, b, yol: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [f for k in sorted(set(a) | set(b)) for f in (_farklar(a.get(k), b.get(k), f"{yol}.{k}") if k in a and k in b else [f"{yol}.{k}: yalnız bir yanda"])]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [f for i, (x, y) in enumerate(zip(a, b)) for f in _farklar(x, y, f"{yol}[{i}]")]
    return [] if a == b else [f"{yol}: {str(a)[:60]} ≠ {str(b)[:60]}"]


def test_c8801_hedefle_ayni():
    hedef = json.loads((HEDEF / "C8801.json").read_text(encoding="utf-8"))
    fark = _farklar(_kimlik("C8801"), hedef)
    assert not fark, "Ç8801 kimliği aday hedeften farklı:\n" + "\n".join(fark[:20])


def test_belirlenimci_ve_sema():
    a, b = YK.tanimdan(_tanim("C8801"), SET), YK.tanimdan(_tanim("C8801"), SET)
    assert a == b
    assert a["sema"] == YK.SEMA and set(a) >= {"anlamsal", "topolojik", "parametrik", "sayisal", "kaynak"}
    assert a["kaynak"]["tanim_sha256"] == tanim_sha_icerik(_tanim("C8801")) and a["kaynak"]["kural_seti"] == "0.19.json"


@pytest.mark.parametrize("kod", MODELLER)
def test_banka_modeli_eksiksiz(kod):
    """Her kapı bir kenarda, her pencere bir mahalde; her mahal girişten ulaşılır; oda programı bayi görseliyle aynı."""
    from motor.genel.bayi_gorseli import oda_programi
    t, k = _tanim(kod), _kimlik(kod)
    kapilar = {a["ad"] for a in t["acikliklar"] if a["tur"] in KAPI}
    assert {x for e in k["topolojik"]["kenarlar"] for x in e["kapilar"]} == kapilar
    assert k["sayisal"]["kapi"] == len(kapilar)
    pencereler = sorted(a["ad"] for a in t["acikliklar"] if a["tur"] == "pencere")
    assert sorted(p["ad"] for m in k["anlamsal"]["mahaller"] for p in m["pencereler"]) == pencereler
    assert sorted(x for e in k["topolojik"]["kenarlar"] for x in e["pencereler"]) == pencereler
    assert all(p["disi"] in (YK.DIS, "veranda") for m in k["anlamsal"]["mahaller"] for p in m["pencereler"])
    assert k["topolojik"]["eslesmeyen_acikliklar"] == [] and k["topolojik"]["ulasilamayan"] == []
    assert all(d["derinlik"] >= 1 for d in k["topolojik"]["dugumler"] if d["ad"] != YK.DIS)
    assert len(k["topolojik"]["dugumler"]) == len(t["mahaller"]) + 1
    assert k["anlamsal"]["oda_programi"] == oda_programi(t)
    # her mahalin dört yanında en az bir kenar; her kenarın ön bilgisi ve gerekçesi var
    for m in k["anlamsal"]["mahaller"]:
        yonler = {e["yon"] for e in k["parametrik"]["kenarlar"] if e["mahal"] == m["ad"]}
        assert yonler <= set(YK.YONLER) and (m["sinif"] == "veranda" or yonler == set(YK.YONLER)), (m["ad"], yonler)
    assert all(e["durum"] in YK.RENK_DURUM and e["neden"] for e in k["parametrik"]["kenarlar"])


@pytest.mark.parametrize("kod", MODELLER)
def test_germe_bandi_aciklik_ve_duvar_kesmez(kod):
    from motor.genel import yapi
    t, k = _tanim(kod), _kimlik(kod)
    y = yapi.kur(t)
    for eksen, bantlar in k["parametrik"]["germe"].items():
        i0, i1 = (0, 2) if eksen == "x" else (1, 3)
        assert bantlar, f"{kod}: {eksen} ekseninde hiç germe bandı yok"
        for g in bantlar:
            a, b = g["aralik"]
            assert a < b and g["duzey"] in (1, 2, 3)
            for ac in y["acikliklar"]:
                if y["adli"][ac["duvar"]]["yon"] == eksen:
                    assert b <= ac["a0"] - YK.KESIT_PAYI + 0.05 or a >= ac["a1"] + YK.KESIT_PAYI - 0.05, (kod, eksen, g["aralik"], ac["ad"])
            for d in y["duvarlar"]:
                if d["yon"] != eksen or d["sinif"] == "kolon":
                    assert b <= d["kutu"][i0] - YK.KESIT_PAYI + 0.05 or a >= d["kutu"][i1] + YK.KESIT_PAYI - 0.05, (kod, eksen, g["aralik"], d["ad"])


def test_imza_addan_bagimsiz_kapidan_bagimli():
    t = _tanim("C8201")
    ad = {m["ad"]: f"M{i}" for i, m in enumerate(t["mahaller"])}
    t2 = copy.deepcopy(t)
    for m in t2["mahaller"]:
        m["ad"] = ad[m["ad"]]
    for a in t2["acikliklar"]:
        if a.get("mahal"):
            a["mahal"] = ad[a["mahal"]]
    for d in (t2.get("osb_takviye") or {}).get("duvarlar", []):
        d["mahal"] = ad[d["mahal"]]
    k1, k2 = _kimlik("C8201"), YK.tanimdan(t2, SET)
    assert k1["topolojik"]["imza"] == k2["topolojik"]["imza"] and k1["kaynak"]["tanim_sha256"] != k2["kaynak"]["tanim_sha256"]
    t3 = copy.deepcopy(t)                                     # bir iç kapı kalkınca bağlantı değişir, imza da
    ic = next(a for a in t3["acikliklar"] if a["tur"] == "ic_kapi")
    t3["acikliklar"].remove(ic)
    assert YK.tanimdan(t3, SET)["topolojik"]["imza"] != k1["topolojik"]["imza"]


def test_imza_aynadan_bagimsiz_prefabrik():
    """Eski biçim prefabrik İş Emri (pano aksı) sözleşmeden okunur; P6001'in iki aynası aynı bağlantıdır."""
    kim = {ad: YK.oku(json.loads((KOK / "is_emri" / f"{ad}.json").read_text(encoding="utf-8"))) for ad in ("P6001_2plus1_6x6", "P6001_ayna_x", "P6001_ayna_y")}
    assert len({k["topolojik"]["imza"] for k in kim.values()}) == 1
    k = kim["P6001_2plus1_6x6"]
    assert k["aile"] == "tek_kat_prefabrik" and k["kaynak"]["alan_olcusu"] == "pano_aksi" and k["parametrik"]["germe"] is None
    assert k["anlamsal"]["oda_programi"] == "2+1" and k["topolojik"]["ulasilamayan"] == [] and k["topolojik"]["eslesmeyen_acikliklar"] == []
    bx = {m["ad"]: m["cepheler"] for m in k["anlamsal"]["mahaller"]}
    ax = {m["ad"]: m["cepheler"] for m in kim["P6001_ayna_x"]["anlamsal"]["mahaller"]}
    takas = {"B": "D", "D": "B"}
    assert all(sorted((takas.get(c, c) for c in bx[a]), key=YK.YONLER.index) == ax[a] for a in bx)


def _kenar(k: dict) -> set:
    return {(e["a"], e["b"], bool(e["kapilar"]), e["acik"]) for e in k["topolojik"]["kenarlar"]}


@pytest.mark.parametrize("kod", ("C8201", "C8801", "C8801K", "C8801L", "KT01"))
def test_tanim_ve_sozlesme_ayni_grafik(kod):
    """Sözleşmenin bu modeli kayıpsız taşıdığı yerde iki kaynak aynı grafiği verir (kapılar, açık geçişler, komşuluklar, imza, cepheler);
    pencereler aynı mahalde ve cephede. Sözleşmede pencerenin yeri yok: cephenin arkasında hem dış hem veranda varsa `belirsiz`."""
    a, b = _kimlik(kod), YK.plandan(celik_oku(_tanim(kod)))
    assert _kenar(a) == _kenar(b) and a["topolojik"]["imza"] == b["topolojik"]["imza"]
    assert [d["derinlik"] for d in a["topolojik"]["dugumler"]] == [d["derinlik"] for d in b["topolojik"]["dugumler"]]
    assert b["topolojik"]["eslesmeyen_acikliklar"] == [] and b["anlamsal"]["oda_programi"] == a["anlamsal"]["oda_programi"]
    ma, mb = ({m["ad"]: m for m in k["anlamsal"]["mahaller"]} for k in (a, b))
    for ad, m in ma.items():
        assert (m["cepheler"], m["verandaya"]) == (mb[ad]["cepheler"], mb[ad]["verandaya"]), ad
        pa = sorted((p["cephe"], p["disi"]) for p in m["pencereler"])
        pb = sorted((p["cephe"], p["disi"]) for p in mb[ad]["pencereler"])
        assert [c for c, _ in pa] == [c for c, _ in pb] and all(y in (x, "belirsiz") for (_, x), (_, y) in zip(pa, pb)), (ad, pa, pb)


@pytest.mark.parametrize("kod, kayip", (("KT02", ("Sundurma", "Yaşama Mekanı")), ("KT03", ("Hol", YK.DIS))))
def test_sozlesme_kayipli_modellerde_fark_gorunur(kod, kayip):
    """İE-23 deneyi: sözleşmeye çeviri mahalleri eksene yaslı dikdörtgenlere çeker. KT-02'de sundurmanın yaşama mekânına değen 8 cm'lik,
    KT-03'te holün sundurmanın yanında dışa değen 29 cm'lik duvarı kaybolur. Sözleşme yeni bağlantı uydurmaz; tanımın kimliği fazlasını
    taşır, imza farklıdır (banka revizyonu bu yüzden tanımda yapılır)."""
    a, b = _kimlik(kod), YK.plandan(celik_oku(_tanim(kod)))
    assert _kenar(b) < _kenar(a) and _kenar(a) - _kenar(b) == {(*kayip, False, False)}
    e = next(e for e in a["topolojik"]["kenarlar"] if (e["a"], e["b"]) == kayip)
    assert 0 < e["ortak_duvar_cm"] < 40 and not e["pencereler"]
    assert a["topolojik"]["imza"] != b["topolojik"]["imza"]


def test_c8801_on_bilgi():
    """Elle bakılmış değerler (30 Ekim 2026; görsel PF Yapi_Kimligi/): hol merkezli, verandadan girilir; ana çatının mahyası doğu–batı."""
    k = _kimlik("C8801")
    der = {d["ad"]: d["derinlik"] for d in k["topolojik"]["dugumler"]}
    assert der["Veranda"] == 1 and der["Hol"] == 2 and k["topolojik"]["duzen"] == "hol_merkezli" and k["topolojik"]["merkez"] == "Hol"
    assert k["anlamsal"]["cati"]["mahya"] == "x" and k["anlamsal"]["oda_programi"] == "2+1"
    ken = {(e["mahal"], e["yon"]): e for e in k["parametrik"]["kenarlar"] if e["en_dis"]}
    # salon sola: dış duvar; düzey 1 kesitlerin hepsi önündeki verandayı da keser (veranda bu işte değişmez)
    assert ken[("Yaşam Alanı", "B")]["tur"] == "dis" and ken[("Yaşam Alanı", "B")]["durum"] == "kilitli"
    assert "verandayı da keser" in ken[("Yaşam Alanı", "B")]["neden"]
    # yatak odası 1 sağa: cumba çatısı yeniden (düzey 2)
    assert ken[("Yatak Odası 1", "D")]["durum"] == "duzey2" and "cumba" in ken[("Yatak Odası 1", "D")]["neden"]
    # mutfak arkaya: ana çatının açıklığı değişir (düzey 3, kilitli)
    assert ken[("Mutfak", "K")]["durum"] == "kilitli" and "düzey 3" in ken[("Mutfak", "K")]["neden"]
    # salon sağa: iç duvar, karşıdaki hol ve mutfak tam paylaşıyor
    assert ken[("Yaşam Alanı", "D")]["tur"] == "ic" and ken[("Yaşam Alanı", "D")]["durum"] == "oynar"
    # salonun önü verandaya bakar: veranda bu işte değişmez
    assert ken[("Yaşam Alanı", "G")]["tur"] == "veranda" and ken[("Yaşam Alanı", "G")]["durum"] == "kilitli"
    # banyo sola: T birleşiminde karşıdaki hol ve yatak odası 1 yalnız banyoya bakıyor, duvar kayar
    assert ken[("Banyo", "B")]["tur"] == "ic" and ken[("Banyo", "B")]["durum"] == "oynar"
    pen = {p["ad"]: p for m in k["anlamsal"]["mahaller"] for p in m["pencereler"]}
    assert pen["P1"]["disi"] == "veranda" and pen["P7"]["olcu"] == "60x40" and pen["P3"]["cephe"] == "B"


@pytest.mark.parametrize("kod, ana, ikincil", (
    ("C8801", {"ana güney", "ana kuzey"}, {"cumba doğu", "cumba batı"}),
    ("C8801K", {"ana güney", "ana kuzey", "doğu", "cumba batı"}, set()),     # cumba doğu yüzü ana çatının doğu yüzüyle sırt yapar
    ("C8801L", {"batı blok güney", "batı blok kuzey", "kanat batı güney", "kanat batı kuzey", "kanat doğu"}, set()),  # L: tepeler eşit
    ("KT01", {"batı", "doğu", "cumba doğu"}, {"veranda", "müştemilat"}),
    ("KT02", {"batı", "doğu", "güney", "kuzey"}, {"sundurma güney", "sundurma kuzey", "sundurma batı"}),
    ("KT03", {"kuzey", "batı", "batı güney", "kanat batı", "kanat güney", "kanat doğu", "doğu güney", "doğu"}, {"veranda", "sundurma"}),
))
def test_cati_parcalari(kod, ana, ikincil):
    """Ana çatı düzlem alanıyla değil, sırt ve kırmayla bağlı parçanın tepesiyle ayrılır (geometri hakemi 1: Ç8801L kanadı, KT-03
    kırmasının güney yüzleri ana çatıdır)."""
    p = _kimlik(kod)["anlamsal"]["cati"]["parcalar"]
    assert {d for x in p if x["ana"] for d in x["duzlemler"]} == ana
    assert {d for x in p if not x["ana"] for d in x["duzlemler"]} == ikincil


@pytest.mark.parametrize("kod", MODELLER)
def test_veranda_degismez(kod):
    """Veranda mahalinin ve verandaya bakan kenarlar kilitli; oynayan ya da düzey 2 dış kenarın kesit aralıkları verandayı kesmez."""
    k = _kimlik(kod)
    veranda = {m["ad"] for m in k["anlamsal"]["mahaller"] if m["sinif"] == "veranda"}
    for e in k["parametrik"]["kenarlar"]:
        if e["mahal"] in veranda or e["tur"] == "veranda":
            assert e["durum"] == "kilitli", (e["mahal"], e["yon"])
        if e["tur"] == YK.DIS and e["durum"] != "kilitli":
            bantlar = k["parametrik"]["germe"][YK.YON_EKSEN[e["yon"]]]
            for a, b in e["kesit_bantlari"]:
                ic = [g for g in bantlar if g["aralik"][0] >= a - 0.05 and g["aralik"][1] <= b + 0.05]
                assert ic and not any(set(g["mahaller"]) & veranda for g in ic), (e["mahal"], e["yon"], a, b)


def test_kenar_on_bilgileri():
    """Geometri hakemi (30 Ekim 2026) bulguları: kaçık hizada devam eden komşu iç kenarı kilitler; T birleşimi kilitlemez; ana çatıya dik
    kesit düzey 3; PR-2'nin düzey 1 hedefi."""
    def ken(kod, mahal, yon):
        return next(e for e in _kimlik(kod)["parametrik"]["kenarlar"] if e["mahal"] == mahal and e["yon"] == yon and e["en_dis"])
    e = ken("KT03", "Hol", "K")                               # çocuk odası 5 cm kaçık D11 boyunca doğuya devam ediyor
    assert e["durum"] == "kilitli" and "Çocuk Odası" in e["neden"]
    for kod, mahal, yon in (("C8201", "Banyo", "D"), ("C8801", "Banyo", "B"), ("KT01", "Banyo", "B")):
        assert ken(kod, mahal, yon)["durum"] == "oynar", (kod, mahal, yon)
    for kod, mahal, yon in (("C8801L", "Yatak Odası 1", "D"), ("C8801L", "Yatak Odası 2", "D"), ("KT03", "Salon", "K")):
        assert ken(kod, mahal, yon)["durum"] == "kilitli" and "düzey 3" in ken(kod, mahal, yon)["neden"], (kod, mahal, yon)
    e = ken("KT01", "Yatak Odası 1", "K")
    assert e["tur"] == YK.DIS and e["durum"] == "oynar" and e["kesit_bantlari"]


def test_komut_ve_gorsel(tmp_path):
    cikti, png = tmp_path / "k.json", tmp_path / "k.png"
    assert YK.main([str(KOK / "modeller" / "C8801.json"), "--cikti", str(cikti), "--gorsel", str(png), "--set", str(SET)]) == 0
    assert json.loads(cikti.read_text(encoding="utf-8")) == _kimlik("C8801")
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and png.stat().st_size > 20_000
    with pytest.raises(ValueError):
        YK.oku({"bilinmeyen": 1})
