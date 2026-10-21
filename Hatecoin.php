<?php
/**
 * ============================================================
 *   HATECOIN.ME — Auto Faucet Bot v3.8
 *   By Dev MoneyMaker_w
 *   - FIX: cooldown = sleep only (NO rejoin, save API key)
 *   - Reject → refresh → retry → rejoin (tetep kocak)
 *   - Max 6 errors stop
 *   - No username display
 * ============================================================
 */

error_reporting(E_ALL);
ini_set('display_errors', '1');
date_default_timezone_set('Asia/Jakarta');
set_time_limit(0);

const HOST           = 'https://hatecoin.me';
const SOLVER_IN      = 'https://api.waryono.my.id/in.php';
const SOLVER_OUT     = 'https://api.waryono.my.id/res.php';
const SOLVER_BALANCE = 'https://api.waryono.my.id/balance.php';
const CFG_FILE       = 'hatecoin_cfg.json';
const COOKIE_FILE    = 'hatecoin_cookie.txt';
const LOG_FILE       = 'hatecoin_claims.log';
const REJECT_DIR     = 'reject_dumps';
const DEFAULT_UA     = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36';
const TG_CHANNEL     = 'MahaRajaZen';
const WIDE           = 62;
const LIVE_MAX_LOGS  = 12;
const MAX_TOTAL_ERR  = 6;

const POST_DELAY_MIN  = 4;
const POST_DELAY_MAX  = 8;
const CLAIM_GAP_MIN   = 3;
const CLAIM_GAP_MAX   = 7;
const WARMUP_MIN      = 2;
const WARMUP_MAX      = 4;
const REFRESH_WAIT    = 2;
const SESSION_TTL     = 300;

$C = [
    'reset'  => "\033[0m", 'green'  => "\033[1;32m", 'red'    => "\033[1;31m",
    'yellow' => "\033[1;33m", 'cyan'   => "\033[1;36m", 'magenta'=> "\033[1;35m",
    'gray'   => "\033[0;90m", 'white'  => "\033[1;37m", 'orange' => "\033[38;5;208m",
    'neonY'  => "\033[38;5;226m", 'neonG'  => "\033[38;5;46m", 'blue'   => "\033[1;34m",
];

$GLOBALS['DEBUG'] = false;
$GLOBALS['USER_AGENT'] = DEFAULT_UA;
$GLOBALS['SESSION_VERIFIED_AT'] = 0;

$LIVE = [
    'enabled'  => false, 'logs' => [], 'lines' => 0,
    'max_logs' => LIVE_MAX_LOGS,
    'stats'    => ['success' => 0, 'error' => 0, 'reward' => 0, 'faucet' => 0, 'mad' => 0],
];

function liveRender() {
    global $C, $LIVE;
    if (!$LIVE['enabled']) return;
    if ($LIVE['lines'] > 0) echo "\033[{$LIVE['lines']}A";
    echo "\033[J";
    $s = $LIVE['stats'];
    $errLimit = $s['error'] . '/' . MAX_TOTAL_ERR;
    echo "{$C['cyan']}[STATS]{$C['reset']}  {$C['green']}✓ {$s['success']}{$C['reset']}  "
       . "{$C['red']}✗ {$errLimit}{$C['reset']}  "
       . "{$C['neonY']}🔥 +{$s['reward']}{$C['reset']}  "
       . "{$C['gray']}F:{$s['faucet']} M:{$s['mad']}{$C['reset']}\n";
    echo "{$C['gray']}" . str_repeat('─', WIDE) . "{$C['reset']}\n";
    foreach ($LIVE['logs'] as $log) echo $log . "\n";
    $LIVE['lines'] = 2 + count($LIVE['logs']);
}

function liveLog($line) {
    global $C, $LIVE;
    if (!$LIVE['enabled']) { echo $line . "\n"; return; }
    $ts = "{$C['gray']}[" . date('H:i:s') . "]{$C['reset']}";
    $LIVE['logs'][] = "$ts $line";
    if (count($LIVE['logs']) > $LIVE['max_logs']) array_shift($LIVE['logs']);
    liveRender();
}

function liveStatSuccess($reward, $type) {
    global $LIVE;
    $LIVE['stats']['success']++;
    $LIVE['stats']['reward'] += $reward;
    if ($type === 'faucet') $LIVE['stats']['faucet']++;
    elseif ($type === 'madfaucet') $LIVE['stats']['mad']++;
}
function liveStatError() { global $LIVE; $LIVE['stats']['error']++; }
function isErrorLimitHit() { global $LIVE; return $LIVE['stats']['error'] >= MAX_TOTAL_ERR; }

function liveWait($seconds, $label = 'next claim in') {
    global $C, $LIVE;
    if (!$LIVE['enabled']) { timer($seconds, "  $label"); return; }
    if ($seconds < 1) $seconds = 1;
    $end = time() + $seconds;
    while (time() < $end) {
        $left = $end - time();
        $h = floor($left / 3600); $m = floor(($left % 3600) / 60); $s = $left % 60;
        echo "\r\033[2K{$C['gray']}[WAIT]{$C['reset']} {$label} {$C['neonY']}"
           . sprintf('%02d:%02d:%02d', $h, $m, $s) . "{$C['reset']}";
        usleep(200000);
    }
    echo "\r\033[2K";
}

function dbg($tag, $msg) {
    if (empty($GLOBALS['DEBUG'])) return;
    global $C;
    liveLog("{$C['gray']}[DEBUG-{$tag}]{$C['reset']} {$C['gray']}{$msg}{$C['reset']}");
}
function dbgDump($tag, $data) {
    if (empty($GLOBALS['DEBUG'])) return;
    global $C;
    $str = is_string($data) ? $data : json_encode($data, JSON_UNESCAPED_SLASHES);
    if (strlen($str) > 300) $str = substr($str, 0, 300) . '...(' . strlen($str) . 'b)';
    liveLog("{$C['gray']}[DEBUG-{$tag}]{$C['reset']} {$C['gray']}{$str}{$C['reset']}");
}

