import ezdxf, collections, json
doc = ezdxf.readfile('t_fix.dxf')
blk = doc.blocks.get('MIMARI PLANSS')
OX, OY = 30828.48614581073, 29498.30263766391
r = lambda v: round(v, 2)
out = collections.defaultdict(list)
for e in blk:
    t = e.dxftype(); L = e.dxf.layer
    if t == 'LINE':
        out[(L,'LINE')].append((r(e.dxf.start.x-OX), r(e.dxf.start.y-OY), r(e.dxf.end.x-OX), r(e.dxf.end.y-OY)))
    elif t == 'LWPOLYLINE':
        out[(L,'LWP')].append([(r(p[0]-OX), r(p[1]-OY)) for p in e.get_points('xy')])
    elif t == 'ARC':
        out[(L,'ARC')].append((r(e.dxf.center.x-OX), r(e.dxf.center.y-OY), r(e.dxf.radius), r(e.dxf.start_angle), r(e.dxf.end_angle)))
    elif t == 'SOLID':
        out[(L,'SOLID')].append([(r(e.dxf.get(f'vtx{i}').x-OX), r(e.dxf.get(f'vtx{i}').y-OY)) for i in range(4)])
    elif t == 'TEXT':
        out[(L,'TEXT')].append((e.dxf.text, r(e.dxf.insert.x-OX), r(e.dxf.insert.y-OY), r(e.dxf.rotation)))
for k, v in out.items():
    print('==', k, len(v))
    for x in sorted(v, key=lambda q: str(q))[:80]: print('  ', x)
json.dump({f'{a}|{b}': v for (a,b), v in out.items()}, open('plan_blok.json','w'), ensure_ascii=False)
