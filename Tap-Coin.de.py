#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  TAP-COIN.DE AUTO CLAIM — SOUU ENGINE Edition v2.4b          ║
║  - COIN only (adcoin removed)                                ║
║  - ⚡ CF NUKE: Direct-IP bypass (no Seledroid)               ║
║  - Dynamic captcha detect (hcaptcha + turnstile) ✔           ║
║  - Success check via claims cookie                           ║
║  - Swal.fire error parsing                                   ║
║  - SurfAds integration                                       ║
║  - Dynamic Sleep based on faucet timer                       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, re, socket, requests
from datetime import datetime

# ═══════════════════ NEON COLORS ═══════════════════
def _c(n): return f"\033[38;5;{n}m"
RED, GREEN, YELLOW, CYAN, MAGENTA, WHITE, GRAY, AQUA = _c(196), _c(118), _c(226), _c(51), _c(201), _c(231), _c(245), _c(87)
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"

# ═══════════════════ CONFIG ═══════════════════
BASE_URL = "https://tap-coin.de"
HOST = "tap-coin.de"
CONFIG_FILE = "tapcoin_config.json"

# ─── ⚡ CF NUKE: DIRECT-IP ───
ORIGIN_IP = "185.30.32.143"
USE_DIRECT_IP = True

_DIRECT_IP_ACTIVE = False
_DIRECT_IP_FAILS = 0
_DIRECT_IP_FAIL_LIMIT = 3

FALLBACK_SITEKEY = "0x4AAAAAAANBXFpXlg2VZfSK"

WARYONO_KEY = ""
WARYONO_IN_URL = "https://api.waryono.my.id/in.php"
WARYONO_RES_URL = "https://api.waryono.my.id/res.php"
WARYONO_BALANCE_URL = "https://api.waryono.my.id/balance.php"

DEBUG_MODE = True

# ═══════════════════ UTILS ═══════════════════
def clear(): os.system('cls' if os.name == 'nt' else 'clear')
def now(): return datetime.now().strftime("%H:%M:%S")

def log(tag, msg, color=WHITE):
    print(f"{GRAY}[{now()}]{RESET} {color}[{tag.upper():6}]{RESET} {msg}")

def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {}

def save_cfg(cfg):
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)

def save_debug(filename, content):
    if DEBUG_MODE:
        try:
            with open(filename, "w", encoding="utf-8") as f: f.write(content or "")
        except: pass

def is_cf_blocked(html):
    if not html: return False
    markers = ["Just a moment...", "cf-chl", "challenge-platform",
               "Enable JavaScript and cookies to continue", "_cf_chl_opt"]
    return any(m in html for m in markers)

def parse_timer_sec(t_str):
    try:
        if not t_str or t_str == "00:00": return 0
        p = t_str.split(":")
        return int(p[0]) * 60 + int(p[1])
    except:
        return 0

def parse_swal(html):
    if not html: return ""
    m = re.search(r'Swal\.fire\("([^"]*)",\s*"([^"]*)"', html)
    if m: return f"{m.group(1)} — {m.group(2)}"
    return ""

# ═══════════════════ ⚡ DIRECT-IP ACTIVATOR ═══════════════════
def _probe_origin():
    try:
        s = socket.create_connection((ORIGIN_IP, 80), timeout=6)
        req = f"HEAD / HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        s.settimeout(6)
        data = s.recv(1024)
        s.close()
        if not data.startswith(b"HTTP/"): return False, "response bukan HTTP"
        line = data.split(b"\r\n", 1)[0].decode(errors="ignore")
        parts = line.split()
        if len(parts) >= 2:
            code = int(parts[1])
            if code in (200, 201, 301, 302, 303, 403): return True, f"HTTP {code}"
            if code >= 500: return False, f"origin error {code}"
            return True, f"HTTP {code}"
        return True, "HTTP ok"
    except socket.timeout:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

