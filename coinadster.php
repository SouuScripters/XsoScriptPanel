#!/usr/bin/env php
<?php
/**
 * ═══════════════════════════════════════════════════════════════
 *  COINADSTER.com Auto Claim Bot v1.3 (Clean UI)
 *  - Auto login via email + password
 *  - Turnstile / hCaptcha solver via Waryono
 *  - Faucet claim with math anti-bot (sc_a + sc_b + 1234)
 *  - UI style: LimeFaucet clean box
 *  - Runtime: UNLIMITED (ikut limit server)
 *  - Human delay: 3-7s di tiap step penting
 *  - FIX: countdown log replace (gak spam)
 *  - FIX: max_failures = 2
 *  By Power @MoneyMaker_w
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
//  HUMAN DELAY HELPER
// ═══════════════════════════════════════════════════════════════
function human_delay(int $extra_sec = 0): void {
    $base = rand(3, 7);
    $total = $base + $extra_sec;
    usleep($total * 1000000);
}

// ═══════════════════════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════════════════════
$STATE = [
    'user'          => 'Unknown',
    'email'         => '-',
    'bits'          => '0',
    'credits'       => '0',
    'claims'        => 0,
    'rewards'       => 0,
    'failures'      => 0,
    'max_failures'  => 2,          // ← diubah dari 5 jadi 2
    'solve_attempt' => 0,
    'max_solve'     => 3,
    'runtime_start' => time(),
    'max_runtime'   => 0,
    'logs'          => [],
    'faucet_status' => 'checking',
    'captcha_type'  => '-',
];

// ═══════════════════════════════════════════════════════════════
//  LOG HELPER — support replace last
// ═══════════════════════════════════════════════════════════════
function _log_tags(): array {
    return [
        'OK'=>GRN."● OK    ".RST, 'ERR'=>RED."● ERR   ".RST, 'WARN'=>YEL."● WARN  ".RST,
        'INFO'=>GRY."● INFO  ".RST, 'CLAIM'=>MAG."◉ CLAIM ".RST, 'SOLVE'=>CYN."◉ SOLVER".RST,
        'VERIFY'=>VIO."◉ VERIFY".RST, 'CAP'=>YEL."◉ CAPTCHA".RST, 'WAIT'=>ORG."◉ WAIT  ".RST,
        'AUTH'=>GRN."● AUTH  ".RST, 'LOGIN'=>CYN."◉ LOGIN ".RST, 'DEBUG'=>GRY."● DEBUG ".RST,
        'HUMAN'=>ORG."● HUMAN ".RST,
    ];
}

/**
 * Push log baru (default).
 * Kalau $replace_last = true DAN log terakhir punya tag WAIT, replace log terakhir.
 * Ini biar countdown gak spam banyak baris.
 */
function slog(string $msg, string $level = 'INFO', bool $replace_last = false): void {
    global $STATE;
    $ts = date('H:i:s');
    $tags = _log_tags();
    $tag = $tags[strtoupper($level)] ?? $tags['INFO'];
    $new = GRY."[{$ts}] ".RST.$tag." ".WHT.$msg.RST;

    if ($replace_last && !empty($STATE['logs'])) {
        $idx = count($STATE['logs']) - 1;
        // Cek apakah log terakhir punya tag WAIT (biar cuma replace WAIT yg sama)
        if (strpos($STATE['logs'][$idx], $tags['WAIT']) !== false
            || strpos($STATE['logs'][$idx], $tags['HUMAN']) !== false) {
            $STATE['logs'][$idx] = $new;
            return;
        }
    }

    $STATE['logs'][] = $new;
    if (count($STATE['logs'])>7) array_shift($STATE['logs']);
}

