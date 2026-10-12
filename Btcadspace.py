#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, re, sys, os, hashlib, random, threading
from datetime import datetime
from typing import Optional, List, Dict, Tuple
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

# ── Waryono.my.id (menggantikan tertuyul) ──
WARYONO_IN        = "https://api.waryono.my.id/in.php"
WARYONO_RES       = "https://api.waryono.my.id/res.php"
WARYONO_BALANCE   = "https://api.waryono.my.id/balance.php"

TURNSTILE_SITEKEY = "0x4AAAAAAAB-TZt_lwYtViEL"
AVISO_API         = "https://aviso.bz/api/v1"
AVISO_API_KEY     = "ak_87e52f3d03d99fbb11505fc3ec24b881dddfb42e"

CONFIG_FILE       = "config.json"
SESSION_DIR       = "sessions_btcadspace"
DEBUG_HTML_DIR    = "debug_html"

MAX_RETRY         = 3
FARM_COOLDOWN     = 300
FAUCET_COOLDOWN   = 5

DEF_UA = ("Mozilla/5.0 (Linux; Android 15; CPH2505 Build/UKQ1.230924.001) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 "
          "Mobile Safari/537.36")

BLK="\033[0;30m"; RED="\033[0;31m"; GRN="\033[0;32m"; YEL="\033[0;33m"
BLU="\033[0;34m"; MAG="\033[0;35m"; CYN="\033[0;36m"; WHT="\033[0;37m"
RST="\033[0m"; BOLD="\033[1m"
CLR = "\r\033[2K"

_HARD_ERR = object()

LIMITED_FAUCET = {}

# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════

def _mark_faucet_limited(username):
    LIMITED_FAUCET[username] = True


def _is_faucet_limited(username):
    return LIMITED_FAUCET.get(username, False)


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
        "i":  f"{CYN}»{RST}", "ok": f"{GRN}✓{RST}", "er": f"{RED}✗{RST}",
        "wr": f"{YEL}⚠{RST}", "in": f"{BLU}●{RST}", "cf": f"{CYN}◇{RST}",
        "bi": f"{GRN}₹{RST}", "bt": f"{MAG}◆{RST}", "ip": f"{MAG}⊕{RST}",
        "wd": f"{YEL}⇩{RST}",
    }
    icon = icons.get(tag, f"{CYN}»{RST}")
    ts = datetime.now().strftime("%H:%M:%S")
    sys.stdout.write(CLR + f"{WHT}[{ts}]{RST} {icon} {msg}")
    if end:
        sys.stdout.write(end)
    sys.stdout.flush()


def tmr(seconds, label="Countdown"):
    symbols   = list(reversed(['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘']))
    spinners  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
    spinners1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽',
                 '▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
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
        sp1    = spinners1[i % len(spinners1)]
        dot    = dots[elapsed % len(dots)]
        i += 1
        c1 = random.randint(1, 7); c2 = random.randint(1, 7)
        sys.stdout.write(
            f"{CLR} \033[1;3{c1}m {sp}\033[1;37m {label} "
            f"\033[1;31m{mm:02d}:{ss:02d}\033[1;3{c2}m {symbol} {sp1}"
            f"\033[1;37m {pct}%\033[1;33m {dot}")
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


def get_ipv6(proxy_raw=None):
    proxy_dict = parse_proxy(proxy_raw)
    for _ in range(2):
        try:
            r = requests.get("https://api6.ipify.org?format=json",
                             impersonate="chrome110", timeout=8,
                             proxies=proxy_dict)
            j = r.json()
            if j.get("ip") and ":" in j["ip"]:
                return j["ip"]
        except Exception:
            pass
    return None


def show_ip_banner(proxy_raw=None):
    ipv6 = get_ipv6(proxy_raw)
    if ipv6:
        print(f"{WHT}IP v6 : {MAG}{ipv6}{RST}")
    else:
        print(f"{WHT}IP v6 : {YEL}-{RST}")


# ═══════════════════════════════════════════════════════════════
# SESSION
# ═══════════════════════════════════════════════════════════════

def session_path(username):
    os.makedirs(SESSION_DIR, exist_ok=True)
    h = hashlib.md5(username.lower().strip().encode()).hexdigest()[:16]
    return os.path.join(SESSION_DIR, f"cookies_{h}.json")


def load_session(username, proxy_raw=None):
    s = requests.Session(impersonate="chrome110")
    s.verify = False
    proxy_dict = parse_proxy(proxy_raw)
    if proxy_dict:
        s.proxies = proxy_dict
    p = session_path(username)
    if os.path.exists(p):
        try:
            with open(p) as f:
                cookies = json.load(f)
            for k, v in cookies.items():
                s.cookies.set(k, v, domain=".btcadspace.com")
        except Exception:
            pass
    return s


def save_session(username, sess):
    try:
        with open(session_path(username), "w") as f:
            json.dump(sess.cookies.get_dict(), f, indent=2)
    except Exception:
        pass


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
                print(f"{RED}✗ ERROR PROXY: {msg}{RST}")
                sys.stdout.flush()
                raise
            sys.stdout.write(CLR + f"{YEL}⚠ [NET] gagal (#{attempt}): {msg[:70]}, retry 8s...{RST}")
            sys.stdout.flush()
            time.sleep(8)


def dump_debug_html(username, tag, html):
    return  # disabled
    try:
        os.makedirs(DEBUG_HTML_DIR, exist_ok=True)
        h = hashlib.md5(username.lower().strip().encode()).hexdigest()[:8]
        path = os.path.join(DEBUG_HTML_DIR, f"{h}_{tag}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html or "")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# SPINNER RENDER (bg)
# ═══════════════════════════════════════════════════════════════

_SYMBOLS   = list(reversed(['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘']))
_SPINNERS  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
_SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽',
              '▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
_DOTS      = ['▪', '▪▪', '▪▪▪', '▪▪▪▪']


def _render_spinner(label, elapsed, total, i):
    remaining = max(0, total - elapsed)
    pct = round(((total - remaining) / total) * 100) if total > 0 else 100
    mm, ss = divmod(elapsed, 60)
    symbol = _SYMBOLS[i % len(_SYMBOLS)]
    sp     = _SPINNERS[i % len(_SPINNERS)]
    sp1    = _SPINNERS1[i % len(_SPINNERS1)]
    dot    = _DOTS[(elapsed // 1) % len(_DOTS)]
    c1 = random.randint(1, 7); c2 = random.randint(1, 7)
    sys.stdout.write(
        f"{CLR} \033[1;3{c1}m {sp}\033[1;37m {label} "
        f"\033[1;31m{mm:02d}:{ss:02d}\033[1;3{c2}m {symbol} {sp1}"
        f"\033[1;37m {pct}%\033[1;33m {dot}")
    sys.stdout.flush()


def _clear_line():
    sys.stdout.write(CLR); sys.stdout.flush()


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


def _is_transient_err(msg: str) -> bool:
    if not msg:
        return False
    up = msg.upper()
    return any(k in up for k in _TRANSIENT_ERR_KEYS)


def _classify_waryono_error(msg: str) -> str:
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
                    impersonate="chrome110", timeout=10)
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
            _render_spinner(label, elapsed, timeout, i)
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
        _clear_line()

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
            }, impersonate="chrome110", timeout=20)
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
            "methods": method,      # "antibot"
            "main":    main_b64,
            "json":    1,
        }
        for i, opt in enumerate(options_b64[:4], 1):
            payload[f"param{i}"] = opt

        r = requests.post(WARYONO_IN, json=payload,
                          impersonate="chrome110", timeout=20)
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
    m = re.search(r'class="[^"]*\bbalance\b[^"]*"[^>]*>\s*([\d,\.]+)', html, re.I)
    if m:
        v = _to_int(m.group(1))
        if v is not None:
            return v
    m = re.search(r'[Bb]alance[^\d]{0,80}?([\d,]{2,}(?:\.\d+)?)\s*(?:Coins?|coins?)',
                  html, re.DOTALL)
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


