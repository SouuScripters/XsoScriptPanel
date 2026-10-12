#!/usr/bin/env php
<?php
/**
 * ═══════════════════════════════════════════════════════════════
 *  LIMEFAUCET.com Auto Claim Bot v2.4 (Clean UI)
 *  - Auto login via email
 *  - Rotation captcha solver via Waryono lime API
 *  - FIX: paksa identity encoding (no compression, no zstd)
 *  - FIX: safe debug preview (hex fallback)
 * ═══════════════════════════════════════════════════════════════
 */

if (PHP_VERSION_ID < 80000) { fwrite(STDERR, "PHP 8.0+ required\n"); exit(1); }

// ═══════════════════════════════════════════════════════════════
//  COLORS
// ═══════════════════════════════════════════════════════════════
const RST="\033[0m", BOLD="\033[1m", DIM="\033[2m";
const RED="\033[38;5;196m", GRN="\033[38;5;46m", YEL="\033[38;5;226m";
const CYN="\033[38;5;51m",  MAG="\033[38;5;201m", ORG="\033[38;5;208m";
const WHT="\033[38;5;15m",  GRY="\033[38;5;240m", VIO="\033[38;5;141m";

function vlen(string $s): int { return mb_strlen(preg_replace('/\033\[[0-9;]*m/','',$s)); }
function pad_to(string $s, int $w): string { return $s . str_repeat(' ', max(0, $w - vlen($s))); }

// ═══════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════
$STATE = [
    'user'          => 'Unknown',
    'email'         => '-',
    'balance_usd'   => 0.0,
    'currency'      => 'LTC',
    'claims'        => 0,
    'rewards'       => 0.0,
    'failures'      => 0,
    'max_failures'  => 5,
    'solve_attempt' => 0,
    'max_solve'     => 3,
    'runtime_start' => time(),
    'max_runtime'   => 3 * 3600,
    'logs'          => [],
    'faucet_status' => 'checking',
];

function slog(string $msg, string $level = 'INFO'): void {
    global $STATE;
    $ts = date('H:i:s');
    $tags = [
        'OK'=>GRN."● OK    ".RST, 'ERR'=>RED."● ERR   ".RST, 'WARN'=>YEL."● WARN  ".RST,
        'INFO'=>GRY."● INFO  ".RST, 'CLAIM'=>MAG."◉ CLAIM ".RST, 'SOLVE'=>CYN."◉ SOLVER".RST,
        'VERIFY'=>VIO."◉ VERIFY".RST, 'CAP'=>YEL."◉ CAPTCHA".RST, 'WAIT'=>ORG."◉ WAIT  ".RST,
        'AUTH'=>GRN."● AUTH  ".RST, 'LOGIN'=>CYN."◉ LOGIN ".RST, 'DEBUG'=>GRY."● DEBUG ".RST,
    ];
    $tag = $tags[strtoupper($level)] ?? $tags['INFO'];
    $STATE['logs'][] = GRY."[{$ts}] ".RST.$tag." ".WHT.$msg.RST;
    if (count($STATE['logs'])>7) array_shift($STATE['logs']);
}

function fmt_dur(int $s): string {
    return sprintf('%02d:%02d:%02d', floor($s/3600), floor(($s%3600)/60), $s%60);
}

