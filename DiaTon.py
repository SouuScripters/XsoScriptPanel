#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  DiaTON Auto Farmer — Single Account v1.3
  - Provider di-shuffle biar gantian tiap round
  - Error apapun → skip provider itu, lanjut yg lain
  - Semua limit → stop otomatis
  - Adsgram auto-skip (webhook)
  - Menu slim: Start / Config / Exit
═══════════════════════════════════════════════════════════════
  INSTALL:  pip install requests
  RUN:      python diaton_single.py
"""

import os, sys, json, time, signal, random, re
from datetime import datetime

try:
    import requests
except ImportError:
    print("Install dulu: pip install requests"); sys.exit(1)

# ═══════════════════════════════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════════════════════════════
RST="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
RED="\033[38;5;196m"; GRN="\033[38;5;46m"; YEL="\033[38;5;226m"
CYN="\033[38;5;51m";  MAG="\033[38;5;201m"; ORG="\033[38;5;208m"
WHT="\033[38;5;15m";  GRY="\033[38;5;240m"; VIO="\033[38;5;141m"

def vlen(s): return len(re.sub(r'\033\[[0-9;]*m','',s))
def pad_to(s,w): return s+" "*max(0,w-vlen(s))
def fmt_dur(s):
    s=max(0,int(s)); return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
def now_str(): return datetime.now().strftime("%H:%M:%S")
def clear_screen(): os.system('cls' if os.name=='nt' else 'clear')

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
BASE_HOST = "https://diaton.biz"
UA = ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36 "
      "Telegram-Android/12.9.2 (Samsung SM-A556E; Android 16; SDK 36; HIGH)")

# Provider via API ad-view (bisa di-farm)
PROVIDERS = ["monetag","adexium","onclicka","towerads","tads_fullscreen","tads_static"]

# Webhook-based → skip dari awal
SKIP_PROVIDERS = {"adsgram"}

AD_DELAY_MIN = 2.5
AD_DELAY_MAX = 5.0
TASK_BETWEEN = 4
COOLDOWN     = 3600

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "diaton_config.json")
LOG_FILE    = os.path.join(SCRIPT_DIR, "diaton.log")

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════
STATE = {
    'phase':'idle', 'cycle':0,
    'name':'-', 'username':'-', 'tg_id':0,
    'balance_dton':0, 'balance_gram':0.0, 'earned_total':0,
    'ads_done':0, 'ads_failed':0,
    'ad_current':'-', 'ad_left':0,
    'tasks_done':0, 'tasks_failed':0,
    'cooldown_end':0, 'runtime_start': time.time(),
    'logs':[], 'menu_hint':'idle',
}

TAG_MAP = {
    'OK':GRN+"● OK    "+RST, 'ERR':RED+"● ERR   "+RST, 'WARN':YEL+"● WARN  "+RST,
    'INFO':GRY+"● INFO  "+RST, 'AD':MAG+"◉ AD    "+RST, 'VIEW':CYN+"◉ VIEW  "+RST,
    'WAIT':ORG+"◉ WAIT  "+RST, 'TASK':VIO+"◉ TASK  "+RST,
    'TG':MAG+"◉ TG    "+RST, 'MENU':VIO+"◉ MENU  "+RST, 'RETRY':ORG+"◉ RETRY "+RST,
    'AUTH':GRN+"● AUTH  "+RST,
}

def slog(msg, level='INFO'):
    tag = TAG_MAP.get(level.upper(), TAG_MAP['INFO'])
    STATE['logs'].append(f"{GRY}[{now_str()}] {RST}{tag} {WHT}{msg}{RST}")
    if len(STATE['logs'])>8: STATE['logs'].pop(0)
    try:
        with open(LOG_FILE,'a',encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][{level}] {msg}\n")
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════
def line(c,W=62): return CYN+"║"+RST+pad_to(" "+c,W)+CYN+"║"+RST

def render():
    W=62; bd=CYN
    top=bd+"╔"+"═"*W+"╗"+RST
    mid=bd+"╠"+"═"*W+"╣"+RST
    bot=bd+"╚"+"═"*W+"╝"+RST

    print("\n"+top)
    print(line(BOLD+WHT+"DIATON AUTO FARMER"+RST))
    print(line(DIM+"──────── SouuEngine v1.3 ────────"+RST))
    print(mid)

    ph=STATE['phase'].upper(); phc=GRY
    if STATE['phase']=='running': phc=GRN
    elif STATE['phase']=='cooldown': phc=ORG

    print(line(VIO+"RUN"+RST))
    print(line(f"├─ Phase    : {phc}{ph}{RST}"))
    print(line(f"└─ Cycle    : {YEL}{STATE['cycle']}{RST}"))
    print(mid)

    print(line(VIO+"ACCOUNT"+RST))
    nm = f"{WHT}{STATE['name']}{RST}"+(f" {DIM}@{STATE['username']}{RST}" if STATE['username']!='-' else "")
    print(line(f"├─ Name     : {nm}"))
    print(line(f"├─ TG ID    : {CYN}{STATE['tg_id']}{RST}"))
    print(line(f"├─ Balance  : {GRN}{STATE['balance_dton']} DTON{RST} {DIM}|{RST} {GRN}{STATE['balance_gram']:.4f} GRAM{RST}"))
    print(line(f"└─ Earned   : {YEL}+{STATE['earned_total']} DTON{RST}"))
    print(mid)

    print(line(VIO+"ADS"+RST))
    print(line(f"├─ Current  : {YEL}{STATE['ad_current']}{RST}"))
    print(line(f"├─ Left     : {CYN}{STATE['ad_left']}{RST}"))
    print(line(f"├─ Done     : {GRN}{STATE['ads_done']}{RST}"))
    print(line(f"└─ Failed   : {RED}{STATE['ads_failed']}{RST}"))
    print(mid)

    print(line(VIO+"TASKS"+RST))
    print(line(f"├─ Done     : {GRN}{STATE['tasks_done']}{RST}"))
    print(line(f"└─ Failed   : {RED}{STATE['tasks_failed']}{RST}"))
    print(mid)

    run = int(time.time()-STATE['runtime_start'])
    print(line(VIO+"SYSTEM"+RST))
    print(line(f"├─ Runtime  : {CYN}{fmt_dur(run)}{RST}"))
    if STATE['phase']=='cooldown' and STATE['cooldown_end']>time.time():
        print(line(f"└─ Cooldown : {ORG}{fmt_dur(STATE['cooldown_end']-time.time())}{RST}"))
    else:
        print(line(f"└─ Cooldown : {DIM}-{RST}"))
    print(mid)

    if not STATE['logs']:
        print(line(DIM+"─ no activity yet ─"+RST))
    else:
        for l in STATE['logs']: print(line(l))
    print(bot)
    print(f"\n   {GRN}SOUU ENGINE{RST} {DIM}•{RST} {CYN}{now_str()}{RST}   {DIM}{STATE['menu_hint']}{RST}\n")

def clear_render(): clear_screen(); render()

# ═══════════════════════════════════════════════════════════════
#  STORAGE
# ═══════════════════════════════════════════════════════════════
def load_cfg():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE,'r',encoding='utf-8') as f: return json.load(f)
    except Exception: return {}

def save_cfg(c):
    try:
        with open(CONFIG_FILE,'w',encoding='utf-8') as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
        os.chmod(CONFIG_FILE, 0o600)
    except Exception as e: slog(f"save error: {e}", 'ERR')

def get_initdata(): return load_cfg().get('initData','')
def set_initdata(s):
    c=load_cfg(); c['initData']=s; c['set_at']=datetime.now().isoformat(); save_cfg(c)

# ═══════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception: pass

def _headers(init_data):
    return {
        "Authorization": f"Bearer {init_data}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": BASE_HOST, "Referer": BASE_HOST+"/",
        "X-Requested-With": "org.telegram.messenger.web",
        "User-Agent": UA,
        "Accept-Language": "id,id-ID;q=0.9,en-US;q=0.8,en;q=0.7",
    }

def _req(method, path, init_data, payload=None, timeout=30):
    url = BASE_HOST + path
    for attempt in range(3):
        try:
            if method=="GET":
                r=requests.get(url, headers=_headers(init_data), timeout=timeout, verify=False)
            else:
                r=requests.post(url, json=payload or {}, headers=_headers(init_data),
                                timeout=timeout, verify=False)
            try: return r.json()
            except Exception: return {"_raw": r.text, "_status": r.status_code}
        except requests.RequestException as e:
            if attempt==2:
                slog(f"HTTP-ERR {path}: {e}", 'ERR'); return None
            time.sleep(1.5*(attempt+1))

def api_me(id_): return _req("GET","/api/user/me",id_)
def api_earn_info(id_): return _req("GET","/api/earn/info",id_)
def api_tasks(id_): return _req("GET","/api/tasks/available",id_)
def api_ad_view(id_,prov): return _req("POST","/api/earn/ad-view",id_,{"provider":prov})
def api_task_done(id_,tid): return _req("POST",f"/api/tasks/complete/{tid}",id_,{})

# ═══════════════════════════════════════════════════════════════
#  SPINNER
# ═══════════════════════════════════════════════════════════════
def tmr(sec,label=""):
    spin=['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
    end=time.time()+sec; i=0
    while (rem:=end-time.time())>0:
        sys.stdout.write(f"\r   {ORG}{spin[i%len(spin)]}{RST} {fmt_dur(rem)} {DIM}{label}{RST} ")
        sys.stdout.flush(); i+=1; time.sleep(0.08)
    sys.stdout.write("\r"+" "*60+"\r")

# ═══════════════════════════════════════════════════════════════
#  BOOTSTRAP
# ═══════════════════════════════════════════════════════════════
def bootstrap(init_data):
    me = api_me(init_data)
    if not me or 'id' not in me: return None
    return {
        'tg_id': int(me['id']),
        'name': me.get('first_name','?'),
        'username': me.get('username','') or '-',
        'balance_dton': int(me.get('balance_dton',0)),
        'balance_gram': float(me.get('ad_balance_gram',0.0)),
    }

# ═══════════════════════════════════════════════════════════════
#  ADS ENGINE — shuffle + skip error
# ═══════════════════════════════════════════════════════════════
def run_ads(init_data, info):
    done=0; fail=0
    STATE['name']=info['name']; STATE['username']=info['username']
    STATE['tg_id']=info['tg_id']
    STATE['balance_dton']=info['balance_dton']
    STATE['balance_gram']=info['balance_gram']

    ei = api_earn_info(init_data) or {}
    ads_left_raw = ei.get('ads_left',{}) or {}
    reward = int(ei.get('config',{}).get('ad_reward',5))

    # ambil left, exclude skip permanen
    ads_left = {p:int(ads_left_raw.get(p,0)) for p in PROVIDERS
                if p in ads_left_raw and p not in SKIP_PROVIDERS}
    total_left = sum(ads_left.values())
    slog(f"{info['name']} — {total_left} ads pending (reward {reward}/ad)", 'AUTH')
    clear_render()

    skipped = [p for p in ads_left_raw if p in SKIP_PROVIDERS]
    if skipped:
        slog(f"skip webhook-based: {', '.join(skipped)}", 'INFO')
        clear_render()

    # kalo semua kosong dari awal → stop
    if total_left == 0:
        slog("semua provider udah limit — stop farming", 'OK')
        clear_render()
        STATE['ad_current']='-'; STATE['ad_left']=0
        return {'ads_done':0,'ads_failed':0,'all_limit':True}

    # pool provider yang masih ada sisa
    pool = [p for p,left in ads_left.items() if left > 0]
    round_num = 0

    # loop sampe pool kosong (semua limit / stuck)
    while pool:
        round_num += 1
        random.shuffle(pool)

        still_has_left = []
        anyone_progress = False

        for prov in pool:
            left = ads_left.get(prov, 0)
            if left <= 0:
                continue

            STATE['ad_current']=prov; STATE['ad_left']=left
            clear_render()
            r = api_ad_view(init_data, prov)

            if r and r.get('status')=='success':
                got=int(r.get('reward',reward))
                left=int(r.get('left',left-1))
                ads_left[prov]=left
                done+=1
                STATE['ads_done']=done
                STATE['earned_total']+=got
                STATE['ad_left']=left
                slog(f"{prov}: +{got} DTON (sisa {left})", 'AD')
                clear_render()
                anyone_progress=True
                if left > 0:
                    still_has_left.append(prov)
            else:
                err = ((r or {}).get('message')
                       or (r or {}).get('detail')
                       or (r or {}).get('error')
                       or str(r))
                err_low = str(err).lower()

                # webhook / invalid → skip permanen
                if 'invalid ad provider' in err_low or 'webhook' in err_low:
                    SKIP_PROVIDERS.add(prov)
                    slog(f"{prov} → webhook-based, skip permanen", 'WARN')
                    clear_render()
                    continue

                # cooldown / rate limit → skip provider ini, coba lagi next round
                if any(k in err_low for k in ('cooldown','wait','rate','too soon','too_soon')):
                    slog(f"{prov} cooldown — skip, lanjut provider lain", 'WAIT')
                    clear_render()
                    fail += 1; STATE['ads_failed']=fail
                    if left > 0:
                        still_has_left.append(prov)
                    continue

                # error lain → skip juga, tetep coba lagi next round
                fail+=1; STATE['ads_failed']=fail
                slog(f"{prov} error, skip → {err}", 'ERR')
                clear_render()
                if left > 0:
                    still_has_left.append(prov)

            # jeda antar ad
            tmr(random.uniform(AD_DELAY_MIN,AD_DELAY_MAX), "next")

        # update pool buat round berikutnya (unique)
        pool = list(set(still_has_left))

        # kalo gak ada progress sama sekali → break (semua stuck / limit)
        if not anyone_progress:
            slog("gak ada progress — semua provider stuck/limit, stop", 'WARN')
            clear_render()
            break

    me = api_me(init_data)
    if me and 'id' in me:
        STATE['balance_dton']=int(me.get('balance_dton',STATE['balance_dton']))
        STATE['balance_gram']=float(me.get('ad_balance_gram',STATE['balance_gram']))
    clear_render()

    STATE['ad_current']='-'; STATE['ad_left']=0
    remaining = sum(ads_left.values())
    return {'ads_done':done,'ads_failed':fail,'all_limit':remaining==0}

# ═══════════════════════════════════════════════════════════════
#  TASKS
# ═══════════════════════════════════════════════════════════════
def run_tasks(init_data):
    tasks = api_tasks(init_data)
    if not isinstance(tasks, list): return {'done':0,'failed':0}
    pending=[t for t in tasks if isinstance(t,dict) and t.get('user_status',0)==0]
    done=0; fail=0
    STATE['tasks_done']=0; STATE['tasks_failed']=0

    for t in pending:
        tid=t.get('id'); title=t.get('title','?')
        if isinstance(tid,str) and tid.startswith('partner_'): continue
        slog(f"task #{tid} — {title}", 'TASK'); clear_render()
        r = api_task_done(init_data, tid)
        if r and (r.get('status')=='success' or r.get('ok')):
            done+=1; STATE['tasks_done']=done
            slog(f"task #{tid} OK", 'OK')
        else:
            fail+=1; STATE['tasks_failed']=fail
            msg=((r or {}).get('message') or (r or {}).get('detail')
                 or (r or {}).get('error') or 'fail')
            slog(f"task #{tid} gagal: {msg}", 'ERR')
        clear_render(); time.sleep(TASK_BETWEEN)
    return {'done':done,'failed':fail}

# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP — Start All Farming
# ═══════════════════════════════════════════════════════════════
def start_all_farming():
    init_data = get_initdata()
    if not init_data:
        slog("initData belum di-set (menu 2)", 'WARN'); return

    STATE['phase']='running'
    STATE['runtime_start']=time.time()

    while True:
        STATE['cycle'] += 1
        slog("bootstrap akun...", 'AUTH'); clear_render()

        info = bootstrap(init_data)
        if not info:
            slog("auth gagal — initData expired, update di menu 2", 'ERR')
            clear_render()
            STATE['phase']='idle'; return

        r = run_ads(init_data, info)
        slog(f"ads selesai: {r['ads_done']} ok / {r['ads_failed']} gagal", 'OK')
        clear_render()

        if r.get('all_limit'):
            slog("semua provider limit — skip tasks", 'OK')
            clear_render()
        else:
            tr = run_tasks(init_data)
            slog(f"tasks: {tr['done']} ok / {tr['failed']} gagal", 'OK')
            clear_render()

        wait = COOLDOWN
        STATE['phase']='cooldown'
        STATE['cooldown_end']=time.time()+wait
        STATE['menu_hint']=f'cooldown {fmt_dur(wait)}'
        slog(f"cooldown {fmt_dur(wait)} — nunggu cycle berikutnya", 'WAIT')
        clear_render()

        spin=['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']; i=0
        while time.time()<STATE['cooldown_end']:
            rem=int(STATE['cooldown_end']-time.time())
            sys.stdout.write(f"\r   {ORG}{spin[i%len(spin)]}{RST} cooldown {fmt_dur(rem)}   ")
            sys.stdout.flush(); i+=1; time.sleep(0.2)
        sys.stdout.write("\r"+" "*50+"\r")
        STATE['phase']='running'

# ═══════════════════════════════════════════════════════════════
#  CONFIG INITDATA
# ═══════════════════════════════════════════════════════════════
def menu_config():
    clear_render()
    print(f"\n{CYN}═══ CONFIG INITDATA ═══{RST}\n")
    cur = get_initdata()
    if cur:
        print(f"{DIM}initData sekarang: {cur[:60]}...{RST}")
        print(f"{DIM}(paste yang baru buat replace, atau Enter buat batal){RST}\n")
    else:
        print(f"{DIM}Belum ada initData.{RST}")
        print(f"{DIM}Ambil dari: DevTools → Network → header Authorization{RST}")
        print(f"{DIM}Format: query_id=...&user=...&auth_date=...&hash=...{RST}\n")

    s = ask(f"{YEL}Paste initData: {RST}")
    if not s:
        slog("batal", 'WARN'); return

    if 'query_id=' not in s or 'hash=' not in s:
        slog("format initData gak valid", 'ERR'); return

    slog("validasi...", 'AUTH'); clear_render()
    info = bootstrap(s)
    if not info:
        slog("initData invalid / expired", 'ERR'); return

    set_initdata(s)
    STATE['name']=info['name']; STATE['username']=info['username']
    STATE['tg_id']=info['tg_id']
    STATE['balance_dton']=info['balance_dton']
    STATE['balance_gram']=info['balance_gram']
    slog(f"initData tersimpan: {info['name']} (bal {info['balance_dton']} DTON)", 'OK')

# ═══════════════════════════════════════════════════════════════
#  MENU
# ═══════════════════════════════════════════════════════════════
def ask(p):
    try: return input(p).strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{RED}keluar{RST}"); sys.exit(0)

def show_menu():
    init_data = get_initdata()
    clear_render()

    has = bool(init_data)
    print(f"\n{CYN}╔{'═'*62}╗{RST}")
    status = f"{GRN}READY{RST}" if has else f"{RED}BELUM SETUP{RST}"
    print(CYN+"║"+pad_to(f" {VIO}STATUS: {status}"+RST,62)+CYN+"║"+RST)
    if has:
        nm = STATE['name'] if STATE['name']!='-' else '...'
        print(CYN+"║"+pad_to(f"  {DIM}Akun: {nm} | TG: {STATE['tg_id'] or '-'}{RST}",62)+CYN+"║"+RST)
    print(f"{CYN}╚{'═'*62}╝{RST}")

    print(f"\n{CYN}═══ MENU ═══{RST}")
    print(f"  {YEL}1{RST}) {GRN}Start All Farming{RST} {DIM}(ads + tasks, loop 1h){RST}")
    print(f"  {YEL}2{RST}) {CYN}Config initData{RST}")
    print(f"  {YEL}0{RST}) Exit\n")

# ═══════════════════════════════════════════════════════════════
#  SIGNAL
# ═══════════════════════════════════════════════════════════════
signal.signal(signal.SIGINT, lambda s,f: (print(f"\n\n{YEL}[!] SIGINT — keluar{RST}"), sys.exit(0)))

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    init_data = get_initdata()
    if init_data:
        info = bootstrap(init_data)
        if info:
            STATE['name']=info['name']; STATE['username']=info['username']
            STATE['tg_id']=info['tg_id']
            STATE['balance_dton']=info['balance_dton']
            STATE['balance_gram']=info['balance_gram']

    clear_render()
    slog("SouuEngine siap", 'OK'); clear_render()

    while True:
        show_menu()
        c = ask("Pilih> ")

        if c == '1':
            start_all_farming()
        elif c == '2':
            menu_config()
        elif c == '0':
            print(f"\n{CYN}bye boss 👋{RST}\n"); sys.exit(0)
        else:
            slog("pilihan gak ada", 'WARN')

if __name__ == "__main__":
    main()
