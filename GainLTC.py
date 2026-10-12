#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto bot"""

import json
import os
import sys
import time
import random
import threading
import requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# ==================== CONFIG ====================
SCRIPT_DIR  = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "gainltc_config.json"

BASE       = "https://gainltc.com"
SOLVER_IN  = "https://api.waryono.my.id/in.php"
SOLVER_RES = "https://api.waryono.my.id/res.php"

DEFAULT_UA = ("Mozilla/5.0 (Linux; Android 10; K) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/127.0.0.0 Mobile Safari/537.36")

DEFAULT_CONFIG = {
    "u": "",
    "p": "",
    "k": "",
    "s": "05e4f926-1cc6-4438-8018-3a388392ea26",
    "ua": "",       # User-Agent (kosong = pakai DEFAULT_UA)
    "d": True,
}

MAX_LOGIN_ATTEMPTS  = 2
RATE_LIMIT_DEFAULT  = 90
RATE_LIMIT_MAX      = 600
BACKOFF_BASE        = 5

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
    "started_at": time.time(),
    "balance": None, "total_earned": None,
    "username": None, "user_id": None,
    "total_claims": 0, "total_reward": 0,
    "next_claim_at": 0.0, "csrf_token": None,
    "logged_in": False,
    "rate_limit_until": 0.0,
}

# ==================== UTILS ====================
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def banner():
    clear()
    print(f"""{C.CYAN}{C.BOLD}
   ╔══════════════════════════════════════════════════════════════╗
   ║           💰  G A I N L T C . C O M  💰                      ║
   ╚══════════════════════════════════════════════════════════════╝
""")


def log(msg, level="info"):
    icons = {
        "info": f"{C.CYAN}ℹ{C.R}", "ok": f"{C.GREEN}✔{C.R}",
        "warn": f"{C.YELLOW}⚠{C.R}", "err": f"{C.RED}✖{C.R}",
        "coin": f"{C.YELLOW}🪙{C.R}", "auth": f"{C.BLUE}🔐{C.R}",
        "captcha": f"{C.BLUE}🛡 {C.R}", "wait": f"{C.GRAY}⏳{C.R}",
        "bal": f"{C.GREEN}💰{C.R}", "dbg": f"{C.MAGENTA}🐛{C.R}",
        "slider": f"{C.MAGENTA}🎯{C.R}", "sleep": f"{C.GRAY}💤{C.R}",
        "limit": f"{C.RED}🚫{C.R}",
    }
    icon = icons.get(level, icons["info"])
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    print(f"{C.GRAY}[{now_str()}]{C.R} {icon}  {msg}")


def section(title):
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    print(f"\n{C.BOLD}{C.GREEN}▸ {title.upper()}{C.R}")
    print(f"{C.GRAY}{'─' * 60}{C.R}")


def spinner_line(text):
    global _spin_idx
    with _spin_lock:
        frame = SPINNER[_spin_idx % len(SPINNER)]
        _spin_idx += 1
    sys.stdout.write(f"\r\033[K{C.CYAN}{frame}{C.R}  {text}")
    sys.stdout.flush()


def clear_line():
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def countdown_sleep(seconds, label="wait"):
    total = int(seconds)
    if total <= 0:
        return
    print()
    last_sec = -1
    end = time.time() + total
    while True:
        left = int(end - time.time())
        if left <= 0:
            break
        if left != last_sec:
            sys.stdout.write(f"\r\033[K{C.GRAY}[{now_str()}]{C.R} {C.GRAY}💤{C.R}  {label}: {C.YELLOW}{fmt_duration(left)}{C.R}")
            sys.stdout.flush()
            last_sec = left
        time.sleep(0.3)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def safe_input(prompt=""):
    try:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            return ""
        return line.rstrip("\r\n").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def ensure_config():
    cfg = load_config()
    if cfg and isinstance(cfg, dict):
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        if changed:
            save_config(cfg)
        return cfg
    return dict(DEFAULT_CONFIG)


