<?php
/**
 * 99FAUCET AUTO BOT v2.0
 * - Solver: WARYONO.MY.ID
 * - Detection pattern dari script kedua (Good job!, Invalid, dll)
 * - Total claim per coin + earning USD
 * - IP display + stats persistent
 */

error_reporting(0);
date_default_timezone_set('Asia/Jakarta');

// ═══════════════ COLORS ═══════════════
const RESET  = "\033[0m";
const BOLD   = "\033[1m";
const DIM    = "\033[2m";
const MERAH  = "\033[1;31m";
const HIJAU  = "\033[1;32m";
const KUNING = "\033[1;33m";
const BIRU   = "\033[1;34m";
const CYAN   = "\033[1;36m";
const PUTIH  = "\033[1;37m";
const UNGU   = "\033[1;35m";
const ABU    = "\033[0;90m";

// ═══════════════ CONFIG ═══════════════
const BASE_URL      = 'https://99faucet.com';
const API_IN        = 'https://api.waryono.my.id/in.php';
const API_OUT       = 'https://api.waryono.my.id/res.php';
const CONFIG_FILE   = 'config_99.json';
const STATS_FILE    = 'stats_99.json';
const COOKIE_FILE   = 'cookie_99.txt';
const SUCCESS_WAIT  = 20;
const FAIL_WAIT     = 11;
const PRICE_PER_CLAIM = 0.0001;   // USDT

const FALLBACK_SITEKEY = 'e6ca07e2-687c-4fca-b47c-d5fc5ed2e188';

// ═══════════════ HELPERS ═══════════════
function clear() { (PHP_OS == 'Linux') ? system('clear') : pclose(popen('cls', 'w')); }

function line($text) { echo "\r\033[K" . $text; }

function timer($seconds, $prefix = "[!] Please wait") {
    $wait = (int)$seconds;
    if ($wait <= 0) return;
    $frames = ['⣾','⣽','⣻','⢿','⡿','⣟','⣯','⣷'];
    $fc = count($frames); $cf = 0;
    while ($wait > 0) {
        $st = microtime(true);
        while ((microtime(true) - $st) < 1) {
            $h = floor($wait / 3600);
            $m = floor(($wait % 3600) / 60);
            $s = $wait % 60;
            $tf = sprintf('%02d:%02d:%02d', $h, $m, $s);
            echo "\r\033[K" . PUTIH . $prefix . HIJAU . " $tf " . PUTIH . $frames[$cf] . RESET;
            usleep(100000);
            $cf = ($cf + 1) % $fc;
            if ((microtime(true) - $st) >= 1) break;
        }
        $wait--;
    }
    echo "\r\033[K";
}

// ═══════════════ IP FETCH ═══════════════
function get_public_ip() {
    $endpoints = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
    ];
    foreach ($endpoints as $ep) {
        $ch = curl_init($ep);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 8,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_USERAGENT => 'Mozilla/5.0',
        ]);
        $r = curl_exec($ch);
        curl_close($ch);
        if ($r && strlen(trim($r)) > 5 && strlen(trim($r)) < 46) {
            return trim($r);
        }
    }
    return 'unknown';
}

// ═══════════════ COOKIE JAR ═══════════════
class CookieJar {
    private $cookies = [];
    public function set($n, $v) { $this->cookies[$n] = $v; }
    public function get($n) { return $this->cookies[$n] ?? null; }
    public function getAll() { return $this->cookies; }

    public function parseSetCookie($header) {
        preg_match_all('/Set-Cookie:\s*([^;]+)/i', $header, $m);
        if (!empty($m[1])) {
            foreach ($m[1] as $cl) {
                $p = explode('=', $cl, 2);
                if (count($p) == 2) $this->cookies[trim($p[0])] = trim($p[1]);
            }
        }
    }

    public function toString() {
        $s = '';
        foreach ($this->cookies as $k => $v) $s .= "$k=$v; ";
        return rtrim($s, '; ');
    }

