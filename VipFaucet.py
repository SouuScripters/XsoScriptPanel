#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  VIPCOIN FAUCET AUTO CLAIM — SOUU ENGINE Edition v1.5        ║
║  HOST : vipcoinfaucet.com (@VipcoinFaucet_bot)               ║
║  FEAT : Faucet + Watch Ads (Auto Loop)                       ║
║  FEAT : Auto Sleep 5m tiap 15 claim + Auto Stop 2x Fail      ║
║  FEAT : Live Dashboard Neon UI                               ║
║  FEAT : AUTO INIT-DATA via Telethon (StringSession, no lock) ║
║  FEAT : SOUU ENGINE Main Menu (Neon ASCII)                   ║
╚══════════════════════════════════════════════════════════════╝
"""

from curl_cffi import requests
import json
import re
import sys
import os
import time
import random
import asyncio
from datetime import datetime
from collections import deque
from urllib.parse import urlparse, parse_qs, unquote

# ═══════════════════ TELETHON IMPORTS ═══════════════════
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.tl.types import InputUser

# ═══════════════════ CONFIGURATION ═══════════════════
HOST = "https://vipcoinfaucet.com"
BOT_NAME = "@VipcoinFaucet_bot"
BOT_USERNAME = "VipcoinFaucet_bot"
BOX_WIDTH = 62
LOG_LINES = 8
CLEAR = "\033[2J\033[3J\033[H"

# ── Telethon Credentials ──
API_ID = 21578873
API_HASH = "b7562db4c393baff2f415d14a14d1f76"
SESSION_FILE = "vipcoin_telethon.session"

COINS = {
    "1": "ltc",   "2": "doge",  "3": "eth",   "4": "ton",
    "5": "zec",   "6": "trump", "7": "trx",   "8": "usdt",
    "9": "fey",   "10": "bnb",  "11": "sol",  "12": "dgb",
    "13": "pepe", "14": "dash", "15": "bch",
}

COOLDOWN_MARGIN = 5
MAX_FAIL_STREAK = 2
WATCH_DURATION = 30
WATCH_COOLDOWN = 12
SLEEP_AFTER_CLAIMS = 15
SLEEP_DURATION_SEC = 5 * 60
REDIRECT_DELAY = 3   # detik nunggu sebelum fetch URL redirect

# ═══════════════════ GLOBAL DEFAULTS ═══════════════════
COIN = "ltc"
MODE = "3"
INIT_DATA = ""

MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
    "Telegram-Android/12.10.6"
)

# ═══════════════════ NEON COLORS ═══════════════════
def _c(n): return f"\033[38;5;{n}m"
RED, GREEN, YELLOW, CYAN, MAGENTA, WHITE, GRAY, AQUA = _c(196), _c(118), _c(226), _c(51), _c(201), _c(231), _c(245), _c(87)
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"

# ═══════════════════ SOUU ENGINE MENU ═══════════════════
SEP = "=" * 60
DEV_TAG = "MoneyMaker_w"

def mode_name_of(m):
    return {"1": "Watch Ads Only", "2": "Faucet Only", "3": "Both (Ads + Faucet)"}.get(m, "?")

def _sep_line():
    return f"{CYAN}{SEP}{RESET}"

def print_menu_banner():
    print(_sep_line())
    print(f"{BOLD}{MAGENTA}{'MAIN MENU':^60}{RESET}")
    print(_sep_line())

def main_menu():
    global COIN, MODE
    while True:
        clear()
        print_menu_banner()
        print(f" {WHITE}Bot{RESET}   : {YELLOW}{BOT_NAME}{RESET}")
        print(f" {WHITE}Coin{RESET}  : {MAGENTA}{COIN.upper()}{RESET}")
        print(f" {WHITE}Mode{RESET}  : {GREEN}{mode_name_of(MODE)}{RESET}")
        print(f" {WHITE}Dev{RESET}   : {AQUA}{DEV_TAG}{RESET}")
        print(_sep_line())
        print()
        print(f" {GREEN}[1]{RESET} Watch Ads Only")
        print(f" {GREEN}[2]{RESET} Faucet Only")
        print(f" {GREEN}[3]{RESET} Both (Ads + Faucet)")
        print(f" {YELLOW}[4]{RESET} Select Coin")
        print(f" {RED}[0]{RESET} Exit")
        print()
        print(_sep_line())

        try:
            choice = input(f" {CYAN}❯ Pilih [0-4]: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Bye bro.{RESET}")
            sys.exit(0)

        if choice == "0":
            print(f"\n{GREEN}✓ Exit. Sampai jumpa, bro.{RESET}")
            sys.exit(0)
        elif choice == "4":
            select_coin_menu()
            continue
        elif choice in ("1", "2", "3"):
            MODE = choice
            return
        else:
            print(f"{RED}✖ Pilihan gak valid.{RESET}")
            time.sleep(0.8)

def select_coin_menu():
    global COIN
    while True:
        clear()
        print(_sep_line())
        print(f"{BOLD}{MAGENTA}{'SELECT COIN':^60}{RESET}")
        print(_sep_line())
        print(f" {WHITE}Current{RESET} : {MAGENTA}{COIN.upper()}{RESET}")
        print(_sep_line())
        print()
        items = list(COINS.items())
        for i in range(0, len(items), 3):
            chunk = items[i:i+3]
            line = "  "
            for k, c in chunk:
                mark = f"{GREEN}*{RESET}" if c == COIN else " "
                line += f"{mark} {WHITE}[{k:>2}]{RESET} {YELLOW}{c.upper():<5}{RESET}  "
            print(line)
        print()
        print(f" {RED}[0]{RESET} Back to Main Menu")
        print()
        print(_sep_line())

        try:
            choice = input(f" {CYAN}❯ Pilih coin [0-15]: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0" or choice == "":
            return
        if choice in COINS:
            COIN = COINS[choice]
            print(f"\n{GREEN}✓ Coin dipilih: {COIN.upper()}{RESET}")
            time.sleep(0.7)
            return
        else:
            print(f"{RED}✖ Pilihan gak valid.{RESET}")
            time.sleep(0.7)

# ═══════════════════ UI DASHBOARD ═══════════════════
class UI:
    state = {
        "title": "VIPCOIN FAUCET AUTO CLAIM",
        "subtitle": "─────── SOUU ENGINE ───────",
        "running": False,
        "bot_name": BOT_NAME,
        "coin": "LTC",
        "mode": "Both",
        "balance": "?",
        "state": "INIT",
        "phase": "-",
        "cooldown": 0,
        "start_ts": int(time.time()),
        "session_reward": 0.0,
        "ad_earned": 0.0,
        "watch_count": 0,
        "success": 0,
        "failed": 0,
        "cycle_count": 0,
        "total_sleeps": 0,
        "sleep_progress": 0,
        "watching_name": "-",
        "watching_progress": 0.0,
        "watching_total": 0,
        "watch_label": "",
    }
    logs = deque(maxlen=300)

    @staticmethod
    def fg(c, s): return f"\033[38;5;{c}m{s}\033[0m"
    @staticmethod
    def bold(s): return f"\033[1m{s}\033[22m"
    @staticmethod
    def dim(s): return f"\033[2m{s}\033[22m"
    @staticmethod
    def _strip(s): return re.sub(r'\033\[[0-9;]*m', '', s)
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
    def c(s, color_name="white"):
        cmap = {
            "cyan": 51, "green": 46, "red": 196, "yellow": 226,
            "magenta": 213, "white": 231, "gray": 245, "blue": 27,
            "br_cyan": 51, "br_green": 46, "br_red": 196, "br_yellow": 226,
            "br_magenta": 213, "br_white": 231, "br_blue": 27, "br_gray": 245,
        }
        return UI.fg(cmap.get(color_name, 231), s)

    @staticmethod
    def banner():
        return

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

        buf += UI.row(UI.bold("SESSION")) + "\n"
        buf += UI.row("├─ " + UI.pad("Bot", 12) + ": " + UI.trunc(UI.fg(226, str(s["bot_name"])), 29)) + "\n"
        buf += UI.row("├─ " + UI.pad("Coin", 12) + ": " + UI.fg(213, str(s["coin"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Mode", 12) + ": " + UI.fg(226, str(s["mode"]))) + "\n"
        buf += UI.mid() + "\n"

        total = s["success"] + s["failed"]
        rate = (s["success"] / total * 100) if total > 0 else 0.0
        buf += UI.row(UI.bold("STATS")) + "\n"
        buf += UI.row("├─ " + UI.pad("Success", 12) + ": " + UI.fg(46, str(s["success"])) + "  " +
                      UI.pad("Failed", 8) + ": " + UI.fg(196, str(s["failed"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Rate", 12) + ": " + UI.fg(226, f"{rate:.1f}%")) + "\n"
        buf += UI.row("├─ " + UI.pad("Balance", 12) + ": " + UI.fg(46, str(s["balance"]))) + "\n"
        buf += UI.row("├─ " + UI.pad("Earned", 12) + ": " + UI.fg(201, f"{s['session_reward']:.8f}") + "\n"
                      "│  " + UI.pad("Watch Ads", 12) + ": " + UI.fg(51, str(s["watch_count"]))) + "\n"
        runtime = int(time.time() - s["start_ts"])
        h, m, sec = runtime // 3600, (runtime % 3600) // 60, runtime % 60
        buf += UI.row("└─ " + UI.pad("Runtime", 12) + ": " + UI.fg(51, f"{h:02d}:{m:02d}:{sec:02d}")) + "\n"
        buf += UI.mid() + "\n"

        buf += UI.row(UI.bold("WATCHING")) + "\n"
        wname = s.get("watching_name", "-")
        wpct = float(s.get("watching_progress", 0.0))
        wtotal = int(s.get("watching_total", 0))
        wlabel = s.get("watch_label", "")
        bar_len = 34
        filled = int(wpct * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        if wname == "-":
            buf += UI.row("├─ " + UI.dim("idle — menunggu…")) + "\n"
            buf += UI.row("├─ [" + UI.dim("░" * bar_len) + "]") + "\n"
        else:
            buf += UI.row("├─ " + UI.fg(226, UI.trunc(wname, 42))) + "\n"
            buf += UI.row("├─ [" + UI.fg(46, bar) + "] " + UI.fg(226, f"{int(wpct*100)}%")) + "\n"

        remain = wtotal - int(wpct * wtotal) if wtotal else 0
        buf += UI.row("└─ " + UI.pad("Label", 9) + ": " + UI.fg(46, UI.trunc(wlabel, 20)) +
                      "  " + UI.pad("Sisa", 5) + ": " + UI.fg(208, f"{remain}s")) + "\n"
        buf += UI.mid() + "\n"

        sleep_bar_len = 34
        cycle = s["cycle_count"]
        spct = min(cycle / SLEEP_AFTER_CLAIMS, 1.0)
        sfilled = int(spct * sleep_bar_len)
        sbar = "█" * sfilled + "░" * (sleep_bar_len - sfilled)
        buf += UI.row(UI.bold("SLEEP PROGRESS")) + "\n"
        buf += UI.row("├─ [" + UI.fg(213, sbar) + "] " + UI.fg(226, f"{cycle}/{SLEEP_AFTER_CLAIMS}")) + "\n"
        buf += UI.row("└─ " + UI.dim(f"Tidur {SLEEP_DURATION_SEC//60}m tiap {SLEEP_AFTER_CLAIMS} claim")) + "\n"
        buf += UI.mid() + "\n"

        phase = str(s["phase"])
        if int(s["cooldown"]) > 0: phase += f" · {int(s['cooldown'])}s"
        state_color = {"INIT": 240, "RUNNING": 46, "WATCHING": 213,
                       "COOLDOWN": 208, "PAUSE": 213, "DONE": 46,
                       "ERROR": 196, "WAITING": 208, "SLEEP": 51}.get(s["state"], 226)
        buf += UI.row(UI.bold("STATUS")) + "\n"
        buf += UI.row("├─ " + UI.pad("State", 12) + ": " + UI.fg(state_color, str(s["state"]))) + "\n"
        buf += UI.row("└─ " + UI.pad("Phase", 12) + ": " + UI.trunc(UI.fg(208, phase), 29)) + "\n"
        buf += UI.mid() + "\n"

        logs = list(UI.logs)[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(logs): buf += UI.row(UI.fmt_log(logs[i])) + "\n"
            else: buf += UI.blank() + "\n"

        buf += UI.bot() + "\n"
        buf += "\n   " + UI.bold(UI.fg(46, "BOT RUNNING")) + " " + UI.dim("• ") + \
               UI.fg(51, datetime.now().strftime("%H:%M:%S")) + "\n"
        buf += "   " + UI.dim("Powered by ") + UI.fg(213, "MoneyMaker_w") + "\n\n"
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
    def watch_timer(duration, name, label="Watching"):
        UI.set(watching_name=name, watching_total=duration, watching_progress=0.0, watch_label=label, state="WATCHING")
        for i in range(1, duration + 1):
            if not UI.state["running"]: break
            UI.set(watching_progress=i / duration, phase=f"{label} {i}/{duration}")
            UI.render()
            time.sleep(1)
        UI.set(watching_name="-", watching_progress=0.0, watching_total=0, watch_label="")

    @staticmethod
    def sleep_timer(seconds, reason=""):
        end_time = time.time() + seconds
        end_str = datetime.fromtimestamp(end_time).strftime("%H:%M:%S")
        UI.set(state="SLEEP", phase=f"Sleep till {end_str}")
        UI.info("SLEEP", f"Tidur {seconds//60}m — lanjut jam {end_str}")

        for left in range(int(seconds), 0, -1):
            m = left // 60
            s = left % 60
            UI.set(phase=f"Sleep {m:02d}:{s:02d}")
            if UI.state["running"]: UI.render()
            time.sleep(1)

        UI.ok("SLEEP", "Bangun — lanjut claim")

# ═══════════════════ LOGGING (Map to UI) ═══════════════════
def log(msg, tag="i"):
    mapping = {
        "i": ("INFO", "info", "◈"), "ok": ("OK", "ok", "✔"),
        "er": ("ERR", "err", "✖"), "wr": ("WARN", "warn", "◈"),
        "money": ("CLAIM", "ok", "⬢"), "sleep": ("SLEEP", "info", "◈"),
        "ad": ("AD", "info", "⬢")
    }
    t, kind, icon = mapping.get(tag, ("INFO", "info", "◈"))
    UI.push(t, msg, kind, icon)

def clear():
    os.system("clear" if os.name == "posix" else "cls")

# ═══════════════════ TELETHON INIT-DATA AUTO FETCH ═══════════════════
def _load_session_str(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""

def _save_session_str(path, s):
    try:
        with open(path, "w") as f:
            f.write(s)
    except Exception as e:
        log(f"Gagal simpen session: {e}", "wr")

async def _fetch_init_data_async():
    sess_str = _load_session_str(SESSION_FILE)
    client = TelegramClient(StringSession(sess_str), API_ID, API_HASH)

    is_first_run = not sess_str
    if is_first_run:
        clear()
        print(f"""{CYAN}{SEP}
{BOLD}{MAGENTA}{'FIRST RUN — TELETHON LOGIN':^60}{RESET}
{CYAN}{SEP}
 {WHITE}Belum ada session tersimpan.{RESET}
 {WHITE}Bakal diminta nomor HP + kode OTP sekali.{RESET}
 {WHITE}Setelah login, session disimpen ke:{RESET}
   {YELLOW}{SESSION_FILE}{RESET}
 {WHITE}Run berikutnya auto login tanpa prompt.{RESET}
{CYAN}{SEP}{RESET}
""")
        time.sleep(0.8)

    print(f"{CYAN}❯ Telethon connecting...{RESET}")
    await client.start()

    _save_session_str(SESSION_FILE, client.session.save())
    print(f"{GREEN}✓ Session tersimpan{RESET}")
    print(f"{CYAN}❯ Ambil initData via webview...{RESET}")

    try:
        try:
            bot_entity = await client.get_entity(BOT_USERNAME)
        except Exception:
            print(f"{YELLOW}◈ Belum pernah chat bot, kirim /start dulu...{RESET}")
            await client.send_message(BOT_USERNAME, "/start")
            await asyncio.sleep(2.5)
            bot_entity = await client.get_entity(BOT_USERNAME)

        bot_peer = await client.get_input_entity(bot_entity)
        bot_user = InputUser(bot_entity.id, bot_entity.access_hash)

        result = None
        try:
            result = await client(RequestWebViewRequest(
                peer=bot_peer, bot=bot_user,
                platform="android", from_bot_menu=True,
                url=f"{HOST}/",
            ))
        except Exception as e1:
            print(f"{YELLOW}◈ from_bot_menu gagal: {e1}{RESET}")
            try:
                result = await client(RequestWebViewRequest(
                    peer=bot_peer, bot=bot_user,
                    platform="android", from_bot_menu=False,
                    url=f"{HOST}/",
                ))
            except Exception as e2:
                print(f"{RED}✖ webview gagal: {e2}{RESET}")

        raw = None
        if result and result.url:
            parsed = urlparse(result.url)
            raw = parse_qs(parsed.fragment).get("tgWebAppData", [None])[0]
            if not raw:
                raw = parse_qs(parsed.query).get("tgWebAppData", [None])[0]

        if not raw:
            print(f"{YELLOW}◈ Fallback: scan pesan bot buat tgWebAppData...{RESET}")
            async for msg in client.iter_messages(bot_entity, limit=15):
                if not msg.buttons:
                    continue
                found = None
                for row_btns in msg.buttons:
                    for btn in row_btns:
                        u = getattr(btn, "url", None)
                        if not u or "tgWebAppData" not in u:
                            continue
                        pu = urlparse(u)
                        pq = parse_qs(pu.fragment) or parse_qs(pu.query)
                        found = pq.get("tgWebAppData", [None])[0]
                        if found: break
                    if found: break
                if found:
                    raw = found
                    break

        if not raw:
            raise RuntimeError("tgWebAppData gak ketemu (webview + fallback)")

        if "%" in raw and "auth_date=" not in raw:
            raw = unquote(raw)

        return raw
    finally:
        await client.disconnect()

def get_init_data_telethon():
    try:
        data = asyncio.run(_fetch_init_data_async())
    except Exception as e:
        print(f"{RED}✖ Telethon error: {e}{RESET}")
        sys.exit(1)

    if not data or "auth_date=" not in data or "hash=" not in data:
        print(f"{RED}✖ initData tidak valid{RESET}")
        sys.exit(1)

    print(f"{GREEN}✓ initData OK (len={len(data)}){RESET}")
    time.sleep(0.6)
    return data

# ═══════════════════ SESSION & HELPERS ═══════════════════
def make_session(init_data):
    s = requests.Session(impersonate="chrome124")
    s.headers.update({
        "User-Agent": MOBILE_UA,
        "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "X-Telegram-Init-Data": init_data,
    })
    return s

def login(s):
    log("Login via initData...", "i")
    try:
        r = s.get(f"{HOST}/app/dashboard", headers={"Referer": f"{HOST}/", "Origin": HOST}, timeout=30)
        if "auth/logout" in r.text or "pc-user-card" in r.text or "logout" in r.text.lower():
            log("Login OK", "ok")
            m = re.search(r'<h3[^>]*>\s*([\d,]+\.?\d*\s*[A-Z]{2,5})\s*</h3>', r.text)
            if m:
                UI.set(balance=m.group(1).strip())
                log(f"Balance: {UI.state['balance']}", "money")
            return True
    except Exception as e:
        log(f"Dashboard error: {e}", "er")
    log("Login gagal", "er")
    return False

def extract_token(html, names, session=None):
    for name in names:
        for attr in ("name", "id"):
            m = re.search(rf'{attr}=["\']{re.escape(name)}["\'][^>]*value=["\']([^"\']+)["\']', html, re.I)
            if m: return m.group(1)
            m = re.search(rf'value=["\']([^"\']+)["\'][^>]*{attr}=["\']{re.escape(name)}["\']', html, re.I)
            if m: return m.group(1)
        m = re.search(rf'{re.escape(name)}\s*[:=]\s*["\']([^"\']+)["\']', html, re.I)
        if m: return m.group(1)
        if session:
            v = session.cookies.get_dict().get(name)
            if v: return v
    return None

def extract_claim_token(html, session=None): return extract_token(html, ["claim_token", "token", "claim-token"], session)
def extract_csrf(html, session): return extract_token(html, ["csrf_test_name", "csrf_token", "_token", "csrf", "csrf_cookie_name", "XSRF-TOKEN"], session)
def extract_ad_token(html, session=None): return extract_token(html, ["ad_token", "adtoken", "ad-token"], session)

def extract_claim_url(html):
    m = re.search(r'data-claim-url=["\']([^"\']+)["\']', html)
    if m:
        u = m.group(1)
        return HOST + u if u.startswith("/") else u
    return None

def parse_cooldown(html):
    m_min = re.search(r'id=["\']minute["\'][^>]*>\s*(\d+)\s*<', html)
    m_sec = re.search(r'id=["\']second["\'][^>]*>\s*(\d+)\s*<', html)
    if m_min and m_sec: return int(m_min.group(1)) * 60 + int(m_sec.group(1))
    m = re.search(r'id=["\']faucetTimer["\'][^>]*>.*?(\d+)\s*:\s*(\d+).*?<', html, re.DOTALL)
    if m: return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"remaining\s*=\s*Math\.max\(0,\s*(\d+)\)", html)
    if m: return int(m.group(1))
    return 0

def parse_available_ads(html):
    patterns = [
        r'<h3[^>]*>\s*(\d+)\s*</h3>\s*<p[^>]*>\s*Available Ads',
        r'Available Ads[^<]*</[^>]+>\s*<[^>]+>\s*(\d+)',
        r'"?availableAds"?\s*:\s*(\d+)'
    ]
    for p in patterns:
        m = re.search(p, html, re.I | re.DOTALL)
        if m:
            try: return int(m.group(1))
            except: pass
    return None

def update_balance_from_html(html, session):
    m = re.search(r'<h3[^>]*>\s*([\d,]+\.?\d*\s*[A-Z]{2,5})\s*</h3>', html)
    if m: UI.set(balance=m.group(1).strip())
    m = re.search(rf"([0-9.]+)\s+{COIN.upper()}\s+has been", html, re.I)
    if m: return float(m.group(1))
    m = re.search(rf"([0-9.]+)\s+{COIN.upper()}", html, re.I)
    if m:
        try: return float(m.group(1))
        except: pass
    return None

# ═══════════════════ CLAIM FAUCET ═══════════════════
def claim_faucet(s):
    faucet_url = f"{HOST}/faucet/currency/{COIN}"
    UI.set(phase="fetching faucet", state="RUNNING")
    UI.render()

    try:
        r = s.get(faucet_url, headers={"Referer": f"{HOST}/app/dashboard", "Origin": HOST}, timeout=30)
        html = r.text
    except Exception as e:
        log(f"Fetch error: {e}", "er")
        return False

    cd = parse_cooldown(html)
    if cd > 0:
        log(f"Cooldown {cd}s", "wr")
        return cd

    claim_token = extract_claim_token(html, s)
    csrf = extract_csrf(html, s)

    if not claim_token or not csrf:
        log("claim_token / CSRF tidak ada", "er")
        return False

    log(f"claim_token: {claim_token[:16]}...", "i")

    payload = {"csrf_test_name": csrf, "claim_token": claim_token, "tg_init_data": INIT_DATA}
    headers = {
        "Referer": faucet_url, "Origin": HOST,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "org.telegram.messenger",
        "X-Telegram-Init-Data": INIT_DATA,
    }

    UI.set(phase="verifying")
    UI.render()

    try:
        vr = s.post(f"{HOST}/faucet/currency/{COIN}/verify", data=payload, headers=headers, timeout=30, allow_redirects=False)
    except Exception as e:
        log(f"Verify error: {e}", "er")
        return False

    if vr.status_code in (301, 302, 303):
        # curl_cffi Session otomatis nyimpen Set-Cookie dari redirect response.
        loc = vr.headers.get("Location", "")
        amt = None
        if loc:
            log(f"Verify OK — nunggu {REDIRECT_DELAY}s sebelum fetch redirect", "i")
            time.sleep(REDIRECT_DELAY)
            try:
                r2 = s.get(loc, timeout=30)
                amt = update_balance_from_html(r2.text, s)
                new_cd = parse_cooldown(r2.text)
                if new_cd > 0: log(f"Next claim in {new_cd}s", "i")
            except Exception as e:
                log(f"Redirect fetch error: {e}", "wr")

        if amt is not None:
            UI.set(session_reward=UI.state["session_reward"] + amt)
            log(f"FAUCET +{amt} {COIN.upper()}", "money")
        else:
            log("FAUCET SUCCESS", "money")
        return True

    if vr.status_code == 200:
        body = vr.text.lower()
        if "has been send" in body or "success" in body:
            amt = update_balance_from_html(vr.text, s)
            if amt is not None:
                UI.set(session_reward=UI.state["session_reward"] + amt)
                log(f"FAUCET +{amt} {COIN.upper()}", "money")
            else:
                log("FAUCET SUCCESS", "money")
            return True

        m = re.search(r'class="alert[^"]*alert-danger"[^>]*>\s*([^<]+)', vr.text)
        if m: log(f"❌ {m.group(1).strip()[:40]}", "er")
        return False

    log(f"Faucet status {vr.status_code}", "wr")
    return False

# ═══════════════════ WATCH ADS ═══════════════════
def watch_ads(s):
    ads_url = f"{HOST}/links/currency/{COIN}"
    UI.set(phase="fetching ads", state="RUNNING")
    UI.render()

    try:
        r = s.get(ads_url, headers={"Referer": f"{HOST}/app/dashboard", "Origin": HOST}, timeout=30)
        html = r.text
    except Exception as e:
        log(f"Ads fetch error: {e}", "er")
        return False

    csrf = extract_csrf(html, s)
    ad_token = extract_ad_token(html, s)
    claim_url = extract_claim_url(html)
    available_ads = parse_available_ads(html)

    if not ad_token or not claim_url or not csrf:
        log("ad_token / claim_url / CSRF hilang", "er")
        return False

    if available_ads is not None and available_ads <= 0:
        log("Tidak ada ads tersedia", "wr")
        return False

    UI.watch_timer(WATCH_DURATION, f"Ad ({COIN.upper()})", "Watching")

    UI.set(phase="confirming ad", state="RUNNING")
    UI.render()

    confirm_payload = {"csrf_test_name": csrf, "ad_token": ad_token}
    confirm_headers = {
        "Referer": ads_url, "Origin": HOST,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "org.telegram.messenger",
        "X-Telegram-Init-Data": INIT_DATA,
    }

    try:
        cr = s.post(f"{HOST}/app/links/confirm_ad", data=confirm_payload, headers=confirm_headers, timeout=30)
    except Exception as e:
        log(f"Confirm error: {e}", "er")
        return False

    new_csrf = csrf
    csrf_field_name = "csrf_test_name"

    if cr.status_code == 200:
        try:
            cdata = cr.json()
            if cdata.get("status") != "ok" and not cdata.get("csrf_hash"):
                log(f"Confirm rejected: {cdata}", "er")
                return False
            new_csrf = cdata.get("csrf_hash") or csrf
            csrf_field_name = cdata.get("csrf_name", "csrf_test_name")
            if cdata.get("csrf_hash"):
                s.cookies.set("csrf_cookie_name", new_csrf, domain=HOST.replace("https://", ""))
            log("Ad confirmed", "ad")
        except Exception:
            log("Ad confirmed (no JSON)", "ad")
    else:
        log(f"Confirm failed HTTP {cr.status_code}", "er")
        return False

    UI.set(phase="claiming ad reward")
    UI.render()

    time.sleep(random.uniform(1.5, 3.0))

    claim_payload = {csrf_field_name: new_csrf, "ad_token": ad_token}
    try:
        rr = s.post(claim_url, data=claim_payload, headers=confirm_headers, timeout=30, allow_redirects=False)
    except Exception as e:
        log(f"Claim error: {e}", "er")
        return False

    if rr.status_code in (301, 302, 303):
        # curl_cffi Session auto-handle cookie dari redirect.
        log(f"AD SUCCESS (redirect) — nunggu {REDIRECT_DELAY}s", "money")
        loc = rr.headers.get("Location", "")
        amt = None
        if loc:
            time.sleep(REDIRECT_DELAY)
            try:
                r2 = s.get(loc, timeout=30)
                amt = update_balance_from_html(r2.text, s)
            except Exception as e:
                log(f"Redirect fetch error: {e}", "wr")

        if amt is not None:
            UI.set(session_reward=UI.state["session_reward"] + amt, ad_earned=UI.state["ad_earned"] + amt)
            log(f"AD +{amt} {COIN.upper()}", "money")
        else:
            log("AD REWARD", "money")
        UI.set(watch_count=UI.state["watch_count"] + 1)
        return True

    if rr.status_code == 200:
        body = rr.text.lower()
        if "success" in body or "claimed" in body:
            amt = update_balance_from_html(rr.text, s)
            if amt is not None:
                UI.set(session_reward=UI.state["session_reward"] + amt, ad_earned=UI.state["ad_earned"] + amt)
                log(f"AD +{amt} {COIN.upper()}", "money")
            else:
                log("AD REWARD", "money")
            UI.set(watch_count=UI.state["watch_count"] + 1)
            return True

    log(f"Ad claim status {rr.status_code}", "wr")
    return False

# ═══════════════════ MAIN LOOP ═══════════════════
def main():
    global INIT_DATA, COIN, MODE

    # ── SOUU ENGINE MENU ──
    main_menu()

    # ── AUTO INIT-DATA VIA TELETHON ──
    INIT_DATA = get_init_data_telethon()

    s = make_session(INIT_DATA)
    clear()
    if not login(s):
        print(f"{RED}✖ Login gagal, keluar.{RESET}")
        return

    UI.set(coin=COIN.upper(), mode=mode_name_of(MODE), state="INIT")
    UI.start_panel()
    UI.ok("START", f"Coin {COIN.upper()} | Mode {UI.state['mode']}")

    consecutive_fail = 0
    alt = 0
    stop_reason = "finished"

    try:
        while True:
            if MODE == "1":
                result = watch_ads(s)
                is_faucet = False
            elif MODE == "2":
                result = claim_faucet(s)
                is_faucet = True
            else:
                alt += 1
                if alt % 2 == 1:
                    result = watch_ads(s)
                    is_faucet = False
                else:
                    result = claim_faucet(s)
                    is_faucet = True

            if result is True:
                UI.set(success=UI.state["success"] + 1)
                consecutive_fail = 0

                if is_faucet:
                    UI.set(cycle_count=UI.state["cycle_count"] + 1)
                    if UI.state["cycle_count"] >= SLEEP_AFTER_CLAIMS:
                        UI.set(total_sleeps=UI.state["total_sleeps"] + 1)
                        UI.sleep_timer(SLEEP_DURATION_SEC)
                        UI.set(cycle_count=0)
                        continue
                    UI.countdown(random.uniform(3, 6), "next cycle")
                else:
                    UI.countdown(WATCH_COOLDOWN + random.uniform(1, 3), "next ad")

            elif isinstance(result, int) and result > 0:
                UI.countdown(result + COOLDOWN_MARGIN, "cooldown")
                continue

            else:
                UI.set(failed=UI.state["failed"] + 1)
                consecutive_fail += 1
                UI.warn("FAIL", f"Gagal {consecutive_fail}/{MAX_FAIL_STREAK}")

                if consecutive_fail >= MAX_FAIL_STREAK:
                    UI.err("STOP", f"{consecutive_fail}x gagal berturut-turut")
                    stop_reason = "fail_limit"
                    break
                UI.countdown(15, "retry")

    except KeyboardInterrupt:
        stop_reason = "user_stopped"
        UI.warn("STOP", "Dihentikan user")

    finally:
        UI.set(state="DONE", phase=stop_reason)
        UI.stop_panel()
        print()
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c("  ✓ BOT SELESAI", "br_green"))
        print(UI.c("═" * 64, "br_cyan"))
        print(UI.c(f"  Reason      : {stop_reason}", "white"))
        print(UI.c(f"  Success     : {UI.state['success']}", "br_green"))
        print(UI.c(f"  Failed      : {UI.state['failed']}", "br_red"))
        print(UI.c(f"  Balance     : {UI.state['balance']}", "br_yellow"))
        print(UI.c(f"  Earned      : {UI.state['session_reward']:.8f} {COIN.upper()}", "br_green"))
        print(UI.c(f"  Watch Ads   : {UI.state['watch_count']}", "br_cyan"))
        print(UI.c(f"  Total Sleep : {UI.state['total_sleeps']}", "br_blue"))
        print(UI.c("═" * 64, "br_cyan"))
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Dihentikan.{RESET}")
