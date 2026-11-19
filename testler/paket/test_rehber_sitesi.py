"""İE-41 · rehber.portatifev.com sitesi main'deki koddan (`araclar/paket/site/`; Lokman, 14 Kasım 2026 20:37 UTC kartı "Siteyi main'den kur").

Paketleyici sahneyi değiştirmez, yalnız iç notları çıkarır. CI'da koşan sınamalar (esbuild ve yazı tipi paketleri gerekmez):
- kayıt: altı rehber (85 m² 17 Kasım 2026'da; beşi canlı paketten sabit), klasörler eşsiz ve yayındaki üç yol korunur, adda kod yok, girdiler depoda;
- 62 m² ve kampanyalı ev (TK-04 r08, main'in komutuyla): veride iç not yok (`ortak.YASAK`), sayılar ve geometri aynı (metin dışındaki her
  değer main'in sayfasındakiyle aynı), başlıkta kod yok, ön onay paftasının üst satırı örtülü;
- açılış sayfası; `vps/rehber_yayin.sh` ve belirlenimci paket.
Betik katı (esbuild) ve tam site `REHBER_SITE_ESBUILD` ve `REHBER_SITE_NPM` verilirse koşar; tarayıcı denemesi `araclar/paket/site/dene.js`.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from araclar.paket.site import ortak, temizle, uret

KOK = Path(__file__).resolve().parents[2]
KAYIT = uret.kayit()
R = {r["klasor"]: r for r in KAYIT["rehberler"]}
ESBUILD, NPM = os.environ.get("REHBER_SITE_ESBUILD"), os.environ.get("REHBER_SITE_NPM")


def _veri(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="pafta">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))


def _yapraklar(x, yol=()):
    """Metin dışındaki her değer (sayı, mantık, boş) yoluyla; iç kaynak alanları hariç."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k not in temizle.ATILAN_ANAHTAR:
                yield from _yapraklar(v, yol + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _yapraklar(v, yol + (i,))
    elif not isinstance(x, str):
        yield yol, x


def test_kayit():
    kl = [r["klasor"] for r in KAYIT["rehberler"]]
    assert len(kl) == len(set(kl)) == 6 and {"62m2", "80m2", "80m2-21"} <= set(kl)     # yayındaki yollar korunur
    for r in KAYIT["rehberler"]:
        assert re.fullmatch(r"[a-z0-9-]+", r["klasor"]) and not re.search(r"\b(TK|AP|PK)-?\d", r["ad"]), r
        assert (KOK / (r.get("veri") or r["is_emri"])).exists(), r
        assert isinstance(r["adim"], int) and isinstance(r["pafta"], bool)
        assert not ortak.bulgular(r["ad"] + temizle.not_metni(r))


@pytest.fixture(scope="module")
def sayfalar(tmp_path_factory):
    g = tmp_path_factory.mktemp("site")
    return {k: uret.ham_sayfa(R[k], g / k).read_text(encoding="utf-8") for k in ("62m2", "80m2-21")}


@pytest.mark.parametrize("kl", ["62m2", "80m2-21"])
def test_veri_temiz_sahne_ayni(sayfalar, kl):
    from PIL import Image
    r = R[kl]
    ham = sayfalar[kl]
    html, pafta, oz = temizle.sayfa(ham, r, esbuild=None)
    a, b = _veri(ham), _veri(html)
    assert not ortak.bulgular(json.dumps(b, ensure_ascii=False)), ortak.bulgular(json.dumps(b, ensure_ascii=False))[:5]
    assert dict(_yapraklar(a)) == {k: v for k, v in _yapraklar(b)}          # sayılar ve geometri aynı
    assert set(a) - set(b) <= temizle.ATILAN_ANAHTAR and oz["adim"] == a["N"] == r["adim"]
    assert b["kod"] == b["kabuk"]["proje"] == r["ad"] and b["kabuk"]["chip"] == a["kabuk"]["chip"]
    assert f"<h1>{r['ad']} · Montaj Rehberi</h1>" in html and f'<p class="note">{temizle.not_metni(r)}</p>' in html
    assert "googleapis" not in html and "jsdelivr" not in html and "data:image/jpeg" not in html
    assert "prefabrik prefabrik" not in html                                  # 62 m² açıklaması (CIO, 14.11 23:09)
    assert (pafta is not None) == r["pafta"]
    if pafta:
        im = Image.open(io.BytesIO(pafta)).convert("L")
        assert im.size == temizle.PAFTA_BOYU and im.crop(temizle.PAFTA_ORTU).getextrema() == (255, 255)   # üst satır örtülü
        assert "gorsel/onay_pafta.jpg" in html


def test_kampanyali_basliginda_brut_ve_net(sayfalar):
    html, _, _ = temizle.sayfa(sayfalar["80m2-21"], R["80m2-21"], esbuild=None)
    assert '<span class="chip">77,95 m² brüt · 73,04 m² net</span>' in html


def test_acilis():
    oz = {r["klasor"]: {"spec": ["a", "b", "c", "d", "e", "f"], "adim": r["adim"], "chip": "1 m²"} for r in KAYIT["rehberler"]}
    s = uret.acilis_sayfasi(KAYIT["rehberler"], oz)
    assert re.findall(r'<a class="kart" href="([^"]+)/">', s) == [r["klasor"] for r in KAYIT["rehberler"]]
    assert "Content-Security-Policy" in s and "__" not in s and not ortak.bulgular(s)


def test_yayin_betigi_ve_paket(tmp_path):
    betik = KOK / "vps" / "rehber_yayin.sh"
    assert subprocess.run(["bash", "-n", str(betik)]).returncode == 0
    assert betik.read_text(encoding="utf-8").count("# __PAKET_YERI__") == 1
    ozet = []
    for i in range(2):
        site = tmp_path / f"site{i}"
        (site / "a").mkdir(parents=True)
        (site / "index.html").write_text("<!doctype html><p>açılış</p>\n", encoding="utf-8")
        (site / "a" / "index.html").write_text("<!doctype html><p>rehber</p>\n", encoding="utf-8")
        cikti = tmp_path / f"cikti{i}"
        cikti.mkdir()
        sha, kur = ortak.paketle_ve_kur(site, cikti, mtime=KAYIT["mtime"])
        assert subprocess.run(["bash", "-n", str(kur)]).returncode == 0 and f"PAKET_SHA256='{sha}'" in kur.read_text(encoding="utf-8")
        ozet.append(sha)
    assert ozet[0] == ozet[1]                                                # belirlenimci


@pytest.mark.skipif(not (ESBUILD and NPM), reason="REHBER_SITE_ESBUILD ve REHBER_SITE_NPM yok (esbuild, three-0.160.0, fontsource)")
def test_sayfa_tam(sayfalar, tmp_path):
    for kl, ham in sayfalar.items():
        html, pafta, _ = temizle.sayfa(ham, R[kl], ESBUILD)
        assert "__CSP__" not in html and "Content-Security-Policy" in html
        addon = temizle.klasor_yaz(html, pafta, tmp_path / kl, Path(NPM))
        assert addon and (tmp_path / kl / "js" / "three.module.js").exists() and (tmp_path / kl / "yazi" / "yazi.css").exists()


def test_sabit_rehber_kaydi():
    """Sabit rehber (17 Kasım 2026): klasörü canlı paketten bayt bayt gelir; kayıtta paketin sürümü ve sha'sı durur."""
    sabit = [r for r in KAYIT["rehberler"] if r.get("sabit")]
    if sabit:
        sp = KAYIT["sabit_paket"]
        assert re.fullmatch(r"[0-9a-f]{64}", sp["sha256"]) and re.fullmatch(r"\d{14}", sp["surum"])
    with pytest.raises(ortak.SiteHatasi, match="--onceki"):
        uret.sabit_dosyalar({"rehberler": [{"sabit": True}], "sabit_paket": {"sha256": "0" * 64}}, None)
    assert uret.sabit_dosyalar({"rehberler": [{"klasor": "a"}]}, None) == {}


def test_onceki_paket(tmp_path):
    site = tmp_path / "site"
    (site / "a" / "gorsel").mkdir(parents=True)
    (site / "index.html").write_text("<p>açılış</p>\n", encoding="utf-8")
    (site / "a" / "index.html").write_text("<p>rehber</p>\n", encoding="utf-8")
    (site / "a" / "gorsel" / "kapak.jpg").write_bytes(bytes(range(256)))
    sha, kur = ortak.paketle_ve_kur(site, tmp_path, mtime=KAYIT["mtime"])
    for kaynak in (kur, tmp_path / "rehber_paket.tgz"):
        d = ortak.onceki_paket(kaynak, sha)
        assert d["a/gorsel/kapak.jpg"] == bytes(range(256)) and d["index.html"] == "<p>açılış</p>\n".encode()
        assert set(d) == {"index.html", "a/index.html", "a/gorsel/kapak.jpg", "SHA256SUMS"}
    with pytest.raises(ortak.SiteHatasi, match="sha256"):
        ortak.onceki_paket(kur, "0" * 64)
