"""Montaj rehberi sayfasını üretir: template.html + data.json → tek dosya HTML.

Kullanım: python uret.py <cikti.html> [--proje PK-01]
--proje: başlıktaki proje adı. Depoda ve herkese açık yayında kod kalır (PK-01).
Lokman'ın özel artefaktında gerçek ad kullanılıyor; adı yalnız özel çıktıda ver, depoya yazma.
data.json'u yeniden kurmak için: python build_data.py (depodaki PK-01 pafta katmanından ve kartlardan okur).
"""
import argparse, json, os

B = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('cikti')
ap.add_argument('--proje', default='PK-01')
a = ap.parse_args()
d = json.load(open(os.path.join(B, 'data.json'), encoding='utf-8'))
s = open(os.path.join(B, 'template.html'), encoding='utf-8').read()
veri = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(a.cikti, 'w', encoding='utf-8').write(s.replace('__DATA__', veri).replace('__PROJE__', a.proje))
print(a.cikti, os.path.getsize(a.cikti), 'bayt')
