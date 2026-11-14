"""İE-35 · Tek fiyat kaynağı CRM (D-72, mühür M-15): `araclar/crm_fiyat.py`, `fiyatla.defter_sec`, `vps/crm_fiyat.sh`.

Lokman, 9 Kasım 2026 13:10: "bunu kural olarak al ve mühürle bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları
çek"; "diğer tüm listeler konu dışı"; 13:15 kartı: pencere de CRM'den ("Samet CRM'e eklesin").

Gerçek CRM listesi depoya girmez: anlık görüntü burada sahte, eşlemedeki her kod için uydurma fiyatla kurulur. Sınanan: eşleme
tutarlı ve fiyat yazmaz, defterin bütün kalemlerini kapsar; hesaplar (aynı, oran, çarp, boy, ortalama, toplam; kuruşa, kutu profil tam
TL'ye); fiyatı 0 ya da kodu olmayan kalem fiyatsız; onay eşleme türünden; kaynak yalnız CRM (ve D-65 çırpı ipi); kaynaksız teklif
durur; günlük çekim betiği (sahte curl ve rclone) ve kurulum betiği (sahte systemctl). D-75 (Lokman 10 Kasım 10:01): kutu profil 6
metrelik boyun fiyatından, pencere paneli tam panodan, banyo dolabı şimdilik boş. D-76 (Lokman 10 Kasım 16:51–16:55): KDV oranı
malzeme grubuna göre %20, %10 ya da KDV'siz; CRM fiyatı KDV hariç; oranı bilinmeyen kalemde oran uydurulmaz.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import crm_fiyat as C  # noqa: E402
from araclar import fiyatla as F  # noqa: E402

ESLEME = KOK / "kurallar" / "fiyat" / "crm_esleme.json"
SON_DEFTER = KOK / "kurallar" / "fiyat" / "defter_2026-11.json"
IE_TK04 = KOK / "testler" / "motor" / "veri" / "TK04_r08.json"


def _oku(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _kayitlar(E):
    """(yer, kayıt, anahtar) üçlüleri: kalemler, bant aralıkları, boy kuralları, makas kuralı."""
    for hat, H in E["hatlar"].items():
        for k, g in H["kalemler"].items():
            yield f"{hat} › {k}", g, k
        for b in H.get("bantlar") or []:
            for a in b["araliklar"]:
                yield f"{hat} › bant {b['kalem']}", a, ""
        for b in H.get("boy_onerileri") or []:
            yield f"{hat} › boy", b, ""
        if H.get("makas_kurali"):
            yield f"{hat} › makas", H["makas_kurali"], ""


def sahte_anlik(E: dict) -> dict:
    """Eşlemedeki her kod için bir satır (icerir'li kodda her renk, crm_olcu'lu kodda her ölçü ayrı satır); fiyat kodun sırasından,
    bazıları kuruşlu."""
    kodlar: dict[str, set] = {}
    for _, g, _ in _kayitlar(E):
        if g.get("kod"):
            for k in g["kod"] if isinstance(g["kod"], list) else [g["kod"]]:
                kodlar.setdefault(k, set()).add((g.get("icerir"), g.get("crm_olcu")))
    data, i = [], 0
    for k in sorted(kodlar):
        suzgec = sorted((t for t in kodlar[k] if t != (None, None)), key=lambda t: (t[0] or "", t[1] or "")) or [(None, None)]
        for r, o in suzgec:
            i += 1
            data.append({"id": i, "urunkodu": k, "urunadi": f"Ürün {k}" + (f" ({r})" if r else ""), "olcu": o or "X", "birim": "Adet",
                         "fiyat": 100 + 7 * i + (0.35 if i % 3 == 0 else 0), "kategori": None})
    return {"success": True, "count": len(data), "currency": "TRY", "generated_at": "2026-11-09T14:27:29+03:00", "data": data}


@pytest.fixture(scope="module")
def E():
    return _oku(ESLEME)


@pytest.fixture(scope="module")
def A(E):
    return sahte_anlik(E)


@pytest.fixture(scope="module")
def D(A, E):
    return C.defter_uret(C.denetle(A), E)


def _fiyat(A, kod, icerir=None, olcu=None):
    return Decimal(str(next(x["fiyat"] for x in A["data"] if x["urunkodu"] == kod and (not icerir or icerir in x["urunadi"])
                            and (not olcu or x["olcu"] == olcu))))


def _kurus(x, adim="0.01"):
    a = Decimal(adim)
    return float((x / a).quantize(Decimal(1), ROUND_HALF_UP) * a)


# ── mühür M-15 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_tek_kaynak_crm(E, A, D, tmp_path):
    """D-72, M-15: tek fiyat kaynağı CRM; öteki listeler konu dışı. Kaynaksız fiyatlama durur (varsayılan defter yok); üretilen defterin
    kaynağı yalnız CRM (çırpı ipi D-65: Lokman'ın kararıyla 0 TL). Kapanmış teklif yalnız açıkça verilen eski defterle."""
    k = E["kaynak"]
    assert (k["tek_kaynak"], k["diger_listeler"], k["yontem"]) == ("CRM", "konu dışı", "POST")
    assert k["adres"] == "https://crm.ikranuryapi.com.tr/api/stok-fiyatlari" and "her gün" in k["cekim"]
    assert [x["soz"] for x in k["lokman"]] == ["bunu kural olarak al ve mühürle bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları çek",
                                               "diğer tüm listeler konu dışı"]
    with pytest.raises(SystemExit) as e:
        F.defter_sec()
    assert "D-72" in str(e.value) and "--crm" in str(e.value)
    p = tmp_path / "anlik.json"
    p.write_text(json.dumps(A, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit):
        F.defter_sec(p, SON_DEFTER)
    assert F.defter_sec(defter=SON_DEFTER)["surum"] == "2026-11-07-r13"
    assert F.defter_sec(crm=p)["surum"] == "CRM 09.11.2026 14:27"
    assert set(D["kaynaklar"]) == {"CRM", "PATRON"}
    for hat, H in D["hatlar"].items():
        for kk, g in H["kalemler"].items():
            if g["fiyat"] is None:
                continue
            assert g["kaynak"] == "CRM" or (g["kaynak"] == "PATRON" and g["fiyat"] == 0 and "D-65" in g["not"]), (hat, kk)
        assert all(b["kaynak"] == "CRM" for b in H["bantlar"] + H.get("boy_onerileri", []))
        assert H.get("makas_kurali") is None or H["makas_kurali"]["kaynak"] == "CRM"
    from araclar import teklif as TK
    with pytest.raises(SystemExit):
        TK.main([str(IE_TK04), str(tmp_path / "t"), "--tavan", "asma"])
    assert not (tmp_path / "t").exists()


# ── eşleme dosyası ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_esleme_tutarli_ve_fiyat_yazmaz(E):
    assert C.esleme_denetle(E) == []
    metin = ESLEME.read_text(encoding="utf-8")
    assert '"fiyat"' not in metin and '"kg_fiyat"' not in metin                 # fiyat her gün CRM'den
    for yer, g, _ in _kayitlar(E):                                            # kararın kendisi (çırpı ipi 0 TL) dışında notta tutar yok
        assert g["esleme"] == "karar" or not re.search(r"\d[\d.]*,?\d* TL|\d\.\d{3}\b", g.get("not") or ""), yer
    assert set(E["esleme_turleri"]) == {"birebir", "kural", "yakın", "birim varsayımı", "birim sorusu", "CRM'de yok", "karar", "bekletme"}


def test_esleme_son_defterin_butun_kalemlerini_kapsar(E):
    """Eşlemenin anahtarları ve birimleri son elle defterin (r13) kalemleri, aynı sırayla; bant, boy ve makas kuralı aynı kalemlerde.
    D-72'den sonra yeni kalem (Motor'un listesinde olup defterde olmayan anahtar) yalnız eşlemeye girer: kapanmış defter değişmez. Yeni
    anahtarlar defterin kalemlerinden sonra gelir (PR-5, TK-06'nın 15 anahtarı; `test_pr5_tk06_anahtarlari`; r06, metal kiremit vidası;
    `test_r06_mahya_bandi_ve_metal_kiremit_vidasi`; r07, 280 ve 300 cm yükseklik; `test_r07_280_ve_300_yukseklik`; r08, fugalı dış
    cephe; `test_r08_fugali_duz_desen`). Yeni bant da defterin bantlarından sonra gelir (r07, r08)."""
    S = _oku(SON_DEFTER)
    for hat in ("prefabrik", "celik"):
        H, R = E["hatlar"][hat], S["hatlar"][hat]
        assert list(H["kalemler"])[:len(R["kalemler"])] == list(R["kalemler"]) and H["anahtar"] == R["anahtar"] and H["atla"] == R["atla"]
        assert {k: H["kalemler"][k]["birim"] for k in R["kalemler"]} == {k: g["birim"] for k, g in R["kalemler"].items()}
        assert set(H["kalemler"]) - set(R["kalemler"]) == \
            (set(PR5_ANAHTARLAR) | set(R06_ANAHTARLAR) | set(R07_ANAHTARLAR) | set(R08_ANAHTARLAR) if hat == "prefabrik" else set())
        if hat == "prefabrik":                                              # yeni anahtarlar sürüm sırasıyla, sona
            assert list(H["kalemler"])[-len(R08_ANAHTARLAR):] == list(R08_ANAHTARLAR)
        assert [(b["kalem"], b["kalinlik_mm"], b["yukseklik_mm"], [(a["en_mm"], a["alt_haric"]) for a in b["araliklar"]]) for b in H["bantlar"]] == \
               [(b["kalem"], b["kalinlik_mm"], b["yukseklik_mm"], [(a["en_mm"], a.get("alt_haric", False)) for a in b["araliklar"]]) for b in R["bantlar"]] \
               + ([(k, kal, h, [(a[0], a[1]) for a in ar]) for h in (2800, 3000) for k, kal, ar in R07_BANT_ARALIK]
                  + [(R08_BANT, 100, h, R08_BANT_ARALIK) for h in (2500, 2800, 3000)] if hat == "prefabrik" else [])
    P, RP = E["hatlar"]["prefabrik"], S["hatlar"]["prefabrik"]
    assert [(b.get("kalem"), b.get("kalem_baslar"), b.get("kapatma_m")) for b in P["boy_onerileri"]] == \
           [(b.get("kalem"), b.get("kalem_baslar"), b.get("kapatma_m")) for b in RP["boy_onerileri"]] + [(None, "Metal kiremit (100 cm kapatır) · ", None)]
    assert {k: P["makas_kurali"][k] for k in ("kalem_baslar", "kg_m", "sacak_mm")} == {k: RP["makas_kurali"][k] for k in ("kalem_baslar", "kg_m", "sacak_mm")}


def test_esleme_denetimi_hatalari_bulur(E):
    X = copy.deepcopy(E)
    P = X["hatlar"]["prefabrik"]["kalemler"]
    P["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]["esleme"] = "tahmin"
    P["H 100 (dış pano eki) | 100 × 100 × 2500"]["agirlik"] = [11]
    P["60'lık alt çerçeve | 60 × 3750"].pop("payda")
    X["kaynak"]["tek_kaynak"] = "L45"
    s = C.esleme_denetle(X)
    assert len(s) == 4 and "tek_kaynak" in s[0]
    with pytest.raises(C.CrmHatasi):
        C.defter_uret(sahte_anlik(E), X)


# ── hesaplar ve onay ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_hesaplar(A, D):
    P, Cl = D["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["celik"]["kalemler"]
    g = P["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]
    assert (g["fiyat"], g["onay"], g["durum"], g["kaynak_satir"]) == (_kurus(_fiyat(A, "YP1")), True, "eşleşti", ["YP1"])
    g = P["H 100 (dış pano eki) | 100 × 100 × 2500"]                         # kulaklı 11 / dübelli 9
    assert (g["fiyat"], g["onay"], g["durum"]) == (_kurus((_fiyat(A, "MA15") * 11 + _fiyat(A, "MA18") * 9) / 20), True, "hesap")
    assert P["60'lık alt çerçeve | 60 × 3750"]["fiyat"] == _kurus(_fiyat(A, "MA64") * 3750 / 2500)
    g = P["Kutu profil (kiriş) 100 × 100 | L 1457,5"]                          # 6 m fiyatından boyla orantı, tam TL (D-36, D-75); kural
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "MA11") * Decimal("1457.5") / 6000, "1"), True)
    assert P["Tek kat çatı paneli · ana çatı | L 5100"]["fiyat"] == _kurus(_fiyat(A, "CG6") * Decimal("5.1"))
    g = P["Besleme kablo borusu | metre"]                                      # NYM'nin iki katı; NYM birimi varsayım → öneri
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "E7") * 2), False)
    assert Cl["Banyo batarya grubu | takım"]["fiyat"] == _kurus(_fiyat(A, "VG5") + _fiyat(A, "VG7"))
    assert P["Silikonize mastik | adet"]["fiyat"] == _kurus(_fiyat(A, "DG14", "beyaz"))
    for c in (P, Cl):
        g = c["Çırpı ipi | adet"]
        assert (g["fiyat"], g["kaynak"], g["onay"], g["durum"]) == (0, "PATRON", True, "Patron verdi")
    g = P["PVC pencere | 120/120"]                                             # 13:15 kartı: pencere de CRM'den; CRM'e eklenene kadar fiyatsız
    assert (g["fiyat"], g["durum"], g["onay"]) == (None, "kaynakta yok", False)
    g = P["Mahya bandı | rulo 10 m"]                                           # Lokman 11 Kasım 11:14:48 kartı: 960 TL bir rulo (10 m)
    assert (g["fiyat"], g["onay"], g["durum"]) == (_kurus(_fiyat(A, "CG23")), True, "hesap")
    for c in (P, Cl):                                                          # Lokman 10 Kasım 16:15 kartı: 4 m parça = CRM fiyatı
        g = c["Metal dere | L 4000"]
        assert (g["fiyat"], g["onay"], g["durum"]) == (_kurus(_fiyat(A, "DR1")), True, "hesap")
    b = D["hatlar"]["prefabrik"]["bantlar"][0]
    assert [(a["en_mm"], a["fiyat"], a["onay"]) for a in b["araliklar"]] == [
        ([627.5, 1250], _kurus(_fiyat(A, "YP1")), True), ([340, 627.5], _kurus(_fiyat(A, "YP4")), True),
        ([225, 225], _kurus(_fiyat(A, "YP1") / 4), False)]
    m = D["hatlar"]["prefabrik"]["makas_kurali"]
    assert (m["kg_fiyat"], m["kg_m"], m["sacak_mm"], m["onay"]) == (_kurus(_fiyat(A, "HM14")), 5.5, 300, False)