def _activate_direct_ip():
    global _DIRECT_IP_ACTIVE
    if not USE_DIRECT_IP: return
    log("cf-nuke", f"Probing origin {ORIGIN_IP}:80...", CYAN)
    ok, reason = _probe_origin()
    if not ok:
        log("cf-nuke", f"Origin unreachable ({reason})", RED)
        log("cf-nuke", "Direct-IP disabled — request via HTTPS + CF", YELLOW)
        return
    log("cf-nuke", f"Origin OK ({reason})", GREEN)
    import urllib3
    from urllib3.util import connection as _u3_conn
    _orig_create = _u3_conn.create_connection
    def _patched_create(address, *args, **kwargs):
        try:
            h, p = address
            if h == HOST and int(p) == 80:
                return _orig_create((ORIGIN_IP, 80), *args, **kwargs)
        except Exception: pass
        return _orig_create(address, *args, **kwargs)
    _u3_conn.create_connection = _patched_create
    urllib3.disable_warnings()
    _DIRECT_IP_ACTIVE = True
    log("cf-nuke", "⚡ DIRECT-IP ACTIVE — CF BYPASS 100%", GREEN)

def _disable_direct_ip(reason=""):
    global _DIRECT_IP_ACTIVE, _DIRECT_IP_FAILS
    if not _DIRECT_IP_ACTIVE: return
    _DIRECT_IP_ACTIVE = False
    _DIRECT_IP_FAILS = 0
    log("cf-nuke", f"Direct-IP disabled ({reason})", YELLOW)

# ═══════════════════ CAPTCHA DETECT ═══════════════════
def detect_captcha(html):
    if not html: return "", ""
    m = re.search(r"""<div[^>]*class=['"][^'"]*h-captcha[^'"]*['"][^>]*data-sitekey=['"]([^'"]+)""", html, re.I)
    if m: return "hcaptcha", m.group(1)
    m = re.search(r"""<div[^>]*data-sitekey=['"]([^'"]+)['"][^>]*class=['"][^'"]*h-captcha[^'"]*['"]""", html, re.I)
    if m: return "hcaptcha", m.group(1)
    if re.search(r"""<div[^>]*class=['"][^'"]*cf-turnstile""", html, re.I):
        m = re.search(r"""<div[^>]*class=['"][^'"]*cf-turnstile[^'"]*['"][^>]*data-sitekey=['"]([^'"]+)['"]""", html, re.I)
        if m: return "turnstile", m.group(1)
        m = re.search(r"""data-sitekey=['"]([^'"]+)['"]""", html)
        if m: return "turnstile", m.group(1)
        return "turnstile", FALLBACK_SITEKEY
    return "", ""

# ═══════════════════ WARYONO ═══════════════════
def check_balance(api_key):
    try:
        r = requests.get(f"{WARYONO_BALANCE_URL}?apikey={api_key}", timeout=10)
        res = r.json()
        if res.get("status") == 1:
            return float(res.get("balance", 0))
        return None
    except Exception:
        return None

