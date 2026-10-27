"""İE-20 PR-1 · `beyin/gorsel_okuma`: bayi çiziminin kayıtlı okumasından kod denetimi, İş Emri'ne ve çelik plana çeviri, bayiye giden
metin ve okunan yerleşimin görseli. LLM yok (kayıtlı okuma, manuel arka uç), Postgres yok.

Kayıtlı okumalar elle yazıldı (`veri/`): TK-01 (teklif çalışmasının bayi çizimi; çizimin kendisi depoya girmez), basit 2+1 prefabrik ve
2+1 çelik. Gerçek bir LLM okuması ücretli denemedir (Lokman'ın onayıyla).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import gorsel_okuma as GO  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def yukle(ad: str) -> dict:
    return {a: v for a, v in json.loads((VERI / ad).read_text(encoding="utf-8")).items() if not a.startswith("_")}


TK01 = yukle("TK01_okuma.json")
BASIT = yukle("BASIT_2p1_okuma.json")
CELIK = yukle("CELIK_2p1_okuma.json")
TK01_BEKLENEN = yukle("TK01_beklenen.json")


# ─── çizimi döndür: aynı ev, giriş çizimin başka kenarında (okuma çizimin kendi çerçevesinde yazılır) ───
def _ters(x: float, y: float, W: float, H: float, giris: str) -> tuple[float, float]:
    """Kanonik (giriş altta, W × H) → giriş `giris` kenarında duran çizimin çerçevesi (`GO._nokta`nın tersi)."""
    if giris == "alt":
        return x, y
    if giris == "ust":
        return W - x, H - y
    if giris == "sol":
        return H - y, x
    return y, W - x


def dondur(okuma: dict, giris: str) -> dict:
    """Giriş altta okunmuş çizimi, girişi `giris` kenarında duran çizimin okumasına çevirir (zincir sırası, kenarlar, verandalar dahil)."""
    assert okuma["giris_kenari"] == "alt"
    o = copy.deepcopy(okuma)
    W, H = float(okuma["dis_olcu"]["yatay_cm"]), float(okuma["dis_olcu"]["dusey_cm"])
    Wd, Hd = (W, H) if giris in ("alt", "ust") else (H, W)
    cephe = GO.KENAR_CEPHE["alt"]
    yeni_kenar = {k: next(k2 for k2, c in GO.KENAR_CEPHE[giris].items() if c == cephe[k]) for k in GO.KENARLAR}

    def dortgen(r):
        x0, y0 = _ters(r[0], r[1], W, H, giris)
        x1, y1 = _ters(r[2], r[3], W, H, giris)
        return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    o["giris_kenari"] = giris
    o["dis_olcu"] = {"yatay_cm": Wd, "dusey_cm": Hd}
    for x in o["odalar"]:
        x["dikdortgenler"] = [dortgen(r) for r in x["dikdortgenler"]]
    for p in o["pencereler"]:
        p["kenar"] = yeni_kenar[p["kenar"]]
    for k in o["kapilar"]:
        if k.get("kenar"):
            k["kenar"] = yeni_kenar[k["kenar"]]
    for z in o["zincirler"]:
        noktalar, t = [0.0], 0.0
        for parca in z["olculer_cm"]:
            t += parca
            noktalar.append(t)
        yatay = z["kenar"] in ("ust", "alt")
        yeni = []
        for n in noktalar:
            px, py = _ters(n, 0, W, H, giris) if yatay else _ters(0, n, W, H, giris)
            yeni.append(px if yeni_kenar[z["kenar"]] in ("ust", "alt") else py)
        yeni.sort()
        z["olculer_cm"] = [round(b - a, 6) for a, b in zip(yeni, yeni[1:])]
        z["kenar"] = yeni_kenar[z["kenar"]]
    for v in o["verandalar"]:
        d = v["derinlik_cm"]
        r = {"ust": [v["bas_cm"], -d, v["bit_cm"], 0], "alt": [v["bas_cm"], H, v["bit_cm"], H + d],
             "sol": [-d, v["bas_cm"], 0, v["bit_cm"]], "sag": [W, v["bas_cm"], W + d, v["bit_cm"]]}[v["kenar"]]
        x0, y0, x1, y1 = dortgen(r)
        v["kenar"] = yeni_kenar[v["kenar"]]
        v["bas_cm"], v["bit_cm"] = (x0, x1) if v["kenar"] in ("ust", "alt") else (y0, y1)
    return o


def geometri(ie: dict) -> dict:
    return {a: ie.get(a) for a in ("mahaller", "acikliklar", "verandalar", "cati")}


# ─── G1/G4 hedef örneği: TK-01 ───
def test_tk01_okumasi_teklif_r04_geometrisini_verir():
    """Kabul: TK-01'in okumasından çıkan İş Emri, teklif çalışmasında elle yazılan İş Emri'yle (r04) geometri olarak aynı."""
    d = GO.denetle(TK01, bk14=True)
    assert d["sorular"] == [] and d["cizilemez"] == []
    ie = d["cevrim"]["is_emri"]
    assert geometri(ie) == geometri(TK01_BEKLENEN)
    beklenen_yapi = {**TK01_BEKLENEN["yapi"], "referans_model": "CIZIM"}
    assert ie["yapi"] == beklenen_yapi
    assert ie["is_emri_no"] == "" and ie["revizyon"] == 0          # numara ve künye `karar._is_emri_uret`te


def test_tk01_bk14_yoksa_cizilmez():
    """BK-14 (PR #50) birleşmeden gövdeden taşan veranda ve dört kollu iç duvar birleşimi çizilemez (main Motor'u + birleşimde doğrulamadan
    düşer): sapmalı plan yerine bayiye ve Patron'a söylenir."""
    d = GO.denetle(TK01, bk14=False)
    assert d["cevrim"] is None and d["sorular"] == []
    assert d["cizilemez"][0] == "gövdenin dışına taşan veranda"
    assert d["cizilemez"][1].startswith("dört kollu duvar birleşimi (") and len(d["cizilemez"]) == 2
    m, ek = GO.cizilemez_metni(TK01, d)
    assert "otomatik çizemiyorum" in m and "veranda" in m and len(m) <= 1000 and ek is None
    yalniz = {**TK01, "verandalar": []}
    assert GO.denetle(yalniz, bk14=False)["cizilemez"] == [d["cizilemez"][1]]


