"""D-91 (İE-40) · Havuz evinin dış duvarındaki özel ölçülü panolar standart panoya: AP-07'nin iki standart hâli (PA-28, PA-29) ve
hakemin standart hâl kipi. LLM'siz, Postgres'siz.

Lokman, 14 Kasım 2026 UTC: 09:46 "dış panolarda özel ölçü varsa o iki aks arasındaki panoları standart ölçümüze çek"; 09:58:53 kartı
"En yakın standart"; 10:01:43 "aslında kısaltta olmuş ... bence ikisinide havuza al"; 10:05:24 "evet 3 de havuza girsin"; 10:10:11
kartı "Kural denetime girsin" (oda, pencere, kapı kaynak evle aynı; dış duvarda özel pano yok (köşedeki 120,5 ve 57,75 özel sayılmaz);
ölçü her yönde en çok 62,75 cm değişir).
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin.katalog import SABLON_DIR, havuz_kayitlari  # noqa: E402

D91 = (KOK / "KARARLAR" / "D-91.md").read_text(encoding="utf-8")
KAYNAK = "testler/havuz/is_emirleri/AP07.json"                                    # PA-27 (D-87)
# kod → (kaynak İş Emri, dış ölçü cm, brüt m², dört hat: sağ duvar, girinti duvarı, salonun ön duvarı, yatak odasının ön duvarı)
HALLER = {
    "PA28": ("testler/havuz/is_emirleri/AP07_STD45.json", (763.0, 710.25), 45.70, (758.0, 318.75, 512.0, 700.25)),   # en yakın
    "PA29": ("testler/havuz/is_emirleri/AP07_STD40.json", (700.25, 647.5), 39.61, (695.25, 256.0, 512.0, 637.5)),    # kısalt
}
ESKI_HATLAR = (745.0, 295.0, 535.0, 680.0)                                        # AP-07'nin ızgara dışı dört hattı (arka-sol çerçevesi)
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}
SOZLER = ('"En yakın standart"', "aslında kısaltta olmuş", "evet 3 de havuza girsin", '"Kural denetime girsin"',
          "dış panolarda özel ölçü varsa o iki aks arasındaki panoları standart ölçümüze çek")


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _kart() -> dict:
    return HH.kartlar()["AP-07"]


def test_karar_dosyasi():
    """Karar dosyası Lokman'ın sözlerini, kartların saatini ve iki evi yazar (projeler kodla; CLAUDE.md › soru 15)."""
    for s in SOZLER:
        assert s in D91, s
    for saat in ("09:58:53", "10:01:43", "10:05:24", "10:10:11", "10:34:26", "11:18:03"):
        assert saat in D91, saat
    for kod, (kaynak, *_) in HALLER.items():
        assert f"| PA-{kod[2:]} | AP-07 | `{kaynak}` |" in D91


