"""CI parçaları (BK-43): pytest dosyaları parçalara bölünürken hiçbir dosya dışarıda kalmaz, hiçbiri iki parçada koşmaz.

`araclar/pytest_parca.py` bir dosyanın parçasını yalnız kendi yolundan bulur; `dogrulama.yml`'deki parça işleri 1/N … N/N'dir ve
kalıcı akış klasörü ayrı işte koşar. Bu test üçünü birlikte denetler: iş akışında bir parça eksilir ya da haritanın N'si iş akışınkiyle
ayrışırsa kırmızı olur."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
IS_AKISI = KOK / ".github" / "workflows" / "dogrulama.yml"

_spec = importlib.util.spec_from_file_location("pytest_parca_eklentisi", KOK / "araclar" / "pytest_parca.py")
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def _dilimler() -> list[str]:
    return re.findall(r"dilim:\s*([0-9]+/[0-9]+)\s*\}", IS_AKISI.read_text(encoding="utf-8"))


def test_is_akisindaki_parcalar_1den_nye_eksiksiz():
    d = _dilimler()
    assert d, "dogrulama.yml'de parça işi (dilim: k/N) yok"
    n = {int(x.split("/")[1]) for x in d}
    assert len(n) == 1, f"parçaların N'si tek olmalı: {d}"
    n = n.pop()
    assert sorted(d, key=lambda x: int(x.split("/")[0])) == [f"{k}/{n}" for k in range(1, n + 1)], d


def test_is_akisi_kalici_disindaki_her_dosyayi_parcalara_verir():
    metin = IS_AKISI.read_text(encoding="utf-8")
    assert 'YOLLAR="testler --ignore=testler/kalici"' in metin
    assert 'PARCA=(-p araclar.pytest_parca --parca "$DILIM")' in metin
    assert '"${PARCA[@]}" $YOLLAR' in metin
    assert "yollar: testler/kalici" in metin                    # kalıcı akış ayrı işte
    assert "--ignore" not in metin.split("yollar: testler/kalici")[1].split("\n")[0]


def test_harita_is_akisiyla_uyumlu():
    h = P.harita_oku()
    n = int(_dilimler()[0].split("/")[1])
    assert P.harita_denetle(h, n) == []


@pytest.mark.parametrize("n", [1, 2, 5, 7])
def test_her_dosya_tam_bir_parcada(n):
    yollar = [f"testler/klasor{i % 4}/test_{i}.py" for i in range(200)]
    harita = {"n": n, "dosyalar": {yollar[0]: n, yollar[1]: 1}}
    parca = {y: P.dosya_parcasi(y, n, harita) for y in yollar}
    assert all(1 <= k <= n for k in parca.values())
    assert parca[yollar[0]] == n and parca[yollar[1]] == 1
    birlesim = [y for k in range(1, n + 1) for y in yollar if parca[y] == k]
    assert sorted(birlesim) == sorted(yollar)                  # dışarıda kalan yok, iki kez sayılan yok


def test_parca_yalniz_kendi_yoluna_bagli():
    """Başka dosyalar eklenip çıksa da bir dosyanın parçası değişmez (parçalar aynı dosya kümesini görmese bile kayıp olmaz)."""
    a = P.dosya_parcasi("testler/test_x.py", 5, {"n": 5, "dosyalar": {}})
    b = P.dosya_parcasi("testler/test_x.py", 5, {"n": 5, "dosyalar": {"testler/test_y.py": 3}})
    assert a == b


def test_bozuk_harita_ve_parca_durdurur():
    assert P.harita_denetle({"n": 4, "dosyalar": {"a.py": 1}}, 5)
    assert P.harita_denetle({"n": 5, "dosyalar": {"a.py": 6}}, 5)
    assert P.harita_denetle({"n": 5, "dosyalar": {"a.py": 0}}, 5)
    assert P.harita_denetle({"n": None, "dosyalar": {}}, 5) == []
    for kotu in ("", "0/5", "6/5", "a/b", "3"):
        with pytest.raises(ValueError):
            P.parca_coz(kotu)
    assert P.parca_coz("2/5") == (2, 5)


def test_harita_kur_dengeler_ve_belirlenimci():
    sure = {"a.py": 100, "b.py": 60, "c.py": 50, "d.py": 40, "e.py": 10}
    h = P.harita_kur(sure, 2)
    assert h == P.harita_kur(dict(reversed(list(sure.items()))), 2)
    assert h["tahmini_sn"] == [140, 120]                       # en uzundan başlayarak en az yüklüye (LPT)
    assert set(h["dosyalar"]) == set(sure)


def test_pytest_ile_parcalarin_birlesimi_hepsi(tmp_path):
    """Eklenti gerçek pytest'te: üç parçanın topladığı testlerin birleşimi parçasız koşunun testleri, kesişim boş."""
    for i in range(9):
        (tmp_path / f"test_ornek_{i}.py").write_text(f"def test_a():\n    pass\n\ndef test_b_{i}():\n    pass\n", encoding="utf-8")
    bos_harita = tmp_path / "yok.json"

    def topla(*ek):
        r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *ek, str(tmp_path)],
                           cwd=KOK, capture_output=True, text=True)
        assert r.returncode in (0, 5), r.stdout + r.stderr
        return {s for s in r.stdout.splitlines() if "::" in s}

    hepsi = topla()
    assert len(hepsi) == 18
    parcalar = [topla("-p", "araclar.pytest_parca", "--parca", f"{k}/3", "--parca-haritasi", str(bos_harita)) for k in (1, 2, 3)]
    assert set().union(*parcalar) == hepsi
    assert sum(len(p) for p in parcalar) == len(hepsi)


def test_pytest_bozuk_haritada_durur(tmp_path):
    (tmp_path / "test_ornek.py").write_text("def test_a():\n    pass\n", encoding="utf-8")
    h = tmp_path / "harita.json"
    h.write_text(json.dumps({"n": 4, "dosyalar": {"x.py": 1}}), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "araclar.pytest_parca", "--parca", "1/5",
                        "--parca-haritasi", str(h), str(tmp_path)], cwd=KOK, capture_output=True, text=True)
    assert r.returncode != 0
    assert "N=4" in r.stdout + r.stderr
