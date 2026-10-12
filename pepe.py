#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║  🚀 PEPEFLOW X CLOCKADS X COINSZON                           ║
║  AUTO CLAIM • AUTO GAMES • AUTO DOUBLE • AUTO SKIP LIMIT      ║
║  🔐 AUTH via init_data (NO PHPSESSID manual)                  ║
║  🎲 FINGERPRINT RANDOM setiap reauth                          ║
║  🎁 AUTO CLAIM PENDING WIN (WITH AD PROOF)                    ║
║  📅 AUTO CLAIM DAILY BONUS                                    ║
║  🎡 CoinBot: LUCKY WHEEL SPINS EDITION                        ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, random, re, requests, urllib.parse
from datetime import datetime
from collections import deque

# ========== WARNA ==========
R = '\033[91m'; G = '\033[92m'; Y = '\033[93m'; B = '\033[94m'; C = '\033[96m'; W = '\033[97m'
M = '\033[95m'
GOLD = '\033[38;5;220m'; PURPLE = '\033[38;5;141m'; PINK = '\033[38;5;206m'
RESET = '\033[0m'

# ========== KONFIGURASI ==========
PEPE_CONFIG  = "pepeflow_config.json"
CLOCK_CONFIG = "clockads_config.json"
COIN_CONFIG  = "coinszon_config.json"

PEPE_URL  = "https://pepeflow.com"
CLOCK_URL = "https://clockads.in"
COIN_URL  = "https://coinszon.com"

UA = "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.47 Mobile Safari/537.36 Telegram-Android/12.6.4"
COIN_UA = "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.7977.87 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"

# ---------- Game config per site ----------
PEPE_GAMES = ["lucky_wheel"]
PEPE_GAME_MAP = {"lucky_wheel": {"display": "SPIN", "icon": "🎡"}}

CLOCK_GAMES = ["lucky_wheel"]
CLOCK_GAME_MAP = {"lucky_wheel": {"display": "SPIN", "icon": "🎡"}}

COIN_GAMES = ["lucky_wheel"]
COIN_GAME_MAP = {"lucky_wheel": {"display": "SPIN", "icon": "🎡"}}

# ========== CONFIG ==========
class BaseConfig:
    def __init__(self, file):
        self.file = file
        self.init_data = None
        self.telegram_id = None
        self.telegram_username = None

    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file) as f:
                    d = json.load(f)
                self.init_data = d.get('init_data')
                self.telegram_id = d.get('telegram_id')
                self.telegram_username = d.get('telegram_username')
                return True
            except:
                return False
        return False

    def save(self):
        with open(self.file, 'w') as f:
            json.dump({
                'init_data': self.init_data,
                'telegram_id': self.telegram_id,
                'telegram_username': self.telegram_username
            }, f, indent=2)

# ========== UTILITY ==========
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def safe_float(val, default=0.0):
    if val is None: return default
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        try: return float(val.replace(',', '').strip())
        except: return default
    return default

def safe_int(val, default=0):
    return int(safe_float(val, default))

def live_timer(seconds, msg="⏳ Menunggu"):
    if seconds < 1: return
    while seconds > 0:
        m, s = divmod(seconds, 60)
        sys.stdout.write(f"\r{Y}{msg} {m:02d}:{s:02d} {RESET}  ")
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

