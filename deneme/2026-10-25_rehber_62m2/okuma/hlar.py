import ezdxf, json
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace()
OX, OY = 30828.48614581073 + 3079.4, 29498.30263766391 + 2663.75
ins = [e for e in msp.query('INSERT') if e.dxf.name == 'MIMARI PLANSS' and abs(e.dxf.insert.x - 3079.4) < 1][0]
OX, OY = 30828.48614581073 + ins.dxf.insert.x, 29498.30263766391 + ins.dxf.insert.y
TUR = {215: 'dubelli_kulakli', 114: 'dubelli', 31: 'standart', 240: 'uclu_dubelli_kulakli', 165: 'uclu_dubelli', 30: 'uclu_standart'}
H = []
for c in msp.query('CIRCLE'):
    x, y = c.dxf.center.x - OX, c.dxf.center.y - OY
    if -50 < x < 950 and -50 < y < 650 and abs(c.dxf.radius - 18) < 0.1:
        H.append(dict(x=round(x, 2), y=round(y, 2), tur=TUR[c.dxf.color]))
for c in msp.query('CIRCLE'):
    x, y = c.dxf.center.x - OX, c.dxf.center.y - OY
    if -50 < x < 950 and -50 < y < 650 and abs(c.dxf.radius - 22.23) < 0.1: print('C işareti', round(x,1), round(y,1))
H.sort(key=lambda h: (h['y'], h['x']))
for h in H: print(h)
print(len(H))
json.dump(H, open('h_ham.json', 'w'))
