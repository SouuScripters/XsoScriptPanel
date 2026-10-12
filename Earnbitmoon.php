<?php
$_mudaPYHnh='RzlH7eOQxpDm';
// External telemetry/shutdown network block removed during protection.


$_rlbYclToF='aether-tool.com';
if(!$_rlbYclToF){exit;}
unset($_rlbYclToF);

error_reporting(1);
date_default_timezone_set("Asia/Jakarta");
$red="\33[1;31m";$white="\33[1;37m";$green="\33[1;32m";$yellow="\33[1;33m";$cyan="\33[1;36m";$purple="\33[1;35m";$bold="\33[1m";$reset="\33[0m";

$v = "1.9";
$svr = "epmpr";
$botname = "BONCEL-BOT";

function clear() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function getIpAndLocation() {
    $ch = curl_init("http://ip-api.com/json/?fields=query,city,country");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $response = curl_exec($ch);
    curl_close($ch);
    
    $data = json_decode($response, true);
    if ($data && isset($data['query'])) {
        return [
            "ip" => $data['query'],
            "location" => $data['city'] . ", " . $data['country']
        ];
    }
    return [
        "ip" => "Unknown IP",
        "location" => "Unknown Location"
    ];
}

function check_api_balance($provider = "alljrlwr") {
    global $user_agent;
    $api_balance = "N/A";
    if ($provider === "alljrlwr" && file_exists("Apikey_AllJrLwr") && trim(file_get_contents("Apikey_AllJrLwr")) !== "") {
        $key = trim(file_get_contents("Apikey_AllJrLwr"));
        $res = @json_decode(@file_get_contents("https://api.alljrlwr.my.id/res.php?action=userinfo&key=$key&json=1"), true);
        $api_balance = $res["balance"] ?? ($res["data"]["balance"] ?? "Ready");
    } elseif ($provider === "xevil" && file_exists("Apikey_Xevil") && trim(file_get_contents("Apikey_Xevil")) !== "") {
        $key_raw = trim(file_get_contents("Apikey_Xevil"));
        $parts = explode('|', $key_raw);
        $key = trim($parts[0]);
        $res = @json_decode(@file_get_contents("https://api.sctg.xyz/res.php?action=userinfo&key=$key&json=1"), true);
        $api_balance = $res["balance"] ?? ($res["data"]["balance"] ?? "Ready");
    } elseif ($provider === "waryono" && file_exists("Apikey_Waryono") && trim(file_get_contents("Apikey_Waryono")) !== "") {
        $key = trim(file_get_contents("Apikey_Waryono"));
        $res = @json_decode(@file_get_contents("https://api.waryono.my.id/balance.php?apikey=$key"), true);
        $api_balance = $res["balance"] ?? "Ready";
    }
    return $api_balance;
}

function banner($username = "AHD1905", $total_coins = "0", $coin_type = "COINS", $active_api = "NONE", $provider = "alljrlwr") {
    global $cyan, $bold, $white, $green, $yellow, $reset, $red;
    
    $clean_coins = rtrim(rtrim(number_format((float)$total_coins, 8, '.', ''), '0'), '.');
    if ($clean_coins == "" || $clean_coins == ".") $clean_coins = "0";
    $coins_text  = $clean_coins . " " . strtoupper($coin_type);
    
    $time_text   = date('H:i:s');
    $api_bal     = check_api_balance($provider);

    clear();
    echo "  " . $red . "███████╗" . $green . "██████╗ " . $yellow . "███╗   ███╗\n" . $reset;
    echo "  " . $red . "██╔════╝" . $green . "██╔══██╗" . $yellow . "████╗ ████║\n" . $reset;
    echo "  " . $red . "█████╗  " . $green . "██████╔╝" . $yellow . "██╔████╔██║\n" . $reset;
    echo "  " . $red . "██╔══╝  " . $green . "██╔══██╗" . $yellow . "██║╚██╔╝██║\n" . $reset;
    echo "  " . $red . "███████╗" . $green . "██████╔╝" . $yellow . "██║ ╚═╝ ██║\n" . $reset;
    echo $yellow . "  ════════════════════════════════════════════\n" . $reset;
    echo $white . "  Script Name : " . $green . "EARNBITMOON Bot\n";
    echo $white . "  Coded by    : " . $green . "AHD1905 " . $white . "| " . $cyan . "SCRIPTYXSOUU\n";
    echo $white . "  Engine      : " . $yellow . "BONCEL ENGINE\n";
    echo $yellow . "  ════════════════════════════════════════════\n" . $reset;
    
    echo $cyan . "  ┌────────────────────────────────────────┐\n";
    echo $white . "    Username : " . $green . $bold . $username . "\n";
    echo $white . "    Balance  : " . $yellow . $bold . $coins_text . "\n";
    echo $white . "    API Saldo: " . $yellow . $bold . $api_bal . "\n";
    echo $white . "    Time     : " . $white . $time_text . "\n";
    echo $white . "    API      : " . $green . strtoupper($active_api) . "\n";
    echo $cyan . "  └────────────────────────────────────────┘\n" . $reset;
}

function tmr($total_seconds, $active_api = "NONE", $provider = "alljrlwr") {
    $clocks = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚'];
    $start_time = time();
    $clock_count = count($clocks);
    $i = 0;
    while (true) {
        $elapsed_time = time() - $start_time;
        $remaining_seconds = max(0, $total_seconds - $elapsed_time);
        $minutes = floor($remaining_seconds / 60);
        $seconds = str_pad($remaining_seconds % 60, 2, "0", STR_PAD_LEFT);
        $clock = $clocks[$i % $clock_count];
        
        $lightning_count = ($i % 5) + 1;
        $lightning = str_repeat('⚡', $lightning_count);
        
        $i++;
        echo "\r   $clock \033[1;37mCountdown \033[1;31m$minutes:$seconds \033[1;33m$lightning          \r";
        if ($remaining_seconds <= 0) break;
        usleep(150000);
    }
}

function printTaskBox($title, $statusText) {
    global $cyan, $green, $white, $reset;
    echo $cyan . "  ┌────────────────────────────────────────┐\n";
    echo $white . "             " . $title . "             \n";
    echo $cyan . "  ├────────────────────────────────────────┤\n";
    echo $green . "           " . $statusText . "           \n";
    echo $cyan . "  └────────────────────────────────────────┘\n" . $reset;
}

