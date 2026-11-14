"""İE-17 · Prefabrik evin beşik dışı çatısı: İş Emri'nin `cati` alanı → genel motorun çatı biçimi (düzlemler, kalkanlar).

Lokman ve CIO, 27 Ekim 2026: çıktı biçimi canlı ön onay PDF'i (`dxf_out`), genel motordan yalnız çatı geometrisi, değerler prefabrikten.
Bu modül çatı geometrisini kendisi kurmaz; genel motorun çatı üreticisini (`genel.cati_uretici.uret`: `cati_cumba`, `cati_kirma`)
prefabrik değerleriyle çağırır ve sonucu onun denetiminden (`cati_uretici.denetle`: `cati_genel.cati_kur`, düzlemler saçaklı ayak izini
boşluksuz ve örtüşmesiz örter, desteksiz üst kenar yok) geçirir.
Denetim bulgu verirse çatı çizilmez, hata söylenir (yanlış çatı çizilmez); tanınmayan alan da (ör. kırmada `cumbalar`, cumbada başka
eğim) yok sayılmaz, hata verir.

Değerler İş Emri'nden: eğim (`egim_yuzde`, paftadan; burada varsayılan yok), saçak (`sacak_cm`, 30), topuk (`topuk_cm`, 10), duvar üstü
`yapi.duvar_yuksekligi_cm` (250 / 280 / 300, D-14). Ayak izi Motor'un gövde dikdörtgeni (`G.govde_kutusu`). Mahya `makas_ekseni`'nden
(`sunum.cati_tanimi` ile aynı: "x" makaslar x'i geçer, mahya y boyunca; "y" mahya x boyunca). Kaplama payı pano Motor'unun IFC'siyle aynı
(`ust_pay` 14: düzlemin 10 cm üstünde 4 cm sac; düzlem başına pay yazılmaz). Kalkanlar dış duvarın dış yüzünde, duvarlar arasında (saçaksız).

Tipler:
- `besik`: bu modülde değil; `sunum.cati_tanimi` aynen (P6001 ve bugünkü paftalar).
- `besik_cumba`: ana beşik ve ona dik küçük beşik (çapraz cumba; AP-13, 16, 22). `cumbalar`: bir giriş {cephe on | arka | sol | sag,
  `bas_cm`–`bit_cm` cephe boyunca dış yüzden (on / arka: x, sol / sag: y; taşan verandayla aynı), `cikinti_cm` 0, `egim_yuzde` yazılırsa
  ana çatınınki}. Cumba ana mahyaya paralel cephede olur; alnı o cephenin duvarında. Çıkıntılı cumba (İE-17 PR-2, AP-22): `cikinti_cm`
  kadar gövdeden taşar; gövde girintili olur ve dış çizgisi ana çatı ile cumbanın birleşimidir (denetlenir). Paralel cumba girintili
  gövdenin beşiğinde (`cati_serit`, AP-15); farklı eğimli cumba (PK-03) kapsam dışı. Çıkıntısız cumbada `ana_makas` "cumba_makasindan"
  (İE-15 K6, D-53 madde 7; TK-04 r06): ana makaslar cumbanın baş makasının arkasına geri çekilir; ana çatının ayak izi o cepheden
  `ana_geri_cm` + saçak geride, cumba o şeridi örter (çıkıntılı cumbanın düzlemleri gibi; gövde girintisiz, girinti denetimi yapılmaz).
- `kirma`: dört düzlem, kalkan yok; mahya uzun kenar boyunca (AP-01). Uçtaki iki kırma yüzünün eğimi paftada ana yüzlerden farklıysa
  `kirma_egimleri` {sol, sag} (mahya x boyunca) ya da {on, arka} (mahya y boyunca), yüzde: kırma çizgileri 45° olmaz, mahya o yana kayar
  (AP-01: ana %33, sol %32,5, sağ %36,2). Verilmezse eşit eğim (`genel.cati_kirma`, kırmalar 45°).
  Tek uçlu kırma (İE-29, AP-27): `kalkan_ucu` sol | sag (mahya x boyunca) ya da on | arka (mahya y boyunca) → o uçta kalkan (beşikteki
  gibi, dış duvarın dış yüzünde; saçak o uçta da), öteki uçta kırma yüzü; eşit eğim, kırma çizgileri 45° (`_tek_uclu_kirma`). Mahya
  kısa kenar boyunca da olur (AP-27 773 × 1000, mahya 773 boyunca). `kirma_egimleri` ile birlikte yazılmaz.
"""
from __future__ import annotations

