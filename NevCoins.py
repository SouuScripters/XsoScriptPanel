#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
  NEVCOINS.CLUB AUTO FARMER — BALANCE-AWARE EDITION
  By Dev MoneyMaker_w
  - Cookie + UA login
  - Turnstile captcha (Waryono)
  - REAL timer detection (HTML + JS vars + local tracking)
  - Auto-balance check after every claim (+ delta)
  - Clean SIGTSTP / Ctrl+Z handling
  - Human delay 6-7 min after success
  - Auto-stop 6 hours
  - Auto-stop 3x Fatal API Error
============================================================
"""

import os, sys, time, json, re, random, signal, requests
from datetime import datetime

# ═══════════════════ NEON TRUE-COLOR ═══════════════════
def _rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"

NEON_GREEN  = _rgb(57, 255, 20)
NEON_YELLOW = _rgb(255, 230, 0)
NEON_CYAN   = _rgb(0, 255, 240)
NEON_PINK   = _rgb(255, 16, 240)
WHITE       = _rgb(235, 235, 235)
GRAY        = _rgb(135, 135, 135)
RESET       = "\033[0m"
BOLD        = "\033[1m"

GREEN, YELLOW, CYAN, PINK, RED = NEON_GREEN, NEON_YELLOW, NEON_CYAN, NEON_PINK, NEON_PINK
AQUA_COLOR = NEON_CYAN  # alias untuk log balance

# ═══════════════════ CONFIG ═══════════════════
BASE_URL         = "https://nevcoins.club"
CONFIG_FILE      = "nevcoins_config.json"
STATE_FILE       = "nevcoins_state.json"
DEBUG_DIR        = "nevcoins_debug"
DEFAULT_UA       = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36")
FALLBACK_SITEKEY = "0x4AAAAAAAM-vGcWBgGyKbwW"
WARYONO_IN       = "https://api.waryono.my.id/in.php"
WARYONO_RES      = "https://api.waryono.my.id/res.php"
RUN_HOURS        = 6
CLAIM_COOLDOWN   = 300
DEFAULT_WAIT     = 300

_TTY = sys.stdout.isatty()
os.makedirs(DEBUG_DIR, exist_ok=True)

# ═══════════════════ SIGNAL HANDLERS ═══════════════════
def _clean_line():
    if _TTY:
        try:
            width = os.get_terminal_size().columns
        except Exception:
            width = 100
        sys.stdout.write("\r" + " " * width + "\r")
        sys.stdout.flush()

def _sig_tstp(signum, frame):
    """Ctrl+Z — clean progress line first, then actually suspend."""
    _clean_line()
    signal.signal(signal.SIGTSTP, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGTSTP)

def _sig_int(signum, frame):
    """Ctrl+C — clean progress line, then raise KeyboardInterrupt."""
    _clean_line()
    raise KeyboardInterrupt

signal.signal(signal.SIGTSTP, _sig_tstp)
signal.signal(signal.SIGINT,  _sig_int)

# ═══════════════════ UTILS ═══════════════════
def now():   return datetime.now().strftime("%H:%M:%S")
def clear(): os.system('cls' if os.name == 'nt' else 'clear')

def _fmt(tag, msg, color):
    return f"{GRAY}[{now()}]{RESET} {color}[{tag.upper():8}]{RESET} {msg}"

def log(tag, msg, color=WHITE):
    print(_fmt(tag, msg, color)); sys.stdout.flush()

def progress(tag, msg, color):
    if not _TTY: return
    sys.stdout.write("\r" + _fmt(tag, msg, color) + " " * 20); sys.stdout.flush()

def progress_done(tag, msg, color):
    if _TTY:
        sys.stdout.write("\r" + _fmt(tag, msg, color) + " " * 20 + "\n")
    else:
        print(_fmt(tag, msg, color))
    sys.stdout.flush()

def clean_html(s):
    if not s: return ""
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def dump(name, content):
    try:
        path = os.path.join(DEBUG_DIR, name)
        with open(path, "w", encoding="utf-8") as f: f.write(content or "")
    except Exception: pass

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except Exception: pass
    return default

def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f, indent=2)
    except Exception as e:
        log("cfg", f"Save err: {e}", PINK)

def load_cfg():  return load_json(CONFIG_FILE, {})
def save_cfg(c): save_json(CONFIG_FILE, c)

def parse_balance_str(s):
    """'18.00' → 18.0"""
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


# ═══════════════════ HEADER ═══════════════════
def print_header():
    clear()
    print(f"""{GREEN}{BOLD}
