#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║           ⚡ SOUU ENGINE — FREEFLARE AUTO CLAIM ⚡                ║
║        FreeFlareCrypto • NO CACHE • MANUAL PASTE COOKIE         ║
╚═══════════════════════════════════════════════════════════════════╝
"""

import requests, time, os, re, json, sys
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
#  COLOR
# ═══════════════════════════════════════════════════════════════════════════
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[38;5;196m"
GREEN  = "\033[38;5;46m"
YELLOW = "\033[38;5;226m"
CYAN   = "\033[38;5;51m"
MAGENTA= "\033[38;5;213m"
BLUE   = "\033[38;5;39m"
WHITE  = "\033[38;5;250m"
GRAY   = "\033[38;5;245m"
ORANGE = "\033[38;5;208m"
PINK   = "\033[38;5;205m"

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
def ansi_len(text): return len(ANSI_RE.sub('', text))

def clear():
    os.system("clear" if os.name != "nt" else "cls")

# ═══════════════════════════════════════════════════════════════════════════
#  BANNER HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def gradient(text, start=51, end=213):
    if len(text) <= 1:
        return f"\033[38;5;{start}m{text}{RESET}"
    out = ''
    for i, ch in enumerate(text):
        t = i / (len(text) - 1)
        c = int(round(start + (end - start) * t))
        out += f"\033[38;5;{c}m{ch}"
    return out + RESET

def box_line(content, width=60):
    pad = width - ansi_len(content)
    if pad < 0: pad = 0
    return f"\033[38;5;51m║  {RESET}{content}{' ' * pad}\033[38;5;51m║{RESET}\n"

def box_div():
    return f"\033[38;5;51m╠{'═' * 62}╣{RESET}\n"

def box_top():
    return f"\033[38;5;51m╔{'═' * 62}╗{RESET}\n"

def box_bot():
    return f"\033[38;5;51m╚{'═' * 62}╝{RESET}\n"

# ═══════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def fmt_uptime(s):
    s = int(s)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

def get_cookie(raw):
    raw = raw.strip()
    if "faas_session=" in raw:
        try:
            return raw.split("faas_session=")[1].split(";")[0].strip()
        except Exception:
            return raw
    return raw.replace(";", "").strip()

def status_color(s):
    s = s.upper()
    if 'BERHASIL' in s or 'SUCCESS' in s or 'FINISH' in s:
        return GREEN
    if 'FAIL' in s or 'VAILED' in s or 'SALAH' in s or 'MATI' in s or 'ERROR' in s:
        return RED
    if 'EMPTY' in s or 'KOSONG' in s:
        return PINK
    if 'WAIT' in s or 'COOLDOWN' in s or 'SKIP' in s:
        return ORANGE
    return YELLOW

# ═══════════════════════════════════════════════════════════════════════════
#  MODE PICKER
# ═══════════════════════════════════════════════════════════════════════════
def claim_mode_picker(title, extra_lines=None):
    out = []
    out.append(box_top())
    out.append(box_line(gradient(title)))
    out.append(box_line(f"{DIM}─────── SOUU ENGINE ───────{RESET}"))
    out.append(box_div())
    if extra_lines:
        for ln in extra_lines:
            out.append(box_line(ln))
        out.append(box_div())
    out.append(box_line(f"{MAGENTA}{BOLD}PILIH MODE CLAIM{RESET}"))
    out.append(box_line(f"  {CYAN}1.{RESET} {WHITE}10x claim{RESET}"))
    out.append(box_line(f"  {CYAN}2.{RESET} {WHITE}25x claim{RESET}"))
    out.append(box_line(f"  {CYAN}3.{RESET} {WHITE}50x claim{RESET}"))
    out.append(box_line(f"  {CYAN}4.{RESET} {ORANGE}Unlimited{RESET}"))
    out.append(box_bot())
    clear()
    print(''.join(out), end='')
    print(f"\n  {CYAN}PILIH > {RESET}", end='')
    p = input().strip()
    if p == "1":   return 10,     '10x claim'
    if p == "2":   return 25,     '25x claim'
    if p == "3":   return 50,     '50x claim'
    if p == "4":   return 999999, 'Unlimited'
    return 10, '10x claim'

# ═══════════════════════════════════════════════════════════════════════════
#  ══════════════════════ FREEFLARE CRYPTO MODULE ══════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
BASE_URL       = "https://freeflarcrypto.com"
SESSION_URL    = f"{BASE_URL}/api/session"
CLAIM_URL      = f"{BASE_URL}/claim"
DEFAULT_INTERVAL = 1800

ff_state = {
    'mode': 'IDLE', 'status': 'INIT', 'success': 0, 'failed': 0,
    'max_claim': 0, 'total_reward': 0.0, 'last_reward': '0.000',
    'currency': 'DGB', 'balance': '0.00000000', 'username': 'unknown',
    'cookie': '', 'interval': DEFAULT_INTERVAL, 'logs': [],
    'start_time': time.time(),
}
FF_MAX_LOGS = 6

def ff_push(msg, tag='i'):
    icons = {'i': f'{CYAN}●{RESET}', 'ok': f'{GREEN}✔{RESET}', 'er': f'{RED}✖{RESET}',
             'wr': f'{ORANGE}◈{RESET}', 'in': f'{MAGENTA}⬢{RESET}', 'g': f'{YELLOW}◆{RESET}',
             'pk': f'{PINK}◉{RESET}'}
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"{GRAY}[{ts}]{RESET} {icons.get(tag, '●')} {msg}"
    ff_state['logs'].append(line)
    if len(ff_state['logs']) > FF_MAX_LOGS:
        ff_state['logs'].pop(0)

def ff_banner():
    elapsed = time.time() - ff_state['start_time']
    out = []
    out.append(box_top())
    out.append(box_line(gradient("FREEFLARE CRYPTO AUTO CLAIM")))
    out.append(box_line(f"{DIM}─────── SOUU ENGINE ───────{RESET}"))
    out.append(box_div())

    out.append(box_line(f"{MAGENTA}{BOLD}SESSION{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ User       : {RESET}{YELLOW}{ff_state['username']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Mode       : {RESET}{YELLOW}{ff_state['mode']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Status     : {RESET}{status_color(ff_state['status'])}{ff_state['status']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m└─ Progress   : {RESET}{YELLOW}{ff_state['success']} / {ff_state['max_claim']}{RESET}"))
    out.append(box_div())

    out.append(box_line(f"{MAGENTA}{BOLD}BALANCE{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Wallet     : {RESET}{GREEN}{ff_state['balance']} {ff_state['currency']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Total Earn : {RESET}{GREEN}+{ff_state['total_reward']:.5f} {ff_state['currency']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m└─ Last Claim : {RESET}{GREEN}+{ff_state['last_reward']} {ff_state['currency']}{RESET}"))
    out.append(box_div())

    out.append(box_line(f"{MAGENTA}{BOLD}SYSTEM{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Success    : {RESET}{GREEN}{ff_state['success']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Failed     : {RESET}{RED}{ff_state['failed']}{RESET}"))
    out.append(box_line(f"\033[38;5;51m└─ Runtime    : {RESET}{YELLOW}{fmt_uptime(elapsed)}{RESET}"))
    out.append(box_div())

    for i in range(FF_MAX_LOGS):
        if i < len(ff_state['logs']):
            out.append(box_line(ff_state['logs'][i]))
        else:
            out.append(f"\033[38;5;51m║{' ' * 62}║{RESET}\n")

    out.append(box_bot())
    out.append(f"\n   {gradient('BOT RUNNING', 46, 226)} {WHITE}• {datetime.now().strftime('%H:%M:%S')}{RESET}\n")
    out.append(f"   {DIM}By Power {RESET}{MAGENTA}@SouuXso{RESET}{DIM} • {RESET}{GREEN}FreeFlare Edition{RESET}\n\n")
    clear()
    print(''.join(out), end='')

def ff_parse_session(text):
    try:
        j = json.loads(text)
        return {
            "balance": j.get("balance", "0"),
            "currency": j.get("balance_currency", "DGB"),
            "username": j.get("name", "unknown"),
            "logged_in": j.get("logged_in", False),
            "interval_seconds": j.get("claim", {}).get("interval_seconds", DEFAULT_INTERVAL),
            "claim_amount": j.get("claim", {}).get("amount", "0"),
        }
    except Exception:
        return None

def ff_parse_claim(text):
    try:
        j = json.loads(text)
        return {
            "success": j.get("success", False),
            "amount": j.get("amount", "0"),
            "currency": j.get("currency", "DGB"),
            "claim_id": j.get("claim_id"),
            "payout_id": j.get("payout_id"),
            "raw": j,
        }
    except Exception:
        return None

def ff_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
    }

def ff_api_session():
    try:
        r = requests.get(SESSION_URL, headers=ff_headers(),
                         cookies={"faas_session": ff_state['cookie']}, timeout=20)
        if r.status_code != 200:
            return None
        return ff_parse_session(r.text)
    except Exception as e:
        ff_push(f"session err: {str(e)[:40]}", 'er')
        return None

def ff_api_claim():
    try:
        r = requests.post(CLAIM_URL,
                          headers={**ff_headers(), "Content-Type": "application/x-www-form-urlencoded"},
                          cookies={"faas_session": ff_state['cookie']}, timeout=20)
        return {
            "status_code": r.status_code,
            "json": ff_parse_claim(r.text),
            "text": r.text[:300],
        }
    except Exception as e:
        ff_push(f"claim err: {str(e)[:40]}", 'er')
        return None

def ff_run():
    out = []
    out.append(box_top())
    out.append(box_line(gradient("FREEFLARE CRYPTO AUTO CLAIM")))
    out.append(box_line(f"{DIM}─────── SOUU ENGINE ───────{RESET}"))
    out.append(box_div())
    out.append(box_line(f"{MAGENTA}{BOLD}SESSION{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Website    : {RESET}{YELLOW}https://freeflarcrypto.com{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Coin       : {RESET}{GREEN}DGB{RESET}"))
    out.append(box_line(f"\033[38;5;51m├─ Cooldown   : {RESET}{YELLOW}30 menit / claim{RESET}"))
    out.append(box_line(f"\033[38;5;51m└─ Mode       : {RESET}{YELLOW}NO SAVE (manual paste){RESET}"))
    out.append(box_bot())
    clear()
    print(''.join(out), end='')

    print(f"\n   {gradient('PASTE COOKIE', 46, 226)}\n")
    print(f"  {CYAN}┌─[ {YELLOW}faas_session{CYAN} ]{RESET}")
    print(f"  {CYAN}└──> {RESET}", end='')
    raw = input().strip()
    cookie = get_cookie(raw)
    if not cookie:
        print(f"{RED}  ✖ Cookie kosong, kembali ke menu.{RESET}")
        time.sleep(1.5)
        return

    ff_state['cookie'] = cookie
    ff_state['start_time'] = time.time()
    ff_state['success'] = 0
    ff_state['failed'] = 0
    ff_state['total_reward'] = 0.0
    ff_state['last_reward'] = '0.000'
    ff_state['logs'] = []

    cookie_preview = cookie[:16] + '...' + cookie[-8:] if len(cookie) > 24 else cookie

    max_claim, mode = claim_mode_picker(
        "FREEFLARE CRYPTO AUTO CLAIM",
        [f"{MAGENTA}{BOLD}SESSION{RESET}",
         f"\033[38;5;51m├─ Website : {RESET}{YELLOW}freeflarcrypto.com{RESET}",
         f"\033[38;5;51m├─ Coin    : {RESET}{GREEN}DGB{RESET}",
         f"\033[38;5;51m└─ Cookie  : {RESET}{GREEN}{cookie_preview}{RESET}"]
    )
    ff_state['max_claim'] = max_claim
    ff_state['mode'] = mode
    ff_state['status'] = 'CHECKING'

    ff_push(f"mode: {mode} | max: {max_claim}", 'g')
    ff_banner()

    sess = ff_api_session()
    if not sess or not sess.get("logged_in"):
        ff_state['status'] = 'COOKIE SALAH/MATI'
        ff_push("cookie invalid — cek faas_session", 'er')
        ff_banner()
        print(f"\n   {RED}✖ Cookie tidak valid. Ambil ulang dari browser.{RESET}\n")
        input(f"  {CYAN}Enter untuk kembali ke menu...{RESET}")
        return

    ff_state['username'] = sess['username']
    ff_state['balance']  = sess['balance']
    ff_state['currency'] = sess['currency']
    ff_state['interval'] = sess.get('interval_seconds', DEFAULT_INTERVAL)

    ff_push(f"login OK — {sess['username']}", 'ok')
    ff_push(f"balance: {sess['balance']} {sess['currency']}", 'i')
    ff_push(f"cooldown: {ff_state['interval']}s", 'i')
    ff_banner()

    while ff_state['success'] < max_claim:
        try:
            sess = ff_api_session()
            if sess and sess.get("logged_in"):
                ff_state['balance']  = sess['balance']
                ff_state['currency'] = sess['currency']
                if sess.get('interval_seconds'):
                    ff_state['interval'] = sess['interval_seconds']

            ff_state['status'] = f'CLAIM #{ff_state["success"]+1}'
            ff_banner()

            res = ff_api_claim()

            if res is None:
                ff_state['failed'] += 1
                ff_state['status'] = f'VAILED #{ff_state["failed"]}'
                ff_push("claim request failed", 'er')
                ff_banner()
                for i in range(5, 0, -1):
                    print(f"\r   {YELLOW}◈ retry in {i}s{RESET}    ", end='')
                    time.sleep(1)
                print()
                continue

            sc = res["status_code"]
            jd = res["json"]
            txt_low = res["text"].lower()

            # ── SUCCESS ──
            if sc == 200 and jd and jd.get("success"):
                amount = jd.get("amount", "0")
                currency = jd.get("currency", ff_state['currency'])
                claim_id = jd.get("claim_id", "-")
                payout_id = jd.get("payout_id", "-")

                ff_state['success'] += 1
                ff_state['last_reward'] = amount
                ff_state['currency'] = currency
                try:
                    ff_state['total_reward'] += float(amount)
                except Exception:
                    pass
                ff_state['status'] = f'BERHASIL #{ff_state["success"]}'

                ff_push(f"+{amount} {currency} | id {claim_id}", 'ok')
                ff_push(f"payout {payout_id}", 'i')
                ff_banner()

                if ff_state['success'] >= max_claim:
                    break

                interval = ff_state['interval']
                ff_push(f"cooldown {interval}s", 'wr')
                ff_banner()
                for i in range(interval, 0, -1):
                    ff_state['status'] = f'COOLDOWN {i}s'
                    print(f"\r   {ORANGE}◈ cooldown {i}s → next {ff_state['success']+1}/{max_claim}{RESET}    ", end='')
                    time.sleep(1)
                print()
                continue

            # ── EMPTY FUND (skip) ──
            if sc == 503 or "insufficient fund" in txt_low or "does not have sufficient" in txt_low:
                ff_state['status'] = 'EMPTY FUND (SKIP)'
                ff_push("faucet kosong — skip 30s", 'pk')
                ff_banner()
                for i in range(30, 0, -1):
                    ff_state['status'] = f'SKIP EMPTY {i}s'
                    print(f"\r   {PINK}◉ faucet kosong — skip {i}s{RESET}    ", end='')
                    time.sleep(1)
                print()
                continue

            # ── COOKIE MATI ──
            if sc in (401, 403) or (jd is None and "login" in txt_low):
                ff_state['status'] = 'COOKIE SALAH/MATI'
                ff_push("cookie mati — paste ulang", 'er')
                ff_banner()
                break

            # ── SERVER COOLDOWN ──
            if sc == 429 or "cooldown" in txt_low or "too soon" in txt_low:
                ff_state['status'] = 'SERVER COOLDOWN'
                ff_push("server masih cooldown", 'wr')
                ff_banner()
                wait = ff_state['interval']
                for i in range(wait, 0, -1):
                    ff_state['status'] = f'WAIT {i}s'
                    print(f"\r   {ORANGE}◈ server cooldown {i}s{RESET}    ", end='')
                    time.sleep(1)
                print()
                continue

            # ── FAILED GENERIC ──
            ff_state['failed'] += 1
            ff_state['status'] = f'VAILED #{ff_state["failed"]}'
            ff_push(f"HTTP {sc} | {res['text'][:40]}", 'er')
            ff_banner()
            for i in range(5, 0, -1):
                ff_state['status'] = f'RETRY {i}s'
                print(f"\r   {YELLOW}◈ retry in {i}s{RESET}    ", end='')
                time.sleep(1)
            print()

        except KeyboardInterrupt:
            raise
        except Exception as e:
            ff_state['failed'] += 1
            ff_state['status'] = 'ERROR'
            ff_push(f"error: {str(e)[:50]}", 'er')
            ff_banner()
            time.sleep(2)

    ff_state['status'] = 'FINISH'
    ff_push(f"selesai | sukses={ff_state['success']} failed={ff_state['failed']} total={ff_state['total_reward']:.5f} {ff_state['currency']}", 'g')
    ff_banner()
    print(f"\n   {gradient('SELESAI', 46, 226)} {WHITE}• sukses {ff_state['success']} | failed {ff_state['failed']} | total +{ff_state['total_reward']:.5f} {ff_state['currency']}{RESET}\n")
    input(f"  {CYAN}Enter untuk kembali...{RESET}")

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    clear()
    while True:
        try:
            ff_run()
        except KeyboardInterrupt:
            print(f"\n{YELLOW}[!] Dihentikan.{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[!] Error: {e}{RESET}")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
