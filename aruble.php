<?php // index.php
/**
 * ═══════════════════════════════════════════════════════════════
 *  SOUUENGINE — ARUBLE.NET AUTO CLAIM
 *  Live Dashboard • Menu-driven • Config JSON
 *  Flow: Login → Challenge → Daily → Faucet → Loop
 * ═══════════════════════════════════════════════════════════════
 */

@system("clear");
error_reporting(0);
set_time_limit(0);

define("SOOU_VERSION", "v2.5");
define("SOOU_AUTHOR",  "MoneyMaker_w");
define("SOOU_TAGLINE", "No AdGate • No Shortlink • Direct Claim");
define("CONFIG_FILE",  __DIR__ . "/souu_config.json");
define("COOKIE_FILE",  __DIR__ . "/aruble.txt");
define("MAX_LOGS",     8);
define("CYCLE_WAIT",   15);

date_default_timezone_set('Asia/Kolkata');

// ═══════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════
$DASH = [
    'stage'        => 'IDLE',
    'status'       => 'INIT',
    'user'         => '-',
    'balance'      => '-',
    'claims'       => 0,
    'total_reward' => 0,
    'last_reward'  => '0',
    'currency'     => 'COINS',
    'fails'        => 0,
    'logs'         => [],
    'start_time'   => time(),
    'solve_type'   => '-',
    'next_in'      => 0,
];

// ═══════════════════════════════════════════════════════════════
//  UTIL
// ═══════════════════════════════════════════════════════════════
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

function box_top() { return "\033[38;5;51m╔" . str_repeat("═", 62) . "╗\033[0m\n"; }
function box_div() { return "\033[38;5;51m╠" . str_repeat("═", 62) . "╣\033[0m\n"; }
function box_bot() { return "\033[38;5;51m╚" . str_repeat("═", 62) . "╝\033[0m\n"; }

function box_line($content, $width = 62) {
    $pad = $width - ansi_len($content) - 2;
    if ($pad < 0) $pad = 0;
    return "\033[38;5;51m║\033[0m " . $content . str_repeat(" ", $pad) . " \033[38;5;51m║\033[0m\n";
}

function gradient($text, $start = 51, $end = 213) {
    $chars = preg_split('//u', $text, -1, PREG_SPLIT_NO_EMPTY);
    $len = count($chars);
    if ($len <= 1) return "\033[38;5;{$start}m{$text}\033[0m";
    $out = '';
    foreach ($chars as $i => $ch) {
        $t = $i / ($len - 1);
        $c = (int) round($start + ($end - $start) * $t);
        $out .= "\033[38;5;{$c}m{$ch}";
    }
    return $out . "\033[0m";
}

function fmt_dur($s) {
    $s = (int)$s;
    return sprintf("%02d:%02d:%02d", $s/3600, ($s%3600)/60, $s%60);
}

function short_str($s, $max = 30) {
    if (mb_strlen($s) > $max) return mb_substr($s, 0, $max - 14) . "..." . mb_substr($s, -10);
    return $s;
}

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD
// ═══════════════════════════════════════════════════════════════
function dash_push($icon, $label, $msg, $color = "\033[1;37m") {
    global $DASH;
    $t = date('H:i:s');
    $line = "\033[1;90m[{$t}]\033[0m \033[1;35m{$icon}\033[0m \033[1;36m{$label}\033[0m {$color}{$msg}\033[0m";
    $DASH['logs'][] = $line;
    if (count($DASH['logs']) > MAX_LOGS) array_shift($DASH['logs']);
}

function dash_render() {
    global $DASH;
    clr();

    $elapsed = time() - $DASH['start_time'];
    $st = strtoupper($DASH['status']);
    $sc = "\033[1;33m";
    if (strpos($st, 'OK') !== false || strpos($st, 'SUCCESS') !== false || strpos($st, 'FINISH') !== false) $sc = "\033[1;32m";
    elseif (strpos($st, 'FAIL') !== false || strpos($st, 'ERROR') !== false || strpos($st, 'EXPIRED') !== false) $sc = "\033[1;31m";
    elseif (strpos($st, 'WAIT') !== false || strpos($st, 'COOLD') !== false || strpos($st, 'SKIP') !== false) $sc = "\033[38;5;208m";

    $out  = box_top();
    $out .= box_line(gradient("SOUUENGINE :: ARUBLE AUTO CLAIM"));
    $out .= box_line("\033[2m────── By " . SOOU_AUTHOR . " • " . SOOU_VERSION . " ──────\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mSESSION\033[0m");
    $out .= box_line("\033[38;5;51m├─ User    : \033[0m\033[1;36m" . $DASH['user'] . "\033[0m");
    $out .= box_line("\033[38;5;51m├─ Stage   : \033[0m\033[1;35m" . strtoupper($DASH['stage']) . "\033[0m");
    $out .= box_line("\033[38;5;51m├─ Status  : \033[0m{$sc}" . $DASH['status'] . "\033[0m");
    if ($DASH['next_in'] > 0) {
        $m = floor($DASH['next_in'] / 60); $s = $DASH['next_in'] % 60;
        $out .= box_line("\033[38;5;51m└─ Next    : \033[0m\033[1;33m" . sprintf("%02d:%02d", $m, $s) . "\033[0m");
    } else {
        $out .= box_line("\033[38;5;51m└─ Next    : \033[0m\033[2m-\033[0m");
    }
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mINCOME\033[0m");
    $out .= box_line("\033[38;5;51m├─ Claims  : \033[0m\033[1;32m" . $DASH['claims'] . "\033[0m");
    $out .= box_line("\033[38;5;51m├─ Total   : \033[0m\033[1;32m+" . number_format($DASH['total_reward'], 2) . " " . $DASH['currency'] . "\033[0m");
    $out .= box_line("\033[38;5;51m├─ Last    : \033[0m\033[1;32m+" . $DASH['last_reward'] . " " . $DASH['currency'] . "\033[0m");
    $out .= box_line("\033[38;5;51m└─ Balance : \033[0m\033[1;36m" . $DASH['balance'] . "\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mSYSTEM\033[0m");
    $out .= box_line("\033[38;5;51m├─ Fails   : \033[0m\033[1;31m" . $DASH['fails'] . "\033[0m");
    $out .= box_line("\033[38;5;51m├─ Solve   : \033[0m\033[1;36m" . $DASH['solve_type'] . "\033[0m");
    $out .= box_line("\033[38;5;51m└─ Runtime : \033[0m\033[1;33m" . fmt_dur($elapsed) . "\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mLIVE LOG\033[0m");
    for ($i = 0; $i < MAX_LOGS; $i++) {
        if (isset($DASH['logs'][$i])) $out .= box_line($DASH['logs'][$i]);
        else $out .= "\033[38;5;51m║\033[0m" . str_repeat(" ", 62) . "\033[38;5;51m║\033[0m\n";
    }
    $out .= box_bot();
    $out .= "\n   " . gradient("SOUUENGINE RUNNING", 46, 226) . " \033[1;90m•\033[0m \033[1;36m" . date('H:i:s') . "\033[0m\n";
    $out .= "   \033[1;90mPowered by \033[0m\033[1;35m" . SOOU_AUTHOR . "\033[0m\033[1;90m • \033[0m\033[1;36mSouuEngine " . SOOU_VERSION . "\033[0m\n";
    $out .= "   \033[1;90m" . SOOU_TAGLINE . "\033[0m\n\n";

    echo $out;
    flush();
}

function dash_log($icon, $label, $msg, $color = "\033[1;37m") {
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
        $m = floor($left / 60); $s = $left % 60;
        $DASH['next_in'] = $left;
        $DASH['status'] = sprintf("%s %02d:%02d", $label, $m, $s);
        dash_render();
        sleep(1);
    }
    $DASH['next_in'] = 0;
    dash_render();
}