function fmt_dur(int $s): string {
    return sprintf('%02d:%02d:%02d', floor($s/3600), floor(($s%3600)/60), $s%60);
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
    echo $line(BOLD.WHT."COINADSTER AUTO CLAIM".RST)."\n";
    echo $line(DIM."─────── SOUU ENGINE ───────".RST)."\n";
    echo $mid."\n";

    $hs_color=GRN; $hs_label='ONLINE';
    if ($STATE['faucet_status']==='suspect')      { $hs_color=YEL; $hs_label='SUSPECT'; }
    elseif ($STATE['faucet_status']==='dead')     { $hs_color=RED; $hs_label='DEAD'; }
    elseif ($STATE['faucet_status']==='checking') { $hs_color=GRY; $hs_label='CHECKING'; }
    elseif ($STATE['faucet_status']==='cooldown') { $hs_color=ORG; $hs_label='COOLDOWN'; }

    echo $line(VIO."FAUCET".RST)."\n";
    echo $line("├─ Status   : ".$hs_color.$hs_label.RST)."\n";
    echo $line("└─ Site     : ".CYN."coinadster.com".RST)."\n";
    echo $mid."\n";

    echo $line(VIO."CAPTCHA".RST)."\n";
    echo $line("├─ Type     : ".YEL.strtoupper($STATE['captcha_type']).RST)."\n";
    echo $line("├─ Solver   : ".CYN."waryono".RST)."\n";
    echo $line("└─ Attempt  : ".($STATE['solve_attempt']>0
            ? YEL.$STATE['solve_attempt']."/".$STATE['max_solve'].RST
            : DIM."-".RST))."\n";
    echo $mid."\n";

    echo $line(VIO."ACCOUNT".RST)."\n";
    echo $line("├─ User     : ".CYN.$STATE['user'].RST)."\n";
    echo $line("├─ Email    : ".$STATE['email'])."\n";
    echo $line("├─ Bits     : ".YEL.$STATE['bits'].RST)."\n";
    echo $line("└─ Credits  : ".MAG.$STATE['credits'].RST)."\n";
    echo $mid."\n";

    $run=time()-$STATE['runtime_start'];
    $max_run_label = ($STATE['max_runtime'] > 0)
        ? DIM.fmt_dur($STATE['max_runtime']).RST
        : DIM."UNLIMITED".RST;

    echo $line(VIO."SYSTEM".RST)."\n";
    echo $line("├─ Claims   : ".GRN.$STATE['claims'].RST)."\n";
    echo $line("├─ Rewards  : ".GRN."+".$STATE['rewards']." bits".RST)."\n";
    echo $line("├─ Failures : ".RED.$STATE['failures'].RST." / ".$STATE['max_failures'])."\n";
    echo $line("└─ Runtime  : ".CYN.fmt_dur($run).RST." / ".$max_run_label)."\n";
    echo $mid."\n";

    $logs=$STATE['logs'];
    if (empty($logs)) {
        echo $line(DIM."─ no activity yet ─".RST)."\n";
    } else {
        foreach ($logs as $l) echo $line($l)."\n";
    }
    echo $bot."\n";
    echo "\n   ".GRN."BOT RUNNING".RST." ".DIM."•".RST." ".CYN.date('H:i:s').RST."\n";
    echo "   ".DIM."By Power @MoneyMaker_w • CoinAdster Edition".RST."\n\n";
}

function clear_render(): void {
    if (PHP_OS_FAMILY==='Windows') pclose(popen('cls','w'));
    else system('clear');
    render();
}

// ═══════════════════════════════════════════════════════════════
//  CONST
// ═══════════════════════════════════════════════════════════════
const script_name = "coinadster.com";
const host        = "https://coinadster.com";
const api_in      = "https://api.waryono.my.id/in.php";
const api_res     = "https://api.waryono.my.id/res.php";

const TURNSTILE_KEY = "0x4AAAAAAAV-tgu1vT_isJ5Q";
const HCAPTCHA_KEY  = "16c8fe32-6d50-4570-8f38-28748bacc5a8";

const POLL_INTERVAL = 3;
const POLL_TIMEOUT  = 180;
const DEBUG         = true;

$CONFIG_FILE  = __DIR__.'/config.json';
$COOKIE_FILE  = __DIR__.'/cookies.txt';

function load_config(): ?array {
    global $CONFIG_FILE;
    if (!file_exists($CONFIG_FILE)) return null;
    $c = json_decode((string) file_get_contents($CONFIG_FILE), true);
    if (!is_array($c) || empty($c['email'])) return null;
    $c['apikey']   = $c['apikey']   ?? '';
    $c['password'] = $c['password'] ?? '';
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
function curl_request($url, $method = 'GET', $data = [], $headers = [], $nofollow = false) {
    global $COOKIE_FILE;
    $ch = curl_init();
    $opts = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HEADER         => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_SSL_VERIFYPEER => 0,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CONNECTTIMEOUT => 30,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_COOKIEFILE     => $COOKIE_FILE,
        CURLOPT_COOKIEJAR      => $COOKIE_FILE,
        CURLOPT_ENCODING       => '',
        CURLOPT_USERAGENT      => 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'
    ];
    if (!$nofollow) $opts[CURLOPT_FOLLOWLOCATION] = true;
    if (strtoupper($method) === 'POST') {
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = $data;
    }
    curl_setopt_array($ch, $opts);
    $resp = curl_exec($ch);
    curl_close($ch);
    return $resp ?: "";
}

