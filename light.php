<?php

error_reporting(0);
date_default_timezone_set('Asia/Jakarta');

// ============================================================
//  COLOR CONSTANTS
// ============================================================
define('RESET', "\033[0m");
define('BOLD', "\033[1m");
define('RED', "\033[31m");
define('GREEN', "\033[32m");
define('YELLOW', "\033[33m");
define('BLUE', "\033[34m");
define('MAGENTA', "\033[35m");
define('CYAN', "\033[36m");
define('WHITE', "\033[37m");
define('GRAY', "\033[90m");
define('B_RED', "\033[1;31m");
define('B_GREEN', "\033[1;32m");
define('B_YELLOW', "\033[1;33m");
define('B_BLUE', "\033[1;34m");
define('B_CYAN', "\033[1;36m");
define('B_WHITE', "\033[1;37m");
define('B_MAGENTA', "\033[1;35m");

// ============================================================
//  SOLVER ENDPOINTS (WARYONO)
// ============================================================
define('SOLVER_BASE', 'https://api.waryono.my.id');
define('API_IN',  SOLVER_BASE . '/in.php');
define('API_OUT', SOLVER_BASE . '/res.php');

// ============================================================
//  FUNCTION CURL (DENGAN COOKIE)
// ============================================================
function curl($url, $post = 0, $httpheader = 0, $proxy = 0) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 30);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    curl_setopt($ch, CURLOPT_COOKIEFILE, 'cookie.txt');
    curl_setopt($ch, CURLOPT_COOKIEJAR, 'cookie.txt');
    
    if ($post) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    }
    if ($httpheader) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $httpheader);
    }
    if ($proxy) {
        curl_setopt($ch, CURLOPT_HTTPPROXYTUNNEL, true);
        curl_setopt($ch, CURLOPT_PROXY, $proxy);
    }
    curl_setopt($ch, CURLOPT_HEADER, true);
    $response = curl_exec($ch);
    if (!$response) {
        return "Curl Error: " . curl_error($ch);
    }
    $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $header = substr($response, 0, $header_size);
    $body = substr($response, $header_size);
    @curl_close($ch);
    return array($header, $body);
}

// ============================================================
//  FUNCTION CURL REQUEST (TANPA HEADER)
// ============================================================
function curl_request($url, $method = 'GET', $post = null, $headers = []) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 30);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    if ($headers) curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    }
    $response = curl_exec($ch);
    $error = curl_error($ch);
    @curl_close($ch);
    if ($error) return false;
    return $response;
}

// ============================================================
//  DISPLAY BANNER
// ============================================================
function displayBanner($username = '') {
    system('clear');
    $line = str_repeat('═', 56);
    echo B_CYAN . "╔" . $line . "╗" . RESET . "\n";
    echo B_CYAN . "║" . RESET . str_repeat(' ', 8) . B_MAGENTA . ":: ⚡️LightningQuest⚡️ ::" . RESET . str_repeat(' ', 9) . B_CYAN . "║" . RESET . "\n";
    echo B_CYAN . "║" . RESET . str_repeat(' ', 14) . B_RED . "🔥AUTO EARN BOT🔥" . RESET . str_repeat(' ', 15) . B_CYAN . "║" . RESET . "\n";
    echo B_CYAN . "╚" . $line . "╝" . RESET . "\n";
    echo "\n";
    echo B_CYAN . "  [+] Website : " . B_WHITE . "⚡️lightningquest.net ⚡️" . RESET . "\n";
    echo B_CYAN . "  [+] ScriptMaker : " . B_YELLOW . "@SouuXso 🔥" . RESET . "\n";
    echo B_CYAN . "  [+] Captcha Solver : " . B_GREEN . "waryono.my.id ⚡" . RESET . "\n";
    echo B_CYAN . "  [+] Bot : " . B_GREEN . "ONLINE 🟢" . RESET . "\n";
    echo B_CYAN . str_repeat('═', 56) . RESET . "\n";
    echo "\n";
    if ($username) {
        echo B_CYAN . "  [+] Welcome, " . B_WHITE . $username . RESET . "\n\n";
    }
}

