"""BK-72 (D-150; Lokman, kart 23 Kasım 2026 12:40:09 UTC "Dördü de, sırayla"): okuyucunun ölçü kuralları.
Kural 1: ızgaranın sonunda 20 cm'den kısa pano kalan dış ölçü sorulmaz, kısa uç kesilir (TK-04 kroki 9,00 → onaylı 8,885; TK-09 6,50 → 6,475).
Kural 4: zincir ile toplamın eşik içindeki farkı sorulmaz; tek parçalı toplamsız ölçü zincir sayılmaz; aynı soru bir kez gider."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
if str(KOK / "kanal") not in sys.path:
    sys.path.insert(0, str(KOK / "kanal"))
from beyin import gorsel_okuma as GO  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def _okuma(ad: str) -> dict:
    return json.loads((VERI / f"BK70_{ad}_okuma.json").read_text(encoding="utf-8"))


def test_kural1_onayli_planlarin_olcusu():
    W, H, notlar = GO.izgaraya_oturt(900, 1000, "y")
    assert (W, H) == (888.5, 1000)
    assert "9,00 m yerine 8,885 m" in notlar[0]
    W, H, _ = GO.izgaraya_oturt(650, 700, "x")
    assert W == 647.5


def test_kural1_oturan_olcu_degismez():
    assert GO.izgaraya_oturt(888.5, 898.5, "x") is None or GO._izgara(888.5, 898.5, "x")[4]
    for W, H, m in ((800, 1088, "x"), (950, 640, "y")):
        if not GO._izgara(W, H, m)[4]:
            assert GO.izgaraya_oturt(W, H, m) is None


def test_kural1_kisa_uc_sorusu_bayiye_gitmez():
    o = _okuma("TK09")
    den = GO.denetle({**o, "emin_olunamayanlar": []})
    assert not any("pano kalıyor" in s for s in den["sorular"])


def test_kural4_kucuk_zincir_farki_sorusu_dusur():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "ust", "olculer_cm": [261, 126, 188, 324], "toplam_cm": 898, "kapsam": "govde"}],
         "emin_olunamayanlar": ["Üst ölçü zinciri 261+126+188+324=899 ediyor, toplam 898 yazıyor; hangi parça 1 cm eksik?",
                                "Salon penceresi hangi duvarda?"]}  # BK-80: pencere ölçüsü sorusu artık sorulmaz (D-155)
    den = GO.denetle(o)
    assert not any("899" in s for s in den["sorular"])
    assert "Salon penceresi hangi duvarda?" in den["sorular"]
    assert any("küçük farkla" in n for n in den["notlar"])


def test_kural4_buyuk_zincir_farki_sorulur():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "ust", "olculer_cm": [261, 126, 188, 330], "toplam_cm": 898, "kapsam": "govde"}],
         "emin_olunamayanlar": []}
    assert any("ölçü zinciri" in s for s in GO.denetle(o)["sorular"])


def test_kural4_tek_parcali_olcu_zincir_sayilmaz():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "sol", "olculer_cm": [624.5], "kapsam": "govde"}], "emin_olunamayanlar": []}
    assert not any("ölçü zinciri" in s for s in GO.denetle(o)["sorular"])


def test_ayni_soru_bir_kez():
    o = _okuma("TK01")
    o = {**o, "emin_olunamayanlar": ["Banyo penceresi hangi duvarda?", "Banyo penceresi hangi duvarda?"]}   # BK-80: ölçü sorusu sorulmaz
    den = GO.denetle(o)
    assert den["sorular"].count("Banyo penceresi hangi duvarda?") == 1


def _yerler(ie: dict) -> dict:
    import copy
    from motor import geometry as G
    plan = G.kur(copy.deepcopy(ie))
    return {(a["tur"], a["mahal"] or "/".join(a["arasi"] or ())): c for a, c, yon in GO._aciklik_merkezleri(plan) if yon == "x"
            and (a["tur"] == "dis_kapi" or a["mahal"] == "SALON")}


def test_kural2_tek_yerlesim_yan_panoya_alinir():
    """76 m²: salonun öndeki 180'lik penceresine yanında tam pano kalmıyordu; Motor'un kurduğu iki yerleşim aynı yeri veriyor → plan, not."""
    den = GO.denetle({**_okuma("TK08"), "emin_olunamayanlar": []})
    assert den["cevrim"] is not None, den["sorular"]
    assert any("panoya sığmadığı için bir yan panoya alındı" in n for n in den["notlar"])
    assert all("_konum_cm" not in a for a in den["cevrim"]["is_emri"]["acikliklar"])


def test_kural2_okunan_yere_en_yakin_yerlesim():
    """45 m²: verandaya bakan salon duvarında kapı ve pencere aynı panoya düşüyor. Yerleri okunmadıysa soru (K21); okunduysa kod, Motor'un
    kurduğu yerleşimlerden okunan yerlere en yakınını seçer (onaylı plan: kapı solda, pencere sağda)."""
    o = {**_okuma("TK09"), "emin_olunamayanlar": []}
    assert GO.denetle(o)["cevrim"] is None
    o["kapilar"] = [k | ({"konum_cm": 330} if k["arasinda"][0] == "DIŞ" else {}) for k in o["kapilar"]]
    o["pencereler"] = [p | ({"konum_cm": 480} if p["oda"] == "SALON" and p["kenar"] == "alt" else {}) for p in o["pencereler"]]
    den = GO.denetle(o)
    assert den["cevrim"] is not None, den["sorular"]
    y = _yerler(den["cevrim"]["is_emri"])
    kapi = next(c for (t, ad), c in y.items() if t == "dis_kapi")
    pencere = next(c for (t, ad), c in y.items() if t == "pencere")
    assert kapi < pencere and abs(kapi - 330) < 20 and abs(pencere - 480) < 40, y
    o["kapilar"] = [k | ({"konum_cm": 600} if k["arasinda"][0] == "DIŞ" else {}) for k in o["kapilar"]]
    o["pencereler"] = [p | ({"konum_cm": 440} if p["oda"] == "SALON" and p["kenar"] == "alt" else {}) for p in o["pencereler"]]
    y = _yerler(GO.denetle(o)["cevrim"]["is_emri"])
    assert next(c for (t, _), c in y.items() if t == "dis_kapi") > 500


def test_kural3_cogunluk_secilir():
    """Üç okumadan ikisi aynı planı okuduysa (imza) çoğunluk odur; aykırı okuma soru az çıkarsa da seçilmez."""
    a = _okuma("TK06")
    aykiri = {**a, "emin_olunamayanlar": [], "dis_olcu": {"yatay_cm": 900, "dusey_cm": 1088}}
    sec, ozet = GO.cogunluk_sec([aykiri, a, a])
    assert ozet["cogunluk"] == 2 and ozet["secilen"] in (1, 2)
    assert GO.okuma_imzasi(sec) == GO.okuma_imzasi(a)


def test_kural3_cogunluk_yoksa_en_az_soru():
    a = _okuma("TK06")
    b = {**a, "emin_olunamayanlar": [], "dis_olcu": {"yatay_cm": 900, "dusey_cm": 1088}}
    c = {**a, "dis_olcu": {"yatay_cm": 700, "dusey_cm": 1088}}
    sec, ozet = GO.cogunluk_sec([a, b, c])
    assert ozet["cogunluk"] == 0
    n = [len(GO.denetle(x)["sorular"]) for x in (a, b, c)]
    assert len(GO.denetle(sec)["sorular"]) == min(n)


def _worker_oku(tmp_path, n: int, ek: list):
    import json as _j
    import worker
    resim = tmp_path / "cizim.png"
    resim.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    hd = tmp_path / "hazir.json"
    hd.write_text(_j.dumps({"okuma": _okuma("TK06"), "ek_okumalar": ek}, ensure_ascii=False), encoding="utf-8")
    settings = {"gorsel_okuma": {"acik": True, "backend": "manuel", "hazir_dosya": str(hd), "max_tokens": 8000, "timeout_s": 10,
                                 "okuma_sayisi": n}}
    return worker.gorsel_oku({"text": ""}, settings, {"yol": str(resim), "mime": "image/png", "boyut": 72, "sha256": "x"})


def test_kural3_worker_uc_okuma(tmp_path):
    a = _okuma("TK06")
    aykiri = {**a, "dis_olcu": {"yatay_cm": 900, "dusey_cm": 1088}}
    s = _worker_oku(tmp_path, 3, [aykiri, {**a, "emin_olunamayanlar": []}])
    assert s["durum"] == "tamam" and s["cok_okuma"]["okuma"] == 3 and s["cok_okuma"]["cogunluk"] == 2
    assert s["okuma"]["emin_olunamayanlar"] == []                     # çoğunluk içinde en az soru çıkaran


def test_kural3_ayar_birken_tek_okuma(tmp_path):
    s = _worker_oku(tmp_path, 1, [{**_okuma("TK06"), "emin_olunamayanlar": []}])
    assert "cok_okuma" not in s and s["okuma"] == GO.CizimOkumasi.model_validate(_okuma("TK06")).model_dump()


def test_kapisiz_hol_salona_acik_ve_olcu_ceyrek_cm():
    """Lokman 23 Kasım 13:14:12 (76 m² okuyucu planı, hol ile salon arası: "buraya pano koymuş çok bariz bir hata"): giriş kapısından
    kapılarla ulaşılamayan hol yanındaki salona duvarsız açılır (onaylı r05: acik_sinirlar [["HOL", "SALON+MUTFAK"]]); dış ölçünün
    0,25'ten küçük artığı atılır (800,05 → 800)."""
    den = GO.denetle({**_okuma("TK08"), "emin_olunamayanlar": []})
    ie = den["cevrim"]["is_emri"]
    assert ie["acik_sinirlar"] == [["HOL", "SALON+MUTFAK"]]
    assert ie["yapi"]["dis_olcu_cm"]["x"] == 800
    assert any("duvarsız" in n for n in den["notlar"]) and any("800,05" in n for n in den["notlar"])


