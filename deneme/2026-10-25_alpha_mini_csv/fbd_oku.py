"""SKP içindeki MRD Frame Builder verisini (fbd-* öznitelik sözlükleri) maskeli, kısa JSON'a döker.

Eklenti her paneli bir grup olarak yazar: grubun `fbd-einfo`su panel ayarı (dikme aralığı, servis deliği
yükseklikleri, boşluklar, takım ayarı), her çubuğun `fbd-einfo`su türü (code), ekseni ve eklentinin hesapladığı
işlemleri tutar: flangeholes = DIMPLE, lip_cuts = LIP_CUT, swages = SWAGE, notches = NOTCH,
service_holes = SERVICE_HOLE, flip_x = LABEL_NRM (doğru) / LABEL_INV (yanlış). SKP içi birim inçtir; burada mm.
Kişi adı taşıyan alanlar (user_profile vb.) yazılmaz.

Kullanım (openskp 1.3.0 gerekir: pip install openskp==1.3.0):
  python fbd_oku.py <proje>.skp --csv kaynak/DVR1_duvar.csv --json kaynak/DVR1_fbd.json
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openskp import _core
import csv_oku

IN = 25.4
KIMLIK = [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]
ATILAN = ('user_profile',)                     # kişi adı
ISLEM = {'flangeholes': 'DIMPLE', 'lip_cuts': 'LIP_CUT', 'swages': 'SWAGE', 'notches': 'NOTCH', 'service_holes': 'SERVICE_HOLE'}
PANEL_MM = ('length', 'height', 'width', 'thickness', 'stud_spacing', 'nog_first', 'nog_spacing', 'edge_clearance',
            'top_clearance', 'bottom_clearance', 'bottom_plate_to_stud', 'top_plate_to_stud', 'noggin_to_stud',
            'sill_to_stud', 'head_to_stud', 'adjacent_clearance', 'adjacent_stud_proximity', 'adjacent_nog_proximity',
            'hole_position', 'hole_diameter', 'lip_width', 'coil_thickness', 'web_brace_to_top_plate',
            'web_brace_to_bottom_plate', 'brace_start_end_clearance', 'brace_hole_extension',
            'header_brace_hole_extension', 'chamfered_end_clearance', 'header_height', 'stud1_offset', 'stud2_offset')
PANEL_LISTE_MM = ('studs', 'deleted_studs', 'nogs')
PANEL_METIN = ('name', 'type', 'style', 'machine_tooling', 'horz_service_hole_pos', 'vert_service_hole_pos',
               'top_track_fixing', 'stick_order', 'staggered_nogging', 'justify')
ACIKLIK_MM = ('width', 'height', 'sill_height', 'header_height', 'new_origin_y', 'webspace', 'web_offset',
              'web_start_end_clearance', 'king_stud_gap', 'head_to_stud', 'noggin_to_stud', 'lip_width')
ACIKLIK_METIN = ('name', 'type', 'base_name', 'header_type', 'style', 'header_style1', 'sill_type', 'qty_jamp_stud')
TAKIM_MM = ('lip_cut_tool_size', 'notch_tool_size', 'swage_tool_size', 'service_hole_size', 'tab_size', 'cut_clearance')


def mm(v, n=2):
    return round(float(v) * IN, n)


def ornekler(yol):
    p = _core.full_parse(yol); defs = p['defs_dict']; cikti = []
    def yuru(did, ust):
        d = defs.get(did)
        if not d:
            return
        for inst in d['builder'].instances:
            alt = defs.get(inst['ref_idx']) or {}
            ad = inst.get('name') or alt.get('name') or ''
            cikti.append({'yol': ust + '/' + ad, 'attr': inst.get('attribute_dictionaries') or {}})
            yuru(inst['ref_idx'], ust + '/' + ad)
    yuru('ROOT', '')
    return p, cikti


def dok(skp, csv_yol):
    p, O = ornekler(skp)
    _, P = csv_oku.oku(csv_yol) if csv_yol else ({}, [])
    paneller = []
    for o in O:
        e = o['attr'].get('fbd-einfo', {})
        if e.get('type') != 'wall' or 'studs' not in e:
            continue
        panel = {k: mm(e[k]) for k in PANEL_MM if isinstance(e.get(k), (int, float))}
        panel.update({k: [mm(x) for x in e.get(k) or []] for k in PANEL_LISTE_MM})
        panel.update({k: e.get(k) for k in PANEL_METIN})
        # elle eklenen servis delikleri: [kod, x1, y1, x2, y2, [konumlar]]
        panel['added_service_holes'] = [[s[0]] + [mm(x) for x in s[1:5]] + [[mm(x) for x in s[5]]] for s in e.get('added_service_holes', [])]
        panel['elle_eklenen_diger'] = {k: v for k, v in e.items() if k.startswith('added_') and v and k != 'added_service_holes'}
        aciklik = []
        uyeler = []
        for a in O:
            if not a['yol'].startswith(o['yol'] + '/'):
                continue
            ea = a['attr'].get('fbd-einfo', {})
            if ea.get('parent_type') == 'wall' and ea.get('type') in ('window', 'door'):
                d = {k: mm(ea[k]) for k in ACIKLIK_MM if isinstance(ea.get(k), (int, float))}
                d.update({k: ea.get(k) for k in ACIKLIK_METIN}); aciklik.append(d)
            if 'code' not in ea:
                continue
            u = {'kod': ea['code'], 'tur': ea.get('type'), 'x1': mm(ea['start_x']), 'y1': mm(ea['start_y']),
                 'x2': mm(ea['end_x']), 'y2': mm(ea['end_y']), 'boy': mm(ea['length']), 'flip_x': ea.get('flip_x') == 'true',
                 'stil': ea.get('style'), 'takim': {k: mm(ea[k]) for k in TAKIM_MM if isinstance(ea.get(k), (int, float))},
                 'islem_skp': {v: [mm(x) for x in ea.get(k) or []] for k, v in ISLEM.items()}}
            esi = [c for c in P if max(abs(c['x1'] - u['x1']), abs(c['y1'] - u['y1']), abs(c['x2'] - u['x2']), abs(c['y2'] - u['y2'])) < 0.05]
            u['csv_ad'] = esi[0]['ad'] if len(esi) == 1 else None
            uyeler.append(u)
        uyeler.sort(key=lambda u: int(u['csv_ad'].rsplit('-', 1)[1]) if u['csv_ad'] else 999)
        paneller.append({'panel': panel, 'aciklik': aciklik, 'uyeler': uyeler})
    for pn in paneller:
        assert not any(k in json.dumps(pn) for k in ATILAN)
    return {'kaynak': 'SketchUp %s · MRD Frame Builder (fbd-einfo, fbd-profile) · birim mm' % str(p.get('version')).strip('{}'),
            'paneller': paneller}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('skp'); ap.add_argument('--csv'); ap.add_argument('--json', required=True)
    a = ap.parse_args()
    r = dok(a.skp, a.csv)
    json.dump(r, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for pn in r['paneller']:
        eslesen = sum(1 for u in pn['uyeler'] if u['csv_ad'])
        print(f"{pn['panel']['name']}: {len(pn['uyeler'])} çubuk ({eslesen} CSV ile eşleşti) · açıklık {len(pn['aciklik'])} · stil {pn['panel']['style']} · takım ayarı {pn['panel']['machine_tooling']}")
