#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☁️ CLOUDEARN AUTO WATCH BOT v2.2
- Reward + limit aware
- Gagal 1x → kick dari rotasi (no retry, no spam)
- Jeda 7s antar network
- Auto-stop kalau semua DONE / KICKED
"""

import requests
import time
import urllib.parse
import sys
import os
import json

# ============================================================
# WARNA
# ============================================================
C = '\033[96m'
LC = '\033[1;96m'
Y = '\033[93m'
G = '\033[92m'
R = '\033[91m'
B = '\033[94m'
W = '\033[97m'
BLD = '\033[1m'
RS = '\033[0m'
DIM = '\033[2m'
M = '\033[95m'

# ============================================================
# BANNER
# ============================================================
BANNER = f"""
{C}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    ██████╗██╗      ██████╗ ██╗   ██╗██████╗             ║
║   ██╔════╝██║     ██╔═══██╗██║   ██║██╔══██╗            ║
║   ██║     ██║     ██║   ██║██║   ██║██║  ██║            ║
║   ██║     ██║     ██║   ██║██║   ██║██║  ██║            ║
║   ╚██████╗███████╗╚██████╔╝╚██████╔╝██████╔╝            ║
║    ╚═════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝             ║
║                                                          ║
║                 {Y}☁️  @CloudEarnBot ☁️{RS}{C}                    ║
║              {LC}Developed by SCRIPTYXSOUU{RS}{C}                 ║
║         {G}AUTO FARM • AUTO CLAIM • AUTO TASK{RS}{C}             ║
╚══════════════════════════════════════════════════════════╝{RS}
"""

MENU = f"""
{C}╔══════════════════════════════════════════════╗
║              {Y}☁️ @CloudEarnBot ☁️{RS}{C}            ║
║          {LC}AUTO FARMING & WATCH ADS{RS}{C}           ║
╠══════════════════════════════════════════════╣
║  {G}[1] 🚀 Start Farming{RS}{C}                       ║
║  {Y}[2] 🔑 Set Init_Data (Bearer opsional){RS}{C}     ║
║  {B}[3] 💰 Check Balance{RS}{C}                       ║
║  {LC}[4] 👆 Taptap Auto (100/tap){RS}{C}              ║
║  {LC}[5] ⛏️  Start Mining (Auto Re-Start){RS}{C}       ║
║                                              ║
║  {R}[0] ❌ Exit{RS}{C}                                ║
╚══════════════════════════════════════════════╝{RS}
"""

CONFIG_FILE = "cloud.json"

INIT_DATA = ""
AUTH_TOKEN = ""
APIKEY = ""
START_PARAM = ""
SUPABASE_URL = "https://supabase.cloudearn.org"
ORIGIN_URL = "https://cloudearn.org"
WATCH_DURATION = 20
DELAY_BETWEEN_NETWORKS = 7

# ============================================================
# NETWORK MAP
# ============================================================
NETWORKS = {
    "adsgram":   {"reward": 30, "limit": 10, "label": "Adsgram"},
    "monetag":   {"reward": 10, "limit": 8,  "label": "Monetag"},
    "towerads":  {"reward": 10, "limit": 10, "label": "TowerAds"},
    "monetix":   {"reward": 5,  "limit": 15, "label": "Monetix"},
    "tads":      {"reward": 5,  "limit": 10, "label": "Tads"},
    "richads":   {"reward": 5,  "limit": 8,  "label": "RichAds"},
    "onclicka":  {"reward": 5,  "limit": 7,  "label": "OnClickA"},
    "gigapup":   {"reward": 5,  "limit": 5,  "label": "GigaPup"},
    "adexium":   {"reward": 5,  "limit": 10, "label": "Adexium"},
    "adsgalaxy": {"reward": 5,  "limit": 5,  "label": "AdsGalaxy"},
    "adloop":    {"reward": 5,  "limit": 3,  "label": "Adloop"},
}

HEADERS = {}
TAPS_PER_REQUEST = 100
TAP_VALUE = 5
TICKET_AGING_INTERVAL = 15
TICKET_AGING_MAX = 180


# ============================================================
# CONFIG
# ============================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def set_data(force=False):
    global INIT_DATA, AUTH_TOKEN, APIKEY, START_PARAM, HEADERS
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

    old_config = load_config()
    old_auth_token = old_config.get("auth_token", "") if old_config else ""

    print(f"\n{Y}🔑 SET INIT_DATA — ☁️ CloudEarn{RS}")
    print(f"{C}{'='*50}{RS}")
    init_data = input(f"{LC}init_data (wajib): {RS}").strip()
    if not init_data:
        print(f"{R}❌ init_data tidak boleh kosong!{RS}")
        time.sleep(2)
        return False

    print(f"{Y}Bearer token (opsional, Enter untuk skip):{RS}")
    auth_token = input(f"{LC}Bearer token: {RS}").strip()
    if not auth_token and old_auth_token:
        auth_token = old_auth_token
    if auth_token and not auth_token.startswith("Bearer "):
        auth_token = "Bearer " + auth_token

    INIT_DATA = init_data
    AUTH_TOKEN = auth_token
    APIKEY = AUTH_TOKEN.replace("Bearer ", "") if AUTH_TOKEN else ""

    parsed = urllib.parse.parse_qs(INIT_DATA)
    sp = parsed.get("start_param", [None])[0]
    START_PARAM = sp if (sp and sp != "null") else None

    HEADERS = {
        "x-telegram-init-data": INIT_DATA,
        "user-agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.181 Mobile Safari/537.36 Telegram-Android/12.6.4",
        "content-type": "application/json",
        "accept": "*/*",
        "origin": "https://cloudearn.org",
        "referer": "https://cloudearn.org/",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "x-requested-with": "org.telegram.messenger.web",
    }
    if AUTH_TOKEN:
        HEADERS["authorization"] = AUTH_TOKEN
        HEADERS["apikey"] = APIKEY

    save_config({
        "platform": "cloudearn",
        "init_data": INIT_DATA,
        "auth_token": AUTH_TOKEN,
        "apikey": APIKEY,
        "start_param": START_PARAM,
        "supabase_url": SUPABASE_URL,
        "origin_url": ORIGIN_URL,
        "headers": HEADERS
    })
    print(f"{G}✅ Config disimpan!{RS}")
    time.sleep(1.5)
    return True


# ============================================================
# SUPABASE
# ============================================================
def supabase_request(action, payload=None, timeout=30):
    url = f"{SUPABASE_URL}/functions/v1/api"
    resp = requests.post(url, params={"action": action}, json=payload or {},
                         headers=HEADERS, timeout=timeout)
    if resp.status_code != 200:
        try: err = resp.json()
        except: err = resp.text
        raise Exception(f"{resp.status_code}: {err}")
    return resp.json()


def _init_payload():
    return {
        "start_param": START_PARAM if START_PARAM else None,
        "fp_hash": "88bba40c3cc06e4bc78f354c012a1d5b0f0307f72934bc902352886f2d03cc9b",
        "webgl_hash": "bfc8fbb0012f8c92b0f1f0e178d08ba95ec000335360ca22edcf270a098ddab2",
        "audio_hash": "05d0c5571616fb4731d584d3a16738cc81dcd566dcb2598bee29200a1eeb4a46",
        "tz": "Asia/Jakarta",
        "lang": "id-ID",
        "platform": "Linux aarch64"
    }

def init_session(debug=True):
    if not HEADERS or not HEADERS.get("x-telegram-init-data"):
        return False
    try:
        r = supabase_request("init", _init_payload())
        if debug:
            u = r.get("user", {})
            print(f"{G}  [DEBUG] session OK | user={u.get('username','?')} | bal={u.get('balance_cloud',0)}{RS}")
        return True
    except Exception as e:
        if debug: print(f"{R}  [DEBUG] init gagal: {e}{RS}")
        return False

def get_user_data(): return supabase_request("init", _init_payload())
def get_ad_stats(): return supabase_request("ad_stats", {})

def issue_ticket(network):
    data = supabase_request("ad_ticket_issue", {"purpose": "task_ads", "network": network})
    return data.get("ticket")

def record_ad_view(network, ticket):
    return supabase_request("record_ad_view", {"network": network, "ad_ticket_id": ticket})

# TAPTAP
def taptap_status(): return supabase_request("taptap_status", {})
def taptap_tap(taps): return supabase_request("taptap_tap", {"taps": taps})
def taptap_unlock(tid): return supabase_request("taptap_unlock", {"ad_ticket_id": tid})
def issue_taptap_ticket(network="adsgram"):
    return supabase_request("ad_ticket_issue", {"purpose": "taptap", "network": network}).get("ticket")

# MINING
def mining_status(): return supabase_request("mining_status", {})
def mining_start(): return supabase_request("mining_start", {})


# ============================================================
# HELPERS
# ============================================================
def now_ms():
    return int(time.time() * 1000)


def human_wait(seconds, label="Wait"):
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"\r  {Y}⌛ {label} {i:2d}s...{RS}   ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 45 + "\r")
    sys.stdout.flush()


# ============================================================
# FARMING v2.2 — One-Strike Kick
# ============================================================
def start_farming():
    if not HEADERS or not HEADERS.get("x-telegram-init-data"):
        print(f"{R}❌ Init_Data belum diset!{RS}")
        time.sleep(2)
        return

    if not init_session(debug=True):
        print(f"{R}❌ Session gagal!{RS}")
        input(f"{Y}Tekan Enter...{RS}")
        return

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    print(f"\n{G}🚀 Session OK. Auto watch dimulai.{RS}")
    print(f"{Y}⏱  Jeda antar network: {DELAY_BETWEEN_NETWORKS}s{RS}")
    print(f"{Y}🛡  Gagal 1x → network di-KICK, lanjut yang lain (no retry).{RS}")
    print(f"{Y}⏹ Auto-stop saat SEMUA network DONE atau KICKED.{RS}")
    print(f"{Y}⏹ Ctrl+C untuk berhenti manual.{RS}\n")
    time.sleep(2)

    grand_success = 0
    grand_failed = 0
    grand_exhausted = 0
    total_cloud_earned = 0
    cycle_count = 0

    done_networks = set()        # limit harian tercapai
    kicked_networks = {}         # {net: reason}

    def all_finished(watched):
        """True kalau semua network DONE atau KICKED."""
        for net, cfg in NETWORKS.items():
            if net in kicked_networks:
                continue
            cnt = int(watched.get(net, 0) or 0)
            if cnt < cfg["limit"]:
                return False
        return True

    try:
        while True:
            cycle_count += 1

            # ==== Ambil stats server ====
            try:
                stats = get_ad_stats()
            except Exception as e:
                print(f"{R}❌ Gagal ambil ad_stats: {e}{RS}")
                time.sleep(15)
                continue

            watched = stats.get("data", {}) or {}
            cooldowns = stats.get("cooldowns", {}) or {}

            # ==== Render table ====
            os.system('cls' if os.name == 'nt' else 'clear')
            print(BANNER)
            print(f"{C}═══ CYCLE #{cycle_count} ═══{RS}")
            print(f"{DIM}  All-time: {G}✅ {grand_success}{RS}  "
                  f"{R}❌ {grand_failed}{RS}  "
                  f"{Y}⛔ {grand_exhausted}{RS}  "
                  f"{R}🚫 {len(kicked_networks)}{RS}  "
                  f"| {G}+{total_cloud_earned} cloud{RS}\n")

            print(f"  {W}{'Network':<12}{'Reward':<8}{'Sisa':<8}{'Limit':<8}{'Status'}{RS}")
            print(f"  {DIM}{'─'*60}{RS}")

            ready = []
            server_cd = []

            for net, cfg in NETWORKS.items():
                label = cfg["label"]
                reward = cfg["reward"]
                limit = cfg["limit"]
                cnt = int(watched.get(net, 0) or 0)
                remaining = max(0, limit - cnt)

                # sudah kicked
                if net in kicked_networks:
                    print(f"  {R}{label:<12}{'+'+str(reward)+' ☁':<8}{remaining:<8}{limit:<8}🚫 KICKED{RS}")
                    continue

                # limit tercapai
                if remaining <= 0:
                    done_networks.add(net)
                    print(f"  {G}{label:<12}{'+'+str(reward)+' ☁':<8}{'0':<8}{limit:<8}✅ DONE{RS}")
                    continue

                # server cooldown
                cd_until = int(cooldowns.get(net, 0) or 0)
                cd_left_s = max(0, (cd_until - now_ms()) // 1000) if cd_until else 0
                if cd_left_s > 0:
                    server_cd.append(net)
                    print(f"  {Y}{label:<12}{'+'+str(reward)+' ☁':<8}{remaining:<8}{limit:<8}⏳ CD {cd_left_s}s{RS}")
                    continue

                # ready
                ready.append(net)
                print(f"  {LC}{label:<12}{'+'+str(reward)+' ☁':<8}{remaining:<8}{limit:<8}▶ READY{RS}")

            print(f"\n  {DIM}Ready: {len(ready)} | ServerCD: {len(server_cd)} | "
                  f"Done: {len(done_networks)}/{len(NETWORKS)} | Kicked: {len(kicked_networks)}{RS}")

            # ==== Semua selesai? ====
            if all_finished(watched):
                print(f"\n{G}🏁 SEMUA network DONE / KICKED. Bot stop.{RS}")
                break

            # ==== Gak ada ready? tunggu ====
            if not ready:
                if server_cd:
                    min_cd = min(
                        max(0, (int(cooldowns.get(n, 0) or 0) - now_ms()) // 1000)
                        for n in server_cd
                    )
                    wait_s = min(min_cd + 3, 120)
                    print(f"\n{Y}⏳ Server cooldown. Tunggu {wait_s}s...{RS}")
                    human_wait(wait_s, "Cooldown")
                    continue
                print(f"\n{Y}⚠ Gak ada ready. Tunggu 60s...{RS}")
                human_wait(60, "Idle")
                continue

            # ==== Proses network ready ====
            for idx, net in enumerate(ready):
                cfg = NETWORKS[net]
                label = cfg["label"]
                reward = cfg["reward"]
                limit = cfg["limit"]

                print(f"\n{LC}  ▶ Nonton iklan: {label} (+{reward} ☁){RS}")

                # ==== Issue ticket ====
                try:
                    ticket = issue_ticket(net)
                    if not ticket:
                        raise Exception("no ticket returned")
                    print(f"  {Y}Ticket: {ticket}{RS}")
                except Exception as e:
                    err = str(e)
                    print(f"  {R}🚫 {label}: KICKED — ticket error.{RS}")
                    print(f"  {DIM}   {err[:120]}{RS}")
                    kicked_networks[net] = "ticket_error"
                    grand_failed += 1
                    time.sleep(DELAY_BETWEEN_NETWORKS)
                    continue

                # ==== Nonton ad ====
                print(f"  {C}Nonton {WATCH_DURATION}s...{RS}")
                for i in range(WATCH_DURATION):
                    time.sleep(1)
                    bar_len = 20
                    filled = int((i + 1) / WATCH_DURATION * bar_len)
                    bar = '█' * filled + '░' * (bar_len - filled)
                    sys.stdout.write(f"\r  {G}[{bar}] {i+1:2d}/{WATCH_DURATION}s{RS}")
                    sys.stdout.flush()
                print()

                # ==== Record ====
                try:
                    res = record_ad_view(net, ticket)
                    got = int(res.get("reward", reward) or reward)
                    total_cloud_earned += got
                    grand_success += 1
                    print(f"  {G}✅ {label}: +{got} ☁{RS}")

                    # refresh cek limit
                    try:
                        s3 = get_ad_stats()
                        w3 = s3.get("data", {}) or {}
                        cnt_now = int(w3.get(net, 0) or 0)
                        if cnt_now >= limit:
                            done_networks.add(net)
                            print(f"  {G}   {label} limit tercapai ({cnt_now}/{limit}).{RS}")
                    except Exception:
                        pass

                except Exception as e:
                    err = str(e)
                    err_lower = err.lower()

                    if "ad_required" in err_lower or "no ads" in err_lower or "quota" in err_lower:
                        print(f"  {Y}⛔ {label}: ABIS → skip permanen.{RS}")
                        done_networks.add(net)
                        grand_exhausted += 1
                    else:
                        print(f"  {R}🚫 {label}: KICKED — record error.{RS}")
                        print(f"  {DIM}   {err[:120]}{RS}")
                        kicked_networks[net] = "record_error"
                        grand_failed += 1

                # ==== Jeda antar network ====
                if idx < len(ready) - 1:
                    print(f"  {DIM}   ⏱ jeda {DELAY_BETWEEN_NETWORKS}s...{RS}")
                    time.sleep(DELAY_BETWEEN_NETWORKS)

            time.sleep(2)

    except KeyboardInterrupt:
        print(f"\n{R}⏹ Dihentikan user.{RS}")
    except Exception as e:
        print(f"{R}❌ Error: {e}{RS}")
        import traceback; traceback.print_exc()

    # ===== SUMMARY =====
    print(f"\n{C}═══════════════════════════════════════════════════════════{RS}")
    print(f"{G}              🏁 FARMING SUMMARY{RS}")
    print(f"{C}═══════════════════════════════════════════════════════════{RS}")
    print(f"  Cycles         : {cycle_count}")
    print(f"  {G}✅ Berhasil   : {grand_success}{RS}")
    print(f"  {R}❌ Gagal      : {grand_failed}{RS}")
    print(f"  {Y}⛔ Limit/Abis : {grand_exhausted}{RS}")
    print(f"  {G}☁  Cloud      : +{total_cloud_earned}{RS}")
    print(f"  {LC}🎯 Done net  : {len(done_networks)}/{len(NETWORKS)}{RS}")
    print(f"  {R}🚫 Kicked net : {len(kicked_networks)}{RS}")
    if kicked_networks:
        for n, reason in kicked_networks.items():
            print(f"     {DIM}• {n}: {reason}{RS}")
    print(f"{C}═══════════════════════════════════════════════════════════{RS}\n")
    input(f"{C}Tekan Enter untuk kembali ke menu...{RS}")


# ============================================================
# BALANCE
# ============================================================
def check_balance():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    if not HEADERS or not HEADERS.get("x-telegram-init-data"):
        print(f"{R}❌ Init_Data belum diset!{RS}")
        time.sleep(2)
        return
    if not init_session(debug=True):
        input(f"{Y}Enter...{RS}")
        return
    print(f"{B}💰 Mengecek Balance...{RS}\n")
    try:
        data = get_user_data()
        u = data.get("user", {})
        if not u:
            print(f"{R}❌ Gagal ambil data.{RS}")
        else:
            print(f"{G}👤 {u.get('username','N/A')} (ID: {u.get('tg_id','N/A')}){RS}")
            print(f"{C}   {u.get('first_name','')} {u.get('last_name','')} — {u.get('country_name','N/A')}{RS}")
            print(f"{Y}───────────────────────────{RS}")
            print(f"{G}☁️ Cloud: {u.get('balance_cloud',0)}{RS}")
            print(f"{G}💰 USDT : {u.get('balance_usdt',0)}{RS}")
            print(f"{G}📈 Total Cloud: {u.get('total_earned_cloud',0)}{RS}")
            print(f"{G}📈 Total USDT : {u.get('total_earned_usdt',0)}{RS}")
            print(f"{C}👥 Refs: {u.get('referral_count',0)} — Earnings: {u.get('ref_earnings_cloud',0)}{RS}")
            print(f"{B}📊 {'✅ Premium' if u.get('is_premium') else '⬜ Free'}{RS}")
    except Exception as e:
        print(f"{R}❌ Error: {e}{RS}")
    input(f"\n{C}Enter untuk kembali...{RS}")


# ============================================================
# TAPTAP
# ============================================================
def start_taptap():
    if not HEADERS or not HEADERS.get("x-telegram-init-data"):
        print(f"{R}❌ Init_Data belum diset!{RS}")
        time.sleep(2)
        return
    if not init_session(debug=True):
        input(f"{Y}Enter...{RS}")
        return

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    print(f"{Y}⏹ Ctrl+C untuk stop.{RS}\n")

    def wait_cd(sec, label):
        for i in range(sec, 0, -1):
            sys.stdout.write(f"\r  {Y}⌛ {label} {i}s...{RS}   ")
            sys.stdout.flush()
            time.sleep(1)
        print()

    try:
        while True:
            try:
                st = taptap_status()
                earned = st.get("earned_today", 0)
                limit = st.get("limit", 500)
                locked = st.get("locked", False)
                next_lock = st.get("next_lock_at", 100)

                print(f"{C}📊 earned={G}{earned}{C}/{limit} | locked={Y}{locked}{C} | next_lock={Y}{next_lock}{RS}")

                if earned >= limit:
                    print(f"\n{G}✅ Limit harian tercapai. Bot berhenti.{RS}")
                    break

                if locked:
                    print(f"\n{Y}🔒 Locked! Unlock...{RS}")
                    ticket = None
                    try:
                        ticket = issue_taptap_ticket("adsgram")
                        print(f"  {G}✓ Ticket: {ticket}{RS}")
                    except Exception as e:
                        print(f"  {R}❌ Issue gagal: {e}{RS}")
                        wait_cd(30, "Retry")
                        continue

                    unlocked = False
                    waited = 0
                    while waited < TICKET_AGING_MAX:
                        try:
                            taptap_unlock(ticket)
                            print(f"  {G}✅ Unlocked! ({waited}s){RS}")
                            unlocked = True
                            break
                        except Exception as e:
                            if "ticket_too_early" in str(e):
                                wait_cd(TICKET_AGING_INTERVAL, f"aging ({waited}s)")
                                waited += TICKET_AGING_INTERVAL
                                continue
                            else:
                                print(f"  {R}❌ {e}{RS}")
                                break
                    if not unlocked:
                        wait_cd(30, "Retry")
                    continue

                remaining_lock = next_lock - earned
                remaining_total = limit - earned
                taps = min(TAPS_PER_REQUEST,
                           max(1, remaining_lock // TAP_VALUE),
                           max(1, remaining_total // TAP_VALUE))
                if taps <= 0: taps = 1

                print(f"{LC}👆 Tap {taps}...{RS}")
                try:
                    res = taptap_tap(taps)
                    print(f"  {G}✓ +{res.get('credited',0)} | earned: {res.get('earned_today',earned)} | locked: {res.get('locked',False)}{RS}")
                except Exception as e:
                    if "max" in str(e).lower() or "too many" in str(e).lower():
                        try:
                            res = taptap_tap(10)
                            print(f"  {G}✓ +{res.get('credited',0)}{RS}")
                        except Exception as e2:
                            print(f"  {R}❌ {e2}{RS}")
                    else:
                        print(f"  {R}❌ {e}{RS}")
                time.sleep(2)
            except Exception as e:
                print(f"{R}❌ Loop: {e}{RS}")
                time.sleep(5)
    except KeyboardInterrupt:
        print(f"\n{R}⏹ Stop.{RS}")
        time.sleep(1.5)


# ============================================================
# MINING
# ============================================================
def start_mining():
    if not HEADERS or not HEADERS.get("x-telegram-init-data"):
        print(f"{R}❌ Init_Data belum diset!{RS}")
        time.sleep(2)
        return
    if not init_session(debug=True):
        input(f"{Y}Enter...{RS}")
        return

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    print(f"{Y}⏹ Ctrl+C untuk stop.{RS}\n")

    try:
        while True:
            try:
                st = mining_status()
                state = st.get("state", "unknown")
                session = st.get("session")
                rate = st.get("rate_per_hour", 40)

                print(f"{C}📊 state: {LC}{state}{RS}")
                if session:
                    print(f"  {Y}• Expires: {session.get('expires_at','-')}{RS}")
                    print(f"  {Y}• Hours  : {session.get('hours_total',1)}{RS}")
                    print(f"  {Y}• Reward : {session.get('reward',0)} cloud{RS}")
                    print(f"  {Y}• Rate   : {rate}/hour{RS}")

                if state == "running":
                    print(f"\n{G}✅ Mining jalan. Cek 60s lagi...{RS}")
                    for i in range(60, 0, -1):
                        sys.stdout.write(f"\r  {Y}⏳ {i}s...{RS}   ")
                        sys.stdout.flush()
                        time.sleep(1)
                    print()
                    continue

                if state in ("idle", "unknown"):
                    print(f"\n{LC}⛏️  Start mining...{RS}")
                    try:
                        print(f"  {G}✓ {mining_start()}{RS}")
                        time.sleep(5)
                    except Exception as e:
                        print(f"  {R}❌ {e}{RS}")
                        time.sleep(10)
                else:
                    print(f"\n{Y}⚠️ state={state}, tunggu 30s{RS}")
                    time.sleep(30)
            except Exception as e:
                print(f"{R}❌ Loop: {e}{RS}")
                time.sleep(10)
    except KeyboardInterrupt:
        print(f"\n{R}⏹ Stop.{RS}")
        time.sleep(1.5)


# ============================================================
# MAIN
# ============================================================
def main():
    global HEADERS, INIT_DATA, AUTH_TOKEN, APIKEY, START_PARAM, SUPABASE_URL, ORIGIN_URL
    config = load_config()
    if config:
        INIT_DATA = config.get("init_data", "")
        AUTH_TOKEN = config.get("auth_token", "")
        APIKEY = config.get("apikey", "")
        START_PARAM = config.get("start_param", None)
        if START_PARAM == "null": START_PARAM = None
        SUPABASE_URL = config.get("supabase_url", "https://supabase.cloudearn.org")
        ORIGIN_URL = config.get("origin_url", "https://cloudearn.org")
        HEADERS = config.get("headers", {})

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(BANNER)
        print(MENU)

        if HEADERS and HEADERS.get("x-telegram-init-data"):
            print(f"{G}🔑 Config: Aktif ✅{RS}")
        else:
            print(f"{R}🔑 Config: Belum diset ❌{RS}")

        choice = input(f"\n{LC}Select » {RS}").strip()

        if choice == "1": start_farming()
        elif choice == "2": set_data(force=True)
        elif choice == "3": check_balance()
        elif choice == "4": start_taptap()
        elif choice == "5": start_mining()
        elif choice == "0":
            print(f"\n{R}❌ Exit...{RS}")
            sys.exit(0)
        else:
            print(f"{R}❌ Invalid!{RS}")
            time.sleep(1)


if __name__ == "__main__":
    main()
