import hashlib
from curl_cffi import requests
import json, time, re, sys, os, traceback, random
from datetime import datetime

HOST         = "https://pitasks.com"
WARYONO_IN   = "https://api.waryono.my.id/in.php"
WARYONO_RES  = "https://api.waryono.my.id/res.php"
CONFIG_FILE  = "cpitaskonfig.json"

DEF_UA = ("Mozilla/5.0 (Linux; Android 16; 23076RN4BI) AppleWebKit/537.36 "
          "Chrome/134.0.6998.135 Mobile Safari/537.36")

BLK="\033[0;30m"; RED="\033[0;31m"; GRN="\033[0;32m"; YEL="\033[0;33m"
BLU="\033[0;34m"; MAG="\033[0;35m"; CYN="\033[0;36m"; WHT="\033[0;37m"
RST="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"

CLR = "\r\033[2K"

# ═══════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════
STATE = {
    "email": "",
    "balance": None,
    "claims_ok": 0,
    "claims_fail": 0,
    "cooldowns": 0,
    "session_start": time.time(),
    "logs": [],
    "status": "init",     # init | running | solving | waiting | idle
    "last_reward": None,
}

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def mask_email(email):
    if '@' not in email: return email
    user, domain = email.split('@', 1)
    if len(user) <= 4: return user[:1] + "****@" + domain
    return user[:2] + "****" + user[-2:] + "@" + domain

def fmt_dur(sec):
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# ═══════════════════════════════════════════════════════════
# LOG + RENDER
# ═══════════════════════════════════════════════════════════
def state_log(msg, tag="i"):
    ts = datetime.now().strftime("%H:%M:%S")
    STATE["logs"].append((ts, tag, msg))
    if len(STATE["logs"]) > 12:
        STATE["logs"] = STATE["logs"][-12:]

def icon(tag):
    return {
        "i": f"{CYN}»{RST}",
        "ok": f"{GRN}✓{RST}",
        "er": f"{RED}✗{RST}",
        "wr": f"{YEL}⚠{RST}",
        "in": f"{BLU}●{RST}",
        "cf": f"{CYN}◇{RST}",
        "bi": f"{GRN}₹{RST}",
    }.get(tag, f"{CYN}»{RST}")

def render_dashboard():
    """Redraw seluruh UI di tempat (tanpa clear)."""
    W = 62
    out = []
    out.append("\033[H")   # cursor ke atas

    # ── Banner ──
    out.append(f"{WHT}╔" + "═" * W + f"╗{RST}")
    title = "PITASKS AUTO CLAIM"
    sub = "─────── SOUU ENGINE ───────"
    out.append(f"{WHT}║{RST} {BOLD}{YEL}{title:<{W-2}}{RST}{WHT} ║{RST}")
    out.append(f"{WHT}║{RST} {DIM}{sub:<{W-2}}{RST}{WHT} ║{RST}")
    out.append(f"{WHT}╠" + "═" * W + f"╣{RST}")

    # ── Account ──
    bal = STATE["balance"] if STATE["balance"] else "?"
    email = mask_email(STATE["email"]) if STATE["email"] else "-"
    uptime = fmt_dur(time.time() - STATE["session_start"])
    st_map = {
        "init": f"{CYN}INIT{RST}",
        "running": f"{GRN}RUNNING{RST}",
        "solving": f"{YEL}SOLVING{RST}",
        "waiting": f"{MAG}WAITING{RST}",
        "idle": f"{DIM}IDLE{RST}",
    }
    status = st_map.get(STATE["status"], "?")

    def L(k, v):
        s = f" {k:<14}: {v}"
        # pad bersih (strip ANSI)
        clean = re.sub(r'\033\[[0-9;]*m', '', s)
        pad = W - len(clean) - 1
        return f"{WHT}║{RST}{s}{' ' * max(0, pad)}{WHT}║{RST}"

    out.append(f"{WHT}║{RST} {BOLD}{CYN}ACCOUNT{RST}{' ' * (W - 9)}{WHT}║{RST}")
    out.append(L("Email", f"{CYN}{email}{RST}"))
    out.append(L("Balance", f"{GRN}${bal}{RST}"))
    out.append(L("Status", status))
    out.append(L("Uptime", f"{WHT}{uptime}{RST}"))
    out.append(f"{WHT}╠" + "═" * W + f"╣{RST}")

    # ── Stats ──
    out.append(f"{WHT}║{RST} {BOLD}{CYN}STATS{RST}{' ' * (W - 7)}{WHT}║{RST}")
    out.append(L("Claims OK", f"{GRN}{STATE['claims_ok']}{RST}"))
    out.append(L("Claims Fail", f"{RED}{STATE['claims_fail']}{RST}"))
    out.append(L("Cooldowns", f"{YEL}{STATE['cooldowns']}{RST}"))
    if STATE["last_reward"]:
        out.append(L("Last Reward", f"{GRN}{STATE['last_reward']}{RST}"))
    out.append(f"{WHT}╠" + "═" * W + f"╣{RST}")

    # ── Logs ──
    out.append(f"{WHT}║{RST} {BOLD}{CYN}LOGS{RST}{' ' * (W - 6)}{WHT}║{RST}")
    logs = STATE["logs"][-8:]
    for ts, tag, msg in logs:
        line = f"{WHT}[{ts}]{RST} {icon(tag)} {msg}"
        clean = re.sub(r'\033\[[0-9;]*m', '', line)
        pad = W - len(clean) - 1
        out.append(f"{WHT}║{RST} {line}{' ' * max(0, pad)}{WHT}║{RST}")

    # fill kosong kalau kurang dari 8
    for _ in range(8 - len(logs)):
        out.append(f"{WHT}║{RST}{' ' * W}{WHT}║{RST}")

    out.append(f"{WHT}╚" + "═" * W + f"╝{RST}")
    out.append("")
    out.append(f"  {GRN}BOT RUNNING{RST} {DIM}•{RST} {CYN}{datetime.now().strftime('%H:%M:%S')}{RST}")
    out.append(f"  {DIM}By Power @SouuXso • PiTasks Edition{RST}")

    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()

