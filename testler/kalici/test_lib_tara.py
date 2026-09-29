"""Kapı B · denetim/lib_tara.py: değer yazdırmaz, sırları bulur, temiz kopya yalnız değerleri değiştirir, özgüne dokunmaz.
Sahte değerler çalışma anında birleştirilir (depo sır taraması bu dosyada gerçek biçimli değer görmesin)."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
BETIK = KOK / "denetim" / "lib_tara.py"
PHP_SURUMLERI = [p for p in ("/opt/php82/bin/php", shutil.which("php")) if p and Path(p).exists()]

G = {   # sahte "gizli" değerler
    "openai": "sk" + "-proj-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8",
    "meta": "EA" + "AB" + "x9Y8z7W6v5U4t3S2r1Q0pOnM",
    "hex": "deadbeef" * 4,
    "telefon": "90" + "5000000071",
    "telefon_bicimli": "0" + "500 000 00 72",
    "eposta": "lokman" + "@" + "portatifev.com",
    "pin": "48" + "1516",
    "dogrulama": "portman_dogrula_" + "2026",
    "rastgele": "Zq8" + "Lm2Nx7Pw4Rt6Vy1Ks9Hd3Jf5Gb0Ca2Qe",
    "kimlik": "10" + "6000000000009",
    "yorumda": "90" + "5000000073",
    "bearer": "Tk" + "9a8b7c6d5e4f3g2h1i0j",
}

SAHTE_LIB = f"""<?php
// PORTMAN lib (sahte, sınama) — iletişim: {G['eposta']}, telefon {G['yorumda']}
define('PM_OPENAI_KEY', '{G['openai']}');
define('PM_WA_TOKEN', "{G['meta']}");
const APP_SECRET = '{G['hex']}';
const PM_KANAL_SURUM = 'kanal-v1.0';
$patron = '{G['telefon']}';
$ayar = ['verify_token' => '{G['dogrulama']}', 'token_alani' => 'access_token', 'pin' => '{G['pin']}', 'tel' => '{G['telefon_bicimli']}'];
$rastgele = "{G['rastgele']}";
$wa_phone_id = {G['kimlik']};
$yol = '/home/portatifevcom/portman_app/api_token.txt';
$basliklar = ['Authorization: Bearer {G['bearer']}', 'X-Y: ' . $x];
$bos = 'it\\'s // not a comment #nor this';
$cift = "a \\"quoted\\" {{$ayar['pin']}} ?> still string";
#[Attribute]
class PMError extends RuntimeException {{ public function __construct(int $c, string $m) {{ parent::__construct($m, $c); }} }}
/* blok yorum ' tırnak içermez */
$boyut = 10485760; $zaman = 1790105524;
$metin = <<<EOT
Merhaba {{$ad}}, numara {G['telefon']} kayıtlı.
EOT;
$nd = <<<'NOW'
ham $metin
NOW;
function pm_remote(string $url, string $token, string $method, $body = null) {{
    if (defined('PM_OFFLINE_TEST') && isset($GLOBALS['pm_test_remote'])) {{ return ($GLOBALS['pm_test_remote'])($url, $token, $method, $body); }}
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Authorization: Bearer ' . $token]);
    return curl_exec($ch);
}}
function pm_indir(string $u) {{ return file_get_contents($u); }}
function pm_oku() {{ return json_decode(file_get_contents(PM_DATA . '/config.json'), true); }}
function pm_graph() {{ return pm_remote('https://graph.facebook.com/v20.0/me', 't', 'GET'); }}
echo mb_substr('abc', 0, 1);
"""


def _kos(*arg, cwd=None):
    return subprocess.run([sys.executable, str(BETIK), *map(str, arg)], capture_output=True, text=True, cwd=cwd, timeout=60)


def test_sirlari_bulur_degerleri_yazmaz_temiz_kopya_dogrulanir(tmp_path):
    lib = tmp_path / "lib.php"; lib.write_text(SAHTE_LIB)
    once = hashlib.sha256(lib.read_bytes()).hexdigest()
    temiz = tmp_path / "lib.clean.php"
    r = _kos(lib, "--temiz-kopya", temiz)
    cikti = r.stdout + r.stderr
    assert r.returncode == 0, cikti
    for ad, deger in G.items():                                          # hiçbir değer ya da 8 karakterlik parçası çıktıda yok
        parca = min(8, len(deger))
        assert not any(deger[i:i + parca] in cikti for i in range(len(deger) - parca + 1)), ad
    for tur in ("openai_anahtari", "meta_erisim_anahtari", "uzun_onaltilik", "telefon", "e_posta", "sir_adli_deger · verify_token",
                "sir_adli_deger · pin", "rastgele_dizge", "kodda_uzun_sayi", "bearer"):
        assert tur in cikti, tur
    assert "token_alani" not in cikti and "PM_KANAL_SURUM" not in cikti      # alan adı ve sürüm dizgesi sır sayılmaz
    assert "PM_OFFLINE_TEST: 1 yer · satır" in cikti and "pm_test_remote: 1 yer" in cikti and "(pm_remote)" in cikti
    assert "curl_init: satır" in cikti and "file_get_contents (değişkenle; ağ olabilir)" in cikti and "(pm_indir)" in cikti
    assert "(pm_oku)" not in cikti                                                # PM_DATA . '/…' yerel yol sayılır
    assert "graph.facebook.com" in cikti and "mbstring 1" in cikti
    for kontrol in ("kopyanın yeniden taranması: bulgu 0", "kod iskeleti özgünle birebir aynı", "değişen", "test kancaları kopyada da aynı"):
        assert "✓ " + kontrol in cikti, kontrol
    assert hashlib.sha256(lib.read_bytes()).hexdigest() == once                  # özgüne dokunulmadı
    yeni = temiz.read_text()
    for ad, deger in G.items():
        assert deger not in yeni, ad
    assert "gizli" in yeni and "example.invalid" in yeni and "'access_token'" in yeni and "10485760" in yeni and "1790105524" in yeni
    assert yeni.count("\n") == SAHTE_LIB.count("\n")
    ikinci = _kos(temiz)                                                         # kopyanın ayrıca taranması
    assert ikinci.returncode == 0 and "bulgusu yok" in ikinci.stdout, ikinci.stdout
    for php in PHP_SURUMLERI:                                                    # kopya geçerli PHP
        assert subprocess.run([php, "-l", str(temiz)], capture_output=True).returncode == 0, php


def test_temiz_dosyada_kopya_yazilmaz(tmp_path):
    lib = tmp_path / "lib.php"; lib.write_text("<?php\nfunction pm_x() { return 'kanal-v1.0'; }\n")
    r = _kos(lib, "--temiz-kopya", tmp_path / "lib.clean.php")
    assert r.returncode == 0 and "bulgusu yok" in r.stdout and not (tmp_path / "lib.clean.php").exists()
    assert "PM_OFFLINE_TEST: 0 yer · YOK" in r.stdout


def test_ozgunun_uzerine_yazmaz(tmp_path):
    lib = tmp_path / "lib.php"; lib.write_text(SAHTE_LIB)
    once = lib.read_bytes()
    r = _kos(lib, "--temiz-kopya", lib)
    assert r.returncode == 2 and "özgün dosyanın üzerine yazılamaz" in r.stdout and lib.read_bytes() == once


@pytest.mark.parametrize("php", PHP_SURUMLERI)
def test_temiz_kopya_ayni_davranir(tmp_path, php):
    """Kopya yalnız değerleri değiştirir: sırları kullanmayan kod aynı çıktıyı verir."""
    kod = "<?php\n$k = '" + G["hex"] + "';\nfunction topla(array $a): int { return array_sum($a); }\necho topla([1, 2, 3]), '|', strlen($k), '|', 'x' . \"y{$k[0]}\";\n"
    lib = tmp_path / "lib.php"; lib.write_text(kod)
    temiz = tmp_path / "lib.clean.php"
    assert _kos(lib, "--temiz-kopya", temiz).returncode == 0
    a = subprocess.run([php, str(lib)], capture_output=True, text=True).stdout
    b = subprocess.run([php, str(temiz)], capture_output=True, text=True).stdout
    assert a.split("|")[:2] == b.split("|")[:2] == ["6", "32"]                  # uzunluk korunur


def test_ara_ve_url_yollari_deger_yazmaz(tmp_path):
    lib = tmp_path / "ai.php"
    lib.write_text("<?php\nrequire __DIR__ . '/config.php';\nfunction cevapla($m) {\n    $k = ayarlarOku()['openai_key'];\n"
                   "    return pm_post('https://api.openai.com/v1/chat/completions?x=1', $k, $m);\n}\n"
                   "$yol = '/home/x/veri/ayarlar.json';\n$gizli = '" + G["openai"] + "';\n")
    r = _kos(lib, "--ara", "openai_key,ayarlarOku,ayarlar.json")
    assert "ara 'openai_key': 1 yer · satır 4 (cevapla, dizge)" in r.stdout
    assert "ara 'ayarlarOku': 1 yer · satır 4 (cevapla, kod)" in r.stdout
    assert "ara 'ayarlar.json': 1 yer · satır 7 ((işlev dışı), dizge içinde)" in r.stdout
    assert "api.openai.com/v1/chat/completions" in r.stdout and "x=1" not in r.stdout
    assert "openai_anahtari" in r.stdout and G["openai"][:12] not in r.stdout
