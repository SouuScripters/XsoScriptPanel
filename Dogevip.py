#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOGEMINER.VIP AUTO WATCH BOT v1.3
- Per-category submit endpoint (watch_ad, watch_ad_bonus, dll)
- Anti-spam animation (\033[K clear-line)
- Branding: MoneyMaker_w
"""

import os
import sys
import time
import json
import random
import urllib.parse
import requests
from datetime import datetime
from collections import deque

CLEAR_LINE = '\033[K'

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[35m'
    ORANGE = '\033[38;5;208m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'
    NEON_G = '\033[38;5;46m'
    NEON_C = '\033[38;5;51m'
    NEON_Y = '\033[38;5;226m'
    NEON_P = '\033[38;5;201m'
    NEON_R = '\033[38;5;196m'

BANNER = f"""{Colors.NEON_Y}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  ██████╗  ██████╗  ██████╗ ███████╗███╗   ███╗██╗███╗   ██╗    ║
║  ██╔══██╗██╔═══██╗██╔════╝ ██╔════╝████╗ ████║██║████╗  ██║    ║
║  ██║  ██║██║   ██║██║  ███╗█████╗  ██╔████╔██║██║██╔██╗ ██║    ║
║  ██║  ██║██║   ██║██║   ██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║    ║
║  ██████╔╝╚██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║██║ ╚████║    ║
║  ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝    ║
║                                                                  ║
║  {Colors.NEON_Y}🐕 DOGEMINER AUTO WATCH  {Colors.NEON_C}│ {Colors.NEON_G}v1.3 {Colors.NEON_C}│ {Colors.NEON_P}4 Categories + Mining{Colors.END}  {Colors.NEON_Y}║
║                                                                  ║
║  {Colors.NEON_G}▸ By Dev  : {Colors.NEON_C}MoneyMaker_w{Colors.END}                                 {Colors.NEON_Y}║
║  {Colors.NEON_G}▸ Channel : {Colors.NEON_C}t.me/ScriptyXSouu{Colors.END}                            {Colors.NEON_Y}║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.END}
"""

INIT_FILE = "init_dogeminer.txt"
AP_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjbHdwYnZvaXV0YWZ6Z2JhdXRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk1MzU0MTksImV4cCI6MjA5NTExMTQxOX0.v9Y8ts0z1I4iGoLJLVPqmlUYR15tjzZ_RYnCRIBBXwI"
BASE_URL = "https://jclwpbvoiutafzgbauth.supabase.co/functions/v1/api"
ORIGIN = "https://dogeminer.vip"

CFG_ADSGRAM = 10
CFG_POPUP   = 10
CFG_BONUS   = 10
CFG_PREMIUM = 10
CFG_DUR_ADSGRAM = 5
CFG_DUR_POPUP   = 30
CFG_DUR_BONUS   = 30
CFG_DUR_PREMIUM = 30
CFG_COOLDOWN    = 15

# ============================================================
# MAPPING ENDPOINT PER KATEGORI
# ============================================================
KIND_STATUS_ACTION = {
    'adsgram': 'ad_watch_status',
    'popup':   'ad_watch_interstitial_status',
    'bonus':   'ad_watch_bonus_status',
    'premium': 'ad_watch_premium_status',
}

KIND_SUBMIT_ACTION = {
    'adsgram': 'watch_ad',
    'popup':   'watch_ad_interstitial',
    'bonus':   'watch_ad_bonus',       # ✅ confirmed
    'premium': 'watch_ad_premium',
}

# ============================================================
# ANIMATIONS
# ============================================================
class Anim:
    @staticmethod
    def spinner(text, duration=2):
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        end = time.time() + duration
        i = 0
        while time.time() < end:
            row = f" {Colors.NEON_C}{frames[i % 10]}{Colors.END} {Colors.WHITE}{text}{Colors.END}"
            sys.stdout.write('\r' + CLEAR_LINE + row)
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.write(f" {Colors.NEON_G}✓{Colors.END} {Colors.WHITE}{text}{Colors.END}\n")
        sys.stdout.flush()

    @staticmethod
    def dots(text, duration=2):
        end = time.time() + duration
        n = 0
        while time.time() < end:
            d = "." * ((n % 3) + 1)
            row = f" {Colors.NEON_C}•{Colors.END} {Colors.WHITE}{text}{Colors.NEON_C}{d:<4}{Colors.END}"
            sys.stdout.write('\r' + CLEAR_LINE + row)
            sys.stdout.flush()
            time.sleep(0.3)
            n += 1
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.write(f" {Colors.NEON_G}✓{Colors.END} {Colors.WHITE}{text}{Colors.END}\n")
        sys.stdout.flush()

    @staticmethod
    def progress(text, duration=2, width=28):
        end = time.time() + duration
        total = duration
        while time.time() < end:
            elapsed = duration - (end - time.time())
            pct = min(1.0, elapsed / total)
            filled = int(pct * width)
            empty = width - filled
            bar = f"{Colors.NEON_G}{'█' * filled}{Colors.DIM}{'░' * empty}{Colors.END}"
            row = (f" {Colors.NEON_C}▶{Colors.END} "
                   f"{Colors.WHITE}{text:<28}{Colors.END} "
                   f"[{bar}] "
                   f"{Colors.NEON_Y}{int(pct * 100):>3}%{Colors.END}")
            sys.stdout.write('\r' + CLEAR_LINE + row)
            sys.stdout.flush()
            time.sleep(0.05)
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.write(f" {Colors.NEON_G}✓{Colors.END} {Colors.WHITE}{text}{Colors.END}\n")
        sys.stdout.flush()

    @staticmethod
    def ad_watch(kind, provider, duration):
        spinner = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
        bar_len = 18
        start = time.time()
        i = 0
        while True:
            elapsed = time.time() - start
            if elapsed >= duration:
                break
            pct = elapsed / duration
            filled = int(bar_len * pct)
            bar = '█' * filled + '░' * (bar_len - filled)
            remaining = duration - elapsed
            row = (f"  {Colors.NEON_P}{spinner[i % 10]}{Colors.END} "
                   f"{Colors.NEON_C}{kind:<10}{Colors.END} "
                   f"{Colors.NEON_G}[{bar}]{Colors.END} "
                   f"{Colors.NEON_Y}{int(pct*100):3d}%{Colors.END} "
                   f"{Colors.ORANGE}{remaining:4.1f}s{Colors.END}")
            sys.stdout.write('\r' + CLEAR_LINE + row)
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.flush()

    @staticmethod
    def glitch(text, duration=0.5):
        gc = "░▒▓█▄▀■□▪▫@#$%&*"
        end = time.time() + duration
        while time.time() < end:
            out = ''.join(random.choice(gc) if (random.randint(0,10)<2 and ch!=' ') else ch for ch in text)
            sys.stdout.write('\r' + CLEAR_LINE + f"  {Colors.NEON_P}{out}{Colors.END}")
            sys.stdout.flush()
            time.sleep(0.06)
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.write(f"  {Colors.NEON_C}{text}{Colors.END}\n")
        sys.stdout.flush()

    @staticmethod
    def typewriter(text, delay=0.015, color=None):
        c = color or Colors.WHITE
        for ch in text:
            sys.stdout.write(f"{c}{ch}{Colors.END}")
            sys.stdout.flush()
            time.sleep(delay)
        print()

# ============================================================
# UTILS
# ============================================================
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def strip_ansi(s):
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)

def print_box(title, lines, color=Colors.CYAN, w=66):
    print(f"{color}╭{'─' * w}╮{Colors.END}")
    print(f"{color}│{Colors.END} {Colors.BOLD}{color}{title:^{w}}{Colors.END} {color}│{Colors.END}")
    print(f"{color}├{'─' * w}┤{Colors.END}")
    for line in lines:
        clean = strip_ansi(line)
        pad = w - len(clean)
        if pad < 0: pad = 0
        print(f"{color}│{Colors.END} {line}{' ' * pad} {color}│{Colors.END}")
    print(f"{color}╰{'─' * w}╯{Colors.END}")

def rand_hex(n=32):
    return os.urandom(n).hex()

# ============================================================
# BOT
# ============================================================
class DogeMinerBot:
    def __init__(self):
        self.init_data = ""
        self.telegram_id = None
        self.username = None
        self.first_name = None
        self.balance = 0.0
        self.total_earned = 0.0
        self.xp = 0
        self.level = 1
        self.country = "Indonesia"
        self.is_banned = False
        self.mining_started_at = None
        self.mining_ends_at = None
        self.boost_active_until = None

        self.sess_adsgram = 0
        self.sess_popup = 0
        self.sess_bonus = 0
        self.sess_premium = 0

        self.logs = deque(maxlen=8)
        self.ads_done_total = 0

        self.session = requests.Session()
        self.session.headers.update(self.build_headers())
        self.load_init_data()
        self.menu()

    def build_headers(self):
        return {
            "apikey": AP_ANON_KEY,
            "authorization": f"Bearer {AP_ANON_KEY}",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.7977.87 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
            "origin": ORIGIN,
            "referer": f"{ORIGIN}/",
            "x-requested-with": "org.telegram.messenger.web",
            "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Android WebView";v="152"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept": "*/*",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def load_init_data(self):
        if os.path.exists(INIT_FILE):
            with open(INIT_FILE, 'r') as f:
                self.init_data = f.read().strip()
            self._parse_user_info()
        else:
            self.init_data = ""

    def save_init_data(self, data):
        with open(INIT_FILE, 'w') as f:
            f.write(data.strip())
        self.init_data = data.strip()
        self._parse_user_info()

    def _parse_user_info(self):
        try:
            parsed = urllib.parse.parse_qs(self.init_data)
            if 'user' in parsed:
                user = json.loads(parsed['user'][0])
                self.telegram_id = user.get('id')
                self.username = user.get('username') or user.get('first_name', 'Unknown')
                self.first_name = user.get('first_name', 'Unknown')
        except:
            pass

    def _action(self, action, extra=None):
        url = f"{BASE_URL}?action={action}"
        headers = self.build_headers()
        headers["x-telegram-init-data"] = self.init_data
        try:
            resp = self.session.post(url, json=extra or {}, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            return {"_http_error": resp.status_code, "_body": resp.text[:200]}
        except Exception as e:
            return {"_error": str(e)}

    def init_user(self):
        if not self.init_data:
            return False
        payload = {
            "username": self.username or "",
            "first_name": self.first_name or "",
            "last_name": None,
            "language_code": "id",
            "referred_by": None,
            "partner_code": None,
            "fingerprint": {
                "visitor_id": rand_hex(32),
                "device_hash": rand_hex(32),
                "platform": "Android",
                "user_agent": self.session.headers.get('user-agent'),
                "screen": "384x832x24",
                "timezone": "Asia/Jakarta",
                "languages": "id-ID,en-US",
                "hardware_concurrency": 8,
                "device_memory": 8,
                "cookies_enabled": True
            }
        }
        r = self._action("init", payload)
        if r and r.get('user'):
            self._update_user(r['user'])
            return True
        return False

    def _update_user(self, u):
        self.balance = float(u.get('balance', self.balance) or 0)
        self.total_earned = float(u.get('total_earned', self.total_earned) or 0)
        self.xp = u.get('xp', self.xp)
        self.level = u.get('level', self.level)
        self.country = u.get('country_name', self.country)
        self.is_banned = (u.get('status', 'active') == 'banned')
        self.mining_started_at = u.get('mining_started_at')
        self.mining_ends_at = u.get('mining_ends_at')
        self.boost_active_until = u.get('boost_active_until')

    def get_user(self):
        r = self._action("get_user")
        if r and r.get('user'):
            self._update_user(r['user'])
            return True
        return False

    def start_mining(self):
        r = self._action("start_mining")
        if r and r.get('user'):
            self._update_user(r['user'])
            return True
        return False

    def is_mining_active(self):
        if not self.mining_started_at or not self.mining_ends_at:
            return False
        try:
            end = datetime.fromisoformat(self.mining_ends_at.replace('Z', '+00:00'))
            now = datetime.now(end.tzinfo)
            return now < end
        except:
            return False

    def get_status(self, kind):
        action = KIND_STATUS_ACTION.get(kind, '')
        if not action:
            return None
        return self._action(action)

    def watch_ad(self, kind, provider):
        """Submit per kategori — endpoint beda tiap kategori."""
        action = KIND_SUBMIT_ACTION.get(kind, 'watch_ad')
        return self._action(action, {"ad_watched": True, "ad_provider": provider})

    def _display_result(self, kind, reward, remaining, cooldown):
        print(f"{Colors.NEON_G}  ✅ Reward       : {Colors.NEON_Y}{reward:.10f} DOGE{Colors.END}")
        print(f"{Colors.NEON_C}  📊 Remaining    : {Colors.WHITE}{remaining}{Colors.END}")
        print(f"{Colors.NEON_C}  📡 Kind         : {Colors.WHITE}{kind}{Colors.END}")
        for i in range(cooldown, 0, -1):
            bar_len = 14
            filled = int((cooldown - i) / cooldown * bar_len)
            bar = '█' * filled + '░' * (bar_len - filled)
            row = f"{Colors.NEON_Y}  ⏱️  Cooldown     : {Colors.NEON_C}[{bar}]{Colors.WHITE} {i}s...{Colors.END}"
            sys.stdout.write('\r' + CLEAR_LINE + row)
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write('\r' + CLEAR_LINE)
        sys.stdout.flush()

    def watch_category(self, kind, limit, duration, provider):
        if getattr(self, f'sess_{kind}') >= limit:
            return False

        status = self.get_status(kind)
        if not status:
            print(f"{Colors.RED}  ❌ Gagal fetch status {kind}{Colors.END}")
            return False

        remaining = status.get('remaining', 0)
        if remaining <= 0:
            self.add_log("⚠️", f"{kind} limit habis", Colors.YELLOW)
            return False

        cooldown_rem = status.get('cooldownRemaining', 0)
        if cooldown_rem > 0:
            for i in range(cooldown_rem, 0, -1):
                row = f"{Colors.YELLOW}  ⏳ {kind} cooldown {i}s...{Colors.END}"
                sys.stdout.write('\r' + CLEAR_LINE + row)
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write('\r' + CLEAR_LINE)
            sys.stdout.flush()

        Anim.ad_watch(kind, provider, duration)

        result = self.watch_ad(kind, provider)
        if result and result.get('success'):
            reward = result.get('reward', 0)
            new_rem = result.get('remaining', remaining - 1)
            cd = result.get('cooldown', CFG_COOLDOWN)
            self.balance += reward
            setattr(self, f'sess_{kind}', getattr(self, f'sess_{kind}') + 1)
            self.ads_done_total += 1
            self._display_result(kind, reward, new_rem, cd)
            self.add_log("💰", f"+{reward:.10f} DOGE ({kind})", Colors.NEON_G)
            return True
        else:
            err = (result or {}).get('error', (result or {}).get('message', (result or {}).get('_body', 'unknown')))
            print(f"{Colors.RED}  ❌ Gagal: {err}{Colors.END}")
            self.add_log("❌", f"{kind}: {str(err)[:40]}", Colors.RED)
            return False

    def auto_watch_session(self):
        start_time = datetime.now()
        saldo_awal = self.balance
        self.sess_adsgram = self.sess_popup = self.sess_bonus = self.sess_premium = 0

        print(f"\n{Colors.NEON_Y}🚀 MULAI SESI AUTO-WATCH untuk user {self.telegram_id}{Colors.END}\n")
        lines = [
            f"{Colors.NEON_C}• Adsgram Reward  : {Colors.WHITE}{CFG_ADSGRAM}x ({CFG_DUR_ADSGRAM}s){Colors.END}",
            f"{Colors.NEON_C}• Pop-Up Ads      : {Colors.WHITE}{CFG_POPUP}x ({CFG_DUR_POPUP}s){Colors.END}",
            f"{Colors.NEON_C}• Bonus Ads       : {Colors.WHITE}{CFG_BONUS}x ({CFG_DUR_BONUS}s){Colors.END}",
            f"{Colors.NEON_C}• Premium Ad      : {Colors.WHITE}{CFG_PREMIUM}x ({CFG_DUR_PREMIUM}s){Colors.END}",
            f"{Colors.NEON_C}• Cooldown        : {Colors.WHITE}{CFG_COOLDOWN}s{Colors.END}",
            f"{Colors.NEON_C}• Waktu mulai     : {Colors.WHITE}{start_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}",
        ]
        print_box("SESSION CONFIG", lines, Colors.NEON_Y)
        print(f"{Colors.NEON_Y}💰 Saldo awal     : {Colors.WHITE}{saldo_awal:.10f} DOGE{Colors.END}\n")

        # ADSGRAM
        print(f"\n{Colors.NEON_Y}🎞️  ADSGRAM REWARD{Colors.END}")
        print(f"{Colors.DIM}   {CFG_ADSGRAM} iklan • {CFG_DUR_ADSGRAM}s each • provider: adsgram{Colors.END}")
        for i in range(1, CFG_ADSGRAM + 1):
            print(f"\n{Colors.NEON_C}  ┌─ [ADSGRAM] {i}/{CFG_ADSGRAM}{Colors.END}")
            if not self.watch_category('adsgram', CFG_ADSGRAM, CFG_DUR_ADSGRAM, 'adsgram'):
                time.sleep(2)

        # POP-UP
        print(f"\n{Colors.MAGENTA}🎞️  POP-UP ADS (Interstitial){Colors.END}")
        print(f"{Colors.DIM}   {CFG_POPUP} iklan • {CFG_DUR_POPUP}s each • provider: adsgram{Colors.END}")
        for i in range(1, CFG_POPUP + 1):
            print(f"\n{Colors.MAGENTA}  ┌─ [POP-UP] {i}/{CFG_POPUP}{Colors.END}")
            if not self.watch_category('popup', CFG_POPUP, CFG_DUR_POPUP, 'adsgram'):
                time.sleep(2)

        # BONUS
        print(f"\n{Colors.NEON_G}🎞️  BONUS ADS{Colors.END}")
        print(f"{Colors.DIM}   {CFG_BONUS} iklan • {CFG_DUR_BONUS}s each • provider: monetag/onclicka/gigapub{Colors.END}")
        bonus_providers = ['monetag', 'onclicka', 'gigapub']
        for i in range(1, CFG_BONUS + 1):
            prov = bonus_providers[(i - 1) % len(bonus_providers)]
            print(f"\n{Colors.NEON_G}  ┌─ [BONUS] {i}/{CFG_BONUS} via {prov}{Colors.END}")
            if not self.watch_category('bonus', CFG_BONUS, CFG_DUR_BONUS, prov):
                time.sleep(2)

        # PREMIUM
        print(f"\n{Colors.NEON_P}🎞️  PREMIUM AD{Colors.END}")
        print(f"{Colors.DIM}   {CFG_PREMIUM} iklan • {CFG_DUR_PREMIUM}s each • provider: richads{Colors.END}")
        for i in range(1, CFG_PREMIUM + 1):
            print(f"\n{Colors.NEON_P}  ┌─ [PREMIUM] {i}/{CFG_PREMIUM}{Colors.END}")
            if not self.watch_category('premium', CFG_PREMIUM, CFG_DUR_PREMIUM, 'richads'):
                time.sleep(2)

        self.get_user()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        gain = self.balance - saldo_awal
        print(f"\n{Colors.NEON_G}✅ SESI SELESAI{Colors.END}")
        lines = [
            f"{Colors.NEON_C}🕒 Durasi         : {Colors.WHITE}{int(duration//60)}m {int(duration%60)}s{Colors.END}",
            f"{Colors.NEON_C}📺 Adsgram        : {Colors.WHITE}{self.sess_adsgram}/{CFG_ADSGRAM}{Colors.END}",
            f"{Colors.NEON_C}📺 Pop-Up         : {Colors.WHITE}{self.sess_popup}/{CFG_POPUP}{Colors.END}",
            f"{Colors.NEON_C}📺 Bonus          : {Colors.WHITE}{self.sess_bonus}/{CFG_BONUS}{Colors.END}",
            f"{Colors.NEON_C}📺 Premium        : {Colors.WHITE}{self.sess_premium}/{CFG_PREMIUM}{Colors.END}",
            f"{Colors.NEON_C}📊 Total          : {Colors.WHITE}{self.ads_done_total}{Colors.END}",
            f"{Colors.NEON_Y}💰 Gain sesi      : {Colors.NEON_G}+{gain:.10f} DOGE{Colors.END}",
            f"{Colors.NEON_Y}💰 Saldo akhir    : {Colors.WHITE}{self.balance:.10f} DOGE{Colors.END}",
        ]
        print_box("SESSION SUMMARY", lines, Colors.NEON_G)

    def add_log(self, icon, message, color=Colors.WHITE):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"{Colors.DIM}[{ts}]{Colors.END} {icon} {color}{message}{Colors.END}")
        if len(self.logs) > 8:
            self.logs.popleft()

    def show_status(self):
        clear()
        print(BANNER)
        mining_status = f"{Colors.NEON_G}🟢 ON{Colors.END}" if self.is_mining_active() else f"{Colors.NEON_R}🔴 OFF{Colors.END}"

        lines = [
            f"{Colors.NEON_G}● SYSTEM      : ONLINE{Colors.END}",
            f"{Colors.NEON_C}◈ ENGINE      : READY{Colors.END}",
            f"{Colors.NEON_Y}💰 BALANCE    : {Colors.NEON_Y}{self.balance:.10f} DOGE{Colors.END}",
            f"{Colors.NEON_P}📈 TOTAL      : {Colors.WHITE}{self.total_earned:.10f} DOGE{Colors.END}",
            f"{Colors.NEON_C}🎖️  LEVEL      : Lv{self.level} (XP: {self.xp}){Colors.END}",
            f"{Colors.MAGENTA}⛏️  MINING     : {mining_status}",
            f"{Colors.NEON_C}🌍 NEGARA     : {Colors.WHITE}{self.country}{Colors.END}",
        ]
        if self.mining_ends_at:
            lines.append(f"{Colors.NEON_Y}⏱️  MINING END : {Colors.WHITE}{self.mining_ends_at[:19]}{Colors.END}")
        if self.init_data:
            lines.append(f"{Colors.NEON_G}◈ INIT DATA   : LOADED{Colors.END}")
            lines.append(f"{Colors.NEON_C}👤 USER       : {Colors.WHITE}@{self.username}{Colors.END}")
        else:
            lines.append(f"{Colors.NEON_R}◈ INIT DATA   : EMPTY{Colors.END}")

        print_box("DOGEMINER BOT v1.3", lines, Colors.NEON_Y)
        print()

        w = 66
        print(f"{Colors.NEON_C}╭{'─' * w}╮{Colors.END}")
        print(f"{Colors.NEON_C}│{Colors.END} {Colors.BOLD}{Colors.WHITE}{'L I V E   L O G':^{w}}{Colors.END} {Colors.NEON_C}│{Colors.END}")
        print(f"{Colors.NEON_C}├{'─' * w}┤{Colors.END}")
        if self.logs:
            for log in list(self.logs)[-8:]:
                clean = strip_ansi(log)
                pad = w - len(clean)
                if pad < 0: pad = 0
                print(f"{Colors.NEON_C}│{Colors.END} {log}{' ' * pad} {Colors.NEON_C}│{Colors.END}")
        else:
            print(f"{Colors.NEON_C}│{Colors.END} {Colors.DIM}(belum ada aktivitas){' ' * (w-21)} {Colors.NEON_C}│{Colors.END}")
        print(f"{Colors.NEON_C}╰{'─' * w}╯{Colors.END}")

    def menu(self):
        while True:
            self.show_status()
            print(f"\n{Colors.NEON_C}╭{'─' * 66}╮{Colors.END}")
            print(f"{Colors.NEON_C}│{Colors.END} {Colors.BOLD}{Colors.NEON_G}[1]{Colors.END} {Colors.WHITE}Start Auto Watch (Adsgram + Pop + Bonus + Premium){Colors.END}    {Colors.NEON_C}│{Colors.END}")
            print(f"{Colors.NEON_C}│{Colors.END} {Colors.BOLD}{Colors.NEON_Y}[2]{Colors.END} {Colors.WHITE}Set InitData{Colors.END}                                        {Colors.NEON_C}│{Colors.END}")
            print(f"{Colors.NEON_C}│{Colors.END} {Colors.BOLD}{Colors.NEON_C}[3]{Colors.END} {Colors.WHITE}Start Mining / Refresh User{Colors.END}                         {Colors.NEON_C}│{Colors.END}")
            print(f"{Colors.NEON_C}│{Colors.END} {Colors.BOLD}{Colors.NEON_R}[0]{Colors.END} {Colors.WHITE}Exit{Colors.END}                                                {Colors.NEON_C}│{Colors.END}")
            print(f"{Colors.NEON_C}╰{'─' * 66}╯{Colors.END}")
            choice = input(f"\n{Colors.NEON_C}  Select option → {Colors.END}").strip()

            if choice == "0":
                print(f"\n{Colors.NEON_G}👋 Goodbye!{Colors.END}")
                sys.exit(0)
            elif choice == "1":
                self.start_all()
                input(f"\n{Colors.NEON_C}Press Enter to continue...{Colors.END}")
            elif choice == "2":
                self.set_init_data()
                input(f"\n{Colors.NEON_C}Press Enter to continue...{Colors.END}")
            elif choice == "3":
                clear()
                print(BANNER)
                Anim.spinner("refresh user", 1)
                if self.get_user():
                    print_box("USER INFO", [
                        f"{Colors.NEON_C}💰 Balance : {Colors.NEON_Y}{self.balance:.10f} DOGE{Colors.END}",
                        f"{Colors.NEON_C}📈 Total   : {Colors.WHITE}{self.total_earned:.10f}{Colors.END}",
                        f"{Colors.NEON_C}⛏️  Mining  : {'ON' if self.is_mining_active() else 'OFF'}{Colors.END}",
                    ], Colors.NEON_Y)
                    if not self.is_mining_active():
                        Anim.dots("start mining", 1.5)
                        if self.start_mining():
                            print(f"{Colors.NEON_G}✓ Mining started!{Colors.END}")
                input(f"\n{Colors.NEON_C}Press Enter...{Colors.END}")
            else:
                print(f"{Colors.NEON_R}❌ Invalid!{Colors.END}")
                time.sleep(1)

    def set_init_data(self):
        print(f"\n{Colors.NEON_C}{Colors.BOLD}📝 MASUKKAN TELEGRAM INIT DATA{Colors.END}")
        print(f"{Colors.NEON_Y}(copy dari network log atau WebView){Colors.END}")
        print(f"{Colors.DIM}{'─' * 50}{Colors.END}")
        new_data = input(f"{Colors.NEON_C}➜ {Colors.END}").strip()
        if not new_data:
            print(f"{Colors.NEON_R}❌ InitData tidak boleh kosong!{Colors.END}")
            return
        self.save_init_data(new_data)
        print(f"{Colors.NEON_G}✅ InitData saved!{Colors.END}")

    def start_all(self):
        clear()
        print(BANNER)
        if not self.init_data:
            print(f"{Colors.NEON_R}❌ Set initData dulu lewat menu [2]!{Colors.END}")
            input(f"\n{Colors.NEON_C}Press Enter...{Colors.END}")
            return

        Anim.progress("initialize session", 1.5)
        if not self.init_user():
            print(f"{Colors.NEON_R}❌ Init user gagal!{Colors.END}")
            input(f"\n{Colors.NEON_C}Press Enter...{Colors.END}")
            return

        print()
        lines = [
            f"{Colors.NEON_G}👤 Username       : {Colors.WHITE}@{self.username}{Colors.END}",
            f"{Colors.NEON_G}📛 Nama           : {Colors.WHITE}{self.first_name}{Colors.END}",
            f"{Colors.NEON_G}🆔 Telegram ID    : {Colors.WHITE}{self.telegram_id}{Colors.END}",
            f"{Colors.NEON_Y}💰 Saldo          : {Colors.WHITE}{self.balance:.10f} DOGE{Colors.END}",
            f"{Colors.NEON_Y}📈 Total Earned   : {Colors.WHITE}{self.total_earned:.10f} DOGE{Colors.END}",
            f"{Colors.NEON_C}🎖️  Level / XP     : {Colors.WHITE}Lv{self.level} / {self.xp} XP{Colors.END}",
            f"{Colors.NEON_C}🌍 Negara         : {Colors.WHITE}{self.country}{Colors.END}",
            f"{Colors.NEON_R}🚫 Banned         : {Colors.WHITE}{self.is_banned}{Colors.END}",
        ]
        print_box("✅ LOGIN BERHASIL", lines, Colors.NEON_G)

        if not self.is_mining_active():
            Anim.dots("start mining", 1.5)
            if self.start_mining():
                print(f"{Colors.NEON_G}⛏️  Mining activated!{Colors.END}")

        total_ads = CFG_ADSGRAM + CFG_POPUP + CFG_BONUS + CFG_PREMIUM
        total_sec = (CFG_ADSGRAM * CFG_DUR_ADSGRAM + CFG_POPUP * CFG_DUR_POPUP +
                     CFG_BONUS * CFG_DUR_BONUS + CFG_PREMIUM * CFG_DUR_PREMIUM +
                     total_ads * CFG_COOLDOWN)
        print()
        print_box("⚙️ AUTO-CONFIG", [
            f"{Colors.NEON_C}Adsgram Reward  : {Colors.WHITE}{CFG_ADSGRAM}x{Colors.END}",
            f"{Colors.NEON_C}Pop-Up Ads      : {Colors.WHITE}{CFG_POPUP}x{Colors.END}",
            f"{Colors.NEON_C}Bonus Ads       : {Colors.WHITE}{CFG_BONUS}x{Colors.END}",
            f"{Colors.NEON_C}Premium Ad      : {Colors.WHITE}{CFG_PREMIUM}x{Colors.END}",
            f"{Colors.NEON_C}Cooldown        : {Colors.WHITE}{CFG_COOLDOWN}s{Colors.END}",
            f"{Colors.NEON_C}Estimasi durasi : {Colors.NEON_Y}±{total_sec // 60} menit{Colors.END}",
        ], Colors.NEON_C)

        konfirmasi = input(f"\n{Colors.NEON_Y}▶ Mulai sekarang? (y/n): {Colors.END}").strip().lower()
        if konfirmasi != 'y':
            print(f"{Colors.NEON_R}❌ Dibatalkan.{Colors.END}")
            return

        self.auto_watch_session()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    try:
        clear()
        Anim.glitch("DOGEMINER AUTO WATCH v1.3", 0.6)
        Anim.typewriter("  >>> Loading modules...", delay=0.012, color=Colors.NEON_C)
        bot = DogeMinerBot()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.NEON_R}🛑 Bot dihentikan oleh user!{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.NEON_R}❌ Error: {e}{Colors.END}")
        sys.exit(1)