// Helper: safe preview untuk body yang mungkin invalid UTF-8
function safe_preview($data, int $max = 130): string {
    if (is_array($data)) {
        $s = json_encode($data, JSON_INVALID_UTF8_SUBSTITUTE | JSON_PARTIAL_OUTPUT_ON_ERROR);
        if ($s === false) {
            $s = '[json_encode failed: ' . json_last_error_msg() . ']';
        }
    } else {
        $s = (string) $data;
    }
    // kalau ada karakter non-printable, ubah jadi hex
    $has_binary = false;
    for ($i = 0; $i < strlen($s) && $i < 32; $i++) {
        $o = ord($s[$i]);
        if ($o < 0x20 && $o !== 0x09 && $o !== 0x0A && $o !== 0x0D) { $has_binary = true; break; }
    }
    if ($has_binary) {
        $s = 'HEX: ' . bin2hex(substr($s, 0, 40));
    }
    return substr($s, 0, $max);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER
// ═══════════════════════════════════════════════════════════════
function render(): void {
    global $STATE;
    $W=62; $bd=CYN;
    $line=fn(string $c)=>$bd."║".RST.pad_to(" ".$c,$W).$bd."║".RST;
    $top=$bd."╔".str_repeat('═',$W)."╗".RST;
    $mid=$bd."╠".str_repeat('═',$W)."╣".RST;
    $bot=$bd."╚".str_repeat('═',$W)."╝".RST;

    echo "\n".$top."\n";
    echo $line(BOLD.WHT."LIMEFAUCET AUTO CLAIM".RST)."\n";
    echo $line(DIM."─────── SOUU ENGINE ───────".RST)."\n";
    echo $mid."\n";

    $hs_color=GRN; $hs_label='ONLINE';
    if ($STATE['faucet_status']==='suspect')      { $hs_color=YEL; $hs_label='SUSPECT'; }
    elseif ($STATE['faucet_status']==='dead')     { $hs_color=RED; $hs_label='DEAD'; }
    elseif ($STATE['faucet_status']==='checking') { $hs_color=GRY; $hs_label='CHECKING'; }

    echo $line(VIO."FAUCET".RST)."\n";
    echo $line("├─ Status   : ".$hs_color.$hs_label.RST)."\n";
    echo $line("└─ Currency : ".CYN.$STATE['currency'].RST)."\n";
    echo $mid."\n";

    echo $line(VIO."CAPTCHA".RST)."\n";
    echo $line("├─ Type     : ".YEL."ROTATION (angle)".RST)."\n";
    echo $line("├─ Solver   : ".CYN."waryono/lime".RST)."\n";
    echo $line("└─ Attempt  : ".($STATE['solve_attempt']>0
            ? YEL.$STATE['solve_attempt']."/".$STATE['max_solve'].RST
            : DIM."-".RST))."\n";
    echo $mid."\n";

    echo $line(VIO."ACCOUNT".RST)."\n";
    echo $line("├─ User     : ".CYN.$STATE['user'].RST)."\n";
    echo $line("├─ Email    : ".$STATE['email'])."\n";
    echo $line("└─ Balance  : ".YEL.sprintf('%.8f USD',$STATE['balance_usd']).RST)."\n";
    echo $mid."\n";

    $run=time()-$STATE['runtime_start'];
    echo $line(VIO."SYSTEM".RST)."\n";
    echo $line("├─ Claims   : ".GRN.$STATE['claims'].RST)."\n";
    echo $line("├─ Rewards  : ".GRN.sprintf('+%.8f %s',$STATE['rewards'],$STATE['currency']).RST)."\n";
    echo $line("├─ Failures : ".RED.$STATE['failures'].RST." / ".$STATE['max_failures'])."\n";
    echo $line("└─ Runtime  : ".CYN.fmt_dur($run).RST." / ".DIM.fmt_dur($STATE['max_runtime']).RST)."\n";
    echo $mid."\n";

    $logs=$STATE['logs'];
    if (empty($logs)) {
        echo $line(DIM."─ no activity yet ─".RST)."\n";
    } else {
        foreach ($logs as $l) echo $line($l)."\n";
    }
    echo $bot."\n";
    echo "\n   ".GRN."BOT RUNNING".RST." ".DIM."•".RST." ".CYN.date('H:i:s').RST."\n";
    echo "   ".DIM."By Power @SouuXso • LimeFaucet Edition".RST."\n\n";
}

function clear_render(): void {
    if (PHP_OS_FAMILY==='Windows') pclose(popen('cls','w'));
    else system('clear');
    render();
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
const DEBUG         = true;   // ← aktifkan biar keliatan raw response

const UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36';

$CONFIG_FILE = __DIR__.'/lime_config.json';

function load_config(): ?array {
    global $CONFIG_FILE;
    if (!file_exists($CONFIG_FILE)) return null;
    $c = json_decode((string) file_get_contents($CONFIG_FILE), true);
    if (!is_array($c) || empty($c['email'])) return null;
    $c['apikey'] = $c['apikey'] ?? '';
    $c['token']  = $c['token']  ?? '';
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
        'origin: '.BASE_URL,
        'referer: '.BASE_URL.'/faucet',
        'sec-ch-ua: "Chromium";v="127", "Not)A;Brand";v="99"',
        'sec-ch-ua-mobile: ?1',
        'sec-ch-ua-platform: "Android"',
        'sec-fetch-site: same-origin',
        'sec-fetch-mode: cors',
        'sec-fetch-dest: empty',
        'user-agent: '.UA,
        'accept-encoding: identity',   // ← paksa NO compression
    ];
    if ($json) $h[] = 'content-type: application/json';
    if ($token) $h[] = 'cookie: lf_token='.$token;
    return $h;
}

function http_req(string $method, string $url, ?string $body, array $headers, int $timeout = 30): array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_TIMEOUT        => $timeout,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CUSTOMREQUEST  => strtoupper($method),
        CURLOPT_HEADER         => true,
        CURLOPT_ENCODING       => 'identity',   // ← paksa no decode
    ]);
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

    return [
        'body'    => $body_raw,
        'headers' => $headers_raw,
        'code'    => $code,
        'error'   => $err,
    ];
}

