"""6 Ekim 2026 denemesi: IFC → pano pano 3D sayfası (tek dosya; çevirme, yakınlaştırma, çatı kaldırma, pano bilgisi).

    python deneme/2026-10-06_kalinlik_160_100/sayfa_3b.py [is_emri.json]

`motor/ucb_sayfa.py`'nin yerine denenen sayfa (Lokman, 6 Ekim 19:46: çevirme ve çatı kaldırma çalışmıyordu).
Farklar: çatı örtüsü, alın ve makaslar ayrı katman (eski sayfa çatı örtüsünü gizlemiyordu, çünkü örtü IfcSlab);
çevirme kendi yazılmış denetimle (fare, dokunma, tekerlek, klavye ve ekrandaki düğmeler); her pano ayrı nesne ve
tıklanınca pafta kodu, malzeme kodu ve ölçüsü görünür; cam ve kasa ayrı renkte; açık ve koyu tema.
İki çıktı: kendi başına açılan HTML (three.js gömülü, ağ gerekmez) ve yayımlanacak sayfa parçası (three.js cdnjs'ten).
Ayrıca Blender betiği için pano etiketlerini yazar (`pano_etiketleri.json`).
"""
from __future__ import annotations
import html, json, multiprocessing, os, sys
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
    el, mahal = [], []
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
                    bilgi = ""
                    if sinif == "IfcWall":
                        p = ps["PortatifEv_Pano"]; et = etiket.get(ad, {})
                        kesik = dis and p["PanoSinifi"] in ("ozel", "yarim")
                        renkler = {0: (R_OZEL if kesik else (R_STANDART if dis else R_IC), 1.0)}
                        mid = np.zeros(len(fc), dtype=int)
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
                        el.append({"g": grup, "ad": ad, "b": bilgi, "r": renk, "o": opak, "v": vy[kul].reshape(-1).tolist(), "i": ters.reshape(-1).tolist()})
            if not it.next():
                break
    return {"kaynak": Path(ifc_yolu).name, "el": el, "mahal": mahal}


STIL = """
/* yerleşim: üstte ince araç çubuğu, altında ekranı dolduran sahne; bilgi ve görünüş düğmeleri sahnenin köşelerinde */
:root{--zemin:#eef0ee;--yuzey:#ffffff;--yazi:#1d2327;--soluk:#5c666d;--cizgi:#cfd5d3;--vurgu:#0d6a73;--vurgu-yazi:#ffffff;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;
  --govde:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;--sayi:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--zemin:#15191b;--yuzey:#20262a;--yazi:#e8ecec;--soluk:#9aa6aa;--cizgi:#374045;--vurgu:#4fb6bf;--vurgu-yazi:#0c1416;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;color-scheme:dark}}
:root[data-theme="dark"]{--zemin:#15191b;--yuzey:#20262a;--yazi:#e8ecec;--soluk:#9aa6aa;--cizgi:#374045;--vurgu:#4fb6bf;--vurgu-yazi:#0c1416;--kesik:#b285d4;--standart:#ded6c2;--ic:#f0ede3;color-scheme:dark}
html,body{height:100%}
body{background:var(--zemin);color:var(--yazi);font-family:var(--govde);font-size:14px;line-height:1.35}
#uyg{height:100%;display:flex;flex-direction:column;min-height:0}
.ust{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;padding-block:8px;padding-inline:16px;background:var(--yuzey);border-bottom:1px solid var(--cizgi)}
.ad{display:flex;flex-direction:column;min-width:0;margin-right:auto}
.ad b{font-size:15px;font-weight:650;text-wrap:balance}.ad span{color:var(--soluk);font-size:12px}
.grup{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.grup>span{color:var(--soluk);font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-right:2px}
button{font:inherit;font-size:13px;color:var(--yazi);background:var(--yuzey);border:1px solid var(--cizgi);border-radius:6px;padding:6px 10px;cursor:pointer;touch-action:manipulation}
button:hover{border-color:var(--vurgu)}button:focus-visible{outline:2px solid var(--vurgu);outline-offset:2px}
button[aria-pressed="true"]{background:var(--vurgu);border-color:var(--vurgu);color:var(--vurgu-yazi)}
.sahne{position:relative;flex:1;min-height:0;overflow:hidden}
#c{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:grab;outline:none}
#c.tut{cursor:grabbing}
#etiket{position:absolute;inset:0;pointer-events:none;overflow:hidden}
#etiket div{position:absolute;transform:translate(-50%,-50%);background:var(--yuzey);color:var(--yazi);border:1px solid var(--cizgi);border-radius:4px;padding:2px 6px;font-size:12px;white-space:nowrap;text-align:center}
#etiket small{display:block;color:var(--soluk);font-family:var(--sayi);font-size:11px}
#bilgi{position:absolute;left:16px;bottom:16px;max-width:min(560px,calc(100% - 32px));background:var(--yuzey);border:1px solid var(--cizgi);border-radius:8px;padding:8px 12px;font-size:13px}
#bilgi b{display:block}#bilgi span{color:var(--soluk);font-size:12px}
.yon{position:absolute;right:16px;top:12px;display:grid;grid-template-columns:repeat(3,auto);gap:6px}
.yon .genis{grid-column:span 3}
.gosterge{position:absolute;right:16px;bottom:16px;display:flex;flex-wrap:wrap;gap:4px 12px;justify-content:flex-end;max-width:calc(100% - 32px);background:var(--yuzey);border:1px solid var(--cizgi);border-radius:8px;padding:6px 10px;font-size:12px;color:var(--soluk)}
.gosterge i{display:inline-block;width:12px;height:12px;border-radius:2px;border:1px solid var(--cizgi);vertical-align:-2px;margin-right:5px}
#hata{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;color:var(--soluk)}
@media (max-width:640px){#bilgi{bottom:56px;font-size:12px}.yon{left:16px;right:16px;top:8px;grid-template-columns:repeat(5,1fr);gap:4px}.yon .genis{grid-column:span 2}.yon button{padding:5px 2px;font-size:12px}}
"""