def solve_captcha(api_key, kind, page_url, sitekey):
    log("captcha", f"Submit {kind} (sitekey={sitekey[:14]}...)", YELLOW)
    payload = {
        "apikey": api_key,
        "methods": kind,
        "domain": page_url,
        "sitekey": sitekey,
        "json": 1,
    }
    try:
        r = requests.post(WARYONO_IN_URL, json=payload, timeout=30)
        res = r.json()
        if res.get("status") != 1:
            err = res.get("request", "UNKNOWN_ERROR")
            log("captcha", f"Submit gagal: {err}", RED)
            return None

        task_id = res.get("request")
        print(f"{GRAY}[{now()}]{RESET} {YELLOW}[CAPTCHA]{RESET} Task ID: {task_id}")

        start = time.time()
        for idx in range(120):
            time.sleep(3)
            elapsed = int(time.time() - start)
            sys.stdout.write(f"\r{GRAY}[{now()}]{RESET} {YELLOW}[CAPTCHA]{RESET} Polling{'.' * (idx % 4)}{' ' * (3 - idx % 4)} {elapsed}s ")
            sys.stdout.flush()

            try:
                poll = requests.get(
                    f"{WARYONO_RES_URL}?apikey={api_key}&id={task_id}&action=get&json=1",
                    timeout=30,
                )
                p_res = poll.json()
            except Exception:
                continue

            if p_res.get("status") == 1:
                print(f"\r{GRAY}[{now()}]{RESET} {GREEN}[CAPTCHA]{RESET} ✔ Solved ({elapsed}s){' ' * 30}")
                return p_res.get("request")
            elif "CAPCHA_NOT_READY" in str(p_res.get("request")).upper():
                continue
            else:
                print(f"\r{GRAY}[{now()}]{RESET} {RED}[CAPTCHA]{RESET} Error: {p_res.get('request')}{' ' * 20}")
                return None

        print(f"\r{GRAY}[{now()}]{RESET} {RED}[CAPTCHA]{RESET} Timeout polling{' ' * 30}")
        return None
    except Exception as e:
        log("captcha", f"Request Error: {e}", RED)
        return None

