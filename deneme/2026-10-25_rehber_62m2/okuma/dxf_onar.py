import re
L = open('t.dxf', 'rb').read().split(b'\n')
L = [l[:-1] if l.endswith(b'\r') else l for l in L]
isint = re.compile(rb'^\s*-?\d+\s*$')
out = []; i = 0; n = len(L); onarim = 0
while i < n - 1:
    code, val = L[i], L[i + 1]; i += 2
    while i < n and not isint.match(L[i]):   # değerin içinde satır sonu: sonraki satırları değere ekle
        val += b' ' + L[i]; i += 1; onarim += 1
    out += [code, val]
open('t_fix.dxf', 'wb').write(b'\r\n'.join(out) + b'\r\n')
print('onarılan satır', onarim)
