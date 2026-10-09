#!/usr/bin/env python3
"""PORTMAN · panel yönetici parolası (İE-06, Kapı 5; root; yalnız standart kitaplık, sistem python3 ile koşar).

Parola STANDART GİRDİDEN okunur (en az 12 karakter); scrypt özeti /etc/portman/panel.env'e PANEL_PAROLA= satırı olarak yazılır
(PANEL_SIR korunur; yoksa üretilir). Parola hiçbir yere yazılmaz; çıktıda özetin 12 haneli parmak izi vardır. Özet biçimi
kanal/panel.py::parola_ozeti ile aynıdır (scrypt$16384$8$1$<tuz>$<özet>); panel.parola_dogru doğrular.
    pbpaste | ssh portman-vps 'python3 /opt/portman/guncel/vps/panel_parola.py'; pbcopy < /dev/null
Panel servisi yeniden başlayınca geçer: systemctl restart portman-panel. Test için: PM_ETC.
"""
import hashlib
import os
import secrets
import sys

ETC = os.environ.get("PM_ETC", "/etc/portman")
EN_AZ = 12
SCRYPT_N, SCRYPT_R, SCRYPT_P = 16384, 8, 1


def parola_ozeti(parola: str) -> str:
    tuz = secrets.token_bytes(16)
    h = hashlib.scrypt(parola.encode("utf-8"), salt=tuz, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${tuz.hex()}${h.hex()}"


def main() -> int:
    deger = sys.stdin.read().strip("\r\n")
    if len(deger) < EN_AZ:
        print(f"DUR: parola en az {EN_AZ} karakter olmalı (verilen {len(deger)}); dosyaya dokunulmadı.", file=sys.stderr)
        return 1
    yol = os.path.join(ETC, "panel.env")
    try:
        with open(yol, encoding="utf-8") as f:
            eski = [s for s in f.read().splitlines() if s.strip()]
    except FileNotFoundError:
        eski = []
    yeni = [s for s in eski if not s.startswith("PANEL_PAROLA=")]
    if not any(s.startswith("PANEL_SIR=") for s in yeni):
        yeni.append("PANEL_SIR=" + secrets.token_hex(32))
        sir_notu = "PANEL_SIR yoktu, üretildi"
    else:
        sir_notu = "PANEL_SIR korundu"
    ozet = parola_ozeti(deger)
    yeni.append("PANEL_PAROLA=" + ozet)
    os.makedirs(ETC, mode=0o700, exist_ok=True)
    gecici = yol + ".yeni"
    fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(yeni) + "\n")
    os.chmod(gecici, 0o600)
    os.replace(gecici, yol)
    print(f"== panel parolası yazıldı: {yol} (PANEL_PAROLA, scrypt; {sir_notu}) · özet parmak izi {hashlib.sha256(ozet.encode()).hexdigest()[:12]}")
    print("   geçmesi için: systemctl restart portman-panel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
