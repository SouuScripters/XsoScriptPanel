#!/usr/bin/env php
<?php
/**
 * SouuEngine — Coinadster Edition v2.3
 * Simple, no bullshit. Claim counter = balance tracker.
 */

if (PHP_VERSION_ID < 80000) { fwrite(STDERR, "PHP 8.0+ required\n"); exit(1); }
error_reporting(E_ALL & ~E_DEPRECATED);

const RST="\033[0m", BOLD="\033[1m", DIM="\033[2m";
const RED="\033[38;5;196m", GRN="\033[38;5;46m", YEL="\033[38;5;226m";
const CYN="\033[38;5;51m",  MAG="\033[38;5;201m", ORG="\033[38;5;208m";
const WHT="\033[38;5;15m",  GRY="\033[38;5;240m", VIO="\033[38;5;141m";

function vlen($s){return mb_strlen(preg_replace('/\033\[[0-9;]*m/','',$s));}
function pad_to($s,$w){return $s.str_repeat(' ',max(0,$w-vlen($s)));}
function fmt_dur($s){return sprintf('%02d:%02d:%02d',floor($s/3600),floor(($s%3600)/60),$s%60);}

const BOT_NAME    = "SouuEngine";
const BOT_TAG     = "@MoneyMaker_w";
const BOT_VERSION = "2.3";
const REWARD      = 6.5;

const host          = "https://coinadster.com";
const api_in        = "https://api.waryono.my.id/in.php";
const api_res       = "https://api.waryono.my.id/res.php";
const POLL_INTERVAL = 3;

$CONFIG_FILE = __DIR__.'/SouuEngine_coinadster.json';
$COOKIE_FILE = __DIR__.'/SouuEngine_cookies.txt';
$LIMIT_LOG   = __DIR__.'/SouuEngine_limit.log';

$UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36';
$CHA = '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127"';
$LANG = 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7';

$STATE = [
    'user'=>'Unknown','email'=>'-',
    'bits_start'=>0.0,'bits_earned'=>0.0,
    'claims'=>0,'failures'=>0,'max_failures'=>3,
    'solve_attempt'=>0,'max_solve'=>3,
    'runtime_start'=>time(),
    'logs'=>[],'status_line'=>'','faucet_status'=>'checking',
];

function _log_tags() {
    return [
        'OK'=>GRN."● OK    ".RST, 'ERR'=>RED."● ERR   ".RST, 'WARN'=>YEL."● WARN  ".RST,
        'INFO'=>GRY."● INFO  ".RST, 'CLAIM'=>MAG."◉ CLAIM ".RST, 'SOLVE'=>CYN."◉ SOLVER".RST,
        'WAIT'=>ORG."◉ WAIT  ".RST, 'AUTH'=>GRN."● AUTH  ".RST, 'LOGIN'=>CYN."◉ LOGIN ".RST,
        'LIMIT'=>RED."■ LIMIT ".RST,
    ];
}

function slog($msg, $level='INFO') {
    global $STATE;
    $tags = _log_tags();
    $tag = $tags[strtoupper($level)] ?? $tags['INFO'];
    $STATE['logs'][] = GRY."[".date('H:i:s')."] ".RST.$tag." ".WHT.$msg.RST;
    if (count($STATE['logs'])>7) array_shift($STATE['logs']);
}

function set_status($s) { global $STATE; $STATE['status_line'] = $s; }

