"""BK-12 PR-2 · Prefabrik yükleme listesi (`motor/prefabrik_liste.py`, kurallar `kurallar/liste/prefabrik.json`).

- PK-01 (AP-19) listesinin kilidi: satır başına grup, kalem, ölçü, adet ve aday (`veri/PK01_liste_kilidi.json`). Gerçek listeyle kıyas
  değildir; hesabın değişmediğini söyler.
- Kurallar dosyadan okunur: bir değer değişince adet değişir; her kuralın değeri, durumu ve kaynağı var. Kural kitabı `kitap_seti`'ndeki
  dondurulmuş setten okunur (`PORTMAN_KURALLAR` etkilemez). Kitabın her kuralı eşlenir: okunur, `kitapla_farkli`'da beyanlı ya da
  `kitaptan_okunmayan`'da nedeniyle.
- Kural bozma (geometri hakemi, BK-12 PR-2): PK-01 ve sentetik türevlerinde okunan her kural yaprağı bozulunca liste değişir; adedi değişen
  satırın yazısı (ölçü, formül ya da aday notu) da değişir; parça boyu değişince ölçü, bölen de birlikte değişir.
- Kural değeri kilidi (`veri/prefabrik_kural_kilidi.json`): okunan her yaprağın değeri. Bir değer değişince test düşer; kilidi yeniden yazmak
  bilinçli bir değişikliktir (`python testler/motor/test_prefabrik_liste.py --kilit`, gerekçesi iş emrine).
- Orta iniş (Lokman, 13 Ekim 15:10): uzunluğa bağlı; eşik kitabın 9 m'si, varsayım. 7.3'ün "her saçak hattına bir" kuralı aday sütununda.
- Pafta kipi Motor kipiyle aynı geometriden aynı adetleri verir; komut satırı JSON ve tek sayfalık Excel yazar.
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
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
PK01 = VERI / "PK01.json"
PAFTA_KATMANI = VERI / "PK01_pafta_katmani.json"
KILIT = VERI / "PK01_liste_kilidi.json"
DEGER_KILIDI = VERI / "prefabrik_kural_kilidi.json"
DURUMLAR = {"lokman", "excel", "uydurma", "varsayim", "pafta", "cizim", "aday"}   # kural kitabının değerleri + prefabrikin üçü


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(PK01))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


@pytest.fixture(scope="module")
def pk01(N, kurallar):
    return PL.liste(copy.deepcopy(N), kurallar, _oku(PAFTA_KATMANI))


def _satir(L: dict, kalem: str) -> dict:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, len(s))
    return s[0]


def test_pk01_kilidi(pk01):
    k = _oku(KILIT)
    assert pk01["ozet"] == k["ozet"]
    assert pk01["girdi_ozeti"] == k["girdi_ozeti"]
    assert [[s["grup"], s["kalem"], s["olcu"], s["adet"], s["aday"]] for s in pk01["satirlar"]] == k["satirlar"]


def test_pk01_motor_sayimlari(pk01):
    """Montaj paftasıyla aynı olduğu PR-1'de sınanan sayımlar listeye aynen geçer (50 pano, 38 H)."""
    g = pk01["girdi_ozeti"]
    assert (g["pano_dis"], g["pano_ic"]) == (30, 20)
    h = sum(_satir(pk01, k)["adet"] for k in ("H 100 (dış pano eki)", "H standart 60 (iç pano eki)", "3'lü H 100 × 100 × 60 (dış duvar T'si)",
                                               "3'lü H standart 60 (iç T)"))
    assert h == 38
    assert _satir(pk01, "H 100 (dış pano eki)")["pafta"] == 19      # pafta katmanı yerinde okunuyor


def test_pk01_aliciya_ait(pk01):
    """PK-01'de pencere, dış kapı, boya ve tesisat alıcıya ait: satır kalır, adet 0."""
    assert _satir(pk01, "Pencere grubu")["adet"] == 0
    dis_kapi = [s for s in pk01["satirlar"] if s["kalem"].startswith("Prefabrik çelik kapı")]
    assert len(dis_kapi) == 1 and dis_kapi[0]["adet"] == 0
    assert _satir(pk01, "Boya grubu ve mastik")["adet"] == 0
    assert _satir(pk01, "Sıhhi tesisat grubu")["adet"] == 0
    assert _satir(pk01, "Elektrik grubu")["dayanak"] == "Kural yok"     # PK-01 paftasında elektrik planı yok


def test_kurallar_dosyadan_okunur(N, kurallar):
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["kosebent"]["deger"] = 9
    k["prefabrik"]["kurallar"]["alt_cerceve_bolen_m"]["deger"] = 2.5
    L = PL.liste(copy.deepcopy(N), k)
    assert _satir(L, "Köşebent")["adet"] == 9
    assert _satir(L, "Köşebent")["formul"].startswith("sabit 9")
    s = _satir(L, "100'lük alt çerçeve")
    assert (s["adet"], s["olcu"]) == (13, "100 × 2500")              # dış çevre 32 m ÷ 2,5 (kuralla ÷ 3,75 → 9)
    assert s["formul"].endswith("÷ 2,5")