function clear() { if (PHP_OS_FAMILY === 'Windows') @system('cls'); else @system('clear'); }
function stripAnsi($s) { return preg_replace('/\033\[[0-9;]*m/', '', $s); }
function wideLine() { return str_repeat('=', WIDE); }
function centerText($text, $width = WIDE) {
    $plain = stripAnsi($text); $len = mb_strlen($plain);
    $pad = max(0, (int)floor(($width - $len) / 2));
    return str_repeat(' ', $pad) . $text;
}

function L_session($msg) { global $C; liveLog("{$C['cyan']}[SESSION]{$C['reset']} {$msg}"); }
function L_balance($msg) { global $C; liveLog("{$C['cyan']}[BALANCE]{$C['reset']} {$msg}"); }
function L_claim($msg)   { global $C; liveLog("{$C['cyan']}[CLAIM ]{$C['reset']} {$msg}"); }
function L_verify($msg)  { global $C; liveLog("{$C['cyan']}[VERIFY]{$C['reset']} {$msg}"); }
function L_wait($msg)    { global $C; liveLog("{$C['yellow']}[WAIT]{$C['reset']} {$msg}"); }
function L_human($msg)   { global $C; liveLog("{$C['magenta']}[HUMAN]{$C['reset']} {$msg}"); }
function L_skip($msg)    { global $C; liveLog("{$C['yellow']}[SKIP]{$C['reset']} {$msg}"); }
function L_rejoin($msg)  { global $C; liveLog("{$C['magenta']}[REJOIN]{$C['reset']} {$msg}"); }
function L_refresh($msg) { global $C; liveLog("{$C['blue']}[REFRESH]{$C['reset']} {$msg}"); }
function L_info($tag, $msg) { global $C; liveLog("{$C['cyan']}[{$tag}]{$C['reset']} {$msg}"); }
function L_success($tag, $msg) { global $C; liveLog("{$C['green']}[{$tag}]{$C['reset']} {$C['green']}{$msg}{$C['reset']}"); }
function L_error($tag, $msg) { global $C; liveLog("{$C['red']}[{$tag}]{$C['reset']} {$C['red']}{$msg}{$C['reset']}"); }
function L_token_cf($t) { global $C; liveLog("{$C['blue']}[Token Cf]{$C['reset']} {$C['gray']}" . substr($t, 0, 32) . "...{$C['reset']}"); }
function L_token_ab($t) { global $C; liveLog("{$C['blue']}[Token Ab]{$C['reset']} {$C['neonY']}{$t}{$C['reset']}"); }

function timer($seconds, $label = '  waiting') {
    global $C;
    if ($seconds < 1) $seconds = 1;
    $end = time() + $seconds;
    $padWidth = 70;
    while (($left = $end - time()) > 0) {
        $h = floor($left / 3600); $m = floor(($left % 3600) / 60); $s = $left % 60;
        $line = "  {$C['gray']}{$label}{$C['reset']} {$C['neonY']}" . sprintf('%02d:%02d:%02d', $h, $m, $s) . "{$C['reset']}";
        $visible = mb_strlen(stripAnsi($line));
        echo "\r" . $line . str_repeat(' ', max(0, $padWidth - $visible));
        usleep(200000);
    }
    echo "\r" . str_repeat(' ', $padWidth) . "\r";
}

function prompt($label) { echo $label; $in = fgets(STDIN); return $in === false ? '' : trim($in); }
function resetCookieJar() { if (file_exists(COOKIE_FILE)) @unlink(COOKIE_FILE); }
function saveRejectResponse($html, $type) {
    if (!is_dir(REJECT_DIR)) @mkdir(REJECT_DIR, 0755, true);
    @file_put_contents(REJECT_DIR . '/reject_' . $type . '_' . date('Ymd_His') . '.html', $html);
}

function buildHeaders($extra = []) {
    $base = [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding: gzip, deflate',
        'User-Agent: ' . $GLOBALS['USER_AGENT'],
        'Sec-Ch-Ua: "Chromium";v="127", "Not)A;Brand";v="99", "Google Chrome";v="127"',
        'Sec-Ch-Ua-Mobile: ?1',
        'Sec-Ch-Ua-Platform: "Android"',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: same-origin',
        'Sec-Fetch-User: ?1',
        'Upgrade-Insecure-Requests: 1',
        'Connection: keep-alive',
    ];
    foreach ($extra as $h) {
        $name = strtolower(trim(strtok($h, ':')));
        $base = array_values(array_filter($base, function ($e) use ($name) {
            return strtolower(trim(strtok($e, ':'))) !== $name;
        }));
        $base[] = $h;
    }
    return $base;
}

function req($url, $post = null, $extraHeaders = []) {
    $maxRetries = 3;
    for ($attempt = 1; $attempt <= $maxRetries; $attempt++) {
        $ch = curl_init();
        $headers = buildHeaders($extraHeaders);
        $httpVer = defined('CURL_HTTP_VERSION_2_0') ? CURL_HTTP_VERSION_2_0 : CURL_HTTP_VERSION_1_1;
        $opts = [
            CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS => 5, CURLOPT_SSL_VERIFYPEER => false, CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_CONNECTTIMEOUT => 20, CURLOPT_TIMEOUT => 60, CURLOPT_HTTPHEADER => $headers,
            CURLOPT_HEADER => true, CURLOPT_ENCODING => 'gzip, deflate', CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4,
            CURLOPT_TCP_KEEPALIVE => 1, CURLOPT_HTTP_VERSION => $httpVer,
            CURLOPT_COOKIEJAR => COOKIE_FILE, CURLOPT_COOKIEFILE => COOKIE_FILE,
        ];
        if ($post !== null) {
            $opts[CURLOPT_POST] = true;
            $opts[CURLOPT_POSTFIELDS] = is_string($post) ? $post : http_build_query($post);
        }
        curl_setopt_array($ch, $opts);
        $response = curl_exec($ch);
        $errtxt = curl_error($ch);
        $code = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $hsize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        if (PHP_VERSION_ID < 80000) curl_close($ch);

        if ($response === false || $errtxt) {
            $retryable = stripos($errtxt, 'reset') !== false || stripos($errtxt, 'timed out') !== false
                || stripos($errtxt, 'Empty reply') !== false || stripos($errtxt, 'Recv failure') !== false;
            if ($retryable && $attempt < $maxRetries) {
                L_error('HTTP', "retry {$attempt}/{$maxRetries}"); sleep(2); continue;
            }
            return ['body' => '', 'code' => 0, 'headers' => '', 'err' => $errtxt];
        }
        return ['body' => substr($response, $hsize), 'code' => $code, 'headers' => substr($response, 0, $hsize), 'err' => ''];
    }
    return ['body' => '', 'code' => 0, 'headers' => '', 'err' => 'max retries'];
}

