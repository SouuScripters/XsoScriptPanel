#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import base64
import random
import re
import threading
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import urllib.parse
from datetime import datetime

# ===============================================================
#  COLOR & UI
# ===============================================================
RED = "\x1b[38;5;203m"
GRN = "\x1b[38;5;114m"
YEL = "\x1b[38;5;179m"
BLU = "\x1b[38;5;39m"
MAG = "\x1b[38;5;170m"
CYN = "\x1b[38;5;39m"
WHT = "\x1b[38;5;255m"
ABU = "\x1b[38;5;245m"
ORG = "\x1b[38;5;208m"
RST = "\x1b[0m"
CLR = "\r\x1b[2K"
BG_MERAH = "\x1b[41m"

ANSI_REGEX = re.compile(r'\x1b\[[0-9;]*m')
def vlen(s): return len(ANSI_REGEX.sub('', s))
def pad(s, n): return s + ' ' * max(0, n - vlen(s))
INNER = 47

def boxTop(label, color):
    prefix = '┌───' + label
    return f"{color}{prefix}{'─' * max(0, INNER + 2 - vlen(prefix) - 1)}┐{RST}"
def boxMid(c, color): return f"{color}│{RST}{pad(c, INNER)}{color}│{RST}"
def boxBot(color): return f"{color}└{'─' * INNER}┘{RST}"
def headerTop(c): return f"{c}╭{'─' * INNER}╮{RST}"
def headerMid(c, col): return f"{col}│{RST}{pad(c, INNER)}{col}│{RST}"
def headerBot(c): return f"{c}╰{'─' * INNER}╯{RST}"

ORIGIN_HOST = 'cryptoadpay.com'
HOST = f"https://{ORIGIN_HOST}"
SITEKEY = '55504660-6a22-42c4-b5dc-9ad08fe4cb10'
DEF_UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'
BITCO_HOST = 'bitcotasks.com'
BITCO_ORIGIN = f"https://{BITCO_HOST}"

DEBUG = False
FAUCET_MIN_WAIT = 70
FAUCET_MAX_WAIT = 75
FAUCET_BATCH = 10
BITCO_BATCH = 20

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
COOKIE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')

PROVIDERS = {
    'skibidixxx': {
        'id': 'skibidixxx', 'name': 'Skibidixxx',
        'host': 'api.waryono.my.id', 'proto': 'https', 'port': 443,
        'submitUrl': '/in.php', 'pollUrl': '/res.php',
        'submitType': 'json', 'submitKey': 'apikey', 'pollKey': 'apikey',
        'pollMethod': 'GET', 'pollActionKey': 'action', 'pollActionValue': 'get', 'pollIdKey': 'id',
        'methodField': 'methods',
        'imageMethod': 'bitcogif', 'imageMethodLabel': 'Bitcogif', 'imageKey': 'base64',
        'hcaptcha': {'sitekeyParam': 'sitekey', 'domainParam': 'domain'}
    }
}

SOLVER_ERROR_MAP = {
    'ERROR_WRONG_USER_KEY': {'kind': 'fatal', 'msg': 'Wrong User Key'},
    'ERROR_KEY_DOES_NOT_EXIST': {'kind': 'fatal', 'msg': 'Key Does Not Exist'},
    'ERROR_ZERO_BALANCE': {'kind': 'fatal', 'msg': 'Zero Balance'},
    'ERROR_INVALID_METHOD': {'kind': 'fatal', 'msg': 'Invalid Method'},
    'ERROR_WRONG_METHOD': {'kind': 'fatal', 'msg': 'Wrong Method'},
    'ERROR_SOLVER_OFFLINE': {'kind': 'fatal', 'msg': 'Solver Offline'},
    'ERROR_PROXY_CONNECTION_FAILED': {'kind': 'fatal', 'msg': 'Proxy Failed'},
    'ERROR_METHOD_NOT_SPECIFIED': {'kind': 'fatal', 'msg': 'Method Not Specified'},
    'ERROR_CAPTCHA_UNSOLVABLE': {'kind': 'retry', 'msg': 'Unsolvable'},
    'ERROR_CAPTCHA_TIMEOUT': {'kind': 'retry', 'msg': 'Timeout'},
    'ERROR_BAD_DATA': {'kind': 'retry', 'msg': 'Bad Data'},
    'ERROR_BAD_PARAMETERS': {'kind': 'retry', 'msg': 'Bad Params'},
    'ERROR_WRONG_ID': {'kind': 'retry', 'msg': 'Wrong ID'},
    'ERROR_INVALID_IMAGE': {'kind': 'retry', 'msg': 'Invalid Image'},
    'ERROR_EMPTY_IMAGE_DATA': {'kind': 'retry', 'msg': 'Empty Image'},
    'ERROR_RATE_LIMIT': {'kind': 'rate', 'msg': 'Rate Limit'},
    'ERROR_TOO_MANY_REQUESTS': {'kind': 'rate', 'msg': 'Too Many Requests'},
    'ERROR_NO_SLOT_AVAILABLE': {'kind': 'rate', 'msg': 'No Slot'},
    'ERROR_REQUEST_COOLDOWN': {'kind': 'rate', 'msg': 'Cooldown'},
    'ERROR_INTERNAL_SERVER': {'kind': 'server', 'msg': 'Internal Server'},
    'ERROR_INTERNAL_SERVER_ERROR': {'kind': 'server', 'msg': 'Internal Server'},
    'ERROR_DATABASE_CONNECTION_FAILED': {'kind': 'server', 'msg': 'DB Connection'},
    'CAPCHA_NOT_READY': {'kind': 'polling', 'msg': 'Not ready'},
    'CAPTCHA_NOT_READY': {'kind': 'polling', 'msg': 'Not ready'},
    'ERROR_CAPTCHA_NOT_READY': {'kind': 'polling', 'msg': 'Not ready'}
}

def classifySolverError(code):
    up = str(code or '').upper().strip()
    if not up: return None
    if up in SOLVER_ERROR_MAP: return SOLVER_ERROR_MAP[up]
    for k in SOLVER_ERROR_MAP:
        if k in up: return SOLVER_ERROR_MAP[k]
    return None

# ===============================================================
#  STATE & SPINNER
# ===============================================================
PROVIDER = ''
API_KEY = ''
STOP_SIGNAL = False
SESSION_BEARER = ''
SESSION_COOKIE = ''

spin_lock = threading.Lock()
spin_paused = False
spin_stopped = False
spin_label = ''
spin_timeout = 300
spin_start_time = 0

def spin_worker():
    global spin_paused, spin_stopped
    i = 0
    SYMBOLS = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑']
    SPINNERS = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
    SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
    DOTS = ['▪','▪▪','▪▪▪','▪▪▪▪']
    
    while not spin_stopped and not STOP_SIGNAL:
        if not spin_paused:
            elapsed = int((time.time() - spin_start_time))
            pct = min(100, int((elapsed / spin_timeout) * 100)) if spin_timeout else 0
            sym = SYMBOLS[i % len(SYMBOLS)]
            sp = SPINNERS[i % len(SPINNERS)]
            sp1 = SPINNERS1[i % len(SPINNERS1)]
            dot = DOTS[elapsed % len(DOTS)]
            i += 1
            c1 = 1 + random.randint(0, 6)
            c2 = 1 + random.randint(0, 6)
            mm = f"{elapsed // 60:02d}"
            ss = f"{elapsed % 60:02d}"
            
            sys.stdout.write(f"{CLR} \x1b[1;3{c1}m {sp}\x1b[1;37m {spin_label} \x1b[1;31m{mm}:{ss}\x1b[1;3{c2}m {sym} {sp1}\x1b[1;37m {pct}%\x1b[1;33m {dot}")
            sys.stdout.flush()
        time.sleep(0.1)