// ============================================================
//  TIMER
// ============================================================
function timer($seconds) {
    $wait_time = (int)$seconds;
    if ($wait_time <= 0) $wait_time = 5;
    $frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
    $current_frame = 0;
    while ($wait_time > 0) {
        $hours = floor($wait_time / 3600);
        $minutes = floor(($wait_time % 3600) / 60);
        $seconds_left = $wait_time % 60;
        $time_formatted = sprintf('%02d:%02d:%02d', $hours, $minutes, $seconds_left);
        $spinner = $frames[$current_frame];
        echo "\r" . B_CYAN . "  ⏳ Cooldown: " . B_WHITE . $time_formatted . " " . $spinner . "   " . RESET;
        sleep(1);
        $wait_time--;
        $current_frame = ($current_frame + 1) % count($frames);
    }
    echo "\r" . str_repeat(" ", 50) . "\r";
}

// ============================================================
//  SAVE DATA
// ============================================================
function Save($namadata) {
    if (file_exists($namadata)) {
        $data = file_get_contents($namadata);
    } else {
        echo B_CYAN . "  [!] " . B_WHITE . "Input " . $namadata . " : " . RESET;
        $data = trim(fgets(STDIN));
        file_put_contents($namadata, $data);
    }
    return $data;
}

// ============================================================
//  GET SITEKEY DARI API CONFIG
// ============================================================
function getSitekeyFromConfig($access_token, $api) {
    $headers = [
        'User-Agent: '.$api,
        'Authorization: Bearer ' . $access_token,
        'x-requested-with: XMLHttpRequest',
        'Content-Type: application/json',
    ];
    list($header, $body) = curl('https://lightningquest.net/api/config', 0, $headers);
    $data = json_decode($body, true);
    
    if (isset($data['hcaptchaSiteKey']) && $data['hcaptchaSiteKey']) {
        return $data['hcaptchaSiteKey'];
    }
    if (isset($data['turnstileSiteKey']) && $data['turnstileSiteKey']) {
        return $data['turnstileSiteKey'];
    }
    return null;
}

// ============================================================
//  GET CSRF 
// ============================================================
function getCSRF() {
    if (file_exists('csrf_cache.txt')) {
        $csrf = trim(file_get_contents('csrf_cache.txt'));
        if (strlen($csrf) > 5) return $csrf;
    }
    
    if (file_exists('cookie.txt')) {
        $cookie = file_get_contents('cookie.txt');
        if (preg_match('/XSRF-TOKEN[=\s]+([^;\s]+)/i', $cookie, $match)) {
            $csrf = urldecode($match[1]);
            if (strlen($csrf) > 5) {
                file_put_contents('csrf_cache.txt', $csrf);
                return $csrf;
            }
        }
        if (preg_match('/csrf_token[=\s]+([^;\s]+)/i', $cookie, $match)) {
            $csrf = urldecode($match[1]);
            if (strlen($csrf) > 5) {
                file_put_contents('csrf_cache.txt', $csrf);
                return $csrf;
            }
        }
    }
    
    $headers = [
        'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'x-requested-with: XMLHttpRequest',
    ];
    if (file_exists('access_token.txt')) {
        $token = trim(file_get_contents('access_token.txt'));
        $headers[] = 'Authorization: Bearer ' . $token;
    }
    list($header, $html) = curl('https://lightningquest.net/faucet', 0, $headers);
    
    $patterns = [
        '/<meta name="csrf-token" content="([^"]+)"/i',
        '/<meta name="csrf_token" content="([^"]+)"/i',
        '/<input[^>]*name="csrf_token"[^>]*value="([^"]+)"/i',
        '/csrfToken\s*=\s*"([^"]+)"/i',
        '/"csrf_token"\s*:\s*"([^"]+)"/i',
        '/<script[^>]*>.*?csrf_token["\']?\s*[:=]\s*["\']([^"\']+)["\']/si',
    ];
    foreach ($patterns as $pattern) {
        if (preg_match($pattern, $html, $match)) {
            $csrf = $match[1];
            if (strlen($csrf) > 5) {
                file_put_contents('csrf_cache.txt', $csrf);
                return $csrf;
            }
        }
    }
    
    return 'fallback_' . md5(time());
}

// ============================================================
//  CEK SALDO WARYONO
// ============================================================
function checkBalance() {
    $apiKey = trim(file_get_contents('bypass_api_key.txt'));
    if (!$apiKey) return false;

    $url = API_OUT . "?" . http_build_query([
        'apikey' => $apiKey,
        'action' => 'getbalance',
        'json'   => 1
    ]);

    $response = curl_request($url);
    if ($response === false) return false;

    $data = json_decode($response, true);
    return $data['balance'] ?? false;
}

