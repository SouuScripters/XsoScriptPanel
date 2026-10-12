#!/usr/bin/env python3
"""
CoinPayuFree Bot - Complete Automation Script
Cookie-Based Login (No reCAPTCHA)
Updated: Turnstile solvers with 3 APIs (MultiBot, Tertuyul, Waryono, BypassAllShortLink)
"""

import os
import sys
import time
import json
import re
import random
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# PSYCHO UI - Complete UI Framework
# ============================================================
class PsychoUI:
    def __init__(self, typing_speed=0.002):
        self.speed = typing_speed
        self.success_history = []
        self.max_history = 999999999
        
        # Premium Color Palette
        self.pri = "\033[38;5;147m"
        self.sec = "\033[38;5;123m"
        self.gray = "\033[38;5;243m"
        self.green = "\033[38;5;120m"
        self.red = "\033[38;5;204m"
        self.yellow = "\033[38;5;223m"
        self.gold = "\033[38;5;220m"
        self.pink = "\033[38;5;212m"
        self.orange = "\033[38;5;214m"
        self.purple = "\033[38;5;135m"
        self.reset = "\033[0m"
        
        self.brand = "PSYCHO BOT"
        self.author = "MoneyMaker_w"
        self.web = "Cookie"
        self.version = "6.8"
        self.user = None
        self.balance = None
        
        self.banner_printed = False
        self.faucet_name = "CoinPayuFree"

    def show_banner(self, faucet_name="CoinPayuFree", show_success=True):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.faucet_name = faucet_name
        self.banner_printed = True
        
        colors = ['\033[38;5;147m', '\033[38;5;123m', '\033[38;5;220m']
        banner_lines = [
            r"██████╗ ██████╗ ██╗███╗   ██╗██████╗  █████╗ ██╗   ██╗███████╗██████╗ ███████╗███████╗",
            r"██╔════╝██╔═══██╗██║████╗  ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗██╔════╝██╔════╝",
            r"██║     ██║   ██║██║██╔██╗ ██║██████╔╝███████║ ╚████╔╝ █████╗  ██████╔╝█████╗  █████╗  ",
            r"██║     ██║   ██║██║██║╚██╗██║██╔═══╝ ██╔══██║  ╚██╔╝  ██╔══╝  ██╔═══╝ ██╔══╝  ██╔══╝  ",
            r"╚██████╗╚██████╔╝██║██║ ╚████║██║     ██║  ██║   ██║   ███████╗██║     ███████╗███████╗",
            r" ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝     ╚══════╝╚══════╝"
        ]
        
        max_len = max(len(line) for line in banner_lines)
        box_width = max_len + 4
        
        for idx, line in enumerate(banner_lines):
            color = colors[idx % len(colors)]
            print(f"{color}{line}{self.reset}")
            time.sleep(0.01)
        
        print()
        
        top_bottom = "┌" + "─" * (box_width - 2) + "┐"
        print(f" {self.gray}{top_bottom}{self.reset}")
        
        left = f" Engine   » {self.gold}{faucet_name}{self.reset}"
        right = f" Version  » {self.sec}{self.version}{self.reset}"
        pad = box_width - len(left) - len(right) - 6
        if pad < 0: pad = 2
        line = f"│ {left}{' ' * pad}│ {right} │"
        print(f" {self.gray}{line}{self.reset}")
        
        left = f" Maker    » {self.pink}{self.author}{self.reset}"
        right = f" Network  » {self.sec}{self.web}{self.reset}"
        pad = box_width - len(left) - len(right) - 6
        if pad < 0: pad = 2
        line = f"│ {left}{' ' * pad}│ {right} │"
        print(f" {self.gray}{line}{self.reset}")
        
        if self.user and self.balance is not None:
            left = f" User     » {self.green}{self.user}{self.reset}"
            right = f" Balance  » {self.gold}{self.balance}{self.reset} coins"
            pad = box_width - len(left) - len(right) - 6
            if pad < 0: pad = 2
            line = f"│ {left}{' ' * pad}│ {right} │"
            print(f" {self.gray}{line}{self.reset}")
        else:
            pad = box_width - 4
            line = f"│{' ' * pad}│"
            print(f" {self.gray}{line}{self.reset}")
        
        print(f" {self.gray}└{'─' * (box_width - 2)}┘{self.reset}\n")

        if show_success and self.success_history:
            for past_success in self.success_history[-self.max_history:]:
                print(f" {self.green}[SUCCESS] {past_success}{self.reset}")
                print(f" {self.gray}────────────────────────────────────────────────────────────{self.reset}")
            print()

    def refresh_banner(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
        colors = ['\033[38;5;147m', '\033[38;5;123m', '\033[38;5;220m']
        banner_lines = [
            r"██████╗ ██████╗ ██╗███╗   ██╗██████╗  █████╗ ██╗   ██╗███████╗██████╗ ███████╗███████╗",
            r"██╔════╝██╔═══██╗██║████╗  ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗██╔════╝██╔════╝",
            r"██║     ██║   ██║██║██╔██╗ ██║██████╔╝███████║ ╚████╔╝ █████╗  ██████╔╝█████╗  █████╗  ",
            r"██║     ██║   ██║██║██║╚██╗██║██╔═══╝ ██╔══██║  ╚██╔╝  ██╔══╝  ██╔═══╝ ██╔══╝  ██╔══╝  ",
            r"╚██████╗╚██████╔╝██║██║ ╚████║██║     ██║  ██║   ██║   ███████╗██║     ███████╗███████╗",
            r" ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝     ╚══════╝╚══════╝"
        ]
        
        max_len = max(len(line) for line in banner_lines)
        box_width = max_len + 4
        
        for idx, line in enumerate(banner_lines):
            color = colors[idx % len(colors)]
            print(f"{color}{line}{self.reset}")
        
        print()
        
        top_bottom = "┌" + "─" * (box_width - 2) + "┐"
        print(f" {self.gray}{top_bottom}{self.reset}")
        
        left = f" Engine   » {self.gold}{self.faucet_name}{self.reset}"
        right = f" Version  » {self.sec}{self.version}{self.reset}"
        pad = box_width - len(left) - len(right) - 6
        if pad < 0: pad = 2
        line = f"│ {left}{' ' * pad}│ {right} │"
        print(f" {self.gray}{line}{self.reset}")
        
        left = f" Maker    » {self.pink}{self.author}{self.reset}"
        right = f" Network  » {self.sec}{self.web}{self.reset}"
        pad = box_width - len(left) - len(right) - 6
        if pad < 0: pad = 2
        line = f"│ {left}{' ' * pad}│ {right} │"
        print(f" {self.gray}{line}{self.reset}")
        
        if self.user and self.balance is not None:
            left = f" User     » {self.green}{self.user}{self.reset}"
            right = f" Balance  » {self.gold}{self.balance}{self.reset} coins"
            pad = box_width - len(left) - len(right) - 6
            if pad < 0: pad = 2
            line = f"│ {left}{' ' * pad}│ {right} │"
            print(f" {self.gray}{line}{self.reset}")
        else:
            pad = box_width - 4
            line = f"│{' ' * pad}│"
            print(f" {self.gray}{line}{self.reset}")
        
        print(f" {self.gray}└{'─' * (box_width - 2)}┘{self.reset}\n")

        if self.success_history:
            for past_success in self.success_history[-self.max_history:]:
                print(f" {self.green}[SUCCESS] {past_success}{self.reset}")
                print(f" {self.gray}────────────────────────────────────────────────────────────{self.reset}")
            print()

    def set_user_info(self, user, balance):
        self.user = user
        self.balance = balance

    def info(self, message):
        print(f"  {self.gray}• {self.reset}{message}")

    def warning(self, message):
        print(f"  {self.yellow}⚠ {self.reset}{message}")

    def error(self, message):
        print(f"  {self.red}✘ {self.reset}{message}")

    def success(self, message):
        self.success_history.append(message)
        if len(self.success_history) > self.max_history:
            self.success_history = self.success_history[-self.max_history:]
        self.refresh_banner()

    def show_menu_banner(self, faucet_name="CoinPayuFree"):
        self.show_banner(faucet_name, False)

    def inline_status(self, text, color="\033[38;5;223m"):
        max_len = 80
        if len(text) > max_len:
            text = text[:max_len-3] + "..."
        sys.stdout.write(f"\r  {color}▶ {self.reset}{text}")
        sys.stdout.flush()

    def clear_inline(self):
        sys.stdout.write("\r" + " " * 90 + "\r")
        sys.stdout.flush()

    # ========== UPDATED COUNTDOWN – CLEAN & NON-SPAM ==========
    def countdown(self, seconds, label="Interval Control"):
        if seconds <= 0:
            return
        total = seconds
        for i in range(total, -1, -1):
            if i == 0:
                break
            m, s = divmod(i, 60)
            if m >= 60:
                h, m = divmod(m, 60)
                time_str = f"{h}h {m}m {s}s"
            else:
                time_str = f"{m}m {s}s"
            pct = int(((total - i) / total) * 100)
            sys.stdout.write(f"\r  {self.yellow}⏳ {self.reset}{label}: {self.sec}{time_str}{self.reset} [ {self.gold}{pct}%{self.reset} ]")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

bot = PsychoUI(typing_speed=0.002)

# ============================================================
# COLOR CODES FOR MENU
# ============================================================
C = {
    'header': '\033[38;5;147m',
    'menu': '\033[38;5;123m',
    'green': '\033[38;5;120m',
    'red': '\033[38;5;204m',
    'yellow': '\033[38;5;223m',
    'gray': '\033[38;5;243m',
    'gold': '\033[38;5;220m',
    'pink': '\033[38;5;212m',
    'orange': '\033[38;5;214m',
    'purple': '\033[38;5;135m',
    'reset': '\033[0m'
}

# ============================================================
# CONFIGURATION
# ============================================================
BASE_URL = "https://coinpayufree.com"
LOGIN_URL = f"{BASE_URL}/login"
LOGIN_ACTION = f"{BASE_URL}/auth/login"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
FAUCET_URL = f"{BASE_URL}/faucet"
FAUCET_CLAIM_URL = f"{BASE_URL}/faucet/verify"
WHEEL_URL = f"{BASE_URL}/wheel"
WHEEL_START_URL = f"{BASE_URL}/wheel/start_claim"
WHEEL_VERIFY_URL = f"{BASE_URL}/wheel/complete_claim"
DAILY_BONUS_URL = f"{BASE_URL}/bonus"
DAILY_CLAIM_URL = f"{BASE_URL}/bonus/claim"
AUTO_FAUCET_URL = f"{BASE_URL}/auto"
AUTO_FAUCET_VERIFY_URL = f"{BASE_URL}/auto/verify"
WITHDRAWAL_URL = f"{BASE_URL}/withdraw"
WITHDRAWAL_POST_URL = f"{BASE_URL}/dashboard/withdraw"

TURNSTILE_SITEKEY = "0x4AAAAAAAhdmcfO-UZf-p6L"
RECAPTCHA_SITEKEY = "6LfrI8cpAAAAAD9fihZI_2p3IyMRNiPGwHwuYkr-"

SESSION_FILE = "coinpayu_session.json"
CONFIG_FILE = "coinpayu_config.json"

# ============================================================
# COOLDOWN TIMERS (configurable)
# ============================================================
MANUAL_FAUCET_COOLDOWN = 3900      # 65 minutes
MANUAL_FAUCET_CSRF_RETRY = 1000   # If no CSRF, wait 1000s
WHEEL_COOLDOWN = 960               # 16 minutes
AUTO_FAUCET_WAIT = 120             # 2 minutes

# ============================================================
# OCR ANTIBOT SOLVER (HYBRID)
# ============================================================
OCR_SERVER = "https://ocr-server-82fr.onrender.com/antibot"
OCR_API = "https://nice-pet-sandboxhubaaa-600a0136.koyeb.app/in.php"
OCR_RES = "https://nice-pet-sandboxhubaaa-600a0136.koyeb.app/res.php"
OCR_API_KEY = "free_ocr_api_key_2024"

OCR_CORRECTIONS = {
    '·': '+', '•': '+', '●': '+', '∘': '+', '×': '*', 'x': '*', 'X': '*', '÷': '/', ':': '/', '−': '-', '—': '-', '–': '-',
    '94': '4', '94.': '4', '94,': '4', '3·2': '3+2', '32': '3+2', '3 2': '3+2', '2·8': '2+8', '28': '2+8', '2 8': '2+8',
    '8·6': '8+6', '86': '8+6', '8 6': '8+6',
    'one': '1', 'won': '1', 'own': '1', 'two': '2', 'too': '2', 'to': '2', 'three': '3', 'tree': '3', 'free': '3',
    'four': '4', 'for': '4', 'frog': '4', 'five': '5', 'fire': '5', 'fine': '5', 'six': '6', 'sun': '6', 'sin': '6',
    'seven': '7', 'even': '7', 'seen': '7', 'eight': '8', 'fight': '8', 'night': '8', 'nine': '9', 'win': '9', 'wine': '9',
    'ten': '10', 'pen': '10', 'hen': '10',
    'lion': 'lion', 'l!on': 'lion', 'l1on': 'lion', '10n': 'lion', 'cat': 'cat', 'c@t': 'cat', 'c4t': 'cat',
    'dog': 'dog', 'd0g': 'dog', 'd09': 'dog', 'zoo': 'zoo', 'z00': 'zoo', 'zo0': 'zoo', 'cow': 'cow', 'c0w': 'cow',
    'rat': 'rat', 'r@t': 'rat', 'fox': 'fox', 'f0x': 'fox', 'pig': 'pig', 'p!g': 'pig', 'bird': 'bird', 'b!rd': 'bird',
    'fish': 'fish', 'f!sh': 'fish', 'bear': 'bear', 'be@r': 'bear', 'wolf': 'wolf', 'w0lf': 'wolf', 'oso': 'oso',
    '0s0': 'oso', 'o5o': 'oso', 'lol': 'lol', 'l0l': 'lol', '1o1': 'lol', 'ooz': 'ooz', '00z': 'ooz', 'o0z': 'ooz',
}

ROMAN_MAP = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10,
    'll': 2, 'lll': 3, 'lv': 4, 'vl': 6, 'vll': 7, 'vlll': 8, 'lx': 11, 'l': 1
}

