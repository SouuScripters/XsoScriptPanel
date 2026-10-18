#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  VIRTUAL MINE AUTO MINER + TASK CLAIM — SOUU ENGINE v1.0     ║
║  HOST : virtual-mine-rbot.ih0st.app (tid=919)                ║
║  Ref  : https://t.me/virtual_mine_rbot?start=6894031790      ║
║  FEAT : Telethon StringSession (no DB lock)                  ║
║  FEAT : Auto start mining session                            ║
║  FEAT : Auto join channel/group, start bot, visit, claim     ║
║  FEAT : Auto claim hashes (accumulated mining)               ║
║  FEAT : Skip ad-network & reflink tasks                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, re, random, asyncio
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

import requests

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.tl.types import InputUser
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import UserAlreadyParticipantError, ChannelPrivateError, FloodWaitError

# ═══════════════════ CONFIG ═══════════════════
API_ID = 21578873
API_HASH = "b7562db4c393baff2f415d14a14d1f76"
SESSION_FILE = "vmine_telethon.session"

BOT_USERNAME = "virtual_mine_rbot"
TID = 919
BASE_URL = "https://virtual-mine-rbot.ih0st.app"

# Referral (buat akun baru; akun existing gak bisa refere diri sendiri)
REF_ID = "6894031790"
REF_LINK = f"https://t.me/{BOT_USERNAME}?start={REF_ID}"

TZ_OFFSET = 420            # menit (Asia/Jakarta = UTC+7)
VISIT_WAIT_DEFAULT = 15    # detik, default kalau title gak ada info durasi
CYCLE_DELAY = 30           # detik jeda antar siklus
INIT_DATA_REFRESH = 3600   # refresh initData tiap 1 jam

UA = (
    "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.8059.43 Mobile Safari/537.36 "
    "Telegram-Android/12.9.2"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "*/*",
    "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": BASE_URL + "/",
    "X-Requested-With": "org.telegram.messenger.web",
}

# Fingerprint (dari dump lu; ganti per akun kalau multi-akun)
FINGERPRINT = {
    "uid": "dmvdvjebvfkehogcc9sk81fpnk6912os9r9",
    "sw": 384, "sh": 832, "dpr": 2.8125, "cd": 24,
    "tz": "Asia/Jakarta", "tzo": -TZ_OFFSET,
    "lang": "id", "langs": "id,id-ID,en-US",
    "plat": "Linux aarch64",
    "hc": 8, "dm": 8, "tp": 5,
    "webgl": "Samsung Electronics Co., Ltd.|ANGLE ((Samsung Xclipse 530) on Vulkan 1.3.279)",
    "cv": "7S+uUQAAAAZJREFUAwCxiYdbdTPkbgAAAABJRU5ErkJggg==",
}

# ═══════════════════ COLORS ═══════════════════
def _c(n): return f"\033[38;5;{n}m"
RED, GREEN, YELLOW, CYAN, MAGENTA, WHITE, GRAY, AQUA = (
    _c(196), _c(46), _c(226), _c(51), _c(201), _c(231), _c(245), _c(87)
)
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"

def clear(): os.system("clear" if os.name == "posix" else "cls")
def now(): return datetime.now().strftime("%H:%M:%S")

def log(tag, msg, color=WHITE):
    print(f"{GRAY}[{now()}]{RESET} {color}[{tag.upper():7}]{RESET} {msg}")

# ═══════════════════ TELETHON SESSION ═══════════════════
def _load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE) as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""

def _save_session(s):
    try:
        with open(SESSION_FILE, "w") as f:
            f.write(s)
    except Exception as e:
        log("session", f"save fail: {e}", RED)

