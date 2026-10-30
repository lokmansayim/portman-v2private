"""Genel motorda sürgülü pencere (Lokman, 30 Ekim 2026, KT-04 bayi paftası: "sürgülü"; prefabrikteki D-31 madde 11'in genel motordaki eşi).

Yapı Tanımı'nda açıklığa isteğe bağlı `acilis: "surgulu"` yazılır (yalnız pencerede ve yalnız bu değer; prefabrik K21 gibi). Görünüşlerde
sürgülü sembol: şablon paftasında ortada bindirmeli iki kanat, sabit kanatta cam işareti, sürülen kanatta kırmızı yön oku; çizim setinin ve
DXF'in görünüşünde kırmızı yön oku. Ölçü, plan simgesi ve yükleme listesi değişmez. Anahtarı yazmayan tanımın çıktısı bayt bayt aynıdır
(altın testler ve `dogrula.py` izleri bunu sınar; burada yalnız yeni davranış)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import ciz_genel, sablon_pafta, yapi  # noqa: E402
from motor.genel import sahne as sahne_m  # noqa: E402

C8801 = json.loads((KOK / "modeller" / "C8801.json").read_text(encoding="utf-8"))


def _tanim(**acilis) -> dict:
    t = json.loads(json.dumps(C8801))
    for a in t["acikliklar"]:
        if a["ad"] in acilis:
            a["acilis"] = acilis[a["ad"]]
    return t


def test_acilis_yalniz_pencerede_ve_yalniz_surgulu():
    with pytest.raises(SystemExit, match="surgulu"):
        yapi.kur(_tanim(K2="surgulu"))
    with pytest.raises(SystemExit, match="surgulu"):
        yapi.kur(_tanim(P1="vasistas"))


class _Kayit:
    """`sablon_pafta.Sayfa` yerine: çizgi ve çokgen çağrılarını sayar."""
    def __init__(self):
        self.cizgiler, self.cokgenler = [], []

    def cizgi(self, x0, y0, x1, y1, renk="black", lw=0.72, ls="-", z=3, **k):
        self.cizgiler.append((renk, ls))

    def cokgen(self, pts, fc, ec="black", lw=0.72, z=2, ls="-"):
        self.cokgenler.append(pts)


def test_sablon_paftasinda_surgulu_sembol():
    P = lambda u, z: (u, z)                                                  # noqa: E731
    acilir, surgulu = _Kayit(), _Kayit()
    sablon_pafta.pencere_gorunus(acilir, P, 0, 200, 10, 190, 200)
    sablon_pafta.pencere_gorunus(surgulu, P, 0, 200, 10, 190, 200, "surgulu")
    kesik = lambda k: [c for c in k.cizgiler if c[0] == sablon_pafta.KIRMIZI and c[1] != "-"]   # noqa: E731  açılır kanadın kesik üçgeni
    duz = lambda k: [c for c in k.cizgiler if c[0] == sablon_pafta.KIRMIZI and c[1] == "-"]     # noqa: E731  sürgülünün yön oku
    assert len(kesik(acilir)) == 4 and not duz(acilir)
    assert not kesik(surgulu) and len(duz(surgulu)) == 4                     # gövde, kuyruk çentiği, iki uç
    assert len(surgulu.cokgenler) == 4                                       # dış kasa, iç kasa, bindirmeli iki kanat


def test_sahne_ogesi_acilisi_tasir_yoksa_ayni():
    y = yapi.kur(_tanim(P1="surgulu"))
    y0 = yapi.kur(_tanim())
    from motor.genel import cati_genel
    S = sahne_m.sahne_kur(y, cati_genel.cati_kur(C8801["cati"]))
    S0 = sahne_m.sahne_kur(y0, cati_genel.cati_kur(C8801["cati"]))
    assert {s.get("acilis") for s in S if s["ad"] == "P1"} == {"surgulu"}
    assert not any("acilis" in s for s in S0)
    assert [{k: v for k, v in s.items() if k != "acilis"} for s in S] == S0


def test_yon_oku_sag_kanatta():
    ok = ciz_genel.surgulu_oku([(0, 10), (200, 10), (200, 190), (0, 190)])
    assert ok[0] == ((125.0, 100.0), (175.0, 100.0)) and len(ok) == 4


def test_uret_liste_ayni_gorunus_farkli(tmp_path):
    """Uçtan uca: Ç8801'in üç büyük penceresi sürgülü; yükleme listesi ve plan aynı, şablon paftası ile görünüş farklı."""
    cikti = {}
    for ad, t in (("acilir", _tanim()), ("surgulu", _tanim(P1="surgulu", P5="surgulu", P9="surgulu"))):
        tp = tmp_path / f"{ad}.json"
        tp.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "motor.genel.uret", str(tp), str(tmp_path / ad), "--perspektifsiz"], cwd=KOK,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
        cikti[ad] = tmp_path / ad
    gk = "C8801"
    liste = lambda k: json.loads((cikti[k] / f"{gk}_yukleme.json").read_text(encoding="utf-8"))["satirlar"]   # noqa: E731
    assert liste("acilir") == liste("surgulu")
    oku = lambda k, ad: (cikti[k] / ad).read_bytes()                                                         # noqa: E731
    assert oku("acilir", f"{gk}_plan.png") == oku("surgulu", f"{gk}_plan.png")
    assert oku("acilir", f"{gk}_gorunusler.png") != oku("surgulu", f"{gk}_gorunusler.png")
    assert oku("acilir", f"{gk}_pafta_sablon.png") != oku("surgulu", f"{gk}_pafta_sablon.png")