class PatternLearner:
    def __init__(self):
        self.patterns = defaultdict(list)
        self.ocr_corrections = {}
        
    def learn_pattern(self, main_parts, option_texts, successful_order):
        pattern_key = "->".join(main_parts)
        pattern_data = {'main_parts': main_parts, 'option_texts': option_texts, 'order': successful_order, 'timestamp': time.time()}
        self.patterns[pattern_key].append(pattern_data)
        for rel, text in option_texts.items():
            for part in main_parts:
                if part in text or text in part:
                    self.ocr_corrections[text] = part
    
    def match_pattern(self, main_parts, option_texts):
        pattern_key = "->".join(main_parts)
        if pattern_key in self.patterns:
            for pattern in self.patterns[pattern_key]:
                if len(pattern['option_texts']) == len(option_texts):
                    matched = sum(1 for rel, text in pattern['option_texts'].items()
                                  if rel in option_texts and (text == option_texts[rel] or text in option_texts[rel] or option_texts[rel] in text))
                    if matched >= len(option_texts) * 0.7:
                        return pattern['order']
        return None

pattern_learner = PatternLearner()

def parse_roman_text(text):
    if not text: return None
    clean = text.lower().strip().replace(' ', '')
    if clean in ROMAN_MAP:
        return str(ROMAN_MAP[clean])
    for op in ['+', '-', '*', '/']:
        if op in clean:
            parts = clean.split(op)
            if len(parts) == 2 and parts[0] in ROMAN_MAP and parts[1] in ROMAN_MAP:
                r1, r2 = ROMAN_MAP[parts[0]], ROMAN_MAP[parts[1]]
                try:
                    if op == '+': return str(r1 + r2)
                    if op == '-': return str(r1 - r2)
                    if op == '*': return str(r1 * r2)
                    if op == '/': return str(int(r1 / r2))
                except: pass
    return None

