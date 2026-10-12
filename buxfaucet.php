<?php
error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$file_config = "configbux.json";
$file_cookie = "cookiesbux.txt";


const c_hitam  = "\033[0;30m";
const c_merah  = "\033[1;31m";
const c_hijau  = "\033[1;32m";
const c_kuning = "\033[1;33m";
const c_biru   = "\033[1;34m";
const c_ungu   = "\033[1;35m";
const c_cyan   = "\033[1;36m";
const c_putih  = "\033[1;37m";
const c_reset  = "\033[0m";

const host_url = "https://buxfaucet.com";
const api_wry  = "https://api.waryono.my.id";

function bersihkan_layar() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function reqServer($url, $method = 'GET', $data = [], $headers = []) {
    while (true) {
        $ch = curl_init();
        $options = [
            CURLOPT_URL            => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER         => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 1,
            CURLOPT_HTTPHEADER     => $headers,
            CURLOPT_CONNECTTIMEOUT => 15,
            CURLOPT_TIMEOUT        => 15,
            CURLOPT_COOKIEFILE     => 'cookies.txt',
            CURLOPT_COOKIEJAR      => 'cookies.txt'
        ];
        if (strtoupper($method) === 'POST') {
            $options[CURLOPT_POST] = true;
            $options[CURLOPT_POSTFIELDS] = $data;
        }
        curl_setopt_array($ch, $options);
        $response = curl_exec($ch);
        if ($response) {
            $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
            $body = substr($response, $header_size);
            curl_close($ch);
            return $body;
        } else {
            curl_close($ch);
            sleep(1);
            return "ngelek";
        }
    }
}

