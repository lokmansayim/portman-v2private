"""Ev render'larını tek, etiketli paftada toplar; rehber galerisi için JPEG kopyalar üretir.
Kullanım: python ev_pafta.py  (son_ev_*.png ve kose_render.png bu klasörde olmalı)"""
import os
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__))
F = '/usr/share/fonts/opentype/inter/'
f_baslik = ImageFont.truetype(F + 'Inter-SemiBold.otf', 40)
f_alt = ImageFont.truetype(F + 'Inter-Regular.otf', 21)
f_yazi = ImageFont.truetype(F + 'Inter-Medium.otf', 21)
f_etiket = ImageFont.truetype(F + 'Inter-Medium.otf', 20)
KOYU, GRI, VURGU, ZEMIN = (28, 32, 38), (95, 100, 108), (176, 62, 38), (246, 245, 242)

def ac(ad): return Image.open(os.path.join(D, ad)).convert('RGB')

# Galeri için JPEG kopyalar (1600 px)
G = os.path.join(D, 'gorsel'); os.makedirs(G, exist_ok=True)
for kaynak, hedef in [('son_ev_on_sag.png', 'ev_on_sag.jpg'), ('son_ev_arka_sol.png', 'ev_arka_sol.jpg'), ('son_ev_catisiz.png', 'ev_catisiz.jpg'),
                      ('son_ev_kose_dere.png', 'kose_dere.jpg'), ('son_ev_kalkan_kesit.png', 'kalkan_kesit_ham.jpg'), ('kose_render.png', 'kose_direkleri.jpg')]:
    im = ac(kaynak); im.thumbnail((1600, 1600)); im.save(os.path.join(G, hedef), quality=86, optimize=True, progressive=True)

# Kalkan kesiti: etiketli (ortografik; 1 cm = 1600 / 56 px; görüntü merkezi o = 10, p = 3)
K = ac('son_ev_kalkan_kesit.png'); dk = ImageDraw.Draw(K); S = K.width / 56.0
def px(o, p): return (K.width / 2 + (o - 10) * S, K.height / 2 - (p - 3) * S)
def etiket(d, nokta, metin, kutu_xy, sag=True):
    x, y = nokta; tx, ty = kutu_xy
    bb = d.textbbox((0, 0), metin, font=f_etiket); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    kx0, ky0 = (tx, ty - th / 2 - 8) if sag else (tx - tw - 24, ty - th / 2 - 8); kx1, ky1 = kx0 + tw + 24, ky0 + th + 16
    ux = kx0 if sag else kx1
    d.line([(x, y), (ux, (ky0 + ky1) / 2)], fill=VURGU, width=2); d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=VURGU)
    d.rounded_rectangle([kx0, ky0, kx1, ky1], radius=6, fill=(255, 255, 255), outline=VURGU, width=2)
    d.text((kx0 + 12, ky0 + 8 - bb[1]), metin, font=f_etiket, fill=VURGU)
ET = [((10, 8.0), 'Trapez sac (çatı kaplaması)', (560, 120), False),
      ((22.8, 8.9), 'Kenar hadvesini kavrayan kıvrım', (1000, 120), True),
      ((30.25, 6.0), 'Alın sacı', (1440, 300), True),
      ((5, 1.5), 'Aşık', (260, 430), False),
      ((29.9, 0.0), 'C kapama', (1440, 520), True),
      ((0.35, -1.5), "Baş makas Z'si · 3 cm çentik", (440, 700), False),
      ((18, -3.05), 'Saçak altı (alın sacının tırnağı Z\'ye girer)', (900, 760), True),
      ((-0.3, -7), 'Betopan', (230, 860), False),
      ((-5, -10), 'Baş makas', (230, 940), False)]
for (o, p), metin, kutu, sag in ET:
    etiket(dk, px(o, p), metin, kutu, sag)
K.save(os.path.join(G, 'kalkan_kesit.jpg'), quality=88, optimize=True, progressive=True)

# Tek pafta: üstte büyük ön-sağ; altta arka-sol ve çatısız; en altta köşe ve kalkan kesiti
W, M = 2000, 40
w2 = (W - 3 * M) // 2
def olc(im, gen): return im.resize((gen, round(im.height * gen / im.width)), Image.LANCZOS)
ust = olc(ac('son_ev_on_sag.png'), W - 2 * M)
r2 = [olc(ac('son_ev_arka_sol.png'), w2), olc(ac('son_ev_catisiz.png'), w2)]
r3 = [olc(ac('son_ev_kose_dere.png'), w2), olc(K, w2)]
YAZI = 44
H = 150 + ust.height + YAZI + M + r2[0].height + YAZI + M + r3[0].height + YAZI + 70
P = Image.new('RGB', (W, H), ZEMIN); d = ImageDraw.Draw(P)
d.text((M, 40), 'PK-01 · 60 m² prefabrik · montaj sonu', font=f_baslik, fill=KOYU)
d.text((M, 96), 'Montaj rehberinin 3B modelinden, Blender Cycles. Ham malzeme: betopan, galvaniz profiller, antrasit sac; boya ve sıva yok.', font=f_alt, fill=GRI)
y = 150
P.paste(ust, (M, y)); y += ust.height + 8
d.text((M, y), 'Ön-sağdan: veranda, dış kapı, saçak ve inişler', font=f_yazi, fill=KOYU); y += YAZI
for satir, yazilar in ((r2, ['Arka-soldan: kalkan, alın sacı, inişler', 'Çatısız: oda oda dizilim, kapılar ve pencereler']),
                       (r3, ['Köşe: alın sacı derenin alnını kapatır; iniş binayla iner', 'Kalkan kesiti (Lokman\'ın çizimiyle)'])):
    for i, im in enumerate(satir):
        x = M + i * (w2 + M); P.paste(im, (x, y)); d.text((x, y + im.height + 8), yazilar[i], font=f_yazi, fill=KOYU)
    y += satir[0].height + YAZI + M
d.text((M, H - 50), 'PortatifEv · PK-01 · 24.10.2026 · ölçüler pafta ve Lokman\'ın çizimlerinden', font=f_alt, fill=GRI)
P.save(os.path.join(D, 'ev_render_pafta.png'), optimize=True)
P.convert('RGB').save(os.path.join(G, 'ev_render_pafta.jpg'), quality=86, optimize=True, progressive=True)
print(P.size, sorted(os.listdir(G)))
