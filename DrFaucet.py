#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DrFaucet.site Auto Claim Bot
=============================

Features:
- Live countdown (real-time timer) saat menunggu claim berikutnya
- Auto-check cookie (startup + setiap 5 cycle + sebelum claim)
- Auto-detect hCaptcha sitekey (fallback ke hardcoded)
- Retry 3x on UNSOLVABLE captcha
- Stop on fatal error, tidak spam retry
- Portable: jalan di server manapun dengan Python 3.7+

Author: MoneyMaker_w
Telegram: https://t.me/+RInZ35ML2GhjM2I1
"""

import json
import os
import sys
import time
import re
import threading
from datetime import datetime
from pathlib import Path

# ==================== DEPENDENCY CHECK ====================
try:
    import requests
except ImportError:
    print("ERROR: library 'requests' belum terinstall")
    print("Jalankan: pip install requests")
    sys.exit(1)

# ==================== KONSTANTA ====================
FALLBACK_SITEKEY = "7f84a1c2-3d72-48fa-93fa-69363330aed8"
BASE             = "https://drfaucet.site"
SOLVER_IN        = "https://api.waryono.my.id/in.php"
SOLVER_RES       = "https://api.waryono.my.id/res.php"
MAX_CAPTCHA_RETRY = 3
SESSION_RECHECK_EVERY = 5

# ==================== PATH / CONFIG ====================
BASE_DIR    = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "drfaucet_config.json"

DEFAULT_CONFIG = {
    "waryono_apikey": "",
    "cookie": "",
    "hcaptcha_sitekey": "",
}

# ==================== COLORS ====================
class C:
    R = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_spin_idx = 0
_spin_lock = threading.Lock()

# ==================== STATE ====================
STATE = {
    "started_at": time.time(),
    "total_claims": 0,
    "total_reward": 0.0,
    "balance": None,
    "currency": "DOGE",
    "username": None,
    "provider": None,
    "next_claim_at": 0.0,
    "sitekey": None,
    "sitekey_source": None,
    "session_valid": False,
}

LINE_WIDTH = 56


# ==================== UI HELPERS ====================
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
   ║           💧  D R F A U C E T . S I T E  💧                   ║
   ║              AUTO CLAIM  ·  hCaptcha Solver                  ║
   ╚══════════════════════════════════════════════════════════════╝
{C.MAGENTA}                       By MoneyMaker_w{C.R}
{C.CYAN}          Telegram: https://t.me/+RInZ35ML2GhjM2I1{C.R}
{C.GRAY}   ────────────────────────────────────────────────────────{C.R}
""")


def section(title):
    bar = "─" * LINE_WIDTH
    print(f"\n{C.BOLD}{C.GREEN}▸ {title.upper()}{C.R} {C.GRAY}{bar}{C.R}")


def log(msg, level="info"):
    icons = {
        "info":    f"{C.CYAN}ℹ{C.R}",
        "ok":      f"{C.GREEN}✔{C.R}",
        "warn":    f"{C.YELLOW}⚠{C.R}",
        "err":     f"{C.RED}✖{C.R}",
        "coin":    f"{C.YELLOW}🪙{C.R}",
        "captcha": f"{C.BLUE}🛡 {C.R}",
        "wait":    f"{C.GRAY}⏳{C.R}",
        "bal":     f"{C.GREEN}💰{C.R}",
        "dbg":     f"{C.MAGENTA}🐛{C.R}",
        "retry":   f"{C.YELLOW}↻{C.R}",
    }
    icon = icons.get(level, icons["info"])
    print(f"{C.GRAY}[{now_str()}]{C.R} {icon}  {msg}")


def spinner_line(text):
    global _spin_idx
    with _spin_lock:
        frame = SPINNER[_spin_idx % len(SPINNER)]
        _spin_idx += 1
    sys.stdout.write(f"\r{C.CYAN}{frame}{C.R}  {text}   ")
    sys.stdout.flush()


def clear_line():
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()


def info_card():
    runtime = fmt_duration(time.time() - STATE["started_at"])
    bal = STATE["balance"]
    bal_str = f"{bal:.8f} {STATE['currency']}" if bal is not None else "---"

    cd = STATE["next_claim_at"] - time.time()
    cd_str = "READY" if cd <= 0 else fmt_duration(cd)

    print(f" {C.GRAY}👤{C.R} Account : {C.CYAN}{STATE['username'] or '?'}{C.R}")
    print(f" {C.GRAY}💰{C.R} Balance : {C.GREEN}{bal_str}{C.R}")
    print(f" {C.GRAY}⏰{C.R} Faucet  : {C.YELLOW}{cd_str}{C.R}")
    print(f" {C.GRAY}📊{C.R} Claims  : {C.CYAN}{STATE['total_claims']}{C.R}")
    print(f" {C.GRAY}💵{C.R} Earned  : {C.YELLOW}{STATE['total_reward']:.8f}{C.R} {STATE['currency']}")
    print(f" {C.GRAY}⏱{C.R} Runtime : {C.CYAN}{runtime}{C.R}")
    print()


