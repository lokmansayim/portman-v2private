import ctypes as C,json,sys,hashlib
from pathlib import Path
class Ref(C.Structure):_fields_=[('ptr',C.c_void_p)]
class Pt(C.Structure):_fields_=[('x',C.c_double),('y',C.c_double),('z',C.c_double)]
class Box(C.Structure):_fields_=[('min',Pt),('max',Pt)]
class Transform(C.Structure):_fields_=[('values',C.c_double*16)]
class Color(C.Structure):_fields_=[('r',C.c_ubyte),('g',C.c_ubyte),('b',C.c_ubyte),('a',C.c_ubyte)]
R=C.POINTER(Ref); SZ=C.c_size_t; PS=C.POINTER(SZ)
lib=C.CDLL(str(Path(__file__).parent/'package/sketchup_importer/SketchUpAPI.framework/Versions/A/SketchUpAPI'))
def bind(name,args,ret=C.c_int):
 f=getattr(lib,name);f.argtypes=args;f.restype=ret;return f
bind('SUInitialize',[],None);bind('SUTerminate',[],None)
bind('SUModelCreateFromFile',[R,C.c_char_p]);bind('SUModelGetEntities',[Ref,R]);bind('SUModelRelease',[R])
bind('SUStringCreate',[R]);bind('SUStringGetUTF8Length',[Ref,PS]);bind('SUStringGetUTF8',[Ref,SZ,C.c_char_p,PS]);bind('SUStringRelease',[R])
for pre in ['SUGroup','SUComponentInstance']:
 bind(pre+'ToEntity',[Ref],Ref);bind(pre+'ToDrawingElement',[Ref],Ref)
 bind(pre+'GetName',[Ref,R]);bind(pre+'GetTransform',[Ref,C.POINTER(Transform)]);bind(pre+'GetDefinition',[Ref,R])
bind('SUGroupGetEntities',[Ref,R]);bind('SUComponentDefinitionGetEntities',[Ref,R]);bind('SUComponentDefinitionGetName',[Ref,R])
bind('SUEntityGetID',[Ref,C.POINTER(C.c_int32)]);bind('SUEntityGetPersistentID',[Ref,C.POINTER(C.c_int64)])
for suffix in ['Groups','Instances','Faces']:
 bind('SUEntitiesGetNum'+suffix,[Ref,PS]);bind('SUEntitiesGet'+suffix,[Ref,SZ,R,PS])
for suffix in ['Hidden'] :bind('SUDrawingElementGet'+suffix,[Ref,C.POINTER(C.c_bool)])
bind('SUDrawingElementGetLayer',[Ref,R]);bind('SULayerGetName',[Ref,R]);bind('SULayerGetVisibility',[Ref,C.POINTER(C.c_bool)])
bind('SUDrawingElementGetMaterial',[Ref,R]);bind('SUDrawingElementGetBoundingBox',[Ref,C.POINTER(Box)])
for typ in ['SUFaceToDrawingElement','SUFaceToEntity']:bind(typ,[Ref],Ref)
bind('SUFaceGetFrontMaterial',[Ref,R]);bind('SUFaceGetBackMaterial',[Ref,R])
bind('SUMeshHelperCreate',[R,Ref]);bind('SUMeshHelperRelease',[R])
for s in ['Triangles','Vertices']:bind('SUMeshHelperGetNum'+s,[Ref,PS])
bind('SUMeshHelperGetVertices',[Ref,SZ,C.POINTER(Pt),PS]);bind('SUMeshHelperGetFrontSTQCoords',[Ref,SZ,C.POINTER(Pt),PS]);bind('SUMeshHelperGetVertexIndices',[Ref,SZ,PS,PS])
bind('SUMaterialGetName',[Ref,R]);bind('SUMaterialGetColor',[Ref,C.POINTER(Color)]);bind('SUMaterialGetOpacity',[Ref,C.POINTER(C.c_double)]);bind('SUMaterialGetTexture',[Ref,R]);bind('SUTextureWriteToFile',[Ref,C.c_char_p])

def ok(code):
 if code:raise RuntimeError(code)
def string(fn,ref):
 s=Ref();ok(lib.SUStringCreate(C.byref(s)))
 try:
  if getattr(lib,fn)(ref,C.byref(s)):return ''
  n=SZ();ok(lib.SUStringGetUTF8Length(s,C.byref(n)));buf=C.create_string_buffer(n.value+1);got=SZ();ok(lib.SUStringGetUTF8(s,n.value+1,buf,C.byref(got)));return buf.value.decode('utf8',errors='replace')
 finally:lib.SUStringRelease(C.byref(s))
def refs(entity,kind):
 n=SZ();ok(getattr(lib,'SUEntitiesGetNum'+kind)(entity,C.byref(n)));a=(Ref*n.value)();got=SZ()
 if n.value:ok(getattr(lib,'SUEntitiesGet'+kind)(entity,n.value,a,C.byref(got)))
 return list(a)[:got.value]
def state(draw):
 h=C.c_bool();lib.SUDrawingElementGetHidden(draw,C.byref(h));layer=Ref();lib.SUDrawingElementGetLayer(draw,C.byref(layer));v=C.c_bool(True);lib.SULayerGetVisibility(layer,C.byref(v));return h.value or not v.value,string('SULayerGetName',layer)
def identity(ref):
 p=C.c_int64();lib.SUEntityGetPersistentID(ref,C.byref(p));return p.value
