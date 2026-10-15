#!/usr/bin/env php
<?php
/**
 * ═══════════════════════════════════════════════════════════════
 *  LIMEFAUCET Multi-Account Bot v3.4
 *  - FASE 1: LOGIN semua akun
 *  - FASE 2: SETUP COIN
 *  - FASE 3: FARMING (countdown lokal, gak spam API)
 * ═══════════════════════════════════════════════════════════════
 */

if (PHP_VERSION_ID < 80000) { fwrite(STDERR, "PHP 8.0+ required\n"); exit(1); }

const RST="\033[0m", BOLD="\033[1m", DIM="\033[2m";
const RED="\033[38;5;196m", GRN="\033[38;5;46m", YEL="\033[38;5;226m";
const CYN="\033[38;5;51m",  MAG="\033[38;5;201m", ORG="\033[38;5;208m";
const WHT="\033[38;5;15m",  GRY="\033[38;5;240m", VIO="\033[38;5;141m";

function vlen(string $s): int {
    $s = preg_replace('/\033\[[0-9;]*m/', '', $s);
    return mb_strlen($s);
}
function pad_to(string $s, int $w): string {
    return $s . str_repeat(' ', max(0, $w - vlen($s)));
}
function clear_screen(): void {
    if (PHP_OS_FAMILY === 'Windows') pclose(popen('cls', 'w'));
    else system('clear');
}
function fmt_cd(int $s): string {
    if ($s <= 0) return "READY";
    if ($s < 60) return $s."s";
    return floor($s/60)."m".($s%60)."s";
}

// ═══════════════════════════════════════════════════════════════
//  CONST
// ═══════════════════════════════════════════════════════════════
const BASE_URL      = 'https://limefaucet.com';
const API_PREFIX    = '/api/faucet';
const AUTH_PREFIX   = '/api/auth';
const WARYONO_IN    = 'https://api.waryono.my.id/in.php';
const WARYONO_RES   = 'https://api.waryono.my.id/res.php';
const POLL_INTERVAL = 3;
const POLL_TIMEOUT  = 180;
const DEBUG         = false;

const UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36';

$CONFIG_FILE = __DIR__ . '/lime_config.json';

// ═══════════════════════════════════════════════════════════════
//  CONFIG
// ═══════════════════════════════════════════════════════════════
function load_config(): array {
    global $CONFIG_FILE;
    $default = ['apikey' => '', 'accounts' => []];
    if (!file_exists($CONFIG_FILE)) return $default;
    $c = json_decode((string) file_get_contents($CONFIG_FILE), true);
    if (!is_array($c)) return $default;
    $c['apikey']   = $c['apikey']   ?? '';
    $c['accounts'] = $c['accounts'] ?? [];
    if (!is_array($c['accounts'])) $c['accounts'] = [];
    return $c;
}
function save_config(array $c): void {
    global $CONFIG_FILE;
    @file_put_contents($CONFIG_FILE, json_encode($c, JSON_PRETTY_PRINT));
}
function read_line(string $p = ""): string {
    if ($p) echo $p;
    return trim((string) fgets(STDIN));
}

// ═══════════════════════════════════════════════════════════════
//  HTTP
// ═══════════════════════════════════════════════════════════════
function base_headers(string $token = '', bool $json = true): array {
    $h = [
        'accept: */*',
        'accept-language: id-ID,id;q=0.9,en;q=0.8',
        'origin: ' . BASE_URL,
        'referer: ' . BASE_URL . '/dashboard',
        'sec-ch-ua: "Chromium";v="127", "Not)A;Brand";v="99"',
        'sec-ch-ua-mobile: ?1',
        'sec-ch-ua-platform: "Android"',
        'sec-fetch-site: same-origin',
        'sec-fetch-mode: cors',
        'sec-fetch-dest: empty',
        'user-agent: ' . UA,
        'accept-encoding: identity',
    ];
    if ($json) $h[] = 'content-type: application/json';
    if ($token) $h[] = 'cookie: lf_token=' . $token;
    return $h;
}

function http_req(string $method, string $url, ?string $body, array $headers, int $timeout = 30, string $proxy = ''): array {
    $ch = curl_init($url);
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_TIMEOUT        => $timeout,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CUSTOMREQUEST  => strtoupper($method),
        CURLOPT_HEADER         => true,
        CURLOPT_ENCODING       => 'identity',
    ];
    if ($proxy) {
        $opts[CURLOPT_PROXY] = $proxy;
        if (stripos($proxy, 'socks5://') === 0) $opts[CURLOPT_PROXYTYPE] = CURLPROXY_SOCKS5;
        elseif (stripos($proxy, 'socks4://') === 0) $opts[CURLOPT_PROXYTYPE] = CURLPROXY_SOCKS4;
        else $opts[CURLOPT_PROXYTYPE] = CURLPROXY_HTTP;
    }
    curl_setopt_array($ch, $opts);
    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        curl_setopt($ch, CURLOPT_POST, true);
    }
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $hdr_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $err = curl_error($ch);
    $headers_raw = substr((string) $resp, 0, $hdr_size);
    $body_raw    = substr((string) $resp, $hdr_size);
    return ['body' => $body_raw, 'headers' => $headers_raw, 'code' => $code, 'error' => $err];
}

function full_url(string $path): string {
    if (str_starts_with($path, '/api/')) return BASE_URL . $path;
    return BASE_URL . API_PREFIX . '/' . ltrim($path, '/');
}

