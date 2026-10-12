<?php
/**
 * CLAIMX AUTO CLAIM BOT v9.0
 * + Auto-detect VIP (limit 100 → 300)
 * + Unlimited mode (pop-faucet, no limit)
 * + Auto-switch mode kalau limit reached
 */

error_reporting(E_ALL & ~E_WARNING & ~E_NOTICE & ~E_DEPRECATED);
date_default_timezone_set('Asia/Jakarta');

// ─── COLOR ───
define('RESET', "\033[0m");
define('RED',   "\033[31m");
define('GREEN', "\033[32m");
define('YELLOW',"\033[33m");
define('CYAN',  "\033[36m");
define('WHITE', "\033[37m");
define('GRAY',  "\033[90m");
define('B_RED',   "\033[1;31m");
define('B_GREEN', "\033[1;32m");
define('B_YELLOW',"\033[1;33m");
define('B_CYAN',  "\033[1;36m");
define('B_WHITE', "\033[1;37m");
define('B_MAGENTA',"\033[1;35m");
define('DIM',     "\033[2m");

// ─── CONFIG ───
const HOST = 'https://claimx.online';
const MAX_DAILY_CLAIMS_DEFAULT = 100;
const MAX_DAILY_CLAIMS_VIP = 300;
const CONFIG_FILE = 'claimx_config.json';
const COOKIE_FILE = 'claimx_cookie.txt';
const DAILY_FILE  = 'claimx_daily.txt';
const AD_VIEW_SECONDS = 6;
const POP_VIEW_SECONDS = 10;
const MIN_CLAIM_DELAY = 3;
const MAX_CLAIM_DELAY = 6;