// ═══════════════════════════════════════════════════════════════
//  CONFIG
// ═══════════════════════════════════════════════════════════════
function config_load() {
    if (!file_exists(CONFIG_FILE)) return [];
    $raw = @file_get_contents(CONFIG_FILE);
    if (!$raw) return [];
    $j = json_decode($raw, true);
    return is_array($j) ? $j : [];
}

function config_save($d) {
    @file_put_contents(CONFIG_FILE, json_encode($d, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
}

function config_ready($cfg) {
    return !empty($cfg['email']) && !empty($cfg['password']) && !empty($cfg['user_agent']);
}

// ═══════════════════════════════════════════════════════════════
//  MENU
// ═══════════════════════════════════════════════════════════════
function show_main_menu($cfg) {
    clr();

    $email = $cfg['email'] ?? '-';
    $pass  = $cfg['password'] ?? '';
    $ua    = $cfg['user_agent'] ?? '';

    $email_s = short_str($email, 30);
    $pass_s  = $pass ? str_repeat('*', min(12, mb_strlen($pass))) . ' (' . mb_strlen($pass) . ' char)' : 'belum diisi';
    $ua_s    = $ua ? short_str($ua, 30) : 'belum diisi';

    $ready = config_ready($cfg);
    $status = $ready ? "\033[1;32m[OK] READY\033[0m" : "\033[1;31m[!] BELUM LENGKAP\033[0m";

    $out  = box_top();
    $out .= box_line(gradient("SOUUENGINE :: ARUBLE AUTO CLAIM"));
    $out .= box_line("\033[2m────── By " . SOOU_AUTHOR . " • " . SOOU_VERSION . " ──────\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mCONFIG STATUS\033[0m");
    $out .= box_line("\033[38;5;51m├─ Status    : \033[0m" . $status);
    $out .= box_line("\033[38;5;51m├─ Email     : \033[0m\033[1;36m{$email_s}\033[0m");
    $out .= box_line("\033[38;5;51m├─ Password  : \033[0m\033[1;36m{$pass_s}\033[0m");
    $out .= box_line("\033[38;5;51m└─ UserAgent : \033[0m\033[1;36m{$ua_s}\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mINFO\033[0m");
    $out .= box_line("\033[38;5;51m├─ Target    : \033[0m\033[1;33maruble.net\033[0m");
    $out .= box_line("\033[38;5;51m├─ Engine    : \033[0m\033[1;32mSouuEngine " . SOOU_VERSION . "\033[0m");
    $out .= box_line("\033[38;5;51m└─ Flow      : \033[0m\033[1;32mChallenge → Daily → Faucet\033[0m");
    $out .= box_div();

    $out .= box_line("\033[38;5;213m\033[1mMENU\033[0m");
    $out .= box_line("  \033[38;5;51m1.\033[0m \033[1;37mStart Farming\033[0m");
    $out .= box_line("  \033[38;5;51m2.\033[0m \033[1;37mConfig Email\033[0m");
    $out .= box_line("  \033[38;5;51m3.\033[0m \033[1;37mConfig Password\033[0m");
    $out .= box_line("  \033[38;5;51m4.\033[0m \033[1;37mConfig User-Agent\033[0m");
    $out .= box_line("  \033[38;5;208m0.\033[0m \033[1;37mExit\033[0m");
    $out .= box_bot();

    $out .= "\n   " . gradient("SOUUENGINE", 46, 226) . " \033[1;90m•\033[0m \033[1;36m" . date('H:i:s') . "\033[0m\n";
    $out .= "   \033[1;90mPowered by \033[0m\033[1;35m" . SOOU_AUTHOR . "\033[0m\033[1;90m • \033[0m\033[1;36mSouuEngine " . SOOU_VERSION . "\033[0m\n";
    $out .= "   \033[1;90m" . SOOU_TAGLINE . "\033[0m\n\n";

    echo $out;
}

function prompt_main() {
    echo "\033[1;35mSouuEngine\033[0m \033[1;36m»\033[0m \033[1;33mPilih\033[0m \033[1;37m[\033[1;36m1/2/3/4/0\033[1;37m]\033[0m \033[1;35m>\033[0m ";
    return trim(fgets(STDIN));
}

function prompt_input($label) {
    echo "\n \033[1;35mSouuEngine\033[0m \033[1;36m»\033[0m \033[1;33m{$label}\033[0m \033[1;35m>\033[0m ";
    return trim(fgets(STDIN));
}

function prompt_enter($msg = "ENTER untuk lanjut...") {
    echo "\n \033[1;90m{$msg}\033[0m";
    fgets(STDIN);
}

// ═══════════════════════════════════════════════════════════════
//  CONFIG HANDLERS
// ═══════════════════════════════════════════════════════════════
function config_email($cfg) {
    clr();
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: CONFIG EMAIL"));
    echo box_line("\033[2m────── By " . SOOU_AUTHOR . " • " . SOOU_VERSION . " ──────\033[0m");
    echo box_div();
    echo box_line("\033[38;5;213m\033[1mCURRENT\033[0m");
    echo box_line("\033[38;5;51m└─ Email : \033[0m\033[1;36m" . ($cfg['email'] ?? '-') . "\033[0m");
    echo box_bot();
    $email = prompt_input("New Email");
    if ($email) {
        $cfg['email'] = $email;
        config_save($cfg);
        echo "\n \033[1;32m[OK]\033[0m \033[1;37mEmail disimpan\033[0m\n";
    } else {
        echo "\n \033[1;33m[!]\033[0m \033[1;37mKosong, ga disave\033[0m\n";
    }
    sleep(1);
}

function config_password($cfg) {
    clr();
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: CONFIG PASSWORD"));
    echo box_line("\033[2m────── By " . SOOU_AUTHOR . " • " . SOOU_VERSION . " ──────\033[0m");
    echo box_div();
    echo box_line("\033[38;5;213m\033[1mCURRENT\033[0m");
    $pass = $cfg['password'] ?? '';
    $pass_disp = $pass ? str_repeat('*', min(12, strlen($pass))) . " (" . strlen($pass) . " char)" : "belum diisi";
    echo box_line("\033[38;5;51m└─ Password : \033[0m\033[1;36m{$pass_disp}\033[0m");
    echo box_bot();
    $p = prompt_input("New Password");
    if ($p) {
        $cfg['password'] = $p;
        config_save($cfg);
        echo "\n \033[1;32m[OK]\033[0m \033[1;37mPassword disimpan\033[0m\n";
    } else {
        echo "\n \033[1;33m[!]\033[0m \033[1;37mKosong, ga disave\033[0m\n";
    }
    sleep(1);
}

function config_useragent($cfg) {
    clr();
    echo box_top();
    echo box_line(gradient("SOUUENGINE :: CONFIG USER-AGENT"));
    echo box_line("\033[2m────── By " . SOOU_AUTHOR . " • " . SOOU_VERSION . " ──────\033[0m");
    echo box_div();
    echo box_line("\033[38;5;213m\033[1mCURRENT\033[0m");
    $ua = $cfg['user_agent'] ?? '';
    $ua_disp = $ua ? short_str($ua, 40) : 'belum diisi';
    echo box_line("\033[38;5;51m└─ UA : \033[0m\033[1;36m{$ua_disp}\033[0m");
    echo box_div();
    echo box_line("\033[1;33m[i] Paste user-agent dari DevTools lo\033[0m");
    echo box_bot();
    $u = prompt_input("New User-Agent");
    if ($u) {
        $cfg['user_agent'] = $u;
        config_save($cfg);
        echo "\n \033[1;32m[OK]\033[0m \033[1;37mUser-Agent disimpan\033[0m\n";
    } else {
        echo "\n \033[1;33m[!]\033[0m \033[1;37mKosong, ga disave\033[0m\n";
    }
    sleep(1);
}

// ═══════════════════════════════════════════════════════════════
//  BOT CHECK SIGNAL
// ═══════════════════════════════════════════════════════════════
function botCheckSignal($path, $api) {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => 'https://aruble.net/bot-check/signal',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => 'POST',
        CURLOPT_POSTFIELDS     => [
            'mouse'         => rand(8, 25),
            'keyboard'      => rand(0, 4),
            'scroll'        => rand(3, 12),
            'touch'         => rand(2, 8),
            'elapsed'       => rand(20000, 80000),
            'mouse_linear'  => rand(0, 3),
            'direct_clicks' => rand(1, 3),
            'integrity'     => '',
            'path'          => $path,
        ],
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: ' . $api,
            'sec-ch-ua-full-version: "149.0.7827.197"',
        ],
    ]);
    $response = curl_exec($curl);
    curl_close($curl);
    return $response;
}

