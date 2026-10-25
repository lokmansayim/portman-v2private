import ezdxf, collections
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace()
ins = [e for e in msp.query('INSERT') if e.dxf.name == 'MIMARI PLANSS' and abs(e.dxf.insert.x - 18350.63) < 1][0]
OX, OY = 30828.48614581073 + ins.dxf.insert.x, 29498.30263766391 + ins.dxf.insert.y
c = collections.Counter(); D = []
for e in msp:
    t = e.dxftype()
    try:
        if t == 'DIMENSION':
            p1, p2 = e.dxf.defpoint2, e.dxf.defpoint3
            a = (p1.x - OX, p1.y - OY); b = (p2.x - OX, p2.y - OY)
            if -200 < a[0] < 1100 and -300 < a[1] < 800:
                D.append((round(a[0],1), round(a[1],1), round(b[0],1), round(b[1],1), round(e.get_measurement(),2), e.dxf.layer))
        elif t == 'LINE':
            a = (e.dxf.start.x - OX, e.dxf.start.y - OY); b = (e.dxf.end.x - OX, e.dxf.end.y - OY)
            if -200 < a[0] < 1100 and -300 < a[1] < 800: c[('LINE', e.dxf.layer)] += 1
        elif t in ('LWPOLYLINE','TEXT','MTEXT','INSERT','SOLID','HATCH'):
            pass
    except Exception as ex: pass
print(c)
for d in sorted(D, key=lambda d: (d[1], d[0])): print(d)
print(len(D))