def parse_withdraw_form(html):
    result = {
        "action": "/ajax/makeWithdrawal",
        "csrf": None, "address": None, "currency_name": None,
        "amount_name": None, "options": [], "amount_min": None,
        "amount_max": None,
    }
    if not html:
        return result

    modal_m = re.search(
        r'<div[^>]*id="withdrawModal"[^>]*>(.*?)(?:<div[^>]*id="[^"]*Modal"|<div[^>]*class="[^"]*graybg)',
        html, re.S)
    if not modal_m:
        fm_m = re.search(
            r'<form[^>]*id="makeWithdrawForm"[^>]*>(.*?)</form>',
            html, re.S)
        inner = fm_m.group(1) if fm_m else ""
    else:
        inner_full = modal_m.group(1)
        fm_m = re.search(
            r'<form[^>]*id="makeWithdrawForm"[^>]*>(.*?)</form>',
            inner_full, re.S)
        inner = fm_m.group(1) if fm_m else inner_full

    if not inner:
        return result

    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', inner)
    if m:
        result["csrf"] = m.group(1)

    m = re.search(r'<input[^>]*name="address"[^>]*>', inner)
    if m:
        result["address"] = "address"

    sm = re.search(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>',
                   inner, re.S)
    if sm:
        result["currency_name"] = sm.group(1)
        for opt in re.finditer(
                r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>',
                sm.group(2)):
            result["options"].append({
                "value": opt.group(1),
                "label": re.sub(r'\s+', ' ', opt.group(2)).strip(),
            })

    m = re.search(r'<input[^>]*name="amount"[^>]*>', inner)
    if m:
        tag = m.group(0)
        result["amount_name"] = "amount"
        mm = re.search(r'min="(\d+)"', tag)
        if mm:
            result["amount_min"] = int(mm.group(1))
        mm = re.search(r'max="(\d+)"', tag)
        if mm:
            result["amount_max"] = int(mm.group(1))

    return result


# ═══════════════════════════════════════════════════════════════
# LOGIN / ACCOUNT
# ═══════════════════════════════════════════════════════════════

def do_login(sess, apikey, username, password):
    log(f"Login: {mask_email(username)}", "in")
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "accept-language": "en-PH,en-US;q=0.9,en;q=0.8"}
    for _ in range(MAX_RETRY):
        html, code, _ = safe_request(sess, f"{HOST}/login", headers=base_hdr)
        csrf = parse_csrf(html)
        if not csrf:
            time.sleep(3); continue
        sitekey = parse_sitekey(html) or TURNSTILE_SITEKEY
        token = solve_turnstile(apikey, sitekey, f"{HOST}/login", "[LOGIN]")
        if token is _HARD_ERR:
            return False
        if not token:
            time.sleep(3); continue
        post_hdr = {"content-type": "application/x-www-form-urlencoded",
                    "user-agent": DEF_UA, "referer": f"{HOST}/login", "origin": HOST}
        body = {"csrf_token": csrf, "username": username, "password": password,
                "2fa": "", "remember": "1", "cf-turnstile-response": token}
        resp, code, final_url = safe_request(
            sess, f"{HOST}/login", method="POST", headers=post_hdr, data=body)
        if "/account" in final_url or is_logged_in(resp):
            log("Login berhasil!", "ok")
            save_session(username, sess)
            return True
        time.sleep(3)
    log("Login gagal", "er")
    return False


def ensure_logged_in(sess, apikey, username, password):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    try:
        html, _, final_url = safe_request(sess, f"{HOST}/account", headers=base_hdr)
    except Exception:
        return False
    if "/login" not in final_url and is_logged_in(html):
        return True
    # Kalau mode no-apikey (YouTube), skip login captcha
    if not apikey:
        return False
    return do_login(sess, apikey, username, password)


def get_balance(sess, username=None, debug=False):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    last_html = None
    for _ in range(3):
        try:
            html, _, _ = safe_request(sess, f"{HOST}/account", headers=base_hdr)
            last_html = html
            bal = parse_balance(html)
            if bal is not None:
                return bal
        except Exception:
            pass
        time.sleep(1)
    if debug and last_html and username:
        dump_debug_html(username, "account_parse_fail", last_html)
    return None


# ═══════════════════════════════════════════════════════════════
# FAUCET
# ═══════════════════════════════════════════════════════════════

def do_faucet(sess, apikey, username=None):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    html, _, _ = safe_request(sess, f"{HOST}/faucet", headers=base_hdr)
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

    log(f"[FAUCET] {GRN}{len(options)}{RST} pilihan antibot", "in")
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
        else:
            log(f"[FAUCET] index {idx} out of range", "wr")

    if not selected_rels:
        log(f"[FAUCET] antibot index tidak valid: {ans}", "er")
        return 0

    antibotlinks = " ".join(selected_rels)
    log(f"[FAUCET] antibot → {antibotlinks.strip()}", "in")

    token = solve_turnstile(apikey, sitekey, f"{HOST}/faucet", "[FAUCET-CF]")
    if token is _HARD_ERR:
        return -3
    if not token:
        log("[FAUCET] captcha gagal", "er")
        return 0

    post_hdr = {"content-type": "application/x-www-form-urlencoded",
                "user-agent": DEF_UA, "referer": f"{HOST}/faucet", "origin": HOST}
    body = {"csrf_token": csrf, "antibotlinks": antibotlinks,
            "cf-turnstile-response": token}

    resp, code, final_url = safe_request(sess, f"{HOST}/faucet",
                                         method="POST", headers=post_hdr,
                                         data=body)
    if username:
        dump_debug_html(username, "faucet_response", resp)

    ntype, nmsg = parse_notyf(resp)
    if ntype:
        msg_l = nmsg.lower()
        if ("maximum daily" in msg_l or "reached the maximum" in msg_l
                or "reached maximum" in msg_l or "daily limit" in msg_l
                or "limit reached" in msg_l):
            log("[FAUCET] ⚠ Limit harian tercapai, skip akun", "wr")
            return -2
        if ntype == "success" or "added to your balance" in msg_l:
            log(f"[FAUCET] {nmsg}", "ok")
            return 1
        log(f"[FAUCET] {nmsg}", "wr")
        return 0

    body_l = resp.lower()
    if "has been added to your balance" in body_l:
        return 1

    limit_kws = ("maximum daily", "reached the maximum", "reached maximum",
                 "daily limit", "limit reached")
    for kw in limit_kws:
        if kw in body_l:
            log("[FAUCET] ⚠ Limit harian tercapai, skip akun", "wr")
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
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf", headers=base_hdr)
    except Exception:
        return []
    if not is_logged_in(html):
        return []
    return parse_surf_ads(html)


def claim_one_surf(sess, apikey, ad):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    uid = ad["uid"]; coins = ad["coins"]; duration = ad["duration"]
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf/{uid}", headers=base_hdr)
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
                     headers={**base_hdr, "referer": f"{HOST}/surf/{uid}"},
                     allow_redirects=False)
    except Exception:
        pass
    tmr(count, "[SURF] View")
    try:
        html, _, _ = safe_request(sess, f"{HOST}/surf/{uid}", headers=base_hdr)
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
    ajax_hdr = {"content-type": "application/x-www-form-urlencoded",
                "user-agent": DEF_UA, "referer": f"{HOST}/surf/{uid}",
                "origin": HOST, "x-requested-with": "XMLHttpRequest"}
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
# AVISO (YouTube) — NO API KEY NEEDED
# ═══════════════════════════════════════════════════════════════

def aviso_headers():
    return {'Accept': '*/*', 'Accept-Language': 'en',
            'Content-Type': 'application/json', 'Origin': HOST, 'Referer': HOST,
            'User-Agent': DEF_UA, 'X-Api-Key': AVISO_API_KEY,
            'X-Requested-With': 'mark.via.gp',
            'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'}