function extractCsrf($html) {
    if (preg_match('/name="csrf_token_name"\s+(?:id="[^"]*"\s+)?value="([a-zA-Z0-9]+)"/i', $html, $m)) return $m[1];
    if (preg_match('/id="token"\s+value="([a-zA-Z0-9]+)"/i', $html, $m)) return $m[1];
    return null;
}
function extractSitekey($html) { if (preg_match('/data-sitekey="([^"]+)"/i', $html, $m)) return $m[1]; return null; }
function extractBalance($html) {
    if (preg_match('/Balance[\s\S]{0,400}?<h4[^>]*>\s*([\d,\.]+)\s*Tokens\s*<\/h4>/i', $html, $m)) return (float)str_replace(',', '', $m[1]);
    if (preg_match('/<h4[^>]*>\s*([\d,\.]+)\s*Tokens\s*<\/h4>/i', $html, $m)) return (float)str_replace(',', '', $m[1]);
    if (preg_match('/Account Balance[\s\S]{0,200}?(\d[\d,\.]*)\s*Tokens/i', $html, $m)) return (float)str_replace(',', '', $m[1]);
    return null;
}
function extractCooldown($html) {
    if (preg_match('/<b id="minute">(\d+)<\/b>\s*:\s*<b id="second">(\d+)<\/b>/i', $html, $m)) {
        $sec = (int)$m[1] * 60 + (int)$m[2]; if ($sec > 0) return $sec;
    }
    if (preg_match('/var wait = (\d+)\s*-\s*1\s*;/i', $html, $m)) return (int)$m[1];
    if (preg_match('/(?:wait|ready in)\s*(\d+)\s*sec/i', $html, $m)) return (int)$m[1];
    return 0;
}
function isReady($html) { return (bool)preg_match('/<h4[^>]*>\s*READY\s*<\/h4>/i', $html); }
function hasActiveForm($html) { return strpos($html, 'Collect your reward') !== false; }
function isLoggedIn($html) {
    return (strpos($html, 'Logout') !== false || strpos($html, 'key="t-henry"') !== false);
}
function hasClaimSuccess($html) {
    if (preg_match('/(\d+)\s+(?:tokens?|coins?)\s+h(?:as|ave)\s+been added/i', $html, $m)) return (int)$m[1];
    if (preg_match('/(\d+)\s+(?:tokens?|coins?)[\s\S]{0,60}?added to your balance/i', $html, $m)) return (int)$m[1];
    if (preg_match('/Success![\s\S]{0,300}?(\d+)\s+(?:tokens?|coins?)/i', $html, $m)) return (int)$m[1];
    return null;
}
function extractAntibot($html) {
    if (!preg_match('/Please click on the Anti-Bot links.*?<img src="data:image\/(\w+);base64,([^"]+)"/si', $html, $m)) return null;
    $instructionB64 = $m[2];
    if (!preg_match('/var ablinks=\s*(\[[\s\S]*?\])\s*<\/script>/si', $html, $m2)) return null;
    $ablinksRaw = $m2[1];
    $links = [];
    if (preg_match_all('/rel=\\\\?"(\d+)\\\\?"[^>]*><img[^>]*base64,([^"]+)/si', $ablinksRaw, $matches, PREG_SET_ORDER)) {
        foreach ($matches as $match) $links[] = ['rel' => $match[1], 'img' => $match[2]];
    }
    if (empty($links)) return null;
    return ['instruction' => $instructionB64, 'links' => $links, 'raw' => $ablinksRaw];
}

function parseSolverResp($raw) {
    $raw = trim($raw);
    if ($raw === '') return ['status'=>'error','id'=>'','code'=>'EMPTY'];
    $j = json_decode($raw, true);
    if (is_array($j)) {
        $req = isset($j['request']) ? trim((string)$j['request']) : '';
        $st  = isset($j['status']) ? (int)$j['status'] : null;
        if ($st === 1 && $req !== '' && strpos($req, 'ERROR_') !== 0 && strpos($req, 'CAPCHA_NOT_READY') === false) return ['status'=>'ok','id'=>$req,'code'=>''];
        if ($req === 'CAPCHA_NOT_READY') return ['status'=>'error','id'=>'','code'=>'NOT_READY'];
        if ($st === 0 || strpos($req, 'ERROR_') === 0) return ['status'=>'error','id'=>'','code'=>$req ?: 'UNKNOWN'];
        return ['status'=>'error','id'=>'','code'=>'UNKNOWN'];
    }
    if (strpos($raw, 'OK|') === 0) return ['status'=>'ok','id'=>trim(substr($raw,3)),'code'=>''];
    if (strpos($raw, 'ERROR_') === 0) { $p = explode('|', $raw, 2); return ['status'=>'error','id'=>'','code'=>$p[0]]; }
    return ['status'=>'error','id'=>'','code'=>$raw];
}

