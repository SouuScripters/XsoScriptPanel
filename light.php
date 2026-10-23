<?php
error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$configFile = "config.json";
if (!is_dir('session')) mkdir('session', 0777, true);
if (!is_dir('debug_ptc')) mkdir('debug_ptc', 0777, true);

const DEBUG_MODE = false;
const DEBUG_DIR  = "debug_ptc";

const NEON_CYAN    = "\033[1;36m";
const NEON_MAGENTA = "\033[1;35m";
const NEON_YELLOW  = "\033[1;33m";
const NEON_GREEN   = "\033[1;32m";
const NEON_RED     = "\033[1;31m";
const NEON_BLUE    = "\033[1;34m";
const NEON_WHITE   = "\033[1;37m";
const NEON_GRAY    = "\033[1;90m";
const RESET        = "\033[0m";
const BOLD         = "\033[1m";

const api_url           = "https://lightningquest.net";
const SITEKEY_HCAPTCHA  = "bbc4e0f2-0052-4980-b1c2-aafe3e3c3bee";
const SITEKEY_TURNSTILE = "0x4AAAAAADxePtT-Imsq_y0B";
const MAX_LOGS = 5;
const TOKEN_TTL = 21600;

const WARYONO_IN  = "https://api.waryono.my.id/in.php";
const WARYONO_OUT = "https://api.waryono.my.id/res.php";

$CONFIG = [
    "apikey"   => "",
    "email"    => "",
    "password" => "",
    "proxy"    => "",
];

$currentUseProxy    = false;
$currentProxyParsed = null;
$currentProxyType   = CURLPROXY_SOCKS5_HOSTNAME;
$currentCookieFile  = '';
$currentEmail       = '';
$currentPassword    = '';
$access_token       = '';
$handling_interrupt = false;

class UserInterrupt extends Exception {}
class EnergyOut extends Exception {}

// ═══════════════ DISPLAY HELPERS ═══════════════
function clear() { (PHP_OS == 'Linux') ? system('clear') : pclose(popen('cls', 'w')); }

function typewrite($text, $speed = 0.015) {
    for ($i = 0; $i < mb_strlen($text); $i++) { echo mb_substr($text, $i, 1); flush(); usleep($speed * 1000000); }
    echo "\n";
}

function banner() {
    echo "\n" . NEON_CYAN . "==================================================" . RESET . "\n";
    echo NEON_MAGENTA . BOLD . "          ⚡ LIGHTNINGQUEST AUTO BOT ⚡" . RESET . "\n";
    echo NEON_GREEN . "          Credit: MoneyMaker_w | Waryono" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n\n";
}

function section($title) {
    $prefix = "===== " . $title;
    $pad = 50 - strlen($prefix);
    if ($pad < 1) $pad = 1;
    echo "\n" . NEON_CYAN . $prefix . " " . str_repeat("=", $pad) . RESET . "\n\n";
}

function bar_timer($seconds, $indent = "  ") {
    $total = (int)$seconds;
    if ($total < 1) return;
    $width = 20;
    $start = microtime(true);

    while (true) {
        $elapsed = microtime(true) - $start;
        $remaining = $total - $elapsed;
        if ($remaining < 0) $remaining = 0;

        $pct = min(100, (int)round(($elapsed / $total) * 100));
        $filled = (int)round(($pct / 100) * $width);
        $empty  = $width - $filled;

        $mm = (int)floor($remaining / 60);
        $ss = (int)$remaining % 60;

        echo "\r\033[K";
        echo $indent;
        echo NEON_GRAY . "[" . RESET;
        echo NEON_GREEN . str_repeat("▓", $filled) . RESET;
        echo NEON_GRAY . str_repeat("░", $empty) . "]" . RESET;
        echo " " . NEON_YELLOW . str_pad($pct . "%", 4, " ", STR_PAD_LEFT) . RESET;
        echo "  " . NEON_GRAY . "|" . RESET . "  " . NEON_CYAN . sprintf('%02d:%02d', $mm, $ss) . RESET;
        flush();

        if ($remaining <= 0) break;
        usleep(100000);
    }
    echo "\r\033[K";
}

function ok($text)   { echo NEON_GREEN . "[+] " . RESET . $text . "\n"; }
function good($text) { echo NEON_GREEN . "[✓] " . RESET . $text . "\n"; }
function info($text) { echo NEON_CYAN  . "[~] " . RESET . $text . "\n"; }
function warn($text) { echo NEON_YELLOW . "[!] " . RESET . $text . "\n"; }
function fail($text) { echo NEON_RED   . "[✗] " . RESET . $text . "\n"; }

function fmt_coin($v) {
    if (is_int($v) || (is_numeric($v) && floor($v) == $v)) return (string)(int)$v;
    $s = number_format((float)$v, 6, '.', '');
    return rtrim(rtrim($s, '0'), '.');
}

function pretty_num($v) {
    if (is_array($v)) {
        if (isset($v['current'])) return $v['current'];
        if (isset($v['value']))   return $v['value'];
        if (isset($v['level']))   return $v['level'];
        foreach ($v as $sub) if (is_numeric($sub)) return $sub;
        return json_encode($v);
    }
    return $v;
}

function maskEmail($email) {
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) return $email;
    list($user, $domain) = explode('@', $email);
    $len = strlen($user);
    if ($len <= 4) return substr($user, 0, 1) . '***' . '@' . $domain;
    return substr($user, 0, 2) . '***' . substr($user, -2) . '@' . $domain;
}

function parseProxyString($proxyString) {
    $parts = explode(':', trim($proxyString));
    if (count($parts) === 4) return ['host_port' => $parts[0] . ':' . $parts[1], 'auth' => $parts[2] . ':' . $parts[3]];
    if (count($parts) === 2) return ['host_port' => $parts[0] . ':' . $parts[1], 'auth' => null];
    return null;
}

function maskProxy($proxyStr) {
    if (empty($proxyStr)) return "(kosong)";
    $parts = explode(':', $proxyStr);
    if (count($parts) === 4) {
        $mu = strlen($parts[2]) > 3 ? substr($parts[2], 0, 3) . "***" : "***";
        $mp = strlen($parts[3]) > 3 ? substr($parts[3], 0, 3) . "***" : "***";
        return $parts[0] . ":" . $parts[1] . ":" . $mu . ":" . $mp;
    }
    return $proxyStr;
}

function bool_val($v) {
    if (is_bool($v)) return $v;
    if (is_string($v)) { $l = strtolower(trim($v)); return !($l === '' || $l === 'false' || $l === '0' || $l === 'no' || $l === 'off' || $l === 'null'); }
    if (is_numeric($v)) return ((int)$v) !== 0;
    return !empty($v);
}

function hacker_intro() {
    clear();
    echo NEON_CYAN;
    typewrite("[+] Initializing LightningQuest Protocol...", 0.015);
    typewrite("[+] Bypassing security...", 0.015);
    typewrite("[+] System Ready & Online!", 0.015);
    echo RESET; sleep(1);
}

// ═══════════════ CONFIG ═══════════════
function loadConfig($configFile) {
    global $CONFIG;
    if (!file_exists($configFile)) {
        clear(); banner();
        echo NEON_YELLOW . BOLD . "[ SETUP AWAL ]" . RESET . "\n";
        echo NEON_WHITE . "API Key (Waryono) : " . NEON_YELLOW; $apikey = trim(fgets(STDIN));
        echo NEON_WHITE . "Email             : " . NEON_YELLOW; $email  = trim(fgets(STDIN));
        echo NEON_WHITE . "Password          : " . NEON_YELLOW; $password = trim(fgets(STDIN));
        echo NEON_WHITE . "Proxy (Enter skip): " . NEON_YELLOW; $proxy  = trim(fgets(STDIN));
        $CONFIG = ["apikey" => $apikey, "email" => $email, "password" => $password, "proxy" => $proxy];
        saveConfig($configFile);
        echo "\n" . NEON_GREEN . "[✓] Config saved." . RESET . "\n"; sleep(2);
    } else {
        $data = json_decode(file_get_contents($configFile), true) ?? [];
        $CONFIG = array_merge($CONFIG, $data);
        if (!empty($data['accounts'][0])) {
            $CONFIG['email']    = $data['accounts'][0]['email']    ?? '';
            $CONFIG['password'] = $data['accounts'][0]['password'] ?? '';
            $CONFIG['proxy']    = $data['accounts'][0]['proxy']    ?? '';
            saveConfig($configFile);
        }
    }
    return $CONFIG;
}

function saveConfig($configFile) {
    global $CONFIG;
    file_put_contents($configFile, json_encode($CONFIG, JSON_PRETTY_PRINT));
}

function setupSession() {
    global $CONFIG, $currentCookieFile, $currentUseProxy, $currentProxyParsed, $currentProxyType, $currentEmail, $currentPassword;
    $currentCookieFile = "session/" . md5($CONFIG['email']) . ".txt";
    $currentUseProxy   = false;
    $currentProxyParsed= null;
    $currentProxyType  = CURLPROXY_SOCKS5_HOSTNAME;
    if (!empty($CONFIG['proxy'])) {
        $currentProxyParsed = parseProxyString($CONFIG['proxy']);
        if ($currentProxyParsed) $currentUseProxy = true;
    }
    $currentEmail    = $CONFIG['email'];
    $currentPassword = $CONFIG['password'];
}

function token_path($email) { return "session/" . md5($email) . "_token.json"; }
function get_cached_token($email) {
    $path = token_path($email);
    if (!file_exists($path)) return null;
    $data = json_decode(file_get_contents($path), true);
    if (!$data || empty($data['token'])) return null;
    if (time() - ($data['ts'] ?? 0) > TOKEN_TTL) return null;
    return $data['token'];
}
function save_token($email, $token) { file_put_contents(token_path($email), json_encode(['token' => $token, 'ts' => time()])); }
function del_token($email) { $p = token_path($email); if (file_exists($p)) @unlink($p); }

