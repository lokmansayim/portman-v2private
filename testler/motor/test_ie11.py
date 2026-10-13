"""İE-11 · Pano motorunun genişletilmesi — anahtarlı davranışlar, anahtarsız yolun kilidi ve PK-01.

İki tür test var; karıştırılmaz (test politikası, geometri hakemi 13.10.2026):
- **Motor kilidi:** bugünkü Motor çıktısını sabitler (gerileme). Paftaya uygunluk kanıtı DEĞİLDİR.
- **Pafta sayıları:** PK-01 montaj paftasından sayılan değerler (`deneme/2026-10-13_pk_01/PK01_okuma.md`). Tutmayanlar `xfail(strict=True)`
  ile işaretlidir: gerekçe İE-11 › Kanıt 3 ve PR-2 kıyas raporunda; Motor düzelince XPASS verir ve işaret kaldırılır.
Eski İş Emri'nin bayt bayt aynı kaldığını `testler/referans/dogrula.py` (18 DXF / 18 PDF izi) söyler; buradaki anahtarsız testler onun
kapsamadığı yolları (doğrulama kuralı, 250 dışı yükseklik, hata sonrası durum) kilitler.
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

PK01 = KOK / "deneme" / "2026-10-13_pk_01" / "tanim" / "PK01.json"
P6001 = KOK / "is_emri" / "P6001_2plus1_6x6.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _kopya(ie: dict) -> dict:
    return json.loads(json.dumps(ie))


def _duvar(plan, yon, c):
    return next(d for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 1e-6)


# --------------------------------------------------------------------------- anahtarsız yol (eski Motor) kilidi

def test_eski_is_emri_yeni_anahtar_yok():
    ie = _oku(P6001)
    assert G.yeni_anahtar_var(ie) is False
    G.kur(ie)
    assert G._AKS == {"x": None, "y": None}, "anahtarsız İş Emri'nde aks tablosu kurulmamalı (eski kod yolu)"
    assert G.X_SON is None and G.Y_SON is None


def _p6001_on_veranda_tam_genislik() -> dict:
    """Anahtarsız türev: ön veranda tam genişlikte, yatak odası 2 yok → ön dış duvar yok. Eski doğrulama kuralı bunu reddeder."""
    ie = _oku(P6001)
    ie["mahaller"] = [m for m in ie["mahaller"] if m["ad"] != "YATAK ODASI 2"]
    for m in ie["mahaller"]:
        if m["tur"] == "veranda":
            m["konum_pano"] = [[0, 0, 6, 2]]
    ie["acikliklar"] = [a for a in ie["acikliklar"] if "YATAK ODASI 2" not in (a.get("mahal"), *(a.get("arasi") or []))]
    ie["acik_sinirlar"] = [s for s in ie.get("acik_sinirlar", []) if "YATAK ODASI 2" not in (s["arasi"] if isinstance(s, dict) else s)]
    ie["dikmeler"] = []
    ie["is_emri_no"] = "TEST-ANAHTARSIZ-VERANDA"
    assert not G.yeni_anahtar_var(ie)
    return ie


def test_anahtarsiz_dogrulama_kurali_eski(tmp_path):
    """Geometri hakemi (13.10) kritik 1: anahtarsız İş Emri'nde 'Dış ölçüler (0,0,W,H)' kuralı eskisi gibi kalmalı (5827ab7 davranışı)."""
    from motor import dxf_out
    m = dxf_out.uret(_p6001_on_veranda_tam_genislik(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is False and m["pdf"] is None
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert any(e.startswith("Dış ölçüler") for e in v["errors"]), v["errors"]


def test_yukseklik_kumesi_250_280_300():
    """Lokman 13.10.2026 07:28: prefabrikte 260 yoktur; yalnız 250 / 280 / 300 (%80 / %19 / %1). Başka yükseklik açık hata (K21);
    250 dışı yükseklik yeni kod yolundan geçer (eski yol 2500 kodu + 50 lento veriyordu — geometri hakemi önemli 7)."""
    ie = _oku(P6001); ie["yapi"]["duvar_yuksekligi_cm"] = 260
    with pytest.raises(G.IsEmriHatasi, match="250 / 280 / 300"):
        G.kur(ie)
    for h in (280, 300):
        ie = _oku(P6001); ie["yapi"]["duvar_yuksekligi_cm"] = h
        assert G.yeni_anahtar_var(ie)
        plan = G.kur(ie); assert (plan.W, plan.H, len(plan.panolar)) == (773.0, 763.0, 36)   # yükseklik plan geometrisini değiştirmez
    assert not G.yeni_anahtar_var(_oku(P6001))                                               # 250: eski yol


def test_yukseklik_280_pano_kodlari_ve_lento(tmp_path):
    import ezdxf
    from motor import dxf_out
    ie = _oku(P6001); ie["yapi"]["duvar_yuksekligi_cm"] = 280
    m = dxf_out.uret(ie, tmp_path, pdf_hatada=False)
    assert m["validation_passed"]
    bom = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))
    panolar = [r for r in bom["kalemler"] if r["kod"][0] in "DI"]
    assert panolar and all(r["olcu_mm"][2] == 2800 for r in panolar), [(r["kod"], r["olcu_mm"]) for r in panolar]
    doc = ezdxf.readfile(tmp_path / Path(m["dxf"]).name)
    yazilar = [t.dxf.text for t in doc.modelspace().query("TEXT")]
    assert any("Lento 80 cm" in t and "Bina yüksekliği 280 cm" in t for t in yazilar), [t for t in yazilar if "Lento" in t]


