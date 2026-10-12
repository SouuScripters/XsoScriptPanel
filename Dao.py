#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto bot"""

import json
import os
import sys
import time
import random
import re
import threading
import requests
from datetime import datetime
from pathlib import Path

# ==================== CONFIG LOCATION ====================
SCRIPT_DIR  = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "bconfig.json"

BASE       = "https://bullydao.org"
SOLVER_IN  = "https://api.waryono.my.id/in.php"
SOLVER_RES = "https://api.waryono.my.id/res.php"
SITEKEY    = "0x4AAAAAAExQ_oRN72W6jvby"

DEFAULT_CONFIG = {
    "k": "",                # waryono apikey
    "u": "",                # email
    "enable_auto_login": True,
    "enable_faucet": True,
    "enable_jackpot": True,
    "enable_balance_check": True,
    "turnstile_action_login": "",
    "turnstile_action_faucet": "",
    "turnstile_action_jackpot": "",
    "human_delay_min": 20,
    "human_delay_max": 60,
    "solver_jitter_min": 0.8,
    "solver_jitter_max": 2.5,
    "faucet_cooldown_default": 300,
    "jackpot_cooldown_default": 600,
    "session_check_every": 10,
}

LOOP_DELAY = 30

# ==================== COLORS ====================
class C:
    R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; MAGENTA = "\033[95m"; BLUE = "\033[94m"
    WHITE = "\033[97m"; GRAY = "\033[90m"

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_spin_idx = 0
_spin_lock = threading.Lock()

STATE = {
    "balance": None,
    "total_claims": 0,
    "total_cashout": 0.0,
    "faucet_next_at": 0.0,
    "jackpot_next_at": 0.0,
    "faucet_claimed": 0,
    "jackpot_claimed": 0,
    "jackpot_coins": 0,
    "faucet_coins": 0,
    "logged_in": False,
    "started_at": time.time(),
    "relogin_count": 0,
}

current_cfg = None

# ==================== UI ====================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def banner():
    clear()
    print(f"""{C.CYAN}{C.BOLD}
   ╔══════════════════════════════════════════════════════════════╗
   ║           🌊  B U L L Y D A O . O R G  🌊                    ║
   ╚══════════════════════════════════════════════════════════════╝
""")

def log(msg, level="info"):
    icons = {
        "info":    f"{C.CYAN}ℹ{C.R}",
        "ok":      f"{C.GREEN}✔{C.R}",
        "warn":    f"{C.YELLOW}⚠{C.R}",
        "err":     f"{C.RED}✖{C.R}",
        "coin":    f"{C.YELLOW}🪙{C.R}",
        "dice":    f"{C.MAGENTA}🎲{C.R}",
        "auth":    f"{C.BLUE}🔐{C.R}",
        "captcha": f"{C.BLUE}🛡 {C.R}",
        "wait":    f"{C.GRAY}⏳{C.R}",
        "bal":     f"{C.GREEN}💰{C.R}",
        "sleep":   f"{C.GRAY}💤{C.R}",
    }
    icon = icons.get(level, icons["info"])
    print(f"{C.GRAY}[{now_str()}]{C.R} {icon}  {msg}")

def section(title):
    print(f"\n{C.BOLD}{C.GREEN}▸ {title}{C.R}")
    print(f"{C.GRAY}{'─' * 52}{C.R}")

def spinner_line(text):
    global _spin_idx
    with _spin_lock:
        frame = SPINNER[_spin_idx % len(SPINNER)]
        _spin_idx += 1
    sys.stdout.write(f"\r{C.CYAN}{frame}{C.R}  {text}   ")
    sys.stdout.flush()

def clear_line():
    sys.stdout.write("\r" + " " * 120 + "\r")
    sys.stdout.flush()

