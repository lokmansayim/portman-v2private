"""BK-15 · yeni planın revizyonunda oda ekleme (`plan_islem` `oda_ekle`): yalnız ebeveyn banyosu, yatak odasının köşesinden; sığmazsa oda
bir kenarından büyütülür (ev en az büyüyen yönde). Öteki oda istekleri gerekçesiyle "uygulanamadı". LLM çağrısı yok: `manuel` arka uç
kayıtlı işlem listesini oynatır.

Örnekler (`testler/plan/ornekler/`): `rehber_3arti1_90` bayi rehberindeki konuşmanın ilk planı ("Tek kat çelik, 3+1, 90 m² civarı", kırma;
`plan_uretici.uret`'in birinci adayı, 27.10.2026); `buyume_2arti1_70` banyonun odaya sığmadığı plan (70 m² 2+1 beşik, birinci aday).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_islem as PI  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402

ORNEK = KOK / "testler" / "plan" / "ornekler"
P3 = {"oda_programi": "3+1"}


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


def ekle(**k) -> dict:
    return {"islemler": [{"op": "oda_ekle", "alinti": k.pop("alinti", "Ebeveyn banyosu ekleyelim"), **k}], "uygulanamayan": []}


def mahal(p, ad):
    return next((m for m in p["mahaller"] if m["ad"] == ad), None)


def test_hedef_ornek_rehberdeki_konusma():
    """Rehber Bölüm 3: "Ebeveyn banyosu ekleyelim" → R2. Banyo en büyük yatak odasının köşesinden (oda L), var olan banyonun yanında (ıslak
    hacimler yan yana), vasistası yan cephede (giriş cephesinde değil), kapısı odadan; odanın penceresi yerinde; dış ölçü aynı; fark koddan."""
    p = ornek("rehber_3arti1_90")
    s = PI.duzenle(p, "Ebeveyn banyosu ekleyelim", P3, hazir=ekle(islev="banyo"))
    assert s["durum"] == "gecerli" and s["cagri"] == 0 and not s["uygulanamayan"]
    assert s["fark"] == ["Yatak Odası 3 17,1 → 12,7 m²", "Ebeveyn Banyo eklendi (4,4 m²)", "pencere eklendi: Ebeveyn Banyo sağ 60/40",
                         "kapı eklendi: Ebeveyn Banyo – Yatak Odası 3"]
    q = s["plan"]
    assert q["dis_olcu"] == p["dis_olcu"]
    assert mahal(q, "Ebeveyn Banyo") == {"ad": "Ebeveyn Banyo", "islev": "banyo", "dikdortgenler": [[585, 290, 800, 495]]}
    assert mahal(q, "Yatak Odası 3")["dikdortgenler"] == [[455, 0, 800, 290], [455, 290, 585, 495]]
    assert mahal(q, "Banyo")["dikdortgenler"] == [[585, 495, 800, 705]]                  # yeni banyo y = 495'te var olan banyoya bitişik
    assert {"arasinda": ["Yatak Odası 3", "Ebeveyn Banyo"]} in q["kapilar"]
    assert {"mahal": "Ebeveyn Banyo", "cephe": "D", "olcu": "60x40", "adet": 1} in q["pencereler"]
    # öteki mahaller, kapılar ve pencereler aynen
    assert [m for m in q["mahaller"] if m["ad"] not in ("Yatak Odası 3", "Ebeveyn Banyo")] == \
        [m for m in p["mahaller"] if m["ad"] != "Yatak Odası 3"]
    assert all(k in q["kapilar"] for k in p["kapilar"]) and all(x in q["pencereler"] for x in p["pencereler"])
    # denetçi: oda en küçükleri (net), program, erişim; ebeveyn banyosu yatak odasından (ikinci banyo olduğu için kural dışı değil)
    d = denetle(q, P3)
    assert d["gecerli"] and d["ozet"]["banyo"] == 2 and d["ozet"]["yatak"] == 3
    assert d["ozet"]["odalar_m2"]["Yatak Odası 3"] >= 10.5 and d["ozet"]["odalar_m2"]["Ebeveyn Banyo"] >= 3.8
    assert s["tanim"] is not None


def test_bayinin_soyledigi_yatak_odasi():
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=ekle(islev="banyo", mahal="Yatak Odası 1"))
    assert s["durum"] == "gecerli"
    assert s["fark"] == ["Yatak Odası 1 16,8 → 12,4 m²", "Ebeveyn Banyo eklendi (4,4 m²)", "pencere eklendi: Ebeveyn Banyo sol 60/40",
                         "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]
    assert mahal(s["plan"], "Yatak Odası 3") == mahal(ornek("rehber_3arti1_90"), "Yatak Odası 3")


def test_ikinci_ebeveyn_banyosu_ayri_adla():
    h = {"islemler": [{"op": "oda_ekle", "islev": "banyo", "alinti": "a"},
                      {"op": "oda_ekle", "islev": "banyo", "mahal": "Yatak Odası 1", "alinti": "b"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli"
    assert mahal(s["plan"], "Ebeveyn Banyo 2") and {"arasinda": ["Yatak Odası 1", "Ebeveyn Banyo 2"]} in s["plan"]["kapilar"]


def test_sigmayan_odada_ev_en_az_buyuyen_yonde_buyur():
    """O2 (önerilen seçenek, CIO onayı 27.10): oda köşesine banyo sığmıyor (oda 10,5 m²'nin altına düşer) → oda bir kenarından büyütülür;
    yeni dış ölçü bayiye fark olarak yazılır."""
    p = ornek("buyume_2arti1_70")
    assert PI._banyo_kes(p, "Yatak Odası 1", "Ebeveyn Banyo") is None
    s = PI.duzenle(p, "x", {"oda_programi": "2+1"}, hazir=ekle(islev="banyo"))
    assert s["durum"] == "gecerli"
    assert s["fark"] == ["dış ölçü 700×1000 → 700×1150 cm", "Yatak Odası 1 11,9 → 12,8 m²", "Yatak Odası 2 11,9 → 17,1 m²",
                         "Ebeveyn Banyo eklendi (4,4 m²)", "pencere eklendi: Ebeveyn Banyo sol 60/40",
                         "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]
    assert denetle(s["plan"], {"oda_programi": "2+1"})["gecerli"]
    # en az büyüme: daha küçük bir büyümeyle (her yön, 100–250 cm) denetçiden geçen yerleşim yok
    brut = lambda x: x["dis_olcu"]["en"] * x["dis_olcu"]["boy"]       # noqa: E731
    secilen = brut(s["plan"]) - brut(p)
    for yon, cm in PI.BUYUME:
        g, _ = PI._oda_kenari(p, "Yatak Odası 1", yon, cm)
        if g is not None and brut(g) - brut(p) < secilen:
            assert PI._banyo_kes(g, "Yatak Odası 1", "Ebeveyn Banyo") is None, (yon, cm)


def test_belirlenimci():
    a = PI.duzenle(ornek("buyume_2arti1_70"), "x", {"oda_programi": "2+1"}, hazir=ekle(islev="banyo"))
    b = PI.duzenle(ornek("buyume_2arti1_70"), "x", {"oda_programi": "2+1"}, hazir=ekle(islev="banyo"))
    assert json.dumps(a["plan"], sort_keys=True) == json.dumps(b["plan"], sort_keys=True) and a["fark"] == b["fark"]


@pytest.mark.parametrize("islem, gerekce", [
    ({"islev": "yatak_odasi", "alinti": "Bir yatak odası daha ekleyelim"},
     "Bir yatak odası daha ekleyelim: yatak odası ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "mutfak", "alinti": "ayrı mutfak olsun"},
     "ayrı mutfak olsun: mutfak ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "depo", "alinti": "kiler ekleyelim"},
     "kiler ekleyelim: depo ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "banyo", "mahal": "Hol", "alinti": "holden ikinci banyo"},
     "holden ikinci banyo: banyo yalnız bir yatak odasının içinden eklenebiliyor (Hol yatak odası değil)"),
    ({"islev": "banyo", "mahal": "Çocuk Odası", "alinti": "çocuk odasına banyo"}, "çocuk odasına banyo: 'Çocuk Odası' adlı mahal yok"),
    ({"alinti": "bir oda daha"}, "bir oda daha: yeni oda ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
])
def test_baska_oda_uygulanamaz_plan_aynen(islem, gerekce):
    """O3: yatak odası, mutfak, kiler, ortak banyo eklenmez; istek bayinin sözü ve gerekçesiyle, plan aynen geçerli."""
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=ekle(**islem))
    assert s["durum"] == "uygulanamadi" and s["plan"] is None and s["uygulanamayan"] == [gerekce]


def test_oda_ekleme_oteki_islemlerle_birlikte():
    h = {"islemler": [{"op": "oda_ekle", "islev": "banyo", "alinti": "a"},
                      {"op": "pencere_ekle", "mahal": "Yatak Odası 1", "cephe": "K", "olcu": "120x120", "alinti": "b"},
                      {"op": "oda_ekle", "islev": "yatak_odasi", "alinti": "bir yatak odası daha"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli" and "Ebeveyn Banyo eklendi (4,4 m²)" in s["fark"] and "pencere eklendi: Yatak Odası 1 arka 120/120" in s["fark"]
    assert len(s["uygulanamayan"]) == 1 and s["uygulanamayan"][0].startswith("bir yatak odası daha: yatak odası ekleme")


def test_yatak_odasi_yoksa_gerekceli():
    p = ornek("rehber_3arti1_90")
    for m in p["mahaller"]:
        if m["islev"] == "yatak_odasi":
            m["islev"] = "depo"
    q, olmayan = PI.uygula(p, ekle(islev="banyo")["islemler"])
    assert q == p and olmayan == ["Ebeveyn banyosu ekleyelim: planda yatak odası yok"]


def test_islem_semasi_ve_istem():
    """LLM'e giden araç şeması `oda_ekle`'yi ve işlevleri tanır; istem yalnız ebeveyn banyosunun uygulandığını söyler, koordinat istemez."""
    sema = PI.IslemListesi.model_json_schema()
    islem = sema["$defs"]["Islem"]["properties"]
    assert "oda_ekle" in islem["op"]["enum"]
    assert "banyo" in json.dumps(islem["islev"]) and "yatak_odasi" in json.dumps(islem["islev"])
    assert "oda_ekle (islev, mahal)" in PI.PROMPT and "ebeveyn banyosu" in PI.PROMPT
    assert PI.Islem.model_validate({"op": "oda_ekle", "islev": "banyo"}).islev == "banyo"