def test_d75_kutu_profil_pencere_paneli_banyo_dolabi(E, A, D, tmp_path):
    """D-75 (Lokman 10 Kasım 10:01): "Profili yine 6 metresi kaç paraysa ona göre orantıla"; pencere üst paneli tam panonun (100 ×
    1250 × 2500) 1/5'i, alt paneli 1/3'ü; "Banyo dolabı şimdilik boş kalsın". Kutu profilin CRM fiyatı 6 metrelik boyun fiyatı: her
    kalem ve listede olmayan boy (boy kuralı) fiyat × L ÷ 6000, tam TL, onaylı. Pencere paneli CRM'in kendi satırından değil YP1'den.
    Banyo dolabı CRM'de fiyatı olsa da fiyatsız ve Samet'e giden eksik listesinde yok."""
    P, Cl = D["hatlar"]["prefabrik"], D["hatlar"]["celik"]["kalemler"]
    for k, g in E["hatlar"]["prefabrik"]["kalemler"].items():
        if g.get("kod") in ("MA11", "MA12"):
            boy = Decimal(k.split("| L ")[1].replace(",", "."))
            d = P["kalemler"][k]
            assert (g["esas_boy_mm"], g["esleme"]) == (6000, "kural"), k
            assert (d["fiyat"], d["onay"], d["durum"]) == (_kurus(_fiyat(A, g["kod"]) * boy / 6000, "1"), True, "hesap"), k
    assert P["kalemler"]["Kutu profil (kiriş) 100 × 100 | L 3760"]["fiyat"] == _kurus(_fiyat(A, "MA11") * Decimal("3.76") / 6, "1")
    boy = {b["kalem"]: b for b in P["boy_onerileri"] if b.get("kalem")}
    for ad, kod in (("Kutu profil (kiriş) 100 × 100", "MA11"), ("Özel kutu profil (kolon) 100 × 100", "MA12")):
        b = boy[ad]
        assert (b["boy_mm"], b["fiyat"], b["onay"], b["kaynak_satir"]) == (6000, _kurus(_fiyat(A, kod)), True, [kod])
        s = {"anahtar": f"{ad} | L 3000", "kalem": ad, "olcu": "L 3000"}
        assert F.boy_onerisi_bul(s, P["boy_onerileri"])[1] == _kurus(_fiyat(A, kod) / 2, "1")     # 3 m = 6 m'nin yarısı
    tam = _fiyat(A, "YP1")
    for k, payda in (("Pencere üst panel | 100 × 1250 × 500", 5), ("Pencere alt panel (120/120) | 100 × 1250 × 800", 3),
                     ("Pencere alt panel (120/180) | 100 × 1250 × 200", 3)):
        d = P["kalemler"][k]
        assert (d["fiyat"], d["onay"], d["durum"], d["kaynak_satir"]) == (_kurus(tam / payda), True, "hesap", ["YP1"]), k
    assert not any(g.get("kod") in ("YP13", "YP16") for _, g, _ in _kayitlar(E))
    g = E["hatlar"]["celik"]["kalemler"]["Banyo dolabı | takım"]
    assert (g["kod"], g["esleme"], g["dayanak"]) == (None, "bekletme", "D-75") and "Banyo dolabı şimdilik boş kalsın" in g["not"]
    d = Cl["Banyo dolabı | takım"]
    assert (d["fiyat"], d["kaynak"], d["onay"], d["durum"]) == (None, None, False, "Lokman fiyat verecek")
    B = copy.deepcopy(A)                                   # VG10 CRM'de fiyatlansa da banyo dolabı boş
    B["data"].append({"id": 99998, "urunkodu": "VG10", "urunadi": "Banyo dolabı", "olcu": "X", "birim": "Adet", "fiyat": 4321,
                      "kategori": None})
    B["count"] = len(B["data"])
    assert C.defter_uret(C.denetle(B), E)["hatlar"]["celik"]["kalemler"]["Banyo dolabı | takım"]["fiyat"] is None
    X = C.eksikler(C.denetle(A), E)
    assert "Lokman fiyat verecek" not in X["gruplar"]
    assert not any(r["kalem"] == "Banyo dolabı | takım" for v in X["gruplar"].values() for r in v)
    Y = copy.deepcopy(E)                                   # denetim: bekletme kodsuz ve dayanaklı; esas boy yalnız boy hesabında
    Y["hatlar"]["celik"]["kalemler"]["Banyo dolabı | takım"]["kod"] = "VG10"
    Y["hatlar"]["prefabrik"]["kalemler"]["Kutu profil (kiriş) 100 × 100 | L 3760"]["esas_boy_mm"] = 0
    Y["hatlar"]["prefabrik"]["kalemler"]["Pencere üst panel | 100 × 1250 × 500"]["esas_boy_mm"] = 6000
    assert len(C.esleme_denetle(Y)) == 3


# ── PR-5: TK-06'nın (Doğan Prefabrik) eşlemede olmayan 15 anahtarı ─────────────────────────────────────────────────────────────

