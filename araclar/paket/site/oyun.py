"""İE-45 (D-138) · Montaj oyunu "Evi kendin kur": sitenin oyun klasörü (rehber.portatifev.com/<klasör>/).

Oyun bir rehberin kendisinden kurulur (D-28): adımlar, oda adları, oda metinleri ve kamera görünüşleri main'in rehber sayfasının
verisinden (`temizle.Temizleyici` ile iç notları çıkmış), 3B model aynı koşunun GLB'sinden (`rehber/glb.js`; kapı ve kanatların
açılıp kapanması, cam yününün serilmesi düğümlerin extras'ında). Oyunun kendi metni yalnız ipuçlarıdır (`oyun_ipuclari.json`).
Klasör: index.html (`oyun.html` şablonu, satır içi betiklerin CSP özetleri), ev.glb (kök adı 'ev'; evin kodu çıkar),
js/ ve yazi/ (yerel three.js ve yazı tipleri), gorsel/kapak.jpg (açılış kartı, `#kapak` kipi). Lokman, 20 Kasım 2026 08:52:07 UTC
"bu oyunu çok beğendim VPS 'da yayına alabilir misin?" ve kart 08:54:40 "Evet, açılışa kart eklensin".
"""
from __future__ import annotations

import html as H
import json
import re
import struct
from pathlib import Path

from . import ortak, temizle

SABLON = Path(__file__).with_name('oyun.html')
IPUCU = Path(__file__).with_name('oyun_ipuclari.json')
ODA_KAMERA = {'az': 0.5, 'el': 0.9, 'd': 14, 'y': 0.7}     # oda adımında kamera: odanın ortasına, eğik üstten
ILK_KAMERA = {'el': 0.95, 'd': 18}                          # ilk adım: bütün taban görünsün (rehberinkinden biraz yatık ve uzak)
GLB_KOK = 'ev'


def rehber_verisi(html: str, r: dict) -> dict:
    """Rehber sayfasının verisi, sitedeki gibi temizlenmiş (iç notlar çıkmış, evin kodu yerine görünen ad)."""
    m = re.search(r'<script type="application/json" id="pafta">(.*?)</script>', html, flags=re.S)
    if not m:
        raise ortak.SiteHatasi(f'{r["klasor"]}: rehber sayfasında veri yok')
    ham = json.loads(m.group(1).replace('<\\/', '</'))
    return temizle.Temizleyici(r.get('kod') or ham.get('kod'), r['ad'], altmis_iki=r['ad'].startswith('62 m²')).veri(ham)


def _duz(s: str) -> str:
    return s.replace('’', "'")


def _kucuk_bas(s: str) -> str:
    return ({'I': 'ı', 'İ': 'i'}.get(s[0]) or s[0].lower()) + s[1:]


def _ilk_cumle(s: str) -> str:
    m = re.match(r'(.+?[.!?])(?:\s|$)', s.strip())
    return m.group(1) if m else s.strip()


def _yuv(x: float) -> float:
    return round(float(x), 4)


def veri(d: dict, r: dict, o: dict) -> dict:
    """Oyunun verisi: her adımın kartı, ipucu, bilgisi, düşme yüksekliği ve kamera görünüşü (metre, sahnenin ekseninde)."""
    ip = json.loads(IPUCU.read_text(encoding='utf-8'))
    ip_adim = {_duz(k): v for k, v in ip['adim'].items()}
    dis = d['dis']
    X = lambda x: _yuv(x / 100 - dis[0] / 200)            # plan (cm, sol alt köşe) → sahne (m, evin ortası)
    Z = lambda y: _yuv(dis[1] / 200 - y / 100)
    odalar = {x['id']: x for x in d['rooms']}
    adimlar, ilk_oda = [], True
    for i, a in enumerate(d['adimlar'][1:], start=1):
        if 'oda' in a:
            od = odalar[a['oda']]
            alan = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in od['rects'])
            cx = sum((x1 - x0) * (y1 - y0) * (x0 + x1) / 2 for x0, y0, x1, y1 in od['rects']) / alan
            cy = sum((x1 - x0) * (y1 - y0) * (y0 + y1) / 2 for x0, y0, x1, y1 in od['rects']) / alan
            ipucu = ip['ilk_oda'].format(oda=_kucuk_bas(od['ad'])) if ilk_oda else ip['oda']
            ilk_oda = False
            adimlar.append({'i': i, 'kart': f'{od["ad"]} duvarları', 'oda': True, 'drop': a.get('drop', 0), 'ipucu': ipucu,
                            'bilgi': _ilk_cumle(od['metin']),
                            'kamera': {'t': [X(cx), ODA_KAMERA['y'], Z(cy)], 'az': ODA_KAMERA['az'], 'el': ODA_KAMERA['el'], 'd': ODA_KAMERA['d']}})
            continue
        ad = _duz(a['ad'])
        if ad not in ip_adim:
            raise ortak.SiteHatasi(f'{r["klasor"]}: oyunun ipucu yok: "{ad}" (oyun_ipuclari.json)')
        k = dict(a['kamera'])
        t = [X(k['t'][0]), _yuv(k['t'][1]), Z(k['t'][2])] if k.pop('plan', False) else [_yuv(x) for x in k['t']]
        k = {'t': t, 'az': k['az'], 'el': k['el'], 'd': k['d']}
        if i == 1:
            k.update(el=min(k['el'], ILK_KAMERA['el']), d=max(k['d'], ILK_KAMERA['d']))
        adimlar.append({'i': i, 'kart': ad, 'oda': False, 'drop': a.get('drop', 0), 'ipucu': ip_adim[ad], 'bilgi': ip_adim[ad],
                        'kamera': k})
    if len(adimlar) != r['adim'] or d['N'] != r['adim']:
        raise ortak.SiteHatasi(f'{r["klasor"]}: oyunda {len(adimlar)} adım; rehberde {r["adim"]} beklenirdi')
    g = d['adimlar'][0]['kamera']
    return {'ad': r['ad'], 'rehber': r['klasor'], 'genel': {'t': [_yuv(x) for x in g['t']], 'az': g['az'], 'el': g['el'], 'd': g['d']},
            'cati_adim': list(d['cati_adim']), 'kapak_adim': o['kapak_adim'], 'adimlar': adimlar}


