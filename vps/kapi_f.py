#!/usr/bin/env python3
"""PORTMAN · Kapı F (İE-02): dosya düzeninden Postgres'e geçişin DEĞER YAZMAYAN özet ve karşılaştırması. Hiçbir şeyi değiştirmez.

  ozet KANAL [--json ÇIKTI]
      Hosting yedeğinin (state.json, durum/, projects/, settings.json) özeti. Mac'te, yalnız standart kütüphaneyle çalışır.
      Boşalma (işlenmekte ya da gönderimde satır var mı), kuyruk (ücretli işlem doğuracak mesaj var mı), aktarılacak kayıtlar,
      konuşmaların toplu özeti, E projesi (konuşma, iş, giden satırlar, PDF), anahtar biçimli dizge taraması.

  karsilastir KANAL --veri /opt/portman/data [--yalniz-kaynak]
      VPS'te, portman kullanıcısıyla (PORTMAN_PG_DSN): aynı kaynak özetini Postgres'teki kayıtlarla karşılaştırır.
      Konuşmalar, mesajlar ve işler birebir mi; E projesinin r01 durumu, konuşmayla ilişkisi ve PDF'i korunmuş mu.
      Uyuşmazlıkta çıkış kodu 2.

Yazdırmaz: telefon numarası, mesaj metni, WhatsApp kimliği, anahtar, kişi adı. Numara yerine yalnız toplu özetler ve sayılar;
durum/ altındaki dosya adları numara olduğu için hiçbir çıktıda yok.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HEDEF_PROJE = "PM-PATRON-20260929-33807"
IS_DURUMU = {"queued": "sirada", "done": "bitti", "failed": "basarisiz"}      # kanal/depo_aktar.py ile aynı
YAZILI = ("text", "button", "interactive")                                    # kanal/worker.py GELEN_YAZILI: LLM çağrısı yapılır
GONDERIMDE = ("pending", "uploading", "sending")
ANAHTAR = re.compile(rb"(?<![A-Za-z0-9+/=._\-])(?:sk-ant-[A-Za-z0-9_\-]{20,}|sk-(?:proj-)?[A-Za-z0-9_\-]{20,}|EAA[A-Za-z0-9]{20,})"
                     rb"|\"(?:openai_key|api_key|access_token|app_secret|verify_token|token)\"\s*:\s*\"[^\"]{8,}\"")
METIN_UZANTI = {".json", ".txt", ".php", ".md", ".csv", ".log", ".env", ".ini", ".conf", ".yml", ".yaml"}


def kanon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def ozet_hash(satirlar) -> str:
    h = hashlib.sha256()
    for s in sorted(satirlar):
        h.update(s.encode("utf-8")); h.update(b"\n")
    return h.hexdigest()[:16]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def say(it) -> dict:
    d: dict = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: str(kv[0])))


# ───────────────────────── kaynak (dosya düzeni) ─────────────────────────
def kaynak(kanal: Path, proje: str = HEDEF_PROJE) -> dict:
    kanal = Path(kanal)
    stp = kanal / "state.json"
    st = json.loads(stp.read_text(encoding="utf-8")) if stp.exists() else {}
    inbound = st.get("inbound") or {}; outbound = st.get("outbound") or {}
    if isinstance(inbound, list): inbound = {}
    if isinstance(outbound, list): outbound = {}
    k: dict = {"state_sha256": sha(stp) if stp.exists() else None, "state_boyut": stp.stat().st_size if stp.exists() else 0}

    # gelen: depo_aktar.ice_aktar'ın kuralları
    aktar, kuyruk, atla, yarim = [], [], 0, 0
    for mid, g in inbound.items():
        if not str(mid).startswith("wamid.") or g.get("self_test"):
            atla += 1; continue
        if g.get("state") == "processing":
            yarim += 1
        if g.get("state") == "queued":
            kuyruk.append(g); continue
        aktar.append((mid, g))
    k["gelen"] = {"toplam": len(inbound), "durumlar": say(str(g.get("state")) for g in inbound.values()), "atlanan": atla,
                  "islenmekte": yarim, "kuyrukta": len(kuyruk), "aktarilacak": len(aktar),
                  "aktarilacak_durum": say(IS_DURUMU.get(g.get("state"), "basarisiz") for _, g in aktar)}
    simdi = time.time()
    k["kuyruk"] = [{"rol": g.get("role") or "bayi", "tur": g.get("type"),
                    "llm_cagrisi": g.get("type") in YAZILI and bool(str(g.get("text") or "").strip()),
                    "yas_dk": round((simdi - float(g.get("received_at") or g.get("timestamp") or simdi)) / 60, 1)} for g in kuyruk]
    k["mesaj_ozeti"] = ozet_hash(f"{mid}\0{g.get('sender')}\0{IS_DURUMU.get(g.get('state'), 'basarisiz')}\0{kanon(g.get('result'))}"
                                 for mid, g in aktar)
    k["bayi_sayisi"] = len({str(g.get("sender")) for _, g in aktar if isinstance(g.get("bayi"), dict)})
    k["giden"] = {"toplam": len(outbound), "durumlar": say(str(r.get("state")) for r in outbound.values()),
                  "gonderimde": sum(str(r.get("state")) in GONDERIMDE for r in outbound.values())}

    # konuşmalar
    durumlar = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((kanal / "durum").glob("*.json"))} \
        if (kanal / "durum").is_dir() else {}
    k["konusma"] = {"sayi": len(durumlar), "asamalar": say(str(d.get("asama")) for d in durumlar.values()),
                    "askida_soru": sum(bool(d.get("son_soru_alani")) for d in durumlar.values()),
                    "ozet": ozet_hash(f"{g}\0{kanon(d)}" for g, d in durumlar.items())}

    # E projesi
    e: dict = {"no": proje}
    kz = [(g, d) for g, d in durumlar.items() if ((d.get("son_is_emri") or {}).get("is_emri_no")) == proje]
    e["konusma_sayisi"] = len(kz)
    if kz:
        g0, d0 = kz[0]
        e["konusma"] = {"asama": d0.get("asama"), "son_is_emri_rev": (d0.get("son_is_emri") or {}).get("revizyon"),
                        "revizyon_sayaci": d0.get("revizyon"), "proje_id": d0.get("proje_id"), "ozet": ozet_hash([f"{g0}\0{kanon(d0)}"])}
    iz = [(mid, g) for mid, g in inbound.items() if ((g.get("result") or {}).get("is_emri_no")) == proje]
    e["gelen_sayisi"] = len(iz)
    if iz:
        mid, g = iz[0]; s = g.get("result") or {}; cz = s.get("cizim") or {}
        e["gelen"] = {"durum": g.get("state"), "eylem": s.get("eylem"), "revizyon": s.get("revizyon"),
                      "pdf": Path(str(cz.get("pdf") or "")).name or None, "pdf_sha": (cz.get("pdf_sha256") or "")[:16] or None,
                      "dogrulama": cz.get("passed"), "konusmayla_ayni_kisi": bool(kz) and str(g.get("sender")) == kz[0][0]}
        satir = [r for r in outbound.values() if r.get("inbound_id") == mid]
        e["giden"] = []
        for r in sorted(satir, key=lambda r: r.get("seq") or 0):
            b = {"sira": r.get("seq"), "tur": r.get("kind"), "durum": r.get("state"), "teslim": r.get("delivery_state")}
            if r.get("kind") == "document":
                f = str(r.get("file") or ""); i = f.find("projects/")
                yerel = kanal / f[i:] if i >= 0 else None
                b.update(dosya=Path(f).name, sha=(r.get("sha256") or "")[:16], hosting_kopyasi=bool(yerel and yerel.is_file()),
                         hosting_kopyasi_sha_ayni=bool(yerel and yerel.is_file() and sha(yerel) == r.get("sha256")))
            e["giden"].append(b)
    rk = kanal / "projects" / proje
    e["dosyalar"] = {str(p.relative_to(rk)): {"boyut": p.stat().st_size, "sha": sha(p)[:16]}
                     for p in sorted(rk.rglob("*")) if p.is_file()} if rk.is_dir() else {}
    k["e"] = e
    return k


def tarama(kok: Path) -> dict:
    """Metin dosyalarında anahtar biçimli dizge; durum/ altındaki adlar (numara) yazılmaz."""
    isabet = []; n = 0
    for p in sorted(Path(kok).rglob("*")):
        if not p.is_file() or p.suffix.lower() not in METIN_UZANTI:
            continue
        n += 1
        try:
            if ANAHTAR.search(p.read_bytes()):
                r = p.relative_to(kok).as_posix()
                isabet.append("durum/<gizli>" if "/durum/" in "/" + r else r)
        except OSError:
            pass
    return {"taranan": n, "isabet": isabet, "api_token_dosyasi": any(p.name.startswith("api_token") for p in Path(kok).rglob("*"))}


def ayarlar(kanal: Path) -> dict | None:
    p = Path(kanal) / "settings.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text(encoding="utf-8"))
    llm = s.get("llm") if isinstance(s.get("llm"), dict) else {}
    return {"worker": s.get("worker"), "enabled": s.get("enabled"), "mode": s.get("mode"), "dry_run": s.get("dry_run"),
            "llm": f"{llm.get('backend')}/{llm.get('model')}", "patron_teknik_not": s.get("patron_teknik_not"), "anahtarlar": sorted(s)}


def yaz_kaynak(k: dict, baslik: str) -> None:
    print(f"-- {baslik}")
    print(f"   state.json sha256 {k['state_sha256']} · {k['state_boyut']} B")
    g = k["gelen"]
    print(f"   gelen: {g['toplam']} satır · durumlar {g['durumlar']} · öz-test/kimliksiz {g['atlanan']}")
    print(f"   aktarılacak {g['aktarilacak']} {g['aktarilacak_durum']} · kuyrukta bırakılacak {g['kuyrukta']} · işlenmekte {g['islenmekte']}")
    print(f"   mesaj/iş özeti {k['mesaj_ozeti']} · bayi/patron kaydı {k['bayi_sayisi']}")
    print(f"   giden: {k['giden']['toplam']} satır · durumlar {k['giden']['durumlar']} · gönderimde (pending/uploading/sending) {k['giden']['gonderimde']}")
    c = k["konusma"]
    print(f"   konuşma: {c['sayi']} · aşamalar {c['asamalar']} · askıda soru {c['askida_soru']} · toplu özet {c['ozet']}")
    if k["kuyruk"]:
        print(f"   KUYRUKTA {len(k['kuyruk'])} mesaj: " + "; ".join(f"{q['rol']} {q['tur']} {q['yas_dk']} dk"
                                                            + (" (LLM çağrısı olur)" if q["llm_cagrisi"] else "") for q in k["kuyruk"]))
    e = k["e"]
    print(f"-- E projesi {e['no']} (kaynak)")
    print(f"   konuşma: {e['konusma_sayisi']} · {e.get('konusma')}")
    print(f"   gelen: {e['gelen_sayisi']} · {e.get('gelen')}")
    for b in e.get("giden") or []:
        print(f"   giden: {b}")
    for ad, v in e["dosyalar"].items():
        print(f"   hosting projects/{e['no']}/{ad}: {v['boyut']} B · {v['sha']}")


# ───────────────────────── Postgres ─────────────────────────
def veritabani(proje: str, veri: Path) -> dict:
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(os.environ.get("PORTMAN_PG_DSN") or "dbname=portman", row_factory=dict_row) as c:
        tablolar = [r["tablename"] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")]
        v: dict = {"tablolar": tablolar}
        if "konusmalar" not in tablolar:
            return v
        v["sayilar"] = {t: c.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
                        for t in ("bayiler", "mesajlar", "isler", "konusmalar", "projeler", "revizyonlar", "sorular", "giden") if t in tablolar}
        v["goc"] = [r["surum"] for r in c.execute("SELECT surum FROM sema_surumu ORDER BY 1")] if "sema_surumu" in tablolar else []
        v["is_durum"] = {r["durum"]: r["n"] for r in c.execute("SELECT durum, count(*) AS n FROM isler GROUP BY 1 ORDER BY 1")}
        v["mesaj_ozeti"] = ozet_hash(f"{r['id']}\0{r['gonderen']}\0{r['durum']}\0{kanon(r['sonuc'])}" for r in c.execute(
            "SELECT m.id, m.gonderen, i.durum, i.sonuc FROM mesajlar m JOIN isler i ON i.mesaj_id = m.id"))
        kz = c.execute("SELECT gonderen, durum FROM konusmalar").fetchall()
        v["konusma"] = {"sayi": len(kz), "asamalar": say(str(r["durum"].get("asama")) for r in kz),
                        "ozet": ozet_hash(f"{r['gonderen']}\0{kanon(r['durum'])}" for r in kz)}
        v["acik_soru"] = c.execute("SELECT count(*) AS n FROM sorular WHERE durum = 'acik'").fetchone()["n"]
        e: dict = {"no": proje}
        ek = [r for r in kz if ((r["durum"].get("son_is_emri") or {}).get("is_emri_no")) == proje]
        e["konusma_sayisi"] = len(ek)
        if ek:
            d0 = ek[0]["durum"]
            e["konusma"] = {"asama": d0.get("asama"), "son_is_emri_rev": (d0.get("son_is_emri") or {}).get("revizyon"),
                            "revizyon_sayaci": d0.get("revizyon"), "proje_id": d0.get("proje_id"),
                            "ozet": ozet_hash([f"{ek[0]['gonderen']}\0{kanon(d0)}"])}
        ei = c.execute("SELECT m.gonderen, i.durum, i.sonuc FROM isler i JOIN mesajlar m ON m.id = i.mesaj_id "
                       "WHERE i.sonuc->>'is_emri_no' = %s ORDER BY i.id", (proje,)).fetchall()
        e["is_sayisi"] = len(ei)
        if ei:
            s = ei[0]["sonuc"] or {}; cz = s.get("cizim") or {}
            pdf = Path(str(cz.get("pdf") or ""))
            yerel = pdf if pdf.is_absolute() else Path(veri) / pdf
            e["is"] = {"durum": ei[0]["durum"], "eylem": s.get("eylem"), "revizyon": s.get("revizyon"), "pdf": pdf.name or None,
                       "pdf_sha": (cz.get("pdf_sha256") or "")[:16] or None, "konusmayla_ayni_kisi": bool(ek) and ei[0]["gonderen"] == ek[0]["gonderen"],
                       "vps_pdf_var": yerel.is_file(), "vps_pdf_sha_ayni": yerel.is_file() and sha(yerel) == cz.get("pdf_sha256")}
        e["proje_kaydi"] = c.execute("SELECT count(*) AS n FROM projeler WHERE ilk_is_emri_no = %s", (proje,)).fetchone()["n"]
        e["revizyon_kaydi"] = c.execute("SELECT count(*) AS n FROM revizyonlar WHERE is_emri_no = %s", (proje,)).fetchone()["n"]
        rk = Path(veri) / "projects" / proje
        e["vps_dosyalar"] = {str(p.relative_to(rk)): {"boyut": p.stat().st_size, "sha": sha(p)[:16]}
                             for p in sorted(rk.rglob("*")) if p.is_file()} if rk.is_dir() else {}
        v["e"] = e
    return v


def karsilastir(kanal: Path, veri: Path, proje: str, yalniz_kaynak: bool) -> int:
    k = kaynak(kanal, proje)
    yaz_kaynak(k, f"kaynak ({kanal})")
    v = veritabani(proje, veri)
    print("-- Postgres")
    print(f"   tablolar ({len(v['tablolar'])}): {' '.join(v['tablolar']) or 'yok'}")
    if "sayilar" not in v:
        print("   Portman tabloları yok (göç uygulanmamış)")
        return 0
    print(f"   göçler {v['goc']} · kayıt sayıları {v['sayilar']} · işler {v['is_durum']} · açık soru {v['acik_soru']}")
    print(f"   konuşma: {v['konusma']['sayi']} · aşamalar {v['konusma']['asamalar']} · toplu özet {v['konusma']['ozet']}")
    print(f"   mesaj/iş özeti {v['mesaj_ozeti']}")
    e = v["e"]
    print(f"-- E projesi {proje} (Postgres ve VPS dosyaları)")
    print(f"   konuşma: {e['konusma_sayisi']} · {e.get('konusma')}")
    print(f"   iş: {e['is_sayisi']} · {e.get('is')}")
    print(f"   projeler/revizyonlar kaydı: {e['proje_kaydi']}/{e['revizyon_kaydi']} (geçişten önceki plan: tablolara yazılmaz, tasarım gereği)")
    for ad, x in e["vps_dosyalar"].items():
        print(f"   VPS projects/{proje}/{ad}: {x['boyut']} B · {x['sha']}")
    if yalniz_kaynak:
        return 0
    s = v["sayilar"]; ke = k["e"]
    # Hosting'in PDF'i: kaynakta projects/ varsa dosyanın kendisi; aktarılan kopyada yoksa (yalnız state.json ve durum/ taşınır)
    # hosting'in giden satırında kayıtlı özet: api.php dosyayı alırken bu özeti dosyayla karşılaştırır (document_sha_mismatch).
    hosting_pdf = {a: x["sha"] for a, x in ke["dosyalar"].items() if a.endswith(".pdf")}
    hosting_pdf_kaynagi = "hosting'teki dosya"
    if not hosting_pdf:
        rev = f"r{int((ke.get('gelen') or {}).get('revizyon') or 1):02d}"
        hosting_pdf = {f"{rev}/{b['dosya']}": b["sha"] for b in ke.get("giden") or [] if b.get("tur") == "document"}
        hosting_pdf_kaynagi = "hosting'in giden satırındaki özet; kopyada projects/ yok"
    denetim = [
        ("konuşma sayısı", k["konusma"]["sayi"], v["konusma"]["sayi"]),
        ("konuşmaların toplu özeti (içerik birebir)", k["konusma"]["ozet"], v["konusma"]["ozet"]),
        ("aktarılan mesaj sayısı", k["gelen"]["aktarilacak"], s.get("mesajlar")),
        ("iş sayısı", k["gelen"]["aktarilacak"], s.get("isler")),
        ("iş durumları", k["gelen"]["aktarilacak_durum"], v["is_durum"]),
        ("mesaj/iş özeti (kimlik, gönderen, durum, sonuç)", k["mesaj_ozeti"], v["mesaj_ozeti"]),
        ("askıdaki soru", k["konusma"]["askida_soru"], v["acik_soru"]),
        ("bayi/patron kaydı", k["bayi_sayisi"], s.get("bayiler")),
        ("giden satır (aktarılmaz)", 0, s.get("giden")),
        ("E: konuşma", (ke["konusma_sayisi"], ke.get("konusma")), (e["konusma_sayisi"], e.get("konusma"))),
        ("E: iş sayısı", ke["gelen_sayisi"], e["is_sayisi"]),
        ("E: r01 iş sonucu", {a: (ke.get("gelen") or {}).get(a) for a in ("revizyon", "eylem", "pdf", "pdf_sha", "konusmayla_ayni_kisi")},
         {a: (e.get("is") or {}).get(a) for a in ("revizyon", "eylem", "pdf", "pdf_sha", "konusmayla_ayni_kisi")}),
        ("E: iş durumu", IS_DURUMU.get((ke.get("gelen") or {}).get("durum"), "basarisiz") if ke.get("gelen") else None, (e.get("is") or {}).get("durum")),
        ("E: VPS'teki PDF kayıttaki özetle aynı", True, (e.get("is") or {}).get("vps_pdf_sha_ayni")),
        (f"E: hosting'teki r01 PDF'i VPS'tekiyle aynı ({hosting_pdf_kaynagi})", hosting_pdf,
         {a: x["sha"] for a, x in e["vps_dosyalar"].items() if a.endswith(".pdf")}),
    ]
    hata = 0
    print("-- karşılaştırma (kaynak → Postgres)")
    for ad, a, b in denetim:
        ok = a == b
        hata += not ok
        print(f"   {'aynı ' if ok else 'FARKLI'} · {ad}" + ("" if ok else f": kaynak {a} · Postgres {b}"))
    print(f"== sonuç: {'kayıtlar birebir korundu' if not hata else f'{hata} UYUŞMAZLIK — DUR, bildir'}")
    return 0 if not hata else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    o = alt.add_parser("ozet"); o.add_argument("kanal"); o.add_argument("--json"); o.add_argument("--proje", default=HEDEF_PROJE)
    k = alt.add_parser("karsilastir"); k.add_argument("kanal"); k.add_argument("--veri", default="/opt/portman/data")
    k.add_argument("--proje", default=HEDEF_PROJE); k.add_argument("--yalniz-kaynak", action="store_true")
    ns = ap.parse_args(argv)
    if ns.komut == "karsilastir":
        return karsilastir(Path(ns.kanal), Path(ns.veri), ns.proje, ns.yalniz_kaynak)
    kanal = Path(ns.kanal)
    print(f"== Kapı F · hosting yedeği özeti · {time.strftime('%Y-%m-%d %H:%M:%S')} (değer yazılmaz)")
    a = ayarlar(kanal)
    print(f"-- settings.json: {a if a else 'yok'}")
    k = kaynak(kanal, ns.proje)
    yaz_kaynak(k, "state.json ve durum/")
    t = tarama(kanal)
    print(f"-- anahtar biçimli dizge: {t['taranan']} metin dosyası tarandı · isabet {len(t['isabet'])} {t['isabet'][:10]} · "
          f"api_token dosyası arşivde: {'EVET (olmamalı)' if t['api_token_dosyasi'] else 'yok'}")
    g = k["gelen"]
    bos = g["islenmekte"] == 0 and k["giden"]["gonderimde"] == 0
    print(f"== boşalma: {'tamam (işlenmekte ya da gönderimde satır yok)' if bos else 'BİTMEDİ'} · kuyrukta {g['kuyrukta']} mesaj"
          + (f", {sum(q['llm_cagrisi'] for q in k['kuyruk'])} tanesi LLM çağrısı doğurur" if k["kuyruk"] else ""))
    if ns.json:
        Path(ns.json).write_text(json.dumps({"ayarlar": a, "kaynak": k, "tarama": t}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
