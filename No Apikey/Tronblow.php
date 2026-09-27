<?php
/**
 * ═══════════════════════════════════════════════════════════════
 *  TronBlow.site Auto Claim Bot v4.0
 *  - Max Claim: 200/day (info di banner)
 *  - Full Hacker Animation Pack terintegrasi
 *  - Fix: hapus curl_close (PHP 8.0+ native)
 * ═══════════════════════════════════════════════════════════════
 */

if (PHP_VERSION_ID < 80000) {
    echo "ERROR: PHP 8.0+ required.\n";
    exit(1);
}

// ═══════════════════════════════════════════════════════════════
//  ANIMATION PACK (Hacker Style)
// ═══════════════════════════════════════════════════════════════

define('RESET',   "\033[0m");
define('BOLD',    "\033[1m");
define('DIM',     "\033[2m");
define('RED',     "\033[1;31m");
define('GREEN',   "\033[1;32m");
define('YELLOW',  "\033[1;33m");
define('BLUE',    "\033[1;34m");
define('MAGENTA', "\033[1;35m");
define('CYAN',    "\033[1;36m");
define('WHITE',   "\033[1;37m");
define('GRAY',    "\033[0;90m");
define('NEON',    "\033[38;5;46m");
define('NEON_P',  "\033[38;5;201m");
define('NEON_C',  "\033[38;5;51m");
define('NEON_Y',  "\033[38;5;226m");
define('ORANGE',  "\033[38;5;208m");
define('PURPLE',  "\033[38;5;135m");

function clear_screen() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function matrix_rain($width = 70, $height = 8, $duration = 2.0) {
    $chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉ01010101TRONBLOW";
    $charsArr = preg_split('//u', $chars, -1, PREG_SPLIT_NO_EMPTY);
    $start = microtime(true);
    $lines = array_fill(0, $height, array_fill(0, $width, ' '));

    echo "\n";
    for ($i = 0; $i < $height; $i++) echo "\n";

    while ((microtime(true) - $start) < $duration) {
        for ($i = 0; $i < 5; $i++) {
            $col = random_int(0, $width - 1);
            $lines[0][$col] = $charsArr[random_int(0, count($charsArr) - 1)];
        }
        for ($y = $height - 1; $y > 0; $y--) {
            $lines[$y] = $lines[$y - 1];
        }
        $lines[0] = array_fill(0, $width, ' ');

        echo "\033[" . $height . "A";
        foreach ($lines as $y => $row) {
            $color = $y < 1 ? NEON : ($y < 2 ? GREEN : (DIM . GREEN));
            echo $color . implode('', $row) . RESET . "\n";
        }
        usleep(80000);
    }
}

function loading_bar($label = "LOADING", $duration = 1.5) {
    $frames = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏'];
    $start = microtime(true);
    $i = 0;
    $barLen = 30;
    while ((microtime(true) - $start) < $duration) {
        $progress = (microtime(true) - $start) / $duration;
        $filled = (int)($barLen * $progress);
        $bar = str_repeat('█', $filled) . str_repeat('░', $barLen - $filled);
        $frame = $frames[$i % count($frames)];
        $hex = '';
        for ($h = 0; $h < 4; $h++) $hex .= dechex(random_int(0, 15));
        $pct = (int)($progress * 100);
        echo "\r" . PURPLE . "  ┃" . RESET . " " . NEON_P . $frame . RESET . " "
            . NEON_C . str_pad($label, 24) . RESET
            . " " . PURPLE . "[" . $bar . "]" . RESET
            . " " . NEON . sprintf("%3d%%", $pct) . RESET
            . " " . DIM . "0x" . strtoupper($hex) . RESET;
        usleep(60000);
        $i++;
    }
    echo "\r" . str_repeat(' ', 110) . "\r";
}

function scan_line($label = "SCANNING", $steps = 50) {
    for ($i = 0; $i <= $steps; $i++) {
        $bar = str_repeat('█', $i) . str_repeat('░', $steps - $i);
        $noise = '';
        for ($n = 0; $n < 16; $n++) $noise .= random_int(0, 1);
        echo "\r" . PURPLE . "  ┃" . RESET . " " . NEON_C . $label . RESET
            . " " . NEON . $bar . RESET
            . " " . NEON_P . "[" . $noise . "]" . RESET;
        usleep(30000);
    }
    echo "\n";
}

