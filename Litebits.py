#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LiteBits.io Auto Claim Bot v4.2.0 — NO ANIM · SAFE PHONE
- Waryono solver (in + res only)
- hCaptcha sitekey detection (unchanged)
- Telethon-only session (no initData paste, no manual menu)
- Silent auto-refresh via saved .session (no phone prompt after first login)
- Phone validation + retry loop + auto-normalize (08xx → +628xx)
- Realistic tap telemetry (anti-ban)
- sdk-frame + ads/outcome reporting
- Human timing
- nextClaimAt-driven cooldown
- NO ANIMATIONS
"""

import time, json, re, os, sys, random, base64, asyncio
import urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from collections import deque

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

class Col:
    R='\033[0m'; B='\033[1m'; D='\033[2m'
    RED='\033[91m'; GRN='\033[92m'; YEL='\033[93m'; BLU='\033[94m'
    MAG='\033[95m'; CYN='\033[96m'; WHT='\033[97m'; GRY='\033[90m'
    NEON_G='\033[38;5;46m'; NEON_C='\033[38;5;51m'; NEON_Y='\033[38;5;226m'
    NEON_P='\033[38;5;207m'; NEON_O='\033[38;5;208m'; NEON_V='\033[38;5;141m'
    NEON_R='\033[38;5;196m'; DIM_C='\033[38;5;244m'

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# ═══════════════════ CONSTANTS ═══════════════════
API_HASH   = 'fb06985ea797ac51aaa1e6d1168ceaaa'
API_ID     = 35898257
BASE_URL   = 'https://mini.litebits.io'
HCAPTCHA_SITEKEY_DEFAULT = '1c602a9a-f05a-403c-9306-cacc4c64e30a'
DEFAULT_BOT      = 'litebits_faucet_bot'
DEFAULT_REFERRAL = 'A7F2K9'
CONFIG_FILE      = 'litebits.json'
SESSION_FILE     = 'session_auth'
REPORT_FILE      = 'litebits_report.txt'

HOLD_MS_MIN      = 2200
HOLD_MS_MAX      = 4200
AD_WAIT_MIN      = 12
AD_WAIT_MAX      = 22
PRE_HUMAN_PAUSE  = (250, 1200)
POST_HUMAN_PAUSE = (150, 600)

DEFAULT_COOLDOWN = 300
MAX_RUNTIME      = 6 * 3600
CAPTCHA_TIMEOUT  = 180
CAPTCHA_POLL_DELAY = 3
WARYONO_IN       = 'https://api.waryono.my.id/in.php'
WARYONO_RES      = 'https://api.waryono.my.id/res.php'

DEFAULT_UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.8059.43 Mobile Safari/537.36 "
    "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

try:
    from telethon import TelegramClient, functions, types
    from telethon.errors import SessionPasswordNeededError
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

# ═══════════════════ HELPERS ═══════════════════
def _post_json(url, payload, timeout=30, ua='Mozilla/5.0 (Linux; Android 14; Mobile)'):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','User-Agent':ua,
                 'Accept':'application/json, text/plain, */*'})
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
        'User-Agent':'Mozilla/5.0 (Linux; Android 14; Mobile)',
        'Accept':'application/json, text/plain, */*'})
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.HTTPError as e:
        body = ''
        try: body = e.read().decode('utf-8', errors='ignore')
        except Exception: pass
        return json.dumps({"_http_error": e.code, "_body": body, "_reason": str(e.reason)})
    except Exception as e:
        return json.dumps({"_error": str(e)})

def jwt_exp(tok):
    try:
        parts = tok.split('.')
        if len(parts) != 3: return 0
        pad = '=' * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
        return int(payload.get('exp', 0))
    except Exception:
        return 0

def jwt_valid(tok, min_secs=600):
    return bool(tok) and jwt_exp(tok) > time.time() + min_secs

def normalize_phone(raw):
    """Normalize Indonesian/international phone numbers."""
    if not raw: return ""
    p = re.sub(r'[\s\-\(\)\.]', '', str(raw).strip())
    if not p: return ""
    if p.startswith('00'): p = '+' + p[2:]
    if not p.startswith('+'):
        if p.startswith('0'):    p = '+62' + p[1:]
        elif p.startswith('62'): p = '+' + p
        elif p.startswith('8'):  p = '+62' + p
        else:                    p = '+' + p
    return p

def is_valid_phone(p):
    if not p or not p.startswith('+'): return False
    digits = re.sub(r'\D', '', p)
    return 8 <= len(digits) <= 15

def extract_attr(html, attr_name, quote_chars='"\''):
    results = []
    if not html or not attr_name: return results
    search = attr_name + '='; idx = 0
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

# ═══════════════════ SITEKEY DETECTOR (UNCHANGED) ═══════════════════
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

# ═══════════════════ WARYONO SOLVER ═══════════════════
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
                print(f" {Col.RED}✗{Col.R} API key SALAH."); return None
            if err_type == 'FATAL_BALANCE':
                print(f" {Col.RED}✗{Col.R} SALDO Waryono HABIS."); return None
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
            print(f" {Col.RED}✗{Col.R} Response bukan JSON"); return None, 'ERROR'

        if '_http_error' in j:
            code = j['_http_error']
            if code == 402: return None, 'FATAL_BALANCE'
            if code in (401, 403): return None, 'FATAL_KEY'
            return None, 'ERROR'
        if '_error' in j: return None, 'RETRY'

        status = j.get('status'); req_msg = str(j.get('request', ''))
        if status == 1 and req_msg:
            tid = req_msg
        else:
            if 'ERROR_WRONG_USER_KEY' in req_msg or 'ERROR_KEY_DOES_NOT_EXIST' in req_msg:
                return None, 'FATAL_KEY'
            if 'ERROR_ZERO_BALANCE' in req_msg:
                return None, 'FATAL_BALANCE'
            if 'ERROR_TOO_MANY_REQUESTS' in req_msg:
                time.sleep(30); return None, 'RETRY'
            return None, 'ERROR'

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
                if pj['_http_error'] == 402:
                    sys.stdout.write("\r" + " "*70 + "\r"); return None, 'FATAL_BALANCE'
                continue
            if '_error' in pj: continue

            if pj.get('status') == 1:
                token = pj.get('request', '')
                sys.stdout.write("\r" + " "*70 + "\r")
                print(f" {Col.NEON_G}✓{Col.R} Solved ({elapsed}s)")
                return token, None

            rs = str(pj.get('request', ''))
            if 'CAPCHA_NOT_READY' in rs: continue
            if 'UNSOLVABLE' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'RETRY'
            if 'ERROR_ZERO_BALANCE' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'FATAL_BALANCE'
            if 'ERROR_WRONG_USER_KEY' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'FATAL_KEY'
            if 'ERROR' in rs:
                sys.stdout.write("\r" + " "*70 + "\r"); return None, 'ERROR'

        sys.stdout.write("\r" + " "*70 + "\r"); return None, 'RETRY'

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

# ═══════════════════ MAIN BOT ═══════════════════
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

    def _telethon_session_exists(self):
        p = self.tg_session_path + '.session'
        return os.path.exists(p) and os.path.getsize(p) > 0

    def _token_valid(self, min_secs=600):
        return jwt_valid(self.auth_token, min_secs)

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
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/?v5',
            'x-platform': 'telegram',
            'x-requested-with': 'org.telegram.messenger.web',
            'sec-ch-ua': '"Android WebView";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
        }
        if self.auth_token: headers['Authorization'] = f"Bearer {self.auth_token}"
        if self.init_data:  headers['x-telegram-init-data'] = self.init_data
        if hasattr(self.session, 'headers'): self.session.headers.update(headers)

    def _human_pause(self, rng=PRE_HUMAN_PAUSE):
        time.sleep(random.randint(rng[0], rng[1]) / 1000.0)

    def _profile_ok(self):
        try:
            r = self.session.get(f"{BASE_URL}/api/user/profile", timeout=12)
            if r.status_code == 200:
                d = r.json()
                if 'balance' in d or 'email' in d:
                    self.user_info.update(d)
                    try: self.balance_history.append(float(d.get('balance', 0) or 0))
                    except Exception: pass
                    return True
            return False
        except Exception:
            return False

    def fetch_user_profile(self):
        return self._profile_ok()

    def fetch_app_settings(self):
        try:
            r = self.session.get(f"{BASE_URL}/api/app-settings", timeout=12)
            if r.status_code == 200:
                d = r.json()
                self.cooldown_seconds = max(60, int(float(d.get('claimInterval', 0.0825)) * 3600))
                return True
        except Exception: pass
        return False

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

    def detect_sitekey(self, force=False):
        if not force and self.hcaptcha_sitekey and self.hcaptcha_sitekey != HCAPTCHA_SITEKEY_DEFAULT:
            return self.hcaptcha_sitekey
        detector = SitekeyDetector(self.session, BASE_URL)
        sk = detector.detect()
        self.hcaptcha_sitekey = sk
        self.sitekey_source = detector.source
        self.save_config()
        return sk

    # ═══════════════════ TELETHON CORE ═══════════════════
    def _ask_phone(self):
        """Prompt phone with validation + retry. Returns normalized phone or None."""
        for attempt in range(1, 6):
            try:
                raw = input(f" {Col.NEON_G}➜{Col.R} Phone (+62 atau 08xx): ").strip()
            except EOFError:
                print(f" {Col.RED}✗{Col.R} stdin closed."); return None
            if not raw:
                print(f" {Col.RED}✗{Col.R} Kosong. Coba lagi ({attempt}/5)."); continue
            phone = normalize_phone(raw)
            if not is_valid_phone(phone):
                print(f" {Col.RED}✗{Col.R} Format invalid: {phone}. Coba lagi ({attempt}/5)."); continue
            print(f" {Col.DIM_C}→ {phone}{Col.R}")
            return phone
        return None

    def _ask_code(self):
        for attempt in range(1, 6):
            try:
                c = input(f" {Col.NEON_G}➜{Col.R} OTP Code: ").strip().replace(' ', '').replace('-', '')
            except EOFError:
                return None
            if c: return c
            print(f" {Col.RED}✗{Col.R} OTP kosong. Coba lagi ({attempt}/5).")
        return None

    def _ask_password(self):
        try:
            return input(f" {Col.NEON_G}➜{Col.R} 2FA Password (kosong kalau gak ada): ").strip()
        except EOFError:
            return ""

    async def _telethon_get_initdata(self, interactive=False):
        if not HAS_TELETHON:
            if interactive: print(f"\n {Col.RED}✗ Telethon not installed. pip install telethon{Col.R}\n")
            return None

        try:
            client = TelegramClient(self.tg_session_path, API_ID, API_HASH)
        except Exception as e:
            if 'locked' in str(e).lower() or 'database is locked' in str(e).lower():
                print(f" {Col.RED}✗ Telethon session LOCKED — matikan proses lain.{Col.R}")
            else:
                print(f" {Col.RED}✗ Telethon open error: {e}{Col.R}")
            return None

        try:
            if interactive:
                # First-time login flow with manual validation
                await client.connect()
                if not await client.is_user_authorized():
                    phone = self._ask_phone()
                    if not phone:
                        print(f" {Col.RED}✗ Phone invalid — login aborted.{Col.R}")
                        return None
                    try:
                        sent = await client.send_code_request(phone)
                        print(f" {Col.NEON_G}✓{Col.R} Code sent via {getattr(sent, 'type', 'app')}")
                    except Exception as e:
                        print(f" {Col.RED}✗ send_code: {type(e).__name__}: {e}{Col.R}")
                        return None

                    code = self._ask_code()
                    if not code:
                        print(f" {Col.RED}✗ OTP kosong.{Col.R}")
                        return None
                    try:
                        await client.sign_in(phone, code)
                    except SessionPasswordNeededError:
                        pw = self._ask_password()
                        if not pw:
                            print(f" {Col.RED}✗ 2FA required but empty.{Col.R}")
                            return None
                        try:
                            await client.sign_in(password=pw)
                        except Exception as e:
                            print(f" {Col.RED}✗ 2FA sign_in: {type(e).__name__}: {e}{Col.R}")
                            return None
                    except Exception as e:
                        err = str(e).lower()
                        if 'invalid' in err or 'expired' in err or 'code' in err:
                            print(f" {Col.RED}✗ Kode salah/expired: {e}{Col.R}")
                        else:
                            print(f" {Col.RED}✗ sign_in: {type(e).__name__}: {e}{Col.R}")
                        return None
            else:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect()
                    return None

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
                                else f'{BASE_URL}/?v5&startapp={self.referral_code}')
                    res_menu = await client(functions.messages.RequestWebViewRequest(
                        peer=bot, bot=bot, platform='android', from_bot_menu=True, url=menu_url))
                    if res_menu and hasattr(res_menu, 'url'):
                        parsed = urllib.parse.urlparse(res_menu.url)
                        params = urllib.parse.parse_qs(parsed.fragment or parsed.query)
                        init_data = params.get('tgWebAppData', [None])[0]
            except Exception as e:
                print(f" {Col.DIM_C}  extract err: {type(e).__name__}: {e}{Col.R}")

            return init_data
        finally:
            try: await client.disconnect()
            except Exception: pass

    def silent_refresh(self):
        try:
            token = asyncio.run(self._telethon_get_initdata(interactive=False))
            if token:
                self.init_data = token
                self.save_config()
                return True
            return False
        except Exception:
            return False

    def first_time_login(self):
        clear(); print()
        print(f"{Col.NEON_C}============================================================{Col.R}")
        print(f"{Col.NEON_Y}         ⚡ LITEBITS · TELETHON FIRST LOGIN ⚡{Col.R}")
        print(f"{Col.NEON_C}============================================================{Col.R}")
        print()
        print(f" {Col.DIM_C}Login sekali. Setelah ini auto-refresh silent 24/7.{Col.R}")
        print()

        try:
            token = asyncio.run(self._telethon_get_initdata(interactive=True))
        except Exception as e:
            print(f" {Col.RED}✗ Login error: {type(e).__name__}: {e}{Col.R}")
            return False

        if not token:
            print(f" {Col.RED}✗ Login gagal — tidak dapat initData.{Col.R}")
            return False

        self.init_data = token
        self.save_config()
        print(f" {Col.NEON_G}✓{Col.R} Session saved")
        return True

    # ═══════════════════ COOLDOWN ═══════════════════
    def get_server_cooldown_left(self):
        nca = self.user_info.get('nextClaimAt')
        if nca:
            try:
                dt = datetime.fromisoformat(nca.replace('Z', '+00:00'))
                return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
            except Exception: pass
        lc = self.user_info.get('lastClaim')
        if not lc: return 0
        try:
            ld = datetime.fromisoformat(lc.replace('Z', '+00:00'))
            return max(0, self.cooldown_seconds - int((datetime.now(timezone.utc) - ld).total_seconds()))
        except Exception: return 0

    def _secs_until_iso(self, iso_str):
        try:
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
        except Exception:
            return self.cooldown_seconds

    # ═══════════════════ HUMAN TELEMETRY ═══════════════════
    def generate_tap_telemetry(self, first_claim=False):
        reaction = random.randint(5800, 9500) if first_claim else random.randint(3200, 7200)
        return {
            "x_off":       random.randint(55, 125),
            "y_off":       random.randint(75, 130),
            "btn_w":       178,
            "btn_h":       178,
            "pointer_type": "touch",
            "press_ms":    random.randint(HOLD_MS_MIN, HOLD_MS_MAX),
            "move_px":     random.randint(0, 4),
            "radius":      random.randint(2, 8),
            "pressure":    round(random.uniform(0.7, 1.0), 2),
            "reaction_ms": reaction,
            "is_trusted":  True,
        }

    # ═══════════════════ RENDERING ═══════════════════
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

    def render_banner(self):
        mode_c = Col.NEON_R if self.mode == 'hcaptcha' else Col.NEON_G
        return f"""
{Col.NEON_C}=============================================================={Col.R}
{Col.NEON_Y}                    ⚡ {Col.NEON_G}LITEBITS{Col.NEON_Y} ⚡{Col.R}
{Col.NEON_C}              {Col.WHT}AUTO CLAIM · TELETHON v4.2.0{Col.R}
{Col.NEON_C}=============================================================={Col.R}
{Col.NEON_V} Bot         : {Col.NEON_C}@{self.bot_username}{Col.R}
{Col.NEON_V} Referral    : {Col.NEON_Y}{self.referral_code}{Col.R}
{Col.NEON_V} Mode        : {mode_c}{self.mode.upper()}{Col.R}
{Col.NEON_V} API Key     : {Col.DIM_C}{(self.captcha_apikey[:10] + '...') if self.captcha_apikey else '(kosong)'}{Col.R}
{Col.NEON_V} Sitekey src : {Col.DIM_C}{self.sitekey_source}{Col.R}
{Col.NEON_V} Session     : {Col.NEON_G if self._token_valid(0) else Col.NEON_O}{'JWT VALID' if self._token_valid(0) else 'EXPIRED'}{Col.R}
{Col.NEON_V} Telethon    : {Col.NEON_G + 'OK' if self._telethon_session_exists() else Col.NEON_R + 'NONE'}{Col.R}
{Col.NEON_V} Auto-stop   : {Col.NEON_O}{MAX_RUNTIME // 3600} hours{Col.R}
{Col.NEON_C}=============================================================={Col.R}
"""

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
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Cycles{Col.R}    : {Col.WHT}{str(self.cycles):<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Success{Col.R}   : {Col.NEON_G if rate >= 90 else Col.NEON_Y}{f'{rate:.1f}%':<46}{Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R} {Col.NEON_V}Captcha{Col.R}   : {Col.NEON_G}{f'{self.captcha_solved}/{self.captcha_failed}':<46}{Col.NEON_C}│{Col.R}")
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
            print(f"{Col.NEON_C}│{Col.R} {spark}  {dc}{ds:>8}{Col.R} {Col.NEON_C}│{Col.R}")
            print(f"{Col.NEON_C}└" + "─"*60 + f"┘{Col.R}")
        print()

    def render_view(self, live_line=None):
        clear()
        print(self.render_banner())
        self.render_dashboard()
        print(f"{Col.NEON_C}========================= {Col.NEON_Y}LIVE LOGS{Col.NEON_C} ==========================={Col.R}")
        print()
        for entry in self.cycle_logs[-12:]: print(entry)
        print()
        if live_line: print(live_line); print()
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

    # ═══════════════════ SETUP ═══════════════════
    def setup(self):
        clear(); print()
        print(f" {Col.NEON_C}•{Col.R} Initializing LiteBits · Telethon mode...")
        self.load_config()
        self.fetch_app_settings()

        valid_auth = False

        if self._token_valid(min_secs=600):
            print(f" {Col.NEON_C}•{Col.R} JWT valid (exp in {(jwt_exp(self.auth_token) - time.time())/3600:.1f}h)")
            if self._profile_ok():
                valid_auth = True
                print(f" {Col.NEON_G}✓{Col.R} Session active")

        if not valid_auth and self._telethon_session_exists():
            print(f" {Col.NEON_C}•{Col.R} Silent refresh via Telethon...")
            if self.silent_refresh():
                if self.validate_telegram_auth() and self._profile_ok():
                    valid_auth = True
                    print(f" {Col.NEON_G}✓{Col.R} Session refreshed")
                else:
                    print(f" {Col.NEON_O}!{Col.R} initData ok tapi auth gagal")
            else:
                print(f" {Col.NEON_O}!{Col.R} Silent refresh gagal")

        if not valid_auth and not self._telethon_session_exists():
            print(f" {Col.NEON_Y}!{Col.R} Belum ada Telethon session — login sekali.")
            if not self.first_time_login(): return False
            if not self.validate_telegram_auth() or not self._profile_ok():
                print(f" {Col.RED}✗ Auth gagal setelah login.{Col.R}")
                return False
            valid_auth = True

        if not valid_auth and self._telethon_session_exists():
            print(f" {Col.RED}✗ Session tidak valid. Login ulang via nomor.{Col.R}")
            if not self.first_time_login(): return False
            if not self.validate_telegram_auth() or not self._profile_ok():
                return False
            valid_auth = True

        if not valid_auth:
            print(f" {Col.RED}✗ Auth gagal total.{Col.R}"); return False

        if self.hcaptcha_sitekey == HCAPTCHA_SITEKEY_DEFAULT:
            print(f" {Col.NEON_C}•{Col.R} Detecting hCaptcha sitekey...")
            sk = self.detect_sitekey(force=True)
            print(f" {Col.NEON_G}✓{Col.R} Sitekey: {Col.WHT}{sk}{Col.R} {Col.DIM_C}({self.sitekey_source}){Col.R}")

        name = self.user_info.get('telegramUsername') or self.user_info.get('username') or 'User'
        try: bal_str = f"{float(str(self.user_info.get('balance', 0))):.2f}"
        except Exception: bal_str = str(self.user_info.get('balance', '0.00'))
        print()
        print(f" {Col.NEON_G}✓{Col.R} Active session: {Col.NEON_C}@{name}{Col.R}")
        print(f" {Col.NEON_Y}💰{Col.R} Balance: {Col.NEON_Y}{bal_str} Coins{Col.R}")
        print(f" {Col.NEON_V}🎮{Col.R} Mode: {Col.NEON_Y}{self.mode.upper()}{Col.R}")
        print()

        print(f"{Col.NEON_C}┌─ {Col.NEON_Y}SELECT MODE{Col.NEON_C} " + "─"*46 + f"┐{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_G}[1]{Col.R} {Col.WHT}No Hcaptcha (claim kosong){Col.R}                        {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_Y}[2]{Col.R} {Col.WHT}Hcaptcha (solve dulu){Col.R}                              {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}├" + "─"*60 + f"┤{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_V}[3]{Col.R} {Col.WHT}Change Waryono API Key{Col.R}                             {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_P}[4]{Col.R} {Col.WHT}Re-detect sitekey{Col.R}                                  {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_G}[5]{Col.R} {Col.WHT}Test Waryono API Key{Col.R}                               {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_C}[6]{Col.R} {Col.WHT}Force silent refresh Telethon{Col.R}                      {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}│{Col.R}  {Col.NEON_O}[7]{Col.R} {Col.WHT}Re-login Telethon (phone){Col.R}                           {Col.NEON_C}│{Col.R}")
        print(f"{Col.NEON_C}└" + "─"*60 + f"┘{Col.R}")
        ch = input(f"\n{Col.WHT} ➜ Pilih [1-7]: {Col.NEON_G}").strip(); print(Col.R, end='')

        if ch == '1':
            self.mode = 'no_hcaptcha'; self.save_config()
            print(f" {Col.NEON_G}✓{Col.R} Mode: NO HCAPTCHA")
        elif ch == '2':
            self.mode = 'hcaptcha'; self.save_config()
            print(f" {Col.NEON_G}✓{Col.R} Mode: HCAPTCHA")
            if not self.captcha_apikey:
                print()
                key = input(f" {Col.NEON_G}➜{Col.R} Waryono API Key: ").strip(); print(Col.R, end='')
                if key:
                    self.captcha_apikey = key; self.save_config()
                    print(f" {Col.NEON_G}✓{Col.R} API key saved")
        elif ch == '3':
            nk = input(f" Waryono API Key baru: ").strip(); print(Col.R, end='')
            if nk:
                self.captcha_apikey = nk; self.save_config()
                print(f" {Col.NEON_G}✓{Col.R} API key updated")
        elif ch == '4':
            sk = self.detect_sitekey(force=True)
            print(f" {Col.NEON_G}✓{Col.R} Sitekey: {Col.WHT}{sk}{Col.R} {Col.DIM_C}({self.sitekey_source}){Col.R}")
        elif ch == '5':
            if not self.captcha_apikey:
                print(f" {Col.RED}✗{Col.R} API key belum di-set")
            else:
                solver = WaryonoSolver(self.captcha_apikey, self.hcaptcha_sitekey)
                ok, msg = solver.test_apikey()
                print(f" {Col.NEON_G}✓{Col.R} Waryono: {msg}" if ok else f" {Col.RED}✗{Col.R} Waryono: {msg}")
        elif ch == '6':
            if not self._telethon_session_exists():
                print(f" {Col.RED}✗{Col.R} Tidak ada .session — pakai [7] login dulu.")
            else:
                print(f" {Col.NEON_C}•{Col.R} Refreshing via Telethon...")
                if self.silent_refresh() and self.validate_telegram_auth() and self._profile_ok():
                    print(f" {Col.NEON_G}✓{Col.R} Session refreshed")
                else:
                    print(f" {Col.RED}✗{Col.R} Refresh gagal — coba [7]")
        elif ch == '7':
            if not self.first_time_login(): return False
            if not self.validate_telegram_auth() or not self._profile_ok():
                print(f" {Col.RED}✗ Auth gagal.{Col.R}"); return False

        return True

    # ═══════════════════ CLAIM FLOW ═══════════════════
    def do_claim_flow(self):
        self.add_log('info', f"Mode: {Col.NEON_Y}{self.mode}{Col.R}")

        hold_ms = random.randint(HOLD_MS_MIN, HOLD_MS_MAX)
        self.add_log('info', f"Hold button {Col.NEON_Y}({hold_ms}ms){Col.R}...")
        self._progress_wait(int(hold_ms / 1000), label="HOLD")

        captcha_token = ""
        if self.mode == 'hcaptcha':
            self.claim_state = 'SOLVING'
            self.add_log('cap', f"Solving hCaptcha (sitekey: {self.hcaptcha_sitekey[:20]}...)")
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

        self._human_pause()
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
        self._human_pause(POST_HUMAN_PAUSE)

        self.add_log('info', f"Start: {str(sd)[:120]}")

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
            self.add_log('info', f"Ad: {Col.DIM_C}{ad_info.get('title')[:60]}{Col.R}")

        self._human_pause()
        ad_token = None; ad_min_secs = 10
        try:
            r_ads = self.session.get(f"{BASE_URL}/api/claim/{claim_id}/ads", timeout=15)
            if r_ads.status_code == 200:
                aj = r_ads.json()
                if aj.get('success') and aj.get('adsUrl'):
                    ad_token = aj['adsUrl'].get('token')
                    sdk = aj['adsUrl'].get('sdkAd') or {}
                    ad_min_secs = sdk.get('min_seconds', 10)
        except Exception: pass
        self._human_pause(POST_HUMAN_PAUSE)

        self._human_pause((400, 1500))
        try:
            self.session.post(f"{BASE_URL}/api/claim/{claim_id}/sdk-frame",
                json={"state": "fallback", "bucket": "timeout"}, timeout=10)
        except Exception: pass

        self._human_pause(POST_HUMAN_PAUSE)
        try:
            self.session.post(f"{BASE_URL}/api/ads/outcome",
                json={"network": "sdk-frame", "outcome": "fallback"}, timeout=10)
        except Exception: pass

        ad_wait = max(ad_min_secs, random.randint(AD_WAIT_MIN, AD_WAIT_MAX))
        self.claim_state = 'WATCHING'
        self.add_log('wait', f"Watching ad {Col.NEON_Y}({ad_wait}s){Col.R}...")
        self._progress_wait(ad_wait, label="AD")

        reaction_ms = random.randint(2500, 6500)
        self._human_pause((reaction_ms, reaction_ms + 200))

        tap = self.generate_tap_telemetry(first_claim=(self.cycles == 0))
        complete_payload = {"token": ad_token or "", "tap": tap}
        self.claim_state = 'CLAIMING'
        self.add_log('net', f"POST /api/claim/{{id}}/complete (tap: {tap['press_ms']}ms/{tap['reaction_ms']}ms)...")
        amount = 1.0; ok = False; next_claim_iso = None
        try:
            r = self.session.post(f"{BASE_URL}/api/claim/{claim_id}/complete",
                                  json=complete_payload, timeout=20)
            cd = r.json()
            self.add_log('info', f"Complete: {str(cd)[:160]}")
            if cd.get('success'):
                ok = True
                amount = float(cd.get('reward', cd.get('amount', 1.0)))
                next_claim_iso = cd.get('nextClaimAt')
        except Exception as e:
            self.add_log('err', f"Complete: {e}")

        if not ok:
            self.add_log('warn', "Claim unconfirmed")
            self.cycles_failed += 1; self.save_config()
            return False, 'unconfirmed'

        self._human_pause((300, 1200))
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
        time.sleep(1.2)
        return True, {"status": "Success", "next_claim_at": next_claim_iso}

    def live_cooldown(self, wait_seconds=None):
        if wait_seconds is not None:
            total_sec = int(wait_seconds)
        else:
            total_sec = self.get_server_cooldown_left() or self.cooldown_seconds
        total_sec = int(total_sec + random.uniform(2, 10))
        total = total_sec
        while total_sec > 0 and self.running:
            if (time.time() - self.start_time) >= MAX_RUNTIME:
                self.add_log('warn', "Runtime limit reached.")
                self.running = False; break
            mm, ss = divmod(total_sec, 60); hh, mm = divmod(mm, 60)
            tstr = f"{hh:02d}:{mm:02d}:{ss:02d}"
            bar = self._bar(total_sec, total)
            self.render_view(live_line=f" {Col.NEON_Y}[⏳ WAIT]{Col.R} Cooldown {Col.WHT}{tstr}{Col.R}  [{bar}]")
            time.sleep(1); total_sec -= 1
        if self.running:
            self.render_view(live_line=f" {Col.NEON_G}[✓ READY]{Col.R} Cooldown finished.")
            time.sleep(1)

    def generate_report(self, reason="TIME LIMIT"):
        runtime = int(time.time() - self.start_time)
        h, r = divmod(runtime, 3600); m, s = divmod(r, 60)
        try:
            final_bal_str = f"{float(str(self.user_info.get('balance', 0))):.2f} Coins"
        except Exception:
            final_bal_str = "N/A"
        total_cyc = self.cycles + self.cycles_failed
        rate = (self.cycles / total_cyc * 100) if total_cyc > 0 else 0.0
        lines = ["",
            f"{Col.NEON_C}╔══════════════════════════════════════════════════════════════╗{Col.R}",
            f"{Col.NEON_C}║{Col.R}           {Col.NEON_Y}⚡ SESSION REPORT · v4.2.0 TELETHON ⚡{Col.R}          {Col.NEON_C}║{Col.R}",
            f"{Col.NEON_C}╚══════════════════════════════════════════════════════════════╝{Col.R}",
            "",
            f"{Col.NEON_V}  Reason          : {Col.WHT}{reason}{Col.R}",
            f"{Col.NEON_V}  Mode            : {Col.NEON_Y}{self.mode.upper()}{Col.R}",
            f"{Col.NEON_V}  Session         : {Col.NEON_G if self._token_valid(0) else Col.NEON_O}{'JWT VALID' if self._token_valid(0) else 'EXPIRED'}{Col.R}",
            f"{Col.NEON_V}  Telethon        : {Col.NEON_G if self._telethon_session_exists() else Col.NEON_R}{'OK' if self._telethon_session_exists() else 'NONE'}{Col.R}",
            f"{Col.NEON_V}  Runtime         : {Col.NEON_C}{h:02d}h {m:02d}m {s:02d}s{Col.R}",
            f"{Col.NEON_V}  Total Earned    : {Col.NEON_G}+{self.session_earned:.4f} Coins{Col.R}",
            f"{Col.NEON_V}  Final Balance   : {Col.NEON_Y}{final_bal_str}{Col.R}",
            f"{Col.NEON_V}  Cycles OK       : {Col.NEON_G}{self.cycles}{Col.R}",
            f"{Col.NEON_V}  Cycles Failed   : {Col.NEON_R}{self.cycles_failed}{Col.R}",
            f"{Col.NEON_V}  Success Rate    : {Col.NEON_G if rate >= 90 else Col.NEON_Y}{rate:.1f}%{Col.R}",
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
        if not self.setup(): sys.exit(1)

        stop_reason = "USER STOPPED"
        max_h = MAX_RUNTIME // 3600

        self.add_log('info', f"Auto-stop {Col.NEON_Y}{max_h}h{Col.R}")
        self.add_log('info', f"Mode: {Col.NEON_Y}{self.mode}{Col.R}")
        self.add_log('info', f"Session: {Col.NEON_G}JWT ACTIVE{Col.R}")
        time.sleep(1)

        while self.running:
            try:
                if (time.time() - self.start_time) >= MAX_RUNTIME:
                    stop_reason = f"TIME LIMIT ({max_h}H)"
                    self.running = False; break

                if not self._token_valid(min_secs=300):
                    self.add_log('warn', "JWT expiring — silent refresh...")
                    if self.silent_refresh() and self.validate_telegram_auth():
                        self.add_log('ok', "Refreshed via Telethon")
                    else:
                        self.add_log('err', "Silent refresh failed — stopping")
                        stop_reason = "SESSION EXPIRED"
                        break

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
                    if res > (MAX_RUNTIME - (time.time() - self.start_time)):
                        stop_reason = "TIME LIMIT DURING COOLDOWN"
                        self.running = False; break
                    self.live_cooldown(wait_seconds=res)
                    continue

                if ok and isinstance(res, dict) and res.get('next_claim_at'):
                    wait_sec = self._secs_until_iso(res['next_claim_at'])
                    self.live_cooldown(wait_seconds=wait_sec)
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