# ==================== LIVE COUNTDOWN ====================
def live_countdown(target_ts, label="Next claim"):
    """
    Live countdown real-time sampai target_ts.
    Update tiap detik di baris yang sama, clear saat selesai.
    Bisa di-interrupt pakai Ctrl+C.
    """
    global _spin_idx
    frame_idx = 0

    # Print blank line biar gak nabrak teks di atas
    print()
    while True:
        now = time.time()
        remaining = target_ts - now
        if remaining <= 0:
            break

        # Get progress bar
        total = max(target_ts - STATE.get("countdown_started_at", now), 1)
        elapsed = total - remaining
        pct = min(100, max(0, int((elapsed / total) * 100)))
        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        frame = SPINNER[frame_idx % len(SPINNER)]
        frame_idx += 1

        # Format
        time_str = fmt_duration(remaining)
        line = (
            f"\r{C.GRAY}[{now_str()}]{C.R} {C.CYAN}{frame}{C.R}  "
            f"{label} {C.GREEN}{time_str}{C.R}  "
            f"{C.CYAN}{bar}{C.R} {C.YELLOW}{pct:3d}%{C.R}  "
            f"{C.GRAY}(Ctrl+C stop){C.R}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()

        time.sleep(0.5)

    # Clear line
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()
    log(f"{label}: {C.GREEN}READY{C.R}", "ok")


# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else False
    except json.JSONDecodeError:
        return False
    except Exception:
        return False


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"{C.RED}!! Gagal simpan config: {e}{C.R}")
        return False


def normalize_cookie(raw):
    raw = raw.strip().rstrip(";, \t\r\n")
    if not raw:
        return ""
    if raw.startswith("faas_session="):
        return raw
    if "=" not in raw:
        return f"faas_session={raw}"
    return raw


def ensure_config():
    cfg = load_config()
    if cfg is False:
        print(f"{C.RED}!! Config corrupt. Hapus drfaucet_config.json dan jalanin ulang.{C.R}")
        sys.exit(1)

    if isinstance(cfg, dict):
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        for old in ("solver_jitter_min", "solver_jitter_max", "wake_buffer_seconds"):
            if old in cfg:
                cfg.pop(old, None)
                changed = True
        if changed:
            save_config(cfg)
        return cfg

    banner()
    section("Setup Config")
    print(f"{C.YELLOW}File config belum ada. Isi data di bawah:{C.R}\n")

    apikey = input(f"  {C.CYAN}Waryono API Key{C.R}                  : ").strip()
    print(f"  {C.CYAN}Cookie{C.R} — paste 'faas_session=xxx' ATAU value-nya doang")
    cookie = input(f"  {C.CYAN}Cookie{C.R}                            : ").strip()
    sitekey = input(f"  {C.CYAN}hCaptcha sitekey (enter=auto-detect){C.R}: ").strip()

    cfg = dict(DEFAULT_CONFIG)
    cfg["waryono_apikey"] = apikey
    cfg["cookie"] = normalize_cookie(cookie)
    cfg["hcaptcha_sitekey"] = sitekey.strip()

    save_config(cfg)
    print(f"\n{C.GREEN}✔ Config tersimpan: {CONFIG_PATH}{C.R}\n")
    time.sleep(1.0)
    return cfg


# ==================== HTTP ====================
def make_session(cookie_raw):
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Origin": BASE,
        "Referer": f"{BASE}/",
    })

    cookie_str = normalize_cookie(cookie_raw)
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            s.cookies.set(k.strip(), v.strip())

    return s


