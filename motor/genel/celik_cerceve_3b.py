#!/usr/bin/env python3
"""Çelik karkas iskeletinin üç boyutlu görünümü (İE-47; Lokman, 28 Kasım 2026 14:19:59 "3 boyutlu verebilir misin?").

İki boyutlu iskelet çiziminin (`celik_cerceve.kur`) aynı hesabından okur; yeni parça eklemez. Uzayda yalnız iki boyutlu çizimde olan
öğeler durur:

- kafes kolon: dört yüzü, örgü ön görünüşteki gibi (adım kolon genişliği);
- kafes makas: her çerçeve hattında (y aksı) kolonun ortasından geçen düşey düzlemde, üyeler ön görünüşteki makasla aynı;
- kuşak: her x aksında kolon tepesinde, y boyunca (yan görünüşteki kuşak çizgisi);
- mahya: her açıklığın ortasında, makasın en üst noktasında, kalkan saçağından kalkan saçağına (yan görünüşteki mahya çizgisi);
- ters mahya: iç akslarda vadide, ön görünüşteki şematik V kesitiyle, kalkan saçağından kalkan saçağına.

Çıktılar: `<kod>_iskelet_3b.png` (eş ölçülü bakış), `<kod>_iskelet_3b.dxf` (3B çizgiler; katmanlar KOLON, MAKAS, KUSAK, MAHYA,
TERS_MAHYA; cm) ve `<kod>_iskelet_3b.html` (tarayıcıda parmakla ya da fareyle döndürülen görünüm; dış kitaplık yok).
Aşık, çapraz bağ, profil ve bağlantı mühendis hesabıdır: görünüm TASLAK'tır.
"""
from __future__ import annotations

import json
from pathlib import Path

from .toplam import sum  # noqa: A004

RENK = {"KOLON": "#1f4e79", "MAKAS": "#b22222", "KUSAK": "#555555", "MAHYA": "#c07a00", "TERS_MAHYA": "#2e8b3a"}


def _kafes(d0, d1, h, adim):
    cizgi = [((d0, 0), (d0, h)), ((d1, 0), (d1, h)), ((d0, 0), (d1, 0))]
    z, s = 0.0, 0
    while z < h - 1e-6:
        z2 = min(z + adim, h)
        cizgi.append(((d0, z), (d1, z2)) if s == 0 else ((d1, z), (d0, z2)))
        cizgi.append(((d0, z2), (d1, z2)))
        z, s = z2, s ^ 1
    return cizgi


def ogeler(k: dict) -> list:
    """(katman, (x, y, z), (x, y, z)) üçlüleri, cm."""
    W, D = k["dis_olcu"]
    H = k["kolon_yuksekligi"]
    sc = k["sacak_cm"]
    out = []
    for c in k["kolonlar"]:
        (x0, x1), (y0, y1) = c["x"], c["y"]
        for y in (y0, y1):
            out += [("KOLON", (p[0], y, p[1]), (q[0], y, q[1])) for p, q in _kafes(x0, x1, H, x1 - x0)]
        for x in (x0, x1):
            out += [("KOLON", (x, p[0], p[1]), (x, q[0], q[1])) for p, q in _kafes(y0, y1, H, y1 - y0)]
    hat_y = sorted({(c["y"][0] + c["y"][1]) / 2 for c in k["kolonlar"]})
    for y in hat_y:
        for m in k["makaslar"]:
            a = m["aks"][0]
            out += [("MAKAS", (a + c["x1"] / 10, y, H + c["y1"] / 10), (a + c["x2"] / 10, y, H + c["y2"] / 10)) for c in m["cubuklar"]]
    for a in sorted({(c["x"][0] + c["x"][1]) / 2 for c in k["kolonlar"]}):
        out.append(("KUSAK", (a, 0.0, H), (a, float(D), H)))
    for m in k["makaslar"]:                          # mahya makasın en üst noktasında (üst başlık ekseni)
        orta = (m["aks"][0] + m["aks"][1]) / 2
        z = H + max(max(c["y1"], c["y2"]) for c in m["cubuklar"]) / 10
        out.append(("MAHYA", (orta, -sc, z), (orta, D + sc, z)))
    e = k["makaslar"][0]["egim"]
    for tm in k["ters_mahya"]:
        a, z = tm["aks"], tm["kot_cm"]
        for dx in (-30, 30):
            for y in (-sc, D + sc):
                out.append(("TERS_MAHYA", (a, y, z), (a + dx, y, z + 30 * e)))
            out.append(("TERS_MAHYA", (a + dx, -sc, z + 30 * e), (a + dx, D + sc, z + 30 * e)))
        out.append(("TERS_MAHYA", (a, -sc, z), (a, D + sc, z)))
    return [(ad, tuple(round(v, 1) for v in p), tuple(round(v, 1) for v in q)) for ad, p, q in out]