PR5_ANAHTARLAR = {
    "OSB 11 mm (çatı) | 1220 × 2440": ("HM41", "birebir"),
    "Duvar alçıpanı beyaz | 1200 × 2500": ("HM38", "birebir"),
    "Duvar alçıpanı yeşil | 1200 × 2500": ("HM39", "birebir"),
    "Kutu profil (kiriş) 100 × 100 | L 3150": ("MA11", "kural"),
    "Kutu profil (kiriş) 100 × 100 | L 4342,5": ("MA11", "kural"),
    "Pencere alt panel (120/100) | 100 × 1250 × 1000": ("YP1", "kural"),
    "Pencere alt panel (120/160) | 100 × 1250 × 400": ("YP1", "kural"),
    "Nem bariyeri | m²": ("HM49", "birim varsayımı"),
    "Alçıpan destek straforu | paket / 60 m²": ("HM48", "birim sorusu"),
    "Özel pencere karkası (120×100) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1000": (None, "CRM'de yok"),
    "Özel pencere karkası (120×160) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1600": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) | 100 × 2500 × 2500": (None, "CRM'de yok"),
    "PVC pencere | 120/100": (None, "CRM'de yok"),
    "PVC pencere | 120/160": (None, "CRM'de yok"),
    "PVC pencere | 160/180": (None, "CRM'de yok"),
}


def test_pr5_tk06_anahtarlari(E, A):
    """TK-06'nın 15 anahtarı: CRM'de aynı ürün birebir; kutu profil ve pencere alt paneli D-75 kuralıyla (kardeşleriyle aynı kayıt);
    nem bariyeri 150 m² paketten m² fiyatı, öneri (onay bekler); destek straforu birim sorusu (CRM paketi 50 m², liste 60 m²); CRM'de
    olmayanlar fiyatsız. Fiyatlı listede öneri toplama girmez, fiyatsız satır "fiyat yok" yazar, sıfır yazmaz (koordinatör, 11 Kasım)."""
    P = E["hatlar"]["prefabrik"]["kalemler"]
    for k, (kod, tur) in PR5_ANAHTARLAR.items():
        assert (P[k]["kod"], P[k]["esleme"]) == (kod, tur), k
    kp, ap = P["Kutu profil (kiriş) 100 × 100 | L 3760"], P["Pencere alt panel (120/120) | 100 × 1250 × 800"]
    assert P["Kutu profil (kiriş) 100 × 100 | L 3150"] == P["Kutu profil (kiriş) 100 × 100 | L 4342,5"] == kp
    assert P["Pencere alt panel (120/100) | 100 × 1250 × 1000"] == P["Pencere alt panel (120/160) | 100 × 1250 × 400"] == ap
    assert all(P[f"PVC pencere | {o}"]["kdv_grubu"] == "Pencereler" for o in ("120/100", "120/160", "160/180"))
    nem = P["Nem bariyeri | m²"]
    assert (nem["hesap"], nem["pay"], nem["payda"], nem["birim"]) == ("oran", 1, 150, "m²")
    assert (E["kdv"]["kodlar"]["HM49"], E["kdv"]["kodlar"]["HM48"]) == ("Membran", "EPS")
    B = kategorili(A)
    for x in B["data"]:                                    # sahte görüntüde bu kodlar CRM'deki gibi
        x.update({"HM49": {"birim": "Paket", "olcu": "150 M2"}, "HM48": {"birim": "Paket", "olcu": "50 M2"}}.get(x["urunkodu"], {}))
    D = C.defter_uret(C.denetle(B), E)
    PD = D["hatlar"]["prefabrik"]["kalemler"]
    assert (PD["Nem bariyeri | m²"]["fiyat"], PD["Nem bariyeri | m²"]["onay"], PD["Nem bariyeri | m²"]["kdv"]) == \
           (_kurus(_fiyat(A, "HM49") / 150), False, 0.2)
    assert (PD["OSB 11 mm (çatı) | 1220 × 2440"]["fiyat"], PD["OSB 11 mm (çatı) | 1220 × 2440"]["onay"]) == (_kurus(_fiyat(A, "HM41")), True)
    for k in ("Alçıpan destek straforu | paket / 60 m²", "PVC pencere | 160/180", "Karkaslı özel pencere panosu (160/180) | 100 × 2500 × 2500"):
        assert PD[k]["fiyat"] is None, k
    from motor import prefabrik_liste as PL
    L = PL.is_emrinden(_oku(IE_TK04))
    ornek = L["satirlar"][0]
    L["satirlar"] = [{**ornek, "kalem": k.split(" | ")[0], "olcu": k.split(" | ")[1], "adet": 3, "birim": "m²" if k.startswith("Nem") else "adet"}
                     for k in PR5_ANAHTARLAR]
    R = F.fiyatla(L, D, "prefabrik")
    s = {f"{x['kalem']} | {x['olcu']}": x for x in R["satirlar"]}
    assert s["Nem bariyeri | m²"]["tutar"] is None and s["Nem bariyeri | m²"]["durum"].startswith("öneri")
    for k in ("Alçıpan destek straforu | paket / 60 m²", "PVC pencere | 160/180", "Karkaslı özel pencere panosu (160/180) | 100 × 2500 × 2500"):
        assert (s[k]["tutar"], s[k]["birim_fiyat"], s[k]["durum"]) == (None, None, "fiyat yok"), k
    assert s["OSB 11 mm (çatı) | 1220 × 2440"]["tutar"] == round(3 * _kurus(_fiyat(A, "HM41")), 2)
    assert R["ozet"]["toplam"] == round(sum(x["tutar"] or 0 for x in R["satirlar"]), 2)


# ── r06: mahya bandının birimi (Lokman'ın kartı) ve metal kiremit vidası (60,8 m² teklifi) ─────────────────────────────────────────

R06_ANAHTARLAR = {"Trapez vida 5,5 × 60 (metal kiremit) | adet": ("V11", "birebir")}


def test_r06_mahya_bandi_ve_metal_kiremit_vidasi(E, A):
    """Lokman 11 Kasım 11:14:48 kartı "960 TL bir rulo (10 m)": iki hatta mahya bandı CRM'deki fiyatla bir rulo, kural (birim sorusu
    kapandı). Motor metal kiremitte vidayı "Trapez vida 5,5 × 60 (metal kiremit)" yazar; CRM'deki V11 (Trapez Sac / Metal Kiremit)
    birebir, trapez sacın vidasıyla aynı kayıt."""
    P, Cl = E["hatlar"]["prefabrik"]["kalemler"], E["hatlar"]["celik"]["kalemler"]
    for g in (P["Mahya bandı | rulo 10 m"], Cl["Mahya bandı | rulo / 10 m"]):
        assert (g["kod"], g["hesap"], g["esleme"], g["birim"]) == ("CG23", "ayni", "kural", "adet")
    for k, (kod, tur) in R06_ANAHTARLAR.items():
        assert (P[k]["kod"], P[k]["esleme"]) == (kod, tur), k
    v = {a: b for a, b in P["Trapez vida 5,5 × 60 (metal kiremit) | adet"].items() if a != "not"}
    assert v == P["Trapez vida 5,5 × 60 (trapez sac) | adet"]
    D = C.defter_uret(C.denetle(kategorili(A)), E)
    PD, CD = D["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["celik"]["kalemler"]
    for g in (PD["Mahya bandı | rulo 10 m"], CD["Mahya bandı | rulo / 10 m"]):
        assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus(_fiyat(A, "CG23")), True, 0.2)
    g = PD["Trapez vida 5,5 × 60 (metal kiremit) | adet"]
    assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus(_fiyat(A, "V11")), True, 0.2)


def test_d79_metal_kiremit_m2_fiyati_ve_boy_adimi(E, A):
    """D-79 (Lokman 11 Kasım 20:24): CRM'deki metal kiremit fiyatı m² fiyatı; levha 100 cm kapatır; boy 50 mm'nin katına yukarı
    tamamlanır (3740 → 3750), levhanın fiyatı m² fiyatı × tamamlanan boy (m). Kural onaylı, her çatının metal kiremidi için."""
    b = [x for x in E["hatlar"]["prefabrik"]["boy_onerileri"] if x.get("kalem_baslar") == "Metal kiremit (100 cm kapatır) · "]
    assert len(b) == 1 and {k: b[0][k] for k in ("kod", "hesap", "boy_mm", "boy_adim_mm", "esleme")} == \
           {"kod": "CG10", "hesap": "ayni", "boy_mm": 1000, "boy_adim_mm": 50, "esleme": "kural"}
    assert [F.boy_tamamla(n, 50) for n in (3740, 3750, 3751, 1550, 1549)] == [3750, 3750, 3800, 1550, 1550]
    D = C.defter_uret(C.denetle(kategorili(A)), E)
    mk = [x for x in D["hatlar"]["prefabrik"]["boy_onerileri"] if x.get("kalem_baslar") == "Metal kiremit (100 cm kapatır) · "]
    assert len(mk) == 1 and (mk[0]["fiyat"], mk[0]["onay"], mk[0]["boy_mm"], mk[0]["boy_adim_mm"], mk[0]["kdv"]) == \
           (_kurus(_fiyat(A, "CG10")), True, 1000, 50, 0.2)
    m2 = Decimal(str(_fiyat(A, "CG10")))
    for olcu, boy_m in (("L 3740", "3.75"), ("L 3750", "3.75"), ("L 2410", "2.45")):
        s = {"kalem": "Metal kiremit (100 cm kapatır) · ana çatı", "olcu": olcu, "adet": 22, "birim": "adet", "grup": "1006"}
        assert F.boy_onerisi_bul(s, D["hatlar"]["prefabrik"]["boy_onerileri"])[1] == _kurus(m2 * Decimal(boy_m)), olcu
    X = copy.deepcopy(E)
    next(x for x in X["hatlar"]["prefabrik"]["boy_onerileri"] if x.get("kalem_baslar", "").startswith("Metal kiremit"))["boy_adim_mm"] = 0
    assert any("boy_adim_mm" in x for x in C.esleme_denetle(X))


# ── r07: 280 ve 300 cm yükseklik (pano 2800 / 3000; koordinatör 13 Kasım 22:46, pano 221 ekstra özellik testi) ───────────────────

