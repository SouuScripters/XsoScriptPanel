<?php
/**
 * ============================================================================
 *  AdClickersBot — YouTube Task Auto-Completer (PHP bot)
 *  SOUU ENGINE · LimeFaucet-style panel UI · v3.2
 * ============================================================================
 */

declare(strict_types=1);

// ─────────────────────────────────────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────────────────────────────────────
const ACB_BASE      = 'https://www.adclickersbot.com';
const DEFAULT_API   = 'https://aviso.bz/api/v1';
const DEFAULT_KEY   = 'ak_9990eed03d4fc4999563d48a4b6814c9c11e9866';
const ORIGIN        = 'https://www.adclickersbot.com';
const DEFAULT_UA    = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36';

const CONFIG_FILE   = __DIR__ . '/conf77ig.json';
const COOKIE_FILE   = __DIR__ . '/coo777kie.txt';
const DEBUG_DIR     = __DIR__ . '/deb77ug';
const LOG_DIR       = __DIR__ . '/log77s';

const SUPPORTED_TASK_TYPES = ['ads', 'like'];

const BOX_WIDTH = 62;
const LOG_LINES = 7;

// ─────────────────────────────────────────────────────────────────────────────
//  UTF-8 substring
// ─────────────────────────────────────────────────────────────────────────────
if (!function_exists('u_substr')) {
    function u_substr(string $s, int $start, ?int $length = null): string
    {
        if (function_exists('mb_substr')) {
            return (string) mb_substr($s, $start, $length, 'UTF-8');
        }
        return (string) substr($s, $start, $length ?? PHP_INT_MAX);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  UI
// ─────────────────────────────────────────────────────────────────────────────
final class UI
{
    private static bool $color = true;

    /** @var array<string,mixed> */
    public static array $state = [
        'title'    => 'ADCLICKERSBOT AUTO COMPLETE',
        'subtitle' => '─────── SOUU ENGINE ───────',
        'running'  => false,
        'status'   => 'INIT',
        'uid'      => '-',
        'hash'     => '-',
        'endpoint' => '-',
        'round'    => 0,
        'done'     => 0,
        'failed'   => 0,
        'mode'     => 'ADS + LIKE',
        'phase'    => '-',
        'cooldown' => 0,
        'start_ts' => 0,
    ];

    /** @var array<int,array{ts:string,icon:string,tag:string,msg:string,kind:string}> */
    private static array $logs = [];

    public static function init(): void
    {
        self::$color = self::detectColor();
        self::$state['start_ts'] = time();
    }

    private static function detectColor(): bool
    {
        if (getenv('NO_COLOR') !== false && getenv('NO_COLOR') !== '') return false;
        if (getenv('TERMUX_VERSION'))               return true;
        if (getenv('WT_SESSION'))                   return true;
        if (PHP_OS_FAMILY === 'Windows')            return true;
        if (function_exists('stream_isatty'))       return @stream_isatty(STDOUT);
        return true;
    }

    // ── ANSI helpers ─────────────────────────────────────────────────────
    private static function fg(int $c, string $s): string
    {
        return self::$color ? "\033[38;5;{$c}m{$s}\033[0m" : $s;
    }
    private static function bold(string $s): string
    {
        return self::$color ? "\033[1m{$s}\033[22m" : $s;
    }
    private static function dim(string $s): string
    {
        return self::$color ? "\033[2m{$s}\033[22m" : $s;
    }
    private static function strip(string $s): string
    {
        return (string) preg_replace('/\033\[[0-9;]*m/', '', $s);
    }
    private static function vlen(string $s): int
    {
        $plain = self::strip($s);
        if (function_exists('mb_strwidth')) return (int) mb_strwidth($plain, 'UTF-8');
        return strlen($plain);
    }
    private static function pad(string $s, int $width): string
    {
        $vl = self::vlen($s);
        if ($vl >= $width) return $s;
        return $s . str_repeat(' ', $width - $vl);
    }
    private static function trunc(string $s, int $max): string
    {
        if (self::vlen($s) <= $max) return $s;
        return u_substr($s, 0, max(0, $max - 1)) . '…';
    }

    private static function gradient(string $text, int $start = 51, int $end = 213): string
    {
        if (!self::$color) return $text;
        $chars = preg_split('//u', $text, -1, PREG_SPLIT_NO_EMPTY);
        $n = count($chars);
        if ($n <= 1) return self::fg($start, $text);
        $out = '';
        foreach ($chars as $i => $ch) {
            $t = $i / max(1, $n - 1);
            $c = (int) round($start + ($end - $start) * $t);
            $out .= "\033[38;5;{$c}m{$ch}";
        }
        return $out . "\033[0m";
    }

    // ── Box primitives ───────────────────────────────────────────────────
    private static function top(): string { return self::fg(51, '╔' . str_repeat('═', BOX_WIDTH) . '╗'); }
    private static function mid(): string { return self::fg(51, '╠' . str_repeat('═', BOX_WIDTH) . '╣'); }
    private static function bot(): string { return self::fg(51, '╚' . str_repeat('═', BOX_WIDTH) . '╝'); }
    private static function row(string $content): string
    {
        $line = self::pad(' ' . $content, BOX_WIDTH);
        return self::fg(51, '║') . $line . self::fg(51, '║');
    }
    private static function blank(): string
    {
        return self::fg(51, '║') . str_repeat(' ', BOX_WIDTH) . self::fg(51, '║');
    }

    /** Ekspos pad() buat menu di luar class */
    public static function padPublic(string $s, int $width): string
    {
        return self::pad($s, $width);
    }

    // ── Render panel ─────────────────────────────────────────────────────
    public static function render(): void
    {
        if (!self::$state['running']) return;

        $s = self::$state;
        $buf = "\033[2J\033[H";

        $buf .= self::top() . "\n";
        $buf .= self::row(self::bold(self::gradient((string)$s['title'], 51, 213))) . "\n";
        $buf .= self::row(self::dim((string)$s['subtitle'])) . "\n";
        $buf .= self::mid() . "\n";

        // TASK
        $buf .= self::row(self::bold('TASK')) . "\n";
        $buf .= self::row('├─ ' . self::pad('UID', 11) . ': ' . (string)$s['uid']) . "\n";
        $buf .= self::row('├─ ' . self::pad('Hash', 11) . ': ' . (string)$s['hash']) . "\n";
        $buf .= self::row('└─ ' . self::pad('Endpoint', 11) . ': ' . self::trunc((string)$s['endpoint'], 30)) . "\n";
        $buf .= self::mid() . "\n";

        // PROGRESS
        $buf .= self::row(self::bold('PROGRESS')) . "\n";
        $buf .= self::row('├─ ' . self::pad('Round', 11) . ': ' . (string)$s['round']) . "\n";
        $buf .= self::row('├─ ' . self::pad('Done', 11) . ': ' . (string)$s['done']) . "\n";
        $buf .= self::row('├─ ' . self::pad('Failed', 11) . ': ' . (string)$s['failed']) . "\n";
        $buf .= self::row('└─ ' . self::pad('Mode', 11) . ': ' . (string)$s['mode']) . "\n";
        $buf .= self::mid() . "\n";

        // STATUS
        $phaseDisp = (string)$s['phase'];
        if ((int)$s['cooldown'] > 0) {
            $phaseDisp .= ' · ' . (int)$s['cooldown'] . 's';
        }
        $buf .= self::row(self::bold('STATUS')) . "\n";
        $buf .= self::row('├─ ' . self::pad('State', 11) . ': ' . (string)$s['status']) . "\n";
        $buf .= self::row('└─ ' . self::pad('Phase', 11) . ': ' . self::trunc($phaseDisp, 30)) . "\n";
        $buf .= self::mid() . "\n";

        // LIVE LOG
        $logs = array_slice(self::$logs, -LOG_LINES);
        for ($i = 0; $i < LOG_LINES; $i++) {
            if (isset($logs[$i])) {
                $buf .= self::row(self::fmtLog($logs[$i])) . "\n";
            } else {
                $buf .= self::blank() . "\n";
            }
        }

        $buf .= self::bot() . "\n";
        $buf .= "\n   " . self::bold(self::fg(46, 'BOT RUNNING')) . ' ' . self::dim('•') . ' ' . self::fg(51, date('H:i:s')) . "\n";
        $buf .= "   " . self::dim('By Power ') . self::fg(213, '@SouuXso') . self::dim(' • ') . self::fg(46, 'AdClickersBot Edition') . "\n\n";

        echo $buf;
        flush();
    }

    /** @param array{ts:string,icon:string,tag:string,msg:string,kind:string} $l */
    private static function fmtLog(array $l): string
    {
        $ts = self::dim('[' . $l['ts'] . ']');
        $colorMap = [
            'info'  => 51,
            'ok'    => 46,
            'warn'  => 208,
            'err'   => 196,
            'step'  => 213,
            'watch' => 51,
            'gray'  => 240,
        ];
        $c = $colorMap[$l['kind']] ?? 250;
        $icon = self::fg($c, $l['icon']);
        $tag  = self::fg($c, self::pad($l['tag'], 7));
        $msg  = self::trunc($l['msg'], 38);
        return $ts . ' ' . $icon . ' ' . $tag . $msg;
    }

    // ── Log & state ──────────────────────────────────────────────────────
    public static function push(string $tag, string $msg, string $kind = 'info', string $icon = '◈'): void
    {
        self::$logs[] = [
            'ts'   => date('H:i:s'),
            'icon' => $icon,
            'tag'  => strtoupper($tag),
            'msg'  => $msg,
            'kind' => $kind,
        ];
        if (count(self::$logs) > 200) array_shift(self::$logs);
        if (self::$state['running']) self::render();
    }

    public static function ok(string $tag, string $msg): void   { self::push($tag, $msg, 'ok',   '✔'); }
    public static function err(string $tag, string $msg): void  { self::push($tag, $msg, 'err',  '✖'); }
    public static function warn(string $tag, string $msg): void { self::push($tag, $msg, 'warn', '◈'); }
    public static function info(string $tag, string $msg): void { self::push($tag, $msg, 'info', '◈'); }
    public static function step(string $tag, string $msg): void { self::push($tag, $msg, 'step', '⬢'); }
    public static function watch(string $tag, string $msg): void{ self::push($tag, $msg, 'watch','⬢'); }

    public static function set(string $k, mixed $v): void { self::$state[$k] = $v; }
    public static function setMany(array $pairs): void { foreach ($pairs as $k => $v) self::$state[$k] = $v; }

    public static function startPanel(): void { self::$state['running'] = true; self::render(); }
    public static function stopPanel(): void  { self::$state['running'] = false; }

    public static function countdown(int $seconds, string $label): void
    {
        for ($i = $seconds; $i > 0; $i--) {
            self::setMany(['phase' => $label, 'cooldown' => $i]);
            if (self::$state['running']) self::render();
            sleep(1);
        }
        self::setMany(['cooldown' => 0, 'phase' => '-']);
    }

    // ── Banner (startup) ─────────────────────────────────────────────────
    public static function banner(): void
    {
        $W = BOX_WIDTH;
        $line = fn(string $c) => self::fg(51,'║') . self::pad(' ' . $c, $W) . self::fg(51,'║');
        $top  = self::fg(51,'╔' . str_repeat('═', $W) . '╗');
        $mid  = self::fg(51,'╠' . str_repeat('═', $W) . '╣');
        $bot  = self::fg(51,'╚' . str_repeat('═', $W) . '╝');

        echo "\n";
        echo $top . "\n";
        echo $line(self::bold(self::gradient('ADCLICKERSBOT AUTO COMPLETE', 51, 213))) . "\n";
        echo $line(self::dim('─────── SOUU ENGINE ───────')) . "\n";
        echo $mid . "\n";
        echo $line(self::bold('ABOUT')) . "\n";
        echo $line('├─ ' . self::pad('Engine', 11) . ': YouTube Task Auto-Completer') . "\n";
        echo $line('├─ ' . self::pad('Runtime', 11) . ': PHP 8.0 – 8.5+') . "\n";
        echo $line('├─ ' . self::pad('Flow', 11) . ': identify → counters → tasks') . "\n";
        echo $line('└─ ' . self::pad('Skipped', 11) . ': sub tasks') . "\n";
        echo $mid . "\n";
        echo $line(self::bold('AUTHOR')) . "\n";
        echo $line('└─ ' . self::pad('By', 11) . ': ' . self::fg(213, '@SouuXso')) . "\n";
        echo $bot . "\n\n";
        flush();
    }

    // ── Untuk prompt di luar panel ───────────────────────────────────────
    public static function c(string $text, string $color): string
    {
        if (!self::$color) return $text;
        $map = [
            'reset'=>0,'bold'=>1,'dim'=>2,
            'red'=>196,'green'=>46,'yellow'=>226,'blue'=>51,'magenta'=>201,
            'cyan'=>51,'white'=>15,'gray'=>240,'violet'=>141,'orange'=>208,
            'br_red'=>196,'br_green'=>46,'br_yellow'=>226,'br_blue'=>51,
            'br_magenta'=>201,'br_cyan'=>51,'br_white'=>15,
        ];
        $code = $map[$color] ?? 0;
        return "\033[{$code}m{$text}\033[0m";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Logger
// ─────────────────────────────────────────────────────────────────────────────
final class Logger
{
    private string $file;

    public function __construct(string $dir)
    {
        if (!is_dir($dir)) @mkdir($dir, 0755, true);
        $this->file = rtrim($dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR
                    . 'app_' . date('Y-m-d') . '.log';
    }

    public function write(string $level, string $message): void
    {
        $line = sprintf("[%s] [%s] %s\n", date('Y-m-d H:i:s'), strtoupper($level), $message);
        @file_put_contents($this->file, $line, FILE_APPEND | LOCK_EX);
    }

    public function info(string $m): void  { $this->write('INFO',  $m); }
    public function warn(string $m): void  { $this->write('WARN',  $m); }
    public function error(string $m): void { $this->write('ERROR', $m); }
    public function debug(string $m): void { $this->write('DEBUG', $m); }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Config
// ─────────────────────────────────────────────────────────────────────────────
final class Config
{
    /** @var array<string,mixed> */
    public array $data = [];

    public function __construct(array $data = [])
    {
        $this->data = array_merge([
            'task_url'             => '',
            'user_hash'            => '',
            'api_key'              => '',
            'api_endpoint'         => '',
            'cookies'              => '',
            'platform'             => 'Win32',
            'lang'                 => 'en',
            'user_agent'           => DEFAULT_UA,
            'fingerprint'          => [
                'fp'         => 'd0de63b9837a4b9c5f7236b8bc7318d0',
                'hashFont'   => 'f730c0cc627b3b3d7db9f459836db692',
                'langs'      => 'vi, en-US, en',
                'timezone'   => 'Asia/Saigon',
                'platform'   => 'Win32',
                'gpu'        => 'Google Inc. (Intel)~ANGLE (Intel, Intel(R) HD Graphics (0x00000152) Direct3D11 vs_5_0 ps_5_0, D3D11)',
                'screen'     => '1280x800',
                'memory'     => 4,
                'cpuCores'   => 2,
            ],
            'delay_between_tasks'  => 1,
            'delay_when_no_tasks'  => 1,
            'delay_like_seconds'   => 2,
        ], $data);
    }

    public static function load(string $file): ?self
    {
        if (!is_file($file)) return null;
        $raw = @file_get_contents($file);
        if ($raw === false || $raw === '') return null;
        $json = json_decode($raw, true);
        if (!is_array($json)) return null;
        return new self($json);
    }

    public function save(string $file): void
    {
        @file_put_contents(
            $file,
            json_encode($this->data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
        );
    }

    public function get(string $key, mixed $default = null): mixed { return $this->data[$key] ?? $default; }
    public function set(string $key, mixed $value): void { $this->data[$key] = $value; }
}

// ─────────────────────────────────────────────────────────────────────────────
//  CookieJar
// ─────────────────────────────────────────────────────────────────────────────
final class CookieJar
{
    /** @var array<string,string> */
    private array $cookies = [];

    public static function parse(string $raw): self
    {
        $jar = new self();
        $raw = trim($raw);
        if ($raw === '') return $jar;
        foreach (explode(';', $raw) as $chunk) {
            $chunk = trim($chunk);
            if ($chunk === '') continue;
            if (!str_contains($chunk, '=')) {
                UI::warn('COOKIE', "Entry without '=' ignored");
                continue;
            }
            [$k, $v] = explode('=', $chunk, 2);
            $k = trim($k);
            if ($k === '') continue;
            $jar->cookies[$k] = trim($v);
        }
        return $jar;
    }

    public function isEmpty(): bool { return count($this->cookies) === 0; }

    public function header(): string
    {
        if ($this->isEmpty()) return '';
        $parts = [];
        foreach ($this->cookies as $k => $v) $parts[] = $k . '=' . $v;
        return implode('; ', $parts);
    }

    public function count(): int { return count($this->cookies); }
}

// ─────────────────────────────────────────────────────────────────────────────
//  HttpClient
// ─────────────────────────────────────────────────────────────────────────────
final class HttpClient
{
    private array $defaultHeaders;
    private ?string $cookieHeader;
    private int $timeout;
    private ?string $proxy;
    private ?string $debugDir;
    private Logger $logger;
    private int $reqCounter = 0;

    public function __construct(
        array $defaultHeaders,
        ?string $cookieHeader,
        Logger $logger,
        int $timeout = 30,
        ?string $proxy = null,
        ?string $debugDir = null
    ) {
        $this->defaultHeaders = $defaultHeaders;
        $this->cookieHeader   = $cookieHeader;
        $this->logger         = $logger;
        $this->timeout        = $timeout;
        $this->proxy          = $proxy;
        $this->debugDir       = $debugDir;
    }

    public function setCookieHeader(?string $header): void { $this->cookieHeader = $header; }

    public function get(string $url, array $headers = []): array { return $this->request('GET', $url, null, $headers); }
    public function post(string $url, array|string|null $body = null, array $headers = []): array
    {
        return $this->request('POST', $url, $body, $headers);
    }

    private function request(string $method, string $url, array|string|null $body, array $extraHeaders): array
    {
        $merged = [];
        foreach ($this->defaultHeaders as $h) {
            $merged[strtolower(explode(':', $h, 2)[0])] = $h;
        }
        foreach ($extraHeaders as $h) {
            $merged[strtolower(explode(':', $h, 2)[0])] = $h;
        }
        $hdr = array_values($merged);

        if (!isset($merged['cookie']) && $this->cookieHeader !== null && $this->cookieHeader !== '') {
            $hdr[] = 'Cookie: ' . $this->cookieHeader;
        }

        $encoded = null;
        if ($body !== null) {
            $encoded = is_array($body)
                ? json_encode($body, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
                : $body;
        }

        $ch = curl_init();
        if ($ch === false) throw new RuntimeException('Failed to initialise cURL handle');

        $opts = [
            CURLOPT_URL             => $url,
            CURLOPT_RETURNTRANSFER  => true,
            CURLOPT_HEADER          => true,
            CURLOPT_FOLLOWLOCATION  => true,
            CURLOPT_MAXREDIRS       => 5,
            CURLOPT_POSTREDIR       => CURL_REDIR_POST_ALL,
            CURLOPT_TIMEOUT         => $this->timeout,
            CURLOPT_CONNECTTIMEOUT  => 15,
            CURLOPT_SSL_VERIFYPEER  => false,
            CURLOPT_SSL_VERIFYHOST  => 0,
            CURLOPT_ENCODING        => '',
            CURLOPT_HTTPHEADER      => $hdr,
            CURLOPT_HTTP_VERSION    => CURL_HTTP_VERSION_2_0,
            CURLOPT_USERAGENT       => DEFAULT_UA,
            CURLOPT_TCP_KEEPALIVE   => 1,
            CURLOPT_TCP_KEEPIDLE    => 30,
            CURLOPT_TCP_KEEPINTVL   => 15,
        ];

        if ($method === 'POST') {
            $opts[CURLOPT_POST]       = true;
            $opts[CURLOPT_POSTFIELDS] = $encoded ?? '';
        }

        if ($this->proxy !== null && $this->proxy !== '') {
            $opts[CURLOPT_PROXY] = $this->proxy;
        }

        curl_setopt_array($ch, $opts);

        $response = curl_exec($ch);
        $errno    = curl_errno($ch);
        $errmsg   = curl_error($ch);
        $info     = curl_getinfo($ch);
        unset($ch);

        if ($response === false || $errno !== 0) {
            throw new RuntimeException("cURL error [{$errno}] {$errmsg} — {$url}");
        }

        $headerSize = (int)($info['header_size'] ?? 0);
        $rawHeaders = substr((string)$response, 0, $headerSize);
        $bodyStr    = substr((string)$response, $headerSize);
        $status     = (int)($info['http_code'] ?? 0);

        $headersOut = [];
        foreach (preg_split("/\r\n\r\n/", trim($rawHeaders)) as $block) {
            foreach (explode("\r\n", $block) as $line) {
                if (str_contains($line, ':')) {
                    [$k, $v] = explode(':', $line, 2);
                    $headersOut[trim($k)] = trim($v);
                }
            }
        }

        $json = null;
        $trimmed = ltrim($bodyStr);
        if ($trimmed !== '' && ($trimmed[0] === '{' || $trimmed[0] === '[')) {
            $decoded = json_decode($bodyStr, true);
            if (is_array($decoded)) $json = $decoded;
        }

        $result = [
            'status'  => $status,
            'headers' => $headersOut,
            'body'    => $bodyStr,
            'url'     => (string)($info['url'] ?? $url),
            'json'    => $json,
        ];

        $this->dumpDebug($method, $url, $hdr, $encoded, $result);
        return $result;
    }

    private function dumpDebug(string $method, string $url, array $reqHeaders, ?string $reqBody, array $res): void
    {
        if ($this->debugDir === null) return;
        if (!is_dir($this->debugDir)) @mkdir($this->debugDir, 0755, true);

        $this->reqCounter++;
        $name = sprintf(
            '%s/%03d_%s_%s.json',
            rtrim($this->debugDir, DIRECTORY_SEPARATOR),
            $this->reqCounter,
            strtolower($method),
            preg_replace('/[^A-Za-z0-9_\-]+/', '_', parse_url($url, PHP_URL_PATH) ?? 'root')
        );

        $payload = [
            'time'     => date('c'),
            'request'  => ['method'=>$method,'url'=>$url,'headers'=>$reqHeaders,'body'=>$reqBody],
            'response' => ['status'=>$res['status'],'headers'=>$res['headers'],'body'=>$res['body']],
        ];

        @file_put_contents(
            $name,
            json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
        );

        $this->logger->debug("HTTP {$method} {$url} → {$res['status']}");
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  TaskUrl
// ─────────────────────────────────────────────────────────────────────────────
final class TaskUrl
{
    public array $params;

    private function __construct(array $params) { $this->params = $params; }

    public static function parse(string $url): self
    {
        $url = trim($url);
        if ($url === '') throw new InvalidArgumentException('Task URL is empty');
        if (!preg_match('~^https?://~i', $url)) throw new InvalidArgumentException('Task URL must start with http:// or https://');
        if (!preg_match('~/task/youtube~i', $url)) throw new InvalidArgumentException('Task URL must contain /task/youtube');
        $q = parse_url($url, PHP_URL_QUERY);
        if (!is_string($q) || $q === '') throw new InvalidArgumentException('Task URL has no query string');
        parse_str($q, $params);
        foreach (['uid', 'exp', 'sig'] as $needle) {
            if (!isset($params[$needle]) || !is_string($params[$needle]) || $params[$needle] === '') {
                throw new InvalidArgumentException("Task URL is missing the '{$needle}' parameter");
            }
        }
        return new self([
            'uid' => (string)$params['uid'],
            'exp' => (string)$params['exp'],
            'sig' => (string)$params['sig'],
        ]);
    }

    public function uid(): string { return $this->params['uid']; }
    public function exp(): string { return $this->params['exp']; }
    public function sig(): string { return $this->params['sig']; }

    public function configEndpoint(): string
    {
        return ACB_BASE . '/api/surveys/aviso/config?' . http_build_query([
            'uid' => $this->uid(), 'exp' => $this->exp(), 'sig' => $this->sig(),
        ]);
    }

    public function taskUrl(): string
    {
        return ACB_BASE . '/task/youtube?' . http_build_query([
            'uid' => $this->uid(), 'exp' => $this->exp(), 'sig' => $this->sig(),
        ]);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  AccountConfig
// ─────────────────────────────────────────────────────────────────────────────
final class AccountConfig
{
    public function __construct(
        public string $apiKey,
        public string $apiEndpoint,
        public string $userHash
    ) {}

    public function tasksBase(): string
    {
        return rtrim($this->apiEndpoint, '/') . '/youtube';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  HashResolver
// ─────────────────────────────────────────────────────────────────────────────
final class HashResolver
{
    public function __construct(
        private HttpClient $http,
        private Logger     $logger
    ) {}

    public function resolve(TaskUrl $url): ?AccountConfig
    {
        $endpoint = $url->configEndpoint();
        UI::info('HEALTH', 'Fetching account config...');

        try {
            $res = $this->http->get($endpoint, [
                'X-Requested-With: XMLHttpRequest',
                'Accept: application/json, text/plain, */*',
                'Referer: ' . $url->taskUrl(),
            ]);
        } catch (Throwable $e) {
            $this->logger->warn('Config request failed: ' . $e->getMessage());
            return null;
        }

        if ($res['status'] >= 400) {
            $this->logger->warn("Config endpoint returned HTTP {$res['status']}");
            return null;
        }

        $data = null;
        if (is_array($res['json'])) $data = $res['json'];
        else {
            $body = trim($res['body']);
            if ($body !== '' && ($body[0] === '{' || $body[0] === '[')) {
                $decoded = json_decode($body, true);
                if (is_array($decoded)) $data = $decoded;
            }
        }

        if (!is_array($data)) {
            $this->logger->warn('Config response is not JSON');
            return null;
        }

        $apiKey = $this->extractString($data, ['apiKey', 'api_key', 'key']);
        $apiEnd = $this->extractString($data, ['apiEndpoint', 'api_endpoint', 'endpoint']);
        $hash   = $this->extractHash($data);

        if ($hash === null) {
            $this->logger->warn('No user hash found in config response');
            return null;
        }

        return new AccountConfig($apiKey ?? DEFAULT_KEY, $apiEnd ?? DEFAULT_API, $hash);
    }

    private function extractString(array $data, array $keys): ?string
    {
        foreach ($keys as $k) {
            if (isset($data[$k]) && is_string($data[$k]) && $data[$k] !== '') return $data[$k];
        }
        return null;
    }

    private function extractHash(array $data): ?string
    {
        $candidates = ['userHash', 'user_hash', 'hash', 'avisoHash', 'aviso_hash'];
        foreach ($candidates as $k) {
            if (isset($data[$k]) && is_string($data[$k]) && preg_match('/^[a-f0-9]{64}$/i', $data[$k])) {
                return strtolower($data[$k]);
            }
        }
        foreach ($data as $v) {
            if (is_array($v)) { $r = $this->extractHash($v); if ($r !== null) return $r; }
            elseif (is_string($v) && preg_match('/^[a-f0-9]{64}$/i', $v)) return strtolower($v);
        }
        return null;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Flow
// ─────────────────────────────────────────────────────────────────────────────
final class Flow
{
    public function __construct(
        private HttpClient    $http,
        private Config        $cfg,
        private Logger        $log,
        private string        $hash,
        private AccountConfig $account
    ) {}

    private function api(string $endpoint, array|string|null $body = null, string $method = 'POST', array $headers = []): array
    {
        $url = $this->account->tasksBase() . '/' . ltrim($endpoint, '/');
        try {
            $res = $method === 'GET'
                ? $this->http->get($url, $headers)
                : $this->http->post($url, $body, $headers);

            $this->log->debug("API {$method} {$endpoint} → HTTP {$res['status']}");

            if ($res['status'] >= 400) {
                throw new RuntimeException("HTTP {$res['status']} from {$endpoint}");
            }
            return is_array($res['json']) ? $res['json'] : [];
        } catch (Throwable $e) {
            $this->log->error("API {$method} {$endpoint} failed: " . $e->getMessage());
            throw $e;
        }
    }

    private function keyHeader(): array { return ['X-API-Key: ' . $this->account->apiKey]; }

    public function identify(): array
    {
        UI::step('INIT', 'Registering fingerprint...');
        $fp = (array)$this->cfg->get('fingerprint', []);
        $body = [
            'hash'        => $this->hash,
            'ip'          => null,
            'userAgent'   => (string)$this->cfg->get('user_agent', DEFAULT_UA),
            'fingerprint' => $fp,
        ];
        $res = $this->api('tasks/identify', $body, 'POST', $this->keyHeader());
        if (isset($res['id'])) {
            UI::ok('INIT', "Identified id={$res['id']}");
        } else {
            UI::warn('INIT', 'Identify returned no id');
        }
        return $res;
    }

    public function counters(): array
    {
        $q = http_build_query([
            'hash'     => $this->hash,
            'platform' => (string)$this->cfg->get('platform', 'Win32'),
        ]);
        $res = $this->api('tasks/counters?' . $q, null, 'GET', $this->keyHeader());
        $c = $res['counters'] ?? [];
        if (is_array($c) && $c) {
            $parts = [];
            foreach ($c as $k => $v) $parts[] = "{$k}={$v}";
            UI::info('HEALTH', 'Counters: ' . implode('  ', $parts));
        }
        return $res;
    }

    public function available(): array
    {
        $q = http_build_query([
            'hash'     => $this->hash,
            'platform' => (string)$this->cfg->get('platform', 'Win32'),
        ]);
        return $this->api('tasks/available?' . $q, null, 'GET', $this->keyHeader());
    }

    public function start(int $taskId, string $type): array
    {
        return $this->api('tasks/start', [
            'taskId'   => $taskId,
            'hash'     => $this->hash,
            'type'     => $type,
            'platform' => (string)$this->cfg->get('platform', 'Win32'),
        ], 'POST', $this->keyHeader());
    }

    private function attemptHeaders(string $token): array
    {
        $h = ['Accept-Language: ' . strtolower((string)$this->cfg->get('lang', 'en'))];
        if ($token !== '') $h[] = 'X-Attempt-Token: ' . $token;
        else               $h[] = 'X-API-Key: ' . $this->account->apiKey;
        return $h;
    }

    public function timerStatus(int $attemptId, int $watchedTime, string $token): array
    {
        return $this->api('tasks/timer-status', [
            'attemptId'   => $attemptId,
            'action'      => 'complete',
            'watchedTime' => $watchedTime,
        ], 'POST', $this->attemptHeaders($token));
    }

    public function complete(int $attemptId, string $token): array
    {
        return $this->api('tasks/complete', ['attemptId' => $attemptId], 'POST', $this->attemptHeaders($token));
    }

    private function extractToken(string $url): string
    {
        if ($url === '') return '';
        $q = parse_url($url, PHP_URL_QUERY);
        if (!is_string($q) || $q === '') return '';
        parse_str($q, $params);
        $t = $params['token'] ?? '';
        return is_string($t) ? $t : '';
    }

    private function prettyUrl(string $url): string
    {
        if ($url === '') return '';
        $q = parse_url($url, PHP_URL_QUERY);
        if (is_string($q) && $q !== '') {
            parse_str($q, $params);
            if (isset($params['url']) && is_string($params['url']) && $params['url'] !== '') {
                return $params['url'];
            }
        }
        return $url;
    }

    public function processTask(array $task, string $type): bool
    {
        $taskId   = (int)($task['id'] ?? 0);
        $title    = (string)($task['title'] ?? 'task');
        $amount   = (float)($task['amount'] ?? 0);
        $progress = !empty($task['inProgress']);

        if ($taskId <= 0) {
            UI::warn('TASK', 'Invalid id skipped');
            return false;
        }

        if ($progress) {
            UI::info('TASK', "Task #{$taskId} in-progress — attempting");
        }

        $short = u_substr($title, 0, 24);
        UI::step('START', "Task #{$taskId} [{$type}] {$short}...");

        try {
            $start = $this->start($taskId, $type);
        } catch (Throwable $e) {
            UI::err('START', "Task #{$taskId} failed: " . $e->getMessage());
            return false;
        }

        $attemptId = (int)($start['attemptId'] ?? 0);
        if ($attemptId <= 0) {
            UI::err('START', "Task #{$taskId} no attemptId");
            return false;
        }

        $url      = (string)($start['url'] ?? '');
        $duration = (int)($start['duration'] ?? 0);
        $token    = $this->extractToken($url);

        if ($type === 'ads') {
            if ($duration <= 0) $duration = 1;
        } elseif ($type === 'like') {
            $duration = max(1, (int)$this->cfg->get('delay_like_seconds', 2));
        } else {
            $duration = 1;
        }

        if ($type === 'like' && $url !== '') {
            UI::info('LIKE', '  → ' . u_substr($this->prettyUrl($url), 0, 40));
        }

        UI::countdown($duration, "Waiting task #{$taskId}");

        $watchedTime = ($type === 'like') ? 0 : $duration;
        try {
            $ts = $this->timerStatus($attemptId, $watchedTime, $token);
            if (isset($ts['verified']) && $ts['verified'] === false) {
                $this->log->warn("timer-status verified=false for #{$taskId}");
            }
        } catch (Throwable $e) {
            $this->log->warn("timer-status failed for #{$taskId}: " . $e->getMessage());
        }

        try {
            $cres = $this->complete($attemptId, $token);
        } catch (Throwable $e) {
            UI::err('CLAIM', "Task #{$taskId} complete failed");
            return false;
        }

        if (isset($cres['code']) && $cres['code'] === 'task_already_processed') {
            UI::ok('CLAIM', "✓ Task #{$taskId} already processed");
            return true;
        }

        $earned = $cres['earned'] ?? $cres['amount'] ?? null;
        $cur    = (string)($cres['currency'] ?? 'usd');
        $human  = $earned !== null
            ? ($cur === 'usd'
                ? number_format((float)$earned, 5) . ' $'
                : number_format((float)$earned, 3) . ' ₽')
            : '';

        UI::ok('CLAIM', "✓ Task #{$taskId} " . ($human !== '' ? "+{$human}" : 'done'));
        return true;
    }

    public function run(): void
    {
        $this->identify();

        $delayTasks = (int)$this->cfg->get('delay_between_tasks', 1);
        $delayIdle  = (int)$this->cfg->get('delay_when_no_tasks', 1);

        $totalDone = 0;
        $totalFail = 0;
        $round     = 0;

        while (true) {
            $round++;
            UI::setMany([
                'round'  => $round,
                'done'   => $totalDone,
                'failed' => $totalFail,
                'status' => 'RUNNING',
                'phase'  => '-',
            ]);
            UI::info('CYCLE', "Cycle #{$round} starting...");

            try {
                $this->counters();
                $avail = $this->available();
            } catch (Throwable $e) {
                UI::warn('RETRY', 'Network hiccup — retry in 3s');
                UI::set('status', 'ERROR');
                sleep(3);
                continue;
            }

            $batch = [];
            foreach (SUPPORTED_TASK_TYPES as $t) {
                if (!empty($avail[$t]) && is_array($avail[$t])) {
                    foreach ($avail[$t] as $task) {
                        if (is_array($task)) {
                            $task['_type'] = $t;
                            $batch[] = $task;
                        }
                    }
                }
            }

            if (empty($batch)) {
                UI::set('status', 'WAITING');
                UI::warn('WAIT', "No ads/like tasks — wait {$delayIdle}s");
                sleep($delayIdle);
                continue;
            }

            UI::set('status', 'RUNNING');
            UI::info('QUEUE', 'Found ' . count($batch) . ' task(s) this cycle');

            $done = 0;
            foreach ($batch as $task) {
                $type = (string)($task['_type'] ?? 'ads');
                try {
                    if ($this->processTask($task, $type)) {
                        $done++;
                        $totalDone++;
                    } else {
                        $totalFail++;
                    }
                } catch (Throwable $e) {
                    $totalFail++;
                    UI::err('TASK', 'Error: ' . $e->getMessage());
                    $this->log->error('Task error: ' . $e->getMessage());
                }
                UI::setMany(['done'=>$totalDone,'failed'=>$totalFail]);
                if ($delayTasks > 0) sleep($delayTasks);
            }

            UI::info('CYCLE', "Cycle #{$round} done — {$done}/" . count($batch));

            if ($done === 0) {
                UI::set('status', 'WAITING');
                UI::warn('WAIT', "Nothing completed — sleep {$delayIdle}s");
                sleep($delayIdle);
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Prompts & menu — FIXED EOF handling
// ─────────────────────────────────────────────────────────────────────────────
function prompt(string $label, ?string $default = null): string
{
    $suffix = $default !== null && $default !== '' ? UI::c(" [{$default}]", 'gray') : '';
    echo UI::c('  › ', 'br_cyan') . $label . $suffix . ': ';
    $line = fgets(STDIN);
    if ($line === false) {
        echo PHP_EOL . UI::c('  ! ', 'br_red') . 'Input stream closed (EOF).' . PHP_EOL;
        exit(0);
    }
    $line = rtrim($line, "\r\n");
    if ($line === '' && $default !== null) return $default;
    return $line;
}

function menu(): int
{
    $W = BOX_WIDTH;

    $row = function (string $plain) use ($W): string {
        return UI::c('║', 'br_cyan') . UI::padPublic(' ' . $plain, $W) . UI::c('║', 'br_cyan');
    };
    $top = UI::c('╔' . str_repeat('═', $W) . '╗', 'br_cyan');
    $mid = UI::c('╠' . str_repeat('═', $W) . '╣', 'br_cyan');
    $bot = UI::c('╚' . str_repeat('═', $W) . '╝', 'br_cyan');

    echo PHP_EOL;
    echo $top . PHP_EOL;
    echo $row(UI::c('MAIN MENU', 'bold')) . PHP_EOL;
    echo $mid . PHP_EOL;
    echo $row('1. Start bot (use saved config)') . PHP_EOL;
    echo $row('2. Enter / change task URL') . PHP_EOL;
    echo $row('3. Update cookies only') . PHP_EOL;
    echo $row('4. Exit') . PHP_EOL;
    echo $bot . PHP_EOL;

    while (true) {
        echo UI::c('  › ', 'br_green') . 'Choose [1-4]: ';
        $line = fgets(STDIN);

        // ── FIX: EOF / stream closed ──
        if ($line === false) {
            echo PHP_EOL . UI::c('  ! ', 'br_red') . 'Input closed (EOF). Bye.' . PHP_EOL;
            exit(0);
        }

        $line = trim($line);

        // ── FIX: empty input → ulang, jangan spam ──
        if ($line === '') continue;

        if (in_array($line, ['1','2','3','4'], true)) return (int)$line;

        // ── FIX: invalid → feedback, ulang ──
        echo UI::c('  ✖ ', 'br_red') . "Invalid choice '{$line}'. Enter 1-4." . PHP_EOL;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Main
// ─────────────────────────────────────────────────────────────────────────────
function main(): int
{
    UI::init();
    UI::banner();

    if (!extension_loaded('curl')) {
        UI::err('INIT', 'cURL extension is required.');
        return 1;
    }

    if (!function_exists('mb_substr')) {
        UI::warn('INIT', 'ext-mbstring not loaded — using fallback.');
    }

    foreach ([DEBUG_DIR, LOG_DIR] as $d) {
        if (!is_dir($d)) @mkdir($d, 0755, true);
    }

    $logger = new Logger(LOG_DIR);
    $logger->info('=== Bot started ===');

    $cfg = Config::load(CONFIG_FILE);
    if ($cfg === null) {
        UI::warn('CONFIG', 'No config.json — creating one.');
        $cfg = new Config();
        $cfg->set('task_url', prompt('Task URL (https://www.adclickersbot.com/task/youtube?…)'));
        $cookieIn = prompt('Cookies (optional, "k=v;k=v", leave blank to skip)', '');
        $cfg->set('cookies', $cookieIn);
        $cfg->save(CONFIG_FILE);
        UI::ok('CONFIG', 'config.json saved');
    }

    while (true) {
        try {
            $choice = menu();
        } catch (Throwable $e) {
            UI::err('MENU', $e->getMessage());
            return 0;
        }

        if ($choice === 4) {
            UI::info('EXIT', 'Bye 👋');
            return 0;
        }
        if ($choice === 2) {
            $cfg->set('task_url', prompt('Task URL', (string)$cfg->get('task_url', '')));
            $cookieIn = prompt('Cookies ("k=v;k=v", blank = keep)', (string)$cfg->get('cookies', ''));
            $cfg->set('cookies', $cookieIn);
            $cfg->set('user_hash', '');
            $cfg->set('api_key', '');
            $cfg->set('api_endpoint', '');
            $cfg->save(CONFIG_FILE);
            UI::ok('CONFIG', 'Config updated');
            continue;
        }
        if ($choice === 3) {
            $cookieIn = prompt('Cookies ("k=v;k=v", blank = clear)', '');
            $cfg->set('cookies', $cookieIn);
            $cfg->save(CONFIG_FILE);
            @file_put_contents(COOKIE_FILE, $cookieIn);
            UI::ok('CONFIG', 'Cookies updated');
            continue;
        }

        // choice === 1 → run
        $taskUrlStr = (string)$cfg->get('task_url', '');
        if ($taskUrlStr === '') {
            UI::err('CONFIG', 'No task URL saved. Use option 2.');
            continue;
        }

        try {
            $taskUrl = TaskUrl::parse($taskUrlStr);
            UI::ok('INIT', "URL parsed uid={$taskUrl->uid()}");
        } catch (Throwable $e) {
            UI::err('INIT', 'Invalid task URL: ' . $e->getMessage());
            continue;
        }

        $cookieIn = (string)$cfg->get('cookies', '');
        if ($cookieIn !== '' && !is_file(COOKIE_FILE)) {
            @file_put_contents(COOKIE_FILE, $cookieIn);
        }
        $jar = CookieJar::parse($cookieIn);
        if (!$jar->isEmpty()) {
            UI::info('INIT', 'Loaded ' . $jar->count() . ' cookie(s)');
        }

        $defaultHeaders = [
            'Origin: ' . ORIGIN,
            'Referer: ' . $taskUrl->taskUrl(),
            'Accept: */*',
            'Content-Type: application/json',
            'Accept-Language: ' . strtolower((string)$cfg->get('lang', 'en')),
            'User-Agent: ' . (string)$cfg->get('user_agent', DEFAULT_UA),
        ];

        $http = new HttpClient(
            defaultHeaders: $defaultHeaders,
            cookieHeader:   $jar->isEmpty() ? null : $jar->header(),
            logger:         $logger,
            timeout:        30,
            proxy:          null,
            debugDir:       DEBUG_DIR,
        );

        UI::step('HEALTH', 'Resolving account config...');
        $account = null;
        $cachedHash = (string)$cfg->get('user_hash', '');
        $cachedKey  = (string)$cfg->get('api_key', '');
        $cachedEnd  = (string)$cfg->get('api_endpoint', '');

        if ($cachedHash !== '' && $cachedKey !== '' && $cachedEnd !== '') {
            $account = new AccountConfig($cachedKey, $cachedEnd, $cachedHash);
            UI::info('HEALTH', 'Using cached hash: ' . substr($cachedHash, 0, 16) . '…');
        } else {
            $resolver = new HashResolver($http, $logger);
            $account  = $resolver->resolve($taskUrl);
            if ($account !== null) {
                UI::ok('HEALTH', 'Hash: ' . substr($account->userHash, 0, 16) . '…');
                UI::ok('HEALTH', 'Endpoint: ' . $account->apiEndpoint);
                $cfg->set('user_hash', $account->userHash);
                $cfg->set('api_key', $account->apiKey);
                $cfg->set('api_endpoint', $account->apiEndpoint);
                $cfg->save(CONFIG_FILE);
            }
        }

        if ($account === null) {
            UI::warn('HEALTH', 'Could not auto-resolve. Manual input required.');
            $manualHash = trim(prompt('Paste aviso.bz user hash (64 hex chars)'));
            if (!preg_match('/^[a-f0-9]{64}$/i', $manualHash)) {
                UI::err('HEALTH', 'Invalid hash. Aborting.');
                continue;
            }
            $account = new AccountConfig(DEFAULT_KEY, DEFAULT_API, strtolower($manualHash));
            $cfg->set('user_hash', $account->userHash);
            $cfg->set('api_key', $account->apiKey);
            $cfg->set('api_endpoint', $account->apiEndpoint);
            $cfg->save(CONFIG_FILE);
        }

        // ── panel mode ──
        UI::setMany([
            'uid'      => $taskUrl->uid(),
            'hash'     => substr($account->userHash, 0, 16) . '…',
            'endpoint' => $account->apiEndpoint,
            'status'   => 'INIT',
            'start_ts' => time(),
        ]);
        UI::startPanel();

        $flow = new Flow($http, $cfg, $logger, $account->userHash, $account);

        try {
            $flow->run();
        } catch (Throwable $e) {
            UI::set('status', 'ERROR');
            UI::err('FATAL', $e->getMessage());
            $logger->error('Fatal: ' . $e->getMessage());
            UI::stopPanel();
            return 2;
        }

        return 0;
    }
}

exit(main());
