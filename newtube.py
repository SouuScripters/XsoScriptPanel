import requests
import json
import time
import sys
import os
import re
import random
import hashlib
from datetime import datetime

# ============================================================
#  ANSI 256 HELPERS
# ============================================================
RESET = "\033[0m"

def fg(c):    return f"\033[38;5;{c}m"
def bold(s):  return f"\033[1m{s}\033[22m"
def dim(s):   return f"\033[2m{s}\033[22m"

def gradient(text, start=51, end=196):
    n = len(text)
    if n <= 1:
        return fg(start) + text + RESET
    out = ""
    for i, ch in enumerate(text):
        t = i / (n - 1)
        c = int(round(start + (end - start) * t))
        out += fg(c) + ch
    return out + RESET

def tag_color(tag):
    m = {
        "AUTH":     fg(46)  + bold("AUTH"),
        "STATUS":   fg(51)  + bold("STATUS"),
        "CAPTCHA":  fg(213) + bold("CAPTCHA"),
        "CLAIM":    fg(226) + bold("CLAIM"),
        "WAIT":     fg(208) + bold("WAIT"),
        "BLOCK":    fg(196) + bold("BLOCK"),
        "SYSTEM":   fg(135) + bold("SYSTEM"),
        "AD":       fg(81)  + bold("AD"),
        "VIDEO":    fg(135) + bold("VIDEO"),
        "ERROR":    fg(196) + bold("ERROR"),
        "INIT":     fg(213) + bold("INIT"),
        "SPIN":     fg(213) + bold("SPIN"),
        "JOIN":     fg(46)  + bold("JOIN"),
        "GIFT":     fg(226) + bold("GIFT"),
    }
    return m.get(tag.strip(), fg(250) + bold(tag))

def tag_icon(tag):
    m = {
        "AUTH":     "●",
        "STATUS":   "●",
        "CAPTCHA":  "◉",
        "CLAIM":    "✔",
        "WAIT":     "◷",
        "BLOCK":    "✖",
        "SYSTEM":   "⚙",
        "AD":       "▶",
        "VIDEO":    "◈",
        "ERROR":    "✖",
        "INIT":     "⚡",
        "SPIN":     "◉",
        "JOIN":     "✔",
        "GIFT":     "🎁",
    }
    return m.get(tag.strip(), "•")

def ansi_len(s):
    return len(re.sub(r'\033\[[0-9;]*m', '', s))

def ansi_pad(s, length):
    pad = length - ansi_len(s)
    return s + (" " * pad if pad > 0 else "")

def human_delay(min_ms=150, max_ms=700):
    time.sleep(random.randint(min_ms, max_ms) / 1000.0)

def human_pause(min_ms=400, max_ms=1200):
    time.sleep(random.randint(min_ms, max_ms) / 1000.0)


# ============================================================
#  CONFIG / CONSTANTS
# ============================================================
VERSION = "6.0"
BASE_URL = "https://newtube-ton.vercel.app/api"

WAIT_TIMES = {
    "adsgramDaily":   20,
    "adsgramSpecial": 25,
    "monetag":        20,
    "giga":           25,
    "usl":            25,
}
VIDEO_WAIT = 90
SPIN_WAIT = 8
DELAY_BETWEEN_ADS = 2
DELAY_BETWEEN_NETWORKS = 3
RETRY_DELAY = 5
MAX_CONSECUTIVE_FAIL = 3

CONFIG_FILE = "config.json"

# ============================================================
#  GLOBAL STATE
# ============================================================
STATS = {
    "ads":       0,
    "rewards":   0,
    "spins":     0,
    "spin_rewards": 0,
    "start":     time.time(),
    "log":       [],
}
ACC = {
    "user":    "?",
    "balance": "0",
    "status":  "idle",
}

def add_log(tag, msg):
    STATS["log"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "tag":  tag,
        "msg":  msg,
    })
    if len(STATS["log"]) > 6:
        STATS["log"].pop(0)


# ============================================================
#  BOX / BANNER
# ============================================================
def box_line(content):
    return fg(51) + "║  " + RESET + ansi_pad(content, 60) + fg(51) + "║" + RESET + "\n"