// ═══════════════ HTTP ═══════════════
function wkwk($url, $payload = null, $headers = [], $method = "POST", $quiet = false, $no_proxy = false) {
    global $currentUseProxy, $currentProxyParsed, $currentProxyType, $currentCookieFile;
    $retry = 0;
    while ($retry < 3) {
        $retry++;
        $ch = curl_init();
        $final = [
            CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYHOST => 0, CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_HTTPHEADER => $headers, CURLOPT_CONNECTTIMEOUT => 20, CURLOPT_TIMEOUT => 45,
            CURLOPT_ENCODING => '', CURLOPT_TCP_KEEPALIVE => 1,
        ];
        if (!empty($currentCookieFile)) { $final[CURLOPT_COOKIEFILE] = $currentCookieFile; $final[CURLOPT_COOKIEJAR] = $currentCookieFile; }
        if (!$no_proxy && $currentUseProxy && $currentProxyParsed) {
            $final[CURLOPT_PROXY]     = $currentProxyParsed['host_port'];
            $final[CURLOPT_PROXYTYPE] = $currentProxyType;
            if ($currentProxyParsed['auth']) $final[CURLOPT_PROXYUSERPWD] = $currentProxyParsed['auth'];
        }
        if ($method === "POST") {
            $final[CURLOPT_POST] = true;
            $final[CURLOPT_POSTFIELDS] = is_array($payload) ? json_encode($payload) : $payload;
        }
        curl_setopt_array($ch, $final);
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err = curl_error($ch); curl_close($ch);
        if ($response !== false && $response !== '') return ["body" => $response, "code" => $code];
        if ($retry < 3) usleep(800000);
    }
    return ["body" => '{"error":"CONNECTION_FAILED"}', "code" => 0];
}

function http_nocookie($url, $method = 'GET', $data = [], $headers = [], $json_body = false) {
    $ch = curl_init();
    $opts = [
        CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false, CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT => 60, CURLOPT_CONNECTTIMEOUT => 30,
    ];
    if (strtoupper($method) === 'POST') {
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = $json_body ? $data : http_build_query($data);
    }
    if (!empty($headers)) $opts[CURLOPT_HTTPHEADER] = $headers;
    curl_setopt_array($ch, $opts);
    $res = curl_exec($ch);
    curl_close($ch);
    return $res;
}

function bitcotasks_raw_request($url, $payload = null, $cookieFileArg = null, $saveAs = null, $referer = null, $fetchDest = "empty", $fetchMode = "cors", $contentType = null) {
    global $currentUseProxy, $currentProxyParsed, $currentProxyType;
    if ($cookieFileArg === null) $cookieFileArg = DEBUG_DIR . "/bitcotasks_cookies.txt";
    $ch = curl_init();
    if ($referer === null) $referer = "https://bitcotasks.com/";
    $headers = [
        'accept: */*', 'accept-language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer: ' . $referer, 'sec-fetch-site: same-origin',
        'sec-fetch-mode: ' . $fetchMode, 'sec-fetch-dest: ' . $fetchDest,
        'user-agent: Mozilla/5.0 (Linux; Android 11; vivo 1904 Build/RP1A.200720.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36',
        'sec-ch-ua: "Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        'sec-ch-ua-mobile: ?1', 'sec-ch-ua-platform: "Android"',
        'cache-control: no-cache', 'pragma: no-cache',
    ];
    if ($contentType !== null) $headers[] = 'content-type: ' . $contentType;
    $opts = [
        CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true, CURLOPT_HEADER => true,
        CURLOPT_FOLLOWLOCATION => false, CURLOPT_COOKIEJAR => $cookieFileArg, CURLOPT_COOKIEFILE => $cookieFileArg,
        CURLOPT_SSL_VERIFYPEER => false, CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_HTTPHEADER => $headers, CURLOPT_TIMEOUT => 60, CURLOPT_CONNECTTIMEOUT => 30, CURLOPT_ENCODING => '',
    ];
    if ($currentUseProxy && $currentProxyParsed) {
        $opts[CURLOPT_PROXY] = $currentProxyParsed['host_port'];
        $opts[CURLOPT_PROXYTYPE] = $currentProxyType;
        if ($currentProxyParsed['auth']) $opts[CURLOPT_PROXYUSERPWD] = $currentProxyParsed['auth'];
    }
    if ($payload !== null) { $opts[CURLOPT_POST] = true; $opts[CURLOPT_POSTFIELDS] = $payload; }
    curl_setopt_array($ch, $opts);
    $response = curl_exec($ch);
    $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $info = curl_getinfo($ch); curl_close($ch);
    if ($response === false) return ['headers' => '', 'body' => '[CURL ERROR]', 'info' => []];
    return ['headers' => substr($response, 0, $headerSize), 'body' => substr($response, $headerSize), 'info' => $info];
}

// ═══════════════ CAPTCHA SOLVER ═══════════════
function captcha_header() {
    echo "\n" . NEON_CYAN . str_repeat("=", 48) . RESET . "\n";
    echo NEON_MAGENTA . BOLD . "    CAPTCHA SOLVER (WARYONO)" . RESET . "\n";
    echo NEON_CYAN . str_repeat("=", 48) . RESET . "\n\n";
}

function solve_captcha($method, $sitekey, $action = "") {
    global $CONFIG;
    $apikey = $CONFIG['apikey'];

    captcha_header();
    echo NEON_WHITE . "Method  : " . NEON_YELLOW . strtoupper($method) . RESET . "\n";

    $body = ["apikey" => $apikey, "methods" => $method, "domain" => "https://lightningquest.net", "sitekey" => $sitekey, "json" => 1];
    if ($action !== "") { $body["action"] = $action; $body["cdata"] = ""; }

    $request = wkwk(WARYONO_IN, $body, ["Content-Type: application/json"], "POST", true, true);
    $j = json_decode($request["body"], true);
    $taskId = $j["request"] ?? null;

    if (!$taskId) {
        echo NEON_WHITE . "Task ID : " . NEON_GRAY . "--" . RESET . "\n";
        echo NEON_WHITE . "Status  : " . NEON_RED . "FAILED ✗" . RESET . "\n\n";
        return null;
    }

    echo NEON_WHITE . "Task ID : " . NEON_MAGENTA . $taskId . RESET . "\n";
    echo NEON_WHITE . "Status  : " . NEON_YELLOW; flush();

    $startTime = microtime(true);
    $lastPoll = 0; $token = null; $maxWait = 120;

    while (true) {
        $elapsed = microtime(true) - $startTime;
        if ($elapsed > $maxWait) break;

        echo "\r" . NEON_WHITE . "Status  : " . NEON_YELLOW . "polling " . str_pad(round($elapsed, 1) . "s", 20) . RESET;
        flush();

        if (($elapsed - $lastPoll) >= 2) {
            $lastPoll = $elapsed;
            $pollUrl = WARYONO_OUT . "?apikey=" . urlencode($apikey) . "&action=get&id=" . urlencode($taskId) . "&json=1";
            $pollRes = wkwk($pollUrl, null, [], "GET", true, true);
            if (strpos($pollRes["body"], "CAPCHA_NOT_READY") !== false) { usleep(200000); continue; }
            $pj = json_decode($pollRes["body"], true);
            if (!empty($pj["request"])) { $token = $pj["request"]; break; }
        }
        usleep(200000);
    }

    $elapsed = round(microtime(true) - $startTime, 1);

    if ($token) {
        echo "\r" . NEON_WHITE . "Status  : " . NEON_GREEN . "SOLVED ✓" . RESET . str_repeat(" ", 20) . "\n";
        echo NEON_WHITE . "Time    : " . NEON_CYAN . $elapsed . "s" . RESET . "\n\n";
        return $token;
    }
    echo "\r" . NEON_WHITE . "Status  : " . NEON_RED . "TIMEOUT ✗" . RESET . str_repeat(" ", 20) . "\n";
    echo NEON_WHITE . "Time    : " . NEON_CYAN . $elapsed . "s" . RESET . "\n\n";
    return null;
}

function solve_captcha_retry($method, $sitekey, $maxRetry = 3, $action = "") {
    for ($attempt = 1; $attempt <= $maxRetry; $attempt++) {
        echo NEON_YELLOW . "[!] Bypass attempt : " . $attempt . "/" . $maxRetry . RESET . "\n";
        sleep(rand(2, 4));
        $token = solve_captcha($method, $sitekey, $action);
        if ($token) return $token;
        if ($attempt < $maxRetry) sleep(2 + $attempt);
    }
    return null;
}

function solve_bitcotask_captcha($base64Image) {
    global $CONFIG;
    $apikey = $CONFIG['apikey'];

    echo "\n" . NEON_CYAN . str_repeat("=", 48) . RESET . "\n";
    echo NEON_MAGENTA . BOLD . "    CAPTCHA (BITCOGIF) — WARYONO" . RESET . "\n";
    echo NEON_CYAN . str_repeat("=", 48) . RESET . "\n\n";
    echo NEON_WHITE . "Image   : " . NEON_GREEN . strlen($base64Image) . " chars" . RESET . "\n";

    $methodName = "bitcogif";
    $body = ["apikey" => $apikey, "methods" => $methodName, "base64" => $base64Image, "json" => 1];

    $startTime = microtime(true);
    $req = wkwk(WARYONO_IN, $body, ["Content-Type: application/json"], "POST", true, true);
    $j = json_decode($req['body'], true);

    if (!is_array($j) || ($j['status'] ?? 0) != 1) {
        echo NEON_WHITE . "Status  : " . NEON_RED . "FAILED ✗ (submit)" . RESET . "\n\n";
        return null;
    }

    $taskId = $j['request'];
    echo NEON_WHITE . "Task ID : " . NEON_MAGENTA . $taskId . RESET . "\n";
    echo NEON_WHITE . "Status  : " . NEON_YELLOW; flush();

    $lastPoll = 0; $coords = null; $maxWait = 120;

    while (true) {
        $elapsed = microtime(true) - $startTime;
        if ($elapsed > $maxWait) break;

        echo "\r" . NEON_WHITE . "Status  : " . NEON_YELLOW . "polling " . str_pad(round($elapsed, 1) . "s", 20) . RESET;
        flush();

        if (($elapsed - $lastPoll) >= 2) {
            $lastPoll = $elapsed;
            $pollUrl = WARYONO_OUT . "?apikey=" . urlencode($apikey) . "&action=get&id=" . urlencode($taskId) . "&json=1";
            $pollRes = wkwk($pollUrl, null, [], "GET", true, true);
            $pj = json_decode($pollRes['body'], true);
            if (!is_array($pj)) continue;

            if (($pj['status'] ?? 0) == 0) {
                $msg = $pj['request'] ?? '';
                if (strpos($msg, "NOT_READY") !== false) continue;
                echo "\r" . NEON_WHITE . "Status  : " . NEON_RED . "FAILED ✗ (" . substr($msg, 0, 20) . ")" . RESET . str_repeat(" ", 10) . "\n\n";
                return null;
            }
            if (($pj['status'] ?? 0) == 1 && !empty($pj['request'])) {
                $answer = $pj['request'];
                $x = null; $y = null;
                if (preg_match('/x[":\s]*(\d+)[,;].*?y[":\s]*(\d+)/i', $answer, $m)) { $x = (int)$m[1]; $y = (int)$m[2]; }
                if ($x !== null) $coords = ["x" => $x, "y" => $y];
                break;
            }
        }
        usleep(200000);
    }

    $elapsed = round(microtime(true) - $startTime, 1);

    if ($coords) {
        echo "\r" . NEON_WHITE . "Status  : " . NEON_GREEN . "SOLVED ✓" . RESET . str_repeat(" ", 20) . "\n";
        echo NEON_WHITE . "Time    : " . NEON_CYAN . $elapsed . "s" . RESET . "\n";
        echo NEON_WHITE . "Coords  : " . NEON_GREEN . "X=" . $coords['x'] . RESET . " " . NEON_GRAY . "|" . RESET . " " . NEON_GREEN . "Y=" . $coords['y'] . RESET . "\n\n";
        return $coords;
    }
    echo "\r" . NEON_WHITE . "Status  : " . NEON_RED . "TIMEOUT ✗" . RESET . str_repeat(" ", 20) . "\n\n";
    return null;
}