    public function fromString($str) {
        if (empty($str)) return;
        foreach (explode(';', $str) as $pair) {
            $p = explode('=', trim($pair), 2);
            if (count($p) == 2) $this->cookies[$p[0]] = $p[1];
        }
    }
}

// ═══════════════ HTTP ═══════════════
function http_request($url, $method = 'GET', $data = [], $headers = [], CookieJar &$jar = null, &$finalUrl = null, $follow = true) {
    if ($jar === null) $jar = new CookieJar();

    $ch = curl_init();
    $opts = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HEADER         => true,
        CURLOPT_FOLLOWLOCATION => $follow,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_CONNECTTIMEOUT => 30,
        CURLOPT_USERAGENT      => 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
    ];
    $cs = $jar->toString();
    if (!empty($cs)) $opts[CURLOPT_COOKIE] = $cs;

    if (strtoupper($method) === 'POST') {
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = http_build_query($data);
    }
    if (!empty($headers)) $opts[CURLOPT_HTTPHEADER] = $headers;

    curl_setopt_array($ch, $opts);
    $response = curl_exec($ch);
    if ($response === false) { curl_close($ch); return null; }

    $hdrSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $body = substr($response, $hdrSize);
    $header = substr($response, 0, $hdrSize);
    $finalUrl = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);

    $jar->parseSetCookie($header);
    curl_close($ch);
    return $body;
}