function api_get(string $path, string $token, string $proxy = ''): array {
    $url = full_url($path);
    $r = http_req('GET', $url, null, base_headers($token, false), 30, $proxy);
    if ($r['error']) return ['_error' => $r['error']];
    $j = json_decode($r['body'], true);
    if (!is_array($j)) return ['_raw' => $r['body'], '_code' => $r['code']];
    return $j;
}

function api_post(string $path, array $payload, string $token, bool $empty_body = false, string $proxy = ''): array {
    $url = full_url($path);
    $body = $empty_body ? '' : json_encode($payload);
    $r = http_req('POST', $url, $body, base_headers($token, !$empty_body), 30, $proxy);
    if ($r['error']) return ['_error' => $r['error']];
    $j = json_decode($r['body'], true);
    if (!is_array($j)) return ['_raw' => $r['body'], '_code' => $r['code']];
    return $j;
}

// ═══════════════════════════════════════════════════════════════
//  API — Login, Config, Change Currency
// ═══════════════════════════════════════════════════════════════
function login_with_email(string $email, string $proxy = ''): ?string {
    $payload = json_encode(['email' => $email, 'referral_code' => null]);
    $r = http_req('POST', BASE_URL . AUTH_PREFIX . '/login', $payload, base_headers('', true), 20, $proxy);
    if ($r['error'] || $r['code'] !== 200) return null;
    if (preg_match('/Set-Cookie:\s*lf_token=([^;\r\n]+)/i', $r['headers'], $m)) {
        $t = trim($m[1]);
        if (strlen($t) > 30) return $t;
    }
    $j = json_decode($r['body'], true);
    if (is_array($j)) {
        foreach (['token', 'lf_token', 'access_token'] as $k) {
            if (!empty($j[$k]) && strlen($j[$k]) > 30) return $j[$k];
        }
    }
    return null;
}

function fetch_site_config(string $token, string $proxy = ''): ?array {
    $c = api_get('/api/config', $token, $proxy);
    if (!is_array($c) || isset($c['_error'])) return null;
    if (!isset($c['supported_currencies']) || !is_array($c['supported_currencies'])) return null;
    return $c;
}

function change_currency(string $token, string $currency, string $proxy = ''): bool {
    $currency = strtoupper($currency);
    $r = api_post('/api/auth/change-currency', ['currency' => $currency], $token, false, $proxy);
    return (($r['success'] ?? false) === true);
}

// ═══════════════════════════════════════════════════════════════
//  WARYONO LIME SOLVER
// ═══════════════════════════════════════════════════════════════
function waryono_solve_lime(string $apikey, string $base64, float $x, float $y, float $radius, string $proxy = ''): array {
    $payload = [
        'apikey'  => $apikey,
        'methods' => 'lime',
        'base64'  => $base64,
        'x'       => $x,
        'y'       => $y,
        'radius'  => $radius,
        'json'    => 1,
    ];
    $ch = curl_init(WARYONO_IN);
    $opts = [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    ];
    if ($proxy) {
        $opts[CURLOPT_PROXY] = $proxy;
        if (stripos($proxy, 'socks5://') === 0) $opts[CURLOPT_PROXYTYPE] = CURLPROXY_SOCKS5;
    }
    curl_setopt_array($ch, $opts);
    $resp = curl_exec($ch);
    $body = (string) $resp;

    if (DEBUG) @file_put_contents(__DIR__.'/debug_solver.log', date('H:i:s')." IN: ".substr($body,0,300)."\n", FILE_APPEND);

    $j = json_decode($body, true);
    if (!is_array($j)) return ['ok'=>false, 'err'=>'solver reply bukan JSON: '.substr($body,0,80)];
    if (($j['status'] ?? 0) != 1) return ['ok'=>false, 'err'=>'solver submit: '.($j['request'] ?? 'unknown')];

    $tid = $j['request'];
    $elapsed = 0;
    while ($elapsed < POLL_TIMEOUT) {
        sleep(POLL_INTERVAL);
        $elapsed += POLL_INTERVAL;
        $url = WARYONO_RES . '?apikey=' . urlencode($apikey) . '&action=get&id=' . urlencode((string) $tid) . '&json=1';
        $ctx = stream_context_create(['http' => ['timeout' => 15]]);
        $pr = @file_get_contents($url, false, $ctx);
        $pj = json_decode((string) $pr, true);
        if (DEBUG) @file_put_contents(__DIR__.'/debug_solver.log', date('H:i:s')." RES: ".substr((string)$pr,0,200)."\n", FILE_APPEND);
        if (!is_array($pj)) continue;
        if (($pj['status'] ?? 0) == 1) {
            $ans = (string) $pj['request'];
            if (preg_match('/answer:\s*(-?\d+)/i', $ans, $m)) return ['ok'=>true, 'angle'=>(int)$m[1]];
            return ['ok'=>false, 'err'=>'format jawaban: '.substr($ans,0,60)];
        }
        $req = (string) ($pj['request'] ?? '');
        if (stripos($req, 'CAPCHA_NOT_READY') !== false) continue;
        if (stripos($req, 'ERROR') !== false) return ['ok'=>false, 'err'=>'solver: '.$req];
    }
    return ['ok'=>false, 'err'=>'solver timeout '.POLL_TIMEOUT.'s'];
}

