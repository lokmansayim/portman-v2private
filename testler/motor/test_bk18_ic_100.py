"""BK-18 · Dış ve iç duvar aynı kalınlıkta (100 / 100).

Motor önceden `yapi.duvar_kalinligi_cm` {dis 10, ic 10}'u `IsEmriHatasi` ile reddediyordu ("katman adları ayrışmıyor"): `katman()` dış ve iç
köşe profilini aynı katmana (`KOSE_PROFIL_100`) koyuyordu. Şimdi eşit kalınlıkta iç köşe `IC_KOSE_PROFIL_<mm>` katmanındadır; 10 / 6'da ve
160 / 100'de katman adları ve çıktılar aynen kalır. Girdi `veri/TK02.json`: TK-01'in bayi çizimi (İş Emri r06 = `araclar/paket/girdi/TK01_r06.json`),
iç duvarlar 100'lük (Patron, 28 Ekim 2026: "içlerde 100'lük").

Hedef örnekler (D-28 madde 2; Lokman, 29 Ekim 2026 13:41: "ikiside çizim motorunda kurallar halinde olsun"): aynı projenin iki hâli,
`veri/TK02.json` iç 100 (ön onay çizimi r09 onayı 12:24, madde 14–15 notları 13:13–13:21) ve `veri/TK01_r07.json` iç 60 (kat planı onayı 13:47,
görünüşler 13:48 "sen onayla"). İzleri `veri/TK02_beklenen.json` ve `veri/TK01_r07_beklenen.json`: A4 ön onay PDF'inin ve DXF'in içerik izi,
doğrulama özeti, pano BOM'u, görünüş çizgileri, yükleme listesi satırları (üretim saati yok). Bilerek değişirse Lokman'ın onayı ve gerekçeli
kararla `python testler/motor/test_bk18_ic_100.py --yaz` (D-28 madde 3); gerekçe `docs/is_emirleri/BK-18.md`'ye.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import ezdxf
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
TK02 = VERI / "TK02.json"
HEDEFLER = {   # girdi, beklenen iz, onay dayanağı
    "TK02": (TK02, VERI / "TK02_beklenen.json",
             "TK-02 (iç 100) ön onay çizimi. Lokman 29 Ekim 2026: 11:01 kat planı, 12:24 r09 \"%100 onaylıyorum ... artık bu noktadan hareket "
             "edeceğiz\"; 13:13–13:21 madde 14–15 notları (r12); 13:48 \"sen onayla PR birleştir\" (D-31)."),
    "TK01_r07": (VERI / "TK01_r07.json", VERI / "TK01_r07_beklenen.json",
                 "TK-01 r07 (aynı proje, iç 60, standart) ön onay çizimi. Lokman 29 Ekim 2026: 13:41 \"ikiside çizim motorunda kurallar halinde "
                 "olsun\", 13:47 kat planı \"60'lık versiyonunda onaylıyorum\", 13:48 görünüşler \"sen onayla\" (D-31 madde 16)."),
}


def _ie() -> dict:
    return json.loads(TK02.read_text(encoding="utf-8"))


ON_KATMANLAR = ("ON_GORUNUS", "ON_DERZ", "ON_CATI", "ON_TOPUK")


def _gorunusler(dxf: Path) -> list:
    """Görünüşlerin çizgileri (duvar, derz, çatı ve topuk; ölçü, yazı ve doğrama bloğu hariç): katman ve noktalar, sıralı (BK-18 ek; Lokman,
    29 Ekim 2026, verandanın saçak ve topuk çizgisi; D-31'den beri dört görünüş)."""
    out = []
    for e in ezdxf.readfile(dxf).modelspace():
        if e.dxf.layer in ON_KATMANLAR and e.dxftype() in ("LINE", "LWPOLYLINE"):
            q = e.get_points("xy") if e.dxftype() == "LWPOLYLINE" else (e.dxf.start, e.dxf.end)
            out.append([e.dxf.layer, bool(e.dxftype() == "LWPOLYLINE" and e.closed)] + [[round(x[0], 3), round(x[1], 3)] for x in q])
    return sorted(out)


def _iz(cikti: Path, ie: dict | None = None) -> dict:
    """Ön onay çiziminin izi: A4 PDF'inin ve DXF'in içerik izi (`testler/referans/parmak_izi.py`; DXF'te üretim saati dışarıda), doğrulama
    özeti, pano BOM'u, dört görünüşün çizgileri ve yükleme listesinin satırları (üretim saati ve dosya adı girmez)."""
    sys.path.insert(0, str(KOK / "testler" / "referans"))
    from parmak_izi import dxf_ozet, pdf_ozet
    v = json.loads((cikti / "validation.json").read_text(encoding="utf-8"))
    b = json.loads((cikti / "bom.json").read_text(encoding="utf-8"))
    m = json.loads((cikti / "manifest.json").read_text(encoding="utf-8"))
    return {"dogrulama": {k: v[k] for k in ("passed", "errors", "outer_cm", "panel_grid", "panel_count", "corner_count", "windows", "doors",
                                            "h_connectors", "h_connectors_dis", "footprint_diff_cm2", "warnings")}
            | {"rooms_m2": {k: round(x, 4) for k, x in v["rooms_m2"].items()},
               "openings": [{"kind": o["kind"], "name": o["name"], "gap": [round(x, 3) for x in o["gap"]]} for o in v["openings"]]},
            "bom": [{k: r[k] for k in ("kod", "malzeme", "olcu_mm", "adet", "birim")} for r in b["kalemler"]],
            "gorunusler": _gorunusler(cikti / m["dxf"]),
            "liste": [{k: r[k] for k in ("grup", "kalem", "olcu", "adet")} for r in PL.is_emrinden(ie or _ie())["satirlar"]],
            "pdf_izi": pdf_ozet(cikti / m["pdf"]), "dxf_izi": dxf_ozet(cikti / m["dxf"])}


def test_esit_kalinlik_kurulur():
    plan = G.kur(_ie())
    assert (G.T_DIS, G.T_IC) == (10.0, 10.0)
    ic = [d for d in plan.duvarlar if d.tur == "ic"]
    assert ic and all(abs(2 * d.h - 10.0) < 1e-9 for d in ic)
    assert G.katman("KOSE_PROFIL_60") == "IC_KOSE_PROFIL_100" and G.katman("KOSE_PROFIL_100") == "KOSE_PROFIL_100"
    assert G.katman("IC_DUVAR_60") == "IC_DUVAR_100" and G.katman("DIS_DUVAR_100") == "DIS_DUVAR_100"


def test_esit_kalinlik_dogrulamadan_gecer_kose_katmanlari_ayri(tmp_path):
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True and m["pdf"], m.get("warnings")
    plan = G.kur(_ie())
    n_dis = sum(k.tur == "dis" for k in plan.koseler); n_ic = sum(k.tur == "ic" for k in plan.koseler)
    assert n_ic > 0
    d = ezdxf.readfile(tmp_path / m["dxf"])
    say = lambda L: sum(1 for e in d.modelspace() if e.dxftype() == "INSERT" and e.dxf.layer == L)
    assert say("IC_KOSE_PROFIL_100") == 2 * n_ic and say("KOSE_PROFIL_100") == 2 * n_dis   # akslı ve net alanlı iki plan kopyası
    assert say("IC_DUVAR_100") > 0 and say("IC_DUVAR_60") == 0
    assert any("100 mm / 100 mm" in (e.dxf.text if e.dxftype() == "TEXT" else e.text)
               for e in d.modelspace() if e.dxftype() in ("TEXT", "MTEXT"))
    # katalog (hakem bulgusu): eşit kalınlıkta dış T'deki üçlü H'ın anahtarı veranda dikmesininkine düşmez
    bom = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))["kalemler"]
    dikme = [r for r in bom if r["malzeme"] == "Veranda dikmesi"]
    h_dis = [r for r in bom if r["malzeme"] == "Üçlü H bağlantı dış 100×100"]
    n_hd = sum(h.tur == "dis" for h in plan.h_baglantilar)
    assert len(dikme) == 1 and dikme[0]["adet"] == 4, dikme                                # dört veranda köşesi (TK-01'deki gibi)
    assert n_hd > 0 and len(h_dis) == 1 and h_dis[0]["adet"] == n_hd and h_dis[0]["kod"] != dikme[0]["kod"], h_dis
    bloklar = {e.dxf.name.split("_")[1] for e in d.modelspace() if e.dxftype() == "INSERT" and e.dxf.layer == "DIS_UCLU_H_100"}
    assert bloklar == {h_dis[0]["kod"]}, bloklar