def box_divider():
    return fg(51) + "╠══════════════════════════════════════════════════════════════╣" + RESET + "\n"


def banner(status_text="RUNNING"):
    s  = STATS
    a  = ACC
    rt = int(time.time() - s["start"])
    rts = f"{rt//3600:02d}:{(rt%3600)//60:02d}:{rt%60:02d}"

    buf = ""
    buf += fg(51) + "╔══════════════════════════════════════════════════════════════╗" + RESET + "\n"
    buf += box_line(gradient("NEWTUBE TON AUTO WATCH", 51, 213))
    buf += box_line(dim("─────── SOUU ENGINE v6 ───────"))
    buf += box_divider()

    # NETWORK
    buf += box_line(fg(213) + bold("NETWORK") + RESET)
    buf += box_line(fg(51) + "├─ Adsgram Daily   : " + RESET + fg(226) + "10x @ 10 WTC" + RESET)
    buf += box_line(fg(51) + "├─ Adsgram Special : " + RESET + fg(226) + "10x @ 25 WTC" + RESET)
    buf += box_line(fg(51) + "├─ Monetag         : " + RESET + fg(226) + "10x @ 10 WTC" + RESET)
    buf += box_line(fg(51) + "├─ Giga            : " + RESET + fg(226) + "15x @ 15 WTC" + RESET)
    buf += box_line(fg(51) + "├─ USL             : " + RESET + fg(226) + "10x @ 15 WTC" + RESET)
    buf += box_line(fg(51) + "├─ Video Mining    : " + RESET + fg(226) + "10x @ 60 WTC" + RESET)
    buf += box_line(fg(51) + "└─ Spin Wheel      : " + RESET + fg(226) + "30x bonus" + RESET)
    buf += box_divider()

    # ACCOUNT
    buf += box_line(fg(213) + bold("ACCOUNT") + RESET)
    buf += box_line(fg(51) + "├─ User       : " + RESET + fg(226) + str(a["user"]) + RESET)
    buf += box_line(fg(51) + "├─ Balance    : " + RESET + fg(46) + str(a["balance"]) + " WTC" + RESET)
    buf += box_line(fg(51) + "└─ Status     : " + RESET + fg(226) + str(a["status"]) + RESET)
    buf += box_divider()

    # SYSTEM
    buf += box_line(fg(213) + bold("SYSTEM") + RESET)
    buf += box_line(fg(51) + "├─ Ads Done     : " + RESET + fg(226) + str(s["ads"]) + RESET)
    buf += box_line(fg(51) + "├─ Spins Done   : " + RESET + fg(213) + str(s["spins"]) + RESET)
    buf += box_line(fg(51) + "├─ Rewards      : " + RESET + fg(46) + "+" + str(s["rewards"]) + " WTC" + RESET)
    buf += box_line(fg(51) + "└─ Runtime      : " + RESET + fg(208) + rts + RESET)
    buf += box_divider()

    # LOGS (6 lines)
    for i in range(6):
        if i < len(s["log"]):
            l    = s["log"][i]
            icon = tag_icon(l["tag"])
            tag  = tag_color(l["tag"])
            line = dim(f"[{l['time']}]") + " " + fg(250) + icon + RESET + " " + tag + " " + fg(252) + l["msg"] + RESET
            buf += box_line(line)
        else:
            buf += fg(51) + "║" + (" " * 62) + "║" + RESET + "\n"

    buf += fg(51) + "╚══════════════════════════════════════════════════════════════╝" + RESET + "\n"
    buf += "\n   " + gradient(f"BOT {status_text}", 46, 226) + " " + fg(250) + "• " + datetime.now().strftime("%H:%M:%S") + RESET + "\n"
    buf += "   " + dim("By Power ") + fg(213) + "@SouuXso" + RESET + dim(" • ") + fg(46) + "NewTube TON v6" + RESET + "\n\n"

    sys.stdout.write(buf)
    sys.stdout.flush()


