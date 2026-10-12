<?php
/**
 * FaucetBot Multi-Site v7.4 — non-blocking + 429 disable
 * CoinDrip BTC removed (AdsLab captcha, unsolvable via API).
 *
 * Modes:
 *   1 Gobrya DOGE | 2 TaraKing TRX | 3 ALL
 *   4 Update cookie | 5 Check cookies | 6 Reset config
 *
 * 429 rate limit → site di-disable permanen sampai restart (biar gak buang token)
 */

error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE);
date_default_timezone_set('Asia/Jakarta');

define("RED", "\033[1;31m"); define("GRN", "\033[1;32m");
define("YEL", "\033[1;33m"); define("BLU", "\033[1;34m");
define("MAG", "\033[1;35m"); define("CYN", "\033[1;36m");
define("WHT", "\033[1;37m"); define("RST", "\033[0m");
define("BOLD","\033[1m");

$SITES = [
    '1' => [
        'name'=>'Gobrya DOGE','host'=>'gobrya.online','base'=>'https://gobrya.online',
        'session'=>'https://gobrya.online/api/session','claim'=>'https://gobrya.online/claim',
        'sitekey'=>'0x4AAAAAAEys95zeqiQRDV2A','currency'=>'DOGE','loop_wait'=>60,
        'captcha_field'=>'cf-turnstile-response','captcha_type'=>'TURNSTILE',
    ],
    '2' => [
        'name'=>'TaraKing TRX','host'=>'taraking.top','base'=>'https://taraking.top',
        'session'=>'https://taraking.top/api/session','claim'=>'https://taraking.top/claim',
        'sitekey'=>'0x4AAAAAAE7f72EIFp1ptwY7','currency'=>'TRX','loop_wait'=>60,
        'captcha_field'=>'captcha_token','captcha_type'=>'TURNSTILE',
    ],
];

const API_IN      = "https://api.waryono.my.id/in.php";
const API_RES     = "https://api.waryono.my.id/res.php";
const API_BALANCE = "https://api.waryono.my.id/balance.php";
const DEFAULT_UA  = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36";
const TICK_INTERVAL = 30;

$GLOBALS['API_KEY'] = "";
$GLOBALS['USER_UA'] = DEFAULT_UA;
$GLOBALS['PROXY']   = null;

$GLOBALS['_logs']         = [];
$GLOBALS['_startTime']    = time();
$GLOBALS['_totalClaims']  = 0;
$GLOBALS['_totalRewards'] = [];
$GLOBALS['_fails']        = 0;
$GLOBALS['_maxFails']     = 10;
$GLOBALS['_stage']        = 'INIT';
$GLOBALS['_activeCoin']   = '-';
$GLOBALS['_balance']      = '-';
$GLOBALS['_user']         = '-';
$GLOBALS['_currentSite']  = null;
$GLOBALS['_mode']         = '1';
$GLOBALS['_nextReadyAt']  = [];
$GLOBALS['_disabledSites']= [];

// ═══ ANSI ═══
function fg($c){ return "\033[38;5;{$c}m"; }
function ansi_len($s){
    $plain = preg_replace('/\x1b\[[0-9;]*m/','',$s);
    $w = 0; $len = mb_strlen($plain, 'UTF-8');
    for ($i=0; $i<$len; $i++){
        $ch = mb_substr($plain,$i,1,'UTF-8'); $cp = mb_ord($ch, 'UTF-8');
        if (($cp>=0x1F300 && $cp<=0x1F9FF) || ($cp>=0x2600 && $cp<=0x27BF) ||
            ($cp>=0x2B00 && $cp<=0x2BFF) || ($cp>=0x25A0 && $cp<=0x25FF) ||
            ($cp>=0x2580 && $cp<=0x259F)) { $w += 2; } else { $w += 1; }
    }
    return $w;
}
function ansi_pad($s,$len){ $p = $len - ansi_len($s); return $s . ($p>0 ? str_repeat(' ',$p) : ''); }
function gradient($text,$start=51,$end=196){
    $len = mb_strlen($text,'UTF-8');
    if ($len<=1) return fg($start).$text.RST;
    $out = '';
    for ($i=0; $i<$len; $i++){
        $t = $i/max(1,$len-1);
        $c = (int)round($start + ($end-$start)*$t);
        $out .= fg($c).mb_substr($text,$i,1,'UTF-8');
    }
    return $out.RST;
}
function box_line($c){ return fg(51)."║  ".RST.ansi_pad($c,60).fg(51)."║".RST."\n"; }
function box_div(){ return fg(51)."╠".str_repeat("═",62)."╣".RST."\n"; }