// ═══════════════════════════════════════════════════════════════
//  ROTATION CAPTCHA
// ═══════════════════════════════════════════════════════════════
function solve_rotation_captcha(string $token, string $apikey, string $proxy = ''): array {
    $ch = api_post('rotation-captcha/challenge', [], $token, true, $proxy);
    if (!isset($ch['session_id']) || !isset($ch['challenge'])) {
        $preview = substr(json_encode($ch), 0, 100);
        return ['ok'=>false, 'err'=>'challenge gagal: '.$preview];
    }
    $session_id = $ch['session_id'];
    $challenge  = $ch['challenge'];
    $img_path   = $challenge['image'] ?? '';
    $crop       = $challenge['crop'] ?? [];
    $cx = (float) ($crop['x'] ?? 0);
    $cy = (float) ($crop['y'] ?? 0);
    $cr = (float) ($crop['radius'] ?? 0);
    if (!$img_path) return ['ok'=>false, 'err'=>'no image path'];

    $img_url = str_starts_with($img_path, 'http') ? $img_path : BASE_URL . $img_path;
    $img_h = base_headers($token, false);
    $img_h[] = 'accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8';
    $img_h[] = 'sec-fetch-dest: image';
    $img_h[] = 'sec-fetch-mode: no-cors';

    $ch2 = curl_init($img_url);
    $opts2 = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER     => $img_h,
    ];
    if ($proxy) {
        $opts2[CURLOPT_PROXY] = $proxy;
        if (stripos($proxy, 'socks5://') === 0) $opts2[CURLOPT_PROXYTYPE] = CURLPROXY_SOCKS5;
    }
    curl_setopt_array($ch2, $opts2);
    $img_bytes = curl_exec($ch2);
    if (empty($img_bytes)) return ['ok'=>false, 'err'=>'download image gagal'];

    $img_b64 = base64_encode($img_bytes);
    $solv = waryono_solve_lime($apikey, $img_b64, $cx, $cy, $cr, $proxy);
    if (!$solv['ok']) return ['ok'=>false, 'err'=>$solv['err']];

    $angle = $solv['angle'];
    $verify = api_post('rotation-captcha/verify', [
        'session_id' => $session_id,
        'angle'      => $angle,
    ], $token, false, $proxy);

    if (!($verify['ok'] ?? false) || empty($verify['token'])) {
        $preview = substr(json_encode($verify), 0, 80);
        return ['ok'=>false, 'err'=>'verify rejected (angle='.$angle.'°) '.$preview];
    }
    return ['ok'=>true, 'token'=>$verify['token'], 'angle'=>$angle];
}

// ═══════════════════════════════════════════════════════════════
//  RENDER
// ═══════════════════════════════════════════════════════════════
function render_menu(array $cfg): void {
    clear_screen();
    $n_acc = count($cfg['accounts']);
    $api_ok = !empty($cfg['apikey']);
    $logged = 0;
    foreach ($cfg['accounts'] as $a) if (!empty($a['token'])) $logged++;

    echo "\n";
    echo CYN . "╔══════════════════════════════════════════════════════════════╗" . RST . "\n";
    echo CYN . "║" . RST . " " . BOLD . WHT . "LIMEFAUCET MULTI-ACCOUNT BOT  v3.4" . RST . str_repeat(' ', 29) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";
    echo CYN . "║" . RST . " " . VIO . "STATUS" . RST . str_repeat(' ', 54) . CYN . "║" . RST . "\n";
    $api_str = $api_ok ? GRN . "SET" . RST : RED . "NOT SET" . RST;
    echo CYN . "║" . RST . "  ├─ Solver : " . pad_to($api_str, 47) . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "  ├─ Akun   : " . pad_to(YEL . $n_acc . " akun" . RST, 47) . CYN . "║" . RST . "\n";
    $lc = $logged > 0 ? GRN : GRY;
    echo CYN . "║" . RST . "  └─ Login  : " . pad_to($lc . $logged . "/" . $n_acc . RST, 47) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";
    echo CYN . "║" . RST . " " . BOLD . "MENU" . RST . str_repeat(' ', 56) . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[1]" . RST . " Start Farming (login + claim)                      " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[2]" . RST . " Config Solver (API key)                            " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[3]" . RST . " Tambah Akun                                        " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[4]" . RST . " Delete Akun                                        " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[5]" . RST . " List Akun                                          " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[6]" . RST . " Reset Token (force re-login)                       " . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "   " . GRN . "[0]" . RST . " Exit                                               " . CYN . "║" . RST . "\n";
    echo CYN . "╚══════════════════════════════════════════════════════════════╝" . RST . "\n\n";
    echo "   " . DIM . "By Power @SouuXso · Multi-Account Edition" . RST . "\n\n";
}

