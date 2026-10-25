"""Dört render'ı tek paftada birleştirir, etiketleri ekler."""
import json, os
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__))
F = '/usr/share/fonts/opentype/inter/'
f_baslik = ImageFont.truetype(F + 'Inter-SemiBold.otf', 34)
f_satir = ImageFont.truetype(F + 'Inter-SemiBold.otf', 25)
f_alt = ImageFont.truetype(F + 'Inter-Regular.otf', 19)
f_etiket = ImageFont.truetype(F + 'Inter-Medium.otf', 19)
KOYU, GRI, VURGU = (28, 32, 38), (95, 100, 108), (176, 62, 38)

S = 0.8                      # render ölçeği (1100 × 1000 → 880 × 800)
PW, PH = int(1100 * S), int(1000 * S)
M, UST, SATIR = 36, 120, 64
W = M * 3 + PW * 2
Hh = UST + 2 * (SATIR + PH) + M + 40
pafta = Image.new('RGB', (W, Hh), (246, 245, 242))
d = ImageDraw.Draw(pafta)
d.text((M, 34), 'Köşe direkleri · pres panel ile', font=f_baslik, fill=KOYU)
d.text((M, 80), 'Kanat = duvar kalınlığı + 3 cm. Biçim aynı, aynı ölçekte. Sac 1 mm galvaniz; panel 8 mm betopan + EPS + 8 mm betopan.', font=f_alt, fill=GRI)

SATIRLAR = [('dis', "B-01 10'luk köşe direği · 13 × 13 cm", 'dış köşeler ve veranda iç köşesi · 10 cm dış duvar', 13, 12.5),
            ('ic', "B-02 6'lık köşe direği · 9 × 9 cm", 'oda içindeki iç duvar köşesi · 6 cm iç duvar', 9, 8.5)]
# etiket: (nokta adı, metin, dx, dy) — dx, dy: yazının noktaya göre kaydırılması (px, ölçekli)
ETIKET = {'disaridan': [('kanat_biten', 'kanat {L} cm', 150, 40), ('kanat_giren', 'kanat {L} cm', -150, 40), ('kutu', 'kutu', -60, -60),
                        ('eps', 'pres panel', -70, -75)],
          'iceriden': [('ic_kanat', 'iç kanat {ik} cm', 150, 30), ('ic_tirnak', 'tırnak 3 cm', -160, 30)]}

def etiket(x, y, metin, dx, dy):
    tx, ty = x + dx, y + dy
    bb = d.textbbox((0, 0), metin, font=f_etiket); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    kx0, ky0 = (tx - tw - 12, ty - th / 2 - 8) if dx < 0 else (tx, ty - th / 2 - 8)
    kx1, ky1 = kx0 + tw + 12 + 12, ky0 + th + 16
    ux = kx1 if dx < 0 else kx0           # çizginin kutuya değdiği yer
    d.line([(x, y), (ux, (ky0 + ky1) / 2)], fill=VURGU, width=2)
    d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=VURGU)
    d.rounded_rectangle([kx0, ky0, kx1, ky1], radius=6, fill=(255, 255, 255), outline=VURGU, width=2)
    d.text((kx0 + 12, ky0 + 8 - bb[1]), metin, font=f_etiket, fill=VURGU)

for r, (tip, ad, alt, L, ik) in enumerate(SATIRLAR):
    y0 = UST + r * (SATIR + PH)
    d.text((M, y0 + 14), ad, font=f_satir, fill=KOYU)
    aw = d.textlength(ad, font=f_satir)
    d.text((M + aw + 18, y0 + 20), alt, font=f_alt, fill=GRI)
    for c, bakis in enumerate(['disaridan', 'iceriden']):
        x0, yy = M + c * (PW + M), y0 + SATIR
        im = Image.open(os.path.join(D, f'son_{tip}_{bakis}.png')).convert('RGB').resize((PW, PH), Image.LANCZOS)
        pafta.paste(im, (x0, yy))
        d.text((x0 + 16, yy + 12), 'Dışarıdan' if bakis == 'disaridan' else 'İçeriden (oda tarafı)', font=f_etiket, fill=GRI)
        nk = json.load(open(os.path.join(D, f'son_{tip}_{bakis}.json')))
        for ad_n, metin, dx, dy in ETIKET[bakis]:
            px, py = nk[ad_n]
            etiket(x0 + px * S, yy + py * S, metin.format(L=L, ik=str(ik).replace('.', ',')), dx, dy)
d.text((M, Hh - 44), 'PortatifEv · PK-01 · 60 m² · ölçüler Lokman\'ın çiziminden, 24.10.2026 · Blender Cycles', font=f_alt, fill=GRI)
pafta.save(os.path.join(D, 'kose_render.png'), optimize=True)
print(pafta.size)