# ============================================================
#  TIMER (spinner)
# ============================================================
def timer(seconds, prefix="  wait.."):
    wait_time = int(seconds)
    if wait_time <= 0:
        wait_time = 1
    frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    fc = len(frames)
    cf = 0
    while wait_time > 0:
        start = time.time()
        while (time.time() - start) < 1:
            h = wait_time // 3600
            m = (wait_time % 3600) // 60
            s = wait_time % 60
            tf = f"{h:02d}:{m:02d}:{s:02d}"
            sp = frames[cf]
            sys.stdout.write(fg(250) + prefix + fg(46) + f" {tf} " + fg(226) + sp + "\r")
            sys.stdout.flush()
            time.sleep(0.1)
            cf = (cf + 1) % fc
            if (time.time() - start) >= 1:
                break
        wait_time -= 1
    sys.stdout.write("\r" + (" " * 60) + "\r")
    sys.stdout.flush()


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


# ============================================================
#  CONFIG IO
# ============================================================
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            c = json.load(f)
        if "initData" not in c:
            return None
        # auto-generate fingerprint kalau belum ada
        if "fingerprint" not in c or not c["fingerprint"]:
            c["fingerprint"] = hashlib.sha256(
                (str(time.time()) + str(random.random())).encode()
            ).hexdigest()
            save_config(c)
        return c
    except Exception:
        return None


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ============================================================
#  BOT CLASS
# ============================================================
class NewTubeBot:
    def __init__(self, init_data, fingerprint):
        self.init_data = self.clean_init_data(init_data)
        self.fingerprint = fingerprint
        self.last_balance = 0
        self.headers = {
            "Host": "newtube-ton.vercel.app",
            "content-type": "application/json",
            "user-agent": (
                "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
                "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"
            ),
            "origin": "https://newtube-ton.vercel.app",
            "referer": "https://newtube-ton.vercel.app/",
            "x-requested-with": "org.telegram.messenger.web",
            "accept": "*/*",
            "accept-language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def clean_init_data(self, raw_data):
        cleaned = raw_data.strip()
        cleaned = ''.join(c for c in cleaned if c.isprintable() or c in '\n\r\t')
        cleaned = cleaned.replace('\n', '').replace('\r', '').replace('\t', '')
        cleaned = re.sub(r'^initData\s*[:=]\s*', '', cleaned)
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        cleaned = ' '.join(cleaned.split())
        return cleaned

    # ===== INIT =====
    def init_user(self):
        """POST /api/user {action: 'init', fingerprint, initData}"""
        url = f"{BASE_URL}/user"
        payload = {
            "action": "init",
            "fingerprint": self.fingerprint,
            "initData": self.init_data,
        }
        try:
            r = requests.post(url, headers=self.headers, json=payload, timeout=30)
            if r.status_code != 200:
                return False
            data = r.json()
            return data.get('ok', False)
        except Exception as e:
            add_log("ERROR", f"init err: {str(e)[:40]}")
            return False

    # ===== CHECK JOIN =====
    def check_join(self):
        """GET /api/user?action=checkJoin"""
        url = f"{BASE_URL}/user"
        params = {"action": "checkJoin", "initData": self.init_data}
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
            return data.get('joined', False)
        except Exception:
            return None

    # ===== CHECK GIFT =====
    def check_gift(self):
        """GET /api/gift?action=check"""
        url = f"{BASE_URL}/gift"
        params = {"action": "check", "initData": self.init_data}
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
            return data.get('gift')
        except Exception:
            return None

    # ===== PROFILE =====
    def get_profile(self):
        url = f"{BASE_URL}/user"
        params = {"action": "profile", "initData": self.init_data}
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"HTTP {r.status_code}")
                return None
            data = r.json()
            if data.get('ok'):
                user = data.get('user', {})
                ACC["user"] = user.get('firstName', 'User')
                ACC["balance"] = str(user.get('wtcBalance', 0))
                self.last_balance = user.get('wtcBalance', 0)
                return {
                    'balance':        user.get('wtcBalance', 0),
                    'daily_count':    user.get('adsgramDailyCountToday', 0),
                    'special_count':  user.get('adsgramSpecialCountToday', 0),
                    'monetag_count':  user.get('monetagCountToday', 0),
                    'giga_count':     user.get('gigaCountToday', 0),
                    'usl_count':      user.get('uslCountToday', 0),
                    'video_mined':    user.get('dailyVideoWtcMined', 0),
                    'bonus_spins':    user.get('bonusSpinsAvailable', 0),
                    'spins_used':     user.get('bonusSpinsUsedToday', 0),
                    'is_banned':      user.get('isBanned', False),
                    'channel_verified': user.get('channelVerified', False),
                }
            else:
                add_log("ERROR", f"API: {str(data)[:50]}")
                return None
        except requests.exceptions.ConnectionError:
            add_log("ERROR", "Connection error")
            return None
        except requests.exceptions.Timeout:
            add_log("ERROR", "Timeout")
            return None
        except Exception as e:
            add_log("ERROR", f"{str(e)[:50]}")
            return None

    # ===== WATCH AD (dengan viewMs!) =====
    def watch_ad(self, network_type):
        url = f"{BASE_URL}/earn"

        # Step 1: adStart
        start_payload = {
            "action": "adStart",
            "network": network_type,
            "initData": self.init_data,
        }
        try:
            human_delay(120, 350)
            r = requests.post(url, headers=self.headers, json=start_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"adStart HTTP {r.status_code}")
                return None
            start_data = r.json()
            if not start_data.get('ok'):
                msg = str(start_data)[:40]
                add_log("ERROR", f"adStart: {msg}")
                return None

            start_time = start_data.get('startTime')
            signature = start_data.get('signature')

            # Step 2: wait (tampilin timer)
            wait_time = WAIT_TIMES.get(network_type, 20)
            clear()
            banner("RUNNING")
            timer(wait_time, f"  {network_type}..")

            # hitung viewMs aktual (ms sejak startTime server)
            view_ms = int(time.time() * 1000) - int(start_time)
            # safety: minimal 5s
            if view_ms < 5000:
                view_ms = 5000 + random.randint(200, 800)

            # Step 3: claimAdReward — WAJIB ada viewMs!
            claim_payload = {
                "action": "claimAdReward",
                "network": network_type,
                "startTime": start_time,
                "signature": signature,
                "viewMs": view_ms,
                "initData": self.init_data,
            }
            human_delay(150, 400)
            r = requests.post(url, headers=self.headers, json=claim_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"claim HTTP {r.status_code}")
                return None
            claim_data = r.json()

            if claim_data.get('ok'):
                # coba extract reward dari beberapa kemungkinan field
                reward = 0
                if 'reward' in claim_data:
                    reward = claim_data['reward']
                elif 'user' in claim_data:
                    # hitung delta balance
                    new_bal = claim_data['user'].get('wtcBalance', self.last_balance)
                    reward = new_bal - self.last_balance
                    self.last_balance = new_bal
                    ACC["balance"] = str(new_bal)
                return {
                    'reward': reward,
                    'count_today': claim_data.get('countToday', 0),
                    'daily_limit': claim_data.get('dailyLimit', 10),
                }
            else:
                msg = claim_data.get('message') or claim_data.get('error') or str(claim_data)[:40]
                add_log("ERROR", f"claim: {msg}")
                return None
        except Exception as e:
            add_log("ERROR", f"ad err: {str(e)[:40]}")
            return None

    # ===== WATCH VIDEO =====
    def watch_video(self):
        url = f"{BASE_URL}/earn"

        start_payload = {"action": "videoStart", "initData": self.init_data}
        try:
            human_delay(120, 350)
            r = requests.post(url, headers=self.headers, json=start_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"videoStart HTTP {r.status_code}")
                return None
            start_data = r.json()
            if not (start_data.get('success') or start_data.get('ok')):
                add_log("ERROR", f"videoStart: {str(start_data)[:40]}")
                return None

            start_time = start_data.get('startTime')
            signature = start_data.get('signature')

            clear()
            banner("RUNNING")
            timer(VIDEO_WAIT, "  video..")

            view_ms = int(time.time() * 1000) - int(start_time)

            claim_payload = {
                "action": "videoClaim",
                "startTime": start_time,
                "signature": signature,
                "viewMs": view_ms,
                "initData": self.init_data,
            }
            human_delay(150, 400)
            r = requests.post(url, headers=self.headers, json=claim_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"videoClaim HTTP {r.status_code}")
                return None
            claim_data = r.json()
            if claim_data.get('success') or claim_data.get('ok'):
                reward = claim_data.get('reward', 60)
                if reward == 0 and 'user' in claim_data:
                    new_bal = claim_data['user'].get('wtcBalance', self.last_balance)
                    reward = new_bal - self.last_balance
                    self.last_balance = new_bal
                    ACC["balance"] = str(new_bal)
                return {'reward': reward}
            else:
                add_log("ERROR", f"videoClaim: {str(claim_data)[:40]}")
                return None
        except Exception as e:
            add_log("ERROR", f"video err: {str(e)[:40]}")
            return None

    # ===== SPIN WHEEL =====
    def spin_wheel(self):
        """POST /api/earn {action: 'spinStart'} lalu {action: 'spin', startTime, signature}"""
        url = f"{BASE_URL}/earn"

        # Step 1: spinStart
        start_payload = {"action": "spinStart", "initData": self.init_data}
        try:
            human_delay(150, 350)
            r = requests.post(url, headers=self.headers, json=start_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"spinStart HTTP {r.status_code}")
                return None
            start_data = r.json()
            if not start_data.get('ok'):
                msg = start_data.get('message') or start_data.get('error') or str(start_data)[:40]
                add_log("ERROR", f"spinStart: {msg}")
                return None

            start_time = start_data.get('startTime')
            signature = start_data.get('signature')

            # Step 2: short wait (spin animasi biasanya cuma 3-8s)
            clear()
            banner("RUNNING")
            timer(SPIN_WAIT, "  spin..")

            view_ms = int(time.time() * 1000) - int(start_time)

            # Step 3: spin (claim)
            claim_payload = {
                "action": "spin",
                "startTime": start_time,
                "signature": signature,
                "viewMs": view_ms,
                "initData": self.init_data,
            }
            human_delay(150, 400)
            r = requests.post(url, headers=self.headers, json=claim_payload, timeout=30)
            if r.status_code != 200:
                add_log("ERROR", f"spin HTTP {r.status_code}")
                return None
            claim_data = r.json()

            if claim_data.get('ok'):
                reward = claim_data.get('reward', 0)
                segment = claim_data.get('segmentIndex', '?')
                used_bonus = claim_data.get('usedBonus', False)
                left = claim_data.get('bonusSpinsLeft', 0)

                if reward == 0 and 'user' in claim_data:
                    new_bal = claim_data['user'].get('wtcBalance', self.last_balance)
                    reward = new_bal - self.last_balance
                    self.last_balance = new_bal
                    ACC["balance"] = str(new_bal)

                return {
                    'reward': reward,
                    'segment': segment,
                    'used_bonus': used_bonus,
                    'spins_left': left,
                }
            else:
                msg = claim_data.get('message') or claim_data.get('error') or str(claim_data)[:40]
                add_log("ERROR", f"spin: {msg}")
                return None
        except Exception as e:
            add_log("ERROR", f"spin err: {str(e)[:40]}")
            return None

    # ===== BATCH ADS =====
    def watch_ads_batch(self, network_type, network_name, target):
        profile = self.get_profile()
        if not profile:
            return 0
        count_key = {
            "adsgramDaily": "daily_count",
            "adsgramSpecial": "special_count",
            "monetag": "monetag_count",
            "giga": "giga_count",
            "usl": "usl_count",
        }.get(network_type, "daily_count")

        watched = profile.get(count_key, 0)
        remaining = target - watched
        if remaining <= 0:
            add_log("STATUS", f"{network_name} done ({target}x)")
            return 0

        total_reward = 0
        consecutive_fail = 0

        for i in range(remaining):
            add_log("AD", f"{network_name} {i+1}/{remaining}")
            clear()
            banner("RUNNING")

            result = self.watch_ad(network_type)
            if result:
                total_reward += result['reward']
                STATS["rewards"] += result['reward']
                STATS["ads"] += 1
                consecutive_fail = 0
                add_log("CLAIM", f"+{result['reward']} WTC | {result['count_today']}/{result['daily_limit']}")
                clear()
                banner("RUNNING")
            else:
                consecutive_fail += 1
                add_log("ERROR", f"Fail ({consecutive_fail}/{MAX_CONSECUTIVE_FAIL})")
                clear()
                banner("RUNNING")
                if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                    add_log("BLOCK", f"{network_name} stop")
                    clear()
                    banner("RUNNING")
                    break
                time.sleep(RETRY_DELAY)

            if i < remaining - 1:
                time.sleep(DELAY_BETWEEN_ADS)

        return total_reward

    # ===== BATCH SPINS =====
    def spin_batch(self, target=None):
        """Spin sampai bonus habis atau target tercapai."""
        profile = self.get_profile()
        if not profile:
            return 0
        available = profile.get('bonus_spins', 0)
        if target is None:
            target = available
        remaining = min(target, available)
        if remaining <= 0:
            add_log("STATUS", f"Spin habis (0 tersedia)")
            return 0

        total_reward = 0
        consecutive_fail = 0

        for i in range(remaining):
            add_log("SPIN", f"Spin {i+1}/{remaining}")
            clear()
            banner("RUNNING")

            result = self.spin_wheel()
            if result:
                total_reward += result['reward']
                STATS["spin_rewards"] += result['reward']
                STATS["spins"] += 1
                STATS["rewards"] += result['reward']
                consecutive_fail = 0
                add_log("SPIN", f"+{result['reward']} WTC | seg={result['segment']} | sisa={result['spins_left']}")
                clear()
                banner("RUNNING")
            else:
                consecutive_fail += 1
                add_log("ERROR", f"Spin fail ({consecutive_fail}/{MAX_CONSECUTIVE_FAIL})")
                clear()
                banner("RUNNING")
                if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                    add_log("BLOCK", "Spin stop")
                    clear()
                    banner("RUNNING")
                    break
                time.sleep(RETRY_DELAY)

            if i < remaining - 1:
                time.sleep(DELAY_BETWEEN_ADS)

        return total_reward

    # ===== BATCH VIDEOS =====
    def watch_videos_batch(self, target=10):
        profile = self.get_profile()
        if not profile:
            return 0
        mined = profile.get('video_mined', 0)
        remaining = target - mined
        if remaining <= 0:
            add_log("STATUS", f"Video done ({target}x)")
            return 0

        total_reward = 0
        consecutive_fail = 0
        for i in range(remaining):
            add_log("VIDEO", f"Mining {i+1}/{remaining}")
            clear()
            banner("RUNNING")

            result = self.watch_video()
            if result and result['reward'] > 0:
                total_reward += result['reward']
                STATS["rewards"] += result['reward']
                STATS["ads"] += 1
                consecutive_fail = 0
                add_log("CLAIM", f"+{result['reward']} WTC (video)")
                clear()
                banner("RUNNING")
            else:
                consecutive_fail += 1
                add_log("ERROR", f"Video fail ({consecutive_fail}/{MAX_CONSECUTIVE_FAIL})")
                clear()
                banner("RUNNING")
                if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                    add_log("BLOCK", "Video stop")
                    clear()
                    banner("RUNNING")
                    break
                time.sleep(RETRY_DELAY)

            if i < remaining - 1:
                time.sleep(DELAY_BETWEEN_NETWORKS)

        return total_reward

    # ===== RUN ALL =====
    def run_all(self, do_spin=True):
        # Reset stats
        STATS["ads"] = 0
        STATS["rewards"] = 0
        STATS["spins"] = 0
        STATS["spin_rewards"] = 0
        STATS["start"] = time.time()
        STATS["log"] = []

        add_log("INIT", f"Engine v{VERSION} boot")
        clear()
        banner("INIT")

        # Step 1: init user (register fingerprint)
        human_delay(200, 500)
        add_log("INIT", "Register fingerprint...")
        clear()
        banner("INIT")
        self.init_user()

        # Step 2: check force-join
        add_log("JOIN", "Checking channel join...")
        clear()
        banner("INIT")
        joined = self.check_join()
        if joined is False:
            add_log("JOIN", "Belum join channel/group!")
            clear()
            banner("ERROR")
            sys.stdout.write(fg(196) + "\n  ✖ Wajib join channel & group dulu. Enter...\n" + RESET)
            sys.stdout.flush()
            input()
            return
        add_log("JOIN", "Channel & group OK")

        # Step 3: check gift
        gift = self.check_gift()
        if gift:
            add_log("GIFT", f"Gift available: {str(gift)[:30]}")
        else:
            add_log("GIFT", "No gift tersedia")

        # Step 4: fetch profile
        human_delay(200, 500)
        profile = self.get_profile()
        if not profile:
            add_log("ERROR", "Cannot fetch profile")
            clear()
            banner("ERROR")
            sys.stdout.write(fg(196) + "\n  ✖ Profile error. Enter...\n" + RESET)
            sys.stdout.flush()
            input()
            return

        if profile.get('is_banned'):
            add_log("ERROR", "User banned")
            clear()
            banner("ERROR")
            sys.stdout.write(fg(196) + "\n  ✖ User banned. Enter...\n" + RESET)
            sys.stdout.flush()
            input()
            return

        ACC["status"] = "running"
        add_log("AUTH", f"Login as {ACC['user']} | +{profile.get('bonus_spins', 0)} spins")
        clear()
        banner("RUNNING")

        # ===== ADS =====
        ad_types = [
            ("adsgramDaily",   "Daily",   10),
            ("adsgramSpecial", "Special", 10),
            ("monetag",        "Monetag", 10),
            ("giga",           "Giga",    15),
            ("usl",            "USL",     10),
        ]

        for i, (net_type, name, target) in enumerate(ad_types):
            if i > 0:
                time.sleep(DELAY_BETWEEN_NETWORKS)
            self.watch_ads_batch(net_type, name, target)

        # ===== SPIN WHEEL =====
        if do_spin:
            time.sleep(DELAY_BETWEEN_NETWORKS)
            add_log("SPIN", "Auto spin wheel...")
            clear()
            banner("RUNNING")
            self.spin_batch()

        # ===== VIDEO =====
        time.sleep(DELAY_BETWEEN_NETWORKS)
        self.watch_videos_batch(10)

        # ===== DONE =====
        ACC["status"] = "done"
        add_log("SYSTEM", f"Finished +{STATS['rewards']} WTC ({STATS['spins']} spins)")
        clear()
        banner("DONE")

        sys.stdout.write(fg(226) + "\n  ⏱  Farming selesai. Enter balik ke menu...\n" + RESET)
        sys.stdout.flush()
        input()
        ACC["status"] = "idle"