// ═══════════════════════════════════════════════════════════════
//  CAPTCHA SOLVER
// ═══════════════════════════════════════════════════════════════
function souuSolve($csrf, $api = null, $path = '/faucet') {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => 'https://aruble.net/bot-check/signal',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST  => 'POST',
        CURLOPT_POSTFIELDS     => [
            'mouse'         => rand(8, 25),
            'keyboard'      => rand(0, 4),
            'scroll'        => rand(3, 12),
            'touch'         => rand(2, 8),
            'elapsed'       => rand(20000, 80000),
            'mouse_linear'  => rand(0, 3),
            'direct_clicks' => rand(1, 3),
            'integrity'     => '',
            'path'          => $path,
        ],
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: ' . $api,
            'sec-ch-ua-full-version: "149.0.7827.197"',
        ],
    ]);
    $res = curl_exec($curl);
    if ($res === false || curl_errno($curl)) { curl_close($curl); return null; }
    curl_close($curl);

    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => 'https://aruble.net/captcha/challenge',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'User-Agent: '.$api,
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8',
        ],
    ]);
    $res = curl_exec($curl);
    if ($res === false || curl_errno($curl)) { curl_close($curl); return null; }
    curl_close($curl);

    $data = json_decode($res, true);
    if (isset($data['banned']) && $data['banned'] === true && isset($data['remaining_seconds'])) {
        dash_log("[!]", "BAN   ", "remaining {$data['remaining_seconds']}s", "\033[1;31m");
        dash_timer((int)$data['remaining_seconds'], "Banned");
        return null;
    }
    if (!$data) return null;

    if (!empty($data['gate_required'])) {
        usleep(($data['hold_ms'] ?? 1000) * 1000);

        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_URL            => 'https://aruble.net/captcha/gate/start',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_ENCODING       => '',
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => "_csrf_token=$csrf",
            CURLOPT_COOKIEJAR      => COOKIE_FILE,
            CURLOPT_COOKIEFILE     => COOKIE_FILE,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_TIMEOUT        => 20,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_HTTPHEADER     => [
                'User-Agent: '.$api,
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8',
            ],
        ]);
        $response = curl_exec($curl);
        if ($response === false || curl_errno($curl)) { curl_close($curl); return null; }
        curl_close($curl);

        $gate = json_decode($response, true);
        if (stripos($res, '<title>Redirecting...') !== false || stripos($res, 'Please login') !== false) return null;
        if (empty($gate['success'])) return null;

        usleep($gate['hold_ms'] * 1000);

        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_URL            => 'https://aruble.net/captcha/gate/complete',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_ENCODING       => '',
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => http_build_query([
                'gate_key'    => $gate['gate_key'],
                'moves'       => rand(40, 60),
                '_csrf_token' => $csrf,
            ]),
            CURLOPT_COOKIEJAR      => COOKIE_FILE,
            CURLOPT_COOKIEFILE     => COOKIE_FILE,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_TIMEOUT        => 20,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_HTTPHEADER     => [
                'User-Agent: '.$api,
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8',
            ],
        ]);
        $response = curl_exec($curl);
        if ($response === false || curl_errno($curl)) { curl_close($curl); return null; }
        curl_close($curl);

        $complete = json_decode($response, true);
        if (empty($complete['success'])) return null;

        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_URL            => 'https://aruble.net/captcha/challenge',
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_COOKIEJAR      => COOKIE_FILE,
            CURLOPT_COOKIEFILE     => COOKIE_FILE,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => false,
            CURLOPT_TIMEOUT        => 20,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_HTTPHEADER     => [
                'User-Agent: '.$api,
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8',
            ],
        ]);
        $res = curl_exec($curl);
        if ($res === false || curl_errno($curl)) { curl_close($curl); return null; }
        curl_close($curl);

        $data = json_decode($res, true);
        if (!$data) return null;
    }

    $key  = $data['key']  ?? null;
    $type = $data['type'] ?? null;
    if (!$key || !$type) return null;

    $answer = "";
    $solve_time = 0;

    if ($type == "least_repeat") {
        $icons = [];
        foreach ($data['grid'] as $item) { $icons[$item['icon']][] = $item['id']; }
        asort($icons);
        $answer     = $icons[array_key_first($icons)][0];
        $solve_time = rand(20000, 50000);
    } elseif ($type == "slide") {
        $target     = $data['target_pct'];
        $answer     = $target + rand(2, 5);
        $solve_time = rand(4000, 8000);
    } elseif ($type == "icon_order") {
        $map = [];
        foreach ($data['display'] as $item) { $map[$item['icon']] = $item['id']; }
        $arr = [];
        foreach ($data['prompt'] as $icon) { $arr[] = $map[$icon] ?? null; }
        $answer     = json_encode($arr);
        $solve_time = rand(20000, 40000);
    } elseif ($type == "drag_dot") {
        $answer = json_encode(["x" => $data['target_x'], "y" => $data['target_y']]);
        $solve_time = rand(5000, 10000);
    } else {
        return null;
    }

    dash_set('solve_type', $type);
    dash_log("[>]", "SOLVE ", "type={$type}", "\033[1;36m");

    usleep($solve_time);

    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => 'https://aruble.net/captcha/verify',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING       => '',
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => "key=$key&answer=" . urlencode($answer) . "&_csrf_token=$csrf",
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'User-Agent: '.$api,
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8',
        ],
    ]);
    $response = curl_exec($curl);
    if ($response === false || curl_errno($curl)) { curl_close($curl); return null; }
    curl_close($curl);

    $result = json_decode($response, true);
    if (empty($result['success']) || empty($result['token'])) {
        dash_log("[X]", "TOKEN ", "failed", "\033[1;31m");
        return null;
    }
    dash_log("[OK]", "TOKEN ", "received", "\033[1;32m");
    return $result['token'];
}

