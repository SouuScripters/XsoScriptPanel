#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BullyDao Auto Bot v7 — Fixed CF Cookie Sync
- curl_cffi (fast path) + Seledroid fallback
- Sync header Android lengkap setelah Seledroid
- Multipart encoder manual
"""

import json, os, sys, time, random, re, subprocess, tempfile
from datetime import datetime
from pathlib import Path
from curl_cffi import requests as cf_requests

# ==================== CONFIG ====================
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "bconfig.json"
BASE = "https://bullydao.org"

DEFAULT_CONFIG = {
    "u": "",
    "cookies_extra": "",
    "enable_auto_login": True,
    "enable_faucet": True,
    "enable_jackpot": True,
    "enable_balance_check": True,
    "human_delay_min": 8,
    "human_delay_max": 20,
    "faucet_cooldown_default": 300,
    "jackpot_cooldown_default": 600,
    "session_check_every": 10,
    "cf_impersonate": "chrome_android",
    "use_seledroid_fallback": True,
}

LOOP_DELAY = 15

# ==================== SELEDROID SCRIPT ====================
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
    try: from seledroid import webdriver as sd
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
        log("Failed (%s)" % e)
        return {"cf_clearance": None, "user_agent": None}
    if not clr:
        log("Failed (no cf_clearance)")
        return {"cf_clearance": None, "user_agent": None}
    tok = clr.split('=', 1)[1] if '=' in clr else clr
    log("Success!")
    return {"cf_clearance": tok, "user_agent": ua}
if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    print(json.dumps(bypass_cf(sys.argv[1])))
'''

class C:
    R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; MAGENTA = "\033[95m"; BLUE = "\033[94m"
    WHITE = "\033[97m"; GRAY = "\033[90m"

STATE = {
    "balance": None, "total_claims": 0,
    "faucet_next_at": 0.0, "jackpot_next_at": 0.0,
    "faucet_claimed": 0, "jackpot_claimed": 0,
    "faucet_coins": 0, "jackpot_coins": 0,
    "daily_used": 0, "daily_limit": 0,
    "logged_in": False, "started_at": time.time(),
    "cf_blocked": 0, "seledroid_used": 0,
}
current_cfg = None

# ==================== UI ====================
def clear(): os.system("cls" if os.name == "nt" else "clear")
def now_str(): return datetime.now().strftime("%H:%M:%S")
def fmt_duration(s):
    s = int(max(0, s)); h, rem = divmod(s, 3600); m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

def banner():
    clear()
    print(f"""{C.CYAN}{C.BOLD}
   ╔══════════════════════════════════════════════════════════════╗
   ║     🌊  B U L L Y D A O  v7 — CF Header Sync  🌊             ║
   ╚══════════════════════════════════════════════════════════════╝
