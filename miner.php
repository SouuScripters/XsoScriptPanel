<?php

error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$configFile = "lightminerconfig.json";

if (!is_dir('session')) {
    mkdir('session', 0777, true);
}

const hitam  = "\033[0;30m";
const merah  = "\033[0;31m";
const hijau  = "\033[0;32m";
const kuning = "\033[0;33m";
const biru   = "\033[0;34m";
const cyan   = "\033[0;36m";
const putih  = "\033[0;37m";
const reset  = "\033[0m";

const api_url   = "https://lightningminer.com";
const SITEKEY   = "764c22e4-3102-4218-8130-1c848c282506";
const SOLVER_IN = "https://api.waryono.my.id/in.php";
const SOLVER_RES= "https://api.waryono.my.id/res.php";

$cookieFile = "session/lightningminer_cookies.txt";

function clear() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function maskEmail($email) {
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) return $email;
    list($user, $domain) = explode('@', $email);
    $len = strlen($user);
    if ($len <= 4) return substr($user, 0, 1) . '****' . '@' . $domain;
    return substr($user, 0, 2) . '****' . substr($user, -2) . '@' . $domain;
}

function timer($seconds, $prefix = "[!] please wait") {
    $wait_time = (int)$seconds;
    if ($wait_time < 1) return;
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
            echo "\r\033[K";
            echo putih . $prefix . hijau . " $time_formatted " . putih . $spinner;
            usleep($frame_delay * 1000000);
            $current_frame = ($current_frame + 1) % $frame_count;
            if ((microtime(true) - $start_time) >= 1) break;
        }
        $wait_time--;
    }
    echo "\r\033[K";
}

function saveConfig($configFile, $configData) {
    file_put_contents($configFile, json_encode($configData, JSON_PRETTY_PRINT));
}

function getConfig($configFile) {
    clear();
    $data = [];
    if (file_exists($configFile)) $data = json_decode(file_get_contents($configFile), true) ?? [];

    $apikey   = $data['apikey'] ?? '';
    $email    = $data['email'] ?? '';
    $password = $data['password'] ?? '';

    if (empty($apikey)) {
        echo putih . "API Key Waryono    : " . kuning;
        $apikey = trim(fgets(STDIN));
    }
    if (empty($email)) {
        echo putih . "Email              : " . kuning;
        $email = trim(fgets(STDIN));
    }
    if (empty($password)) {
        echo putih . "Password           : " . kuning;
        $password = trim(fgets(STDIN));
    }

    $configData = [
        "apikey"   => $apikey,
        "email"    => $email,
        "password" => $password
    ];

    saveConfig($configFile, $configData);
    return $configData;
}

function request($url, $method = 'GET', $payload = null, $headers = []) {
    global $cookieFile;
    $ch = curl_init();
    $final = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_SSL_VERIFYHOST => 1,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CONNECTTIMEOUT => 30,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_COOKIEFILE     => $cookieFile,
        CURLOPT_COOKIEJAR      => $cookieFile,
        CURLOPT_ENCODING       => ''
    ];
    if (strtoupper($method) === 'POST') {
        $final[CURLOPT_POST] = true;
        $final[CURLOPT_POSTFIELDS] = is_array($payload) ? json_encode($payload) : $payload;
    }
    curl_setopt_array($ch, $final);
    $response = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    return ["body" => $response, "code" => $code];
}

function curl_solver($url, $method = 'GET', $data = [], $headers = []) {
    $ch = curl_init();
    $final_headers = [];
    foreach ($headers as $header) $final_headers[] = $header;
    $options = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_CONNECTTIMEOUT => 30,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_ENCODING       => ''
    ];
    if ($headers) $options[CURLOPT_HTTPHEADER] = $final_headers;
    if (strtoupper($method) === 'POST') {
        $options[CURLOPT_POST] = true;
        $options[CURLOPT_POSTFIELDS] = $data;
    }
    curl_setopt_array($ch, $options);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