def log(msg, tag="i"):
    state_log(msg, tag)
    render_dashboard()

# ═══════════════════════════════════════════════════════════
# TIMER (inline di bawah dashboard)
# ═══════════════════════════════════════════════════════════
def tmr(seconds, label="Countdown"):
    total = int(seconds)
    if total < 1: return
    symbols   = list(reversed(['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘']))
    spinners  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
    spinners1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','⣇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
    dots      = ['▪', '▪▪', '▪▪▪', '▪▪▪▪']

    start = time.time()
    i = 0
    while True:
        elapsed = int(time.time() - start)
        remaining = max(0, total - elapsed)
        if remaining <= 0: break
        pct = round(((total - remaining) / total) * 100)
        mm, ss = divmod(remaining, 60)

        symbol = symbols[i % len(symbols)]
        sp     = spinners[i % len(spinners)]
        sp1    = spinners1[i % len(spinners1)]
        dot    = dots[elapsed % len(dots)]
        i += 1

        c1 = random.randint(1, 7)
        c2 = random.randint(1, 7)

        sys.stdout.write(
            f"\r{CLR} \033[1;3{c1}m {sp}\033[1;37m {label} "
            f"\033[1;31m{mm}:{ss:02d}\033[1;3{c2}m {symbol} {sp1}"
            f"\033[1;37m {pct}%\033[1;33m {dot}"
        )
        sys.stdout.flush()
        time.sleep(0.2)

    sys.stdout.write(CLR)
    sys.stdout.flush()

# ═══════════════════════════════════════════════════════════
# HTTP
# ═══════════════════════════════════════════════════════════
def load_session():
    return requests.Session(impersonate="chrome110")

def safe_request(sess, url, method='GET', data=None, headers=None):
    attempt = 0
    while True:
        attempt += 1
        try:
            opts = {"timeout": 45, "allow_redirects": True}
            if headers: opts["headers"] = headers
            if method == 'POST':
                r = sess.post(url, data=data, **opts)
            else:
                r = sess.get(url, **opts)
            return r.text
        except Exception as e:
            msg = str(e)
            log(f"[NET] gagal (#{attempt}): {msg[:50]}, retry 8s", "wr")
            time.sleep(8)

