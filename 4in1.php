<?php
error_reporting(0);
date_default_timezone_set('Asia/Jakarta');

// ============================================================
// GLOBAL CONFIG
// ============================================================
const CONFIG_FILE  = "faucet_4in1_config.json";
const SOLVER_IN    = "https://api.waryono.my.id/in.php";
const SOLVER_OUT   = "https://api.waryono.my.id/res.php";
const FF_DEVID     = "0000000000000000000000000000000000000000000000000000000000000000";

// ===== COLORS =====
const hitam  = "\033[0;30m";
const merah  = "\033[0;31m";
const hijau  = "\033[0;32m";
const kuning = "\033[0;33m";
const biru   = "\033[0;34m";
const cyan   = "\033[0;36m";
const putih  = "\033[0;37m";
const reset  = "\033[0m";

// ============================================================
// UTILS
// ============================================================
function kclear() { (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w')); }

function ktimer($seconds, $prefix = "[!] wait") {
    $w = (int)$seconds;
    if ($w < 1) return;
    $f = ['⣾','⣽','⣻','⢿','⡿','⣟','⣯','⣷'];
    $fc = count($f); $i = 0;
    while ($w > 0) {
        $st = microtime(true);
        while ((microtime(true) - $st) < 1) {
            $tf = sprintf('%02d:%02d:%02d', floor($w/3600), floor(($w%3600)/60), $w%60);
            echo putih . $prefix . hijau . " $tf " . putih . $f[$i] . "\r";
            usleep(100000); $i = ($i + 1) % $fc;
            if ((microtime(true) - $st) >= 1) break;
        }
        $w--;
    }
    echo "\r                                     \r";
}

function kfnum($n) { return rtrim(rtrim(number_format((float)$n, 8, '.', ''), '0'), '.'); }

function khttp($url, $payload = null, $headers = [], $method = "POST") {
    while (true) {
        $ch = curl_init();
        $opt = [
            CURLOPT_URL=>$url, CURLOPT_RETURNTRANSFER=>true, CURLOPT_FOLLOWLOCATION=>true,
            CURLOPT_SSL_VERIFYHOST=>2, CURLOPT_SSL_VERIFYPEER=>true,
            CURLOPT_HTTPHEADER=>$headers, CURLOPT_CONNECTTIMEOUT=>30, CURLOPT_TIMEOUT=>60,
            CURLOPT_COOKIEFILE=>'cookies.txt', CURLOPT_COOKIEJAR=>'cookies.txt'
        ];
        if ($method === "POST") { $opt[CURLOPT_POST]=true; $opt[CURLOPT_POSTFIELDS]=json_encode($payload); }
        curl_setopt_array($ch, $opt);
        $r = curl_exec($ch); curl_close($ch);
        if ($r) return $r;
        echo putih . "\nretry...\n"; sleep(2);
    }
}

function ksolve($apikey, $domain, $sitekey, $action = "") {
    while (true) {
        $body = ["apikey"=>$apikey,"methods"=>"turnstile","domain"=>$domain,"sitekey"=>$sitekey,"action"=>$action,"cdata"=>"","json"=>1];
        $req = khttp(SOLVER_IN, $body, ["Content-Type: application/json"]);
        foreach (["ERROR_WRONG_METHOD","ERROR_KEY_DOES_NOT_EXIST","ERROR_NO_SUCH_METHOD","ERROR_WRONG_USER_KEY","ERROR_ZERO_BALANCE","ERROR_BAD_PARAMETERS","ERROR_UNKNOWN"] as $e) {
            if (strpos($req, $e) !== false) { echo putih . "Err: " . merah . $e . "\n"; return null; }
        }
        if (strpos($req, "ERROR_TOO_MANY_REQUESTS") !== false) { sleep(2); continue; }
        $id = (json_decode($req, true))["request"] ?? "";
        if (!$id) { sleep(3); continue; }
        while (true) {
            ktimer(5, "  captcha...");
            $res = khttp(SOLVER_OUT . "?apikey=$apikey&action=get&id=$id&json=1", null, [], "GET");
            if (strpos($res, "CAPCHA_NOT_READY") !== false) continue;
            $j = json_decode($res, true);
            $tok = is_array($j) ? ($j["request"] ?? "") : "";
            if (is_string($tok) && strlen($tok) > 50 && strpos($tok, ".") !== false) {
                echo putih . "[CAPTCHA] " . hijau . "OK\n"; return $tok;
            }
            sleep(3);
        }
    }
}

// ============================================================
// CONFIG IO
// ============================================================
function cfg_load() {
    $f = CONFIG_FILE;
    $empty = ["apikey"=>"","apps"=>[
        "ff"=>["initData"=>"","coupon"=>""],
        "cp"=>["initData"=>"","coupon"=>""],
        "cf"=>["initData"=>"","coupon"=>""],
        "fm"=>["initData"=>"","coupon"=>""]
    ]];
    if (!file_exists($f)) { file_put_contents($f, json_encode($empty, JSON_PRETTY_PRINT)); return $empty; }
    $d = json_decode(file_get_contents($f), true);
    if (!is_array($d)) $d = $empty;
    if (!isset($d['apikey'])) $d['apikey'] = "";
    if (!isset($d['apps']) || !is_array($d['apps'])) $d['apps'] = [];
    foreach (["ff","cp","cf","fm"] as $k) {
        if (!isset($d['apps'][$k])) $d['apps'][$k] = ["initData"=>"","coupon"=>""];
        if (!isset($d['apps'][$k]['initData'])) $d['apps'][$k]['initData'] = "";
        if (!isset($d['apps'][$k]['coupon']))   $d['apps'][$k]['coupon']   = "";
    }
    return $d;
}
function cfg_save($d) { file_put_contents(CONFIG_FILE, json_encode($d, JSON_PRETTY_PRINT)); }
function cfg_apikey()      { return trim(cfg_load()['apikey']); }
function cfg_init($k)      { return trim(cfg_load()['apps'][$k]['initData'] ?? ''); }
function cfg_coupon($k)    { return trim(cfg_load()['apps'][$k]['coupon'] ?? ''); }
function cfg_set_init($k,$v)   { $d = cfg_load(); $d['apps'][$k]['initData'] = $v; cfg_save($d); }
function cfg_set_coupon($k,$v) { $d = cfg_load(); $d['apps'][$k]['coupon']   = $v; cfg_save($d); }

// ============================================================
// SHARED DETECTORS
// ============================================================
function is_blocked_resp($j) {
    if (!is_array($j)) return false;
    $st  = strtolower($j['status'] ?? '');
    $msg = strtolower($j['message'] ?? '');
    if (in_array($st, ['blocked','banned','suspended','unauthorized'])) return true;
    foreach (['under review','cannot use the faucet','cannot use','not allowed','banned','blocked','suspended','account disabled','account is disabled','forbidden','restricted','access denied','permanently','violation','unauthorized access','invalid initdata','initdata invalid'] as $kw) {
        if (strpos($msg, $kw) !== false) return true;
    }
    return false;
}
function is_expired_resp($j) {
    if (!is_array($j)) return false;
    $st  = strtolower($j['status'] ?? '');
    $msg = strtolower($j['message'] ?? '');
    if ($st === 'auth_failed') return true;
    foreach (['initdata expired','initdata tidak valid','init data expired','session expired','auth_date'] as $kw) {
        if (strpos($msg, $kw) !== false) return true;
    }
    return false;
}
function prompt_reprompt($key, $label, $msg = "initData expired") {
    echo putih . "\n[" . merah . $label . putih . "] " . kuning . $msg . "\n";
    echo putih . "Paste initData baru " . cyan . $label . putih . " (kosong=skip app ini): " . kuning;
    $v = trim(fgets(STDIN));
    if ($v === '') return false;
    cfg_set_init($key, $v);
    echo hijau . "OK tersimpan\n" . reset; sleep(1);
    return true;
}

// ============================================================
// APP 1: FaucetFi (mini.keran.co) - ff_
// ============================================================
const FF_API     = "https://mini.keran.co/api.php";
const FF_SITEKEY = "0x4AAAAAAACAEtFrYI5hvlhN";
const FF_DOMAIN  = "https://mini.keran.co";
const FF_MODES   = ["meteor","card","roll","wheel","box","target","scratch","chest"];

$FF_HEADERS = [
    'sec-ch-ua: "Not=A?Brand";v="99", "Android WebView";v="151", "Chromium";v="151"',
    'sec-ch-ua-platform: "Android"',
    'sec-ch-ua-mobile: ?1',
    'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1',
    'content-type: application/json',
    'origin: https://mini.keran.co',
    'x-requested-with: org.telegram.messenger.web',
    'referer: https://mini.keran.co/',
    'accept-language: en,id-ID;q=0.9,id;q=0.8'
];

function ff_api($action, $extra = []) {
    global $FF_HEADERS;
    $payload = array_merge(["action"=>$action, "initData"=>cfg_init('ff'), "deviceId"=>FF_DEVID], $extra);
    $res = khttp(FF_API, $payload, $FF_HEADERS);
    return json_decode($res, true) ?: ["status"=>"error","message"=>substr($res,0,200)];
}
function ff_blk($r) { if (is_blocked_resp($r)) { echo putih . "[FF] " . merah . ($r['message'] ?? 'blocked') . "\n"; return true; } return false; }
function ff_exp($r) { return is_expired_resp($r) ? prompt_reprompt('ff', 'FaucetFi', $r['message'] ?? 'expired') : false; }

function ff_claim_once(&$st) {
    $u = ff_api("get_user_data");
    if (ff_blk($u)) return 'blocked';
    if (ff_exp($u)) return 'expired';
    if (($u['status'] ?? '') != 'success') { $st['ready_at'] = time()+30; return 'cooldown'; }
    $d = $u['data'];

    if (!empty($st['first'])) {
        if (!empty($d['daily_streak']['can_checkin'])) {
            $ds = ff_api("claim_daily_streak");
            if (!ff_blk($ds) && !ff_exp($ds) && ($ds['status'] ?? '') == 'success') {
                $s = $ds['data'] ?? [];
                echo putih . "[FF-DAILY] " . hijau . "+" . ($s['reward_amount'] ?? '?') . " " . ($s['reward_coin'] ?? '') . "\n";
            }
        }
        if (floatval($d['referral_balance'] ?? 0) > 0) {
            $r = ff_api("claim_referral_earnings");
            if (!ff_blk($r) && !ff_exp($r) && ($r['status'] ?? '') == 'success') {
                echo putih . "[FF-REF] " . hijau . ($r['message'] ?? 'OK') . "\n";
            }
        }
        $cp = cfg_coupon('ff');
        if ($cp !== '') {
            $c = ff_api("redeem_daily_coupon", ["coupon_code" => $cp]);
            if (!ff_blk($c) && !ff_exp($c) && ($c['status'] ?? '') == 'success') {
                echo putih . "[FF-CPN] " . hijau . ($c['message'] ?? 'OK') . "\n";
            }
        }
        $st['first'] = false;
    }

    $used = intval($d['faucet_global_games_started_user'] ?? 0);
    $max = intval($d['faucet_global_daily_limit_user'] ?? 0);
    echo putih . "[FF] bal " . biru . ($d['balance'] ?? '?') . " " . strtoupper($d['preferred_coin'] ?? '') . putih . " | games " . $used . "/" . $max . "\n";

    if ($max > 0 && $used >= $max) return 'limited';

    $cd = intval($d['post_claim_cooldown_remaining'] ?? 0);
    if ($cd > 0) { $st['ready_at'] = time() + $cd; return 'cooldown'; }

    $mode = null; $spin = null;
    for ($i = 0; $i < count(FF_MODES); $i++) {
        $st['mode_idx'] = ($st['mode_idx'] + 1) % count(FF_MODES);
        $cand = FF_MODES[$st['mode_idx']];
        if (!empty($st['notified'][$cand])) continue;
        if (!empty($d['faucet_daily_limit_reached_' . $cand])) { $st['notified'][$cand] = true; continue; }
        $t = ff_api("get_faucet_spin_reward", ["mode" => $cand]);
        if (ff_blk($t)) return 'blocked';
        if (ff_exp($t)) return 'expired';
        if (($t['status'] ?? '') == 'success') { $mode = $cand; $spin = $t; break; }
        $msg = $t['message'] ?? '';
        if (stripos($msg,'limit') !== false || stripos($msg,'exhaust') !== false) { $st['notified'][$cand] = true; continue; }
        sleep(3);
    }
    if (!$mode) return 'limited';

    $gToken = $spin['gameToken'] ?? '';
    $dbl = ff_api("start_double_reward", ["mode"=>$mode, "gameToken"=>$gToken]);
    if (ff_blk($dbl)) return 'blocked';
    if (ff_exp($dbl)) return 'expired';
    if (($dbl['status'] ?? '') == 'success') {
        $challenge = $dbl['challenge'] ?? '';
        $nb = intval($dbl['not_before'] ?? 0);
        if ($nb > time()) ktimer($nb - time(), "  FF not_before...");
        $t1 = ksolve(cfg_apikey(), FF_DOMAIN, FF_SITEKEY, "double_reward");
        if ($t1) ff_api("complete_double_reward", ["mode"=>$mode,"gameToken"=>$gToken,"adProof"=>"","challenge"=>$challenge,"captchaToken"=>$t1]);
    }

    $t2 = ksolve(cfg_apikey(), FF_DOMAIN, FF_SITEKEY, "faucet_claim");
    if (!$t2) { $st['ready_at'] = time() + 10; return 'cooldown'; }

    $c = ff_api("claim_faucet", ["mode"=>$mode, "gameToken"=>$gToken, "captchaToken"=>$t2]);
    if (ff_blk($c)) return 'blocked';
    if (ff_exp($c)) return 'expired';
    if (($c['status'] ?? '') != 'success') {
        $m = $c['message'] ?? 'err';
        if (stripos($m,'limit') !== false) { $st['notified'][$mode] = true; return 'skip'; }
        echo putih . "[FF " . $mode . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 15; return 'cooldown';
    }
    $mult = ($c['double_applied'] ?? false) ? ($c['double_reward_multiplier'] ?? 2) : 1;
    echo putih . "[FF] " . kuning . $mode . putih . " +" . hijau . ($c['claimed_amount'] ?? '?') . " " . ($c['coin'] ?? '') . " x" . $mult . "\n";
    $cd2 = intval($c['post_claim_cooldown_seconds'] ?? 55);
    $st['ready_at'] = time() + $cd2 + mt_rand(2,5);
    return 'claimed';
}

// ============================================================
// APP 2: CoinPlay (tgapp.bagi.co.in) - cp_
// ============================================================
const CP_API     = "https://tgapp.bagi.co.in/api.php";
const CP_SITEKEY = "0x4AAAAAAACDrb9H09S1fhrY";
const CP_DOMAIN  = "https://tgapp.bagi.co.in";
const CP_ASSET   = "GRAM";
const CP_GAMES   = ["scratch","dig","safe","balloon","crystal","box","capsule","portal"];
const CP_POST_CD = 60;

$CP_HEADERS = [
    'content-type: application/json',
    'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1',
    'accept: application/json, text/plain',
    'origin: https://tgapp.bagi.co.in',
    'referer: https://tgapp.bagi.co.in/',
    'accept-language: en,id-ID;q=0.9,id;q=0.8'
];

function cp_api($action, $extra = []) {
    global $CP_HEADERS;
    $payload = array_merge(["action"=>$action, "initData"=>cfg_init('cp'),
        "clientInfo"=>["user_agent"=>"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/151.0 Mobile Safari/537.36","platform"=>"android","timezone"=>"Asia/Jakarta"]
    ], $extra);
    $res = khttp(CP_API, $payload, $CP_HEADERS);
    return json_decode($res, true) ?: ["status"=>"error","message"=>substr($res,0,200)];
}
function cp_blk($r) { if (is_blocked_resp($r)) { echo putih . "[CP] " . merah . ($r['message'] ?? 'blocked') . "\n"; return true; } return false; }
function cp_exp($r) { return is_expired_resp($r) ? prompt_reprompt('cp', 'CoinPlay', $r['message'] ?? 'expired') : false; }

function cp_claim_once(&$st) {
    $u = cp_api("get_user_data", ["gameType"=>"scratch"]);
    if (cp_blk($u)) return 'blocked';
    if (cp_exp($u)) return 'expired';
    if (($u['status'] ?? '') != 'success') { $st['ready_at'] = time()+30; return 'cooldown'; }
    $d = $u['data'] ?? [];
    $gs = $d['game_stats'] ?? [];

    if (!empty($st['first'])) {
        $s = cp_api("get_daily_bonus_status");
        if (!cp_blk($s) && !cp_exp($s) && ($s['status'] ?? '') == 'success' && !empty($s['data']['can_claim'])) {
            $r = cp_api("claim_daily_bonus");
            if (!cp_blk($r) && !cp_exp($r) && ($r['status'] ?? '') == 'success') {
                $dd = $r['data'] ?? $r;
                echo putih . "[CP-DAILY] " . hijau . "+" . ($dd['reward'] ?? $dd['amount'] ?? '?') . " " . CP_ASSET . "\n";
            }
        }
        $rf = cp_api("claim_referral_earnings");
        if (!cp_blk($rf) && !cp_exp($rf) && ($rf['status'] ?? '') == 'success') {
            echo putih . "[CP-REF] " . hijau . ($rf['message'] ?? 'OK') . "\n";
        }
        $cp = cfg_coupon('cp');
        if ($cp !== '') {
            $c = cp_api("redeem_daily_coupon", ["coupon_code" => $cp]);
            if (!cp_blk($c) && !cp_exp($c) && ($c['status'] ?? '') == 'success') {
                echo putih . "[CP-CPN] " . hijau . ($c['message'] ?? 'OK') . "\n";
            }
        }
        $st['first'] = false;
    }

    echo putih . "[CP] bal " . biru . ($d['balance'] ?? '?') . " " . CP_ASSET . "\n";

    $pl = intval($d['post_claim_start_cooldown_remaining'] ?? 0);
    if ($pl > 0) { $st['ready_at'] = time() + $pl; return 'cooldown'; }

    $picked = null;
    for ($i = 0; $i < count(CP_GAMES); $i++) {
        $st['mode_idx'] = ($st['mode_idx'] + 1) % count(CP_GAMES);
        $cand = CP_GAMES[$st['mode_idx']];
        if (!empty($st['notified'][$cand])) continue;
        if (isset($st['ready_at_mode'][$cand]) && $st['ready_at_mode'][$cand] > time()) continue;
        $s = $gs[$cand] ?? [];
        if (!empty($s['last_claim_timestamp_unix']) && intval($s['spins_today'] ?? 0) > 0) {
            $ends = intval($s['last_claim_timestamp_unix']) + ($s['spins_today'] < 3 ? 300 : 300 + (($s['spins_today'] - 3) * 60));
            if ($ends > time()) { $st['ready_at_mode'][$cand] = $ends; continue; }
        }
        $picked = $cand; break;
    }
    if (!$picked) {
        $minw = 999999; $now = time();
        foreach ($st['ready_at_mode'] as $t) if ($t > $now && $t-$now < $minw) $minw = $t-$now;
        if ($minw >= 999999) return 'limited';
        $st['ready_at'] = $now + $minw;
        return 'cooldown';
    }

    $spin = cp_api("get_game_reward", ["gameType"=>$picked]);
    if (cp_blk($spin)) return 'blocked';
    if (cp_exp($spin)) return 'expired';
    if (($spin['status'] ?? '') != 'success') {
        $m = $spin['message'] ?? '';
        if (stripos($m,'limit') !== false || stripos($m,'exhaust') !== false) { $st['notified'][$picked] = true; return 'skip'; }
        $rem = intval($spin['cooldown_remaining'] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[CP " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10; return 'cooldown';
    }

    $needDbl = false;
    $dbl = cp_api("confirm_double_reward", ["gameType"=>$picked]);
    if (cp_blk($dbl)) return 'blocked';
    if (cp_exp($dbl)) return 'expired';
    if (($dbl['status'] ?? '') == 'success') $needDbl = true;

    $tok = ksolve(cfg_apikey(), CP_DOMAIN, CP_SITEKEY, "");
    if (!$tok) { $st['ready_at'] = time() + 10; return 'cooldown'; }

    $c = cp_api("claim_faucet", ["gameType"=>$picked, "captchaToken"=>$tok, "requireDouble"=>$needDbl]);
    if (cp_blk($c)) return 'blocked';
    if (cp_exp($c)) return 'expired';
    if (($c['status'] ?? '') != 'success') {
        $m = $c['message'] ?? 'err';
        if (stripos($m,'limit') !== false) { $st['notified'][$picked] = true; return 'skip'; }
        $rem = intval($c['cooldown_remaining'] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[CP " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10; return 'cooldown';
    }
    $credit = $c['credited_amount'] ?? $c['base_reward'] ?? '?';
    $mult = !empty($c['double_applied']) ? floatval($c['multiplier'] ?? 2) : 1;
    echo putih . "[CP] " . kuning . $picked . putih . " +" . hijau . $credit . " " . CP_ASSET . " (x" . $mult . ")\n";
    $st['ready_at'] = time() + intval($c['post_claim_start_cooldown_seconds'] ?? CP_POST_CD);
    return 'claimed';
}

// ============================================================
// APP 3: CoinFree (coinfree.app) - cf_  [PATCHED]
// ============================================================
const CF_API     = "https://coinfree.app/api.php";
const CF_SITEKEY = "0x4AAAAAAB6mAUIH75NUE5fq";
const CF_DOMAIN  = "https://coinfree.app";
// FIX: "roll" udah invalid, dihapus. 8 mode valid.
const CF_MODES   = ["drop","coinflip","claw","plinko","target","box","card","wheel"];
const CF_RATE_LIMIT_WAIT = 90;   // detik, kalau kena "Too many requests from this IP"
const CF_MODE_LIMIT_WAIT = 3600; // detik, kalau mode limit harian

$CF_HEADERS = [
    'content-type: application/json',
    'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1',
    'accept: application/json, text/plain',
    'origin: https://coinfree.app',
    'referer: https://coinfree.app/',
    'accept-language: en,id-ID;q=0.9,id;q=0.8'
];

function cf_api($action, $extra = []) {
    global $CF_HEADERS;
    $payload = array_merge(["action"=>$action, "initData"=>cfg_init('cf'), "deviceId"=>FF_DEVID], $extra);
    $res = khttp(CF_API, $payload, $CF_HEADERS);
    return json_decode($res, true) ?: ["status"=>"error","message"=>substr($res,0,200)];
}
function cf_blk($r) { if (is_blocked_resp($r)) { echo putih . "[CF] " . merah . ($r['message'] ?? 'blocked') . "\n"; return true; } return false; }
function cf_exp($r) { return is_expired_resp($r) ? prompt_reprompt('cf', 'CoinFree', $r['message'] ?? 'expired') : false; }

// helper: klasifikasi pesan error CF
function cf_classify($msg) {
    $m = strtolower(is_string($msg) ? $msg : '');
    if ($m === '') return 'unknown';
    if (strpos($m, 'too many requests') !== false || strpos($m, 'rate limit') !== false || strpos($m, 'slow down') !== false)
        return 'ratelimit';
    if (strpos($m, 'invalid faucet mode') !== false || strpos($m, 'unknown mode') !== false || strpos($m, 'mode not found') !== false || strpos($m, 'invalid mode') !== false)
        return 'invalid_mode';
    if (strpos($m, 'limit') !== false || strpos($m, 'exhaust') !== false || strpos($m, 'daily') !== false || strpos($m, 'cap') !== false)
        return 'limited';
    if (strpos($m, 'cooldown') !== false || strpos($m, 'wait') !== false)
        return 'cooldown';
    return 'unknown';
}

function cf_claim_once(&$st) {
    $u = cf_api("get_user_data");
    if (cf_blk($u)) return 'blocked';
    if (cf_exp($u)) return 'expired';
    if (($u['status'] ?? '') != 'success') { $st['ready_at'] = time()+30; return 'cooldown'; }
    $d = $u['data'] ?? $u;

    // ===== first-time: daily, referral, coupon =====
    if (!empty($st['first'])) {
        $r = cf_api("claim_daily_streak");
        if (!cf_blk($r) && !cf_exp($r) && ($r['status'] ?? '') == 'success') {
            $s = $r['data'] ?? [];
            echo putih . "[CF-DAILY] " . hijau . "+" . ($s['reward_amount'] ?? '?') . " " . strtoupper($s['reward_coin'] ?? '') . "\n";
        }
        $rf = cf_api("claim_referral_earnings");
        if (!cf_blk($rf) && !cf_exp($rf) && ($rf['status'] ?? '') == 'success') {
            echo putih . "[CF-REF] " . hijau . ($rf['message'] ?? 'OK') . "\n";
        }
        $cp = cfg_coupon('cf');
        if ($cp !== '') {
            $c = cf_api("redeem_daily_coupon", ["coupon_code" => $cp]);
            if (!cf_blk($c) && !cf_exp($c) && ($c['status'] ?? '') == 'success') {
                echo putih . "[CF-CPN] " . hijau . ($c['message'] ?? 'OK') . "\n";
            }
        }
        $st['first'] = false;
    }

    echo putih . "[CF] bal " . biru . kfnum($d['balance'] ?? 0) . " " . strtoupper($d['preferred_coin'] ?? '') . "\n";

    // ===== global cooldown =====
    $gl = intval($d['faucet_global_cooldown_remaining'] ?? 0);
    if ($gl > 0) { $st['ready_at'] = time() + $gl; return 'cooldown'; }

    // ===== cari mode yang ready =====
    $now = time();
    $picked = null;
    $shortest = 999999;

    for ($i = 0; $i < count(CF_MODES); $i++) {
        $st['mode_idx'] = ($st['mode_idx'] + 1) % count(CF_MODES);
        $m = CF_MODES[$st['mode_idx']];

        // FIX: skip kalau mode udah di-mark dead (invalid mode) atau notified (limit)
        if (!empty($st['dead'][$m]))     continue;
        if (!empty($st['notified'][$m])) continue;

        // FIX: cek ready_at_mode dulu sebelum query cooldown
        if (isset($st['ready_at_mode'][$m]) && $st['ready_at_mode'][$m] > $now) {
            $shortest = min($shortest, $st['ready_at_mode'][$m] - $now);
            continue;
        }

        $left = intval($d["faucet_cooldown_remaining_".$m] ?? 0);
        if ($left > 0) {
            $st['ready_at_mode'][$m] = $now + $left;
            $shortest = min($shortest, $left);
            continue;
        }
        $picked = $m;
        break;
    }

    if (!$picked) {
        if ($shortest < 999999) {
            $st['ready_at'] = $now + $shortest;
            return 'cooldown';
        }
        return 'limited';
    }

    // ===== get spin reward =====
    $spin = cf_api("get_faucet_spin_reward", ["mode"=>$picked]);
    if (cf_blk($spin)) return 'blocked';
    if (cf_exp($spin)) return 'expired';

    if (($spin['status'] ?? '') != 'success') {
        $m = $spin['message'] ?? '';
        $cls = cf_classify($m);

        if ($cls === 'ratelimit') {
            // FIX: rate limit IP → tunggu lama, JANGAN retry cepat
            echo putih . "[CF " . $picked . "] " . kuning . "rate-limit IP, tunggu " . CF_RATE_LIMIT_WAIT . "s\n";
            $st['ready_at'] = time() + CF_RATE_LIMIT_WAIT;
            return 'cooldown';
        }
        if ($cls === 'invalid_mode') {
            // FIX: mode invalid → mark dead permanen
            if (empty($st['notified'][$picked])) {
                echo putih . "[CF " . $picked . "] " . kuning . "mode tidak tersedia, buang\n";
                $st['notified'][$picked] = true;
            }
            $st['dead'][$picked] = true;
            $st['ready_at'] = time() + 2;
            return 'cooldown';
        }
        if ($cls === 'limited') {
            if (empty($st['notified'][$picked])) {
                echo putih . "[CF " . $picked . "] " . kuning . "limit tercapai\n";
                $st['notified'][$picked] = true;
            }
            $st['ready_at_mode'][$picked] = time() + CF_MODE_LIMIT_WAIT;
            $st['ready_at'] = time() + 2;
            return 'cooldown';
        }
        if ($cls === 'cooldown') {
            $rem = intval($spin["faucet_cooldown_remaining_".$picked] ?? $spin['cooldown_remaining'] ?? 0);
            if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        }

        $rem = intval($spin["faucet_cooldown_remaining_".$picked] ?? $spin['cooldown_remaining'] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[CF " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10;
        return 'cooldown';
    }

    // ===== solve captcha =====
    $tok = ksolve(cfg_apikey(), CF_DOMAIN, CF_SITEKEY, "faucet_claim");
    if (!$tok) { $st['ready_at'] = time() + 10; return 'cooldown'; }

    // ===== claim =====
    $cf = cf_api("claim_faucet", ["mode"=>$picked, "captchaToken"=>$tok]);
    if (cf_blk($cf)) return 'blocked';
    if (cf_exp($cf)) return 'expired';

    if (($cf['status'] ?? '') != 'success') {
        $m = $cf['message'] ?? 'err';
        $cls = cf_classify($m);

        if ($cls === 'ratelimit') {
            echo putih . "[CF " . $picked . "] " . kuning . "rate-limit IP, tunggu " . CF_RATE_LIMIT_WAIT . "s\n";
            $st['ready_at'] = time() + CF_RATE_LIMIT_WAIT;
            return 'cooldown';
        }
        if ($cls === 'invalid_mode') {
            $st['dead'][$picked] = true;
            $st['notified'][$picked] = true;
            $st['ready_at'] = time() + 2;
            return 'cooldown';
        }
        if ($cls === 'limited') {
            $st['notified'][$picked] = true;
            $st['ready_at_mode'][$picked] = time() + CF_MODE_LIMIT_WAIT;
            $st['ready_at'] = time() + 2;
            return 'cooldown';
        }

        $rem = intval($cf["faucet_cooldown_remaining_".$picked] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[CF " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10;
        return 'cooldown';
    }

    // ===== sukses =====
    $dd = $cf['data'] ?? $cf;
    $amt = $dd['claimed_amount'] ?? $dd['reward_amount'] ?? '?';
    echo putih . "[CF] " . kuning . $picked . putih . " +" . hijau . kfnum($amt) . "\n";
    $st['ready_at'] = time() + intval($dd['faucet_global_cooldown_seconds'] ?? 60) + mt_rand(2,5);
    return 'claimed';
}

// ============================================================
// APP 4: FaucetMini (faucetmini.app) - fm_
// ============================================================
const FM_API     = "https://faucetmini.app/api.php";
const FM_SITEKEY = "0x4AAAAAABuBae9KLy3ELiTP";
const FM_DOMAIN  = "https://faucetmini.app";
const FM_GAMES   = ["spin","balloon","claw","flip","neon","portal","rocket","tap"];

$FM_HEADERS = [
    'content-type: application/json',
    'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1',
    'accept: application/json, text/plain, */*',
    'origin: https://faucetmini.app',
    'referer: https://faucetmini.app/',
    'accept-language: en,id-ID;q=0.9,id;q=0.8'
];

function fm_api($action, $extra = []) {
    global $FM_HEADERS;
    $payload = array_merge(["action"=>$action, "initData"=>cfg_init('fm'),
        "clientInfo"=>["user_agent"=>"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/151.0 Mobile Safari/537.36","platform"=>"android","timezone"=>"Asia/Jakarta"]
    ], $extra);
    $res = khttp(FM_API, $payload, $FM_HEADERS);
    return json_decode($res, true) ?: ["status"=>"error","message"=>substr($res,0,200)];
}
function fm_asset($d) {
    $s = strtoupper(trim($d['asset_symbol'] ?? $d['symbol'] ?? 'USDT'));
    return preg_match('/^[A-Z0-9]{2,10}$/', $s) ? $s : 'USDT';
}
function fm_cdw($j, $def = 60) {
    foreach (['global_game_cooldown_remaining','faucet_global_cooldown_remaining','cooldown_remaining','post_claim_start_cooldown_remaining'] as $k) {
        if (isset($j[$k]) && intval($j[$k]) > 0) return intval($j[$k]);
    }
    foreach (['global_game_cooldown_seconds','faucet_global_cooldown_seconds'] as $k) {
        if (isset($j[$k]) && intval($j[$k]) > 0) return intval($j[$k]);
    }
    return $def;
}
function fm_blk($r) { if (is_blocked_resp($r)) { echo putih . "[FM] " . merah . ($r['message'] ?? 'blocked') . "\n"; return true; } return false; }
function fm_exp($r) { return is_expired_resp($r) ? prompt_reprompt('fm', 'FaucetMini', $r['message'] ?? 'expired') : false; }

function fm_claim_once(&$st) {
    $u = fm_api("get_user_data");
    if (fm_blk($u)) return 'blocked';
    if (fm_exp($u)) return 'expired';
    if (($u['status'] ?? '') != 'success') { $st['ready_at'] = time()+30; return 'cooldown'; }
    $d = $u['data'] ?? $u;
    $gs = $d['game_stats'] ?? [];

    if (!empty($st['first'])) {
        $s = fm_api("get_daily_bonus_status");
        if (!fm_blk($s) && !fm_exp($s) && ($s['status'] ?? '') == 'success' && !empty($s['data']['can_claim'])) {
            $r = fm_api("claim_daily_bonus");
            if (!fm_blk($r) && !fm_exp($r) && ($r['status'] ?? '') == 'success') {
                $rd = $r['data'] ?? $r;
                echo putih . "[FM-DAILY] " . hijau . "+" . kfnum($rd['reward_amount'] ?? $rd['reward'] ?? '?') . " " . strtoupper($rd['reward_coin'] ?? 'USDT') . "\n";
            }
        }
        $rf = fm_api("claim_referral_earnings");
        if (!fm_blk($rf) && !fm_exp($rf) && ($rf['status'] ?? '') == 'success') {
            echo putih . "[FM-REF] " . hijau . ($rf['message'] ?? 'OK') . "\n";
        }
        $cp = cfg_coupon('fm');
        if ($cp !== '') {
            $c = fm_api("redeem_daily_coupon", ["coupon_code" => $cp]);
            if (!fm_blk($c) && !fm_exp($c) && ($c['status'] ?? '') == 'success') {
                echo putih . "[FM-CPN] " . hijau . ($c['message'] ?? 'OK') . "\n";
            }
        }
        $st['first'] = false;
    }

    echo putih . "[FM] bal " . biru . kfnum($d['balance'] ?? 0) . " " . fm_asset($d) . "\n";

    $gl = fm_cdw($d, 0);
    if ($gl > 0) { $st['ready_at'] = time() + $gl; return 'cooldown'; }

    $now = time(); $picked = null;
    for ($i = 0; $i < count(FM_GAMES); $i++) {
        $st['mode_idx'] = ($st['mode_idx'] + 1) % count(FM_GAMES);
        $m = FM_GAMES[$st['mode_idx']];
        if (!empty($st['notified'][$m])) continue;
        if (isset($st['ready_at_mode'][$m]) && $st['ready_at_mode'][$m] > $now) continue;
        $s = $gs[$m] ?? [];
        if (!empty($s['last_claim_timestamp_unix']) && intval($s['spins_today'] ?? 0) > 0) {
            $cd = intval($s['cooldown_seconds'] ?? $d['global_game_cooldown_seconds'] ?? 60);
            $ends = intval($s['last_claim_timestamp_unix']) + $cd;
            if ($ends > $now) { $st['ready_at_mode'][$m] = $ends; continue; }
        }
        $picked = $m; break;
    }
    if (!$picked) {
        $minw = 999999;
        foreach ($st['ready_at_mode'] as $t) if ($t > $now && $t-$now < $minw) $minw = $t-$now;
        if ($minw >= 999999) return 'limited';
        $st['ready_at'] = $now + $minw;
        return 'cooldown';
    }

    $spin = fm_api("get_faucet_spin_reward", ["gameType"=>$picked]);
    if (fm_blk($spin)) return 'blocked';
    if (fm_exp($spin)) return 'expired';
    if (($spin['status'] ?? '') != 'success') {
        $m = $spin['message'] ?? '';
        if (stripos($m,'limit')!==false || stripos($m,'exhaust')!==false || stripos($m,'cap')!==false) { $st['notified'][$picked] = true; return 'skip'; }
        $rem = intval($spin['cooldown_remaining'] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[FM " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10; return 'cooldown';
    }

    $tok = ksolve(cfg_apikey(), FM_DOMAIN, FM_SITEKEY, "faucet_claim");
    if (!$tok) { $st['ready_at'] = time() + 10; return 'cooldown'; }

    $cf = fm_api("claim_faucet", ["gameType"=>$picked, "captchaToken"=>$tok, "requireDouble"=>false]);
    if (fm_blk($cf)) return 'blocked';
    if (fm_exp($cf)) return 'expired';
    if (($cf['status'] ?? '') != 'success') {
        $m = $cf['message'] ?? 'err';
        if (stripos($m,'limit') !== false) { $st['notified'][$picked] = true; return 'skip'; }
        $rem = intval($cf['cooldown_remaining'] ?? 0);
        if ($rem > 0) { $st['ready_at'] = time() + $rem; return 'cooldown'; }
        echo putih . "[FM " . $picked . "] " . merah . $m . "\n";
        $st['ready_at'] = time() + 10; return 'cooldown';
    }
    $dd = $cf['data'] ?? $cf;
    $amt = $dd['credited_amount'] ?? $dd['claimed_amount'] ?? $dd['base_reward'] ?? '?';
    $mult = !empty($dd['double_applied']) ? floatval($dd['multiplier'] ?? 2) : 1;
    echo putih . "[FM] " . kuning . $picked . putih . " +" . hijau . kfnum($amt) . " " . fm_asset($d) . ($mult>1?" x".$mult:"") . "\n";
    $st['ready_at'] = time() + fm_cdw($cf, 60);
    return 'claimed';
}

// ============================================================
// ROTASI MASTER (FM -> CP -> CF -> FF)
// ============================================================
function run_rotasi($apps = ['fm','cp','cf','ff']) {
    $labels = ['fm'=>'FaucetMini','cp'=>'CoinPlay','cf'=>'CoinFree','ff'=>'FaucetFi'];
    $st = [];
    foreach ($apps as $a) {
        // FIX: tambah 'dead' buat track mode yang invalid/mati
        $st[$a] = [
            'limited' => false,
            'ready_at' => 0,
            'mode_idx' => -1,
            'first' => true,
            'notified' => [],
            'dead' => [],
            'ready_at_mode' => []
        ];
    }

    kclear();
    echo putih . "=== ROTASI: " . strtoupper(implode(" -> ", $apps)) . " ===\n";
    echo putih . "per-app 1x claim, abis itu ganti. limit/blocked -> stop app\n";
    echo putih . "------------------------------------------\n";

    while (true) {
        $alive = [];
        foreach ($apps as $a) if (!$st[$a]['limited']) $alive[] = $a;
        if (empty($alive)) {
            echo putih . "\n" . hijau . "Semua app limit/blocked. Selesai.\n";
            return;
        }

        $now = time();
        $did_any = false;

        foreach ($alive as $a) {
            if ($st[$a]['ready_at'] > $now) continue;

            echo putih . "\n--- " . cyan . $labels[$a] . putih . " ---\n";
            try {
                $fn = $a . '_claim_once';
                $res = $fn($st[$a]);
            } catch (\Throwable $e) {
                echo putih . "[" . merah . $labels[$a] . putih . "] " . merah . $e->getMessage() . putih . " (skip)\n";
                $st[$a]['ready_at'] = time() + 30;
                continue;
            }
            $did_any = true;

            if ($res === 'limited') {
                $st[$a]['limited'] = true;
                echo putih . "[" . kuning . $labels[$a] . putih . "] " . kuning . "LIMIT -> keluar dari rotasi\n";
            } elseif ($res === 'blocked') {
                $st[$a]['limited'] = true;
                echo putih . "[" . merah . $labels[$a] . putih . "] " . merah . "BLOCKED -> keluar dari rotasi\n";
            } elseif ($res === 'expired') {
                if (cfg_init($a) === '') {
                    $st[$a]['limited'] = true;
                    echo putih . "[" . kuning . $labels[$a] . putih . "] " . kuning . "skip (initData kosong)\n";
                }
            }
        }

        if (!$did_any) {
            $minw = 999999; $now = time();
            foreach ($alive as $a) {
                $w = $st[$a]['ready_at'] - $now;
                if ($w < $minw) $minw = $w;
            }
            if ($minw < 1) $minw = 5;
            if ($minw > 99999) $minw = 10;
            ktimer($minw, "  tunggu...");
        }
    }
}

// ============================================================
// MENU
// ============================================================
function menu_set_init($key, $label) {
    kclear();
    $cur = cfg_init($key);
    echo putih . "=== Config initData: " . cyan . $label . putih . " ===\n\n";
    echo putih . "Sekarang: " . (empty($cur) ? kuning . "(kosong)" : hijau . substr($cur,0,60).'...') . "\n\n";
    echo putih . "Paste initData " . cyan . $label . putih . " (kosong=batal, '-'=hapus):\n" . kuning;
    $v = trim(fgets(STDIN));
    if ($v === '') { echo putih . "batal.\n"; sleep(1); return; }
    if ($v === '-') { cfg_set_init($key, ""); echo hijau . "dihapus.\n" . reset; sleep(1); return; }
    cfg_set_init($key, $v);
    echo hijau . "OK tersimpan\n" . reset; sleep(1);
}
function menu_set_coupon($key, $label) {
    kclear();
    $cur = cfg_coupon($key);
    echo putih . "=== Coupon: " . cyan . $label . putih . " ===\n\n";
    echo putih . "Sekarang: " . (empty($cur) ? kuning . "(kosong)" : hijau . $cur) . "\n\n";
    echo putih . "Isi coupon (kosong=batal, '-'=hapus):\n" . kuning;
    $v = trim(fgets(STDIN));
    if ($v === '') { echo putih . "batal.\n"; sleep(1); return; }
    if ($v === '-') { cfg_set_coupon($key, ""); echo hijau . "dihapus.\n" . reset; sleep(1); return; }
    cfg_set_coupon($key, $v);
    echo hijau . "OK\n" . reset; sleep(1);
}
function menu_config_app($key, $label) {
    while (true) {
        kclear();
        $init = cfg_init($key);
        $coupon = cfg_coupon($key);
        echo putih . "==========================================\n";
        echo putih . "  Config: " . cyan . $label . putih . "\n";
        echo putih . "==========================================\n";
        echo putih . "initData : " . (empty($init) ? merah . "(kosong)" : hijau . substr($init,0,40).'...') . "\n";
        echo putih . "coupon   : " . (empty($coupon) ? kuning . "(kosong)" : hijau . $coupon) . "\n";
        echo putih . "------------------------------------------\n";
        echo putih . "  1. Set initData\n";
        echo putih . "  2. Set coupon\n";
        echo putih . "  3. Hapus initData\n";
        echo putih . "  4. Hapus coupon\n";
        echo putih . "  0. Kembali\n";
        echo putih . "pilih: " . kuning;
        $o = trim(fgets(STDIN));
        if ($o == '1') menu_set_init($key, $label);
        elseif ($o == '2') menu_set_coupon($key, $label);
        elseif ($o == '3') { cfg_set_init($key, ""); echo hijau . "initData dihapus\n" . reset; sleep(1); }
        elseif ($o == '4') { cfg_set_coupon($key, ""); echo hijau . "coupon dihapus\n" . reset; sleep(1); }
        elseif ($o == '0') return;
    }
}

function menu_main() {
    while (true) {
        kclear();
        $cfg = cfg_load();
        echo putih . "==========================================\n";
        echo putih . "   MULTI FAUCET 4IN1 (ROTASI)\n";
        echo putih . "==========================================\n";
        echo putih . "apikey : " . (empty($cfg['apikey']) ? merah . "(belum diset)" : hijau . substr($cfg['apikey'],0,10) . "...") . "\n";
        echo putih . "initData:\n";
        foreach (['fm'=>'FaucetMini','cp'=>'CoinPlay','cf'=>'CoinFree','ff'=>'FaucetFi'] as $k=>$n) {
            $v = $cfg['apps'][$k]['initData'] ?? '';
            $c = $cfg['apps'][$k]['coupon'] ?? '';
            echo putih . "  " . str_pad($n, 12) . ": " . (empty($v) ? kuning . "(kosong)" : hijau . substr($v,0,15).'...');
            if (!empty($c)) echo putih . " cp:" . hijau . $c;
            echo "\n";
        }
        echo putih . "------------------------------------------\n";
        echo putih . "  1. " . cyan . "Start Rotasi ALL 4 (FM -> CP -> CF -> FF)\n";
        echo putih . "  2. " . cyan . "Start Rotasi custom\n";
        echo putih . "  3. " . cyan . "Run Single App\n";
        echo putih . "  4. " . cyan . "Reset Semua InitData\n";
        echo putih . "  5. " . cyan . "Config Apikey\n";
        echo putih . "  6. " . cyan . "Config FaucetMini\n";
        echo putih . "  7. " . cyan . "Config CoinPlay\n";
        echo putih . "  8. " . cyan . "Config CoinFree\n";
        echo putih . "  9. " . cyan . "Config FaucetFi\n";
        echo putih . "  0. " . merah . "Exit\n";
        echo putih . "pilih: " . kuning;
        $opt = trim(fgets(STDIN));

        if ($opt == '1') { run_rotasi(['fm','cp','cf','ff']); echo putih . "\nenter..."; fgets(STDIN); }
        elseif ($opt == '2') {
            kclear();
            echo putih . "Pilih app (pisah spasi, contoh: fm cf ff): " . kuning;
            $line = trim(fgets(STDIN));
            $picked = preg_split('/[\s,]+/', strtolower($line));
            $valid = [];
            foreach ($picked as $p) if (in_array($p, ['fm','cp','cf','ff'])) $valid[] = $p;
            if (empty($valid)) { echo merah . "nggak ada yang valid.\n" . reset; sleep(2); continue; }
            run_rotasi($valid);
            echo putih . "\nenter..."; fgets(STDIN);
        }
        elseif ($opt == '3') {
            kclear();
            echo putih . "Pilih app:\n";
            echo putih . "  1. FaucetMini\n  2. CoinPlay\n  3. CoinFree\n  4. FaucetFi\n";
            echo putih . "pilih: " . kuning;
            $s = trim(fgets(STDIN));
            $map = ['1'=>'fm','2'=>'cp','3'=>'cf','4'=>'ff'];
            if (isset($map[$s])) {
                $st = [
                    'limited' => false, 'ready_at' => 0, 'mode_idx' => -1,
                    'first' => true, 'notified' => [], 'dead' => [], 'ready_at_mode' => []
                ];
                $fn = $map[$s] . '_claim_once';
                echo putih . "\n--- single run ---\n";
                $fn($st);
                echo putih . "\nenter..."; fgets(STDIN);
            }
        }
        elseif ($opt == '4') {
            $d = cfg_load();
            foreach (["ff","cp","cf","fm"] as $k) { $d['apps'][$k]['initData'] = ""; $d['apps'][$k]['coupon'] = ""; }
            cfg_save($d);
            echo hijau . "Semua initData & coupon dihapus\n" . reset; sleep(1);
        }
        elseif ($opt == '5') {
            kclear();
            echo putih . "Apikey sekarang: " . kuning . (empty($cfg['apikey']) ? "(kosong)" : substr($cfg['apikey'],0,20).'...') . "\n\n";
            echo putih . "Apikey baru: " . kuning;
            $k = trim(fgets(STDIN));
            if ($k !== '') { $d = cfg_load(); $d['apikey'] = $k; cfg_save($d); echo hijau . "OK\n" . reset; sleep(1); }
        }
        elseif ($opt == '6') menu_config_app('fm', 'FaucetMini');
        elseif ($opt == '7') menu_config_app('cp', 'CoinPlay');
        elseif ($opt == '8') menu_config_app('cf', 'CoinFree');
        elseif ($opt == '9') menu_config_app('ff', 'FaucetFi');
        elseif ($opt == '0') exit;
    }
}

// ============================================================
// BOOT
// ============================================================
menu_main();