def aviso_identify(sess, user_hash):
    if not user_hash:
        return None
    payload = {"hash": user_hash, "ip": None, "userAgent": DEF_UA,
               "fingerprint": {
                   "fp": "8661a494702c33f967373004765326f5",
                   "hashFont": "2f48d5374924fd0ce9bb54863fb00708",
                   "langs": "en-PH, en-US", "timezone": "Asia/Manila",
                   "platform": "Linux aarch64",
                   "gpu": "Qualcomm~Adreno (TM) 619",
                   "screen": "360x804", "memory": 8, "cpuCores": 8}}
    try:
        r = requests.post(f"{AVISO_API}/youtube/tasks/identify", json=payload,
                          headers=aviso_headers(), timeout=15, verify=False,
                          impersonate="chrome110")
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
                         impersonate="chrome110")
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
                          impersonate="chrome110")
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
                          impersonate="chrome110")
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
                          impersonate="chrome110")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def claim_one_video(sess, user_hash, task):
    if task.get("inProgress"):
        return False
    tid = task["id"]; ttype = task["type"]
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


# ═══════════════════════════════════════════════════════════════
# WITHDRAW
# ═══════════════════════════════════════════════════════════════

def fetch_withdraw_form(sess, username=None):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    try:
        html, code, _ = safe_request(sess, f"{HOST}/account", headers=base_hdr)
    except Exception:
        return None
    if code != 200 or not is_logged_in(html):
        return None
    form = parse_withdraw_form(html)
    form["_html"] = html
    if not form.get("csrf"):
        return None
    return form


def do_withdraw(sess, apikey, coin_value, amount, address):
    form = fetch_withdraw_form(sess)
    if not form:
        return ("err", "form withdraw gak ketemu")

    csrf = form.get("csrf")
    if not csrf:
        return ("err", "csrf token hilang")
    if not form.get("currency_name"):
        return ("err", "select currency gak ketemu")
    if not form.get("amount_name"):
        return ("err", "input amount gak ketemu")

    valid_values = [o["value"] for o in form["options"]]
    if coin_value not in valid_values:
        return ("err", f"coin '{coin_value}' gak ada di opsi web")

    amin = form.get("amount_min") or 0
    if amount < amin:
        return ("err", f"amount {amount} < min {amin}")

    post_hdr = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": DEF_UA,
        "referer": f"{HOST}/account",
        "origin": HOST,
        "x-requested-with": "XMLHttpRequest",
        "accept": "*/*",
    }

    body = {
        "csrf_token": csrf,
        "address": address,
        "currency": coin_value,
        "amount": str(int(amount)),
    }

    try:
        resp, code, _ = safe_request(
            sess, f"{HOST}/ajax/makeWithdrawal",
            method="POST", headers=post_hdr, data=body)
    except Exception as e:
        return ("err", f"POST: {e}")

    try:
        data = json.loads(resp)
    except Exception:
        snippet = re.sub(r'\s+', ' ', (resp or "")[:200])
        return ("err", f"response non-JSON: {snippet}")

    status = data.get("status")
    notify = data.get("notify", {}) or {}
    if status == 200 and notify.get("success"):
        new_bal_str = data.get("balance", "")
        new_bal = None
        m = re.search(r'([\d,]+)', new_bal_str)
        if m:
            try:
                new_bal = int(m.group(1).replace(",", ""))
            except Exception:
                pass
        msg = notify.get("success", "")
        return ("ok", new_bal, amount, msg)

    err_msg = notify.get("error") or notify.get("danger") or \
              notify.get("warning") or str(data)[:120]
    return ("err", err_msg)


def fetch_history(sess, username=None, limit=20):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    try:
        html, code, _ = safe_request(sess, f"{HOST}/account", headers=base_hdr)
    except Exception:
        return []
    if code != 200 or not is_logged_in(html):
        return []

    tm = re.search(
        r'<table[^>]*id="lastWithdrawals"[^>]*>(.*?)</table>',
        html, re.S)
    if not tm:
        return []
    inner = tm.group(1)

    results = []
    rows = re.findall(r'<tr>(.*?)</tr>', inner, re.S)
    for row in rows:
        tds = re.findall(r'<td>(.*?)</td>', row, re.S)
        if len(tds) < 4:
            continue

        def _clean(s):
            return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()

        gateway = _clean(tds[0])
        amount = _clean(tds[1])

        badge_m = re.search(
            r'<span[^>]*class="[^"]*badge[^"]*bg-(\w+)[^"]*"[^>]*>([^<]+)</span>',
            tds[2])
        status_class = badge_m.group(1).lower() if badge_m else ""
        status = badge_m.group(2).strip() if badge_m else _clean(tds[2])

        dt_m = re.search(r'datetime="([^"]+)"', tds[3])
        dt = dt_m.group(1) if dt_m else _clean(tds[3])

        results.append({
            "gateway": gateway,
            "amount": amount,
            "status": status,
            "status_class": status_class,
            "time": dt,
        })
    return results[:limit]


# ═══════════════════════════════════════════════════════════════
# DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════

def print_history(items, title="History Withdrawals"):
    if not items:
        print(f"{YEL}  ⚠ Belum ada history withdrawal.{RST}")
        return

    ansi = re.compile(r'\033\[[0-9;]*m')

    def _short_time(s):
        if not s:
            return "?"
        s = re.sub(r',\s*\d{4}', '', s)
        months = {
            'January': 'Jan', 'February': 'Feb', 'March': 'Mar',
            'April': 'Apr', 'May': 'May', 'June': 'Jun',
            'July': 'Jul', 'August': 'Aug', 'September': 'Sep',
            'October': 'Oct', 'November': 'Nov', 'December': 'Dec',
        }
        for full, abbr in months.items():
            s = s.replace(full, abbr)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    W_ID   = 3
    W_GATE = 9
    W_AMT  = 11
    W_STAT = 12
    W_TIME = 12
    dashes = W_ID + W_GATE + W_AMT + W_STAT + W_TIME + 8

    print(f"\n{WHT}  {BOLD}{title}{RST}  {WHT}({len(items)}){RST}")
    print(f"{WHT}  ╭{'─' * dashes}╮{RST}")
    print(
        f"{WHT}  │{RST} "
        f"{BOLD}{'ID':<{W_ID}}{RST} "
        f"{BOLD}{'GATEWAY':<{W_GATE}}{RST} "
        f"{BOLD}{'AMOUNT':>{W_AMT}}{RST} "
        f"{BOLD}{'STATUS':<{W_STAT}}{RST} "
        f"{BOLD}{'TIME':<{W_TIME}}{RST} "
        f"{WHT}│{RST}"
    )
    print(f"{WHT}  ├{'─' * dashes}┤{RST}")

    for i, it in enumerate(items, 1):
        sc = it.get("status_class", "")
        if sc == "success":
            color, icon = GRN, "✓"
        elif sc in ("warning", "info"):
            color, icon = YEL, "!"
        elif sc in ("danger", "dark"):
            color, icon = RED, "✗"
        else:
            color, icon = WHT, "?"

        status_str   = f"{icon} {it.get('status', '?')}"
        status_clean = ansi.sub('', status_str)

        gateway = str(it.get("gateway", "?"))[:W_GATE]
        amount  = str(it.get("amount", "?"))[:W_AMT]
        time_s  = _short_time(it.get("time", "?"))[:W_TIME]

        c_id     = f"{i:<{W_ID}}"
        c_gw     = f"{gateway:<{W_GATE}}"
        c_amt    = f"{amount:>{W_AMT}}"
        c_status = status_str + " " * max(0, W_STAT - len(status_clean))
        c_time   = f"{time_s:<{W_TIME}}"

        content_visible = (
            c_id + " " + c_gw + " " + c_amt + " " +
            c_status + " " + c_time
        )
        pad = max(0, dashes - len(content_visible))

        content_colored = (
            f"{c_id} "
            f"{CYN}{c_gw}{RST} "
            f"{YEL}{c_amt}{RST} "
            f"{color}{status_str}{RST}"
            f"{' ' * max(0, W_STAT - len(status_clean))} "
            f"{WHT}{c_time}{RST}"
        )

        print(f"{WHT}  │{RST} {content_colored}{' ' * pad} {WHT}│{RST}")

    print(f"{WHT}  ╰{'─' * dashes}╯{RST}")