function render_login_phase(array $accounts, array $accState, array $logs, int $curIdx = -1): void {
    clear_screen();
    echo "\n";
    echo CYN . "╔══════════════════════════════════════════════════════════════╗" . RST . "\n";
    echo CYN . "║" . RST . " " . BOLD . WHT . "PHASE 1 — LOGIN SEMUA AKUN" . RST . str_repeat(' ', 30) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";

    $i = 0;
    foreach ($accounts as $idx => $acc) {
        $i++;
        $st = $accState[$idx] ?? ['state' => 'wait'];
        $mark = ($idx === $curIdx) ? CYN . "►" . RST : " ";
        $state_str = 'WAIT'; $col = GRY;
        switch ($st['state']) {
            case 'logging': $state_str = 'LOGIN'; $col = CYN; break;
            case 'ok':      $state_str = 'OK';    $col = GRN; break;
            case 'fail':    $state_str = 'FAIL';  $col = RED; break;
        }
        $email = substr($acc['email'], 0, 28);
        $px = !empty($acc['proxy']) ? GRY . "[px]" . RST : "";
        $row = " " . $mark . " " . $col . str_pad($state_str, 6) . RST . " " . WHT . str_pad($email, 29) . RST . " " . $px;
        $vis = vlen($row);
        echo CYN . "║" . RST . $row . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
    }
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";

    $last = array_slice($logs, -7);
    if (empty($last)) {
        echo CYN . "║" . RST . " " . DIM . "(menunggu...)" . RST . str_repeat(' ', 48) . CYN . "║" . RST . "\n";
    } else {
        foreach ($last as $l) {
            $txt = " " . $l;
            $vis = vlen($txt);
            echo CYN . "║" . RST . $txt . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
        }
    }
    echo CYN . "╚══════════════════════════════════════════════════════════════╝" . RST . "\n\n";
}

function render_farm(array $accounts, array $status, array $logs, int $round, int $curIdx = -1): void {
    clear_screen();
    $total_claims  = 0; $total_rewards = 0.0; $total_fails = 0;
    foreach ($status as $s) {
        $total_claims  += (int)($s['claims'] ?? 0);
        $total_rewards += (float)($s['rewards'] ?? 0);
        $total_fails   += (int)($s['fails'] ?? 0);
    }

    echo "\n";
    echo CYN . "╔══════════════════════════════════════════════════════════════╗" . RST . "\n";
    echo CYN . "║" . RST . " " . BOLD . WHT . "FARMING" . RST . " " . DIM . "round #" . str_pad((string)$round, -3, ' ') . RST . str_repeat(' ', 40) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";

    $i = 0;
    foreach ($accounts as $idx => $acc) {
        $i++;
        $s = $status[$idx] ?? ['state' => 'idle'];
        $mark = ($idx === $curIdx) ? CYN . "►" . RST : " ";
        $state_str = 'IDLE'; $col = GRY;

        // tampilkan countdown lokal
        if (($s['wait'] ?? 0) > 0) {
            $state_str = 'CD ' . fmt_cd((int)$s['wait']);
            $col = YEL;
        } else {
            switch ($s['state'] ?? 'idle') {
                case 'cek_token': $state_str = 'CEK';    $col = CYN; break;
                case 'info':      $state_str = 'INFO';   $col = CYN; break;
                case 'solving':   $state_str = 'SOLVE';  $col = MAG; break;
                case 'claiming':  $state_str = 'CLAIM';  $col = MAG; break;
                case 'ok':        $state_str = 'READY';  $col = GRN; break;
                case 'error':     $state_str = 'ERR';    $col = RED; break;
                case 'idle':      $state_str = 'IDLE';   $col = GRY; break;
            }
        }

        $email = substr($acc['email'], 0, 20);
        $stat  = sprintf('%d✓ %d✗', (int)($s['claims'] ?? 0), (int)($s['fails'] ?? 0));
        $rw    = sprintf('+%.6f', (float)($s['rewards'] ?? 0));
        $curc  = $s['currency'] ?? '-';

        $row = " " . $mark . " " . $col . str_pad($state_str, 9) . RST . " " . WHT . str_pad($email, 21) . RST . " " . $stat . " " . $rw . " " . YEL . $curc . RST;
        $vis = vlen($row);
        echo CYN . "║" . RST . $row . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
    }
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";
    $tot_line = " " . GRN . "✓" . $total_claims . " claim" . RST . "  " . RED . "✗" . $total_fails . " fail" . RST . "  " . YEL . "+" . sprintf('%.8f', $total_rewards) . RST;
    $vis = vlen($tot_line);
    echo CYN . "║" . RST . $tot_line . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";

    $last = array_slice($logs, -6);
    if (empty($last)) {
        echo CYN . "║" . RST . " " . DIM . "(belum ada aktivitas)" . RST . str_repeat(' ', 42) . CYN . "║" . RST . "\n";
    } else {
        foreach ($last as $l) {
            $txt = " " . $l;
            $vis = vlen($txt);
            echo CYN . "║" . RST . $txt . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
        }
    }
    echo CYN . "╚══════════════════════════════════════════════════════════════╝" . RST . "\n";
    echo "\n   " . GRN . "FARMING" . RST . " " . DIM . "•" . RST . " " . CYN . date('H:i:s') . RST . "  " . DIM . "[Ctrl+C to stop]" . RST . "\n\n";
}

function flog(array &$logs, string $msg, string $lvl = 'INFO'): void {
    $ts = date('H:i:s');
    $tags = [
        'OK'=>GRN."● OK    ".RST, 'ERR'=>RED."● ERR   ".RST, 'WARN'=>YEL."● WARN  ".RST,
        'INFO'=>GRY."● INFO  ".RST, 'CLAIM'=>MAG."◉ CLAIM ".RST, 'SOLVE'=>CYN."◉ SOLVER".RST,
        'WAIT'=>ORG."◉ WAIT  ".RST, 'LOGIN'=>CYN."◉ LOGIN ".RST, 'COIN'=>VIO."◉ COIN  ".RST,
        'AUTH'=>GRN."● AUTH  ".RST, 'CFG'=>GRY."● CONFIG".RST, 'STEP'=>VIO."▸ STEP  ".RST,
    ];
    $tag = $tags[strtoupper($lvl)] ?? $tags['INFO'];
    $logs[] = GRY . "[" . $ts . "] " . RST . $tag . " " . WHT . $msg . RST;
    if (count($logs) > 15) array_shift($logs);
}