function run($url, $ua, $data = false) {
$iphost = ["172.67.72.62","104.26.12.122","104.26.13.122"];
$iphost = $iphost[array_rand($iphost)];
    while (true) {
        $ch = curl_init();
        curl_setopt_array($ch, array(CURLOPT_URL => $url, CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true, CURLOPT_SSL_VERIFYPEER => 2, CURLOPT_RESOLVE => ["earnbitmoon.club:443:$iphost"], CURLOPT_DNS_SERVERS => '1.1.1.1,8.8.8.8', CURLOPT_SSL_VERIFYHOST => 2, CURLOPT_ACCEPT_ENCODING => 'gzip', CURLOPT_COOKIEFILE => "cookie.txt", CURLOPT_COOKIEJAR => "cookie.txt", CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 10));
        if ($data) {
            curl_setopt_array($ch, array(CURLOPT_POST => true, CURLOPT_POSTFIELDS => $data));
        }
        curl_setopt_array($ch, array(CURLOPT_HTTPHEADER => $ua, CURLOPT_HEADER => true));
        $response = curl_exec($ch);
        if ($response) {
            $response = substr($response, curl_getinfo($ch, CURLINFO_HEADER_SIZE));
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            return new class($response, $httpCode) {
              public $body, $code;
              function __construct($body, $code) {
                $this->body = $body;
                $this->code = $code;
              }
              function __toString() {
                return $this->body;
              }
            };
        } else {
           echo $war = "\33[1;" . rand(30,37) . "mCheck Your Connection!";
            sleep(1);
            echo "\r                                               \r";
            continue;
        }
    }
}

function hapus($files) {
    $list = explode(" ", $files);
    foreach ($list as $file) {
        if (file_exists($file)) {
            unlink($file);
        }
    }
}

function solve_captcha($user_agent, $cookie, $theme = ""){
if (stripos($theme, 'light') !== false) {
  $theme = 'light';
} elseif (stripos($theme, 'dark') !== false) {
  $theme = 'dark';
} else {
  $theme = 'dark';
}
$clocks = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚'];
$c_idx = 0;
do {
    $c_idx++;
    $clock = $clocks[$c_idx % count($clocks)];
    $uacap = array(
        "Host: earnbitmoon.club",
        "user-agent: $user_agent",
        "accept: */*",
        "content-type: multipart/form-data; boundary=----WebKitFormBoundarymX0AIrJNxhqTFCSo",
        "x-requested-with: XMLHttpRequest",
        "referer: https://earnbitmoon.club/?ref=1093541",
        "origin: https://earnbitmoon.club", 
        "cookie: $cookie"
    );
    echo "\r   $clock \033[1;33mBypassing... [$c_idx]\033[0m          \r";
    $timestamp = round(microtime(true) * 1000);
    $data = [
        "i" => 1,
        "a" => 1,
        "t" => $theme,
        "ts" => $timestamp
    ];
    $encodedData = base64_encode(json_encode($data));
    $postData1 = <<<DATA
------WebKitFormBoundarymX0AIrJNxhqTFCSo
Content-Disposition: form-data; name="payload"

$encodedData
------WebKitFormBoundarymX0AIrJNxhqTFCSo--
DATA;
    $res1 = base64_decode(run("https://earnbitmoon.club/system/libs/captcha/request.php", $uacap, $postData1));
    $dataxy = [
        ['x' => 24, 'y' => 19], ['x' => 67, 'y' => 27], ['x' => 83, 'y' => 31], ['x' => 142, 'y' => 23],
        ['x' => 167, 'y' => 17], ['x' => 241, 'y' => 28], ['x' => 298, 'y' => 23], ['x' => 206, 'y' => 21],
        ['x' => 254, 'y' => 26], ['x' => 294, 'y' => 27], ['x' => 191, 'y' => 19], ['x' => 26, 'y' => 26],
        ['x' => 55, 'y' => 23], ['x' => 115, 'y' => 15], ['x' => 149, 'y' => 16], ['x' => 303, 'y' => 13],
        ['x' => 245, 'y' => 12], ['x' => 195, 'y' => 17], ['x' => 135, 'y' => 19], ['x' => 85, 'y' => 11],
        ['x' => 28, 'y' => 16], ['x' => 37, 'y' => 25], ['x' => 96, 'y' => 22], ['x' => 161, 'y' => 28],
        ['x' => 237, 'y' => 18], ['x' => 303, 'y' => 7], ['x' => 25, 'y' => 11], ['x' => 80, 'y' => 13],
        ['x' => 290, 'y' => 9], ['x' => 240, 'y' => 17], ['x' => 191, 'y' => 23]
    ];
    for ($i = 0; $i < 5; $i++) {
        $dataxy[] = ['x' => rand(20, 300), 'y' => rand(5, 30)];
    }
    $index = array_rand($dataxy);
    $x = $dataxy[$index]['x'];
    $y = $dataxy[$index]['y'];
    $timestamp = round(microtime(true) * 1000);
    $data2 = [
        "i" => 1,
        "x" => $x,
        "y" => $y,
        "w" => 320,
        "a" => 2,
        "ts" => $timestamp
    ];
    $encodedData2 = base64_encode(json_encode($data2));
    $postData2 = <<<DATA
------WebKitFormBoundarymX0AIrJNxhqTFCSo
Content-Disposition: form-data; name="payload"

$encodedData2
------WebKitFormBoundarymX0AIrJNxhqTFCSo--
DATA;
    $res2 = run("https://earnbitmoon.club/system/libs/captcha/request.php", $uacap, $postData2);
    if($c_idx > 15) break;
} while (!isset($res2->code) || $res2->code != 200);
return ["x" => $x, "y" => $y];
}


function bonus($ua){
    $res = run("https://earnbitmoon.club/bonus.html", $ua);
    if (strpos($res, "Come back tomorrow !") !== false) {
        printTaskBox("DAILY BONUS", "Daily Bonus already Claimed !");
        sleep(2);
        return false;
    }

    $res = run("https://earnbitmoon.club/system/ajax.php?a=dailyBonus", $ua);

    if (strpos($res, 'SUCCESS') !== false) {
        $msg = explode('"', explode('<b>SUCCESS!<\/b> ', $res)[1])[0] ?? '';
        printTaskBox("DAILY BONUS", "Successfully | $msg");
        sleep(2);
        return true;
    } else {
        printTaskBox("DAILY BONUS", "Sorry Failed to Claim Daily Bonus!");
        sleep(2);
        return false;
    }
}


