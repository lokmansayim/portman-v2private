"""İE-09 · Atölye kontrol sayfası (PDF; D-20): Lokman her modeli tek dosyada görür, "kabul" ya da düzeltmeyi düz cümleyle yazar.

Sayfa Lokman içindir ve sade Türkçeyle yazılır (Lokman, 30 Ekim 2026: "kartta çok terim var"; teknik denetimler, pim, kural seti,
hakemin ayrıntısı kartta ve kayıtta kalır, sayfaya girmez). Sayfalar (A4 yatay):
1. Bayiye ne gider (kabul bayiye bir şey göndermez; hangi sayfa bayiye gider), cevap biçimi; ev (kod, nereden, alan, oda sayısı,
   dış ölçü, çatı, pencere ve kapı), çelik ağırlığının mühendisin listesiyle kıyası (toplam ve parça parça; parçalar eşiği aşıyorsa
   uyarı), odalar (projede yazanla yan yana, varsa), projeyle karşılaştırma, bakmanız gerekenler (geçmeyen denetimlerin `sade`
   cümlesi), yükleme listesi özeti, düzeltmeler.
2. Mühendis paftası (`<kod>_pafta.png`: plan, çatı planı, dört görünüş, notlar; bayiye gitmez).
3–4. Bayiye giden pafta (Örnek Şablon, `<kod>_pafta.pdf`; antet "...", kişi ve bayi adı yok).
5. Bayiye giden WhatsApp görseli (`<kod>_bayi_gorsel.png`; aday kartı ve r01'in başlık görseli).

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


DURUM_ADI = {"taslak": "taslak (henüz çizilmedi)", "kontrolde": "onayınızı bekliyor", "beklemede": "bekletiliyor: çelik kıyası tutmadı",
             "kabul": "kabul edildi", "ret": "reddedildi"}


def _nereden(kart: dict) -> str:
    """Modelin nereden geldiği, düz cümleyle (kartın `kaynak`ı; teknik metin kayıtta kalır)."""
    k = kart.get("kaynak") or {}
    pk = str(k.get("proje") or "")
    if k.get("tur") == "varyant":
        s = f"{k.get('taban')} modelinin çatısı değişik hali (asıl model değişmedi)"
    elif k.get("tur") == "proje":
        s = f"Mühendisin projesi {pk}" if pk.startswith("ÇP") else f"AIPrefabrik projesi {pk}" if pk.startswith("AP") else "Gerçek proje"
        mt = kart.get("metraj_testi") or {}
        if mt.get("kaynak") == "celik_hakemi" and mt.get("proje") == pk:
            s += "; aynı ev, yalnız kodu ve adı değişti"          # metraj kapısı tanımın ölçülen tanımla aynı olmasını ister
    else:
        s = "Sizin isteğiniz" + (f": {k['metin']}" if k.get("metin") else "")
    return s + (". Bayiye müşteri adı gitmez." if kart.get("musteri_projesi") else "")


def _sol(kart: dict) -> str:
    o = kart.get("olcum") or {}
    cati = o.get("cati") or {}
    satirlar = [("Kod", f"{kart['gosterim']} (adını siz verirsiniz)"), ("Nereden", _nereden(kart)),
                ("Alan", f"{sayi(o.get('oturum_m2'))} m² (veranda {sayi(o.get('veranda_m2'))} m² dahil)"),
                ("Oda sayısı", o.get("oda_programi")),
                ("Dış ölçü", " × ".join(sayi(x / 100) for x in o.get("dis_olcu_cm") or []) + " m"),
                ("Çatı", f"{kart.get('cati_adi') or cati.get('tip')}; {cati.get('duzlem')} çatı yüzeyi, toplam {sayi(cati.get('yuzey_m2'))} m²"),
                ("Pencere · kapı", f"{o.get('pencere')} pencere · {o.get('kapi')} kapı (dış + iç)")]
    s = ["<h2>Ev</h2><table>"] + [f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in satirlar] + ["</table>"]
    mt = kart.get("metraj_testi") or {}
    s.append("<h2>Çelik ağırlığı: mühendisin listesiyle kıyas</h2><div class='kutu'>")
    if mt.get("durum") == "yok":
        s.append("<p>Bu modelin mühendis listesi yok; bizim çelik hesabımız "
                 f"({sayi((o.get('liste') or {}).get('celik_kg'), 1)} kg) hiçbir listeyle kıyaslanmadı. \"Kabul\"ünüz bu kıyasın yerine geçmez; "
                 "kayda \"kıyas yapılmadı\" yazılır. Mühendis listesi gelince kıyaslanır.</p>")
    elif mt.get("hakem_sonucu") is None:
        s.append("<p class='kaldi'>Bu çizim, mühendisin listesiyle kıyaslanan çizimden farklı (düzeltme yapıldı). Çelik kıyası bu çizim için "
                 "yeniden doğrulanmadan kabul edilemez.</p>")
    else:
        esik = float(mt.get("esik_yuzde") or 3)
        sonuc = ("<span class='gecti'>uygun</span>" if mt.get("durum") == "gecti"
                 else "<span class='kaldi'>uygun değil: model bekletiliyor, kabul edilemez</span>")
        s.append(f"<p>{e(mt.get('proje'))} projesinde bizim hesap <b>{sayi(mt.get('bizim_kapi_kg'), 1)} kg</b>, mühendisin listesi "
                 f"<b>{sayi(mt.get('gercek_kapi_kg'), 1)} kg</b>. Fark <b>{yuzde_html(mt.get('fark_yuzde'))}</b>; izin verilen ±%{sayi(esik)} → {sonuc}.</p>")
        turler = mt.get("turler") or []
        adlar = {r.get("tur"): r.get("ad") for r in turler}
        if mt.get("kapi_disi"):
            s.append(f"<p>{e(', '.join(adlar.get(x) or x for x in mt['kapi_disi']))}: mühendisin listesinde ağırlığı yazılı değil; kıyasa girmedi.</p>")
        buyuk = False
        if turler:
            s.append("<table><tr><th>Parça</th><th class='sag'>Bizim adet</th><th class='sag'>Mühendis adet</th><th class='sag'>Bizim kg</th>"
                     "<th class='sag'>Mühendis kg</th><th class='sag'>Fark</th></tr>")
            for r in turler:
                b, g = r.get("bizim_kg"), r.get("gercek_kg")
                fy = 100 * (b - g) / g if b is not None and g else None
                buyuk = buyuk or (fy is not None and abs(fy) > esik)
                fark = yuzde_html(fy, 1) if fy is not None else "ağırlık yok" if g is None else "-"
                s.append(f"<tr><td>{e(r['ad'])}</td><td class='sag'>{e(r.get('bizim_adet') if r.get('bizim_adet') is not None else '-')}</td>"
                         f"<td class='sag'>{e(r.get('gercek_adet') if r.get('gercek_adet') is not None else '-')}</td>"
                         f"<td class='sag'>{sayi(b, 1) if b is not None else '-'}</td><td class='sag'>{sayi(g, 1) if g is not None else '-'}</td>"
                         f"<td class='sag'>{fark}</td></tr>")
            s.append("</table>")
        if buyuk:
            s.append("<p class='uyari'>Dikkat: toplam tutuyor ama parçalar tek tek farklı. Bir parçadaki fazla, ötekindeki eksiği kapatıyor "
                     "olabilir. Onayınızı bu satırlara bakarak verin.</p>")
        if (mt.get("yontem") or {}).get("kod") == "omega_asik":
            s.append("<p>Kıyas, mühendisin projesindeki yapım şekliyle yapıldı: tavan omega profille, çatı aşıkla. Yükleme listesinde ise "
                     "(sizin 25 Ekim kararınız) tavan ve çatı da çelik panelle yapılır; bu yüzden sağdaki listede çelik "
                     f"<b>{sayi((o.get('liste') or {}).get('celik_kg'), 1)} kg</b> görünür.</p>")
    s.append("</div>")
    if kart.get("duzeltmeler"):
        s.append("<h2>Düzeltmeler</h2><table><tr><th>Çizim</th><th>Düzeltme</th></tr>")
        for d in kart["duzeltmeler"]:
            s.append(f"<tr><td>{d['cizim'] if d.get('cizim') else '-'}</td><td>{e(d['metin'])}</td></tr>")
        s.append("</table>")
    return "".join(s)


def _sag(kart: dict) -> str:
    o = kart.get("olcum") or {}
    kd = kart.get("kaynak_degerleri") or {}
    ko = kd.get("odalar") or {}
    odalar = o.get("odalar") or {}
    s = ["<h2>Odalar</h2><p class='soluk'>Alanlar duvarların iç yüzleri arasıdır.</p>"]
    if ko:
        s.append("<table><tr><th>Oda</th><th class='sag'>Çizimde m²</th><th class='sag'>Projede m²</th><th class='sag'>Fark</th><th>Nereden okundu</th></tr>")
        for ad in list(odalar) + [x for x in ko if x not in odalar]:
            c = odalar.get(ad); k = (ko.get(ad) or {}).get("deger")
            fark = sayi(c - k) if c is not None and k is not None else ""
            s.append(f"<tr><td>{e(ad)}</td><td class='sag'>{sayi(c) if c is not None else '-'}</td><td class='sag'>{sayi(k) if k is not None else '-'}</td>"
                     f"<td class='sag'>{fark}</td><td>{e((ko.get(ad) or {}).get('kaynak', 'projede yazmıyor'))}</td></tr>")
    else:
        s.append("<table><tr><th>Oda</th><th class='sag'>m²</th></tr>")
        s += [f"<tr><td>{e(ad)}</td><td class='sag'>{sayi(c)}</td></tr>" for ad, c in odalar.items()]
        s.append("</table><p class='soluk'>Projede oda alanları yazmıyor; yalnız çizimdeki alanlar var.")
    s.append("</table>" if ko else "</p>")
    degerler = (("brut_m2", "Toplam alan (m²)", sayi(o.get("oturum_m2"))), ("oda_programi", "Oda sayısı", o.get("oda_programi")),
                ("pencere", "Pencere", o.get("pencere")), ("kapi", "Kapı (dış + iç)", o.get("kapi")),
                ("dis_olcu_cm", "Dış ölçü (cm)", sayi(o.get("dis_olcu_cm"))), ("cati_tipi", "Çatı", (o.get("cati") or {}).get("tip")))
    yazan = [(alan, ad, c) for alan, ad, c in degerler if (kd.get(alan) or {}).get("deger") is not None]
    s.append("<h2>Projeyle karşılaştırma</h2>")
    if yazan:
        s.append("<table><tr><th>Değer</th><th>Çizimde</th><th>Projede</th><th>Nereden okundu</th></tr>")
        for alan, ad, c in yazan:
            k = kd[alan]
            kdeg = k["deger"]
            s.append(f"<tr><td>{e(ad)}</td><td>{e(c)}</td><td>{e(sayi(kdeg) if isinstance(kdeg, (float, list)) else kdeg)}</td>"
                     f"<td>{e(k.get('kaynak', ''))}</td></tr>")
        s.append("</table>")
    else:
        s.append("<p class='soluk'>Projeden karşılaştırılacak değer girilmedi.</p>")
    notlar = [d["sade"] for d in (kart.get("son_cizim") or {}).get("denetimler") or [] if d.get("sade") and d.get("durum") != "geçti"]
    s.append("<h2>Bakmanız gerekenler</h2>")
    s.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in notlar) + "</ul>" if notlar else "<p>Bilgisayarın kontrollerinde sorun çıkmadı.</p>")
    lo = (o.get("liste") or {})
    s.append(f"<h2>Yükleme listesi özeti ({lo.get('satir', '…')} kalem; mühendise gider, bayiye gitmez)</h2><table><tr><th>Grup</th>"
             "<th class='sag'>Kalem</th><th class='sag'>Çelik kg</th></tr>")
    for g, x in (lo.get("gruplar") or {}).items():
        s.append(f"<tr><td>{e(g)}</td><td class='sag'>{x['satir']}</td><td class='sag'>{sayi(x['kg'], 1) if x['kg'] else ''}</td></tr>")
    s.append(f"<tr><th>Toplam</th><th class='sag'>{lo.get('satir', '…')}</th><th class='sag'>{sayi(lo.get('celik_kg'), 1)}</th></tr></table>")
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
    pafta_png, pafta_pdf, gorsel = cizim / f"{gk}_pafta.png", cizim / f"{gk}_pafta.pdf", cizim / f"{gk}_bayi_gorsel.png"
    n_pafta = 0
    if pafta_pdf.exists():
        with pymupdf.open(pafta_pdf) as p:
            n_pafta = p.page_count
    no_muh = 2 if pafta_png.exists() else None
    ilk_bayi = 1 + (1 if no_muh else 0) + 1
    no_gorsel = ilk_bayi + n_pafta if gorsel.exists() else None
    bayi_sayfa = (f"sayfa {ilk_bayi}" if n_pafta == 1 else f"sayfa {ilk_bayi}–{ilk_bayi + n_pafta - 1}") if n_pafta else None
    if kart.get("taban_model"):
        bayi = (f"Bu model {e(kart['taban_model'])}'in çatısı değişik hali olduğu için bayiye ayrı seçenek olarak çıkmaz; bugünkü çatı "
                "seçenekleri (katalog, K, L) değişmez.")
    else:
        bayi = ("Bayiye gösterilmesi ayrıca sizin onayınızla olur. O zaman bayi seçenek olarak yalnız WhatsApp görselini"
                + (f" (sayfa {no_gorsel})" if no_gorsel else "") + " görür; bu evi seçerse bayi paftası"
                + (f" ({bayi_sayfa})" if bayi_sayfa else "") + " ve 3B görünüm bağlantısı gider.")
    doc = pymupdf.open()
    s = doc.new_page(width=A4[0], height=A4[1])
    ust = (f"<h1>{e(kart['gosterim'])} · kontrol sayfası (çizim {sc.get('no', 0)})</h1>"
           f"<p>{e(kart.get('ad'))} · {e(str(sc.get('zaman', ''))[:10])} · <b>{e(DURUM_ADI.get(kart.get('durum'), kart.get('durum')))}</b> · "
           "taslaktır, üretim projesi değildir</p>"
           f"<div class='kutu'><p><b>Bayiye ne gider?</b> Bu sayfa yalnız sizin için. \"Kabul\" yazmanız bayiye hiçbir şey göndermez: model önce "
           f"bankaya girer. {bayi} Mühendis paftası{f' (sayfa {no_muh})' if no_muh else ''}, çelik kıyası ve yükleme listesi bayiye gitmez.</p>"
           "<p><b>Cevabınız:</b> uygunsa <b>kabul</b> yazın. Değilse düzeltmeyi düz cümleyle yazın (ör. \"mutfak penceresi 120x120\", "
           "\"çatı eğimi %30\"); ev yeniden çizilir ve yeni kontrol sayfası gelir.</p></div>")
    s.insert_htmlbox(pymupdf.Rect(24, 16, A4[0] - 24, 110), ust, css=CSS)
    s.insert_htmlbox(pymupdf.Rect(24, 114, 404, A4[1] - 16), _sol(kart), css=CSS)
    s.insert_htmlbox(pymupdf.Rect(416, 114, A4[0] - 24, A4[1] - 16), _sag(kart), css=CSS)
    if no_muh:
        _gorsel_sayfa(doc, pafta_png, f"Sayfa {no_muh} · {kart['gosterim']} · mühendis paftası (bayiye gitmez)",
                      "plan, çatı planı, dört görünüş ve notlar; ölçüler cm")
    if n_pafta:
        with pymupdf.open(pafta_pdf) as p:
            doc.insert_pdf(p)
    if no_gorsel:
        pers = (sc.get("perspektif") or "")
        _gorsel_sayfa(doc, gorsel, f"Sayfa {no_gorsel} · {kart['gosterim']} · bayiye giden WhatsApp görseli",
                      "" if pers == "TAMAM" else "bu bilgisayarda 3B perspektif çizilemiyor; yerine görünüşler kondu")
    doc.set_metadata({"title": f"{kart['gosterim']} kontrol sayfası c{sc.get('no', 0):02d}", "creator": "Portman İE-09 atölyesi"})
    hedef.parent.mkdir(parents=True, exist_ok=True)
    doc.save(hedef, garbage=3, deflate=True)
    doc.close()
    return hedef


if __name__ == "__main__":                                                  # elle: python3 araclar/atolye_sayfa.py <kart.json> <çizim klasörü> <gövde> <hedef.pdf>
    import sys
    kontrol_pdf(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