function render() {
    global $STATE;
    $W=62; $bd=CYN;
    $line=fn($c)=>$bd."║".RST.pad_to(" ".$c,$W).$bd."║".RST;
    echo "\n".$bd."╔".str_repeat('═',$W)."╗".RST."\n";
    echo $line(BOLD.WHT.BOT_NAME.RST)."\n";
    echo $line(DIM."──── Coinadster Edition v".BOT_VERSION." ────".RST)."\n";
    echo $bd."╠".str_repeat('═',$W)."╣".RST."\n";

    $hs_c=GRN; $hs_l='ONLINE';
    if ($STATE['faucet_status']==='dead')         { $hs_c=RED; $hs_l='DEAD'; }
    elseif ($STATE['faucet_status']==='cooldown') { $hs_c=ORG; $hs_l='COOLDOWN'; }
    elseif ($STATE['faucet_status']==='limit')    { $hs_c=RED; $hs_l='LIMIT'; }
    elseif ($STATE['faucet_status']==='checking') { $hs_c=GRY; $hs_l='CHECKING'; }

    echo $line(VIO."FAUCET".RST)."\n";
    echo $line("├─ Status : ".$hs_c.$hs_l.RST)."\n";
    echo $line("└─ Site   : ".CYN."coinadster.com".RST)."\n";
    if (!empty($STATE['status_line'])) {
        echo $line(ORG."  ◉ ".$STATE['status_line'].RST)."\n";
    }
    echo $bd."╠".str_repeat('═',$W)."╣".RST."\n";

    $bits_now = $STATE['bits_start'] + $STATE['bits_earned'];
    $earned_s = $STATE['bits_earned'] > 0 ? " ".GRN."(+".number_format($STATE['bits_earned'],2,'.','').")".RST : "";

    echo $line(VIO."ACCOUNT".RST)."\n";
    echo $line("├─ User   : ".CYN.$STATE['user'].RST)."\n";
    echo $line("├─ Email  : ".$STATE['email'])."\n";
    echo $line("├─ Start  : ".GRY.number_format($STATE['bits_start'],2,'.','')." bits".RST)."\n";
    echo $line("└─ Now    : ".YEL.number_format($bits_now,2,'.','')." bits".RST.$earned_s)."\n";
    echo $bd."╠".str_repeat('═',$W)."╣".RST."\n";

    $run=time()-$STATE['runtime_start'];
    echo $line(VIO."SYSTEM".RST)."\n";
    echo $line("├─ Claims : ".GRN.$STATE['claims'].RST)."\n";
    echo $line("├─ Fails  : ".RED.$STATE['failures'].RST." / ".$STATE['max_failures'])."\n";
    echo $line("└─ Runtime: ".CYN.fmt_dur($run).RST)."\n";
    echo $bd."╠".str_repeat('═',$W)."╣".RST."\n";

    if (empty($STATE['logs'])) echo $line(DIM."─ no activity ─".RST)."\n";
    else foreach ($STATE['logs'] as $l) echo $line($l)."\n";
    echo $bd."╚".str_repeat('═',$W)."╝".RST."\n";
    echo "\n   ".GRN.BOT_NAME." • ".CYN.date('H:i:s').RST."\n";
    echo "   ".DIM."By ".BOT_TAG." • v".BOT_VERSION.RST."\n\n";
}

function clear_render(){ if(PHP_OS_FAMILY==='Windows') pclose(popen('cls','w')); else system('clear'); render(); }

function load_config(){
    global $CONFIG_FILE;
    if (!file_exists($CONFIG_FILE)) return null;
    $c = json_decode(file_get_contents($CONFIG_FILE), true);
    if (!is_array($c) || empty($c['email'])) return null;
    return $c;
}
function save_config($c){ global $CONFIG_FILE; @file_put_contents($CONFIG_FILE, json_encode($c, JSON_PRETTY_PRINT)); }
function read_line($p=""){ if($p) echo $p; return trim((string)fgets(STDIN)); }

function curl_full($url, $method='GET', $data=[], $headers=[], $follow=false){
    global $COOKIE_FILE, $UA;
    $ch = curl_init();
    $opts = [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_SSL_VERIFYPEER => 0,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_COOKIEFILE => $COOKIE_FILE,
        CURLOPT_COOKIEJAR => $COOKIE_FILE,
        CURLOPT_ENCODING => 'gzip,deflate',
        CURLOPT_USERAGENT => $UA,
    ];
    if ($follow) $opts[CURLOPT_FOLLOWLOCATION] = true;
    if (strtoupper($method) === 'POST') {
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = $data;
    }
    curl_setopt_array($ch, $opts);
    $body = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    return ['body'=>$body?:'','code'=>$code,'len'=>strlen($body?:'')];
}

