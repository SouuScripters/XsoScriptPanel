#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRX Miner Auto Claim — SOUU ENGINE EDITION
Login by Email + Password (auto relogin)
Flow : Login → Daily (once) → Faucet Loop
Config: configtrexminer.json
Captcha Solver : Waryono
UI by Souu Engine
"""

import requests
import json
import time
import os
import sys
import random
from datetime import datetime

# ======================== KONSTANTA ========================
CONFIG_FILE = "configtrexminer.json"
BASE_URL = "https://trxminer.net"
HCAPTCHA_SITEKEY = "764c22e4-3102-4218-8130-1c848c282506"
USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
FAUCET_INTERVAL = 310

# ======================== ANSI COLOR ========================
RST  = "\033[0m"
RED  = "\033[0;31m"
GRN  = "\033[0;32m"
YEL  = "\033[0;33m"
WHT  = "\033[0;37m"
BOLD = "\033[1m"

def fg(c):
    return f"\033[38;5;{c}m"

def strip_ansi(s):
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def ansi_len(s):
    plain = strip_ansi(s)
    w = 0
    for ch in plain:
        cp = ord(ch)
        if (0x1F300 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF) or \
           (0x2B00 <= cp <= 0x2BFF) or (0x25A0 <= cp <= 0x25FF) or \
           (0x2580 <= cp <= 0x259F):
            w += 2
        else:
            w += 1
    return w

def ansi_pad(s, length):
    p = length - ansi_len(s)
    return s + (" " * p if p > 0 else "")

def gradient(text, start=51, end=196):
    if len(text) <= 1:
        return fg(start) + text + RST
    out = ""
    n = len(text)
    for i, ch in enumerate(text):
        t = i / max(1, n - 1)
        c = int(round(start + (end - start) * t))
        out += fg(c) + ch
    return out + RST

def box_line(content):
    return fg(51) + "║  " + RST + ansi_pad(content, 60) + fg(51) + "║" + RST + "\n"

def box_div():
    return fg(51) + "╠" + ("═" * 62) + "╣" + RST + "\n"

# ======================== GLOBAL STATE ========================
_state = {
    "start_time": time.time(),
    "claims": 0,
    "total_gained": 0,
    "fails": 0,
    "email": "-",
    "user": "-",
    "active_action": "-",
    "last_gain": 0,
    "balance": 0,
    "hashpower": 0,
    "daily_done": False,
    "logs": [],
    "relogin_count": 0,
}

def push_log(msg, tag="i"):
    icons = {
        "i":  fg(51)  + "●" + RST,
        "ok": fg(46)  + "✔" + RST,
        "er": fg(196) + "✖" + RST,
        "wr": fg(208) + "◈" + RST,
        "in": fg(213) + "⬢" + RST,
        "g":  fg(226) + "◆" + RST,
    }
    ts = datetime.now().strftime("%H:%M:%S")
    line = fg(250) + f"[{ts}]" + RST + " " + icons.get(tag, "●") + " " + msg
    _state["logs"].append(line)
    if len(_state["logs"]) > 6:
        _state["logs"].pop(0)

def fmt_uptime(s):
    s = int(s)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"

def format_number(n):
    try:
        return f"{int(n):,}"
    except:
        return str(n)

# ======================== TAMPILAN ========================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    elapsed = time.time() - _state["start_time"]
    claims = _state["claims"]
    total = _state["total_gained"]
    fails = _state["fails"]
    daily_status = "CLAIMED" if _state["daily_done"] else "PENDING"

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(fg(51) + "╔" + ("═" * 62) + "╗" + RST + "\n")
    sys.stdout.write(box_line(gradient("TRX MINER AUTO CLAIM", 51, 213)))
    sys.stdout.write(box_line(fg(240) + "─────── SOUU ENGINE ───────" + RST))
    sys.stdout.write(box_div())

    sys.stdout.write(box_line(fg(213) + BOLD + "CAPTCHA" + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Type     : " + RST + fg(226) + "HCAPTCHA" + RST))
    sys.stdout.write(box_line(fg(51) + "└─ Solver   : " + RST + fg(226) + "waryono" + RST))
    sys.stdout.write(box_div())

    sys.stdout.write(box_line(fg(213) + BOLD + "ACCOUNT" + RST))
    sys.stdout.write(box_line(fg(51) + "├─ User       : " + RST + fg(226) + str(_state["user"]) + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Email      : " + RST + fg(226) + str(_state["email"]) + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Balance    : " + RST + fg(226) + format_number(_state["balance"]) + " coins" + RST))
    sys.stdout.write(box_line(fg(51) + "└─ Hashpower  : " + RST + fg(226) + format_number(_state["hashpower"]) + " H/s" + RST))
    sys.stdout.write(box_div())

    sys.stdout.write(box_line(fg(213) + BOLD + "INCOME" + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Total      : " + RST + fg(46) + "+" + f"{total:,}" + " coins" + RST))
    sys.stdout.write(box_line(fg(51) + "└─ Last       : " + RST + fg(46) + "+" + f"{_state['last_gain']:,}" + " coins" + RST))
    sys.stdout.write(box_div())

    sys.stdout.write(box_line(fg(213) + BOLD + "SYSTEM" + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Action       : " + RST + fg(226) + str(_state["active_action"]).upper() + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Daily        : " + RST + (fg(46) if _state["daily_done"] else fg(208)) + daily_status + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Claims       : " + RST + fg(226) + str(claims) + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Relogins     : " + RST + fg(226) + str(_state["relogin_count"]) + RST))
    sys.stdout.write(box_line(fg(51) + "├─ Failures     : " + RST + (fg(196) if fails >= 5 else fg(226)) + str(fails) + " / 5" + RST))
    sys.stdout.write(box_line(fg(51) + "└─ Runtime      : " + RST + fg(226) + fmt_uptime(elapsed) + RST))
    sys.stdout.write(box_div())

    logs = _state["logs"]
    for i in range(6):
        if i < len(logs):
            sys.stdout.write(box_line(fg(252) + logs[i] + RST))
        else:
            sys.stdout.write(fg(51) + "║" + (" " * 62) + "║" + RST + "\n")

    sys.stdout.write(fg(51) + "╚" + ("═" * 62) + "╝" + RST + "\n")
    sys.stdout.write("\n   " + gradient("BOT RUNNING", 46, 226) + " " + fg(250) + "• " + datetime.now().strftime("%H:%M:%S") + RST + "\n")
    sys.stdout.write("   " + fg(240) + "Souu Engine Edition" + RST + "\n\n")
    sys.stdout.flush()

# ======================== ANIMASI ========================
def animated_check():
    frames = [
        (fg(51),  "⠋"), (fg(39),  "⠙"), (fg(213), "⠹"),
        (fg(208), "⠸"), (fg(51),  "⠼"), (fg(39),  "⠴"),
        (fg(213), "⠦"), (fg(208), "⠧"), (fg(51),  "⠇"),
        (fg(46),  "⠏"), (fg(46),  "✓")
    ]
    for color, frame in frames:
        sys.stdout.write(f"\r{color}{frame}{RST}")
        sys.stdout.flush()
        time.sleep(0.055)
    sys.stdout.write("\r")
    return fg(46) + "✓" + RST

def waiting_timer(seconds):
    colors = [fg(51), fg(39), fg(213), fg(208), fg(46)]
    i = 0
    print()
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        timer = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"00:{mins:02d}:{secs:02d}"
        dots = "." * ((seconds - remaining) % 4)
        color = colors[i % len(colors)]
        sys.stdout.write(f"\r  {color}⣾ waiting  {timer} {dots:<3}{RST}")
        sys.stdout.flush()
        time.sleep(1)
        i += 1
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

# ======================== CONFIG ========================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_config():
    clear()
    banner()
    print(fg(213) + BOLD + "\n[ UPDATE EMAIL / PASSWORD / API KEY ]\n" + RST)
    print("Isi kredensial akun TRX Miner + API key Waryono.\n")

    old = load_config()
    cur_email = old.get("email", "")
    cur_pass  = old.get("password", "")
    cur_key   = old.get("waryono_apikey", "")

    email = input(fg(51) + f"Email [{cur_email}]: " + RST).strip() or cur_email
    password = input(fg(51) + f"Password [{'*'*len(cur_pass) if cur_pass else '-'}]: " + RST).strip() or cur_pass
    apikey = input(fg(51) + f"API Key Waryono [{cur_key[:8]}...]: " + RST).strip() or cur_key

    if not email or not password or not apikey:
        print(fg(196) + "\nEmail / Password / API Key tidak boleh kosong!" + RST)
        time.sleep(2)
        return

    save_config({
        "email": email,
        "password": password,
        "waryono_apikey": apikey,
    })
    print(fg(46) + "\n✓ Config berhasil disimpan!" + RST)
    time.sleep(1.5)

# ======================== SESSION ========================
session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/dashboard",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
})

def do_login(email, password):
    """POST /api/login → simpan cookie trx_session di session."""
    try:
        session.cookies.clear()
        r = session.post(
            f"{BASE_URL}/api/login",
            json={"email": email, "password": password},
            timeout=35
        )
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"

        # cookie biasanya otomatis masuk ke session.cookies
        if "trx_session" not in session.cookies.get_dict():
            return False, "cookie trx_session tidak diterima"

        data = r.json() if r.text.strip().startswith("{") else {}
        if data and data.get("ok") is False:
            return False, data.get("error", "login gagal")

        return True, "ok"
    except Exception as e:
        return False, str(e)

# ======================== API WRAPPER ========================
class SessionExpired(Exception):
    pass

def api(path, body=None, _retry=True):
    url = f"{BASE_URL}{path}"
    try:
        if body is not None:
            r = session.post(url, json=body, timeout=35)
        else:
            r = session.get(url, timeout=35)

        # deteksi session expired → trigger re-login
        if r.status_code in (401, 403):
            raise SessionExpired(f"HTTP {r.status_code} (session expired)")

        try:
            data = r.json()
        except:
            # bukan JSON, cek redirect ke /login
            if "/login" in r.text[:500] or r.status_code == 302:
                raise SessionExpired("redirect ke /login")
            raise Exception(f"respon bukan JSON (HTTP {r.status_code})")

        if not data.get("ok"):
            err = data.get("error") or f"HTTP {r.status_code}"
            if any(k in err.lower() for k in ["unauthor", "login", "session", "invalid token"]):
                raise SessionExpired(err)
            raise Exception(err)

        return data
    except SessionExpired:
        if not _retry:
            raise
        # auto re-login
        cfg = load_config()
        if not cfg.get("email") or not cfg.get("password"):
            raise Exception("session expired & credential kosong — update config dulu")
        push_log("session expired → re-login...", "wr")
        ok, msg = do_login(cfg["email"], cfg["password"])
        if not ok:
            raise Exception(f"re-login gagal: {msg}")
        _state["relogin_count"] += 1
        push_log("re-login berhasil", "ok")
        return api(path, body, _retry=False)

def check_login():
    try:
        data = api("/api/me")
        user = data.get("user", {})
        _state["user"] = user.get("username") or "TRXMiner User"
        _state["email"] = user.get("email") or "-"
        _state["balance"] = user.get("coins", 0)
        _state["hashpower"] = user.get("miningPower") or user.get("hashpower") or 0
        return data
    except Exception as e:
        push_log(f"check login gagal → {e}", "er")
        return None

# ======================== CAPTCHA SOLVER ========================
def solve_hcaptcha(apikey):
    print(fg(51) + "↻ Mengirim captcha ke Waryono..." + RST, end="", flush=True)

    payload = {
        "apikey": apikey,
        "methods": "hcaptcha",
        "domain": BASE_URL,
        "sitekey": HCAPTCHA_SITEKEY,
        "json": 1
    }
    r = requests.post("https://api.waryono.my.id/in.php", json=payload, timeout=60)
    res = r.json()
    if res.get("status") != 1:
        print()
        raise Exception(f"Submit gagal: {res}")

    task_id = res["request"]
    frames = [fg(51)+"⠋", fg(39)+"⠙", fg(213)+"⠹", fg(208)+"⠸",
              fg(51)+"⠼", fg(39)+"⠴", fg(213)+"⠦", fg(208)+"⠧",
              fg(51)+"⠇", fg(46)+"⠏"]
    i = 0

    for detik in range(50):
        time.sleep(2.8)
        check = requests.get(
            f"https://api.waryono.my.id/res.php?apikey={apikey}&action=get&id={task_id}&json=1",
            timeout=30
        ).json()

        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r{frame} {fg(213)}Menunggu captcha Waryono... ({detik}s){RST}")
        sys.stdout.flush()
        i += 1

        if check.get("status") == 1:
            print(f"\r{fg(46)}✓ Captcha berhasil disolve!{' '*35}{RST}")
            return check["request"]
        if "NOT_READY" not in str(check.get("request", "")):
            print()
            raise Exception(f"Waryono: {check}")

    print()
    raise Exception("Timeout menunggu captcha")

# ======================== FAKE INTERACTION ========================
def fake_interaction():
    return {
        "elapsedMs": random.randint(9000, 20000),
        "focusMs": random.randint(7000, 16000),
        "pointerDowns": random.randint(1, 5),
        "pointerUps": random.randint(1, 5),
        "pointerMoves": random.randint(20, 80),
        "touchStarts": 0,
        "keydowns": random.randint(0, 3),
        "scrolls": random.randint(0, 4),
        "untrustedEvents": 0,
        "visible": True
    }

# ======================== DAILY ========================
def claim_daily_bonus(apikey):
    _state["active_action"] = "daily bonus"
    try:
        push_log("mengambil daily bonus...", "in")
        data = api("/api/daily-bonus", {})

        user = data.get("user", {})
        coins = user.get("coins", 0)
        gained = data.get("claimedDailyBonusCoins") or 25

        _state["balance"] = coins
        _state["claims"] += 1
        _state["total_gained"] += int(gained)
        _state["last_gain"] = int(gained)
        _state["daily_done"] = True
        push_log(f"[DAILY] +{gained} coins | balance: {format_number(coins)}", "ok")
        return True
    except Exception as e:
        msg = str(e).lower()
        if any(x in msg for x in ["already", "cooldown", "claimed", "wait", "sudah"]):
            _state["daily_done"] = True
            push_log("[DAILY] sudah diklaim hari ini", "wr")
            return True
        push_log(f"[DAILY] gagal: {e}", "er")
        return False

# ======================== FAUCET ========================
def claim_faucet_once(apikey):
    _state["active_action"] = "faucet"
    try:
        push_log("mengambil challenge faucet...", "in")
        print(fg(51) + "↻ Mengambil challenge faucet..." + RST, end="", flush=True)
        challenge = api("/api/faucet/challenge")
        claim_token = challenge.get("claimToken")
        if not claim_token:
            print()
            raise Exception("Gagal mendapatkan claimToken")

        ready_at = challenge.get("readyAt", 0)
        now = int(time.time() * 1000)
        if ready_at > now:
            wait = (ready_at - now) / 1000 + 0.5
            print(f"\r{fg(208)}↻ Menunggu readyAt {wait:.1f}s...{' '*20}{RST}")
            time.sleep(wait)
        else:
            print(f"\r{fg(46)}✓ Challenge siap{' '*30}{RST}")

        captcha_token = solve_hcaptcha(apikey)

        body = {
            "captchaToken": captcha_token,
            "claimToken": claim_token,
            "interaction": fake_interaction()
        }
        data = api("/api/faucet", body)

        user = data.get("user", {})
        balance = user.get("coins", 0)
        hashpower = user.get("miningPower") or user.get("hashpower") or 0
        gained = data.get("claimedCoins") or data.get("reward") or 5

        _state["balance"] = balance
        _state["hashpower"] = hashpower
        _state["claims"] += 1
        _state["total_gained"] += int(gained)
        _state["last_gain"] = int(gained)

        animated_check()
        push_log(f"+{gained} coins | balance: {format_number(balance)} | hp: {format_number(hashpower)} H/s", "ok")
        return True

    except Exception as e:
        msg = str(e).lower()
        if any(x in msg for x in ["cooldown", "wait", "5 minute", "already"]):
            push_log("masih dalam cooldown", "wr")
        else:
            _state["fails"] += 1
            push_log(f"faucet gagal: {e}", "er")
        return False

# ======================== MAIN LOOP ========================
def run_bot():
    cfg = load_config()
    if not cfg.get("email") or not cfg.get("password"):
        clear()
        banner()
        print(fg(196) + "\nConfig belum lengkap. Silakan update data dulu (menu 2)." + RST)
        time.sleep(2)
        return
    if not cfg.get("waryono_apikey"):
        clear()
        banner()
        print(fg(196) + "\nAPI key Waryono belum diisi (menu 2)." + RST)
        time.sleep(2)
        return

    email = cfg["email"]
    password = cfg["password"]
    apikey = cfg["waryono_apikey"]
    _state["email"] = email

    # --- login ---
    banner()
    push_log("login ke trxminer.net...", "in")
    banner()
    ok, msg = do_login(email, password)
    if not ok:
        push_log(f"login gagal: {msg}", "er")
        banner()
        print(fg(196) + f"\nLogin gagal: {msg}" + RST)
        time.sleep(3)
        return
    push_log("login sukses", "ok")
    banner()

    # --- verify ---
    if not check_login():
        time.sleep(2)
        return
    push_log(f"selamat datang, {_state['user']}", "g")
    banner()

    # --- daily (sekali) ---
    push_log("cek daily bonus...", "in")
    banner()
    claim_daily_bonus(apikey)
    banner()

    # kalau daily udah beres, lanjut loop faucet
    try:
        while True:
            banner()
            sukses = claim_faucet_once(apikey)

            if sukses:
                waiting_timer(FAUCET_INTERVAL)
            else:
                push_log("tunggu 15 detik sebelum retry", "wr")
                banner()
                time.sleep(15)

    except KeyboardInterrupt:
        push_log("loop dihentikan", "wr")
        banner()
        print(f"\n{fg(208)}Loop dihentikan. Kembali ke menu...{RST}")
        time.sleep(1.5)

# ======================== MENU ========================
def main_menu():
    while True:
        clear()
        banner()

        cfg = load_config()
        ready = bool(cfg.get("email") and cfg.get("password") and cfg.get("waryono_apikey"))

        print()
        if ready:
            print(fg(46) + "  Status Config : ✓ LENGKAP" + RST)
            print(fg(240) + f"  Email  : {cfg.get('email', '-')}" + RST)
            print(fg(240) + f"  APIKey : {cfg.get('waryono_apikey','-')[:12]}..." + RST)
        else:
            print(fg(196) + "  Status Config : ✗ BELUM LENGKAP" + RST)
            print(fg(240) + "  Isi email, password, dan API key di menu 2." + RST)

        print()
        print(fg(51) + "─" * 60 + RST)
        print()
        print(fg(255) + "  [1] Start Bot (Daily → Faucet Loop)" + RST)
        print(fg(255) + "  [2] Update Email / Password / API Key" + RST)
        print(fg(255) + "  [0] Keluar" + RST)
        print()
        print(fg(51) + "─" * 60 + RST)

        pilihan = input(fg(51) + "\nPilih [1 / 2 / 0 Keluar]: " + RST).strip()

        if pilihan == "1":
            run_bot()
        elif pilihan == "2":
            update_config()
        elif pilihan == "0":
            clear()
            print(fg(208) + "\nTerima kasih sudah memakai script ini!\n" + RST)
            print(fg(46) + "Jangan Lupa Bersyukur Dan Teruslah Berusaha \n" + RST)
            break
        else:
            print(fg(196) + "Pilihan tidak valid!" + RST)
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
