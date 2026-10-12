<?php // index.php
/**
 * ═══════════════════════════════════════════════════════════════
 *  SOUUENGINE — TRONPICK AUTO CLAIM
 *  Live Dashboard • Menu-driven • Waryono Turnstile
 * ═══════════════════════════════════════════════════════════════
 */

error_reporting(E_ERROR | E_PARSE);
date_default_timezone_set("Asia/Karachi");
set_time_limit(0);

define("APP_NAME",   "SouuEngine");
define("APP_AUTHOR", "MoneyMaker_w");
define("APP_VER",    "v1.2");
define("APP_TAGLINE","Waryono Turnstile • Direct Claim");
define("BASE_DIR",   dirname(__FILE__));
define("MAX_LOGS",   8);

// ======================== WARYONO ========================
define("WARYONO_IN",  "https://api.waryono.my.id/in.php");
define("WARYONO_RES", "https://api.waryono.my.id/res.php");
define("WARYONO_BAL", "https://api.waryono.my.id/balance.php");

// ======================== TRONPICK ========================
define("TP_HOST", "tronpick.io");
define("TP_URL",  "https://tronpick.io");
define("TP_TURNSTILE_SITEKEY", "0x4AAAAAAAW74HiAaujGhyeV");
define("TP_HASH_KEY", "801e176b8cf63a9b84ae9d645291a416f7da3d6d31b4793a1c7b07e6e35bbefe");
define("TP_UNIT", 1000000);

// ======================== CONFIG FILES ========================
define("TP_INFO_FILE", BASE_DIR . "/information/tronpick.io.txt");
define("WARYONO_FILE", BASE_DIR . "/configs/SouuEngine/waryono-apikey.txt");
define("UA_FILE",      BASE_DIR . "/configs/SouuEngine/useragent.txt");

// ======================== TELEGRAM ========================
$GLOBALS['TG_ENABLED']   = true;
$GLOBALS['TG_BOT_TOKEN'] = '';
$GLOBALS['TG_CHAT_ID']   = '';

// ======================== API KEY ========================
if (!is_dir(dirname(WARYONO_FILE))) @mkdir(dirname(WARYONO_FILE), 0777, true);
if (file_exists(WARYONO_FILE)) {
    define("WARYONO_KEY", trim(file_get_contents(WARYONO_FILE)));
} else {
    echo "First run — enter your Waryono API key.\n";
    $k = trim(readline("Waryono API key: "));
    file_put_contents(WARYONO_FILE, $k);
    define("WARYONO_KEY", $k);
}

// ======================== USER AGENT ========================
if (file_exists(UA_FILE)) {
    define("TP_UA", trim(file_get_contents(UA_FILE)));
} else {
    $ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36";
    file_put_contents(UA_FILE, $ua);
    define("TP_UA", $ua);
}

// ======================== COLORS ========================
define("RESET", "\033[0m");
define("BOLD",  "\033[1m");
define("DIM",   "\033[2m");
define("RED",   "\033[38;5;196m");
define("GREEN", "\033[38;5;46m");
define("YELLOW","\033[38;5;226m");
define("CYAN",  "\033[38;5;51m");
define("MAGENTA","\033[38;5;213m");
define("WHITE", "\033[38;5;250m");
define("GRAY",  "\033[38;5;245m");
define("ORANGE","\033[38;5;208m");
define("PINK",  "\033[38;5;205m");
define("VIO",   "\033[38;5;141m");
define("NEWLINE","\n");

// ======================== DASHBOARD STATE ========================
$DASH = [
    'stage'        => 'IDLE',
    'status'       => 'INIT',
    'user'         => '-',
    'balance'      => '-',
    'claims'       => 0,
    'total_reward' => 0,
    'last_reward'  => '0',
    'currency'     => 'TRX',
    'fails'        => 0,
    'logs'         => [],
    'start_time'   => time(),
    'cooldown'     => 0,
    'stamina'      => null,
    'level'        => null,
    'progress'     => null,
    'solver_bal'   => null,
];

// ======================== UTIL ========================
function clr() {
    if (stripos(PHP_OS, 'WIN') === 0) @system("cls");
    else @system("clear");
}

function strip_ansi($s) { return preg_replace('/\x1b\[[0-9;]*m/', '', $s); }

function ansi_len($s) {
    $plain = strip_ansi($s);
    $chars = preg_split('//u', $plain, -1, PREG_SPLIT_NO_EMPTY);
    $len = 0;
    foreach ($chars as $ch) {
        $cp = mb_ord($ch, 'UTF-8');
        if (($cp >= 0x1F300 && $cp <= 0x1F9FF) ||
            ($cp >= 0x2600  && $cp <= 0x27BF) ||
            ($cp >= 0x2B00  && $cp <= 0x2BFF) ||
            ($cp >= 0x25A0  && $cp <= 0x25FF)) $len += 2;
        else $len += 1;
    }
    return $len;
}

function box_top() { return CYAN . "╔" . str_repeat("═", 62) . "╗" . RESET . NEWLINE; }
function box_div() { return CYAN . "╠" . str_repeat("═", 62) . "╣" . RESET . NEWLINE; }
function box_bot() { return CYAN . "╚" . str_repeat("═", 62) . "╝" . RESET . NEWLINE; }

function box_line($content, $width = 62) {
    $pad = $width - ansi_len($content) - 2;
    if ($pad < 0) $pad = 0;
    return CYAN . "║" . RESET . " " . $content . str_repeat(" ", $pad) . " " . CYAN . "║" . RESET . NEWLINE;
}

function gradient($text, $start = 51, $end = 213) {
    $chars = preg_split('//u', $text, -1, PREG_SPLIT_NO_EMPTY);
    $len = count($chars);
    if ($len <= 1) return "\033[38;5;{$start}m{$text}" . RESET;
    $out = '';
    foreach ($chars as $i => $ch) {
        $t = $i / ($len - 1);
        $c = (int) round($start + ($end - $start) * $t);
        $out .= "\033[38;5;{$c}m{$ch}";
    }
    return $out . RESET;
}

function fmt_dur($s) {
    $s = (int)$s;
    return sprintf("%02d:%02d:%02d", $s/3600, ($s%3600)/60, $s%60);
}

function fmt_trx($raw) {
    if ($raw === null) return '-';
    return number_format((float)$raw / TP_UNIT, 6, '.', '');
}

