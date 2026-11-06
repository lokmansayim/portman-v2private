"""İE-15 K6 · TK-04'ün çatısı kart modelinde ve montaj rehberinde (D-53; İş Emri r06 `testler/motor/veri/TK04_r06.json`: r05'in planı ve
trapez sac kaplaması, Lokman 4 Kasım 2026 20:47 "çatı paneli tek kat değil Trapez olacak", "Trapez mahya olacak"; ana makaslar cumba
makasının arkasından, Lokman 5 Kasım 07:19–10:15, `cati.cumbalar[0].ana_makas: "cumba_makasindan"`).

Beşik + çıkıntısız çapraz cumba (AP-06 gibi, D-47): ana çatının mahyası x yönünde, cumba önde 0–386,5. Ana makaslar cumbanın baş makasının
iç yüzünden (7,5) 10 cm topukla başlar, arka saçak 30 cm; cumbanın iki yanında dere ve 37,5 cm'lik kısa saçak. Çatı çatı tanımından
(`motor/cati_capraz.py`; liste üreteci, çizim ve bugünkü IFC aynı tanımı okur). Kart modelinde çatı kartları "kural yok" değil, listeyle
aynı: yerleşen adetle sayılanlar (makaslar, tek kat panel, iniş) adet adet, boyla alınanlar kesim stoğuyla (dere ve saçak omegası kısa
saçaklar yüzünden ayrı, testte gerekçesiyle). Saçak omegası (M-01, D-41; D-53 ile beşik + cumbada da) saçak duvarının üstünde duvar
boyunca. Rehber 62 m² şablonunun cumbasıyla: ana çatının 8 makası, cumbanın baş makası ve ana çatının üstündeki yavru makası (MA-05),
derelerde kırpılan yüzler, ters mahya adımı, iki boy kaplama; mahya x yönünde olduğu için asma tavanın omegaları x boyunca, H'ları dik.
Trapez sac (KP-03) tek kat panel gibi dizilir, kapatması liste kuralından (D-50, M-11: standart 100 cm); trapez sac mahyası (CK-07) her
beşiğin mahyasında ⌈mahya ÷ kapatma⌉. Beşik evlerin rehberi değişmez (`test_rehber.py`, `test_paket.py`).
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
IE = KOK / "testler" / "motor" / "veri" / "TK04_r06.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tk04(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(IE)
    kart = tmp_path_factory.mktemp("tk04_k6")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return {"d": veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04"), "say": _oku(kart / "TK04_kart_sayim.json"), "L": L, "ie": ie, "kart": kart}


def _liste(L: list[dict], ad: str) -> int:
    """Listedeki satırın adedi (`veri.kiyas` gibi: ad aynen ya da ardından " ·" / " (" ile; "Metal dere" inişi saymaz)."""
    return sum(s["adet"] or 0 for s in L if s["kalem"] == ad or s["kalem"].startswith((ad + " ·", ad + " (")))


def test_cati_capraz_cumba(tk04):
    c = tk04["ie"]["cati"]
    assert c["tip"] == "besik_cumba" and c["makas_ekseni"] == "y" and c["cumbalar"] == [{"cephe": "on", "bas_cm": 0, "bit_cm": 386.5, "cikinti_cm": 0, "ana_makas": "cumba_makasindan"}]


def test_kart_modeli_listeyle_ayni(tk04):
    say, L = tk04["say"], tk04["L"]
    assert say["cati_tipi"] == "besik_cumba" and say["kural_yok"] == [] and say["sema_hatasi"] == {"bugunku_ifc": 0, "kart_modeli": 0}
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    yerlesen = {"MA-01": "Makas (baş)", "MA-02": "Makas (orta)", "MA-05": "Yavru makas · cumba", "KP-03": "Trapez sac",
                "BT-01": "Baş makas betopanı"}
    assert {k: adet[k] for k in yerlesen} == {k: _liste(L, on) for k, on in yerlesen.items()} == {
        "MA-01": 2, "MA-02": 6, "MA-05": 2, "KP-03": 26, "BT-01": 9}
    # iniş: cumba ile verandanın köşesinde tek iniş (Lokman, 5 Kasım 2026 12:51: "cumba ile veranda köşesindeki dere inişi de tam köşenin
    # iç tarafına gelsin"; önce cumbanın kısa saçağının ve ön saçağın inişi aynı köşede ikiydi): kart modeli 6; liste de 6 (D-61 madde 2,
    # Lokman'ın kartı 5 Kasım 22:49; önce "ek çatı parçası başına 2" ile 7)
    assert (adet["DR-02"], _liste(L, "Metal dere inişi aparatı")) == (6, 6)
    assert (_liste(L, "70 mm PVC dere iniş borusu"), _liste(L, "Açık dirsek"), _liste(L, "Kapalı dirsek"), _liste(L, "PVC iniş kelepçesi")) == (12, 12, 6, 12)
    stok = {k: say["kesim_plani"][k]["stok"] for k in ("AS-01", "CK-02", "CK-03", "CK-04", "CK-07")}
    boyla = {"AS-01": "Aşık", "CK-02": "Saçak sacı", "CK-03": "Alın sacı", "CK-04": "Baş makas Z'si", "CK-07": "Trapez sac mahyası"}
    assert stok == {k: _liste(L, on) for k, on in boyla.items()} == {"AS-01": 44, "CK-02": 7, "CK-03": 11, "CK-04": 10, "CK-07": 13}
    # r06 (ana makaslar cumba makasının arkasında): cumbanın iki yanındaki 37,5 cm'lik kısa saçaklar listede saçak hattı (dere 15,25 m ÷ 3,8
    # = 5; saçak omegası M-01 "adedi saçak boyundan" 15,25 m ÷ 2,5 = 7). Kart modelinde dere hat başına kesilir, iki kısa hattın parçası
    # artandan çıkar (4); kısa saçağın altında duvar boyu yok (duvarın ucu cumbanın baş makas omegasının altında), saçak omegası kurulmaz (6)
    assert {k: (say["kesim_plani"][k]["stok"], _liste(L, on)) for k, on in (("DR-01", "Metal dere"), ("CK-01", "100'lük saçak omegası"))} == {
        "DR-01": (4, 5), "CK-01": (6, 7)}
    assert adet["MA-03"] == adet["MA-04"] == adet["KP-02"] == 0 and "CK-06" not in say["kesim_plani"]   # taşan veranda, paralel cumba, tek kat yok


def test_trapez_sac_ve_mahyasi(tk04):
    """Trapez sac liste gibi: ana çatıda yüz başına ⌈mahya ÷ kapatma⌉, cumbada iki yüz birlikte; kapatma liste kuralından (D-50, M-11: 1,0).
    Trapez sac mahyası her beşiğin mahyası ayrı, ⌈mahya ÷ kapatma⌉ (ana çatı 10, cumba 3), parça boyu sacın kapatması; kural yok yok."""
    say, L = tk04["say"], tk04["L"]
    kp = [p for p in say["yerlesim"]["parcalar"] if p["kart"] == "KP-03"]
    assert {p["bilgi"]["Genislik_cm"] for p in kp} == {100.0} and Counter(p["bilgi"]["Cati"] for p in kp) == {"ana çatı": 20, "cumba": 6}
    c7 = say["kesim_plani"]["CK-07"]
    assert (c7["parca_boyu_cm"], c7["hat_basina"]) == (100.0, [10, 3]) and next(s["olcu"] for s in L if s["kalem"] == "Trapez sac mahyası") == "L 1000"
    assert say["kenar"]["liste"]["CK-07"] == 13 and "CK-06" not in say["kenar"]["liste"] and "kurulmadi" not in say["kenar"]


def test_trapez_kapatmasi_is_emrinden():
    """İş Emri'nin çatı kaplaması kapatmayı yazıyorsa ("(80 cm kapatır)") o, yazmıyorsa liste kuralı; liste üretecinin okuması (D-50)."""
    from motor import yerlesim as Y
    C = {"kapatma_trapez": 1.0}
    assert Y.trapez_kapatma_m({"ozellikler": {"Çatı Kaplaması": "Trapez Saç"}}, C) == 1.0
    assert Y.trapez_kapatma_m({"ozellikler": {"Çatı Kaplaması": "Trapez Kaplama (80 cm kapatır)"}}, C) == 0.8
    assert Y.trapez_kapatma_m({"ozellikler": {"ÇATI KAPLAMASI": "Trapez Sac (82,5 cm kapatır)"}}, C) == 0.825