# ═══════════════════════════════════════════════════════════
# TURNSTILE SOLVER — WARYONO
# ═══════════════════════════════════════════════════════════
def solve_turnstile(apikey, sitekey, pageurl):
    global_attempt = 0
    while True:
        global_attempt += 1
        STATE["status"] = "solving"
        log(f"Submit Turnstile (attempt #{global_attempt})", "cf")

        payload = {
            "apikey": apikey, "methods": "turnstile",
            "domain": pageurl, "sitekey": sitekey,
            "action": "login", "cdata": "",
        }
        try:
            r = requests.post(WARYONO_IN, json=payload,
                              impersonate="chrome110", timeout=30)
            body = r.text.strip()
        except Exception as e:
            log(f"submit error: {str(e)[:50]}", "er")
            time.sleep(5); continue

        task_id = None
        if body.startswith("{"):
            try:
                j = json.loads(body)
                if j.get("status") == 1:
                    task_id = j.get("request")
                else:
                    err = j.get("request", "")
                    if err in ("ERROR_WRONG_USER_KEY", "ERROR_KEY_DOES_NOT_EXIST",
                               "ERROR_ZERO_BALANCE", "ERROR_IP_NOT_ALLOWED"):
                        log(f"API error: {err}", "er"); time.sleep(30); continue
                    log(f"submit: {err}", "wr"); time.sleep(3); continue
            except Exception:
                time.sleep(3); continue
        elif body.startswith("OK|"):
            task_id = body[3:].strip()

        if not task_id:
            time.sleep(3); continue

        log(f"Task ID: {task_id}", "ok")

        poll_start = time.time()
        need_resubmit = False
        i = 0
        total = 180

        while True:
            elapsed = int(time.time() - poll_start)
            if elapsed > total:
                sys.stdout.write(CLR); sys.stdout.flush()
                need_resubmit = True; break

            remaining = max(0, total - elapsed)
            pct = round(((total - remaining) / total) * 100)
            mm, ss = divmod(elapsed, 60)

            symbols   = list(reversed(['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘']))
            spinners  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾']
            spinners1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','⣇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯']
            dots      = ['▪', '▪▪', '▪▪▪', '▪▪▪▪']

            symbol = symbols[i % len(symbols)]
            sp     = spinners[i % len(spinners)]
            sp1    = spinners1[i % len(spinners1)]
            dot    = dots[elapsed % len(dots)]
            i += 1

            c1 = random.randint(1, 7); c2 = random.randint(1, 7)
            sys.stdout.write(
                f"\r{CLR} \033[1;3{c1}m {sp}\033[1;37m Solving "
                f"\033[1;31m{mm}:{ss:02d}\033[1;3{c2}m {symbol} {sp1}"
                f"\033[1;37m {pct}%\033[1;33m {dot}"
            )
            sys.stdout.flush()
            time.sleep(0.5)

            if (time.time() - poll_start) % 2.5 < 0.5:
                try:
                    pr = requests.get(
                        WARYONO_RES,
                        params={"apikey": apikey, "id": task_id, "action": "get", "json": 1},
                        impersonate="chrome110", timeout=30,
                    )
                    res_body = pr.text.strip()
                except Exception:
                    continue

                if res_body.startswith("OK|"):
                    token = res_body[3:].strip()
                    sys.stdout.write(CLR); sys.stdout.flush()
                    log(f"Solved in {elapsed}s", "ok")
                    return token

                if res_body.startswith("{"):
                    try: res = json.loads(res_body)
                    except Exception: continue
                    if res.get("status") == 1:
                        token = res.get("request", "")
                        sys.stdout.write(CLR); sys.stdout.flush()
                        log(f"Solved in {elapsed}s", "ok")
                        return token
                    req = res.get("request", "")
                    if req == "CAPCHA_NOT_READY": continue
                    if req.startswith("ERROR"):
                        sys.stdout.write(CLR); sys.stdout.flush()
                        log(f"Solver error: {req}", "er")
                        need_resubmit = True; break

        if need_resubmit:
            continue

# ═══════════════════════════════════════════════════════════
# PARSERS
# ═══════════════════════════════════════════════════════════
def get_sitekey(html):
    m = re.search(r'data-sitekey="([^"]+)"', html) or re.search(r"data-sitekey='([^']+)'", html)
    return m.group(1) if m else None

def get_antibot(html):
    m = re.search(r'<div class="antibot-sequence">(.*?)</div>', html, re.S)
    if not m: return None
    seq = re.split(r'\s+', m.group(1).strip())
    seq = [s for s in seq if s and s not in ('→', '>') and '<' not in s]
    return ",".join(seq[:3]) if seq else None