def test_hata_sonrasi_durum_sifirlanir():
    """Geometri hakemi isteğe bağlı 10: hatayla düşen kurulumun aks tablosu / kesimi sonraki kur()'a sızmaz."""
    ie = _oku(PK01)
    ie["mahaller"][3]["konum_cm"] = [[261, 256, 386.5, 800]]
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)
    ref = G.kur(_oku(P6001))
    assert G._AKS == {"x": None, "y": None} and G.X_SON is None
    assert (ref.W, ref.H, len(ref.panolar)) == (773.0, 763.0, 36)


# --------------------------------------------------------------------------- PK-01 · Motor kilidi (paftaya uygunluk kanıtı değil)

def test_pk01_motor_kilidi():
    """PK-01'in bugünkü Motor çıktısı (gerileme kilidi). Paftayla karşılaştırma `test_pk01_paftadan_sayilanlar`'da."""
    ie = _oku(PK01)
    assert G.yeni_anahtar_var(ie)
    plan = G.kur(_kopya(ie))
    assert (plan.W, plan.H) == (600.0, 1000.0)
    assert (plan.nx, plan.ny) == (5.0, 8.0), "Plan.nx/ny İş Emri ızgarasıdır; ek aks tabloyu büyütür, ızgarayı değil"
    dis = [d for d in plan.duvarlar if d.tur == "dis"]; ic = [d for d in plan.duvarlar if d.tur == "ic"]
    assert sum(len(d.panolar) for d in dis) == 28 and sum(len(d.panolar) for d in ic) == 20
    assert len(plan.koseler) == 7 and Counter(k.tur for k in plan.koseler) == {"dis": 6, "ic": 1}
    assert Counter(h.tur for h in plan.h_baglantilar) == {"ic": 4, "dis": 5}
    # boylar: tam küme (alt küme değil)
    assert Counter(round(p.boy, 2) for d in dis for p in d.panolar) == {125.5: 19, 111.5: 2, 78.0: 2, 62.75: 2, 120.5: 1, 83.5: 1, 37.0: 1}
    assert Counter(round(p.boy, 2) for d in ic for p in d.panolar) == {125.5: 9, 122.5: 5, 120.5: 2, 32.0: 2, 62.75: 1, 78.0: 1}
    assert Counter(p.acilim.tur for p in plan.panolar if p.acilim) == {"pencere": 6, "ic_kapi": 5, "dis_kapi": 1}
    # aks dışı duvar: arkadan 795 → gerçek çerçevede 205
    assert any(d.yon == "x" and abs(d.c - 205.0) < 1e-6 for d in dis)
    assert abs(_duvar(plan, "y", 5.0).panolar[0].boy - 111.5) < 1e-6           # sol dış duvarın ön ucu kesilmiş pano
    assert [round(p.boy, 2) for p in _duvar(plan, "y", 266.0).panolar] == [111.5, 83.5]   # veranda sol duvarı ızgara hizalı
    assert [p.acilim.dograma for p in plan.panolar if p.acilim and p.acilim.tur == "dis_kapi"] == ["alıcıya ait"]
    # hol↔mutfak ve hol↔salon kapıları paftadaki panoda: arkadan 381,5–507 → gerçek 493–618,5
    for c in (261.0, 386.5):
        kapi = [p for p in _duvar(plan, "y", c).panolar if p.acilim and p.acilim.tur == "ic_kapi" and set(p.acilim.arasi) & {"MUTFAK", "SALON"}]
        assert len(kapi) == 1 and (round(kapi[0].a0, 2), round(kapi[0].a1, 2)) == (493.0, 618.5), (c, [(p.a0, p.a1) for p in kapi])
    # aks etiketleri: ek aks numara kaydırmaz (205 → "2′")
    assert G.ana_aks_etiketleri("x") == ["A", "B", "C", "D", "E", "F"]
    assert G.ana_aks_etiketleri("y") == ["1", "2", "2′", "3", "4", "5", "6", "7", "8", "9"]
    assert G.ana_akslar("y")[2] == 205.0
    assert plan.uyarilar == []