def test_sacak_omegasi_duvar_boyunca(tk04):
    """M-01 (D-41, D-53): saçak omegası saçak duvarının üstünde, duvar boyunca; saçağa uzamaz. TK-04'te saçak duvarları ana çatının önü
    (cumbanın sağı, veranda kirişi dahil) ve arkası; cumbanın saçağı yok (yüzleri derelerle ana çatıya iner)."""
    d = tk04["d"]
    W, DY = d["dis"]
    om = sorted((o["perp"], o["a0"], o["a1"]) for o in d["omega_duvar"] if o["tur"] == "sacak")
    assert om == [(5, 416.5, W), (DY - 5, 0, W)]
    assert sorted(o["yer"] for o in d["omega_duvar"] if o["tur"] == "bas") == [
        "sağ duvar ve veranda kirişi (MKS08 altı)", "sol duvar (MKS01 altı)", "ön duvar ve veranda kirişi, cumbanın altı (MKS09 altı)"]


def test_rehber_adimlari(tk04):
    d = tk04["d"]
    ad = [a.get("ad") for a in d["adimlar"]]
    assert d["N"] == 21 and len(d["panels"]) == 50
    i = ad.index("Dere ve inişler")
    assert ad[i + 1:i + 3] == ["Ters mahya", "Trapez sac ve mahya"] and d["S"]["tersmahya"] == i + 1
    assert "Ana çatı ve cumba makasları" in ad and d["cati_adim"] == list(range(d["S"]["makas"], d["S"]["alin"] + 1))
    tm = d["adimlar"][i + 1]
    assert [r[1:3] for r in tm["rows"]] == [["Ters mahya (dere içi) L 2800", "3 adet"], ["Ters mahya kenar kutusu L 21 × 40 × 21 × 2800", "6 adet"]]
    assert d["kabuk"]["spec"][3].startswith("beşik + çapraz cumba %33")
    kp = d["adimlar"][i + 2]
    assert [r[1:3] for r in kp["rows"] if r[3:] == ["liste"]] == [["Trapez sac · ana çatı L 4900", "20 adet"], ["Trapez sac · cumba L 2410", "6 adet"],
                                                              ["Trapez sac mahyası L 1000", "13 adet"], ["Mahya bandı rulo 10 m", "2 adet"]]
    assert "trapez sac mahyasıyla" in kp["p"] and d["kaplama"]["profil"]["kapatir"] == 100 and d["kaplama"]["metin"]["mahya_ad"] == "Trapez sac mahyası"