function http_nocookie($url, $method = 'GET', $data = [], $headers = [], $json_body = false) {
    $ch = curl_init();
    $opts = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_CONNECTTIMEOUT => 30,
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

// ═══════════════ STATS ═══════════════
function load_stats() {
    if (!file_exists(STATS_FILE)) return ['coins' => [], 'total_claims' => 0, 'total_usd' => 0.0];
    $d = json_decode(file_get_contents(STATS_FILE), true);
    if (!is_array($d)) return ['coins' => [], 'total_claims' => 0, 'total_usd' => 0.0];
    if (!isset($d['coins'])) $d['coins'] = [];
    if (!isset($d['total_claims'])) $d['total_claims'] = 0;
    if (!isset($d['total_usd'])) $d['total_usd'] = 0.0;
    return $d;
}

function save_stats($s) {
    file_put_contents(STATS_FILE, json_encode($s, JSON_PRETTY_PRINT));
}

function record_claim($coin, $amount_usd = PRICE_PER_CLAIM) {
    $s = load_stats();
    if (!isset($s['coins'][$coin])) $s['coins'][$coin] = ['claims' => 0, 'usd' => 0.0];
    $s['coins'][$coin]['claims']++;
    $s['coins'][$coin]['usd'] += $amount_usd;
    $s['total_claims']++;
    $s['total_usd'] += $amount_usd;
    save_stats($s);
    return $s;
}

// ═══════════════ WARYONO SOLVER ═══════════════
function solve_hcaptcha($apikey, $sitekey, $pageurl) {
    $attempt = 0;
    while ($attempt < 5) {
        $attempt++;
        $payload = json_encode([
            "apikey"  => $apikey,
            "methods" => "hcaptcha",
            "domain"  => $pageurl,
            "sitekey" => $sitekey,
            "json"    => 1,
        ]);

        $res = http_nocookie(API_IN, 'POST', $payload, ["Content-Type: application/json"], true);
        $json = json_decode($res, true);
        $id = $json["request"] ?? null;

        if (!$id || strpos($id, "ERROR_") !== false) {
            $err = $json["request"] ?? "no response";
            echo MERAH . "[!] Submit gagal ($err) — retry #$attempt" . RESET . "\n";
            if (is_string($err) && (
                strpos($err, 'ERROR_KEY') !== false ||
                strpos($err, 'ERROR_WRONG_USER_KEY') !== false ||
                strpos($err, 'ERROR_ZERO_BALANCE') !== false
            )) {
                echo MERAH . "[💀] API key / saldo Waryono bermasalah. Stop." . RESET . "\n";
                return null;
            }
            sleep(3);
            continue;
        }

        echo KUNING . "[+] Task ID    : $id" . RESET . "\n";
        echo CYAN  . "[*] hCaptcha    : WAITING..." . RESET . "\n";

        for ($i = 1; $i <= 60; $i++) {
            sleep(5);
            $url = API_OUT . "?apikey=" . urlencode($apikey) . "&id=" . urlencode($id) . "&action=get&json=1";
            $r = http_nocookie($url);

            line(PUTIH . "[*] Polling     : " . ($i * 5) . "s " . HIJAU . "⣾");

            if (strpos($r, "CAPCHA_NOT_READY") !== false) continue;

            $d = json_decode($r, true);
            if ($d && isset($d["request"])
                && strpos($d["request"], "ERROR_") === false
                && $d["request"] !== "CAPCHA_NOT_READY") {
                echo "\r\033[K" . HIJAU . "[+] hCaptcha   : SOLVED ✓" . RESET . "\n";
                return $d["request"];
            }
            echo "\r\033[K" . MERAH . "[!] Solver error: " . ($d["request"] ?? $r) . RESET . "\n";
            break;
        }
        sleep(3);
    }
    return null;
}

// ═══════════════ 99FAUCET DETECTION ═══════════════
function get_sitekey($html) {
    if (preg_match('/class="h-captcha"\s+data-sitekey="([^"]+)"/i', $html, $m)) return $m[1];
    if (preg_match('/data-sitekey="([^"]+)"/', $html, $m)) return $m[1];
    if (preg_match('/sitekey:\s*"([^"]+)"/', $html, $m)) return $m[1];
    return null;
}

function is_logged_in($html) {
    return strpos($html, 'Logout') !== false
        || strpos($html, 'Dashboard') !== false
        || strpos($html, 'Dashboard | 99Faucet') !== false;
}

function is_shortlink_page($html) {
    return strpos($html, 'Shortlinks | 99Faucet') !== false
        || strpos($html, 'You Need to Complete') !== false
        || strpos($html, 'Click To Visit') !== false;
}

function generate_uf() { return md5(uniqid(mt_rand(), true)); }

function get_config() {
    if (!file_exists(CONFIG_FILE)) return null;
    return json_decode(file_get_contents(CONFIG_FILE), true);
}
function save_config($cfg) {
    file_put_contents(CONFIG_FILE, json_encode($cfg, JSON_PRETTY_PRINT));
}

// ═══════════════ UI / BANNER ═══════════════
function print_banner($ip, $stats) {
    $lines = [
        "",
        CYAN . "╔══════════════════════════════════════════════════════════╗" . RESET,
        CYAN . "║" . RESET . BOLD . KUNING . "              🍪 99FAUCET AUTO BOT v2.0                   " . RESET . CYAN . "║" . RESET,
        CYAN . "║" . RESET . DIM . PUTIH . "              Solver: WARYONO.MY.ID                        " . RESET . CYAN . "║" . RESET,
        CYAN . "╠══════════════════════════════════════════════════════════╣" . RESET,
        CYAN . "║" . RESET . PUTIH . " 🌐 IP Address  : " . HIJAU . str_pad($ip, 38) . RESET . CYAN . "║" . RESET,
        CYAN . "║" . RESET . PUTIH . " 💰 Price/claim : " . KUNING . str_pad(number_format(PRICE_PER_CLAIM, 4) . " USDT", 38) . RESET . CYAN . "║" . RESET,
        CYAN . "║" . RESET . PUTIH . " 📊 Total Claim : " . CYAN . str_pad($stats['total_claims'], 38) . RESET . CYAN . "║" . RESET,
        CYAN . "║" . RESET . PUTIH . " 💵 Total Earn  : " . HIJAU . str_pad(number_format($stats['total_usd'], 6) . " USDT", 38) . RESET . CYAN . "║" . RESET,
        CYAN . "╚══════════════════════════════════════════════════════════╝" . RESET,
    ];
    foreach ($lines as $l) echo $l . "\n";
}

function print_coin_table($coins, $stats, $emoji_map) {
    echo "\n" . KUNING . "💰 Coin yang tersedia:" . RESET . "\n";
    echo ABU . "  ┌────┬────────┬───────────┬──────────────┬────────────────┐" . RESET . "\n";
    echo ABU . "  │ " . PUTIH . "#  " . ABU . "│ " . PUTIH . "Coin   " . ABU . "│ " . PUTIH . "Claimed   " . ABU . "│ " . PUTIH . "Earned (USD) " . ABU . "│ " . PUTIH . "Last claim     " . ABU . "│" . RESET . "\n";
    echo ABU . "  ├────┼────────┼───────────┼──────────────┼────────────────┤" . RESET . "\n";
    foreach ($coins as $i => $coin) {
        $num = $i + 1;
        $emoji = $emoji_map[$coin] ?? '🪙';
        $c = $stats['coins'][$coin] ?? ['claims' => 0, 'usd' => 0.0, 'last' => '-'];
        $last = $c['last'] ?? '-';
        if (strlen($last) > 14) $last = substr($last, 0, 14);
        printf(
            ABU . "  │ " . HIJAU . "%-3d" . ABU . "│ " . PUTIH . "%s %-4s" . ABU . "│ " . CYAN . "%-9d" . ABU . "│ " . HIJAU . "%-12s" . ABU . "│ " . ABU . "%-14s" . ABU . "│" . RESET . "\n",
            $num,
            $emoji,
            strtoupper($coin),
            $c['claims'],
            number_format($c['usd'], 6),
            $last
        );
    }
    echo ABU . "  └────┴────────┴───────────┴──────────────┴────────────────┘" . RESET . "\n\n";
}

// ═══════════════ LOGIN ═══════════════
function login(CookieJar &$jar, $email, $password, $apikey) {
    echo CYAN . "[*] Login via email..." . RESET . "\n";
    $home = http_request(BASE_URL, 'GET', [], [], $jar);
    if (!$home) { echo MERAH . "[!] Gagal akses homepage." . RESET . "\n"; return false; }

    if (!$jar->get('uf')) $jar->set('uf', generate_uf());

    $sitekey = get_sitekey($home) ?: FALLBACK_SITEKEY;
    echo KUNING . "[+] Sitekey    : $sitekey" . RESET . "\n";

    $captcha = solve_hcaptcha($apikey, $sitekey, BASE_URL);
    if (!$captcha) return false;

    $data = [
        'email'                 => $email,
        'password'              => $password,
        'captcha'               => 'hcaptcha',
        'g-recaptcha-response'  => $captcha,
        'h-captcha-response'    => $captcha,
        'captcha_choosen'       => '',
        'uf'                    => $jar->get('uf'),
        'utt'                   => 'Asia/Jakarta',
        'ls'                    => 'id-ID'
    ];

    http_request(BASE_URL . "/auth/login", 'POST', $data, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . BASE_URL,
        'Referer: ' . BASE_URL . '/',
    ], $jar);

    $dash = http_request(BASE_URL . "/dashboard", 'GET', [], [], $jar);
    if ($dash && is_logged_in($dash)) {
        echo HIJAU . "[+] Login sukses!" . RESET . "\n";
        return true;
    }
    echo MERAH . "[!] Login gagal." . RESET . "\n";
    return false;
}

