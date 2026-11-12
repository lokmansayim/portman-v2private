#!/usr/bin/env python3
"""PORTMAN · talep ve revizyon formunu Meta'da TASLAK kurar, önizleme bağlantısını verir (İE-20, pano satır 110; root; yalnız standart
kitaplık, sistem python3 ile koşar).

Ne yapar (Meta Flows API, belge: developers.facebook.com › WhatsApp › Flows › Flows API):
  1. Belirteci /etc/portman/whatsapp.env'den okur (ekrana yalnız 12 haneli parmak izi). WABA kimliği --waba'dan, WA_WABA_ID satırından
     ya da belirtecin kapsamından (GET /debug_token, granular_scopes) gelir.
  2. Formlar sunucudaki sürümden okunur: <kök>/kanal/formlar/talep.json ve revizyon.json (canlı kodun sunduğu formun aynısı).
  3. Her form için WABA'daki formlar adıyla aranır (GET /<waba>/flows). Yoksa taslak kurulur (POST /<waba>/flows, publish false). Taslak
     varsa JSON'u güncellenir (POST /<flow>/assets). Yayımlanmışsa dokunulmaz.
  4. Formun durumu, Meta'nın doğrulama hataları ve önizleme bağlantısı yazılır (GET /<flow>?fields=…,preview.invalidate(false)).
     Önizleme girişsiz açılır, telefonda tarayıcıda denenir, 30 gün geçerlidir (Meta). Etkileşimli bağlantı formu, canlı kodun yeni
     bayiye sunduğu veriyle açar (kanal/talep_formu.py › ekran_verisi).
Ne yapmaz: mesaj göndermez (ücret yok), formu yayımlamaz (/publish çağrısı ve publish true yok), ayara ve sunucudaki dosyalara yazmaz,
servisleri yeniden başlatmaz, formu silmez, belirteci yazdırmaz (hata iletileri maskeli).

Koşum (Mac'ten; sunucuda kopyası yoksa geçici betik, AGENTS.md › Sunucu erişimi):
    curl -fsSL https://raw.githubusercontent.com/lokmansayim/portman-v2private/<commit>/vps/flow_taslak.py \
      | ssh portman-vps 'timeout 120 python3 -' > flow_taslak.txt 2>&1
Sunucuda kopyası varsa:
    ssh -n portman-vps 'timeout 120 python3 /opt/portman/guncel/vps/flow_taslak.py' > flow_taslak.txt 2>&1
Seçenekler: --waba <kimlik> · --kok <dizin> (formların sürümü; varsayılan betiğin deposu, yoksa /opt/portman/guncel) · --bak (Meta'da
hiçbir şeyi kurmaz ve değiştirmez; yalnız var olanı listeler). Çıkış: 0 tamam, 2 Meta doğrulama hatası buldu, 1 durdu.
Test için: PM_ETC, PM_GRAPH_BASE (ağa çıkılmaz).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ETC = os.environ.get("PM_ETC", "/etc/portman")
GUNCEL = "/opt/portman/guncel"
TURLER = ("talep", "revizyon")
AD = {"talep": "Portman Talep Formu", "revizyon": "Portman Revizyon Formu"}
KATEGORI = ["OTHER"]
KIMLIK = re.compile(r"^[0-9]{5,30}$")
BELIRTEC: str = ""


def iz(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:12]


def degisken(yol: str, ad: str) -> str | None:
    try:
        with open(yol, encoding="utf-8") as f:
            for s in f.read().splitlines():
                if s.startswith(ad + "="):
                    return s[len(ad) + 1:].strip() or None
    except FileNotFoundError:
        return None
    return None


def maskele(metin: str) -> str:
    """Belirteç ve belirtece benzeyen uzun diziler (≥ 40 harf/rakam) yazılmaz."""
    s = str(metin or "")
    if BELIRTEC:
        s = s.replace(BELIRTEC, "<belirteç>")
    return re.sub(r"[A-Za-z0-9_\-]{40,}", "<gizli>", s)


def graph_tabani() -> str:
    taban = os.environ.get("PM_GRAPH_BASE")
    if taban:
        return taban.rstrip("/")
    surum = degisken(os.path.join(ETC, "whatsapp.env"), "WA_GRAPH_VERSION") or "v23.0"
    if not re.fullmatch(r"v[0-9]{1,3}\.[0-9]{1,2}", surum):
        surum = "v23.0"
    return f"https://graph.facebook.com/{surum}"


def istek(yontem: str, yol: str, sorgu: dict | None = None, govde: dict | None = None,
          dosya: tuple[str, str, bytes, dict] | None = None) -> tuple[int, dict | None, str]:
    """Graph isteği; dönen (HTTP kodu, JSON, maskeli hata özeti). Belirteç yalnız Authorization başlığında (debug_token'da sorguda da)."""
    url = f"{graph_tabani()}/{yol}" + ("?" + urllib.parse.urlencode(sorgu) if sorgu else "")
    basliklar = {"Authorization": "Bearer " + BELIRTEC, "User-Agent": "portman-flow-taslak"}
    veri = None
    if govde is not None:
        veri = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        basliklar["Content-Type"] = "application/json"
    elif dosya is not None:
        alan, dosya_adi, icerik, alanlar = dosya
        sinir = "portman" + uuid.uuid4().hex
        parca = []
        for k, v in alanlar.items():
            parca.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
        parca.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{alan}"; filename="{dosya_adi}"\r\n'
                     f"Content-Type: application/json\r\n\r\n".encode("utf-8") + icerik + b"\r\n")
        parca.append(f"--{sinir}--\r\n".encode("utf-8"))
        veri = b"".join(parca)
        basliklar["Content-Type"] = f"multipart/form-data; boundary={sinir}"
    req = urllib.request.Request(url, data=veri, headers=basliklar, method=yontem)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}"), ""
    except urllib.error.HTTPError as e:
        try:
            g = json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            g = {}
        h = (g.get("error") if isinstance(g, dict) else None) or {}
        ozet = " · ".join(str(x) for x in (h.get("code"), h.get("error_subcode"), h.get("type"),
                                          h.get("error_user_msg") or h.get("message")) if x not in (None, ""))
        return e.code, None, maskele(ozet)[:400]
    except OSError as e:
        return 0, None, type(e).__name__


