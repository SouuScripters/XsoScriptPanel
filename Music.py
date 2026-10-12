import os
import sys
import time
import json
import glob
import asyncio
import urllib.parse
import random
import requests
import base64
import shutil
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import StartBotRequest, RequestWebViewRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantRequest
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError, AuthKeyInvalidError

# ====== Warna ======
C = "\033[1;36m"
G = "\033[1;32m"
Y = "\033[1;33m"
R = "\033[1;31m"
M = "\033[1;35m"
W = "\033[1;37m"
RES = "\033[0m"
PURPLE = "\033[38;5;93m"
RESET = "\033[0m"

# ====== Konfigurasi ======
API_ID = 28752231
API_HASH = "ec1c1f2c30e2f1855c3edee7e348480b"
BOT_USERNAME = "MusicMiningMB_Bot"
TOKEN_FILE = "all_token.json"
DEFAULT_REF = "MB000LPP"
CACHE_DIR = "__pycache__"

# ====== Teks ======
TEXTS = {
    "no_sess": "❌ No sess*.session files found!",
    "no_sess_ask": "No session found. Do you want to create a new session? (y/n): ",
    "creating_session": "Creating new session...",
    "enter_phone": "Enter your phone number with country code (e.g., +628123456789): ",
    "enter_code": "Enter the verification code sent to your Telegram: ",
    "enter_password": "Enter your 2FA password (if any, or press Enter): ",
    "session_created": "✅ Session created successfully: {}",
    "session_create_fail": "❌ Failed to create session: {}",
    "found_sess": "📌 Found {} session file.",
    "exec_acc": "EXECUTING ACCOUNT",
    "target_sess": "TARGET SESSION:",
    "auth_exp": "Session unauthorized or expired!",
    "start_bot": "Executing /start command to @{}...",
    "fetch_init": "Fetching initData from MusicMB WebApp...",
    "req_cap": "Requesting CAPTCHA Challenge...",
    "cap_id_fail": "Failed to retrieve CAPTCHA Task ID!",
    "cap_poll": "Polling CAPTCHA Status... (Wait 5s)",
    "cap_ok": "Captcha Solved! Token:",
    "cap_err": "Captcha Error:",
    "auth_srv": "Authenticating with Server...",
    "auth_ok": "Authentication Success! Token saved.",
    "auth_fail": "Auth Failed! Status:",
    "tok_found": "Token found in database, attempting to access Dashboard...",
    "tok_not": "Token not found, initiating Auth process...",
    "tok_exp": "Token Expired / Unauthorized! Re-authenticating...",
    "dash_fail": "Failed to access Dashboard! HTTP",
    "user_id": "ID/User :",
    "balance": "Balance :",
    "wall_not": "Wallet Address is not set!",
    "input_wall": "Please enter your TON Wallet: ",
    "raw_addr": "Your Raw address :",
    "bind_ok": "Bind Wallet Success!",
    "bind_fail": "Failed to bind wallet! HTTP",
    "inv_wall": "Invalid wallet format:",
    "wall_link": "Wallet Address is already linked.",
    "watch_ads": "Watching ads for boost...",
    "ad_giga": "GigaPub: watching ad ({}/{})",
    "ad_giga_ok": "GigaPub ad watched successfully",
    "ad_giga_done": "GigaPub ads completed ({}/{} watched)",
    "ad_giga_fail": "GigaPub ad failed: {}",
    "ad_giga_skip": "GigaPub ad already completed or active",
    "ad_giga_error": "GigaPub ad error: {}",
    "ad_libtl": "Libtl: watching ad ({}/{})",
    "ad_libtl_ok": "Libtl ad watched successfully",
    "ad_libtl_done": "Libtl ads completed ({}/{} watched)",
    "ad_libtl_fail": "Libtl ad failed: {}",
    "ad_libtl_skip": "Libtl ad already completed or active",
    "ad_libtl_error": "Libtl ad error: {}",
    "act_mine": "Activating Mining Engine...",
    "mine_ok": "Mining Start : Success",
    "start_at": "Started at :",
    "claim_in": "Claim In   :",
    "mine_fail_act": "Failed to activate mining (might already be active).",
    "mine_alr": "Mining is already active.",
    "mine_fail": "Failed to start mining! HTTP",
    "all_done": "Session Executed Successfully.",
    "term": "Automation session forcefully terminated.",
    "cache_cleared": "Cache script dibersihkan",
    "config_saved": "Konfigurasi tersimpan di folder ini",
    "press_enter": "Press Enter to continue..."
}

