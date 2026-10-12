#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   NOTBUX AUTO WATCH — SOUU ENGINE Edition v4.2               ║
║   FIX : banner numpuk (clear scrollback)                     ║
║   FIX : merge ads dari /earn/data + /tasks/available         ║
║   FEAT : live dashboard watch ads                            ║
║   FEAT : auto-loop sampe semua iklan habis                   ║
║   NEW : auto re-auth kalau init_data expired                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests, re, json, time, sys, os, random, signal
from datetime import datetime
from collections import deque
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
init(autoreset=True)

VERSION = "4.2"
HOST = "https://notbux.click"
API = f"{HOST}/api"
CONFIG_FILE = "config_notbux.json"

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

CLEAR = "\033[2J\033[3J\033[H"


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

        # USER
        buf += UI.row(UI.bold("USER")) + "\n"
        buf += UI.row("├─ " + UI.pad("Name", 11) + ": " + UI.trunc(UI.fg(226, str(s["user"])), 30)) + "\n"
        buf += UI.row("├─ " + UI.pad("TG ID", 11) + ": " + UI.trunc(UI.fg(226, str(s["user_id"])), 30)) + "\n"
        bal_str = f"{int(s['balance']):,}"
        buf += UI.row("├─ " + UI.pad("Balance", 11) + ": " + UI.fg(46, f"{bal_str} coins")) + "\n"
        buf += UI.row("└─ " + UI.pad("Started", 11) + ": " + UI.fg(213, str(int(s['start_balance']))) + " coins") + "\n"
        buf += UI.mid() + "\n"

        # ADS
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
                else:
                    color, tag = 226, st.upper()

                line = (branch + " " + UI.pad(name, 15) +
                        " " + UI.fg(226, f"{views}/{mx}") +
                        " " + UI.fg(color, UI.pad(tag, 8)))
                buf += UI.row(line) + "\n"
        buf += UI.mid() + "\n"

        # WATCHING
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

        # SESSION
        buf += UI.row(UI.bold("SESSION")) + "\n"
        buf += UI.row("├─ " + UI.pad("Cycle", 11) + ": " + UI.fg(226, str(s["cycle"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Ads watched", 11) + ": " + UI.fg(226, str(s["session_ads"]))) + "\n"
        srew = s.get("session_reward", 0)
        buf += UI.row("├─ " + UI.pad("Reward", 11) + ": " + UI.fg(46, f"+{int(srew)} coins")) + "\n"
        buf += UI.row("├─ " + UI.pad("Last", 11) + ": " + UI.fg(226, str(s["last_reward"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Net retry", 11) + ": " + UI.fg(208, str(s.get("net_retry", 0)))) + "\n"
        buf += UI.row("└─ " + UI.pad("Re-auth", 11) + ": " + UI.fg(213, str(s.get("reauth_count", 0)))) + "\n"
        buf += UI.mid() + "\n"

        # STATUS
        phase = str(s["phase"])
        if int(s["cooldown"]) > 0: phase += f" · {int(s['cooldown'])}s"
        state_color = {"RUNNING": 46, "WAITING": 208, "ERROR": 196,
                       "INIT": 240, "DONE": 46, "PAUSE": 213, "RETRY": 208,
                       "WATCHING": 213, "COOLDOWN": 208, "REAUTH": 196}.get(s["state"], 226)
        buf += UI.row(UI.bold("STATUS")) + "\n"
        buf += UI.row("├─ " + UI.pad("State", 11) + ": " + UI.fg(state_color, str(s["state"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Phase", 11) + ": " + UI.trunc(UI.fg(208, phase), 30)) + "\n"
        buf += UI.mid() + "\n"

        # LOGS
        logs = list(UI.logs)[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(logs): buf += UI.row(UI.fmt_log(logs[i])) + "\n"
            else: buf += UI.blank() + "\n"

        buf += UI.bot() + "\n"
        buf += "\n   " + UI.bold(UI.fg(46, "BOT RUNNING")) + " " + UI.dim("•") + " " + \
               UI.fg(51, datetime.now().strftime("%H:%M:%S")) + "\n"
        buf += "   " + UI.dim("By Power ") + UI.fg(213, "@SouuXso") + UI.dim(" • ") + \
               UI.fg(46, "NotBux Edition") + "\n\n"
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
            if not UI.state["running"]: break
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

    @staticmethod
    def banner():
        W_ = BOX_WIDTH
        def line(c): return UI.fg(51, "║") + UI.pad(" " + c, W_) + UI.fg(51, "║")
        print(CLEAR, end="")
        print(UI.fg(51, "╔" + "═" * W_ + "╗"))
        print(line(UI.bold(UI.gradient("NOTBUX AUTO WATCH", 51, 213))))
        print(line(UI.dim("─────── SOUU ENGINE ───────")))
        print(UI.fg(51, "╠" + "═" * W_ + "╣"))
        print(line(UI.bold("ABOUT")))
        print(line("├─ " + UI.pad("Host", 11) + ": " + HOST))
        print(line("├─ " + UI.pad("Watch", 11) + f": {AD_WATCH_MIN}-{AD_WATCH_MAX}s"))
        print(line("├─ " + UI.pad("Retry", 11) + f": {HTTP_MAX_RETRY}x backoff"))
        print(line("├─ " + UI.pad("Re-auth", 11) + f": auto up to {MAX_REAUTH}x"))
        print(line("└─ " + UI.pad("Version", 11) + ": v" + VERSION))
        print(UI.fg(51, "╠" + "═" * W_ + "╣"))
        print(line(UI.bold("AUTHOR")))
        print(line("└─ " + UI.pad("By", 11) + ": " + UI.fg(213, "@SouuXso")))
        print(UI.fg(51, "╚" + "═" * W_ + "╝"))
        print()


# ═══════════════════════════════════════════════════════════════
#  RE-AUTH PROMPT
# ═══════════════════════════════════════════════════════════════
def prompt_new_init_data():
    """Prompt user paste init_data baru. Return string atau None kalau kosong/batal."""
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
    print(UI.c("  atau dari DevTools → Network → cari request ke notbux.click,", "gray"))
    print(UI.c("     copy header 'authorization'", "gray"))
    print()
    print(UI.c("  Kosongkan + Enter buat batal & keluar.", "gray"))
    print()
    print(UI.c("  init_data : ", "white"), end="")

    try:
        new_init = input().strip()
    except EOFError:
        new_init = ""

    if not new_init:
        UI.state["running"] = was_running
        return None

    # Validasi minimal
    required = ['query_id', 'user', 'auth_date']
    missing = [k for k in required if f"{k}=" not in new_init]
    if missing:
        print(UI.c(f"\n  ✖ init_data gak lengkap. Missing: {', '.join(missing)}", "br_red"))
        print(UI.c("  Tekan Enter buat tetep lanjut, atau Ctrl+C buat batal...", "gray"), end="")
        try: input()
        except EOFError: pass

    # Cek umur
    try:
        kv = dict(p.split("=", 1) for p in new_init.split("&") if "=" in p)
        ad = int(kv.get("auth_date", "0"))
        age = int(time.time()) - ad
        if age > 300:
            print(UI.c(f"\n  ⚠ init_data udah umur {age//60} menit — mungkin tetep expired.", "yellow"))
            print(UI.c("  Lanjut? (y/N): ", "white"), end="")
            try:
                ans = input().strip().lower()
            except EOFError:
                ans = "n"
            if ans not in ("y", "ya", "yes"):
                UI.state["running"] = was_running
                return None
    except Exception:
        pass

    UI.state["running"] = was_running
    return new_init


def save_init_data(new_init):
    """Update config file dengan init_data baru."""
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

    def __init__(self, init_data):
        self.session = make_session()
        self.init_data = init_data
        self.user = {}
        self.ads = []
        self.user_id = "-"
        self.username = "-"
        self.balance = 0
        self.start_balance = 0

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

    def get_config(self):
        if not os.path.exists(CONFIG_FILE):
            print(CLEAR, end="")
            print(UI.c("\n  ⚙  SETUP — NOTBUX", "br_cyan"))
            print(UI.c("  " + "─" * 50, "br_cyan") + "\n")
            print(UI.c("  Telegram Desktop → Console:", "white"))
            print(UI.c("  copy(Telegram.WebApp.initData)", "br_cyan"))
            print(UI.c("  atau ambil dari DevTools → Network → authorization header\n", "white"))
            print(UI.c("  init_data : ", "white"), end="")
            idata = input().strip()
            if not idata:
                print(UI.c("  ✖ kosong\n", "br_red")); sys.exit(1)
            cfg = {"init_data": idata}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=2)
            print(UI.c(f"\n  ✓ Saved\n", "br_green"))
            time.sleep(1)
            return cfg
        with open(CONFIG_FILE) as f:
            return json.load(f)

    # ── RE-AUTH ──
    def reauth(self):
        """
        Minta init_data baru, update header, reset state. Return True kalau sukses.
        """
        UI.warn("AUTH", "init_data expired — minta paste baru")
        try:
            new_init = prompt_new_init_data()
        except KeyboardInterrupt:
            raise

        if not new_init:
            UI.err("AUTH", "user gak kasih init_data baru — stop")
            return False

        # Update header & session
        self.init_data = new_init
        try: self.session.close()
        except Exception: pass
        self.session = make_session()

        # Reset state
        self.app_key = ""  # kalo ada di script lain
        self.user = {}
        self.ads = []
        self.balance = 0

        # Simpen ke config
        if save_init_data(new_init):
            UI.ok("AUTH", "init_data baru disimpan")
        else:
            UI.warn("AUTH", "gagal simpen, tetep lanjut pakai yang baru")

        # Update counter
        UI.set(reauth_count=int(UI.state.get("reauth_count", 0)) + 1)
        return True

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
        """Gabung dari /earn/data + /tasks/available."""
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
        for a in self.ads:
            mx = a.get("maxViews", 0)
            views = a.get("views", 0)
            cd = a.get("cooldown", 0)
            watching = a.get("isWatching", False)

            if mx and views >= mx:
                st = "limited"
            elif watching:
                st = "watching"
            elif cd > 0:
                st = "cooldown"
            else:
                st = "ready"

            out.append({
                "id": a["id"], "name": a["name"],
                "views": views, "max": mx,
                "cd": cd, "status": st,
                "reward": a.get("reward", 0),
            })
        return out

    def watch_ad(self, ad):
        aid = ad.get("id")
        name = ad.get("name") or aid
        reward = ad.get("reward", 0)

        cd = ad.get("cooldown", 0)
        if cd > 0:
            wait_s = min(int(cd), 60)
            UI.warn("CD", f"{name}: server cd {cd}s")
            UI.set(state="COOLDOWN")
            UI.countdown(wait_s, f"cd {name}")
            return "RETRY"

        duration = random.randint(AD_WATCH_MIN, AD_WATCH_MAX)
        UI.step("WATCH", f"{name} • {duration}s • +{reward} coins")
        UI.watch_timer(duration, name, f"+{reward}")

        UI.step("CLAIM", f"POST /tasks/ads/{aid}/claim")
        code, j, txt = self.api_post(f"/tasks/ads/{aid}/claim", None)

        if code != 200:
            UI.err("CLAIM", f"{name}: HTTP {code}: {txt[:50]}")
            return "FAIL"

        new_bal = None
        got_reward = reward
        if isinstance(j, dict):
            if "balance" in j:
                new_bal = int(j["balance"])
                got_reward = new_bal - self.balance
                if got_reward < 0: got_reward = reward
            elif j.get("status") == "success":
                new_bal = j.get("balance", self.balance + reward)
                got_reward = j.get("reward", reward)

        if new_bal is not None:
            self.balance = new_bal
            UI.set(balance=self.balance)

        UI.set(
            session_reward=int(UI.state.get("session_reward", 0)) + int(got_reward),
            session_ads=int(UI.state.get("session_ads", 0)) + 1,
            last_reward=f"+{int(got_reward)}",
        )
        UI.ok("DONE", f"{name}: +{int(got_reward)} coins • bal {self.balance}")
        return got_reward

    def run(self):
        UI.set(state="INIT", session_reward=0, session_ads=0,
               last_reward="-", net_retry=0, reauth_count=0)
        UI.start_panel()

        # ── 1. Initial fetch user, dengan re-auth loop ──
        reauth_tries = 0
        while True:
            try:
                if self.fetch_user():
                    break
                UI.err("FATAL", "gagal fetch user — bukan auth error")
                UI.stop_panel(); return
            except InitDataExpired:
                reauth_tries += 1
                if reauth_tries > MAX_REAUTH:
                    UI.err("FATAL", f"re-auth gagal {MAX_REAUTH}x — keluar")
                    UI.stop_panel(); return
                if not self.reauth():
                    UI.err("FATAL", "user gak mau kasih init_data baru")
                    UI.stop_panel(); return

        self.start_balance = self.balance

        # ── 2. Initial fetch ads ──
        while True:
            try:
                if self.fetch_ads():
                    break
                UI.warn("ADS", "fetch_ads gagal")
                break
            except InitDataExpired:
                if not self.reauth():
                    UI.err("FATAL", "reauth gagal di fetch_ads")
                    UI.stop_panel(); return

        UI.set(ads_summary=self._ads_summary())

        cycle = 0
        stop_reason = "finished"
        empty_cycles = 0

        while True:
            if not UI.state["running"]:
                stop_reason = "stopped"
                break

            cycle += 1
            UI.set(cycle=cycle, state="RUNNING", phase="-")
            UI.info("CYCLE", f"#{cycle}")

            # ── Refresh ads tiap cycle ──
            try:
                self.fetch_ads()
                UI.set(ads_summary=self._ads_summary())
            except InitDataExpired:
                UI.warn("CYCLE", "init_data expired mid-run")
                if not self.reauth():
                    stop_reason = "reauth_failed"
                    break
                continue

            ready = [a for a in self.ads
                     if a.get("cooldown", 0) == 0
                     and (a.get("maxViews", 0) == 0 or a.get("views", 0) < a.get("maxViews", 0))
                     and not a.get("isWatching", False)]

            def sort_key(a):
                try:
                    return self.AD_ORDER.index(a.get("id", ""))
                except ValueError:
                    return 999
            ready.sort(key=sort_key)

            if not ready:
                has_cd = any(a.get("cooldown", 0) > 0 for a in self.ads
                             if a.get("maxViews", 0) == 0 or a.get("views", 0) < a.get("maxViews", 0))
                if has_cd:
                    min_cd = min(
                        (a.get("cooldown", 0) for a in self.ads if a.get("cooldown", 0) > 0),
                        default=60
                    )
                    wait_s = min(int(min_cd) + 2, 90)
                    UI.warn("IDLE", f"semua cooldown — tunggu {wait_s}s")
                    UI.set(state="WAITING", ads_summary=self._ads_summary())
                    UI.countdown(wait_s, "waiting cooldown")
                    continue
                else:
                    empty_cycles += 1
                    if empty_cycles >= MAX_EMPTY_CYCLES:
                        UI.ok("DONE", "semua iklan habis — bot stop")
                        UI.set(state="DONE", phase="all done")
                        stop_reason = "all_done"
                        break
                    UI.warn("IDLE", f"kosong {empty_cycles}/{MAX_EMPTY_CYCLES} — tunggu 30s")
                    UI.set(state="WAITING")
                    UI.countdown(30, "idle wait")
                    continue

            empty_cycles = 0
            claimed_this_cycle = 0

            for ad in ready:
                if not UI.state["running"]: break

                try:
                    result = self.watch_ad(ad)
                except InitDataExpired:
                    UI.warn("WATCH", "init_data expired mid-watch")
                    if not self.reauth():
                        stop_reason = "reauth_failed"
                        break
                    break  # keluar for loop, cycle bakal restart

                if result == "FAIL":
                    UI.warn("SKIP", f"{ad.get('name', ad.get('id'))} — fail, skip")
                elif result == "RETRY":
                    pass
                else:
                    claimed_this_cycle += 1

                # Refresh ads (ignore auth error di sini biar gak ganggu loop)
                try:
                    self.fetch_ads()
                    UI.set(ads_summary=self._ads_summary())
                except InitDataExpired:
                    UI.warn("REFRESH", "auth expired — bakal re-auth next cycle")
                    break
                except Exception:
                    pass

                pause = random.randint(HUMAN_PAUSE_MIN, HUMAN_PAUSE_MAX)
                UI.set(state="PAUSE")
                UI.warn("PAUSE", f"{pause}s")
                UI.countdown(pause, "human pause")

            if stop_reason == "reauth_failed":
                break

            if claimed_this_cycle == 0:
                UI.warn("CYCLE", "gak ada reward — tunggu 15s")
                UI.set(state="WAITING")
                UI.countdown(15, "retry cycle")

        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()

        print()
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c("  ✓ BOT SELESAI", "br_green"))
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c(f"  Reason      : {stop_reason}", "white"))
        print(UI.c(f"  User        : {UI.state['user']}", "white"))
        print(UI.c(f"  Balance     : {self.balance} coins", "br_yellow"))
        print(UI.c(f"  Session     : +{int(UI.state['session_reward'])} coins ({UI.state['session_ads']} ads)", "br_green"))
        print(UI.c(f"  Net retries : {UI.state['net_retry']}", "yellow"))
        print(UI.c(f"  Re-auth     : {UI.state.get('reauth_count', 0)}x", "yellow"))
        print(UI.c("═" * 64, "br_cyan"))
        print()


# ═══════════════════════════════════════════════════════════════
#  ENTRY
# ═══════════════════════════════════════════════════════════════
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    UI.banner()
    try:
        if not os.path.exists(CONFIG_FILE):
            bot_tmp = NotBuxBot("")
            bot_tmp.get_config()
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        init_data = cfg.get("init_data", "").strip()
        if not init_data:
            print(UI.c("  ✖ init_data kosong\n", "br_red")); return
        bot = NotBuxBot(init_data)
        bot.run()
    except KeyboardInterrupt:
        raise
    except InitDataExpired:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ init_data expired — keluar{RESET}\n")
    except Exception as e:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ fatal: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
    finally:
        pass


def _on_sigint(sig, frame):
    try: signal.signal(signal.SIGINT, signal.SIG_DFL)
    except Exception: pass
    try: UI.stop_panel()
    except Exception: pass
    try:
        sys.stdout.write(f"\n{Fore.YELLOW}  ! CTRL+C — keluar{RESET}\n\n")
        sys.stdout.flush()
    except Exception: pass
    os._exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _on_sigint)
    try:
        main()
    except KeyboardInterrupt:
        _on_sigint(signal.SIGINT, None)
