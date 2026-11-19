"""D-96 › Havuza uygulama (İE-40 PR-7): iç duvarı 100'lük iki evin veranda köşesinde üçlü H, ev ev kartla. LLM'siz, Postgres'siz.

Lokman, 15 Kasım 2026 07:32:42 UTC: üçlü H yalnız iç duvar 100'lükken olur; 60'lıkta köşe direği kalır. Havuzda iç duvarı 100'lük üç ev var:
71 m² 2+1 (PA-35, BK-34, ayrı dosya), 91 m² 3+1 ve 143 m² 4+1. Ev kartları (standart pano sohbeti):
- 91 m² 3+1, 07:57:38 "Doğru, yanına eklensin": paftada köşe direği; bugünkü PA-11 aynen kalır, üçlü H'lı hâl yeni numara PA-37 (D-103).
- 143 m² 4+1, 07:57:47 "Evet, havuzda yenilensin": paftada özel 3'lü H; havuzdaki kayıt (köşe direği) paftaya döner, numara PA-13 aynı.

Girdi kör ölçümün İş Emri'sinin kopyası (kör dosya aynen); fark yalnız `yapi.birlesimler`, talep metni ve bir varsayım satırı.
"""
from __future__ import annotations

import contextlib
import copy
import glob
import io
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import havuz_hakemi as HH  # noqa: E402
from beyin.katalog import SABLON_DIR, havuz_kayitlari  # noqa: E402
from motor import geometry as G, prefabrik_liste as PL  # noqa: E402

D96 = (KOK / "KARARLAR" / "D-96.md").read_text(encoding="utf-8")
SOZ = ("bu 71 m² deki üçlü H iç duvarlar 100'lük olduğu için olur ama iç duvarlar 60'lık olursa olmaz köşe kullanmak zorunda kalırız şöyle "
       "bir mantık vereyim standart H'larda 100'lükten 60'lığa geçen redisyon gibi bir malzeme yok")
# kod → (proje, kör İş Emri, üçlü H'lı kaynak, nokta (Motor çerçevesi), kartın saati ve seçimi, pano, dış ölçü)
EVLER = {
    "PA37": ("AP-06", "testler/kor/projeler/AP06/is_emri.json", "testler/havuz/is_emirleri/AP06_UCLU_H.json", [381.5, 700.25],
             ("07:57:38", "Doğru, yanına eklensin"), 49, (888.5, 1024.0)),
    "PA13": ("AP-12", "testler/kor/projeler/AP12/is_emri.json", "testler/havuz/is_emirleri/AP12_UCLU_H.json", [512.0, 1260.0],
             ("07:57:47", "Evet, havuzda yenilensin"), 91, (888.5, 1641.5)),
}
# değişen panolar (duvar, a0, a1, boy, açıklık): önce (köşe direği) → sonra (üçlü H); öteki panolar aynı
PANOLAR = {
    "PA37": ([(4, 381.5, 507.0, 125.5, "dis_kapi"), (7, 261.0, 318.75, 57.75, ""), (9, 328.75, 386.5, 57.75, "")],
             [(4, 386.5, 507.0, 120.5, "dis_kapi"), (7, 261.0, 323.75, 62.75, ""), (9, 323.75, 386.5, 62.75, "")]),
    "PA13": ([(6, 386.5, 512.0, 125.5, "dis_kapi"), (11, 256.0, 376.5, 120.5, ""), (12, 386.5, 507.0, 120.5, "")],
             [(6, 386.5, 507.0, 120.5, "dis_kapi"), (11, 256.0, 381.5, 125.5, ""), (12, 381.5, 507.0, 125.5, "")]),
}
# yükleme listesi farkı (grup, kalem, ölçü, önce, sonra); D-96 › Havuza uygulama
LISTE = {
    "PA37": {
        ("1001", "100'lük yapıştırma dolu pano", "100 × 575 × 2500", 6, 4),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 625 × 2500", None, 2),
        ("1001", "Karkaslı çelik kapı panosu", "100 × 1200 × 2500", None, 1),
        ("1001", "Karkaslı çelik kapı panosu", "100 × 1250 × 2500", 2, 1),
        ("1002", "10'luk köşe direği 100 × 100", "100 × 100 × 2500", 7, 6),
        ("1002", "3'lü H 100 × 100 × 100 (dış duvar T'si)", "L 2500", 3, 4),
        ("1002", "Çektirme U'su 100 (iç duvar)", "100 × 2440", 4, 3),      # D-105 madde 2 (BK-38; Lokman kartı 15 Kasım 09:14:41 "Evet, 1 adet 100'lük"): köşe direkli 100'lük dış köşede 1 çektirme U'su; üçlü H'lı hâlde yok
        ("1009", "Çelik dübel", "adet", 25, 26),
    },
    "PA13": {
        ("1001", "100'lük yapıştırma dolu pano", "100 × 1200 × 2800", 12, 10),
        ("1001", "100'lük yapıştırma dolu pano", "100 × 1250 × 2800", 37, 39),
        ("1001", "Karkaslı çelik kapı panosu", "100 × 1200 × 2800", None, 1),
        ("1001", "Karkaslı çelik kapı panosu", "100 × 1250 × 2800", 2, 1),
        ("1002", "10'luk köşe direği 100 × 100", "100 × 100 × 2800", 6, 5),
        ("1002", "3'lü H 100 × 100 × 100 (dış duvar T'si)", "L 2800", 9, 10),
        ("1002", "Çektirme U'su 100 (iç duvar)", "100 × 2740", 1, 0),      # D-105 madde 2 (BK-38; Lokman kartı 15 Kasım 09:14:41 "Evet, 1 adet 100'lük"): köşe direkli 100'lük dış köşede 1 çektirme U'su; üçlü H'lı hâlde yok
        ("1007", "NYM kablo 2 × 1,5", "metre", 144, 143),
        ("1007", "NYM kablo 3 × 2,5", "metre", 160, 159),
        ("1009", "Çelik dübel", "adet", 40, 41),
    },
}
KAYIT = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}


