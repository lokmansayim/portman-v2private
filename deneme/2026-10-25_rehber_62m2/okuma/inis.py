import ezdxf, collections
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace()
ins = [e for e in msp.query('INSERT') if e.dxf.name == 'MIMARI PLANSS' and abs(e.dxf.insert.x - 21887.84) < 1][0]
OX, OY = 30828.48614581073 + ins.dxf.insert.x, 29498.30263766391 + ins.dxf.insert.y
print('orijin', OX, OY)
for e in msp.query('CIRCLE'):
    x, y = e.dxf.center.x - OX, e.dxf.center.y - OY
    if -300 < x < 1200 and -400 < y < 900: print('çember', round(x,1), round(y,1), round(e.dxf.radius,1), e.dxf.layer, e.dxf.get('color'))
c = collections.Counter()
for e in msp.query('LINE LWPOLYLINE'):
    P = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)] if e.dxftype()=='LINE' else [tuple(p) for p in e.get_points('xy')]
    P = [(p[0]-OX, p[1]-OY) for p in P]
    if all(-300 < p[0] < 1200 and -400 < p[1] < 900 for p in P):
        c[(e.dxftype(), e.dxf.layer, e.dxf.get('linetype'))] += 1
        if e.dxf.get('linetype') not in (None, 'BYLAYER', 'Continuous', 'CONTINUOUS') or e.dxf.layer not in ('0',):
            print(e.dxftype(), e.dxf.layer, e.dxf.get('linetype'), [(round(a,1), round(b,1)) for a,b in P][:6])
print(c)
cm = [e for e in msp.query('INSERT') if e.dxf.name == 'CMAKAS' and abs(e.dxf.insert.x - 54642.06) < 1][0]
print('CMAKAS ins', cm.dxf.insert.x - OX, cm.dxf.insert.y - OY)
