"""6 Ekim 2026 denemesi: IFC → pano pano 3D sunum sayfası (tek dosya).

    python deneme/2026-10-06_kalinlik_160_100/sayfa_3b.py [is_emri.json]

`motor/ucb_sayfa.py`'nin yerine denenen sayfa. İki tur geri bildirim (Lokman, 6 Ekim):
- 19:46 — çevirme ve çatı kaldırma çalışmıyordu. Çatı örtüsü, alın ve makaslar ayrı katman oldu (eski sayfa örtüyü gizlemiyordu,
  çünkü örtü IfcSlab); çevirme kendi yazılmış denetimle (fare, dokunma, tekerlek, klavye, ekrandaki düğmeler).
- 21:00 — "Astra'nın yaptığı daha iyi". Astra'nın 30 Eylül tarihli sunum sayfası (`Uc_Model_Sunum/Incele.html`, Lokman'ın Mac'inde;
  yalnız okundu, kopyalanmadı) örnek alındı: başlık bandı, çerçeveli sahne ve yan pano, "Çatıyı aç / Üstten bak / Dış görünüş / Döndür"
  düğmeleri, parçaların sırayla belirdiği "Oluşumu oynat" ve sürgüsü, malzemeli görünüş (ışık, gölge, trapez sac çatı), yanında plan.
  Buradaki fark: model SKP'den değil İş Emri'nden gelir; her pano ayrı parçadır, tıklanınca pafta kodu ve ölçüsü görünür.
İki çıktı: kendi başına açılan HTML (three.js gömülü, ağ gerekmez) ve yayımlanacak sayfa parçası (three.js cdnjs'ten).
Ayrıca Blender betiği için pano etiketlerini yazar (`pano_etiketleri.json`).
"""
from __future__ import annotations
import base64, html, io, json, multiprocessing, os, sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = BURASI / "cikti"
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(BURASI))
os.environ.setdefault("PORTMAN_REF_DIR", str(KOK / "kanal"))

R_STANDART, R_OZEL, R_IC = [0.87, 0.84, 0.76], [0.70, 0.52, 0.83], [0.94, 0.93, 0.89]
GRUP_RENK = {"cati": [0.26, 0.29, 0.33], "alin": [0.82, 0.80, 0.73], "makas": [0.62, 0.65, 0.69], "baglanti": [0.50, 0.52, 0.55],
             "zemin": [0.60, 0.60, 0.58], "kapi": [0.48, 0.30, 0.16]}


def grup_of(sinif: str, ad: str, dis: bool | None) -> str | None:
    if sinif == "IfcWall":
        return "dis_pano" if dis else "ic_pano"
    if sinif == "IfcWindow": return "pencere"
    if sinif == "IfcDoor": return "kapi"
    if sinif == "IfcSlab": return "cati" if ad.startswith(("CATI", "VERANDA_CATI")) else "zemin"
    if sinif == "IfcPlate": return "alin"
    if sinif == "IfcMember": return "makas" if ad.startswith("MAKAS") else "baglanti"
    if sinif in ("IfcColumn", "IfcBeam"): return "baglanti"
    return None


def model_json(ifc_yolu: Path, etiket: dict) -> dict:
    """IFC → üçgen ağlar (metre; three.js için y yukarı: x, z, −y). Pencere ve kapıda cam ile kasa ayrı parça."""
    import numpy as np
    import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue
    f = ifcopenshell.open(str(ifc_yolu))
    s = ifcopenshell.geom.settings(); s.set("use-world-coords", True)
    it = ifcopenshell.geom.iterator(s, f, max(1, multiprocessing.cpu_count()))
    el, mahal, sayim = [], [], []
    if it.initialize():
        while True:
            sh = it.get(); e = f.by_id(sh.id); g = sh.geometry
            sinif, ad = e.is_a(), (e.Name or e.is_a())
            if sinif == "IfcSpace":
                v = np.array(g.verts, dtype=float).reshape(-1, 3)
                q = (ue.get_psets(e) or {}).get("Qto_SpaceBaseQuantities") or {}
                mahal.append({"ad": getattr(e, "LongName", None) or ad, "alan": round(float(q["NetFloorArea"]), 2) if q.get("NetFloorArea") is not None else None,
                              "p": [round(float(v[:, 0].mean()), 3), 1.3, round(float(-v[:, 1].mean()), 3)]})
            else:
                ps = ue.get_psets(e) if sinif == "IfcWall" else {}
                dis = bool(ps["Pset_WallCommon"]["IsExternal"]) if ps else None
                grup = grup_of(sinif, ad, dis)
                if grup is not None:
                    v = np.array(g.verts, dtype=float).reshape(-1, 3); fc = np.array(g.faces, dtype=int).reshape(-1, 3)
                    vy = np.column_stack([v[:, 0], v[:, 2], -v[:, 1]]).round(4)
                    mid = np.array(g.material_ids, dtype=int) if len(g.material_ids) == len(fc) else np.zeros(len(fc), dtype=int)
                    mats = list(g.materials)
                    bilgi = ""; tur = ""
                    if sinif == "IfcWall":
                        p = ps["PortatifEv_Pano"]; et = etiket.get(ad, {})
                        kesik = dis and p["PanoSinifi"] in ("ozel", "yarim")
                        renkler = {0: (R_OZEL if kesik else (R_STANDART if dis else R_IC), 1.0)}
                        mid = np.zeros(len(fc), dtype=int)
                        tur = "kesik" if kesik else ("standart" if dis else "ic")
                        sayim.append({"dis": bool(dis), "sinif": p["PanoSinifi"], "boy": float(p["Boy_cm"])})
                        bilgi = (f"{et.get('sira', '')} · {p['BOMKod']} {p['BOMKalem'].split(' ', 1)[-1]} · "
                                 f"{p['Boy_cm']:g} × {p['Kalinlik_cm']:g} × {p['Yukseklik_cm']:g} cm · {et.get('duvar', '')}").strip(" ·")
                    elif grup in ("pencere", "kapi") and mats:
                        renkler = {i: ([round(m.diffuse.r(), 3), round(m.diffuse.g(), 3), round(m.diffuse.b(), 3)],
                                       round(1.0 - (m.transparency if m.transparency == m.transparency else 0.0), 2)) for i, m in enumerate(mats)}
                        d = (ue.get_psets(e) or {}).get("PortatifEv_Dograma") or {}
                        bilgi = d.get("BOMKalem", "") or ad
                    else:
                        renkler = {0: (GRUP_RENK.get(grup, [0.7, 0.7, 0.7]), 1.0)}; mid = np.zeros(len(fc), dtype=int)
                        bilgi = ((ue.get_psets(e) or {}).get("PortatifEv_Kapsam") or {}).get("BOMKalem", "") if grup in ("baglanti", "alin", "cati") else ""
                    for i in sorted(set(mid.tolist())):
                        renk, opak = renkler.get(i, renkler[min(renkler)])
                        alt = fc[mid == i]
                        kul, ters = np.unique(alt, return_inverse=True)
                        el.append({"g": grup, "ad": ad, "b": bilgi, "t": tur, "r": renk, "o": opak, "v": vy[kul].reshape(-1).tolist(), "i": ters.reshape(-1).tolist()})
            if not it.next():
                break
    return {"kaynak": Path(ifc_yolu).name, "el": el, "mahal": mahal, "sayim": sayim}


