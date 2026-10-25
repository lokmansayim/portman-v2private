"""Render'ları rehber galerisi için JPEG'e çevirir; çatı katman ve baş makas kesiti görünümlerini etiketler; hepsini tek paftada toplar.
Kullanım: python pafta.py <render klasörü> <gorsel klasörü> "<başlık>" [maket_onizleme.png]
Etiket noktaları Blender kamerasıyla aynı iğne deliği izdüşümüyle hesaplanır (render.py KAM)."""
import os, sys, math
from PIL import Image, ImageDraw, ImageFont
RD, G, BASLIK = sys.argv[1], sys.argv[2], sys.argv[3]
MAKET = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(G, exist_ok=True)
F = '/usr/share/fonts/opentype/inter/'
f_baslik = ImageFont.truetype(F + 'Inter-SemiBold.otf', 40); f_alt = ImageFont.truetype(F + 'Inter-Regular.otf', 21)
f_yazi = ImageFont.truetype(F + 'Inter-Medium.otf', 21); f_etiket = ImageFont.truetype(F + 'Inter-Medium.otf', 22)
KOYU, GRI, VURGU, ZEMIN = (28, 32, 38), (95, 100, 108), (176, 62, 38), (246, 245, 242)
def ac(ad): return Image.open(ad if os.path.isabs(ad) else os.path.join(RD, ad)).convert('RGB')

# Galeri JPEG'leri (1600 px)
ADLAR = {'son_on_sol.png': 'ev_on_sol.jpg', 'son_on_sag.png': 'ev_on_sag.jpg', 'son_arka_sol.png': 'ev_arka_sol.jpg',
         'son_catisiz.png': 'ev_catisiz.jpg', 'son_ic_kose.png': 'ic_kose.jpg'}
for k, v in ADLAR.items():
    im = ac(k); im.thumbnail((1600, 1600)); im.save(os.path.join(G, v), quality=86, optimize=True, progressive=True)

# Çatı katmanları: etiketli (kamera: konum, hedef, objektif 38 mm, 36 mm sensör, 1600 × 1000)
def izd(p, kp=(10.0, 12.5, 8.6), kh=(1.6, 1.4, 2.9), lens=38, W=1600, H=1000):
    f = [kh[i] - kp[i] for i in range(3)]; n = math.sqrt(sum(v * v for v in f)); f = [v / n for v in f]
    r = [f[1], -f[0], 0]; n = math.hypot(r[0], r[1]); r = [r[0] / n, r[1] / n, 0]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [p[i] - kp[i] for i in range(3)]; xc = sum(d[i] * r[i] for i in range(3)); yc = sum(d[i] * u[i] for i in range(3)); zc = sum(d[i] * f[i] for i in range(3))
    k = lens / 36 * W
    return (W / 2 + xc / zc * k, H / 2 - yc / zc * k)
def zM(y, n=0):   # ana çatı arka yüzü, plan y (cm) → aşık oturma yüzü + n (cm), m
    return (260.25 + (630 - y) * (108.5 / 330) + n) / 100
def etiket(d, nokta, metin, kutu, sag=True):
    x, y = nokta; tx, ty = kutu
    bb = d.textbbox((0, 0), metin, font=f_etiket); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    kx0, ky0 = (tx, ty - th / 2 - 9) if sag else (tx - tw - 26, ty - th / 2 - 9); kx1, ky1 = kx0 + tw + 26, ky0 + th + 18
    ux = kx0 if sag else kx1
    d.line([(x, y), (ux, (ky0 + ky1) / 2)], fill=VURGU, width=3); d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=VURGU)
    d.rounded_rectangle([kx0, ky0, kx1, ky1], radius=7, fill=(255, 255, 255), outline=VURGU, width=2)
    d.text((kx0 + 13, ky0 + 9 - bb[1]), metin, font=f_etiket, fill=VURGU)
K = None
if os.path.exists(os.path.join(RD, 'son_cati_katman.png')):
    K = ac('son_cati_katman.png'); dk = ImageDraw.Draw(K); s = K.width / 1600
    by = lambda y: y / 100 - 3
    NOK = [((-1.2, by(470), zM(470, 6.5)), 'Trapez sac (doğrudan aşıkta)', (1110, 290), True),
           ((2.0, by(630 - 167.4 * 0.95), zM(630 - 167.4 * 0.95, 1.5)), 'Omega aşık', (540, 300), False),
           ((7.58 - 4.5, by(450), zM(450, -30)), 'Makas (C80)', (330, 720), False),
           ((8.40 - 4.5, by(540), 2.603), 'Cam yünü 10 cm (rulo)', (1180, 640), True)]
    for p, metin, kutu, sag in NOK:
        x, y = izd(p); etiket(dk, (x * s, y * s), metin, (kutu[0] * s, kutu[1] * s), sag)
    k2 = K.copy(); k2.thumbnail((1600, 1600)); k2.save(os.path.join(G, 'cati_katman.jpg'), quality=88, optimize=True, progressive=True)

