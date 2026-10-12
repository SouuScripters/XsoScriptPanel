#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoCrops Auto Farm - v5
===========================
Fix:
  - Cookie parsing robust (jadi cookie jar bener)
  - AUTHENTICATION_REQUIRED → bot STOP, bukan cooldown
  - Local state = source of truth setelah plant/harvest
  - Bootstrap gagal → JANGAN overwrite local state
"""

import json
import os
import sys
import time
import uuid
import base64
import hashlib
import random
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

try:
    import requests
except ImportError:
    print("ERROR: install dulu 'requests' → pip install requests")
    sys.exit(1)

# ==================== CONSTANTS ====================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "cconfig.json"
BASE = "https://cryptocrops.net"

DEFAULT_CONFIG = {
    "cookie": "",
    "idle_poll_seconds": 30,
    "enable_harvest": True,
    "enable_plant": True,
    "enable_faucet": True,
    "enable_mission": True,
}

RUN_HOURS_BEFORE_PAUSE = 5
PAUSE_MINUTES = 30
MIN_IDLE_SLEEP = 3.0
FAUCET_FAIL_COOLDOWN = 120

# ==================== STATS / STATE ====================
STATS = {
    "started_at": time.time(),
    "cycles": 0, "idle_cycles": 0,
    "harvested": 0, "planted": 0,
    "faucet_claims": 0, "faucet_coins": 0,
    "mission_claims": 0, "mission_xp": 0,
    "checkpoint_ok": 0, "errors": 0,
    "solver_success": 0, "solver_failed": 0,
    "pause_count": 0,
}

STATE = {
    "farm_coins": 0,
    "farm_level": 1,
    "farm_xp": 0,
    "total_capacity": 4,
    "base_capacity": 4,
    "crops": [],
    "seeds": {},
    "faucet_next_at_ms": 0,
    "faucet_available": False,
    "missions_ready": 0,
    "checkpoint_required": False,
    "last_sync": 0.0,
    "faucet_fail_until_ms": 0,
}

AUTH_ERROR_KEYWORDS = [
    "AUTHENTICATION_REQUIRED",
    "UNAUTHORIZED",
    "INVALID_SESSION",
    "SESSION_EXPIRED",
    "AUTH_REQUIRED",
]

# ==================== COLORS ====================
class C:
    R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; MAGENTA = "\033[95m"; BLUE = "\033[94m"
    WHITE = "\033[97m"; GRAY = "\033[90m"

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_spin_idx = 0
_spin_lock = threading.Lock()

# ==================== UTILS ====================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def fmt_duration(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def banner():
    clear()
    print(f"""{C.GREEN}{C.BOLD}
   ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗  ██████╗██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗██╔════╝
  ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║██║     ██████╔╝██║   ██║██████╔╝███████╗
  ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║██║     ██╔══██╗██║   ██║██╔═══╝ ╚════██║
  ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝╚██████╗██║  ██║╚██████╔╝██║     ███████║
   ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝
{C.R}
{C.CYAN}    Auto Farm · Faucet · Mission  |  Local Countdown (minimal request){C.R}
{C.MAGENTA}                       By MoneyMaker_w{C.R}
{C.CYAN}          Telegram Group: https://t.me/+RInZ35ML2GhjM2I1{C.R}
{C.GRAY}   ────────────────────────────────────────────────────────{C.R}
""")

def log(msg, level="info"):
    icons = {
        "info": f"{C.CYAN}ℹ{C.R}", "ok": f"{C.GREEN}✔{C.R}",
        "warn": f"{C.YELLOW}⚠{C.R}", "err": f"{C.RED}✖{C.R}",
        "farm": f"{C.GREEN}🌱{C.R}", "coin": f"{C.YELLOW}🪙{C.R}",
        "mission": f"{C.MAGENTA}🎯{C.R}", "captcha": f"{C.BLUE}🔐{C.R}",
        "wait": f"{C.GRAY}⏳{C.R}", "pause": f"{C.MAGENTA}⏸{C.R}",
        "sync": f"{C.BLUE}🔄{C.R}",
    }
    icon = icons.get(level, icons["info"])
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    print(f"{C.GRAY}[{now_str()}]{C.R} {icon}  {msg}")

def section(title):
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    print(f"\n{C.BOLD}{C.GREEN}▸ {title}{C.R}")
    print(f"{C.GRAY}{'─' * 56}{C.R}")

def spinner_line(text):
    global _spin_idx
    with _spin_lock:
        frame = SPINNER[_spin_idx % len(SPINNER)]
        _spin_idx += 1
    sys.stdout.write(f"\r\033[K{C.CYAN}{frame}{C.R}  {text}")
    sys.stdout.flush()

def clear_spinner():
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

def is_auth_error(err_str):
    """Cek apakah error message indikasi auth gagal."""
    s = str(err_str).upper()
    return any(k in s for k in AUTH_ERROR_KEYWORDS)

# ==================== CONFIG ====================
def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"{C.RED}!! Gagal simpan config: {e}{C.R}")

def normalize_cookie(raw):
    """
    Bersihkan cookie string:
      - Trim spasi/newline
      - Buang kontrol karakter & zero-width
      - Ganti separator koma → titik-koma
      - Rapihin spasi setelah ;
    """
    if not raw:
        return ""
    # Buang \r\n, \t, zero-width
    raw = raw.strip().replace("\r", "").replace("\n", "").replace("\t", " ")
    raw = raw.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    # Kalau pakai koma sebagai separator
    if ";" not in raw and "," in raw:
        raw = raw.replace(",", ";")
    # Rapihin spasi setelah ;
    import re
    raw = re.sub(r"\s*;\s*", "; ", raw)
    return raw.strip().rstrip(";")

def ensure_config():
    cfg = load_config()
    if cfg and isinstance(cfg, dict):
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        for old in ("waryono_apikey", "loop_delay", "human_delay_min", "human_delay_max"):
            if old in cfg:
                cfg.pop(old, None)
                changed = True
        # Normalize cookie setiap load
        if cfg.get("cookie"):
            normalized = normalize_cookie(cfg["cookie"])
            if normalized != cfg["cookie"]:
                cfg["cookie"] = normalized
                changed = True
        if changed:
            save_config(cfg)
        return cfg

    banner()
    section("Setup Config Pertama Kali")
    print(f"{C.YELLOW}File cconfig.json belum ada. Isi data di bawah:{C.R}\n")
    cookie = input(f"  {C.CYAN}Cookie browser{C.R} : ").strip()
    cfg = dict(DEFAULT_CONFIG)
    cfg["cookie"] = normalize_cookie(cookie)
    save_config(cfg)
    print(f"\n{C.GREEN}✔ cconfig.json tersimpan di {CONFIG_PATH}{C.R}\n")
    time.sleep(1)
    return cfg

# ==================== ALTCHA SOLVER ====================
def solve_altcha(params, verbose=True):
    algorithm = params["algorithm"]
    cost = int(params["cost"])
    key_length = int(params.get("keyLength", 32))
    key_prefix = params["keyPrefix"].lower()
    nonce = bytes.fromhex(params["nonce"])
    salt = bytes.fromhex(params["salt"])

    algo_map = {
        "PBKDF2/SHA-256": "sha256",
        "PBKDF2/SHA-384": "sha384",
        "PBKDF2/SHA-512": "sha512",
    }
    if algorithm not in algo_map:
        raise Exception(f"Algo altcha unsupported: {algorithm}")
    py_algo = algo_map[algorithm]

    if verbose:
        log(f"Altcha {algorithm} cost={cost} prefix={key_prefix[:16]}...", "captcha")

    counter = 0
    start = time.time()
    max_iter = 500000

    while counter < max_iter:
        password = nonce + counter.to_bytes(4, byteorder="big")
        derived = hashlib.pbkdf2_hmac(py_algo, password, salt, cost, dklen=key_length)
        hex_str = derived.hex()

        if hex_str.startswith(key_prefix):
            elapsed_ms = round((time.time() - start) * 1000, 1)
            if verbose:
                clear_spinner()
                log(f"Altcha solved: counter={counter} ({elapsed_ms}ms)", "ok")
            STATS["solver_success"] += 1
            return {"counter": counter, "derivedKey": hex_str, "time": elapsed_ms}

        counter += 1
        if verbose and counter % 200 == 0:
            elapsed = round((time.time() - start) * 1000, 0)
            spinner_line(f"Altcha searching counter={counter} ({elapsed}ms)")

    clear_spinner()
    STATS["solver_failed"] += 1
    return None

def build_altcha_token(altcha_block, solution):
    payload = {
        "challenge": {
            "parameters": altcha_block["parameters"],
            "signature":  altcha_block["signature"],
        },
        "solution": {
            "counter":    solution["counter"],
            "derivedKey": solution["derivedKey"],
            "time":       solution["time"],
        },
    }
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.b64encode(raw.encode()).decode()

def extract_altcha_block(payload):
    if not isinstance(payload, dict):
        return None
    candidates = [payload.get("altcha"), payload.get("captcha"), payload]
    for c in candidates:
        if isinstance(c, dict) and c.get("parameters") and c.get("signature"):
            return {"parameters": c["parameters"], "signature": c["signature"]}
    cap = payload.get("captcha")
    if isinstance(cap, dict):
        nested = cap.get("altcha")
        if isinstance(nested, dict) and nested.get("parameters") and nested.get("signature"):
            return {"parameters": nested["parameters"], "signature": nested["signature"]}
    return None

# ==================== STATE UPDATER ====================
def update_state_from_bootstrap(bootstrap):
    """
    Sync STATE dari bootstrap.
    PENTING: crop yg belum punya crop_id di server akan di-SKIP countdown,
    tapi tetap dihitung di total crops (based on plot_index).
    """
    farm = bootstrap.get("farm") or {}
    profile = farm.get("profile") or {}

    STATE["farm_coins"] = profile.get("farm_coins", 0)
    STATE["farm_level"] = profile.get("farm_level", 1)
    STATE["farm_xp"] = profile.get("farm_xp", 0)
    STATE["total_capacity"] = profile.get("total_capacity") or profile.get("base_capacity") or 4
    STATE["base_capacity"] = profile.get("base_capacity") or 4

    crops = []
    for c in farm.get("crops") or []:
        crops.append({
            "crop_id": c.get("crop_id"),
            "seed_id": c.get("seed_id"),
            "plot_index": c.get("plot_index"),
            "ready_at_ms": c.get("ready_at") or c.get("harvest_ready_at") or 0,
            "status": c.get("status"),
        })
    STATE["crops"] = crops

    seeds = {}
    for s in farm.get("seeds") or []:
        seeds[s["seed_id"]] = s.get("quantity", 0)
    STATE["seeds"] = seeds

    faucet = farm.get("faucet") or {}
    now_ms = int(time.time() * 1000)
    next_claim = int(faucet.get("next_claim_at") or 0)
    STATE["faucet_available"] = bool(faucet.get("available")) and next_claim <= now_ms
    STATE["faucet_next_at_ms"] = next_claim

    missions = farm.get("missions") or []
    STATE["missions_ready"] = sum(
        1 for m in missions if m.get("complete") and not m.get("claimed")
    )

    checkpoint = farm.get("farm_checkpoint") or {}
    STATE["checkpoint_required"] = bool(checkpoint.get("required"))
    STATE["last_sync"] = time.time()

# ==================== CLIENT ====================
class FarmClient:
    RARITY_RANK = {"mythical": 6, "legendary": 5, "epic": 4,
                   "rare": 3, "uncommon": 2, "common": 1}

    def __init__(self, cfg):
        self.cfg = cfg
        self._catalog = {}
        self._last_bootstrap = {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Linux; Android 10; K) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/127.0.0.0 Mobile Safari/537.36"),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": BASE,
            "Referer": f"{BASE}/faucet/",
        })
        # ── FIX #1: Set cookies properly via cookie jar (bukan header) ──
        cookie_raw = normalize_cookie(cfg.get("cookie", ""))
        for part in cookie_raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = unquote(v.strip())  # decode URL-encoded values
                if k and v:
                    self.session.cookies.set(k, v, domain="cryptocrops.net")

    def api(self, method, path, json_data=None, referer=None):
        headers = {}
        if referer:
            headers["Referer"] = referer
        r = self.session.request(
            method, BASE + path, json=json_data, headers=headers or None, timeout=45
        )

        # Parse JSON first, then check status
        try:
            data = r.json()
        except Exception:
            raise Exception(f"HTTP {r.status_code} | non-JSON: {r.text[:200]}")

        if r.status_code >= 400:
            err = data.get("error") or data.get("message") or str(data)
            raise Exception(err)

        return data

    def bootstrap(self, update_state=True):
        data = self.api("GET", "/api/bootstrap")
        self._last_bootstrap = data
        if update_state:
            update_state_from_bootstrap(data)
        return data

    def load_catalog(self):
        if self._catalog:
            return self._catalog
        data = self.api("GET", "/api/catalog?version=3")
        seeds = data.get("seeds") or []
        self._catalog = {s["seed_id"]: s for s in seeds}
        return self._catalog

    def seed_priority(self, seed_id):
        cat = self.load_catalog()
        info = cat.get(seed_id) or {}
        points = int(info.get("base_points") or 0)
        rarity = str(info.get("rarity", "")).lower()
        rank = info.get("rarity_rank")
        if rank is None:
            rank = self.RARITY_RANK.get(rarity, 0)
        grow = int(info.get("grow_seconds") or 0)
        return (points, int(rank), grow)

    def seed_grow_seconds(self, seed_id):
        cat = self.load_catalog()
        info = cat.get(seed_id) or {}
        return int(info.get("grow_seconds") or 0)

    # ---------- CHECKPOINT ----------
    def handle_checkpoint(self, bootstrap):
        security = bootstrap.get("security") or {}
        farm = bootstrap.get("farm") or {}
        checkpoint = farm.get("farm_checkpoint") or {}

        if not security.get("farm_checkpoint_enabled"):
            return False
        if not checkpoint.get("required"):
            return False

        provider = security.get("farm_checkpoint_provider", "altcha")
        if provider != "altcha":
            log(f"Provider bukan altcha ({provider}), skip", "warn")
            return False

        log("Farm checkpoint required", "warn")
        attempt_id = str(uuid.uuid4())
        try:
            chal = self.api("POST", "/api/farm-checkpoint/challenge",
                            {"attempt_id": attempt_id}, referer=f"{BASE}/farm/")
        except Exception as e:
            if is_auth_error(e):
                raise
            log(f"Checkpoint challenge error: {e}", "warn")
            return False

        altcha_block = extract_altcha_block(chal)
        if not altcha_block:
            log("Checkpoint: tidak ada altcha params", "warn")
            return False

        server_attempt_id = chal.get("attempt_id") or attempt_id
        required_since = (chal.get("checkpoint") or {}).get("required_since") or \
                         checkpoint.get("required_since") or 0

        try:
            solution = solve_altcha(altcha_block["parameters"])
        except Exception as e:
            log(f"Altcha solve error: {e}", "err")
            return False
        if not solution:
            log("Altcha solve failed", "err")
            return False

        captcha_token = build_altcha_token(altcha_block, solution)
        try:
            result = self.api("POST", "/api/farm-checkpoint/verify",
                              {"attempt_id": server_attempt_id,
                               "required_since": int(required_since),
                               "captcha_token": captcha_token},
                              referer=f"{BASE}/farm/")
        except Exception as e:
            log(f"Checkpoint verify error: {e}", "warn")
            return False

        if result.get("verified"):
            log("Checkpoint ✓ verified", "ok")
            STATS["checkpoint_ok"] += 1
            STATE["checkpoint_required"] = False
            return True
        log(f"Verify checkpoint gagal: {result}", "warn")
        return False

    # ---------- HARVEST ----------
    def harvest(self):
        now_ms = int(time.time() * 1000)
        ready = [c for c in STATE["crops"]
                 if c.get("crop_id") and c["ready_at_ms"] and now_ms >= c["ready_at_ms"]]

        if not ready:
            log("Tidak ada crop ready", "wait")
            return 0

        count = 0
        for crop in ready:
            crop_id = crop["crop_id"]
            try:
                res = self.api("POST", "/api/farm/harvest", {
                    "idempotency_key": str(uuid.uuid4()),
                    "crop_id": crop_id,
                })
                h = res.get("harvested", {})
                pts = h.get("point_value", "?")
                perfect = " (Perfect)" if h.get("perfect_harvest") else ""
                log(f"Harvest {crop['seed_id']} → {pts} pts{perfect}", "farm")
                count += 1
                STATS["harvested"] += 1
                # Hapus dari local state
                STATE["crops"] = [c for c in STATE["crops"] if c.get("crop_id") != crop_id]
                # Update coins kalau server kasih
                if "coins" in res:
                    try:
                        STATE["farm_coins"] = int(res["coins"])
                    except (TypeError, ValueError):
                        pass
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                if is_auth_error(e) or "FARM_CHECKPOINT_REQUIRED" in str(e):
                    raise
                log(f"Gagal harvest {crop_id}: {e} (skip)", "warn")
        return count

    # ---------- PLANT ----------
    def plant(self):
        capacity = max(1, min(int(STATE["total_capacity"]), 24))
        used_plots = {c["plot_index"] for c in STATE["crops"] if c.get("plot_index") is not None}
        empty_plots = [i for i in range(1, capacity + 1) if i not in used_plots]

        if not empty_plots:
            log("Tidak ada plot kosong", "wait")
            return 0

        planted_map = {}
        for c in STATE["crops"]:
            sid = c.get("seed_id")
            if sid:
                planted_map[sid] = planted_map.get(sid, 0) + 1

        available = []
        for sid, qty in STATE["seeds"].items():
            free = qty - planted_map.get(sid, 0)
            if free > 0:
                available.append({"seed_id": sid, "free": free})

        if not available:
            log("Tidak ada seed free", "wait")
            return 0

        available.sort(key=lambda x: self.seed_priority(x["seed_id"]), reverse=True)
        top = available[0]
        info = self.load_catalog().get(top["seed_id"], {})
        log(f"Prioritas: {info.get('name', top['seed_id'])} "
            f"[{info.get('rarity', '?')}] {int(info.get('base_points', 0))} pts · "
            f"grow {int(info.get('grow_seconds', 0)) // 3600}h", "farm")
        log(f"Plot: {len(empty_plots)} kosong / {capacity} total", "info")

        count = 0
        for plot in empty_plots:
            chosen = None
            for item in available:
                if item["free"] > 0:
                    chosen = item
                    break
            if not chosen:
                break

            seed_id = chosen["seed_id"]
            try:
                resp = self.api("POST", "/api/farm/plant", {
                    "idempotency_key": str(uuid.uuid4()),
                    "seed_id": seed_id,
                    "plot_index": plot,
                })
                info = self.load_catalog().get(seed_id, {})
                name = info.get("name", seed_id)
                rarity = info.get("rarity", "?")
                pts = int(info.get("base_points", 0))
                log(f"Plant {name} [{rarity}] {pts} pts → plot {plot}", "farm")

                # Update local state
                STATE["seeds"][seed_id] = STATE["seeds"].get(seed_id, 0) - 1
                grow_sec = self.seed_grow_seconds(seed_id)
                STATE["crops"].append({
                    "crop_id": None,
                    "seed_id": seed_id,
                    "plot_index": plot,
                    "ready_at_ms": int((time.time() + grow_sec) * 1000),
                    "status": "growing",
                })
                chosen["free"] -= 1
                count += 1
                STATS["planted"] += 1
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                if is_auth_error(e) or "FARM_CHECKPOINT_REQUIRED" in str(e):
                    raise
                log(f"Gagal plant plot {plot}: {e} (skip)", "warn")
                break
        return count

    # ---------- FAUCET ----------
    def faucet(self):
        now_ms = int(time.time() * 1000)

        if STATE["faucet_fail_until_ms"] > now_ms:
            return False
        if not STATE["faucet_available"] or STATE["faucet_next_at_ms"] > now_ms:
            if STATE["faucet_next_at_ms"] > now_ms:
                sisa = max(0, (STATE["faucet_next_at_ms"] - now_ms) // 1000)
                log(f"Faucet cooldown {fmt_duration(sisa)}", "wait")
            return False

        log("Ambil faucet challenge...", "coin")
        try:
            challenge_payload = self.api("POST", "/api/earn/faucet-challenge", {},
                                         referer=f"{BASE}/faucet/")
        except Exception as e:
            err_str = str(e)
            if is_auth_error(err_str):
                # ── FIX #2: Auth error → STOP, jangan cooldown ──
                raise Exception(f"AUTH_EXPIRED: {err_str}")
            log(f"Faucet challenge error: {err_str}", "warn")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + FAUCET_FAIL_COOLDOWN) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + FAUCET_FAIL_COOLDOWN) * 1000)
            return False

        challenge = challenge_payload.get("challenge") or {}
        challenge_id = str(challenge.get("challenge_id") or "")
        expires_at = int(challenge.get("expires_at") or 0)
        now_ms = int(time.time() * 1000)

        if not challenge_id or (expires_at and expires_at <= now_ms):
            log("Challenge kosong / expired", "warn")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + 60) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + 60) * 1000)
            return False

        log(f"Challenge: {challenge_id[:18]}...", "coin")

        altcha_block = extract_altcha_block(challenge_payload)
        if not altcha_block:
            log("Tidak ada altcha params di response", "warn")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + 60) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + 60) * 1000)
            return False

        try:
            solution = solve_altcha(altcha_block["parameters"])
        except Exception as e:
            log(f"Altcha solve error: {e}", "err")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + 60) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + 60) * 1000)
            return False
        if not solution:
            log("Altcha solve failed", "err")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + 60) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + 60) * 1000)
            return False

        token = build_altcha_token(altcha_block, solution)
        try:
            result = self.api("POST", "/api/earn/faucet",
                              {"idempotency_key": str(uuid.uuid4()),
                               "faucet_challenge": challenge_id,
                               "captcha_token": token},
                              referer=f"{BASE}/faucet/")
        except Exception as e:
            err_str = str(e)
            if is_auth_error(err_str):
                raise Exception(f"AUTH_EXPIRED: {err_str}")
            log(f"Faucet claim error: {err_str}", "warn")
            STATE["faucet_available"] = False
            STATE["faucet_next_at_ms"] = int((time.time() + 60) * 1000)
            STATE["faucet_fail_until_ms"] = int((time.time() + 60) * 1000)
            return False

        claimed = result.get("claimed") or result
        coins = claimed.get("total_coins") or claimed.get("coins") or 0
        log(f"Faucet claimed! +{coins} Farm Coins", "coin")

        STATS["faucet_claims"] += 1
        try:
            STATS["faucet_coins"] += int(coins)
        except (TypeError, ValueError):
            pass

        if "farm_coin_balance" in claimed:
            try:
                STATE["farm_coins"] = int(claimed["farm_coin_balance"])
            except (TypeError, ValueError):
                pass

        next_ts = 0
        if "next_claim_at" in claimed:
            try:
                next_ts = int(claimed["next_claim_at"])
            except (TypeError, ValueError):
                pass
        if not next_ts and "faucetCooldownSeconds" in result:
            try:
                next_ts = int((time.time() + int(result["faucetCooldownSeconds"])) * 1000)
            except (TypeError, ValueError):
                pass
        if not next_ts:
            next_ts = int((time.time() + 300) * 1000)

        STATE["faucet_next_at_ms"] = next_ts
        STATE["faucet_available"] = False
        STATE["faucet_fail_until_ms"] = 0
        return True

    # ---------- MISSION ----------
    def claim_missions(self):
        missions = (self._last_bootstrap.get("farm") or {}).get("missions") or []
        ready = [m for m in missions if m.get("complete") and not m.get("claimed")]
        if not ready:
            log("Tidak ada mission siap claim", "wait")
            return 0

        count = 0
        for m in ready:
            mid = m.get("mission_id")
            title = m.get("title", mid)
            try:
                res = self.api("POST", "/api/missions/claim",
                               {"idempotency_key": str(uuid.uuid4()), "mission_id": mid},
                               referer=f"{BASE}/missions/")
                claimed = res.get("claimed") or {}
                xp = claimed.get("pass_xp_earned", m.get("pass_xp", "?"))
                fert = claimed.get("fertilizer_rarity")
                extra = f" + {fert} fertilizer" if fert else ""
                log(f"Mission: {title} → +{xp} Pass XP{extra}", "mission")
                count += 1
                STATS["mission_claims"] += 1
                try:
                    STATS["mission_xp"] += int(xp)
                except (TypeError, ValueError):
                    pass
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                if is_auth_error(e):
                    raise
                log(f"Gagal claim {title}: {e} (skip)", "warn")
        return count

# ==================== DASHBOARD ====================
IDLE_POLL = 30

def next_event_time():
    now = time.time()
    candidates = []

    if STATE["faucet_next_at_ms"] > 0:
        ft = STATE["faucet_next_at_ms"] / 1000.0
        if ft > now:
            candidates.append(ft)
        elif STATE["faucet_available"]:
            candidates.append(now)

    for c in STATE["crops"]:
        r = c.get("ready_at_ms", 0)
        if r > 0:
            ts = r / 1000.0
            if ts > now:
                candidates.append(ts)
            else:
                candidates.append(now)

    if not candidates:
        return now + IDLE_POLL
    return min(candidates)


def dashboard_line():
    now = time.time()

    if STATE["faucet_fail_until_ms"] > time.time() * 1000:
        faucet = f"{C.RED}LMT{C.R}"
    elif STATE["faucet_next_at_ms"] > 0 and STATE["faucet_next_at_ms"] / 1000.0 > now:
        faucet = f"{C.YELLOW}{fmt_duration(STATE['faucet_next_at_ms'] / 1000.0 - now)}{C.R}"
    else:
        faucet = f"{C.GREEN}OK{C.R}"

    # Crop ready terdekat (dari semua crop, termasuk yg crop_id=None)
    crop_ready_ts = None
    for c in STATE["crops"]:
        r = c.get("ready_at_ms", 0) / 1000.0
        if r > 0:
            if crop_ready_ts is None or r < crop_ready_ts:
                crop_ready_ts = r

    if crop_ready_ts is not None and crop_ready_ts > now:
        crop = f"{C.CYAN}{fmt_duration(crop_ready_ts - now)}{C.R}"
    elif crop_ready_ts is not None:
        crop = f"{C.GREEN}RDY{C.R}"
    else:
        crop = f"{C.GRAY}--{C.R}"

    runtime = fmt_duration(now - STATS["started_at"])
    crops = len(STATE["crops"])

    return (
        f"{C.GRAY}[{now_str()}]{C.R} "
        f"🪙{C.YELLOW}{STATE['farm_coins']}{C.R} "
        f"Lv{STATE['farm_level']} "
        f"🌱{crops}/{STATE['total_capacity']}({crop}) "
        f"🚰{faucet} "
        f"🎯{STATE['missions_ready']} "
        f"⏱{C.CYAN}{runtime}{C.R}"
    )


def wait_with_dashboard(target_ts, label="wait"):
    print()
    last_sec = -1
    try:
        while True:
            left = target_ts - time.time()
            if left <= 0:
                break
            cur_sec = int(left)
            if cur_sec != last_sec:
                line = f"{dashboard_line()} {C.GRAY}💤{fmt_duration(left)}{C.R}"
                sys.stdout.write(f"\r\033[K{line}")
                sys.stdout.flush()
                last_sec = cur_sec
            time.sleep(min(left, 0.2))
    finally:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

# ==================== SUMMARY / PAUSE ====================
def show_summary(reason="AUTO-PAUSE"):
    runtime = time.time() - STATS["started_at"]
    sys.stdout.write("\r\033[K")
    print()
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}  📊  RINGKASAN AKTIVITAS — {reason}{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print(f"  {C.WHITE}Runtime          :{C.R} {C.CYAN}{fmt_duration(runtime)}{C.R}")
    print(f"  {C.WHITE}Cycles           :{C.R} {C.CYAN}{STATS['cycles']}{C.R}")
    print(f"  {C.WHITE}Idle cycles      :{C.R} {C.CYAN}{STATS['idle_cycles']}{C.R}")
    print(f"  {C.GREEN}🌱 Harvested     :{C.R} {C.CYAN}{STATS['harvested']}{C.R}")
    print(f"  {C.GREEN}🌱 Planted       :{C.R} {C.CYAN}{STATS['planted']}{C.R}")
    print(f"  {C.YELLOW}🪙 Faucet claims  :{C.R} {C.CYAN}{STATS['faucet_claims']}{C.R}")
    print(f"  {C.YELLOW}🪙 Faucet coins   :{C.R} {C.CYAN}{STATS['faucet_coins']}{C.R}")
    print(f"  {C.MAGENTA}🎯 Mission claims :{C.R} {C.CYAN}{STATS['mission_claims']}{C.R}")
    print(f"  {C.MAGENTA}🎯 Mission XP     :{C.R} {C.CYAN}{STATS['mission_xp']}{C.R}")
    print(f"  {C.BLUE}🔐 Checkpoint OK  :{C.R} {C.CYAN}{STATS['checkpoint_ok']}{C.R}")
    print(f"  {C.BLUE}🔐 Solver         :{C.R} {C.GREEN}OK:{STATS['solver_success']}{C.R} {C.RED}Fail:{STATS['solver_failed']}{C.R}")
    print(f"  {C.RED}✖ Errors          :{C.R} {C.CYAN}{STATS['errors']}{C.R}")
    print(f"  {C.WHITE}Pauses           :{C.R} {C.CYAN}{STATS['pause_count']}{C.R}")
    print(f"  {C.WHITE}Balance (local)  :{C.R} {C.YELLOW}{STATE['farm_coins']}{C.R}")
    print(f"{C.MAGENTA}{C.BOLD}════════════════════════════════════════════════════════{C.R}")
    print()


def auto_pause_countdown(minutes):
    total = int(minutes * 60)
    log(f"Auto-pause {minutes} menit...", "pause")
    end = time.time() + total
    while True:
        left = int(end - time.time())
        if left <= 0:
            break
        spinner_line(f"⏸ PAUSED — resume in {fmt_duration(left)} (Ctrl+C stop)")
        time.sleep(1)
    clear_spinner()
    log("Resume!", "ok")


def check_auto_pause():
    if time.time() - STATS["started_at"] >= RUN_HOURS_BEFORE_PAUSE * 3600:
        show_summary("AUTO-PAUSE")
        auto_pause_countdown(PAUSE_MINUTES)
        STATS["started_at"] = time.time()
        STATS["pause_count"] += 1
        return True
    return False

# ==================== MAIN ====================
def main():
    global IDLE_POLL

    cfg = ensure_config()
    if not cfg.get("cookie"):
        banner()
        log("cookie kosong di cconfig.json", "err")
        return

    banner()
    IDLE_POLL = int(cfg.get("idle_poll_seconds", 30))
    client = FarmClient(cfg)

    try:
        client.load_catalog()
        log(f"Catalog loaded: {len(client._catalog)} seeds", "ok")
    except Exception as e:
        log(f"Gagal load catalog: {e}", "warn")

    log("Bot started — minimal request mode", "ok")
    log(f"Idle poll: {IDLE_POLL}s | Faucet fail cooldown: {FAUCET_FAIL_COOLDOWN}s", "info")

    section("Initial Bootstrap")
    try:
        client.bootstrap(update_state=True)
        log(f"Synced: {STATE['farm_coins']} coins, Lv{STATE['farm_level']}, "
            f"{len(STATE['crops'])} crops, "
            f"faucet {'READY' if STATE['faucet_available'] else 'CD'}", "sync")
    except Exception as e:
        if is_auth_error(e):
            log(f"❌ Cookie expired / invalid saat bootstrap!", "err")
            log(f"Update cookie di: {CONFIG_PATH}", "err")
            return
        log(f"Bootstrap error: {e}", "err")
        return

    print()
    while True:
        try:
            now = time.time()
            now_ms = int(now * 1000)

            crops_ready = [c for c in STATE["crops"]
                           if c["ready_at_ms"] and now_ms >= c["ready_at_ms"]]
            faucet_ready = (
                STATE["faucet_available"]
                and STATE["faucet_next_at_ms"] <= now_ms
                and STATE["faucet_fail_until_ms"] <= now_ms
            )
            mission_ready = STATE["missions_ready"] > 0
            checkpoint_ready = STATE["checkpoint_required"]

            need_action = crops_ready or faucet_ready or mission_ready or checkpoint_ready

            # ── IDLE ──
            if not need_action:
                STATS["idle_cycles"] += 1
                target = next_event_time()

                min_sleep = time.time() + MIN_IDLE_SLEEP
                if target < min_sleep:
                    target = min_sleep

                if STATS["idle_cycles"] == 1 or STATS["idle_cycles"] % 10 == 0:
                    section(f"Idle #{STATS['idle_cycles']}")
                    print(dashboard_line())

                wait_with_dashboard(target, label="next event")
                continue

            # ── CYCLE ──
            STATS["cycles"] += 1
            section(f"Cycle #{STATS['cycles']}")
            print(dashboard_line())
            print()

            harvested = planted = claimed_m = 0
            did_anything = False
            auth_error = False

            # Checkpoint
            if STATE["checkpoint_required"]:
                try:
                    client.bootstrap(update_state=True)
                except Exception as e:
                    if is_auth_error(e):
                        auth_error = True
                if not auth_error:
                    try:
                        client.handle_checkpoint(client._last_bootstrap or {})
                    except Exception as e:
                        if is_auth_error(e):
                            auth_error = True
                        else:
                            log(f"Checkpoint error: {e}", "warn")
                            STATS["errors"] += 1

            # Harvest
            if not auth_error and cfg.get("enable_harvest", True) and crops_ready:
                try:
                    harvested = client.harvest()
                    did_anything = did_anything or bool(harvested)
                except Exception as e:
                    if is_auth_error(e):
                        auth_error = True
                    elif "FARM_CHECKPOINT_REQUIRED" in str(e):
                        try:
                            client.bootstrap(update_state=True)
                            if client.handle_checkpoint(client._last_bootstrap or {}):
                                harvested = client.harvest()
                                did_anything = did_anything or bool(harvested)
                        except Exception as e2:
                            if is_auth_error(e2):
                                auth_error = True
                            else:
                                log(f"Harvest retry fail: {e2}", "warn")
                    else:
                        log(f"Harvest error: {e}", "warn")
                        STATS["errors"] += 1

            # Plant
            if not auth_error and cfg.get("enable_plant", True):
                try:
                    planted = client.plant()
                    did_anything = did_anything or bool(planted)
                except Exception as e:
                    if is_auth_error(e):
                        auth_error = True
                    else:
                        log(f"Plant error: {e}", "warn")
                        STATS["errors"] += 1

            # Faucet
            if not auth_error and cfg.get("enable_faucet", True) and faucet_ready:
                try:
                    if client.faucet():
                        did_anything = True
                except Exception as e:
                    if is_auth_error(e):
                        auth_error = True
                    else:
                        log(f"Faucet error: {e}", "err")
                        STATS["errors"] += 1

            # Mission
            if not auth_error and cfg.get("enable_mission", True) and mission_ready:
                try:
                    claimed_m = client.claim_missions()
                    did_anything = did_anything or bool(claimed_m)
                except Exception as e:
                    if is_auth_error(e):
                        auth_error = True
                    else:
                        log(f"Mission error: {e}", "warn")
                        STATS["errors"] += 1

            # ── AUTH ERROR HANDLING ──
            if auth_error:
                print()
                log("❌ SESSION EXPIRED / INVALID!", "err")
                log(f"Update cookie di: {CONFIG_PATH}", "err")
                log("Cara: buka cryptocrops.net di browser, F12 → Application → Cookies", "info")
                log("Copy value 'cc_session_v1=...' ke cconfig.json", "info")
                show_summary("AUTH EXPIRED — MANUAL STOP")
                return

            print()
            log(f"Selesai → H:{harvested} P:{planted} M:{claimed_m}", "ok")

            # Re-sync — tapi HANYA kalau bukan auth error
            if did_anything:
                try:
                    log("Re-sync state...", "sync")
                    client.bootstrap(update_state=True)
                except Exception as e:
                    log(f"Re-sync error: {e}", "warn")
                    STATS["errors"] += 1

            check_auto_pause()
            time.sleep(MIN_IDLE_SLEEP)

        except KeyboardInterrupt:
            print()
            log("Stopped by user.", "warn")
            show_summary("MANUAL STOP")
            break
        except Exception as e:
            log(f"Loop error: {e} (retry 15s)", "err")
            STATS["errors"] += 1
            time.sleep(15)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Stopped.{C.R}")