def test_ortak_degerler_kural_kitabindan(N, kurallar):
    """Kitapla aynı değerler (parça boyları, bindirmeler, levhalar, zayiatlar …) `kurallar.json`'dan okunur; prefabrik dosyası onları yinelemez.
    Geometri hakeminin denemesi: saçak sacı parçası 2,8 olunca ölçü, formül ve adet birlikte değişir."""
    yinelenmez = {"parca_boyu_m", "bindirme_m", "asik", "silte_adet_m2", "sandvic_panel_kapatma_m", "trapez_sac_kapatma_m", "levha_m2", "zayiat",
                  "bas_makas_z", "dere_kelepcesi_dere_basina", "inis", "inis_basina", "veranda_boardex", "ters_mahya_bolen_m", "bas_makas_z_bolen_m",
                  "mahya_bandi", "tesisat", "levha_kalinligi_mm", "cati_mudahale_kapagi"}
    assert not yinelenmez & set(kurallar["prefabrik"]["kurallar"])
    k = copy.deepcopy(kurallar)
    k["ortak"]["parca_boyu_m"]["sacak_saci"]["deger"] = 2.8
    L0, L1 = PL.liste(copy.deepcopy(N), kurallar), PL.liste(copy.deepcopy(N), k)
    s0, s1 = _satir(L0, "Saçak sacı (30'luk, 3'ü menfezli)"), _satir(L1, "Saçak sacı (30'luk, 3'ü menfezli)")
    assert s1["adet"] < s0["adet"]
    assert (s0["olcu"], s1["olcu"]) == ("300 × 2500", "300 × 2800")
    assert "÷ 2,3" in s0["formul"] and "÷ 2,6" in s1["formul"]


def test_kitap_seti_sabit(monkeypatch):
    """Kural kitabı prefabrik dosyasının sabitlediği dondurulmuş setten okunur; `PORTMAN_KURALLAR` (çelik için seçilen set) etkilemez."""
    R = PL.kurallari_oku()["prefabrik"]
    assert R["kitap_seti"].startswith("setler/") and (KOK / "kurallar" / "liste" / R["kitap_seti"]).is_file()
    taban = PL.kurallari_oku()["ortak"]["sema"]
    monkeypatch.setenv("PORTMAN_KURALLAR", str(KOK / "kurallar" / "liste" / "setler" / "0.12.json"))
    assert PL.kurallari_oku()["ortak"]["sema"] == taban


def test_levha_olcusu_alanla_celisirse_liste_uretilmez(N, kurallar):
    """Levha alanı kitaptan, ölçü ürünün adı: biri değişip öteki değişmezse liste üretilmez (adet ile ölçü çelişmesin)."""
    k = copy.deepcopy(kurallar)
    k["ortak"]["levha_m2"]["alcipan"]["deger"] = 2.88
    with pytest.raises(ValueError, match="1200 × 2500"):
        PL.liste(copy.deepcopy(N), k)


def test_kural_dosyasi_bicimi(kurallar):
    R = kurallar["prefabrik"]
    assert R["sema"].startswith("portman.prefabrik_liste/")
    assert list(R) == ["sema", "aciklama", "kitap_seti", "kurallar", "kitapla_farkli", "kitaptan_okunmayan"]
    for ad, v in R["kurallar"].items():
        assert set(v) == {"deger", "durum", "kaynak"}, ad
        assert v["durum"] in DURUMLAR, (ad, v["durum"])
        assert v["kaynak"].strip(), ad
    assert R["kurallar"]["inis_orta"]["deger"] in ("esik", "her_sacak")
    assert R["kurallar"]["inis_orta"]["durum"] == "varsayim"         # eşiği Lokman vermedi (geometri hakemi, bulgu 2)


def _yol(kok: dict, yol: str):
    v = kok
    for a in yol.split("."):
        v = v[a]
        if isinstance(v, dict) and "deger" in v:
            v = v["deger"]
    return v


# Kitabın Lokman'ın kararıyla çelişen ve prefabrikte başka yazılan değerleri: Lokman'ın kararını bekler (geometri hakemi, 1.–5. tur).
# Alçıpan vidasının levhaları kitabın Lokman kararı değil, çalışma kitabının notu; PK-03'ün gerçek listesi kitapla tuttuğu için soruya girer.
KARAR_BEKLEYEN = {"Tek kat çatı paneli kapatması", "Metal kiremit kapatması", "Çatı paneli boyu", "Sandviç panel kapaması", "Trapez sac mahyası",
                  "Veranda tavanı", "Pencere alıcıya aitken vida ve mastik", "Ters mahya kenar kutusu", "Müdahale kapakları", "Duvar dibi",
                  "Dayson", "Silikonize mastik", "Buat kasa", "NYM kablo uzunluğu", "Alçıpan vidasının levhaları",
                  "Panel çatının kenarları", "Tek kat panel kapaması"}


def _kitap_yollari(b: dict) -> list[str]:
    return b["kitap"] if isinstance(b["kitap"], list) else [b["kitap"]]