def test_kapili_hol_kapali_kalir():
    o = _okuma("TK08")
    o = {**o, "emin_olunamayanlar": [], "kapilar": o["kapilar"] + [{"arasinda": ["HOL", "SALON+MUTFAK"], "kenar": None}]}
    den = GO.denetle(o)
    assert den["cevrim"] is None or den["cevrim"]["is_emri"]["acik_sinirlar"] == []


def _tk08_uc_okuma() -> tuple[dict, dict]:
    d = json.loads((VERI / "BK72_TK08_uc_okuma.json").read_text(encoding="utf-8"))
    return d["ilk"], d["ikinci"]


def test_girinti_ve_on_serit_l_veranda():
    """23 Kasım sunucu okuması (üç okuma, 76 m²): girinti ayrı veranda (125,5) ve önündeki şerit cephe boyu (200,01). Şerit gövdeye
    oturmuyordu (Motor: "gövdenin dış yüzüne tam oturmuyor"); şimdi L veranda, gövde 9,50 m (onaylı r05: L VERANDA, 951,25)."""
    _, ikinci = _tk08_uc_okuma()
    kan = GO.kanonik(ikinci)
    assert kan["verandalar"] == [] and round(kan["H"], 2) == 950.06
    v = next(x for x in kan["odalar"] if x["islev"] == "veranda")
    assert len(v["rects"]) == 2