R07_ANAHTARLAR = {
    "6'lık köşe direği 60 × 60 | 60 × 60 × 2800": ("MA5", "birebir"),
    "H 100 (dış pano eki) | 100 × 100 × 2800": (("MA16", "MA19"), "kural"),
    "H standart 60 (iç pano eki) | 60 × 60 × 2800": ("MA22", "birebir"),
    "3'lü H 100 × 100 × 60 (dış duvar T'si) | L 2800": (("MA25", "MA28"), "kural"),
    "3'lü H 100 × 100 × 100 (dış duvar T'si) | L 2800": (("MA25", "MA28"), "kural"),
    "3'lü H standart 60 (iç T) | L 2800": ("MA31", "kural"),
    "Çektirme U'su 100 | 100 × 2740": ("MA40", "birebir"),
    "Özel kutu profil (kolon) 100 × 100 | L 2800": ("MA12", "kural"),
    "Pencere üst panel | 100 × 1250 × 800": ("YP1", "kural"),
    "100'lük yapıştırma dolu vasistaslı pano (60/40) | 100 × 1250 × 2800": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (50/50) | 100 × 1250 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (150/180) | 100 × 2500 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) | 100 × 2500 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (170/180) | 100 × 2125 × 2800": (None, "CRM'de yok"),
    "10'luk köşe direği 100 × 100 | 100 × 100 × 3000": ("MA3", "birebir"),
    "6'lık köşe direği 60 × 60 | 60 × 60 × 3000": ("MA6", "birebir"),
    "H 100 (dış pano eki) | 100 × 100 × 3000": (("MA17", "MA20"), "kural"),
    "H standart 100 (iç pano eki) | 100 × 100 × 3000": (("MA17", "MA20"), "kural"),
    "H standart 60 (iç pano eki) | 60 × 60 × 3000": ("MA23", "birebir"),
    "3'lü H 100 × 100 × 60 (dış duvar T'si) | L 3000": (("MA26", "MA29"), "kural"),
    "3'lü H 100 × 100 × 100 (dış duvar T'si) | L 3000": (("MA26", "MA29"), "kural"),
    "3'lü H standart 60 (iç T) | L 3000": ("MA32", "kural"),
    "3'lü H standart 100 (iç T) | L 3000": ("MA32", "kural"),
    "Çektirme U'su 100 | 100 × 2940": (None, "CRM'de yok"),
    "Çektirme U'su 100 (iç duvar) | 100 × 2940": (None, "CRM'de yok"),
    "Çektirme U'su 60 | 60 × 2940": (None, "CRM'de yok"),
    "Özel kutu profil (kolon) 100 × 100 | L 3000": ("MA12", "kural"),
    "Pencere üst panel | 100 × 1250 × 1000": ("YP1", "kural"),
    "100'lük yapıştırma dolu vasistaslı pano (60/40) | 100 × 1250 × 3000": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (50/50) | 100 × 1250 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (150/180) | 100 × 2500 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) | 100 × 2500 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (170/180) | 100 × 2125 × 3000": (None, "CRM'de yok"),
    "Metal iniş borusu | L 3000": ("DR13", "birebir"),                 # iniş borusu özelliği metal (yükseklikten bağımsız)
}
R07_BANT_ARALIK = [("100'lük yapıştırma dolu pano", 100, [([627.5, 1250], True), ([340, 627.5], False), ([225, 225], False)]),
                   ("60'lık yapıştırma dolu pano", 60, [([627.5, 1250], True), ([350, 627.5], False), ([175, 320], False)]),
                   ("60'lık karkaslı + kasalı pano", 60, [([1070, 1250], False)]),
                   ("100'lük karkaslı + kasalı pano", 100, [([1070, 1250], False)]),
                   ("Karkaslı çelik kapı panosu", 100, [([1070, 1250], False)])]
R07_BANT_KOD = {2800: ["YP2", "YP5", "YP2", "YP8", "YP11", "YP8", "KP2", "KP11", "KP11"],
                3000: ["YP3", "YP6", "YP3", "YP9", "YP12", "YP9", "KP3", "KP12", "KP12"]}
R07_YAPISTIRMA, R07_KAPI = ("YP3", "YP6", "YP8", "YP9", "YP11", "YP12"), ("KP2", "KP3", "KP12")
HAVUZ = KOK / "is_emri" / "adaylar"


def _kod(g):
    return tuple(g["kod"]) if isinstance(g["kod"], list) else g["kod"]


def test_r07_280_ve_300_yukseklik(E, A):
    """280 ve 300 cm yükseklikte (pano 2800 / 3000) havuz evlerinin listesinde eşlemede olmayan satırlar vardı: pano, H, 3'lü H, köşe
    direği, çektirme U'su, kolon, pencere üst paneli; fiyatsız satır toplama girmediği için 280'in teklifi 250'ninkinden düşük çıkıyordu.
    r07 CRM'deki h:2800 / h:3000 ürünlerine eşler, fiyat yazmaz: tam/yarım pano bandı (Patron 27 Ekim 22:08), H ve 3'lü H'da kulaklı /
    dübelli ortalaması (defterin 2500'deki kuralı), D-36 (100'lük iç eleman dıştakinin fiyatı), köşe direği ve standart H birebir, kolon
    D-75. Pencere üst paneli 800 / 1000: aynı ölçüdeki alt panelin kuralı, tam panonun 1/3'ü (Lokman 14 Kasım 07:28:15 kartı). CRM'de olmayan
    (vasistaslı pano, karkaslı özel pencere panosu, 2940'lık çektirme U'su) fiyatsız. Listede 280 ve 300'ün yeni satırı "defterde yok"
    kalmaz."""
    P = E["hatlar"]["prefabrik"]
    K = P["kalemler"]
    for k, (kod, tur) in R07_ANAHTARLAR.items():
        assert (_kod(K[k]), K[k]["esleme"]) == (kod, tur), k
    for h in (2800, 3000):
        assert K[f"Özel kutu profil (kolon) 100 × 100 | L {h}"] == K["Özel kutu profil (kolon) 100 × 100 | L 2500"]
        bant = [b for b in P["bantlar"] if b["yukseklik_mm"] == h and b["kalem"] in {x[0] for x in R07_BANT_ARALIK}]
        assert [a["kod"] for b in bant for a in b["araliklar"]] == R07_BANT_KOD[h]
        assert [a["esleme"] for b in bant for a in b["araliklar"]] == ["kural", "kural", "yakın"] * 2 + ["kural"] * 3
        for k in (f"H 100 (dış pano eki) | 100 × 100 × {h}", f"3'lü H 100 × 100 × 60 (dış duvar T'si) | L {h}"):
            k25 = k.replace(str(h), "2500")
            assert (K[k]["hesap"], K[k]["agirlik"]) == (K[k25]["hesap"], K[k25]["agirlik"]), k
        assert {a: K[f"3'lü H 100 × 100 × 100 (dış duvar T'si) | L {h}"][a] for a in ("kod", "agirlik")} == \
               {a: K[f"3'lü H 100 × 100 × 60 (dış duvar T'si) | L {h}"][a] for a in ("kod", "agirlik")}            # D-36
    assert {a: K["H standart 100 (iç pano eki) | 100 × 100 × 3000"][a] for a in ("kod", "hesap", "agirlik")} == \
           {a: K["H 100 (dış pano eki) | 100 × 100 × 3000"][a] for a in ("kod", "hesap", "agirlik")}                 # D-36
    for ust, alt in ((800, "Pencere alt panel (120/120) | 100 × 1250 × 800"), (1000, "Pencere alt panel (120/100) | 100 × 1250 × 1000")):
        g = K[f"Pencere üst panel | 100 × 1250 × {ust}"]
        assert {a: g[a] for a in ("kod", "hesap", "pay", "payda")} == {a: K[alt][a] for a in ("kod", "hesap", "pay", "payda")}
        assert g["esleme"] == "kural" and "07:28:15" in g["not"] and "Tam panonun 1/3'ü" in g["not"]
    D = C.defter_uret(C.denetle(kategorili(A)), E)
    PD = D["hatlar"]["prefabrik"]
    g = PD["kalemler"]["H 100 (dış pano eki) | 100 × 100 × 2800"]
    assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus((_fiyat(A, "MA16") * 11 + _fiyat(A, "MA19") * 9) / 20), True, 0.2)
    g = PD["kalemler"]["6'lık köşe direği 60 × 60 | 60 × 60 × 3000"]
    assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus(_fiyat(A, "MA6")), True, 0.2)
    g = PD["kalemler"]["Pencere üst panel | 100 × 1250 × 800"]
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "YP1") / 3), True)
    for k in ("Çektirme U'su 100 | 100 × 2940", "100'lük yapıştırma dolu vasistaslı pano (60/40) | 100 × 1250 × 3000"):
        assert PD["kalemler"][k]["fiyat"] is None, k
    b = next(b for b in PD["bantlar"] if (b["kalem"], b["yukseklik_mm"]) == ("100'lük yapıştırma dolu pano", 3000))
    assert [(a["fiyat"], a["onay"], a["kdv"]) for a in b["araliklar"]] == [
        (_kurus(_fiyat(A, "YP3")), True, 0.2), (_kurus(_fiyat(A, "YP6")), True, 0.2), (_kurus(_fiyat(A, "YP3") / 4), False, 0.2)]
    b = next(b for b in PD["bantlar"] if (b["kalem"], b["yukseklik_mm"]) == ("60'lık karkaslı + kasalı pano", 2800))
    assert [(a["fiyat"], a["onay"], a["kdv"]) for a in b["araliklar"]] == [(_kurus(_fiyat(A, "KP2")), True, 0.2)]
    assert {a: K["Metal iniş borusu | L 3000"][a] for a in ("kod", "hesap", "esleme")} == \
           {a: E["hatlar"]["celik"]["kalemler"]["Dere iniş borusu | L 3000"][a] for a in ("kod", "hesap", "esleme")}
    g = PD["kalemler"]["Metal iniş borusu | L 3000"]
    assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus(_fiyat(A, "DR13")), True, 0.2)
    from motor import prefabrik_liste as PL
    KU = PL.kurallari_oku()
    ie = _oku(HAVUZ / "PA01.json")
    ie.setdefault("ozellikler", {})["Yağmur İniş Borusu"] = "Metal"
    s = [s for s in F.fiyatla(PL.is_emrinden(ie, KU), D, "prefabrik")["satirlar"] if s["kalem"] == "Metal iniş borusu"]
    assert len(s) == 1 and s[0]["durum"].startswith("onaylı") and s[0]["tutar"], s
    for ev, ic in (("PA01", 6), ("PA06C", 6), ("PA01", 10)):              # iç 100'lü evde 100'lük iç eleman
        ie0 = _oku(HAVUZ / f"{ev}.json")
        ie0["yapi"].setdefault("duvar_kalinligi_cm", {})["ic"] = ic
        R = {}
        for h in (250, 280, 300):
            ie = copy.deepcopy(ie0)
            ie["yapi"]["duvar_yuksekligi_cm"] = h
            R[h] = F.fiyatla(PL.is_emrinden(ie, KU), D, "prefabrik")
        yok250 = {x["anahtar"] for x in R[250]["ozet"]["fiyatsiz"]}
        for h in (280, 300):
            yeni = [x for x in R[h]["ozet"]["fiyatsiz"] if x["anahtar"] not in yok250]
            assert all(x["anahtar"] in R07_ANAHTARLAR and x["durum"] in ("fiyat yok", "öneri, onay bekliyor") for x in yeni), (ev, ic, h, yeni)
            assert any(f"× {h}" in s["olcu"] and s["durum"].startswith("onaylı") for s in R[h]["satirlar"] if s["olcu"]), (ev, h)

