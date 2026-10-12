#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  METASFASBOT Auto Farmer — Telethon + SouuEngine Edition v2.0
  - Telethon: multi akun, auto /start reff, auto open mini app
  - Task engine: retry + exponential backoff (fix too_soon)
  - Continuous loop: cooldown ~1h → ulang otomatis
  - SouuEngine panel: log queue, spinner, live stats
═══════════════════════════════════════════════════════════════

  INSTALL:
    pip install telethon requests

  SETUP:
    1. Ambil api_id & api_hash dari https://my.telegram.org
    2. Taruh di config bawah (atau .env)
    3. Jalanin: python meta_farmer_telethon.py
    4. Pilih menu → Telethon auth
"""

import os
import sys
import json
import time
import signal
import random
import hashlib
import asyncio
import subprocess
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse, urlencode

try:
    import requests
    from telethon import TelegramClient, functions, types
    from telethon.sessions import StringSession
    from telethon.errors import (
        SessionPasswordNeededError,
        PhoneCodeInvalidError,
        FloodWaitError,
        UserAlreadyParticipantError,
    )
    from telethon.tl.functions.messages import RequestWebViewRequest
except ImportError as e:
    print(f"Install dulu: pip install telethon requests\nMissing: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
#  COLORS + HELPERS
# ═══════════════════════════════════════════════════════════════
RST="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
RED="\033[38;5;196m"; GRN="\033[38;5;46m"; YEL="\033[38;5;226m"
CYN="\033[38;5;51m";  MAG="\033[38;5;201m"; ORG="\033[38;5;208m"
WHT="\033[38;5;15m";  GRY="\033[38;5;240m"; VIO="\033[38;5;141m"

def vlen(s): return len(re.sub(r'\033\[[0-9;]*m', '', s))
def pad_to(s, w): return s + " " * max(0, w - vlen(s))
def fmt_dur(s):
    s = max(0, int(s))
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
def ts_ms(): return int(time.time() * 1000)
def now_str(): return datetime.now().strftime("%H:%M:%S")
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
API_ID   = 0          # <-- ISI DARI my.telegram.org
API_HASH = ""         # <-- ISI DARI my.telegram.org

BASE_HOST = "https://metasfasbot.ih0st.app"
TID = 1293
BOT_USERNAME = "METASFASBOT"
BOT_URL = f"https://t.me/{BOT_USERNAME}"
MINI_APP_URL = f"{BASE_HOST}/?tid={TID}"
UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
      "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(SCRIPT_DIR, "sessions")
ACCOUNTS_FILE = os.path.join(SCRIPT_DIR, "meta_accounts.json")
REF_CONFIG_FILE = os.path.join(SCRIPT_DIR, "meta_ref.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "meta_bot.log")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# FIX too_soon: makin lama makin naik
TASK_OPEN_DELAY_BASE = 12     # detik awal (server butuh >= 10s biasanya)
TASK_OPEN_DELAY_MAX  = 45     # cap biar gak kelamaan
BETWEEN_TASKS = 4
COOLDOWN_FALLBACK = 3600
MAX_TASK_RETRIES = 4

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════
STATE = {
    'mode': '-', 'phase': 'idle', 'cycle': 0,
    'acc_total': 0, 'acc_idx': 0, 'current_acc': '-',
    'current_bal': 0.0, 'earned_total': 0.0,
    'tasks_done': 0, 'tasks_failed': 0,
    'task_pending': 0, 'task_current': '-', 'task_retry': 0,
    'cooldown_end': 0, 'runtime_start': time.time(),
    'logs': [], 'menu_hint': 'idle',
    'ref_master': 0, 'ref_link': '-', 'ref_total': 0, 'ref_active': 0,
}

TAG_MAP = {
    'OK':GRN+"● OK    "+RST, 'ERR':RED+"● ERR   "+RST, 'WARN':YEL+"● WARN  "+RST,
    'INFO':GRY+"● INFO  "+RST, 'TASK':MAG+"◉ TASK  "+RST, 'OPEN':CYN+"◉ OPEN  "+RST,
    'VERIFY':VIO+"◉ VERIFY"+RST, 'WAIT':ORG+"◉ WAIT  "+RST, 'AUTH':GRN+"● AUTH  "+RST,
    'ACC':CYN+"◉ ACC   "+RST, 'REFF':YEL+"◉ REFF  "+RST, 'MENU':VIO+"◉ MENU  "+RST,
    'TG':MAG+"◉ TG    "+RST, 'RETRY':ORG+"◉ RETRY "+RST,
}

def slog(msg, level='INFO'):
    tag = TAG_MAP.get(level.upper(), TAG_MAP['INFO'])
    STATE['logs'].append(f"{GRY}[{now_str()}] {RST}{tag} {WHT}{msg}{RST}")
    if len(STATE['logs']) > 8: STATE['logs'].pop(0)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][{level}] {msg}\n")
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════
def line(content, W=62):
    return CYN+"║"+RST+pad_to(" "+content, W)+CYN+"║"+RST

def render():
    W=62; bd=CYN
    top=bd+"╔"+"═"*W+"╗"+RST
    mid=bd+"╠"+"═"*W+"╣"+RST
    bot=bd+"╚"+"═"*W+"╝"+RST

    print("\n"+top)
    print(line(BOLD+WHT+"METASFASBOT AUTO FARMER"+RST))
    print(line(DIM+"─────── Telethon + SouuEngine v2.0 ───────"+RST))
    print(mid)

    ph=STATE['phase'].upper(); phc=GRY
    if STATE['phase']=='running': phc=GRN
    elif STATE['phase']=='cooldown': phc=ORG

    print(line(VIO+"RUN"+RST))
    print(line(f"├─ Mode     : {CYN}{STATE['mode'].upper()}{RST}"))
    print(line(f"├─ Phase    : {phc}{ph}{RST}"))
    print(line(f"└─ Cycle    : {YEL}{STATE['cycle']}{RST}"))
    print(mid)

    print(line(VIO+"ACCOUNT"+RST))
    print(line(f"├─ Total    : {GRN}{STATE['acc_total']} akun{RST}"))
    print(line(f"├─ Current  : {WHT}{STATE['current_acc']}{RST}"))
    print(line(f"├─ Index    : {CYN}{STATE['acc_idx']}/{STATE['acc_total']}{RST}"))
    print(line(f"└─ Balance  : {GRN}{STATE['current_bal']:.6f} GRAM{RST}"))
    print(mid)

    print(line(VIO+"REFERRAL"+RST))
    ms = f"{WHT}{STATE['ref_master']}{RST}" if STATE['ref_master'] else f"{DIM}-{RST}"
    ls = f"{CYN}{STATE['ref_link']}{RST}" if STATE['ref_link']!='-' else f"{DIM}-{RST}"
    print(line(f"├─ Master   : {ms}"))
    print(line(f"├─ Link     : {ls}"))
    print(line(f"├─ Total    : {YEL}{STATE['ref_total']} refs{RST}"))
    print(line(f"└─ Active   : {GRN}{STATE['ref_active']} valid{RST}"))
    print(mid)

    print(line(VIO+"TASK"+RST))
    rtr = f" {ORG}(retry {STATE['task_retry']}){RST}" if STATE['task_retry'] else ""
    print(line(f"├─ Current  : {YEL}{STATE['task_current']}{RST}{rtr}"))
    print(line(f"├─ Pending  : {CYN}{STATE['task_pending']}{RST}"))
    print(line(f"├─ Done     : {GRN}{STATE['tasks_done']}{RST}"))
    print(line(f"└─ Failed   : {RED}{STATE['tasks_failed']}{RST}"))
    print(mid)

    run = int(time.time()-STATE['runtime_start'])
    print(line(VIO+"SYSTEM"+RST))
    print(line(f"├─ Earned   : {GRN}+{STATE['earned_total']:.6f} GRAM{RST}"))
    print(line(f"├─ Runtime  : {CYN}{fmt_dur(run)}{RST}"))
    if STATE['phase']=='cooldown' and STATE['cooldown_end']>time.time():
        print(line(f"└─ Cooldown : {ORG}{fmt_dur(STATE['cooldown_end']-time.time())}{RST}"))
    else:
        print(line(f"└─ Cooldown : {DIM}-{RST}"))
    print(mid)

    if not STATE['logs']:
        print(line(DIM+"─ no activity yet ─"+RST))
    else:
        for l in STATE['logs']: print(line(l))
    print(bot)
    print(f"\n   {GRN}SOUU ENGINE{RST} {DIM}•{RST} {CYN}{now_str()}{RST}   {DIM}{STATE['menu_hint']}{RST}\n")

def clear_render():
    clear_screen(); render()

# ═══════════════════════════════════════════════════════════════
#  STORAGE
# ═══════════════════════════════════════════════════════════════
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE): return []
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception: return []

def save_accounts(a):
    try:
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(a, f, indent=2, ensure_ascii=False)
        os.chmod(ACCOUNTS_FILE, 0o600)
    except Exception as e:
        slog(f"save error: {e}", 'ERR')

def load_ref_config():
    if not os.path.exists(REF_CONFIG_FILE): return {'master': 0}
    try:
        with open(REF_CONFIG_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {'master': 0}
    except Exception: return {'master': 0}

def save_ref_config(c):
    try:
        with open(REF_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(c, f, indent=2)
        os.chmod(REF_CONFIG_FILE, 0o600)
    except Exception: pass

def get_master_ref(): return int(load_ref_config().get('master', 0))
def set_master_ref(tgid): save_ref_config({'master': tgid, 'set_at': datetime.now().isoformat()})
def build_ref_link(tgid): return f"{BOT_URL}?start={tgid}"

def open_url(url):
    try:
        if os.name == 'nt': os.startfile(url)
        elif sys.platform == 'darwin': subprocess.Popen(['open', url])
        else: subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e: slog(f"open_url: {e}", 'ERR')

# ═══════════════════════════════════════════════════════════════
#  HTTP (buat mini app API)
# ═══════════════════════════════════════════════════════════════
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception: pass

def http_post(path, payload, timeout=30):
    url = BASE_HOST + path
    headers = {
        "Content-Type":"application/json", "Accept":"*/*",
        "Origin":BASE_HOST, "Referer":BASE_HOST+"/",
        "X-Requested-With":"org.telegram.messenger.web",
        "User-Agent":UA,
        "Accept-Language":"id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=timeout, verify=False)
            return r.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            if attempt == 2:
                slog(f"HTTP-ERR {path}: {e}", 'ERR'); return None
            time.sleep(1.5 * (attempt+1))

def gen_fp(tgid):
    uid = hashlib.md5(f"{tgid}{random.randint(0,999999)}".encode()).hexdigest()[:40]
    return {
        "uid":uid, "sw":384, "sh":832, "dpr":2.8125,
        "cd":24, "tz":"Asia/Jakarta", "tzo":-420,
        "lang":"id", "langs":"id,id-ID,en-US",
        "plat":"Linux aarch64", "hc":8, "dm":8, "tp":5,
        "webgl":"Samsung Electronics Co., Ltd.|ANGLE ((Samsung Xclipse 530) on Vulkan 1.3.279)",
        "cv":"7S+uUQAAAAZJREFUAwCxiYdbdTPkbgAAAABJRU5ErkJggg==",
    }

def api_auth(init_data, tgid):
    return http_post(f"/miniapp/auth?tid={TID}", {"initData":init_data,"tid":TID,"fp":gen_fp(tgid)})
def api_state(init_data):
    return http_post(f"/miniapp/turbogram/state?tid={TID}", {"initData":init_data})
def api_open(init_data, task_id):
    return http_post(f"/miniapp/turbogram/open?tid={TID}", {"taskId":task_id,"initData":init_data})
def api_task(init_data, task_id):
    return http_post(f"/miniapp/turbogram/task?tid={TID}", {"taskId":task_id,"initData":init_data})
def api_claim(init_data):
    return http_post(f"/miniapp/claim?tid={TID}", {"initData":init_data,"tid":TID})

# ═══════════════════════════════════════════════════════════════
#  TELETHON — initData GRABBER
# ═══════════════════════════════════════════════════════════════
async def telethon_get_initdata(client, bot_username, start_param=""):
    """
    Buka WebView ke mini app via MTProto dan extract initData dari URL.
    """
    try:
        bot_entity = await client.get_entity(bot_username)
    except Exception as e:
        slog(f"get_entity {bot_username}: {e}", 'ERR'); return None

    # kirim /start dengan param kalo ada
    start_cmd = "/start" + (f" {start_param}" if start_param else "")
    try:
        await client.send_message(bot_entity, start_cmd)
        await asyncio.sleep(2)
    except Exception as e:
        slog(f"send /start: {e}", 'ERR')

    # cari pesan bot terakhir yang ada tombol web_app
    init_data = None
    try:
        messages = await client.get_messages(bot_entity, limit=5)
        for msg in messages:
            if not msg or not msg.reply_markup: continue
            # cek inline keyboard
            rows = getattr(msg.reply_markup, 'rows', [])
            for row in rows:
                for btn in row.buttons:
                    web_app = getattr(btn, 'web_app', None) or getattr(btn, 'url', None)
                    if not web_app: continue

                    if hasattr(web_app, 'url'): url = web_app.url
                    else: url = web_app

                    # request web view via MTProto
                    try:
                        result = await client(RequestWebViewRequest(
                            peer=bot_entity,
                            bot=bot_entity,
                            platform='android',
                            from_bot_menu=False,
                            url=url,
                        ))
                        # result.url biasanya mengandung #tgWebAppData=...
                        if hasattr(result, 'url') and 'tgWebAppData=' in result.url:
                            frag = result.url.split('#',1)[1] if '#' in result.url else ''
                            q = parse_qs(frag)
                            if 'tgWebAppData' in q:
                                init_data = q['tgWebAppData'][0]
                                slog(f"initData captured ({len(init_data)} chars)", 'TG')
                                return init_data
                    except Exception as e:
                        slog(f"RequestWebView: {e}", 'WARN')
                        continue
    except Exception as e:
        slog(f"get_messages: {e}", 'ERR')

    return init_data

async def telethon_send_start(client, bot_username, start_param=""):
    """Kirim /start dengan referral param."""
    try:
        bot_entity = await client.get_entity(bot_username)
        await client.send_message(bot_entity, f"/start {start_param}" if start_param else "/start")
        return True
    except Exception as e:
        slog(f"send_start: {e}", 'ERR')
        return False

# ═══════════════════════════════════════════════════════════════
#  TELETHON — SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════
async def telethon_login_flow(phone, session_name=None):
    """
    Login flow lengkap: phone → code → (2FA).
    Return: (client, session_string) atau (None, None).
    """
    if not API_ID or not API_HASH:
        slog("API_ID/API_HASH belum di-set!", 'ERR'); return None, None

    session_name = session_name or phone.replace('+', '')
    session_path = os.path.join(SESSIONS_DIR, session_name)
    client = TelegramClient(session_path, API_ID, API_HASH)

    try:
        await client.connect()
    except Exception as e:
        slog(f"connect: {e}", 'ERR'); return None, None

    if await client.is_user_authorized():
        slog(f"session valid: {session_name}", 'OK')
        try:
            me = await client.get_me()
            return client, StringSession.save(client.session) if hasattr(client.session, 'save') else None, me
        except Exception:
            return client, None, None

    try:
        sent = await client.send_code_request(phone)
        code = ask(f"  {YEL}Kode OTP ({phone}): {RST}")
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            pwd = ask(f"  {YEL}Password 2FA: {RST}")
            await client.sign_in(password=pwd)

        me = await client.get_me()
        slog(f"login OK: {me.first_name} ({me.id})", 'OK')
        return client, None, me
    except (PhoneCodeInvalidError, Exception) as e:
        slog(f"login error: {e}", 'ERR')
        try: await client.disconnect()
        except Exception: pass
        return None, None, None

# ═══════════════════════════════════════════════════════════════
#  ACCOUNT BOOTSTRAP
# ═══════════════════════════════════════════════════════════════
def account_bootstrap(init_data):
    if not init_data: return None
    q = parse_qs(init_data)
    if 'user' not in q: return None
    try: user = json.loads(q['user'][0])
    except Exception: return None

    auth = api_auth(init_data, int(user['id']))
    if not auth or not auth.get('ok'): return None

    state = api_state(init_data)
    if not state or not state.get('ok'): return None

    u = state.get('user', {})
    return {
        'tg_id': int(u.get('telegramId', user['id'])),
        'name': u.get('firstName', user.get('first_name', '?')),
        'username': u.get('username', user.get('username', '')),
        'balance': float(state.get('balance', 0)),
        'earned': float(state.get('earned', 0)),
        'tasks_done': int(state.get('tasksDone', 0)),
        'tasks': state.get('tasks', []),
        'referral': state.get('referral', {}),
    }

# ═══════════════════════════════════════════════════════════════
#  TASK RUNNER (FIX too_soon)
# ═══════════════════════════════════════════════════════════════
def tmr(seconds, label=""):
    spin = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
    end = time.time()+seconds; i=0
    while (rem := end-time.time())>0:
        sys.stdout.write(f"\r   {ORG}{spin[i%len(spin)]}{RST} {fmt_dur(rem)} {DIM}{label}{RST} ")
        sys.stdout.flush(); i+=1; time.sleep(0.08)
    sys.stdout.write("\r"+" "*60+"\r")

def run_tasks_for_account(init_data, info):
    """
    FIX too_soon:
      - Delay awal 12s (naik dari 6s)
      - Retry dengan exponential backoff kalo error
      - Detect 'too_soon' → naikin delay buat task berikutnya
    """
    done=0; fail=0; next_available=0
    tasks = info.get('tasks', [])
    pending = [t for t in tasks if not t.get('done')]
    total = len(pending)

    STATE['current_acc'] = info['name'] + (f" @{info['username']}" if info.get('username') else "")
    STATE['current_bal'] = info['balance']
    STATE['task_pending'] = total

    slog(f"{info['name']} — {total} task, bal {info['balance']:.6f}", 'ACC')
    clear_render()

    # track dynamic delay — task berikutnya tambah kalo sering too_soon
    extra_delay = 0

    for i, t in enumerate(pending):
        tid = int(t['id'])
        reward = float(t.get('reward', 0))
        idx = i+1

        STATE['task_current'] = f"#{tid} ({idx}/{total})"
        STATE['task_retry'] = 0
        slog(f"open task #{tid}", 'OPEN')
        clear_render()

        # ── OPEN ──
        op = api_open(init_data, tid)
        if not op or not op.get('ok'):
            slog(f"open #{tid} gagal", 'ERR')
            fail += 1; STATE['tasks_failed'] += 1
            clear_render(); continue

        # ── VERIFY dengan retry ──
        success = False
        open_delay = TASK_OPEN_DELAY_BASE + extra_delay

        for attempt in range(MAX_TASK_RETRIES):
            STATE['task_retry'] = attempt
            slog(f"nunggu {open_delay}s → verify #{tid} (try {attempt+1})", 'WAIT')
            clear_render()
            tmr(open_delay, f"verify #{tid}")

            tk = api_task(init_data, tid)

            if tk and tk.get('ok'):
                new_bal = float(tk.get('balance', 0))
                STATE['current_bal'] = new_bal
                STATE['earned_total'] += reward
                STATE['tasks_done'] += 1
                done += 1
                success = True
                slog(f"task #{tid} OK +{reward} (bal {new_bal})", 'OK')
                clear_render()

                for tt in tk.get('tasks', []):
                    if int(tt['id'])==tid and tt.get('availableAt'):
                        next_available = max(next_available, int(tt['availableAt']))
                break
            else:
                err = (tk or {}).get('error', 'unknown')

                # ─── FIX too_soon ───
                if err == 'too_soon':
                    # naikin delay buat next attempt + jaga-jaga buat task berikutnya
                    open_delay = min(open_delay + 8, TASK_OPEN_DELAY_MAX)
                    extra_delay = min(extra_delay + 2, 10)
                    slog(f"too_soon! naikin delay ke {open_delay}s", 'RETRY')
                    clear_render()
                    continue

                # ─── FloodWait ───
                if err in ('flood_wait','rate_limit'):
                    slog(f"rate limit, tunggu 30s", 'RETRY')
                    clear_render(); time.sleep(30)
                    continue

                # error lain, coba sekali lagi
                slog(f"task #{tid} gagal: {err}", 'ERR')
                if attempt < MAX_TASK_RETRIES-1:
                    time.sleep(3)
                    continue
                break

        if not success:
            fail += 1; STATE['tasks_failed'] += 1
            clear_render()

        time.sleep(BETWEEN_TASKS)

    if next_available == 0:
        for t in info.get('tasks', []):
            if t.get('availableAt'):
                next_available = max(next_available, int(t['availableAt']))
    if next_available == 0:
        next_available = ts_ms() + COOLDOWN_FALLBACK*1000

    cl = api_claim(init_data)
    if cl and cl.get('ok') and cl.get('hashes_added'):
        slog(f"claim hashes: +{cl['hashes_added']}", 'OK')
        clear_render()

    STATE['task_current'] = '-'; STATE['task_retry'] = 0
    return {'completed':done, 'failed':fail, 'next_available_at':next_available}

# ═══════════════════════════════════════════════════════════════
#  LOOP
# ═══════════════════════════════════════════════════════════════
def run_loop(selected, continuous=True):
    if not selected: return
    STATE['phase']='running'; STATE['acc_total']=len(selected); STATE['acc_idx']=0

    while True:
        STATE['cycle'] += 1
        cooldowns = {}

        for i, a in enumerate(selected):
            STATE['acc_idx'] = i+1
            init_data = a.get('initData','')
            name = a.get('name','?')

            slog(f"bootstrap: {name}", 'ACC')
            clear_render()

            info = account_bootstrap(init_data)
            if not info:
                slog(f"{name} — auth gagal (initData expired?)", 'ERR')
                clear_render(); continue

            r = run_tasks_for_account(init_data, info)
            slog(f"{name}: {r['completed']} ok / {r['failed']} gagal", 'OK')
            clear_render()
            cooldowns[a['tg_id']] = r['next_available_at']

        if not continuous:
            STATE['phase']='idle'; STATE['menu_hint']='single-shot selesai'
            clear_render(); return

        earliest = min(cooldowns.values()) if cooldowns else ts_ms()+COOLDOWN_FALLBACK*1000
        wait_sec = max(30, (earliest - ts_ms())//1000)
        STATE['phase']='cooldown'
        STATE['cooldown_end']=time.time()+wait_sec
        STATE['menu_hint']='cooldown — nunggu cycle berikutnya'

        slog(f"cooldown {fmt_dur(wait_sec)} → {datetime.fromtimestamp(earliest/1000).strftime('%H:%M:%S')}", 'WAIT')
        clear_render()

        spin=['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']; i=0
        while time.time() < STATE['cooldown_end']:
            rem = int(STATE['cooldown_end']-time.time())
            sys.stdout.write(f"\r   {ORG}{spin[i%len(spin)]}{RST} cooldown {fmt_dur(rem)}   ")
            sys.stdout.flush(); i+=1; time.sleep(0.2)
        sys.stdout.write("\r"+" "*50+"\r")
        STATE['phase']='running'

# ═══════════════════════════════════════════════════════════════
#  ASYNC HELPERS (wrapper buat panggil telethon dari sync code)
# ═══════════════════════════════════════════════════════════════
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed(): raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ═══════════════════════════════════════════════════════════════
#  MENU ACTIONS
# ═══════════════════════════════════════════════════════════════
def ask(prompt):
    try: return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{RED}keluar{RST}"); sys.exit(0)

# ─────────────── ADD VIA TELETHON ───────────────
def add_via_telethon():
    if not API_ID or not API_HASH:
        clear_render()
        print(f"\n{RED}API_ID & API_HASH belum di-set!{RST}")
        print(f"{DIM}Ambil dari https://my.telegram.org/apps{RST}")
        print(f"{DIM}Edit file script, ganti baris:{RST}")
        print(f"  API_ID   = 0       →  angka api_id lu")
        print(f"  API_HASH = \"\"      →  hash string lu\n")
        ask("Enter buat lanjut...")
        return

    clear_render()
    print(f"\n{CYN}═══ TAMBAH AKUN VIA TELETHON ═══{RST}\n")
    phone = ask(f"{YEL}Nomor HP (format +62...): {RST}")
    if not phone: return

    accs = load_accounts()
    for a in accs:
        if a.get('phone') == phone:
            slog("nomor udah ada", 'WARN'); return

    clear_render()
    slog(f"login {phone}...", 'TG')
    clear_render()

    client, _, me = run_async(telethon_login_flow(phone))
    if not client or not me:
        slog("login gagal", 'ERR'); return

    slog(f"login OK: {me.first_name} ({me.id})", 'OK')
    clear_render()

    # ambil master ref kalo ada → kirim /start dengan param
    master = get_master_ref()
    start_param = str(master) if master else ""

    slog(f"open mini app (reff={start_param or 'none'})...", 'TG')
    clear_render()

    init_data = run_async(telethon_get_initdata(client, BOT_USERNAME, start_param))

    if not init_data:
        slog("gagal extract initData", 'ERR')
        try: run_async(client.disconnect())
        except Exception: pass
        return

    # validasi via API
    info = account_bootstrap(init_data)
    if not info:
        slog("validasi API gagal — initData mungkin invalid", 'ERR')
        try: run_async(client.disconnect())
        except Exception: pass
        return

    accs.append({
        'name': me.first_name + (f" {me.last_name}" if me.last_name else ""),
        'tg_id': int(me.id),
        'username': me.username or '',
        'phone': phone,
        'initData': init_data,
        'added_at': datetime.now().isoformat(),
    })
    save_accounts(accs)

    try: run_async(client.disconnect())
    except Exception: pass

    slog(f"ditambahkan: {info['name']} (bal {info['balance']:.6f})", 'OK')

# ─────────────── ADD MANUAL (paste initData) ───────────────
def add_account():
    clear_render()
    print(f"\n{CYN}═══ TAMBAH AKUN (paste initData) ═══{RST}\n")
    init_data = ask(f"{YEL}Paste initData: {RST}")
    if not init_data: slog("batal", 'WARN'); return

    q = parse_qs(init_data)
    if 'user' not in q: slog("initData gak valid", 'ERR'); return
    try: u = json.loads(q['user'][0])
    except Exception: slog("user JSON invalid", 'ERR'); return

    accs = load_accounts()
    for a in accs:
        if a.get('tg_id',0) == int(u['id']): slog("akun udah ada", 'WARN'); return

    name = u.get('first_name', f"user_{u['id']}")
    if u.get('last_name'): name += " "+u['last_name']

    slog(f"validasi {name}...", 'ACC'); clear_render()
    info = account_bootstrap(init_data)
    if not info: slog("auth gagal", 'ERR'); return

    accs.append({
        'name': name, 'tg_id': int(u['id']),
        'username': u.get('username',''),
        'initData': init_data,
        'added_at': datetime.now().isoformat(),
    })
    save_accounts(accs)
    slog(f"ditambahkan: {name} (bal {info['balance']:.6f})", 'OK')

# ─────────────── AUTO REFF ALL ───────────────
def auto_reff_all():
    """
    Kirim /start <master_id> dari SEMUA akun ke bot.
    Buka mini app biar server catat sebagai ref.
    """
    master = get_master_ref()
    if not master:
        slog("set master dulu (menu 6)", 'WARN'); return

    accs = load_accounts()
    targets = [a for a in accs if int(a['tg_id']) != master]
    if not targets:
        slog("gak ada akun non-master buat di-reff", 'WARN'); return

    clear_render()
    print(f"\n{CYN}═══ AUTO REFF ALL ═══{RST}")
    print(f"{DIM}Master: tg={master}{RST}")
    print(f"{DIM}Target: {len(targets)} akun{RST}\n")

    ok=0; fail=0
    for i, a in enumerate(targets):
        phone = a.get('phone')
        name = a.get('name','?')
        if not phone:
            slog(f"{name} — skip (no phone/session)", 'WARN'); clear_render(); continue

        slog(f"[{i+1}/{len(targets)}] reff: {name}", 'REFF')
        clear_render()

        # connect ulang pakai session file
        session_name = phone.replace('+','')
        session_path = os.path.join(SESSIONS_DIR, session_name)
        if not os.path.exists(session_path + '.session'):
            slog(f"{name} — no session file, skip", 'WARN'); clear_render()
            fail += 1; continue

        async def do_reff():
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect(); return False
            # kirim /start dengan ref param
            ok_send = await telethon_send_start(client, BOT_USERNAME, str(master))
            if ok_send:
                # buka mini app biar tercatat reff valid
                init = await telethon_get_initdata(client, BOT_USERNAME, str(master))
                await client.disconnect()
                return init is not None
            await client.disconnect(); return False

        try:
            if run_async(do_reff()):
                ok += 1
                slog(f"reff OK: {name}", 'OK')
            else:
                fail += 1
                slog(f"reff gagal: {name}", 'ERR')
        except Exception as e:
            fail += 1
            slog(f"reff err: {name} → {e}", 'ERR')
        clear_render()

    slog(f"auto reff selesai: {ok} ok / {fail} gagal", 'OK')
    # refresh stats
    ref_refresh_stats()

# ─────────────── REFRESH REF STATS ───────────────
def ref_refresh_stats():
    accs = load_accounts()
    master = get_master_ref()
    if not master or not accs: return

    total=0; valid=0
    for a in accs:
        if int(a['tg_id']) != master: continue
        info = account_bootstrap(a.get('initData',''))
        if not info: continue
        ref = info.get('referral', {})
        total = int(ref.get('total', 0))
        for row in ref.get('rows', []):
            if row.get('active'): valid += 1

    STATE['ref_master']=master; STATE['ref_link']=build_ref_link(master)
    STATE['ref_total']=total; STATE['ref_active']=valid
    slog(f"ref stats: {total} total, {valid} valid", 'OK')

# ─────────────── OTHER ───────────────
def remove_account():
    accs = load_accounts()
    if not accs: slog("kosong", 'WARN'); return
    clear_render()
    print(f"\n{CYN}═══ HAPUS AKUN ═══{RST}\n")
    for i,a in enumerate(accs):
        u = f" @{a['username']}" if a.get('username') else ""
        print(f"  {YEL}[{i+1}]{RST} {WHT}{a['name']}{RST}{DIM}{u} tg={a['tg_id']}{RST}")
    idx = int(ask("\nNomor: ") or "0")
    if 1 <= idx <= len(accs):
        rem = accs.pop(idx-1); save_accounts(accs)
        slog(f"dihapus: {rem['name']}", 'OK')

def show_referral():
    accs = load_accounts()
    if not accs: slog("kosong", 'WARN'); return
    clear_render()
    print(f"\n{CYN}═══ REFERRAL LINK ═══{RST}\n")
    for i,a in enumerate(accs):
        u = f" @{a['username']}" if a.get('username') else ""
        print(f"  {YEL}[{i+1}]{RST} {WHT}{a['name']}{RST}{DIM}{u}{RST}")
    idx = int(ask("\nNomor: ") or "0")
    if idx < 1 or idx > len(accs): slog("invalid", 'ERR'); return
    a = accs[idx-1]
    link = build_ref_link(a['tg_id'])

    print(f"\n{CYN}╔{'═'*62}╗{RST}")
    print(CYN+"║"+pad_to(" "+VIO+f"REF LINK — {a['name']}"+RST,62)+CYN+"║"+RST)
    print(f"{CYN}╚{'═'*62}╝{RST}\n")
    print(f"  {CYN}{link}{RST}\n")

    if ask("  Buka? (y/n): ").lower() == 'y':
        open_url(link)

def ref_set_master():
    accs = load_accounts()
    if not accs: slog("kosong", 'WARN'); return
    clear_render()
    print(f"\n{CYN}═══ SET MASTER ═══{RST}\n")
    current = get_master_ref()
    for i,a in enumerate(accs):
        u = f" @{a['username']}" if a.get('username') else ""
        mark = f" {GRN}★{RST}" if a['tg_id']==current else ""
        print(f"  {YEL}[{i+1}]{RST} {WHT}{a['name']}{RST}{DIM}{u}{RST}{mark}")
    idx = int(ask("\nMaster (0=batal): ") or "0")
    if 1 <= idx <= len(accs):
        a = accs[idx-1]
        set_master_ref(int(a['tg_id']))
        STATE['ref_master']=int(a['tg_id'])
        STATE['ref_link']=build_ref_link(int(a['tg_id']))
        slog(f"master: {a['name']}", 'REFF')

# ═══════════════════════════════════════════════════════════════
#  MENU UI
# ═══════════════════════════════════════════════════════════════
def show_menu():
    accs = load_accounts()
    clear_render()

    print(f"\n{CYN}╔{'═'*62}╗{RST}")
    print(CYN+"║"+pad_to(" "+VIO+f"DAFTAR AKUN ({len(accs)})"+RST,62)+CYN+"║"+RST)
    if not accs:
        print(CYN+"║"+pad_to("  "+DIM+"(kosong — pakai menu 3/8)"+RST,62)+CYN+"║"+RST)
    else:
        for i,a in enumerate(accs):
            u = f" @{a['username']}" if a.get('username') else ""
            print(CYN+"║"+pad_to(f"  {YEL}[{i+1}]{RST} {WHT}{a['name']}{RST}{DIM}{u} tg={a['tg_id']}{RST}",62)+CYN+"║"+RST)
    print(f"{CYN}╚{'═'*62}╝{RST}")

    print(f"\n{CYN}═══ MENU ═══{RST}")
    print(f"  {YEL}1{RST}) Run {WHT}1 akun{RST}")
    print(f"  {YEL}2{RST}) Run {WHT}semua akun (multi){RST}")
    print(f"  {YEL}3{RST}) {GRN}Tambah akun{RST} (paste initData manual)")
    print(f"  {YEL}4{RST}) {RED}Hapus akun{RST}")
    print(f"  {YEL}5{RST}) {CYN}Generate referral link{RST}")
    print(f"  {YEL}6{RST}) {VIO}Set master referrer{RST}")
    print(f"  {YEL}7{RST}) {MAG}Auto Reff ALL{RST} (semua akun /start ke master)")
    print(f"  {YEL}8{RST}) {MAG}Tambah akun via TELETHON{RST} (login + auto grab initData)")
    print(f"  {YEL}0{RST}) Exit\n")

# ═══════════════════════════════════════════════════════════════
#  SIGNAL
# ═══════════════════════════════════════════════════════════════
def on_sigint(sig, frame):
    print(f"\n\n{YEL}[!] SIGINT — keluar aman{RST}"); sys.exit(0)
signal.signal(signal.SIGINT, on_sigint)

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    # load ref config
    master = get_master_ref()
    if master:
        STATE['ref_master'] = master
        STATE['ref_link'] = build_ref_link(master)
        for a in load_accounts():
            if int(a['tg_id']) == master:
                info = account_bootstrap(a.get('initData',''))
                if info:
                    ref = info.get('referral', {})
                    STATE['ref_total'] = int(ref.get('total', 0))
                    for row in ref.get('rows', []):
                        if row.get('active'): STATE['ref_active'] += 1
                break

    clear_render()
    slog("SouuEngine Telethon siap", 'OK')
    slog("silakan pilih menu", 'MENU')
    clear_render()

    while True:
        show_menu()
        choice = ask("Pilih> ")

        if choice == '1':
            accs = load_accounts()
            if not accs: slog("kosong", 'WARN'); continue
            if len(accs) == 1:
                idx = 1
                slog(f"auto-pick: {accs[0]['name']}", 'ACC')
            else:
                for i,a in enumerate(accs):
                    u = f" @{a['username']}" if a.get('username') else ""
                    print(f"  {YEL}[{i+1}]{RST} {WHT}{a['name']}{RST}{DIM}{u}{RST}")
                try: idx = int(ask("Index: ") or "0")
                except ValueError: slog("invalid", 'ERR'); continue
                if idx < 1 or idx > len(accs): slog("invalid", 'ERR'); continue
            cont = ask("Continuous loop? (y/n): ").lower() == 'y'
            STATE['mode'] = 'single-loop' if cont else 'single'
            run_loop([accs[idx-1]], cont)

        elif choice == '2':
            accs = load_accounts()
            if not accs: slog("kosong", 'WARN'); continue
            clear_render()
            cont = ask(f"Jalanin semua {len(accs)} akun? Continuous? (y/n): ").lower() == 'y'
            STATE['mode'] = 'multi-loop' if cont else 'multi'
            run_loop(accs, cont)

        elif choice == '3': add_account()
        elif choice == '4': remove_account()
        elif choice == '5': show_referral()
        elif choice == '6': ref_set_master()
        elif choice == '7': auto_reff_all()
        elif choice == '8': add_via_telethon()
        elif choice == '0':
            print(f"\n{CYN}bye boss 👋{RST}\n"); sys.exit(0)
        else: slog("pilihan gak ada", 'WARN')

if __name__ == "__main__":
    main()