def test_ikinci_bakis_hol_salon_kapisi_eklemez():
    """İkinci bakış hol–salon açık geçişini kapı diye yazdı (şemada açık geçiş alanı yok); kapı alınmaz, geçiş duvarsız (Lokman 13:14)."""
    ilk, ikinci = _tk08_uc_okuma()
    sec, den, secildi = GO.ikinci_bakis_sec(ilk, GO.denetle(ilk), ikinci)
    assert secildi and den["sorular"] == []
    assert not any({"HOL", "SALON+MUTFAK"} == set(k["arasinda"]) for k in sec["kapilar"])
    ie = den["cevrim"]["is_emri"]
    assert ie["acik_sinirlar"] == [["HOL", "SALON+MUTFAK"]] and ie["yapi"]["dis_olcu_cm"] == {"x": 800, "y": 950}


def _tk08_okunan_plan():
    ilk, ikinci = _tk08_uc_okuma()
    _, den, _ = GO.ikinci_bakis_sec(ilk, GO.denetle(ilk), ikinci)
    ie = den["cevrim"]["is_emri"]
    from motor import geometry as G
    return ie, G.kur(json.loads(json.dumps(ie)))


def test_bk73_salon_on_penceresi_okunan_yerde():
    """BK-73 (76 m², Nimet Doğan): 180/150 okunan yerinde (600) salonun önünde; Motor onu mutfağın önüne atıyordu (464 cm uzak). Salonun
    ön duvarı yatak odası 2'nin duvar aksına dayanır: 57,75 + 125,5 + 251 + 89,75 (onaylı r05 ile aynı); 120/150 mutfağın önünde."""
    ie, plan = _tk08_okunan_plan()
    assert ie["yapi"]["dizilim"]["dis_pano_dayanagi"] == [{"x": 449.25, "aralik_cm": [261.0, 790.0], "duvar_cm": 758.0}]
    merkez = {k["olcu"]: round(c, 2) for k, c, _ in GO._aciklik_merkezleri(plan) if k["olcu"] in ("180x150", "120x150")}
    assert merkez == {"180x150": 574.75, "120x150": 135.5}
    on = sorted((p.a0, p.a1) for p in plan.panolar if p.duvar.yon == "x" and abs(p.duvar.c - 192.0) < 1e-6)
    assert [round(b - a, 2) for a, b in on] == [57.75, 125.5, 251.0, 89.75]


