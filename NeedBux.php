<?php

error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE);
date_default_timezone_set('Asia/Jakarta');
$configFile = "needbux.json";

/* ═══════════ COLOR CONSTANTS ═══════════ */
const hitam  = "\033[0;30m";
const merah  = "\033[0;31m";
const hijau  = "\033[0;32m";
const kuning = "\033[0;33m";
const biru   = "\033[0;34m";
const cyan   = "\033[0;36m";
const putih  = "\033[0;37m";
const reset  = "\033[0m";

const RST  = "\033[0m";
const RED  = "\033[0;31m";
const GRN  = "\033[0;32m";
const YEL  = "\033[0;33m";
const WHT  = "\033[0;37m";
const BOLD = "\033[1m";

/* ═══════════ SITE CONFIG ═══════════ */
const version     = "1.0";
const script_name = "needbux.com";
const host        = "https://needbux.com";
const SOLVER_IN   = "https://api.waryono.my.id/in.php";
const SOLVER_RES  = "https://api.waryono.my.id/res.php";

/* ═══════════ RICH ANSI ═══════════ */
function fg($c){ return "\033[38;5;{$c}m"; }
function ansi_len($s){
    $plain = preg_replace('/\x1b\[[0-9;]*m/','',$s);
    $w = 0;
    $len = mb_strlen($plain, 'UTF-8');
    for ($i=0; $i<$len; $i++){
        $ch = mb_substr($plain,$i,1,'UTF-8');
        $cp = mb_ord($ch, 'UTF-8');
        if (($cp>=0x1F300 && $cp<=0x1F9FF) || ($cp>=0x2600 && $cp<=0x27BF) ||
            ($cp>=0x2B00 && $cp<=0x2BFF) || ($cp>=0x25A0 && $cp<=0x25FF) ||
            ($cp>=0x2580 && $cp<=0x259F)) { $w += 2; }
        else { $w += 1; }
    }
    return $w;
}
function ansi_pad($s,$len){ $p = $len - ansi_len($s); return $s . ($p>0 ? str_repeat(' ',$p) : ''); }
function gradient($text,$start=51,$end=196){
    $len = mb_strlen($text,'UTF-8');
    if ($len<=1) return fg($start).$text.RST;
    $out = '';
    for ($i=0; $i<$len; $i++){
        $t = $i/max(1,$len-1);
        $c = (int)round($start + ($end-$start)*$t);
        $out .= fg($c).mb_substr($text,$i,1,'UTF-8');
    }
    return $out.RST;
}
function box_line($c){ return fg(51)."║  ".RST.ansi_pad($c,60).fg(51)."║".RST."\n"; }
function box_div(){ return fg(51)."╠".str_repeat("═",62)."╣".RST."\n"; }

/* ═══════════ GLOBAL STATE ═══════════ */
$GLOBALS['_logs']        = [];
$GLOBALS['_startTime']   = time();
$GLOBALS['_claims']      = 0;
$GLOBALS['_rewards']     = 0.0;
$GLOBALS['_fails']       = 0;
$GLOBALS['_maxFails']    = 5;
$GLOBALS['_email']       = 'Unknown';
$GLOBALS['_user']        = 'Unknown';
$GLOBALS['_solverTag']   = 'waryono';
$GLOBALS['_activeCoin']  = '-';
$GLOBALS['_coinRewards'] = [];
$GLOBALS['_lastReward']  = 0.0;
$GLOBALS['_lastCoin']    = '-';

function push_log($msg, $tag='i'){
    $icons = ['i'=>fg(51)."●".RST, 'ok'=>fg(46)."✔".RST, 'er'=>fg(196)."✖".RST,
              'wr'=>fg(208)."◈".RST, 'in'=>fg(213)."⬢".RST, 'g'=>fg(226)."◆".RST];
    $ts = date('H:i:s');
    $line = fg(250)."[{$ts}]".RST." ".($icons[$tag]??'●')." ".$msg;
    $GLOBALS['_logs'][] = $line;
    if (count($GLOBALS['_logs'])>6) array_shift($GLOBALS['_logs']);
}