""")

def log(msg, level="info"):
    icons = {
        "info": f"{C.CYAN}ℹ{C.R}", "ok": f"{C.GREEN}✔{C.R}", "warn": f"{C.YELLOW}⚠{C.R}",
        "err": f"{C.RED}✖{C.R}", "coin": f"{C.YELLOW}🪙{C.R}", "dice": f"{C.MAGENTA}🎲{C.R}",
        "auth": f"{C.BLUE}🔐{C.R}", "captcha": f"{C.BLUE}🛡 {C.R}", "wait": f"{C.GRAY}⏳{C.R}",
        "bal": f"{C.GREEN}💰{C.R}", "cf": f"{C.YELLOW}☁️ {C.R}", "sd": f"{C.MAGENTA}📱{C.R}",
    }
    print(f"{C.GRAY}[{now_str()}]{C.R} {icons.get(level, icons['info'])}  {msg}", flush=True)

def section(t):
    print(f"\n{C.BOLD}{C.GREEN}▸ {t}{C.R}")
    print(f"{C.GRAY}{'─' * 52}{C.R}")

def status_bar(cfg):
    now = time.time()
    bal = STATE["balance"]
    bal_str = f"{C.GREEN}{bal:,.2f}{C.R} DAO" if bal is not None else f"{C.GRAY}---{C.R}"
    f_cd = STATE["faucet_next_at"] - now
    f_str = f"{C.GREEN}READY{C.R}" if f_cd <= 0 else f"{C.YELLOW}{fmt_duration(f_cd)}{C.R}"
    j_cd = STATE["jackpot_next_at"] - now
    j_str = f"{C.GREEN}READY{C.R}" if j_cd <= 0 else f"{C.YELLOW}{fmt_duration(j_cd)}{C.R}"
    runtime = fmt_duration(time.time() - STATE["started_at"])
    auth_str = f"{C.GREEN}✓{C.R}" if STATE["logged_in"] else f"{C.RED}✗{C.R}"
    print(f"{C.GRAY}│{C.R} auth:{auth_str} 💰 {bal_str} 🚰 {f_str} 🎲 {j_str} 📱SD:{STATE['seledroid_used']} ⏱ {C.CYAN}{runtime}{C.R}")

# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists(): return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else False
    except: return False

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except: pass

def menu():
    banner()
    cfg = load_config() or {}
    u = cfg.get("u", "") or "(empty)"
    has_cf = "cf_clearance=" in (cfg.get("cookies_extra") or "")
    print(f"{C.GRAY}Account   :{C.R} {C.CYAN}{u}{C.R}")
    print(f"{C.GRAY}CF cookie :{C.R} {C.GREEN + '✓ set' if has_cf else C.YELLOW + '✗ not set'}{C.R}")
    print(f"{C.GRAY}Impersonate:{C.R} {cfg.get('cf_impersonate', 'chrome_android')}")
    print(f"{C.GRAY}Seledroid :{C.R} {'ON' if cfg.get('use_seledroid_fallback', True) else 'OFF'}")
    print(f"\n{C.BOLD}{C.GREEN}MENU:{C.R}")
    print(f"  {C.YELLOW}[1]{C.R} Start Bot")
    print(f"  {C.YELLOW}[2]{C.R} Set Email")
    print(f"  {C.YELLOW}[3]{C.R} Set Cookies")
    print(f"  {C.YELLOW}[4]{C.R} Test curl_cffi Bypass")
    print(f"  {C.YELLOW}[5]{C.R} Test Seledroid Bypass")
    print(f"  {C.YELLOW}[0]{C.R} Exit")
    try: return input(f"\n{C.CYAN}Pilih → {C.R}").strip()
    except: return "0"

def menu_config_field(label, key):
    banner(); section(f"Set {label}")
    cfg = load_config() or dict(DEFAULT_CONFIG)
    cur = cfg.get(key, "")
    if cur: print(f"{C.GRAY}Current: {C.CYAN}{cur[:60]}{C.R}")
    try: val = input(f"  {C.CYAN}{label}{C.R} (empty=skip): ").strip()
    except: return
    if val:
        cfg[key] = val; save_config(cfg)
        print(f"\n{C.GREEN}✔ Saved.{C.R}")
    else: print(f"\n{C.YELLOW}Skip.{C.R}")
    time.sleep(1.2)

def menu_loop():
    while True:
        choice = menu()
        if choice == "1":
            cfg = load_config() or {}
            if not cfg.get("u"):
                banner(); print(f"{C.RED}Email belum di-set.{C.R}"); time.sleep(2); continue
            return dict(cfg)
        elif choice == "2": menu_config_field("Email", "u")
        elif choice == "3": menu_config_field("Cookies", "cookies_extra")
        elif choice == "4": test_cf_curl()
        elif choice == "5": test_cf_seledroid()
        elif choice == "0": return None
        else: time.sleep(1)

def test_cf_curl():
    banner(); section("Test curl_cffi Bypass")
    cfg = load_config() or {}
    session = make_session(cfg.get("cookies_extra", ""), cfg)
    try:
        r = session.get(f"{BASE}/faucet", timeout=30, allow_redirects=True)
        if is_cf_challenge(r):
            print(f"{C.RED}✖ CF blocked. Pakai Seledroid bypass (menu [5]).{C.R}")
        else:
            print(f"{C.GREEN}✔ Bypassed! HTTP {r.status_code}, {len(r.text)} bytes{C.R}")
    except Exception as e:
        print(f"{C.RED}✖ Error: {e}{C.R}")
    input(f"\n{C.DIM}Enter...{C.R}")

def test_cf_seledroid():
    banner(); section("Test Seledroid Bypass")
    print(f"{C.GRAY}Target: {C.CYAN}{BASE}/faucet{C.R}\n")
    result = seledroid_bypass(f"{BASE}/faucet")
    if result and result.get("cf_clearance"):
        print(f"\n{C.GREEN}✔ Success!{C.R}")
        print(f"{C.GRAY}cf_clearance: {C.CYAN}{result['cf_clearance'][:60]}...{C.R}")
        print(f"{C.GRAY}user_agent  : {C.CYAN}{result.get('user_agent')}{C.R}")
        cfg = load_config() or dict(DEFAULT_CONFIG)
        cfg["cookies_extra"] = f"cf_clearance={result['cf_clearance']}"
        save_config(cfg)
        print(f"\n{C.GREEN}✔ Saved to config.{C.R}")
    else:
        print(f"\n{C.RED}✖ Seledroid gagal.{C.R}")
    input(f"\n{C.DIM}Enter...{C.R}")

# ==================== SELEDROID EXEC ====================
def seledroid_bypass(target_url):
    log("Menjalankan Seledroid bypass... (30-90s)", "sd")
    tmp = Path(tempfile.gettempdir()) / f"seledroid_{int(time.time())}.py"
    try: tmp.write_text(SELEDROID_SCRIPT, encoding="utf-8")
    except Exception as e: log(f"Gagal tulis temp: {e}", "err"); return None
    python_bin = "python" if os.name == "nt" else "python3"
    try:
        proc = subprocess.run([python_bin, str(tmp), target_url], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        log("Seledroid timeout (180s)", "err")
        try: tmp.unlink()
        except: pass
        return None
    except Exception as e:
        log(f"Subprocess error: {e}", "err")
        try: tmp.unlink()
        except: pass
        return None
    try: tmp.unlink()
    except: pass
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()[:300]
        log(f"Seledroid exit {proc.returncode}: {err}", "err")
        return None
    out = (proc.stdout or "").strip()
    if not out: log("Seledroid stdout kosong", "err"); return None
    try: data = json.loads(out)
    except Exception as e:
        log(f"JSON parse fail: {e} | raw: {out[:200]}", "err")
        return None
    if not data.get("cf_clearance"):
        log("Seledroid: cf_clearance kosong", "warn"); return None
    log(f"Seledroid sukses! UA={str(data.get('user_agent'))[:50]}", "sd")
    STATE["seledroid_used"] += 1
    return data

# ==================== HTTP ====================
def human_delay(min_s, max_s, label="delay"):
    try: min_s = float(min_s); max_s = float(max_s)
    except: return 0
    if max_s <= 0 or max_s < min_s: return 0
    d = random.uniform(min_s, max_s)
    log(f"{label}: {d:.1f}s", "wait"); time.sleep(d)
    return d

def make_session(extra_cookies="", cfg=None):
    impersonate = (cfg or {}).get("cf_impersonate", "chrome_android")
    try: s = cf_requests.Session(impersonate=impersonate)
    except: s = cf_requests.Session(impersonate="chrome")
    s.headers.update({"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"})
    if extra_cookies:
        for part in extra_cookies.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                try: s.cookies.set(k.strip(), v.strip(), domain="bullydao.org")
                except: pass
    return s

def is_cf_challenge(r):
    if not r: return False
    if r.status_code in (403, 503): return True
    text = (r.text or "")[:3000]
    return any(m in text for m in ["Just a moment", "cf-chl", "challenge-platform", "cf-error-details"])

# ==================== MULTIPART ENCODER ====================
def encode_multipart(fields):
    boundary = '----WebKitFormBoundary' + ''.join(random.choices('0123456789abcdef', k=16))
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}')
        parts.append(f'Content-Disposition: form-data; name="{name}"')
        parts.append('')
        parts.append(str(value))
    parts.append(f'--{boundary}--')
    parts.append('')
    body = '\r\n'.join(parts).encode('utf-8')
    return body, f'multipart/form-data; boundary={boundary}'

def post_multipart(session, url, fields, extra_headers=None):
    body, ct = encode_multipart(fields)
    h = {"Origin": BASE, "Referer": url, "Accept": "application/json, */*; q=0.01",
         "X-Requested-With": "XMLHttpRequest", "Content-Type": ct}
    if extra_headers: h.update(extra_headers)
    return session.post(url, data=body, headers=h, timeout=45, allow_redirects=False)

# ==================== PARSER ====================
def parse_target_icon(html):
    m = re.search(r'Please click the[^\[]*\[\s*(\w+)\s*<i', html, re.IGNORECASE)
    if m: return m.group(1).lower()
    m = re.search(r'Please click the[^\[]*\[\s*(\w+)', html, re.IGNORECASE)
    return m.group(1).lower() if m else None

def parse_balance(html):
    idx = html.find("Total Available Balance")
    if idx == -1: return None
    chunk = html[idx:idx + 1500]
    m = re.search(r'<span[^>]*class="[^"]*font-num[^"]*"[^>]*>\s*([\d,]+(?:\.\d+)?)\s*</span>', chunk)
    if m: return float(m.group(1).replace(",", ""))
    m = re.search(r'>\s*([\d,]+\.\d+)\s*<', chunk)
    return float(m.group(1).replace(",", "")) if m else None

def parse_daily_limit(html):
    m = re.search(r"Daily Limit:\s*<[^>]*>(\d+)\s*/\s*(\d+)", html)
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r"Daily Limit:\s*(\d+)\s*/\s*(\d+)", html)
    return (int(m.group(1)), int(m.group(2))) if m else None

def parse_faucet_cooldown(html):
    m = re.search(r"let\s+timeLeft\s*=\s*(\d+)", html)
    if m: return int(m.group(1))
    m = re.search(r"Next Claim in[^\d]{0,15}(\d{1,2}):(\d{2})", html)
    if m: return int(m.group(1)) * 60 + int(m.group(2))
    return 0 if ("Ready to Claim" in html or "Claim 20 DAO" in html) else None

def parse_jackpot_cooldown(html):
    m = re.search(r"let\s+jpTimeLeft\s*=\s*(\d+)", html)
    if m: return int(m.group(1))
    return 0 if ("Ready to Roll" in html or "Roll Lucky Number" in html) else None

def is_account_page(html):
    if 'name="action_auth"' in html and "Direct FaucetPay Access" in html: return False
    markers = ["Connected Account", "Total Available Balance", "Bullydao — Cabinet"]
    if sum(1 for m in markers if m in html) >= 2: return True
    return 'href="https://bullydao.org/logout"' in html

# ==================== CF BYPASS HANDLER ====================
def handle_cf_challenge(session, cfg, target_url, r):
    STATE["cf_blocked"] += 1
    log(f"CF Challenge di {target_url} → Seledroid", "cf")
    if not cfg.get("use_seledroid_fallback", True):
        log("Seledroid fallback OFF", "warn")
        return None
    result = seledroid_bypass(target_url)
    if not result or not result.get("cf_clearance"):
        return None
    try:
        session.cookies.set("cf_clearance", result["cf_clearance"], domain=".bullydao.org")
    except Exception as e:
        log(f"Cookie set error: {e}", "err")

    # 🔥 Sync SEMUA header browser Android dari log network
    try:
        session.headers.update({
            "User-Agent": result["user_agent"] or session.headers.get("User-Agent"),
            "sec-ch-ua": '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-ch-ua-full-version": '"127.0.6533.144"',
            "sec-ch-ua-platform-version": '"16.0.0"',
            "sec-ch-ua-model": '"SM-A556E"',
            "sec-ch-ua-bitness": '""',
            "sec-ch-ua-arch": '""',
            "sec-ch-ua-full-version-list": '"Chromium";v="127.0.6533.144", "Not)A;Brand";v="99.0.0.0", "Microsoft Edge Simulate";v="127.0.6533.144", "Lemur";v="127.0.6533.144"',
        })
        # Ganti impersonate ke chrome_android biar TLS match
        try:
            # Note: cf_requests tidak bisa re-impersonate di session yang sama,
            # tapi kita bisa set header manual sebagai workaround
            pass
        except: pass
        log("Headers Android synced", "ok")
    except Exception as e:
        log(f"Header sync err: {e}", "warn")

    # Persist ke config
    try:
        cur = cfg.get("cookies_extra", "") or ""
        parts = [p.strip() for p in cur.split(";") if p.strip() and not p.strip().startswith("cf_clearance=")]
        parts.append(f"cf_clearance={result['cf_clearance']}")
        cfg["cookies_extra"] = "; ".join(parts)
        save_config(cfg)
    except: pass

    return session

# ==================== ACTIONS ====================
def verify_session(session, cfg):
    try:
        r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)
        if is_cf_challenge(r):
            session = handle_cf_challenge(session, cfg, f"{BASE}/cabinet", r)
            if not session: return False
            r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)
        if r.ok and is_account_page(r.text):
            STATE["logged_in"] = True
            return True
    except: pass
    STATE["logged_in"] = False
    return False

def check_balance(session, cfg):
    try:
        r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)
        if is_cf_challenge(r):
            session = handle_cf_challenge(session, cfg, f"{BASE}/cabinet", r)
            if not session: return False
            r = session.get(f"{BASE}/cabinet", timeout=30, allow_redirects=True)
        if not r.ok: return False
        html = r.text
        if not is_account_page(html):
            STATE["logged_in"] = False; return False
        STATE["logged_in"] = True
        bal = parse_balance(html)
        if bal is not None:
            if STATE["balance"] != bal: log(f"Balance: {C.GREEN}{bal:,.2f}{C.R} DAO", "bal")
            STATE["balance"] = bal
        return True
    except Exception as e:
        log(f"Balance err: {e}", "err"); return False

def do_login(session, cfg):
    log("Auto login...", "auth")
    try: r = session.get(f"{BASE}/", timeout=30)
    except Exception as e: log(f"Homepage err: {e}", "err"); return False

    if is_cf_challenge(r):
        new_session = handle_cf_challenge(session, cfg, BASE, r)
        if not new_session: return False
        session = new_session
        try: r = session.get(f"{BASE}/", timeout=30)
        except Exception as e: log(f"Retry homepage err: {e}", "err"); return False
        if is_cf_challenge(r):
            log("Masih CF challenge setelah Seledroid. Coba test ulang nanti.", "err")
            return False

    html = r.text
    if is_account_page(html):
        log("Session masih valid", "ok"); STATE["logged_in"] = True; return True

    target_icon = parse_target_icon(html)
    if not target_icon:
        log("Target icon tidak ditemukan", "err")
        with open("debug_login.html", "w", encoding="utf-8") as f: f.write(html)
        return False

    log(f"Target icon: {C.MAGENTA}{target_icon}{C.R}", "captcha")
    data = {"action_auth": "1", "captcha_type": "icon", "captcha_selected_icon": target_icon, "email": cfg["u"], "cf-turnstile-response": ""}
    h = {"Origin": BASE, "Referer": f"{BASE}/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Content-Type": "application/x-www-form-urlencoded", "Upgrade-Insecure-Requests": "1"}

    try: r = session.post(f"{BASE}/", data=data, headers=h, timeout=45, allow_redirects=True)
    except Exception as e: log(f"Login POST err: {e}", "err"); return False

    if is_cf_challenge(r):
        new_session = handle_cf_challenge(session, cfg, BASE, r)
        if not new_session: return False
        session = new_session
        try: r = session.post(f"{BASE}/", data=data, headers=h, timeout=45, allow_redirects=True)
        except Exception as e: log(f"Retry login err: {e}", "err"); return False

    if not r.ok: log(f"Login HTTP {r.status_code}", "warn"); return False
    if verify_session(session, cfg): log("Login ✓", "ok"); return True
    log("Login gagal", "err")
    with open("debug_login.html", "w", encoding="utf-8") as f: f.write(r.text)
    return False

def do_faucet(session, cfg):
    log("Faucet claim...", "coin")
    try: r0 = session.get(f"{BASE}/faucet", timeout=30, allow_redirects=True)
    except Exception as e: log(f"Faucet GET err: {e}", "err"); return 60
    if is_cf_challenge(r0):
        session = handle_cf_challenge(session, cfg, f"{BASE}/faucet", r0)
        if not session: return 60
        try: r0 = session.get(f"{BASE}/faucet", timeout=30, allow_redirects=True)
        except: return 60
        if is_cf_challenge(r0): return 60
    html = r0.text
    cd = parse_faucet_cooldown(html)
    if cd is not None and cd > 0:
        STATE["faucet_next_at"] = time.time() + cd; log(f"Faucet cooldown: {fmt_duration(cd)}", "wait"); return cd
    dl = parse_daily_limit(html)
    if dl: STATE["daily_used"], STATE["daily_limit"] = dl
    target_icon = parse_target_icon(html)
    if not target_icon: log("Icon faucet tidak ditemukan", "err"); return 60
    log(f"Target icon: {C.MAGENTA}{target_icon}{C.R}", "captcha")
    fields = {"bot_honeypot_trap": "", "action_claim": "1", "captcha_type": "icon", "captcha_selected_icon": target_icon, "cf-turnstile-response": ""}
    try: r = post_multipart(session, f"{BASE}/faucet", fields)
    except Exception as e: log(f"Faucet POST err: {e}", "err"); return 60
    if is_cf_challenge(r): log("CF di POST faucet", "cf"); return 60
    if not r.ok: log(f"Faucet HTTP {r.status_code}", "warn"); return 60
    try: data = r.json()
    except:
        m = re.search(r"\+(\d+)\s*DAO\s*Coins\s*added", r.text, re.IGNORECASE)
        if m:
            coins = int(m.group(1)); STATE["faucet_claimed"] += 1; STATE["faucet_coins"] += coins; STATE["daily_used"] += 1
            log(f"Faucet ✓ +{coins} DAO", "ok"); cd = int(cfg.get("faucet_cooldown_default", 300))
            STATE["faucet_next_at"] = time.time() + cd; return cd
        return 60
    if data.get("status") == "success":
        msg = data.get("message", "Claimed!"); m = re.search(r"\+(\d+)", msg)
        coins = int(m.group(1)) if m else 20; cd = int(data.get("cooldown", 300))
        STATE["faucet_claimed"] += 1; STATE["faucet_coins"] += coins; STATE["faucet_next_at"] = time.time() + cd
        limit = data.get("daily_limit", 0)
        if limit: STATE["daily_used"] = limit - data.get("remaining", 0); STATE["daily_limit"] = limit
        log(f"Faucet ✓ +{coins} DAO | next {fmt_duration(cd)}", "ok"); return cd
    log(f"Faucet: {data.get('message', '?')}", "warn"); return 60

def do_jackpot(session, cfg):
    log("Jackpot roll...", "dice")
    try: r0 = session.get(f"{BASE}/jackpot", timeout=30, allow_redirects=True)
    except Exception as e: log(f"Jackpot GET err: {e}", "err"); return 60
    if is_cf_challenge(r0):
        session = handle_cf_challenge(session, cfg, f"{BASE}/jackpot", r0)
        if not session: return 60
        try: r0 = session.get(f"{BASE}/jackpot", timeout=30, allow_redirects=True)
        except: return 60
        if is_cf_challenge(r0): return 60
    html = r0.text
    cd = parse_jackpot_cooldown(html)
    if cd is not None and cd > 0:
        STATE["jackpot_next_at"] = time.time() + cd; log(f"Jackpot cooldown: {fmt_duration(cd)}", "wait"); return cd
    target_icon = parse_target_icon(html)
    if not target_icon: log("Icon jackpot tidak ditemukan", "err"); return 60
    log(f"Target icon: {C.MAGENTA}{target_icon}{C.R}", "captcha")
    fields = {"action_spin": "1", "captcha_type": "icon", "captcha_selected_icon": target_icon, "cf-turnstile-response": ""}
    try: r = post_multipart(session, f"{BASE}/jackpot", fields)
    except Exception as e: log(f"Jackpot POST err: {e}", "err"); return 60
    if is_cf_challenge(r): return 60
    if not r.ok: return 60
    try: data = r.json()
    except: return 60
    if data.get("status") == "success":
        num = data.get("num", "?"); coins = int(data.get("coins", 0)); cd = int(data.get("cooldown", 600))
        STATE["jackpot_claimed"] += 1; STATE["jackpot_coins"] += coins; STATE["jackpot_next_at"] = time.time() + cd
        log(f"Jackpot ✓ #{num} +{coins} DAO | next {fmt_duration(cd)}", "ok"); return cd
    cd = int(data.get("cooldown", 60))
    if cd > 0: STATE["jackpot_next_at"] = time.time() + cd
    log(f"Jackpot: {data.get('msg', '?')}", "warn"); return max(cd, 30)

# ==================== MAIN ====================
def compute_next_wake(cfg):
    now = time.time()
    if cfg.get("enable_faucet", True) and STATE["faucet_next_at"] <= now: return now + 1
    if cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] <= now: return now + 1
    candidates = []
    if cfg.get("enable_faucet", True) and STATE["faucet_next_at"] > now: candidates.append(STATE["faucet_next_at"])
    if cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] > now: candidates.append(STATE["jackpot_next_at"])
    return (min(candidates) + 1) if candidates else (now + LOOP_DELAY)

def run_bot(cfg):
    global current_cfg
    current_cfg = cfg
    banner(); log("Bot start", "ok"); log(f"Email: {cfg['u']}", "info")
    session = make_session(cfg.get("cookies_extra", ""), cfg)
    STATE["started_at"] = time.time()

    if cfg.get("enable_auto_login", True):
        ok = False
        for attempt in range(3):
            if do_login(session, cfg): ok = True; break
            log(f"Login err ({attempt+1}/3)", "err"); time.sleep(5)
        if not ok: log("Login gagal 3x, ke menu", "err"); time.sleep(2); return
    else:
        if not verify_session(session, cfg): log("Session invalid", "err"); time.sleep(2); return

    section("Initial Sync")
    check_balance(session, cfg)

    cycle = 0
    try:
        while True:
            cycle += 1
            now = time.time()
            fr = cfg.get("enable_faucet", True) and STATE["faucet_next_at"] <= now
            jr = cfg.get("enable_jackpot", True) and STATE["jackpot_next_at"] <= now
            if not fr and not jr:
                wake = compute_next_wake(cfg)
                delta = int(wake - now)
                status_bar(cfg)
                log(f"Tidur {fmt_duration(delta)}...", "wait")
                time.sleep(min(delta, 60))
                continue
            print(); section(f"Cycle #{cycle}"); status_bar(cfg)
            if fr:
                try: do_faucet(session, cfg)
                except Exception as e: log(f"Faucet err: {e}", "err"); STATE["faucet_next_at"] = time.time() + 60
            if jr:
                try: do_jackpot(session, cfg)
                except Exception as e: log(f"Jackpot err: {e}", "err"); STATE["jackpot_next_at"] = time.time() + 60
            check_balance(session, cfg)
            time.sleep(2)
    except KeyboardInterrupt:
        log("Stopped by user.", "warn")

def main():
    while True:
        cfg = menu_loop()
        if cfg is None:
            clear(); print(f"{C.YELLOW}Bye.{C.R}"); return
        try: run_bot(cfg)
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}Kembali ke menu...{C.R}"); time.sleep(1)

if __name__ == "__main__":
    main()