function hacking_boot($steps = null) {
    $steps = $steps ?? [
        "Initializing kernel module...",
        "Loading anti-bot engine...",
        "Rotating device fingerprint...",
        "Injecting stealth headers...",
        "Connecting to remote server...",
        "Bypassing security layers...",
        "Loading session cookies...",
        "System ready.",
    ];

    echo NEON_C . "  ⚡ SYSTEM BOOT SEQUENCE" . RESET . "\n\n";
    foreach ($steps as $s) {
        echo NEON . "[✓]" . RESET . " " . $s;
        usleep(random_int(60000, 90000));
        echo "\n";
    }
    echo NEON_Y . "[⚡]" . RESET . "   Status: " . NEON . "SECURE" . RESET . "\n";
    echo NEON_P . "[★]" . RESET . "   Welcome, Operative." . RESET . "\n";
}

function decrypt_text($target, $duration = 1.0) {
    $chars = "!@#$%^&*()_+-=[]{}|;:,.<>?~ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    $len = strlen($target);
    $start = microtime(true);
    $result = str_split(str_repeat(' ', $len));

    while ((microtime(true) - $start) < $duration) {
        $progress = (microtime(true) - $start) / $duration;
        $lockCount = (int)($len * $progress);
        for ($i = 0; $i < $len; $i++) {
            if ($i < $lockCount) {
                $result[$i] = $target[$i];
            } else {
                $result[$i] = $target[$i] === ' ' ? ' ' : $chars[random_int(0, strlen($chars) - 1)];
            }
        }
        echo "\r  " . NEON . implode('', $result) . RESET;
        usleep(50000);
    }
    echo "\r  " . NEON_C . $target . RESET . "\n";
}

function glitch_text($text, $duration = 0.8) {
    $start = microtime(true);
    $glitchChars = "░▒▓█▄▀■□▪▫";
    while ((microtime(true) - $start) < $duration) {
        $out = '';
        for ($i = 0; $i < strlen($text); $i++) {
            if (random_int(0, 10) < 2 && $text[$i] !== ' ') {
                $out .= $glitchChars[random_int(0, strlen($glitchChars) - 1)];
            } else {
                $out .= $text[$i];
            }
        }
        echo "\r  " . NEON_P . $out . RESET;
        usleep(60000);
    }
    echo "\r  " . NEON_C . $text . RESET . "\n";
}

function faucet_progress($label = "Claiming reward", $duration = 3.0) {
    $barLen = 40;
    $start = microtime(true);
    $waves = ['░', '▒', '▓', '█'];
    while ((microtime(true) - $start) < $duration) {
        $progress = (microtime(true) - $start) / $duration;
        $filled = (int)($barLen * $progress);
        $bar = '';
        for ($i = 0; $i < $barLen; $i++) {
            if ($i < $filled) {
                $bar .= '█';
            } elseif ($i === $filled) {
                $bar .= $waves[random_int(0, 3)];
            } else {
                $bar .= '░';
            }
        }
        $pct = (int)($progress * 100);
        echo "\r  " . NEON_C . "⚡ " . str_pad($label, 22) . RESET
            . " " . NEON . "[" . $bar . "]" . RESET
            . " " . NEON_Y . sprintf("%3d%%", $pct) . RESET;
        usleep(50000);
    }
    echo "\r  " . NEON . "✓ " . str_pad($label . " — DONE", 22) . RESET
        . " " . NEON . "[" . str_repeat('█', $barLen) . "]" . RESET
        . " " . NEON_Y . "100%" . RESET . "\n";
}