async def _get_init_data_async():
    sess = _load_session()
    client = TelegramClient(StringSession(sess), API_ID, API_HASH)

    if not sess:
        clear()
        print(f"{CYAN}{'='*60}{RESET}")
        print(f"{BOLD}{MAGENTA}{'FIRST RUN — TELETHON LOGIN':^60}{RESET}")
        print(f"{CYAN}{'='*60}{RESET}")
        print(f" {WHITE}Belum ada session. Login sekali pakai nomor HP + OTP.{RESET}")
        print(f" {WHITE}Session disimpan ke: {YELLOW}{SESSION_FILE}{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")
        time.sleep(1)

    log("telethon", "Connecting...", CYAN)
    await client.start()
    _save_session(client.session.save())
    log("telethon", "Session tersimpan", GREEN)

    try:
        bot = await client.get_entity(BOT_USERNAME)
        peer = await client.get_input_entity(bot)
        iuser = InputUser(bot.id, bot.access_hash)

        # First-time bot start with ref (hanya apply untuk akun baru)
        try:
            await client.send_message(BOT_USERNAME, f"/start {REF_ID}")
            await asyncio.sleep(3)
        except Exception:
            pass

        log("webview", "Fetching initData...", CYAN)
        try:
            res = await client(RequestWebViewRequest(
                peer=peer, bot=iuser,
                platform="android", from_bot_menu=True,
                url=f"{BASE_URL}/",
            ))
        except Exception:
            res = await client(RequestWebViewRequest(
                peer=peer, bot=iuser,
                platform="android", from_bot_menu=False,
                url=f"{BASE_URL}/",
            ))

        raw = None
        if res and res.url:
            pq = parse_qs(urlparse(res.url).fragment)
            raw = pq.get("tgWebAppData", [None])[0]
            if not raw:
                pq = parse_qs(urlparse(res.url).query)
                raw = pq.get("tgWebAppData", [None])[0]

        if not raw:
            # fallback: scan messages
            async for msg in client.iter_messages(bot, limit=20):
                if not msg.buttons: continue
                for row in msg.buttons:
                    for b in row:
                        u = getattr(b, "url", None) or ""
                        if "tgWebAppData" not in u: continue
                        pu = urlparse(u)
                        pq = parse_qs(pu.fragment) or parse_qs(pu.query)
                        v = pq.get("tgWebAppData", [None])[0]
                        if v: raw = v; break
                    if raw: break
                if raw: break

        if not raw:
            raise RuntimeError("tgWebAppData tidak ditemukan")

        if "%" in raw and "auth_date=" not in raw:
            raw = unquote(raw)

        return raw, client
    except Exception:
        await client.disconnect()
        raise

# ═══════════════════ JOIN / START BOT ═══════════════════
def _extract_path(target):
    """https://t.me/X?start=... → X ; @chan → chan ; t.me/X/app?startapp → X"""
    if not target: return None
    if "t.me/" in target:
        p = target.split("t.me/")[1]
        # strip query / fragment
        p = p.split("?")[0].split("#")[0]
        # strip trailing path (like /App)
        p = p.split("/")[0]
        return p if p else None
    if target.startswith("@"):
        return target[1:]
    return target

async def join_channel_or_group(client, target):
    path = _extract_path(target)
    if not path:
        log("join", f"invalid target: {target}", YELLOW)
        return False
    try:
        entity = await client.get_entity(path)
        try:
            await client(JoinChannelRequest(entity))
            log("join", f"✔ joined {path}", GREEN)
            return True
        except UserAlreadyParticipantError:
            log("join", f"already in {path}", GRAY)
            return True
        except (ChannelPrivateError, FloodWaitError) as e:
            log("join", f"{path}: {type(e).__name__}", YELLOW)
            return False
    except Exception as e:
        log("join", f"{path}: {str(e)[:50]}", YELLOW)
        return False

async def start_bot(client, target):
    path = _extract_path(target)
    if not path:
        log("bot", f"invalid target: {target}", YELLOW)
        return False
    try:
        await client.send_message(path, "/start")
        log("bot", f"✔ started {path}", GREEN)
        return True
    except Exception as e:
        log("bot", f"{path}: {str(e)[:50]}", YELLOW)
        return False