def startSpinner(label, timeout=300):
    global spin_paused, spin_stopped, spin_label, spin_timeout, spin_start_time
    with spin_lock:
        spin_paused = False
        spin_stopped = False
        spin_label = label
        spin_timeout = timeout
        spin_start_time = time.time()
    t = threading.Thread(target=spin_worker, daemon=True)
    t.start()
    return t

def stopSpinner():
    global spin_stopped
    with spin_lock:
        spin_stopped = True
    sys.stdout.write(CLR)
    sys.stdout.flush()

def pauseSpinner():
    global spin_paused
    with spin_lock:
        spin_paused = True
    sys.stdout.write(CLR)
    sys.stdout.flush()

def resumeSpinner():
    global spin_paused
    with spin_lock:
        spin_paused = False

def sleep(ms): time.sleep(ms / 1000.0)
def now(): return datetime.now().strftime('%H:%M:%S')
def clear(): os.system('cls' if os.name == 'nt' else 'clear')

def log(msg, tag='i'):
    icons = {'i': f"{CYN}»{RST}", 'ok': f"{GRN}✓{RST}", 'er': f"{RED}✗{RST}", 'wr': f"{YEL}⚠{RST}", 'in': f"{BLU}●{RST}", 'or': f"{ORG}●{RST}", 'dbg': f"{MAG}⚙{RST}", 'limit': f"{RED}✗{RST}"}
    icon = icons.get(tag, icons['i'])
    textColor = RED if tag in ['wr', 'er', 'limit'] else WHT
    pauseSpinner()
    print(f"{WHT}[{now()}]{RST} {icon} {textColor}{msg}{RST}")
    resumeSpinner()

def claimOut(msg):
    pauseSpinner()
    print(f"{WHT}[{now()}]{RST} {GRN}{msg}{RST}")
    resumeSpinner()

def claimOutLine(msg):
    pauseSpinner()
    print(msg)
    resumeSpinner()

def logPlain(m):
    pauseSpinner()
    print(m)
    resumeSpinner()

def blinkErr(message, durationMs=2000):
    start = time.time() * 1000
    on = True
    pauseSpinner()
    while (time.time() * 1000 - start) < durationMs:
        if STOP_SIGNAL: break
        if on: sys.stdout.write(f"{CLR}{RED}[{now()}] ✗ {str(message).upper()}{RST}")
        else: sys.stdout.write(CLR)
        sys.stdout.flush()
        on = not on
        sleep(250)
    sys.stdout.write(CLR)
    sys.stdout.flush()
    resumeSpinner()

def blinkWarn(message, durationMs=2000):
    start = time.time() * 1000
    on = True
    pauseSpinner()
    while (time.time() * 1000 - start) < durationMs:
        if STOP_SIGNAL: break
        if on: sys.stdout.write(f"{CLR}{YEL}[{now()}] ⚠ {message}{RST}")
        else: sys.stdout.write(CLR)
        sys.stdout.flush()
        on = not on
        sleep(250)
    sys.stdout.write(CLR)
    sys.stdout.flush()
    resumeSpinner()

def tmr(seconds, label='Waiting...'):
    total = int(seconds)
    if total < 1: return
    start = time.time()
    i = 0
    SYMBOLS = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑']
    SPINNERS = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
    SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','⣇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
    DOTS = ['▪','▪▪','▪▪▪','▪▪▪▪']
    
    while True:
        if STOP_SIGNAL: break
        elapsed = int(time.time() - start)
        remaining = max(0, total - elapsed)
        pct = int(((total - remaining) / total) * 100)
        mm = f"{remaining // 60:02d}"
        ss = f"{remaining % 60:02d}"
        sym = SYMBOLS[i % len(SYMBOLS)]
        sp = SPINNERS[i % len(SPINNERS)]
        sp1 = SPINNERS1[i % len(SPINNERS1)]
        dot = DOTS[elapsed % len(DOTS)]
        i += 1
        c1 = 1 + random.randint(0, 6)
        c2 = 1 + random.randint(0, 6)
        
        sys.stdout.write(f"{CLR} \x1b[1;3{c1}m {sp}\x1b[1;37m {label} \x1b[1;31m{mm}:{ss}\x1b[1;3{c2}m {sym} {sp1}\x1b[1;37m {pct}%\x1b[1;33m {dot}")
        sys.stdout.flush()
        
        if remaining <= 0: break
        sleep(100)
    sys.stdout.write(CLR)
    sys.stdout.flush()

def withSpinner(label, fn, timeout=300):
    startSpinner(label, timeout)
    try:
        r = fn()
        stopSpinner()
        return r
    except Exception as e:
        stopSpinner()
        raise e

# ===============================================================
#  CONFIG
# ===============================================================
def defaultConfig():
    return {'provider': '', 'apikeys': {}, 'email': '', 'password': '', 'userAgent': '', 'cookie': '', 'bitcotasksLink': ''}

def saveConfig(cfg):
    with open(CONFIG_PATH, 'w') as f: json.dump(cfg, f, indent=2)

def loadConfig():
    if not os.path.exists(CONFIG_PATH): return None
    try:
        with open(CONFIG_PATH, 'r') as f: cfg = json.load(f)
        if 'apikeys' not in cfg: cfg['apikeys'] = {}
        for k in ['provider', 'userAgent', 'email', 'password', 'cookie', 'bitcotasksLink']:
            if k not in cfg: cfg[k] = ''
        return cfg
    except:
        return None

def getApiKey(provider):
    cfg = loadConfig()
    if not cfg or 'apikeys' not in cfg: return ''
    return cfg['apikeys'].get(provider, '')

def setApiKey(provider, key):
    cfg = loadConfig() or defaultConfig()
    if 'apikeys' not in cfg: cfg['apikeys'] = {}
    cfg['apikeys'][provider] = key
    if not cfg['provider']: cfg['provider'] = provider
    saveConfig(cfg)

def setActiveProvider(provider):
    cfg = loadConfig() or defaultConfig()
    cfg['provider'] = provider
    saveConfig(cfg)

def maskKey(k):
    if not k: return ''
    if len(k) <= 12: return k
    return k[:8] + '...' + k[-4:]

# ===============================================================
#  HTTP & COOKIE JAR
# ===============================================================
class CookieJar:
    def __init__(self):
        self.map = {}
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': DEF_UA})
        
    def set(self, host, set_cookie):
        if not set_cookie: return
        arr = set_cookie if isinstance(set_cookie, list) else [set_cookie]
        key = host.lower()
        if key not in self.map: self.map[key] = {}
        for sc in arr:
            kv = sc.split(';')[0]
            if '=' not in kv: continue
            name, value = kv.split('=', 1)
            name = name.strip()
            value = value.strip()
            if value == '' or 'expires=Thu, 01 Jan 1970' in sc:
                if name in self.map[key]: del self.map[key][name]
            else:
                self.map[key][name] = value

    def header(self, host):
        store = self.map.get(host.lower(), {})
        return '; '.join([f"{k}={v}" for k, v in store.items()])

    def save(self, file):
        try:
            with open(file, 'w') as f: json.dump(self.map, f, indent=2)
        except: pass

    def load(self, file):
        if not os.path.exists(file): return
        try:
            with open(file, 'r') as f: self.map = json.load(f)
        except: pass

jar = CookieJar()
jar.load(COOKIE_PATH)