def test_makaslar(tk04):
    """Ana çatı 8 makas (MA-01/MA-02, y boyunca), cumbanın baş makası dış uçtaki kalkan duvarının üstünde ve ana çatının üstündeki yavru
    makas (ikisi de MA-05, x boyunca); yavru makas sayısı kart modeliyle ve listedeki "Yavru makas · cumba" ile aynı."""
    d, say, L = tk04["d"], tk04["say"], tk04["L"]
    m = d["makas"]
    assert Counter((x["aile"], x["R"], x["yon"]) for x in m) == {("ana", "AN", "y"): 8, ("cumba", "CU", "x"): 1, ("ara", "CU", "x"): 1}
    assert all("kod" not in x for x in m if x["aile"] == "ana") and all(x["kod"] == "MA-05" for x in m if x["aile"] != "ana")
    n05 = next(k["adet"] for k in say["kartlar"] if k["kod"] == "MA-05")
    assert sum(x["aile"] != "ana" for x in m) == n05 == _liste(L, "Yavru makas · cumba")
    ana = sorted(x["konum"] for x in m if x["aile"] == "ana")
    assert ana[0] == 3.7 and ana[-1] == round(d["dis"][0] - 3.7, 2) and all(abs(b - a - 125.5) < 0.01 for a, b in zip(ana[1:-1], ana[2:-1]))
    ara = next(x for x in m if x["aile"] == "ara")
    assert ara["zR"] == "AN" and ara["dereler_arasi"][0] < ara["bas"] < ara["son"] < ara["dereler_arasi"][1]
    assert d["cards"]["MA-05"]["ad"] == "Yavru makas (çapraz cumba)"
    # AP-06 paftasındaki gibi (D-53 ek, Lokman 5 Kasım 00:45; `cumba_yavru_makasi`): baş makasın iç yüzünden net 46,75 geride, 130,5 ve
    # 256'daki ana makaslara oturur, uçları onlardan 36,3 taşar (198,1 cm); önce 130,5'te, dereler arasında 73 cm idi
    assert (ara["konum"], ara["bas"], ara["son"]) == (56.75, 94.2, 292.3)
    assert ana[1] == 130.5 and ana[2] == 256.0 and ara["bas"] < ana[1] < ana[2] < ara["son"]
    # D-61 madde 1 (Lokman, kart 5 Kasım 22:49): listede de kısa, boyu çatının tanımından (uçtan uca 198,1); baş makas yavru makas boyuyla
    assert sorted((s["olcu"], s["adet"]) for s in L if s["kalem"] == "Yavru makas · cumba") == [("L 1981", 1), ("L 4465", 1)]
    assert round((ara["son"] - ara["bas"]) * 10) == 1981


