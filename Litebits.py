#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LiteBits.io Auto Claim Bot v3.9.1
- Waryono solver: in.php + res.php only
- Auto-detect hCaptcha sitekey
- FIX v3.9.1: {RST} → {Col.R} di _solve_once
"""

import time
import json
import re
import os
import sys
import random
import urllib.parse
import urllib.request
import urllib.error
import asyncio
from datetime import datetime, timezone
from collections import deque

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class Col:
    R='\033[0m'; B='\033[1m'; D='\033[2m'
    RED='\033[91m'; GRN='\033[92m'; YEL='\033[93m'; BLU='\033[94m'
    MAG='\033[95m'; CYN='\033[96m'; WHT='\033[97m'; GRY='\033[90m'
    NEON_G='\033[38;5;46m'; NEON_C='\033[38;5;51m'; NEON_Y='\033[38;5;226m'
    NEON_P='\033[38;5;207m'; NEON_O='\033[38;5;208m'; NEON_V='\033[38;5;141m'
    NEON_R='\033[38;5;196m'; DIM_C='\033[38;5;244m'

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

class Anim:
    @staticmethod
    def spinner(text, duration=2):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        end = time.time() + duration; i = 0
        while time.time() < end:
            sys.stdout.write(f"\r {Col.NEON_C}{frames[i%len(frames)]}{Col.R} {Col.WHT}{text}{Col.R}")
            sys.stdout.flush(); time.sleep(0.08); i += 1
        sys.stdout.write(f"\r{' '*(len(text)+6)}\r")
        print(f" {Col.NEON_G}✓{Col.R} {Col.WHT}{text}{Col.R}")

    @staticmethod
    def dots(text, duration=2):
        end = time.time() + duration; n = 0
        while time.time() < end:
            sys.stdout.write(f"\r {Col.NEON_C}•{Col.R} {Col.WHT}{text}{Col.NEON_C}{'.'*((n%3)+1):<4}{Col.R}")
            sys.stdout.flush(); time.sleep(0.3); n += 1
        sys.stdout.write(f"\r{' '*(len(text)+8)}\r")
        print(f" {Col.NEON_G}✓{Col.R} {Col.WHT}{text}{Col.R}")

    @staticmethod
    def progress(text, duration=2, width=30):
        end = time.time() + duration; total = duration
        while time.time() < end:
            elapsed = duration - (end - time.time())
            pct = min(1.0, elapsed / total); filled = int(pct * width)
            bar = f"{Col.NEON_G}{'█'*filled}{Col.DIM_C}{'░'*(width-filled)}{Col.R}"
            sys.stdout.write(f"\r {Col.NEON_C}▶{Col.R} {Col.WHT}{text:<30}{Col.R} [{bar}] {Col.NEON_Y}{int(pct*100):>3}%{Col.R}")
            sys.stdout.flush(); time.sleep(0.05)
        sys.stdout.write(f"\r{' '*(len(text)+60)}\r")
        print(f" {Col.NEON_G}✓{Col.R} {Col.WHT}{text}{Col.R}")

    @staticmethod
    def scan(text, duration=2):
        end = time.time() + duration; i = 0; bar_w = 30
        while time.time() < end:
            pos = i % (bar_w * 2)
            if pos >= bar_w: pos = bar_w * 2 - pos
            bar = "".join(f"{Col.NEON_G}█{Col.R}" if abs(j-pos)<3 else f"{Col.DIM_C}·{Col.R}" for j in range(bar_w))
            sys.stdout.write(f"\r {Col.NEON_C}[SCAN]{Col.R} {Col.WHT}{text:<25}{Col.R} [{bar}]")
            sys.stdout.flush(); time.sleep(0.06); i += 1
        sys.stdout.write(f"\r{' '*(len(text)+50)}\r")
        print(f" {Col.NEON_G}✓{Col.R} {Col.WHT}{text}{Col.R}")

    @staticmethod
    def typewriter(text, delay=0.02, color=None):
        c = color or Col.WHT
        for ch in text:
            sys.stdout.write(f"{c}{ch}{Col.R}"); sys.stdout.flush(); time.sleep(delay)
        print()

    @staticmethod
    def matrix_line(width=62, duration=1.5):
        chars = "0123456789ABCDEF"
        end = time.time() + duration
        while time.time() < end:
            line = "".join(random.choice(chars) if random.random() < 0.3 else " " for _ in range(width))
            sys.stdout.write(f"\r{Col.NEON_G}{line}{Col.R}")
            sys.stdout.flush(); time.sleep(0.04)
        for _ in range(3):
            line = "".join(random.choice(chars) if random.random() < 0.1 else "─" for _ in range(width))
            sys.stdout.write(f"\r{Col.NEON_C}{line}{Col.R}")
            sys.stdout.flush(); time.sleep(0.08)
        sys.stdout.write(f"\r{Col.NEON_C}{'─'*width}{Col.R}\n")

    @staticmethod
    def opening_sequence():
        clear(); print()
        Anim.typewriter(f"{Col.NEON_C}Initializing boot sequence...", 0.02, Col.NEON_C)
        time.sleep(0.3)
        Anim.progress("Loading core modules", 1.0)
        Anim.progress("Establishing secure channel", 1.0)
        Anim.progress("Verifying signature chain", 0.8)
        print()
        Anim.matrix_line(62, 1.2)
        print()
        time.sleep(0.4)

API_HASH   = 'fb06985ea797ac51aaa1e6d1168ceaaa'
API_ID     = 35898257
BASE_URL   = 'https://mini.litebits.io'
HCAPTCHA_SITEKEY_DEFAULT = '1c602a9a-f05a-403c-9306-cacc4c64e30a'

DEFAULT_BOT      = 'litebits_faucet_bot'
DEFAULT_REFERRAL = 'A7F2K9'
CONFIG_FILE      = 'litebits.json'
SESSION_FILE     = 'session_auth'
REPORT_FILE      = 'litebits_report.txt'

HOLD_DURATION    = 5
PREPARE_WAIT     = 8
AD_VIEW_WAIT     = 20
DEFAULT_COOLDOWN = 300
MAX_RUNTIME      = 6 * 3600

CAPTCHA_TIMEOUT    = 180
CAPTCHA_POLL_DELAY = 3

WARYONO_IN  = 'https://api.waryono.my.id/in.php'
WARYONO_RES = 'https://api.waryono.my.id/res.php'

DEFAULT_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
    "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

try:
    from telethon import TelegramClient, functions, types
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

def _post_json(url, payload, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json',
                 'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Mobile)',
                 'Accept': 'application/json, text/plain, */*'})
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.HTTPError as e:
        body = ''
        try: body = e.read().decode('utf-8', errors='ignore')
        except Exception: pass
        return json.dumps({"_http_error": e.code, "_body": body, "_reason": str(e.reason)})
    except Exception as e:
        return json.dumps({"_error": str(e)})

def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Mobile)',
        'Accept': 'application/json, text/plain, */*'})
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.HTTPError as e:
        body = ''
        try: body = e.read().decode('utf-8', errors='ignore')
        except Exception: pass
        return json.dumps({"_http_error": e.code, "_body": body, "_reason": str(e.reason)})
    except Exception as e:
        return json.dumps({"_error": str(e)})

def extract_attr(html, attr_name, quote_chars='"\''):
    results = []
    if not html or not attr_name: return results
    search = attr_name + '='
    idx = 0
    while True:
        i = html.find(search, idx)
        if i < 0: break
        j = i + len(search)
        while j < len(html) and html[j] in ' \t': j += 1
        if j >= len(html): break
        q = html[j]
        if q in quote_chars:
            k = html.find(q, j + 1)
            if k > 0:
                val = html[j + 1:k]
                if val and len(val) >= 16: results.append(val.strip())
            idx = k + 1 if k > 0 else j + 1
        else:
            k = j
            while k < len(html) and html[k] not in ' \t\r\n>/': k += 1
            val = html[j:k]
            if val and len(val) >= 16: results.append(val.strip())
            idx = k
    return results

def extract_meta_content(html, meta_name):
    results = []
    if not html: return results
    idx = 0
    while True:
        i = html.find('<meta', idx)
        if i < 0: break
        j = html.find('>', i)
        if j < 0: break
        tag = html[i:j + 1]
        if ('name=' + '"' + meta_name + '"') in tag or ("name='" + meta_name + "'") in tag:
            c_idx = tag.find('content=')
            if c_idx >= 0:
                k = c_idx + len('content=')
                while k < len(tag) and tag[k] in ' \t': k += 1
                if k < len(tag) and tag[k] in '"\'':
                    q = tag[k]
                    end = tag.find(q, k + 1)
                    if end > 0: results.append(tag[k + 1:end])
        idx = j + 1
    return results

class SitekeyDetector:
    def __init__(self, session, base_url):
        self.session = session; self.base_url = base_url
        self.detected = None; self.source = None

    def detect(self):
        json_endpoints = ['/api/app-settings', '/api/config', '/api/claim/captcha',
                          '/api/captcha', '/api/captcha/config', '/api/captcha/sitekey']
        for ep in json_endpoints:
            try:
                r = self.session.get(self.base_url + ep, timeout=8)
                if r.status_code == 200:
                    try: d = r.json()
                    except Exception: continue
                    if isinstance(d, dict):
                        for key in ('sitekey','siteKey','hcaptchaSiteKey','hcaptcha_sitekey','hCaptchaSiteKey'):
                            v = d.get(key)
                            if v and isinstance(v, str) and len(v) >= 16:
                                self.detected = v; self.source = f'json:{ep}'; return v
                        for k1 in ('captcha', 'hcaptcha', 'config'):
                            sub = d.get(k1)
                            if isinstance(sub, dict):
                                for key in ('sitekey','siteKey','key'):
                                    v = sub.get(key)
                                    if v and isinstance(v, str) and len(v) >= 16:
                                        self.detected = v; self.source = f'json:{ep}.{k1}.{key}'; return v
            except Exception: continue

        html = None
        for path in ('/?v3', '/', '/claim', '/dashboard'):
            try:
                r = self.session.get(self.base_url + path, timeout=10)
                if r.status_code == 200:
                    html = r.text if hasattr(r, 'text') else r.content.decode('utf-8', errors='ignore')
                    break
            except Exception: continue

        if html:
            vals = extract_attr(html, 'data-sitekey')
            if vals: self.detected = vals[0]; self.source = 'html:data-sitekey'; return vals[0]
            vals = extract_attr(html, 'data-hcaptcha-sitekey')
            if vals: self.detected = vals[0]; self.source = 'html:data-hcaptcha-sitekey'; return vals[0]
            for meta_name in ('hcaptcha-sitekey', 'hcaptcha_sitekey', 'sitekey'):
                vals = extract_meta_content(html, meta_name)
                if vals:
                    for v in vals:
                        if len(v) >= 16:
                            self.detected = v; self.source = f'meta:{meta_name}'; return v
            markers = ['sitekey=', 'siteKey=', 'SITE_KEY=', 'hcaptchaSiteKey']
            for m in markers:
                idx = 0
                while True:
                    i = html.find(m, idx)
                    if i < 0: break
                    j = i + len(m)
                    if j < len(html) and html[j] in ('"', "'"):
                        q = html[j]
                        k = html.find(q, j + 1)
                        if k > 0:
                            v = html[j + 1:k]
                            if 16 <= len(v) <= 60 and '/' not in v and ' ' not in v:
                                self.detected = v; self.source = f'script:{m}'; return v
                    idx = i + len(m)

        self.detected = HCAPTCHA_SITEKEY_DEFAULT
        self.source = 'default'
        return self.detected

class WaryonoSolver:
    def __init__(self, apikey, sitekey=None):
        self.apikey  = apikey or ''
        self.sitekey = sitekey or HCAPTCHA_SITEKEY_DEFAULT
        self.pageurl = BASE_URL

    def solve(self, max_retry=2):
        if not self.apikey:
            print(f" {Col.RED}✗{Col.R} Waryono apikey kosong"); return None
        for attempt in range(1, max_retry + 1):
            print(f" {Col.NEON_C}[TRY {attempt}/{max_retry}]{Col.R} Waryono solve...")
            tok, err_type = self._solve_once()
            if tok and isinstance(tok, str) and not tok.startswith('RETRY'):
                return tok
            if err_type == 'FATAL_KEY':
                print(f" {Col.RED}✗{Col.R} API key SALAH. Update di config."); return None
            if err_type == 'FATAL_BALANCE':
                print(f" {Col.RED}✗{Col.R} SALDO Waryono HABIS. Top-up dulu."); return None
            if err_type == 'RETRY':
                time.sleep(4 * attempt); continue
            if attempt < max_retry: time.sleep(2 * attempt)
        return None

    def _solve_once(self):
        payload = {"apikey": self.apikey, "methods": "hcaptcha",
                   "domain": self.pageurl, "sitekey": self.sitekey, "json": 1}
        raw = _post_json(WARYONO_IN, payload)
        print(f" {Col.DIM_C}→ POST in.php{Col.R}")

        try: j = json.loads(raw)
        except Exception:
            print(f" {Col.RED}✗{Col.R} Response bukan JSON: {raw[:100]}"); return None, 'ERROR'

        if '_http_error' in j:
            code = j['_http_error']; body = j.get('_body',''); reason = j.get('_reason','')
            if code == 402:
                print(f" {Col.RED}✗{Col.R} Waryono HTTP 402: Payment Required (saldo habis)")
                if body: print(f" {Col.DIM_C}  body: {body[:120]}{Col.R}")
                return None, 'FATAL_BALANCE'
            if code in (401, 403):
                print(f" {Col.RED}✗{Col.R} Waryono HTTP {code}: API key salah"); return None, 'FATAL_KEY'
            print(f" {Col.RED}✗{Col.R} Waryono HTTP {code}: {reason[:80]}"); return None, 'ERROR'

        if '_error' in j:
            print(f" {Col.RED}✗{Col.R} Network: {j['_error'][:80]}"); return None, 'RETRY'

        status = j.get('status'); req_msg = str(j.get('request', ''))

        if status == 1 and req_msg:
            tid = req_msg
        else:
            if 'ERROR_WRONG_USER_KEY' in req_msg or 'ERROR_KEY_DOES_NOT_EXIST' in req_msg:
                print(f" {Col.RED}✗{Col.R} {req_msg}"); return None, 'FATAL_KEY'
            if 'ERROR_ZERO_BALANCE' in req_msg:
                print(f" {Col.RED}✗{Col.R} {req_msg}"); return None, 'FATAL_BALANCE'
            if 'ERROR_IP_NOT_ALLOWED' in req_msg:
                print(f" {Col.RED}✗{Col.R} {req_msg}"); return None, 'FATAL_KEY'
            if 'ERROR_TOO_MANY_REQUESTS' in req_msg:
                print(f" {Col.YEL}!{Col.R} {req_msg} → tunggu 30s"); time.sleep(30)
                return None, 'RETRY'
            print(f" {Col.RED}✗{Col.R} Submit resp: {req_msg[:100]}"); return None, 'ERROR'

        print(f" {Col.NEON_G}✓{Col.R} Task ID: {Col.WHT}{tid}{Col.R}")

        elapsed = 0; last_print = -1
        while elapsed < CAPTCHA_TIMEOUT:
            time.sleep(CAPTCHA_POLL_DELAY); elapsed += CAPTCHA_POLL_DELAY
            if elapsed != last_print:
                filled = int(elapsed / CAPTCHA_TIMEOUT * 20)
                bar = f"{Col.NEON_G}{'█'*filled}{Col.DIM_C}{'░'*(20-filled)}{Col.R}"
                sys.stdout.write(f"\r {Col.NEON_Y}[WAIT]{Col.R} {Col.WHT}{elapsed}s{Col.R} [{bar}]   ")
                sys.stdout.flush(); last_print = elapsed

            url = f"{WARYONO_RES}?apikey={urllib.parse.quote(self.apikey)}&action=get&id={urllib.parse.quote(str(tid))}&json=1"
            raw = _get(url)
            try: pj = json.loads(raw)
            except Exception: continue

            if '_http_error' in pj:
                code = pj['_http_error']
                if code == 402:
                    sys.stdout.write("\r" + " "*70 + "\r")
                    print(f" {Col.RED}✗{Col.R} Poll HTTP 402 (saldo habis)")
                    return None, 'FATAL_BALANCE'
                continue
            if '_error' in pj: continue

            if pj.get('status') == 1:
                token = pj.get('request', '')
                sys.stdout.write("\r" + " "*70 + "\r")
                print(f" {Col.NEON_G}✓{Col.R} Solved ({elapsed}s)")
                return token, None

            rs = str(pj.get('request', ''))
            if 'CAPCHA_NOT_READY' in rs: continue
            if 'ERROR_CAPTCHA_UNSOLVABLE' in rs or 'UNSOLVABLE' in rs:
                sys.stdout.write("\r" + " "*70 + "\r")
                print(f" {Col.YEL}!{Col.R} UNSOLVABLE → retry"); return None, 'RETRY'
            if 'ERROR_ZERO_BALANCE' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'FATAL_BALANCE'
            if 'ERROR_WRONG_USER_KEY' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'FATAL_KEY'
            if 'ERROR_TOO_MANY_REQUESTS' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); time.sleep(30); return None, 'RETRY'
            if 'ERROR' in rs:
                sys.stdout.write("\r" + " "*70 + "\r")
                print(f" {Col.RED}✗{Col.R} Poll: {rs}"); return None, 'ERROR'

        sys.stdout.write("\r" + " "*70 + "\r")
        print(f" {Col.YEL}!{Col.R} Timeout"); return None, 'RETRY'

    def test_apikey(self):
        payload = {"apikey": self.apikey, "methods": "hcaptcha",
                   "domain": self.pageurl, "sitekey": self.sitekey, "json": 1}
        raw = _post_json(WARYONO_IN, payload)
        try: j = json.loads(raw)
        except Exception: return False, "Response tidak valid"
        if '_http_error' in j:
            code = j['_http_error']
            if code == 402: return False, "SALDO HABIS (HTTP 402)"
            if code in (401, 403): return False, f"API key SALAH (HTTP {code})"
            return False, f"HTTP {code}"
        if '_error' in j: return False, j['_error']
        req = str(j.get('request', ''))
        if 'ERROR_WRONG_USER_KEY' in req: return False, "API key SALAH"
        if 'ERROR_ZERO_BALANCE' in req: return False, "SALDO HABIS"
        if j.get('status') == 1: return True, f"OK (test task: {req})"
        return False, req or "Unknown error"

class LiteBitsBot:
    def __init__(self):
        self.session = None
        self.init_data = ''
        self.auth_token = ''
        self.bot_username = DEFAULT_BOT
        self.referral_code = DEFAULT_REFERRAL
        self.user_agent = DEFAULT_UA
        self.captcha_apikey = ''
        self.hcaptcha_sitekey = HCAPTCHA_SITEKEY_DEFAULT
        self.sitekey_source = 'default'
        self.mode = 'no_hcaptcha'
        self.session_earned = 0.0
        self.cycles = 0
        self.cycles_failed = 0
        self.user_info = {}
        self.cooldown_seconds = DEFAULT_COOLDOWN
        self.cooldown_left = 0
        self.cooldown_total = 0
        self.captcha_solved = 0
        self.captcha_failed = 0
        self.running = True
        self.claim_state = 'IDLE'
        self.start_time = time.time()
        self.balance_history = deque(maxlen=30)
        self.last_claim_time = None
        self.streak = 0
        self.cycle_logs = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, CONFIG_FILE)
        self.tg_session_path = os.path.join(self.base_dir, SESSION_FILE)

    def has_telethon_session(self):
        p = self.tg_session_path + '.session'
        return os.path.exists(p) and os.path.getsize(p) > 0

    def sparkline(self, values, width=30):
        if not values or len(values) < 2: return f"{Col.DIM_C}{'·'*width}{Col.R}"
        blocks = "▁▂▃▄▅▆▇█"
        vmin = min(values); vmax = max(values)
        span = vmax - vmin if vmax > vmin else 1
        vals = list(values)
        if len(vals) > width:
            step = len(vals) / width
            vals = [vals[int(i*step)] for i in range(width)]
        elif len(vals) < width:
            vals = [vmin] * (width - len(vals)) + vals
        out = ""
        for v in vals:
            idx = max(0, min(7, int((v - vmin) / span * 7)))
            c = Col.NEON_G if idx>=6 else Col.NEON_C if idx>=4 else Col.NEON_Y if idx>=2 else Col.NEON_O
            out += f"{c}{blocks[idx]}{Col.R}"
        return out

    def _bar(self, remaining, total, width=20):
        if total <= 0: total = 1
        filled = max(0, min(width, int((total - remaining) / total * width)))
        return f"{Col.NEON_G}{'█'*filled}{Col.DIM_C}{'░'*(width-filled)}{Col.R}"

    def _progress_wait(self, seconds, label="WAIT", total=None):
        total = total or seconds
        self.claim_state = label
        for left in range(seconds, 0, -1):
            if not self.running: break
            self.cooldown_left = left; self.cooldown_total = total
            bar = self._bar(left, total)
            mm, ss = divmod(left, 60); hh, mm = divmod(mm, 60)
            line = f" {Col.NEON_Y}[⏳ {label}]{Col.R} {Col.WHT}{hh:02d}:{mm:02d}:{ss:02d}{Col.R} [{bar}]"
            self.render_view(live_line=line)
            time.sleep(1)
        self.cooldown_left = 0; self.claim_state = 'IDLE'

    def render_dashboard(self):
        name = str(self.user_info.get('telegramUsername') or self.user_info.get('username')
                   or self.user_info.get('first_name') or 'User')
        if not name.startswith('@') and (self.user_info.get('telegramUsername')
                                          or self.user_info.get('username')):
            name = '@' + name
        try: bal_str = f"{float(str(self.user_info.get('balance', '0'))):.2f} Coins"
        except Exception: bal_str = f"{self.user_info.get('balance', '0.00')} Coins"
        earned_str = f"+{self.session_earned:.2f} Coins"
        total_cyc = self.cycles + self.cycles_failed
        rate = (self.cycles / total_cyc * 100) if total_cyc > 0 else 100.0
        elapsed = int(time.time() - self.start_time)
        remaining = max(0, MAX_RUNTIME - elapsed)
        eh, er = divmod(elapsed, 3600); em, es = divmod(er, 60)
        rh, rr = divmod(remaining, 3600); rm, rs = divmod(rr, 60)
        mode_c = Col.NEON_R if self.mode == 'hcaptcha' else Col.NEON_G
        mode_s = f"{mode_c}{self.mode.upper()}{Col.R}"

        print(f"{Col.NEON_C}┌─ {Col.NEON_Y}ACCOUNT{Col.NEON_C} " + "─"*49 + f"┐{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}User{Col.R}      : {Col.NEON_C}{name:<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Balance{Col.R}   : {Col.NEON_Y}{bal_str:<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Earned{Col.R}    : {Col.NEON_G}{earned_str:<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Mode{Col.R}      : {mode_s:<51}{Col.NEON_C}│{Col.R}")
        if self.mode == 'hcaptcha':
            sk = self.hcaptcha_sitekey[:20] + '...' if len(self.hcaptcha_sitekey) > 20 else self.hcaptcha_sitekey
            print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Sitekey{Col.R}   : {Col.DIM_C}{sk:<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Cycles{Col.R}    : {Col.WHT}{str(self.cycles):<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Success{Col.R}   : {Col.NEON_G if rate >= 90 else Col.NEON_Y}{f'{rate:.1f}%':<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Captcha{Col.R}   : {Col.NEON_G}{f'{self.captcha_solved} solved / {self.captcha_failed} failed':<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Uptime{Col.R}    : {Col.NEON_C}{f'{eh:02d}:{em:02d}:{es:02d}':<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Remaining{Col.R} : {Col.NEON_O}{f'{rh:02d}:{rm:02d}:{rs:02d}':<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}└" + "─"*60 + f"┘{Col.R}")
        if len(self.balance_history) >= 2:
            spark = self.sparkline(list(self.balance_history), 50)
            try:
                cur = float(self.balance_history[-1]); prev = float(self.balance_history[0])
                delta = cur - prev
                dc = Col.NEON_G if delta >= 0 else Col.NEON_R
                ds = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
            except Exception: ds = "?"; dc = Col.WHT
            print(f"{Col.NEON_C}┌─ {Col.NEON_Y}BALANCE TREND{Col.NEON_C} " + "─"*43 + f"┐{Col.R}")
            print(f"{Col.NEON_C}│{Col.R} {spark}  {dc}{ds:>8}{Col.R} {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}└" + "─"*60 + f"┘{Col.R}")
        print()

    def render_banner(self):
        mode_c = Col.NEON_R if self.mode == 'hcaptcha' else Col.NEON_G
        return f"""
{Col.NEON_C}=============================================================={Col.R}
{Col.NEON_Y}                    ⚡ {Col.NEON_G}LITEBITS{Col.NEON_Y} ⚡{Col.R}
{Col.NEON_C}                 {Col.WHT}AUTO CLAIM SYSTEM v3.9.1{Col.R}
{Col.NEON_C}=============================================================={Col.R}
{Col.NEON_V} Bot         : {Col.NEON_C}@{self.bot_username}{Col.R}
{Col.NEON_V} Referral    : {Col.NEON_Y}{self.referral_code}{Col.R}
{Col.NEON_V} Mode        : {mode_c}{self.mode.upper()}{Col.R}
{Col.NEON_V} API Key     : {Col.DIM_C}{(self.captcha_apikey[:10] + '...') if self.captcha_apikey else '(kosong)'}{Col.R}
{Col.NEON_V} Sitekey src : {Col.DIM_C}{self.sitekey_source}{Col.R}
{Col.NEON_V} Auto-stop   : {Col.NEON_O}{MAX_RUNTIME // 3600} hours{Col.R}
{Col.NEON_V} Status      : {Col.NEON_G}● ONLINE{Col.R}
{Col.NEON_C}=============================================================={Col.R}
"""

    def render_view(self, live_line=None):
        clear()
        print(self.render_banner())
        self.render_dashboard()
        print(f"{Col.NEON_C}========================= {Col.NEON_Y}LIVE LOGS{Col.NEON_C} ==========================={Col.R}")
        print()
        for entry in self.cycle_logs[-12:]: print(entry)
        print()
        if live_line:
            print(live_line); print()
        runtime = int(time.time() - self.start_time)
        h, r = divmod(runtime, 3600); m, s = divmod(r, 60)
        status = f"{Col.NEON_G}● RUNNING" if self.running else f"{Col.NEON_R}● STOPPED"
        print(f"{Col.NEON_C}=============================================================={Col.R}")
        print(f"{Col.NEON_V} STATUS : {status}{Col.R}   {Col.DIM_C}| Uptime: {h:02d}:{m:02d}:{s:02d}{Col.R}   {Col.DIM_C}| PID: {os.getpid()}{Col.R}")
        print(f"{Col.NEON_C}=============================================================={Col.R}")

    def add_log(self, level, msg):
        icons = {'ok': f"{Col.NEON_G}✓{Col.R}", 'err': f"{Col.RED}✗{Col.R}",
                 'info': f"{Col.NEON_C}•{Col.R}", 'wait': f"{Col.NEON_Y}⏳{Col.R}",
                 'warn': f"{Col.NEON_O}!{Col.R}", 'star': f"{Col.NEON_P}★{Col.R}",
                 'bal': f"{Col.NEON_Y}💰{Col.R}", 'cycle': f"{Col.NEON_V}🔄{Col.R}",
                 'net': f"{Col.NEON_C}🌐{Col.R}", 'cap': f"{Col.NEON_Y}[C]{Col.R}"}
        ts = datetime.now().strftime("%H:%M:%S")
        self.cycle_logs.append(f"{Col.DIM_C}[{ts}]{Col.R} {icons.get(level, f'{Col.NEON_C}·{Col.R}')} {Col.WHT}{msg}{Col.R}")
        self.render_view()

    def init_http_session(self):
        try:
            from curl_cffi import requests as cr
            self.session = cr.Session(impersonate="chrome120")
        except ImportError:
            try:
                import cloudscraper
                self.session = cloudscraper.create_scraper()
            except ImportError:
                import requests
                self.session = requests.Session()
        self.apply_headers()

    def apply_headers(self):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/?v3',
            'x-platform': 'telegram',
            'x-requested-with': 'org.telegram.messenger.web',
            'sec-ch-ua': '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
        }
        if self.auth_token: headers['Authorization'] = f"Bearer {self.auth_token}"
        if self.init_data:  headers['x-telegram-init-data'] = self.init_data
        if hasattr(self.session, 'headers'): self.session.headers.update(headers)

    def load_config(self):
        if not os.path.exists(self.config_path): return False
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                c = json.load(f)
            self.init_data      = c.get('init_data', '') or ''
            self.auth_token     = c.get('auth_token', '') or ''
            self.bot_username   = c.get('bot_username', DEFAULT_BOT)
            self.referral_code  = c.get('referral_code', DEFAULT_REFERRAL)
            self.captcha_apikey = c.get('captcha_apikey', '')
            self.user_agent     = c.get('user_agent', DEFAULT_UA)
            self.mode           = c.get('mode', 'no_hcaptcha')
            self.hcaptcha_sitekey = c.get('hcaptcha_sitekey', HCAPTCHA_SITEKEY_DEFAULT)
            self.sitekey_source = c.get('sitekey_source', 'default')
            self.session_earned = float(c.get('total_earned', 0) or 0)
            self.cycles         = int(c.get('total_cycles', 0) or 0)
            self.cycles_failed  = int(c.get('total_failed', 0) or 0)
            self.captcha_solved = int(c.get('captcha_solved', 0) or 0)
            self.captcha_failed = int(c.get('captcha_failed', 0) or 0)
            self.user_info      = c.get('user_info', {}) or {}
            return True
        except Exception:
            return False

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'init_data': self.init_data, 'auth_token': self.auth_token,
                    'bot_username': self.bot_username, 'referral_code': self.referral_code,
                    'captcha_apikey': self.captcha_apikey, 'user_agent': self.user_agent,
                    'mode': self.mode, 'hcaptcha_sitekey': self.hcaptcha_sitekey,
                    'sitekey_source': self.sitekey_source,
                    'total_earned': round(self.session_earned, 4),
                    'total_cycles': self.cycles, 'total_failed': self.cycles_failed,
                    'captcha_solved': self.captcha_solved, 'captcha_failed': self.captcha_failed,
                    'user_info': self.user_info,
                    'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }, f, indent=2)
        except Exception: pass

    def validate_telegram_auth(self):
        if not self.init_data: return False
        try:
            r = self.session.post(f"{BASE_URL}/api/auth/telegram/validate",
                json={'initData': self.init_data, 'referralCode': self.referral_code}, timeout=12)
            if r.status_code == 200:
                d = r.json()
                if d.get('success'):
                    self.auth_token = d.get('token', '')
                    if d.get('user'): self.user_info.update(d['user'])
                    self.apply_headers(); self.save_config()
                    return True
        except Exception: pass
        return False

    def fetch_app_settings(self):
        try:
            r = self.session.get(f"{BASE_URL}/api/app-settings", timeout=12)
            if r.status_code == 200:
                d = r.json()
                self.cooldown_seconds = max(60, int(float(d.get('claimInterval', 0.0825)) * 3600))
                return True
        except Exception: pass
        return False

    def fetch_user_profile(self):
        if not self.auth_token and not self.validate_telegram_auth(): return False
        try:
            r = self.session.get(f"{BASE_URL}/api/user/profile", timeout=12)
            if r.status_code == 200:
                d = r.json()
                if 'balance' in d or 'email' in d:
                    self.user_info.update(d)
                    try:
                        bal = float(str(d.get('balance', 0)))
                        self.balance_history.append(bal)
                    except Exception: pass
                    return True
            elif r.status_code == 401:
                if self.validate_telegram_auth():
                    r2 = self.session.get(f"{BASE_URL}/api/user/profile", timeout=12)
                    if r2.status_code == 200:
                        self.user_info.update(r2.json()); return True
        except Exception: pass
        return bool(self.user_info)

    def get_server_cooldown_left(self):
        nca = self.user_info.get('nextClaimAt')
        if nca:
            try:
                nca_dt = datetime.fromisoformat(nca.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                return max(0, int((nca_dt - now).total_seconds()))
            except Exception: pass
        lc = self.user_info.get('lastClaim')
        if not lc: return 0
        try:
            ld = datetime.fromisoformat(lc.replace('Z', '+00:00'))
            return max(0, self.cooldown_seconds - int((datetime.now(timezone.utc) - ld).total_seconds()))
        except Exception: return 0

    def detect_sitekey(self, force=False):
        if not force and self.hcaptcha_sitekey and self.hcaptcha_sitekey != HCAPTCHA_SITEKEY_DEFAULT:
            return self.hcaptcha_sitekey
        detector = SitekeyDetector(self.session, BASE_URL)
        sk = detector.detect()
        self.hcaptcha_sitekey = sk
        self.sitekey_source = detector.source
        self.save_config()
        return sk

    async def extract_init_data_async(self, interactive=True):
        if not HAS_TELETHON:
            if interactive: print(f"\n {Col.RED}✗ Telethon not found. pip install telethon{Col.R}\n")
            return None
        client = TelegramClient(self.tg_session_path, API_ID, API_HASH)
        if interactive:
            clear(); print()
            Anim.typewriter(f"{Col.NEON_C}╔════════════════════════════════════════════════════════════╗", 0.001)
            Anim.typewriter(f"{Col.NEON_C}║{Col.R}          ⚡ {Col.NEON_Y}LITEBITS SECURE LOGIN v3.9.1{Col.NEON_Y} ⚡{Col.R}          {Col.NEON_C}║", 0.001)
            Anim.typewriter(f"{Col.NEON_C}╚════════════════════════════════════════════════════════════╝", 0.001)
            print()
            Anim.scan("Scanning secure environment", 1.5)
            Anim.progress("Loading Telegram API", 1.0)
            print()
            def get_phone():
                print(f"{Col.NEON_Y}  📱 STEP 1/3 · PHONE{Col.R}")
                p = input(f" {Col.NEON_G}➜{Col.R} {Col.WHT}Phone (+62...){Col.NEON_C} »{Col.R} ").strip()
                print(); Anim.dots("Sending login code", 1.5); print()
                return p
            def get_code():
                print(f"{Col.NEON_Y}  🔐 STEP 2/3 · OTP{Col.R}")
                c = input(f" {Col.NEON_G}➜{Col.R} {Col.WHT}OTP Code{Col.NEON_C} »{Col.R} ").strip()
                print(); Anim.dots("Verifying OTP", 1.5); print()
                return c
            def get_password():
                print(f"{Col.NEON_Y}  🔒 STEP 3/3 · 2FA (kosongin kalau gak ada){Col.R}")
                pw = input(f" {Col.NEON_G}➜{Col.R} {Col.WHT}2FA Password{Col.NEON_C} »{Col.R} ").strip()
                print(); Anim.dots("Authenticating 2FA", 1.5); print()
                return pw
            try:
                await client.start(phone=get_phone, code_callback=get_code, password=get_password)
            except Exception as e:
                print(f" {Col.RED}✗ Login: {e}{Col.R}")
                try: await client.disconnect()
                except Exception: pass
                return None
        else:
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect(); return None
            except Exception:
                try: await client.disconnect()
                except Exception: pass
                return None
        if interactive:
            print()
            Anim.progress("Establishing session", 1.5)
            Anim.scan(f"Connecting to @{self.bot_username}", 1.5)
            print()
        else:
            print(f" {Col.NEON_C}•{Col.R} {Col.WHT}Refreshing init_data via saved session...{Col.R}")
        init_data = None
        try:
            bot = await client.get_input_entity(self.bot_username)
            if interactive:
                try: await client.send_message(bot, f'/start {self.referral_code}')
                except Exception: pass
            try:
                res_app = await client(functions.messages.RequestAppWebViewRequest(
                    peer=bot, app=types.InputBotAppShortName(bot_id=bot, short_name='app'),
                    platform='android', write_allowed=True, start_param=self.referral_code))
                if res_app and hasattr(res_app, 'url'):
                    parsed = urllib.parse.urlparse(res_app.url)
                    params = urllib.parse.parse_qs(parsed.fragment or parsed.query)
                    init_data = params.get('tgWebAppData', [None])[0]
            except Exception: pass
            if not init_data:
                full_user = await client(functions.users.GetFullUserRequest(id=bot))
                bot_info = full_user.full_user.bot_info
                menu_url = (bot_info.menu_button.url
                            if bot_info and bot_info.menu_button and hasattr(bot_info.menu_button, 'url')
                            else f'{BASE_URL}/?v3&startapp={self.referral_code}')
                res_menu = await client(functions.messages.RequestWebViewRequest(
                    peer=bot, bot=bot, platform='android', from_bot_menu=True, url=menu_url))
                if res_menu and hasattr(res_menu, 'url'):
                    parsed = urllib.parse.urlparse(res_menu.url)
                    params = urllib.parse.parse_qs(parsed.fragment or parsed.query)
                    init_data = params.get('tgWebAppData', [None])[0]
            if init_data and interactive:
                Anim.progress("Extracting token", 1.2)
                print(f"\n {Col.NEON_G}✓{Col.R} Session token acquired! ({len(init_data)} chars)\n")
            return init_data
        except Exception: return None
        finally:
            try: await client.disconnect()
            except Exception: pass

    def do_telegram_login(self, interactive=True):
        try:
            token = asyncio.run(self.extract_init_data_async(interactive=interactive))
            if token:
                self.init_data = token; self.save_config()
                if interactive: Anim.spinner("Saving session", 1.0); time.sleep(0.5)
                return True
            return False
        except Exception as e:
            if interactive: print(f" {Col.RED}✗ Telegram error: {e}{Col.R}")
            return False

    def setup_interactive(self):
        Anim.opening_sequence()
        self.load_config()
        self.fetch_app_settings()

        valid_auth = False
        if self.init_data:
            Anim.scan("Validating saved init_data", 1.5)
            if self.validate_telegram_auth(): valid_auth = True
        if not valid_auth and self.has_telethon_session():
            print()
            print(f" {Col.NEON_Y}!{Col.R} {Col.WHT}init_data expired. Refreshing via Telethon session...{Col.R}")
            if self.do_telegram_login(interactive=False) and self.validate_telegram_auth():
                valid_auth = True
                print(f" {Col.NEON_G}✓{Col.R} {Col.WHT}Auto-refreshed!{Col.R}\n")

        print(f" {Col.NEON_C}•{Col.R} Detecting hCaptcha sitekey...")
        sk = self.detect_sitekey(force=True)
        print(f" {Col.NEON_G}✓{Col.R} Sitekey: {Col.WHT}{sk}{Col.R} {Col.DIM_C}(source: {self.sitekey_source}){Col.R}")
        print()

        if valid_auth:
            name = self.user_info.get('telegramUsername') or self.user_info.get('username') or 'User'
            try: bal_str = f"{float(str(self.user_info.get('balance', 0))):.2f}"
            except Exception: bal_str = str(self.user_info.get('balance', '0.00'))
            print()
            print(f" {Col.NEON_G}✓{Col.R} Active session: {Col.NEON_C}@{name}{Col.R}")
            print(f" {Col.NEON_Y}💰{Col.R} Balance: {Col.NEON_Y}{bal_str} Coins{Col.R}")
            print(f" {Col.NEON_V}🎮{Col.R} Current mode: {Col.NEON_Y}{self.mode.upper()}{Col.R}")
            print()

            print(f"{Col.NEON_C}┌─ {Col.NEON_Y}SELECT MODE{Col.NEON_C} " + "─"*46 + f"┐{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_G}[1]{Col.R} {Col.WHT}No Hcaptcha {Col.DIM_C}(claim kosong){Col.R}              {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_Y}[2]{Col.R} {Col.WHT}Hcaptcha    {Col.DIM_C}(solve captcha dulu){Col.R}        {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}├" + "─"*60 + f"┤{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_C}[3]{Col.R} {Col.WHT}Re-login Telegram Phone{Col.R}                        {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_V}[4]{Col.R} {Col.WHT}Ganti Waryono API Key{Col.R}                          {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_O}[5]{Col.R} {Col.WHT}Force refresh init_data{Col.R}                        {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_P}[6]{Col.R} {Col.WHT}Re-detect sitekey{Col.R}                              {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_G}[7]{Col.R} {Col.WHT}Test Waryono API Key{Col.R}                          {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}└" + "─"*60 + f"┘{Col.R}")
            ch = input(f"\n{Col.WHT} ➜ Pilih [1-7] (default: current mode): {Col.NEON_G}").strip()
            print(Col.R, end='')
        else:
            print()
            print(f" {Col.NEON_Y}!{Col.R} {Col.WHT}First time — login required.{Col.R}\n")
            ch = '3'

        if ch == '1':
            self.mode = 'no_hcaptcha'; self.save_config()
            Anim.spinner("Mode set: NO HCAPTCHA", 1.0)
        elif ch == '2':
            self.mode = 'hcaptcha'; self.save_config()
            Anim.spinner("Mode set: HCAPTCHA", 1.0)
            if not self.captcha_apikey:
                print()
                key = input(f" {Col.NEON_G}➜{Col.R} {Col.WHT}Waryono API Key{Col.NEON_C} »{Col.R} ").strip()
                print(Col.R, end='')
                if key:
                    self.captcha_apikey = key; self.save_config()
                    Anim.spinner("API key saved", 1.0)
        elif ch == '3':
            if not self.do_telegram_login(interactive=True): return False
            self.validate_telegram_auth()
        elif ch == '4':
            nk = input(f" {Col.WHT}Waryono API Key baru: {Col.NEON_G}").strip()
            print(Col.R, end='')
            if nk:
                self.captcha_apikey = nk; self.save_config()
                Anim.spinner("API key updated", 1.0)
        elif ch == '5':
            if not self.has_telethon_session():
                print(f" {Col.RED}✗{Col.R} session gak ada, pilih [3]."); return False
            if self.do_telegram_login(interactive=False) and self.validate_telegram_auth():
                print(f" {Col.NEON_G}✓{Col.R} refreshed")
            else:
                print(f" {Col.RED}✗{Col.R} refresh gagal."); return False
        elif ch == '6':
            print(f" {Col.NEON_C}•{Col.R} Re-detecting sitekey...")
            sk = self.detect_sitekey(force=True)
            print(f" {Col.NEON_G}✓{Col.R} Sitekey: {Col.WHT}{sk}{Col.R} {Col.DIM_C}(source: {self.sitekey_source}){Col.R}")
        elif ch == '7':
            if not self.captcha_apikey:
                print(f" {Col.RED}✗{Col.R} API key belum di-set. Set dulu via menu [4].")
            else:
                print(f" {Col.NEON_C}•{Col.R} Testing Waryono API key...")
                print(f" {Col.DIM_C}  key: {self.captcha_apikey[:8]}...{self.captcha_apikey[-4:] if len(self.captcha_apikey) > 12 else ''}{Col.R}")
                print(f" {Col.DIM_C}  sitekey: {self.hcaptcha_sitekey}{Col.R}")
                solver = WaryonoSolver(self.captcha_apikey, self.hcaptcha_sitekey)
                ok, msg = solver.test_apikey()
                if ok: print(f" {Col.NEON_G}✓{Col.R} Waryono: {msg}")
                else: print(f" {Col.RED}✗{Col.R} Waryono: {msg}")

        return True

    def do_claim_flow(self):
        self.add_log('info', f"Mode: {Col.NEON_Y}{self.mode}{Col.R}")
        self.add_log('info', f"Holding button {Col.NEON_Y}({HOLD_DURATION}s){Col.R}...")
        self._progress_wait(HOLD_DURATION, label="HOLD")

        captcha_token = ""
        if self.mode == 'hcaptcha':
            self.claim_state = 'SOLVING'
            self.add_log('cap', f"Solving hCaptcha via Waryono (sitekey: {self.hcaptcha_sitekey[:20]}...)")
            solver = WaryonoSolver(self.captcha_apikey, self.hcaptcha_sitekey)
            tok = solver.solve()
            if not tok:
                self.captcha_failed += 1
                self.add_log('err', "Solver FAILED")
                self.cycles_failed += 1; self.save_config()
                return False, 'captcha_failed'
            captcha_token = tok
            self.captcha_solved += 1; self.save_config()
            self.add_log('ok', f"Token: {tok[:24]}...")
        else:
            self.add_log('info', "No hcaptcha mode — using empty token")

        start_payload = {
            "h-captcha-response": captcha_token,
            "captchaProvider": "hcaptcha",
            "tapTimings": [],
            "fingerprint": ""
        }
        self.add_log('net', "POST /api/claim/start...")

        try:
            r = self.session.post(f"{BASE_URL}/api/claim/start", json=start_payload, timeout=20)
            sd = r.json()
        except Exception as e:
            self.add_log('err', f"Net: {e}")
            self.cycles_failed += 1; self.save_config()
            return False, str(e)

        self.add_log('info', f"Start resp: {str(sd)[:140]}")

        if not sd.get('success'):
            rt = sd.get('retryInSeconds') or sd.get('retryAfterSeconds')
            if rt:
                self.add_log('wait', f"Server cooldown: {Col.NEON_Y}{rt}s{Col.R}")
                return True, int(rt)
            msg = sd.get('message', 'Claim rejected')
            self.add_log('err', f"Server: {msg}")
            if self.mode == 'no_hcaptcha' and any(k in str(msg).lower() for k in ('captcha','verif','human')):
                self.add_log('warn', "Server minta captcha! Ganti ke mode [2] HCAPTCHA")
            self.cycles_failed += 1; self.save_config()
            return False, msg

        claim_id = sd.get('claimId')
        ad_info = sd.get('ad') or {}
        self.add_log('ok', f"claimId: {str(claim_id)[:13]}...")
        if ad_info.get('title'):
            self.add_log('info', f"Ad: {Col.DIM_C}{ad_info.get('title')}{Col.R}")

        ad_token = None
        try:
            r_ads = self.session.get(f"{BASE_URL}/api/claim/{claim_id}/ads", timeout=15)
            if r_ads.status_code == 200:
                aj = r_ads.json()
                if aj.get('success') and aj.get('adsUrl'):
                    ad_token = aj['adsUrl'].get('token')
        except Exception: pass

        self.claim_state = 'WATCHING'
        self.add_log('wait', f"Watching ad {Col.NEON_Y}({AD_VIEW_WAIT}s){Col.R}...")
        self._progress_wait(AD_VIEW_WAIT, label="AD")

        self.add_log('net', "POST /api/claim/{id}/complete...")
        complete_payload = {"token": ad_token or ""}

        self.claim_state = 'CLAIMING'
        amount = 1.0; ok = False
        try:
            r = self.session.post(f"{BASE_URL}/api/claim/{claim_id}/complete",
                                  json=complete_payload, timeout=20)
            cd = r.json()
            self.add_log('info', f"Complete: {str(cd)[:140]}")
            if cd.get('success'):
                ok = True
                amount = float(cd.get('reward', cd.get('amount', 1.0)))
        except Exception as e:
            self.add_log('err', f"Complete: {e}")

        if not ok:
            self.add_log('warn', "Claim unconfirmed")
            self.cycles_failed += 1; self.save_config()
            return False, 'unconfirmed'

        time.sleep(1)
        self.fetch_user_profile()
        try: self.session_earned += float(amount)
        except Exception: pass
        self.cycles += 1
        self.last_claim_time = datetime.now()
        if self.cycles % 10 == 0: self.streak += 1

        try: bal_str = f"{float(str(self.user_info.get('balance', 0))):.2f}"
        except Exception: bal_str = str(self.user_info.get('balance', '0.00'))

        print()
        print(f" {Col.NEON_G}╔══════════════════════════════════════════════════╗{Col.R}")
        print(f" {Col.NEON_G}║{Col.R}  {Col.NEON_G}[✓ SUCCESS]{Col.R} {Col.WHT}+{amount:.2f} Coins{Col.R}")
        print(f" {Col.NEON_G}║{Col.R}  {Col.NEON_Y}[✓ BALANCE]{Col.R} {Col.WHT}{bal_str} Coins{Col.R}")
        print(f" {Col.NEON_G}║{Col.R}  {Col.NEON_V}[✓ CYCLE]{Col.R}   {Col.WHT}#{self.cycles} COMPLETED{Col.R}")
        print(f" {Col.NEON_G}╚══════════════════════════════════════════════════╝{Col.R}")
        print()

        self.add_log('star', f"Reward {Col.NEON_G}+{amount:.2f} Coins{Col.R}")
        self.add_log('bal', f"Balance {Col.NEON_Y}{bal_str} Coins{Col.R}")
        self.add_log('cycle', f"Cycle {Col.NEON_V}#{self.cycles}{Col.R} done")
        self.save_config()
        time.sleep(1.5)
        return True, "Success"

    def live_cooldown(self, wait_seconds=None):
        if wait_seconds is not None:
            total_sec = int(wait_seconds)
        else:
            total_sec = self.get_server_cooldown_left() or self.cooldown_seconds
        total = total_sec
        while total_sec > 0 and self.running:
            if (time.time() - self.start_time) >= MAX_RUNTIME:
                self.add_log('warn', "Runtime limit, break cooldown.")
                self.running = False; break
            mm, ss = divmod(total_sec, 60); hh, mm = divmod(mm, 60)
            tstr = f"{hh:02d}:{mm:02d}:{ss:02d}"
            bar = self._bar(total_sec, total)
            self.render_view(live_line=f" {Col.NEON_Y}[⏳ WAIT]{Col.R} Cooldown {Col.WHT}{tstr}{Col.R}  [{bar}]")
            time.sleep(1); total_sec -= 1
        if self.running:
            self.render_view(live_line=f" {Col.NEON_G}[✓ READY]{Col.R} Cooldown finished.")
            time.sleep(1)

    def generate_report(self, reason="TIME LIMIT REACHED"):
        runtime = int(time.time() - self.start_time)
        h, r = divmod(runtime, 3600); m, s = divmod(r, 60)
        try:
            final_bal = float(str(self.user_info.get('balance', 0)))
            final_bal_str = f"{final_bal:.2f} Coins"
        except Exception:
            final_bal = 0.0; final_bal_str = "N/A"
        total_cyc = self.cycles + self.cycles_failed
        rate = (self.cycles / total_cyc * 100) if total_cyc > 0 else 0.0
        finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_str = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S")
        lines = ["",
            f"{Col.NEON_C}╔══════════════════════════════════════════════════════════════╗{Col.R}",
            f"{Col.NEON_C}║{Col.R}           {Col.NEON_Y}⚡ SESSION REPORT · LITEBITS v3.9.1 ⚡{Col.R}          {Col.NEON_C}║{Col.R}",
            f"{Col.NEON_C}╚══════════════════════════════════════════════════════════════╝{Col.R}",
            "",
            f"{Col.NEON_V}  Reason          : {Col.WHT}{reason}{Col.R}",
            f"{Col.NEON_V}  Mode            : {Col.NEON_Y}{self.mode.upper()}{Col.R}",
            f"{Col.NEON_V}  Sitekey source  : {Col.WHT}{self.sitekey_source}{Col.R}",
            f"{Col.NEON_V}  Started         : {Col.WHT}{start_str}{Col.R}",
            f"{Col.NEON_V}  Finished        : {Col.WHT}{finish_time}{Col.R}",
            f"{Col.NEON_V}  Runtime         : {Col.NEON_C}{h:02d}h {m:02d}m {s:02d}s{Col.R}",
            "",
            f"{Col.NEON_V}  Total Earned    : {Col.NEON_G}+{self.session_earned:.4f} Coins{Col.R}",
            f"{Col.NEON_V}  Final Balance   : {Col.NEON_Y}{final_bal_str}{Col.R}",
            f"{Col.NEON_V}  Cycles OK       : {Col.NEON_G}{self.cycles}{Col.R}",
            f"{Col.NEON_V}  Cycles Failed   : {Col.NEON_R}{self.cycles_failed}{Col.R}",
            f"{Col.NEON_V}  Success Rate    : {Col.NEON_G if rate >= 90 else Col.NEON_Y}{rate:.1f}%{Col.R}",
            f"{Col.NEON_V}  Captcha Solved  : {Col.NEON_G}{self.captcha_solved}{Col.R}",
            f"{Col.NEON_V}  Captcha Failed  : {Col.NEON_R}{self.captcha_failed}{Col.R}",
            "",
            f"{Col.NEON_C}══════════════════════════════════════════════════════════════{Col.R}",
            ""]
        for line in lines: print(line)
        plain = re.sub(r'\x1b\[[0-9;]*m', '', "\n".join(lines))
        try:
            with open(os.path.join(self.base_dir, REPORT_FILE), 'w', encoding='utf-8') as f:
                f.write(plain)
            print(f" {Col.NEON_G}✓{Col.R} Report: {REPORT_FILE}\n")
        except Exception: pass

    def run(self):
        self.init_http_session()
        if not self.setup_interactive(): sys.exit(1)

        stop_reason = "USER STOPPED"
        max_h = MAX_RUNTIME // 3600

        self.add_log('info', f"Auto-stop after {Col.NEON_Y}{max_h}h{Col.R}")
        self.add_log('info', f"Mode: {Col.NEON_Y}{self.mode}{Col.R}")
        self.add_log('info', f"Sitekey: {Col.DIM_C}{self.hcaptcha_sitekey[:24]}...{Col.R}")
        time.sleep(1)

        while self.running:
            try:
                elapsed = time.time() - self.start_time
                if elapsed >= MAX_RUNTIME:
                    stop_reason = f"TIME LIMIT ({max_h}H)"
                    self.add_log('warn', f"⏰ {max_h}h reached, stop...")
                    self.running = False; break

                self.fetch_user_profile()
                self.fetch_app_settings()

                time_left = self.get_server_cooldown_left()
                if time_left > 0:
                    if time_left > (MAX_RUNTIME - (time.time() - self.start_time)):
                        stop_reason = "TIME LIMIT DURING COOLDOWN"
                        self.running = False; break
                    self.cycle_logs.clear()
                    self.render_view()
                    self.live_cooldown(wait_seconds=time_left)
                    self.fetch_user_profile()

                self.cycle_logs.clear()
                self.render_view()

                ok, res = self.do_claim_flow()

                if isinstance(res, int) and res > 0:
                    elapsed_now = time.time() - self.start_time
                    if res > (MAX_RUNTIME - elapsed_now):
                        stop_reason = "TIME LIMIT DURING COOLDOWN"
                        self.running = False; break
                    self.live_cooldown(wait_seconds=res)
                    continue

                if not ok:
                    self.add_log('warn', "Retry in 30s...")
                    if (time.time() - self.start_time) >= MAX_RUNTIME:
                        stop_reason = f"TIME LIMIT ({max_h}H)"
                        self.running = False; break
                    self._progress_wait(30, label="RETRY")
                    continue

                self.live_cooldown()
            except KeyboardInterrupt:
                stop_reason = "USER STOPPED (Ctrl+C)"
                self.running = False; break
            except Exception as e:
                self.add_log('err', f"Loop: {e}")
                time.sleep(15)

        self.save_config()
        self.generate_report(reason=stop_reason)

if __name__ == '__main__':
    bot = LiteBitsBot()
    bot.run()