def sayfa(v: dict, o: dict, esbuild: str | None = None, glb_eki: str = '') -> str:
    """Şablon + veri → index.html (CSP'li). `esbuild` verilirse modül betiği yorumsuz (rehber sayfaları gibi).
    `glb_eki`: modelin adres eki (`ortak.surum_eki`); model değişince tarayıcı eskisini göstermesin."""
    s = SABLON.read_text(encoding='utf-8')
    if glb_eki:
        if s.count("fetch('ev.glb')") != 1:
            raise ortak.SiteHatasi("oyun şablonunda fetch('ev.glb') bir kez olmalı")
        s = s.replace("fetch('ev.glb')", f"fetch('ev.glb{glb_eki}')")
    for yer, deger in (('__BAS__', ortak.bas_etiketleri(f'PortatifEv · {o["ad"]} · {v["ad"]}')), ('__AD__', H.escape(v['ad'])),
                       ('__N__', str(len(v['adimlar']))), ('__REHBER__', v['rehber'])):
        if yer not in s:
            raise ortak.SiteHatasi(f'oyun şablonunda {yer} yok')
        s = s.replace(yer, deger)
    if esbuild:
        s = re.sub(r'<script type="module">(.*?)</script>', lambda m: '<script type="module">\n' + temizle._kucult(m.group(1), esbuild) + '</script>',
                   s, flags=re.S)
    vs = json.dumps(v, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    if s.count('__VERI__') != 1:
        raise ortak.SiteHatasi('oyun şablonunda __VERI__ bir kez olmalı')
    s = s.replace('__VERI__', vs)
    s = ortak.belge_ve_csp(s, 2)
    ortak.denetle(s, f'{o["klasor"]} (oyun sayfası)')
    return s


def glb_temizle(glb: bytes, kod: str) -> bytes:
    """GLB'nin kök düğümünün adı evin kodudur (`glb.js`); herkese açık dosyada 'ev' olur. İkili parça değişmez.
    Düğüm adları ve extras son kapı taramasından geçer (`ortak.YASAK`)."""
    if glb[:4] != b'glTF' or struct.unpack('<I', glb[4:8])[0] != 2:
        raise ortak.SiteHatasi('GLB değil (glTF 2)')
    n, tur = struct.unpack('<II', glb[12:20])
    if tur != 0x4E4F534A:
        raise ortak.SiteHatasi('GLB: ilk parça JSON değil')
    j = json.loads(glb[20:20 + n].decode('utf-8'))
    kok = [j['nodes'][k] for k in j['scenes'][j.get('scene', 0)]['nodes']]
    for nd in kok:
        if nd.get('name') == kod:
            nd['name'] = GLB_KOK
    js = json.dumps(j, ensure_ascii=False, separators=(',', ':'))
    ortak.denetle(js, 'oyun modeli (GLB düğüm adları)')
    jb = js.encode('utf-8')
    jb += b' ' * (-len(jb) % 4)
    kalan = glb[20 + n:]
    toplam = 12 + 8 + len(jb) + len(kalan)
    return b'glTF' + struct.pack('<II', 2, toplam) + struct.pack('<II', len(jb), 0x4E4F534A) + jb + kalan


def klasor_yaz(v: dict, o: dict, glb: bytes, kod: str, hedef: Path, npm: Path, esbuild: str | None) -> list[str]:
    hedef.mkdir(parents=True, exist_ok=True)
    model = glb_temizle(glb, kod)
    (hedef / 'index.html').write_text(sayfa(v, o, esbuild, ortak.surum_eki(model)), encoding='utf-8')
    (hedef / 'ev.glb').write_bytes(model)
    return ortak.yerel_kutuphaneler((hedef / 'index.html').read_text(encoding='utf-8'), hedef, npm)


def kart_html(o: dict, v: dict, ek: str = '') -> str:
    """Açılış sayfasındaki oyun kartı (rehber kartlarının önünde). `ek`: kapak görselinin adres eki."""
    sp = [f'{len(v["adimlar"])} adım', 'her adımda 4 kart', 'puan ve yıldız']
    return (f'    <a class="kart" href="{o["klasor"]}/">\n'
            f'      <img src="{o["klasor"]}/gorsel/kapak.jpg{ek}" alt="{H.escape(o["ad"])}: yarım kurulmuş evin görünümü" loading="lazy">\n'
            f'      <div class="ic"><h2>{H.escape(o["ad"])}</h2>\n'
            f'        <div class="alan">Montaj oyunu · {H.escape(v["ad"])}</div>\n'
            f'        <div class="spec">{"".join(f"<span>{H.escape(x)}</span>" for x in sp)}</div>\n'
            f'        <span class="ac">Oyunu aç</span></div>\n'
            f'    </a>')