def get_reward(html):
    m = re.search(r'<div class="alert alert-success">(.*?)</div>', html, re.S)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'Claimed \$([\d.]+) successfully', html)
    if m: return f"Claimed ${m.group(1)} successfully!"
    return None

def get_balance(html):
    for pat in (r'<span class="value-style">([\d.]+)</span>',
                r'<div class="perf-value">([\d.]+)</div>',
                r'Available:\s*\$?([\d.]+)'):
        m = re.search(pat, html, re.I)
        if m: return m.group(1)
    return None

def get_cooldown(html):
    for pat in (r'let\s+remaining\s*=\s*(\d+)', r'var\s+wait\s*=\s*(\d+)',
                r'Please wait (\d+)\s*seconds?', r'wait\s+(\d+)\s*seconds'):
        m = re.search(pat, html, re.I)
        if m: return int(m.group(1))
    return None

def is_logged_in(html): return 'Logout' in html or 'Dashboard' in html
def is_locked(html):    return 'account has been locked' in html or '/locked' in html

# ═══════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════
def do_login(sess, apikey, email, password):
    log(f"Login: {mask_email(email)}", "in")
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9"}
    tries = 0
    while True:
        tries += 1
        sitekey = None
        for _ in range(5):
            html = safe_request(sess, f"{HOST}/login", headers=base_hdr)
            if is_locked(html):
                log("AKUN DI-LOCK", "er"); return "LOCKED"
            sitekey = get_sitekey(html)
            if sitekey: break
            time.sleep(3)

        if not sitekey:
            time.sleep(5); continue

        token = solve_turnstile(apikey, sitekey, f"{HOST}/login")
        post_hdr = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": DEF_UA,
            "referer": f"{HOST}/login",
        }
        resp = safe_request(sess, f"{HOST}/login", method="POST", headers=post_hdr, data={
            "login_input": email, "password": password,
            "cf-turnstile-response": token,
        })
        if is_locked(resp):
            log("AKUN DI-LOCK", "er"); return "LOCKED"
        if is_logged_in(resp):
            log("Login berhasil!", "ok")
            return resp
        log(f"Login gagal (#{tries}), retry 5s", "wr")
        time.sleep(5)

