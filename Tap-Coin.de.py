#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  TAP-COIN.DE AUTO CLAIM — SOUU ENGINE Edition v2.4           ║
║  - Dynamic captcha detect (hcaptcha + turnstile) ✔           ║
║  - Success check via claims cookie                           ║
║  - Swal.fire error parsing                                   ║
║  - SurfAds integration                                       ║
║  - Fetch /user/{action}/claim                                ║
║  - Dynamic Sleep based on faucet timer                       ║
║  - Auto CF bypass (Seledroid) + Waryono solver               ║
║  - Clean log + polling progress                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, re, requests, subprocess, tempfile
from datetime import datetime

# ═══════════════════ NEON COLORS ═══════════════════
def _c(n): return f"\033[38;5;{n}m"
RED, GREEN, YELLOW, CYAN, MAGENTA, WHITE, GRAY, AQUA = _c(196), _c(118), _c(226), _c(51), _c(201), _c(231), _c(245), _c(87)
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"

# ═══════════════════ CONFIG ═══════════════════
BASE_URL = "https://tap-coin.de"
CONFIG_FILE = "tapcoin_config.json"

FALLBACK_SITEKEY = "0x4AAAAAAANBXFpXlg2VZfSK"

WARYONO_KEY = ""
WARYONO_IN_URL = "https://api.waryono.my.id/in.php"
WARYONO_RES_URL = "https://api.waryono.my.id/res.php"
WARYONO_BALANCE_URL = "https://api.waryono.my.id/balance.php"

DEBUG_MODE = True

SELEDROID_SCRIPT = '''\
import time, sys, json, warnings, os
warnings.filterwarnings('ignore')
os.environ["PYTHONWARNINGS"] = "ignore"
def log(msg): print(msg, file=sys.stderr)
def bypass_cf(target):
    log("Seledroid Cloudflare...")
    _stderr_backup = sys.stderr
    _devnull = open(os.devnull, 'w')
    sys.stderr = _devnull
    try:
        from seledroid import webdriver as sd
    except ImportError:
        sys.stderr = _stderr_backup; _devnull.close()
        log("install Seledroid module and Apk"); sys.exit(1)
    finally:
        sys.stderr = _stderr_backup
        try: _devnull.close()
        except: pass
    time.sleep(3)
    try:
        d = sd.Chrome(gui=True, pip_mode=False)
        d.get(target); time.sleep(10)
        clr = None
        for _ in range(15):
            clr = d.get_cookie("cf_clearance")
            if clr: break
            time.sleep(5)
        try: ua = d.user_agent
        except:
            try: ua = d.execute_script("return navigator.userAgent;")
            except: ua = None
        try: d.close()
        except: pass
    except Exception as e:
        log(f"Failed ({e})"); return {"cf_clearance": None, "user_agent": None}
    if not clr:
        log("Failed (no cf_clearance)"); return {"cf_clearance": None, "user_agent": None}
    tok = clr.split('=', 1)[1] if '=' in clr else clr
    log("Success!")
    return {"cf_clearance": tok, "user_agent": ua}
if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    print(json.dumps(bypass_cf(sys.argv[1])))
'''

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
            with open(filename, "w", encoding="utf-8") as f: f.write(content)
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

# ═══════════════════ CAPTCHA DETECT ═══════════════════
def detect_captcha(html):
    """Return (kind, sitekey). Support hcaptcha + turnstile."""
    if not html:
        return "", ""

    # ── hCaptcha ──
    # Pola 1: class="h-captcha" dengan single/double quote, urutan class → data-sitekey
    m = re.search(
        r"""<div[^>]*class=['"][^'"]*h-captcha[^'"]*['"][^>]*data-sitekey=['"]([^'"]+)""",
        html, re.I,
    )
    if m:
        return "hcaptcha", m.group(1)

    # Pola 2: data-sitekey muncul dulu baru class
    m = re.search(
        r"""<div[^>]*data-sitekey=['"]([^'"]+)['"][^>]*class=['"][^'"]*h-captcha[^'"]*['"]""",
        html, re.I,
    )
    if m:
        return "hcaptcha", m.group(1)

    # ── Turnstile ──
    if re.search(r"""<div[^>]*class=['"][^'"]*cf-turnstile""", html, re.I):
        # data-sitekey di tag yang sama
        m = re.search(r"""<div[^>]*class=['"][^'"]*cf-turnstile[^'"]*['"][^>]*data-sitekey=['"]([^'"]+)['"]""", html, re.I)
        if m: return "turnstile", m.group(1)
        # fallback: ambil data-sitekey manapun di HTML
        m = re.search(r"""data-sitekey=['"]([^'"]+)['"]""", html)
        if m: return "turnstile", m.group(1)
        return "turnstile", FALLBACK_SITEKEY

    return "", ""