I=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
def mm(a,b):return [sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4)]
def tp(p,t):return [(t[r]*p.x+t[4+r]*p.y+t[8+r]*p.z+t[12+r])*0.0254 for r in range(3)]
def run(path,out,mesh=False):
 out.mkdir(parents=True,exist_ok=True);(out/'textures').mkdir(exist_ok=True)
 model=Ref();ok(lib.SUModelCreateFromFile(C.byref(model),str(path).encode()));ent=Ref();ok(lib.SUModelGetEntities(model,C.byref(ent)))
 nodes=[];meshes={};materials={};stats={'faces':0,'triangles':0,'errors':[]}
 def mat(ref):
  if not ref.ptr:return None
  key=str(ref.ptr)
  if key in materials:return key
  color=Color(200,200,200,255);lib.SUMaterialGetColor(ref,C.byref(color));a=C.c_double(1);lib.SUMaterialGetOpacity(ref,C.byref(a))
  name=string('SUMaterialGetName',ref);tex=Ref();texture=None
  if lib.SUMaterialGetTexture(ref,C.byref(tex))==0 and tex.ptr:
   target=out/'textures'/f'{len(materials):03}.png'
   if lib.SUTextureWriteToFile(tex,str(target).encode())==0:texture=str(target.resolve())
  materials[key]={'name':name,'color':[color.r/255,color.g/255,color.b/255,a.value],'texture':texture}
  return key
 def walk(e,parent,transform,depth=0,inherited_mat=None):
  if depth>30:raise RuntimeError('recursion')
  faces=refs(e,'Faces');geomkey=str(e.ptr)
  if mesh and geomkey not in meshes:
   verts=[];tris=[];uv=[];fm=[];ids=[]
   for f in faces:
    draw=lib.SUFaceToDrawingElement(f)
    hidden,layer=state(draw)
    if hidden:continue
    helper=Ref();err=lib.SUMeshHelperCreate(C.byref(helper),f)
    if err:stats['errors'].append({'face':identity(lib.SUFaceToEntity(f)),'error':err});continue
    nv=SZ();nt=SZ();lib.SUMeshHelperGetNumVertices(helper,C.byref(nv));lib.SUMeshHelperGetNumTriangles(helper,C.byref(nt));vs=(Pt*nv.value)();st=(Pt*nv.value)();ix=(SZ*(nt.value*3))();got=SZ()
    ok(lib.SUMeshHelperGetVertices(helper,nv,vs,C.byref(got)));ok(lib.SUMeshHelperGetVertexIndices(helper,nt.value*3,ix,C.byref(got)));lib.SUMeshHelperGetFrontSTQCoords(helper,nv,st,C.byref(got))
    mr=Ref();lib.SUFaceGetFrontMaterial(f,C.byref(mr));mk=mat(mr)
    offset=len(verts);verts.extend([[p.x*.0254,p.y*.0254,p.z*.0254] for p in vs]);uv.extend([[p.x/p.z,p.y/p.z] if abs(p.z)>1e-12 else [p.x,p.y] for p in st]);tris.extend([[offset+ix[k],offset+ix[k+1],offset+ix[k+2]] for k in range(0,nt.value*3,3)]);fm.extend([mk]*nt.value);ids.extend([identity(lib.SUFaceToEntity(f))]*nt.value)
    lib.SUMeshHelperRelease(C.byref(helper));stats['faces']+=1;stats['triangles']+=nt.value
   meshes[geomkey]={'vertices':verts,'triangles':tris,'uv':uv,'materials':fm,'source_faces':ids}
  nodes[parent]['geometry']=geomkey;nodes[parent]['face_count']=len(faces)
  for kind,pre in [('Groups','SUGroup'),('Instances','SUComponentInstance')]:
   for ref in refs(e,kind):
    d=getattr(lib,pre+'ToDrawingElement')(ref);hidden,layer=state(d);t=Transform();ok(getattr(lib,pre+'GetTransform')(ref,C.byref(t)));definition=Ref();ok(getattr(lib,pre+'GetDefinition')(ref,C.byref(definition)))
    child=Ref();ok(lib.SUComponentDefinitionGetEntities(definition,C.byref(child)))
    box=Box();lib.SUDrawingElementGetBoundingBox(d,C.byref(box));name=string(pre+'GetName',ref) or string('SUComponentDefinitionGetName',definition)
    mr=Ref();lib.SUDrawingElementGetMaterial(d,C.byref(mr));mk=mat(mr) if mesh else None;mk=mk or inherited_mat
    full=mm(transform,list(t.values));full=[x/full[15] for x in full];idx=len(nodes)
    nodes.append({'id':idx,'parent':parent,'name':name,'layer':layer,'source_id':identity(getattr(lib,pre+'ToEntity')(ref)),'hidden':hidden or nodes[parent]['hidden'],'transform':list(t.values),'world_transform':full,'material':mk,'bbox_parent_inches':[[box.min.x,box.min.y,box.min.z],[box.max.x,box.max.y,box.max.z]]})
    walk(child,idx,full,depth+1,mk)
 nodes.append({'id':0,'parent':None,'name':path.stem,'hidden':False,'transform':I,'world_transform':I,'material':None})
 walk(ent,0,I)
 result={'source':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'units':'meters','source_units':'inches','conversion':.0254,'nodes':nodes,'meshes':meshes,'materials':materials,'stats':stats}
 (out/('scene.json' if mesh else 'inventory.json')).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(path.name,len(nodes),'nodes',len(meshes),'meshes',stats)
 for n in nodes:
  if n['parent']==0:print(n['id'],n['name'],n['layer'],'hidden',n['hidden'],'faces',n['face_count'],n.get('bbox_parent_inches'))
 lib.SUModelRelease(C.byref(model))
lib.SUInitialize()
try:run(Path(sys.argv[1]),Path(sys.argv[2]),'--mesh' in sys.argv)
finally:lib.SUTerminate()