// ═══════════════════════════════════════════════════════════════
//  MENU ACTIONS
// ═══════════════════════════════════════════════════════════════
function menu_config_solver(array &$cfg): void {
    clear_screen();
    echo "\n" . CYN . "═══ CONFIG SOLVER ═══" . RST . "\n\n";
    $cur = $cfg['apikey'] ? substr($cfg['apikey'], 0, 20) . '...' : '(kosong)';
    echo DIM . "Current: " . $cur . RST . "\n\n";
    $key = read_line(YEL . "Waryono API key (enter = skip): " . RST);
    if ($key !== '') {
        $cfg['apikey'] = $key;
        save_config($cfg);
        echo "\n" . GRN . "✓ API key tersimpan" . RST . "\n";
    } else {
        echo "\n" . DIM . "Skip." . RST . "\n";
    }
    echo "\n" . DIM . "Enter untuk kembali..." . RST;
    fgets(STDIN);
}

function menu_add_account(array &$cfg): void {
    clear_screen();
    echo "\n" . CYN . "═══ TAMBAH AKUN ═══" . RST . "\n\n";
    echo DIM . "Masukkan email satu per satu. Enter di email kosong = selesai." . RST . "\n\n";
    $added = 0;
    while (true) {
        $email = read_line(YEL . "Email FaucetPay : " . RST);
        if ($email === '') break;
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            echo RED . "  ✗ Email gak valid.\n\n" . RST;
            continue;
        }
        $exists = false;
        foreach ($cfg['accounts'] as $a) {
            if (strcasecmp($a['email'], $email) === 0) { $exists = true; break; }
        }
        if ($exists) {
            echo YEL . "  ! Email udah ada.\n\n" . RST;
            continue;
        }
        $proxy = read_line(YEL . "Proxy (Optional) : " . RST);
        $cfg['accounts'][] = ['email' => $email, 'proxy' => $proxy, 'currency' => '', 'token' => ''];
        $added++;
        echo GRN . "  ✓ Ditambahkan (#" . $added . ")\n\n" . RST;
    }
    if ($added > 0) {
        save_config($cfg);
        echo "\n" . GRN . "✓ " . $added . " akun tersimpan. Total: " . count($cfg['accounts']) . RST . "\n";
    } else {
        echo "\n" . DIM . "Tidak ada yang ditambahkan." . RST . "\n";
    }
    echo "\n" . DIM . "Enter untuk kembali..." . RST;
    fgets(STDIN);
}

function menu_delete_account(array &$cfg): void {
    clear_screen();
    echo "\n" . CYN . "═══ DELETE AKUN ═══" . RST . "\n\n";
    if (empty($cfg['accounts'])) {
        echo YEL . "Belum ada akun.\n" . RST;
        echo "\n" . DIM . "Enter..." . RST; fgets(STDIN); return;
    }
    foreach ($cfg['accounts'] as $i => $a) {
        $px = $a['proxy'] ? GRY . "[proxy]" . RST : '';
        echo "  " . GRN . sprintf('%2d', $i + 1) . RST . ". " . WHT . $a['email'] . RST . " " . $px . "\n";
    }
    echo "\n";
    $in = read_line(YEL . "Pilih nomor (0 = batal): " . RST);
    if (!is_numeric($in)) return;
    $n = (int) $in;
    if ($n === 0) return;
    if ($n < 1 || $n > count($cfg['accounts'])) { echo RED . "Invalid.\n" . RST; sleep(1); return; }
    $email = $cfg['accounts'][$n - 1]['email'];
    array_splice($cfg['accounts'], $n - 1, 1);
    save_config($cfg);
    echo "\n" . GRN . "✓ Dihapus: " . $email . RST . "\n";
    echo "\n" . DIM . "Enter..." . RST; fgets(STDIN);
}

function menu_list_accounts(array $cfg): void {
    clear_screen();
    echo "\n" . CYN . "═══ LIST AKUN ═══" . RST . "\n\n";
    if (empty($cfg['accounts'])) {
        echo YEL . "Belum ada akun.\n" . RST;
        echo "\n" . DIM . "Enter..." . RST; fgets(STDIN); return;
    }
    foreach ($cfg['accounts'] as $i => $a) {
        $px  = $a['proxy'] ? GRY . "proxy: " . substr($a['proxy'], 0, 35) . RST : DIM . "(no proxy)" . RST;
        $cur = $a['currency'] ?: DIM . "-" . RST;
        $tok = !empty($a['token']) ? GRN . "✓" . RST : DIM . "-" . RST;
        echo "  " . GRN . sprintf('%2d', $i + 1) . RST . ". " . WHT . $a['email'] . RST . "\n";
        echo "      " . DIM . "├─" . RST . " coin   : " . YEL . $cur . RST . "\n";
        echo "      " . DIM . "├─" . RST . " proxy  : " . $px . "\n";
        echo "      " . DIM . "└─" . RST . " token  : " . $tok . "\n\n";
    }
    echo DIM . "Total: " . count($cfg['accounts']) . RST . "\n";
    echo "\n" . DIM . "Enter..." . RST; fgets(STDIN);
}

function menu_reset_token(array &$cfg): void {
    clear_screen();
    echo "\n" . CYN . "═══ RESET TOKEN ═══" . RST . "\n\n";
    foreach ($cfg['accounts'] as $i => &$a) { $a['token'] = ''; }
    unset($a);
    save_config($cfg);
    echo GRN . "✓ Semua token di-reset.\n" . RST;
    echo "\n" . DIM . "Enter..." . RST; fgets(STDIN);
}