// ═══════════════ AUTH ═══════════════
function auth_headers() {
    global $access_token;
    $h = [
        'sec-ch-ua: "Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        'sec-ch-ua-mobile: ?1', 'sec-ch-ua-platform: "Android"', 'upgrade-insecure-requests: 1',
        'user-agent: Mozilla/5.0 (Linux; Android 11; vivo 1904 Build/RP1A.200720.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36',
        'accept: */*', 'x-requested-with: qzbr.zpr.pt',
        'sec-fetch-site: same-origin', 'sec-fetch-mode: cors', 'sec-fetch-dest: empty',
        'referer: https://lightningquest.net/ptc',
        'accept-language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority: u=1, i', 'content-type: application/json',
    ];
    if ($access_token) $h[] = 'authorization: Bearer ' . $access_token;
    return $h;
}

function do_login($email, $password) {
    $body = ["email" => $email, "password" => $password, "trafficExchangeBonus" => false];
    $res = wkwk(api_url . "/api/auth/login", $body, auth_headers());
    $json = json_decode($res["body"], true);
    if (!empty($json['access_token'])) return $json;
    fail("Login : " . ($json['msg'] ?? $json['message'] ?? substr($res['body'], 0, 80)));
    return null;
}

function ensure_login($email, $password, $force = false) {
    global $access_token;
    if (!$force) {
        $cached = get_cached_token($email);
        if ($cached) {
            $access_token = $cached;
            $res = wkwk(api_url . "/api/me", null, auth_headers(), "GET");
            if ($res["code"] == 200) {
                $me = json_decode($res["body"], true);
                if (is_array($me) && !isset($me['error']) && !empty($me)) {
                    return ['access_token' => $cached, 'user' => $me, 'me' => $me, '_cached' => true];
                }
            }
            del_token($email);
        }
    }
    $json = do_login($email, $password);
    if ($json) {
        save_token($email, $json['access_token']);
        $access_token = $json['access_token'];
        $meRes = wkwk(api_url . "/api/me", null, auth_headers(), "GET");
        $json['me'] = json_decode($meRes['body'], true) ?: [];
        return $json;
    }
    return null;
}

function api_get($path) {
    global $access_token, $currentEmail, $currentPassword;
    $res = wkwk(api_url . $path, null, auth_headers(), "GET");
    if ($res["code"] == 401) {
        del_token($currentEmail);
        $login = ensure_login($currentEmail, $currentPassword, true);
        if ($login) { $access_token = $login['access_token']; $res = wkwk(api_url . $path, null, auth_headers(), "GET"); }
    }
    return json_decode($res["body"], true);
}

function api_post($path, $payload) {
    global $access_token, $currentEmail, $currentPassword;
    $res = wkwk(api_url . $path, $payload, auth_headers(), "POST");
    if ($res["code"] == 401) {
        del_token($currentEmail);
        $login = ensure_login($currentEmail, $currentPassword, true);
        if ($login) { $access_token = $login['access_token']; $res = wkwk(api_url . $path, $payload, auth_headers(), "POST"); }
    }
    return json_decode($res["body"], true);
}

// ═══════════════ QUEST HELPERS ═══════════════
function fetch_all_quests() {
    $prog = api_get("/api/quests/progress");
    $ach  = api_get("/api/achievements");

    $daily = []; $weekly = [];
    if (is_array($prog) && isset($prog['progress']) && is_array($prog['progress'])) {
        foreach ($prog['progress'] as $q) {
            if (!is_array($q)) continue;
            $id = strtolower((string)($q['id'] ?? ''));
            if (strpos($id, 'daily_')  === 0) $daily[]  = $q;
            if (strpos($id, 'weekly_') === 0) $weekly[] = $q;
        }
    }
    $achievements = [];
    if (is_array($ach) && isset($ach['achievements']) && is_array($ach['achievements'])) {
        $achievements = $ach['achievements'];
    }
    return ['daily' => $daily, 'weekly' => $weekly, 'achievements' => $achievements];
}

function claim_quests_once() {
    $stats = ['daily' => 0, 'daily_coins' => 0, 'daily_xp' => 0,
              'weekly' => 0, 'weekly_coins' => 0, 'weekly_xp' => 0,
              'ach' => 0, 'ach_coins' => 0, 'ach_xp' => 0];

    $q = fetch_all_quests();

    foreach ($q['daily'] as $item) {
        if (empty($item['complete']) || !empty($item['claimed'])) continue;
        $res = api_post("/api/quests/" . $item['id'] . "/claim", []);
        if (is_array($res) && ($res['ok'] ?? false) === true) {
            $coins = $res['reward']['coins'] ?? 0;
            $xp    = $res['reward']['xp'] ?? 0;
            $stats['daily']++;
            $stats['daily_coins'] += $coins;
            $stats['daily_xp']    += $xp;
            echo NEON_GREEN . "[+] Daily " . $item['id'] . "  " . NEON_YELLOW . "+" . fmt_coin($coins) . "c" . RESET . "  " . NEON_GREEN . "+" . $xp . "xp" . RESET . "\n";
        }
        usleep(200000);
    }

    foreach ($q['weekly'] as $item) {
        if (empty($item['complete']) || !empty($item['claimed'])) continue;
        $res = api_post("/api/quests/" . $item['id'] . "/claim", []);
        if (is_array($res) && ($res['ok'] ?? false) === true) {
            $coins = $res['reward']['coins'] ?? 0;
            $xp    = $res['reward']['xp'] ?? 0;
            $stats['weekly']++;
            $stats['weekly_coins'] += $coins;
            $stats['weekly_xp']    += $xp;
            echo NEON_GREEN . "[+] Weekly " . $item['id'] . "  " . NEON_YELLOW . "+" . fmt_coin($coins) . "c" . RESET . "  " . NEON_GREEN . "+" . $xp . "xp" . RESET . "\n";
        }
        usleep(200000);
    }

    foreach ($q['achievements'] as $item) {
        if (empty($item['complete']) || !empty($item['claimed'])) continue;
        $res = api_post("/api/achievements/" . $item['id'] . "/claim", []);
        $ok = is_array($res) && ($res['ok'] ?? false) === true;
        if (!$ok) {
            $res = api_post("/api/quests/" . $item['id'] . "/claim", []);
            $ok = is_array($res) && ($res['ok'] ?? false) === true;
        }
        if ($ok) {
            $coins = $res['reward']['coins'] ?? 0;
            $xp    = $res['reward']['xp'] ?? 0;
            $stats['ach']++;
            $stats['ach_coins'] += $coins;
            $stats['ach_xp']    += $xp;
            echo NEON_GREEN . "[+] Achievement " . $item['id'] . "  " . NEON_YELLOW . "+" . fmt_coin($coins) . "c" . RESET . "  " . NEON_GREEN . "+" . $xp . "xp" . RESET . "\n";
        }
        usleep(200000);
    }

    return $stats;
}

// ═══════════════ FAUCET + DAILY ═══════════════
function faucet_claim_single() {
    $status = api_get("/api/claim-status");
    $faucet = $status['faucet'] ?? [];

    if (empty($faucet['ready'])) {
        $nextAt = strtotime($faucet['nextAt'] ?? '');
        $cd = intval($faucet['cooldownSeconds'] ?? 300);
        $wait = $nextAt ? ($nextAt - time()) : $cd;
        if ($wait < 5) $wait = 5;
        return ['status' => 'cooldown', 'wait' => $wait];
    }

    info("Faucet challenge...");
    $ch = api_get("/api/faucet/challenge");
    if (empty($ch['claimToken'])) return ['status' => 'error', 'wait' => 10];
    $claimToken = $ch['claimToken'];
    $minWait = intval($ch['minWaitSeconds'] ?? 5);
    if ($minWait > 0) { info("Waiting bypass " . $minWait . "s..."); sleep($minWait); }

    $captchaRequired = bool_val($faucet['captchaRequired'] ?? false);
    $provider = $faucet['captchaProvider'] ?? 'hcaptcha';
    if (!empty($ch['captchaProvider'])) $provider = $ch['captchaProvider'];

    $captchaToken = "";
    if ($captchaRequired) {
        info("Solving " . $provider . "...");
        $sitekey = ($provider === "hcaptcha") ? SITEKEY_HCAPTCHA : SITEKEY_TURNSTILE;
        $captchaToken = solve_captcha_retry($provider, $sitekey, 3, ($provider === "turnstile" ? "faucet-cadence-v1" : ""));
        if (!$captchaToken) return ['status' => 'error', 'wait' => 10];
    }

    sleep(rand(1, 3));

    $claim = api_post("/api/claim/faucet", ["captchaToken" => $captchaToken, "claimToken" => $claimToken]);
    if (empty($claim['ok'])) {
        $errMsg = $claim['msg'] ?? $claim['message'] ?? $claim['error'] ?? substr(json_encode($claim), 0, 60);
        fail("Faucet : " . $errMsg);
        return ['status' => 'error', 'wait' => 10];
    }

    $reward = $claim['reward'] ?? [];
    $snap   = $reward['snapshot'] ?? $claim['snapshot'] ?? [];
    $nextAt = strtotime($claim['nextAt'] ?? '');
    $cd     = $nextAt ? ($nextAt - time()) : 300;
    if ($cd < 5) $cd = 300;

    return [
        'status' => 'claimed',
        'wait' => $cd,
        'coins' => $reward['coins'] ?? 0,
        'xp' => $reward['xp'] ?? 0,
        'balance' => pretty_num($snap['balance'] ?? '?'),
        'level' => pretty_num($snap['level'] ?? '?'),
    ];
}

