#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import urllib.parse
import requests
import uuid
from datetime import datetime

# ===== COLOR =====
class Colors:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PINK = '\033[38;5;206m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    END = '\033[0m'

BANNER = f"""
{Colors.CYAN}================================================{Colors.END}
{Colors.PINK}             █████╗ ████████╗███████╗{Colors.END}
{Colors.PINK}            ██╔══██╗╚══██╔══╝██╔════╝{Colors.END}
{Colors.PINK}            ███████║   ██║   █████╗{Colors.END}
{Colors.PINK}            ██╔══██║   ██║   ██╔══╝{Colors.END}
{Colors.PINK}            ██║  ██║   ██║   ███████╗{Colors.END}
{Colors.PINK}            ╚═╝  ╚═╝   ╚═╝   ╚══════╝{Colors.END}
{Colors.CYAN}================================================{Colors.END}
{Colors.BOLD}{Colors.WHITE}              ⚡ ATF MINER ⚡{Colors.END}
{Colors.BOLD}{Colors.WHITE}              AUTO FARM BOT{Colors.END}
{Colors.CYAN}================================================{Colors.END}
{Colors.GREEN}        ScriptMaker : MoneyMaker_w{Colors.END}
{Colors.CYAN}================================================{Colors.END}
{Colors.GREEN}   [✓] MINING     [✓] CLAIM{Colors.END}
{Colors.GREEN}   [✓] REWARD     [✓] AUTO RUN{Colors.END}
{Colors.GREEN}   [✓] AUTO TASK  [✓] SKIP EMPTY{Colors.END}
{Colors.CYAN}================================================{Colors.END}
"""

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

# ============================================================
# SINGLE USE BOT
# ============================================================

class ATFMinerBot:
    # List task ID yang bakal dicoba
    # dari network log: telegram_join, kemungkinan ada lain
    KNOWN_TASKS = [
        "telegram_join",
        "telegram_channel",
        "telegram_group",
        "twitter_follow",
        "youtube_subscribe",
        "tiktok_follow",
        "instagram_follow",
        "daily_checkin",
    ]

    def __init__(self):
        self.device_id = f"dev-{uuid.uuid4()}"
        self.base_url = "https://atfminers.asloni.online"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.181 Mobile Safari/537.36 Telegram-Android/12.9.1",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/miner/index.html"
        })
        self.balance = 0.0
        self.total_boost = 0
        self.mining_freeze_at = 0
        self.username = "Unknown"
        self.tg_id = "0"
        self.init_data = ""
        self.is_logged_in = False

        self.get_init_data()

    def get_init_data(self):
        print(f"{Colors.CYAN}╔════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.CYAN}║{Colors.END}  {Colors.BOLD}MASUKKAN TELEGRAM INIT DATA{Colors.END}    {Colors.CYAN}║{Colors.END}")
        print(f"{Colors.CYAN}║{Colors.END}  {Colors.GRAY}(copy dari WebView / network log){Colors.END} {Colors.CYAN}║{Colors.END}")
        print(f"{Colors.CYAN}╚════════════════════════════════════════╝{Colors.END}")
        print()
        self.init_data = input(f"{Colors.GREEN}➜ {Colors.END}").strip()

        if not self.init_data:
            print(f"{Colors.RED}❌ InitData tidak boleh kosong!{Colors.END}")
            sys.exit(1)

        if 'query_id=' not in self.init_data or 'user=' not in self.init_data:
            print(f"{Colors.YELLOW}⚠️ InitData sepertinya tidak lengkap{Colors.END}")
            retry = input(f"{Colors.YELLOW}Lanjutkan tetap? (y/n): {Colors.END}").strip().lower()
            if retry != 'y':
                self.get_init_data()
                return

        self._parse_user()
        self.login()

    def _parse_user(self):
        try:
            parsed = urllib.parse.parse_qs(self.init_data)
            if 'user' in parsed:
                user = json.loads(parsed['user'][0])
                self.username = user.get('username') or user.get('first_name', 'Unknown')
                self.tg_id = str(user.get('id', '0'))
                print(f"{Colors.GREEN}✅ User terdeteksi: {self.username} (ID: {self.tg_id}){Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ InitData tidak mengandung 'user'{Colors.END}")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Parse error: {e}{Colors.END}")

    def _call_api(self, action, extra=None):
        url = f"{self.base_url}/miner/index.php"
        params = {"action": action, "t": str(int(time.time()*1000))}
        payload = {
            "initData": self.init_data,
            "request_id": str(uuid.uuid4()),
            "device_id": self.device_id
        }
        if extra:
            payload.update(extra)

        try:
            resp = self.session.post(url, params=params, json=payload, timeout=30)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return {"status": "error", "raw": resp.text[:300]}
            else:
                return {"status": "error", "http": resp.status_code}
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    def login(self):
        print(f"\n{Colors.CYAN}🔄 Mencoba login...{Colors.END}")
        result = self._call_api("login")

        if result and result.get('status') == 'success':
            user = result.get('user', {})
            self.is_logged_in = True
            self.balance = float(user.get('mined_balance', 0))
            self.total_boost = int(user.get('total_boost_count', 0))
            self.mining_freeze_at = int(user.get('mining_freezes_at', 0))

            print(f"\n{Colors.GREEN}✅ LOGIN BERHASIL!{Colors.END}")
            print(f"{Colors.CYAN}👤 Username :{Colors.END} {Colors.WHITE}{user.get('username')}{Colors.END}")
            print(f"{Colors.CYAN}📊 Level    :{Colors.END} {Colors.WHITE}{user.get('miner_level')}{Colors.END}")
            print(f"{Colors.CYAN}💰 Balance  :{Colors.END} {Colors.WHITE}{self.balance:.4f} ATF{Colors.END}")
            print(f"{Colors.CYAN}📈 Total Boost:{Colors.END} {Colors.WHITE}{self.total_boost}{Colors.END}")
            print()
            return True
        else:
            print(f"\n{Colors.RED}❌ LOGIN GAGAL!{Colors.END}")
            if result and result.get('message'):
                print(f"{Colors.RED}Pesan: {result.get('message')}{Colors.END}")
            if result and result.get('reason'):
                print(f"{Colors.RED}Alasan: {result.get('reason')}{Colors.END}")

            retry = input(f"\n{Colors.YELLOW}Masukkan initData baru? (y/n): {Colors.END}").strip().lower()
            if retry == 'y':
                self.get_init_data()
            else:
                print(f"{Colors.RED}Keluar...{Colors.END}")
                sys.exit(1)

    def countdown(self, sec, msg="⏳ Menunggu"):
        for i in range(sec, 0, -1):
            print(f"\r{Colors.YELLOW}{msg} {i} detik...{Colors.END}", end="", flush=True)
            time.sleep(1)
        print(f"\r{Colors.GREEN}{msg} selesai!{Colors.END}          ")

    # ==================== TASK ====================
    def try_claim_task(self, task_id):
        """
        Coba claim 1 task.
        Return: 'claimed' / 'skip' / 'already' / 'not_found' / 'error'
        """
        extra = {
            "tg_id": self.tg_id,
            "task_id": task_id,
            "client_started_at": 0,
        }
        result = self._call_api("claim_task", extra)

        if not result:
            return 'error', 0

        status = str(result.get('status', '')).lower()
        msg = str(result.get('message', '')).lower()

        # sukses
        if status == 'success':
            reward = result.get('reward', 0)
            return 'claimed', reward

        # sudah pernah / already
        for kw in ['already', 'sudah', 'claimed', 'duplicate']:
            if kw in msg:
                return 'already', 0

        # task gak ada / belum dibuka
        for kw in ['not found', 'invalid task', 'unknown', 'tidak ada', 'unavailable', 'not available']:
            if kw in msg or status in ('not_found', 'invalid'):
                return 'not_found', 0

        # task belum bisa (harus join dulu dll)
        for kw in ['not completed', 'belum', 'must join', 'please join', 'requirement', 'need to']:
            if kw in msg:
                return 'skip', 0

        # rate limited
        if status == 'rate_limited':
            return 'skip', 0

        # default
        return 'skip', 0

    def run_tasks(self):
        """Auto kerjakan semua task yang bisa, skip yang gagal/empty"""
        print(f"\n{Colors.CYAN}{'═' * 50}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}📋 AUTO TASK{Colors.END}")
        print(f"{Colors.CYAN}{'═' * 50}{Colors.END}")

        total_claimed = 0
        total_reward = 0

        for task_id in self.KNOWN_TASKS:
            print(f"{Colors.GRAY}➜ Coba task: {Colors.WHITE}{task_id}{Colors.END}", end=" ")
            res, reward = self.try_claim_task(task_id)

            if res == 'claimed':
                print(f"{Colors.GREEN}✅ +{reward} ATF{Colors.END}")
                total_claimed += 1
                total_reward += float(reward or 0)
            elif res == 'already':
                print(f"{Colors.GRAY}↺ sudah claim{Colors.END}")
            elif res == 'not_found':
                print(f"{Colors.GRAY}⏭ tidak ada{Colors.END}")
            elif res == 'skip':
                print(f"{Colors.YELLOW}⏭ skip (belum memenuhi){Colors.END}")
            else:
                print(f"{Colors.RED}✗ error{Colors.END}")

            # delay kecil biar gak rate limited
            time.sleep(1.2)

        print(f"{Colors.CYAN}{'═' * 50}{Colors.END}")
        if total_claimed > 0:
            print(f"{Colors.GREEN}✅ Task selesai: {total_claimed} claimed | +{total_reward} ATF{Colors.END}")
        else:
            print(f"{Colors.YELLOW}ℹ️ Tidak ada task baru hari ini{Colors.END}")
        print(f"{Colors.CYAN}{'═' * 50}{Colors.END}\n")

        return total_claimed, total_reward

    # ==================== CLAIM ====================
    def claim(self):
        print(f"{Colors.CYAN}🔄 Claiming reward...{Colors.END}")
        result = self._call_api("claim")
        if not result:
            print(f"{Colors.RED}❌ Claim gagal{Colors.END}")
            return False

        status = result.get('status')
        if status == 'success':
            self.balance = float(result.get('user', {}).get('mined_balance', self.balance))
            self.mining_freeze_at = int(result.get('user', {}).get('mining_freezes_at', 0))
            print(f"{Colors.GREEN}✅ Claim berhasil! Balance: {self.balance:.4f} ATF{Colors.END}")
            return True
        elif status in ('busy', 'cooldown'):
            wait = result.get('mining_freezes_at', 0) - int(time.time())
            if wait > 0:
                print(f"{Colors.YELLOW}⏳ Claim cooldown {wait} detik{Colors.END}")
                self.countdown(wait, "⏳ Claim cooldown")
                return self.claim()
        else:
            print(f"{Colors.RED}❌ Claim status: {status}{Colors.END}")
        return False

    # ==================== BOOST ====================
    def do_boost(self):
        if self.mining_freeze_at > 0 and int(time.time()) >= self.mining_freeze_at:
            print(f"{Colors.YELLOW}⛔ Mining frozen! Claim dulu...{Colors.END}")
            if not self.claim():
                print(f"{Colors.RED}❌ Claim gagal, skip boost{Colors.END}")
                return False

        print(f"{Colors.CYAN}🚀 Mengirim boost...{Colors.END}")
        result = self._call_api("activate_boost", {"display_preview": round(0.15 + 0.1 * (time.time() % 1), 4)})

        if not result:
            print(f"{Colors.RED}❌ Boost gagal (no response){Colors.END}")
            return False

        status = result.get('status')

        if status == 'success':
            reward = result.get('pending_reward', 0)
            self.balance = float(result.get('user', {}).get('mined_balance', self.balance))
            self.total_boost = int(result.get('user', {}).get('total_boost_count', self.total_boost))
            self.mining_freeze_at = int(result.get('user', {}).get('mining_freezes_at', 0))

            print(f"{Colors.GREEN}✅ BOOST BERHASIL!{Colors.END}")
            print(f"   {Colors.YELLOW}+{reward:.4f} ATF{Colors.END}")
            print(f"   {Colors.CYAN}💰 Balance: {self.balance:.4f} ATF{Colors.END}")
            print(f"   {Colors.CYAN}📊 Total boost: {self.total_boost}{Colors.END}")
            print(f"   {Colors.GRAY}⏰ {datetime.now().strftime('%H:%M:%S')}{Colors.END}")
            return True

        elif status == 'frozen':
            print(f"{Colors.YELLOW}⛔ Frozen response, claim...{Colors.END}")
            if self.claim():
                return self.do_boost()
            return False

        elif status in ('busy', 'cooldown'):
            wait = result.get('boost_ready_at', 0) - int(time.time())
            if wait > 0:
                print(f"{Colors.YELLOW}⏳ Cooldown {wait} detik{Colors.END}")
                self.countdown(wait, "⏳ Cooldown")
                return self.do_boost()
            time.sleep(1)
            return self.do_boost()

        elif status == 'rate_limited':
            wait = 30
            print(f"{Colors.YELLOW}⚠️ Rate limited, tunggu {wait} detik{Colors.END}")
            self.countdown(wait, "⏳ Rate limit")
            return self.do_boost()

        else:
            print(f"{Colors.RED}❌ Boost gagal: {status}{Colors.END}")
            return False

    # ==================== RUN ====================
    def run(self):
        # ===== AUTO TASK DULU =====
        print(f"\n{Colors.GREEN}{Colors.BOLD}📋 AUTO TASK RUN{Colors.END}")
        self.run_tasks()

        print(f"\n{Colors.GREEN}{Colors.BOLD}🚀 START AUTO BOOST{Colors.END}")
        print(f"{Colors.CYAN}{'═' * 50}{Colors.END}")
        print(f"{Colors.GRAY}Press Ctrl+C to stop{Colors.END}\n")

        boost_count = 0
        task_check_counter = 0

        while True:
            try:
                # ===== CEK TASK SETIAP 20 BOOST =====
                if task_check_counter >= 20:
                    self.run_tasks()
                    task_check_counter = 0

                if self.do_boost():
                    boost_count += 1
                    task_check_counter += 1
                    print(f"{Colors.GRAY}➜ Total boost sesi ini: {boost_count}{Colors.END}")
                else:
                    print(f"{Colors.RED}❌ Boost gagal, tunggu 5 detik...{Colors.END}")
                    time.sleep(5)

                self.countdown(15, "⏳ Cooling down")

            except KeyboardInterrupt:
                print(f"\n\n{Colors.GREEN}👋 Dihentikan! Total boost: {boost_count}{Colors.END}")
                break
            except Exception as e:
                print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
                time.sleep(5)

# ============================================================
# MAIN
# ============================================================

def main():
    print_banner()
    try:
        bot = ATFMinerBot()
        if bot.is_logged_in:
            bot.run()
        else:
            print(f"{Colors.RED}❌ Tidak bisa lanjut karena login gagal{Colors.END}")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}🛑 Dihentikan user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()
