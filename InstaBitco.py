#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BITCOTASKS FAUCET BOT — SOUU ENGINE v2.4
- FIX: loadAd Monetag (ill3.com) — WAJIB sebelum claim
- Auto loop, IP check, join gate, auto re-auth
"""

import requests, re, json, time, sys, os, random, secrets, uuid, signal
import urllib.parse
from datetime import datetime
from collections import deque

VERSION = "2.4"
BASE_HOST = "instabitcofaucet.bitcotasks.com"
BASE_URL = f"https://{BASE_HOST}"
AD_HOST = "https://ill3.com"
ZONE_ID = 11904492
SW_VERSION = "v1.930.0"

CONFIG_FILE = "config_bitcotasks.json"
JOIN_LINK = "https://t.me/+f3QBLkR5D8k4YzNl"
JOIN_GROUP_NAME = "SOUU ENGINE Community"

TELEGRAM_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
               "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

REQUEST_TIMEOUT = 30
POLL_INTERVAL = 3
AD_POLL_MAX = 40
HUMAN_MIN, HUMAN_MAX = 2, 5
REAUTH_MAX = 3
BOX_WIDTH = 62
LOG_LINES = 8
ANSI_RE = re.compile(r'\033\[[0-9;]*m')


class UI:
    state = {
        "title": "BITCOTASKS FAUCET BOT", "subtitle": "─────── SOUU ENGINE ───────",
        "running": False, "cycle": 0, "host": BASE_HOST, "user": "-",
        "balance": "0.00000000", "total": "0.00000000", "today": "0.00000000",
        "state": "INIT", "phase": "-", "cooldown": 0, "mode": "fixed",
        "streak_day": "-", "streak_claimed": "-", "start_ts": int(time.time()),
        "last_reward": "-", "session_reward": 0.0, "session_claims": 0,
        "ip": "-", "country": "-", "init_age": "-", "wait_sec": 0, "spin": 0,
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
    def trunc_ansi(s, mv):
        if UI.vlen(s) <= mv: return s
        out, visible, i, n = [], 0, 0, len(s)
        target = mv - 1
        while i < n and visible < target:
            if s[i] == '\033':
                j = i + 1
                while j < n and s[j] != 'm': j += 1
                if j < n: out.append(s[i:j + 1]); i = j + 1
                else: i += 1
            else:
                out.append(s[i]); visible += 1; i += 1
        return "".join(out) + "…\033[0m"
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
    def top(): return UI.gradient("╔" + "═" * BOX_WIDTH + "╗", 51, 213)
    @staticmethod
    def mid(): return UI.gradient("╠" + "═" * BOX_WIDTH + "╣", 51, 213)
    @staticmethod
    def bot(): return UI.gradient("╚" + "═" * BOX_WIDTH + "╝", 51, 213)
    @staticmethod
    def row(content):
        return UI.fg(51, "║") + UI.pad(" " + content, BOX_WIDTH) + UI.fg(213, "║")
    @staticmethod
    def blank():
        return UI.fg(51, "║") + (" " * BOX_WIDTH) + UI.fg(213, "║")
    @staticmethod
    def lbl(name, w=12):
        return UI.fg(245, UI.pad(name, w)) + UI.fg(240, "·")

    @staticmethod
    def render():
        if not UI.state["running"]: return
        s = UI.state
        spin_frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spin = spin_frames[s["spin"] % len(spin_frames)]

        buf = "\033[2J\033[H"
        buf += UI.top() + "\n"
        buf += UI.row(UI.bold(UI.gradient(s["title"], 51, 213))) + "\n"
        buf += UI.row(UI.fg(240, s["subtitle"])) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold(UI.fg(226, "▎ SESSION"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Host") + " " +
                      UI.trunc(UI.fg(51, s["host"]), 30)) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Cycle") + " " +
                      UI.fg(220, f"#{s['cycle']}")) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Mode") + " " +
                      UI.fg(213, UI.bold(str(s["mode"]).upper()))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Init") + " " +
                      UI.fg(208, str(s["init_age"]))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("IP") + " " +
                      UI.fg(46, UI.trunc(str(s["ip"]), 22)) + " " +
                      UI.fg(240, f"({s['country']})")) + "\n"
        buf += UI.row(UI.fg(240, "  └─ ") + UI.lbl("Uptime") + " " +
                      UI.fg(51, UI.fmt_uptime(int(time.time()) - s["start_ts"]))) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold(UI.fg(226, "▎ ACCOUNT"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("User") + " " +
                      UI.trunc(UI.fg(220, s["user"]), 30)) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Balance") + " " +
                      UI.bold(UI.fg(46, f"${s['balance']}"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Total") + " " +
                      UI.fg(46, f"${s['total']}")) + "\n"
        buf += UI.row(UI.fg(240, "  └─ ") + UI.lbl("Today") + " " +
                      UI.fg(220, f"${s['today']}")) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold(UI.fg(226, "▎ SESSION STATS"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Reward", 13) + " " +
                      UI.bold(UI.fg(46, f"+${s['session_reward']:.8f}"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Claims", 13) + " " +
                      UI.fg(220, str(s["session_claims"]))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Streak", 13) + " " +
                      UI.fg(213, f"day {s['streak_day']}")) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("Streak st", 13) + " " +
                      UI.fg(46 if s["streak_claimed"] == "✔" else 208, str(s["streak_claimed"]))) + "\n"
        buf += UI.row(UI.fg(240, "  └─ ") + UI.lbl("Last +", 13) + " " +
                      UI.fg(46, str(s["last_reward"]))) + "\n"
        buf += UI.mid() + "\n"

        sc_map = {"RUNNING": 46, "WAITING": 208, "ERROR": 196, "INIT": 240,
                  "DONE": 46, "PAUSE": 213, "RETRY": 208, "COOLDOWN": 208,
                  "STOPPED": 240}
        sc = sc_map.get(s["state"], 226)

        phase = str(s["phase"])
        if int(s.get("wait_sec", 0)) > 0:
            phase += f" · {int(s['wait_sec'])}s"
        phase_show = f"{spin} {phase}" if phase not in ("-", "") else phase

        buf += UI.row(UI.bold(UI.fg(226, "▎ STATUS"))) + "\n"
        buf += UI.row(UI.fg(240, "  ├─ ") + UI.lbl("State") + " " +
                      UI.bold(UI.fg(sc, str(s["state"])))) + "\n"
        buf += UI.row(UI.fg(240, "  └─ ") + UI.lbl("Phase") + " " +
                      UI.trunc(UI.fg(51, phase_show), 30)) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold(UI.fg(226, "▎ LOG"))) + "\n"
        logs = list(UI.logs)[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(logs):
                buf += UI.row(UI.fmt_log(logs[i])) + "\n"
            else:
                buf += UI.blank() + "\n"

        buf += UI.bot() + "\n"
        status_txt = UI.bold(UI.fg(46, f"{spin} RUNNING")) if s["state"] == "RUNNING" \
            else UI.bold(UI.fg(sc, f"● {s['state']}"))
        buf += "\n   " + status_txt + " " + UI.fg(240, "•") + " " + \
               UI.fg(51, datetime.now().strftime("%H:%M:%S")) + "\n"
        buf += "   " + UI.fg(240, "By ") + UI.fg(213, UI.bold("@SouuXso")) + \
               UI.fg(240, " • ") + UI.fg(46, "SOUU ENGINE") + " " + \
               UI.fg(240, "•") + " " + UI.fg(51, f"v{VERSION}") + "\n"
        buf += "   " + UI.fg(240, "Press ") + UI.fg(226, "Ctrl+C") + \
               UI.fg(240, " to stop") + "\n\n"
        sys.stdout.write(buf); sys.stdout.flush()

    @staticmethod
    def fmt_uptime(sec):
        h, r = divmod(int(sec), 3600)
        m, s = divmod(r, 60)
        return f"{h}h{m:02d}m{s:02d}s" if h > 0 else f"{m}m{s:02d}s"

    @staticmethod
    def fmt_log(l):
        cmap = {"info": 51, "ok": 46, "warn": 208, "err": 196, "step": 213, "dbg": 240}
        c = cmap.get(l["kind"], 250)
        ts = UI.fg(240, "[" + l["ts"] + "]")
        icon = UI.fg(c, l["icon"])
        tag = UI.fg(c, UI.bold(UI.pad(l["tag"], 8)))
        avail = BOX_WIDTH - 1 - 10 - 1 - 1 - 1 - 8
        mcol = 250 if l["kind"] != "err" else 196
        maxw = avail if l["kind"] != "err" else avail + 20
        msg = UI.trunc(UI.fg(mcol, l["msg"]), maxw)
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
    def c(text, color):
        cmap = {"reset": 0, "bold": 1, "dim": 2, "red": 196, "green": 46,
                "yellow": 226, "blue": 51, "magenta": 201, "cyan": 51,
                "white": 15, "gray": 240, "orange": 208, "br_red": 196,
                "br_green": 46, "br_yellow": 226, "br_cyan": 51,
                "br_magenta": 213, "br_white": 231, "pink": 213}
        return f"\033[{cmap.get(color, 0)}m{text}\033[0m"

    @staticmethod
    def banner():
        W_ = BOX_WIDTH
        def line(c): return UI.fg(51, "║") + UI.pad(" " + c, W_) + UI.fg(213, "║")
        print()
        print(UI.gradient("╔" + "═" * W_ + "╗", 51, 213))
        print(line(UI.bold(UI.gradient("BITCOTASKS FAUCET BOT", 51, 213))))
        print(line(UI.fg(240, "─────── SOUU ENGINE ───────")))
        print(UI.gradient("╠" + "═" * W_ + "╣", 51, 213))
        print(line(UI.bold(UI.fg(226, "ABOUT"))))
        print(line("├─ " + UI.fg(245, UI.pad("Host", 11)) + "· " + UI.fg(51, BASE_HOST)))
        print(line("├─ " + UI.fg(245, UI.pad("AdHost", 11)) + "· " + UI.fg(213, AD_HOST)))
        print(line("├─ " + UI.fg(245, UI.pad("Version", 11)) + "· " + UI.fg(213, "v" + VERSION)))
        print(line("└─ " + UI.fg(245, UI.pad("By", 11)) + "· " + UI.bold(UI.fg(213, "@SouuXso"))))
        print(UI.gradient("╚" + "═" * W_ + "╝", 51, 213))
        print()


class IPCheck:
    SERVICES = ["https://api.ipify.org?format=json",
                "https://ipinfo.io/json",
                "https://api64.ipify.org?format=json"]

    @staticmethod
    def fetch():
        result = {"ip": "-", "country": "-", "city": "-", "isp": "-", "org": "-"}
        for url in IPCheck.SERVICES:
            try:
                r = requests.get(url, timeout=8, headers={"User-Agent": TELEGRAM_UA})
                if r.status_code != 200: continue
                data = r.json() if r.text.strip().startswith("{") else {"ip": r.text.strip()}
                result["ip"] = data.get("ip") or data.get("query") or result["ip"]
                result["country"] = data.get("country") or data.get("countryCode") or "-"
                result["city"] = data.get("city") or "-"
                result["isp"] = data.get("isp") or "-"
                result["org"] = data.get("org") or data.get("as") or "-"
                if result["ip"] != "-": return result
            except Exception:
                continue
        return result

    @staticmethod
    def show(info):
        print()
        print(UI.c("  ┌─ NETWORK / IP CHECK " + "─" * 40, "br_cyan"))
        print(UI.c("  │ IP       : ", "white") + UI.c(info["ip"], "br_green"))
        print(UI.c("  │ Country  : ", "white") + UI.c(info["country"], "br_yellow"))
        print(UI.c("  │ City     : ", "white") + UI.c(info["city"], "white"))
        print(UI.c("  │ ISP      : ", "white") + UI.c(info["isp"][:40], "white"))
        print(UI.c("  └" + "─" * 57, "br_cyan"))
        print()


class JoinGate:
    @staticmethod
    def check(cfg):
        if cfg.get("joined_group"): return True
        while True:
            print()
            print(UI.c("╔" + "═" * 62 + "╗", "br_yellow"))
            print(UI.c("║", "br_yellow") +
                  UI.pad(UI.c("  ⚠  WAJIB JOIN GRUP DULU SEBELUM PAKE BOT", "br_yellow"), 62) +
                  UI.c("║", "br_yellow"))
            print(UI.c("╚" + "═" * 62 + "╝", "br_yellow"))
            print()
            print(UI.c("  Grup   : ", "white") + UI.c(JOIN_GROUP_NAME, "br_cyan"))
            print(UI.c("  Link   : ", "white") + UI.c(JOIN_LINK, "br_green"))
            print()
            try:
                ans = input(UI.c("  ▶ Udah join? [Enter=ya / n=keluar]: ", "br_yellow")).strip().lower()
            except EOFError:
                ans = "n"
            if ans == "n":
                print(UI.c("  ✖ Gak join = gak lanjut. Bye.", "br_red"))
                sys.exit(0)
            cfg["joined_group"] = True
            cfg["joined_at"] = datetime.now().isoformat()
            save_config(cfg)
            print(UI.c("  ✔ Makasih, lanjut...", "br_green"))
            time.sleep(1)
            return True


def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE) as f: return json.load(f)
    except Exception: return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)
    except Exception as e:
        UI.err("CFG", f"save fail: {e}")


def prompt_init_data():
    print()
    print(UI.c("  ⚠ Ambil init_data dari Telegram Desktop:", "br_yellow"))
    print(UI.c("    Ctrl+Shift+I → Console → copy(Telegram.WebApp.initData)", "gray"))
    print()
    while True:
        try:
            init_data = input(UI.c("  init_data : ", "white")).strip()
        except EOFError:
            init_data = ""
        if not init_data:
            print(UI.c("  ✖ kosong, coba lagi", "br_red")); continue
        missing = [k for k in ('query_id', 'user', 'auth_date', 'hash') if f"{k}=" not in init_data]
        if missing:
            print(UI.c(f"  ✖ kurang field: {', '.join(missing)}", "br_red")); continue
        return init_data


def prompt_email(default=""):
    if default:
        try:
            print(UI.c(f"  Email [{default}]: ", "white"), end="")
            v = input().strip()
            return v or default
        except EOFError:
            return default
    while True:
        try:
            v = input(UI.c("  FaucetPay email : ", "white")).strip()
        except EOFError:
            v = ""
        if "@" in v: return v
        print(UI.c("  ✖ email gak valid", "br_red"))


class InitDataExpired(Exception):
    pass


class BitcoFaucetBot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.host = cfg.get("host", BASE_HOST)
        self.base_url = f"https://{self.host}"
        self.device_id = cfg.get("device_id") or str(uuid.uuid4())
        self.init_data = cfg.get("init_data", "")
        self.email = cfg.get("email", "")
        self.token = None
        self.user = {}
        self.session = self._make_session()

    def _make_session(self):
        s = requests.Session()
        s.headers.update({
            "User-Agent": TELEGRAM_UA, "Accept": "*/*",
            "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-requested-with": "org.telegram.messenger.web",
        })
        return s

    def _headers(self, with_token=True, json_body=True):
        h = {"Origin": self.base_url, "Referer": f"{self.base_url}/miniapp",
             "x-mini-device": self.device_id}
        if json_body: h["Content-Type"] = "application/json"
        if with_token and self.token: h["x-mini-token"] = self.token
        return h

    def get(self, path, with_token=True, params=None, headers=None, timeout=None):
        try:
            r = self.session.get(f"{self.base_url}{path}",
                                 headers=headers or self._headers(with_token, json_body=False),
                                 params=params, timeout=timeout or REQUEST_TIMEOUT)
            return r.status_code, self._safe_json(r), r.text
        except Exception as e:
            return 0, None, f"{type(e).__name__}: {e}"

    def post(self, path, body=None, with_token=True):
        try:
            data = json.dumps(body) if body is not None else ""
            r = self.session.post(f"{self.base_url}{path}",
                                  headers=self._headers(with_token),
                                  data=data, timeout=REQUEST_TIMEOUT)
            return r.status_code, self._safe_json(r), r.text
        except Exception as e:
            return 0, None, f"{type(e).__name__}: {e}"

    def _safe_json(self, r):
        try: return r.json()
        except Exception: return {"_raw": r.text[:300]}

    def _is_auth_error(self, code, body_text):
        if code in (401, 403): return True
        if not body_text: return False
        low = body_text.lower()
        return code != 200 and any(h in low for h in
                                   ("unauthorized", "expired", "invalid init",
                                    "init_data", "auth_date"))

    def warmup(self):
        UI.step("WARM", "GET /miniapp (cookies)")
        try:
            self.session.get(f"{self.base_url}/miniapp",
                             headers={"User-Agent": TELEGRAM_UA,
                                      "x-requested-with": "org.telegram.messenger.web"},
                             timeout=REQUEST_TIMEOUT)
            return True
        except Exception as e:
            UI.err("WARM", f"fail: {e}"); return False

    def auth(self):
        UI.step("AUTH", "POST /mini/auth")
        body = {"init_data": self.init_data, "ref": "", "email": self.email}
        code, j, txt = self.post("/mini/auth", body, with_token=False)
        if code != 200:
            UI.err("AUTH", f"HTTP {code}: {txt[:60]}")
            if self._is_auth_error(code, txt): raise InitDataExpired(f"HTTP {code}")
            return False
        if not isinstance(j, dict): return False
        status = j.get("status")
        if status == "need_email":
            body["email"] = self.email
            code, j, txt = self.post("/mini/auth", body, with_token=False)
            status = j.get("status") if isinstance(j, dict) else None
        if status != "ok":
            UI.err("AUTH", f"gagal: {str(j)[:80]}")
            if self._is_auth_error(200, json.dumps(j)): raise InitDataExpired("status != ok")
            return False
        self.token = j.get("token")
        if not self.token:
            UI.err("AUTH", "token kosong"); return False
        UI.ok("AUTH", f"token={self.token[:20]}…")
        return True

    def ensure_login(self):
        self.warmup()
        return self.auth()

    def reauth(self):
        UI.warn("AUTH", "init_data expired — prompt input baru")
        UI.stop_panel()
        sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
        new_init = prompt_init_data()
        new_email = prompt_email(self.email)
        self.init_data = new_init
        self.email = new_email
        self.token = None
        self.user = {}
        self.cfg["init_data"] = new_init
        self.cfg["email"] = new_email
        self.cfg["device_id"] = self.device_id
        save_config(self.cfg)
        UI.ok("AUTH", "config baru disimpan")
        UI.start_panel()
        if not self.ensure_login():
            UI.err("AUTH", "re-auth gagal"); return False
        UI.ok("AUTH", "re-auth sukses, lanjut loop")
        return True

    def me(self):
        code, j, txt = self.get("/mini/me")
        if self._is_auth_error(code, txt): raise InitDataExpired(f"me HTTP {code}")
        if code != 200 or not isinstance(j, dict) or j.get("status") != "ok":
            return False
        self.user = j.get("user", {})
        return True

    def sync_ui_user(self):
        u = self.user or {}
        UI.set(user=u.get("username", "?"),
               balance=f"{u.get('balance_usd', 0):.8f}",
               total=f"{u.get('total_earn', 0):.8f}",
               today=f"{u.get('today_earn', 0):.8f}")

    def faucet_status(self):
        code, j, txt = self.get("/mini/faucet/status")
        if self._is_auth_error(code, txt): raise InitDataExpired(f"status HTTP {code}")
        if code != 200 or not isinstance(j, dict): return None
        return j

    def build_ymid(self, prefix="fct"):
        return f"{prefix}-{self.user.get('id', 0)}-{int(time.time() * 1000)}"

    # ─── AD LOAD (WAJIB) ───────────────────────────────────
    def _ad_url(self, ymid):
        oaid = self.cfg.get("oaid", "")
        if not oaid:
            oaid = secrets.token_hex(16)
            self.cfg["oaid"] = oaid
            save_config(self.cfg)

        params = {
            "excludes": "", "oaid": oaid, "ymid": ymid,
            "tgp": "tdesktop", "tglc": "en", "sdkp": "1",
            "var_3": str(self.user.get("id", 0)),
            "of": "true", "os": "windows", "os_version": "10.0.0",
            "is_mobile": "false", "browser_version": "153.0.4234.48",
            "sw_version": SW_VERSION, "dmn": "libtl.com",
            "fs": "0", "cf": "0", "sw": "1280", "sh": "800", "sah": "760",
            "wx": "448", "wy": "110", "ww": "384", "wh": "590",
            "cw": "374", "wiw": "384", "wih": "590", "wfc": "0",
            "pl": f"{BASE_URL}/miniapp", "drf": "",
            "np": "1", "pt": "0", "nb": "1", "ng": "1", "ix": "0",
            "nw": "1", "tb": "false", "vsbl": "true",
            "navlng": "en-US", "bto": "-420", "btz": "Asia/Saigon",
            "jsp": "1",
        }
        return f"{AD_HOST}/500/{ZONE_ID}?" + urllib.parse.urlencode(params)

    def _ad_headers(self):
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Storage-Access": "active",
        }

    def loadAd(self, ymid):
        url = self._ad_url(ymid)
        UI.step("ADLOAD", f"GET {AD_HOST}/500/...")

        try:
            r = self.session.get(url, headers=self._ad_headers(),
                                 timeout=REQUEST_TIMEOUT)
        except Exception as e:
            UI.err("ADLOAD", f"{type(e).__name__}: {e}")
            return False

        if r.status_code != 200:
            UI.err("ADLOAD", f"HTTP {r.status_code}: {r.text[:60]}")
            return False

        try:
            j = r.json()
        except Exception:
            UI.err("ADLOAD", "response bukan JSON")
            return False

        ads = j.get("ads", [])
        ruid = j.get("ruid", "")
        if not ads or not ruid:
            UI.err("ADLOAD", f"no ads/ruid: {str(j)[:80]}")
            return False

        ad = ads[0]
        UI.ok("ADLOAD", f"ruid={ruid[:16]}…")

        # fire impression
        imp = ad.get("impression_url", "")
        if imp:
            try:
                self.session.get(imp, headers={
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Origin": self.base_url,
                    "Referer": f"{self.base_url}/",
                    "Sec-Fetch-Site": "cross-site",
                    "Sec-Fetch-Mode": "no-cors",
                    "Sec-Fetch-Dest": "image",
                }, timeout=15)
                UI.dbg("ADLOAD", "impression fired")
            except Exception as e:
                UI.dbg("ADLOAD", f"imp fail: {e}")

        # resolve
        try:
            resolve_url = f"{AD_HOST}/resolve?ruid={urllib.parse.quote(ruid)}"
            self.session.get(resolve_url, headers=self._ad_headers(), timeout=15)
            UI.dbg("ADLOAD", "resolve fired")
        except Exception as e:
            UI.dbg("ADLOAD", f"resolve fail: {e}")

        return True

    def _poll_ad_status(self, ymid, max_polls=40, accept_rewarded=True):
        UI.info("AD", "polling ad-status…")
        for i in range(max_polls):
            time.sleep(POLL_INTERVAL)
            code, j, _ = self.get("/mini/ad-status", params={"ymid": ymid})
            if code != 200 or not isinstance(j, dict):
                continue
            state = j.get("state", "")
            valued = j.get("valued", False)
            rewarded = j.get("rewarded", False)
            UI.dbg("AD", f"poll {i+1} state={state} valued={valued} rewarded={rewarded}")
            if accept_rewarded:
                if state in ("confirmed", "rewarded") or valued or rewarded:
                    return True, j
            else:
                if state == "rewarded" or rewarded:
                    return True, j
        return False, None

    def claim_faucet_fixed(self):
        st = self.faucet_status()
        if not st: return {"err": "status fail"}
        if st.get("limit_reached"): return {"limited": True}
        if not st.get("can_claim"):
            return {"wait": int(st.get("wait_sec", 0))}

        ymid = self.build_ymid("fct")

        # STEP 1: load ad Monetag
        if not self.loadAd(ymid):
            return {"err": "loadAd gagal"}

        # STEP 2: poll sampe verified
        ok_, _ = self._poll_ad_status(ymid, max_polls=AD_POLL_MAX, accept_rewarded=True)
        if not ok_:
            return {"err": "ad gak keverifikasi (timeout)"}

        # STEP 3: claim
        time.sleep(random.uniform(HUMAN_MIN, HUMAN_MAX))
        UI.step("CLAIM", f"fixed ymid={ymid}")
        code, j, txt = self.post("/mini/faucet/claim",
                                 {"ymid": ymid, "chosen_mode": "fixed"})
        if self._is_auth_error(code, txt): raise InitDataExpired(f"claim HTTP {code}")
        if code != 200: return {"err": f"HTTP {code}: {txt[:100]}"}
        if j.get("status") == "ok":
            return {"reward": j.get("reward", 0)}
        msg = j.get("message") if isinstance(j, dict) else str(j)
        return {"err": str(msg) if msg else str(j)[:100]}

    def claim_faucet_ad(self):
        st = self.faucet_status()
        if not st: return {"err": "status fail"}
        if st.get("limit_reached"): return {"limited": True}
        if not st.get("can_claim"):
            return {"wait": int(st.get("wait_sec", 0))}

        ymid = self.build_ymid("watch")

        # STEP 1: ad-start register watch session
        UI.step("ADSTART", f"ymid={ymid}")
        code, j, txt = self.post("/mini/ad-start", {"ymid": ymid})
        if code != 200:
            UI.warn("ADSTART", f"HTTP {code}: {txt[:60]}")

        # STEP 2: load ad
        if not self.loadAd(ymid):
            return {"err": "loadAd gagal"}

        # STEP 3: poll reward
        ok_, _ = self._poll_ad_status(ymid, max_polls=60, accept_rewarded=False)
        if not ok_:
            return {"err": "ad gak keverifikasi (timeout)"}

        # STEP 4: claim
        time.sleep(random.uniform(HUMAN_MIN, HUMAN_MAX))
        UI.step("CLAIM", f"revenue_share ymid={ymid}")
        code, j, txt = self.post("/mini/faucet/claim",
                                 {"ymid": ymid, "chosen_mode": "revenue_share"})
        if self._is_auth_error(code, txt): raise InitDataExpired(f"claim HTTP {code}")
        if code != 200: return {"err": f"HTTP {code}: {txt[:100]}"}
        if j.get("status") == "ok":
            return {"reward": j.get("reward", 0)}
        msg = j.get("message") if isinstance(j, dict) else str(j)
        return {"err": str(msg) if msg else str(j)[:100]}

    def streak_status(self):
        code, j, txt = self.get("/mini/streak")
        if self._is_auth_error(code, txt): raise InitDataExpired(f"streak HTTP {code}")
        if code != 200 or not isinstance(j, dict): return None
        return j

    def claim_streak(self):
        st = self.streak_status()
        if not st: return {"err": "streak status fail"}
        if not st.get("enabled"): return {"disabled": True}
        if st.get("claimed_today"): return {"already": True, "day": st.get("streak_day")}
        UI.step("STREAK", "POST /mini/streak/claim")
        time.sleep(random.uniform(HUMAN_MIN, HUMAN_MAX))
        code, j, txt = self.post("/mini/streak/claim", None)
        if self._is_auth_error(code, txt): raise InitDataExpired(f"streak HTTP {code}")
        if code != 200: return {"err": f"HTTP {code}"}
        if j.get("status") == "ok":
            return {"reward": j.get("coins", 0), "day": j.get("streak_day", 0)}
        return {"err": str(j)[:60]}


def run_loop(bot, mode="fixed"):
    UI.set(mode=mode, state="RUNNING", phase="-")
    UI.start_panel()
    cycle = 0
    reauth_attempts = 0
    streak_checked_today = False

    while UI.state["running"]:
        cycle += 1
        UI.set(cycle=cycle, state="RUNNING", phase="-",
               spin=UI.state.get("spin", 0) + 1)
        UI.info("CYCLE", f"#{cycle} mode={mode}")

        try:
            if not bot.me():
                UI.warn("ME", "gagal refresh, retry 30s")
                UI.set(state="RETRY"); time.sleep(30); continue
            bot.sync_ui_user()
        except InitDataExpired:
            reauth_attempts += 1
            if reauth_attempts > REAUTH_MAX:
                UI.err("STOP", f"re-auth {REAUTH_MAX}x gagal"); break
            if not bot.reauth(): break
            continue

        ip_info = IPCheck.fetch()
        UI.set(ip=ip_info["ip"], country=ip_info["country"])

        if not streak_checked_today:
            try:
                res = bot.claim_streak()
                if res.get("reward"):
                    UI.ok("STREAK", f"day {res['day']} +{res['reward']:.6f}")
                    UI.set(streak_claimed="✔", streak_day=res["day"])
                    cur = float(UI.state["session_reward"])
                    UI.set(session_reward=cur + float(res["reward"]))
                elif res.get("already"):
                    UI.info("STREAK", f"udah claimed (day {res.get('day')})")
                    UI.set(streak_claimed="✔", streak_day=res.get("day", "-"))
                elif res.get("disabled"):
                    UI.warn("STREAK", "gak aktif"); UI.set(streak_claimed="off")
                else:
                    UI.warn("STREAK", f"gagal: {res.get('err','?')}")
                streak_checked_today = True
            except InitDataExpired:
                reauth_attempts += 1
                if reauth_attempts > REAUTH_MAX: break
                if not bot.reauth(): break
                continue

        try:
            if mode == "watch_ad":
                res = bot.claim_faucet_ad()
            else:
                res = bot.claim_faucet_fixed()
        except InitDataExpired:
            reauth_attempts += 1
            if reauth_attempts > REAUTH_MAX: break
            if not bot.reauth(): break
            continue

        if res.get("reward") is not None:
            rew = float(res["reward"])
            UI.ok("FAUCET", f"+{rew:.8f}")
            UI.set(last_reward=f"+{rew:.8f}", wait_sec=0)
            cur = float(UI.state["session_reward"])
            UI.set(session_reward=cur + rew,
                   session_claims=int(UI.state["session_claims"]) + 1,
                   state="RUNNING", phase="-")
            time.sleep(random.uniform(3, 6)); continue

        if res.get("limited"):
            UI.ok("DONE", "daily limit reached — stop")
            UI.set(state="DONE", phase="daily limit"); break

        if res.get("wait"):
            wait = int(res["wait"])
            UI.warn("COOLDOWN", f"tunggu {wait}s")
            UI.set(state="COOLDOWN")
            for i in range(wait, 0, -1):
                if not UI.state["running"]: break
                UI.set(wait_sec=i, phase=f"cooldown {i}s",
                       spin=UI.state.get("spin", 0) + 1)
                UI.render(); time.sleep(1)
            UI.set(wait_sec=0); continue

        errmsg = str(res.get("err", "?"))
        UI.warn("FAUCET", f"error: {errmsg}")
        print(UI.c(f"  ⚠ full error: {errmsg}", "br_red"))
        UI.set(state="RETRY"); time.sleep(20)

    UI.set(state="DONE", phase="stopped")
    UI.stop_panel()

    print()
    print(UI.c("═" * 64, "br_cyan"))
    print(UI.c("  ✓ BOT SELESAI", "br_green"))
    print(UI.c("═" * 64, "br_cyan"))
    print(UI.c(f"  Cycles     : {UI.state['cycle']}", "white"))
    print(UI.c(f"  User       : {UI.state['user']}", "white"))
    print(UI.c(f"  Balance    : ${UI.state['balance']}", "br_yellow"))
    print(UI.c(f"  Session    : +${UI.state['session_reward']:.8f} "
               f"({UI.state['session_claims']} claims)", "br_green"))
    print(UI.c(f"  IP         : {UI.state['ip']} ({UI.state['country']})", "white"))
    print(UI.c("═" * 64, "br_cyan"))
    print()


def setup_config():
    cfg = load_config()
    if not cfg.get("init_data") or not cfg.get("email"):
        print()
        print(UI.c("  ⚙ SETUP WIZARD", "br_cyan"))
        cfg["init_data"] = prompt_init_data()
        cfg["email"] = prompt_email(cfg.get("email", ""))
        cfg.setdefault("device_id", str(uuid.uuid4()))
        cfg.setdefault("host", BASE_HOST)
        save_config(cfg)
        print(UI.c("  ✔ config disimpan", "br_green"))
    if "oaid" not in cfg or not cfg["oaid"]:
        cfg["oaid"] = secrets.token_hex(16)
    JoinGate.check(cfg)
    cfg.setdefault("device_id", str(uuid.uuid4()))
    cfg.setdefault("host", BASE_HOST)
    save_config(cfg)
    return cfg


def pick_mode():
    print()
    print(UI.c("  ┌─ MODE FAUCET " + "─" * 46, "br_cyan"))
    print(UI.c("  │ [1] Fixed  (faucet claim only)", "white"))
    print(UI.c("  │ [2] Watch Ad (revenue share)", "white"))
    print(UI.c("  └" + "─" * 57, "br_cyan"))
    try:
        ans = input(UI.c("  ▶ Pilih [default=1]: ", "br_yellow")).strip()
    except EOFError:
        ans = ""
    return "watch_ad" if ans == "2" else "fixed"


def _sigint_handler(sig, frame):
    UI.stop_panel()
    print()
    print(UI.c("  ! Ctrl+C — stop", "br_yellow"))
    sys.exit(0)


def main():
    UI.banner()
    print(UI.c("  ⬢ Cek IP publik...", "br_cyan"))
    ip_info = IPCheck.fetch()
    IPCheck.show(ip_info)

    cfg = setup_config()
    UI.set(ip=ip_info["ip"], country=ip_info["country"])
    bot = BitcoFaucetBot(cfg)
    print(UI.c(f"  ◈ host   : {bot.host}", "white"))
    print(UI.c(f"  ◈ device : {bot.device_id[:24]}…", "white"))
    print(UI.c(f"  ◈ oaid   : {cfg.get('oaid','-')[:20]}…", "white"))

    mode = pick_mode()

    try:
        if not bot.ensure_login():
            UI.err("FATAL", "login gagal"); return
    except InitDataExpired:
        UI.err("FATAL", "init_data expired pas login"); return

    signal.signal(signal.SIGINT, _sigint_handler)
    try:
        run_loop(bot, mode=mode)
    except KeyboardInterrupt:
        _sigint_handler(None, None)


if __name__ == "__main__":
    main()
