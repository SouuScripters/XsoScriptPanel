#!/usr/bin/env php
<?php
/**
 * ===============================================================
 *  TRONBLOW.site Auto Claim Bot v6.1 (Email Only)
 *  - Pre-flight check (PHP, curl, connectivity)
 *  - Cloudflare detection + auto fresh session
 *  - Random User-Agent
 *  - Health check faucet (last payment age)
 *  - STOP otomatis kalau "insufficient funds"
 * ===============================================================
 */

// Suppress deprecation warnings (curl_close dll di PHP 8.5)
error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE);

if (PHP_VERSION_ID < 80000) {
    fwrite(STDERR, "ERROR: Butuh PHP 8.0+. Versi sekarang: " . PHP_VERSION . "\n");
    exit(1);
}
if (!extension_loaded('curl')) {
    fwrite(STDERR, "ERROR: ext-curl gak ada.\n");
    fwrite(STDERR, "  Debian/Ubuntu : sudo apt install php-curl\n");
    fwrite(STDERR, "  Termux        : pkg install php-curl\n");
    exit(1);
}

// ===============================================================
//  COLOR
// ===============================================================
const RST = "\033[0m";
const BOLD = "\033[1m";
const DIM  = "\033[2m";
const RED  = "\033[38;5;196m";
const GRN  = "\033[38;5;46m";
const YEL  = "\033[38;5;226m";
const CYN  = "\033[38;5;51m";
const MAG  = "\033[38;5;201m";
const ORG  = "\033[38;5;208m";
const WHT  = "\033[38;5;15m";
const GRY  = "\033[38;5;240m";
const VIO  = "\033[38;5;141m";

function vlen(string $s): int {
    return mb_strlen(preg_replace('/\033\[[0-9;]*m/', '', $s));
}
function pad_to(string $s, int $w): string {
    $len = vlen($s);
    return $s . str_repeat(' ', max(0, $w - $len));
}

// ===============================================================
//  STATE
// ===============================================================
$STATE = [
    'email'         => '-',
    'claims'        => 0,
    'rewards'       => 0.0,
    'failures'      => 0,
    'max_failures'  => 10,
    'runtime_start' => time(),
    'max_runtime'   => 3 * 3600,
    'logs'          => [],
    'faucet_status' => 'checking',
    'last_payment'  => null,
    'daily_count'   => 0,
    'daily_limit'   => 200,
];

function state_log(string $msg, string $level = 'INFO'): void {
    global $STATE;
    $ts = date('H:i:s');
    $tag = match(strtoupper($level)) {
        'OK'     => GRN . "[OK]    " . RST,
        'ERR'    => RED . "[ERR]   " . RST,
        'WARN'   => YEL . "[WARN]  " . RST,
        'CLAIM'  => MAG . "[CLAIM] " . RST,
        'VERIFY' => VIO . "[VERIFY]" . RST,
        'HEALTH' => ORG . "[HEALTH]" . RST,
        'WAIT'   => YEL . "[WAIT]  " . RST,
        'PRE'    => CYN . "[PREFLT]" . RST,
        default  => GRY . "[INFO]  " . RST,
    };
    $STATE['logs'][] = GRY . "[{$ts}] " . RST . $tag . " " . WHT . $msg . RST;
    if (count($STATE['logs']) > 6) array_shift($STATE['logs']);
}

function fmt_duration(int $sec): string {
    $h = floor($sec / 3600);
    $m = floor(($sec % 3600) / 60);
    $s = $sec % 60;
    return sprintf('%02d:%02d:%02d', $h, $m, $s);
}