// ═══════════════════════════════════════════════════════════════
//  HTTP HELPERS
// ═══════════════════════════════════════════════════════════════
function http_get($url, $api) {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: '.$api,
            'sec-ch-ua-full-version: "149.0.7827.197"',
        ],
    ]);
    $res = curl_exec($curl);
    $code = curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);
    return ['body' => $res, 'code' => $code];
}

function http_post($url, $data, $api, $referer) {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING       => '',
        CURLOPT_MAXREDIRS      => 10,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_HTTP_VERSION   => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST  => 'POST',
        CURLOPT_POSTFIELDS     => $data,
        CURLOPT_COOKIEJAR      => COOKIE_FILE,
        CURLOPT_COOKIEFILE     => COOKIE_FILE,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER     => [
            'User-Agent: '.$api,
            'Accept: application/json, text/javascript, */*; q=0.01',
            'sec-ch-ua-platform: "Android"',
            'x-requested-with: XMLHttpRequest',
            'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Android WebView";v="146"',
            'content-type: application/x-www-form-urlencoded; charset=UTF-8',
            'sec-ch-ua-mobile: ?1',
            'origin: https://aruble.net',
            'sec-fetch-site: same-origin',
            'sec-fetch-mode: cors',
            'sec-fetch-dest: empty',
            'referer: '.$referer,
            'accept-language: en-GB,en-US;q=0.9,en;q=0.8',
            'priority: u=1, i',
        ],
    ]);
    $res = curl_exec($curl);
    curl_close($curl);
    return $res;
}