from . import geometry as G

TIPLER = ("besik_cumba", "kirma")
TIP_ADI = {"besik_cumba": "beşik + cumba", "kirma": "kırma"}
UST_PAY_CM = 14.0                  # ifc_uret: sac düzlemin 10 cm üstünde, 4 cm (pano Motor'unun beşik IFC'siyle aynı)
CEPHE_YAN = {"on": "G", "arka": "K", "sol": "B", "sag": "D"}
ALANLAR = {"tip", "egim_yuzde", "sacak_cm", "topuk_cm", "makas_ekseni", "makas_yonu"}   # her tipte; tanınmayan alan yok sayılmaz
TIP_ALANI = {"besik_cumba": {"cumbalar"}, "kirma": {"kirma_egimleri", "kalkan_ucu"}}
KALKAN_UCLARI = {"x": ("sol", "sag"), "y": ("on", "arka")}       # İE-29: tek uçlu kırmada kalkanlı uç (mahya yönüne göre)
CUMBA_ALANLARI = {"cephe", "bas_cm", "bit_cm", "cikinti_cm", "egim_yuzde", "ana_makas"}
VERANDA_CUMBA_ALANLARI = {"cephe", "veranda"}   # ikinci cumba: taşan verandanın çatısı (Lokman, 14 Kasım 2026 08:41)
KARSI = {"on": "arka", "arka": "on", "sol": "sag", "sag": "sol"}
ANA_MAKAS = ("cumba_makasindan",)   # İE-15 K6, D-53 madde 7: ana makaslar cumbanın baş makasının arkasından 10 cm topukla


class PrefabrikCatiHatasi(G.IsEmriHatasi):
    pass


def ana_geri_cm(c: dict, plan: G.Plan | None) -> float | None:
    """İE-15 K6 (D-53 madde 7; Lokman, 5 Kasım 2026 07:19–10:15): cumbanın `ana_makas` "cumba_makasindan" ise ana makaslar kesilmez, geri
    çekilir: cumbanın baş makasının iç yüzünden 10 cm topukla başlar, arka saçak aynı; makas kısalır, mahyası arkaya kayar, ön saçak (verandanın
    üstü dahil) içeri çekilir, cumbanın iki yanında dere oluşur. Dönen: ana çatının ön kenarının (makasın topuklu ucunun) cumbanın cephesindeki
    dış yüzden uzaklığı (dış duvarın yarı kalınlığı + makas kalınlığının yarısı, `cumba_altindaki_ana_makas`); anahtar yoksa None (eski yol)."""
    u = (c.get("cumbalar") or [{}])[0]
    if u.get("ana_makas") is None:
        return None
    if u["ana_makas"] not in ANA_MAKAS:
        raise PrefabrikCatiHatasi(f"cumbanın ana_makas'ı {u['ana_makas']!r}: {', '.join(ANA_MAKAS)} olur (yanlış çatı kurulmaz)")
    if float(u.get("cikinti_cm", 0)) != 0:
        raise PrefabrikCatiHatasi("cumbanın ana_makas'ı yalnız çıkıntısız cumbada (çıkıntılı cumbada ana çatı zaten geride)")
    if plan is None:
        raise PrefabrikCatiHatasi("cumbanın ana_makas'ı: dış duvar kalınlığı için plan gerekir")
    from .cati_capraz import bitis_kurali, yavru_kurali
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    return h + (yavru_kurali()["kalinlik"] / 2 if bitis_kurali() == "yuz" else 0.0)


