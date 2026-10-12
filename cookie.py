#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  🔑 AUTO GET PHPSESSID FROM BOT TELEGRAM v1.3 (FIX SESSION)║
║  DEVELOPED BY MoneyMaker_w                                 ║
║  Ambil PHPSESSID dari bot Telegram via WebView            ║
║  📞 Nomor HP tersimpan • Session otomatis (skip OTP)     ║
║  🔓 Auto-clear session jika database terkunci             ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import urllib.parse
import requests
import json
import os
import sys
import time
import sqlite3
from telethon import TelegramClient, functions, types

# ==================== WARNA ====================
R, G, Y, B, M, C, W, X = '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[97m', '\033[0m'
GOLD = '\033[38;5;220m'
CYAN = '\033[1;96m'
PINK = '\033[38;5;206m'
DIM = '\033[2;37m'

# ==================== KONFIGURASI ====================
API_ID = 21578873
API_HASH = "b7562db4c393baff2f415d14a14d1f76"
DEFAULT_BOT = "PepeFlowOfficialBot"
SESSION_FILE = "telegram_session_phpsessid"
BASE_URL = "https://pepeflow.com"
PHONE_FILE = "phone_number.txt"

# ==================== BANNER ====================
def show_banner():
    print(f"""
{GOLD}╔══════════════════════════════════════════════════════════════╗
║  {CYAN}🔑 AUTO GET PHPSESSID FROM BOT TELEGRAM v1.3{GOLD}           ║
║  {PINK}DEVELOPED BY ScriptyXSouu{GOLD}                              ║
║  Ambil PHPSESSID dari bot Telegram via WebView            ║
║  📞 Nomor HP tersimpan • Session otomatis (skip OTP)     ║
║  🔓 Auto-clear session jika database terkunci             ║
╚══════════════════════════════════════════════════════════════╝{X}
""")

# ==================== FUNGSI ====================
def save_phone(phone):
    try:
        with open(PHONE_FILE, 'w') as f:
            f.write(phone.strip())
        return True
    except:
        return False

def load_phone():
    try:
        if os.path.exists(PHONE_FILE):
            with open(PHONE_FILE, 'r') as f:
                return f.read().strip()
    except:
        pass
    return None

def is_session_valid():
    """Cek apakah session file ada dan valid (bisa dibuka)"""
    if not os.path.exists(SESSION_FILE + ".session"):
        return False
    try:
        # Coba buka database
        conn = sqlite3.connect(SESSION_FILE + ".session", timeout=0.1)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sessions")
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except:
        return False

def clear_session():
    """Hapus session file"""
    try:
        if os.path.exists(SESSION_FILE + ".session"):
            os.remove(SESSION_FILE + ".session")
            print(f"{Y}🗑️ Session file dihapus.{X}")
        return True
    except:
        return False

async def get_webview_initdata(client, bot_username):
    try:
        bot = await client.get_input_entity(bot_username)
    except Exception as e:
        print(f"{R}❌ Gagal menemukan bot @{bot_username}: {e}{X}")
        return None

    try:
        full_user = await client(functions.users.GetFullUserRequest(id=bot))
        bot_info = full_user.full_user.bot_info
        target_url = "https://pepeflow.com/miniapp.php"
        if bot_info and bot_info.menu_button and hasattr(bot_info.menu_button, 'url'):
            target_url = bot_info.menu_button.url
            print(f"{G}🔗 Auto-detected URL: {target_url}{X}")
        else:
            print(f"{Y}⚠️ Tidak dapat mendeteksi URL menu, menggunakan default: {target_url}{X}")
    except Exception as e:
        print(f"{Y}⚠️ Gagal mengambil info bot: {e}, menggunakan URL default{X}")
        target_url = "https://pepeflow.com/miniapp.php"

    print(f"{C}📱 Meminta WebView untuk @{bot_username}...{X}")
    try:
        result = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform='android',
            from_bot_menu=True,
            url=target_url
        ))
    except Exception as e:
        print(f"{R}❌ Gagal meminta WebView: {e}{X}")
        return None

    parsed = urllib.parse.urlparse(result.url)
    init_data = None

    if parsed.fragment:
        params = urllib.parse.parse_qs(parsed.fragment)
        init_data = params.get('tgWebAppData', [None])[0]
    if not init_data and parsed.query:
        params = urllib.parse.parse_qs(parsed.query)
        init_data = params.get('tgWebAppData', [None])[0]

    if init_data:
        print(f"{G}✅ initData berhasil didapat.{X}")
        return init_data
    else:
        print(f"{R}❌ Tidak ditemukan tgWebAppData di URL WebView.{X}")
        return None