def test_kitapla_farkli_beyanlari(kurallar):
    """Kitaptan farklı değer, yöntem, kalem ya da kapsam beyanlıdır: her kayıt iki yanda da bulunur, değer kayıtlarında değerler gerçekten
    farklıdır (eşitlenince kayıt kalkar, değer kitaptan okunur), kitapla aynı adı taşıyan her prefabrik kuralı beyan edilmiştir ve
    Lokman'ın kararını bekleyenler işaretlidir."""
    R, kitap = kurallar["prefabrik"], kurallar["ortak"]
    beyan = R["kitapla_farkli"]
    for b in beyan:
        assert set(b) == {"konu", "prefabrik", "kitap", "tur", "karar_bekliyor", "not"}, b
        assert b["tur"] in {"deger", "yontem", "kalem", "kapsam"}, b
        assert isinstance(b["karar_bekliyor"], bool) and b["not"].strip(), b
        k_ = [_yol(kitap, y) for y in _kitap_yollari(b)]
        if b["prefabrik"] is not None:
            p_ = _yol(R["kurallar"], b["prefabrik"])
            if b["tur"] == "deger":
                assert p_ != k_[0], b["konu"]
    assert len({b["konu"] for b in beyan}) == len(beyan)
    beyanli = {b["prefabrik"].split(".")[0] for b in beyan if b["prefabrik"]}
    ayni_ad = set(R["kurallar"]) & set(kitap)
    assert ayni_ad <= beyanli, ayni_ad - beyanli
    assert {b["konu"] for b in beyan if b["karar_bekliyor"]} == KARAR_BEKLEYEN
    assert {"Dere kapağı", "Çatı OSB'si zayiatı", "Boya", "Vida", "Elektrik"} <= {b["konu"] for b in beyan}


def _kitap_kurallari(kitap: dict) -> list[tuple]:
    """Kitabın kuralları: değeri ve durumu ya da kaynağı olan her düğüm (ör. ("parca_boyu_m", "mahya"), ("vida",))."""
    out = []

    def gez(v, yol):
        if isinstance(v, dict):
            if "deger" in v and ("durum" in v or "kaynak" in v):
                out.append(yol)
                return
            for a, x in v.items():
                gez(x, yol + (a,))
    gez(kitap, ())
    return out


def test_kitabin_her_kurali_eslenir(bozma, kurallar):
    """Kitabın her kuralı üç yerden birindedir: prefabrik okur (bozma testinin izi), `kitapla_farkli`'da beyanlıdır ya da `kitaptan_okunmayan`'da
    nedeniyle durur. Okunmayan diye yazılan bir kural okunmaz; her yol kitapta vardır (geometri hakemi, 2. tur: beyan edilmemiş çelişki kalmasın)."""
    okunan, _ = bozma
    R, kitap = kurallar["prefabrik"], kurallar["ortak"]
    okunan_k = {y[1:] for y in okunan if y[0] == "ortak"}
    farkli = {tuple(y.split(".")) for b in R["kitapla_farkli"] for y in _kitap_yollari(b)}
    okunmayan = [tuple(o["kitap"].split(".")) for o in R["kitaptan_okunmayan"]]
    for o in R["kitaptan_okunmayan"]:
        assert set(o) == {"kitap", "neden"} and o["neden"].strip(), o
    for y in farkli | set(okunmayan):
        _yol(kitap, ".".join(y))                                    # yol kitapta var
    ust = lambda a, b: a == b[:len(a)]                              # noqa: E731
    eslenmeyen = []
    for kr in _kitap_kurallari(kitap):
        if any(ust(kr, o) for o in okunan_k):
            continue
        if any(ust(kr, f) or ust(f, kr) for f in farkli):
            continue
        if any(ust(o, kr) for o in okunmayan):
            continue
        eslenmeyen.append(".".join(kr))
    assert eslenmeyen == []
    okunan_okunmayan = sorted(".".join(o) for o in okunmayan if any(ust(o, y) or ust(y, o) for y in okunan_k))
    assert okunan_okunmayan == []


def test_orta_inis_uzunluga_bagli(kurallar):
    """Beşik ana çatı, saçak hatları 8 ve 10 m: eşik (9 m) yalnız 10 m'lik hatta orta iniş koyar; 7.3'ün kuralı ikisine de."""
    N = {"kaynak": "pafta", "H0": 250.0, "W": 600.0, "D": 900.0, "t_dis": 10.0, "panolar": [], "ekler": [], "koseler": {"dis": 4},
         "dikmeler": 0, "veranda_kirisleri_cm": [], "kapali": [], "acik": [], "ozellikler": {}, "alici_ait": {},
         "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 600.0, "boy_cm": 900.0, "egim_yuzde": 33.0, "sacak_cm": 30.0,
                   "sacak_hatlari_m": [8.0, 10.0]}]}
    esik = _satir(PL.liste(PL.model_pafta(copy.deepcopy(N)), kurallar), "Metal dere inişi aparatı")
    assert (esik["adet"], esik["aday"]) == (5, 6)
    assert esik["dayanak"] == "Varsayım (uzunluğa bağlı: Lokman 13.10 15:10; eşik 9 m kural kitabından)"
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["inis_orta"]["deger"] = "her_sacak"
    her = _satir(PL.liste(PL.model_pafta(copy.deepcopy(N)), k), "Metal dere inişi aparatı")
    assert (her["adet"], her["aday"]) == (6, 5)
    assert her["dayanak"] == "Kural (Lokman 13.10 14:35, R3)"
    L = PL.liste(PL.model_pafta(copy.deepcopy(N)), kurallar)
    assert _satir(L, "Açık dirsek")["adet"] == 2 * esik["adet"]          # iniş başına parçalar varsayılan inişe göre