def status_bar(cfg):
    now = time.time()
    bal = STATE["balance"]
    bal_str = f"{C.GREEN}{bal:,.2f}{C.R} DAO" if bal is not None else f"{C.GRAY}---{C.R}"

    if not cfg.get("enable_faucet", True):
        f_str = f"{C.GRAY}OFF{C.R}"
    else:
        f_cd = STATE["faucet_next_at"] - now
        f_str = f"{C.GREEN}READY{C.R}" if f_cd <= 0 else f"{C.YELLOW}{fmt_duration(f_cd)}{C.R}"

    if not cfg.get("enable_jackpot", True):
        j_str = f"{C.GRAY}OFF{C.R}"
    else:
        j_cd = STATE["jackpot_next_at"] - now
        j_str = f"{C.GREEN}READY{C.R}" if j_cd <= 0 else f"{C.YELLOW}{fmt_duration(j_cd)}{C.R}"

    runtime = fmt_duration(time.time() - STATE["started_at"])
    auth_str = f"{C.GREEN}✓{C.R}" if STATE["logged_in"] else f"{C.RED}✗{C.R}"

    print(
        f"{C.GRAY}│{C.R} "
        f"{auth_str} auth  "
        f"💰 {bal_str}  "
        f"🚰 {f_str}  "
        f"🎲 {j_str}  "
        f"📊 F:{C.CYAN}{STATE['faucet_claimed']}{C.R}/J:{C.CYAN}{STATE['jackpot_claimed']}{C.R}  "
        f"⏱ {C.CYAN}{runtime}{C.R}"
    )

# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False
        return data
    except Exception:
        return False

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def ensure_config():
    cfg = load_config()
    if cfg is False:
        return dict(DEFAULT_CONFIG)
    if isinstance(cfg, dict):
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        for old in ("loop_delay", "waryono_apikey", "email"):
            if old in cfg and old not in DEFAULT_CONFIG:
                cfg.pop(old, None)
                changed = True
        if changed:
            save_config(cfg)
        return cfg
    return dict(DEFAULT_CONFIG)

# ==================== MENU ====================
def menu():
    banner()
    cfg = load_config() or {}

    k = cfg.get("k", "")
    u = cfg.get("u", "") or "(empty)"
    k_disp = f"{k[:8]}..." if k else "(empty)"

    print(f"{C.GRAY}Account :{C.R} {C.CYAN}{u}{C.R}")
    print(f"{C.GRAY}API Key :{C.R} {C.CYAN}{k_disp}{C.R}")
    print()
    print(f"{C.BOLD}{C.GREEN}MENU:{C.R}")
    print(f"  {C.YELLOW}[1]{C.R} Start Bot")
    print(f"  {C.YELLOW}[2]{C.R} Set API Key")
    print(f"  {C.YELLOW}[3]{C.R} Set Email")
    print(f"  {C.YELLOW}[0]{C.R} Exit")
    print()
    try:
        choice = input(f"{C.CYAN}Pilih → {C.R}").strip()
    except (EOFError, KeyboardInterrupt):
        return "0"
    return choice

def menu_config_field(label, key):
    banner()
    section(f"Set {label}")
    cfg = load_config() or dict(DEFAULT_CONFIG)
    current = cfg.get(key, "")
    if current:
        print(f"{C.GRAY}Current: {C.CYAN}{current}{C.R}")

    try:
        val = input(f"  {C.CYAN}{label}{C.R} (empty=skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if val:
        cfg[key] = val
        save_config(cfg)
        print(f"\n{C.GREEN}✔ Saved.{C.R}")
    else:
        print(f"\n{C.YELLOW}Skip.{C.R}")
    time.sleep(1.2)

def menu_loop():
    while True:
        choice = menu()
        if choice == "1":
            cfg = load_config() or {}
            missing = []
            if not cfg.get("k"): missing.append("API Key")
            if not cfg.get("u"): missing.append("Email")
            if missing:
                banner()
                print(f"{C.RED}Belum lengkap:{C.R} {', '.join(missing)}")
                time.sleep(2)
                continue
            # Map short keys ke field farming
            full = dict(cfg)
            full["waryono_apikey"] = cfg.get("k", "")
            full["email"] = cfg.get("u", "")
            return full
        elif choice == "2":
            menu_config_field("API Key", "k")
        elif choice == "3":
            menu_config_field("Email", "u")
        elif choice == "0":
            return None
        else:
            time.sleep(1)

# ==================== DELAY ====================
def human_delay(min_s, max_s, label="delay"):
    try:
        min_s = float(min_s); max_s = float(max_s)
    except (TypeError, ValueError):
        return 0
    if max_s <= 0 or max_s < min_s:
        return 0
    d = random.uniform(min_s, max_s)
    log(f"{label}: {int(d)}s", "wait")
    time.sleep(d)
    return d

def solver_jitter(cfg, label="solver pause"):
    try:
        a = float(cfg.get("solver_jitter_min", 0.8))
        b = float(cfg.get("solver_jitter_max", 2.5))
    except (TypeError, ValueError):
        return
    if b <= 0 or b < a:
        return
    d = random.uniform(a, b)
    log(f"{label}: {d:.1f}s", "wait")
    time.sleep(d)

# ==================== HTTP ====================
def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Origin": BASE,
        "Upgrade-Insecure-Requests": "1",
    })
    return s