def request(method, url, opts=None):
    if opts is None: opts = {}
    headers = opts.get('headers', {})
    body = opts.get('body')
    follow_redirect = opts.get('follow_redirect', True)
    max_redirects = opts.get('max_redirects', 5)
    timeout = opts.get('timeout', 45000) / 1000.0
    _redirect = opts.get('_redirect', 0)

    try:
        parsed = urllib.parse.urlparse(url)
    except:
        return {'status': 0, 'headers': {}, 'body': '', 'error': 'bad url'}

    final_headers = {**headers}
    final_headers['Host'] = parsed.netloc
    if 'User-Agent' not in final_headers: final_headers['User-Agent'] = DEF_UA
    if 'Accept-Encoding' not in final_headers: final_headers['Accept-Encoding'] = 'gzip, deflate'
    
    ck = jar.header(parsed.hostname)
    if ck: final_headers['Cookie'] = ck

    body_data = None
    if body is not None:
        if isinstance(body, bytes): body_data = body
        elif isinstance(body, str): body_data = body.encode('utf-8')
        elif isinstance(body, dict): body_data = urllib.parse.urlencode(body).encode('utf-8')

    try:
        res = requests.request(method, url, headers=final_headers, data=body_data, allow_redirects=False, timeout=timeout, verify=False)
        
        sc = res.headers.get('Set-Cookie')
        if sc: jar.set(parsed.hostname, sc)

        if follow_redirect and res.status_code in [301, 302, 303, 307, 308] and 'location' in res.headers and _redirect < max_redirects:
            next_url = urllib.parse.urljoin(url, res.headers['location'])
            next_method = 'GET' if (res.status_code == 303 or (res.status_code in [301, 302] and method == 'POST')) else method
            new_opts = {**opts, 'body': None if next_method == 'GET' else body, '_redirect': _redirect + 1}
            return request(next_method, next_url, new_opts)

        return {'status': res.status_code, 'headers': res.headers, 'body': res.text}
    except Exception as e:
        return {'status': 0, 'headers': {}, 'body': '', 'error': str(e)}

def buildMultipart(fields):
    boundary = '----WebKitFormBoundary' + ''.join(random.choices('0123456789abcdef', k=16))
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8'))
    parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'

def normalizeSolverResp(raw):
    text = (raw or '').strip()
    if not text: return {'status': 0, 'request': ''}
    if text.startswith('OK|'):
        payload = text[3:].strip()
        if payload in ['CAPCHA_NOT_READY', 'CAPTCHA_NOT_READY']: return {'status': 0, 'request': 'CAPCHA_NOT_READY'}
        return {'status': 1, 'request': payload}
    if text.startswith('{'):
        try:
            j = json.loads(text)
            ok = j.get('status') in [1, '1', 'OK']
            if ok: return {'status': 1, 'request': j.get('request') or j.get('result') or ''}
            return {'status': 0, 'request': j.get('request') or j.get('error') or j.get('message') or ''}
        except:
            pass
    return {'status': 0, 'request': text}

def buildSolverBody(p, fields):
    if p['submitType'] == 'json': return json.dumps(fields), 'application/json'
    if p['submitType'] == 'multipart': return buildMultipart(fields)
    return urllib.parse.urlencode(fields), 'application/x-www-form-urlencoded'

def solverSubmit(providerId, fields):
    p = PROVIDERS.get(providerId)
    if not p: raise Exception(f"Unknown provider: {providerId}")
    body, content_type = buildSolverBody(p, fields)
    res = request('POST', f"{p['proto']}://{p['host']}{p['submitUrl']}", {
        'headers': {'Content-Type': content_type, 'Accept': 'application/json'},
        'body': body, 'timeout': 30000
    })
    return normalizeSolverResp(res['body'])

def solverPoll(providerId, apikey, taskId):
    p = PROVIDERS.get(providerId)
    if not p: raise Exception(f"Unknown provider: {providerId}")
    params = urllib.parse.urlencode({
        p['pollKey']: apikey, p['pollActionKey']: p['pollActionValue'], p['pollIdKey']: taskId, 'json': '1'
    })
    url = f"{p['proto']}://{p['host']}{p['pollUrl']}"
    if p['pollMethod'] == 'POST':
        res = request('POST', url, {'headers': {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}, 'body': params, 'timeout': 30000})
    else:
        res = request('GET', f"{url}?{params}", {'headers': {'Accept': 'application/json'}, 'timeout': 30000})
    return normalizeSolverResp(res['body'])

def runSolver(providerId, methodLabel, payload, timeoutSec=180, maxAttempts=3):
    rawKey = getApiKey(providerId) or API_KEY
    if not rawKey: return None, 'NO_APIKEY'
    apikey = rawKey.strip()
    lastError = None
    attempt = 0
    unsolvableStreak = 0
    MAX_UNSOLVABLE = 5

    while True:
        if STOP_SIGNAL: return None, 'STOPPED'
        attempt += 1
        startSpinner(f"{PROVIDERS[providerId]['name']} {methodLabel}", timeoutSec)

        taskId = None
        try:
            sub = solverSubmit(providerId, payload)
            if STOP_SIGNAL: stopSpinner(); return None, 'STOPPED'
            if sub['status'] != 1 or not sub['request']:
                stopSpinner()
                raw = str(sub['request'] or 'SUBMIT_FAILED')
                info = classifySolverError(raw)
                if info and info['kind'] == 'fatal':
                    blinkErr(f"FATAL: {info['msg']}", 2500)
                    return None, raw
                lastError = raw
                blinkWarn(f"{info['msg'] if info else raw} — retry...", 1500)
                sleep(1500)
                continue
            taskId = sub['request']
        except Exception as e:
            stopSpinner()
            lastError = f"SUBMIT_NET:{str(e)}"
            blinkWarn('Network error — retry...', 1500)
            sleep(1500)
            continue

        pStart = time.time()
        outcome = None
        while time.time() - pStart < timeoutSec:
            if STOP_SIGNAL: stopSpinner(); return None, 'STOPPED'
            sleep(3000)
            try: r = solverPoll(providerId, apikey, taskId)
            except: continue
            
            if r['status'] == 1 and r['request']:
                outcome = {'type': 'success', 'token': r['request']}
                break
            raw = str(r['request'] or '')
            info = classifySolverError(raw)
            if info and info['kind'] == 'polling': continue
            if info and info['kind'] == 'fatal': outcome = {'type': 'fatal', 'error': raw, 'info': info}; break
            if info and info['kind'] == 'rate': outcome = {'type': 'rate', 'error': raw, 'info': info}; break
            if info and info['kind'] == 'server': outcome = {'type': 'server', 'error': raw, 'info': info}; break
            if info and info['kind'] == 'retry': outcome = {'type': 'retry', 'error': raw, 'info': info}; break
            if raw: outcome = {'type': 'retry', 'error': raw, 'info': None}; break

        stopSpinner()
        if not outcome: outcome = {'type': 'timeout', 'error': 'POLL_TIMEOUT'}
        if outcome['type'] == 'success': return outcome['token'], None
        if outcome['type'] == 'fatal':
            blinkErr(f"FATAL: {outcome['info']['msg']}", 2500)
            return None, outcome['error']

        lastError = outcome['error']
        if outcome['error'] == 'ERROR_CAPTCHA_UNSOLVABLE':
            unsolvableStreak += 1
            blinkErr('Error Unsolvable', 3000)
            if unsolvableStreak >= MAX_UNSOLVABLE:
                blinkErr(f"Unsolvable {MAX_UNSOLVABLE}x", 3000)
                return None, 'UNSOLVABLE_STREAK'
            sleep(500)
            continue
        unsolvableStreak = 0

        if attempt >= maxAttempts:
            info = classifySolverError(lastError)
            blinkErr(f"{info['msg'] if info else lastError or 'UNKNOWN'}", 2500)
            return None, lastError or 'EXHAUSTED'

        if outcome['type'] == 'rate':
            blinkWarn(f"{outcome['info']['msg']} — retry {attempt + 1}/{maxAttempts}", 1500)
            tmr(8, 'Rate limit...')
            continue
        if outcome['type'] == 'server':
            blinkWarn(f"{outcome['info']['msg']} — retry {attempt + 1}/{maxAttempts}", 1500)
            tmr(5, 'Server error...')
            continue

        msg = outcome['info']['msg'] if outcome['info'] else outcome['error']
        blinkWarn(f"{msg} — retry {attempt + 1}/{maxAttempts}", 1800)
        sleep(1500)

