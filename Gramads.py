#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GramBux Auto Claim + Watch Ads FULL
- Fix: /api/tasks return list, bukan dict
- Auto task dengan skip-on-error
============================================================
👨‍💻 ScriptMaker : @JoshuaXSupport
📢 TG          : https://t.me/+f3QBLkR5D8k4YzNl
============================================================
"""

import requests
import json
import time
import urllib.parse
import os
import gzip
import zlib
from typing import Dict, Optional, List, Any, Union

# ============================================================
# WARNA ANSI
# ============================================================
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
MAGENTA = "\033[95m"

def pprint(msg, color=GREEN):
    print(f"{color}{msg}{RESET}")

def print_sep():
    print(f"{GRAY}{'='*60}{RESET}")

def print_header():
    print(f"{CYAN}{BOLD}")
    print("╔════════════════════════════════════════════════════╗")
    print("║          🚀 GRAM BUX AUTO CLAIM                    ║")
    print("╠════════════════════════════════════════════════════╣")
    print("║  👨‍💻 Maker : MoneyMaker_w                          ║")
    print("║  📢 TG    : https://t.me/+f3QBLkR5D8k4YzNl        ║")
    print("╚════════════════════════════════════════════════════╝")
    print(f"{RESET}")

def countdown(seconds, msg="⏳ Menunggu"):
    while seconds > 0:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            time_str = f"{minutes:02d}:{secs:02d}"
        print(f"\r{msg} {time_str}   ", end="", flush=True)
        time.sleep(1)
        seconds -= 1
    print(f"\r{msg} selesai!     ")

def progress_bar(current, target=10, width=20):
    filled = int((current / target) * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    pct = int((current / target) * 100)
    return f"[{bar}] {pct}%"

# ============================================================
# CLASS GRAMBUX
# ============================================================
class GramBux:
    BASE_URL = "https://grambux-backend.ankisaw1003.workers.dev"
    FRONTEND = "https://grambux-frontend.onrender.com"

    def __init__(self, init_data: str, debug=False):
        self.init_data = init_data
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
            "Accept": "*/*",
            "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Origin": self.FRONTEND,
            "Referer": self.FRONTEND + "/",
            "X-Requested-With": "org.telegram.messenger.web",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Sec-Ch-Ua": '"Not=A?Brand";v="99", "Android WebView";v="151", "Chromium";v="151"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "X-Telegram-Init-Data": init_data,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, endpoint: str, json_data: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Union[Dict, List, None]:
        url = self.BASE_URL + endpoint
        try:
            resp = self.session.request(method, url, json=json_data, params=params, timeout=30)

            if self.debug:
                print(f"\n🔍 DEBUG: {method} {endpoint}")
                print(f"   Status: {resp.status_code}")
                print(f"   Content-Encoding: {resp.headers.get('content-encoding')}")
                print(f"   First 100 bytes: {repr(resp.content[:100])}")

            if resp.status_code != 200:
                return {
                    "error": f"http_{resp.status_code}",
                    "status_code": resp.status_code,
                    "text": resp.text[:500]
                }

            try:
                return resp.json()
            except ValueError:
                raw = resp.content
                # Coba gzip
                if raw.startswith(b'\x1f\x8b'):
                    try:
                        return json.loads(gzip.decompress(raw).decode('utf-8'))
                    except Exception as e:
                        return {"error": "gzip_decompress_failed", "text": str(e)}
                # Coba zlib
                elif raw.startswith(b'\x78\x9c'):
                    try:
                        return json.loads(zlib.decompress(raw).decode('utf-8'))
                    except Exception as e:
                        return {"error": "zlib_decompress_failed", "text": str(e)}
                else:
                    return {"error": "invalid_json", "text": resp.text[:500]}
        except Exception as e:
            return {"error": "exception", "text": str(e)}

    def _has_error(self, result) -> bool:
        """Helper: cek error tanpa asumsi tipe data. List = sukses."""
        if result is None:
            return True
        if isinstance(result, list):
            return False
        if isinstance(result, dict):
            return "error" in result
        return True

    def _request_with_retry(self, method: str, endpoint: str,
                            json_data: Optional[Dict] = None,
                            params: Optional[Dict] = None,
                            max_retries: int = 3, retry_delay: int = 3):
        last = None
        for attempt in range(max_retries):
            result = self._request(method, endpoint, json_data, params)
            last = result
            # Kalau list → langsung return (sukses, gak ada error key)
            if isinstance(result, list):
                return result
            # Kalau dict & gak ada error → return
            if isinstance(result, dict) and "error" not in result:
                return result
            # Kalau error & masih ada retry → delay
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        return last

    def get_user(self, tg_id: str, username: str, telegram_username: str, referrer: str = "") -> Dict:
        params = {
            "tg_id": tg_id,
            "username": username,
            "telegram_username": telegram_username,
            "referrer": referrer,
            "_t": int(time.time() * 1000)
        }
        return self._request_with_retry("GET", "/api/user", params=params)

    def get_earn_status(self, tg_id: str) -> Dict:
        return self._request_with_retry("GET", "/api/earn/status", params={"tg_id": tg_id})

    def get_tasks(self):
        return self._request_with_retry("GET", "/api/tasks")

    def watch_ad(self, tg_id: str, block_id: int) -> Dict:
        return self._request("POST", "/api/watch-ad/watch", json_data={"tg_id": tg_id, "block_id": block_id})

    def claim_ad(self, tg_id: str, block_id: int) -> Dict:
        return self._request("POST", "/api/watch-ad/claim", json_data={"tg_id": tg_id, "block_id": block_id})

    def initiate_task(self, tg_id: str, task_id: str) -> Dict:
        return self._request("POST", "/api/task/initiate", json_data={"tg_id": tg_id, "task_id": task_id})

    def claim_task(self, tg_id: str, task_id: str) -> Dict:
        return self._request("POST", "/api/task/claim", json_data={"tg_id": tg_id, "task_id": task_id})

    def claim_tap(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/tap-to-earn/claim", json_data={"tg_id": tg_id})

    def claim_mystery_box(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/mystery-box/claim", json_data={"tg_id": tg_id})

    def start_miner(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/miner/start", json_data={"tg_id": tg_id})

    def claim_miner(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/miner/claim", json_data={"tg_id": tg_id})

    def start_vault(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/vault/start", json_data={"tg_id": tg_id})

    def claim_vault(self, tg_id: str) -> Dict:
        return self._request("POST", "/api/vault/claim", json_data={"tg_id": tg_id})

# ============================================================
# FUNGSI BANTU
# ============================================================
def parse_init_data(init_data: str) -> Dict:
    parsed = urllib.parse.parse_qs(init_data)
    user_str = parsed.get("user", [""])[0]
    try:
        user_obj = json.loads(user_str)
    except Exception:
        user_obj = {}
    return {
        "tg_id": str(user_obj.get("id", "")),
        "username": user_obj.get("username", ""),
        "full_name": f"{user_obj.get('first_name', '')} {user_obj.get('last_name', '')}".strip()
    }

def check_block_status(bot, tg_id, username, block_id):
    try:
        user_data = bot.get_user(tg_id, username, f"@{username}" if username else "")
        if not isinstance(user_data, dict) or user_data.get("error"):
            return 0, False
        watch_progress = user_data.get("watchProgress", {})
        block_data = watch_progress.get(str(block_id), {})
        return block_data.get("watched_count", 0), block_data.get("claimed_today", False)
    except Exception:
        return 0, False

def watch_block(bot, tg_id, username, block_id, retry_delay=3600):
    print(f"\n{YELLOW}📺 BLOCK {block_id}{RESET}")
    watched_count, claimed_today = check_block_status(bot, tg_id, username, block_id)

    if watched_count >= 10 and claimed_today:
        print(f"   ✅ Sudah selesai dan di-claim")
        return {"status": "already_claimed", "watched": watched_count, "claimed": True, "earned": 0.0022}

    attempt = 0
    while True:
        attempt += 1
        watch_res = bot.watch_ad(tg_id, block_id)

        # Fix: cek tipe sebelum .get()
        if not isinstance(watch_res, dict):
            print(f"   ❌ Response aneh, retry...")
            time.sleep(10)
            continue

        if watch_res.get("error"):
            if "block" in str(watch_res).lower() or "400" in str(watch_res):
                print(f"   ⚠️ Block terkunci, jeda 1 jam...")
                countdown(retry_delay, "   ⏳ Jeda")
                watched_count, claimed_today = check_block_status(bot, tg_id, username, block_id)
                if watched_count >= 10 and claimed_today:
                    return {"status": "already_claimed", "watched": watched_count, "claimed": True, "earned": 0.0022}
                continue
            else:
                print(f"   ❌ Error: {watch_res.get('text', '')}")
                time.sleep(10)
                continue

        watched_count = watch_res.get("watched_count", 0)
        bar = progress_bar(watched_count, 10)
        print(f"\r   🔄 Watch {attempt}: {bar}  ({watched_count}/10)", end="", flush=True)

        if watched_count >= 10:
            print()
            break
        time.sleep(15)

    if watched_count >= 10 and not claimed_today:
        print("   🎯 Target tercapai! Claiming...")
        claim_res = bot.claim_ad(tg_id, block_id)
        if not isinstance(claim_res, dict) or claim_res.get("error"):
            txt = claim_res.get("text", "") if isinstance(claim_res, dict) else "invalid response"
            print(f"   ❌ Gagal claim: {txt}")
            return {"status": "claim_failed", "watched": watched_count, "claimed": False, "earned": 0}
        earned = claim_res.get("newStars", 0)
        print(f"   ✅ +{earned:.5f} TON")
        return {"status": "success", "watched": watched_count, "claimed": True, "earned": earned}
    elif watched_count >= 10 and claimed_today:
        return {"status": "already_claimed", "watched": watched_count, "claimed": True, "earned": 0.0022}
    else:
        return {"status": "failed", "watched": watched_count, "claimed": False, "earned": 0}

def claim_bot_tasks(bot, tg_id, completions):
    print(f"\n{CYAN}📋 BOT TASKS{RESET}")
    tasks_res = bot.get_tasks()

    # Fix utama: /api/tasks return list
    if tasks_res is None:
        print(f"   ❌ Gagal ambil tasks (None)")
        return 0, 0
    if isinstance(tasks_res, dict) and tasks_res.get("error"):
        print(f"   ❌ Gagal ambil tasks: {tasks_res.get('text', tasks_res.get('error'))}")
        return 0, 0
    if not isinstance(tasks_res, list):
        # kemungkinan dibungkus {"tasks": [...]}
        if isinstance(tasks_res, dict) and isinstance(tasks_res.get("tasks"), list):
            tasks_res = tasks_res["tasks"]
        else:
            print(f"   ❌ Format tasks tidak dikenal")
            return 0, 0

    # Filter task type=bot, belum selesai, bukan daily
    bot_tasks = []
    for t in tasks_res:
        if not isinstance(t, dict):
            continue
        t_id = t.get('id')
        t_type = t.get('type')
        if t_type == 'bot' and t_id not in completions and t_id != 'daily1':
            bot_tasks.append(t)

    if not bot_tasks:
        print("   ✅ Semua bot tasks sudah diklaim / tidak ada")
        return 0, 0

    print(f"   🔍 Ditemukan {len(bot_tasks)} task")
    total_earned = 0
    claimed_count = 0

    for idx, task in enumerate(bot_tasks, 1):
        task_id = task.get('id')
        title = str(task.get('title', 'No title'))[:30]
        reward = task.get('reward_ton', 0) or 0
        print(f"\n   [{idx}/{len(bot_tasks)}] {title} (reward: {reward:.5f} TON)")

        init_res = bot.initiate_task(tg_id, task_id)
        if not isinstance(init_res, dict):
            print("      ⏭ Skip (response invalid)")
            continue
        if init_res.get("error"):
            if "already completed" in str(init_res).lower():
                print("      ⏳ Sudah diklaim")
                continue
            print(f"      ⏭ Skip: {init_res.get('text', init_res.get('error'))}")
            continue

        if init_res.get('success'):
            time.sleep(5)
            claim_res = bot.claim_task(tg_id, task_id)
            if isinstance(claim_res, dict) and claim_res.get('success'):
                earned = claim_res.get('starsAwarded', 0)
                print(f"      ✅ +{earned:.5f} TON")
                total_earned += earned
                claimed_count += 1
            else:
                print(f"      ⏭ Gagal claim, skip")
        time.sleep(2)

    return claimed_count, total_earned

def claim_tap(bot, tg_id):
    print(f"\n{CYAN}🖐️ TAP TO EARN{RESET}")
    status = bot.get_earn_status(tg_id)
    if not isinstance(status, dict) or status.get("error"):
        print(f"   ❌ Gagal ambil status")
        return 0, 0

    tap_info = status.get("tap_to_earn", {})
    remaining = tap_info.get("remaining_taps", 0)
    cooldown = tap_info.get("cooldown_remaining_sec", 0)

    if remaining == 0:
        print("   ✅ Tap habis hari ini")
        return 0, 0
    if cooldown > 60:
        print(f"   ⏳ Cooldown {cooldown//60}m {cooldown%60}s - SKIP")
        return 0, 0

    print(f"   🔍 Tersisa {remaining} tap")
    claimed = 0
    earned = 0
    for i in range(remaining):
        if cooldown > 60:
            break
        if cooldown > 0:
            time.sleep(cooldown + 1)
            cooldown = 0
        res = bot.claim_tap(tg_id)
        if not isinstance(res, dict) or res.get("error"):
            print(f"   ❌ Gagal tap")
            break
        if res.get("success"):
            earned += res.get("earned_ton", 0)
            claimed += 1
            print(f"   💰 Tap #{i+1}: +{res.get('earned_ton', 0):.5f} TON")
            cooldown = res.get("cooldown_sec", 0)
        time.sleep(1)

    return claimed, earned

def claim_mystery_box(bot, tg_id):
    print(f"\n{CYAN}📦 MYSTERY BOX{RESET}")
    status = bot.get_earn_status(tg_id)
    if not isinstance(status, dict) or status.get("error"):
        print("   ❌ Gagal ambil status")
        return 0
    mystery = status.get("mystery_box", {})
    if not mystery.get("available"):
        print("   ℹ️ Belum tersedia")
        return 0
    print("   🎁 Claiming...")
    res = bot.claim_mystery_box(tg_id)
    if isinstance(res, dict) and res.get("success"):
        earned = res.get("earned_ton", 0)
        print(f"   ✅ +{earned:.5f} TON")
        return earned
    return 0

def handle_miner(bot, tg_id):
    print(f"\n{CYAN}⛏️ MINER{RESET}")
    status = bot.get_earn_status(tg_id)
    if not isinstance(status, dict) or status.get("error"):
        print("   ❌ Gagal ambil status")
        return 0
    miner = status.get("miner", {})
    if miner.get("ready"):
        print("   🎯 Claiming...")
        res = bot.claim_miner(tg_id)
        if isinstance(res, dict) and res.get("success"):
            earned = res.get("earned_ton", 0)
            print(f"   ✅ +{earned:.5f} TON")
            return earned
    elif miner.get("can_start") and not miner.get("is_running"):
        print("   🔄 Starting...")
        res = bot.start_miner(tg_id)
        if isinstance(res, dict) and res.get("success"):
            print("   ✅ Miner started")
    else:
        print("   ⏳ Miner running")
    return 0

def handle_vault(bot, tg_id):
    print(f"\n{CYAN}🏦 VAULT{RESET}")
    status = bot.get_earn_status(tg_id)
    if not isinstance(status, dict) or status.get("error"):
        print("   ❌ Gagal ambil status")
        return 0
    vault = status.get("vault", {})
    if vault.get("ready"):
        print("   🎯 Claiming...")
        res = bot.claim_vault(tg_id)
        if isinstance(res, dict) and res.get("success"):
            earned = res.get("earned_ton", 0)
            print(f"   ✅ +{earned:.5f} TON")
            return earned
    elif vault.get("can_start") and not vault.get("is_running"):
        print("   🔄 Starting...")
        res = bot.start_vault(tg_id)
        if isinstance(res, dict) and res.get("success"):
            print("   ✅ Vault started")
    else:
        print("   ⏳ Vault running")
    return 0

# ============================================================
# MAIN
# ============================================================
def main():
    print_header()
    print()

    print(f"{YELLOW}🔐 Masukkan X-Telegram-Init-Data:{RESET}")
    print("   (Ambil dari Mini App Telegram)")
    init_data = input("👉 ").strip()
    if not init_data:
        print(f"{RED}❌ Init data kosong, keluar.{RESET}")
        return

    user_info = parse_init_data(init_data)
    tg_id = user_info.get("tg_id")
    username = user_info.get("username")
    full_name = user_info.get("full_name") or username

    if not tg_id:
        print(f"{RED}❌ Gagal parse tg_id, init_data tidak valid{RESET}")
        return

    bot = GramBux(init_data, debug=False)

    print(f"\n{CYAN}👤 USER INFORMATION{RESET}")
    print("   ⏳ Menghubungi server...")

    user_data = bot.get_user(tg_id, username, f"@{username}" if username else "")
    if not isinstance(user_data, dict) or user_data.get("error"):
        txt = user_data.get('text', user_data.get('error', '?')) if isinstance(user_data, dict) else "invalid response"
        print(f"   {RED}❌ Gagal login: {txt}{RESET}")
        print(f"\n{YELLOW}💡 Saran: init_data mungkin expired. Buka ulang Mini App.{RESET}")
        return

    user = user_data.get("user", {})
    balance = user.get("ton_balance", 0)
    completions = user_data.get("completions", {})
    watch_progress = user_data.get("watchProgress", {})

    print(f"   {GREEN}✅ Login sebagai : {full_name}{RESET}")
    print(f"   🆔 User ID      : {tg_id}")
    print(f"   💰 Balance      : {balance:.5f} TON")
    print(f"   📋 Tasks done   : {len(completions)}")
    total_watch = sum(b.get("watched_count", 0) for b in watch_progress.values() if isinstance(b, dict))
    print(f"   👁️ Total watch  : {total_watch}")

    print_sep()
    total_earned = 0
    total_claim = 0

    # WATCH ADS
    print(f"\n{CYAN}▶️ WATCH ADS BLOCK 1-5{RESET}")
    print("   📊 Target: 10 ads x 5 block = 50 ads")
    for block_id in range(1, 6):
        result = watch_block(bot, tg_id, username, block_id)
        if result["status"] in ["success", "already_claimed"]:
            total_earned += result.get("earned", 0)
            total_claim += 1
        if block_id < 5:
            countdown(7, f"   ⏳ Jeda sebelum block {block_id+1}")

    # TAP
    tap_claimed, tap_earned = claim_tap(bot, tg_id)
    total_earned += tap_earned
    total_claim += tap_claimed

    # BOT TASKS
    task_claimed, task_earned = claim_bot_tasks(bot, tg_id, completions)
    total_earned += task_earned
    total_claim += task_claimed

    # MYSTERY BOX
    total_earned += claim_mystery_box(bot, tg_id)

    # MINER
    total_earned += handle_miner(bot, tg_id)

    # VAULT
    total_earned += handle_vault(bot, tg_id)

    # FINAL
    print_sep()
    print(f"{CYAN}📊 RINGKASAN AKHIR{RESET}")
    print(f"   💰 Total Earned : {total_earned:.5f} TON")
    print(f"   📋 Total Claim  : {total_claim}")

    # Refresh balance
    user_data = bot.get_user(tg_id, username, f"@{username}" if username else "")
    if isinstance(user_data, dict) and not user_data.get("error"):
        new_balance = user_data.get("user", {}).get("ton_balance", 0)
        print(f"   💎 Balance Akhir: {new_balance:.5f} TON")

    print_sep()
    print(f"{GREEN}✅ Selesai! 🎉{RESET}")
    print(f"{CYAN}📢 TG: https://t.me/+f3QBLkR5D8k4YzNl{RESET}")
    print_sep()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}⚠️ Dibatalkan oleh user.{RESET}")
    except Exception as e:
        print(f"{RED}❌ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
