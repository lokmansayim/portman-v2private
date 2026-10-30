"""İE-09 · Atölye kontrol sayfası (PDF; D-20): Lokman her modeli tek dosyada görür, "kabul" ya da düzeltmeyi düz cümleyle yazar.

Sayfalar (A4 yatay):
1. Kart, oda tablosu (çizimden çıkan m² ile kaynakta yazan m² yan yana; her değerin kaynağı yazar: kod, görsel okuma, DXF, Lokman),
   öteki değerler (brüt oturum, oda programı, pencere, kapı, dış ölçü, çatı), otomatik denetimler, metraj kabul testi, liste özeti,
   düzeltme geçmişi.
2. Çizim seti paftası (`<kod>_pafta.png`: plan, çatı planı, dört görünüş, notlar).
3–4. Bayiye giden pafta (Örnek Şablon, `<kod>_pafta.pdf`; antet "...", kişi ve bayi adı yok).
5. Bayi görseli (`<kod>_bayi_gorsel.png`; aday kartı ve r01'in başlık görseli).

Çizimler motorun çıktısıdır; bu sayfa yeniden çizmez, yalnız dizer (PyMuPDF). Sayfa bayiye gitmez, depoya girmez."""
from __future__ import annotations

import html
import json
from pathlib import Path

A4 = (842, 595)
CSS = """
* { font-family: sans-serif; font-size: 7.6pt; line-height: 1.25; }
h1 { font-size: 13pt; margin: 0 0 2px 0; }
h2 { font-size: 9pt; margin: 7px 0 2px 0; }
p { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 0.4px solid #9aa3ad; padding: 1.5px 3px; vertical-align: top; text-align: left; }
th { background-color: #e8edf2; }
.sag { text-align: right; }
.nw { white-space: nowrap; }
.gecti { color: #1d6b2f; font-weight: bold; }
.uyari { color: #9a5b00; font-weight: bold; }
.kaldi { color: #b0161b; font-weight: bold; }
.bilgi { color: #33507a; font-weight: bold; }
.kutu { border: 0.8px solid #33507a; background-color: #f2f6fb; padding: 4px; }
.soluk { color: #5d6670; }
"""
SINIF = {"geçti": "gecti", "uyarı": "uyari", "kaldı": "kaldi", "bilgi": "bilgi"}


def e(x) -> str:
    return html.escape(str(x if x is not None else "…"))


def sayi(x, basamak: int = 2) -> str:
    if x is None:
        return "…"
    if isinstance(x, (list, tuple)):
        return " × ".join(sayi(y, 1) for y in x)
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    s = f"{float(x):.{basamak}f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s.replace(".", ",")


def yuzde(x, basamak: int = 2) -> str:
    """İşaretli yüzde, işaret yüzde imisinden önce: +%6,3 / −%14,9 (Türkçe yazım; "%-14,9" okunmuyordu)."""
    if x is None:
        return "…"
    return ("−" if x < 0 else "+" if x > 0 else "") + "%" + sayi(abs(x), basamak)


def yuzde_html(x, basamak: int = 2) -> str:
    """`yuzde`, satır sonunda işaretten bölünmesin diye tek parça."""
    return f"<span class='nw'>{yuzde(x, basamak)}</span>"