function headers_html($ref=null){
    global $UA, $CHA, $LANG;
    $h = [
        'Host: coinadster.com','Connection: keep-alive',
        'sec-ch-ua: '.$CHA,'sec-ch-ua-mobile: ?1','sec-ch-ua-platform: "Android"',
        'Upgrade-Insecure-Requests: 1','User-Agent: '.$UA,
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding: gzip, deflate',
        'Sec-Fetch-Site: same-origin','Sec-Fetch-Mode: navigate','Sec-Fetch-User: ?1','Sec-Fetch-Dest: document',
        'Accept-Language: '.$LANG,
    ];
    if ($ref) $h[] = 'Referer: '.$ref;
    return $h;
}
function headers_post($ref){
    global $UA, $CHA, $LANG;
    return [
        'Host: coinadster.com','Connection: keep-alive',
        'Content-Type: application/x-www-form-urlencoded','Origin: '.host,
        'Upgrade-Insecure-Requests: 1','User-Agent: '.$UA,
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding: gzip, deflate',
        'Sec-Fetch-Site: same-origin','Sec-Fetch-Mode: navigate','Sec-Fetch-User: ?1','Sec-Fetch-Dest: document',
        'Referer: '.$ref,'Accept-Language: '.$LANG,
        'sec-ch-ua: '.$CHA,'sec-ch-ua-mobile: ?1','sec-ch-ua-platform: "Android"',
    ];
}
function headers_ajax($ref=null){
    global $UA, $CHA, $LANG;
    return [
        'Host: coinadster.com','Accept: application/json, text/javascript, */*; q=0.01',
        'Accept-Language: '.$LANG,'Accept-Encoding: gzip, deflate',
        'Content-Type: application/x-www-form-urlencoded; charset=UTF-8','Origin: '.host,
        'Sec-Fetch-Dest: empty','Sec-Fetch-Mode: cors','Sec-Fetch-Site: same-origin',
        'User-Agent: '.$UA,'X-Requested-With: XMLHttpRequest',
        'sec-ch-ua: '.$CHA,'sec-ch-ua-mobile: ?1','sec-ch-ua-platform: "Android"',
        'Referer: '.($ref ?: host.'/'),
    ];
}

function extract_hidden($html, $id=null, $name=null){
    if ($id) {
        $q = preg_quote($id,'/');
        if (preg_match('/<input[^>]*\bid=["\']'.$q.'["\'][^>]*\bvalue=["\']([^"\']+)["\']/i',$html,$m)) return $m[1];
        if (preg_match('/<input[^>]*\bvalue=["\']([^"\']+)["\'][^>]*\bid=["\']'.$q.'["\']/i',$html,$m)) return $m[1];
    }
    if ($name) {
        $q = preg_quote($name,'/');
        if (preg_match('/<input[^>]*\bname=["\']'.$q.'["\'][^>]*\bvalue=["\']([^"\']+)["\']/i',$html,$m)) return $m[1];
        if (preg_match('/<input[^>]*\bvalue=["\']([^"\']+)["\'][^>]*\bname=["\']'.$q.'["\']/i',$html,$m)) return $m[1];
    }
    return null;
}

function extract_login_csrf($html){
    foreach (['bjk6isimajk','ghadutmtbua'] as $id) {
        $t = extract_hidden($html, $id);
        if ($t && preg_match('/^[a-f0-9]{32,}$/i',$t)) return $t;
    }
    if (preg_match("/var token\s*=\s*'([a-f0-9]{32,})'/",$html,$m)) return $m[1];
    if (preg_match_all('/<input[^>]*value=["\']([a-f0-9]{60,})["\']/i',$html,$all)) return $all[1][0];
    return null;
}

function extract_honeypot($html){
    if (preg_match('/<input[^>]*name=["\'](f_[a-f0-9]+)["\'][^>]*id=["\']fg_hp["\']/i',$html,$m)) return $m[1];
    if (preg_match('/<input[^>]*id=["\']fg_hp["\'][^>]*name=["\'](f_[a-f0-9]+)["\']/i',$html,$m)) return $m[1];
    return null;
}