function fmt_uptime($s){
    $s = (int)$s;
    $h = floor($s/3600);
    $m = floor(($s%3600)/60);
    $sec = $s%60;
    return sprintf('%02d:%02d:%02d', $h, $m, $sec);
}

/* ═══════════ BANNER ═══════════ */
function banner(){
    $elapsed = time() - $GLOBALS['_startTime'];
    $claims  = $GLOBALS['_claims'];
    $rewards = $GLOBALS['_rewards'];
    $fails   = $GLOBALS['_fails'];
    $maxF    = $GLOBALS['_maxFails'];
    $email   = $GLOBALS['_email'];
    $user    = $GLOBALS['_user'];

    echo "\033[2J\033[H";

    echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
    echo box_line(gradient("NEEDBUX AUTO CLAIM", 51, 213));
    echo box_line(fg(240)."─────── SOUU ENGINE ───────".RST);
    echo box_div();

    echo box_line(fg(213).BOLD."CAPTCHA".RST);
    echo box_line(fg(51)."├─ Type     : ".RST.fg(226)."HCAPTCHA (rotation)".RST);
    echo box_line(fg(51)."└─ Solver   : ".RST.fg(226).$GLOBALS['_solverTag']."/lime".RST);
    echo box_div();

    echo box_line(fg(213).BOLD."ACCOUNT".RST);
    echo box_line(fg(51)."├─ User       : ".RST.fg(226).$user.RST);
    echo box_line(fg(51)."└─ Email      : ".RST.fg(226).$email.RST);
    echo box_div();

    echo box_line(fg(213).BOLD."INCOME".RST);
    echo box_line(fg(51)."├─ Total      : ".RST.fg(46)."+".number_format($rewards,8).RST);
    echo box_line(fg(51)."├─ Last       : ".RST.fg(46)."+".number_format($GLOBALS['_lastReward'],8)." ".strtoupper($GLOBALS['_lastCoin']).RST);

    $breakdown = "";
    foreach ($GLOBALS['_coinRewards'] as $c => $amt) {
        if ($amt <= 0) continue;
        $breakdown .= strtoupper($c)." ".number_format($amt,8)."  ";
    }
    if ($breakdown !== '') {
        echo box_line(fg(51)."└─ Per-coin   : ".RST.fg(226).substr($breakdown, 0, 50).RST);
    } else {
        echo box_line(fg(51)."└─ Per-coin   : ".RST.fg(240)."—".RST);
    }
    echo box_div();

    echo box_line(fg(213).BOLD."SYSTEM".RST);
    echo box_line(fg(51)."├─ Coin         : ".RST.fg(226).strtoupper($GLOBALS['_activeCoin']).RST);
    echo box_line(fg(51)."├─ Claims       : ".RST.fg(226).$claims.RST);
    echo box_line(fg(51)."├─ Failures     : ".RST.($fails>=$maxF?fg(196):fg(226)).$fails." / ".$maxF.RST);
    echo box_line(fg(51)."└─ Runtime      : ".RST.fg(226).fmt_uptime($elapsed).RST);
    echo box_div();

    $logs = $GLOBALS['_logs'];
    $rows = 6;
    for ($i=0; $i<$rows; $i++){
        if (isset($logs[$i])) echo box_line(fg(252).$logs[$i].RST);
        else echo fg(51)."║".str_repeat(" ",62)."║".RST."\n";
    }

    echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
    echo "\n   ".gradient("BOT RUNNING", 46, 226)." ".fg(250)."• ".date('H:i:s').RST."\n";
    echo "   ".fg(240)."By Power ".RST.fg(213)."@SouuXso".RST.fg(240)." • ".RST.fg(46)."NeedBux Edition".RST."\n\n";
}

/* ═══════════ REWARD PARSER ═══════════ */
function parseReward($html) {
    if (preg_match('/([0-9.]+)\s+([A-Z]+)\s+was added successfully/i', $html, $m)) {
        return ['amount' => (float)$m[1], 'coin' => strtoupper($m[2])];
    }
    if (preg_match('/([0-9.]+)\s+([A-Z]+)\s+(?:has been|was)\s+added/i', $html, $m)) {
        return ['amount' => (float)$m[1], 'coin' => strtoupper($m[2])];
    }
    if (preg_match('/([0-9.]+)\s+([A-Z]{2,10})/i', strip_tags($html), $m)) {
        if (stripos($html, 'success') !== false || stripos($html, 'added') !== false) {
            return ['amount' => (float)$m[1], 'coin' => strtoupper($m[2])];
        }
    }
    return null;
}