def _sol(kart: dict) -> str:
    o = kart.get("olcum") or {}
    k = kart.get("kaynak") or {}
    dosyalar = ", ".join(f"{d['etiket']} ({d['uzanti']}, {d['sha256'][:12]})" for d in k.get("dosyalar") or []) or "yok"
    kaynak = {"varyant": f"{k.get('taban')} tanımından çatı varyantı (taban tanım değişmedi)", "proje": f"gerçek proje {k.get('proje') or ''}".strip(),
              "istek": "Lokman'ın isteği"}.get(k.get("tur"), k.get("tur"))
    cati = o.get("cati") or {}
    satirlar = [("Kod", f"{kart['gosterim']} (iç kod {kart['kod']}; adı siz verirsiniz)"), ("Ad", kart.get("ad")),
                ("Aile · kat", f"{kart.get('aile')} · {kart.get('kat')}"), ("Kaynak", f"{kaynak}: {k.get('metin') or '…'}"),
                ("Kaynak dosyalar", dosyalar),
                ("Brüt oturum", f"{sayi(o.get('oturum_m2'))} m² (veranda dahil; veranda {sayi(o.get('veranda_m2'))} m²)"),
                ("Oda programı", o.get("oda_programi")), ("Dış ölçü", f"{sayi(o.get('dis_olcu_cm'))} cm"),
                ("Çatı", f"{kart.get('cati_adi')} · tip {cati.get('tip')} · {cati.get('duzlem')} düzlem · yüzey {sayi(cati.get('yuzey_m2'))} m²"),
                ("Çatı kenarları", ", ".join(f"{a} {sayi(v / 100)} m" for a, v in (cati.get("kenar_cm") or {}).items()) or "…"),
                ("Müşteri projesi", "evet (bayiye adsız)" if kart.get("musteri_projesi") else "hayır"),
                ("Durum", kart.get("durum"))]
    s = ["<h2>Model kartı</h2><table>"] + [f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in satirlar] + ["</table>"]
    mt = kart.get("metraj_testi") or {}
    s.append("<h2>Metraj kapısı (çelik kg, eşik ±%3)</h2><div class='kutu'>")
    if mt.get("durum") == "yok":
        s.append("<p><b>Metraj kapısı: referans yok, koşulmadı.</b> Bu modelin gerçek yükleme listesi (Excel) yok; motorun çelik toplamı "
                 f"{sayi((o.get('liste') or {}).get('celik_kg'), 1)} kg hiçbir listeyle kıyaslanmadı. \"Kabul\" bu kapının yerine geçmez: kabul kaydına "
                 "\"metraj kapısı koşulmadı\" yazılır; gerçek liste gelince kıyas yapılır.</p>")
    elif mt.get("tanim_degisti"):                                         # tanım ölçümden sonra değişti, ölçüm bu tanım için geçerli değil
        s.append(f"<p><span class='kaldi'>beklemede</span> · çelik hakemi (İE-16), proje {e(mt.get('proje'))}: {e(mt.get('neden'))}. "
                 "Model beklemede, kabul edilemez (<code>metraj --celik</code> ve <code>ciz</code> yeniden koşulmalı).</p>")
    else:
        sinif = "gecti" if mt.get("durum") == "gecti" else "kaldi"
        yontem = (mt.get("yontem") or {}).get("ad") or "…"
        s.append(f"<p><span class='{sinif}'>{e(mt.get('hakem_sonucu'))}</span> · çelik hakemi (İE-16), proje {e(mt.get('proje'))}, sonuç "
                 f"{e(mt.get('sonuc_tarihi'))} · toplam çelik: bizim {sayi(mt.get('bizim_kapi_kg'), 1)} kg, gerçek liste {sayi(mt.get('gercek_kapi_kg'), 1)} kg, "
                 f"fark <b>{yuzde_html(mt.get('fark_yuzde'))}</b> (eşik ±%{sayi(mt.get('esik_yuzde'))})"
                 + (f" · kapı dışı: {e(', '.join(mt['kapi_disi']))} (gerçek listede kg yazılmamış)" if mt.get("kapi_disi") else "") + "</p>")
        if mt.get("turler"):
            s.append("<table><tr><th>Tür</th><th class='sag'>Bizim adet</th><th class='sag'>Liste adet</th><th class='sag'>Bizim kg</th>"
                     "<th class='sag'>Liste kg</th><th class='sag'>Fark</th></tr>")
            for r in mt["turler"]:
                b, g = r.get("bizim_kg"), r.get("gercek_kg")
                fark = yuzde_html(100 * (b - g) / g, 1) if b is not None and g else "kg yok" if g is None else "-"
                s.append(f"<tr><td>{e(r['ad'])}</td><td class='sag'>{e(r.get('bizim_adet') if r.get('bizim_adet') is not None else '-')}</td>"
                         f"<td class='sag'>{e(r.get('gercek_adet') if r.get('gercek_adet') is not None else '-')}</td>"
                         f"<td class='sag'>{sayi(b, 1) if b is not None else '-'}</td><td class='sag'>{sayi(g, 1) if g is not None else '-'}</td>"
                         f"<td class='sag'>{fark}</td></tr>")
            s.append("</table><p class='uyari'>Toplam kapıdan geçiyor; türlerin farkları birbirini götürüyor olabilir. Kabulünüzü tür satırlarına "
                     "bakarak verin.</p>")
        s.append(f"<p>Kapı projenin paftasındaki yöntemle ölçüldü ({e(yontem)}). Bayiye giden liste kitabın yöntemiyle (A, panel) çıkar "
                 f"(Lokman, 25 Ekim): onda çelik panel grubu <b>{sayi((o.get('liste') or {}).get('celik_kg'), 1)} kg</b>, çünkü tavan paneli ve makas "
                 "üstü çatı paneli A'da çelik panel grubundadır; B'de yerlerinde tavan omegası ve aşık vardır (çelik grubunun dışında). "
                 "Aşağıdaki liste özeti A'dır. Model ölçümdeki kural setiyle çizildi.</p>")
        if mt.get("durum") == "beklemede":
            s.append(f"<p class='kaldi'>Kapı geçmedi ({e(mt.get('neden'))}): model beklemede, kabul edilemez.</p>")
    s.append("</div>")
    lo = (o.get("liste") or {})
    s.append(f"<h2>Yükleme listesi özeti ({lo.get('satir', '…')} satır; kural seti {e(o.get('kural_seti'))})</h2><table><tr><th>Grup</th><th class='sag'>Satır</th>"
             "<th class='sag'>Çelik kg</th></tr>")
    for g, x in (lo.get("gruplar") or {}).items():
        s.append(f"<tr><td>{e(g)}</td><td class='sag'>{x['satir']}</td><td class='sag'>{sayi(x['kg'], 1) if x['kg'] else ''}</td></tr>")
    s.append(f"<tr><th>Toplam</th><th class='sag'>{lo.get('satir', '…')}</th><th class='sag'>{sayi(lo.get('celik_kg'), 1)}</th></tr></table>")
    return "".join(s)