function _submitSolverTask($body, $asMultipart = false) {
    $ch = curl_init();
    $opts = [CURLOPT_URL => SOLVER_IN, CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true,
             CURLOPT_TIMEOUT => 60, CURLOPT_SSL_VERIFYPEER => false, CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4];
    if ($asMultipart) { $opts[CURLOPT_POSTFIELDS] = $body; }
    else { $opts[CURLOPT_POSTFIELDS] = json_encode($body); $opts[CURLOPT_HTTPHEADER] = ['Content-Type: application/json']; }
    curl_setopt_array($ch, $opts);
    $resp = curl_exec($ch); $err = curl_error($ch);
    if (PHP_VERSION_ID < 80000) curl_close($ch);
    if ($resp === false) { dbg('SOLVER', 'submit curl err: ' . $err); return false; }
    dbgDump('SOLVER-SUBMIT', $resp);
    $p = parseSolverResp($resp);
    if ($p['status'] === 'ok') return $p['id'];
    dbg('SOLVER', 'submit: ' . $p['code']);
    return false;
}

function _pollSolverTask($apikey, $id, $maxPolls = 40, $tag = 'POLL') {
    for ($i = 1; $i <= $maxPolls; $i++) {
        sleep(3);
        if ($i === 1 || $i % 5 === 0 || $i === $maxPolls) {
            liveLog("{$GLOBALS['C']['gray']}[{$tag}]{$GLOBALS['C']['reset']} polling {$i}/{$maxPolls}");
        }
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => SOLVER_OUT . "?apikey=" . urlencode($apikey) . "&action=get&id=" . urlencode($id) . "&json=1",
            CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 30,
            CURLOPT_SSL_VERIFYPEER => false, CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4,
        ]);
        $poll = curl_exec($ch);
        if (PHP_VERSION_ID < 80000) curl_close($ch);
        if ($poll === false) continue;
        dbgDump('POLL', $poll);
        $p = parseSolverResp($poll);
        if ($p['status'] === 'ok' && $p['id']) return $p['id'];
        if ($p['code'] === 'NOT_READY' || $p['code'] === 'CAPCHA_NOT_READY') continue;
        dbg('POLL', "hard err poll #$i: " . $p['code']);
        return false;
    }
    return false;
}

function solveTurnstile($apikey, $sitekey, $domain = 'https://hatecoin.me') {
    $body = ['apikey' => $apikey, 'methods' => 'turnstile', 'domain' => $domain, 'sitekey' => $sitekey, 'json' => 1];
    $id = _submitSolverTask($body);
    if (!$id) return false;
    return _pollSolverTask($apikey, $id, 60, 'TS');
}

function solveAntibot($apikey, $antibot) {
    $payloads = [];
    $base = ['apikey' => $apikey, 'methods' => 'antibot', 'main' => $antibot['instruction'], 'json' => 1];
    $pA = $base;
    foreach ($antibot['links'] as $l) $pA[$l['rel']] = $l['img'];
    $payloads['rel_as_key'] = ['body' => $pA, 'multipart' => false];
    $payloads['rel_as_key_mp'] = ['body' => $pA, 'multipart' => true];
    $pC = $base;
    foreach ($antibot['links'] as $i => $l) {
        $n = $i + 1; $pC['img' . $n] = $l['img']; $pC['id' . $n] = $l['rel'];
    }
    $payloads['imgN+idN'] = ['body' => $pC, 'multipart' => false];
    foreach ($payloads as $name => $cfg) {
        $id = _submitSolverTask($cfg['body'], $cfg['multipart']);
        if (!$id) continue;
        $token = _pollSolverTask($apikey, $id, 20, 'AB');
        if ($token) return $token;
    }
    return false;
}

function formatAntibotToken($raw) {
    $raw = trim($raw); if ($raw === '') return '';
    $parts = preg_split('/[\s,]+/', $raw);
    $parts = array_filter(array_map('trim', $parts), fn($x) => $x !== '');
    $clean = [];
    foreach ($parts as $p) { $p = ltrim($p, '+'); if ($p !== '' && ctype_digit($p)) $clean[] = $p; }
    if (empty($clean)) return '+' . preg_replace('/[\s,]+/', '+', ltrim($raw, '+'));
    return '+' . implode('+', $clean);
}

function checkSolverBalance($apikey) {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => SOLVER_BALANCE . "?apikey=" . urlencode($apikey),
        CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => false, CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4,
    ]);
    $r = curl_exec($ch); if (PHP_VERSION_ID < 80000) curl_close($ch);
    $j = json_decode($r, true);
    return ($j && isset($j['balance'])) ? (int)$j['balance'] : null;
}