/* ═══════════ PARSERS ═══════════ */
function parseAlerts($html) {
    $alerts = [];
    preg_match_all('/<div[^>]*class="([^"]*alert-[^"]*)"[^>]*>(.*?)<\/div>/is', $html, $matches, PREG_SET_ORDER);
    foreach ($matches as $m) {
        $class = strtolower($m[1]);
        if (strpos($class, 'alert') === false) continue;
        if (strpos($class, 'alert-') === false) continue;
        $text = trim(preg_replace('/\s+/', ' ', strip_tags($m[2])));
        if ($text === '') continue;
        if (preg_match('/^please wait\s+\d+\s+seconds?$/i', $text)) continue;
        $alerts[] = ['class' => $class, 'text' => $text];
    }
    return $alerts;
}

function parseError($response, $httpCode = 0, $location = '') {
    if ($httpCode === 302 && stripos($location, 'instant-faucet-list') !== false) {
        return ['type' => 'success', 'message' => 'claimed (redirect)', 'raw' => $response];
    }
    if (stripos($response, 'added successfully') !== false) {
        return ['type' => 'success', 'message' => 'added successfully', 'raw' => $response];
    }

    $alerts = parseAlerts($response);
    $texts  = array_column($alerts, 'text');
    $joined = strtolower(implode(' | ', $texts));

    if (strpos($response, 'Page Expired') !== false) {
        return ['type' => 'csrf_expired', 'message' => 'CSRF token expired', 'raw' => $response];
    }
    if (preg_match('/claim again after\s+([0-9]{2}):([0-9]{2})\s+Minutes/i', $response, $t)) {
        return ['type' => 'cooldown', 'minutes' => (int)$t[1], 'seconds' => (int)$t[2],
                'message' => 'cooldown ' . $t[1] . ':' . $t[2], 'raw' => $response];
    }
    if ($joined !== '') {
        if (strpos($joined, 'email field') !== false) {
            return ['type' => 'email_error', 'message' => $texts[0], 'raw' => $response];
        }
        if (strpos($joined, 'captcha') !== false
            && (strpos($joined, 'failed') !== false || strpos($joined, 'required') !== false
                || strpos($joined, 'invalid') !== false || strpos($joined, 'verification') !== false)) {
            return ['type' => 'captcha_error', 'message' => $texts[0], 'raw' => $response];
        }
        if (strpos($joined, 'too many') !== false || strpos($joined, 'rate limit') !== false) {
            return ['type' => 'rate_limit', 'message' => $texts[0], 'raw' => $response];
        }
        if (strpos($joined, 'daily limit') !== false || strpos($joined, 'limit reached') !== false
            || strpos($joined, 'exhaust') !== false || strpos($joined, 'already claimed') !== false) {
            return ['type' => 'daily_limit', 'message' => $texts[0], 'raw' => $response];
        }
        if (strpos($joined, 'an error occurred') !== false) {
            return ['type' => 'server_error', 'message' => $texts[0], 'raw' => $response];
        }
    }
    foreach ($alerts as $a) {
        $low = strtolower($a['text']);
        if (strpos($a['class'], 'danger') !== false) continue;
        if (strpos($a['class'], 'success') !== false || strpos($low, 'success') !== false
            || strpos($low, 'reward') !== false || strpos($low, 'claimed') !== false
            || strpos($low, 'congrats') !== false) {
            return ['type' => 'success', 'message' => $a['text'], 'raw' => $response];
        }
    }
    foreach ($alerts as $a) {
        if (strpos($a['class'], 'danger') !== false) {
            return ['type' => 'error', 'message' => $a['text'], 'raw' => $response];
        }
    }
    if (preg_match('/<h1[^>]*>\s*(\d{3})\s*<\/h1>/i', $response, $m)) {
        return ['type' => 'http_error', 'code' => (int)$m[1], 'raw' => $response];
    }
    return ['type' => 'unknown', 'raw' => $response, 'alerts' => $texts];
}