// ═══════════════════════════════════════════════════════════════
//  PHASE 1 — LOGIN
// ═══════════════════════════════════════════════════════════════
function phase_login(array &$cfg, array &$accState, array &$logs): int {
    $accounts = $cfg['accounts'];
    $total = count($accounts);
    $ok = 0;
    flog($logs, "PHASE 1: login $total akun dimulai...", 'LOGIN');
    render_login_phase($accounts, $accState, $logs, -1);

    foreach ($accounts as $i => $acc) {
        if (!empty($acc['token'])) {
            $accState[$i] = ['state' => 'ok'];
            $ok++;
            flog($logs, "[".substr($acc['email'],0,18)."] pakai token lama", 'OK');
            render_login_phase($accounts, $accState, $logs, $i);
            continue;
        }
        $accState[$i] = ['state' => 'logging'];
        $tag = substr($acc['email'], 0, 18);
        flog($logs, "[$tag] logging in...", 'LOGIN');
        render_login_phase($accounts, $accState, $logs, $i);

        $token = login_with_email($acc['email'], $acc['proxy'] ?? '');
        if ($token) {
            $cfg['accounts'][$i]['token'] = $token;
            $accState[$i] = ['state' => 'ok'];
            $ok++;
            flog($logs, "[$tag] login OK", 'OK');
            save_config($cfg);
        } else {
            $accState[$i] = ['state' => 'fail'];
            flog($logs, "[$tag] login FAIL", 'ERR');
        }
        render_login_phase($accounts, $accState, $logs, $i);
        sleep(1);
    }
    flog($logs, "PHASE 1 selesai: $ok/$total akun login OK", $ok === $total ? 'OK' : 'WARN');
    render_login_phase($accounts, $accState, $logs, -1);
    return $ok;
}

// ═══════════════════════════════════════════════════════════════
//  PHASE 2 — SETUP COIN
// ═══════════════════════════════════════════════════════════════
function phase_setup_coin(array &$cfg, array &$accState, array &$logs): void {
    $firstToken = null;
    foreach ($cfg['accounts'] as $a) {
        if (!empty($a['token'])) { $firstToken = $a['token']; break; }
    }
    if (!$firstToken) return;

    clear_screen();
    echo "\n";
    echo CYN . "╔══════════════════════════════════════════════════════════════╗" . RST . "\n";
    echo CYN . "║" . RST . " " . BOLD . WHT . "PHASE 2 — SETUP COIN" . RST . str_repeat(' ', 38) . CYN . "║" . RST . "\n";
    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";

    $site = fetch_site_config($firstToken);
    $currencies = [];
    if ($site && !empty($site['supported_currencies'])) {
        $currencies = $site['supported_currencies'];
        flog($logs, "Config loaded (".count($currencies)." coins)", 'CFG');
        if (!empty($site['turnstile_site_key'])) {
            flog($logs, "key: ".substr($site['turnstile_site_key'],0,20)."...", 'CFG');
        }
    } else {
        $currencies = ['DOGE','LTC','BCH','DASH','TRX','USDT','BNB','SOL','XRP','POL','ADA','TON','XLM'];
        flog($logs, "Config fetch gagal, fallback", 'WARN');
    }

    echo CYN . "╠══════════════════════════════════════════════════════════════╣" . RST . "\n";
    echo CYN . "║" . RST . " " . VIO . "SUPPORTED CURRENCIES" . RST . str_repeat(' ', 40) . CYN . "║" . RST . "\n";
    echo CYN . "║" . RST . "                                                              " . CYN . "║" . RST . "\n";

    $cols = 4; $row = []; $i = 0;
    foreach ($currencies as $cur) {
        $i++;
        $row[] = YEL . sprintf('%2d.', $i) . RST . " " . str_pad($cur, 5);
        if (count($row) >= $cols) {
            $line = "   " . implode("  ", $row);
            $vis = vlen($line);
            echo CYN . "║" . RST . $line . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
            $row = [];
        }
    }
    if (!empty($row)) {
        $line = "   " . implode("  ", $row);
        $vis = vlen($line);
        echo CYN . "║" . RST . $line . str_repeat(' ', max(0, 62 - $vis)) . CYN . "║" . RST . "\n";
    }
    echo CYN . "╚══════════════════════════════════════════════════════════════╝" . RST . "\n\n";

    $pick = read_line(YEL . "  Pilih coin (nomor/symbol, enter=LTC): " . RST);
    $chosen = 'LTC';
    if ($pick !== '') {
        if (is_numeric($pick)) {
            $idx = (int)$pick - 1;
            if (isset($currencies[$idx])) $chosen = $currencies[$idx];
        } else {
            $up = strtoupper($pick);
            if (in_array($up, $currencies, true)) $chosen = $up;
        }
    }
    echo "\n  " . GRN . "Pilihan: " . YEL . $chosen . RST . "\n\n";

    foreach ($cfg['accounts'] as $i => $acc) {
        if (empty($acc['token'])) continue;
        $tag = substr($acc['email'], 0, 18);
        if (($acc['currency'] ?: '') === $chosen) {
            flog($logs, "[$tag] coin udah $chosen", 'OK');
            continue;
        }
        flog($logs, "[$tag] set coin → $chosen", 'COIN');
        if (change_currency($acc['token'], $chosen, $acc['proxy'] ?? '')) {
            $cfg['accounts'][$i]['currency'] = $chosen;
            $accState[$i]['currency'] = $chosen;
            flog($logs, "[$tag] coin OK", 'OK');
        } else {
            flog($logs, "[$tag] coin gagal", 'WARN');
        }
        save_config($cfg);
        sleep(1);
    }
    echo "  " . GRN . "✓ Coin setup selesai" . RST . "\n";
    sleep(2);
}