# ═══════════════════ BOT ═══════════════════
class TapCoinBot:
    def __init__(self, cookie_str, api_key, cfg):
        self.s = requests.Session()
        self.api_key = api_key
        self.cfg = cfg
        self.setup_headers()
        self.parse_cookies(cookie_str)

    def setup_headers(self):
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/user/faucet",
        })

    def parse_cookies(self, cookie_str):
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self.s.cookies.set(k, v, domain=HOST)

    # ═══ ⚡ URL builder — direct-IP aware ═══
    def _url(self, path):
        if _DIRECT_IP_ACTIVE:
            return f"http://{HOST}{path}"
        return f"{BASE_URL}{path}"

    def _force_cookies_insecure(self):
        if not _DIRECT_IP_ACTIVE: return
        for c in list(self.s.cookies):
            try: c.secure = False
            except: pass

    def _prep_headers(self, extra=None):
        h = dict(extra or {})
        if _DIRECT_IP_ACTIVE:
            for k in ("Origin", "Referer"):
                if k in h and isinstance(h[k], str) and h[k].startswith("https://"):
                    h[k] = "http://" + h[k][8:]
        return h

    def _strip_cf_cookies_temp(self):
        if not _DIRECT_IP_ACTIVE: return {}
        cf_prefixes = ("cf_clearance", "__cf", "_cf", "cf_chl")
        saved = {}
        for c in list(self.s.cookies):
            try:
                if any(c.name.startswith(p) for p in cf_prefixes):
                    saved[c.name] = (c.value, c.domain, c.path)
                    self.s.cookies.clear(domain=c.domain, path=c.path, name=c.name)
            except: pass
        return saved

    def _restore_cf_cookies(self, saved):
        if not saved: return
        for name, (val, dom, pth) in saved.items():
            try: self.s.cookies.set(name, val, domain=dom, path=pth, secure=False)
            except: pass

    # ═══ ⚡ Universal GET wrapper (direct-IP aware) ═══
    def fetch_get(self, path, extra_headers=None):
        global _DIRECT_IP_FAILS
        h = self._prep_headers(extra_headers)
        cf_saved = self._strip_cf_cookies_temp()
        try:
            r = self.s.get(self._url(path), headers=h, timeout=30)
        except Exception as e:
            self._restore_cf_cookies(cf_saved)
            log("fetch", f"GET [{path}] err: {e}", RED)
            return None
        self._restore_cf_cookies(cf_saved)
        self._force_cookies_insecure()

        if _DIRECT_IP_ACTIVE:
            if r.status_code >= 500 or r.status_code == 403:
                _DIRECT_IP_FAILS += 1
                log("fetch", f"Origin {r.status_code} [{path}] ({_DIRECT_IP_FAILS}/{_DIRECT_IP_FAIL_LIMIT})", YELLOW)
                if r.status_code == 403:
                    save_debug(f"403_{path.replace('/','_')}.html", r.text)
                if _DIRECT_IP_FAILS >= _DIRECT_IP_FAIL_LIMIT:
                    _disable_direct_ip(f"{_DIRECT_IP_FAIL_LIMIT}x {r.status_code}")
            else:
                _DIRECT_IP_FAILS = 0
        return r

    # ═══ ⚡ Universal POST wrapper (direct-IP aware) ═══
    def fetch_post(self, path, data, extra_headers=None):
        global _DIRECT_IP_FAILS
        h = self._prep_headers(extra_headers)
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        if _DIRECT_IP_ACTIVE:
            h.setdefault("X-Requested-With", "XMLHttpRequest")
        cf_saved = self._strip_cf_cookies_temp()
        try:
            r = self.s.post(self._url(path), data=data, headers=h, timeout=30, allow_redirects=True)
        except Exception as e:
            self._restore_cf_cookies(cf_saved)
            log("fetch", f"POST [{path}] err: {e}", RED)
            return None
        self._restore_cf_cookies(cf_saved)
        self._force_cookies_insecure()

        if _DIRECT_IP_ACTIVE:
            if r.status_code >= 500 or r.status_code == 403:
                _DIRECT_IP_FAILS += 1
                log("fetch", f"Origin {r.status_code} [{path}] ({_DIRECT_IP_FAILS}/{_DIRECT_IP_FAIL_LIMIT})", YELLOW)
                if r.status_code == 403:
                    save_debug(f"403_post_{path.replace('/','_')}.html", r.text)
                if _DIRECT_IP_FAILS >= _DIRECT_IP_FAIL_LIMIT:
                    _disable_direct_ip(f"{_DIRECT_IP_FAIL_LIMIT}x {r.status_code}")
            else:
                _DIRECT_IP_FAILS = 0
        return r

    def get_balance(self):
        r = self.fetch_get("/user/dashboard")
        if r is None: return {"error": "fetch_fail"}
        html = r.text
        if is_cf_blocked(html): return {"error": "cf_block"}
        if "Logout" not in html: return {"error": "invalid_cookie"}

        main_match = re.search(r'Main Balance.*?<h5[^>]*>\s*([\d.,]+)', html, re.DOTALL | re.IGNORECASE)
        main = main_match.group(1) if main_match else "0.00"
        return {"main": main}

    def get_faucet_status(self):
        log("check", "Fetching faucet status...", CYAN)
        r = self.fetch_get("/user/faucet")
        if r is None: return {"error": "fetch_fail"}
        html = r.text
        if is_cf_blocked(html): return {"error": "cf_block"}
        if "Logout" not in html: return {"error": "invalid_cookie"}

        coin_ready = bool(re.search(r'getfreecoins/claim"[^>]*>\s*<span>\s*Ready To Claim!', html))
        coin_cd = "00:00"
        if not coin_ready:
            m = re.search(r'id=["\']timer1["\']>([\d:]+)<', html)
            if m: coin_cd = m.group(1)

        return {"coin": coin_ready, "coin_cd": coin_cd}

    def get_csrf(self, html):
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        if m: return m.group(1)
        for c in self.s.cookies:
            if c.name == "csrf_cookie": return c.value
        return None

    def claim_coin(self):
        tag = "coin"
        log(tag, "Starting claim for coin...", MAGENTA)

        claim_page_url = f"{BASE_URL}/user/getfreecoins/claim"
        r = self.fetch_get("/user/getfreecoins/claim")
        if r is None:
            log(tag, "Fetch claim page fail — abort", RED)
            return False

        html = r.text
        if is_cf_blocked(html):
            log(tag, "CF block — abort", RED)
            return False
        save_debug("claim_coin.html", html)

        kind, sitekey = detect_captcha(html)
        if not kind:
            swal = parse_swal(html)
            log(tag, f"Captcha gak kedetect{(' (' + swal + ')') if swal else ''}", YELLOW)
            return False

        log(tag, f"Detected: {kind.upper()} | sitekey={sitekey[:16]}...", GRAY)

        csrf = self.get_csrf(html)
        if not csrf:
            log(tag, "CSRF gak ketemu!", RED)
            return False

        captcha_token = solve_captcha(self.api_key, kind, claim_page_url, sitekey)
        if not captcha_token:
            log(tag, "Solve captcha gagal", RED)
            return False

        field = "h-captcha-response" if kind == "hcaptcha" else "cf-turnstile-response"
        data = {
            "csrf_token": csrf,
            field: captcha_token,
            "g-recaptcha-response": captcha_token,
        }

        referer = claim_page_url
        origin = BASE_URL
        if _DIRECT_IP_ACTIVE:
            referer = referer.replace("https://", "http://", 1)
            origin = origin.replace("https://", "http://", 1)

        post_headers = {"Referer": referer, "Origin": origin}

        claims_before = self.s.cookies.get("claims")

        log(tag, "POST verify...", CYAN)
        p_res = self.fetch_post("/user/getfreecoins/verify", data, extra_headers=post_headers)
        if p_res is None:
            log(tag, "POST fail — abort", RED)
            return False

        claims_after = self.s.cookies.get("claims")
        success_by_cookie = bool(claims_after) and claims_after != claims_before
        success_by_body = "Successful" in p_res.text or "success" in p_res.text.lower()

        if success_by_cookie or success_by_body:
            log(tag, f"✔ Claim coin SUCCESS!", GREEN)
            return True

        reason = parse_swal(p_res.text) or f"HTTP {p_res.status_code}"
        log(tag, f"✖ Failed: {reason}", RED)
        save_debug("fail_coin.html", p_res.text)
        return False

    # ─── SurfAds ───
    def get_surfads(self):
        r = self.fetch_get("/user/surfads")
        if r is None: return None
        html = r.text
        if is_cf_blocked(html): return None
        if "Logout" not in html: return None

        ads = []
        for m in re.finditer(r'openAd\((\d+),\s*(\d+),', html):
            ads.append({"id": m.group(1), "duration": int(m.group(2))})

        csrf = self.get_csrf(html)
        if not ads or not csrf:
            return {"ads": [], "csrf": csrf}
        return {"ads": ads, "csrf": csrf}

    def watch_surfad(self, ad_id, duration, csrf):
        log("surfad", f"Ad #{ad_id} — {duration}s", CYAN)
        for i in range(duration, 0, -1):
            sys.stdout.write(f"\r{GRAY}[{now()}] Ad #{ad_id} — {i}s...{RESET}   ")
            sys.stdout.flush()
            time.sleep(1)
        print()

        r = self.fetch_post(f"/user/surfads/claim/{ad_id}", {"csrf_token": csrf})
        if r is None:
            log("surfad", "Claim POST fail", RED)
            return None
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("success"):
                return j.get("coins", "?")
            msg = j.get("message") if isinstance(j, dict) else r.text[:120]
            log("surfad", f"✖ {msg}", RED)
            return None
        except Exception as e:
            log("surfad", f"Claim err: {e}", RED)
            return None

