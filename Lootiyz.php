<?php

error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$configFile = "lootiyz.json";

// ===== WARNA NEON KLASIK =====
const hitam  = "\033[38;5;232m";
const merah  = "\033[38;5;196m";
const hijau  = "\033[38;5;46m";
const kuning = "\033[38;5;226m";
const biru   = "\033[38;5;51m";
const cyan   = "\033[38;5;51m";
const ungu   = "\033[38;5;171m";
const pink   = "\033[38;5;213m";
const putih  = "\033[38;5;255m";
const abu    = "\033[38;5;245m";
const reset  = "\033[0m";

const my_url     = "https://api.lootizy.com/api/v2/user/my-details";
const get_data   = "https://api.lootizy.com/api/v2/user/faucet/get-data";
const cp_url     = "https://api.lootizy.com/api/v2/user/get-my-captcha";
const claim_url  = "https://api.lootizy.com/api/v2/user/faucet/verify";
const api_in     = "https://api.waryono.my.id/in.php";
const api_res    = "https://api.waryono.my.id/res.php";

function clear() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function req($url, $method = 'GET', $data = [], $headers = []) {
    $ch = curl_init();
    $final_headers = [];
    foreach ($headers as $header) {
        $final_headers[] = trim($header);
    }
    $options = [
        CURLOPT_URL            => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HEADER         => false,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_HTTPHEADER     => $final_headers,
        CURLOPT_CONNECTTIMEOUT => 30,
        CURLOPT_TIMEOUT        => 60,
        CURLOPT_ENCODING       => ''
    ];
    if (strtoupper($method) === 'POST') {
        $options[CURLOPT_POST]       = true;
        $options[CURLOPT_POSTFIELDS] = is_array($data) ? http_build_query($data) : $data;
    }
    curl_setopt_array($ch, $options);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

function timer($seconds, $prefix = "waiting...") {
    $wait_time   = (int)$seconds;
    $frames      = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'];
    $frame_count = count($frames);
    $cur_frame   = 0;
    
    while ($wait_time > 0) {
        $start = microtime(true);
        while ((microtime(true) - $start) < 1) {
            $h   = floor($wait_time / 3600);
            $m   = floor(($wait_time % 3600) / 60);
            $s   = $wait_time % 60;
            $fmt = sprintf('%02d:%02d:%02d', $h, $m, $s);
            echo putih . "^Z " . $prefix . " " . hijau . $fmt . " " . pink . $frames[$cur_frame] . "\r";
            usleep(100000);
            $cur_frame = ($cur_frame + 1) % $frame_count;
            if ((microtime(true) - $start) >= 1) break;
        }
        $wait_time--;
    }
    echo "\r" . str_repeat(" ", 50) . "\r";
}

function solve_captcha($base64, $apikey) {
    $headers = ["Content-Type: application/json"];
    $body = json_encode([
        "apikey"  => $apikey,
        "methods" => "lootizy",
        "type"    => "leasticon",
        "image"   => $base64,
        "json"    => 1
    ]);

    $request = req(api_in, "POST", $body, $headers);
    if (!$request) return "CONNECTION_ERROR";

    $fatal = ["ERROR_WRONG_METHOD", "ERROR_KEY_DOES_NOT_EXIST", "ERROR_ZERO_BALANCE", "ERROR_WRONG_USER_KEY"];
    foreach ($fatal as $err) {
        if (strpos($request, $err) !== false) return "FATAL:$err";
    }

    $json = json_decode($request, true);
    if (!isset($json["status"]) || $json["status"] != 1) return "SUBMIT_ERROR";
    
    $id = $json["request"];
    $retries = 0;
    
    while ($retries < 15) {
        sleep(4);
        $url    = api_res . "?apikey=$apikey&action=get&id=$id&json=1";
        $result = req($url, "GET", []);
        
        if (!$result) return "CONNECTION_ERROR";
        if (strpos($result, "CAPCHA_NOT_READY") !== false) {
            $retries++;
            continue;
        }

        $json = json_decode($result, true);
        if (isset($json["status"]) && $json["status"] == 1) {
            $res = $json["request"];
            preg_match('/x:(\d+),\s*y:(\d+)/', $res, $match);
            if (isset($match[1])) return ["x" => (int)$match[1], "y" => (int)$match[2]];
        }
        return "SOLVER_FAILED";
    }
    return "TIMEOUT";
}

function getConfig($configFile) {
    if (!file_exists($configFile)) {
        return [
            "apikey" => "", 
            "cookie" => "", 
            "user_agent" => "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
        ];
    }
    return json_decode(file_get_contents($configFile), true);
}

function saveConfig($configFile, $data) {
    file_put_contents($configFile, json_encode($data, JSON_PRETTY_PRINT));
}

function print_banner() {
    echo cyan . "==================================================\n";
    echo putih . "LOOTIZY AUTO FAUCET — COOKIE MODE\n";
    echo putih . "By Dev " . kuning . "MoneyMaker_w \n";
    echo cyan . "==================================================\n";
}

function print_menu() {
    echo putih . "\n[" . hijau . "1" . putih . "] Start Farming\n";
    echo putih . "[" . hijau . "2" . putih . "] Config Cookie\n";
    echo putih . "[" . hijau . "3" . putih . "] Config Provider\n";
    echo putih . "[" . merah . "0" . putih . "] Exit\n";
    echo putih . "==================================================\n";
    echo putih . "Choose : " . kuning;
}

function start_farming(&$config, $configFile) {
    $apikey = $config["apikey"];
    $coki   = $config["cookie"];
    $ua     = $config["user_agent"];

    if (empty($coki) || empty($apikey)) {
        echo merah . "\n[!] Cookie atau Provider belum diset. Config dulu di menu!\n";
        sleep(2);
        return;
    }

    $h_get = [
        "host: api.lootizy.com",
        "accept: application/json, text/plain, */*",
        "user-agent: ".$ua,
        "origin: https://lootizy.com",
        "referer: https://lootizy.com/",
        "cookie: ".$coki
    ];

    $h_post = [
        "host: api.lootizy.com",
        "user-agent: ".$ua,
        "accept: application/json, text/plain, */*",
        "content-type: application/json",
        "origin: https://lootizy.com",
        "referer: https://lootizy.com/",
        "cookie: ".$coki
    ];

    $my = req(my_url, "GET", [], $h_get);
    $my_json = json_decode($my, true);

    if (!isset($my_json["success"]) || $my_json["success"] !== true) {
        echo merah . "\n[!] Cookie expired / invalid.\n";
        echo kuning . "Update cookie dulu di menu [2].\n";
        sleep(2);
        return;
    }

    $user = $my_json["payload"]["username"] ?? "Unknown";
    $balance = $my_json["payload"]["balance"]["\$numberDecimal"] ?? "0";
    $todayFaucet = $my_json["payload"]["todayFaucet"] ?? 0;

    clear();
    print_banner();
    echo putih . "\nLogin  : " . hijau . $user . "\n";
    echo putih . "Balance: " . hijau . $balance . " COINS\n";
    echo cyan . "==================================================\n\n";

    while (true) {
        $get_raw = req(get_data, "GET", [], $h_get);
        $get = json_decode($get_raw, true);
        
        if (!isset($get["success"]) || $get["success"] !== true) {
            echo merah . "[!] Error get-data: " . ($get["message"] ?? "Unknown") . "\n";
            timer(5, "Retrying in...");
            continue;
        }
        
        $left = $get["left"] ?? 0;
        $status = $get["payload"]["status"] ?? "off";
        $limit = $get["payload"]["limit"] ?? 200;
        
        if ($todayFaucet >= $limit) {
            echo kuning . "\n[!] Daily limit reached ({$todayFaucet}/{$limit}).\n";
            echo putih . "[!] Auto-stop. Silakan coba lagi besok.\n";
            echo "Tekan Enter untuk kembali ke menu...";
            fgets(STDIN);
            return;
        }
        
        if ($status !== "on") {
            echo merah . "\n[!] Faucet is currently OFF.\n";
            echo putih . "[!] Auto-stop. Silakan coba lagi nanti.\n";
            echo "Tekan Enter untuk kembali ke menu...";
            fgets(STDIN);
            return;
        }

        if ($left > 0) {
            echo putih . "[*] Next claim in: " . hijau . $left . "s\n";
            timer($left, "waiting...");
        }

        echo putih . "[*] Solving captcha...\n";
        $cp = req(cp_url, "POST", "{}", $h_post);
        $cp_json = json_decode($cp, true);
        
        if (!isset($cp_json["success"]) || $cp_json["success"] !== true) {
            echo merah . "[!] Error captcha: " . ($cp_json["message"] ?? "Unknown") . "\n";
            timer(5, "Retrying in...");
            continue;
        }
        
        $uuids = $cp_json["uuids"] ?? [];
        $user_data = $cp_json["user"] ?? [];
        $img_data = $cp_json["imageData"] ?? "";
        
        preg_match('/base64,(.+)/', $img_data, $base64_match);
        $base64 = $base64_match[1] ?? null;

        $offer = $user_data["offersAvailable"] ?? null;
        $user_id = $user_data["_id"] ?? null;
        $nextBonus = $user_data["nextBonusId"] ?? null;

        if ($offer === null || $user_id === null || $nextBonus === null || $base64 === null) {
            echo merah . "[!] Data captcha tidak lengkap.\n";
            timer(5, "Retrying in...");
            continue;
        }

        $r = $offer % 100;
        $g = substr($nextBonus, $r, 2);
        $idx = intval($g);
        if (!isset($uuids[$idx])) $idx = 0;
        
        $claim_time_ms = round(microtime(true) * 1000);
        $data_string = "{$uuids[$idx]}-{$user_id}-{$claim_time_ms}";
        $generate = hash('sha256', $data_string);

        $solver = solve_captcha($base64, $apikey);
        
        if (is_string($solver) && strpos($solver, "FATAL:") === 0) {
            echo merah . "\n[!] Solver Error: " . substr($solver, 6) . "\n";
            echo putih . "[!] Auto-stop. Periksa API Key atau saldo Waryono.\n";
            echo "Tekan Enter untuk kembali ke menu...";
            fgets(STDIN);
            return;
        }
        
        if (!is_array($solver)) {
            echo merah . "[!] Solver gagal: $solver\n";
            timer(5, "Retrying in...");
            continue;
        }

        $x = $solver["x"];
        $y = $solver["y"];
        echo hijau . "[+] Captcha solved: x=$x, y=$y\n";

        $claim_data = json_encode([
            "captchaId" => $generate,
            "clickCoords" => ["x" => (int)$x, "y" => (int)$y],
            "claimTime" => $claim_time_ms
        ]);

        $claim = req(claim_url, "POST", $claim_data, $h_post);
        $claim_json = json_decode($claim, true);
        $msg = $claim_json["message"] ?? "Unknown";

        if (isset($claim_json["success"]) && $claim_json["success"] === true) {
            echo hijau . "[+] " . $msg . "\n";
            $balance = $claim_json["payload"]["balance"]["\$numberDecimal"] ?? $balance;
            $todayFaucet = $claim_json["payload"]["todayFaucet"] ?? ($todayFaucet + 1);
            
            echo putih . "Balance: " . hijau . $balance . " COINS\n";
            echo cyan . "==================================================\n\n";
            sleep(1); 
        } else {
            echo merah . "[!] Gagal claim: " . $msg . "\n";
            echo cyan . "==================================================\n\n";
            timer(10, "Retrying in...");
            continue;
        }
    }
}

$config = getConfig($configFile);

while (true) {
    clear();
    print_banner();
    print_menu();
    $choice = trim(fgets(STDIN));

    if ($choice === '1') {
        start_farming($config, $configFile);
    } elseif ($choice === '2') {
        clear();
        print_banner();
        echo putih . "\n[ CONFIG COOKIE ]\n";
        echo abu . "Contoh format:\n";
        echo kuning . "ss-cookie=s%3AYePR36UBXH4inDOSosRjZRpQZYIHR4JK.0AMqq6ySLvLO9fpTNxhrSbJWQDkpNGSuwGQMjIxGyvI\n\n";
        echo putih . "Paste Cookie : " . kuning;
        $new_cookie = trim(fgets(STDIN));
        if ($new_cookie) {
            $config["cookie"] = $new_cookie;
            saveConfig($configFile, $config);
            echo hijau . "\n[+] Cookie berhasil disimpan!\n";
            sleep(1.5);
        }
    } elseif ($choice === '3') {
        clear();
        print_banner();
        echo putih . "\n[ CONFIG PROVIDER ]\n";
        echo putih . "API Key Waryono : " . kuning; $new_key = trim(fgets(STDIN));
        echo putih . "User Agent      : " . kuning; $new_ua = trim(fgets(STDIN));
        
        if ($new_key) $config["apikey"] = $new_key;
        if ($new_ua) $config["user_agent"] = $new_ua;
        
        saveConfig($configFile, $config);
        echo hijau . "\n[+] Provider berhasil disimpan!\n";
        sleep(1.5);
    } elseif ($choice === '0') {
        echo merah . "\nKeluar dari program...\n" . reset;
        exit;
    } else {
        echo merah . "\n[!] Pilihan tidak valid.\n";
        sleep(1);
    }
}