function full_url(string $path): string {
    if (str_starts_with($path, '/api/')) return BASE_URL.$path;
    $path = '/' . ltrim($path, '/');
    return BASE_URL.API_PREFIX.$path;
}

function api_get(string $path, string $token): array {
    $url = full_url($path);
    $r = http_req('GET', $url, null, base_headers($token, false));
    if ($r['error']) return ['_error' => $r['error']];
    $j = json_decode($r['body'], true);
    if (!is_array($j)) {
        if (DEBUG) slog("GET {$url} [{$r['code']}] raw: ".safe_preview($r['body']), 'DEBUG');
        return ['_raw' => $r['body'], '_code' => $r['code']];
    }
    return $j;
}

function api_post(string $path, array $payload, string $token, bool $empty_body = false): array {
    $url = full_url($path);
    $body = $empty_body ? '' : json_encode($payload);
    $r = http_req('POST', $url, $body, base_headers($token, !$empty_body));
    if ($r['error']) return ['_error' => $r['error']];
    $j = json_decode($r['body'], true);
    if (!is_array($j)) {
        if (DEBUG) slog("POST {$url} [{$r['code']}] raw: ".safe_preview($r['body']), 'DEBUG');
        return ['_raw' => $r['body'], '_code' => $r['code']];
    }
    return $j;
}

// ═══════════════════════════════════════════════════════════════
//  LOGIN via EMAIL
// ═══════════════════════════════════════════════════════════════
function login_with_email(string $email): ?string {
    $payload = json_encode([
        'email'         => $email,
        'referral_code' => null,
    ]);
    $h = base_headers('', true);
    $url = BASE_URL.AUTH_PREFIX.'/login';

    $r = http_req('POST', $url, $payload, $h, 20);

    if ($r['error']) { slog("Login error: {$r['error']}", 'ERR'); return null; }
    if ($r['code'] !== 200) { slog("Login HTTP {$r['code']}", 'ERR'); return null; }

    if (preg_match('/Set-Cookie:\s*lf_token=([^;\r\n]+)/i', $r['headers'], $m)) {
        $token = trim($m[1]);
        if (strlen($token) > 30) {
            slog("Login OK, token: ".substr($token,0,20)."...", 'OK');
            return $token;
        }
    }

    $j = json_decode($r['body'], true);
    if (is_array($j)) {
        foreach (['token','lf_token','access_token'] as $k) {
            if (!empty($j[$k]) && strlen($j[$k]) > 30) {
                slog("Login OK (body token)", 'OK');
                return $j[$k];
            }
        }
    }

    slog("Login: token gak ketemu", 'ERR');
    if (DEBUG) slog("Login raw: ".safe_preview($r['body']), 'DEBUG');
    return null;
}

// ═══════════════════════════════════════════════════════════════
//  WARYONO LIME SOLVER
// ═══════════════════════════════════════════════════════════════
function waryono_solve_lime(string $apikey, string $base64, float $x, float $y, float $radius): ?int {
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
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    ]);
    $resp = curl_exec($ch);
    $j = json_decode((string) $resp, true);

    if (!is_array($j) || ($j['status'] ?? 0) != 1) {
        slog("Waryono submit error: ".substr((string)$resp,0,80), 'ERR');
        return null;
    }
    $tid = $j['request'];
    slog("Waryono task: {$tid}", 'SOLVE');

    $elapsed = 0;
    while ($elapsed < POLL_TIMEOUT) {
        sleep(POLL_INTERVAL);
        $elapsed += POLL_INTERVAL;

        $url = WARYONO_RES.'?apikey='.urlencode($apikey).'&action=get&id='.urlencode((string)$tid).'&json=1';
        $pr = @file_get_contents($url);
        $pj = json_decode((string) $pr, true);

        if (!is_array($pj)) continue;

        if (($pj['status'] ?? 0) == 1) {
            $ans = (string) $pj['request'];
            if (preg_match('/answer:\s*(-?\d+)/i', $ans, $m)) {
                $angle = (int) $m[1];
                slog("Waryono solved: {$angle}° ({$elapsed}s)", 'OK');
                return $angle;
            }
            slog("Waryono bad format: {$ans}", 'ERR');
            return null;
        }

        $req = (string)($pj['request'] ?? '');
        if (stripos($req, 'CAPCHA_NOT_READY') !== false) continue;
        if (stripos($req, 'ERROR_CAPTCHA_UNSOLVABLE') !== false) { slog("Waryono: UNSOLVABLE", 'ERR'); return null; }
        if (stripos($req, 'ERROR_ZERO_BALANCE')       !== false) { slog("Waryono: SALDO HABIS", 'ERR'); return null; }
        if (stripos($req, 'ERROR_WRONG_USER_KEY')     !== false) { slog("Waryono: API KEY SALAH", 'ERR'); return null; }
        if (stripos($req, 'ERROR')                    !== false) { slog("Waryono: {$req}", 'ERR'); return null; }
    }
    slog("Waryono timeout", 'ERR');
    return null;
}

