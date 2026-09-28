<?php
/* Portman Claude Messages adaptoru, 2026-09-29. Anahtar web kokunun disindaki claude_api.json'da. */
function portmanClaudeSor(array $ayar, array $mesajlar, ?array $araclar = null) {
    static $toolTurns = [];
    $cfgPath = defined('PORTMAN_CLAUDE_CONFIG') ? PORTMAN_CLAUDE_CONFIG : __DIR__ . '/claude_api.json';
    $cfg = is_file($cfgPath) ? json_decode((string)file_get_contents($cfgPath), true) : null;
    $key = is_array($cfg) ? trim((string)($cfg['api_key'] ?? '')) : '';
    if ($key === '') return ['ok'=>false,'hata'=>'Claude API anahtari bulunamadi'];
    $system = []; $messages = [];
    foreach ($mesajlar as $m) {
        $role = $m['role'] ?? '';
        if ($role === 'system' || $role === 'developer') { $system[] = (string)($m['content'] ?? ''); continue; }
        if ($role === 'tool') {
            $id = (string)($m['tool_call_id'] ?? '');
            if ($id === '') return ['ok'=>false,'hata'=>'Claude arac sonucunda kimlik eksik'];
            $messages[] = ['role'=>'user','content'=>[['type'=>'tool_result','tool_use_id'=>$id,'content'=>(string)($m['content'] ?? '')]]];
        } elseif ($role === 'assistant' && !empty($m['tool_calls'])) {
            $id = (string)($m['tool_calls'][0]['id'] ?? '');
            if (!isset($toolTurns[$id])) return ['ok'=>false,'hata'=>'Claude arac gecmisi eksik; islem durduruldu'];
            $messages[] = ['role'=>'assistant','content'=>$toolTurns[$id]];
        } elseif (in_array($role, ['user','assistant'], true)) {
            if (!is_string($m['content'] ?? null)) return ['ok'=>false,'hata'=>'Claude icin desteklenmeyen mesaj bicimi'];
            if ($m['content'] !== '') $messages[] = ['role'=>$role,'content'=>$m['content']];
        } else { return ['ok'=>false,'hata'=>'Claude icin desteklenmeyen mesaj rolu']; }
    }
    if (!$messages || end($messages)['role'] !== 'user') return ['ok'=>false,'hata'=>'Claude icin son kullanici mesaji gerekli'];
    $body = ['model'=>'claude-opus-5-5','max_tokens'=>4096,'output_config'=>['effort'=>'low'],
             'system'=>implode("\n\n",$system),'messages'=>$messages];
    if ($araclar !== null && count($araclar) > 0) {
        $body['tools'] = [];
        foreach ($araclar as $t) {
            $f = $t['function'] ?? null;
            if (($t['type'] ?? '') !== 'function' || !is_array($f) || empty($f['name']))
                return ['ok'=>false,'hata'=>'Claude icin desteklenmeyen arac'];
            $body['tools'][] = ['name'=>$f['name'],'description'=>$f['description'] ?? '',
                               'input_schema'=>$f['parameters'] ?? ['type'=>'object','properties'=>(object)[]]];
        }
        $body['tool_choice'] = ['type'=>'auto','disable_parallel_tool_use'=>true];
    }
    $encoded = json_encode($body, JSON_UNESCAPED_UNICODE);
    if ($encoded === false) return ['ok'=>false,'hata'=>'Claude istegi kodlanamadi'];
    [$raw,$err] = httpIstek('https://api.anthropic.com/v1/messages',
        ['x-api-key: '.$key,'anthropic-version: 2023-06-01','Content-Type: application/json'], $encoded, 60);
    if ($err) return ['ok'=>false,'hata'=>'Claude baglanti hatasi'];
    $j = json_decode((string)$raw,true);
    if (!is_array($j)) return ['ok'=>false,'hata'=>'Claude gecersiz yanit dondu'];
    if (isset($j['error'])) return ['ok'=>false,'hata'=>'Claude API: '.preg_replace('/[^a-z_]/','',(string)($j['error']['type'] ?? 'api_error'))];
    $stop = $j['stop_reason'] ?? '';
    if (!in_array($stop,['end_turn','tool_use'],true)) return ['ok'=>false,'hata'=>'Claude yaniti tamamlanmadi'];
    $texts=[]; $calls=[];
    foreach (($j['content'] ?? []) as $block) {
        if (($block['type'] ?? '') === 'text') $texts[]=(string)($block['text'] ?? '');
        if (($block['type'] ?? '') === 'tool_use') {
            $allowed=array_column($body['tools'] ?? [],'name');
            if (!in_array($block['name'] ?? '',$allowed,true) || empty($block['id']) || !isset($block['input']))
                return ['ok'=>false,'hata'=>'Claude beklenmeyen arac dondurdu'];
            $calls[]=['id'=>$block['id'],'type'=>'function','function'=>['name'=>$block['name'],
                       'arguments'=>json_encode($block['input'],JSON_UNESCAPED_UNICODE)]];
        }
    }
    $usage=$j['usage'] ?? [];
    $usage['prompt_tokens']=(int)($usage['input_tokens'] ?? 0)+(int)($usage['cache_creation_input_tokens'] ?? 0)+(int)($usage['cache_read_input_tokens'] ?? 0);
    $usage['completion_tokens']=(int)($usage['output_tokens'] ?? 0);
    $usage['total_tokens']=$usage['prompt_tokens']+$usage['completion_tokens'];
    $meta=['response_id'=>$j['id'] ?? null,'model'=>$j['model'] ?? 'claude-opus-5-5','kullanim'=>$usage];
    if ($stop === 'tool_use') {
        if (count($calls)!==1) return ['ok'=>false,'hata'=>'Claude arac yaniti tamamlanmadi'];
        $toolTurns[$calls[0]['id']]=$j['content']; // Dusunme imzalarini degistirmeden geri gonder.
        return ['ok'=>true,'tool_calls'=>$calls]+$meta;
    }
    if ($calls) return ['ok'=>false,'hata'=>'Claude arac bitis bilgisi gecersiz'];
    $text=trim(implode("\n",$texts));
    if ($text==='') return ['ok'=>false,'hata'=>'Claude bos yanit dondu'];
    return ['ok'=>true,'metin'=>$text]+$meta;
}