// ═══════════════════════════════════════════════════════════════
//  PROCESS AKUN — cek info, solve, claim (dipanggil saat ready)
// ═══════════════════════════════════════════════════════════════
function process_account(array &$acc, string $apikey, array &$status, int $idx, array &$logs, array $accounts, int $round): void {
    $email = $acc['email'];
    $proxy = $acc['proxy'] ?? '';
    $tag = substr($email, 0, 18);
    $token = $acc['token'] ?? '';
    if (empty($token)) {
        $status[$idx]['state'] = 'error';
        return;
    }

    $redraw = function() use (&$accounts, &$status, &$logs, $round, $idx) {
        render_farm($accounts, $status, $logs, $round, $idx);
    };

    // cek token
    $status[$idx]['state'] = 'cek_token';
    $redraw();
    $me = api_get('/api/auth/me', $token, $proxy);
    if (isset($me['_code']) && $me['_code'] == 401) {
        flog($logs, "[$tag] token expired, skip", 'WARN');
        $acc['token'] = '';
        $status[$idx]['state'] = 'error';
        $status[$idx]['fails'] = (int)($status[$idx]['fails'] ?? 0) + 1;
        $redraw();
        return;
    }
    if (isset($me['user'])) {
        $status[$idx]['currency'] = $me['user']['preferred_currency'] ?? ($acc['currency'] ?: '-');
        if (empty($acc['currency'])) $acc['currency'] = $status[$idx]['currency'];
    }

    // cek info
    $status[$idx]['state'] = 'info';
    $redraw();
    $info = api_get('info', $token, $proxy);
    $cd = (int)($info['time_remaining_seconds'] ?? 0);
    if ($cd > 0) {
        $status[$idx]['state'] = 'cooldown';
        $status[$idx]['wait'] = $cd;
        flog($logs, "[$tag] cooldown " . fmt_cd($cd), 'WAIT');
        $redraw();
        return;
    }

    // solve
    $status[$idx]['state'] = 'solving';
    $captcha = null; $lastErr = '';
    for ($i = 1; $i <= 3; $i++) {
        flog($logs, "[$tag] solve #$i/3", 'SOLVE');
        $redraw();
        $res = solve_rotation_captcha($token, $apikey, $proxy);
        if ($res['ok']) { $captcha = $res; break; }
        $lastErr = $res['err'] ?? 'unknown';
        flog($logs, "[$tag] gagal: " . substr($lastErr, 0, 40), 'ERR');
        $redraw();
        if ($i < 3) sleep(2);
    }
    if (!$captcha) {
        $status[$idx]['state'] = 'error';
        $status[$idx]['fails'] = (int)($status[$idx]['fails'] ?? 0) + 1;
        flog($logs, "[$tag] solve gagal 3x", 'ERR');
        $redraw();
        return;
    }
    flog($logs, "[$tag] captcha OK (angle=".$captcha['angle']."°)", 'OK');
    $redraw();

    // claim
    $status[$idx]['state'] = 'claiming';
    flog($logs, "[$tag] kirim claim...", 'CLAIM');
    $redraw();
    $claim = api_post('claim', ['captcha_token' => $captcha['token']], $token, false, $proxy);
    if (isset($claim['_error'])) {
        flog($logs, "[$tag] net err: ".$claim['_error'], 'ERR');
        $status[$idx]['state'] = 'error';
        $status[$idx]['fails'] = (int)($status[$idx]['fails'] ?? 0) + 1;
        $redraw();
        return;
    }

    $st = $claim['payout_status'] ?? 'unknown';
    if ($st === 'success') {
        $reward = (float)($claim['reward_crypto'] ?? 0);
        $cur = $claim['currency'] ?? $acc['currency'];
        $status[$idx]['claims']   = (int)($status[$idx]['claims'] ?? 0) + 1;
        $status[$idx]['rewards']  = (float)($status[$idx]['rewards'] ?? 0) + $reward;
        $status[$idx]['currency'] = $cur;
        $acc['currency'] = $cur;
        flog($logs, "[$tag] ✓ +{$reward} {$cur}", 'OK');
        // set countdown 120s default (server biasanya kasih cooldown)
        $status[$idx]['wait'] = 120;
        $status[$idx]['state'] = 'ok';
    } elseif (!empty($claim['error'])) {
        flog($logs, "[$tag] err: ".substr($claim['error'],0,40), 'ERR');
        $status[$idx]['state'] = 'error';
        $status[$idx]['fails'] = (int)($status[$idx]['fails'] ?? 0) + 1;
        $status[$idx]['wait'] = 30; // retry dalam 30s
    } else {
        flog($logs, "[$tag] unknown: ".substr(json_encode($claim),0,40), 'WARN');
        $status[$idx]['state'] = 'error';
        $status[$idx]['fails'] = (int)($status[$idx]['fails'] ?? 0) + 1;
        $status[$idx]['wait'] = 60;
    }
    $redraw();
}