# ── r08: fugalı dış cephe, düz desen (Lokman 14 Kasım 2026 08:16:59 UTC kartı) ─────────────────────────────────────────────────────

R08_ANAHTARLAR = {
    "100'lük yapıştırma dolu vasistaslı pano (60/40) (FUGALI) | 100 × 1250 × 2500": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (50/50) (FUGALI) | 100 × 1250 × 2500": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (60/40) (FUGALI) | 100 × 1250 × 2800": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (50/50) (FUGALI) | 100 × 1250 × 2800": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (60/40) (FUGALI) | 100 × 1250 × 3000": (None, "CRM'de yok"),
    "100'lük yapıştırma dolu vasistaslı pano (50/50) (FUGALI) | 100 × 1250 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (150/180) (FUGALI) | 100 × 2500 × 2500": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) (FUGALI) | 100 × 2500 × 2500": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (170/180) (FUGALI) | 100 × 2125 × 2500": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (150/180) (FUGALI) | 100 × 2500 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) (FUGALI) | 100 × 2500 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (170/180) (FUGALI) | 100 × 2125 × 2800": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (150/180) (FUGALI) | 100 × 2500 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (160/180) (FUGALI) | 100 × 2500 × 3000": (None, "CRM'de yok"),
    "Karkaslı özel pencere panosu (170/180) (FUGALI) | 100 × 2125 × 3000": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1150 × 2500": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1200 × 2500": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1250 × 2500": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1150 × 2800": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1200 × 2800": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1250 × 2800": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1150 × 3000": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1200 × 3000": (None, "CRM'de yok"),
    "Karkaslı çelik kapı panosu (FUGALI) | 100 × 1250 × 3000": (None, "CRM'de yok"),
    "Pencere üst panel (FUGALI) | 100 × 1250 × 500": ("YP19", "kural"),
    "Pencere üst panel (FUGALI) | 100 × 1250 × 800": ("YP19", "kural"),
    "Pencere üst panel (FUGALI) | 100 × 1250 × 1000": ("YP19", "kural"),
    "Pencere alt panel (120/100) (FUGALI) | 100 × 1250 × 1000": ("YP19", "kural"),
    "Pencere alt panel (120/120) (FUGALI) | 100 × 1250 × 800": ("YP19", "kural"),
    "Pencere alt panel (120/160) (FUGALI) | 100 × 1250 × 400": ("YP19", "kural"),
    "Pencere alt panel (120/180) (FUGALI) | 100 × 1250 × 200": ("YP19", "kural"),
    "Pencere alt panel (120/70) (FUGALI) | 100 × 1250 × 1300": ("YP19", "kural"),
    "H'lar için lata (10 mm betopan, oymalı) | 100 × 2500": (None, "CRM'de yok"),
    "Köşe latası | 150 × 2500": ("KG2", "birebir"),
    "Köşe latası | 130 × 2500": ("KG2", "birebir"),
    "Pencere latası | 100 × 2500": ("KG3", "birebir"),
    "Pencere latası | 100 × 2800": ("KG3", "kural"),
}
R08_BANT, R08_BANT_ARALIK = "100'lük yapıştırma dolu pano (FUGALI)", [([627.5, 1250], True), ([340, 627.5], False), ([225, 225], False)]
R08_BANT_KOD = {2500: ["YP19", "YP22", "YP19"], 2800: ["YP20", "YP23", "YP20"], 3000: ["YP21", "YP24", "YP21"]}
R08_YAPISTIRMA = ("YP19", "YP20", "YP21", "YP22", "YP23", "YP24")


def test_r08_fugali_duz_desen(E, A):
    """İş Emri'nin `Açıklama: Fugalı`'sı 100'lük dış duvar panolarını "(FUGALI)" adıyla yazar, lata satırları girer; eşlemede bunların
    hiçbiri yoktu ("defterde yok"). CRM'de fugalı pano iki desende (düz YP19–YP24, ahşap YP25–YP30); Lokman'ın kartı (14 Kasım 08:16:59,
    "Düz desen"): düz desen. r08 fiyat yazmaz: tam / yarım pano bandı düz desenin h:2500 / 2800 / 3000 panosu (Patron 27 Ekim 22:08),
    çeyrek tamın 1/4'ü öneri; fugalı pencere üst / alt paneli düz kaplamalı panelin kuralıyla (D-75) fugalı tam panodan; köşe latası
    `KG2` iki satırda, satır ölçüsüyle (`crm_olcu`); pencere latası 2500 `KG3` birebir, 2800 boyla orantılı (pencere panelleri ve 2800'lük
    lata Lokman'ın 08:28:03 kartıyla onaylı, "İkisi de onaylı");
    CRM'de olmayan (vasistaslı pano, karkaslı özel pencere panosu, fugalı dış çelik kapı panosu, H latası) fiyatsız. Lata KDV'si
    `Betopan` (okuma; Lokman'ın sözü değil). Havuz evinde fugalının yeni satırı "defterde yok" kalmaz."""
    P = E["hatlar"]["prefabrik"]
    K = P["kalemler"]
    for k, (kod, tur) in R08_ANAHTARLAR.items():
        assert (_kod(K[k]), K[k]["esleme"]) == (kod, tur), k
    for h, kodlar in R08_BANT_KOD.items():
        (b,) = [b for b in P["bantlar"] if (b["kalem"], b["yukseklik_mm"]) == (R08_BANT, h)]
        assert [a["kod"] for a in b["araliklar"]] == kodlar and [a["esleme"] for a in b["araliklar"]] == ["kural", "kural", "yakın"]
        assert all("08:16:59" in a["not"] and "Düz desen" in a["not"] for a in b["araliklar"][:2])
        assert b["araliklar"][2]["carpan"] == 0.25
    for k, g in K.items():
        if k.startswith(("Pencere üst panel (FUGALI)", "Pencere alt panel (")) and "(FUGALI)" in k:
            duz = K[k.replace(" (FUGALI)", "")] if k.replace(" (FUGALI)", "") in K else None
            assert (g["kod"], g["hesap"], g["pay"], g["esleme"]) == ("YP19", "oran", 1, "kural"), k
            assert "08:28:03" in g["not"] and "İkisi de onaylı" in g["not"], k
            if duz:                                                     # düz kaplamalı panelin oranı, tam pano YP1 yerine YP19
                assert (duz["kod"], duz["pay"], duz["payda"]) == ("YP1", 1, g["payda"]), k
    assert K["Köşe latası | 150 × 2500"]["crm_olcu"] == "150*2500" and K["Köşe latası | 130 × 2500"]["crm_olcu"] == "130*2500"
    assert {E["kdv"]["kodlar"][k] for k in ("KG2", "KG3")} == {"Betopan"} and any(y.startswith("KG2, KG3") for y in E["kdv"]["okuma"]["yerler"])
    D = C.defter_uret(C.denetle(kategorili(A)), E)
    PD = D["hatlar"]["prefabrik"]
    b = next(b for b in PD["bantlar"] if (b["kalem"], b["yukseklik_mm"]) == (R08_BANT, 2800))
    assert [(a["fiyat"], a["onay"], a["kdv"]) for a in b["araliklar"]] == [
        (_kurus(_fiyat(A, "YP20")), True, 0.2), (_kurus(_fiyat(A, "YP23")), True, 0.2), (_kurus(_fiyat(A, "YP20") / 4), False, 0.2)]
    for en in (130, 150):                                               # aynı kod iki satırda: satır ölçüsüyle ayrı fiyat
        g = PD["kalemler"][f"Köşe latası | {en} × 2500"]
        assert (g["fiyat"], g["onay"], g["kdv"], g["kdv_grubu"]) == (_kurus(_fiyat(A, "KG2", olcu=f"{en}*2500")), True, 0.2, "Betopan")
    assert _fiyat(A, "KG2", olcu="130*2500") != _fiyat(A, "KG2", olcu="150*2500")
    g = PD["kalemler"]["Pencere latası | 100 × 2800"]
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "KG3") * 28 / 25), True) and "08:28:03" in E["hatlar"]["prefabrik"]["kalemler"]["Pencere latası | 100 × 2800"]["not"]
    g = PD["kalemler"]["Pencere üst panel (FUGALI) | 100 × 1250 × 500"]
    assert (g["fiyat"], g["onay"], g["kdv"]) == (_kurus(_fiyat(A, "YP19") / 5), True, 0.2)
    g = PD["kalemler"]["Pencere alt panel (120/120) (FUGALI) | 100 × 1250 × 800"]
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "YP19") / 3), True)
    for k in ("Karkaslı çelik kapı panosu (FUGALI) | 100 × 1250 × 2500", "H'lar için lata (10 mm betopan, oymalı) | 100 × 2500"):
        assert PD["kalemler"][k]["fiyat"] is None and PD["kalemler"][k]["durum"] == "kaynakta yok", k
    B = copy.deepcopy(A)                                                # süzgeçsiz: iki satır, kod belirsiz → fiyatsız
    X = copy.deepcopy(E)
    X["hatlar"]["prefabrik"]["kalemler"]["Köşe latası | 130 × 2500"].pop("crm_olcu")
    assert C.defter_uret(C.denetle(B), X)["hatlar"]["prefabrik"]["kalemler"]["Köşe latası | 130 × 2500"]["durum"] == "CRM'de kod yok"
    X["hatlar"]["prefabrik"]["kalemler"]["Köşe latası | 150 × 2500"]["crm_olcu"] = " "
    assert any("crm_olcu" in x for x in C.esleme_denetle(X))
    from motor import prefabrik_liste as PL
    KU = PL.kurallari_oku()
    for ev in ("PA01", "PA06C", "PA08"):
        ie0 = _oku(HAVUZ / f"{ev}.json")
        for h in (250, 280, 300):
            ie = copy.deepcopy(ie0)
            ie["yapi"]["duvar_yuksekligi_cm"] = h
            R0 = F.fiyatla(PL.is_emrinden(copy.deepcopy(ie), KU), D, "prefabrik")
            ie.setdefault("ozellikler", {})["Açıklama"] = "Fugalı"
            R = F.fiyatla(PL.is_emrinden(ie, KU), D, "prefabrik")
            yok0 = {x["anahtar"] for x in R0["ozet"]["fiyatsiz"]}
            yeni = [x for x in R["ozet"]["fiyatsiz"] if x["anahtar"] not in yok0]
            assert yeni and all(x["anahtar"] in R08_ANAHTARLAR and x["durum"] == "fiyat yok" for x in yeni), (ev, h, yeni)
            fug = [s for s in R["satirlar"] if s["kalem"] == R08_BANT]
            assert fug and all(s["durum"].startswith("onaylı") and s["tutar"] for s in fug), (ev, h)