function push_log($msg, $tag='i'){
    $icons = ['i'=>fg(51)."●".RST,'ok'=>fg(46)."✔".RST,'er'=>fg(196)."✖".RST,
              'wr'=>fg(208)."◈".RST,'in'=>fg(213)."⬢".RST,'g'=>fg(226)."◆".RST];
    $ts = date('H:i:s');
    $line = fg(250)."[{$ts}]".RST." ".($icons[$tag]??'●')." ".$msg;
    $GLOBALS['_logs'][] = $line;
    if (count($GLOBALS['_logs'])>6) array_shift($GLOBALS['_logs']);
}
function fmt_uptime($s){
    $s = (int)$s;
    return sprintf('%02d:%02d:%02d', floor($s/3600), floor(($s%3600)/60), $s%60);
}
function fmt_time($s){
    $s = (int)$s;
    if ($s <= 0) return 'ready';
    if ($s >= 3600) return floor($s/3600)."h".floor(($s%3600)/60)."m";
    if ($s >= 60)   return floor($s/60)."m".($s%60)."s";
    return $s."s";
}
function total_rewards_str(){
    if (empty($GLOBALS['_totalRewards'])) return '0';
    $parts = [];
    foreach ($GLOBALS['_totalRewards'] as $coin => $amt) {
        if ($amt <= 0) continue;
        $parts[] = number_format($amt, 8)." ".$coin;
    }
    return $parts ? implode(' | ', $parts) : '0';
}

function banner(){
    $elapsed = time() - $GLOBALS['_startTime'];
    $claims  = $GLOBALS['_totalClaims'];
    $fails   = $GLOBALS['_fails'];
    $maxF    = $GLOBALS['_maxFails'];
    $site    = $GLOBALS['_currentSite'];

    echo "\033[2J\033[H";
    echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
    echo box_line(gradient("FAUCETBOT MULTI-SITE", 51, 213));
    echo box_line(fg(240)."─────── SOUU ENGINE ───────".RST);
    echo box_div();

    echo box_line(fg(213).BOLD."CAPTCHA".RST);
    echo box_line(fg(51)."├─ Type     : ".RST.fg(226).($site ? $site['captcha_type'] : 'TURNSTILE').RST);
    echo box_line(fg(51)."└─ Solver   : ".RST.fg(226)."waryono".RST);
    echo box_div();

    echo box_line(fg(213).BOLD."CURRENT".RST);
    echo box_line(fg(51)."├─ Site       : ".RST.fg(226).($site ? $site['name'] : '-').RST);
    echo box_line(fg(51)."├─ User       : ".RST.fg(226).$GLOBALS['_user'].RST);
    echo box_line(fg(51)."├─ Coin       : ".RST.fg(226).$GLOBALS['_activeCoin'].RST);
    echo box_line(fg(51)."└─ Balance    : ".RST.fg(46).$GLOBALS['_balance'].RST);
    echo box_div();

    if ($GLOBALS['_mode'] === '3') {
        echo box_line(fg(213).BOLD."STATUS".RST);
        foreach ($GLOBALS['_nextReadyAt'] as $id => $ts) {
            $siteInfo = $GLOBALS['SITES'][$id] ?? null;
            if (!$siteInfo) continue;

            if (!empty($GLOBALS['_disabledSites'][$id])) {
                echo box_line(
                    fg(51)."├─ ".str_pad($siteInfo['name'], 14).RST
                    .fg(196)."DISABLED (429)".RST
                );
                continue;
            }

            $remain = $ts - time();
            $color = $remain <= 0 ? 46 : 208;
            echo box_line(
                fg(51)."├─ ".str_pad($siteInfo['name'], 14).RST
                .fg($color).fmt_time($remain).RST
            );
        }
        echo box_div();
    }

    echo box_line(fg(213).BOLD."INCOME".RST);
    echo box_line(fg(51)."├─ Total      : ".RST.fg(46).total_rewards_str().RST);
    echo box_line(fg(51)."└─ Claims     : ".RST.fg(226).$claims.RST);
    echo box_div();

    echo box_line(fg(213).BOLD."SYSTEM".RST);
    echo box_line(fg(51)."├─ Stage      : ".RST.fg(208).$GLOBALS['_stage'].RST);
    echo box_line(fg(51)."├─ Failures   : ".RST.($fails>=$maxF?fg(196):fg(226)).$fails." / ".$maxF.RST);
    echo box_line(fg(51)."└─ Runtime    : ".RST.fg(226).fmt_uptime($elapsed).RST);
    echo box_div();

    $logs = $GLOBALS['_logs'];
    for ($i=0; $i<6; $i++){
        if (isset($logs[$i])) echo box_line(fg(252).$logs[$i].RST);
        else echo fg(51)."║".str_repeat(" ",62)."║".RST."\n";
    }

    echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
    echo "\n   ".gradient("BOT RUNNING", 46, 226)." ".fg(250)."• ".date('H:i:s').RST."\n";
    echo "   ".fg(240)."By Power ".RST.fg(213)."@SouuXso".RST.fg(240)." • ".RST.fg(46)."FaucetBot Edition".RST."\n\n";
}