# ==================== SITEKEY DETECT ====================
def detect_sitekey(session, debug=False):
    try:
        r = session.get(f"{BASE}/", timeout=30, allow_redirects=True)
        if not r.ok:
            return None, None
        html = r.text

        patterns = [
            r'data-sitekey=["\']([0-9a-f\-]{30,})["\']',
            r'hcaptcha\.render\([^)]*["\']([0-9a-f\-]{30,})["\']',
            r'["\']sitekey["\']\s*[:=]\s*["\']([0-9a-f\-]{30,})["\']',
            r'sitekey["\']?\s*[:=]\s*["\']([0-9a-f\-]{30,})["\']',
            r'new\s+hcaptcha[^)]*["\']([0-9a-f\-]{30,})["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1), "homepage"

        script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html)
        if debug:
            log(f"Homepage miss, scanning {len(script_urls)} scripts...", "dbg")

        for js_url in script_urls[:6]:
            if not js_url.startswith("http"):
                js_url = BASE + (js_url if js_url.startswith("/") else "/" + js_url)
            try:
                jr = session.get(js_url, timeout=20)
                if not jr.ok:
                    continue
                jt = jr.text
                for pat in patterns:
                    m = re.search(pat, jt, re.IGNORECASE)
                    if m:
                        return m.group(1), f"js:{js_url.split('/')[-1][:30]}"
            except Exception:
                continue
    except Exception:
        pass
    return None, None


# ==================== WARYONO HCAPTCHA ====================
def _solve_hcaptcha_once(cfg, sitekey):
    apikey = cfg["waryono_apikey"]

    payload = {
        "apikey": apikey,
        "methods": "hcaptcha",
        "domain": BASE,
        "sitekey": sitekey,
        "json": 1,
    }

    try:
        r = requests.post(SOLVER_IN, json=payload, timeout=60)
    except Exception as e:
        raise Exception(f"submit network error: {e}")

    if not r.ok:
        raise Exception(f"submit HTTP {r.status_code}")

    try:
        res = r.json()
    except Exception:
        raise Exception(f"submit non-JSON: {r.text[:150]}")

    if res.get("status") != 1:
        raise Exception(f"submit fail: {res.get('request', res)}")

    task_id = res.get("request")
    if not task_id:
        raise Exception(f"no task id: {res}")

    log(f"CAPTCHA task submitted", "captcha")

    max_polls = 100
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

        if check.get("status") == 1:
            token = check.get("request")
            if not token:
                raise Exception(f"solved but empty token: {check}")
            clear_line()
            log(f"CAPTCHA task completed", "ok")
            return token

        req = str(check.get("request", ""))
        if req in ("CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"):
            spinner_line(f"Polling solver... ({i*3}s)")
            continue

        clear_line()
        raise Exception(f"waryono error: {req}")

    clear_line()
    raise Exception("hcaptcha timeout")


def solve_hcaptcha(cfg, sitekey):
    last_err = None
    for attempt in range(1, MAX_CAPTCHA_RETRY + 1):
        if attempt > 1:
            log(f"CAPTCHA retry ({attempt}/{MAX_CAPTCHA_RETRY})", "retry")
        else:
            log(f"CAPTCHA task submitted (1/{MAX_CAPTCHA_RETRY})", "captcha")

        try:
            return _solve_hcaptcha_once(cfg, sitekey)
        except Exception as e:
            err_str = str(e)
            last_err = err_str

            retryable = (
                "ERROR_CAPTCHA_UNSOLVABLE" in err_str
                or "timeout" in err_str.lower()
                or "network error" in err_str.lower()
            )

            if not retryable:
                raise

            if attempt < MAX_CAPTCHA_RETRY:
                time.sleep(2)
            else:
                log(f"{err_str} (max retry reached)", "err")

    raise Exception(f"hCaptcha failed after {MAX_CAPTCHA_RETRY}x: {last_err}")


# ==================== SESSION / COOKIE CHECK ====================
def api_session(session, silent=False):
    try:
        r = session.get(f"{BASE}/api/session", timeout=30)
        if not r.ok:
            if not silent:
                log(f"Session HTTP {r.status_code}", "err")
            return None
        return r.json()
    except Exception as e:
        if not silent:
            log(f"Session error: {e}", "err")
        return None


def check_cookie_valid(session, silent=False):
    sess = api_session(session, silent=silent)
    if sess is None:
        return None, None
    if not sess.get("logged_in"):
        return False, None
    return True, sess


def apply_session_data(sess):
    STATE["username"] = sess.get("name") or STATE["username"]
    STATE["currency"] = sess.get("balance_currency") or STATE["currency"]
    STATE["provider"] = sess.get("provider") or STATE["provider"]

    if sess.get("balance_available"):
        try:
            STATE["balance"] = float(sess["balance"])
        except (TypeError, ValueError):
            pass


# ==================== API ====================
def api_faucet_status(session):
    r = session.get(f"{BASE}/api/faucet-status", timeout=30)
    if not r.ok:
        raise Exception(f"faucet-status HTTP {r.status_code}")
    return r.json()