// ============================================================
//  BYPASS CAPTCHA (WARYONO.MY.ID)
// ============================================================
function bypassCaptcha($sitekey, $method, $pageurl) {
    $apiKey = trim(file_get_contents('bypass_api_key.txt'));
    if (!$apiKey) {
        echo B_RED . "  [!] API Key waryono.my.id tidak ditemukan!\n" . RESET;
        return false;
    }

    // Map method ke format waryono
    $methodMap = [
        'hcaptcha'     => 'hcaptcha',
        'turnstile'    => 'turnstile',
        'recaptcha'    => 'recaptcha',
        'recaptcha_v2' => 'recaptcha',
    ];
    $solverMethod = $methodMap[strtolower($method)] ?? 'hcaptcha';

    // --- STEP 1: SUBMIT KE /in.php (POST JSON) ---
    $submitUrl = API_IN;

    $payload = json_encode([
        'apikey'  => $apiKey,
        'methods' => $solverMethod,
        'domain'  => $pageurl,
        'sitekey' => $sitekey,
        'json'    => 1,
    ]);

    echo B_YELLOW . "  [BYPASS] Submitting to waryono.my.id ({$solverMethod})...\n" . RESET;

    $response = curl_request($submitUrl, 'POST', $payload, [
        'Content-Type: application/json'
    ]);

    if ($response === false) {
        echo B_RED . "  [!] Gagal koneksi ke waryono.my.id\n" . RESET;
        return false;
    }

    $data = json_decode($response, true);
    if (!isset($data['status']) || $data['status'] != 1 || empty($data['request'])) {
        $errMsg = $data['request'] ?? $response;
        echo B_RED . "  [!] Submit error: " . $errMsg . "\n" . RESET;

        // Fatal: API key / saldo
        if (is_string($errMsg) && (
            strpos($errMsg, 'ERROR_KEY') !== false ||
            strpos($errMsg, 'ERROR_WRONG') !== false ||
            strpos($errMsg, 'ERROR_ZERO_BALANCE') !== false
        )) {
            echo B_RED . "  [💀] API key / saldo bermasalah. Stop.\n" . RESET;
            return false;
        }
        return false;
    }

    $taskId = $data['request'];
    echo B_YELLOW . "  [BYPASS] Task ID: " . $taskId . "\n" . RESET;

    // --- STEP 2: POLLING KE /res.php (GET) ---
    for ($i = 0; $i < 60; $i++) {
        sleep(3);

        $pollUrl = API_OUT . "?" . http_build_query([
            'apikey' => $apiKey,
            'id'     => $taskId,
            'action' => 'get',
            'json'   => 1
        ]);

        $result = curl_request($pollUrl);
        if ($result === false) continue;

        $pollData = json_decode($result, true);
        if (!isset($pollData['status'])) continue;

        // Sukses
        if ($pollData['status'] == 1 && !empty($pollData['request'])) {
            $token = $pollData['request'];
            echo "\r" . B_GREEN . "  [BYPASS] ✓ Token obtained (" . strlen($token) . " chars)          \n" . RESET;
            return $token;
        }

        // Masih diproses
        if ($pollData['request'] === 'CAPCHA_NOT_READY') {
            echo "\r" . B_CYAN . "  [BYPASS] Polling... (" . ($i + 1) . "/60)   " . RESET;
            continue;
        }

        // Error
        if (is_string($pollData['request']) && strpos($pollData['request'], 'ERROR') !== false) {
            echo "\n" . B_RED . "  [BYPASS] Error: " . $pollData['request'] . "\n" . RESET;
            return false;
        }
    }

    echo "\n" . B_RED . "  [BYPASS] ✗ Timeout menunggu token\n" . RESET;
    return false;
}