// ═══════════════════════════════════════════════════════════════
//  ROTATION CAPTCHA FULL FLOW
// ═══════════════════════════════════════════════════════════════
function solve_rotation_captcha(string $token, string $apikey): ?array {
    // STEP 1: request challenge (empty body)
    $ch = api_post('rotation-captcha/challenge', [], $token, true);

    if (!isset($ch['session_id']) || !isset($ch['challenge'])) {
        $preview = safe_preview($ch);
        slog("Bad challenge: {$preview}", 'ERR');
        return null;
    }

    $session_id = $ch['session_id'];
    $challenge  = $ch['challenge'];
    $img_path   = $challenge['image'] ?? '';
    $crop       = $challenge['crop'] ?? [];
    $cx = (float)($crop['x'] ?? 0);
    $cy = (float)($crop['y'] ?? 0);
    $cr = (float)($crop['radius'] ?? 0);

    slog("Challenge x={$cx} y={$cy} r={$cr}", 'CAP');

    if (!$img_path) { slog("No image path", 'ERR'); return null; }

    // STEP 2: download image
    $img_url = str_starts_with($img_path, 'http') ? $img_path : BASE_URL.$img_path;
    $img_h = base_headers($token, false);
    $img_h[] = 'accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8';
    $img_h[] = 'sec-fetch-dest: image';
    $img_h[] = 'sec-fetch-mode: no-cors';

    $ch2 = curl_init($img_url);
    curl_setopt_array($ch2, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_HTTPHEADER     => $img_h,
    ]);
    $img_bytes = curl_exec($ch2);

    if (empty($img_bytes)) { slog("Failed to download image", 'ERR'); return null; }
    $sig = substr($img_bytes, 0, 4);
    if ($sig !== "RIFF" && $sig !== "\x89PNG" && substr($img_bytes,0,3) !== "\xFF\xD8\xFF") {
        slog("Image corrupt (sig: ".bin2hex($sig).")", 'ERR');
        return null;
    }
    $img_b64 = base64_encode($img_bytes);
    slog("Image OK (".strlen($img_bytes)." bytes)", 'CAP');

    // STEP 3: solve
    $angle = waryono_solve_lime($apikey, $img_b64, $cx, $cy, $cr);
    if ($angle === null) return null;

    // STEP 4: verify
    $verify = api_post('rotation-captcha/verify', [
        'session_id' => $session_id,
        'angle'      => $angle,
    ], $token);

    if (!($verify['ok'] ?? false) || empty($verify['token'])) {
        $preview = safe_preview($verify, 100);
        slog("Verify rejected (angle={$angle}°) — {$preview}", 'ERR');
        return null;
    }

    slog("Verify OK angle={$angle}°", 'OK');
    return ['token' => $verify['token'], 'angle' => $angle];
}

// ═══════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════
function setup(): array {
    echo "\n".CYN."═══ LIMEFAUCET SETUP ═══".RST."\n\n";
    echo DIM."Login pakai email aja, gak perlu lf_token manual.\n\n".RST;

    $email = '';
    while (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $email = read_line(YEL."Email: ".RST);
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            echo RED."  ✗ Email gak valid\n".RST;
        }
    }
    $apikey = read_line(YEL."Waryono API key: ".RST);
    return ['email' => $email, 'apikey' => $apikey, 'token' => ''];
}

// ═══════════════════════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════════════════════
clear_render();

$config = load_config();
if ($config) {
    echo GRN."  ✓ Config found\n".RST;
    echo DIM."    Email  : {$config['email']}\n".RST;
    echo DIM."    APIKey : ".substr($config['apikey'], 0, 12)."...\n\n".RST;
    $ans = read_line(YEL."  Use saved? (y/n): ".RST);
    if (strtolower($ans) === 'n') $config = setup();
} else {
    $config = setup();
}

slog("Logging in via email...", 'LOGIN');
clear_render();