def test_yavru_makas_ap06_paftasindaki_gibi(tk04):
    """Çatı tanımı (`cati_capraz._yavru_yeri`) ile bugünkü IFC'nin yavru makası aynı uçlarda; kural kitaptan (`cumba_yavru_makasi`)."""
    import ifcopenshell
    import ifcopenshell.util.element as E
    from motor import cati_capraz as CC
    from motor import geometry as G
    ie = tk04["ie"]
    T = CC.tanim(G.kur(copy.deepcopy(ie)), copy.deepcopy(ie))
    cu = next(q for q in T["parcalar"] if q["rol"] == "cumba")
    bas, yavru = cu["makaslar"]
    assert CC.yavru_kurali() == {"net": 46.75, "tasma": 36.3, "kalinlik": 5.0}
    assert yavru["konum"] - bas["konum"] - 5.0 == pytest.approx(46.75)                    # yüzden yüze net (makas kalınlığı 5)
    assert yavru["oturdugu"] == [130.5, 256.0] and yavru["uclar"] == [94.2, 292.3]
    f = ifcopenshell.open(str(tk04["kart"] / "TK04_model.ifc"))
    ust = [a for a in f.by_type("IfcElementAssembly") if E.get_pset(a, "PortatifEv_Kapsam", "AnaCatininUstunde")]
    assert len(ust) == 1
    alt = [e for e in f.by_type("IfcMember") if e.Name == f"{ust[0].Name}_ALT_BASLIK"]
    import ifcopenshell.geom
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)
    v = ifcopenshell.geom.create_shape(st, alt[0]).geometry.verts
    xs, ys = v[0::3], v[1::3]
    birim = 100 if max(xs) < 50 else 1                                                     # IFC metre ya da cm
    assert (round(min(xs) * birim, 1), round(max(xs) * birim, 1)) == (94.2, 292.3)
    assert round((min(ys) + max(ys)) / 2 * birim, 2) == 56.75
    # kural kurulamazsa (dar cumba: uçlar derelerin dışında) makas D-47'nin yerinde kalır, uyarı yazılır; çatı yine kurulur (geometri hakemi)
    dar = copy.deepcopy(ie)
    dar["cati"]["cumbalar"][0].update(bas_cm=0, bit_cm=300)
    T2 = CC.tanim(G.kur(copy.deepcopy(dar)), copy.deepcopy(dar))
    y2 = next(q for q in T2["parcalar"] if q["rol"] == "cumba")["makaslar"][1]
    assert y2["konum"] == 130.5 and "uclar" not in y2
    assert any("yavru makas AP-06'nın kuralıyla kurulamadı" in u for u in T2["uyarilar"])