function loadCfg() {
    if (!file_exists(CFG_FILE)) return ['email' => '', 'password' => '', 'apikey' => '', 'user_agent' => DEFAULT_UA];
    $d = json_decode(file_get_contents(CFG_FILE), true);
    if (!is_array($d)) return ['email' => '', 'password' => '', 'apikey' => '', 'user_agent' => DEFAULT_UA];
    return array_merge(['email' => '', 'password' => '', 'apikey' => '', 'user_agent' => DEFAULT_UA], $d);
}
function saveCfg($d) {
    file_put_contents(CFG_FILE, json_encode($d, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    @chmod(CFG_FILE, 0600);
}

function doLogin($cfg) {
    $GLOBALS['USER_AGENT'] = $cfg['user_agent'] ?? DEFAULT_UA;
    $r = req(HOST . '/login', null, ['Referer: ' . HOST . '/']);
    if ($r['body'] === '') return ['ok' => false, 'reason' => 'empty: ' . $r['err']];
    $csrf = extractCsrf($r['body']);
    $sitekey = extractSitekey($r['body']);
    if (!$csrf || !$sitekey) return ['ok' => false, 'reason' => 'csrf/sitekey missing'];

    L_verify('Turnstile verification in progress...');
    $ts = solveTurnstile($cfg['apikey'], $sitekey);
    if (!$ts) return ['ok' => false, 'reason' => 'turnstile failed'];
    L_token_cf($ts);

    usleep(mt_rand(1500000, 3000000));
    $post = [
        'csrf_token_name' => $csrf, 'email' => $cfg['email'], 'password' => $cfg['password'],
        'captcha' => 'recaptchav2', 'cf-turnstile-response' => $ts, 'g-recaptcha-response' => $ts,
    ];
    $r2 = req(HOST . '/auth/login', $post, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST, 'Referer: ' . HOST . '/login',
    ]);
    if ($r2['body'] === '') return ['ok' => false, 'reason' => 'empty POST'];

    usleep(mt_rand(800000, 1500000));
    $r3 = req(HOST . '/dashboard', null, ['Referer: ' . HOST . '/login']);
    if ($r3['body'] === '') return ['ok' => false, 'reason' => 'empty dash'];
    if (!isLoggedIn($r3['body'])) return ['ok' => false, 'reason' => 'login failed'];

    $GLOBALS['SESSION_VERIFIED_AT'] = time();
    return ['ok' => true, 'balance' => extractBalance($r3['body'])];
}

function verifySession() {
    $r = req(HOST . '/dashboard', null, ['Referer: ' . HOST . '/']);
    if ($r['body'] === '') return ['ok' => false];
    if (!isLoggedIn($r['body'])) return ['ok' => false];
    $GLOBALS['SESSION_VERIFIED_AT'] = time();
    return ['ok' => true, 'balance' => extractBalance($r['body'])];
}

function refreshBalance() {
    $r = req(HOST . '/dashboard', null, ['Referer: ' . HOST . '/']);
    if ($r['body'] === '') return null;
    $GLOBALS['SESSION_VERIFIED_AT'] = time();
    return extractBalance($r['body']);
}

function ensureSession(&$cfg, &$session, $force = false) {
    $cacheValid = (time() - $GLOBALS['SESSION_VERIFIED_AT']) < SESSION_TTL;
    if (!$force && $cacheValid && $session && $session['ok']) return true;

    $r = req(HOST . '/dashboard', null, ['Referer: ' . HOST . '/']);
    if ($r['body'] !== '' && isLoggedIn($r['body'])) {
        $GLOBALS['SESSION_VERIFIED_AT'] = time();
        return true;
    }
    L_rejoin('session expired — relogin...');
    resetCookieJar();
    $login = doLogin($cfg);
    if (!$login['ok']) { L_error('REJOIN', 'failed: ' . $login['reason']); return false; }
    $session = $login;
    L_success('SESSION', 'logged in');
    return true;
}

function refreshPage($path) {
    L_refresh("GET $path");
    $r = req(HOST . $path, null, ['Referer: ' . HOST . '/dashboard']);
    usleep(mt_rand(REFRESH_WAIT * 1000000, (REFRESH_WAIT + 1) * 1000000));
    return $r;
}

function attemptClaim($cfg, $type = 'faucet') {
    $path       = $type === 'madfaucet' ? '/madfaucet' : '/faucet';
    $verifyPath = $type === 'madfaucet' ? '/madfaucet/verify' : '/faucet/verify';
    $defaultCd  = $type === 'madfaucet' ? 600 : 300;
    $tag        = $type === 'madfaucet' ? 'MAD' : 'FAUCET';

    L_info($tag, 'Checking availability...');
    $r = req(HOST . $path, null, ['Referer: ' . HOST . '/dashboard']);
    if ($r['body'] === '') return ['status' => 'error', 'reason' => 'empty GET'];

    if (!isLoggedIn($r['body'])) return ['status' => 'expired', 'reason' => 'session expired'];
    if (!isReady($r['body'])) {
        $cd = extractCooldown($r['body']);
        if ($cd > 0) return ['status' => 'cooldown', 'wait' => $cd];
        return ['status' => 'skip', 'reason' => 'not ready'];
    }

    $csrf = extractCsrf($r['body']);
    $sitekey = extractSitekey($r['body']);
    $antibot = extractAntibot($r['body']);

    if (!$csrf) return ['status' => 'skip', 'reason' => 'csrf missing'];
    if (!$sitekey) return ['status' => 'skip', 'reason' => 'sitekey missing'];
    if (!$antibot) return ['status' => 'skip', 'reason' => 'antibot not found'];

    L_claim("Processing $type claim...");
    L_verify('Turnstile verification in progress...');
    $ts = solveTurnstile($cfg['apikey'], $sitekey);
    if (!$ts) return ['status' => 'error', 'reason' => 'turnstile solve failed'];
    L_token_cf($ts);

    L_verify('Anti-bot verification in progress...');
    $abRaw = solveAntibot($cfg['apikey'], $antibot);
    if (!$abRaw) return ['status' => 'error', 'reason' => 'antibot solve failed'];

    $ab = formatAntibotToken($abRaw);
    if ($ab === '') return ['status' => 'error', 'reason' => 'antibot token invalid'];
    L_token_ab($ab);

    L_verify('Verification completed');

    $delay = mt_rand(POST_DELAY_MIN, POST_DELAY_MAX);
    L_human("delay before POST: {$delay}s");
    sleep($delay);

    $body = 'antibotlinks=' . $ab
          . '&csrf_token_name=' . urlencode($csrf)
          . '&captcha=recaptchav2'
          . '&cf-turnstile-response=' . urlencode($ts)
          . '&g-recaptcha-response=' . urlencode($ts);

    $r2 = req(HOST . $verifyPath, $body, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST, 'Referer: ' . HOST . $path,
        'Sec-Fetch-Dest: document', 'Sec-Fetch-Mode: navigate', 'Sec-Fetch-Site: same-origin',
    ]);
    if ($r2['body'] === '') return ['status' => 'error', 'reason' => 'empty POST'];

    $reward = hasClaimSuccess($r2['body']);
    $cd = extractCooldown($r2['body']);
    $ready = isReady($r2['body']);
    $activeForm = hasActiveForm($r2['body']);

    if ($reward !== null) {
        if ($cd < 1) $cd = $defaultCd;
        L_info('BALANCE', 'refreshing...');
        $bal = refreshBalance();
        @file_put_contents(LOG_FILE, date('Y-m-d H:i:s') . " | $type | reward=$reward | balance=" . ($bal ?? '?') . " | cd=$cd\n", FILE_APPEND);
        return ['status' => 'success', 'reward' => $reward, 'balance' => $bal, 'cooldown' => $cd];
    }
    if ($cd > 0 && !$activeForm) {
        L_info('BALANCE', 'refreshing...');
        $bal = refreshBalance();
        $fb = $type === 'madfaucet' ? 20 : 40;
        @file_put_contents(LOG_FILE, date('Y-m-d H:i:s') . " | $type | reward=$fb (fallback) | balance=" . ($bal ?? '?') . " | cd=$cd\n", FILE_APPEND);
        return ['status' => 'success', 'reward' => $fb, 'balance' => $bal, 'cooldown' => $cd];
    }
    if ($cd > 0) return ['status' => 'cooldown', 'wait' => $cd];
    if ($activeForm && $ready) { saveRejectResponse($r2['body'], $type); return ['status' => 'rejected', 'reason' => 'rejected']; }
    if (!$activeForm) {
        L_info('BALANCE', 'refreshing...');
        $bal = refreshBalance();
        return ['status' => 'success', 'reward' => 0, 'balance' => $bal, 'cooldown' => $defaultCd];
    }
    return ['status' => 'error', 'reason' => 'unknown state'];
}