def test_ic_60_ile_dis_aciklik_ve_akslar_ayni(tmp_path):
    """Aynı İş Emri iç 6'yla (TK-01 r06): akslar, dış ölçü ve dış kapı aynı; açıklıklar aynı sırada, aynı tür ve boyda. İç duvar 4 cm
    kalınlaşınca bir açıklık en çok yarım fark (2 cm) kayar: oda ortasındaki pencere odanın net ortasıyla (1 cm), duvar ucuna yaslı iç kapı
    ucun yüzüyle (2 cm). Oda net alanları küçülür."""
    ie60 = _ie(); ie60["yapi"]["duvar_kalinligi_cm"] = {"dis": 10, "ic": 6}
    p100, p60 = G.kur(_ie()), G.kur(ie60)
    eksen = lambda p: sorted({(d.yon, round(d.c, 3)) for d in p.duvarlar})                 # duvarların oturduğu akslar
    assert (p100.W, p100.H) == (p60.W, p60.H) and eksen(p100) == eksen(p60)
    dxf_out.uret(_ie(), tmp_path / "100", pdf_hatada=False); dxf_out.uret(ie60, tmp_path / "60", pdf_hatada=False)
    v100, v60 = (json.loads((tmp_path / k / "validation.json").read_text(encoding="utf-8")) for k in ("100", "60"))
    assert v100["outer_cm"] == v60["outer_cm"] and v100["panel_grid"] == v60["panel_grid"]
    a, b = v100["openings"], v60["openings"]
    assert [(o["kind"], o["length"]) for o in a] == [(o["kind"], o["length"]) for o in b]
    kayma = []
    for o, p in zip(a, b):
        uzun = 0 if o["gap"][2] - o["gap"][0] > o["gap"][3] - o["gap"][1] else 1          # açıklığın boyunca uzandığı eksen
        kayma.append(abs((o["gap"][uzun] + o["gap"][uzun + 2]) - (p["gap"][uzun] + p["gap"][uzun + 2])) / 2)
    assert max(kayma) <= (10.0 - 6.0) / 2 + 1e-6, kayma
    dk = lambda v: [o["gap"] for o in v["openings"] if "_DIS_K" in o["name"]]
    assert dk(v100) == dk(v60)                                                            # dış kapı (GİRİŞ–HOL) yerinde
    assert v100["rooms_m2"].keys() == v60["rooms_m2"].keys()
    assert all(v100["rooms_m2"][k] <= v60["rooms_m2"][k] + 1e-9 for k in v60["rooms_m2"])
    assert v100["rooms_m2"]["SALON"] < v60["rooms_m2"]["SALON"]


