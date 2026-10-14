#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HOTFAUCET.in AutoClaimer — Python port
- Login:  GET / → skip jika cookie udah auth → else solve icaptcha → POST /auth/login
- Faucet: GET /faucet/currency/{coin} → solve icaptcha → POST /faucet/verify/{coin}
- Solver: IconCaptcha v4.0.1 direct (brute force coordinate, no API)
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
CONFIG_FILE   = "hotfaucet_config.json"      # ← pisah dari config.json feyorra

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
# CONFIG — with safety keys
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

    # ── SAFETY: setdefault semua key wajib ──
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

    # Kalau wallet atau cookie kosong, prompt ulang
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
    print(f"{PUTIH}─────────────────────────────────────────────\n")

# ═══════════════════════════════════════════════════════════
# HEADER HELPER — with safe .get() fallback
# ═══════════════════════════════════════════════════════════
def base_headers(cfg, referer=None, content_type=None, origin=None, host_header=None):
    ua = cfg.get("user_agent") or DEFAULT_UA
    h = {
        "host": host_header or DOMAIN,
        "user-agent": ua,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "id-ID,id;q=0.9,en;q=0.8",
        "upgrade-insecure-requests": "1",
        "cache-control": "max-age=0",
        "cookie": cfg.get("cookie", ""),
    }
    if referer:
        h["referer"] = referer
    if content_type:
        h["content-type"] = content_type
    if origin:
        h["origin"] = origin
    return h

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
        "cookie": cfg.get("cookie", ""),
    }

    # ── LOAD ──
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
            res = session.post(endpoint, data={"payload": encoded},
                               headers=headers, timeout=15)
            cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), res)
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

    # ── SELECTION (wider spread) ──
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
            res = session.post(endpoint, data=mp_body.encode('utf-8'),
                               headers=headers, timeout=15)
            cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), res)
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
# COOKIE HELPERS
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════
def login(cfg, session):
    try:
        r = session.get(HOST + "/",
                        headers=base_headers(cfg, referer=HOST + "/"),
                        timeout=30, allow_redirects=True)
    except Exception as e:
        print(f"{PUTIH}[!] {MERAH}homepage fetch error: {e}")
        return False

    cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), r)
    save_config(cfg)

    page = r.text or ""
    print(f"{PUTIH}[*] homepage: {HIJAU}{len(page)} byte{PUTIH} (http {r.status_code})")

    if "Dashboard | HOTFAUCET" in page or "Welcome back" in page:
        print(f"{PUTIH}[+] {HIJAU}cookie udah login (skip login step)")
        return True

    if 'name="wallet"' not in page and "_iconcaptcha-token" not in page:
        print(f"{PUTIH}[!] {KUNING}bukan login page & bukan dashboard")
        with open("debug_home.html", "w", encoding="utf-8") as f:
            f.write(page)
        print(f"{PUTIH}[i] saved: debug_home.html")
        return False

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
        with open("debug_home.html", "w", encoding="utf-8") as f:
            f.write(page)
        return False

    form_time = int(time.time())
    mf = re.search(r'name\s*=\s*["\']form_time["\'][^>]*?value\s*=\s*["\']([^"\']+)["\']',
                   page, re.IGNORECASE)
    if mf:
        form_time = mf.group(1)

    print(f"{PUTIH}[*] icon_token : {HIJAU}{icon_token[:24]}...")

    solved = solve_icaptcha(ICAP_ENDPOINT, icon_token, cfg, session, host_url=HOST)
    if not solved:
        print(f"{PUTIH}[!] {MERAH}solve fail")
        return False
    save_config(cfg)

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

    h = base_headers(cfg, referer=HOST + "/",
                     content_type="application/x-www-form-urlencoded",
                     origin=HOST)

    try:
        r = session.post(HOST + "/auth/login", data=payload, headers=h,
                         timeout=30, allow_redirects=True)
    except Exception as e:
        print(f"{PUTIH}[!] {MERAH}login post error: {e}")
        return False

    cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), r)
    save_config(cfg)

    resp = r.text or ""
    if ("Login Successful" in resp or "Welcome back" in resp or "Dashboard" in resp):
        print(f"{PUTIH}[+] {HIJAU}LOGIN OK")
        return True

    print(f"{PUTIH}[!] {MERAH}login fail (http {r.status_code})")
    with open("debug_login.html", "w", encoding="utf-8") as f:
        f.write(resp)
    return False