def get_user_agent(cfg):
    """Ambil UA dari config, fallback ke default."""
    ua = (cfg or {}).get("ua", "").strip()
    return ua if ua else DEFAULT_UA


# ==================== MENU ====================
def menu():
    banner()
    cfg = load_config() or {}
    u = cfg.get("u", "") or "(empty)"
    k = cfg.get("k", "")
    k_disp = f"{k[:8]}..." if k else "(empty)"
    ua = cfg.get("ua", "") or "(default)"

    # Preview UA (potong kalau panjang)
    ua_disp = ua if len(ua) <= 50 else ua[:47] + "..."

    print(f"{C.GRAY}Account  :{C.R} {C.CYAN}{u}{C.R}")
    print(f"{C.GRAY}API Key  :{C.R} {C.CYAN}{k_disp}{C.R}")
    print(f"{C.GRAY}User-Agent:{C.R} {C.CYAN}{ua_disp}{C.R}")
    print()
    print(f"{C.BOLD}{C.GREEN}MENU:{C.R}")
    print(f"  {C.YELLOW}[1]{C.R} Start")
    print(f"  {C.YELLOW}[2]{C.R} Set API Key")
    print(f"  {C.YELLOW}[3]{C.R} Set Email")
    print(f"  {C.YELLOW}[4]{C.R} Set Password")
    print(f"  {C.YELLOW}[5]{C.R} Set User-Agent")
    print(f"  {C.YELLOW}[0]{C.R} Exit")
    print()
    choice = safe_input(f"{C.CYAN}Pilih → {C.R}")
    if not choice:
        return "0"
    return choice


def menu_config_field(label, key):
    banner()
    section(f"Set {label}")
    cfg = load_config() or dict(DEFAULT_CONFIG)
    cur = cfg.get(key, "")
    if cur:
        if key == "p":
            preview = "*" * len(cur)
        else:
            preview = cur
        print(f"{C.GRAY}Current: {C.CYAN}{preview}{C.R}")
    print()

    if key == "ua":
        print(f"{C.GRAY}Kosongin buat pakai default:{C.R}")
        print(f"{C.DIM}{DEFAULT_UA}{C.R}")
        print()

    val = safe_input(f"  {C.CYAN}{label}{C.R} (empty=skip): ")

    # Khusus UA: kalau user ketik "-" → reset ke default (kosongin)
    if key == "ua" and val == "-":
        cfg[key] = ""
        save_config(cfg)
        print(f"\n{C.GREEN}✔ User-Agent reset ke default.{C.R}")
    elif val:
        cfg[key] = val
        save_config(cfg)
        print(f"\n{C.GREEN}✔ {label} saved.{C.R}")
    else:
        print(f"\n{C.YELLOW}Skip.{C.R}")
    time.sleep(1.2)


def menu_loop():
    while True:
        choice = menu()
        if choice == "1":
            cfg = load_config() or {}
            missing = []
            if not cfg.get("u"): missing.append("Email")
            if not cfg.get("p"): missing.append("Password")
            if not cfg.get("k"): missing.append("API Key")
            if missing:
                banner()
                print(f"{C.RED}Belum lengkap:{C.R} {', '.join(missing)}")
                time.sleep(2)
                continue
            return {
                "email": cfg["u"],
                "password": cfg["p"],
                "waryono_apikey": cfg["k"],
                "hcaptcha_sitekey": cfg.get("s", DEFAULT_CONFIG["s"]),
                "user_agent": get_user_agent(cfg),
                "debug_challenge": cfg.get("d", True),
            }
        elif choice == "2":
            menu_config_field("API Key", "k")
        elif choice == "3":
            menu_config_field("Email", "u")
        elif choice == "4":
            menu_config_field("Password", "p")
        elif choice == "5":
            menu_config_field("User-Agent", "ua")
        elif choice == "0":
            return None
        else:
            time.sleep(1)


