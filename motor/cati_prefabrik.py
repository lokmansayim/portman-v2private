"""İE-17 · Prefabrik evin beşik dışı çatısı: İş Emri'nin `cati` alanı → genel motorun çatı biçimi (düzlemler, kalkanlar).

Lokman, 27 Ekim 2026: çizim biçimi canlıdaki çizim setinden, değerler prefabrikten. Bu modül çatı geometrisini kendisi kurmaz; genel motorun
çatı üreticisini (`genel.cati_uretici.uret`: `cati_cumba`, `cati_kirma`) prefabrik değerleriyle çağırır ve sonucu onun denetiminden
(`cati_uretici.denetle`: `cati_genel.cati_kur`, düzlemler saçaklı ayak izini boşluksuz ve örtüşmesiz örter, desteksiz üst kenar yok) geçirir.
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
  ana çatınınki}. Cumba ana mahyaya paralel cephede olur; alnı o cephenin duvarında. Çıkıntılı cumba ve paralel cumba (AP-15, 09) PR-2;
  farklı eğimli cumba (PK-03) kapsam dışı.
- `kirma`: dört düzlem, kalkan yok; mahya uzun kenar boyunca (AP-01). Uçtaki iki kırma yüzünün eğimi paftada ana yüzlerden farklıysa
  `kirma_egimleri` {sol, sag} (mahya x boyunca) ya da {on, arka} (mahya y boyunca), yüzde: kırma çizgileri 45° olmaz, mahya o yana kayar
  (AP-01: ana %33, sol %32,5, sağ %36,2). Verilmezse eşit eğim (`genel.cati_kirma`, kırmalar 45°).
"""
from __future__ import annotations

from . import geometry as G

TIPLER = ("besik_cumba", "kirma")
TIP_ADI = {"besik_cumba": "beşik + cumba", "kirma": "kırma"}
UST_PAY_CM = 14.0                  # ifc_uret: sac düzlemin 10 cm üstünde, 4 cm (köprünün beşik çatısıyla aynı)
CEPHE_YAN = {"on": "G", "arka": "K", "sol": "B", "sag": "D"}
ALANLAR = {"tip", "egim_yuzde", "sacak_cm", "topuk_cm", "makas_ekseni", "makas_yonu"}   # her tipte; tanınmayan alan yok sayılmaz
TIP_ALANI = {"besik_cumba": {"cumbalar"}, "kirma": {"kirma_egimleri"}}
CUMBA_ALANLARI = {"cephe", "bas_cm", "bit_cm", "cikinti_cm", "egim_yuzde"}


class PrefabrikCatiHatasi(G.IsEmriHatasi):
    pass


def _cumba(c: dict, kutu: tuple) -> list[float]:
    """`cumbalar`'ın tek girişi → cumba dikdörtgeni (çıkıntı 0: ana gövdenin kenarında sıfır derinlikli şerit)."""
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
    if float(u.get("cikinti_cm", 0)) != 0:
        raise PrefabrikCatiHatasi("çıkıntılı cumba bu sürümde çizilmez (İE-17 PR-2)")
    a, b = float(u["bas_cm"]), float(u["bit_cm"])
    boy = (x1 - x0) if cephe in ("on", "arka") else (y1 - y0)
    if not 0 <= a < b <= boy + 1e-6:
        raise PrefabrikCatiHatasi(f"cumba {cephe} cephesinde {a:g}–{b:g} cm; cephe {boy:g} cm")
    if cephe == "on":
        return [x0 + a, y0, x0 + b, y0]
    if cephe == "arka":
        return [x0 + a, y1, x0 + b, y1]
    if cephe == "sol":
        return [x0, y0 + a, x0, y0 + b]
    return [x1, y0 + a, x1, y0 + b]


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


def cati(plan: G.Plan, ie: dict) -> dict:
    """Beşik dışı ana çatı → genel motorun `cati` biçimi. Dönen sözlük köprünün beşik çatısıyla aynı anahtarlarda (`tip`, `tip_adi`,
    `sacak`, `topuk`, `duvar_ustu`, `ust_pay`, `duzlemler`, `kalkanlar`)."""
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
    if tip == "kirma":
        ayak = [list(kutu)]
        try:
            u = CU.uret(ayak, "kirma", mahya=mahya, egim_yuzde=float(c["egim_yuzde"]), duvar_ustu=H0, kural=k)
        except CU.CatiHatasi as e:
            raise PrefabrikCatiHatasi(f"kırma çatı: {e}")
        if c.get("kirma_egimleri"):                  # uç yüzler paftadaki eğimle (ana yüzler ve mahya yönü üreticinin denetiminden geçti)
            from .genel import cati_ortak as CO
            u["duzlemler"] = _kirma_farkli(kutu, mahya, round(float(c["egim_yuzde"]) / 100, 5), dict(c["kirma_egimleri"]),
                                           CO.baglam(k, round(float(c["egim_yuzde"]) / 100, 5), H0), k)
    else:
        ayak = [list(kutu), _cumba(c, kutu)]
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