GOVDE = """
<div id="uyg">
  <header class="ust">
    <div class="ad"><b>__BASLIK__</b><span>Pano pano model · ölçüler planla aynı · taslak, üretim çizimi değildir</span></div>
    <div class="grup" role="group" aria-label="Katmanlar"><span>Göster</span>
      <button id="k-cati" aria-pressed="true">Çatı</button>
      <button id="k-makas" aria-pressed="true">Makaslar</button>
      <button id="k-ic" aria-pressed="true">İç duvarlar</button>
      <button id="k-ad" aria-pressed="false">Oda adları</button>
    </div>
  </header>
  <div class="sahne">
    <canvas id="c" tabindex="0" aria-label="3D model. Sürükleyerek çevirin, tekerlekle yakınlaştırın."></canvas>
    <div id="etiket" hidden></div>
    <div id="hata" hidden>Bu tarayıcı 3D çizimi (WebGL) açamadı. Sayfayı Safari ya da Chrome'da açın.</div>
    <div class="yon" role="group" aria-label="Görünüş">
      <button id="g-3b" class="genis">3B görünüş</button>
      <button id="g-on">Ön</button><button id="g-arka">Arka</button><button id="g-ust">Üst</button>
      <button id="g-sol">Sol</button><button id="g-sag">Sağ</button><button id="g-don" aria-pressed="false">Döndür</button>
      <button id="g-yakin" aria-label="Yakınlaştır">+</button><button id="g-uzak" aria-label="Uzaklaştır">−</button><button id="g-sifir">Sıfırla</button>
    </div>
    <div id="bilgi"><b id="b1">Bir panoya tıklayın</b><span id="b2">Sürükle: çevir · Tekerlek ya da iki parmak: yakınlaştır · Sağ tuş ya da Shift + sürükle: kaydır</span></div>
    <div class="gosterge"><span><i style="background:var(--standart)"></i>Standart pano 125,5</span><span><i style="background:var(--kesik)"></i>Kesilmiş pano</span><span><i style="background:var(--ic)"></i>İç pano</span></div>
  </div>
</div>
"""

