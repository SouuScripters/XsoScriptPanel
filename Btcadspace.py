#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCadSpace Bot - Single Account, Cookie Auth + YouTube Videos
Fixed by MoneyMaker_w
Butuh: pip install curl_cffi
"""

import json, time, re, sys, os, random, threading
from datetime import datetime
from urllib.parse import urlparse

try:
    from curl_cffi import requests
except ImportError:
    print("Install dulu: pip install curl_cffi")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
HOST              = "https://btcadspace.com"

WARYONO_IN        = "https://api.waryono.my.id/in.php"
WARYONO_RES       = "https://api.waryono.my.id/res.php"
WARYONO_BALANCE   = "https://api.waryono.my.id/balance.php"

TURNSTILE_SITEKEY = "0x4AAAAAAAB-TZt_lwYtViEL"

AVISO_API         = "https://aviso.bz/api/v1"
AVISO_API_KEY     = "ak_87e52f3d03d99fbb11505fc3ec24b881dddfb42e"

CONFIG_FILE       = "config.json"

MAX_RETRY         = 3
FAUCET_COOLDOWN   = 300
DEBUG_COOKIE      = False

DEF_UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36")

# ═══════════════════════════════════════════════════════════════
# NEON COLORS
# ═══════════════════════════════════════════════════════════════
RST   = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

# Neon (bright ANSI)
NEON_PINK     = "\033[38;5;205m"   # hot pink
NEON_CYAN     = "\033[38;5;51m"    # bright cyan
NEON_GREEN    = "\033[38;5;46m"    # neon green
NEON_YELLOW   = "\033[38;5;226m"   # bright yellow
NEON_ORANGE   = "\033[38;5;208m"   # orange
NEON_PURPLE   = "\033[38;5;141m"   # light purple
NEON_BLUE     = "\033[38;5;45m"    # electric blue
NEON_RED      = "\033[38;5;196m"   # bright red
NEON_WHITE    = "\033[38;5;231m"   # pure white
NEON_MAGENTA  = "\033[38;5;201m"   # magenta

# Aliases
GRN = NEON_GREEN
RED = NEON_RED
YEL = NEON_YELLOW
CYN = NEON_CYAN
WHT = NEON_WHITE
MAG = NEON_MAGENTA
BLU = NEON_BLUE
PINK = NEON_PINK
ORG = NEON_ORANGE
PUR = NEON_PURPLE

CLR = "\r\033[2K"

_HARD_ERR = object()

# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════
def clear():
    os.system('clear' if os.name == 'posix' else 'cls')


def mask_email(email):
    if not email or '@' not in email:
        return email or "?"
    user, domain = email.split('@', 1)
    if len(user) <= 4:
        return user[:1] + "****@" + domain
    return user[:2] + "****" + user[-2:] + "@" + domain


def log(msg, tag="i", end="\n"):
    icons = {
        "i":  f"{NEON_CYAN}»{RST}",
        "ok": f"{NEON_GREEN}✓{RST}",
        "er": f"{NEON_RED}✗{RST}",
        "wr": f"{NEON_YELLOW}⚠{RST}",
        "in": f"{NEON_BLUE}●{RST}",
        "bi": f"{NEON_GREEN}₹{RST}",
        "yt": f"{NEON_PINK}▶{RST}",
        "sf": f"{NEON_PURPLE}◆{RST}",
        "fa": f"{NEON_ORANGE}⛲{RST}",
    }
    icon = icons.get(tag, f"{NEON_CYAN}»{RST}")
    ts = datetime.now().strftime("%H:%M:%S")
    sys.stdout.write(CLR + f"{NEON_PURPLE}[{ts}]{RST} {icon} {msg}")
    if end:
        sys.stdout.write(end)
    sys.stdout.flush()


def tmr(seconds, label="Countdown"):
    symbols   = list(reversed(['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘']))
    spinners  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
    dots      = ['▪', '▪▪', '▪▪▪', '▪▪▪▪']
    total = int(seconds)
    if total < 1:
        return
    start = time.time()
    i = 0
    while True:
        elapsed = int(time.time() - start)
        remaining = max(0, total - elapsed)
        pct = round(((total - remaining) / total) * 100)
        mm, ss = divmod(remaining, 60)
        symbol = symbols[i % len(symbols)]
        sp     = spinners[i % len(spinners)]
        dot    = dots[elapsed % len(dots)]
        i += 1
        # Neon color cycling
        cols = [NEON_CYAN, NEON_PINK, NEON_GREEN, NEON_YELLOW, NEON_PURPLE, NEON_BLUE]
        c1 = cols[i % len(cols)]
        c2 = cols[(i + 3) % len(cols)]
        sys.stdout.write(
            f"{CLR} {c1}{BOLD}{sp}{RST} {NEON_WHITE}{label} "
            f"{NEON_RED}{mm:02d}:{ss:02d}{RST} {c2}{symbol}"
            f" {NEON_WHITE}{pct}%{RST} {NEON_YELLOW}{dot}{RST}")
        sys.stdout.flush()
        if remaining <= 0:
            break
        time.sleep(0.1)
    sys.stdout.write(CLR); sys.stdout.flush()


def parse_proxy(raw):
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    if "://" in s:
        if s.startswith(("socks5://", "socks5h://", "http://", "https://")):
            return {"http": s, "https": s}
        return None
    if "@" in s:
        return {"http": "socks5h://" + s, "https": "socks5h://" + s}
    parts = s.split(":")
    if len(parts) == 4:
        ip, port, user, pwd = parts
        if not port.isdigit():
            return None
        return {"http": f"socks5h://{user}:{pwd}@{ip}:{port}",
                "https": f"socks5h://{user}:{pwd}@{ip}:{port}"}
    if len(parts) == 2:
        ip, port = parts
        if not port.isdigit():
            return None
        return {"http": f"socks5h://{ip}:{port}", "https": f"socks5h://{ip}:{port}"}
    return None


def parse_cookie_string(raw):
    out = {}
    if not raw:
        return out
    if isinstance(raw, dict):
        return {k: str(v) for k, v in raw.items()}

    raw = raw.strip()

    if "\t" in raw and "=" not in raw.split("\n")[0]:
        for line in raw.split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0] and parts[1]:
                out[parts[0].strip()] = parts[1].strip()
        if out:
            return out

    raw = raw.replace("\n", ";").replace("\r", "")
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


# ═══════════════════════════════════════════════════════════════
# SESSION / REQUEST
# ═══════════════════════════════════════════════════════════════
def build_session(cookies_dict, proxy_raw=None):
    try:
        s = requests.Session(impersonate="chrome124")
    except Exception:
        s = requests.Session(impersonate="chrome120")
    s.verify = False

    proxy_dict = parse_proxy(proxy_raw)
    if proxy_dict:
        s.proxies = proxy_dict

    for k, v in (cookies_dict or {}).items():
        try:
            if k in ("cf_clearance", "remember_token"):
                s.cookies.set(k, v, domain="btcadspace.com", secure=True)
            else:
                s.cookies.set(k, v, domain="btcadspace.com")
        except Exception:
            try:
                s.cookies.set(k, v)
            except Exception:
                pass
    return s


def base_headers():
    return {
        "user-agent": DEF_UA,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "id-ID,id;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "upgrade-insecure-requests": "1",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
    }


def safe_request(sess, url, method='GET', data=None, headers=None,
                 allow_redirects=True):
    attempt = 0
    while True:
        attempt += 1
        try:
            opts = {"timeout": 45, "allow_redirects": allow_redirects}
            if headers:
                opts["headers"] = headers
            if method == 'POST':
                r = sess.post(url, data=data, **opts)
            else:
                r = sess.get(url, **opts)
            return r.text, r.status_code, getattr(r, "url", url)
        except Exception as e:
            msg = str(e)
            if "proxy" in msg.lower() or "unsupported" in msg.lower():
                sys.stdout.write(CLR)
                print(f"{NEON_RED}✗ ERROR PROXY: {msg}{RST}")
                sys.stdout.flush()
                raise
            sys.stdout.write(CLR + f"{NEON_YELLOW}⚠ [NET] gagal (#{attempt}): {msg[:70]}, retry 8s...{RST}")
            sys.stdout.flush()
            time.sleep(8)


# ═══════════════════════════════════════════════════════════════
# WARYONO SOLVER
# ═══════════════════════════════════════════════════════════════
WARYONO_ERRORS = {
    "ERROR_WRONG_USER_KEY":        "API key salah",
    "ERROR_BANNED":                "Akun diblokir",
    "ERROR_ZERO_BALANCE":          "Saldo habis (topup dulu)",
    "ERROR_METHOD_DOES_NOT_EXIST": "Method tidak dikenal",
    "ERROR_BAD_DATA":              "Parameter tidak valid (refunded)",
    "ERROR_SOLVER_FAILED":         "Solver gagal solve (refunded)",
    "ERROR_NO_SUCH_ID":            "Task ID tidak dikenal",
    "ERROR_CAPTCHA_UNSOLVABLE":    "Task timeout (refunded)",
    "ERROR_RATE_LIMIT":            "Rate limit — slot penuh",
    "CAPCHA_NOT_READY":            "Masih solving — poll lagi",
}

_TRANSIENT_ERR_KEYS = ("UNSOLVABLE", "TIMEOUT", "CAPCHA_NOT_READY", "NO_SLOT")


def _is_transient_err(msg):
    if not msg:
        return False
    up = msg.upper()
    return any(k in up for k in _TRANSIENT_ERR_KEYS)


def _classify_waryono_error(msg):
    if not msg:
        return ""
    m = msg.upper()
    for code, desc in WARYONO_ERRORS.items():
        if code in m:
            return f"{code} ({desc})"
    return ""


def _solve_waryono_common(apikey, label, submit_fn, parse_fn,
                          timeout=180, poll_interval=2.5):
    task_id = submit_fn()
    if not task_id:
        return None
    if task_id.upper().startswith("ERROR"):
        if _is_transient_err(task_id):
            return None
        err_desc = _classify_waryono_error(task_id)
        log(f"Solver submit: {err_desc or task_id}", "er")
        return _HARD_ERR

    state = {"data": None, "done": True}
    stop_flag = {"stop": False}

    def bg_poll():
        while not stop_flag["stop"]:
            try:
                pr = requests.get(
                    WARYONO_RES,
                    params={"apikey": apikey, "action": "get",
                            "id": task_id, "json": 1},
                    impersonate="chrome124", timeout=10)
                state["data"] = pr.json()
            except Exception:
                state["data"] = None
            state["done"] = True
            time.sleep(poll_interval)

    t = threading.Thread(target=bg_poll, daemon=True)
    t.start()

    start = time.time()
    i = 0
    result = None
    try:
        while True:
            elapsed = int(time.time() - start)
            if elapsed > timeout:
                break
            remaining = max(0, timeout - elapsed)
            pct = round(((timeout - remaining) / timeout) * 100)
            mm, ss = divmod(elapsed, 60)
            sp = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾'][i % 8]
            cols = [NEON_CYAN, NEON_PINK, NEON_GREEN, NEON_YELLOW, NEON_PURPLE, NEON_BLUE]
            c = cols[i % len(cols)]
            sys.stdout.write(f"{CLR} {c}{BOLD}{sp}{RST} {NEON_WHITE}{label} {NEON_RED}{mm:02d}:{ss:02d}{RST} {NEON_GREEN}{pct}%{RST}")
            sys.stdout.flush()
            i += 1
            if state["done"] and state["data"] is not None:
                state["done"] = False
                parsed = parse_fn(state["data"])
                kind = parsed[0]
                if kind == "ok":
                    result = ("ok", parsed[1], elapsed); break
                elif kind == "err":
                    result = ("err", parsed[1], elapsed); break
            time.sleep(0.1)
    finally:
        stop_flag["stop"] = True
        sys.stdout.write(CLR); sys.stdout.flush()

    if result and result[0] == "ok":
        log(f"Solved ({result[2]}s)", "ok")
        return result[1]
    if result and result[0] == "err":
        err_msg = result[1] or ""
        if _is_transient_err(err_msg):
            return None
        err_desc = _classify_waryono_error(err_msg)
        log(f"Solver: {err_desc or err_msg}", "er")
        return _HARD_ERR
    return None


def _parse_turnstile_resp(d):
    if not isinstance(d, dict):
        return ("wait", None)
    if d.get("status") == 1 and d.get("request") is not None:
        tok = str(d["request"]).strip()
        if tok:
            return ("ok", tok)
    msg = str(d.get("request", ""))
    if msg and "CAPCHA_NOT_READY" not in msg.upper():
        err = _classify_waryono_error(msg)
        if err:
            return ("err", msg)
    return ("wait", None)


def _parse_antibot_resp(d):
    if not isinstance(d, dict):
        return ("wait", None)
    if d.get("status") == 1 and d.get("request") is not None:
        ans = str(d["request"]).strip()
        if ans:
            return ("ok", ans)
    msg = str(d.get("request", ""))
    if msg and "CAPCHA_NOT_READY" not in msg.upper():
        err = _classify_waryono_error(msg)
        if err:
            return ("err", msg)
    return ("wait", None)


def solve_turnstile(apikey, sitekey, pageurl, label="[CAPTCHA]"):
    if not apikey:
        log(f"{label} apikey kosong", "er")
        return _HARD_ERR

    parsed = urlparse(pageurl)
    domain = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else pageurl

    def submit():
        try:
            r = requests.post(WARYONO_IN, json={
                "apikey":  apikey,
                "methods": "turnstile",
                "domain":  domain,
                "sitekey": sitekey,
                "json":    1,
            }, impersonate="chrome124", timeout=20)
            d = r.json()
        except Exception:
            return None
        if not isinstance(d, dict) or d.get("status") != 1:
            return None
        return str(d.get("request", "")) or None

    while True:
        token = _solve_waryono_common(apikey, f"{label} Solve",
                                      submit, _parse_turnstile_resp)
        if token is _HARD_ERR:
            return _HARD_ERR
        if token:
            return token
        time.sleep(1)


def _submit_antibot(apikey, main_b64, options_b64, method="antibot"):
    try:
        payload = {
            "apikey":  apikey,
            "methods": method,
            "main":    main_b64,
            "json":    1,
        }
        for i, opt in enumerate(options_b64[:4], 1):
            payload[f"param{i}"] = opt

        r = requests.post(WARYONO_IN, json=payload,
                          impersonate="chrome124", timeout=20)
        d = r.json()
    except Exception:
        return None
    if not isinstance(d, dict) or d.get("status") != 1:
        return None
    return str(d.get("request", "")) or None


def solve_antibot(apikey, main_b64, options_b64, label="[ANTIBOT]"):
    if not main_b64 or not options_b64:
        return None
    if not apikey:
        log(f"{label} apikey kosong", "er")
        return _HARD_ERR

    main_b64 = re.sub(r'\s+', '', main_b64)
    options_b64 = [re.sub(r'\s+', '', o) for o in options_b64]

    while True:
        ans = _solve_waryono_common(
            apikey, f"{label} Solve",
            lambda: _submit_antibot(apikey, main_b64, options_b64, "antibot"),
            _parse_antibot_resp)
        if ans is _HARD_ERR:
            log(f"{label} fallback ke antibotv2...", "wr")
            while True:
                ans2 = _solve_waryono_common(
                    apikey, f"{label}v2 Solve",
                    lambda: _submit_antibot(apikey, main_b64, options_b64, "antibotv2"),
                    _parse_antibot_resp)
                if ans2 is _HARD_ERR:
                    return _HARD_ERR
                if ans2:
                    return ans2
                time.sleep(1)
        if ans:
            return ans
        time.sleep(1)


# ═══════════════════════════════════════════════════════════════
# HTML PARSERS
# ═══════════════════════════════════════════════════════════════
def parse_csrf(html):
    for pat in [r'name="csrf_token"\s+value="([^"]+)"',
                r'<meta\s+name="csrf-token"\s+content="([^"]+)"']:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def parse_sitekey(html):
    for pat in [r'data-sitekey="([^"]+)"',
                r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)']:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def parse_user_hash(html):
    for pat in [r'data-user-hash="([a-f0-9]{64})"',
                r'user_hash["\']?\s*[:=]\s*["\']([a-f0-9]{64})',
                r'ext_user_id["\']?\s*[:=]\s*["\']([a-f0-9]{32,64})']:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def parse_balance(html):
    if not html:
        return None
    def _to_int(s):
        try:
            return int(float(str(s).replace(",", "").strip()))
        except Exception:
            return None
    m = re.search(
        r'<span\s+id="balance"[^>]*>\s*([\d,\.]+)\s*(?:Coins?|coins?)\s*</span>',
        html, re.I)
    if m:
        v = _to_int(m.group(1))
        if v is not None:
            return v
    m = re.search(r'<span\s+id="balance"[^>]*>\s*([\d,\.]+)', html, re.I)
    if m:
        v = _to_int(m.group(1))
        if v is not None:
            return v
    return None


def parse_notyf(html):
    if not html:
        return (None, None)
    m = re.search(
        r"notyf\.open\s*\(\s*\{\s*type\s*:\s*['\"](\w+)['\"]\s*,\s*"
        r"message\s*:\s*['\"]([^'\"]+)['\"]",
        html, re.DOTALL)
    if m:
        ntype = m.group(1).lower()
        nmsg = m.group(2)
        nmsg = re.sub(r'\\u([0-9a-fA-F]{4})',
                      lambda x: chr(int(x.group(1), 16)), nmsg)
        nmsg = nmsg.replace("\\'", "'").replace('\\"', '"').replace("\\n", " ")
        return (ntype, nmsg.strip())
    return (None, None)


def parse_ablinks(html):
    main_b64 = None
    m = re.search(
        r'class="alert\s+alert-warning"[^>]*>.*?'
        r'<img\s+src="data:image/[^;]+;base64,([^"]+)"',
        html, re.DOTALL)
    if m:
        main_b64 = m.group(1)

    m = re.search(r'var\s+ablinks\s*=\s*(\[.*?\])\s*;', html, re.DOTALL)
    if not m:
        return main_b64, [], []

    js = m.group(1).replace('\\"', '"').replace('\\/', '/')

    entries = re.findall(
        r'rel="(\d+)"[^>]*>.*?<img\s+src="data:image/[^;]+;base64,([^"]+)"',
        js, re.DOTALL)

    if not entries:
        entries = re.findall(
            r'rel="(\d+)"[^>]*?src="data:image/[^;]+;base64,([^"]+)"',
            js, re.DOTALL)

    if not entries:
        rels = re.findall(r'rel="(\d+)"', js)
        b64s = re.findall(r'src="data:image/[^;]+;base64,([^"]+)"', js)
        if not b64s:
            b64s = re.findall(r'data:image/[^;]+;base64,([^"]+)', js)
        if len(rels) == len(b64s) and len(rels) > 0:
            entries = list(zip(rels, b64s))

    if not entries:
        return main_b64, [], []

    rel_ids = [e[0] for e in entries]
    options = [e[1] for e in entries]
    return main_b64, options, rel_ids


def parse_surf_ads(html):
    ads = []
    pattern = re.compile(
        r'<a\s+href="/surf/([a-f0-9]{32})"\s+class="([^"]*)"[^>]*>\s*'
        r'(.*?)</a>',
        re.DOTALL)
    for m in pattern.finditer(html):
        uid = m.group(1)
        classes = m.group(2)
        inner = m.group(3)
        if 'd-none' in classes:
            continue
        title_m = re.search(r'<span class="fw-bold">([^<]+)</span>', inner)
        coins_m = re.search(r'<i class="far fa-coins"></i>\s*(\d+)\s*Coins', inner)
        dur_m   = re.search(r'<i class="far fa-stopwatch"></i>\s*(\d+)\s*seconds', inner)
        if not (title_m and coins_m and dur_m):
            continue
        ads.append({
            "uid": uid,
            "title": title_m.group(1).strip(),
            "coins": int(coins_m.group(1)),
            "duration": int(dur_m.group(1)),
        })
    return ads


def is_logged_in(html):
    if not html:
        return False
    h = html.lower()
    return ('logout' in h) and ('/login' not in h or 'name="password"' not in h)


# ═══════════════════════════════════════════════════════════════
# ACCOUNT CHECK / BALANCE
# ═══════════════════════════════════════════════════════════════
def check_session(sess):
    try:
        html, code, final_url = safe_request(
            sess, f"{HOST}/account", headers=base_headers())
    except Exception as e:
        log(f"[DEBUG] Request error: {e}", "er")
        return False, None

    if DEBUG_COOKIE:
        print(f"\n{NEON_WHITE}[DEBUG] code={code}{RST}")
        print(f"{NEON_WHITE}[DEBUG] final_url={final_url}{RST}")
        print(f"{NEON_WHITE}[DEBUG] html_len={len(html) if html else 0}{RST}")
        if html:
            low = html.lower()
            if "just a moment" in low or "challenge-platform" in low or "cf-chl" in low:
                print(f"{NEON_RED}[DEBUG] ⚠ Cloudflare challenge detected{RST}")
            elif 'name="password"' in low and "/login" in final_url:
                print(f"{NEON_YELLOW}[DEBUG] ⚠ Redirect /login — cookie expired{RST}")
            elif "logout" in low:
                print(f"{NEON_GREEN}[DEBUG] ✓ Session OK{RST}")
        print()

    if "/login" in final_url or not is_logged_in(html):
        return False, html
    return True, html


def get_balance(sess):
    for _ in range(3):
        try:
            html, _, _ = safe_request(
                sess, f"{HOST}/account", headers=base_headers())
            bal = parse_balance(html)
            if bal is not None:
                return bal
        except Exception:
            pass
        time.sleep(1)
    return None


# ═══════════════════════════════════════════════════════════════
# FAUCET
# ═══════════════════════════════════════════════════════════════
def do_faucet(sess, apikey):
    html, _, _ = safe_request(sess, f"{HOST}/faucet", headers=base_headers())
    if not is_logged_in(html):
        return -1

    csrf = parse_csrf(html)
    if not csrf:
        log("[FAUCET] csrf token gak ada", "wr")
        return 0

    sitekey = parse_sitekey(html) or TURNSTILE_SITEKEY
    main_b64, options, rel_ids = parse_ablinks(html)
    if not options:
        log("[FAUCET] antibot links gak ketemu", "wr")
        return 0
    if not main_b64:
        main_b64 = options[0]
    if len(options) > 4:
        options, rel_ids = options[:4], rel_ids[:4]

    log(f"[FAUCET] {NEON_GREEN}{len(options)}{RST} pilihan antibot", "fa")
    ans = solve_antibot(apikey, main_b64, options, "[FAUCET-AB]")
    if ans is _HARD_ERR:
        return -3
    if not ans:
        log("[FAUCET] antibot gagal", "er")
        return 0

    tokens = re.findall(r"\d+", ans)
    if not tokens:
        log(f"[FAUCET] antibot jawaban kosong: {ans}", "er")
        return 0
    selected_rels = []
    for t in tokens:
        try:
            idx = int(t)
        except ValueError:
            continue
        if 1 <= idx <= len(options):
            selected_rels.append(rel_ids[idx - 1])
        elif 0 <= idx < len(options):
            selected_rels.append(rel_ids[idx])

    if not selected_rels:
        log(f"[FAUCET] antibot index tidak valid: {ans}", "er")
        return 0

    antibotlinks = " ".join(selected_rels)
    log(f"[FAUCET] antibot → {antibotlinks.strip()}", "fa")

    token = solve_turnstile(apikey, sitekey, f"{HOST}/faucet", "[FAUCET-CF]")
    if token is _HARD_ERR:
        return -3
    if not token:
        log("[FAUCET] captcha gagal", "er")
        return 0

    post_hdr = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": DEF_UA,
        "referer": f"{HOST}/faucet",
        "origin": HOST,
    }
    body = {"csrf_token": csrf, "antibotlinks": antibotlinks,
            "cf-turnstile-response": token}

    resp, code, final_url = safe_request(sess, f"{HOST}/faucet",
                                         method="POST", headers=post_hdr,
                                         data=body)

    ntype, nmsg = parse_notyf(resp)
    if ntype:
        msg_l = nmsg.lower()
        if any(k in msg_l for k in ("maximum daily", "reached the maximum",
                                     "reached maximum", "daily limit", "limit reached")):
            log("[FAUCET] ⚠ Limit harian tercapai", "wr")
            return -2
        if ntype == "success" or "added to your balance" in msg_l:
            log(f"[FAUCET] {nmsg}", "ok")
            return 1
        log(f"[FAUCET] {nmsg}", "wr")
        return 0

    body_l = resp.lower()
    if "has been added to your balance" in body_l:
        return 1

    for kw in ("maximum daily", "reached the maximum", "reached maximum",
               "daily limit", "limit reached"):
        if kw in body_l:
            log("[FAUCET] ⚠ Limit harian tercapai", "wr")
            return -2

    for kw in ("too early", "invalid", "error", "captcha failed"):
        if kw in body_l:
            log(f"[FAUCET] {kw}", "wr")
            return 0
    return 0


# ═══════════════════════════════════════════════════════════════
# SURF / PTC
# ═══════════════════════════════════════════════════════════════
def get_surf_ads(sess):
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf", headers=base_headers())
    except Exception:
        return []
    if not is_logged_in(html):
        return []
    return parse_surf_ads(html)


def claim_one_surf(sess, apikey, ad):
    uid = ad["uid"]; duration = ad["duration"]
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf/{uid}", headers=base_headers())
    except Exception as e:
        log(f"[SURF] View error: {e}", "er")
        return False
    if not is_logged_in(html):
        return None
    csrf = parse_csrf(html)
    btn = (re.search(r'<button\s+id="([a-f0-9]+)"\s+class="btn btn-primary start-btn"', html)
           or re.search(r'id="([a-f0-9]+)"[^>]*class="[^"]*start-btn', html))
    if not btn:
        return False
    start_token = btn.group(1)
    id_m = re.search(r"let id = '([a-f0-9]+)';", html)
    cnt_m = re.search(r"let count = (\d+);", html)
    ad_id = id_m.group(1) if id_m else start_token
    count = int(cnt_m.group(1)) if cnt_m else duration
    c_param = ad_id + str(random.randint(1, 9999))
    try:
        safe_request(sess, f"{HOST}/surf/{uid}/{c_param}",
                     headers={**base_headers(), "referer": f"{HOST}/surf/{uid}"},
                     allow_redirects=False)
    except Exception:
        pass
    tmr(count, "[SURF] View")
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf/{uid}", headers=base_headers())
    except Exception:
        return False
    csrf = parse_csrf(html) or csrf
    sitekey = parse_sitekey(html) or TURNSTILE_SITEKEY
    token = solve_turnstile(apikey, sitekey, f"{HOST}/surf/{uid}", "[SURF-CF]")
    if token is _HARD_ERR:
        return False
    if not token:
        log("[SURF] captcha gagal", "er")
        return False
    ajax_hdr = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": DEF_UA,
        "referer": f"{HOST}/surf/{uid}",
        "origin": HOST,
        "x-requested-with": "XMLHttpRequest",
    }
    body = {"csrf_token": csrf, "uid": uid, "c": c_param,
            "cf-turnstile-response": token}
    try:
        r = sess.post(f"{HOST}/ajax/surf", data=body, headers=ajax_hdr,
                      timeout=30, allow_redirects=True)
        if r.status_code == 200:
            try:
                d = r.json()
            except Exception:
                return False
            if d.get("success"):
                return True
    except Exception:
        pass
    return False


# ═══════════════════════════════════════════════════════════════
# AVISO / YOUTUBE
# ═══════════════════════════════════════════════════════════════
def aviso_headers():
    return {
        'Accept': '*/*',
        'Accept-Language': 'en',
        'Content-Type': 'application/json',
        'Origin': HOST,
        'Referer': HOST,
        'User-Agent': DEF_UA,
        'X-Api-Key': AVISO_API_KEY,
        'X-Requested-With': 'mark.via.gp',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
    }


def aviso_identify(user_hash):
    if not user_hash:
        return None
    payload = {
        "hash": user_hash, "ip": None, "userAgent": DEF_UA,
        "fingerprint": {
            "fp": "8661a494702c33f967373004765326f5",
            "hashFont": "2f48d5374924fd0ce9bb54863fb00708",
            "langs": "en-PH, en-US",
            "timezone": "Asia/Manila",
            "platform": "Linux aarch64",
            "gpu": "Qualcomm~Adreno (TM) 619",
            "screen": "360x804", "memory": 8, "cpuCores": 8,
        }
    }
    try:
        r = requests.post(f"{AVISO_API}/youtube/tasks/identify", json=payload,
                          headers=aviso_headers(), timeout=15, verify=False,
                          impersonate="chrome124")
        if r.status_code == 200:
            return r.json().get("id")
    except Exception:
        pass
    return None


def aviso_tasks_page(user_hash, offset=0, limit=100):
    try:
        r = requests.get(f"{AVISO_API}/youtube/tasks/available",
                         params={"hash": user_hash, "platform": "Linux aarch64",
                                 "offset": offset, "limit": limit},
                         headers=aviso_headers(), timeout=20, verify=False,
                         impersonate="chrome124")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def aviso_start(user_hash, task_id, task_type):
    try:
        r = requests.post(f"{AVISO_API}/youtube/tasks/start",
                          json={"taskId": task_id, "hash": user_hash,
                                "type": task_type, "platform": "Linux aarch64"},
                          headers=aviso_headers(), timeout=15, verify=False,
                          impersonate="chrome124")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def aviso_timer(attempt_id, action, watched=None):
    p = {"attemptId": attempt_id, "action": action}
    if watched is not None:
        p["watchedTime"] = watched
    try:
        r = requests.post(f"{AVISO_API}/youtube/tasks/timer-status", json=p,
                          headers=aviso_headers(), timeout=15, verify=False,
                          impersonate="chrome124")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def aviso_complete(attempt_id):
    try:
        r = requests.post(f"{AVISO_API}/youtube/tasks/complete",
                          json={"attemptId": attempt_id},
                          headers=aviso_headers(), timeout=15, verify=False,
                          impersonate="chrome124")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def claim_one_video(sess, user_hash, task):
    if task.get("inProgress"):
        return False
    tid = task["id"]
    ttype = task["type"]
    duration = int(task.get("duration", 10)) if ttype == "ads" else 5
    start = aviso_start(user_hash, tid, ttype)
    if not start:
        return False
    aid = start.get("attemptId")
    if not aid:
        return False
    if start.get("duration"):
        duration = int(start["duration"])
    url = start.get("url")
    if url:
        try:
            sess.get(url, headers={"user-agent": DEF_UA}, timeout=15)
        except Exception:
            pass
    t = aviso_timer(aid, "start")
    if not t:
        return False
    if t.get("status") == "need_check":
        tmr(duration, f"[{ttype}] Watch")
        comp = aviso_timer(aid, "complete", duration)
        if not comp or not comp.get("verified"):
            return False
        chk = aviso_timer(aid, "check")
        if not chk or not chk.get("viewExists"):
            return False
        fin = aviso_complete(aid)
        if fin:
            return True
        return False
    if ttype in ("like", "sub"):
        time.sleep(3)
        chk = aviso_timer(aid, "check")
        if chk and chk.get("viewExists"):
            fin = aviso_complete(aid)
            if fin:
                return True
    return False


def do_youtube(sess, username=None):
    """Return: dict stats atau None kalau gagal."""
    try:
        yt_html, _, _ = safe_request(sess, f"{HOST}/ytvideos",
                                     headers={"user-agent": DEF_UA})
    except Exception:
        return None
    user_hash = parse_user_hash(yt_html)
    if not user_hash:
        log("[YT] user_hash gak ketemu", "wr")
        return None

    aviso_id = aviso_identify(user_hash)
    if not aviso_id:
        log("[YT] aviso identify gagal", "wr")
        return None

    data = aviso_tasks_page(user_hash, 0, 100)
    if not data:
        log("[YT] gak ada tasks", "wr")
        return None

    all_tasks = []
    for t in ("ads", "like", "sub"):
        for task in data.get(t, []):
            if task.get("inProgress"):
                continue
            task["type"] = t
            all_tasks.append(task)

    if not all_tasks:
        log("[YT] 0 task tersedia", "wr")
        return {"total": 0, "ok": 0}

    log(f"[YT] {NEON_GREEN}{len(all_tasks)}{RST} task tersedia", "yt")
    total_ok = 0
    for i, task in enumerate(all_tasks, 1):
        log(f"[YT] [{i}/{len(all_tasks)}] [{NEON_PINK}{task['type']}{RST}] "
            f"{task.get('title', '-')[:35]}", "yt")
        try:
            r = claim_one_video(sess, user_hash, task)
        except Exception as e:
            log(f"[YT] err: {e}", "er"); r = False
        if r:
            total_ok += 1
            log(f"[YT] ✓ {task['type']} ok", "ok")
        else:
            log(f"[YT] ✗ gagal: {task['type']}", "er")
        time.sleep(2)

    return {"total": len(all_tasks), "ok": total_ok}


# ═══════════════════════════════════════════════════════════════
# BANNER / CONFIG
# ═══════════════════════════════════════════════════════════════
def banner():
    print(f"{NEON_PINK}╔═══════════════════════════════════════════════╗{RST}")
    print(f"{NEON_PINK}║{RST}  {NEON_CYAN}{BOLD}BTCADSPACE BOT{RST} {NEON_YELLOW}—{RST} {NEON_GREEN}SINGLE ACCOUNT{RST}       {NEON_PINK}║{RST}")
    print(f"{NEON_PINK}║{RST}  {NEON_PURPLE}Fixed by{RST} {NEON_MAGENTA}{BOLD}MoneyMaker_w{RST}                    {NEON_PINK}║{RST}")
    print(f"{NEON_PINK}╚═══════════════════════════════════════════════╝{RST}")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        clear(); banner()
        print(f"\n{NEON_WHITE}Setup awal — paste cookie dari browser.{RST}")
        print(f"{NEON_WHITE}Cara: login manual di btcadspace.com{RST}")
        print(f"{NEON_WHITE}      F12 → Console → ketik: copy(document.cookie){RST}\n")

        print(f"{NEON_CYAN}Username/Email : {RST}", end="")
        username = input().strip()
        print(f"{NEON_CYAN}API Key (Waryono): {RST}", end="")
        apikey = input().strip()
        print(f"{NEON_CYAN}Proxy (Opt)    : {RST}", end="")
        proxy = input().strip()
        print(f"{NEON_CYAN}Cookie         : {RST}", end="")
        cookie_raw = input().strip()

        cfg = {
            "username": username,
            "apikey":   apikey,
            "proxy":    proxy,
            "cookies":  parse_cookie_string(cookie_raw),
        }
        save_config(cfg)
        log("Config tersimpan", "ok")
        time.sleep(1)
        return cfg

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg.setdefault("username", "")
    cfg.setdefault("apikey", "")
    cfg.setdefault("proxy", "")
    cfg.setdefault("cookies", {})
    if isinstance(cfg["cookies"], str):
        cfg["cookies"] = parse_cookie_string(cfg["cookies"])
    cfg.pop("fp_email", None)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def show_info(cfg):
    clear(); banner()
    print(f"{NEON_WHITE}Account : {NEON_CYAN}{mask_email(cfg['username'])}{RST}")
    k = cfg.get("apikey") or ""
    k_disp = (k[:8] + "…" + k[-4:]) if len(k) > 14 else (k or "(kosong)")
    print(f"{NEON_WHITE}API Key : {NEON_YELLOW}{k_disp}{RST}")
    print(f"{NEON_WHITE}Proxy   : {NEON_YELLOW}{cfg.get('proxy') or '-'}{RST}")
    print(f"{NEON_WHITE}Cookies : {NEON_GREEN}{len(cfg.get('cookies', {}))}{RST} entries")
    print(f"{NEON_PURPLE}───────────────────────────────────────────────{RST}")


# ═══════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════
def claim_loop(sess, cfg):
    apikey = cfg["apikey"]

    old_bal = get_balance(sess)
    if old_bal is not None:
        log(f"Balance awal: {NEON_YELLOW}{old_bal}{RST} coins", "bi")

    faucet_limited = False

    while True:
        # ═══ SURF ═══
        print(f"\n{NEON_PURPLE}╭─ {NEON_BLUE}{BOLD}SURF ADS{RST} {NEON_PURPLE}──────────────────────╮{RST}")
        try:
            ads = get_surf_ads(sess)
        except Exception:
            ads = []
        if not ads:
            log("[SURF] 0 tersedia", "wr")
        else:
            log(f"[SURF] {NEON_GREEN}{len(ads)}{RST} tersedia", "sf")
            for i, ad in enumerate(ads, 1):
                log(f"[SURF] [{i}/{len(ads)}] {ad['title'][:30]} | "
                    f"{NEON_YELLOW}{ad['coins']}c{RST} | {ad['duration']}s", "sf")
                try:
                    r = claim_one_surf(sess, apikey, ad)
                except Exception as e:
                    log(f"[SURF] err: {e}", "er"); r = False
                if r:
                    time.sleep(1)
                    new_bal = get_balance(sess)
                    diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                    log(f"[SURF] ✓ {ad['title'][:30]} | balance: {NEON_GREEN}{new_bal}{RST} (+{diff})", "ok")
                    if new_bal is not None:
                        old_bal = new_bal
                else:
                    log(f"[SURF] ✗ gagal: {ad['title'][:30]}", "er")
                time.sleep(2)
        print(f"{NEON_PURPLE}╰────────────────────────────────────╯{RST}")

        # ═══ FAUCET ═══
        print(f"\n{NEON_PURPLE}╭─ {NEON_ORANGE}{BOLD}FAUCET{RST} {NEON_PURPLE}─────────────────────────╮{RST}")
        if faucet_limited:
            log("[FAUCET] skip (limit harian)", "wr")
        else:
            for attempt in range(1, MAX_RETRY + 1):
                try:
                    r = do_faucet(sess, apikey)
                except Exception as e:
                    log(f"[FAUCET] err: {e}", "er"); r = 0

                if r == -1:
                    log("[FAUCET] session expired", "er")
                    return
                if r == -2:
                    faucet_limited = True
                    break
                if r == -3:
                    break
                if r == 1:
                    time.sleep(2)
                    new_bal = get_balance(sess)
                    diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                    log(f"[FAUCET] ✓ balance: {NEON_GREEN}{new_bal}{RST} (+{diff})", "ok")
                    if new_bal is not None:
                        old_bal = new_bal
                    break
                if attempt < MAX_RETRY:
                    log(f"[FAUCET] retry {attempt}/{MAX_RETRY}...", "wr")
                time.sleep(2)
        print(f"{NEON_PURPLE}╰────────────────────────────────────╯{RST}")

        # ═══ YOUTUBE ═══
        print(f"\n{NEON_PURPLE}╭─ {NEON_PINK}{BOLD}YOUTUBE VIDEOS{RST} {NEON_PURPLE}─────────────────╮{RST}")
        try:
            yt_result = do_youtube(sess, cfg.get("username"))
            if yt_result:
                if yt_result["total"] == 0:
                    log("[YT] 0 task", "wr")
                else:
                    log(f"[YT] Selesai: {NEON_GREEN}{yt_result['ok']}{RST}/{yt_result['total']} ok",
                        "ok" if yt_result["ok"] else "wr")
                    # Refresh balance setelah YT
                    time.sleep(2)
                    new_bal = get_balance(sess)
                    if new_bal is not None and new_bal != old_bal:
                        diff = (new_bal - old_bal) if old_bal is not None else None
                        log(f"[YT] balance: {NEON_GREEN}{new_bal}{RST} (+{diff})", "bi")
                        old_bal = new_bal
        except Exception as e:
            log(f"[YT] err: {e}", "er")
        print(f"{NEON_PURPLE}╰────────────────────────────────────╯{RST}")

        # ═══ COOLDOWN ═══
        print(f"\n{NEON_PURPLE}[LOOP] Cooldown {NEON_RED}{FAUCET_COOLDOWN}s{NEON_PURPLE}...{RST}")
        tmr(FAUCET_COOLDOWN, "Cooldown")


def main():
    try:
        cfg = load_config()
    except KeyboardInterrupt:
        print(f"\n{NEON_YELLOW}Cancelled.{RST}")
        return

    show_info(cfg)

    if not cfg.get("apikey"):
        print(f"{NEON_RED}⚠ API key kosong. Isi di config.json lalu jalanin lagi.{RST}")
        time.sleep(3)
        return

    if not cfg.get("cookies"):
        print(f"{NEON_RED}⚠ Cookies kosong. Isi di config.json lalu jalanin lagi.{RST}")
        time.sleep(3)
        return

    try:
        sess = build_session(cfg["cookies"], cfg.get("proxy") or None)
    except Exception as e:
        print(f"{NEON_RED}Session error: {e}{RST}")
        return

    log("Verifikasi session cookies...", "in")
    ok, html = check_session(sess)
    if not ok:
        log("Session expired / cookie invalid", "er")
        print(f"\n{NEON_WHITE}Update cookie di config.json, lalu jalanin lagi.{RST}")
        time.sleep(3)
        return
    log(f"Session valid: {NEON_GREEN}{mask_email(cfg['username'])}{RST}", "ok")

    try:
        claim_loop(sess, cfg)
    except KeyboardInterrupt:
        print(f"\n{NEON_YELLOW}Dihentikan user.{RST}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{NEON_YELLOW}Dihentikan user.{RST}")
