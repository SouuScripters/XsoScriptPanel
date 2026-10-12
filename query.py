#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  🔥 DARK INITDATA GRABBER + AUTO POST TO API v2.0                ║
║  DEVELOPED BY MoneyMaker_w | FIXED BY DARK NIGHT                 ║
║  Fitur: Auto fallback URL • Kirim langsung ke API • Simpan sesi ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import urllib.parse
import json
import os
import sys
import sqlite3
import requests
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
SESSION_FILE = "telegram_session_initdata"
PHONE_FILE = "phone_number.txt"
TARGET_API = "https://paidadz.xyz/api/auth/telegram"  # Endpoint tujuan

# ==================== BANNER ====================
def show_banner():
    print(f"""
{GOLD}╔══════════════════════════════════════════════════════════════════════╗
║  {CYAN}🔥 MAKER INITDATA GRABBER + AUTO POST TO API v2.0{GOLD}             ║
║  {PINK}DEVELOPED BY ScriptyXSouu | FIXED BY ScriptyXSouu{GOLD}              ║
║  Auto fallback URL • Kirim langsung ke API • Simpan sesi              ║
╚══════════════════════════════════════════════════════════════════════╝{X}
""")

# ==================== FUNGSI PENDUKUNG ====================
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

def clear_session_if_locked():
    session_path = SESSION_FILE + ".session"
    if os.path.exists(session_path):
        try:
            conn = sqlite3.connect(session_path, timeout=0.1)
            conn.close()
            return False
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                try:
                    os.remove(session_path)
                    print(f"{Y}🗑️ Session file terkunci, dihapus.{X}")
                    return True
                except:
                    pass
    return False

def generate_fallback_urls(bot_name):
    """Generate daftar URL umum yang sering dipakai bot Telegram WebApp"""
    name = bot_name.replace('@', '').strip()
    return [
        f"https://{name}.vercel.app",
        f"https://{name}.t.me",
        f"https://t.me/{name}/app",
        f"https://{name}.xyz",
        f"https://{name}.web.app"
    ]

# ==================== AMBIL INITDATA ====================
async def get_webview_initdata(client, bot_username, custom_url=None):
    """Buka WebView bot dengan fallback otomatis"""
    try:
        bot = await client.get_input_entity(bot_username)
    except Exception as e:
        print(f"{R}❌ Gagal menemukan bot @{bot_username}: {e}{X}")
        return None

    target_url = custom_url

    # Jika tidak ada custom_url, coba deteksi otomatis
    if not target_url:
        print(f"{C}🔍 Mendeteksi URL WebView otomatis...{X}")
        # Coba menu button resmi
        try:
            full_user = await client(functions.users.GetFullUserRequest(id=bot))
            bot_info = full_user.full_user.bot_info
            if bot_info and bot_info.menu_button and hasattr(bot_info.menu_button, 'url'):
                target_url = bot_info.menu_button.url
                print(f"{G}✅ Auto-detected menu URL: {target_url}{X}")
        except Exception as e:
            print(f"{Y}⚠️ Gagal ambil menu button: {e}{X}")

        # Jika masih None, coba fallback URL
        if not target_url:
            fallbacks = generate_fallback_urls(bot_username)
            print(f"{C}🔄 Mencoba {len(fallbacks)} URL fallback...{X}")
            for idx, url in enumerate(fallbacks, 1):
                print(f"  Coba {idx}: {url}")
                try:
                    # Tes akses URL (bisa di-skip, kita coba langsung minta WebView)
                    test_result = await client(functions.messages.RequestWebViewRequest(
                        peer=bot,
                        bot=bot,
                        platform='android',
                        from_bot_menu=True,
                        url=url
                    ))
                    # Jika berhasil sampai sini, tandanya URL valid
                    target_url = url
                    print(f"  {G}✅ URL berhasil: {url}{X}")
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "URL" in err_msg or "invalid" in err_msg:
                        print(f"  {R}❌ Gagal: {err_msg[:80]}...{X}")
                    else:
                        print(f"  {Y}⚠️ Skip: {err_msg[:60]}...{X}")

        # Jika semua fallback gagal, minta manual
        if not target_url:
            print(f"{Y}⚠️ Semua URL otomatis gagal. Mohon input manual.{X}")
            manual_url = input(f"{G}🔗 Masukkan URL WebView (misal: https://paidadz.xyz): {X}").strip()
            if not manual_url:
                print(f"{R}❌ URL tidak boleh kosong.{X}")
                return None
            target_url = manual_url

    print(f"{C}📱 Meminta WebView ke URL: {target_url}{X}")
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
        print(f"{R}❌ Tidak ditemukan tgWebAppData di URL.{X}")
        print(f"{DIM}URL: {result.url}{X}")
        return None