/* ═══════════ UTIL ═══════════ */
function clear() {
    if (PHP_OS_FAMILY === 'Windows') { @pclose(@popen('cls', 'w')); }
    else { system('clear'); }
}

function skibidixxx($url, $method = 'GET', $data = [], $headers = [], $noFollow = false) {
    $ch = curl_init();
    $final_headers = [];
    foreach ($headers as $header) { $final_headers[] = $header; }
    $options = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HEADER         => true,
        CURLOPT_FOLLOWLOCATION => !$noFollow,
        CURLOPT_MAXREDIRS      => 5,
        CURLOPT_SSL_VERIFYHOST => 1,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_HTTPHEADER     => $final_headers,
        CURLOPT_CONNECTTIMEOUT => 60,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_COOKIEFILE     => 'cookies.txt',
        CURLOPT_COOKIEJAR      => 'cookies.txt',
    ];
    if (strtoupper($method) === 'POST') {
        $options[CURLOPT_POST] = true;
        $options[CURLOPT_POSTFIELDS] = $data;
    }
    curl_setopt_array($ch, $options);
    $response = curl_exec($ch);
    if ($response === false) {
        $err = curl_error($ch);
        curl_close($ch);
        return ['body'=>"curl error: $err", 'code'=>0, 'headers'=>'', 'location'=>''];
    }
    $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $rawHeaders  = substr($response, 0, $header_size);
    $body        = substr($response, $header_size);
    $code        = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $GLOBALS['last_url'] = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
    curl_close($ch);

    $location = '';
    if (preg_match_all('/^location:\s*(.+)$/mi', $rawHeaders, $lm)) {
        $location = trim(end($lm[1]));
    }
    return ['body'=>$body, 'code'=>$code, 'headers'=>$rawHeaders, 'location'=>$location];
}

function timer($seconds, $prefix = "[!] please wait") {
    $wait_time = (int)$seconds;
    $frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
    $frame_count = count($frames);
    $current_frame = 0;
    $frame_delay = 0.1;
    while ($wait_time > 0) {
        $start_time = microtime(true);
        while ((microtime(true) - $start_time) < 1) {
            $hours = floor($wait_time / 3600);
            $minutes = floor(($wait_time % 3600) / 60);
            $seconds_left = $wait_time % 60;
            $time_formatted = sprintf('%02d:%02d:%02d', $hours, $minutes, $seconds_left);
            $spinner = $frames[$current_frame];
            echo putih . $prefix . hijau . " $time_formatted " . putih . $spinner . "\r";
            usleep((int)($frame_delay * 1000000));
            $current_frame = ($current_frame + 1) % $frame_count;
            if ((microtime(true) - $start_time) >= 1) break;
        }
        $wait_time--;
    }
    echo "\r" . str_repeat(" ", 60) . "\r";
}

/* ═══════════ CONFIG ═══════════ */
function getConfig($configFile) {
    if (!file_exists($configFile)) {
        clear();
        banner();
        echo putih . "API Key   : " . kuning;
        $apikey = trim(fgets(STDIN));
        echo putih . "Email     : " . kuning;
        $email = trim(fgets(STDIN));
        $data = ["apikey" => $apikey, "email" => $email];
        file_put_contents($configFile, json_encode($data, JSON_PRETTY_PRINT));
        $GLOBALS['_email'] = $email;
        echo hijau . "Konfigurasi disimpan ke $configFile\n\n" . reset;
        sleep(2);
        return $data;
    }
    $cfg = json_decode(file_get_contents($configFile), true);
    if (!is_array($cfg)) $cfg = ['apikey'=>'','email'=>''];
    if (isset($cfg['email'])) $GLOBALS['_email'] = $cfg['email'];
    return $cfg;
}

