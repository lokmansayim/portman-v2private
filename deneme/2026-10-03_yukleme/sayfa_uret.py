#!/usr/bin/env python3
"""Ç8201 yükleme listesi taslağını okunur bir sayfaya (tek HTML dosyası) çevirir.

Sayılar `sonuc/` altındaki hesap çıktılarından alınır; elle yazılmaz. Önce `hepsini_kos.sh` koşulmalı.
Sayfa Claude'un artefakt biçimindedir (doctype, html, head, body etiketleri yok). Depoya çıktı yazılmaz.
Şimdilik Ç8201'e özgüdür: dosya adları, "değişenler", çatı açılımı ve "sizden beklenenler" metinleri bu modele göredir.
Sayfa Lokman'ın özel artefaktıdır ama paylaşılabilir; o yüzden kişi adı yazılmaz (mühendis "mühendis" diye geçer).

Kullanım:
    python sayfa_uret.py --cikti /tmp/C8201_yukleme_listesi.html --zaman "4 Ekim 2026 14:00"
"""
import argparse
import base64
import html
import json
from pathlib import Path

from motor_formul import BESIK_10, SABLON, motor_kaplama

S = Path(__file__).resolve().parent / "sonuc"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--cikti", type=Path, required=True)
ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
A = ap.parse_args()
baz = json.loads((S / "C8201_yukleme_taslak.json").read_text(encoding="utf-8"))
d140 = json.loads((S / "C8201_dis_karkas_140_yukleme_taslak.json").read_text(encoding="utf-8"))
KAPLAMALAR = [("Tek kat panel (baz paket)", baz, None)] + [
    (ad, json.loads((S / f"C8201_kaplama_{kod}.json").read_text(encoding="utf-8")), notu) for ad, kod, notu in (
        ("Sandviç panel", "sandvic_panel", None),
        ("OSB + nem bariyeri + kiremit desen sac", "osb_kiremit", "Motordaki adı: OSB + membran + metal kiremit"),
        ("OSB + nem bariyeri + trapez sac", "osb_trapez", "Gerçek listeyle karşılaştırılmadı"),
        ("Trapez sac", "trapez_sac", "Gerçek listeyle karşılaştırılmadı"),
        ("OSB + membran + shingle", "osb_shingle", "Yalnız motorun formülüyle; gerçek listeyle karşılaştırılmadı"))]

def tr(x, n=0):
    return f"{x:.{n}f}".replace(".", ",")

def e(s):
    return html.escape(str(s), quote=True)

# Sayfa bağlantıyla paylaşılabildiği için kişi adı taşımaz: hesap çıktısındaki notlarda geçen adlar okura hitaba ("siz") ya da role çevrilir.
SAYFA_DILI = (
    ("(Lokman, 4 Ekim düzeltmesi)", "(4 Ekim düzeltmeniz)"),
    ("Lokman makas ve kirişleri bir makas ölçüsünden ayrıca verecek", "makas ve kirişleri bir makas ölçüsünden ayrıca vereceksiniz"),
    ("Lokman'ın kuralı", "sizin kuralınız"), ("Lokman'ın", "sizin"), ("Lokman,", "siz,"), ("Lokman", "siz"),
    ("Ubeydullah'ın", "mühendisin"), ("Ubeydullah", "mühendis"),
)


def sayfa_dili(s):
    for eski, yeni in SAYFA_DILI:
        s = s.replace(eski, yeni)
    return s

DURUM = {
    "lokman": ("Sizin kuralınız", "ok", "Kuralı ya da değeri siz verdiniz"),
    "muhendis": ("Mühendisin kuralı", "ok", "Kuralı ya da değeri inşaat mühendisi verdi (3 ve 4 Ekim'de ilettiğiniz cevaplar)"),
    "excel": ("Liste formülü", "kaynak", "Gerçek yükleme listelerinin çalışma kitabındaki formül"),
    "motor": ("Excel motoru", "kaynak", "CTKBF V1.1'deki formül ya da proje ortalaması"),
    "model": ("Modelden", "kaynak", "Çizimdeki açıklıklardan sayıldı"),
    "uydurma": ("Listeye uyduruldu", "bekle", "Gerçek listelerdeki adedi tutturan kural; teyit bekliyor"),
    "varsayim": ("Varsayım", "bekle", "Benim varsayımım; teyit bekliyor"),
    "soru": ("Soru", "eksik", "Kural bilinmiyor; adet yok"),
    "bekliyor": ("Değer yok", "eksik", "Ölçü ya da sayım gelince hesaplanacak"),
}

def es(s):
    for x in d140["satirlar"]:
        if x["grup"] == s["grup"] and x["kalem"] == s["kalem"] and (x["boyut"] == s["boyut"] or s["grup"] == "Çelik panel"):
            if s["grup"] == "Çelik panel" and s["kalem"] == "Boy C profil" and x["boyut"] != s["boyut"]:
                continue
            return x
    return None

def olcu(s):
    return "" if s["olcu"] is None else f"{tr(s['olcu'], 1)} {s['birim']}"

gruplar = []
for s in baz["satirlar"]:
    if s["grup"] not in gruplar:
        gruplar.append(s["grup"])

ACIK = ("tahmin", "teyit bekliyor", "geçici", "priz sayısı bilinmediği", "katalog görsellerinden", "iki katı")


def bekleyen(s):
    return DURUM[s["durum"]][1] in ("bekle", "eksik") or any(k in (s.get("not") or "") for k in ACIK)