STIL = """
/* yerleşim (Astra'nın 30 Eylül sunum sayfası örnek alındı): başlık bandı, düğme sırası, solda çerçeveli sahne ve oluşum sürgüsü, sağda bilgi ve plan */
:root{--zemin:#edf0ed;--yuzey:#ffffff;--yazi:#203333;--soluk:#5f716a;--cizgi:#c1cac3;--vurgu:#215549;--vurgu-yazi:#ffffff;--uzerinde:#e6ece7;--bant:#163733;--bant-yazi:#f5f4ed;
  --sahne:#dce4df;--yer:#b4c1b6;--rozet:rgba(255,255,255,.88);--uyari:#c48a3c;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;
  --govde:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--zemin:#121816;--yuzey:#1b2421;--yazi:#e6ece8;--soluk:#9db0a8;--cizgi:#34423d;--vurgu:#62b59e;--vurgu-yazi:#0d1a16;--uzerinde:#24302c;--bant:#0f2622;--bant-yazi:#f5f4ed;
  --sahne:#27322e;--yer:#323d38;--rozet:rgba(27,36,33,.9);--uyari:#d9a45c;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;color-scheme:dark}}
:root[data-theme="dark"]{--zemin:#121816;--yuzey:#1b2421;--yazi:#e6ece8;--soluk:#9db0a8;--cizgi:#34423d;--vurgu:#62b59e;--vurgu-yazi:#0d1a16;--uzerinde:#24302c;--bant:#0f2622;--bant-yazi:#f5f4ed;
  --sahne:#27322e;--yer:#323d38;--rozet:rgba(27,36,33,.9);--uyari:#d9a45c;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--zemin);color:var(--yazi);font-family:var(--govde);font-size:15px;line-height:1.4}
.bant{display:flex;align-items:center;justify-content:space-between;gap:18px;padding-block:18px;padding-inline:28px;background:var(--bant);color:var(--bant-yazi)}
.bant b{font-size:22px;letter-spacing:2px}.bant span{font-size:13px;opacity:.82;text-align:right}
.kabuk{max-width:1600px;margin:auto;padding-block:18px;padding-inline:20px}
.araclar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.grup{display:flex;flex-wrap:wrap;gap:8px}.ayrac{flex:1}
button{font:inherit;border:1px solid var(--cizgi);background:var(--yuzey);color:var(--yazi);padding:10px 16px;border-radius:8px;cursor:pointer;touch-action:manipulation}
button:hover{background:var(--uzerinde)}
button[aria-pressed="true"]{color:var(--vurgu-yazi);background:var(--vurgu);border-color:var(--vurgu)}
button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--uyari);outline-offset:2px}
main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px}main>div{min-width:0}
.sahne{position:relative;background:var(--sahne);border-radius:12px;overflow:hidden}
#tuval{height:min(69vh,780px);min-height:440px;touch-action:none}
#c{display:block;width:100%;height:100%;cursor:grab;outline:none;touch-action:none}#c.tut{cursor:grabbing}
.rozet{position:absolute;top:16px;left:18px;background:var(--rozet);padding:8px 12px;border-radius:6px;font-size:13px;pointer-events:none}
.ipucu{position:absolute;bottom:14px;left:18px;right:70px;font-size:12px;pointer-events:none}.ipucu span{background:var(--rozet);padding:6px 10px;border-radius:5px;display:inline-block}
.yakin{position:absolute;right:14px;bottom:12px;display:flex;gap:6px}.yakin button{padding:4px 0;width:36px;font-size:17px;line-height:1.2}
#etiket{position:absolute;inset:0;pointer-events:none;overflow:hidden}
#etiket div{position:absolute;transform:translate(-50%,-50%);background:var(--rozet);border-radius:5px;padding:3px 8px;font-size:12px;white-space:nowrap;text-align:center;font-weight:600}
#etiket small{display:block;color:var(--soluk);font-weight:400;font-variant-numeric:tabular-nums}
#hata{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;color:var(--soluk)}
.olusum{display:flex;align-items:center;flex-wrap:wrap;gap:12px;padding:14px 2px 6px}
.olusum label{font-size:13px;color:var(--soluk)}
input[type=range]{flex:1;min-width:160px;accent-color:var(--vurgu)}
#ilerleme{font-variant-numeric:tabular-nums;min-width:120px;font-size:13px}
.not{font-size:12px;color:var(--soluk);line-height:1.55}
.secim{min-height:46px;margin-top:10px;padding:10px 14px;background:var(--yuzey);border-radius:10px;font-size:13px}
.secim b{display:block;font-size:14px}.secim span{color:var(--soluk)}
.yan{background:var(--yuzey);border-radius:12px;padding:22px;min-width:0}
h1{font-size:24px;font-weight:600;margin:0 0 5px;text-wrap:balance}h2{font-size:16px;margin:24px 0 10px}
.kucuk{font-size:13px;color:var(--soluk);line-height:1.5}
.durum{border-left:3px solid var(--uyari);padding-left:12px;margin:16px 0;font-size:13px;line-height:1.5}
.sayim{width:100%;border-collapse:collapse;font-size:13px}
.sayim td{padding:7px 0;border-top:1px solid var(--cizgi);vertical-align:top}.sayim td:first-child{white-space:nowrap}
.sayim td:nth-child(2){text-align:right;font-variant-numeric:tabular-nums;font-weight:600;padding-inline:10px;white-space:nowrap}
.sayim td:nth-child(3){color:var(--soluk)}
.gosterge{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:14px;font-size:12px;color:var(--soluk)}
.gosterge i{display:inline-block;width:12px;height:12px;border-radius:2px;border:1px solid var(--cizgi);vertical-align:-2px;margin-right:5px}
details{font-size:13px;margin-top:18px;line-height:1.5}summary{cursor:pointer;font-weight:600}details p{margin:8px 0 0;color:var(--soluk)}
.plan{display:block;width:100%;padding:0;border-radius:6px;overflow:hidden;cursor:zoom-in;background:#fff}.plan img{display:block;width:100%;height:auto}
#buyuk{position:fixed;inset:0;z-index:20;background:rgba(10,16,14,.86);overflow:auto;padding:16px;cursor:zoom-out}
#buyuk img{display:block;margin:auto;width:min(1500px,100%);height:auto;background:#fff;border-radius:6px}
#buyuk button{position:fixed;top:calc(12px + env(safe-area-inset-top,0px));right:16px}
@media (max-width:950px){main{grid-template-columns:1fr}#tuval{height:60vh;min-height:360px}}
@media (max-width:560px){.bant{padding-block:14px;padding-inline:16px}.bant b{font-size:19px}.kabuk{padding-block:10px;padding-inline:16px}.araclar,.grup{gap:6px}.araclar button{padding:8px 10px;font-size:13px}.ayrac{display:none}
  #tuval{height:54vh;min-height:330px}#etiket div{font-size:10px;padding:2px 5px}#etiket small{display:inline;margin-left:4px}.ipucu{font-size:11px;left:10px}.rozet{left:10px;top:10px}.yan{padding:16px}}
"""