async def login_telegram():
    """Login ke Telegram dengan session tersimpan"""
    # Cek session valid
    if is_session_valid():
        print(f"{G}✅ Session Telegram ditemukan! Login otomatis...{X}")
        try:
            client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                print(f"{G}✅ Session valid! Login sukses.{X}")
                return client, await client.get_me()
            else:
                print(f"{Y}⚠️ Session tidak valid, login ulang.{X}")
                clear_session()
        except Exception as e:
            print(f"{Y}⚠️ Session error: {e}, login ulang.{X}")
            clear_session()

    # Jika session tidak ada, login manual
    print(f"\n{C}📱 Login ke Telegram diperlukan.{X}")
    saved_phone = load_phone()
    if saved_phone:
        print(f"{G}📞 Menggunakan nomor tersimpan: {saved_phone}{X}")
        phone = saved_phone
    else:
        phone = input(f"{G}📞 Masukkan nomor HP (dengan kode negara, +628...): {X}").strip()
        if not phone:
            print(f"{R}❌ Nomor HP tidak boleh kosong.{X}")
            return None, None

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()

    try:
        await client.send_code_request(phone)
        code = input(f"{G}🔑 Masukkan kode OTP yang dikirim ke Telegram: {X}").strip()
        if not code:
            print(f"{R}❌ Kode OTP tidak boleh kosong.{X}")
            return None, None
        await client.sign_in(phone, code)
        save_phone(phone)
        print(f"{G}✅ Login sukses! Session tersimpan.{X}")
        return client, await client.get_me()
    except Exception as e:
        print(f"{R}❌ Login gagal: {e}{X}")
        return None, None

async def get_phpsessid_from_bot(client, bot_username):
    init_data = await get_webview_initdata(client, bot_username)
    if not init_data:
        return None

    print(f"\n{C}🔐 Mengirim initData ke /actions/tg_auth.php...{X}")
    session = requests.Session()
    
    parsed_init = urllib.parse.parse_qs(init_data)
    user_str = parsed_init.get('user', [None])[0]
    telegram_id = None
    telegram_username = None
    if user_str:
        try:
            user_json = json.loads(urllib.parse.unquote(user_str))
            telegram_id = str(user_json.get('id', ''))
            telegram_username = user_json.get('username', '')
        except:
            pass

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.47 Mobile Safari/537.36 Telegram-Android/12.6.4 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/miniapp.php",
        "X-Requested-With": "org.telegram.messenger.web",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Accept": "*/*",
        "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    files = {
        "init_data": (None, init_data),
        "telegram_id": (None, telegram_id or "0"),
        "telegram_username": (None, telegram_username or ""),
        "auto_login": (None, "1"),
    }

    try:
        resp = session.post(f"{BASE_URL}/actions/tg_auth.php", headers=headers, files=files)
        if resp.status_code == 200:
            for cookie in session.cookies:
                if cookie.name == "PHPSESSID":
                    print(f"{G}✅ PHPSESSID ditemukan dari /actions/tg_auth.php{X}")
                    return cookie.value
            if 'Set-Cookie' in resp.headers:
                for cookie in resp.headers.get('Set-Cookie', '').split(';'):
                    if 'PHPSESSID' in cookie:
                        phpsessid = cookie.split('=')[1].strip()
                        print(f"{G}✅ PHPSESSID ditemukan dari Set-Cookie header{X}")
                        return phpsessid
            print(f"{Y}⚠️ Response sukses tapi tidak ada PHPSESSID di cookie.{X}")
            return None
        else:
            print(f"{R}❌ Request ke /actions/tg_auth.php gagal: {resp.status_code}{X}")
            return None
    except Exception as e:
        print(f"{R}❌ Error: {e}{X}")
        return None

async def main():
    show_banner()
    print(f"{C}{'═' * 55}{X}")

    # Cek session di awal
    if is_session_valid():
        print(f"{G}📁 Session Telegram ditemukan! Akan login otomatis.{X}")
    else:
        print(f"{Y}⚠️ Session Telegram tidak ditemukan. Perlu login ulang.{X}")

    client, me = await login_telegram()
    if not client:
        print(f"{R}❌ Gagal login. Keluar.{X}")
        return
    print(f"{G}👤 Login sebagai: @{me.username if me.username else me.first_name}{X}")

    bot_name = input(f"\n{C}🤖 Masukkan username bot (default: {DEFAULT_BOT}): {X}").strip()
    if not bot_name:
        bot_name = DEFAULT_BOT
    if not bot_name.startswith('@'):
        bot_name = '@' + bot_name

    print(f"\n{C}🔍 Mencari PHPSESSID dari bot {bot_name}...{X}")
    phpsessid = await get_phpsessid_from_bot(client, bot_name)

    await client.disconnect()

    if phpsessid:
        print(f"\n{GOLD}{'═' * 55}{X}")
        print(f"{G}🎯 PHPSESSID: {phpsessid}{X}")
        print(f"{GOLD}{'═' * 55}{X}")
        print(f"\n{C}📌 Simpan nilai ini untuk digunakan di script PepeFlow.{X}")
        save = input(f"\n{G}💾 Simpan ke file config PepeFlow? (y/n): {X}").strip().lower()
        if save == 'y':
            config_file = "pepeflow_config.json"
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                except:
                    config = {}
            else:
                config = {}
            config['phpsessid'] = phpsessid
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"{G}✅ PHPSESSID disimpan ke {config_file}{X}")
    else:
        print(f"\n{R}❌ Gagal mendapatkan PHPSESSID.{X}")
        print(f"{Y}💡 Coba manual: buka bot di Telegram, buka WebView, lalu ambil cookie dari browser.{X}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Y}⚠️ Dihentikan oleh user.{X}")
        sys.exit(0)