function spinner_wait($seconds, $prefix = "Waiting") {
    $frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
    $fc = count($frames);
    $cf = 0;
    $wait = (int)$seconds;
    while ($wait > 0) {
        $start = microtime(true);
        while ((microtime(true) - $start) < 1) {
            $h = floor($wait / 3600);
            $m = floor(($wait % 3600) / 60);
            $s = $wait % 60;
            $t = sprintf('%02d:%02d:%02d', $h, $m, $s);
            echo "\r  " . NEON_C . "⏳ " . $prefix . RESET . " : " . NEON . $t . " " . $frames[$cf] . RESET . "  ";
            usleep(100000);
            $cf = ($cf + 1) % $fc;
            if ((microtime(true) - $start) >= 1) break;
        }
        $wait--;
    }
    echo "\r" . str_repeat(' ', 70) . "\r";
}

function success_banner($title = "SUCCESS", $lines = []) {
    $w = 58;
    echo "\n" . NEON . BOLD . "╔" . str_repeat('═', $w) . "╗" . RESET . "\n";
    echo NEON . BOLD . "║" . RESET . str_pad("  ✓ " . $title, $w) . NEON . BOLD . "║" . RESET . "\n";
    echo NEON . BOLD . "╠" . str_repeat('═', $w) . "╣" . RESET . "\n";
    foreach ($lines as $k => $v) {
        $line = "  " . str_pad($k, 15) . ": " . $v;
        echo NEON . BOLD . "║" . RESET . str_pad($line, $w) . NEON . BOLD . "║" . RESET . "\n";
    }
    echo NEON . BOLD . "╚" . str_repeat('═', $w) . "╝" . RESET . "\n\n";
}

function hack_progress($label = "Bypassing security", $duration = 2.5) {
    $steps = [
        "Analyzing target...",
        "Scanning open ports...",
        "Injecting payload...",
        "Bypassing firewall...",
        "Escalating privileges...",
        "Access granted!",
    ];
    foreach ($steps as $i => $s) {
        echo "  " . NEON_C . "[>]" . RESET . " " . $s;
        $dots = 0;
        while ($dots < 3) {
            echo ".";
            usleep(random_int(80000, 150000));
            $dots++;
        }
        echo " " . NEON . "[OK]" . RESET . "\n";
    }
}

// ═══════════════════════════════════════════════════════════════
//  KONFIGURASI & FUNGSI BOT
// ═══════════════════════════════════════════════════════════════

$CONFIG_FILE  = __DIR__ . "/tronblow_config.json";
$COOKIE_FILE  = __DIR__ . "/cookies_tronblow.txt";
$COUNTER_FILE = __DIR__ . "/tronblow_counter.json";

const DAILY_LIMIT = 200;

function log_msg(string $msg, string $type = "INFO"): void {
    $colors = [
        "SUCCESS" => "\033[32m",
        "ERROR"   => "\033[31m",
        "WARN"    => "\033[33m",
        "INPUT"   => "\033[36m",
        "DEBUG"   => "\033[35m",
        "INFO"    => "\033[0m"
    ];
    $color = $colors[$type] ?? "\033[0m";
    echo $color . "[" . date("H:i:s") . "] [$type] $msg\033[0m\n";
}

function read_line(string $prompt = ""): string {
    if ($prompt) echo $prompt;
    $handle = fopen("php://stdin", "r");
    $line = fgets($handle);
    fclose($handle);
    return trim($line);
}

// ── Counter 200/day ──────────────────────────────────────────
function load_counter(): array {
    global $COUNTER_FILE;
    $today = date("Y-m-d");
    if (file_exists($COUNTER_FILE)) {
        $data = json_decode(file_get_contents($COUNTER_FILE), true);
        if (is_array($data) && ($data['date'] ?? '') === $today) {
            return $data;
        }
    }
    return ['date' => $today, 'count' => 0];
}

function save_counter(array $counter): void {
    global $COUNTER_FILE;
    file_put_contents($COUNTER_FILE, json_encode($counter, JSON_PRETTY_PRINT));
}

function increment_counter(): array {
    $c = load_counter();
    $c['count']++;
    save_counter($c);
    return $c;
}

// ── Config ───────────────────────────────────────────────────
function load_config(): ?array {
    global $CONFIG_FILE;
    if (file_exists($CONFIG_FILE)) {
        $json = file_get_contents($CONFIG_FILE);
        $config = json_decode($json, true);
        if (is_array($config) && !empty($config['email'])) {
            if (!isset($config['base_url'])) $config['base_url'] = 'https://tronblow.site';
            if (!isset($config['delay']))    $config['delay']    = 65;
            if (!isset($config['cookie']))   $config['cookie']   = '';
            return $config;
        }
    }
    return null;
}

