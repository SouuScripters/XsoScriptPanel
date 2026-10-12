<?php
error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$configFile = "payub.json";
$apiKeyFile = "payubapi.txt";

define('version', '2.0');
define('script_name', 'PAYUP.VIDEO');
define('host', 'https://payup.video');
define('in_api', 'https://sctg.xyz/in.php');
define('res_api', 'https://sctg.xyz/res.php');
define('waryono_in', 'https://api.waryono.my.id/in.php');
define('waryono_res', 'https://api.waryono.my.id/res.php');
define('default_ua', 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36');

function clear() {
    (PHP_OS == "Linux") ? system('clear') : pclose(popen('cls', 'w'));
}

function skibidixxx($url, $method = 'GET', $data = [], $headers = []) {
    while (true) {
        $ch = curl_init();
        $options = [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYHOST => 0,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_CONNECTTIMEOUT => 999,
            CURLOPT_TIMEOUT => 999
        ];
        if (strtoupper($method) === 'POST') {
            $options[CURLOPT_POST] = true;
            $options[CURLOPT_POSTFIELDS] = $data;
        }
        if (!empty($headers)) {
            $options[CURLOPT_HTTPHEADER] = $headers;
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

function timer($seconds, $prefix = "[!] please wait") {
    $wait_time = (int)$seconds;
    while ($wait_time > 0) {
        $hours = floor($wait_time / 3600);
        $minutes = floor(($wait_time % 3600) / 60);
        $seconds_left = $wait_time % 60;
        $time_formatted = sprintf('%02d:%02d:%02d', $hours, $minutes, $seconds_left);
        echo "$prefix $time_formatted\r";
        sleep(1);
        $wait_time--;
    }
    echo "\r                                     \r";
}

function fix_b64($main_b64) {
    $main_b64 = str_replace(['с', 'а'], ['c', 'a'], $main_b64);
    if (strpos($main_b64, 'base64,') !== false) {
        $parts = explode('base64,', $main_b64);
        $main_b64 = trim(end($parts));
    }
    $main_b64 = preg_replace('/\s+/', '', $main_b64);
    return trim($main_b64);
}

function xevilSolver($base64, $apikey) {
    $base64 = fix_b64($base64);
    $data = [
        'key' => $apikey,
        'method' => 'buxmoney',
        'body' => $base64
    ];
    $postData = http_build_query($data);
    $headers = ['Content-Type: application/x-www-form-urlencoded'];
    
    $request = skibidixxx(in_api, "POST", $postData, $headers);
    if (!preg_match('/(?:OK|1)\|(\d+)/i', $request, $match)) {
        return [];
    }
    
    $taskId = trim($match[1]);
    if (empty($taskId)) return [];
    
    $maxWait = 300;
    $pollInterval = 5;
    $startTime = time();

    while ((time() - $startTime) < $maxWait) {
        sleep($pollInterval);
        $pollParams = [
            'key' => $apikey,
            'id' => $taskId,
            'action' => 'get'
        ];
        $pollUrl = res_api . "?" . http_build_query($pollParams);
        $pollResponse = skibidixxx($pollUrl, "GET", [], []);

        if (strpos($pollResponse, 'NOT_READY') === false && strpos($pollResponse, 'PROCESSING') === false) {
            $res = $pollResponse;
            $points = [];
            preg_match_all('/x:(\d+),y:(\d+)/', $res, $matches, PREG_SET_ORDER);
            foreach ($matches as $m) {
                $points[] = ["x" => $m[1], "y" => $m[2]];
            }
            if (empty($points)) {
                preg_match_all('/x[^\d]*(\d+)[^\d]*y[^\d]*(\d+)/i', $res, $matches, PREG_SET_ORDER);
                foreach ($matches as $m) {
                    $points[] = ["x" => $m[1], "y" => $m[2]];
                }
            }
            return $points;
        }
    }
    return [];
}

function waryonoSolver($base64, $apikey) {
    $base64 = fix_b64($base64);
    $headers = ["Content-Type: application/json"];
    $body = json_encode([
        "apikey" => $apikey,
        "methods" => "payup",
        "image" => $base64,
        "json" => 1
    ]);
    
    $request = skibidixxx(waryono_in, "POST", $body, $headers);
    $json = json_decode($request, true);
    if (!isset($json["request"])) return [];
    $id = $json["request"];
    
    $maxWait = 60;
    $pollInterval = 3;
    $startTime = time();

    while ((time() - $startTime) < $maxWait) {
        sleep($pollInterval);
        $url = waryono_res . "?apikey=" . $apikey . "&action=get&id=" . $id . "&json=1";
        $result = skibidixxx($url, "GET", []);
        
        if (strpos($result, "ERROR_CAPTCHA_UNSOLVABLE") !== false) {
            return [];
        }
        
        if (strpos($result, "CAPCHA_NOT_READY") !== false || strpos($result, "ERROR_SOLVE_PENDING") !== false) {
            continue;
        }
        
        $jsonRes = json_decode($result, true);
        if (isset($jsonRes["request"])) {
            $res = $jsonRes["request"];
            $points = [];
            
            $parts = explode(', ', $res);
            foreach ($parts as $part) {
                if (preg_match('/x:(\d+),y:(\d+)/', $part, $m)) {
                    $points[] = ["x" => $m[1], "y" => $m[2]];
                }
            }
            if (empty($points)) {
                preg_match_all('/x:(\d+),y:(\d+)/', $res, $matches, PREG_SET_ORDER);
                foreach ($matches as $m) {
                    $points[] = ["x" => $m[1], "y" => $m[2]];
                }
            }
            return $points;
        }
    }
    return [];
}

function setupApiKey($apiKeyFile, $type) {
    $keys = file_exists($apiKeyFile) ? json_decode(file_get_contents($apiKeyFile), true) : [];
    
    if ($type === 'apikey_xevil') {
        echo "\033[1;36m[?] Masukkan API Key XEVIL: \033[0m";
        $keys['apikey_xevil'] = trim(fgets(STDIN));
    } elseif ($type === 'apikey_waryono') {
        echo "\033[1;36m[?] Masukkan API Key WARYONO: \033[0m";
        $keys['apikey_waryono'] = trim(fgets(STDIN));
    }
    
    file_put_contents($apiKeyFile, json_encode($keys, JSON_PRETTY_PRINT));
    echo "\033[1;32m[✓] API Key berhasil disimpan ke $apiKeyFile!\033[0m\n\n";
    sleep(2);
}

function setupCookie($configFile) {
    $existing = file_exists($configFile) ? json_decode(file_get_contents($configFile), true) : [];
    echo "\033[1;36m[?] Masukkan Cookie: \033[0m";
    $existing['cookie'] = trim(fgets(STDIN));
    if (!isset($existing['user_agent']) || empty($existing['user_agent'])) {
        $existing['user_agent'] = default_ua;
    }
    file_put_contents($configFile, json_encode($existing, JSON_PRETTY_PRINT));
    echo "\033[1;32m[✓] Cookie berhasil disimpan!\033[0m\n\n";
    sleep(2);
}

function deleteConfig($configFile, $apiKeyFile) {
    if (file_exists($configFile)) unlink($configFile);
    if (file_exists($apiKeyFile)) unlink($apiKeyFile);
    echo "\033[1;32m[✓] Semua file konfigurasi & API Key berhasil dihapus!\033[0m\n\n";
    sleep(2);
}

function banner() {
    echo "\033[1;35m=========================================\033[0m\n";
    echo "\033[1;33m██████╗  █████╗ ██╗   ██╗██╗   ██╗██████╗  \033[0m\n";
    echo "\033[1;33m██╔══██╗██╔══██╗╚██╗ ██╔╝██║   ██║██╔══██╗ \033[0m\n";
    echo "\033[1;36m██████╔╝███████║ ╚████╔╝ ██║   ██║██████╔╝ \033[0m\n";
    echo "\033[1;36m██╔═══╝ ██╔══██║  ╚██╔╝  ██║   ██║██╔═══╝  \033[0m\n";
    echo "\033[1;32m██║     ██║  ██║   ██║   ╚██████╔╝██║      \033[0m\n";
    echo "\033[1;35m=========================================\033[0m\n";
    echo "\033[1;37m Script Name  : \033[1;32m" . script_name . " YouTube Bot\033[0m\n";
    echo "\033[1;37m Coded by     : \033[1;36mAHD1905\033[0m | \033[1;35mSCRIPTYXSOUU\033[0m\n";
    echo "\033[1;37m Engine       : \033[1;33mBONCEL ENGINE\033[0m\n";
    echo "\033[1;35m=========================================\033[0m\n\n";
}

main_menu:
clear();
banner();
echo "\033[1;35m┌─────────────────────────────────────────┐\033[0m\n";
echo "\033[1;35m│\033[0m          \033[1;36mPANEL KONTROL UTAMA\033[0m            \033[1;35m│\033[0m\n";
echo "\033[1;35m├─────────────────────────────────────────┤\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m1.\033[1;37m Run XEVIL                             \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m2.\033[1;37m Run WARYONO                           \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m3.\033[1;37m API KEY XEVIL                         \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m4.\033[1;37m API KEY WARYONO                       \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m5.\033[1;37m COOKIE                                \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m6.\033[1;37m Hapus CONFIG                          \033[1;35m│\033[0m\n";
echo "\033[1;35m│\033[0m \033[1;33m0.\033[1;37m Exit                                  \033[1;35m│\033[0m\n";
echo "\033[1;35m└─────────────────────────────────────────┘\033[0m\n\n";
echo "\033[1;32m[?] Pilih Menu [0-6]: \033[0m";
$pilih = trim(fgets(STDIN));

$solver_mode = "";
if ($pilih === '1') {
    $solver_mode = "xevil";
} elseif ($pilih === '2') {$solver_mode = "waryono";
} elseif ($pilih === '3') {
    clear();
    banner();
    setupApiKey($apiKeyFile, 'apikey_xevil');
    goto main_menu;
} elseif ($pilih === '4') {
    clear();
    banner();
    setupApiKey($apiKeyFile, 'apikey_waryono');
    goto main_menu;
} elseif ($pilih === '5') {
    clear();
    banner();
    setupCookie($configFile);
    goto main_menu;
} elseif ($pilih === '6') {
    clear();
    banner();
    deleteConfig($configFile,$apiKeyFile);
    goto main_menu;
} elseif ($pilih === '0') {
    echo "\033[1;31m[!] Keluar dari program. Sampai jumpa!\033[0m\n";
    exit;
} else {
    echo "\033[1;31m[!] Pilihan tidak valid!\033[0m\n";
    sleep(2);
    goto main_menu;
}

$config = file_exists($configFile) ? json_decode(file_get_contents($configFile), true) : [];$keys   = file_exists($apiKeyFile) ? json_decode(file_get_contents($apiKeyFile), true) : [];

$apikey_xevil   =$keys['apikey_xevil'] ?? '';
$apikey_waryono =$keys['apikey_waryono'] ?? '';
$coki           =$config['cookie'] ?? '';
$ua             =$config['user_agent'] ?? default_ua;

if (empty($coki)) {
    echo "\033[1;31m[!] Cookie belum diatur! Silakan atur melalui menu COOKIE.\033[0m\n";
    sleep(2);
    goto main_menu;
}

if ($solver_mode === "xevil" && empty($apikey_xevil)) {
    echo "\033[1;31m[!] API Key XEVIL belum diatur! Silakan isi lewat menu API KEY XEVIL.\033[0m\n";
    sleep(2);
    goto main_menu;
}

if ($solver_mode === "waryono" && empty($apikey_waryono)) {
    echo "\033[1;31m[!] API Key WARYONO belum diatur! Silakan isi lewat menu API KEY WARYONO.\033[0m\n";
    sleep(2);
    goto main_menu;
}

function get_dash_headers($coki,$ua) {
    return [
        "host: " . script_name,
        "user-agent: " . $ua,
        "cookie: " . $coki
    ];
}

function ajax_h($coki, $ua,$referer) {
    return [
        "host: " . script_name,
        "x-requested-with: XMLHttpRequest",
        "user-agent: " . $ua,
        "content-type: application/x-www-form-urlencoded; charset=UTF-8",
        "origin: " . host,
        "referer: " . $referer,
        "cookie: " . $coki
    ];
}

function cek_balance($coki, $ua) {$res = skibidixxx(host . "/dashboard/", "GET", [], get_dash_headers($coki,$ua));
    if (strpos($res, "userGlobal") === false) return '0';
    preg_match('/JSON\.parse\(`(\{.*?\})`\);/s', $res,$ud);
    $udata = json_decode($ud[1] ?? '{}', true);
    preg_match('/balance-numeric[^>]*>([^<]+)</', $res,$bal);
    return trim($bal[1] ?? (isset($udata['balanceU']) ? (string)$udata['balanceU'] : '0'));
}

$res_dash = skibidixxx(host . "/dashboard/", "GET", [], get_dash_headers($coki,$ua));
if (strpos($res_dash, "userGlobal") === false) {
    echo "\033[1;31m[ERROR] Cookie expired atau belum login!\033[0m\n";
    sleep(3);
    goto main_menu;
}
preg_match('/JSON\.parse\(`(\{.*?\})`\);/s', $res_dash,$ud);
$udata = json_decode($ud[1] ?? '{}', true);
$uid   =$udata['id'] ?? '?';
$lvl   =$udata['lvl'] ?? 0;
$balance = cek_balance($coki,$ua);

yt_loop:
$last_update = date('H:i:s');
$active_api_display = ($solver_mode === "xevil") ? "XEVIL API" : "WARYONO API";

clear();
banner();
echo "\033[1;36m┌─────────────────────────────────────────┐\033[0m\n";
echo "\033[1;36m│\033[0m \033[1;32mUser ID    : \033[1;37m" . str_pad($uid, 28) . "\033[1;36m│\033[0m\n";
echo "\033[1;36m│\033[0m \033[1;32mLevel      : \033[1;37m" . str_pad($lvl, 28) . "\033[1;36m│\033[0m\n";
echo "\033[1;36m│\033[0m \033[1;32mBalance    : \033[1;33m" . str_pad($balance . " RUB", 28) . "\033[1;36m│\033[0m\n";
echo "\033[1;36m│\033[0m \033[1;32mTime       : \033[1;37m" . str_pad($last_update, 28) . "\033[1;36m│\033[0m\n";
echo "\033[1;36m│\033[0m \033[1;32mActive API : \033[1;33m" . str_pad($active_api_display, 28) . "\033[1;36m│\033[0m\n";
echo "\033[1;36m└─────────────────────────────────────────┘\033[0m\n\n";

$tj = json_decode(skibidixxx(host . "/tasks/control/getExtYT.php", "POST", "mac=0", ajax_h($coki,$ua, host . "/tasks/videoExtYT/")), true);
if (($tj['status'] ?? '') === "error") {
    $msg =$tj['message'] ?? 'limit';
    echo "\033[1;31m[INFO] Task video: $msg, menunggu...\033[0m\n";
    timer(300);
    goto yt_loop;
}
if ((($tj['status'] ?? '') !== "ok") || !isset($tj['data'])) {
    echo "\033[1;33m[INFO] Task video kosong/habis, cooldown 10 menit...\033[0m\n";
    timer(600);
    goto yt_loop;
}
$task =$tj['data'];
$tid  = trim((string)($task['id'] ?? ''));
if ($tid === '') {
    echo "\033[1;33m[INFO] Task video habis, cooldown 10 menit...\033[0m\n";
    timer(600);
    goto yt_loop;
}
$dur   = max(1, (int)($task['duration'] ?? 15));

echo "\033[1;33m┌─────────────────────────────────────────┐\033[0m\n";
echo "\033[1;33m│\033[0m \033[1;34m[YT-TASK]\033[0m ID: " . str_pad($tid, 26) . "\033[1;33m│\033[0m\n";
echo "\033[1;33m└─────────────────────────────────────────┘\033[0m\n";

$fin = [
    "videoCard" => ["vendor" => "Google Inc. (ARM)", "renderer" => "ANGLE (ARM, Mali-G52 MC2, OpenGL ES 3.2)"],
    "viewPort" => ["h" => 897, "w" => 450, "hM" => 1000, "wM" => 450],
    "platform" => "Linux armv81",
    "dpr" => 1.600000023841858,
    "multi" => ["speakers" => 1, "micros" => 1, "webcams" => 1, "devices" => 1],
    "ori" => ["alpha" => 284.7, "beta" => 33, "gamma" => 3.4, "is" => 1],
    "v" => 2.4,
    "cl" => ["x" => 51, "y" => 18],
    "c" => 150,
    "memory" => 4,
    "concur" => 8,
    "en" => ["ar" => "", "b" => 150, "m" => "25078RA3EY", "p" => "Android", "pv" => "16.0.0"],
    "bat" => ["charging" => 0, "lvl" => 0.87]
];
$fdata = http_build_query(["TaskId" => $tid, "fin" => $fin]);
skibidixxx(host . "/tasks/control/start.php", "POST", $fdata, ajax_h($coki,$ua, host . "/tasks/videoExtYT/"));

timer($dur + 6, "  \033[1;33mwatching video...\033[0m");

$chk = json_decode(skibidixxx(host . "/captcha/control/checkExtYT.php", "POST", "refreshTask=0", ajax_h($coki,$ua, host . "/tasks/videoExtYT/")), true);
if (($chk['status'] ?? '') === "ok") {
    $reward =$chk['data']['reward'] ?? '0';
    echo "\033[1;32m[CHECK] " . ($chk['message'] ?? "Проверка пройдена") . "\033[0m\n";
    echo "\033[1;32m[DONE] Sesi video selesai (+ $reward RUB)\033[0m\n";
    $balance = cek_balance($coki,$ua);
    sleep(3);
    goto yt_loop;
}

if (($chk['status'] ?? '') === "data" && !empty($chk['data'])) {$captcha_retry = 0;
    $solved = false;
    
    while ($captcha_retry < 3 && !$solved) {$captcha_retry++;
        echo "\033[1;36m[INFO] Captcha terdeteksi, mencoba solver ($solver_mode - percobaan ke-$captcha_retry)...\033[0m\n";
        
        $img = fix_b64($chk['data']);$pts = [];
        if ($solver_mode === "xevil") {
            $pts = xevilSolver($img,$apikey_xevil);
        } else {
            $pts = waryonoSolver($img,$apikey_waryono);
        }
        
        if (is_array($pts) && !empty($pts)) {
            foreach ($pts as $p) {$post_data = "x=" . (int)$p['x'] . "&y=" . (int)$p['y'];
                $ckj = json_decode(skibidixxx(host . "/captcha/control/checkExtYT.php", "POST", $post_data, ajax_h($coki,$ua, host . "/tasks/videoExtYT/")), true);
                if (($ckj['status'] ?? '') === "ok") {
                    $reward =$ckj['data']['reward'] ?? '0';
                    echo "\033[1;32m[CHECK] " . ($ckj['message'] ?? "Проверка пройдена") . "\033[0m\n";
                    echo "\033[1;32m[DONE] Sesi video selesai (+ $reward RUB)\033[0m\n";
                    $balance = cek_balance($coki, $ua);$solved = true;
                    break 2;
                }
            }
        }
        
        if (!$solved) {
            echo "\033[1;33m[INFO] Solver belum merespons, mencoba ulang dalam 3 detik...\033[0m\n";
            sleep(3);
        }
    }
    
    if (!$solved) {
        echo "\033[1;31m[INFO] Gagal menyelesaikan captcha setelah 3 kali percobaan, melewati task...\033[0m\n";
    }
} else {
    echo "\033[1;32m[DONE] Sesi video selesai.\033[0m\n";
    $balance = cek_balance($coki,$ua);
}
sleep(3);
goto yt_loop;