// ═══════════════════════════════════════════════════════════════
//  START FARMING — pakai countdown lokal, gak spam API
// ═══════════════════════════════════════════════════════════════
function menu_start_farming(array &$cfg): void {
    if (empty($cfg['accounts'])) {
        clear_screen();
        echo YEL . "\nBelum ada akun. Tambah dulu di menu 3.\n" . RST;
        echo "\n" . DIM . "Enter..." . RST; fgets(STDIN); return;
    }
    if (empty($cfg['apikey'])) {
        clear_screen();
        echo YEL . "\nSolver API key belum di-set. Set dulu di menu 2.\n" . RST;
        echo "\n" . DIM . "Enter..." . RST; fgets(STDIN); return;
    }

    $accState = [];
    foreach ($cfg['accounts'] as $i => $a) {
        $accState[$i] = ['state' => !empty($a['token']) ? 'ok' : 'wait'];
    }
    $logs = [];

    // PHASE 1
    phase_login($cfg, $accState, $logs);
    $okCount = 0;
    foreach ($accState as $s) if (($s['state'] ?? '') === 'ok') $okCount++;
    if ($okCount === 0) {
        echo "\n" . RED . "Semua akun gagal login." . RST . "\n";
        echo "\n" . DIM . "Enter..." . RST; fgets(STDIN); return;
    }

    // PHASE 2
    phase_setup_coin($cfg, $accState, $logs);

    // PHASE 3 — farming loop dengan countdown lokal
    $status = [];
    foreach ($cfg['accounts'] as $i => $a) {
        $status[$i] = [
            'state'    => 'idle',
            'wait'     => 0,
            'claims'   => 0,
            'rewards'  => 0.0,
            'fails'    => 0,
            'currency' => $a['currency'] ?: '-',
        ];
    }
    $logs = [];
    $round = 0;
    flog($logs, "Farming start — " . count($cfg['accounts']) . " akun", 'INFO');

    if (function_exists('pcntl_signal')) {
        pcntl_async_signals(true);
        pcntl_signal(SIGINT, function () use (&$cfg) {
            save_config($cfg);
            echo "\n\n" . YEL . "  Stopped. Config saved.\n" . RST;
            exit(0);
        });
    }

    while (true) {
        $round++;

        // process akun yang ready (wait == 0)
        $anyProcessed = false;
        foreach ($cfg['accounts'] as $i => &$acc) {
            // skip kalau masih cooldown
            if (($status[$i]['wait'] ?? 0) > 0) continue;
            // skip kalau gak ada token
            if (empty($acc['token'])) {
                $status[$i]['state'] = 'error';
                continue;
            }
            // skip akun yang gagal login
            if (($accState[$i]['state'] ?? '') !== 'ok') continue;

            $anyProcessed = true;
            render_farm($cfg['accounts'], $status, $logs, $round, $i);
            try {
                process_account($acc, $cfg['apikey'], $status, $i, $logs, $cfg['accounts'], $round);
            } catch (Throwable $e) {
                flog($logs, "exception: " . $e->getMessage(), 'ERR');
                $status[$i]['state'] = 'error';
                $status[$i]['wait'] = 60;
            }
            $cfg['accounts'][$i] = $acc;
            save_config($cfg);
        }
        unset($acc);

        // kalau gak ada yang diproses, tandai round idle
        if (!$anyProcessed) {
            // kecil kemungkinan, tapi kalau semua cooldown besar, tetap tunggu
        }

        // hitung minimum wait dari semua akun
        $minWait = PHP_INT_MAX;
        foreach ($status as $s) {
            $w = (int)($s['wait'] ?? 0);
            if ($w > 0 && $w < $minWait) $minWait = $w;
        }

        // render sekali lagi abis proses
        render_farm($cfg['accounts'], $status, $logs, $round);

        // tunggu: countdown lokal per detik, tampilan update
        if ($minWait === PHP_INT_MAX) {
            // gak ada wait sama sekali (harusnya gak terjadi karena wait selalu diset > 0 setelah claim)
            sleep(5);
        } else {
            // tunggu sampe ada akun yang ready (countdown lokal, bukan API polling)
            $secs = $minWait;
            // kalau semua cooldown besar, tunggu sampe salah satu ready
            while ($secs > 0) {
                sleep(1);
                // decrement wait semua akun
                $anyReady = false;
                foreach ($status as $idx => $s) {
                    if (($status[$idx]['wait'] ?? 0) > 0) {
                        $status[$idx]['wait']--;
                        if ($status[$idx]['wait'] <= 0) $anyReady = true;
                    }
                }
                $secs--;
                // render tiap 5 detik aja biar gak berat
                if ($secs % 5 === 0 || $anyReady) {
                    render_farm($cfg['accounts'], $status, $logs, $round);
                }
                if ($anyReady) break;
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════
//  MAIN LOOP
// ═══════════════════════════════════════════════════════════════
$cfg = load_config();

while (true) {
    render_menu($cfg);
    $in = read_line(YEL . "  Pilih: " . RST);

    if ($in === '1')      menu_start_farming($cfg);
    elseif ($in === '2')  menu_config_solver($cfg);
    elseif ($in === '3')  menu_add_account($cfg);
    elseif ($in === '4')  menu_delete_account($cfg);
    elseif ($in === '5')  menu_list_accounts($cfg);
    elseif ($in === '6')  menu_reset_token($cfg);
    elseif ($in === '0') { echo "\n" . GRN . "Bye bro.\n" . RST . "\n"; exit(0); }
}
