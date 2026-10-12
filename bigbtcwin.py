#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
 BOT bigbtc.win — Python Edition
 CF bypass Seledroid • Waryono hCaptcha • Auto claim
 By MoneyMaker_w
═══════════════════════════════════════════════════════════════
"""

import os, sys, re, json, time, math, ssl, random, subprocess, threading, signal
import urllib.parse
import requests
from datetime import datetime

import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
#  COLOR
# ═══════════════════════════════════════════════════════════════
RED = "\x1b[0;31m"; GRN = "\x1b[0;32m"; YEL = "\x1b[0;33m"
BLU = "\x1b[0;34m"; MAG = "\x1b[0;35m"; CYN = "\x1b[0;36m"; WHT = "\x1b[0;37m"
RST = "\x1b[0m"; ORG = "\x1b[38;5;208m"
CLR = "\r\x1b[2K"

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
TMP_EXEC_PY = os.path.join(BASE_DIR, ".cf_bypass.py")

HOST = "https://bigbtc.win"
PAGE_URL = f"{HOST}/faucet"
CLAIM_URL = f"{HOST}/claimreward"
SITEKEY = "c0a0b0a5-2a3c-4a10-b165-7b93e4e81a00"

SOLVER_IN = "https://api.waryono.my.id/in.php"
SOLVER_RES = "https://api.waryono.my.id/res.php"
SOLVER_HOST = "api.waryono.my.id"

DEF_UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"

TG_GROUP = "https://t.me/+f3QBLkR5D8k4YzNl"
SOLVER_TIMEOUT = 600

FATAL_ERRORS = {
    "ERROR_KEY_DOES_NOT_EXIST": "API key kosong / tidak dikirim",
    "ERROR_WRONG_USER_KEY": "API key tidak valid / tidak ditemukan",
    "ERROR_ZERO_BALANCE": "Saldo token habis / tidak cukup",
    "ERROR_NO_SUCH_METHOD": "Method tidak dikenali (bukan hcaptcha)",
    "ERROR_BAD_PARAMETERS": "Parameter tidak lengkap (sitekey/url/domain)",
    "ERROR_METHOD_NOT_SPECIFIED": "Parameter methods tidak diisi",
    "ERROR_EMPTY_IMAGE": "Gambar tidak dikirim (base64 kosong)",
    "ERROR_URL_EMPTY": "URL tidak dikirim",
    "ERROR_WRONG_METHOD": "HTTP Method salah (harus POST)",
}

RETRYABLE_ERRORS = {
    "ERROR_CAPTCHA_UNSOLVABLE", "WRONG_CAPTCHA_ID",
    "ERROR_TOO_MANY_REQUESTS", "ERROR_DATABASE_CONNECTION_FAILED",
    "INTERNAL_SERVER_ERROR", "ERROR_POLL_TIMEOUT",
    "ERROR_INVALID_JSON", "ERROR_NO_TASK_ID",
}

# ═══════════════════════════════════════════════════════════════
#  SELEDROID EXEC SOURCE
# ═══════════════════════════════════════════════════════════════
EXEC_PY_SOURCE = '''import time
import sys
import json
import warnings
import os

warnings.filterwarnings('ignore')
os.environ["PYTHONWARNINGS"] = "ignore"

def log(msg):
    print(msg, file=sys.stderr)

def bypass_cf(target):
    log("Seledroid Cloudflare...")

    _stderr_backup = sys.stderr
    _devnull = open(os.devnull, 'w')
    sys.stderr = _devnull

    try:
        from seledroid import webdriver as sd
    except ImportError:
        sys.stderr = _stderr_backup
        _devnull.close()
        log("install Seledroid module and Apk")
        sys.exit(1)
    finally:
        sys.stderr = _stderr_backup
        try:
            _devnull.close()
        except Exception:
            pass

    time.sleep(3)

    try:
        d = sd.Chrome(gui=True, pip_mode=False)
        d.get(target)
        time.sleep(10)

        clr = None
        for _ in range(15):
            clr = d.get_cookie("cf_clearance")
            if clr:
                break
            time.sleep(5)

        try:
            ua = d.user_agent
        except Exception:
            try:
                ua = d.execute_script("return navigator.userAgent;")
            except Exception:
                ua = None

        try:
            d.close()
        except Exception:
            pass

    except Exception as e:
        log("Failed ({})".format(e))
        return {"cf_clearance": None, "user_agent": None}

    if not clr:
        log("Failed (no cf_clearance)")
        return {"cf_clearance": None, "user_agent": None}

    tok = clr.split("=", 1)[1] if "=" in clr else clr
    log("Success!")
    return {
        "cf_clearance": tok,
        "user_agent": ua
    }

def usage():
    log("Usage:")
    log("  python exec.py <url>")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    TARGET_URL = sys.argv[1]
    result = bypass_cf(TARGET_URL)
    print(json.dumps(result))
'''

# ═══════════════════════════════════════════════════════════════
#  UTIL
# ═══════════════════════════════════════════════════════════════
def clear():
    sys.stdout.write('\x1b[2J\x1b[3J\x1b[H')
    sys.stdout.flush()

def now():
    return datetime.now().strftime("%H:%M:%S")

def log(msg, tag='i'):
    icons = {
        'i':   f"{CYN}»{RST}",
        'ok':  f"{GRN}✓{RST}",
        'er':  f"{RED}✗{RST}",
        'wr':  f"{YEL}⚠{RST}",
        'in':  f"{BLU}●{RST}",
        'bi':  f"{GRN}₹{RST}",
        'dbg': f"{MAG}⚙{RST}",
        'or':  f"{ORG}●{RST}",
    }
    icon = icons.get(tag, f"{CYN}»{RST}")
    sys.stdout.write(CLR + f"{WHT}[{now()}]{RST} {icon} {msg}\n")
    sys.stdout.flush()

SYMBOLS = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑']
SPINNERS = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
DOTS = ['▪', '▪▪', '▪▪▪', '▪▪▪▪']

# ═══════════════════════════════════════════════════════════════
#  SPINNER
# ═══════════════════════════════════════════════════════════════
class Spinner:
    def __init__(self, label, timeout):
        self.label = label
        self.timeout = timeout
        self.running = False
        self.thread = None
        self.start_time = time.time()

    def _run(self):
        i = 0
        while self.running:
            elapsed = int(time.time() - self.start_time)
            pct = int((elapsed / self.timeout * 100)) if self.timeout else 0
            sym = SYMBOLS[i % len(SYMBOLS)]
            sp = SPINNERS[i % len(SPINNERS)]
            sp1 = SPINNERS1[i % len(SPINNERS1)]
            dot = DOTS[elapsed % len(DOTS)]
            i += 1
            c1 = 1 + random.randint(0, 6)
            c2 = 1 + random.randint(0, 6)
            mm = f"{elapsed // 60:02d}"
            ss = f"{elapsed % 60:02d}"
            sys.stdout.write(
                f"{CLR} \x1b[1;3{c1}m {sp}\x1b[1;37m {self.label} "
                f"\x1b[1;31m{mm}:{ss}\x1b[1;3{c2}m {sym} {sp1}"
                f"\x1b[1;37m {pct}%\x1b[1;33m {dot}"
            )
            sys.stdout.flush()
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        sys.stdout.write(CLR)
        sys.stdout.flush()

def start_spinner(label, timeout):
    return Spinner(label, timeout).start()

def tmr(seconds, label="Waiting..."):
    total = int(seconds)
    if total < 1:
        return
    start = time.time()
    i = 0
    while True:
        elapsed = int(time.time() - start)
        remaining = max(0, total - elapsed)
        pct = int(((total - remaining) / total) * 100) if total else 0
        mm = f"{remaining // 60:02d}"
        ss = f"{remaining % 60:02d}"
        sym = SYMBOLS[i % len(SYMBOLS)]
        sp = SPINNERS[i % len(SPINNERS)]
        sp1 = SPINNERS1[i % len(SPINNERS1)]
        dot = DOTS[elapsed % len(DOTS)]
        i += 1
        c1 = 1 + random.randint(0, 6)
        c2 = 1 + random.randint(0, 6)
        sys.stdout.write(
            f"{CLR} \x1b[1;3{c1}m {sp}\x1b[1;37m {label} "
            f"\x1b[1;31m{mm}:{ss}\x1b[1;3{c2}m {sym} {sp1}"
            f"\x1b[1;37m {pct}%\x1b[1;33m {dot}"
        )
        sys.stdout.flush()
        if remaining <= 0:
            break
        time.sleep(0.1)
    sys.stdout.write(CLR)
    sys.stdout.flush()

def banner_main():
    print(f"{WHT}═══════════════════════════════════════════════{RST}")
    print(f"{YEL}              BOT bigbtc.win{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")
    print(f"{CYN}  Join grup: {WHT}{TG_GROUP}{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")

# ═══════════════════════════════════════════════════════════════
#  COOKIE
# ═══════════════════════════════════════════════════════════════
def parse_cookie_string(s):
    out = {}
    if not s:
        return out
    for part in s.split(';'):
        t = part.strip()
        if not t: continue
        idx = t.find('=')
        if idx == -1: continue
        k = t[:idx].strip()
        v = t[idx+1:].strip()
        if k: out[k] = v
    return out

# ═══════════════════════════════════════════════════════════════
#  HTTP CLIENT
# ═══════════════════════════════════════════════════════════════
def make_client(cfg, jar):
    session = requests.Session()
    session.headers.update({
        'User-Agent': cfg.get('userAgent') or DEF_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Ch-Ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?1',
        'Sec-Ch-Ua-Platform': '"Android"',
        'Upgrade-Insecure-Requests': '1',
    })

    def do_get(url, extra_headers=None):
        session.cookies.clear()
        for k, v in jar.items():
            session.cookies.set(k, v, domain='bigbtc.win')
        r = session.get(url, headers=extra_headers or {}, timeout=45, allow_redirects=True)
        for c in session.cookies:
            jar[c.name] = c.value
        return r

    def do_post(url, body, extra_headers=None):
        session.cookies.clear()
        for k, v in jar.items():
            session.cookies.set(k, v, domain='bigbtc.win')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        if extra_headers:
            headers.update(extra_headers)
        r = session.post(url, data=body, headers=headers, timeout=45, allow_redirects=True)
        for c in session.cookies:
            jar[c.name] = c.value
        return r

    return do_get, do_post

# ═══════════════════════════════════════════════════════════════
#  SOLVER
# ═══════════════════════════════════════════════════════════════
def solver_post_json(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=30,
                          headers={'User-Agent': DEF_UA, 'Accept': 'application/json'})
        return r.status_code, r.json() if r.text.strip().startswith('{') else {'status': 0, 'request': r.text}
    except Exception as e:
        return 0, {'status': 0, 'request': f"ERROR_INVALID_JSON:{e}"}

def solver_get_json(url, params):
    try:
        r = requests.get(url, params=params, timeout=30,
                         headers={'User-Agent': DEF_UA, 'Accept': 'application/json'})
        return r.status_code, r.json() if r.text.strip().startswith('{') else {'status': 0, 'request': r.text}
    except Exception as e:
        return 0, {'status': 0, 'request': f"ERROR_INVALID_JSON:{e}"}

def classify_solver_status(status_code, status_msg):
    if status_code in (401, 402, 400, 405): return 'fatal'
    if status_msg in FATAL_ERRORS: return 'fatal'
    if status_msg == 'ERROR_TOO_MANY_REQUESTS': return 'rate'
    if status_code == 429 or status_code >= 500: return 'server'
    if status_msg in RETRYABLE_ERRORS: return 'retry'
    if status_msg == 'CAPCHA_NOT_READY': return 'polling'
    return 'unknown'

def solve_hcaptcha(apikey, timeout=SOLVER_TIMEOUT):
    payload = {
        'apikey': apikey,
        'methods': 'hcaptcha',
        'domain': HOST,
        'sitekey': SITEKEY,
        'json': 1,
    }

    spinner = start_spinner('[hCaptcha]', timeout)

    try:
        code, data = solver_post_json(SOLVER_IN, payload)
        task = data or {}

        if task.get('status') != 1:
            err_msg = str(task.get('error') or task.get('request') or 'UNKNOWN')
            kind = classify_solver_status(code, err_msg)
            spinner.stop()

            log(f'[hCaptcha] Gagal: {{"status":0, "request":"{err_msg}"}}', 'er')

            if kind == 'fatal':
                log(FATAL_ERRORS.get(err_msg, err_msg), 'er')
                return ('fatal', err_msg)
            return (kind, err_msg)

        task_id = task.get('request') or ''
        if not task_id:
            spinner.stop()
            log('[hCaptcha] Gagal: no task_id', 'er')
            return ('retry', 'ERROR_NO_TASK_ID')

        log(f'[hCaptcha] Submit OK, task_id: {task_id}', 'dbg')

        p_start = time.time()
        last = 0

        while True:
            p_elapsed = time.time() - p_start

            if p_elapsed > timeout:
                spinner.stop()
                print('')
                print(f"{RED}═══════════════════════════════════════════════{RST}")
                print(f"{RED}  ✗ SOLVER TIMEOUT — hCaptcha DOWN!{RST}")
                print(f"{RED}  Menunggu {int(timeout/60)} menit tanpa hasil.{RST}")
                print(f"{RED}  Bot dihentikan.{RST}")
                print(f"{WHT}  Cek grup: {CYN}{TG_GROUP}{RST}")
                print(f"{RED}═══════════════════════════════════════════════{RST}")
                print('')
                return ('timeout_fatal', 'SOLVER_DOWN')

            if p_elapsed >= last + 3:
                last = p_elapsed

                pcode, pdata = solver_get_json(SOLVER_RES, {
                    'apikey': apikey, 'action': 'get', 'id': task_id, 'json': 1,
                })

                d = pdata or {}
                if d.get('status') == 1:
                    spinner.stop()
                    tok = d.get('request', '')
                    log(f'[hCaptcha] Solved: {tok[:30]}...', 'ok')
                    return tok

                req_status = str(d.get('request') or d.get('error') or '')

                if req_status == 'CAPCHA_NOT_READY':
                    # update spinner label aja, ga spam log
                    spinner.label = f"[hCaptcha] polling {int(p_elapsed)}s"
                elif req_status.startswith('ERROR_') or req_status == 'WRONG_CAPTCHA_ID':
                    spinner.stop()
                    log(f'[hCaptcha] Gagal: {req_status}', 'er')
                    kind = classify_solver_status(200, req_status)
                    if kind == 'fatal':
                        log(FATAL_ERRORS.get(req_status, req_status), 'er')
                        return ('fatal', req_status)
                    return (kind, req_status)

            time.sleep(0.3)
    except Exception as e:
        spinner.stop()
        log(f'[hCaptcha] Gagal: {e}', 'er')
        return ('retry', f"ERROR_INVALID_JSON:{e}")

# ═══════════════════════════════════════════════════════════════
#  HTML PARSER
# ═══════════════════════════════════════════════════════════════
def is_logged_in(html):
    if not html: return False
    return 'id="btcaddress"' in html and 'logout' in html.lower()

def is_cf_challenge(html, status_code):
    if status_code in (403, 503): return True
    if not html: return False
    low = html.lower()
    return ('just a moment' in low or 'challenges.cloudflare.com' in low or
            'cf-chl' in low or 'cf-mitigated' in low)

def parse_csrf(html):
    if not html: return None
    patterns = [
        r'name=["\']csrftoken["\']\s+value=["\']([^"\']+)["\']',
        r'value=["\']([^"\']+)["\']\s+name=["\']csrftoken["\']',
        r'csrftoken\s*[=:]\s*["\']([^"\']+)["\']',
        r'csrf_token\s*[=:]\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m: return m.group(1)
    return None

def parse_balance(html):
    if not html: return None
    m = re.search(r'id="account"[^>]*><b>(\d+)</b>\s*satoshi', html)
    return int(m.group(1)) if m else None

def parse_reward(html):
    if not html: return None
    m = re.search(r'You won\s*<b>(\d+)</b>\s*satoshi', html, re.I)
    if m: return f"{m.group(1)} satoshi"
    m2 = re.search(r'You won\s*([\d.]+)\s*satoshi', html, re.I)
    return f"{m2.group(1)} satoshi" if m2 else None

def parse_cooldown(html):
    if not html: return None
    m = re.search(r'countdown\((\d+)\)', html)
    return int(m.group(1)) if m else None

def print_reward(reward_text, balance):
    ts = now()
    print(f"{WHT}[{ts}]{RST} {GRN}{reward_text.lower()} has been sent to your account!{RST}")
    if balance is not None:
        print(f"{WHT}[{ts}]{RST} {YEL}» New Balance: {balance} sats{RST}")

# ═══════════════════════════════════════════════════════════════
#  CF BYPASS
# ═══════════════════════════════════════════════════════════════
def extract_exec_py():
    with open(TMP_EXEC_PY, 'w', encoding='utf-8') as f:
        f.write(EXEC_PY_SOURCE)

def cleanup_exec_py():
    try:
        if os.path.exists(TMP_EXEC_PY):
            os.unlink(TMP_EXEC_PY)
    except Exception:
        pass

def run_cf_bypass(target, suppress_stderr=False):
    extract_exec_py()

    proc = subprocess.Popen(
        ['python', TMP_EXEC_PY, target],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout_buf = []
    stderr_buf = []

    def read_stdout():
        for line in proc.stdout:
            stdout_buf.append(line)

    def read_stderr():
        for line in proc.stderr:
            stderr_buf.append(line)
            if not suppress_stderr:
                ln = line.strip()
                if ln:
                    sys.stdout.write(f"   {MAG}[seledroid]{RST} {ln}\n")
                    sys.stdout.flush()

    t1 = threading.Thread(target=read_stdout)
    t2 = threading.Thread(target=read_stderr)
    t1.start(); t2.start()
    proc.wait()
    t1.join(); t2.join()

    cleanup_exec_py()

    if proc.returncode != 0:
        raise Exception(''.join(stderr_buf).strip() or f"exit code {proc.returncode}")

    lines = [ln.strip() for ln in ''.join(stdout_buf).strip().split('\n') if ln.strip()]
    if not lines:
        raise Exception("no output")

    last = lines[-1]
    try:
        return json.loads(last)
    except Exception:
        raise Exception(f"bad JSON: {last[:100]}")

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return cfg if (cfg.get('apikey') and cfg.get('cookie')) else None
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════════
#  WIZARD
# ═══════════════════════════════════════════════════════════════
def ask(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ''

def setup_wizard():
    clear()
    banner_main()
    print(f"{WHT}  ⚙  BigBTC Configuration Setup{RST}")
    print(f"{WHT}  ─────────────────────────────{RST}")

    apikey = ask(f"{WHT}  Skibidixxx Apikey : {RST}").strip()
    user_agent = ask(f"{WHT}  User Agent        : {RST}").strip()
    cookie = ask(f"{WHT}  Cookie            : {RST}").strip()

    if not apikey or not cookie:
        print('')
        log('Apikey & Cookie wajib diisi.', 'er')
        sys.exit(1)

    cfg = {
        'apikey': apikey,
        'userAgent': user_agent or DEF_UA,
        'cookie': cookie,
        'minDelaySec': 485,
        'maxDelaySec': 490,
    }
    save_config(cfg)

    clear()
    banner_main()
    log('Config tersimpan di config.json', 'ok')
    time.sleep(1)
    return cfg

def prompt_new_cookie(cfg, jar):
    print('')
    print(f"{WHT}═══════════════════════════════════════════════{RST}")
    print(f"{RED}  ⚠  Cookie Expired / Cloudflare Block!{RST}")
    print(f"{WHT}═══════════════════════════════════════════════{RST}")

    new_cookie = ask(f"{WHT}  Paste New Cookie : {RST}").strip()
    clear()
    banner_main()

    if not new_cookie:
        log('Cookie kosong, batal.', 'er')
        time.sleep(1)
        return False

    parsed = parse_cookie_string(new_cookie)
    if 'PHPSESSID' not in parsed:
        log('Cookie tidak punya PHPSESSID.', 'wr')

    jar.clear()
    jar.update(parsed)
    cfg['cookie'] = new_cookie
    save_config(cfg)
    log('Cookie baru disimpan ke config.json', 'ok')
    return True

# ═══════════════════════════════════════════════════════════════
#  SESSION
# ═══════════════════════════════════════════════════════════════
def check_session(cfg, jar):
    do_get, _ = make_client(cfg, jar)
    r = do_get(PAGE_URL)
    if is_cf_challenge(r.text, r.status_code):
        return ('cf', r.text, r)
    if not is_logged_in(r.text):
        return ('invalid', r.text, r)
    return ('ok', r.text, r)

def handle_cf_challenge(cfg, jar):
    sys.stdout.write(CLR + f"{WHT}[{now()}]{RST} {ORG}●{RST} Seledroid Cloudflare... ")
    sys.stdout.flush()

    try:
        result = run_cf_bypass(HOST, suppress_stderr=True)

        if not result.get('cf_clearance'):
            sys.stdout.write(f"{RED}Failed{RST}\n")
            sys.stdout.flush()
            return False

        jar['cf_clearance'] = result['cf_clearance']

        if result.get('user_agent'):
            cfg['userAgent'] = result['user_agent']

        parsed_cookie = parse_cookie_string(cfg.get('cookie', ''))
        parsed_cookie['cf_clearance'] = result['cf_clearance']
        cfg['cookie'] = '; '.join(f"{k}={v}" for k, v in parsed_cookie.items())
        save_config(cfg)

        sys.stdout.write(f"{GRN}Success!{RST}\n")
        sys.stdout.flush()
        time.sleep(1)
        return True
    except Exception as e:
        sys.stdout.write(f"{RED}Failed ({e}){RST}\n")
        sys.stdout.flush()
        return False

# ═══════════════════════════════════════════════════════════════
#  FAUCET LOOP
# ═══════════════════════════════════════════════════════════════
def run_faucet(cfg, jar):
    reject_count = 0
    last_balance = None
    first_round = True

    while True:
        try:
            if first_round:
                log('Cek status session...', 'i')

            status, html, res = check_session(cfg, jar)

            if status == 'cf':
                ok = handle_cf_challenge(cfg, jar)
                if not ok:
                    tmr(15, 'Retry...')
                continue

            if status == 'invalid':
                log('Cookie expired. Input ulang...', 'wr')
                ok = prompt_new_cookie(cfg, jar)
                if not ok:
                    return
                continue

            bal = parse_balance(html)
            if bal is not None:
                last_balance = bal
            if bal is not None and first_round:
                log(f'Session aktif — Balance: {bal} satoshi', 'ok')

            first_round = False

            reward_in_page = parse_reward(html)
            if reward_in_page:
                print_reward(reward_in_page, bal)
                cd = parse_cooldown(html) or 480
                tmr(cd + 2, 'Waiting...')
                continue

            csrf = parse_csrf(html)
            if not csrf:
                cd = parse_cooldown(html)
                if cd:
                    tmr(cd + 2, 'Waiting...')
                    continue
                log('csrftoken tidak ditemukan!', 'er')
                time.sleep(5)
                continue

            token = solve_hcaptcha(cfg['apikey'])
            if isinstance(token, tuple):
                kind, code = token

                if kind == 'timeout_fatal':
                    print(f"{YEL}Bot dihentikan karena hCaptcha solver tidak respond.{RST}")
                    return

                if kind == 'fatal':
                    print('')
                    print(f"{RED}═══════════════════════════════════════════════{RST}")
                    print(f"{RED}  FATAL: {code}{RST}")
                    print(f"{RED}  {FATAL_ERRORS.get(code, '')}{RST}")
                    print(f"{WHT}  Join grup: {CYN}{TG_GROUP}{RST}")
                    print(f"{RED}═══════════════════════════════════════════════{RST}")
                    return

                if kind == 'rate':
                    tmr(10, 'Waiting...')
                    continue
                if kind == 'server':
                    tmr(5, 'Waiting...')
                    continue
                time.sleep(2)
                continue

            body = urllib.parse.urlencode({
                'csrftoken': csrf,
                'claim': 'true',
                'g-recaptcha-response': token,
                'h-captcha-response': token,
            })

            _, do_post = make_client(cfg, jar)
            try:
                claim_res = do_post(CLAIM_URL, body, extra_headers={
                    'Origin': HOST,
                    'Referer': PAGE_URL,
                })
            except Exception as e:
                log(f'Claim error: {e}', 'er')
                time.sleep(5)
                continue

            if is_cf_challenge(claim_res.text, claim_res.status_code):
                ok = handle_cf_challenge(cfg, jar)
                if not ok:
                    tmr(15, 'Retry...')
                continue

            reward = parse_reward(claim_res.text)
            if reward:
                reject_count = 0
                new_bal = parse_balance(claim_res.text)
                if new_bal is None:
                    new_bal = last_balance
                else:
                    last_balance = new_bal

                print_reward(reward, new_bal)
                wait = parse_cooldown(claim_res.text) or 480
                tmr(wait + 2, 'Waiting...')
                continue

            low = claim_res.text.lower()
            if 'invalid' in low or 'expired' in low or 'login' in low:
                reject_count += 1
                if reject_count >= 3:
                    log('Session invalid, input ulang cookie...', 'wr')
                    ok = prompt_new_cookie(cfg, jar)
                    if not ok:
                        return
                    reject_count = 0
                    continue
                time.sleep(3)
                continue

            reject_count += 1
            if reject_count >= 5:
                log(f'Terlalu banyak reject ({reject_count}). Retry...', 'wr')
                tmr(30, 'Waiting...')
                reject_count = 0
                continue
            time.sleep(3)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            log(f'Error: {e}', 'er')
            time.sleep(5)

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def handle_sigint(sig, frame):
    cleanup_exec_py()
    sys.stdout.write('\n')
    print(f"{YEL}Dihentikan user.{RST}")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, handle_sigint)

    cfg = load_config()
    if not cfg:
        cfg = setup_wizard()
    else:
        clear()
        banner_main()
        log('Config loaded dari config.json', 'ok')
        log(f'UA     : {(cfg.get("userAgent") or "")[:55]}...', 'dbg')
        log(f'Cookie : {(cfg.get("cookie") or "")[:40]}...', 'dbg')
        time.sleep(0.5)

    jar = parse_cookie_string(cfg.get('cookie', ''))

    clear()
    banner_main()
    print(f"{WHT}Mode  : {CYN}Auto Claim{RST}")
    print(f"{WHT}───────────────────────────────────────────────{RST}")

    try:
        run_faucet(cfg, jar)
    finally:
        cleanup_exec_py()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        cleanup_exec_py()
        print(f"\n{YEL}Dihentikan user.{RST}")
        sys.exit(0)
    except Exception as e:
        cleanup_exec_py()
        print(f"{RED}Fatal: {e}{RST}")
        sys.exit(1)