def solveHcaptcha(providerId, pageUrl, sitekey):
    p = PROVIDERS.get(providerId)
    if not p or 'hcaptcha' not in p: return None, 'NO_HCAPTCHA_METHOD'
    rawKey = getApiKey(providerId) or API_KEY
    if not rawKey: return None, 'NO_APIKEY'
    fields = {
        p['submitKey']: rawKey.strip(), p['methodField']: 'hcaptcha',
        p['hcaptcha']['sitekeyParam']: sitekey or SITEKEY,
        p['hcaptcha']['domainParam']: pageUrl or HOST, 'json': 1
    }
    return runSolver(providerId, '[hCaptcha]', fields, 180)

def solveImageCaptcha(providerId, imageBase64):
    p = PROVIDERS.get(providerId)
    if not p: return None, 'NO_PROVIDER'
    rawKey = getApiKey(providerId) or API_KEY
    if not rawKey: return None, 'NO_APIKEY'
    fields = {
        p['submitKey']: rawKey.strip(), p['methodField']: p['imageMethod'],
        p['imageKey']: imageBase64, 'json': 1
    }
    return runSolver(providerId, f"[{p['imageMethodLabel']}]", fields, 180)

# ===============================================================
#  PARSERS
# ===============================================================
def parseCoords(answer):
    if not answer: return None
    m = re.search(r'x["\'=:\s]*(\d+)\s*[,;].*?y["\'=:\s]*(\d+)', answer, re.I)
    if m: return {'x': int(m.group(1)), 'y': int(m.group(2))}
    m = re.match(r'^(\d+)\s*[,;]\s*(\d+)$', answer)
    if m: return {'x': int(m.group(1)), 'y': int(m.group(2))}
    return None

def parseCsrf(html):
    if not html: return None
    m = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)">', html)
    if m: return m.group(1)
    for pat in [r'name="_token"\s+value="([^"]+)"', r"name='_token'\s+value='([^']+)'", r'name="csrf_token_name"\s+value="([^"]+)"']:
        m = re.search(pat, html)
        if m: return m.group(1)
    return None

def detectSitekey(html):
    if not html: return None
    for pat in [r'data-sitekey="([^"]+)"', r'data-hcaptcha-sitekey="([^"]+)"', r'sitekey[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]']:
        m = re.search(pat, html)
        if m: return m.group(1)
    return None

def isLoggedIn(html):
    if not html: return False
    return 'action="https://cryptoadpay.com/logout"' in html or '/logout' in html or '>Logout<' in html

def isLimitReached(html):
    if not html: return False
    hasClaimForm = 'action="/faucet/claim"' in html or 'action="https://cryptoadpay.com/faucet/claim"' in html
    if hasClaimForm: return False
    if 'Daily limit reached' in html or 'Limit reached' in html or 'limit reached' in html or '200/200' in html: return True
    return False

def isFaucetPaused(html):
    if not html: return False
    return 'Faucet Paused' in html or 'Complete the pause requirements' in html

def parseFaucetPause(html):
    if not html: return {'current': 0, 'max': 20}
    m = re.search(r'<span>Pause Progress</span><span>(\d+)\/(\d+)</span>', html, re.I)
    if m: return {'current': int(m.group(1)), 'max': int(m.group(2))}
    return {'current': 0, 'max': 20}

def isFaucetSuccess(html):
    if not html: return False
    return bool(re.search(r'flashType\s*=\s*"success"', html) or 'added to your balance' in html or 'Good job' in html)

def extractFlashMessage(html):
    if not html: return None
    fm = re.search(r'var\s+flashMessage\s*=\s*"([^"]+)"', html)
    if not fm: return None
    rawMsg = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), fm.group(1))
    return re.sub(r'<[^>]+>', ' ', rawMsg).strip()

def getFaucetRemainingTime(html):
    if not html: return None
    m = re.search(r'var\s+remainingTime\s*=\s*(\d+)\s*;', html)
    return int(m.group(1)) if m else None

def parseBalanceFromJson(body):
    try:
        j = json.loads(body)
        if j.get('success') and j.get('balance'):
            m = re.search(r'([\d,]+\.\d+)', str(j['balance']))
            if m: return float(m.group(1).replace(',', ''))
    except: pass
    return None

def parseBalanceFromHtml(html):
    if not html: return None
    m = re.search(r'Account Balance[^0-9]*([\d,]+\.\d+)', html, re.I)
    if m: return float(m.group(1).replace(',', ''))
    return None

def randomFaucetWait():
    return FAUCET_MIN_WAIT + random.randint(0, FAUCET_MAX_WAIT - FAUCET_MIN_WAIT)

def refreshBalance():
    try:
        r = request('GET', f"{HOST}/get-balance", {'headers': {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}, 'maxRedirects': 5})
        if r['status'] == 200:
            bal = parseBalanceFromJson(r['body'])
            if bal is not None: return bal
    except: pass
    try:
        r = request('GET', f"{HOST}/dashboard", {'maxRedirects': 5})
        if isLoggedIn(r['body']):
            bal = parseBalanceFromHtml(r['body'])
            if bal is not None: return bal
    except: pass
    return None

def ensureLoggedIn(cfg):
    # Coba pake cookie yang ada
    r = request('GET', f"{HOST}/dashboard", {'maxRedirects': 5})
    if isLoggedIn(r['body']):
        return {'ok': True, 'html': r['body']}

    log('Session expired / Cookie invalid.', 'wr')
    print(f"{WHT}Silakan copy 'Cookie' dari browser / Reqable.{RST}")
    print(f"{CYN}Contoh: XSRF-TOKEN=xxx; cryptoadpay_session=yyy; remember_web_zzz=...;{RST}")
    
    new_cookie = askQuestion(f"  {YEL}▸{RST} {WHT}Paste Cookie : {RST}").strip()
    
    if not new_cookie:
        blinkErr('Cookie kosong, batal.', 2000)
        return {'ok': False}

    cfg['cookie'] = new_cookie
    saveConfig(cfg)
    
    jar.map.clear()
    for p in new_cookie.split(';'):
        t = p.strip()
        if t: jar.set(ORIGIN_HOST, [t])

    r = request('GET', f"{HOST}/dashboard", {'maxRedirects': 5})
    if isLoggedIn(r['body']):
        log('Cookie baru berhasil dipasang!', 'ok')
        return {'ok': True, 'html': r['body']}
    
    blinkErr('Cookie masih invalid / expired.', 2500)
    return {'ok': False}