function short_str($s, $max = 30) {
    if (mb_strlen($s) > $max) return mb_substr($s, 0, $max - 14) . "..." . mb_substr($s, -10);
    return $s;
}

// ======================== DASHBOARD ========================
function dash_push($icon, $label, $msg, $color = WHITE) {
    global $DASH;
    $t = date('H:i:s');
    $line = GRAY . "[" . $t . "]" . RESET . " " . MAGENTA . $icon . RESET . " " . CYAN . $label . RESET . " " . $color . $msg . RESET;
    $DASH['logs'][] = $line;
    if (count($DASH['logs']) > MAX_LOGS) array_shift($DASH['logs']);
}

function dash_render() {
    global $DASH;
    clr();

    $elapsed = time() - $DASH['start_time'];
    $st = strtoupper($DASH['status']);
    $sc = YELLOW;
    if (strpos($st, 'OK') !== false || strpos($st, 'SUCCESS') !== false || strpos($st, 'FINISH') !== false) $sc = GREEN;
    elseif (strpos($st, 'FAIL') !== false || strpos($st, 'ERROR') !== false || strpos($st, 'EXPIRED') !== false) $sc = RED;
    elseif (strpos($st, 'WAIT') !== false || strpos($st, 'COOLD') !== false || strpos($st, 'SKIP') !== false) $sc = ORANGE;

    $out  = box_top();
    $out .= box_line(gradient("SOUUENGINE :: TRONPICK AUTO CLAIM"));
    $out .= box_line(DIM . "────── By " . APP_AUTHOR . " • " . APP_VER . " ──────" . RESET);
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "SESSION" . RESET);
    $out .= box_line(CYAN . "├─ User    : " . RESET . WHITE . $DASH['user'] . RESET);
    $out .= box_line(CYAN . "├─ Stage   : " . RESET . MAGENTA . strtoupper($DASH['stage']) . RESET);
    $out .= box_line(CYAN . "├─ Status  : " . RESET . $sc . $DASH['status'] . RESET);
    if ($DASH['cooldown'] > 0) {
        $m = floor($DASH['cooldown'] / 60); $s = $DASH['cooldown'] % 60;
        $out .= box_line(CYAN . "└─ Next    : " . RESET . YELLOW . sprintf("%02d:%02d", $m, $s) . RESET);
    } else {
        $out .= box_line(CYAN . "└─ Next    : " . RESET . DIM . "-" . RESET);
    }
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "INCOME" . RESET);
    $out .= box_line(CYAN . "├─ Claims  : " . RESET . GREEN . $DASH['claims'] . RESET);
    $out .= box_line(CYAN . "├─ Total   : " . RESET . GREEN . "+" . number_format($DASH['total_reward'], 6, '.', '') . " " . $DASH['currency'] . RESET);
    $out .= box_line(CYAN . "├─ Last    : " . RESET . GREEN . "+" . $DASH['last_reward'] . " " . $DASH['currency'] . RESET);
    $out .= box_line(CYAN . "└─ Balance : " . RESET . CYAN . $DASH['balance'] . " " . $DASH['currency'] . RESET);
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "SYSTEM" . RESET);
    $out .= box_line(CYAN . "├─ Fails   : " . RESET . RED . $DASH['fails'] . RESET);
    if ($DASH['level'] !== null) {
        $lv = $DASH['level'] . ($DASH['progress'] !== null ? " ({$DASH['progress']}%)" : "");
        $out .= box_line(CYAN . "├─ Level   : " . RESET . YELLOW . $lv . RESET);
    }
    if ($DASH['stamina'] !== null) {
        $stc = $DASH['stamina'] > 0 ? GREEN : RED;
        $out .= box_line(CYAN . "├─ Stamina : " . RESET . $stc . $DASH['stamina'] . RESET);
    }
    if ($DASH['solver_bal'] !== null) {
        $out .= box_line(CYAN . "├─ Solver  : " . RESET . GREEN . "Waryono (" . $DASH['solver_bal'] . " tk)" . RESET);
    } else {
        $out .= box_line(CYAN . "├─ Solver  : " . RESET . GREEN . "Waryono (Turnstile)" . RESET);
    }
    $out .= box_line(CYAN . "└─ Runtime : " . RESET . YELLOW . fmt_dur($elapsed) . RESET);
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "LIVE LOG" . RESET);
    for ($i = 0; $i < MAX_LOGS; $i++) {
        if (isset($DASH['logs'][$i])) $out .= box_line($DASH['logs'][$i]);
        else $out .= CYAN . "║" . RESET . str_repeat(" ", 62) . CYAN . "║" . RESET . NEWLINE;
    }
    $out .= box_bot();
    $out .= NEWLINE . "   " . gradient("SOUUENGINE RUNNING", 46, 226) . " " . DIM . "•" . RESET . " " . CYAN . date('H:i:s') . RESET . NEWLINE;
    $out .= "   " . DIM . "Powered by " . RESET . MAGENTA . APP_AUTHOR . RESET . DIM . " • " . RESET . CYAN . APP_NAME . " " . APP_VER . RESET . NEWLINE;
    $out .= "   " . DIM . APP_TAGLINE . RESET . NEWLINE . NEWLINE;

    echo $out;
    flush();
}

function dash_log($icon, $label, $msg, $color = WHITE) {
    dash_push($icon, $label, $msg, $color);
    dash_render();
}

function dash_set($key, $val) { global $DASH; $DASH[$key] = $val; }

function dash_timer($seconds, $label = "Cooldown") {
    global $DASH;
    if (!$seconds || !is_numeric($seconds)) $seconds = 5;
    $end = time() + $seconds;
    while (true) {
        $left = $end - time();
        if ($left < 1) break;
        $DASH['cooldown'] = $left;
        $DASH['status'] = sprintf("%s %02d:%02d", $label, floor($left/60), $left % 60);
        dash_render();
        sleep(1);
    }
    $DASH['cooldown'] = 0;
    dash_render();
}