t = TEXTS

def clr():
    os.system('cls' if os.name == 'nt' else 'clear')

def clear_cache():
    """Bersihkan cache Python"""
    if os.path.exists(CACHE_DIR):
        try:
            shutil.rmtree(CACHE_DIR)
            print(f" \033[38;5;51m│\033[0m \033[1;38;5;46m[✓] {t['cache_cleared']}\033[0m")
        except:
            pass
    # Hapus file .pyc
    for f in glob.glob("*.pyc"):
        try:
            os.remove(f)
        except:
            pass

def get_width():
    cols = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    return max(50, min(cols, 100))

def banner():
    clr()
    clear_cache()
    w = get_width()
    line = "=" * w
    print(PURPLE + line + RESET)
    print(PURPLE + "||" + " " * (w - 4) + "||" + RESET)
    title = "🎵 MUSIC AUTO BOT 🎵"
    pad_left = (w - 4 - len(title)) // 2
    pad_right = w - 4 - len(title) - pad_left
    print(PURPLE + "||" + " " * pad_left + title + " " * pad_right + "||" + RESET)
    print(PURPLE + "||" + " " * (w - 4) + "||" + RESET)
    total_inner = w - 4
    maker = "👨‍💻 ScriptMaker : MoneyMaker_w"
    bot_link = "🎶 BOT : https://t.me/MusicMiningMB_Bot?start=MB000LPP"
    print(PURPLE + "||" + " " + maker + " " * (total_inner - len(maker) - 1) + "||" + RESET)
    print(PURPLE + "||" + " " + bot_link + " " * (total_inner - len(bot_link) - 1) + "||" + RESET)
    tg = "📢 TG          : https://t.me/ScriptyXSouu"
    print(PURPLE + "||" + " " + tg + " " * (total_inner - len(tg) - 1) + "||" + RESET)
    print(PURPLE + "||" + " " * (w - 4) + "||" + RESET)
    print(PURPLE + line + RESET)
    print(f" \033[38;5;51m│\033[0m \033[1;38;5;46m[✓] {t['config_saved']}\033[0m")
    print(f" \033[38;5;51m│\033[0m")

def log(acc_num, icon, text, color):
    print(f" \033[38;5;51m│\033[0m \033[38;5;220m[{acc_num:04d}]\033[0m {color}{icon} {W}{text}{RES}")

async def animate(acc_num, text):
    frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    for i in range(12):
        f = frames[i % len(frames)]
        print(f"\r \033[38;5;51m│\033[0m \033[38;5;220m[{acc_num:04d}]\033[0m \033[38;5;208m[{f}]\033[0m \033[1;38;5;51m{text}\033[0m\033[K", end="", flush=True)
        await asyncio.sleep(0.08)
    print("\r\033[K", end="")

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return {}
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            tokens = {}
            for item in data:
                tokens.update(item)
            return tokens
    except:
        return {}

def save_token(sess_name, token):
    tokens = load_tokens()
    tokens[sess_name] = token
    new_data = [{k: v} for k, v in tokens.items()]
    with open(TOKEN_FILE, 'w') as f:
        json.dump(new_data, f, indent=4)

def format_date(iso_str):
    if not iso_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_str

