import os
import json
import time
import random
import re
import sys
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# ================= KONFIGURASI =================
CONFIG_FILE = "plus_config.json"
BASE_URL = "https://gameblog.in"
SITEKEY = "915157bc-24e1-4725-9c3d-d19190c9cce6"
USER_AGENT = "Mozilla/5.0 (Linux; Android 16; K) Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)"
# ===============================================

# Warna
R, G, Y, B, M, C, W, X = '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[97m', '\033[0m'

BANNER = f"""
{W} $$$$$$\\  $$$$$$$\\ $$\\     $$\\ $$$$$$$\\ $$$$$$$$\\  $$$$$$\\        {W}
{W}$$  __$$\\ $$  __$$\\\\$$\\   $$  |$$  __$$\\__$$  __|$$  __$$\\       {W}
{W}$$ /  \\__|$$ |  $$ |\\$$\\ $$  / $$ |  $$ |  $$ |   $$ /  $$ |      {W}
{W}$$ |      $$$$$$$  | \\$$$$  /  $$$$$$$  |  $$ |   $$ |  $$ |      {W}
{W}$$ |      $$  __$$<   \\$$  /   $$  ____/   $$ |   $$ |  $$ |      {W}
{W}$$ |  $$\\ $$ |  $$ |   $$ |    $$ |        $$ |   $$ |  $$ |      {W}
{W}\\$$$$$$  |$$ |  $$ |   $$ |    $$ |        $$ |    $$$$$$  |      {W}
{W} \\______/ \\__|  \\__|   \\__|    \\__|        \\__|    \\______/       {W}
                                                                  
{C}=============================================================={X}
{G}👨‍💻 ScriptMaker : MoneyMaker_w{X}
{G}📢 TG          : https://t.me/+f3QBLkR5D8k4YzNl{X}
{G}🤖 Bot         : PlusCrypto{X}
{G}🧩 Solver      : Waryono.my.id{X}
{C}=============================================================={X}
"""

CURRENCIES = {
    "1": "DOGE", "2": "TRX", "3": "DGB", "4": "LTC",
    "5": "USDT", "6": "ETH", "7": "BCH", "8": "DASH",
    "9": "FEY", "10": "ZEC", "11": "BNB", "12": "SOL",
    "13": "XRP", "14": "POL", "15": "TON", "16": "USDC",
    "17": "XMR", "19": "TRUMP", "20": "PEPE"
}

