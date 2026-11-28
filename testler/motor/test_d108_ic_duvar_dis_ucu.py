"""D-108 (BK-41, PC-44) · iç duvarın dış duvar ucunda kalan parça (`geometry._ic_duvar_dis_ucu`).

Lokman, 15 Kasım 2026 22:04 UTC (67 m² 2+1'in banyo duvarlarındaki 120,5 + 64,75'e): "bizim standart panomuz 125,5 cm eğer yarısı olan
62,75 den büyük bir sayı alırsan o tam pano sayılır"; 22:21:41: "standart aks düzenimizi bozma sadece sen orada yanlış ölçü vermiştin ...
aynı akstaki 60'lık duvarlar köşe yerleşim planı/kuralından dolayı 5'er santim kesilir ve 59,75 ile başlar wc"; kart 22:28:26 "Doğru,
59,75 başta".

Testler: uydurma 1+1 evde (banyonun ön duvarı ızgaranın 2 cm dışındaki ek aksta, 67 m²'nin banyosu gibi) banyo ile oda arasındaki duvar
120,5 + 64,75 yerine dış duvar ucunda 59,75, köşede 125,5; öteki bütün panolar aynen; depodaki İş Emri'lerinde kural hiçbir aralığı
değiştirmez (aks düzeni aynen); pano harcaması.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

UYDURMA = KOK / "testler/motor/veri/D108_ic_duvar_uydurma.json"
KOKLER = ("is_emri", "testler", "deneme", "araclar/paket/girdi", "beyin/testler")


def _ie(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _is_emri_mi(ie) -> bool:
    return isinstance(ie, dict) and "yapi" in ie and "mahaller" in ie and ie["yapi"].get("sistem", "prefabrik") != "celik"


def _depo() -> list[tuple[Path, str]]:
    """Depodaki bütün prefabrik İş Emri'leri (havuz, hedef örnekler, kör projeler, P6001, 6×8, Yan 6×8,5, denemeler; bir kaydın içindeki
    `is_emri` dahil); uydurma ev hariç. Öğe: (yol, iç anahtar ya da "")."""
    out = []
    for kok in KOKLER:
        for y in sorted((KOK / kok).rglob("*.json")):
            if y == UYDURMA:
                continue
            try:
                ie = _ie(y)
            except (ValueError, UnicodeDecodeError):
                continue
            if _is_emri_mi(ie):
                out.append((y, ""))
            elif isinstance(ie, dict) and _is_emri_mi(ie.get("is_emri")):
                out.append((y, "is_emri"))
    return out


DEPO = _depo()


def _depo_ie(oge) -> dict:
    yol, ic = oge
    ie = _ie(yol)
    return ie[ic] if ic else ie


def _panolar(plan) -> dict:
    return {(q.duvar.tur, q.duvar.yon, round(q.duvar.c, 4), round(q.a0, 4), round(q.a1, 4)) for q in plan.panolar}


def _kuralsiz(ie: dict, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(G, "_ic_duvar_dis_ucu", lambda plan: [])
        return G.kur(copy.deepcopy(ie))


def test_pano_harcamasi():
    """62,75'ten büyük parça 1 pano, 62,75 ve küçüğü yarım pano (Lokman 22:04)."""
    assert G.pano_harcamasi([120.5, 64.75]) == 2.0
    assert G.pano_harcamasi([59.75, 125.5]) == 1.5
    assert G.pano_harcamasi([62.75]) == 0.5
    assert G.pano_harcamasi([62.76]) == 1.0
    assert G.pano_harcamasi([62.85]) == 1.0
    assert G.YARIM_PANO_CM == G.MOD / 2


def test_uydurma_ev_bugun_120_5_ve_64_75(monkeypatch):
    """Kuralsız Motor uydurma evde 67 m²'nin hatasını verir: banyo ile oda arasındaki duvar köşeden 64,75, arka duvardan 120,5."""
    p = _kuralsiz(_ie(UYDURMA), monkeypatch)
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    assert [round(q.boy, 2) for q in d.panolar] == [64.75, 120.5]
    assert G.pano_harcamasi([q.boy for q in d.panolar]) == 2.0


def test_uydurma_ev_59_75_dis_duvar_ucunda():
    """Kural: dış duvar ucunda 59,75, köşeye 125,5 (kart 22:28:26 "Doğru, 59,75 başta"); yarım pano az harcanır."""
    p = G.kur(_ie(UYDURMA))
    assert p.ic_duvar_dis_ucu == [{"duvar": "ic y 261", "once": [64.75, 120.5], "sonra": [125.5, 59.75]}]
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    arka_yuz = p.H - G.T_DIS
    assert [(round(q.a0, 2), round(q.a1, 2)) for q in d.panolar] == [(316.75, 442.25), (442.25, round(arka_yuz, 2))]
    assert round(d.panolar[-1].boy, 2) == 59.75 and abs(d.panolar[-1].a1 - arka_yuz) < 1e-6   # 59,75 arka dış duvarın iç yüzünde
    assert G.pano_harcamasi([q.boy for q in d.panolar]) == 1.5
    assert p.uyarilar == []