def _cumba(c: dict, kutu: tuple, plan: G.Plan | None = None) -> tuple[list[float], list[float]]:
    """`cumbalar`'ın tek girişi → (ana çatının dikdörtgeni, cumba dikdörtgeni). Çıkıntı 0: ana çatı gövdenin kutusu, cumba onun kenarında
    sıfır derinlikli şerit. Çıkıntılı cumba (İE-17 PR-2, AP-22: veranda ve üstündeki cumba gövdeden 62,75 öne taşar): ana çatı kutunun o
    cephesinden `cikinti_cm` geride, cumba kutunun kenarından ana çatıya kadar (gövdenin girintisiyle denetlenir, `cati`).
    İE-15 K6 (`ana_makas` "cumba_makasindan", `ana_geri_cm`): ana çatının ayak izi o cepheden geri + saçak kadar geride (saçaklı ön kenarı
    cumbanın baş makasının iç yüzünde), cumba kutunun kenarından ana çatıya kadar; gövde değişmez (girinti denetimi yok)."""
    x0, y0, x1, y1 = kutu
    cs = c.get("cumbalar") or []
    if len(cs) != 1:
        raise PrefabrikCatiHatasi(f"beşik + cumba: bir cumba yazılır ({len(cs)} yazılmış; çift cumba yol haritasında sonra)")
    u = cs[0]
    fazla = sorted(set(u) - CUMBA_ALANLARI)
    if fazla:
        raise PrefabrikCatiHatasi(f"cumbada tanınmayan alan: {', '.join(fazla)} (yok sayılmaz; yanlış çatı çizilmez)")
    if u.get("egim_yuzde") is not None and float(u["egim_yuzde"]) != float(c["egim_yuzde"]):
        yuzde = lambda v: f"%{float(v):g}".replace(".", ",")
        raise PrefabrikCatiHatasi(f"cumba eğimi ana çatıdan farklı ({yuzde(u['egim_yuzde'])} ↔ {yuzde(c['egim_yuzde'])}): genel motorun "
                                  f"cumbası ana çatının eğimiyle kurulur; farklı eğimli cumba bu sürümde çizilmez")
    cephe = u.get("cephe")
    if cephe not in CEPHE_YAN:
        raise PrefabrikCatiHatasi(f"cumba cephesi on, arka, sol ya da sag olur: {cephe}")
    cik = float(u.get("cikinti_cm", 0))
    yon = "x" if cephe in ("on", "arka") else "y"               # D-30: tam panoya tamamlanan yönde eski köşe yenisine
    a, b = G.tamamla_gercek_cm(u["bas_cm"], yon), G.tamamla_gercek_cm(u["bit_cm"], yon)
    boy = (x1 - x0) if cephe in ("on", "arka") else (y1 - y0)
    derin = (y1 - y0) if cephe in ("on", "arka") else (x1 - x0)
    if not 0 <= a < b <= boy + 1e-6:
        raise PrefabrikCatiHatasi(f"cumba {cephe} cephesinde {a:g}–{b:g} cm; cephe {boy:g} cm")
    if not 0 <= cik < derin / 2:
        raise PrefabrikCatiHatasi(f"cumbanın çıkıntısı {cik:g} cm: 0 ya da gövdenin derinliğinin yarısından az olur")
    geri = ana_geri_cm(c, plan)
    if geri is not None:
        cik = geri + float(c.get("sacak_cm", 30))
    if cephe == "on":
        return [x0, y0 + cik, x1, y1], [x0 + a, y0, x0 + b, y0 + cik]
    if cephe == "arka":
        return [x0, y0, x1, y1 - cik], [x0 + a, y1 - cik, x0 + b, y1]
    if cephe == "sol":
        return [x0 + cik, y0, x1, y1], [x0, y0 + a, x0 + cik, y0 + b]
    return [x0, y0, x1 - cik, y1], [x1 - cik, y0 + a, x1, y0 + b]