def kok_bul(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    betik = globals().get("__file__")
    if betik and not str(betik).startswith("<"):
        aday = Path(betik).resolve().parent.parent
        if (aday / "kanal" / "talep_formu.py").is_file():
            return aday
    return Path(GUNCEL)


def talep_formu_modulu(kok: Path):
    """Canlı kodun form modülü (kanal/talep_formu.py; yalnız standart kitaplık): form tanımı ve sunulan veri aynı yerden."""
    yol = kok / "kanal" / "talep_formu.py"
    spec = importlib.util.spec_from_file_location("portman_talep_formu", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def onizleme_verisi(tf, tur: str, tanim: dict) -> dict:
    """Etkileşimli önizlemenin ekran verisi: talep → kartı ve taslağı olmayan yeni bayiye sunulan veri; revizyon → formun örnek değeri."""
    if tur == "talep":
        return tf.ekran_verisi(None, None)
    ekran = next(s for s in tanim["screens"] if s["id"] == tf.EKRAN[tur])
    return {k: v.get("__example__", "") for k, v in (ekran.get("data") or {}).items()}


def etkilesimli(onizleme: str, ekran: str, veri: dict) -> str:
    yuk = json.dumps({"screen": ekran, "data": veri}, ensure_ascii=False, separators=(",", ":"))
    ek = urllib.parse.urlencode({"interactive": "true", "flow_action": "navigate", "flow_action_payload": yuk},
                                quote_via=urllib.parse.quote)
    return onizleme + ("&" if "?" in onizleme else "?") + ek


def hatalar(liste) -> list[str]:
    out = []
    for h in liste or []:
        if isinstance(h, dict):
            yer = f"satır {h.get('line_start')}" if h.get("line_start") is not None else ""
            yol = h.get("pointers") or h.get("path") or ""
            out.append(maskele(" · ".join(str(x) for x in (h.get("error") or h.get("error_type"), h.get("message"), yer, yol) if x))[:300])
        else:
            out.append(maskele(str(h))[:300])
    return out


def waba_bul(arg: str | None) -> tuple[str | None, str]:
    if arg:
        return (arg, "komut satırından") if KIMLIK.match(arg) else (None, "--waba yalnız rakam olmalı")
    env = degisken(os.path.join(ETC, "whatsapp.env"), "WA_WABA_ID")
    if env and KIMLIK.match(env):
        return env, "whatsapp.env WA_WABA_ID"
    kod, g, h = istek("GET", "debug_token", sorgu={"input_token": BELIRTEC})
    if kod != 200 or not g:
        return None, f"belirtecin kapsamı okunamadı (GET /debug_token: HTTP {kod} {h})".strip()
    d = g.get("data") or {}
    kapsam = [str(s) for s in d.get("scopes") or []]
    bitis = d.get("expires_at")
    print(f"   belirteç: geçerli {'evet' if d.get('is_valid') else 'HAYIR'} · tür {d.get('type', '?')} · "
          f"süre {'süresiz' if bitis in (0, None) else time.strftime('%Y-%m-%d', time.gmtime(int(bitis)))} · "
          f"izinler {', '.join(k for k in kapsam if k.startswith('whatsapp')) or '-'}")
    if "whatsapp_business_management" not in kapsam:
        return None, "belirteçte whatsapp_business_management izni yok (Flows API ister); sistem kullanıcısının belirtecine eklenmeli"
    def hedefler(kapsam_adi: str) -> list[str]:
        return [str(t) for s in d.get("granular_scopes") or [] if isinstance(s, dict) and s.get("scope") == kapsam_adi
                for t in s.get("target_ids") or [] if KIMLIK.match(str(t))]

    kimlikler, kaynak = sorted(set(hedefler("whatsapp_business_management"))), "belirtecin kapsamından"
    if not kimlikler:                          # belirteç bütün varlıklara açıksa kapsamda hesap yazmaz: işletmenin hesapları
        for isletme in sorted(set(hedefler("business_management")))[:5]:
            for kenar in ("owned_whatsapp_business_accounts", "client_whatsapp_business_accounts"):
                kod, g, _ = istek("GET", f"{isletme}/{kenar}", sorgu={"fields": "id", "limit": "50"})
                kimlikler += [str(w.get("id")) for w in (g or {}).get("data") or [] if isinstance(w, dict) and KIMLIK.match(str(w.get("id")))]
        kimlikler, kaynak = sorted(set(kimlikler)), "işletmenin WhatsApp hesaplarından"
    if len(kimlikler) == 1:
        return kimlikler[0], kaynak
    if kimlikler:                              # birden çok hesap: kanalın numarasının (WA_PHONE_NUMBER_ID) bağlı olduğu hesap
        pnid = degisken(os.path.join(ETC, "whatsapp.env"), "WA_PHONE_NUMBER_ID") or ""
        eslesen = []
        for w in kimlikler[:10]:
            kod, g, _ = istek("GET", f"{w}/phone_numbers", sorgu={"fields": "id"})
            if pnid and any(str(n.get("id")) == pnid for n in (g or {}).get("data") or [] if isinstance(n, dict)):
                eslesen.append(w)
        if len(eslesen) == 1:
            return eslesen[0], "kanalın numarasının bağlı olduğu hesap"
        return None, "belirteç birden çok WhatsApp hesabını görüyor (" + ", ".join(kimlikler) + "); --waba ile birini seçin"
    return None, "belirtecin kapsamında WhatsApp hesabı yok; WABA kimliğini --waba ile verin"


def formlari_listele(waba: str) -> tuple[list[dict] | None, str]:
    out, sonraki = [], None
    for _ in range(20):
        sorgu = {"limit": "100", **({"after": sonraki} if sonraki else {})}
        kod, g, h = istek("GET", f"{waba}/flows", sorgu=sorgu)
        if kod != 200 or g is None:
            return None, f"GET /<waba>/flows: HTTP {kod} {h}".strip()
        out += [f for f in g.get("data") or [] if isinstance(f, dict)]
        sonraki = (((g.get("paging") or {}).get("cursors") or {}).get("after")) if (g.get("paging") or {}).get("next") else None
        if not sonraki:
            break
    return out, ""


def formu_kur(waba: str, tur: str, tanim: dict, var: list[dict], bak: bool) -> tuple[str | None, str, list[str]]:
    """Dönen (kimlik, ne yapıldı, doğrulama hataları)."""
    ad = AD[tur]
    ayni = [f for f in var if f.get("name") == ad]
    taslaklar = [f for f in ayni if f.get("status") == "DRAFT"]
    metin = json.dumps(tanim, ensure_ascii=False, indent=2)
    if taslaklar:
        fid = str(taslaklar[0]["id"])
        not_ = f" (aynı adla {len(taslaklar)} taslak var; ilki kullanıldı)" if len(taslaklar) > 1 else ""
        if bak:
            return fid, "taslak var; --bak: dokunulmadı" + not_, []
        kod, g, h = istek("POST", f"{fid}/assets", dosya=("file", "flow.json", metin.encode("utf-8"),
                                                           {"name": "flow.json", "asset_type": "FLOW_JSON"}))
        if kod != 200 or g is None:
            return fid, f"DURDU: taslağın JSON'u güncellenemedi (POST /<flow>/assets: HTTP {kod} {h})".strip(), []
        return fid, "taslak vardı; JSON'u sürümdeki formla güncellendi" + not_, hatalar(g.get("validation_errors"))
    if ayni:
        f = ayni[0]
        return str(f["id"]), f"durum {f.get('status')}: yayımlanmış form değiştirilemez; dokunulmadı", []
    if bak:
        return None, "yok; --bak: kurulmadı", []
    kod, g, h = istek("POST", f"{waba}/flows", govde={"name": ad, "categories": KATEGORI, "flow_json": metin, "publish": False})
    if kod != 200 or g is None or not KIMLIK.match(str(g.get("id") or "")):
        return None, f"DURDU: taslak kurulamadı (POST /<waba>/flows: HTTP {kod} {h})".strip(), []
    return str(g["id"]), "yeni taslak kuruldu", hatalar(g.get("validation_errors"))


def main(argv: list[str]) -> int:
    global BELIRTEC
    p = argparse.ArgumentParser(prog="flow_taslak.py", description="Talep ve revizyon formunu Meta'da taslak kurar (yayımlamaz).")
    p.add_argument("--waba")
    p.add_argument("--kok")
    p.add_argument("--bak", action="store_true")
    a = p.parse_args(argv)
    print(f"== PORTMAN · WhatsApp formları Meta'da taslak ({time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC)"
          f"{' · yalnız bakış (--bak)' if a.bak else ''}")
    BELIRTEC = degisken(os.path.join(ETC, "whatsapp.env"), "WA_ACCESS_TOKEN") or ""
    if not BELIRTEC:
        print(f"DUR: {ETC}/whatsapp.env içinde WA_ACCESS_TOKEN yok (vps/sir_koy.py wa_token)")
        return 1
    print(f"   belirteç parmak izi {iz(BELIRTEC)} (değer yazılmaz)")
    kok = kok_bul(a.kok)
    try:
        tf = talep_formu_modulu(kok)
        tanimlar = {t: tf.tanim(t) for t in TURLER}
    except (OSError, ValueError, AttributeError) as e:
        print(f"DUR: formlar okunamadı ({kok}/kanal: {type(e).__name__}); sürüm kurulu mu?")
        return 1
    print(f"   formlar: {kok}/kanal/formlar · " + " · ".join(f"{t} Flow JSON {tanimlar[t].get('version')}" for t in TURLER))
    waba, kaynak = waba_bul(a.waba)
    if not waba:
        print(f"DUR: WABA kimliği yok: {kaynak}")
        return 1
    print(f"   WhatsApp hesabı (WABA) {waba} ({kaynak})")
    var, h = formlari_listele(waba)
    if var is None:
        print(f"DUR: formlar listelenemedi: {h}")
        return 1
    print(f"   hesapta {len(var)} form var")
    sonuc, kimlikler = 0, {}
    for tur in TURLER:
        fid, ne, hata = formu_kur(waba, tur, tanimlar[tur], var, a.bak)
        print(f"\n-- {tur} formu ({AD[tur]}): {ne}")
        if ne.startswith("DURDU"):
            sonuc = 1
        if not fid:
            continue
        kimlikler[tur] = fid
        kod, g, h = istek("GET", fid, sorgu={"fields": "id,name,status,categories,validation_errors,json_version,preview.invalidate(false)"})
        if kod != 200 or g is None:
            print(f"   kimlik {fid} · bilgi alınamadı: HTTP {kod} {h}".strip())
            sonuc = max(sonuc, 1)
            continue
        hata = hatalar(g.get("validation_errors")) if "validation_errors" in g else hata
        print(f"   kimlik {fid} · durum {g.get('status', '?')} · Flow JSON {g.get('json_version', '?')} · Meta doğrulama hatası {len(hata)}")
        for x in hata:
            print(f"   ! {x}")
        if hata and sonuc == 0:
            sonuc = 2
        on = ((g.get("preview") or {}).get("preview_url") or "")
        if on.startswith("https://"):
            bitis = (g.get("preview") or {}).get("expires_at") or "?"
            print(f"   önizleme (telefonda açın; giriş istemez; son gün {str(bitis)[:10]}):")
            print(f"   {etkilesimli(on, tf.EKRAN[tur], onizleme_verisi(tf, tur, tanimlar[tur]))}")
            print(f"   düz önizleme: {on}")
        else:
            print("   önizleme bağlantısı gelmedi")
    if kimlikler:
        print("\n== kimlikler (sır değil): " + " · ".join(f"{t}_flow_id {k}" for t, k in kimlikler.items()))
    print("== mesaj gönderilmedi · form yayımlanmadı · ayar ve sunucudaki dosyalar değişmedi")
    print(f"== sonuç: {'tamam' if sonuc == 0 else 'Meta doğrulama hatası var' if sonuc == 2 else 'durdu'}")
    return sonuc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