GOVDE = """
<div id="uyg">
<header class="bant"><b>PORTMAN</b><span>__ALT__</span></header>
<div class="kabuk">
  <div class="araclar">
    <div class="grup" role="group" aria-label="Görünüş">
      <button id="g-dis">Dış görünüş</button><button id="g-ust">Üstten bak</button><button id="g-on">Ön</button><button id="g-arka">Arka</button><button id="g-sol">Sol</button><button id="g-sag">Sağ</button>
    </div>
    <span class="ayrac"></span>
    <div class="grup" role="group" aria-label="Göster">
      <button id="k-cati" aria-pressed="false">Çatıyı aç</button><button id="k-iskelet" aria-pressed="false">Çatı iskeleti</button><button id="k-renk" aria-pressed="false">Pano renkleri</button><button id="k-ad" aria-pressed="false">Oda adları</button><button id="g-don" aria-pressed="false">Döndür</button>
    </div>
  </div>
  <main>
    <div>
      <div class="sahne">
        <div id="tuval"><canvas id="c" tabindex="0" aria-label="Fareyle döndürülebilen üç boyutlu pano modeli"></canvas></div>
        <div id="etiket" hidden></div>
        <div class="rozet" id="kip">Malzemeli dış görünüş</div>
        <div class="ipucu"><span>Sürükle: döndür · Tekerlek: yakınlaştır · Panoya tıkla: kodu ve ölçüsü</span></div>
        <div class="yakin"><button id="g-yakin" aria-label="Yakınlaştır">+</button><button id="g-uzak" aria-label="Uzaklaştır">−</button></div>
        <div id="hata" hidden>Bu tarayıcı 3D çizimi (WebGL) açamadı. Sayfayı Safari ya da Chrome'da açın.</div>
      </div>
      <div class="olusum"><button id="oynat">Oluşumu oynat</button><label for="surgu">Parçalar</label><input id="surgu" type="range" min="0" max="100" value="100" aria-label="Parçaların oluşum yüzdesi"><span id="ilerleme" aria-live="polite">%100</span></div>
      <div class="not">Oluşum, parçaların sunum sırasıdır (zemin, bağlantılar, dış panolar, iç panolar, doğramalar, makaslar, çatı); montaj talimatı değildir.</div>
      <div class="secim" aria-live="polite"><b id="b1">Bir panoya tıklayın</b><span id="b2">Pafta kodu, malzeme kodu ve ölçüsü burada görünür.</span></div>
    </div>
    <aside class="yan">__YAN__</aside>
  </main>
</div>
<div id="buyuk" hidden><button id="kapat">Kapat</button><img alt="Plan paftası, büyütülmüş"></div>
</div>
"""