def _png(k, og, yol: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    W, D = k["dis_olcu"]
    tepe = k["ozet"]["mahya_kotu_cm"]
    fig = plt.figure(figsize=(14, 11), dpi=150)
    ax = fig.add_axes((0, 0, 1, 0.9), projection="3d", proj_type="ortho")
    for ad, renk in RENK.items():
        parca = [(p, q) for a, p, q in og if a == ad]
        if parca:
            lc = Line3DCollection(parca, colors=renk, linewidths=0.5 if ad == "KOLON" else 0.6)
            lc.set_clip_on(False)
            ax.add_collection3d(lc)
    ax.set_xlim(-50, W + 50)
    ax.set_ylim(-50, D + 50)
    ax.set_zlim(0, tepe + 50)
    ax.set_box_aspect((W + 100, D + 100, tepe + 50), zoom=1.0)
    ax.view_init(elev=22, azim=-62)
    ax.set_axis_off()
    o = k["ozet"]
    fig.suptitle(f"{k['kod']} · ÇELİK KARKAS İSKELET · 3B GÖRÜNÜM — TASLAK\n"
                 f"{W / 100:.2f} × {D / 100:.2f} m · {o['kolon']} kafes kolon · {o['makas_toplam']} kafes makas · "
                 f"{len(k['ters_mahya'])} ters mahya · aşık, çapraz bağ ve profil mühendis hesabı", fontsize=12)
    fig.savefig(yol, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)


def _dxf(k, og, yol: Path):
    import ezdxf

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 5  # cm
    for i, ad in enumerate(RENK):
        doc.layers.add(ad, color=(5, 1, 8, 8, 3)[i])
    msp = doc.modelspace()
    for ad, p, q in og:
        msp.add_line(p, q, dxfattribs={"layer": ad})
    doc.saveas(yol)
    ezdxf.readfile(yol)  # yeniden açılır (K23)


HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Çelik iskelet 3B</title>
<style>
:root{--bg:#f7f7f5;--fg:#1d1d1b;--muted:#6b6b66;--line:#d8d8d2}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#ececea;--muted:#9a9a94;--line:#333}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#ececea;--muted:#9a9a94;--line:#333}
html,body{margin:0;height:100%;}
body{display:flex;flex-direction:column;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}
header{padding:12px 16px;border-bottom:1px solid var(--line)}
h1{font-size:16px;margin:0 0 4px}
p{margin:0;color:var(--muted)}
.lej{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:13px}
.lej span::before{content:"";display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:middle;background:var(--c)}
canvas{display:block;width:100%;flex:1;min-height:0;touch-action:none;cursor:grab}
</style></head><body>
<header><h1>__BASLIK__</h1><p>__OZET__ · Parmağınızla ya da fareyle döndürün, iki parmakla ya da tekerle yaklaşın.</p>
<div class="lej">__LEJ__</div></header>
<canvas id="c"></canvas>
<script>
const V=__VERI__;
const cv=document.getElementById('c'),cx=cv.getContext('2d');
let az=-0.95,el=0.45,zoom=1,drag=null,pin=null;
const [W,D,T]=V.kutu,mx=W/2,my=D/2,mz=T/2;
function boyut(){const r=devicePixelRatio||1;cv.width=cv.clientWidth*r;cv.height=cv.clientHeight*r;ciz();}
function pr(p,s,ox,oy){const x=p[0]-mx,y=p[1]-my,z=p[2]-mz;
 const ca=Math.cos(az),sa=Math.sin(az),ce=Math.cos(el),se=Math.sin(el);
 const X=x*ca-y*sa,Y=x*sa+y*ca;return [ox+X*s,oy-(z*ce-Y*se)*s];}
function ciz(){const w=cv.width,h=cv.height;cx.clearRect(0,0,w,h);
 const s=Math.min(w/(W*1.15),h/(D*1.1+T))*zoom,ox=w/2,oy=h/2;cx.lineWidth=Math.max(0.6,(devicePixelRatio||1)*0.7);
 for(const [k,renk] of Object.entries(V.renk)){cx.strokeStyle=renk;cx.beginPath();
  for(const [a,b] of V.c[k]){const p=pr(a,s,ox,oy),q=pr(b,s,ox,oy);cx.moveTo(p[0],p[1]);cx.lineTo(q[0],q[1]);}cx.stroke();}}
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY};});
cv.addEventListener('pointermove',e=>{if(!drag||pin)return;az+=(e.clientX-drag.x)*0.008;el=Math.max(-0.2,Math.min(1.5,el+(e.clientY-drag.y)*0.008));drag={x:e.clientX,y:e.clientY};ciz();});
cv.addEventListener('pointerup',()=>drag=null);
cv.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(0.5,Math.min(8,zoom*Math.exp(-e.deltaY*0.0015)));ciz();},{passive:false});
cv.addEventListener('touchstart',e=>{if(e.touches.length==2){pin=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);}});
cv.addEventListener('touchmove',e=>{if(e.touches.length==2&&pin){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);zoom=Math.max(0.5,Math.min(8,zoom*d/pin));pin=d;ciz();}});
cv.addEventListener('touchend',e=>{if(e.touches.length<2)pin=null;});
addEventListener('resize',boyut);boyut();
</script></body></html>
"""

ADLAR = {"KOLON": "kafes kolon", "MAKAS": "kafes makas", "KUSAK": "kuşak", "MAHYA": "mahya", "TERS_MAHYA": "ters mahya"}


def _html(k, og, yol: Path):
    W, D = k["dis_olcu"]
    o = k["ozet"]
    veri = {"kutu": [W, D, o["mahya_kotu_cm"]], "renk": RENK,
            "c": {ad: [[list(p), list(q)] for a, p, q in og if a == ad] for ad in RENK}}
    lej = "".join(f'<span style="--c:{RENK[a]}">{ADLAR[a]}</span>' for a in RENK)
    metin = (HTML.replace("__BASLIK__", f"{k['kod']} çelik karkas iskelet · 3B · TASLAK")
             .replace("__OZET__", f"{W / 100:.2f} × {D / 100:.2f} m, {o['kolon']} kafes kolon, {o['makas_toplam']} kafes makas")
             .replace("__LEJ__", lej).replace("__VERI__", json.dumps(veri, separators=(",", ":"))))
    yol.write_text(metin, encoding="utf-8")


def uret(k: dict, cikti: Path, dosya: str) -> list:
    og = ogeler(k)
    _png(k, og, cikti / f"{dosya}_iskelet_3b.png")
    _dxf(k, og, cikti / f"{dosya}_iskelet_3b.dxf")
    _html(k, og, cikti / f"{dosya}_iskelet_3b.html")
    return og


def sayim(og) -> dict:
    return {ad: sum(1 for a, _, _ in og if a == ad) for ad in RENK}