// ===============================================================
//  RENDER BOX
// ===============================================================
function render_box(): void {
    global $STATE;
    $W = 62;
    $bdr = CYN;
    $top = $bdr . "+" . str_repeat('-', $W) . "+" . RST;
    $mid = $bdr . "+" . str_repeat('-', $W) . "+" . RST;
    $bot = $bdr . "+" . str_repeat('-', $W) . "+" . RST;
    $line = fn(string $c) => $bdr . "|" . RST . pad_to(" " . $c, $W) . $bdr . "|" . RST;

    echo "\n";
    echo $top . "\n";
    echo $line(BOLD . WHT . "TRONBLOW AUTO CLAIM" . RST) . "\n";
    echo $line(DIM . "------ SOUU ENGINE v6.1 ------" . RST) . "\n";
    echo $mid . "\n";

    $hs_label = 'CHECKING'; $hs_color = GRY;
    switch ($STATE['faucet_status']) {
        case 'ok':      $hs_label = 'ONLINE';  $hs_color = GRN; break;
        case 'suspect': $hs_label = 'SUSPECT'; $hs_color = YEL; break;
        case 'dead':    $hs_label = 'DEAD';    $hs_color = RED; break;
    }
    echo $line(VIO . "FAUCET" . RST) . "\n";
    echo $line("|- Status     : " . $hs_color . $hs_label . RST) . "\n";
    if ($STATE['last_payment']) {
        $age = (int) floor((time() - $STATE['last_payment']) / 60);
        echo $line("|- Last Pay   : " . DIM . $age . " min ago" . RST) . "\n";
    }
    echo $line("|- Daily      : " . CYN . $STATE['daily_count'] . RST . " / " . $STATE['daily_limit']) . "\n";
    echo $line("'- Email      : " . $STATE['email']) . "\n";
    echo $mid . "\n";

    $runtime = time() - $STATE['runtime_start'];
    echo $line(VIO . "SYSTEM" . RST) . "\n";
    echo $line("|- Claims     : " . GRN . $STATE['claims'] . RST) . "\n";
    echo $line("|- Rewards    : " . GRN . sprintf('+%.5f TRX', $STATE['rewards']) . RST) . "\n";
    echo $line("|- Failures   : " . RED . $STATE['failures'] . RST . " / " . $STATE['max_failures']) . "\n";
    echo $line("'- Runtime    : " . CYN . fmt_duration($runtime) . RST . " / " . DIM . fmt_duration($STATE['max_runtime']) . RST) . "\n";
    echo $mid . "\n";

    $logs = $STATE['logs'];
    if (empty($logs)) {
        echo $line(DIM . "- no activity yet -" . RST) . "\n";
    } else {
        foreach ($logs as $l) echo $line($l) . "\n";
    }
    echo $bot . "\n";
    echo "\n   " . GRN . "BOT RUNNING" . RST . " " . DIM . "*" . RST . " " . CYN . date('H:i:s') . RST . "\n";
    echo "   " . DIM . "By Power @SouuXso - TronBlow v6.1" . RST . "\n\n";
}

function render_box_clear(): void {
    if (PHP_OS_FAMILY === 'Windows') {
        pclose(popen('cls', 'w'));
    } else {
        system('clear');
    }
    render_box();
}

// ===============================================================
//  CONFIG
// ===============================================================
$CONFIG_FILE  = __DIR__ . "/tronblow_config.json";
$COUNTER_FILE = __DIR__ . "/tronblow_counter.json";

const DAILY_LIMIT = 200;
const BASE_URL    = 'https://tronblow.site';

$UA_POOL = [
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-A536E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
];

function random_ua(): string {
    global $UA_POOL;
    return $UA_POOL[array_rand($UA_POOL)];
}

// ===============================================================
//  IO HELPERS
// ===============================================================
function read_line(string $prompt = ""): string {
    if ($prompt) echo $prompt;
    $line = fgets(STDIN);
    return trim((string) $line);
}

function load_config(): ?array {
    global $CONFIG_FILE;
    if (!file_exists($CONFIG_FILE)) return null;
    $json = @file_get_contents($CONFIG_FILE);
    $cfg = json_decode((string) $json, true);
    if (is_array($cfg) && !empty($cfg['email'])) {
        $cfg['base_url'] = $cfg['base_url'] ?? BASE_URL;
        $cfg['delay']    = $cfg['delay']    ?? 65;
        return $cfg;
    }
    return null;
}