def test_pk01_paftadan_sayilanlar():
    """Paftadan sayılanların Motor'la tutan kısmı (PK01_okuma.md). Tutmayanlar `test_pk01_pafta_sapmalari`'nda."""
    plan = G.kur(_oku(PK01))
    pafta = {"YATAK ODASI 1": 7.5, "BANYO": 4.4, "YATAK ODASI 2": 7.3, "HOL": 6.3, "MUTFAK": 14.9, "SALON": 8.1, "VERANDA": 6.6}
    for ad, m2 in pafta.items():
        assert abs(plan.mahaller[ad].alan_m2 - m2) <= 0.2, (ad, plan.mahaller[ad].alan_m2)   # pafta etiketi 0,1 m²'ye yuvarlı
    assert Counter(p.acilim.tur for p in plan.panolar if p.acilim) == {"pencere": 6, "ic_kapi": 5, "dis_kapi": 1}   # pafta: 6 pencere, 5 iç + 1 dış kapı
    ic = [d for d in plan.duvarlar if d.tur == "ic"]
    ic_eki = sum(len(d.panolar) - 1 for d in ic) - sum(1 for h in plan.h_baglantilar if h.tur == "ic")
    assert ic_eki == 10                                                                      # pafta: H standart (iç) 10
    assert {37.0, 62.75, 78.0, 83.5, 111.5, 120.5, 122.5, 32.0} <= {round(p.boy, 2) for d in plan.duvarlar for p in d.panolar}   # paftadaki özel boylar
    assert len(plan.koseler) == 7


@pytest.mark.xfail(strict=True, reason="PK-01 paftası: üçlü H 10 (5 iç) ve dış pano eki H 19; Motor 9 (4 iç + 5 dış) ve 17 — İE-11 Kanıt 3, PR-2 kıyas raporu")
def test_pk01_pafta_sapmalari():
    plan = G.kur(_oku(PK01))
    dis = [d for d in plan.duvarlar if d.tur == "dis"]
    dis_eki = sum(len(d.panolar) - 1 for d in dis) - sum(1 for h in plan.h_baglantilar if h.tur == "dis")
    assert len(plan.h_baglantilar) == 10 and dis_eki == 19


def test_pk01_uret_dogrulama(tmp_path):
    import ezdxf
    from motor import dxf_out
    m = dxf_out.uret(_oku(PK01), tmp_path, pdf_hatada=True)
    assert m["validation_passed"] is True and m["pdf"] is not None
    bom = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))["kalemler"]
    k03 = [r for r in bom if r["kod"] == "K03"]                       # doğrama satırı; "Dış kapılı özel pano" (D07) işaretlenmez
    assert len(k03) == 1 and k03[0].get("alici") is True and k03[0]["alici_adet"] == 1 and "Alıcıya ait" in k03[0]["not"]
    assert not any(r.get("alici") for r in bom if r["kod"] != "K03"), "alıcıya ait işareti yalnız doğrama satırında olmalı"
    assert any(r["malzeme"].startswith("Üçlü H bağlantı dış") and r["adet"] == 5 for r in bom)
    # dış üçlü H kendi katmanında; iç katmanda yalnız 4 iç
    doc = ezdxf.readfile(tmp_path / Path(m["dxf"]).name); msp = doc.modelspace(); W = 600.0 + 150.0
    assert sum(1 for e in msp.query('INSERT[layer=="DIS_UCLU_H_100"]') if e.dxf.insert.x < W) == 5
    assert sum(1 for e in msp.query('INSERT[layer=="IC_UCLU_H_60"]') if e.dxf.insert.x < W) == 4
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert v["panel_grid"] == [5.0, 8.0]
    # Motor uyarısı yok; İş Emri'nin pafta uyarıları validation.json'da
    assert len(v["warnings"]) == 4 and all("PK-01" in w or "Veranda" in w or "Banyo" in w or "Üçlü H" in w for w in v["warnings"])