function save_config(array $config): void {
    global $CONFIG_FILE;
    file_put_contents($CONFIG_FILE, json_encode($config, JSON_PRETTY_PRINT));
    log_msg("Config saved!", "SUCCESS");
}

// ── HTTP ─────────────────────────────────────────────────────
function fetch_page(string $url, string $cookie_file): array {
    $ch = curl_init($url);
    $headers = [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language: en-GB,en;q=0.9',
        'Sec-Ch-Ua: "Chromium";v="127", "Not)A;Brand";v="99"',
        'Sec-Ch-Ua-Mobile: ?1',
        'Sec-Ch-Ua-Platform: "Android"',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: none',
        'Sec-Fetch-User: ?1',
        'Upgrade-Insecure-Requests: 1'
    ];
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_ENCODING => '',
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_COOKIEJAR => $cookie_file,
        CURLOPT_COOKIEFILE => $cookie_file,
    ]);

    $html = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);

    if ($error) {
        log_msg("cURL Error: $error", "ERROR");
        return ['html' => false, 'http_code' => 0];
    }
    if ($http_code !== 200 || empty($html)) {
        log_msg("HTTP $http_code", "ERROR");
        return ['html' => false, 'http_code' => $http_code];
    }
    return ['html' => $html, 'http_code' => $http_code];
}

function submit_claim(string $url, string $cookie_file, string $email, string $csrf_token, int $math_answer): array {
    $post_data = http_build_query([
        'action'      => 'claim',
        'csrf_token'  => $csrf_token,
        'website'     => '',
        'email'       => $email,
        'math_answer' => $math_answer
    ]);

    $ch = curl_init($url);
    $headers = [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language: en-GB,en;q=0.9',
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . $url,
        'Referer: ' . $url . '/',
        'Sec-Ch-Ua: "Chromium";v="127", "Not)A;Brand";v="99"',
        'Sec-Ch-Ua-Mobile: ?1',
        'Sec-Ch-Ua-Platform: "Android"',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: same-origin',
        'Sec-Fetch-User: ?1',
        'Upgrade-Insecure-Requests: 1'
    ];
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $post_data,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_ENCODING => '',
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_COOKIEJAR => $cookie_file,
        CURLOPT_COOKIEFILE => $cookie_file,
    ]);

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    return ['code' => $http_code, 'body' => (string)$response];
}

// ── Parser ───────────────────────────────────────────────────
function extract_csrf_token(string $html): ?string {
    if (preg_match('/<input\s+type="hidden"\s+name="csrf_token"\s+value="([^"]+)"/i', $html, $m)) {
        return $m[1];
    }
    return null;
}

function extract_math_question(string $html): ?array {
    if (preg_match('/<div\s+class="captcha-q">(.*?)<\/div>/is', $html, $m)) {
        $text = strip_tags($m[1]);
        $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $text = trim($text);
    } else {
        $text = strip_tags($html);
        $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    }

    $text = str_replace(['−', '–', '—', '‐', '‑', '‒', '&minus;'], '-', $text);
    $text = str_replace(['×', '&times;'], '*', $text);
    $text = str_replace(['÷', '&divide;'], '/', $text);

    if (preg_match('/what\s+is\s+(\d+)\s*([+\-*\/])\s*(\d+)\s*=\s*\?/i', $text, $m)) {
        return ['q1' => (int)$m[1], 'op' => $m[2], 'q2' => (int)$m[3]];
    }
    if (preg_match('/(\d+)\s*([+\-*\/])\s*(\d+)\s*=\s*\?/i', $text, $m)) {
        return ['q1' => (int)$m[1], 'op' => $m[2], 'q2' => (int)$m[3]];
    }
    if (preg_match('/(\d+)\s*([+\-*\/])\s*(\d+)\s*=/i', $text, $m)) {
        return ['q1' => (int)$m[1], 'op' => $m[2], 'q2' => (int)$m[3]];
    }
    return null;
}