function daily_claim_single() {
    $status = api_get("/api/claim-status");
    $daily = $status['daily'] ?? [];

    if (empty($daily['ready'])) {
        $nextAt = strtotime($daily['nextAt'] ?? '');
        $wait = $nextAt ? ($nextAt - time()) : 3600;
        if ($wait < 5) $wait = 3600;
        return ['status' => 'cooldown', 'wait' => $wait];
    }

    info("Daily bonus...");
    $captcha = solve_captcha_retry("turnstile", SITEKEY_TURNSTILE, 3);
    if (!$captcha) return ['status' => 'error', 'wait' => 10];

    $claim = api_post("/api/claim/daily", ["captchaToken" => $captcha]);
    if (!empty($claim['ok'])) {
        $r = $claim['reward'] ?? [];
        return ['status' => 'claimed', 'coins' => $r['coins'] ?? 0, 'xp' => $r['xp'] ?? 0];
    }
    return ['status' => 'error', 'wait' => 10];
}

// ═══════════════ BITCOTASKS — SINGLE TASK ═══════════════
function run_ptc_single($acc, $task, $cookieFile, $index, $total) {
    echo "\n" . NEON_CYAN . "--- Task " . $index . "/" . $total . ": " . RESET . NEON_MAGENTA . substr($task['title'], 0, 30) . RESET . NEON_YELLOW . " (" . $task['rewardCoins'] . "c)" . RESET . NEON_CYAN . " ---" . RESET . "\n";

    info("Opening task page...");
    $view = bitcotasks_raw_request($task['url'], null, $cookieFile, null, "https://lightningquest.net/ptc", "document", "navigate");

    $leadUrl = '';
    if (preg_match("/window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]/", $view['body'], $m)) $leadUrl = $m[1];
    elseif (preg_match('/<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?\d+;\s*url=([^"\'>\s]+)/i', $view['body'], $m)) $leadUrl = $m[1];
    elseif (preg_match("/location\.replace\(['\"]([^'\"]+)['\"]\)/", $view['body'], $m)) $leadUrl = $m[1];

    if (!$leadUrl) { fail("No redirect"); return false; }
    $leadUrl = preg_replace('#(?<!:)//+#', '/', $leadUrl);
    if (strpos($leadUrl, 'http') !== 0) $leadUrl = 'https://bitcotasks.com' . $leadUrl;

    info("Following lead...");
    $lead = bitcotasks_raw_request($leadUrl, null, $cookieFile, null, $task['url'], "document", "navigate");
    $html = $lead['body'];

    preg_match('/var\s+token\s*=\s*"([^"]+)"/', $html, $mToken);
    preg_match('/var\s+sub_id\s*=\s*"([^"]+)"/', $html, $mSubId);
    preg_match('/var\s+hash\s*=\s*"([^"]+)"/', $html, $mHash);
    preg_match('/var\s+api_key\s*=\s*"([^"]+)"/', $html, $mKey);
    preg_match('/var\s+ctoken\s*=\s*"([^"]+)"/', $html, $mCtoken);
    preg_match('/var\s+duration\s*=\s*(\d+)/', $html, $mDuration);
    preg_match('/captcha2\/([a-f0-9]+)\.js\?action=captcha/', $html, $mCapShort);

    $token = $mToken[1] ?? ''; $subId = $mSubId[1] ?? ''; $hash = $mHash[1] ?? '';
    $apiKey = $mKey[1] ?? ''; $ctoken = $mCtoken[1] ?? '';
    $duration = intval($mDuration[1] ?? $task['durationSeconds']);
    $capHash = $mCapShort[1] ?? '';

    if (!$token || !$ctoken || !$capHash || !$hash) { fail("Extract vars failed"); return false; }

    bitcotasks_raw_request("https://bitcotasks.com/firewall.php?key={$apiKey}&sub_id={$subId}", null, $cookieFile, null, $leadUrl, "empty", "cors");

    info("Fetching captcha...");
    $capUrl = "https://bitcotasks.com/captcha2/{$capHash}.js?action=captcha";
    $capJs = bitcotasks_raw_request($capUrl, null, $cookieFile, null, $leadUrl, "script", "no-cors")['body'];

    unset($mVerify, $mFields, $mRespSuccess, $mRespTokens, $mDynamicField);
    preg_match('#/captcha2/([a-zA-Z0-9]+)\?action=data&cdata=([a-f0-9]+)#', $capJs, $mVerify);
    $verifyShort = $mVerify[1] ?? ''; $cdata = $mVerify[2] ?? '';
    preg_match('/var\s+payload\s*=\s*"([A-Za-z0-9]+)=([^"&]*)&([A-Za-z0-9]+)=/', $capJs, $mFields);
    $field1 = $mFields[1] ?? ''; $field1Val = $mFields[2] ?? ''; $field2 = $mFields[3] ?? '';
    preg_match('/if\s*\(\s*response\.([A-Za-z0-9]+)\s*\)/', $capJs, $mRespSuccess);
    preg_match_all('/=\s*response\.([A-Za-z0-9]+)/', $capJs, $mRespTokens);
    $respSuccessField = $mRespSuccess[1] ?? ''; $respTokenField = $mRespTokens[1][0] ?? '';
    preg_match('/getElementById\("([^"]+)"\)\.value\s*=\s*response\./', $capJs, $mDynamicField);
    $dynamicField = $mDynamicField[1] ?? '';
    if (!$dynamicField) { $dynamicField = $ctoken; }

    if (!$verifyShort || !$cdata || !$field1 || !$field2 || !$respSuccessField || !$respTokenField) {
        fail("Extract captcha pattern failed"); return false;
    }

    $postBody = json_encode(["t" => round(microtime(true) * 1000), "r" => mt_rand() / mt_getrandmax()]);
    $capImg = bitcotasks_raw_request($capUrl, $postBody, $cookieFile, null, $leadUrl, "empty", "cors", "application/json");
    $capImgJson = json_decode($capImg['body'], true);
    $img = $capImgJson['image'] ?? '';

    if (strlen($img) < 100) { fail("No captcha image"); return false; }

    $coords = solve_bitcotask_captcha($img);
    if (!$coords) { fail("Captcha solve failed"); return false; }

    $submitBody = $field1 . "=" . urlencode($field1Val) . "&" . $field2 . "=" . urlencode("[" . $coords['x'] . "," . $coords['y'] . "]");
    $submitUrl = "https://bitcotasks.com/captcha2/{$verifyShort}?action=data&cdata={$cdata}";
    $capSubmit = bitcotasks_raw_request($submitUrl, $submitBody, $cookieFile, null, $leadUrl, "empty", "cors", "application/x-www-form-urlencoded");
    $submitJson = json_decode($capSubmit['body'], true);

    if (!is_array($submitJson) || empty($submitJson[$respSuccessField]) || empty($submitJson[$respTokenField])) {
        fail("Captcha token parse failed"); return false;
    }
    $captchaAnswer = $submitJson[$respTokenField];

    bitcotasks_raw_request($leadUrl, "action=start_view", $cookieFile, null, $leadUrl, "empty", "cors", "application/x-www-form-urlencoded");

    info("Watching ad " . $duration . "s...");
    bar_timer($duration + 3, "  ");

    $confirmBody = "action=proccessLead&hash={$hash}&key={$apiKey}&sub_id={$subId}&token={$token}&{$dynamicField}=" . urlencode($captchaAnswer);
    $confirm = bitcotasks_raw_request("https://bitcotasks.com/system/ajax.php", $confirmBody, $cookieFile, null, $leadUrl, "empty", "cors", "application/x-www-form-urlencoded");
    $confirmJson = json_decode($confirm['body'], true);

    if (isset($confirmJson['status']) && ($confirmJson['status'] == '200' || $confirmJson['status'] == 200)) {
        good("Success " . NEON_YELLOW . "+" . $task['rewardCoins'] . "c" . RESET);
        return true;
    }
    fail("Confirm failed");
    return false;
}

// ═══════════════ BITCOTASKS — ALL TASKS ═══════════════
function run_ptc_all_tasks($acc) {
    global $access_token;
    $cookieFile = DEBUG_DIR . "/bitcotasks_cookies_" . md5($acc['email']) . ".txt";

    bitcotasks_raw_request("https://bitcotasks.com/", null, $cookieFile, null, "https://lightningquest.net/ptc", "document", "navigate");

    $done = 0;
    $failed = 0;
    $triedIds = [];
    $maxIterations = 60;
    $totalTasks = 0;

    $res = api_get("/api/ptc/bitcotasks");
    if (is_array($res)) {
        $totalTasks = count($res['tasks'] ?? []);
    }

    info("PTC : " . NEON_GREEN . $totalTasks . " task(s)" . RESET . " available. Processing ALL...");

    for ($i = 0; $i < $maxIterations; $i++) {
        $res = api_get("/api/ptc/bitcotasks");
        if (!is_array($res)) { fail("API fetch failed, stopping"); break; }

        $tasks = $res['tasks'] ?? [];
        if (empty($tasks)) { warn("No more tasks available"); break; }

        $task = null;
        foreach ($tasks as $t) {
            if (!in_array($t['id'], $triedIds)) { $task = $t; break; }
        }
        if (!$task) { warn("All tasks tried"); break; }

        $triedIds[] = $task['id'];
        $index = count($triedIds);
        $total = max($totalTasks, count($tasks) + $index - 1);

        $ok = false;
        try {
            $ok = run_ptc_single($acc, $task, $cookieFile, $index, $total);
        } catch (Exception $e) {
            fail("Exception: " . $e->getMessage());
        }

        if ($ok) $done++;
        else $failed++;

        sleep(2);
    }

    good("PTC summary : " . NEON_GREEN . $done . " success" . RESET . " / " . NEON_RED . $failed . " failed" . RESET . " / " . NEON_YELLOW . count($triedIds) . " tried" . RESET);
    return ['done' => $done, 'failed' => $failed, 'tried' => count($triedIds)];
}