def test_bk73_veranda_ara_kolonu_zincirden():
    """BK-73: verandanın ön kenarındaki 391,5 / 408,55 zinciri ara kolondur (onaylı r05: dikme [386,5, 0]); öteki zincir noktaları oda
    sınırına yakın (624,55 ve 750,05) kolon değildir."""
    ie, plan = _tk08_okunan_plan()
    assert ie["dikmeler"] == [[386.5, 0]]
    assert any("ara kolon" in v and "391,5" in v for v in ie["varsayimlar"])
    assert (386.5, 0.0, 396.5, 10.0) in plan.dikmeler


def test_bk73_uzak_yerlesim_secilmez():
    """BK-73: yeri okunan açıklık tek yerleşimde bir panodan (125,5 cm) uzak düşüyorsa kod seçmez, soru kalır (K21)."""
    ilk, ikinci = _tk08_uc_okuma()
    sec, den, _ = GO.ikinci_bakis_sec(ilk, GO.denetle(ilk), ikinci)
    ie = json.loads(json.dumps(den["cevrim"]["is_emri"]))
    ie["yapi"]["dizilim"].pop("dis_pano_dayanagi", None)
    for a in ie["acikliklar"]:
        a.pop("pano", None)
        if a.get("olcu") == "180x150":
            a[GO.KONUM] = 150.0                       # mutfağın önünde okunmuş gibi; 120/150 salonun önünde
        if a.get("olcu") == "120x150":
            a[GO.KONUM] = 700.0
    from motor import geometry as G
    import copy
    t = copy.deepcopy(ie)
    for a in t["acikliklar"]:
        a.pop(GO.KONUM, None)
    try:
        G.kur(t)
        hata = None
    except G.IsEmriHatasi as h:
        hata = str(h)
    assert hata
    yeni, _ = GO._yerlesim_ara(ie, hata, G)
    if yeni is not None:
        merkez = {k["olcu"]: c for k, c, _ in GO._aciklik_merkezleri(G.kur(copy.deepcopy(yeni)))}
        assert abs(merkez["180x150"] - 150.0) <= 125.5 and abs(merkez["120x150"] - 700.0) <= 125.5


# ───────────── BK-80 (D-155): kapı odanın içine; pencere ölçüsü ve yüksekliği sorulmaz ─────────────
def test_bk80_pencere_olcu_ve_yukseklik_sorusu_bayiye_gitmez():
    """26 Kasım canlı denemesi (87 m² kroki): okuyucu banyo penceresinin ölçüsünü ve pencere yüksekliğini sordu. Lokman, kart 06:41:28 UTC
    "Evet, dördü de bakımda": sorulmasın, standart alınsın. Yeri, duvarı, adedi soran soru kalır."""
    for s in ("Banyo penceresinin ölçüsü yazmıyor; kaç cm?", "Pencere yüksekliği (denizlik) kaç cm?",
              "Pencere yükseklikleri ve banyo penceresinin ölçüsü nedir?"):
        assert GO.pencere_olcu_sorusu(s), s
    for s in ("Salon penceresi hangi duvarda?", "Banyo penceresinin yeri neresi?", "Mutfakta kaç pencere var?",
              "Giriş kapısının genişliği yazmıyor", "Üst ölçü zinciri 261+126+188+324 = 899, toplam 898; hangisi doğru?"):
        assert not GO.pencere_olcu_sorusu(s), s
    o = {**_okuma("TK01"), "emin_olunamayanlar": ["Banyo penceresinin ölçüsü yazmıyor; kaç cm?", "Pencere yüksekliği kaç cm?"]}
    den = GO.denetle(o)
    assert not any("pencere" in q.lower() for q in den["sorular"]), den["sorular"]
    assert any("pencerenin üstü yerden 200 cm" in n for n in den["notlar"])


