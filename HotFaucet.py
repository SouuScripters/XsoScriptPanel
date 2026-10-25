#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOTFAUCET.in AutoClaimer — Python port v3
- Login:  probe /dashboard → skip jika logged → else solve icaptcha → POST /auth/login
- Faucet: GET /faucet/currency/{coin} → solve icaptcha → POST /faucet/verify/{coin}
- Solver: IconCaptcha v4.0.1 direct (brute force coordinate, no API)
- FIX   : login success = probe dashboard (bukan string match homepage)
- FIX   : form_time fresh tiap attempt (hindari stale-timestamp rejection)
- FIX   : cookie murni via session (no header injection, no duplicate state)
- FIX   : cache-bust homepage GET (hindari CF cache return token basi)
- NEW   : diagnose_verify() — alasan gagal claim
"""

import os
import sys
import re
import json
import time
import uuid
import base64
import random
import secrets

import requests
from requests.adapters import HTTPAdapter

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
HOST          = "https://hotfaucet.in"
DOMAIN        = "hotfaucet.in"
SCRIPT_NAME   = "HOTFAUCET.in"
ICAP_ENDPOINT = "https://hotfaucet.in/icaptcha/req"
CONFIG_FILE   = "hotfaucet_config.json"

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
)

HITAM  = "\033[0;30m"
MERAH  = "\033[0;31m"
HIJAU  = "\033[0;32m"
KUNING = "\033[0;33m"
BIRU   = "\033[0;34m"
CYAN   = "\033[0;36m"
PUTIH  = "\033[0;37m"
RESET  = "\033[0m"

DEBUG_DIR = "hotfaucet_debug"


# ═══════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def now_ms():
    return int(time.time() * 1000)


def b64_json(obj):
    return base64.b64encode(
        json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ).decode('utf-8')


def b64_decode_json(s):
    try:
        return json.loads(base64.b64decode(s.strip()).decode('utf-8'))
    except Exception:
        return None


def ensure_debug_dir():
    if not os.path.exists(DEBUG_DIR):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
        except Exception:
            pass


def save_debug(name, content):
    ensure_debug_dir()
    try:
        path = os.path.join(DEBUG_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        return path
    except Exception:
        return None


def timer(seconds, prefix="[!] please wait"):
    seconds = int(seconds)
    if seconds <= 0:
        return
    frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
    idx = 0
    while seconds > 0:
        start = time.time()
        while (time.time() - start) < 1:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            t = f"{h:02d}:{m:02d}:{s:02d}"
            sys.stdout.write(f"{PUTIH}{prefix}{HIJAU} {t} {PUTIH}{frames[idx]}\r")
            sys.stdout.flush()
            time.sleep(0.1)
            idx = (idx + 1) % len(frames)
            if (time.time() - start) >= 1:
                break
        seconds -= 1
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()


def build_session():
    s = requests.Session()
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# ═══════════════════════════════════════════════════════════
# VERIFY DIAGNOSIS
# ═══════════════════════════════════════════════════════════
def _extract_swal(body):
    if not body:
        return None
    m = re.search(r"Swal\.fire\s*\(\s*\{(.*?)\}\s*\)", body, re.DOTALL)
    if not m:
        return None
    block = m.group(1)

    def _get_field(field):
        pat = re.search(rf"{field}\s*:\s*(['\"`])(.*?)\1", block, re.DOTALL)
        if not pat:
            return None
        val = pat.group(2)
        val = val.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
        clean = re.sub(r"<[^>]+>", " ", val)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    title = _get_field("title")
    html  = _get_field("html")
    if title or html:
        return (title or "", html or "")
    return None


def diagnose_verify(body, http_code):
    if not body:
        return ("unknown", f"empty body (http {http_code})", "retry")

    b = body

    if "has been sent to your FaucetPay" in b:
        m = re.search(r"html:\s*'([^']+)'", b)
        msg = (m.group(1) if m else "Claimed!").strip()
        return ("ok", msg, "continue")

    swal = _extract_swal(b)
    swal_title = swal[0] if swal else ""
    swal_html  = swal[1] if swal else ""

    blob = b.lower()

    checks = [
        (["insufficient funds", "not have sufficient", "faucet is empty",
          "faucet has run out", "no funds"],
         "soft_fail", "Faucet saldo kosong", "wait"),

        (["complete atleast 1 shortlink", "complete at least 1 shortlink",
          "shortlink required", "must complete a shortlink",
          "need to complete 1 shortlink"],
         "hard_fail", "Wajib selesaikan 1 shortlink dulu (200-claim rule)", "shortlink"),

        (["you need to join", "join our telegram", "must join telegram",
          "verify your telegram", "telegram not verified", "not verified"],
         "hard_fail", "Akun belum join / verify Telegram", "verify"),

        (["invalid captcha", "captcha incorrect", "wrong captcha",
          "iconcaptcha invalid", "captcha failed", "invalid token"],
         "soft_fail", "Captcha salah / token invalid", "retry"),

        (["you need to wait", "cooldown", "try again in", "you can claim again in"],
         "soft_fail", "Cooldown aktif", "cooldown"),

        (["ip already", "same ip", "multiple accounts", "vpn detected",
          "proxy detected", "ip blacklist"],
         "hard_fail", "IP kena rate-limit / flagged (VPN?)", "quit"),

        (["country not supported", "not available in your country",
          "geo blocked", "region not allowed"],
         "hard_fail", "Negara tidak didukung / geo block", "quit"),

        (["invalid wallet", "wallet not valid", "faucetpay email",
          "wallet address invalid"],
         "hard_fail", "Wallet / FaucetPay email invalid", "quit"),

        (["account banned", "suspended", "banned", "blacklisted"],
         "hard_fail", "Akun kena ban / suspend", "quit"),

        (["payout processing failed", "please try again in a moment"],
         "soft_fail", "Server payout gagal (transient)", "wait"),

        (["not logged in", "please login", "session expired", "unauthorized"],
         "hard_fail", "Session expired / belum login", "relogin"),
    ]

    for kws, status, reason, hint in checks:
        if any(k in blob for k in kws):
            return (status, reason, hint)

    if swal:
        label = swal_title or "alert"
        return ("soft_fail", f"{label}: {swal_html or '(no detail)'}", "retry")

    if 'name="claim_token"' in b or 'id="claim_token"' in b:
        return ("soft_fail",
                f"Server balikin form lagi tanpa alert (http {http_code}) — token/captcha/antibot reject",
                "retry")

    return ("unknown", f"response tidak dikenali (http {http_code}, {len(b)} byte)", "retry")


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
def get_config():
    if not os.path.exists(CONFIG_FILE):
        clear()
        print(f"{PUTIH}────────────────────────────────────────────")
        print(f"{PUTIH} HOTFAUCET.in Setup")
        print(f"{PUTIH}────────────────────────────────────────────")
        wallet = input(f"{PUTIH}FaucetPay Email  : {KUNING}").strip()
        cookie = input(f"{PUTIH}Cookie (browser) : {KUNING}").strip()
        ua     = input(f"{PUTIH}User-Agent (opt) : {KUNING}").strip()
        if not ua:
            ua = DEFAULT_UA
        data = {"wallet": wallet, "cookie": cookie, "user_agent": ua}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"{HIJAU}Saved: {CONFIG_FILE}{RESET}")
        time.sleep(2)
        return data

    try:
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"{MERAH}config.json korup: {e}. Hapus dan run ulang.")
        sys.exit(1)

    changed = False
    if not cfg.get("user_agent"):
        cfg["user_agent"] = DEFAULT_UA
        changed = True
    if "wallet" not in cfg:
        cfg["wallet"] = ""
        changed = True
    if "cookie" not in cfg:
        cfg["cookie"] = ""
        changed = True
    if changed:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)

    if not cfg.get("wallet"):
        print(f"{KUNING}FaucetPay Email belum di-set{RESET}")
        cfg["wallet"] = input(f"{PUTIH}FaucetPay Email : {KUNING}").strip()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    if not cfg.get("cookie"):
        print(f"{KUNING}Cookie belum di-set{RESET}")
        cfg["cookie"] = input(f"{PUTIH}Cookie : {KUNING}").strip()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)

    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def banner():
    print(f"{PUTIH}─────────────────────────────────────────────")
    print(f"{PUTIH} Script  : {CYAN}{SCRIPT_NAME}{PUTIH} AutoClaim")
    print(f"{PUTIH} Captcha : {KUNING}IconCaptcha v4.0.1 (direct solver)")
    print(f"{PUTIH} Diag    : {HIJAU}on — alasan gagal bakal di-print")
    print(f"{PUTIH}─────────────────────────────────────────────\n")


# ═══════════════════════════════════════════════════════════
# HEADER + COOKIE (murni via session)
# ═══════════════════════════════════════════════════════════
def base_headers(cfg, referer=None, content_type=None, origin=None):
    """Cookie TIDAK di-inject via header — pakai session.cookies."""
    ua = cfg.get("user_agent") or DEFAULT_UA
    h = {
        "user-agent": ua,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "id-ID,id;q=0.9,en;q=0.8",
        "upgrade-insecure-requests": "1",
        "cache-control": "max-age=0",
    }
    if referer:
        h["referer"] = referer
    if content_type:
        h["content-type"] = content_type
    if origin:
        h["origin"] = origin
    return h


def merge_cookie(cookie_str, resp):
    try:
        set_cookies = resp.raw.headers.getlist('Set-Cookie')
    except Exception:
        return cookie_str
    if not set_cookies:
        return cookie_str

    jar = {}
    for part in cookie_str.split(';'):
        part = part.strip()
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        jar[k.strip()] = v.strip()

    for line in set_cookies:
        first = line.split(';')[0]
        if '=' not in first:
            continue
        k, v = first.split('=', 1)
        jar[k.strip()] = v.strip()

    return '; '.join(f"{k}={v}" for k, v in jar.items())


def sync_session_cookies(session, cfg):
    """Load cookie string ke session.cookies (source of truth)."""
    session.cookies.clear()
    for part in cfg.get("cookie", "").split(';'):
        part = part.strip()
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        try:
            session.cookies.set(k.strip(), v.strip(), domain=DOMAIN)
        except Exception:
            pass


def sync_back_from_session(cfg, session):
    """Tarik cookie terbaru dari session.cookies → cfg string."""
    jar = {}
    for part in cfg.get("cookie", "").split(';'):
        part = part.strip()
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        jar[k.strip()] = v.strip()
    for c in session.cookies:
        if DOMAIN in (c.domain or ""):
            jar[c.name] = c.value or ""
    cfg["cookie"] = '; '.join(f"{k}={v}" for k, v in jar.items())
    save_config(cfg)


# ═══════════════════════════════════════════════════════════
# ICONCAPTCHA SOLVER
# ═══════════════════════════════════════════════════════════
def solve_icaptcha(endpoint, icon_token, cfg, session, host_url=HOST):
    print(f"{PUTIH}[*] solving icaptcha directly...")

    widget_id = str(uuid.uuid4())
    ts = now_ms()
    ua = cfg.get("user_agent") or DEFAULT_UA

    base_h = {
        "X-Requested-With": "XMLHttpRequest",
        "x-iconcaptcha-token": icon_token,
        "Referer": host_url + "/",
        "Origin": host_url,
        "User-Agent": ua,
        "Accept": "*/*",
    }

    load_dict = {
        "widgetId": widget_id,
        "action": "LOAD",
        "theme": "light",
        "token": icon_token,
        "timestamp": ts,
        "initTimestamp": ts - 2000,
    }
    encoded = b64_json(load_dict)

    challenge_id = None
    for retry in range(3):
        headers = dict(base_h)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            sync_session_cookies(session, cfg)
            res = session.post(endpoint, data={"payload": encoded},
                               headers=headers, timeout=15)
            sync_back_from_session(cfg, session)
            if res.text:
                decoded = b64_decode_json(res.text)
                if decoded and decoded.get("identifier"):
                    challenge_id = decoded["identifier"]
                    print(f"{PUTIH}[+] ic LOAD ok. cid: {HIJAU}{challenge_id[:18]}...")
                    break
                else:
                    print(f"{PUTIH}[?] ic LOAD resp: {res.text[:80]}")
        except Exception as e:
            print(f"{PUTIH}[!] ic LOAD error: {e}")
        time.sleep(1)

    if not challenge_id:
        print(f"{PUTIH}[!] {MERAH}ic LOAD fail")
        return None

    icon_centers = [27, 80, 133, 187, 240, 293]
    attempts = []
    for _ in range(3):
        for cx in icon_centers:
            jx = cx + random.randint(-8, 8)
            jy = random.randint(20, 32)
            attempts.append((jx, jy))
    random.shuffle(attempts)

    for i, (px, py) in enumerate(attempts):
        ts = now_ms()
        sel = {
            "x": px,
            "y": py,
            "width": 320,
            "token": icon_token,
            "action": "SELECTION",
            "widgetId": widget_id,
            "timestamp": ts,
            "challengeId": challenge_id,
            "initTimestamp": ts - 2000,
        }
        encoded_sel = b64_json(sel)
        boundary = "----WebKitFormBoundary" + secrets.token_hex(8)
        mp_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="payload"\r\n\r\n'
            f"{encoded_sel}\r\n"
            f"--{boundary}--\r\n"
        )

        headers = dict(base_h)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        try:
            sync_session_cookies(session, cfg)
            res = session.post(endpoint, data=mp_body.encode('utf-8'),
                               headers=headers, timeout=15)
            sync_back_from_session(cfg, session)
            if res.text:
                decoded = b64_decode_json(res.text)
                if decoded and decoded.get("completed") is True:
                    print(f"{PUTIH}[+] {HIJAU}ic SELECTION ok (try #{i+1}, x={px}, y={py})")
                    return {
                        "_iconcaptcha-token": icon_token,
                        "ic-rq": "1",
                        "ic-wid": widget_id,
                        "ic-cid": challenge_id,
                        "ic-hp": "",
                    }
                if decoded and decoded.get("error"):
                    print(f"{PUTIH}[?] ic err: {json.dumps(decoded)}")
        except Exception as e:
            print(f"{PUTIH}[!] ic SELECTION error: {e}")
        time.sleep(0.3)

    print(f"{PUTIH}[!] {MERAH}ic SELECTION exhausted")
    return None


# ═══════════════════════════════════════════════════════════
# DASHBOARD PROBE — deteksi logged-in
# ═══════════════════════════════════════════════════════════
def _probe_dashboard(cfg, session, quiet=False):
    """
    Return True jika cookie valid (session logged in).
    Tanda: body dashboard mengandung link /logout.
    """
    sync_session_cookies(session, cfg)
    try:
        r = session.get(
            HOST + "/dashboard",
            headers=base_headers(cfg, referer=HOST + "/"),
            timeout=20, allow_redirects=True
        )
    except Exception as e:
        if not quiet:
            print(f"{PUTIH}[!] {MERAH}dash probe error: {e}")
        return False

    sync_back_from_session(cfg, session)

    if r.status_code != 200:
        if not quiet:
            print(f"{PUTIH}[!] dash probe http {r.status_code}")
        return False

    body = r.text or ""

    # marker paling reliable: link logout ada di semua page yg authenticated
    if "/logout" in body or ">Logout<" in body or "Logout" in body:
        return True

    # fallback markers
    if "Dashboard | HOTFAUCET" in body and "Welcome" in body:
        return True

    return False


# ═══════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════
def login(cfg, session):
    # ── STEP 1: probe cookie yg ada ──
    print(f"{PUTIH}[*] probing session...")
    if _probe_dashboard(cfg, session):
        print(f"{PUTIH}[+] {HIJAU}cookie valid — skip login step")
        return True

    print(f"{PUTIH}[*] cookie invalid — attempting fresh login")

    # ── STEP 2: ambil homepage (cache-bust) ──
    bust_ts = int(time.time())
    home_url = f"{HOST}/?_={bust_ts}"
    sync_session_cookies(session, cfg)
    try:
        r = session.get(
            home_url,
            headers=base_headers(cfg, referer=HOST + "/"),
            timeout=30, allow_redirects=True
        )
    except Exception as e:
        print(f"{PUTIH}[!] {MERAH}homepage fetch error: {e}")
        return False

    sync_back_from_session(cfg, session)

    page = r.text or ""
    print(f"{PUTIH}[*] homepage: {HIJAU}{len(page)} byte{PUTIH} (http {r.status_code})")

    # probe lagi — kadang cookie valid setelah hit homepage
    if _probe_dashboard(cfg, session, quiet=True):
        print(f"{PUTIH}[+] {HIJAU}cookie valid setelah refresh homepage — skip login")
        return True

    if 'name="wallet"' not in page and "_iconcaptcha-token" not in page:
        print(f"{PUTIH}[!] {KUNING}bukan login page & bukan dashboard")
        save_debug("login_home.html", page)
        return False

    # ── STEP 3: parse token ──
    icon_token = ""
    m = re.search(r"name\s*=\s*['\"]_iconcaptcha-token['\"][^>]*?value\s*=\s*['\"]([^'\"]+)['\"]",
                  page, re.IGNORECASE)
    if m:
        icon_token = m.group(1)
    else:
        m = re.search(r"value\s*=\s*['\"]([^'\"]+)['\"][^>]*?name\s*=\s*['\"]_iconcaptcha-token['\"]",
                      page, re.IGNORECASE)
        if m:
            icon_token = m.group(1)

    if not icon_token:
        print(f"{PUTIH}[!] {MERAH}_iconcaptcha-token ga ketemu")
        save_debug("login_no_token.html", page)
        return False

    # form_time FRESH — jangan percaya HTML (bisa stale dari cache)
    form_time = int(time.time()) - random.randint(2, 5)

    print(f"{PUTIH}[*] icon_token : {HIJAU}{icon_token[:24]}...")
    print(f"{PUTIH}[*] form_time  : {HIJAU}{form_time} (fresh)")

    # ── STEP 4: solve captcha ──
    solved = solve_icaptcha(ICAP_ENDPOINT, icon_token, cfg, session, host_url=HOST)
    if not solved:
        print(f"{PUTIH}[!] {MERAH}solve fail")
        return False

    # ── STEP 5: POST login ──
    payload = {
        "wallet": cfg.get("wallet", ""),
        "website": "",
        "form_time": form_time,
        "ci_csrf_token": "",
        "captcha": "icaptcha",
        "_iconcaptcha-token": icon_token,
        "ic-rq": "1",
        "ic-wid": solved["ic-wid"],
        "ic-cid": solved["ic-cid"],
        "ic-hp": "",
    }

    sync_session_cookies(session, cfg)
    try:
        r = session.post(
            HOST + "/auth/login",
            data=payload,
            headers=base_headers(cfg, referer=HOST + "/",
                                 content_type="application/x-www-form-urlencoded",
                                 origin=HOST),
            timeout=30, allow_redirects=True
        )
    except Exception as e:
        print(f"{PUTIH}[!] {MERAH}login post error: {e}")
        return False

    sync_back_from_session(cfg, session)

    resp = r.text or ""
    print(f"{PUTIH}[*] login post: {HIJAU}{len(resp)} byte{PUTIH} (http {r.status_code})")

    # ── STEP 6: probe dashboard setelah login ──
    if _probe_dashboard(cfg, session):
        print(f"{PUTIH}[+] {HIJAU}LOGIN OK")
        return True

    # fail — simpan detail
    print(f"{PUTIH}[!] {MERAH}login POST gagal — dashboard tetap tidak accessible")

    # cek swal / error text
    swal = _extract_swal(resp)
    if swal:
        print(f"{PUTIH}[i] swal.title: {KUNING}{swal[0][:80]}")
        print(f"{PUTIH}[i] swal.html : {KUNING}{swal[1][:120]}")

    # cek marker error umum
    blob = resp.lower()
    if "invalid wallet" in blob or "not registered" in blob:
        print(f"{PUTIH}[i] {MERAH}wallet tidak terdaftar / salah")
    elif "invalid captcha" in blob or "captcha" in blob and "error" in blob:
        print(f"{PUTIH}[i] {MERAH}captcha rejected")
    elif "too many" in blob:
        print(f"{PUTIH}[i] {MERAH}rate limit / too many attempts")
    elif "banned" in blob or "suspended" in blob:
        print(f"{PUTIH}[i] {MERAH}akun banned")
    else:
        print(f"{PUTIH}[i] kemungkinan: form_time expired, cf_clearance expired, atau bot-filter")
        print(f"{PUTIH}[i] saran: re-grab cookie dari browser (cf_clearance rotasi)")

    save_debug(f"login_fail_{int(time.time())}.html", resp)
    return False


# ═══════════════════════════════════════════════════════════
# GET CURRENCIES
# ═══════════════════════════════════════════════════════════
def get_currencies(cfg, session):
    sync_session_cookies(session, cfg)
    try:
        r = session.get(HOST + "/dashboard",
                        headers=base_headers(cfg, referer=HOST + "/"),
                        timeout=30)
    except Exception as e:
        print(f"{PUTIH}[!] dash fetch error: {e}")
        return None

    sync_back_from_session(cfg, session)

    dash = r.text or ""
    if "/logout" not in dash and "Dashboard" not in dash:
        save_debug("dash_fail.html", dash)
        return None

    raw = re.findall(r'href="' + re.escape(HOST) + r'/faucet/currency/([^"]+)"', dash)
    currencies = []
    for c in raw:
        if c not in currencies and re.match(r'^[a-z0-9]+$', c):
            currencies.append(c)
    currencies.sort(key=len)
    return currencies


# ═══════════════════════════════════════════════════════════
# CLAIM ONE
# ═══════════════════════════════════════════════════════════
def claim_one(cfg, session, coin):
    sync_session_cookies(session, cfg)
    try:
        r = session.get(HOST + f"/faucet/currency/{coin}",
                        headers=base_headers(cfg, referer=HOST + "/dashboard"),
                        timeout=30)
    except Exception as e:
        print(f"{PUTIH}[!] faucet fetch error: {e}")
        return "retry"

    sync_back_from_session(cfg, session)

    page = r.text or ""
    print(f"{PUTIH}[*] faucet page: {HIJAU}{len(page)} byte")

    m = re.search(r'var wait\s*=\s*(\d+)\s*-\s*1', page)
    if m:
        wait = int(m.group(1))
        if wait > 0:
            print(f"{PUTIH}[*] cooldown {KUNING}{wait}s")
            timer(wait, "[*] cooling")
            return "cooldown"

    if "Complete Atleast 1 Shortlinks" in page or "Complete at least 1 Shortlink" in page:
        print(f"{PUTIH}[!] {KUNING}perlu shortlink manual — {CYAN}{HOST}/links/currency/{coin}")
        return "shortlink"

    icon_token = ""
    m = re.search(r"name\s*=\s*['\"]_iconcaptcha-token['\"][^>]*?value\s*=\s*['\"]([^'\"]+)['\"]",
                  page, re.IGNORECASE)
    if m:
        icon_token = m.group(1)
    else:
        m = re.search(r"value\s*=\s*['\"]([^'\"]+)['\"][^>]*?name\s*=\s*['\"]_iconcaptcha-token['\"]",
                      page, re.IGNORECASE)
        if m:
            icon_token = m.group(1)

    claim_token = ""
    m = re.search(r'id\s*=\s*["\']claim_token["\'][^>]*?value\s*=\s*["\']([^"\']+)["\']',
                  page, re.IGNORECASE)
    if m:
        claim_token = m.group(1)
    else:
        m = re.search(r'name\s*=\s*["\']token["\'][^>]*?value\s*=\s*["\']([^"\']+)["\']',
                      page, re.IGNORECASE)
        if m:
            claim_token = m.group(1)

    csrf = ""
    m = re.search(r'name\s*=\s*["\']ci_csrf_token["\'][^>]*?value\s*=\s*["\']([^"\']*)["\']',
                  page, re.IGNORECASE)
    if m:
        csrf = m.group(1)

    wallet = cfg.get("wallet", "")
    m = re.search(r'name\s*=\s*["\']wallet["\'][^>]*?value\s*=\s*["\']([^"\']+)["\']',
                  page, re.IGNORECASE)
    if m:
        wallet = m.group(1)

    if not icon_token or not claim_token:
        print(f"{PUTIH}[!] {MERAH}missing tokens (icon={bool(icon_token)}, claim={bool(claim_token)})")
        save_debug(f"faucet_{coin}_no_tokens.html", page)
        return "retry"

    print(f"{PUTIH}[*] claim_token: {HIJAU}{claim_token[:20]}...")

    solved = solve_icaptcha(ICAP_ENDPOINT, icon_token, cfg, session, host_url=HOST)
    if not solved:
        print(f"{PUTIH}[!] {MERAH}solve fail")
        return "retry"

    payload = {
        "_email_confirm": "",
        "ci_csrf_token": csrf,
        "token": claim_token,
        "captcha": "icaptcha",
        "_iconcaptcha-token": icon_token,
        "ic-rq": "1",
        "ic-wid": solved["ic-wid"],
        "ic-cid": solved["ic-cid"],
        "ic-hp": "",
        "wallet": wallet,
    }

    sync_session_cookies(session, cfg)
    try:
        r = session.post(HOST + f"/faucet/verify/{coin}", data=payload,
                         headers=base_headers(cfg, referer=HOST + f"/faucet/currency/{coin}",
                                              content_type="application/x-www-form-urlencoded",
                                              origin=HOST),
                         timeout=30, allow_redirects=True)
    except Exception as e:
        print(f"{PUTIH}[!] verify post error: {e}")
        return "retry"

    sync_back_from_session(cfg, session)

    resp = r.text or ""
    http = r.status_code

    status, reason, hint = diagnose_verify(resp, http)

    safe_reason = re.sub(r"[^a-zA-Z0-9_-]", "_", reason)[:40]
    dbg_name = f"verify_{coin}_{int(time.time())}_{safe_reason}.html"
    save_debug(dbg_name, resp)

    if status == "ok":
        print(f"{PUTIH}[+] {HIJAU}CLAIM OK: {reason.strip()}")
        wait = 10
        mw = re.search(r'var wait\s*=\s*(\d+)\s*-\s*1', resp)
        if mw:
            wait = int(mw.group(1))
        timer(wait, "[*] next")
        return "ok"

    color = MERAH if status == "hard_fail" else KUNING
    print(f"{PUTIH}[!] {color}CLAIM FAIL [{status}] — {reason}")
    print(f"{PUTIH}[i] hint: {CYAN}{hint}{PUTIH} | http={http} | saved {HIJAU}{dbg_name}")

    swal = _extract_swal(resp)
    if swal:
        print(f"{PUTIH}[i] swal.title: {KUNING}{swal[0][:80]}")
        print(f"{PUTIH}[i] swal.html : {KUNING}{swal[1][:120]}")

    if hint == "quit":
        return "fatal"
    if hint == "shortlink":
        return "shortlink"
    if hint == "verify":
        return "unverified"
    if hint == "cooldown":
        return "cooldown"
    if hint == "wait":
        timer(30, "[*] cooling")
        return "retry"
    if hint == "relogin":
        return "relogin"
    return "retry"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    clear()
    banner()
    ensure_debug_dir()

    cfg = get_config()
    session = build_session()
    sync_session_cookies(session, cfg)

    print(f"{PUTIH}[*] attempting login...")
    tries = 0
    while not login(cfg, session):
        tries += 1
        if tries >= 3:
            print(f"{MERAH}login gagal 3x. cek {DEBUG_DIR}/")
            print(f"{PUTIH}saran: {KUNING}cookie browser expired — re-grab dari DevTools")
            print(f"{PUTIH}        (cf_clearance biasanya cuma bertahan beberapa jam)")
            input(f"\n{PUTIH}Press Enter to continue...")
            return
        print(f"{PUTIH}[!] retry login ({tries}/3)...")
        time.sleep(3)

    clear()
    banner()

    currencies = get_currencies(cfg, session)
    if not currencies:
        print(f"{MERAH}gagal ambil daftar coin")
        input(f"\n{PUTIH}Press Enter to continue...")
        return

    cols = 4
    total = len(currencies)
    print(f"{PUTIH}Available Faucets:\n")
    for i, cur in enumerate(currencies):
        n = i + 1
        sys.stdout.write(f"{PUTIH}({n:>2}) {HIJAU}{cur.upper():<6}{PUTIH}")
        if (i + 1) % cols == 0 or i == total - 1:
            sys.stdout.write("\n")
    print(f"{PUTIH}\nchoose: {MERAH}", end="")
    choice = input().strip()

    if not choice.isdigit():
        print(f"{PUTIH}invalid!")
        time.sleep(2)
        return
    idx = int(choice)
    if idx < 1 or idx > total:
        print(f"{PUTIH}invalid (1-{total})")
        time.sleep(2)
        return
    coin = currencies[idx - 1]
    print(f"{PUTIH}selected: {HIJAU}{coin.upper()}\n")

    claimed = 0
    errs = 0
    while True:
        print(f"{PUTIH}─────────────────────────────────────────────")
        print(f"{PUTIH}[#{claimed+1}] {HIJAU}{coin.upper()}{PUTIH} claim attempt")
        print(f"{PUTIH}─────────────────────────────────────────────")

        try:
            res = claim_one(cfg, session, coin)
        except KeyboardInterrupt:
            print(f"\n{PUTIH}interrupted.")
            return
        except Exception as e:
            print(f"{PUTIH}[!] {MERAH}exception: {e}")
            res = "retry"

        if res == "ok":
            claimed += 1
            errs = 0
        elif res == "cooldown":
            errs = 0
        elif res == "fatal":
            print(f"{PUTIH}{MERAH}fatal — stop.{PUTIH} enter=retry, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
            errs = 0
        elif res == "shortlink":
            print(f"{PUTIH}selesai shortlink? enter=lanjut, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
        elif res == "unverified":
            print(f"{PUTIH}verify telegram: {CYAN}{HOST}/dashboard")
            print(f"{PUTIH}enter=retry, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
        elif res == "relogin":
            print(f"{PUTIH}session mati — relogin...")
            tries = 0
            while not login(cfg, session) and tries < 3:
                tries += 1
                time.sleep(3)
            errs = 0
        else:
            errs += 1
            if errs >= 5:
                print(f"{MERAH}\n5x error berturut.")
                print(f"{PUTIH}enter=retry, q=quit: ", end="")
                if input().strip().lower() == 'q':
                    return
                errs = 0
            time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{PUTIH}stopped by user.{RESET}")
        sys.exit(0)