def _veranda_cumbasi(u: dict, plan: G.Plan | None) -> list[float]:
    """Taşan verandanın üstündeki cumba (`cumbalar[]` öğesinde `veranda`: verandanın adı; verandanın `cati.tip`'i "cumba"): cumbanın ayak izi
    verandanın dikdörtgeni (kolonlar içinde); eğim, saçak ve topuk ana çatınınki. Lokman, 14 Kasım 2026 08:41–08:42 (45 m² ev, arka sundurma):
    "cumba çatısı gibi birleştireceksin vadi dere oluşacak böyle eğrelti olmayacak", "çapraz cumba çatısını nasıl çiziyorsan öyle çiz"."""
    fazla = sorted(set(u) - VERANDA_CUMBA_ALANLARI)
    if fazla:
        raise PrefabrikCatiHatasi(f"verandanın cumbasında yalnız cephe ve veranda yazılır ({', '.join(fazla)} yazılmış; yeri ve eğimi verandadan "
                                  "ve ana çatıdan)")
    if plan is None:
        raise PrefabrikCatiHatasi("verandanın cumbası: verandanın yeri için plan gerekir")
    v = next((v for v in plan.dis_verandalar if v["ad"] == u["veranda"]), None)
    if v is None:
        raise PrefabrikCatiHatasi(f"cumbanın verandası yok: {u['veranda']} (İş Emri `verandalar`'ında taşan veranda olmalı)")
    if v["cephe"] != u.get("cephe"):
        raise PrefabrikCatiHatasi(f"cumba {u.get('cephe')} cephesinde, verandası {v['ad']} {v['cephe']} cephesinde")
    if v["cati"]["tip"] != "cumba":
        raise PrefabrikCatiHatasi(f"veranda {v['ad']}: çatısı cumba değil ({v['cati']['tip']}); cumbanın verandasında `cati.tip` cumba yazılır")
    return [float(t) for t in v["rect"]]


def cumba_dikdortgenleri(c: dict, kutu: tuple, plan: G.Plan | None = None) -> tuple[list[float], list[list[float]]]:
    """`cumbalar` → (ana çatının dikdörtgeni, [cumba dikdörtgeni, …]). Tek cumba `_cumba` (eski yol, aynen). İki cumba (14 Kasım 2026, 45 m² ev:
    önde gövdenin cumbası, arkada sundurmanın cumbası): ana çatının iki karşı saçak yüzünde; her biri tek cumbanın kuralıyla kurulur, ana çatı
    iki çıkıntının arasında. Taşan verandanın cumbası `veranda` ile (`_veranda_cumbasi`). Ana makasın geri çekilmesi (`ana_makas`) iki cumbada yok."""
    cs = c.get("cumbalar") or []
    if len(cs) != 2:
        if any(isinstance(u, dict) and "veranda" in u for u in cs):
            raise PrefabrikCatiHatasi("verandanın cumbası yalnız gövdenin çıkıntılı cumbasıyla birlikte, ikinci cumba olarak yazılır (PC-38)")
        ana, cumba = _cumba(c, kutu, plan)
        return ana, [cumba]
    if any("ana_makas" in u for u in cs):
        raise PrefabrikCatiHatasi("iki cumbada ana_makas (ana makasların cumba makasından geri çekilmesi) bu sürümde yok")
    if KARSI.get(cs[0].get("cephe")) != cs[1].get("cephe"):
        raise PrefabrikCatiHatasi(f"iki cumba ana çatının karşı iki saçak yüzünde olur ({cs[0].get('cephe')}, {cs[1].get('cephe')} yazılmış)")
    if sum("veranda" in u for u in cs) != 1:
        raise PrefabrikCatiHatasi("iki cumbanın biri gövdenin çıkıntılı cumbası, öteki taşan verandanın cumbası (`veranda`) olur (PC-38); "
                                  "iki gövde cumbası ya da iki veranda cumbası bu sürümde yok")
    if not all(float(u.get("cikinti_cm") or 0) > 0 for u in cs if "veranda" not in u):
        raise PrefabrikCatiHatasi("veranda cumbasının karşısındaki gövde cumbası çıkıntılı olur (`cikinti_cm` > 0; PC-38, 45 m² ev); "
                                  "çıkıntısız gövde cumbasıyla iki cumba bu sürümde yok")
    ana, rs = list(kutu), []
    for u in cs:
        if "veranda" in u:
            rs.append(_veranda_cumbasi(u, plan))
            continue
        a_, r = _cumba({**c, "cumbalar": [u]}, kutu, plan)
        ana = [max(ana[0], a_[0]), max(ana[1], a_[1]), min(ana[2], a_[2]), min(ana[3], a_[3])]
        rs.append(r)
    for u, r in zip(cs, rs):
        bitisik = {"on": r[3] == ana[1], "arka": r[1] == ana[3], "sol": r[2] == ana[0], "sag": r[0] == ana[2]}[u["cephe"]]
        if not bitisik:
            raise PrefabrikCatiHatasi(f"{u['cephe']} cumbası ana çatının kenarına bitişik değil ({r} ↔ ana çatı {ana})")
    return ana, rs