function solve_math(array $math): int {
    $n1 = $math['q1'];
    $n2 = $math['q2'];
    switch ($math['op']) {
        case '+': return $n1 + $n2;
        case '-': return $n1 - $n2;
        case '*': return $n1 * $n2;
        case '/': return $n2 != 0 ? (int)($n1 / $n2) : 0;
        default: return 0;
    }
}

function extract_endAt(string $html): ?int {
    if (preg_match('/var\s+endAt\s*=\s*(\d+)\s*\*\s*1000/', $html, $m)) {
        return (int)($m[1] * 1000);
    }
    if (preg_match('/endAt\s*=\s*(\d+)\s*\*\s*1000/', $html, $m)) {
        return (int)($m[1] * 1000);
    }
    if (preg_match('/endAt\s*=\s*(\d+)\s*;?/', $html, $m)) {
        return (int)$m[1];
    }
    return null;
}

function check_response(string $html): array {
    $lower = strtolower($html);
    $patterns = [
        'success' => ['success','claimed','reward','sent','received','balance','congratulations'],
        'wait'    => ['wait','countdown','timer','please wait','try again later','time remaining'],
        'wrong'   => ['wrong','incorrect','invalid','error','failed','captcha','try again'],
        'already' => ['already','recently','one claim','per day','limit','maximum'],
        'banned'  => ['banned','blocked','suspicious','bot detected','vpn','proxy']
    ];
    foreach ($patterns as $status => $keywords) {
        foreach ($keywords as $kw) {
            if (strpos($lower, $kw) !== false) {
                return ['status' => $status, 'msg' => ucfirst($status) . " (keyword: '$kw')"];
            }
        }
    }
    return ['status' => 'unknown', 'msg' => 'Unclear response'];
}

function countdown_seconds(int $seconds): void {
    // pakai spinner animasi dari animation pack
    spinner_wait($seconds, "Next claim");
}

// ── Banner Utama ─────────────────────────────────────────────
function print_main_banner(array $config): void {
    $counter = load_counter();
    $remaining = max(0, DAILY_LIMIT - $counter['count']);

    $status_color = $remaining > 50 ? NEON : ($remaining > 10 ? NEON_Y : RED);

    echo NEON . "
╭──────────────────────────────────────────────────────────────╮
│                                                              │
│   ████████╗██████╗  ██████╗ ███╗   ██╗                      │
│   ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║                      │
│      ██║   ██████╔╝██║   ██║██╔██╗ ██║                      │
│      ██║   ██╔══██╗██║   ██║██║╚██╗██║                      │
│      ██║   ██║  ██║╚██████╔╝██║ ╚████║                      │
│      ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝                      │
│                                                              │
│              " . NEON_C . "TRONBLOW // AUTO CLAIM v4.0" . NEON . "              │
│                                                              │
│   " . WHITE . "┌─ SYSTEM ─────────────────────────────────────────┐" . NEON . " │
│   " . WHITE . "│ " . NEON . "● BOT STATUS   : ONLINE" . WHITE . "                      │" . NEON . " │
│   " . WHITE . "│ " . NEON_C . "⚡ CLAIM MODE   : AUTOMATIC" . WHITE . "                   │" . NEON . " │
│   " . WHITE . "│ " . NEON_Y . "💰 REWARD      : 1000 SATOSHI" . WHITE . "                 │" . NEON . " │
│   " . WHITE . "│ " . NEON_P . "⏱ INTERVAL    : 60 SECONDS" . WHITE . "                 │" . NEON . " │
│   " . WHITE . "│ " . ORANGE . "📊 DAILY LIMIT : " . DAILY_LIMIT . " / DAY" . WHITE . "                     │" . NEON . " │
│   " . WHITE . "│ " . $status_color . "🎯 CLAIMED     : " . $counter['count'] . " (" . $remaining . " left)" . WHITE . "             │" . NEON . " │
│   " . WHITE . "└───────────────────────────────────────────────────┘" . NEON . " │
│                                                              │
│             " . NEON_Y . ">>> INITIALIZING CLAIM ENGINE..." . NEON . "             │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
" . RESET . "\n";
}