/* ═══════════ SOLVER ═══════════ */
function hc($apikey, $sitekey) {
    $headers = ["Content-Type: application/json"];
    $body = json_encode([
        "apikey"  => $apikey,
        "methods" => "hcaptcha",
        "domain"  => host,
        "sitekey" => $sitekey,
        "json"    => 1
    ]);
    $req = skibidixxx(SOLVER_IN, "POST", $body, $headers);
    $request = $req['body'];

    $fatal = [
        "ERROR_WRONG_METHOD","ERROR_KEY_DOES_NOT_EXIST","ERROR_METHOD_NOT_SPECIFIED",
        "ERROR_NO_SUCH_METHOD","ERROR_DATABASE_CONNECTION_FAILED",
        "ERROR_WRONG_USER_KEY","ERROR_ZERO_BALANCE","ERROR_BAD_PARAMETERS",
        "ERROR_EMPTY_IMAGE","ERROR_UNKNOWN"
    ];
    foreach ($fatal as $f) {
        if (strpos($request, $f) !== false) {
            push_log("solver fatal: $f", 'er');
            return $f;
        }
    }
    if (strpos($request, "ERROR_TOO_MANY_REQUESTS") !== false) {
        return "ERROR_TOO_MANY_REQUESTS";
    }

    $json = json_decode($request, true);
    $id   = $json["request"] ?? '';
    if ($id === '') return "NO_ID";

    for ($i = 0; $i < 30; $i++) {
        timer(3, "  hcap... ");
        $url    = SOLVER_RES."?apikey=".$apikey."&action=get&id=".$id."&json=1";
        $r      = skibidixxx($url, "GET", []);
        $result = $r['body'];

        if (strpos($result, "CAPCHA_NOT_READY") !== false) continue;
        if (strpos($result, "ERROR_CAPTCHA_UNSOLVABLE") !== false) return "ERROR_CAPTCHA_UNSOLVABLE";
        if (strpos($result, "WRONG_CAPTCHA_ID") !== false)         return "WRONG_CAPTCHA_ID";
        if (strpos($result, "ERROR_SOLVE_PENDING") !== false)      continue;
        if (strpos($result, "ERROR_BAD_PARAMETERS") !== false)     return "ERROR_BAD_PARAMETERS";
        if (strpos($result, "Database connection failed") !== false) return "DB_FAIL";
        if (strpos($result, "ERROR_BAD_REQUEST") !== false)        return "ERROR_BAD_REQUEST";
        if (strpos($result, "INTENAL_SERVER_ERROR") !== false)     return "INTENAL_SERVER_ERROR";

        $j = json_decode($result, true);
        if (is_array($j) && isset($j["request"])) {
            return ["captcha" => $j["request"]];
        }
    }
    return "TIMEOUT";
}

/* ═══════════ HEADERS ═══════════ */
function kon(&$a, &$b){
    $a = [
        "host: needbux.com",
        "user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language: id-ID,id;q=0.9,en;q=0.8",
        "upgrade-insecure-requests: 1",
    ];
    $b = [
        "host: needbux.com",
        "content-type: application/x-www-form-urlencoded",
        "user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "origin: https://needbux.com",
        "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language: id-ID,id;q=0.9,en;q=0.8",
        "upgrade-insecure-requests: 1",
        "referer: https://needbux.com/"
    ];
}

/* ═══════════ EMAIL PROMPT ═══════════ */
function promptEmail($current = '') {
    global $configFile;
    echo putih . "Email FaucetPay baru" . ($current !== '' ? " (sekarang: $current)" : "") . ": " . kuning;
    $new = trim(fgets(STDIN));
    if ($new === '') {
        echo putih . "[EMAIL] batal, tetap pakai email lama.\n" . reset;
        return $current;
    }
    $cfg = file_exists($configFile) ? json_decode(file_get_contents($configFile), true) : [];
    if (!is_array($cfg)) $cfg = [];
    $cfg['email'] = $new;
    file_put_contents($configFile, json_encode($cfg, JSON_PRETTY_PRINT));
    $GLOBALS['_email'] = $new;
    echo hijau . "[EMAIL] disimpan ke $configFile\n" . reset;
    return $new;
}