# ═══════════════════ MINIAPP API ═══════════════════
def api_auth(init_data):
    body = {"initData": init_data, "tid": TID, "fp": FINGERPRINT}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/auth?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.status_code == 200
    except Exception as e:
        log("auth", str(e)[:60], RED)
        return False

def api_state(init_data):
    body = {"initData": init_data, "tid": TID, "tz_offset": TZ_OFFSET}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/taskminer/state?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}

def api_mine(init_data):
    body = {"initData": init_data, "tid": TID, "tz_offset": TZ_OFFSET}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/taskminer/mine?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}

def api_task_open(init_data, task_id):
    body = {"initData": init_data, "tid": TID, "tz_offset": TZ_OFFSET, "task_id": task_id}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/taskminer/task/open?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}

def api_task_claim(init_data, task_id):
    body = {"initData": init_data, "tid": TID, "tz_offset": TZ_OFFSET, "task_id": task_id}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/taskminer/task/claim?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}

def api_claim_hashes(init_data):
    body = {"initData": init_data, "tid": TID}
    try:
        r = requests.post(f"{BASE_URL}/miniapp/claim?tid={TID}",
                          json=body, headers=HEADERS, timeout=30)
        return r.json()
    except Exception:
        return {"ok": False}

# ═══════════════════ TASK PROCESSING ═══════════════════
def parse_wait_seconds(task):
    title = task.get("title", "")
    m = re.search(r'(\d+)\s*s', title, re.I)
    if m:
        try:
            return max(5, int(m.group(1)))
        except: pass
    return VISIT_WAIT_DEFAULT

def fmt_bal(data):
    b = data.get("balances", {})
    return f"GRAM={b.get('gram', 0):.6f}  POWER={b.get('power', 0)}"

async def process_task(client, init_data, task):
    tid = task["id"]
    kind = task["kind"]
    target = task.get("target", "")
    title = task.get("title", "?")

    # Skip tasks yang gak bisa diotomasi
    if kind == "ad":
        log("task", f"#{tid} {kind} [SKIP] {title} (butuh ad network)", GRAY)
        return False
    if kind == "reflink":
        log("task", f"#{tid} {kind} [SKIP] {title} (butuh referral)", GRAY)
        return False

    # Channel/group: join via Telethon dulu
    if kind in ("channel", "group"):
        await join_channel_or_group(client, target)
        await asyncio.sleep(2)

    # Bot: /start dulu
    if kind == "bot":
        await start_bot(client, target)
        await asyncio.sleep(2)

    # Visit: hit target URL (fire & forget)
    if kind == "visit" and target:
        try:
            requests.get(target, headers={"User-Agent": UA}, timeout=10)
        except Exception:
            pass

    # Open (mulai timer)
    op = api_task_open(init_data, tid)
    if not op.get("ok"):
        log("task", f"#{tid} open FAIL: {op.get('error', op)}", RED)
        return False

    # Tunggu sesuai durasi task
    wait_s = parse_wait_seconds(task)
    log("task", f"#{tid} {kind} waiting {wait_s}s...", CYAN)
    await asyncio.sleep(wait_s + 2)

    # Claim
    cl = api_task_claim(init_data, tid)
    if cl.get("ok"):
        rp = cl.get("reward_power", 0)
        ra = cl.get("reward_amount", 0)
        log("task", f"#{tid} {kind} ✔ +{rp} POWER +{ra} GRAM", GREEN)
        return True
    else:
        log("task", f"#{tid} {kind} claim FAIL: {cl.get('error', cl)}", YELLOW)
        return False

