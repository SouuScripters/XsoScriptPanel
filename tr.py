#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 TREWARDS AUTO WATCH BOT v1.2
- Human-like delay & jitter (gak robotik)
- Limit detection → skip block, jangan spam
- Backoff per-block, session break random
- ScriptMaker: MoneyMaker_w
"""

import os, sys, time, json, random, re
import requests
from datetime import datetime

CLEAR = '\033[K'
R = '\033[0m'
B = '\033[1m'
D = '\033[2m'
NG = '\033[38;5;46m'
NC = '\033[38;5;51m'
NP = '\033[38;5;201m'
NY = '\033[38;5;226m'
NO = '\033[38;5;208m'
NR = '\033[38;5;196m'
NM = '\033[38;5;135m'
DW = '\033[38;5;15m'
DG = '\033[38;5;240m'

BASE = "https://trewards-backend.ankisaw1010.workers.dev"
ORIGIN = "https://trewards-frontend.onrender.com"
CONFIG_FILE = "trewards_config.json"

UA = "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.7977.87 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"

AD_BLOCKS = [
    {"id": "adCounter1", "reward": "5000 TR"},
    {"id": "adCounter2", "reward": "5000 TR"},
    {"id": "adCounter3", "reward": "0.0005 TON"},
    {"id": "adCounter4", "reward": "0.0005 TON"},
]

# ==================== HUMAN-LIKE TIMING ====================
AD_DURATION_RANGE      = (18, 28)      # detik nonton ad (random)
DELAY_BETWEEN_RANGE    = (20, 45)      # jeda antar block
CYCLE_DELAY_RANGE      = (60, 180)     # jeda antar cycle kalau masih ada ready
ALL_LIMITED_SLEEP      = (300, 900)    # 5-15 menit kalau semua block limited
SESSION_BREAK_EVERY    = (4, 6)        # tiap 4-6 cycle istirahat
SESSION_BREAK_LEN      = (180, 600)    # 3-10 menit

MAX_CYCLES = 999

# limit detection keywords (lowercase)
LIMIT_KEYWORDS = (
    'limit', 'max', 'cooldown', 'wait', 'too many', 'rate',
    'exceeded', 'try again', 'habis', 'sudah', 'batas', 'nanti',
    'slow down', 'please wait', 'not ready',
)
# backoff stages (detik)
LIMIT_BACKOFF = [300, 900, 1800, 3600, 7200]  # 5m, 15m, 30m, 60m, 120m


def human_pause(min_s, max_s, label=None, color=NY):
    """Jeda random yang keliatan manusia — gak flat."""
    total = random.uniform(min_s, max_s)
    # pecah jadi 3-6 segmen biar ritmenya gak konstan
    segments = random.randint(3, 6)
    seg_time = total / segments
    for i in range(segments):
        jitter = random.uniform(0.7, 1.3)
        t = seg_time * jitter
        if label:
            remain = total - sum([seg_time] * i)
            row = f"  {color}⏳ {label} {remain:5.1f}s{R}"
            sys.stdout.write('\r' + CLEAR + row)
            sys.stdout.flush()
        time.sleep(t)
    if label:
        sys.stdout.write('\r' + CLEAR)
        sys.stdout.flush()


def micro_pause():
    """Pause super pendek — biar keliatan mikir."""
    time.sleep(random.uniform(0.4, 2.2))


def is_limit_error(msg):
    if not msg:
        return False
    m = str(msg).lower()
    return any(k in m for k in LIMIT_KEYWORDS)


# ==================== BANNER ====================
BANNER = f"""{NC}{B}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  ████████╗██████╗ ███████╗██╗    ██╗ █████╗ ██████╗ ██████╗ ███████╗
║  ╚══██╔══╝██╔══██╗██╔════╝██║    ██║██╔══██╗██╔══██╗██╔══██╗██╔════╝
║     ██║   ██████╔╝█████╗  ██║ █╗ ██║███████║██████╔╝██║  ██║███████╗
║     ██║   ██╔══██╗██╔══╝  ██║███╗██║██╔══██║██╔══██╗██║  ██║╚════██║
║     ██║   ██║  ██║███████╗╚███╔███╔╝██║  ██║██║  ██║██████╔╝███████║
║     ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
║                                                                  ║
║  {NY}🎁 TREWARDS AUTO WATCH  {NC}│ {NG}v1.2 {NC}│ {NP}Human Mode{R}
║                                                                  ║
║  {NG}▸ ScriptMaker : {NC}MoneyMaker_w
║  {NG}▸ Channel     : {NC}https://t.me/ScriptyXSouu
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{R}
"""


class Anim:
    @staticmethod
    def matrix_rain(lines=5, width=60, duration=1.5):
        chars = list("01ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉTREWARDS")
        start = time.time()
        canvas = [[' '] * width for _ in range(lines)]
        for _ in range(lines): print()
        while time.time() - start < duration:
            for _ in range(3):
                col = random.randint(0, width - 1)
                canvas[0][col] = random.choice(chars)
            for i in range(lines - 1, 0, -1):
                canvas[i] = canvas[i - 1][:]
            canvas[0] = [' '] * width
            sys.stdout.write(f"\033[{lines}A")
            for i, row in enumerate(canvas):
                color = NG if i < 1 else (NG if i < 2 else D + NG)
                sys.stdout.write(color + ''.join(row) + R + "\n")
            sys.stdout.flush()
            time.sleep(0.08)

    @staticmethod
    def boot(duration=2.0):
        steps = [
            "Initializing kernel module...",
            "Loading stealth headers...",
            "Rotating device fingerprint...",
            "Connecting to trewards-backend...",
            "Session ready.",
        ]
        per = duration / len(steps)
        print()
        for s in steps:
            sys.stdout.write(f"  {NG}[✓]{R} {DW}{s}{R}\n")
            sys.stdout.flush()
            time.sleep(per)
        print(f"  {NY}[⚡]{R} {DW}Status: {NG}SECURE{R}")
        print(f"  {NP}[★]{R} {DW}Welcome, {NC}Operative{R}\n")
        time.sleep(0.3)

    @staticmethod
    def watch_bar(label, duration):
        spinner = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
        bar_len = 22
        start = time.time(); i = 0
        while True:
            elapsed = time.time() - start
            if elapsed >= duration: break
            pct = elapsed / duration
            filled = int(bar_len * pct)
            bar = '█' * filled + '░' * (bar_len - filled)
            rem = duration - elapsed
            row = (f"  {NP}{spinner[i%10]}{R} {NC}{label:<12}{R} "
                   f"{NG}[{bar}]{R} {NY}{int(pct*100):3d}%{R} {NY}{rem:4.1f}s{R}")
            sys.stdout.write('\r' + CLEAR + row)
            sys.stdout.flush()
            time.sleep(0.1); i += 1
        sys.stdout.write('\r' + CLEAR); sys.stdout.flush()

    @staticmethod
    def dots(text, duration=1.5):
        end = time.time() + duration
        n = 0
        while time.time() < end:
            d = "." * ((n % 3) + 1)
            sys.stdout.write('\r' + CLEAR + f" {NC}•{R} {DW}{text}{NC}{d:<4}{R}")
            sys.stdout.flush()
            time.sleep(0.3); n += 1
        sys.stdout.write('\r' + CLEAR + f" {NG}✓{R} {DW}{text}{R}\n")
        sys.stdout.flush()

    @staticmethod
    def glitch(text, duration=0.5):
        gc = "░▒▓█▄▀■□▪▫@#$%&*"
        start = time.time()
        while time.time() - start < duration:
            out = ''.join(random.choice(gc) if (random.randint(0,10)<2 and ch!=' ') else ch for ch in text)
            sys.stdout.write('\r' + CLEAR + f"  {NP}{out}{R}")
            sys.stdout.flush()
            time.sleep(0.06)
        sys.stdout.write('\r' + CLEAR + f"  {NC}{text}{R}\n")
        sys.stdout.flush()


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def strip_ansi(s):
    return re.sub(r'\033\[[0-9;]*m', '', s)

def print_box(title, lines, color=NC, w=62):
    print(f"{color}╭{'─' * w}╮{R}")
    print(f"{color}│{R} {B}{color}{title:^{w}}{R} {color}│{R}")
    print(f"{color}├{'─' * w}┤{R}")
    for line in lines:
        clean = strip_ansi(line)
        pad = w - len(clean)
        if pad < 0: pad = 0
        print(f"{color}│{R} {line}{' ' * pad} {color}│{R}")
    print(f"{color}╰{'─' * w}╯{R}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

def get_user_id():
    cfg = load_config()
    if cfg.get('user_id'):
        print(f"{NG}✓ {DW}User ID tersimpan: {NC}{cfg['user_id']}{R}")
        use = input(f"{NY}? Pakai user_id ini? [Y/n]: {R}").strip().lower()
        if not use or use in ('y', 'yes', 'ya'):
            return str(cfg['user_id'])
    print(f"\n{NY}CARA DAPAT USER ID:{R}")
    print(f"{DG}  Buka Trewards di Telegram → DevTools → Network → /api/user/sync")
    print(f"  Cari field 'telegram_id' di body atau URL.{R}\n")
    uid = input(f"{NC}📧 User ID: {R}").strip()
    if uid:
        cfg['user_id'] = uid
        save_config(cfg)
    return uid


class TRewardsBot:
    def __init__(self):
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "user-agent": UA,
            "origin": ORIGIN,
            "referer": ORIGIN + "/",
            "x-requested-with": "org.telegram.messenger.web",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        self.stats = {
            "ads_watched": 0,
            "tr_earned": 0,
            "ton_earned": 0.0,
            "failed": 0,
            "skipped": 0,
            "cycles": 0,
            "start_time": datetime.now(),
        }
        self.user_data = None
        # block_id -> { "until": ts, "stage": int, "reason": str }
        self.block_cooldown = {}

    def _req(self, method, path, json_data=None, timeout=30):
        url = f"{BASE}{path}"
        for attempt in range(3):
            try:
                if method.upper() == 'GET':
                    r = self.session.get(url, timeout=timeout)
                else:
                    r = self.session.post(url, json=json_data, timeout=timeout)
                if r.status_code == 429:
                    wait = int(r.headers.get('Retry-After', random.randint(10, 30)))
                    print(f"\n{NY}  ⚠ 429 rate limit — tunggu {wait}s{R}")
                    time.sleep(wait)
                    continue
                try:
                    return r.json()
                except:
                    return {"_raw": r.text[:200], "_code": r.status_code}
            except Exception as e:
                if attempt == 2:
                    return {"_error": str(e)}
                # backoff acak biar gak pattern
                time.sleep(random.uniform(2, 6))
        return None

    def sync_user(self):
        data = self._req('POST', f"/api/user/sync?_t={int(time.time()*1000)}", {
            "telegram_id": int(self.user_id),
            "username": "",
            "first_name": "",
            "last_name": "",
            "referrer_id": None
        })
        if data and data.get('success'):
            self.user_data = data.get('user', {})
            return True
        return False

    def get_user(self):
        return self.user_data or {}

    def verify_channels(self):
        return self._req('POST', f"/api/channels/verify?_t={int(time.time()*1000)}", {
            "user_id": int(self.user_id)
        })

    def watch_ad(self, block_id):
        # durasi & timestamp random biar gak keliatan robot
        duration = random.randint(*AD_DURATION_RANGE)
        # jitter timestamp ±3s
        ts_jitter = random.randint(-3000, 3000)
        payload = {
            "user_id": int(self.user_id),
            "ad_block_id": block_id,
            "duration_sec": duration,
            "client_timestamp": int(time.time() * 1000) + ts_jitter
        }
        return self._req('POST', f"/api/ad/watch?_t={int(time.time()*1000)}", payload)

    # ---------- limit tracking ----------
    def is_block_limited(self, block_id):
        cd = self.block_cooldown.get(block_id)
        if not cd:
            return False
        return time.time() < cd['until']

    def block_limited_left(self, block_id):
        cd = self.block_cooldown.get(block_id)
        if not cd:
            return 0
        return max(0, int(cd['until'] - time.time()))

    def mark_block_limited(self, block_id, reason=""):
        cur = self.block_cooldown.get(block_id, {"stage": -1, "reason": ""})
        stage = min(cur.get('stage', -1) + 1, len(LIMIT_BACKOFF) - 1)
        wait = LIMIT_BACKOFF[stage]
        self.block_cooldown[block_id] = {
            "until": time.time() + wait,
            "stage": stage,
            "reason": reason[:80],
        }
        return wait

    # ---------- UI ----------
    def _show_user_info(self):
        user = self.get_user()
        print()
        lines = [
            f"{NG}👤 Username      : {DW}@{user.get('username', 'N/A')}{R}",
            f"{NG}📛 Nama          : {DW}{user.get('first_name', 'N/A')}{R}",
            f"{NG}🆔 User ID       : {DW}{user.get('id', 'N/A')}{R}",
            f"{NG}💰 TR Balance    : {NY}{user.get('tr_balance', 0):,} TR{R}",
            f"{NG}💎 TON Balance   : {NY}{user.get('ton_balance', 0):.4f} TON{R}",
            f"{NG}🎯 Ads Watched   : {DW}{user.get('ads_watched_count', 0)}{R}",
            f"{NG}🎰 Spins         : {DW}{user.get('spins_available', 0)}{R}",
            f"{NG}🚫 Banned        : {DW}{user.get('is_banned', False)}{R}",
        ]
        print_box("✅ USER INFO", lines, NG)

    def _show_blocks(self):
        user = self.get_user()
        today = user.get('today_ads_watched', {}) if isinstance(user, dict) else {}
        print()
        lines = []
        for b in AD_BLOCKS:
            cnt = today.get(b['id'], 0)
            if self.is_block_limited(b['id']):
                left = self.block_limited_left(b['id'])
                m, s = divmod(left, 60)
                status = f"{NR}🔒 LIMITED {m}m{s}s{R}"
            elif cnt >= 1:
                status = f"{NG}✅ DONE{R}"
            else:
                status = f"{NY}⭕ READY{R}"
            lines.append(f"{NC}{b['id']:<12}{R} : {status} {DG}({b['reward']}){R}")
        print_box("📺 AD BLOCKS", lines, NC)

    def _get_ready_blocks(self):
        """Block yang (a) belum watched today, (b) gak lagi kena limit."""
        user = self.get_user()
        today = user.get('today_ads_watched', {}) if isinstance(user, dict) else {}
        ready = []
        for b in AD_BLOCKS:
            if today.get(b['id'], 0) >= 1:
                continue
            if self.is_block_limited(b['id']):
                continue
            ready.append(b)
        return ready

    def _all_blocks_limited_or_done(self):
        """True kalau semua block either done atau limited."""
        user = self.get_user()
        today = user.get('today_ads_watched', {}) if isinstance(user, dict) else {}
        for b in AD_BLOCKS:
            if today.get(b['id'], 0) >= 1:
                continue
            if not self.is_block_limited(b['id']):
                return False
        return True

    # ============ MAIN LOOP ============
    def auto_watch_loop(self):
        Anim.dots("sync user", 1.5)
        human_pause(0.5, 1.5)
        if not self.sync_user():
            print(f"{NR}❌ Sync user gagal!{R}")
            return

        Anim.dots("verify channels", 1.0)
        human_pause(0.5, 1.5)
        self.verify_channels()
        self.sync_user()

        self._show_user_info()
        self._show_blocks()

        next_break_at = random.randint(*SESSION_BREAK_EVERY)

        while self.stats['cycles'] < MAX_CYCLES:
            self.stats['cycles'] += 1

            # ==== session break (istirahat random) ====
            if self.stats['cycles'] >= next_break_at and self.stats['cycles'] > 1:
                brk = random.randint(*SESSION_BREAK_LEN)
                m, s = divmod(brk, 60)
                print(f"\n{NY}☕ Session break — istirahat {m}m {s}s biar keliatan manusia...{R}")
                # progress bar santai
                start = time.time()
                while time.time() - start < brk:
                    el = time.time() - start
                    rem = brk - el
                    pct = el / brk
                    bar_len = 24
                    filled = int(bar_len * pct)
                    bar = '█' * filled + '░' * (bar_len - filled)
                    sys.stdout.write(f"\r  {NC}☕ {NG}[{bar}]{R} {NY}{rem:5.0f}s{R}")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write('\r' + ' ' * 60 + '\r')
                next_break_at = self.stats['cycles'] + random.randint(*SESSION_BREAK_EVERY)
                # refresh pas bangun
                self.sync_user()
                self._show_blocks()

            ready = self._get_ready_blocks()

            # kalau gak ada yang ready
            if not ready:
                if self._all_blocks_limited_or_done():
                    print(f"\n{NG}✅ Semua block done atau lagi limit. Bot stop.{R}")
                    break
                else:
                    print(f"\n{NY}⚠ Gak ada block ready — tunggu...{R}")
                    human_pause(60, 180, label="idle wait")

            print(f"\n{NP}{'═' * 60}{R}")
            print(f"{NP}  🔄 CYCLE #{self.stats['cycles']}  |  {len(ready)} block ready{R}")
            print(f"{NP}{'═' * 60}{R}")

            total = len(ready)
            cycle_success = 0
            cycle_fail = 0
            cycle_skip = 0

            for idx, block in enumerate(ready, 1):
                # cek ulang — mungkin udah kena limit pas di loop sebelumnya
                if self.is_block_limited(block['id']):
                    left = self.block_limited_left(block['id'])
                    print(f"\n{NY}  ┌─ [{idx:02d}/{total:02d}] {block['id']} — SKIP (limited {left}s){R}")
                    cycle_skip += 1
                    continue

                print(f"\n{NC}  ┌─ [{idx:02d}/{total:02d}] {block['id']} {DG}({block['reward']}){R}")

                # micro pause sebelum "nonton" — kayak buka ad dulu
                micro_pause()

                # durasi nonton random tiap block
                watch_sec = random.randint(*AD_DURATION_RANGE)
                Anim.watch_bar(block['id'], watch_sec)

                # micro pause setelah nonton sebelum POST
                micro_pause()

                result = self.watch_ad(block['id'])

                if result and result.get('success'):
                    reward = result.get('reward_amount', 0)
                    currency = result.get('currency', '?')
                    user_new = result.get('user', {})

                    if currency == 'TR':
                        self.stats['tr_earned'] += reward
                    elif currency == 'TON':
                        self.stats['ton_earned'] += reward

                    self.stats['ads_watched'] += 1
                    cycle_success += 1
                    if user_new:
                        self.user_data = user_new

                    print(f"{NG}  ✅ {block['id']}: +{reward} {currency} | bal: {user_new.get('tr_balance',0):,} TR | {user_new.get('ton_balance',0):.4f} TON{R}")

                    # jeda antar block — random, gak fix
                    if idx < total:
                        human_pause(*DELAY_BETWEEN_RANGE, label=f"next block in")
                else:
                    err = (result or {}).get('error', (result or {}).get('message', 'unknown'))

                    if is_limit_error(err):
                        wait = self.mark_block_limited(block['id'], str(err))
                        m, w = divmod(wait, 60)
                        print(f"{NY}  🔒 {block['id']}: LIMIT — skip, cooldown {m}m{w}s{R}")
                        print(f"{DG}      reason: {str(err)[:70]}{R}")
                        self.stats['skipped'] += 1
                        cycle_skip += 1
                        # jeda kecil aja biar cepet lanjut block lain
                        human_pause(2, 6)
                    else:
                        print(f"{NR}  ❌ {block['id']}: {str(err)[:80]}{R}")
                        self.stats['failed'] += 1
                        cycle_fail += 1
                        human_pause(3, 8)

            # ==== refresh ====
            print()
            Anim.dots("refresh user", 1.0)
            human_pause(1, 3)
            self.sync_user()

            # ==== evaluasi ====
            remaining = self._get_ready_blocks()

            if not remaining:
                if self._all_blocks_limited_or_done():
                    print(f"\n{NG}🏁 Semua block done/limited. Bot stop.{R}")
                    break
                else:
                    # gak ada yang ready tapi belum done semua — tunggu panjang
                    wait = random.randint(*ALL_LIMITED_SLEEP)
                    m, s = divmod(wait, 60)
                    print(f"\n{NY}⏳ {len(AD_BLOCKS)} block, gak ada ready. Tunggu {m}m {s}s...{R}")
                    human_pause(wait - 5, wait + 5, label="waiting")

            # kalau cycle gagal total & gak ada skip → stop biar gak spam
            if cycle_success == 0 and cycle_skip == 0 and cycle_fail > 0:
                print(f"\n{NR}⚠ Cycle gagal total, stop biar gak spam.{R}")
                break

            # kalau semua sisa di-skip (limit), tidur panjang
            if cycle_success == 0 and cycle_skip > 0 and not remaining:
                wait = random.randint(*ALL_LIMITED_SLEEP)
                m, s = divmod(wait, 60)
                print(f"\n{NY}⏳ Semua sisa block kena limit — tunggu {m}m {s}s...{R}")
                human_pause(wait - 5, wait + 5, label="limit wait")
                continue

            # masih ada ready → cycle delay random
            if remaining:
                wait = random.randint(*CYCLE_DELAY_RANGE)
                m, s = divmod(wait, 60)
                print(f"\n{NY}⏳ {len(remaining)} block ready — cycle berikutnya {m}m {s}s...{R}")
                human_pause(wait - 3, wait + 3, label="next cycle")

        self._show_summary()

    def _show_summary(self):
        user = self.get_user()
        dur = (datetime.now() - self.stats['start_time']).total_seconds()
        print()
        lines = [
            f"{NC}🔄 Cycles        : {DW}{self.stats['cycles']}{R}",
            f"{NG}📺 Ads Watched   : {DW}{self.stats['ads_watched']}{R}",
            f"{NG}💰 TR Earned     : {NY}{self.stats['tr_earned']:,} TR{R}",
            f"{NG}💎 TON Earned    : {NY}{self.stats['ton_earned']:.4f} TON{R}",
            f"{NY}🔒 Skipped/Limit : {DW}{self.stats['skipped']}{R}",
            f"{NR}❌ Failed        : {DW}{self.stats['failed']}{R}",
            f"{NC}⏱  Duration      : {DW}{int(dur//60)}m {int(dur%60)}s{R}",
            f"{NM}💰 TR Balance    : {NY}{user.get('tr_balance', 0):,} TR{R}",
            f"{NM}💎 TON Balance   : {NY}{user.get('ton_balance', 0):.4f} TON{R}",
        ]
        print_box("🏁 FINAL SUMMARY", lines, NG)


def main():
    clear()
    Anim.matrix_rain(lines=5, width=60, duration=1.2)
    print()
    Anim.glitch("TREWARDS AUTO WATCH v1.2", 0.5)
    Anim.boot(1.5)
    clear()
    print(BANNER)

    user_id = get_user_id()
    if not user_id:
        print(f"{NR}❌ User ID wajib!{R}")
        sys.exit(1)

    bot = TRewardsBot()
    bot.user_id = user_id

    print()
    Anim.glitch("STARTING AUTO WATCH (HUMAN MODE)", 0.4)

    try:
        bot.auto_watch_loop()
    except KeyboardInterrupt:
        print(f"\n{NY}⏹️  Stopped by user.{R}")
        bot._show_summary()
    except Exception as e:
        print(f"\n{NR}❌ Error: {e}{R}")
        import traceback; traceback.print_exc()

    input(f"\n{NC}Press Enter to exit...{R}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{NY}Stopped.{R}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{NR}Fatal: {e}{R}")
        import traceback; traceback.print_exc()
        sys.exit(1)