def check_http(r, context="request"):
    if r.status_code == 429:
        return (120, f"{context}: rate limited (429)")
    if r.status_code == 403:
        return (60, f"{context}: forbidden (403)")
    if r.status_code == 401:
        return (30, f"{context}: unauthorized (401)")
    if r.status_code >= 500:
        return (60, f"{context}: server error ({r.status_code})")
    if not r.ok:
        return (30, f"{context}: HTTP {r.status_code}")
    return None

# ==================== WARYONO ====================
def solve_turnstile(cfg, action="", cdata=None):
    apikey = cfg["waryono_apikey"]
    label = action or "default"
    log(f"Solve Turnstile [{label}]", "captcha")

    solver_jitter(cfg, "pre-solve pause")

    payload = {
        "apikey": apikey,
        "methods": "turnstile",
        "domain": BASE,
        "sitekey": SITEKEY,
        "json": 1,
    }
    if action:
        payload["action"] = action
    if cdata:
        payload["cdata"] = cdata

    try:
        r = requests.post(SOLVER_IN, json=payload, timeout=60)
    except Exception as e:
        raise Exception(f"waryono submit network error: {e}")

    if not r.ok:
        raise Exception(f"waryono submit HTTP {r.status_code}")

    try:
        res = r.json()
    except Exception:
        raise Exception(f"waryono submit non-JSON: {r.text[:150]}")

    if not isinstance(res, dict):
        raise Exception(f"waryono submit unexpected: {res}")

    if res.get("status") != 1:
        raise Exception(f"waryono submit fail: {res.get('request', res)}")

    task_id = res.get("request")
    if not task_id:
        raise Exception(f"waryono no task id: {res}")

    log(f"Task ID: {task_id}", "captcha")

    max_polls = 80
    for i in range(max_polls):
        time.sleep(3)
        try:
            check_res = requests.get(
                SOLVER_RES,
                params={"apikey": apikey, "id": task_id, "action": "get", "json": 1},
                timeout=30,
            )
        except Exception:
            continue

        if not check_res.ok:
            continue

        try:
            check = check_res.json()
        except Exception:
            continue

        if not isinstance(check, dict):
            continue

        if check.get("status") == 1:
            token = check.get("request")
            if not token:
                raise Exception(f"waryono solved but empty token: {check}")
            log(f"Turnstile solved ({i*3}s)", "ok")
            solver_jitter(cfg, "post-solve pause")
            return token

        req = str(check.get("request", ""))
        if req in ("CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"):
            continue

        raise Exception(f"waryono error: {req}")

    raise Exception("turnstile timeout")

# ==================== PARSER ====================
def parse_balance(html):
    idx = html.find("Available Balance")
    if idx == -1:
        return None

    chunk = html[idx:idx + 800]

    m = re.search(
        r'<span[^>]*class="[^"]*text-(?:3|4|5)xl[^"]*"[^>]*>\s*([\d,]+(?:\.\d+)?)\s*</span>',
        chunk,
    )
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    m = re.search(r'<span[^>]*>\s*([\d,]+\.\d+)\s*</span>', chunk)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    return None