class PlusCryptoClaimer:
    def __init__(self):
        self.initdata = ""
        self.email = ""
        self.api_key = ""
        self.selected = "5"
        self.proxy = None
        self.csrf_token = ""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.total_claimed = 0.0
        self.success = 0
        self.failed = 0
        self.load_config()
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    self.initdata = cfg.get("initdata", "")
                    self.email = cfg.get("email", "")
                    self.api_key = cfg.get("api_key", "")
                    self.selected = cfg.get("selected", "5")
                    self.proxy = cfg.get("proxy", None)
                    self.total_claimed = cfg.get("total_claimed", 0.0)
                    self.success = cfg.get("success", 0)
                    self.failed = cfg.get("failed", 0)
            except:
                pass
    
    def save_config(self):
        cfg = {
            "initdata": self.initdata,
            "email": self.email,
            "api_key": self.api_key,
            "selected": self.selected,
            "proxy": self.proxy,
            "total_claimed": self.total_claimed,
            "success": self.success,
            "failed": self.failed
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    
    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_csrf_token(self, html):
        match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        return match.group(1) if match else None
    
    def login(self):
        print(f"{C}🔐 [LOGIN]      {W}Authenticating with Telegram...{X}")
        try:
            home_url = f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/index-home"
            resp = self.session.get(home_url, timeout=30)
            if resp.status_code != 200:
                print(f"{R}❌ [ERROR]     {W}Home page load failed: {resp.status_code}{X}")
                return False
            
            self.csrf_token = self.get_csrf_token(resp.text)
            if not self.csrf_token:
                print(f"{R}❌ [ERROR]     {W}CSRF token not found{X}")
                return False
            print(f"{G}🛡️  [CSRF]       {W}Token obtained{X}")
            
            verify_url = f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/verify-telegram-user"
            headers = {
                "Content-Type": "application/json",
                "X-CSRF-TOKEN": self.csrf_token,
                "X-Requested-With": "org.telegram.messenger.web",
                "Origin": BASE_URL,
                "Referer": home_url
            }
            payload = {"initData": self.initdata, "source": "organic"}
            resp = self.session.post(verify_url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200 and resp.json().get("status") in ["valid", "validated"]:
                print(f"{G}✅ [SUCCESS]    {W}Authentication successful{X}")
                return True
            else:
                print(f"{R}❌ [ERROR]     {W}Authentication failed: {resp.text}{X}")
                return False
        except Exception as e:
            print(f"{R}❌ [ERROR]     {W}Login error: {e}{X}")
            return False
    
    # ============================================================
    # SOLVER WARYONO.MY.ID
    # ============================================================
    def solve_captcha(self, page_url, retries=3):
        """hCaptcha solver via Waryono.my.id (POST JSON submit + GET poll)"""
        for attempt in range(retries):
            print(f"{C}🤖 [HCAPTCHA]   {W}Attempt {attempt+1}/{retries} (Waryono){X}")
            try:
                # ─── STEP 1: Submit task via POST JSON ───
                submit_url = "https://api.waryono.my.id/in.php"
                payload = {
                    "apikey":  self.api_key,
                    "methods": "hcaptcha",
                    "domain":  page_url,
                    "sitekey": SITEKEY,
                    "json":    1
                }
                headers = {
                    "User-Agent":   USER_AGENT,
                    "Content-Type": "application/json"
                }
                resp = requests.post(
                    submit_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                if resp.status_code != 200:
                    print(f"{R}❌ [ERROR]     {W}HTTP {resp.status_code}{X}")
                    time.sleep(2)
                    continue
                
                try:
                    data = resp.json()
                except Exception:
                    print(f"{R}❌ [ERROR]     {W}Invalid JSON response: {resp.text[:120]}{X}")
                    time.sleep(2)
                    continue
                
                if data.get("status") != 1:
                    err = data.get("request", "Unknown")
                    print(f"{R}❌ [ERROR]     {W}Submission error: {err}{X}")
                    if "ERROR_KEY" in err or "ERROR_WRONG" in err or "ERROR_ZERO_BALANCE" in err:
                        print(f"{R}💀 [FATAL]     {W}API key/saldo issue, check your key{X}")
                        return None
                    time.sleep(2)
                    continue
                
                job_id = data["request"]
                print(f"{G}🎫 [JOB]        {W}ID received: {job_id}{X}")
                
                # ─── STEP 2: Poll for result via GET ───
                max_polls = 60
                for _ in range(max_polls):
                    time.sleep(3)
                    try:
                        poll = requests.get(
                            "https://api.waryono.my.id/res.php",
                            params={
                                "apikey": self.api_key,
                                "action": "get",
                                "id":     job_id,
                                "json":   1
                            },
                            headers=headers,
                            timeout=30
                        )
                        if poll.status_code != 200:
                            continue
                        
                        poll_data = poll.json()
                        
                        if poll_data.get("status") == 1 and poll_data.get("request"):
                            token = poll_data["request"]
                            print(f"{G}✅ [SOLVED]     {W}Token obtained{X}")
                            return token
                        
                        req_val = poll_data.get("request", "")
                        
                        if "ERROR" in req_val:
                            print(f"{R}❌ [ERROR]     {W}Poll error: {req_val}{X}")
                            break
                        
                        if req_val == "CAPCHA_NOT_READY":
                            sys.stdout.write(f"\r⏳ [WAIT]       {W}Solving...{X}   ")
                            sys.stdout.flush()
                            continue
                        
                        print(f"{R}❌ [ERROR]     {W}Unexpected poll response: {poll_data}{X}")
                        break
                    
                    except Exception as e:
                        print(f"{R}❌ [ERROR]     {W}Poll exception: {e}{X}")
                        continue
                
                print()
            
            except Exception as e:
                print(f"{R}❌ [ERROR]     {W}Exception: {e}{X}")
                time.sleep(2)
        
        print(f"{R}❌ [FAILED]     {W}Captcha not solved after {retries} attempts{X}")
        return None
    
    def get_faucet_page(self, currency_id, currency_name):
        print(f"{C}🌐 [NAVIGATE]   {W}Getting {currency_name} faucet page...{X}")
        try:
            home_url = f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/index-home"
            resp = self.session.get(home_url, timeout=30)
            if resp.status_code != 200:
                print(f"{R}❌ [ERROR]     {W}Home page failed{X}")
                return None
            pattern = rf'href="([^"]*manual-faucet/{currency_id}/{currency_name}[^"]*)"'
            match = re.search(pattern, resp.text)
            if not match:
                print(f"{R}❌ [ERROR]     {W}Claim link not found for {currency_name}{X}")
                return None
            claim_url = match.group(1)
            if not claim_url.startswith('http'):
                claim_url = BASE_URL + claim_url
            print(f"{G}🔎 [FOUND]      {W}Claim URL found{X}")
            resp2 = self.session.get(claim_url, timeout=30)
            if resp2.status_code != 200:
                print(f"{R}❌ [ERROR]     {W}Claim page load failed{X}")
                return None
            new_csrf = self.get_csrf_token(resp2.text)
            if new_csrf:
                self.csrf_token = new_csrf
            return resp2.text
        except Exception as e:
            print(f"{R}❌ [ERROR]     {W}{e}{X}")
            return None
    
    def wait_for_countdown(self, html):
        match = re.search(r'data-seconds="(\d+)"', html)
        if match:
            seconds = int(match.group(1))
            print(f"{Y}⏳ [TIMER]      {W}Waiting {seconds} seconds...{X}")
            for i in range(seconds, 0, -1):
                sys.stdout.write(f"\r{Y}⌛ [WAIT]       {W}{i} seconds remaining...{X}   ")
                sys.stdout.flush()
                time.sleep(1)
            print()
            return True
        return False
    
    def submit_claim(self, currency_id, currency_name, captcha_token):
        print(f"{C}📤 [SUBMIT]     {W}Submitting claim...{X}")
        try:
            claim_url = f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/verify-manual-faucet/{currency_id}"
            data = {
                "_token": self.csrf_token,
                "email": self.email,
                "g-recaptcha-response": captcha_token,
                "h-captcha-response": captcha_token,
                "countdown_value": "0",
                "submitbtn": ""
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRF-TOKEN": self.csrf_token,
                "X-Requested-With": "org.telegram.messenger.web",
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/manual-faucet/{currency_id}/{currency_name}"
            }
            resp = self.session.post(claim_url, headers=headers, data=data, timeout=30, allow_redirects=True)
            
            if "alert-success" in resp.text or "successfully added" in resp.text:
                reward_match = re.search(r'([\d.]+)\s*' + currency_name, resp.text, re.IGNORECASE)
                if reward_match:
                    amount = float(reward_match.group(1))
                    self.total_claimed += amount
                    print(f"{G}💰 [SUCCESS]    {W}Claimed {amount} {currency_name}! 🎉🔥{X}")
                else:
                    print(f"{G}✅ [SUCCESS]    {W}Claim successful!{X}")
                self.success += 1
                self.save_config()
                return True
            else:
                print(f"{Y}📡 HTTP Status : {resp.status_code}{X}")
                print(f"{Y}📍 Final URL   : {resp.url}{X}")
                clean_text = re.sub(r'<[^>]+>', ' ', resp.text)
                snippet = clean_text[:300].strip()
                print(f"{Y}📄 Response    : {snippet}{'...' if len(clean_text) > 300 else ''}{X}")
                
                error_match = re.search(r'alert-danger[^>]*>(.*?)</div>', resp.text, re.DOTALL)
                if error_match:
                    err_msg = re.sub(r'<[^>]+>', '', error_match.group(1)).strip()
                    print(f"{R}❌ [FAILED]     {W}{err_msg}{X}")
                else:
                    if "login" in resp.url.lower() or "signin" in resp.url.lower() or "auth" in resp.url.lower():
                        print(f"{R}❌ [FAILED]     {W}Session expired / redirected to login!{X}")
                    elif resp.status_code in [302, 303, 307, 308]:
                        print(f"{R}❌ [FAILED]     {W}Redirect detected (maybe session expired){X}")
                    elif "csrf" in resp.text.lower() and "token" in resp.text.lower():
                        print(f"{R}❌ [FAILED]     {W}CSRF token mismatch / invalid{X}")
                    else:
                        print(f"{R}❌ [FAILED]     {W}Claim failed (unknown reason){X}")
                self.failed += 1
                self.save_config()
                return False
        except Exception as e:
            print(f"{R}❌ [ERROR]     {W}{e}{X}")
            self.failed += 1
            self.save_config()
            return False
    
    def claim_currency(self, currency_id, currency_name):
        print(f"\n{C}{'='*54}{X}")
        print(f"{C}╔══════════════════════════════════════════════════════════════╗{X}")
        print(f"{C}║                 💵🔥 CLAIMING {currency_name} 🔥💵                     ║{X}")
        print(f"{C}║                      🆔 ID: {currency_id}                              ║{X}")
        print(f"{C}╚══════════════════════════════════════════════════════════════╝{X}")
        
        if not self.login():
            return False
        
        html = self.get_faucet_page(currency_id, currency_name)
        if not html:
            return False
        
        self.wait_for_countdown(html)
        
        page_url = f"{BASE_URL}/apps-tgmini/plus-crypto-faucet-bot/manual-faucet/{currency_id}/{currency_name}"
        print(f"{C}🧩                    HCAPTCHA (Waryono){X}")
        print(f"{C}{'='*54}{X}")
        token = self.solve_captcha(page_url)
        if not token:
            print(f"{R}❌ [ERROR]     {W}Captcha solving failed{X}")
            return False
        
        time.sleep(random.uniform(1, 2))
        success = self.submit_claim(currency_id, currency_name, token)
        if success:
            print(f"{G}💵 [BALANCE]    {W}Reward successfully received! 💎{X}")
        return success
    
    def claim_loop(self):
        if not self.initdata or not self.email or not self.api_key:
            print(f"{R}❌ [ERROR]     {W}Config incomplete, please edit config first{X}")
            input("Press Enter...")
            return
        cid = self.selected
        name = CURRENCIES[cid]
        print(f"{G}🚀 [INFO]      {W}Starting auto claim loop for {name}{X}")
        print(f"{Y}🔄 Press Ctrl+C to stop{X}")
        try:
            while True:
                self.claim_currency(cid, name)
                wait = random.randint(60, 80)
                print(f"{Y}⏳ [WAIT]      {W}Next claim in {wait}s{X}")
                for i in range(wait, 0, -1):
                    sys.stdout.write(f"\r{Y}⌛ [WAIT]       {W}{i}s remaining...{X}   ")
                    sys.stdout.flush()
                    time.sleep(1)
                print()
        except KeyboardInterrupt:
            print(f"\n{G}🛑 [STOPPED]   {W}Auto loop terminated{X}")
            input("Press Enter...")
    
    def edit_config(self):
        while True:
            self.clear()
            print(BANNER)
            print(f"\n{C}╔══════════════════════════════════════════════════════════════╗")
            print(f"║ {W}                    EDIT CONFIG{C}                                  ║")
            print(f"╚══════════════════════════════════════════════════════════════╝{X}")
            print(f"\n  {C}[{W}1{C}] {Y}Set InitData (Telegram auth){X}")
            print(f"  {C}[{W}2{C}] {Y}Set Email address{X}")
            print(f"  {C}[{W}3{C}] {Y}Set API Key (Waryono.my.id){X}")
            print(f"  {C}[{W}4{C}] {Y}Select default currency{X}")
            print(f"  {C}[{W}5{C}] {Y}Set proxy (optional){X}")
            print(f"  {C}[{W}0{C}] {R}Back{X}")
            print(f"\n  Current: InitData={G}{'SET' if self.initdata else 'NOT SET'}{X}")
            print(f"  Email={G}{self.email or 'NOT SET'}{X}")
            print(f"  API Key={G}{self.api_key[:8]+'...' if self.api_key else 'NOT SET'}{X}")
            print(f"  Currency={G}{CURRENCIES.get(self.selected, 'N/A')}{X}")
            print(f"  Proxy={G}{self.proxy or 'OFF'}{X}")
            choice = input(f"\n{C}═⫸ {W}Select: {C}").strip()
            if choice == "1":
                inp = input(f"{M}[?] {W}Paste InitData: {C}").strip()
                if inp:
                    self.initdata = inp
                    self.save_config()
                    print(f"{G}[SUCCESS] InitData saved{X}")
                else:
                    print(f"{R}[ERROR] Cannot be empty{X}")
                time.sleep(1)
            elif choice == "2":
                inp = input(f"{M}[?] {W}Enter Faucetpay Email: {C}").strip()
                if inp:
                    self.email = inp
                    self.save_config()
                    print(f"{G}[SUCCESS] Email saved{X}")
                else:
                    print(f"{R}[ERROR] Cannot be empty{X}")
                time.sleep(1)
            elif choice == "3":
                inp = input(f"{M}[?] {W}Enter Waryono API Key: {C}").strip()
                if inp:
                    self.api_key = inp
                    self.save_config()
                    print(f"{G}[SUCCESS] API Key saved{X}")
                else:
                    print(f"{R}[ERROR] Cannot be empty{X}")
                time.sleep(1)
            elif choice == "4":
                print(f"\n{C}Available currencies:{X}")
                for cid, name in CURRENCIES.items():
                    print(f"  {C}[{cid}] {name}{X}")
                inp = input(f"{M}[?] {W}Select ID: {C}").strip()
                if inp in CURRENCIES:
                    self.selected = inp
                    self.save_config()
                    print(f"{G}[SUCCESS] Default set to {CURRENCIES[inp]}{X}")
                else:
                    print(f"{R}[ERROR] Invalid ID{X}")
                time.sleep(1)
            elif choice == "5":
                inp = input(f"{M}[?] {W}Proxy (http://ip:port) or Enter to clear: {C}").strip()
                self.proxy = inp if inp else None
                self.save_config()
                print(f"{G}[SUCCESS] Proxy {'set' if self.proxy else 'cleared'}{X}")
                time.sleep(1)
            elif choice == "0":
                break
    
    def dashboard(self):
        self.clear()
        print(BANNER)
        
        email_display = self.email
        if len(email_display) > 10:
            email_display = email_display[:4] + "####" + email_display[-7:]
        
        print(f"\n{C}=============================================================={X}")
        print(f"{C}                 🔐💎 ACCOUNT STATUS 💎🔐{X}")
        print(f"{C}=============================================================={X}")
        print(f"{G}🆔 InitData  » {W}{'✅ SET' if self.initdata else '❌ NOT SET'}{X}")
        print(f"{G}📧 Email     » {W}{email_display if self.email else '❌ NOT SET'}{X}")
        print(f"{G}🔑 API Key   » {W}{self.api_key[:8]+'...' if self.api_key else '❌ NOT SET'}{X}")
        print(f"{G}🧩 Solver    » {W}WARYONO.MY.ID{X}")
        print(f"{G}🌐 Proxy     » {W}{'🟢 ' + self.proxy if self.proxy else '🔴 OFF'}{X}")
        print(f"{G}💰 Currency  » {W}{CURRENCIES.get(self.selected, 'N/A')}{X}")
        
        print(f"\n{C}=============================================================={X}")
        print(f"{C}                📊🔥 CLAIM STATISTICS 🔥📊{X}")
        print(f"{C}=============================================================={X}")
        print(f"{G}✅ Successful » {W}{self.success}{X}")
        print(f"{R}❌ Failed     » {W}{self.failed}{X}")
        print(f"{G}💰 Total      » {W}{self.total_claimed:.8f} {CURRENCIES.get(self.selected, '')}{X}")
        
        print(f"\n{C}=============================================================={X}")
        print(f"{C}                     🚀 MAIN MENU 🚀{X}")
        print(f"{C}=============================================================={X}")
    
    def main_menu(self):
        while True:
            self.dashboard()
            print(f"\n  {C}[{W}1{C}] {G}START AUTO CLAIM LOOP{X}")
            print(f"  {C}[{W}2{C}] {Y}EDIT CONFIGURATION{X}")
            print(f"  {C}[{W}3{C}] {M}EXIT{X}")
            print()
            choice = input(f"{C}═⫸ {W}Select: {C}").strip()
            if choice == "1":
                if not self.initdata or not self.email or not self.api_key:
                    print(f"{R}❌ [ERROR]     {W}Config incomplete, please edit config first{X}")
                    time.sleep(2)
                    continue
                self.claim_loop()
            elif choice == "2":
                self.edit_config()
            elif choice == "3":
                print(f"{G}Exiting...{X}")
                break

if __name__ == "__main__":
    bot = PlusCryptoClaimer()
    bot.main_menu()
