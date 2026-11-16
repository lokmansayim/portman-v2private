"""pytest'i CI'da N parçaya bölen eklenti (BK-43, 16 Kasım 2026).

`dogrulama.yml`'in "testler (parça k/N)" işleri bütün pytest dosyalarını (kalıcı akış hariç) N işe böler. Bölme dosya dosyadır: her
test dosyası tam bir parçada koşar; bir dosyanın testleri bölünmez (modül fikstürleri iki kez kurulmaz).

  python -m pytest -p araclar.pytest_parca --parca 2/5 testler --ignore=testler/kalici

Bir dosyanın parçası yalnız kendi yolundan çıkar, öteki dosyalara bakmaz:
  1. `testler/parca_haritasi.json` o yolu yazıyorsa haritadaki parça (geçmiş sürelerle dengelenmiş);
  2. yazmıyorsa (yeni dosya) yolun CRC32'sinin N'ye göre kalanı + 1.
Böylece 1…N parçanın birleşimi her koşuda toplanan testlerin tamamıdır; bir dosya iki parçada koşmaz, hiçbir dosya dışarıda kalmaz
(`testler/test_pytest_parca.py` iş akışındaki parça listesinin 1…N olduğunu ve haritanın N'sini de denetler).

Harita yalnız dengeyi etkiler, kapsamı etkilemez. Haritadaki N iş akışınınkiyle aynı değilse ya da bir değer 1…N dışındaysa koşu durur
(UsageError, iş kırmızı). Her parça koşunun sonunda kendi dosyalarının sürelerini `PARÇA-SÜRE <sn> <yol>` satırlarıyla yazar; harita
o satırlardan yeniden kurulur:

  python araclar/pytest_parca.py harita <iş kaydı 1> <iş kaydı 2> … [--n 5]     # testler/parca_haritasi.json'u yazar
"""
from __future__ import annotations

import json
import os
import re
import sys
import zlib
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
HARITA = KOK / "testler" / "parca_haritasi.json"
SURE_SATIRI = re.compile(r"PARÇA-SÜRE\s+([0-9.]+)\s+(\S+\.py)\s*$")


def parca_coz(metin: str) -> tuple[int, int]:
    """'2/5' → (2, 5); 1 ≤ k ≤ N."""
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", metin or "")
    if not m:
        raise ValueError(f"--parca k/N biçiminde olmalı: {metin!r}")
    k, n = int(m.group(1)), int(m.group(2))
    if not 1 <= k <= n:
        raise ValueError(f"--parca: 1 ≤ k ≤ N olmalı: {metin!r}")
    return k, n


def harita_oku(yol: Path = HARITA) -> dict:
    """{'n': N, 'dosyalar': {yol: parça}}; dosya yoksa boş harita (her dosya CRC32 ile)."""
    if not Path(yol).is_file():
        return {"n": None, "dosyalar": {}}
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def harita_denetle(harita: dict, n: int) -> list[str]:
    """Haritanın N'si ve değerleri bu koşuyla uyumlu mu; sorunlar listesi (boşsa uyumlu)."""
    sorun = []
    dosyalar = harita.get("dosyalar") or {}
    if dosyalar and harita.get("n") != n:
        sorun.append(f"parça haritası N={harita.get('n')} için kurulmuş, koşu N={n} istiyor (haritayı yeniden kurun)")
    for yol, k in dosyalar.items():
        if not (isinstance(k, int) and 1 <= k <= n):
            sorun.append(f"parça haritasında {yol}: {k!r} 1…{n} dışında")
    return sorun


def dosya_parcasi(yol: str, n: int, harita: dict) -> int:
    """Bir test dosyasının parçası (1…N); yalnız kendi yoluna bağlı."""
    k = (harita.get("dosyalar") or {}).get(yol)
    if k is not None:
        return k
    return zlib.crc32(yol.encode("utf-8")) % n + 1


def harita_kur(sureler: dict[str, float], n: int) -> dict:
    """Süreleri en uzundan başlayarak en az yüklü parçaya koyar (LPT). Eşitlikte yol sırası ve küçük parça: aynı girdi aynı harita."""
    yuk = [0.0] * n
    dosyalar = {}
    for yol, sn in sorted(sureler.items(), key=lambda t: (-t[1], t[0])):
        i = min(range(n), key=lambda j: (yuk[j], j))
        dosyalar[yol] = i + 1
        yuk[i] += sn
    return {"n": n, "aciklama": "araclar/pytest_parca.py harita ile kuruldu; değerler parça numarası (1…n). Yalnız dengeyi etkiler.",
            "tahmini_sn": [round(y) for y in yuk], "dosyalar": dict(sorted(dosyalar.items()))}