/* ================= HEADERS ================= */
function headers_html($referer = null) {
    $h = [
        'Host: '.script_name,
        'Connection: keep-alive',
        'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile: ?1',
        'sec-ch-ua-platform: "Android"',
        'Upgrade-Insecure-Requests: 1',
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Sec-Fetch-Site: same-origin',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-User: ?1',
        'Sec-Fetch-Dest: document',
        'Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    ];
    if ($referer) $h[] = 'Referer: '.$referer;
    return $h;
}
function headers_form_post($url_referer) {
    return [
        'Host: '.script_name,
        'Connection: keep-alive',
        'Content-Type: application/x-www-form-urlencoded',
        'Cache-Control: max-age=0',
        'Origin: '.host,
        'Upgrade-Insecure-Requests: 1',
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Sec-Fetch-Site: same-origin',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-User: ?1',
        'Sec-Fetch-Dest: document',
        'Referer: '.$url_referer,
        'Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile: ?1',
        'sec-ch-ua-platform: "Android"'
    ];
}
function headers_ajax($referer = null) {
    $h = [
        'Host: '.script_name,
        'Accept: application/json, text/javascript, */*; q=0.01',
        'Accept-Language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Content-Type: application/x-www-form-urlencoded; charset=UTF-8',
        'Origin: '.host,
        'Sec-Fetch-Dest: empty',
        'Sec-Fetch-Mode: cors',
        'Sec-Fetch-Site: same-origin',
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'X-Requested-With: XMLHttpRequest',
        'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile: ?1',
        'sec-ch-ua-platform: "Android"'
    ];
    $h[] = 'Referer: '.($referer ?: host.'/');
    return $h;
}

// ═══════════════════════════════════════════════════════════════
//  WARYONO SOLVER
// ═══════════════════════════════════════════════════════════════
function solve_captcha($apikey, $sitekey, $method = 'turnstile', $domain = host) {
    $body = json_encode([
        "apikey"  => $apikey,
        "methods" => $method,
        "domain"  => $domain,
        "sitekey" => $sitekey,
        "json"    => 1
    ]);
    $req = curl_request(api_in, "POST", $body, ["Content-Type: application/json"]);

    if (strpos($req, "ERROR_") !== false) {
        slog("captcha submit: ".trim($req), 'ERR');
        return $req;
    }

    $json = json_decode($req, true);
    $id   = $json["request"] ?? '';
    if (!$id) {
        slog("captcha: tidak dapat ID", 'ERR');
        if (DEBUG) {
            $raw = trim($req);
            if (strlen($raw) > 150) $raw = substr($raw, 0, 150)."...";
            slog("waryono raw: ".$raw, 'DEBUG');
        }
        return "ERROR_UNKNOWN";
    }

    $tries = 0;
    while ($tries < 40) {
        $tries++;
        sleep(POLL_INTERVAL);
        $url = api_res."?apikey=".$apikey."&action=get&id=".$id."&json=1";
        $res = curl_request($url, "GET", []);

        if (strpos($res, "CAPCHA_NOT_READY") !== false) continue;
        if (strpos($res, "ERROR_") !== false) {
            slog("captcha poll: ".trim($res), 'ERR');
            return $res;
        }

        $json = json_decode($res, true);
        $tok  = $json["request"] ?? '';
        if ($tok) return $tok;
    }
    return "ERROR_TIMEOUT";
}

// ═══════════════════════════════════════════════════════════════
//  LOGIN
// ═══════════════════════════════════════════════════════════════
function is_logged_in($html) {
    return (strpos($html, 'cx-head') !== false
         || strpos($html, 'id="bitBal"') !== false
         || strpos($html, '?logout') !== false);
}

function do_login($apikey, $email, $password) {
    slog("login required...", 'LOGIN');
    clear_render();

    $attempt = 0;
    while ($attempt < 5) {
        $attempt++;
        slog("login attempt $attempt/5...", 'LOGIN');
        clear_render();

        slog("human delay sebelum GET home...", 'HUMAN');
        clear_render();
        human_delay();

        $home = curl_request(host."/", "GET", [], headers_html());
        if (!preg_match('/id="tbkjja65ot7"\s+value="([^"]+)"/', $home, $m)) {
            if (!preg_match('/id="[a-z0-9]+"\s+value="([a-f0-9]{60,})"/', $home, $m)) {
                slog("gagal parse CSRF login", 'ERR');
                clear_render();
                sleep(3); continue;
            }
        }
        $token = $m[1];

        slog("human delay sebelum solve captcha...", 'HUMAN');
        clear_render();
        human_delay();

        $capToken = solve_captcha($apikey, TURNSTILE_KEY, 'turnstile');
        if (strpos($capToken, "ERROR_") !== false) {
            slog("captcha gagal ($capToken), retry...", 'WARN');
            clear_render();
            sleep(3); continue;
        }

        slog("human delay sebelum submit login...", 'HUMAN');
        clear_render();
        human_delay();

        $data = http_build_query([
            "a"         => "login",
            "token"     => $token,
            "username"  => $email,
            "password"  => $password,
            "remember"  => "on",
            "recaptcha" => $capToken,
            "cap"       => "turnstile"
        ]);
        $resp = curl_request(host."/system/ajax.php", "POST", $data, headers_ajax(host."/"));
        $j = json_decode(trim($resp), true);

        if (!is_array($j)) {
            slog("response login bukan JSON", 'ERR');
            clear_render();
            sleep(5); continue;
        }

        $status = $j['status'] ?? -1;
        $msg    = strip_tags($j['msg'] ?? $j['message'] ?? '');

        if ($status == 1 || ($j['loggedin'] ?? 0) == 1) {
            slog("login sukses", 'OK');
            clear_render();
            return true;
        }
        if ($status == 2) {
            slog("akun pakai 2FA email. Matikan 2FA dulu di /account.html", 'ERR');
            clear_render();
            exit;
        }
        slog("login gagal: ".trim($msg), 'ERR');
        clear_render();
        if (stripos($msg, 'password') !== false || stripos($msg, 'wrong') !== false) {
            @unlink($GLOBALS['COOKIE_FILE']);
            @unlink($GLOBALS['CONFIG_FILE']);
            exit;
        }
        sleep(5);
    }
    slog("login gagal setelah 5 percobaan", 'ERR');
    clear_render();
    exit;
}

// ═══════════════════════════════════════════════════════════════
//  BALANCE
// ═══════════════════════════════════════════════════════════════
function get_balance() {
    $home = curl_request(host."/", "GET", [], headers_html());
    $bits = null; $credits = null; $ajax_token = null;

    if (preg_match("/var token = '([a-f0-9]+)';/", $home, $m)) $ajax_token = $m[1];
    if (preg_match('~id="sbBalanceBits">([^<]+)</span>~', $home, $m)) $bits = trim($m[1]);
    if (preg_match('~id="credBal">([^<]+)</span>~', $home, $m)) $credits = trim($m[1]);

    return [
        'bits'    => $bits,
        'credits' => $credits,
        'token'   => $ajax_token,
        'html'    => $home
    ];
}

// ═══════════════════════════════════════════════════════════════
//  FAUCET CLAIM
// ═══════════════════════════════════════════════════════════════
function do_faucet_claim($apikey) {
    global $STATE;
    slog("buka /faucet.html...", 'INFO');
    clear_render();

    slog("human delay sebelum buka faucet...", 'HUMAN');
    clear_render();
    human_delay();

    $html = curl_request(host."/faucet.html", "GET", [], headers_html(host."/"));

    if (!is_logged_in($html)) {
        slog("session expired, re-login...", 'WARN');
        clear_render();
        return 'RELOGIN';
    }

    if (strpos($html, 'countdown_timer') !== false && strpos($html, 'id="claimForm"') === false) {
        preg_match('/var secondsLeft = (\d+);/', $html, $cd);
        return ['status' => 'cooldown', 'wait' => intval($cd[1] ?? 300)];
    }

    if (!preg_match('/name="csrf_token"\s+value="([^"]+)"/', $html, $m)) return 'PARSE_FAIL:csrf_token';
    $csrf_token = $m[1];
    if (!preg_match('/name="sc_ts"\s+value="([^"]+)"/', $html, $m)) return 'PARSE_FAIL:sc_ts';
    $sc_ts = $m[1];
    if (!preg_match('/name="sc_a"\s+id="sc_a_val"\s+value="(\d+)"/', $html, $m)) return 'PARSE_FAIL:sc_a';
    $sc_a = intval($m[1]);
    if (!preg_match('/name="sc_b"\s+id="sc_b_val"\s+value="(\d+)"/', $html, $m)) return 'PARSE_FAIL:sc_b';
    $sc_b = intval($m[1]);
    if (!preg_match('/name="sc_sig"\s+value="([^"]+)"/', $html, $m)) return 'PARSE_FAIL:sc_sig';
    $sc_sig = $m[1];

    $sc_res = $sc_a + $sc_b + 1234;
    slog("math: $sc_a + $sc_b + 1234 = $sc_res", 'INFO');
    clear_render();

    $cap_type = null;
    $cap_sitekey = null;

    if (strpos($html, 'class="h-captcha"') !== false) {
        $cap_type = 'hcaptcha';
        $cap_sitekey = HCAPTCHA_KEY;
        slog("form minta hCaptcha", 'WARN');
    } elseif (strpos($html, 'class="cf-turnstile"') !== false) {
        $cap_type = 'turnstile';
        $cap_sitekey = TURNSTILE_KEY;
        slog("form minta Turnstile", 'WARN');
    } else {
        slog("form tidak minta captcha", 'INFO');
        $cap_type = 'none';
    }
    $STATE['captcha_type'] = $cap_type ?: '-';
    clear_render();

    slog("human delay (thinking)...", 'HUMAN');
    clear_render();
    human_delay();

    $post_arr = [
        "csrf_token"    => $csrf_token,
        "sc_ts"         => $sc_ts,
        "website_hp"    => "",
        "sc_a"          => $sc_a,
        "sc_b"          => $sc_b,
        "sc_sig"        => $sc_sig,
        "sc_res"        => $sc_res,
        "claim_submit"  => ""
    ];

    if ($cap_type && $cap_sitekey) {
        slog("solve $cap_type via Waryono...", 'SOLVE');
        clear_render();
        $token = solve_captcha($apikey, $cap_sitekey, $cap_type);
        if (strpos($token, "ERROR_") !== false) {
            slog("captcha gagal: $token", 'ERR');
            clear_render();
            return ['status' => 'failed', 'msg' => "captcha gagal: $token"];
        }
        $post_arr['g-recaptcha-response'] = $token;
        $post_arr['h-captcha-response']   = $token;
        if ($cap_type === 'turnstile') {
            $post_arr['cf-turnstile-response'] = $token;
        }
        slog("captcha token didapat", 'OK');
        clear_render();

        slog("human delay sebelum submit claim...", 'HUMAN');
        clear_render();
        human_delay();
    }

    $post = http_build_query($post_arr);
    $resp = curl_request(
        host."/faucet.html",
        "POST",
        $post,
        headers_form_post(host."/faucet.html"),
        true
    );

    if (preg_match("~<div class='alert alert-success'>([^<]+)</div>~", $resp, $ok)) {
        return ['status' => 'success', 'msg' => trim($ok[1])];
    }
    if (preg_match("~<div class='alert alert-danger'>([^<]+)</div>~", $resp, $err)) {
        $msg = trim(strip_tags($err[1]));

        if (stripos($msg, 'too fast') !== false) {
            return ['status' => 'too_fast', 'msg' => $msg];
        }
        if (stripos($msg, 'session expired') !== false) {
            return 'RELOGIN';
        }
        if (stripos($msg, 'wait') !== false) {
            preg_match('/(\d+)\s*(second|minute|hour)/i', $msg, $mm);
            $w = intval($mm[1] ?? 300);
            if (isset($mm[2])) {
                if (stripos($mm[2], 'minute') !== false) $w *= 60;
                if (stripos($mm[2], 'hour')   !== false) $w *= 3600;
            }
            return ['status' => 'cooldown', 'wait' => $w, 'msg' => $msg];
        }
        if (stripos($msg, 'limit') !== false || stripos($msg, 'daily') !== false) {
            return ['status' => 'server_limit', 'msg' => $msg];
        }
        if (stripos($msg, 'banned') !== false || stripos($msg, 'suspend') !== false) {
            return ['status' => 'banned', 'msg' => $msg];
        }
        return ['status' => 'failed', 'msg' => $msg];
    }
    if (preg_match("~<div class='alert alert-warning'>([^<]+)</div>~", $resp, $warn)) {
        return ['status' => 'failed', 'msg' => trim(strip_tags($warn[1]))];
    }
    if (strpos($resp, 'countdown_timer') !== false && strpos($resp, 'id="claimForm"') === false) {
        preg_match('/var secondsLeft = (\d+);/', $resp, $cd);
        return ['status' => 'cooldown', 'wait' => intval($cd[1] ?? 300)];
    }
    if (strpos($resp, 'id="claimForm"') !== false) {
        if (preg_match('~<div id="messageArea">(.*?)</div>~s', $resp, $ma)) {
            $msg = trim(strip_tags($ma[1]));
            if ($msg) return ['status' => 'failed', 'msg' => $msg];
        }
        return ['status' => 'failed', 'msg' => 'form muncul kembali'];
    }

    $preview = substr(trim($resp), 0, 800);
    return [
        'status'  => 'unknown',
        'msg'     => 'response tidak dikenali',
        'preview' => $preview,
        'len'     => strlen($resp)
    ];
}

// ═══════════════════════════════════════════════════════════════
//  SETUP WIZARD
// ═══════════════════════════════════════════════════════════════
function setup(): array {
    echo "\n".CYN."═══ COINADSTER SETUP ═══".RST."\n\n";
    echo DIM."Login pakai email + password + API key Waryono.\n\n".RST;

    $email = '';
    while (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $email = read_line(YEL."Email: ".RST);
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            echo RED."  ✗ Email gak valid\n".RST;
        }
    }
    $password = read_line(YEL."Password: ".RST);
    $apikey   = read_line(YEL."Waryono API key: ".RST);
    return ['email' => $email, 'password' => $password, 'apikey' => $apikey];
}