function Captcha_Solver_AllJrLwr($method, $sitekey, $pageurl) {
    if (!file_exists("Apikey_AllJrLwr") || trim(file_get_contents("Apikey_AllJrLwr")) === "") {
        echo "\33[1;31m [ERROR] Apikey AllJrLwr belum diatur!\n";
        return false;
    }
    $apikey = trim(file_get_contents("Apikey_AllJrLwr"));
    $host = "api.alljrlwr.my.id";
    $data = [
        'key'     => $apikey,
        'method'  => $method,
        'sitekey' => $sitekey,
        'url'     => $pageurl,
    ];

    $options = [
        "http" => [
            "header"  => "Content-Type: application/x-www-form-urlencoded\r\n",
            "method"  => "POST",
            "content" => http_build_query($data),
            "timeout" => 30,
        ]
    ];
    $context = stream_context_create($options);
    $requestFirst = @file_get_contents("https://$host/in.php", false, $context);

    if ($requestFirst === false || strpos($requestFirst, "OK|") === false) {
        echo "\r                                                       \r";
        echo "\33[1;31m   [ERROR] AllJrLwr Submit Failed: $requestFirst\033[0m\n";
        return false;
    }

    $captcha_id = str_replace("OK|", "", $requestFirst);
    $attempt_solver = 0;
    $clocks = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚'];
    while (true) {
        $attempt_solver++;
        $clock = $clocks[$attempt_solver % count($clocks)];
        echo "\r   $clock \033[1;33m[AllJrLwr] Mencoba resolver... [" . ($attempt_solver * 5) . "s]\033[0m          \r";
        
        $result = @file_get_contents("https://$host/res.php?key=$apikey&action=get&id=".$captcha_id);
        if ($result === false) return false;

        if ($result == 'CAPCHA_NOT_READY' || strpos($result, 'PROCESSING') !== false) {
            sleep(5);
            continue;
        } elseif (strpos($result, "OK|") !== false) {
            $token = explode("OK|", $result)[1];
            echo "\r                                                       \r";
            echo "\33[1;32m   [AllJrLwr SUCCESS]\033[0m\n";
            return $token;
        } else {
            echo "\r                                                       \r";
            echo "\33[1;31m   [ERROR] AllJrLwr Service: $result\033[0m\n";
            return false;
        }
    }
}


function Captcha_Solver_Xevil($method, $sitekey, $pageurl) {
    if (!file_exists("Apikey_Xevil") || trim(file_get_contents("Apikey_Xevil")) === "") {
        echo "\33[1;31m [ERROR] Apikey Xevil belum diatur!\n";
        return false;
    }
    
    $apikey_raw = trim(file_get_contents("Apikey_Xevil"));
    $parts = explode('|', $apikey_raw);
    $apikey = trim($parts[0]);
    $softid = isset($parts[1]) ? trim($parts[1]) : "SOFTID1078381261";

    $host = "api.sctg.xyz";
    $data = [
        'key'     => $apikey . "|" . $softid,
        'method'  => $method,
        'sitekey' => $sitekey,
        'pageurl' => $pageurl,
    ];

    $options = [
        "http" => [
            "header"  => "Content-Type: application/x-www-form-urlencoded\r\n",
            "method"  => "POST",
            "content" => http_build_query($data),
            "timeout" => 30,
        ]
    ];
    $context = stream_context_create($options);
    $requestFirst = @file_get_contents("https://$host/in.php", false, $context);

    if ($requestFirst === false || strpos($requestFirst, "OK|") === false) {
        echo "\r                                                       \r";
        echo "\33[1;31m   [ERROR] Xevil Submit Failed: $requestFirst\033[0m\n";
        return false;
    }

    $captcha_id = str_replace("OK|", "", $requestFirst);
    $attempt_solver = 0;
    $clocks = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚'];
    while (true) {
        $attempt_solver++;
        $clock = $clocks[$attempt_solver % count($clocks)];
        echo "\r   $clock \033[1;33m[Xevil] Mencoba resolver... [" . ($attempt_solver * 5) . "s]\033[0m          \r";
        
        $result = @file_get_contents("https://$host/res.php?key=$apikey&action=get&id=".$captcha_id);
        if ($result === false) return false;

        if ($result == 'CAPCHA_NOT_READY' || strpos($result, 'PROCESSING') !== false) {
            sleep(5);
            continue;
        } elseif (strpos($result, "OK|") !== false) {
            $token = explode("OK|", $result)[1];
            echo "\r                                                       \r";
            echo "\33[1;32m   [Xevil SUCCESS]\033[0m\n";
            return $token;
        } else {
            echo "\r                                                       \r";
            echo "\33[1;31m   [ERROR] Xevil Service: $result\033[0m\n";
            return false;
        }
    }
}