function auth_headers() {
    return [
        'sec-ch-ua: "Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        'sec-ch-ua-platform: "Android"',
        'sec-ch-ua-mobile: ?1',
        'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'content-type: application/json',
        'accept: */*',
        'origin: https://lightningminer.com',
        'sec-fetch-site: same-origin',
        'sec-fetch-mode: cors',
        'sec-fetch-dest: empty',
        'referer: https://lightningminer.com/faucet',
        'accept-language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    ];
}

// ========== SOLVER WARYONO (HCAPTCHA) ==========
function solve_hcaptcha($apikey, $sitekey) {
    $headers = ["Content-Type: application/json"];
    $body = json_encode([
        "apikey"  => $apikey,
        "methods" => "hcaptcha",
        "domain"  => "https://lightningminer.com",
        "sitekey" => $sitekey,
        "json"    => 1
    ]);
    $request = curl_solver(SOLVER_IN, "POST", $body, $headers);

    $task = json_decode($request, true);
    if (($task['status'] ?? 0) != 1) return false;

    $taskId = $task['request'];

    reload:
    timer(5, "  hcaptcha (waryono)... ");

    $url = SOLVER_RES . "?apikey=" . urlencode($apikey) . "&action=get&id=" . urlencode($taskId) . "&json=1";
    $result = curl_solver($url);

    $res = json_decode($result, true);
    if (($res['status'] ?? 0) == 1) return $res['request'];

    $result_msg = $res['request'] ?? $result;
    if ($result_msg === "CAPCHA_NOT_READY") goto reload;

    return false;
}

// ========== LOGIN ==========
function do_login($email, $password) {
    $res = request(api_url . "/api/login", "POST", [
        "email" => $email,
        "password" => $password
    ], auth_headers());

    $json = json_decode($res['body'], true);
    if (!empty($json['ok']) && !empty($json['user'])) {
        return $json;
    }
    return false;
}

// ========== CEK COOLDOWN ==========
function get_faucet_cooldown($login_data) {
    $user = $login_data['user'];
    $lastFaucet = intval($user['lastFaucetAt'] ?? 0);
    $faucetCd = intval($login_data['faucetCooldownSeconds'] ?? 300);
    $nextFaucet = $lastFaucet + ($faucetCd * 1000);
    $wait = max(0, floor(($nextFaucet - (time() * 1000)) / 1000));
    return $wait;
}

// ========== RUN FAUCET ==========
function run_faucet($apikey, $email, $password) {
    while (true) {
        $fresh = do_login($email, $password);
        if (!$fresh) {
            sleep(5);
            continue;
        }

        $waitFaucet = get_faucet_cooldown($fresh);
        if ($waitFaucet > 0) {
            return $waitFaucet;
        }

        $ch = request(api_url . "/api/faucet/challenge", "GET", null, auth_headers());
        $ch_json = json_decode($ch['body'], true);

        if (empty($ch_json['ok']) || empty($ch_json['claimToken'])) {
            sleep(3);
            continue;
        }

        $claimToken = $ch_json['claimToken'];
        $minWait = intval($ch_json['minWaitSeconds'] ?? 0);
        $issuedAt = intval($ch_json['issuedAt'] ?? 0);

        if ($minWait > 0) timer($minWait, "  tunggu readyAt...");

        $captchaToken = null;
        while ($captchaToken === null) {
            $captchaToken = solve_hcaptcha($apikey, SITEKEY);
            if ($captchaToken) break;
            sleep(3);
        }

        $elapsed = ($issuedAt > 0) ? (time() * 1000 - $issuedAt + $minWait * 1000) : ($minWait * 1000 + 2000);
        if ($elapsed < 1000) $elapsed = 15876;
        $interaction = [
            "elapsedMs"       => $elapsed,
            "focusMs"         => $elapsed - 600,
            "pointerDowns"    => rand(1, 3),
            "pointerUps"      => rand(1, 3),
            "pointerMoves"    => rand(8, 20),
            "touchStarts"     => rand(0, 2),
            "keydowns"        => 0,
            "scrolls"         => rand(50, 150),
            "untrustedEvents" => 0,
            "visible"         => true
        ];

        $claim = request(api_url . "/api/faucet", "POST", [
            "captchaToken" => $captchaToken,
            "claimToken"   => $claimToken,
            "interaction"  => $interaction
        ], auth_headers());

        $claim_json = json_decode($claim['body'], true);

        if (!empty($claim_json['ok'])) {
            $user = $claim_json['user'];
            $reward = $claim_json['claimedCoins'] ?? 5;
            echo hijau . "[FAUCET] ✓ +" . $reward . " coins";
            echo putih . " | balance: " . cyan . number_format($user['coins']);
            echo putih . " | hashpower: " . cyan . number_format($user['miningPower']) . " H/s\n";

            $nextFaucet = intval($user['lastFaucetAt'] ?? 0) + (300 * 1000);
            $cd = max(0, floor(($nextFaucet - (time() * 1000)) / 1000));
            return $cd > 0 ? $cd : 300;
        }

        $fresh = do_login($email, $password);
        if ($fresh) {
            $waitFaucet = get_faucet_cooldown($fresh);
            if ($waitFaucet > 0) return $waitFaucet;
        }

        sleep(3);
    }
}

// ============ MAIN ============
clear();
echo putih . "===============================================\n";
echo kuning . "     LIGHTNINGMINER.COM BOT - HCAPTCHA         \n";
echo putih . "===============================================\n";

$config = getConfig($configFile);
$apikey = $config['apikey'];
$email = $config['email'];
$password = $config['password'];

clear();
echo putih . "===============================================\n";
echo kuning . "     LIGHTNINGMINER.COM BOT - HCAPTCHA         \n";
echo putih . "===============================================\n";
echo putih . "Email : " . cyan . maskEmail($email) . "\n";
echo putih . "-----------------------------------------------\n";

$login = do_login($email, $password);

if (!$login) {
    echo merah . "[AUTH] Login gagal!\n";
    exit;
}

$user = $login['user'];
echo hijau . "[AUTH] ✓ Login sukses!\n";
echo putih . "Username     : " . cyan . $user['username'] . "\n";
echo putih . "Coins        : " . hijau . number_format($user['coins']) . "\n";
echo putih . "Mining Power : " . biru . number_format($user['miningPower']) . " H/s\n";
echo putih . "Currency     : " . kuning . $user['selectedCurrency'] . "\n";
echo putih . "-----------------------------------------------\n";

while (true) {
    $cooldown = run_faucet($apikey, $email, $password);

    echo putih . "-----------------------------------------------\n";
    timer($cooldown + 2, " Waiting ");
}
