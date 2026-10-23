#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= WARNA NEON =================
def _rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"
GREEN  = _rgb(57, 255, 20)
YELLOW = _rgb(255, 230, 0)
CYAN   = _rgb(0, 255, 240)
PINK   = _rgb(255, 16, 240)
WHITE  = _rgb(235, 235, 235)
GRAY   = _rgb(135, 135, 135)
RESET  = "\033[0m"
BOLD   = "\033[1m"

BASE_URL = "https://cryptofuture.co.in"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(tag, msg, color=WHITE):
    print(f"{GRAY}[{time.strftime('%H:%M:%S')}]{RESET} {color}[{tag.upper():8}]{RESET} {msg}")

# ================= PARSERS =================
def is_logged_in(html):
    """Cek cookie valid atau nggak."""
    return "Logout" in html or "auth/logout" in html

def is_login_page(html):
    return "auth/login" in html or 'name="email"' in html and 'name="password"' in html

def parse_balance(html):
    """Coba berbagai pattern untuk ambil balance."""
    patterns = [
        # Pattern standar: <div class="db-big">0 <span class="db-unit">Coins</span></div>
        r'<div[^>]*class="[^"]*db-big[^"]*"[^>]*>\s*([\d,\.]+)\s*<span[^>]*>Coins</span>',
        # Pattern lebih longgar: db-big dengan angka apapun
        r'class="[^"]*db-big[^"]*"[^>]*>\s*([\d,\.]+)',
        # Pattern alternatif: db-stat-value
        r'class="[^"]*db-stat-value[^"]*"[^>]*>\s*([\d,\.]+)\s*<',
        # Pattern: Balance: xxx Coins
        r'Balance[^0-9]*([\d,\.]+)\s*Coins',
        # Pattern generic: angka diikuti Coins
        r'([\d,]+\.\d+)\s*<span[^>]*>Coins</span>',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except ValueError:
                continue
    return None

def parse_ads(html):
    ads = []
    pattern = r'<h3 class="ptc-ticket-title">(.*?)</h3>[\s\S]*?location\.href=\'https://cryptofuture\.co\.in/ptc/(window|iframe)/(\d+)\''
    matches = re.findall(pattern, html)
    for match in matches:
        ads.append({
            "title": match[0].strip(),
            "type": match[1],
            "id": match[2]
        })
    return ads

def parse_verify_data(html):
    timer_match = re.search(r'var timer = (\d+);', html)
    timer = int(timer_match.group(1)) if timer_match else 10
    csrf_match = re.search(r'name="csrf_token_name" value="([^"]+)"', html)
    csrf = csrf_match.group(1) if csrf_match else None
    return timer, csrf

# ================= BALANCE CHECK =================
def check_session_and_balance(session, headers):
    """
    Return: (status, balance, raw_snippet)
    status: 'ok' | 'expired' | 'error' | 'parse_fail'
    """
    try:
        r = session.get(f"{BASE_URL}/dashboard", headers=headers, verify=False, timeout=30)
        html = r.text

        if is_login_page(html) and not is_logged_in(html):
            return ('expired', None, None)

        if not is_logged_in(html):
            return ('error', None, html[:300])

        balance = parse_balance(html)
        if balance is not None:
            return ('ok', balance, None)

        # Logged in tapi balance gak kebaca
        # Kasih snippet biar user bisa liat struktur
        snippet = ''
        m = re.search(r'<div[^>]*class="[^"]*db-big[^"]*"[^>]*>[\s\S]{0,200}', html)
        if m:
            snippet = m.group(0)
        return ('parse_fail', None, snippet)

    except Exception as e:
        return ('error', None, str(e))

def fmt_bal(v):
    if v is None: return "N/A"
    return f"{v:,.2f}"

# ================= MAIN =================
def main():
    clear()
    print(f"{CYAN}{BOLD}============================================================{RESET}")
    print(f"{CYAN}{BOLD}           CRYPTOFUTURE PTC AUTO-FARMER{RESET}")
    print(f"{PINK}{BOLD}                    By Dev MoneyMaker_w{RESET}")
    print(f"{CYAN}{BOLD}============================================================{RESET}\n")

    print(f"{YELLOW}Paste Cookie lu di sini:{RESET}")
    print(f"{GRAY}(Contoh: ci_session=xxx; csrf_cookie_name=yyy; cf_clearance=zzz;){RESET}")
    cookie_str = input(f"{WHITE}Cookie > {RESET}").strip()

    if not cookie_str:
        print(f"{PINK}[-] Cookie kosong, keluar.{RESET}")
        return

    session = requests.Session()
    for c in cookie_str.split(';'):
        c = c.strip()
        if '=' in c:
            k, v = c.split('=', 1)
            session.cookies.set(k.strip(), v.strip())

    headers = {
        "host": "cryptofuture.co.in",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "referer": f"{BASE_URL}/",
    }

    # ================= CEK COOKIE & BALANCE AWAL =================
    print()
    log("session", "Cek cookie & balance awal...", YELLOW)
    status, pre_balance, snippet = check_session_and_balance(session, headers)

    if status == 'expired':
        print(f"{PINK}[-] Cookie EXPIRED / belum login.{RESET}")
        print(f"{PINK}    Silakan refresh cookie dari browser, terus jalanin ulang.{RESET}")
        return

    if status == 'error':
        print(f"{PINK}[-] Gagal akses dashboard: {snippet}{RESET}")
        return

    if status == 'parse_fail':
        print(f"{PINK}[-] Cookie VALID (udah login), tapi balance gak kebaca.{RESET}")
        print(f"{YELLOW}[!] Markup balance mungkin berubah. Snippet:{RESET}")
        print(f"{GRAY}{snippet}{RESET}")
        print(f"{YELLOW}[!] Lanjut farming aja dulu (saldo awal dianggap 0).{RESET}")
        pre_balance = 0.0

    print(f"{WHITE}  ┌─ Saldo Awal: {GREEN}{fmt_bal(pre_balance)} Coins{RESET}")
    last_balance = pre_balance

    # ================= FETCH PTC =================
    print()
    log("fetch", "Mengambil halaman /ptc...", CYAN)
    try:
        r = session.get(f"{BASE_URL}/ptc", headers=headers, verify=False, timeout=30)
    except Exception as e:
        print(f"{PINK}[-] Gagal fetch /ptc: {e}{RESET}")
        return

    if not is_logged_in(r.text):
        print(f"{PINK}[-] Session mati di /ptc. Cookie expired.{RESET}")
        return

    ads = parse_ads(r.text)
    if not ads:
        print(f"{PINK}[-] Tidak ada iklan PTC yang tersedia saat ini.{RESET}")
        return

    print(f"{GREEN}[+] Ditemukan {len(ads)} iklan PTC.{RESET}\n")

    claimed_count = 0
    fail_streak = 0
    total_earned = 0.0
    balance_fail_count = 0

    # ================= LOOP IKLAN =================
    for idx, ad in enumerate(ads):
        print(f"{CYAN}────────────────────────────────────────────────────────────{RESET}")
        log("info", f"Iklan [{idx+1}/{len(ads)}] : {ad['title']} ({ad['type']})", YELLOW)

        ad_url = f"{BASE_URL}/ptc/{ad['type']}/{ad['id']}"

        try:
            r_ad = session.get(ad_url, headers=headers, verify=False, timeout=30)

            timer, csrf = parse_verify_data(r_ad.text)

            if not csrf:
                print(f"{PINK}[-] Gagal dapet CSRF token, skip iklan ini.{RESET}")
                fail_streak += 1
                if fail_streak >= 3:
                    print(f"{PINK}[-] 3x gagal berturut-turut. Stop.{RESET}")
                    break
                continue

            log("wait", f"Nunggu timer {timer} detik...", YELLOW)

            for i in range(timer, 0, -1):
                sys.stdout.write(f"\r{GRAY}[WAIT]{RESET} {YELLOW}Sisa {i} detik...{RESET}    ")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write(f"\r{GREEN}[OK] Timer selesai!{' ' * 30}{RESET}\n")

            verify_url = f"{BASE_URL}/ptc/verify/{ad['id']}"
            payload = {"csrf_token_name": csrf}

            log("claim", f"Kirim POST /ptc/verify/{ad['id']}...", CYAN)
            r_verify = session.post(verify_url, headers=headers, data=payload,
                                    allow_redirects=True, verify=False, timeout=30)

            if "Coins have been added" in r_verify.text or "Success!" in r_verify.text:
                m = re.search(r'([\d,\.]+)\s*Coins have been added', r_verify.text)
                reward = m.group(1) if m else "?"

                # ================= BALANCE CHECK SETELAH CLAIM =================
                time.sleep(1)
                st, new_balance, snip = check_session_and_balance(session, headers)

                if st == 'ok':
                    diff = new_balance - last_balance
                    total_earned += diff if diff > 0 else 0
                    diff_str = f"{'+' if diff >= 0 else ''}{diff:,.2f}"
                    diff_color = GREEN if diff > 0 else (WHITE if diff == 0 else PINK)
                    log("success",
                        f"Klaim Berhasil! +{reward}c | "
                        f"Balance: {CYAN}{fmt_bal(new_balance)}{WHITE} "
                        f"({diff_color}{diff_str}{WHITE})",
                        GREEN)
                    last_balance = new_balance
                    balance_fail_count = 0
                elif st == 'expired':
                    print(f"{PINK}[!] Cookie expired pas ngecek balance!{RESET}")
                    print(f"{PINK}[!] Balance gak keupdate, tapi claim tetep dihitung.{RESET}")
                    log("success", f"Klaim Berhasil! +{reward}c | Balance: {PINK}COOKIE EXPIRED{RESET}", GREEN)
                    balance_fail_count += 1
                else:
                    log("success", f"Klaim Berhasil! +{reward}c | Balance: {GRAY}N/A{RESET}", GREEN)
                    balance_fail_count += 1

                claimed_count += 1
                fail_streak = 0

                if balance_fail_count >= 5:
                    print(f"{PINK}[!] 5x balance gagal kebaca, tapi farming tetep jalan.{RESET}")
            else:
                log("fail", "Gagal klaim. (limit / captcha / error)", PINK)
                fail_streak += 1
                if fail_streak >= 3:
                    print(f"{PINK}[-] 3x gagal berturut-turut. Stop.{RESET}")
                    break

            time.sleep(2)

        except Exception as e:
            print(f"{PINK}[-] Error: {e}{RESET}")
            fail_streak += 1
            if fail_streak >= 3:
                print(f"{PINK}[-] 3x error berturut-turut. Stop.{RESET}")
                break
            time.sleep(2)

    # ================= POST-BALANCE FINAL =================
    print()
    log("balance", "Cek balance FINAL setelah farming...", YELLOW)
    st, post_balance, snip = check_session_and_balance(session, headers)

    if st != 'ok':
        post_balance = None

    delta = None
    if pre_balance is not None and post_balance is not None:
        delta = post_balance - pre_balance

    print()
    print(f"{CYAN}{BOLD}============================================================{RESET}")
    print(f"{GREEN}{BOLD}                    FARMING SELESAI{RESET}")
    print(f"{CYAN}{BOLD}============================================================{RESET}")
    print(f"{WHITE}  Total Klaim      : {GREEN}{claimed_count}{WHITE} iklan{RESET}")
    print(f"{WHITE}  Saldo Awal       : {YELLOW}{fmt_bal(pre_balance)} Coins{RESET}")
    print(f"{WHITE}  Saldo Akhir      : {YELLOW}{fmt_bal(post_balance)} Coins{RESET}")
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        color = GREEN if delta >= 0 else PINK
        print(f"{WHITE}  Selisih (Delta)  : {color}{sign}{delta:,.2f} Coins{RESET}")
    else:
        print(f"{WHITE}  Selisih (Delta)  : {PINK}N/A (session mati){RESET}")
    print(f"{CYAN}{BOLD}============================================================{RESET}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{PINK}[!] Dihentikan oleh user.{RESET}")