def test_ana_makaslar_cumba_makasinin_arkasindan(tk04):
    """Lokman, 5 Kasım 2026 07:19 ve 07:23 (`cumba_altindaki_ana_makas`, İş Emri r06 `cati.cumbalar[0].ana_makas: "cumba_makasindan"`):
    "… cumba makasının tam arkasına ana makası normal 10 cm topuk olarak koy …"; "kesme yapmayacağız makasları geri çekeceğiz ama arka
    taraftaki 30 cm saçağıda bozmayacağız …"; 10:15 eskize "evet doğru gözüküyor". Bütün ana makaslar cumbanın baş makasının iç yüzünde
    (y = 7,5) 10 cm topukla başlar, arka saçak 30 cm; makas kısalır, mahya arkaya kayar (468), cumbanın iki yanında birer dere ve 37,5 cm
    kısa saçak. Çatı tanımı, liste, bugünkü IFC ve rehber aynı; makas sayısı değişmez."""
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as E
    from motor import cati_capraz as CC
    from motor import cati_prefabrik as CP
    from motor import geometry as G
    from motor.genel import cati_genel
    ie = tk04["ie"]
    assert ie["cati"]["cumbalar"][0]["ana_makas"] == "cumba_makasindan" and CC.bitis_kurali() == "yuz"
    T = CC.tanim(G.kur(copy.deepcopy(ie)), copy.deepcopy(ie))
    ana, cu = (next(q for q in T["parcalar"] if q["rol"] == r) for r in ("ana", "cumba"))
    assert (ana["b"], ana["duvar_b"], ana["geri_cm"], ana["aciklik_cm"]) == ([37.5, 898.5], [0.0, 898.5], 7.5, 861.0)
    assert (ana["mahya"][0][1], ana["makas_yuksekligi_cm"]) == (468.0, 161.97) and len(ana["makaslar"]) == 8
    assert cu["makaslar"][0]["konum"] == 5.0 and cu["boy_cm"] == 230.75                     # baş makas 2,5–7,5: ana makas iç yüzünde
    k = {(e["tur"], tuple(round(v, 2) for v in e["p"]), tuple(round(v, 2) for v in e["q"])) for e in cati_genel.cati_kur(T)["kenarlar"]
         if e["tur"] in ("vadi", "sacak")}
    vadi = sorted(sorted([p, q]) for t_, p, q in k if t_ == "vadi")
    assert vadi == [[(-30.0, 7.5), (193.25, 230.75)], [(193.25, 230.75), (416.5, 7.5)]]
    assert sorted(abs(p[1] - q[1]) for t_, p, q in k if t_ == "sacak" and p[0] == q[0]) == [37.5, 37.5]      # cumbanın iki yanı
    # liste: ana makasların açıklığı 861, sayı aynı; cumbanın kısa saçakları saçak hatlarında (dere, saçak omegası saçak boyundan)
    L = tk04["L"]
    assert {s["olcu"] for s in L if s["kalem"].startswith("Makas (")} == {"açıklık 8610"}
    # bugünkü IFC: ana makasların üst başlığı saçak ucunda (ön 7,5, arka 928,5), alt başlığı topuktan topuğa
    f = ifcopenshell.open(str(tk04["kart"] / "TK04_model.ifc"))
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)

    def uc(ad):
        v = ifcopenshell.geom.create_shape(st, next(e for e in f.by_type("IfcMember") if e.Name == ad)).geometry.verts
        b = 100 if max(abs(x) for x in v) < 50 else 1
        return round(min(v[1::3]) * b, 1), round(max(v[1::3]) * b, 1)
    asm = [a for a in f.by_type("IfcElementAssembly") if (E.get_pset(a, "PortatifEv_Kapsam") or {}).get("CatiParcasi") == "ana çatı"]
    assert len(asm) == 8
    # alt başlık açıklık boyunca (37,5 … 898,5), listedeki "açıklık 8610" gibi (geometri hakemi, dördüncü tur; önce 7,5'ten başlıyordu)
    assert {(uc(f"{a.Name}_UST_1")[0], uc(f"{a.Name}_UST_2")[1], uc(f"{a.Name}_ALT_BASLIK")) for a in asm} == {(7.5, 928.5, (37.5, 898.5))}
    # rehber: ana makaslar 7,5'ten 928,5'e (ön duvarın dikmesi yok, makasın topuğu duvarın üstünde); baş makas omegası makasın boyunca
    # (M-03, Lokman 07:15 "baş makasın omegasını dışarda bırakmışsın"); sol kalkanın ön ucunda saçak ucu betopanı yok
    m = tk04["d"]["makas"]
    assert {(x["bas"], x["son"], tuple(x["wl"])) for x in m if x["aile"] == "ana"} == {(7.5, 928.5, (895.8,))}
    om = {o["yer"]: (o["a0"], o["a1"]) for o in tk04["d"]["omega_duvar"] if o["tur"] == "bas"}
    assert om == {"sol duvar (MKS01 altı)": (7.5, 928.5), "sağ duvar ve veranda kirişi (MKS08 altı)": (7.5, 928.5),
                  "ön duvar ve veranda kirişi, cumbanın altı (MKS09 altı)": (-30.0, 416.5)}, om
    K = {k["ad"]: k for k in tk04["d"]["kalkan"]}
    assert K["ana çatı sol kalkanı (MKS01)"]["duvar"]["A"] == K["ana çatı sol kalkanı (MKS01)"]["uc"]["A"] == -7.5
    # saçak: ön saçak duvarın üstünde biter (saçak altı yok); cumbanın iki yanında y boyunca kısa saçak (sol yanında iniş evin köşesinde,
    # sağ yanının deresi cumba ile verandanın köşesindeki inişe akar; Lokman 12:51)
    sa = {s["ad"]: s for s in tk04["d"]["sacak"]}
    assert sorted(sa) == ["ana çatı arka saçağı", "ana çatı ön (cumbanın sağı) saçağı", "cumba sağ yanı saçağı", "cumba sol yanı saçağı"]
    on = sa["ana çatı ön (cumbanın sağı) saçağı"]
    assert on["t0"] == on["t1"] and "saçak altı yok" in on["not"] and {sa[a]["o"] for a in sa if a.startswith("cumba")} == {"v"}
    # r05 (anahtarsız) ve kör İş Emri'leri eski yolda: ana çatının ayak izi gövde, makaslar saçaktan saçağa
    for yol in (IE.with_name("TK04_r05.json"), KOK / "testler" / "kor" / "projeler" / "AP06" / "is_emri.json",
                KOK / "testler" / "cizim" / "evler" / "AP13.json", KOK / "testler" / "kor" / "projeler" / "AP16" / "is_emri.json"):
        k_ie = _oku(yol)
        a_ = next(q for q in CC.tanim(G.kur(copy.deepcopy(k_ie)), copy.deepcopy(k_ie))["parcalar"] if q["rol"] == "ana")
        assert "geri_cm" not in a_ and "duvar_b" not in a_ and CP.ana_geri_cm(k_ie["cati"], G.kur(copy.deepcopy(k_ie))) is None, yol
    with pytest.raises(CP.PrefabrikCatiHatasi):
        bozuk = copy.deepcopy(ie)
        bozuk["cati"]["cumbalar"][0]["ana_makas"] = "kes"
        CP.cati(G.kur(copy.deepcopy(bozuk)), bozuk)


def test_inisler_kendi_hatlarinda(tk04):
    """Rehberin inişleri kart modelinin yazdığı düzlemin hattında (geometri hakemi, İE-15 K6 dördüncü tur: ön saçağın sol uç inişi yakın
    olan cumbanın kısa hattına düşüyor, o hat iki iniş alıyordu); cumbanın kısa yan saçaklarının inişi derenin boyunda (-30 … 7,5)."""
    ini = tk04["d"]["dere"]["inisler"]
    assert Counter(i["hat"] for i in ini) == {"ana çatı ön (cumbanın sağı)": 2, "ana çatı arka": 3, "cumba sol yanı": 1}
    hat = {h["ad"]: h for h in tk04["d"]["dere"]["hatlar"]}
    assert all(hat[i["hat"]]["a0"] <= i["s"] <= hat[i["hat"]]["a1"] for i in ini if i["hat"].startswith("cumba"))