// ======================== TELEGRAM ========================
function tg_notify($text, $botToken = null, $chatId = null) {
    if (!$GLOBALS['TG_ENABLED']) return false;
    $botToken = $botToken ?: $GLOBALS['TG_BOT_TOKEN'];
    $chatId   = $chatId   ?: $GLOBALS['TG_CHAT_ID'];
    if (empty($botToken) || empty($chatId)) return false;
    $ch = curl_init("https://api.telegram.org/bot{$botToken}/sendMessage");
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query([
            'chat_id'=>$chatId, 'text'=>$text, 'parse_mode'=>'HTML',
            'disable_web_page_preview'=>'true',
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_SSL_VERIFYPEER => false,
    ]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return $code === 200;
}

// ======================== HTTP ========================
function Run($url, $head = 0, $post = 0, $proxy = 0, $returnType = 2, $name = "") {
    $host = parse_url($url, PHP_URL_HOST);
    $folder = BASE_DIR . "/configs/{$host}-config";
    if (!is_dir($folder)) @mkdir($folder, 0777, true);

    if (!empty($proxy)) {
        $pf = trim($proxy);
        if (!preg_match('#^https?://#i', $pf)) $pf = "http://" . $pf;
        $parts = parse_url($pf);
        $proxyPart = preg_replace('/[^a-zA-Z0-9._-]/', '_', $parts['host'] ?? $pf);
        $cookieFile = $folder . "/" . (!empty($name) ? "{$name}-{$proxyPart}-cookie.txt" : "{$proxyPart}-cookie.txt");
    } else {
        $cookieFile = $folder . "/" . (!empty($name) ? "{$name}-cookie.txt" : "cookie.txt");
    }

    $response=false; $info=[]; $curlErr='';
    $maxRetries=30; $retryDelay=1; $attempt=0;
    do {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_COOKIEJAR, $cookieFile);
        curl_setopt($ch, CURLOPT_COOKIEFILE, $cookieFile);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 30);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);
        curl_setopt($ch, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2TLS);
        if (!empty($proxy)) {
            $pws = preg_match('#^https?://#i', $proxy) ? $proxy : "http://{$proxy}";
            $parts = parse_url($pws);
            if (!empty($parts['host']) && !empty($parts['port'])) {
                curl_setopt($ch, CURLOPT_PROXY, $parts['host'] . ":" . $parts['port']);
                if (!empty($parts['user']) && !empty($parts['pass']))
                    curl_setopt($ch, CURLOPT_PROXYUSERPWD, $parts['user'] . ":" . $parts['pass']);
                curl_setopt($ch, CURLOPT_PROXYTYPE, CURLPROXY_HTTP);
            }
        }
        if ($post) { curl_setopt($ch, CURLOPT_POST, true); curl_setopt($ch, CURLOPT_POSTFIELDS, $post); }
        if ($head && is_array($head)) curl_setopt($ch, CURLOPT_HTTPHEADER, $head);
        curl_setopt($ch, CURLOPT_HEADER, true);
        $response = curl_exec($ch);
        $info = curl_getinfo($ch);
        $curlErr = curl_error($ch);
        $hs = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $responseHeader = substr($response, 0, $hs);
        $responseBody   = substr($response, $hs);
        if ($response !== false && $info['http_code'] != 0) break;
        $attempt++;
        if ($attempt < $maxRetries) sleep($retryDelay);
    } while ($attempt < $maxRetries);

    if ($response === false || $info['http_code'] == 0)
        return ["body"=>"Request failed: $curlErr", "info"=>$info];
    if ($returnType == 1) return $responseBody;
    if ($returnType == 2) return ["body"=>$responseBody, "info"=>$info];
    return ["header"=>$responseHeader, "body"=>$responseBody, "info"=>$info];
}