def parse_next_claim(status, default_interval=300):
    interval = int(status.get("interval_seconds", default_interval))
    next_at = status.get("next_claim_at")

    if next_at:
        try:
            dt = datetime.strptime(next_at.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
            return dt.timestamp(), interval
        except Exception:
            pass

    return time.time() + interval, interval


def do_claim(session, cfg, sitekey):
    log("Claiming faucet...", "coin")

    token = solve_hcaptcha(cfg, sitekey)

    data = {
        "g-recaptcha-response": token,
        "h-captcha-response": token,
    }

    try:
        r = session.post(
            f"{BASE}/claim",
            data=data,
            timeout=60,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{BASE}/",
                "Origin": BASE,
            },
        )
    except Exception as e:
        raise Exception(f"claim POST error: {e}")

    if not r.ok:
        raise Exception(f"claim HTTP {r.status_code}")

    ct = r.headers.get("Content-Type", "")
    if "application/json" not in ct:
        raise Exception(f"claim unexpected content-type: {ct}")

    try:
        data = r.json()
    except Exception:
        raise Exception(f"claim non-JSON: {r.text[:200]}")

    if not data.get("success"):
        err = data.get("error") or data.get("message") or json.dumps(data)[:200]
        raise Exception(f"claim failed: {err}")

    amount = float(data.get("amount", 0) or 0)
    payout_id = data.get("payout_id", "?")
    bonus = data.get("bonus") or {}

    STATE["total_claims"] += 1
    STATE["total_reward"] += amount

    print(f"{C.GRAY}[{now_str()}]{C.R} {C.GREEN}✔{C.R}  Claim successful")
    print(f"             {C.GRAY}Reward :{C.R} {C.YELLOW}+{amount:.8f} {data.get('currency', STATE['currency'])}{C.R}")

    if bonus and bonus.get("total_bps"):
        pct = bonus["total_bps"] / 100
        bonus_line = f"+{pct:.0f}%"
        if bonus.get("mystery_bps"):
            bonus_line += f" (Mystery: {bonus['mystery_bps']/100:.0f}%)"
        print(f"             {C.GRAY}Bonus  :{C.R} {C.MAGENTA}{bonus_line}{C.R}")

    print(f"             {C.GRAY}Payout :{C.R} {C.CYAN}#{payout_id}{C.R}")

    return data