# ── kural bozma (geometri hakemi, bulgu 3 ve 4) ─────────────────────────────────
def _varyantlar(N: dict, pf: dict) -> dict:
    """PK-01 ve sentetik türevleri: PK-01'de koşmayan yolları açar (gerçek proje değildir; öteki inceleme projelerinin girdileri PR-3'te gelir).
    bizde: alıcıya ait kalem yok, fugalı cephe, iç cephe alçıpanı, metal iniş, elektrik planı, kubbe, vasistas sınırının iki yanında pencere;
    kisa_uzun: 8 ve 10 m saçaklı beşik (orta iniş); ters100 ve ters60: ters tavan, trapez / kiremit + OSB + nem, 100'lük iç duvar, cumba,
    özel köşe, özel büküm; tekyon: tek yön çatı, tek kat panel, iç duvarsız, ıslak hacimsiz, makassız açık veranda çatısı."""
    def tur(n, **d):
        n = copy.deepcopy(n)
        n.update(d)
        return n
    oz = N["ozellikler"]
    bizde_oz = {**oz, "Dış Kapı": "Standart", "Dış Cephe Boya": "Standart", "İç Cephe Boya": "Standart", "Pencere Rengi": "Beyaz",
                "Açıklama": "fugalı cephe, iç cephede alçıpan kaplama", "Yağmur İniş Borusu": "Metal"}
    elektrik = {"elektrik": {a: {"adet": n} for a, n in (("priz_tekli", 6), ("priz_cift", 4), ("anahtar_tekli", 5), ("anahtar_cift", 2),
                                                        ("uydu_prizi", 1), ("zil", 1), ("tavan_armaturu", 7), ("glop", 2), ("sigorta_kutusu", 1))}}
    kubbe = {"ad": "kubbe", "tip": "besik", "kubbe": True, "aciklik_cm": 200.0, "boy_cm": 200.0, "egim_yuzde": 33.0, "sacak_cm": 30.0}
    cumba = {"ad": "cumba", "tip": "besik", "aciklik_cm": 251.0, "boy_cm": 150.0, "egim_yuzde": 33.0, "sacak_cm": 30.0, "kalkan": 1,
             "makas_kosu_cm": 130.0}
    ana = N["cati"][0]
    pen = [i for i, p in enumerate(N["panolar"]) if p["aciklik"] and p["aciklik"]["tur"] == "pencere"]
    dolu = next(i for i, p in enumerate(N["panolar"]) if p["duvar"] == "dis" and not p["aciklik"])
    pan_b = copy.deepcopy(N["panolar"])
    pan_b[pen[0]]["aciklik"]["olcu"], pan_b[pen[1]]["aciklik"]["olcu"] = "80/50", "50/80"   # vasistas sınırının iki yanı
    pan_b[pen[2]]["aciklik"]["olcu"] = "120x70"                  # fugalı latada artan 0,30 m: artık eşiğinin üstünde
    pan_b[dolu]["boy"] = 2 * PL.MOD + 0.3                        # modül katına 3 mm: sipariş boyu toleransı
    kisa_uzun = {"kaynak": "pafta", "H0": 250.0, "W": 600.0, "D": 900.0, "t_dis": 10.0, "panolar": [], "ekler": [], "koseler": {"dis": 4},
                 "dikmeler": 0, "veranda_kirisleri_cm": [], "kapali": [], "acik": [], "ozellikler": {}, "alici_ait": {},
                 "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 600.0, "boy_cm": 900.0, "egim_yuzde": 33.0, "sacak_cm": 30.0,
                           "sacak_hatlari_m": [8.0, 10.0]}]}
    veranda = dict(ana, ad="veranda", acik=True, makas_yok=True, aciklik_cm=200.0, boy_cm=300.0, kalkan=0, makas_kosu_cm=280.0)
    return {
        "pk01": (N, pf),
        "bizde": (tur(N, alici_ait={}, ozellikler=bizde_oz, cati=N["cati"] + [kubbe], panolar=pan_b), {**pf, **elektrik}),
        "kisa_uzun": (PL.model_pafta(kisa_uzun), None),
        "ters100": (tur(N, panolar=[dict(p, kal_mm=100) if p["duvar"] == "ic" else p for p in N["panolar"]],
                        ozellikler={**oz, "Tavan": "Ters tavan", "Çatı Kaplaması": "Trapez sac"}, koseler={**N["koseler"], "ozel": 1},
                        ozel_bukum={"sacak": 2, "alin": 2}, kolon_boylari_cm=[260.0] * N["dikmeler"], ic_kalan_dis_duvar_m=3.0,
                        cati=N["cati"] + [cumba]), pf),
        "ters60": (tur(N, ozellikler={**oz, "Tavan": "Ters tavan", "Çatı Kaplaması": "Metal kiremit, OSB ve nem bariyeri"}), pf),
        "tekyon": (tur(N, panolar=[p for p in N["panolar"] if p["duvar"] == "dis"], ekler=[e for e in N["ekler"] if e["duvar"] == "dis"],
                       kapali=[dict(m, tur="oda") for m in N["kapali"]], ozellikler={**oz, "Çatı Kaplaması": "Tek kat panel"},
                       cati=[dict(ana, tip="tek_yon"), veranda]), pf),
    }