def print_balance_box(username, balance, is_error=False):
    ansi = re.compile(r'\033\[[0-9;]*m')

    if is_error:
        line1 = f"✗ {username}"
        line2 = "Login gagal / error"
        box_color = RED
        color1 = f"{RED}{BOLD}"
        color2 = f"{RED}"
    else:
        line1 = f"✓ {username}"
        if balance is not None:
            line2 = f"Balance : {balance} coins"
        else:
            line2 = "Balance : ?"
        box_color = GRN
        color1 = f"{GRN}{BOLD}"
        color2 = f"{WHT}"

    w1 = len(ansi.sub('', line1))
    w2 = len(ansi.sub('', line2))
    inner = max(w1, w2) + 2

    print(f"{box_color}  ╭{'─' * inner}╮{RST}")
    print(f"{box_color}  │{RST} {color1}{line1}{RST}{' ' * (inner - w1 - 1)}{box_color}│{RST}")
    print(f"{box_color}  │{RST} {color2}{line2}{RST}{' ' * (inner - w2 - 1)}{box_color}│{RST}")
    print(f"{box_color}  ╰{'─' * inner}╯{RST}")


def banner_main():
    print(f"{WHT}═══════════════════════════════════════════════{RST}")
    print(f"{YEL}       BOT BTCADSPACE.XYZ MULTI AKUN{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")


def banner_account(idx, username, proxy_raw=None, show_ip=True):
    print(f"{WHT}═══════════════════════════════════════════════{RST}")
    tag = f" {WHT}(UTAMA){RST}" if idx == 0 else ""
    print(f"{WHT}Akun : {CYN}{mask_email(username)}{RST}{tag}")
    if show_ip:
        show_ip_banner(proxy_raw)
    print(f"{WHT}───────────────────────────────────────────────{RST}")


def print_success_banner(reward_text, new_bal, diff, unit="coins"):
    line1 = f"✓ {reward_text}"
    if new_bal is not None:
        if diff is not None and diff > 0:
            line2 = f"New Balance : {new_bal} {unit}  (+{diff})"
        else:
            line2 = f"New Balance : {new_bal} {unit}"
    else:
        line2 = None
    ansi = re.compile(r'\033\[[0-9;]*m')
    w1 = len(ansi.sub('', line1))
    w2 = len(ansi.sub('', line2)) if line2 else 0
    inner = max(w1, w2) + 2
    print(f"{GRN}  ╭{'─' * inner}╮{RST}")
    print(f"{GRN}  │{RST} {GRN}{BOLD}{line1}{RST}{' ' * (inner - w1 - 1)}{GRN}│{RST}")
    if line2:
        print(f"{GRN}  │{RST} {WHT}{line2}{RST}{' ' * (inner - w2 - 1)}{GRN}│{RST}")
    print(f"{GRN}  ╰{'─' * inner}╯{RST}")


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

def load_config():
    if not os.path.exists(CONFIG_FILE):
        clear(); banner_main()
        print(f"{WHT}  ⚙  BTCadspace Configuration Setup{RST}")
        print(f"{WHT}  ─────────────────────────────{RST}")
        print(f"{WHT}  API key bisa diisi nanti di menu Setting.{RST}")
        cfg = {
            "apikey_faucet": "",
            "apikey_ptc":    "",
            "accounts":      [],
        }
        save_config(cfg)
        log("Config tersimpan", "ok")
        time.sleep(1)
        return cfg
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    # Migrasi config lama (apikey tunggal)
    if "apikey" in cfg and not cfg.get("apikey_faucet"):
        cfg["apikey_faucet"] = cfg.pop("apikey")
    cfg.setdefault("apikey_faucet", "")
    cfg.setdefault("apikey_ptc",    "")
    cfg.setdefault("accounts",      [])
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def add_account(cfg):
    clear(); banner_main()
    print(f"{WHT} TAMBAH AKUN{RST}\n")
    while True:
        n = len(cfg["accounts"]) + 1
        print(f"{WHT}───────────────────────────────────────────────{RST}")
        print(f"{WHT}Akun #{n}{RST}")
        print(f"{WHT}Username/Email : {RST}", end="")
        username = input().strip()
        if not username:
            print(f"{WHT}Selesai.{RST}")
            time.sleep(1)
            return
        print(f"{WHT}Password       : {RST}", end="")
        password = input().strip()
        print(f"{WHT}FaucetPay Email: {RST}", end="")
        fp_email = input().strip()
        print(f"{WHT}Proxy (Opt)    : {RST}", end="")
        proxy = input().strip()
        cfg["accounts"].append({
            "username": username, "password": password,
            "fp_email": fp_email or username,
            "proxy": proxy})
        save_config(cfg)
        print(f"{GRN}✓ Ditambahkan: {mask_email(username)}{RST}\n")


def delete_account(cfg):
    clear(); banner_main()
    print(f"{WHT} HAPUS AKUN{RST}\n")
    if not cfg["accounts"]:
        print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); return
    for i, a in enumerate(cfg["accounts"]):
        tag = f" {WHT}[UTAMA]{RST}" if i == 0 else ""
        print(f"{CYN}[{i+1}]{WHT} {mask_email(a['username'])}{tag}")
    print(f"\n{WHT}Nomor (1,3 atau 1-3) | 0 batal: {RST}", end="")
    inp = input().strip()
    if not inp or inp == '0':
        print(f"{RED}Batal.{RST}"); time.sleep(1); return
    idxs = set(); total = len(cfg["accounts"])
    for part in inp.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a, b = map(int, part.split("-"))
                for k in range(a, b + 1):
                    if 1 <= k <= total:
                        idxs.add(k - 1)
            except Exception:
                pass
        else:
            try:
                k = int(part)
                if 1 <= k <= total:
                    idxs.add(k - 1)
            except Exception:
                pass
    if not idxs:
        print(f"{RED}Nomor invalid.{RST}"); time.sleep(2); return
    for i in sorted(idxs, reverse=True):
        acc = cfg["accounts"].pop(i)
        try:
            p = session_path(acc["username"])
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    save_config(cfg)
    print(f"{GRN}✓ Dihapus {len(idxs)} akun.{RST}")
    time.sleep(2)


def get_range(total):
    print(f"{WHT}jump to : {RST}", end="")
    a = input().strip()
    print(f"{WHT}end to  : {RST}", end="")
    b = input().strip()
    start = int(a) if a.isdigit() and int(a) >= 1 else 1
    end   = int(b) if b.isdigit() and int(b) >= 1 else total
    start = min(max(start, 1), total)
    end   = min(max(end, 1), total)
    if start > end:
        start = end
    return start - 1, end - 1


# ═══════════════════════════════════════════════════════════════
# MENU: SETTING API KEY
# ═══════════════════════════════════════════════════════════════

def _check_key_balance(label, key):
    if not key:
        print(f"{YEL}  [{label}] key kosong{RST}")
        return
    try:
        r = requests.get(WARYONO_BALANCE, params={"apikey": key},
                         impersonate="chrome110", timeout=15)
        d = r.json()
        if d.get("status") == 1:
            bal = d.get("balance")
            print(f"{GRN}  [{label}]{RST} balance: {YEL}{bal}{RST} token")
        else:
            print(f"{RED}  [{label}]{RST} error: {d.get('request')}")
    except Exception as e:
        print(f"{RED}  [{label}]{RST} err: {e}")