# ==================== MAIN ====================
def main():
    cfg = ensure_config()

    if not cfg.get("waryono_apikey"):
        banner()
        log("waryono_apikey kosong di config", "err")
        return

    if not cfg.get("cookie"):
        banner()
        log("cookie kosong di config", "err")
        return

    banner()
    log("Bot started", "ok")
    log(f"Cookie: {cfg['cookie'][8:18]}...{cfg['cookie'][-6:]}", "dbg")

    session = make_session(cfg["cookie"])

    # ── Session verify ──
    section("Session Verification")
    valid, sess = check_cookie_valid(session, silent=False)

    if valid is None:
        log("Network error, coba lagi nanti", "err")
        return

    if not valid:
        log("Cookie invalid / expired", "err")
        print()
        print(f"{C.YELLOW}Penyebab umum:{C.R}")
        print(f"  1. Cookie expired — login ulang di browser, ambil cookie baru")
        print(f"  2. Cookie di-rotate per request")
        print(f"  3. Cookie di-bind ke IP/User-Agent beda")
        print()
        print(f"{C.YELLOW}Update cookie di:{C.R} {CONFIG_PATH}")
        return

    STATE["session_valid"] = True
    apply_session_data(sess)

    log(f"Logged in as {STATE['username']} ({(STATE['provider'] or '?').title()})", "ok")
    if STATE["balance"] is not None:
        log(f"Balance: {STATE['balance']:.8f} {STATE['currency']}", "bal")

    # ── Captcha sitekey ──
    section("Captcha Detection")
    sitekey = cfg.get("hcaptcha_sitekey", "").strip()

    if not sitekey:
        log("Detecting hCaptcha sitekey...", "info")
        detected, source = detect_sitekey(session, debug=True)
        if detected:
            sitekey = detected
            STATE["sitekey"] = detected
            STATE["sitekey_source"] = source
            log(f"Sitekey detected ({source})", "ok")
            cfg["hcaptcha_sitekey"] = detected
            save_config(cfg)
        else:
            sitekey = FALLBACK_SITEKEY
            STATE["sitekey"] = FALLBACK_SITEKEY
            STATE["sitekey_source"] = "fallback"
            log(f"Auto-detect gagal, pakai fallback", "warn")
    else:
        STATE["sitekey"] = sitekey
        STATE["sitekey_source"] = "config"
        log(f"Sitekey loaded from config", "ok")

    # ── Initial sync ──
    section("Initial Sync")
    try:
        status = api_faucet_status(session)
    except Exception as e:
        log(f"faucet-status error: {e}", "err")
        return

    STATE["next_claim_at"], interval = parse_next_claim(status)

    cd = STATE["next_claim_at"] - time.time()
    if cd > 0:
        log(f"Faucet status: {fmt_duration(cd)} cooldown", "wait")
    else:
        log("Faucet status: READY", "ok")

    # ── Main loop ──
    cycle = 0
    while True:
        cycle += 1
        section(f"Cycle #{cycle}")
        info_card()

        try:
            # Re-verify cookie tiap N cycle
            if cycle > 1 and cycle % SESSION_RECHECK_EVERY == 0:
                log("Re-checking cookie...", "info")
                valid, sess = check_cookie_valid(session, silent=True)
                if valid is False:
                    log("Cookie expired! Bot stop.", "err")
                    print(f"{C.YELLOW}Update cookie di: {CONFIG_PATH}{C.R}")
                    print_summary()
                    return
                elif valid is True:
                    apply_session_data(sess)
                    log("Cookie still valid", "ok")

            # Live countdown sampai ready
            cd = STATE["next_claim_at"] - time.time()
            if cd > 0:
                STATE["countdown_started_at"] = time.time()
                live_countdown(STATE["next_claim_at"], label="Next claim")

            # Pre-claim cookie check
            valid, sess = check_cookie_valid(session, silent=True)
            if valid is False:
                log("Cookie expired before claim! Bot stop.", "err")
                print(f"{C.YELLOW}Update cookie di: {CONFIG_PATH}{C.R}")
                print_summary()
                return
            if valid is True:
                apply_session_data(sess)

            # Claim
            try:
                do_claim(session, cfg, sitekey)
            except Exception as e:
                log(f"Claim error: {e}", "err")
                log("Bot berhenti karena error.", "warn")
                print_summary()
                return

            # Update balance
            sess = api_session(session, silent=True)
            if sess:
                apply_session_data(sess)

            # Update next claim
            try:
                status = api_faucet_status(session)
                STATE["next_claim_at"], interval = parse_next_claim(status, interval)
            except Exception:
                STATE["next_claim_at"] = time.time() + interval

            cd = STATE["next_claim_at"] - time.time()
            log(f"Next claim in {fmt_duration(cd)}", "wait")

        except KeyboardInterrupt:
            print()
            log("Stopped by user.", "warn")
            print_summary()
            break
        except Exception as e:
            log(f"Loop error: {e}", "err")
            print_summary()
            return


def print_summary():
    runtime = time.time() - STATE["started_at"]
    print()
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}  📊  SESSION SUMMARY — DrFaucet{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"  {C.GRAY}Account      :{C.R} {C.CYAN}{STATE['username'] or '?'}{C.R}")
    print(f"  {C.GRAY}Provider     :{C.R} {C.CYAN}{(STATE['provider'] or '?').title()}{C.R}")
    print(f"  {C.GRAY}Runtime      :{C.R} {C.CYAN}{fmt_duration(runtime)}{C.R}")
    bal_str = f"{STATE['balance']:.8f} {STATE['currency']}" if STATE['balance'] is not None else "?"
    print(f"  {C.GRAY}Balance      :{C.R} {C.GREEN}{bal_str}{C.R}")
    print(f"  {C.GRAY}Total claims :{C.R} {C.CYAN}{STATE['total_claims']}{C.R}")
    print(f"  {C.GRAY}Total reward :{C.R} {C.YELLOW}{STATE['total_reward']:.8f} {STATE['currency']}{C.R}")
    if STATE["total_claims"] > 0:
        avg = STATE["total_reward"] / STATE["total_claims"]
        print(f"  {C.GRAY}Avg / claim  :{C.R} {C.CYAN}{avg:.8f} {STATE['currency']}{C.R}")
    print(f"  {C.GRAY}Sitekey      :{C.R} {C.CYAN}{STATE['sitekey'] or '?'}{C.R} ({STATE['sitekey_source'] or '?'})")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Stopped.{C.R}")
        try:
            print_summary()
        except Exception:
            pass
    except Exception as e:
        print(f"\n{C.RED}!! Fatal error: {e}{C.R}")
        import traceback
        traceback.print_exc()