function clear() {
    if (PHP_OS_FAMILY === 'Windows') { @pclose(@popen('cls', 'w')); }
    else { system('clear'); }
}

// ═══ Config ═══
function config_dir($host) {
    $dir = __DIR__ . "/configs/" . $host;
    if (!is_dir($dir)) mkdir($dir, 0777, true);
    return $dir;
}
function config_get($host, $filename, $default = null) {
    $path = config_dir($host) . "/" . $filename;
    if (file_exists($path)) {
        $v = trim(file_get_contents($path));
        if ($v !== "") return $v;
    }
    return $default;
}
function config_save($host, $filename, $value) {
    file_put_contents(config_dir($host) . "/" . $filename, $value);
}

// ═══ HTTP ═══
function Run($url, $headers = [], $post = null, $proxy = null) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_MAXREDIRS, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 30);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    curl_setopt($ch, CURLOPT_ENCODING, "");
    curl_setopt($ch, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2TLS);

    if (!empty($proxy)) {
        if (!preg_match('#^https?://#i', $proxy)) $proxy = "http://" . $proxy;
        $p = parse_url($proxy);
        if (!empty($p['host']) && !empty($p['port'])) {
            curl_setopt($ch, CURLOPT_PROXY, $p['host'] . ":" . $p['port']);
            if (!empty($p['user']) && !empty($p['pass'])) {
                curl_setopt($ch, CURLOPT_PROXYUSERPWD, $p['user'] . ":" . $p['pass']);
            }
            curl_setopt($ch, CURLOPT_PROXYTYPE, CURLPROXY_HTTP);
        }
    }
    if ($post !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    }
    if (!empty($headers)) curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

    $response = curl_exec($ch);
    $err      = curl_error($ch);
    $info     = curl_getinfo($ch);

    $headerSize = $info['header_size'] ?? 0;
    $body       = $response !== false ? substr($response, $headerSize) : "";
    $rawHeaders = $response !== false ? substr($response, 0, $headerSize) : "";

    $loc = null;
    if (preg_match_all('/^location:\s*(.+)$/im', $rawHeaders, $mm)) {
        $loc = trim(end($mm[1]));
    }

    return [
        "body"   => $body,
        "info"   => $info,
        "header" => ["location" => $loc],
        "error"  => $err,
    ];
}