// ═══════════════ GET COINS ═══════════════
function get_coins(CookieJar &$jar) {
    $result = http_request(BASE_URL . "/dashboard", 'GET', [], [], $jar);
    if (!$result) return [];
    preg_match_all('/href="https:\/\/99faucet\.com\/faucet\/([^"\/]+)"/', $result, $m);
    if (!empty($m[1])) {
        $coins = array_values(array_unique($m[1]));
        // filter yang bukan dashboard/links
        $coins = array_filter($coins, function($c) {
            return !in_array($c, ['', 'dashboard', 'links', 'logout', 'login']);
        });
        $coins = array_values($coins);
        usort($coins, function($a, $b) { return strlen($a) - strlen($b); });
        return $coins;
    }
    return [];
}

// ═══════════════ GET FAUCET PAGE ═══════════════
function get_faucet_page(CookieJar &$jar, $coin, &$finalUrl = null) {
    $url = BASE_URL . "/faucet/$coin";
    $result = http_request($url, 'GET', [], [], $jar, $finalUrl);
    if (!$result) return null;

    if ($finalUrl && strpos($finalUrl, '/links/') !== false) {
        return ['status' => 'shortlink', 'url' => $finalUrl];
    }
    if (is_shortlink_page($result)) {
        return ['status' => 'shortlink', 'url' => $url];
    }

    preg_match('/name="token"\s+value="([^"]+)"/', $result, $tm);
    preg_match('/<input[^>]+name="token"\s+value="([^"]+)"/i', $result, $tm2);
    $token = $tm[1] ?? $tm2[1] ?? null;

    preg_match('/id="minute">(\d+)/', $result, $min);
    preg_match('/id="second">(\d+)/', $result, $sec);
    $wait = 0;
    if (!empty($min) && !empty($sec)) $wait = (int)$min[1] * 60 + (int)$sec[1];

    $sitekey = get_sitekey($result) ?: FALLBACK_SITEKEY;

    return ['status' => 'ok', 'token' => $token, 'html' => $result, 'wait_time' => $wait, 'sitekey' => $sitekey];
}

