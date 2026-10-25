import ezdxf, collections
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace()
X0, Y0, W, H = 59723, 31585, 3601, 2517
D = []; Lines = []
for e in msp:
    t = e.dxftype()
    try:
        if t == 'DIMENSION':
            p1, p2 = e.dxf.defpoint2, e.dxf.defpoint3
            if X0 <= p1.x <= X0+W and Y0 <= p1.y <= Y0+H:
                D.append((round(p1.x,1), round(p1.y,1), round(p2.x,1), round(p2.y,1), round(e.get_measurement(),3)))
        elif t == 'LINE':
            a, b = e.dxf.start, e.dxf.end
            if X0 <= a.x <= X0+W and Y0 <= a.y <= Y0+H: Lines.append((round(a.x,1), round(a.y,1), round(b.x,1), round(b.y,1), e.dxf.layer))
        elif t == 'LWPOLYLINE':
            P = e.get_points('xy')
            if all(X0 <= p[0] <= X0+W and Y0 <= p[1] <= Y0+H for p in P): Lines.append(('LWP', [(round(p[0],1), round(p[1],1)) for p in P]))
    except Exception: pass
for d in sorted(D, key=lambda d: (-d[1], d[0])): print(d)
print(len(D))
for l in Lines: print(l)