// ═══ Solver ═══
function get_balance() {
    $url = API_BALANCE . "?apikey=" . urlencode($GLOBALS['API_KEY']);
    $raw = Run($url, [], null, $GLOBALS['PROXY'])['body'];
    $r   = json_decode($raw, true);
    if (isset($r['balance'])) return number_format((float)$r['balance'], 2, ".", "");
    return null;
}

function poll($id) {
    for ($i = 1; $i <= 60; $i++) {
        sleep(3);
        $url = API_RES . "?apikey=" . urlencode($GLOBALS['API_KEY'])
             . "&id=" . urlencode($id) . "&action=get&json=1";
        $raw = Run($url, [], null, $GLOBALS['PROXY'])['body'];
        $r   = json_decode($raw, true);

        if (!is_array($r)) {
            $t = trim($raw);
            if (preg_match('/^OK\|(.+)$/', $t, $m)) return ['status'=>1, 'token'=>$m[1]];
            if (stripos($t, 'CAPCHA_NOT_READY') !== false) { echo WHT."  .".RST; flush(); continue; }
            return ['status'=>0, 'request'=>$t];
        }
        $status = (int)($r['status'] ?? 0);
        $req    = $r['request'] ?? '';

        if ($status === 1 && !empty($req)) return ['status'=>1, 'token'=>$req];
        if ($status === 0 && $req === 'CAPCHA_NOT_READY') { echo WHT."  .".RST; flush(); continue; }
        return ['status'=>0, 'request'=>$req];
    }
    return ['status'=>0, 'request'=>'TIMEOUT'];
}

function captcha_solve($url, $sitekey, $method = 'turnstile') {
    $body = json_encode([
        "apikey"  => $GLOBALS['API_KEY'],
        "methods" => $method,
        "domain"  => $url,
        "sitekey" => $sitekey,
        "json"    => 1,
    ]);
    $raw = Run(API_IN, ["Content-Type: application/json"], $body, $GLOBALS['PROXY'])['body'];
    $r   = json_decode($raw, true);

    if (is_array($r)) {
        $status = (int)($r['status'] ?? 0);
        $req    = $r['request'] ?? '';
        if ($status === 1 && !empty($req)) return poll($req);
        return ['status'=>0, 'request'=>$req];
    }
    if (preg_match('/^OK\|(\S+)$/', trim($raw), $m)) return poll($m[1]);
    return ['status'=>0, 'request'=>trim($raw)];
}

function sleep_tick($seconds, $label = "next tick"){
    $w = (int)$seconds;
    while ($w > 0) {
        echo "\r".WHT."  ".$label." ".GRN.fmt_time($w).RST."    ";
        flush();
        sleep(min($w, 1));
        $w -= 1;
    }
    echo "\r".str_repeat(" ", 60)."\r";
}

// ═══ Cookie helpers ═══
function check_cookie($site, $cookie) {
    $headers = [
        "Cookie: faas_session=$cookie",
        "User-Agent: " . $GLOBALS['USER_UA'],
        "Accept: */*",
        "Referer: " . $site['base'] . "/",
    ];
    $r = Run($site['session'], $headers, null, $GLOBALS['PROXY']);
    return json_decode($r['body'] ?? '', true);
}

function ensure_cookie($site) {
    $cookie = config_get($site['host'], 'cookie.txt');
    if (!$cookie) {
        echo "\n".WHT."Cookie ".YEL.$site['name'].WHT." (faas_session):\n".RST;
        echo WHT."  → ".YEL;
        $cookie = trim(fgets(STDIN));
        echo RST;
        if (!$cookie) exit(RED."❌ cookie required\n".RST);
        $cookie = preg_replace('/^faas_session=/i', '', $cookie);
        config_save($site['host'], 'cookie.txt', $cookie);
    }
    return $cookie;
}