// ============================================================
//  LOGIN
// ============================================================
function doLogin($email, $pass, $api) {
    @unlink('cookie.txt');
    @unlink('access_token.txt');
    @unlink('csrf_cache.txt');
    
    $headers = [
        'User-Agent: '.$api,
        'sec-ch-ua-platform: "Android"',
        'x-requested-with: XMLHttpRequest',
        'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Android WebView";v="146"',
        'Content-Type: application/json',
        'sec-ch-ua-mobile: ?1',
        'origin: https://lightningquest.net',
        'sec-fetch-site: same-origin',
        'sec-fetch-mode: cors',
        'sec-fetch-dest: empty',
        'referer: https://lightningquest.net/login',
        'accept-language: en-GB,en-US;q=0.9,en;q=0.8',
        'priority: u=1, i',
    ];
    $post = '{"email":"'.$email.'","password":"'.$pass.'","trafficExchangeBonus":false}';
    
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => 'https://lightningquest.net/api/auth/login',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $post,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_COOKIEFILE => 'cookie.txt',
        CURLOPT_COOKIEJAR => 'cookie.txt',
        CURLOPT_HEADER => false,
        CURLOPT_TIMEOUT => 30,
    ]);
    $response = curl_exec($ch);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error) {
        echo B_RED . "  [LOGIN] Curl error: $error\n" . RESET;
        return false;
    }
    
    $data = json_decode($response, true);
    if (!empty($data['access_token']) && !empty($data['user']['user_metadata']['username'])) {
        file_put_contents('access_token.txt', $data['access_token']);
        return $data['user']['user_metadata']['username'];
    } else {
        echo B_RED . "  [LOGIN] Gagal! Response: " . substr($response, 0, 200) . "\n" . RESET;
        return false;
    }
}

// ============================================================
//  QUESTS
// ============================================================
function doQuests($api, $access_token) {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL => 'https://lightningquest.net/api/quests/progress',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_COOKIEJAR => 'cookie.txt',
        CURLOPT_COOKIEFILE => 'cookie.txt',
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: '.$api,
            'sec-ch-ua-platform: "Android"',
            'sec-ch-ua: "Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            'upgrade-insecure-requests: 1',
            'sec-ch-ua-mobile: ?1',
            'sec-fetch-site: same-origin',
            'sec-fetch-mode: navigate',
            'sec-fetch-dest: empty',
            'referer: https://lightningquest.net/quests',
            'accept-language: en-GB,en-US;q=0.9,hi;q=0.7',
            'priority: u=0, i',
            'Authorization: Bearer ' . $access_token,
        ],
    ]);
    $res = curl_exec($curl);
    $data = json_decode($res, true);
    
    if (($data['error'] ?? '') === 'unauthorized') return 'unauthorized';
    
    $claimId = null;
    foreach ($data['progress'] ?? [] as $q) {
        if ($q['complete'] && !$q['claimed']) {
            $claimId = $q['id'];
            break;
        }
    }
    if (!$claimId) {
        echo B_YELLOW . "      ⚠️ No quest to claim.\n" . RESET;
        return true;
    }
    
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL => "https://lightningquest.net/api/quests/$claimId/claim",
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_COOKIEJAR => 'cookie.txt',
        CURLOPT_COOKIEFILE => 'cookie.txt',
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_CUSTOMREQUEST => 'POST',
        CURLOPT_HTTPHEADER => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: '.$api,
            'sec-ch-ua-platform: "Android"',
            'sec-ch-ua: "Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            'upgrade-insecure-requests: 1',
            'sec-ch-ua-mobile: ?1',
            'sec-fetch-site: same-origin',
            'sec-fetch-mode: navigate',
            'sec-fetch-dest: empty',
            'referer: https://lightningquest.net/quests',
            'accept-language: en-GB,en-US;q=0.9,hi;q=0.7',
            'priority: u=0, i',
            'Authorization: Bearer ' . $access_token,
        ],
    ]);
    $res = curl_exec($curl);
    $data = json_decode($res, true);
    
    if (($data['ok'] ?? false) === true) {
        $coins = $data['reward']['coins'] ?? 0;
        $xp = $data['reward']['xp'] ?? 0;
        echo B_GREEN . "      ✓ Quest claimed! +{$coins} Coins, +{$xp} XP\n" . RESET;
        return true;
    }
    echo B_YELLOW . "      ⚠️ No quest to claim.\n" . RESET;
    return true;
}