# ── D-76: KDV ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

KDV_LOKMAN = {**{g: 0.2 for g in ("Metal aksam", "Betopan", "EPS", "Kiremit desen sac", "Boardex", "Alçıpan", "OSB", "Knauf", "Pencereler",
                                  "Vida", "Su tesisatı", "Boya grubu", "Dereler", "Mahya bandı", "Membran", "PVC iniş", "Çelik paneller",
                                  "Shingle", "Çatı izolasyonu")},
              **{g: 0.0 for g in ("İç kapı", "Dış (çelik) kapı", "Elektrik", "Vitrifiye")},
              **{g: 0.1 for g in ("Trapez", "Sandviç panel", "Kutu profil")}}
KDV_KART = {g: 0.2 for g in ("Yapıştırma pano", "Kapı panoları", "Tek kat panel", "Tavan H'ı", "PVC omega kapak", "PVC betopan H'ı",
                             "Acil müdahale kapağı", "Baca")}       # Lokman 10 Kasım 18:01:47 kart: "Hepsi %20, form aynen"
KATEGORI = {"MA": "Metal Aksam Grubu", "E": "Elektrik Grubu", "VG": "Vitrifiye Grubu", "DR": "Dere Grubu", "V": "Vida Grubu",
            "MT": "Mekanik Tesisat", "YP": "Yapıştırma Panel Grubu", "KP": "Karkaslı Kaplamalı Panoları", "CG": "Özel Çatı Grubu",
            "HM": "Ham Malzeme Grubu", "DG": "Depo Grubu", "PK": "Kapı ve Pencere Grubu", "B": "Özel Boya Grubu"}


def kategorili(A: dict) -> dict:
    """Sahte görüntüye CRM'in kategorileri (kod önekinden; gerçek CRM'deki gibi)."""
    B = copy.deepcopy(A)
    for x in B["data"]:
        x["kategori"] = KATEGORI.get(re.match(r"[A-Z]+", x["urunkodu"]).group())
    return B


def test_d76_kdv_gruplari_lokmanin_listesi(E):
    """D-76: eşlemenin KDV grupları ve oranları Lokman'ın listesi (10 Kasım 16:54 el yazısı, 16:55:54 "Çelik Paneller %20, Shingle %20,
    Çatı İzolasynonu %20"), kartı (18:01:47: listede olmayan 8 kalem %20) ve 18:05:03 sözü ("hepsini kural olarak kayda geç"). Kutu profil Metal Aksam kategorisinde olsa da %10; MA10'un
    grubu bilinmiyor (adında kutu profil geçer). Kartın 8 kalemi yalnız kodlarıyla: yapıştırma panel kategorisinin pencere panelleri
    (YP13–YP18) ve karkaslı panoların öteki kodları kartta yok."""
    K = E["kdv"]
    assert (K["dayanak"], K["gruplar"]) == ("D-76", {**KDV_LOKMAN, **KDV_KART})
    assert K["kodlar"]["MA11"] == K["kodlar"]["MA12"] == "Kutu profil" and K["kodlar"]["MA10"] is None
    assert {K["kodlar"][k] for k in ("CG14", "CG2", "HM14", "HM45", "PK2", "PK5")} == \
           {"Trapez", "Sandviç panel", "Çelik paneller", "Çatı izolasyonu", "İç kapı", "Dış (çelik) kapı"}
    kart = {k: g for k, g in K["kodlar"].items() if g in KDV_KART}
    assert kart == {**{k: "Yapıştırma pano" for k in ("YP1", "YP2", "YP4", "YP5", "YP7", "YP10")},
                    **{k: "Kapı panoları" for k in ("KP1", "KP10", "KP11")},
                    **{k: "Yapıştırma pano" for k in R07_YAPISTIRMA}, **{k: "Kapı panoları" for k in R07_KAPI},   # r07: aynı ürünün h:2800 / 3000'i
                    **{k: "Yapıştırma pano" for k in R08_YAPISTIRMA},                                         # r08: fugalı düz desen
                    "CG6": "Tek kat panel", "DG1": "Tavan H'ı",
                    "DG2": "PVC omega kapak", "DG3": "PVC betopan H'ı", "DG11": "Acil müdahale kapağı",
                    **{f"DG{i}": "Baca" for i in range(15, 21)}}
    assert not {"Yapıştırma Panel Grubu", "Karkaslı Kaplamalı Panoları", "Özel Çatı Grubu", "Depo Grubu"} & set(K["kategoriler"])
    # Lokman 18:05:03 "hepsini kural olarak kayda geç": çelik listesinde adı geçmeyen yerler kural (çırpı ipi vida, banyo dolabı vitrifiye)
    assert "18:05:03" in K["listede_adi_yok"]["aciklama"] and "Lokman'ın sözü değildir" in K["okuma"]["aciklama"]
    H = E["hatlar"]
    assert H["prefabrik"]["kalemler"]["Çırpı ipi | adet"]["kdv_grubu"] == H["celik"]["kalemler"]["Çırpı ipi | adet"]["kdv_grubu"] == "Vida"
    assert H["celik"]["kalemler"]["Banyo dolabı | takım"]["kdv_grubu"] == "Vitrifiye"
    pencere = [g for _, g, k in _kayitlar(E) if k.startswith(("PVC pencere", "PVC vasistas"))]
    assert pencere and all(g["kdv_grubu"] == "Pencereler" for g in pencere)
    X = copy.deepcopy(E)
    X["kdv"]["kodlar"]["ZZ1"] = "Uydurma"
    X["kdv"]["kategoriler"]["Depo Grubu"] = None
    X["hatlar"]["prefabrik"]["kalemler"]["Şase pul | adet"]["kdv_grubu"] = "Yok"
    X["kdv"]["gruplar"]["Shingle"] = 18
    assert len(C.esleme_denetle(X)) == 4