def _kose_inisi(d: dict) -> None:
    """Lokman, 5 Kasım 2026 12:51: "ne olursa olsun kesinlikle düzgün insin … cumbanın solundaki kısa dere tam köşeye gelsin": cumbanın sol
    kısa saçağının borusu evin ön sol köşesinde (sol duvarın yüzünde, köşeden borunun yarısı kadar), ağzı borunun tam hizasında (kaz boynu duvara
    dik; önce boru köşe direği kaplamasının yanında, 17 cm gerideydi); cumba ile verandanın köşesinde tek iniş."""
    ini = d["dere"]["inisler"]
    sol = [i for i in ini if i["hat"] == "cumba sol yanı"]
    assert len(sol) == 1 and sol[0]["boru"] == sol[0]["agiz"] and 0 < sol[0]["boru"] <= 4 and sol[0]["yuz"] == 0 and "köşesi" in sol[0]["duvar"]
    assert not [i for i in ini if i["hat"] == "cumba sağ yanı"]


def test_kose_inisleri(tk04):
    _kose_inisi(tk04["d"])


def test_yuzler_dere_ve_kaplama(tk04):
    d, L = tk04["d"], tk04["L"]
    Y = d["yuz"]
    assert set(Y) == {"MFL", "MFR", "MB", "CL", "CR"} and {k for k, y in Y.items() if "dere" in y} == {"MFL", "MFR", "CL", "CR"}
    assert [h["ad"] for h in d["dere"]["hatlar"]] == ["ana çatı ön (cumbanın sağı)", "ana çatı arka", "cumba sol yanı", "cumba sağ yanı"]
    assert len(d["dere"]["inisler"]) == next(k["adet"] for k in tk04["say"]["kartlar"] if k["kod"] == "DR-02")
    assert sorted(k["ad"] for k in d["kalkan"]) == ["ana çatı sağ kalkanı (MKS08)", "ana çatı sol kalkanı (MKS01)", "cumba kalkanı (MKS09)"]
    assert {k: y["serit"]["ad"] for k, y in Y.items()} == {"MFL": "L 4900 (ana çatı)", "MFR": "L 4900 (ana çatı)", "MB": "L 4900 (ana çatı)",
                                                          "CL": "L 2410 (cumba)", "CR": "L 2410 (cumba)"}
    assert _liste(L, "Trapez sac · ana çatı") == 20 and _liste(L, "Trapez sac · cumba") == 6


def test_asiklar_kart_modelinden(tk04):
    """Aşık sıraları ve parçaları kart modelinden; ana çatının cumbalı yüzü derelerin birleştiği yerden ikiye bölünür, bölme çizgisini geçen
    parça iki yüzde de gerçek boyuyla (410) yazılır: rehberdeki parçalar, bölünen parçalar bir sayılınca, kart modelinin aşıklarıyla aynı."""
    d, say = tk04["d"], tk04["say"]
    A = d["asik"]["yuzler"]
    bolunen = sum(1 for p in A["MFL"]["pafta"] if p == [410.0])
    assert bolunen == 5 and all(p[-1] == 410.0 for p in A["MFR"]["pafta"][-bolunen:])
    assert sum(len(p) for a in A.values() for p in a["pafta"]) - bolunen == say["kesim_plani"]["AS-01"]["parca"] == 63


def test_asma_tavan_mahyaya_paralel(tk04):
    """Mahya x yönünde: oda içi tavan omegaları x boyunca, tavan H'ları onlara dik (y boyunca); gözler odaların içinde."""
    d = tk04["d"]
    assert d["tavan"]["tip"] == "asma" and {o["yon"] for o in d["omega"] if o["oda"] != "veranda"} == {"x"}
    assert d["tavan"]["h"] and {h["o"] for h in d["tavan"]["h"]} == {"v"}
    assert d["tavan"]["acik"] == [{"ad": "Veranda", "yon": "x", "rects": [[386.5, 10, 878.5, 193.25]]}]


@pytest.mark.parametrize("kod, kp03, ck07", [("AP16", 28, 14), ("AP06", 30, 15)])
def test_seksenlik_trapez_kor_is_emrinde(kod, kp03, ck07):
    """80'lik trapez sac (İş Emri "Trapez Kaplama (80 cm kapatır)"; D-50: kapatma İş Emri'nden, mahya L 800) kör İş Emri'lerinde: kart
    modelinin kaplaması, mahyası, alın sacı ve Z'si listeyle aynı. Alın sacı çatının kenarından milimetreye, liste gibi (AP-16: hatlar
    25,30 m ÷ 2,3 = 11; geometri hakemi, İE-15 K6). Aşığın parça adedi iki yolla sayılır (D-28 › A3; AP-16 41 / 42, AP-06 52 / 53)."""
    from motor import kart_model, prefabrik_liste as PL
    import tempfile
    ie = _oku(KOK / "testler" / "kor" / "projeler" / kod / "is_emri.json")
    assert "80 cm kapatır" in ie["ozellikler"]["Çatı Kaplaması"] and ie["cati"]["tip"] == "besik_cumba"
    with tempfile.TemporaryDirectory() as t:
        kart_model.uret(copy.deepcopy(ie), Path(t), kod)
        say = _oku(Path(t) / f"{kod}_kart_sayim.json")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    kp = [p for p in say["yerlesim"]["parcalar"] if p["kart"] == "KP-03"]
    assert say["kural_yok"] == [] and adet["KP-03"] == _liste(L, "Trapez sac") == kp03 and {p["bilgi"]["Genislik_cm"] for p in kp} == {80.0}
    c7 = say["kesim_plani"]["CK-07"]
    assert (c7["stok"], c7["parca_boyu_cm"]) == (_liste(L, "Trapez sac mahyası"), 80.0) == (ck07, 80.0)
    assert next(s["olcu"] for s in L if s["kalem"] == "Trapez sac mahyası") == "L 800"
    for k, on in (("CK-03", "Alın sacı"), ("CK-04", "Baş makas Z'si"), ("CK-01", "100'lük saçak omegası"), ("CK-02", "Saçak sacı")):
        assert say["kesim_plani"][k]["stok"] == _liste(L, on), k


