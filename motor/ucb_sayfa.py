"""İE-04 · Basit 3D sayfası: IFC → tek dosyalık statik HTML görüntüleyici (three.js r128 gömülü; dış ağ yok). Aynı revizyonun IFC'sinden üretilir.

Sayfa sunucu kodu çalıştırmaz; üçgenlenmiş geometri JSON olarak dosyanın içindedir. Odalara dokununca ad ve net alan görünür.
Barınak: VPS'te nginx `/3d/<anahtar>/` (İE-21; `kanal/ucb_yayin.py`); bu modül yalnız dosyayı üretir.
İE-21 (27 Ekim 2026): renkler IFC'nin yüzey malzemesinden (yüz yüz; antrasit çatı, cam saydam); "Çatıyı aç" örtüyü, alını, kalkanı,
makası ve tavanı gizler (örtü IfcSlab ROOF olduğu için eski sayfa gizlemiyordu); kamera evi ekran oranına göre sığdırır (telefon dikey);
düğmeler altta, en az 44 px. Prefabrik (pano Motor'u) ve çelik (genel motor) IFC'si aynı sayfayı verir.
"""
from __future__ import annotations
import html, json, re
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue

RENK = {"IfcWall": [0.86, 0.86, 0.84], "IfcWindow": [0.45, 0.70, 0.92], "IfcDoor": [0.62, 0.45, 0.28], "IfcSlab": [0.55, 0.30, 0.25],
        "IfcRoof": [0.55, 0.30, 0.25], "IfcSpace": [0.95, 0.85, 0.55], "IfcColumn": [0.40, 0.35, 0.30], "IfcBeam": [0.40, 0.35, 0.30],
        "IfcMember": [0.60, 0.55, 0.45], "IfcPlate": [0.80, 0.78, 0.72]}      # IFC'de malzeme yoksa