def test_d76_kdv_defter_ve_fiyatli_liste(E, A, tmp_path):
    """Defterin her kaydı oranını taşır: kod kaydı, sonra CRM kategorisi. Fiyatlı liste satırda KDV oranı ve tutarı (tutar × oran,
    kuruşa), özette KDV hariç, oranlara göre KDV, KDV dahil; Excel'de KDV sütunları ve KDV DAHİL TOPLAM. Grubu bulunmayan kod (burada
    kayıtları silinmiş yapıştırma panolar) oransız: satırda oran yok, KDV dahil toplam eksik."""
    from openpyxl import load_workbook

    from motor import prefabrik_liste as PL
    B = kategorili(A)
    D = C.defter_uret(C.denetle(B), E)
    assert D["kdv"]["dayanak"] == "D-76" and D["kdv"]["gruplar"] == {**KDV_LOKMAN, **KDV_KART}
    P = D["hatlar"]["prefabrik"]
    beklenen = {"Kutu profil (kiriş) 100 × 100 | L 3760": (0.1, "Kutu profil"),       # MA11 Metal Aksam'da, kod kaydı önce gelir
                "100'lük duvar omegası | 100 × 2500": (0.2, "Metal aksam"),          # kategoriden
                "100'lük yapıştırma dolu pano | 100 × 1250 × 2500": (0.2, "Yapıştırma pano"),   # YP1, kart
                "PVC pencere | 120/120": (0.2, "Pencereler")}                         # kodsuz; kalemin kdv_grubu
    for k, (o, g) in beklenen.items():
        assert (P["kalemler"][k]["kdv"], P["kalemler"][k]["kdv_grubu"]) == (o, g), k
    assert P["kalemler"]["PVC pencere | 120/120"]["fiyat"] is None
    assert {(b.get("kalem") or b["kalem_baslar"]): b["kdv"] for b in P["boy_onerileri"]}["Trapez sac · "] == 0.1
    assert P["makas_kurali"]["kdv"] == 0.2 and {a["kdv"] for b in P["bantlar"] for a in b["araliklar"]} == {0.2}
    L = PL.is_emrinden(_oku(IE_TK04))
    R = F.fiyatla(L, D, "prefabrik")
    k = R["ozet"]["kdv"]
    for s in R["satirlar"]:
        if s["tutar"] is None or s["kdv_orani"] is None:
            assert s["kdv_tutari"] is None
        else:
            assert s["kdv_tutari"] == round(s["tutar"] * s["kdv_orani"], 2)
    assert not [s for s in R["satirlar"] if s["tutar"] and s["kdv_orani"] is None]
    assert k["haric"] == R["ozet"]["toplam"] and k["kdv"] == round(sum(s["kdv_tutari"] or 0 for s in R["satirlar"]), 2)
    assert k["dahil"] == round(k["haric"] + k["kdv"], 2) and k["kdv"] > 0
    assert (k["oransiz"]["satir"], k["eksik"]) == (0, False)
    assert set(k["oranlar"]) <= {"%20", "%10", "%0"} and sum(o["satir"] for o in k["oranlar"].values()) == \
        sum(1 for s in R["satirlar"] if s["tutar"])
    X = copy.deepcopy(E)                                   # grubu bulunmayan kod: oran uydurulmaz
    for kod in ("YP1", "YP2", "YP4", "YP5", "YP7", "YP10"):
        del X["kdv"]["kodlar"][kod]
    RX = F.fiyatla(L, C.defter_uret(C.denetle(B), X), "prefabrik")
    kx = RX["ozet"]["kdv"]
    oransiz = [s for s in RX["satirlar"] if s["tutar"] and s["kdv_orani"] is None]
    assert (kx["oransiz"]["satir"], kx["eksik"]) == (len(oransiz), True) and oransiz
    assert all(s["kalem"].startswith(("100'lük yapıştırma dolu pano", "60'lık yapıştırma dolu pano", "Pencere")) for s in oransiz)
    assert kx["oransiz"]["tutar"] == round(sum(s["tutar"] for s in oransiz), 2)
    assert sum(o["satir"] for o in kx["oranlar"].values()) + len(oransiz) == sum(1 for s in RX["satirlar"] if s["tutar"])
    p = tmp_path / "anlik.json"
    p.write_text(json.dumps(B, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "l.json").write_text(json.dumps(L, ensure_ascii=False), encoding="utf-8")
    assert F.main([str(tmp_path / "l.json"), "--crm", str(p), "--excel", str(tmp_path / "f.xlsx")]) == 0
    hucre = [c for r in load_workbook(tmp_path / "f.xlsx").active.iter_rows(values_only=True) for c in r if c is not None]
    assert "KDV %" in hucre and "KDV DAHİL TOPLAM" in hucre and k["dahil"] in hucre


def test_d76_eski_defter_ve_kdvsiz_esleme_aynen(E, A, tmp_path):
    """Kapanmış teklifin eski defteri (KDV'siz) ve kdv bölümü olmayan eşleme: satırda ve özette KDV yok, Excel'de KDV sütunu yok."""
    from openpyxl import load_workbook

    from motor import prefabrik_liste as PL
    L = PL.is_emrinden(_oku(IE_TK04))
    R = F.fiyatla(L, _oku(SON_DEFTER), "prefabrik")
    assert "kdv" not in R["ozet"] and not any("kdv_orani" in s for s in R["satirlar"])
    X = copy.deepcopy(E)
    X.pop("kdv")
    for _, g, _ in _kayitlar(X):
        g.pop("kdv_grubu", None)
    D = C.defter_uret(C.denetle(kategorili(A)), X)
    assert D["kdv"] == "CRM yanıtında KDV yazmıyor" and not any("kdv" in g for g in D["hatlar"]["prefabrik"]["kalemler"].values())
    assert "kdv" not in F.fiyatla(L, D, "prefabrik")["ozet"]
    (tmp_path / "l.json").write_text(json.dumps(L, ensure_ascii=False), encoding="utf-8")
    assert F.main([str(tmp_path / "l.json"), "--defter", str(SON_DEFTER), "--excel", str(tmp_path / "f.xlsx")]) == 0
    hucre = {c for r in load_workbook(tmp_path / "f.xlsx").active.iter_rows(values_only=True) for c in r if c is not None}
    assert "KDV %" not in hucre and "KDV DAHİL TOPLAM" not in hucre


def test_onay_esleme_turunden(E, D):
    for hat, H in E["hatlar"].items():
        for k, g in H["kalemler"].items():
            d = D["hatlar"][hat]["kalemler"][k]
            if g["esleme"] in ("birebir", "kural", "karar"):
                assert d["onay"] and d["fiyat"] is not None, k
            elif g["esleme"] in ("yakın", "birim varsayımı"):
                assert not d["onay"] and d["fiyat"] is not None, k
            else:
                assert not d["onay"] and d["fiyat"] is None, k


def test_defter_bicimi(D):
    """Üretilen defter elle defterin şemasında (`test_fiyat_defteri.test_defter_bicimi`'nin kuralları; durum adları CRM'in)."""
    assert D["sema"] == "portman.fiyat_defteri/1" and set(D["hatlar"]) == {"prefabrik", "celik"}
    assert all(re.search(r"\d{2}\.\d{2}\.\d{4}$", v["kisa"]) and v["patron_verdi"] for v in D["kaynaklar"].values())
    for hat, H in D["hatlar"].items():
        for k, g in H["kalemler"].items():
            # m²: Motor'un nem bariyeri satırı (PR-5); liste_excel'in BIRIM_SOZCUK'unda zaten var
            assert g["durum"] in set(C.DURUM.values()) | {"CRM'de fiyat 0", "CRM'de kod yok"} and g["birim"] in {"adet", "metre", "m", "kg", "m²"}
            assert g["fiyat"] is None or g["fiyat"] > 0 or (g["fiyat"] == 0 and g["kaynak"] == "PATRON" and g["onay"])
        for b in H["bantlar"]:
            assert all(a["fiyat"] > 0 and a["dayanak"] for a in b["araliklar"])
        for b in H.get("boy_onerileri", []):
            assert b["boy_mm"] > 0 and b["fiyat"] > 0 and ("kalem" in b) != ("kalem_baslar" in b)
    json.dumps(D, ensure_ascii=False)


def test_fiyat_sifir_kod_yok_ve_belirsiz_kod(E, A):
    """Fiyat uydurulmaz: kodun fiyatı 0 ya da boşsa, kod listede yoksa ya da süzgeçsiz birden çok satırdaysa kalem fiyatsız; bant ve
    boy kuralı o gün deftere girmez, `crm.fiyatsiz_kurallar`'da sayılır."""
    B = copy.deepcopy(A)
    for x in B["data"]:
        if x["urunkodu"] == "YP1":
            x["fiyat"] = 0
        if x["urunkodu"] == "CG6":
            x["fiyat"] = None
    B["data"] = [x for x in B["data"] if x["urunkodu"] != "VG2"]
    B["data"].append(dict(next(x for x in B["data"] if x["urunkodu"] == "E7"), id=99999))   # E7 iki satır
    B["count"] = len(B["data"])
    D = C.defter_uret(C.denetle(B), E)
    P, Cl = D["hatlar"]["prefabrik"], D["hatlar"]["celik"]
    assert (P["kalemler"]["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]["fiyat"], P["kalemler"]["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]["durum"]) == (None, "CRM'de fiyat 0")
    assert P["kalemler"]["Tek kat çatı paneli · ana çatı | L 5100"]["durum"] == "CRM'de fiyat 0"
    assert Cl["kalemler"]["Klozet | takım"]["durum"] == "CRM'de kod yok"
    assert P["kalemler"]["NYM kablo 3 × 2,5 | metre"]["durum"] == "CRM'de kod yok"
    assert [a["en_mm"] for a in P["bantlar"][0]["araliklar"]] == [[340, 627.5]]           # YP1'li tam ve çeyrek aralık düştü
    assert not any(b.get("kalem_baslar") == "Tek kat çatı paneli · " for b in P["boy_onerileri"])
    assert {r["yer"] for r in D["crm"]["fiyatsiz_kurallar"]} >= {"bant 100'lük yapıştırma dolu pano [627.5, 1250]", "boy Tek kat çatı paneli · "}
    X = C.eksikler(C.denetle(B), E)
    assert {"CRM'de fiyat 0", "CRM'de kod yok", "kaynakta yok", "birim sorusu"} <= set(X["gruplar"])


# ── anlık görüntü denetimi ────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bozuk", [
    {"success": False}, {"count": 3}, {"currency": "USD"}, {"generated_at": "dün"}, {"data": []},
    {"data": [{"urunkodu": "", "fiyat": 1}]}, {"data": [{"urunkodu": "X", "fiyat": -1}]}, {"data": [{"urunkodu": "X", "fiyat": "12"}]},
    {"data": [{"urunkodu": "X", "fiyat": True}]},
], ids=["success", "count", "para", "zaman", "bos", "kodsuz", "eksi", "metin", "bool"])
def test_denetle_bozuk_yaniti_reddeder(A, bozuk):
    B = dict(copy.deepcopy(A), **bozuk)
    if "data" in bozuk:
        B["count"] = len(bozuk["data"])
    with pytest.raises(C.CrmHatasi):
        C.denetle(B)


def test_denetle_alanlari_daraltir_ve_dususu_durdurur(A):
    B = copy.deepcopy(A)
    B["data"][0]["stok"] = 12
    B["sunucu"] = "x"
    T = C.denetle(B)
    assert set(T) == {"success", "count", "currency", "generated_at", "data"} and all(set(x) == set(C.ALANLAR) for x in T["data"])
    Y = dict(copy.deepcopy(A), data=A["data"][: int(len(A["data"]) * 0.7)])
    Y["count"] = len(Y["data"])
    with pytest.raises(C.CrmHatasi, match="düştü"):
        C.denetle(Y, onceki=A)
    Z = dict(copy.deepcopy(A), data=A["data"][: int(len(A["data"]) * 0.9)])
    Z["count"] = len(Z["data"])
    assert C.denetle(Z, onceki=A)["count"] == Z["count"]