============================================================{RESET}
{GREEN}{BOLD}              NEVCOINS.CLUB AUTO FARMER{RESET}
{PINK}{BOLD}                 By Dev MoneyMaker_w{RESET}
{GREEN}{BOLD}============================================================{RESET}
""")

def _status(v):
    return f"{GREEN}✔ SET{RESET}" if v else f"{PINK}✖ EMPTY{RESET}"

def print_menu(cfg):
    print(f"""{CYAN}{BOLD}============================{RESET}
{YELLOW}{BOLD}         MAIN MENU{RESET}
{CYAN}{BOLD}============================{RESET}
{WHITE}  1. Start Farming{RESET}
{WHITE}  2. Config Cookies      [{_status(cfg.get('cookie'))}{WHITE}]
{WHITE}  3. Config Apikey       [{_status(cfg.get('apikey'))}{WHITE}]
{WHITE}  4. Config User-Agent   [{_status(cfg.get('user_agent'))}{WHITE}]
{WHITE}  0. Exit{RESET}
{CYAN}{BOLD}============================{RESET}""")


# ═══════════════════ PARSERS ═══════════════════
def parse_hms(s):
    try:
        parts = list(map(int, s.split(':')))
        if   len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
        elif len(parts) == 2: return parts[0]*60 + parts[1]
        elif len(parts) == 1: return parts[0]
    except Exception: pass
    return 0

def parse_wait_sec(msg):
    if not msg: return None
    m = re.search(r'(\d+)\s*(?:second|sec|detik|s)\b', msg, re.I)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:minute|min|menit|m)\b', msg, re.I)
    if m: return int(m.group(1)) * 60
    m = re.search(r'(\d{1,2}):(\d{2})', msg)
    if m: return int(m.group(1))*60 + int(m.group(2))
    return None

def detect_timer_from_html(html):
    if not html: return None, None
    for var in ("waitTime", "wait_time", "cooldown", "remaining", "timeLeft",
                "time_left", "timer", "seconds", "faucetTimer", "countdown"):
        pat = rf'(?:var|let|const)\s+{var}\s*=\s*["\']?(\d+)["\']?'
        m = re.search(pat, html, re.I)
        if m:
            sec = int(m.group(1))
            if 0 < sec < 86400:
                return sec, f"js_var:{var}"
    for attr in ("data-timer", "data-cooldown", "data-remaining",
                 "data-wait", "data-seconds", "data-time"):
        m = re.search(rf'{attr}=["\'](\d+)["\']', html, re.I)
        if m:
            sec = int(m.group(1))
            if 0 < sec < 86400:
                return sec, f"attr:{attr}"
    patterns = [
        (r'id=["\'](?:timer|faucet_timer|faucetTimer|countdown|cooldown)[^"\']*["\'][^>]*>\s*([\d:]+)\s*<', "id:timer"),
        (r'class=["\'][^"\']*(?:timer|countdown|cooldown)[^"\']*["\'][^>]*>\s*([\d:]+)\s*<', "class:timer"),
    ]
    for pat, src in patterns:
        m = re.search(pat, html, re.I)
        if m:
            v = m.group(1).strip()
            if ':' in v:
                sec = parse_hms(v)
                if 0 < sec < 86400:
                    return sec, src
    return None, None


# ═══════════════════ CAPTCHA SOLVER ═══════════════════
def solve_captcha(apikey, sitekey, page_url):
    log("captcha", f"Submit turnstile | sitekey={sitekey[:22]}...", YELLOW)
    try:
        r = requests.post(WARYONO_IN, json={
            "apikey": apikey, "methods": "turnstile",
            "domain": page_url, "sitekey": sitekey, "json": 1,
        }, timeout=30)
        res = r.json()
    except Exception as e:
        log("captcha", f"Submit err: {e}", PINK); return "CONNECTION_ERROR"

    if res.get("status") != 1:
        err_msg = res.get('request','?')
        log("captcha", f"Submit fail: {err_msg}", PINK)
        return err_msg  # Return error string

    task_id = res.get("request")
    log("captcha", f"Task ID: {task_id}", GRAY)

    start = time.time()
    last_log = -15
    for i in range(120):
        time.sleep(3)
        elapsed = int(time.time() - start)
        if _TTY:
            progress("captcha", f"Polling{'.'*(i%4)} {elapsed}s", YELLOW)
        else:
            if elapsed - last_log >= 15:
                log("captcha", f"Polling... {elapsed}s", YELLOW); last_log = elapsed
        try:
            poll = requests.get(WARYONO_RES, params={
                "apikey": apikey, "id": task_id, "action": "get", "json": 1
            }, timeout=30)
            pr = poll.json()
        except Exception:
            continue
        if pr.get("status") == 1:
            progress_done("captcha", f"✔ Solved ({elapsed}s)", GREEN)
            return pr.get("request")
        if "CAPCHA_NOT_READY" in str(pr.get("request", "")).upper():
            continue
        
        err_msg = pr.get('request')
        progress_done("captcha", f"✖ Err: {err_msg}", PINK)
        return err_msg  # Return error string
    progress_done("captcha", "✖ Timeout", PINK)
    return "TIMEOUT"


# ═══════════════════ HUMAN WAIT ═══════════════════
def human_wait(total_sec, label="wait"):
    total = max(1, int(total_sec))
    log(label, f"Sleeping {total/60:.1f}min ({total}s)...", CYAN)
    last_log = -30
    for i in range(total, 0, -1):
        mm, ss = divmod(i, 60)
        if _TTY:
            progress(label, f"{mm:02d}:{ss:02d} sisa", YELLOW)
        else:
            elapsed = total - i
            if elapsed - last_log >= 30:
                log(label, f"{mm:02d}:{ss:02d} sisa", YELLOW); last_log = elapsed
        time.sleep(1)
    progress_done(label, "✔ Done", GREEN)


# ═══════════════════ BOT ═══════════════════
class NevBot:
    def __init__(self, cfg):
        self.cfg   = cfg
        self.state = load_json(STATE_FILE, {"last_claim": 0, "last_success": 0})
        self.s     = requests.Session()
        self.s.headers.update({
            "User-Agent":      cfg.get("user_agent", DEFAULT_UA),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,"
                               "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer":         BASE_URL + "/",
        })
        self._parse_cookies(cfg.get("cookie", ""))
        self.api_fail_count = 0  # Tambahan buat track error API

    def _parse_cookies(self, cstr):
        for part in cstr.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self.s.cookies.set(k, v, domain="nevcoins.club")

    def _is_logged_in(self, html):
        return ("Logout" in html) or ("logout" in html) or ("AccExist" in str(self.s.cookies))

    # ═══ BALANCE ═══
    def get_balance(self):
        """Return {'balance': float, 'raw': str} or {'error': str}"""
        try:
            r = self.s.get(f"{BASE_URL}/", timeout=30)
            html = r.text
            if not self._is_logged_in(html):
                return {"error": "invalid_cookie"}
            m = re.search(r'nv-bal-amount">\s*([\d.,]+)\s*Coins', html)
            raw = m.group(1) if m else None
            return {"balance": parse_balance_str(raw), "raw": raw or "?"}
        except Exception as e:
            return {"error": str(e)}

    # ═══ CHECK READY ═══
    def check_ready(self):
        try:
            r = self.s.get(f"{BASE_URL}/claim.html", timeout=30)
            html = r.text
        except Exception as e:
            return {"error": f"fetch: {e}"}

        if not self._is_logged_in(html):
            return {"error": "invalid_cookie"}

        dump("claim_page.html", html)

        # L1: HTML timer
        sec, src = detect_timer_from_html(html)
        if sec is not None:
            log("check", f"HTML timer detected: {sec}s (source: {src})", GRAY)
            return {"ready": sec <= 0, "timer": max(0, sec), "source": src}

        # L2: AJAX endpoint
        m = re.search(r"var\s+token\s*=\s*'([a-f0-9]+)'", html)
        token = m.group(1) if m else None
        if token:
            self.s.headers["X-Requested-With"] = "XMLHttpRequest"
            self.s.headers["Referer"]          = f"{BASE_URL}/claim.html"
            for action in ("checkFaucet", "getFaucetStatus", "checkTimer", "faucetStatus"):
                try:
                    p = self.s.post(f"{BASE_URL}/system/ajax.php",
                                    data={"a": action, "token": token}, timeout=15)
                except Exception:
                    continue
                if not p.text.strip().startswith("{"):
                    continue
                dump(f"check_{action}.json", p.text)
                try:
                    j = p.json()
                except Exception:
                    continue
                if not isinstance(j, dict): continue

                for k in ("timer", "remaining", "seconds", "wait", "cooldown",
                          "time_left", "timeLeft", "waitTime", "wait_time"):
                    if k in j and j[k] not in (None, "", 0, "0"):
                        try:
                            sec = int(j[k])
                            if 0 < sec < 86400:
                                return {"ready": False, "timer": sec, "source": f"ajax:{k}"}
                        except Exception:
                            pass

                ready = j.get("ready") or j.get("canClaim") or j.get("can_claim")
                if ready is True:  return {"ready": True,  "timer": 0, "source": "ajax:ready_flag"}
                if ready is False:
                    msg = clean_html(j.get("message") or j.get("msg") or "")
                    sec = parse_wait_sec(msg) or DEFAULT_WAIT
                    return {"ready": False, "timer": sec, "source": "ajax:ready_false"}

                st = j.get("status")
                if st in (1, 200): return {"ready": True,  "timer": 0, "source": "ajax:status_ok"}
                if st == 400:
                    msg = clean_html(j.get("message") or j.get("msg") or "")
                    sec = parse_wait_sec(msg) or DEFAULT_WAIT
                    return {"ready": False, "timer": sec, "source": "ajax:status_400"}

        # L3: local tracking
        last_success = self.state.get("last_success", 0)
        if last_success > 0:
            elapsed   = time.time() - last_success
            remaining = CLAIM_COOLDOWN - elapsed
            if remaining > 0:
                return {"ready": False, "timer": int(remaining), "source": "local:last_success"}
            return {"ready": True,  "timer": 0, "source": "local:last_success_expired"}

        return {"ready": True, "timer": 0, "source": "assumed"}

    # ═══ CLAIM ═══
    def claim(self):
        log("claim", "Fetching /claim.html...", CYAN)
        try:
            r = self.s.get(f"{BASE_URL}/claim.html", timeout=30)
            html = r.text
        except Exception as e:
            log("claim", f"Fetch err: {e}", PINK); return False

        if not self._is_logged_in(html):
            log("claim", "Cookie invalid / not logged in", PINK); return False

        m = re.search(r"var\s+token\s*=\s*'([a-f0-9]+)'", html)
        if not m:
            log("claim", "CSRF token not found", PINK); return False
        token = m.group(1)

        m = re.search(r'cf-turnstile"[^>]*data-sitekey="([^"]+)"', html)
        sitekey = m.group(1) if m else FALLBACK_SITEKEY

        log("claim", f"Token={token[:12]}... | Sitekey={sitekey[:22]}...", GRAY)

        captcha = solve_captcha(self.cfg.get("apikey", ""), sitekey,
                                f"{BASE_URL}/claim.html")
        
        # ═══ HANDLE SOLVER ERRORS ═══
        if not captcha or captcha.startswith("ERROR"):
            log("claim", f"Solver Error: {captcha}", PINK)
            
            # Daftar error yang bikin bot berhenti kalau nyampe 3x
            fatal_errors = ["ERROR_CAPTCHA_UNSOLVABLE", "ERROR_WRONG_USER_KEY", 
                            "ERROR_ZERO_BALANCE", "ERROR_KEY_DOES_NOT_EXIST"]
            
            if any(e in captcha for e in fatal_errors):
                self.api_fail_count += 1
                log("claim", f"Fatal API Error Streak: {self.api_fail_count}/3", YELLOW)
                if self.api_fail_count >= 3:
                    return "STOP"
            else:
                log("claim", "Non-fatal solver error, retrying...", YELLOW)
            return False
            
        # Reset counter kalau sukses dapet captcha
        self.api_fail_count = 0

        self.s.headers["X-Requested-With"] = "XMLHttpRequest"
        self.s.headers["Referer"]          = f"{BASE_URL}/claim.html"
        payload = {"a": "getFaucet", "token": token, "captcha": captcha}
        log("claim", "POST /system/ajax.php ...", CYAN)
        try:
            p = self.s.post(f"{BASE_URL}/system/ajax.php", data=payload, timeout=30)
            j = p.json()
        except Exception as e:
            log("claim", f"POST err: {e}", PINK); return False

        dump("claim_result.json", p.text)

        st = j.get("status")
        if st in (1, 200):
            reward = j.get("reward") or j.get("lucky") or j.get("amount") or "?"
            msg    = clean_html(j.get("message") or j.get("msg") or "OK")
            log("claim", f"✔ SUCCESS | Reward: {reward} | {msg}", GREEN)

            self.state["last_claim"]   = time.time()
            self.state["last_success"] = time.time()
            save_json(STATE_FILE, self.state)
            return True

        msg = clean_html(j.get("message") or j.get("msg") or str(j)[:120])
        log("claim", f"✖ Failed: {msg}", PINK)
        sec = parse_wait_sec(msg)
        if sec and sec > 0:
            self.state["last_success"] = time.time() - (CLAIM_COOLDOWN - sec)
            save_json(STATE_FILE, self.state)
        return False


# ═══════════════════ FARMING LOOP ═══════════════════
def run_farming(cfg):
    print_header()
    print(f"{GREEN}{BOLD}============================================================{RESET}")
    print(f"{GREEN}  FARMING STARTED  —  LIMIT {RUN_HOURS} HOURS{RESET}")
    print(f"{GREEN}{BOLD}============================================================{RESET}\n")

    bot      = NevBot(cfg)
    start    = time.time()
    end_time = start + (RUN_HOURS * 3600)
    ok, fail = 0, 0
    earned_total = 0.0

    try:
        # ── initial balance ──
        bal = bot.get_balance()
        if "error" in bal:
            log("auth", f"Gagal login: {bal['error']}", PINK)
            input(f"\n{YELLOW}Enter buat balik ke menu...{RESET}")
            return

        start_balance = bal["balance"]
        last_balance  = bal["balance"]
        log("auth", f"Logged in ✔ | Balance: {bal['raw']} Coins", GREEN)

        while time.time() < end_time:
            remain_h = (end_time - time.time()) / 3600
            log("loop", f"Remaining: {remain_h:.2f}h | OK: {ok} | FAIL: {fail}", CYAN)

            status = bot.check_ready()

            if "error" in status:
                log("check", f"Err: {status['error']}", PINK)
                human_wait(30, "wait")
                continue

            if not status["ready"]:
                timer  = status["timer"] or DEFAULT_WAIT
                source = status.get("source", "?")
                jitter = random.uniform(3, 15)
                wait_total = min(timer + jitter, max(1, end_time - time.time()))
                log("check", f"✖ Not ready — {timer}s ({source}) + {jitter:.0f}s jitter", YELLOW)
                human_wait(wait_total, "wait")
                continue

            log("check", f"✔ Faucet READY ({status.get('source','?')}) — claiming now", GREEN)

            res = bot.claim()
            
            if res == "STOP":
                log("bot", "AUTO-STOP: 3x Fatal API / Solver Errors detected.", PINK)
                break
            elif res:
                ok += 1

                # ═══ AUTO BALANCE CHECK AFTER CLAIM ═══
                time.sleep(2)  # let server propagate
                new_bal = bot.get_balance()
                if "error" not in new_bal:
                    delta = (new_bal["balance"] or 0) - (last_balance or 0)
                    if delta > 0:
                        earned_total += delta
                        log("balance", f"Balance: {new_bal['raw']} Coins | +{delta:.2f} (total earned: {earned_total:.2f})", AQUA_COLOR)
                    elif delta < 0:
                        log("balance", f"Balance: {new_bal['raw']} Coins | {delta:.2f}", YELLOW)
                    else:
                        log("balance", f"Balance: {new_bal['raw']} Coins | ±0 (pending?)", GRAY)
                    last_balance = new_bal["balance"]
                else:
                    log("balance", f"Balance check err: {new_bal['error']}", PINK)

                delay = min(random.uniform(360, 420), max(0, end_time - time.time()))
                if delay > 0:
                    human_wait(delay, "wait")
            else:
                fail += 1
                log("loop", "Claim failed, retry in 45s", YELLOW)
                human_wait(45, "wait")

        # ── final summary ──
        final_bal = bot.get_balance()
        print(f"\n{GREEN}{BOLD}============================================================{RESET}")
        print(f"{GREEN}{BOLD}  FARMING ENDED{RESET}")
        print(f"{GREEN}  Claims OK: {ok} | FAIL: {fail}{RESET}")
        if "error" not in final_bal and start_balance is not None:
            total = (final_bal["balance"] or 0) - start_balance
            print(f"{GREEN}  Start Balance: {start_balance:.2f} → End: {final_bal['balance']:.2f}{RESET}")
            print(f"{CYAN}  Total Earned: +{total:.2f} Coins{RESET}")
        print(f"{GREEN}{BOLD}============================================================{RESET}\n")
        input(f"{YELLOW}Enter buat balik ke menu...{RESET}")
        return

    except KeyboardInterrupt:
        _clean_line()
        print(f"\n{PINK}Stopped by user.{RESET}")
        print(f"{GREEN}  Session: OK: {ok} | FAIL: {fail} | Earned: +{earned_total:.2f} Coins{RESET}")
        return


# ═══════════════════ MAIN MENU ═══════════════════
def main():
    cfg = load_cfg()
    while True:
        print_header()
        print_menu(cfg)
        ch = input(f"\n{YELLOW}Pilih > {RESET}").strip()

        if ch == "0":
            print(f"\n{GREEN}Bye bro. — {PINK}MoneyMaker_w{RESET}")
            return

        elif ch == "1":
            if not cfg.get("cookie"):
                print(f"\n{PINK}Cookie kosong! Set dulu di menu 2.{RESET}")
                time.sleep(2); continue
            if not cfg.get("apikey"):
                print(f"\n{PINK}Apikey kosong! Set dulu di menu 3.{RESET}")
                time.sleep(2); continue
            run_farming(cfg)

        elif ch == "2":
            print(f"\n{CYAN}Paste cookie (PHPSESSID=xxx; SesHashKey=xxx; ...):{RESET}")
            c = input(f"{YELLOW}> {RESET}").strip()
            if c:
                cfg["cookie"] = c; save_cfg(cfg)
                print(f"{GREEN}✔ Cookie saved.{RESET}")
            else:
                print(f"{YELLOW}Skip.{RESET}")
            time.sleep(1)

        elif ch == "3":
            print(f"\n{GRAY}Format: API key Waryono{RESET}")
            a = input(f"{YELLOW}Apikey > {RESET}").strip()
            if a:
                cfg["apikey"] = a; save_cfg(cfg)
                print(f"{GREEN}✔ Apikey saved.{RESET}")
            else:
                print(f"{YELLOW}Skip.{RESET}")
            time.sleep(1)

        elif ch == "4":
            print(f"\n{GRAY}Default: {DEFAULT_UA}{RESET}")
            ua = input(f"{YELLOW}UA > {RESET}").strip()
            cfg["user_agent"] = ua if ua else DEFAULT_UA
            save_cfg(cfg)
            print(f"{GREEN}✔ User-Agent saved.{RESET}")
            time.sleep(1)

        else:
            print(f"{PINK}Pilihan gak ada bro.{RESET}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _clean_line()
        print(f"\n{PINK}Killed.{RESET}")
        sys.exit(0)