KOD = r"""
(function(){
'use strict';
var M=__MODEL__;
var cv=document.getElementById('c'),sahneEl=cv.parentNode,r;
try{r=new THREE.WebGLRenderer({canvas:cv,antialias:true});}catch(e){document.getElementById('hata').hidden=false;return;}
r.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
var sc=new THREE.Scene(),cam=new THREE.PerspectiveCamera(42,1,0.05,600);
sc.add(new THREE.HemisphereLight(0xffffff,0x8d8a80,0.95));
var gunes=new THREE.DirectionalLight(0xffffff,0.55);gunes.position.set(8,14,10);sc.add(gunes);
var katman={cati:[],makas:[],ic:[]},secilebilir=[],kutu=new THREE.Box3();
M.el.forEach(function(e){
  var g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(e.v,3));g.setIndex(e.i);g.computeVertexNormals();
  var saydam=e.o<0.95;
  var m=new THREE.Mesh(g,new THREE.MeshLambertMaterial({color:new THREE.Color(e.r[0],e.r[1],e.r[2]),transparent:saydam,opacity:saydam?Math.max(e.o,0.35):1,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
  m.userData=e;sc.add(m);
  if(e.g!=='makas'&&e.g!=='zemin'){m.add(new THREE.LineSegments(new THREE.EdgesGeometry(g,25),new THREE.LineBasicMaterial({color:0x22272b,transparent:true,opacity:e.g==='cati'?0.35:0.7})));}
  if(e.g==='cati'||e.g==='alin')katman.cati.push(m);else if(e.g==='makas')katman.makas.push(m);else if(e.g==='ic_pano')katman.ic.push(m);
  if(e.g!=='zemin'&&e.g!=='makas')secilebilir.push(m);
  if(e.g==='dis_pano'||e.g==='ic_pano')kutu.expandByObject(m);
});
var mrk=kutu.getCenter(new THREE.Vector3()),byt=kutu.getSize(new THREE.Vector3()),cap=Math.max(byt.x,byt.z);
var zemin=new THREE.Mesh(new THREE.PlaneGeometry(cap*8,cap*8),new THREE.MeshLambertMaterial({color:0x8a9484}));zemin.rotation.x=-Math.PI/2;zemin.position.set(mrk.x,-0.16,mrk.z);sc.add(zemin);

/* kamera: hedefin çevresinde yön (az), yükseklik (el) ve uzaklık */
var ilk={az:0.62,el:0.5,uz:cap*1.9,hx:mrk.x,hy:byt.y*0.45,hz:mrk.z};
var K={az:ilk.az,el:ilk.el,uz:ilk.uz,h:new THREE.Vector3(ilk.hx,ilk.hy,ilk.hz)},don=false;
function tema(){var s=getComputedStyle(document.documentElement).getPropertyValue('--zemin').trim()||'#eef0ee';sc.background=new THREE.Color(s);zemin.material.color.set(new THREE.Color(s).multiplyScalar(0.82));}
function ciz(){
  K.el=Math.max(-0.05,Math.min(1.5607,K.el));K.uz=Math.max(cap*0.25,Math.min(cap*6,K.uz));
  cam.position.set(K.h.x+K.uz*Math.cos(K.el)*Math.sin(K.az),K.h.y+K.uz*Math.sin(K.el),K.h.z+K.uz*Math.cos(K.el)*Math.cos(K.az));
  cam.lookAt(K.h);r.render(sc,cam);etiketle();
}
function boyut(){var w=sahneEl.clientWidth,h=sahneEl.clientHeight;if(!w||!h)return;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();ciz();}
window.addEventListener('resize',boyut);
if(window.ResizeObserver){new ResizeObserver(boyut).observe(sahneEl);}
if(window.matchMedia){var mq=window.matchMedia('(prefers-color-scheme: dark)');var f=function(){tema();ciz();};if(mq.addEventListener)mq.addEventListener('change',f);else if(mq.addListener)mq.addListener(f);}
if(window.MutationObserver){new MutationObserver(function(){tema();ciz();}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});}

/* oda adları */
var etk=document.getElementById('etiket'),etkD=M.mahal.map(function(o){var d=document.createElement('div');d.textContent=o.ad;if(o.alan!=null){var s=document.createElement('small');s.textContent=String(o.alan.toFixed(2)).replace('.',',')+' m²';d.appendChild(s);}etk.appendChild(d);return d;});
var v3=new THREE.Vector3();
function etiketle(){if(etk.hidden)return;var w=sahneEl.clientWidth,h=sahneEl.clientHeight;M.mahal.forEach(function(o,i){v3.set(o.p[0],o.p[1],o.p[2]).project(cam);var d=etkD[i];d.hidden=v3.z>1;d.style.left=((v3.x+1)/2*w)+'px';d.style.top=((1-v3.y)/2*h)+'px';});}

/* fare, dokunma, tekerlek, klavye */
var imlec={},tek=null,son=0,basX=0,basY=0,oynadi=false;
function kaydir(dx,dy){var s=K.uz*0.0016;var sag=new THREE.Vector3(Math.cos(K.az),0,-Math.sin(K.az));K.h.addScaledVector(sag,-dx*s);K.h.y=Math.max(0,K.h.y+dy*s);}
function bas(id,x,y,kay){imlec[id]={x:x,y:y};tek=Object.keys(imlec).length===1?{kay:kay}:null;basX=x;basY=y;oynadi=false;son=0;cv.classList.add('tut');don=false;dugme('g-don',false);}
function oyna(id,x,y){var p=imlec[id];if(!p)return;var dx=x-p.x,dy=y-p.y;var ids=Object.keys(imlec);
  if(ids.length>=2){var o=imlec[ids[0]===String(id)?ids[1]:ids[0]];var eski=Math.hypot(p.x-o.x,p.y-o.y),yeni=Math.hypot(x-o.x,y-o.y);if(eski>0&&yeni>0)K.uz*=eski/yeni;kaydir(dx/2,dy/2);}
  else if(tek&&tek.kay){kaydir(dx,dy);}
  else{K.az-=dx*0.0075;K.el+=dy*0.0075;}
  p.x=x;p.y=y;if(Math.hypot(x-basX,y-basY)>5)oynadi=true;ciz();}
function birak(id,x,y){if(!imlec[id])return;delete imlec[id];if(!Object.keys(imlec).length){cv.classList.remove('tut');if(!oynadi)sec(x,y);}}
function yer(e){var b=cv.getBoundingClientRect();return [e.clientX-b.left,e.clientY-b.top];}
if(window.PointerEvent){
  cv.addEventListener('pointerdown',function(e){var q=yer(e);try{cv.setPointerCapture(e.pointerId);}catch(_){}bas(e.pointerId,q[0],q[1],e.button===2||e.button===1||e.shiftKey);cv.focus({preventScroll:true});e.preventDefault();});
  cv.addEventListener('pointermove',function(e){if(imlec[e.pointerId]){var q=yer(e);oyna(e.pointerId,q[0],q[1]);e.preventDefault();}});
  ['pointerup','pointercancel','lostpointercapture'].forEach(function(n){cv.addEventListener(n,function(e){var q=yer(e);birak(e.pointerId,q[0],q[1]);});});
}else{
  cv.addEventListener('mousedown',function(e){var q=yer(e);bas('m',q[0],q[1],e.button===2||e.shiftKey);e.preventDefault();});
  window.addEventListener('mousemove',function(e){if(imlec.m){var q=yer(e);oyna('m',q[0],q[1]);}});
  window.addEventListener('mouseup',function(e){var q=yer(e);birak('m',q[0],q[1]);});
  cv.addEventListener('touchstart',function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();bas('t'+t.identifier,t.clientX-b.left,t.clientY-b.top,false);}e.preventDefault();},{passive:false});
  cv.addEventListener('touchmove',function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();oyna('t'+t.identifier,t.clientX-b.left,t.clientY-b.top);}e.preventDefault();},{passive:false});
  ['touchend','touchcancel'].forEach(function(n){cv.addEventListener(n,function(e){for(var i=0;i<e.changedTouches.length;i++){var t=e.changedTouches[i],b=cv.getBoundingClientRect();birak('t'+t.identifier,t.clientX-b.left,t.clientY-b.top);}});});
}
cv.addEventListener('wheel',function(e){var d=e.deltaMode===1?e.deltaY*32:e.deltaY;if(e.ctrlKey)d*=4;K.uz*=Math.exp(d*0.0012);ciz();e.preventDefault();},{passive:false});
cv.addEventListener('contextmenu',function(e){e.preventDefault();});
cv.addEventListener('keydown',function(e){var k=e.key,a=0.09;if(k==='ArrowLeft')K.az-=a;else if(k==='ArrowRight')K.az+=a;else if(k==='ArrowUp')K.el+=a;else if(k==='ArrowDown')K.el-=a;else if(k==='+'||k==='=')K.uz*=0.88;else if(k==='-'||k==='_')K.uz*=1.14;else return;ciz();e.preventDefault();});

/* pano seçimi */
var isin=new THREE.Raycaster(),nk=new THREE.Vector2(),secili=null;
function sec(x,y){nk.set(x/sahneEl.clientWidth*2-1,-(y/sahneEl.clientHeight)*2+1);isin.setFromCamera(nk,cam);
  var h=isin.intersectObjects(secilebilir.filter(function(m){return m.visible;}),false);
  if(secili){secili.material.emissive.setHex(0);secili=null;}
  if(h.length){secili=h[0].object;secili.material.emissive.setHex(0x0d5a63);var d=secili.userData;document.getElementById('b1').textContent=d.b||d.ad;document.getElementById('b2').textContent='IFC adı: '+d.ad;}
  else{document.getElementById('b1').textContent='Bir panoya tıklayın';document.getElementById('b2').textContent='Sürükle: çevir · Tekerlek ya da iki parmak: yakınlaştır · Sağ tuş ya da Shift + sürükle: kaydır';}
  ciz();}

/* düğmeler */
function dugme(id,acik){var b=document.getElementById(id);if(b.hasAttribute('aria-pressed'))b.setAttribute('aria-pressed',acik?'true':'false');}
function katmanDugmesi(id,liste){var acik=true;document.getElementById(id).addEventListener('click',function(){acik=!acik;liste.forEach(function(m){m.visible=acik;});dugme(id,acik);if(secili&&!secili.visible){secili.material.emissive.setHex(0);secili=null;}ciz();});}
katmanDugmesi('k-cati',katman.cati);katmanDugmesi('k-makas',katman.makas);katmanDugmesi('k-ic',katman.ic);
document.getElementById('k-ad').addEventListener('click',function(){etk.hidden=!etk.hidden;dugme('k-ad',!etk.hidden);ciz();});
function bak(az,el){K.az=az;K.el=el;K.uz=ilk.uz;K.h.set(ilk.hx,ilk.hy,ilk.hz);don=false;dugme('g-don',false);ciz();}
var P=Math.PI;
document.getElementById('g-3b').addEventListener('click',function(){bak(ilk.az,ilk.el);});
document.getElementById('g-sifir').addEventListener('click',function(){bak(ilk.az,ilk.el);});
document.getElementById('g-on').addEventListener('click',function(){bak(0,0.12);});
document.getElementById('g-arka').addEventListener('click',function(){bak(P,0.12);});
document.getElementById('g-sag').addEventListener('click',function(){bak(P/2,0.12);});
document.getElementById('g-sol').addEventListener('click',function(){bak(-P/2,0.12);});
document.getElementById('g-ust').addEventListener('click',function(){bak(0,1.5607);});
document.getElementById('g-yakin').addEventListener('click',function(){K.uz*=0.8;ciz();});
document.getElementById('g-uzak').addEventListener('click',function(){K.uz*=1.25;ciz();});
document.getElementById('g-don').addEventListener('click',function(){don=!don;dugme('g-don',don);if(don)cevir();});
var azalt=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function cevir(){if(!don)return;K.az+=azalt?0.02:0.006;ciz();requestAnimationFrame(cevir);}
tema();boyut();
window.__portman3b={K:K,ciz:ciz,katman:katman};
})();
"""