// ═══ Claim ═══
function attempt_claim($site, $cookie, $proxy = null) {
    $headers = [
        "Cookie: faas_session=$cookie",
        "User-Agent: " . $GLOBALS['USER_UA'],
        "Accept: */*",
        "Referer: " . $site['base'] . "/",
        "Origin: " . $site['base'],
    ];

    $sess = check_cookie($site, $cookie);

    if (empty($sess['logged_in'])) return ['status' => 'session_invalid'];

    $name      = $sess['name']                            ?? '?';
    $balance   = $sess['balance']                         ?? '?';
    $currency  = $sess['balance_currency']                ?? '?';
    $available = $sess['balance_available']               ?? false;
    $amount    = $sess['claim']['amount']                 ?? '?';
    $enabled   = $sess['claim']['enabled']                ?? false;
    $nextAt    = $sess['next_claim_at']                   ?? null;

    $GLOBALS['_user']       = $name;
    $GLOBALS['_balance']    = "$balance $currency";
    $GLOBALS['_activeCoin'] = $currency;

    if (!$available) return ['status' => 'not_available'];
    if (!$enabled)   return ['status' => 'claim_disabled'];

    if ($nextAt) {
        $wait = strtotime($nextAt) - time();
        if ($wait > 0) return ['status' => 'cooldown', 'wait' => $wait];
    }

    push_log("solving captcha...", 'in');
    banner();

    $capResp = captcha_solve($site['base'] . "/", $site['sitekey'], 'turnstile');
    $cap     = $capResp['token'] ?? null;

    if (empty($cap) || strlen($cap) < 20) {
        return ['status' => 'captcha_failed', 'msg' => json_encode($capResp)];
    }
    push_log("captcha solved", 'ok');
    banner();

    $claimHeaders = $headers;
    $claimHeaders[] = "Content-Type: application/x-www-form-urlencoded";

    $postBody = http_build_query([$site['captcha_field'] => $cap]);

    $claimResp = Run($site['claim'], $claimHeaders, $postBody, $proxy);
    $httpCode  = (int)($claimResp['info']['http_code'] ?? 0);
    $respBody  = $claimResp['body'] ?? '';

    if ($httpCode === 429) {
        return [
            'status' => 'rate_limited',
            'msg'    => trim(strip_tags(substr($respBody, 0, 100))) ?: 'rate limit reached',
        ];
    }

    $cj = json_decode($respBody, true);

    if (!empty($cj['success'])) {
        return [
            'status'    => 'success',
            'amount'    => $cj['amount']   ?? $amount,
            'currency'  => $cj['currency'] ?? $currency,
            'claim_id'  => $cj['claim_id'] ?? '?',
            'payout_id' => $cj['payout_id'] ?? '?',
        ];
    }

    $msg = $cj['message'] ?? $cj['error'] ?? ($respBody ?: 'unknown error');
    return ['status' => 'error', 'msg' => $msg, 'http' => $httpCode];
}