$token = login_with_email($config['email']);
if (!$token) { slog("Login failed — exit", 'ERR'); clear_render(); exit(1); }
$config['token'] = $token;
save_config($config);

$STATE['email'] = $config['email'];
slog("Session OK", 'AUTH');

$me = api_get('/api/auth/me', $token);
if (isset($me['user'])) {
    $STATE['user']        = 'u'.$me['user']['id'];
    $STATE['balance_usd'] = (float)($me['user']['balance_usd'] ?? 0);
    $STATE['currency']    = $me['user']['preferred_currency'] ?? 'LTC';
}
clear_render();

while (true) {
    if ((time() - $STATE['runtime_start']) >= $STATE['max_runtime']) {
        slog("Max runtime reached", 'WARN'); clear_render(); break;
    }
    if ($STATE['failures'] >= $STATE['max_failures']) {
        slog("Max failures reached", 'ERR'); clear_render(); break;
    }

    // refresh token kalau expired
    $me_check = api_get('/api/auth/me', $token);
    if (isset($me_check['_code']) && $me_check['_code'] == 401) {
        slog("Token expired, re-login...", 'WARN'); clear_render();
        $token = login_with_email($config['email']);
        if (!$token) { slog("Re-login failed", 'ERR'); clear_render(); exit(1); }
        $config['token'] = $token;
        save_config($config);
    } elseif (isset($me_check['user'])) {
        $STATE['balance_usd'] = (float)($me_check['user']['balance_usd'] ?? 0);
        $STATE['currency']    = $me_check['user']['preferred_currency'] ?? 'LTC';
    }

    $info = api_get('info', $token);
    $STATE['faucet_status'] = 'ok';
    $cd_sec = (int)($info['time_remaining_seconds'] ?? 0);

    if ($cd_sec > 0) {
        slog("Cooldown {$cd_sec}s", 'WAIT'); clear_render();
        sleep(min($cd_sec, 30));
        continue;
    }

    $captcha = null;
    $STATE['solve_attempt'] = 0;

    while ($STATE['solve_attempt'] < $STATE['max_solve']) {
        $STATE['solve_attempt']++;
        slog("Solving ({$STATE['solve_attempt']}/{$STATE['max_solve']})...", 'SOLVE');
        clear_render();
        $captcha = solve_rotation_captcha($token, $config['apikey']);
        clear_render();
        if ($captcha) break;
        slog("Solve failed, retry...", 'WARN');
        clear_render();
        sleep(2);
    }

    if (!$captcha) {
        slog("All solve attempts failed", 'ERR');
        $STATE['failures']++; clear_render(); sleep(10); continue;
    }

    slog("Claiming...", 'CLAIM'); clear_render();

    $claim = api_post('claim', ['captcha_token' => $captcha['token']], $token);

    if (isset($claim['_error'])) {
        slog("Network: {$claim['_error']}", 'ERR');
        $STATE['failures']++; clear_render(); sleep(15); continue;
    }

    $status = $claim['payout_status'] ?? 'unknown';
    if ($status === 'success') {
        $reward = (float)($claim['reward_crypto'] ?? 0);
        $cur    = $claim['currency'] ?? 'LTC';
        $STATE['claims']++;
        $STATE['rewards'] += $reward;
        $STATE['currency'] = $cur;
        $STATE['failures'] = 0;
        slog("Claimed #{$claim['roll_number']} +{$reward} {$cur}", 'OK');
        clear_render();
    } elseif (!empty($claim['error'])) {
        slog("Claim error: {$claim['error']}", 'ERR');
        $STATE['failures']++; clear_render(); sleep(10); continue;
    } else {
        slog("Claim unknown: ".safe_preview($claim, 60), 'WARN');
        $STATE['failures']++; clear_render(); sleep(10); continue;
    }

    $me2 = api_get('/api/auth/me', $token);
    if (isset($me2['user'])) {
        $STATE['balance_usd'] = (float)($me2['user']['balance_usd'] ?? 0);
    }
    clear_render();

    $info2 = api_get('info', $token);
    $cd2 = (int)($info2['time_remaining_seconds'] ?? 120);
    if ($cd2 > 0) {
        slog("Next in {$cd2}s", 'WAIT'); clear_render();
        sleep($cd2);
    }
}

clear_render();
echo "\n".CYN."  ◉ Bot stopped.\n".RST;
echo DIM."  Claims: {$STATE['claims']}  |  Failures: {$STATE['failures']}  |  Rewards: ".sprintf('%.8f',$STATE['rewards'])." {$STATE['currency']}\n\n".RST;