class _Izli(dict):
    """Okunan kural yapraklarını kaydeden sözlük (yalnız `[]` ile okuma)."""
    def __init__(self, d, yol, iz):
        super().__init__(d)
        self._yol, self._iz = yol, iz

    def __getitem__(self, a):
        v = super().__getitem__(a)
        if isinstance(v, dict):
            return _Izli(v, self._yol + (a,), self._iz)
        self._iz.add(self._yol + (a,))
        return v


def _okunanlar(monkeypatch, calistir) -> set:
    iz, asil_pr, asil_or, asil_dt = set(), PL._pr, PL._ortak, PL._dt

    def sar(v, yol):
        if isinstance(v, dict):
            return _Izli(v, yol, iz)
        iz.add(yol)
        return v
    with monkeypatch.context() as m:
        m.setattr(PL, "_pr", lambda k, yol: sar(asil_pr(k, yol), ("prefabrik",) + tuple(yol.split("."))))
        m.setattr(PL, "_ortak", lambda k, *yol: sar(asil_or(k, *yol), ("ortak",) + yol))
        m.setattr(PL, "_dt", lambda k, *yol: sar(asil_dt(k, *yol), ("duvar_tipleri",) + yol))
        calistir()
    return iz


def _boz(v):
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v * 2 + 1
    if isinstance(v, float):
        return round(v * 3.1 + 0.37, 4)
    if isinstance(v, str):
        return {"esik": "her_sacak", "her_sacak": "esik"}.get(v, v + "0")
    v = copy.deepcopy(v)
    if v and isinstance(v[0], list) and isinstance(v[0][-1], int):   # takım listesi: ilk kalemin adedi
        v[0][-1] = v[0][-1] * 2 + 1
    elif v and isinstance(v[0], list):                          # adı ve kitap anahtarı olan takım: ilk kalemin adı
        v[0][0] = v[0][0] + "0"
    elif v and v[0].startswith("L "):                           # parça boyu listesi
        v = [x + "0" for x in v]
    else:                                                       # ad listesi: ilk ad çıkar
        v = v[1:]
    return v


def _koy(K: dict, yol: tuple, yeni) -> None:
    kok, *yol = yol
    if kok == "prefabrik":
        sahip, a, v = K["prefabrik"]["kurallar"][yol[0]], "deger", K["prefabrik"]["kurallar"][yol[0]]["deger"]
        yol = yol[1:]
    else:
        sahip, a, v = None, None, K[kok]
    for b in yol:
        sahip, a, v = v, b, v[b]
        if kok == "ortak" and isinstance(v, dict) and "deger" in v:
            sahip, a, v = v, "deger", v["deger"]
    sahip[a] = yeni


def _al(K: dict, yol: tuple):
    kok, *yol = yol
    return _yol(K["prefabrik"]["kurallar"] if kok == "prefabrik" else K[kok], ".".join(yol))


def _harita(L: dict) -> dict:
    say, h = Counter(), {}
    for s in L["satirlar"]:
        a = (s["grup"], s["kalem"])
        h[a + (say[a],)] = s
        say[a] += 1
    return h


# Parça boyu ya da levha olan yapraklar: bozulunca bir satırın ölçüsü değişmeli (ya da levha denetimi listeyi durdurmalı)
OLCULU = {("prefabrik", "trapez_mahyasi_parca_m"), ("prefabrik", "kapama", "sandvic_parca_m"), ("prefabrik", "fugali_cephe", "lata_boyu_m"),
          ("prefabrik", "fugali_cephe", "lata_kisa_boyu_m"), ("prefabrik", "duvar_omegasi_100_bolen_m"), ("prefabrik", "sacak_omegasi_bolen_m"),
          ("prefabrik", "bas_makas_omegasi_bolen_m"), ("prefabrik", "alt_cerceve_bolen_m"), ("prefabrik", "cektirme_u_100_aday", "boy_cm"),
          ("prefabrik", "bas_makas_betopani", "levha_m2"), ("prefabrik", "siparis_boyu", "modul_siparis_mm"), ("ortak", "bas_makas_z", "parca_boyu_m"),
          ("prefabrik", "omega_kapak", "parca_m"), ("prefabrik", "veranda_tavani", "kalinlik_mm"), ("duvar_tipleri", "tipler", "PE-IC-60", "anma_mm")}


