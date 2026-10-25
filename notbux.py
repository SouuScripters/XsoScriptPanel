#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   NOTBUX AUTO WATCH — SOUU ENGINE Edition v4.6               ║
║   FIX : banner numpuk (clear scrollback)                     ║
║   FIX : merge ads dari /earn/data + /tasks/available         ║
║   FIX : POST /start sebelum WATCH + CLAIM (claim 400 fix)    ║
║   FEAT : live dashboard watch ads                            ║
║   FEAT : auto-loop sampe semua iklan habis                   ║
║   FEAT : auto re-auth kalau init_data expired                ║
║   NEW  : aviso_youtube via direct aviso (userId + userSig)   ║
║   NEW  : aviso start payload matches real client body        ║
║   NEW  : startup menu (Start All / Aviso Only / Config)      ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests, re, json, time, sys, os, random, signal
import urllib.parse
import urllib3
from datetime import datetime
from collections import deque
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
init(autoreset=True)
urllib3.disable_warnings()

VERSION = "4.6"
HOST = "https://notbux.click"
API = f"{HOST}/api"
CONFIG_FILE = "config_notbux.json"

AVISO_API = "https://aviso.bz/api/v1"
AVISO_ORIGIN = "https://notbux.click"
AVISO_PLATFORM = "Linux aarch64"

BOX_WIDTH = 62
LOG_LINES = 8
ANSI_RE = re.compile(r'\033\[[0-9;]*m')

TELEGRAM_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
               "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

HTTP_MAX_RETRY = 5
HTTP_BACKOFF_BASE = 3
REQUEST_TIMEOUT = 30
AD_WATCH_MIN = 30
AD_WATCH_MAX = 35
HUMAN_PAUSE_MIN = 2
HUMAN_PAUSE_MAX = 5
MAX_EMPTY_CYCLES = 3
MAX_REAUTH = 3

AVISO_FALLBACK_WATCH = 35
AVISO_CD_NO_TASK = 60
AVISO_CD_AUTH_FAIL = 120
AVISO_CD_START_FAIL = 45
AVISO_CD_COMPLETE_FAIL = 30

CLEAR = "\033[2J\033[3J\033[H"

_IN_MENU = False


class InitDataExpired(Exception):
    pass