function doClaimWithFlow(&$cfg, &$session, $type = 'faucet') {
    $path = $type === 'madfaucet' ? '/madfaucet' : '/faucet';

    $res = attemptClaim($cfg, $type);
    if ($res['status'] === 'success') return $res;
    if ($res['status'] === 'cooldown') return $res;
    if ($res['status'] === 'expired') {
        L_rejoin('session expired');
        if (ensureSession($cfg, $session, true)) {
            L_refresh('retry after rejoin');
            return attemptClaim($cfg, $type);
        }
        return $res;
    }

    if ($res['status'] === 'rejected' || $res['status'] === 'error' || $res['status'] === 'skip') {
        // Refresh page (cheap, no solver yet)
        L_refresh("refresh before retry");
        refreshPage($path);

        // Retry with fresh tokens
        L_info('RETRY', 'retry with fresh tokens');
        $res2 = attemptClaim($cfg, $type);
        if ($res2['status'] === 'success') return $res2;
        if ($res2['status'] === 'cooldown') return $res2;

        // Still failing → rejoin (kocak: this stays)
        if ($res2['status'] === 'rejected' || $res2['status'] === 'error' || $res2['status'] === 'skip' || $res2['status'] === 'expired') {
            L_rejoin('instant rejoin on retry fail');
            resetCookieJar();
            $login = doLogin($cfg);
            if (!$login['ok']) return ['status' => 'error', 'reason' => 'rejoin failed'];
            $session = $login;
            L_success('SESSION', 'logged in');

            L_refresh('retry after rejoin');
            usleep(mt_rand(2000000, 3500000));
            $res3 = attemptClaim($cfg, $type);
            return $res3;
        }
        return $res2;
    }
    return $res;
}

function printBanner($mode = '', $status = '') {
    global $C;
    echo "\n" . $C['cyan'] . wideLine() . $C['reset'] . "\n";
    echo centerText($C['white'] . "HATECOIN.ME AUTO BOT" . $C['reset']) . "\n";
    echo $C['cyan'] . wideLine() . $C['reset'] . "\n";
    if ($mode !== '') {
        printf("  %-10s : %s\n", 'Developer', 'MoneyMaker_w');
        printf("  %-10s : %s\n", 'Mode', $C['neonY'] . $mode . $C['reset']);
        if ($status !== '') printf("  %-10s : %s\n", 'Status', $C['neonG'] . $status . $C['reset']);
        printf("  %-10s : %s\n", 'CH', $C['cyan'] . TG_CHANNEL . $C['reset']);
        echo $C['cyan'] . wideLine() . $C['reset'] . "\n";
    }
}

function printSection($title, $color = 'cyan') {
    global $C, $LIVE;
    if ($LIVE['enabled']) {
        $LIVE['logs'][] = "{$C[$color]}━━━ {$C['white']}" . strtoupper($title) . "{$C[$color]} ━━━{$C['reset']}";
        if (count($LIVE['logs']) > $LIVE['max_logs']) array_shift($LIVE['logs']);
        liveRender();
        return;
    }
    echo "\n" . $C[$color] . wideLine() . $C['reset'] . "\n";
    echo centerText($C['white'] . strtoupper($title) . $C['reset']) . "\n";
    echo $C[$color] . wideLine() . $C['reset'] . "\n\n";
}

function printMainMenu($cfg, $session) {
    global $C;
    printBanner();
    if ($session && $session['ok']) { L_session('logged in'); L_balance(($session['balance'] ?? '?') . ' coins'); }
    else L_info('SESSION', 'Not logged in');
    L_info('SOLVER', (strlen($cfg['apikey']) > 0 ? substr($cfg['apikey'], 0, 8) . '...' : '(empty)'));
    L_info('UA', (strlen($cfg['user_agent'] ?? '') > 0 ? substr($cfg['user_agent'], 0, 50) . '...' : '(empty)'));
    $dbgState = !empty($GLOBALS['DEBUG']) ? "{$C['green']}ON{$C['reset']}" : "{$C['gray']}OFF{$C['reset']}";
    echo "\n" . $C['gray'] . str_repeat('─', WIDE) . $C['reset'] . "\n\n";
    echo "    {$C['orange']}[1]{$C['reset']} Start Farming ( Faucet & Mad )\n";
    echo "    {$C['orange']}[2]{$C['reset']} Only Faucet\n";
    echo "    {$C['orange']}[3]{$C['reset']} Only MadFaucet\n";
    echo "    {$C['orange']}[4]{$C['reset']} Config Email And Password\n";
    echo "    {$C['orange']}[5]{$C['reset']} Provider / Solver\n";
    echo "    {$C['orange']}[6]{$C['reset']} Toggle Debug ({$dbgState})\n";
    echo "    {$C['orange']}[7]{$C['reset']} Set User-Agent\n";
    echo "    {$C['gray']}[0]{$C['reset']} Exit\n\n";
    echo "  {$C['gray']}>> {$C['reset']}";
}