function extract_csrf($html) {
    return explode('">', explode('<meta name="csrf-token" content="', $html)[1] ?? '">')[0] ?? null;
}

function extract_title($html) {
    return explode('</title>', explode('<title>', $html)[1] ?? '</title>')[0] ?? '';
}

// ═══════════════════════════════════════════════════════════════
//  TASK REQUIRED PAUSE
// ═══════════════════════════════════════════════════════════════
function task_required_pause($msg, $taskNeeded, $cfg, $api) {
    global $DASH;

    dash_set('stage', 'TASK');
    dash_set('status', "Task required — {$taskNeeded} needed");

    dash_log("[!]", "TASK  ", "faucet butuh {$taskNeeded} task tambahan", "\033[1;33m");
    dash_log("[i]", "TASK  ", "selesaikan offers/PTC/shortlinks/videos dulu", "\033[1;36m");
    dash_render();

    // Box UI
    echo "\n";
    echo "\033[38;5;208m╔══════════════════════════════════════════════════════════════╗\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;33m⚠  TASK REQUIRED — ACTION NEEDED\033[0m                          \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m╠══════════════════════════════════════════════════════════════╣\033[0m\n";
    echo "\033[38;5;208m║\033[0m                                                              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;37mServer message:\033[0m                                           \033[38;5;208m║\033[0m\n";

    // wrap message
    $cleanMsg = strip_tags($msg);
    $lines = explode("\n", wordwrap($cleanMsg, 56, "\n", true));
    foreach ($lines as $line) {
        $pad = 56 - mb_strlen($line);
        if ($pad < 0) $pad = 0;
        echo "\033[38;5;208m║\033[0m  \033[38;5;245m" . $line . str_repeat(" ", $pad) . "\033[0m  \033[38;5;208m║\033[0m\n";
    }
    echo "\033[38;5;208m║\033[0m                                                              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m╠══════════════════════════════════════════════════════════════╣\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;33mLangkah yang harus lo lakuin:\033[0m                            \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m                                                              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;37m1. Buka browser, login ke aruble.net\033[0m                       \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;37m2. Selesaikan \033[1;36m" . str_pad($taskNeeded, 2, " ", STR_PAD_LEFT) . " task\033[0m \033[1;37m(offers/PTC/shortlinks/videos)\033[0m  \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;37m3. Balik ke script ini, ketik \033[1;32my\033[0m \033[1;37mbuat lanjut\033[0m              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m                                                              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m╠══════════════════════════════════════════════════════════════╣\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;32m[y]\033[0m \033[1;37mTask udah selesai, lanjut claim\033[0m                    \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;33m[c]\033[0m \033[1;37mCek status task lagi\033[0m                            \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m║\033[0m  \033[1;31m[q]\033[0m \033[1;37mKeluar dari farming\033[0m                              \033[38;5;208m║\033[0m\n";
    echo "\033[38;5;208m╚══════════════════════════════════════════════════════════════╝\033[0m\n\n";

    while (true) {
        echo "\033[1;35mSouuEngine\033[0m \033[1;36m»\033[0m \033[1;33mPilih\033[0m \033[1;37m[\033[1;32my\033[1;37m/\033[1;33mc\033[1;37m/\033[1;31mq\033[1;37m]\033[0m \033[1;35m>\033[0m ";
        $ans = strtolower(trim(fgets(STDIN)));

        if ($ans === 'y') {
            dash_log("[>]", "TASK  ", "user lanjut, verify ulang faucet...", "\033[1;36m");

            $check = http_get('https://aruble.net/faucet', $api);
            sleep(2);
            $checkBody = $check['body'];

            // cek masih ada task required atau engga
            if (preg_match('/complete\s+(\d+)\s+more\s+task/i', $checkBody, $tm2)) {
                $newNeeded = (int)$tm2[1];
                dash_log("[!]", "TASK  ", "task belum selesai, masih butuh {$newNeeded}", "\033[1;31m");
                echo "\n \033[38;5;208m⚠ Task belum selesai. Selesaikan {$newNeeded} task lagi, terus ketik 'y'.\033[0m\n\n";
                continue;
            }

            // coba claim ulang
            dash_log("[>]", "FAUCET", "coba claim ulang...", "\033[1;36m");
            $csrf2 = extract_csrf($checkBody);
            if (!$csrf2) {
                dash_log("[X]", "FAUCET", "no csrf, back to loop", "\033[1;31m");
                return;
            }

            // handle meta refresh
            if (preg_match('/<meta http-equiv="refresh" content="0;url=([^"]+)"/i', $checkBody, $mr)) {
                $check = http_get(trim($mr[1]), $api);
                sleep(2);
                $csrf2 = extract_csrf($check['body']);
                if (!$csrf2) {
                    dash_log("[X]", "FAUCET", "no csrf after refresh", "\033[1;31m");
                    return;
                }
            }

            $token = souuSolve($csrf2, $api, '/faucet');
            if (!$token) {
                dash_log("[X]", "FAUCET", "captcha failed, balik loop", "\033[1;31m");
                return;
            }

            dash_set('status', 'Faucet - retry claim');
            $body2 = "dest=account&wc_id=0&captcha_token=$token&fp=0d2be167b01027c02ec8e88326aaa91d26c20f1794b4c221d905fa603846c7c3&_csrf_token=$csrf2";
            $retry = http_post('https://aruble.net/faucet/claim', $body2, $api, 'https://aruble.net/faucet');
            $retryData = json_decode($retry, true);

            if ($retryData && ($retryData['success'] ?? false)) {
                $amount    = $retryData['amount'];
                $symbol    = $retryData['symbol'];
                $balance   = $retryData['balance_after'];
                $cooldownF = $retryData['next_claim_in'];
                $DASH['claims']++;
                $DASH['total_reward'] += (float)$amount;
                $DASH['last_reward'] = $amount;
                $DASH['currency'] = $symbol;
                $DASH['balance'] = $balance;
                dash_log("[OK]", "FAUCET", "+{$amount} {$symbol} | Balance {$balance}", "\033[1;32m");
                dash_log("[>]", "TASK  ", "task clear, balik ke cycle", "\033[1;32m");
                dash_timer($cooldownF, "Cooldown");
                return;
            } else {
                $retryMsg = $retryData['message'] ?? 'unknown';
                if (preg_match('/complete\s+(\d+)\s+more\s+task/i', $retryMsg, $tm3)) {
                    $newNeeded = (int)$tm3[1];
                    dash_log("[!]", "TASK  ", "masih butuh {$newNeeded} task, ulangi", "\033[1;33m");
                    continue;
                } else {
                    dash_log("[X]", "FAUCET", "retry failed: {$retryMsg}", "\033[1;31m");
                    return;
                }
            }
        }

        if ($ans === 'c') {
            dash_log("[>]", "TASK  ", "re-check status task...", "\033[1;36m");
            $check = http_get('https://aruble.net/faucet', $api);
            sleep(2);

            if (preg_match('/complete\s+(\d+)\s+more\s+task[^<]*/i', $check['body'], $mm)) {
                dash_log("[!]", "TASK  ", "masih butuh task: " . trim($mm[0]), "\033[1;33m");
            } else {
                dash_log("[OK]", "TASK  ", "task udah selesai, ketik 'y' buat lanjut", "\033[1;32m");
            }
            continue;
        }

        if ($ans === 'q') {
            dash_log("[!]", "TASK  ", "keluar dari farming", "\033[1;33m");
            return;
        }

        echo "\n \033[1;31m⚠ Pilihan ga valid. Ketik y / c / q.\033[0m\n\n";
    }
}