def parse_faucet_cooldown(html):
    m = re.search(r"Next Claim in[^\d]{0,15}(\d{1,2}):(\d{2})", html)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    m = re.search(r"let\s+timeLeft\s*=\s*(\d+)", html)
    if m:
        return int(m.group(1))

    if "Ready to Claim" in html:
        return 0

    if "Cooldown Active" in html:
        m2 = re.search(r"(\d{1,2}):(\d{2})", html)
        if m2:
            return int(m2.group(1)) * 60 + int(m2.group(2))
        return None

    return None

def parse_jackpot_cooldown(html):
    m = re.search(r"jpTimeLeft\s*=\s*(\d+)", html)
    if m:
        return int(m.group(1))
    if "Ready to Roll" in html:
        return 0
    return None

# ==================== LOGIN DETECTION ====================
def is_account_page(html):
    if 'name="action_auth"' in html:
        return False

    strong = ["Connected Account", "Logout / Exit", "Member since"]
    hits = sum(1 for m in strong if m in html)

    if hits >= 2:
        return True
    if hits >= 1 and "Available Balance" in html:
        return True
    if "Withdraw to FaucetPay" in html and "Total Claims" in html:
        return True

    return False

# ==================== BALANCE / COOLDOWN ====================
def check_balance(session, cfg):
    try:
        r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)

        err = check_http(r, "check_balance")
        if err:
            log(err[1], "warn")
            return False

        html = r.text

        if not is_account_page(html):
            log("Session tidak valid", "warn")
            STATE["logged_in"] = False
            return False

        STATE["logged_in"] = True

        bal = parse_balance(html)
        if bal is not None:
            old = STATE["balance"]
            STATE["balance"] = bal
            if old is None or old != bal:
                log(f"Balance: {C.GREEN}{bal:,.2f}{C.R} DAO", "bal")

        m = re.search(r"Total Claims[\s\S]{0,300}?font-mono[^>]*>\s*(\d+)", html)
        if m:
            STATE["total_claims"] = int(m.group(1))

        m = re.search(r"Total Cashout[\s\S]{0,300}?>\s*\$?([\d.]+)", html)
        if m:
            try:
                STATE["total_cashout"] = float(m.group(1))
            except ValueError:
                pass

        return True
    except Exception as e:
        log(f"Balance check error: {e}", "err")
        return False

def sync_faucet_cooldown(session, cfg):
    try:
        r = session.get(f"{BASE}/faucet", timeout=30, allow_redirects=True)
        err = check_http(r, "faucet_sync")
        if err:
            log(err[1], "warn")
            return None

        cd = parse_faucet_cooldown(r.text)
        if cd is None:
            log("Faucet cooldown tidak terdeteksi", "warn")
            return None

        STATE["faucet_next_at"] = time.time() + cd
        if cd > 0:
            log(f"Faucet cooldown: {fmt_duration(cd)}", "wait")
        else:
            log("Faucet READY", "ok")
        return cd
    except Exception as e:
        log(f"Faucet sync error: {e}", "err")
        return None

def sync_jackpot_cooldown(session, cfg):
    try:
        r = session.get(f"{BASE}/jackpot", timeout=30, allow_redirects=True)
        err = check_http(r, "jackpot_sync")
        if err:
            log(err[1], "warn")
            return None

        cd = parse_jackpot_cooldown(r.text)
        if cd is None:
            log("Jackpot cooldown tidak terdeteksi", "warn")
            return None

        STATE["jackpot_next_at"] = time.time() + cd
        if cd > 0:
            log(f"Jackpot cooldown: {fmt_duration(cd)}", "wait")
        else:
            log("Jackpot READY", "ok")
        return cd
    except Exception as e:
        log(f"Jackpot sync error: {e}", "err")
        return None

# ==================== LOGIN ====================
def verify_session(session, cfg):
    try:
        r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)
        if r.ok and is_account_page(r.text):
            STATE["logged_in"] = True
            return True
    except Exception:
        pass
    STATE["logged_in"] = False
    return False

