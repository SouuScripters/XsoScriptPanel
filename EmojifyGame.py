#!/usr/bin/env python3
# ============================================================
#  EMOJIFYEARN BOT — SOUU ENGINE
#  Live Dashboard UI + Auto Watch Ads + AD_COOLDOWN Handler
# ============================================================
#  pip install requests colorama
# ============================================================

import os, sys, time, random, string, re
from datetime import datetime

try:
    import requests
except ImportError:
    print("[!] pip install requests"); sys.exit(1)

try:
    from colorama import init as cinit, Fore, Style
    cinit(autoreset=True)
except ImportError:
    class Fore:
        RED=GREEN=YELLOW=CYAN=MAGENTA=WHITE=BLUE=RESET=''
    class Style:
        BRIGHT=DIM=RESET_ALL=''


# ============================================================
#  CONFIG
# ============================================================
API_BASE = "https://api.emojifyearn.site"
ORIGIN   = "https://emojifyearn.site"

MAX_FAILURES = 3
DELAY_MIN    = 2.0
DELAY_MAX    = 5.0

SHOWN_PER_AD  = 1
CLICKS_PER_AD = 1

STATIC_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/156.0.8078.47 Mobile Safari/537.36 "
        "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"
    ),
    "sec-ch-ua": '"Not:A-Brand";v="8", "Chromium";v="156", "Android WebView";v="156"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "content-type": "application/json",
    "accept": "*/*",
    "origin": ORIGIN,
    "x-requested-with": "org.telegram.messenger.web",
    "sec-fetch-site": "same-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": ORIGIN + "/",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "priority": "u=1, i",
}


# ============================================================
#  STATE
# ============================================================
state = {
    "host": "https://emojifyearn.site",
    "cycle": 0,
    "tier": "-",
    "init_age": "0m",
    "app_key": "-",
    "user": "-",
    "balance": 0.0,
    "total_earn": 0.0,
    "ads_total": 0,
    "reward": 0.0,
    "ads_count": 0,
    "net_retry": 0,
    "ad_fails": 0,
    "last_reward": "-",
    "bot_state": "INIT",
    "bot_phase": "-",
    "logs": [],
}


# ============================================================
#  DASHBOARD UI
# ============================================================
def _clear():
    os.system("cls" if os.name == "nt" else "clear")

def _print_line(text=""):
    clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
    width = 58
    padding = width - 2 - len(clean_text)
    if padding < 0: padding = 0
    print(f"{Fore.CYAN}║{Fore.RESET} {text}{' ' * padding} {Fore.CYAN}║{Fore.RESET}")

def render_ui():
    _clear()
    print(f"{Fore.CYAN}╔{'═' * 58}╗{Fore.RESET}")
    _print_line(f"{Style.BRIGHT}{Fore.CYAN}EMOJIFYEARN {Fore.MAGENTA}AUTO {Fore.YELLOW}WATCH{Style.RESET_ALL}")
    _print_line(f"{Fore.WHITE}────────── {Style.BRIGHT}SOUU ENGINE{Style.RESET_ALL} ──────────")
    print(f"{Fore.CYAN}╠{'═' * 58}╣{Fore.RESET}")
    
    # SESSION
    _print_line(f"{Style.BRIGHT}SESSION{Style.RESET_ALL}")
    _print_line(f"{Fore.WHITE}├─ Host      {Fore.RESET}: {Fore.YELLOW}{state['host']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Cycle     {Fore.RESET}: {Fore.WHITE}{state['cycle']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Tier      {Fore.RESET}: {Fore.WHITE}{state['tier']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Init age  {Fore.RESET}: {Fore.MAGENTA}{state['init_age']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}└─ App Key   {Fore.RESET}: {Fore.WHITE}{state['app_key']}{Fore.RESET}")
    print(f"{Fore.CYAN}╠{'═' * 58}╣{Fore.RESET}")
    
    # ACCOUNT
    _print_line(f"{Style.BRIGHT}ACCOUNT{Style.RESET_ALL}")
    _print_line(f"{Fore.WHITE}├─ User      {Fore.RESET}: {Fore.WHITE}{state['user']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Balance   {Fore.RESET}: {Fore.GREEN}${state['balance']:.6f}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Total Earn{Fore.RESET}: {Fore.GREEN}${state['total_earn']:.6f}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}└─ Ads Total {Fore.RESET}: {Fore.WHITE}{state['ads_total']}{Fore.RESET}")
    print(f"{Fore.CYAN}╠{'═' * 58}╣{Fore.RESET}")

    # SESSION STATS
    _print_line(f"{Style.BRIGHT}SESSION STATS{Style.RESET_ALL}")
    _print_line(f"{Fore.WHITE}├─ Reward    {Fore.RESET}: {Fore.GREEN}+${state['reward']:.6f}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Ads count {Fore.RESET}: {Fore.WHITE}{state['ads_count']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Net retry {Fore.RESET}: {Fore.WHITE}{state['net_retry']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}├─ Ad fails  {Fore.RESET}: {Fore.WHITE}{state['ad_fails']}/{MAX_FAILURES}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}└─ Last reward{Fore.RESET}: {Fore.WHITE}{state['last_reward']}{Fore.RESET}")
    print(f"{Fore.CYAN}╠{'═' * 58}╣{Fore.RESET}")

    # STATUS
    _print_line(f"{Style.BRIGHT}STATUS{Style.RESET_ALL}")
    _print_line(f"{Fore.WHITE}├─ State     {Fore.RESET}: {Fore.MAGENTA}{state['bot_state']}{Fore.RESET}")
    _print_line(f"{Fore.WHITE}└─ Phase     {Fore.RESET}: {Fore.WHITE}{state['bot_phase']}{Fore.RESET}")
    print(f"{Fore.CYAN}╠{'═' * 58}╣{Fore.RESET}")

    # LOGS
    for log_line in state["logs"]:
        _print_line(log_line)
    for _ in range(8 - len(state["logs"])):
        _print_line("")
    
    print(f"{Fore.CYAN}╚{'═' * 58}╝{Fore.RESET}")
    print(f"\n   {Fore.GREEN}● BOT RUNNING{Fore.RESET} • {datetime.now().strftime('%H:%M:%S')}")