def test_tk01_teyit_metni():
    d = GO.denetle(TK01, bk14=True)
    m, ek = GO.teyit_metni(TK01, d)
    assert len(m) <= 1000 and ek is None
    for parca in ("Tek katlı prefabrik, gövde 8,98 × 8,88 m, duvar 2,50 m, beşik çatı.",
                  "salon 19,5 m²", "mutfak 9,5 m²", "3 yatak odası (11,5 / 13 / 9,5 m²)", "e. banyo 3 m²", "banyo 5 m²",
                  "Veranda: önde 3,86 × 1,81 m, arkada 2,61 × 1,30 m.", "8 pencere, giriş kapısı önde.",
                  "Yapı tipi yazmıyordu, prefabrik aldım.", "banyoların derinliği 256 cm", "Okuduğum yerleşim görselde. Doğru mu?"):
        assert parca in m, parca
    assert "Okuduğum yerleşim görselde" not in GO.teyit_metni(TK01, d, gorsel_var=False)[0]


@pytest.mark.parametrize("giris", ["ust", "sol", "sag"])
def test_dondurulmus_cizim_ayni_is_emrini_verir(giris):
    """Çizimin yönü (giriş üstte, solda, sağda) planı değiştirmez: kanonik çerçeve giriş altta."""
    o = dondur(TK01, giris)
    assert o != TK01
    d = GO.denetle(o, bk14=True)
    assert d["sorular"] == [] and d["cizilemez"] == [], (d["sorular"], d["cizilemez"])
    a = d["cevrim"]["is_emri"]
    b = GO.denetle(TK01, bk14=True)["cevrim"]["is_emri"]
    assert geometri(a) == geometri(b) and a["yapi"] == b["yapi"]