def setting_apikey_menu(cfg):
    while True:
        clear(); banner_main()
        print(f"{WHT}  ⚙  SETTING API KEY (Waryono.my.id){RST}")
        print(f"{WHT}  ─────────────────────────────────{RST}")
        kf = cfg.get("apikey_faucet") or ""
        kp = cfg.get("apikey_ptc")    or ""
        kf_disp = (kf[:8] + "…" + kf[-4:]) if len(kf) > 14 else (kf or "(kosong)")
        kp_disp = (kp[:8] + "…" + kp[-4:]) if len(kp) > 14 else (kp or "(kosong)")
        print(f"{CYN}[1]{WHT} API Key Faucet   : {YEL}{kf_disp}{RST}")
        print(f"{CYN}[2]{WHT} API Key PTC      : {YEL}{kp_disp}{RST}")
        print(f"{CYN}[3]{WHT} Pakai 1 key buat semuanya{RST}")
        print(f"{CYN}[4]{WHT} Hapus semua key{RST}")
        print(f"{CYN}[5]{WHT} Cek balance key (Faucet & PTC){RST}")
        print(f"{CYN}[0]{WHT} Kembali{RST}")
        print(f"{WHT}Pilih: {RST}", end="")
        c = input().strip()

        if c == '0':
            save_config(cfg); return
        elif c == '1':
            print(f"{WHT}API key Faucet: {RST}", end="")
            cfg["apikey_faucet"] = input().strip()
            save_config(cfg)
            log("Tersimpan", "ok"); time.sleep(1)
        elif c == '2':
            print(f"{WHT}API key PTC   : {RST}", end="")
            cfg["apikey_ptc"] = input().strip()
            save_config(cfg)
            log("Tersimpan", "ok"); time.sleep(1)
        elif c == '3':
            print(f"{WHT}API key (sama buat Faucet & PTC): {RST}", end="")
            k = input().strip()
            cfg["apikey_faucet"] = k
            cfg["apikey_ptc"]    = k
            save_config(cfg)
            log("Tersimpan", "ok"); time.sleep(1)
        elif c == '4':
            cfg["apikey_faucet"] = ""
            cfg["apikey_ptc"]    = ""
            save_config(cfg)
            log("Dihapus", "wr"); time.sleep(1)
        elif c == '5':
            print()
            _check_key_balance("Faucet", kf)
            _check_key_balance("PTC",    kp)
            print(f"\n{WHT}Tekan Enter...{RST}", end="")
            input()


# ═══════════════════════════════════════════════════════════════
# LOOP: FAUCET
# ═══════════════════════════════════════════════════════════════

def check_balance_all(cfg):
    accounts = cfg["accounts"]
    if not accounts:
        print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); return
    start, end = get_range(len(accounts))
    sel = accounts[start:end + 1]
    print()
    # Butuh apikey buat login. Pakai faucet key, fallback ptc key.
    apikey = cfg.get("apikey_faucet") or cfg.get("apikey_ptc") or ""
    for acc in sel:
        username = acc["username"]
        try:
            sess = load_session(username, acc.get("proxy") or None)
        except Exception:
            print_balance_box(username, None, is_error=True)
            print()
            continue
        try:
            if not ensure_logged_in(sess, apikey, username, acc["password"]):
                print_balance_box(username, None, is_error=True)
                print()
                continue
            bal = get_balance(sess, username=username, debug=True)
            print_balance_box(username, bal)
            print()
        except Exception:
            print_balance_box(username, None, is_error=True)
            print()
    print(f"{WHT}Tekan Enter...{RST}", end="")
    input()