// ═══════════════ AUTOFARM ═══════════════
function menu_autofarm($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    $cycle = 0;
    $grandCoins = 0; $grandXp = 0;
    $grandFaucet = 0; $grandDaily = 0; $grandQuests = 0; $grandPtc = 0;
    $sessionStart = time();

    while (true) {
        $cycle++;
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { fail("Login gagal. Retry 15s..."); sleep(15); continue; }
        $access_token = $login['access_token'];
        $me = $login['me'] ?? api_get("/api/me");

        $uptime = gmdate("H:i:s", time() - $sessionStart);

        clear(); banner();
        echo NEON_CYAN . "[ AUTO FARMING ALL ]" . RESET . " " . NEON_MAGENTA . "Cycle #" . str_pad($cycle, 3, "0", STR_PAD_LEFT) . RESET . " | Up " . NEON_YELLOW . $uptime . RESET . "\n";
        echo NEON_CYAN . "==================================================" . RESET . "\n";
        echo NEON_WHITE . "Acc     : " . NEON_YELLOW . maskEmail($CONFIG['email']) . RESET . "\n";
        echo NEON_WHITE . "Balance : " . NEON_GREEN . pretty_num($me['balance'] ?? $me['coins'] ?? '?') . RESET . "       Lv : " . NEON_BLUE . pretty_num($me['level'] ?? 1) . RESET . "\n";
        echo NEON_WHITE . "Coins   : " . NEON_YELLOW . fmt_coin($grandCoins) . RESET . "                 XP : " . NEON_GREEN . $grandXp . RESET . "\n";
        echo NEON_WHITE . "Quests  : " . NEON_GREEN . $grandQuests . RESET . "                 Daily : " . NEON_GREEN . $grandDaily . RESET . "\n";
        echo NEON_WHITE . "Faucet  : " . NEON_GREEN . $grandFaucet . RESET . "                 PTC   : " . NEON_GREEN . $grandPtc . RESET . "\n";
        echo NEON_CYAN . "==================================================" . RESET . "\n";

        section("[1/4] QUEST");
        $qs = claim_quests_once();
        $qCount = $qs['daily'] + $qs['weekly'] + $qs['ach'];
        if ($qCount > 0) {
            $grandQuests += $qCount;
            $grandCoins  += $qs['daily_coins'] + $qs['weekly_coins'] + $qs['ach_coins'];
            $grandXp     += $qs['daily_xp'] + $qs['weekly_xp'] + $qs['ach_xp'];
            echo "\n" . NEON_GREEN . "[✓] Total quest : " . $qCount . " claimed" . RESET . "\n";
        } else {
            warn("No quest ready");
        }

        section("[2/4] DAILY BONUS");
        $dailyRes = daily_claim_single();
        if ($dailyRes['status'] === 'claimed') {
            $grandDaily++;
            $grandCoins += $dailyRes['coins'];
            $grandXp    += $dailyRes['xp'];
            good("Daily : " . NEON_YELLOW . "+" . fmt_coin($dailyRes['coins']) . "c" . RESET . " | " . NEON_GREEN . "+" . $dailyRes['xp'] . "xp" . RESET);
        } elseif ($dailyRes['status'] === 'cooldown') {
            warn("Daily cooldown : " . NEON_YELLOW . gmdate("H:i:s", $dailyRes['wait']) . RESET);
        } else {
            fail("Daily failed");
        }

        section("[3/4] FAUCET");
        $faucetRes = faucet_claim_single();
        $faucetWait = 300;
        if ($faucetRes['status'] === 'claimed') {
            $grandFaucet++;
            $grandCoins += $faucetRes['coins'];
            $grandXp    += $faucetRes['xp'];
            $faucetWait = $faucetRes['wait'];
            good("Faucet : " . NEON_YELLOW . "+" . fmt_coin($faucetRes['coins']) . "c" . RESET . " | " . NEON_GREEN . "+" . $faucetRes['xp'] . "xp" . RESET);
            echo NEON_GREEN . "[+] Balance: " . NEON_GREEN . $faucetRes['balance'] . RESET . "\n";
        } elseif ($faucetRes['status'] === 'cooldown') {
            $faucetWait = $faucetRes['wait'];
            warn("Faucet cooldown : " . NEON_YELLOW . gmdate("H:i:s", $faucetWait) . RESET);
        } else {
            fail("Faucet failed");
        }

        section("[4/4] BITCOTASKS PTC");
        $ptcResult = run_ptc_all_tasks($CONFIG);
        $grandPtc += $ptcResult['done'];
        echo "\n" . NEON_GREEN . "[✓] PTC success : " . $ptcResult['done'] . " task(s)" . RESET . "\n";

        $sleepSec = ($faucetWait > 10) ? $faucetWait + 10 : 60;
        echo "\n" . NEON_CYAN . "==================================================" . RESET . "\n";
        echo NEON_MAGENTA . "Cycle #" . $cycle . " completed" . RESET . "\n";
        echo NEON_WHITE . "Next cycle : " . NEON_YELLOW . gmdate("H:i:s", $sleepSec) . RESET . "\n";
        echo NEON_CYAN . "==================================================" . RESET . "\n\n";
        bar_timer($sleepSec, "  ");
    }
}

// ═══════════════ FAUCET MENU ═══════════════
function menu_faucet($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ MODE : FAUCET + QUEST + DAILY ]" . RESET . "\n";
    echo NEON_GRAY . "Loop auto claim — Ctrl+C untuk stop" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    $claims = 0;

    while (true) {
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { fail("Login gagal. Retry 10s..."); sleep(10); continue; }
        $access_token = $login['access_token'];
        $me = $login['me'] ?? api_get("/api/me");

        echo "\n" . NEON_CYAN . "[ Round #" . ($claims + 1) . " ] " . date('H:i:s') . RESET . "\n";
        echo NEON_WHITE . "Acc : " . NEON_YELLOW . maskEmail($CONFIG['email']) . RESET . " | " . NEON_WHITE . "Bal : " . NEON_GREEN . pretty_num($me['balance'] ?? '?') . RESET . "\n";

        section("[1/3] QUEST");
        $qs = claim_quests_once();
        $qCount = $qs['daily'] + $qs['weekly'] + $qs['ach'];
        good($qCount . " quest claimed");

        section("[2/3] DAILY");
        $dr = daily_claim_single();
        if ($dr['status'] === 'claimed') good("Daily " . NEON_YELLOW . "+" . fmt_coin($dr['coins']) . "c" . RESET . " | " . NEON_GREEN . "+" . $dr['xp'] . "xp" . RESET);
        elseif ($dr['status'] === 'cooldown') warn("Daily cooldown : " . NEON_YELLOW . gmdate("H:i:s", $dr['wait']) . RESET);
        else fail("Daily failed");

        section("[3/3] FAUCET");
        $r = faucet_claim_single();

        if ($r['status'] === 'claimed') {
            $claims++;
            good("Faucet : " . NEON_YELLOW . "+" . fmt_coin($r['coins']) . "c" . RESET . " | " . NEON_GREEN . "+" . $r['xp'] . "xp" . RESET);
            echo NEON_GREEN . "[+] Balance: " . $r['balance'] . RESET . "\n";
            echo NEON_BLUE . "[+] Level  : " . $r['level'] . RESET . "\n";
            echo "\n" . NEON_YELLOW . "[!] Next claim in " . gmdate("H:i:s", $r['wait']) . RESET . "\n";
            bar_timer($r['wait'] + 2, "  ");
        } elseif ($r['status'] === 'cooldown') {
            warn("Faucet cooldown : " . NEON_YELLOW . gmdate("H:i:s", $r['wait']) . RESET);
            bar_timer($r['wait'] + 2, "  ");
        } else {
            fail("Faucet failed. Retry 15s...");
            sleep(15);
        }
    }
}

// ═══════════════ CLAIM QUEST MENU ═══════════════
function menu_claim_quest($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ MODE : CLAIM QUEST ONLY ]" . RESET . "\n";
    echo NEON_GRAY . "Loop claim daily/weekly/achievement" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    $total = 0; $totalCoins = 0; $totalXp = 0;
    $round = 0;

    while (true) {
        $round++;
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { fail("Login gagal. Retry 10s..."); sleep(10); continue; }
        $access_token = $login['access_token'];

        section("[ Round #" . $round . " — " . date('H:i:s') . " ]");

        $qs = claim_quests_once();
        $c = $qs['daily'] + $qs['weekly'] + $qs['ach'];
        $coins = $qs['daily_coins'] + $qs['weekly_coins'] + $qs['ach_coins'];
        $xp = $qs['daily_xp'] + $qs['weekly_xp'] + $qs['ach_xp'];

        $total += $c; $totalCoins += $coins; $totalXp += $xp;

        echo "\n" . NEON_CYAN . "[ Summary ]" . RESET . "\n";
        echo NEON_WHITE . "This round : " . NEON_GREEN . $c . " quest" . RESET . ", " . NEON_YELLOW . "+" . fmt_coin($coins) . "c" . RESET . ", " . NEON_GREEN . "+" . $xp . "xp" . RESET . "\n";
        echo NEON_WHITE . "Total      : " . NEON_GREEN . $total . " quest" . RESET . ", " . NEON_YELLOW . "+" . fmt_coin($totalCoins) . "c" . RESET . ", " . NEON_GREEN . "+" . $totalXp . "xp" . RESET . "\n";

        if ($c === 0) {
            echo "\n" . NEON_YELLOW . "[!] No quest ready. Wait 60s..." . RESET . "\n";
            bar_timer(60, "  ");
        } else {
            echo "\n" . NEON_CYAN . "[~] Retry in 30s..." . RESET . "\n";
            bar_timer(30, "  ");
        }
    }
}

// ═══════════════ DAILY MENU ═══════════════
function menu_daily($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ MODE : AUTO DAILY BONUS ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    $claims = 0; $coins = 0;

    while (true) {
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { sleep(10); continue; }
        $access_token = $login['access_token'];

        $r = daily_claim_single();
        if ($r['status'] === 'claimed') {
            $claims++; $coins += $r['coins'];
            good("Daily #" . $claims . " : " . NEON_YELLOW . "+" . fmt_coin($r['coins']) . "c" . RESET . " | Total : " . NEON_YELLOW . fmt_coin($coins) . "c" . RESET);
            sleep(5);
        } elseif ($r['status'] === 'cooldown') {
            warn("Cooldown : " . NEON_YELLOW . gmdate("H:i:s", $r['wait']) . RESET);
            bar_timer($r['wait'] + 2, "  ");
        } else {
            fail("Failed. Retry 15s");
            sleep(15);
        }
    }
}