// ============================================================
//  DAILY BONUS
// ============================================================
function doDaily($api, $access_token) {
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL => "https://lightningquest.net/api/claim/daily",
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_COOKIEJAR => 'cookie.txt',
        CURLOPT_COOKIEFILE => 'cookie.txt',
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_CUSTOMREQUEST => 'POST',
        CURLOPT_POSTFIELDS => '{}',
        CURLOPT_HTTPHEADER => [
            'x-requested-with: XMLHttpRequest',
            'User-Agent: '.$api,
            'sec-ch-ua-platform: "Android"',
            'sec-ch-ua: "Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            'upgrade-insecure-requests: 1',
            'sec-ch-ua-mobile: ?1',
            'sec-fetch-site: same-origin',
            'sec-fetch-mode: navigate',
            'sec-fetch-dest: empty',
            'referer: https://lightningquest.net/daily',
            'accept-language: en-GB,en-US;q=0.9,hi;q=0.7',
            'priority: u=0, i',
            'Authorization: Bearer ' . $access_token,
        ],
    ]);
    $res = curl_exec($curl);
    $data = json_decode($res, true);
    
    if (($data['ok'] ?? false) === true) {
        $coins = $data['reward']['coins'] ?? 0;
        $xp = $data['reward']['xp'] ?? 0;
        echo B_GREEN . "      ✓ Daily bonus claimed! +{$coins} Coins, +{$xp} XP\n" . RESET;
        return true;
    }
    echo B_YELLOW . "      ⚠️ Daily bonus already claimed.\n" . RESET;
    return false;
}

// ============================================================
//  FAUCET
// ============================================================
function doFaucet($api, $access_token, &$reward_info) {
    echo B_CYAN . "  [💧] Faucet\n" . RESET;
    echo "      Status      : " . B_YELLOW . "Checking...\n" . RESET;

    $headers = [
        'x-requested-with: XMLHttpRequest',
        'User-Agent: '.$api,
        'Authorization: Bearer ' . $access_token,
    ];
    list($header, $body) = curl('https://lightningquest.net/api/claim-status', 0, $headers);
    $data0 = json_decode($body, true);
    
    if (isset($data0['error']) && $data0['error'] === 'unauthorized') {
        return 'unauthorized';
    }
    
    if ($data0 && isset($data0['faucet']['ready']) && $data0['faucet']['ready'] === false) {
        $nextAt = strtotime($data0['faucet']['nextAt']);
        $next = max(0, $nextAt - time());
        $min = floor($next / 60);
        $sec = $next % 60;
        echo "      Status      : " . B_YELLOW . "⏳ Cooldown\n" . RESET;
        echo "      Next Claim  : " . B_WHITE . "{$min}m {$sec}s\n" . RESET;
        timer($next);
        return 'cooldown';
    }

    $captchaRequired = $data0['faucet']['captchaRequired'] ?? false;
    $captchaProvider = $data0['faucet']['captchaProvider'] ?? 'hcaptcha';
    
    $csrf = getCSRF();
    if (!$csrf || strlen($csrf) < 3) {
        echo "      Status      : " . B_RED . "❌ CSRF token tidak ditemukan\n" . RESET;
        return false;
    }
    
    // GET challenge
    $challengeHeaders = [
        'User-Agent: '.$api,
        'Authorization: Bearer ' . $access_token,
        'Content-Type: application/json',
        'x-requested-with: XMLHttpRequest',
        'referer: https://lightningquest.net/faucet',
        'X-CSRF-TOKEN: ' . $csrf,
    ];
    list($header3, $body3) = curl('https://lightningquest.net/api/faucet/challenge', 0, $challengeHeaders);
    $data3 = json_decode($body3, true);
    
    if (!isset($data3['claimToken'])) {
        echo "      Status      : " . B_RED . "❌ Failed to get claimToken\n" . RESET;
        return false;
    }
    
    $claimToken = $data3['claimToken'];
    $minWaitSeconds = $data3['minWaitSeconds'] ?? 5;
    echo "      ⏳ Waiting   : " . B_WHITE . "{$minWaitSeconds}s\n" . RESET;
    timer($minWaitSeconds);

    // Build payload
    if ($captchaRequired) {
        echo "      Status      : " . B_YELLOW . "Bypassing {$captchaProvider}...\n" . RESET;
        
        // AMBIL SITEKEY
        $sitekey = getSitekeyFromConfig($access_token, $api);
        
        if (!$sitekey) {
            $headers2 = [
                'User-Agent: ' . $api,
                'Authorization: Bearer ' . $access_token,
                'referer: https://lightningquest.net/faucet',
                'X-CSRF-TOKEN: ' . $csrf,
            ];
            list($header2, $html) = curl('https://lightningquest.net/faucet', 0, $headers2);
            
            $patterns = [
                '/data-sitekey="([^"]+)"/i',
                '/data-turnstile-widget="[^"]+"[^>]*data-sitekey="([^"]+)"/i',
                '/hcaptcha-sitekey="([^"]+)"/i',
                '/turnstile-sitekey="([^"]+)"/i',
            ];
            foreach ($patterns as $pattern) {
                if (preg_match($pattern, $html, $match)) {
                    $sitekey = $match[1];
                    break;
                }
            }
        }
        
        if (!$sitekey) {
            echo "      Status      : " . B_RED . "❌ Sitekey not found\n" . RESET;
            return false;
        }
        
        echo B_YELLOW . "  [DEBUG] Sitekey: " . $sitekey . "\n" . RESET;
        
        $token = bypassCaptcha($sitekey, $captchaProvider, 'https://lightningquest.net/faucet');
        if (!$token) {
            echo "      Status      : " . B_RED . "❌ Bypass failed\n" . RESET;
            return false;
        }
        
        $payload = json_encode([
            'csrf_token' => $csrf,
            'claimToken' => $claimToken,
            'captchaToken' => $token,
            'captchaProvider' => $captchaProvider,
        ]);
    } else {
        echo "      Status      : " . B_GREEN . "No captcha required\n" . RESET;
        $payload = json_encode([
            'csrf_token' => $csrf,
            'claimToken' => $claimToken,
        ]);
    }

    // Claim
    $claimHeaders = [
        'User-Agent: '.$api,
        'Content-Type: application/json',
        'Authorization: Bearer ' . $access_token,
        'X-CSRF-TOKEN: ' . $csrf,
        'x-requested-with: XMLHttpRequest',
        'referer: https://lightningquest.net/faucet',
    ];
    list($header4, $body4) = curl('https://lightningquest.net/api/claim/faucet', $payload, $claimHeaders);
    $data4 = json_decode($body4, true);
    
    if ($data4 && ($data4['ok'] ?? false)) {
        $coins = $data4['reward']['coins'] ?? 0;
        $xp = $data4['reward']['xp'] ?? 0;
        $balance = $data4['reward']['snapshot']['balance'] ?? 0;
        $level = $data4['reward']['snapshot']['level'] ?? 0;
        $multiplier = $data4['reward']['snapshot']['multiplier'] ?? 1;
        $nextAt = strtotime($data4['nextAt'] ?? date('Y-m-d H:i:s', time() + 60));
        $next = max(0, $nextAt - time());
        $min = floor($next / 60);
        $sec = $next % 60;

        $reward_info = [
            'coins' => $coins,
            'xp' => $xp,
            'balance' => number_format($balance, 0, '.', ','),
            'level' => $level,
            'multiplier' => $multiplier,
            'next_min' => $min,
            'next_sec' => $sec
        ];

        echo "      ✓ " . B_GREEN . "Claim Successful!\n" . RESET;
        return true;
    } else {
        $errorMsg = $data4['message'] ?? 'Unknown error';
        echo "      Status      : " . B_RED . "❌ Claim failed: $errorMsg\n" . RESET;
        return false;
    }
}