# ═══════════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════════
class UI:
    state = {
        "title": "NOTBUX AUTO WATCH",
        "subtitle": "─────── SOUU ENGINE ───────",
        "running": False,
        "stop_requested": False,
        "cycle": 0,
        "host": HOST,
        "user": "-",
        "user_id": "-",
        "balance": 0,
        "start_balance": 0,
        "state": "INIT",
        "phase": "-",
        "cooldown": 0,
        "start_ts": int(time.time()),
        "last_reward": "-",
        "session_reward": 0,
        "session_ads": 0,
        "net_retry": 0,
        "ads_summary": [],
        "watching_name": "-",
        "watching_reward": "-",
        "watching_progress": 0.0,
        "watching_total": 0,
        "reauth_count": 0,
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
        buf = CLEAR
        buf += UI.top() + "\n"
        buf += UI.row(UI.bold(UI.gradient(s["title"], 51, 213))) + "\n"
        buf += UI.row(UI.dim(s["subtitle"])) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold("USER")) + "\n"
        buf += UI.row("├─ " + UI.pad("Name", 11) + ": " + UI.trunc(UI.fg(226, str(s["user"])), 30)) + "\n"
        buf += UI.row("├─ " + UI.pad("TG ID", 11) + ": " + UI.trunc(UI.fg(226, str(s["user_id"])), 30)) + "\n"
        bal_str = f"{int(s['balance']):,}"
        buf += UI.row("├─ " + UI.pad("Balance", 11) + ": " + UI.fg(46, f"{bal_str} coins")) + "\n"
        buf += UI.row("└─ " + UI.pad("Started", 11) + ": " + UI.fg(213, str(int(s['start_balance']))) + " coins") + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold("AD NETWORKS")) + "\n"
        ads = s.get("ads_summary", [])
        if not ads:
            buf += UI.row("└─ " + UI.dim("(belum load)")) + "\n"
        else:
            for i, a in enumerate(ads):
                last = (i == len(ads) - 1)
                branch = "└─" if last else "├─"
                name = a["name"][:14]
                views = a["views"]
                mx = a["max"]
                cd = a["cd"]
                st = a["status"]

                if st == "ready":
                    color, tag = 46, "READY"
                elif st == "cooldown":
                    color, tag = 208, f"CD {cd}s"
                elif st == "limited":
                    color, tag = 240, "LIMIT"
                elif st == "watching":
                    color, tag = 213, "WATCH"
                elif st == "skip":
                    color, tag = 240, "SKIP"
                else:
                    color, tag = 226, st.upper()

                line = (branch + " " + UI.pad(name, 15) +
                        " " + UI.fg(226, f"{views}/{mx}") +
                        " " + UI.fg(color, UI.pad(tag, 8)))
                buf += UI.row(line) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold("WATCHING")) + "\n"
        wname = s.get("watching_name", "-")
        wrew = s.get("watching_reward", "-")
        wpct = float(s.get("watching_progress", 0.0))
        wtotal = int(s.get("watching_total", 0))
        bar_len = 34
        filled = int(wpct * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        if wname == "-":
            buf += UI.row("├─ " + UI.dim("idle — menunggu iklan…")) + "\n"
            buf += UI.row("├─ [" + UI.dim("░" * bar_len) + "]") + "\n"
        else:
            buf += UI.row("├─ " + UI.fg(226, UI.trunc(wname, 40))) + "\n"
            buf += UI.row("├─ [" + UI.fg(46, bar) + "] " + UI.fg(226, f"{int(wpct*100)}%")) + "\n"
        remain = wtotal - int(wpct * wtotal) if wtotal else 0
        buf += UI.row("└─ " + UI.pad("Reward", 9) + ": " + UI.fg(46, str(wrew)) +
                      "  " + UI.pad("Sisa", 5) + ": " + UI.fg(208, f"{remain}s")) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold("SESSION")) + "\n"
        buf += UI.row("├─ " + UI.pad("Cycle", 11) + ": " + UI.fg(226, str(s["cycle"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Ads watched", 11) + ": " + UI.fg(226, str(s["session_ads"]))) + "\n"
        srew = s.get("session_reward", 0)
        buf += UI.row("├─ " + UI.pad("Reward", 11) + ": " + UI.fg(46, f"+{int(srew)} coins")) + "\n"
        buf += UI.row("├─ " + UI.pad("Last", 11) + ": " + UI.fg(226, str(s["last_reward"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Net retry", 11) + ": " + UI.fg(208, str(s.get("net_retry", 0)))) + "\n"
        buf += UI.row("└─ " + UI.pad("Re-auth", 11) + ": " + UI.fg(213, str(s.get("reauth_count", 0)))) + "\n"
        buf += UI.mid() + "\n"

        phase = str(s["phase"])
        if int(s["cooldown"]) > 0: phase += f" · {int(s['cooldown'])}s"
        state_color = {"RUNNING": 46, "WAITING": 208, "ERROR": 196,
                       "INIT": 240, "DONE": 46, "PAUSE": 213, "RETRY": 208,
                       "WATCHING": 213, "COOLDOWN": 208, "REAUTH": 196}.get(s["state"], 226)
        buf += UI.row(UI.bold("STATUS")) + "\n"
        buf += UI.row("├─ " + UI.pad("State", 11) + ": " + UI.fg(state_color, str(s["state"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Phase", 11) + ": " + UI.trunc(UI.fg(208, phase), 30)) + "\n"
        buf += UI.mid() + "\n"

        logs = list(UI.logs)[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(logs): buf += UI.row(UI.fmt_log(logs[i])) + "\n"
            else: buf += UI.blank() + "\n"

        buf += UI.bot() + "\n"
        buf += "\n   " + UI.bold(UI.fg(46, "BOT RUNNING")) + " " + UI.dim("•") + " " + \
               UI.fg(51, datetime.now().strftime("%H:%M:%S")) + "\n"
        buf += "   " + UI.dim("CTRL+C = balik ke menu") + "\n\n"
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
            if UI.state.get("stop_requested"): return
            UI.set(phase=label, cooldown=i)
            if UI.state["running"]: UI.render()
            time.sleep(1)
        UI.set(phase="-", cooldown=0)

    @staticmethod
    def watch_timer(duration, name, reward):
        UI.set(watching_name=name, watching_reward=reward,
               watching_total=duration, watching_progress=0.0,
               state="WATCHING")
        for i in range(1, duration + 1):
            if not UI.state["running"] or UI.state.get("stop_requested"): break
            UI.set(watching_progress=i / duration,
                   phase=f"watch {name} {i}/{duration}")
            UI.render()
            time.sleep(1)
        UI.set(watching_name="-", watching_reward="-",
               watching_progress=0.0, watching_total=0)

    @staticmethod
    def c(text, color):
        cmap = {"reset": 0, "bold": 1, "dim": 2,
                "red": 196, "green": 46, "yellow": 226, "blue": 51, "magenta": 201,
                "cyan": 51, "white": 15, "gray": 240, "orange": 208,
                "br_red": 196, "br_green": 46, "br_yellow": 226, "br_cyan": 51}
        return f"\033[{cmap.get(color, 0)}m{text}\033[0m"


# ═══════════════════════════════════════════════════════════════
#  MENU
# ═══════════════════════════════════════════════════════════════
def _menu_header():
    W_ = BOX_WIDTH
    def line(c): return UI.fg(51, "║") + UI.pad(" " + c, W_) + UI.fg(51, "║")
    print(UI.fg(51, "╔" + "═" * W_ + "╗"))
    print(line(UI.bold(UI.gradient("NOTBUX AUTO WATCH — MENU", 51, 213))))
    print(line(UI.dim("─────── SOUU ENGINE v" + VERSION + " ───────")))
    print(UI.fg(51, "╠" + "═" * W_ + "╣"))
    print(line(UI.fg(46, "  [1]") + "  Start All " + UI.dim("(kecuali aviso)")))
    print(line(UI.fg(46, "  [2]") + "  Aviso Only"))
    print(line(UI.fg(46, "  [3]") + "  Config initData"))
    print(line(UI.fg(196, "  [0]") + "  Exit"))
    print(UI.fg(51, "╚" + "═" * W_ + "╝"))
    print()


def menu():
    global _IN_MENU
    while True:
        _IN_MENU = True
        os.system('cls' if os.name == 'nt' else 'clear')
        _menu_header()
        try:
            choice = input(UI.c("  pilih > ", "br_cyan")).strip()
        except EOFError:
            _IN_MENU = False
            return "0"
        if choice in ("1", "2", "3", "0"):
            _IN_MENU = False
            return choice
        # invalid — loop


# ═══════════════════════════════════════════════════════════════
#  CONFIG EDITOR
# ═══════════════════════════════════════════════════════════════
def config_menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    print()
    print(UI.c("═" * BOX_WIDTH, "br_cyan"))
    print(UI.c("  CONFIG — initData", "br_cyan"))
    print(UI.c("═" * BOX_WIDTH, "br_cyan"))
    print()

    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        except Exception:
            pass

    cur = cfg.get("init_data", "").strip()
    if cur:
        preview = cur[:56] + ("…" if len(cur) > 56 else "")
        print(UI.c(f"  current : {preview}", "gray"))
        try:
            kv = dict(p.split("=", 1) for p in cur.split("&") if "=" in p)
            ad = int(kv.get("auth_date", "0"))
            if ad:
                age = int(time.time()) - ad
                print(UI.c(f"           age {age//60}m {age%60}s", "gray"))
            uname = kv.get("user", "")
            if uname:
                try:
                    u = json.loads(urllib.parse.unquote(uname))
                    nm = u.get("username") or u.get("first_name") or "?"
                    print(UI.c(f"           user {nm}", "gray"))
                except Exception:
                    pass
        except Exception:
            pass
    else:
        print(UI.c("  current : (kosong)", "gray"))
    print()
    print(UI.c("  Ambil dari Telegram Desktop:", "white"))
    print(UI.c("  Console (Ctrl+Shift+I) → copy(Telegram.WebApp.initData)", "br_cyan"))
    print(UI.c("  atau Network tab → cari notbux.click → copy header 'authorization'", "gray"))
    print()
    print(UI.c("  Kosongkan + Enter buat batal.", "gray"))
    print()
    print(UI.c("  init_data baru > ", "white"), end="")

    try:
        new = input().strip()
    except EOFError:
        new = ""
    except KeyboardInterrupt:
        return

    if not new:
        print(UI.c("\n  batal.\n", "gray"))
        time.sleep(1)
        return

    required = ['user', 'auth_date']
    missing = [k for k in required if f"{k}=" not in new]
    if missing:
        print(UI.c(f"\n  ✖ gak lengkap: missing {', '.join(missing)}", "br_red"))
        time.sleep(2)
        return

    cfg["init_data"] = new
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        print(UI.c("\n  ✓ saved.\n", "br_green"))
    except Exception as e:
        print(UI.c(f"\n  ✖ gagal: {e}\n", "br_red"))
    time.sleep(1)


# ═══════════════════════════════════════════════════════════════
#  RE-AUTH PROMPT (in-run)
# ═══════════════════════════════════════════════════════════════
def prompt_new_init_data():
    was_running = UI.state["running"]
    UI.state["running"] = False
    sys.stdout.write(CLEAR)
    sys.stdout.flush()

    print()
    print(UI.c("═" * 62, "br_yellow"))
    print(UI.c("  ⚠  INIT DATA EXPIRED / INVALID", "br_yellow"))
    print(UI.c("═" * 62, "br_yellow"))
    print(UI.c("  Ambil init_data baru dari Telegram Desktop:", "white"))
    print(UI.c("  → Ctrl+Shift+I → Console → ketik:", "gray"))
    print(UI.c("     copy(Telegram.WebApp.initData)", "br_cyan"))
    print()
    print(UI.c("  Kosongkan + Enter buat stop (balik ke menu).", "gray"))
    print()
    print(UI.c("  init_data : ", "white"), end="")

    try:
        new_init = input().strip()
    except (EOFError, KeyboardInterrupt):
        new_init = ""

    if not new_init:
        UI.state["running"] = was_running
        return None

    required = ['user', 'auth_date']
    missing = [k for k in required if f"{k}=" not in new_init]
    if missing:
        print(UI.c(f"\n  ✖ init_data gak lengkap. Missing: {', '.join(missing)}", "br_red"))
        print(UI.c("  Tekan Enter buat tetep lanjut...", "gray"), end="")
        try: input()
        except (EOFError, KeyboardInterrupt): pass

    UI.state["running"] = was_running
    return new_init


def save_init_data(new_init):
    try:
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        cfg["init_data"] = new_init
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception as e:
        print(UI.c(f"  ✖ gagal simpen config: {e}", "br_red"))
        return False


# ═══════════════════════════════════════════════════════════════
#  SESSION
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
class NotBuxBot:
    AD_ORDER = ["adsgram", "monetag", "taskgram", "onclicka", "adexium"]

    def __init__(self, init_data, include_aviso=True, aviso_only=False):
        self.session = make_session()
        self.init_data = init_data
        self.user = {}
        self.ads = []
        self.user_id = "-"
        self.username = "-"
        self.balance = 0
        self.start_balance = 0
        self.include_aviso = include_aviso
        self.aviso_only = aviso_only

        self._aviso_keys = None
        self._aviso_identified = False
        self._aviso_session = None
        self.aviso_cooldown = 0.0

    # ── HEADERS / RETRY / AUTH-ERR ─────────────────────────────
    def _headers(self):
        return {
            "authorization": self.init_data,
            "user-agent": TELEGRAM_UA,
            "accept": "*/*",
            "content-type": "application/json",
            "origin": HOST,
            "referer": f"{HOST}/",
            "x-requested-with": "org.telegram.messenger.web",
            "sec-ch-ua-platform": '"Android"',
            "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            "sec-ch-ua-mobile": "?1",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _is_transient(self, exc):
        msg = str(exc).lower()
        keys = ['connection aborted', 'connection reset', 'connection refused',
                'read timed out', 'timed out', 'timeout', 'ssl error', 'sslerror',
                'temporary failure', 'remote end closed', 'connection broken',
                'protocolerror', 'protocol error', 'badstatusline', 'bad gateway',
                'service unavailable', 'server disconnected', 'incompleteread']
        return any(k in msg for k in keys)

    def _request_with_retry(self, method, url, headers, body=None):
        last_exc = None
        for attempt in range(1, HTTP_MAX_RETRY + 1):
            try:
                if method == "GET":
                    r = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                else:
                    r = self.session.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
                return r, None
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                    requests.exceptions.SSLError, requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ContentDecodingError, requests.exceptions.ProxyError) as e:
                last_exc = e
                if not self._is_transient(e):
                    return None, e
                if attempt < HTTP_MAX_RETRY:
                    wait = HTTP_BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 2)
                    UI.warn("NET", f"{type(e).__name__} (try {attempt}/{HTTP_MAX_RETRY}) — retry {int(wait)}s")
                    UI.set(net_retry=int(UI.state.get("net_retry", 0)) + 1)
                    if attempt >= 2:
                        try: self.session.close()
                        except Exception: pass
                        self.session = make_session()
                    time.sleep(wait)
                else:
                    return None, e
        return None, last_exc

    def _is_auth_error(self, code, body_text):
        if code in (401, 403):
            return True
        if not body_text: return False
        low = body_text.lower()
        hints = ['unauthorized', 'invalid init', 'expired', 'forbidden']
        if code != 200 and any(h in low for h in hints):
            return True
        return False

    def api_get(self, path):
        url = f"{API}{path}"
        headers = self._headers()
        r, err = self._request_with_retry("GET", url, headers)
        if r is None:
            UI.err("HTTP", f"{type(err).__name__}: {str(err)[:40]}")
            return 0, None, str(err)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        return r.status_code, self._try_json(r), r.text

    def api_post(self, path, body=None):
        url = f"{API}{path}"
        headers = self._headers()
        data = json.dumps(body) if body is not None else ""
        r, err = self._request_with_retry("POST", url, headers, data)
        if r is None:
            UI.err("HTTP", f"{type(err).__name__}: {str(err)[:40]}")
            return 0, None, str(err)
        if self._is_auth_error(r.status_code, r.text):
            raise InitDataExpired(f"HTTP {r.status_code}")
        return r.status_code, self._try_json(r), r.text

    def _try_json(self, r):
        try: return r.json()
        except Exception: return {"_raw": r.text[:200]}

    # ── RE-AUTH ────────────────────────────────────────────────
    def reauth(self):
        UI.warn("AUTH", "init_data expired — minta paste baru")
        try:
            new_init = prompt_new_init_data()
        except KeyboardInterrupt:
            raise

        if not new_init:
            UI.err("AUTH", "no init_data — stop")
            return False

        self.init_data = new_init
        try: self.session.close()
        except Exception: pass
        self.session = make_session()

        self.user = {}
        self.ads = []
        self.balance = 0

        self._aviso_keys = None
        self._aviso_identified = False
        self.aviso_cooldown = 0.0
        try:
            if self._aviso_session is not None:
                self._aviso_session.close()
        except Exception:
            pass
        self._aviso_session = None

        if save_init_data(new_init):
            UI.ok("AUTH", "init_data baru disimpan")
        else:
            UI.warn("AUTH", "gagal simpen, tetep lanjut pakai yang baru")

        UI.set(reauth_count=int(UI.state.get("reauth_count", 0)) + 1)
        return True

    # ── FETCH USER / ADS ───────────────────────────────────────
    def fetch_user(self):
        UI.step("USER", "GET /api/user/me")
        code, j, txt = self.api_get("/user/me")
        if code != 200 or not isinstance(j, dict):
            UI.err("USER", f"HTTP {code}: {txt[:50]}")
            return False
        if j.get("status") != "success":
            UI.warn("USER", f"status: {j.get('status')}")
            return False

        self.user = j
        self.user_id = j.get("telegram_id", "-")
        self.username = (j.get("username") or j.get("first_name") or "?")
        self.balance = int(j.get("balance", 0))

        UI.set(user=self.username, user_id=self.user_id, balance=self.balance)
        UI.ok("USER", f"{self.username} • {self.balance} coins")
        return True

    def _normalize_ad(self, a, source):
        aid = a.get("id") or "?"
        name = a.get("name") or a.get("title") or aid
        mx = a.get("maxViews")
        if mx is None:
            mx = a.get("max_views") or 0
        views = a.get("views", 0)
        cd = a.get("cooldown", 0)
        return {
            "id": aid,
            "name": name,
            "reward": a.get("reward", 0),
            "views": int(views) if views is not None else 0,
            "maxViews": int(mx) if mx else 0,
            "cooldown": int(cd) if cd else 0,
            "isWatching": bool(a.get("isWatching", False)),
            "canClaim": bool(a.get("canClaim", False)),
            "source": source,
        }

    def fetch_ads(self):
        merged = {}

        code, j, txt = self.api_get("/earn/data")
        if code == 200 and isinstance(j, dict):
            for a in (j.get("ads", []) or []):
                n = self._normalize_ad(a, "earn")
                merged[n["id"]] = n

        code, j, txt = self.api_get("/tasks/available")
        if code == 200 and isinstance(j, dict):
            for a in (j.get("ads", []) or []):
                n = self._normalize_ad(a, "tasks")
                if n["id"] not in merged:
                    merged[n["id"]] = n

        self.ads = list(merged.values())

        if self.ads:
            UI.ok("ADS", f"{len(self.ads)} network(s) merged")
        else:
            UI.warn("ADS", "0 network — cek auth / server")
        return True

    def _ads_summary(self):
        out = []
        now_ts = time.time()
        for a in self.ads:
            aid = a.get("id")

            # filter per mode
            if self.aviso_only and aid != "aviso_youtube":
                continue

            mx = a.get("maxViews", 0)
            views = a.get("views", 0)
            cd = a.get("cooldown", 0)
            watching = a.get("isWatching", False)

            if aid == "aviso_youtube":
                if not self.include_aviso and not self.aviso_only:
                    st = "skip"
                elif now_ts < self.aviso_cooldown:
                    st = "cooldown"
                    cd = int(self.aviso_cooldown - now_ts)
                elif watching:
                    st = "watching"
                else:
                    st = "ready"
            elif mx and views >= mx:
                st = "limited"
            elif watching:
                st = "watching"
            elif cd > 0:
                st = "cooldown"
            else:
                st = "ready"

            out.append({
                "id": aid, "name": a["name"],
                "views": views, "max": mx,
                "cd": cd, "status": st,
                "reward": a.get("reward", 0),
            })
        return out

    # ═══════════════════════════════════════════════════════════
    #  AVISO (direct)
    # ═══════════════════════════════════════════════════════════
    def _get_aviso_session(self):
        if self._aviso_session is None:
            s = make_session()
            s.verify = False
            self._aviso_session = s
        return self._aviso_session

    def _aviso_headers(self, keys, extra=None):
        h = {
            "Host": "aviso.bz",
            "User-Agent": TELEGRAM_UA,
            "Accept": "*/*",
            "Accept-Language": "en",
            "Content-Type": "application/json",
            "Origin": AVISO_ORIGIN,
            "Referer": AVISO_ORIGIN + "/",
            "X-API-Key": keys["api_key"],
            "X-Requested-With": "org.telegram.messenger.web",
            "Sec-Ch-Ua": '"Android WebView";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=1, i",
        }
        if extra:
            h.update(extra)
        return h

    def _aviso_get_keys(self):
        code, j, txt = self.api_get("/tasks/aviso/auth")
        if code == 200 and isinstance(j, dict) and j.get("api_key"):
            return {
                "api_key": j["api_key"],
                "user_hash": j.get("user_hash", ""),
                "user_id": str(j.get("user_id", "")),
                "user_sig": j.get("user_sig", ""),
            }
        UI.err("AVISO", f"auth HTTP {code}: {txt[:40]}")
        return None

    def _aviso_identify(self, keys):
        fp = {
            "fp": "d0de63b9837a4b9c5f7236b8bc7318d0",
            "hashFont": "f730c0cc627b3b3d7db9f459836db692",
            "langs": "id, en-US, en",
            "timezone": "Asia/Jakarta",
            "platform": AVISO_PLATFORM,
            "gpu": "Qualcomm~Adreno (TM) 640",
            "screen": "1080x2400",
            "memory": 8,
            "cpuCores": 8,
        }
        body = {
            "hash": keys["user_hash"],
            "ip": None,
            "userAgent": TELEGRAM_UA,
            "fingerprint": fp,
        }
        try:
            r = self._get_aviso_session().post(
                f"{AVISO_API}/youtube/tasks/identify",
                data=json.dumps(body),
                headers=self._aviso_headers(keys),
                timeout=REQUEST_TIMEOUT,
            )
            return r.json() if r.status_code < 400 else None
        except Exception as e:
            UI.warn("AVISO", f"identify err: {str(e)[:40]}")
            return None

    def _aviso_available(self, keys):
        q = urllib.parse.urlencode({
            "hash": keys["user_hash"],
            "platform": AVISO_PLATFORM,
        })
        try:
            r = self._get_aviso_session().get(
                f"{AVISO_API}/youtube/tasks/available?{q}",
                headers=self._aviso_headers(keys),
                timeout=REQUEST_TIMEOUT,
            )
            return r.json() if r.status_code < 400 else None
        except Exception as e:
            UI.warn("AVISO", f"available err: {str(e)[:40]}")
            return None

    def _aviso_start(self, keys, task_id, typ="ads"):
        body = {
            "taskId": task_id,
            "hash": keys["user_hash"],
            "type": typ,
            "platform": AVISO_PLATFORM,
            "userId": keys["user_id"],
            "userSig": keys["user_sig"],
        }
        try:
            r = self._get_aviso_session().post(
                f"{AVISO_API}/youtube/tasks/start",
                data=json.dumps(body),
                headers=self._aviso_headers(keys),
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code >= 400:
                UI.warn("AVISO", f"start HTTP {r.status_code}: {r.text[:50]}")
                return None
            return r.json()
        except Exception as e:
            UI.warn("AVISO", f"start err: {str(e)[:40]}")
            return None

    def _aviso_timer(self, keys, attempt_id, watched, token):
        body = {"attemptId": attempt_id, "action": "complete", "watchedTime": watched}
        h = self._aviso_headers(keys)
        if token:
            h.pop("X-API-Key", None)
            h["X-Attempt-Token"] = token
        try:
            r = self._get_aviso_session().post(
                f"{AVISO_API}/youtube/tasks/timer-status",
                data=json.dumps(body),
                headers=h,
                timeout=REQUEST_TIMEOUT,
            )
            return r.json() if r.status_code < 400 else None
        except Exception:
            return None

    def _aviso_complete(self, keys, attempt_id, token):
        body = {"attemptId": attempt_id}
        h = self._aviso_headers(keys)
        if token:
            h.pop("X-API-Key", None)
            h["X-Attempt-Token"] = token
        try:
            r = self._get_aviso_session().post(
                f"{AVISO_API}/youtube/tasks/complete",
                data=json.dumps(body),
                headers=h,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code >= 400:
                UI.warn("AVISO", f"complete HTTP {r.status_code}: {r.text[:50]}")
                return None
            return r.json()
        except Exception as e:
            UI.warn("AVISO", f"complete err: {str(e)[:40]}")
            return None

    def _aviso_extract_token(self, url):
        if not url:
            return ""
        try:
            q = urllib.parse.urlparse(url).query
            p = urllib.parse.parse_qs(q)
            return p.get("token", [""])[0]
        except Exception:
            return ""

    def _find_aviso_youtube_task(self, avail):
        if not isinstance(avail, dict):
            return None
        for key in ("ads", "youtube", "like"):
            for t in (avail.get(key) or []):
                if not isinstance(t, dict):
                    continue
                url = t.get("url") or ""
                if "youtube.com" in url or "youtu.be" in url:
                    return t
                title = (t.get("title") or "").lower()
                if "youtube" in title:
                    return t
        return None

    def _watch_aviso(self):
        if not self._aviso_keys:
            self._aviso_keys = self._aviso_get_keys()
        if not self._aviso_keys:
            self.aviso_cooldown = time.time() + AVISO_CD_AUTH_FAIL
            return "FAIL"

        keys = self._aviso_keys
        UI.dbg("AVISO", f"hash {keys['user_hash'][:12]}… id {keys['user_id']}")

        if not self._aviso_identified:
            UI.step("AVISO", "POST tasks/identify")
            ident = self._aviso_identify(keys)
            if ident and (ident.get("id") or ident.get("ok")):
                self._aviso_identified = True
                UI.dbg("AVISO", f"identified id={ident.get('id','?')}")
            else:
                UI.warn("AVISO", "identify returned nothing — tetap lanjut")

        UI.step("AVISO", "GET tasks/available")
        avail = self._aviso_available(keys)
        if not avail:
            self.aviso_cooldown = time.time() + AVISO_CD_NO_TASK
            return "RETRY"

        task = self._find_aviso_youtube_task(avail)
        if not task:
            UI.warn("AVISO", "no youtube task in aviso pool")
            self.aviso_cooldown = time.time() + AVISO_CD_NO_TASK
            return "RETRY"

        try:
            tid = int(task.get("id") or 0)
        except (ValueError, TypeError):
            tid = 0
        title = str(task.get("title") or task.get("name") or f"yt#{tid}")[:24]
        if tid <= 0:
            self.aviso_cooldown = time.time() + AVISO_CD_NO_TASK
            return "RETRY"

        UI.step("AVISO", f"start #{tid} {title}")
        s = self._aviso_start(keys, tid, "ads")
        if not s:
            self.aviso_cooldown = time.time() + AVISO_CD_START_FAIL
            return "FAIL"

        try:
            attempt_id = int(s.get("attemptId") or 0)
        except (ValueError, TypeError):
            attempt_id = 0
        try:
            duration = int(s.get("duration") or 0)
        except (ValueError, TypeError):
            duration = 0
        url = str(s.get("url") or "")
        token = self._aviso_extract_token(url)

        if attempt_id <= 0:
            UI.err("AVISO", "no attemptId in start response")
            self.aviso_cooldown = time.time() + AVISO_CD_START_FAIL
            return "FAIL"

        if duration <= 0:
            duration = random.randint(30, AVISO_FALLBACK_WATCH)

        UI.step("AVISO", f"watch {duration}s • {title}")
        UI.watch_timer(duration, f"Aviso · {title}", f"#{tid}")

        try:
            self._aviso_timer(keys, attempt_id, duration, token)
        except Exception:
            pass

        UI.step("AVISO", f"complete #{tid}")
        cres = self._aviso_complete(keys, attempt_id, token)
        if not cres:
            self.aviso_cooldown = time.time() + AVISO_CD_COMPLETE_FAIL
            return "FAIL"

        if cres.get("code") == "task_already_processed":
            UI.ok("AVISO", f"✓ #{tid} already done")
            self.aviso_cooldown = 0
            return "done"

        earned = cres.get("earned")
        if earned is None:
            earned = cres.get("amount")
        cur = str(cres.get("currency", "usd"))
        if earned is not None:
            try:
                human = (f"+${float(earned):.5f}" if cur == "usd"
                         else f"+{float(earned):.3f}{cur.upper()}")
            except (ValueError, TypeError):
                human = str(earned)
        else:
            human = "ok"

        UI.ok("AVISO", f"✓ {title}: {human}")
        self.aviso_cooldown = 0

        try:
            self.fetch_user()
        except InitDataExpired:
            pass

        UI.set(
            session_ads=int(UI.state.get("session_ads", 0)) + 1,
            last_reward=human,
        )
        return human

    # ═══════════════════════════════════════════════════════════
    #  WATCH AD — dispatch
    # ═══════════════════════════════════════════════════════════
    def watch_ad(self, ad):
        aid = ad.get("id")

        if aid == "aviso_youtube":
            return self._watch_aviso()

        name = ad.get("name") or aid
        reward = ad.get("reward", 0)

        cd = ad.get("cooldown", 0)
        if cd > 0:
            wait_s = min(int(cd), 60)
            UI.warn("CD", f"{name}: server cd {cd}s")
            UI.set(state="COOLDOWN")
            UI.countdown(wait_s, f"cd {name}")
            return "RETRY"

        UI.step("START", f"POST /tasks/ads/{aid}/start")
        code, j, txt = self.api_post(f"/tasks/ads/{aid}/start", None)
        if code != 200:
            detail = ""
            if isinstance(j, dict):
                detail = str(j.get("detail") or j.get("message") or "")
                if not detail and "_raw" in j:
                    detail = str(j["_raw"])[:80]
            elif txt:
                detail = txt[:80]
            UI.err("START", f"{name}: HTTP {code} {detail[:40]}")
            low = detail.lower()
            if "cooldown" in low or "watching" in low or "already" in low:
                ad["cooldown"] = 60
                return "RETRY"
            return "FAIL"

        server_duration = 0
        if isinstance(j, dict):
            try:
                server_duration = int(j.get("duration") or 0)
            except (ValueError, TypeError):
                server_duration = 0
            if j.get("status") not in ("started", "success", None):
                UI.warn("START", f"{name}: status={j.get('status')}")

        if server_duration > 0:
            duration = server_duration + 2
        else:
            duration = random.randint(AD_WATCH_MIN, AD_WATCH_MAX)
        UI.step("WATCH", f"{name} • {duration}s • +{reward} coins")
        UI.watch_timer(duration, name, f"+{reward}")

        UI.step("CLAIM", f"POST /tasks/ads/{aid}/claim")
        code, j, txt = self.api_post(f"/tasks/ads/{aid}/claim", None)

        if code != 200:
            detail = ""
            if isinstance(j, dict):
                detail = str(j.get("detail") or j.get("message") or "")
                if not detail and "_raw" in j:
                    detail = str(j["_raw"])[:80]
            elif txt:
                detail = txt[:80]
            UI.err("CLAIM", f"{name}: HTTP {code} {detail[:60]}")
            low = detail.lower()
            if ("not completed" in low or "watch" in low
                    or "duration" in low or "too short" in low):
                ad["cooldown"] = 45
                return "RETRY"
            if "cooldown" in low or "already" in low:
                ad["cooldown"] = 60
                return "RETRY"
            return "FAIL"

        new_bal = None
        got_reward = reward
        if isinstance(j, dict):
            if "balance" in j:
                new_bal = int(j["balance"])
                got_reward = new_bal - self.balance
                if got_reward < 0: got_reward = reward
            elif j.get("status") == "success":
                new_bal = j.get("balance", self.balance + (reward if isinstance(reward, int) else 0))
                got_reward = j.get("reward", reward)

        if new_bal is not None:
            self.balance = new_bal
            UI.set(balance=self.balance)

        try:
            got_reward_int = int(got_reward)
        except (ValueError, TypeError):
            got_reward_int = 0

        UI.set(
            session_reward=int(UI.state.get("session_reward", 0)) + got_reward_int,
            session_ads=int(UI.state.get("session_ads", 0)) + 1,
            last_reward=f"+{got_reward_int}",
        )
        UI.ok("DONE", f"{name}: +{got_reward_int} coins • bal {self.balance}")
        return got_reward_int

    # ═══════════════════════════════════════════════════════════
    #  INIT HELPERS
    # ═══════════════════════════════════════════════════════════
    def _init_user(self):
        reauth_tries = 0
        while True:
            if UI.state.get("stop_requested"): return False
            try:
                if self.fetch_user():
                    return True
                UI.err("FATAL", "gagal fetch user")
                return False
            except InitDataExpired:
                reauth_tries += 1
                if reauth_tries > MAX_REAUTH:
                    UI.err("FATAL", f"re-auth gagal {MAX_REAUTH}x")
                    return False
                if not self.reauth():
                    return False

    def _init_ads(self):
        while True:
            if UI.state.get("stop_requested"): return False
            try:
                return self.fetch_ads()
            except InitDataExpired:
                if not self.reauth():
                    return False

    # ═══════════════════════════════════════════════════════════
    #  RUN — Start All (exclude aviso unless include_aviso)
    # ═══════════════════════════════════════════════════════════
    def run(self):
        UI.set(state="INIT", session_reward=0, session_ads=0,
               last_reward="-", net_retry=0, reauth_count=0,
               stop_requested=False)
        UI.logs.clear()
        UI.start_panel()

        if not self._init_user():
            UI.stop_panel(); return
        self.start_balance = self.balance

        if not self._init_ads():
            UI.stop_panel(); return

        UI.set(ads_summary=self._ads_summary())

        cycle = 0
        stop_reason = "finished"
        empty_cycles = 0

        while not UI.state.get("stop_requested") and UI.state["running"]:
            cycle += 1
            UI.set(cycle=cycle, state="RUNNING", phase="-")
            UI.info("CYCLE", f"#{cycle}")

            try:
                self.fetch_ads()
                UI.set(ads_summary=self._ads_summary())
            except InitDataExpired:
                UI.warn("CYCLE", "init_data expired mid-run")
                if not self.reauth():
                    stop_reason = "reauth_failed"
                    break
                continue

            now_ts = time.time()
            ready = []
            for a in self.ads:
                aid = a.get("id")
                if aid == "aviso_youtube" and not self.include_aviso:
                    continue
                if a.get("cooldown", 0) > 0:
                    continue
                if a.get("maxViews", 0) and a.get("views", 0) >= a.get("maxViews", 0):
                    continue
                if a.get("isWatching", False):
                    continue
                if aid == "aviso_youtube" and now_ts < self.aviso_cooldown:
                    continue
                ready.append(a)

            def sort_key(a):
                try:
                    return self.AD_ORDER.index(a.get("id", ""))
                except ValueError:
                    return 999
            ready.sort(key=sort_key)

            if not ready:
                has_cd = any(
                    a.get("cooldown", 0) > 0
                    for a in self.ads
                    if (a.get("maxViews", 0) == 0 or a.get("views", 0) < a.get("maxViews", 0))
                    and not (a.get("id") == "aviso_youtube" and not self.include_aviso)
                )
                if has_cd:
                    min_cd = min(
                        (a.get("cooldown", 0) for a in self.ads if a.get("cooldown", 0) > 0),
                        default=60,
                    )
                    wait_s = min(int(min_cd) + 2, 90)
                    UI.warn("IDLE", f"semua cooldown — tunggu {wait_s}s")
                    UI.set(state="WAITING", ads_summary=self._ads_summary())
                    UI.countdown(wait_s, "waiting cooldown")
                    continue
                else:
                    empty_cycles += 1
                    if empty_cycles >= MAX_EMPTY_CYCLES:
                        UI.ok("DONE", "semua iklan habis — stop")
                        UI.set(state="DONE", phase="all done")
                        stop_reason = "all_done"
                        break
                    UI.warn("IDLE", f"kosong {empty_cycles}/{MAX_EMPTY_CYCLES} — 30s")
                    UI.set(state="WAITING")
                    UI.countdown(30, "idle wait")
                    continue

            empty_cycles = 0
            claimed = 0

            for ad in ready:
                if UI.state.get("stop_requested") or not UI.state["running"]:
                    break

                try:
                    result = self.watch_ad(ad)
                except InitDataExpired:
                    UI.warn("WATCH", "init_data expired mid-watch")
                    if not self.reauth():
                        stop_reason = "reauth_failed"
                        break
                    break

                if result == "FAIL":
                    UI.warn("SKIP", f"{ad.get('name', ad.get('id'))} — fail")
                elif result == "RETRY":
                    pass
                else:
                    claimed += 1

                try:
                    self.fetch_ads()
                    UI.set(ads_summary=self._ads_summary())
                except InitDataExpired:
                    UI.warn("REFRESH", "auth expired — re-auth next cycle")
                    break
                except Exception:
                    pass

                pause = random.randint(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                UI.set(state="PAUSE")
                UI.warn("PAUSE", f"{pause}s")
                UI.countdown(pause, "human pause")

            if stop_reason == "reauth_failed":
                break

            if claimed == 0 and not UI.state.get("stop_requested"):
                UI.warn("CYCLE", "gak ada reward — 15s")
                UI.set(state="WAITING")
                UI.countdown(15, "retry cycle")

        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()
        self._summary(stop_reason)

    # ═══════════════════════════════════════════════════════════
    #  RUN — Aviso Only
    # ═══════════════════════════════════════════════════════════
    def run_aviso_only(self):
        self.include_aviso = True
        self.aviso_only = True

        UI.set(state="INIT", session_reward=0, session_ads=0,
               last_reward="-", net_retry=0, reauth_count=0,
               stop_requested=False)
        UI.logs.clear()
        UI.start_panel()

        if not self._init_user():
            UI.stop_panel(); return
        self.start_balance = self.balance

        if not self._init_ads():
            UI.stop_panel(); return
        UI.set(ads_summary=self._ads_summary())

        cycle = 0
        stop_reason = "stopped"

        while not UI.state.get("stop_requested") and UI.state["running"]:
            cycle += 1
            UI.set(cycle=cycle, state="RUNNING", phase="-")
            UI.info("CYCLE", f"aviso #{cycle}")

            try:
                result = self._watch_aviso()
            except InitDataExpired:
                UI.warn("AVISO", "init_data expired")
                if not self.reauth():
                    stop_reason = "reauth_failed"
                    break
                continue
            except Exception as e:
                UI.err("AVISO", f"err: {str(e)[:40]}")
                result = "FAIL"

            try:
                self.fetch_ads()
                UI.set(ads_summary=self._ads_summary())
            except Exception:
                pass

            if UI.state.get("stop_requested") or not UI.state["running"]:
                break

            now_ts = time.time()
            if now_ts < self.aviso_cooldown:
                wait_s = int(self.aviso_cooldown - now_ts) + 2
                UI.set(state="WAITING")
                UI.countdown(wait_s, "aviso cd")
            elif result == "RETRY":
                UI.set(state="WAITING")
                UI.countdown(30, "no task idle")
            else:
                pause = random.randint(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                UI.set(state="PAUSE")
                UI.countdown(pause, "pause")

        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()
        self._summary(stop_reason)

    def _summary(self, stop_reason):
        print()
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c("  ✓ BOT SELESAI", "br_green"))
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c(f"  Reason      : {stop_reason}", "white"))
        print(UI.c(f"  User        : {UI.state['user']}", "white"))
        print(UI.c(f"  Balance     : {self.balance} coins", "br_yellow"))
        print(UI.c(f"  Session     : {UI.state['session_ads']} ads watched", "br_green"))
        print(UI.c(f"  Net retries : {UI.state['net_retry']}", "yellow"))
        print(UI.c(f"  Re-auth     : {UI.state.get('reauth_count', 0)}x", "yellow"))
        print(UI.c("═" * 64, "br_cyan"))
        print()
        print(UI.c("  (enter buat balik ke menu)", "gray"))
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass


# ═══════════════════════════════════════════════════════════════
#  ENTRY
# ═══════════════════════════════════════════════════════════════
def _load_init_data():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        return cfg.get("init_data", "").strip() or None
    except Exception:
        return None


def _run_mode(include_aviso: bool, aviso_only: bool):
    if not os.path.exists(CONFIG_FILE):
        print(UI.c("\n  ⚙ belum ada config — isi initData dulu.\n", "yellow"))
        time.sleep(1)
        config_menu()
        if not os.path.exists(CONFIG_FILE):
            return

    init_data = _load_init_data()
    if not init_data:
        print(UI.c("\n  ✖ init_data kosong.\n", "br_red"))
        time.sleep(1.5)
        return

    try:
        bot = NotBuxBot(init_data, include_aviso=include_aviso, aviso_only=aviso_only)
        if aviso_only:
            bot.run_aviso_only()
        else:
            bot.run()
    except InitDataExpired:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ init_data expired{RESET}\n")
        time.sleep(1.5)
    except Exception as e:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ fatal: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
        time.sleep(2)


def _on_sigint(sig, frame):
    global _IN_MENU
    if _IN_MENU:
        try: UI.stop_panel()
        except Exception: pass
        try:
            sys.stdout.write(f"\n{Fore.YELLOW}  ! exit{RESET}\n\n")
            sys.stdout.flush()
        except Exception: pass
        os._exit(0)
    UI.set(running=False, stop_requested=True)
    try:
        sys.stdout.write(f"\n{Fore.YELLOW}  ! stopping, balik ke menu setelah ini…{RESET}\n")
        sys.stdout.flush()
    except Exception:
        pass


def main():
    signal.signal(signal.SIGINT, _on_sigint)
    while True:
        choice = menu()
        if choice == "0":
            print()
            print(UI.c("  bye bro.\n", "br_cyan"))
            return
        if choice == "1":
            _run_mode(include_aviso=False, aviso_only=False)
        elif choice == "2":
            _run_mode(include_aviso=True, aviso_only=True)
        elif choice == "3":
            config_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try: UI.stop_panel()
        except Exception: pass
        sys.stdout.write(f"\n{Fore.YELLOW}  ! interrupted{RESET}\n\n")