function run_site($site, $cookie, $siteId = null) {
    $GLOBALS['_currentSite'] = $site;
    $GLOBALS['_activeCoin']  = $site['currency'];
    $GLOBALS['_stage']       = "RUN ".strtoupper($site['currency']);
    banner();

    $res = attempt_claim($site, $cookie, $GLOBALS['PROXY']);

    if ($res['status'] === 'success') {
        $GLOBALS['_totalClaims']++;
        $amt = (float)($res['amount'] ?? 0);
        $sym = $res['currency'] ?? $site['currency'];
        if (!isset($GLOBALS['_totalRewards'][$sym])) $GLOBALS['_totalRewards'][$sym] = 0.0;
        $GLOBALS['_totalRewards'][$sym] += $amt;
        push_log("+".$amt." $sym | claim_id: {$res['claim_id']}", 'ok');
        $GLOBALS['_fails'] = 0;
        if ($siteId !== null) $GLOBALS['_nextReadyAt'][$siteId] = time() + (int)$site['loop_wait'];
        banner();
        return true;
    }
    elseif ($res['status'] === 'cooldown') {
        $wait = (int)$res['wait'];
        if ($siteId !== null) $GLOBALS['_nextReadyAt'][$siteId] = time() + $wait;
        push_log("cooldown ".fmt_time($wait)." — skip", 'wr');
        banner();
        return false;
    }
    elseif ($res['status'] === 'rate_limited') {
        if ($siteId !== null) {
            $GLOBALS['_disabledSites'][$siteId] = true;
            $GLOBALS['_nextReadyAt'][$siteId]   = PHP_INT_MAX;
        }
        $siteName = $site['name'] ?? '?';
        push_log("429 — $siteName DISABLED sampai restart", 'er');
        banner();
        return false;
    }
    elseif ($res['status'] === 'session_invalid') {
        push_log("session expired — update cookie", 'er');
        banner();
        if ($siteId !== null) $GLOBALS['_nextReadyAt'][$siteId] = time() + 300;
        return false;
    }
    elseif ($res['status'] === 'not_available') {
        push_log("balance not available", 'wr');
        banner();
        return false;
    }
    elseif ($res['status'] === 'claim_disabled') {
        push_log("claim disabled", 'er');
        banner();
        return false;
    }
    elseif ($res['status'] === 'captcha_failed') {
        $GLOBALS['_fails']++;
        push_log("captcha failed: ".substr($res['msg'] ?? '', 0, 60), 'er');
        banner();
        return false;
    }
    else {
        $GLOBALS['_fails']++;
        $http = $res['http'] ?? '?';
        push_log("error (HTTP $http): ".substr($res['msg'] ?? '?', 0, 80), 'er');
        banner();
        return false;
    }
}

// ═══ Menu helpers ═══
function menu_update_cookie() {
    global $SITES;
    clear();
    echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
    echo box_line(gradient("UPDATE COOKIE", 51, 213));
    echo box_div();
    echo box_line(fg(213).BOLD."PILIH SITE".RST);
    foreach ($SITES as $id => $s) {
        $status = config_get($s['host'], 'cookie.txt') ? fg(46)."set".RST : fg(196)."kosong".RST;
        echo box_line(fg(51)."  ".fg(226).$id.".".RST.fg(46)." ".str_pad($s['name'], 16).RST." [".$status.fg(51)."]".RST);
    }
    echo box_line(fg(51)."  ".fg(226)."3.".RST.fg(208)." SEMUA site".RST);
    echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
    echo "\n   ".gradient("PILIH > ", 46, 226).fg(226);
    $pick = trim(fgets(STDIN));
    echo RST."\n";

    if ($pick === '3') {
        foreach ($SITES as $s) {
            echo "\n".WHT."Cookie ".YEL.$s['name'].WHT." (blank=skip):\n".RST;
            echo WHT."  → ".YEL;
            $c = trim(fgets(STDIN));
            echo RST;
            if ($c !== '') {
                $c = preg_replace('/^faas_session=/i', '', $c);
                config_save($s['host'], 'cookie.txt', $c);
                echo GRN."  ✓ saved\n".RST;
            }
        }
    } elseif (isset($SITES[$pick])) {
        $s = $SITES[$pick];
        echo WHT."Cookie baru untuk ".YEL.$s['name'].WHT.":\n".RST;
        echo WHT."  → ".YEL;
        $c = trim(fgets(STDIN));
        echo RST;
        if ($c !== '') {
            $c = preg_replace('/^faas_session=/i', '', $c);
            config_save($s['host'], 'cookie.txt', $c);
            echo GRN."  ✓ saved\n".RST;
        }
    }
    sleep(2);
}

function menu_check_cookies() {
    global $SITES;
    clear();
    echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
    echo box_line(gradient("CHECK COOKIES", 51, 213));
    echo box_div();

    foreach ($SITES as $id => $s) {
        $cookie = config_get($s['host'], 'cookie.txt');
        if (!$cookie) {
            echo box_line(fg(196)."✖ ".str_pad($s['name'], 16)." — cookie.txt kosong".RST);
            continue;
        }
        $sess = check_cookie($s, $cookie);
        if (!empty($sess['logged_in'])) {
            $name = $sess['name'] ?? '?';
            $bal  = ($sess['balance'] ?? '?')." ".($sess['balance_currency'] ?? '?');
            echo box_line(fg(46)."✔ ".str_pad($s['name'], 16)." — $name ($bal)".RST);
        } else {
            echo box_line(fg(196)."✖ ".str_pad($s['name'], 16)." — SESSION EXPIRED".RST);
        }
    }
    echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
    echo "\n   Tekan Enter buat lanjut...";
    fgets(STDIN);
}