def _ie(yol) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _sablon(kod: str) -> dict:
    return json.loads((SABLON_DIR / KAYIT[kod]["sablon"]).read_text(encoding="utf-8"))


def _anahtarsiz(ie: dict) -> dict:
    ie = copy.deepcopy(ie)
    ie["yapi"].pop("birlesimler")
    return ie


def _an(q) -> tuple:
    return (q.duvar.id, round(q.a0, 3), round(q.a1, 3))


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_kaynak_kor_is_emri_arti_uclu_h(kod):
    """Kaynak kör ölçümün İş Emri'sidir; yalnız üçlü H noktası, talep metninin sonu ve bir varsayım satırı eklenir. İç duvar 100'lük."""
    _, kor, kaynak, nokta, (saat, secim), _, _ = EVLER[kod]
    k, ie = _ie(kor), _ie(kaynak)
    assert k["yapi"]["duvar_kalinligi_cm"] == ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 10}   # 07:32:42 sözünün koşulu
    assert "birlesimler" not in k["yapi"] and ie["yapi"]["birlesimler"] == [{"nokta_cm": nokta, "t": "uclu_h"}]
    assert ie["talep"]["metin"].startswith(k["talep"]["metin"]) and SOZ in ie["talep"]["metin"]
    assert saat in ie["talep"]["metin"] and f'"{secim}"' in ie["talep"]["metin"]
    assert ie["varsayimlar"][:-1] == k["varsayimlar"] and "üçlü H" in ie["varsayimlar"][-1]
    for d in (k, ie):
        d["yapi"].pop("birlesimler", None)
        d["talep"].pop("metin")
        d["varsayimlar"] = d["varsayimlar"][:len(k["varsayimlar"])]
    assert ie == k


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_kayit_ve_karar(kod):
    """Kayıt D-96 ile ve üçlü H'lı kaynaktan; karar dosyası evi, kartın saatini ve seçimini yazar; proje kartı hakemi normal kipte geçer."""
    proje, _, kaynak, nokta, (saat, secim), pano, dis = EVLER[kod]
    a = KAYIT[kod]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"], a["kaynak"]["kart_kiyasi"]["kart"]) == (kaynak, "D-96", proje)
    assert a["kaynak"]["kart_kiyasi"]["sonuc"] == "geçti" and a["kaynak"]["standart"] is True
    assert f"| {kod[:2]}-{kod[2:]} | {proje} | `{kaynak}` |" in D96
    assert f'{saat} Lokman seçti: **"{secim}"**' in D96 and f'| {saat} "{secim}" |' in D96
    sab = _sablon(kod)
    assert sab["yapi"]["birlesimler"] == [{"nokta_cm": nokta, "t": "uclu_h"}]
    bulgular, olc = HH.denetle(sab, HH.kartlar()[proje])
    assert bulgular == [] and olc == a["kaynak"]["kart_kiyasi"]["olcum"]
    assert a["ozet"]["pano"] == pano and a["ozet"]["dis_olcu_cm"] == list(dis)


