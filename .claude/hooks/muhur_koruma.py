#!/usr/bin/env python3
"""Mühürlü konular freni (BK-20, D-42).

Lokman, 1 Kasım 2026 20:16: "bir daha değişmemek üzere bu konuyu mühürle taki ben yeni bir değişiklik verene kadar sen yorumlama";
20:25: "hook diye bir şey varmış yapay zeka'nın sağa sola sapmaması için bunu uygula emeklerimiz boşa gitmesin".

Kayıt `KARARLAR/muhurlu.json`: her mühürlü konunun kuralı, kararı, Lokman'ın sözü ve kilitleri. Kilit, kuralı sabitleyen bir yerdir
(kural kitabının anahtarı, hedef örnek, testin kendisi) ve izi (sha256'nın ilk 16 hanesi) kayıtta durur. Yer biçimleri:
  yol                       dosyanın tamamı
  yol::Ad                   Python: üst düzey işlev, sınıf ya da atama (süsleyicileriyle); `Sınıf.üye`; `Ad[anahtar]` sözlük atamasının bir anahtarı
  yol#a.b[alan=değer].c     JSON: anahtar yolu; `[alan=değer]` listede o alanı o değer olan öğeler (birden çoksa liste; sonraki anahtar her birine)
  yol@desen                 metin: deseni tutan satırlar
  {son_referans}            `testler/referans/` altındaki en yeni tarihli klasör

Kipler (ilk argüman; hook'lar `.claude/settings.json`'da):
  duzenleme    PreToolUse Edit|Write|MultiEdit: mühürlü bir kilidin içeriğini değiştiren düzenleme ENGEL (dosyanın öteki yerleri serbest);
               kayıt zayıflatılamaz (mühür kaldırma, açma, kilit ya da söz değiştirme ENGEL; yeni mühür ve yeni kilit serbest);
               frenin kendi dosyaları SOR (CLAUDE.md › Frenler: hook değişikliği Lokman'ın onayıyla).
  komut        PreToolUse Bash: mühürlü bir yolu anan ve yazan komut ENGEL; mühür açma (`ac`) SOR: Lokman onaylar.
  komut_sonu   PostToolUse Bash: çalışma ağacı kayıtla uyuşmuyorsa (bir betik mühürlü yeri değiştirdiyse) geri bildirim.
  oturum       SessionStart: mühürlü listeyi oturumun bağlamına yazar.
  liste | denetle | ac KOD --soz … | kapat KOD --karar D-NN | kilitle [KOD]   elle (açma Lokman'ın açık sözüyle).
Yalnız standart kütüphane. Hook kiplerinde beklenmeyen hata akışı durdurmaz (çıkış 0); asıl son kapı CI'daki kilit testi
(`testler/test_muhurlu_konular.py`) ve `main`'e birleştirmede Lokman'ın onayıdır.
"""
from __future__ import annotations

import ast
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

KAYIT = "KARARLAR/muhurlu.json"
MUHURLU = "mühürlü"
ACIK = "açık"
YOK = object()
BU = Path(__file__).resolve()
KOMUT = "python3 .claude/hooks/muhur_koruma.py"


# ---------------------------------------------------------------- kayıt ve izler

def kayit_oku(kok: Path) -> dict | None:
    p = kok / KAYIT
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def kayit_yaz(kok: Path, kayit: dict) -> None:
    (kok / KAYIT).write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def son_referans(kok: Path) -> str:
    ref = kok / "testler" / "referans"
    adlar = sorted(p.name for p in ref.iterdir() if p.is_dir() and re.fullmatch(r"20\d\d-\d\d-\d\d[a-z]?", p.name)) if ref.is_dir() else []
    return f"testler/referans/{adlar[-1]}" if adlar else "testler/referans/YOK"


def ayir(yer: str, kok: Path) -> tuple[str, str | None, str | None]:
    """Yer → (göreli yol, tür, seçici). Tür: None (dosya), 'py', 'json', 'satir'."""
    if "{son_referans}" in yer:
        yer = yer.replace("{son_referans}", son_referans(kok))
    for ayrac, tur in (("::", "py"), ("#", "json"), ("@", "satir")):
        if ayrac in yer:
            yol, secici = yer.split(ayrac, 1)
            return yol, tur, secici
    return yer, None, None