function menu_reset_config() {
    clear();
    echo WHT."Yakin reset semua config (api_key + cookies)? [y/N]: ".YEL;
    $c = trim(fgets(STDIN));
    echo RST;
    if (strtolower($c) === 'y') {
        $dir = __DIR__ . "/configs";
        if (is_dir($dir)) {
            exec('rm -rf ' . escapeshellarg($dir));
        }
        echo GRN."✓ Config dihapus. Restart script.\n".RST;
        sleep(2);
    }
}

// ═══ MAIN ═══
while (true) {
    clear();
    echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
    echo box_line(gradient("FAUCETBOT MULTI-SITE v7.4", 51, 213));
    echo box_line(fg(240)."─────── SOUU ENGINE ───────".RST);
    echo box_div();
    echo box_line(fg(213).BOLD."PILIH MODE".RST);
    echo box_line(fg(51)."  ".RST.fg(226)."1.".RST.fg(46)." Gobrya DOGE".RST);
    echo box_line(fg(51)."  ".RST.fg(226)."2.".RST.fg(46)." TaraKing TRX".RST);
    echo box_line(fg(51)."  ".RST.fg(208)."3. ALL (rotate, non-blocking)".RST);
    echo box_div();
    echo box_line(fg(213).BOLD."TOOLS".RST);
    echo box_line(fg(51)."  ".RST.fg(226)."4.".RST.fg(46)." Update cookie".RST);
    echo box_line(fg(51)."  ".RST.fg(226)."5.".RST.fg(46)." Check cookie (test session)".RST);
    echo box_line(fg(51)."  ".RST.fg(226)."6.".RST.fg(196)." Reset config".RST);
    echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
    echo "\n   ".gradient("PILIH > ", 46, 226).fg(226);
    $mode = trim(fgets(STDIN));
    echo RST."\n";

    if ($mode === '4') { menu_update_cookie(); continue; }
    if ($mode === '5') { menu_check_cookies(); continue; }
    if ($mode === '6') { menu_reset_config(); continue; }

    if (!in_array($mode, ['1','2','3'])) {
        echo RED."❌ mode invalid\n".RST;
        sleep(2);
        continue;
    }

    $GLOBALS['_mode'] = $mode;
    break;
}

// ── API key ──
$apiKey = config_get('_shared', 'api_key.txt');
if (!$apiKey) {
    echo WHT."API key waryono: ".YEL;
    $apiKey = trim(fgets(STDIN));
    echo RST;
    if (!$apiKey) exit(RED."❌ api key required\n".RST);
    config_save('_shared', 'api_key.txt', $apiKey);
}
$GLOBALS['API_KEY'] = $apiKey;

$ua = config_get('_shared', 'user-agent.txt', DEFAULT_UA);
$GLOBALS['USER_UA'] = $ua;

$proxyFile = config_get('_shared', 'proxy.txt');
if ($proxyFile === null) {
    echo WHT."Proxy (blank=no): ".YEL;
    $proxy = trim(fgets(STDIN));
    echo RST;
    config_save('_shared', 'proxy.txt', $proxy);
    $proxyFile = $proxy;
}
$GLOBALS['PROXY'] = ($proxyFile === '') ? null : $proxyFile;

$bal = get_balance();
echo WHT."💰 Solver balance: ".GRN.($bal ?? "None").RST." token\n";
sleep(1);