// ======================== COOKIE ========================
function getCookieString($host, $email) {
    $folder = BASE_DIR . "/configs/{$host}-config";
    $cookieFile   = "$folder/$email-cookie.txt";
    $cfCookieFile = "$folder/cf_cookie.txt";
    $cookies = [];
    if (is_file($cookieFile)) {
        foreach (file($cookieFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            $line = trim($line);
            if ($line === '') continue;
            if ($line[0] === '#') {
                if (strpos($line, '#HttpOnly_') === 0) $line = substr($line, 10);
                else continue;
            }
            $parts = preg_split('/\s+/', $line);
            if (count($parts) < 7) continue;
            [$domain,$flag,$path,$secure,$exp,$name,$value] = $parts;
            if ($domain !== $host && strpos($domain,'.'.$host)===false && strpos($host,ltrim($domain,'.'))===false) continue;
            if ($exp != 0 && $exp < time()) continue;
            $cookies[$name] = ['value'=>$value,'path'=>$path];
        }
    }
    if (is_file($cfCookieFile)) {
        foreach (file($cfCookieFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#') continue;
            $parts = preg_split('/\s+/', $line, 2);
            if (count($parts) == 2) $cookies[trim($parts[0])] = ['value'=>trim($parts[1]),'path'=>'/'];
        }
    }
    $out = '';
    foreach ($cookies as $n => $d) $out .= "$n={$d['value']}; ";
    return rtrim($out, '; ');
}

function getCookieValue($host, $email, $name) {
    $folder = BASE_DIR . "/configs/{$host}-config";
    $cookieFile = "$folder/$email-cookie.txt";
    if (!is_file($cookieFile)) return '';
    foreach (file($cookieFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '') continue;
        if ($line[0] === '#') {
            if (strpos($line, '#HttpOnly_') === 0) $line = substr($line, 10);
            else continue;
        }
        $parts = preg_split('/\s+/', $line);
        if (count($parts) < 7) continue;
        if ($parts[5] === $name) return $parts[6];
    }
    return '';
}

function getRequestHeaders($host, $email = null) {
    $ck = getCookieString($host, $email);
    $h = [
        "accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language: en-GB,en-US;q=0.9,en;q=0.8",
        "User-Agent: ".TP_UA,
    ];
    if ($ck) $h[] = "cookie: " . $ck;
    return $h;
}

function getFormHeaders($host, $email = null) {
    $ck = getCookieString($host, $email);
    return [
        "User-Agent: ".TP_UA,
        "Referer: https://$host/faucet.php",
        "Origin: https://$host",
        "Accept: */*",
        "X-Requested-With: XMLHttpRequest",
        "content-type: application/x-www-form-urlencoded; charset=UTF-8",
        "cookie: " . $ck,
    ];
}

// ======================== HASH ========================
function generate_hash($key, $x = null, $y = null) {
    if ($x === null) $x = rand(40, 260);
    if ($y === null) $y = rand(100, 380);
    $timestamp = time();
    $data = $x . ':' . $y . ':' . $timestamp;
    $encrypted = '';
    $klen = strlen($key);
    for ($i = 0; $i < strlen($data); $i++) {
        $encrypted .= chr(ord($data[$i]) ^ ord($key[$i % $klen]));
    }
    return base64_encode($encrypted);
}

// ======================== WARYONO ========================
function waryono_balance() {
    $r = Run(WARYONO_BAL . "?apikey=" . urlencode(WARYONO_KEY), null, null, null, 2);
    $j = json_decode($r['body'], true);
    return $j['balance'] ?? null;
}

function waryono_solve_turnstile($pageurl, $sitekey, $action = "", $cdata = "") {
    $body = json_encode([
        "apikey"  => WARYONO_KEY,
        "methods" => "turnstile",
        "domain"  => $pageurl,
        "sitekey" => $sitekey,
        "action"  => $action,
        "cdata"   => $cdata,
        "json"    => 1,
    ]);

    $t0 = microtime(true);
    $r = Run(WARYONO_IN, ["Content-Type: application/json"], $body, null, 2);
    $j = json_decode($r['body'], true);

    if (empty($j['request']) || (int)($j['status'] ?? 0) !== 1) {
        return ["success" => false, "error" => $j['request'] ?? "submit failed"];
    }

    $id = $j['request'];
    for ($i = 1; $i <= 100; $i++) {
        sleep(3);
        $poll = Run(WARYONO_RES . "?apikey=" . urlencode(WARYONO_KEY) . "&id=" . urlencode($id) . "&action=get&json=1", null, null, null, 2);
        $pj = json_decode($poll['body'], true);
        $req = $pj['request'] ?? '';
        if ((int)($pj['status'] ?? 0) === 1 && $req && $req !== 'CAPCHA_NOT_READY') {
            return ["success" => true, "token" => $req, "elapsed" => round(microtime(true) - $t0, 2)];
        }
        if ($req === 'CAPCHA_NOT_READY') continue;
        if (stripos($req, 'ERROR') !== false) return ["success" => false, "error" => $req];
    }
    return ["success" => false, "error" => "timeout"];
}

// ======================== PARSER ========================
function parseTronPickStatus($html) {
    $out = [
        'level'=>null,'progress_pct'=>null,'stamina_remaining'=>null,
        'main_balance'=>null,'commission_balance'=>null,
        'cooldown'=>0,'can_claim'=>true,'reason'=>null
    ];
    if (preg_match('/Your level is\s*<b>([^<]+)<\/b>/i', $html, $m)) $out['level'] = trim($m[1]);
    if (preg_match('/id="wagering_progress"[^>]*aria-valuenow="(\d+)"/i', $html, $m)) $out['progress_pct'] = (int)$m[1];
    elseif (preg_match('/id="wagering_progress"[^>]*style="width:\s*(\d+)%/i', $html, $m)) $out['progress_pct'] = (int)$m[1];

    if (preg_match('/faucet_claims_remaining[^>]*>\s*(\d+)\s*</i', $html, $m)) {
        $out['stamina_remaining'] = (int)$m[1];
    } elseif (preg_match('/You have\s*<b>(\d+)<\/b>\s*claims/i', $html, $m)) {
        $out['stamina_remaining'] = (int)$m[1];
    } elseif (preg_match('/(\d+)\s*\/\s*(\d+)\s*claims/i', $html, $m)) {
        $out['stamina_remaining'] = (int)$m[1];
    }

    if (preg_match('/id="dd_main_balance"[^>]*>\s*([\d,.]+)\s*</i', $html, $m)) {
        $out['main_balance'] = (float) str_replace(',', '', trim($m[1]));
    }
    if (preg_match('/id="dd_commission_balance"[^>]*>\s*([\d,.]+)\s*</i', $html, $m)) {
        $out['commission_balance'] = (float) str_replace(',', '', trim($m[1]));
    }

    if (preg_match('/show_countdown_clock\((\d+)\)/i', $html, $m)) {
        $out['cooldown'] = (int)$m[1];
        if ($out['cooldown'] > 0) {
            $out['can_claim'] = false;
            $out['reason'] = "Cooldown aktif ({$out['cooldown']}s)";
        }
    }

    if (!preg_match('/id="process_claim_hourly_faucet"/i', $html)) {
        $out['can_claim'] = false;
        $out['reason'] = $out['reason'] ?? "Form claim gak ada di halaman";
    }

    if (stripos($html, 'come back later') !== false) {
        $out['can_claim'] = false;
        $out['reason'] = "Server bilang Come Back Later";
    }

    if ($out['stamina_remaining'] !== null && $out['stamina_remaining'] <= 0) {
        $out['can_claim'] = false;
        $out['reason'] = "Stamina 0";
    }

    return $out;
}

function extractProcessJson($body) {
    $candidates = [];
    if (preg_match_all('/\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}/s', $body, $mm)) {
        foreach ($mm[0] as $chunk) {
            $d = json_decode($chunk, true);
            if (is_array($d) && !empty($d)) $candidates[] = $d;
        }
    }
    if (empty($candidates)) return null;
    foreach ($candidates as $c) {
        if (($c['ret'] ?? null) == 1) {
            $mes = strtolower($c['mes'] ?? $c['message'] ?? '');
            if (isset($c['balance']) || isset($c['new_balance'])
                || strpos($mes, 'claim') !== false
                || strpos($mes, 'success') !== false
                || strpos($mes, 'received') !== false) return $c;
        }
    }
    foreach ($candidates as $c) if (($c['ret'] ?? null) == 1) return $c;
    foreach ($candidates as $c) if (!empty($c['success'])) return $c;
    foreach ($candidates as $c) {
        $mes = strtolower($c['mes'] ?? $c['message'] ?? '');
        if (strpos($mes, 'something went wrong') === false) return $c;
    }
    return $candidates[0];
}

// ======================== CAPTCHA ========================
function build_turnstile_payload($pageurl, &$solverTime, &$err) {
    $res = waryono_solve_turnstile($pageurl, TP_TURNSTILE_SITEKEY);
    if (!$res['success']) {
        $err = $res['error'] ?? 'turnstile solve failed';
        return null;
    }
    $solverTime = $res['elapsed'] ?? null;
    return [
        'captcha_type'         => 3,
        'c_captcha_response'   => $res['token'],
    ];
}

// ======================== CHECK FAUCET ========================
function tp_check($email, $password, $proxy, $accountId) {
    dash_set('stage', 'CHECK');
    dash_set('status', "Check — GET /faucet.php");
    dash_set('user', short_str($email, 24));
    dash_render();

    $url = TP_URL . "/faucet.php";
    $response = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
    $html = $response['body'] ?? '';
    $code = $response['info']['http_code'] ?? 0;

    if ($code == 302) {
        dash_log("[!]", "CHECK ", "not logged in → login", YELLOW);
        if (!tp_login($email, $password, $proxy, $accountId)) {
            dash_log("[X]", "CHECK ", "login failed", RED);
            return null;
        }
        $response = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
        $html = $response['body'] ?? '';
        $code = $response['info']['http_code'] ?? 0;
    }

    if ($code != 200 || $html === '') {
        dash_log("[X]", "CHECK ", "HTTP {$code}", RED);
        return null;
    }

    $tp = parseTronPickStatus($html);

    dash_log("[>]", "CHECK ", "─── faucet status ───", CYAN);
    dash_log("[i]", "USER  ", $email, WHITE);
    dash_log("[i]", "LEVEL ", ($tp['level'] ?? '-') . ($tp['progress_pct'] !== null ? " ({$tp['progress_pct']}%)" : ''), YELLOW);
    dash_log("[i]", "BAL   ", ($tp['main_balance'] !== null ? number_format($tp['main_balance'], 6, '.', '') : '-') . " TRX", GREEN);
    if ($tp['stamina_remaining'] !== null) {
        $stc = $tp['stamina_remaining'] > 0 ? GREEN : RED;
        dash_log("[i]", "STAM  ", $tp['stamina_remaining'] . " claim(s) tersisa", $stc);
    }

    if ($tp['can_claim']) {
        dash_log("[OK]", "CHECK ", "✓ FAUCET BISA DI-CLAIM", GREEN);
    } else {
        dash_log("[!]", "CHECK ", "✗ GA BISA: " . ($tp['reason'] ?? 'unknown'), RED);
        if ($tp['cooldown'] > 0) {
            $m = floor($tp['cooldown'] / 60);
            $s = $tp['cooldown'] % 60;
            dash_log("[i]", "COOLDN", "tunggu {$m}m {$s}s lagi", ORANGE);
        }
    }

    dash_set('balance', $tp['main_balance'] !== null ? number_format($tp['main_balance'], 6, '.', '') : '-');
    dash_set('level', $tp['level']);
    dash_set('progress', $tp['progress_pct']);
    dash_set('stamina', $tp['stamina_remaining']);

    return $tp;
}

// ======================== LOGIN ========================
function tp_login($email, $password, $proxy, $accountId) {
    $url = TP_URL . "/login.php";
    $response = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
    if (($response['info']['http_code'] ?? 0) == 302) return true;

    $csrf = getCookieValue(TP_HOST, $email, 'csrf_cookie_name');
    if (!$csrf && preg_match('/csrf_cookie_name=([^;]+)/i', $response['header'] ?? '', $m)) $csrf = $m[1];

    dash_set('status', 'Login - solving captcha');
    dash_log("[>]", "SOLVE ", "login turnstile...", CYAN);
    $solverTime = null; $err = '';
    $cap = build_turnstile_payload($url, $solverTime, $err);
    if (!$cap) return false;
    dash_log("[OK]", "TOKEN ", "received" . ($solverTime ? " ({$solverTime}s)" : ""), GREEN);

    $data = array_merge($cap, [
        'action'         => 'login',
        'email'          => $email,
        'password'       => $password,
        'twofa'          => '',
        'csrf_test_name' => $csrf,
    ]);

    $payload = http_build_query($data);
    $post = Run(TP_URL . "/process.php", getFormHeaders(TP_HOST, $email), $payload, $proxy, 3, $email);
    $body = $post['body'] ?? '';
    return strpos($body, '"ret":1') !== false || strpos($body, '"success":true') !== false;
}

// ======================== CLAIM ========================
function tp_claim($email, $password, $proxy, $accountId, $counters = [], $tg = []) {
    global $DASH;

    $state = [
        'status' => 'failed',
        'reward' => null,
        'new_balance' => null,
        'cooldown' => 0,
        'success_count'=>$counters['success']??0,
        'fail_count'=>$counters['fail']??0,
        'total_count'=>$counters['total']??0,
        'tg_token'=>$tg['token']??null,
        'tg_chat'=>$tg['chat']??null,
    ];

    dash_set('stage', 'FAUCET');
    dash_set('status', 'Faucet - GET /faucet.php');
    dash_render();

    $url = TP_URL . "/faucet.php";
    $response = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
    $html = $response['body'] ?? '';
    $code = $response['info']['http_code'] ?? 0;

    if ($code == 302) {
        dash_log("[!]", "LOGIN ", "redirect → relogin", YELLOW);
        if (!tp_login($email, $password, $proxy, $accountId)) {
            $state['message'] = 'login failed';
            logAccountBlock($accountId, $email, $state);
            return ['success'=>false,'timer'=>5];
        }
        $response = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
        $html = $response['body'] ?? '';
        $code = $response['info']['http_code'] ?? 0;
    }

    if ($code != 200 || $html === '') {
        dash_log("[X]", "FAUCET", "HTTP {$code}", RED);
        $state['message'] = "faucet HTTP {$code}";
        logAccountBlock($accountId, $email, $state);
        return ['success'=>false,'timer'=>30];
    }

    $tp = parseTronPickStatus($html);
    dash_set('balance', $tp['main_balance'] !== null ? number_format((float)$tp['main_balance'], 6, '.', '') : '-');
    dash_set('level', $tp['level']);
    dash_set('progress', $tp['progress_pct']);
    dash_set('stamina', $tp['stamina_remaining']);

    if ($tp['stamina_remaining'] !== null && $tp['stamina_remaining'] <= 0) {
        dash_log("[!]", "FAUCET", "stamina 0 — skip", YELLOW);
        $state['message'] = 'stamina 0';
        logAccountBlock($accountId, $email, $state);
        return ['success'=>false,'timer'=>3600];
    }

    if ($tp['cooldown'] > 0) {
        dash_log("[!]", "COOLDN", "cooldown {$tp['cooldown']}s", ORANGE);
        $state['cooldown'] = $tp['cooldown'];
        logAccountBlock($accountId, $email, $state);
        return ['success'=>false,'timer'=>$tp['cooldown']];
    }

    $csrf = getCookieValue(TP_HOST, $email, 'csrf_cookie_name');
    if (!$csrf && preg_match('/csrf_cookie_name=([^;]+)/i', $response['header'] ?? '', $m)) $csrf = $m[1];

    dash_log("[>]", "SOLVE ", "turnstile solving...", CYAN);
    $solverTime = null; $err = '';
    $cap = build_turnstile_payload($url, $solverTime, $err);
    if (!$cap) {
        dash_log("[X]", "SOLVE ", "failed: {$err}", RED);
        $state['message'] = "captcha: $err";
        logAccountBlock($accountId, $email, $state);
        return ['success'=>false,'timer'=>0];
    }
    dash_log("[OK]", "TOKEN ", "received" . ($solverTime ? " ({$solverTime}s)" : ""), GREEN);

    $hash = generate_hash(TP_HASH_KEY);

    $data = [
        'action'               => 'claim_hourly_faucet',
        'hash'                 => $hash,
        'captcha_type'         => 3,
        'g-recaptcha-response' => '',
        '_iconcaptcha-token'   => '',
        'ic-rq'                => '',
        'ic-wid'               => '',
        'ic-cid'               => '',
        'ic-hp'                => '',
        'h-captcha-response'   => '',
        'c_captcha_response'   => $cap['c_captcha_response'],
        'pcaptcha_token'       => '',
        'ft'                   => getCookieValue(TP_HOST, $email, '_ft'),
        'csrf_test_name'       => $csrf,
    ];

    dash_set('status', 'Faucet - POST /process.php');
    dash_render();

    $payload = http_build_query($data);
    $post = Run(TP_URL . "/process.php", getFormHeaders(TP_HOST, $email), $payload, $proxy, 3, $email);
    $body = $post['body'] ?? '';

    $js = extractProcessJson($body);

    if ($js) {
        $jsStr = json_encode($js);
        $isRealSuccess = (($js['ret'] ?? null) == 1)
            && stripos($jsStr, 'error') === false
            && stripos($jsStr, 'invalid') === false;

        if ($isRealSuccess) {
            $state['status'] = 'success';

            $rawReward  = $js['reward']  ?? $js['amount'] ?? $js['payout'] ?? 0;
            $rawBalance = $js['balance'] ?? $js['new_balance'] ?? null;

            $state['reward']      = number_format((float)$rawReward / TP_UNIT, 6, '.', '');
            $state['new_balance'] = $rawBalance !== null ? number_format((float)$rawBalance / TP_UNIT, 6, '.', '') : null;
            $state['message']     = $js['mes'] ?? $js['message'] ?? 'claimed';

            $DASH['claims']++;
            $DASH['total_reward'] += (float)$state['reward'];
            $DASH['last_reward'] = $state['reward'];
            if ($state['new_balance'] !== null) {
                $DASH['balance'] = $state['new_balance'];
            }
            dash_log("[OK]", "FAUCET", "+{$state['reward']} TRX | Balance {$DASH['balance']}", GREEN);
        } else {
            $state['status'] = 'failed';
            $state['message'] = $js['mes'] ?? $js['message'] ?? 'rejected';
            dash_log("[X]", "FAUCET", $state['message'], RED);
        }
    } else {
        $state['status'] = 'failed';
        $state['message'] = substr(strip_tags($body), 0, 200);
        dash_log("[X]", "FAUCET", "no json: " . substr($body, 0, 60), RED);
    }

    if ($state['status'] === 'success') {
        $after = Run($url, getRequestHeaders(TP_HOST, $email), null, $proxy, 3, $email);
        $tp2 = parseTronPickStatus($after['body'] ?? '');
        if ($tp2['main_balance'] !== null) {
            $DASH['balance'] = number_format((float)$tp2['main_balance'], 6, '.', '');
            dash_set('balance', $DASH['balance']);
        }
        if ($tp2['stamina_remaining'] !== null) dash_set('stamina', $tp2['stamina_remaining']);
        if ($tp2['cooldown'] > 0) $state['cooldown'] = $tp2['cooldown'];
    }

    logAccountBlock($accountId, $email, $state);
    return ['success'=>$state['status']==='success','timer'=>$state['cooldown']??0];
}

// ======================== LOG BLOCK (telegram only) ========================
function logAccountBlock($accountId, $email, array $state) {
    if (!$GLOBALS['TG_ENABLED']) return;
    $status = $state['status'] ?? 'unknown';
    $t  = "🎯 <b>" . TP_HOST . "</b>  <code>#" . $accountId . "</code>\n";
    $t .= "👤 <code>" . htmlspecialchars($email) . "</code>\n";
    if (!empty($state['reward'])) $t .= "🎁 Reward: <b>{$state['reward']}</b>\n";
    if (!empty($state['new_balance'])) $t .= "💵 New: <b>" . $state['new_balance'] . "</b>\n";
    if (!empty($state['cooldown'])) $t .= "⏱ Cooldown: <b>{$state['cooldown']}s</b>\n";
    $t .= "📊 <b>" . strtoupper($status) . "</b>  (" . ($state['success_count'] ?? 0) . "/" . ($state['total_count'] ?? 0) . ")\n";
    if (!empty($state['message'])) $t .= "📝 <i>" . htmlspecialchars(substr($state['message'], 0, 200)) . "</i>\n";
    tg_notify($t, $state['tg_token'] ?? null, $state['tg_chat'] ?? null);
}

// ======================== ACCOUNT FILE ========================
function ensureInfoFile() {
    $f = TP_INFO_FILE;
    if (!is_dir(dirname($f))) @mkdir(dirname($f), 0777, true);
    if (!file_exists($f)) {
        file_put_contents($f, "# " . APP_NAME . " TronPick accounts\n# format: email|password|proxy|tg_bot_token|tg_chat_id\n");
    }
}
function loadTpAccounts() {
    ensureInfoFile();
    $out = [];
    foreach (file(TP_INFO_FILE, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        $p = array_map('trim', explode('|', $line));
        if (empty($p[0])) continue;
        $out[] = ['email'=>$p[0],'password'=>$p[1]??'','proxy'=>$p[2]??null,'tg_token'=>$p[3]??null,'tg_chat'=>$p[4]??null];
    }
    return $out;
}
function saveAccounts(array $accounts) {
    $lines = ["# " . APP_NAME . " TronPick accounts", "# format: email|password|proxy|tg_bot_token|tg_chat_id"];
    foreach ($accounts as $a) {
        $lines[] = implode('|', [$a['email']??'',$a['password']??'',$a['proxy']??'',$a['tg_token']??'',$a['tg_chat']??'']);
    }
    file_put_contents(TP_INFO_FILE, implode(NEWLINE, $lines) . NEWLINE);
}

// ======================== MENU ========================
function show_main_menu($accounts, $bal) {
    clr();
    $out  = box_top();
    $out .= box_line(gradient("SOUUENGINE :: TRONPICK AUTO CLAIM"));
    $out .= box_line(DIM . "────── By " . APP_AUTHOR . " • " . APP_VER . " ──────" . RESET);
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "INFO" . RESET);
    $out .= box_line(CYAN . "├─ Accounts : " . RESET . WHITE . count($accounts) . RESET);
    $out .= box_line(CYAN . "├─ Telegram : " . RESET . ($GLOBALS['TG_ENABLED'] ? GREEN . "ON" : RED . "OFF") . RESET);
    $out .= box_line(CYAN . "├─ Solver   : " . RESET . GREEN . "Waryono (Turnstile)" . RESET);
    if ($bal !== null) {
        $out .= box_line(CYAN . "└─ Balance  : " . RESET . GREEN . $bal . " token" . RESET);
    } else {
        $out .= box_line(CYAN . "└─ Balance  : " . RESET . RED . "unavailable" . RESET);
    }
    $out .= box_div();

    $out .= box_line(MAGENTA . BOLD . "MENU" . RESET);
    $out .= box_line("  " . CYAN . "1." . RESET . " " . WHITE . "Add account" . RESET);
    $out .= box_line("  " . CYAN . "2." . RESET . " " . WHITE . "List accounts" . RESET);
    $out .= box_line("  " . CYAN . "3." . RESET . " " . WHITE . "Delete account" . RESET);
    $out .= box_line("  " . GREEN . "4." . RESET . " " . WHITE . "Start claiming" . RESET);
    $out .= box_line("  " . YELLOW . "5." . RESET . " " . WHITE . "Check faucet status (all)" . RESET);
    $out .= box_line("  " . ORANGE . "0." . RESET . " " . WHITE . "Exit" . RESET);
    $out .= box_bot();

    $out .= NEWLINE . "   " . gradient("SOUUENGINE", 46, 226) . " " . DIM . "•" . RESET . " " . CYAN . date('H:i:s') . RESET . NEWLINE;
    $out .= "   " . DIM . "Powered by " . RESET . MAGENTA . APP_AUTHOR . RESET . DIM . " • " . RESET . CYAN . APP_NAME . " " . APP_VER . RESET . NEWLINE;
    $out .= "   " . DIM . APP_TAGLINE . RESET . NEWLINE . NEWLINE;

    echo $out;
}

function prompt_main() {
    echo MAGENTA . APP_NAME . RESET . " " . CYAN . "»" . RESET . " " . YELLOW . "Pilih" . RESET . " " . WHITE . "[" . CYAN . "1/2/3/4/5/0" . WHITE . "]" . RESET . " " . MAGENTA . ">" . RESET . " ";
    return trim(fgets(STDIN));
}

function prompt_input($label) {
    echo NEWLINE . " " . MAGENTA . APP_NAME . RESET . " " . CYAN . "»" . RESET . " " . YELLOW . $label . RESET . " " . MAGENTA . ">" . RESET . " ";
    return trim(fgets(STDIN));
}

function prompt_enter($msg = "ENTER untuk lanjut...") {
    echo NEWLINE . " " . GRAY . $msg . RESET;
    fgets(STDIN);
}

// ======================== UI HANDLERS ========================
function addAccountUI() {
    clr();
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: ADD ACCOUNT"));
    echo box_line(DIM . "────── By " . APP_AUTHOR . " • " . APP_VER . " ──────" . RESET);
    echo box_bot();

    $email = prompt_input("Email");
    if ($email === '') { echo NEWLINE . " " . RED . "[!]" . RESET . " " . WHITE . "Cancelled" . RESET . NEWLINE; sleep(1); return; }
    $password = prompt_input("Password");
    $proxy    = prompt_input("Proxy (Enter skip)");
    $tgToken  = prompt_input("TG bot token (Enter skip)");
    $tgChat   = prompt_input("TG chat id (Enter skip)");

    $accounts = loadTpAccounts();
    $replaced = false;
    foreach ($accounts as $i => $a) {
        if (strcasecmp($a['email'], $email) === 0) {
            $accounts[$i] = ['email'=>$email,'password'=>$password,'proxy'=>$proxy?:null,'tg_token'=>$tgToken?:null,'tg_chat'=>$tgChat?:null];
            $replaced = true; break;
        }
    }
    if (!$replaced) {
        $accounts[] = ['email'=>$email,'password'=>$password,'proxy'=>$proxy?:null,'tg_token'=>$tgToken?:null,'tg_chat'=>$tgChat?:null];
    }
    saveAccounts($accounts);
    echo NEWLINE . " " . GREEN . "[OK]" . RESET . " " . WHITE . "Saved. Total: " . count($accounts) . RESET . NEWLINE;
    sleep(1);
}

function listAccountsUI() {
    clr();
    $accounts = loadTpAccounts();
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: LIST ACCOUNTS"));
    echo box_line(DIM . "────── By " . APP_AUTHOR . " • " . APP_VER . " ──────" . RESET);
    echo box_div();
    echo box_line(MAGENTA . BOLD . "SAVED (" . count($accounts) . ")" . RESET);
    if (empty($accounts)) {
        echo box_line(GRAY . "(none yet)" . RESET);
    } else {
        foreach ($accounts as $i => $a) {
            $px = $a['proxy'] ? GRAY . " proxy=" . short_str($a['proxy'], 20) : GRAY . " no-proxy";
            $tg = $a['tg_token'] ? GREEN . " tg=on" : GRAY . " tg=off";
            echo box_line(CYAN . "[$i] " . RESET . WHITE . short_str($a['email'], 26) . $px . $tg . RESET);
        }
    }
    echo box_bot();
    prompt_enter("ENTER untuk balik...");
}

function deleteAccountUI() {
    clr();
    $accounts = loadTpAccounts();
    if (empty($accounts)) { echo NEWLINE . " " . RED . "[!]" . RESET . " No accounts." . NEWLINE; sleep(1); return; }
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: DELETE ACCOUNT"));
    echo box_div();
    foreach ($accounts as $i => $a) {
        echo box_line(CYAN . "[$i] " . RESET . WHITE . short_str($a['email'], 40) . RESET);
    }
    echo box_bot();
    $sel = prompt_input("Delete index #");
    if (!is_numeric($sel) || !isset($accounts[(int)$sel])) {
        echo NEWLINE . " " . RED . "[!]" . RESET . " Invalid." . NEWLINE; sleep(1); return;
    }
    array_splice($accounts, (int)$sel, 1);
    saveAccounts($accounts);
    echo NEWLINE . " " . GREEN . "[OK]" . RESET . " Removed. Remaining: " . count($accounts) . NEWLINE;
    sleep(1);
}

// ======================== START CLAIMING ========================
function start_claiming($accounts) {
    global $DASH;

    $DASH['stage'] = 'LOGIN';
    $DASH['status'] = 'Starting';
    $DASH['user'] = '-';
    $DASH['balance'] = '-';
    $DASH['claims'] = 0;
    $DASH['total_reward'] = 0;
    $DASH['last_reward'] = '0';
    $DASH['currency'] = 'TRX';
    $DASH['fails'] = 0;
    $DASH['logs'] = [];
    $DASH['start_time'] = time();
    $DASH['cooldown'] = 0;
    $DASH['solver_bal'] = waryono_balance();

    dash_log("[*]", "BOOT  ", APP_NAME . " " . APP_VER . " ready", GREEN);
    sleep(1);

    $timers = [];
    $counters = [];

    while (true) {
        $now = time();

        // ═══ CEK AKUN YANG READY ═══
        $readyList = [];
        $nextReady = null;
        $userList = [];

        foreach ($accounts as $idx => $acc) {
            if (isset($timers[$idx]) && $timers[$idx] > $now) {
                $rem = $timers[$idx] - $now;
                $userList[] = short_str($acc['email'], 16) . " (" . gmdate("i:s", $rem) . ")";
                if ($nextReady === null || $timers[$idx] < $nextReady) {
                    $nextReady = $timers[$idx];
                }
                continue;
            }
            $readyList[] = $idx;
        }

        // ═══ KALAU GA ADA YANG READY → TUNGGU SAMPE AKUN PERTAMA READY ═══
        if (empty($readyList) && $nextReady !== null) {
            $wait = $nextReady - $now;
            if ($wait > 0) {
                dash_set('user', implode(", ", array_slice($userList, 0, 2)) . (count($userList) > 2 ? " +" . (count($userList)-2) : ""));
                dash_log("[!]", "COOLDN", "all accounts on cooldown — waiting {$wait}s", ORANGE);
                dash_timer($wait, "Cooldown");
                continue;
            }
        }

        // ═══ PROSES AKUN YANG READY ═══
        foreach ($readyList as $idx) {
            $acc = $accounts[$idx];
            $email = $acc['email']; $password = $acc['password']; $proxy = $acc['proxy'];
            $tg = ['token'=>$acc['tg_token'],'chat'=>$acc['tg_chat']];

            dash_set('user', short_str($email, 24));

            if (isset($timers[$idx])) {
                dash_log("[>]", "READY ", "{$email} — claiming...", CYAN);
                unset($timers[$idx]);
            }

            $counters[$idx] = $counters[$idx] ?? ['success'=>0,'fail'=>0,'total'=>0];
            $r = tp_claim($email, $password, $proxy, $idx, $counters[$idx], $tg);
            $counters[$idx]['total']++;
            if (!empty($r['success'])) {
                $counters[$idx]['success']++;
            } else {
                $counters[$idx]['fail']++;
                dash_set('fails', $DASH['fails'] + 1);
            }
            if (!empty($r['timer'])) {
                $timers[$idx] = time() + (int)$r['timer'];
            }

            dash_set('cooldown', 0);
            sleep(1);
        }
        // Loop langsung lagi tanpa delay — kalau ada yang cooldown baru tunggu
    }
}

// ======================== CHECK ALL ACCOUNTS ========================
function check_all_accounts($accounts) {
    global $DASH;

    $DASH['stage'] = 'CHECK';
    $DASH['status'] = 'Checking all accounts';
    $DASH['logs'] = [];
    $DASH['start_time'] = time();
    $DASH['cooldown'] = 0;
    $DASH['solver_bal'] = waryono_balance();

    dash_log("[*]", "CHECK ", "checking " . count($accounts) . " account(s)...", CYAN);
    sleep(1);

    foreach ($accounts as $idx => $acc) {
        $email = $acc['email']; $password = $acc['password']; $proxy = $acc['proxy'];
        dash_set('user', short_str($email, 24));
        dash_log("[>]", "CHECK ", "─── #{$idx} {$email} ───", CYAN);
        tp_check($email, $password, $proxy, $idx);
        sleep(2);
    }

    dash_log("[OK]", "CHECK ", "semua akun udah di-check", GREEN);
    prompt_enter("ENTER untuk balik ke menu...");
}

// ======================== MAIN ========================
ensureInfoFile();

while (true) {
    $accounts = loadTpAccounts();
    $bal = waryono_balance();
    show_main_menu($accounts, $bal);

    $choice = prompt_main();

    if ($choice === '1') { addAccountUI(); continue; }
    if ($choice === '2') { listAccountsUI(); continue; }
    if ($choice === '3') { deleteAccountUI(); continue; }
    if ($choice === '0') { clr(); echo NEWLINE . " " . YELLOW . "Bye." . NEWLINE; exit(0); }
    if ($choice === '4') {
        if (empty($accounts)) { echo NEWLINE . " " . RED . "[!] No accounts." . NEWLINE; sleep(2); continue; }
        if ($bal === null || (int)$bal <= 0) { echo NEWLINE . " " . RED . "[!] Waryono balance 0." . NEWLINE; sleep(2); continue; }
        start_claiming($accounts);
    }
    if ($choice === '5') {
        if (empty($accounts)) { echo NEWLINE . " " . RED . "[!] No accounts." . NEWLINE; sleep(2); continue; }
        check_all_accounts($accounts);
    }
    echo NEWLINE . " " . RED . "[!] Invalid choice." . NEWLINE;
    sleep(1);
}