def _iki_cumba(ana: list, rs: list, mahya: str, c: dict, H0: float, k: dict) -> dict:
    """İki cumbalı çatı: her cumba tek cumbanın üreticisiyle (`cati_uretici.uret`, "cumba") aynı ana çatıya kurulur; çatı, birincinin girdiği
    ana yüz ve onun cumbası + ikincinin girdiği karşı yüz ve onun cumbası. Ana çatının uç kalkanları iki kurulumun aralıklarının birleşimi
    (cumba bir uçla aynı hizadaysa kalkan onun yanını da örter). İkinci cumbanın yüzleri "cumba 2 …" adını alır."""
    from .genel import cati_uretici as CU
    us = []
    for r in rs:
        try:
            us.append(CU.uret([ana, r], "cumba", mahya=mahya, egim_yuzde=float(c["egim_yuzde"]), duvar_ustu=H0, kural=k))
        except CU.CatiHatasi as e:
            raise PrefabrikCatiHatasi(str(e))
    u1, u2 = us
    ana_ad = {d["ad"] for d in u1["duzlemler"] if d["ad"].startswith("ana ")}
    giris1 = next(d["ad"] for d in u1["duzlemler"] if d["ad"].startswith("ana ") and len(d["plan"]) > 4)
    giris2 = next(d["ad"] for d in u2["duzlemler"] if d["ad"].startswith("ana ") and len(d["plan"]) > 4)
    if giris1 == giris2 or giris2 not in ana_ad:
        raise PrefabrikCatiHatasi("iki cumba ana çatının aynı yüzüne giriyor; karşı iki yüzde olmalı")
    yeni = lambda ad: ad.replace("cumba ", "cumba 2 ", 1) if ad.startswith("cumba ") else ad
    duz = [d for d in u1["duzlemler"] if d["ad"] != giris2]
    duz += [dict(d, ad=yeni(d["ad"])) for d in u2["duzlemler"] if d["ad"] == giris2 or not d["ad"].startswith("ana ")]
    kal, uc2 = [], {kk["ad"]: kk for kk in u2["kalkanlar"]}
    for kk in u1["kalkanlar"]:
        o = uc2.pop(kk["ad"], None) if not kk["ad"].startswith("cumba") else None
        if o is not None:
            kk = dict(kk, aralik=[min(kk["aralik"][0], o["aralik"][0]), max(kk["aralik"][1], o["aralik"][1])])
        kal.append(kk)
    kal += [dict(kk, ad=kk["ad"].replace("cumbanın", "cumba 2'nin", 1), ust=[yeni(a) for a in kk["ust"]]) for kk in uc2.values()]
    return dict(u1, duzlemler=duz, kalkanlar=kal)