# ─── kod okunanı düzeltmez: tutmayan ölçü bayiye sorulur ───
def test_tutmayan_zincir_sorulur():
    o = copy.deepcopy(TK01)
    z = next(z for z in o["zincirler"] if z["kenar"] == "ust")
    z["olculer_cm"][0] += 20
    d = GO.denetle(o, bk14=True)
    assert d["cevrim"] is None
    assert any(s.startswith("Üstteki ölçü zinciri") and "hangisi doğru?" in s for s in d["sorular"]), d["sorular"]
    m, _ = GO.soru_metni(o, d)
    assert "Şunlardan emin olamadım" in m and "Doğrusunu yazar mısınız?" in m and len(m) <= 1024


def test_kucuk_zincir_farki_not_olur():
    d = GO.denetle(TK01, bk14=True)
    assert any("küçük farkla tutuyor" in n for n in d["notlar"])
    assert d["zincir_tutuyor"] is True


def test_yazili_alan_ile_olcu_tutmazsa_sorulur():
    o = copy.deepcopy(BASIT)
    next(x for x in o["odalar"] if x["ad"] == "SALON")["alan_m2"] = 25
    d = GO.denetle(o)
    assert d["cevrim"] is None
    assert any(s.startswith("Salon için 25 m² yazıyor") for s in d["sorular"]), d["sorular"]


def test_izgaraya_oturmayan_sinir_sorulur():
    """Oda sınırı yarım pano aksına `pano_cm`den (10 cm) uzaksa sessizce kaydırılmaz."""
    o = copy.deepcopy(BASIT)
    for x in o["odalar"]:
        x["alan_m2"] = None                                     # yalnız ızgara denetimi
        for r in x["dikdortgenler"]:
            r[:] = [v + 30 if v == 387 else v for v in r]
    for z in o["zincirler"]:
        if z["kenar"] == "ust":
            z["olculer_cm"] = [417, 96, 260]
    d = GO.denetle(o)
    assert d["cevrim"] is None
    assert any("pano ızgarasına oturmuyor" in s and "Öyle çizebilir miyim?" in s for s in d["sorular"]), d["sorular"]


def test_bos_kalan_bolum_ve_cakisma_sorulur():
    o = copy.deepcopy(BASIT)
    o["odalar"] = [x for x in o["odalar"] if x["ad"] != "MUTFAK"]
    o["kapilar"] = [k for k in o["kapilar"] if "MUTFAK" not in k["arasinda"]]
    o["pencereler"] = [p for p in o["pencereler"] if p["oda"] != "MUTFAK"]
    d = GO.denetle(o)
    assert any("hiçbir odaya ait görünmüyor" in s for s in d["sorular"]), d["sorular"]
    o2 = copy.deepcopy(BASIT)
    next(x for x in o2["odalar"] if x["ad"] == "SALON")["dikdortgenler"] = [[0, 382, 513, 888]]
    next(x for x in o2["odalar"] if x["ad"] == "SALON")["alan_m2"] = None
    d2 = GO.denetle(o2)
    assert any("üst üste biniyor" in s for s in d2["sorular"]), d2["sorular"]


def test_emin_olunamayan_ve_giris_kapisi_sorulur():
    o = copy.deepcopy(BASIT)
    o["emin_olunamayanlar"] = ["Mutfak penceresinin ölçüsü okunmuyor."]
    o["kapilar"] = [k for k in o["kapilar"] if "DIŞ" not in k["arasinda"]]
    d = GO.denetle(o)
    assert "Mutfak penceresinin ölçüsü okunmuyor." in d["sorular"]
    assert any("Giriş kapısını çizimde göremedim" in s for s in d["sorular"])