def _sag(kart: dict) -> str:
    o = kart.get("olcum") or {}
    kd = kart.get("kaynak_degerleri") or {}
    ko = kd.get("odalar") or {}
    s = ["<h2>Oda tablosu</h2><p class='soluk'>Çizim sütunu genel motorun hesabıdır (kod, kaplanmış yüzler arası). Kaynak sütunu kaynakta yazan "
         "değerdir; yanında nereden geldiği yazar (kod, DXF, görsel okuma, Lokman).</p>",
         "<table><tr><th>Oda</th><th class='sag'>Çizim m²</th><th class='sag'>Kaynak m²</th><th class='sag'>Fark</th><th>Kaynağın kaynağı</th></tr>"]
    for ad in list(o.get("odalar") or {}) + [x for x in ko if x not in (o.get("odalar") or {})]:
        c = (o.get("odalar") or {}).get(ad); k = (ko.get(ad) or {}).get("deger")
        fark = sayi(c - k) if c is not None and k is not None else ""
        s.append(f"<tr><td>{e(ad)}</td><td class='sag'>{sayi(c) if c is not None else '-'}</td><td class='sag'>{sayi(k) if k is not None else '-'}</td>"
                 f"<td class='sag'>{fark}</td><td>{e((ko.get(ad) or {}).get('kaynak', 'kaynak değeri yok'))}</td></tr>")
    s.append("</table><h2>Öteki değerler</h2><table><tr><th>Değer</th><th>Çizim</th><th>Kaynak</th><th>Kaynağın kaynağı</th></tr>")
    for alan, ad, c in (("brut_m2", "Brüt oturum m²", sayi(o.get("oturum_m2"))), ("oda_programi", "Oda programı", o.get("oda_programi")),
                        ("pencere", "Pencere (adet)", o.get("pencere")), ("kapi", "Kapı (adet; dış + iç)", o.get("kapi")),
                        ("dis_olcu_cm", "Dış ölçü cm", sayi(o.get("dis_olcu_cm"))), ("cati_tipi", "Çatı tipi", (o.get("cati") or {}).get("tip"))):
        k = kd.get(alan) or {}
        kdeg = k.get("deger")
        s.append(f"<tr><td>{e(ad)}</td><td>{e(c)}</td><td>{e(sayi(kdeg) if isinstance(kdeg, (float, list)) else kdeg) if kdeg is not None else '-'}</td>"
                 f"<td>{e(k.get('kaynak', 'kaynak değeri yok'))}</td></tr>")
    s.append("</table><h2>Otomatik denetimler</h2><table><tr><th>Denetim</th><th>Sonuç</th><th>Ayrıntı</th></tr>")
    for d in (kart.get("son_cizim") or {}).get("denetimler") or []:
        s.append(f"<tr><td>{e(d['ad'])}</td><td class='{SINIF.get(d['durum'], '')}'>{e(d['durum'])}</td><td>{e(d['ayrinti'])}</td></tr>")
    s.append("</table>")
    if kart.get("duzeltmeler"):
        s.append("<h2>Düzeltmeler</h2><table><tr><th>Çizim</th><th>Tür</th><th>Düzeltme</th></tr>")
        for d in kart["duzeltmeler"]:
            s.append(f"<tr><td>{'c%02d' % d['cizim'] if d.get('cizim') else '-'}</td><td>{e(d['tur'])}</td><td>{e(d['metin'])}</td></tr>")
        s.append("</table>")
    if kart.get("taban_model"):
        s.append(f"<h2>Bayiye sunum</h2><p>Bu model {e(kart['taban_model'])}'in çatı varyantıdır: kabul edilince bankaya girer, ama bayiye bugünkü çatı "
                 "setinde (katalog çatısı, K, L; WhatsApp'ta üç düğme) çıkmaz. Dördüncü çatı seçeneği ayrı iştir.</p>")
    return "".join(s)