/* ═══════════ CLAIM ═══════════ */
function claimCoin($selected_coin, $a, $b, $apikey, &$email, $loop = true) {
    $GLOBALS['_activeCoin'] = $selected_coin;
    $attempt = 0;

    while (true) {
        $attempt++;

        $pageResp = skibidixxx(host."/?faucet=".$selected_coin, "GET", [], $a);
        $faucet   = $pageResp['body'];

        if (preg_match('/claim again after\s+([0-9]{2}):([0-9]{2})\s+Minutes/i', $faucet, $t_match)) {
            $menit = (int)$t_match[1];
            $detik = (int)$t_match[2];
            $total_seconds = ($menit * 60) + $detik;
            if ($total_seconds > 0) {
                push_log("cooldown ".$menit."m".$detik."s | ".strtoupper($selected_coin), 'wr');
                banner();
                timer($total_seconds + 2, "  cooldown..");
                continue;
            }
        }

        $csrf_token = '';
        if (preg_match('/name="_token"\s+value="([^"]+)"/i', $faucet, $m)) {
            $csrf_token = $m[1];
        } elseif (preg_match('/<meta name="csrf-token" content="([^"]+)"/i', $faucet, $m)) {
            $csrf_token = $m[1];
        }

        preg_match('/id="timer-data"\s+data-seconds="([^"]+)"/i', $faucet, $timer_match);
        $timer_seconds = (int)($timer_match[1] ?? 0);

        preg_match('/class="h-captcha"\s+data-sitekey="([^"]+)"/i', $faucet, $captcha_match);
        $sitekey = $captcha_match[1] ?? '';

        preg_match('/name="currency"[^>]*value="([^"]+)"/i', $faucet, $currency_match);
        $currency = $currency_match[1] ?? strtoupper($selected_coin);

        if ($timer_seconds > 0) {
            push_log("wait ".$timer_seconds."s (page timer)", 'wr');
            banner();
            timer($timer_seconds + 1, "  timer..");

            $pageResp = skibidixxx(host."/?faucet=".$selected_coin, "GET", [], $a);
            $faucet   = $pageResp['body'];
            if (preg_match('/name="_token"\s+value="([^"]+)"/i', $faucet, $m)) $csrf_token = $m[1];
            if (preg_match('/<meta name="csrf-token" content="([^"]+)"/i', $faucet, $m)) $csrf_token = $m[1];
            preg_match('/class="h-captcha"\s+data-sitekey="([^"]+)"/i', $faucet, $captcha_match);
            $sitekey = $captcha_match[1] ?? $sitekey;
        }

        if ($csrf_token === '' || $sitekey === '') {
            push_log("token/sitekey kosong — refresh", 'er');
            banner();
            sleep(2);
            if (!$loop) return false;
            continue;
        }

        push_log("solver solving ".strtoupper($selected_coin)."... (attempt $attempt)", 'in');
        banner();

        $bypass = hc($apikey, $sitekey);
        if (is_array($bypass)) {
            push_log("captcha solved", 'in');
            banner();

            $post_headers = $b;
            $post_headers[count($post_headers) - 1] = "referer: https://needbux.com/?faucet=".$selected_coin;

            $data = http_build_query([
                "_token"               => $csrf_token,
                "email"                => $email,
                "g-recaptcha-response" => $bypass["captcha"],
                "h-captcha-response"   => $bypass["captcha"],
                "countdown_value"      => "0",
                "currency"             => $currency,
                "submitbtn"            => ""
            ]);

            $claimResp = skibidixxx(host, "POST", $data, $post_headers, true);
            $claim     = $claimResp['body'];
            $code      = $claimResp['code'];
            $location  = $claimResp['location'];

            if ($code === 302 && $location !== '') {
                $follow = skibidixxx($location, "GET", [], $a);
                $claim  = $follow['body'];
            }

            $parsed = parseError($claim, $code, $location);

            if ($parsed['type'] === 'success') {
                $rewardInfo = parseReward($claim);
                if ($rewardInfo) {
                    $rewardAmt  = $rewardInfo['amount'];
                    $rewardCoin = $rewardInfo['coin'];
                    $GLOBALS['_lastReward'] = $rewardAmt;
                    $GLOBALS['_lastCoin']   = $rewardCoin;
                    $GLOBALS['_rewards']   += $rewardAmt;
                    if (!isset($GLOBALS['_coinRewards'][$rewardCoin])) {
                        $GLOBALS['_coinRewards'][$rewardCoin] = 0.0;
                    }
                    $GLOBALS['_coinRewards'][$rewardCoin] += $rewardAmt;
                    $GLOBALS['_claims']++;
                    push_log("+".number_format($rewardAmt,8)." ".$rewardCoin." | total: ".number_format($GLOBALS['_rewards'],8), 'ok');
                } else {
                    $GLOBALS['_claims']++;
                    push_log("+".strtoupper($selected_coin)." claimed (reward unknown)", 'ok');
                }
                banner();
                return true;
            }
            if ($parsed['type'] === 'captcha_error') {
                $GLOBALS['_fails']++;
                push_log("VERIFY Wrong: ".$parsed['message'], 'wr');
                banner();
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'email_error') {
                push_log("VERIFY Email: ".$parsed['message'], 'er');
                banner();
                $email = promptEmail($email);
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'rate_limit') {
                push_log("VERIFY Rate: ".$parsed['message'], 'er');
                banner();
                timer(30, "  rate limit..");
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'daily_limit') {
                push_log("VERIFY Limit: ".$parsed['message'], 'wr');
                banner();
                return false;
            }
            if ($parsed['type'] === 'server_error') {
                push_log("VERIFY Server: ".$parsed['message'], 'er');
                banner();
                if (!$loop) return false;
                sleep(3);
                continue;
            }
            if ($parsed['type'] === 'cooldown') {
                $total_seconds = (($parsed['minutes'] ?? 0) * 60) + ($parsed['seconds'] ?? 0);
                push_log("VERIFY Cooldown: ".$parsed['message'], 'wr');
                banner();
                if ($total_seconds > 0) timer($total_seconds + 2, "  cooldown..");
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'csrf_expired') {
                push_log("VERIFY CSRF expired, refreshing...", 'er');
                banner();
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'http_error') {
                push_log("VERIFY HTTP ".$parsed['code'], 'er');
                banner();
                if (!$loop) return false;
                continue;
            }
            if ($parsed['type'] === 'error') {
                push_log("VERIFY: ".$parsed['message'], 'er');
                banner();
                if (!$loop) return false;
                continue;
            }
            if ($code === 302) {
                $GLOBALS['_claims']++;
                push_log("+ claimed (302) | ".strtoupper($selected_coin), 'ok');
                banner();
                return true;
            }
            push_log("VERIFY Unknown (HTTP $code)", 'er');
            banner();
            if (!$loop) return false;
            continue;
        } else {
            $err = is_string($bypass) ? $bypass : 'UNKNOWN';
            push_log("solver err: $err — retry in 3s", 'er');
            banner();
            sleep(3);
            continue;
        }
    }
}

