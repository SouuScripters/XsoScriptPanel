<?php
/**
 * altcryp.com faucet bot v8 FINAL
 * - TIDAK re-GET setelah wait (fix timer reset)
 * - Hitung 8s dari GET pertama sebelum POST
 * - Firewall bypass hanya kalau ke-detect
 * Credit: MoneyMaker_w
 */

error_reporting(0);
date_default_timezone_set('Asia/Jakarta');

$configFile = "config_altcryp.json";
$debugLog   = "debug_altcryp.log";
$DEBUG = true;

const RESET      = "\033[0m";
const N_CYAN     = "\033[38;5;51m";
const N_GREEN    = "\033[38;5;46m";
const N_YELLOW   = "\033[38;5;226m";
const N_MAGENTA  = "\033[38;5;201m";
const N_PINK     = "\033[38;5;207m";
const N_BLUE     = "\033[38;5;45m";
const N_RED      = "\033[38;5;196m";
const N_ORANGE   = "\033[38;5;208m";
const N_PURPLE   = "\033[38;5;129m";
const N_WHITE    = "\033[38;5;231m";
const N_GRAY     = "\033[38;5;245m";

const putih = N_WHITE; const hijau = N_GREEN; const kuning = N_YELLOW;
const merah = N_RED;   const cyan  = N_CYAN;  const reset  = RESET;

const host        = "https://altcryp.com";
const solver_in   = "https://api.waryono.my.id/in.php";
const solver_res  = "https://api.waryono.my.id/res.php";
const MIN_PAGE_WAIT = 8;   // detik minimum dari GET sebelum POST
const FIREWALL_MAX_BYPASS = 3;

$ALL_COINS = ['bnb','bch','dash','doge','dgb','pol','sol','trx','ltc','xrp','zec','usdt','ton','pepe','eth','fey','trump'];

function dbg($tag, $msg) {
    global $DEBUG, $debugLog;
    if (!$DEBUG) return;
    $line = "[".date('H:i:s')."][$tag] $msg";
    echo "    ".N_GRAY.$line.RESET."\n";
    file_put_contents($debugLog, $line."\n", FILE_APPEND);
}

