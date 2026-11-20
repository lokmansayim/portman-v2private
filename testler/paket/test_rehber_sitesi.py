"""İE-41 · rehber.portatifev.com sitesi main'deki koddan (`araclar/paket/site/`; Lokman, 14 Kasım 2026 20:37 UTC kartı "Siteyi main'den kur").

Paketleyici sahneyi değiştirmez, yalnız iç notları çıkarır. CI'da koşan sınamalar (esbuild ve yazı tipi paketleri gerekmez):
- kayıt: altı rehber (85 m² 17 Kasım 2026'da; beşi canlı paketten sabit), klasörler eşsiz ve yayındaki üç yol korunur, adda kod yok, girdiler depoda;
- 62 m² ve kampanyalı ev (TK-04 r08, main'in komutuyla): veride iç not yok (`ortak.YASAK`), sayılar ve geometri aynı (metin dışındaki her
  değer main'in sayfasındakiyle aynı), başlıkta kod yok, ön onay paftasının üst satırı örtülü;
- açılış sayfası; `vps/rehber_yayin.sh` ve belirlenimci paket;
- montaj oyunu (İE-45, D-138): oyunun verisi kampanyalı evin main'deki sayfasından, hedef örnek `testler/paket/oyun/veri_80m2-21.json`
  ile aynı; sayfa CSP'li, iç notsuz; GLB'nin kök adından evin kodu çıkar (GLB'nin kendisi CI'da üretilmez: tarayıcıda WebGL gerekir).
Betik katı (esbuild) ve tam site `REHBER_SITE_ESBUILD` ve `REHBER_SITE_NPM` verilirse koşar; tarayıcı denemesi `araclar/paket/site/dene.js`.
"""
from __future__ import annotations

import io
import json
import os
import re
import struct
import subprocess
from pathlib import Path

import pytest

from araclar.paket.site import oyun, ortak, temizle, uret

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
    for o in KAYIT.get("oyunlar", []):                                       # İE-45: oyun bir İş Emri rehberinden, klasörü eşsiz
        assert re.fullmatch(r"[a-z0-9-]+", o["klasor"]) and o["klasor"] not in kl and R[o["rehber"]].get("kod")
        assert 1 <= o["kapak_adim"] <= R[o["rehber"]]["adim"] and not ortak.bulgular(o["ad"])


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
        assert f"gorsel/onay_pafta.jpg{ortak.surum_eki(pafta)}" in html          # önbellek kırıcı ek (20 Kasım 2026)


def test_kampanyali_basliginda_brut_ve_net(sayfalar):
    html, _, _ = temizle.sayfa(sayfalar["80m2-21"], R["80m2-21"], esbuild=None)
    assert '<span class="chip">77,95 m² brüt · 73,04 m² net</span>' in html


def test_acilis():
    oz = {r["klasor"]: {"spec": ["a", "b", "c", "d", "e", "f"], "adim": r["adim"], "chip": "1 m²"} for r in KAYIT["rehberler"]}
    s = uret.acilis_sayfasi(KAYIT["rehberler"], oz)
    assert re.findall(r'<a class="kart" href="([^"]+)/">', s) == [r["klasor"] for r in KAYIT["rehberler"]]
    assert "Content-Security-Policy" in s and "__" not in s and not ortak.bulgular(s)
    # oyunun kartı rehber kartlarının önünde; rehber kartları aynen (sabit rehberin kartı canlıdakiyle aynı kalır)
    ov = {o["klasor"]: {"ad": R[o["rehber"]]["ad"], "adimlar": [0] * R[o["rehber"]]["adim"]} for o in KAYIT["oyunlar"]}
    s2 = uret.acilis_sayfasi(KAYIT["rehberler"], oz, KAYIT["oyunlar"], ov)
    assert re.findall(r'<a class="kart" href="([^"]+)/">', s2) == ["oyun"] + [r["klasor"] for r in KAYIT["rehberler"]]
    assert all(uret.kart_html(r, oz[r["klasor"]]) in s2 for r in KAYIT["rehberler"])
    assert '<span class="ac">Oyunu aç</span>' in s2 and "oyun/gorsel/kapak.jpg" in s2 and not ortak.bulgular(s2)


