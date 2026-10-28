"""İE-18 · Rehberin "Render görselleri" galerisi (`araclar/paket/rehber/galeri.py`, `render.py`) ve GLB'nin parça yükseklikleri.

Galeri 62 m² rehberindeki gibi: sahne rehberin verisinden (çatısız görünüşte gizlenen adımlar 62'de 8–19, Lokman'ın sırası), görseller
sayfaya gömülü, galerisiz sayfa öncekiyle bayt bayt aynı (hedef örneğin izi değişmez). Blender (`BLENDER_PY`) varsa küçük bir render
denemesi; yoksa o test atlanır (CI'da Blender yok). GLB testi Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import galeri, sayfa  # noqa: E402

R62 = json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8"))


def test_sahne_62_ile_ayni():
    """62 m²'nin render betiği çatısız görünüşte 8–19. adımları gizliyordu (duvar omegasından alın sacına); kural verinin adımlarından aynı."""
    s = galeri.sahne(R62)
    assert s["catisiz"] == list(range(8, 20))
    assert s["dis"] == [900, 600] and s["zemin"] == [-12, 912, -162, 612]
    b = galeri.basliklar(R62)
    assert b["cati_katman"].startswith("Çatı katmanları: makas, omega aşık, trapez sac; ters tavanın üstünde")


def test_sayfa_galerisiz_ayni_galerili_gomulu():
    """Galerisiz sayfa önceki gibi (`GORSELLER = []`, düğme gizli); galeri verilince görseller ve başlıkları sayfanın içinde."""
    bos = sayfa.metin(R62)
    assert bos == sayfa.metin(R62, []) and "const GORSELLER = [];" in bos
    g = [["data:image/jpeg;base64,QUJD", "Ön-soldan </script> deneme"]]
    t = sayfa.metin(R62, g)
    assert 'const GORSELLER = [["data:image/jpeg;base64,QUJD","Ön-soldan <\\/script> deneme"]];' in t.replace(", ", ",")
    assert t.replace(json.dumps(g, ensure_ascii=False).replace("</", "<\\/"), "[]") == bos


def _glb_json(yol: Path) -> dict:
    b = yol.read_bytes()
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n])


@pytest.mark.skipif(not (os.environ.get("THREE_DIR") and shutil.which("node")), reason="Node ve three.js (THREE_DIR) yok")
def test_glb_parcalar_yerinde(tmp_path):
    """GLB'de parçalar yerindeki yükseklikte (eskiden kökü yüksekte duran çatı kaplaması, aşık, cam yünü yere düşüyordu) ve serilirken
    görünen rulo yok."""
    from araclar.paket import uret as U
    m = next(x for x in U.kayit()["modeller"] if x["kod"] == "TK-01")
    r = U.paket(m, tmp_path / "M", tmp_path / "gec", glb=True)
    assert r["dosyalar"]["TK-01_model.glb"] == "Var"
    G = _glb_json(tmp_path / "M" / "prefabrik" / "TK-01" / "TK-01_model.glb")
    nodes = G["nodes"]
    import numpy as np

    def matris(n):                                # glTF düğümünün yerel dönüşümü (matrix ya da TRS)
        if "matrix" in n:
            return np.array(n["matrix"], float).reshape(4, 4).T
        x, y, z, w = n.get("rotation", [0, 0, 0, 1]); t = n.get("translation", [0, 0, 0]); sx, sy, sz = n.get("scale", [1, 1, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]) @ np.diag([sx, sy, sz])
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t
        return M

    def alt_y(i, M=np.eye(4)):                    # alt ağacın dünyadaki en alçak noktası (metre, y yukarı)
        n = nodes[i]; M = M @ matris(n); ys = []
        for pr in (G["meshes"][n["mesh"]]["primitives"] if "mesh" in n else []):
            a = G["accessors"][pr["attributes"]["POSITION"]]
            for k in range(8):
                q = [a["max"][j] if k >> j & 1 else a["min"][j] for j in range(3)]
                ys.append((M @ np.array(q + [1.0]))[1])
        ys += [alt_y(c, M) for c in n.get("children", [])]
        return min(ys) if ys else float("inf")
    kok = [i for s_ in G["scenes"] for i in s_["nodes"]]
    ust = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}

    def dunya(i):                                 # grubun üstündeki düğümlerin dönüşümü
        z = []
        while i in ust:
            i = ust[i]; z.append(i)
        M = np.eye(4)
        for j in reversed(z):
            M = M @ matris(nodes[j])
        return M
    assert kok
    for ad in ("Çatı izolasyonu", "Aşıklar"):     # adım grupları "NN <adım adı>"
        gi = next(i for i, n in enumerate(nodes) if re.fullmatch(r"\d\d " + ad + ".*", n.get("name", "")))
        alt = alt_y(gi, dunya(gi))
        assert 2.4 < alt < 6, (ad, alt)            # duvar 250 cm'nin üstünde (eskiden 0'a düşüyordu)
    izo = {i for i, m in enumerate(G["materials"]) if m.get("name") == "izocam"}
    serit = sum(1 for me in G["meshes"] for pr in me["primitives"] if pr.get("material") in izo)
    assert serit == 7                             # TK-01'de 7 şerit (rehberin "Modelde 7 şerit"i); rulolar da yazılınca 14'tü


@pytest.mark.skipif(not os.environ.get("BLENDER_PY"), reason="Blender (BLENDER_PY) yok; galeri yalnız yerelde üretilir")
def test_render_kucuk(tmp_path):
    """Blender varsa: 62 m²'nin hedef GLB'si yok, TK-01'in GLB'siyle küçük (8 örnek, 0,2 ölçek) beş görünüş ve etiket yerleri."""
    if not (os.environ.get("THREE_DIR") and shutil.which("node")):
        pytest.skip("GLB için Node ve three.js yok")
    from araclar.paket import uret as U
    m = next(x for x in U.kayit()["modeller"] if x["kod"] == "TK-01")
    U.paket(m, tmp_path / "M", tmp_path / "gec", glb=True)
    glb = tmp_path / "M" / "prefabrik" / "TK-01" / "TK-01_model.glb"
    html = (tmp_path / "M" / "prefabrik" / "TK-01" / "TK-01_montaj_rehberi.html").read_text(encoding="utf-8")
    d = json.loads(re.search(r'<script type="application/json" id="pafta">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
    k = tmp_path / "r"; k.mkdir()
    (k / "sahne.json").write_text(json.dumps(galeri.sahne(d)), encoding="utf-8")
    r = subprocess.run([os.environ["BLENDER_PY"], str(KOK / "araclar/paket/rehber/render.py"), str(glb), str(k / "sahne.json"), str(k), "8", "0.2"],
                       capture_output=True, text=True, timeout=1200)
    assert r.returncode == 0, r.stderr[-500:]
    assert sorted(p.stem for p in k.glob("*.png")) == sorted(galeri.GORUNUMLER)
    yer = json.loads((k / "cati_katman.json").read_text(encoding="utf-8"))
    assert set(yer) == {"roof", "asik", "izocam", "truss"} and all(0 <= x <= 320 and 0 <= y <= 200 for x, y in yer.values())
