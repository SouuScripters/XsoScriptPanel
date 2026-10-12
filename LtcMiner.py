#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import random
import urllib.parse
import requests
from datetime import datetime
from collections import deque

# ============================================================
# COLOR
# ============================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[35m'
    MAGENTA = '\033[35m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;206m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

BANNER = f"""{Colors.PINK}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  ██╗     ████████╗ ██████╗██╗   ██╗██╗  ██╗███████╗██╗   ██╗  ║
║  ██║     ╚══██╔══╝██╔════╝╚██╗ ██╔╝██║  ██║██╔════╝╚██╗ ██╔╝  ║
║  ██║        ██║   ██║      ╚████╔╝ ███████║█████╗   ╚████╔╝   ║
║  ██║        ██║   ██║       ╚██╔╝  ██╔══██║██╔══╝    ╚██╔╝    ║
║  ███████╗   ██║   ╚██████╗   ██║   ██║  ██║███████╗   ██║     ║
║  ╚══════╝   ╚═╝    ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝   ╚═╝     ║
║                                                                  ║
║  {Colors.PINK}🔥 LTC MINER BOT  {Colors.CYAN}│ {Colors.GREEN}v4.1 {Colors.CYAN}│ {Colors.YELLOW}Auto Watch Multi-Counter{Colors.END}  {Colors.PINK}║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.END}
"""

INIT_FILE = "init_ltcminer.txt"
TOKEN_FILE = "token_ltcminer.txt"

# Config default
CFG_IKLAN_BIASA   = 10
CFG_IKLAN_PREMIUM = 10
CFG_POP_AD        = 10
CFG_MEGA_POP      = 5
CFG_COOLDOWN      = 20
CFG_DUR_BIASA     = 30
CFG_DUR_PREMIUM   = 30
CFG_DUR_POP       = 22
CFG_DUR_MEGA      = 12

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def strip_ansi(s):
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)

def print_banner():
    clear_screen()
    print(BANNER)

def print_box(title, lines, color=Colors.CYAN):
    w = 66
    print(f"{color}╭{'─' * w}╮{Colors.END}")
    print(f"{color}│{Colors.END} {Colors.BOLD}{color}{title:^{w}}{Colors.END} {color}│{Colors.END}")
    print(f"{color}├{'─' * w}┤{Colors.END}")
    for line in lines:
        clean = strip_ansi(line)
        pad = w - len(clean)
        if pad < 0: pad = 0
        print(f"{color}│{Colors.END} {line}{' ' * pad} {color}│{Colors.END}")
    print(f"{color}╰{'─' * w}╯{Colors.END}")