# ═══════════════════ SELEDROID WRAPPER ═══════════════════
def run_seledroid(target_url):
    log("seledroid", "Bypass Cloudflare via browser (30-90s)...", CYAN)
    tmp = os.path.join(tempfile.gettempdir(), f"sd_{int(time.time())}.py")
    try:
        with open(tmp, "w", encoding="utf-8") as f: f.write(SELEDROID_SCRIPT)
    except Exception as e:
        log("seledroid", f"Gagal bikin tmp: {e}", RED)
        return None

    python_bin = "python" if os.name == "nt" else "python3"
    try:
        proc = subprocess.run([python_bin, tmp, target_url], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        log("seledroid", "Timeout (180s)", RED)
        return None
    except Exception as e:
        log("seledroid", f"Spawn err: {e}", RED)
        return None
    finally:
        try: os.remove(tmp)
        except: pass

    if proc.returncode != 0:
        log("seledroid", f"Exit {proc.returncode}: {proc.stderr.strip()[:100]}", RED)
        return None

    out = proc.stdout.strip()
    if not out:
        log("seledroid", "Output kosong", RED)
        return None

    try:
        data = json.loads(out)
        if not data.get("cf_clearance"):
            log("seledroid", "Gagal dapat cf_clearance", RED)
            return None
        log("seledroid", "✔ cf_clearance baru!", GREEN)
        return data
    except Exception as e:
        log("seledroid", f"JSON Error: {e}", RED)
        return None

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

        # polling dengan progress dots
        start = time.time()
        for idx in range(120):  # max 120 * 3s = 6 menit
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
            except Exception as e:
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
                self.s.cookies.set(k, v, domain="tap-coin.de")

    def refresh_cf_cookie(self):
        log("bypass", "Memicu Seledroid...", MAGENTA)
        res = run_seledroid(BASE_URL)
        if not res: return False

        self.s.cookies.set("cf_clearance", res["cf_clearance"], domain="tap-coin.de")
        if res.get("user_agent"):
            self.s.headers["User-Agent"] = res["user_agent"]

        old = self.cfg.get("cookie", "")
        parts = [p.strip() for p in old.split(";") if "cf_clearance=" not in p and p.strip()]
        parts.append(f"cf_clearance={res['cf_clearance']}")
        self.cfg["cookie"] = "; ".join(parts)
        save_cfg(self.cfg)
        log("bypass", "✓ cookie updated", GREEN)
        return True

    def get_balance(self):
        try:
            r = self.s.get(f"{BASE_URL}/user/dashboard", timeout=30)
            html = r.text
            if is_cf_blocked(html):
                if self.refresh_cf_cookie():
                    html = self.s.get(f"{BASE_URL}/user/dashboard", timeout=30).text
                    if is_cf_blocked(html): return {"error": "cf_block"}
                else:
                    return {"error": "cf_block"}

            if "Logout" not in html:
                return {"error": "invalid_cookie"}

            main_match = re.search(r'Main Balance.*?<h5[^>]*>\s*([\d.,]+)', html, re.DOTALL | re.IGNORECASE)
            adcoin_match = re.search(r'Purchase Balance.*?<h4[^>]*>\s*([\d.,]+)', html, re.DOTALL | re.IGNORECASE)

            main = main_match.group(1) if main_match else "0.00"
            adcoin = adcoin_match.group(1) if adcoin_match else "0"
            return {"main": main, "adcoin": adcoin}
        except Exception:
            return {"error": "network"}

    def get_faucet_status(self):
        log("check", "Fetching faucet status...", CYAN)
        try:
            r = self.s.get(f"{BASE_URL}/user/faucet", timeout=30)
            html = r.text

            if is_cf_blocked(html):
                if self.refresh_cf_cookie():
                    html = self.s.get(f"{BASE_URL}/user/faucet", timeout=30).text
                    if is_cf_blocked(html): return {"error": "cf_block"}
                else:
                    return {"error": "cf_block"}

            if "Logout" not in html:
                return {"error": "invalid_cookie"}

            coin_ready = bool(re.search(r'getfreecoins/claim"[^>]*>\s*<span>\s*Ready To Claim!', html))
            coin_cd = "00:00"
            if not coin_ready:
                m = re.search(r'id=["\']timer1["\']>([\d:]+)<', html)
                if m: coin_cd = m.group(1)

            adcoin_ready = bool(re.search(r'getfreeadcoins/claim"[^>]*>\s*<span>\s*Ready To Claim!', html))
            adcoin_cd = "00:00"
            if not adcoin_ready:
                m = re.search(r'id=["\']timer2["\']>([\d:]+)<', html)
                if m: adcoin_cd = m.group(1)
                else:
                    m = re.search(r'getfreeadcoins/claim.*?Claim again in.*?([\d:]+)', html, re.DOTALL)
                    if m: adcoin_cd = m.group(1)

            return {
                "coin": coin_ready, "coin_cd": coin_cd,
                "adcoin": adcoin_ready, "adcoin_cd": adcoin_cd,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_csrf(self, html):
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        if m: return m.group(1)
        for c in self.s.cookies:
            if c.name == "csrf_cookie": return c.value
        return None

    def claim(self, faucet_type="coin"):
        action = "getfreecoins" if faucet_type == "coin" else "getfreeadcoins"
        tag = faucet_type
        log(tag, f"Starting claim for {faucet_type}...", MAGENTA)

        claim_page_url = f"{BASE_URL}/user/{action}/claim"
        try:
            r = self.s.get(claim_page_url, timeout=30)
        except Exception as e:
            log(tag, f"Fetch claim page error: {e}", RED)
            return False

        if is_cf_blocked(r.text):
            if not self.refresh_cf_cookie():
                log(tag, "CF block — abort", RED)
                return False
            r = self.s.get(claim_page_url, timeout=30)
            if is_cf_blocked(r.text):
                log(tag, "CF block after retry — abort", RED)
                return False

        html = r.text
        save_debug(f"claim_{faucet_type}.html", html)

        # Detect captcha
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

        # Solve
        captcha_token = solve_captcha(self.api_key, kind, claim_page_url, sitekey)
        if not captcha_token:
            log(tag, "Solve captcha gagal", RED)
            return False

        # Build payload
        field = "h-captcha-response" if kind == "hcaptcha" else "cf-turnstile-response"
        data = {
            "csrf_token": csrf,
            field: captcha_token,
            "g-recaptcha-response": captcha_token,
        }

        self.s.headers["Referer"] = claim_page_url
        post_url = f"{BASE_URL}/user/{action}/verify"

        claims_before = self.s.cookies.get("claims")

        log(tag, "POST verify...", CYAN)
        try:
            p_res = self.s.post(post_url, data=data, timeout=30, allow_redirects=True)
        except Exception as e:
            log(tag, f"POST error: {e}", RED)
            return False

        claims_after = self.s.cookies.get("claims")
        success_by_cookie = bool(claims_after) and claims_after != claims_before
        success_by_body = "Successful" in p_res.text or "success" in p_res.text.lower()

        if success_by_cookie or success_by_body:
            log(tag, f"✔ Claim {faucet_type} SUCCESS!", GREEN)
            return True

        reason = parse_swal(p_res.text) or f"HTTP {p_res.status_code}"
        log(tag, f"✖ Failed: {reason}", RED)
        save_debug(f"fail_{faucet_type}.html", p_res.text)
        return False

    # ─── SurfAds ───
    def get_surfads(self):
        try:
            r = self.s.get(f"{BASE_URL}/user/surfads", timeout=30)
            if is_cf_blocked(r.text):
                if not self.refresh_cf_cookie():
                    return None
                r = self.s.get(f"{BASE_URL}/user/surfads", timeout=30)
                if is_cf_blocked(r.text):
                    return None

            html = r.text
            if "Logout" not in html:
                return None

            ads = []
            for m in re.finditer(r'openAd\((\d+),\s*(\d+),', html):
                ads.append({"id": m.group(1), "duration": int(m.group(2))})

            csrf = self.get_csrf(html)
            if not ads or not csrf:
                return {"ads": [], "csrf": csrf}

            return {"ads": ads, "csrf": csrf}
        except Exception as e:
            log("surfad", f"get_surfads err: {e}", RED)
            return None

    def watch_surfad(self, ad_id, duration, csrf):
        log("surfad", f"Ad #{ad_id} — {duration}s", CYAN)
        for i in range(duration, 0, -1):
            sys.stdout.write(f"\r{GRAY}[{now()}] Ad #{ad_id} — {i}s...{RESET}   ")
            sys.stdout.flush()
            time.sleep(1)
        print()

        try:
            r = self.s.post(
                f"{BASE_URL}/user/surfads/claim/{ad_id}",
                data={"csrf_token": csrf},
                timeout=30,
            )
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
   ║    Captcha: hcaptcha + turnstile (auto-detect)     ║
   ╚════════════════════════════════════════════════════╝{RESET}
    """)

def main():
    global WARYONO_KEY
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

    print(f"\n{MAGENTA}Bot berjalan...{RESET}")
    print(f"{GRAY}Ctrl+C untuk berhenti.{RESET}\n")

    while True:
        try:
            status = bot.get_faucet_status()

            if "error" in status:
                if status["error"] == "cf_block":
                    log("loop", "CF block. Stop.", RED)
                elif status["error"] == "invalid_cookie":
                    log("loop", "Cookie invalid. Stop.", RED)
                else:
                    log("loop", f"Error: {status['error']}", RED)
                break

            bal = bot.get_balance()
            if "error" in bal:
                bal = {"main": "?", "adcoin": "?"}

            c_stat = f"{GREEN}READY{RESET}" if status['coin'] else f"{YELLOW}{status['coin_cd']}{RESET}"
            ac_stat = f"{GREEN}READY{RESET}" if status['adcoin'] else f"{YELLOW}{status['adcoin_cd']}{RESET}"

            print(f"\n{GRAY}[{now()}]{RESET} 💰 Balance: {AQUA}{bal['main']}{RESET} Coin | {AQUA}{bal['adcoin']}{RESET} AdCoin")
            print(f"{GRAY}[{now()}]{RESET} ⏳ Timer : Coin [{c_stat}] | AdCoin [{ac_stat}]\n")

            coin_sec = parse_timer_sec(status['coin_cd']) if not status['coin'] else 0
            adcoin_sec = parse_timer_sec(status['adcoin_cd']) if not status['adcoin'] else 0

            if status["coin"]:
                bot.claim("coin")
                time.sleep(3)
            if status["adcoin"]:
                bot.claim("adcoin")
                time.sleep(3)

            if not status["coin"] and not status["adcoin"]:
                surf = bot.get_surfads()
                if surf and surf.get("ads"):
                    ad = surf["ads"][0]
                    reward = bot.watch_surfad(ad["id"], ad["duration"], surf["csrf"])
                    if reward:
                        log("surfad", f"✔ +{reward} coins (#{ad['id']})", GREEN)
                        time.sleep(2)
                        continue

                if coin_sec > 0 and adcoin_sec > 0:
                    wait_time = min(coin_sec, adcoin_sec) + 5
                elif coin_sec > 0:
                    wait_time = coin_sec + 5
                elif adcoin_sec > 0:
                    wait_time = adcoin_sec + 5
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