def test_uydurma_ev_oteki_panolar_aynen(monkeypatch):
    """Yalnız o aralığın iki panosu değişir: dış duvarlar, öteki iç duvarlar, açıklıklar, ölçü, odalar ve pano sayısı aynen."""
    ie = _ie(UYDURMA)
    p0, p1 = _kuralsiz(ie, monkeypatch), G.kur(copy.deepcopy(ie))
    a, b = _panolar(p0), _panolar(p1)
    assert len(p0.panolar) == len(p1.panolar)
    assert {k for k in a - b} == {("ic", "y", 261.0, 316.75, 381.5), ("ic", "y", 261.0, 381.5, 502.0)}
    assert {k for k in b - a} == {("ic", "y", 261.0, 316.75, 442.25), ("ic", "y", 261.0, 442.25, 502.0)}
    assert (p0.W, p0.H) == (p1.W, p1.H)
    assert {k: round(m.alan_m2, 4) for k, m in p0.mahaller.items()} == {k: round(m.alan_m2, 4) for k, m in p1.mahaller.items()}
    ac = lambda p: sorted((q.duvar.id, round(q.a0, 4), round(q.a1, 4), tuple(a.tur for a in q.aciklar)) for q in p.panolar if q.aciklar)
    assert ac(p0) == ac(p1)


def test_depo_listesi_bos_degil():
    assert len(DEPO) >= 120


@pytest.mark.parametrize("oge", DEPO, ids=lambda o: str(o[0].relative_to(KOK)) + (f"::{o[1]}" if o[1] else ""))
def test_depodaki_evlerde_kural_bir_sey_degistirmez(oge, monkeypatch):
    """Lokman 22:21:41 "standart aks düzenimizi bozma": depodaki hiçbir İş Emri'nde dış duvar ucunda fazla pano harcayan iç duvar
    aralığı yok; kural hiçbir aralığı değiştirmez (havuz, hedef örnekler, mühürlü evler, P6001, 6×8, kör projeler). Kurallı Motor bir
    İş Emri'ni kuramıyorsa kuralsız Motor da kuramamalı (kural yeni hata getirmez)."""
    ie = _depo_ie(oge)
    try:
        p = G.kur(copy.deepcopy(ie))
    except G.IsEmriHatasi as e:
        with pytest.raises(G.IsEmriHatasi):
            _kuralsiz(ie, monkeypatch)
        pytest.skip(f"Motor bu İş Emri'ni kuralsız da kurmuyor: {e}")
    assert p.ic_duvar_dis_ucu == KURALIN_EVLERI.get(str(oge[0].relative_to(KOK)), [])


# Kuralın yazıldığı gerçek ev: 67 m² 2+1 (disk arşivi, D-165 / PA-51). Lokman kat planını bu hâliyle onayladı (kart 28 Kasım 2026
# 09:25:26 UTC "Onaylıyorum, kat planı böyle"; banyo duvarı 59,75 başta, kart 15 Kasım 22:28:26). Değer uydurma evdekiyle aynı.
_D108_67M2 = [{"duvar": "ic y 261", "once": [64.75, 120.5], "sonra": [125.5, 59.75]}]
KURALIN_EVLERI = {"is_emri/adaylar/PA51.json": _D108_67M2, "testler/havuz/is_emirleri/HD259.json": _D108_67M2}


def _varyant(ek: float, t: bool = False) -> dict:
    """Uydurma evin banyo ön duvarı `ek` aksında. `t`: banyo ile oda arasındaki duvar geçen duvara T ile bağlanır (oda tek dikdörtgen,
    salon banyonun önünde boydan boya)."""
    ie = _ie(UYDURMA)
    ie["yapi"]["ek_akslar_cm"]["y"] = [ek]
    for m in ie["mahaller"]:
        m["konum_cm"] = [[c if c != 316.75 else ek for c in r] for r in m["konum_cm"]]
        if t and m["ad"] == "ODA":
            m["konum_cm"] = [[10.0, ek, 261.0, 507.0]]
        if t and m["ad"] == "SALON":
            m["konum_cm"] = [[10.0, 5.0, 512.0, ek]]
    if t:
        for a in ie["acikliklar"]:
            if a.get("mahal") == "ODA":
                a["pano"] = 0
    return ie


def _banyo_yani(p) -> list:
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    return [round(q.boy, 2) for q in d.panolar]


@pytest.mark.parametrize("ek, beklenen", [
    (376.47, [5.03, 120.5]),     # kalan 0,03 cm (kıymık): dokunulmaz, komşu pano 125,5'i aşmaz (D-69)
    (376.5, [5.0, 120.5]),       # tek eksik parça 62,75'ten büyük değil: Okuma 1'in dışında
    (313.72, [67.78, 120.5]),    # 62,78 tam pano: 125,5 + 62,78 de 2 pano harcar, aks düzeni aynen
    (310.75, [70.75, 120.5]),    # kalan 65,75: kazanç yok
])
def test_fazla_harcamayan_ya_da_kiymik_aralik_aynen(ek, beklenen, monkeypatch):
    """Hakem bulguları: yeni dizilim daha az pano harcamıyorsa ya da kalan 0,05 cm'den kısaysa aralık aynen kalır."""
    ie = _varyant(ek)
    p0, p1 = _kuralsiz(ie, monkeypatch), G.kur(copy.deepcopy(ie))
    assert _banyo_yani(p0) == _banyo_yani(p1) == beklenen
    assert p1.ic_duvar_dis_ucu == []


def test_t_ucunda_boy_aks_ustunden(monkeypatch):
    """Öteki uç T ise 125,5 T'nin aksından ölçülür (D-92 gibi; ek ızgara aksında, "standart aks düzenimizi bozma"): T payı uçtaki panodan
    düşer, 122,5 + 62,75."""
    ie = _varyant(313.75, t=True)
    assert _banyo_yani(_kuralsiz(ie, monkeypatch)) == [64.75, 120.5]
    p = G.kur(copy.deepcopy(ie))
    assert _banyo_yani(p) == [122.5, 62.75]
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    assert abs(d.panolar[0].a1 - (313.75 + G.MOD)) < 1e-6    # ek T aksından 125,5'te
    assert G.pano_harcamasi(_banyo_yani(p)) == 1.5
