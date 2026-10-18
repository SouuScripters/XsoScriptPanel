import requests
import json
import time
import os
import sys
import random
import asyncio
import urllib.parse
import uuid
from datetime import datetime
from telethon import TelegramClient, functions
from telethon.errors import SessionPasswordNeededError

# ============ RICH UI ============
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

# ============ NETWORK FIX ============
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

console = Console()

def create_retry_session(retries=5, backoff_factor=2):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor,
                  status_forcelist=[500, 502, 503, 504, 408], allowed_methods=["GET", "POST"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.verify = False
    return session

http_session = create_retry_session()

def post_request(url, params=None, data=None, headers=None):
    return http_session.post(url, params=params, data=data, headers=headers, timeout=60)

# ============ KONFIGURASI ============
API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
URL_API = "https://atfminers.asloni.online/miner/index.php"
BOT_USERNAME = '@ATF_AIRDROP_bot'
TASKS_STATE_FILE = "tasks_state.json"

# State UI
STATE = {
    "username": "Loading...",
    "task_status": {"YT LIKE": "SKIP", "X RETWEET": "SKIP", "WEBSITE": "SKIP", "REACT POST": "SKIP"},
    "energy": 0.0, "max_energy": 0.0, "pending": 0.0,
    "events": [],
    "status_msg": "Starting...",
    "balance": "0.0000", 
    "holding": "0.0000"
}

USER_AGENTS = ["Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8037.106 Mobile Safari/537.36 Telegram-Android/12.9.1"]
TASKS = [
    {"name": "YT LIKE", "task_id": "youtube_like_comment", "cooldown": 7200, "wait_time": 50},
    {"name": "X RETWEET", "task_id": "twitter_retweet", "cooldown": 7200, "wait_time": 50},
    {"name": "WEBSITE", "task_id": "website_visit", "cooldown": 7200, "wait_time": 15},
    {"name": "REACT POST", "task_id": "telegram_react_latest", "cooldown": 7200, "wait_time": 45},
]

def get_timestamp(): return str(int(time.time() * 1000))

def add_event(msg, color="white"):
    t = datetime.now().strftime("%H:%M:%S")
    STATE["events"].append(f"[{t}] {msg}")
    if len(STATE["events"]) > 5: STATE["events"].pop(0)

# ============ UI GENERATOR ============
def make_header():
    user = STATE["username"]
    engine = Text("⚡ ENGINE ................ ", style="yellow")
    engine.append("AUTO TASK / BOOST HUMAN LIKE", style="bold green")
    engine.append("\n🔧 MODE .................. ", style="yellow")
    engine.append("SMOOTH MODE NOT DETECTED", style="bold green")
    
    info = Text("\n💰 BALANCE ................ ", style="yellow")
    info.append(f"{STATE['balance']} ATF\n", style="bold green")
    info.append("🏦 HOLDING ................ ", style="yellow")
    info.append(f"{STATE['holding']} ATF", style="bold green")

    login_text = Text("\n✨ Logged in as: ", style="white")
    login_text.append(f"@{user}", style="bold green")

    return Panel(
        Group(engine, info, login_text),
        title="[bold magenta]⚡ ATF MINER ⚡[/]", border_style="magenta"
    )

def make_task_panel():
    txt = Text()
    for task in TASKS:
        name = task['name'].ljust(20, '.')
        status = STATE["task_status"][task['name']]
        color = "green" if status == "READY" else "red" if status == "SKIP" else "yellow"
        txt.append(f"➔ {name} ")
        txt.append(f"» {status}\n", style=f"bold {color}")
    return Panel(txt, title="[bold white]📊 AUTO TASK MODULE[/]", border_style="blue")

def make_monitor_panel():
    e = STATE["energy"]
    me = STATE["max_energy"]
    p = STATE["pending"]
    
    pct = min(100, max(0, (e / me) * 100)) if me > 0 else 0
    bar_len = 20
    filled = int((pct / 100) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    
    status_txt = Text()
    # Kalau lagi nunggu energy 70%, kasih tau targetnya
    if pct < 70:
        status_txt.append(f"⏱ Recharging... {pct:.1f}% (Target: 75%)\n", style="yellow")
    else:
        status_txt.append(f"⚡ {int(e)}/{int(me)}  ", style="yellow")
        status_txt.append(f"💰 {p:.4f} ATF\n", style="green")
    
    status_txt.append(f"🔋 Energy: [{bar}] {pct:.1f}%\n", style="bold green")

    events = Text()
    for ev in STATE["events"]:
        if "TAPS" in ev: events.append(ev + "\n", style="green")
        elif "SUCCESS" in ev or "CLAIM" in ev: events.append(ev + "\n", style="bold green")
        elif "Error" in ev: events.append(ev + "\n", style="red")
        else: events.append(ev + "\n", style="dim")

    return Panel(
        Group(status_txt, Text(""), Panel(events, title="[dim]📋 EVENTS[/]", border_style="dim")),
        title="[bold green]📊 SESSION MONITOR[/]", border_style="green"
    )

def draw_ui():
    return Group(make_header(), Text(""), make_task_panel(), Text(""), make_monitor_panel())

# ============ HELPERS ============
def load_tasks_state():
    if os.path.exists(TASKS_STATE_FILE):
        try:
            with open(TASKS_STATE_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_tasks_state(state):
    with open(TASKS_STATE_FILE, 'w') as f: json.dump(state, f)

def get_task_cooldown_remaining(task_id, server_cooldowns=None):
    state = load_tasks_state()
    current_time = int(time.time())
    if server_cooldowns and task_id in server_cooldowns:
        sc = int(server_cooldowns[task_id] or 0)
        if sc > current_time: return sc - current_time
    server_cd = state.get(task_id, {}).get('server_cooldown_until', 0)
    if server_cd > current_time: return server_cd - current_time
    last_claim = state.get(task_id, {}).get('last_claim', 0)
    cd = 7200
    for t in TASKS:
        if t['task_id'] == task_id: cd = t['cooldown']; break
    rem = cd - (current_time - last_claim)
    return rem if rem > 0 else 0

def is_unauthorized_error(data):
    if data.get("status") == "error":
        m = data.get("message", "").lower()
        if "unauthorized" in m or "invalid" in m or "session" in m: return True
    return False

# ============ TELEGRAM & ATF LOGIN ============
async def get_fresh_init_data(client, skip_start=True):
    try:
        bot = await client.get_entity(BOT_USERNAME)
        if not skip_start:
            await client.send_message(bot, '/start')
            await asyncio.sleep(1)
        wv = await client(functions.messages.RequestWebViewRequest(
            peer=bot, bot=bot, platform='android', from_bot_menu=True,
            url='https://atfminers.asloni.online'))
        raw = wv.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
        return urllib.parse.unquote(raw)
    except: return None

async def relogin(client):
    init_data = await get_fresh_init_data(client, skip_start=True)
    if not init_data: return None, None
    res = atf_login(init_data)
    return init_data, res

def atf_login(init_data):
    try:
        u_enc = init_data.split('user=')[1].split('&')[0]
        u_json = json.loads(urllib.parse.unquote(u_enc))
        tg_id = int(u_json['id'])
        user = u_json.get('username', '')
    except: return None

    dev_id = f"dev-{uuid.uuid4()}"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Content-Type': "application/json",
        'x-requested-with': "XMLHttpRequest",
        'origin': "https://atfminers.asloni.online",
        'referer': "https://atfminers.asloni.online/miner/index.html?v=1788012819",
        'x-telegram-init-data': init_data,
    }
    payload = {"initData": init_data, "request_id": str(uuid.uuid4()), "device_id": dev_id, "tg_id": tg_id, "username": user}
    try:
        r = post_request(URL_API, params={'action': "login", 't': get_timestamp()}, data=json.dumps(payload), headers=headers)
        d = r.json()
    except: return None

    if d.get("status") != "success": return None
    
    token = d.get("tma_session_token")
    if token:
        headers['x-atf-tma-session'] = token
        headers['cookie'] = f"atf_tma_session={token}"

    u_data = d.get("user", {})
    STATE["holding"] = str(u_data.get("wallet_holding_atf", "0.0000"))
    STATE["balance"] = str(u_data.get("claimable_now", "0.0000"))

    return {"headers": headers, "tg_id": tg_id, "username": user, "data": d, "dev_id": dev_id}

# ============ CORE LOGIC ============
async def fetch_state(url, headers, init_data, tg_id, dev_id, client_inst):
    """Cuma ngecek state (energy & pending) tanpa nge-tap."""
    s = post_request(url, params={'action': 'tap_v2_state', 't': get_timestamp()}, 
                     data=json.dumps({"initData": init_data, "tg_id": str(tg_id), "device_id": dev_id, "client_instance": client_inst}), headers=headers).json()
    return s

async def run_tap(url, headers, init_data, tg_id, dev_id, client_inst, client, s):
    """Eksekusi tap. Asumsi state (s) udah didapet dari fetch_state."""
    nonce = s.get("session_nonce")
    seq = int(s.get("last_seq", 0)) + 1
    energy = float(s.get("energy", 0))
    energy_cost = 10
    
    STATE["pending"] = float(s.get("pending_reward", 0))
    
    add_event("Tapping started (10 Taps/batch)...", "cyan")
    
    while energy >= energy_cost:
        taps_to_send = 10 
        if energy < (taps_to_send * energy_cost):
            taps_to_send = int(energy // energy_cost)
        if taps_to_send <= 0: break
        
        bid = f"b_{uuid.uuid4().hex[:20]}"
        r = post_request(url, params={'action': 'tap_v2_sync', 't': get_timestamp()},
            data=json.dumps({"initData": init_data, "tg_id": str(tg_id), "device_id": dev_id, "client_instance": client_inst, "session_nonce": nonce, "seq": seq, "batch_id": bid, "taps": taps_to_send}), headers=headers).json()
        
        if r.get("status") == "success":
            acc, rej = r.get("accepted", 0), r.get("rejected", 0)
            energy = float(r.get("energy", energy))
            STATE["energy"] = energy
            STATE["pending"] = float(r.get("pending_reward", STATE["pending"]))
            seq = int(r.get("next_seq", seq + 1))
            
            add_event(f"⚡ {taps_to_send} TAPS ({acc} SUCCESS) ({rej} REJECT)", "green" if rej == 0 else "yellow")
            if acc == 0: await asyncio.sleep(1)
        elif is_unauthorized_error(r):
            add_event("Unauthorized, relogin...", "red")
            i, h = await relogin(client)
            if i and h: return i, h["headers"]
            break
        else:
            add_event(f"Sync error: {r.get('message', 'Unknown')}", "red")
            await asyncio.sleep(2)
        await asyncio.sleep(0.5)

    return init_data, headers

async def do_claim(url, headers, init_data, tg_id, dev_id, preview, client):
    if preview <= 0: return init_data, headers, False
    
    add_event("Mencoba claim...", "cyan")
    await asyncio.sleep(random.uniform(2, 4))
    payload = {"initData": init_data, "request_id": str(uuid.uuid4()), "device_id": dev_id, "tg_id": str(tg_id), "claim_preview": preview}
    r = post_request(url, params={'action': 'claim', 't': get_timestamp()}, data=json.dumps(payload), headers=headers).json()
    
    if is_unauthorized_error(r):
        i, h = await relogin(client)
        if i and h: return i, h["headers"], False
        return init_data, headers, False
        
    if r.get("status") == "success":
        amt = r.get("claimed_amount", "0")
        add_event(f"💰 CLAIM OK! +{amt} ATF", "bold green")
        STATE["pending"] = 0
        try: STATE["balance"] = f"{float(STATE['balance']) + float(amt):.4f}"
        except: pass
        return init_data, headers, True
    else:
        add_event(f"Claim failed: {r.get('status')}", "red")
        return init_data, headers, False

async def run_tasks(url, headers, init_data, tg_id, dev_id, client, srv_cd):
    for task in TASKS:
        rem = get_task_cooldown_remaining(task['task_id'], srv_cd)
        if rem > 0:
            STATE["task_status"][task['name']] = "SKIP"
            continue
            
        STATE["task_status"][task['name']] = "RUNNING"
        payload = {"initData": init_data, "request_id": str(uuid.uuid4()), "device_id": dev_id, "tg_id": str(tg_id), "task_id": task['task_id'], "client_started_at": int(time.time())}
        r = post_request(url, params={'action': 'start_task', 't': get_timestamp()}, data=json.dumps(payload), headers=headers).json()
        
        if r.get("status") == "error" and "cooldown" in r.get("message", "").lower():
            STATE["task_status"][task['name']] = "SKIP"
            continue
            
        if r.get("status") == "success" and r.get("started"):
            wait = task.get('wait_time', 15)
            for _ in range(wait): await asyncio.sleep(1)
            
            c_payload = {"initData": init_data, "request_id": str(uuid.uuid4()), "device_id": dev_id, "tg_id": str(tg_id), "task_id": task['task_id'], "client_started_at": int(time.time())}
            c = post_request(url, params={'action': 'claim_task', 't': get_timestamp()}, data=json.dumps(c_payload), headers=headers).json()
            
            if c.get("status") == "success":
                STATE["task_status"][task['name']] = "DONE"
                add_event(f"Task {task['name']} sukses", "green")
                st = load_tasks_state()
                st[task['task_id']] = {'last_claim': int(time.time())}
                save_tasks_state(st)
            else:
                STATE["task_status"][task['name']] = "FAILED"
        else:
            STATE["task_status"][task['name']] = "SKIP"
        await asyncio.sleep(2)

# ============ MAIN LOOP ============
async def main():
    console.clear()
    console.print("[bold yellow]Sedang login ke Telegram...[/]")
    
    client = TelegramClient("atf_miner", API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("Nomor (+62): ")
        await client.send_code_request(phone)
        otp = input("OTP: ")
        try: await client.sign_in(phone, otp)
        except SessionPasswordNeededError:
            pw = input("2FA Password: ")
            await client.sign_in(password=pw)
            
    console.print("[bold green]Login Telegram OK! Mengambil data ATF...[/]")
    
    init_data = await get_fresh_init_data(client, skip_start=False)
    res = atf_login(init_data)
    if not res: console.print("[red]ATF Login gagal![/]"); sys.exit()
    
    STATE["username"] = res['username']
    headers = res['headers']
    tg_id = res['tg_id']
    dev_id = res['dev_id']
    srv_cd = res['data'].get("task_cooldowns", {})
    client_inst = f"c_{uuid.uuid4().hex[:28]}"
    
    console.clear()
    
    # Target energy awal (acak 70-90%)
    target_pct = random.randint(75, 85)
    
    with Live(draw_ui(), refresh_per_second=4, screen=True) as live:
        while True:
            try:
                # 1. Ambil state terbaru dari server
                s = await fetch_state(URL_API, headers, init_data, tg_id, dev_id, client_inst)
                
                if s.get("status") == "success":
                    energy = float(s.get("energy", 0))
                    max_energy = float(s.get("max_energy", 1997))
                    STATE["energy"] = energy
                    STATE["max_energy"] = max_energy
                    STATE["pending"] = float(s.get("pending_reward", 0))
                    pct = (energy / max_energy) * 100 if max_energy > 0 else 0
                else:
                    # Kalau gagal ambil state (misal unauthorized), relogin
                    if is_unauthorized_error(s):
                        add_event("Session expired, relogin...", "red")
                        init_data, new_res = await relogin(client)
                        if new_res:
                            headers = new_res['headers']
                            res = new_res
                    await asyncio.sleep(2)
                    continue

                # 2. Logika Tap: Tunggu sampai energy nyampe target (70-90%)
                if pct >= target_pct:
                    add_event(f"Energy {pct:.1f}% (Target {target_pct}%). Mulai tap!", "cyan")
                    init_data, headers = await run_tap(URL_API, headers, init_data, tg_id, dev_id, client_inst, client, s)
                    
                    # Setelah tap, random target baru buat siklus berikutnya
                    target_pct = random.randint(75, 85)
                    
                    # Setelah tap, coba claim kalau pending lumayan gede
                    if STATE["pending"] >= 0.5:
                        init_data, headers, ok = await do_claim(URL_API, headers, init_data, tg_id, dev_id, STATE["pending"], client)
                
                # 3. Kalau energy belum nyampe target, ngapain? Kerjain task aja
                elif pct < target_pct:
                    # Cek dulu, kalau ada task yang READY, kerjain sambil nunggu energy
                    any_task_ready = any(get_task_cooldown_remaining(t['task_id'], srv_cd) <= 0 for t in TASKS)
                    if any_task_ready:
                        await run_tasks(URL_API, headers, init_data, tg_id, dev_id, client, srv_cd)
                        live.update(draw_ui())
                        await asyncio.sleep(2)
                        continue

                # 4. Claim independen (kalau pending gede tapi gak jadi tap)
                if STATE["pending"] >= 1.0 and pct < target_pct:
                    init_data, headers, ok = await do_claim(URL_API, headers, init_data, tg_id, dev_id, STATE["pending"], client)

                # 5. Sync Wallet tiap 30 detik (biar balance update)
                # Karena loop jalan tiap ~1 detik, kita hitung pakai modulo waktu
                if int(time.time()) % 30 == 0:
                    sw_payload = {"initData": init_data, "request_id": str(uuid.uuid4()), "device_id": dev_id, "tg_id": str(tg_id), "wallet": res['data'].get('user', {}).get('wallet_address', ''), "public_key": "", "wallet_state_init": "", "network": "", "proof": None, "refresh_holding": 0, "fg_visible": 1, "fg_epoch": int(time.time() * 1000), "activity_lease": res['data'].get('activity_lease_token', '')}
                    sw_res = post_request(URL_API, params={'action': 'sync_wallet', 't': get_timestamp()}, data=json.dumps(sw_payload), headers=headers).json()
                    
                    if sw_res.get("status") == "success" and "user" in sw_res:
                        u = sw_res["user"]
                        STATE["holding"] = str(u.get("wallet_holding_atf", STATE["holding"]))
                        STATE["balance"] = str(u.get("claimable_now", STATE["balance"]))
                    
                    await asyncio.sleep(1) # Biar gak double request di detik yang sama

                live.update(draw_ui())
                await asyncio.sleep(1) # Jeda pengecekan state
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                add_event(f"Loop Error: {e}", "red")
                live.update(draw_ui())
                await asyncio.sleep(3)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