def _py(metin: str, ad: str) -> str | object:
    try:
        agac = ast.parse(metin)
    except SyntaxError:
        return YOK
    anahtar = None
    m = re.fullmatch(r"(.+?)\[(.+)\]", ad)
    if m:
        ad, anahtar = m[1], m[2]
    govde, dugum = agac.body, None
    for parca in ad.split("."):
        dugum = None
        for n in govde:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == parca:
                dugum = n
            elif isinstance(n, ast.Assign) and any(isinstance(h, ast.Name) and h.id == parca for h in n.targets):
                dugum = n
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == parca:
                dugum = n
        if dugum is None:
            return YOK
        govde = getattr(dugum, "body", [])
    if anahtar is not None:
        deger = getattr(dugum, "value", None)
        if not isinstance(deger, ast.Dict):
            return YOK
        for k, v in zip(deger.keys, deger.values):
            if isinstance(k, ast.Constant) and str(k.value) == anahtar:
                return ast.get_source_segment(metin, v) or YOK
        return YOK
    bas = min([dugum.lineno] + [d.lineno for d in getattr(dugum, "decorator_list", [])])
    return "\n".join(metin.splitlines()[bas - 1:dugum.end_lineno])


def _json(metin: str, secici: str) -> str | object:
    try:
        veri = json.loads(metin)
    except ValueError:
        return YOK
    for m in re.finditer(r"\[([^=\]]+)=([^\]]*)\]|([^.\[\]]+)", secici):
        if m[3] is not None:
            if isinstance(veri, dict):
                if m[3] not in veri:
                    return YOK
                veri = veri[m[3]]
            elif isinstance(veri, list) and all(isinstance(x, dict) and m[3] in x for x in veri):
                veri = [x[m[3]] for x in veri]
            else:
                return YOK
        else:
            if not isinstance(veri, list):
                return YOK
            secilen = [x for x in veri if isinstance(x, dict) and str(x.get(m[1])) == m[2]]
            if not secilen:
                return YOK
            veri = secilen[0] if len(secilen) == 1 else secilen
    return json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deger(yer: str, kok: Path, metin: str | None = YOK) -> str | object:
    """Kilidin içeriği (metin); yer bulunamazsa YOK. `metin` verilirse dosya yerine o okunur (düzenlemenin benzetimi)."""
    yol, tur, secici = ayir(yer, kok)
    if metin is YOK:
        p = kok / yol
        if not p.is_file():
            return YOK
        try:
            metin = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return hashlib.sha256(p.read_bytes()).hexdigest() if tur is None else YOK
    if metin is None:
        return YOK
    if tur is None:
        return metin
    if tur == "py":
        return _py(metin, secici)
    if tur == "json":
        return _json(metin, secici)
    satirlar = [s for s in metin.splitlines() if re.search(secici, s)]
    return "\n".join(satirlar) if satirlar else YOK


def iz(icerik: str | object) -> str:
    return "YOK" if icerik is YOK else hashlib.sha256(icerik.encode("utf-8")).hexdigest()[:16]


def muhurluler(kayit: dict) -> list[dict]:
    return [m for m in kayit.get("muhurler", []) if m.get("durum") == MUHURLU]


def bozuklar(kok: Path, kayit: dict) -> list[tuple[dict, dict, str]]:
    """Mühürlü konularda izi kayıtla uyuşmayan kilitler: (mühür, kilit, şimdiki iz)."""
    out = []
    for m in muhurluler(kayit):
        for k in m.get("kilitler", []):
            simdi = iz(deger(k["yer"], kok))
            if simdi != k.get("iz"):
                out.append((m, k, simdi))
    return out


def ozet(m: dict) -> str:
    soz = m.get("lokman", [{}])[-1]
    return f"{m['kod']} {m['konu']} ({', '.join(m.get('kararlar', []))}; Lokman {soz.get('tarih', '?')}: \"{soz.get('soz', '')}\")"


# ---------------------------------------------------------------- hook çıktıları

def _cik(cikti: dict | None = None) -> None:
    if cikti:
        print(json.dumps(cikti, ensure_ascii=False))
    sys.exit(0)


def _karar(decision: str, reason: str) -> None:
    _cik({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}})


def _kok(veri: dict) -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or veri.get("cwd") or os.getcwd()).resolve()


def _gorece(yol: str, kok: Path) -> str:
    p = Path(yol)
    if not p.is_absolute():
        p = kok / p
    try:
        return p.resolve().relative_to(kok).as_posix()
    except ValueError:
        return p.as_posix()