// ═══════════════ UTILS ═══════════════
function clearScreen() { (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w')); }

function printBanner() {
    clearScreen();
    echo B_CYAN . "==================================================\n";
    echo B_CYAN . "  " . B_WHITE . "ClaimX Auto Claim Bot v9.0" . B_CYAN . "  \n";
    echo B_CYAN . "==================================================\n";
    echo B_CYAN . "  Unlimited Faucet + VIP Auto-Detect\n";
    echo B_CYAN . "  Regular: 100/day  |  VIP: 300/day\n";
    echo B_CYAN . "  Unlimited Mode: no daily limit\n";
    echo B_CYAN . "==================================================\n\n";
}

function timer($seconds, $prefix = "Waiting") {
    $w = (int)$seconds;
    if ($w <= 0) return;
    $f = ['⣾','⣽','⣻','⢿','⡿','⣟','⣯','⣷'];
    $i = 0;
    while ($w > 0) {
        $tf = sprintf('%02d:%02d:%02d', floor($w/3600), floor(($w%3600)/60), $w%60);
        echo "\r" . B_YELLOW . "  ⏳ {$prefix}: " . B_WHITE . $tf . " " . $f[$i] . "   " . RESET;
        sleep(1); $w--; $i = ($i + 1) % count($f);
    }
    echo "\r" . str_repeat(" ", 60) . "\r";
}

// ═══════════════ HTTP ═══════════════
function req($url, $method = 'GET', $post = null, $extra = []) {
    $ch = curl_init();
    $headers = array_merge([
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language: id-ID,id;q=0.9,en;q=0.8',
        'Accept-Encoding: gzip, deflate, br',
        'Connection: keep-alive',
        'Upgrade-Insecure-Requests: 1',
    ], $extra);
    curl_setopt_array($ch, [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 10,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_COOKIEFILE => COOKIE_FILE,
        CURLOPT_COOKIEJAR  => COOKIE_FILE,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_ENCODING => '',
    ]);
    if (strtoupper($method) === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    }
    $r = curl_exec($ch);
    $errno = curl_errno($ch);
    $errmsg = curl_error($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $GLOBALS['LAST_REQ'] = [
        'url' => $url,
        'errno' => $errno,
        'errmsg' => $errmsg,
        'code' => $httpCode,
        'len' => is_string($r) ? strlen($r) : 0,
    ];

    if ($errno) return false;
    return $r;
}

function reqNoFollow($url, $post = null, $extra = []) {
    $ch = curl_init();
    $headers = array_merge([
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'Accept: */*',
        'Accept-Language: id-ID,id;q=0.9,en;q=0.8',
        'Accept-Encoding: gzip, deflate, br',
        'Connection: keep-alive',
        'X-Requested-With: XMLHttpRequest',
    ], $extra);
    curl_setopt_array($ch, [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_COOKIEFILE => COOKIE_FILE,
        CURLOPT_COOKIEJAR  => COOKIE_FILE,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_ENCODING => '',
    ]);
    if ($post !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    }
    $r = curl_exec($ch);
    $errno = curl_errno($ch);
    curl_close($ch);
    return $errno ? false : $r;
}

// ═══════════════ PARSERS ═══════════════
function parseCSRF($html) {
    if (preg_match('/<input[^>]*name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']/i', $html, $m)) return $m[1];
    if (preg_match('/csrf_token\s*[:=]\s*["\']([^"\']+)["\']/i', $html, $m)) return $m[1];
    return null;
}

function parseIconCaptcha($html) {
    $target = null;
    $choices = [];

    // Target: cari div dengan class yang mengandung text-warning / border-warning
    if (preg_match_all('/<div[^>]*class=["\'][^"\']*(?:text-warning|border-warning)[^"\']*["\'][^>]*>\s*<i[^>]*class=["\']([^"\']+)["\'][^>]*>\s*<\/i>/si', $html, $ms)) {
        foreach ($ms[1] as $cls) {
            if (preg_match('/\bbi-[a-z0-9\-]+/i', $cls, $ic)) {
                $target = $ic[0];
                break;
            }
        }
    }

    // Choices: button dengan data-key
    if (preg_match_all('/<button[^>]*class=["\'][^"\']*icon-captcha-btn[^"\']*["\'][^>]*data-key=["\']([^"\']+)["\'][^>]*>(.*?)<\/button>/si', $html, $ms, PREG_SET_ORDER)) {
        foreach ($ms as $m) {
            $key = $m[1];
            $inner = $m[2];
            if (preg_match('/<i[^>]*class=["\']([^"\']*bi-[a-z0-9\-]+[^"\']*)["\']/i', $inner, $ic)) {
                if (preg_match('/\bbi-[a-z0-9\-]+/i', $ic[1], $only)) {
                    $choices[] = ['key' => $key, 'icon' => $only[0]];
                }
            }
        }
    }

    return [$target, $choices];
}

function matchIcon($target, $choices) {
    if (!$target || empty($choices)) return null;

    $targetIcon = preg_match('/\bbi-[a-z0-9\-]+/i', $target, $m) ? $m[0] : $target;

    foreach ($choices as $c) {
        if (strcasecmp($targetIcon, $c['icon']) === 0) return $c['key'];
    }
    $targetPart = preg_replace('/^bi-/', '', $targetIcon);
    foreach ($choices as $c) {
        $choicePart = preg_replace('/^bi-/', '', $c['icon']);
        if (strcasecmp($targetPart, $choicePart) === 0) return $c['key'];
    }
    return null;
}

/**
 * Auto-detect VIP status dari HTML page.
 * Return: ['vip'=>bool, 'tier'=>string, 'limit'=>int]
 */
function detectVIP($html) {
    $vip = false;
    $tier = 'Free';
    $limit = MAX_DAILY_CLAIMS_DEFAULT;

    // Cari badge VIP / plan name
    $vipKeywords = [
        'VIP Member', 'VIP Member Active', 'Premium', 'PRO Plan',
        'VIP Plan', 'Plan: VIP', 'Membership: VIP',
        'badge-vip', 'vip-badge', 'plan-vip',
        'bi-gem-fill text-warning', // VIP icon di navbar
    ];

    foreach ($vipKeywords as $kw) {
        if (stripos($html, $kw) !== false) {
            $vip = true;
            break;
        }
    }

    // Cari tier spesifik
    if (preg_match('/(?:VIP|Premium|PRO|Plan)[\s:]*(?:<[^>]+>)*([A-Za-z0-9 ]+?)(?:<|\n|$)/i', $html, $m)) {
        $tier = trim($m[1]);
    }

    // Cari daily limit yang tertulis di page
    if (preg_match('/daily\s+limit[^0-9]*(\d+)/i', $html, $m)) {
        $limit = (int)$m[1];
    }
    if (preg_match('/(\d+)\s*(?:claims?|claim).*?(?:per|\/)\s*day/i', $html, $m)) {
        $limit = (int)$m[1];
    }
    if (preg_match('/remaining.*?(\d+)\s*(?:of|\/)\s*(\d+)/i', $html, $m)) {
        $limit = (int)$m[2];
    }

    // Kalau ketemu badge VIP, naikin limit
    if ($vip && $limit <= MAX_DAILY_CLAIMS_DEFAULT) {
        $limit = MAX_DAILY_CLAIMS_VIP;
    }

    return ['vip' => $vip, 'tier' => $tier, 'limit' => $limit];
}

function isLoginPage($html) {
    return strpos($html, 'FaucetPay Email Address') !== false
        && strpos($html, 'Enter Faucet Portal') !== false;
}

function isCooldownPage($html) {
    return strpos($html, 'countdownClock') !== false
        || strpos($html, 'Faucet Cooling Down') !== false;
}

function isReadyToClaim($html) {
    return strpos($html, 'id="faucetForm"') !== false
        || strpos($html, 'id="popFaucetForm"') !== false;
}

function parseCooldownSeconds($html) {
    if (preg_match('/id="countdownClock"[^>]*data-seconds=["\']?(\d+)/i', $html, $m)) {
        return (int)$m[1];
    }
    return 0;
}

function isPopFaucet($html) {
    return strpos($html, 'id="popFaucetForm"') !== false
        || strpos($html, 'Pop-Under Faucet') !== false;
}

// ═══════════════ DAILY ═══════════════
function getDailyCount() {
    if (file_exists(DAILY_FILE)) {
        $d = json_decode(file_get_contents(DAILY_FILE), true);
        if (($d['date'] ?? '') === date('Y-m-d')) return (int)$d['count'];
    }
    return 0;
}
function updateDailyCount($c) {
    file_put_contents(DAILY_FILE, json_encode(['date'=>date('Y-m-d'), 'count'=>$c]));
}
function resetDailyIfNeeded() {
    if (file_exists(DAILY_FILE)) {
        $d = json_decode(file_get_contents(DAILY_FILE), true);
        if (($d['date'] ?? '') !== date('Y-m-d')) { updateDailyCount(0); return true; }
    }
    return false;
}

function getBalance() {
    $html = req(HOST . '/dashboard');
    if (!$html) return '0.00000000';
    $pats = [
        '/Earnings Balance.*?<h3[^>]*class="[^"]*fs-4[^"]*"[^>]*>([0-9.]+)/si',
        '/Earnings Balance<\/p>\s*<h3[^>]*>([0-9.]+)/si',
        '/balance[^>]*>([0-9.]+)/si',
    ];
    foreach ($pats as $p) if (preg_match($p, $html, $m)) return trim($m[1]);
    return '0.00000000';
}

function checkDailyLimit($html) {
    return strpos($html, 'Daily Limit Reached') !== false
        || strpos($html, 'You have completed all') !== false
        || strpos($html, 'Upgrade Membership') !== false;
}

// ═══════════════ LOGIN ═══════════════
function doLogin($email, $password) {
    echo B_CYAN . "  [LOGIN] Attempting login...\n" . RESET;

    if (file_exists(COOKIE_FILE)) @unlink(COOKIE_FILE);

    $html = false;
    for ($i = 1; $i <= 3; $i++) {
        $html = req(HOST . '/login');
        if ($html && strlen($html) > 500) break;
        echo "  " . B_YELLOW . "[retry $i/3] fetch /login gagal, tunggu 5s..." . RESET . "\n";
        sleep(5);
    }

    if (!$html || strlen($html) < 500) {
        echo B_RED . "  [ERROR] Gagal fetch /login\n" . RESET;
        return false;
    }

    $csrf = parseCSRF($html);
    if (!$csrf) { echo B_RED . "  [ERROR] CSRF login ga ketemu\n" . RESET; return false; }

    list($target, $choices) = parseIconCaptcha($html);
    if (!$target) { echo B_RED . "  [ERROR] Target icon login ga ketemu\n" . RESET; return false; }
    if (empty($choices)) { echo B_RED . "  [ERROR] Choices login kosong\n" . RESET; return false; }

    $key = matchIcon($target, $choices);
    if (!$key) {
        echo B_RED . "  [ERROR] Ikon login ga match\n" . RESET;
        echo "  " . DIM . "  target: {$target}\n";
        foreach ($choices as $c) echo "  " . DIM . "  choice: {$c['key']} = {$c['icon']}\n" . RESET;
        return false;
    }

    echo B_CYAN . "  [LOGIN] {$target} → {$key}\n" . RESET;

    $post = http_build_query([
        'csrf_token' => $csrf,
        'email' => $email,
        'password' => $password,
        'icon_captcha_selected' => $key
    ]);
    $r = req(HOST . '/login', 'POST', $post, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST,
        'Referer: ' . HOST . '/login',
    ]);
    if ($r === false) { echo B_RED . "  [ERROR] POST login gagal\n" . RESET; return false; }

    if (strpos($r, 'Welcome back') !== false || strpos($r, 'Dashboard') !== false) {
        echo B_GREEN . "  [SUCCESS] Login OK\n" . RESET;
        return true;
    }
    echo B_RED . "  [ERROR] Login reject\n" . RESET;
    return false;
}

// ═══════════════ AD-TOKEN ═══════════════
function fetchAdToken($csrf) {
    $body = 'csrf_token=' . urlencode($csrf);
    $r = reqNoFollow(HOST . '/faucet/verify-ad', $body, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST,
        'Referer: ' . HOST . '/faucet',
    ]);

    if ($r === false) return ['ok'=>false, 'raw'=>'curl failed'];

    $j = json_decode($r, true);
    if (is_array($j) && !empty($j['success']) && !empty($j['token'])) {
        return ['ok'=>true, 'token'=>$j['token'], 'raw'=>$r];
    }
    return ['ok'=>false, 'token'=>null, 'raw'=>$r];
}

// ═══════════════ CLAIM: REGULAR FAUCET ═══════════════
function claimFaucet(&$info) {
    $html = false;
    for ($try = 1; $try <= 3; $try++) {
        $html = req(HOST . '/faucet');
        if ($html && strlen($html) > 500) break;

        $dbg = $GLOBALS['LAST_REQ'] ?? [];
        echo "  " . B_YELLOW . "[fetch] try {$try}/3 gagal | "
             . "errno=" . ($dbg['errno'] ?? '?') . " code=" . ($dbg['code'] ?? '?')
             . " len=" . ($dbg['len'] ?? '?')
             . RESET . "\n";

        if ($try < 3) sleep(rand(3, 5));
    }

    if (!$html || strlen($html) < 500) {
        $dbg = $GLOBALS['LAST_REQ'] ?? [];
        $code = (int)($dbg['code'] ?? 0);
        if ($code == 0 || $code >= 500) {
            return ['cooldown' => 30];
        }
        if ($code == 200 && ($dbg['len'] ?? 0) < 500) {
            return 'session_invalid';
        }
        return 'fetch_fail';
    }

    if (isLoginPage($html)) return 'session_invalid';
    if (checkDailyLimit($html)) return 'limit_reached';

    if (!isReadyToClaim($html)) {
        if (isCooldownPage($html)) {
            $s = parseCooldownSeconds($html);
            return ['cooldown' => $s > 0 ? $s : 3];
        }
        return 'no_form';
    }

    $csrf = parseCSRF($html);
    if (!$csrf) return 'no_csrf';

    echo B_CYAN . "  [FAUCET] Regular claim processing...\n" . RESET;

    for ($i = AD_VIEW_SECONDS; $i > 0; $i--) {
        echo "\r  " . B_CYAN . "[AD] Viewing ad: " . B_WHITE . "{$i}s" . RESET . "   ";
        sleep(1);
    }
    echo "\r" . str_repeat(' ', 50) . "\r";

    $tokRes = fetchAdToken($csrf);
    if (!$tokRes['ok'] && stripos($tokRes['raw'], 'at least 5 seconds') !== false) {
        sleep(4);
        $tokRes = fetchAdToken($csrf);
    }

    if (!$tokRes['ok']) {
        return 'ad_token_fail';
    }

    $token = $tokRes['token'];

    $postArr = [
        'csrf_token' => $csrf,
        'ad_verification_token' => $token,
    ];

    list($target, $choices) = parseIconCaptcha($html);
    if ($target && !empty($choices)) {
        $key = matchIcon($target, $choices);
        if ($key) {
            echo B_CYAN . "  [CAPTCHA] {$target} → {$key}\n" . RESET;
            $postArr['icon_captcha_selected'] = $key;
        } else {
            return 'captcha_skip';
        }
    }

    $r = req(HOST . '/faucet/claim', 'POST', http_build_query($postArr), [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST,
        'Referer: ' . HOST . '/faucet',
    ]);
    if ($r === false) return 'fetch_fail';

    if (isLoginPage($r)) return 'session_invalid';
    if (checkDailyLimit($r)) return 'limit_reached';

    $amount = null;
    if (preg_match('/Claim successful!\s*Received\s*\+?([0-9.]+)\s*USDT/i', $r, $m)) {
        $amount = $m[1];
    } elseif (preg_match('/alert-success[^>]*>([^<]*?Received[^<]*?)</i', $r, $m)) {
        if (preg_match('/([0-9.]+)/', $m[1], $n)) $amount = $n[1];
    }

    if ($amount) {
        echo B_GREEN . "  [SUCCESS] +{$amount} USDT\n" . RESET;
        $info = ['amount' => $amount];
        return true;
    }

    if (preg_match('/alert-(?:danger|warning)[^>]*>([^<]+)</i', $r, $m)) {
        $err = trim($m[1]);
        echo B_RED . "  [SERVER] {$err}\n" . RESET;
        if (stripos($err, 'adblock') !== false) return ['cooldown' => rand(30, 45)];
        if (stripos($err, 'wait') !== false || stripos($err, 'cooldown') !== false) {
            $cd = 3;
            if (preg_match('/(\d+)\s*second/i', $err, $s)) $cd = (int)$s[1];
            return ['cooldown' => $cd];
        }
        if (stripos($err, 'captcha') !== false || stripos($err, 'verification') !== false || stripos($err, 'token') !== false) {
            return 'captcha_skip';
        }
    }

    if (strlen($r) < 100) return 'fetch_fail';
    return 'unknown';
}

// ═══════════════ CLAIM: POP-UNDER / UNLIMITED FAUCET ═══════════════
function claimPopFaucet(&$info) {
    $html = false;
    for ($try = 1; $try <= 3; $try++) {
        $html = req(HOST . '/pop-faucet');
        if ($html && strlen($html) > 500) break;
        $dbg = $GLOBALS['LAST_REQ'] ?? [];
        echo "  " . B_YELLOW . "[fetch-pop] try {$try}/3 gagal | code="
             . ($dbg['code'] ?? '?') . " len=" . ($dbg['len'] ?? '?') . RESET . "\n";
        if ($try < 3) sleep(rand(3, 5));
    }

    if (!$html || strlen($html) < 500) {
        $dbg = $GLOBALS['LAST_REQ'] ?? [];
        $code = (int)($dbg['code'] ?? 0);
        if ($code == 0 || $code >= 500) return ['cooldown' => 30];
        if ($code == 200 && ($dbg['len'] ?? 0) < 500) return 'session_invalid';
        return 'fetch_fail';
    }

    if (isLoginPage($html)) return 'session_invalid';

    if (!isReadyToClaim($html)) {
        // pop-faucet kadang ke-redirect balik ke /faucet kalau ada cooldown
        if (isCooldownPage($html)) {
            $s = parseCooldownSeconds($html);
            return ['cooldown' => $s > 0 ? $s : 5];
        }
        return 'no_form';
    }

    $csrf = parseCSRF($html);
    if (!$csrf) return 'no_csrf';

    echo B_MAGENTA . "  [UNLIMITED] Pop-Under claim processing...\n" . RESET;

    // ── Icon captcha (WAJIB di pop-faucet) ──
    list($target, $choices) = parseIconCaptcha($html);
    if (!$target || empty($choices)) {
        echo B_YELLOW . "  [CAPTCHA-POP] target/choices kosong" . RESET . "\n";
        return 'captcha_skip';
    }
    $key = matchIcon($target, $choices);
    if (!$key) {
        echo B_YELLOW . "  [CAPTCHA-POP] ikon ga match" . RESET . "\n";
        return 'captcha_skip';
    }
    echo B_CYAN . "  [CAPTCHA-POP] {$target} → {$key}\n" . RESET;

    // ── Simulasi "view ad" 10 detik (server cuma tracking durasi) ──
    for ($i = POP_VIEW_SECONDS; $i > 0; $i--) {
        echo "\r  " . B_MAGENTA . "[POP-AD] Watching: " . B_WHITE . "{$i}s" . RESET . "   ";
        sleep(1);
    }
    echo "\r" . str_repeat(' ', 50) . "\r";

    // ── POST ke /pop-faucet/claim ──
    $postArr = [
        'csrf_token' => $csrf,
        'icon_captcha_selected' => $key,
    ];

    $r = req(HOST . '/pop-faucet/claim', 'POST', http_build_query($postArr), [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . HOST,
        'Referer: ' . HOST . '/pop-faucet',
    ]);
    if ($r === false) return 'fetch_fail';

    if (isLoginPage($r)) return 'session_invalid';

    // ── Parse result ──
    $amount = null;
    if (preg_match('/Pop-Under Faucet claim successful!\s*Received\s*\+?([0-9.]+)\s*USDT/i', $r, $m)) {
        $amount = $m[1];
    } elseif (preg_match('/alert-success[^>]*>([^<]*?Received[^<]*?)</i', $r, $m)) {
        if (preg_match('/([0-9.]+)/', $m[1], $n)) $amount = $n[1];
    } elseif (preg_match('/Received\s*\+?([0-9.]+)\s*USDT/i', $r, $m)) {
        $amount = $m[1];
    }

    if ($amount) {
        echo B_GREEN . "  [SUCCESS-UNLIMITED] +{$amount} USDT\n" . RESET;
        $info = ['amount' => $amount];
        return true;
    }

    // Error handling
    if (preg_match('/alert-(?:danger|warning)[^>]*>([^<]+)</i', $r, $m)) {
        $err = trim($m[1]);
        echo B_RED . "  [SERVER-POP] {$err}\n" . RESET;

        if (stripos($err, 'wait') !== false || stripos($err, 'cooldown') !== false) {
            $cd = 5;
            if (preg_match('/(\d+)\s*second/i', $err, $s)) $cd = (int)$s[1];
            return ['cooldown' => $cd];
        }
        if (stripos($err, 'captcha') !== false || stripos($err, 'token') !== false) {
            return 'captcha_skip';
        }
        if (stripos($err, 'ad') !== false && stripos($err, 'view') !== false) {
            // Server minta ad view dulu
            return ['cooldown' => 3];
        }
    }

    if (strlen($r) < 100) return 'fetch_fail';
    return 'unknown';
}

// ═══════════════ FARMING MODE ═══════════════
/**
 * $mode: 'regular' | 'unlimited' | 'auto'
 *  - regular   : cuma /faucet (100-300/day)
 *  - unlimited : cuma /pop-faucet (no limit)
 *  - auto      : coba regular dulu, kalau limit → switch unlimited
 */
function startFarming($email, $password, $mode = 'auto') {
    if (!doLogin($email, $password)) return;

    // ── VIP detection ──
    $dashHtml = req(HOST . '/dashboard');
    if (!$dashHtml) $dashHtml = '';
    $vipInfo = detectVIP($dashHtml);
    $isVip = $vipInfo['vip'];
    $maxDaily = $vipInfo['limit'];

    $balance = getBalance();
    $dailyCount = getDailyCount();

    echo B_CYAN . "  [ACCOUNT] " . B_WHITE . $email . RESET . "\n";
    echo B_CYAN . "  [VIP]     " . ($isVip ? B_GREEN . "YES ({$vipInfo['tier']})" : B_YELLOW . "NO (Free)") . RESET . "\n";
    echo B_CYAN . "  [LIMIT]   " . B_WHITE . "{$maxDaily}/day" . RESET . "\n";
    echo B_CYAN . "  [BALANCE] " . B_WHITE . $balance . " USDT" . RESET . "\n";
    echo B_CYAN . "  [DAILY]   " . B_WHITE . $dailyCount . "/" . $maxDaily . RESET . "\n";
    echo B_CYAN . "  [MODE]    " . B_WHITE . strtoupper($mode) . RESET . "\n\n";

    $claims = 0; $failures = 0; $skips = 0;
    $unlimitedClaims = 0;
    $maxFailures = 15;
    $sessionInvalidCount = 0;
    $currentMode = $mode;

    while (true) {
        if (resetDailyIfNeeded()) { $dailyCount = 0; }

        $round = $claims + $failures + $skips + $unlimitedClaims + 1;
        echo "\n" . B_CYAN . "  ╔══ ROUND #{$round} ─ " . date('H:i:s')
             . " [{$currentMode}] ═══╗" . RESET . "\n";

        // ── Cek limit kalau mode regular ──
        if ($currentMode === 'regular' && $dailyCount >= $maxDaily) {
            echo "  " . B_YELLOW . "[LIMIT] Regular limit habis, switch ke unlimited..." . RESET . "\n";
            $currentMode = 'unlimited';
            continue;
        }

        $info = [];
        if ($currentMode === 'unlimited') {
            $res = claimPopFaucet($info);
        } else {
            $res = claimFaucet($info);
        }

        // ── Handle responses ──
        if ($res === 'limit_reached') {
            echo "  " . B_YELLOW . "[LIMIT] Regular limit reached, switch ke unlimited..." . RESET . "\n";
            $currentMode = 'unlimited';
            continue;
        }
        elseif ($res === 'session_invalid') {
            $sessionInvalidCount++;
            echo "  " . B_YELLOW . "[!] Session expired ({$sessionInvalidCount}x), re-login..." . RESET . "\n";
            sleep(5);

            if (!doLogin($email, $password)) {
                if ($sessionInvalidCount >= 3) break;
                sleep(30);
                continue;
            }
            $sessionInvalidCount = 0;
            $balance = getBalance();
            echo B_CYAN . "  [BALANCE] " . B_WHITE . $balance . " USDT\n" . RESET;
            sleep(5);
            continue;
        }
        elseif ($res === 'captcha_skip') {
            $skips++;
            echo "  " . B_YELLOW . "skip round" . RESET . "\n";
            sleep(rand(3, 6));
        }
        elseif ($res === 'no_form' || $res === 'no_csrf') {
            echo "  " . B_YELLOW . "form kosong, tunggu 5s" . RESET . "\n";
            sleep(5);
        }
        elseif ($res === 'fetch_fail') {
            $failures++;
            echo "  " . B_RED . "fetch fail ({$failures}/{$maxFailures})" . RESET . "\n";
            if ($failures >= $maxFailures) { echo "  " . B_RED . "[STOP] Gagal terus." . RESET . "\n"; break; }
            sleep(10);
        }
        elseif ($res === 'ad_token_fail') {
            $failures++;
            echo "  " . B_RED . "ad token fail ({$failures}/{$maxFailures})" . RESET . "\n";
            if ($failures >= $maxFailures) { echo "  " . B_RED . "[STOP] Gagal terus." . RESET . "\n"; break; }
            sleep(8);
        }
        elseif (is_array($res) && isset($res['cooldown'])) {
            $cd = max(1, (int)$res['cooldown']);
            echo "  " . B_YELLOW . "cooldown {$cd}s" . RESET . "\n";
            timer($cd, "Cooldown");
        }
        elseif ($res === true) {
            if ($currentMode === 'unlimited') {
                $unlimitedClaims++;
            } else {
                $claims++; $dailyCount++;
                updateDailyCount($dailyCount);
            }
            $failures = 0;
            $balance = getBalance();
            echo B_CYAN . "  [BALANCE] " . B_WHITE . $balance . " USDT\n" . RESET;
            if ($currentMode === 'regular') {
                echo B_CYAN . "  [DAILY] " . B_WHITE . $dailyCount . "/" . $maxDaily . "\n" . RESET;
            }
            echo B_GREEN . "  [TOTAL] {$claims} regular | {$unlimitedClaims} unlimited" . RESET . "\n";

            $waitS = rand(MIN_CLAIM_DELAY, MAX_CLAIM_DELAY);
            sleep($waitS);
        }
        else {
            $failures++;
            echo B_RED . "  [FAIL] {$failures}/{$maxFailures}" . RESET . "\n";
            if ($failures >= $maxFailures) { echo "  " . B_RED . "[STOP] Gagal terus." . RESET . "\n"; break; }
            sleep(rand(5, 10));
        }

        echo B_CYAN . "  ╚═══════════════════════════════════════╝" . RESET . "\n";
    }

    $balance = getBalance();
    echo "\n" . B_CYAN . "  [FINAL] " . B_WHITE . $balance . " USDT" . RESET . "\n";
    echo "  " . B_GREEN . "{$claims} regular" . RESET . " | "
         . B_MAGENTA . "{$unlimitedClaims} unlimited" . RESET . " | "
         . B_YELLOW . "{$skips} skip" . RESET . " | "
         . B_RED . "{$failures} fail" . RESET . "\n";
}

// ═══════════════ MENU ═══════════════
function printMenu() {
    printBanner();
    echo B_CYAN . "  [1] " . B_GREEN . "Start Farming (AUTO mode)\n";
    echo B_CYAN . "      " . DIM . "Regular dulu, auto-switch unlimited kalau limit\n" . RESET;
    echo B_CYAN . "  [2] " . B_MAGENTA . "Unlimited Mode Only\n";
    echo B_CYAN . "      " . DIM . "Pop-Under faucet, no daily limit\n" . RESET;
    echo B_CYAN . "  [3] " . B_YELLOW . "Regular Mode Only\n";
    echo B_CYAN . "  [4] " . B_WHITE . "Config Email & Password\n";
    echo B_CYAN . "  [5] " . B_CYAN . "Check Account Info (VIP detect)\n";
    echo B_CYAN . "  [0] " . B_RED . "Exit\n";
    echo B_CYAN . "==================================================\n";
    echo B_WHITE . "  Pilih: " . RESET;
}

function configEmailPassword() {
    clearScreen();
    printBanner();
    echo B_CYAN . "  ── Konfigurasi Akun ──\n\n";
    echo B_WHITE . "Email: " . RESET;
    $e = trim(fgets(STDIN));
    echo B_WHITE . "Password: " . RESET;
    $p = trim(fgets(STDIN));
    file_put_contents(CONFIG_FILE, json_encode(['email'=>$e, 'password'=>$p], JSON_PRETTY_PRINT));
    echo B_GREEN . "\n  ✅ Config disimpan!\n" . RESET;
    echo B_WHITE . "\n  Tekan Enter untuk kembali...\n" . RESET;
    fgets(STDIN);
}

function checkAccountInfo($email, $password) {
    clearScreen();
    printBanner();
    echo B_CYAN . "  ── Account Info ──\n\n";

    if (!doLogin($email, $password)) {
        echo B_RED . "  Login gagal.\n" . RESET;
        echo B_WHITE . "\n  Tekan Enter..." . RESET;
        fgets(STDIN);
        return;
    }

    $dash = req(HOST . '/dashboard');
    $vipInfo = detectVIP($dash ?: '');
    $balance = getBalance();

    echo B_CYAN . "  Email       : " . B_WHITE . $email . RESET . "\n";
    echo B_CYAN . "  VIP Status  : " . ($vipInfo['vip'] ? B_GREEN . "YES" : B_YELLOW . "NO") . RESET . "\n";
    echo B_CYAN . "  Tier        : " . B_WHITE . $vipInfo['tier'] . RESET . "\n";
    echo B_CYAN . "  Daily Limit : " . B_WHITE . $vipInfo['limit'] . "/day" . RESET . "\n";
    echo B_CYAN . "  Balance     : " . B_WHITE . $balance . " USDT" . RESET . "\n";
    echo B_CYAN . "  Unlimited   : " . B_MAGENTA . "Available (via /pop-faucet)" . RESET . "\n";

    echo B_WHITE . "\n  Tekan Enter..." . RESET;
    fgets(STDIN);
}

// ═══════════════ MAIN ═══════════════
printBanner();

if (!file_exists(CONFIG_FILE)) {
    echo "  " . B_YELLOW . "[!] Config belum ada, isi dulu.\n" . RESET;
    echo "  " . DIM . "Enter untuk lanjut..." . RESET;
    fgets(STDIN);
    configEmailPassword();
}

$cfg = json_decode(file_get_contents(CONFIG_FILE), true);
$email = $cfg['email'] ?? '';
$password = $cfg['password'] ?? '';

while (true) {
    printMenu();
    $choice = trim(fgets(STDIN));

    switch ($choice) {
        case '1':
            startFarming($email, $password, 'auto');
            echo "\n  " . DIM . "Enter untuk kembali..." . RESET;
            fgets(STDIN);
            break;
        case '2':
            startFarming($email, $password, 'unlimited');
            echo "\n  " . DIM . "Enter untuk kembali..." . RESET;
            fgets(STDIN);
            break;
        case '3':
            startFarming($email, $password, 'regular');
            echo "\n  " . DIM . "Enter untuk kembali..." . RESET;
            fgets(STDIN);
            break;
        case '4':
            configEmailPassword();
            $cfg = json_decode(file_get_contents(CONFIG_FILE), true);
            $email = $cfg['email'] ?? '';
            $password = $cfg['password'] ?? '';
            break;
        case '5':
            checkAccountInfo($email, $password);
            break;
        case '0':
            echo "\n" . B_GREEN . "  Bye." . RESET . "\n";
            exit(0);
        default:
            echo "\n  " . B_RED . "salah pilihan." . RESET . "\n";
            echo "  " . DIM . "Enter..." . RESET;
            fgets(STDIN);
    }
}