THREE_CDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'


def sayfalar(m: dict, baslik: str, kisa_ad: str) -> tuple[str, str]:
    """(kendi başına açılan HTML, yayımlanacak sayfa parçası)."""
    govde = GOVDE.replace("__BASLIK__", html.escape(baslik))
    kod = KOD.replace("__MODEL__", json.dumps(m, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
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
    g = md["girdi"]
    baslik = f"{ie.get('talep', {}).get('musteri_adi', '')} · {g['x']:g} × {g['y']:g} cm · {no} r{rev:02d}"
    tek, parca = sayfalar(m, baslik, f"3+1 Pano Modeli {g['x']:g}×{g['y']:g}")
    y1 = hedef / f"Portman_{no}_r{rev:02d}_3B.html"; y2 = hedef / f"Portman_{no}_r{rev:02d}_3B_yayin.html"
    y1.write_text(tek, encoding="utf-8"); y2.write_text(parca, encoding="utf-8")
    from collections import Counter
    return {"html": str(y1), "yayin": str(y2), "bayt": [y1.stat().st_size, y2.stat().st_size], "parca": dict(Counter(e["g"] for e in m["el"])), "mahal": len(m["mahal"]),
            "etiketli_pano": sum(1 for e in m["el"] if e["g"] in ("dis_pano", "ic_pano") and e["b"].split(" · ")[0])}


if __name__ == "__main__":
    yol = Path(sys.argv[1]) if len(sys.argv) > 1 else BURASI / "is_emri_3arti1_1150x1050.json"
    if not yol.is_absolute() and not yol.exists():
        yol = BURASI / yol
    print(json.dumps(uret(yol), ensure_ascii=False, indent=1))