def ad_progress(seconds=30, label="📺 Watching ad"):
    for i in range(seconds, 0, -1):
        bar_len = 20
        filled = int((seconds - i) / seconds * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        sys.stdout.write(f"\r{Colors.GREEN}{label} [{bar}] {i}s left{Colors.END}")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

# ============================================================
# MAIN BOT
# ============================================================
class LTCMinerBot:
    def __init__(self):
        self.init_data = ""
        self.telegram_id = None
        self.username = None
        self.first_name = None
        self.balance = 0.0
        self.xp = 0
        self.level = 1
        self.total_earned = 0.0
        self.boost_active = False
        self.mining_active = False
        self.boost_expires = None
        self.is_banned = False
        self.country = "Unknown"
        self.init_age_hours = 0.0

        # Counter per kategori (dari server)
        self.cnt_biaya_global = 0
        self.cnt_premium = 0
        self.cnt_pop = 0
        self.cnt_mega = 0

        # Counter per sesi (buat tracking)
        self.sess_biaya = 0
        self.sess_premium = 0
        self.sess_pop = 0
        self.sess_mega = 0

        self.logs = deque(maxlen=8)
        self.session_gain = 0.0
        self.cycle_count = 0
        self.ads_done_total = 0

        self.base_url = "https://supabase.ltcminer.xyz"
        self.token = self.load_token()
        self.session = requests.Session()
        self.session.headers.update(self.build_headers())

        self.load_init_data()
        self.menu()

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip()
        return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc4NjcxNzIwMCwiZXhwIjo0OTQyMzkwODAwLCJyb2xlIjoiYW5vbiJ9.sUtI3lKmtdBpXDW4StLp_wtdYzUPOZuGEZuMt2tnWZM"

    def build_headers(self):
        return {
            "authorization": f"Bearer {self.token}",
            "apikey": self.token,
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.7977.87 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
            "origin": "https://tgltcminer.vercel.app",
            "referer": "https://tgltcminer.vercel.app/",
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

    # ========== INIT DATA ==========
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
            if 'auth_date' in parsed:
                auth_ts = int(parsed['auth_date'][0])
                self.init_age_hours = (time.time() - auth_ts) / 3600
        except:
            pass

    def show_init_extract(self):
        print(f"\n{Colors.CYAN}⌛ Mengekstrak data dari _init_data...{Colors.END}")
        time.sleep(0.5)
        if not self.init_data:
            print(f"{Colors.RED}❌ InitData kosong! Set dulu lewat menu.{Colors.END}")
            return False
        print(f"{Colors.GREEN}✅ Telegram ID : {Colors.WHITE}{self.telegram_id}{Colors.END}")
        print(f"{Colors.GREEN}✅ Username    : {Colors.WHITE}@{self.username}{Colors.END}")
        print(f"{Colors.GREEN}✅ Nama        : {Colors.WHITE}{self.first_name}{Colors.END}")
        print(f"{Colors.YELLOW}🕒 Umur init   : {Colors.WHITE}{self.init_age_hours:.1f} jam{Colors.END}")
        print(f"\n{Colors.CYAN}⌛ Memverifikasi login...{Colors.END}")
        return True

    def show_login_result(self):
        lines = [
            f"{Colors.GREEN}👤 Username       : {Colors.WHITE}@{self.username}{Colors.END}",
            f"{Colors.GREEN}📛 Nama           : {Colors.WHITE}{self.first_name}{Colors.END}",
            f"{Colors.GREEN}🆔 Telegram ID    : {Colors.WHITE}{self.telegram_id}{Colors.END}",
            f"{Colors.YELLOW}💰 Saldo          : {Colors.WHITE}{self.balance:.10f} LTC{Colors.END}",
            f"{Colors.YELLOW}📺 Daily Ad       : {Colors.WHITE}{self.cnt_biaya_global}/{CFG_IKLAN_BIASA}{Colors.END}",
            f"{Colors.CYAN}🎖️ Level / XP     : {Colors.WHITE}Lv{self.level} / {self.xp} XP{Colors.END}",
            f"{Colors.CYAN}🌍 Negara         : {Colors.WHITE}{self.country}{Colors.END}",
            f"{Colors.RED}🚫 Banned         : {Colors.WHITE}{self.is_banned}{Colors.END}",
        ]
        print_box("✅ LOGIN BERHASIL", lines, Colors.GREEN)

    def show_auto_config(self):
        total_ads = CFG_IKLAN_BIASA + CFG_IKLAN_PREMIUM + CFG_POP_AD + CFG_MEGA_POP
        total_sec = (CFG_IKLAN_BIASA * CFG_DUR_BIASA
                     + CFG_IKLAN_PREMIUM * CFG_DUR_PREMIUM
                     + CFG_POP_AD * CFG_DUR_POP
                     + CFG_MEGA_POP * CFG_DUR_MEGA
                     + total_ads * CFG_COOLDOWN)
        est_min = total_sec // 60
        lines = [
            f"{Colors.CYAN}Iklan biasa        : {Colors.WHITE}{CFG_IKLAN_BIASA}x{Colors.END}",
            f"{Colors.CYAN}Iklan premium      : {Colors.WHITE}{CFG_IKLAN_PREMIUM}x{Colors.END}",
            f"{Colors.CYAN}Pop-ad             : {Colors.WHITE}{CFG_POP_AD}x{Colors.END}",
            f"{Colors.CYAN}Mega pop-ad        : {Colors.WHITE}{CFG_MEGA_POP}x{Colors.END}",
            f"{Colors.CYAN}Cooldown           : {Colors.WHITE}{CFG_COOLDOWN}s{Colors.END}",
            f"{Colors.CYAN}Estimasi durasi    : {Colors.YELLOW}±{est_min} menit{Colors.END}",
        ]
        print()
        print_box("⚙️ AUTO-CONFIG (default)", lines, Colors.CYAN)

    # ========== API ==========
    def _post(self, endpoint, data):
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.post(url, json=data, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            return {"_http_error": resp.status_code, "_body": resp.text[:200]}
        except Exception as e:
            return {"_error": str(e)}

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            return None
        except:
            return None

    # ========== LOGIN ==========
    def login(self):
        if not self.init_data:
            return False
        payload = {
            "action": "get_user",
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/user-operations", payload)
        if result and result.get('success') and result.get('user'):
            u = result['user']
            self.balance = u.get('balance', 0.0)
            self.xp = u.get('xp', 0)
            self.level = u.get('level', 1)
            self.total_earned = u.get('total_earned', 0.0)
            self.cnt_biaya_global = u.get('daily_ad_count', 0)
            self.mining_active = u.get('mining_active', False)
            self.boost_active = u.get('boost_active', False)
            self.boost_expires = u.get('boost_expires_at')
            self.is_banned = u.get('is_banned', False)
            self.country = u.get('country_name', 'Indonesia')
            self.add_log("✅", f"Login OK — bal {self.balance:.10f}", Colors.GREEN)
            return True
        else:
            err = (result or {}).get('error', (result or {}).get('message', 'unknown'))
            self.add_log("❌", f"Login gagal: {err}", Colors.RED)
            return False

    def register_or_login(self):
        """Register pake endpoint asli biar dapet user data lengkap"""
        if not self.init_data:
            return False
        payload = {
            "action": "register_or_login",
            "telegram_id": self.telegram_id,
            "username": self.username or "",
            "first_name": self.first_name or "",
            "last_name": "",
            "language_code": "id",
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/user-operations", payload)
        if result and result.get('success'):
            user = result.get('user', {})
            self.balance = user.get('balance', self.balance)
            self.xp = user.get('xp', self.xp)
            self.level = user.get('level', self.level)
            self.cnt_biaya_global = user.get('daily_ad_count', 0)
            return True
        return False

    def start_mining(self):
        if self.mining_active:
            return True
        payload = {
            "action": "start_mining",
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        r = self._post("/functions/v1/user-operations", payload)
        return bool(r and r.get('success'))

    def activate_boost(self):
        if self.boost_active:
            return True
        payload = {
            "action": "activate_boost",
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        r = self._post("/functions/v1/user-operations", payload)
        return bool(r and r.get('success'))

    def claim_daily_task(self):
        payload = {
            "action": "claim_daily_ad_task",
            "telegram_id": self.telegram_id,
            "task_type": "watch_3",
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        r = self._post("/functions/v1/user-operations", payload)
        return bool(r and r.get('success'))

    # ========== AD RESULT DISPLAY ==========
    def _show_ad_result(self, kind, reward, provider):
        print(f"{Colors.GREEN}✅ Reward         : {Colors.YELLOW}{reward:.10f} LTC{Colors.END}")
        print(f"{Colors.CYAN}📊 Daily Count    : {Colors.WHITE}{self.cnt_biaya_global}{Colors.END}")
        print(f"{Colors.CYAN}🛡️  VPN            : {Colors.WHITE}False{Colors.END}")
        print(f"{Colors.CYAN}📡 Provider       : {Colors.WHITE}{provider}{Colors.END}")
        # Cooldown visual
        for i in range(CFG_COOLDOWN, 0, -1):
            bar_len = 12
            filled = int((CFG_COOLDOWN - i) / CFG_COOLDOWN * bar_len)
            bar = '█' * filled + '░' * (bar_len - filled)
            sys.stdout.write(f"\r{Colors.YELLOW}⏱️  Cooldown       : {Colors.CYAN}[{bar}]{Colors.WHITE} {i}s tersisa...{Colors.END}")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()

    # ========== IKLAN BIASA ==========
    def watch_short_ad(self, idx, total):
        if self.sess_biaya >= CFG_IKLAN_BIASA:
            return False
        print(f"\n{Colors.BOLD}{Colors.CYAN}┌─ [{Colors.WHITE}IKLAN BIASA{Colors.CYAN}] IKLAN #{idx}/{total}{Colors.END}")
        print(f"{Colors.CYAN}└─────────────────────────────────────────────────────{Colors.END}")
        ad_progress(CFG_DUR_BIASA, "📺 Watching ad")

        payload = {
            "action": "ad_watch_reward",
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/user-operations", payload)
        if result and result.get('success'):
            reward = result.get('reward', 0.0)
            if reward > 0:
                self.balance += reward
                self.session_gain += reward
                self.cnt_biaya_global = result.get('dailyAdCount', self.cnt_biaya_global + 1)
                self.sess_biaya += 1
                self.ads_done_total += 1
                self._show_ad_result("short", reward, result.get('provider', 'adsgram_reward'))
                return True
        err = (result or {}).get('message', (result or {}).get('error', 'no reward'))
        self.add_log("❌", f"Short: {err}", Colors.RED)
        return False

    # ========== IKLAN PREMIUM ==========
    def watch_premium_ad(self, idx, total):
        if self.sess_premium >= CFG_IKLAN_PREMIUM:
            return False
        print(f"\n{Colors.BOLD}{Colors.PURPLE}┌─ [{Colors.WHITE}IKLAN PREMIUM{Colors.PURPLE}] IKLAN #{idx}/{total}{Colors.END}")
        print(f"{Colors.PURPLE}└─────────────────────────────────────────────────────{Colors.END}")
        ad_progress(CFG_DUR_PREMIUM, "📺 Premium ad")

        payload = {
            "action": "premium_ad_reward",
            "telegram_id": self.telegram_id,
            "provider": "gigapub",
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/user-operations", payload)
        if result and result.get('success'):
            reward = result.get('reward', 0.0)
            if reward > 0:
                self.balance += reward
                self.session_gain += reward
                self.cnt_premium = result.get('dailyAdCount', self.cnt_premium + 1)
                self.cnt_biaya_global = self.cnt_premium
                self.sess_premium += 1
                self.ads_done_total += 1
                self._show_ad_result("premium", reward, result.get('provider', 'gigapub'))
                return True
            else:
                # success tapi reward 0 = limit tercapai
                self.add_log("⚠️", "Premium limit reached", Colors.YELLOW)
                return False
        err = (result or {}).get('message', (result or {}).get('error', 'no reward'))
        self.add_log("❌", f"Premium: {err}", Colors.RED)
        return False

    # ========== POP AD ==========
    def pop_ad_start(self):
        payload = {
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/pop-ad-start", payload)
        if result and result.get('ok'):
            return result.get('session_id')
        return None

    def pop_ad_claim(self, session_id):
        payload = {
            "telegram_id": self.telegram_id,
            "session_id": session_id,
            "blur_total_ms": random.randint(2000, 8000),
            "elapsed_ms": random.randint(25000, 35000),
            "ad_done": True,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/pop-ad-claim", payload)
        if result and result.get('ok'):
            reward = result.get('reward', 0.0)
            if reward > 0:
                self.balance += reward
                self.session_gain += reward
                self.cnt_pop += 1
                self.ads_done_total += 1
                return reward
        return 0

    def watch_pop_ad(self, idx, total):
        if self.sess_pop >= CFG_POP_AD:
            return False
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}┌─ [{Colors.WHITE}POP-AD{Colors.MAGENTA}] IKLAN #{idx}/{total}{Colors.END}")
        print(f"{Colors.MAGENTA}└─────────────────────────────────────────────────────{Colors.END}")
        session_id = self.pop_ad_start()
        if not session_id:
            self.add_log("❌", "Pop start gagal", Colors.RED)
            return False
        ad_progress(CFG_DUR_POP, "📺 Pop ad")
        reward = self.pop_ad_claim(session_id)
        if reward > 0:
            self.sess_pop += 1
            self._show_ad_result("pop", reward, "pop_reward")
            return True
        self.add_log("❌", "Pop claim gagal", Colors.RED)
        return False

    # ========== MEGA POP ==========
    def mega_pop_ad_start(self):
        payload = {
            "telegram_id": self.telegram_id,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/mega-pop-ad-start", payload)
        if result and result.get('ok'):
            return result.get('session_id')
        return None

    def mega_pop_ad_claim(self, session_id):
        payload = {
            "telegram_id": self.telegram_id,
            "session_id": session_id,
            "blur_total_ms": random.randint(3000, 10000),
            "elapsed_ms": random.randint(25000, 40000),
            "ad_done": True,
            "_init_data": self.init_data,
            "_ts": int(time.time() * 1000)
        }
        result = self._post("/functions/v1/mega-pop-ad-claim", payload)
        if result and result.get('ok'):
            reward = result.get('reward', 0.0)
            if reward > 0:
                self.balance += reward
                self.session_gain += reward
                self.cnt_mega += 1
                self.ads_done_total += 1
                return reward
        return 0

    def watch_mega_pop_ad(self, idx, total):
        if self.sess_mega >= CFG_MEGA_POP:
            return False
        print(f"\n{Colors.BOLD}{Colors.ORANGE}┌─ [{Colors.WHITE}MEGA POP-AD{Colors.ORANGE}] IKLAN #{idx}/{total}{Colors.END}")
        print(f"{Colors.ORANGE}└─────────────────────────────────────────────────────{Colors.END}")
        session_id = self.mega_pop_ad_start()
        if not session_id:
            self.add_log("❌", "Mega start gagal", Colors.RED)
            return False
        ad_progress(CFG_DUR_MEGA, "📺 Mega ad")
        reward = self.mega_pop_ad_claim(session_id)
        if reward > 0:
            self.sess_mega += 1
            self._show_ad_result("mega", reward, "mega_reward")
            return True
        self.add_log("❌", "Mega claim gagal", Colors.RED)
        return False

    # ========== AUTO WATCH SESSION ==========
    def auto_watch_session(self):
        start_time = datetime.now()
        saldo_awal = self.balance

        # Reset counter per sesi
        self.sess_biaya = 0
        self.sess_premium = 0
        self.sess_pop = 0
        self.sess_mega = 0

        total_ads = CFG_IKLAN_BIASA + CFG_IKLAN_PREMIUM + CFG_POP_AD + CFG_MEGA_POP

        print(f"\n{Colors.PINK}🚀 MULAI SESI AUTO-WATCH untuk user {self.telegram_id}{Colors.END}\n")
        lines = [
            f"{Colors.CYAN}• Iklan biasa      : {Colors.WHITE}{CFG_IKLAN_BIASA}x{Colors.END}",
            f"{Colors.CYAN}• Iklan premium    : {Colors.WHITE}{CFG_IKLAN_PREMIUM}x (gigapub){Colors.END}",
            f"{Colors.CYAN}• Pop-ad           : {Colors.WHITE}{CFG_POP_AD}x ({CFG_DUR_POP}s){Colors.END}",
            f"{Colors.CYAN}• Mega pop-ad      : {Colors.WHITE}{CFG_MEGA_POP}x ({CFG_DUR_MEGA}s){Colors.END}",
            f"{Colors.CYAN}• Cooldown         : {Colors.WHITE}{CFG_COOLDOWN}s{Colors.END}",
            f"{Colors.CYAN}• Waktu mulai      : {Colors.WHITE}{start_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}",
        ]
        print_box("SESSION CONFIG", lines, Colors.PINK)

        print(f"{Colors.YELLOW}💰 Saldo awal      : {Colors.WHITE}{saldo_awal:.10f} LTC{Colors.END}\n")

        # === IKLAN BIASA ===
        print(f"\n{Colors.PINK}🎞️  IKLAN BIASA{Colors.END}")
        print(f"{Colors.DIM}   {CFG_IKLAN_BIASA} iklan • cooldown {CFG_COOLDOWN}s • provider: adsgram_reward{Colors.END}")
        for i in range(1, CFG_IKLAN_BIASA + 1):
            if not self.watch_short_ad(i, CFG_IKLAN_BIASA):
                time.sleep(2)

        # === IKLAN PREMIUM ===
        print(f"\n{Colors.PURPLE}🎞️  IKLAN PREMIUM (gigapub){Colors.END}")
        print(f"{Colors.DIM}   {CFG_IKLAN_PREMIUM} iklan • cooldown {CFG_COOLDOWN}s{Colors.END}")
        for i in range(1, CFG_IKLAN_PREMIUM + 1):
            if not self.watch_premium_ad(i, CFG_IKLAN_PREMIUM):
                time.sleep(2)

        # === POP-AD ===
        print(f"\n{Colors.MAGENTA}🎞️  POP-AD{Colors.END}")
        print(f"{Colors.DIM}   {CFG_POP_AD} iklan • {CFG_DUR_POP}s each{Colors.END}")
        for i in range(1, CFG_POP_AD + 1):
            if not self.watch_pop_ad(i, CFG_POP_AD):
                time.sleep(2)

        # === MEGA POP-AD ===
        print(f"\n{Colors.ORANGE}🎞️  MEGA POP-AD{Colors.END}")
        print(f"{Colors.DIM}   {CFG_MEGA_POP} iklan • {CFG_DUR_MEGA}s each{Colors.END}")
        for i in range(1, CFG_MEGA_POP + 1):
            if not self.watch_mega_pop_ad(i, CFG_MEGA_POP):
                time.sleep(2)

        # === CLAIM DAILY ===
        self.claim_daily_task()

        # === REFRESH BALANCE ===
        self.login()

        # === SUMMARY ===
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        gain = self.balance - saldo_awal

        print(f"\n{Colors.GREEN}✅ SESI SELESAI{Colors.END}")
        lines = [
            f"{Colors.CYAN}🕒 Durasi         : {Colors.WHITE}{int(duration//60)}m {int(duration%60)}s{Colors.END}",
            f"{Colors.CYAN}📺 Iklan biasa    : {Colors.WHITE}{self.sess_biaya}/{CFG_IKLAN_BIASA}{Colors.END}",
            f"{Colors.CYAN}📺 Iklan premium  : {Colors.WHITE}{self.sess_premium}/{CFG_IKLAN_PREMIUM}{Colors.END}",
            f"{Colors.CYAN}📺 Pop-ad         : {Colors.WHITE}{self.sess_pop}/{CFG_POP_AD}{Colors.END}",
            f"{Colors.CYAN}📺 Mega pop-ad    : {Colors.WHITE}{self.sess_mega}/{CFG_MEGA_POP}{Colors.END}",
            f"{Colors.CYAN}📊 Total iklan    : {Colors.WHITE}{self.ads_done_total}{Colors.END}",
            f"{Colors.YELLOW}💰 Gain sesi      : {Colors.GREEN}+{gain:.10f} LTC{Colors.END}",
            f"{Colors.YELLOW}💰 Saldo akhir    : {Colors.WHITE}{self.balance:.10f} LTC{Colors.END}",
        ]
        print_box("SESSION SUMMARY", lines, Colors.GREEN)

    # ========== LOG ==========
    def add_log(self, icon, message, color=Colors.WHITE):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"{Colors.DIM}[{timestamp}]{Colors.END} {icon} {color}{message}{Colors.END}")
        if len(self.logs) > 8:
            self.logs.popleft()

    # ========== STATUS DISPLAY ==========
    def show_status(self):
        clear_screen()
        print_banner()
        mining_status = f"{Colors.GREEN}🟢 ON{Colors.END}" if self.mining_active else f"{Colors.RED}🔴 OFF{Colors.END}"
        boost_status = f"{Colors.GREEN}🟢 ON{Colors.END}" if self.boost_active else f"{Colors.RED}🔴 OFF{Colors.END}"
        lines = [
            f"{Colors.GREEN}● SYSTEM        : ONLINE{Colors.END}",
            f"{Colors.CYAN}◈ ENGINE        : READY{Colors.END}",
            f"{Colors.PINK}◉ NETWORK       : ACTIVE{Colors.END}",
            f"{Colors.GREEN}💰 BALANCE      : {Colors.YELLOW}{self.balance:.10f} LTC{Colors.END}",
            f"{Colors.PURPLE}📈 LEVEL        : Lv{self.level} (XP: {self.xp}){Colors.END}",
            f"{Colors.CYAN}📺 ADS TODAY    : {Colors.YELLOW}{self.cnt_biaya_global}/{CFG_IKLAN_BIASA}{Colors.END}",
            f"{Colors.MAGENTA}⛏️ MINING       : {mining_status}",
            f"{Colors.PINK}🚀 BOOST        : {boost_status}",
            f"{Colors.ORANGE}🔄 SIKLUS       : {self.cycle_count}{Colors.END}",
        ]
        if self.init_data:
            lines.append(f"{Colors.GREEN}◈ INIT DATA     : LOADED{Colors.END}")
            lines.append(f"{Colors.CYAN}👤 USER         : {Colors.WHITE}@{self.username}{Colors.END}")
        else:
            lines.append(f"{Colors.RED}◈ INIT DATA     : EMPTY{Colors.END}")

        print_box("LTC MINER BOT v4.1", lines, Colors.PINK)
        print()

        # Live log
        w = 66
        print(f"{Colors.CYAN}╭{'─' * w}╮{Colors.END}")
        print(f"{Colors.CYAN}│{Colors.END} {Colors.BOLD}{Colors.WHITE}{'L I V E   L O G':^{w}}{Colors.END} {Colors.CYAN}│{Colors.END}")
        print(f"{Colors.CYAN}├{'─' * w}┤{Colors.END}")
        if self.logs:
            for log in list(self.logs)[-8:]:
                clean = strip_ansi(log)
                pad = w - len(clean)
                if pad < 0: pad = 0
                print(f"{Colors.CYAN}│{Colors.END} {log}{' ' * pad} {Colors.CYAN}│{Colors.END}")
        else:
            print(f"{Colors.CYAN}│{Colors.END} {Colors.DIM}(belum ada aktivitas){' ' * (w-22)} {Colors.CYAN}│{Colors.END}")
        print(f"{Colors.CYAN}╰{'─' * w}╯{Colors.END}")

    # ========== MENU ==========
    def menu(self):
        while True:
            self.show_status()
            print(f"\n{Colors.CYAN}╭{'─' * 66}╮{Colors.END}")
            print(f"{Colors.CYAN}│{Colors.END} {Colors.BOLD}{Colors.GREEN}[1]{Colors.END} {Colors.WHITE}Start Auto Watch (10B → 10P → 10POP → 5MEGA){Colors.END}          {Colors.CYAN}│{Colors.END}")
            print(f"{Colors.CYAN}│{Colors.END} {Colors.BOLD}{Colors.YELLOW}[2]{Colors.END} {Colors.WHITE}Set InitData{Colors.END}                                          {Colors.CYAN}│{Colors.END}")
            print(f"{Colors.CYAN}│{Colors.END} {Colors.BOLD}{Colors.CYAN}[3]{Colors.END} {Colors.WHITE}Refresh Login (fetch user info){Colors.END}                        {Colors.CYAN}│{Colors.END}")
            print(f"{Colors.CYAN}│{Colors.END} {Colors.BOLD}{Colors.RED}[0]{Colors.END} {Colors.WHITE}Exit{Colors.END}                                                  {Colors.CYAN}│{Colors.END}")
            print(f"{Colors.CYAN}╰{'─' * 66}╯{Colors.END}")
            print()
            choice = input(f"{Colors.CYAN}  Select option → {Colors.END}").strip()

            if choice == "0":
                print(f"\n{Colors.GREEN}👋 Goodbye!{Colors.END}")
                sys.exit(0)
            elif choice == "1":
                self.start_all()
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
            elif choice == "2":
                self.set_init_data()
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
            elif choice == "3":
                if self.show_init_extract():
                    if self.login():
                        self.show_login_result()
                    else:
                        print(f"{Colors.RED}❌ Login gagal!{Colors.END}")
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
            else:
                print(f"{Colors.RED}❌ Invalid option!{Colors.END}")
                time.sleep(1)

    def set_init_data(self):
        print(f"\n{Colors.CYAN}{Colors.BOLD}📝 MASUKKAN TELEGRAM INIT DATA{Colors.END}")
        print(f"{Colors.YELLOW}(copy dari network log atau WebView){Colors.END}")
        print(f"{Colors.DIM}{'─' * 50}{Colors.END}")
        new_data = input(f"{Colors.CYAN}➜ {Colors.END}").strip()
        if not new_data:
            print(f"{Colors.RED}❌ InitData tidak boleh kosong!{Colors.END}")
            return
        self.save_init_data(new_data)
        print(f"{Colors.GREEN}✅ InitData saved!{Colors.END}")

    # ========== START ALL ==========
    def start_all(self):
        clear_screen()
        print_banner()

        if not self.show_init_extract():
            input(f"\n{Colors.CYAN}Press Enter...{Colors.END}")
            return

        if not self.login():
            print(f"{Colors.RED}❌ Verifikasi login gagal!{Colors.END}")
            input(f"\n{Colors.CYAN}Press Enter...{Colors.END}")
            return

        print()
        self.show_login_result()
        print()

        # Auto-start mining & boost
        if not self.mining_active:
            if self.start_mining():
                print(f"{Colors.GREEN}⛏️ Mining activated{Colors.END}")
        if not self.boost_active:
            if self.activate_boost():
                print(f"{Colors.GREEN}🚀 Boost activated{Colors.END}")

        self.show_auto_config()
        print()
        konfirmasi = input(f"{Colors.YELLOW}▶ Mulai sekarang? (y/n): {Colors.END}").strip().lower()
        if konfirmasi != 'y':
            print(f"{Colors.RED}❌ Dibatalkan.{Colors.END}")
            return

        self.auto_watch_session()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    try:
        bot = LTCMinerBot()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}🛑 Bot dihentikan oleh user!{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")
        sys.exit(1)