def test_odaya_degmeyen_pencere_ve_komsu_olmayan_kapi_sorulur():
    o = copy.deepcopy(BASIT)
    o["pencereler"].append({"oda": "HOL", "kenar": "sol", "olcu": "120x120", "adet": 1})
    o["kapilar"].append({"arasinda": ["SALON", "YATAK ODASI 2"]})
    d = GO.denetle(o)
    assert any("Hol penceresini solda okudum ama oda o cepheye değmiyor" in s for s in d["sorular"]), d["sorular"]
    assert any("Salon ile Yatak Odası 2 arasında kapı okudum ama iki oda yan yana değil" in s for s in d["sorular"]), d["sorular"]


# ─── Motor'un çizemediği: okunur, bayiye "çizemiyorum", Patron'a ───
def test_iki_kat_ve_kirma_cati_cizilemez():
    o = copy.deepcopy(BASIT); o["kat_sayisi"] = 2
    assert any("2 katlı plan" in c for c in GO.denetle(o)["cizilemez"])
    o = copy.deepcopy(BASIT); o["cati"] = {"tip": "kirma", "mahya": None}
    d = GO.denetle(o)
    assert d["cevrim"] is None and any("kırma çatı" in c for c in d["cizilemez"])


def test_desteklenmeyen_duvar_yuksekligi_sorulur():
    o = copy.deepcopy(BASIT); o["duvar_yuksekligi_cm"] = 260
    d = GO.denetle(o)
    assert any("2,50 / 2,80 / 3,00" in s for s in d["sorular"])


# ─── G6: fotoğraf tek başına yetmez ───
def test_fotograf_plan_degil():
    d = GO.denetle({"tur": "fotograf", "ozet": "tek katlı ev fotoğrafı"})
    assert d["plan_mi"] is False and d["cevrim"] is None and d["sorular"] == []


# ─── varsayılanlar bayiye yazılır ───
def test_varsayilanlar_not_olur():
    o = copy.deepcopy(BASIT)
    o["yapi_turu"] = None; o["duvar_yuksekligi_cm"] = None; o["cati"] = {"tip": None, "mahya": None}
    next(p for p in o["pencereler"] if p["oda"] == "BANYO")["olcu"] = None
    d = GO.denetle(o)
    assert d["sorular"] == [] and d["cizilemez"] == []
    for n in ("yapı tipi yazmıyordu, prefabrik aldım", "duvar yüksekliği yazmıyordu, 2,50 m aldım", "çatı tipi görünmüyordu, beşik aldım",
              "ölçüsü yazmayan pencereler: 60x40 (Banyo)"):
        assert n in d["notlar"], (n, d["notlar"])
    ie = d["cevrim"]["is_emri"]
    assert ie["yapi"]["duvar_yuksekligi_cm"] == 250
    assert any(a["tur"] == "pencere" and a["mahal"] == "BANYO" and a["olcu"] == "60x40" for a in ie["acikliklar"])
    assert any("Duvar yüksekliği yazmıyordu" in v for v in ie["varsayimlar"])


# ─── G4: bugünkü Pano Motor'u okunan basit planı çizer ───
def test_basit_okuma_motorda_cizilir(tmp_path):
    from motor import dxf_out
    d = GO.denetle(BASIT)
    assert d["sorular"] == [] and d["cizilemez"] == [], (d["sorular"], d["cizilemez"])
    ie = json.loads(json.dumps(d["cevrim"]["is_emri"]))
    ie.update(is_emri_no="PM-TEST-CIZIM", revizyon=1, talep={"bayi_kodu": "TST", "kaynak": GO.KAYNAK})
    sonuc = dxf_out.uret(ie, tmp_path / "plan")
    v = json.loads((tmp_path / "plan" / "validation.json").read_text(encoding="utf-8"))
    assert v["passed"] is True, v.get("errors")
    assert (tmp_path / "plan" / sonuc["pdf"]).stat().st_size > 10_000