def _baslik(sayfa, metin: str, alt: str = "") -> None:
    import pymupdf
    sayfa.insert_htmlbox(pymupdf.Rect(24, 12, A4[0] - 24, 40), f"<p><b>{e(metin)}</b> <span class='soluk'>{e(alt)}</span></p>",
                         css="* {font-family: sans-serif; font-size: 9pt;} .soluk {color: #5d6670;}")


def _gorsel_sayfa(doc, yol: Path, baslik: str, alt: str = "") -> None:
    import pymupdf
    s = doc.new_page(width=A4[0], height=A4[1])
    _baslik(s, baslik, alt)
    s.insert_image(pymupdf.Rect(20, 40, A4[0] - 20, A4[1] - 16), filename=str(yol), keep_proportion=True)


def kontrol_pdf(kart: dict, cizim: Path, gk: str, hedef: Path) -> Path:
    """Kontrol sayfasını yazar; `cizim` motorun çıktı klasörü, `gk` dosya gövdesi (C8801D)."""
    import pymupdf
    sc = kart.get("son_cizim") or {}
    doc = pymupdf.open()
    s = doc.new_page(width=A4[0], height=A4[1])
    ust = (f"<h1>{e(kart['gosterim'])} · kontrol sayfası, çizim c{sc.get('no', 0):02d}</h1>"
           f"<p>{e(kart.get('ad'))} · {e(str(sc.get('zaman', ''))[:10])} · durum <b>{e(kart.get('durum'))}</b> · TASLAK: üretim projesi değildir · "
           f"kural seti {e((kart.get('olcum') or {}).get('kural_seti'))}</p>"
           "<div class='kutu'><p><b>Cevabınız:</b> uygunsa <b>kabul</b> yazın. Değilse düzeltmeyi düz cümleyle yazın (ör. \"mutfak penceresi "
           "120x120\", \"çatı eğimi %30\"); model yeniden çizilir ve yeni kontrol sayfası gelir.</p></div>")
    s.insert_htmlbox(pymupdf.Rect(24, 16, A4[0] - 24, 92), ust, css=CSS)
    s.insert_htmlbox(pymupdf.Rect(24, 96, 404, A4[1] - 16), _sol(kart), css=CSS)
    s.insert_htmlbox(pymupdf.Rect(416, 96, A4[0] - 24, A4[1] - 16), _sag(kart), css=CSS)
    pafta_png = cizim / f"{gk}_pafta.png"
    if pafta_png.exists():
        _gorsel_sayfa(doc, pafta_png, f"{kart['gosterim']} · çizim seti (mühendis paftası)", "plan, çatı planı, dört görünüş ve notlar; ölçüler cm")
    pafta_pdf = cizim / f"{gk}_pafta.pdf"
    if pafta_pdf.exists():
        with pymupdf.open(pafta_pdf) as p:
            doc.insert_pdf(p)
    gorsel = cizim / f"{gk}_bayi_gorsel.png"
    if gorsel.exists():
        pers = (sc.get("perspektif") or "")
        _gorsel_sayfa(doc, gorsel, f"{kart['gosterim']} · bayiye giden görsel (aday kartı)",
                      "" if pers == "TAMAM" else "bu ortamda perspektif çizilemiyor (VTK yok): perspektif yerine görünüşler")
    doc.set_metadata({"title": f"{kart['gosterim']} kontrol sayfası c{sc.get('no', 0):02d}", "creator": "Portman İE-09 atölyesi"})
    hedef.parent.mkdir(parents=True, exist_ok=True)
    doc.save(hedef, garbage=3, deflate=True)
    doc.close()
    return hedef


if __name__ == "__main__":                                                  # elle: python3 araclar/atolye_sayfa.py <kart.json> <çizim klasörü> <gövde> <hedef.pdf>
    import sys
    kontrol_pdf(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