def test_hakem_sabitleri():
    """Kartın sayıları hakemde: 62,75 cm sınır; standart pano 125,5 / 62,75 (+ 251 pencereli pano); köşe payı 120,5 / 57,75."""
    assert HH.TOL_STANDART_CM == 62.75 and HH.KOSE_PAYI_CM == (120.5, 57.75)
    assert HH.STANDART_PANO_CM == (125.5, 62.75, 251.0)


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kayit(kod):
    """Kayıt hakemin standart hâl kipinden geçti; ölçüm şablonla yeniden koşunca aynı; dışta özel pano 0."""
    a = KAYIT[kod]
    kk = a["kaynak"]["kart_kiyasi"]
    assert (kk["kart"], kk["sonuc"], kk["kip"], a["kaynak"]["karar"]) == ("AP-07", "geçti", "standart_hal", "D-91")
    assert kk["kart_sha256"] == _kart()["kart_sha256"] and kk["kaynak_is_emri"] == KAYNAK
    assert kk["kaynak_sha256"] == hashlib.sha256((KOK / KAYNAK).read_bytes()).hexdigest()   # kaynak değişirse kayıt yeniden yazılır
    sab = json.loads((SABLON_DIR / a["sablon"]).read_text(encoding="utf-8"))
    bulgular, olc = HH.denetle_standart(sab, _kart(), _ie(KAYNAK))
    assert bulgular == [] and olc == kk["olcum"] and olc["dis_ozel_pano"] == 0, (kod, bulgular)
    kaynak, olcu, brut, _ = HALLER[kod]
    assert tuple(a["ozet"]["dis_olcu_cm"]) == olcu and a["ozet"]["brut_m2"] == brut
    assert a["kaynak"]["dosya"] == kaynak and a["oda_programi"] == "1+1" and a["katalog_m2"] == round(brut)


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kaynakla_ayni(kod):
    """Standart hâl kaynak İş Emri'sidir: odalar, açıklıklar, sundurma, dikmeler, çatı tipi ve müşteri seçimleri aynı; değişen yalnız dört
    hat (mahallerin ve girintinin köşeleri), dış ölçü, ızgara, ek akslar (kalktı), cumbanın boyu ve kimlik/talep yazıları."""
    src, ie = _ie(KAYNAK), _ie(HALLER[kod][0])
    for d in (src, ie):
        for anahtar in ("is_emri_no", "revizyon", "talep", "varsayimlar", "girintiler"):
            d.pop(anahtar)
        for anahtar in ("dis_olcu_cm", "grid", "ek_akslar_cm"):
            d["yapi"].pop(anahtar, None)
        d["yapi"]["dizilim"].pop("son_pano")
        for m in d["mahaller"]:
            m.pop("konum_cm")
        c = d["cati"]["cumbalar"][0]
        c.pop("bit_cm"); c.pop("cikinti_cm")
    assert ie == src
    son = _ie(HALLER[kod][0])["yapi"]["dizilim"]["son_pano"]
    assert son == ("kosu" if kod == "PA29" else _ie(KAYNAK)["yapi"]["dizilim"]["son_pano"])  # kısaltta salon penceresi için (10:01)


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_yalniz_dort_hat_kayar(kod):
    """Mahallerin ve girintinin her köşesi ya kaynaktaki yerinde ya da dört hattın yeni yerinde; yeni hatlar yarım pano hattında."""
    R, Gi, S, F = HALLER[kod][3]
    esle_x, esle_y = {745.0: R, 295.0: Gi}, {535.0: S, 680.0: F}
    src, ie = _ie(KAYNAK), _ie(HALLER[kod][0])
    for ms, mi in zip(src["mahaller"], ie["mahaller"]):
        for rs, ri in zip(ms["konum_cm"], mi["konum_cm"]):
            assert [esle_x.get(rs[0], rs[0]), esle_y.get(rs[1], rs[1]), esle_x.get(rs[2], rs[2]), esle_y.get(rs[3], rs[3])] == ri, kod
    assert ie["girintiler"] == [[Gi, S, R, F]]
    for v in (R, Gi):                                                             # kisa_kenar y: x'te ilk aks 5 (duvar ekseni)
        assert ((v - 5) / 62.75).is_integer(), v
    for v in (S, F):                                                              # y'de ilk aks 10 (iç yüz)
        assert ((v - 10) / 62.75).is_integer(), v
    assert ie["yapi"]["dis_olcu_cm"] == {"x": R + 5, "y": F + 10}
    for eski, yeni in zip(ESKI_HATLAR, (R, Gi, S, F)):
        assert abs(yeni - eski) < 62.75, (eski, yeni)


def test_kaynak_ev_standart_hal_degil():
    """Kaynak evin (PA-27) dış duvarında 8 özel pano var; standart hâl kipi onu geçirmez, normal kip geçirir (D-87 aynen)."""
    src = _ie(KAYNAK)
    ozel = HH.dis_ozel_panolar(src)
    assert sorted(p["boy"] for p in ozel) == [18.0, 34.75, 39.0, 86.5, 105.25, 105.25, 112.5, 112.5]
    b, o = HH.denetle_standart(src, _kart(), src)
    assert [x.split(":")[0] for x in b] == ["dış duvarda özel pano"] and o["dis_ozel_pano"] == 8
    assert HH.denetle(src, _kart())[0] == []