// ═══════════════ MINIGAMES ═══════════════
function menu_minigames($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ MODE : AUTO MINIGAMES ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    $totalOk = 0; $totalScraps = 0; $totalXp = 0;

    while (true) {
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { sleep(10); continue; }
        $access_token = $login['access_token'];

        $mg = api_get("/api/minigames");
        $games = $mg['games'] ?? [];

        if (!is_array($games) || empty($games)) {
            fail("Fetch minigames failed. Retry 10s");
            sleep(10); continue;
        }

        section("[ Fetch Minigames — " . date('H:i:s') . " ]");
        $played = 0;

        foreach ($games as $game) {
            $gameId = $game['id'] ?? '';
            if (!$gameId) continue;

            $available = (int)($game['today']['availablePlays'] ?? 0);
            if ($available <= 0) {
                warn(str_pad($game['name'] ?? $gameId, 18) . " : no plays left");
                continue;
            }

            for ($i = 0; $i < $available; $i++) {
                $gameName = $game['name'] ?? $gameId;
                echo "\n" . NEON_GREEN . "[+] " . RESET . NEON_MAGENTA . $gameName . RESET . " (" . ($i + 1) . "/" . $available . ") — " . NEON_CYAN . "Starting..." . RESET . "\n";

                $start = api_post("/api/minigames/start", ["gameId" => $gameId]);
                if (!is_array($start) || empty($start['runId'])) {
                    fail("Start failed");
                    break;
                }

                $durationMs = (int)($start['durationMs'] ?? $game['durationMs'] ?? 30000);
                $waitSec = (int)ceil($durationMs / 1000) + 2;
                if ($waitSec < 5) $waitSec = 5;

                info("Playing " . $waitSec . "s...");
                bar_timer($waitSec, "  ");

                $scrapsNeed = (float)($game['maxScraps'] ?? 0) * (float)($game['scoreDivisor'] ?? 1);
                $xpNeed     = (float)($game['maxXp'] ?? 0) / max(0.01, (float)($game['xpPerScore'] ?? 1));
                $score = (int)ceil(max($scrapsNeed, $xpNeed) * 1.05);
                if ($score < 50) $score = 50;

                $complete = api_post("/api/minigames/complete", [
                    "gameId"        => $gameId,
                    "runId"         => $start['runId'],
                    "runToken"      => $start['runToken'] ?? '',
                    "score"         => $score,
                    "hits"          => max(1, (int)round($score / 200)),
                    "misses"        => 2,
                    "hazards"       => 1,
                    "maxCombo"      => 10,
                    "durationMs"    => $durationMs + rand(100, 800),
                    "clientVersion" => 34,
                ]);

                if (is_array($complete) && !empty($complete['ok'])) {
                    $reward = $complete['reward'] ?? [];
                    $scraps = $reward['scraps'] ?? 0;
                    $xp = $reward['xp'] ?? 0;
                    $totalScraps += $scraps; $totalXp += $xp; $totalOk++;
                    good("+" . NEON_GREEN . $scraps . "s" . RESET . ", " . NEON_GREEN . "+" . $xp . "xp" . RESET);
                } else {
                    fail("Complete failed");
                }

                $played++;
                sleep(2);
            }
        }

        echo "\n" . NEON_CYAN . "[ Summary ]" . RESET . " plays: " . NEON_YELLOW . $played . RESET . " | ok: " . NEON_GREEN . $totalOk . RESET . " | scraps: " . NEON_GREEN . $totalScraps . RESET . " | xp: " . NEON_GREEN . $totalXp . RESET . "\n";
        if ($played === 0) warn("No plays. Wait 180s...");
        bar_timer(180, "  ");
    }
}

// ═══════════════ BOSS ═══════════════
function _boss_hp_bar($hp, $max, $width = 8) {
    if ($max <= 0 || $hp === null) return NEON_GRAY . str_repeat("░", $width) . RESET;
    $pct = max(0, min(100, ($hp / $max) * 100));
    $filled = (int)round(($pct / 100) * $width);
    $empty  = $width - $filled;
    return NEON_RED . str_repeat("█", $filled) . NEON_GRAY . str_repeat("░", $empty) . RESET;
}

function _fmt_big($n) {
    $n = (float)$n;
    if ($n >= 1000000000) return number_format($n / 1000000000, 2) . "B";
    if ($n >= 1000000)    return number_format($n / 1000000, 2) . "M";
    if ($n >= 1000)       return number_format($n / 1000, 1) . "K";
    return number_format($n);
}

function menu_boss($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    while (true) {
        clear(); banner();
        echo NEON_MAGENTA . BOLD . "[ BOSS ATTACK MODE ]" . RESET . "\n";
        echo NEON_CYAN . "==================================================" . RESET . "\n";
        echo NEON_GREEN . "[1] " . RESET . "Attack Boss (1 Energy)\n";
        echo NEON_GREEN . "[2] " . RESET . "Use 5 Energy (x5 dmg)\n";
        echo NEON_RED   . "[0] " . RESET . "Back\n";
        echo "\n" . NEON_YELLOW . "Pilih : " . RESET;
        $mode = trim(fgets(STDIN));
        if ($mode === '0' || $mode === '') return;
        if ($mode === '1' || $mode === '2') break;
    }

    $energyPerHit = ($mode === '2') ? 5 : 1;

    $login = ensure_login($CONFIG['email'], $CONFIG['password']);
    if (!$login) { fail("Login failed"); sleep(2); return; }
    $access_token = $login['access_token'];

    $hits = 0; $dmgTotal = 0; $critTotal = 0;
    $lastHp = null; $lastMax = null;
    $lastPool = 0; $lastEst = 0; $lastShare = 0;
    $lastEnergy = null;

    section("[ ATTACKING BOSS ]");

    while (true) {
        $res = api_post("/api/game/attack", ["count" => $energyPerHit, "useMaxEnergy" => false]);

        if (!is_array($res) || empty($res['ok'])) {
            $msg = strtolower((string)($res['msg'] ?? $res['message'] ?? $res['error'] ?? 'error'));
            if (strpos($msg, 'energy') !== false || strpos($msg, 'insufficient') !== false) {
                warn("Energy not enough");
                break;
            }
            fail("Error: " . substr($msg, 0, 60));
            sleep(2); continue;
        }

        $hits++;
        $damage = intval($res['damage'] ?? 0);
        $crit = !empty($res['crit']);
        $critCount = intval($res['critCount'] ?? 0);
        $dmgTotal += $damage;
        $critTotal += $critCount;

        $game = $res['game'] ?? [];
        $boss = $game['boss'] ?? [];
        $player = $game['player'] ?? [];

        if (isset($boss['health']))    $lastHp = intval($boss['health']);
        if (isset($boss['maxHealth'])) $lastMax = intval($boss['maxHealth']);
        if (isset($boss['rewardPool']))$lastPool = floatval($boss['rewardPool']);
        if (isset($player['energy']))  $lastEnergy = intval($player['energy']);
        if (isset($player['estimatedReward'])) $lastEst = floatval($player['estimatedReward']);
        if (isset($player['rewardSharePct']))  $lastShare = floatval($player['rewardSharePct']) * 100;

        $critMark = $crit ? NEON_YELLOW . " [CRIT]" . RESET : "       ";

        echo NEON_GRAY . "#" . str_pad($hits, 4, " ", STR_PAD_LEFT) . RESET
            . " " . NEON_WHITE . "D:" . NEON_RED . str_pad(number_format($damage), 6) . RESET
            . $critMark
            . " " . NEON_WHITE . "E:" . NEON_GREEN . str_pad($lastEnergy ?? '?', 4) . RESET
            . " " . _boss_hp_bar($lastHp, $lastMax, 8)
            . " " . NEON_YELLOW . str_pad(_fmt_big($lastHp), 7) . RESET
            . " " . NEON_YELLOW . str_pad(_fmt_big($lastPool) . "c", 8) . RESET
            . " " . NEON_GREEN . str_pad(number_format($lastEst, 2) . "c", 9) . RESET
            . " " . NEON_CYAN . number_format($lastShare, 3) . "%" . RESET . "\n";
        flush();

        if (!empty($res['defeated']) || (isset($boss['alive']) && $boss['alive'] === false)) {
            echo "\n" . NEON_GREEN . BOLD . "[✓] BOSS DEFEATED!" . RESET . "\n";
            break;
        }

        if ($lastEnergy !== null && $lastEnergy < $energyPerHit) {
            warn("Energy habis (E=" . $lastEnergy . ")");
            break;
        }

        usleep(700000);
    }

    echo "\n" . NEON_CYAN . "[ Summary ]" . RESET . " hits: " . NEON_GREEN . $hits . RESET . " | dmg: " . NEON_RED . number_format($dmgTotal) . RESET . " | crit: " . NEON_YELLOW . $critTotal . RESET . " | share: " . NEON_CYAN . number_format($lastShare, 3) . "%" . RESET . "\n";
    echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
    fgets(STDIN);
}

