"""İE-04 · Basit 3D sayfası: IFC → tek dosyalık statik HTML görüntüleyici (three.js r128 gömülü; dış ağ yok). Aynı revizyonun IFC'sinden üretilir.

Sayfa sunucu kodu çalıştırmaz; üçgenlenmiş geometri JSON olarak dosyanın içindedir. Odalara dokununca ad ve net alan görünür.
Barınak (hosting'te statik sayfa ya da VPS) canlı karardır; bu modül yalnız dosyayı üretir.
"""
from __future__ import annotations
import html, json
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue

RENK = {"IfcWall": [0.86, 0.86, 0.84], "IfcWindow": [0.45, 0.70, 0.92], "IfcDoor": [0.62, 0.45, 0.28], "IfcSlab": [0.55, 0.30, 0.25],
        "IfcRoof": [0.55, 0.30, 0.25], "IfcSpace": [0.95, 0.85, 0.55], "IfcColumn": [0.40, 0.35, 0.30], "IfcBeam": [0.40, 0.35, 0.30],
        "IfcMember": [0.60, 0.55, 0.45], "IfcPlate": [0.80, 0.78, 0.72]}
ATLA = {"IfcOpeningElement", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcProject"}

SAYFA = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__BASLIK__ · 3D</title>
<style>html,body{margin:0;height:100%;background:#f4f2ee;font-family:system-ui,sans-serif}#c{width:100%;height:100%;display:block;touch-action:none}
#u{position:fixed;left:12px;top:12px;background:rgba(255,255,255,.92);padding:10px 12px;border-radius:10px;font-size:14px;max-width:80vw;box-shadow:0 2px 8px rgba(0,0,0,.12)}
#u b{display:block;font-size:15px}#u small{color:#666}#b{position:fixed;right:12px;top:12px;display:flex;gap:6px}
#b button{border:0;background:#fff;border-radius:8px;padding:8px 10px;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,.12)}</style></head>
<body><canvas id="c"></canvas><div id="u"><b>__BASLIK__</b><span id="s">Bir odaya dokunun</span><br><small>Şematik model · ölçüler planla aynı · üretim çizimi değildir</small></div>
<div id="b"><button id="cati">Çatı gizle</button><button id="ust">Üstten</button></div>
<script>__THREE__</script>
<script>__ORBIT__</script>
<script>
const M=__MODEL__;
const cv=document.getElementById('c'),r=new THREE.WebGLRenderer({canvas:cv,antialias:true});r.setPixelRatio(window.devicePixelRatio||1);
const sc=new THREE.Scene();sc.background=new THREE.Color(0xf4f2ee);
const cam=new THREE.PerspectiveCamera(50,1,0.05,500);const ctl=new THREE.OrbitControls(cam,cv);ctl.enableDamping=true;
sc.add(new THREE.HemisphereLight(0xffffff,0x9a8f7a,0.9));const dl=new THREE.DirectionalLight(0xffffff,0.6);dl.position.set(5,10,7);sc.add(dl);
const grp=new THREE.Group();sc.add(grp);const odalar=[],catilar=[];const bb=new THREE.Box3();
for(const e of M.elemanlar){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(e.v,3));g.setIndex(e.i);g.computeVertexNormals();
 const oda=e.sinif==='IfcSpace';const mat=new THREE.MeshLambertMaterial({color:new THREE.Color(...e.renk),transparent:oda||e.sinif==='IfcWindow',opacity:oda?0.25:(e.sinif==='IfcWindow'?0.55:1),side:THREE.DoubleSide});
 const m=new THREE.Mesh(g,mat);m.userData=e;grp.add(m);if(oda)odalar.push(m);if(e.sinif==='IfcRoof'||e.sinif==='IfcPlate'||e.sinif==='IfcMember')catilar.push(m);bb.expandByObject(m);
 if(!oda){const ed=new THREE.LineSegments(new THREE.EdgesGeometry(g,20),new THREE.LineBasicMaterial({color:0x333333,transparent:true,opacity:0.35}));m.add(ed);}}
const c=bb.getCenter(new THREE.Vector3()),sz=bb.getSize(new THREE.Vector3());ctl.target.copy(c);
function bak(ust){if(ust){cam.position.set(c.x,c.y+Math.max(sz.x,sz.z)*1.6,c.z+0.01);}else{cam.position.set(c.x+sz.x*1.1,c.y+sz.y*1.6,c.z+sz.z*1.3);}cam.lookAt(c);}bak(false);
function boyut(){const w=cv.clientWidth,h=cv.clientHeight;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();}window.addEventListener('resize',boyut);boyut();
const ray=new THREE.Raycaster(),pt=new THREE.Vector2();let secili=null;
function sec(x,y){pt.x=(x/cv.clientWidth)*2-1;pt.y=-(y/cv.clientHeight)*2+1;ray.setFromCamera(pt,cam);const h=ray.intersectObjects(odalar,false);
 if(secili){secili.material.opacity=0.25;}if(h.length){secili=h[0].object;secili.material.opacity=0.6;const d=secili.userData;document.getElementById('s').textContent=d.ad+(d.alan?(' · '+d.alan+' m²'):'');}}
let sx=0,sy=0;cv.addEventListener('pointerdown',e=>{sx=e.clientX;sy=e.clientY;});cv.addEventListener('pointerup',e=>{if(Math.hypot(e.clientX-sx,e.clientY-sy)<6)sec(e.clientX,e.clientY);});
let catiAcik=true;document.getElementById('cati').onclick=()=>{catiAcik=!catiAcik;for(const m of catilar)m.visible=catiAcik;document.getElementById('cati').textContent=catiAcik?'Çatı gizle':'Çatı göster';};
document.getElementById('ust').onclick=()=>bak(true);
(function an(){requestAnimationFrame(an);ctl.update();r.render(sc,cam);})();
</script></body></html>
"""


def model_json(ifc_yolu: Path) -> dict:
    """IFC → üçgen ağlar (metre; y yukarı olacak biçimde eksen çevrilir). Odalar ad ve net alanla."""
    f = ifcopenshell.open(str(ifc_yolu))
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    elemanlar = []
    for e in f.by_type("IfcProduct"):
        if e.is_a() in ATLA or not e.Representation:
            continue
        try:
            sh = ifcopenshell.geom.create_shape(s, e)
        except Exception:
            continue
        v = list(sh.geometry.verts); i = list(sh.geometry.faces)
        if not v or not i:
            continue
        # IFC: z yukarı → three.js: y yukarı (x, z, -y)
        vy = []
        for k in range(0, len(v), 3):
            vy += [round(v[k], 4), round(v[k + 2], 4), round(-v[k + 1], 4)]
        sinif = e.is_a()
        ad = (getattr(e, "LongName", None) or e.Name or sinif) if sinif == "IfcSpace" else (e.Name or sinif)
        kayit = {"sinif": sinif, "ad": ad, "renk": RENK.get(sinif, [0.7, 0.7, 0.7]), "v": vy, "i": i}
        if sinif == "IfcSpace":
            q = (ue.get_psets(e) or {}).get("Qto_SpaceBaseQuantities") or {}
            alan = q.get("NetFloorArea")
            kayit["alan"] = round(float(alan), 1) if alan is not None else None
        elemanlar.append(kayit)
    return {"kaynak": ifc_yolu.name, "elemanlar": elemanlar}


def uret(ifc_yolu: Path, html_yolu: Path, baslik: str = "") -> Path:
    m = model_json(Path(ifc_yolu))
    vendor = Path(__file__).resolve().parent / "vendor"
    sayfa = (SAYFA.replace("__BASLIK__", html.escape(baslik or Path(ifc_yolu).stem))
             .replace("__THREE__", (vendor / "three.min.js").read_text(encoding="utf-8").replace("</script", "<\\/script"))
             .replace("__ORBIT__", (vendor / "OrbitControls.js").read_text(encoding="utf-8").replace("</script", "<\\/script"))
             .replace("__MODEL__", json.dumps(m, separators=(",", ":")).replace("</", "<\\/")))
    html_yolu = Path(html_yolu); html_yolu.parent.mkdir(parents=True, exist_ok=True)
    html_yolu.write_text(sayfa, encoding="utf-8")
    return html_yolu