def do_login(session, cfg):
    log("Auto login...", "auth")

    try:
        token = solve_turnstile(cfg, cfg.get("turnstile_action_login", ""), cdata=None)
    except Exception as e:
        log(f"Turnstile login error: {e}", "err")
        return False

    data = {
        "action_auth": "1",
        "email": cfg["email"],
        "cf-turnstile-response": token,
    }

    try:
        r = session.post(
            f"{BASE}/",
            data=data,
            timeout=45,
            allow_redirects=True,
            headers={
                "Referer": f"{BASE}/",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    except Exception as e:
        log(f"Login POST error: {e}", "err")
        return False

    err = check_http(r, "login")
    if err:
        log(err[1], "warn")
        return False

    if verify_session(session, cfg):
        log("Login ✓", "ok")
        return True

    if is_account_page(r.text):
        log("Login ✓", "ok")
        STATE["logged_in"] = True
        return True

    log("Login ✗", "err")
    STATE["logged_in"] = False
    return False

# ==================== FAUCET ====================
def do_faucet(session, cfg):
    log("Faucet claim...", "coin")

    try:
        token = solve_turnstile(cfg, cfg.get("turnstile_action_faucet", ""))
    except Exception as e:
        log(f"Turnstile faucet error: {e}", "err")
        return 60

    data = {
        "action_claim": "1",
        "cf-turnstile-response": token,
    }

    try:
        r = session.post(
            f"{BASE}/faucet",
            data=data,
            timeout=45,
            allow_redirects=True,
            headers={
                "Referer": f"{BASE}/faucet",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    except Exception as e:
        log(f"Faucet POST error: {e}", "err")
        return 60

    err = check_http(r, "faucet")
    if err:
        log(err[1], "warn")
        return err[0]

    html = r.text

    if not is_account_page(html) and 'name="action_auth"' in html:
        log("Faucet: session expired", "warn")
        STATE["logged_in"] = False
        return 30

    m = re.search(r"\+(\d+)\s*DAO\s*Coins\s*added", html, re.IGNORECASE)
    if m:
        coins = int(m.group(1))
        STATE["faucet_claimed"] += 1
        STATE["faucet_coins"] += coins
        log(f"Faucet ✓ +{coins} DAO", "ok")

        cd = parse_faucet_cooldown(html)
        if cd is None or cd <= 0:
            cd = int(cfg.get("faucet_cooldown_default", 300))
        STATE["faucet_next_at"] = time.time() + cd
        log(f"Faucet next: {fmt_duration(cd)}", "wait")
        return cd

    if "Cooldown Active" in html or "Next Claim in" in html:
        cd = parse_faucet_cooldown(html)
        if cd is None or cd <= 0:
            cd = int(cfg.get("faucet_cooldown_default", 300))
        STATE["faucet_next_at"] = time.time() + cd
        log(f"Faucet cooldown: {fmt_duration(cd)}", "wait")
        return cd

    m = re.search(r'class="[^"]*red[^"]*"[^>]*>([^<]{5,150})', html)
    if m:
        log(f"Faucet: {m.group(1).strip()[:150]}", "warn")
        return 60

    log("Faucet: unknown response", "warn")
    return 60

# ==================== JACKPOT ====================
def do_jackpot(session, cfg):
    log("Jackpot roll...", "dice")

    try:
        token = solve_turnstile(cfg, cfg.get("turnstile_action_jackpot", ""))
    except Exception as e:
        log(f"Turnstile jackpot error: {e}", "err")
        return 60

    files = {
        "action_spin":           (None, "1"),
        "cf-turnstile-response": (None, token),
    }

    try:
        r = session.post(
            f"{BASE}/jackpot",
            files=files,
            timeout=45,
            headers={
                "Referer": f"{BASE}/jackpot",
                "Origin": BASE,
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
    except Exception as e:
        log(f"Jackpot POST error: {e}", "err")
        return 60

    err = check_http(r, "jackpot")
    if err:
        log(err[1], "warn")
        return err[0]

    ct = r.headers.get("Content-Type", "")
    if "text/html" in ct and "application/json" not in ct:
        if 'name="action_auth"' in r.text:
            log("Jackpot: session expired", "warn")
            STATE["logged_in"] = False
            return 30
        log(f"Jackpot: unexpected HTML ({r.status_code})", "err")
        return 60

    try:
        data = r.json()
    except Exception:
        log(f"Jackpot: non-JSON ({r.status_code})", "err")
        return 60

    if not isinstance(data, dict):
        log(f"Jackpot: unexpected response", "err")
        return 60

    status = data.get("status")

    if status == "success":
        num   = data.get("num", "?")
        try:
            coins = int(data.get("coins", 0))
        except (TypeError, ValueError):
            coins = 0
        try:
            cd = int(data.get("cooldown", 600))
        except (TypeError, ValueError):
            cd = 600

        STATE["jackpot_claimed"] += 1
        STATE["jackpot_coins"] += coins
        STATE["jackpot_next_at"] = time.time() + cd
        log(f"Jackpot ✓ #{num} +{coins} DAO | next {fmt_duration(cd)}", "ok")
        return cd
    else:
        msg = data.get("msg", "?")
        try:
            cd = int(data.get("cooldown", 60))
        except (TypeError, ValueError):
            cd = 60
        if cd > 0:
            STATE["jackpot_next_at"] = time.time() + cd
        log(f"Jackpot: {msg}", "warn")
        return max(cd, 30)

# ==================== WAIT LOGIC ====================
def event_state(cfg):
    now = time.time()
    fr = cfg.get("enable_faucet", True) and STATE["faucet_next_at"] <= now
    jr = cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] <= now
    return {"faucet_ready": fr, "jackpot_ready": jr, "any_ready": fr or jr}

def compute_next_wake(cfg):
    now = time.time()

    if cfg.get("enable_faucet", True) and STATE["faucet_next_at"] <= now:
        return now + 1
    if cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] <= now:
        return now + 1

    candidates = []
    if cfg.get("enable_faucet", True) and STATE["faucet_next_at"] > now:
        candidates.append(STATE["faucet_next_at"])
    if cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] > now:
        candidates.append(STATE["jackpot_next_at"])

    if candidates:
        return min(candidates) + 1

    return now + LOOP_DELAY

def wait_until(target_ts):
    now = time.time()
    delta = int(target_ts - now)

    if delta <= 0:
        return

    if abs(target_ts - STATE["faucet_next_at"]) <= 2:
        target_label = "faucet ready"
    elif abs(target_ts - STATE["jackpot_next_at"]) <= 2:
        target_label = "jackpot ready"
    else:
        target_label = "idle poll"

    print()
    status_bar(current_cfg)
    print(f"{C.GRAY}[{now_str()}]{C.R} {C.GRAY}💤{C.R}  Tidur {fmt_duration(delta)} → {C.CYAN}{target_label}{C.R}  "
          f"(faucet {fmt_duration(max(0, STATE['faucet_next_at'] - now))}, "
          f"jackpot {fmt_duration(max(0, STATE['jackpot_next_at'] - now))})")
    print()

    while True:
        left = target_ts - time.time()
        if left <= 0:
            break
        chunk = min(left, 5.0)
        time.sleep(chunk)

# ==================== SUMMARY ====================
def print_summary():
    runtime = time.time() - STATE["started_at"]
    print()
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}  📊  RINGKASAN SESSION{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"  Runtime           : {C.CYAN}{fmt_duration(runtime)}{C.R}")
    print(f"  Balance akhir     : {C.GREEN}{STATE['balance'] if STATE['balance'] is not None else '?'}{C.R} DAO")
    print(f"  Total claims      : {C.CYAN}{STATE['total_claims']}{C.R}")
    print(f"  Total cashout     : {C.CYAN}${STATE['total_cashout']:.6f}{C.R}")
    print(f"  Faucet claims     : {C.CYAN}{STATE['faucet_claimed']}{C.R} (+{STATE['faucet_coins']} DAO)")
    print(f"  Jackpot claims    : {C.CYAN}{STATE['jackpot_claimed']}{C.R} (+{STATE['jackpot_coins']} DAO)")
    print(f"  Re-login count    : {C.CYAN}{STATE['relogin_count']}{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print()

# ==================== BOT ====================
def run_bot(cfg):
    global current_cfg
    current_cfg = cfg

    banner()
    log("Bot start", "ok")
    log(f"Email: {cfg['email']}", "info")

    session = make_session()
    session_check_every = int(cfg.get("session_check_every", 10))
    hd_min = float(cfg.get("human_delay_min", 20))
    hd_max = float(cfg.get("human_delay_max", 60))

    STATE["started_at"] = time.time()

    if cfg.get("enable_auto_login", True):
        ok = False
        for attempt in range(3):
            try:
                if do_login(session, cfg):
                    ok = True
                    break
            except Exception as e:
                log(f"Login err ({attempt+1}/3): {e}", "err")
                time.sleep(5)
        if not ok:
            log("Login gagal 3x, kembali ke menu", "err")
            time.sleep(2)
            return
    else:
        log("Verify session...", "warn")
        if not verify_session(session, cfg):
            log("Session tidak valid. Kembali ke menu.", "err")
            time.sleep(2)
            return
        log("Session valid ✓", "ok")

    section("Initial Sync")
    if cfg.get("enable_balance_check", True):
        check_balance(session, cfg)
    if cfg.get("enable_faucet", True):
        sync_faucet_cooldown(session, cfg)
    if cfg.get("enable_jackpot", True):
        sync_jackpot_cooldown(session, cfg)

    cycle = 0
    idle_count = 0

    while True:
        try:
            ev = event_state(cfg)

            if not ev["any_ready"]:
                idle_count += 1
                wake_at = compute_next_wake(cfg)

                if idle_count == 1 or idle_count % 5 == 0:
                    section(f"Idle #{idle_count} — nunggu event")

                wait_until(wake_at)
                continue

            idle_count = 0
            cycle += 1
            print()
            section(f"Cycle #{cycle}")
            status_bar(cfg)

            if session_check_every > 0 and cycle % session_check_every == 0:
                if not verify_session(session, cfg):
                    log("Session expired, re-login...", "warn")
                    STATE["relogin_count"] += 1
                    if cfg.get("enable_auto_login", True):
                        if do_login(session, cfg):
                            log("Re-login ✓", "ok")
                        else:
                            log("Re-login gagal, skip 60s", "err")
                            time.sleep(60)
                            continue
                    else:
                        log("Auto login off, kembali ke menu", "err")
                        return

            if not STATE["logged_in"]:
                log("Skip klaim (session invalid)", "warn")
                time.sleep(30)
                continue

            if ev["faucet_ready"]:
                try:
                    do_faucet(session, cfg)
                except Exception as e:
                    log(f"Faucet err: {e}", "err")
                    STATE["faucet_next_at"] = time.time() + 60

            ev = event_state(cfg)
            if ev["jackpot_ready"]:
                try:
                    do_jackpot(session, cfg)
                except Exception as e:
                    log(f"Jackpot err: {e}", "err")
                    STATE["jackpot_next_at"] = time.time() + 60

            if cfg.get("enable_balance_check", True):
                check_balance(session, cfg)

            wake_at = compute_next_wake(cfg)
            spare = wake_at - time.time()

            if spare > 5:
                capped_max = min(hd_max, max(2.0, spare - 3.0))
                capped_min = min(hd_min, capped_max)
                if capped_max >= 2.0 and capped_min <= capped_max:
                    human_delay(capped_min, capped_max, "post-event pause")

            ev_after = event_state(cfg)
            if ev_after["any_ready"]:
                log("Event baru ready, lanjut cycle berikutnya", "info")
                continue

            wake_at = compute_next_wake(cfg)
            wait_until(wake_at)

        except KeyboardInterrupt:
            print()
            log("Dihentikan user.", "warn")
            print_summary()
            time.sleep(1)
            return
        except Exception as e:
            log(f"Loop error: {e}", "err")
            time.sleep(15)

# ==================== MAIN ====================
def main():
    while True:
        cfg = menu_loop()
        if cfg is None:
            clear()
            print(f"{C.YELLOW}Bye.{C.R}")
            return
        try:
            run_bot(cfg)
        except KeyboardInterrupt:
            print()
            print(f"{C.YELLOW}Kembali ke menu...{C.R}")
            time.sleep(1)

if __name__ == "__main__":
    sys.tracebacklimit = 0
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Stopped.{C.R}")