// ── SINGLE MODE ──
if ($mode !== '3') {
    $site   = $SITES[$mode];
    $cookie = ensure_cookie($site);

    $cj = check_cookie($site, $cookie);
    if (empty($cj['logged_in'])) {
        echo RED."❌ session invalid — pilih menu 4 buat update cookie\n".RST;
        sleep(3);
        exit;
    }
    echo WHT."✓ Logged in as: ".GRN.($cj['name'] ?? '?').RST."\n";
    echo WHT."✓ Currency: ".GRN.($cj['balance_currency'] ?? '?').RST."\n";

    push_log("mode single: ".$site['name'], 'g');
    banner();

    $loopWait = (int)$site['loop_wait'];
    while (true) {
        run_site($site, $cookie, $mode);
        if (!empty($GLOBALS['_disabledSites'][$mode])) {
            push_log("site disabled — keluar", 'er');
            banner();
            sleep(3);
            exit;
        }
        if ($GLOBALS['_fails'] >= $GLOBALS['_maxFails']) {
            push_log("max fails — pause 5 min", 'er'); banner();
            sleep_tick(300, "pause");
            $GLOBALS['_fails'] = 0;
        } else {
            $wait = ($GLOBALS['_nextReadyAt'][$mode] ?? time()) - time();
            if ($wait > 0) sleep_tick($wait, "next in");
        }
    }
}

// ── ALL MODE ──
push_log("MODE: ALL — non-blocking", 'g');
banner();

$cookies = [];
foreach ($SITES as $id => $site) {
    $cookies[$id] = ensure_cookie($site);
    $GLOBALS['_nextReadyAt'][$id] = time();
}

foreach ($SITES as $id => $site) {
    $cj = check_cookie($site, $cookies[$id]);
    if (empty($cj['logged_in'])) {
        push_log("❌ ".$site['name']." — session invalid (menu 4 buat update)", 'er');
    } else {
        push_log("✓ ".$site['name']." — ".($cj['name'] ?? '?')." (".($cj['balance_currency'] ?? '?').")", 'ok');
    }
}
banner();
sleep(2);

while (true) {
    $activeSites = 0;
    foreach ($SITES as $id => $site) {
        if (empty($GLOBALS['_disabledSites'][$id])) $activeSites++;
    }
    if ($activeSites === 0) {
        push_log("SEMUA SITE DISABLED (429) — exit", 'er');
        banner();
        echo fg(196)."\n  ✖ Semua site kena rate limit. Restart script buat reset.\n".RST;
        sleep(5);
        exit;
    }

    $now = time();
    $readyIds = [];
    foreach ($SITES as $id => $site) {
        if (!empty($GLOBALS['_disabledSites'][$id])) continue;
        $nextReady = $GLOBALS['_nextReadyAt'][$id] ?? 0;
        if ($now >= $nextReady) $readyIds[] = $id;
    }

    if (!empty($readyIds)) {
        foreach ($readyIds as $id) {
            $site = $SITES[$id];
            push_log("→ ".$site['name'], 'in');
            banner();
            run_site($site, $cookies[$id], $id);
            if ($GLOBALS['_fails'] >= $GLOBALS['_maxFails']) {
                push_log("max fails — pause 5 min", 'er');
                banner();
                sleep_tick(300, "pause");
                $GLOBALS['_fails'] = 0;
            }
            sleep(2);
        }
    } else {
        banner();
        push_log("semua site aktif cooldown — tunggu tick", 'wr');
        sleep_tick(TICK_INTERVAL, "tick in");
        continue;
    }

    $minWait = null;
    foreach ($SITES as $id => $site) {
        if (!empty($GLOBALS['_disabledSites'][$id])) continue;
        $nextReady = $GLOBALS['_nextReadyAt'][$id] ?? 0;
        $remain = $nextReady - time();
        if ($remain > 0) {
            if ($minWait === null || $remain < $minWait) $minWait = $remain;
        }
    }
    if ($minWait === null) $minWait = 30;
    if ($minWait < 5) $minWait = 5;
    if ($minWait > TICK_INTERVAL) $minWait = TICK_INTERVAL;

    sleep_tick($minWait, "next site in");
}
