#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   GRAMAD AUTO WATCH — SOUU ENGINE Edition v1.2               ║
║   HOST : gram.surf                                           ║
║   FEAT : auto watch adsgram / monetag / onclicka / task      ║
║   FEAT : auto claim daily bonus                              ║
║   FEAT : live dashboard + cooldown handler                   ║
║   FEAT : auto-loop sampe limit / habis                       ║
║   NEW  : auto re-auth kalau init_data expired                ║
╚══════════════════════════════════════════════════════════════╝
"""

import requests, json, time, sys, os, random, signal
import urllib.parse, re as _re
from datetime import datetime
from collections import deque
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import init, Fore, Style
init(autoreset=True)

VERSION = "1.2"
HOST = "https://gram.surf"
API = f"{HOST}/ajax.php"
CONFIG_FILE = "config_gramad.json"

BOX_WIDTH = 62
LOG_LINES = 8

TELEGRAM_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
               "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

HTTP_MAX_RETRY = 4
HTTP_BACKOFF_BASE = 3
REQUEST_TIMEOUT = 30

AD_WATCH_MIN = 20
AD_WATCH_MAX = 30
HUMAN_PAUSE_MIN = 2
HUMAN_PAUSE_MAX = 4
DEFAULT_COOLDOWN = 60
MAX_REAUTH = 3

# Prioritas: reward gede dulu
AD_TYPES = ["adsgram_task", "onclicka", "adsgram", "monetag"]

AD_DISPLAY = {
    "adsgram": "Adsgram",
    "monetag": "Monetag",
    "onclicka": "Onclicka",
    "adsgram_task": "Adsgram Task",
}

CLEAR = "\033[2J\033[3J\033[H"


class AuthError(Exception):
    pass


# ═══════════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════════
class UI:
    state = {
        "title": "GRAMAD AUTO WATCH",
        "subtitle": "─────── SOUU ENGINE ───────",
        "running": False,
        "cycle": 0,
        "host": HOST,
        "user": "-",
        "user_id": "-",
        "balance": 0,
        "balance_gram": "0",
        "start_balance": 0,
        "state": "INIT",
        "phase": "-",
        "cooldown": 0,
        "last_reward": "-",
        "session_reward": 0,
        "session_ads": 0,
        "net_retry": 0,
        "ad_summary": [],
        "daily_status": "checking...",
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
    def _strip(s): return _re.sub(r'\033\[[0-9;]*m', '', s)
    @staticmethod
    def vlen(s): return len(UI._strip(s))
    @staticmethod
    def pad(s, w):
        vl = UI.vlen(s)
        return s + (" " * (w - vl)) if vl < w else s
    @staticmethod
    def trunc(s, n):
        if UI.vlen(s) <= n: return s
        out = s
        while UI.vlen(out) > n - 1 and len(out) > 0:
            out = out[:-1]
        return out + "…\033[0m"
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
        buf += UI.row("├─ " + UI.pad("Name", 12) + ": " + UI.trunc(UI.fg(226, str(s["user"])), 29)) + "\n"
        buf += UI.row("├─ " + UI.pad("TG ID", 12) + ": " + UI.trunc(UI.fg(226, str(s["user_id"])), 29)) + "\n"
        buf += UI.row("├─ " + UI.pad("Balance", 12) + ": " + UI.fg(46, f"{int(s['balance']):,} coins")) + "\n"
        buf += UI.row("├─ " + UI.pad("GRAM", 12) + ": " + UI.fg(46, str(s.get("balance_gram", "0")))) + "\n"
        buf += UI.row("└─ " + UI.pad("Started", 12) + ": " + UI.fg(213, str(int(s['start_balance']))) + " coins") + "\n"
        buf += UI.mid() + "\n"

        # ADS
        buf += UI.row(UI.bold("AD NETWORKS")) + "\n"
        ads = s.get("ad_summary", [])
        if not ads:
            buf += UI.row("└─ " + UI.dim("(belum load)")) + "\n"
        else:
            for i, a in enumerate(ads):
                last = (i == len(ads) - 1)
                branch = "└─" if last else "├─"
                name = a["name"][:14]
                count = a["count"]
                mx = a["max"]
                st = a["status"]
                rw = a["reward"]

                if st == "ready":
                    color, tag = 46, "READY"
                elif st == "cooldown":
                    color, tag = 208, f"CD {a.get('cd', 0)}s"
                elif st == "limit":
                    color, tag = 240, "LIMIT"
                elif st == "watching":
                    color, tag = 213, "WATCH"
                elif st == "disabled":
                    color, tag = 196, "OFF"
                elif st == "error":
                    color, tag = 196, "ERR"
                else:
                    color, tag = 226, st.upper()

                line = (branch + " " + UI.pad(name, 14) +
                        " " + UI.fg(226, f"{count}/{mx}") +
                        " " + UI.fg(46, f"+{rw}") +
                        " " + UI.fg(color, tag))
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
            buf += UI.row("├─ " + UI.fg(226, UI.trunc(wname, 42))) + "\n"
            buf += UI.row("├─ [" + UI.fg(46, bar) + "] " + UI.fg(226, f"{int(wpct*100)}%")) + "\n"
        remain = wtotal - int(wpct * wtotal) if wtotal else 0
        buf += UI.row("└─ " + UI.pad("Reward", 9) + ": " + UI.fg(46, str(wrew)) +
                      "  " + UI.pad("Sisa", 5) + ": " + UI.fg(208, f"{remain}s")) + "\n"
        buf += UI.mid() + "\n"

        # DAILY BONUS
        buf += UI.row(UI.bold("DAILY BONUS")) + "\n"
        buf += UI.row("└─ " + UI.fg(213, UI.trunc(str(s.get("daily_status", "-")), 45))) + "\n"
        buf += UI.mid() + "\n"

        # SESSION
        buf += UI.row(UI.bold("SESSION")) + "\n"
        buf += UI.row("├─ " + UI.pad("Cycle", 12) + ": " + UI.fg(226, str(s["cycle"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Ads watched", 12) + ": " + UI.fg(226, str(s["session_ads"]))) + "\n"
        srew = s.get("session_reward", 0)
        buf += UI.row("├─ " + UI.pad("Reward", 12) + ": " + UI.fg(46, f"+{int(srew)} coins")) + "\n"
        buf += UI.row("├─ " + UI.pad("Last", 12) + ": " + UI.fg(226, str(s["last_reward"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Net retry", 12) + ": " + UI.fg(208, str(s.get("net_retry", 0)))) + "\n"
        buf += UI.row("└─ " + UI.pad("Re-auth", 12) + ": " + UI.fg(213, str(s.get("reauth_count", 0)))) + "\n"
        buf += UI.mid() + "\n"

        # STATUS
        phase = str(s["phase"])
        if int(s["cooldown"]) > 0: phase += f" · {int(s['cooldown'])}s"
        state_color = {"RUNNING": 46, "WAITING": 208, "ERROR": 196,
                       "INIT": 240, "DONE": 46, "PAUSE": 213, "RETRY": 208,
                       "WATCHING": 213, "COOLDOWN": 208, "REAUTH": 196}.get(s["state"], 226)
        buf += UI.row(UI.bold("STATUS")) + "\n"
        buf += UI.row("├─ " + UI.pad("State", 12) + ": " + UI.fg(state_color, str(s["state"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Phase", 12) + ": " + UI.trunc(UI.fg(208, phase), 29)) + "\n"
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
               UI.fg(46, "GramAD Edition") + "\n\n"
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
    def set(**kw): UI.state.update(kw)

    @staticmethod
    def start_panel():
        UI.state["running"] = True
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
        print(line(UI.bold(UI.gradient("GRAMAD AUTO WATCH", 51, 213))))
        print(line(UI.dim("─────── SOUU ENGINE ───────")))
        print(UI.fg(51, "╠" + "═" * W_ + "╣"))
        print(line(UI.bold("ABOUT")))
        print(line("├─ " + UI.pad("Host", 11) + ": " + HOST))
        print(line("├─ " + UI.pad("Ads", 11) + f": {len(AD_TYPES)} types"))
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
    print(UI.c("  atau dari DevTools → Network → cari request ke gram.surf,", "gray"))
    print(UI.c("     copy header 'x-tg-auth'", "gray"))
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
class GramAdBot:
    def __init__(self, init_data):
        self.session = make_session()
        self.init_data = init_data
        self.user = {}
        self.user_id = "-"
        self.username = "-"
        self.balance = 0
        self.balance_gram = "0"
        self.start_balance = 0

    # ── HEADERS ──
    def _headers(self):
        return {
            "x-tg-auth": self.init_data,
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
        hints = ['unauthorized', 'invalid init', 'auth error', 'expired']
        if code != 200 and any(h in low for h in hints):
            return True
        return False

    def _ajax(self, action, data=None):
        url = f"{API}?action={action}"
        headers = self._headers()
        body = json.dumps(data) if data is not None else "{}"
        r, err = self._request_with_retry("POST", url, headers, body)
        if r is None:
            UI.err("HTTP", f"{type(err).__name__}: {str(err)[:40]}")
            return None
        if self._is_auth_error(r.status_code, r.text):
            raise AuthError(f"HTTP {r.status_code}")
        try:
            return r.json()
        except Exception:
            return {"success": False, "error": "invalid json", "_raw": r.text[:200]}

    # ── CONFIG ──
    def get_config(self):
        if not os.path.exists(CONFIG_FILE):
            print(CLEAR, end="")
            print(UI.c("\n  ⚙  SETUP — GRAMAD", "br_cyan"))
            print(UI.c("  " + "─" * 50, "br_cyan") + "\n")
            print(UI.c("  Telegram Desktop → DevTools → Network", "white"))
            print(UI.c("  Cari request ke /ajax.php, copy header 'x-tg-auth'", "white"))
            print(UI.c("  (isinya: query_id=...&user=...&auth_date=...&signature=...&hash=...)\n", "br_cyan"))
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
        self.user = {}
        self.balance = 0

        # Simpen ke config
        if save_init_data(new_init):
            UI.ok("AUTH", "init_data baru disimpan")
        else:
            UI.warn("AUTH", "gagal simpen, tetep lanjut pakai yang baru")

        UI.set(reauth_count=int(UI.state.get("reauth_count", 0)) + 1)
        return True

    # ── USER ──
    def fetch_user(self):
        UI.step("USER", "POST init_user")
        res = self._ajax("init_user", {})
        if not res or not res.get("success"):
            UI.err("USER", f"init_user gagal: {str(res)[:60]}")
            return False

        u = res.get("user", {}) or {}
        self.user = u
        self.user_id = u.get("tg_id", "-")
        self.balance = int(u.get("balance", 0))
        self.balance_gram = str(u.get("balance_gram", "0"))

        UI.set(
            user=f"user_{self.user_id}" if self.user_id != "-" else "user",
            user_id=self.user_id,
            balance=self.balance,
            balance_gram=self.balance_gram,
        )
        UI.ok("USER", f"ID {self.user_id} • {self.balance} coins")
        return True

    def sync_balance(self):
        res = self._ajax("ad_manager&mode=balance", {})
        if res and res.get("success"):
            u = res.get("user", {}) or {}
            self.balance = int(u.get("balance", self.balance))
            self.balance_gram = str(u.get("balance_gram", self.balance_gram))
            UI.set(balance=self.balance, balance_gram=self.balance_gram)

    # ── ADS CHECK ──
    def check_ad(self, ad_type):
        return self._ajax("ad_manager&mode=check", {"type": ad_type})

    def refresh_ad_summary(self):
        out = []
        for at in AD_TYPES:
            try:
                res = self.check_ad(at)
            except AuthError:
                raise
            if not res:
                out.append({"id": at, "name": AD_DISPLAY.get(at, at),
                            "count": 0, "max": 0, "reward": 0,
                            "status": "error", "cd": 0})
                continue

            disabled = res.get("disabled", False)
            cnt = int(res.get("current_count", 0))
            mx = int(res.get("max_ads", 0))
            rw = int(res.get("reward", 0))
            cd = int(res.get("seconds_left", 0))
            cooldown_flag = bool(res.get("cooldown", False))

            if disabled:
                st = "disabled"
            elif mx and cnt >= mx:
                st = "limit"
            elif cooldown_flag and cd > 0:
                st = "cooldown"
            else:
                st = "ready"

            out.append({
                "id": at, "name": AD_DISPLAY.get(at, at),
                "count": cnt, "max": mx, "reward": rw,
                "status": st, "cd": cd,
            })
        UI.set(ad_summary=out)
        return out

    def _get_status(self, ad_type):
        res = self.check_ad(ad_type)
        if not res:
            return None
        return {
            "disabled": bool(res.get("disabled", False)),
            "count": int(res.get("current_count", 0)),
            "max": int(res.get("max_ads", 0)),
            "reward": int(res.get("reward", 0)),
            "cd": int(res.get("seconds_left", 0)),
            "cooldown": bool(res.get("cooldown", False)),
            "message": res.get("message", ""),
        }

    # ── WATCH AD ──
    def watch_ad(self, ad_type):
        name = AD_DISPLAY.get(ad_type, ad_type)
        is_task_type = (ad_type == "adsgram_task")

        # 1. Cek status
        st = self._get_status(ad_type)
        if st is None:
            UI.err("CHECK", f"{name}: response null")
            return "FAIL"

        if st["disabled"]:
            UI.warn("SKIP", f"{name}: disabled")
            return "SKIP"

        if st["max"] and st["count"] >= st["max"]:
            UI.warn("SKIP", f"{name}: limit {st['count']}/{st['max']}")
            return "SKIP"

        # 2. Cooldown
        if st["cooldown"] and st["cd"] > 0:
            wait_s = min(int(st["cd"]) + 2, 90)
            UI.warn("CD", f"{name}: tunggu {wait_s}s")
            UI.set(state="COOLDOWN")
            UI.countdown(wait_s, f"cd {name}")
            st = self._get_status(ad_type)
            if st and (st["cooldown"] and st["cd"] > 0):
                return "COOLDOWN"

        reward = st["reward"] if st["reward"] else 0
        token = None

        # 3. Start ad (adsgram_task skip, langsung success)
        if not is_task_type:
            UI.step("START", f"{name} • reward +{reward}")
            res = self._ajax("ad_manager&mode=start_ad", {"type": ad_type})
            if not res or not res.get("success") or not res.get("view_token"):
                msg = res.get("message", "") if res else "no response"
                UI.err("START", f"{name}: {msg[:50]}")
                return "FAIL"
            token = res["view_token"]
        else:
            UI.info("START", f"{name} • reward +{reward} (direct)")

        # 4. Simulasi nonton
        duration = random.randint(AD_WATCH_MIN, AD_WATCH_MAX)
        UI.info("WATCH", f"{name}: {duration}s")
        UI.watch_timer(duration, name, f"+{reward}")

        # 5. Claim
        UI.step("CLAIM", f"mode=success {name}")
        if is_task_type:
            res2 = self._ajax("ad_manager&mode=success", {"type": ad_type})
        else:
            res2 = self._ajax("ad_manager&mode=success", {
                "type": ad_type, "view_token": token,
            })

        # Fallback: kalo adsgram_task direct fail, coba via start_ad
        if is_task_type and res2 and not res2.get("success"):
            UI.warn("CLAIM", f"{name}: direct fail, coba via start_ad")
            res_start = self._ajax("ad_manager&mode=start_ad", {"type": ad_type})
            if res_start and res_start.get("success") and res_start.get("view_token"):
                res2 = self._ajax("ad_manager&mode=success", {
                    "type": ad_type, "view_token": res_start["view_token"],
                })

        if not res2:
            UI.err("CLAIM", f"{name}: no response")
            return "FAIL"

        if not res2.get("success"):
            msg = res2.get("message", "") or res2.get("error", "")
            UI.err("CLAIM", f"{name}: {msg[:50]}")
            return "FAIL"

        got = int(res2.get("new_reward", reward))
        new_count = int(res2.get("current_count", st["count"] + 1))
        new_max = int(res2.get("max_ads", st["max"]))

        try:
            cur = int(UI.state.get("session_reward", 0))
            UI.set(
                session_reward=cur + got,
                session_ads=int(UI.state.get("session_ads", 0)) + 1,
                last_reward=f"+{got}",
            )
        except Exception:
            pass

        self.sync_balance()
        UI.ok("DONE", f"{name}: +{got} • {new_count}/{new_max} • bal {self.balance}")
        return got

    # ── DAILY BONUS ──
    def handle_daily_bonus(self):
        UI.step("DAILY", "check_daily")
        try:
            res = self._ajax("bonus_manager&mode=check_daily", {})
        except AuthError:
            raise

        if not res or not res.get("success"):
            UI.warn("DAILY", "check gagal")
            UI.set(daily_status="error")
            return False

        can_claim = bool(res.get("can_claim", False))
        streak = int(res.get("streak", 0))
        secs = int(res.get("seconds_to_next", 0))

        if can_claim:
            UI.set(daily_status=f"claimable (streak {streak})")
            UI.info("DAILY", f"claimable! streak={streak}")

            try:
                res2 = self._ajax("bonus_manager&mode=claim_daily", {})
            except AuthError:
                raise

            if res2 and res2.get("success"):
                rw = int(res2.get("reward", 0))
                new_streak = int(res2.get("new_streak", streak + 1))
                UI.ok("DAILY", f"+{rw} coins • streak {new_streak}")
                UI.set(daily_status=f"claimed +{rw} (streak {new_streak})")

                try:
                    cur = int(UI.state.get("session_reward", 0))
                    UI.set(session_reward=cur + rw,
                           last_reward=f"+{rw} (daily)")
                except Exception:
                    pass

                self.sync_balance()
                return True
            else:
                msg = (res2 or {}).get("message", "?")
                UI.warn("DAILY", f"claim fail: {msg[:40]}")
                UI.set(daily_status=f"claim fail: {msg[:20]}")
                return False
        else:
            h = secs // 3600
            m = (secs % 3600) // 60
            UI.set(daily_status=f"cooldown {h}h{m}m (streak {streak})")
            UI.info("DAILY", f"cooldown — next in {h}h{m}m")
            return False

    # ── MAIN LOOP ──
    def run(self):
        UI.set(state="INIT", session_reward=0, session_ads=0,
               last_reward="-", net_retry=0, daily_status="checking...",
               reauth_count=0)
        UI.start_panel()

        # ── 1. User dengan re-auth loop ──
        reauth_tries = 0
        while True:
            try:
                if self.fetch_user():
                    break
                UI.err("FATAL", "gagal fetch user — bukan auth error")
                UI.stop_panel(); return
            except AuthError:
                reauth_tries += 1
                if reauth_tries > MAX_REAUTH:
                    UI.err("FATAL", f"re-auth gagal {MAX_REAUTH}x — keluar")
                    UI.stop_panel(); return
                if not self.reauth():
                    UI.err("FATAL", "user gak mau kasih init_data baru")
                    UI.stop_panel(); return

        self.start_balance = self.balance

        # ── 2. Load ad summary ──
        while True:
            try:
                self.refresh_ad_summary()
                break
            except AuthError:
                if not self.reauth():
                    UI.err("FATAL", "reauth gagal di refresh")
                    UI.stop_panel(); return

        # ── 3. Daily bonus ──
        try:
            self.handle_daily_bonus()
        except AuthError:
            if not self.reauth():
                UI.err("FATAL", "reauth gagal di daily bonus")
                UI.stop_panel(); return

        # ── 4. Main loop ──
        cycle = 0
        stop_reason = "finished"
        empty_cycles = 0
        MAX_EMPTY = 3

        while True:
            if not UI.state["running"]:
                stop_reason = "stopped"
                break

            cycle += 1
            UI.set(cycle=cycle, state="RUNNING", phase="-")
            UI.info("CYCLE", f"#{cycle}")

            # Refresh ads
            try:
                ads = self.refresh_ad_summary()
            except AuthError:
                UI.warn("CYCLE", "init_data expired mid-run")
                if not self.reauth():
                    stop_reason = "reauth_failed"
                    break
                continue

            ready = [a for a in ads if a["status"] == "ready"]
            has_cd = any(a["status"] == "cooldown" for a in ads)

            if not ready:
                if has_cd:
                    min_cd = min(
                        (a.get("cd", 0) for a in ads if a["status"] == "cooldown"),
                        default=DEFAULT_COOLDOWN,
                    )
                    wait_s = min(int(min_cd) + 2, 90)
                    UI.warn("IDLE", f"semua cooldown — tunggu {wait_s}s")
                    UI.set(state="WAITING")
                    UI.countdown(wait_s, "waiting cooldown")
                    continue
                else:
                    empty_cycles += 1
                    if empty_cycles >= MAX_EMPTY:
                        UI.ok("DONE", "semua ad habis / limit — bot stop")
                        UI.set(state="DONE", phase="all done")
                        stop_reason = "all_done"
                        break
                    UI.warn("IDLE", f"kosong {empty_cycles}/{MAX_EMPTY} — tunggu 20s")
                    UI.set(state="WAITING")
                    UI.countdown(20, "idle wait")
                    continue

            empty_cycles = 0
            claimed_this_cycle = 0

            for ad in ready:
                if not UI.state["running"]: break
                try:
                    result = self.watch_ad(ad["id"])
                except AuthError:
                    UI.warn("WATCH", "init_data expired mid-watch")
                    if not self.reauth():
                        stop_reason = "reauth_failed"
                        break
                    # break for loop, restart cycle
                    break

                if result == "FAIL":
                    UI.warn("SKIP", f"{ad['name']}: fail, lanjut")
                elif result == "SKIP" or result == "COOLDOWN":
                    pass
                else:
                    claimed_this_cycle += 1

                try:
                    self.refresh_ad_summary()
                except AuthError:
                    UI.warn("REFRESH", "auth expired — bakal re-auth next cycle")
                    break

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

        # SUMMARY
        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()

        print()
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c("  ✓ BOT SELESAI", "br_green"))
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c(f"  Reason      : {stop_reason}", "white"))
        print(UI.c(f"  User ID     : {UI.state['user_id']}", "white"))
        print(UI.c(f"  Balance     : {self.balance} coins ({self.balance_gram} GRAM)", "br_yellow"))
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
            bot_tmp = GramAdBot("")
            bot_tmp.get_config()
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        init_data = cfg.get("init_data", "").strip()
        if not init_data:
            print(UI.c("  ✖ init_data kosong\n", "br_red")); return
        bot = GramAdBot(init_data)
        bot.run()
    except KeyboardInterrupt:
        raise
    except AuthError:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ auth error — init_data expired{RESET}\n")
    except Exception as e:
        UI.stop_panel()
        print(f"\n{Fore.RED}  ✖ fatal: {e}{RESET}\n")
        import traceback
        traceback.print_exc()


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