# ─── G5: çelik okuma İE-14 plan denetçisinden geçer ───
def test_celik_okuma_plan_denetciden_gecer():
    d = GO.denetle(CELIK)
    assert d["yapi_turu"] == "celik" and d["sorular"] == [] and d["cizilemez"] == []
    plan = d["cevrim"]["plan"]
    assert plan["dis_olcu"] == {"en": 1100, "boy": 850}
    assert {m["islev"] for m in plan["mahaller"]} == {"yatak_odasi", "banyo", "hol", "salon", "mutfak"}
    banyo = next(m for m in plan["mahaller"] if m["islev"] == "banyo")
    assert banyo["dikdortgenler"] == [[400, 550, 640, 850]]            # köken güneybatı: arka (çizimin üstü) kuzey
    assert d["cevrim"]["tanim"]
    assert "Tek katlı çelik, gövde 11,00 × 8,50 m" in GO.teyit_metni(CELIK, d)[0]


def test_celik_kurala_uymayan_oda_cizilemez():
    o = copy.deepcopy(BASIT); o["yapi_turu"] = "celik"
    d = GO.denetle(o)
    assert d["cevrim"] is None
    assert any(c.startswith("çelik plan kuralı: Banyo") for c in d["cizilemez"]), d["cizilemez"]


# ─── düzeltme ───
def test_degisenler():
    yeni = copy.deepcopy(BASIT)
    next(x for x in yeni["odalar"] if x["ad"] == "SALON")["alan_m2"] = 20
    yeni["verandalar"] = [{"kenar": "alt", "bas_cm": 0, "bit_cm": 387, "derinlik_cm": 150}]
    yeni["pencereler"][0]["olcu"] = "120x180"
    f = GO.degisenler(BASIT, yeni)
    assert "Salon 19 → 20 m²" in f and "veranda değişti" in f and "pencereler değişti" in f
    assert GO.degisenler(BASIT, copy.deepcopy(BASIT)) == []


def test_oku_ve_duzelt_kayitli_okumayla():
    """Manuel arka uç: kayıtlı okuma döner, LLM çağrılmaz, dosya bloğu kurulmaz; düzeltmede `okuma` boşsa hata (istisna yok)."""
    s = GO.oku(VERI / "yok.png", "image/png", "ekte plan var", hazir=BASIT)
    assert s["durum"] == "tamam" and s["cagri"] == 0 and s["okuma"]["dis_olcu"] == {"yatay_cm": 773.0, "dusey_cm": 888.0}
    yeni = copy.deepcopy(BASIT); yeni["duvar_yuksekligi_cm"] = 280
    dz = GO.duzelt(BASIT, "duvar 2,80 olsun", hazir={"niyet": "duzeltme", "okuma": yeni, "degisenler": ["duvar 2,80 m"]})
    assert dz["durum"] == "tamam" and dz["niyet"] == "duzeltme" and dz["okuma"]["duvar_yuksekligi_cm"] == 280
    assert GO.duzelt(BASIT, "x", hazir={"niyet": "duzeltme", "okuma": None})["durum"] == "hata"
    assert GO.duzelt(BASIT, "vazgeçtim", hazir={"niyet": "iptal"})["niyet"] == "iptal"
    assert GO.oku(VERI / "yok.png", "image/png", hazir={"tur": "plan", "odalar": "bozuk"})["durum"] == "hata"


def test_dosya_blogu_ve_okunabilirlik(tmp_path):
    p = tmp_path / "a.pdf"; p.write_bytes(b"%PDF-1.4 deneme")
    b = GO.dosya_blogu(p, "application/pdf")
    assert b["type"] == "document" and b["source"]["media_type"] == "application/pdf"
    assert GO.dosya_blogu(p, "image/png")["type"] == "image"
    assert GO.okunabilir_mi("image/jpeg", 1000) is None and GO.okunabilir_mi("application/pdf", 1000) is None
    assert "türünü okuyamıyorum" in GO.okunabilir_mi("audio/ogg", 1000)
    assert "büyük" in GO.okunabilir_mi("image/png", GO.EN_BUYUK_BAYT + 1)


def test_numara_llm_e_maskeli_gider(monkeypatch):
    gonderilen = {}

    def sahte(sistem, mesajlar, *a, **k):
        gonderilen["metin"] = json.dumps(mesajlar, ensure_ascii=False)
        return BASIT, {}
    monkeypatch.setattr(GO.llm, "arac_cagir", sahte)
    GO.oku(VERI / "yok.png", "image/png", "beni 0532 111 22 33'ten arayın", hazir=BASIT)
    assert "111 22 33" not in gonderilen["metin"]