function Captcha_Solver_Waryono($method, $sitekey, $pageurl) {
    if (!file_exists("Apikey_Waryono") || trim(file_get_contents("Apikey_Waryono")) === "") {
        echo "\33[1;31m [ERROR] Apikey Waryono belum diatur!\n";
        return false;
    }
    $apikey = trim(file_get_contents("Apikey_Waryono"));
    $host = "api.waryono.my.id";

    $waryono_method = $method;
    if ($method === "rscaptcha" || $method === "rsicon") {
        $waryono_method = "rsicon";
    }

    $payload = [
        'apikey'  => $apikey,
        'methods' => $waryono_method,
        'json'    => 1
    ];

    if ($waryono_method === "rsicon") {
        return false; 
    } else {
        $payload['domain']  = "https://earnbitmoon.club";
        $payload['sitekey'] = $sitekey;
    }

    $options = [
        "http" => [
            "header"  => "Content-Type: application/json\r\n",
            "method"  => "POST",
            "content" => json_encode($payload),
            "timeout" => 30,
        ]
    ];
    $context = stream_context_create($options);
    $responseRaw = @file_get_contents("https://$host/in.php", false, $context);

    if ($responseRaw === false) {
        echo "\r                                                       \r";
        echo "\33[1;31m   [ERROR] Waryono Network Failed\033[0m\n";
        return false;
    }

    $resJson = json_decode($responseRaw, true);
    if (!isset($resJson['status']) || $resJson['status'] != 1) {
        $errReason = $resJson['request'] ?? $responseRaw;
        echo "\r                                                       \r";
        echo "\33[1;31m   [ERROR] Waryono Submit Failed: $errReason\033[0m\n";
        return false;
    }

    $captcha_id = $resJson['request'];
    $attempt_solver = 0;
    $clocks = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚'];

    while (true) {
        $attempt_solver++;
        $clock = $clocks[$attempt_solver % count($clocks)];
        echo "\r   $clock \033[1;33m[Waryono] Mencoba resolver... [" . ($attempt_solver * 5) . "s]\033[0m          \r";
        
        $pollingUrl = "https://$host/res.php?apikey=$apikey&id=$captcha_id&action=get&json=1";
        $pollRaw = @file_get_contents($pollingUrl);
        if ($pollRaw === false) {
            sleep(5);
            continue;
        }

        $pollJson = json_decode($pollRaw, true);
        $status = $pollJson['status'] ?? 0;
        $msg = $pollJson['request'] ?? '';

        if ($status == 0) {
            if ($msg === 'CAPCHA_NOT_READY' || strpos($msg, 'PROCESSING') !== false) {
                sleep(5);
                continue;
            } else {
                echo "\r                                                       \r";
                echo "\33[1;31m   [ERROR] Waryono Service: $msg\033[0m\n";
                return false;
            }
        } elseif ($status == 1) {
            $token = $msg;
            echo "\r                                                       \r";
            echo "\33[1;32m   [Waryono SUCCESS]\033[0m\n";
            return $token;
        }
        sleep(5);
    }
}


clear();
echo $cyan . "  ┌────────────────────────────────────────┐\n";
echo $white . "       " . $bold . "HALLO SELAMAT DATANG DI" . $cyan . "\n";
echo $white . "            " . $bold . "BONCEL ENGINE!" . $cyan . "\n";
echo $cyan . "  ├────────────────────────────────────────┤\n";
echo $white . "  Untuk membuat script ini membutuhkan\n";
echo $white . "  " . $green . "14 kali revisi" . $white . " dalam waktu " . $green . "9 hari" . $white . ".\n";
echo $white . "  Tolong hargai kerja author untuk tidak\n";
echo $white . "  di Decompile ulang " . $red . "🙏" . $reset . "\n";
echo $cyan . "  ├────────────────────────────────────────┤\n";
echo $white . "  Script ini " . $yellow . "98%" . $white . " tidak menggunakan Apikey\n";
echo $white . "  pihak ke-3 untuk solving captcha.\n";
echo $white . "  Apikey hanya sebagai tools pembantu jika\n";
echo $white . "  BONCEL ENGINE tidak bisa membypass\n";
echo $white . "  rsCaptcha dan Cloudflare.\n";
echo $cyan . "  ├────────────────────────────────────────┤\n";
echo $red . "  ⚠️ Peringatan!!! ⚠️" . $reset . "\n";
echo $white . "  Jika ingin tetap menggunakan script ini\n";
echo $white . "  dan terjadi kendala pada akun anda,\n";
echo $white . "  bukan tanggung jawab author.\n";
echo $cyan . "  ├────────────────────────────────────────┤\n";
echo $bold . $purple . "  By AHD1905 ❤️ BONCEL 😘                  \n";
echo $cyan . "  └────────────────────────────────────────┘\n" . $reset;

$konfirmasi = strtolower(trim(readline($white . "  Ingin masuk ke Panel Utama? (y/n) » " . $red)));
if ($konfirmasi !== 'y') {
    echo $yellow . "\n  Keluar dari program. Sampai jumpa lagi, Caplung!\n" . $reset;
    exit;
}

mainPanel:
clear();
$active_api_display = "ALLJRLWR API";
$active_provider = "alljrlwr";

banner("AHD1905", "0", "COINS", $active_api_display, $active_provider);
echo $cyan."  ┌────────────────────────────────────────┐\n";
echo $white . " " . $bold . "           P A N E L   U T A M A          \n";
echo $cyan."  ├────────────────────────────────────────┤\n";
echo $green . "  [1]" . $white . " Run Alljrlwr                          \n";
echo $green . "  [2]" . $white . " Run Xevil                             \n";
echo $green . "  [3]" . $white . " Run Waryono                           \n";
echo $green . "  [4]" . $white . " Config                                 \n";
echo $green . "  [5]" . $white . " Apikey Allrjlwr                        \n";
echo $green . "  [6]" . $white . " Apikey Xevil                           \n";
echo $green . "  [7]" . $white . " Apikey Waryono                         \n";
echo $green . "  [8]" . $white . " Hapus data                             \n";
echo $green . "  [0]" . $white . " Exit                                   \n";
echo $cyan."  └────────────────────────────────────────┘\n" . $reset;

$pilih_panel = readline($white."  Input Menu » " . $red);
switch($pilih_panel) {
    case "1":
        runBotEngine("alljrlwr");
        break;
    case "2":
        runBotEngine("xevil");
        break;
    case "3":
        runBotEngine("waryono");
        break;
    case "4":
        clear();
        banner("AHD1905", "0", "COINS", "CONFIG", "alljrlwr");
        $user_agent = readline($white."• Input User-Agent :\33[1;31m ");
        file_put_contents("UserAgent", $user_agent);
        $cookie = readline($white."• Input Cookie :\33[1;31m ");
        file_put_contents("Cookie", $cookie);
        echo $green."\n[SUCCESS] Config berhasil disimpan!\n";
        sleep(2);
        goto mainPanel;
        break;
    case "5":
        clear();
        banner("AHD1905", "0", "COINS", "ALLJRLWR", "alljrlwr");
        $apikey_all = readline($white."• Input Apikey Allrjlwr :\33[1;31m ");
        file_put_contents("Apikey_AllJrLwr", $apikey_all);
        echo $green."\n[SUCCESS] Apikey Allrjlwr berhasil disimpan!\n";
        sleep(2);
        goto mainPanel;
        break;
    case "6":
        clear();
        banner("AHD1905", "0", "COINS", "XEVIL", "xevil");
        $apikey_xevil = readline($white."• Input Apikey Xevil :\33[1;31m ");
        file_put_contents("Apikey_Xevil", $apikey_xevil);
        echo $green."\n[SUCCESS] Apikey Xevil berhasil disimpan!\n";
        sleep(2);
        goto mainPanel;
        break;
    case "7":
        clear();
        banner("AHD1905", "0", "COINS", "WARYONO", "waryono");
        $apikey_waryono = readline($white."• Input Apikey Waryono :\33[1;31m ");
        file_put_contents("Apikey_Waryono", $apikey_waryono);
        echo $green."\n[SUCCESS] Apikey Waryono berhasil disimpan!\n";
        sleep(2);
        goto mainPanel;
        break;
    case "8":
        hapus("UserAgent Cookie Apikey_AllJrLwr Apikey_Xevil Apikey_Waryono Apikey_Tertuyul cookie.txt");
        echo $red."\n[SUCCESS] Semua data config & apikey berhasil dihapus!\n";
        sleep(2);
        goto mainPanel;
        break;
    case "0":
        echo $yellow."\nKeluar dari program. Sampai jumpa!\n";
        exit;
    default:
        echo $red."\nPilihan salah!\n";
        sleep(1);
        goto mainPanel;
}