def convert_ton_address(address):
    pad = "=" * (-len(address) % 4)
    data = base64.urlsafe_b64decode(address + pad)
    workchain = data[1]
    if workchain == 255:
        workchain = -1
    hash_part = data[2:34]
    return f"{workchain}:{hash_part.hex()}"

def parse_channel_from_url(url):
    if 't.me/' in url:
        part = url.split('t.me/')[1]
        return part.split('/')[0].split('?')[0]
    return None

async def claim_task(acc_num, headers, task_id, reward):
    try:
        res = requests.post(f"https://api.musicmb.site/api/tasks/{task_id}/complete", headers=headers, timeout=30)
        if res.status_code == 200:
            return True
        else:
            return False
    except:
        return False

async def process_captcha(acc_num):
    log(acc_num, "🛡️", t["req_cap"], Y)
    try:
        res = requests.get("https://seed-flowers.vercel.app/api/captcha/check", timeout=30).json()
        task_id = res.get("task_id")
        if not task_id:
            log(acc_num, "❌", t["cap_id_fail"], R)
            return None
        
        frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        attempt = 1
        while True:
            try:
                poll_res = requests.get(f"https://seed-flowers.vercel.app/api/captcha/poll?task_id={task_id}", timeout=30).json()
                status = poll_res.get("status")
                if status == "oke":
                    print("\r\033[K", end="")
                    token = poll_res.get("token")
                    short_token = token[:10] + "...." if token else ""
                    log(acc_num, "✅", f"{t['cap_ok']} {G}{short_token}{RES}", G)
                    return token
            except Exception:
                pass
            poll_text = t["cap_poll"].replace("(Wait 5s)", f"(Attempt {attempt})")
            for i in range(50):
                f = frames[i % len(frames)]
                print(f"\r \033[38;5;51m│\033[0m \033[38;5;220m[{acc_num:04d}]\033[0m \033[38;5;208m[{f}]\033[0m \033[1;38;5;51m{poll_text}\033[0m\033[K", end="", flush=True)
                await asyncio.sleep(0.1)
            attempt += 1
    except Exception as e:
        log(acc_num, "❌", f"{t['cap_err']} {e}", R)
        return None

async def authenticate(client, acc_num, sess_name, start_param):
    log(acc_num, "🤖", t["start_bot"].format(BOT_USERNAME), Y)
    try:
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        await client(StartBotRequest(
            bot=bot_entity,
            peer=bot_entity,
            start_param=start_param
        ))
        await asyncio.sleep(3)

        log(acc_num, "⚙️", t["fetch_init"], Y)
        result = await client(RequestWebViewRequest(
            peer=bot_entity,
            bot=bot_entity,
            platform="android",
            from_bot_menu=False,
            url="https://musicmb.site"
        ))
        
        raw_init = result.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
        init_data = urllib.parse.unquote(raw_init)

        token_captcha = await process_captcha(acc_num)
        if not token_captcha:
            return None

        log(acc_num, "🔐", t["auth_srv"], C)
        url = "https://api.musicmb.site/api/auth/telegram"
        payload = {
            "init_data": init_data,
            "turnstile_token": token_captcha
        }
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Not=A?Brand";v="99", "Android WebView";v="151", "Chromium";v="151"',
            'sec-ch-ua-mobile': "?1",
            'Origin': "https://musicmb.site",
            'X-Requested-With': "org.telegram.messenger.web",
            'Sec-Fetch-Site': "same-site",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://musicmb.site/",
            'Accept-Language': "en,id-ID;q=0.9,id;q=0.8,en-US;q=0.7"
        }
        
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            auth_token = res.json().get("token")
            save_token(sess_name, auth_token)
            log(acc_num, "✅", t["auth_ok"], G)
            return auth_token
        else:
            log(acc_num, "❌", f"{t['auth_fail']} {res.status_code}", R)
            return None
    except Exception as e:
        log(acc_num, "❌", f"Auth exception: {e}", R)
        return None

