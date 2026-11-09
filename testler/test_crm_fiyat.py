"""İE-35 · Tek fiyat kaynağı CRM (D-72, mühür M-15): `araclar/crm_fiyat.py`, `fiyatla.defter_sec`, `vps/crm_fiyat.sh`.

Lokman, 9 Kasım 2026 13:10: "bunu kural olarak al ve mühürle bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları
çek"; "diğer tüm listeler konu dışı"; 13:15 kartı: pencere de CRM'den ("Samet CRM'e eklesin").

Gerçek CRM listesi depoya girmez: anlık görüntü burada sahte, eşlemedeki her kod için uydurma fiyatla kurulur. Sınanan: eşleme
tutarlı ve fiyat yazmaz, defterin bütün kalemlerini kapsar; hesaplar (aynı, oran, çarp, boy, ortalama, toplam; kuruşa, kutu profil tam
TL'ye); fiyatı 0 ya da kodu olmayan kalem fiyatsız; onay eşleme türünden; kaynak yalnız CRM (ve D-65 çırpı ipi); kaynaksız teklif
durur; günlük çekim betiği (sahte curl ve rclone) ve kurulum betiği (sahte systemctl).
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
    """Eşlemedeki her kod için bir satır (icerir'li kodda her renk ayrı satır); fiyat kodun sırasından, bazıları kuruşlu."""
    kodlar: dict[str, set] = {}
    for _, g, _ in _kayitlar(E):
        if g.get("kod"):
            for k in g["kod"] if isinstance(g["kod"], list) else [g["kod"]]:
                kodlar.setdefault(k, set()).add(g.get("icerir"))
    data, i = [], 0
    for k in sorted(kodlar):
        renkler = sorted(r for r in kodlar[k] if r) or [None]
        for r in renkler:
            i += 1
            data.append({"id": i, "urunkodu": k, "urunadi": f"Ürün {k}" + (f" ({r})" if r else ""), "olcu": "X", "birim": "Adet",
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


def _fiyat(A, kod, icerir=None):
    return Decimal(str(next(x["fiyat"] for x in A["data"] if x["urunkodu"] == kod and (not icerir or icerir in x["urunadi"]))))


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
    assert set(E["esleme_turleri"]) == {"birebir", "kural", "yakın", "birim varsayımı", "birim sorusu", "CRM'de yok", "karar"}


def test_esleme_son_defterin_butun_kalemlerini_kapsar(E):
    """Eşlemenin anahtarları ve birimleri son elle defterin (r13) kalemleri; bant, boy ve makas kuralı aynı kalemlerde."""
    S = _oku(SON_DEFTER)
    for hat in ("prefabrik", "celik"):
        H, R = E["hatlar"][hat], S["hatlar"][hat]
        assert list(H["kalemler"]) == list(R["kalemler"]) and H["anahtar"] == R["anahtar"] and H["atla"] == R["atla"]
        assert {k: g["birim"] for k, g in H["kalemler"].items()} == {k: g["birim"] for k, g in R["kalemler"].items()}
        assert [(b["kalem"], b["kalinlik_mm"], b["yukseklik_mm"], [(a["en_mm"], a["alt_haric"]) for a in b["araliklar"]]) for b in H["bantlar"]] == \
               [(b["kalem"], b["kalinlik_mm"], b["yukseklik_mm"], [(a["en_mm"], a.get("alt_haric", False)) for a in b["araliklar"]]) for b in R["bantlar"]]
    P, RP = E["hatlar"]["prefabrik"], S["hatlar"]["prefabrik"]
    assert [(b.get("kalem"), b.get("kalem_baslar"), b.get("kapatma_m")) for b in P["boy_onerileri"]] == \
           [(b.get("kalem"), b.get("kalem_baslar"), b.get("kapatma_m")) for b in RP["boy_onerileri"]]
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
    g = P["Kutu profil (kiriş) 100 × 100 | L 1457,5"]                          # boyla orantı, tam TL (D-36); birim varsayımı → öneri
    assert (g["fiyat"], g["onay"]) == (_kurus(_fiyat(A, "MA11") * Decimal("1457.5") / 1000, "1"), False)
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
    g = P["Metal dere | L 4000"]
    assert (g["fiyat"], g["durum"]) == (None, "birim sorusu")
    b = D["hatlar"]["prefabrik"]["bantlar"][0]
    assert [(a["en_mm"], a["fiyat"], a["onay"]) for a in b["araliklar"]] == [
        ([627.5, 1250], _kurus(_fiyat(A, "YP1")), True), ([340, 627.5], _kurus(_fiyat(A, "YP4")), True),
        ([225, 225], _kurus(_fiyat(A, "YP1") / 4), False)]
    m = D["hatlar"]["prefabrik"]["makas_kurali"]
    assert (m["kg_fiyat"], m["kg_m"], m["sacak_mm"], m["onay"]) == (_kurus(_fiyat(A, "HM14")), 5.5, 300, False)


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
            assert g["durum"] in set(C.DURUM.values()) | {"CRM'de fiyat 0", "CRM'de kod yok"} and g["birim"] in {"adet", "metre", "m", "kg"}
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
    ozet = [c for r in load_workbook(tmp_path / "t" / "TK04_teklif.xlsx")["Özet"].iter_rows(values_only=True) for c in r if isinstance(c, str)]
    assert any(c.startswith("Kaynaklar: CRM stok fiyatları, 09.11.2026") for c in ozet)
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