function fg_extract($html){
    if (!preg_match('/function\s+fgTransform\s*\(\s*x\s*\)\s*\{([^}]+)\}/s',$html,$m)) return null;
    if (!preg_match('/var\s+SEED\s*=\s*(\d+)/',$html,$ms)) return null;
    $seed = (int)$ms[1];
    $stmts = array_filter(array_map('trim', explode(';', $m[1])));
    $php = '$x = $x & 0xFFFFFFFF; ';
    foreach ($stmts as $s) {
        if (preg_match('/^x\s*=\s*x\s*>>>\s*0$/',$s)) { $php.='$x=$x&0xFFFFFFFF;'; continue; }
        if (preg_match('/^x\s*=\s*\(x\s*\+\s*(\d+)\)\s*>>>\s*0$/',$s,$mm)) { $php.='$x=($x+'.$mm[1].')&0xFFFFFFFF;'; continue; }
        if (preg_match('/^x\s*=\s*\(x\s*\^\s*(\d+)\)\s*>>>\s*0$/',$s,$mm)) { $php.='$x=($x^'.$mm[1].')&0xFFFFFFFF;'; continue; }
        if (preg_match('/^x\s*=\s*\(\(x\s*<<\s*(\d+)\)\s*\|\s*\(x\s*>>>\s*(\d+)\)\)\s*>>>\s*0$/',$s,$mm)) { $php.='$x=((($x<<'.$mm[1].')|($x>>'.$mm[2].'))&0xFFFFFFFF);'; continue; }
        if (preg_match('/^x\s*=\s*Math\.imul\(x\s*,\s*(\d+)\)\s*>>>\s*0$/',$s,$mm)) { $php.='$x=(($x*'.$mm[1].')&0xFFFFFFFF);'; continue; }
        if (preg_match('/^return\s+x\s*>>>\s*0$/',$s)) { $php.='return $x&0xFFFFFFFF;'; continue; }
    }
    $fn = @eval('return function($x){'.$php.'};');
    if (!is_callable($fn)) return null;
    try { return ['seed'=>$seed,'result'=>$fn($seed)]; } catch (Throwable $e) { return null; }
}

function pow_extract($html){
    if (!preg_match('/var\s+NONCE\s*=\s*"([^"]+)"/',$html,$mn)) return null;
    if (!preg_match('/var\s+BITS\s*=\s*(\d+)/',$html,$mb)) return null;
    $nonce = $mn[1]; $bits = (int)$mb[1];
    $fb = intdiv($bits,8); $rb = $bits%8;
    for ($c=0; $c<60000000; $c++) {
        $h = hash('sha256', $nonce.':'.$c, true);
        $ok = true;
        for ($i=0; $i<$fb; $i++) { if ($h[$i] !== "\x00") { $ok=false; break; } }
        if ($ok && $rb>0) { if ((ord($h[$fb]) >> (8-$rb)) !== 0) $ok=false; }
        if ($ok) return ['counter'=>$c];
    }
    return null;
}

function solve_captcha($apikey, $sitekey, $method='turnstile'){
    $body = json_encode(["apikey"=>$apikey,"methods"=>$method,"domain"=>host,"sitekey"=>$sitekey,"json"=>1]);
    $req = curl_full(api_in, "POST", $body, ["Content-Type: application/json","Accept-Encoding: gzip, deflate"]);
    if (strpos($req['body'],"ERROR_") !== false) return $req['body'];
    $j = json_decode($req['body'], true);
    $id = $j["request"] ?? '';
    if (!$id) return "ERROR_UNKNOWN";
    $tries = 0;
    while ($tries < 40) {
        $tries++; sleep(POLL_INTERVAL);
        $res = curl_full(api_res."?apikey=".$apikey."&action=get&id=".$id."&json=1","GET",[]);
        if (strpos($res['body'],"CAPCHA_NOT_READY") !== false) continue;
        if (strpos($res['body'],"ERROR_") !== false) return $res['body'];
        $j = json_decode($res['body'], true);
        $tok = $j["request"] ?? '';
        if ($tok) return $tok;
    }
    return "ERROR_TIMEOUT";
}

function is_logged_in($h){
    return strpos($h,'cx-head')!==false || strpos($h,'id="bitBal"')!==false || strpos($h,'?logout')!==false;
}