async def watch_ads_until_done(acc_num, headers):
    """Fungsi untuk menonton iklan sampai habis untuk kedua provider"""
    log(acc_num, "📺", t["watch_ads"], C)
    
    # ===== GIGAPUB =====
    log(acc_num, "📢", "Processing GigaPub ads...", Y)
    attempt = 0
    max_attempts = 100
    while attempt < max_attempts:
        attempt += 1
        try:
            resp = requests.get("https://api.musicmb.site/api/dashboard", headers=headers, timeout=30)
            if resp.status_code != 200:
                log(acc_num, "⚠️", f"Failed to refresh dashboard: {resp.status_code}", Y)
                break
            data = resp.json()
            ad_data = data.get('ad_boost', {})
            if ad_data.get('active') == True:
                log(acc_num, "⏭️", t["ad_giga_skip"], G)
                break
            watched = ad_data.get('ads_watched', 0)
            required = ad_data.get('ads_required', 10)
            if watched >= required:
                log(acc_num, "✅", t["ad_giga_done"].format(watched, required), G)
                break
            log(acc_num, "📢", t["ad_giga"].format(watched+1, required), Y)
            res_ad = requests.post("https://api.musicmb.site/api/mining/ad-boost/complete", headers=headers, timeout=30)
            if res_ad.status_code == 200:
                log(acc_num, "✅", t["ad_giga_ok"], G)
            else:
                log(acc_num, "⚠️", t["ad_giga_fail"].format(res_ad.status_code), Y)
            await asyncio.sleep(random.uniform(1.5, 3))
        except Exception as e:
            log(acc_num, "❌", t["ad_giga_error"].format(e), R)
            await asyncio.sleep(2)
    
    # ===== LIBTL =====
    log(acc_num, "📢", "Processing Libtl ads...", Y)
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            resp = requests.get("https://api.musicmb.site/api/dashboard", headers=headers, timeout=30)
            if resp.status_code != 200:
                log(acc_num, "⚠️", f"Failed to refresh dashboard: {resp.status_code}", Y)
                break
            data = resp.json()
            ad_data = data.get('libtl_ad_boost', {})
            if ad_data.get('active') == True:
                log(acc_num, "⏭️", t["ad_libtl_skip"], G)
                break
            watched = ad_data.get('ads_watched', 0)
            required = ad_data.get('ads_required', 10)
            if watched >= required:
                log(acc_num, "✅", t["ad_libtl_done"].format(watched, required), G)
                break
            log(acc_num, "📢", t["ad_libtl"].format(watched+1, required), Y)
            res_ad = requests.post("https://api.musicmb.site/api/mining/libtl-ad-boost/complete", headers=headers, timeout=30)
            if res_ad.status_code == 200:
                log(acc_num, "✅", t["ad_libtl_ok"], G)
            else:
                log(acc_num, "⚠️", t["ad_libtl_fail"].format(res_ad.status_code), Y)
            await asyncio.sleep(random.uniform(1.5, 3))
        except Exception as e:
            log(acc_num, "❌", t["ad_libtl_error"].format(e), R)
            await asyncio.sleep(2)