function wait_for_cooldown(CookieJar &$jar, $coin) {
    echo KUNING . "[*] Cek cooldown..." . RESET . "\n";
    $max = 600; $total = 0;
    while ($total < $max) {
        $page = get_faucet_page($jar, $coin);
        if (!$page) break;
        if ($page['status'] === 'shortlink') return 'SHORTLINK';
        $wait = $page['wait_time'] ?? 0;
        if ($wait <= 0) { echo HIJAU . "[+] Cooldown selesai." . RESET . "\n"; return true; }
        $m = floor($wait / 60); $s = $wait % 60;
        echo "\r\033[K" . KUNING . "[!] Cooldown " . sprintf("%02d:%02d", $m, $s) . " - menunggu..." . RESET;
        sleep(2); $total += 2;
    }
    return false;
}

// ═══════════════ CLAIM (detection dari script 2) ═══════════════
function claim_faucet(CookieJar &$jar, $coin, $apikey) {
    echo CYAN . "[*] Claim      : PROCESSING... (coin: " . strtoupper($coin) . ")" . RESET . "\n";

    $finalUrl = null;
    $page = get_faucet_page($jar, $coin, $finalUrl);
    if (!$page) { echo MERAH . "[!] Gagal ambil halaman faucet." . RESET . "\n"; return false; }
    if ($page['status'] === 'shortlink') return 'SHORTLINK';

    $cd = wait_for_cooldown($jar, $coin);
    if ($cd === 'SHORTLINK') return 'SHORTLINK';
    if (!$cd) { echo MERAH . "[!] Gagal menunggu cooldown." . RESET . "\n"; return false; }

    $page = get_faucet_page($jar, $coin);
    if (!$page || $page['status'] === 'shortlink') return 'SHORTLINK';

    $token = $page['token'];
    $sitekey = $page['sitekey'];

    if (!$token || !$sitekey) {
        echo MERAH . "[!] Token / sitekey kosong." . RESET . "\n";
        return false;
    }

    echo KUNING . "[+] Token      : $token" . RESET . "\n";
    echo KUNING . "[+] Sitekey    : " . substr($sitekey, 0, 20) . "..." . RESET . "\n";

    $url = BASE_URL . "/faucet/$coin";
    $captcha = solve_hcaptcha($apikey, $sitekey, $url);
    if (!$captcha) return false;

    $data = [
        'ci_csrf_token'         => '',
        'token'                 => $token,
        'currency'              => $coin,
        'captcha'               => 'hcaptcha',
        'g-recaptcha-response'  => $captcha,
        'h-captcha-response'    => $captcha,
        'uf'                    => generate_uf(),
        'utt'                   => 'Asia/Jakarta',
        'ls'                    => 'id-ID,id,en-US,en'
    ];

    $result = http_request(BASE_URL . "/faucet/verify", 'POST', $data, [
        'Content-Type: application/x-www-form-urlencoded',
        'Origin: ' . BASE_URL,
        'Referer: ' . $url,
    ], $jar);

    if (!$result) { echo MERAH . "[!] Gagal claim (no response)." . RESET . "\n"; return false; }

    // ─── DETECTION (dari script 2) ───
    if (strpos($result, 'Good job!') !== false) {
        $msg = '';
        if (preg_match('/text:\s*[\'"]?([^\'"<]+)/', $result, $r)) $msg = $r[1];
        echo HIJAU . "[+] Claim      : SUCCESS ✓" . RESET . "\n";
        if ($msg) echo KUNING . "[+] Message    : $msg" . RESET . "\n";
        return true;
    }

    if (stripos($result, 'Invalid') !== false) {
        echo MERAH . "[!] Invalid captcha / claim!" . RESET . "\n";
        return 'INVALID';
    }

    if (stripos($result, 'insufficient funds') !== false) {
        echo KUNING . "[!] Faucet kehabisan dana (insufficient funds)." . RESET . "\n";
        return 'INSUFFICIENT';
    }

    if (is_shortlink_page($result)) return 'SHORTLINK';

    // Cooldown pattern
    preg_match('/id="minute">(\d+)/', $result, $min);
    preg_match('/id="second">(\d+)/', $result, $sec);
    if (!empty($min) && !empty($sec)) {
        $wait = (int)$min[1] * 60 + (int)$sec[1];
        if ($wait > 0) { echo KUNING . "[!] Cooldown $wait detik." . RESET . "\n"; return 'COOLDOWN'; }
    }

    if (strpos($result, 'has been sent') !== false || stripos($result, 'success') !== false) {
        echo HIJAU . "[+] Claim      : SUCCESS ✓" . RESET . "\n";
        return true;
    }

    if (stripos($result, 'login') !== false && strlen($result) < 500) {
        echo MERAH . "[!] Session expired." . RESET . "\n";
        return 'EXPIRED';
    }

    echo MERAH . "[?] Claim tidak jelas → claim_debug_99.html" . RESET . "\n";
    file_put_contents("claim_debug_99.html", $result);
    return false;
}

