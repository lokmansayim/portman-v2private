#!/usr/bin/env python3
"""KT-01'in kararlardan sonraki durumunu okunur tek bir sayfaya (kendi başına HTML dosyası) çevirir.

Sayılar ve satır açıklamaları `sonuc/KT01_kararlar_kiyas.json`'dan (`kararlar_kiyas.py` çıktısı), "sizden beklenenler" yöntem belgesinin
açık sorularından (`docs/sartname/yukleme_listesi_yontemi.md`; baştaki `SORU_ADEDI` madde) okunur; elle yazılmaz. Önce `kararlar_kos.sh` koşulmalı.
Sayfada kişi, bayi ve firma adı, telefon ve fiyat yoktur. Çıktı depoya yazılmaz; Lokman'a dosya olarak verilir.

Kullanım:
    python kararlar_sayfa.py --cikti /tmp/KT01_kararlardan_sonra.html --zaman "7 Ekim 2026 10:00"
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

BURADA = Path(__file__).resolve().parent
BELGE = BURADA.parents[1] / "docs" / "sartname" / "yukleme_listesi_yontemi.md"
SORU_ADEDI = 3          # açık soruların başındaki, Lokman'dan cevap beklenen maddeler (kalkan kenarı üst kapaması; parça C profil; özel mahyanın ayrıntıları)
TUR = {"karar": ("kararınız farklı", "ok", "kararınız o listeden farklı"), "yöntem": ("yöntem", "kaynak", "liste omega ve aşıklı yöntemle hazırlanmış; çelikte artık yok"),
       "elle": ("elle (liste)", "kaynak", "listenin elle hesabı, yuvarlaması ya da elle dizilimi"), "ölçü": ("ölçünün yeri", "kaynak", "ölçünün alındığı yüz; kararınız: bizdeki"),
       "soru": ("soru", "bekle", "kural bekliyor")}
# Sayfa kişi adı taşımaz: açıklamalardaki adlar okura hitaba çevrilir.
SAYFA_DILI = (("Lokman'ın kararı", "kararınız"), ("Lokman'ın", "sizin"), ("Lokman,", "siz,"), ("Lokman", "siz"))
DURUM = {"lokman": "sizin kuralınız", "muhendis": "mühendisin kuralı", "uydurma": "listeye uyduruldu; teyit bekliyor", "soru": "soru: cevabınızı bekliyor"}


def e(s) -> str:
    return html.escape(str(s), quote=True)


def dil(s: str) -> str:
    for eski, yeni in SAYFA_DILI:
        s = s.replace(eski, yeni)
    return s


def md(s: str) -> str:
    """Satır içi biçim: **kalın** ve `kod`."""
    s = e(dil(s))
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def n(v) -> str:
    return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else str(v).replace(".", ","))


def acik_sorular(metin: str) -> list[str]:
    a = metin.index("## Açık sorular")
    b = metin.index("Kapananlar:", a)
    return [re.sub(r"^\d+\.\s+", "", x) for x in metin[a:b].split("\n") if re.match(r"^\d+\.\s", x)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cikti", type=Path, required=True)
    ap.add_argument("--zaman", required=True, help="künyede görünecek tarih ve saat")
    ap.add_argument("--kiyas", type=Path, default=BURADA / "sonuc" / "KT01_kararlar_kiyas.json")
    ap.add_argument("--belge", type=Path, default=BELGE)
    a = ap.parse_args()
    k = json.loads(a.kiyas.read_text(encoding="utf-8"))
    if k["denetim_sorunlari"]:
        raise SystemExit("Kıyasta denetim sorunu var; sayfa üretilmez: " + "; ".join(k["denetim_sorunlari"][:3]))
    B, oz, on, ck, ft = k["birimler"], k["ozet"], k["onceki"], k["celik_kg"], k["fark_turleri"]
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    toplam = oz["b"]["gercek_satir"]
    sorular = acik_sorular(a.belge.read_text(encoding="utf-8"))[:SORU_ADEDI]
    if (len(sorular) != SORU_ADEDI or not sorular[0].startswith("**Kalkan kenarında") or not sorular[1].startswith("**Trapez vidada parça C profil")
            or not sorular[2].startswith("**Özel mahyanın ayrıntıları")):
        raise SystemExit("Yöntem belgesindeki açık soruların başı beklenen sırada değil (kalkan kenarı, trapez vidada parça C profil, özel mahyanın ayrıntıları); önce belge_uret.py, sonra SORU_ADEDI.")

    ozet = (f'<div><b>{on["duzeltilmis"]}<small> / {toplam}</small></b><span>Kararlardan önce (7 Ekim 03:46): yalnız bizim hatalarımız düzeltilmişti</span></div>'
            f'<div><b>{oz["b"]["ayni"]}<small> / {toplam}</small></b><span>Kararlarınızdan sonra, projenin yapıldığı yöntemle (tavan omegası ve aşık)</span></div>'
            f'<div><b>{oz["a"]["ayni"]}<small> / {toplam}</small></b><span>Kararlarınızdan sonra, çelik standardıyla (çatı ve tavan paneli)</span></div>'
            f'<div><b>{n(round(ck["a"]))}<small> / {n(round(ck["gercek"]))} kg</small></b><span>Çelik: çelik standardıyla / gerçek liste (tavan ve çatı panelleri eklenir)</span></div>')
    kalan = toplam - oz["b"]["ayni"]
    lejant = "".join(f'<li><span class="rozet {TUR[t][1]}">{e(TUR[t][0])}</span> {ft[t]} satır: {e(TUR[t][2])}</li>' for t in TUR if ft[t])

    paftadan = lambda b: b["karar_turu"] == "pafta"
    degisen_karar, degisen_pafta = k["degisen"]["karar"], k["degisen"]["pafta"]
    yt = k["yeni_tutan"]
    if yt["toplam"] != oz["b"]["ayni"] - on["duzeltilmis"] or yt["bozulan"]:
        raise SystemExit("Sayfa 'önce tutan hiçbir satır bozulmadı' diyor; kıyas öyle değil.")
    kazanc_toplam, kazanc_pafta, kazanc_inis = yt["toplam"], yt["pafta"], yt["inis"]
    govde, grup = [], None
    for b in B:
        if b["grup"] != grup:
            grup = b["grup"]
            govde.append(f'<tr class="grup"><th colspan="5">{e(grup)}</th></tr>')
        etiket = []
        if b["karar"]:      # adedi 03:46'daki düzeltilmiş listeden farklı: kararla ya da elektrik sayıları paftadan alındığı için
            etiket.append('<span class="rozet kaynak">paftadan</span>' if paftadan(b) else '<span class="rozet ok">kararla değişti</span>')
        if b["fark_turu"]:
            etiket.append(f'<span class="rozet cizgili">{e(TUR[b["fark_turu"]][0])}</span>')
        if b["b_ayni"] and not b["karar"]:
            etiket.append('<span class="rozet kaynak">tutuyordu</span>')
        if len(b["gercek_satirlar"]) > 1:
            etiket.append(f'<span class="cok">gerçek listede {len(b["gercek_satirlar"])} satır</span>')
        aciklama = "".join(f'<p class="alt"><b>{bas}</b> {md(b[alan])}</p>' for bas, alan in (("Değişikliği doğuran:", "karar"), ("Hâlâ farklı:", "fark")) if b.get(alan))
        hucre = (f'<td class="say{"" if b["duzeltilmis_ayni"] else " fark"}">{n(b["duzeltilmis"])}</td>'
                 f'<td class="say{"" if b["b_ayni"] else " fark"}">{n(b["b"])}</td>'
                 f'<td class="say{"" if b["a_ayni"] or b["a"] is None else " fark"}">{n(b["a"])}</td>')
        veri = f'data-degisen="{int(bool(b["karar"]))}" data-kalan="{int(not b["b_ayni"])}" data-tutan="{int(b["b_ayni"])}"'
        govde.append(f'<tr {veri}><td class="kalem"><span class="ad">{e(b["ad"])}</span> {" ".join(etiket)}{aciklama}</td>'
                     f'<td class="say gercek">{n(b["gercek"])}</td>{hucre}</tr>')
    say = {"hepsi": satir(B), "degisen": satir([b for b in B if b["karar"]]), "kalan": satir([b for b in B if not b["b_ayni"]]), "tutan": satir([b for b in B if b["b_ayni"]])}
    if say["hepsi"] != toplam or say["kalan"] != kalan or say["tutan"] != oz["b"]["ayni"] or say["degisen"] != k["karardan_degisen_satir"] or sum(ft.values()) != kalan \
            or degisen_karar + degisen_pafta != say["degisen"]:
        raise SystemExit(f"Sayfadaki sayım kıyasın özetiyle tutmuyor: {say} / {oz} / {ft}")
    suzgec = "".join(f'<button type="button" data-suz="{anahtar}" aria-pressed="{"true" if anahtar == "hepsi" else "false"}">{e(ad)} <span>{say[anahtar]}</span></button>'
                     for anahtar, ad in (("hepsi", "Hepsi"), ("degisen", "Adedi değişen"), ("kalan", "Hâlâ farklı"), ("tutan", "Tutuyor")))
    ek = "".join(f'<tr><td>{e(s.get("liste_adi") or s["kalem"])}</td><td class="boyut">{e(s["boyut"])}</td>'
                 f'<td class="say">{n(s["adet"]) if s["adet"] is not None or s.get("olcu") is None else "— (" + n(s["olcu"]) + " " + e(s["birim"]) + ")"}</td>'
                 f'<td class="say">{"" if s["kg"] is None else n(round(s["kg"]))}</td>'
                 f'<td>{e(DURUM.get(s["durum"], s["durum"]))}</td></tr>' for s in k["a_listesinde_gercek_listede_olmayan"])

    sayfa = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KT-01 Kararlardan Sonra</title>
<style>
/* Düzen: tek sütun; üstte özet ve beklenenler, altında satır satır kıyas. Sayılar eş aralıklı yazıyla sağa hizalı. */
:root {{
  --zemin: #f3f5f6; --kagit: #ffffff; --yazi: #17212b; --soluk: #5b6875; --cizgi: #d5dbe0; --vurgu: #1f5f7a;
  --ok-z: #dff1e6; --ok-y: #1c6b3c; --kay-z: #e3ebf2; --kay-y: #2f4a63; --bek-z: #fdebc8; --bek-y: #7a4d00; --eks-z: #f8d9d6; --eks-y: #8a2118;
  --sans: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --zemin: #11171c; --kagit: #1a2229; --yazi: #e6ebef; --soluk: #9aa7b3; --cizgi: #2f3a44; --vurgu: #7cc4de;
  --ok-z: #173a27; --ok-y: #9fe0b8; --kay-z: #22303d; --kay-y: #b9cee2; --bek-z: #40300d; --bek-y: #f3cf85; --eks-z: #46201c; --eks-y: #f3b1aa; color-scheme: dark }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--zemin); color: var(--yazi); font-family: var(--sans); font-size: 15px; line-height: 1.5; }}
.sayfa {{ max-width: 1040px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: flex; flex-direction: column; gap: 28px; }}
header {{ display: flex; flex-direction: column; gap: 10px; }}
.kunye {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); }}
h1 {{ font-size: clamp(24px, 4.6vw, 34px); line-height: 1.15; margin: 0; font-weight: 600; text-wrap: balance; }}
.aciklama {{ color: var(--soluk); max-width: 76ch; margin: 0; }}
.ozet {{ display: flex; flex-wrap: wrap; gap: 1px; background: var(--cizgi); border: 1px solid var(--cizgi); }}
.ozet div {{ flex: 1 1 200px; background: var(--kagit); padding: 12px 14px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.ozet b {{ font-family: var(--mono); font-size: 24px; font-weight: 500; font-variant-numeric: tabular-nums; }}
.ozet b small {{ font-size: 13px; color: var(--soluk); font-weight: 400; white-space: nowrap; }}
.ozet span {{ font-size: 12.5px; color: var(--soluk); }}
h2 {{ font-size: 15px; margin: 0 0 10px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
section > p {{ margin: 0 0 10px; max-width: 80ch; }}
.kaydir {{ overflow-x: auto; background: var(--kagit); border: 1px solid var(--cizgi); }}
table {{ border-collapse: collapse; width: 100%; min-width: 680px; }}
th, td {{ padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--cizgi); font-size: 13.5px; }}
tbody tr:last-child td {{ border-bottom: 0; }}
thead th {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--soluk); font-weight: 500; position: sticky; top: 0; background: var(--kagit); }}
tr.grup th {{ font-size: 12px; letter-spacing: .06em; text-transform: uppercase; background: var(--zemin); color: var(--soluk); }}
.say {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.say {{ font-size: 15px; font-weight: 500; }}
td.say.fark {{ color: var(--eks-y); }}
td.say.gercek {{ background: var(--kay-z); color: var(--kay-y); }}
.boyut {{ font-family: var(--mono); font-size: 12.5px; color: var(--soluk); white-space: nowrap; }}
.kalem {{ min-width: 300px; }}
.ad {{ font-weight: 600; margin-right: 6px; }}
.alt {{ font-size: 12.5px; color: var(--soluk); max-width: 72ch; margin: 4px 0 0; }}
.alt b {{ color: var(--yazi); font-weight: 500; }}
.rozet {{ display: inline-block; font-size: 11.5px; padding: 1px 8px; border-radius: 10px; white-space: nowrap; font-weight: 500; }}
.rozet.ok {{ background: var(--ok-z); color: var(--ok-y); }}
.rozet.kaynak {{ background: var(--kay-z); color: var(--kay-y); }}
.rozet.bekle {{ background: var(--bek-z); color: var(--bek-y); }}
.rozet.cizgili {{ border: 1px solid var(--cizgi); color: var(--soluk); }}
.cok {{ font-size: 11.5px; color: var(--soluk); white-space: nowrap; }}
.suzgec {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }}
.suzgec button {{ font: inherit; font-size: 13.5px; padding: 6px 12px; border: 1px solid var(--cizgi); background: var(--kagit); color: var(--yazi); border-radius: 4px; cursor: pointer; }}
.suzgec button span {{ font-family: var(--mono); font-size: 12px; color: var(--soluk); }}
.suzgec button[aria-pressed="true"] {{ background: var(--vurgu); border-color: var(--vurgu); color: var(--kagit); }}
.suzgec button[aria-pressed="true"] span {{ color: inherit; }}
.suzgec button:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
ol.sorular {{ margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; max-width: 86ch; }}
.lejant {{ list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; color: var(--soluk); }}
code {{ font-family: var(--mono); font-size: .92em; }}
table.dar {{ min-width: 520px; }}
footer {{ font-size: 12.5px; color: var(--soluk); max-width: 86ch; }}
@media print {{ .suzgec {{ display: none; }} .kaydir {{ overflow: visible; border: 0; }} thead th {{ position: static; }} }}
</style>
</head>
<body>
<div class="sayfa">
<header>
  <div class="kunye">KT-01 · kör test · kararlardan sonra · {e(a.zaman)} · deneme, canlıda değil</div>
  <h1>Kararlarınızdan sonra: kendi listemiz ile gerçek liste</h1>
  <p class="aciklama">98,7 m² tek kat çelik proje (beşik + cumba çatı, müştemilat, sandviç panel; Eylül 2026 listesi). 7 Ekim 07:45 cevaplarınız, 08:02 düzeltmeleriniz ve 8 Ekim 00:45 cevaplarınız kurallara işlendi; aynı proje güncel kurallarla iki kez hesaplandı ve gerçek listenin adedi yazılı {toplam} satırıyla tek tek kıyaslandı. "Aynı" yalnız adedin aynı olmasıdır. Elektrik sayıları projenin paftasından. Kişi, bayi ve firma adı, fiyat yoktur.</p>
</header>
<div class="ozet">{ozet}</div>
<section>
  <h2>Yapıldığı yöntemle farklı kalan {kalan} satır</h2>
  <ul class="lejant">{lejant}</ul>
  <p>{k["karardan_degisen_satir"]} satırın adedi değişti: {degisen_karar} satır kararlarınızla, {degisen_pafta} satır elektrik sayıları projenin paftasından alındığı için. Yeni tutan {kazanc_toplam} satırın {kazanc_toplam - kazanc_pafta}'u kararlarınızdan ({kazanc_inis}'i iniş kuralından{"" if k.get("inis_onayli") else "; eşiği önerimdir, teyidinizi bekliyor"}), {kazanc_pafta}'i pafta sayımından; önce tutan hiçbir satır bozulmadı. Aynı satır sayısı kuralların o listeye ne kadar benzediğini gösterir, doğruluğunu değil: kararlarınızın bir kısmı o listeyi düzeltiyor (Boardex kalınlığı, çatı şiltesi, duvar izolasyonu, vida katsayıları).</p>
</section>
<section>
  <h2>Sizden beklenenler</h2>
  <ol class="sorular">{"".join(f"<li>{md(x)}</li>" for x in sorular)}</ol>
</section>
<section>
  <h2>Çelik standardıyla gelen, gerçek listede olmayan satırlar</h2>
  <p>Proje bugün sipariş edilse çatı ve tavan paneliyle hazırlanır; omega, aşık, saçak ve alın sacı çıkar, yerine bunlar girer.</p>
  <div class="kaydir"><table class="dar"><thead><tr><th>Kalem</th><th>Boyut</th><th class="say">Adet</th><th class="say">kg</th><th>Kaynak</th></tr></thead><tbody>{ek}</tbody></table></div>
</section>
<section>
  <h2>Satır satır</h2>
  <div class="suzgec" role="group" aria-label="Satırları süz">{suzgec}</div>
  <div class="kaydir"><table class="kiyas"><thead><tr><th>Kalem (gerçek listedeki satır)</th><th class="say">Gerçek</th><th class="say">Önce (03:46)</th><th class="say">Sonra, aynı yöntem</th><th class="say">Sonra, çelik standardı</th></tr></thead><tbody>{"".join(govde)}</tbody></table></div>
  <p class="alt">Düğmelerdeki sayılar gerçek listenin satırıdır; tablonun bir satırı gerçek listede birden çok satırı karşılayabilir ({len(B)} tablo satırı, {toplam} gerçek satır). Kırmızı sayı: gerçek listeden farklı. "—": o yöntemde kalem yok.</p>
</section>
<footer>Kaynak: <code>deneme/2026-10-06_kor_test/sonuc/KT01_kararlar_kiyas.json</code>; sayfa <code>kararlar_sayfa.py</code> ile üretilir, elle düzeltilmez. Açıklamalar elle yazılmıştır ve hesap çıktısıyla denetlenir (<code>kararlar_kiyas.py</code>). Sınır: tek proje; kararların bir kısmının hesabı tarifinizden geliştirildi ve teyidinizi bekliyor (yukarıdaki sorular).</footer>
</div>
<script>
(function () {{
  var dugmeler = document.querySelectorAll(".suzgec button"), satirlar = document.querySelectorAll("table.kiyas tbody tr");
  function suz(anahtar) {{
    var gorunen = null;
    satirlar.forEach(function (tr) {{
      if (tr.classList.contains("grup")) {{ if (gorunen) gorunen.hidden = !gorunen._var; gorunen = tr; tr._var = false; return; }}
      var goster = anahtar === "hepsi" || tr.dataset[anahtar] === "1";
      tr.hidden = !goster;
      if (goster && gorunen) gorunen._var = true;
    }});
    if (gorunen) gorunen.hidden = !gorunen._var;
  }}
  dugmeler.forEach(function (d) {{
    d.addEventListener("click", function () {{
      dugmeler.forEach(function (x) {{ x.setAttribute("aria-pressed", x === d ? "true" : "false"); }});
      suz(d.dataset.suz);
    }});
  }});
}})();
</script>
</body>
</html>
"""
    for ad in ("Lokman", "Ubeydullah"):   # sayfada kişi adı kalmamalı
        if ad in sayfa:
            raise SystemExit(f"Sayfada kişi adı kaldı: {ad}")
    a.cikti.write_text(sayfa, encoding="utf-8")
    print("yazıldı:", a.cikti, "·", len(sayfa) // 1024, "KB ·", len(B), "birim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