async def process_account(client, acc_num, sess_name, start_param):
    tokens = load_tokens()
    auth_token = tokens.get(sess_name)
    
    if auth_token:
        log(acc_num, "♻️", t["tok_found"], C)
    else:
        log(acc_num, "⚠️", t["tok_not"], Y)
        auth_token = await authenticate(client, acc_num, sess_name, start_param)
        if not auth_token:
            return

    headers = {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Android WebView";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': "?1",
        'Origin': "https://musicmb.site",
        'X-Requested-With': "org.telegram.messenger.web",
        'Sec-Fetch-Site': "same-site",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Dest': "empty",
        'Referer': "https://musicmb.site/",
        'Accept-Language': "en,id-ID;q=0.9,id;q=0.8,en-US;q=0.7",
        'Authorization': f"Bearer {auth_token}"
    }

    res_dash = requests.get("https://api.musicmb.site/api/dashboard", headers=headers, timeout=30)
    
    if res_dash.status_code in [401, 403]:
        log(acc_num, "⚠️", t["tok_exp"], R)
        auth_token = await authenticate(client, acc_num, sess_name, start_param)
        if not auth_token:
            return
        headers['Authorization'] = f"Bearer {auth_token}"
        res_dash = requests.get("https://api.musicmb.site/api/dashboard", headers=headers, timeout=30)
        
    if res_dash.status_code != 200:
        log(acc_num, "❌", f"{t['dash_fail']} {res_dash.status_code}", R)
        return

    dash_data = res_dash.json()
    user_info = dash_data.get("user", {})
    
    log(acc_num, "👤", f"{t['user_id']} {G}{user_info.get('telegram_id')} | {user_info.get('name')}{RES}", C)
    log(acc_num, "💰", f"{t['balance']} {Y}{user_info.get('balance')}{RES}", C)

    if user_info.get("wallet_address") is None:
        log(acc_num, "💼", t["wall_not"], Y)
        user_wallet = input(f" \033[38;5;51m│\033[0m \033[38;5;220m[{acc_num:04d}]\033[0m \033[1;38;5;208m{t['input_wall']}\033[1;37m").strip()
        
        try:
            raw_addr = convert_ton_address(user_wallet)
            short_raw = raw_addr[:10] + "...."
            log(acc_num, "🔗", f"{t['raw_addr']} {short_raw}", C)
            
            res_wallet = requests.put("https://api.musicmb.site/api/profile/wallet", json={"address": raw_addr}, headers=headers, timeout=30)
            if res_wallet.status_code == 200:
                wallet_data = res_wallet.json()
                if wallet_data.get("wallet_locked"):
                    log(acc_num, "✅", t["bind_ok"], G)
            else:
                log(acc_num, "❌", f"{t['bind_fail']} {res_wallet.status_code}", R)
        except Exception as e:
            log(acc_num, "❌", f"{t['inv_wall']} {e}", R)
    else:
        log(acc_num, "💼", t["wall_link"], G)

    # ===== URUTAN: WATCH ADS DAHULU SAMPAI HABIS =====
    await watch_ads_until_done(acc_num, headers)

    # ===== BARU KLAIM TUGAS =====
    tasks = dash_data.get('tasks', [])
    for task in tasks:
        if task.get('completed', True):
            continue
        task_id = task['id']
        reward = task.get('reward', 0)
        vtype = task.get('verification_type', '')
        title = task.get('title', f'Task {task_id}')
        log(acc_num, "📋", f"Processing task {task_id} - {title} (Reward: {reward})", C)

        if vtype == 'telegram_subscription':
            action_url = task.get('action_url', '')
            channel_username = parse_channel_from_url(action_url)
            if channel_username:
                try:
                    entity = await client.get_entity(channel_username)
                    try:
                        await client(GetParticipantRequest(channel=entity, participant='me'))
                        log(acc_num, "⏭️", f"Already joined @{channel_username}, skipping join", G)
                    except:
                        log(acc_num, "⏳", f"Joining @{channel_username}...", Y)
                        await client(JoinChannelRequest(entity))
                        await asyncio.sleep(2)
                        log(acc_num, "✅", f"Joined @{channel_username}", G)
                    success = await claim_task(acc_num, headers, task_id, reward)
                    if success:
                        log(acc_num, "✅", f"Task {task_id} claimed: {reward} MB", G)
                    else:
                        log(acc_num, "⚠️", f"Failed to claim task {task_id}", Y)
                except Exception as e:
                    log(acc_num, "❌", f"Error with channel @{channel_username}: {e}", R)
            else:
                log(acc_num, "⚠️", f"No channel found for task {task_id}", Y)

        elif vtype == 'api':
            success = await claim_task(acc_num, headers, task_id, reward)
            if success:
                log(acc_num, "✅", f"Task {task_id} claimed: {reward} MB", G)
            else:
                log(acc_num, "⚠️", f"Failed to claim task {task_id}", Y)

        else:
            log(acc_num, "⏭️", f"Skipping task {task_id} (type: {vtype})", Y)

        await asyncio.sleep(random.uniform(0.5, 1.5))

    # ===== AKTIVASI MINING =====
    log(acc_num, "⛏️", t["act_mine"], Y)
    res_mine = requests.post("https://api.musicmb.site/api/mining/start", headers=headers, timeout=30)
    
    if res_mine.status_code in [200, 201]:
        mine_data = res_mine.json().get("mining", {})
        if mine_data.get("active"):
            start_time = format_date(mine_data.get("started_at"))
            exp_time = format_date(mine_data.get("expires_at"))
            log(acc_num, "✅", t["mine_ok"], G)
            log(acc_num, "🕒", f"{t['start_at']} {start_time}", C)
            log(acc_num, "⏳", f"{t['claim_in']} {exp_time}", M)
        else:
            log(acc_num, "⚠️", t["mine_fail_act"], Y)
    elif res_mine.status_code == 400 and "already active" in res_mine.text.lower():
        log(acc_num, "⏭️", t["mine_alr"], G)
    else:
        log(acc_num, "❌", f"{t['mine_fail']} {res_mine.status_code}", R)
        
    print(f" \033[38;5;51m│\033[0m")

