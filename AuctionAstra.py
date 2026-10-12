#!/usr/bin/env python3
"""
Astra Auction Bot - Auto Mining, Gift Box, Auction Monitor
ScriptMaker : ScriptyXSou
Channel : t.me/ScriptyXSouu
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

# Warna ANSI
PINK = '\033[95m'
RESET = '\033[0m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
BOLD = '\033[1m'
WHITE = '\033[97m'

class AstraBot:
    def __init__(self, init_data: str = ""):
        self.base_url = "https://auction-astra.biz"
        self.init_data = init_data
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.181 Mobile Safari/537.36 Telegram-Android/12.9.1',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': self.base_url,
            'Referer': self.base_url + '/',
            'X-Requested-With': 'org.telegram.messenger.web',
        })
        self.cookies = {}
        self.user_id = None
        self.coins_balance = 0.0
        self.usdt_balance = 0.0
        self.mining_cycles_left = 0
        self.boxes_left = 0
        self.running = False
        self.logs: List[str] = []  # history log (max 6 baris)
        self.fail_mining = 0
        self.fail_box = 0
        self.skip_mining = False
        self.skip_box = False
        self.total_claimed_coins = 0.0
        self.total_claimed_usdt = 0.0

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        url = self.base_url + endpoint
        try:
            resp = self.session.request(method, url, json=data, params=params)
            self.cookies.update(resp.cookies.get_dict())
            self.session.cookies.update(self.cookies)
            if resp.status_code == 200:
                if resp.headers.get('content-type', '').startswith('application/json'):
                    return resp.json()
                return {"raw": resp.text}
            return None
        except Exception:
            return None

    def auth(self) -> bool:
        if not self.init_data:
            self._add_log("InitData kosong!", "ERROR")
            return False
        payload = {
            "initData": self.init_data,
            "platform": "android",
            "referrer": "",
            "device_fingerprint": "",
            "timezone_offset_minutes": 420
        }
        result = self._request("POST", "/api/telegram/auth", data=payload)
        if result:
            self._add_log("Auth berhasil", "SUCCESS")
            return True
        self._add_log("Auth gagal", "ERROR")
        return False

    def update_state(self) -> bool:
        mining = self._request("GET", "/api/mining/state")
        if mining and "user" in mining:
            user = mining["user"]
            self.user_id = user.get("id")
            self.coins_balance = user.get("coins_balance", 0.0)
            self.usdt_balance = user.get("usdt_balance", 0.0)
            if "mining" in mining:
                self.mining_cycles_left = mining["mining"].get("cycles_left", 0)
        else:
            return False

        box = self._request("GET", "/api/gift-box/state")
        if box and "box" in box:
            self.boxes_left = box["box"].get("boxes_left", 0)
        else:
            return False
        return True

    def claim_mining_cycle(self) -> bool:
        result = self._request("POST", "/api/mining/claim", data={"action": "claim_cycle"})
        if result and "user" in result:
            user = result["user"]
            old_coins = self.coins_balance
            old_usdt = self.usdt_balance
            self.coins_balance = user.get("coins_balance", self.coins_balance)
            self.usdt_balance = user.get("usdt_balance", self.usdt_balance)
            gain_coins = self.coins_balance - old_coins
            gain_usdt = self.usdt_balance - old_usdt
            self.total_claimed_coins += gain_coins
            self.total_claimed_usdt += gain_usdt
            self._add_log(f"✔ MINING +{gain_coins:.5f} coins / +{gain_usdt:.5f} USDT", "SUCCESS")
            return True
        self._add_log("✘ MINING gagal", "ERROR")
        return False

    def open_gift_box(self) -> bool:
        result = self._request("POST", "/api/gift-box/open", data={})
        if result and "prize" in result:
            prize = result["prize"]
            amount = prize.get("amount", 0)
            title = prize.get("title", "prize")
            if "user" in result:
                user = result["user"]
                old_coins = self.coins_balance
                self.coins_balance = user.get("coins_balance", self.coins_balance)
                gain = self.coins_balance - old_coins
                self.total_claimed_coins += gain
            self._add_log(f"✔ BOX +{amount} {title}", "SUCCESS")
            return True
        self._add_log("✘ BOX gagal", "ERROR")
        return False

    def _add_log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "SUCCESS": GREEN,
            "ERROR": RED,
            "WARNING": YELLOW,
            "INFO": CYAN,
            "ACTION": PINK,
        }
        color = color_map.get(level, WHITE)
        entry = f"{color}[{timestamp}] {msg}{RESET}"
        self.logs.append(entry)
        if len(self.logs) > 6:
            self.logs.pop(0)

    def _render_box(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        width = 58
        border = "═" * width
        print(f"{PINK}╔{border}╗{RESET}")
        print(f"{PINK}║{RESET}  {BOLD}ASTRA BOT{RESET}  {PINK}⚡{RESET}  {YELLOW}(COIN){RESET}  {PINK}║{RESET}".ljust(width+3))
        print(f"{PINK}╠{border}╣{RESET}")
        bal_line = f"  Balance : {self.coins_balance:.5f} coins  |  {self.usdt_balance:.5f} USDT"
        print(f"{PINK}║{RESET} {bal_line:<{width-2}} {PINK}║{RESET}")
        print(f"{PINK}╠{border}╣{RESET}")
        mining_status = f"  ⛏️ MINING  left: {self.mining_cycles_left}"
        box_status = f"  📦 BOX  left: {self.boxes_left}"
        print(f"{PINK}║{RESET} {mining_status:<{width-2}} {PINK}║{RESET}")
        print(f"{PINK}║{RESET} {box_status:<{width-2}} {PINK}║{RESET}")
        if self.skip_mining:
            print(f"{PINK}║{RESET}  {RED}⚠ MINING skipped (2x fails){RESET}  {PINK}║{RESET}")
        if self.skip_box:
            print(f"{PINK}║{RESET}  {RED}⚠ BOX skipped (2x fails){RESET}  {PINK}║{RESET}")
        print(f"{PINK}╠{border}╣{RESET}")

        # Tampilkan log history (max 6 baris)
        log_lines = self.logs[-6:]
        for line in log_lines:
            # bersihkan ansi untuk perhitungan panjang (tapi kita tampilkan apa adanya)
            print(f"{PINK}║{RESET} {line:<{width-2}} {PINK}║{RESET}")

        # footer
        print(f"{PINK}╚{border}╝{RESET}")
        print(f"{PINK}  {YELLOW}Total gain: +{self.total_claimed_coins:.5f} coins | +{self.total_claimed_usdt:.5f} USDT{RESET}")

    def run_all(self):
        if not self.auth():
            self._add_log("Auth gagal, cek initData!", "ERROR")
            self._render_box()
            return

        if not self.update_state():
            self._add_log("Gagal ambil state awal", "ERROR")
            self._render_box()
            return

        self.running = True
        self.fail_mining = 0
        self.fail_box = 0
        self.skip_mining = False
        self.skip_box = False
        self.total_claimed_coins = 0.0
        self.total_claimed_usdt = 0.0
        self.logs.clear()

        self._add_log("Mulai eksekusi...", "ACTION")
        self._render_box()

        while self.running:
            self.update_state()
            self._render_box()

            # Mining
            if not self.skip_mining and self.mining_cycles_left > 0:
                success = self.claim_mining_cycle()
                if success:
                    self.fail_mining = 0
                    self.mining_cycles_left -= 1
                else:
                    self.fail_mining += 1
                    if self.fail_mining >= 2:
                        self.skip_mining = True
                        self._add_log("⛔ MINING di-skip (2x gagal)", "WARNING")
            elif self.mining_cycles_left == 0 and not self.skip_mining:
                self._add_log("Mining habis", "INFO")

            # Box
            if not self.skip_box and self.boxes_left > 0:
                success = self.open_gift_box()
                if success:
                    self.fail_box = 0
                    self.boxes_left -= 1
                else:
                    self.fail_box += 1
                    if self.fail_box >= 2:
                        self.skip_box = True
                        self._add_log("⛔ BOX di-skip (2x gagal)", "WARNING")
            elif self.boxes_left == 0 and not self.skip_box:
                self._add_log("Box habis", "INFO")

            self._render_box()

            # Stop jika semua habis dan skip flag aktif
            if self.mining_cycles_left == 0 and self.boxes_left == 0:
                self._add_log("✅ SEMUA SELESAI!", "SUCCESS")
                self.running = False
                self._render_box()
                break

            if self.skip_mining and self.skip_box:
                self._add_log("⛔ Kedua aksi di-skip, stop.", "WARNING")
                self.running = False
                self._render_box()
                break

            time.sleep(5)

    def set_init_data(self):
        print(f"{CYAN}Masukkan initData (dari Telegram WebApp):{RESET}")
        new_data = input("> ").strip()
        if new_data:
            self.init_data = new_data
            print(f"{GREEN}InitData diperbarui.{RESET}")
        else:
            print(f"{YELLOW}InitData tidak berubah.{RESET}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = r"""
   ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄ 
  ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
  ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌
  ▐░▌          ▐░▌       ▐░▌▐░▌       ▐░▌▐░▌          ▐░▌       ▐░▌
  ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌▐░▌       ▐░▌▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌
  ▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░▌       ▐░▌
   ▀▀▀▀▀▀▀▀▀█░▌▐░▌       ▐░▌▐░▌       ▐░▌ ▀▀▀▀▀▀▀▀▀█░▌▐░▌       ▐░▌
            ▐░▌▐░▌       ▐░▌▐░▌       ▐░▌          ▐░▌▐░▌       ▐░▌
   ▄▄▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌ ▄▄▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌
  ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌
   ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀ 
    """
    print(f"{PINK}{banner}{RESET}")
    print(f"{PINK}{BOLD}        Astra Auto Bot - All Actions Automator{RESET}")
    print(f"{PINK}{BOLD}        ScriptMaker : ScriptyXSou{RESET}")
    print(f"{PINK}{BOLD}        Channel : t.me/ScriptyXSouu{RESET}\n")

def main():
    bot = AstraBot()
    while True:
        clear_screen()
        print_banner()
        print(f"{CYAN}1. Start All Live Log{RESET}")
        print(f"{CYAN}2. Set InitData (wajib diisi sebelum start){RESET}")
        print(f"{CYAN}0. Exit{RESET}")
        choice = input(f"{YELLOW}Pilih menu: {RESET}").strip()

        if choice == "1":
            if not bot.init_data:
                print(f"{RED}InitData belum diset! Silakan pilih menu 2.{RESET}")
                input(f"{YELLOW}\nTekan Enter untuk kembali...{RESET}")
                continue
            bot.run_all()
            input(f"{YELLOW}\nTekan Enter untuk kembali ke menu...{RESET}")
        elif choice == "2":
            bot.set_init_data()
            input(f"{YELLOW}\nTekan Enter untuk kembali...{RESET}")
        elif choice == "0":
            print(f"{PINK}Terima kasih, sampai jumpa!{RESET}")
            break
        else:
            print(f"{RED}Pilihan tidak valid!{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{PINK}Program dihentikan oleh pengguna.{RESET}")
        sys.exit(0)