// ============================================================
//  FARMING MAIN LOOP
// ============================================================
function startFarming($email, $pass, $api) {
    $username = doLogin($email, $pass, $api);
    if (!$username) {
        echo B_RED . "  [!] Login Gagal! Cek email/password.\n" . RESET;
        return;
    }
    
    $access_token = trim(file_get_contents('access_token.txt'));
    displayBanner($username);

    // Cek saldo Waryono
    $balance = checkBalance();
    if ($balance !== false) {
        echo B_CYAN . "  💰 Waryono Balance : " . B_WHITE . $balance . " Tokens\n" . RESET;
    }
    echo B_YELLOW . "  🔄 Starting auto loop...\n\n" . RESET;
    
    $fail_count = 0;
    $loop_count = 0;
    $max_failures = 10;
    
    while (true) {
        $loop_count++;
        echo B_CYAN . "  ===== Loop #{$loop_count} ===== \n\n" . RESET;
        
        // 1. QUESTS
        echo B_CYAN . "  [📋] Quest\n" . RESET;
        $quest_result = doQuests($api, $access_token);
        if ($quest_result === 'unauthorized') {
            echo B_RED . "  [!] Session expired. Re-login...\n" . RESET;
            $username = doLogin($email, $pass, $api);
            if (!$username) {
                echo B_RED . "  [FATAL] Re-login gagal, keluar.\n" . RESET;
                break;
            }
            $access_token = trim(file_get_contents('access_token.txt'));
            sleep(2);
            continue;
        }
        echo "\n";
        
        // 2. DAILY BONUS
        echo B_CYAN . "  [🎁] Daily\n" . RESET;
        doDaily($api, $access_token);
        echo "\n";
        
        // 3. FAUCET
        $reward_info = [];
        $faucet_result = doFaucet($api, $access_token, $reward_info);
        
        if ($faucet_result === 'unauthorized') {
            echo B_RED . "  [!] Session expired. Re-login...\n" . RESET;
            $username = doLogin($email, $pass, $api);
            if (!$username) {
                echo B_RED . "  [FATAL] Re-login gagal, keluar.\n" . RESET;
                break;
            }
            $access_token = trim(file_get_contents('access_token.txt'));
            sleep(2);
            continue;
        }
        
        if ($faucet_result === true && !empty($reward_info)) {
            echo "\n" . B_CYAN . "  ==================== REWARD ====================\n\n" . RESET;
            echo B_WHITE . "      [+] Coins      : " . B_GREEN . "+" . $reward_info['coins'] . "⚡️\n" . RESET;
            echo B_WHITE . "      [+] XP         : " . B_GREEN . "+" . $reward_info['xp'] . "⭐️\n" . RESET;
            echo B_WHITE . "      [+] Balance    : " . B_YELLOW . $reward_info['balance'] . "⚡️\n" . RESET;
            echo B_WHITE . "      [+] Level      : " . B_MAGENTA . $reward_info['level'] . "📍\n" . RESET;
            echo B_WHITE . "      [+] Multiplier : " . B_CYAN . "x" . $reward_info['multiplier'] . "🥇\n" . RESET;
            echo B_WHITE . "      [+] Next Claim : " . B_YELLOW . $reward_info['next_min'] . "m " . sprintf("%02d", $reward_info['next_sec']) . "s\n" . RESET;
            echo B_CYAN . "\n  ================================================\n" . RESET;
        }
        
        if ($faucet_result === false) {
            $fail_count++;
            if ($fail_count >= $max_failures) {
                echo B_RED . "  [!] Too many failures. Waiting 60s...\n" . RESET;
                timer(60);
                $fail_count = 0;
            }
            timer(10);
        } else {
            $fail_count = 0;
        }
        
        echo "\n" . B_CYAN . "  🔄 Preparing next loop...\n\n" . RESET;
        sleep(5);
    }
}

