#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   ADTUBES AUTO WATCH — SOUU ENGINE Edition v2.6             ║
║   FIX : auto-retry network + SSL tolerance + backoff        ║
║   NEW : stop kalau semua network daily limit                ║
║   NEW : stop kalau ads fail 3x berturut-turut               ║
║   NEW : auto re-auth kalau init_data expired (401/403)      ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests, re, json, time, sys, os, random, signal, hashlib, secrets
import base64, urllib.parse
from datetime import datetime
from collections import deque
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
init(autoreset=True)

VERSION = "2.6"
HOST = "https://adtubes.lol"
ADSGRAM_BASE = "https://api.adsgram.ai"
CONFIG_FILE = "config_adtubes.json"
DEBUG_FILE = "debug.txt"

DEBUG = True

R, G, Y, B, C, W, M = Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.CYAN, Fore.WHITE, Fore.MAGENTA
RESET = Style.RESET_ALL

BOX_WIDTH = 62
LOG_LINES = 8
ANSI_RE = re.compile(r'\033\[[0-9;]*m')

TELEGRAM_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
               "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

SCREENS = ["384x832@2.8125", "360x812@3", "412x915@2.625", "393x873@3", "360x780@3"]
TOP_DOMAINS = ["adtubes.lol", "bot.richmancrypto.com"]

HUMAN_PAUSE_MIN = 14
HUMAN_PAUSE_MAX = 19
DEFAULT_AD_DURATION = 15
INIT_DATA_MAX_AGE_SEC = 3600

# Network retry config
HTTP_MAX_RETRY = 5
HTTP_BACKOFF_BASE = 3
REQUEST_TIMEOUT = 45

# Ad fail limit — stop kalau ads gagal berturut-turut
AD_FAIL_LIMIT = 3

# Re-auth limit
MAX_REAUTH = 3

_debug_fp = None


class InitDataExpired(Exception):
    """Raised pas server bilang init_data gak valid / expired."""
    pass


def open_debug():
    global _debug_fp
    if not DEBUG: return
    try:
        _debug_fp = open(DEBUG_FILE, "w", encoding="utf-8")
        write_debug("=" * 70)
        write_debug(f"AdTubes Bot v{VERSION} Debug Log")
        write_debug(f"Started: {datetime.now().isoformat()}")
        write_debug(f"Python: {sys.version.split()[0]}")
        write_debug("=" * 70)
        write_debug("")
    except Exception as e:
        print(f"failed open debug.txt: {e}")


def close_debug():
    global _debug_fp
    try:
        if _debug_fp:
            write_debug("")
            write_debug("=" * 70)
            write_debug(f"Closed: {datetime.now().isoformat()}")
            _debug_fp.close()
    except Exception:
        pass


def write_debug(line):
    if not DEBUG or not _debug_fp: return
    try:
        _debug_fp.write(line + "\n")
        _debug_fp.flush()
    except Exception:
        pass