@pytest.fixture(scope="module")
def tk04_r05(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(IE.with_name("TK04_r05.json"))
    kart = tmp_path_factory.mktemp("tk04_r05")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return {"d": veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04"), "say": _oku(kart / "TK04_kart_sayim.json"), "L": L}


def test_r05_anahtarsiz_eski_yol(tk04_r05):
    """`ana_makas` anahtarı olmayan çapraz cumba (TK-04 r05) eski yoldan: ana makaslar saçaktan saçağa (gövdenin önünden), kart modeli
    listeyle aynı, rehber r05'teki gibi (geometri hakemi, İE-15 K6 dördüncü tur: r06'ya geçen dosyada anahtarsız yolun koruması kalmıştı)."""
    say, L, d = tk04_r05["say"], tk04_r05["L"], tk04_r05["d"]
    assert say["kural_yok"] == [] and say["sema_hatasi"] == {"bugunku_ifc": 0, "kart_modeli": 0}
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    yerlesen = {"MA-01": "Makas (baş)", "MA-02": "Makas (orta)", "MA-05": "Yavru makas · cumba", "KP-03": "Trapez sac",
                "BT-01": "Baş makas betopanı", "DR-02": "Metal dere inişi aparatı"}
    assert {k: adet[k] for k in yerlesen} == {k: _liste(L, on) for k, on in yerlesen.items()} == {
        "MA-01": 2, "MA-02": 6, "MA-05": 2, "KP-03": 25, "BT-01": 9, "DR-02": 5}
    boyla = {"AS-01": "Aşık", "DR-01": "Metal dere", "CK-01": "100'lük saçak omegası", "CK-02": "Saçak sacı", "CK-03": "Alın sacı",
             "CK-04": "Baş makas Z'si", "CK-07": "Trapez sac mahyası"}
    assert {k: say["kesim_plani"][k]["stok"] for k in boyla} == {k: _liste(L, on) for k, on in boyla.items()} == {
        "AS-01": 43, "DR-01": 4, "CK-01": 6, "CK-02": 7, "CK-03": 11, "CK-04": 10, "CK-07": 13}
    assert {s["olcu"] for s in L if s["kalem"].startswith("Makas (")} == {"açıklık 8985"}
    W, DY = d["dis"]
    assert sorted((o["perp"], o["a0"], o["a1"]) for o in d["omega_duvar"] if o["tur"] == "sacak") == [(5, 416.5, W), (DY - 5, 0, W)]
    assert {(x["bas"], x["son"]) for x in d["makas"] if x["aile"] == "ana"} == {(-30.0, 928.5)}
    assert sorted(s["ad"] for s in d["sacak"]) == ["ana çatı arka saçağı", "ana çatı ön (cumbanın sağı) saçağı"]
    assert all("not" not in s for s in d["sacak"]) and len(d["dere"]["inisler"]) == 5
    kp = next(a for a in d["adimlar"] if a.get("ad") == "Trapez sac ve mahya")
    assert [r[1:3] for r in kp["rows"] if r[3:] == ["liste"]] == [["Trapez sac · ana çatı L 5100", "20 adet"], ["Trapez sac · cumba L 2410", "5 adet"],
                                                              ["Trapez sac mahyası L 1000", "13 adet"], ["Mahya bandı rulo 10 m", "2 adet"]]


@pytest.fixture(scope="module")
def tk04_r07(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _oku(IE.with_name("TK04_r07.json"))
    kart = tmp_path_factory.mktemp("tk04_r07")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return {"d": veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04"), "say": _oku(kart / "TK04_kart_sayim.json"), "L": L, "ie": ie, "kart": kart}


def test_r07_veranda_sacak_kadar_icerde(tk04_r07):
    """Lokman, 5 Kasım 2026 11:00: "veranda da saçak oturmadığı için verandayı 30cm saçak olacak şekilde içeri almamız gerekiyor … tam
    geldiği yerede bir tane 250cm kolon koyması gerekiyor" (İş Emri r07, kat planı sohbetinin; gövde L, ön kirişin dış yüzü 37,5, salon
    duvarında kolon 386,5). Çatı r06'nınkiyle aynı (ana çatının ayak izi 37,5 … 898,5); ana çatının ön saçağının altındaki kiriş 37,5'ta:
    saçak altı var, saçak omegası kirişin üstünde, sağ kalkan köşe kolonundan (önü saçak ucu), ön saçağın inişleri iki kolonda (sol uçtaki
    cumba ile verandanın köşesinde tek iniş; Lokman 12:51); makasın alt başlığı ve topuğundaki dikme kirişin üstünde. Ön kirişin kendisi (çizimde PC-36) burada sınanmaz."""
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element as E
    from motor import cati_capraz as CC
    from motor import geometry as G
    ie, say, L, d = tk04_r07["ie"], tk04_r07["say"], tk04_r07["L"], tk04_r07["d"]
    plan = G.kur(copy.deepcopy(ie))
    assert plan.girintili and ie["dikmeler"] == [[386.5, 37.5]]
    ana = next(q for q in CC.tanim(plan, copy.deepcopy(ie))["parcalar"] if q["rol"] == "ana")
    assert (ana["b"], ana["duvar_b"], ana["geri_cm"], ana["mahya"][0][1]) == ([37.5, 898.5], [37.5, 898.5], 7.5, 468.0)
    assert say["kural_yok"] == [] and say["sema_hatasi"] == {"bugunku_ifc": 0, "kart_modeli": 0}
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    assert {k: adet[k] for k in ("MA-01", "MA-02", "MA-05", "KP-03", "DR-02")} == {"MA-01": 2, "MA-02": 6, "MA-05": 2, "KP-03": 26, "DR-02": 6}
    assert {s["olcu"] for s in L if s["kalem"].startswith("Makas (")} == {"açıklık 8610"} and _liste(L, "Metal dere inişi aparatı") == 6
    # D-61 madde 3 (Lokman, kart 5 Kasım 22:49): ön kiriş iki kolonun arasında, yüzünden yüzüne (502 − 2 × 10); sağ kiriş 155,75 − 10
    assert sorted(s["olcu"] for s in L if s["kalem"].startswith("Kutu profil (kiriş)")) == ["L 1457,5", "L 4820"]
    # rehber kirişin boyunu listeden okur (D-28 madde 1): iki ucunda kolon olan ön kiriş L 482, liste satırına bağlı
    assert {k["bu"].split(":")[0]: k["liste"] for v in d["verandalar"] for k in v["kiris"]} == {
        "veranda · ön kiriş · L 482 cm": "Kutu profil (kiriş) 100 × 100 L 4820 · 1 adet",
        "veranda · sağ yan kiriş · L 145,75 cm": "Kutu profil (kiriş) 100 × 100 L 1457,5 · 1 adet"}
    f = ifcopenshell.open(str(tk04_r07["kart"] / "TK04_model.ifc"))
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)

    def uc(ad):
        v = ifcopenshell.geom.create_shape(st, next(e for e in f.by_type("IfcMember") if e.Name == ad)).geometry.verts
        b = 100 if max(abs(x) for x in v) < 50 else 1
        return round(min(v[1::3]) * b, 1), round(max(v[1::3]) * b, 1)
    asm = [a for a in f.by_type("IfcElementAssembly") if (E.get_pset(a, "PortatifEv_Kapsam") or {}).get("CatiParcasi") == "ana çatı"]
    assert len(asm) == 8 and {uc(f"{a.Name}_ALT_BASLIK") for a in asm} == {(37.5, 898.5)}
    assert {(x["bas"], x["son"], tuple(x["wl"])) for x in d["makas"] if x["aile"] == "ana"} == {(7.5, 928.5, (40.2, 895.8))}
    sa = {s["ad"]: s for s in d["sacak"]}
    on = sa["ana çatı ön (cumbanın sağı) saçağı"]
    assert "not" not in on and on["t0"] < on["t1"]
    assert sorted((o["perp"], o["a0"], o["a1"]) for o in d["omega_duvar"] if o["tur"] == "sacak") == [(42.5, 416.5, 888.5), (893.5, 0, 888.5)]
    K = {k["ad"]: k for k in d["kalkan"]}
    assert (K["ana çatı sağ kalkanı (MKS08)"]["duvar"]["A"], K["ana çatı sağ kalkanı (MKS08)"]["uc"]["A"]) == (37.5, 7.5)
    assert K["ana çatı sol kalkanı (MKS01)"]["duvar"]["A"] == -7.5
    ini = [i for i in d["dere"]["inisler"] if i["hat"] == "ana çatı ön (cumbanın sağı)"]
    assert sorted((i["duvar"], i["s"], i["sw"]) for i in ini) == [("veranda kolonu", 416.7, 391.5), ("veranda kolonu", 918.7, 883.5)]
    # cumba ile verandanın köşesindeki iniş köşenin iç tarafında: salon duvarının kolonu (386,5 … 396,5) cumbanın duvarına (386,5) dayalı
    assert ie["dikmeler"][0][0] == 386.5 and len(d["dere"]["inisler"]) == 6
    _kose_inisi(d)