function save_config(array $cfg): void {
    global $CONFIG_FILE;
    @file_put_contents($CONFIG_FILE, json_encode($cfg, JSON_PRETTY_PRINT));
}

function load_counter(): array {
    global $COUNTER_FILE;
    $today = date('Y-m-d');
    if (file_exists($COUNTER_FILE)) {
        $d = json_decode((string) file_get_contents($COUNTER_FILE), true);
        if (is_array($d) && ($d['date'] ?? '') === $today) return $d;
    }
    return ['date' => $today, 'count' => 0];
}

function save_counter(array $c): void {
    global $COUNTER_FILE;
    @file_put_contents($COUNTER_FILE, json_encode($c, JSON_PRETTY_PRINT));
}

function increment_counter(): array {
    $c = load_counter();
    $c['count']++;
    save_counter($c);
    return $c;
}

// ===============================================================
//  PRE-FLIGHT
// ===============================================================
function preflight(): bool {
    state_log("PHP " . PHP_VERSION . " - OK", 'PRE');
    state_log("ext-curl - OK", 'PRE');

    $ch = curl_init(BASE_URL);
    curl_setopt_array($ch, [
        CURLOPT_NOBODY         => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_USERAGENT      => random_ua(),
    ]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err  = curl_error($ch);
    // No curl_close() — deprecated PHP 8.5

    if ($err) {
        state_log("Koneksi gagal: $err", 'ERR');
        return false;
    }
    if ($code >= 500) {
        state_log("Server HTTP $code - mungkin down", 'ERR');
        return false;
    }
    state_log("Koneksi OK (HTTP $code)", 'PRE');
    return true;
}

// ===============================================================
//  HTTP (tanpa cookie jar - stateless request)
// ===============================================================
function base_headers(): array {
    return [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language: en-GB,en;q=0.9',
        'Cache-Control: no-cache',
        'Pragma: no-cache',
        'Sec-Ch-Ua: "Chromium";v="127", "Not)A;Brand";v="99"',
        'Sec-Ch-Ua-Mobile: ?1',
        'Sec-Ch-Ua-Platform: "Android"',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: none',
        'Upgrade-Insecure-Requests: 1',
    ];
}

function fetch_page(string $url): array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS      => 5,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_ENCODING       => '',
        CURLOPT_USERAGENT      => random_ua(),
        CURLOPT_HTTPHEADER     => base_headers(),
    ]);
    $html = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err  = curl_error($ch);
    // No curl_close()

    if ($err || $code !== 200 || empty($html)) {
        return ['html' => false, 'http_code' => $code, 'err' => $err];
    }
    return ['html' => $html, 'http_code' => $code, 'err' => ''];
}

function submit_claim(string $url, string $email, string $csrf, int $answer): array {
    $post = http_build_query([
        'action'      => 'claim',
        'csrf_token'  => $csrf,
        'website'     => '',
        'email'       => $email,
        'math_answer' => $answer,
    ]);

    $headers = base_headers();
    $headers[] = 'Content-Type: application/x-www-form-urlencoded';
    $headers[] = 'Origin: ' . $url;
    $headers[] = 'Referer: ' . $url . '/';
    $headers = array_map(function($h) {
        return str_replace('Sec-Fetch-Site: none', 'Sec-Fetch-Site: same-origin', $h);
    }, $headers);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $post,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS      => 5,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_ENCODING       => '',
        CURLOPT_USERAGENT      => random_ua(),
        CURLOPT_HTTPHEADER     => $headers,
    ]);
    $body = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err  = curl_error($ch);
    // No curl_close()
    return ['code' => $code, 'body' => (string) $body, 'err' => $err];
}

