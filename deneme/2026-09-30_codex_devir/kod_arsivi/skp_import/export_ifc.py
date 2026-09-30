import sys,json,uuid,time,math
from pathlib import Path
sys.path.insert(0,str(Path('work/ifc_runtime').resolve()))
import ifcopenshell,ifcopenshell.guid,ifcopenshell.validate,ifcopenshell.geom
from mathutils import Matrix,Vector
code=sys.argv[sys.argv.index('--')+1];d=json.loads((Path('work/skp_import')/code/'selected.json').read_text(encoding='utf-8'));out=Path('outputs/Uc_Model_Sunum')/code
f=ifcopenshell.file(schema='IFC4');guid=lambda key:ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL,d['source_sha256']+'/'+code+'/'+str(key)).hex)
org=f.create_entity('IfcOrganization',Name='Portman');person=f.create_entity('IfcPerson',FamilyName='Kaynak inceleme');user=f.create_entity('IfcPersonAndOrganization',ThePerson=person,TheOrganization=org);app=f.create_entity('IfcApplication',ApplicationDeveloper=org,Version='SKP-inceleme-01',ApplicationFullName='Portman kaynak geometri aktarımı',ApplicationIdentifier='PORTMAN-SKP-REVIEW');owner=f.create_entity('IfcOwnerHistory',OwningUser=user,OwningApplication=app,ChangeAction='ADDED',CreationDate=int(time.time()))
axis=f.create_entity('IfcAxis2Placement3D',Location=f.create_entity('IfcCartesianPoint',Coordinates=(0.,0.,0.)));ctx=f.create_entity('IfcGeometricRepresentationContext',ContextType='Model',CoordinateSpaceDimension=3,Precision=1e-7,WorldCoordinateSystem=axis);body=f.create_entity('IfcGeometricRepresentationSubContext',ContextIdentifier='Body',ContextType='Model',ParentContext=ctx,TargetView='MODEL_VIEW')
units=f.create_entity('IfcUnitAssignment',Units=[f.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Name='METRE'),f.create_entity('IfcSIUnit',UnitType='AREAUNIT',Name='SQUARE_METRE'),f.create_entity('IfcSIUnit',UnitType='VOLUMEUNIT',Name='CUBIC_METRE')]);project=f.create_entity('IfcProject',GlobalId=guid('project'),OwnerHistory=owner,Name=code+' kaynak inceleme',RepresentationContexts=[ctx],UnitsInContext=units)
def local(parent=None):return f.create_entity('IfcLocalPlacement',PlacementRelTo=parent,RelativePlacement=axis)
site=f.create_entity('IfcSite',GlobalId=guid('site'),OwnerHistory=owner,Name='Kaynak konumu',ObjectPlacement=local(),CompositionType='ELEMENT');building=f.create_entity('IfcBuilding',GlobalId=guid('building'),OwnerHistory=owner,Name=code,ObjectPlacement=local(site.ObjectPlacement),CompositionType='ELEMENT');storey=f.create_entity('IfcBuildingStorey',GlobalId=guid('storey'),OwnerHistory=owner,Name='Zemin Kat',ObjectPlacement=local(building.ObjectPlacement),CompositionType='ELEMENT',Elevation=0.)
for i,(parent,child) in enumerate([(project,site),(site,building),(building,storey)]):f.create_entity('IfcRelAggregates',GlobalId=guid('rel'+str(i)),OwnerHistory=owner,RelatingObject=parent,RelatedObjects=[child])
styles={}
for k,m in d['materials'].items():
 color=f.create_entity('IfcColourRgb',Red=m['color'][0],Green=m['color'][1],Blue=m['color'][2]);shade=f.create_entity('IfcSurfaceStyleShading',SurfaceColour=color,Transparency=1-m['color'][3]);styles[k]=f.create_entity('IfcSurfaceStyle',Name=m['name'],Side='BOTH',Styles=[shade])