def test_standart_hal_normal_kipte_kalir():
    """Standart hâl proje kartının 5 cm ve 0,5 m² sınırını geçmez: havuza yalnız standart hâl kipiyle girer."""
    b, _ = HH.denetle(_ie(HALLER["PA28"][0]), _kart())
    assert [x.split(":")[0] for x in b] == ["dış ölçü", "brüt oturum"]


def _sag_duvar(ie: dict, eski: float, yeni: float) -> dict:
    """Sağ duvarı (x) başka bir yarım pano hattına taşır: mahaller, girinti, dış ölçü ve ızgara."""
    ie = json.loads(json.dumps(ie))
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            r[0], r[2] = (yeni if r[0] == eski else r[0]), (yeni if r[2] == eski else r[2])
    ie["girintiler"] = [[g[0], g[1], yeni if g[2] == eski else g[2], g[3]] for g in ie["girintiler"]]
    ie["yapi"]["dis_olcu_cm"]["x"] = yeni + 5
    ie["yapi"]["grid"]["x_pano"] = (yeni - 5) / 125.5
    return ie


def test_standart_hal_kalemleri():
    """Standart hâl kipi kalem kalem bulur: ölçü kaynaktan 62,75 cm'den çok kayınca, kaynak ev kartla aynı değilse, oda, pencere, kapı ve
    açık mahal farkında; brüt sayılmaz."""
    ie, src, kart = _ie(HALLER["PA28"][0]), _ie(KAYNAK), _kart()
    assert HH.denetle_standart(ie, kart, src)[0] == []
    iki_pano = _sag_duvar(ie, 758.0, 820.75)                                      # 750 → 825,75: 75,75 cm > 62,75
    b, o = HH.denetle_standart(iki_pano, kart, src)
    assert [x.split(":")[0] for x in b] == ["dış ölçü", "hat", "açıklık yeri"] and o["dis_olcu_cm"] == [825.75, 710.25] \
        and o["dis_ozel_pano"] == 0, b                                               # sağ duvarın penceresi duvarla 75,75 cm kayar
    assert "745 → 820.75" in b[1]
    bozuk = {**kart, "brut_oturum_m2": 90, "oda_sayisi": "2+1", "dis_kapi_adedi": 2, "sundurma_adedi": 0,
             "acikliklar": {**kart["acikliklar"], "999/999": 1}}
    bas = [x.split(":")[0] for x in HH.denetle_standart(ie, bozuk, src)[0]]
    assert bas == ["kaynak ev", "oda programı", "pencereler", "dis kapi", "veranda"]


def _girinti_x(ie: dict, eski: float, yeni: float) -> dict:
    """Girinti duvarını (x) taşır: yatak odasının ön parçası, girinti ve cumba birlikte; dış ölçü aynı."""
    ie = json.loads(json.dumps(ie))
    for m in ie["mahaller"]:
        for r in m["konum_cm"]:
            r[0], r[2] = (yeni if r[0] == eski else r[0]), (yeni if r[2] == eski else r[2])
    ie["girintiler"] = [[yeni if g[0] == eski else g[0], *g[1:]] for g in ie["girintiler"]]
    ie["cati"]["cumbalar"][0]["bit_cm"] = yeni + 5
    return ie