// ===============================================================
//  PARSER
// ===============================================================
function extract_csrf_token(string $html): ?string {
    $patterns = [
        '/<input\s+type="hidden"\s+name="csrf_token"\s+value="([^"]+)"/i',
        '/<input\s+name="csrf_token"\s+type="hidden"\s+value="([^"]+)"/i',
        '/name=["\']csrf_token["\']\s+value=["\']([^"\']+)/i',
        '/<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)/i',
    ];
    foreach ($patterns as $p) {
        if (preg_match($p, $html, $m)) return $m[1];
    }
    return null;
}

function extract_math_question(string $html): ?array {
    if (preg_match('/<div\s+class="captcha-q">(.*?)<\/div>/is', $html, $m)) {
        $text = strip_tags($m[1]);
    } else {
        $text = strip_tags($html);
    }
    $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $text = str_replace(['-', '-', '-', '-', '-', '-', '&minus;'], '-', $text);
    $text = str_replace(['x', '&times;'], '*', $text);
    $text = str_replace(['/', '&divide;'], '/', $text);

    $patterns = [
        '/what\s+is\s+(\d+)\s*([+\-*\/])\s*(\d+)\s*=\s*\?/i',
        '/(\d+)\s*([+\-*\/])\s*(\d+)\s*=\s*\?/i',
        '/(\d+)\s*([+\-*\/])\s*(\d+)\s*=/i',
        '/(\d+)\s*([+\-*\/])\s*(\d+)/i',
    ];
    foreach ($patterns as $p) {
        if (preg_match($p, $text, $m)) {
            return ['q1' => (int)$m[1], 'op' => $m[2], 'q2' => (int)$m[3]];
        }
    }
    return null;
}

function solve_math(array $m): int {
    $a = $m['q1']; $b = $m['q2'];
    return match($m['op']) {
        '+' => $a + $b,
        '-' => $a - $b,
        '*' => $a * $b,
        '/' => $b != 0 ? (int)($a / $b) : 0,
        default => 0,
    };
}

function extract_endAt(string $html): ?int {
    if (preg_match('/endAt\s*=\s*(\d+)\s*\*\s*1000/', $html, $m)) return (int)($m[1] * 1000);
    if (preg_match('/endAt\s*=\s*(\d+)\s*;?/', $html, $m)) return (int)$m[1];
    return null;
}

function detect_cloudflare(string $html): bool {
    $low = strtolower($html);
    $keywords = [
        'cf-browser-verification',
        'challenge-platform',
        'just a moment',
        'checking your browser',
        'cloudflare ray id',
        'enable javascript and cookies to continue',
    ];
    foreach ($keywords as $kw) {
        if (strpos($low, $kw) !== false) return true;
    }
    return false;
}

function detect_login_wall(string $html): bool {
    $low = strtolower($html);
    return strpos($low, 'login required') !== false
        || strpos($low, 'please login') !== false
        || strpos($low, 'sign in to continue') !== false;
}

// ===============================================================
//  RESPONSE PARSER
// ===============================================================
function parse_alert_message(string $html): array {
    $out = ['success' => null, 'error' => null];
    if (preg_match('/<div[^>]*class="[^"]*alert-success[^"]*"[^>]*>(.*?)<\/div>/is', $html, $m)) {
        $out['success'] = trim(strip_tags($m[1]));
    }
    if (preg_match('/<div[^>]*class="[^"]*alert-error[^"]*"[^>]*>(.*?)<\/div>/is', $html, $m)) {
        $out['error'] = trim(strip_tags($m[1]));
    }
    if ($out['success'] === null && $out['error'] === null) {
        if (preg_match('/<div[^>]*class="[^"]*alert[^"]*"[^>]*>(.*?)<\/div>/is', $html, $m)) {
            $txt = trim(strip_tags($m[1]));
            $low = strtolower($txt);
            if (strpos($low, 'success') !== false || strpos($low, 'sent') !== false) {
                $out['success'] = $txt;
            } else {
                $out['error'] = $txt;
            }
        }
    }
    return $out;
}