# ============================================================
#  MENU
# ============================================================
def menu():
    cfg = get_config()
    init_disp = "belum diset"
    if cfg and cfg.get("initData"):
        raw = cfg["initData"]
        init_disp = raw[:30] + "..." if len(raw) > 30 else raw

    fp_disp = "-"
    if cfg and cfg.get("fingerprint"):
        fp_disp = cfg["fingerprint"][:16] + "..."

    buf = ""
    buf += fg(51) + "╔══════════════════════════════════════════════════════════════╗" + RESET + "\n"
    buf += box_line(gradient("NEWTUBE TON MENU v6", 51, 213))
    buf += box_divider()
    buf += box_line(fg(51) + "  initData    : " + RESET + fg(226) + init_disp + RESET)
    buf += box_line(fg(51) + "  fingerprint : " + RESET + fg(226) + fp_disp + RESET)
    buf += box_divider()
    buf += box_line(fg(46)  + "  [1] " + RESET + fg(252) + "Start Farming (Ads + Spin + Video)" + RESET)
    buf += box_line(fg(213) + "  [2] " + RESET + fg(252) + "Spin Wheel Only" + RESET)
    buf += box_line(fg(81)  + "  [3] " + RESET + fg(252) + "Config initData" + RESET)
    buf += box_line(fg(196) + "  [4] " + RESET + fg(252) + "Regenerate Fingerprint" + RESET)
    buf += box_line(fg(196) + "  [0] " + RESET + fg(252) + "Exit" + RESET)
    buf += fg(51) + "╚══════════════════════════════════════════════════════════════╝" + RESET + "\n\n"
    buf += fg(51) + "  Pilih >> " + RESET

    sys.stdout.write(buf)
    sys.stdout.flush()