products=[];expected={};source_triangles=0
for n in d['nodes']:
 mesh=d['meshes'][n['geometry']];t=n['world_transform'];matrix=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)]);
 for r in range(3):matrix[r][3]*=.0254
 verts=[tuple(float(v) for v in matrix@Vector(v)) for v in mesh['vertices']];faces=mesh['triangles'];source_triangles+=len(faces);coord=f.create_entity('IfcCartesianPointList3D',CoordList=verts);bins={}
 for tri,m in zip(faces,mesh['materials']):bins.setdefault(m or n['material'],[]).append(tuple(int(i)+1 for i in tri))
 items=[]
 for mk,tris in bins.items():
  item=f.create_entity('IfcTriangulatedFaceSet',Coordinates=coord,Closed=False,CoordIndex=tris);items.append(item)
  if mk in styles:f.create_entity('IfcStyledItem',Item=item,Styles=[styles[mk]])
 rep=f.create_entity('IfcShapeRepresentation',ContextOfItems=body,RepresentationIdentifier='Body',RepresentationType='Tessellation',Items=items);shape=f.create_entity('IfcProductDefinitionShape',Representations=[rep]);ob=f.create_entity('IfcBuildingElementProxy',GlobalId=guid(n['id']),OwnerHistory=owner,Name=f"{code}_{n['id']:03}_{n['name']}",Description='Kaynak SKP geometrisi; teknik ve üretim kabulü bekliyor.',ObjectType='SKP kaynak parçası',ObjectPlacement=local(storey.ObjectPlacement),Representation=shape,Tag=str(n.get('source_id','')),PredefinedType='NOTDEFINED');products.append(ob)
 props={'Model':code,'Revizyon':d['revision'],'KaynakSHA256':d['source_sha256'],'SKP_Nesne':str(n.get('source_id','')),'SKP_Grup':str(n['root']),'Kabul':'Bekliyor','IFC_Kapsami':'Geometrik referans; BIM/BOM sınıflandırması bekliyor','Sunum_Cati':'Evet' if n['roof'] else 'Hayır'}
 plist=[f.create_entity('IfcPropertySingleValue',Name=k,NominalValue=f.create_entity('IfcLabel',v)) for k,v in props.items()];ps=f.create_entity('IfcPropertySet',GlobalId=guid('ps'+str(n['id'])),OwnerHistory=owner,Name='Portman_Kaynak',HasProperties=plist);f.create_entity('IfcRelDefinesByProperties',GlobalId=guid('psrel'+str(n['id'])),OwnerHistory=owner,RelatedObjects=[ob],RelatingPropertyDefinition=ps)
 expected[ob.GlobalId]={'bounds':[[min(v[i] for v in verts) for i in range(3)],[max(v[i] for v in verts) for i in range(3)]],'triangles':len(faces)}
f.create_entity('IfcRelContainedInSpatialStructure',GlobalId=guid('contains'),OwnerHistory=owner,RelatedElements=products,RelatingStructure=storey)
path=out/f'{code}_referans.ifc';f.header.file_description.description=('ViewDefinition [ReferenceView_V1.2]','Geometrik kaynak incelemesi; teknik kabul bekliyor.');f.write(str(path))
reopened=ifcopenshell.open(str(path));log=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(reopened,log)
settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);errors=[];maxdiff=0;total=0
for ob in reopened.by_type('IfcBuildingElementProxy'):
 try:
  shape=ifcopenshell.geom.create_shape(settings,ob);vs=shape.geometry.verts;tri=shape.geometry.faces;bounds=[[min(vs[i::3]) for i in range(3)],[max(vs[i::3]) for i in range(3)]];total+=len(tri)//3
  expectedbox=expected[ob.GlobalId]['bounds'];err=max(abs(bounds[a][b]-expectedbox[a][b]) for a in range(2) for b in range(3));maxdiff=max(maxdiff,err)
 except Exception as exc:errors.append({'id':ob.GlobalId,'error':str(exc)})
report={'model':code,'revision':d['revision'],'scope':'SKP geometrik referans; üretim veya semantik BIM kabulü değildir','schema':'IFC4','objects':len(products),'reopened_objects':len(reopened.by_type('IfcBuildingElementProxy')),'source_triangles':source_triangles,'reopened_triangles':total,'max_bounds_delta_m':maxdiff,'schema_issues':log.statements,'geometry_errors':errors,'source_sha256':d['source_sha256']}
(out/'ifc_kontrol.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['schema_issues','geometry_errors']},ensure_ascii=False));print('SCHEMA',len(log.statements),'GEOMETRY',len(errors))
