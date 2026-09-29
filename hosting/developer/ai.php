<?php
/* Yapay zeka (OpenAI / ChatGPT) ile otomatik yanit */

/* OpenAI chat completions cagrisi. Donus: ['ok'=>bool, 'metin'=>..., 'hata'=>...] */
function openaiSor(array $ayar, array $mesajlar, ?array $araclar = null) {
    require_once dirname(__DIR__, 4) . '/portman_app/claude_api.php';
    return portmanClaudeSor($ayar, $mesajlar, $araclar);
}

/* Bayi bilgisi + fiyat listesini metne cevirir (sistem promptuna eklenir) */
function baglamMetni(array $ayar, array $bayi) {
    $birim = $ayar['para_birimi'] ?: 'TL';
    $iskonto = (float)($bayi['iskonto'] ?? 0);

    $s  = "\n\n### BAYİ BİLGİSİ\n";
    $s .= "- Ad: " . ($bayi['ad'] ?: 'Belirtilmemiş') . "\n";
    if (!empty($bayi['firma'])) $s .= "- Firma: {$bayi['firma']}\n";
    if (!empty($bayi['bolge'])) $s .= "- Bölge: {$bayi['bolge']}\n";
    $s .= "- Bayi iskontosu: " . ($iskonto > 0 ? "%$iskonto" : 'yok') . "\n";
    if (!empty($bayi['notlar'])) $s .= "- Notlar: {$bayi['notlar']}\n";

    $s .= "\n### FİYAT LİSTESİ\n";
    $adet = 0;
    foreach (fiyatlarOku() as $f) {
        if (empty($f['aktif'])) continue;
        $adet++;
        $satir = "- {$f['model']}";
        if ($f['tip'] !== '') $satir .= " | {$f['tip']}";
        if ($f['m2']  !== '') $satir .= " | {$f['m2']} m²";
        $satir .= " | Liste fiyatı: " . fiyatBicim($f['fiyat'], $birim);
        if ($iskonto > 0) $satir .= " | Bayi fiyatı (%$iskonto iskontolu): " . fiyatBicim($f['fiyat'] * (1 - $iskonto / 100), $birim);
        if ($f['detay'] !== '') $satir .= "\n  Detay: " . str_replace(["\r", "\n"], ['', ' '], $f['detay']);
        $s .= $satir . "\n";
    }
    if ($adet === 0) $s .= "(Fiyat listesi henüz girilmemiş. Fiyat sorulursa yöneticiden teyit alınacağını söyle.)\n";

    $s .= "\nBugünün tarihi: " . date('d.m.Y') . "\n";
    return $s;
}

/* Bir sohbet icin OpenAI mesaj dizisini kurar */
function aiMesajlariKur(array $ayar, array $bayi, $wa_id) {
    $sistem = str_replace('{FIRMA}', $ayar['firma_adi'] ?: 'firmamız', (string)$ayar['sistem_prompt']);
    $sistem .= baglamMetni($ayar, $bayi);

    $mesajlar = [['role' => 'system', 'content' => $sistem]];
    foreach (sonMesajlar($wa_id, max(2, (int)$ayar['gecmis_adet'])) as $m) {
        $icerik = (string)$m['icerik'];
        if ($m['tip'] !== 'text') {
            if (in_array($m['tip'], ['image', 'video', 'audio', 'document', 'sticker'], true)) $icerik = '[' . $m['tip'] . ' gönderildi]';
        }
        if ($icerik === '') continue;
        $mesajlar[] = ['role' => $m['yon'] === 'gelen' ? 'user' : 'assistant', 'content' => $icerik];
    }
    return $mesajlar;
}

/* Ayni numaraya ayni bilgi mesajini kisa surede tekrar atma */
function yakinZamandaGonderildiMi($wa_id, $metin, $saniye) {
    foreach (array_reverse(sonMesajlar($wa_id, 20)) as $m) {
        if ($m['yon'] === 'giden' && $m['icerik'] === $metin) return (time() - $m['tarih']) < $saniye;
    }
    return false;
}

/* Gelen mesaj kaydedildikten sonra cagrilir. Gerekirse otomatik yanit gonderir. */
function otomatikYanit($wa_id, $isim, $tip, $icerik) {
    $ayar = ayarlarOku();
    if (empty($ayar['ai_aktif'])) return;

    $numaralar = numaralarOku();
    $bayi = $numaralar[$wa_id] ?? null;

    /* Tanimsiz numara */
    if ($bayi === null) {
        $metin = trim((string)$ayar['tanimsiz_mesaj']);
        if ($metin === '' || yakinZamandaGonderildiMi($wa_id, $metin, 6 * 3600)) return;
        yanitGonder($wa_id, $isim, $metin, false);
        return;
    }

    /* Tanimli ama otomatik yanit kapali: yonetici elle yanitlar */
    if (empty($bayi['otomatik'])) return;

    /* Yazili olmayan mesaj */
    $yazili = in_array($tip, ['text', 'button', 'interactive'], true) && trim($icerik) !== '';
    if (!$yazili) {
        $metin = trim((string)$ayar['medya_mesaj']);
        if ($metin === '' || yakinZamandaGonderildiMi($wa_id, $metin, 3600)) return;
        yanitGonder($wa_id, $isim, $metin, false);
        return;
    }

    $r = openaiSor($ayar, aiMesajlariKur($ayar, $bayi, $wa_id));
    if (!$r['ok']) {
        hataLog("AI ($wa_id): " . $r['hata']);
        $metin = trim((string)$ayar['hata_mesaj']);
        if ($metin !== '' && !yakinZamandaGonderildiMi($wa_id, $metin, 3600)) yanitGonder($wa_id, $isim, $metin, false);
        return;
    }
    yanitGonder($wa_id, $isim, $r['metin'], true);
}

function yanitGonder($wa_id, $isim, $metin, $ai) {
    $g = waGonder($wa_id, $metin);
    if (!$g['ok']) { hataLog("Otomatik yanit gonderilemedi ($wa_id): " . $g['hata']); return; }
    mesajKaydet($wa_id, $isim, 'giden', 'text', $metin, $g['msg_id'], ['ai' => $ai]);
}
