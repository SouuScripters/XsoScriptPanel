#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAIDZ SINGLE SESSION - v13 BLUE EDITION (SOUU ENGINE)
- Adloop, Telega.io, USL region rotation
- Smart cooldown: rate limit + no banners + consecutive fails
"""

import asyncio
import aiohttp
import json
import re
import uuid
import time
import struct
import os
import random
import base64
import urllib.parse
import sys
from collections import deque
from urllib.parse import quote
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import RequestWebViewRequest


# ═══════════════════════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════════════════════
WARMUP_SECONDS = 8
ADSTART_MAX_ATTEMPTS = 2

PROVIDER_ORDER = ["adloop", "adsgram", "gigapub", "tads", "telega", "usl", "monetix", "adexium", "richads"]

PROVIDER_LABEL = {
    "adloop": "Adloop", "adsgram": "Adsgram", "gigapub": "Gigapub",
    "tads": "Tads", "telega": "Telega", "usl": "USL",
    "monetix": "Monetix", "adexium": "Adexium", "richads": "Richads",
}

# Cooldown rules (detik)
COOLDOWN_NO_BANNERS   = 60
COOLDOWN_FAIL_STREAK  = 300
FAIL_STREAK_THRESHOLD = 3


# ═══════════════════════════════════════════════════════════
# WARNA — BLUE EDITION
# ═══════════════════════════════════════════════════════════
class C:
    RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
    RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'
    BLUE='\033[94m'; MAGENTA='\033[95m'; CYAN='\033[96m'
    WHITE='\033[97m'; ORANGE='\033[38;5;208m'
    PINK='\033[38;5;205m'
    LIME='\033[38;5;33m'
    LIME2='\033[38;5;39m'
    LIME3='\033[38;5;45m'
    GREY='\033[38;5;245m'


# ═══════════════════════════════════════════════════════════
# KONFIG TELEGRAM / API
# ═══════════════════════════════════════════════════════════
API_ID   = 28752231
API_HASH = "ec1c1f2c30e2f1855c3edee7e348480b"
BOT_USERNAME = "PAlDZ_BOT"
API_BASE = "https://api.paidz.biz"
APP_URL = "https://paidz.biz"
ADSGRAM_BASE = "https://api.adsgram.ai"
GIGAPUB_BASE = "https://ad.gigapub.tech"
GIGAPUB_PROJECT_ID = "7780"
USL_BASE = "https://api.uslads.com"

ADV_BLOCK_ID = "43282"
USL_API_KEY = "4f4578ac2736beb5f3fe0013a1ac4239"
USL_PLACEMENT_ID = "plc_18fc0989315cc854"
MONETIX_MXID = "MX-DAC015C2"

LIMITS = {
    "adloop": 80,
    "adsgram": 100, "gigapub": 150, "tads": 60, "telega": 80,
    "usl": 80, "monetix": 80, "adexium": 80, "richads": 40,
}

SESSION_NAME = "paidz_account"
SESSION_PATH = SESSION_NAME
PROGRESS_FILE = "paidz_progress.json"
PER_ACCOUNT_TIMEOUT = 7200

BOX_WIDTH = 64
LOG_LINES_MAX = 10


# ═══════════════════════════════════════════════════════════
# GLOBAL UI STATE
# ═══════════════════════════════════════════════════════════
LOG_BUFFER = deque(maxlen=LOG_LINES_MAX)
UI_STATS = {"claims": 0, "success": 0, "failures": 0}
USER_META = {"username": "-", "name": "-", "session": SESSION_NAME}
START_TS = time.time()


def log(tag, msg, kind="info"):
    ts = time.strftime("%H:%M:%S")
    LOG_BUFFER.append((ts, tag, msg, kind))


# ═══════════════════════════════════════════════════════════
# FINGERPRINTS
# ═══════════════════════════════════════════════════════════
UA_POOL = [
    "Mozilla/5.0 (Linux; Android 15; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1 (Infinix Infinix X6871; Android 15; SDK 35; HIGH)",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7822.100 Mobile Safari/537.36 Telegram-Android/12.9.0 (Samsung SM-S928B; Android 14; SDK 34)",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7622.50 Mobile Safari/537.36 Telegram-Android/12.8.5 (Google Pixel 7; Android 13; SDK 33)",
    "Mozilla/5.0 (Linux; Android 15; OnePlus 12R) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.199 Mobile Safari/537.36 Telegram-Android/12.9.1 (OnePlus CPH2585; Android 15; SDK 35)",
    "Mozilla/5.0 (Linux; Android 14; Redmi Note 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7522.80 Mobile Safari/537.36 Telegram-Android/12.8.0 (Xiaomi 2312DRA50I; Android 14; SDK 34)",
    "Mozilla/5.0 (Linux; Android 13; Vivo V25) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7422.60 Mobile Safari/537.36 Telegram-Android/12.7.5 (Vivo V2202; Android 13; SDK 33)",
    "Mozilla/5.0 (Linux; Android 14; Realme GT 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7822.100 Mobile Safari/537.36 Telegram-Android/12.9.0 (Realme RMX2151; Android 14; SDK 34)",
    "Mozilla/5.0 (Linux; Android 13; Samsung A54) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7522.80 Mobile Safari/537.36 Telegram-Android/12.8.0 (Samsung SM-A546E; Android 13; SDK 33)",
]
SCREENS = ["360x812@3","412x915@2.625","393x873@3","360x780@3","412x892@2.625","360x800@3"]
TIMEZONES = ["Asia/Calcutta","Asia/Kolkata","Asia/Mumbai","Asia/Delhi","Asia/Chennai","Asia/Bangalore"]
WEBGL_REND = ["Mali-G610 MC6","Adreno (TM) 730","Mali-G78 MP14","Adreno (TM) 660","Mali-G77 MC9","Adreno (TM) 650"]
WEBGL_VEND = ["ARM","Qualcomm","Mali"]
LANGS = ["en-US","en-IN","en-GB","en"]
ISP_PREFIXES = [
    (49,36),(49,37),(49,43),(49,44),(59,144),(59,145),
    (103,21),(103,22),(103,23),(106,51),(106,193),
    (122,160),(122,161),(182,64),(182,65),(202,83),
    (202,84),(203,88),(203,89),(223,185),
]

def rand_ip():
    a,b = random.choice(ISP_PREFIXES)
    return f"{a}.{b}.{random.randint(1,254)}.{random.randint(1,254)}"

def rand_telemetry():
    return {
        "visitorId": f"{uuid.uuid4()}:{uuid.uuid4().hex[:7]}",
        "platform": "android",
        "screen": random.choice(SCREENS),
        "userAgent": random.choice(UA_POOL),
        "language": random.choice(LANGS),
        "timezone": random.choice(TIMEZONES),
        "webglVendor": random.choice(WEBGL_VEND),
        "webglRenderer": random.choice(WEBGL_REND),
        "hardwareConcurrency": random.choice([4,6,8]),
        "deviceMemory": random.choice([4,6,8]),
        "isWebdriver": False,
        "secChUaPlatform": "Android",
        "secChUaMobile": "?1",
        "pluginsLength": 0,
        "maxTouchPoints": 5,
        "isTelegramWebApp": True,
    }


# ═══════════════════════════════════════════════════════════
# PROGRESS
# ═══════════════════════════════════════════════════════════
def _today(): return time.strftime("%Y-%m-%d")

def load_all_progress():
    if not os.path.exists(PROGRESS_FILE): return {}
    try:
        with open(PROGRESS_FILE) as f: return json.load(f)
    except: return {}

_plock = asyncio.Lock()

async def save_all_progress(data):
    async with _plock:
        try:
            with open(PROGRESS_FILE,"w") as f:
                json.dump(data, f, indent=2)
        except: pass

def ensure_account_entry(all_prog, name):
    today = _today()
    if name not in all_prog:
        all_prog[name] = {"date": today, "providers": {p:0 for p in LIMITS}}
    if all_prog[name].get("date") != today:
        all_prog[name] = {"date": today, "providers": {p:0 for p in LIMITS}}
    for p in LIMITS:
        all_prog[name]["providers"].setdefault(p, 0)
    return all_prog[name]

def remaining(acc_prog, provider):
    used = acc_prog["providers"].get(provider, 0)
    return max(0, LIMITS.get(provider, 0) - used)


# ═══════════════════════════════════════════════════════════
# RETRY
# ═══════════════════════════════════════════════════════════
async def retry_async(fn,*a,retries=3,delay=2,name="",**kw):
    for att in range(1,retries+1):
        try:
            return await fn(*a,**kw)
        except (aiohttp.ClientOSError, aiohttp.ClientConnectionError,
                aiohttp.ServerDisconnectedError, asyncio.TimeoutError):
            if att<retries:
                await asyncio.sleep(delay*att)
                continue
            raise


# ═══════════════════════════════════════════════════════════
# PROTOBUF
# ═══════════════════════════════════════════════════════════
def encode_touch(p):
    b=p.encode()
    return b'\x0a'+bytes([len(b)])+b+b'\x12\x05touch\x18\x01'

def encode_watch(p, adsess):
    pb=p.encode(); ab=adsess.encode()
    return (b'\x0a'+bytes([len(pb)])+pb+
            b'\x12'+bytes([len(ab)])+ab+
            b'\x19'+struct.pack('<d',time.time()))

def decode_adsess(data):
    m=re.search(r'adsess_[a-f0-9]+',data.decode('utf-8','ignore'))
    return m.group() if m else None


# ═══════════════════════════════════════════════════════════
# ADSGRAM DCS BUILDER
# ═══════════════════════════════════════════════════════════
def build_adsgram_dcs_from_raw(init_data: str):
    try:
        kv = {}
        for p in init_data.split("&"):
            if "=" in p:
                k, v = p.split("=", 1)
                kv[k] = v
        auth_date = kv.get("auth_date", "")
        query_id  = kv.get("query_id", "")
        user_enc  = kv.get("user", "")
        signature = kv.get("signature", "")
        user_raw = urllib.parse.unquote(user_enc)
        dcs_raw = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_raw}"
        dcs_b64 = base64.b64encode(dcs_raw.encode()).decode()
        dcs_b64 = dcs_b64.replace('+', '-').replace('/', '_').rstrip('=')
        return signature, dcs_b64
    except Exception:
        return None, None


# ═══════════════════════════════════════════════════════════
# SESSION HELPERS
# ═══════════════════════════════════════════════════════════
def _nuke_session_journals(session_path: str):
    for suf in ("-journal", "-wal", "-shm", ".lock"):
        p = session_path + suf
        if os.path.exists(p):
            try: os.remove(p)
            except: pass


async def open_tg_client(session_path, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            _nuke_session_journals(session_path)
            client = TelegramClient(
                session_path,
                API_ID, API_HASH,
                sequential_updates=True,
                auto_reconnect=True,
                connection_retries=3,
                retry_delay=2,
                timeout=20,
            )
            await client.connect()
            return client, None
        except Exception as e:
            err_name = type(e).__name__
            err_msg = str(e)
            print(f"\n{C.RED}=== open_tg_client ATTEMPT {attempt}/{max_retries} ==={C.RESET}")
            print(f"   Type    : {err_name}")
            print(f"   Message : {err_msg}")
            if "OperationalError" in err_name or "locked" in err_msg.lower() \
               or "database" in err_msg.lower():
                _nuke_session_journals(session_path)
                await asyncio.sleep(2 * attempt)
                continue
            return None, f"{err_name}: {err_msg}"
    return None, "OperationalError: session locked / corrupt"


# ═══════════════════════════════════════════════════════════
# LOGIN INTERAKTIF
# ═══════════════════════════════════════════════════════════
async def login_interaktif():
    print(f"\n{C.LIME}╔{'═'*60}╗{C.RESET}")
    print(f"{C.LIME}║{C.WHITE}  🔐 BELUM ADA SESSION — LOGIN DULU{(' '*24)}{C.LIME}║{C.RESET}")
    print(f"{C.LIME}╚{'═'*60}╝{C.RESET}\n")

    phone = input(f"{C.LIME2}📱 Nomor HP (format +62xxx / +91xxx): {C.RESET}").strip()
    if not phone:
        print(f"{C.RED}❌ Nomor HP kosong.{C.RESET}")
        return False

    phone = phone.replace(' ', '').replace('-', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    _nuke_session_journals(SESSION_PATH)

    client = None
    try:
        client, err = await open_tg_client(SESSION_PATH)
        if err:
            print(f"{C.RED}❌ Gagal buka client: {err}{C.RESET}")
            return False

        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\n{C.LIME2}✅ Session sudah ada!")
            print(f"{C.WHITE}   Nama : {C.LIME}{me.first_name or '-'}{C.RESET}")
            print(f"{C.WHITE}   User : {C.LIME}@{me.username or me.id}{C.RESET}")
            await client.disconnect()
            return True

        MAX_OTP_RETRY = 3
        signed_in = False
        sent = None

        for otp_attempt in range(1, MAX_OTP_RETRY + 1):
            try:
                print(f"{C.YELLOW}⏳ Mengirim kode OTP... (attempt {otp_attempt}/{MAX_OTP_RETRY}){C.RESET}")
                sent = await client.send_code_request(phone)
                print(f"{C.LIME3}   ℹ️  Cek Telegram app / SMS.{C.RESET}")
                print(f"{C.LIME3}   ⏱️  Input dalam 60 detik.{C.RESET}")

                code = input(f"{C.LIME2}🔢 Kode OTP: {C.RESET}").strip()
                if not code:
                    print(f"{C.RED}❌ Kode kosong.{C.RESET}")
                    continue

                try:
                    await client.sign_in(phone, code,
                                         phone_code_hash=sent.phone_code_hash)
                    signed_in = True
                    break
                except SessionPasswordNeededError:
                    for pw_attempt in range(1, 4):
                        pw = input(f"{C.LIME2}🔒 Password 2FA ({pw_attempt}/3): {C.RESET}").strip()
                        if not pw:
                            print(f"{C.RED}❌ Password kosong.{C.RESET}")
                            continue
                        try:
                            await client.sign_in(password=pw)
                            signed_in = True
                            break
                        except Exception as e:
                            print(f"{C.RED}❌ 2FA salah: {type(e).__name__}{C.RESET}")
                    if signed_in:
                        break
                    else:
                        print(f"{C.RED}❌ 3x salah password.{C.RESET}")
                        await client.disconnect()
                        try: os.remove(SESSION_PATH + ".session")
                        except: pass
                        return False

            except Exception as e:
                err_name = type(e).__name__
                err_msg = str(e)
                if "PhoneCodeExpired" in err_name or "expired" in err_msg.lower():
                    print(f"{C.YELLOW}⚠️  Kode expired! Minta kode baru...{C.RESET}")
                    await asyncio.sleep(2)
                    continue
                if "PhoneCodeInvalid" in err_name or "invalid" in err_msg.lower():
                    print(f"{C.YELLOW}⚠️  Kode salah! Coba lagi...{C.RESET}")
                    if otp_attempt >= 2:
                        sent = None
                    continue
                if "FloodWait" in err_name:
                    wait = getattr(e, "seconds", 60)
                    print(f"{C.YELLOW}⚠️  Flood wait {wait}s...{C.RESET}")
                    await asyncio.sleep(wait + 2)
                    continue
                raise

        if not signed_in:
            print(f"{C.RED}❌ Login gagal setelah {MAX_OTP_RETRY} percobaan.{C.RESET}")
            await client.disconnect()
            try: os.remove(SESSION_PATH + ".session")
            except: pass
            _nuke_session_journals(SESSION_PATH)
            return False

        me = await client.get_me()
        print(f"\n{C.LIME2}✅ LOGIN BERHASIL!")
        print(f"{C.WHITE}   Nama : {C.LIME}{me.first_name or '-'}{C.RESET}")
        print(f"{C.WHITE}   User : {C.LIME}@{me.username or me.id}{C.RESET}")
        print(f"{C.WHITE}   File : {C.LIME}{SESSION_PATH}.session{C.RESET}\n")
        await client.disconnect()
        return True

    except Exception as e:
        print(f"{C.RED}❌ Login gagal: {type(e).__name__}: {e}{C.RESET}")
        import traceback
        traceback.print_exc()
        if client:
            try: await client.disconnect()
            except: pass
        try: os.remove(SESSION_PATH + ".session")
        except: pass
        _nuke_session_journals(SESSION_PATH)
        return False


def session_exists():
    return os.path.exists(SESSION_PATH + ".session")

def session_is_valid_size():
    p = SESSION_PATH + ".session"
    if not os.path.exists(p): return False
    return os.path.getsize(p) > 1024


# ═══════════════════════════════════════════════════════════
# REGION POOL
# ═══════════════════════════════════════════════════════════
REGION_POOL = [
    ("US", "8.8.8.8",         "en-US", "America/New_York"),
    ("GB", "51.140.0.1",      "en-GB", "Europe/London"),
    ("DE", "18.194.0.1",      "de-DE", "Europe/Berlin"),
    ("FR", "15.188.0.1",      "fr-FR", "Europe/Paris"),
    ("IN", "49.44.0.1",       "en-IN", "Asia/Kolkata"),
    ("BR", "18.228.0.1",      "pt-BR", "America/Sao_Paulo"),
    ("PH", "13.229.0.1",      "en-PH", "Asia/Manila"),
    ("NG", "52.31.0.1",       "en-NG", "Africa/Lagos"),
    ("PK", "39.32.0.1",       "en-PK", "Asia/Karachi"),
    ("BD", "103.4.0.1",       "bn-BD", "Asia/Dhaka"),
    ("RU", "5.16.0.1",        "ru-RU", "Europe/Moscow"),
    ("TR", "78.163.0.1",      "tr-TR", "Europe/Istanbul"),
    ("MX", "187.188.0.1",     "es-MX", "America/Mexico_City"),
    ("EG", "41.32.0.1",       "ar-EG", "Africa/Cairo"),
    ("ZA", "41.0.0.1",        "en-ZA", "Africa/Johannesburg"),
    ("VN", "14.160.0.1",      "vi-VN", "Asia/Ho_Chi_Minh"),
    ("TH", "49.228.0.1",      "th-TH", "Asia/Bangkok"),
    ("MY", "60.48.0.1",       "ms-MY", "Asia/Kuala_Lumpur"),
    ("IT", "79.10.0.1",       "it-IT", "Europe/Rome"),
    ("SA", "5.42.0.1",        "ar-SA", "Asia/Riyadh"),
]


# ═══════════════════════════════════════════════════════════
# AKUN
# ═══════════════════════════════════════════════════════════
class PaidzAccount:
    def __init__(self, session_path, name, ui):
        self.session_path = session_path
        self.name = name
        self.ui = ui
        self.client = None
        self.ua = random.choice(UA_POOL)
        self.device_uuid = str(uuid.uuid4())
        self.telemetry = rand_telemetry()
        self.REAL_INIT_DATA = None
        self.USER_INFO = {"id":"","first_name":"User","username":"user","language_code":"en"}
        self.token = None
        self.balance = 0
        self.ads = 0
        self.acc_prog = None
        self.start_time = time.time()
        self.cooldowns = {}
        self.fail_streak = {}

    def set_ui(self, **kwargs):
        self.ui.update(kwargs)

    def get_headers(self, token=None, ct="application/json"):
        fake_ip = rand_ip(); fake_ip2 = rand_ip()
        h = {
            'Accept':"*/*", 'Content-Type':ct,
            'User-Agent': self.ua,
            'X-Requested-With':"org.telegram.messenger.web",
            'Origin':APP_URL, 'Referer':f"{APP_URL}/",
            'Sec-Fetch-Site':"same-site", 'Sec-Fetch-Mode':"cors",
            'Sec-Fetch-Dest':"empty",
            'Accept-Language': random.choice(LANGS)+",en;q=0.9",
            'X-Idempotency-Key': str(uuid.uuid4()),
            'X-Forwarded-For': f"{fake_ip}, {fake_ip2}",
            'X-Real-IP': fake_ip, 'X-Client-IP': fake_ip,
            'CF-Connecting-IP': fake_ip, 'True-Client-IP': fake_ip,
            'X-Originating-IP': fake_ip, 'X-Remote-Addr': fake_ip,
            'Forwarded': f"for={fake_ip};proto=https",
            'sec-ch-ua': f'"Chromium";v="{random.randint(140,151)}", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
        }
        if token: h['Authorization']=f"Bearer {token}"
        h['Cookie'] = f"paidz_device_uuid_v2={self.device_uuid}; _ga=GA1.2.{random.randint(10**9,10**10)}.{int(time.time())}"
        return h

    def get_adsgram_headers(self):
        return {
            'Accept':"*/*", 'User-Agent': self.ua,
            'X-Requested-With':"org.telegram.messenger.web",
            'Origin':APP_URL, 'Referer':f"{APP_URL}/",
            'Sec-Fetch-Site':"cross-site", 'Sec-Fetch-Mode':"cors",
            'Sec-Fetch-Dest':"empty", 'Accept-Language':"en-US,en;q=0.9",
        }

    async def paidz_auth(self, session):
        try:
            async with session.post(f"{API_BASE}/auth/telegram",
                    json={"initData":self.REAL_INIT_DATA,"telemetry":self.telemetry},
                    headers=self.get_headers(),
                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status!=200: return None,f"HTTP {r.status}"
                d=await r.json()
                if not d.get("token"): return None,"no token"
                return d,None
        except Exception as e:
            return None,f"{type(e).__name__}"

    async def _ads_start_raw(self, session, provider):
        h=self.get_headers(self.token,"application/x-protobuf")
        h['Accept']="application/x-protobuf"
        try:
            async with session.post(f"{API_BASE}/ads/start",
                    data=encode_touch(provider),headers=h,
                    timeout=aiohttp.ClientTimeout(total=20, connect=10, sock_read=15)) as r:
                raw = await r.read()
                if b"AUTH_WARMUP_REQUIRED" in raw:
                    return None, "AUTH_WARMUP_REQUIRED"
                if r.status==429:
                    ra=r.headers.get("Retry-After")
                    wait=int(ra) if ra and ra.isdigit() else 15
                    return None,f"RATE_LIMIT:{wait}"
                if r.status!=200:
                    return None,f"HTTP {r.status}"
                return decode_adsess(raw),None
        except asyncio.TimeoutError:
            return None, "timeout"
        except aiohttp.ClientError as e:
            return None, f"{type(e).__name__}"

    async def paidz_ads_start(self, session, provider):
        adsess, err = await self._ads_start_raw(session, provider)
        if err and err.startswith("RATE_LIMIT:"):
            wait = int(err.split(":")[1])
            return None, f"RATE_LIMIT:{wait}"
        if err == "AUTH_WARMUP_REQUIRED":
            await asyncio.sleep(10)
            adsess, err = await self._ads_start_raw(session, provider)
            if err and err.startswith("RATE_LIMIT:"):
                wait = int(err.split(":")[1])
                return None, f"RATE_LIMIT:{wait}"
            if err: return None, err
        if err:
            return None, err
        return adsess, None

    async def _ads_watch_raw(self, session, provider, adsess):
        h=self.get_headers(self.token,"application/x-protobuf")
        h['Accept']="application/x-protobuf"
        async with session.post(f"{API_BASE}/ads/watch",
                data=encode_watch(provider,adsess),headers=h,
                timeout=aiohttp.ClientTimeout(total=30)) as r:
            return r.status,await r.read()

    async def paidz_ads_watch(self, session, provider, adsess):
        return await retry_async(self._ads_watch_raw,session,provider,adsess,
                                 retries=3,delay=2,name="ads/watch")

    async def login(self):
        self.set_ui(status='login')
        if self.client:
            try: await self.client.disconnect()
            except: pass
            self.client = None

        client, err = await open_tg_client(self.session_path)
        if err:
            self.set_ui(status='error', progress=f'login: {err[:30]}')
            log("LOGIN", f"Gagal buka client: {err}", "err")
            return False
        self.client = client

        try:
            if not await self.client.is_user_authorized():
                self.set_ui(status='error', progress='belum login')
                log("LOGIN", "Session belum authorize", "err")
                return False

            me = await self.client.get_me()
            if not me:
                self.set_ui(status='error', progress='get_me failed')
                log("LOGIN", "get_me() returned None", "err")
                return False

            self.USER_INFO = {
                "id": str(me.id),
                "first_name": me.first_name or "User",
                "username": me.username or f"user_{me.id}",
                "language_code": "en",
            }
            USER_META["username"] = f"@{me.username}" if me.username else f"id{me.id}"
            USER_META["name"] = me.first_name or "User"
            USER_META["session"] = self.name
            self.set_ui(status='farming')
            log("LOGIN", f"Authorized: {USER_META['username']}", "ok")
            return True
        except Exception as e:
            err_name = type(e).__name__
            self.set_ui(status='error', progress=f'login: {err_name}')
            log("LOGIN", f"Gagal: {err_name}", "err")
            if "OperationalError" in err_name:
                try: await self.client.disconnect()
                except: pass
                self.client = None
            return False

    async def get_init_data(self):
        self.set_ui(progress='ambil initData')
        log("INIT", "Requesting init data from bot...", "info")
        try:
            bot = await self.client.get_input_entity(BOT_USERNAME)
            await self.client.send_message(bot, "/start")
            await asyncio.sleep(3)
            result = await self.client(RequestWebViewRequest(
                peer=bot, bot=bot, platform='android',
                from_bot_menu=False, url=f"{APP_URL}/"
            ))
            if not result or not result.url or 'tgWebAppData=' not in result.url:
                log("INIT", "init data tidak diterima", "err")
                return False
            raw = result.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
            self.REAL_INIT_DATA = urllib.parse.unquote(raw)
            log("INIT", "init data OK", "ok")
            return True
        except Exception as e:
            log("INIT", f"error: {type(e).__name__}", "err")
            return False

    async def auth(self, session):
        d, err = await self.paidz_auth(session)
        if err:
            log("AUTH", f"gagal: {err}", "err")
            return False
        self.token = d["token"]
        u = d.get("user", {})
        self.balance = u.get("balanceCoins", 0)
        self.ads = u.get("adsWatchedCount", 0)
        self.set_ui(balance=self.balance, ads=self.ads)
        log("BALANCE", f"{self.balance:.4f} coins", "bal")
        return True

    async def refresh(self, session):
        try:
            d, _ = await self.paidz_auth(session)
            if d:
                self.token = d["token"]
                u = d.get("user", {})
                self.balance = u.get("balanceCoins", 0)
                self.ads = u.get("adsWatchedCount", 0)
                self.set_ui(balance=self.balance, ads=self.ads)
                log("BALANCE", f"{self.balance:.4f} coins", "bal")
        except Exception:
            pass

    # ── ADSGRAM ──
    ADSGRAM_LOCATIONS = [
        ("us", "en", "America/New_York",    "Linux x86_64"),
        ("gb", "en", "Europe/London",       "Linux x86_64"),
        ("de", "de", "Europe/Berlin",       "Linux x86_64"),
        ("fr", "fr", "Europe/Paris",        "Linux x86_64"),
        ("in", "en", "Asia/Kolkata",        "Linux aarch64"),
        ("br", "pt", "America/Sao_Paulo",   "Linux aarch64"),
        ("id", "id", "Asia/Jakarta",        "Android 14"),
        ("ph", "en", "Asia/Manila",         "Android 13"),
        ("ng", "en", "Africa/Lagos",        "Android 14"),
        ("pk", "en", "Asia/Karachi",        "Android 13"),
        ("bd", "bn", "Asia/Dhaka",          "Android 14"),
        ("ru", "ru", "Europe/Moscow",       "Linux armv8l"),
        ("tr", "tr", "Europe/Istanbul",     "Android 14"),
        ("mx", "es", "America/Mexico_City", "Android 13"),
        ("eg", "ar", "Africa/Cairo",        "Android 14"),
        ("za", "en", "Africa/Johannesburg", "Android 13"),
        ("vn", "vi", "Asia/Ho_Chi_Minh",    "Android 14"),
        ("th", "th", "Asia/Bangkok",        "Android 13"),
        ("my", "ms", "Asia/Kuala_Lumpur",   "Android 14"),
        ("it", "it", "Europe/Rome",         "Linux x86_64"),
    ]

    def _random_platform(self):
        return random.choice([
            "Linux aarch64", "Linux armv8l", "Linux armv7l",
            "Linux x86_64", "Android 13", "Android 14", "Android 15",
            "iPhone", "iPad", "MacIntel", "Win32",
        ])

    def _random_request_id(self):
        return str(random.randint(10**20, 10**21 - 1))

    def _random_raw(self):
        return uuid.uuid4().hex + uuid.uuid4().hex[:16]

    def _random_language(self):
        return random.choice([
            "en", "de", "fr", "es", "pt", "it", "ru", "tr",
            "id", "vi", "th", "ms", "bn", "ar", "hi",
        ])

    def _random_ua_for_platform(self, platform):
        if "Android" in platform:
            return random.choice(UA_POOL)
        if "iPhone" in platform or "iPad" in platform:
            return ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1")
        if "MacIntel" in platform:
            return ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{random.randint(130,151)}.0.0.0 Safari/537.36")
        if "Win32" in platform:
            return ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{random.randint(130,151)}.0.0.0 Safari/537.36")
        return (f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{random.randint(130,151)}.0.0.0 Safari/537.36")

    async def adsgram_get_adv(self, session):
        signature, dcs = build_adsgram_dcs_from_raw(self.REAL_INIT_DATA or "")
        if not signature or not dcs:
            return None, "no sig/dcs"

        tg_id = self.USER_INFO["id"]
        country, lang, tz, platform = random.choice(self.ADSGRAM_LOCATIONS)
        if random.random() < 0.5:
            platform = self._random_platform()
        if random.random() < 0.3:
            lang = self._random_language()

        req_id = self._random_request_id()
        raw = self._random_raw()

        url = (f"{ADSGRAM_BASE}/adv?envType=telegram&blockId={ADV_BLOCK_ID}"
               f"&platform={quote(platform)}&language={lang}&top_domain=paidz.biz"
               f"&signature={signature}&data_check_string={dcs}"
               f"&sdk_version=2.2.5&tg_id={tg_id}&tg_platform=android&tma_version=9.6"
               f"&request_id={req_id}&raw={raw}")

        headers = self.get_adsgram_headers()
        headers['User-Agent'] = self._random_ua_for_platform(platform)

        async with session.get(url, headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status != 200:
                return None, f"HTTP {r.status}"
            try:
                d = await r.json()
                if not d.get("banners"):
                    return None, f"no banners"
                return d, None
            except Exception as e:
                return None, f"JSON: {e}"

    async def adsgram_event(self, session, record, etype, tid, media="00:00:00.000"):
        tz_offset = random.randint(-12, 12)
        now = time.gmtime(time.time() + tz_offset * 3600)
        ts = time.strftime('%Y-%m-%dT%H:%M:%S', now) + f".{random.randint(100,999):03d}Z"
        url = (f"{ADSGRAM_BASE}/event?record={record}&trackingtypeid={tid}"
               f"&user_timestamp={quote(ts)}"
               f"&mediaplayhead={quote(media)}&type={etype}")
        async with session.get(url, headers=self.get_adsgram_headers(),
                timeout=aiohttp.ClientTimeout(total=20)) as r:
            return r.status, await r.text()

    async def watch_adsgram(self, session):
        self.set_ui(provider='adsgram', progress='memulai')
        log("ADSGRAM", "Requesting advertisement...", "info")

        adsess, err = await self.paidz_ads_start(session, "adsgram")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.8)

        adv = None
        last_err = None
        for attempt in range(1, 4):
            self.set_ui(progress=f'ambil iklan #{attempt}')
            adv, err = await self.adsgram_get_adv(session)
            if adv: break
            last_err = err
            if "HTTP 400" in str(err) or "HTTP 429" in str(err):
                await asyncio.sleep(random.uniform(3, 6))
                continue
            break
        if not adv:
            log("ADSGRAM", f"adv gagal: {last_err}", "err")
            if "no banners" in str(last_err):
                return False, "NO_BANNERS"
            return False, f"adv: {last_err}"

        log("ADSGRAM", "Advertisement received", "ok")

        banners = adv.get("banners", [])
        if not banners: return False, "no banners"
        trackings = banners[0].get("banner", {}).get("trackings", [])
        if not trackings: return False, "no trackings"

        tmap = {}
        tid_map = {}
        for t in trackings:
            name = t.get("name", "").lower()
            m = re.search(r'record=([^&]+)', t.get("value", ""))
            if m: tmap[name] = m.group(1)
            tid = (t.get("trackingtypeid") or t.get("trackingTypeId")
                   or t.get("type_id") or t.get("tid"))
            if tid is not None: tid_map[name] = tid

        if "render" not in tmap: return False, "no render"
        rec = tmap["render"]

        TID_RENDER   = tid_map.get("render",   13)
        TID_SHOW     = tid_map.get("show",     0)
        TID_START    = tid_map.get("start",    2)
        TID_COMPLETE = tid_map.get("complete", 6)
        TID_REWARD   = tid_map.get("reward",   14)

        s, _ = await self.adsgram_event(session, rec, "Render", TID_RENDER, "00:00:00.004")
        if s != 200: return False, f"render {s}"
        await asyncio.sleep(0.5)

        s, _ = await self.adsgram_event(session, rec, "Show", TID_SHOW, "00:00:02.090")
        if s != 200: return False, f"show {s}"
        await asyncio.sleep(0.5)

        s, _ = await self.adsgram_event(session, rec, "start", TID_START, "00:00:00.004")
        if s != 200: return False, f"start {s}"

        watch_secs = random.choice([15, 16, 17, 18])
        self.set_ui(progress=f'nonton {watch_secs}s')
        log("WATCH", f"Watching {watch_secs}s...", "watch")
        for i in range(watch_secs, 0, -3):
            await asyncio.sleep(3)
            left = max(i - 3, 0)
            self.set_ui(progress=f'nonton {left}s')
            if left > 0:
                log("WATCH", f"{left}s remaining", "watch")

        final_media = f"00:00:{watch_secs:02d}.090"
        s, _ = await self.adsgram_event(session, rec, "complete", TID_COMPLETE, final_media)
        if s != 200:
            for ctid, cmedia in [(TID_COMPLETE, f"00:00:{watch_secs+1:02d}.000"),
                                  (TID_COMPLETE, f"00:00:{watch_secs:02d}.500")]:
                s2, _ = await self.adsgram_event(session, rec, "complete", ctid, cmedia)
                if s2 == 200:
                    s = 200; break
                await asyncio.sleep(0.4)

        await asyncio.sleep(2.0)

        reward_ok = False
        reward_combos = [
            (TID_REWARD, final_media),
            (TID_REWARD, f"00:00:{watch_secs+1:02d}.000"),
            (TID_REWARD, f"00:00:{watch_secs+2:02d}.000"),
            (TID_REWARD, f"00:00:{watch_secs:02d}.500"),
            (TID_REWARD, f"00:00:{watch_secs+5:02d}.000"),
            (TID_REWARD+1, final_media),
            (13, final_media),
        ]
        for rtid, rmedia in reward_combos:
            s, _ = await self.adsgram_event(session, rec, "Reward", rtid, rmedia)
            if s == 200:
                reward_ok = True
                break
            await asyncio.sleep(0.5)

        if reward_ok:
            return True, "ok"
        return True, "ok(reward_skip)"

    # ── GIGAPUB ──
    async def gigapub_adshowed(self, session, adsess):
        url = f"{GIGAPUB_BASE}/v1/ad"
        h = {
            'Accept':"*/*", 'Content-Type':"application/json",
            'Authorization':"Bearer CEEUHXgZVL184wyaDp6laEchjHQ7RNN3",
            'Project-Id':GIGAPUB_PROJECT_ID,
            'User-Agent': self.ua,
            'X-Requested-With':"org.telegram.messenger.web",
            'Origin':APP_URL, 'Referer':f"{APP_URL}/",
            'Sec-Fetch-Site':"cross-site", 'Sec-Fetch-Mode':"cors",
            'Sec-Fetch-Dest':"empty",
        }
        payload = {"method":"adShowed","args":{
            "user":{"user":{
                "id":int(self.USER_INFO["id"]),
                "first_name":self.USER_INFO["first_name"],
                "last_name":"","username":self.USER_INFO["username"],
                "language_code":"en","allows_write_to_pm":True,
                "photo_url":"https://t.me/i/userpic/320/1QB8tmsBAxtjkGa8s1GYkm3v5bqIx_WJnKwnhjm9AYFkltCVyzlsCUkEMllb0KKW.svg",
            },"platform":"android","version":"9.6","start_param":None},
            "placementId":"main","network":"mc","rotationType":"priority",
            "showCounter":1,"transactionId":None,"version":"v87",
            "seconds":3.504,
            "anyData":{
                "showDone":False,
                "fallPriorityList":["mc","rD","rich","monetag","t","rB"],
                "showCounter":0,"fallRotationType":"priority","showTryCounter":2,
                "uniqShowId":f"{int(time.time()*1000)}.{int(time.time()*1000%1000000)}",
                "readyNetsCount":5,"showTag":None,
            },
        }}
        async with session.post(url, json=payload, headers=h,
                timeout=aiohttp.ClientTimeout(total=20)) as r:
            return r.status, await r.text()

    async def watch_gigapub(self, session):
        self.set_ui(provider='gigapub', progress='memulai')
        log("GIGAPUB", "Starting provider...", "info")
        adsess, err = await self.paidz_ads_start(session, "gigapub")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(1)
        self.set_ui(progress='adshowed')
        try:
            await self.gigapub_adshowed(session, adsess)
        except Exception:
            pass
        self.set_ui(progress='nonton 5s')
        log("WATCH", "Watching 5s...", "watch")
        await asyncio.sleep(5)
        s, _ = await self.paidz_ads_watch(session, "gigapub", adsess)
        return (True, "ok") if s == 200 else (False, f"watch {s}")

    # ── MONETIX ──
    async def watch_monetix(self, session):
        self.set_ui(provider='monetix', progress='memulai')
        log("MONETIX", "Starting provider...", "info")
        adsess, err = await self.paidz_ads_start(session, "monetix")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.5)
        self.set_ui(progress='nonton 16s')
        log("WATCH", "Watching 16s...", "watch")
        for i in range(16, 0, -4):
            await asyncio.sleep(4)
            left = max(i - 4, 0)
            self.set_ui(progress=f'nonton {left}s')
            if left > 0:
                log("WATCH", f"{left}s remaining", "watch")
        s, _ = await self.paidz_ads_watch(session, "monetix", adsess)
        return (True, "ok") if s == 200 else (False, f"watch {s}")

    # ── SIMPLE ──
    async def watch_simple(self, session, provider, wait_secs=10):
        self.set_ui(provider=provider, progress='memulai')
        log(provider.upper(), "Starting provider...", "info")
        adsess, err = await self.paidz_ads_start(session, provider)
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.5)
        self.set_ui(progress=f'nonton {wait_secs}s')
        log("WATCH", f"Watching {wait_secs}s...", "watch")
        step = 2
        for i in range(wait_secs, 0, -step):
            await asyncio.sleep(step)
            left = max(i - step, 0)
            self.set_ui(progress=f'nonton {left}s')
            if left > 0:
                log("WATCH", f"{left}s remaining", "watch")
        s, _ = await self.paidz_ads_watch(session, provider, adsess)
        return (True, "ok") if s == 200 else (False, f"watch {s}")

    # ── ADLOOP ──
    ADLOOP_BASE = "https://supabase.adloopnetwork.com/functions/v1"
    ADLOOP_SITE_ID = "SITE-LCEWW3R38Z"
    ADLOOP_SLOT_ID = "125094"

    def get_adloop_headers(self):
        return {
            'Accept': "*/*", 'Content-Type': "application/json",
            'User-Agent': self.ua,
            'X-Requested-With': "org.telegram.messenger.web",
            'Origin': APP_URL, 'Referer': f"{APP_URL}/",
            'Sec-Fetch-Site': "cross-site", 'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty", 'Accept-Language': "en-US,en;q=0.9",
        }

    async def adloop_serve(self, session):
        device = uuid.uuid4().hex[:12]
        url = f"{self.ADLOOP_BASE}/ad-serve"
        payload = {
            "site_id": self.ADLOOP_SITE_ID,
            "slot_id": self.ADLOOP_SLOT_ID,
            "device": device,
            "tg_user_id": int(self.USER_INFO["id"]),
        }
        try:
            async with session.post(url, json=payload,
                    headers=self.get_adloop_headers(),
                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    return None, f"HTTP {r.status}"
                d = await r.json()
                fb = d.get("fallback") or {}
                token = fb.get("token")
                ads = fb.get("ads") or []
                if not token: return None, "no token"
                if not ads: return None, "no ads"
                return {"token": token, "ads": ads}, None
        except Exception as e:
            return None, f"{type(e).__name__}"

    async def adloop_event(self, session, token, etype):
        url = f"{self.ADLOOP_BASE}/ad-event"
        payload = {"token": token, "type": etype}
        try:
            async with session.post(url, json=payload,
                    headers=self.get_adloop_headers(),
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                return r.status, await r.text()
        except Exception as e:
            return 0, f"{type(e).__name__}"

    async def watch_adloop(self, session):
        self.set_ui(provider='adloop', progress='memulai')
        log("ADLOOP", "Starting provider...", "info")

        adsess, err = await self.paidz_ads_start(session, "adloop")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.5)

        self.set_ui(progress='ad-serve')
        served, err = await self.adloop_serve(session)
        if err:
            log("ADLOOP", f"ad-serve: {err}", "err")
            return False, f"serve: {err}"
        token = served["token"]
        log("ADLOOP", f"token ok, {len(served['ads'])} fallback ads", "ok")

        s, _ = await self.adloop_event(session, token, "render")
        if s != 200:
            log("ADLOOP", f"render: HTTP {s}", "err")
        await asyncio.sleep(0.3)

        wait_secs = 17
        self.set_ui(progress=f'nonton {wait_secs}s')
        log("WATCH", f"Watching {wait_secs}s...", "watch")
        for i in range(wait_secs, 0, -3):
            await asyncio.sleep(3)
            left = max(i - 3, 0)
            self.set_ui(progress=f'nonton {left}s')
            if left > 0:
                log("WATCH", f"{left}s remaining", "watch")

        try:
            await self.adloop_event(session, token, "complete")
        except Exception:
            pass

        s, _ = await self.paidz_ads_watch(session, "adloop", adsess)
        return (True, "ok") if s == 200 else (False, f"watch {s}")

    # ── TELEGA.IO ──
    TELEGA_BID_HOST = "https://15209.xml.4armn.com"
    TELEGA_BASE = "https://inapp.telega.io"
    TELEGA_PUBLISHER_ID = "1014157"
    TELEGA_WIDGET_ID = 407491
    TELEGA_AUTH = "4bb9c7d1-82a7-4a93-b902-741aba1f7ee5"

    def get_telega_bid_headers(self):
        return {
            'Accept': "*/*",
            'Content-Type': "text/plain;charset=UTF-8",
            'User-Agent': self.ua,
            'X-Requested-With': "org.telegram.messenger.web",
            'Origin': APP_URL, 'Referer': f"{APP_URL}/",
            'Sec-Fetch-Site': "cross-site", 'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty", 'Accept-Language': "en-US,en;q=0.9",
        }

    def get_telega_hit_headers(self):
        return {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'Authorization': self.TELEGA_AUTH,
            'User-Agent': self.ua,
            'X-Requested-With': "org.telegram.messenger.web",
            'Origin': APP_URL, 'Referer': f"{APP_URL}/",
            'Sec-Fetch-Site': "cross-site", 'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty", 'Accept-Language': "en-US,en;q=0.9",
        }

    async def telega_bid(self, session, fake_ip, lang):
        url = f"{self.TELEGA_BID_HOST}/telegram-bid"
        payload = {
            "publisher_id": self.TELEGA_PUBLISHER_ID,
            "user_agent": self.ua,
            "language_code": lang,
            "premium": False,
            "last_name": "",
            "first_name": self.USER_INFO["first_name"],
            "telegram_id": self.USER_INFO["id"],
            "version": "9.6",
            "platform": "android",
            "motivated": False,
            "ip": fake_ip,
            "number_of_bids": 1,
            "bid_floor": 0.05,
            "widget_id": self.TELEGA_WIDGET_ID,
            "width": None,
            "height": None,
        }
        try:
            async with session.post(url, data=json.dumps(payload),
                    headers=self.get_telega_bid_headers(),
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                return r.status, None
        except Exception as e:
            return 0, f"{type(e).__name__}"

    async def telega_hit(self, session, ad_block_uuid):
        url = f"{self.TELEGA_BASE}/api/public/v1/ad_hit/create"
        payload = {
            "telegram_user_data": self.REAL_INIT_DATA,
            "ad_block_uuid": ad_block_uuid,
            "platform": "android",
        }
        try:
            async with session.post(url, json=payload,
                    headers=self.get_telega_hit_headers(),
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                return r.status, None
        except Exception as e:
            return 0, f"{type(e).__name__}"

    async def watch_telega(self, session):
        self.set_ui(provider='telega', progress='memulai')
        log("TELEGA", "Starting provider...", "info")

        adsess, err = await self.paidz_ads_start(session, "telega")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.5)

        regions = random.sample(REGION_POOL, 4)
        last_err = "no region"
        bid_ok = False
        for i, (country, ip, lang, tz) in enumerate(regions, 1):
            self.set_ui(progress=f'telega {country} ({i}/{len(regions)})')
            log("TELEGA", f"try region {country} ip={ip}", "info")
            status, err = await self.telega_bid(session, ip, lang)
            if err:
                last_err = err
                await asyncio.sleep(0.8)
                continue
            if status in (200, 204):
                log("TELEGA", f"region {country} bid OK ({status})", "ok")
                bid_ok = True
                break
            last_err = f"bid HTTP {status}"
            await asyncio.sleep(0.8)
        if not bid_ok:
            return False, f"bid: {last_err}"

        self.set_ui(progress='ad_hit')
        ad_block_uuid = str(uuid.uuid4())
        s, err = await self.telega_hit(session, ad_block_uuid)
        # ad_hit 404 = OK, gak wajib
        if err:
            log("TELEGA", f"hit: {err} (skip)", "info")
        elif s not in (200, 204, 404):
            log("TELEGA", f"hit: HTTP {s} (skip)", "info")
        else:
            log("TELEGA", "ad_hit OK", "ok")
        await asyncio.sleep(0.5)

        wait_secs = 17
        self.set_ui(progress=f'nonton {wait_secs}s')
        log("WATCH", f"Watching {wait_secs}s...", "watch")
        for i in range(wait_secs, 0, -3):
            await asyncio.sleep(3)
            left = max(i - 3, 0)
            self.set_ui(progress=f'nonton {left}s')
            if left > 0:
                log("WATCH", f"{left}s remaining", "watch")

        s, _ = await self.paidz_ads_watch(session, "telega", adsess)
        return (True, "ok") if s == 200 else (False, f"watch {s}")

    # ── USL ──
    def get_usl_headers(self, secret=None, fake_ip=None, region=None):
        h = {
            'Accept':"*/*", 'Content-Type':"application/json",
            'User-Agent': self.ua,
            'X-Requested-With':"org.telegram.messenger.web",
            'X-TG-INIT-DATA': self.REAL_INIT_DATA,
            'X-TG-USER-ID': self.USER_INFO["id"],
            'X-TG-USERNAME': self.USER_INFO["username"],
            'X-TG-FIRST-NAME': self.USER_INFO["first_name"],
            'X-TG-LANGUAGE-CODE': self.USER_INFO["language_code"],
            'Origin':APP_URL, 'Referer':f"{APP_URL}/",
            'Sec-Fetch-Site':"cross-site", 'Sec-Fetch-Mode':"cors",
            'Sec-Fetch-Dest':"empty", 'Accept-Language':"en-US,en;q=0.9",
        }
        if fake_ip:
            h['X-Forwarded-For'] = f"{fake_ip}, {fake_ip}"
            h['X-Real-IP'] = fake_ip
            h['X-Client-IP'] = fake_ip
            h['CF-Connecting-IP'] = fake_ip
            h['True-Client-IP'] = fake_ip
            h['X-Originating-IP'] = fake_ip
            h['X-Remote-Addr'] = fake_ip
            h['Forwarded'] = f"for={fake_ip};proto=https"
        if region:
            h['X-Country-Code'] = region
            h['CF-IPCountry'] = region
        if secret:
            h['X-USL-Player-Secret']=secret
            h['Origin']=USL_BASE; h['Referer']=f"{USL_BASE}/"
            h['Sec-Fetch-Site']="same-origin"
        return h

    async def usl_request(self, session, fake_ip=None, region=None):
        url = f"{USL_BASE}/tower-ads/request"
        enc = quote(self.REAL_INIT_DATA, safe='')
        ref = (f"{APP_URL}/#tgWebAppData={enc}"
               f"&tgWebAppVersion=9.6&tgWebAppPlatform=android"
               f"&tgWebAppThemeParams=%7B%22bg_color%22%3A%22%23212d3b%22%7D")
        payload = {"api_key":USL_API_KEY,"placement_id":USL_PLACEMENT_ID,
                   "sdk_forensic":None,
                   "user_data":{"device":"mobile","os":"android",
                                "user_agent":self.ua,"referer":ref}}
        try:
            async with session.post(url, json=payload,
                    headers=self.get_usl_headers(fake_ip=fake_ip, region=region),
                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                body = await r.text()
                if r.status != 200: return None, None, None, f"HTTP {r.status}"
                try: d = json.loads(body)
                except Exception: return None, None, None, f"JSON: {body[:60]}"
                if not d.get("success"):
                    err = (d.get("error") or d.get("code")
                           or d.get("message") or "not_success")
                    return None, None, None, str(err)
                return d.get("secure_player", {}), d.get("ad", {}), d.get("impression_id"), None
        except Exception as e:
            return None, None, None, f"{type(e).__name__}"

    async def usl_secret(self, session, sid, fake_ip=None, region=None):
        try:
            async with session.get(f"{USL_BASE}/api/secure-player/{sid}",
                    headers=self.get_usl_headers(fake_ip=fake_ip, region=region),
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200: return None, f"HTTP {r.status}"
                html = await r.text()
                m = re.search(r'playerSecret\s*=\s*["\']([^"\']+)["\']', html)
                if not m: return None, "no secret"
                return m.group(1), None
        except Exception as e:
            return None, f"{type(e).__name__}"

    async def usl_post(self, session, sid, secret, path, body):
        try:
            async with session.post(f"{USL_BASE}/secure-player/{sid}/{path}",
                    json=body, headers=self.get_usl_headers(secret),
                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                txt = await r.text()
                try: return r.status, json.loads(txt)
                except Exception: return r.status, {"_raw": txt[:200]}
        except Exception as e:
            return 0, {"_err": f"{type(e).__name__}"}

    async def watch_usl(self, session):
        self.set_ui(provider='usl', progress='memulai')
        log("USL", "Starting provider...", "info")

        adsess, err = await self.paidz_ads_start(session, "usl")
        if err: return False, f"start: {err}"
        if not adsess: return False, "start: no adsess"
        await asyncio.sleep(0.5)

        regions = random.sample(REGION_POOL, 6)
        sp = ad = imp_id = None
        last_err = "empty"
        used_ip = None
        used_region = None

        for i, (country, ip, lang, tz) in enumerate(regions, 1):
            self.set_ui(progress=f'usl {country} ({i}/{len(regions)})')
            log("USL", f"try region {country}", "info")
            sp, ad, imp_id, err = await self.usl_request(session, fake_ip=ip, region=country)
            if err is None and sp:
                log("USL", f"region {country} OK", "ok")
                used_ip = ip
                used_region = country
                break
            last_err = str(err) if err else "empty"
            log("USL", f"region {country}: {last_err[:30]}", "err")

            # kalau 429 → langsung return, biar cooldown
            if "429" in last_err:
                return False, "RATE_LIMIT:60"

            await asyncio.sleep(2.5)

        if not sp:
            return False, f"usl req: {last_err}"

        sid = sp.get("session_id")
        close_at = ad.get("close_available_at", 19)

        self.set_ui(progress='ambil secret')
        secret, err = await self.usl_secret(session, sid, fake_ip=used_ip, region=used_region)
        if err: return False, f"secret: {err}"

        await asyncio.sleep(0.5)
        s, _ = await self.usl_post(session, sid, secret, "start", {})
        if s != 200: return False, f"start {s}"

        self.set_ui(progress=f'nonton 0/{close_at}s')
        log("WATCH", f"Watching {close_at}s...", "watch")
        pos = 0
        while pos < close_at:
            pos += 2
            if pos > close_at: pos = close_at
            self.set_ui(progress=f'nonton {pos}/{close_at}s')
            try:
                await self.usl_post(session, sid, secret, "heartbeat",
                                     {"position_seconds":pos})
            except Exception:
                pass
            await asyncio.sleep(2)

        await asyncio.sleep(3)
        self.set_ui(progress='selesai')
        final_pos = float(close_at) + 2.0
        reward = False
        for att in range(1, 4):
            try:
                s, d = await self.usl_post(session, sid, secret, "finish",
                                            {"position_seconds":final_pos})
                if s == 200 and d.get("reward_granted"):
                    reward = True; break
                if att < 3:
                    final_pos += 1.0; await asyncio.sleep(3)
            except Exception:
                await asyncio.sleep(3)
        if not reward: return False, "no reward"

        try:
            async with session.post(f"{USL_BASE}/tower-ads/provider-result-batch",
                    json={"impression_id":imp_id,
                          "attempts":[{"provider":"usl","status":"filled"}],
                          "served_provider":"usl"},
                    headers=self.get_usl_headers(),
                    timeout=aiohttp.ClientTimeout(total=20)) as r:
                pass
        except Exception:
            pass

        return True, "ok"

    async def watch_provider(self, session, provider):
        try:
            if provider == "adloop":    return await self.watch_adloop(session)
            if provider == "adsgram":   return await self.watch_adsgram(session)
            if provider == "gigapub":   return await self.watch_gigapub(session)
            if provider == "monetix":   return await self.watch_monetix(session)
            if provider == "telega":    return await self.watch_telega(session)
            if provider == "usl":       return await self.watch_usl(session)
            return await self.watch_simple(session, provider)
        except Exception as e:
            return False, f"{type(e).__name__}"

    def _apply_cooldown(self, provider, wait_secs, reason=""):
        self.cooldowns[provider] = time.time() + wait_secs
        log("RATE", f"{PROVIDER_LABEL[provider]}: cooldown {wait_secs}s {reason}".strip(), "err")

    async def run(self, all_prog):
        self.acc_prog = ensure_account_entry(all_prog, self.name)

        if not await self.login():
            await self.cleanup()
            return
        if not await self.get_init_data():
            await self.cleanup()
            return

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        ) as session:
            if not await self.auth(session):
                self.set_ui(status='error', progress='auth gagal')
                await self.cleanup()
                return

            self.set_ui(status='farming')
            self.set_ui(progress='warming up...')
            log("SYSTEM", f"Warming up {WARMUP_SECONDS}s...", "info")
            await asyncio.sleep(WARMUP_SECONDS)
            log("SYSTEM", "Warmup done, mulai farming", "ok")

            while True:
                if all(remaining(self.acc_prog, p) <= 0 for p in LIMITS):
                    self.set_ui(status='done', provider='-', progress='SEMUA SELESAI')
                    log("SYSTEM", "Semua provider selesai", "ok")
                    break
                if time.time() - self.start_time > PER_ACCOUNT_TIMEOUT:
                    self.set_ui(status='done', progress='TIMEOUT')
                    log("SYSTEM", "Timeout tercapai", "err")
                    break

                any_attempted = False

                for provider in PROVIDER_ORDER:
                    rem = remaining(self.acc_prog, provider)
                    if rem <= 0: continue

                    cd_until = self.cooldowns.get(provider, 0)
                    now_ts = time.time()
                    if cd_until > now_ts:
                        sisa = int(cd_until - now_ts)
                        log("SKIP", f"{PROVIDER_LABEL[provider]}: cooldown {sisa}s", "info")
                        continue

                    any_attempted = True
                    ok_, msg = await self.watch_provider(session, provider)

                    if ok_:
                        self.acc_prog["providers"][provider] += 1
                        UI_STATS["claims"] += 1
                        UI_STATS["success"] += 1
                        self.cooldowns.pop(provider, None)
                        self.fail_streak.pop(provider, None)
                        used = self.acc_prog["providers"][provider]
                        self.set_ui(progress=f'{provider} {used}/{LIMITS[provider]}')
                        log("SUCCESS",
                            f"{PROVIDER_LABEL[provider]} {used}/{LIMITS[provider]}",
                            "ok")
                        await save_all_progress(all_prog)
                    else:
                        UI_STATS["claims"] += 1
                        UI_STATS["failures"] += 1

                        if "RATE_LIMIT:" in msg:
                            wait = int(msg.split("RATE_LIMIT:")[1])
                            self._apply_cooldown(provider, wait, "(rate limit)")
                            self.set_ui(progress=f'{provider}: cooldown {wait}s')
                        elif msg == "NO_BANNERS":
                            self._apply_cooldown(provider, COOLDOWN_NO_BANNERS, "(no banners)")
                            self.set_ui(progress=f'{provider}: no banners')
                        else:
                            streak = self.fail_streak.get(provider, 0) + 1
                            self.fail_streak[provider] = streak
                            if streak >= FAIL_STREAK_THRESHOLD:
                                self._apply_cooldown(provider,
                                    COOLDOWN_FAIL_STREAK, f"(fail x{streak})")
                                self.fail_streak[provider] = 0
                            self.set_ui(progress=f'{provider}: {msg[:18]}')
                            log("FAIL",
                                f"{PROVIDER_LABEL[provider]}: {msg[:30]}",
                                "err")

                    await asyncio.sleep(random.uniform(3, 6))

                await self.refresh(session)

                if not any_attempted:
                    log("SYSTEM", "Semua provider cooldown, tunggu 30s...", "info")
                    await asyncio.sleep(30)

        await self.cleanup()
        self.set_ui(status='done', progress='selesai')

    async def cleanup(self):
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None


# ═══════════════════════════════════════════════════════════
# BOX DRAWING
# ═══════════════════════════════════════════════════════════
def _visible_len(s: str) -> int:
    return len(re.sub(r'\033\[[0-9;]*m', '', s))

def _pad(s: str, width: int) -> str:
    vl = _visible_len(s)
    if vl > width:
        plain = re.sub(r'\033\[[0-9;]*m', '', s)
        return plain[:width]
    return s + (' ' * (width - vl))

def _box_top(label: str = "") -> str:
    if label:
        pad = BOX_WIDTH - 2 - len(label) - 2
        return (f"{C.LIME}╔═ {C.LIME2}{label}{C.LIME} "
                + ("═" * max(pad, 0)) + "╗" + C.RESET)
    return f"{C.LIME}╔{'═' * (BOX_WIDTH - 2)}╗{C.RESET}"

def _box_mid(label: str = "") -> str:
    if label:
        pad = BOX_WIDTH - 2 - len(label) - 2
        return (f"{C.LIME}╠═ {C.LIME3}{label}{C.LIME} "
                + ("═" * max(pad, 0)) + "╣" + C.RESET)
    return f"{C.LIME}╠{'═' * (BOX_WIDTH - 2)}╣{C.RESET}"

def _box_bot() -> str:
    return f"{C.LIME}╚{'═' * (BOX_WIDTH - 2)}╝{C.RESET}"

def _box_line(content: str) -> str:
    inner_width = BOX_WIDTH - 4
    return f"{C.LIME}║{C.RESET} {_pad(content, inner_width)} {C.LIME}║{C.RESET}"

def _bar(used: int, total: int, width: int = 18) -> str:
    if total <= 0:
        return "░" * width
    filled = int(round(width * (used / total)))
    filled = max(0, min(width, filled))
    empty = width - filled
    pct = used / total if total else 0
    if pct >= 0.7: color = C.LIME2
    elif pct >= 0.4: color = C.LIME3
    else: color = C.YELLOW
    return f"{color}{'█' * filled}{C.GREY}{'░' * empty}{C.RESET}"

def _fmt_runtime(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600; m = (s % 3600) // 60; sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


# ═══════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════
def banner_lime():
    print(f"{C.LIME}")
    print(f"  ██████╗  █████╗ ██╗██████╗ ███████╗")
    print(f"  ██╔══██╗██╔══██╗██║██╔══██╗╚══███╔╝")
    print(f"  ██████╔╝███████║██║██║  ██║  ███╔╝ ")
    print(f"  ██╔═══╝ ██╔══██║██║██║  ██║ ███╔╝  ")
    print(f"  ██║     ██║  ██║██║██████╔╝███████╗")
    print(f"  ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚══════╝")
    print(f"{C.LIME2}")
    print(f"      💙  B L U E   E D I T I O N  💙")
    print(f"{C.LIME3}")
    print(f"      ──────────────────────────────────────────")
    print(f"      ⚡ SOUU ENGINE • v13 • Single Session ⚡")
    print(f"      ──────────────────────────────────────────")
    print(f"{C.RESET}")


# ═══════════════════════════════════════════════════════════
# RENDER PANEL
# ═══════════════════════════════════════════════════════════
def _status_text(status: str) -> str:
    if status == 'done': return f"{C.LIME2}FARMED ✓{C.RESET}"
    if status == 'error': return f"{C.RED}ERROR{C.RESET}"
    if status == 'farming': return f"{C.LIME}FARMING{C.RESET}"
    if status == 'login': return f"{C.YELLOW}LOGIN{C.RESET}"
    return f"{C.DIM}INIT{C.RESET}"

def _log_color(kind: str):
    return {"info": C.CYAN, "watch": C.LIME3, "ok": C.LIME2,
            "err": C.RED, "bal": C.YELLOW}.get(kind, C.WHITE)

def _log_icon(kind: str) -> str:
    return {"info": "◈", "watch": "⬢", "ok": "✓",
            "err": "✗", "bal": "◈"}.get(kind, "◈")


def draw_screen(ui_states):
    os.system('clear' if os.name == 'posix' else 'cls')

    acc = ui_states[0]
    balance = acc.get('balance', 0) or 0
    ads = acc.get('ads', 0) or 0
    status = acc.get('status', 'init')
    acc_prog = acc.get('_acc_prog') or {}

    print(_box_top())
    print(_box_line(f"{C.LIME2}{C.BOLD}PAIDZ AUTO FARM{C.RESET}"))
    print(_box_line(f"{C.LIME3}─────── SOUU ENGINE ───────{C.RESET}"))

    print(_box_mid("TELEGRAM"))
    print(_box_line(f"{C.LIME}├─ User       {C.WHITE}: {C.LIME2}{USER_META['username']}{C.RESET}"))
    print(_box_line(f"{C.LIME}├─ Name       {C.WHITE}: {C.LIME2}{USER_META['name']}{C.RESET}"))
    print(_box_line(f"{C.LIME}└─ Session    {C.WHITE}: {C.LIME2}{USER_META['session']}{C.RESET}"))

    print(_box_mid("ACCOUNT"))
    print(_box_line(f"{C.LIME}├─ Balance    {C.WHITE}: {C.YELLOW}{balance:.4f} coins{C.RESET}"))
    print(_box_line(f"{C.LIME}├─ Ads        {C.WHITE}: {C.YELLOW}{ads}{C.RESET}"))
    print(_box_line(f"{C.LIME}└─ Status     {C.WHITE}: {_status_text(status)}"))

    print(_box_mid("PROVIDERS"))
    for i, p in enumerate(PROVIDER_ORDER):
        used = acc_prog.get("providers", {}).get(p, 0)
        total = LIMITS[p]
        label = PROVIDER_LABEL[p]
        branch = "└─" if i == len(PROVIDER_ORDER) - 1 else "├─"
        bar = _bar(used, total, 18)
        count = f"{used:03d} / {total:03d}"
        line = (f"{C.LIME}{branch} {C.WHITE}{label:<9}{C.RESET} "
                f"{C.GREY}:{C.RESET} {C.LIME3}{count}{C.RESET}  {bar}")
        print(_box_line(line))

    print(_box_mid("SYSTEM"))
    runtime = _fmt_runtime(time.time() - START_TS)
    max_rt = _fmt_runtime(PER_ACCOUNT_TIMEOUT)
    print(_box_line(f"{C.LIME}├─ Claims     {C.WHITE}: {C.LIME2}{UI_STATS['claims']}{C.RESET}"))
    print(_box_line(f"{C.LIME}├─ Success    {C.WHITE}: {C.LIME2}{UI_STATS['success']}{C.RESET}"))
    print(_box_line(f"{C.LIME}├─ Failures   {C.WHITE}: {C.RED}{UI_STATS['failures']}{C.RESET} {C.GREY}/ 20{C.RESET}"))
    print(_box_line(f"{C.LIME}└─ Runtime    {C.WHITE}: {C.CYAN}{runtime}{C.RESET} {C.GREY}/ {max_rt}{C.RESET}"))

    print(_box_mid())
    logs = list(LOG_BUFFER)
    while len(logs) < LOG_LINES_MAX:
        logs.append(("--:--:--", "", "", "info"))
    for ts, tag, msg, kind in logs[-LOG_LINES_MAX:]:
        color = _log_color(kind)
        icon = _log_icon(kind)
        if not tag:
            line = f"{C.DIM}[{ts}]   ...{C.RESET}"
        else:
            line = (f"{C.GREY}[{ts}]{C.RESET} {color}{icon}{C.RESET} "
                    f"{C.LIME3}{tag:<8}{C.RESET} {color}{msg}{C.RESET}")
        print(_box_line(line))

    print(_box_bot())

    now = time.strftime("%H:%M:%S")
    print(f"\n   {C.LIME2}BOT RUNNING{C.RESET} {C.GREY}•{C.RESET} {C.LIME3}{now}{C.RESET}")
    print(f"   {C.GREY}By Power {C.LIME}@SouuXso{C.GREY} • {C.LIME2}PAIDZ Edition{C.RESET}\n")
    sys.stdout.flush()


async def display_loop(ui_states, stop_event):
    while not stop_event.is_set():
        try: draw_screen(ui_states)
        except Exception: pass
        await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
async def ask_confirm(prompt, default="y"):
    loop = asyncio.get_event_loop()
    try:
        v = await loop.run_in_executor(None, input, prompt)
        v = v.strip().lower() or default
        return v in ('y', 'ya', 'yes', '1', 'true')
    except Exception:
        return False


async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    banner_lime()

    name = SESSION_NAME

    if not session_exists() or not session_is_valid_size():
        if session_exists():
            print(f"{C.YELLOW}⚠️  Session corrupt, hapus...{C.RESET}")
            try: os.remove(SESSION_PATH + ".session")
            except: pass
            _nuke_session_journals(SESSION_PATH)

        ok = await login_interaktif()
        if not ok:
            print(f"{C.RED}❌ Login gagal. Keluar.{C.RESET}")
            return
    else:
        print(f"{C.LIME2}✅ Session ditemukan: {C.WHITE}{SESSION_PATH}.session{C.RESET}\n")

    all_prog = load_all_progress()
    today = _today()
    acc_prog = all_prog.get(name)

    if acc_prog and acc_prog.get("date") == today:
        if all(acc_prog["providers"].get(p, 0) >= LIMITS[p] for p in LIMITS):
            print(f"{C.LIME2}✅ Akun ini sudah selesai untuk hari ini.{C.RESET}")
            ulang = await ask_confirm(
                f"{C.YELLOW}Ulang dari awal? (y/N): {C.RESET}", "n")
            if not ulang:
                return
            all_prog[name] = {"date": today, "providers": {p: 0 for p in LIMITS}}
            await save_all_progress(all_prog)
            print(f"{C.LIME2}🔄 Progress di-reset.{C.RESET}\n")

    print(f"{C.LIME}▶️  Mulai farming...{C.RESET}\n")
    await asyncio.sleep(1.5)

    LOG_BUFFER.clear()
    UI_STATS["claims"] = 0
    UI_STATS["success"] = 0
    UI_STATS["failures"] = 0

    ui_states = [{
        'name': name, 'status': 'init', 'provider': '-',
        'progress': 'inisialisasi', 'balance': 0, 'ads': 0,
        '_acc_prog': ensure_account_entry(all_prog, name),
    }]

    stop_event = asyncio.Event()
    display_task = asyncio.create_task(display_loop(ui_states, stop_event))

    try:
        runner = PaidzAccount(SESSION_PATH, name, ui_states[0])
        await runner.run(all_prog)
    except Exception as e:
        ui_states[0]['status'] = 'error'
        ui_states[0]['progress'] = f'{type(e).__name__}'
        log("SYSTEM", f"crash: {type(e).__name__}", "err")

    stop_event.set()
    await asyncio.sleep(0.5)
    display_task.cancel()
    try: await display_task
    except Exception: pass

    draw_screen(ui_states)

    st = ui_states[0]
    print(f"\n{C.LIME}╔{'═'*60}╗{C.RESET}")
    if st['status'] == 'done':
        print(f"{C.LIME}║{C.LIME2}  ✅ SELESAI — {name:<40}{C.LIME}║{C.RESET}")
    else:
        print(f"{C.LIME}║{C.RED}  ❌ {st['status'].upper()} — {name:<40}{C.LIME}║{C.RESET}")
    print(f"{C.LIME}║{C.WHITE}  Saldo: {C.LIME2}{st['balance']:.4f}{C.WHITE} coins  |  Iklan: {C.LIME2}{st['ads']}{(' '*14)}{C.LIME}║{C.RESET}")
    print(f"{C.LIME}╚{'═'*60}╝{C.RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.RED}⛔ Dihentikan.{C.RESET}")
        _nuke_session_journals(SESSION_PATH)
        sys.exit(0)