# ==================== SESSION ====================
def make_session(user_agent=None):
    ua = user_agent or DEFAULT_UA
    s = requests.Session()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Origin": BASE,
        "Referer": f"{BASE}/",
    })
    return s


def refresh_csrf(session):
    try:
        r = session.get(f"{BASE}/api/csrf-token", timeout=30)
        if not r.ok:
            return None
        data = r.json()
        token = data.get("csrfToken") or data.get("token")
        if not token:
            token = session.cookies.get("csrf_token")
        if token:
            token = unquote(token)
            STATE["csrf_token"] = token
            return token
    except Exception:
        pass
    return None


def csrf_headers(token=None):
    if not token:
        token = STATE["csrf_token"]
    return {"x-csrf-token": token} if token else {}


# ==================== BLOCK / RATE LIMIT ====================
def parse_block_info(resp, context=""):
    if resp is None:
        return (False, 0, "")

    if resp.status_code == 429:
        wait = _extract_wait_from_response(resp, default=RATE_LIMIT_DEFAULT)
        return (True, wait, "HTTP 429 (too many requests)")

    if resp.status_code == 503:
        wait = _extract_wait_from_response(resp, default=60)
        return (True, wait, "HTTP 503 (service unavailable)")

    try:
        rj = resp.json()
    except Exception:
        rj = None

    if isinstance(rj, dict):
        blocked = bool(rj.get("blocked"))
        err_msg = str(rj.get("error", "")).lower()
        if "too many" in err_msg or "try again later" in err_msg or "rate" in err_msg:
            blocked = True
        if blocked:
            wait = _extract_wait_from_json(rj, default=RATE_LIMIT_DEFAULT)
            return (True, wait, rj.get("error", "rate limited"))

    return (False, 0, "")


def _extract_wait_from_response(resp, default=RATE_LIMIT_DEFAULT):
    ra = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
    if ra:
        try:
            return min(int(float(ra)), RATE_LIMIT_MAX)
        except (TypeError, ValueError):
            pass
    try:
        rj = resp.json()
        if isinstance(rj, dict):
            return _extract_wait_from_json(rj, default=default)
    except Exception:
        pass
    return default


def _extract_wait_from_json(rj, default=RATE_LIMIT_DEFAULT):
    if "retryAfterSeconds" in rj:
        try:
            return min(int(rj["retryAfterSeconds"]), RATE_LIMIT_MAX)
        except (TypeError, ValueError):
            pass
    if "blockedUntil" in rj:
        try:
            ts_str = str(rj["blockedUntil"]).replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            now = datetime.now(timezone.utc)
            wait = max(0, int((dt - now).total_seconds()))
            if wait > 0:
                return min(wait, RATE_LIMIT_MAX)
        except Exception:
            pass
    return default


def set_rate_limit(wait_seconds, reason=""):
    until = time.time() + wait_seconds
    if until > STATE.get("rate_limit_until", 0):
        STATE["rate_limit_until"] = until


def check_rate_limit():
    left = STATE.get("rate_limit_until", 0) - time.time()
    return max(0, int(left))