def test_alici_karisik_kod_satiri_isaretlenmez(tmp_path):
    """Geometri hakemi önemli 8: aynı koddan alıcıya ait olmayan doğrama da varsa satır işaretlenmez, yalnız adet düşülür."""
    from motor import dxf_out
    ie = _oku(PK01)
    for a in ie["acikliklar"]:                                        # YO1 sol penceresi alıcıya ait; öteki iki 120×120 bizim
        if a["tur"] == "pencere" and a["olcu"] == "120x120" and a["mahal"] == "YATAK ODASI 1":
            a["dograma"] = "alıcıya ait"
    m = dxf_out.uret(ie, tmp_path, pdf_hatada=True)
    assert m["validation_passed"]
    bom = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))["kalemler"]
    p01 = next(r for r in bom if r["kod"] == "P01")
    assert p01["adet"] == 3 and p01["alici_adet"] == 1 and p01["alici"] is False and "2 adet girer" in p01["not"]


# --------------------------------------------------------------------------- dizilim arka-sol (ayna)

def _aday_dizini_arkadan(plan, ac: dict, hedef_duvar, hedef_pano, W, H):
    """kur()'un aday sıralamasını yeniden kurar: adaylar aynalı çerçevede a0'a göre sıralıdır (y duvarda a0' = H − a1).
    Hedef duvarda, gerçek çerçevede hedef panoyla en çok örtüşen adayın dizinini verir."""
    NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
    if ac["tur"] == "pencere":
        cand = G._edges_of_room_side(plan.duvarlar, ac["mahal"], NORMAL[ac["duvar"]]); gen = float(G.PENCERE_OLCULERI[ac["olcu"]][0])
    else:
        cand = G._edges_between(plan.duvarlar, *ac["arasi"]); gen = float(ac.get("olcu", G.KAPI_GENISLIK[ac["tur"]]))
    adaylar = []
    for d, k0, k1 in cand:
        lo = G.X(k0 / 2) if d.yon == "x" else G.Y(k0 / 2); hi = G.X(k1 / 2) if d.yon == "x" else G.Y(k1 / 2)
        lo, hi = min(lo, hi), max(lo, hi)                              # aynalı tabloda Y dizinleri ters
        for p in d.panolar:
            mid = (p.a0 + p.a1) / 2
            if mid - gen / 2 >= lo - 1e-6 and mid + gen / 2 <= hi + 1e-6 and p not in [q for _, q in adaylar]:
                adaylar.append((d, p))
    adaylar.sort(key=lambda dp: (H - dp[1].a1) if dp[0].yon == "y" else dp[1].a0)
    en_iyi = max((i for i, (d, p) in enumerate(adaylar) if d.yon == hedef_duvar.yon and abs(d.c - hedef_duvar.c) < 1e-6),
                 key=lambda i: min(adaylar[i][1].a1, hedef_pano.a1) - max(adaylar[i][1].a0, hedef_pano.a0), default=None)
    assert en_iyi is not None, ("hedef duvarda aday yok", ac)
    return en_iyi