# ─── okunan yerleşimin görseli ───
@pytest.mark.parametrize("okuma", [TK01, BASIT, CELIK], ids=["TK01", "BASIT", "CELIK"])
def test_yerlesim_gorseli(tmp_path, okuma):
    d = GO.denetle(okuma, bk14=True)
    yol = GO.yerlesim_gorseli(okuma, d, tmp_path / "g" / "okunan_yerlesim.png")
    assert yol.is_file() and yol.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and yol.stat().st_size > 20_000
    assert GO.yerlesim_gorseli(okuma, d, tmp_path / "h.png").read_bytes() == yol.read_bytes()      # belirlenimci


# ─── geometri hakemi (27 Ekim): ızgaranın ucu, dış ölçünün kaynağı, varsayımların bayiye ulaşması ───
def iki_oda(W: float, H: float, sinir: float) -> dict:
    return {"tur": "plan", "yapi_turu": "prefabrik", "giris_kenari": "alt", "dis_olcu": {"yatay_cm": W, "dusey_cm": H},
            "odalar": [{"ad": "SALON", "islev": "salon", "dikdortgenler": [[0, 0, sinir, H]]},
                       {"ad": "MUTFAK", "islev": "mutfak", "dikdortgenler": [[sinir, 0, W, H]]}],
            "kapilar": [{"arasinda": ["DIŞ", "SALON"], "kenar": "alt"}, {"arasinda": ["SALON", "MUTFAK"]}],
            "pencereler": [{"oda": "SALON", "kenar": "sol", "olcu": "120x120"}, {"oda": "MUTFAK", "kenar": "sag", "olcu": "120x120"}],
            "cati": {"tip": "besik", "mahya": "giristen_arkaya"}, "duvar_yuksekligi_cm": 250}


def test_pano_izgarasinin_kisa_ucu_sorulur():
    """9,00 m: yarım adımlı ızgarada sonda 1,5 cm'lik pano kalır, Motor çizemez → teyit yerine soru (en yakın iki ölçüyle)."""
    d = GO.denetle(iki_oda(900, 763, 386.5))
    assert d["cevrim"] is None
    assert any("ön cephesi 9,00 m" in s and "sonda 1,5 cm'lik pano" in s and "8,98 m ve 9,61 m" in s for s in d["sorular"]), d["sorular"]
    assert GO.denetle(iki_oda(898, 763, 386.5))["cevrim"] is not None
    d = GO.denetle(iki_oda(898, 770, 386.5))
    assert any("yan cephesi 7,70 m" in s for s in d["sorular"]), d["sorular"]


def test_dis_duvara_cok_yakin_sinir_sorulur():
    """Tam adımlı ızgarada son yarım aks dış duvara 2,75 cm: oraya oturan oda sınırı Motor'un çizemeyeceği pano bırakır."""
    d = GO.denetle(iki_oda(713, 763, 692))
    assert d["cevrim"] is None
    assert any("Salon sınırı (692 cm) dış duvara 2,8 cm kalıyor" in s for s in d["sorular"]), d["sorular"]


def test_dis_olcu_yazmiyorsa_zincirin_yazili_toplami():
    o = copy.deepcopy(TK01)
    o["dis_olcu"] = {"yatay_cm": None, "dusey_cm": None}
    d = GO.denetle(o, bk14=True)
    assert d["kanonik"]["W"] == 898 and d["kanonik"]["H"] == 888, (d["kanonik"]["W"], d["kanonik"]["H"])
    assert "dış ölçü yazmıyordu: eni ölçü zincirinden, boyu odaların ölçülerinden alındı" in d["notlar"]   # yan zincirler verandayı kapsıyor
    o["zincirler"] = [{**z, "kapsam": "govde", "olculer_cm": [382, 506], "toplam_cm": 888} if z["kenar"] == "sol" else z for z in o["zincirler"]]
    assert "dış ölçü yazmıyordu: ölçü zincirlerinden alındı" in GO.denetle(o, bk14=True)["notlar"]
    assert geometri(d["cevrim"]["is_emri"]) == geometri(GO.denetle(TK01, bk14=True)["cevrim"]["is_emri"])


