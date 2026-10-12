#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════╗
║     💀 DOGEMINING AUTO CLAIM V4 - HACKED EDITION 💀          ║
║                                                               ║
║   🎯 1 AKUN  : Jalan langsung (tanpa proxy)                   ║
║   🌐 MULTI   : WAJIB pakai PROXY per akun                     ║
║                                                               ║
║   ✅ Fingerprint unik per akun                                ║
║   ✅ Hacker-style loading animation                           ║
║   ✅ Auto login + claim + captcha SVG solver                  ║
║   ✅ Concurrent worker dengan proxy terisolasi                ║
╚═══════════════════════════════════════════════════════════════╝
"""

import requests
import re
import json
import time
import hashlib
import sys
import os
import random
import threading
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://app.dogenetwork.online"
CONFIG_FILE = "config_doge.json"

# ===================== WARNA =====================
class Colors:
    merah    = "\033[91m"
    hijau    = "\033[92m"
    kuning   = "\033[93m"
    biru     = "\033[94m"
    ungu     = "\033[95m"
    cyan     = "\033[96m"
    putih    = "\033[97m"
    abu      = "\033[90m"
    bold     = "\033[1m"
    reset    = "\033[0m"
    matrix1  = "\033[38;5;46m"
    matrix2  = "\033[38;5;82m"
    matrix3  = "\033[38;5;118m"
    matrix4  = "\033[38;5;154m"
    red_glow = "\033[38;5;196m"
    cyan_glow= "\033[38;5;51m"
    purple   = "\033[38;5;129m"
    gold     = "\033[38;5;220m"
C = Colors()

PRINT_LOCK = threading.Lock()

# ===================== UTILS =====================
def clear():
    os.system('cls' if os.name == 'nt' else 'cls')

def safe_print(*args, **kwargs):
    with PRINT_LOCK:
        print(*args, **kwargs, flush=True)

def loading_animation(label="INITIALIZING", duration=2.0):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    start = time.time()
    i = 0
    while time.time() - start < duration:
        progress = (time.time() - start) / duration
        bar_len = 30
        filled = int(bar_len * progress)
        bar = "█" * filled + "░" * (bar_len - filled)
        frame = frames[i % len(frames)]
        hex_noise = "".join(random.choices("0123456789ABCDEF", k=8))
        line = (f"\r{C.matrix1}┃{C.reset} {C.red_glow}{frame}{C.reset} "
                f"{C.matrix2}{label:<20}{C.reset} {C.cyan_glow}[{bar}]{C.reset} "
                f"{C.matrix3}{int(progress*100):>3}%{C.reset} {C.abu}0x{hex_noise}{C.reset}")
        sys.stdout.write(line)
        sys.stdout.flush()
        time.sleep(0.06)
        i += 1
    sys.stdout.write("\r" + " " * 100 + "\r")
    sys.stdout.flush()

def glitch_text(text, duration=1.2):
    glitch_chars = "!@#$%^&*()_+{}|:<>?~`"
    start = time.time()
    while time.time() - start < duration:
        result = "".join(random.choice(glitch_chars) if random.random() < 0.3 else ch for ch in text)
        sys.stdout.write(f"\r{C.matrix1}{result}{C.reset}")
        sys.stdout.flush()
        time.sleep(0.05)
    sys.stdout.write(f"\r{C.matrix1}{text}{C.reset}\n")

def terminal_boot_sequence():
    clear()
    logo = f"""{C.matrix1}
    ██████╗  ██████╗  ██████╗ ███████╗███╗   ███╗██╗███╗   ██╗
    ██╔══██╗██╔════╝ ██╔════╝ ██╔════╝████╗ ████║██║████╗  ██║
    ██║  ██║██║  ███╗██║  ███╗█████╗  ██╔████╔██║██║██╔██╗ ██║
    ██║  ██║██║   ██║██║   ██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║
    ██████╔╝╚██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║██║ ╚████║
    ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝
    {C.reset}"""
    print(logo)
    print(f"{C.red_glow}{'═'*62}{C.reset}\n")

    boot_lines = [
        (f"{C.matrix2}[✓]{C.reset} Establishing secure connection...", 0.15),
        (f"{C.matrix2}[✓]{C.reset} Loading kernel modules...", 0.1),
        (f"{C.matrix2}[✓]{C.reset} Bypassing detection layer...", 0.25),
        (f"{C.matrix2}[✓]{C.reset} Injecting fingerprint bypass...", 0.2),
        (f"{C.matrix2}[✓]{C.reset} Proxy manager initialized...", 0.15),
        (f"{C.matrix2}[✓]{C.reset} Captcha solver ready...", 0.2),
        (f"{C.gold}[⚡]{C.reset} CryptLink: ONLINE", 0.15),
        (f"{C.hijau}[★]{C.reset} System ready. Welcome, Operative.", 0.2),
    ]
    for line, delay in boot_lines:
        print(f"  {line}")
        time.sleep(delay)
    print(f"\n{C.red_glow}{'═'*62}{C.reset}")
    time.sleep(0.4)

def hacker_scan_animation(label="Scanning target"):
    bar_len = 40
    for i in range(bar_len + 1):
        bar = f"{C.matrix1}{'█' * i}{C.abu}{'░' * (bar_len - i)}{C.reset}"
        noise = "".join(random.choices("01", k=16))
        sys.stdout.write(f"\r{C.red_glow}┃{C.reset} {C.gold}{label}{C.reset} {bar} {C.matrix2}[{noise}]{C.reset}")
        sys.stdout.flush()
        time.sleep(0.04)
    sys.stdout.write("\n")

# ===================== BANNERS =====================
def banner_boncel():
    print(f"""{C.cyan}╔════════════════════════════════════════════════════════════╗{C.reset}
{C.cyan}║                 {C.bold}{C.kuning}I @Ahd1905 LOVE @Wulandari9832{C.reset}{C.cyan}             ║{C.reset}
{C.cyan}║        {C.putih}Copyright by @Ahd1905 ❤️ @Wulandari9832{C.reset}{C.cyan}          ║{C.reset}
{C.cyan}║        {C.putih}supported by @MoneyMaker_w{C.reset}{C.cyan}                         ║{C.reset}
{C.cyan}╚════════════════════════════════════════════════════════════╝{C.reset}
""")

def banner_menu(accounts):
    clear()
    print(f"""{C.matrix1}╔════════════════════════════════════════════════════════════╗{C.reset}
{C.matrix1}║{C.reset}  {C.red_glow}██████╗  ██████╗  ██████╗ ███████╗███╗   ███╗██╗███╗   ██╗{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}  {C.red_glow}██╔══██╗██╔════╝ ██╔════╝ ██╔════╝████╗ ████║██║████╗  ██║{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}  {C.gold}██║  ██║██║  ███╗██║  ███╗█████╗  ██╔████╔██║██║██╔██╗ ██║{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}  {C.gold}██║  ██║██║   ██║██║   ██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}  {C.matrix3}██████╔╝╚██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║██║ ╚████║{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}  {C.matrix3}╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝{C.reset}  {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}            {C.bold}{C.red_glow}💀 H A C K E D   E D I T I O N 💀{C.reset}              {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}            {C.matrix2}V4 · PROXY-ENFORCED MULTI MODE{C.reset}                 {C.matrix1}║{C.reset}
{C.matrix1}╠════════════════════════════════════════════════════════════╣{C.reset}
{C.matrix1}║{C.reset}   {C.hijau}[ 1 ] 🚀  AUTO CLAIM (1 AKUN){C.reset}                        {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.kuning}[ 2 ] ➕  TAMBAH AKUN{C.reset}                               {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.merah}[ 3 ] 🗑   HAPUS AKUN{C.reset}                                 {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.purple}[ 4 ] 🌐  LIST AKUN + PROXY{C.reset}                         {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.matrix3}[ 5 ] ⚡  RUN MULTI (BUTUH PROXY){C.reset}                   {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.biru}[ 6 ] 🧪  TEST PROXY{C.reset}                                 {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.merah}[ 0 ] ❌  EXIT{C.reset}                                         {C.matrix1}║{C.reset}
{C.matrix1}╠════════════════════════════════════════════════════════════╣{C.reset}
{C.matrix1}║{C.reset}   {C.gold}🎯 1 akun     : LANGSUNG (no proxy){C.reset}                {C.matrix1}║{C.reset}
{C.matrix1}║{C.reset}   {C.gold}🌐 Multi akun : WAJIB PROXY per akun{C.reset}               {C.matrix1}║{C.reset}
{C.matrix1}╚════════════════════════════════════════════════════════════╝{C.reset}
""")

    # Tampilkan akun
    if accounts:
        print(f"{C.matrix1}┏━[ {C.gold}AKUN TERSIMPAN{C.matrix1} ]{'━'*42}{C.reset}")
        for i, acc in enumerate(accounts, 1):
            email = acc.get("email", "?")
            proxy = acc.get("proxy", "") or ""
            proxy_display = proxy[:38] if proxy else f"{C.merah}(no proxy){C.reset}"
            proxy_color = C.matrix2 if proxy else C.merah
            print(f"{C.matrix1}┃{C.reset} {C.gold}[{i}]{C.reset} {C.putih}{email:<30}{C.reset} {C.abu}→{C.reset} {proxy_color}{proxy_display}{C.reset}")
        print(f"{C.matrix1}┗{'━'*55}{C.reset}\n")
    else:
        print(f"{C.merah}[!] Belum ada akun. Pilih [2] untuk tambah.{C.reset}\n")

def banner_claim(email, balance, delay_minutes=10, proxy=""):
    proxy_display = proxy[:30] if proxy else "DIRECT"
    safe_print(f"""
{C.matrix1}┌───────────────────────────────────────────────────────────┐{C.reset}
{C.matrix1}│{C.reset}  {C.gold}🚀 AUTO CLAIM DOGE{C.reset}                                       {C.matrix1}│{C.reset}
{C.matrix1}├───────────────────────────────────────────────────────────┤{C.reset}
{C.matrix1}│{C.reset}  {C.putih}Account :{C.reset} {C.gold}{email[:48]:<48}{C.reset}  {C.matrix1}│{C.reset}
{C.matrix1}│{C.reset}  {C.putih}Proxy   :{C.reset} {C.cyan_glow}{proxy_display:<48}{C.reset}  {C.matrix1}│{C.reset}
{C.matrix1}│{C.reset}  {C.putih}Balance :{C.reset} {C.matrix2}{balance:.8f} DOGE{C.reset}                              {C.matrix1}│{C.reset}
{C.matrix1}│{C.reset}  {C.putih}Delay   :{C.reset} {C.gold}{delay_minutes} minutes{C.reset}                                 {C.matrix1}│{C.reset}
{C.matrix1}└───────────────────────────────────────────────────────────┘{C.reset}
""")

# ===================== FINGERPRINT =====================
def get_fingerprint_for(email):
    import platform
    device_basis = f"{platform.node()}-{platform.processor()}"
    salt = f"{email}-{platform.system()}"
    raw = f"{device_basis}|{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()

# ===================== SESSION =====================
def create_session(proxy=""):
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    })
    if proxy:
        s.proxies.update({
            "http": proxy,
            "https": proxy,
        })
    return s

# ===================== LOGIN / CLAIM =====================
def get_csrf_from_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    meta = soup.find('meta', {'name': 'csrf-token'})
    if meta:
        return meta.get('content')
    inp = soup.find('input', {'name': '_token'})
    if inp:
        return inp.get('value')
    match = re.search(r'X-CSRF-TOKEN["\']?\s*:\s*["\']([^"\']+)', html)
    if match:
        return match.group(1)
    return None

def login(session, email, fingerprint):
    try:
        resp = session.get(f"{BASE_URL}/register?ref=2953", timeout=25)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        csrf = get_csrf_from_page(resp.text)
        if not csrf:
            return False, "CSRF not found"

        headers = {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': csrf,
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/register?ref=2953",
        }
        payload = {"email": email, "fingerprint": fingerprint}
        resp = session.post(f"{BASE_URL}/register", json=payload, headers=headers, timeout=25)

        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        try:
            data = resp.json()
            if data.get('success') and data.get('redirect'):
                session.get(f"{BASE_URL}{data['redirect']}", timeout=25)
                return True, "OK"
            return False, data.get('message', 'unknown')
        except json.JSONDecodeError:
            return False, "Non-JSON response"
    except Exception as e:
        return False, str(e)[:60]

def get_balance(session):
    try:
        resp = session.get(f"{BASE_URL}/dashboard", timeout=20)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag, attrs in [
            ('span', {'id': 'account-balance-val'}),
            ('span', {'class': 'header-balance-amount'}),
            ('span', {'id': 'user-account-balance-display'}),
        ]:
            el = soup.find(tag, attrs)
            if el:
                text = re.sub(r'[^\d.]+', '', el.get_text(strip=True))
                if text:
                    return float(text)
        match = re.search(r'([\d.]+)\s*DOGE', resp.text)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0

def get_csrf_cookie(session):
    for cookie in session.cookies:
        if cookie.name == 'XSRF-TOKEN':
            return cookie.value
    return None

def fetch_captcha(session):
    csrf = get_csrf_cookie(session)
    if not csrf:
        return None
    headers = {
        "Accept": "application/json",
        "X-CSRF-TOKEN": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/dashboard",
        "Origin": BASE_URL,
    }
    try:
        resp = session.get(f"{BASE_URL}/captcha", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and 'svg' in data:
                return data['svg']
    except:
        pass
    return None

def parse_svg_captcha(svg):
    soup = BeautifulSoup(svg, 'html.parser')
    digits = []
    for text in soup.find_all('text'):
        content = text.get_text(strip=True)
        if content.isdigit():
            digits.append(content)
    return ''.join(digits)

def do_claim(session, captcha_code):
    csrf = get_csrf_cookie(session)
    if not csrf:
        return None
    payload = {"captcha": captcha_code}
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/dashboard",
    }
    try:
        resp = session.post(f"{BASE_URL}/claim", json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def check_session(session):
    try:
        resp = session.get(f"{BASE_URL}/dashboard", timeout=20)
        return resp.status_code == 200 and "login" not in resp.url.lower()
    except:
        return False

# ===================== CONFIG =====================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_accounts():
    """
    Struktur baru:
      {"accounts": [
          {"email": "...", "proxy": ""},          # direct
          {"email": "...", "proxy": "http://..."} # via proxy
      ]}
    Backward compat: kalau format lama (list of string), convert.
    """
    config = load_config()
    raw = config.get("accounts", [])

    accounts = []
    for item in raw:
        if isinstance(item, str):
            # format lama
            accounts.append({"email": item.strip(), "proxy": ""})
        elif isinstance(item, dict):
            email = str(item.get("email", "")).strip()
            proxy = str(item.get("proxy", "")).strip()
            if email:
                accounts.append({"email": email, "proxy": proxy})

    return accounts, config

def save_accounts(accounts, config):
    # Dedup by email (last wins)
    seen = {}
    for acc in accounts:
        seen[acc["email"]] = acc
    config["accounts"] = list(seen.values())
    save_config(config)

# ===================== WORKER =====================
def run_account(account, delay_seconds=600, worker_id=0, require_proxy=False):
    """Jalankan 1 akun."""
    email = account.get("email", "")
    proxy = account.get("proxy", "") or ""

    if require_proxy and not proxy:
        safe_print(f"{C.merah}[✗] {email}: PROXY tidak ada! Multi-akun wajib pakai proxy.{C.reset}")
        return

    try:
        fingerprint = get_fingerprint_for(email)

        proxy_tag = f"{C.cyan_glow}{proxy[:30]}{C.reset}" if proxy else f"{C.matrix2}DIRECT{RESET if False else C.reset}"

        safe_print(f"\n{C.matrix1}┏━━━[{C.gold} WORKER #{worker_id+1} {C.matrix1}]━━━ {C.gold}{email}{C.reset}")
        safe_print(f"{C.matrix1}┃{C.reset} {C.abu}Fingerprint : {fingerprint[:40]}...{C.reset}")
        safe_print(f"{C.matrix1}┃{C.reset} {C.abu}Proxy       : {proxy_tag}{C.reset}")

        session = create_session(proxy)

        ok, msg = login(session, email, fingerprint)
        if not ok:
            safe_print(f"{C.merah}┃{C.reset} {C.merah}[✗] Login gagal: {msg}{C.reset}")
            safe_print(f"{C.merah}┗{'━'*55}{C.reset}\n")
            return

        if not check_session(session):
            safe_print(f"{C.merah}┃{C.reset} {C.merah}[✗] Session invalid{C.reset}")
            safe_print(f"{C.merah}┗{'━'*55}{C.reset}\n")
            return

        balance = get_balance(session) or 0.0
        safe_print(f"{C.matrix2}┃{C.reset} {C.hijau}[✓] Login OK | Balance: {balance:.8f} DOGE{C.reset}")
        safe_print(f"{C.matrix1}┗{'━'*55}{C.reset}")

        claim_count = 0
        while True:
            safe_print(f"\n{C.matrix1}┏━[{datetime.now().strftime('%H:%M:%S')}] {C.gold}{email}{C.reset}")
            safe_print(f"{C.matrix1}┃{C.reset} {C.cyan_glow}🎯 Claim #{claim_count + 1}{C.reset} | {C.matrix2}Balance: {balance:.8f} DOGE{C.reset}")

            svg = fetch_captcha(session)
            if not svg:
                safe_print(f"{C.merah}┃{C.reset} {C.merah}[!] Captcha gagal, re-login...{C.reset}")
                ok, msg = login(session, email, fingerprint)
                if ok:
                    svg = fetch_captcha(session)
                if not svg:
                    safe_print(f"{C.kuning}┃{C.reset} {C.kuning}[⏳] Tunggu 30s...{C.reset}")
                    time.sleep(30)
                    continue

            captcha = parse_svg_captcha(svg)
            if not captcha or len(captcha) != 4:
                safe_print(f"{C.merah}┃{C.reset} {C.merah}[!] Captcha invalid: {captcha}{C.reset}")
                time.sleep(10)
                continue

            safe_print(f"{C.matrix2}┃{C.reset} {C.matrix2}[✓] Captcha solved: {C.bold}{captcha}{C.reset}")

            result = do_claim(session, captcha)
            if result and result.get("success"):
                claimed = float(result.get("amount", 0))
                balance = float(result.get("balance", 0))
                claim_count += 1
                safe_print(f"{C.matrix2}┃{C.reset} {C.hijau}[✓] +{claimed:.8f} DOGE | Balance: {balance:.8f} DOGE{C.reset}")
            else:
                msg = result.get("message", "unknown") if result else "no response"
                safe_print(f"{C.merah}┃{C.reset} {C.merah}[✗] Claim gagal: {msg}{C.reset}")

            # Countdown
            for remaining in range(delay_seconds, 0, -1):
                if remaining % 30 == 0 or remaining <= 5:
                    mins = remaining // 60
                    secs = remaining % 60
                    safe_print(f"{C.matrix1}┃{C.reset} {C.kuning}[⏳] {email[:20]}: next in {mins:02d}:{secs:02d}{C.reset}")
                time.sleep(1)

    except Exception as e:
        safe_print(f"{C.merah}[!] {email} worker error: {e}{C.reset}")

# ===================== TEST PROXY =====================
def test_proxy(proxy):
    """Test apakah proxy bisa dipakai."""
    try:
        session = create_session(proxy)
        r = session.get("https://api.ipify.org?format=json", timeout=15)
        if r.status_code == 200:
            return True, r.json().get("ip", "?")
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:80]

# ===================== RUN MULTI =====================
def start_all_accounts(accounts, delay_seconds=600):
    # Validasi: multi = wajib proxy
    no_proxy = [a for a in accounts if not a.get("proxy")]
    if no_proxy:
        safe_print(f"\n{C.merah}╔═══════════════════════════════════════════════════════════╗{C.reset}")
        safe_print(f"{C.merah}║  ⛔ MULTI-ACCOUNT DITOLAK — PROXY WAJIB PER AKUN          ║{C.reset}")
        safe_print(f"{C.merah}╚═══════════════════════════════════════════════════════════╝{C.reset}\n")
        safe_print(f"{C.kuning}Akun tanpa proxy:{C.reset}")
        for acc in no_proxy:
            safe_print(f"  {C.merah}• {acc['email']}{C.reset}")
        safe_print(f"\n{C.kuning}Edit akun di menu [4] untuk tambah proxy.{C.reset}")
        return

    safe_print(f"\n{C.gold}╔═══════════════════════════════════════════════════════════╗{C.reset}")
    safe_print(f"{C.gold}║     ⚡ MULTI-ACCOUNT CONCURRENT MODE (PROXY) ⚡{C.reset}")
    safe_print(f"{C.gold}╚═══════════════════════════════════════════════════════════╝{C.reset}\n")
    safe_print(f"{C.matrix2}[*] Total akun   : {len(accounts)}{C.reset}")
    safe_print(f"{C.matrix2}[*] Unique proxy : {len(set(a['proxy'] for a in accounts))}{C.reset}")
    safe_print(f"{C.matrix2}[*] Isolated session per akun : ✓{C.reset}\n")

    hacker_scan_animation("Validating proxy pool")
    time.sleep(0.3)
    hacker_scan_animation("Spawning isolated workers")

    safe_print(f"\n{C.matrix1}{'═'*60}{C.reset}\n")

    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        futures = [
            pool.submit(run_account, acc, delay_seconds, i, True)
            for i, acc in enumerate(accounts)
        ]
        try:
            for f in futures:
                f.result()
        except KeyboardInterrupt:
            safe_print(f"\n{C.kuning}[!] Menghentikan semua worker...{C.reset}")
            raise

# ===================== MAIN =====================
def main():
    terminal_boot_sequence()
    loading_animation("Establishing secure link", 1.5)
    loading_animation("Loading modules", 1.0)

    accounts, config = load_accounts()

    while True:
        banner_menu(accounts)

        choice = input(f"{C.matrix1}┃ {C.gold}root@dogemining{C.reset}{C.matrix1}:~# {C.reset}").strip()

        # ---------- [1] AUTO CLAIM 1 AKUN ----------
        if choice == "1":
            if not accounts:
                input(f"{C.merah}Belum ada akun. Enter...{C.reset}")
                continue
            try:
                n = int(input(f"{C.matrix1}┃ {C.gold}Pilih nomor akun:{C.reset} "))
                if 1 <= n <= len(accounts):
                    loading_animation(f"Loading {accounts[n-1]['email']}", 1.0)
                    run_account(accounts[n-1], 600, 0, require_proxy=False)
                else:
                    print(f"{C.merah}Nomor tidak valid.{C.reset}")
            except ValueError:
                print(f"{C.merah}Masukkan nomor.{C.reset}")
            except KeyboardInterrupt:
                pass

        # ---------- [2] TAMBAH AKUN ----------
        elif choice == "2":
            print(f"\n{C.matrix1}┏━[ TAMBAH AKUN ]{'━'*40}{C.reset}")
            email = input(f"{C.matrix1}┃{C.reset} {C.gold}Email          :{C.reset} ").strip()
            if not email:
                print(f"{C.merah}Email kosong.{C.reset}")
                input(f"{C.matrix1}Enter...{C.reset}")
                continue

            total_after = len([a for a in accounts if a["email"] != email]) + 1
            if total_after > 1:
                print(f"{C.kuning}┃{C.reset} {C.kuning}Multi-akun terdeteksi. PROXY WAJIB diisi.{C.reset}")
                proxy = input(f"{C.matrix1}┃{C.reset} {C.gold}Proxy (URL)    :{C.reset} ").strip()
                if not proxy:
                    print(f"{C.merah}┃{C.reset} {C.merah}✗ Dibatalkan: multi-akun butuh proxy.{C.reset}")
                    input(f"{C.matrix1}Enter...{C.reset}")
                    continue
                # Validasi format
                if not (proxy.startswith("http://") or proxy.startswith("https://") or proxy.startswith("socks")):
                    print(f"{C.merah}┃{C.reset} {C.merah}Format proxy salah. Contoh:{C.reset}")
                    print(f"{C.abu}     http://user:pass@ip:port{C.reset}")
                    print(f"{C.abu}     socks5://ip:port{C.reset}")
                    input(f"{C.matrix1}Enter...{C.reset}")
                    continue
            else:
                print(f"{C.matrix2}┃{C.reset} {C.matrix2}1 akun → tidak butuh proxy (boleh dikosongkan){C.reset}")
                proxy = input(f"{C.matrix1}┃{C.reset} {C.gold}Proxy (opt)    :{C.reset} ").strip()

            # Hapus entry lama (kalau ada) lalu tambah baru
            accounts = [a for a in accounts if a["email"] != email]
            accounts.append({"email": email, "proxy": proxy})
            save_accounts(accounts, config)

            print(f"{C.matrix2}┃{C.reset} {C.hijau}[✓] Akun ditambahkan{C.reset}")
            print(f"{C.matrix2}┃{C.reset} {C.abu}Fingerprint : {get_fingerprint_for(email)[:40]}...{C.reset}")
            print(f"{C.matrix2}┃{C.reset} {C.abu}Proxy       : {proxy if proxy else 'DIRECT'}{C.reset}")
            print(f"{C.matrix1}┗{'━'*55}{C.reset}")
            input(f"{C.matrix1}Enter...{C.reset}")

        # ---------- [3] HAPUS AKUN ----------
        elif choice == "3":
            if not accounts:
                input(f"{C.merah}Tidak ada akun. Enter...{C.reset}")
                continue
            try:
                n = int(input(f"{C.matrix1}┃ {C.gold}Nomor akun yang dihapus:{C.reset} "))
                if 1 <= n <= len(accounts):
                    removed = accounts.pop(n - 1)
                    save_accounts(accounts, config)
                    print(f"{C.matrix2}[✓] Dihapus: {removed['email']}{C.reset}")
                else:
                    print(f"{C.merah}Nomor tidak valid.{C.reset}")
            except ValueError:
                print(f"{C.merah}Masukkan nomor.{C.reset}")
            input(f"{C.matrix1}Enter...{C.reset}")

        # ---------- [4] LIST AKUN + PROXY ----------
        elif choice == "4":
            clear()
            banner_boncel()
            print(f"{C.matrix1}┏━[ {C.gold}LIST AKUN & PROXY{C.matrix1} ]{'━'*37}{C.reset}")
            if not accounts:
                print(f"{C.matrix1}┃{C.reset} {C.merah}(kosong){C.reset}")
            for i, acc in enumerate(accounts, 1):
                fp = get_fingerprint_for(acc["email"])
                proxy = acc.get("proxy", "")
                proxy_str = proxy if proxy else f"{C.merah}DIRECT (single only){C.reset}"
                print(f"{C.matrix1}┃{C.reset}")
                print(f"{C.matrix1}┃{C.reset} {C.gold}[{i}]{C.reset} {C.putih}{acc['email']}{C.reset}")
                print(f"{C.matrix1}┃{C.reset}    {C.abu}Proxy       : {proxy_str}{C.reset}")
                print(f"{C.matrix1}┃{C.reset}    {C.abu}Fingerprint : {fp[:40]}...{C.reset}")
            print(f"{C.matrix1}┗{'━'*55}{C.reset}")
            input(f"\n{C.matrix1}Enter...{C.reset}")

        # ---------- [5] RUN MULTI (BUTUH PROXY) ----------
        elif choice == "5":
            if not accounts:
                input(f"{C.merah}Belum ada akun. Enter...{C.reset}")
                continue
            if len(accounts) < 2:
                print(f"{C.kuning}[!] Cuma 1 akun. Multi mode butuh ≥2 akun dengan proxy.{C.reset}")
                print(f"{C.kuning}    Pakai menu [1] untuk single.{C.reset}")
                input(f"{C.matrix1}Enter...{C.reset}")
                continue
            try:
                start_all_accounts(accounts, 600)
            except KeyboardInterrupt:
                pass
            input(f"\n{C.matrix1}Enter...{C.reset}")

        # ---------- [6] TEST PROXY ----------
        elif choice == "6":
            clear()
            banner_boncel()
            print(f"{C.matrix1}┏━[ {C.gold}TEST PROXY{C.matrix1} ]{'━'*43}{C.reset}")
            if not accounts:
                print(f"{C.matrix1}┃{C.reset} {C.merah}(belum ada akun){C.reset}")
                input(f"{C.matrix1}Enter...{C.reset}")
                continue

            to_test = [a for a in accounts if a.get("proxy")]
            if not to_test:
                print(f"{C.matrix1}┃{C.reset} {C.merah}Tidak ada akun dengan proxy.{C.reset}")
                input(f"{C.matrix1}Enter...{C.reset}")
                continue

            for i, acc in enumerate(to_test, 1):
                proxy = acc["proxy"]
                print(f"{C.matrix1}┃{C.reset} {C.gold}[{i}]{C.reset} {C.putih}{acc['email']}{C.reset}")
                print(f"{C.matrix1}┃{C.reset}    {C.abu}Proxy: {proxy}{C.reset}")
                sys.stdout.write(f"{C.matrix1}┃{C.reset}    Testing...")
                sys.stdout.flush()
                ok, info = test_proxy(proxy)
                if ok:
                    print(f"\r{C.matrix1}┃{C.reset}    {C.matrix2}[✓] OK — IP publik: {info}{C.reset}")
                else:
                    print(f"\r{C.matrix1}┃{C.reset}    {C.merah}[✗] GAGAL: {info}{C.reset}")
            print(f"{C.matrix1}┗{'━'*55}{C.reset}")
            input(f"\n{C.matrix1}Enter...{C.reset}")

        # ---------- [0] EXIT ----------
        elif choice == "0":
            clear()
            glitch_text("SHUTTING DOWN...", 0.8)
            print(f"{C.matrix1}Disconnected. Goodbye, operative.{C.reset}")
            break

        else:
            print(f"{C.merah}Pilihan tidak valid.{C.reset}")
            time.sleep(0.8)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.merah}Terminated.{C.reset}")