// ═══════════════ MAIN ═══════════════
clear();
$ip = get_public_ip();
$stats = load_stats();
$stats['ip'] = $ip;   // simpan IP terakhir

$config = get_config();

if ($config && isset($config['login_method'])) {
    echo CYAN . "Config ditemukan. Login: " . $config['login_method'] . RESET . "\n";
    echo PUTIH . "Gunakan config yang ada? (y/n): " . KUNING;
    $use = trim(fgets(STDIN));
    echo RESET;
    if (strtolower($use) === 'y') {
        $login_data = [
            'login_method' => $config['login_method'],
            'email'        => $config['email']    ?? '',
            'password'     => $config['password'] ?? '',
            'apikey'       => $config['apikey']   ?? '',
            'cookie'       => $config['cookie']   ?? ''
        ];
    } else {
        // ── Setup baru ──
        clear();
        print_banner($ip, $stats);
        echo "\n" . PUTIH . "Pilih metode login:\n";
        echo HIJAU . "  [1] " . PUTIH . "Cookie\n";
        echo HIJAU . "  [2] " . PUTIH . "Email + Password\n";
        echo PUTIH . "Pilihan (1/2): " . KUNING;
        $choice = trim(fgets(STDIN));
        echo RESET;
        if ($choice == '2') {
            echo PUTIH . "Email: " . KUNING;
            $email = trim(fgets(STDIN));
            echo PUTIH . "Password: " . KUNING;
            system('stty -echo');
            $password = trim(fgets(STDIN));
            system('stty echo');
            echo "\n" . PUTIH . "API Key Waryono: " . KUNING;
            $apikey = trim(fgets(STDIN));
            echo RESET;
            $login_data = ['login_method'=>'email','email'=>$email,'password'=>$password,'apikey'=>$apikey,'cookie'=>''];
        } else {
            echo PUTIH . "Cookie: " . KUNING;
            $cookie = trim(fgets(STDIN));
            echo PUTIH . "API Key Waryono: " . KUNING;
            $apikey = trim(fgets(STDIN));
            echo RESET;
            $login_data = ['login_method'=>'cookie','email'=>'','password'=>'','apikey'=>$apikey,'cookie'=>$cookie];
        }
    }
} else {
    clear();
    print_banner($ip, $stats);
    echo "\n" . PUTIH . "Pilih metode login:\n";
    echo HIJAU . "  [1] " . PUTIH . "Cookie\n";
    echo HIJAU . "  [2] " . PUTIH . "Email + Password\n";
    echo PUTIH . "Pilihan (1/2): " . KUNING;
    $choice = trim(fgets(STDIN));
    echo RESET;
    if ($choice == '2') {
        echo PUTIH . "Email: " . KUNING;
        $email = trim(fgets(STDIN));
        echo PUTIH . "Password: " . KUNING;
        system('stty -echo');
        $password = trim(fgets(STDIN));
        system('stty echo');
        echo "\n" . PUTIH . "API Key Waryono: " . KUNING;
        $apikey = trim(fgets(STDIN));
        echo RESET;
        $login_data = ['login_method'=>'email','email'=>$email,'password'=>$password,'apikey'=>$apikey,'cookie'=>''];
    } else {
        echo PUTIH . "Cookie: " . KUNING;
        $cookie = trim(fgets(STDIN));
        echo PUTIH . "API Key Waryono: " . KUNING;
        $apikey = trim(fgets(STDIN));
        echo RESET;
        $login_data = ['login_method'=>'cookie','email'=>'','password'=>'','apikey'=>$apikey,'cookie'=>$cookie];
    }
}