function parse_bits($h){
    if (preg_match('~id="sbBalanceBits">([^<]+)</span>~',$h,$m)) return (float)str_replace(',','',trim($m[1]));
    if (preg_match('~id="bitBal">([^<]+)<~',$h,$m)) return (float)str_replace(',','',trim($m[1]));
    return null;
}

function do_login($apikey,$email,$password){
    @unlink($GLOBALS['COOKIE_FILE']);
    slog("login...",'LOGIN'); clear_render();
    for ($i=1; $i<=5; $i++) {
        slog("attempt $i/5",'LOGIN'); clear_render();
        $r = curl_full(host."/","GET",[],headers_html());
        $token = $r['body'] ? extract_login_csrf($r['body']) : null;
        if (!$token) {
            $alt = curl_full(host."/faucet.html","GET",[],headers_html(host."/"));
            if ($alt['body']) $token = extract_login_csrf($alt['body']);
        }
        if (!$token) { slog("CSRF gak ketemu",'ERR'); clear_render(); sleep(3); continue; }
        $cap = solve_captcha($apikey,"0x4AAAAAAAV-tgu1vT_isJ5Q",'turnstile');
        if (strpos($cap,"ERROR_")!==false) { slog("captcha gagal: $cap",'WARN'); clear_render(); sleep(3); continue; }
        $data = http_build_query(["a"=>"login","token"=>$token,"username"=>$email,"password"=>$password,"remember"=>"on","recaptcha"=>$cap,"cap"=>"turnstile"]);
        $r = curl_full(host."/system/ajax.php","POST",$data,headers_ajax(host."/"));
        $j = json_decode(trim($r['body']),true);
        if (!is_array($j)) { slog("bukan JSON",'ERR'); clear_render(); sleep(3); continue; }
        $st = $j['status'] ?? -1;
        $msg = strip_tags($j['msg'] ?? $j['message'] ?? '');
        if ($st==1 || ($j['loggedin']??0)==1) { slog("login sukses",'OK'); clear_render(); return true; }
        if ($st==2) { slog("akun 2FA",'ERR'); clear_render(); exit; }
        slog("login gagal: ".$msg,'ERR'); clear_render();
        if (stripos($msg,'password')!==false || stripos($msg,'wrong')!==false) {
            @unlink($GLOBALS['COOKIE_FILE']); @unlink($GLOBALS['CONFIG_FILE']); exit;
        }
        sleep(4);
    }
    slog("login gagal 5x",'ERR'); clear_render(); exit;
}

function is_daily_limit($m){
    $l = strtolower($m);
    foreach (['daily limit','max claims','maximum claim','claim limit','limit reached','daily cap','you have reached','come back tomorrow','per day','limit for today','daily maximum','out of claims','no more claims','quota','exhausted'] as $p) {
        if (strpos($l,$p)!==false) return true;
    }
    return false;
}

function classify_response($resp, $http_code){
    if (preg_match('~alert-success[^>]*>([^<]+)<~i', $resp, $ok)) {
        return ['status'=>'success','msg'=>trim(strip_tags($ok[1]))];
    }
    if (preg_match('~alert-danger[^>]*>([^<]+)<~i', $resp, $err)) {
        $m = trim(strip_tags($err[1]));
        if (is_daily_limit($m)) return ['status'=>'daily_limit','msg'=>$m];
        if (stripos($m,'too fast')!==false) return ['status'=>'too_fast','msg'=>$m];
        if (stripos($m,'session expired')!==false) return 'RELOGIN';
        if (stripos($m,'captcha')!==false) return ['status'=>'captcha_bad','msg'=>$m];
        if (stripos($m,'verification')!==false) return ['status'=>'verify_bad','msg'=>$m];
        if (stripos($m,'wait')!==false) {
            preg_match('/(\d+)\s*(second|minute|hour)/i',$m,$mm);
            $w = intval($mm[1]??300);
            if (isset($mm[2])) {
                if (stripos($mm[2],'minute')!==false) $w*=60;
                if (stripos($mm[2],'hour')!==false) $w*=3600;
            }
            return ['status'=>'cooldown','wait'=>$w,'msg'=>$m];
        }
        if (stripos($m,'banned')!==false || stripos($m,'suspend')!==false) return ['status'=>'banned','msg'=>$m];
        return ['status'=>'failed','msg'=>$m];
    }
    if (strpos($resp,'countdown_timer')!==false) {
        $wait = 300;
        if (preg_match('/data-left="(\d+)"/',$resp,$cd)) $wait = intval($cd[1]);
        return ['status'=>'success','msg'=>'claimed','wait'=>$wait];
    }
    if (stripos($resp,'token mismatch')!==false || (stripos($resp,'csrf')!==false && stripos($resp,'invalid')!==false)) {
        return ['status'=>'csrf_retry','msg'=>'csrf'];
    }
    if (strpos($resp,'id="claimForm"')!==false) return ['status'=>'failed','msg'=>'form rejected'];
    return ['status'=>'unknown','msg'=>"HTTP $http_code"];
}