def _goreli(config, path) -> str:
    return Path(os.path.relpath(str(path), str(config.invocation_params.dir))).as_posix()


# ───────────────────────────────────────────────────────────────────────── pytest kancaları ──
def pytest_addoption(parser):
    g = parser.getgroup("parca", "CI parçası (araclar/pytest_parca.py)")
    g.addoption("--parca", default=None, help="k/N: test dosyalarını N parçaya böl, k'ıncıyı koş")
    g.addoption("--parca-haritasi", default=str(HARITA), help="dengelenmiş parça haritası (JSON)")


def pytest_configure(config):
    metin = config.getoption("--parca")
    if not metin:
        return
    import pytest
    try:
        k, n = parca_coz(metin)
    except ValueError as e:
        raise pytest.UsageError(str(e))
    harita = harita_oku(Path(config.getoption("--parca-haritasi")))
    sorun = harita_denetle(harita, n)
    if sorun:
        raise pytest.UsageError("; ".join(sorun))
    config.pluginmanager.register(Parca(config, k, n, harita), "portman-parca")


class Parca:
    """Bir parçanın seçimi ve süre dökümü."""

    def __init__(self, config, k: int, n: int, harita: dict):
        self.config, self.k, self.n, self.harita = config, k, n, harita
        self.yol: dict[str, str] = {}               # nodeid → dosyanın çağrı dizinine göre yolu
        self.sure: dict[str, float] = defaultdict(float)
        self.toplam_dosya = self.toplam_test = 0

    def pytest_collection_modifyitems(self, session, config, items):
        secilen, atilan, dosyalar = [], [], set()
        for it in items:
            yol = _goreli(config, it.path)
            dosyalar.add(yol)
            if dosya_parcasi(yol, self.n, self.harita) == self.k:
                secilen.append(it)
                self.yol[it.nodeid] = yol
            else:
                atilan.append(it)
        self.toplam_dosya, self.toplam_test = len(dosyalar), len(items)
        if atilan:
            config.hook.pytest_deselected(items=atilan)
        items[:] = secilen

    def pytest_runtest_logreport(self, report):
        yol = self.yol.get(report.nodeid)
        if yol:
            self.sure[yol] += report.duration

    def pytest_terminal_summary(self, terminalreporter):
        tr = terminalreporter
        secilen = sorted(set(self.yol.values()))
        tr.write_line(f"parça {self.k}/{self.n}: {len(secilen)} dosya, {len(self.yol)} test "
                      f"(toplanan {self.toplam_dosya} dosya, {self.toplam_test} test)")
        for yol in sorted(secilen, key=lambda y: (-self.sure.get(y, 0.0), y)):
            tr.write_line(f"PARÇA-SÜRE {self.sure.get(yol, 0.0):9.1f} {yol}")


# ─────────────────────────────────────────────────────────────────────────────── komut ──
def _ana(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="CI parça haritasını iş kayıtlarındaki PARÇA-SÜRE satırlarından kurar.")
    alt = ap.add_subparsers(dest="komut", required=True)
    h = alt.add_parser("harita")
    h.add_argument("kayitlar", nargs="+", type=Path, help="parça işlerinin kayıtları (GitHub'dan indirilen metin)")
    h.add_argument("--n", type=int, default=None, help="parça sayısı (varsayılan: var olan haritanınki)")
    h.add_argument("--cikti", type=Path, default=HARITA)
    a = ap.parse_args(argv)
    sureler: dict[str, float] = {}
    for kayit in a.kayitlar:
        for satir in kayit.read_text(encoding="utf-8", errors="replace").splitlines():
            m = SURE_SATIRI.search(satir)
            if m:
                sureler[m.group(2)] = max(sureler.get(m.group(2), 0.0), float(m.group(1)))
    if not sureler:
        print("DUR: kayıtlarda PARÇA-SÜRE satırı yok", file=sys.stderr)
        return 1
    n = a.n or harita_oku(a.cikti).get("n")
    if not n:
        print("DUR: --n verin (haritada N yok)", file=sys.stderr)
        return 1
    h = harita_kur(sureler, n)
    a.cikti.write_text(json.dumps(h, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{a.cikti}: {len(h['dosyalar'])} dosya, {n} parça, tahmini süre (sn) {h['tahmini_sn']}")
    return 0


if __name__ == "__main__":
    sys.exit(_ana(sys.argv[1:]))