# ==================== CAPTCHA SOLVERS ====================
def solve_emoji_slider(challenge):
    ghosts = challenge.get("ghosts") or []
    active_idx = int(challenge.get("activeGhostIndex", 0))
    tolerance = int(challenge.get("tolerance", 12))
    active_emoji = challenge.get("activeEmoji", "?")
    if not ghosts or active_idx >= len(ghosts):
        raise Exception("emoji-slider: invalid")
    target = int(ghosts[active_idx].get("position", 0))
    jitter = max(1, tolerance // 3)
    answer = target + random.randint(-jitter, jitter)
    answer = max(0, min(100, answer))
    log(f"slider: {active_emoji} pos~{target} → {answer}", "slider")
    return [str(answer)]


def solve_count(challenge):
    grid = challenge.get("grid") or []
    winner = challenge.get("winner")
    if not grid or not winner:
        raise Exception("count: invalid")
    indices = [i for i, e in enumerate(grid) if e == winner]
    if not indices:
        raise Exception("count: winner tidak ada di grid")
    log(f"count: {winner} freq={len(indices)} idx={indices}", "slider")
    return [winner]


def solve_sequence(challenge):
    target = challenge.get("target") or []
    grid = challenge.get("grid") or []
    if not target or not grid:
        raise Exception("sequence: invalid")
    for t in target:
        if t not in grid:
            raise Exception(f"sequence: '{t}' tidak ada di grid")
    log(f"sequence: {target}", "slider")
    return list(target)


def solve_tap_target(challenge):
    target = challenge.get("target")
    taps = int(challenge.get("tapsRequired", 1))
    if not target:
        raise Exception("tap-target: invalid")
    answer = [target] * taps
    log(f"tap-target: {target} x{taps}", "slider")
    return answer


def solve_connect_pairs(challenge):
    emojis = challenge.get("emojis") or []
    left = challenge.get("leftOrder") or []
    right = challenge.get("rightOrder") or []
    if not emojis or not left or not right:
        raise Exception("connect-pairs: invalid")
    answer = []
    for e in emojis:
        try:
            l_idx = left.index(e)
            r_idx = right.index(e)
            answer.append(f"{l_idx}-{r_idx}")
        except ValueError:
            raise Exception(f"connect-pairs: '{e}' not found")
    log(f"connect-pairs: {answer}", "slider")
    return answer


def solve_drag_order(challenge):
    items = challenge.get("items") or challenge.get("targets") or []
    order = challenge.get("correctOrder") or challenge.get("order") or challenge.get("sequence")
    if order:
        return [str(x) for x in order]
    if items:
        sorted_items = sorted(items, key=lambda x: x.get("order", x.get("index", 0)))
        answer = [str(it.get("id")) for it in sorted_items if it.get("id") is not None]
        if answer:
            return answer
    raise Exception("drag-order: invalid")


def solve_challenge(challenge):
    ctype = (challenge.get("type") or "").lower().strip()
    log(f"Challenge: {ctype}", "captcha")
    solvers = {
        "emoji-slider": solve_emoji_slider,
        "count": solve_count,
        "sequence": solve_sequence,
        "tap-target": solve_tap_target,
        "connect-pairs": solve_connect_pairs,
        "drag-order": solve_drag_order,
    }
    fn = solvers.get(ctype)
    if not fn:
        raise Exception(f"Unknown: {ctype}")
    return fn(challenge)


# ==================== LOGIN ====================
class RateLimited(Exception):
    def __init__(self, wait_seconds, reason=""):
        super().__init__(f"Rate limited: {wait_seconds}s ({reason})")
        self.wait_seconds = wait_seconds
        self.reason = reason


def do_login(session, cfg):
    log("Login flow started", "auth")

    rl = check_rate_limit()
    if rl > 0:
        raise RateLimited(rl, "global rate limit active")

    token = refresh_csrf(session)
    if not token:
        log("CSRF fail", "err")
        return False
    log(f"CSRF OK", "auth")

    try:
        r = session.post(f"{BASE}/api/captcha/generate",
                         headers=dict(csrf_headers(token)), timeout=30)
    except Exception as e:
        log(f"Captcha gen error: {e}", "err")
        return False

    if not r.ok:
        blocked, wait, reason = parse_block_info(r, "captcha-gen")
        if blocked:
            set_rate_limit(wait, reason)
            raise RateLimited(wait, reason)
        log(f"Captcha gen HTTP {r.status_code}", "err")
        return False

    try:
        cap = r.json()
    except Exception:
        log("Captcha response non-JSON", "err")
        return False

    cap_token = cap.get("token")
    challenge = cap.get("challenge") or {}
    if not cap_token or not challenge:
        log("Captcha invalid", "err")
        return False

    if cfg.get("debug_challenge", False):
        log(f"keys: {list(challenge.keys())}", "dbg")

    try:
        answer = solve_challenge(challenge)
    except Exception as e:
        log(f"Solve error: {e}", "err")
        log(f"dump: {json.dumps(challenge, ensure_ascii=False)[:400]}", "dbg")
        return False

    log(f"Answer: {json.dumps(answer, ensure_ascii=False)[:200]}", "dbg")

    try:
        r = session.post(f"{BASE}/api/captcha/verify",
                         json={"token": cap_token, "answer": answer, "type": challenge.get("type")},
                         headers={**csrf_headers(token), "Content-Type": "application/json"},
                         timeout=30)
    except Exception as e:
        log(f"Verify error: {e}", "err")
        return False

    if not r.ok:
        blocked, wait, reason = parse_block_info(r, "captcha-verify")
        if blocked:
            set_rate_limit(wait, reason)
            raise RateLimited(wait, reason)
        try:
            body = r.json()
            log(f"Verify fail: {body}", "err")
        except Exception:
            log(f"Verify HTTP {r.status_code}: {r.text[:150]}", "err")
        return False

    try:
        vres = r.json()
    except Exception:
        log("Verify non-JSON", "err")
        return False

    blocked, wait, reason = parse_block_info(r, "captcha-verify-body")
    if blocked:
        set_rate_limit(wait, reason)
        raise RateLimited(wait, reason)

    verified_token = vres.get("verifiedToken")
    if not verified_token:
        log(f"Verify fail: {vres}", "err")
        return False
    log("Verified ✓", "captcha")

    try:
        r = session.post(f"{BASE}/api/auth/login",
                         json={"email": cfg["email"], "password": cfg["password"],
                               "captchaToken": verified_token, "rememberMe": True},
                         headers={**csrf_headers(token), "Content-Type": "application/json"},
                         timeout=30)
    except Exception as e:
        log(f"Login error: {e}", "err")
        return False

    if not r.ok:
        blocked, wait, reason = parse_block_info(r, "login")
        if blocked:
            set_rate_limit(wait, reason)
            raise RateLimited(wait, reason)
        log(f"Login HTTP {r.status_code}", "err")
        return False

    try:
        result = r.json()
    except Exception:
        log("Login non-JSON", "err")
        return False

    blocked, wait, reason = parse_block_info(r, "login-body")
    if blocked:
        set_rate_limit(wait, reason)
        raise RateLimited(wait, reason)

    if not result.get("success"):
        log(f"Login failed: {result}", "err")
        return False

    user = result.get("user") or {}
    STATE["user_id"] = user.get("id")
    STATE["username"] = user.get("username")
    STATE["balance"] = user.get("balance")
    STATE["total_earned"] = user.get("totalEarned")
    STATE["logged_in"] = True
    STATE["rate_limit_until"] = 0

    log(f"Login ✓ {STATE['username']}", "ok")
    log(f"Balance: {STATE['balance']}", "bal")
    return True


def verify_session(session):
    try:
        r = session.get(f"{BASE}/api/auth/me", headers=csrf_headers(), timeout=30)
        if r.status_code == 401:
            STATE["logged_in"] = False
            return False
        if not r.ok:
            return False
        data = r.json()
        if data.get("success") and data.get("user"):
            u = data["user"]
            STATE["balance"] = u.get("balance")
            STATE["total_earned"] = u.get("totalEarned")
            STATE["logged_in"] = True
            return True
    except Exception:
        pass
    STATE["logged_in"] = False
    return False


def login_with_retry(session, cfg, max_attempts=MAX_LOGIN_ATTEMPTS):
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            if do_login(session, cfg):
                return True
            if attempt < max_attempts:
                backoff = BACKOFF_BASE * attempt
                log(f"Retry dalam {backoff}s...", "wait")
                time.sleep(backoff)
        except RateLimited as e:
            wait = e.wait_seconds
            log(f"🚫 Rate limit: tunggu {fmt_duration(wait)} ({e.reason})", "limit")
            countdown_sleep(wait + 3, "Rate limit")
            log("Rate limit selesai, coba login lagi...", "info")
            try:
                if do_login(session, cfg):
                    return True
            except RateLimited as e2:
                log(f"Masih rate limited ({e2.wait_seconds}s lagi)", "limit")
                return None
            except Exception as e2:
                log(f"Login err: {e2}", "err")
                return False
            return False
        except Exception as e:
            log(f"Login err ({attempt}/{max_attempts}): {e}", "err")
            if attempt < max_attempts:
                backoff = BACKOFF_BASE * attempt
                log(f"Retry dalam {backoff}s...", "wait")
                time.sleep(backoff)
    return False


# ==================== HCAPTCHA ====================
def solve_hcaptcha(cfg, sitekey):
    apikey = cfg["waryono_apikey"]
    payload = {"apikey": apikey, "methods": "hcaptcha", "domain": BASE,
               "sitekey": sitekey, "json": 1}
    try:
        r = requests.post(SOLVER_IN, json=payload, timeout=60)
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        res = r.json()
    except Exception as e:
        raise Exception(f"submit: {e}")

    if res.get("status") != 1:
        raise Exception(f"fail: {res.get('request', res)}")

    task_id = res.get("request")
    log(f"hCaptcha task: {task_id}", "captcha")

    for i in range(100):
        time.sleep(3)
        try:
            check = requests.get(SOLVER_RES, params={"apikey": apikey, "id": task_id,
                                                     "action": "get", "json": 1},
                                 timeout=30).json()
        except Exception:
            continue

        if check.get("status") == 1:
            token = check.get("request")
            if not token:
                raise Exception("empty token")
            clear_line()
            log(f"hCaptcha ✓ ({i*3}s)", "ok")
            return token

        req = str(check.get("request", ""))
        if req in ("CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"):
            spinner_line(f"polling... ({i*3}s)")
            continue
        clear_line()
        raise Exception(f"error: {req}")

    clear_line()
    raise Exception("timeout")


# ==================== FAUCET ====================
def get_faucet_status(session):
    r = session.get(f"{BASE}/api/faucet/status", headers=csrf_headers(), timeout=30)
    if not r.ok:
        raise Exception(f"HTTP {r.status_code}")
    return r.json()


def do_faucet_claim(session, cfg):
    log("Faucet claim...", "coin")
    status = get_faucet_status(session)
    if not status.get("canClaim"):
        next_at = status.get("nextClaimAt")
        if next_at:
            STATE["next_claim_at"] = int(next_at) / 1000.0
        raise Exception("FAUCET_COOLDOWN")

    sitekey = (status.get("captcha") or {}).get("siteKey") or cfg["hcaptcha_sitekey"]
    token = solve_hcaptcha(cfg, sitekey)

    r = session.post(f"{BASE}/api/faucet/claim", json={"captchaToken": token},
                     headers={**csrf_headers(), "Content-Type": "application/json"},
                     timeout=60)
    if not r.ok:
        raise Exception(f"HTTP {r.status_code}: {r.text[:150]}")

    data = r.json()
    if not data.get("success", True) and "reward" not in data:
        err = data.get("error") or data.get("message") or json.dumps(data)[:150]
        raise Exception(f"fail: {err}")

    reward = int(data.get("reward", 0))
    roll = data.get("roll", "?")
    new_balance = data.get("newBalance")
    next_at = data.get("nextClaimAt")

    STATE["total_claims"] += 1
    STATE["total_reward"] += reward
    if new_balance is not None:
        STATE["balance"] = new_balance
    if next_at:
        STATE["next_claim_at"] = int(next_at) / 1000.0

    log(f"Claim ✓ #{roll} +{reward} | bal: {new_balance}", "coin")
    return data


# ==================== DASHBOARD ====================
def dashboard_line():
    now = time.time()
    cd = STATE["next_claim_at"] - now
    cd_str = f"{C.GREEN}READY{C.R}" if cd <= 0 else f"{C.YELLOW}{fmt_duration(cd)}{C.R}"
    bal = STATE["balance"] if STATE["balance"] is not None else "---"
    runtime = fmt_duration(now - STATE["started_at"])
    return (f"{C.GRAY}[{now_str()}]{C.R} "
            f"👤{C.CYAN}{STATE['username'] or '?'}{C.R} "
            f"💰{C.GREEN}{bal}{C.R} "
            f"⏰{cd_str} "
            f"📊{STATE['total_claims']} "
            f"💵{C.YELLOW}{STATE['total_reward']}{C.R} "
            f"⏱{C.CYAN}{runtime}{C.R}")


def wait_with_dashboard(target_ts):
    print()
    last_sec = -1
    try:
        while True:
            left = target_ts - time.time()
            if left <= 0:
                break
            cur_sec = int(left)
            if cur_sec != last_sec:
                line = f"{dashboard_line()} {C.GRAY}💤{fmt_duration(left)}{C.R}"
                sys.stdout.write(f"\r\033[K{line}")
                sys.stdout.flush()
                last_sec = cur_sec
            time.sleep(min(left, 0.2))
    finally:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# ==================== FARMING ====================
def start_farming(cfg):
    banner()
    log("Bot started", "ok")

    ua = cfg.get("user_agent") or DEFAULT_UA
    if ua != DEFAULT_UA:
        log(f"UA: {ua[:60]}{'...' if len(ua) > 60 else ''}", "info")

    session = make_session(user_agent=ua)

    section("Login")
    res = login_with_retry(session, cfg)
    if res is None:
        log("Masih rate limited. Balik ke menu.", "err")
        time.sleep(3)
        return
    if not res:
        log("Login failed, balik ke menu", "err")
        time.sleep(2)
        return

    section("Sync")
    try:
        status = get_faucet_status(session)
        if status.get("canClaim"):
            STATE["next_claim_at"] = time.time()
            log("Faucet READY", "ok")
        else:
            nxt = status.get("nextClaimAt")
            if nxt:
                STATE["next_claim_at"] = int(nxt) / 1000.0
                cd = STATE["next_claim_at"] - time.time()
                log(f"Cooldown: {fmt_duration(cd)}", "wait")
    except Exception as e:
        log(f"Sync error: {e}", "warn")

    cycle = 0
    while True:
        cycle += 1
        try:
            if not verify_session(session):
                log("Session expired, re-login...", "warn")
                res = login_with_retry(session, cfg)
                if res is None:
                    log("Masih rate limited. Balik ke menu.", "err")
                    time.sleep(3)
                    return
                if not res:
                    log("Re-login failed, balik ke menu", "err")
                    time.sleep(2)
                    return

            now = time.time()
            cd = STATE["next_claim_at"] - now
            if cd > 0:
                wait_with_dashboard(STATE["next_claim_at"])
                continue

            section(f"Cycle #{cycle}")
            print(dashboard_line())
            print()

            try:
                do_faucet_claim(session, cfg)
            except Exception as e:
                err = str(e)
                if "FAUCET_COOLDOWN" in err:
                    log("Still cooldown", "wait")
                    continue
                log(f"Claim error: {err}", "err")
                refresh_csrf(session)
                time.sleep(5)
                continue

            verify_session(session)
            if STATE["next_claim_at"] <= time.time():
                STATE["next_claim_at"] = time.time() + 300

        except KeyboardInterrupt:
            print()
            log("Stopped — back to menu.", "warn")
            time.sleep(1)
            return
        except Exception as e:
            log(f"Loop error: {e} (retry 10s)", "err")
            time.sleep(10)


# ==================== MAIN ====================
def main():
    while True:
        cfg = menu_loop()
        if cfg is None:
            clear()
            print(f"{C.YELLOW}Bye.{C.R}")
            return
        try:
            start_farming(cfg)
        except KeyboardInterrupt:
            print()
            print(f"{C.YELLOW}Back to menu...{C.R}")
            time.sleep(1)


if __name__ == "__main__":
    sys.tracebacklimit = 0
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Stopped.{C.R}")