# Baş makas kesiti (sol kalkan, plan y = 150): Lokman'ın çizimindeki detay; kamera render.py KAM['bas_kesit']
B = None
if os.path.exists(os.path.join(RD, 'son_bas_kesit.png')):
    B = ac('son_bas_kesit.png'); db = ImageDraw.Draw(B); s = B.width / 1600
    KP, KH, LN = (-4.46, -2.9, 2.52), (-4.46, -1.5, 2.52), 135
    X = lambda x: x / 100 - 4.5
    NOK = [((X(3.7), -1.5, 2.525), 'Baş makas (alt başlık)', (1180, 470), True),
           ((X(-0.8), -1.5, 2.4695), 'Baş makas omegası: dış U yanak', (520, 840), False),
           ((X(-0.7), -1.5, 2.60), 'Baş makas betopanı (8 mm)', (520, 150), False),
           ((X(5.0), -1.5, 2.43), 'Pano: 8 mm betopan + 84 mm strafor + 8 mm betopan', (520, 950), False),
           ((X(16), -1.5, 2.57), 'Cam yünü 10 cm', (1180, 200), True),
           ((X(18), -1.5, 2.461), 'Ters tavan alçıpanı', (1180, 880), True)]
    for p, metin, kutu, sag in NOK:
        x, y = izd(p, KP, KH, LN); etiket(db, (x * s, y * s), metin, (kutu[0] * s, kutu[1] * s), sag)
    b2 = B.copy(); b2.thumbnail((1600, 1600)); b2.save(os.path.join(G, 'bas_kesit.jpg'), quality=88, optimize=True, progressive=True)

# Tek pafta
W, M = 2000, 40; w2 = (W - 3 * M) // 2
def olc(im, gen): return im.resize((gen, round(im.height * gen / im.width)), Image.LANCZOS)
ust = olc(ac('son_on_sol.png'), W - 2 * M)
satirlar = [([ac('son_on_sag.png'), ac('son_arka_sol.png')], ['Ön-sağdan: cumba ile ana çatının dere hattı, iç köşede iniş', 'Arka-soldan: kalkan, alın sacı ve inişler']),
            ([ac('son_catisiz.png'), K or ac('son_cati_katman.png')], ['Çatısız: oda oda dizilim, kapılar ve pencereler', 'Çatı: makas → aşık → trapez sac; tavanda cam yünü (OSB, nem bariyeri yok)'])]
satirlar.append(([ac('son_ic_kose.png'), B or ac('son_bas_kesit.png')], ['Cumbanın sağı: iç köşede dere ve iniş', 'Baş makas kesiti: 8 mm betopan omeganın dış U yanağında']))
if MAKET:
    mk = Image.open(MAKET).convert('RGB')
    satirlar.append(([mk.crop((230, 100, 1190, 680))], ['3D yazıcı maketi 1:50: gövde ve çıkarılabilir çatı']))
satirlar = [([olc(i, w2) for i in ims], yz) for ims, yz in satirlar]
YAZI = 44
H = 150 + ust.height + YAZI + M + sum(max(i.height for i in ims) + YAZI + M for ims, _ in satirlar) + 70
P = Image.new('RGB', (W, H), ZEMIN); d = ImageDraw.Draw(P)
d.text((M, 40), f'{BASLIK} · prefabrik · montaj sonu', font=f_baslik, fill=KOYU)
d.text((M, 96), 'Montaj rehberinin 3B modelinden, Blender Cycles. Ham malzeme: betopan, galvaniz profiller, antrasit sac; boya ve sıva yok.', font=f_alt, fill=GRI)
y = 150; P.paste(ust, (M, y)); y += ust.height + 8
d.text((M, y), 'Ön-soldan: veranda, cumba ve ana çatı; fugalı cephe', font=f_yazi, fill=KOYU); y += YAZI
for ims, yz in satirlar:
    for i, im in enumerate(ims):
        x = M + i * (w2 + M); P.paste(im, (x, y)); d.text((x, y + im.height + 8), yz[i], font=f_yazi, fill=KOYU)
    y += max(i.height for i in ims) + YAZI + M
d.text((M, H - 50), 'PortatifEv · 900 × 600 cm · beşik + cumba · trapez sac · 10 cm cam yünü · ters tavan alçıpan · fugalı cephe · ölçüler paftadan', font=f_alt, fill=GRI)
P.save(os.path.join(RD, 'ev_render_pafta.png'), optimize=True)
P.save(os.path.join(G, 'ev_render_pafta.jpg'), quality=86, optimize=True, progressive=True)
print(P.size, sorted(os.listdir(G)))