KOD = r"""
(function(){
'use strict';
var M=__MODEL__;
function $(id){return document.getElementById(id);}
var cv=$('c'),tuval=$('tuval'),r;
try{r=new THREE.WebGLRenderer({canvas:cv,antialias:true});}catch(e){$('hata').hidden=false;return;}
r.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
r.outputEncoding=THREE.sRGBEncoding;r.toneMapping=THREE.ACESFilmicToneMapping;r.toneMappingExposure=0.98;
r.shadowMap.enabled=true;r.shadowMap.type=THREE.PCFSoftShadowMap;
var sc=new THREE.Scene(),cam=new THREE.PerspectiveCamera(38,1,0.05,500);
function renk(h){return new THREE.Color(h).convertSRGBToLinear();}
function renk3(a){return new THREE.Color(a[0],a[1],a[2]).convertSRGBToLinear();}
sc.add(new THREE.HemisphereLight(0xffffff,0x6f7b73,0.62));
var gunes=new THREE.DirectionalLight(0xfff3e0,1.25);gunes.castShadow=true;sc.add(gunes);sc.add(gunes.target);
var dolgu=new THREE.DirectionalLight(0xdce8ff,0.28);sc.add(dolgu);

/* trapez sac: bir doku tekrarı = bir hadve (20 cm) */
function trapez(hex){var c=document.createElement('canvas');c.width=64;c.height=4;var x=c.getContext('2d'),t=new THREE.Color(hex);
  function ton(k){return 'rgb('+Math.round(Math.min(255,t.r*255*k))+','+Math.round(Math.min(255,t.g*255*k))+','+Math.round(Math.min(255,t.b*255*k))+')';}
  x.fillStyle=ton(1);x.fillRect(0,0,64,4);x.fillStyle=ton(0.86);x.fillRect(0,0,5,4);x.fillStyle=ton(1.2);x.fillRect(5,0,13,4);x.fillStyle=ton(0.68);x.fillRect(18,0,5,4);
  var d=new THREE.CanvasTexture(c);d.wrapS=d.wrapT=THREE.RepeatWrapping;d.encoding=THREE.sRGBEncoding;d.anisotropy=r.capabilities.getMaxAnisotropy();return d;}
var R={dis:'#efebe1',ic:'#f7f5ef',makas:'#9ea5ab',baglanti:'#8a9095',zemin:'#aba598',cati:M.cati_rengi||'#5f666e'};
var catiDoku=trapez(R.cati),sirtX=M.mahya!=='z';

var parca=[],secilebilir=[],kutu=new THREE.Box3(),tum=new THREE.Box3();
M.el.forEach(function(e){
  var g0=new THREE.BufferGeometry();g0.setAttribute('position',new THREE.Float32BufferAttribute(e.v,3));g0.setIndex(e.i);
  var g=g0.toNonIndexed();g.computeVertexNormals();g.computeBoundingBox();
  var saydam=e.o<0.95,ayar={side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1,roughness:0.85,metalness:0};
  if(e.g==='cati'){var p=g.attributes.position,uv=new Float32Array(p.count*2);
    for(var i=0;i<p.count;i++){uv[2*i]=(sirtX?p.getX(i):p.getZ(i))/0.2;uv[2*i+1]=(sirtX?p.getZ(i):p.getX(i))/0.2;}
    g.setAttribute('uv',new THREE.BufferAttribute(uv,2));ayar.map=catiDoku;ayar.roughness=0.66;ayar.metalness=0.1;}
  else if(e.g==='dis_pano'||e.g==='alin')ayar.color=renk(R.dis);
  else if(e.g==='ic_pano')ayar.color=renk(R.ic);
  else if(e.g==='makas'){ayar.color=renk(R.makas);ayar.roughness=0.45;ayar.metalness=0.55;}
  else if(e.g==='baglanti'){ayar.color=renk(R.baglanti);ayar.roughness=0.5;ayar.metalness=0.4;}
  else if(e.g==='zemin')ayar.color=renk(R.zemin);
  else{ayar.color=renk3(e.r);if(saydam){ayar.transparent=true;ayar.opacity=Math.max(e.o,0.4);ayar.roughness=0.08;ayar.depthWrite=false;ayar.color=renk('#bcd6e2');}else ayar.roughness=0.6;}
  var m=new THREE.Mesh(g,new THREE.MeshStandardMaterial(ayar));m.castShadow=!saydam;m.receiveShadow=!saydam;m.userData=e;sc.add(m);
  if(e.g!=='makas'&&e.g!=='zemin'&&e.g!=='cati'&&e.g!=='baglanti'){m.add(new THREE.LineSegments(new THREE.EdgesGeometry(g,25),new THREE.LineBasicMaterial({color:0x2b3336,transparent:true,opacity:0.55})));}
  parca.push(m);if(e.g!=='zemin')secilebilir.push(m);
  if(e.g==='dis_pano'||e.g==='ic_pano')kutu.union(g.boundingBox);tum.union(g.boundingBox);
});
var mrk=kutu.getCenter(new THREE.Vector3()),byt=kutu.getSize(new THREE.Vector3()),cap=Math.max(byt.x,byt.z);
var yer=new THREE.Mesh(new THREE.PlaneGeometry(cap*14,cap*14),new THREE.MeshStandardMaterial({roughness:0.95}));yer.rotation.x=-Math.PI/2;yer.position.set(mrk.x,tum.min.y-0.01,mrk.z);yer.receiveShadow=true;sc.add(yer);
gunes.position.set(mrk.x+cap*0.75,cap*1.7,mrk.z+cap*1.15);gunes.target.position.copy(mrk);dolgu.position.set(mrk.x-cap,cap*0.7,mrk.z-cap*1.2);
var gk=gunes.shadow.camera;gk.left=-cap*1.25;gk.right=cap*1.25;gk.top=cap*1.25;gk.bottom=-cap*1.25;gk.near=0.1;gk.far=cap*6;gk.updateProjectionMatrix();
gunes.shadow.mapSize.set(2048,2048);gunes.shadow.bias=-0.0004;gunes.shadow.normalBias=0.03;

/* oluşum sırası: zemin, bağlantılar, dış panolar (yapının çevresinde sırayla), iç panolar, doğramalar, makaslar, çatı */
var asama={zemin:0,baglanti:1,dis_pano:2,ic_pano:3,pencere:4,kapi:4,makas:5,cati:6,alin:6},anahtar={};
parca.forEach(function(m){var e=m.userData;if(anahtar[e.ad]!=null)return;var c=m.geometry.boundingBox.getCenter(new THREE.Vector3()),k;
  if(e.g==='dis_pano'){k=Math.atan2(c.x-mrk.x,c.z-mrk.z);k=(k+Math.PI*2+Math.PI*0.75)%(Math.PI*2);}
  else if(e.g==='makas')k=(sirtX?c.x:c.z)+c.y*0.001;
  else k=(c.x-kutu.min.x)+(kutu.max.z-c.z)*0.01;
  anahtar[e.ad]=asama[e.g]*1000+k;});
var sirali=parca.map(function(m,i){return [anahtar[m.userData.ad],i,m];}).sort(function(a,b){return a[0]-b[0]||a[1]-b[1];}).map(function(a){return a[2];});

/* durum */
var cati='kapali',renkli=false,yuzde=100,oynuyor=false,don=false,kirli=true,secili=null;
function dugme(id,acik){var b=$(id);if(b.hasAttribute('aria-pressed'))b.setAttribute('aria-pressed',acik?'true':'false');}
function gorunur(){var sinir=Math.ceil(sirali.length*yuzde/100),gorulen={},n=0;
  sirali.forEach(function(m,i){var e=m.userData,v=i<sinir;
    if(v&&(e.g==='cati'||e.g==='alin'))v=cati==='kapali';
    if(v&&e.g==='makas')v=cati!=='acik';
    m.visible=v;if(v&&!gorulen[e.ad]){gorulen[e.ad]=1;n++;}});
  if(secili&&!secili.visible)birakSecim();
  $('surgu').value=yuzde;$('ilerleme').textContent='%'+Math.round(yuzde)+' · '+n+' parça';
  $('kip').textContent=(oynuyor?'Parçaların oluşumu':cati==='acik'?'Çatı açık · iç bölmeler':cati==='iskelet'?'Çatı iskeleti · makaslar':'Malzemeli dış görünüş')+(renkli?' · pano renkleri':'');
  $('k-cati').textContent=cati==='acik'?'Çatıyı kapat':'Çatıyı aç';dugme('k-cati',cati==='acik');dugme('k-iskelet',cati==='iskelet');kirli=true;}
function boya(){parca.forEach(function(m){var e=m.userData;if(e.g==='dis_pano')m.material.color.copy(renkli?renk3(e.r):renk(R.dis));else if(e.g==='ic_pano')m.material.color.copy(renkli?renk3(e.r):renk(R.ic));});
  dugme('k-renk',renkli);var g=$('gosterge');if(g)g.hidden=!renkli;gorunur();}

/* kamera: hedefin çevresinde yön (az), yükseklik (el) ve uzaklık */
var ilk={az:0.62,el:0.5,uz:cap*2.05,hx:mrk.x,hy:byt.y*0.42,hz:mrk.z};
var K={az:ilk.az,el:ilk.el,uz:ilk.uz,h:new THREE.Vector3(ilk.hx,ilk.hy,ilk.hz)};
function tema(){var s=getComputedStyle(document.documentElement),a=(s.getPropertyValue('--sahne').trim()||'#dce4df'),b=(s.getPropertyValue('--yer').trim()||'#b4c1b6');
  sc.background=new THREE.Color(a);sc.fog=new THREE.Fog(new THREE.Color(a),cap*3.2,cap*7.5);yer.material.color.copy(renk(b));kirli=true;}
function ciz(){
  K.el=Math.max(-0.03,Math.min(1.5607,K.el));K.uz=Math.max(cap*0.3,Math.min(cap*5,K.uz));
  var u=K.uz*Math.max(1,1.3/cam.aspect);
  cam.position.set(K.h.x+u*Math.cos(K.el)*Math.sin(K.az),K.h.y+u*Math.sin(K.el),K.h.z+u*Math.cos(K.el)*Math.cos(K.az));
  cam.lookAt(K.h);r.render(sc,cam);etiketle();kirli=false;}
function boyut(){var w=tuval.clientWidth,h=tuval.clientHeight;if(!w||!h)return;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();kirli=true;}
window.addEventListener('resize',boyut);
if(window.ResizeObserver){new ResizeObserver(boyut).observe(tuval);}
if(window.matchMedia){var mq=window.matchMedia('(prefers-color-scheme: dark)');if(mq.addEventListener)mq.addEventListener('change',tema);else if(mq.addListener)mq.addListener(tema);}
if(window.MutationObserver){new MutationObserver(tema).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});}

/* oda adları */
var etk=$('etiket'),etkD=M.mahal.map(function(o){var d=document.createElement('div');d.textContent=o.ad;if(o.alan!=null){var s=document.createElement('small');s.textContent=String(Math.round(o.alan))+' m²';d.appendChild(s);}etk.appendChild(d);return d;});
var v3=new THREE.Vector3();
function etiketle(){if(etk.hidden)return;var w=tuval.clientWidth,h=tuval.clientHeight;M.mahal.forEach(function(o,i){v3.set(o.p[0],o.p[1],o.p[2]).project(cam);var d=etkD[i];d.hidden=v3.z>1;d.style.left=((v3.x+1)/2*w)+'px';d.style.top=((1-v3.y)/2*h)+'px';});}
function odaAdi(acik){etk.hidden=!acik;dugme('k-ad',acik);kirli=true;}

/* fare, dokunma, tekerlek, klavye */
var imlec={},tek=null,basX=0,basY=0,oynadi=false;
function durDon(){if(don){don=false;dugme('g-don',false);$('g-don').textContent='Döndür';}}
function kaydir(dx,dy){var s=K.uz*0.0016,sag=new THREE.Vector3(Math.cos(K.az),0,-Math.sin(K.az));K.h.addScaledVector(sag,-dx*s);K.h.y=Math.max(0,K.h.y+dy*s);}
function bas(id,x,y,kay){imlec[id]={x:x,y:y};tek=Object.keys(imlec).length===1?{kay:kay}:null;basX=x;basY=y;oynadi=false;cv.classList.add('tut');durDon();}
function oyna(id,x,y){var p=imlec[id];if(!p)return;var dx=x-p.x,dy=y-p.y,ids=Object.keys(imlec);
  if(ids.length>=2){var o=imlec[ids[0]===String(id)?ids[1]:ids[0]],eski=Math.hypot(p.x-o.x,p.y-o.y),yeni=Math.hypot(x-o.x,y-o.y);if(eski>0&&yeni>0)K.uz*=eski/yeni;kaydir(dx/2,dy/2);}
  else if(tek&&tek.kay){kaydir(dx,dy);}
  else{K.az-=dx*0.008;K.el+=dy*0.008;}
  p.x=x;p.y=y;if(Math.hypot(x-basX,y-basY)>5)oynadi=true;kirli=true;}
function birak(id,x,y){if(!imlec[id])return;delete imlec[id];if(!Object.keys(imlec).length){cv.classList.remove('tut');if(!oynadi)sec(x,y);}}
function yerB(e){var b=cv.getBoundingClientRect();return [e.clientX-b.left,e.clientY-b.top];}
if(window.PointerEvent){
  cv.addEventListener('pointerdown',function(e){var q=yerB(e);try{cv.setPointerCapture(e.pointerId);}catch(_){}bas(e.pointerId,q[0],q[1],e.button===2||e.button===1||e.shiftKey);cv.focus({preventScroll:true});e.preventDefault();});
  cv.addEventListener('pointermove',function(e){if(imlec[e.pointerId]){var q=yerB(e);oyna(e.pointerId,q[0],q[1]);e.preventDefault();}});
  ['pointerup','pointercancel','lostpointercapture'].forEach(function(n){cv.addEventListener(n,function(e){var q=yerB(e);birak(e.pointerId,q[0],q[1]);});});
}else{
  cv.addEventListener('mousedown',function(e){var q=yerB(e);bas('m',q[0],q[1],e.button===2||e.shiftKey);e.preventDefault();});
  window.addEventListener('mousemove',function(e){if(imlec.m){var q=yerB(e);oyna('m',q[0],q[1]);}});
  window.addEventListener('mouseup',function(e){var q=yerB(e);birak('m',q[0],q[1]);});
  cv.addEventListener('touchstart',function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();bas('t'+t.identifier,t.clientX-b.left,t.clientY-b.top,false);}e.preventDefault();},{passive:false});
  cv.addEventListener('touchmove',function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();oyna('t'+t.identifier,t.clientX-b.left,t.clientY-b.top);}e.preventDefault();},{passive:false});
  ['touchend','touchcancel'].forEach(function(n){cv.addEventListener(n,function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();birak('t'+t.identifier,t.clientX-b.left,t.clientY-b.top);}});});
}
cv.addEventListener('wheel',function(e){var d=e.deltaMode===1?e.deltaY*32:e.deltaY;if(e.ctrlKey)d*=4;K.uz*=Math.exp(d*0.0012);kirli=true;e.preventDefault();},{passive:false});
cv.addEventListener('contextmenu',function(e){e.preventDefault();});
cv.addEventListener('keydown',function(e){var k=e.key,a=0.09;if(k==='ArrowLeft')K.az-=a;else if(k==='ArrowRight')K.az+=a;else if(k==='ArrowUp')K.el+=a;else if(k==='ArrowDown')K.el-=a;else if(k==='+'||k==='=')K.uz*=0.88;else if(k==='-'||k==='_')K.uz*=1.14;else return;kirli=true;e.preventDefault();});

/* pano seçimi */
var isin=new THREE.Raycaster(),nk=new THREE.Vector2();
function birakSecim(){if(secili){secili.material.emissive.setHex(0);secili=null;}$('b1').textContent='Bir panoya tıklayın';$('b2').textContent='Pafta kodu, malzeme kodu ve ölçüsü burada görünür.';}
function sec(x,y){nk.set(x/tuval.clientWidth*2-1,-(y/tuval.clientHeight)*2+1);isin.setFromCamera(nk,cam);
  var h=isin.intersectObjects(secilebilir.filter(function(m){return m.visible;}),false);birakSecim();
  if(h.length){secili=h[0].object;secili.material.emissive.setHex(0x0b3d36);var d=secili.userData;$('b1').textContent=d.b||d.ad;$('b2').textContent='IFC adı: '+d.ad;}
  kirli=true;}

/* düğmeler */
function bak(az,el){K.az=az;K.el=el;K.uz=ilk.uz;K.h.set(ilk.hx,ilk.hy,ilk.hz);durDon();kirli=true;}
var P=Math.PI;
function durOlusum(){oynuyor=false;$('oynat').textContent='Oluşumu oynat';}
$('g-dis').addEventListener('click',function(){cati='kapali';yuzde=100;durOlusum();odaAdi(false);gorunur();bak(ilk.az,ilk.el);});
$('g-ust').addEventListener('click',function(){bak(0,1.5607);});
$('g-on').addEventListener('click',function(){bak(0,0.1);});
$('g-arka').addEventListener('click',function(){bak(P,0.1);});
$('g-sag').addEventListener('click',function(){bak(P/2,0.1);});
$('g-sol').addEventListener('click',function(){bak(-P/2,0.1);});
$('g-yakin').addEventListener('click',function(){K.uz*=0.82;kirli=true;});
$('g-uzak').addEventListener('click',function(){K.uz*=1.22;kirli=true;});
$('k-cati').addEventListener('click',function(){cati=cati==='acik'?'kapali':'acik';if(cati==='acik'){K.el=Math.max(K.el,1.08);odaAdi(true);}else odaAdi(false);gorunur();});
$('k-iskelet').addEventListener('click',function(){cati=cati==='iskelet'?'kapali':'iskelet';gorunur();});
$('k-renk').addEventListener('click',function(){renkli=!renkli;boya();});
$('k-ad').addEventListener('click',function(){odaAdi(etk.hidden);});
$('g-don').addEventListener('click',function(){don=!don;dugme('g-don',don);$('g-don').textContent=don?'Dönüşü durdur':'Döndür';});
$('oynat').addEventListener('click',function(){oynuyor=!oynuyor;if(oynuyor&&yuzde>=100)yuzde=0;$('oynat').textContent=oynuyor?'Duraklat':'Oluşumu oynat';gorunur();});
$('surgu').addEventListener('input',function(e){durOlusum();yuzde=Number(e.target.value);gorunur();});

/* plan: tıklayınca sayfanın içinde büyür */
var plan=$('plan'),buyuk=$('buyuk');
function kapat(){buyuk.hidden=true;}
if(plan){plan.addEventListener('click',function(){buyuk.querySelector('img').src=plan.querySelector('img').src;buyuk.hidden=false;$('kapat').focus();});
  buyuk.addEventListener('click',kapat);document.addEventListener('keydown',function(e){if(e.key==='Escape')kapat();});}

var azalt=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches,sonT=performance.now();
function dongu(t){var dt=Math.min(0.05,(t-sonT)/1000);sonT=t;
  if(don){K.az+=dt*(azalt?0.08:0.2);kirli=true;}
  if(oynuyor){yuzde=Math.min(100,yuzde+dt*(azalt?40:9));if(yuzde>=100){oynuyor=false;$('oynat').textContent='Yeniden oynat';}gorunur();}
  if(kirli)ciz();requestAnimationFrame(dongu);}
tema();boyut();boya();requestAnimationFrame(dongu);
window.__portman3b={K:K,get cati(){return cati;},get yuzde(){return yuzde;},get renkli(){return renkli;},
  say:function(g){return parca.filter(function(m){return m.visible&&m.userData.g===g;}).length;},toplam:parca.length,ciz:ciz};
})();
"""