def dump(label, data):
    write_debug(f"--- {label} ---")
    try:
        if isinstance(data, (dict, list)):
            write_debug(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            write_debug(str(data))
    except Exception:
        write_debug(repr(data))
    write_debug("")


def prompt_new_init_data():
    """Prompt user buat paste init_data baru. Return dict config baru."""
    print()
    print(UI.c("═" * 62, "br_yellow"))
    print(UI.c("  ⚠  INIT DATA EXPIRED / INVALID", "br_yellow"))
    print(UI.c("═" * 62, "br_yellow"))
    print(UI.c("  Ambil init_data baru:", "white"))
    print(UI.c("  Telegram Desktop → Ctrl+Shift+I → Console →", "gray"))
    print(UI.c("  copy(Telegram.WebApp.initData)", "br_cyan"))
    print()
    print(UI.c("  init_data : ", "white"), end="")

    while True:
        try:
            new_init = input().strip()
        except EOFError:
            new_init = ""

        if not new_init:
            print(UI.c("  ✖ kosong, coba lagi: ", "br_red"), end="")
            continue

        missing = [k for k in ('query_id', 'user', 'auth_date', 'signature', 'hash')
                   if f"{k}=" not in new_init]
        if missing:
            print(UI.c(f"  ✖ kurang field: {', '.join(missing)}", "br_red"))
            print(UI.c("  init_data : ", "white"), end="")
            continue

        try:
            kv = dict(p.split("=", 1) for p in new_init.split("&") if "=" in p)
            ad = int(kv.get("auth_date", "0"))
            age = int(time.time()) - ad
            if age > 300:
                print(UI.c(f"  ⚠ init_data udah umur {age//60} menit.", "yellow"))
                print(UI.c("  Tetap pakai? (y/N): ", "white"), end="")
                ans = input().strip().lower()
                if ans not in ("y", "ya", "yes"):
                    print(UI.c("  init_data : ", "white"), end="")
                    continue
        except Exception:
            pass

        break

    sp = ""
    m = re.search(r'start_param=([^&]+)', new_init)
    if m:
        sp = urllib.parse.unquote(m.group(1))

    return {
        "init_data": new_init,
        "start_param": sp,
    }


# ═══════════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════════
class UI:
    state = {
        "title": "ADTUBES AUTO WATCH", "subtitle": "─────── SOUU ENGINE ───────",
        "running": False, "cycle": 0, "host": HOST, "user": "-",
        "balance": "0.000000", "total_earned": "0.000000", "ads_total": 0,
        "state": "INIT", "phase": "-", "cooldown": 0,
        "tier": "-", "app_key": "-", "start_ts": int(time.time()),
        "last_reward": "-", "session_reward": 0.0, "session_ads": 0,
        "dcs_variant": "-", "init_age": "-", "net_retry": 0,
        "ad_fails": 0,
    }
    logs = deque(maxlen=300)

    @staticmethod
    def fg(c, s): return f"\033[38;5;{c}m{s}\033[0m"
    @staticmethod
    def bold(s): return f"\033[1m{s}\033[22m"
    @staticmethod
    def dim(s): return f"\033[2m{s}\033[22m"
    @staticmethod
    def strip_ansi(s): return ANSI_RE.sub('', s)
    @staticmethod
    def vlen(s): return len(UI.strip_ansi(s))
    @staticmethod
    def pad(s, w):
        vl = UI.vlen(s)
        return s + (" " * (w - vl)) if vl < w else s
    @staticmethod
    def trunc_ansi(s, max_visible):
        if UI.vlen(s) <= max_visible: return s
        out, visible, i, n = [], 0, 0, len(s)
        target = max_visible - 1
        while i < n and visible < target:
            if s[i] == '\033':
                j = i + 1
                while j < n and s[j] != 'm': j += 1
                if j < n: out.append(s[i:j + 1]); i = j + 1
                else: i += 1
            else:
                out.append(s[i]); visible += 1; i += 1
        return "".join(out) + "…" + "\033[0m"
    @staticmethod
    def trunc(s, n): return UI.trunc_ansi(s, n)
    @staticmethod
    def gradient(text, start=51, end=213):
        if not text: return text
        n = len(text)
        if n <= 1: return UI.fg(start, text)
        return "".join(
            f"\033[38;5;{int(round(start + (end - start) * i / (n - 1)))}m{ch}"
            for i, ch in enumerate(text)
        ) + "\033[0m"
    @staticmethod
    def top(): return UI.fg(51, "╔" + "═" * BOX_WIDTH + "╗")
    @staticmethod
    def mid(): return UI.fg(51, "╠" + "═" * BOX_WIDTH + "╣")
    @staticmethod
    def bot(): return UI.fg(51, "╚" + "═" * BOX_WIDTH + "╝")
    @staticmethod
    def row(content):
        return UI.fg(51, "║") + UI.pad(" " + content, BOX_WIDTH) + UI.fg(51, "║")
    @staticmethod
    def blank():
        return UI.fg(51, "║") + (" " * BOX_WIDTH) + UI.fg(51, "║")

    @staticmethod
    def render():
        if not UI.state["running"]: return
        s = UI.state
        buf = "\033[2J\033[H"
        buf += UI.top() + "\n"
        buf += UI.row(UI.bold(UI.gradient(s["title"], 51, 213))) + "\n"
        buf += UI.row(UI.dim(s["subtitle"])) + "\n"
        buf += UI.mid() + "\n"
        buf += UI.row(UI.bold("SESSION")) + "\n"
        buf += UI.row("├─ " + UI.pad("Host", 11) + ": " + UI.trunc(UI.fg(226, s["host"]), 30)) + "\n"
        buf += UI.row("├─ " + UI.pad("Cycle", 11) + ": " + UI.fg(226, str(s["cycle"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Tier", 11) + ": " + UI.fg(213, str(s["tier"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Init age", 11) + ": " + UI.fg(213, str(s["init_age"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("App Key", 11) + ": " + UI.trunc(UI.fg(46, str(s["app_key"])), 30)) + "\n"
        buf += UI.mid() + "\n"
        buf += UI.row(UI.bold("ACCOUNT")) + "\n"
        buf += UI.row("├─ " + UI.pad("User", 11) + ": " + UI.trunc(UI.fg(226, str(s["user"])), 30)) + "\n"
        buf += UI.row("├─ " + UI.pad("Balance", 11) + ": " + UI.fg(46, f"${s['balance']}")) + "\n"
        buf += UI.row("├─ " + UI.pad("Total Earn", 11) + ": " + UI.fg(46, f"${s['total_earned']}")) + "\n"
        buf += UI.row("└─ " + UI.pad("Ads Total", 11) + ": " + UI.fg(226, str(s["ads_total"]))) + "\n"
        buf += UI.mid() + "\n"
        buf += UI.row(UI.bold("SESSION STATS")) + "\n"
        buf += UI.row("├─ " + UI.pad("Reward", 13) + ": " + UI.fg(46, f"+${s['session_reward']:.6f}")) + "\n"
        buf += UI.row("├─ " + UI.pad("Ads count", 13) + ": " + UI.fg(226, str(s["session_ads"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Net retry", 13) + ": " + UI.fg(208, str(s.get("net_retry", 0)))) + "\n"
        fails = int(s.get("ad_fails", 0))
        fail_color = 196 if fails >= AD_FAIL_LIMIT else (208 if fails > 0 else 46)
        buf += UI.row("├─ " + UI.pad("Ad fails", 13) + ": " + UI.fg(fail_color, f"{fails}/{AD_FAIL_LIMIT}")) + "\n"
        buf += UI.row("└─ " + UI.pad("Last reward", 13) + ": " + UI.fg(226, str(s["last_reward"]))) + "\n"
        buf += UI.mid() + "\n"
        phase = str(s["phase"])
        if int(s["cooldown"]) > 0: phase += f" · {int(s['cooldown'])}s"
        state_color = {"RUNNING": 46, "WAITING": 208, "ERROR": 196,
                       "INIT": 240, "DONE": 46, "PAUSE": 213, "RETRY": 208}.get(s["state"], 226)
        buf += UI.row(UI.bold("STATUS")) + "\n"
        buf += UI.row("├─ " + UI.pad("State", 11) + ": " + UI.fg(state_color, str(s["state"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Phase", 11) + ": " + UI.trunc(UI.fg(208, phase), 30)) + "\n"
        buf += UI.mid() + "\n"
        logs = list(UI.logs)[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(logs): buf += UI.row(UI.fmt_log(logs[i])) + "\n"
            else: buf += UI.blank() + "\n"
        buf += UI.bot() + "\n"
        buf += "\n   " + UI.bold(UI.fg(46, "BOT RUNNING")) + " " + UI.dim("•") + " " + UI.fg(51, datetime.now().strftime("%H:%M:%S")) + "\n"
        buf += "   " + UI.dim("By Power ") + UI.fg(213, "@SouuXso") + UI.dim(" • ") + UI.fg(46, "AdTubes Edition") + "\n"
        buf += "   " + UI.dim(f"Debug → {DEBUG_FILE}") + "\n\n"
        sys.stdout.write(buf); sys.stdout.flush()

    @staticmethod
    def fmt_log(l):
        cmap = {"info": 51, "ok": 46, "warn": 208, "err": 196, "step": 213, "dbg": 240}
        c = cmap.get(l["kind"], 250)
        ts = UI.dim("[" + l["ts"] + "]")
        icon = UI.fg(c, l["icon"])
        tag = UI.fg(c, UI.pad(l["tag"], 8))
        avail = BOX_WIDTH - 1 - 10 - 1 - 1 - 1 - 8
        msg = UI.trunc(UI.fg(250, l["msg"]), avail)
        return f"{ts} {icon} {tag} {msg}"

    @staticmethod
    def push(tag, msg, kind="info", icon="◈"):
        UI.logs.append({"ts": datetime.now().strftime("%H:%M:%S"),
                        "icon": icon, "tag": tag.upper(), "msg": msg, "kind": kind})
        write_debug(f"[{kind.upper():5}] {tag}: {msg}")
        if UI.state["running"]: UI.render()

    @staticmethod
    def ok(tag, msg): UI.push(tag, msg, "ok", "✔")
    @staticmethod
    def err(tag, msg): UI.push(tag, msg, "err", "✖")
    @staticmethod
    def warn(tag, msg): UI.push(tag, msg, "warn", "◈")
    @staticmethod
    def info(tag, msg): UI.push(tag, msg, "info", "◈")
    @staticmethod
    def step(tag, msg): UI.push(tag, msg, "step", "⬢")
    @staticmethod
    def dbg(tag, msg): UI.push(tag, msg, "dbg", "·")

    @staticmethod
    def set(**kw): UI.state.update(kw)
    @staticmethod
    def start_panel():
        UI.state["running"] = True
        UI.state["start_ts"] = int(time.time())
        UI.render()
    @staticmethod
    def stop_panel(): UI.state["running"] = False

    @staticmethod
    def countdown(seconds, label):
        for i in range(int(seconds), 0, -1):
            UI.set(phase=label, cooldown=i)
            if UI.state["running"]: UI.render()
            time.sleep(1)
        UI.set(phase="-", cooldown=0)

    @staticmethod
    def c(text, color):
        cmap = {"reset": 0, "bold": 1, "dim": 2,
                "red": 196, "green": 46, "yellow": 226, "blue": 51, "magenta": 201,
                "cyan": 51, "white": 15, "gray": 240, "orange": 208,
                "br_red": 196, "br_green": 46, "br_yellow": 226, "br_cyan": 51}
        return f"\033[{cmap.get(color, 0)}m{text}\033[0m"

    @staticmethod
    def banner():
        W_ = BOX_WIDTH
        def line(c): return UI.fg(51, "║") + UI.pad(" " + c, W_) + UI.fg(51, "║")
        print()
        print(UI.fg(51, "╔" + "═" * W_ + "╗"))
        print(line(UI.bold(UI.gradient("ADTUBES AUTO WATCH", 51, 213))))
        print(line(UI.dim("─────── SOUU ENGINE ───────")))
        print(UI.fg(51, "╠" + "═" * W_ + "╣"))
        print(line(UI.bold("ABOUT")))
        print(line("├─ " + UI.pad("Host", 11) + ": " + HOST))
        print(line("├─ " + UI.pad("Retry", 11) + f": {HTTP_MAX_RETRY}x backoff"))
        print(line("├─ " + UI.pad("Ad fail", 11) + f": stop after {AD_FAIL_LIMIT}x"))
        print(line("├─ " + UI.pad("Re-auth", 11) + f": auto up to {MAX_REAUTH}x"))
        print(line("├─ " + UI.pad("Debug", 11) + f": {DEBUG_FILE}"))
        print(line("└─ " + UI.pad("Version", 11) + ": v" + VERSION))
        print(UI.fg(51, "╠" + "═" * W_ + "╣"))
        print(line(UI.bold("AUTHOR")))
        print(line("└─ " + UI.pad("By", 11) + ": " + UI.fg(213, "@SouuXso")))
        print(UI.fg(51, "╚" + "═" * W_ + "╝"))
        print()


# ═══════════════════════════════════════════════════════════════
#  SESSION BUILDER
# ═══════════════════════════════════════════════════════════════
def make_session():
    s = requests.Session()
    retry = Retry(total=0, connect=0, read=0, redirect=0, status=0, backoff_factor=0)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# ═══════════════════════════════════════════════════════════════
#  BOT
# ═══════════════════════════════════════════════════════════════
class AdTubesBot:
    def __init__(self):
        self.session = make_session()
        self.ua = TELEGRAM_UA
        self.init_data = ""
        self.app_key = ""
        self.user = {}
        self.networks = []
        self.fp = ""
        self.did = ""
        self.dcs_variant = ""
        self.start_param = ""

    def get_config(self):
        if not os.path.exists(CONFIG_FILE):
            print(UI.c("\n  ⚙  SETUP WIZARD — ADTUBES", "br_cyan"))
            print(UI.c("  " + "─" * 50, "br_cyan") + "\n")
            print(UI.c("  WAJIB: query_id, user, auth_date, signature, hash", "yellow"))
            print(UI.c("  Telegram Desktop → Console → copy(Telegram.WebApp.initData)\n", "white"))
            print(UI.c("  init_data : ", "white"), end="")
            init_data = input().strip()
            if not init_data:
                print(UI.c("  ✖ kosong\n", "br_red")); sys.exit(1)

            missing = [k for k in ['query_id', 'user', 'auth_date', 'signature', 'hash']
                       if f"{k}=" not in init_data]
            if missing:
                print(UI.c(f"\n  ✖ GAK LENGKAP. Missing: {', '.join(missing)}\n", "br_red"))
                sys.exit(1)

            sp = ""
            m = re.search(r'start_param=([^&]+)', init_data)
            if m:
                sp = urllib.parse.unquote(m.group(1))

            cfg = {
                "init_data": init_data,
                "start_param": sp,
                "fp": hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
                "did": secrets.token_hex(16),
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=2)
            print(UI.c(f"\n  ✓ Saved\n", "br_green"))
            time.sleep(1)
            return cfg
        with open(CONFIG_FILE) as f:
            return json.load(f)

    def _api_headers(self, with_app_key=True):
        h = {
            'x-init-data': self.init_data,
            'User-Agent': TELEGRAM_UA,
            'Accept': '*/*',
            'Accept-Language': 'id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'x-requested-with': 'org.telegram.messenger.web',
            'Origin': HOST,
            'Referer': f'{HOST}/',
        }
        if with_app_key and self.app_key:
            h['x-app-key'] = self.app_key
        return h

    def _log_request(self, method, path, body=None, headers=None):
        write_debug(f">>> {method} {path}")
        write_debug(f"    Time: {datetime.now().isoformat()}")
        if body is not None:
            dump("REQUEST BODY", body)
        if headers:
            redacted = {}
            for k, v in headers.items():
                if k.lower() in ('x-init-data',) and len(str(v)) > 30:
                    redacted[k] = str(v)[:30] + f"…[REDACTED]"
                else:
                    redacted[k] = v
            dump("REQUEST HEADERS", redacted)

    def _log_response(self, method, path, status, body_text, headers=None):
        write_debug(f"<<< {method} {path} → HTTP {status}")
        if body_text:
            try:
                j = json.loads(body_text)
                dump("RESPONSE BODY", j)
            except Exception:
                write_debug("--- RESPONSE BODY (raw) ---")
                write_debug(body_text[:2000])
                write_debug("")

    def _is_transient(self, exc):
        msg = str(exc).lower()
        transient_keywords = [
            'connection aborted', 'connection reset', 'connection refused',
            'read timed out', 'timed out', 'timeout',
            'ssl error', 'sslerror', 'temporary failure',
            'remote end closed', 'connection broken',
            'protocolerror', 'protocol error',
            'badstatusline', 'bad gateway', 'service unavailable',
            'server disconnected', 'incompleteread',
        ]
        return any(k in msg for k in transient_keywords)

    def _request_with_retry(self, method, url, headers, body=None):
        last_exc = None
        for attempt in range(1, HTTP_MAX_RETRY + 1):
            try:
                if method == "GET":
                    r = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                else:
                    r = self.session.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
                return r, None
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.SSLError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ContentDecodingError,
                    requests.exceptions.ProxyError) as e:

                last_exc = e
                if not self._is_transient(e):
                    write_debug(f"!!! NON-TRANSIENT ERROR: {type(e).__name__}: {e}")
                    return None, e

                if attempt < HTTP_MAX_RETRY:
                    wait = HTTP_BACKOFF_BASE * (2 ** (attempt - 1))
                    wait += random.uniform(0, 2)
                    UI.warn("NET", f"{type(e).__name__} (try {attempt}/{HTTP_MAX_RETRY}) — retry {int(wait)}s")
                    UI.set(net_retry=int(UI.state.get("net_retry", 0)) + 1)
                    write_debug(f"!!! RETRY {attempt}/{HTTP_MAX_RETRY}: {type(e).__name__}: {str(e)[:100]}")
                    write_debug(f"    Waiting {wait:.1f}s before next try...")

                    if attempt >= 2:
                        try: self.session.close()
                        except Exception: pass
                        self.session = make_session()
                        write_debug("    Session rebuilt")

                    time.sleep(wait)
                else:
                    write_debug(f"!!! MAX RETRY EXCEEDED: {type(e).__name__}: {e}")
                    return None, e
        return None, last_exc

    def _is_auth_error(self, code, body_text):
        """Deteksi 401/403 atau pesan auth gagal dari server."""
        if code in (401, 403):
            return True
        if not body_text:
            return False
        low = body_text.lower()
        auth_hints = [
            'please open ad tube',
            'initdata',
            'init_data',
            'unauthorized',
            'invalid signature',
            'expired',
        ]
        if code != 200 and any(h in low for h in auth_hints):
            return True
        return False

    def api_get(self, path, with_app_key=True):
        url = f"{HOST}{path}"
        headers = self._api_headers(with_app_key)
        self._log_request("GET", path, None, headers)
        r, err = self._request_with_retry("GET", url, headers)
        if r is None:
            UI.err("HTTP", f"{type(err).__name__}: {str(err)[:40]}")
            return 0, None, str(err)
        self._log_response("GET", path, r.status_code, r.text, r.headers)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        return r.status_code, self._try_json(r), r.text

    def api_post(self, path, body=None, with_app_key=True):
        url = f"{HOST}{path}"
        headers = self._api_headers(with_app_key)
        data = json.dumps(body) if body is not None else ""
        self._log_request("POST", path, body, headers)
        r, err = self._request_with_retry("POST", url, headers, data)
        if r is None:
            UI.err("HTTP", f"{type(err).__name__}: {str(err)[:40]}")
            return 0, None, str(err)
        self._log_response("POST", path, r.status_code, r.text, r.headers)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        return r.status_code, self._try_json(r), r.text

    def _try_json(self, r):
        try: return r.json()
        except Exception: return {"_raw": r.text[:200]}

    def _parse_kv(self):
        kv = {}
        for p in self.init_data.split("&"):
            if "=" in p:
                k, v = p.split("=", 1)
                kv[k] = v
        return kv

    def _b64url(self, s: str) -> str:
        b64 = base64.b64encode(s.encode()).decode()
        return b64.replace('+', '-').replace('/', '_').rstrip('=')

    def build_dcs_variants(self):
        kv = self._parse_kv()
        signature = kv.get('signature', '')
        auth_date = kv.get('auth_date', '')
        query_id = kv.get('query_id', '')
        user_enc = kv.get('user', '')
        user_raw = urllib.parse.unquote(user_enc)
        try:
            tg_id = json.loads(user_raw).get('id', 0)
        except Exception:
            tg_id = 0

        variants = []
        if auth_date and query_id and user_raw:
            dcs = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_raw}"
            variants.append(("v1:auth+query+user", signature, self._b64url(dcs), tg_id))
        fields = [(k, urllib.parse.unquote(v)) for k, v in kv.items() if k not in ('hash', 'signature')]
        fields.sort()
        dcs = "\n".join(f"{k}={v}" for k, v in fields)
        variants.append(("v2:all-sorted", signature, self._b64url(dcs), tg_id))
        if auth_date and user_raw:
            dcs = f"auth_date={auth_date}\nuser={user_raw}"
            variants.append(("v3:auth+user", signature, self._b64url(dcs), tg_id))
        return variants

    def adsgram_headers(self, top_domain="adtubes.lol"):
        return {
            'User-Agent': TELEGRAM_UA,
            'Accept': '*/*',
            'Accept-Language': 'id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'X-Color-Scheme': 'dark',
            'X-Requested-With': 'org.telegram.messenger.web',
            'X-Gyroscope': json.dumps({"x": -0.012, "y": 0.134, "z": -0.181, "isStarted": False}),
            'X-Accelerometer': json.dumps({"x": -5.14, "y": -8.55, "z": -1.23, "isStarted": False}),
            'X-Viewport-Height': '856.1778',
            'X-Is-Fullscreen': 'true',
            'sec-ch-ua': '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'Origin': f"https://{top_domain}",
            'Referer': f'https://{top_domain}/',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
        }

    def adsgram_get_adv(self, block_id):
        variants = self.build_dcs_variants()
        if not variants: return None, "no variants"
        platform = "Linux aarch64"
        lang = "id"
        last_err = "?"

        for top_domain in TOP_DOMAINS:
            for vname, sig, dcs, tg_id in variants:
                req_id = str(random.randint(10**20, 10**21 - 1))
                raw = secrets.token_hex(24)
                q = urllib.parse.urlencode({
                    'envType': 'telegram', 'blockId': str(block_id),
                    'platform': platform, 'language': lang,
                    'top_domain': top_domain,
                    'signature': sig, 'data_check_string': dcs,
                    'sdk_version': '2.2.5', 'tg_id': str(tg_id),
                    'tg_platform': 'android', 'tma_version': '9.6',
                    'request_id': req_id, 'raw': raw,
                })
                url = f"{ADSGRAM_BASE}/adv?{q}"
                write_debug(f">>> GET ADSGRAM /adv ({top_domain} | {vname})")
                try:
                    r = self.session.get(url, headers=self.adsgram_headers(top_domain), timeout=20)
                    write_debug(f"<<< ADSGRAM /adv → HTTP {r.status_code}")
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            banners = data.get('banners', [])
                            if banners:
                                UI.ok("ADSGRAM", f"OK {top_domain} via {vname}")
                                UI.set(dcs_variant=vname[:12])
                                return banners, None
                        except Exception:
                            pass
                    else:
                        write_debug(f"    body: {r.text[:300]}")
                    last_err = f"HTTP {r.status_code}"
                except Exception as e:
                    write_debug(f"!!! ADSGRAM exception: {type(e).__name__}: {e}")
                    last_err = f"{type(e).__name__}"
        return None, last_err

    def fire_event(self, url):
        try:
            self.session.get(url, headers={'User-Agent': TELEGRAM_UA, 'Accept': '*/*'}, timeout=10)
            write_debug(f">>> EVENT: {url[:120]}")
            return True
        except Exception:
            return False

    def _fire_banner_events(self, banner_obj, label="banner"):
        try:
            trackings = banner_obj.get('banner', {}).get('trackings', []) or []
            tmap = {}
            for t in trackings:
                nm = (t.get('name') or '').lower()
                v = t.get('value') or ''
                if nm and v: tmap[nm] = v
            if 'render' in tmap:
                self.fire_event(tmap['render']); UI.dbg("EVENT", f"{label}: render")
                time.sleep(0.4)
            if 'show' in tmap:
                self.fire_event(tmap['show']); UI.dbg("EVENT", f"{label}: show")
                time.sleep(0.4)
            return tmap
        except Exception as e:
            write_debug(f"!!! banner events: {type(e).__name__}: {e}")
            return {}

    # ── RE-AUTH ──
    def reauth(self):
        """Prompt new init_data, reset state, rebuild everything. Return True kalau sukses."""
        UI.warn("AUTH", "init_data expired — prompt input baru")

        was_running = UI.state["running"]
        UI.state["running"] = False
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

        try:
            new_cfg = prompt_new_init_data()
        except KeyboardInterrupt:
            raise

        try: self.session.close()
        except Exception: pass
        self.session = make_session()

        self.init_data = new_cfg["init_data"]
        self.start_param = new_cfg.get("start_param", "")
        self.fp = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        self.did = secrets.token_hex(16)
        self.app_key = ""
        self.user = {}
        self.networks = []

        try:
            cfg = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    cfg = json.load(f)
            cfg.update({
                "init_data": self.init_data,
                "start_param": self.start_param,
                "fp": self.fp,
                "did": self.did,
                "app_key": "",
            })
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
            UI.ok("AUTH", "config baru disimpan")
        except Exception as e:
            UI.warn("AUTH", f"gagal simpan config: {e}")

        UI.set(app_key="-", net_retry=0, ad_fails=0, init_age="0m")

        UI.state["running"] = was_running
        if was_running: UI.render()

        try:
            if not self.bootstrap():
                UI.err("AUTH", "bootstrap gagal setelah re-auth")
                return False
            if not self.device():
                UI.err("AUTH", "device gagal setelah re-auth")
                return False
            self.ping()
        except InitDataExpired:
            UI.err("AUTH", "init_data baru juga ditolak server")
            return False

        UI.ok("AUTH", "re-auth selesai, lanjut cycle")
        return True

    # ── FLOW ──
    def bootstrap(self):
        UI.step("BOOT", "GET /api/bootstrap")
        code, j, txt = self.api_get("/api/bootstrap", with_app_key=False)
        if code != 200:
            UI.err("BOOT", f"HTTP {code}: {txt[:50]}")
            return False

        if isinstance(j, dict):
            u = j.get("user", {})
            if u:
                self.user = u
                UI.set(
                    user=u.get("username") or u.get("firstName", "?"),
                    balance=f"{u.get('balance', 0):.6f}",
                    total_earned=f"{u.get('totalEarned', 0):.6f}",
                    ads_total=u.get("adsTotal", 0),
                    tier=(u.get("tier") or {}).get("name", "-") if isinstance(u.get("tier"), dict) else "-",
                )
        UI.ok("BOOT", "OK")
        return True

    def device(self, max_retry=3):
        for attempt in range(1, max_retry + 1):
            UI.step("DEVICE", f"POST /api/device (try {attempt}/{max_retry})")

            if attempt > 1:
                self.fp = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
                self.did = secrets.token_hex(16)

            payload = {
                "fp": self.fp, "did": self.did, "platform": "android",
                "info": {"screen": random.choice(SCREENS), "tz": "Asia/Jakarta",
                         "lang": "id", "gpu": "ANGLE ((Samsung Xclipse 530) on Vulkan 1.3.279)",
                         "tgv": "9.6"}
            }
            code, j, txt = self.api_post("/api/device", payload, with_app_key=False)

            if code != 200:
                UI.warn("DEVICE", f"HTTP {code}: {txt[:50]}")
                time.sleep(2); continue

            if isinstance(j, dict):
                new_key = j.get("appKey", "")
                if new_key:
                    self.app_key = new_key
                    UI.set(app_key=new_key)
                    UI.ok("DEVICE", f"appKey={new_key[:16]}…")
                    try:
                        cfg = self.get_config()
                        cfg["app_key"] = new_key
                        cfg["fp"] = self.fp
                        cfg["did"] = self.did
                        with open(CONFIG_FILE, 'w') as f:
                            json.dump(cfg, f, indent=2)
                    except Exception:
                        pass
                    return True
                else:
                    UI.warn("DEVICE", f"no appKey: {str(j)[:50]}")

            time.sleep(2)

        UI.err("DEVICE", f"fail after {max_retry} attempts")
        return False

    def ping(self):
        try:
            code, _, _ = self.api_post("/api/ping", None)
            return code == 200
        except InitDataExpired:
            raise

    def home(self):
        UI.step("HOME", "GET /api/home")
        code, j, txt = self.api_get("/api/home")
        if code != 200:
            UI.err("HOME", f"HTTP {code}: {txt[:50]}")
            return False

        if not isinstance(j, dict):
            UI.err("HOME", "response bukan dict")
            return False

        u = j.get("user", {})
        if not u or not u.get("id"):
            UI.err("HOME", "no user data — init_data expired?")
            raise InitDataExpired("home no user")

        self.user = u
        UI.set(
            user=u.get("username") or u.get("firstName", "?"),
            balance=f"{u.get('balance', 0):.6f}",
            total_earned=f"{u.get('totalEarned', 0):.6f}",
            ads_total=u.get("adsTotal", 0),
            tier=(u.get("tier") or {}).get("name", "-") if isinstance(u.get("tier"), dict) else "-",
        )

        self.networks = j.get("networks", []) or []
        if not self.networks:
            UI.err("HOME", "0 networks")
            return False

        UI.ok("HOME", f"{len(self.networks)} networks")
        return True

    def _all_networks_limited(self):
        if not self.networks:
            return False
        for net in self.networks:
            today = net.get("today", 0)
            limit = net.get("dailyLimit", 0)
            if today < limit:
                return False
        return True

    def watch_ad(self, network):
        """
        Return:
          reward (float)  → success
          "SKIP"          → network daily limit / cooldown
          "FAIL"          → error (network/HTTP/token)
          None            → fallback
        """
        nid = network["id"]
        name = network["name"]
        reward = network["reward"]
        today = network.get("today", 0)
        limit = network.get("dailyLimit", 0)
        sdk = network.get("sdk", "")
        sdk_cfg = network.get("sdkConfig") or {}

        if today >= limit:
            UI.warn("SKIP", f"{name}: limit"); return "SKIP"

        wait_until = network.get("waitUntil")
        if wait_until:
            wait_s = max(0, int((wait_until / 1000) - time.time()))
            if wait_s > 0:
                UI.warn("CD", f"{name}: {wait_s}s")
                UI.countdown(min(wait_s, 60), f"cd {name}")
                return "SKIP"

        time.sleep(random.uniform(2, 4))

        UI.step("START", f"#{nid} {name} +${reward}")
        body = {"networkId": nid}
        try:
            code, j, txt = self.api_post("/api/ads/start", body)
        except InitDataExpired:
            raise

        if code != 200:
            UI.err("START", f"{name}: HTTP {code}")
            if txt:
                try:
                    errj = json.loads(txt)
                    emsg = errj.get('error', str(errj))
                    ecode = errj.get('code', '?')
                    UI.warn("START", f"[{ecode}] {emsg[:50]}")
                except Exception:
                    UI.warn("START", f"body: {txt[:60]}")
            return "FAIL"

        if isinstance(j, dict) and j.get("blockType") == "RewardBlock":
            banners = j.get("banners", []) or []
            UI.info("START", f"banner reward ({len(banners)})")
            if banners:
                self._fire_banner_events(banners[0], label=f"start-{name}")

        token = j.get("token") if isinstance(j, dict) else None
        if not token:
            UI.err("START", f"{name}: no token")
            return "FAIL"

        if sdk == "adsgram" and not (isinstance(j, dict) and j.get("blockType") == "RewardBlock"):
            block_id = sdk_cfg.get("blockId", "")
            adv, err = self.adsgram_get_adv(block_id)
            if adv:
                self._fire_banner_events(adv[0], label=f"adsgram-{name}")

        watch_sec = random.choice([15, 16, 17, 18])
        UI.info("WATCH", f"{name}: {watch_sec}s")
        UI.countdown(watch_sec, f"watch {name}")

        UI.step("COMPLETE", f"{name}: submit")
        try:
            code, j2, txt2 = self.api_post("/api/ads/complete", {"token": token})
        except InitDataExpired:
            raise

        if code != 200:
            UI.err("COMPLETE", f"{name}: HTTP {code}")
            if txt2: UI.warn("COMPLETE", f"body: {txt2[:50]}")
            return "FAIL"

        got_reward = j2.get("reward", reward) if isinstance(j2, dict) else reward
        u = j2.get("user", {}) if isinstance(j2, dict) else {}
        if u:
            self.user = u
            UI.set(
                balance=f"{u.get('balance', 0):.6f}",
                total_earned=f"{u.get('totalEarned', 0):.6f}",
                ads_total=u.get("adsTotal", 0),
            )
        try:
            cur = float(UI.state.get("session_reward", 0.0))
            UI.set(session_reward=cur + float(got_reward),
                   session_ads=int(UI.state.get("session_ads", 0)) + 1,
                   last_reward=f"+${got_reward}")
        except Exception:
            pass

        UI.ok("DONE", f"{name}: +${got_reward} | bal ${self.user.get('balance',0):.6f}")
        return got_reward

    def run(self):
        sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()

        open_debug()

        cfg = self.get_config()
        self.init_data = cfg.get("init_data", "").strip()
        self.start_param = cfg.get("start_param", "").strip()
        self.fp = cfg.get("fp") or hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        self.did = cfg.get("did") or secrets.token_hex(16)
        self.app_key = cfg.get("app_key", "")

        if "fp" not in cfg:
            cfg["fp"] = self.fp; cfg["did"] = self.did
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=2)

        if not self.init_data:
            print(UI.c("  ✖ init_data kosong\n", "br_red")); return

        kv = self._parse_kv()
        missing = [k for k in ['query_id', 'user', 'auth_date', 'signature', 'hash'] if k not in kv]
        if missing:
            print(UI.c(f"\n  ✖ init_data missing: {', '.join(missing)}\n", "br_red"))
            sys.exit(1)

        auth_date = int(kv.get('auth_date', 0))
        age_sec = int(time.time()) - auth_date
        age_min = age_sec // 60
        age_str = f"{age_min}m" if age_min < 60 else f"{age_min//60}h{age_min%60}m"

        UI.set(state="INIT", session_reward=0.0, session_ads=0,
               last_reward="-", app_key=self.app_key or "-", dcs_variant="-",
               init_age=age_str, net_retry=0, ad_fails=0)
        UI.start_panel()

        UI.ok("INIT", f"query_id={kv['query_id'][:16]}… age={age_str}")

        if age_sec > INIT_DATA_MAX_AGE_SEC:
            UI.warn("INIT", f"init_data > 1 jam — mungkin expired")

        # ── 1. bootstrap — auto re-auth kalau expired ──
        reauth_count = 0
        while True:
            try:
                if self.bootstrap():
                    break
                UI.err("FATAL", "bootstrap failed")
                UI.stop_panel(); return
            except InitDataExpired:
                reauth_count += 1
                if reauth_count > MAX_REAUTH:
                    UI.err("FATAL", f"re-auth gagal {MAX_REAUTH}x — keluar")
                    UI.stop_panel(); return
                if not self.reauth():
                    UI.err("FATAL", "reauth gagal")
                    UI.stop_panel(); return

        # ── 2. device ──
        if not self.app_key:
            if not self.device():
                UI.err("FATAL", "device failed — gak dapet appKey")
                UI.stop_panel(); return
        else:
            UI.info("DEVICE", f"using cached appKey: {self.app_key[:16]}…")

        # ── 3. ping ──
        try:
            self.ping()
        except InitDataExpired:
            if not self.reauth():
                UI.stop_panel(); return

        stop_reason = "finished"

        cycle = 0
        while True:
            cycle += 1
            UI.set(cycle=cycle, state="RUNNING", phase="-")
            UI.info("CYCLE", f"Cycle #{cycle}")
            write_debug("")
            write_debug("=" * 70)
            write_debug(f"CYCLE #{cycle}")
            write_debug("=" * 70)

            # ── home — handle re-auth ──
            try:
                if not self.home():
                    UI.warn("CYCLE", "home fail — 30s")
                    UI.set(state="RETRY")
                    UI.countdown(30, "retry"); continue
                self.ping()
            except InitDataExpired:
                UI.warn("CYCLE", "init_data expired mid-run — re-auth")
                if not self.reauth():
                    UI.err("FATAL", "reauth gagal — keluar")
                    stop_reason = "reauth_failed"
                    break
                continue

            # ── Cek awal: semua network udah limit? ──
            if self._all_networks_limited():
                UI.ok("DONE", "Semua network daily limit — bot stop")
                UI.set(state="DONE", phase="all limited")
                write_debug("!!! ALL NETWORKS LIMITED — STOPPING")
                stop_reason = "all_limited"
                break

            any_done = False
            for net in self.networks:
                if not UI.state["running"]: break
                UI.set(state="RUNNING", phase=f"{net['name']}…")

                try:
                    got = self.watch_ad(net)
                except InitDataExpired:
                    UI.warn("WATCH", "init_data expired mid-watch — re-auth")
                    if not self.reauth():
                        stop_reason = "reauth_failed"
                        break
                    # break dari for loop biar cycle di-restart
                    got = None
                    break

                if got == "FAIL":
                    fails = int(UI.state.get("ad_fails", 0)) + 1
                    UI.set(ad_fails=fails)
                    UI.warn("FAIL", f"{net['name']}: fail {fails}/{AD_FAIL_LIMIT}")
                    write_debug(f"!!! AD FAIL {fails}/{AD_FAIL_LIMIT} on {net['name']}")
                    if fails >= AD_FAIL_LIMIT:
                        UI.err("STOP", f"{AD_FAIL_LIMIT}x ads fail — bot stop")
                        UI.set(state="DONE", phase=f"{AD_FAIL_LIMIT}x fail")
                        write_debug(f"!!! AD FAIL LIMIT {AD_FAIL_LIMIT} REACHED — STOPPING")
                        stop_reason = "ad_fail_limit"
                        break
                elif got == "SKIP" or got is None:
                    pass
                else:
                    UI.set(ad_fails=0)
                    any_done = True

                pause = random.randint(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                UI.set(state="PAUSE")
                UI.warn("PAUSE", f"human pause {pause}s")
                UI.countdown(pause, "human pause")

            if stop_reason in ("ad_fail_limit", "reauth_failed"):
                break

            # ── Refresh network list ──
            try:
                if self.home():
                    if self._all_networks_limited():
                        UI.ok("DONE", "Semua network daily limit — bot stop")
                        UI.set(state="DONE", phase="all limited")
                        write_debug("!!! ALL NETWORKS LIMITED AFTER CYCLE — STOPPING")
                        stop_reason = "all_limited"
                        break
            except InitDataExpired:
                if not self.reauth():
                    stop_reason = "reauth_failed"
                    break
                continue

            if not any_done:
                UI.warn("CYCLE", "no ad — 60s")
                UI.countdown(60, "idle")
            else:
                UI.countdown(10, "refresh")

        # ── Summary akhir ──
        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()

        print()
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c("  ✓ BOT SELESAI", "br_green"))
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c(f"  Reason      : {stop_reason}", "white"))
        print(UI.c(f"  User        : {UI.state['user']}", "white"))
        print(UI.c(f"  Balance     : ${UI.state['balance']}", "br_yellow"))
        print(UI.c(f"  Session     : +${UI.state['session_reward']:.6f} ({UI.state['session_ads']} ads)", "br_green"))
        print(UI.c(f"  Net retries : {UI.state['net_retry']}", "yellow"))
        print(UI.c(f"  Ad fails    : {UI.state['ad_fails']}/{AD_FAIL_LIMIT}", "yellow"))
        print(UI.c(f"  Debug log   : {DEBUG_FILE}", "gray"))
        print(UI.c("═" * 64, "br_cyan"))
        print()


# ═══════════════════════════════════════════════════════════════
#  ENTRY
# ═══════════════════════════════════════════════════════════════
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    UI.banner()
    try:
        AdTubesBot().run()
    except KeyboardInterrupt:
        raise
    except InitDataExpired:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ init_data expired — keluar{RESET}\n")
    except Exception as e:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ fatal: {e}{RESET}\n")
        write_debug(f"!!! FATAL: {type(e).__name__}: {e}")
        import traceback
        write_debug(traceback.format_exc())
        traceback.print_exc(); return
    finally:
        close_debug()


def _on_sigint(sig, frame):
    try: signal.signal(signal.SIGINT, signal.SIG_DFL)
    except Exception: pass
    try: UI.stop_panel()
    except Exception: pass
    try:
        sys.stdout.write(f"\n{Fore.YELLOW}  ! CTRL+C — keluar{RESET}\n")
        sys.stdout.write(f"{Fore.WHITE}  Debug → {DEBUG_FILE}{RESET}\n\n")
        sys.stdout.flush()
    except Exception: pass
    close_debug()
    os._exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _on_sigint)
    try:
        main()
    except KeyboardInterrupt:
        _on_sigint(signal.SIGINT, None)
