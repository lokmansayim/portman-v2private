<?php
require dirname(__DIR__).'/portman_app/claude_api.php';
define('PORTMAN_CLAUDE_CONFIG',__DIR__.'/mock-key.json');
file_put_contents(PORTMAN_CLAUDE_CONFIG,json_encode(['api_key'=>'mock']));
$reply=[];$last=[];$calls=0;
function httpIstek($url,$headers,$body,$timeout) {global $reply,$last,$calls;$last=json_decode($body,true);$calls++;return [json_encode($reply),null];}
function must($v,$name) {if(!$v)throw new Exception($name);}
$msg=[['role'=>'system','content'=>'Turkce yanitla'],['role'=>'user','content'=>'Merhaba']];
$reply=['stop_reason'=>'end_turn','content'=>[['type'=>'thinking','thinking'=>'','signature'=>'test'],['type'=>'text','text'=>'Merhaba']], 'usage'=>['input_tokens'=>10,'output_tokens'=>20]];
$r=portmanClaudeSor([],$msg);must($r['ok']&&$r['metin']==='Merhaba','text');must($r['kullanim']['total_tokens']===30,'usage');must(!isset($last['temperature'])&&$last['model']==='claude-opus-5-5','parameters');
$tools=[['type'=>'function','function'=>['name'=>'fiyat','parameters'=>['type'=>'object','properties'=>(object)[]]]]];
$reply=['stop_reason'=>'tool_use','content'=>[['type'=>'thinking','thinking'=>'','signature'=>'KEEP'],['type'=>'tool_use','id'=>'t1','name'=>'fiyat','input'=>['model'=>'P6001']]]];
$r=portmanClaudeSor([],$msg,$tools);must($r['ok']&&$r['tool_calls'][0]['function']['name']==='fiyat','tool');
$next=array_merge($msg,[['role'=>'assistant','tool_calls'=>$r['tool_calls']],['role'=>'tool','tool_call_id'=>'t1','content'=>'100']]);
$reply=['stop_reason'=>'end_turn','content'=>[['type'=>'text','text'=>'Fiyat 100']]];
$r=portmanClaudeSor([],$next,$tools);must($r['ok']&&$last['messages'][1]['content'][0]['signature']==='KEEP','thinking preservation');
foreach(['max_tokens','refusal','pause_turn'] as $stop) {$reply=['stop_reason'=>$stop,'content'=>[['type'=>'text','text'=>'kesik']]];must(!portmanClaudeSor([],$msg)['ok'],'incomplete');}
$reply=['stop_reason'=>'end_turn','content'=>[]];must(!portmanClaudeSor([],$msg)['ok'],'empty');
$reply=['error'=>['type'=>'authentication_error','message'=>'mock-secret']];$r=portmanClaudeSor([],$msg);must(!$r['ok']&&strpos($r['hata'],'mock-secret')===false,'error masking');
unlink(PORTMAN_CLAUDE_CONFIG);echo "Bot adapter: text, tools, thinking preservation, usage, incomplete/refusal/error tests PASSED. External API calls: 0\n";