// ═══════════════════════════════════════════════════════════════
//  INTERACTIVE SETUP
// ═══════════════════════════════════════════════════════════════

function interactive_setup(): array {
    echo "\n" . NEON . "╔════════════════════════════════════════════════╗" . RESET . "\n";
    echo NEON . "║     TRONBLOW FAUCET BOT v4.0                  ║" . RESET . "\n";
    echo NEON . "║     Developer: ScriptyXSouu                   ║" . RESET . "\n";
    echo NEON . "╚════════════════════════════════════════════════╝" . RESET . "\n\n";

    $config = [];
    echo NEON_C . "[1/2] Enter your FaucetPay email:" . RESET . "\n";
    $config['email'] = read_line("Email: ");
    while (empty($config['email']) || !filter_var($config['email'], FILTER_VALIDATE_EMAIL)) {
        log_msg("Invalid email!", "WARN");
        $config['email'] = read_line("Email: ");
    }

    $config['base_url'] = "https://tronblow.site";
    $config['delay'] = 65;
    $config['cookie'] = '';

    echo "\n" . NEON . "Config saved!" . RESET . "\n";
    return $config;
}

// ═══════════════════════════════════════════════════════════════
//  MAIN EXECUTION
// ═══════════════════════════════════════════════════════════════

clear_screen();

// 1. Efek boot ala hacker
hacking_boot([
    "Initializing kernel module...",
    "Loading anti-bot engine...",
    "Rotating device fingerprint...",
    "Injecting stealth headers...",
    "Connecting to remote server...",
    "Bypassing security layers...",
    "Loading session cookies...",
    "System ready.",
]);
echo "\n";

// 2. Decrypt title
decrypt_text("TRONBLOW AUTO CLAIM ENGINE v4.0", 1.2);
glitch_text("MAX 200 CLAIM/DAY • 1000 SATOSHI/CLAIM", 0.8);
echo "\n";

// 3. Loading modules
loading_bar("Loading modules", 1.0);
loading_bar("Fetching cookies", 0.8);
scan_line("Reading target", 40);
echo "\n";

// 4. Load config
$config = load_config();
if ($config) {
    log_msg("Saved config found!", "SUCCESS");
    echo "  Email: {$config['email']}\n";
    echo "  URL:   {$config['base_url']}\n";
    echo "  Delay: {$config['delay']}s\n\n";
    $use = read_line("\033[36mUse saved? (y/n/reconfig): \033[0m");
    if ($use === 'n' || $use === 'reconfig') {
        $config = interactive_setup();
    }
} else {
    $config = interactive_setup();
}

if (empty($config['email']) || empty($config['base_url'])) {
    log_msg("Invalid configuration!", "ERROR");
    exit(1);
}
if (!isset($config['delay'])) $config['delay'] = 65;
if (!isset($config['cookie'])) $config['cookie'] = '';

if (!file_exists($COOKIE_FILE)) {
    touch($COOKIE_FILE);
}

// 5. Banner utama dengan info 200/day
print_main_banner($config);

// 6. Efek hack sebelum mulai
hack_progress("Hacking server");
echo "\n";
faucet_progress("Bypassing Cloudflare", 1.5);
echo "\n";

log_msg("=== BOT STARTED ===", "SUCCESS");
log_msg("Daily limit: " . DAILY_LIMIT . " claims", "INFO");
log_msg("Press Ctrl+C to stop", "WARN");
echo "\n";