# ═══════════════════ MAIN LOOP ═══════════════════
async def run_bot():
    init_data, tg_client = await _get_init_data_async()
    log("initdata", f"OK (len={len(init_data)})", GREEN)

    if not api_auth(init_data):
        log("auth", "miniapp auth failed", RED)
        await tg_client.disconnect()
        return
    log("auth", "miniapp OK", GREEN)

    last_refresh = time.time()

    try:
        while True:
            # ── Refresh initData kalau udah 1 jam ──
            if time.time() - last_refresh > INIT_DATA_REFRESH:
                log("refresh", "Refreshing initData...", CYAN)
                try:
                    bot = await tg_client.get_entity(BOT_USERNAME)
                    peer = await tg_client.get_input_entity(bot)
                    iuser = InputUser(bot.id, bot.access_hash)
                    try:
                        res = await tg_client(RequestWebViewRequest(
                            peer=peer, bot=iuser,
                            platform="android", from_bot_menu=True,
                            url=f"{BASE_URL}/",
                        ))
                    except Exception:
                        res = await tg_client(RequestWebViewRequest(
                            peer=peer, bot=iuser,
                            platform="android", from_bot_menu=False,
                            url=f"{BASE_URL}/",
                        ))
                    new_data = None
                    if res and res.url:
                        pq = parse_qs(urlparse(res.url).fragment)
                        new_data = pq.get("tgWebAppData", [None])[0]
                        if not new_data:
                            pq = parse_qs(urlparse(res.url).query)
                            new_data = pq.get("tgWebAppData", [None])[0]
                    if new_data:
                        init_data = new_data
                        api_auth(init_data)
                        log("refresh", "✔ OK", GREEN)
                except Exception as e:
                    log("refresh", str(e)[:60], YELLOW)
                last_refresh = time.time()

            # ── Fetch state ──
            st = api_state(init_data)
            if not st.get("ok"):
                log("state", f"error: {st.get('error', st)}", RED)
                await asyncio.sleep(30)
                continue

            log("state", f"balance: {fmt_bal(st)}", AQUA)

            # ── Ensure mining active ──
            mining = st.get("mining", {})
            if not mining.get("active"):
                log("mine", "session not active — starting...", YELLOW)
                mr = api_mine(init_data)
                if mr.get("ok"):
                    log("mine", "✔ mining started", GREEN)
                else:
                    log("mine", f"fail: {mr.get('error', mr)}", RED)

            # ── Filter tugas todo ──
            tasks = [t for t in st.get("tasks", []) if t.get("status") == "todo"]
            log("tasks", f"{len(tasks)} todo task ditemukan", CYAN)

            # ── Proses satu per satu ──
            done_count = 0
            for task in tasks:
                try:
                    ok = await process_task(tg_client, init_data, task)
                    if ok:
                        done_count += 1
                    await asyncio.sleep(random.uniform(2, 4))
                except Exception as e:
                    log("task", f"#{task.get('id')}: {str(e)[:50]}", RED)

            log("cycle", f"{done_count}/{len(tasks)} tasks success", GREEN)

            # ── Claim hashes ──
            try:
                ch = api_claim_hashes(init_data)
                added = ch.get("hashes_added", 0)
                if added and added > 0:
                    log("claim", f"+{added} hashes claimed", GREEN)
            except Exception:
                pass

            # ── Sleep ──
            wait = CYCLE_DELAY + random.randint(0, 15)
            log("wait", f"next cycle in {wait}s", GRAY)
            for i in range(wait, 0, -1):
                sys.stdout.write(f"\r{GRAY}[{now()}] {i}s...{RESET}   ")
                sys.stdout.flush()
                await asyncio.sleep(1)
            print()

    finally:
        try:
            await tg_client.disconnect()
        except: pass

def main():
    clear()
    print(f"""{CYAN}{BOLD}
   ╔════════════════════════════════════════════════════╗
   ║   ⛏  VIRTUAL MINE AUTO MINER + TASK CLAIM  ⛏      ║
   ║   Ref: {YELLOW}{REF_LINK:<44}{CYAN}║
   ║   StringSession · no DB lock                       ║
   ╚════════════════════════════════════════════════════╝{RESET}
""")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopped.{RESET}")
    except Exception as e:
        print(f"\n{RED}Fatal: {e}{RESET}")

if __name__ == "__main__":
    main()