def log(msg, tag="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon, color = "♦", Fore.YELLOW
    if tag == "OK":      icon, color = "✔", Fore.GREEN
    elif tag == "ERR":   icon, color = "✘", Fore.RED
    elif tag == "BOOT":  icon, color = "●", Fore.CYAN
    elif tag == "WARN":  icon, color = "♦", Fore.YELLOW
    elif tag == "AUTH":  icon, color = "●", Fore.MAGENTA
    elif tag == "INIT":  icon, color = "✔", Fore.GREEN

    formatted = f"{Fore.WHITE}[{ts}]{Fore.RESET} {color}{icon} {tag:<5}{Fore.RESET} {msg}"
    state["logs"].append(formatted)
    if len(state["logs"]) > 8:
        state["logs"].pop(0)
    render_ui()


# ============================================================
#  API CLIENT
# ============================================================
class Client:
    def __init__(self, init_data: str):
        self.init_data = init_data
        self.s = requests.Session()
        self.device = {
            "id": "".join(random.choices(string.ascii_letters + string.digits + "-_", k=24)),
            "fingerprint": "".join(random.choices("0123456789abcdef", k=32)),
            "platform": "android",
        }
        h = dict(STATIC_HEADERS)
        h["authorization"] = f"tma {init_data}"
        self.s.headers.update(h)

    def _post(self, path, body=None, retries=3):
        last = None
        for i in range(retries):
            try:
                r = self.s.post(API_BASE + path, json=body or {}, timeout=30)
                if r.status_code == 200:
                    try: return r.json()
                    except: return {"ok": True}
                if 400 <= r.status_code < 500:
                    # parse JSON error from server (like AD_COOLDOWN)
                    try: return r.json()
                    except: return {"_error": r.text[:200], "_status": r.status_code}
                last = f"HTTP {r.status_code}"
            except Exception as e:
                last = str(e)
            if i < retries - 1:
                state["net_retry"] += 1
                render_ui()
                time.sleep(2)
        return {"_error": last or "max retries"}

    def _get(self, path, retries=3):
        last = None
        for i in range(retries):
            try:
                r = self.s.get(API_BASE + path, timeout=30)
                if r.status_code == 200:
                    try: return r.json()
                    except: return {"ok": True}
                last = f"HTTP {r.status_code}"
            except Exception as e:
                last = str(e)
            if i < retries - 1:
                state["net_retry"] += 1
                render_ui()
                time.sleep(2)
        return {"_error": last or "max retries"}

    def auth(self):
        state["bot_phase"] = "POST /api/auth"
        render_ui()
        return self._post("/api/auth", {"device": self.device})

    def get_tasks(self):
        state["bot_phase"] = "GET /api/tasks"
        render_ui()
        return self._get("/api/tasks")

    def start_ad(self, task_id):
        state["bot_phase"] = f"POST /api/ads/start ({task_id})"
        render_ui()
        return self._post("/api/ads/start", {"placement": "task", "taskId": task_id})

    def click_ad(self, token, count=1):
        state["bot_phase"] = "POST /api/ads/click"
        render_ui()
        return self._post("/api/ads/click", {"token": token, "count": count})

    def complete_ad(self, token, shown=1, clicks=1):
        state["bot_phase"] = "POST /api/ads/complete"
        render_ui()
        return self._post("/api/ads/complete", {"token": token, "shown": shown, "clicks": clicks})


# ============================================================
#  HELPERS
# ============================================================
def apply_auth(auth):
    if not auth or "_error" in auth:
        return False
    u = auth.get("user", {})
    state["user"] = u.get("first_name") or u.get("username") or "-"
    state["balance"] = u.get("balance", 0.0) * 0.00001
    state["total_earn"] = u.get("total_earned", 0.0) * 0.00001
    
    ads_t = 0
    for t in auth.get("tasks", []):
        if t.get("kind") == "ad":
            ads_t += t.get("ad", {}).get("count", 0)
    state["ads_total"] = ads_t
    return True

def parse_init_age(init_data):
    match = re.search(r'auth_date=(\d+)', init_data)
    if match:
        auth_date = int(match.group(1))
        age_sec = time.time() - auth_date
        age_min = int(age_sec / 60)
        if age_min < 60:
            return f"{age_min}m"
        else:
            return f"{age_min//60}h{age_min%60}m"
    return "0m"


# ============================================================
#  CORE — FARM ADS
# ============================================================
def farm_ads(client: Client):
    state["bot_state"] = "RUNNING"
    state["ad_fails"] = 0
    log("Authenticating...", "BOOT")
    auth = client.auth()
    if not apply_auth(auth):
        log(f"Auth failed", "ERR")
        state["ad_fails"] += 1
        state["bot_state"] = "FAILED"
        render_ui()
        return
    log(f"Logged in as {state['user']}", "OK")

    tasks_resp = client.get_tasks()
    tasks = tasks_resp.get("tasks", []) or []
    ad_tasks = [t for t in tasks if t.get("kind") == "ad"]
    
    if not ad_tasks:
        log("No ad tasks available", "WARN")
        state["bot_state"] = "IDLE"
        render_ui()
        return

    log(f"Found {len(ad_tasks)} ad networks", "OK")

    for t in ad_tasks:
        task_id = t["id"]
        title = t.get("title", f"task-{task_id}")
        ad = t.get("ad", {})
        total = ad.get("count", 0)
        done = ad.get("done", 0)
        remaining = total - done

        if remaining <= 0:
            log(f"{title}: done ({done}/{total})", "WARN")
            continue

        log(f"{title}: {remaining} ads left", "INIT")
        state["cycle"] += 1

        for i in range(remaining):
            if state["ad_fails"] >= MAX_FAILURES:
                log("Max failures reached, aborting", "ERR")
                state["bot_state"] = "FAILED"
                render_ui()
                return

            network = ad.get("network", "?")
            
            # Retry loop for a SINGLE ad
            while True:
                start = client.start_ad(task_id)
                
                # Intercept AD_COOLDOWN
                if "error" in start:
                    err_code = start["error"].get("code")
                    if err_code == "AD_COOLDOWN":
                        wait_s = start["error"].get("details", {}).get("seconds", 2)
                        log(f"AD_COOLDOWN: wait {wait_s}s", "WARN")
                        time.sleep(wait_s + 1.5)
                        continue # Retry the SAME ad
                    else:
                        log(f"start err: {start['error'].get('message')}", "ERR")
                        state["ad_fails"] += 1
                        break # Skip to next ad

                if "_error" in start:
                    log(f"start err: {start['_error']}", "ERR")
                    state["ad_fails"] += 1
                    break
                    
                token = start.get("token")
                if not token:
                    log("no token from start", "ERR")
                    state["ad_fails"] += 1
                    break

                # If we reach here, start is success
                try:
                    client.click_ad(token, count=CLICKS_PER_AD)
                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX) + (3 if network in ("adsgram", "gigapub", "usl", "adexium") else 2))

                    comp = client.complete_ad(token, shown=SHOWN_PER_AD, clicks=CLICKS_PER_AD)
                    if "_error" in comp or "error" in comp:
                        log(f"complete err", "ERR")
                        state["ad_fails"] += 1
                        break # Skip to next ad

                    reward_pts = comp.get("reward", 0)
                    reward_usd = reward_pts * 0.00001
                    state["reward"] += reward_usd
                    state["ads_count"] += 1
                    state["last_reward"] = f"+${reward_usd:.6f}"

                    sync = comp.get("sync", {}).get("user", {})
                    if "balance" in sync:
                        state["balance"] = sync["balance"] * 0.00001
                    if "total_earned" in sync:
                        state["total_earn"] = sync["total_earned"] * 0.00001

                    log(f"{title} +{reward_pts} PTS", "OK")
                    time.sleep(random.uniform(1.5, 3.5))
                    break # Ad success, break while loop and go to next i
                    
                except Exception as e:
                    log(f"loop err: {e}", "ERR")
                    state["ad_fails"] += 1
                    break

    log("Farm session done", "OK")
    state["bot_state"] = "DONE"
    render_ui()