def action_config_initdata():
    cfg = get_config() or {"initData": "", "fingerprint": ""}
    sys.stdout.write("\n" + fg(213) + "  initData baru (query_id=...) : " + RESET)
    sys.stdout.flush()
    val = sys.stdin.readline().strip()
    if val:
        val = val.strip()
        val = ''.join(c for c in val if ord(c) >= 32 or c in '\n\r\t')
        val = val.replace('\n', '').replace('\r', '').replace('\t', '')
        val = re.sub(r'^initData\s*[:=]\s*', '', val)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        cfg["initData"] = val
        save_config(cfg)
        sys.stdout.write(fg(46) + f"  ✓ initData disimpan ({len(val)} karakter)\n" + RESET)
    else:
        sys.stdout.write(fg(196) + "  ✖ kosong, tidak disimpan\n" + RESET)
    sys.stdout.flush()
    human_pause(500, 900)


def action_regen_fingerprint():
    cfg = get_config() or {"initData": "", "fingerprint": ""}
    old = cfg.get("fingerprint", "")
    new = hashlib.sha256(
        (str(time.time()) + str(random.random())).encode()
    ).hexdigest()
    cfg["fingerprint"] = new
    save_config(cfg)
    sys.stdout.write("\n" + fg(46) + f"  ✓ Fingerprint baru: {new[:32]}...\n" + RESET)
    sys.stdout.flush()
    human_pause(800, 1200)