$cycle = 0;
while (true) {
    // Cek limit harian
    $counter = load_counter();
    if ($counter['count'] >= DAILY_LIMIT) {
        log_msg("🚫 Daily limit reached ({$counter['count']}/" . DAILY_LIMIT . "). Waiting for reset...", "WARN");
        $secs_until_reset = strtotime("tomorrow 00:00 UTC") - time();
        if ($secs_until_reset > 0) spinner_wait($secs_until_reset, "Reset in");
        continue;
    }

    $cycle++;
    echo "\n" . NEON_P . "╭─── CYCLE #$cycle ─── " . date("H:i:s") . " ─── " . $counter['count'] . "/" . DAILY_LIMIT . " ───╮" . RESET . "\n";

    $result = fetch_page($config['base_url'], $COOKIE_FILE);
    if (!$result['html']) {
        log_msg("Failed to fetch page. Retry in 30s...", "ERROR");
        spinner_wait(30, "Retry");
        continue;
    }
    $html = $result['html'];

    $lower = strtolower($html);
    if (strpos($lower, 'cf-browser-verification') !== false ||
        strpos($lower, 'challenge-platform') !== false ||
        strpos($lower, 'just a moment') !== false) {
        log_msg("Cloudflare challenge detected! Clearing cookies...", "WARN");
        glitch_text("!! CLOUDFLARE CHALLENGE DETECTED !!", 0.6);
        unlink($COOKIE_FILE);
        touch($COOKIE_FILE);
        spinner_wait(60, "Cooldown");
        continue;
    }

    $csrf = extract_csrf_token($html);
    if (!$csrf) {
        log_msg("CSRF token not found! Retry in 30s...", "ERROR");
        spinner_wait(30, "Retry");
        continue;
    }
    log_msg("CSRF: " . substr($csrf, 0, 10) . "...", "DEBUG");

    $math = extract_math_question($html);
    if (!$math) {
        log_msg("Could not extract math question. Retry in 30s...", "ERROR");
        spinner_wait(30, "Retry");
        continue;
    }
    $answer = solve_math($math);
    log_msg("Math: {$math['q1']} {$math['op']} {$math['q2']} = $answer", "SUCCESS");

    // Animasi dekripsi payload
    decrypt_text("SOLVING CAPTCHA → " . $answer, 0.6);

    // Animasi progress claim
    faucet_progress("Claiming 1000 SATOSHI", 2.0);

    $submit = submit_claim($config['base_url'], $COOKIE_FILE, $config['email'], $csrf, $answer);
    log_msg("HTTP Status: {$submit['code']}", "INFO");

    $status = check_response($submit['body']);
    $wait_seconds = $config['delay'];

    switch ($status['status']) {
        case 'success':
            $counter = increment_counter();
            $remaining = max(0, DAILY_LIMIT - $counter['count']);

            success_banner("CLAIM COMPLETED", [
                "Reward"     => "1000 SATOSHI TRX",
                "Account"    => $config['email'],
                "Progress"   => $counter['count'] . "/" . DAILY_LIMIT . " today",
                "Remaining"  => $remaining . " claims left",
                "Next"       => "Auto-wait...",
            ]);

            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $now = time() * 1000;
                $wait_ms = $endAt - $now;
                if ($wait_ms > 0) $wait_seconds = (int)ceil($wait_ms / 1000);
            }
            break;

        case 'wait':
        case 'already':
            log_msg("⏳ Cooldown active. Waiting for server timer.", "WARN");
            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $now = time() * 1000;
                $wait_ms = $endAt - $now;
                if ($wait_ms > 0) $wait_seconds = (int)ceil($wait_ms / 1000);
            }
            break;

        case 'wrong':
            log_msg("❌ Math answer wrong! Retrying with new page...", "ERROR");
            glitch_text("!! CAPTCHA FAILED !!", 0.5);
            spinner_wait(10, "Retry");
            continue 2;

        case 'banned':
            log_msg("🚫 ACCOUNT BANNED! Exiting...", "ERROR");
            glitch_text("!! ACCESS DENIED — BANNED !!", 0.8);
            exit(1);

        default:
            log_msg("❓ Unknown response: {$status['msg']}", "WARN");
            $endAt = extract_endAt($submit['body']);
            if ($endAt) {
                $now = time() * 1000;
                $wait_ms = $endAt - $now;
                if ($wait_ms > 0) $wait_seconds = (int)ceil($wait_ms / 1000);
            }
    }

    echo NEON . "╰─────────────────────────────────────────────╯" . RESET . "\n";

    if ($wait_seconds > 0) {
        spinner_wait($wait_seconds, "Next claim");
    } else {
        log_msg("No timer found, using default delay {$config['delay']}s", "WARN");
        spinner_wait($config['delay'], "Next claim");
    }
}