function do_claim($apikey){
    slog("buka faucet...",'INFO'); clear_render();
    sleep(1);
    $page = curl_full(host."/faucet.html","GET",[],headers_html(host."/"));
    $h = $page['body'];

    if (!is_logged_in($h)) { slog("session drop",'WARN'); clear_render(); return 'RELOGIN'; }

    if (preg_match('~alert-danger[^>]*>([^<]+)<~i',$h,$e)) {
        $em = trim(strip_tags($e[1]));
        if (is_daily_limit($em)) return ['status'=>'daily_limit','msg'=>$em];
    }

    if (strpos($h,'countdown_timer')!==false && strpos($h,'id="claimForm"')===false) {
        if (preg_match('/data-left="(\d+)"/',$h,$cd)) return ['status'=>'cooldown','wait'=>intval($cd[1])];
        return ['status'=>'cooldown','wait'=>300];
    }

    $csrf = extract_hidden($h,null,'csrf_token');
    $fg_t = extract_hidden($h,null,'fg_token');
    if (!$csrf || !$fg_t) { slog("csrf/fg_token gak ketemu",'ERR'); clear_render(); return 'PARSE_FAIL:token'; }

    $fg = fg_extract($h);
    if (!$fg) { slog("fgTransform gagal",'ERR'); clear_render(); return 'PARSE_FAIL:fg'; }

    $pow = pow_extract($h);
    if (!$pow) { slog("PoW gagal",'ERR'); clear_render(); return 'PARSE_FAIL:pow'; }

    $hp = extract_honeypot($h);
    $sc_ts = extract_hidden($h,null,'sc_ts');
    $sc_a  = (int)extract_hidden($h,'sc_a_val');
    $sc_b  = (int)extract_hidden($h,'sc_b_val');
    $sc_sg = extract_hidden($h,null,'sc_sig');
    if (!$hp || !$sc_ts || !$sc_a || !$sc_b || !$sc_sg) { slog("field gak lengkap",'ERR'); clear_render(); return 'PARSE_FAIL:fields'; }
    $sc_r = $sc_a + $sc_b + 1234;

    $cap_type=null; $cap_key=null;
    if (strpos($h,'class="h-captcha"')!==false) { $cap_type='hcaptcha'; $cap_key="16c8fe32-6d50-4570-8f38-28748bacc5a8"; }
    elseif (strpos($h,'class="cf-turnstile"')!==false) { $cap_type='turnstile'; $cap_key="0x4AAAAAAAV-tgu1vT_isJ5Q"; }

    $post = [
        "csrf_token"=>$csrf,"fg_token"=>$fg_t,
        "fg_res"=>(string)$fg['result'],"fg_pow"=>(string)$pow['counter'],
        $hp=>"","sc_ts"=>$sc_ts,"sc_a"=>(string)$sc_a,"sc_b"=>(string)$sc_b,
        "sc_sig"=>$sc_sg,"sc_res"=>(string)$sc_r,
        "website_hp"=>"","claim_submit"=>"",
    ];

    if ($cap_type) {
        slog("solve $cap_type...",'SOLVE'); clear_render();
        $tok = solve_captcha($apikey,$cap_key,$cap_type);
        if (strpos($tok,"ERROR_")!==false) { slog("captcha gagal",'ERR'); clear_render(); return ['status'=>'failed','msg'=>"captcha"]; }
        $post['g-recaptcha-response']=$tok;
        $post['h-captcha-response']=$tok;
        $post['cf-turnstile-response']=$tok;
    }

    slog("submit claim...",'CLAIM'); clear_render();
    $r = curl_full(host."/faucet.html","POST",http_build_query($post),headers_post(host."/faucet.html"),true);

    return classify_response($r['body'], $r['code']);
}