def ocr_antibot_server(question, answers, rels):
    try:
        payload = {"question": question, "answers": answers, "rels": rels}
        resp = requests.post(OCR_SERVER, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.text.strip()
            indexes = [int(x) for x in result.split()]
            ordered = [rels[i-1] for i in indexes if 1 <= i <= len(rels)]
            if ordered:
                return " " + " ".join(ordered)
        return None
    except:
        return None

def ocr_image(base64_image, max_retries=3):
    for attempt in range(max_retries):
        try:
            payload = {"apikey": OCR_API_KEY, "methods": "image-to-text", "base64_img": base64_image, "json": 1}
            resp = requests.post(OCR_API, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    return poll_ocr_result(data.get("request"))
                elif data.get("status") == 0:
                    return data.get("request")
        except:
            pass
        time.sleep(0.5)
    return None

def poll_ocr_result(job_id, max_attempts=20, delay=1.0):
    for _ in range(max_attempts):
        time.sleep(delay)
        try:
            resp = requests.get(OCR_RES, params={"apikey": OCR_API_KEY, "id": job_id, "json": 1}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    return data.get("request")
                if data.get("request") == "CAPCHA_NOT_READY":
                    continue
                return data.get("request")
        except:
            continue
    return None

def correct_ocr_text(text):
    if not text: return text
    text = text.strip()
    text_lower = text.lower()
    if text in OCR_CORRECTIONS: return OCR_CORRECTIONS[text]
    if text_lower in OCR_CORRECTIONS: return OCR_CORRECTIONS[text_lower]
    if text in pattern_learner.ocr_corrections: return pattern_learner.ocr_corrections[text]
    if text_lower in pattern_learner.ocr_corrections: return pattern_learner.ocr_corrections[text_lower]
    return re.sub(r'^[.,;:!?]+|[.,;:!?]+$', '', text)

def parse_arithmetic(text):
    if not text: return None
    roman_res = parse_roman_text(text)
    if roman_res: return roman_res

    text = text.replace(' ', '').replace('·', '+').replace('•', '+').replace('×', '*').replace('÷', '/').replace('−', '-').replace('—', '-')
    text = re.sub(r'[^0-9+\-*/]', '', text)
    if not text: return None
    try:
        if '+' in text: return str(sum(int(p.strip()) for p in text.split('+') if p.strip()))
        if '-' in text:
            parts = text.split('-')
            total = int(parts[0].strip())
            for p in parts[1:]:
                if p.strip(): total -= int(p.strip())
            return str(total)
        if '*' in text:
            total = 1
            for p in text.split('*'):
                if p.strip(): total *= int(p.strip())
            return str(total)
        if '/' in text:
            parts = text.split('/')
            total = int(parts[0].strip())
            for p in parts[1:]:
                if p.strip(): total /= int(p.strip())
            return str(total)
    except: pass
    return None

def extract_numbers(text):
    if not text: return []
    results = re.findall(r'\d+', text)
    for word in re.findall(r'[a-zA-Z]+', text):
        if word.lower() in OCR_CORRECTIONS:
            corrected = OCR_CORRECTIONS[word.lower()]
            if corrected.isdigit(): results.append(corrected)
    return results

def calculate_similarity(word1, word2):
    if not word1 or not word2: return 0.0
    w1, w2 = word1.lower().strip(), word2.lower().strip()
    if w1 == w2: return 1.0
    if w1 in OCR_CORRECTIONS and OCR_CORRECTIONS[w1] == w2: return 1.0
    if w2 in OCR_CORRECTIONS and OCR_CORRECTIONS[w2] == w1: return 1.0
    if w1 in w2 or w2 in w1: return 0.9
    if len(w1) >= 2 and len(w2) >= 2 and w1[0] == w2[0]:
        if w1[-1] == w2[-1]: return 0.85
        return 0.7
    n1, n2 = extract_numbers(w1), extract_numbers(w2)
    for a in n1:
        for b in n2:
            if a == b: return 0.95
            if a.isdigit() and b.isdigit() and abs(int(a) - int(b)) <= 1: return 0.8
    common = len(set(w1) & set(w2))
    max_len = max(len(w1), len(w2))
    if max_len > 0 and common / max_len >= 0.5: return (common / max_len) * 0.8
    return 0.0

def smart_parse_main_text(text):
    if not text: return []
    text = correct_ocr_text(text.strip())
    arithmetic_result = parse_arithmetic(text)
    if arithmetic_result: return [arithmetic_result]
    roman_result = parse_roman_text(text)
    if roman_result: return [roman_result]

    for delim in [',', ';', ':', '|', '.', '  ']:
        if delim in text:
            parts = [p.strip() for p in text.split(delim) if p.strip()]
            if len(parts) >= 2: return [parse_arithmetic(p) or parse_roman_text(p) or p for p in parts]
            
    parts = text.split()
    if len(parts) >= 2:
        return [parse_arithmetic(p) or parse_roman_text(p) or p for p in parts]
    return [text]

def ocr_worker(item):
    key, b64 = item
    res = ocr_image(b64)
    return key, correct_ocr_text(res) if res else None

def solve_antibot_ocr(html, config=None):
    soup = BeautifulSoup(html, 'html.parser')
    
    all_images = re.findall(r'data:image/png;base64,([A-Za-z0-9+/=]+)', html)
    if len(all_images) < 4:
        return None
    
    question_img = all_images[0]
    answer_imgs = all_images[1:4]
    
    rels = re.findall(r'rel=\\\"(\d+)\\\"', html)
    if not rels:
        rels = re.findall(r'rel="(\d+)"', html)
    
    if len(rels) < 3:
        return None
    
    primary_result = ocr_antibot_server(question_img, answer_imgs, rels)
    if primary_result:
        clean_result = re.sub(r'\+', ' ', primary_result)
        clean_result = re.sub(r'\s+', ' ', clean_result).strip()
        return " " + clean_result
    
    instruction = soup.find('div', class_='alert-warning') or soup.find('div', id='atb-instruction')
    if not instruction or not instruction.find('img'):
        return None
    
    main_src = instruction.find('img').get('src', '')
    if 'base64,' not in main_src:
        return None
    main_base64 = main_src.split('base64,')[1]
    
    script = soup.find('script', string=re.compile(r'var ablinks='))
    if not script:
        return None
    script_text = script.string
    
    matches = []
    for p in [r'rel\s*=\s*["\']?(\d+)["\']?.*?src\s*=\s*["\']data:image/png;base64,([^"\']+)["\']',
              r'rel\s*=\s*\\"(\d+)\\".*?src\s*=\s*\\"data:image/png;base64,([^\\]+)\\"',
              r'rel\s*=\s*&quot;(\d+)&quot;.*?src\s*=\s*&quot;data:image/png;base64,([^&]+)&quot;']:
        m = re.findall(p, script_text, re.DOTALL)
        if m:
            matches.extend(m)
            break

    seen = set()
    matches = [(r, i) for r, i in matches if not (r in seen or seen.add(r))]
    
    attempts = 0
    option_texts = {}
    main_parts = []
    
    while attempts < 3:
        attempts += 1
        jobs = [('main', main_base64)] + matches
        ocr_results = {}
        
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            results = executor.map(ocr_worker, jobs)
            for key, text in results:
                if text:
                    ocr_results[key] = text

        if 'main' not in ocr_results:
            continue
        
        main_parts = smart_parse_main_text(ocr_results['main'])
        option_texts = {k: v for k, v in ocr_results.items() if k != 'main'}
        if len(option_texts) < 2:
            continue
        
        remembered = pattern_learner.match_pattern(main_parts, option_texts)
        if remembered:
            clean_result = re.sub(r'\+', ' ', remembered)
            clean_result = re.sub(r'\s+', ' ', clean_result).strip()
            return " " + clean_result
        
        ordered, used = [], set()
        for part in main_parts:
            best_rel, best_sim = None, 0.0
            for rel, opt_text in option_texts.items():
                if rel in used:
                    continue
                opt_result = parse_arithmetic(opt_text) or parse_roman_text(opt_text)
                sim = 1.0 if opt_result and opt_result == part else (calculate_similarity(opt_result or opt_text, part) if opt_result else calculate_similarity(part, opt_text))
                if sim > best_sim:
                    best_sim, best_rel = sim, rel
            if best_rel and best_sim >= 0.5:
                ordered.append(best_rel)
                used.add(best_rel)
                
        if len(ordered) == len(main_parts) and len(ordered) >= 3:
            result = " " + " ".join(ordered)
            clean_result = re.sub(r'\+', ' ', result)
            clean_result = re.sub(r'\s+', ' ', clean_result).strip()
            return " " + clean_result
        
        time.sleep(0.4)

    ordered, used = [], set()
    for part in main_parts:
        best_rel, best_sim = None, 0.0
        for rel, opt_text in option_texts.items():
            if rel in used:
                continue
            opt_result = parse_arithmetic(opt_text) or parse_roman_text(opt_text)
            sim = 1.0 if opt_result and opt_result == part else (calculate_similarity(opt_result or opt_text, part) if opt_result else calculate_similarity(part, opt_text))
            if sim > best_sim:
                best_sim, best_rel = sim, rel
        if best_rel and best_sim >= 0.35:
            ordered.append(best_rel)
            used.add(best_rel)

    remaining_rels = [r for r in option_texts if r not in used]
    for rel in sorted(remaining_rels, key=int):
        if len(ordered) < 3:
            ordered.append(rel)

    if len(ordered) >= 3:
        result = " " + " ".join(ordered[:3])
        clean_result = re.sub(r'\+', ' ', result)
        clean_result = re.sub(r'\s+', ' ', clean_result).strip()
        return " " + clean_result
    elif len(ordered) == 2 and len(remaining_rels) > 0:
        ordered.append(remaining_rels[0])
        result = " " + " ".join(ordered)
        clean_result = re.sub(r'\+', ' ', result)
        clean_result = re.sub(r'\s+', ' ', clean_result).strip()
        return " " + clean_result
        
    result = " " + " ".join(sorted(option_texts.keys(), key=int)[:3])
    clean_result = re.sub(r'\+', ' ', result)
    clean_result = re.sub(r'\s+', ' ', clean_result).strip()
    return " " + clean_result

# ============================================================
# SESSION & CONFIG
# ============================================================
def save_session(cookies_dict, user_agent):
    data = {"cookies": cookies_dict, "user_agent": user_agent, "saved_at": time.time()}
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except:
        return False

def load_session():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get("saved_at", 0) < 86400:
                    return data
    except:
        pass
    return None

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "cookie": "",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "withdraw_method": "faucetpay", 
        "faucetpay_email": "", 
        "withdraw_amount": "",
        "multibot_key": "",
        "bypass_key": "",
        "tertuyul_key": "",      # NEW
        "waryono_key": "",       # NEW
        "recaptcha_solver": "multibot",
        "antibot_solver": "ocr",
        "turnstile_solver": "multibot"  # can be 'multibot', 'tertuyul', 'waryono', 'bypassallshortlink'
    }

def get_input_with_default(prompt, default=""):
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    value = input(prompt).strip()
    return value if value else default

# ============================================================
# CAPTCHA SOLVERS - Updated with 3 APIs
# ============================================================

# ---------- MultiBot (existing) ----------
def solve_multibot_captcha(api_key, method, sitekey, pageurl, max_attempts=30):
    bot.inline_status(f"Solving {method} via MultiBot...")
    
    try:
        params = {
            "key": api_key,
            "method": method,
            "pageurl": pageurl,
            "json": "1",
        }
        
        if method == "userrecaptcha":
            params["googlekey"] = sitekey
        elif method == "turnstile":
            params["sitekey"] = sitekey
        
        files = {k: (None, v) for k, v in params.items()}
        resp = requests.post("https://api.multibot.cloud/in.php", files=files, timeout=30)
        result = resp.json()
        
        if result.get("status") == 1:
            task_id = result.get("request")
            
            for attempt in range(max_attempts):
                time.sleep(5)
                poll_resp = requests.get(
                    f"https://api.multibot.cloud/res.php?key={api_key}&action=get&id={task_id}&json=1",
                    timeout=30
                )
                poll_result = poll_resp.json()
                
                if poll_result.get("status") == 1:
                    token = poll_result.get("request")
                    bot.clear_inline()
                    return token
                elif poll_result.get("request") == "CAPCHA_NOT_READY":
                    continue
                else:
                    return None
        else:
            return None
    except:
        return None

# ---------- Tertuyul API (NEW) ----------
def solve_tertuyul_captcha(api_key, sitekey, pageurl, max_attempts=30):
    bot.inline_status("Solving Turnstile via Tertuyul...")
    try:
        # Submit
        submit_url = "http://api.tertuyul.my.id/in.php"
        payload = {
            'key': api_key,
            'method': 'turnstile',
            'sitekey': sitekey,
            'pageurl': pageurl,
            'json': '1'
        }
        resp = requests.post(submit_url, data=payload, timeout=30)
        data = resp.json()
        if data.get('status') != 1:
            bot.clear_inline()
            return None
        task_id = data.get('request')
        # Poll
        for _ in range(max_attempts):
            time.sleep(5)
            poll_payload = {
                'key': api_key,
                'action': 'get',
                'id': task_id,
                'json': '1'
            }
            poll_resp = requests.post("http://api.tertuyul.my.id/res.php", data=poll_payload, timeout=30)
            poll_data = poll_resp.json()
            if poll_data.get('status') == 1:
                token = poll_data.get('request')
                bot.clear_inline()
                return token
            if poll_data.get('request') == 'CAPCHA_NOT_READY':
                continue
            break
    except Exception as e:
        bot.clear_inline()
    return None

# ---------- Waryono API (NEW) ----------
def solve_waryono_captcha(api_key, sitekey, pageurl, max_attempts=30):
    bot.inline_status("Solving Turnstile via Waryono...")
    try:
        # Submit - POST with JSON
        submit_url = "https://api.waryono.my.id/in.php"
        payload = {
            "apikey": api_key,
            "methods": "turnstile",
            "domain": pageurl,
            "sitekey": sitekey,
            "action": "login",
            "cdata": "session_abc123"  # optional, can be empty
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(submit_url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get('status') != 1:
            return None
        task_id = data.get('request')
        # Poll - GET with apikey and id
        for _ in range(max_attempts):
            time.sleep(5)
            poll_url = f"https://api.waryono.my.id/res.php?apikey={api_key}&id={task_id}&action=get&json=1"
            poll_resp = requests.get(poll_url, timeout=30)
            if poll_resp.status_code != 200:
                continue
            poll_data = poll_resp.json()
            if poll_data.get('status') == 1:
                token = poll_data.get('request')
                bot.clear_inline()
                return token
            if poll_data.get('request') == 'CAPCHA_NOT_READY':
                continue
            break
    except Exception as e:
        bot.clear_inline()
    return None

# ---------- BypassAllShortLink (existing, with minor tweak) ----------
def solve_bypassall_captcha(api_key, method, sitekey, pageurl, max_attempts=40):
    bot.inline_status(f"Solving {method} via BypassAllShortLink...")
    api_base = "https://bypassallshortlinks.space"
    
    try:
        resp = requests.get(
            f"{api_base}/in.php", 
            params={'key': api_key, 'method': method, 'pageurl': pageurl, 'sitekey': sitekey}, 
            timeout=30
        )
        result = resp.text.strip()
        
        if result.startswith('OK|'):
            task_id = result.split('|')[1]
            
            for attempt in range(max_attempts):
                time.sleep(5)
                poll_resp = requests.get(
                    f"{api_base}/res.php", 
                    params={'key': api_key, 'id': task_id}, 
                    timeout=30
                )
                poll_result = poll_resp.text.strip()
                
                if 'NOT_READY' in poll_result.upper():
                    continue
                elif poll_result == 'ERROR_CAPTCHA_UNSOLVABLE':
                    return None
                elif poll_result.startswith('ERROR') and attempt < max_attempts - 1:
                    continue
                elif poll_result.startswith('OK|'):
                    token = poll_result.split('|')[1]
                    bot.clear_inline()
                    return token
            
            return None
        else:
            return None
    except:
        return None

# ---------- Main Turnstile dispatcher ----------
def solve_turnstile(sitekey, pageurl, config):
    solver = config.get("turnstile_solver", "multibot")
    api_key = config.get(f"{solver}_key", "")  # e.g., multibot_key, tertuyul_key, waryono_key, bypass_key
    
    if not api_key:
        bot.warning(f"API key for {solver} not set!")
        return None
    
    if solver == "multibot":
        return solve_multibot_captcha(api_key, "turnstile", sitekey, pageurl)
    elif solver == "tertuyul":
        return solve_tertuyul_captcha(api_key, sitekey, pageurl)
    elif solver == "waryono":
        return solve_waryono_captcha(api_key, sitekey, pageurl)
    elif solver == "bypassallshortlink":
        return solve_bypassall_captcha(api_key, "turnstile", sitekey, pageurl)
    else:
        return None

def solve_antibot(html, config):
    return solve_antibot_ocr(html, config)

# ============================================================
# MAIN BOT - Cookie Based
# ============================================================
class CoinPayuBot:
    def __init__(self, config):
        self.config = config
        self.cookie = config.get("cookie", "")
        self.user_agent = config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        self.withdraw_method = config.get("withdraw_method", "faucetpay")
        self.faucetpay_email = config.get("faucetpay_email", "")
        self.withdraw_amount = config.get("withdraw_amount", "")
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        saved = load_session()
        if saved and saved.get("user_agent"):
            self.user_agent = saved["user_agent"]
            self.session.headers.update({'User-Agent': self.user_agent})
            for name, value in saved["cookies"].items():
                self.session.cookies.set(name, value, domain="coinpayufree.com")
        
        if self.cookie and not saved:
            try:
                for item in self.cookie.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        self.session.cookies.set(name, value, domain="coinpayufree.com")
            except:
                pass
        
        self.logged_in = False
        self.balance = 0
        self.username = ""
        
        self.faucet_last_claim = 0
        self.wheel_last_claim = 0
        self.faucet_cooldown = MANUAL_FAUCET_COOLDOWN
        self.faucet_csrf_retry = MANUAL_FAUCET_CSRF_RETRY
        self.wheel_cooldown = WHEEL_COOLDOWN
        
        self.auto_faucet_count = 0
        self.total_auto_earned = 0.0
        
    def _headers(self, extra=None):
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Referer': BASE_URL
        }
        if extra:
            headers.update(extra)
        return headers
    
    def _get_csrf(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        csrf = soup.find('input', {'name': 'csrf_token_name'}) or soup.find('input', {'id': 'token'})
        return csrf.get('value') if csrf else None
    
    def _get_token(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        token_input = soup.find('input', {'name': 'token'})
        return token_input.get('value') if token_input else None
    
    def _get_swal_message(self, html):
        match = re.search(r"Swal\.fire\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", html)
        if match:
            return {"title": match.group(1), "text": match.group(2), "icon": match.group(3)}
        match = re.search(r"text:\s*'([^']+)'", html)
        if match:
            return {"title": "", "text": match.group(1), "icon": "info"}
        return None
    
    def _get_balance(self, html):
        match = re.search(r'Balance:?\s*<b>([\d,]+)\s*coins?</b>', html, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        match = re.search(r'Balance:?\s*<b>([\d,.]+)\s*coins?</b>', html, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
        return 0
    
    def _get_username(self, html):
        match = re.search(r'key="t-henry">([^<]+)</span>', html)
        if match:
            return match.group(1).strip()
        return None
    
    def is_session_valid(self):
        try:
            resp = self.session.get(DASHBOARD_URL, headers=self._headers(), timeout=10, allow_redirects=False)
            if resp.status_code == 200 and '<title>Dashboard' in resp.text:
                self.balance = self._get_balance(resp.text)
                self.username = self._get_username(resp.text)
                bot.set_user_info(self.username, self.balance)
                self.logged_in = True
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                return True
            if '/login' in resp.headers.get('Location', ''):
                self.logged_in = False
                return False
            return False
        except:
            return False
    
    def ensure_logged_in(self):
        if self.logged_in and self.is_session_valid():
            return True
        
        saved = load_session()
        if saved and saved.get("cookies"):
            self.user_agent = saved.get("user_agent", self.user_agent)
            self.session.headers.update({'User-Agent': self.user_agent})
            for name, value in saved["cookies"].items():
                self.session.cookies.set(name, value, domain="coinpayufree.com")
            if self.is_session_valid():
                bot.info("Session restored from saved cookies")
                return True
        
        if self.cookie:
            try:
                for item in self.cookie.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        self.session.cookies.set(name, value, domain="coinpayufree.com")
                if self.is_session_valid():
                    bot.info("Cookie-based login successful")
                    return True
            except:
                pass
        
        bot.warning("No valid session. Please provide your cookie.")
        print(f"\n  {C['gray']}• Get cookie from browser after logging in to {C['menu']}coinpayufree.com{C['reset']}")
        print(f"  {C['gray']}• Open DevTools → Application → Cookies → copy all cookies as string{C['reset']}")
        print(f"  {C['gray']}• Example: ci_session=abc123; csrf_cookie_name=xyz789{C['reset']}\n")
        new_cookie = input(f"  {C['menu']}Enter Cookie: {C['reset']}").strip()
        if new_cookie:
            self.cookie = new_cookie
            self.config['cookie'] = new_cookie
            save_config(self.config)
            for item in new_cookie.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    self.session.cookies.set(name, value, domain="coinpayufree.com")
            if self.is_session_valid():
                bot.success("Login successful with provided cookie!")
                return True
        
        bot.error("Failed to establish a valid session.")
        return False

    def check_dashboard(self):
        try:
            resp = self.session.get(DASHBOARD_URL, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                self.balance = self._get_balance(resp.text)
                self.username = self._get_username(resp.text)
                bot.set_user_info(self.username, self.balance)
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                return True
        except:
            pass
        return False
    
    # ============================================================
    # MANUAL FAUCET
    # ============================================================
    def claim_faucet(self):
        current_time = time.time()
        
        if self.faucet_last_claim > 0:
            elapsed = current_time - self.faucet_last_claim
            if elapsed < self.faucet_cooldown:
                remaining = int(self.faucet_cooldown - elapsed)
                bot.info(f"Manual Faucet cooldown active ({self.faucet_cooldown}s = 65 minutes)")
                bot.info(f"Remaining: {remaining}s ({remaining//60}m {remaining%60}s)")
                bot.countdown(remaining, "Faucet Cooldown (65 min)")
                return self.claim_faucet()
        
        try:
            bot.info("Accessing Manual Faucet page...")
            resp = self.session.get(FAUCET_URL, headers=self._headers(), timeout=15)
            
            if resp.status_code != 200:
                bot.warning(f"Faucet page returned status {resp.status_code}")
                return False
            
            html = resp.text
            
            if '/wait' in resp.url:
                wait_match = re.search(r'id="countdown">(\d+)</span>', resp.text)
                if wait_match:
                    total = int(wait_match.group(1))
                    bot.info(f"Faucet cooldown active: {total}s")
                    bot.countdown(total + random.randint(5, 10), "Faucet Timer")
                    return self.claim_faucet()
            
            csrf = self._get_csrf(html)
            if not csrf:
                bot.warning("CSRF Token not found on faucet page!")
                bot.info(f"Waiting {self.faucet_csrf_retry}s (16+ minutes) before retry...")
                bot.countdown(self.faucet_csrf_retry, "CSRF Wait (1000s)")
                if not self.is_session_valid():
                    self.ensure_logged_in()
                return self.claim_faucet()
            
            bot.info(f"CSRF Token found: {csrf[:15]}...")
            bot.info("Manual Faucet ready! Claiming...")
            
            antibot = solve_antibot(html, self.config)
            if not antibot:
                bot.warning("AntiBot solve failed, using fallback...")
                antibot = " 7499 1023 7320"
            
            turnstile = solve_turnstile(TURNSTILE_SITEKEY, FAUCET_URL, self.config)
            if not turnstile:
                bot.error("Turnstile solve failed!")
                return False
            
            payload = {
                'antibotlinks': antibot,
                'csrf_token_name': csrf,
                'captcha': 'turnstile',
                'cf-turnstile-response': turnstile
            }
            
            time.sleep(random.uniform(1, 2))
            
            bot.info("Submitting faucet claim...")
            resp = self.session.post(
                FAUCET_CLAIM_URL, 
                data=payload, 
                headers=self._headers({'Content-Type': 'application/x-www-form-urlencoded'}),
                timeout=30, 
                allow_redirects=True
            )
            
            html = resp.text
            
            if '/wait' in resp.url:
                wait_match = re.search(r'id="countdown">(\d+)</span>', resp.text)
                if wait_match:
                    total = int(wait_match.group(1))
                    bot.info(f"Faucet claimed! Next available in: {total}s")
                    bot.countdown(total + random.randint(5, 10), "Faucet Cooldown")
                    self.faucet_last_claim = time.time()
                    return True
            
            swal = self._get_swal_message(html)
            if swal and swal['icon'] == 'success':
                bot.success(f"Manual Faucet: {swal['text']}")
                self.balance += 50
                bot.set_user_info(self.username, self.balance)
                self.faucet_last_claim = time.time()
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                bot.info(f"Next faucet available in 65 minutes ({self.faucet_cooldown}s)")
                return True
            elif swal:
                bot.warning(f"Manual Faucet: {swal['text']}")
                self.faucet_last_claim = time.time()
                return False
            
            if 'coins' in html and 'added' in html:
                bot.success("Manual Faucet: 50 coins added to your balance")
                self.balance += 50
                bot.set_user_info(self.username, self.balance)
                self.faucet_last_claim = time.time()
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                return True
            
            bot.warning("Manual Faucet claim unclear, setting cooldown...")
            self.faucet_last_claim = time.time()
            return False
            
        except Exception as e:
            bot.error(f"Manual Faucet error: {str(e)}")
            self.faucet_last_claim = time.time()
            return False
    
    # ============================================================
    # WHEEL FAUCET
    # ============================================================
    def claim_wheel(self):
        current_time = time.time()
        
        if self.wheel_last_claim > 0:
            elapsed = current_time - self.wheel_last_claim
            if elapsed < self.wheel_cooldown:
                remaining = int(self.wheel_cooldown - elapsed)
                bot.info(f"Wheel cooldown active ({self.wheel_cooldown}s = 16 minutes)")
                bot.info(f"Remaining: {remaining}s ({remaining//60}m {remaining%60}s)")
                bot.countdown(remaining, "Wheel Cooldown (16 min)")
                return self.claim_wheel()
        
        try:
            bot.info("Accessing Wheel page...")
            resp = self.session.get(WHEEL_URL, headers=self._headers(), timeout=15)
            
            if resp.status_code != 200:
                bot.warning(f"Wheel page returned status {resp.status_code}")
                return False
            
            html = resp.text
            
            timer = re.search(r'id="minute">(\d+)</div>.*?id="second">(\d+)</div>', html, re.DOTALL)
            if timer:
                minutes = int(timer.group(1))
                seconds = int(timer.group(2))
                total = minutes * 60 + seconds
                if total > 0:
                    bot.info(f"Wheel cooldown from page: {total}s ({minutes}m {seconds}s)")
                    bot.countdown(total + random.randint(3, 5), "Wheel Timer")
                    return self.claim_wheel()
            
            if 'proverka' not in html or 'progress-wrapper' not in html:
                bot.info("Wheel not ready, waiting 5s...")
                time.sleep(5)
                return self.claim_wheel()
            
            bot.info("Wheel ready! Spinning...")
            
            resp = self.session.post(
                WHEEL_START_URL, 
                headers=self._headers({
                    'Content-Type': 'application/x-www-form-urlencoded', 
                    'X-Requested-With': 'XMLHttpRequest'
                }), 
                timeout=15
            )
            data = resp.json()
            
            if data.get('status') != 'success':
                bot.warning(f"Wheel start failed: {data.get('status')}")
                return False
            
            token = data.get('token')
            if not token:
                bot.warning("No wheel token received")
                return False
            
            wait = data.get('seconds', 10)
            bot.info(f"Wheel spinning... waiting {wait}s for result...")
            bot.countdown(wait + random.randint(2, 4), "Wheel Spin")
            
            resp = self.session.post(
                WHEEL_VERIFY_URL, 
                data={'token': token}, 
                headers=self._headers({
                    'Content-Type': 'application/x-www-form-urlencoded', 
                    'X-Requested-With': 'XMLHttpRequest'
                }), 
                timeout=15
            )
            data = resp.json()
            
            if data.get('status') == 'success':
                reward = data.get('reward', 'coins')
                bot.success(f"Wheel: {reward} added to your balance")
                self.wheel_last_claim = time.time()
                self.check_dashboard()
                bot.info(f"Next wheel available in 16 minutes ({self.wheel_cooldown}s)")
                return True
            else:
                bot.warning(f"Wheel claim failed: {data.get('status')}")
                return False
                
        except Exception as e:
            bot.error(f"Wheel error: {str(e)}")
            return False
    
    # ============================================================
    # AUTO FAUCET
    # ============================================================
    def claim_auto_faucet(self):
        try:
            resp = self.session.get(AUTO_FAUCET_URL, headers=self._headers(), timeout=15)
            if resp.status_code != 200:
                bot.warning(f"Auto faucet page returned status {resp.status_code}")
                return False
            
            html = resp.text
            
            token = self._get_token(html)
            if not token:
                wait_match = re.search(r'(\d+)\s*seconds?</span>', html, re.IGNORECASE)
                if wait_match:
                    wait_seconds = int(wait_match.group(1))
                    bot.countdown(wait_seconds + random.randint(3, 8), "Auto Faucet Timer")
                    return self.claim_auto_faucet()
                
                countdown_match = re.search(r'id="countdown">(\d+)</span>', html)
                if countdown_match:
                    wait_seconds = int(countdown_match.group(1))
                    bot.countdown(wait_seconds + random.randint(3, 8), "Auto Faucet Timer")
                    return self.claim_auto_faucet()
                
                bot.warning("No token found on auto faucet page")
                return False
            
            wait_time = AUTO_FAUCET_WAIT + random.randint(10, 15)
            bot.countdown(wait_time, "Auto Faucet Wait")
            
            payload = {'token': token}
            resp = self.session.post(
                AUTO_FAUCET_VERIFY_URL, 
                data=payload, 
                headers=self._headers({'Content-Type': 'application/x-www-form-urlencoded'}),
                timeout=30,
                allow_redirects=True
            )
            
            html = resp.text
            swal = self._get_swal_message(html)
            
            if swal and swal['icon'] == 'success':
                amount_match = re.search(r'([\d.]+)\s*coins?\s*has\s*been\s*added', swal['text'], re.IGNORECASE)
                earned = float(amount_match.group(1)) if amount_match else 2.5
                
                self.auto_faucet_count += 1
                self.total_auto_earned += earned
                
                bot.success(f"Auto Faucet: {earned} coins added | Claim #{self.auto_faucet_count}")
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                self.check_dashboard()
                return True
            
            if 'coins has been added' in html.lower():
                amount_match = re.search(r'([\d.]+)\s*coins?\s*has\s*been\s*added', html, re.IGNORECASE)
                earned = float(amount_match.group(1)) if amount_match else 2.5
                
                self.auto_faucet_count += 1
                self.total_auto_earned += earned
                
                bot.success(f"Auto Faucet: {earned} coins added | Claim #{self.auto_faucet_count}")
                cookies = self.session.cookies.get_dict()
                save_session(cookies, self.user_agent)
                self.check_dashboard()
                return True
            
            return False
            
        except Exception as e:
            bot.warning(f"Auto faucet error: {str(e)}")
            return False
    
    def auto_faucet_loop(self):
        bot.info("▶ Auto Faucet Started - Unlimited Mode")
        bot.info(f"• Earning ~2.5 coins every ~2 minutes")
        bot.info(f"• Using saved session (no re-login needed)")
        print(f"  {C['gray']}{'─'*55}{C['reset']}\n")
        
        try:
            while True:
                if not self.is_session_valid():
                    bot.warning("Session expired! Re-authenticating...")
                    self.ensure_logged_in()
                    if not self.logged_in:
                        bot.error("Authentication failed! Retrying in 30s...")
                        bot.countdown(30, "Retry Timer")
                        continue
                
                self.claim_auto_faucet()
                
        except KeyboardInterrupt:
            print(f"\n\n  {C['yellow']}▶ Auto Faucet Stopped!{C['reset']}")
            print(f"  {C['gray']}• Total Claims: {self.auto_faucet_count}{C['reset']}")
            print(f"  {C['gray']}• Total Earned: {self.total_auto_earned:.1f} coins{C['reset']}")
    
    # ============================================================
    # DAILY BONUS
    # ============================================================
    def claim_daily_bonus(self):
        try:
            resp = self.session.get(DAILY_BONUS_URL, headers=self._headers(), timeout=15)
            if resp.status_code != 200:
                return False
            
            csrf = self._get_csrf(resp.text)
            if not csrf:
                bot.info("Daily Bonus not available today")
                return False
            
            bot.info("Daily Bonus ready! Claiming...")
            
            resp = self.session.post(
                DAILY_CLAIM_URL, 
                data={'csrf_token_name': csrf}, 
                headers=self._headers({'Content-Type': 'application/x-www-form-urlencoded'}),
                timeout=30, 
                allow_redirects=True
            )
            
            swal = self._get_swal_message(resp.text)
            if swal and swal['icon'] == 'success':
                bot.success(f"Daily Bonus: {swal['text']}")
                self.balance += 80
                bot.set_user_info(self.username, self.balance)
                return True
            elif swal:
                bot.warning(f"Daily Bonus: {swal['text']}")
                return False
            return False
        except Exception as e:
            bot.warning(f"Daily bonus error: {str(e)}")
            return False
    
    # ============================================================
    # WITHDRAWAL
    # ============================================================
    def process_withdrawal(self):
        if not self.withdraw_amount:
            return False
        
        try:
            resp = self.session.get(WITHDRAWAL_URL, headers=self._headers(), timeout=15)
            if resp.status_code != 200:
                return False
            
            csrf = self._get_csrf(resp.text)
            if not csrf:
                return False
            
            self.check_dashboard()
            bot.info(f"Withdrawing {self.withdraw_amount} coins...")
            
            turnstile = solve_turnstile(TURNSTILE_SITEKEY, WITHDRAWAL_URL, self.config)
            
            payload = {
                'csrf_token_name': csrf,
                'method': '10',
                'amount': self.withdraw_amount,
                'wallet': self.faucetpay_email if self.withdraw_method == 'faucetpay' else self.email,
                'captcha': 'turnstile'
            }
            if turnstile:
                payload['cf-turnstile-response'] = turnstile
            
            time.sleep(random.uniform(1, 2))
            resp = self.session.post(
                WITHDRAWAL_POST_URL, 
                data=payload, 
                headers=self._headers({'Content-Type': 'application/x-www-form-urlencoded'}),
                timeout=30, 
                allow_redirects=True
            )
            
            swal = self._get_swal_message(resp.text)
            if swal and swal['icon'] == 'success':
                bot.success(f"Withdrawal: {swal['text']}")
                self.balance -= int(self.withdraw_amount)
                bot.set_user_info(self.username, self.balance)
                return True
            elif swal:
                bot.warning(f"Withdrawal: {swal['text']}")
                return False
            return False
        except Exception as e:
            bot.warning(f"Withdrawal error: {str(e)}")
            return False

# ============================================================
# COLORFUL MENU FUNCTIONS
# ============================================================
def print_header(text):
    print(f"{C['header']}{'═'*55}{C['reset']}")
    print(f"{C['header']}  {text}{C['reset']}")
    print(f"{C['header']}{'═'*55}{C['reset']}")

def print_menu_option(key, value, status=None):
    if status:
        print(f"  {C['menu']}▶ [{key}]{C['reset']} {value} {C['green']}[{status}]{C['reset']}")
    else:
        print(f"  {C['menu']}▶ [{key}]{C['reset']} {value}")

def print_info(text):
    print(f"  {C['gray']}• {C['reset']}{text}")

def print_success(text):
    print(f"  {C['green']}✔ {C['reset']}{text}")

def print_error(text):
    print(f"  {C['red']}✘ {C['reset']}{text}")

def print_warning(text):
    print(f"  {C['yellow']}⚠ {C['reset']}{text}")

def print_instruction(text):
    print(f"  {C['orange']}ℹ {C['reset']}{text}")

def get_menu_choice(prompt, options):
    print(f"\n{C['gold']}{prompt}{C['reset']}")
    print(f"{C['gray']}{'─'*55}{C['reset']}")
    for key, value in options.items():
        print_menu_option(key, value)
    print(f"{C['gray']}{'─'*55}{C['reset']}")
    while True:
        choice = input(f"{C['menu']}Select option: {C['reset']}").strip()
        if choice in options:
            return choice
        print_error("Invalid option. Please try again.")

def show_main_menu():
    bot.show_menu_banner("CoinPayuFree")
    print_header("CoinPayuFree Bot")
    
    menu_options = {
        '1': 'Set User Agent',
        '2': 'Set Cookie (Login)',
        '3': 'Set Solver',
        '4': 'Set Withdraw',
        '5': 'Start Work',
        '6': 'Exit'
    }
    return get_menu_choice("Main Menu:", menu_options)

def show_work_menu():
    bot.show_menu_banner("CoinPayuFree")
    print_header("Start Work")
    
    work_options = {
        '1': 'Daily Bonus',
        '2': 'Manual Faucet (65 min cooldown)',
        '3': 'Wheel Faucet (16 min cooldown)',
        '4': 'Auto Faucet - Unlimited (2 min)',
        '5': 'Withdraw',
        '6': 'All Tasks (Loop)'
    }
    return get_menu_choice("Select Task:", work_options)

def show_solver_menu(config):
    bot.show_menu_banner("CoinPayuFree")
    print_header("Set Solver")
    
    recaptcha_solver = config.get("recaptcha_solver", "multibot")
    antibot_solver = config.get("antibot_solver", "ocr")
    turnstile_solver = config.get("turnstile_solver", "multibot")
    
    multibot_key = config.get("multibot_key", "")
    bypass_key = config.get("bypass_key", "")
    tertuyul_key = config.get("tertuyul_key", "")
    waryono_key = config.get("waryono_key", "")
    
    print(f"\n{C['gray']}Current Solver Status:{C['reset']}")
    print(f"  {C['menu']}▶ AntiBot         : {C['green']}{antibot_solver}{C['reset']} {C['green']}[ON (OCR)]{C['reset']}")
    print(f"  {C['menu']}▶ Turnstile       : {C['green']}{turnstile_solver}{C['reset']} {C['green']}[{'ON' if (
        (turnstile_solver=='multibot' and multibot_key) or
        (turnstile_solver=='tertuyul' and tertuyul_key) or
        (turnstile_solver=='waryono' and waryono_key) or
        (turnstile_solver=='bypassallshortlink' and bypass_key)
    ) else 'OFF'}]{C['reset']}")
    print()
    
    solver_options = {
        '1': f"AntiBot (Current: {antibot_solver})",
        '2': f"Turnstile (Current: {turnstile_solver})",
        '3': 'Set MultiBot API Key',
        '4': 'Set BypassAllShortLink API Key',
        '5': 'Set Tertuyul API Key',       # NEW
        '6': 'Set Waryono API Key',        # NEW
        '7': 'Back to Main Menu'
    }
    choice = get_menu_choice("Solver Menu:", solver_options)
    
    if choice == '1':
        bot.show_menu_banner("CoinPayuFree")
        print_header("AntiBot Solver")
        print_warning("OCR solver is enabled by default (free & accurate).")
        antibot_options = {'1': 'OCR (Default)', '2': 'BypassAllShortLink (API)', '3': 'Back'}
        opt = get_menu_choice("Choose:", antibot_options)
        if opt == '1':
            config['antibot_solver'] = 'ocr'
            print_success("AntiBot solver set to: OCR")
        elif opt == '2':
            config['antibot_solver'] = 'bypassallshortlink'
            print_success("AntiBot solver set to: BypassAllShortLink")
        save_config(config)
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '2':
        bot.show_menu_banner("CoinPayuFree")
        print_header("Turnstile Solver")
        turnstile_options = {
            '1': 'MultiBot',
            '2': 'Tertuyul',
            '3': 'Waryono',
            '4': 'BypassAllShortLink',
            '5': 'Back'
        }
        opt = get_menu_choice("Choose:", turnstile_options)
        if opt == '1':
            config['turnstile_solver'] = 'multibot'
            print_success("Turnstile solver set to: MultiBot")
        elif opt == '2':
            config['turnstile_solver'] = 'tertuyul'
            # Ensure key is set
            if not config.get('tertuyul_key'):
                new_key = get_input_with_default("Enter Tertuyul API Key", "")
                if new_key:
                    config['tertuyul_key'] = new_key
                    print_success("Tertuyul API Key saved")
                else:
                    print_warning("Tertuyul API Key not set, solver may fail")
            print_success("Turnstile solver set to: Tertuyul")
        elif opt == '3':
            config['turnstile_solver'] = 'waryono'
            if not config.get('waryono_key'):
                new_key = get_input_with_default("Enter Waryono API Key", "")
                if new_key:
                    config['waryono_key'] = new_key
                    print_success("Waryono API Key saved")
                else:
                    print_warning("Waryono API Key not set, solver may fail")
            print_success("Turnstile solver set to: Waryono")
        elif opt == '4':
            config['turnstile_solver'] = 'bypassallshortlink'
            if not config.get('bypass_key'):
                new_key = get_input_with_default("Enter BypassAllShortLink API Key", "")
                if new_key:
                    config['bypass_key'] = new_key
                    print_success("BypassAllShortLink API Key saved")
                else:
                    print_warning("BypassAllShortLink API Key not set, solver may fail")
            print_success("Turnstile solver set to: BypassAllShortLink")
        elif opt == '5':
            return show_solver_menu(config)
        save_config(config)
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '3':
        bot.show_menu_banner("CoinPayuFree")
        print_header("Set MultiBot API Key")
        current = config.get('multibot_key', '')
        api_key = get_input_with_default("Enter MultiBot API Key", current)
        config['multibot_key'] = api_key
        save_config(config)
        print_success("MultiBot API Key updated")
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '4':
        bot.show_menu_banner("CoinPayuFree")
        print_header("Set BypassAllShortLink API Key")
        current = config.get('bypass_key', '')
        api_key = get_input_with_default("Enter BypassAllShortLink API Key", current)
        config['bypass_key'] = api_key
        save_config(config)
        print_success("BypassAllShortLink API Key updated")
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '5':
        bot.show_menu_banner("CoinPayuFree")
        print_header("Set Tertuyul API Key")
        current = config.get('tertuyul_key', '')
        api_key = get_input_with_default("Enter Tertuyul API Key", current)
        config['tertuyul_key'] = api_key
        save_config(config)
        print_success("Tertuyul API Key updated")
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '6':
        bot.show_menu_banner("CoinPayuFree")
        print_header("Set Waryono API Key")
        current = config.get('waryono_key', '')
        api_key = get_input_with_default("Enter Waryono API Key", current)
        config['waryono_key'] = api_key
        save_config(config)
        print_success("Waryono API Key updated")
        input("\nPress Enter to continue...")
        return show_solver_menu(config)
    
    elif choice == '7':
        return

def main():
    config = load_config()
    
    while True:
        choice = show_main_menu()
        
        if choice == '1':
            bot.show_menu_banner("CoinPayuFree")
            print_header("Set User Agent")
            current = config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            new_ua = get_input_with_default("Enter User Agent", current)
            config['user_agent'] = new_ua
            save_config(config)
            print_success("User Agent updated")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            bot.show_menu_banner("CoinPayuFree")
            print_header("Set Cookie (Login)")
            print_instruction("Get cookie from browser after logging in to coinpayufree.com")
            print(f"  {C['gray']}• Open DevTools → Application → Cookies{C['reset']}")
            print(f"  {C['gray']}• Copy all cookies as: name1=value1; name2=value2; ...{C['reset']}\n")
            current = config.get('cookie', '')
            cookie = get_input_with_default("Enter Cookie", current)
            config['cookie'] = cookie
            save_config(config)
            print_success("Cookie saved. Try to login...")
            bot_obj = CoinPayuBot(config)
            if bot_obj.ensure_logged_in():
                print_success("Login successful!")
            else:
                print_error("Login failed with provided cookie.")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            show_solver_menu(config)
            
        elif choice == '4':
            bot.show_menu_banner("CoinPayuFree")
            print_header("Set Withdraw")
            method_choice = get_menu_choice("Select Withdraw Method:", {'1': 'faucetpay', '2': 'email'})
            method = 'faucetpay' if method_choice == '1' else 'email'
            config['withdraw_method'] = method
            
            if method == 'faucetpay':
                email = get_input_with_default("FaucetPay Email", config.get('faucetpay_email', ''))
                config['faucetpay_email'] = email
            
            amount = get_input_with_default("Withdraw Amount (coins)", config.get('withdraw_amount', '1000'))
            config['withdraw_amount'] = amount
            save_config(config)
            print_success(f"Withdraw set: {amount} coins via {method}")
            input("\nPress Enter to continue...")
            
        elif choice == '5':
            work_choice = show_work_menu()
            
            if not config.get('cookie'):
                bot.show_menu_banner("CoinPayuFree")
                print_error("Cookie not set! Please set cookie first.")
                input("\nPress Enter to continue...")
                continue
            
            bot_obj = CoinPayuBot(config)
            bot.refresh_banner()
            
            if not bot_obj.ensure_logged_in():
                print_error("Failed to login with cookie!")
                input("\nPress Enter to continue...")
                continue
            
            if work_choice == '1':
                bot_obj.claim_daily_bonus()
            elif work_choice == '2':
                bot_obj.claim_faucet()
            elif work_choice == '3':
                bot_obj.claim_wheel()
            elif work_choice == '4':
                bot_obj.auto_faucet_loop()
            elif work_choice == '5':
                if config.get('withdraw_amount'):
                    bot_obj.process_withdrawal()
                else:
                    print_error("Withdraw amount not set!")
            elif work_choice == '6':
                bot.info("Starting All Tasks Loop...")
                try:
                    while True:
                        print()
                        bot.info("─── New Cycle ───")
                        
                        if not bot_obj.is_session_valid():
                            if not bot_obj.ensure_logged_in():
                                break
                        
                        bot_obj.claim_daily_bonus()
                        time.sleep(3)
                        bot_obj.claim_wheel()
                        time.sleep(3)
                        bot_obj.claim_auto_faucet()
                        time.sleep(3)
                        bot_obj.claim_faucet()
                        time.sleep(3)
                        
                        bot_obj.check_dashboard()
                        bot.info(f"Balance: {bot_obj.balance} coins")
                        
                        if bot_obj.balance >= 1000 and config.get('withdraw_amount'):
                            bot_obj.process_withdrawal()
                        
                        wait = random.randint(60, 120)
                        bot.countdown(wait, "Cycle Timer")
                except KeyboardInterrupt:
                    bot.info("Loop stopped by user")
            
            bot_obj.check_dashboard()
            bot.info(f"Balance: {bot_obj.balance} coins")
            input("\nPress Enter to continue...")
            
        elif choice == '6':
            print(f"\n{C['yellow']}Exiting...{C['reset']}")
            break

if __name__ == "__main__":
    main()