# ═══════════════════ MAIN ═══════════════════
def print_banner():
    clear()
    print(f"""{CYAN}{BOLD}
   ╔════════════════════════════════════════════════════╗
   ║    🪙 TAP-COIN.DE AUTO CLAIM — SOUU ENGINE  🪙     ║
   ║    ⚡ CF NUKE: Direct-IP | COIN only              ║
   ╚════════════════════════════════════════════════════╝{RESET}
    """)
    mode = f"{GREEN}⚡ DIRECT-IP ({ORIGIN_IP}:80){RESET}" if _DIRECT_IP_ACTIVE else f"{YELLOW}🛡  HTTPS + CF{RESET}"
    print(f"  {GRAY}Mode:{RESET} {mode}\n")

def main():
    global WARYONO_KEY
    _activate_direct_ip()
    print_banner()
    cfg = load_cfg()

    WARYONO_KEY = os.environ.get("WARYONO_KEY") or cfg.get("waryono_key", "")
    if not WARYONO_KEY:
        WARYONO_KEY = input(f"{YELLOW}Masukkan Waryono API Key: {RESET}").strip()
        cfg["waryono_key"] = WARYONO_KEY
        save_cfg(cfg)

    cookie_str = cfg.get("cookie", "")
    if cookie_str:
        print(f"\n{GRAY}Cookie tersimpan (ujungnya: ...{cookie_str[-20:]}){RESET}")
        if input(f"{WHITE}Pakai cookie ini? (y/n) [y]: {RESET}").strip().lower() == 'n':
            cookie_str = ""

    if not cookie_str:
        print(f"\n{CYAN}Paste Cookie dari browser:{RESET}")
        cookie_str = input(f"{YELLOW}Cookie: {RESET}").strip()
        cfg["cookie"] = cookie_str
        save_cfg(cfg)

    if not cookie_str:
        return

    bot = TapCoinBot(cookie_str, WARYONO_KEY, cfg)

    pbal = check_balance(WARYONO_KEY)
    if pbal is not None:
        print(f"{GRAY}Provider balance: {pbal}{RESET}")

    print(f"\n{MAGENTA}Bot berjalan...{RESET}")
    print(f"{GRAY}Ctrl+C untuk berhenti.{RESET}\n")

    while True:
        try:
            status = bot.get_faucet_status()

            if "error" in status:
                if status["error"] == "cf_block":
                    log("loop", "CF block. Retry 30s...", YELLOW)
                    time.sleep(30)
                    continue
                elif status["error"] == "invalid_cookie":
                    log("loop", "Cookie invalid. Stop.", RED)
                    break
                elif status["error"] == "fetch_fail":
                    log("loop", "Fetch fail. Retry 30s...", YELLOW)
                    time.sleep(30)
                    continue
                else:
                    log("loop", f"Error: {status['error']}", RED)
                    break

            bal = bot.get_balance()
            if "error" in bal:
                bal = {"main": "?"}

            c_stat = f"{GREEN}READY{RESET}" if status['coin'] else f"{YELLOW}{status['coin_cd']}{RESET}"

            print(f"\n{GRAY}[{now()}]{RESET} 💰 Balance: {AQUA}{bal['main']}{RESET} Coin")
            print(f"{GRAY}[{now()}]{RESET} ⏳ Timer : Coin [{c_stat}]\n")

            coin_sec = parse_timer_sec(status['coin_cd']) if not status['coin'] else 0

            if status["coin"]:
                bot.claim_coin()
                time.sleep(3)
                continue

            if not status["coin"]:
                surf = bot.get_surfads()
                if surf and surf.get("ads"):
                    ad = surf["ads"][0]
                    reward = bot.watch_surfad(ad["id"], ad["duration"], surf["csrf"])
                    if reward:
                        log("surfad", f"✔ +{reward} coins (#{ad['id']})", GREEN)
                        time.sleep(2)
                        continue

                if coin_sec > 0:
                    wait_time = coin_sec + 5
                else:
                    wait_time = 60

                log("wait", f"Cooldown. Tidur {wait_time}s...", CYAN)
                for i in range(wait_time, 0, -1):
                    sys.stdout.write(f"\r{GRAY}[{now()}] {i}s... (Ctrl+C){RESET}   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
                continue

            time.sleep(5)

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Dihentikan.{RESET}")
            break
        except Exception as e:
            log("loop", f"Error: {e}", RED)
            time.sleep(30)

if __name__ == "__main__":
    main()