save_config($login_data);

// ─── AUTH ───
clear();
print_banner($ip, $stats);
echo KUNING . "[*] Login method: " . $login_data['login_method'] . RESET . "\n";
echo KUNING . "[*] Solver      : WARYONO.MY.ID" . RESET . "\n";

$jar = new CookieJar();

if ($login_data['login_method'] === 'cookie') {
    if (empty($login_data['cookie'])) { echo MERAH . "[!] Cookie kosong!" . RESET . "\n"; exit(1); }
    $jar->fromString($login_data['cookie']);
    echo HIJAU . "[+] Cookie loaded." . RESET . "\n";
    $dash = http_request(BASE_URL . "/dashboard", 'GET', [], [], $jar);
    if ($dash && is_logged_in($dash)) {
        echo HIJAU . "[+] Session aktif dengan cookie!" . RESET . "\n";
    } else {
        echo MERAH . "[!] Cookie tidak valid / expired." . RESET . "\n";
        exit(1);
    }
} else {
    $dash = http_request(BASE_URL . "/dashboard", 'GET', [], [], $jar);
    if ($dash && is_logged_in($dash)) {
        echo HIJAU . "[+] Session aktif!" . RESET . "\n";
    } else {
        echo KUNING . "[*] Session tidak aktif, mencoba login..." . RESET . "\n";
        if (!login($jar, $login_data['email'], $login_data['password'], $login_data['apikey'])) {
            echo MERAH . "[!] Login gagal. Cek config." . RESET . "\n";
            exit(1);
        }
        $login_data['cookie'] = $jar->toString();
        save_config($login_data);
        echo HIJAU . "[+] Cookie disimpan." . RESET . "\n";
    }
}

// ─── COIN PICKER ───
$coins = get_coins($jar);
if (empty($coins)) { echo MERAH . "[!] Gagal ambil daftar coin." . RESET . "\n"; exit(1); }