# ==================== LOGIN TELEGRAM ====================
async def login_telegram():
    clear_session_if_locked()
    session_path = SESSION_FILE + ".session"

    if os.path.exists(session_path):
        try:
            client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                print(f"{G}✅ Session Telegram ditemukan! Login otomatis.{X}")
                return client, await client.get_me()
            else:
                print(f"{Y}⚠️ Session tidak valid, login ulang.{X}")
                os.remove(session_path)
        except Exception as e:
            print(f"{Y}⚠️ Session error: {e}{X}")
            if os.path.exists(session_path):
                try: os.remove(session_path)
                except: pass

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

# ==================== KIRIM KE API ====================
def send_init_to_api(init_data):
    """Kirim initData ke endpoint target dan simpan response"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 Chrome/150.0.7871.124 Mobile Safari/537.36 Telegram-Android/12.6.4",
        "Origin": "https://paidadz.xyz",
        "Referer": "https://paidadz.xyz/",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors"
    }
    payload = {"initData": init_data}

    print(f"\n{C}🚀 Mengirim ke API {TARGET_API}...{X}")
    try:
        resp = requests.post(TARGET_API, json=payload, headers=headers, timeout=20)
        print(f"{G}📦 Status Code: {resp.status_code}{X}")

        try:
            json_resp = resp.json()
            print(f"{G}📨 Response JSON:{X}")
            print(json.dumps(json_resp, indent=2, ensure_ascii=False))

            # Simpan response ke file
            with open("api_response.json", "w") as f:
                json.dump(json_resp, f, indent=2)
            print(f"{G}💾 Response disimpan ke api_response.json{X}")

            # Cek apakah ada session token/cookie
            if 'token' in json_resp:
                print(f"{G}🔑 Token ditemukan: {json_resp['token'][:30]}...{X}")
            elif 'session' in json_resp:
                print(f"{G}🔑 Session ditemukan: {json_resp['session'][:30]}...{X}")
        except:
            print(f"{Y}⚠️ Response bukan JSON valid:{X}\n{resp.text[:500]}")

        return resp
    except Exception as e:
        print(f"{R}❌ Gagal kirim ke API: {e}{X}")
        return None

# ==================== MAIN ====================
async def main():
    show_banner()
    print(f"{C}{'═' * 60}{X}")

    client, me = await login_telegram()
    if not client:
        print(f"{R}❌ Gagal login. Keluar.{X}")
        return
    print(f"{G}👤 Login sebagai: @{me.username if me.username else me.first_name}{X}")

    bot_name = input(f"\n{C}🤖 Masukkan username bot (tanpa @, contoh: Paid_Adzbot): {X}").strip()
    if not bot_name:
        print(f"{R}❌ Nama bot tidak boleh kosong!{X}")
        await client.disconnect()
        return
    if not bot_name.startswith('@'):
        bot_name = '@' + bot_name

    print(f"\n{C}🔍 Mengambil initData dari bot {bot_name}...{X}")
    init_data = await get_webview_initdata(client, bot_name)

    await client.disconnect()

    if not init_data:
        print(f"\n{R}❌ Gagal mendapatkan initData.{X}")
        return

    print(f"\n{GOLD}{'═' * 60}{X}")
    print(f"{G}🎯 INIT_DATA (tgWebAppData):{X}\n{init_data}")
    print(f"{GOLD}{'═' * 60}{X}")

    parsed = urllib.parse.parse_qs(init_data)
    query_id = parsed.get('query_id', [None])[0]
    if query_id:
        print(f"\n{C}📌 Query ID: {G}{query_id}{X}")

    # Simpan ke file lokal
    save_local = input(f"\n{G}💾 Simpan ke file init_data.txt? (y/n): {X}").strip().lower()
    if save_local == 'y':
        with open("init_data.txt", "w") as f:
            f.write(init_data)
        print(f"{G}✅ init_data disimpan ke init_data.txt{X}")

    # Kirim langsung ke API
    send_api = input(f"\n{G}🚀 Kirim langsung ke API [ Pilih No ] {TARGET_API}? (y/n): {X}").strip().lower()
    if send_api == 'y':
        send_init_to_api(init_data)

    print(f"\n{G}✅ Ty From MoneyMaker_w !{X}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Y}⚠️ Dihentikan oleh user.{X}")
        sys.exit(0)