def run_faucet_loop(cfg, selected, apikey=None):
    apikey = apikey or cfg.get("apikey_faucet") or ""
    clear(); banner_main()
    print(f"{WHT}Mode      : {CYN}Faucet Only{RST}")
    print(f"{WHT}Total Akun: {GRN}{len(selected)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    LIMITED_FAUCET.clear()
    single_account = (len(selected) == 1)

    try:
        while True:
            for idx, acc in enumerate(selected):
                username = acc["username"]
                banner_account(idx, username,
                               proxy_raw=acc.get("proxy") or None, show_ip=True)

                if _is_faucet_limited(username):
                    log(f"[FAUCET] {mask_email(username)} limit harian, skip", "wr")
                    time.sleep(1)
                    continue

                try:
                    sess = load_session(username, acc.get("proxy") or None)
                except Exception as e:
                    log(f"Proxy error: {e}", "er")
                    time.sleep(2)
                    continue

                if not ensure_logged_in(sess, apikey, username, acc["password"]):
                    log("Login gagal, skip", "er")
                    time.sleep(2)
                    continue

                old_bal = get_balance(sess)
                if old_bal is not None:
                    log(f"Balance: {old_bal} coins", "bi")

                print(f"\n{WHT}  ── FAUCET ──{RST}")
                for attempt in range(1, MAX_RETRY + 1):
                    try:
                        r = do_faucet(sess, apikey, username=username)
                    except Exception as e:
                        log(f"[FAUCET] err: {e}", "er"); r = 0
                    if r == -1:
                        if ensure_logged_in(sess, apikey, username, acc["password"]):
                            continue
                        break
                    if r == -2:
                        _mark_faucet_limited(username)
                        break
                    if r == -3:
                        break
                    if r == 1:
                        time.sleep(2)
                        new_bal = get_balance(sess)
                        diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                        if new_bal == old_bal and old_bal is not None:
                            log(f"[FAUCET] ⚠ Balance gak berubah (masih {old_bal})", "wr")
                        print_success_banner("Faucet Claim!", new_bal, diff)
                        if new_bal is not None:
                            old_bal = new_bal
                        break
                    if attempt < MAX_RETRY:
                        log(f"[FAUCET] retry {attempt}/{MAX_RETRY}...", "wr")
                    time.sleep(2)

                if single_account and _is_faucet_limited(username):
                    log("Akun ini limit harian, stop loop.", "wr")
                    print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
                    input()
                    return

                time.sleep(2)

            if all(_is_faucet_limited(a["username"]) for a in selected):
                log("Semua akun limit harian, stop loop.", "wr")
                print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
                input()
                return

            print(f"\n{WHT}[LOOP] Cooldown {FAUCET_COOLDOWN}s...{RST}")
            tmr(FAUCET_COOLDOWN, "Cooldown")
    except KeyboardInterrupt:
        print(f"\n{YEL}Dihentikan user.{RST}"); time.sleep(1)


# ═══════════════════════════════════════════════════════════════
# LOOP: PTC
# ═══════════════════════════════════════════════════════════════

def run_ptc_loop(cfg, selected, apikey=None):
    apikey = apikey or cfg.get("apikey_ptc") or ""
    clear(); banner_main()
    print(f"{WHT}Mode      : {CYN}PTC (Surf Ads){RST}")
    print(f"{WHT}Total Akun: {GRN}{len(selected)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    for idx, acc in enumerate(selected):
        username = acc["username"]
        banner_account(idx, username,
                       proxy_raw=acc.get("proxy") or None, show_ip=True)

        try:
            sess = load_session(username, acc.get("proxy") or None)
        except Exception as e:
            log(f"Proxy error: {e}", "er")
            time.sleep(2)
            continue

        if not ensure_logged_in(sess, apikey, username, acc["password"]):
            log("Login gagal, skip", "er")
            time.sleep(2)
            continue

        old_bal = get_balance(sess)
        if old_bal is not None:
            log(f"Balance: {old_bal} coins", "bi")

        try:
            ads = get_surf_ads(sess)
        except Exception:
            ads = []

        if not ads:
            log(f"[SURF] {GRN}0{RST} tersedia", "wr")
            time.sleep(2)
            continue

        print(f"\n{WHT}  ── SURF ADS ──{RST}")
        log(f"[SURF] {GRN}{len(ads)}{RST} tersedia", "in")
        total_ok = 0
        for i, ad in enumerate(ads, 1):
            log(f"[SURF] [{i}/{len(ads)}] {ad['title'][:30]} | "
                f"{YEL}{ad['coins']}c{RST} | {ad['duration']}s", "in")
            try:
                r = claim_one_surf(sess, apikey, ad)
            except Exception as e:
                log(f"[SURF] err: {e}", "er"); r = False

            if r is None:
                if ensure_logged_in(sess, apikey, username, acc["password"]):
                    try:
                        r = claim_one_surf(sess, apikey, ad)
                    except Exception:
                        r = False
                else:
                    r = False

            if r:
                time.sleep(1)
                new_bal = get_balance(sess)
                diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                print_success_banner(f"Surf +{ad['coins']}c", new_bal, diff)
                if new_bal is not None:
                    old_bal = new_bal
                total_ok += 1
            else:
                log(f"[SURF] ✗ gagal: {ad['title'][:30]}", "er")
            time.sleep(2)

        log(f"[SURF] Selesai: {GRN}{total_ok}{RST}/{len(ads)} ok",
            "ok" if total_ok else "wr")
        time.sleep(2)

    print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
    input()


# ═══════════════════════════════════════════════════════════════
# LOOP: VIDEO (no API key)
# ═══════════════════════════════════════════════════════════════

def run_video_loop(cfg, selected):
    clear(); banner_main()
    print(f"{WHT}Mode      : {CYN}YouTube Videos {GRN}(no API key){RST}")
    print(f"{WHT}Total Akun: {GRN}{len(selected)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    for idx, acc in enumerate(selected):
        username = acc["username"]
        banner_account(idx, username,
                       proxy_raw=acc.get("proxy") or None, show_ip=True)

        try:
            sess = load_session(username, acc.get("proxy") or None)
        except Exception as e:
            log(f"Proxy error: {e}", "er")
            time.sleep(2)
            continue

        # YouTube mode: login tanpa captcha solve (apikey None → fallback token-based)
        # Tapi biasanya session cookie masih valid, jadi cukup /account check.
        base_hdr = {"user-agent": DEF_UA,
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        try:
            html, _, final_url = safe_request(sess, f"{HOST}/account", headers=base_hdr)
            if "/login" in final_url or not is_logged_in(html):
                log("Session expired & YouTube mode no-solve. Update cookie manual.", "er")
                time.sleep(2)
                continue
        except Exception as e:
            log(f"Session check err: {e}", "er")
            time.sleep(2)
            continue

        old_bal = get_balance(sess)
        if old_bal is not None:
            log(f"Balance: {old_bal} coins", "bi")

        print(f"\n{WHT}  ── YOUTUBE VIDEOS ──{RST}")
        try:
            yt_html, _, _ = safe_request(sess, f"{HOST}/ytvideos",
                                         headers={"user-agent": DEF_UA})
            user_hash = parse_user_hash(yt_html)
        except Exception:
            user_hash = None

        if not user_hash:
            log("[VIDEO] user_hash gak ketemu, skip", "wr")
            time.sleep(2)
            continue

        aviso_id = aviso_identify(sess, user_hash)
        if not aviso_id:
            log("[VIDEO] aviso identify gagal", "wr")
            time.sleep(2)
            continue

        data = aviso_tasks_page(user_hash, 0, 100)
        if not data:
            log("[VIDEO] gak ada tasks", "wr")
            time.sleep(2)
            continue

        all_tasks = []
        for t in ("ads", "like", "sub"):
            for task in data.get(t, []):
                if task.get("inProgress"):
                    continue
                task["type"] = t
                all_tasks.append(task)

        if not all_tasks:
            log("[VIDEO] 0 task tersedia", "wr")
            time.sleep(2)
            continue

        log(f"[VIDEO] {GRN}{len(all_tasks)}{RST} task tersedia", "in")
        total_ok = 0
        for i, task in enumerate(all_tasks, 1):
            log(f"[VIDEO] [{i}/{len(all_tasks)}] [{task['type']}] "
                f"{task.get('title', '-')[:30]}", "in")
            try:
                r = claim_one_video(sess, user_hash, task)
            except Exception as e:
                log(f"[VIDEO] err: {e}", "er"); r = False

            if r:
                time.sleep(1)
                new_bal = get_balance(sess)
                diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                print_success_banner(f"Video [{task['type']}]", new_bal, diff)
                if new_bal is not None:
                    old_bal = new_bal
                total_ok += 1
            else:
                log(f"[VIDEO] ✗ gagal: {task['type']}", "er")
            time.sleep(2)

        log(f"[VIDEO] Selesai: {GRN}{total_ok}{RST}/{len(all_tasks)} ok",
            "ok" if total_ok else "wr")
        time.sleep(2)

    print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
    input()


# ═══════════════════════════════════════════════════════════════
# FARM ALL
# ═══════════════════════════════════════════════════════════════

STATS = {"faucet": 0, "surf": 0, "video": 0, "coins": 0}
PER_ACCOUNT_STATS = {}


def reset_stats():
    STATS["faucet"] = 0
    STATS["surf"] = 0
    STATS["video"] = 0
    PER_ACCOUNT_STATS.clear()


def _ensure_acc_stats(username, start_bal=None):
    if username not in PER_ACCOUNT_STATS:
        PER_ACCOUNT_STATS[username] = {
            "faucet": 0, "surf": 0, "video": 0,
            "start_bal": start_bal, "end_bal": start_bal,
            "claims_faucet": 0, "claims_surf": 0, "claims_video": 0,
            "status": "running",
        }
    return PER_ACCOUNT_STATS[username]


def _track_earned(username, category, amount):
    s = _ensure_acc_stats(username)
    s[category] = s.get(category, 0) + amount
    s[f"claims_{category}"] = s.get(f"claims_{category}", 0) + 1


def _set_end_bal(username, end_bal):
    s = _ensure_acc_stats(username)
    s["end_bal"] = end_bal


def print_account_summary():
    if not PER_ACCOUNT_STATS:
        return

    print(f"\n{WHT}═══════════════════════════════════════════════{RST}")
    print(f"{WHT}  {BOLD}📊 PER-ACCOUNT EARNINGS{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")

    total_faucet = total_surf = total_video = 0

    for username, s in PER_ACCOUNT_STATS.items():
        earned_total = s["faucet"] + s["surf"] + s["video"]
        total_faucet += s["faucet"]
        total_surf += s["surf"]
        total_video += s["video"]

        status = s.get("status", "?")
        if status == "ok":
            status_icon = f"{GRN}✓{RST}"
        elif status == "partial":
            status_icon = f"{YEL}◐{RST}"
        elif status == "login_fail":
            status_icon = f"{RED}✗{RST}"
        else:
            status_icon = f"{CYN}▶{RST}"

        start_b = s.get("start_bal")
        end_b = s.get("end_bal")
        start_str = f"{start_b}" if start_b is not None else "?"
        end_str   = f"{end_b}"   if end_b   is not None else "?"

        print(f"\n  {status_icon} {CYN}{mask_email(username)}{RST}")
        print(f"     Balance  : {YEL}{start_str}{RST} → {YEL}{end_str}{RST}  "
              f"{WHT}(net {GRN}+{earned_total}{RST})")
        print(f"     Faucet   : {GRN}+{s['faucet']:<5}{RST} "
              f"({s.get('claims_faucet', 0)}x)  "
              f"{WHT}|{RST}  "
              f"Surf : {GRN}+{s['surf']:<5}{RST} ({s.get('claims_surf', 0)}x)  "
              f"{WHT}|{RST}  "
              f"Video: {GRN}+{s['video']:<5}{RST} ({s.get('claims_video', 0)}x)")

    print(f"\n{WHT}───────────────────────────────────────────────{RST}")
    print(f"  {BOLD}GRAND TOTAL ({len(PER_ACCOUNT_STATS)} akun){RST}")
    print(f"  Faucet : {GRN}+{total_faucet}{RST}  "
          f"|  Surf : {GRN}+{total_surf}{RST}  "
          f"|  Video : {GRN}+{total_video}{RST}")
    grand = total_faucet + total_surf + total_video
    print(f"  {BOLD}{GRN}💎 TOTAL EARNED : +{grand} coins{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")


def farm_one_account(cfg, acc, idx, apikey_faucet="", apikey_ptc=""):
    sess = load_session(acc["username"], acc.get("proxy") or None)
    username = acc["username"]

    login_key = apikey_faucet or apikey_ptc
    if not ensure_logged_in(sess, login_key, username, acc["password"]):
        log("Login gagal, skip akun", "er")
        _ensure_acc_stats(username)
        PER_ACCOUNT_STATS[username]["status"] = "login_fail"
        return

    old_bal = get_balance(sess)
    if old_bal is not None:
        log(f"Balance: {old_bal} coins", "bi")

    _ensure_acc_stats(username, start_bal=old_bal)
    PER_ACCOUNT_STATS[username]["start_bal"] = old_bal
    PER_ACCOUNT_STATS[username]["status"] = "running"

    # ── SURF (pakai apikey_ptc) ──
    try:
        ads = get_surf_ads(sess)
    except Exception:
        ads = []

    if not ads:
        log(f"[SURF] {GRN}0{RST} tersedia", "wr")
    else:
        print(f"\n{WHT}  ── SURF ADS (PTC) ──{RST}")
        log(f"[SURF] {GRN}{len(ads)}{RST} tersedia", "in")
        for i, ad in enumerate(ads, 1):
            log(f"[SURF] [{i}/{len(ads)}] {ad['title'][:30]} | "
                f"{YEL}{ad['coins']}c{RST} | {ad['duration']}s", "in")
            done = False
            for attempt in range(1, MAX_RETRY + 1):
                try:
                    r = claim_one_surf(sess, apikey_ptc, ad)
                except Exception as e:
                    log(f"[SURF] err: {e}", "er"); r = False
                if r is None:
                    if not ensure_logged_in(sess, apikey_ptc,
                                            username, acc["password"]):
                        break
                    continue
                if r:
                    time.sleep(1)
                    new_bal = get_balance(sess)
                    diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                    print_success_banner(f"Surf +{ad['coins']}c", new_bal, diff)
                    STATS["surf"] += 1
                    if diff and diff > 0:
                        _track_earned(username, "surf", diff)
                    else:
                        _track_earned(username, "surf", ad["coins"])
                    if new_bal is not None:
                        old_bal = new_bal
                    done = True
                    break
                break
            if not done:
                log(f"[SURF] ✗ gagal: {ad['title'][:30]}", "er")
            time.sleep(2)

    # ── FAUCET (pakai apikey_faucet) ──
    print(f"\n{WHT}  ── FAUCET ──{RST}")
    if _is_faucet_limited(username):
        log(f"[FAUCET] limit harian, skip ke video", "wr")
    else:
        for attempt in range(1, MAX_RETRY + 1):
            try:
                r = do_faucet(sess, apikey_faucet, username=username)
            except Exception as e:
                log(f"[FAUCET] err: {e}", "er"); r = 0
            if r == -1:
                if ensure_logged_in(sess, apikey_faucet, username, acc["password"]):
                    continue
                break
            if r == -2:
                _mark_faucet_limited(username)
                break
            if r == -3:
                break
            if r == 1:
                time.sleep(2)
                new_bal = get_balance(sess)
                diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                if new_bal == old_bal and old_bal is not None:
                    log(f"[FAUCET] ⚠ Balance gak berubah (masih {old_bal})", "wr")
                print_success_banner("Faucet Claim!", new_bal, diff)
                STATS["faucet"] += 1
                if diff and diff > 0:
                    _track_earned(username, "faucet", diff)
                else:
                    _track_earned(username, "faucet", 5)
                if new_bal is not None:
                    old_bal = new_bal
                break
            if attempt < MAX_RETRY:
                log(f"[FAUCET] retry {attempt}/{MAX_RETRY}...", "wr")
            time.sleep(2)

    # ── VIDEO (no apikey) ──
    print(f"\n{WHT}  ── YOUTUBE VIDEOS ──{RST}")
    try:
        yt_html, _, _ = safe_request(sess, f"{HOST}/ytvideos",
                                     headers={"user-agent": DEF_UA})
        user_hash = parse_user_hash(yt_html)
    except Exception:
        user_hash = None

    if not user_hash:
        log("[VIDEO] user_hash gak ketemu, skip", "wr")
    else:
        aviso_id = aviso_identify(sess, user_hash)
        if not aviso_id:
            log("[VIDEO] aviso identify gagal", "wr")
        else:
            data = aviso_tasks_page(user_hash, 0, 100)
            if not data:
                log("[VIDEO] gak ada tasks", "wr")
            else:
                all_tasks = []
                for t in ("ads", "like", "sub"):
                    for task in data.get(t, []):
                        if task.get("inProgress"):
                            continue
                        task["type"] = t
                        all_tasks.append(task)
                log(f"[VIDEO] {GRN}{len(all_tasks)}{RST} task tersedia", "in")
                for i, task in enumerate(all_tasks, 1):
                    log(f"[VIDEO] [{i}/{len(all_tasks)}] [{task['type']}] "
                        f"{task.get('title', '-')[:30]}", "in")
                    try:
                        r = claim_one_video(sess, user_hash, task)
                    except Exception as e:
                        log(f"[VIDEO] err: {e}", "er"); r = False
                    if r:
                        time.sleep(1)
                        new_bal = get_balance(sess)
                        diff = (new_bal - old_bal) if (new_bal is not None and old_bal is not None) else None
                        print_success_banner(f"Video [{task['type']}]", new_bal, diff)
                        STATS["video"] += 1
                        if diff and diff > 0:
                            _track_earned(username, "video", diff)
                        if new_bal is not None:
                            old_bal = new_bal
                    else:
                        log(f"[VIDEO] ✗ gagal: {task['type']}", "er")
                    time.sleep(2)

    if old_bal is not None:
        STATS["coins"] = old_bal
        _set_end_bal(username, old_bal)

    total_earned = (PER_ACCOUNT_STATS[username]["faucet"] +
                    PER_ACCOUNT_STATS[username]["surf"] +
                    PER_ACCOUNT_STATS[username]["video"])
    if total_earned > 0:
        PER_ACCOUNT_STATS[username]["status"] = "ok"
    else:
        PER_ACCOUNT_STATS[username]["status"] = "partial"


def run_farm_all(cfg, selected, apikey_faucet=None, apikey_ptc=None):
    apikey_faucet = apikey_faucet or cfg.get("apikey_faucet") or ""
    apikey_ptc    = apikey_ptc    or cfg.get("apikey_ptc")    or ""

    clear(); banner_main()
    print(f"{WHT}Mode      : {CYN}Farm All (PTC + Faucet + Videos){RST}")
    print(f"{WHT}Total Akun: {GRN}{len(selected)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    LIMITED_FAUCET.clear()
    reset_stats()
    try:
        while True:
            for idx, acc in enumerate(selected):
                banner_account(idx, acc["username"],
                               proxy_raw=acc.get("proxy") or None, show_ip=True)
                try:
                    farm_one_account(cfg, acc, idx,
                                     apikey_faucet=apikey_faucet,
                                     apikey_ptc=apikey_ptc)
                except Exception as e:
                    log(f"Err akun: {type(e).__name__}: {e}", "er")
                    time.sleep(3)

            print_account_summary()

            print(f"\n{WHT}[LOOP] Cooldown {FARM_COOLDOWN}s...{RST}")
            tmr(FARM_COOLDOWN, "Cooldown")
    except KeyboardInterrupt:
        print(f"\n{YEL}Farming dihentikan.{RST}"); time.sleep(1)


# ═══════════════════════════════════════════════════════════════
# WITHDRAW / HISTORY MENU
# ═══════════════════════════════════════════════════════════════

def withdraw_menu(cfg):
    accounts = cfg["accounts"]
    if not accounts:
        print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); return
    start, end = get_range(len(accounts))
    sel = accounts[start:end + 1]

    login_key = cfg.get("apikey_faucet") or cfg.get("apikey_ptc") or ""
    try:
        sess = load_session(sel[0]["username"], sel[0].get("proxy") or None)
        if not ensure_logged_in(sess, login_key,
                                sel[0]["username"], sel[0]["password"]):
            print(f"{RED}Login gagal.{RST}"); time.sleep(2); return
        form = fetch_withdraw_form(sess, sel[0]["username"])
        if not form or not form.get("options"):
            print(f"{RED}Form withdraw gak ketemu / opsi currency kosong.{RST}")
            time.sleep(3); return
        options = form["options"]
    except Exception as e:
        print(f"{RED}Fetch error: {e}{RST}"); time.sleep(3); return

    clear(); banner_main()
    print(f"{WHT}Mode    : {CYN}Withdraw{RST}")
    print(f"{WHT}Total   : {GRN}{len(sel)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")
    print(f"{WHT}Pilih currency:{RST}")
    for i, opt in enumerate(options, 1):
        label = opt["label"] or opt["value"]
        print(f"{CYN}[{i}]{WHT} {label}")
    print(f"{CYN}[0]{WHT} Batal")
    print()
    print(f"{WHT}Pilih: {RST}", end="")
    ch = input().strip()
    if not ch.isdigit() or ch == '0':
        return
    idx = int(ch) - 1
    if not (0 <= idx < len(options)):
        print(f"{RED}Invalid.{RST}"); time.sleep(2); return
    coin = options[idx]

    print(f"{WHT}Amount mode: {RST}")
    print(f"{CYN}[1]{WHT} ALL balance")
    print(f"{CYN}[2]{WHT} Custom amount")
    print(f"{WHT}Pilih [1/2]: {RST}", end="")
    amode = input().strip()
    custom_amount = None
    if amode == "2":
        print(f"{WHT}Amount: {RST}", end="")
        try:
            custom_amount = int(input().strip())
        except Exception:
            print(f"{RED}Invalid.{RST}"); time.sleep(2); return

    clear(); banner_main()
    print(f"{WHT}Mode    : {CYN}Withdraw{RST}")
    print(f"{WHT}Koin    : {CYN}{coin['label'] or coin['value']}{RST}")
    print(f"{WHT}Amount  : {YEL}{'ALL' if custom_amount is None else custom_amount}{RST}")
    print(f"{WHT}Total   : {GRN}{len(sel)}{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    ok_count = skip_count = err_count = 0
    for i, acc in enumerate(sel):
        try:
            sess = load_session(acc["username"], acc.get("proxy") or None)
        except Exception as e:
            print(f"{RED}[SKIP] Proxy error: {e}{RST}"); err_count += 1; continue

        banner_account(i, acc["username"], proxy_raw=acc.get("proxy") or None,
                       show_ip=True)

        try:
            if not ensure_logged_in(sess, login_key,
                                    acc["username"], acc["password"]):
                log("Login gagal, skip", "er"); err_count += 1; continue

            bal = get_balance(sess)
            if bal is None:
                log("Balance gak ke-parse, skip", "er"); err_count += 1; continue

            amount = custom_amount if custom_amount is not None else bal
            if amount <= 0:
                log(f"Balance {bal} <= 0, skip", "wr"); skip_count += 1; continue
            if amount > bal:
                log(f"Amount {amount} > balance {bal}, pakai balance", "wr")
                amount = bal

            fp_email = acc.get("fp_email") or acc["username"]
            result = do_withdraw(sess, login_key, coin["value"], amount, fp_email)
            if result[0] == "ok":
                new_bal = result[1]
                print_success_banner(f"WD {coin['label'] or coin['value']}",
                                     new_bal,
                                     (new_bal - bal) if new_bal is not None else None,
                                     unit="coins")
                ok_count += 1
            else:
                log(f"Gagal: {result[1]}", "er"); err_count += 1
        except Exception as e:
            log(f"Error: {type(e).__name__}: {e}", "er"); err_count += 1
        time.sleep(2)

    print(f"{WHT}───────────────────────────────────────────────{RST}")
    log(f"WD Selesai: {GRN}{ok_count} ok{RST} | {YEL}{skip_count} skip{RST} | {RED}{err_count} err{RST}",
        "ok")
    print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
    input()


def history_menu(cfg):
    accounts = cfg["accounts"]
    if not accounts:
        print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); return
    start, end = get_range(len(accounts))
    sel = accounts[start:end + 1]
    login_key = cfg.get("apikey_faucet") or cfg.get("apikey_ptc") or ""
    for i, acc in enumerate(sel):
        try:
            sess = load_session(acc["username"], acc.get("proxy") or None)
            if not ensure_logged_in(sess, login_key,
                                    acc["username"], acc["password"]):
                log(f"Login gagal: {mask_email(acc['username'])}", "er")
                continue
            items = fetch_history(sess, acc["username"], limit=15)
            banner_account(i, acc["username"], proxy_raw=acc.get("proxy") or None,
                           show_ip=False)
            print_history(items, title=f"History - {mask_email(acc['username'])}")
        except Exception as e:
            log(f"Error: {e}", "er")
    print(f"\n{WHT}Tekan Enter buat balik ke menu...{RST}", end="")
    input()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    cfg = load_config()
    while True:
        clear(); banner_main()
        accounts = cfg["accounts"]
        kf = cfg.get("apikey_faucet") or ""
        kp = cfg.get("apikey_ptc")    or ""

        kf_disp = (kf[:8] + "…" + kf[-4:]) if len(kf) > 14 else (kf or "empty")
        kp_disp = (kp[:8] + "…" + kp[-4:]) if len(kp) > 14 else (kp or "empty")

        print(f"{WHT}Total Akun   : {GRN}{len(accounts)}{RST}")
        print(f"{WHT}Key Faucet   : {YEL}{kf_disp}{RST}")
        print(f"{WHT}Key PTC      : {YEL}{kp_disp}{RST}")
        print(f"{WHT}───────────────────────────────────────────────{RST}")
        print(f"{CYN}[1]{WHT} Faucet {YEL}(butuh API key){RST}")
        print(f"{CYN}[2]{WHT} PTC (Surf Ads) {YEL}(butuh API key){RST}")
        print(f"{CYN}[3]{WHT} YouTube Videos {GRN}(no API key){RST}")
        print(f"{CYN}[4]{WHT} Farm All (PTC + Faucet + Video){RST}")
        print(f"{CYN}[5]{WHT} Withdrawal{RST}")
        print(f"{CYN}[6]{WHT} Cek Balance{RST}")
        print(f"{CYN}[7]{WHT} History WD{RST}")
        print(f"{CYN}[8]{GRN} Tambah Akun{RST}")
        print(f"{CYN}[9]{RED} Hapus Akun{RST}")
        print(f"{CYN}[0]{MAG} Setting API Key{RST}")
        print(f"{CYN}[q]{WHT} Keluar{RST}")
        print(f"{WHT}───────────────────────────────────────────────{RST}")
        print(f"{WHT}Pilih: {RST}", end="")
        c = input().strip()

        if c.lower() == 'q':
            print(f"{WHT}Bye!{RST}"); return
        elif c == '0':
            setting_apikey_menu(cfg)
        elif c == '8':
            add_account(cfg)
        elif c == '9':
            delete_account(cfg)
        elif c == '6':
            if not accounts:
                print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); continue
            check_balance_all(cfg)
        elif c == '7':
            if not accounts:
                print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); continue
            history_menu(cfg)
        elif c == '5':
            if not accounts:
                print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); continue
            withdraw_menu(cfg)
        elif c in ('1', '2', '3', '4'):
            if not accounts:
                print(f"{RED}Tidak ada akun.{RST}"); time.sleep(2); continue

            # Gating API key per-mode
            if c == '1' and not kf:
                print(f"{RED}API key Faucet belum diset. Buka menu [0] Setting.{RST}")
                time.sleep(3); continue
            if c == '2' and not kp:
                print(f"{RED}API key PTC belum diset. Buka menu [0] Setting.{RST}")
                time.sleep(3); continue
            if c == '4' and (not kf or not kp):
                print(f"{RED}Farm All butuh key Faucet & PTC. Buka menu [0] Setting.{RST}")
                time.sleep(3); continue

            start, end = get_range(len(accounts))
            sel = accounts[start:end + 1]

            if c == '1':
                run_faucet_loop(cfg, sel, apikey=kf)
            elif c == '2':
                run_ptc_loop(cfg, sel, apikey=kp)
            elif c == '3':
                run_video_loop(cfg, sel)     # no apikey
            else:
                run_farm_all(cfg, sel, apikey_faucet=kf, apikey_ptc=kp)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YEL}Dihentikan user.{RST}")