def test_bk80_oda_kapisi_odanin_icine_acilir_plan_dogrulamadan_gecer(tmp_path):
    """26 Kasım canlı denemesi: dört oda kapısı 125,5'lik hole açıldı, kanatlar çarpıştı, Motor denetimi planı durdurdu. Lokman, kart
    26 Kasım 06:47:13 UTC "Odanın içine, eskizdeki gibi". Aynı okuma (BK-74, aynı kroki) artık plan çıkarır; onaylı TK-04 r08 gibi
    kapılar holden odaya."""
    import copy, json
    from motor import dxf_out
    o = json.loads((Path(__file__).resolve().parent / "veri" / "BK74_TK04_okuma.json").read_text(encoding="utf-8"))
    ie = GO.denetle({**o, "emin_olunamayanlar": []})["cevrim"]["is_emri"]
    ic = sorted(a["arasi"] for a in ie["acikliklar"] if a["tur"] == "ic_kapi")
    assert ic == [["HOL", "BANYO"], ["HOL", "MUTFAK"], ["HOL", "SALON"], ["HOL", "YATAK ODASI 1"], ["HOL", "YATAK ODASI 2"]], ic
    r = dxf_out.uret(copy.deepcopy(ie), tmp_path)
    assert r["validation_passed"] is True


def test_bk80_iki_oda_arasinda_kapi_kucuk_odaya_acilir():
    mh = [{"ad": "SALON", "konum_cm": [[0, 0, 400, 400]]}, {"ad": "MUTFAK", "konum_cm": [[400, 0, 650, 400]]},
          {"ad": "HOL", "konum_cm": [[0, 400, 650, 525.5]]}]
    kan = {"odalar": [{"ad": "SALON", "islev": "salon"}, {"ad": "MUTFAK", "islev": "mutfak"}, {"ad": "HOL", "islev": "hol"}]}
    assert GO._kapi_yonu(kan, mh, "MUTFAK", "SALON") == ["SALON", "MUTFAK"]
    assert GO._kapi_yonu(kan, mh, "SALON", "MUTFAK") == ["SALON", "MUTFAK"]
    assert GO._kapi_yonu(kan, mh, "MUTFAK", "HOL") == ["HOL", "MUTFAK"]


def test_bk80_varsayim_metni_sade_koordinat_yok():
    """26 Kasım canlı denemesi: "Çiziminizi okurken varsaydıklarım" mesajında "duvar eksenleri x=310, 530 ve y=390" gibi okuyucu notları
    bayiye gitti. Lokman, kart 06:41:28 UTC: sade yazılsın (D-70). Aynı okuma: koordinat yok, standartlar tek satır, her not yine var."""
    import json, re
    o = json.loads((Path(__file__).resolve().parent / "veri" / "BK74_TK04_okuma.json").read_text(encoding="utf-8"))
    den = GO.denetle({**o, "emin_olunamayanlar": []})
    m, ek = GO.teyit_metni(o, den)
    tum = m + (ek or "")
    assert not re.search(r"\b[xy]\s*=|eksen|ızgara", tum), tum
    assert "Çizimde yazmayanları standart aldım: prefabrik, duvar 2,50 m, beşik çatı, mahya girişe paralel." in tum
    assert "Yan cephe 9,00 m yerine 8,985 m oldu." in tum
    assert "Yazılı oda ölçülerini en yakın pano aksına getirdim: Hol 410 → 381,5 cm." in tum
    assert "Ölçüsü yazmayan 4 yeri çizimdeki orana göre aldım." in tum
    assert len(GO.bayi_notlari(den["notlar"])) == len(den["notlar"]) - 3      # dört standart notu tek satır
