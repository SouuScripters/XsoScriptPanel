#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTX Miner Auto-Clicker v2.1 — RollerCoin UI + Bugfix
"""

import asyncio, time, os, sys, hashlib, glob, re, requests
from telethon import TelegramClient, events

# ================= KONFIG =================
API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USERNAME = '@NOTX_MINER_BOT'
SESSION_FILE = 'notx_session'

WATCH_AD_WAIT       = 5
COOLDOWN_BETWEEN    = 2
AUTO_LOOP_INTERVAL  = 4        # ← dipercepat
RENDER_INTERVAL     = 1.0
DEDUP_WINDOW        = 3        # detik

# Auto-reff (spread manual, bukan bot)
REF_LINK = 'https://t.me/NOTX_MINER_BOT?start=6894031790'
AUTO_SPREAD_CHATS = []         # ['@grup1', -1001234] kalau mau spread
SPREAD_INTERVAL   = 3600
SPREAD_DELAY      = 30

# ==========================================

class C:
    RST="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
    CYAN="\033[1;36m"; MAGENTA="\033[1;35m"; YELLOW="\033[1;33m"
    GREEN="\033[1;32m"; RED="\033[1;31m"; BLUE="\033[1;34m"
    WHITE="\033[1;37m"; GRAY="\033[1;90m"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def parse_balance(text):
    """Parse balance dari berbagai format bot."""
    if not text: return None
    patterns = [
        r'Balance[^\d\n]*\n\s*([\d.]+)\s*NOT',   # Balance\n9.88 NOT
        r'Balance[^\d]*([\d.]+)\s*NOT',          # Balance: 9.88 NOT
        r'Balance[^\d]*([\d.]+)',                # Balance 9.88
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try: return float(m.group(1))
            except: pass
    return None

def parse_power(text):
    if not text: return None
    m = re.search(r'Power[^\d]*([\d.]+)\s*(GH|TH|MH)', text, re.IGNORECASE)
    if m:
        try: return f"{m.group(1)} {m.group(2).upper()}"
        except: pass
    return None

def parse_friends(text):
    if not text: return None
    m = re.search(r'Friends[^\d]*(\d+)', text, re.IGNORECASE)
    if m:
        try: return int(m.group(1))
        except: pass
    return None


# ═══════════════ DASHBOARD ═══════════════
class Dashboard:
    def __init__(self, session_name="?"):
        self.session_name = session_name
        self.s = {
            'account': {'name': '-', 'balance': 0.0, 'power': '-', 'friends': 0},
            'ads':     {'total': 0, 'earned': 0.0, 'last_reward': 0.0},
            'task':    {'current': 'idle', 'elapsed': 0.0, 'total': 0.0, 'running': False},
            'status':  'starting',
            'logs':    [],
            'start_time': time.time(),
        }
        self.W = 62
        self._render_task = None
        self._render_lock = asyncio.Lock()

    def log(self, msg, tag='i'):
        icons = {'i':'»','ok':'✓','er':'✗','wr':'⚠','in':'●','ad':'◉'}
        colors = {'i':C.CYAN,'ok':C.GREEN,'er':C.RED,'wr':C.YELLOW,'in':C.BLUE,'ad':C.MAGENTA}
        self.s['logs'].append({
            'ts': time.strftime('%H:%M:%S'),
            'icon': icons.get(tag, '»'),
            'color': colors.get(tag, C.WHITE),
            'msg': str(msg)
        })
        if len(self.s['logs']) > 5: self.s['logs'].pop(0)  # 5 line, bukan 8

    def set(self, k, v):
        if isinstance(v, dict) and k in self.s and isinstance(self.s[k], dict):
            self.s[k].update(v)
        else:
            self.s[k] = v

    def _vlen(self, s):
        return len(re.sub(r'\033\[[0-9;]*m', '', s))

    def _pad(self, s, w):
        v = self._vlen(s)
        return s + (' ' * (w - v) if v < w else '')

    def _row(self, content):
        inner = self.W - 2
        return f"{C.CYAN}║{C.RST}{self._pad(' ' + content, inner)}{C.CYAN}║{C.RST}"

    def _bar(self, pct, width, color):
        filled = max(0, min(width, int(round(pct * width))))
        empty = width - filled
        return f"{color}{'█' * filled}{C.GRAY}{'░' * empty}{C.RST}"

    def _dur(self, sec):
        return f"{int(sec) // 3600:02d}:{(int(sec) % 3600) // 60:02d}:{int(sec) % 60:02d}"

    def render(self):
        inner = self.W - 2
        acc = self.s['account']
        ads = self.s['ads']
        task = self.s['task']
        run = int(time.time() - self.s['start_time'])

        lines = []
        lines.append(f"\n{C.CYAN}╔{'═' * inner}╗{C.RST}")
        lines.append(self._row(f"{C.BOLD}{C.WHITE}NOTX MINER AUTO-CLICKER{C.RST}"))
        lines.append(self._row(f"{C.GRAY}──── RollerCoin UI v2.1 ────{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        status = self.s['status']
        sc = C.GREEN if status == 'running' else (C.YELLOW if status == 'cooldown' else C.RED)
        lines.append(self._row(f"{C.BLUE}▸ BOT{C.RST}"))
        lines.append(self._row(f"  Session : {C.YELLOW}{self.session_name}{C.RST}   Status: {sc}{status.upper()}{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        lines.append(self._row(f"{C.GREEN}▸ ACCOUNT{C.RST}"))
        lines.append(self._row(f"  Name    : {C.CYAN}{acc['name']}{C.RST}"))
        lines.append(self._row(f"  Balance : {C.GREEN}{acc['balance']} NOT{C.RST}   Power: {C.YELLOW}{acc['power']}{C.RST}   Friends: {C.CYAN}{acc['friends']}{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        lines.append(self._row(f"{C.MAGENTA}▸ ADS{C.RST}"))
        lines.append(self._row(f"  Total   : {C.GREEN}{ads['total']}{C.RST}   Earned: {C.YELLOW}+{ads['earned']:.4f} NOT{C.RST}   Last: +{ads['last_reward']:.2f}{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        pct = min(1, task['elapsed'] / task['total']) if task['total'] > 0 else 0
        barw = max(15, inner - 20)
        color = C.MAGENTA if task['running'] else C.GRAY
        icon = f"{C.GREEN}▶{C.RST}" if task['running'] else f"{C.GRAY}○{C.RST}"
        lines.append(self._row(f"{C.YELLOW}▸ CURRENT TASK{C.RST}"))
        lines.append(self._row(f"  {icon} {task['current'][:inner - 6]}"))
        lines.append(self._row(f"  [{self._bar(pct, barw, color)}] {C.YELLOW}{int(pct * 100):>3}%{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        lines.append(self._row(f"{C.MAGENTA}▸ SESSION{C.RST}"))
        lines.append(self._row(f"  Runtime : {C.CYAN}{self._dur(run)}{C.RST}"))
        lines.append(f"{C.CYAN}╠{'═' * inner}╣{C.RST}")

        lines.append(self._row(f"{C.MAGENTA}▸ LOG{C.RST}"))
        if not self.s['logs']:
            lines.append(self._row(f"{C.GRAY}  ─ no activity ─{C.RST}"))
        else:
            maxm = inner - 18
            for l in self.s['logs']:
                m = l['msg']
                if len(m) > maxm: m = m[:maxm - 1] + '…'
                lines.append(self._row(f"  {C.GRAY}[{l['ts']}]{C.RST} {l['color']}{l['icon']}{C.RST} {m}"))

        lines.append(f"{C.CYAN}╚{'═' * inner}╝{C.RST}")
        lines.append(f"\n   {C.GREEN}● {status.upper()}{C.RST} {C.GRAY}•{C.RST} {C.CYAN}{time.strftime('%H:%M:%S')}{C.RST}\n")

        # FIX: full clear biar ga overlap
        output = "\033[2J\033[H" + "\n".join(lines)
        sys.stdout.write(output)
        sys.stdout.flush()

    async def _render_loop(self):
        try:
            while True:
                await asyncio.sleep(RENDER_INTERVAL)
                if self.s['task']['running'] and self.s['task']['total'] > 0:
                    self.s['task']['elapsed'] = min(
                        self.s['task']['total'],
                        self.s['task']['elapsed'] + RENDER_INTERVAL
                    )
                async with self._render_lock:
                    self.render()
        except asyncio.CancelledError:
            pass

    def start_render(self):
        sys.stdout.write("\033[2J\033[?25l")
        self._render_task = asyncio.create_task(self._render_loop())

    async def stop_render(self):
        if self._render_task:
            self._render_task.cancel()
            try: await self._render_task
            except asyncio.CancelledError: pass
        sys.stdout.write("\033[?25h")

    async def set_task(self, current, total, running=True):
        self.s['task'] = {'current': current, 'elapsed': 0.0, 'total': float(total), 'running': running}

    async def task_done(self):
        self.s['task'] = {'current': 'idle', 'elapsed': 0.0, 'total': 0.0, 'running': False}


# ═══════════════ GLOBALS ═══════════════
last_action_time = 0
last_msg_key = None
refer_clicked = False           # ← reff 1x per session
recent_texts = []               # dedup buffer

def bisa_aksi():
    global last_action_time
    return (time.time() - last_action_time) >= COOLDOWN_BETWEEN

def tandai_aksi():
    global last_action_time
    last_action_time = time.time()

def is_duplicate(msg):
    """Dedup by text + 3s window. Fix '1 ad = 2 hits'."""
    global recent_texts
    text = (msg.text or "")[:120]
    if not text: return False
    now = time.time()
    recent_texts[:] = [(t, ts) for t, ts in recent_texts if now - ts < DEDUP_WINDOW]
    for t, ts in recent_texts:
        if t == text:
            return True
    recent_texts.append((text, now))
    return False

def hit_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        return r.url
    except: return None

def update_account_from_text(DB, text):
    """Update balance/power/friends dari text apapun."""
    bal = parse_balance(text)
    pow_ = parse_power(text)
    fri = parse_friends(text)
    if bal is not None or pow_ is not None or fri is not None:
        upd = {}
        if bal is not None: upd['balance'] = bal
        if pow_ is not None: upd['power'] = pow_
        if fri is not None: upd['friends'] = fri
        DB.set('account', upd)


async def klik_tombol(msg, keyword, klik_url=False):
    if not msg or not msg.buttons: return False
    for row in msg.buttons:
        for btn in row:
            if keyword.lower() not in btn.text.lower(): continue
            if getattr(btn, 'url', None):
                if klik_url:
                    hit_url(btn.url); return True
                return False
            try:
                await btn.click(); return True
            except: return False
    return False


async def klik_menu_terbaru(client):
    try:
        msgs = await client.get_messages(BOT_USERNAME, limit=1)
        if msgs and msgs[0].buttons:
            toms = [b.text for r in msgs[0].buttons for b in r]
            if any("Menu" in t for t in toms):
                return await klik_tombol(msgs[0], "Menu")
            if any("Open dashboard" in t for t in toms):
                return await klik_tombol(msgs[0], "Open dashboard")
    except: pass
    return False


# ═══════════════ CORE ═══════════════
async def proses(client, DB, msg, sumber="NEW"):
    global last_msg_key, refer_clicked

    if not bisa_aksi(): return
    if is_duplicate(msg): return

    text = msg.text or ""

    # Update account info dari setiap message
    update_account_from_text(DB, text)

    # 1. Cooldown
    if "Cooldown" in text or "Next ad in" in text:
        DB.set('status', 'cooldown')
        DB.log("Cooldown → Menu", 'wr')
        await klik_tombol(msg, "Menu")
        tandai_aksi()
        return

    # 2. Reward claimed
    if "Reward claimed" in text or "Ad watched" in text:
        ads = DB.s['ads']
        ads['total'] += 1
        ads['earned'] += 0.2
        ads['last_reward'] = 0.2
        DB.set('status', 'running')
        DB.log(f"Reward +0.2 | ads #{ads['total']}", 'ad')
        if msg.buttons and await klik_tombol(msg, "Watch Ad", klik_url=True):
            tandai_aksi()
            await DB.set_task("Watching ad...", WATCH_AD_WAIT)
            await asyncio.sleep(WATCH_AD_WAIT)
            await DB.task_done()   # ← FIX reset
            await klik_menu_terbaru(client)
            return

    # 3. Profit credited
    if "Profit credited" in text or "Mined" in text:
        DB.log("Profit masuk → dashboard", 'ok')
        if msg.buttons and await klik_tombol(msg, "Open dashboard"):
            tandai_aksi()
            await asyncio.sleep(2)
            await klik_menu_terbaru(client)
        return

    # 4. Auto-click Invite — ONCE per session
    if not refer_clicked:
        for kw in ('Invite', 'Refer', 'Referral'):
            if msg.buttons and await klik_tombol(msg, kw):
                refer_clicked = True
                DB.log(f"Invite clicked (1x)", 'ok')
                tandai_aksi()
                await asyncio.sleep(1)
                return

    # 5. Watch Ad
    if msg.buttons and await klik_tombol(msg, "Watch Ad", klik_url=True):
        tandai_aksi()
        await DB.set_task("Watching ad...", WATCH_AD_WAIT)
        await asyncio.sleep(WATCH_AD_WAIT)
        await DB.task_done()   # ← FIX reset
        await klik_menu_terbaru(client)
        return

    # 6. Verify
    if msg.buttons and await klik_tombol(msg, "Verify"):
        DB.log("Verify", 'in')
        tandai_aksi()
        await asyncio.sleep(3)
        return

    # 7. Menu
    if msg.buttons and await klik_tombol(msg, "Menu"):
        tandai_aksi()
        return

    # 8. Open dashboard
    if msg.buttons and await klik_tombol(msg, "Open dashboard"):
        tandai_aksi()
        await asyncio.sleep(2)
        await klik_menu_terbaru(client)
        return


async def scan_history(client, DB):
    DB.log("Scan history...", 'in')
    try:
        async for m in client.iter_messages(BOT_USERNAME, limit=10):
            update_account_from_text(DB, m.text or "")
            if m.buttons:
                toms = [b.text for r in m.buttons for b in r]
                if any(k in t for t in toms for k in ("Watch Ad","Verify","Menu","Open dashboard","Refer","Invite")):
                    await proses(client, DB, m, "HISTORY")
                    return
    except: pass


async def auto_loop(client, DB):
    while True:
        await asyncio.sleep(AUTO_LOOP_INTERVAL)
        try:
            msgs = await client.get_messages(BOT_USERNAME, limit=1)
            if msgs:
                m = msgs[0]
                update_account_from_text(DB, m.text or "")
                if m.buttons:
                    await proses(client, DB, m, "AUTO")
        except: pass


async def spread_loop(client, DB):
    if not AUTO_SPREAD_CHATS: return
    while True:
        for chat in AUTO_SPREAD_CHATS:
            try:
                await client.send_message(chat, REF_LINK)
                DB.log(f"Sent to {chat}", 'ok')
                await asyncio.sleep(SPREAD_DELAY)
            except Exception as e:
                DB.log(f"Send fail: {str(e)[:30]}", 'er')
        await asyncio.sleep(SPREAD_INTERVAL)


# ═══════════════ SESSION ═══════════════
async def run_session(session_name):
    DB = Dashboard(session_name)
    client = TelegramClient(session_name, API_ID, API_HASH)
    existed = os.path.exists(f"{session_name}.session")

    DB.set('status', 'starting')
    DB.log("Starting session", 'in')
    DB.start_render()

    try:
        await client.start()
    except Exception as e:
        DB.log(f"Auth failed: {str(e)[:40]}", 'er')
        await asyncio.sleep(3)
        return

    if not existed:
        try: await client.send_message(BOT_USERNAME, '/start')
        except: pass
        await asyncio.sleep(5)

    try:
        me = await client.get_me()
        DB.set('account', {'name': me.first_name or me.username or '-'})
    except: pass

    DB.set('status', 'running')
    DB.log("Bot started", 'ok')
    await scan_history(client, DB)

    client.add_event_handler(lambda e: proses(client, DB, e.message), events.NewMessage(chats=BOT_USERNAME))
    client.add_event_handler(lambda e: proses(client, DB, e.message), events.MessageEdited(chats=BOT_USERNAME))

    asyncio.create_task(auto_loop(client, DB))
    if AUTO_SPREAD_CHATS: asyncio.create_task(spread_loop(client, DB))

    try:
        await client.run_until_disconnected()
    finally:
        await DB.stop_render()


def find_sessions():
    files = glob.glob('*.session')
    return [f.replace('.session','') for f in files] if files else [SESSION_FILE]


async def main():
    sessions = find_sessions()
    if len(sessions) > 1:
        print(f"{C.YELLOW}[!] {len(sessions)} sessions: {sessions}{C.RST}")
        await asyncio.sleep(2)
        for s in sessions:
            print(f"{C.CYAN}[+] Running: {s}{C.RST}")
            await asyncio.sleep(1)
            await run_session(s)
    else:
        await run_session(sessions[0])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h")
        print(f"\n{C.YELLOW}[!] Stopped{C.RST}")