def ad_progress(seconds=10, label="📺 Watching ad"):
    for i in range(seconds, 0, -1):
        bar_len = 15
        filled = int((seconds - i) / seconds * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        sys.stdout.write(f"\r{G}{label} [{bar}] {i}s left{RESET}")
        sys.stdout.flush()
        time.sleep(1)
    print()

# ========== BASE BOT ==========
class BaseBot:
    def __init__(self, url, cfg, game_list, game_map, name, currency):
        self.url = url
        self.cfg = cfg
        self.game_list = game_list
        self.game_map = game_map
        self.name = name
        self.currency = currency
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept": "*/*",
            "Origin": url,
            "Referer": f"{url}/miniapp.php",
            "X-Requested-With": "org.telegram.messenger.web",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Not;A=Brand";v="8","Chromium";v="150","Android WebView";v="150"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
        })
        self.balance = 0.0
        self.cooldowns = {g: 0 for g in game_list}
        self.play_counts = {g: 0 for g in game_list}
        self.doubled_available = {g: False for g in game_list}
        self.status = {g: "Ready" for g in game_list}
        self.rewards = {g: 0 for g in game_list}
        self.logs = deque(maxlen=8)
        self.running = True
        self.retry_doubled = {g: True for g in game_list}
        self.daily_claimed = False
        self.game_index = 0
        self.treasure_token = None
        self.limited_games = set()
        self.unavailable_games = set()
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.start_time = datetime.now()
        self._initial_auth()

    def fmt(self, sec):
        if sec <= 0: return "Ready"
        m, s = divmod(int(sec), 60)
        return f"{m}m{s}s" if m else f"{s}s"

    def log(self, msg):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # ---------- AUTH ----------
    def _initial_auth(self):
        if not self.cfg.init_data:
            self.log(f"{R}❌ init_data kosong! Bot tidak bisa jalan{RESET}")
            self.running = False
            return False
        return self.reauth()

    def reauth(self):
        if not self.cfg.init_data:
            self.log(f"{R}❌ init_data tidak ada{RESET}")
            return False

        parsed = urllib.parse.parse_qs(self.cfg.init_data)
        user_str = parsed.get('user', [None])[0]
        tid, tuname = "0", ""
        if user_str:
            try:
                u = json.loads(urllib.parse.unquote(user_str))
                tid = str(u.get('id', '0'))
                tuname = u.get('username', '')
            except: pass

        self.cfg.telegram_id = tid
        self.cfg.telegram_username = tuname
        self.cfg.save()

        fingerprint = os.urandom(16).hex()

        files = {
            "init_data": (None, self.cfg.init_data),
            "telegram_id": (None, tid),
            "telegram_username": (None, tuname),
            "auto_login": (None, "1"),
            "fingerprint": (None, fingerprint),
        }
        try:
            resp = self.session.post(f"{self.url}/actions/tg_auth.php", files=files, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    self.log(f"{G}✅ {self.name} auth OK (fp: {fingerprint[:8]}...){RESET}")
                    return True
                else:
                    self.log(f"{R}❌ Auth gagal: {data.get('message', 'unknown')}{RESET}")
                    return False
            else:
                self.log(f"{R}❌ Auth gagal, status {resp.status_code}{RESET}")
                return False
        except Exception as e:
            self.log(f"{R}❌ Auth error: {e}{RESET}")
            return False

    # ---------- HTTP ----------
    def _request(self, method, endpoint, **kwargs):
        if not self.running:
            return None
        url = f"{self.url}{endpoint}"
        try:
            kwargs.setdefault('timeout', 30)
            resp = self.session.request(method, url, **kwargs)

            if resp.status_code == 429:
                self.consecutive_errors += 1
                self.log(f"{R}🚫 429 ({self.consecutive_errors}/{self.max_consecutive_errors}){RESET}")
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.log(f"{R}🛑 {self.name} terlalu banyak 429! Stop{RESET}")
                    self.running = False
                return None
            else:
                self.consecutive_errors = 0

            if resp.status_code in [401, 403] or (resp.status_code == 200 and "Not logged" in resp.text):
                self.log(f"{Y}⚠️ Session expired, reauth...{RESET}")
                if self.reauth():
                    resp = self.session.request(method, url, **kwargs)
                    if "Not logged" in resp.text:
                        self.log(f"{R}❌ Session masih invalid{RESET}")
                        return None
                else:
                    return None

            return resp
        except Exception as e:
            self.log(f"{R}❌ Request error: {e}{RESET}")
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.max_consecutive_errors:
                self.log(f"{R}🛑 {self.name} terlalu banyak error! Stop{RESET}")
                self.running = False
            return None

    def get(self, endpoint):
        return self._request('GET', endpoint)

    def post(self, endpoint, files=None, data=None):
        return self._request('POST', endpoint, files=files, data=data)

    # ---------- Pending Win ----------
    def get_pending(self):
        resp = self.post("/actions/mini_games.php", data={"action": "get_pending"})
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def issue_ad_proof(self, pending_id):
        data = {"action": "issue_ad_proof", "pending_id": str(pending_id)}
        resp = self.post("/actions/mini_games.php", data=data)
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def complete_ad_proof(self, proof_token):
        data = {"action": "complete_ad_proof", "proof_token": proof_token, "ad_clicked": "1"}
        resp = self.post("/actions/mini_games.php", data=data)
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def claim_pending_with_proof(self, pending_id, claim_token, proof_token):
        data = {
            "action": "claim_pending",
            "pending_id": str(pending_id),
            "claim_token": claim_token,
            "ad_completed": "1",
            "proof_token": proof_token
        }
        resp = self.post("/actions/mini_games.php", data=data)
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def claim_pending(self):
        pending = self.get_pending()
        if not pending or pending.get('status') != 'success' or not pending.get('pending'):
            return False

        pending_data = pending['pending']
        pending_id = pending_data.get('id')
        claim_token = pending_data.get('claim_token')
        if not pending_id or not claim_token:
            self.log(f"{R}❌ Pending data incomplete{RESET}")
            return False

        reward = pending_data.get('reward', 0)
        self.log(f"{Y}🎁 Found pending win: {reward} {self.currency}{RESET}")

        proof_resp = self.issue_ad_proof(pending_id)
        if not proof_resp or proof_resp.get('status') != 'success':
            self.log(f"{R}❌ Failed to issue ad proof{RESET}")
            return False

        proof_token = proof_resp.get('proof_token')
        if not proof_token:
            self.log(f"{R}❌ No proof token received{RESET}")
            return False

        ad_progress(10, "📺 Watching ad for pending")

        complete_resp = self.complete_ad_proof(proof_token)
        if not complete_resp or complete_resp.get('status') != 'success':
            self.log(f"{R}❌ Failed to complete ad proof{RESET}")
            return False

        claim_resp = self.claim_pending_with_proof(pending_id, claim_token, proof_token)
        if claim_resp and claim_resp.get('status') == 'success':
            reward_claimed = claim_resp.get('reward', 0)
            self.balance = safe_float(claim_resp.get('new_balance', self.balance))
            self.log(f"{G}✅ Claimed pending win! +{reward_claimed} {self.currency}{RESET}")
            return True
        else:
            err = claim_resp.get('message', 'unknown') if claim_resp else 'no response'
            self.log(f"{R}❌ Claim pending failed: {err}{RESET}")
            return False

    # ---------- Dashboard ----------
    def get_dashboard(self):
        resp = self.get("/pages/load_dashboard.php")
        if resp and resp.status_code == 200:
            html = resp.text
            patterns = [
                r'id="header-user-balance"[^>]*>([\d.,]+\s*PEPE|[\d.,]+)',
                r'id="dash-balance-coin">([\d.,]+)',
                r'Balance:\s*([\d.,]+)',
                r'"balance":\s*([\d.]+)',
            ]
            for p in patterns:
                match = re.search(p, html, re.IGNORECASE)
                if match:
                    self.balance = safe_float(match.group(1))
                    return html
            return html
        return None

    # ---------- Game status ----------
    def get_games_status(self):
        if not self.game_list: return None
        resp = self.get("/pages/load_games.php")
        if resp and resp.status_code == 200:
            html = resp.text
            match = re.search(r'var gameConfigs\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    for g in self.game_list:
                        if g in data:
                            info = data[g]
                            cd = info.get('cooldown_remaining', 0)
                            self.cooldowns[g] = cd
                            self.status[g] = self.fmt(cd) if cd > 0 else "Ready"
                            self.doubled_available[g] = bool(info.get('doubled', False))
                            daily_limit = info.get('daily_limit', None)
                            limit_reached = info.get('limit_reached', False)
                            daily_remaining = info.get('daily_remaining', 999)
                            if daily_limit is not None and daily_limit > 0:
                                if limit_reached or daily_remaining <= 0:
                                    self.limited_games.add(g)
                                else:
                                    self.limited_games.discard(g)
                            else:
                                self.limited_games.discard(g)
                    return data
                except: pass
            for g in self.game_list:
                pattern = rf'{g}.*?cooldown.*?(\d+)'
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    self.cooldowns[g] = int(match.group(1))
                    self.status[g] = self.fmt(self.cooldowns[g]) if self.cooldowns[g] > 0 else "Ready"
        return None

    def has_ready_games(self):
        if not self.game_list: return False
        try:
            self.get_games_status()
            ready = [g for g in self.game_list
                     if g not in self.limited_games
                     and g not in self.unavailable_games
                     and self.cooldowns.get(g, 0) <= 0]
            return len(ready) > 0
        except:
            return False

    def get_ready_games(self):
        if not self.game_list: return []
        try:
            self.get_games_status()
            return [g for g in self.game_list
                    if g not in self.limited_games
                    and g not in self.unavailable_games
                    and self.cooldowns.get(g, 0) <= 0]
        except:
            return []

    def is_all_limited(self):
        if not self.game_list: return False
        return all(g in self.limited_games or g in self.unavailable_games for g in self.game_list)

    # ---------- Play game ----------
    def play_game(self, game, doubled=False, base_reward=None, pick=None, quiz_token=None,
                  answer_index=None, double_token=None, score=None, bombed=None,
                  diamonds=None, survived=None):
        if not self.game_list: return None
        if game in self.limited_games:
            self.log(f"{Y}⏭️ {game} sudah limit, skip{RESET}")
            return None
        if game in self.unavailable_games:
            self.log(f"{Y}⏭️ {game} unavailable, skip{RESET}")
            return None

        files = {
            "action": (None, "play"),
            "game": (None, game),
            "doubled": (None, "1" if doubled else "0")
        }
        if doubled and base_reward is not None:
            files["base_reward"] = (None, str(base_reward))
        if doubled and double_token:
            files["double_token"] = (None, str(double_token))
        if pick is not None: files["pick"] = (None, str(pick))
        if quiz_token is not None: files["quiz_token"] = (None, str(quiz_token))
        if answer_index is not None: files["answer_index"] = (None, str(answer_index))
        if score is not None: files["score"] = (None, str(score))
        if bombed is not None: files["bombed"] = (None, "1" if bombed else "0")
        if diamonds is not None: files["diamonds"] = (None, str(diamonds))
        if survived is not None: files["survived"] = (None, "1" if survived else "0")

        resp = self.post("/actions/mini_games.php", files=files)
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def play_single(self, game):
        if not self.game_list: return None
        if game in self.limited_games:
            self.log(f"{Y}⏭️ {game} sudah limit, skip{RESET}")
            return None
        if game in self.unavailable_games:
            return None

        if self.doubled_available.get(game, False) and self.retry_doubled.get(game, True):
            ad_progress(10, f"📺 {self.game_map[game]['display']} double ad")
            base = random.uniform(1e-7, 5e-6)
            result = self.play_game(game, doubled=True, base_reward=base)
            if result and result.get('status') == 'success':
                return result
            elif result and result.get('status') == 'error':
                if '2x bonus window has expired' in result.get('message', ''):
                    self.retry_doubled[game] = False
            else:
                return result

        if game == "lucky_wheel":
            return self.play_game(game, doubled=False)
        elif game == "slots":
            return self.play_game("slots", doubled=False)
        return None

    # ---------- Claim Daily ----------
    def claim_daily(self):
        if self.daily_claimed:
            return True
        if not self.cfg.init_data:
            self.log(f"{R}❌ init_data kosong{RESET}")
            return False
        self.log(f"📅 Claim daily {self.name}...")
        resp = self.post("/actions/daily_bonus_ajax.php", data={"action": "claim_daily"})
        if resp and resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('success') or result.get('status') == 'success':
                    self.balance = safe_float(result.get('new_balance', self.balance))
                    self.daily_claimed = True
                    self.log(f"{G}✅ Daily claimed! Bal: {self.balance:.8f} {self.currency}{RESET}")
                    return True
                msg = result.get('message', '')
                if 'already claimed' in msg.lower():
                    self.daily_claimed = True
                    return True
                self.log(f"{R}❌ Daily gagal: {msg}{RESET}")
                return False
            except:
                if 'already' in str(resp.text).lower():
                    self.daily_claimed = True
                    return True
                return False
        return False

    # ---------- Display ----------
    def display_dashboard(self):
        try:
            self.get_games_status()

            elapsed = datetime.now() - self.start_time
            h, r = divmod(int(elapsed.total_seconds()), 3600)
            m, s = divmod(r, 60)
            runtime = f"{h:02d}:{m:02d}:{s:02d}"

            lines = []
            lines.append(f"{GOLD}╔══════════════════════════════════════════════════════════╗")
            lines.append(f"{GOLD}║{RESET}  {C}{self.name.upper()}{RESET}  ({self.currency})")
            lines.append(f"{GOLD}╠══════════════════════════════════════════════════════════╣")
            lines.append(f"{GOLD}║{RESET}  💰 Balance : {G}{self.balance:.8f} {self.currency}{RESET}")
            lines.append(f"{GOLD}║{RESET}  ⏱️  Runtime : {C}{runtime}{RESET}")

            if self.game_list:
                lines.append(f"{GOLD}╠══════════════════════════════════════════════════════════╣")
                for g in self.game_list:
                    icon = self.game_map[g]['icon']; disp = self.game_map[g]['display']
                    if g in self.limited_games:
                        st = "LIMIT 🚫"; sc = R
                    elif g in self.unavailable_games:
                        st = "UNAVAIL ⛔"; sc = R
                    else:
                        st = self.status[g]
                        sc = G if st == "Ready" else Y

                    twox = "2X" if self.doubled_available.get(g, False) and self.retry_doubled.get(g, True) else "-"
                    ply = self.play_counts[g]
                    rwd = self.rewards[g]
                    cd = self.fmt(self.cooldowns[g])

                    if rwd <= 0.00000001:
                        reward_str = f"{G}0.00000000{RESET}"
                    else:
                        reward_str = f"{G}{rwd:.8f}{RESET}" if rwd < 0.001 else f"{G}{rwd:.2f}{RESET}"

                    line = f"{GOLD}║{RESET}  {icon} {disp:<6} {sc}{st:<10}{RESET} {twox:<4} {ply:<4} {reward_str:<16} {cd:<6}{GOLD}║"
                    lines.append(line)

            lines.append(f"{GOLD}╠══════════════════════════════════════════════════════════╣")
            for log in list(self.logs)[-6:]:
                log_clean = log[:48] if len(log) > 48 else log
                lines.append(f"{GOLD}║{RESET}  {log_clean}{' ' * (50 - len(log_clean))} {GOLD}║")
            lines.append(f"{GOLD}╚══════════════════════════════════════════════════════════╝")
            return "\n".join(lines)
        except Exception as e:
            return f"{R}❌ Error display: {e}{RESET}"

    # ---------- Process ----------
    def process_one_game(self):
        if not self.game_list: return False
        try:
            ready = self.get_ready_games()
            if not ready:
                if self.is_all_limited():
                    self.log(f"{R}🛑 {self.name} SEMUA GAME LIMIT/UNAVAILABLE! Stop{RESET}")
                    self.running = False
                return False

            for i in range(len(self.game_list)):
                idx = (self.game_index + i) % len(self.game_list)
                g = self.game_list[idx]
                if g in ready:
                    self.game_index = (idx + 1) % len(self.game_list)
                    break
            else:
                return False

            print(f"{C}🎮 {self.name} {self.game_map[g]['display']}...{RESET}")
            result = self.play_single(g)

            if result and result.get('status') == 'error':
                err_msg = result.get('message', '')
                if 'pending' in err_msg.lower():
                    self.log(f"{Y}⚠️ Pending win detected, claiming...{RESET}")
                    if self.claim_pending():
                        self.log(f"{G}↻ Retrying after claim{RESET}")
                        time.sleep(2)
                        result2 = self.play_single(g)
                        if result2 and result2.get('status') == 'success':
                            rwd = safe_float(result2.get('reward', 0))
                            self.balance = safe_float(result2.get('new_balance', self.balance))
                            self.rewards[g] = rwd
                            self.play_counts[g] += 1
                            self.log(f"{G}✔ +{rwd:.8f} (after claim){RESET}")
                            return True
                    return False
                elif 'unavailable' in err_msg.lower() or 'not available' in err_msg.lower():
                    self.unavailable_games.add(g)
                    self.log(f"{Y}⏭️ UNAVAILABLE, skip{RESET}")
                    return False

            if result and result.get('status') == 'success':
                rwd = safe_float(result.get('reward', 0))
                if rwd == 0:
                    rwd = safe_float(result.get('base_reward', 0))
                self.balance = safe_float(result.get('new_balance', self.balance))
                self.rewards[g] = rwd
                self.play_counts[g] += 1
                if rwd > 0:
                    self.log(f"{G}✔ {self.game_map[g]['display']} +{rwd:.8f} (Bal: {self.balance:.8f}){RESET}")
                else:
                    self.log(f"{G}✔ {self.game_map[g]['display']} +0.00000000{RESET}")

                daily_played = result.get('daily_played')
                daily_limit = result.get('daily_limit')
                if daily_played is not None and daily_limit is not None and daily_limit > 0 and daily_played >= daily_limit:
                    self.limited_games.add(g)
                    self.log(f"{Y}⏭️ daily limit ({daily_played}/{daily_limit}){RESET}")

                global_played = result.get('global_played')
                global_limit = result.get('global_limit')
                if global_played is not None and global_limit is not None and global_limit > 0 and global_played >= global_limit:
                    self.log(f"{Y}🌍 Global limit reached — stop all{RESET}")
                    for game in self.game_list:
                        self.limited_games.add(game)

            elif result and result.get('status') == 'error':
                err = result.get('message', '')
                if 'not logged in' in err.lower():
                    self.log(f"{Y}⚠️ Not logged in, reauth...{RESET}")
                    if self.reauth():
                        time.sleep(2)
                        result2 = self.play_single(g)
                        if result2 and result2.get('status') == 'success':
                            rwd = safe_float(result2.get('reward', 0))
                            self.balance = safe_float(result2.get('new_balance', self.balance))
                            self.rewards[g] = rwd
                            self.play_counts[g] += 1
                            self.log(f"{G}✔ +{rwd:.8f} [retry OK]{RESET}")
                elif 'daily_limit' in err.lower() or 'limit reached' in err.lower():
                    self.limited_games.add(g)
                    self.log(f"{Y}⏭️ LIMIT, skip{RESET}")
                elif 'unavailable' in err.lower() or 'not available' in err.lower():
                    self.unavailable_games.add(g)
                    self.log(f"{Y}⏭️ UNAVAILABLE, skip{RESET}")
                else:
                    self.log(f"{R}✖ FAIL: {err}{RESET}")
            else:
                err = result.get('message', 'No resp') if result else 'No resp'
                self.log(f"{R}✖ FAIL: {err}{RESET}")

            time.sleep(random.uniform(1, 3))
            self.get_dashboard()
            return True
        except Exception as e:
            self.log(f"{R}✖ Process error: {e}{RESET}")
            return False

# ========== BOT SUBCLASSES ==========
class PepeBot(BaseBot):
    def __init__(self, cfg):
        super().__init__(PEPE_URL, cfg, PEPE_GAMES, PEPE_GAME_MAP, "PepeFlow", "PEPE")

class ClockBot(BaseBot):
    def __init__(self, cfg):
        super().__init__(CLOCK_URL, cfg, CLOCK_GAMES, CLOCK_GAME_MAP, "ClockAds", "TRX")


# ============================================================
# 🎡 COINSZON — SPINS EDITION
# Endpoint: /actions/tg_auth.php, /actions/get_balance.php,
#           /actions/mini_games.php, /pages/load_wheel.php
# ============================================================
class CoinBot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.name = "Coinszon"
        self.currency = "LTC"
        self.url = COIN_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": COIN_UA,
            "Accept": "*/*",
            "Origin": COIN_URL,
            "Referer": f"{COIN_URL}/miniapp.php",
            "X-Requested-With": "org.telegram.messenger.web",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Android WebView";v="152"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        })

        # State
        self.running = True
        self.balance = 0.0          # coin_balance (LTC)
        self.usd_balance = 0.0      # USD equivalent
        self.display_balance = "0"
        self.wheel_spins = 0
        self.last_wheel_spins = 0
        self.play_counts = 0
        self.rewards = 0.0
        self.last_reward = 0.0
        self.logs = deque(maxlen=8)
        self.start_time = datetime.now()
        self.daily_claimed = False
        self.boost_until = 0
        self.boost_remaining = 0
        self.jackpot_hits = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 8
        self.cooldown_until = 0     # local cooldown if server says so
        self.game_index = 0         # not used but keep interface
        self.doubled_available = {"lucky_wheel": False}
        self.retry_doubled = {"lucky_wheel": True}
        self.cooldowns = {"lucky_wheel": 0}
        self.status = {"lucky_wheel": "Ready"}
        self.limited_games = set()
        self.unavailable_games = set()

        self._initial_auth()

    # ---------- HELPERS ----------
    def log(self, msg):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _request(self, method, endpoint, **kwargs):
        if not self.running:
            return None
        url = f"{self.url}{endpoint}"
        try:
            kwargs.setdefault('timeout', 30)
            resp = self.session.request(method, url, **kwargs)

            if resp.status_code == 429:
                self.consecutive_errors += 1
                self.log(f"{R}🚫 429 ({self.consecutive_errors}/{self.max_consecutive_errors}){RESET}")
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.log(f"{R}🛑 {self.name} terlalu banyak 429! Stop{RESET}")
                    self.running = False
                return None
            else:
                self.consecutive_errors = 0

            if resp.status_code in [401, 403]:
                self.log(f"{Y}⚠️ Session expired, reauth...{RESET}")
                if self.reauth():
                    resp = self.session.request(method, url, **kwargs)
                    if resp.status_code in [401, 403]:
                        self.log(f"{R}❌ Session masih invalid{RESET}")
                        return None
                else:
                    return None

            return resp
        except Exception as e:
            self.log(f"{R}❌ Request error: {e}{RESET}")
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.max_consecutive_errors:
                self.log(f"{R}🛑 {self.name} terlalu banyak error! Stop{RESET}")
                self.running = False
            return None

    def get(self, endpoint):
        return self._request('GET', endpoint)

    def post(self, endpoint, files=None, data=None):
        return self._request('POST', endpoint, files=files, data=data)

    # ---------- AUTH ----------
    def _initial_auth(self):
        if not self.cfg.init_data:
            self.log(f"{R}❌ init_data kosong! Bot tidak bisa jalan{RESET}")
            self.running = False
            return False
        return self.reauth()

    def reauth(self):
        if not self.cfg.init_data:
            self.log(f"{R}❌ init_data tidak ada{RESET}")
            return False

        parsed = urllib.parse.parse_qs(self.cfg.init_data)
        user_str = parsed.get('user', [None])[0]
        tid, tuname = "0", ""
        if user_str:
            try:
                u = json.loads(urllib.parse.unquote(user_str))
                tid = str(u.get('id', '0'))
                tuname = u.get('username', '')
            except: pass

        self.cfg.telegram_id = tid
        self.cfg.telegram_username = tuname
        self.cfg.save()

        fingerprint = os.urandom(16).hex()

        files = {
            "init_data": (None, self.cfg.init_data),
            "telegram_id": (None, tid),
            "telegram_username": (None, tuname),
            "auto_login": (None, "1"),
            "fingerprint": (None, fingerprint),
        }
        try:
            resp = self.session.post(f"{self.url}/actions/tg_auth.php", files=files, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    self.log(f"{G}✅ {self.name} auth OK (fp: {fingerprint[:8]}...){RESET}")
                    return True
                elif data.get('status') == 'banned':
                    self.log(f"{R}❌ {self.name} BANNED: {data.get('message','')}{RESET}")
                    self.running = False
                    return False
                else:
                    self.log(f"{R}❌ Auth gagal: {data.get('message', 'unknown')}{RESET}")
                    return False
            else:
                self.log(f"{R}❌ Auth gagal, status {resp.status_code}{RESET}")
                return False
        except Exception as e:
            self.log(f"{R}❌ Auth error: {e}{RESET}")
            return False

    # ---------- BALANCE / DASHBOARD ----------
    def get_dashboard(self):
        resp = self.get("/actions/get_balance.php")
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
            except:
                return None
            if data.get('status') == 'success' or data.get('success') is True:
                self.usd_balance = safe_float(data.get('balance', 0))
                self.balance = safe_float(data.get('coin_balance', 0))
                self.display_balance = str(data.get('display_balance', self.balance))
                if data.get('currency_label'):
                    self.currency = str(data.get('currency_label')).upper()
                return data
        return None

    # ---------- WHEEL STATUS ----------
    def get_wheel_status(self):
        """Parse /pages/load_wheel.php buat ambil wheel_spins."""
        resp = self.get("/pages/load_wheel.php")
        if not (resp and resp.status_code == 200):
            return None
        html = resp.text

        # Spin count — id="hdr-wheel-spins" atau var wheelSpins
        m = re.search(r'id=["\']hdr-wheel-spins["\'][^>]*>\s*(\d+)\s*<', html)
        if m:
            self.wheel_spins = safe_int(m.group(1))
        else:
            m = re.search(r'var\s+wheelSpins\s*=\s*(\d+)\s*;', html)
            if m:
                self.wheel_spins = safe_int(m.group(1))

        # Daily Free Spins badge number
        m2 = re.search(r'Daily Free Spins.*?<span[^>]*>\s*(\d+)\s*<', html, re.DOTALL)
        if m2 and self.wheel_spins == 0:
            self.wheel_spins = safe_int(m2.group(1))

        if self.wheel_spins > 0:
            self.status["lucky_wheel"] = "Ready"
            self.limited_games.discard("lucky_wheel")
        else:
            self.status["lucky_wheel"] = "No Spins"
            self.limited_games.add("lucky_wheel")

        return {"wheel_spins": self.wheel_spins}

    def has_ready_games(self):
        # Kalau baru play dan masih ada spin tersisa, cepet
        if self.wheel_spins > 0 and "lucky_wheel" not in self.unavailable_games:
            return True
        self.get_wheel_status()
        return self.wheel_spins > 0 and "lucky_wheel" not in self.unavailable_games

    def get_ready_games(self):
        if self.has_ready_games():
            return ["lucky_wheel"]
        return []

    def is_all_limited(self):
        return self.wheel_spins <= 0 or "lucky_wheel" in self.unavailable_games

    # ---------- CLAIM DAILY ----------
    def claim_daily(self):
        if self.daily_claimed:
            return True

        self.log(f"📅 Claim daily {self.name}...")

        # Cek status dulu via dashboard — kalau daily bonus gate ada = available
        dash = self.get("/pages/load_dashboard.php")
        daily_available = False
        if dash and dash.status_code == 200:
            daily_available = ('id="daily-bonus-gate"' in dash.text) or ('Daily Bonus' in dash.text and 'Claim' in dash.text)

        if not daily_available:
            self.daily_claimed = True
            self.log(f"{Y}⏭️ Daily bonus tidak tersedia{RESET}")
            return True

        # Flow: ad_start → ad_complete → check_ad_status → claim_daily (server-side)
        # Kita coba tanpa ad proof langsung (server bakal reject kalau butuh)
        try:
            # 1. ad_start
            s = self.post("/actions/daily_bonus_ajax.php", data={"action": "ad_start"})
            token = ""
            if s and s.status_code == 200:
                try:
                    sd = s.json()
                    if sd.get('success'):
                        token = str(sd.get('token', ''))
                except: pass

            if token:
                # 2. Play ad simulation (server butuh waktu)
                ad_progress(10, "📺 Watch daily bonus ad")
                # 3. ad_complete (client report)
                self.post("/actions/daily_bonus_ajax.php", data={"action": "ad_complete", "token": token})
                # 4. Poll verify — tunggu S2S postback
                verified = False
                for attempt in range(10):
                    time.sleep(3)
                    c = self.post("/actions/daily_bonus_ajax.php", data={"action": "check_ad_status", "token": token})
                    if c and c.status_code == 200:
                        try:
                            cd = c.json()
                            if cd.get('verified'):
                                verified = True
                                break
                        except: pass
                if not verified:
                    self.log(f"{Y}⚠️ Daily ad belum ter-verify, skip{RESET}")
                    self.daily_claimed = True
                    return False

            # 5. claim
            r = self.post("/actions/daily_bonus_ajax.php", data={"action": "claim_daily", "db_ad_token": token})
            if r and r.status_code == 200:
                try:
                    rd = r.json()
                    if rd.get('status') == 'success' or rd.get('success') is True:
                        if rd.get('display_balance') or rd.get('new_balance'):
                            self.display_balance = str(rd.get('display_balance', rd.get('new_balance')))
                            self.balance = safe_float(rd.get('new_balance', self.balance))
                        self.daily_claimed = True
                        self.log(f"{G}✅ Daily bonus OK: {rd.get('message', '')}{RESET}")
                        return True
                    msg = rd.get('message', '')
                    if 'already' in msg.lower():
                        self.daily_claimed = True
                        return True
                    self.log(f"{R}❌ Daily gagal: {msg}{RESET}")
                except: pass
        except Exception as e:
            self.log(f"{R}❌ Daily exception: {e}{RESET}")

        self.daily_claimed = True
        return False

    # ---------- PLAY WHEEL ----------
    def play_game(self, game="lucky_wheel", doubled=False):
        files = {
            "action": (None, "play"),
            "game": (None, game),
            "doubled": (None, "1" if doubled else "0"),
        }
        resp = self.post("/actions/mini_games.php", files=files)
        if resp and resp.status_code == 200:
            try: return resp.json()
            except: pass
        return None

    def play_single(self, game="lucky_wheel"):
        if game in self.limited_games:
            return None
        # Ad required before spin? — detect via wheel page var
        if self.wheel_spins <= 0:
            self.get_wheel_status()
            if self.wheel_spins <= 0:
                return None
        # Simulate watch ad (server butuh waktu, biasanya ~5-10s)
        ad_progress(6, "📺 Watch spin ad")
        return self.play_game(game, doubled=False)

    # ---------- PROCESS ONE GAME ----------
    def process_one_game(self):
        try:
            if not self.has_ready_games():
                if self.is_all_limited():
                    # Kalau gak ada spin, coba cek lagi nanti
                    self.log(f"{Y}⏳ {self.name} tidak ada spin, tunggu...{RESET}")
                return False

            self.get_dashboard()

            print(f"{C}🎡 {self.name} SPIN...{RESET}")
            result = self.play_single("lucky_wheel")

            if not result:
                self.consecutive_errors += 1
                self.log(f"{R}✖ No response{RESET}")
                time.sleep(3)
                return False

            status = result.get('status', '')
            if status != 'success':
                # Error handling
                msg = result.get('message', 'unknown')
                low = msg.lower()

                if 'banned' in low or 'game banned' in low or 'suspend' in low:
                    self.log(f"{R}❌ {self.name} GAME BANNED: {msg}{RESET}")
                    self.running = False
                    return False
                if 'no spin' in low or 'not enough spin' in low or 'spin habis' in low:
                    self.wheel_spins = 0
                    self.limited_games.add("lucky_wheel")
                    self.log(f"{Y}⏭️ No spins left{RESET}")
                    return False
                if 'limit' in low or 'exhaust' in low:
                    self.limited_games.add("lucky_wheel")
                    self.log(f"{Y}⏭️ Limit reached{RESET}")
                    return False
                if 'unavailable' in low:
                    self.unavailable_games.add("lucky_wheel")
                    self.log(f"{Y}⏭️ Unavailable{RESET}")
                    return False

                self.log(f"{R}✖ SPIN fail: {msg}{RESET}")
                time.sleep(5)
                return False

            # Parse success
            won        = bool(result.get('won', False))
            reward     = safe_float(result.get('reward', 0))
            base_rwd   = safe_float(result.get('base_reward', reward))
            new_bal    = result.get('new_balance')
            rd         = result.get('result_data', {}) or {}
            prize_t    = result.get('prize_type', rd.get('prize_type', 'coin'))
            bonus_sp   = safe_int(result.get('bonus_spins', rd.get('bonus_spins', 0)))
            wheel_sp   = result.get('wheel_spins', rd.get('wheel_spins', None))
            is_jack    = bool(result.get('is_jackpot', rd.get('is_jackpot', False)))
            boost_rem  = safe_int(result.get('boost_remaining', rd.get('boost_remaining', 0)))

            self.play_counts += 1

            if new_bal is not None:
                self.balance = safe_float(new_bal)
            self.rewards = reward

            if wheel_sp is not None:
                self.wheel_spins = safe_int(wheel_sp)
                if self.wheel_spins > 0:
                    self.limited_games.discard("lucky_wheel")
                else:
                    self.limited_games.add("lucky_wheel")

            if boost_rem > 0:
                self.boost_remaining = boost_rem

            # Log per prize type
            if is_jack:
                self.jackpot_hits += 1
                self.log(f"{G}🎉 JACKPOT! +{reward:.8f} {self.currency} (spin left: {self.wheel_spins}){RESET}")
            elif prize_t == 'spins' and bonus_sp > 0:
                self.log(f"{G}✔ +{bonus_sp} BONUS SPINS (total: {self.wheel_spins}){RESET}")
            elif prize_t == 'boost':
                self.log(f"{G}✔ 1.5x BOOST +{boost_rem}s{RESET}")
            elif won and reward > 0:
                self.log(f"{G}✔ +{reward:.8f} {self.currency} (Bal: {self.balance:.8f}, spin left: {self.wheel_spins}){RESET}")
            else:
                self.log(f"{Y}✖ No prize (spin left: {self.wheel_spins}){RESET}")

            # Delay antar spin (spins-based, no strict cooldown but server may rate-limit)
            time.sleep(random.uniform(2, 4))
            return True

        except Exception as e:
            self.log(f"{R}✖ Process error: {e}{RESET}")
            return False

    # ---------- DISPLAY ----------
    def display_dashboard(self):
        try:
            elapsed = datetime.now() - self.start_time
            h, r = divmod(int(elapsed.total_seconds()), 3600)
            m, s = divmod(r, 60)
            runtime = f"{h:02d}:{m:02d}:{s:02d}"

            boost_str = f"{self.boost_remaining}s" if self.boost_remaining > 0 else "OFF"
            boost_c = G if self.boost_remaining > 0 else R

            lines = []
            lines.append(f"{GOLD}╔══════════════════════════════════════════════════════════╗")
            lines.append(f"{GOLD}║{RESET}  {C}{self.name.upper()}{RESET}  ({self.currency})")
            lines.append(f"{GOLD}╠══════════════════════════════════════════════════════════╣")
            lines.append(f"{GOLD}║{RESET}  💰 Balance : {G}{self.balance:.8f} {self.currency}{RESET}")
            lines.append(f"{GOLD}║{RESET}  💵 USD     : {B}${self.usd_balance:.8f}{RESET}")
            lines.append(f"{GOLD}║{RESET}  🎡 Spins   : {G}{self.wheel_spins}{RESET}")
            lines.append(f"{GOLD}║{RESET}  🚀 Boost   : {boost_c}{boost_str}{RESET}")
            lines.append(f"{GOLD}║{RESET}  🎉 Jackpot : {G}{self.jackpot_hits}{RESET}")
            lines.append(f"{GOLD}║{RESET}  ⏱️  Runtime : {C}{runtime}{RESET}")
            lines.append(f"{GOLD}║{RESET}  🔄 Plays   : {W}{self.play_counts}{RESET}  |  💎 Reward: {G}{self.rewards:.8f}{RESET}")
            lines.append(f"{GOLD}╠══════════════════════════════════════════════════════════╣")
            for log in list(self.logs)[-6:]:
                log_clean = log[:48] if len(log) > 48 else log
                lines.append(f"{GOLD}║{RESET}  {log_clean}{' ' * (50 - len(log_clean))} {GOLD}║")
            lines.append(f"{GOLD}╚══════════════════════════════════════════════════════════╝")
            return "\n".join(lines)
        except Exception as e:
            return f"{R}❌ Error display: {e}{RESET}"

# ========== PARALLEL RUNNER ==========
def parallel_run(bots):
    for bot in bots:
        try:
            bot.claim_daily()
        except:
            pass

    while any(b.running for b in bots):
        any_played = False
        for bot in bots:
            if not bot.running: continue
            try:
                if bot.has_ready_games():
                    clear()
                    for b in bots:
                        if b.running:
                            print(b.display_dashboard())
                            print()
                    print(f"{C}▶️ {bot.name} game ready, playing...{RESET}")
                    bot.process_one_game()
                    any_played = True
                    time.sleep(0.3)
            except Exception as e:
                try: bot.log(f"{R}✖ {e}{RESET}")
                except: pass

        if not any_played:
            # Kumpulkan cooldown dari semua bot
            all_cds = []
            for bot in bots:
                if not bot.running: continue
                # CoinBot tidak pakai self.cooldowns biasanya; fallback 5s
                if hasattr(bot, 'cooldowns'):
                    all_cds.extend([cd for cd in bot.cooldowns.values() if cd > 0])
            if all_cds:
                min_cd = min(all_cds)
                clear()
                for b in bots:
                    if b.running:
                        print(b.display_dashboard())
                        print()
                print(f"{Y}⏳ Semua bot cooldown. Menunggu {min_cd} detik...{RESET}")
                live_timer(min_cd, f"⏳ Cooldown {min_cd}s")
            else:
                # Tidak ada cooldown → tunggu sebentar aja (kasus spin habis)
                time.sleep(3)

# ========== BOT FACTORY ==========
BOT_MAP = {
    'pepe':  ('PepeFlow',  PEPE_CONFIG,  PepeBot),
    'clock': ('ClockAds',  CLOCK_CONFIG, ClockBot),
    'coin':  ('Coinszon',  COIN_CONFIG,  CoinBot),
}

def build_bots(keys):
    bots = []
    missing = []
    for k in keys:
        if k not in BOT_MAP: continue
        name, cfgfile, cls = BOT_MAP[k]
        cfg = BaseConfig(cfgfile)
        if not cfg.load() or not cfg.init_data:
            missing.append(name)
            continue
        bots.append(cls(cfg))
    return bots, missing

# ========== SETUP ==========
def setup_bot(name, config_file, prompt):
    clear()
    print(f"\n{PURPLE}╔══════════════════════════════════════════════════════════╗")
    print(f"║   {GOLD}⚙️  SETUP {name:<40} {PURPLE}║")
    print(f"╚══════════════════════════════════════════════════════════╝{RESET}\n")
    print(f"{Y}Cara ambil init_data:{RESET}")
    print(f"{W}1. Buka Mini App di Telegram")
    print(f"2. Klik titik 3 → Open in Browser")
    print(f"3. DevTools (F12) → Console")
    print(f"4. Ketik: window.Telegram.WebApp.initData")
    print(f"5. Copy hasilnya{RESET}\n")

    init = input(f"{C}{prompt}: {W}").strip()
    if not init:
        print(f"{R}❌ Kosong, tidak disimpan{RESET}")
        return
    cfg = BaseConfig(config_file)
    cfg.init_data = init
    try:
        parsed = urllib.parse.parse_qs(init)
        user_str = parsed.get('user', [None])[0]
        if user_str:
            u = json.loads(urllib.parse.unquote(user_str))
            cfg.telegram_id = str(u.get('id', ''))
            cfg.telegram_username = u.get('username', '')
    except: pass
    cfg.save()
    print(f"\n{G}✅ {name} tersimpan di {config_file}{RESET}")
    if cfg.telegram_id:
        print(f"{G}✅ User ID: {cfg.telegram_id}{RESET}")
    if cfg.telegram_username:
        print(f"{G}✅ Username: @{cfg.telegram_username}{RESET}")

def check_config(name, config_file):
    cfg = BaseConfig(config_file)
    if cfg.load() and cfg.init_data:
        return f"{G}✓{RESET} {name:<12} {M}ID:{RESET} {cfg.telegram_id or '?':<15} {M}@{cfg.telegram_username or '?':<15} {M}init:{RESET} {len(cfg.init_data)} chars"
    return f"{R}✗{RESET} {name:<12} {R}belum disetup{RESET}"

# ========== RUNNER WRAPPER ==========
def run_selection(keys, label):
    bots, missing = build_bots(keys)
    if missing:
        print(f"\n{R}❌ Setup dulu:{RESET}")
        for m in missing:
            print(f"   {R}✗{RESET} {m}")
        input("\nEnter...")
        return
    if not bots:
        print(f"\n{R}❌ Gak ada bot yang bisa dijalanin{RESET}")
        input("\nEnter...")
        return

    print(f"\n{G}🚀 {label}{RESET}")
    print(f"{C}   Bots: {', '.join(b.name for b in bots)}{RESET}")
    time.sleep(1)
    try:
        parallel_run(bots)
    except KeyboardInterrupt:
        print(f"\n{Y}👋 Dihentikan.{RESET}")
    input("\nEnter...")

# ========== MAIN ==========
def main():
    while True:
        clear()
        print(f"""
{PURPLE}╔══════════════════════════════════════════════════════════╗
║   {GOLD}🚀 PEPEFLOW X CLOCKADS X COINSZON                {PURPLE}║
╠══════════════════════════════════════════════════════════╣
║   {PINK}🔐 AUTH via init_data (NO PHPSESSID manual)      {PURPLE}║
║   {PINK}🎲 FINGERPRINT RANDOM setiap reauth               {PURPLE}║
║   {PINK}🚫 AUTO SKIP LIMIT (daily + global)               {PURPLE}║
║   {PINK}🎁 AUTO CLAIM PENDING WIN (WITH AD PROOF)         {PURPLE}║
║   {PINK}📅 AUTO CLAIM DAILY BONUS                         {PURPLE}║
║   {PINK}🎡 CoinBot: SPINS EDITION                          {PURPLE}║
╠══════════════════════════════════════════════════════════╣
║   {G}▶️  RUN MODE{RESET}
║   {G}[1]{RESET}  🚀 Start ALL (PepeFlow + ClockAds + Coinszon)  ║
║   {C}[2]{RESET}  🎯 PepeFlow X Coinszon                          ║
║   {C}[3]{RESET}  🎯 Coinszon X ClockAds                          ║
║   {C}[4]{RESET}  🎯 ClockAds X PepeFlow                          ║
╠══════════════════════════════════════════════════════════╣
║   {Y}⚙️  SETUP{RESET}
║   {Y}[5]{RESET}  ⚙️  Setup PepeFlow                             ║
║   {Y}[6]{RESET}  ⚙️  Setup ClockAds                             ║
║   {Y}[7]{RESET}  ⚙️  Setup Coinszon                             ║
║   {B}[8]{RESET}  📊 Check semua config                          ║
║   {R}[0]{RESET}  ❌ Exit                                         ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")
        choice = input(f"{PURPLE}❯ Pilih: {RESET}").strip()

        if choice == '0':
            print(f"\n{G}👋 Bye bos!{RESET}")
            sys.exit(0)

        elif choice == '1':
            run_selection(['pepe', 'clock', 'coin'], "Start ALL bots parallel")

        elif choice == '2':
            run_selection(['pepe', 'coin'], "PepeFlow X Coinszon")

        elif choice == '3':
            run_selection(['coin', 'clock'], "Coinszon X ClockAds")

        elif choice == '4':
            run_selection(['clock', 'pepe'], "ClockAds X PepeFlow")

        elif choice == '5':
            setup_bot("PepeFlow", PEPE_CONFIG, "Masukkan init_data PepeFlow")
            input("Enter...")
        elif choice == '6':
            setup_bot("ClockAds", CLOCK_CONFIG, "Masukkan init_data ClockAds")
            input("Enter...")
        elif choice == '7':
            setup_bot("Coinszon", COIN_CONFIG, "Masukkan init_data Coinszon")
            input("Enter...")

        elif choice == '8':
            clear()
            print(f"\n{PURPLE}╔══════════════════════════════════════════════════════════╗")
            print(f"║   {GOLD}📊 CONFIG INFO                                     {PURPLE}║")
            print(f"╚══════════════════════════════════════════════════════════╝{RESET}\n")
            print(check_config("PepeFlow", PEPE_CONFIG))
            print(check_config("ClockAds", CLOCK_CONFIG))
            print(check_config("Coinszon", COIN_CONFIG))
            input("\nEnter...")

        else:
            print(f"{R}❌ Pilihan invalid{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}👋 Keluar.{RESET}")
        sys.exit(0)