def test_standart_hal_kaynakla_ayni_degilse_kalir():
    """Dış ölçü aynı kalsa da: köşe 62,75'ten çok kayarsa (girinti 295 → 507), pencere başka odaya, kapı başka odaya taşınırsa ya da
    odanın türü değişirse standart hâl kipi bulur (geometri hakemi, 14 Kasım 2026: bunlar dış ölçü ve kart sayılarından geçiyordu). İkinci
    turdan beri Motor'un yerleştirdiği açıklığın yeri de kıyaslanır: taşınan açıklık "açıklık yeri" bulgusunu da verir."""
    ie, src, kart = _ie(HALLER["PA28"][0]), _ie(KAYNAK), _kart()
    b = HH.denetle_standart(_girinti_x(ie, 318.75, 507.0), kart, src)[0]
    assert {x.split(":")[0] for x in b} == {"hat", "açıklık yeri"} and b[0].startswith("hat") and "295 → 507" in b[0], b
    pencere = json.loads(json.dumps(ie))
    a = next(a for a in pencere["acikliklar"] if a.get("olcu") == "120x120")
    a.update(mahal="YATAK ODASI", duvar="sol", pano=0)
    assert [x.split(":")[0] for x in HH.denetle_standart(pencere, kart, src)[0]] == ["açıklıklar", "açıklık yeri"]
    kapi = json.loads(json.dumps(ie))
    next(a for a in kapi["acikliklar"] if a.get("arasi") == ["GİRİŞ", "YATAK ODASI"])["arasi"] = ["SALON & MUTFAK", "YATAK ODASI"]
    b = HH.denetle_standart(kapi, kart, src)[0]
    assert b[0].startswith("açıklıklar") and {x.split(":")[0] for x in b} == {"açıklıklar", "açıklık yeri"}, b
    oda = json.loads(json.dumps(ie))
    next(m for m in oda["mahaller"] if m["ad"] == "BANYO")["tur"] = "mutfak"
    assert "odalar" in [x.split(":")[0] for x in HH.denetle_standart(oda, kart, src)[0]]


@pytest.mark.parametrize("kod", sorted(HALLER))
def test_kapi_yeri_kaynakla_ayni(kod):
    """Motor'un yerleştirdiği kapılar kaynak evdekiyle aynı yerde, pencereler en çok 62,75 cm kaymış (İş Emri'nin çerçevesinde). Çelik kapı
    sundurmanın altında (193,25–318,75; Lokman 10:12:22, kart 10:34:26). Geometri hakemi, 14 Kasım 2026 ikinci tur: dizilimden kapının
    dayanağı silinince kapı 62,75 cm kayıp sundurmanın ucundan taşıyordu ve hakem geçiyordu; şimdi iki bulgu."""
    ie, src = _ie(HALLER[kod][0]), _ie(KAYNAK)
    yer, yer_k = HH.acikliklarin_yeri(ie), HH.acikliklarin_yeri(src)
    assert len(yer) == len(yer_k) == 8
    for d, dk in zip(yer, yer_k):
        assert (d["tur"], d["olcu"], d["duvar_tur"], d["yon"]) == (dk["tur"], dk["olcu"], dk["duvar_tur"], dk["yon"])
        if d["tur"] in HH.KAPI_TURLERI:
            assert (d["a0"], d["a1"]) == (dk["a0"], dk["a1"]), (kod, d, dk)
        assert max(abs(d[k] - dk[k]) for k in ("hat", "a0", "a1")) <= HH.TOL_STANDART_CM, (kod, d, dk)
    dis_kapi = next(d for d in yer if d["tur"] == "dis_kapi")
    assert (dis_kapi["a0"], dis_kapi["a1"]) == (193.25, 318.75)
    dayanaksiz = json.loads(json.dumps(ie))
    del dayanaksiz["yapi"]["dizilim"]["dis_pano_dayanagi"]
    b = HH.denetle_standart(dayanaksiz, _kart(), src)[0]
    assert [x.split(":")[0] for x in b] == ["dizilim", "açıklık yeri"] and "193.25–318.75 → 256–381.5" in b[1], b


def test_ozel_pano_tanimi():
    """Dış duvarda yalnız 125,5 / 62,75, köşede 120,5 / 57,75 ve 251'lik pencereli pano; iç duvar sayılmaz."""
    from motor import geometry as G
    for kod, (kaynak, *_) in HALLER.items():
        plan = G.kur(_ie(kaynak))
        boylar = {round(p.boy, 2) for p in plan.panolar if p.duvar.tur == "dis"}
        assert boylar <= {125.5, 62.75, 120.5, 57.75, 251.0}, (kod, boylar)
        assert HH.dis_ozel_panolar(_ie(kaynak)) == []