# ====== FUNGSI PEMBUATAN SESSION OTOMATIS ======
async def create_session():
    print(f" \033[38;5;51m│\033[0m \033[1;38;5;208m{t['creating_session']}\033[0m")
    phone = input(f" \033[38;5;51m│\033[0m \033[1;38;5;208m{t['enter_phone']}\033[0m").strip()
    if not phone:
        print(f" \033[38;5;51m│\033[0m \033[1;31mPhone number is required.\033[0m")
        return None

    sessions = glob.glob("sess*.session")
    max_num = 0
    for f in sessions:
        try:
            num = int(f.replace('sess', '').replace('.session', ''))
            if num > max_num:
                max_num = num
        except:
            pass
    new_num = max_num + 1
    sess_name = f"sess{new_num}"

    client = TelegramClient(sess_name, API_ID, API_HASH)
    await client.connect()

    try:
        await client.send_code_request(phone)
        code = input(f" \033[38;5;51m│\033[0m \033[1;38;5;208m{t['enter_code']}\033[0m").strip()
        if not code:
            print(f" \033[38;5;51m│\033[0m \033[1;31mCode is required.\033[0m")
            await client.disconnect()
            return None

        await client.sign_in(phone, code)
        print(f" \033[38;5;51m│\033[0m \033[1;32m{t['session_created'].format(sess_name + '.session')}\033[0m")
        await client.disconnect()
        return sess_name

    except SessionPasswordNeededError:
        password = input(f" \033[38;5;51m│\033[0m \033[1;38;5;208m{t['enter_password']}\033[0m").strip()
        try:
            await client.sign_in(password=password)
            print(f" \033[38;5;51m│\033[0m \033[1;32m{t['session_created'].format(sess_name + '.session')}\033[0m")
            await client.disconnect()
            return sess_name
        except Exception as e:
            print(f" \033[38;5;51m│\033[0m \033[1;31m{t['session_create_fail'].format(str(e))}\033[0m")
            await client.disconnect()
            return None

    except Exception as e:
        print(f" \033[38;5;51m│\033[0m \033[1;31m{t['session_create_fail'].format(str(e))}\033[0m")
        await client.disconnect()
        return None

async def validate_session(client, sess_name):
    """Validasi apakah session masih aktif"""
    try:
        if not await client.is_user_authorized():
            return False
        # Coba dapatkan info user
        me = await client.get_me()
        if me:
            return True
        return False
    except (AuthKeyUnregisteredError, AuthKeyInvalidError):
        return False
    except Exception:
        return False