@pytest.mark.parametrize("kod", sorted(EVLER))
def test_pano_ve_liste_farki(kod):
    """Motor'un köşe direğiyle ve üçlü H'la planı: yalnız kapı panosu ve köşenin iki yanındaki pano değişir; dış ölçü ve pano sayısı aynı.
    Liste farkı karar dosyasındaki gibi (köşe direği bir az, 3'lü H bir fazla)."""
    sab = _sablon(kod)
    p0, p1 = G.kur(_anahtarsiz(sab)), G.kur(copy.deepcopy(sab))
    _, _, _, _, _, pano, dis = EVLER[kod]
    assert len(p0.panolar) == len(p1.panolar) == pano and (p0.W, p0.H) == (p1.W, p1.H) == dis
    k0, k1 = {_an(q): q for q in p0.panolar}, {_an(q): q for q in p1.panolar}
    ozet = lambda k, q: (*k, round(q.boy, 2), q.acilim.tur if q.acilim else "")   # noqa: E731
    assert (sorted(ozet(k, q) for k, q in k0.items() if k not in k1), sorted(ozet(k, q) for k, q in k1.items() if k not in k0)) \
        == PANOLAR[kod]

    def satirlar(ie):
        with contextlib.redirect_stdout(io.StringIO()):
            L = PL.liste(PL.model_motor(copy.deepcopy(ie)))
        return {(r["grup"], r["kalem"], r["olcu"]): r["adet"] for r in L["satirlar"]}
    a, b = satirlar(_anahtarsiz(sab)), satirlar(sab)
    assert {(*k, a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)} == LISTE[kod]


def test_bugunku_91m2_aynen():
    """91 m² 3+1'in bugünkü kaydı (PA-11) paftadaki köşe direğiyle kalır (D-103): kaynağı kör İş Emri, kararı D-87, şablonda üçlü H yok."""
    a = KAYIT["PA11"]
    assert (a["kaynak"]["dosya"], a["kaynak"]["karar"]) == ("testler/kor/projeler/AP06/is_emri.json", "D-87")
    assert "birlesimler" not in _sablon("PA11")["yapi"]
    b = KAYIT["PA37"]                                                                   # yeni ev: aynı ölçü, oda ve m²
    assert (b["ozet"]["dis_olcu_cm"], b["ozet"]["pano"], b["ozet"]["brut_m2"]) == (a["ozet"]["dis_olcu_cm"], a["ozet"]["pano"],
                                                                                   a["ozet"]["brut_m2"])
    assert (b["katalog_m2"], b["oda_programi"]) == (a["katalog_m2"], a["oda_programi"]) == (91.0, "3+1")


# Üçlü H'lı evin çatı seçenekleri (İE-44; D-117, Lokman kartı 16 Kasım 16:17:03 "18'i girsin"): plan evinkiyle aynı, yalnız `cati`
# değişir; şablon evin İş Emri'sini birleşimleriyle taşır. Kod → (ev, karar). Ayrıntı test_cati_secenekleri_toplu.py.
CATI_SECENEKLERI = {"PA37B": ("PA37", "D-117")}


def test_uclu_h_yalniz_kartli_evlerde():
    """Havuz şablonlarında üçlü H yalnız Lokman'ın ev kartıyla yazılan üç evde: 71 m² hâli (PA-35), 91 m² hâli (PA-37), 143 m² (PA-13).
    Bu evlerin çatı seçeneği evin birleşimlerini aynen taşır (D-117).
    İç duvarı 60'lık evlerde köşe direği kalır, soru sorulmaz (07:32:42 sözü); yeni ev eklenirse bilinçli olarak buraya yazılır."""
    uclu, birlesim = set(), {}
    for f in sorted(glob.glob(str(SABLON_DIR / "adaylar" / "*.json"))):
        ie = json.loads(Path(f).read_text(encoding="utf-8"))
        birlesim[Path(f).stem] = (ie.get("yapi") or {}).get("birlesimler")
        if any(b.get("t") == "uclu_h" for b in birlesim[Path(f).stem] or []):
            uclu.add(Path(f).stem)
            assert ie["yapi"]["duvar_kalinligi_cm"]["ic"] == 10, f
    assert uclu == {"PA35", "PA37", "PA13"} | set(CATI_SECENEKLERI)
    for secenek, (ev, karar) in CATI_SECENEKLERI.items():
        kayit = json.loads((KOK / "beyin/veri/cati_varyantlari" / f"{ev}.json").read_text(encoding="utf-8"))
        assert ev in {"PA35", "PA37", "PA13"} and birlesim[secenek] == birlesim[ev]
        assert [(v["sablon"], v["kaynak"]["karar"]) for v in kayit["varyantlar"] if v["kod"] == secenek] == [(f"adaylar/{secenek}.json", karar)]


def test_karar_dosyasi_sozu_yazar():
    assert "07:32:42, Lokman" in D96 and SOZ.replace(" kalırız", "\n  kalırız") in D96
    assert "genel kural yazılmaz" in D96 and "Anahtar yine yalnız İş Emri'ne yazılan noktada çalışır" in D96