// ═══════════════ BATTLE PASS ═══════════════
function menu_battlepass($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ BATTLE PASS AUTO CLAIM ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    $login = ensure_login($CONFIG['email'], $CONFIG['password']);
    if (!$login) { fail("Login failed"); sleep(2); return; }
    $access_token = $login['access_token'];

    $bp = api_get("/api/battlepass");
    if (!is_array($bp) || isset($bp['error'])) {
        fail("Fetch battle pass failed");
        sleep(2); return;
    }

    $level = pretty_num($bp['level'] ?? ($bp['progress']['level'] ?? '?'));
    $xp    = pretty_num($bp['xp'] ?? ($bp['progress']['xp'] ?? '?'));
    echo NEON_WHITE . "Level : " . NEON_YELLOW . $level . RESET . " | XP : " . NEON_GREEN . $xp . RESET . "\n";

    $tasks = [];
    foreach (['tasks', 'missions', 'dailyTasks', 'weeklyTasks', 'daily', 'weekly', 'premiumTasks'] as $k) {
        if (isset($bp[$k]) && is_array($bp[$k])) {
            foreach ($bp[$k] as $t) { if (is_array($t)) $tasks[] = $t; }
        }
    }
    $rewards = [];
    foreach (['rewards', 'tiers', 'levels', 'track', 'milestones'] as $k) {
        if (isset($bp[$k]) && is_array($bp[$k])) {
            foreach ($bp[$k] as $r) { if (is_array($r)) $rewards[] = $r; }
        }
    }

    $tasksClaimed = 0; $gXp = 0; $gCoins = 0; $gEnergy = 0;
    section("[ TASKS ]");
    foreach ($tasks as $t) {
        $id = $t['id'] ?? ($t['taskId'] ?? null);
        if (!$id) continue;
        $complete = !empty($t['completed']) || !empty($t['complete']) || !empty($t['ready']);
        $claimed  = !empty($t['claimed']);
        if (!$complete || $claimed) continue;

        $res = api_post("/api/battlepass/tasks/claim", ['taskId' => $id]);
        if (is_array($res) && ($res['ok'] ?? true) !== false) {
            $tasksClaimed++;
            $rw = $res['reward'] ?? [];
            $xpGained = $rw['xp'] ?? 0;
            ok($id . "  " . NEON_GREEN . "+" . $xpGained . " BP XP" . RESET);
            $gXp += $xpGained;
            $gCoins += $rw['coins'] ?? 0;
            $gEnergy += $rw['energy'] ?? 0;
        }
        usleep(200000);
    }

    $rewardsClaimed = 0;
    section("[ REWARDS ]");
    foreach ($rewards as $r) {
        $lvl = $r['level'] ?? ($r['tier'] ?? null);
        if (!$lvl) continue;
        foreach (['free', 'premium'] as $track) {
            $trackData = $r[$track] ?? null;
            if (!is_array($trackData)) continue;
            $claimed = !empty($trackData['claimed']);
            $ready   = !empty($trackData['ready']) || !empty($trackData['unlocked']);
            if (!$ready && empty($trackData['locked'])) $ready = true;
            if ($claimed || !$ready) continue;

            $res = api_post("/api/battlepass/rewards/claim", ['level' => (int)$lvl, 'track' => $track]);
            if (is_array($res) && ($res['ok'] ?? true) !== false) {
                $rewardsClaimed++;
                $rw = $res['reward'] ?? [];
                $gXp += $rw['xp'] ?? 0;
                $gCoins += $rw['coins'] ?? 0;
                $gEnergy += $rw['energy'] ?? 0;
            }
            usleep(200000);
        }
    }

    echo "\n" . NEON_CYAN . "[ Summary ]" . RESET . " tasks: " . NEON_GREEN . $tasksClaimed . RESET . " | rewards: " . NEON_GREEN . $rewardsClaimed . RESET . " | " . NEON_GREEN . "+" . $gXp . "xp" . RESET . " | " . NEON_YELLOW . "+" . fmt_coin($gCoins) . "c" . RESET . " | " . NEON_GREEN . "+" . $gEnergy . "energy" . RESET . "\n";
    echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
    fgets(STDIN);
}

// ═══════════════ WITHDRAW ═══════════════
function menu_withdraw($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    $methods = [
        '1'  => ['key' => 'faucetpay_btc',  'label' => 'FaucetPay BTC',   'targetHint' => 'email'],
        '2'  => ['key' => 'faucetpay_ltc',  'label' => 'FaucetPay LTC',   'targetHint' => 'email'],
        '3'  => ['key' => 'faucetpay_doge', 'label' => 'FaucetPay DOGE',  'targetHint' => 'email'],
        '4'  => ['key' => 'faucetpay_usdc', 'label' => 'FaucetPay USDC',  'targetHint' => 'email'],
        '5'  => ['key' => 'faucetpay_sol',  'label' => 'FaucetPay SOL',   'targetHint' => 'email'],
        '6'  => ['key' => 'faucetpay_eth',  'label' => 'FaucetPay ETH',   'targetHint' => 'email'],
        '7'  => ['key' => 'lightning',      'label' => 'BTC Lightning',   'targetHint' => 'lightning address'],
        '8'  => ['key' => 'bitcoin',        'label' => 'Bitcoin (-2%)',   'targetHint' => 'BTC address'],
        '9'  => ['key' => 'litecoin',       'label' => 'Litecoin (-100)', 'targetHint' => 'LTC address'],
        '10' => ['key' => 'solana',         'label' => 'Solana (-100)',   'targetHint' => 'SOL address'],
        '11' => ['key' => 'paypal',         'label' => 'PayPal (-5%)',    'targetHint' => 'email'],
        '12' => ['key' => 'cxl_wallet',     'label' => 'CXL Wallet',      'targetHint' => 'email'],
    ];

    while (true) {
        clear(); banner();
        echo NEON_MAGENTA . BOLD . "[ AUTO WITHDRAW ]" . RESET . "\n";
        echo NEON_CYAN . "==================================================" . RESET . "\n";
        foreach ($methods as $k => $m) {
            echo NEON_GREEN . "[" . str_pad($k, 2, " ", STR_PAD_LEFT) . "] " . RESET . NEON_YELLOW . $m['label'] . RESET . "\n";
        }
        echo NEON_RED . "[ 0] " . RESET . "Back\n";
        echo "\n" . NEON_WHITE . "Pilih : " . NEON_YELLOW;
        $choice = trim(fgets(STDIN));
        if ($choice === '0' || $choice === '') return;
        if (isset($methods[$choice])) {
            $methodKey  = $methods[$choice]['key'];
            $methodLabel= $methods[$choice]['label'];
            $targetHint = $methods[$choice]['targetHint'];
            break;
        }
    }

    echo "\n" . NEON_WHITE . "Target (" . $targetHint . "): " . NEON_YELLOW;
    $target = trim(fgets(STDIN));
    if ($target === '') { fail("Cancelled"); sleep(2); return; }

    $login = ensure_login($CONFIG['email'], $CONFIG['password']);
    if (!$login) { fail("Login failed"); sleep(2); return; }
    $access_token = $login['access_token'];

    $w = api_get("/api/wallet");
    if (!is_array($w) || empty($w['ok'])) { fail("Fetch wallet failed"); sleep(2); return; }

    $wallet = $w['wallet'] ?? [];
    $balance = floatval($wallet['balance'] ?? 0);
    $minWithdraw = intval($wallet['minimumWithdrawalCoins'] ?? 1000);

    $min = $minWithdraw;
    if ($methodKey === 'bitcoin')      $min = intval($wallet['bitcoinMinimumWithdrawalCoins'] ?? 30000);
    elseif ($methodKey === 'paypal')   $min = intval($wallet['paypalMinimumWithdrawalCoins'] ?? 50000);
    elseif (in_array($methodKey, ['litecoin', 'solana']))
                                        $min = intval($wallet['directWalletMinimumWithdrawalCoins'] ?? 10000);

    $amount = (int)floor($balance);
    if (in_array($methodKey, ['litecoin', 'solana'])) $amount -= 100;

    echo "\n" . NEON_WHITE . "Balance : " . NEON_GREEN . number_format($balance, 4) . RESET . " | Min : " . NEON_YELLOW . number_format($min) . RESET . " | Amount : " . NEON_GREEN . number_format($amount) . RESET . "\n";

    if ($amount < $min) {
        warn("Balance below minimum");
        echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
        fgets(STDIN); return;
    }

    info("Sending request...");
    $res = api_post("/api/withdrawals", ["method" => $methodKey, "target" => $target, "amount" => $amount]);

    if (is_array($res) && !empty($res['ok'])) {
        $wid = $res['withdrawalId'] ?? '?';
        $snap = $res['snapshot'] ?? [];
        good("WD Success! ID : " . NEON_CYAN . substr($wid, 0, 8) . "..." . RESET);
        echo NEON_GREEN . "[+] Amount : " . number_format($amount) . "c" . RESET . " | " . NEON_WHITE . "New Bal : " . NEON_GREEN . pretty_num($snap['balance'] ?? '?') . RESET . "\n";
    } else {
        $msg = $res['msg'] ?? $res['message'] ?? $res['error'] ?? 'Unknown';
        fail("Failed: " . substr($msg, 0, 60));
    }

    echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
    fgets(STDIN);
}

function menu_wd_history($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    $login = ensure_login($CONFIG['email'], $CONFIG['password']);
    if (!$login) { fail("Login failed"); sleep(2); return; }
    $access_token = $login['access_token'];

    $w = api_get("/api/wallet");
    if (!is_array($w) || empty($w['ok'])) { fail("Fetch wallet failed"); sleep(2); return; }

    $wallet = $w['wallet'] ?? [];
    echo NEON_MAGENTA . BOLD . "[ WITHDRAW HISTORY ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";
    echo NEON_WHITE . "Balance : " . NEON_GREEN . pretty_num($wallet['balance'] ?? 0) . "c" . RESET . "\n";

    $wds = $w['withdrawals'] ?? [];
    if (empty($wds)) {
        warn("No withdrawals yet");
        echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
        fgets(STDIN); return;
    }

    echo NEON_CYAN . "--------------------------------------------------" . RESET . "\n";
    echo NEON_CYAN . "#  | Date       | Method         | Amount   | Status" . RESET . "\n";
    echo NEON_CYAN . "--------------------------------------------------" . RESET . "\n";

    $i = 1;
    foreach (array_slice($wds, 0, 10) as $wd) {
        $date   = isset($wd['requestedAt']) ? substr($wd['requestedAt'], 0, 10) : '?';
        $method = substr($wd['method'] ?? '?', 0, 14);
        $amt    = number_format(intval($wd['amount'] ?? 0));
        $status = $wd['status'] ?? '?';
        $stColor = NEON_YELLOW;
        if ($status === 'paid') $stColor = NEON_GREEN;
        elseif (in_array($status, ['rejected', 'failed'])) $stColor = NEON_RED;
        echo NEON_GRAY . str_pad($i, 2, " ", STR_PAD_LEFT) . RESET
            . " | " . NEON_CYAN . str_pad($date, 10, " ") . RESET
            . " | " . NEON_MAGENTA . str_pad($method, 14, " ") . RESET
            . " | " . NEON_YELLOW . str_pad($amt, 8, " ", STR_PAD_LEFT) . RESET
            . " | " . $stColor . $status . RESET . "\n";
        $i++;
    }
    echo NEON_CYAN . "--------------------------------------------------" . RESET . "\n";

    $totalPaid = 0; $countPaid = 0; $totalPending = 0;
    foreach ($wds as $wd) {
        $st = $wd['status'] ?? '';
        if ($st === 'paid') { $totalPaid += floatval($wd['amount'] ?? 0); $countPaid++; }
        elseif ($st === 'pending') { $totalPending += floatval($wd['amount'] ?? 0); }
    }
    echo NEON_WHITE . "Total PAID    : " . NEON_GREEN . number_format($totalPaid) . "c" . RESET . " (" . $countPaid . " tx)\n";
    if ($totalPending > 0) echo NEON_WHITE . "Total PENDING : " . NEON_YELLOW . number_format($totalPending) . "c" . RESET . "\n";

    echo "\n" . NEON_YELLOW . "Press Enter to return..." . RESET;
    fgets(STDIN);
}