function aturHeader(&$headGet, &$headPost) {
    $headGet = [
        "host: buxfaucet.com",
        "user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ];
    $headPost = [
        "host: buxfaucet.com",
        "content-type: application/x-www-form-urlencoded",
        "user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "origin: https://buxfaucet.com",
        "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "referer: https://buxfaucet.com/withdraw"
    ];
}

function getSaldoWaryono($apikey) {
    $res = reqServer(api_wry . "/res.php?apikey=" . trim($apikey) . "&action=getuser", "GET");
    $json = json_decode($res, true);
    return (isset($json['status']) && $json['status'] == 1) ? $json['balance'] : "Invalid Key";
}

function cetakBanner($apikey, $rekapan = []) {
    bersihkan_layar();
    $saldo_api = getSaldoWaryono($apikey);
    echo c_cyan . " ╔═════════════════════════════════════════╗\n";
    echo c_cyan . " ║ " . c_biru . "██████╗ " . c_merah . "██╗   ██╗" . c_hijau . "██╗  ██╗" . c_cyan . "    ║\n";
    echo c_cyan . " ║ " . c_biru . "██╔══██╗" . c_merah . "██║   ██║" . c_hijau . "╚██╗██╔╝" . c_cyan . "    ║\n";
    echo c_cyan . " ║ " . c_biru . "██████╔╝" . c_merah . "██║   ██║" . c_hijau . " ╚███╔╝ " . c_cyan . "    ║\n";
    echo c_cyan . " ║ " . c_biru . "██╔══██╗" . c_merah . "██║   ██║" . c_hijau . " ██╔██╗ " . c_cyan . "    ║\n";
    echo c_cyan . " ║ " . c_biru . "██████╔╝" . c_merah . "╚██████╔╝" . c_hijau . "██╔╝ ██╗" . c_cyan . "    ║\n";
    echo c_cyan . " ║ " . c_cyan . "╚═════╝  ╚═════╝ ╚═╝  ╚═╝" . c_cyan . "    ║\n";
    echo c_cyan . " ╚═════════════════════════════════════════╝\n";
    echo c_putih . " [ " . c_cyan . "ENGINE" . c_putih . " : " . c_hijau . "BONCEL ENGINE" . c_putih . " ]\n";
    echo c_putih . " [ " . c_cyan . "SOLVER" . c_putih . " : " . c_kuning . "Waryono Solver" . c_putih . " ]\n";
    echo c_putih . " [ " . c_cyan . "BALANCE" . c_putih . " : " . c_hijau . $saldo_api . c_putih . " ]\n";
    echo c_putih . " [ " . c_cyan . "AUTHOR" . c_putih . " : " . c_kuning . "AHD1905" . c_putih . " ]\n";
    echo c_putih . " [ " . c_cyan . "SUPPORT" . c_putih . " : " . c_kuning . "ScriptyXSouu" . c_putih . " ]\n";
    
    if (!empty($rekapan)) {
        echo c_cyan . " ┌─[ " . c_hijau . "TODAY'S ACCUMULATED COINS" . c_cyan . " ]───────┐\n";
        foreach ($rekapan as $k => $v) {
            echo c_cyan . " │ " . c_putih . sprintf("%-8s", strtoupper($k)) . " : " . c_hijau . sprintf("%-27s", number_format($v, 8)) . c_cyan . " │\n";
        }
        echo c_cyan . " └───────────────────────────────────────────┘\n";
    }
}

function parseAlerts($html) {
    $alerts = [];
    preg_match_all('/<div[^>]*class="([^"]*)"[^>]*>(.*?)<\/div>/is', $html, $matches, PREG_SET_ORDER);
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

function parseError($response) {
    $alerts = parseAlerts($response);
    $texts  = array_column($alerts, 'text');
    $joined = strtolower(implode(' | ', $texts));

    if (strpos($response, 'Page Expired') !== false) {
        return ['type' => 'csrf_expired', 'message' => 'CSRF token expired - refresh page', 'raw' => $response];
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

    return ['type' => 'unknown', 'raw' => $response, 'alerts' => $texts];
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
            echo c_putih . $prefix . c_hijau . " $time_formatted " . c_putih . $spinner . "\r";
            usleep($frame_delay * 1000000);
            $current_frame = ($current_frame + 1) % $frame_count;
            if ((microtime(true) - $start_time) >= 1) {
                break;
            }
        }
        $wait_time--;
    }
    echo "\r                                     \r";
}

function getConfig($configFile) {
    if (!file_exists($configFile)) {
        echo c_putih . "API Key   : " . c_kuning;
        $apikey = trim(fgets(STDIN));
        echo c_putih . "Email     : " . c_kuning;
        $email = trim(fgets(STDIN));
        $data = [
            "apikey"   => $apikey,
            "email"    => $email
        ];
        file_put_contents($configFile, json_encode($data, JSON_PRETTY_PRINT));
        echo c_hijau . "Konfigurasi disimpan ke $configFile\n\n" . c_reset;
        sleep(3);
        return $data;
    }
    return json_decode(file_get_contents($configFile), true);
}

function hc($apikey, $sitekey) {
    $headers = ["Content-Type: application/json"];
    $body = json_encode([
        "apikey"  => $apikey,
        "methods" => "hcaptcha",
        "domain"  => host_url,
        "sitekey" => $sitekey,
        "json"    => 1
    ]);
    $request = reqServer(api_wry . "/in.php", "POST", $body, $headers);
    if (strpos($request, "ERROR_WRONG_METHOD") !== false)              { return "ERROR_WRONG_METHOD"; }
    if (strpos($request, "ERROR_KEY_DOES_NOT_EXIST") !== false)        { return "ERROR_KEY_DOES_NOT_EXIST"; }
    if (strpos($request, "ERROR_METHOD_NOT_SPECIFIED") !== false)      { return "ERROR_METHOD_NOT_SPECIFIED"; }
    if (strpos($request, "ERROR_NO_SUCH_METHOD") !== false)            { return "ERROR_NO_SUCH_METHOD"; }
    if (strpos($request, "ERROR_DATABASE_CONNECTION_FAILED") !== false){ return "ERROR_DATABASE_CONNECTION_FAILED"; }
    if (strpos($request, "ERROR_TOO_MANY_REQUESTS") !== false)         { return "ERROR_TOO_MANY_REQUESTS"; }
    if (strpos($request, "ERROR_WRONG_USER_KEY") !== false)            { return "ERROR_WRONG_USER_KEY"; }
    if (strpos($request, "ERROR_ZERO_BALANCE") !== false)              { return "ERROR_ZERO_BALANCE"; }
    if (strpos($request, "ERROR_BAD_PARAMETERS") !== false)            { return "ERROR_BAD_PARAMETERS"; }
    if (strpos($request, "ERROR_EMPTY_IMAGE") !== false)               { return "ERROR_EMPTY_IMAGE"; }
    if (strpos($request, "ERROR_UNKNOWN") !== false)                   { return "ERROR_UNKNOWN"; }

    $json = json_decode($request, true);
    $id   = $json["request"] ?? '';

    reload:
    timer(3, "  [hcap] ");
    $url    = "https://api.waryono.my.id/res.php?apikey=".$apikey."&action=get&id=".$id."&json=1";
    $result = reqServer($url, "GET", []);

    if (strpos($result, "ERROR_BAD_PARAMETERS") !== false)        { return "ERROR_BAD_PARAMETERS"; }
    if (strpos($result, "Database connection failed") !== false)   { return "DB_FAILED"; }
    if (strpos($result, "WRONG_CAPTCHA_ID") !== false)           { return "WRONG_CAPTCHA_ID"; }
    if (strpos($result, "ERROR_SOLVE_PENDING") !== false)        { return "ERROR_SOLVE_PENDING"; }
    if (strpos($result, "CAPCHA_NOT_READY") !== false)           { goto reload; }
    if (strpos($result, "ERROR_CAPTCHA_UNSOLVABLE") !== false)   { return "ERROR_CAPTCHA_UNSOLVABLE"; }
    if (strpos($result, "ERROR_BAD_REQUEST") !== false)          { return "ERROR_BAD_REQUEST"; }
    if (strpos($result, "INTENAL_SERVER_ERROR") !== false)       { return "INTENAL_SERVER_ERROR"; }

    $json = json_decode($result, true);
    $res  = $json["request"] ?? '';
    return ["captcha" => $res];
}

function promptEmail($current = '') {
    global $file_config;
    echo c_putih . "Email FaucetPay baru" . ($current !== '' ? " (sekarang: $current)" : "") . ": " . c_kuning;
    $new = trim(fgets(STDIN));
    if ($new === '') {
        echo c_putih . "[EMAIL] batal, tetap pakai email lama.\n" . c_reset;
        return $current;
    }
    $cfg = file_exists($file_config) ? json_decode(file_get_contents($file_config), true) : [];
    if (!is_array($cfg)) $cfg = [];
    $cfg['email'] = $new;
    file_put_contents($file_config, json_encode($cfg, JSON_PRETTY_PRINT));
    echo c_hijau . "[EMAIL] disimpan ke $file_config\n" . c_reset;
    return $new;
}

function claimCoin($selected_coin, $a, $b, $apikey, &$email) {
    $ku = strtoupper($selected_coin);
    while (true) {
        $url_faucet = host_url."/?faucet=".$selected_coin;
        $b_custom = $b;
        $b_custom[] = "referer: " . $url_faucet;

        $faucet = reqServer($url_faucet, "GET", [], $a);
        if (preg_match('/claim again after\s+([0-9]{2}):([0-9]{2})\s+Minutes/i', $faucet, $t_match)) {
            $menit = (int)$t_match[1];
            $detik = (int)$t_match[2];
            $total_seconds = ($menit * 60) + $detik;
            if ($total_seconds > 0) {
                echo c_kuning . " [$ku] Cooldown (" . $t_match[1] . ":" . $t_match[2] . ")\n" . c_reset;
                return ['status' => false, 'reward' => 0];
            }
        }
        preg_match('/name="_token"\s+value="([^"]+)"/i', $faucet, $token_match);
        $csrf_token = $token_match[1] ?? '';
        preg_match('/class="h-captcha"\s+data-sitekey="([^"]+)"/i', $faucet, $captcha_match);
        $sitekey = $captcha_match[1] ?? '';

        if (empty($sitekey)) {
            echo c_merah . " [$ku] Sitekey tidak ditemukan!\n" . c_reset;
            return ['status' => false, 'reward' => 0];
        }

        $bypass = hc($apikey, $sitekey);
        if (is_array($bypass)) {
            $data = http_build_query([
                "_token" => $csrf_token,
                "email" => $email,
                "g-recaptcha-response" => $bypass["captcha"],
                "h-captcha-response" => $bypass["captcha"],
                "countdown_value" => "0",
                "submitbtn" => ""
            ]);
            $claim = reqServer($url_faucet, "POST", $data, $b_custom);
            
            $reward_val = 0.00001000;
            if (preg_match('/([0-9]+\.[0-9]+)\s*(?:' . $ku . '|satoshis?|coins?)/i', $claim, $match_rew)) {
                $reward_val = (float)$match_rew[1];
            } elseif (preg_match('/(?:\+|successfully sent|added|reward)[:\s]*([0-9]+\.[0-9]+)/i', $claim, $match_rew2)) {
                $reward_val = (float)$match_rew2[1];
            }

            if (stripos($claim, 'success') !== false || stripos($claim, 'congratulations') !== false || stripos($claim, 'claimed') !== false || stripos($claim, 'reward') !== false) {
                echo c_hijau . " [$ku] Claim Berhasil! (+" . number_format($reward_val, 8) . ")\n" . c_reset;
                return ['status' => true, 'reward' => $reward_val];
            }

            $parsed = parseError($claim);

            if ($parsed['type'] === 'success') {
                echo c_hijau . " [$ku] " . $parsed['message'] . " (+" . number_format($reward_val, 8) . ")\n" . c_reset;
                return ['status' => true, 'reward' => $reward_val];
            }
            if ($parsed['type'] === 'captcha_error') {
                echo c_merah . " [$ku] Captcha Salah / Expired, Retrying...\n" . c_reset;
                continue;
            }
            if ($parsed['type'] === 'email_error') {
                echo c_merah . " [$ku] " . $parsed['message'] . "\n" . c_reset;
                $email = promptEmail($email);
                return ['status' => false, 'reward' => 0];
            }
            if ($parsed['type'] === 'rate_limit') {
                echo c_merah . " [$ku] Rate limit terdeteksi..\n" . c_reset;
                timer(15, "  [limit] ");
                continue;
            }
            if ($parsed['type'] === 'daily_limit') {
                echo c_kuning . " [$ku] Daily limit tercapai.\n" . c_reset;
                return ['status' => false, 'reward' => 0];
            }
            if ($parsed['type'] === 'cooldown') {
                echo c_kuning . " [$ku] Sedang Cooldown.\n" . c_reset;
                return ['status' => false, 'reward' => 0];
            }
            if ($parsed['type'] === 'csrf_expired') {
                echo c_merah . " [$ku] CSRF token expired, refreshing...\n" . c_reset;
                continue;
            }
            if ($parsed['type'] === 'error') {
                echo c_merah . " [$ku] " . $parsed['message'] . "\n" . c_reset;
                return ['status' => false, 'reward' => 0];
            }
            echo c_hijau . " [$ku] Claim Berhasil! (+" . number_format($reward_val, 8) . ")\n" . c_reset;
            return ['status' => true, 'reward' => $reward_val];
        } else {
            $err = is_string($bypass) ? $bypass : 'UNKNOWN';
            if (in_array($err, ["WRONG_CAPTCHA_ID", "ERROR_CAPTCHA_UNSOLVABLE", "ERROR_TOO_MANY_REQUESTS", "ERROR_SOLVE_PENDING", "INTENAL_SERVER_ERROR"])) {
                timer(2);
                continue;
            }
            echo c_merah . " [$ku] Captcha Error ($err), Retry...\n" . c_reset;
            sleep(2);
            continue;
        }
    }
}

function prosesWithdraw($headGet, $headPost, $apikey, $email) {
    while (true) {
        bersihkan_layar();
        echo c_cyan . " [~] Initializing session & parsing withdraw data...\n";
        reqServer(host_url, "GET", [], $headGet);
        $html = reqServer(host_url . "/withdraw", "GET", [], $headGet);
        
        $data_wd = [];
        preg_match('/name="_token"\s+value="([^"]+)"/i', $html, $global_token);
        $token = $global_token[1] ?? '';
        preg_match('/class="h-captcha"\s+data-sitekey="([^"]+)"/i', $html, $glob_sk);
        $sitekey_wd = $glob_sk[1] ?? '';

        $home = reqServer(host_url, "GET", [], $headGet);
        preg_match_all('/href="https?:\/\/buxfaucet\.com\/\?faucet=([^"]+)"/i', $home, $m_faucet);
        $coins_list = array_values(array_unique($m_faucet[1] ?? []));

        foreach ($coins_list as $fc) {
            $koin = strtoupper($fc);
            if ($koin !== 'INPUT' && $koin !== 'TOKEN' && $koin !== 'FORM' && $koin !== 'QUEST') {
                $saldo_val = "0.00000000";
                if (preg_match('/' . $koin . '.*?Balance[^0-9]*([0-9\.]+)/is', $html, $match_bal)) {
                    $saldo_val = $match_bal[1];
                }
                
                $token_koin = $token;
                if (preg_match('/' . $koin . '.*?name="_token"\s+value="([^"]+)"/is', $html, $match_tok)) {
                    $token_koin = $match_tok[1];
                }

                $data_wd[] = [
                    'coin' => $koin,
                    'balance' => $saldo_val,
                    'sitekey' => $sitekey_wd,
                    'token' => $token_koin
                ];
            }
        }

        cetakBanner($apikey);
        echo c_cyan . " ┌─[ " . c_hijau . "AUTO WITHDRAW MENU" . c_cyan . " ]───────┐\n";
        if (empty($data_wd)) {
            echo c_cyan . " │ " . c_kuning . " No withdraw options found or need login. " . c_cyan . " │\n";
        } else {
            $no = 1;
            foreach ($data_wd as $wd) {
                echo c_cyan . " │ " . c_putih . "[" . c_kuning . sprintf("%02d", $no) . c_putih . "] " . c_hijau . sprintf("%-11s", $wd['coin']) . " Bal: " . c_kuning . sprintf("%-10s", $wd['balance']) . c_cyan . " │\n";
                $no++;
            }
        }
        echo c_cyan . " └───────────────────────────────────────────┘\n";
        echo c_cyan . " [ " . c_hijau . "0" . c_cyan . " ] ➔ Kembali ke Menu Utama\n";
        echo c_putih . " Pilih Koin ➔ " . c_kuning;
        $pil = trim(fgets(STDIN));

        if ($pil === '0' || $pil === '') {
            return;
        }

        if (isset($data_wd[$pil - 1])) {
            $target = $data_wd[$pil - 1];
            if (empty($target['sitekey'])) {
                echo c_merah . "[ERROR] Sitekey tidak ditemukan, withdraw ditolak sistem.\n" . c_reset;
                sleep(2);
                continue;
            }

            echo "\n" . c_cyan . " [~] Solving hCaptcha for " . c_ungu . $target['coin'] . c_cyan . " withdraw...\n";
            $cap = hc($apikey, $target['sitekey']);
            
            if (is_array($cap)) {
                $captcha_val = $cap["captcha"];
                echo c_cyan . " [~] Sending request...\n";
                
                $withdraw_url = host_url . "/withdraw/" . $target['coin'];

                $post_data = http_build_query([
                    "_token" => $target['token'],
                    "g-recaptcha-response" => $captcha_val,
                    "h-captcha-response" => $captcha_val,
                    "submitbtn" => ""
                ]);
                
                $res = reqServer($withdraw_url, "POST", $post_data, $headPost);
                
                if (stripos($res, 'success') !== false || stripos($res, 'sent') !== false || stripos($res, 'withdrawn') !== false || stripos($res, 'successfully') !== false) {
                    echo c_hijau . "[SUCCESS] Withdraw " . $target['coin'] . " Berhasil Dikirim!\n" . c_reset;
                } else {
                    echo c_merah . "[ERROR] Withdraw Gagal / Respons Server Ditolak.\n" . c_reset;
                }
            } else {
                echo c_merah . "[ERROR] Gagal bypass hCaptcha!\n" . c_reset;
            }
            
            sleep(2);
        }
    }
}


menu_awal:
bersihkan_layar();
echo c_cyan . " ┌─[ " . c_kuning . "BUX FAUCET BOT" . c_cyan . " ]──────────────────┐\n";
$config   = getConfig($file_config);
$apikey   = $config['apikey'];
$email    = $config['email'];
aturHeader($hGet, $hPost);

cetakBanner($apikey);
echo c_cyan . " ┌─[ " . c_hijau . "MAIN MENU" . c_cyan . " ]──────────────────────────┐\n";
echo c_cyan . " │ " . c_putih . "[" . c_kuning . "1" . c_putih . "] " . c_hijau . sprintf("%-33s", "Start Faucet Bot") . c_cyan . " │\n";
echo c_cyan . " │ " . c_putih . "[" . c_kuning . "2" . c_putih . "] " . c_hijau . sprintf("%-33s", "Auto Withdraw Menu") . c_cyan . " │\n";
echo c_cyan . " └───────────────────────────────────────────┘\n";
echo c_putih . " Select Menu ➔ " . c_kuning;
$pilih_menu = trim(fgets(STDIN));

if ($pilih_menu === '2') {
    prosesWithdraw($hGet, $hPost, $apikey, $email);
    goto menu_awal;
}

$home = reqServer(host_url, "GET", [], $hGet);
preg_match_all('/href="https?:\/\/buxfaucet\.com\/\?faucet=([^"]+)"/i', $home, $matches);
$coins = array_values(array_unique($matches[1] ?? []));

$rekap = [];
foreach ($coins as $k) $rekap[strtoupper($k)] = 0.0;

if (!empty($coins)) {
    cetakBanner($apikey, $rekap);
    echo c_cyan . " ┌─[ " . c_hijau . "AVAILABLE COINS" . c_cyan . " ]\n";
    echo c_cyan . " └───────────────────────────────────────────┘\n";
    echo c_cyan . " [ " . c_hijau . "all" . c_cyan . " ] ➔ Rotasi semua coin\n";
    echo c_putih . " Select Option ➔ " . c_kuning;
$pilihan = trim(fgets(STDIN));

    echo "\n";
    if (strtolower($pilihan) === 'all') {
        while (true) {
            cetakBanner($apikey, $rekap);
            echo c_cyan . " ┌─[ " . c_hijau . "ROTASI 8 KOIN DIMULAI" . c_cyan . " ]──────────┐\n";
            foreach ($coins as $index => $coin) {
                $ku = strtoupper($coin);
                echo c_cyan . " │ " . c_ungu . sprintf("%-8s", "[$ku]") . " ➔ ";
                $res = claimCoin($coin, $hGet, $hPost, $apikey, $email);
                if (is_array($res) && $res['status']) {
                    $rekap[$ku] += $res['reward'];
                }
            }
            echo c_cyan . " └───────────────────────────────────────────┘\n";
            echo c_kuning . " [!] Putaran selesai. Menunggu 5 detik...\n" . c_reset;
            sleep(5);
        }
    } elseif (is_numeric($pilihan) && $pilihan >= 1 && $pilihan <= count($coins)) {
        $selected_coin = $coins[$pilihan - 1];
        $ku = strtoupper($selected_coin);
        cetakBanner($apikey, $rekap);
        while (true) {
            $res = claimCoin($selected_coin, $hGet, $hPost, $apikey, $email);
            if (is_array($res) && $res['status']) {
                $rekap[$ku] += $res['reward'];
                cetakBanner($apikey, $rekap);
            }
        }
    } else {
        echo c_merah . "[!] Pilihan tidak valid!\n";
        sleep(3); goto menu_awal;
    }

} else {
    echo c_merah . "Tidak ada koin yang ditemukan!\n";
    sleep(2); exit;
}