# ===============================================================
#  FAUCET & BITCO
# ===============================================================
def runFaucet(cfg):
    hdr = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'}
    claimCount = 0
    target = FAUCET_BATCH
    oldBal = refreshBalance()

    while not STOP_SIGNAL and claimCount < target:
        try:
            r = request('GET', f"{HOST}/faucet", {'headers': hdr, 'maxRedirects': 5})
            if STOP_SIGNAL: return {'count': claimCount, 'paused': False, 'limited': False}
            html = r['body']

            if not isLoggedIn(html):
                res = ensureLoggedIn(cfg)
                if not res['ok']:
                    log('Re-login gagal', 'er')
                    return {'count': claimCount, 'paused': False, 'limited': False}
                continue

            if isFaucetPaused(html):
                prog = parseFaucetPause(html)
                print('')
                log('Faucet Paused!', 'wr')
                return {'count': claimCount, 'paused': True, 'current': prog['current'], 'max': prog['max'], 'limited': False}

            if isLimitReached(html):
                print('')
                log('Faucet limit reached (200/200)', 'limit')
                return {'count': claimCount, 'paused': False, 'limited': True}

            if isFaucetSuccess(html):
                claimCount += 1
                nb = refreshBalance()
                successMsg = extractFlashMessage(html) or 'added to your balance!'
                claimOut(f"✓ [{claimCount}/{target}] {successMsg}")
                if nb is not None:
                    claimOutLine(f"{WHT}[{now()}]{RST} {MAG}»{RST} New Balance: {YEL}{nb:.2f}{RST}")
                    oldBal = nb
                if claimCount >= target: break
                tmr(randomFaucetWait(), 'Waiting...')
                continue

            remaining = getFaucetRemainingTime(html)
            csrf = parseCsrf(html)
            sitekey = detectSitekey(html) or SITEKEY
            hasClaimForm = 'action="/faucet/claim"' in html or 'action="https://cryptoadpay.com/faucet/claim"' in html

            if remaining is not None and remaining > 0:
                tmr(remaining + 3 + random.randint(0, 3), 'Cooldown faucet...')
                continue
            if not hasClaimForm or not csrf:
                tmr(10, 'Waiting faucet ready...')
                continue

            capToken, capErr = solveHcaptcha(PROVIDER, f"{HOST}/faucet", sitekey)
            if STOP_SIGNAL: return {'count': claimCount, 'paused': False, 'limited': False}
            if not capToken:
                sleep(3000)
                continue

            payload = urllib.parse.urlencode({'_token': csrf, 'g-recaptcha-response': capToken, 'h-captcha-response': capToken})
            r2 = request('POST', f"{HOST}/faucet/claim", {
                'headers': {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': f"{HOST}/faucet", 'Origin': HOST},
                'body': payload, 'maxRedirects': 0
            })
            if STOP_SIGNAL: return {'count': claimCount, 'paused': False, 'limited': False}

            finalHtml = r2['body']
            if r2['status'] == 302 and 'location' in r2['headers']:
                loc = r2['headers']['location']
                followUrl = loc if loc.startswith('http') else f"{HOST}{loc}"
                followRes = request('GET', followUrl, {'headers': hdr, 'maxRedirects': 5})
                if STOP_SIGNAL: return {'count': claimCount, 'paused': False, 'limited': False}
                finalHtml = followRes['body']

            if isFaucetSuccess(finalHtml):
                claimCount += 1
                nb = refreshBalance()
                successMsg = extractFlashMessage(finalHtml) or 'added to your balance!'
                claimOut(f"✓ [{claimCount}/{target}] {successMsg}")
                if nb is not None:
                    claimOutLine(f"{WHT}[{now()}]{RST} {MAG}»{RST} New Balance: {YEL}{nb:.2f}{RST}")
                    oldBal = nb
                if claimCount >= target: break
                tmr(randomFaucetWait(), 'Waiting...')
                continue

            if isLimitReached(finalHtml):
                log('Faucet limit reached (200/200)', 'limit')
                return {'count': claimCount, 'paused': False, 'limited': True}

            msg = extractFlashMessage(finalHtml) or f"HTTP {r2['status']}"
            log(f"Faucet: {msg}", 'wr')
            tmr(randomFaucetWait(), 'Waiting...')
        except Exception as e:
            log(f"Faucet err: {e}", 'er')
            sleep(5000)

    return {'count': claimCount, 'paused': False, 'limited': False}

def parseOfferwallUrl(url):
    try:
        p = urllib.parse.urlparse(url)
        seg = p.path.strip('/').split('/')
        if seg[0] != 'offerwall' or len(seg) < 3: return None
        return {'key': seg[1], 'subId': seg[2], 'hash': seg[3] if len(seg) > 3 else None}
    except: return None

def getAutoBitcoLink():
    paths = ['/offerwall/bitcotasks', '/offerwalls', '/earn', '/dashboard']
    for p in paths:
        if STOP_SIGNAL: return None
        try:
            r = request('GET', f"{HOST}{p}", {'maxRedirects': 5})
            if isLoggedIn(r['body']):
                match = re.search(r'https://bitcotasks\.com/offerwall/[a-zA-Z0-9_/\-]+', r['body'], re.I)
                if match: return match.group(0)
        except: pass
    return None

def pickVar(html, name):
    pats = [
        rf'(?:var|let|const)\s+{name}\s*=\s*[\'"]([^\'"]+)[\'"]',
        rf'data-{name.replace("_", "-")}\s*=\s*[\'"]([^\'"]+)[\'"]',
        rf'"{name}"\s*:\s*"([^"]+)"'
    ]
    for p in pats:
        m = re.search(p, html)
        if m: return m.group(1)
    return None

def solveBitcoCaptcha(html, pageUrl):
    jsUrl = None
    for pat in [r'<script[^>]+src=["\'](\/captcha2\/[^"\']+\.js\?[^"\']+)["\']', r'src=["\'](\/captcha2\/[^"\']+)["\']', r'["\'](\/captcha2\/[a-f0-9]+\.js[^"\']*)["\']']:
        m = re.search(pat, html, re.I)
        if m:
            jsUrl = urllib.parse.urljoin(pageUrl, m.group(1))
            break
    if not jsUrl:
        log('Captcha JS tidak ditemukan', 'wr')
        return None

    jsRes = request('GET', jsUrl, {'headers': {'Accept': '*/*', 'Referer': pageUrl, 'Sec-Fetch-Dest': 'script', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-origin'}})
    if STOP_SIGNAL: return None
    js = jsRes['body']
    if not js or len(js) < 50:
        log('Captcha JS empty', 'wr')
        return None

    p = None
    for pat in [r'(?:var|let|const)\s+payload\s*=\s*["\']([A-Za-z0-9_]+)=([^"\'&]*)&([A-Za-z0-9_]+)=["\']', r'payload\s*[:=]\s*["\']([A-Za-z0-9_]+)=([^"\'&]*)&([A-Za-z0-9_]+)=']:
        p = re.search(pat, js)
        if p: break
    if not p:
        log('Captcha pattern invalid', 'wr')
        return None
    fn1, fv, fn2 = p.group(1), p.group(2), p.group(3)

    sMatch = re.search(r'if\s*\(\s*response\.([A-Za-z0-9_]+)\s*\)', js) or re.search(r'response\.([A-Za-z0-9_]+)', js)
    if not sMatch:
        log('Captcha pattern invalid', 'wr')
        return None
    successField = sMatch.group(1)

    allResp = [m.group(1) for m in re.finditer(r'=\s*response\.([A-Za-z0-9_]+)', js)]
    tokenField = next((f for f in allResp if f != successField), None)
    if not tokenField:
        log('Captcha pattern invalid', 'wr')
        return None

    vMatch = re.search(r'\/captcha2\/([a-zA-Z0-9_]+)\?action=data&cdata=([a-f0-9]+)', js)
    if not vMatch:
        log('Captcha pattern invalid', 'wr')
        return None
    verifyShort, cdata = vMatch.group(1), vMatch.group(2)

    dMatch = re.search(r'getElementById\(\s*["\']([^"\']+)["\']\s*\)\s*\.\s*value\s*=\s*response\.', js)
    dynamicField = dMatch.group(1) if dMatch else None

    prov = PROVIDERS.get(PROVIDER)
    solvingLabel = f"{prov['name']} [{prov['imageMethodLabel']}]"

    for attempt in range(1, 4):
        if STOP_SIGNAL: return None
        imgRes = request('POST', jsUrl, {
            'headers': {'Content-Type': 'application/json', 'Accept': '*/*', 'Referer': pageUrl, 'X-Requested-With': 'XMLHttpRequest'},
            'body': json.dumps({'t': int(time.time()*1000), 'r': random.random()})
        })
        if STOP_SIGNAL: return None
        try: imgJson = json.loads(imgRes['body'])
        except: continue
        
        if 'error' in imgJson:
            if imgJson['error'] == 'rate_limited':
                tmr(imgJson.get('retryAfter', 60), 'Rate limited')
                continue
            log(f"Captcha api: {imgJson['error']}", 'wr')
            continue

        image = imgJson.get('image') or imgJson.get('gif') or imgJson.get('preload') or ''
        if len(image) < 100:
            log('Image kosong', 'wr')
            continue

        answer, err = withSpinner(solvingLabel, lambda: solveImageCaptcha(PROVIDER, image), 600)
        if STOP_SIGNAL: return None
        if not answer:
            blinkWarn(err or 'Solver gagal', 2000)
            continue

        coords = parseCoords(answer)
        if not coords:
            log('Parse coords fail', 'wr')
            continue

        submitBody = f"{fn1}={urllib.parse.quote(fv)}&{fn2}={urllib.parse.quote(f'[{coords["x"]},{coords["y"]}]')}"
        verifyUrl = urllib.parse.urljoin(pageUrl, f"/captcha2/{verifyShort}?action=data&cdata={cdata}")

        subRes = request('POST', verifyUrl, {
            'headers': {'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN, 'Referer': pageUrl},
            'body': submitBody
        })
        if STOP_SIGNAL: return None
        try: subJson = json.loads(subRes['body'])
        except: continue
        
        if not subJson.get(successField):
            log('Submit invalid', 'wr')
            continue
        captchaToken = subJson.get(tokenField)
        if not captchaToken:
            log('Token kosong', 'wr')
            continue
        return {'token': captchaToken, 'field': dynamicField}
    return None

def bypassFirewall(owUrl):
    if STOP_SIGNAL: return None
    r1 = request('GET', owUrl, {'headers': {'Accept': 'text/html'}, 'follow_redirect': False})
    if STOP_SIGNAL: return None
    if r1['status'] == 0:
        log(f"net error: {r1.get('error')}", 'er')
        return None
    firewallUrl = None
    redir = re.search(r'window\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]', r1['body'])
    if redir: firewallUrl = urllib.parse.urljoin(owUrl, redir.group(1))
    elif 'firewall.php' in owUrl: firewallUrl = owUrl
    
    if not firewallUrl: return {'html': r1['body'], 'url': owUrl}

    fwRes = request('GET', firewallUrl, {'headers': {'Accept': 'text/html'}})
    if STOP_SIGNAL: return None
    fwHtml = fwRes['body']
    ctnMatch = re.search(r'const\s+captchaTokenName\s*=\s*"([^"]+)"', fwHtml)
    if not ctnMatch: return {'html': fwHtml, 'url': firewallUrl}
    ctn = ctnMatch.group(1)

    log('Firewall captcha...', 'in')
    cap = solveBitcoCaptcha(fwHtml, firewallUrl)
    if STOP_SIGNAL: return None
    if not cap or not cap['token']:
        blinkWarn('Firewall captcha gagal', 2500)
        return None

    valRes = request('POST', firewallUrl, {
        'headers': {'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'},
        'body': urllib.parse.urlencode({'action': 'validate', ctn: cap['token']})
    })
    if STOP_SIGNAL: return None
    
    try: vj = json.loads(valRes['body'])
    except: vj = {}
    
    nextUrl = None
    if vj.get('status') == 'success' and vj.get('redirect'):
        nextUrl = urllib.parse.urljoin(BITCO_ORIGIN, vj['redirect'])
    else:
        m = re.search(r'window\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]', valRes['body'])
        if m: nextUrl = urllib.parse.urljoin(BITCO_ORIGIN, m.group(1))
        
    if not nextUrl:
        blinkWarn('Firewall validate gagal', 2500)
        return None

    finalRes = request('GET', nextUrl, {'headers': {'Accept': 'text/html'}})
    if STOP_SIGNAL: return None
    return {'html': finalRes['body'], 'url': nextUrl}

def processBitcoTask(task, owUrl, owToken, idx, total):
    log(f"{YEL}TASK {idx}/{total}{RST} — {CYN}{task.get('title', 'Unknown')}{RST} {GRN}+{task.get('reward', 0)}{RST}", 'i')

    initRes = withSpinner('Init transaction...', lambda: request('POST', owUrl, {
        'headers': {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN},
        'body': urllib.parse.urlencode({'hash': task.get('hash', ''), 'sid': task.get('sid', ''), 'key': task.get('key', ''), 'type': 'ptc', 'token': owToken, 'action': 'init_transaction'})
    }), 15)
    if STOP_SIGNAL: return False

    try: initJson = json.loads(initRes['body'])
    except:
        log('init parse fail', 'er')
        return False
    
    if not initJson.get('offer'):
        log('no offer', 'er')
        return False
    offerUrl = initJson['offer']

    leadRes = request('GET', offerUrl, {'headers': {'Accept': 'text/html'}})
    if STOP_SIGNAL: return False
    leadHtml = leadRes['body']
    
    vars = {
        'token': pickVar(leadHtml, 'token'),
        'hash': pickVar(leadHtml, 'hash'),
        'subId': pickVar(leadHtml, 'sub_id'),
        'key': pickVar(leadHtml, 'key') or pickVar(leadHtml, 'api_key'),
        'ctoken': pickVar(leadHtml, 'ctoken')
    }
    if not vars['token'] or not vars['hash'] or not vars['subId'] or not vars['key']:
        log('vars missing', 'er')
        return False

    request('GET', f"{BITCO_ORIGIN}/firewall.php?key={urllib.parse.quote(vars['key'])}&sub_id={urllib.parse.quote(vars['subId'])}", {'headers': {'X-Requested-With': 'XMLHttpRequest', 'Accept': '*/*'}})
    if STOP_SIGNAL: return False

    log('Captcha challenge...', 'in')
    cap = solveBitcoCaptcha(leadHtml, offerUrl)
    if STOP_SIGNAL: return False
    if not cap or not cap['token']: return False

    log('start_view...', 'in')
    def do_start_view():
        return request('POST', offerUrl, {
            'headers': {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN, 'Accept': '*/*', 'Referer': offerUrl, 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'},
            'body': 'action=start_view'
        })
    
    svRes = do_start_view()
    if STOP_SIGNAL: return False

    if svRes['status'] == 429:
        tmr(6, 'Retry 429')
        do_start_view()
        if STOP_SIGNAL: return False

    duration = 30
    dm = re.search(r'(?:var|let|const)\s+duration\s*=\s*(\d+)', leadHtml)
    if dm:
        parsed = int(dm.group(1))
        if 5 <= parsed <= 300: duration = parsed
        
    tmr(duration + 5, f"⏳ Ad running ({duration}s)")
    if STOP_SIGNAL: return False

    dynField = cap.get('field') or vars.get('ctoken')
    if not dynField: return False

    confirmParams = {
        'action': 'proccessLead', 'hash': vars['hash'], 'key': vars['key'], 'sub_id': vars['subId'], 'sid': vars['subId'], 'token': vars['token']
    }
    confirmParams[dynField] = cap['token']

    confirmRes = withSpinner('Submitting...', lambda: request('POST', f"{BITCO_ORIGIN}/system/ajax.php", {
        'headers': {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN, 'Accept': '*/*', 'Referer': offerUrl, 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'},
        'body': urllib.parse.urlencode(confirmParams)
    }), 30)
    if STOP_SIGNAL: return False

    try: cj = json.loads(confirmRes['body'])
    except:
        log('parse fail', 'er')
        return False

    if cj.get('status') == 200 and cj.get('success') is not False:
        claimOut(f"✓ [{idx}/{total}] +{task.get('reward')} coins")
        if cj.get('redirect'):
            request('GET', cj['redirect'], {'headers': {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Referer': offerUrl, 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site'}, 'timeout': 15000, 'follow_redirect': True, 'max_redirects': 3})
        sleep(2000)
        return True
        
    log(f"❌ Gagal: status={cj.get('status')}", 'er')
    return False

def runBitcotasks(cfg, targetSuccess):
    if not cfg.get('bitcotasksLink'):
        log('Bitcotasks link belum di-set', 'wr')
        return 0
    parsed = parseOfferwallUrl(cfg['bitcotasksLink'])
    if not parsed:
        log('Bitcotasks link invalid', 'er')
        return 0

    owUrl = f"{BITCO_ORIGIN}/offerwall/{parsed['key']}/{parsed['subId']}"
    log('Loading offerwall...', 'or')
    fw = bypassFirewall(owUrl)
    if STOP_SIGNAL: return 0
    if not fw:
        blinkWarn('Firewall bypass failed', 2500)
        return 0

    tm = re.search(r'var\s+token\s*=\s*[\'"]([^\'"]+)[\'"]', fw['html'])
    if not tm:
        blinkWarn('Offerwall token tidak ditemukan', 2500)
        return 0
    owToken = tm.group(1)
    log('Firewall bypassed', 'ok')

    log('Fetching PTC tasks...', 'in')
    swRes = withSpinner('switch_cat ptc...', lambda: request('POST', fw['url'], {
        'headers': {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN},
        'body': urllib.parse.urlencode({'token': owToken, 'action': 'switch_cat', 'type': 'ptc'})
    }), 20)
    if STOP_SIGNAL: return 0

    try: sj = json.loads(swRes['body'])
    except:
        log('switch_cat parse fail', 'er')
        return 0
    
    tasks = sj.get('items', [])
    if not tasks:
        log('No PTC tasks available', 'wr')
        return 0

    log(f"Found {len(tasks)} tasks (target: {targetSuccess} sukses)", 'ok')
    ok, fail = 0, 0
    MAX_RETRY = 5

    for i in range(len(tasks)):
        if ok >= targetSuccess or STOP_SIGNAL: break
        success = False
        attempt = 0
        while attempt <= MAX_RETRY and not STOP_SIGNAL:
            success = processBitcoTask(tasks[i], fw['url'], owToken, i + 1, len(tasks))
            if STOP_SIGNAL: break
            if success: break
            attempt += 1
            if attempt <= MAX_RETRY: sleep(1500)
        if STOP_SIGNAL: break
        if success: ok += 1
        else: fail += 1
        jar.save(COOKIE_PATH)
        if i < len(tasks) - 1 and ok < targetSuccess:
            tmr(6 + random.randint(0, 3), 'Delay')

    return ok

def runFullCycle(cfg):
    while not STOP_SIGNAL:
        faucetRes = runFaucet(cfg)
        if STOP_SIGNAL: break
        log(f"Faucet cycle selesai: {faucetRes['count']}/{FAUCET_BATCH} claim", 'ok')

        if faucetRes['limited']:
            print('')
            askQuestion(f"{WHT}  Press Enter to return to menu...{RST}")
            break

        targetBitco = BITCO_BATCH
        if faucetRes['paused']:
            needed = faucetRes['max'] - faucetRes['current']
            if needed > 0:
                log(f"Butuh {needed} task Bitcotasks lagi untuk unpause Faucet.", 'wr')
                targetBitco = needed
            else:
                log("Pause progress penuh tapi faucet masih pause?", 'wr')

        tmr(5, 'Transisi ke Bitcotasks...')
        if STOP_SIGNAL: break

        autoLink = getAutoBitcoLink()
        if STOP_SIGNAL: break

        if autoLink:
            cfg['bitcotasksLink'] = autoLink
            saveConfig(cfg)
        else:
            if not cfg.get('bitcotasksLink'):
                log('Gagal auto-find & link belum diset. Masukkan manual:', 'wr')
                inp = askQuestion('Bitcotasks Link : ').strip()
                if inp:
                    cfg['bitcotasksLink'] = inp
                    saveConfig(cfg)
                else:
                    blinkErr('Link invalid. Cycle berhenti.', 2000)
                    break
            else:
                log('Auto-find gagal, pakai link tersimpan.', 'wr')

        bitcoCount = runBitcotasks(cfg, targetBitco)
        if STOP_SIGNAL: break
        log(f"Bitcotasks cycle selesai: {bitcoCount}/{targetBitco} sukses", 'ok')

        tmr(10, 'Transisi ke Faucet...')

# ===============================================================
#  MENU & MAIN
# ===============================================================
def askQuestion(q):
    try:
        return input(q)
    except KeyboardInterrupt:
        global STOP_SIGNAL
        if not STOP_SIGNAL:
            STOP_SIGNAL = True
            print(f"{CLR}\n{YEL}⚠ Dihentikan. Kembali ke menu...{RST}")
        else:
            print(f"\n{RED}Program keluar.{RST}")
            sys.exit(0)
        return ''

def bannerMain():
    print(headerTop(CYN))
    print(headerMid(f"  {BG_MERAH}{WHT} KUYANGIN DONG {RST}", CYN))
    print(headerBot(CYN))
    print('')

def maskEmail(email):
    if not email or '@' not in email: return email or '(kosong)'
    u, d = email.split('@', 1)
    if len(u) <= 4: return u[0] + '****@' + d
    return u[:2] + '****' + u[-2:] + '@' + d

def tampilkanMenu(cfg, balStr):
    clear(); bannerMain()
    print(f"  {YEL}▸{RST} {WHT}Channel      {RST}: {GRN}@bijikelot_v5{RST}")
    print(f"  {YEL}▸{RST} {WHT}Creator      {RST}: {GRN}iyannn{RST}")
    print(f"  {YEL}▸{RST} {WHT}Version      {RST}: {GRN}Ceban{RST}")
    print(f"  {YEL}▸{RST} {WHT}Status       {RST}: {GRN}Ngopi Dong{RST}")
    print("")
    print(f"  {CYN}◉{RST} {ABU}Site         {RST}: {CYN}{HOST}{RST}")
    
    uaDisp = f"{GRN}{cfg['userAgent']}{RST}" if cfg.get('userAgent') else f"{RED}✗ belum diset{RST}"
    print(f"  {CYN}◉{RST} {ABU}User-Agent   {RST}: {uaDisp}")
    
    ckDisp = f"{GRN}{cfg['cookie'][:20]}...{RST}" if cfg.get('cookie') else f"{RED}✗ belum diset{RST}"
    print(f"  {CYN}◉{RST} {ABU}Cookie       {RST}: {ckDisp}")
    
    provDisp = f"{GRN}{PROVIDERS[PROVIDER]['name']}{RST}" if PROVIDER and PROVIDER in PROVIDERS else f"{WHT}-{RST}"
    print(f"  {CYN}◉{RST} {ABU}Provider     {RST}: {provDisp}")
    
    if balStr: print(f"  {CYN}◉{RST} {ABU}Balance      {RST}: {YEL}{balStr}{RST}")
    
    print('')
    print(boxTop('[ MENU ]', CYN))
    print(boxMid(f"  {YEL}[1]{RST} {WHT}Start Faucet{RST}", CYN))
    print(boxMid(f"  {YEL}[2]{RST} {WHT}Set Provider{RST}", CYN))
    print(boxMid(f"  {YEL}[3]{RST} {WHT}Set Account{RST}", CYN))
    print(boxMid(f"  {YEL}[4]{RST} {WHT}Set User-Agent{RST}", CYN))
    print(boxMid(f"  {YEL}[5]{RST} {WHT}Set Cookie{RST}", CYN))
    print(boxMid(f"  {YEL}[0]{RST} {RED}Exit{RST}", CYN))
    print(boxBot(CYN))
    print('')

def menuProvider():
    global PROVIDER, API_KEY
    while True:
        clear(); bannerMain()
        print(f"{WHT}  ⚙  Provider Setup{RST}\n")
        cfg = loadConfig() or defaultConfig()
        active = cfg.get('provider', '')
        print(f"  {WHT}Provider aktif:{RST} {GRN + PROVIDERS[active]['name'] + RST if active and active in PROVIDERS else WHT + '-' + RST}\n")
        ids = list(PROVIDERS.keys())
        for i, pid in enumerate(ids):
            p = PROVIDERS[pid]
            key = cfg.get('apikeys', {}).get(pid, '')
            marker = f" {GRN}●{RST}" if pid == active else '  '
            print(f"  {GRN}[{i + 1}]{RST}{marker} {WHT}{p['name']:<14}{RST} {GRN + maskKey(key) + RST if key else WHT + '-' + RST}")
        print(f"  {RED}[0]{RST}  {WHT}Kembali{RST}\n")
        c = askQuestion(f"  {WHT}❯ Pilih: {RST}").strip()
        if c == '0': return
        try: idx = int(c) - 1
        except: 
            blinkErr('Pilihan invalid', 1200)
            continue
        if idx < 0 or idx >= len(ids):
            blinkErr('Pilihan invalid', 1200)
            continue
        chosenId = ids[idx]
        chosen = PROVIDERS[chosenId]
        cur = cfg.get('apikeys', {}).get(chosenId, '')
        print('')
        print(f"  {WHT}Apikey sekarang:{RST} {GRN + maskKey(cur) + RST if cur else WHT + '-' + RST}")
        inp = askQuestion(f"  {WHT}{chosen['name']} Apikey : {RST}").strip()
        if inp:
            setApiKey(chosenId, inp)
            log(f"Apikey {chosen['name']} disimpan.", 'ok')
        else:
            log('Apikey tidak diubah.', 'i')
        setActiveProvider(chosenId)
        PROVIDER = chosenId
        API_KEY = getApiKey(chosenId)
        log(f"Provider aktif → {chosen['name']}", 'ok')
        sleep(1500)

def menuAccount(cfg):
    clear(); bannerMain()
    print(f"{WHT}  👤 Account Setup{RST}\n")
    print(f"  {WHT}Current Email:{RST} {GRN}{maskEmail(cfg.get('email', '-'))}{RST}\n")
    email = askQuestion("  Email    : ").strip()
    password = askQuestion("  Password : ").strip()
    if email: cfg['email'] = email
    if password: cfg['password'] = password
    saveConfig(cfg)
    log('Account updated!', 'ok')
    sleep(1200)
    return cfg

def menuUA(cfg):
    clear(); bannerMain()
    print(f"{WHT}  🛠  User-Agent Setup{RST}\n")
    newUA = askQuestion("  User Agent : ").strip()
    cfg['userAgent'] = newUA or DEF_UA
    saveConfig(cfg)
    log('User-Agent updated!', 'ok')
    sleep(1200)
    return cfg

def menuCookie(cfg):
    clear(); bannerMain()
    print(f"{WHT}  🍪 Cookie Setup{RST}\n")
    cur = cfg.get('cookie', '')
    print(f"  {WHT}Current:{RST} {GRN}{cur[:30]}...{RST}\n" if cur else f"  {WHT}Current:{RST} {RED}not set{RST}\n")
    new_c = askQuestion(f"  {YEL}▸{RST} {WHT}Paste Cookie : {RST}").strip()
    if new_c:
        cfg['cookie'] = new_c
        saveConfig(cfg)
        jar.map.clear()
        for p in new_c.split(';'):
            t = p.strip()
            if t: jar.set(ORIGIN_HOST, [t])
        log('Cookie disimpan.', 'ok')
    else:
        log('Batal.', 'wr')
    sleep(1500)
    return cfg

def main():
    global PROVIDER, API_KEY, STOP_SIGNAL

    cfg = loadConfig() or defaultConfig()

    if cfg.get('cookie'):
        for p in cfg['cookie'].split(';'):
            t = p.strip()
            if t: jar.set(ORIGIN_HOST, [t])

    PROVIDER = cfg.get('provider', '')
    API_KEY = getApiKey(PROVIDER)

    clear(); bannerMain()
    log('Config loaded', 'ok')
    log(f"Provider : {PROVIDERS[PROVIDER]['name'] if PROVIDER and PROVIDER in PROVIDERS else '-'}", 'dbg')
    log(f"Cookie   : {cfg.get('cookie', '')[:20]}...", 'dbg')
    sleep(800)

    while True:
        STOP_SIGNAL = False
        balStr = None
        try:
            bal = refreshBalance()
            if bal is not None: balStr = f"{bal:.2f}"
        except: pass

        tampilkanMenu(cfg, balStr)
        c = askQuestion(f"  {YEL}▸{RST} {WHT}Option : {RST}").strip()

        if c == '0':
            print(f"\n{RED}[!] Program stopped.{RST}")
            sys.exit(0)
        if c == '2':
            menuProvider()
            cfg = loadConfig() or cfg
            PROVIDER = cfg.get('provider', PROVIDER)
            API_KEY = getApiKey(PROVIDER)
            continue
        if c == '3':
            cfg = menuAccount(cfg)
            continue
        if c == '4':
            cfg = menuUA(cfg)
            continue
        if c == '5':
            cfg = menuCookie(cfg)
            continue

        if not cfg.get('userAgent'):
            print('')
            log('User-Agent belum di-set. Set dulu di menu [4].', 'wr')
            sleep(2000)
            continue
        if not cfg.get('cookie'):
            print('')
            log('Cookie belum di-set. Set dulu di menu [5].', 'wr')
            sleep(2000)
            continue
        if not PROVIDER or PROVIDER not in PROVIDERS or not getApiKey(PROVIDER):
            print('')
            log('Provider/apikey belum di-set. Setup dulu di menu [2].', 'wr')
            sleep(2000)
            continue

        try:
            chk = request('GET', f"{HOST}/dashboard", {'maxRedirects': 5})
            if not isLoggedIn(chk['body']):
                res = ensureLoggedIn(cfg)
                if not res['ok']:
                    sleep(1500)
                    continue
        except Exception as e:
            log(f"Pre-check err: {e}", 'er')

        if c == '1':
            try:
                runFullCycle(cfg)
            except Exception as e:
                if not STOP_SIGNAL:
                    log(f"Cycle err: {e}", 'er')
        else:
            blinkErr(f"Pilihan salah: {c}", 1200)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"{RED}Fatal: {e}{RST}")
        sys.exit(1)