function is_fatal_error(string $msg): bool {
    $s = strtolower($msg);
    $keys = [
        'insufficient fund', 'does not have sufficient', 'payment failed',
        'faucet is empty', 'out of funds', 'no funds', 'balance is empty',
        'not enough balance',
    ];
    foreach ($keys as $k) if (strpos($s, $k) !== false) return true;
    return false;
}

function check_faucet_health(string $html, int $max_age_min = 30): array {
    $out = ['ok' => true, 'last_payment' => null, 'age_min' => null, 'reason' => ''];
    if (preg_match_all('/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/', $html, $matches)) {
        $ts = array_map('strtotime', $matches[1]);
        sort($ts);
        $latest = end($ts);
        $out['last_payment'] = $latest;
        $age_min = (int) floor((time() - $latest) / 60);
        $out['age_min'] = $age_min;
        if ($age_min > $max_age_min) {
            $out['ok'] = false;
            $out['reason'] = "Last payment {$age_min} menit lalu (threshold {$max_age_min}m)";
        }
    } else {
        $out['ok'] = false;
        $out['reason'] = 'Gak ada entry di Live Payment Proof';
    }
    return $out;
}

function check_response(string $html): array {
    $alerts = parse_alert_message($html);

    if ($alerts['success'] !== null) {
        return ['status' => 'success', 'msg' => $alerts['success']];
    }
    if ($alerts['error'] !== null) {
        $msg = $alerts['error'];
        if (is_fatal_error($msg)) return ['status' => 'fatal', 'msg' => $msg];
        $low = strtolower($msg);
        if (strpos($low, 'math') !== false || strpos($low, 'captcha') !== false
            || strpos($low, 'wrong') !== false || strpos($low, 'incorrect') !== false
            || strpos($low, 'invalid') !== false) {
            return ['status' => 'wrong', 'msg' => $msg];
        }
        return ['status' => 'error', 'msg' => $msg];
    }

    $low = strtolower($html);
    foreach (['banned', 'blocked', 'vpn not allowed', 'proxy not allowed'] as $kw) {
        if (strpos($low, $kw) !== false) return ['status' => 'banned', 'msg' => "Keyword: $kw"];
    }
    foreach (['please wait', 'try again later', 'countdown', 'one claim'] as $kw) {
        if (strpos($low, $kw) !== false) return ['status' => 'wait', 'msg' => "Cooldown: $kw"];
    }
    return ['status' => 'unknown', 'msg' => 'Unclear response'];
}

// ===============================================================
//  SETUP
// ===============================================================
function interactive_setup(): array {
    echo "\n" . CYN . "=== FIRST TIME SETUP ===" . RST . "\n\n";
    $email = '';
    while (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $email = read_line(YEL . "FaucetPay Email: " . RST);
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            echo RED . "  x Email gak valid, coba lagi.\n" . RST;
        }
    }
    return [
        'email'    => $email,
        'base_url' => BASE_URL,
        'delay'    => 65,
    ];
}

// ===============================================================
//  MAIN
// ===============================================================
render_box_clear();
echo CYN . "  + TRONBLOW AUTO CLAIM ENGINE v6.1\n" . RST;
echo DIM . "  --- Souu Engine ---\n\n" . RST;

// PRE-FLIGHT
state_log("Running pre-flight check...", 'PRE');
render_box_clear();
if (!preflight()) {
    render_box_clear();
    echo "\n" . RED . "  x Pre-flight gagal. Cek koneksi / server.\n\n" . RST;
    exit(1);
}

// LOAD CONFIG
$config = load_config();
if ($config) {
    echo GRN . "  v Config found\n" . RST;
    echo DIM . "    Email : {$config['email']}\n" . RST;
    echo DIM . "    Delay : {$config['delay']}s\n" . RST;
    echo DIM . "    URL   : {$config['base_url']}\n\n" . RST;
    $ans = read_line(YEL . "  Use saved? (y/n): " . RST);
    if (strtolower($ans) === 'n') {
        $config = interactive_setup();
        save_config($config);
    }
} else {
    $config = interactive_setup();
    save_config($config);
}