def _kirma_farkli(kutu: tuple, mahya: str, e: float, uc: dict, b: dict, k: dict) -> list[dict]:
    """Uç yüzleri farklı eğimli kırma: ana iki yüz `e`, uçlar `uc` (yüzde). Kanonik yön mahya x boyunca (uçlar sol / sağ); mahya y boyunca
    çatı devrik kurulup geri çevrilir (`cati_ortak.devrik`; uçlar ön / arka). Mahya yüksekliği ana yüzden: R = (derinlik / 2 + saçak) · e;
    uçta kırma çizgisinin plandaki boyu R / e_uç."""
    from .genel import cati_ortak as CO
    x0, y0, x1, y1 = kutu
    adlar = ("sol", "sag") if mahya == "x" else ("on", "arka")
    if set(uc) != set(adlar):
        raise PrefabrikCatiHatasi(f"kırma: uç eğimleri {', '.join(adlar)} için yazılır ({', '.join(sorted(uc))} yazılmış)")
    lo, hi = k["egim_yuzde_aralik"]
    for ad in adlar:
        if not lo <= float(uc[ad]) <= hi:
            raise PrefabrikCatiHatasi(f"kırma: {ad} yüzünün eğimi %{uc[ad]:g} aralık dışı (%{lo}–%{hi})")
    if mahya == "y":                                  # devrik: x ↔ y
        x0, y0, x1, y1 = y0, x0, y1, x1
    e0, e1 = float(uc[adlar[0]]) / 100, float(uc[adlar[1]]) / 100
    S = b["S"]
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S
    ym = (Y0 + Y1) / 2
    R = (ym - Y0) * e
    xa, xb = X0 + R / e0, X1 - R / e1
    if xb - xa < float(k["kirma_mahya_en_az_cm"]):
        raise PrefabrikCatiHatasi(f"kırma: mahya {xb - xa:.1f} cm (uç eğimleriyle); en az {k['kirma_mahya_en_az_cm']:g} cm")
    duz = [CO.duzlem(b, "güney", [[X0, Y0], [X1, Y0], [xb, ym], [xa, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
           CO.duzlem(b, "kuzey", [[xa, ym], [xb, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü"),
           CO.duzlem(b, "batı", [[X0, Y0], [xa, ym], [X0, Y1]], [1, 0], {"x": X0}, "batı kırması", egim=e0),
           CO.duzlem(b, "doğu", [[X1, Y0], [X1, Y1], [xb, ym]], [-1, 0], {"x": X1}, "doğu kırması", egim=e1)]
    if mahya == "y":
        duz = CO.devrik({"duzlemler": duz, "kalkanlar": []})["duzlemler"]
    return duz


def _tek_uclu_kirma(kutu: tuple, mahya: str, uc: str, b: dict, k: dict) -> tuple[list[dict], list[dict]]:
    """İE-29 (AP-27): bir ucu kalkan, öteki ucu kırma; eşit eğim (kırma çizgileri 45°). Kanonik yön mahya x (kalkan sol ya da sağda);
    mahya y boyunca çatı devrik kurulup geri çevrilir (kalkan ön ya da arkada). Saçak her yanda S, kalkanlı uçta da (`cati_besik` gibi;
    kalkan dış duvarın dış yüzünde). Mahya kalkanlı uçtaki saçaktan kırmanın tepesine: uzun kenar + 2 S − (derinlik / 2 + S)."""
    from .genel import cati_ortak as CO
    if uc not in KALKAN_UCLARI[mahya]:
        raise PrefabrikCatiHatasi(f"tek uçlu kırma: kalkan ucu mahya {mahya} boyunca {' ya da '.join(KALKAN_UCLARI[mahya])} olur ({uc} yazılmış)")
    x0, y0, x1, y1 = kutu
    if mahya == "y":                                  # devrik: x ↔ y (ön ↔ sol, arka ↔ sağ)
        x0, y0, x1, y1 = y0, x0, y1, x1
    bati = uc in ("sol", "on")
    S = b["S"]
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S
    ym = (Y0 + Y1) / 2
    yari = ym - Y0
    if (X1 - X0) - yari < float(k["kirma_mahya_en_az_cm"]):
        raise PrefabrikCatiHatasi(f"tek uçlu kırma: mahya {(X1 - X0) - yari:.1f} cm; en az {k['kirma_mahya_en_az_cm']:g} cm")
    if bati:                                          # kalkan batıda, kırma doğuda
        xb = X1 - yari
        duz = [CO.duzlem(b, "güney", [[X0, Y0], [X1, Y0], [xb, ym], [X0, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
               CO.duzlem(b, "kuzey", [[X0, ym], [xb, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü"),
               CO.duzlem(b, "doğu", [[X1, Y0], [X1, Y1], [xb, ym]], [-1, 0], {"x": X1}, "doğu kırması")]
        kal = [CO.kalkan("batı kalkanı", "x", x0, (y0, y1), "dogu", ["güney", "kuzey"])]
    else:                                             # kalkan doğuda, kırma batıda
        xa = X0 + yari
        duz = [CO.duzlem(b, "güney", [[X0, Y0], [X1, Y0], [X1, ym], [xa, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
               CO.duzlem(b, "kuzey", [[xa, ym], [X1, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü"),
               CO.duzlem(b, "batı", [[X0, Y0], [xa, ym], [X0, Y1]], [1, 0], {"x": X0}, "batı kırması")]
        kal = [CO.kalkan("doğu kalkanı", "x", x1, (y0, y1), "bati", ["güney", "kuzey"])]
    if mahya == "y":
        c = CO.devrik({"duzlemler": duz, "kalkanlar": kal})
        duz, kal = c["duzlemler"], c["kalkanlar"]
    return duz, kal


def cati(plan: G.Plan, ie: dict) -> dict:
    """Beşik dışı ana çatı → genel motorun `cati` biçimi. Dönen sözlük `sunum.cati_tanimi`'nin beşik çatısının anahtarlarında,
    ek olarak `tip_adi`, `ust_pay` ve `kalkanlar` (`cati_genel.cati_kur` ve `cephe_gorunus` okur)."""
    from .genel import cati_uretici as CU
    c = ie.get("cati") or {}
    tip = c.get("tip", "besik")
    if tip not in TIPLER:
        raise PrefabrikCatiHatasi(f"çatı tipi '{tip}' prefabrik çatıda yok (beşik `sunum.cati_tanimi`; {', '.join(TIPLER)} burada)")
    fazla = sorted(set(c) - ALANLAR - TIP_ALANI[tip])
    if fazla:
        raise PrefabrikCatiHatasi(f"{TIP_ADI[tip]} çatıda tanınmayan alan: {', '.join(fazla)} (yok sayılmaz; yanlış çatı çizilmez)")
    if c.get("egim_yuzde") is None:
        raise PrefabrikCatiHatasi(f"{TIP_ADI[tip]} çatının eğimi paftadan yazılır (`cati.egim_yuzde`; varsayılan yok)")
    k = dict(CU.kurallar())
    k["sacak_cm"] = float(c.get("sacak_cm", 30))
    k["topuk_cm"] = float(c.get("topuk_cm", 10))
    H0 = float((ie.get("yapi") or {}).get("duvar_yuksekligi_cm", 250))
    kutu = tuple(float(v) for v in G.govde_kutusu(plan))
    mahya = "y" if c.get("makas_ekseni", "x") == "x" else "x"
    if tip == "kirma" and c.get("kalkan_ucu") is not None:   # İE-29: tek uçlu kırma (AP-27); genel motorun üreticisi değişmez
        if c.get("kirma_egimleri"):
            raise PrefabrikCatiHatasi("tek uçlu kırmada uç eğimi (`kirma_egimleri`) bu sürümde yok: kırma yüzü ana yüzlerin eğiminde")
        from .genel import cati_ortak as CO
        lo, hi = k["egim_yuzde_aralik"]
        if not lo <= float(c["egim_yuzde"]) <= hi:
            raise PrefabrikCatiHatasi(f"tek uçlu kırma: eğim %{c['egim_yuzde']:g} aralık dışı (%{lo}–%{hi})")
        ayak = [list(kutu)]
        e = round(float(c["egim_yuzde"]) / 100, 5)
        duz0, kal0 = _tek_uclu_kirma(kutu, mahya, c["kalkan_ucu"], CO.baglam(k, e, H0), k)
        u = {"tip": "kirma", "sacak": k["sacak_cm"], "topuk": k["topuk_cm"], "duvar_ustu": H0, "panel_kalinligi": k["panel_kalinligi_cm"],
             "duzlemler": duz0, "kalkanlar": kal0}
    elif tip == "kirma":
        ayak = [list(kutu)]
        try:
            u = CU.uret(ayak, "kirma", mahya=mahya, egim_yuzde=float(c["egim_yuzde"]), duvar_ustu=H0, kural=k)
        except CU.CatiHatasi as e:
            raise PrefabrikCatiHatasi(f"kırma çatı: {e}")
        if c.get("kirma_egimleri"):                  # uç yüzler paftadaki eğimle (ana yüzler ve mahya yönü üreticinin denetiminden geçti)
            from .genel import cati_ortak as CO
            u["duzlemler"] = _kirma_farkli(kutu, mahya, round(float(c["egim_yuzde"]) / 100, 5), dict(c["kirma_egimleri"]),
                                           CO.baglam(k, round(float(c["egim_yuzde"]) / 100, 5), H0), k)
    elif len(c.get("cumbalar") or []) == 2:          # 14 Kasım 2026: iki cumba (gövdenin cumbası + taşan verandanın cumbası)
        ana, rs = cumba_dikdortgenleri(c, kutu, plan)
        from shapely.geometry import box
        from shapely.ops import unary_union
        from .cati_serit import cati_izi
        fark = cati_izi(plan).symmetric_difference(unary_union([box(*ana)] + [box(*r) for r in rs])).area
        if fark > 1.0:
            raise PrefabrikCatiHatasi(f"iki cumba: gövdenin ve verandanın dış çizgisi ana çatı ile cumbaların birleşimi değil ({fark:.0f} cm² fark)")
        ayak = [ana, *rs]
        u = _iki_cumba(ana, rs, mahya, c, H0, k)
    else:
        ana, cumba = _cumba(c, kutu, plan)
        if (ana != list(kutu) and ana_geri_cm(c, plan) is None) or plan.girintili:                   # çıkıntılı cumba: gövde = ana çatı + cumba (girinti cumbanın yanında)
            from shapely.geometry import box
            from .cati_serit import cati_izi
            fark = cati_izi(plan).symmetric_difference(box(*ana).union(box(*cumba))).area
            if fark > 1.0:
                ne = ("beşik + cumba (ana makaslar cumba makasının arkasından)" if ana_geri_cm(c, plan) is not None else
                      "çıkıntılı cumba" if ana != list(kutu) else "beşik + cumba (girintili gövde)")
                raise PrefabrikCatiHatasi(f"{ne}: gövdenin dış "
                                          f"çizgisi ana çatı ile cumbanın birleşimi değil ({fark:.0f} cm² fark; çıkıntı ve cumbanın yeri gövdenin "
                                          "girintisiyle aynı olmalı)")
        ayak = [ana, cumba]
        try:
            u = CU.uret(ayak, "cumba", mahya=mahya, egim_yuzde=float(c["egim_yuzde"]), duvar_ustu=H0, kural=k)
        except CU.CatiHatasi as e:
            raise PrefabrikCatiHatasi(str(e))
    bulgu = CU.denetle(u, ayak)
    if bulgu:
        raise PrefabrikCatiHatasi(f"{TIP_ADI[tip]} çatı denetimden geçmedi: {'; '.join(bulgu)}")
    duz = []
    for d in u["duzlemler"]:
        d = dict(d)
        d.pop("ust_pay", None)                       # kaplama payı çatının `ust_pay`'ından (pano Motor'unun sacı), çeliğin paneli değil
        duz.append(d)
    return {"tip": u["tip"], "tip_adi": TIP_ADI[tip], "tip_kaynak": "İE-17 prefabrik çatı (motor/cati_prefabrik.py; İE-14 çatı üreticisi)",
            "sacak": k["sacak_cm"], "topuk": k["topuk_cm"], "duvar_ustu": H0, "ust_pay": UST_PAY_CM, "duzlemler": duz,
            "kalkanlar": u["kalkanlar"]}