def _engel_metni(degisen: list[tuple[dict, dict]]) -> str:
    konular = {}
    for m, k in degisen:
        konular.setdefault(m["kod"], (m, []))[1].append(k["yer"])
    satirlar = ["MÜHÜRLÜ KONU: Patron onayı gerekir. Bu değişiklik Lokman'ın mühürlediği bir kuralı sabitleyen yere dokunuyor:"]
    for m, yerler in konular.values():
        satirlar.append(f"- {ozet(m)}. Kural: {m['kural']} Değişen yer: {', '.join(yerler)}.")
    kod = next(iter(konular))
    satirlar.append(
        "Mühürlü konu Lokman yeni bir değişiklik verene kadar değiştirilmez ve yorumlanmaz; eski sohbete ya da başka konunun kararına "
        "dayanılarak açılmaz (AGENTS.md › Mühürlü konular). Yapılacak: Lokman'a tek satırla sorun ve cevabını bekleyin. Lokman bu konuda "
        f"açıkça yeni bir değişiklik verdiyse mühürü onun sözüyle açın: `{KOMUT} ac {kod} --soz \"<Lokman'ın sözü, kelimesi kelimesine>\" "
        f"--mesaj <mesaj no>`; iş bitince yeni kararla kapatın: `{KOMUT} kapat {kod} --karar D-NN`.")
    return "\n".join(satirlar)


def _benzet(ad: str, ti: dict, eski: str | None) -> str | None | object:
    """Düzenlemeden sonraki metin; benzetilemezse YOK (araç da başaramayacak: eski metin dosyada yok)."""
    if ad == "Write":
        return str(ti.get("content") or "")
    duzen = ti.get("edits") if ad == "MultiEdit" else [ti]
    metin = eski or ""
    for e in duzen or []:
        once, sonra = str(e.get("old_string") or ""), str(e.get("new_string") or "")
        if once == "":
            if eski is not None:
                return YOK
            metin = sonra
            continue
        if once not in metin:
            return YOK
        metin = metin.replace(once, sonra) if e.get("replace_all") else metin.replace(once, sonra, 1)
    return metin


def zayiflatmalar(eski: dict, yeni_metin: str) -> list[str]:
    """Kayıtta mühürlü bir konuyu gevşeten değişiklikler (yeni mühür ve yeni kilit eklemek serbest)."""
    try:
        yeni = json.loads(yeni_metin)
    except ValueError as h:
        return [f"kayıt JSON olarak okunmuyor ({h})"]
    yk = {m.get("kod"): m for m in yeni.get("muhurler", [])}
    out = []
    for m in muhurluler(eski):
        n = yk.get(m["kod"])
        if n is None:
            out.append(f"{m['kod']} kayıttan kalkıyor (mühür silinmez)")
            continue
        if n.get("durum") != MUHURLU:
            out.append(f"{m['kod']} açılıyor (yalnız `ac` komutuyla, Lokman'ın sözüyle)")
        if not {(k["yer"], k.get("iz")) for k in m.get("kilitler", [])} <= {(k.get("yer"), k.get("iz")) for k in n.get("kilitler", [])}:
            out.append(f"{m['kod']} kilitlerinden biri kalkıyor ya da izi değişiyor")
        for alan in ("konu", "kural", "kararlar", "lokman", "gecmis"):
            if n.get(alan) != m.get(alan):
                out.append(f"{m['kod']} `{alan}` alanı değişiyor")
    if set(eski.get("cekirdek", [])) - set(yeni.get("cekirdek", [])):
        out.append("frenin dosyalarından biri çekirdek listesinden çıkıyor")
    return out


def kip_duzenleme(veri: dict) -> None:
    ti = veri.get("tool_input") or {}
    kok = _kok(veri)
    kayit = kayit_oku(kok)
    if kayit is None:
        _cik()
    gorece = _gorece(str(ti.get("file_path") or ""), kok)
    p = kok / gorece
    eski = p.read_text(encoding="utf-8") if p.is_file() else None
    yeni = _benzet(str(veri.get("tool_name") or ""), ti, eski)
    if gorece == KAYIT:
        if yeni is YOK:
            _cik()
        hatalar = zayiflatmalar(kayit, yeni)
        if hatalar:
            _karar("deny", "MÜHÜRLÜ KONU: Patron onayı gerekir. Bu düzenleme mühürlü konuları gevşetiyor: " + "; ".join(hatalar)
                   + f". Mühür yalnız Lokman'ın açık sözüyle açılır: `{KOMUT} ac <KOD> --soz \"…\" --mesaj <mesaj no>`; "
                   "yeni mühür ve yeni kilit eklemek serbesttir (izleri `kilitle` doldurur).")
        _cik()
    if gorece in kayit.get("cekirdek", []):
        _karar("ask", "Mühür freninin kendi dosyası (" + gorece + "). Hook'u değiştirmek ya da kapatmak Lokman'ın onayını gerektirir "
               "(CLAUDE.md › Frenler). Lokman, onaylıyor musunuz?")
    ilgili = [(m, k) for m in muhurluler(kayit) for k in m.get("kilitler", []) if ayir(k["yer"], kok)[0] == gorece]
    if not ilgili or yeni is YOK:
        _cik()
    degisen = [(m, k) for m, k in ilgili if iz(deger(k["yer"], kok, eski)) != iz(deger(k["yer"], kok, yeni))]
    if degisen:
        _karar("deny", _engel_metni(degisen))
    _cik()