def test_onbellek_kirici_ek():
    """20 Kasım 2026: nginx resim ve modeli 7 gün saklatır; 85 m² yenilenince telefonda eski ön onay paftası göründü. Değişen resim
    ve model adresi içerikle değişir (`ortak.surum_eki`); sabit rehberin kartı canlıdakiyle, ek atılınca, aynı kalır."""
    a, b = ortak.surum_eki(b"bir"), ortak.surum_eki(b"iki")
    assert a == ortak.surum_eki(b"bir") != b and ortak.SURUM_EKI.fullmatch(a)
    r = R["85m2"]
    oz = {"spec": ["a", "b", "c", "d", "e", "f"], "adim": r["adim"], "chip": "1 m²"}
    kart = uret.kart_html(r, oz, a)
    assert f'src="85m2/gorsel/kapak.jpg{a}"' in kart and ortak.SURUM_EKI.sub("", kart) == uret.kart_html(r, oz)
    ozet = {x["klasor"]: oz for x in KAYIT["rehberler"]}
    ov = {o["klasor"]: {"ad": R[o["rehber"]]["ad"], "adimlar": [0] * R[o["rehber"]]["adim"]} for o in KAYIT["oyunlar"]}
    s = uret.acilis_sayfasi(KAYIT["rehberler"], ozet, KAYIT["oyunlar"], ov, {"85m2": a, "oyun": b})
    assert f"85m2/gorsel/kapak.jpg{a}" in s and f"oyun/gorsel/kapak.jpg{b}" in s and 'src="62m2/gorsel/kapak.jpg"' in s
    v = json.loads(OYUN_HEDEF.read_text(encoding="utf-8"))
    sy = oyun.sayfa(v, KAYIT["oyunlar"][0], glb_eki=b)
    assert f"fetch('ev.glb{b}')" in sy and "fetch('ev.glb')" not in sy and len(re.findall(r"'sha256-[^']+'", sy)) == 2


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
    v, o = json.loads(OYUN_HEDEF.read_text(encoding="utf-8")), KAYIT["oyunlar"][0]
    addon = oyun.klasor_yaz(v, o, _glb("TK-04"), "TK-04", tmp_path / "oyun", Path(NPM), ESBUILD)
    assert "utils/BufferGeometryUtils.js" in addon and (tmp_path / "oyun" / "js" / "addons" / "utils" / "BufferGeometryUtils.js").exists()
    assert (tmp_path / "oyun" / "ev.glb").exists() and "Content-Security-Policy" in (tmp_path / "oyun" / "index.html").read_text(encoding="utf-8")


OYUN_HEDEF = KOK / "testler" / "paket" / "oyun" / "veri_80m2-21.json"


def test_oyun_verisi_hedef(sayfalar):
    """İE-45 (D-138): oyunun verisi (kartlar, ipuçları, oda bilgisi, kamera) kampanyalı evin main'deki rehberinden; hedef örnekle aynı."""
    o = next(o for o in KAYIT["oyunlar"] if o["rehber"] == "80m2-21")
    v = oyun.veri(oyun.rehber_verisi(sayfalar["80m2-21"], R["80m2-21"]), R["80m2-21"], o)
    assert v == json.loads(OYUN_HEDEF.read_text(encoding="utf-8"))
    assert [a["i"] for a in v["adimlar"]] == list(range(1, 22)) and sum(a["oda"] for a in v["adimlar"]) == 6
    assert not ortak.bulgular(json.dumps(v, ensure_ascii=False))


def test_oyun_sayfasi():
    v = json.loads(OYUN_HEDEF.read_text(encoding="utf-8"))
    o = KAYIT["oyunlar"][0]
    s = oyun.sayfa(v, o)
    assert s.startswith("<!doctype html>") and "Content-Security-Policy" in s and "connect-src 'self'" in s
    assert not re.search(r"__[A-Z]+__", s) and len(re.findall(r"'sha256-[^']+'", s)) == 2
    gomulu = re.search(r'<script type="application/json" id="veri">(.*?)</script>', s, re.S).group(1)
    assert json.loads(gomulu.replace("<\\/", "</")) == v
    assert "fetch('ev.glb')" in s and '"three": "./js/three.module.js"' in s and 'href="../80m2-21/"' in s
    assert "<title>PortatifEv · Evi kendin kur · 80 m² 2+1</title>" in s
    v2 = json.loads(json.dumps(v))
    v2["adimlar"][0]["ipucu"] = "Lokman böyle dedi"
    with pytest.raises(ortak.SiteHatasi):                                    # son kapı: iç not geçen oyun sayfası pakete girmez
        oyun.sayfa(v2, o)


def _glb(ad: str, ek: str = "") -> bytes:
    j = json.dumps({"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
                    "nodes": [{"name": ad, "children": [1]}, {"name": "01 Alt çerçeve" + ek, "extras": {"ackapa": {"tip": "don", "max": 1.2}}}],
                    "buffers": [{"byteLength": 8}]}).encode()
    j += b" " * (-len(j) % 4)
    b = bytes(range(8))
    return (b"glTF" + struct.pack("<II", 2, 28 + len(j) + len(b)) + struct.pack("<II", len(j), 0x4E4F534A) + j
            + struct.pack("<II", len(b), 0x004E4942) + b)


def test_glb_kok_adi():
    g = oyun.glb_temizle(_glb("TK-04"), "TK-04")
    n = struct.unpack("<I", g[12:16])[0]
    j = json.loads(g[20:20 + n])
    assert j["nodes"][0]["name"] == "ev" and j["nodes"][1]["extras"]["ackapa"]["max"] == 1.2
    assert struct.unpack("<I", g[8:12])[0] == len(g) and n % 4 == 0 and g.endswith(bytes(range(8)))
    assert "tk-0" not in g[20:20 + n].decode().lower()
    with pytest.raises(ortak.SiteHatasi):
        oyun.glb_temizle(_glb("TK-04", " (Lokman)"), "TK-04")


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
