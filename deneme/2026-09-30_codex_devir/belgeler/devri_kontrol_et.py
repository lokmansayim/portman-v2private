"""Yerel, salt okunur devir bütünlüğü denetimi. Model üretmez veya ağ kullanmaz."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rapor',type=Path,help='İsteğe bağlı yerel JSON sonuç yolu');args=p.parse_args()
manifest=json.loads((root/'DOSYA_MANIFESTI.json').read_text(encoding='utf-8'));issues=[]
for row in manifest:
 f=root/row['file']
 if not f.is_file():issues.append({'file':row['file'],'error':'missing'});continue
 if hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:issues.append({'file':row['file'],'error':'sha256 mismatch'})
syntax=0
for f in (root/'kod_arsivi').rglob('*.py'):
 try:ast.parse(f.read_text(encoding='utf-8'));syntax+=1
 except SyntaxError as e:issues.append({'file':str(f.relative_to(root)),'error':str(e)})
reports=[]
for f in (root/'teslimler').rglob('ifc_kontrol.json'):
 d=json.loads(f.read_text(encoding='utf-8'));bad=bool(d.get('schema_issues') or d.get('geometry_errors') or d.get('saved_topology_mismatch_nodes') or d.get('saved_coordinate_max_delta_m',1)>1e-6)
 reports.append({'file':str(f.relative_to(root)),'recorded_report_passed':not bad})
 if bad:issues.append({'file':str(f.relative_to(root)),'error':'recorded IFC report has unresolved errors'})
runtime=json.loads((root/'ORTAM.json').read_text(encoding='utf-8'));paths={k:Path(runtime[k]).exists() for k in ['blender','python_with_pillow','node','playwright_module','chrome','sketchup_api','ifc_runtime']}
rule=root/'kurallar/yerel_2026-09-07/KURALLAR.json';rules=json.loads(rule.read_text(encoding='utf-8'));rulehash=hashlib.sha256((rule.parent/'prefabrik-cizim-kurallari.md').read_bytes()).hexdigest();rulematch=(rulehash==rules['belge_sha256'])
result={'status':'passed' if not issues else 'failed','checked_files':len(manifest),'syntax_parsed_python_files':syntax,'ifc_report_records':reports,'runtime_paths_present':paths,'local_rule_md_matches_json_recorded_hash':rulematch,'issues':issues,'scope':'Paket hashleri, Python sözdizimi, mevcut rapor kayıtları ve bağımlılık yolları kontrol edildi. Geometri yeniden üretilmedi; üretim veya entegrasyon kabulü değildir.'}
if args.rapor:args.rapor.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(bool(issues))