def test_liste_100luk_ic_duvar():
    L = PL.is_emrinden(_ie())
    k = [r["kalem"] for r in L["satirlar"]]
    adet = lambda kalem: sum(r["adet"] for r in L["satirlar"] if r["kalem"] == kalem)
    formul = lambda kalem: " ".join(r["formul"] for r in L["satirlar"] if r["kalem"] == kalem)
    plan = G.kur(_ie())
    assert L["ozet"]["kural_yok"] == 0
    assert not [x for x in k if x.startswith("60'lık") and "pano" in x], k
    assert not [x for x in k if "6'lık köşe direği" in x or "Çektirme U'su 60" in x]
    assert "H standart 100 (iç pano eki)" in k and "3'lü H standart 100 (iç T)" in k and "Çektirme U'su 100 (iç duvar)" in k
    assert adet("3'lü H 100 × 100 × 100 (dış duvar T'si)") == sum(h.tur == "dis" for h in plan.h_baglantilar)
    assert adet("10'luk köşe direği 100 × 100") == len(plan.koseler)                       # dış ve iç köşe hepsi 100'lük
    assert "100'lük iç duvarlar" in formul("100'lük alt çerçeve")
    # D-32 ek (Lokman 30 Ekim 07:04): asma tavanda da 100'lük iç duvarın üstü 100'lük duvar omegası; 60'lık duvar omegasında değil, ayrı satır yok
    assert "100'lük iç duvarlar" in formul("100'lük duvar omegası") and "iç duvar üstleri 100'lük duvar omegasında" in formul(
        "60'lık duvar omegası (asma dizme tavan)") and not [x for x in k if x.startswith("60'lık iç duvar üstü")]