@pytest.fixture(scope="module")
def bozma(N, kurallar):
    """Her okunan kural yaprağı bozulur; döner: (okunanlar, {yol: [(varyant, taban listesi, bozuk liste ya da hata)]})."""
    V = _varyantlar(N, _oku(PAFTA_KATMANI))
    taban = {ad: PL.liste(copy.deepcopy(n), kurallar, pf) for ad, (n, pf) in V.items()}
    mp = pytest.MonkeyPatch()
    try:
        okunan = _okunanlar(mp, lambda: [PL.liste(copy.deepcopy(n), kurallar, pf) for n, pf in V.values()])
    finally:
        mp.undo()
    sonuc = {}
    for yol in sorted(okunan):
        K = copy.deepcopy(kurallar)
        _koy(K, yol, _boz(_al(kurallar, yol)))
        sonuc[yol] = []
        for ad, (n, pf) in V.items():
            try:
                sonuc[yol].append((ad, taban[ad], PL.liste(copy.deepcopy(n), K, pf)))
            except ValueError as e:                             # levha denetimi: çelişen liste üretilmez
                sonuc[yol].append((ad, taban[ad], e))
    return okunan, sonuc


def test_her_prefabrik_kurali_okunur(bozma, kurallar):
    okunan, _ = bozma
    for ad, kr in kurallar["prefabrik"]["kurallar"].items():
        yapraklar = [(ad, a) for a in kr["deger"]] if isinstance(kr["deger"], dict) else [(ad,)]
        for y in yapraklar:
            assert any(o[1:1 + len(y)] == y for o in okunan if o[0] == "prefabrik"), y


def test_bozulan_her_kural_listeyi_degistirir(bozma):
    """Okunan her kural yaprağı (prefabrik ve kitap) PK-01 ya da türevlerinden birinde ölçüyü, adedi ya da adayı değiştirir (kapsanmayan yok)."""
    _, sonuc = bozma
    kapsanmayan = []
    for yol, kosular in sonuc.items():
        def degisti(t, b):
            if isinstance(b, Exception):
                return True
            T, B = _harita(t), _harita(b)
            return T.keys() != B.keys() or any((T[a]["olcu"], T[a]["adet"], T[a]["aday"]) != (B[a]["olcu"], B[a]["adet"], B[a]["aday"]) for a in T)
        if not any(degisti(t, b) for _ad, t, b in kosular):
            kapsanmayan.append(".".join(yol))
    assert kapsanmayan == []


def test_adet_degisince_yazi_da_degisir(bozma):
    """Bir kural bozulunca adedi ya da adayı değişen her satırın ölçüsü, formülü ya da aday notu da değişir: yazı koda gömülü kalmaz."""
    _, sonuc = bozma
    bayat = set()
    for yol, kosular in sonuc.items():
        for ad, t, b in kosular:
            if isinstance(b, Exception):
                continue
            T, B = _harita(t), _harita(b)
            for a in T.keys() & B.keys():
                x, y = T[a], B[a]
                if (x["adet"], x["aday"]) != (y["adet"], y["aday"]) and (x["olcu"], x["formul"], x["aday_notu"]) == (y["olcu"], y["formul"], y["aday_notu"]):
                    bayat.add((".".join(yol), ad, a[1]))
    assert sorted(bayat) == []


def test_parca_boyu_degisince_olcu_degisir(bozma, kurallar):
    """Parça boyu ve levha kuralları ölçü sütununa yazılır: bozulunca bir satırın ölçüsü değişir ya da levha denetimi listeyi durdurur. Ölçüsü
    değişen ve adedi bölmeyle bulunan satırın adedi ya da formülü de değişir: bölen parça boyundan kopmaz (geometri hakemi, 2. tur: tavan
    omegası "60 × 5248", "÷ 3,65 + 5")."""
    okunan, sonuc = bozma
    _al_taban = lambda y: _al(kurallar, y)                       # noqa: E731
    olculu = OLCULU | {y for y in okunan if y[0] == "ortak" and y[1] in ("parca_boyu_m", "levha_m2")}
    for yol in olculu:
        assert yol in sonuc, yol
        def olcu_degisti(t, b):
            if isinstance(b, Exception):
                return True
            T, B = _harita(t), _harita(b)
            return T.keys() != B.keys() or any(T[a]["olcu"] != B[a]["olcu"] for a in T)
        assert any(olcu_degisti(t, b) for _ad, t, b in sonuc[yol]), yol
        if yol[-1].endswith("_m") or yol[1] == "parca_boyu_m":     # metre: eski boy (mm) ölçüde kaldıysa ve adet değiştiyse yazı bayat
            eski = PL.mm_m(_al_taban(yol))
            for _ad, t, b in sonuc[yol]:
                if isinstance(b, Exception):
                    continue
                T, B = _harita(t), _harita(b)
                for a in T.keys() & B.keys():
                    if T[a]["adet"] != B[a]["adet"] and eski in T[a]["olcu"] and T[a]["olcu"] == B[a]["olcu"]:
                        pytest.fail(f"{'.'.join(yol)}: {a[1]} ölçüsü {T[a]['olcu']} kaldı, adet {T[a]['adet']} → {B[a]['adet']}")
                    x, y = T[a], B[a]
                    if x["olcu"] != y["olcu"] and "÷" in x["formul"] and (x["adet"], x["formul"]) == (y["adet"], y["formul"]):
                        pytest.fail(f"{'.'.join(yol)}: {a[1]} ölçüsü {x['olcu']} → {y['olcu']}, adet ve formül aynı ({x['formul']})")
                    if x["olcu"] != y["olcu"] and "÷" in x["aday_notu"] and (x["aday"], x["aday_notu"]) == (y["aday"], y["aday_notu"]):
                        pytest.fail(f"{'.'.join(yol)}: {a[1]} ölçüsü {x['olcu']} → {y['olcu']}, aday ve notu aynı ({x['aday_notu']})")