$emoji_map = [
    'ltc'=>'🪙','dgb'=>'💎','trx'=>'🔥','bch'=>'💵','bnb'=>'🟡','sol'=>'☀️',
    'xrp'=>'💧','pol'=>'🟣','ada'=>'🔵','ton'=>'💎','xlm'=>'🌟','eth'=>'♦️',
    'usdt'=>'💵','dash'=>'🟠','doge'=>'🐕','usdc'=>'💵','pepe'=>'🐸','trump'=>'🇺🇸'
];

clear();
print_banner($ip, $stats);
print_coin_table($coins, $stats, $emoji_map);

echo CYAN . "🎯 Pilih nomor coin: " . RESET;
$choice = trim(fgets(STDIN));
$idx = (int)$choice - 1;
$coin = $coins[$idx] ?? $coins[0];
echo HIJAU . "✅ Coin dipilih: " . strtoupper($coin) . RESET . "\n";

// ─── LOOP ───
$count = 0;
$session_claims = 0;

while (true) {
    $count++;
    $stats = load_stats();
    $stats['ip'] = $ip;

    echo "\n" . CYAN . "┌─[ ROUND $count ]─── " . date('H:i:s') . " ──" . RESET . "\n";

    $result = claim_faucet($jar, $coin, $login_data['apikey']);

    if ($result === 'EXPIRED') {
        echo KUNING . "[*] Session expired. Refresh..." . RESET . "\n";
        if ($login_data['login_method'] === 'email') {
            if (login($jar, $login_data['email'], $login_data['password'], $login_data['apikey'])) {
                $login_data['cookie'] = $jar->toString();
                save_config($login_data);
                echo HIJAU . "[+] Session refresh sukses!" . RESET . "\n";
                continue;
            }
        } else {
            echo MERAH . "[!] Cookie expired. Update cookie di config." . RESET . "\n";
            break;
        }
    }

    if ($result === 'SHORTLINK') {
        echo MERAH . "[!] Shortlink terdeteksi!" . RESET . "\n";
        echo KUNING . "[*] Selesaikan shortlink manual di browser:" . RESET . "\n";
        echo PUTIH . "    " . BASE_URL . "/links/" . $coin . RESET . "\n";
        echo PUTIH . "    Tekan Enter setelah selesai..." . RESET;
        trim(fgets(STDIN));
        continue;
    }

    if ($result === 'INSUFFICIENT') {
        echo KUNING . "⚠ Faucet kehabisan dana. Coba coin lain atau tunggu." . RESET . "\n";
        timer(60, "⏳ Retry in");
        continue;
    }

    if ($result === 'INVALID') {
        echo KUNING . "⚠ Captcha invalid, retry..." . RESET . "\n";
        timer(FAIL_WAIT, "🔄 Retry in");
        continue;
    }

    if ($result === 'COOLDOWN') {
        timer(FAIL_WAIT, "🔄 Retry in");
        continue;
    }

    if ($result === true) {
        $session_claims++;
        $stats = record_claim($coin);
        $stats['ip'] = $ip;
        echo HIJAU . "✅ Claim sukses! (" . $session_claims . " session total)" . RESET . "\n";
        echo KUNING . "💰 Coin " . strtoupper($coin) . " : " . ($stats['coins'][$coin]['claims'] ?? 0) . " claims = " . number_format($stats['coins'][$coin]['usd'] ?? 0, 6) . " USDT" . RESET . "\n";
        echo UNGU  . "📊 GRAND TOTAL : " . $stats['total_claims'] . " claims = " . number_format($stats['total_usd'], 6) . " USDT" . RESET . "\n";
        timer(SUCCESS_WAIT, "🔄 Next in");
    } else {
        echo KUNING . "🔄 Retry in " . FAIL_WAIT . "s..." . RESET . "\n";
        timer(FAIL_WAIT, "🔄 Retry in");
    }
}