ATLA = {"IfcOpeningElement", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcProject"}
CATI_ADI = re.compile(r"^(VERANDA_)?(CATI|ALIN|KALKAN|MAKAS)")   # iki motorun çatı parçası adları (ifc_uret, genel/ifc_genel); VERANDA_KIRIS_ALIN_* kiriştir

SAYFA = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__BASLIK__ · 3D</title>
<style>html,body{margin:0;height:100%;background:#f4f2ee;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d1b16;overflow:hidden}
#c{width:100%;height:100%;display:block;touch-action:none}
#u{position:fixed;left:12px;right:12px;top:calc(12px + env(safe-area-inset-top));background:rgba(255,255,255,.92);padding:10px 12px;border-radius:12px;font-size:14px;line-height:1.35;box-shadow:0 2px 8px rgba(0,0,0,.12);pointer-events:none}
#u b{display:block;font-size:16px}#s{display:block;margin-top:2px}#u small{display:block;color:#5e594f;margin-top:2px}
#b{position:fixed;left:0;right:0;bottom:0;display:flex;gap:8px;justify-content:center;padding:10px 12px calc(12px + env(safe-area-inset-bottom))}
#b button{flex:1 1 0;max-width:150px;min-height:44px;padding:0 4px;white-space:nowrap;border:0;background:#fff;color:#1d1b16;border-radius:10px;font:inherit;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.14)}
#b button[aria-pressed="true"]{background:#22211d;color:#fff}
#b #cati{flex-grow:1.4}
#hata{position:fixed;left:12px;right:12px;top:45%;background:#fff;padding:14px;border-radius:12px;font-size:15px;box-shadow:0 2px 8px rgba(0,0,0,.14)}</style></head>
<body><canvas id="c" aria-label="Parmakla çevrilebilen 3D model"></canvas>
<div id="u"><b>__BASLIK__</b><span id="s">Bir odaya dokunun</span><small>Tek parmakla çevirin · iki parmakla yaklaştırın</small><small>Şematik model · ölçüler planla aynı · üretim çizimi değildir</small></div>
<div id="b"><button id="cati" aria-pressed="false">Çatıyı aç</button><button id="ust">Üstten</button><button id="dis">Dışarıdan</button><button id="don" aria-pressed="false">Döndür</button></div>
<div id="hata" hidden>Bu tarayıcı 3D çizimi açamadı. Bağlantıyı Chrome ya da Safari'de açın.</div>
<script>__THREE__</script>
<script>__ORBIT__</script>
<script>
const M=__MODEL__;
const cv=document.getElementById('c');let r;
try{r=new THREE.WebGLRenderer({canvas:cv,antialias:true});}catch(e){document.getElementById('hata').hidden=false;document.getElementById('b').hidden=true;throw e;}
r.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
const sc=new THREE.Scene();sc.background=new THREE.Color(0xf4f2ee);
const cam=new THREE.PerspectiveCamera(45,1,0.05,500);const ctl=new THREE.OrbitControls(cam,cv);ctl.enableDamping=true;ctl.autoRotateSpeed=1.5;
sc.add(new THREE.HemisphereLight(0xffffff,0x9a8f7a,0.85));const dl=new THREE.DirectionalLight(0xffffff,0.65);dl.position.set(5,10,7);sc.add(dl);
const grp=new THREE.Group();sc.add(grp);const odalar=[],catilar=[];const bb=new THREE.Box3();
for(const e of M.elemanlar){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(e.v,3));g.setIndex(e.i);g.computeVertexNormals();
 const oda=e.sinif==='IfcSpace';
 const mats=e.m.map(([cr,cg,cb,a])=>new THREE.MeshLambertMaterial({color:new THREE.Color(cr,cg,cb),transparent:oda||a<1,opacity:oda?0.22:a,depthWrite:!oda&&a>=1,side:THREE.DoubleSide}));
 for(const [s,n,k] of e.g)g.addGroup(s,n,k);
 const m=new THREE.Mesh(g,mats.length>1?mats:mats[0]);m.userData=e;grp.add(m);if(oda)odalar.push(m);if(e.cati)catilar.push(m);if(!oda)bb.expandByObject(m);
 if(!oda&&e.m.every(x=>x[3]>=1)){const ed=new THREE.LineSegments(new THREE.EdgesGeometry(g,20),new THREE.LineBasicMaterial({color:0x333333,transparent:true,opacity:0.3}));m.add(ed);}}
if(bb.isEmpty())for(const m of odalar)bb.expandByObject(m);
const c=bb.getCenter(new THREE.Vector3()),sz=bb.getSize(new THREE.Vector3()),R=Math.max(sz.length()/2,0.5);
const DIS=new THREE.Vector3(sz.x*1.1,sz.y*1.6,sz.z*1.3),UST=new THREE.Vector3(0,1,0.001);let yon=DIS;
function bak(v){yon=v;const vf=cam.fov*Math.PI/180,hf=2*Math.atan(Math.tan(vf/2)*cam.aspect),d=R/Math.sin(Math.min(vf,hf)/2)*1.05;
 cam.position.copy(c).add(v.clone().normalize().multiplyScalar(d));cam.near=d/200;cam.far=d*20;cam.updateProjectionMatrix();ctl.target.copy(c);ctl.update();}
function boyut(){const w=cv.clientWidth,h=cv.clientHeight;r.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();}
let elle=false;   // bayi çevirdi ya da yaklaştırdıysa ekran boyu değişince (araç çubuğu, yön) görünüşü sıfırlama
window.addEventListener('resize',()=>{boyut();if(!elle)bak(yon);});boyut();bak(DIS);
const ray=new THREE.Raycaster(),pt=new THREE.Vector2();let secili=null;
function sec(x,y){pt.x=(x/cv.clientWidth)*2-1;pt.y=-(y/cv.clientHeight)*2+1;ray.setFromCamera(pt,cam);const h=ray.intersectObjects(odalar,false);
 if(secili){secili.material.opacity=0.22;}if(h.length){secili=h[0].object;secili.material.opacity=0.55;const d=secili.userData;document.getElementById('s').textContent=d.ad+(d.alan?(' · '+String(d.alan).replace('.',',')+' m²'):'');}}
let sx=0,sy=0;cv.addEventListener('pointerdown',e=>{sx=e.clientX;sy=e.clientY;});cv.addEventListener('pointerup',e=>{if(Math.hypot(e.clientX-sx,e.clientY-sy)<6)sec(e.clientX,e.clientY);});
const bc=document.getElementById('cati'),bd=document.getElementById('don');
bc.onclick=()=>{const acik=bc.getAttribute('aria-pressed')!=='true';for(const m of catilar)m.visible=!acik;bc.setAttribute('aria-pressed',String(acik));bc.textContent=acik?'Çatıyı kapat':'Çatıyı aç';};
document.getElementById('ust').onclick=()=>{elle=false;bak(UST);};document.getElementById('dis').onclick=()=>{elle=false;bak(DIS);};
function don(a){ctl.autoRotate=a;bd.setAttribute('aria-pressed',String(a));bd.textContent=a?'Durdur':'Döndür';}
bd.onclick=()=>don(!ctl.autoRotate);ctl.addEventListener('start',()=>{elle=true;if(ctl.autoRotate)don(false);});
(function an(){requestAnimationFrame(an);ctl.update();r.render(sc,cam);})();
</script></body></html>
"""


def _cati_mi(e) -> bool:
    """Çatı parçası mı ("Çatıyı aç" gizler): çatı tipli döşeme (örtü), tavan, IfcRoof ya da makas topluluğunun parçası, ya da iki motorun
    çatı adları (CATI, ALIN, KALKAN, MAKAS)."""
    tip = str(getattr(e, "PredefinedType", "") or "")
    if (e.is_a("IfcSlab") and tip == "ROOF") or (e.is_a("IfcCovering") and tip == "CEILING") or e.is_a("IfcRoof"):
        return True
    a = ue.get_aggregate(e)
    while a is not None:
        if a.is_a("IfcRoof") or (a.is_a("IfcElementAssembly") and str(getattr(a, "PredefinedType", "") or "") == "TRUSS"):
            return True
        a = ue.get_aggregate(a)
    return bool(CATI_ADI.search((e.Name or "").upper()))


def _renkler(sinif: str, geo, n_ucgen: int, i: list) -> tuple[list, list, list]:
    """Yüz yüz IFC malzemesi → ([[r, g, b, opaklık], …], gruplar [[başlangıç, adet, malzeme], …], malzemeye göre dizilmiş üçgenler).
    Malzeme yoksa ya da yüz sayısı tutmazsa sınıf rengi (RENK), tek grup."""
    mats, ids = list(geo.materials or []), list(geo.material_ids or [])
    if not mats or len(ids) != n_ucgen or sinif == "IfcSpace":
        return [RENK.get(sinif, [0.7, 0.7, 0.7]) + [1.0]], [[0, len(i), 0]], i
    if any(not 0 <= k < len(mats) for k in ids):             # biçemsiz yüz (-1): sınıf rengi, yüz kaybolmasın
        ids = [k if 0 <= k < len(mats) else len(mats) for k in ids]
        mats = mats + [None]
    renk = []
    for m in mats:
        if m is None:
            renk.append(RENK.get(sinif, [0.7, 0.7, 0.7]) + [1.0]); continue
        t = getattr(m, "transparency", 0.0)
        t = 0.0 if t is None or t != t else float(t)          # NaN: saydamlık yazılmamış
        renk.append([round(x, 3) for x in m.diffuse.components[:3]] + [round(max(0.0, min(1.0, 1.0 - t)), 2)])
    sira = sorted(range(n_ucgen), key=lambda k: ids[k])
    yeni, gruplar = [], []
    for k in sira:
        if not gruplar or gruplar[-1][2] != ids[k]:
            gruplar.append([len(yeni), 0, ids[k]])
        yeni += i[3 * k:3 * k + 3]
        gruplar[-1][1] += 3
    return renk, gruplar, yeni


def model_json(ifc_yolu: Path) -> dict:
    """IFC → üçgen ağlar (metre; y yukarı olacak biçimde eksen çevrilir). Odalar ad ve net alanla; renk IFC malzemesinden."""
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
        renk, gruplar, i = _renkler(sinif, sh.geometry, len(i) // 3, i)
        kayit = {"sinif": sinif, "ad": ad, "m": renk, "g": gruplar, "v": vy, "i": i}
        if sinif != "IfcSpace" and _cati_mi(e):
            kayit["cati"] = True
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