def test_sigmayan_varsayimlar_ayri_mesajda_gider():
    o = copy.deepcopy(TK01)
    for p in o["pencereler"]:
        p["olcu"] = None
    o["tahminler"] += [f"{i}. tahmin: bu ölçü çizimde yazmıyordu, komşu odanın ölçüsünden ve çizimin oranından aldım" for i in range(1, 5)]
    d = GO.denetle(o, bk14=True)
    m, ek = GO.teyit_metni(o, d)
    assert ek is not None and len(m) <= 1000 and "Varsaydıklarımı bir önceki mesajda yazdım." in m and m.endswith("yazmanız yeterli.")
    for n in d["notlar"]:
        assert GO._bas_buyuk(n) in ek, n
    for t in d["tahminler"]:
        assert t in ek, t
    assert "Ölçüsü yazmayan pencereler: 120x120 (Yatak Odası 1, Yatak Odası 2, Yatak Odası 3, Salon 2, Mutfak), 60x40 (E. Banyo, Banyo)." in ek
    assert "4. tahmin" in ek


def test_izgaraya_oturtunca_alan_cok_degisirse_sorulur_azsa_yazilir():
    o = copy.deepcopy(BASIT)
    for x in o["odalar"]:
        x["alan_m2"] = None
        for r in x["dikdortgenler"]:
            r[:] = [395 if v == 387 else 503 if v == 513 else v for v in r]
    next(z for z in o["zincirler"] if z["kenar"] == "ust")["olculer_cm"] = [395, 108, 270]
    d = GO.denetle(o)
    assert d["cevrim"] is None
    assert any(s.startswith("Hol pano ızgarasına oturtunca 6,8 m² yerine 7,9 m² oluyor") for s in d["sorular"]), d["sorular"]
    d = GO.denetle(BASIT)
    assert "oda sınırlarını pano ızgarasına oturttum (en çok 1 cm kayma)" in d["notlar"], d["notlar"]


def test_mahya_egim_sacak_ve_kapi_varsayimlari_yazilir():
    o = copy.deepcopy(BASIT)
    o["cati"] = {"tip": "besik", "mahya": None, "egim_yuzde": 25, "sacak_cm": 50}
    o["kapilar"][0]["genislik_cm"] = 100
    d = GO.denetle(o)
    assert d["sorular"] == [] and d["cizilemez"] == []
    for n in ("mahya yönü görünmüyordu, girişten arkaya aldım", "çatı eğimi çizimdeki gibi %25 (standardımız %33)",
              "saçak çizimdeki gibi 50 cm (standardımız 30 cm)", "kapılar prefabrik standardında: giriş 90, iç 82 cm (çizimde 100 cm yazıyordu)"):
        assert n in d["notlar"], (n, d["notlar"])
    c = d["cevrim"]["is_emri"]["cati"]
    assert (c["egim_yuzde"], c["sacak_cm"], c["makas_ekseni"]) == (25, 50, "x")


def test_celik_katalog_disi_pencere_sorulur_yildiz_okunur():
    o = copy.deepcopy(CELIK)
    o["pencereler"][3]["olcu"] = "125x125"
    o["pencereler"][4]["olcu"] = "120*180"
    d = GO.denetle(o)
    assert d["cevrim"] is None
    assert [s for s in d["sorular"] if "125x125" in s and "Hangisi olsun?" in s], d["sorular"]
    o["pencereler"][3]["olcu"] = "120x180"
    d = GO.denetle(o)
    assert d["cevrim"] and [p["olcu"] for p in d["cevrim"]["plan"]["pencereler"] if p["mahal"] == "Salon"] == ["120x180", "120x180"]