def test_varsayilan_katman_adlari_degismez():
    G.kur(json.loads((VERI / "PK01.json").read_text(encoding="utf-8")))
    assert (G.T_DIS, G.T_IC) == (10.0, 6.0)
    assert G.katman("KOSE_PROFIL_60") == "KOSE_PROFIL_60" and G.katman("KOSE_PROFIL_100") == "KOSE_PROFIL_100"
    try:
        G.kalinlik_ayarla(16.0, 10.0)                     # 160 / 100: iç köşe eskisi gibi KOSE_PROFIL_100 (dışınki 160)
        assert G.katman("KOSE_PROFIL_60") == "KOSE_PROFIL_100" and G.katman("KOSE_PROFIL_100") == "KOSE_PROFIL_160"
    finally:
        G.kalinlik_ayarla(10.0, 6.0)


@pytest.mark.parametrize("ad", sorted(HEDEFLER))
def test_hedef_ornek_izi(ad, tmp_path):
    """Aynı kurallar iç 60 ve iç 100'de (D-31 madde 16): ikisinin ön onay çizimi Lokman'ın onayladığı hedef örnekle aynı."""
    girdi, beklenen, _ = HEDEFLER[ad]
    ie = json.loads(girdi.read_text(encoding="utf-8"))
    m = dxf_out.uret(json.loads(json.dumps(ie)), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True and m["pdf"]
    b = json.loads(beklenen.read_text(encoding="utf-8"))
    assert b["girdi"] == girdi.relative_to(KOK).as_posix() and b["onay"]
    assert _iz(tmp_path, ie) == b["iz"]


def test_iki_hedef_yalniz_ic_kalinlikta_ayrisir():
    a, b = (json.loads(HEDEFLER[k][0].read_text(encoding="utf-8")) for k in ("TK02", "TK01_r07"))
    assert (a["yapi"]["duvar_kalinligi_cm"], b["yapi"]["duvar_kalinligi_cm"]) == ({"dis": 10, "ic": 10}, {"dis": 10, "ic": 6})
    for x in (a, b):
        for k in ("is_emri_no", "revizyon", "talep", "varsayimlar"): x.pop(k)
        x["yapi"].pop("duvar_kalinligi_cm"); x["yapi"].pop("referans_model")
    assert a == b


if __name__ == "__main__" and "--yaz" in sys.argv:
    import tempfile
    for ad, (girdi, beklenen, onay) in HEDEFLER.items():
        ie = json.loads(girdi.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as t:
            dxf_out.uret(json.loads(json.dumps(ie)), Path(t), pdf_hatada=False)
            beklenen.write_text(json.dumps({"aciklama": "BK-18 · ön onay çiziminin hedef örneği (D-28 madde 2): A4 PDF ve DXF içerik izi, doğrulama özeti, "
                                            "pano BOM'u, görünüş çizgileri ve yükleme listesi satırları.", "girdi": girdi.relative_to(KOK).as_posix(),
                                            "onay": onay, "iz": _iz(Path(t), ie)}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("yazıldı:", beklenen)