def _deger_kilidi(okunan: set, kurallar: dict) -> dict:
    """Okunan değerler ve beyanların listesi (konu ve karar bayrağı; kitaptan okunmayanların yolu): bir beyan sessizce kalkmaz (hakem, 3. tur)."""
    R = kurallar["prefabrik"]
    return {"kitap_seti": R["kitap_seti"], "degerler": {".".join(y): _al(kurallar, y) for y in sorted(okunan)},
            "kitapla_farkli": sorted([b["konu"], b["karar_bekliyor"]] for b in R["kitapla_farkli"]),
            "kitaptan_okunmayan": sorted(b["kitap"] for b in R["kitaptan_okunmayan"])}


def test_kural_degerleri_kilitli(bozma, kurallar):
    """Okunan her kural yaprağının değeri kilitlidir (prefabrik, kitap seti ve duvar tipleri): bozma testleri kodun kurala duyarlı olduğunu,
    bu kilit kuralın değişmediğini söyler. PK-01'in kilidi bir değer değişikliğini her zaman görmez (geometri hakemi, 2. tur)."""
    okunan, _ = bozma
    simdi, kilit = _deger_kilidi(okunan, kurallar), _oku(DEGER_KILIDI)
    assert simdi["kitap_seti"] == kilit["kitap_seti"]
    assert (simdi["kitapla_farkli"], simdi["kitaptan_okunmayan"]) == (kilit["kitapla_farkli"], kilit["kitaptan_okunmayan"]), "beyan değişti; --kilit"
    farklar = sorted(set(simdi["degerler"]) ^ set(kilit["degerler"])) + sorted(
        y for y in simdi["degerler"].keys() & kilit["degerler"].keys() if simdi["degerler"][y] != kilit["degerler"][y])
    assert farklar == [], "kural değeri değişti; bilerek değiştiyse kilidi yeniden yaz (--kilit) ve gerekçeyi iş emrine yaz"


def test_pafta_kipi_motor_kipiyle_ayni(N, kurallar):
    """Motor'un geometrisi `yapi_pafta` biçiminde verilince aynı adetler çıkar; değişen yalnız kaynak yazısı."""
    yp = {k: v for k, v in copy.deepcopy(N).items() if k not in ("kaynak", "veranda_kenarlari_cm")}
    yp["veranda_kirisleri_cm"] = [x - 10 for x in N["veranda_kenarlari_cm"]]
    Lm = PL.liste(copy.deepcopy(N), kurallar)
    Lp = PL.liste(PL.model_pafta(yp), kurallar)
    assert [(s["kalem"], s["olcu"], s["adet"], s["aday"]) for s in Lm["satirlar"]] == [(s["kalem"], s["olcu"], s["adet"], s["aday"]) for s in Lp["satirlar"]]
    assert Lp["girdi_ozeti"]["geometri"] == "pafta"