def satir_html(s):
    o = es(s)
    ad, sinif, _ = DURUM[s["durum"]]
    celik = s["grup"] == "Çelik panel"
    adet_baz = "" if s["adet"] is None else str(s["adet"])
    if celik:
        kg_baz = "" if s["kg"] is None else tr(s["kg"])
        if o is None:
            oteki = "—"
        else:
            parca = []
            if o["boyut"] != s["boyut"]:
                parca.append(e(o["boyut"]))
            if o["kg"] is not None and (o["kg"] != s["kg"] or o["boyut"] != s["boyut"]):
                parca.append(f"{tr(o['kg'])} kg")
            elif o["kg"] is None and o["olcu"] != s["olcu"]:
                parca.append(e(olcu(o)))
            oteki = " · ".join(parca) if parca else "aynı"
        hucre = f'<td class="say">{adet_baz}</td><td class="say">{kg_baz}</td><td class="oteki">{oteki}</td>'
    else:
        if o is None:
            oteki = "—"
        elif o["adet"] == s["adet"]:
            oteki = "aynı"
        else:
            oteki = f'<b>{o["adet"]}</b>'
        hucre = f'<td class="say">{adet_baz}</td><td class="oteki">{oteki}</td>'
    alt = []
    if s["olcu"] is not None:
        alt.append(e(olcu(s)))
    if s["formul"]:
        alt.append(e(sayfa_dili(s["formul"])))
    notu = f'<div class="not">{e(sayfa_dili(s["not"]))}</div>' if s.get("not") else ""
    return (f'<tr data-d="{"bekle" if bekleyen(s) else "tamam"}"><td class="kalem"><div class="ad">{e(s["kalem"])}</div><div class="alt">{" · ".join(alt)}</div>{notu}</td>'
            f'<td class="boyut">{e(s["boyut"])}</td>{hucre}<td><span class="rozet {sinif}" title="{e(DURUM[s["durum"]][2])}">{ad}</span></td></tr>')

bolumler = []
for g in gruplar:
    celik = g == "Çelik panel"
    bas = ("<tr><th>Kalem</th><th>Boyut</th><th class='say'>Adet</th><th class='say'>kg</th><th>Dış 140</th><th>Kaynak</th></tr>" if celik
           else "<tr><th>Kalem</th><th>Boyut</th><th class='say'>Baz</th><th>Dış 140</th><th>Kaynak</th></tr>")
    govde = "\n".join(satir_html(s) for s in baz["satirlar"] if s["grup"] == g)
    n = sum(1 for s in baz["satirlar"] if s["grup"] == g)
    bolumler.append(f'<section class="grup"><h2>{e(g)} <span class="sayac">{n} kalem</span></h2><div class="kaydir"><table class="{"celik" if celik else ""}"><thead>{bas}</thead><tbody>{govde}</tbody></table></div></section>')

def kap(v):
    return [s for s in v["satirlar"] if s["grup"] == "Çatı kaplamaları" or (s["grup"] == "Vida" and ("5,5 × 60" in s["kalem"] or "panel)" in s["kalem"] or "OSB ve yalıpan" in s["kalem"]))]

def dizilim_notu(v):
    """Kırma çatıda dizilimin duyarlı olduğu yerler (hesap çıktısından): başlangıç yeri, kesim payı, artan parçanın kullanılmaması."""
    z = v["ara"].get("kirma_dizilim")
    if not z:
        return None
    parca, den = [], z["baslangica_gore"]
    if len(set(den.values())) > 1:
        parca.append(f"Dizilim {z['baslangic_adi']} başlarsa {z['adet']}; her yüzde sol köşeden başlanırsa {den['sol']}")
    if z["paysiz_adet"] != z["adet"]:
        parca.append(f"Kesim payı sıfır alınırsa {z['paysiz_adet']}")
    if z["bir_cm_payla_adet"] != z["adet"]:
        parca.append(f"Kesim payı 1 cm alınırsa {z['bir_cm_payla_adet']}")
    if not z["artan_parca_karsi_yuzde"]:
        parca.append("Desen ters geldiği için artan parça karşı yüzde kullanılmaz (mühendis)")
    return ". ".join(parca) or None


def kap_tablo(ad, v, notu):
    r = "".join(f'<tr><td>{e(s["kalem"])}</td><td class="boyut">{e(s["boyut"])}</td><td class="say">{s["adet"]}</td></tr>' for s in kap(v))
    notlar = [x for x in (notu, dizilim_notu(v)) if x]
    alt = f'<p class="secenek-not">{e(". ".join(notlar))}</p>' if notlar else ""
    return f'<div class="secenek"><h3>{e(ad)}</h3><table><tbody>{r}</tbody></table>{alt}</div>'

def kg(v, kalem):
    return next(s["kg"] for s in v["satirlar"] if s["kalem"] == kalem)
def adet(v, kalem):
    return next(s["adet"] for s in v["satirlar"] if s["kalem"] == kalem)