// ============================================================
//  MENU FUNCTIONS
// ============================================================
function clearScreen() {
    system('clear');
}

function printMenu() {
    clearScreen();
    echo B_CYAN . "================================================\n";
    echo B_CYAN . "  " . B_WHITE . "LightningQuest Auto Claim Bot" . B_CYAN . "  \n";
    echo B_CYAN . "================================================\n";
    echo B_CYAN . "  [1] " . B_GREEN . "Start Farming\n";
    echo B_CYAN . "  [2] " . B_YELLOW . "Config Email & Password\n";
    echo B_CYAN . "  [3] " . B_YELLOW . "Config Bypass API Key (waryono.my.id)\n";
    echo B_CYAN . "  [4] " . B_YELLOW . "Check Waryono Balance\n";
    echo B_CYAN . "  [0] " . B_RED . "Exit\n";
    echo B_CYAN . "================================================\n";
    echo B_WHITE . "  Pilih menu: " . RESET;
}

function configEmailPassword() {
    clearScreen();
    echo B_CYAN . "================================================\n";
    echo B_CYAN . "  " . B_WHITE . "Konfigurasi Akun\n";
    echo B_CYAN . "================================================\n\n";
    
    echo B_WHITE . "Email: " . RESET;
    $email = trim(fgets(STDIN));
    echo B_WHITE . "Password: " . RESET;
    $pass = trim(fgets(STDIN));
    echo B_WHITE . "User-Agent (default: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36): " . RESET;
    $ua = trim(fgets(STDIN));
    if (empty($ua)) {
        $ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36";
    }
    
    file_put_contents('Email', $email);
    file_put_contents('Password', $pass);
    file_put_contents('user-agent', $ua);
    
    echo B_GREEN . "\n✅ Konfigurasi disimpan!\n" . RESET;
    echo B_WHITE . "\nTekan Enter untuk kembali...\n" . RESET;
    fgets(STDIN);
}