// ═══════════════════════════════════════════════════════════════
//  HELPER: cooldown live countdown (replace log, no spam)
// ═══════════════════════════════════════════════════════════════
function live_wait(int $seconds, string $label = "cooldown", string $extra = ""): void {
    global $STATE;
    if ($seconds < 1) return;
    $STATE['faucet_status'] = 'cooldown';

    /* Push log WAIT pertama (biar keliatan) */
    slog("{$label} ".fmt_dur($seconds).($extra ? " ({$extra})" : ""), 'WAIT');
    clear_render();

    $start = time();
    while ((time() - $start) < $seconds) {
        $left = $seconds - (time() - $start);
        /* replace_last = true → cuma update 1 baris WAIT */
        slog("{$label} ".fmt_dur($left).($extra ? " ({$extra})" : ""), 'WAIT', true);
        clear_render();
        sleep(1);
    }
    $STATE['faucet_status'] = 'ok';
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
save_config($config);

$apikey   = $config['apikey'];
$email    = $config['email'];
$password = $config['password'];

$STATE['email'] = $email;

/* Initial login check */
$state = get_balance();
if (!$state['html'] || !is_logged_in($state['html'])) {
    do_login($apikey, $email, $password);
    sleep(2);
    $state = get_balance();
    if (!is_logged_in($state['html'])) {
        slog("login selesai tapi dashboard tidak bisa diakses. Keluar.", 'ERR');
        clear_render();
        exit;
    }
}

preg_match('~<div class="cx-uname">([^<]+)</div>~', $state['html'], $un);
$STATE['user']    = trim($un[1] ?? 'unknown');
$STATE['bits']    = $state['bits']    ?? '0';
$STATE['credits'] = $state['credits'] ?? '0';
$STATE['faucet_status'] = 'ok';

slog("session OK as {$STATE['user']}", 'AUTH');
clear_render();

/* ================= LOOP ================= */
$fail_streak = 0;

while (true) {
    if ($STATE['max_runtime'] > 0 && (time() - $STATE['runtime_start']) >= $STATE['max_runtime']) {
        slog("Max runtime reached", 'WARN'); clear_render(); break;
    }
    if ($STATE['failures'] >= $STATE['max_failures']) {
        slog("Max failures reached ({$STATE['failures']})", 'ERR'); clear_render(); break;
    }

    $STATE['solve_attempt'] = 0;
    $res = do_faucet_claim($apikey);

    if ($res === 'RELOGIN') {
        @unlink($GLOBALS['COOKIE_FILE']);
        sleep(2);
        do_login($apikey, $email, $password);
        sleep(3);
        continue;
    }
    if (is_string($res) && strpos($res, 'PARSE_FAIL') === 0) {
        $fail_streak++;
        $STATE['failures']++;
        slog("parse form gagal: $res (streak: $fail_streak)", 'ERR');
        clear_render();
        if ($fail_streak >= 2) {
            slog("2x gagal parse, re-login...", 'WARN');
            clear_render();
            @unlink($GLOBALS['COOKIE_FILE']);
            sleep(2);
            do_login($apikey, $email, $password);
            $fail_streak = 0;
        }
        sleep(10);
        continue;
    }
    if (!is_array($res)) {
        $STATE['failures']++;
        slog("response tidak valid", 'ERR');
        clear_render();
        sleep(10);
        continue;
    }

    switch ($res['status']) {
        case 'success':
            $fail_streak = 0;
            $STATE['failures'] = 0;
            $STATE['claims']++;
            sleep(1);
            $state = get_balance();
            $STATE['bits']    = $state['bits']    ?? $STATE['bits'];
            $STATE['credits'] = $state['credits'] ?? $STATE['credits'];

            slog($res['msg']." | bits: ".$STATE['bits'], 'OK');
            clear_render();

            $cd = 300;
            $info_html = curl_request(host."/", "GET", [], headers_html());
            if (preg_match('/var secondsLeft = (\d+);/', $info_html, $im)) {
                $server_cd = intval($im[1]);
                if ($server_cd > 0) $cd = $server_cd;
            }
            if ($cd < 30) $cd = 30;
            live_wait($cd, "next claim");
            break;

        case 'too_fast':
            slog("server bilang terlalu cepat, retry 5s...", 'WARN');
            clear_render();
            sleep(5);
            $retry = do_faucet_claim($apikey);
            if (is_array($retry) && $retry['status'] === 'success') {
                $fail_streak = 0;
                $STATE['claims']++;
                sleep(1);
                $state = get_balance();
                $STATE['bits']    = $state['bits']    ?? $STATE['bits'];
                $STATE['credits'] = $state['credits'] ?? $STATE['credits'];
                slog($retry['msg']." | bits: ".$STATE['bits'], 'OK');
                clear_render();
                live_wait(300, "next claim");
            } else {
                slog("retry gagal, tunggu 30s...", 'WARN');
                clear_render();
                sleep(30);
            }
            break;

        case 'cooldown':
            $msg = $res['msg'] ?? '';
            $wait = (int)($res['wait'] ?? 300);
            live_wait($wait, "cooldown", $msg);
            break;

        case 'server_limit':
            slog("SERVER LIMIT: ".$res['msg'], 'WARN');
            clear_render();
            $STATE['faucet_status'] = 'suspect';
            live_wait(1800, "server limit cooldown");
            @unlink($GLOBALS['COOKIE_FILE']);
            sleep(2);
            do_login($apikey, $email, $password);
            $fail_streak = 0;
            break;

        case 'banned':
            slog("BANNED/SUSPENDED: ".$res['msg'], 'ERR');
            $STATE['faucet_status'] = 'dead';
            clear_render();
            slog("Bot stop — akun kena banned/suspend.", 'ERR');
            clear_render();
            exit;

        case 'failed':
            $STATE['failures']++;
            $fail_streak++;
            slog("claim gagal: ".($res['msg'] ?? ''), 'ERR');
            clear_render();
            if ($fail_streak >= 2) {
                slog("2x gagal, re-login...", 'WARN');
                clear_render();
                @unlink($GLOBALS['COOKIE_FILE']);
                sleep(2);
                do_login($apikey, $email, $password);
                $fail_streak = 0;
            }
            sleep(10);
            break;

        case 'unknown':
        default:
            $STATE['failures']++;
            $fail_streak++;
            slog("response tidak dikenali (".($res['len'] ?? 0)." bytes)", 'WARN');
            if (DEBUG) {
                $prev = substr($res['preview'] ?? '(kosong)', 0, 80);
                slog("preview: ".$prev, 'DEBUG');
            }
            clear_render();
            if ($fail_streak >= 2) {
                slog("2x unknown, re-login...", 'WARN');
                clear_render();
                @unlink($GLOBALS['COOKIE_FILE']);
                sleep(2);
                do_login($apikey, $email, $password);
                $fail_streak = 0;
            }
            sleep(10);
            break;
    }
}

clear_render();
echo "\n".CYN."  ◉ Bot stopped.\n".RST;
echo DIM."  Claims: {$STATE['claims']}  |  Failures: {$STATE['failures']}  |  Bits: {$STATE['bits']}\n\n".RST;