def action_spin_only():
    cfg = get_config()
    if not cfg or not cfg.get("initData"):
        clear()
        sys.stdout.write(fg(196) + "\n  ✖ Config initData belum diset.\n" + RESET)
        sys.stdout.write(fg(250) + "  Tekan Enter..." + RESET)
        sys.stdout.flush()
        input()
        return
    bot = NewTubeBot(cfg["initData"], cfg.get("fingerprint", ""))
    STATS["start"] = time.time()
    STATS["log"] = []

    bot.init_user()
    profile = bot.get_profile()
    if not profile:
        sys.stdout.write(fg(196) + "\n  ✖ Profile error.\n" + RESET)
        sys.stdout.flush()
        input()
        return

    ACC["status"] = "spin"
    add_log("SPIN", f"Bonus available: {profile.get('bonus_spins', 0)}")
    clear()
    banner("RUNNING")
    bot.spin_batch()

    add_log("SYSTEM", f"Spin done +{STATS['spin_rewards']} WTC")
    clear()
    banner("DONE")
    sys.stdout.write(fg(226) + "\n  ⏱  Spin selesai. Enter...\n" + RESET)
    sys.stdout.flush()
    input()


# ============================================================
#  MAIN LOOP
# ============================================================
def main():
    first = True
    while True:
        clear()
        if first:
            sys.stdout.write("\n")
            first = False
        menu()
        opt = sys.stdin.readline().strip()

        if opt == '1':
            cfg = get_config()
            if not cfg or not cfg.get("initData"):
                clear()
                sys.stdout.write(fg(196) + "\n  ✖ Config initData belum diset. Set dulu (menu 3).\n" + RESET)
                sys.stdout.write(fg(250) + "  Tekan Enter..." + RESET)
                sys.stdout.flush()
                input()
                continue
            bot = NewTubeBot(cfg["initData"], cfg.get("fingerprint", ""))
            bot.run_all(do_spin=True)

        elif opt == '2':
            action_spin_only()

        elif opt == '3':
            action_config_initdata()

        elif opt == '4':
            action_regen_fingerprint()

        elif opt == '0':
            clear()
            sys.stdout.write(fg(213) + "\n  bye boss 👋\n\n" + RESET)
            sys.stdout.flush()
            sys.exit(0)

        else:
            sys.stdout.write(fg(196) + "\n  ✖ Pilihan gak valid.\n" + RESET)
            sys.stdout.flush()
            human_pause(600, 1000)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write(fg(196) + "\n\n  ✖ Dihentikan\n" + RESET)
        sys.exit(0)
    except Exception as e:
        sys.stdout.write(fg(196) + f"\n  ✖ Fatal: {e}\n" + RESET)
        import traceback
        traceback.print_exc()
        sys.exit(1)