THREE_CDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'
CATI_RENGI = {"kırmızı": "#8f2a2c", "antrasit": "#4a4f57", "gri": "#5f666e", "yeşil": "#2f6b45", "mavi": "#2f5e8a", "kahverengi": "#5b3a21"}


def tr(v: float, n: int = 0) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def boy_yaz(v: float) -> str:
    return tr(v, 0 if abs(v - round(v)) < 1e-6 else (1 if abs(v * 10 - round(v * 10)) < 1e-6 else 2))


def plan_gorseli(png: Path, en: int = 1500) -> str | None:
    """Plan paftasının sayfaya gömülen küçültülmüş kopyası (data URI). Pafta yoksa None."""
    if not png.exists():
        return None
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if im.width > en:
        im = im.resize((en, round(im.height * en / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=74, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def yan_pano(ie: dict, m: dict, ozet: dict, plan_uri: str | None) -> str:
    """Sağdaki bilgi panosu: başlık, taslak notu, parça sayımı, renk göstergesi, sınırlar, plan."""
    from collections import Counter
    y = ie["yapi"]; g = y.get("dis_olcu_cm", {}); k = y.get("duvar_kalinligi_cm", {"dis": 10, "ic": 6})
    x_cm, y_cm = float(g.get("x", 0)), float(g.get("y", 0))
    dis = [s for s in m["sayim"] if s["dis"]]; ic = [s for s in m["sayim"] if not s["dis"]]
    tam = [s for s in dis if s["sinif"] == "tam"]; kesik = Counter(s["boy"] for s in dis if s["sinif"] != "tam")
    kesik_yazi = ", ".join(f"{boy_yaz(b)} cm × {n}" for b, n in sorted(kesik.items(), reverse=True))
    ic_tam = sum(1 for s in ic if s["sinif"] == "tam")
    satir = [("Dış pano", len(dis), f"{len(tam)} tam (125,5 cm)" + (f" · {sum(kesik.values())} kesilmiş ({kesik_yazi})" if kesik else "")),
             ("İç pano", len(ic), f"{ic_tam} tam · {len(ic) - ic_tam} özel boy"),
             ("Pencere", ozet.get("pencere", ""), ""), ("Kapı", ozet.get("kapi", ""), ""),
             ("Makas", ozet.get("cati", {}).get("makas", ""), "pano akslarında"),
             ("Duvar", f"{k['dis'] * 10:g} / {k['ic'] * 10:g}", "dış / iç, mm")]
    tablo = "".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(str(b))}</td><td>{html.escape(c)}</td></tr>" for a, b, c in satir)
    no = f"{ie['is_emri_no']} r{int(ie.get('revizyon', 1)):02d}"
    brut = x_cm * y_cm / 1e4
    plan = (f'<div><h2>Plan</h2><button class="plan" id="plan" aria-label="Planı büyüt"><img src="{plan_uri}" alt="Plan paftası"></button>'
            '<p class="not">Plana tıklayınca büyür. Plan ve model aynı İş Emri\'nden üretilir.</p></div>') if plan_uri else ""
    return (f'<div><h1>3+1 · {brut:.0f} m²</h1><div class="kucuk">{tr(x_cm / 100, 2)} × {tr(y_cm / 100, 2)} m · tek kat prefabrik · duvar yüksekliği {float(y.get("duvar_yuksekligi_cm", 250)):g} cm</div>'
            '<div class="durum">El çiziminden kurulan pano pano model. Taslaktır; üretim ve statik projesi değildir.</div>'
            f'<table class="sayim"><tbody>{tablo}</tbody></table>'
            '<div class="gosterge" id="gosterge" hidden><span><i style="background:var(--standart)"></i>Tam pano 125,5</span><span><i style="background:var(--kesik)"></i>Kesilmiş pano</span><span><i style="background:var(--ic)"></i>İç pano</span></div>'
            f'<details><summary>Kaynak ve sınırlar</summary><p>Model {html.escape(no)} İş Emri\'nden üretilen IFC dosyasından gelir; her pano ayrı parçadır ve pafta kodunu taşır.</p>'
            '<p>Renkler ve malzeme görünümü sunum içindir. Çatı kaplama rengi bilinmediği için gri çizildi; duvar, doğrama ve çatı renkleri nihai ürün kararı değildir.</p>'
            '<p>Köşe ve H bağlantı ölçüleri, dar kalan son panolar ve makas yönü teyit bekliyor.</p></details></div>' + plan)


def sayfalar(m: dict, alt: str, yan: str, kisa_ad: str) -> tuple[str, str]:
    """(kendi başına açılan HTML, yayımlanacak sayfa parçası)."""
    govde = GOVDE.replace("__ALT__", html.escape(alt)).replace("__YAN__", yan)
    veri = {k: v for k, v in m.items() if k != "sayim"}
    kod = KOD.replace("__MODEL__", json.dumps(veri, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    bas = f"<title>{html.escape(kisa_ad)}</title>\n<style>{STIL}</style>\n"
    three = (KOK / "motor" / "vendor" / "three.min.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    tek = ('<!doctype html>\n<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
           f"{bas}<style>html,body{{margin:0}}[hidden]{{display:none!important}}</style></head>\n<body>{govde}\n<script>{three}</script>\n<script>{kod}</script>\n</body></html>\n")
    parca = f"{bas}{govde}\n{THREE_CDN}\n<script>{kod}</script>\n"
    return tek, parca


def uret(is_emri_yolu: Path) -> dict:
    import yukleme_listesi
    ie = json.loads(Path(is_emri_yolu).read_text(encoding="utf-8"))
    no = ie["is_emri_no"]; rev = int(ie.get("revizyon", 1))
    hedef = CIKTI / no / "ifc"
    ifc = hedef / f"Portman_{no}_r{rev:02d}.ifc"
    if not ifc.exists():
        raise SystemExit(f"DUR: önce IFC üretilmeli (ifc_3b.py): {ifc}")
    md = yukleme_listesi.model(ie)
    etiket = {s["ifc"]: {"kod": s["kod"], "sira": s["sira"], "duvar": s["duvar"], "boy_mm": s["boy"]} for s in md["satirlar"] if s["ifc"]}
    (hedef / "pano_etiketleri.json").write_text(json.dumps(etiket, ensure_ascii=False, indent=1), encoding="utf-8")
    m = model_json(ifc, etiket)
    m["mahya"] = "x" if ie.get("cati", {}).get("makas_ekseni") == "y" else "z"     # mahyanın sayfadaki ekseni (three.js: x, z = −y)
    renk_adi = str(ie.get("pafta", {}).get("ozellikler", {}).get("Çatı Kaplama Rengi", "")).strip().lower()
    m["cati_rengi"] = CATI_RENGI.get(renk_adi, CATI_RENGI["gri"])
    ozet_yolu = hedef / "ifc_ozet.json"
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8")).get("ozet", {}) if ozet_yolu.exists() else {}
    g = md["girdi"]
    plan_uri = plan_gorseli(CIKTI / no / "plan" / f"Portman_{no}_r{rev:02d}_plan.png")
    alt = f"3+1 · {tr(g['x'] / 100, 2)} × {tr(g['y'] / 100, 2)} m · pano pano model · r{rev:02d}"
    adlar = ie.get("pafta", {}).get("mahal_adi", {})       # oda adları plan paftasındakiyle aynı yazılır
    for o in m["mahal"]:
        o["ad"] = adlar.get(o["ad"], o["ad"])
    tek, parca = sayfalar(m, alt, yan_pano(ie, m, ozet, plan_uri), f"3+1 Pano Modeli {g['x']:g}×{g['y']:g}")
    y1 = hedef / f"Portman_{no}_r{rev:02d}_3B.html"; y2 = hedef / f"Portman_{no}_r{rev:02d}_3B_yayin.html"
    y1.write_text(tek, encoding="utf-8"); y2.write_text(parca, encoding="utf-8")
    from collections import Counter
    return {"html": str(y1), "yayin": str(y2), "bayt": [y1.stat().st_size, y2.stat().st_size], "parca": dict(Counter(e["g"] for e in m["el"])), "mahal": len(m["mahal"]),
            "plan_gomulu": plan_uri is not None, "pano_sayimi": {"dis": sum(1 for s in m["sayim"] if s["dis"]), "ic": sum(1 for s in m["sayim"] if not s["dis"])},
            "etiketli_pano": sum(1 for e in m["el"] if e["g"] in ("dis_pano", "ic_pano") and e["b"].split(" · ")[0])}


if __name__ == "__main__":
    yol = Path(sys.argv[1]) if len(sys.argv) > 1 else BURASI / "is_emri_3arti1_1150x1050.json"
    if not yol.is_absolute() and not yol.exists():
        yol = BURASI / yol
    print(json.dumps(uret(yol), ensure_ascii=False, indent=1))