/* ═══════════ ENTRY ═══════════ */
$config = getConfig($configFile);
$apikey = $config['apikey'] ?? '';
$email  = $config['email'] ?? '';
if ($apikey === '') { echo merah."apikey kosong, edit $configFile\n"; exit; }
$GLOBALS['_email'] = $email;

clear();
banner();
kon($a, $b);

/* ═══ MENU PILIHAN ═══ */
clear();
echo fg(51)."╔".str_repeat("═",62)."╗".RST."\n";
echo box_line(gradient("NEEDBUX AUTO CLAIM", 51, 213));
echo box_line(fg(240)."─────── SOUU ENGINE ───────".RST);
echo box_div();
echo box_line(fg(213).BOLD."PILIH COIN".RST);
echo box_line(fg(51)."  ".RST.fg(226)."1.".RST.fg(46)." DOGE".RST);
echo box_line(fg(240)."".RST);
echo box_line(fg(240)."  ketik 1 lalu enter".RST);
echo fg(51)."╚".str_repeat("═",62)."╝".RST."\n";
echo "\n   ".gradient("PILIH > ", 46, 226).fg(226);
$pilihan = trim(fgets(STDIN));
echo reset."\n";

if ($pilihan === '1') {
    push_log("mode: DOGE (loop forever)", 'g');
    banner();
    while (true) {
        claimCoin('doge', $a, $b, $apikey, $email, false);
        $GLOBALS['_fails'] = 0;
        sleep(2);
    }
} else {
    echo merah . "[!] Pilihan tidak valid! ketik 1\n";
    sleep(3);
    exit;
}