// ═══════════════ SETTINGS ═══════════════
function menu_set_account($configFile) {
    global $CONFIG;
    clear(); banner();
    echo NEON_MAGENTA . BOLD . "[ SET AKUN ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";
    echo NEON_WHITE . "Email saat ini : " . NEON_YELLOW . ($CONFIG['email'] ?: '(kosong)') . RESET . "\n";
    echo NEON_WHITE . "Proxy saat ini : " . NEON_YELLOW . maskProxy($CONFIG['proxy'] ?? '') . RESET . "\n\n";
    echo NEON_WHITE . "Email baru (Enter = tetap)    : " . NEON_YELLOW; $email = trim(fgets(STDIN));
    if ($email !== '') {
        echo NEON_WHITE . "Password baru (Enter = tetap) : " . NEON_YELLOW; $password = trim(fgets(STDIN));
        echo NEON_WHITE . "Proxy baru (Enter = hapus)    : " . NEON_YELLOW; $proxy = trim(fgets(STDIN));
        $CONFIG['email']    = $email;
        $CONFIG['password'] = $password;
        $CONFIG['proxy']    = $proxy;
        del_token($email);
        saveConfig($configFile);
        echo "\n" . NEON_GREEN . "[✓] Akun updated" . RESET . "\n";
    } else {
        echo NEON_WHITE . "Proxy baru (Enter = hapus)    : " . NEON_YELLOW; $proxy = trim(fgets(STDIN));
        $CONFIG['proxy'] = $proxy;
        saveConfig($configFile);
        echo "\n" . NEON_GREEN . "[✓] Proxy updated" . RESET . "\n";
    }
    sleep(2);
}

function menu_set_apikey($configFile) {
    global $CONFIG;
    clear(); banner();
    echo NEON_MAGENTA . BOLD . "[ SET API KEY WARYONO ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";
    $cur = $CONFIG['apikey'] ?? '';
    echo NEON_WHITE . "Key saat ini : " . NEON_YELLOW . (strlen($cur) > 8 ? substr($cur, 0, 8) . "..." : ($cur ?: '(kosong)')) . RESET . "\n\n";
    echo NEON_WHITE . "Key baru (Enter = batal) : " . NEON_YELLOW;
    $k = trim(fgets(STDIN));
    if ($k === "") { fail("Cancelled"); sleep(2); return; }
    $CONFIG['apikey'] = $k;
    saveConfig($configFile);
    good("Saved");
    sleep(2);
}

// ═══════════════ MAIN MENU ═══════════════
function main_menu($configFile) {
    global $CONFIG, $access_token, $handling_interrupt;

    while (true) {
        try {
            clear();
            banner();

            $mk = (strlen($CONFIG['apikey']) > 10)
                ? substr($CONFIG['apikey'], 0, 8) . "..." . substr($CONFIG['apikey'], -4)
                : ($CONFIG['apikey'] ?: "(kosong)");

            $accDisplay = $CONFIG['email'] ? maskEmail($CONFIG['email']) : NEON_RED . "(belum di-set)" . RESET;

            $balance = '-';
            $level = '-';
            if (!empty($CONFIG['email'])) {
                setupSession();
                $me = api_get("/api/me");
                if (is_array($me) && !isset($me['error'])) {
                    $balance = pretty_num($me['balance'] ?? $me['coins'] ?? '-');
                    $level = pretty_num($me['level']['level'] ?? $me['level'] ?? '-');
                }
            }

            echo NEON_MAGENTA . BOLD . "[ ACCOUNT INFO ]" . RESET . "\n";
            echo NEON_CYAN . "==================================================" . RESET . "\n";
            echo NEON_WHITE . "Akun     : " . NEON_YELLOW . $accDisplay . RESET . "\n";
            echo NEON_WHITE . "Balance  : " . NEON_GREEN . $balance . RESET . "\n";
            echo NEON_WHITE . "Level    : " . NEON_BLUE . $level . RESET . "\n";
            echo NEON_WHITE . "Provider : " . NEON_GREEN . "MoneyMaker_w (Waryono)" . RESET . "\n";
            echo NEON_WHITE . "API Key  : " . NEON_MAGENTA . $mk . RESET . "\n";
            echo NEON_CYAN . "==================================================" . RESET . "\n\n";

            echo NEON_MAGENTA . BOLD . "[ PILIH MENU ]" . RESET . "\n";
            echo NEON_CYAN . "==================================================" . RESET . "\n";
            echo NEON_GREEN  . "[1]  " . RESET . NEON_YELLOW . BOLD . "🌾  AUTO FARMING ALL (RECOMMENDED)" . RESET . "\n";
            echo NEON_GREEN  . "[2]  " . RESET . "Claim Faucet + Quest + Daily\n";
            echo NEON_GREEN  . "[3]  " . RESET . "Auto Daily Bonus 🎁\n";
            echo NEON_GREEN  . "[4]  " . RESET . "Auto Minigames 🎮\n";
            echo NEON_GREEN  . "[5]  " . RESET . "Auto Claim Quest 📋\n";
            echo NEON_GREEN  . "[6]  " . RESET . "Attack Boss ⚔️\n";
            echo NEON_GREEN  . "[7]  " . RESET . "PTC Auto Claim (BitcoTasks) 💰\n";
            echo NEON_GREEN  . "[8]  " . RESET . "Battle Pass Auto Claim 🎫\n";
            echo NEON_GREEN  . "[9]  " . RESET . "Auto Withdraw 💸\n";
            echo NEON_GREEN  . "[10] " . RESET . "Withdraw History 📜\n";
            echo NEON_GREEN  . "[11] " . RESET . "Set Akun\n";
            echo NEON_GREEN  . "[12] " . RESET . "Set API Key (Waryono)\n";
            echo NEON_RED    . "[0]  " . RESET . "Keluar\n";
            echo NEON_CYAN . "==================================================" . RESET . "\n";
            echo "\n" . NEON_WHITE . "Pilih (0-12): " . NEON_YELLOW;

            $choice = trim(fgets(STDIN));

            switch ($choice) {
                case '1':  menu_autofarm($configFile); break;
                case '2':  menu_faucet($configFile); break;
                case '3':  menu_daily($configFile); break;
                case '4':  menu_minigames($configFile); break;
                case '5':  menu_claim_quest($configFile); break;
                case '6':  menu_boss($configFile); break;
                case '7':  menu_ptc_all($configFile); break;
                case '8':  menu_battlepass($configFile); break;
                case '9':  menu_withdraw($configFile); break;
                case '10': menu_wd_history($configFile); break;
                case '11': menu_set_account($configFile); break;
                case '12': menu_set_apikey($configFile); break;
                case '0':  echo "\n" . NEON_GREEN . "Terima kasih!" . RESET . "\n"; exit;
                default:   fail("Invalid"); fgets(STDIN); break;
            }

        } catch (UserInterrupt $e) {
            echo "\n" . NEON_YELLOW . "Press Enter..." . RESET;
            @fgets(STDIN);
            $handling_interrupt = false;
        } catch (EnergyOut $e) {
            echo "\n" . NEON_RED . "[!] Energy habis!" . RESET . "\n";
            echo NEON_YELLOW . "Press Enter..." . RESET;
            @fgets(STDIN);
        }
    }
}

// ═══════════════ PTC MENU (FULL LOOP) ═══════════════
function menu_ptc_all($configFile) {
    global $CONFIG, $access_token;
    clear(); banner();
    if (empty($CONFIG['email'])) { fail("Akun belum di-set."); sleep(2); return; }
    setupSession();

    echo NEON_MAGENTA . BOLD . "[ MODE : BITCOTASKS FULL LOOP ]" . RESET . "\n";
    echo NEON_CYAN . "==================================================" . RESET . "\n";

    while (true) {
        $login = ensure_login($CONFIG['email'], $CONFIG['password']);
        if (!$login) { fail("Login failed. Retry 10s..."); sleep(10); continue; }
        $access_token = $login['access_token'];

        section("[ BITCOTASKS — " . date('H:i:s') . " ]");
        $res = run_ptc_all_tasks($CONFIG);

        echo "\n" . NEON_YELLOW . "[!] Wait 60s for next batch..." . RESET . "\n";
        bar_timer(60, "  ");
    }
}

// ═══════════════ BOOT ═══════════════
register_shutdown_function(function() { echo "\r\033[K"; });

if (function_exists('pcntl_async_signals') && function_exists('pcntl_signal') && defined('SIGINT')) {
    pcntl_async_signals(true);
    pcntl_signal(SIGINT, function() {
        if (!empty($GLOBALS['handling_interrupt'])) { exit(1); }
        $GLOBALS['handling_interrupt'] = true;
        throw new UserInterrupt();
    });
}

hacker_intro();
echo NEON_CYAN;
typewrite("[+] Installing bitcotasks bot...", 0.015);
typewrite("[+] Installing auto boss attack...", 0.015);
typewrite("[+] Installing auto farming engine...", 0.015);
typewrite("[+] Installing auto withdraw...", 0.015);
typewrite("[+] Minigames: wait-duration fix applied.", 0.015);
typewrite("[+] Bar timer active (▓▓▓ style).", 0.015);
typewrite("[+] Moon animation: REMOVED.", 0.015);
typewrite("[+] BitcoTasks: process ALL tasks.", 0.015);
typewrite("[+] Error auto-handle: ENABLED.", 0.015);
typewrite("[+] Single-account engine ready...", 0.015);
echo RESET;

loadConfig($configFile);
main_menu($configFile);