def test_karar_bekleyen_satirlar(pk01, N, kurallar):
    """Hesabında Lokman'ın kararını bekleyen değeri ya da kuralı kullanan satır konuyu taşır (türeyen vida, bant, kelepçe, iniş dahil); karar
    verilince (bayrak kalkınca) işaret de kalkar. PK-01'de yedi konu, sekiz satır (CIO kıyası, 18 Ekim: Patron'un baktığı Excel'de görünmüyordu;
    geometri hakemi, 7. ve 8. tur: panelli çatının dere ve kenarları, türev satırlar, acil kapak)."""
    isaretli = {s["kalem"]: s["karar_bekliyor"] for s in pk01["satirlar"] if s["karar_bekliyor"]}
    assert isaretli == {"Veranda tavan Boardex": ["Veranda tavanı"], "Sandviç panel (100 cm kapatır) · ana çatı": ["Çatı paneli boyu"],
                        "Sandviç panel kapaması": ["Sandviç panel kapaması"],
                        "Prefabrik pencere vidası (4,8 × 70)": ["Pencere alıcıya aitken vida ve mastik"],
                        "Alçıpan vidası": ["Alçıpan vidasının levhaları"], "Trapez vida 5,5 × 110 (sandviç panel)": ["Çatı paneli boyu"],
                        "Çatı müdahale kapağı": ["Müdahale kapakları"], "Dayson (çatı renginde)": ["Dayson"]}
    assert set().union(*isaretli.values()) <= KARAR_BEKLEYEN
    V = {ad: PL.liste(copy.deepcopy(n), kurallar, pf) for ad, (n, pf) in _varyantlar(N, _oku(PAFTA_KATMANI)).items() if ad in ("tekyon", "ters100")}
    pck = {s["kalem"] for s in V["tekyon"]["satirlar"] if "Panel çatının kenarları" in s["karar_bekliyor"]}
    assert pck == {"Metal dere", "Dere kelepçesi", "Metal dere inişi aparatı", "70 mm PVC dere iniş borusu", "Açık dirsek", "Kapalı dirsek",
                   "PVC iniş kelepçesi", "Dere kapağı",                # makassız açık veranda: kitapta saçakta dere (PK-07'de dere 6 → 7)
                   "100'lük saçak omegası", "Saçak sacı (30'luk, 3'ü menfezli)", "Alın sacı (30'luk)"}   # kitapta özel büküm, sundurma kapama
    n, pf = _varyantlar(N, _oku(PAFTA_KATMANI))["tekyon"]
    n = copy.deepcopy(n)
    n["cati"][1].update(acik=False, dere_yok=True)                       # paftası deresiz makassız parça: kitapta yine saçakta dere
    assert "Panel çatının kenarları" in _satir(PL.liste(n, kurallar, pf), "Metal dere")["karar_bekliyor"]
    assert _satir(V["tekyon"], "Trapez vida 5,5 × 76 (tek kat panel)")["karar_bekliyor"] == ["Çatı paneli boyu", "Tek kat çatı paneli kapatması"]
    assert _satir(V["ters100"], "Mahya bandı")["karar_bekliyor"] == ["Trapez sac mahyası"]
    assert not any("Panel çatının kenarları" in s["karar_bekliyor"] for s in pk01["satirlar"])
    k = copy.deepcopy(kurallar)
    for b in k["prefabrik"]["kitapla_farkli"]:
        if b["konu"] == "Dayson":
            b["karar_bekliyor"] = False
    L = PL.liste(copy.deepcopy(N), k, _oku(PAFTA_KATMANI))
    assert _satir(L, "Dayson (çatı renginde)")["karar_bekliyor"] == [] and _satir(L, "Veranda tavan Boardex")["karar_bekliyor"] == ["Veranda tavanı"]
    k["prefabrik"]["kitapla_farkli"] = [b for b in k["prefabrik"]["kitapla_farkli"] if b["konu"] != "Dayson"]
    with pytest.raises(ValueError, match="Dayson"):                  # satırın bağlandığı konu beyandan çıkarsa liste üretilmez
        PL.liste(copy.deepcopy(N), k, _oku(PAFTA_KATMANI))


def test_komut_satiri(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    assert PL.main([str(PK01), str(tmp_path), "--pafta", str(PAFTA_KATMANI)]) == 0
    L = _oku(tmp_path / "PK01_liste.json")
    assert L["kod"] == "PK-01" and L["ozet"]["satir"] == len(L["satirlar"]) == 93
    assert L["kural_seti"]["prefabrik"] == "portman.prefabrik_liste/1.0"
    wb = openpyxl.load_workbook(tmp_path / "PK01_liste.xlsx")
    assert wb.sheetnames == ["Liste"] and wb["Liste"].max_row == 93 + 2
    d = {r[1]: r[5] for r in wb["Liste"].iter_rows(min_row=3, values_only=True)}
    assert d["Dayson (çatı renginde)"] == "Şablon formülü (O18) · karar bekliyor (Dayson)" and d["Poliüretan köpük"] == "Şablon formülü (O18)"
    with pytest.raises(SystemExit):
        PL.main([str(tmp_path)])                                     # ne İş Emri ne --yapi


if __name__ == "__main__" and sys.argv[1:] == ["--kilit"]:      # kural değeri kilidini yeniden yazar (bilinçli değişiklik)
    _k = PL.kurallari_oku()
    _V = _varyantlar(PL.model_motor(_oku(PK01)), _oku(PAFTA_KATMANI))
    _mp = pytest.MonkeyPatch()
    try:
        _ok = _okunanlar(_mp, lambda: [PL.liste(copy.deepcopy(n), _k, pf) for n, pf in _V.values()])
    finally:
        _mp.undo()
    DEGER_KILIDI.write_text(json.dumps({"aciklama": "BK-12 PR-2: prefabrik listenin okuduğu kural yapraklarının değeri (test_kural_degerleri_kilitli). "
                                        "Elle düzenlenmez; `python testler/motor/test_prefabrik_liste.py --kilit` yazar.", **_deger_kilidi(_ok, _k)},
                                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(DEGER_KILIDI, len(_ok))