# ── fiyatla ve teklif ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_teklif_crm_ile(A, tmp_path):
    """Yeni teklif --crm ile: defter sürümü CRM'in görüntü zamanı; fiyatlı her satırın kaynağı CRM (çırpı ipi PATRON); Excel'in
    kaynak satırı CRM'i yazar. fiyatla.py da --crm alır."""
    from openpyxl import load_workbook

    from araclar import teklif as TK
    p = tmp_path / "anlik.json"
    p.write_text(json.dumps(A, ensure_ascii=False), encoding="utf-8")
    assert TK.main([str(IE_TK04), str(tmp_path / "t"), "--tavan", "asma", "--tarih", "09.11.2026", "--crm", str(p)]) == 0
    T = _oku(tmp_path / "t" / "TK04_teklif.json")
    assert T["defter_surumu"] == "CRM 09.11.2026 14:27"
    R = T["secenekler"][0]["fiyat"]
    assert {s["kaynak"] for s in R["satirlar"] if s["tutar"] is not None} <= {"CRM", "PATRON"}
    assert R["ozet"]["fiyatli"] > 0 and any(f["anahtar"] == "PVC pencere | 120/120" for f in R["ozet"]["fiyatsiz"])
    wb = load_workbook(tmp_path / "t" / "TK04_teklif.xlsx")
    ozet = [c for r in wb["Özet"].iter_rows(values_only=True) for c in r if isinstance(c, str)]
    assert any(c.startswith("Kaynaklar: CRM stok fiyatları, 09.11.2026") for c in ozet)
    from araclar.liste_excel import formul_degeri          # formüllü Excel (Lokman 11 Kasım 10:54–10:55): KDV ve kâr da formül
    ws, k = wb["Asma tavan"], R["ozet"]["kdv"]
    satir = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}
    deger = {a: formul_degeri(ws, f"F{satir[a]}") for a in ("KDV (kalem grubunun oranıyla)", "KDV DAHİL TOPLAM", "KDV · kâr dahil",
                                                             "TEKLİF TOPLAMI · kâr dahil, KDV dahil")}
    assert list(deger.values()) == [k["kdv"], k["dahil"], k["kdv"], k["dahil"]]
    ws.cell(satir["KÂR MARJI %"], 6).value = 0.1
    assert formul_degeri(ws, f"F{satir['KDV · kâr dahil']}") == round(k["kdv"] * 1.1, 2)
    kdvli = next(r for r in range(3, satir["KDV (kalem grubunun oranıyla)"]) if isinstance(ws.cell(r, 7).value, (int, float)) and ws.cell(r, 7).value)
    assert ws.cell(kdvli, 8).value == f'=IF(AND(ISNUMBER(F{kdvli}),ISNUMBER(G{kdvli})),ROUND(F{kdvli}*G{kdvli},2),"")'
    from motor import prefabrik_liste as PL
    (tmp_path / "l.json").write_text(json.dumps(PL.is_emrinden(_oku(IE_TK04)), ensure_ascii=False), encoding="utf-8")
    assert F.main([str(tmp_path / "l.json"), "--crm", str(p), "--json", str(tmp_path / "f.json")]) == 0
    assert _oku(tmp_path / "f.json")["defter_surumu"] == "CRM 09.11.2026 14:27"


def test_komut_satiri(A, tmp_path, capsys):
    p = tmp_path / "ham.json"
    p.write_text(json.dumps(dict(A, stok_ozeti=1), ensure_ascii=False), encoding="utf-8")
    assert C.main(["denetle", str(p), "--yaz", str(tmp_path / "a.json")]) == 0
    assert "stok_ozeti" not in (tmp_path / "a.json").read_text(encoding="utf-8")
    assert C.main(["defter", str(tmp_path / "a.json"), str(tmp_path / "d.json")]) == 0
    assert _oku(tmp_path / "d.json")["surum"] == "CRM 09.11.2026 14:27"
    assert C.main(["eksik", str(tmp_path / "a.json")]) == 0 and "== kaynakta yok" in capsys.readouterr().out
    assert C.main(["defter", str(tmp_path / "yok.json"), str(tmp_path / "x.json")]) == 1 and "DUR" in capsys.readouterr().err


# ── sunucu betikleri (sahte araçlarla) ────────────────────────────────────────────────────────────────────────────────────────────

SAHTE_CURL = """#!/usr/bin/env bash
# sahte curl: -4 ve POST şart; -o dosyasına PM_SAHTE_YANIT'ı yazar, durum kodu PM_SAHTE_KOD
echo "$@" >> "$PM_ARAC_LOG"
case " $* " in *" -4 "*) ;; *) exit 99 ;; esac
case " $* " in *" -X POST "*) ;; *) exit 98 ;; esac
while [ $# -gt 0 ]; do case "$1" in -o) CIKTI="$2"; shift ;; esac; shift; done
cp "$PM_SAHTE_YANIT" "$CIKTI"; printf '%s' "${PM_SAHTE_KOD:-200}"
"""
SAHTE_RCLONE = '#!/usr/bin/env bash\necho "rclone $*" >> "$PM_ARAC_LOG"\n'
SAHTE_SYSTEMCTL = '#!/usr/bin/env bash\necho "systemctl $*" >> "$PM_ARAC_LOG"\n'


def _arac(d: Path, ad: str, metin: str) -> Path:
    p = d / ad
    p.write_text(metin, encoding="utf-8")
    p.chmod(0o755)
    return p


@pytest.fixture
def sunucu(tmp_path, A):
    d = {k: tmp_path / k for k in ("kok", "etc", "bin", "systemd")}
    for p in d.values():
        p.mkdir()
    (d["etc"] / "rclone.conf").write_text("[portman-drive]\ntype = drive\n", encoding="utf-8")
    yanit = tmp_path / "yanit.json"
    yanit.write_text(json.dumps(A, ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "PM_KOK": str(d["kok"]), "PM_ETC": str(d["etc"]), "PM_GUNCEL": str(KOK), "PM_PYTHON": sys.executable,
           "PM_CURL": str(_arac(d["bin"], "curl", SAHTE_CURL)), "PM_RCLONE": str(_arac(d["bin"], "rclone", SAHTE_RCLONE)),
           "PM_SYSTEMCTL": str(_arac(d["bin"], "systemctl", SAHTE_SYSTEMCTL)), "PM_JOURNALCTL": "true",
           "PM_SYSTEMD_DIR": str(d["systemd"]), "PM_ARAC_LOG": str(tmp_path / "arac.log"), "PM_SAHTE_YANIT": str(yanit)}
    return d, env, yanit


def _kos(betik: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(KOK / "vps" / betik)], env=env, capture_output=True, text=True, timeout=60)


def test_crm_fiyat_sh_gunluk_cekim(sunucu, A):
    d, env, yanit = sunucu
    r = _kos("crm_fiyat.sh", env)
    assert r.returncode == 0, r.stderr
    crm = d["kok"] / "data" / "crm"
    goruntu = sorted(crm.glob("crm_2*.json"))
    assert len(goruntu) == 1 and _oku(crm / "crm_son.json") == _oku(goruntu[0]) == C.denetle(A)
    son = _oku(crm / "son_cekim.json")
    assert son["dosya"] == goruntu[0].name and son["uzak"] == f"portman-drive:Portman-Fiyat/{goruntu[0].name}"
    log = (d["kok"].parent / "arac.log").read_text(encoding="utf-8")
    assert "-4" in log and "https://crm.ikranuryapi.com.tr/api/stok-fiyatlari" in log
    assert f"rclone --config {d['etc']}/rclone.conf copy {goruntu[0]} portman-drive:Portman-Fiyat/" in log
    # 403: görüntü alınmaz, eski fiyatlar yerinde
    r = _kos("crm_fiyat.sh", {**env, "PM_SAHTE_KOD": "403"})
    assert r.returncode == 1 and "HTTP 403" in r.stderr
    # yarım yanıt (kalem %30 düştü): görüntü alınmaz
    yarim = dict(A, data=A["data"][: len(A["data"]) // 2], count=len(A["data"]) // 2)
    yanit.write_text(json.dumps(yarim, ensure_ascii=False), encoding="utf-8")
    r = _kos("crm_fiyat.sh", env)
    assert r.returncode == 1 and "düştü" in r.stderr
    assert sorted(crm.glob("crm_2*.json")) == goruntu and _oku(crm / "crm_son.json") == C.denetle(A)
    assert not list(crm.glob(".gecici*"))
    # rclone.conf yoksa Drive atlanır, görüntü yine alınır
    yanit.write_text(json.dumps(A, ensure_ascii=False), encoding="utf-8")
    (d["etc"] / "rclone.conf").unlink()
    r = _kos("crm_fiyat.sh", env)
    assert r.returncode == 0 and "atlandı" in r.stdout


def test_crm_fiyat_kur_sh(sunucu):
    d, env, _ = sunucu
    (d["kok"] / "data" / "crm").mkdir(parents=True)
    r = _kos("crm_fiyat_kur.sh", env)
    assert r.returncode == 0, r.stderr
    for b in ("portman-crm-fiyat.service", "portman-crm-fiyat.timer"):
        assert (d["systemd"] / b).read_bytes() == (KOK / "vps" / "systemd" / b).read_bytes()
    log = (d["kok"].parent / "arac.log").read_text(encoding="utf-8")
    assert "systemctl enable --now portman-crm-fiyat.timer" in log and "systemctl start portman-crm-fiyat.service" in log
    r = _kos("crm_fiyat_kur.sh", env)
    assert r.returncode == 0 and r.stdout.count("aynı, dokunulmadı") == 2


def test_zamanlayici_her_gun_ve_kurulumda_gomulu():
    t = (KOK / "vps" / "systemd" / "portman-crm-fiyat.timer").read_text(encoding="utf-8")
    assert "OnCalendar=*-*-* 06:15:00" in t and "Persistent=true" in t
    for b in ("portman-crm-fiyat.service", "portman-crm-fiyat.timer"):
        r = subprocess.run(["bash", "-c", f'source "{KOK}/vps/kurulum.sh"; birim_sablon {b}'], env={**os.environ, "PM_YALNIZ_ISLEVLER": "1"},
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and r.stdout == (KOK / "vps" / "systemd" / b).read_text(encoding="utf-8"), b
    k = (KOK / "vps" / "kurulum.sh").read_text(encoding="utf-8")
    assert re.search(r"enable [^\n]*portman-crm-fiyat\.timer", k) and "portman-crm-fiyat.service portman-crm-fiyat.timer\"" in k