function live_wait($sec,$label="wait"){
    global $STATE;
    if ($sec<1) return;
    $STATE['faucet_status']='cooldown';
    $start = time();
    while ((time()-$start) < $sec) {
        $left = $sec - (time()-$start);
        set_status("$label ".fmt_dur($left));
        clear_render();
        sleep(1);
    }
    set_status("");
    $STATE['faucet_status']='ok';
}

function stop_banner($reason,$detail=''){
    global $STATE,$LIMIT_LOG;
    $STATE['faucet_status']='limit';
    set_status("");
    clear_render();
    $W=62; $bd=RED;
    echo "\n".$bd."╔".str_repeat('═',$W)."╗".RST."\n";
    echo $bd."║".RST.pad_to(" ".BOLD.RED.BOT_NAME." STOPPED".RST,$W).$bd."║".RST."\n";
    echo $bd."╠".str_repeat('═',$W)."╣".RST."\n";
    echo $bd."║".RST.pad_to(" ".WHT."Reason : ".YEL.$reason.RST,$W).$bd."║".RST."\n";
    if ($detail!=='') { $d = strlen($detail)>56?substr($detail,0,56).'...':$detail; echo $bd."║".RST.pad_to(" ".DIM."Detail : ".$d.RST,$W).$bd."║".RST."\n"; }
    echo $bd."║".RST.pad_to(" ".WHT."Claims : ".GRN.$STATE['claims'].RST,$W).$bd."║".RST."\n";
    echo $bd."║".RST.pad_to(" ".WHT."Earned : ".GRN."+".number_format($STATE['bits_earned'],2,'.','').RST,$W).$bd."║".RST."\n";
    echo $bd."║".RST.pad_to(" ".WHT."Runtime: ".CYN.fmt_dur(time()-$STATE['runtime_start']).RST,$W).$bd."║".RST."\n";
    echo $bd."╚".str_repeat('═',$W)."╝".RST."\n\n";
    @file_put_contents($LIMIT_LOG,"[".date('Y-m-d H:i:s')."] $reason | user={$STATE['user']} claims={$STATE['claims']} earned={$STATE['bits_earned']} | $detail\n",FILE_APPEND);
}

function setup(){
    echo "\n".CYN."═══ ".BOT_NAME." SETUP ═══".RST."\n\n";
    $email='';
    while (!filter_var($email,FILTER_VALIDATE_EMAIL)) {
        $email = read_line(YEL."Email: ".RST);
        if (!filter_var($email,FILTER_VALIDATE_EMAIL)) echo RED."  ✗ invalid\n".RST;
    }
    $pass = read_line(YEL."Password: ".RST);
    $key  = read_line(YEL."Waryono key: ".RST);
    return ['email'=>$email,'password'=>$pass,'apikey'=>$key];
}

clear_render();

$cfg = load_config();
if ($cfg) {
    echo GRN."  ✓ Config found\n".RST;
    echo DIM."    Email: {$cfg['email']}\n".RST;
    echo DIM."    Key  : ".substr($cfg['apikey'],0,12)."...\n\n".RST;
    if (strtolower(read_line(YEL."  Use saved? (y/n): ".RST))==='n') $cfg = setup();
} else { $cfg = setup(); }
save_config($cfg);

$apikey   = $cfg['apikey'];
$email    = $cfg['email'];
$password = $cfg['password'];
$STATE['email'] = $email;

$r = curl_full(host."/","GET",[],headers_html());
$st_html = $r['body'];
if (!is_logged_in($st_html)) {
    do_login($apikey,$email,$password);
    sleep(2);
    $r = curl_full(host."/","GET",[],headers_html());
    $st_html = $r['body'];
    if (!is_logged_in($st_html)) { slog("dashboard gak bisa diakses",'ERR'); clear_render(); exit; }
}