function configApikey() {
    clearScreen();
    echo B_CYAN . "================================================\n";
    echo B_CYAN . "  " . B_WHITE . "Konfigurasi API Key (WARYONO.MY.ID)\n";
    echo B_CYAN . "================================================\n\n";
    echo B_YELLOW . "  Dapatkan API Key dari https://waryono.my.id\n";
    echo B_YELLOW . "  Biaya hCaptcha: 1 Token / solve\n\n" . RESET;
    echo B_WHITE . "API Key: " . RESET;
    $key = trim(fgets(STDIN));
    if (!empty($key)) {
        file_put_contents('bypass_api_key.txt', $key);
        echo B_GREEN . "\n✅ API Key disimpan!\n" . RESET;

        // Cek saldo otomatis
        $balance = checkBalance();
        if ($balance !== false) {
            echo B_GREEN . "💰 Saldo tersedia: " . B_WHITE . $balance . " Tokens\n" . RESET;
        } else {
            echo B_YELLOW . "⚠️ Gagal cek saldo, pastikan API Key benar.\n" . RESET;
        }
    } else {
        echo B_RED . "\n❌ API Key kosong, tidak disimpan.\n" . RESET;
    }
    echo B_WHITE . "\nTekan Enter untuk kembali...\n" . RESET;
    fgets(STDIN);
}

function menuCheckBalance() {
    clearScreen();
    echo B_CYAN . "================================================\n";
    echo B_CYAN . "  " . B_WHITE . "Check Waryono Balance\n";
    echo B_CYAN . "================================================\n\n";

    if (!file_exists('bypass_api_key.txt')) {
        echo B_RED . "❌ API Key belum diatur! Atur di menu [3] terlebih dahulu.\n" . RESET;
    } else {
        $apiKey = trim(file_get_contents('bypass_api_key.txt'));
        echo B_WHITE . "API Key: " . B_YELLOW . substr($apiKey, 0, 8) . "..." . substr($apiKey, -4) . "\n\n" . RESET;

        $balance = checkBalance();
        if ($balance !== false) {
            echo B_GREEN . "💰 Saldo : " . B_WHITE . $balance . " Tokens\n" . RESET;
            echo B_GRAY . "   ≈ " . floor($balance / 1.0) . " hCaptcha solves remaining\n" . RESET;
        } else {
            echo B_RED . "❌ Gagal cek saldo, API Key mungkin tidak valid.\n" . RESET;
        }
    }
    echo B_WHITE . "\nTekan Enter untuk kembali...\n" . RESET;
    fgets(STDIN);
}

// ============================================================
//  MAIN MENU
// ============================================================
while (true) {
    printMenu();
    $choice = trim(fgets(STDIN));
    
    switch ($choice) {
        case '1':
            clearScreen();
            if (!file_exists('Email') || !file_exists('Password') || !file_exists('user-agent')) {
                echo B_RED . "  [!] Konfigurasi belum lengkap! Silakan atur Email & Password terlebih dahulu (Menu 2).\n" . RESET;
                echo B_WHITE . "\nTekan Enter untuk kembali...\n" . RESET;
                fgets(STDIN);
                break;
            }
            if (!file_exists('bypass_api_key.txt')) {
                echo B_YELLOW . "  [!] API Key bypass belum diatur. Script akan tetap jalan, tapi jika captcha muncul mungkin gagal.\n" . RESET;
                echo B_WHITE . "  Tekan Enter untuk lanjutkan, atau Ctrl+C untuk keluar dan atur API Key (Menu 3).\n" . RESET;
                fgets(STDIN);
            }
            $email = trim(file_get_contents('Email'));
            $pass = trim(file_get_contents('Password'));
            $api = trim(file_get_contents('user-agent'));
            startFarming($email, $pass, $api);
            break;
            
        case '2':
            configEmailPassword();
            break;
            
        case '3':
            configApikey();
            break;
            
        case '4':
            menuCheckBalance();
            break;
            
        case '0':
            echo B_GREEN . "\nTerima kasih! Sampai jumpa.\n" . RESET;
            exit(0);
            
        default:
            echo B_RED . "\nPilihan tidak valid!\n" . RESET;
            echo B_WHITE . "Tekan Enter untuk melanjutkan...\n" . RESET;
            fgets(STDIN);
    }
}