YAZAN = re.compile(r"\bsed\b[^|;&\n]*\s-(?:[a-zA-Z]*i|-in-place)|\bperl\b[^|;&\n]*\s-[a-zA-Z]*i|\btee\b|\b(?:mv|cp|rm|truncate|dd|ln|install|patch|unlink)\s"
                   r"|\bgit\s+(?:checkout|restore|apply|mv|rm|am|cherry-pick|revert|reset|stash)\b|open\([^)]*['\"][wax]|write_(?:text|bytes)\(|\.write\(|json\.dump\(")


def kip_komut(veri: dict) -> None:
    komut = str((veri.get("tool_input") or {}).get("command") or "")
    kok = _kok(veri)
    kayit = kayit_oku(kok)
    if kayit is None:
        _cik()
    m = re.search(r"muhur_koruma\.py['\"]?\s+ac\s+(\S+)", komut)
    if m:
        soz = re.search(r"--soz\s+(\"[^\"]*\"|'[^']*'|\S+)", komut)
        _karar("ask", f"Mühür açılıyor: {m[1]}. Gerekçe olarak yazılan Lokman sözü: {soz[1] if soz else '(yok)'}. "
               "Mühürlü konu yalnız Lokman'ın açık sözüyle açılır; bu adımı Lokman onaylar.")
    yollar = {ayir(k["yer"], kok)[0] for mm in muhurluler(kayit) for k in mm.get("kilitler", [])} | {KAYIT} | set(kayit.get("cekirdek", []))
    yonlendirme = {h.strip("'\"") for h in re.findall(r"(?<![0-9&<])>>?\s*([^\s;&|<>]+)", komut)}
    anilan = sorted(y for y in yollar if y in komut)
    hedef = sorted(y for y in yollar if any(h == y or h.endswith("/" + y) for h in yonlendirme))
    if hedef or (anilan and YAZAN.search(komut)):
        _karar("deny", "MÜHÜRLÜ KONU: Patron onayı gerekir. Bu komut mühürlü bir yere yazıyor gibi görünüyor: " + ", ".join(hedef or anilan)
               + ". Mühürlü yerler Lokman yeni bir değişiklik verene kadar değişmez (AGENTS.md › Mühürlü konular); okumak serbest. "
               "Dosyanın mühürsüz yerleri Edit aracıyla değiştirilir (kilit düzeyinde denetlenir; komut dosyanın neresine yazdığını söylemez). "
               f"Liste: `{KOMUT} liste`. Lokman açıkça yeni değişiklik verdiyse önce `{KOMUT} ac <KOD> --soz \"…\"`.")
    _cik()