# ═══════════════════════════════════════════════════════════
# GET CURRENCIES
# ═══════════════════════════════════════════════════════════
def get_currencies(cfg, session):
    h = base_headers(cfg, referer=HOST + "/")
    try:
        r = session.get(HOST + "/dashboard", headers=h, timeout=30)
    except Exception as e:
        print(f"{PUTIH}[!] dash fetch error: {e}")
        return None

    dash = r.text or ""
    if "Welcome back" not in dash and "Dashboard" not in dash:
        with open("debug_dash.html", "w", encoding="utf-8") as f:
            f.write(dash)
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
    h = base_headers(cfg, referer=HOST + "/dashboard")
    try:
        r = session.get(HOST + f"/faucet/currency/{coin}", headers=h, timeout=30)
    except Exception as e:
        print(f"{PUTIH}[!] faucet fetch error: {e}")
        return "retry"

    cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), r)
    save_config(cfg)

    page = r.text or ""
    print(f"{PUTIH}[*] faucet page: {HIJAU}{len(page)} byte")

    m = re.search(r'var wait\s*=\s*(\d+)\s*-\s*1', page)
    if m:
        wait = int(m.group(1))
        if wait > 0:
            print(f"{PUTIH}[*] cooldown {KUNING}{wait}s")
            timer(wait, "[*] cooling")
            return "cooldown"

    if "Complete Atleast 1 Shortlinks" in page:
        print(f"{PUTIH}[!] {KUNING}perlu shortlink manual")
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
        print(f"{PUTIH}[!] {MERAH}missing tokens")
        with open("debug_faucet.html", "w", encoding="utf-8") as f:
            f.write(page)
        return "retry"

    print(f"{PUTIH}[*] claim_token: {HIJAU}{claim_token[:20]}...")

    solved = solve_icaptcha(ICAP_ENDPOINT, icon_token, cfg, session, host_url=HOST)
    if not solved:
        print(f"{PUTIH}[!] {MERAH}solve fail")
        return "retry"
    save_config(cfg)

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

    h = base_headers(cfg, referer=HOST + f"/faucet/currency/{coin}",
                     content_type="application/x-www-form-urlencoded",
                     origin=HOST)

    try:
        r = session.post(HOST + f"/faucet/verify/{coin}", data=payload,
                         headers=h, timeout=30, allow_redirects=True)
    except Exception as e:
        print(f"{PUTIH}[!] verify post error: {e}")
        return "retry"

    cfg["cookie"] = merge_cookie(cfg.get("cookie", ""), r)
    save_config(cfg)

    resp = r.text or ""

    with open("debug_verify_last.html", "w", encoding="utf-8") as f:
        f.write(resp)

    if "has been sent to your FaucetPay" in resp:
        mm = re.search(r"html:\s*'([^']+)'", resp)
        msg = mm.group(1) if mm else "Claimed!"
        print(f"{PUTIH}[+] {HIJAU}CLAIM OK: {msg.strip()}")
        wait = 10
        mw = re.search(r'var wait\s*=\s*(\d+)\s*-\s*1', resp)
        if mw:
            wait = int(mw.group(1))
        timer(wait, "[*] next")
        return "ok"

    if "does not have sufficient funds" in resp:
        print(f"{PUTIH}[!] {KUNING}faucet kosong")
        return "empty"

    if "Invalid" in resp:
        print(f"{PUTIH}[!] {MERAH}invalid captcha/token")
        time.sleep(2)
        return "retry"

    if "not verified" in resp:
        print(f"{PUTIH}[!] {MERAH}akun belum verify telegram")
        return "unverified"

    print(f"{PUTIH}[?] {KUNING}response unknown (http {r.status_code})")
    return "retry"

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    clear()
    banner()

    cfg = get_config()
    session = build_session()
    sync_session_cookies(session, cfg)

    print(f"{PUTIH}[*] attempting login...")
    tries = 0
    while not login(cfg, session):
        tries += 1
        if tries >= 3:
            print(f"{MERAH}login gagal 3x. cek debug files.")
            input(f"\n{PUTIH}Press Enter to continue...")
            return
        print(f"{PUTIH}[!] retry login ({tries}/3)...")
        time.sleep(3)

    clear()
    banner()

    sync_session_cookies(session, cfg)
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
    print(f"{PUTIH}\nchosee: {MERAH}", end="")
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
        elif res == "empty":
            print(f"{PUTIH}faucet kosong. enter=retry, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
        elif res == "shortlink":
            print(f"{PUTIH}selesai shortlink? enter=lanjut, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
        elif res == "unverified":
            print(f"{PUTIH}verify telegram: {CYAN}{HOST}/dashboard")
            print(f"{PUTIH}enter=retry, q=quit: ", end="")
            if input().strip().lower() == 'q':
                return
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
