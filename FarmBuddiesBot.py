#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FarmBuddies Auto Claim — SOUU ENGINE EDITION v7 (FULL AUTO FIXED)
Live Dashboard TUI
Base: AHD1905 (fixed by Kyriel v4)
UI  : Souu Engine

Endpoint map (dari sniff network):
  AUTH    : POST /auth/telegram
  STATE   : GET  /user/bootstrap  |  GET /user/home  |  GET /tasks
  JOIN    : GET  /user/force-join |  POST /user/force-join
  TERMS   : GET  /user/accept-terms
  STREAK  : POST /user/streak/claim
  ADS     : POST /ads/task/{id}/session     (mulai)
            POST /ads/task/{id}/complete    (selesai)
            POST /ads/task/{id}/reward      (khusus adsgramTask id=4)
  HARVEST : POST /ads/harvest/session  +  /ads/harvest/complete
  WATER   : POST /ads/farm/session     +  /ads/farm/complete
  FARM    : POST /farm/plant  |  POST /farm/water
  LINK    : POST /tasks/{id}/start     (dapet reward instan)
            POST /tasks/{id}/claim
  SHORT   : GET  /shortlinks
            POST /shortlinks/{pid}/issue  (guess)
            POST /shortlinks/{pid}/claim  (guess)
"""

import time
import json
import os
import sys
import re
import base64
import random
import urllib.parse
import requests
from datetime import datetime

# ═══════════════ KONSTANTA ═══════════════
CONFIG_FILE = "config.json"
CURRENT_TOKEN = None
CONFIG = {}
BASE_URL = ""
FARM_FP = ""
DEVICE_ID = ""
INIT_DATA = ""

W = 60

# ═══════════════ ANSI / SOUU PALETTE ═══════════════
RST = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[0;31m"
GRN = "\033[0;32m"
YEL = "\033[0;33m"
BLU = "\033[0;34m"
CYN = "\033[0;36m"
WHT = "\033[0;37m"

def fg(c): return f"\033[38;5;{c}m"

C_HDR_1  = 51
C_HDR_2  = 213
C_ACCENT = 226
C_OK     = 46
C_WARN   = 208
C_ERR    = 196
C_DIM    = 240
C_TEXT   = 252
C_SUB    = 245

def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def ansi_len(s):
    plain = strip_ansi(s)
    w = 0
    for ch in plain:
        cp = ord(ch)
        if (0x1F300 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF) or \
           (0x2B00 <= cp <= 0x2BFF) or (0x25A0 <= cp <= 0x25FF) or \
           (0x2580 <= cp <= 0x259F) or (0x2500 <= cp <= 0x257F):
            w += 2
        else:
            w += 1
    return w

def pad(s, n):
    p = n - ansi_len(s)
    return s + (" " * p if p > 0 else "")

def gradient(text, start=51, end=213):
    if len(text) <= 1:
        return fg(start) + text + RST
    out = ""
    n = len(text)
    for i, ch in enumerate(text):
        t = i / max(1, n - 1)
        c = int(round(start + (end - start) * t))
        out += fg(c) + ch
    return out + RST

# ═══════════════ GLOBAL STATE ═══════════════
_state = {
    "user": "-", "status": "boot", "aksi": "init",
    "start": time.time(),
    "ads_used": 0, "ads_max": 200,
    "coins": 0, "usdt": 0.0, "ads_done": 0, "today_earned": 0,
    "level": 1, "xp": 0, "xp_max": 3200,
    "water": 0, "water_max": 10, "farm_level": 1,
    "plots": [], "tasks": [], "shortlinks": [], "crops": [],
    "streak_day": 0, "streak_claimed": False,
    "claimed_ids": set(),
    "session_gained": 0,
    "logs": [],
}

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def push_log(msg, tag="i"):
    icons = {
        "i":  fg(C_HDR_1) + "●" + RST,
        "ok": fg(C_OK)    + "✔" + RST,
        "er": fg(C_ERR)   + "✖" + RST,
        "wr": fg(C_WARN)  + "◈" + RST,
        "in": fg(C_HDR_2) + "⬢" + RST,
        "g":  fg(C_ACCENT)+ "◆" + RST,
        "f":  fg(C_OK)    + "▲" + RST,
        "s":  fg(C_HDR_2) + "🌱" + RST,
        "w":  fg(C_HDR_1) + "💧" + RST,
    }
    line = f"{fg(C_DIM)}[{now_str()}]{RST} {icons.get(tag,'●')} {msg}"
    _state["logs"].append(line)
    if len(_state["logs"]) > 6:
        _state["logs"].pop(0)

def fmt_uptime(s):
    s = int(s); h = s // 3600; m = (s % 3600) // 60; sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"

# ═══════════════ BOX HELPERS ═══════════════
B = fg(C_HDR_1)
def top():  return B + "╔" + ("═" * (W + 2)) + "╗" + RST + "\n"
def bot():  return B + "╚" + ("═" * (W + 2)) + "╝" + RST + "\n"
def sep():  return B + "╠" + ("═" * (W + 2)) + "╣" + RST + "\n"
def row(content=""):
    return B + "║ " + RST + pad(content, W) + " " + B + "║" + RST + "\n"
def row_blank():
    return row("")

# ═══════════════ RENDER DASHBOARD ═══════════════
def render_dashboard():
    sys.stdout.write("\033[2J\033[H")
    out = []
    out.append(top())
    out.append(row(gradient("FARMBUDDIES DASHBOARD", C_HDR_1, C_HDR_2)))
    out.append(row(fg(C_DIM) + "SOUU ENGINE v7 • by AHD1905" + RST))
    out.append(sep())

    uptime = fmt_uptime(time.time() - _state["start"])
    ads_str = f"{_state['ads_used']}/{_state['ads_max']}"

    out.append(row(f"{fg(C_HDR_1)}👤 User   :{RST} {fg(C_ACCENT)}{_state['user']}{RST}"))
    out.append(row(f"{fg(C_HDR_1)}🎯 Fase   :{RST} {fg(C_OK)}{_state['status'].upper()}{RST}"))
    out.append(row(f"{fg(C_HDR_1)}⚡ Aksi   :{RST} {fg(C_TEXT)}{_state['aksi']}{RST}"))
    out.append(row(f"{fg(C_HDR_1)}⏱  Uptime :{RST} {fg(C_TEXT)}{uptime}{RST}"))
    out.append(row(f"{fg(C_HDR_1)}📺 Ads    :{RST} {fg(C_TEXT)}{ads_str}{RST}"))
    out.append(sep())

    # TUGAS
    out.append(row(f"{fg(C_HDR_2)}{BOLD}▌ TUGAS{RST}"))
    tasks = _state["tasks"]
    shown = 0
    if tasks:
        for t in tasks:
            if shown >= 6: break
            tid    = t.get("id", "?")
            title  = t.get("title", "Task")[:12]
            target = t.get("target", 10)
            prog   = t.get("progress", 0)
            state  = t.get("state", "open")
            rew    = t.get("reward", 0)
            pct    = int((prog / max(1, target)) * 100)
            bar_len = 8
            filled = int(bar_len * pct / 100)
            bar = f"{fg(C_OK)}" + ("█" * filled) + f"{fg(C_DIM)}" + ("░" * (bar_len - filled)) + RST
            if state == "done":
                st = fg(C_DIM) + "DONE" + RST
            elif t.get("adsgramTask"):
                st = fg(C_HDR_2) + f"ADG+{rew}" + RST
            else:
                st = fg(C_ACCENT) + f"{prog}/{target}+{rew}" + RST
            line = f"{fg(C_TEXT)}T{tid:<3}{title:<12}{RST}{bar} {st}"
            out.append(row(line))
            shown += 1
    if shown == 0:
        out.append(row(f"{fg(C_DIM)}— belum ada data task —{RST}"))
    out.append(sep())

    # PLOT
    out.append(row(f"{fg(C_HDR_2)}{BOLD}▌ PLOT DETAILS{RST}"))
    plots = _state["plots"]
    if plots:
        for p in plots:
            idx   = p.get("idx", 0)
            name  = (p.get("name") or "-")[:12]
            state = (p.get("state") or "empty").upper()
            payout= p.get("payout", 0)
            if state == "READY":
                st = fg(C_OK) + "READY" + RST
            elif state == "GROWING":
                st = fg(C_ACCENT) + "GROWING" + RST
            else:
                st = fg(C_DIM) + "EMPTY" + RST
            pay = f"{fg(C_OK)}+{payout}{RST}" if payout else f"{fg(C_DIM)}0{RST}"
            out.append(row(f"{fg(C_TEXT)}{idx}{RST}  {name:<13} {st:<16} {fg(C_SUB)}pay:{RST} {pay}"))
    else:
        out.append(row(f"{fg(C_DIM)}— belum ada data plot —{RST}"))
    out.append(sep())

    # REWARD
    out.append(row(f"{fg(C_ACCENT)}{BOLD}▌ REWARD{RST}"))
    out.append(row(f"{fg(C_SUB)}Coins total     :{RST} {fg(C_ACCENT)}{_state['coins']:,}{RST}"))
    out.append(row(f"{fg(C_SUB)}Session gained  :{RST} {fg(C_OK)}+{_state['session_gained']}{RST}"))
    out.append(row(f"{fg(C_SUB)}Ads selesai     :{RST} {fg(C_ACCENT)}{_state['ads_done']}{RST}"))
    out.append(row(f"{fg(C_SUB)}Today earned    :{RST} {fg(C_OK)}{_state['today_earned']}{RST}"))
    out.append(row(f"{fg(C_SUB)}USDT            :{RST} {fg(C_OK)}{_state['usdt']:.5f}{RST}"))
    out.append(sep())

    # FARM
    out.append(row(f"{fg(C_OK)}{BOLD}▌ FARM{RST}"))
    ready   = sum(1 for p in plots if p.get("state") == "ready")
    growing = sum(1 for p in plots if p.get("state") == "growing")
    empty   = sum(1 for p in plots if p.get("state") == "empty")
    xp_str  = f"{_state['xp']}/{_state['xp_max']}"
    out.append(row(f"{fg(C_SUB)}Level     :{RST} {fg(C_TEXT)}{_state['level']}  {fg(C_SUB)}XP:{RST} {fg(C_TEXT)}{xp_str}{RST}"))
    out.append(row(f"{fg(C_SUB)}Water     :{RST} {fg(C_HDR_1)}{_state['water']}/{_state['water_max']}{RST}"))
    out.append(row(f"{fg(C_SUB)}Ringkasan :{RST} {fg(C_OK)}R{ready}{RST} · {fg(C_ACCENT)}G{growing}{RST} · {fg(C_DIM)}E{empty}{RST}"))
    out.append(sep())

    # EVENT
    out.append(row(f"{fg(C_HDR_2)}{BOLD}▌ EVENT TERAKHIR{RST}"))
    logs = _state["logs"]
    for i in range(6):
        if i < len(logs):
            out.append(row(logs[i]))
        else:
            out.append(row_blank())
    out.append(sep())
    out.append(row(
        f"{gradient('AHD1905', C_HDR_1, C_HDR_2)} {fg(C_DIM)}•{RST} "
        f"{fg(C_SUB)}Souu Engine v7{RST} {fg(C_DIM)}•{RST} "
        f"{fg(C_HDR_1)}{now_str()}{RST}"
    ))
    out.append(bot())

    sys.stdout.write("".join(out))
    sys.stdout.flush()

# ═══════════════ CONFIG ═══════════════
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def isi_data():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(top())
    sys.stdout.write(row(gradient("SETUP AKUN FARM BUDDIES", C_HDR_1, C_HDR_2)))
    sys.stdout.write(row(fg(C_DIM) + "Copy dari devtools Telegram WebApp" + RST))
    sys.stdout.write(bot())
    print()
    init_data   = input(f"{fg(C_HDR_1)}▸ init_data/query_id :{RST} ").strip()
    device_id   = input(f"{fg(C_HDR_1)}▸ deviceId (dev_…)   :{RST} ").strip()
    fingerprint = input(f"{fg(C_HDR_1)}▸ x-farm-fp          :{RST} ").strip()

    data = {
        "init_data": init_data,
        "device_id": device_id,
        "fingerprint": fingerprint,
        "base_url": "https://farm-buddies-api.nhathaybip2000.workers.dev/api",
    }
    save_config(data)
    print(f"\n{fg(C_OK)}✔ Config disimpan ke {CONFIG_FILE}{RST}")
    time.sleep(1.6)

# ═══════════════ HTTP ═══════════════
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)",
    "Accept": "*/*",
    "Origin": "https://farm-buddies-4g5.pages.dev",
    "Referer": "https://farm-buddies-4g5.pages.dev/",
    "x-requested-with": "org.telegram.messenger.web",
})

def get_headers():
    return {
        "Content-Type": "application/json",
        "authorization": f"Bearer {CURRENT_TOKEN}",
        "x-farm-fp": FARM_FP,
    }

def parse_initdata(init_data_str):
    if not init_data_str:
        return None
    parts = urllib.parse.parse_qsl(init_data_str, keep_blank_values=True)
    fields = dict(parts)
    try:
        if "user" in fields:
            fields["user"] = json.loads(fields["user"])
    except: pass
    dc_pairs = [(k, v) for k, v in parts if k != "hash"]
    dc_pairs.sort(key=lambda x: x[0])
    dc_str = "\n".join(f"{k}={v}" for k, v in dc_pairs)
    return {
        "fields": fields,
        "data_check_string": dc_str,
        "signature": fields.get("signature", ""),
        "hash": fields.get("hash", ""),
        "auth_date": fields.get("auth_date", ""),
        "query_id": fields.get("query_id", ""),
        "user_id": str((fields.get("user") or {}).get("id", "")),
    }

def authenticate():
    global CURRENT_TOKEN
    try:
        _state["aksi"] = "auth request"
        render_dashboard()
        res = requests.post(
            f"{BASE_URL}/auth/telegram",
            headers={"Content-Type": "application/json"},
            json={"initData": INIT_DATA, "deviceId": DEVICE_ID, "fingerprint": FARM_FP},
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                CURRENT_TOKEN = data.get("token")
                push_log("bearer token didapat", "ok")
                return True
        push_log(f"auth gagal. status: {res.status_code}", "er")
    except Exception as e:
        push_log(f"auth error: {e}", "er")
    return False

def make_request(method, endpoint, json_payload=None):
    global CURRENT_TOKEN
    if not CURRENT_TOKEN and not authenticate():
        return None
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(3):
        try:
            if method.lower() == "get":
                res = session.get(url, headers=get_headers(), timeout=15)
            else:
                payload = json_payload if json_payload is not None else {}
                res = session.post(url, headers=get_headers(), json=payload, timeout=15)

            if res.status_code == 401:
                push_log("token expired → refresh", "wr")
                if authenticate():
                    continue
                else:
                    return None

            if res.status_code >= 500 and attempt < 2:
                time.sleep(2 * (2 ** attempt))
                continue

            return res
        except Exception as e:
            push_log(f"req err {endpoint}: {str(e)[:40]}", "er")
            if attempt < 2:
                time.sleep(2 * (2 ** attempt))
            else:
                return None
    return None

# ═══════════════ FETCH STATE ═══════════════
def fetch_state():
    res = make_request("get", "/user/bootstrap")
    if res and res.status_code == 200:
        try:
            data = res.json()
        except:
            return None
        if data.get("ok"):
            profile = data.get("profile", {})
            farm    = data.get("farm", {})
            streak  = data.get("streak", {})
            ads     = data.get("ads", {})
            cap     = ads.get("cap", {})

            _state["user"]         = profile.get("username", "Unknown")
            _state["coins"]        = int(profile.get("coins", 0))
            _state["usdt"]         = float(profile.get("usdt", 0))
            _state["level"]        = profile.get("level", 1)
            _state["xp"]           = profile.get("xp", 0)
            _state["xp_max"]       = profile.get("xpMax", 3200)
            _state["ads_done"]     = profile.get("totalAds", 0)
            _state["today_earned"] = profile.get("todayEarned", 0)
            _state["farm_level"]   = profile.get("farmLevel", 1)
            _state["water"]        = farm.get("water", 0)
            _state["water_max"]    = farm.get("waterMax", 10)
            _state["plots"]        = farm.get("plots", [])
            _state["crops"]        = farm.get("crops", [])
            _state["tasks"]        = data.get("tasks", [])
            _state["ads_used"]     = cap.get("used", 0)
            _state["ads_max"]      = cap.get("max", 200)
            _state["streak_day"]   = streak.get("day", 0)
            _state["streak_claimed"] = streak.get("claimedToday", False)
            return _state
    return None

# ═══════════════ HELPERS ═══════════════
def get_best_affordable(crops, coins):
    unlocked = [c for c in crops if not c.get("locked", True)]
    affordable = [c for c in unlocked if c.get("plantCost", 0) <= coins]
    if affordable:
        best = max(affordable, key=lambda x: x.get("payout", 0))
        return best.get("id", "wheat"), best.get("plantCost", 0)
    if unlocked:
        cheapest = min(unlocked, key=lambda x: x.get("plantCost", 999999))
        return cheapest.get("id", "wheat"), cheapest.get("plantCost", 999999)
    return "wheat", 30

def get_cheapest_crop(crops):
    unlocked = [c for c in crops if not c.get("locked", True)]
    if not unlocked:
        return 30, "wheat"
    c = min(unlocked, key=lambda x: x.get("plantCost", 999999))
    return c.get("plantCost", 30), c.get("id", "wheat")

# ═══════════════ ACTIONS ═══════════════

def action_harvest(plot_idx):
    _state["aksi"] = f"harvest plot {plot_idx}"
    render_dashboard()
    r = make_request("post", "/ads/harvest/session", {"idx": plot_idx})
    if not r: return False
    if r.status_code == 409: return "COOLDOWN"
    if r.status_code != 200: return False
    try: d = r.json()
    except: return False
    if not d.get("ok"): return False

    sid = d.get("sessionId"); mw = d.get("minWatchSec", 8)
    push_log(f"harvest plot [{plot_idx}] — ad {mw}s", "in"); render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "provider": "adsgram", "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", "/ads/harvest/complete", payload)
    if r2 and r2.status_code == 200 and r2.json().get("ok"):
        push_log(f"panen plot [{plot_idx}] sukses", "ok"); return True
    return False

def action_water(plot_idx):
    _state["aksi"] = f"water plot {plot_idx}"
    render_dashboard()
    r = make_request("post", "/farm/water", {"idx": plot_idx})
    if r and r.status_code == 200 and r.json().get("ok"):
        push_log(f"siram plot [{plot_idx}]", "w"); return True
    return False

def action_plant(plot_idx, crop_id):
    _state["aksi"] = f"plant {crop_id}@{plot_idx}"
    render_dashboard()
    r = make_request("post", "/farm/plant", {"idx": plot_idx, "crop": crop_id})
    if r and r.status_code == 200 and r.json().get("ok"):
        push_log(f"{crop_id.upper()} ditanam di plot [{plot_idx}]", "s"); return True
    if r and r.status_code == 400:
        body = r.text.lower()
        if any(k in body for k in ["coin", "insufficient", "balance", "funds"]):
            push_log("coins tidak cukup", "wr"); return "NO_COINS"
    return False

def action_refill_water():
    _state["aksi"] = "refill air"
    render_dashboard()
    r = make_request("post", "/ads/farm/session", {"ref": "water"})
    if not r: return False
    if r.status_code == 409: return "COOLDOWN"
    if r.status_code != 200: return False
    try: d = r.json()
    except: return False
    if not d.get("ok"): return False

    sid = d.get("sessionId"); mw = d.get("minWatchSec", 6)
    push_log(f"refill air — ad {mw}s", "in"); render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "ref": "water", "provider": "adsgram", "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", "/ads/farm/complete", payload)
    if r2 and r2.status_code == 200 and r2.json().get("ok"):
        push_log("air diisi penuh", "ok"); return True
    return False

def action_watch_ad_task(task_id, title, min_watch=8):
    _state["aksi"] = f"watch ad {title[:12]}"
    render_dashboard()
    r = make_request("post", f"/ads/task/{task_id}/session", {"slotIndex": -1})
    if not r: return False
    if r.status_code == 409: return "COOLDOWN"
    if r.status_code != 200: return False
    try: d = r.json()
    except: return False
    if not d.get("ok"): return False

    sid  = d.get("sessionId"); mw = d.get("minWatchSec", min_watch)
    slot = d.get("slotIndex", 0); prov = d.get("provider", "adsgram")
    push_log(f"nonton [{title}] {mw}s", "in"); render_dashboard()
    time.sleep(mw + 2)

    payload = {"sessionId": sid, "slotIndex": slot, "provider": prov,
               "clicked": True, "adsgramClicked": False}
    r2 = make_request("post", f"/ads/task/{task_id}/complete", payload)
    if r2 and r2.status_code == 200:
        try:
            d2 = r2.json()
            if d2.get("ok"):
                gain = d2.get("reward") or 0
                push_log(f"reward [{title}] +{gain}", "ok")
                return True
        except: pass
    return False

def action_adsgram_task(task_id, title, block_id):
    """Adsgram Task (id 4) — POST /ads/task/{id}/reward."""
    _state["aksi"] = f"adsgram {title[:12]}"
    render_dashboard()

    # opsional: fire tracking /adv
    try:
        initp = parse_initdata(INIT_DATA)
        if initp:
            block_num = re.sub(r"^task-", "", str(block_id))
            params = {
                "envType": "telegram",
                "blockId": block_num,
                "platform": "Linux aarch64",
                "language": "id",
                "top_domain": "farm-buddies-4g5.pages.dev",
                "signature": initp["signature"],
                "data_check_string": base64.b64encode(
                    initp["data_check_string"].encode()).decode(),
                "sdk_version": "2.2.5",
                "tg_id": initp["user_id"],
                "tg_platform": "android",
                "tma_version": "9.6",
            }
            adv = requests.get("https://api.adsgram.ai/adv", params=params,
                               headers={"Origin": "https://farm-buddies-4g5.pages.dev",
                                        "Referer": "https://farm-buddies-4g5.pages.dev/",
                                        "User-Agent": session.headers["User-Agent"],
                                        "Accept": "*/*"}, timeout=12)
            if adv.status_code == 200:
                banners = adv.json().get("banners", [])
                if banners:
                    trackings = {t["name"]: t["value"] for t in banners[0]
                                 .get("banner", {}).get("trackings", [])}
                    for k in ("render", "show"):
                        if k in trackings:
                            try: requests.get(trackings[k], timeout=6)
                            except: pass
                    push_log(f"[ADG] banner fire {len(trackings)} tracks", "in")
                    render_dashboard()
                    time.sleep(9)
                    if trackings.get("reward"):
                        try: requests.get(trackings["reward"], timeout=6)
                        except: pass
    except Exception as e:
        push_log(f"[ADG] adv err: {str(e)[:40]}", "wr")

    r = make_request("post", f"/ads/task/{task_id}/reward", {})
    if not r:
        push_log(f"[ADG] no respon", "er"); return False
    if r.status_code == 409:
        push_log(f"[ADG] cooldown", "wr"); return "COOLDOWN"
    if r.status_code != 200:
        push_log(f"[ADG] HTTP {r.status_code}", "er"); return False
    try: d = r.json()
    except: return False
    if not d.get("ok"):
        push_log(f"[ADG] {d.get('message','gagal')}", "er"); return False

    reward = d.get("reward", 0)
    if d.get("already"):
        push_log(f"[ADG] sudah diklaim", "wr"); return "COOLDOWN"

    _state["session_gained"] += reward
    push_log(f"[ADG] ✅ +{reward} coins | used {d.get('usedToday','?')}/{d.get('total','?')}", "ok")
    prof = d.get("profile", {})
    if prof:
        _state["coins"] = prof.get("coins", _state["coins"])
        _state["today_earned"] = prof.get("todayEarned", _state["today_earned"])
        _state["ads_done"] = prof.get("totalAds", _state["ads_done"])
    return True

def action_link_task(task_id, title, url, dwell=15, verify=15):
    _state["aksi"] = f"link {title[:12]}"
    render_dashboard()

    # 1. start
    r = make_request("post", f"/tasks/{task_id}/start", {})
    start_reward = 0
    if r and r.status_code == 200:
        try:
            d = r.json()
            if d.get("ok"):
                start_reward = d.get("reward", 0)
                if start_reward:
                    _state["session_gained"] += start_reward
                    push_log(f"[LINK T{task_id}] start +{start_reward}", "ok")
        except: pass
    elif r and r.status_code == 409:
        push_log(f"[LINK T{task_id}] cooldown", "wr"); return "COOLDOWN"

    # 2. buka URL
    if url:
        try:
            requests.get(url, headers={
                "User-Agent": session.headers["User-Agent"],
                "Referer": "https://farm-buddies-4g5.pages.dev/",
            }, timeout=20, allow_redirects=True)
            push_log(f"[LINK T{task_id}] URL dibuka", "in")
            render_dashboard()
        except Exception as e:
            push_log(f"[LINK] err: {str(e)[:40]}", "wr")

    time.sleep(dwell + 3)

    # 3. claim
    r2 = make_request("post", f"/tasks/{task_id}/claim", {})
    if r2 and r2.status_code == 200:
        try:
            d2 = r2.json()
            if d2.get("ok"):
                gain = d2.get("reward", 0) or start_reward
                _state["session_gained"] += gain
                _state["claimed_ids"].add(task_id)
                push_log(f"[LINK T{task_id}] ✅ +{gain}", "ok")
                return True
            msg = d2.get("message", "belum valid")
            push_log(f"[LINK T{task_id}] {msg}", "wr")
            _state["claimed_ids"].add(task_id)
        except: pass
    elif r2 and r2.status_code == 409:
        push_log(f"[LINK T{task_id}] cooldown", "wr")
        _state["claimed_ids"].add(task_id)
        return "COOLDOWN"
    return False

def action_claim_task(task_id, title, expected_reward=0):
    """Task yang progress >= target — cuma butuh claim."""
    _state["aksi"] = f"claim T{task_id}"
    render_dashboard()
    for ep in (f"/tasks/{task_id}/claim", f"/tasks/{task_id}/complete"):
        r = make_request("post", ep, {})
        if r and r.status_code in (404, 405):
            continue
        if not r:
            continue
        if r.status_code == 200:
            try:
                d = r.json()
            except:
                continue
            if d.get("ok"):
                gain = (d.get("reward") or d.get("coins") or
                        d.get("claimedCoins") or expected_reward or 0)
                prof = d.get("profile") or {}
                bal_now = prof.get("coins", _state["coins"])
                _state["claimed_ids"].add(task_id)
                _state["session_gained"] += gain
                if gain:
                    push_log(f"[CLAIM T{task_id}] ✅ {title} +{gain} | bal {bal_now}", "ok")
                else:
                    push_log(f"[CLAIM T{task_id}] ✅ {title} | bal {bal_now}", "ok")
                return True
            else:
                msg = d.get("message", "")
                _state["claimed_ids"].add(task_id)
                if any(k in msg.lower() for k in ["already", "cooldown", "claimed"]):
                    push_log(f"[CLAIM T{task_id}] sudah diklaim", "wr")
                else:
                    push_log(f"[CLAIM T{task_id}] {msg or 'skip'}", "wr")
                return "COOLDOWN"
        if r.status_code == 409:
            _state["claimed_ids"].add(task_id)
            push_log(f"[CLAIM T{task_id}] cooldown", "wr")
            return "COOLDOWN"
    _state["claimed_ids"].add(task_id)
    return False

def action_streak():
    _state["aksi"] = "streak claim"
    render_dashboard()
    r = make_request("post", "/user/streak/claim", {})
    if not r: return False
    if r.status_code == 200:
        try: d = r.json()
        except: return False
        if d.get("ok"):
            gained = d.get("reward", 0)
            _state["session_gained"] += gained
            push_log(f"[STREAK] ✅ +{gained} coins", "ok")
            return True
        code = d.get("code", "")
        if code == "STREAK_BIO_REQUIRED":
            push_log("[STREAK] butuh referral link di bio Telegram", "wr")
            return "BIO"
        msg = d.get("message", "")
        if "already" in msg.lower() or "claimed" in msg.lower():
            push_log("[STREAK] sudah diklaim hari ini", "wr")
            return "DONE"
        push_log(f"[STREAK] {msg or code}", "wr")
        return False
    if r.status_code == 409:
        push_log("[STREAK] sudah diklaim", "wr"); return "DONE"
    return False

def action_shortlink(provider_id, provider_name, reward_coins):
    _state["aksi"] = f"short {provider_id[:10]}"
    render_dashboard()

    r = make_request("post", f"/shortlinks/{provider_id}/issue", {})
    short_url = None
    if r and r.status_code == 200:
        try:
            d = r.json()
            if d.get("ok"):
                short_url = d.get("shortUrl") or d.get("url")
                push_log(f"[SHORT] {provider_name}: issued", "in")
        except: pass
    if r and r.status_code == 409:
        push_log(f"[SHORT] {provider_name}: cooldown", "wr"); return "COOLDOWN"
    if not short_url:
        return False

    try:
        requests.get(short_url, headers={
            "User-Agent": session.headers["User-Agent"],
            "Referer": "https://farm-buddies-4g5.pages.dev/",
        }, timeout=20, allow_redirects=True)
        push_log(f"[SHORT] {provider_name}: dibuka", "in")
        render_dashboard()
    except Exception as e:
        push_log(f"[SHORT] err: {str(e)[:40]}", "wr")

    time.sleep(8)

    r2 = make_request("post", f"/shortlinks/{provider_id}/claim", {})
    if r2 and r2.status_code == 200:
        try:
            d2 = r2.json()
            if d2.get("ok"):
                _state["session_gained"] += reward_coins
                push_log(f"[SHORT] {provider_name}: ✅ +{reward_coins}", "ok")
                return True
        except: pass
    return False

# ═══════════════ SMART SCANNER ═══════════════
def run_smart_scanner(s):
    plots = s["plots"]
    coins = s["coins"]
    water = s["water"]
    tasks = s["tasks"]
    crops = s.get("crops") or [
        {"id": "wheat", "payout": 30, "plantCost": 30, "locked": False},
        {"id": "carrot", "payout": 60, "plantCost": 60, "locked": False},
        {"id": "corn", "payout": 90, "plantCost": 90, "locked": False},
    ]

    # ── 0. Claim task yang beneran ada reward ──
    for t in tasks:
        if t.get("state") != "open": continue
        tid = t.get("id")
        if tid in _state["claimed_ids"]: continue
        rew = t.get("reward", 0)
        if rew <= 0: continue
        if t.get("type") in ("link", "telegram", "offerwall"): continue
        if t.get("adsgramTask"): continue  # handle di step 5
        prog = t.get("progress", 0); tgt = t.get("target", 1)
        if prog >= tgt and tgt > 0:
            if action_claim_task(tid, t.get("title", "?"), rew):
                return True

    # ── 1. HARVEST ready ──
    for p in plots:
        if p.get("state") == "ready":
            idx = p.get("idx"); name = p.get("name", "crop"); payout = p.get("payout", 0)
            push_log(f"plot [{idx}] {name} ready (+{payout})", "f"); render_dashboard()
            res = action_harvest(idx)
            if res is True: return True
            if res == "COOLDOWN": time.sleep(1); continue

    # ── 2. WATER ──
    if water > 0:
        for p in plots:
            if p.get("state") in ["growing", "ready"] and not p.get("watered", False):
                if action_water(p.get("idx")): return True

    # ── 3. PLANT ──
    empty_plots = [p for p in plots if p.get("state") == "empty" and not p.get("locked", False)]
    cheapest_cost, _ = get_cheapest_crop(crops)
    if empty_plots and coins >= cheapest_cost:
        crop_id, cost = get_best_affordable(crops, coins)
        idx = empty_plots[0].get("idx")
        push_log(f"coba tanam {crop_id.upper()} (cost={cost}) @{idx}", "s"); render_dashboard()
        res = action_plant(idx, crop_id)
        if res is True: return True

    # ── 4. STREAK ──
    if not s.get("streak_claimed"):
        res = action_streak()
        if res is True: return True
        if res in ("BIO", "DONE"):
            _state["streak_claimed"] = True

    # ── 5. ADSGRAM TASK ──
    for t in tasks:
        if not t.get("adsgramTask"): continue
        if t.get("state") != "open": continue
        tid = t.get("id"); block = t.get("blockId"); title = t.get("title", "Adsgram Task")
        if not block: continue
        nxt = t.get("nextAdAt") or 0
        if nxt and nxt > int(time.time() * 1000):
            continue
        res = action_adsgram_task(tid, title, block)
        if res is True: return True

    # ── 6. LINK TASKS ──
    for t in tasks:
        if t.get("type") != "link": continue
        if t.get("state") != "open": continue
        if not t.get("url"): continue
        tid = t.get("id")
        if tid in _state["claimed_ids"]: continue
        dwell = t.get("dwellSec", 15); verify = t.get("verifySec", 15)
        res = action_link_task(tid, t.get("title", "Link"), t.get("url"), dwell, verify)
        if res is True: return True
        if res == "COOLDOWN": continue

    # ── 7. ADS TASKS biasa ──
    ad_tasks = [t for t in tasks if t.get("type") == "ad"
                and not t.get("adsgramTask")
                and t.get("state") == "open"]
    ad_tasks.sort(key=lambda x: x.get("reward", 0), reverse=True)
    for t in ad_tasks:
        tid = t.get("id"); title = t.get("title", "Ad")
        target = t.get("target", 10); progress = t.get("progress", 0)
        if progress >= target: continue
        res = action_watch_ad_task(tid, title)
        if res is True: return True
        if res == "COOLDOWN": time.sleep(1); continue

    # ── 8. SHORTLINKS ──
    sl_res = make_request("get", "/shortlinks")
    if sl_res and sl_res.status_code == 200:
        try:
            sl_data = sl_res.json()
            summaries = sl_data.get("shortlinks", {}).get("summaries", {})
            for pid, info in summaries.items():
                if not info.get("enabled"): continue
                if not info.get("canIssue"): continue
                if info.get("remainingCount", 0) <= 0: continue
                if info.get("status") == "claimed": continue
                res = action_shortlink(pid, info.get("providerName", pid), info.get("rewardCoins", 0))
                if res is True: return True
        except: pass

    # ── 9. REFILL AIR ──
    if water == 0:
        push_log("air habis → refill", "wr"); render_dashboard()
        res = action_refill_water()
        if res is True: return True

    return False

# ═══════════════ MAIN LOOP ═══════════════
def run_bot():
    global BASE_URL, FARM_FP, DEVICE_ID, INIT_DATA
    BASE_URL  = CONFIG.get("base_url", "https://farm-buddies-api.nhathaybip2000.workers.dev/api")
    FARM_FP   = CONFIG.get("fingerprint", "")
    DEVICE_ID = CONFIG.get("device_id", "")
    INIT_DATA = CONFIG.get("init_data", "")

    _state["start"] = time.time()
    _state["status"] = "boot"
    _state["claimed_ids"].clear()

    if not authenticate():
        push_log("auth awal gagal!", "er"); render_dashboard()
        time.sleep(3); return

    s = fetch_state()
    if s:
        push_log(f"login sebagai {_state['user']}", "ok"); render_dashboard()

    # pre-check force-join
    push_log("[BOOT] cek force-join...", "in"); render_dashboard()
    fj = make_request("get", "/user/force-join")
    if fj and fj.status_code == 200:
        try:
            d = fj.json()
            req = d.get("required", [])
            if req:
                push_log(f"[JOIN] wajib join: {len(req)} channel", "wr")
            else:
                push_log("[JOIN] semua ok", "ok")
        except: pass

    push_log("bot v7 FULL AUTO — siap tempur", "g")
    render_dashboard()

    idle_count = 0
    while True:
        try:
            s = fetch_state()
            if not s:
                push_log("gagal sync, retry 10s", "wr"); render_dashboard()
                time.sleep(10); continue

            _state["status"] = "farming"
            render_dashboard()
            acted = run_smart_scanner(s)

            if acted:
                idle_count = 0
                time.sleep(2)
            else:
                idle_count += 1
                if idle_count >= 3:
                    push_log("semua cooldown → idle 5 menit", "wr")
                    _state["status"] = "idle"
                    _state["aksi"] = "waiting cooldown"
                    render_dashboard()
                    time.sleep(300)
                    idle_count = 0
                else:
                    push_log(f"idle, tunggu 20s ({idle_count}/3)", "wr")
                    _state["aksi"] = "idle"
                    render_dashboard()
                    time.sleep(20)

        except KeyboardInterrupt:
            push_log("bot dimatiin manual", "wr"); render_dashboard()
            print(f"\n{fg(C_WARN)}Loop dihentikan. Balik ke menu...{RST}")
            time.sleep(1.5); return
        except Exception as e:
            push_log(f"loop error: {str(e)[:50]}", "er"); render_dashboard()
            time.sleep(30)

# ═══════════════ MENU ═══════════════
def banner_menu():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(top())
    sys.stdout.write(row(gradient("FARMBUDDIES • SOUU ENGINE v7", C_HDR_1, C_HDR_2)))
    sys.stdout.write(row(fg(C_DIM) + "base by AHD1905 • fixed by Kyriel v4" + RST))
    sys.stdout.write(bot())
    print()

def main():
    while True:
        banner_menu()
        print(f"  {fg(C_HDR_1)}[1]{RST} {fg(C_TEXT)}Mainkan Wak (FULL AUTO){RST}")
        print(f"  {fg(C_HDR_1)}[2]{RST} {fg(C_TEXT)}Isi init_data{RST}")
        print(f"  {fg(C_HDR_1)}[3]{RST} {fg(C_TEXT)}Hapus Data{RST}")
        print(f"  {fg(C_HDR_1)}[0]{RST} {fg(C_TEXT)}Pulang Wak Turu{RST}\n")
        pilih = input(f"{fg(C_HDR_2)}▸ Pilih menu :{RST} ").strip()

        if pilih == "1":
            if os.path.exists(CONFIG_FILE):
                global CONFIG
                CONFIG = load_config()
                run_bot()
            else:
                print(f"\n{fg(C_ERR)}Data belum diisi! pilih menu 2 dulu.{RST}"); time.sleep(2)
        elif pilih == "2":
            isi_data()
        elif pilih == "3":
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                print(f"\n{fg(C_OK)}config.json dihapus!{RST}")
            else:
                print(f"\n{fg(C_WARN)}tidak ada config.json.{RST}")
            time.sleep(2)
        elif pilih == "0":
            print(f"\n{fg(C_HDR_1)}Selamat istirahat wak!{RST}\n"); sys.exit(0)
        else:
            print(f"\n{fg(C_ERR)}Pilihan tidak valid!{RST}"); time.sleep(1)

if __name__ == "__main__":
    main()