# ═══════════════════════════════════════════════════════════
# FAUCET CLAIM
# ═══════════════════════════════════════════════════════════
def run_faucet(sess, apikey):
    base_hdr = {"user-agent": DEF_UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9"}
    outer = 0
    while True:
        outer += 1
        STATE["status"] = "running"
        render_dashboard()

        html = safe_request(sess, f"{HOST}/faucet", headers=base_hdr)
        if is_locked(html):
            log("AKUN DI-LOCK", "er"); return "LOCKED"
        if not is_logged_in(html):
            return -1

        cd = get_cooldown(html)
        if cd and cd > 0:
            STATE["cooldowns"] += 1
            STATE["status"] = "waiting"
            render_dashboard()
            log(f"Cooldown {cd//60:02d}:{cd%60:02d}", "wr")
            tmr(cd, "Waiting")
            continue

        sitekey = get_sitekey(html)
        if not sitekey:
            log("Sitekey tidak ditemukan, retry 3s", "wr")
            time.sleep(3); continue

        antibot = get_antibot(html)
        if not antibot:
            log("Antibot tidak ditemukan, retry 3s", "wr")
            time.sleep(3); continue

        log(f"Antibot: {antibot}", "i")
        token = solve_turnstile(apikey, sitekey, f"{HOST}/faucet")

        post_hdr = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": DEF_UA,
            "referer": f"{HOST}/faucet",
            "origin": HOST,
        }
        resp = safe_request(sess, f"{HOST}/faucet", method="POST", headers=post_hdr, data={
            "adblock_status": "clean",
            "antibot_sequence": antibot,
            "cf-turnstile-response": token,
            "claim": "",
        })

        if is_locked(resp):
            log("AKUN DI-LOCK", "er"); return "LOCKED"

        reward = get_reward(resp)
        if reward:
            dash = safe_request(sess, f"{HOST}/dashboard", headers=base_hdr)
            new_bal = get_balance(dash)
            STATE["balance"] = new_bal
            STATE["claims_ok"] += 1
            STATE["last_reward"] = reward
            render_dashboard()
            log(f"SUCCESS: {reward}", "ok")
            if new_bal:
                log(f"New Balance: ${new_bal}", "bi")
            return 605

        cd2 = get_cooldown(resp)
        if cd2 and cd2 > 0:
            dash = safe_request(sess, f"{HOST}/dashboard", headers=base_hdr)
            new_bal = get_balance(dash)
            STATE["balance"] = new_bal
            STATE["cooldowns"] += 1
            STATE["status"] = "waiting"
            render_dashboard()
            log(f"Cooldown {cd2//60:02d}:{cd2%60:02d}", "wr")
            tmr(cd2, "Waiting")
            continue

        STATE["claims_fail"] += 1
        render_dashboard()
        clean = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', resp))
        log(f"Gagal claim (#{outer}), retry 5s", "er")
        log(f"Preview: {clean[:150]}", "wr")
        time.sleep(5)

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
def load_config():
    if not os.path.exists(CONFIG_FILE):
        clear()
        print(f"{WHT}═══════════════════════════════════════{RST}")
        print(f"{YEL}      PITASKS AUTO BOT v2.0{RST}")
        print(f"{WHT}═══════════════════════════════════════{RST}")
        print(f"{WHT}Setup config baru:{RST}")
        print(f"{WHT}Email    : {RST}", end=""); email = input().strip()
        print(f"{WHT}Password : {RST}", end=""); password = input().strip()
        print(f"{WHT}API Key  : {RST}", end=""); apikey = input().strip()
        cfg = {"email": email, "password": password, "apikey": apikey}
        with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)
        print(f"{GRN}✓ Config tersimpan{RST}")
        time.sleep(1)
        return cfg
    with open(CONFIG_FILE) as f: cfg = json.load(f)
    cfg.setdefault("email", ""); cfg.setdefault("password", ""); cfg.setdefault("apikey", "")
    return cfg

# ═══════════════════════════════════════════════════════════
# MAIN — single account, auto loop
# ═══════════════════════════════════════════════════════════
def main():
    cfg = load_config()
    if not cfg["email"] or not cfg["password"] or not cfg["apikey"]:
        print(f"{RED}Config belum lengkap. Edit config.json manual.{RST}")
        return

    STATE["email"] = cfg["email"]
    STATE["session_start"] = time.time()

    clear()
    render_dashboard()

    # ── Session ──
    sess = load_session()
    hdr = {"user-agent": DEF_UA,
           "accept": "text/html,application/xhtml+xml,application/xml;q=0.9"}

    while True:
        try:
            # ── Cek session / auto login ──
            dash = safe_request(sess, f"{HOST}/dashboard", headers=hdr)

            if is_locked(dash):
                log("AKUN DI-LOCK, stop.", "er")
                return

            if not is_logged_in(dash):
                log("Session drop, auto re-login...", "wr")
                r = do_login(sess, cfg["apikey"], cfg["email"], cfg["password"])
                if r == "LOCKED":
                    log("AKUN DI-LOCK, stop.", "er")
                    return
                if not r:
                    log("Login gagal, retry 30s", "er")
                    time.sleep(30); continue
                dash = safe_request(sess, f"{HOST}/dashboard", headers=hdr)

            bal = get_balance(dash)
            if bal:
                STATE["balance"] = bal

            STATE["status"] = "running"
            render_dashboard()

            # ── Loop claim (selamanya) ──
            while True:
                try:
                    result = run_faucet(sess, cfg["apikey"])
                    if result == "LOCKED":
                        log("AKUN DI-LOCK, stop.", "er"); return
                    if result == -1:
                        log("Session hilang di dalam loop, re-login...", "wr")
                        break  # ke outer loop untuk re-login
                    # result int → cooldown detik
                    if isinstance(result, int) and result > 0:
                        tmr(result, "Waiting")
                        continue
                except Exception as e:
                    log(f"[LOOP] {str(e)[:80]}", "er")
                    time.sleep(5)

        except KeyboardInterrupt:
            print(f"\n{YEL}Dihentikan user.{RST}")
            return
        except Exception as e:
            log(f"[MAIN] {str(e)[:80]}", "er")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YEL}Dihentikan user.{RST}")