# ====== MAIN ======
async def main():
    banner()
    user_ref = input(f"{Y} Input Code [ {DEFAULT_REF} ] : {W}").strip()
    if not user_ref:
        user_ref = DEFAULT_REF

    banner()
    sessions = glob.glob("sess*.session")
    
    if not sessions:
        print(f" \033[38;5;51m│\033[0m \033[1;38;5;196m{t['no_sess']}\033[0m")
        choice = input(f" \033[38;5;51m│\033[0m \033[1;38;5;208m{t['no_sess_ask']}\033[0m").strip().lower()
        if choice not in ['y', 'yes']:
            print(f" \033[38;5;51m│\033[0m \033[1;31mExiting...\033[0m")
            return
        sess_name = await create_session()
        if not sess_name:
            print(f" \033[38;5;51m│\033[0m \033[1;31mFailed to create session. Exiting.\033[0m")
            return
        session_file = sess_name + '.session'
        sessions = [session_file]
    else:
        session_file = sessions[0]
        sess_name = session_file.replace('.session', '')

    acc_num = 1
    print(f" \033[38;5;51m│\033[0m \033[1;38;5;46m{t['found_sess'].format(1)}\033[0m")
    print(f" \033[38;5;51m│\033[0m")

    print(f" \033[38;5;51m├─[ \033[1;38;5;220m{t['exec_acc']} 1/1\033[0m \033[38;5;51m]\033[0m")
    print(f" \033[38;5;51m│\033[0m \033[38;5;45m{t['target_sess']}\033[0m \033[1;97m{sess_name}\033[0m")

    try:
        client = TelegramClient(sess_name, API_ID, API_HASH)
        await client.connect()
        
        # Validasi session
        is_valid = await validate_session(client, sess_name)
        
        if not is_valid:
            log(acc_num, "❌", t["auth_exp"], R)
            await client.disconnect()
            
            # Tawarkan membuat session baru
            print(f" \033[38;5;51m│\033[0m")
            choice = input(f" \033[38;5;51m│\033[0m \033[1;38;5;208mSession expired. Create new session? (y/n): \033[0m").strip().lower()
            if choice in ['y', 'yes']:
                # Hapus session lama yang corrupt
                if os.path.exists(session_file):
                    try:
                        os.remove(session_file)
                        print(f" \033[38;5;51m│\033[0m \033[1;33mRemoved old session file: {session_file}\033[0m")
                    except:
                        pass
                sess_name = await create_session()
                if not sess_name:
                    print(f" \033[38;5;51m│\033[0m \033[1;31mFailed to create session. Exiting.\033[0m")
                    input(f"\n{Fore.CYAN}Tekan Enter untuk keluar...{Style.RESET_ALL}")
                    return
                session_file = sess_name + '.session'
                client = TelegramClient(sess_name, API_ID, API_HASH)
                await client.connect()
            else:
                print(f" \033[38;5;51m│\033[0m \033[1;31mExiting...\033[0m")
                input(f"\n{Fore.CYAN}Tekan Enter untuk keluar...{Style.RESET_ALL}")
                return
        
        # Proses account
        await process_account(client, acc_num, sess_name, user_ref)
        await client.disconnect()
        
    except Exception as e:
        log(acc_num, "❌", f"Critical Error: {e}", R)
        import traceback
        traceback.print_exc()
            
    print(f"\033[38;5;51m" + "─" * get_width() + "\033[0m")
    print(f" \033[1;38;5;46m[✔] {t['all_done']}\033[0m")
    print(f"\033[38;5;51m" + "─" * get_width() + "\033[0m")
    print(f" \033[38;5;51m│\033[0m \033[1;38;5;46m{t['press_enter']}\033[0m")
    input()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\033[1;38;5;196m[!] {t['term']}\033[0m")