function clear() { (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w')); }

function timer($seconds, $prefix = "") {
    $wait_time = (int)$seconds;
    if ($wait_time <= 0) return;
    $frames = ['⣾','⣽','⣻','⢿','⡿','⣟','⣯','⣷'];
    $fc = count($frames); $cf = 0;
    while ($wait_time > 0) {
        $start = microtime(true);
        while ((microtime(true) - $start) < 1) {
            $tf = sprintf('%02d:%02d:%02d', floor($wait_time/3600), floor(($wait_time%3600)/60), $wait_time%60);
            echo "    ".N_CYAN.$prefix." ".N_YELLOW.$tf." ".N_MAGENTA.$frames[$cf]."\r";
            usleep(100000);
            $cf = ($cf + 1) % $fc;
            if ((microtime(true) - $start) >= 1) break;
        }
        $wait_time--;
    }
    echo "\r                                                \r";
}

function sleepUntil($targetTs, $prefix = "") {
    $remain = $targetTs - microtime(true);
    if ($remain > 0) timer(ceil($remain), $prefix);
}

function cookiesToStr($state) {
    $p = []; foreach ($state as $k => $v) $p[] = $k.'='.$v;
    return implode('; ', $p);
}
function cookiesFromStr($str) {
    $out = [];
    foreach (explode(';', $str) as $p) {
        $p = trim($p); if (!$p) continue;
        $kv = explode('=', $p, 2);
        if (count($kv) === 2) $out[trim($kv[0])] = trim($kv[1]);
    }
    return $out;
}
function mergeSetCookies(&$state, $rawHeaders) {
    if (!$rawHeaders) return;
    if (preg_match_all('/^set-cookie:\s*([^=]+)=([^;\r\n]*)/im', $rawHeaders, $m, PREG_SET_ORDER)) {
        foreach ($m as $mm) {
            $k = trim($mm[1]); $v = trim($mm[2]);
            if ($k) $state[$k] = $v;
        }
    }
}

function req($url, $method = 'GET', $data = null, $headers = [], &$cookieState = null) {
    $ch = curl_init();
    if ($cookieState !== null) {
        $ck = cookiesToStr($cookieState);
        $newHeaders = []; $hasCookie = false;
        foreach ($headers as $h) {
            if (stripos($h, 'Cookie:') === 0) { $hasCookie = true; $h = "Cookie: $ck"; }
            $newHeaders[] = $h;
        }
        if (!$hasCookie) $newHeaders[] = "Cookie: $ck";
        $headers = $newHeaders;
    }
    $opts = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HEADER         => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS      => 5,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CONNECTTIMEOUT => 60,
        CURLOPT_TIMEOUT        => 120,
        CURLOPT_ENCODING       => "",
    ];
    if (strtoupper($method) === 'POST') {
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = is_array($data) ? http_build_query($data) : $data;
    }
    curl_setopt_array($ch, $opts);
    $resp = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $finalUrl = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
    if ($resp === false) {
        $err = curl_error($ch); curl_close($ch);
        dbg("REQ", "$method $url → FAIL: $err");
        return ['body' => '', 'headers' => '', 'error' => $err, 'code'=>0, 'url'=>$url];
    }
    $hsize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $rawHeaders = substr($resp, 0, $hsize);
    $body = substr($resp, $hsize);
    curl_close($ch);
    if ($cookieState !== null) mergeSetCookies($cookieState, $rawHeaders);
    dbg("REQ", "$method $url → $httpCode (final:$finalUrl, len:".strlen($body).")");
    return ['body' => $body, 'headers' => $rawHeaders, 'error' => null, 'code'=>$httpCode, 'url'=>$finalUrl];
}

function solveTurnstile($apikey, $sitekey, $domain) {
    $payload = ["apikey"=>$apikey,"methods"=>"turnstile","domain"=>$domain,"sitekey"=>$sitekey,"json"=>1];
    $null = null;
    $r = req(solver_in, "POST", json_encode($payload), ["Content-Type: application/json"], $null);
    $json = json_decode($r['body'], true);
    if (!isset($json['status'])) {
        if (preg_match('/OK\|(\w+)/', $r['body'], $m)) $json = ['status'=>1,'request'=>$m[1]];
        else return ['error' => "solver_reply: ".trim(substr($r['body'],0,80))];
    }
    if ($json['status'] != 1) return ['error' => $json['request']];
    $id = $json['request'];
    $start = time();
    while (true) {
        if (time() - $start > 180) return ['error' => 'TIMEOUT_SOLVE'];
        sleep(5);
        $u = solver_res."?apikey=".$apikey."&action=get&id=".$id."&json=1";
        $rr = req($u, "GET", null, [], $null);
        $j = json_decode($rr['body'], true);
        if (!isset($j['status'])) {
            if (strpos($rr['body'], 'CAPCHA_NOT_READY') !== false) continue;
            if (preg_match('/OK\|(.+)/', $rr['body'], $m)) return ['token' => trim($m[1])];
            continue;
        }
        if ($j['status'] == 1) return ['token' => $j['request']];
        if ($j['request'] === 'CAPCHA_NOT_READY') continue;
        return ['error' => $j['request']];
    }
}

function getConfig($file) {
    if (!file_exists($file)) {
        echo N_CYAN."API Key (waryono): ".N_YELLOW;  $api = trim(fgets(STDIN));
        echo N_CYAN."Cookie (paste full cookie string): ".N_YELLOW; $ck = trim(fgets(STDIN));
        echo N_CYAN."User-Agent (enter=default): ".N_YELLOW; $ua = trim(fgets(STDIN));
        if (!$ua) $ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36";
        $cfg = ["apikey" => $api, "cookie" => $ck, "user_agent" => $ua];
        file_put_contents($file, json_encode($cfg, JSON_PRETTY_PRINT));
        echo N_GREEN."Saved -> $file\n".RESET; sleep(2);
        return $cfg;
    }
    return json_decode(file_get_contents($file), true);
}
function saveConfig($file, $cfg) { file_put_contents($file, json_encode($cfg, JSON_PRETTY_PRINT)); }

function banner() {
    echo N_CYAN."╔═══════════════════════════════════════════════════════╗\n";
    echo N_CYAN."║  ".N_GREEN."  ▄▀█ █░░ ▀█▀ █▀▀ █▀█ █▄█ █▀█   ".N_CYAN."Faucet Bot v8   ║\n";
    echo N_CYAN."║  ".N_GREEN."  █▀█ █▄▄ ░█░ █▄▄ █▀▄ ░█░ █▀▀   ".N_CYAN."Timer Fixed     ║\n";
    echo N_CYAN."╠═══════════════════════════════════════════════════════╣\n";
    echo N_CYAN."║  ".N_YELLOW."Script :".N_WHITE." altcryp.com           ".N_CYAN."║\n";
    echo N_CYAN."║  ".N_YELLOW."Solver :".N_WHITE." api.waryono.my.id     ".N_CYAN."║\n";
    echo N_CYAN."║  ".N_MAGENTA."Maker  :".N_PINK." MoneyMaker_w          ".N_CYAN."║\n";
    echo N_CYAN."╚═══════════════════════════════════════════════════════╝".RESET."\n\n";
}

function buildHeaders($ua, $referer = '') {
    $h = [
        "Host: altcryp.com",
        "User-Agent: $ua",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language: id-ID,id;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests: 1",
    ];
    if ($referer) $h[] = "Referer: $referer";
    return $h;
}

function hasClaimForm($html) {
    $a = preg_match('/<form[^>]+action="[^"]*\/faucet\/verify\/[^"]*"/i', $html);
    $b = strpos($html, 'id="fauform"') !== false;
    $c = preg_match('/name="token"\s+value="[^"]+"/i', $html);
    $d = preg_match('/name="csrf_token_name"/i', $html);
    return ($a || $b || ($c && $d));
}

function isFirewallPage($html) {
    if (strpos($html, '<title>Firewall') !== false) return true;
    if (preg_match('/<form[^>]+action="[^"]*\/firewall\/verify/i', $html)) return true;
    return false;
}

function parseFirewallForm($html, $currentUrl) {
    $out = ['action'=>null, 'sitekey'=>null, 'inputs'=>[]];
    if (preg_match('/<form[^>]+action="([^"]+)"/i', $html, $m)) {
        $action = html_entity_decode($m[1]);
        if (strpos($action, 'http') !== 0) $action = host.$action;
        $out['action'] = $action;
    } else {
        $out['action'] = $currentUrl;
    }
    if (preg_match('/data-sitekey="([^"]+)"/i', $html, $m)) $out['sitekey'] = $m[1];

    if (preg_match_all('/<input[^>]+name="([^"]+)"[^>]*value="([^"]*)"/i', $html, $mm, PREG_SET_ORDER)) {
        foreach ($mm as $inp) {
            $name = $inp[1]; $val = $inp[2];
            if ($name === 'cf-turnstile-response' || $name === 'g-recaptcha-response') continue;
            $out['inputs'][$name] = $val;
        }
    }
    return $out;
}

function bypassFirewall(&$cookieState, $cfg, $firewallUrl, $firewallHtml, $debug) {
    $ua = $cfg['user_agent'];
    $api = $cfg['apikey'];

    $form = parseFirewallForm($firewallHtml, $firewallUrl);
    if ($debug) {
        dbg("FW-PARSE", "action=".$form['action']." sitekey=".($form['sitekey']?substr($form['sitekey'],0,25):'NONE'));
        dbg("FW-PARSE", "inputs=".json_encode($form['inputs']));
    }

    if (!$form['sitekey']) { dbg("FW", "no sitekey"); return false; }

    echo "    ".N_ORANGE."🔥 Firewall challenge".RESET."\n";
    $solv = solveTurnstile($api, $form['sitekey'], host);
    if (isset($solv['error'])) { dbg("FW", "solver fail: ".$solv['error']); return false; }
    $tsToken = $solv['token'];
    echo "    ".N_GREEN."🔓 Solved".RESET."\n";

    $postData = $form['inputs'];
    $postData['cf-turnstile-response'] = $tsToken;

    $headers = [
        "Host: altcryp.com",
        "Origin: ".host,
        "Content-Type: application/x-www-form-urlencoded",
        "User-Agent: $ua",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language: id-ID,id;q=0.9,en;q=0.8",
        "Referer: $firewallUrl",
        "Upgrade-Insecure-Requests: 1",
        "Cache-Control: max-age=0",
    ];

    $r = req($form['action'], "POST", $postData, $headers, $cookieState);
    if ($debug) dbg("FW-POST", "code=".$r['code']." final=".$r['url']." len=".strlen($r['body']));

    if (isFirewallPage($r['body'])) {
        dbg("FW", "masih firewall setelah POST");
        return false;
    }
    return true;
}

function parseCooldown($html) {
    if (preg_match('/(?:var|let)\s+wait\s*=\s*(\d+)\s*-\s*1/i', $html, $m)) {
        $w = (int)$m[1]; return $w > 0 ? $w : 0;
    }
    if (preg_match('/Please wait\s*<b id="minute">(\d+)<\/b>\s*:\s*<b id="second">(\d+)<\/b>/i', $html, $m)) {
        return (int)$m[1]*60 + (int)$m[2];
    }
    return 0;
}
function parseButtonWait($html) {
    if (preg_match('/id="subbutt"[^>]*>\s*Please wait\s*(\d+)\s*second/i', $html, $m)) return (int)$m[1];
    return 0;
}
function parseWaitFromClaim($html) {
    if (preg_match('/(?:var|let)\s+wait\s*=\s*(\d+)\s*-\s*1/i', $html, $m)) return (int)$m[1];
    return null;
}
function parseSwalError($html) {
    if (preg_match("/Swal\.fire\('Error!',\s*'([^']+)'/", $html, $m)) return $m[1];
    if (preg_match("/Swal\.fire\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]/", $html, $m)) return $m[1].": ".$m[2];
    return null;
}
function parseSwalSuccess($html) {
    if (preg_match("/Swal\.fire\('Good job!',\s*'([^']+)'/", $html, $m)) return $m[1];
    return null;
}
function parseWaitAtLeast($msg) {
    if (preg_match('/at least\s+(\d+)\s+second/i', $msg, $m)) return (int)$m[1];
    if (preg_match('/wait\s+(\d+)\s+second/i', $msg, $m)) return (int)$m[1];
    return 0;
}
function isLoggedIn($html) { return (strpos($html, 'altcryp.com/account') !== false); }

function claimOnce(&$cookieState, $cfg, $coin, $debug = false) {
    $ua  = $cfg['user_agent'];
    $api = $cfg['apikey'];

    $url = host."/faucet/currency/".$coin;

    // ====== STEP 1: GET page, catat timestamp ======
    $tGet = microtime(true);
    $h = buildHeaders($ua, host."/");
    $r = req($url, "GET", null, $h, $cookieState);
    $html = $r['body'];
    $finalUrl = $r['url'];

    // ====== STEP 2: Firewall bypass loop (kalau perlu) ======
    $bypassCount = 0;
    while (isFirewallPage($html) && $bypassCount < FIREWALL_MAX_BYPASS) {
        $bypassCount++;
        echo "    ".N_GRAY."(firewall bypass $bypassCount/".FIREWALL_MAX_BYPASS.")".RESET."\n";
        $ok = bypassFirewall($cookieState, $cfg, $finalUrl, $html, $debug);
        if (!$ok) return ['status' => 'firewall', 'msg' => 'Firewall bypass gagal'];
        // re-GET page asli — INI BUKAN buat reset timer claim, ini setelah firewall
        // baru timer claim mulai dari sini
        $tGet = microtime(true);
        $r = req($url, "GET", null, buildHeaders($ua, host."/"), $cookieState);
        $html = $r['body'];
        $finalUrl = $r['url'];
    }
    if (isFirewallPage($html)) return ['status' => 'firewall', 'msg' => 'Firewall masih muncul'];

    if (!$html || strpos($html, "Just a moment") !== false) return ['status' => 'cf', 'msg' => 'CF challenge'];
    if (!isLoggedIn($html)) return ['status' => 'login', 'msg' => 'Cookie expired'];
    if (strpos($html, 'You Need to Complete') !== false) return ['status' => 'shortlink', 'msg' => 'Wajib shortlink'];

    $cd = parseCooldown($html);
    if ($cd > 0) return ['status' => 'cooldown', 'msg' => "Cooldown {$cd}s", 'wait' => $cd];

    if (!hasClaimForm($html)) return ['status' => 'parse', 'msg' => 'Bukan halaman claim'];

    $parsed = ['sitekey'=>null,'token'=>null,'csrf'=>null];
    if (preg_match('/data-sitekey="([^"]+)"/i', $html, $m)) $parsed['sitekey'] = $m[1];
    if (preg_match('/name="token"\s+value="([^"]+)"/i', $html, $m)) $parsed['token'] = $m[1];
    if (preg_match('/name="csrf_token_name"\s+(?:id="token"\s+)?value="([^"]+)"/i', $html, $m)) $parsed['csrf'] = $m[1];

    if (!$parsed['token']) return ['status' => 'parse', 'msg' => 'Token kosong'];

    $hasTurnstile = !empty($parsed['sitekey']);
    $btnWait = parseButtonWait($html);

    // ====== STEP 3: Solve turnstile DULU (sambil nunggu timer server) ======
    $tsToken = "";
    if ($hasTurnstile) {
        echo "    ".N_CYAN."🔒 Turnstile solving...".RESET."\n";
        $solv = solveTurnstile($api, $parsed['sitekey'], host);
        if (isset($solv['error'])) return ['status' => 'solver', 'msg' => $solv['error']];
        $tsToken = $solv['token'];
        echo "    ".N_GREEN."🔓 Solved".RESET."\n";
    } else {
        echo "    ".N_YELLOW."⚡ No turnstile".RESET."\n";
    }

    // ====== STEP 4: Tunggu sampai total elapsed dari GET >= waitBefore ======
    // TIDAK re-GET. Pakai token dari GET pertama.
    $waitTarget = max(MIN_PAGE_WAIT, $btnWait + 1);
    $elapsed = microtime(true) - $tGet;
    $remain = $waitTarget - $elapsed;
    if ($debug) dbg("WAIT", sprintf("elapsed=%.1fs target=%ds remain=%.1fs", $elapsed, $waitTarget, $remain));
    if ($remain > 0) {
        echo "    ".N_CYAN."⏳ Wait ".round($remain,1)."s".RESET."\n";
        timer(ceil($remain), "wait");
    } else {
        echo "    ".N_GREEN."⏳ Timer OK (".round($elapsed,1)."s elapsed)".RESET."\n";
    }

    // ====== STEP 5: POST verify ======
    $postData = [
        "username_fake_field" => "",
        "csrf_token_name"     => $parsed['csrf'] ?? "",
        "token"               => $parsed['token'],
    ];
    if ($hasTurnstile) {
        $postData["captcha"]               = "turnstile";
        $postData["cf-turnstile-response"] = $tsToken;
    }

    $headers = [
        "Host: altcryp.com",
        "Origin: ".host,
        "Content-Type: application/x-www-form-urlencoded",
        "User-Agent: $ua",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language: id-ID,id;q=0.9,en;q=0.8",
        "Referer: ".$url,
        "Upgrade-Insecure-Requests: 1",
        "Cache-Control: max-age=0",
    ];

    $claim = req(host."/faucet/verify/".$coin, "POST", $postData, $headers, $cookieState);
    $cHtml = $claim['body'];

    if (strpos($cHtml, "Good job!") !== false) {
        $msg = parseSwalSuccess($cHtml) ?: 'Claim sukses';
        $wait = parseWaitFromClaim($cHtml);
        return ['status' => 'ok', 'msg' => $msg, 'wait' => $wait];
    }

    $swalErr = parseSwalError($cHtml);

    if (stripos($cHtml, "sufficient funds") !== false
        || stripos($cHtml, "insufficient") !== false
        || ($swalErr && stripos($swalErr, 'funds') !== false)) {
        return ['status' => 'coin_empty', 'msg' => $swalErr ?: 'Saldo coin habis'];
    }
    if (stripos($cHtml, "Invalid") !== false) {
        return ['status' => 'invalid', 'msg' => $swalErr ?: 'Invalid captcha/token'];
    }
    if ($swalErr && stripos($swalErr, 'wait') !== false) {
        $sec = parseWaitAtLeast($swalErr);
        return ['status' => 'cooldown', 'msg' => $swalErr, 'wait' => ($sec > 0 ? $sec + 2 : 10)];
    }
    $cd2 = parseCooldown($cHtml);
    if ($cd2 > 0) return ['status' => 'cooldown', 'msg' => "POST cooldown {$cd2}s", 'wait' => $cd2];

    if (isFirewallPage($cHtml)) return ['status' => 'firewall', 'msg' => 'Firewall di POST response'];

    if ($swalErr) return ['status' => 'unknown', 'msg' => "Swal: ".$swalErr];
    return ['status' => 'unknown', 'msg' => 'Response tidak dikenali'];
}

// =================== MAIN ===================
clear();
banner();
@file_put_contents($debugLog, "\n\n===== SESSION ".date('Y-m-d H:i:s')." =====\n");

$cfg = getConfig($configFile);
$cookieState = cookiesFromStr($cfg['cookie']);

dash:
clear();
banner();
echo N_CYAN."Pilih mode:\n";
echo N_GREEN."  (1)".N_WHITE." Pilih 1 coin\n";
echo N_GREEN."  (2)".N_WHITE." Loop semua coin\n";
echo N_GREEN."  (3)".N_WHITE." Edit config\n";
echo N_GREEN."  (4)".N_WHITE." Debug mode\n";
echo N_GREEN."  (5)".N_WHITE." Lihat debug log\n";
echo N_GREEN."  (6)".N_WHITE." Exit\n";
echo N_CYAN."pilih: ".N_YELLOW;
$in = trim(fgets(STDIN));

$debug = false;
if ($in === '1') {
    echo "\n".N_CYAN."Daftar coin:\n";
    foreach ($ALL_COINS as $i => $c) {
        echo N_GREEN."(".($i+1).") ".N_WHITE.strtoupper($c)."  ";
        if (($i+1) % 6 == 0) echo "\n";
    }
    echo "\n".N_CYAN."pilih nomor: ".N_YELLOW;
    $n = (int)trim(fgets(STDIN));
    if ($n < 1 || $n > count($ALL_COINS)) { echo N_RED."invalid\n"; sleep(2); goto dash; }
    $coins = [$ALL_COINS[$n-1]]; $mode = 'single';
} elseif ($in === '2') { $coins = $ALL_COINS; $mode = 'all'; }
elseif ($in === '3') { @unlink($configFile); goto dash; }
elseif ($in === '4') { $coins = $ALL_COINS; $mode = 'all'; $debug = true; }
elseif ($in === '5') {
    if (file_exists($debugLog)) {
        clear(); echo file_get_contents($debugLog);
        echo "\n".N_CYAN."Press enter...".RESET; fgets(STDIN);
    }
    goto dash;
}
elseif ($in === '6') { exit; }
else { goto dash; }

$loop = true;
$round = 0;
$exhausted = [];

while ($loop) {
    $round++;
    echo "\n".N_MAGENTA."═══ ROUND $round ═══".RESET."\n";
    $claimCount = 0; $skipCount = 0; $emptyCount = 0;

    foreach ($coins as $coin) {
        if (in_array($coin, $exhausted)) {
            echo N_CYAN."[>] ".N_WHITE.strtoupper($coin)." ".N_GRAY."(saldo habis)".RESET."\n";
            $skipCount++; continue;
        }

        echo N_CYAN."[>] ".N_WHITE.strtoupper($coin).N_GRAY." ...".RESET."\n";

        $maxAttempts = 3; $attempt = 0; $done = false;
        while ($attempt < $maxAttempts && !$done) {
            $attempt++;
            if ($attempt > 1) echo "    ".N_GRAY."(retry $attempt/$maxAttempts)".RESET."\n";
            $res = claimOnce($cookieState, $cfg, $coin, $debug);
            $st = $res['status'];

            if ($st === 'ok') {
                echo "    ".N_GREEN."✔ OK ".N_WHITE."-> ".$res['msg'].RESET."\n";
                $claimCount++;
                $cfg['cookie'] = cookiesToStr($cookieState);
                saveConfig($configFile, $cfg);
                if (!empty($res['wait'])) timer($res['wait'], "wait");
                else sleep(3);
                $done = true;
            } elseif ($st === 'cooldown') {
                $w = $res['wait'] ?? 10;
                echo "    ".N_YELLOW."⏱ COOLDOWN ".N_WHITE."-> ".$res['msg'].RESET."\n";
                if ($w > 0) timer($w, "cool");
            } elseif ($st === 'coin_empty') {
                echo "    ".N_ORANGE."💸 SALDO HABIS ".N_WHITE."-> ".$res['msg'].RESET."\n";
                $exhausted[] = $coin; $emptyCount++; $done = true;
            } elseif ($st === 'firewall') {
                echo "    ".N_RED."🔥 FW FAIL ".N_WHITE."-> ".$res['msg'].RESET."\n";
                $skipCount++; sleep(2); $done = true;
            } elseif (in_array($st, ['parse','shortlink','invalid','solver','unknown'])) {
                echo "    ".N_YELLOW."⚠ SKIP ".N_WHITE."-> ".$res['msg'].RESET."\n";
                $skipCount++; sleep(2); $done = true;
            } elseif ($st === 'login' || $st === 'cf') {
                echo "    ".N_RED."✖ STOP ".N_WHITE."-> ".$res['msg'].RESET."\n";
                if ($st === 'login') {
                    echo N_CYAN."    Update cookie? (y/n): ".N_YELLOW;
                    $ans = strtolower(trim(fgets(STDIN)));
                    if ($ans === 'y') {
                        echo N_CYAN."    Cookie baru: ".N_YELLOW;
                        $cfg['cookie'] = trim(fgets(STDIN));
                        saveConfig($configFile, $cfg);
                        $cookieState = cookiesFromStr($cfg['cookie']);
                        echo N_GREEN."    Saved.\n"; $done = true;
                    } else { $loop = false; break 2; }
                } else { $loop = false; break 2; }
            }
        }

        if ($attempt >= $maxAttempts && !$done) {
            echo "    ".N_YELLOW."⚠ SKIP max attempts".RESET."\n";
            $skipCount++;
        }
    }

    echo N_GRAY."    Round $round → ".N_GREEN."claims:$claimCount"
        .N_GRAY." ".N_YELLOW."skip:$skipCount"
        .N_GRAY." ".N_ORANGE."empty:$emptyCount".RESET."\n";

    if ($mode === 'single') {
        echo N_CYAN."\nUlang? (y/n): ".N_YELLOW;
        $a = strtolower(trim(fgets(STDIN))); if ($a !== 'y') $loop = false;
    } else {
        echo N_CYAN."\nLanjut round? (y/n): ".N_YELLOW;
        $a = strtolower(trim(fgets(STDIN))); if ($a !== 'y') $loop = false;
    }
}

echo N_GREEN."\nDone bos. Log: $debugLog\n".RESET;
