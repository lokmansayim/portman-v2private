from pathlib import Path
import json, ctypes as C, collections
p=Path('work/skp_import/read_skp.py').resolve()
ns={'__file__':str(p)}
exec(compile(p.read_text().split('\nlib.SUInitialize()')[0],str(p),'exec'),ns)
globals().update(ns)
bind('SUFaceGetNormal',[Ref,C.POINTER(Pt)])
bind('SUFaceGetArea',[Ref,C.POINTER(C.c_double)])
lib.SUInitialize()
model=Ref(); source=json.loads(Path('work/skp_import/P9501/scene.json').read_text())['source']
ok(lib.SUModelCreateFromFile(C.byref(model),source.encode())); ent=Ref(); ok(lib.SUModelGetEntities(model,C.byref(ent)))
visited=set(); faces={}
def info(m):
 if not m.ptr:return None
 color=Color();lib.SUMaterialGetColor(m,C.byref(color))
 return {'name':string('SUMaterialGetName',m),'color':[color.r,color.g,color.b,color.a]}
def walk(e):
 if e.ptr in visited:return
 visited.add(e.ptr)
 for f in refs(e,'Faces'):
  fm=Ref();bm=Ref();lib.SUFaceGetFrontMaterial(f,C.byref(fm));lib.SUFaceGetBackMaterial(f,C.byref(bm));n=Pt();lib.SUFaceGetNormal(f,C.byref(n));a=C.c_double();lib.SUFaceGetArea(f,C.byref(a))
  pid=identity(lib.SUFaceToEntity(f));faces[pid]={'front':info(fm),'back':info(bm),'normal':[n.x,n.y,n.z],'local_area_m2':a.value*.0254**2}
 for kind,pre in [('Groups','SUGroup'),('Instances','SUComponentInstance')]:
  for ref in refs(e,kind):
   definition=Ref();ok(getattr(lib,pre+'GetDefinition')(ref,C.byref(definition)));child=Ref();ok(lib.SUComponentDefinitionGetEntities(definition,C.byref(child)));walk(child)
walk(ent)
Path('work/roof_qa/face_materials.json').write_text(json.dumps(faces))
print('faces',len(faces),'different front/back',sum(x['front']!=x['back'] for x in faces.values()))
print('cyan faces',sum((x['front']or{}).get('name')=='[Color H02]' for x in faces.values()))
for pid,x in faces.items():
 if (x['front']or{}).get('name')=='[Color H02]' and x['local_area_m2']>1:print(pid,x)
lib.SUModelRelease(C.byref(model));lib.SUTerminate()
