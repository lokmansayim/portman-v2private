import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
root=Path.cwd();out=root/'outputs/P9401_Cati_Alternatifleri';work=root/'work/p9401_cati';key=sys.argv[sys.argv.index('--')+1];d=json.loads((work/(key+'_selected.json')).read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(root/'outputs/Uc_Model_Sunum/P9401/P9401_inceleme.blend'));bpy.context.preferences.filepaths.save_version=0
sc=bpy.context.scene;sc.frame_set(300);roof=bpy.data.collections['CATI_AC_KAPAT'];roof.hide_render=(key!='A');roof.hide_viewport=(key!='A')
# Preview-only neutral palette to compare roof forms. Original files remain intact.
for ob in bpy.data.objects:
 if 'skp_node' not in ob:continue
 for slot in ob.material_slots:
  old=slot.material
  if old is None:continue
  mat=old.copy();slot.material=mat;mat['source_material']=old.name;mat['purpose']='Karşılaştırma için nötr görünüm; ürün rengi onayı değil'
  if not mat.use_nodes:mat.use_nodes=True
  p=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if p and not p.inputs['Base Color'].is_linked:
   color=p.inputs['Base Color'].default_value[:]
   if ob.get('roof'):p.inputs['Base Color'].default_value=(.12,.15,.17,1)
   elif max(color[:3])-min(color[:3])>.12:p.inputs['Base Color'].default_value=(.76,.77,.72,1)
prop=bpy.data.collections.new('CATI_ONERISI_'+key);sc.collection.children.link(prop)
mats={}
for k,m in d['materials'].items():
 if k not in ['roof','wall','edge']:continue
 mat=bpy.data.materials.new(m['name']);mat.use_nodes=True;p=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None);p.inputs['Base Color'].default_value=m['color'];p.inputs['Roughness'].default_value=.65;mats[k]=mat
for n in d['nodes']:
 if not n.get('proposal'):continue
 g=d['meshes'][n['geometry']];me=bpy.data.meshes.new(n['geometry']);me.from_pydata(g['vertices'],[],g['triangles']);me.update();me.materials.append(mats[n['material']]);ob=bpy.data.objects.new(n['name'],me);prop.objects.link(ob);ob['roof']=True;ob['proposal']=True;ob['variant']=key;ob['revision']=d['revision'];ob['technical_acceptance']='pending';ob['proposal_id']=n['id']
sc['model']='P9401';sc['revision']=d['revision'];sc['scope']='Modele özgü çatı tasarım önerisi; kaynak geometri ölçü onayı değildir';sc['display_palette']='Nötr karşılaştırma rengi'
f=Vector((5.12,4.1,1.9));cam=sc.camera;cam.location=f+Vector((17,-23,14));cam.rotation_euler=(f-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=18.5
sc.render.resolution_x=1500;sc.render.resolution_y=1050;sc.render.resolution_percentage=100;sc.cycles.samples=32;sc.render.filepath=str(out/key/'dis_gorunus.png');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/key/f'P9401_Cati_{key}.blend'));bpy.ops.render.render(write_still=True)
# Verify unchanged base source vertices, independently of the proposal roof.
original=json.loads((root/'work/skp_import/P9401/scene.json').read_text());maxerr=0.;count=0
for ob in bpy.data.objects:
 node=ob.get('skp_node')
 if node is None or ob.get('roof'):continue
 n=original['nodes'][node];g=original['meshes'][n['geometry']];t=n['world_transform'];assert len(g['vertices'])==len(ob.data.vertices)
 for p,v in zip(g['vertices'],ob.data.vertices):
  expected=[sum(t[c*4+r]*p[c] for c in range(3))+t[12+r]*.0254 for r in range(3)];actual=ob.matrix_world@v.co;maxerr=max(maxerr,max(abs(expected[i]-actual[i]) for i in range(3)));count+=1
report={'variant':key,'source_body_vertices_checked':count,'max_delta_m':maxerr,'passed':maxerr<1e-5,'source_body_changed':False};(out/key/'govde_kontrol.json').write_text(json.dumps(report,indent=2));assert report['passed'];print(report)