function printClaimSuccess($res, $type) {
    liveStatSuccess($res['reward'], $type);
    $tag = $type === 'madfaucet' ? 'MAD' : 'CLAIM';
    $label = $type === 'madfaucet' ? 'Claim successful' : 'SUCCESS';
    L_success($tag, "{$label} | 🔥 +{$res['reward']} coins");
    L_balance('Updated → ' . ($res['balance'] ?? '?') . ' coins');
}

function configAccount(&$cfg) {
    global $C, $LIVE; $LIVE['enabled'] = false;
    clear(); printBanner(); printSection('CONFIG EMAIL & PASSWORD');
    echo "  Current email : " . ($cfg['email'] ?: '(empty)') . "\n";
    $email = prompt("  New email     : ");
    if ($email !== '') $cfg['email'] = $email;
    echo "  Current pass  : " . (strlen($cfg['password']) ? str_repeat('*', 8) : '(empty)') . "\n";
    $pass = prompt("  New password  : ");
    if ($pass !== '') $cfg['password'] = $pass;
    saveCfg($cfg);
    echo "\n"; L_success('CONFIG', 'saved');
    sleep(1);
}

function configSolver(&$cfg) {
    global $C, $LIVE; $LIVE['enabled'] = false;
    clear(); printBanner(); printSection('PROVIDER / SOLVER');
    echo "  Provider  : api.waryono.my.id\n";
    echo "  Services  : Turnstile (2.3 tok) + Antibot (0.4 tok)\n\n";
    echo "  Current key : " . (strlen($cfg['apikey']) ? substr($cfg['apikey'], 0, 12) . '...' : '(empty)') . "\n";
    $key = prompt("  New API key : ");
    if ($key !== '') {
        $cfg['apikey'] = $key; saveCfg($cfg);
        echo "\n"; L_success('SOLVER', 'saved');
        L_info('SOLVER', 'checking balance...');
        $bal = checkSolverBalance($key);
        if ($bal !== null) L_success('SOLVER', 'balance: ' . number_format($bal) . ' tokens');
        else L_error('SOLVER', 'balance check failed');
    }
    sleep(1);
}

function configUA(&$cfg) {
    global $C, $LIVE; $LIVE['enabled'] = false;
    clear(); printBanner(); printSection('SET USER-AGENT');
    echo "  Current UA :\n  {$C['gray']}" . ($cfg['user_agent'] ?: '(empty)') . "{$C['reset']}\n\n";
    echo "  {$C['gray']}Paste User-Agent baru (kosong = reset ke default){$C['reset']}\n";
    $ua = prompt("  New UA : ");
    if ($ua === '') { $cfg['user_agent'] = DEFAULT_UA; L_success('UA', 'reset'); }
    else { $cfg['user_agent'] = $ua; L_success('UA', 'saved'); }
    saveCfg($cfg);
    sleep(1);
}