preg_match('~<div class="cx-uname">([^<]+)</div>~',$st_html,$un);
$STATE['user'] = trim($un[1] ?? 'unknown');
$b = parse_bits($st_html);
$STATE['bits_start'] = $b ?? 0.0;
$STATE['faucet_status'] = 'ok';

slog("session OK as {$STATE['user']} (start ".number_format($STATE['bits_start'],2,'.','')." bits)",'AUTH');
clear_render();

$fail = 0; $csrf_r = 0;

while (true) {
    if ($STATE['failures'] >= $STATE['max_failures']) { slog("max failures",'ERR'); clear_render(); break; }
    $STATE['solve_attempt'] = 0;
    $res = do_claim($apikey);

    if ($res === 'RELOGIN') {
        @unlink($GLOBALS['COOKIE_FILE']);
        do_login($apikey,$email,$password);
        sleep(3);
        continue;
    }
    if (is_string($res) && strpos($res,'PARSE_FAIL')===0) {
        $fail++; $STATE['failures']++;
        slog("parse fail ($fail/2): ".substr($res,11),'ERR'); clear_render();
        if ($fail>=2) { @unlink($GLOBALS['COOKIE_FILE']); do_login($apikey,$email,$password); $fail=0; }
        sleep(5);
        continue;
    }
    if (!is_array($res)) { $STATE['failures']++; sleep(5); continue; }

    switch ($res['status']) {
        case 'success':
            $fail=0; $csrf_r=0; $STATE['failures']=0;
            $STATE['claims']++;
            $STATE['bits_earned'] += REWARD;
            slog("CLAIMED +".number_format(REWARD,2,'.','')." | total ".number_format($STATE['bits_start']+$STATE['bits_earned'],2,'.',''),'OK');
            clear_render();
            $w = $res['wait'] ?? (rand(300,360) + rand(-15,15));
            if ($w<280) $w=280;
            live_wait($w,"next claim");
            break;

        case 'daily_limit':
            slog("DAILY LIMIT",'LIMIT'); clear_render();
            stop_banner('Daily claim limit',$res['msg']);
            exit(0);

        case 'csrf_retry':
            $csrf_r++;
            if ($csrf_r>3) { $STATE['failures']++; $fail++; $csrf_r=0; @unlink($GLOBALS['COOKIE_FILE']); do_login($apikey,$email,$password); }
            else { sleep(2); }
            continue 2;

        case 'too_fast':
            sleep(5); continue 2;

        case 'captcha_bad':
        case 'verify_bad':
            $STATE['solve_attempt']++;
            if ($STATE['solve_attempt'] >= $STATE['max_solve']) { $STATE['failures']++; $fail++; sleep(20); }
            else sleep(4);
            continue 2;

        case 'cooldown':
            live_wait((int)($res['wait']??300),"cooldown");
            break;

        case 'server_limit':
            slog("SERVER LIMIT",'LIMIT'); clear_render();
            stop_banner('Server limit',$res['msg']);
            exit(0);

        case 'banned':
            slog("BANNED",'ERR'); clear_render();
            stop_banner('Account banned',$res['msg']);
            exit(1);

        case 'failed':
            $STATE['failures']++; $fail++;
            slog("failed: ".($res['msg']??''),'ERR'); clear_render();
            if ($fail>=2) { @unlink($GLOBALS['COOKIE_FILE']); do_login($apikey,$email,$password); $fail=0; }
            sleep(10);
            break;

        default:
            $STATE['failures']++; $fail++;
            slog("unknown: ".($res['msg']??''),'WARN'); clear_render();
            if ($fail>=2) { @unlink($GLOBALS['COOKIE_FILE']); do_login($apikey,$email,$password); $fail=0; }
            sleep(10);
            break;
    }
}

clear_render();
echo "\n".CYN."  ◉ ".BOT_NAME." stopped. Claims: {$STATE['claims']} | Earned: +".number_format($STATE['bits_earned'],2,'.','')."\n\n".RST;