def kip_komut_sonu(veri: dict) -> None:
    kok = _kok(veri)
    try:
        kayit = kayit_oku(kok)
    except ValueError:
        _cik({"decision": "block", "reason": f"{KAYIT} okunmuyor (JSON bozuk). Düzeltin; mühür kaydı bozuk kalamaz."})
    if kayit is None:
        _cik()
    b = bozuklar(kok, kayit)
    if b:
        metin = _engel_metni([(m, k) for m, k, _ in b]).replace(
            "Bu değişiklik", "Son komuttan sonra çalışma ağacında") + " Değişikliği geri alın (Lokman'ın yeni sözü yoksa) ve devam etmeden önce Lokman'a sorun."
        _cik({"decision": "block", "reason": metin, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": metin}})
    _cik()


def kip_oturum(veri: dict) -> None:
    kok = _kok(veri)
    kayit = kayit_oku(kok)
    if kayit is None:
        _cik()
    satirlar = ["MÜHÜRLÜ KONULAR (Lokman; AGENTS.md › Mühürlü konular, kayıt KARARLAR/muhurlu.json). Lokman yeni bir değişiklik verene kadar "
                "değiştirilmez ve yorumlanmaz; eski sohbete ya da başka konunun kararına dayanılarak açılmaz. Bu konulara dokunacak iş önce "
                "Lokman'a tek satırla sorar. Mühürlü yerleri değiştiren düzenleme hook'la durur."]
    for m in kayit.get("muhurler", []):
        satirlar.append(f"- {ozet(m)} [{m.get('durum')}]: {m['kural']}")
    b = bozuklar(kok, kayit)
    if b:
        satirlar.append("UYARI: çalışma ağacında izi kayıtla uyuşmayan mühürlü yer var: " + ", ".join(f"{m['kod']} {k['yer']}" for m, k, _ in b))
    _cik({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(satirlar)}})


# ---------------------------------------------------------------- elle kullanılan komutlar

def _simdi() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _bul(kayit: dict, kod: str) -> dict:
    for m in kayit.get("muhurler", []):
        if m.get("kod") == kod:
            return m
    sys.exit(f"{kod} kayıtta yok")


def elle(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="muhur_koruma.py", description="Mühürlü konular (KARARLAR/muhurlu.json)")
    ap.add_argument("--kok", default=str(BU.parents[2]))
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("liste")
    alt.add_parser("denetle")
    a = alt.add_parser("ac", help="Lokman'ın açık sözüyle mühürü açar")
    a.add_argument("kod")
    a.add_argument("--soz", required=True)
    a.add_argument("--mesaj", default="")
    a.add_argument("--tarih", default="")
    k = alt.add_parser("kapat", help="açık mühürün izlerini yeniden alır ve mühürler")
    k.add_argument("kod")
    k.add_argument("--karar", required=True)
    i = alt.add_parser("kilitle", help="izi boş kilitlere iz yazar (var olan ize dokunmaz)")
    i.add_argument("kod", nargs="?")
    o = ap.parse_args(argv)
    kok = Path(o.kok).resolve()
    kayit = kayit_oku(kok)
    if kayit is None:
        sys.exit(f"{KAYIT} yok")
    if o.komut == "liste":
        for m in kayit["muhurler"]:
            print(f"{m['kod']}  [{m['durum']}]  {m['konu']}  ({', '.join(m.get('kararlar', []))}; {len(m.get('kilitler', []))} kilit)")
        return 0
    if o.komut == "denetle":
        sorun = [f"{m['kod']} açık kaldı ({m.get('acilis', {}).get('soz', '')})" for m in kayit["muhurler"] if m.get("durum") != MUHURLU]
        sorun += [f"{m['kod']} {k['yer']}: kayıt {k.get('iz')}, şimdi {s}" for m, k, s in bozuklar(kok, kayit)]
        print("\n".join(sorun) if sorun else f"mühürler sağlam ({len(kayit['muhurler'])} konu)")
        return 1 if sorun else 0
    m = _bul(kayit, o.kod) if o.kod else None
    if o.komut == "ac":
        if m["durum"] != MUHURLU:
            sys.exit(f"{o.kod} zaten {m['durum']}")
        m["durum"] = ACIK
        m["acilis"] = {"tarih": o.tarih or _simdi(), "soz": o.soz, "mesaj": o.mesaj}
    elif o.komut == "kapat":
        if m["durum"] != ACIK or "acilis" not in m:
            sys.exit(f"{o.kod} açık değil; önce Lokman'ın sözüyle `ac`")
        if not (kok / "KARARLAR" / f"{o.karar}.md").is_file():
            sys.exit(f"KARARLAR/{o.karar}.md yok; yeni durum önce kararla yazılır")
        for kl in m["kilitler"]:
            kl["iz"] = iz(deger(kl["yer"], kok))
        m.setdefault("gecmis", []).append({**m.pop("acilis"), "kapanis": _simdi(), "karar": o.karar})
        if o.karar not in m.setdefault("kararlar", []):
            m["kararlar"].append(o.karar)
        m["durum"] = MUHURLU
    elif o.komut == "kilitle":
        for mm in ([m] if m else kayit["muhurler"]):
            for kl in mm["kilitler"]:
                if not kl.get("iz"):
                    kl["iz"] = iz(deger(kl["yer"], kok))
                    print(f"{mm['kod']} {kl['yer']}: {kl['iz']}")
    kayit_yaz(kok, kayit)
    print(f"{o.komut} tamam")
    return 0


KIPLER = {"duzenleme": kip_duzenleme, "komut": kip_komut, "komut_sonu": kip_komut_sonu, "oturum": kip_oturum}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in KIPLER:
        try:
            veri = json.load(sys.stdin)
        except Exception:
            sys.exit(0)
        try:
            KIPLER[sys.argv[1]](veri)
        except SystemExit:
            raise
        except Exception as h:  # fren bozuksa akışı durdurmaz, söyler
            print(f"muhur_koruma: {h}", file=sys.stderr)
            sys.exit(0)
    sys.exit(elle(sys.argv[1:]))