def test_ayna_p6001_ayni_gecometri():
    """dizilim arka-sol: y arkadan sayılan P6001, öndekiyle aynı geometriyi vermeli (ayna iki kez). Açıklıklar aynı duvara pano
    diziniyle sabitlenir; kapı varyantı (menteşe) ve normaller bire bir aynı olmalı (geometri hakemi kritik 2 / önemli 5)."""
    ie = _oku(P6001)
    ref = G.kur(_kopya(ie))
    ny = float(ie["yapi"]["grid"]["y_pano"])
    ayna = _kopya(ie)
    ayna["yapi"]["dizilim"] = {"baslangic": "arka-sol"}
    for m in ayna["mahaller"]:
        m["konum_pano"] = [[x0, ny - y1, x1, ny - y0] for (x0, y0, x1, y1) in m["konum_pano"]]
    ayna["dikmeler"] = ie.get("dikmeler", [])                           # dikmeler gerçek çerçevede (cm) kalır
    # 1) açıklıksız kurulum → her açıklığı ref'teki duvar/panoya götüren arkadan dizin
    bos = _kopya(ayna); bos["acikliklar"] = []
    plan0 = G.kur(bos)
    hedef = {}
    for d in ref.duvarlar:
        for p in d.panolar:
            if p.acilim:
                anahtar = (p.acilim.tur, p.acilim.mahal, tuple(sorted(p.acilim.arasi)) if p.acilim.arasi else None, p.acilim.olcu)
                hedef[anahtar] = (d, p)
    for a in ayna["acikliklar"]:
        anahtar = (a["tur"], a.get("mahal"), tuple(sorted(a["arasi"])) if a.get("arasi") else None,
                   a["olcu"] if a["tur"] == "pencere" else str(int(a.get("olcu", G.KAPI_GENISLIK[a["tur"]]))))
        d, p = hedef[anahtar]
        a["pano"] = _aday_dizini_arkadan(plan0, a, d, p, ref.W, ref.H)
    plan = G.kur(ayna)
    # 2) bütün: dış ölçü, sayılar, köşeler, mahaller
    assert (plan.W, plan.H) == (ref.W, ref.H)
    assert len(plan.panolar) == len(ref.panolar) and len(plan.koseler) == len(ref.koseler) and len(plan.h_baglantilar) == len(ref.h_baglantilar)
    assert sorted(round(k.rect[i], 3) for k in plan.koseler for i in range(4)) == sorted(round(k.rect[i], 3) for k in ref.koseler for i in range(4))
    assert sorted((round(h.x, 3), round(h.y, 3), h.rot, h.tur) for h in plan.h_baglantilar) == sorted((round(h.x, 3), round(h.y, 3), h.rot, h.tur) for h in ref.h_baglantilar)
    for ad in ref.mahaller:
        assert abs(plan.mahaller[ad].alan_m2 - ref.mahaller[ad].alan_m2) < 1e-6
        assert plan.mahaller[ad].poly.symmetric_difference(ref.mahaller[ad].poly).area < 1e-6
    # 3) panolar: her duvarda pano sayısı, tam modül sayısı ve toplam boy aynı. Yerler karşılaştırılmaz: "koşu başından" dizilim arkadan
    #    başladığı için 125,5'in katı olmayan koşuda ekler 62,75 kayar ve artık parça karşı uca düşer (örn. iç duvar x=449,25: ekler
    #    569,75/695,25 ↔ 507/632,5; boylar 122,5+125,5+57,75 ↔ 120,5+125,5+59,75). Bu, arka-sol dizilimin tanımıdır (İE-11, D-10).
    ozet = lambda p: sorted((d.tur, d.yon, round(d.c, 3), len(d.panolar), sum(1 for pn in d.panolar if abs(pn.boy - G.MOD) < 1e-6),
                             round(sum(pn.boy for pn in d.panolar), 3)) for d in p.duvarlar)
    assert ozet(plan) == ozet(ref)
    # 4) açıklıklar: aynı duvar, aynı normal, aynı kapı varyantı (menteşe), pano örtüşür
    def acikliklar(p):
        out = {}
        for d in p.duvarlar:
            for pn in d.panolar:
                if pn.acilim:
                    a = pn.acilim
                    out[(a.tur, a.mahal, tuple(sorted(a.arasi)) if a.arasi else None, a.olcu)] = (d, pn)
        return out
    A, B = acikliklar(ref), acikliklar(plan)
    assert set(A) == set(B) and len(A) == len(ie["acikliklar"]) == 9
    for k in A:
        (da, pa), (db, pb) = A[k], B[k]
        assert (da.yon, round(da.c, 3)) == (db.yon, round(db.c, 3)), k
        assert (pa.acilim.disari_normal, pa.acilim.icine_normal, pa.acilim.mentese) == (pb.acilim.disari_normal, pb.acilim.icine_normal, pb.acilim.mentese), k
        if pa.acilim.tur != "pencere":
            assert G.kapi_varyanti(da, pa.acilim) == G.kapi_varyanti(db, pb.acilim), k
        assert min(pa.a1, pb.a1) - max(pa.a0, pb.a0) > pa.acilim.genislik / 2, k   # aynı yerde (pano ekleri kayabilir)


# --------------------------------------------------------------------------- hata yolları

def test_konum_cm_aks_disi_hata():
    ie = _oku(PK01)
    ie["mahaller"][3]["konum_cm"] = [[261, 256, 386.5, 800]]   # 800 aks değil
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)


def test_dizilim_bilinmeyen_hata():
    ie = _oku(PK01)
    ie["yapi"]["dizilim"] = {"baslangic": "sag-on"}
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)


def test_aciklik_konum_cm_desteklenmiyor_hata():
    """Geometri hakemi önemli 6: açıklıkta konum_cm / hizalama sessizce yutulmaz (K21)."""
    ie = _oku(PK01)
    ie["acikliklar"][4]["konum_cm"] = 120.0
    with pytest.raises(G.IsEmriHatasi, match="konum_cm"):
        G.kur(ie)