# ============================================================
#  CHECK BALANCE
# ============================================================
def check_balance(client):
    if not client:
        log("No init_data — cannot auth", "ERR")
        return False
    log("Fetching balance...", "BOOT")
    auth = client.auth()
    if not apply_auth(auth):
        log(f"Auth failed", "ERR")
        return False
    log(f"Balance = ${state['balance']:.6f}", "OK")
    return True


# ============================================================
#  MENU
# ============================================================
def show_menu():
    _clear()
    print(Fore.CYAN + "╔════════════════════════════════════════╗" + Fore.RESET)
    print(Fore.CYAN + "║  EMOJIFYEARN MENU                      ║" + Fore.RESET)
    print(Fore.CYAN + "╠════════════════════════════════════════╣" + Fore.RESET)
    print(Fore.CYAN + "║  1. Start Farming                      ║" + Fore.RESET)
    print(Fore.CYAN + "║  2. Input InitData                     ║" + Fore.RESET)
    print(Fore.CYAN + "║  3. Check Balance                      ║" + Fore.RESET)
    print(Fore.CYAN + "║  0. Exit                               ║" + Fore.RESET)
    print(Fore.CYAN + "╚════════════════════════════════════════╝" + Fore.RESET)
    print()


def main():
    init_data = os.getenv("INIT_DATA", "").strip()
    client = None
    if init_data:
        client = Client(init_data)
        try:
            if apply_auth(client.auth()):
                state["init_age"] = parse_init_age(init_data)
        except Exception:
            pass

    while True:
        show_menu()
        try:
            choice = input(Fore.CYAN + "[?] Pilih menu > " + Fore.RESET).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            if not client:
                print(Fore.RED + "\n  [!] init_data kosong. Input dulu (menu 2)." + Fore.RESET)
                input(Fore.CYAN + "\n  [Enter] untuk kembali ke menu..." + Fore.RESET)
                continue
            try:
                farm_ads(client)
            except KeyboardInterrupt:
                pass
            print(Fore.CYAN + "\n  [*] Kembali ke menu... (tekan Enter)" + Fore.RESET)
            input()

        elif choice == "2":
            _clear()
            print(Fore.CYAN + "=== INPUT INIT DATA ===" + Fore.RESET)
            print(Fore.WHITE + "Paste init_data (query_id=...&user=...) " + Fore.RESET)
            data = input(Fore.CYAN + "> " + Fore.RESET).strip()
            if data:
                client = Client(data)
                try:
                    if apply_auth(client.auth()):
                        state["init_age"] = parse_init_age(data)
                        print(Fore.GREEN + "  [✔] Auth success." + Fore.RESET)
                    else:
                        print(Fore.RED + "  [✘] Auth failed." + Fore.RESET)
                except Exception as e:
                    print(Fore.RED + f"  [✘] err: {e}" + Fore.RESET)
                time.sleep(1.5)

        elif choice == "3":
            try:
                check_balance(client)
            except Exception as e:
                print(Fore.RED + f"  [✘] err: {e}" + Fore.RESET)
            print(Fore.CYAN + "\n  [*] Kembali ke menu... (tekan Enter)" + Fore.RESET)
            input()

        elif choice in ("0", "q", "exit"):
            print(Fore.YELLOW + "\n  Bye bos." + Fore.RESET)
            break

        else:
            print(Fore.RED + "\n  [!] Pilihan tidak dikenal." + Fore.RESET)
            time.sleep(1)


if __name__ == "__main__":
    main()