$STATE['email'] = $config['email'];
$STATE['daily_count'] = load_counter()['count'];
$STATE['runtime_start'] = time();

render_box_clear();

$cycle = 0;
$consecutive_parse_fails = 0;

while (true) {
    // Daily limit
    $counter = load_counter();
    $STATE['daily_count'] = $counter['count'];
    if ($counter['count'] >= DAILY_LIMIT) {
        state_log("Daily limit reached ({$counter['count']}/" . DAILY_LIMIT . ")", 'WARN');
        render_box_clear();
        $secs = strtotime("tomorrow 00:00 UTC") - time();
        while ($secs > 0) {
            sleep(min(60, $secs));
            $secs = strtotime("tomorrow 00:00 UTC") - time();
        }
        continue;
    }

    // Max runtime
    if ((time() - $STATE['runtime_start']) >= $STATE['max_runtime']) {
        state_log("Max runtime reached, exiting", 'WARN');
        render_box_clear();
        break;
    }

    // Max failures
    if ($STATE['failures'] >= $STATE['max_failures']) {
        state_log("Max failures reached, exiting", 'ERR');
        render_box_clear();
        break;
    }

    $cycle++;
    state_log("Cycle #$cycle starting...", 'INFO');
    render_box_clear();

    // FETCH
    $result = fetch_page($config['base_url']);
    if (!$result['html']) {
        state_log("Fetch failed (HTTP {$result['http_code']}) {$result['err']}", 'ERR');
        $STATE['failures']++;
        render_box_clear();
        sleep(30);
        continue;
    }
    $html = $result['html'];

    // CLOUDFLARE
    if (detect_cloudflare($html)) {
        state_log("Cloudflare challenge detected", 'WARN');
        render_box_clear();
        $STATE['failures']++;
        $backoff = min(300, 60 + ($STATE['failures'] * 30));
        state_log("Tunggu {$backoff}s", 'WAIT');
        render_box_clear();
        sleep($backoff);
        continue;
    }

    // LOGIN WALL
    if (detect_login_wall($html)) {
        state_log("Login wall - email mungkin belum set", 'WARN');
        $STATE['failures']++;
        render_box_clear();
        sleep(30);
        continue;
    }

    // HEALTH CHECK
    state_log("Checking faucet health...", 'HEALTH');
    render_box_clear();
    $health = check_faucet_health($html, 30);
    $STATE['faucet_status'] = $health['ok'] ? 'ok' : 'suspect';
    $STATE['last_payment'] = $health['last_payment'];

    if (!$health['ok']) {
        state_log("SUSPECT: {$health['reason']}", 'WARN');
        render_box_clear();

        $pre = parse_alert_message($html);
        if ($pre['error'] && is_fatal_error($pre['error'])) {
            $STATE['faucet_status'] = 'dead';
            state_log("FATAL: {$pre['error']}", 'ERR');
            render_box_clear();
            echo "\n" . RED . "  +--------------------------------------------------+\n" . RST;
            echo RED   . "  |  x FAUCET SUDAH TIDAK BISA BAYAR                |\n" . RST;
            echo RED   . "  |  Bot dihentikan otomatis.                        |\n" . RST;
            echo RED   . "  +--------------------------------------------------+\n\n" . RST;
            break;
        }

        echo "\n" . YEL . "  ! Faucet kelihatan gak bayar (" . ($health['age_min'] ?? '?') . " menit).\n" . RST;
        $ans = read_line(YEL . "  Lanjut claim? (y/n): " . RST);
        if (strtolower($ans) !== 'y') {
            state_log("Stopped by user", 'WARN');
            render_box_clear();
            break;
        }
    }

    // CSRF
    $csrf = extract_csrf_token($html);
    if (!$csrf) {
        $STATE['failures']++;
        $consecutive_parse_fails++;
        state_log("CSRF token not found (attempt $consecutive_parse_fails/3)", 'ERR');
        render_box_clear();
        if ($consecutive_parse_fails >= 3) {
            state_log("3x gagal parse - mundur 60s", 'WARN');
            $consecutive_parse_fails = 0;
            render_box_clear();
            sleep(60);
        } else {
            sleep(15);
        }
        continue;
    }

    // MATH
    $math = extract_math_question($html);
    if (!$math) {
        $STATE['failures']++;
        state_log("Math question not found", 'ERR');
        render_box_clear();
        sleep(15);
        continue;
    }
    $answer = solve_math($math);
    state_log("Math: {$math['q1']} {$math['op']} {$math['q2']} = $answer", 'VERIFY');
    render_box_clear();

    // SUBMIT
    state_log("Claiming 1000 SAT...", 'CLAIM');
    render_box_clear();

    $submit = submit_claim($config['base_url'], $config['email'], $csrf, $answer);
    if ($submit['err']) {
        state_log("Submit curl error: {$submit['err']}", 'ERR');
        $STATE['failures']++;
        render_box_clear();
        sleep(20);
        continue;
    }

    $status = check_response($submit['body']);
    $wait_seconds = $config['delay'];
    $consecutive_parse_fails = 0;

    switch ($status['status']) {
        case 'success':
            $counter = increment_counter();
            $STATE['daily_count'] = $counter['count'];
            $STATE['claims']++;
            $STATE['rewards'] += 0.00001;
            $STATE['failures'] = 0;
            state_log("v CLAIMED: {$status['msg']}", 'OK');
            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $wait_ms = $endAt - (int)(microtime(true) * 1000);
                if ($wait_ms > 0) $wait_seconds = (int) ceil($wait_ms / 1000);
            }
            render_box_clear();
            break;

        case 'fatal':
            $STATE['faucet_status'] = 'dead';
            state_log("FATAL: {$status['msg']}", 'ERR');
            render_box_clear();
            echo "\n" . RED . "  +--------------------------------------------------+\n" . RST;
            echo RED   . "  |  x FAUCET SUDAH TIDAK BISA BAYAR                |\n" . RST;
            echo RED   . "  |  Bot dihentikan otomatis.                        |\n" . RST;
            echo RED   . "  +--------------------------------------------------+\n\n" . RST;
            exit(2);

        case 'wait':
            state_log("[WAIT] {$status['msg']}", 'WAIT');
            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $wait_ms = $endAt - (int)(microtime(true) * 1000);
                if ($wait_ms > 0) $wait_seconds = (int) ceil($wait_ms / 1000);
            }
            render_box_clear();
            break;

        case 'wrong':
            state_log("Math wrong: {$status['msg']}", 'ERR');
            $STATE['failures']++;
            render_box_clear();
            sleep(5);
            continue 2;

        case 'error':
            state_log("Error: {$status['msg']}", 'ERR');
            $STATE['failures']++;
            render_box_clear();
            sleep(15);
            continue 2;

        case 'banned':
            state_log("BANNED: {$status['msg']}", 'ERR');
            render_box_clear();
            exit(1);

        default:
            state_log("Unknown response", 'WARN');
            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $wait_ms = $endAt - (int)(microtime(true) * 1000);
                if ($wait_ms > 0) $wait_seconds = (int) ceil($wait_ms / 1000);
            }
            render_box_clear();
            break;
    }

    if ($wait_seconds > 0) {
        state_log("Next claim in {$wait_seconds}s", 'WAIT');
        render_box_clear();
        sleep($wait_seconds);
    }
}

render_box_clear();
echo "\n" . CYN . "  + Bot stopped.\n" . RST;
echo DIM . "  Claims: {$STATE['claims']}  |  Failures: {$STATE['failures']}\n" . RST;
echo "\n";