function farmLoop(&$cfg, &$session, $mode = 'both') {
    global $C, $LIVE;
    clear();
    $modeStr = $mode === 'both' ? 'FAUCET + MAD' : ($mode === 'faucet' ? 'ONLY FAUCET' : 'ONLY MAD FAUCET');
    printBanner($modeStr, 'LIVE RUNNING');

    $LIVE['enabled'] = true;
    $LIVE['logs'] = [];
    $LIVE['lines'] = 0;
    $LIVE['stats'] = ['success' => 0, 'error' => 0, 'reward' => 0, 'faucet' => 0, 'mad' => 0];

    if (!$session || !$session['ok']) {
        resetCookieJar();
        $res = doLogin($cfg);
        if (!$res['ok']) {
            $LIVE['enabled'] = false;
            L_error('SESSION', $res['reason']);
            echo "\n  ENTER untuk kembali..."; fgets(STDIN); return;
        }
        $session = $res;
    }
    L_success('SESSION', 'logged in');
    L_balance(($session['balance'] ?? '?') . ' coins');

    // 1x check timer di awal
    L_info('CHECK', 'initial timer...');
    $fsR = req(HOST . '/faucet', null, ['Referer: ' . HOST . '/dashboard']);
    $fsCd = ($fsR['body'] !== '') ? (isReady($fsR['body']) ? 0 : extractCooldown($fsR['body'])) : 0;
    usleep(mt_rand(1000000, 2000000));
    $msR = req(HOST . '/madfaucet', null, ['Referer: ' . HOST . '/dashboard']);
    $msCd = ($msR['body'] !== '') ? (isReady($msR['body']) ? 0 : extractCooldown($msR['body'])) : 0;

    $cdFaucet = time() + $fsCd;
    $cdMad = time() + $msCd;
    L_info('STATUS', "faucet=" . ($fsCd > 0 ? "{$fsCd}s" : 'READY') . "  mad=" . ($msCd > 0 ? "{$msCd}s" : 'READY'));

    $consecErr = 0; $round = 0;

    while (true) {
        if (isErrorLimitHit()) {
            $LIVE['enabled'] = false;
            clear();
            printBanner('STOPPED', 'ERROR LIMIT');
            L_error('STOP', 'max ' . MAX_TOTAL_ERR . ' errors reached — stopping');
            L_info('STATS', "✓ {$LIVE['stats']['success']}  ✗ {$LIVE['stats']['error']}  🔥 +{$LIVE['stats']['reward']}");
            echo "\n  ENTER untuk kembali..."; fgets(STDIN);
            return;
        }

        $round++;
        $now = time();
        $doFaucet = false; $doMad = false;
        if (($mode === 'faucet' || $mode === 'both') && $now >= $cdFaucet) $doFaucet = true;
        if (($mode === 'madfaucet' || $mode === 'both') && $now >= $cdMad) $doMad = true;

        // ═══ FIX: cooldown = sleep only, NO rejoin, NO API call ═══
        if (!$doFaucet && !$doMad) {
            $waitFaucet = ($mode === 'madfaucet') ? PHP_INT_MAX : max(0, $cdFaucet - $now);
            $waitMad    = ($mode === 'faucet')    ? PHP_INT_MAX : max(0, $cdMad - $now);
            $wait = max(1, min($waitFaucet, $waitMad));

            L_wait("sleeping {$wait}s — cooldown (no API call)");
            L_info('STATUS', "faucet={$waitFaucet}s  mad={$waitMad}s");
            liveWait($wait, 'next claim in');
            continue;
        }

        // Session verify hanya kalau TTL expired atau baru ada error
        $needSession = ((time() - $GLOBALS['SESSION_VERIFIED_AT']) > SESSION_TTL) || ($consecErr > 0);
        if ($needSession && !ensureSession($cfg, $session)) {
            $LIVE['enabled'] = false;
            L_error('SESSION', 'cannot rejoin — stopping');
            echo "\n  ENTER..."; fgets(STDIN); return;
        }

        if ($doFaucet) {
            printSection('FAUCET CLAIM');
            $res = doClaimWithFlow($cfg, $session, 'faucet');
            if ($res['status'] === 'success') {
                printClaimSuccess($res, 'faucet');
                $cdFaucet = time() + $res['cooldown'] + mt_rand(CLAIM_GAP_MIN, CLAIM_GAP_MAX);
                $consecErr = 0;
            } elseif ($res['status'] === 'cooldown') {
                L_wait('faucet cooldown ' . $res['wait'] . 's');
                $cdFaucet = time() + $res['wait'] + mt_rand(2, 5);
            } elseif ($res['status'] === 'expired') {
                if (!ensureSession($cfg, $session, true)) { $LIVE['enabled'] = false; echo "\n  ENTER..."; fgets(STDIN); return; }
                $cdFaucet = time() + 3;
            } else {
                liveStatError();
                L_error('FAUCET', $res['reason'] ?? 'unknown');
                $consecErr++;
                $backoff = min(180, 20 * pow(2, $consecErr - 1));
                $cdFaucet = time() + $backoff;
                if ($consecErr >= 3) $consecErr = 0;
            }
        }

        if ($doMad) {
            printSection('MAD FAUCET');
            $res = doClaimWithFlow($cfg, $session, 'madfaucet');
            if ($res['status'] === 'success') {
                printClaimSuccess($res, 'madfaucet');
                $cdMad = time() + $res['cooldown'] + mt_rand(CLAIM_GAP_MIN, CLAIM_GAP_MAX);
                $consecErr = 0;
            } elseif ($res['status'] === 'cooldown') {
                L_wait('mad faucet cooldown ' . $res['wait'] . 's');
                $cdMad = time() + $res['wait'] + mt_rand(2, 5);
            } elseif ($res['status'] === 'expired') {
                if (!ensureSession($cfg, $session, true)) { $LIVE['enabled'] = false; echo "\n  ENTER..."; fgets(STDIN); return; }
                $cdMad = time() + 3;
            } else {
                liveStatError();
                L_error('MAD', $res['reason'] ?? 'unknown');
                $consecErr++;
                $backoff = min(180, 20 * pow(2, $consecErr - 1));
                $cdMad = time() + $backoff;
                if ($consecErr >= 3) $consecErr = 0;
            }
        }
    }
}

clear();
$LIVE['enabled'] = false;
$cfg = loadCfg();
$GLOBALS['USER_AGENT'] = $cfg['user_agent'] ?? DEFAULT_UA;
$session = null;

if ($cfg['email'] !== '' && $cfg['password'] !== '' && $cfg['apikey'] !== '') {
    $v = verifySession();
    if ($v['ok']) $session = $v;
}

while (true) {
    clear();
    $LIVE['enabled'] = false;
    printMainMenu($cfg, $session);
    $choice = prompt('');
    if ($choice === '0' || $choice === '') { echo "\n  Bye, bos.\n"; exit(0); }

    $needConfig = ($cfg['email'] === '' || $cfg['password'] === '' || $cfg['apikey'] === '');

    if ($choice === '1') { if ($needConfig) { L_error('CONFIG', 'lengkapi config dulu'); sleep(2); continue; } farmLoop($cfg, $session, 'both'); }
    if ($choice === '2') { if ($needConfig) { L_error('CONFIG', 'lengkapi config dulu'); sleep(2); continue; } farmLoop($cfg, $session, 'faucet'); }
    if ($choice === '3') { if ($needConfig) { L_error('CONFIG', 'lengkapi config dulu'); sleep(2); continue; } farmLoop($cfg, $session, 'madfaucet'); }
    if ($choice === '4') { configAccount($cfg); $session = null; }
    if ($choice === '5') { configSolver($cfg); }
    if ($choice === '6') {
        $GLOBALS['DEBUG'] = empty($GLOBALS['DEBUG']);
        clear(); printBanner();
        L_success('DEBUG', 'toggled → ' . ($GLOBALS['DEBUG'] ? 'ON' : 'OFF'));
        sleep(1);
    }
    if ($choice === '7') {
        configUA($cfg);
        $GLOBALS['USER_AGENT'] = $cfg['user_agent'] ?? DEFAULT_UA;
        $session = null;
    }
}