// 
function runBotEngine($provider) {
    global $red, $white, $green, $yellow, $cyan, $bold, $reset;

    if(!file_exists("UserAgent") || !file_exists("Cookie")){
      clear();
      banner("AHD1905", "0", "COINS", "NOT SET", $provider);
      echo $red."Config belum lengkap! Silakan atur Config terlebih dahulu di Menu 4.\n";
      sleep(3);
      return;
    }

    $user_agent = file_get_contents("UserAgent");
    $cookie = file_get_contents("Cookie");

    $ua = array("host: earnbitmoon.club","accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7","user-agent: $user_agent","content-type: application/x-www-form-urlencoded; charset=UTF-8","accept: application/json, text/javascript, */*; q=0.01","x-requested-with: XMLHttpRequest","cookie: $cookie");
    $res = run("https://earnbitmoon.club?ts=".time(),$ua);

    if(strpos($res, "Just a moment...")){
      echo $red."Cloudflare Detect, please update your Cookie .. \n";
      hapus("cookie cookie.txt");
      sleep(2);
      return;
    }
    $username = explode("'", explode("siteUserFullName: '",$res)[1])[0] ?? 'User';
    $balance = explode('<', explode('class="ebm-sb-hero-value" id="sidebarCoins">',$res)[1])[0] ?? '0';

    if(empty($username) || empty($balance)) {
      echo $red."Session expired, please update your cookie! \n";
      hapus("cookie cookie.txt");
      sleep(2);
      return;
    }

    $active_api_display = ($provider === "xevil") ? "XEVIL API" : (($provider === "waryono") ? "WARYONO API" : "ALLJRLWR API");
    $active_provider = $provider;

    banner($username, $balance, "COINS", $active_api_display, $active_provider);

    echo $cyan."  ┌────────────────────────────────────────┐\n";
    echo $white . " " . $bold . "            M E N U   B O T             \n";
    echo $cyan."  ├────────────────────────────────────────┤\n";
    echo $green . "  [1]" . $white . " Faucet                            \n";
    echo $green . "  [2]" . $white . " PTC Ads                         \n";
    echo $green . "  [3]" . $white . " Video Ads                       \n";
    echo $green . "  [4]" . $white . " Challenges                      \n";
    echo $green . "  [5]" . $white . " Claim Daily Bonus               \n";
    echo $green . "  [6]" . $white . " Kembali ke Panel Utama          \n";
    echo $cyan."  └────────────────────────────────────────┘\n" . $reset;

    $pil = readline($white."  Input Menu » " . $red);
    switch($pil) {
      case "1":
        clear();
        banner($username, $balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("MENU FAUCET", "Memuat Menu Faucet ($active_api_display)...");
        
        if ($active_provider === "xevil") {
            runFaucetXevil($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username);
        } elseif ($active_provider === "waryono") {
            runFaucetWaryono($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username);
        } else {
            runFaucetAllJrLwr($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username);
        }
        break;
      case "2":
        clear();
        banner($username, $balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("PTC ADS", "Menjalankan PTC Ads...");
        ptc($ua, $user_agent, $cookie, $active_provider);
        sleep(1);
        runBotEngine($provider);
        break;
      case "3":
        clear();
        banner($username, $balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("VIDEO ADS", "Menjalankan Video Ads...");
        $video = video($ua, $user_agent, $cookie, $active_provider);
        if($video == false){
          return;
        }
        sleep(1);
        runBotEngine($provider);
        break;
      case "4":
        clear();
        banner($username, $balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("CHALLENGES", "Menjalankan Challenges...");
        chl($ua, $active_api_display, $active_provider);
        sleep(1);
        runBotEngine($provider);
        break;
      case "5":
        clear();
        banner($username, $balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("DAILY BONUS", "Mengecek & Klaim Daily Bonus...");
        bonus($ua);
        sleep(1);
        runBotEngine($provider);
        break;
      case "6":
        return;
      default:
        printTaskBox("ERROR", "Pilihan salah: $pil");
        sleep(2);
        runBotEngine($provider);
    }
}


function runFaucetAllJrLwr($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username) {
    global $red, $white, $green, $reset;
    $attemp = 0; $ula = 0;
    
    while(true){
        hapus("cookie.txt");
        $res = run("https://earnbitmoon.club?ts=".time(),$ua);
        if(strpos($res, "Just a moment...")){
          echo $red."Cloudflare Detect, please update your Cookie .. \n";
          hapus("cookie cookie.txt");
          return;
        }
        $username = explode("'", explode("siteUserFullName: '",$res)[1])[0] ?? $username;
        $balance = explode('<', explode('class="ebm-sb-hero-value" id="sidebarCoins">',$res)[1])[0] ?? '0';
        if(empty($username) || empty($balance)) {
          $ula++;
          if($ula >= 5){
          echo $red."Session expired, please update your cookie! \n";
          hapus("cookie cookie.txt");
          return;
          } else {
            continue;
          }
        }

        $salt = explode("'", explode("const FAUCET_POV_SALT = '",$res)[1])[0] ?? '';
        $time = round(microtime(true) * 1000);
        $datString = explode("'", explode("const dataString = '",$res)[1])[0] ?? '';
        $data = $datString . $salt . $time;
        $povToken = base64_encode($data);

        $token = explode("'", explode("token: '",$res)[1])[0] ?? '';
        $wait = explode(',', explode('("#claimTime").countdown(',$res)[1])[0] ?? '';
        if (!empty($wait)){
            $remaining = (int) ($wait / 1000) - time();
            $rand = rand(5,15);
            tmr($remaining+$rand, $active_api_display, $active_provider);
            continue;
        } 
        if ($attemp >= 100){
          echo $red."Timer to avoid Suspension by the site !!\r";
          sleep(5);
          tmr(60, $active_api_display, $active_provider);
          $attemp = 0;
          echo "\r                                                          \r";
          continue;
        }

        $cap = explode(';', explode('var captchaType = ',$res)[1])[0] ?? '0';
        if($cap === "0" || $cap === 0){
            $result = solve_captcha($user_agent, $cookie, $theme="dark");
            echo "\r                                                       \r";
            echo $green . "   [SUCCESS]\n" . $reset;
            sleep(1);

            $data = "captcha_type=0&a=getFaucet&token=$token&captcha=3&challenge=false&response=false&ic-hf-id=1&ic-hf-se=".$result["x"]."%2C".$result["y"]."%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "1" || $cap === 1) {
            echo $white."Captcha Type :".$green." Hcaptcha \n";
            $method = "hcaptcha";
            $sitekey = "1f3d0bc1-e639-4597-a1f0-01b72f5c2bcf";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_AllJrLwr($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=1&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "2" || $cap === 2){
            echo $white."Captcha Type :".$green." Turnstile \n";
            $method = "turnstile";
            $sitekey = "0x4AAAAAAAUpl4YpF0xdcm9r";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_AllJrLwr($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=2&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        }

        $res_faucet = json_decode(run("https://earnbitmoon.club/system/ajax.php",$ua,$data));
        echo "\r                                                     \r";
        if(isset($res_faucet->status) && ($res_faucet->status == 200 || $res_faucet->status == "200")){
            $number = $res_faucet->number ?? '';
            $reward = $res_faucet->reward ?? '';
            $current_balance = bln($ua);
            banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
            printTaskBox("FAUCET SUCCESS", "Lucky: $number | Reward: $reward Coins");
            $attemp++;
        } else {
            $err = $res_faucet->message ?? 'Unknown error';
            printTaskBox("FAUCET ERROR", strip_tags($err));
            sleep(5);
        }
    }
}


function runFaucetXevil($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username) {
    global $red, $white, $green, $reset;
    $attemp = 0; $ula = 0;
    
    while(true){
        hapus("cookie.txt");
        $res = run("https://earnbitmoon.club?ts=".time(),$ua);
        if(strpos($res, "Just a moment...")){
          echo $red."Cloudflare Detect, please update your Cookie .. \n";
          hapus("cookie cookie.txt");
          return;
        }
        $username = explode("'", explode("siteUserFullName: '",$res)[1])[0] ?? $username;
        $balance = explode('<', explode('class="ebm-sb-hero-value" id="sidebarCoins">',$res)[1])[0] ?? '0';
        if(empty($username) || empty($balance)) {
          $ula++;
          if($ula >= 5){
          echo $red."Session expired, please update your cookie! \n";
          hapus("cookie cookie.txt");
          return;
          } else {
            continue;
          }
        }

        $salt = explode("'", explode("const FAUCET_POV_SALT = '",$res)[1])[0] ?? '';
        $time = round(microtime(true) * 1000);
        $datString = explode("'", explode("const dataString = '",$res)[1])[0] ?? '';
        $data = $datString . $salt . $time;
        $povToken = base64_encode($data);

        $token = explode("'", explode("token: '",$res)[1])[0] ?? '';
        $wait = explode(',', explode('("#claimTime").countdown(',$res)[1])[0] ?? '';
        if (!empty($wait)){
            $remaining = (int) ($wait / 1000) - time();
            $rand = rand(5,15);
            tmr($remaining+$rand, $active_api_display, $active_provider);
            continue;
        } 
        if ($attemp >= 100){
          echo $red."Timer to avoid Suspension by the site !!\r";
          sleep(5);
          tmr(60, $active_api_display, $active_provider);
          $attemp = 0;
          echo "\r                                                          \r";
          continue;
        }

        $cap = explode(';', explode('var captchaType = ',$res)[1])[0] ?? '0';
        if($cap === "0" || $cap === 0){
            $result = solve_captcha($user_agent, $cookie, $theme="dark");
            echo "\r                                                       \r";
            echo $green . "   [SUCCESS]\n" . $reset;
            sleep(1);

            $data = "captcha_type=0&a=getFaucet&token=$token&captcha=3&challenge=false&response=false&ic-hf-id=1&ic-hf-se=".$result["x"]."%2C".$result["y"]."%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "1" || $cap === 1) {
            echo $white."Captcha Type :".$green." Hcaptcha \n";
            $method = "hcaptcha";
            $sitekey = "1f3d0bc1-e639-4597-a1f0-01b72f5c2bcf";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_Xevil($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=1&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "2" || $cap === 2){
            echo $white."Captcha Type :".$green." Turnstile \n";
            $method = "turnstile";
            $sitekey = "0x4AAAAAAAUpl4YpF0xdcm9r";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_Xevil($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=2&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        }

        $res_faucet = json_decode(run("https://earnbitmoon.club/system/ajax.php",$ua,$data));
        echo "\r                                                     \r";
        if(isset($res_faucet->status) && ($res_faucet->status == 200 || $res_faucet->status == "200")){
            $number = $res_faucet->number ?? '';
            $reward = $res_faucet->reward ?? '';
            $current_balance = bln($ua);
            banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
            printTaskBox("FAUCET SUCCESS", "Lucky: $number | Reward: $reward Coins");
            $attemp++;
        } else {
            $err = $res_faucet->message ?? 'Unknown error';
            printTaskBox("FAUCET ERROR", strip_tags($err));
            sleep(5);
        }
    }
}


function runFaucetWaryono($ua, $user_agent, $cookie, $active_api_display, $active_provider, $username) {
    global $red, $white, $green, $reset;
    $attemp = 0; $ula = 0;
    
    while(true){
        hapus("cookie.txt");
        $res = run("https://earnbitmoon.club?ts=".time(),$ua);
        if(strpos($res, "Just a moment...")){
          echo $red."Cloudflare Detect, please update your Cookie .. \n";
          hapus("cookie cookie.txt");
          return;
        }
        $username = explode("'", explode("siteUserFullName: '",$res)[1])[0] ?? $username;
        $balance = explode('<', explode('class="ebm-sb-hero-value" id="sidebarCoins">',$res)[1])[0] ?? '0';
        if(empty($username) || empty($balance)) {
          $ula++;
          if($ula >= 5){
          echo $red."Session expired, please update your cookie! \n";
          hapus("cookie cookie.txt");
          return;
          } else {
            continue;
          }
        }

        $salt = explode("'", explode("const FAUCET_POV_SALT = '",$res)[1])[0] ?? '';
        $time = round(microtime(true) * 1000);
        $datString = explode("'", explode("const dataString = '",$res)[1])[0] ?? '';
        $data = $datString . $salt . $time;
        $povToken = base64_encode($data);

        $token = explode("'", explode("token: '",$res)[1])[0] ?? '';
        $wait = explode(',', explode('("#claimTime").countdown(',$res)[1])[0] ?? '';
        if (!empty($wait)){
            $remaining = (int) ($wait / 1000) - time();
            $rand = rand(5,15);
            tmr($remaining+$rand, $active_api_display, $active_provider);
            continue;
        } 
        if ($attemp >= 100){
          echo $red."Timer to avoid Suspension by the site !!\r";
          sleep(5);
          tmr(60, $active_api_display, $active_provider);
          $attemp = 0;
          echo "\r                                                          \r";
          continue;
        }

        $cap = explode(';', explode('var captchaType = ',$res)[1])[0] ?? '0';
        if($cap === "0" || $cap === 0){
            $result = solve_captcha($user_agent, $cookie, $theme="dark");
            echo "\r                                                       \r";
            echo $green . "   [SUCCESS]\n" . $reset;
            sleep(1);

            $data = "captcha_type=0&a=getFaucet&token=$token&captcha=3&challenge=false&response=false&ic-hf-id=1&ic-hf-se=".$result["x"]."%2C".$result["y"]."%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "1" || $cap === 1) {
            echo $white."Captcha Type :".$green." Hcaptcha \n";
            $method = "hcaptcha";
            $sitekey = "1f3d0bc1-e639-4597-a1f0-01b72f5c2bcf";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_Waryono($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=1&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        } elseif ($cap === "2" || $cap === 2){
            echo $white."Captcha Type :".$green." Turnstile \n";
            $method = "turnstile";
            $sitekey = "0x4AAAAAAAUpl4YpF0xdcm9r";
            $pageurl = "https://earnbitmoon.club/";
            
            $captcha = Captcha_Solver_Waryono($method, $sitekey, $pageurl);

            if($captcha === false){
              tmr(5, $active_api_display, $active_provider);
              continue;
            }
            $data = "captcha_type=2&a=getFaucet&token=$token&captcha=3&challenge=false&response=$captcha&ic-hf-id=false&ic-hf-se=%2C%2C320&ic-hf-hp=&hp_field=&hash_xx_token=$povToken";
        }

        $res_faucet = json_decode(run("https://earnbitmoon.club/system/ajax.php",$ua,$data));
        echo "\r                                                     \r";
        if(isset($res_faucet->status) && ($res_faucet->status == 200 || $res_faucet->status == "200")){
            $number = $res_faucet->number ?? '';
            $reward = $res_faucet->reward ?? '';
            $current_balance = bln($ua);
            banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
            printTaskBox("FAUCET SUCCESS", "Lucky: $number | Reward: $reward Coins");
            $attemp++;
        } else {
            $err = $res_faucet->message ?? 'Unknown error';
            printTaskBox("FAUCET ERROR", strip_tags($err));
            sleep(5);
        }
    }
}

function bln($ua) {
  $res = run("https://earnbitmoon.club?ts=".time(),$ua);
  $balance = explode('<', explode('class="ebm-sb-hero-value" id="sidebarCoins">',$res)[1])[0];
  return $balance ?: '0';
}

function ptc($ua, $user_agent, $cookie, $active_provider){
global $green, $reset;
$username = explode("'", explode("siteUserFullName: '",run("https://earnbitmoon.club?ts=".time(),$ua))[1])[0];
$active_api_display = ($active_provider === "xevil") ? "XEVIL API" : (($active_provider === "waryono") ? "WARYONO API" : "ALLJRLWR API");

while(true){
$res = run("https://earnbitmoon.club/ptc.html",$ua);
preg_match_all('/<div\s+class=["\']website_block["\']\s+id=["\'](\d+)["\']>/i', $res, $match);
$match = $match[1] ?? [];
if(empty($match[0])){
  printTaskBox("PTC ADS", "No PTC Ads Available");
  return false;
}
$id = $match[0];
$key = explode("'", explode('&key=',$res)[1])[0] ?? '';

$salt = explode("'", explode("const POV_SALT = '",$res)[1])[0] ?? '';
$time = round(microtime(true) * 1000);
$data = $id . $salt . $time;
$povToken = base64_encode($data);

  $res = run("https://earnbitmoon.club/surf.php?sid=$id&key=$key",$ua);
  if(strpos($res, "static/ptc/errors/nopage.html")){
    printTaskBox("PTC ADS", "Page no longer available");
    return false;
  }
  if(stripos($res, "Session expired")){
  printTaskBox("SESSION", "Session expired, update cookie!");
  hapus("cookie cookie.txt");
  return false;
  }
  $wait = explode(';', explode("var secs = ",$res)[1])[0] ?? '5';
  $token = explode("'", explode("var token = '",$res)[1])[0] ?? '';
  if(!$wait) continue;
  
  clear();
  banner($username, bln($ua), "COINS", $active_api_display, $active_provider);
  printTaskBox("PTC ADS", "Sedang Mengerjakan Task PTC...");
  
  tmr((int)$wait, $active_api_display, $active_provider);
  
  $result = solve_captcha($user_agent, $cookie);
  echo "\r                                                       \r";
  echo $green . "   [SUCCESS]\n" . $reset;
  sleep(1);
  
  $uaclaim = array("host: earnbitmoon.club","user-agent: $user_agent","content-type: application/x-www-form-urlencoded; charset=UTF-8","accept: application/json, text/javascript, */*; q=0.01","x-requested-with: XMLHttpRequest","referer: https://earnbitmoon.club/surf.php?sid=$id&key=$key","cookie: $cookie");
  $data = "a=proccessPTC&data=$id&token=$token&ic-hf-id=1&ic-hf-se=".$result["x"].",".$result["y"].",320&ic-hf-hp=&tcpw_hash=$povToken";
  $res = run("https://earnbitmoon.club/system/ajax.php",$uaclaim,$data);
  echo "\r                                                           \r";
$data_json = json_decode($res, true);
if (isset($data_json['message'])) {
    $msg = $data_json['message'];
    if (strpos($msg, 'alert-success') !== false) {
        $text = trim(strip_tags(explode('</b>', $msg)[1] ?? $msg));
        $current_balance = bln($ua);
        banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("PTC SUCCESS", $text);
    } else {
        $text = trim(strip_tags($msg));
        printTaskBox("PTC ERROR", $text);
        sleep(1);
    }
}
}
}

function video($ua, $user_agent, $cookie, $active_provider){
global $green, $reset;
$username = explode("'", explode("siteUserFullName: '",run("https://earnbitmoon.club?ts=".time(),$ua))[1])[0];
$active_api_display = ($active_provider === "xevil") ? "XEVIL API" : (($active_provider === "waryono") ? "WARYONO API" : "ALLJRLWR API");

while(true){
$res = run("https://earnbitmoon.club/video.html", $ua);
preg_match_all('/[?&]vid=([^"&\'\s<>]+)/i', $res, $matches);
$ids = array_values(array_unique($matches[1] ?? []));
if(empty($ids[0])){
  printTaskBox("VIDEO ADS", "No Video Ads Available");
  return false;
}
$res = run("https://earnbitmoon.club/surf_video.php?vid=$ids[0]",$ua);
if(stripos($res, "Session expired")){
  printTaskBox("SESSION", "Session expired, update cookie!");
  hapus("cookie cookie.txt");
  return false;
}

$start = strpos($res, 'initVideoWatcher(');
if ($start !== false) {
    $substr = substr($res, $start);
    $end = strpos($substr, '</script>');
    $scriptBlock = substr($substr, 0, $end);

    preg_match_all('/[\'"]([^\'"]+)[\'"]|(\d+)/', $scriptBlock, $allMatches);

    $params = [];
    foreach ($allMatches[0] as $match) {
        $clean = trim($match, "\"'");
        if ($clean !== '') {
            $params[] = $clean;
        }
    }
    $duration = $params[0] ?? '5';
    $campaignId = $params[1] ?? '';
    $token = $params[2] ?? '';
    $videoId = $params[3] ?? '';
} else {
    printTaskBox("ERROR", "Error 404 not found !");
    return false;
}

$salt = explode("'", explode("const POV_SALT = '",$res)[1])[0] ?? '';
$time = round(microtime(true) * 1000);
$data = $videoId . $salt . $time;
$povToken = base64_encode($data);

clear();
banner($username, bln($ua), "COINS", $active_api_display, $active_provider);
printTaskBox("VIDEO ADS", "Sedang Mengerjakan Task Video...");

tmr((int)$duration, $active_api_display, $active_provider);

$result = solve_captcha($user_agent, $cookie, $theme="light");
echo "\r                                                       \r";
echo $green . "   [SUCCESS]\n" . $reset;
sleep(1);

$uaclaim = array("host: earnbitmoon.club","user-agent: $user_agent","content-type: application/x-www-form-urlencoded; charset=UTF-8","accept: application/json, text/javascript, */*; q=0.01","x-requested-with: XMLHttpRequest","referer: https://earnbitmoon.club/surf_video.php?vid=$campaignId","cookie: $cookie");
$data = "a=proccess_video&id=$campaignId&token=$token&ic-hf-id=1&ic-hf-se=".$result["x"].",".$result["y"].",319.995&ic-hf-hp=&videow_hash=$povToken";
$res = run("https://earnbitmoon.club/system/ajax.php", $ua, $data);

$data_json = json_decode($res, true);
if (isset($data_json['message'])) {
    $msg = $data_json['message'];
    if (strpos($msg, 'alert-success') !== false) {
        $text = trim(strip_tags(explode('</b>', $msg)[1] ?? $msg));
        $text = trim(str_replace("Redirecting", "",$text));
        $current_balance = bln($ua);
        banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("VIDEO SUCCESS", $text);
    } else {
        $text = trim(strip_tags($msg));
        printTaskBox("VIDEO ERROR", $text);
        sleep(1);
    }
}
}
}

function chl($ua, $active_api_display, $active_provider){
$username = explode("'", explode("siteUserFullName: '",run("https://earnbitmoon.club?ts=".time(),$ua))[1])[0];
while(true){
$res = run("https://earnbitmoon.club/challenges.html",$ua);
if(empty($res)){
    printTaskBox("CHALLENGES", "Failed to fetch page, retrying...");
    sleep(3);
    continue;
}

if (preg_match('/onclick="claimCL\(\'?(\d+)\'?\)"/i', $res, $m)) {
    $butID = $m[1];
    
    clear();
    banner($username, bln($ua), "COINS", $active_api_display, $active_provider);
    printTaskBox("CHALLENGES", "Sedang Mengerjakan Task Challenges...");
    
    $claimRes = run("https://earnbitmoon.club/system/ajax.php?a=claimChallenge&rID=$butID", $ua);
    $json = json_decode($claimRes, true);
    
    if (!$json) {
        printTaskBox("CHALLENGES", "Invalid JSON response.");
        sleep(3);
        return false;
    }

    $type = $json["type"] ?? "unknown";
    $msg = $json["message"] ?? "No message";
    $text = trim(strip_tags(explode('</b>', $msg)[1] ?? $msg));

    if (stripos($type, 'success') !== false) {
        $current_balance = bln($ua);
        banner($username, $current_balance, "COINS", $active_api_display, $active_provider);
        printTaskBox("CHALLENGE SUCCESS", $text);
    } else {
        printTaskBox("CHALLENGE ERROR", "$type - $text");
    }
    sleep(3);
} else {
    printTaskBox("CHALLENGES", "No Challenges Can Be Claimed !");
    sleep(3);
    return false;
}
}
}