// ═══════════════════════════════════════════════════════════════
//  FARMING
// ═══════════════════════════════════════════════════════════════
function start_farming($cfg) {
    global $DASH;

    if (!config_ready($cfg)) {
        clr();
        echo box_top();
        echo box_line(gradient("SOUUENGINE :: ERROR"));
        echo box_div();
        echo box_line("\033[1;31m[!] Config belum lengkap!\033[0m");
        echo box_line("\033[38;5;51m└─ Isi Email + Password + User-Agent\033[0m");
        echo box_bot();
        prompt_enter("ENTER untuk balik...");
        return;
    }

    $email = $cfg['email'];
    $pass  = $cfg['password'];
    $api   = $cfg['user_agent'];

    $DASH['stage'] = 'LOGIN';
    $DASH['status'] = 'Starting';
    $DASH['user'] = '-';
    $DASH['balance'] = '-';
    $DASH['claims'] = 0;
    $DASH['total_reward'] = 0;
    $DASH['last_reward'] = '0';
    $DASH['fails'] = 0;
    $DASH['logs'] = [];
    $DASH['start_time'] = time();
    $DASH['solve_type'] = '-';
    $DASH['next_in'] = 0;

    dash_log("[*]", "BOOT  ", "SouuEngine " . SOOU_VERSION . " ready", "\033[1;32m");
    sleep(1);

    // ═══════════ LOGIN ═══════════
    if (!file_exists(COOKIE_FILE)) {
        $login_ok = false;
        $attempts = 0;

        while (!$login_ok && $attempts < 5) {
            $attempts++;
            @unlink(COOKIE_FILE);

            dash_log("[>]", "LOGIN ", "fetching homepage...", "\033[1;36m");
            dash_set('status', 'Login - GET /');

            $curl = curl_init();
            curl_setopt_array($curl, [
                CURLOPT_URL            => 'https://aruble.net',
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_ENCODING       => '',
                CURLOPT_MAXREDIRS      => 10,
                CURLOPT_TIMEOUT        => 30,
                CURLOPT_HTTP_VERSION   => CURL_HTTP_VERSION_1_1,
                CURLOPT_CUSTOMREQUEST  => 'GET',
                CURLOPT_COOKIEJAR      => COOKIE_FILE,
                CURLOPT_COOKIEFILE     => COOKIE_FILE,
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_SSL_VERIFYHOST => false,
                CURLOPT_HTTPHEADER     => [
                    'User-Agent: '.$api,
                    'cache-control: max-age=0',
                    'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Android WebView";v="146"',
                    'sec-ch-ua-mobile: ?1',
                    'sec-ch-ua-platform: "Android"',
                    'upgrade-insecure-requests: 1',
                    'x-requested-with: XMLHttpRequest',
                    'sec-fetch-site: none',
                    'sec-fetch-mode: navigate',
                    'sec-fetch-user: ?1',
                    'sec-fetch-dest: document',
                    'accept-language: en-GB,en-US;q=0.9,en;q=0.8',
                    'priority: u=0, i',
                ],
            ]);
            $res = curl_exec($curl);
            curl_close($curl);
            $csrf = extract_csrf($res);
            if (!$csrf) {
                dash_log("[!]", "LOGIN ", "no csrf, retry", "\033[1;33m");
                sleep(3);
                continue;
            }

            dash_set('status', 'Login - Solving captcha');
            $token = souuSolve($csrf, $api, '/login');
            if (!$token) {
                dash_log("[!]", "LOGIN ", "captcha failed, retry", "\033[1;33m");
                sleep(3);
                continue;
            }

            dash_set('status', 'Login - POST /api/auth/login');
            dash_log("[>]", "LOGIN ", "posting credentials...", "\033[1;36m");

            $body = "_csrf_token=$csrf&email=$email&password=$pass&captcha_token=$token&remember_me=1&device_fingerprint=0d2be167b01027c02ec8e88326aaa91d26c20f1794b4c221d905fa603846c7c3";
            $response = http_post('https://aruble.net/api/auth/login', $body, $api, 'https://aruble.net/');
            $data = json_decode($response, true);

            if ($data && ($data['success'] ?? false)) {
                $username = $data['user']['username'] ?? $data['user']['name'] ?? $data['username'] ?? 'User';
                dash_set('user', $username);
                dash_log("[OK]", "LOGIN ", $data['message'] ?? 'success', "\033[1;32m");
                $login_ok = true;
                sleep(2);
            } else {
                dash_set('fails', $DASH['fails'] + 1);
                $m = $data['message'] ?? 'unknown';
                dash_log("[X]", "LOGIN ", "failed: {$m}", "\033[1;31m");
                sleep(3);
            }
        }

        if (!$login_ok) {
            dash_log("[X]", "LOGIN ", "max attempts, balik menu", "\033[1;31m");
            sleep(3);
            return;
        }
    }

    // ═══════════ CYCLE ═══════════
    while (true) {

        // ── CHALLENGE ──
        $DASH['stage'] = 'CHALLENGE';
        $challenge_done = false;
        $challenge_retry = 0;

        while (!$challenge_done && $challenge_retry < 5) {
            $challenge_retry++;
            dash_set('status', 'Challenge - GET /challenge');

            $r = http_get('https://aruble.net/challenge', $api);
            sleep(rand(2, 4));
            $csrf = extract_csrf($r['body']);
            $title = extract_title($r['body']);

            if ($csrf === null) {
                dash_log("[!]", "CHALNG", "no csrf (HTTP {$r['code']})", "\033[1;33m");
                sleep(3);
                continue;
            }
            if ($title == "Just a moment...") {
                dash_log("[!]", "CHALNG", "Cloudflare challenge", "\033[1;33m");
                dash_timer(60, "CF Wait");
                continue;
            }
            if (stripos($r['body'], 'Please login') !== false) {
                @unlink(COOKIE_FILE);
                dash_log("[X]", "SESSION", "expired → relogin", "\033[1;31m");
                sleep(2);
                start_farming($cfg);
                return;
            }
            if (!preg_match('/onclick="claimChallenge\((\d+),\s*this\)"/i', $r['body'], $m)) {
                dash_log("[!]", "CHALNG", "no claim button", "\033[1;33m");
                $challenge_done = true;
                break;
            }
            $claimid = $m[1];
            botCheckSignal('/challenge', $api);
            dash_set('status', "Challenge - claim #{$claimid}");

            $body = http_build_query(['challenge_id' => $claimid, '_csrf_token' => $csrf]);
            $res2 = http_post('https://aruble.net/challenge/claim', $body, $api, 'https://aruble.net/challenge');
            $data = json_decode($res2, true);

            if (isset($data['message']) && ($data['message'] === "Invalid session. Please go back and try again." || $data['message'] === "Please login")) {
                @unlink(COOKIE_FILE);
                dash_log("[X]", "SESSION", "expired → relogin", "\033[1;31m");
                start_farming($cfg);
                return;
            }

            if ($data && ($data['success'] ?? false)) {
                $reward = $data['reward'] ?? 0;
                $DASH['claims']++;
                $DASH['total_reward'] += (float)$reward;
                $DASH['last_reward'] = $reward;
                $DASH['currency'] = 'COINS';
                dash_log("[OK]", "CHALNG", "[{$data['challenge_name']}] +{$reward} COINS", "\033[1;32m");
            } else {
                $msg = $data['message'] ?? 'failed';
                dash_log("[X]", "CHALNG", $msg, "\033[1;31m");
            }
            sleep(rand(2, 4));
        }

        // ── DAILY ──
        $DASH['stage'] = 'DAILY';
        dash_set('status', 'Daily - GET /daily-bonus');

        $r = http_get('https://aruble.net/daily-bonus', $api);
        sleep(rand(2, 4));
        $csrf = extract_csrf($r['body']);
        $title = extract_title($r['body']);

        if ($title == "Just a moment...") {
            dash_log("[!]", "DAILY ", "Cloudflare challenge", "\033[1;33m");
            dash_timer(60, "CF Wait");
        } elseif ($csrf === null) {
            dash_log("[!]", "DAILY ", "no csrf", "\033[1;33m");
        } elseif (strpos($r['body'], 'Come Back Later') !== false) {
            dash_log("[!]", "DAILY ", "Come Back Later", "\033[1;33m");
        } elseif (stripos($r['body'], 'Please login') !== false) {
            @unlink(COOKIE_FILE);
            dash_log("[X]", "SESSION", "expired → relogin", "\033[1;31m");
            start_farming($cfg);
            return;
        } else {
            $token = souuSolve($csrf, $api, '/daily-bonus');
            if ($token) {
                dash_set('status', 'Daily - claim');
                $body = "captcha_token=$token&_csrf_token=$csrf";
                $res2 = http_post('https://aruble.net/daily-bonus/claim', $body, $api, 'https://aruble.net/daily-bonus');
                $data = json_decode($res2, true);

                if ($data && ($data['success'] ?? false)) {
                    $amount  = $data['amount'];
                    $streak  = $data['streak'];
                    $balance = $data['balance_after'];
                    $symbol  = $data['symbol'];
                    $DASH['claims']++;
                    $DASH['total_reward'] += (float)$amount;
                    $DASH['last_reward'] = $amount;
                    $DASH['currency'] = $symbol;
                    $DASH['balance'] = $balance;
                    dash_log("[OK]", "DAILY ", "+{$amount} {$symbol} | Streak {$streak} | Balance {$balance}", "\033[1;32m");
                } else {
                    $msg = $data['message'] ?? 'failed';
                    dash_log("[!]", "DAILY ", $msg, "\033[1;33m");
                }
            } else {
                dash_log("[!]", "DAILY ", "captcha failed", "\033[1;33m");
            }
        }

        // ── FAUCET ──
        $DASH['stage'] = 'FAUCET';
        dash_set('status', 'Faucet - GET /faucet');

        $r = http_get('https://aruble.net/faucet', $api);
        sleep(rand(2, 4));

        if (preg_match('/<meta http-equiv="refresh" content="0;url=([^"]+)"/i', $r['body'], $m)) {
            $url = trim($m[1]);
            $r = http_get($url, $api);
            sleep(rand(2, 4));
        }

        $csrf = extract_csrf($r['body']);
        $title = extract_title($r['body']);

        if ($title == "Just a moment...") {
            dash_log("[!]", "FAUCET", "Cloudflare challenge", "\033[1;33m");
            dash_timer(60, "CF Wait");
        } elseif ($csrf === null) {
            dash_log("[!]", "FAUCET", "no csrf", "\033[1;33m");
        } elseif (stripos($r['body'], 'Please login') !== false) {
            @unlink(COOKIE_FILE);
            dash_log("[X]", "SESSION", "expired → relogin", "\033[1;31m");
            start_farming($cfg);
            return;
        } else {
            $cd = 0;
            if (preg_match('/globalCooldown\s*:\s*(\d+)/', $r['body'], $m)) {
                $cd = (int)$m[1];
            }

            if ($cd > 0) {
                dash_log("[!]", "COOLDN", "global cooldown {$cd}s", "\033[1;33m");
                dash_timer($cd + rand(5, 15), "Cooldown");
            } else {
                dash_log("[>]", "FAUCET", "ready, solving captcha...", "\033[1;36m");
                $token = souuSolve($csrf, $api, '/faucet');
                if ($token) {
                    dash_set('status', 'Faucet - claim');
                    $body = "dest=account&wc_id=0&captcha_token=$token&fp=0d2be167b01027c02ec8e88326aaa91d26c20f1794b4c221d905fa603846c7c3&_csrf_token=$csrf";
                    $res2 = http_post('https://aruble.net/faucet/claim', $body, $api, 'https://aruble.net/faucet');
                    $data = json_decode($res2, true);

                    if ($data && ($data['success'] ?? false)) {
                        $amount    = $data['amount'];
                        $symbol    = $data['symbol'];
                        $balance   = $data['balance_after'];
                        $cooldownF = $data['next_claim_in'];
                        $DASH['claims']++;
                        $DASH['total_reward'] += (float)$amount;
                        $DASH['last_reward'] = $amount;
                        $DASH['currency'] = $symbol;
                        $DASH['balance'] = $balance;
                        dash_log("[OK]", "FAUCET", "+{$amount} {$symbol} | Balance {$balance} | {$data['claims_today']}/{$data['claims_max']}", "\033[1;32m");
                        dash_timer($cooldownF, "Cooldown");
                    } else {
                        $msg = $data['message'] ?? 'failed';

                        // ═══ DETEKSI TASK REQUIRED ═══
                        if (preg_match('/complete\s+(\d+)\s+more\s+task/i', $msg, $tm)) {
                            $taskNeeded = (int)$tm[1];
                            task_required_pause($msg, $taskNeeded, $cfg, $api);
                        } elseif (stripos($msg, 'daily limit') !== false) {
                            dash_log("[!]", "FAUCET", "daily limit, next cycle", "\033[1;33m");
                        } else {
                            dash_log("[X]", "FAUCET", $msg, "\033[1;31m");
                        }
                    }
                } else {
                    dash_log("[!]", "FAUCET", "captcha failed", "\033[1;33m");
                }
            }
        }

        dash_log("[>]", "LOOP  ", "next cycle in " . CYCLE_WAIT . "s...", "\033[1;33m");
        sleep(CYCLE_WAIT);
    }
}

// ═══════════════════════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════════════════════
while (true) {
    $cfg = config_load();
    show_main_menu($cfg);

    $pilih = prompt_main();

    switch ($pilih) {
        case "1":
            start_farming($cfg);
            prompt_enter("ENTER untuk balik ke menu...");
            break;
        case "2":
            config_email($cfg);
            break;
        case "3":
            config_password($cfg);
            break;
        case "4":
            config_useragent($cfg);
            break;
        case "0":
            clr();
            echo "\n \033[1;32mTerima kasih. Sampai jumpa, bro.\033[0m\n";
            echo " \033[1;90mPowered by \033[0m\033[1;35m" . SOOU_AUTHOR . "\033[0m\033[1;90m • \033[0m\033[1;36mSouuEngine " . SOOU_VERSION . "\033[0m\n\n";
            exit;
        default:
            echo "\n \033[1;31m[!] Pilihan tidak valid.\033[0m\n";
            sleep(1);
    }
}