toplam_baz, toplam_140 = kg(baz, "Toplam (adedi ve kg'ı bilinenler)"), kg(d140, "Toplam (adedi ve kg'ı bilinenler)")
_kars = [json.loads((S / f"ornek_{n}m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma_ozeti"] for n in (90, 62, 105)]
kars_toplam, kars_ayni = sum(x["karsilastirilan"] for x in _kars), sum(x["ayni"] for x in _kars)
toplam_satir = len(baz["satirlar"])
bekleyen_sayisi = sum(1 for s in baz["satirlar"] if bekleyen(s))

def satir(v, kalem):
    return next(s for s in v["satirlar"] if s["kalem"] == kalem)

# Mühendisin üçüncü cevaplarıyla (4 Ekim 12:14'te iletildi) değişenler.
# "Önce" değerleri yayımlanmış son sürümden (4 Ekim 02:58; commit 61d1996; sabit), "sonra" değerleri hesap çıktısından.
ONCE = {"kosebent": 51, "boardex": 33, "mahya_bandi": 3, "trapez_vida_25": 1000, "panel_boyu_mm": 4300, "tek_kat": 28, "sandvic": 24, "trapez": 30, "kiremit": 26}
K = json.loads((S.parent / "kurallar.json").read_text(encoding="utf-8"))
G = json.loads((S / "C8201_girdi.json").read_text(encoding="utf-8"))
kaplama = "".join(kap_tablo(ad, v, notu) for ad, v, notu in KAPLAMALAR)
assert baz["cati_kaplamasi_anahtar"] == K["baz_paket_cati_kaplamasi"]["deger"] == "tek_kat_panel", "sayfa metinleri baz kaplama tek kat panel diye yazıldı"
pk_t, pk_c = K["celik"]["tavan_paneli"]["deger"], K["celik"]["cati_paneli"]["deger"]
osb_s, kose_s = satir(baz, "OSB (TV ve mutfak dolabı arkası takviyesi)"), satir(baz, "Köşebent")
tp, cp = satir(baz, "Tavan paneli (makas arası)"), satir(baz, "Çatı paneli (makas üstü, sırt 80 mm)")
kap_s, bant_s, boardex_s = satir(baz, "Tek kat panel"), satir(baz, "Mahya bandı"), satir(baz, "Dış cephe Boardex")
dz = baz["ara"]["kirma_dizilim"]
kap_cm, boy_mm = round(dz["kapatma_m"] * 100), round(G["cati"]["panel_boyu_m"] * 1000)
k62 = json.loads((S / "ornek_62m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma"]["Sandviç panel"]
zb = K["zayiat"]["boardex"]["deger"]
tasma_cm, kesim_mm = K["cati_kaplama_tasma_m"]["deger"] * 100, K["kirma_cati_dizilim"]["deger"]["kesim_payi_m"] * 1000
boardex_15 = -(-boardex_s["olcu"] * 1.15 // K["levha_m2"]["boardex"]["deger"])      # önceki zayiatla (%15), yukarı
dis_kose = sum(o["dis_kose"] for o in G["odalar"])
sol_adet = dz["baslangica_gore"]["sol"]


def dz_oku(kod):
    return json.loads((S / f"C8201_kaplama_{kod}.json").read_text(encoding="utf-8"))["ara"]["kirma_dizilim"]


dz_s, dz_t, dz_k = dz_oku("sandvic_panel"), dz_oku("trapez_sac"), dz_oku("osb_kiremit")
# Sayfadaki sabit cümlelerin dayandığı durumlar; hesap değişirse sayfa üretilmez, metin gözden geçirilir.
assert kap_s["adet"] == dz["adet"] == ONCE["tek_kat"] and dz_k["adet"] == ONCE["kiremit"], "sayfa: tek kat panel ve kiremit desen sac adedi değişmedi diyor"
assert dz["baslangic"] != "sol" and sol_adet == dz["adet"] + 1, "sayfa: her yüzde sol köşeden başlanırsa bir panel fazla diyor"
assert dz["paysiz_adet"] == dz["bir_cm_payla_adet"] == dz["adet"], "sayfa: tek kat panelde adet kesim payından etkilenmiyor diyor"
assert dz["tasma_cm"] == tasma_cm == 5 and dz["kesim_payi_mm"] == kesim_mm == 5, "sayfa: taşma 5 cm, kesim payı 5 mm diyor"
assert not dz_k["artan_parca_karsi_yuzde"], "sayfa: kiremit desen sacda artan parça kullanılmıyor diyor"
assert adet(baz, "Saçaklar için Boardex") == 5 and adet(baz, "Saçak yüzü için Boardex") == 3, "sayfa: saçak Boardex'i değişmedi diyor"
_boyle = [json.loads((S / f"ornek_{n}m2_karsilastirma.json").read_text(encoding="utf-8"))["karsilastirma"]["Dış cephe Boardex"] for n in (90, 62, 105)]
assert all(2 <= b["liste"] - b["hesap"] <= 3 for b in _boyle), ("sayfa: %8 ile gerçek listelerden 2–3 levha az diyor", _boyle)

degisenler = [
    ("Çatı kaplaması saçaktan 5 cm taşıyor", f"Panel boyu L {ONCE['panel_boyu_mm']} → L {boy_mm} (eğimli boy + 5 cm). Tek kat panel yine {kap_s['adet']} adet; ama artık şu dizilimle: "
                                             f"{dz['baslangic_adi']}. Her yüzde sol köşeden başlanırsa {sol_adet} gerekiyor. "
                                             f"Seçeneklerde sandviç panel {ONCE['sandvic']} → {dz_s['adet']}, trapez sac {ONCE['trapez']} → {dz_t['adet']}."),
    ("Köşebent", f"Veranda tavanının çevresi eklendi: {ONCE['kosebent']} → {kose_s['adet']}. Odaya doğru çıkıntı yapan köşe sayılmıyor (zaten öyleydi). "
                 f"Köşebente bağlı trapez vida (5,5 × 25) {ONCE['trapez_vida_25']} → {adet(baz, 'Trapez vida (5,5 × 25)')}."),
    ("Boardex", f"Zayiat %15 → %{tr(zb * 100)}: dış cephe Boardex {ONCE['boardex']} → {boardex_s['adet']}. Saçak altı ve saçak yüzü aynı kaldı (5 ve 3). "
                "Satırlarda kalınlık yazıyor: Boardex 12,5 mm, OSB 11 mm. 2025'teki üç gerçek listenin adetleri %15'e uyuyor; %8 ile onlardan 2–3 levha az çıkıyor."),
    ("Mahya bandı", f"Mühendisin formülüyle (mahya adedi × 2,8 m ÷ 10 m): {ONCE['mahya_bandi']} → {bant_s['adet']} rulo. Damlalık listede olmadığı için sıfır alındı."),
    ("Dış kapı", "Boşluk 95 × 210: planda kapı 100 → 95 cm oldu, plan yeniden çizildi. Liste hesabı zaten 95 × 210 ileydi; adetler değişmedi."),
    ("Kiremit desen sac", f"Artan parçanın karşı yüzde kullanılmadığı teyit edildi (desen ters geliyor): {dz_k['adet']} adet; varsayım notu kalktı."),
    ("Teyit edilenler; hesap değişmedi", "Makas ve kirişler şimdilik Excel motorunun ortalamasıyla. Tek katta et kalınlığı 1,2 mm. "
                                         f"Tavan ve çatı paneli 100 m²'deki {pk_t['adet_100m2']} ve {pk_c['adet_100m2']} adetten oranla ({tp['adet']} ve {cp['adet']}). "
                                         f"OSB takviyesinde duvarın tamamı ({osb_s['adet']} levha). Buat kasada veranda hariç odalar; yatak odası ve banyoda tekli priz."),
    ("Excel motorundaki formül", "Yeniden okudum: hangi hücreden ne geldiği ve formülün nasıl işlediği aşağıda. Bulgu aynı: 0,8 paydanın parantezi dışında kaldığı için "
                                 "formül kapatma genişliğine bölmek yerine çarpıyor."),
    ("Bayi standartları", "Henüz oturmadığı için bütün gruplar (vida, boya, elektrik, tesisat) listede kalıyor."),
]
degisen_html = "".join(f"<li><b>{e(b)}.</b> {e(m)}</li>" for b, m in degisenler)

sorular = [
    ("Çatı dizilimi", f"Montaj ekibi dizilime nereden başlıyor? Listeye en az paneli veren dizilimi yazdım: {dz['baslangic_adi']}, {kap_s['adet']} panel. "
                      f"Her yüzde köşeden başlanırsa {sol_adet} gerekir. Ekip şemaya uymayacaksa {sol_adet} yazayım mı? Kesim payını {tr(kesim_mm)} mm aldım; uygun mu? "
                      f"Yedek panel eklenir mi: 62 m² gerçek listede (kırma çatı, sandviç panel) {k62['liste']} uzun ve 2 kısa panel var, aynı yöntem {k62['hesap']} veriyor."),
    ("Excel motorundaki formül", "Aşağıdaki bulguları mühendise iletir misiniz? Bir de kapatma genişliği: tek kat panel 87 cm mi (gerçek listeler ve montaj paftası), "
                                 "100 cm mi (Excel motoru)? Kiremit desen sac 110 mu, 105 mi? Liste 87 ve 110 ile hesaplıyor."),
    ("Boardex zayiatı", f"%{tr(zb * 100)} ile dış cephe Boardex {boardex_s['adet']} levha; 2025 listelerindeki oranla (%15) {tr(boardex_15)} olurdu. %{tr(zb * 100)} ile devam ediyorum; bilginiz olsun."),
    ("Damlalık", "Mahya bandı formülünde geçiyor; okuduğum listelerde yok, Excel motorunda adedi elle giriliyor. Hangi durumda listeye girer, adedi nasıl bulunur?"),
    ("Klima duvarı", "OSB takviyesinde sayılır mı? Gerçek listelerde kalemin adı \"TV, klima ve mutfak dolabı arkası\". Şimdi sayılmıyor."),
    ("Makas ve kiriş ölçüsü", f"Şimdilik Excel motorunun ortalamasıyla: makaslar {tr(kg(baz, 'Çatı makas panelleri'))} kg, veranda dikmeleri {tr(kg(baz, 'Veranda dikmeleri (kolon paneli)'))} kg, "
                              f"veranda kirişleri {tr(kg(baz, 'Veranda kirişleri (kiriş paneli)'))} kg. Bir makas ölçüsü verirseniz değişir."),
]
soru_html = "".join(f"<li><b>{e(b)}.</b> {e(m)}</li>" for b, m in sorular)

# Excel motorundaki kaplama formülü (mühendisin isteği: hangi hücreden ne geliyor, formül nasıl işliyor). Sayılar `motor_formul.py`'den.
uzun, kisa = G["kapali_olcu_m"]
mk_c = motor_kaplama(uzun, kisa, G["dis_olcu_m"][0] - uzun, "kirma")
assert mk_c["sac_boyu_mm"] == boy_mm, "sayfa: motorun sac boyu listedeki panel boyuyla aynı diyor"
HUCRELER = (("K10", "Bina dış uzun kenar (m)"), ("K11", "Bina dış kısa kenar (m)"), ("K13, K14", "Sundurma dış uzun ve kısa kenar"),
            ("K17", "Oturum dışı veranda dış kısa kenar"), ("K23", "Çatı tipi"), ("K24", "Çatı kaplama"))
hucre_html = "".join(f"<tr><td class='boyut'>{e(h)}</td><td>{e(a)}</td></tr>" for h, a in HUCRELER)
motor_bulgular = [
    ("Parantez", "Formülde yüzey ÷ sac boyu × 0,8 yazıyor. Excel bölmeyi ve çarpmayı soldan sağa yapar: sonuç (yüzey ÷ sac boyu) × 0,8 olur. "
                 "Anlatılan hesap (sac boyu × 0,8 = bir sacın kapattığı alan; yüzey ÷ o alan) için 0,8 paydanın parantezi içinde olmalı. "
                 "Şimdiki haliyle trapez sacda adet olması gerekenin 0,64 katı çıkıyor. Metal kiremitte 1,05 de aynı yerde: adet %10 fazla çıkıyor. "
                 "Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok."),
    ("Uzun kenarda saçak yok", "Yüzeyde kısa kenara 0,6 eklenmiş, uzun kenara (K10 + K17) eklenmemiş. Aynı sayfadaki çatı izolasyonu satırı uzun kenara da 0,6 ekliyor. "
                               f"10 × 10 m binada formülün yüzeyi {tr(BESIK_10['yuzey_m2'], 1)} m²; mühendisin kendi metrajında 118 m²."),
    ("Kapatma genişlikleri", "Motorda tek kat panel \"100 cm kapatır\", metal kiremit \"105 cm kapatır\" yazıyor. Gerçek listelerde ve montaj paftasında tek kat panel 87 cm, "
                             "kiremit desen sac 110 cm. Tek kat panelde motor bu yüzden %13 az verir."),
    ("Sac boyu hücresi (B61)", "Yalnız \"Trapez Saç\" seçiliyken hesaplıyor; \"OSB+Nem Bariyeri+Trapez Saç\" seçiliyken 0 gösteriyor. "
                               "Trapez vida (5,5 × 60) formülü sac boyunu bu hücreden aldığı için o seçenekte sacın vidası hesaba girmiyor."),
]
motor_bulgu_html = "".join(f"<li><b>{e(b)}.</b> {e(m)}</li>" for b, m in motor_bulgular)
motor_ornekler = [
    ("Motorun şablonundaki kayıtlı örnek (9,74 × 7,44; veranda 2,12; dört omuz)", SABLON, f"Hücrede kayıtlı metal kiremit adedi {SABLON['yazilan']['kiremit']}"),
    ("10 × 10 m beşik çatı", BESIK_10, "Mühendisin metrajında 28 trapez sac var (her saçakta 10,6 ÷ 0,8 → 14). Düzeltilince kalan fark uzun kenara eklenmeyen saçaktan ve her saçağın ayrı yuvarlanmasından"),
    (f"Ç8201 (K10 {tr(uzun, 2)}; K11 {tr(kisa, 2)}; K17 {tr(G['dis_olcu_m'][0] - uzun, 2)}; dört omuz)", mk_c,
     f"Çatı açılımı trapez sacda {dz_t['adet']}, kiremit desen sacda {dz_k['adet']} veriyor. Tek kat panelde motor {mk_c['yazilan']['panel']} verir (87 cm ile {mk_c['tek_kat_87']}); açılım {dz['adet']}"),
]
motor_ornek_html = "".join(
    f"<tr><td>{e(ad)}<div class='alt'>Yüzey {tr(m['yuzey_m2'], 1)} m² ÷ sac boyu {tr(m['sac_boyu_m'], 3)} m = {tr(m['oran'], 2)}. {e(notu)}.</div></td>"
    f"<td class='say'>{m['yazilan']['trapez']} → {m['duzeltilmis']['trapez']}</td><td class='say'>{m['yazilan']['kiremit']} → {m['duzeltilmis']['kiremit']}</td></tr>"
    for ad, m, notu in motor_ornekler)
motor_html = f'''<section>
  <h2>Excel motorundaki kaplama formülü</h2>
  <p class="aciklama" style="margin-bottom:10px">Mühendisin isteği üzerine motorun MALZEMELER sayfasını yeniden okudum: hangi hücreden ne geliyor, formül nasıl işliyor. Yapıştırılan formül 61. satırdaki trapez sac formülü; aynı ifade tek kat panel (64), sandviç panel (67) ve metal kiremit (72) satırlarında da var.</p>
  <div class="kaydir"><table class="dar hucre"><thead><tr><th>Hücre</th><th>Ne</th></tr></thead><tbody>{hucre_html}</tbody></table></div>
  <ul class="degisen" style="margin-top:12px">
    <li><b>Çatı yüzeyi</b> = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14. Kısa kenara iki saçak eklenir, %33 eğimle eğimli genişliğe çevrilir, uzun kenarla (veranda dahil) çarpılır; sundurma düz alanıyla eklenir.</li>
    <li><b>Sac boyu</b> = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05: saçaktan mahyaya eğimli boy + 5 cm taşma.</li>
    <li><b>Adet</b> = yüzey ÷ sac boyu × kaplama katsayısı (trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05) × çatı katsayısı (dört omuzda 1,06), yukarı yuvarlanır.</li>
  </ul>
  <h3 style="margin-top:16px">Bulgular</h3>
  <ol class="sorular">{motor_bulgu_html}</ol>
  <h3 style="margin-top:16px">Düzeltme</h3>
  <p class="aciklama" style="margin-bottom:8px">Trapez sac için formülün ilgili yeri (metal kiremitte 0,8 yerine 1,05):</p>
  <div class="formul">
    <div><span class="etiket">Şimdi</span><code>…+(K13*K14))/(((K11+0,6)/2)*KAREKÖK(1+0,33^2)+0,05)<b>*0,8</b></code></div>
    <div><span class="etiket">Olması gereken</span><code>…+(K13*K14))/<b>(</b>(((K11+0,6)/2)*KAREKÖK(1+0,33^2)+0,05)<b>*0,8)</b></code></div>
  </div>
  <h3 style="margin-top:16px">Örnekler: formül yazıldığı gibi → parantez düzeltilince</h3>
  <div class="kaydir"><table class="dar"><thead><tr><th>Örnek</th><th class="say">Trapez sac</th><th class="say">Metal kiremit</th></tr></thead><tbody>{motor_ornek_html}</tbody></table></div>
  <p class="aciklama" style="margin-top:10px">Bu liste kaplama adedini motorun formülünden almıyor; çatı açılımından alıyor. Motorun sac boyu Ç8201'de {mk_c["sac_boyu_mm"]} mm: listedeki L {boy_mm} ile aynı.</p>
</section>'''

# Plan görseli (OSB takviyesi gelen duvarlar turuncu çizgili): çizim denemesinin son çıktısı, sayfanın içine gömülür.
_plan = S.parents[1] / "2026-10-02_celik" / "sonuc" / "C8201_plan.png"
plan_html = ""
if _plan.is_file():
    plan_html = ('<section><h2>Plan</h2><p class="aciklama" style="margin-bottom:10px">OSB takviyesi gelen duvarlar turuncu çizgiyle işaretli; '
                 'kesik çizgi veranda kirişi, siyah kutular dikmeler.</p><div class="plan"><img alt="Ç8201 planı: beş mahal ve veranda; OSB takviyesi gelen üç duvar turuncu çizgiyle işaretli" '
                 f'src="data:image/png;base64,{base64.b64encode(_plan.read_bytes()).decode("ascii")}"></div></section>')

def gorsel(yol: Path, alt: str) -> str:
    return f'<div class="plan"><img alt="{e(alt)}" src="data:image/png;base64,{base64.b64encode(yol.read_bytes()).decode("ascii")}"></div>'


_acilim, _kesim = S / "C8201_cati_acilim.png", S / "C8201_cati_kesim.png"
acilim_html = ""
if _acilim.is_file() and _kesim.is_file():
    acilim_notlari = [
        f"Tek kat panel: {kap_s['adet']} adet L {boy_mm} ({dz['tam_boy']} tam boy + {dz['kesilen']} kesilen). Çatı yüzeyi alan olarak en az {dz['alan_alt_siniri']} panel ediyor.",
        f"Kaplama saçaktan {tr(tasma_cm)} cm taşıyor (mühendisin cevabı): panel boyu = eğimli boy {tr(dz['egimli_boy_m'] * 100, 1)} cm + {tr(tasma_cm)} cm.",
        f"Dizilim {dz['baslangic_adi']} başlıyor. Altı başlangıcı denedim; en az paneli veren bu. Her yüzde sol köşeden başlanırsa {sol_adet} panel gerekiyor.",
        f"Kesim payı {tr(kesim_mm)} mm (varsayımım). Tek kat panelde adet bundan etkilenmiyor: sıfır da olsa 1 cm de olsa {kap_s['adet']}.",
        "Aynı kuralı ayrı bir hesapla da denetledim (taşma ve kesim payıyla yeniden): aynı adetler çıktı; bu dizilimde daha az panelle olmuyor.",
        f"62 m² gerçek listede (kırma çatı, sandviç panel) {k62['liste']} adet L 3200 ve 2 adet L 1000 var; aynı yöntem {k62['hesap']} veriyor.",
        "Boy bindirmesi ve yedek panel yok.",
    ]
    acilim_html = ('<section><h2>Çatı açılımı ve kaplama dizilimi</h2>'
                   f'<p class="aciklama" style="margin-bottom:10px">Çatı mahyadan dışarı doğru açıldı; dört yüz gerçek boyutunda. Paneller saçaktan mahyaya, {kap_cm} cm\'lik şeritler halinde; saçaktan {tr(tasma_cm)} cm taşıyor. '
                   'Sayı panel numarası: aynı numara iki yüzde görünüyorsa iki parça aynı panelden çıkıyor.</p>'
                   + gorsel(_acilim, f"Ç8201 çatı açılımı: iki yamuk ve iki üçgen yüz, {kap_cm} cm'lik şeritlere bölünmüş; her parçada panel numarası; toplam {kap_s['adet']} panel")
                   + '<p class="aciklama" style="margin-block:14px 10px">Kesim planı: her dikdörtgen bir panel. Yeşil parça olduğu gibi kullanılır; turuncu parça, düz ucu saçağa gelecek biçimde karşı yüze konur.</p>'
                   + gorsel(_kesim, f"Ç8201 kesim planı: {kap_s['adet']} panelin her biri; {dz['tam_boy']} panel tam boy, {dz['kesilen']} panel çapraz kesilip iki yüze paylaştırılıyor")
                   + '<ul class="degisen" style="margin-top:12px">' + "".join(f"<li>{e(x)}</li>" for x in acilim_notlari) + "</ul></section>")

kullanilan = {s["durum"] for s in baz["satirlar"]}
lejant = "".join(f'<li><span class="rozet {v[1]}">{v[0]}</span><span>{e(v[2])}</span></li>' for k, v in DURUM.items() if k in kullanilan)

sayfa = f"""<title>Ç8201 Yükleme Listesi</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Düzen: sevk listesi gibi tek sütun; üstte künye ve özet, altında grup grup tablolar. Sayılar eş aralıklı yazıyla sağa hizalı. */
:root {{
  --zemin: #f3f5f6; --kagit: #ffffff; --yazi: #17212b; --soluk: #5b6875; --cizgi: #d5dbe0; --vurgu: #1f5f7a;
  --ok-z: #dff1e6; --ok-y: #1c6b3c; --kay-z: #e3ebf2; --kay-y: #2f4a63; --bek-z: #fdebc8; --bek-y: #7a4d00; --eks-z: #f8d9d6; --eks-y: #8a2118;
  --cizim-z: #ffffff; /* çizimin kendi zemini beyaz: iki temada da beyaz kalır */
  --sans: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }}
body {{ background: var(--zemin); color: var(--yazi); font-family: var(--sans); font-size: 15px; line-height: 1.5; }}
.sayfa {{ max-width: 980px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: flex; flex-direction: column; gap: 26px; }}
header {{ display: flex; flex-direction: column; gap: 10px; }}
.kunye {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
h1 {{ font-size: clamp(24px, 4.6vw, 34px); line-height: 1.15; margin: 0; font-weight: 600; text-wrap: balance; }}
.aciklama {{ color: var(--soluk); max-width: 68ch; margin: 0; }}
.taslak {{ display: inline-block; font-family: var(--mono); font-size: 12px; border: 1px solid var(--bek-y); color: var(--bek-y); padding: 2px 8px; border-radius: 3px; letter-spacing: .05em; }}
.ozet {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--cizgi); border: 1px solid var(--cizgi); }}
.ozet div {{ background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 8px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; display: flex; align-items: baseline; gap: 10px; }}
h2 .sayac {{ font-family: var(--mono); font-size: 11.5px; font-weight: 400; color: var(--soluk); letter-spacing: 0; text-transform: none; }}
h3 {{ font-size: 14px; margin: 0 0 6px; font-weight: 600; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 620px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); }}
tbody tr:last-child td {{ border-bottom: 0; }}
th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; white-space: nowrap; }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
.boyut {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); white-space: nowrap; }}
.oteki {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); }}
.oteki b {{ color: var(--yazi); font-weight: 500; font-size: 15px; }}
.kalem {{ min-width: 240px; }}
.ad {{ font-weight: 500; }}
.alt {{ font-size: 12.5px; color: var(--soluk); max-width: 62ch; }}
.not {{ font-size: 12.5px; color: var(--bek-y); max-width: 62ch; }}
.rozet {{ display: inline-block; font-size: 11.5px; padding: 2px 8px; border-radius: 10px; white-space: nowrap; font-weight: 500; }}
.rozet.ok {{ background: var(--ok-z); color: var(--ok-y); }}
.rozet.kaynak {{ background: var(--kay-z); color: var(--kay-y); }}
.rozet.bekle {{ background: var(--bek-z); color: var(--bek-y); }}
.rozet.eksik {{ background: var(--eks-z); color: var(--eks-y); }}
.suzgec {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
.suzgec button {{ font: inherit; font-size: 13.5px; padding: 6px 12px; border: 1px solid var(--cizgi); background: var(--kagit); color: var(--yazi); border-radius: 4px; cursor: pointer; }}
.suzgec button[aria-pressed="true"] {{ background: var(--vurgu); border-color: var(--vurgu); color: var(--kagit); }}
.suzgec button:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
.lejant {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 6px 18px; font-size: 13px; color: var(--soluk); }}
.lejant li {{ display: flex; gap: 8px; align-items: baseline; }}
.secenekler {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; }}
.secenek {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 12px 14px; min-width: 0; }}
.secenek table {{ min-width: 0; }}
.secenek td {{ padding: 5px 0; font-size: 13.5px; }}
.secenek td.boyut {{ padding-inline: 8px; white-space: normal; }}
.secenek-not {{ margin: 8px 0 0; font-size: 12.5px; color: var(--bek-y); }}
.degisen {{ margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; max-width: 76ch; }}
table.dar {{ min-width: 0; }}
table.hucre td:first-child, table.hucre th:first-child {{ width: 92px; }}
.formul {{ background: var(--kagit); border: 1px solid var(--cizgi); padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }}
.formul > div {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.formul code {{ font-family: var(--mono); font-size: 12.5px; overflow-wrap: anywhere; }}
.formul code b {{ background: var(--bek-z); color: var(--bek-y); font-weight: 500; padding: 0 2px; border-radius: 2px; }}
.formul .etiket {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
.plan {{ background: var(--cizim-z); border: 1px solid var(--cizgi); padding: 8px; }}
.plan img {{ display: block; width: 100%; height: auto; }}
.sorular {{ margin: 0; padding-left: 28px; display: flex; flex-direction: column; gap: 8px; max-width: 76ch; }}
.dip {{ font-size: 12.5px; color: var(--soluk); max-width: 76ch; }}
[data-gizli] {{ display: none; }}
@media (max-width: 560px) {{ .ozet {{ grid-template-columns: 1fr 1fr; }} .ozet div:last-child {{ grid-column: 1 / -1; }} }}
</style>
<div class="sayfa" lang="tr">
<header>
  <div class="kunye">PortatifEv · Portman · İE-05 · {e(A.zaman)}</div>
  <h1>Ç8201 yükleme listesi</h1>
  <p class="aciklama">Tek kat çelik, 2+1, 82 m². Çatı: kırma, çatı ve tavan panelli yöntem; kaplama baz paketteki tek kat panel. Her sayının yanında nereden geldiği yazıyor.</p>
  <div><span class="taslak">TASLAK · ÜRETİM LİSTESİ DEĞİLDİR</span></div>
</header>

<div class="ozet">
  <div><b>{tr(toplam_baz)} kg</b><span>Çelik, baz paket (tavan ve çatı paneli dahil)</span></div>
  <div><b>{tr(toplam_140)} kg</b><span>Çelik, dış 140 (duvarlar 1,2 mm: mühendisin kuralı)</span></div>
  <div><b>{adet(baz, "Dış cephe Boardex")} + {adet(baz, "Saçaklar için Boardex")} + {adet(baz, "Saçak yüzü için Boardex")}</b><span>Boardex: cephe, saçak altı, saçak yüzü</span></div>
  <div><b>{adet(baz, "Duvar alçıpan beyaz") + adet(baz, "Tavan alçıpan beyaz")} + {adet(baz, "Duvar alçıpan yeşil") + adet(baz, "Tavan alçıpan yeşil")}</b><span>Alçıpan: beyaz + yeşil</span></div>
  <div><b>{bekleyen_sayisi} / {toplam_satir}</b><span>Teyit ya da değer bekleyen satır</span></div>
</div>

<section>
  <h2>4 Ekim 12:14'te ilettiğiniz on iki cevapla değişenler</h2>
  <ul class="degisen">{degisen_html}</ul>
</section>

<section>
  <h2>Kaynak işaretleri</h2>
  <ul class="lejant">{lejant}</ul>
</section>

<div class="suzgec" role="group" aria-label="Satırları süz">
  <button type="button" id="s-hepsi" aria-pressed="true">Bütün satırlar</button>
  <button type="button" id="s-bekle" aria-pressed="false">Yalnız teyit ya da değer bekleyenler</button>
</div>

{chr(10).join(bolumler)}

{acilim_html}

<section>
  <h2>Çatı kaplaması seçenekleri</h2>
  <p class="aciklama" style="margin-bottom:10px">Baz pakette tek kat panel var (4 Ekim düzeltmeniz). Altı seçenek Excel motorundaki listeden; seçeneğe göre değişen kalemler:</p>
  <div class="secenekler">{kaplama}</div>
</section>

{plan_html}

{motor_html}

<section>
  <h2>Sizden beklenenler</h2>
  <ol class="sorular">{soru_html}</ol>
</section>

<p class="dip">Kaynaklar: 3 Ekim 13:27 cevaplarınız, 4 Ekim 01:24 ve 01:42 düzeltmeleriniz; inşaat mühendisinin üç tur cevabı (3 Ekim 18:14, 4 Ekim 01:24 ve 12:14'te ilettiniz); üç gerçek yükleme listesinin çalışma kitapları (62, 90 ve 105 m²); Excel hesaplama motoru (CTKBF V1.1). Bu modelin kendi gerçek listesi yok: sayılar yalnız kurallardan çıkıyor. Üç gerçek listeyle karşılaştırmada {kars_toplam} kalemin {kars_ayni} tanesinde adet aynı; bu bir sınama değil, çünkü katsayıların bir kısmı o listelere bakılarak seçildi. Ayrıntı depoda: docs/sartname/yukleme_listesi_yontemi.md.</p>
</div>
<script>
(function () {{
  var hepsi = document.getElementById('s-hepsi'), bekle = document.getElementById('s-bekle');
  function uygula(yalniz) {{
    document.querySelectorAll('tr[data-d]').forEach(function (tr) {{
      var d = tr.getAttribute('data-d');
      if (yalniz && d !== 'bekle') tr.setAttribute('data-gizli', ''); else tr.removeAttribute('data-gizli');
    }});
    document.querySelectorAll('section.grup').forEach(function (s) {{
      var gorunen = s.querySelectorAll('tbody tr:not([data-gizli])').length;
      if (gorunen === 0) s.setAttribute('data-gizli', ''); else s.removeAttribute('data-gizli');
    }});
    hepsi.setAttribute('aria-pressed', String(!yalniz));
    bekle.setAttribute('aria-pressed', String(yalniz));
  }}
  hepsi.addEventListener('click', function () {{ uygula(false); }});
  bekle.addEventListener('click', function () {{ uygula(true); }});
}})();
</script>
"""
for ad in ("Lokman", "Ubeydullah"):   # sayfada kişi adı kalmamalı
    if ad in sayfa:
        raise SystemExit(f"Sayfada kişi adı kaldı: {ad}")
A.cikti.write_text(sayfa, encoding="utf-8")
print("yazıldı:", A.cikti, "·", toplam_satir, "satır; teyit ya da değer bekleyen", bekleyen_sayisi)
