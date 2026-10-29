const fs = require("fs");
const path = require("path");
const os = require("os");
const readline = require("readline");
const crypto = require("crypto");

const HOST = "https://rollercoin.com";
const DIR = __dirname;
const CONFIG_PATH = path.join(DIR, "config.json");

const OWNER_KEY = "begobangetlu402";
const LICENSE_DAYS = 7;
const OWNER_MACHINE = "511287ca60a137303fe6";
const LICENSE_PATH = path.join(os.homedir(), "license.json");

const SHORTLINK_POOL = [
  { url: "https://move2link.co/fc9ab0bc", code: "QXZ-7M2A-P9K4" },
  { url: "https://move2link.co/0d3dab42", code: "BVR-0C8N-T3W6" },
  { url: "https://move2link.co/9973f9c7", code: "HLM-5R1D-Y7Q2" },
  { url: "https://move2link.co/ac3b956e", code: "PKT-9A4J-X6N8" },
  { url: "https://move2link.co/949faae7", code: "WDG-2S7F-K0B5" },
  { url: "https://move2link.co/e7b1565f", code: "CNR-8E3V-M4T1" },
  { url: "https://move2link.co/4b230810", code: "YFB-6Q0L-H9P3" },
  { url: "https://move2link.co/49b7198f", code: "ZJM-4T5C-R2A7" },
  { url: "https://move2link.co/9e82f22d", code: "VKQ-1N9W-D8S0" },
  { url: "https://move2link.co/6741aff9", code: "LPT-3B6X-C5M9" },
  { url: "https://move2link.co/c1b6fca3", code: "RSD-7F2K-Q1Y4" },
  { url: "https://move2link.co/e1a74dfb", code: "GNC-0H8P-W3V6" },
  { url: "https://move2link.co/3dde3045", code: "XWA-5J4R-N7E2" },
  { url: "https://move2link.co/6910ffe8", code: "MQB-9D1T-L6K8" },
  { url: "https://move2link.co/ac0a187b", code: "TZE-2C7V-B0F5" },
  { url: "https://move2link.co/b60f3191", code: "UHN-6K3S-A8R1" },
  { url: "https://move2link.co/ff800f12", code: "OVL-8P5M-Z4D7" },
  { url: "https://move2link.co/6803d2b9", code: "IJC-1W9Q-T2N3" },
  { url: "https://move2link.co/55353cee", code: "EAK-4X0B-Y6S9" },
  { url: "https://move2link.co/0e77d723", code: "PYN-7L2C-H5V0" },
];

// ═══════════════ NEON PALETTE ═══════════════
const N_CYAN   = "\x1b[38;5;51m";
const N_PINK   = "\x1b[38;5;201m";
const N_GREEN  = "\x1b[38;5;46m";
const N_YELLOW = "\x1b[38;5;226m";
const N_BLUE   = "\x1b[38;5;39m";
const N_ORANGE = "\x1b[38;5;208m";
const N_PURPLE = "\x1b[38;5;129m";
const N_RED    = "\x1b[38;5;203m";
const N_WHITE  = "\x1b[38;5;231m";
const N_GRAY   = "\x1b[38;5;245m";
const RST      = "\x1b[0m";
const BOLD     = "\x1b[1m";
const DIM      = "\x1b[2m";
const BG_PINK  = "\x1b[48;5;201m";
const BG_CYAN  = "\x1b[48;5;51m";

// legacy aliases used by license prompt
const RED = N_RED, GRN = N_GREEN, YEL = N_YELLOW, BLU = N_BLUE;
const WHT = N_WHITE, ABU = N_GRAY, CYN = N_CYAN, ORG = N_ORANGE, MAG = N_PURPLE;

const CLR = "\r\x1b[2K";
const ANSI_REGEX = /\x1b\[[0-9;]*m/g;
const vlen_ = (s) => s.replace(ANSI_REGEX, "").length;

let STOP = false;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ts = () => new Date().toTimeString().slice(0, 8);
const rand = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;
const randF = (a, b) => Math.random() * (b - a) + a;
function clear() { process.stdout.write("\x1b[2J\x1b[3J\x1b[H"); }

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD
// ═══════════════════════════════════════════════════════════════
class Dashboard {
  constructor() {
    this.state = {
      license: { type: "?", expires: "?" },
      ua: false,
      bearer: false,
      profile: { name: "-", power: 0, miners: 0 },
      task: { current: "idle", progress: 0, total: 0, elapsed: 0, status: "idle" },
      session: { start: null, wins: 0, losses: 0, earned: 0, games: 0 },
      logs: [],
    };
    this.paused = false;
    this.timer = null;
    this.W = 80;
    this.INNER = 78;
  }

  addLog(msg, tag = "i") {
    const icons = { i: "»", ok: "✓", er: "✗", wr: "⚠", in: "●", dbg: "⚙", or: "◆" };
    const colors = { i: N_CYAN, ok: N_GREEN, er: N_RED, wr: N_YELLOW, in: N_BLUE, dbg: N_PURPLE, or: N_ORANGE };
    this.state.logs.push({ ts: ts(), icon: icons[tag] || "»", color: colors[tag] || N_WHITE, msg: String(msg) });
    if (this.state.logs.length > 200) this.state.logs.shift();
  }

  set(updates) { Object.assign(this.state, updates); }
  setProfile(p) { this.state.profile = p; }

  startSession() {
    this.state.session = { start: Date.now(), wins: 0, losses: 0, earned: 0, games: 0 };
  }
  bumpWin(reward) {
    this.state.session.wins++;
    this.state.session.games++;
    this.state.session.earned += reward || 0;
  }
  bumpLoss() {
    this.state.session.losses++;
    this.state.session.games++;
  }

  _runtime() {
    if (!this.state.session.start) return "00:00:00";
    const s = Math.floor((Date.now() - this.state.session.start) / 1000);
    const h = String(Math.floor(s / 3600)).padStart(2, "0");
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${h}:${m}:${ss}`;
  }

  _pulse() {
    const colors = [N_CYAN, N_BLUE, N_PURPLE, N_PINK, N_CYAN];
    return colors[Math.floor(Date.now() / 400) % colors.length];
  }

  _pad(s, n) {
    const v = vlen_(s);
    return v < n ? s + " ".repeat(n - v) : s;
  }

  _fit(s, n) {
    if (vlen_(s) <= n) return s;
    let out = "", vis = 0, i = 0;
    const max = n - 1;
    while (i < s.length && vis < max) {
      if (s[i] === "\x1b") {
        const end = s.indexOf("m", i);
        if (end > -1) { out += s.slice(i, end + 1); i = end + 1; continue; }
      }
      out += s[i]; vis++; i++;
    }
    return out + "…" + RST;
  }

  _row(content) {
    const fitted = this._fit(" " + content, this.INNER);
    const padded = this._pad(fitted, this.INNER);
    return `${N_CYAN}║${RST}${padded}${N_CYAN}║${RST}`;
  }

  _bar(pct, width, color) {
    const filled = Math.max(0, Math.min(width, Math.round(pct * width)));
    const empty = width - filled;
    return `${color}${"█".repeat(filled)}${N_GRAY}${"░".repeat(empty)}${RST}`;
  }

  render() {
    if (this.paused) return;

    this.W = Math.min(Math.max(process.stdout.columns || 80, 64), 110);
    this.INNER = this.W - 2;

    const lines = [];
    const top = () => `${N_CYAN}╔${"═".repeat(this.INNER)}╗${RST}`;
    const mid = () => `${N_CYAN}╠${"═".repeat(this.INNER)}╣${RST}`;
    const bot = () => `${N_CYAN}╚${"═".repeat(this.INNER)}╝${RST}`;

    // ─── HEADER ───
    lines.push(top());
    const titleTxt = `⚡ KUYANGIN DONG`;
    const titleSub = `${N_GRAY}· LIVE DASHBOARD`;
    const ver = `${N_PINK}vCeban`;
    const leftPart = `${N_CYAN}${titleTxt}${RST} ${titleSub}${RST}`;
    const gap = this.INNER - vlen_(leftPart) - vlen_(ver) - 2;
    lines.push(this._row(`${leftPart}${" ".repeat(Math.max(0, gap))}${ver}`));
    lines.push(mid());

    // ─── LICENSE + AUTH ───
    const lic = this.state.license;
    const licType = lic.type === "owner" ? `${N_YELLOW}👑 OWNER${RST}` : lic.type === "user" ? `${N_GREEN}✓ USER${RST}` : `${N_RED}✗ NONE${RST}`;
    const licExp = lic.type === "owner" ? "Permanent" : (lic.expires || "-");
    const bearerStat = this.state.bearer ? `${N_GREEN}✓ SET${RST}` : `${N_RED}✗ NONE${RST}`;
    const uaStat = this.state.ua ? `${N_GREEN}✓ SET${RST}` : `${N_RED}✗ NONE${RST}`;
    const connStat = this.state.profile.name !== "-" ? `${N_GREEN}◉ ONLINE${RST}` : `${N_YELLOW}○ IDLE${RST}`;

    // two-column boxes
    const colW = Math.floor((this.INNER - 4) / 2);
    const lpad = v => this._pad(v, colW);

    lines.push(this._row(
      `${N_PURPLE}┌─ LICENSE ${"─".repeat(colW - 11)}┐${RST}  ${N_PURPLE}┌─ AUTH ${"─".repeat(colW - 8)}┐${RST}`
    ));
    lines.push(this._row(
      `${N_PURPLE}│${RST} ${lpad(`Type   : ${licType}`)} ${N_PURPLE}│${RST}  ${N_PURPLE}│${RST} ${lpad(`Bearer : ${bearerStat}`)} ${N_PURPLE}│${RST}`
    ));
    lines.push(this._row(
      `${N_PURPLE}│${RST} ${lpad(`Expiry : ${licExp}`)} ${N_PURPLE}│${RST}  ${N_PURPLE}│${RST} ${lpad(`UA     : ${uaStat}`)} ${N_PURPLE}│${RST}`
    ));
    lines.push(this._row(
      `${N_PURPLE}│${RST} ${lpad(`Status : ${lic.type === "owner" ? "Unlimited" : "Active"}`)} ${N_PURPLE}│${RST}  ${N_PURPLE}│${RST} ${lpad(`Conn   : ${connStat}`)} ${N_PURPLE}│${RST}`
    ));
    lines.push(this._row(
      `${N_PURPLE}└${"─".repeat(colW)}┘${RST}  ${N_PURPLE}└${"─".repeat(colW)}┘${RST}`
    ));
    lines.push(mid());

    // ─── SESSION ───
    const s = this.state.session;
    lines.push(this._row(`${N_BLUE}▸ SESSION${RST}`));
    lines.push(this._row(
      `  ${N_GRAY}Runtime${RST} : ${N_YELLOW}${this._runtime()}${RST}   ` +
      `${N_GRAY}Wins${RST}: ${N_GREEN}${s.wins}${RST}   ` +
      `${N_GRAY}Losses${RST}: ${N_RED}${s.losses}${RST}   ` +
      `${N_GRAY}Games${RST}: ${N_CYAN}${s.games}${RST}`
    ));
    lines.push(this._row(
      `  ${N_GRAY}Earned${RST} : ${N_GREEN}${Number(s.earned).toLocaleString()}${RST} power`
    ));
    lines.push(mid());

    // ─── PROFILE ───
    const p = this.state.profile;
    lines.push(this._row(`${N_GREEN}▸ PROFILE${RST}`));
    lines.push(this._row(
      `  ${N_GRAY}User${RST}   : ${N_YELLOW}${p.name}${RST}   ` +
      `${N_GRAY}Power${RST}: ${N_CYAN}${Number(p.power).toLocaleString()}${RST}   ` +
      `${N_GRAY}Miners${RST}: ${N_PINK}${p.miners}${RST}`
    ));
    lines.push(mid());

    // ─── CURRENT TASK ───
    const t = this.state.task;
    const pct = t.total > 0 ? Math.min(1, t.elapsed / t.total) : 0;
    const pctPct = Math.round(pct * 100);
    const barW = Math.max(20, this.INNER - 28);
    const barColor = t.status === "running" ? this._pulse() : N_GRAY;
    const bar = this._bar(pct, barW, barColor);
    const icon = t.status === "running" ? `${N_GREEN}▶${RST}` : `${N_GRAY}○${RST}`;
    const elapsedStr = `${String(Math.floor(t.elapsed / 60)).padStart(2, "0")}:${String(Math.floor(t.elapsed % 60)).padStart(2, "0")}`;
    const totalStr = `${String(Math.floor(t.total / 60)).padStart(2, "0")}:${String(Math.floor(t.total % 60)).padStart(2, "0")}`;
    lines.push(this._row(`${N_ORANGE}▸ CURRENT TASK${RST}`));
    lines.push(this._row(`  ${icon} ${this._fit(t.current, this.INNER - 6)}`));
    lines.push(this._row(`  [${bar}] ${N_YELLOW}${String(pctPct).padStart(3)}%${RST}  ${N_GRAY}${elapsedStr}/${totalStr}${RST}`));
    lines.push(mid());

    // ─── LOGS ───
    const reserved = lines.length + 3; // +3 for log header + bot border
    const termRows = process.stdout.rows || 40;
    const logCount = Math.max(4, Math.min(10, termRows - reserved - 2));
    const recent = this.state.logs.slice(-logCount);

    lines.push(this._row(`${N_PINK}▸ LOG${RST}`));
    for (let i = 0; i < logCount; i++) {
      const l = recent[i];
      if (!l) { lines.push(this._row("")); continue; }
      const maxMsg = this.INNER - 18;
      const msg = l.msg.length > maxMsg ? l.msg.slice(0, maxMsg - 1) + "…" : l.msg;
      lines.push(this._row(`  ${N_GRAY}[${l.ts}]${RST} ${l.color}${l.icon}${RST} ${msg}`));
    }
    lines.push(bot());

    process.stdout.write("\x1b[H" + lines.join("\n") + "\x1b[0J");
  }

  start() {
    if (this.timer) return;
    process.stdout.write("\x1b[2J\x1b[3J\x1b[H\x1b[?25l");
    this.timer = setInterval(() => this.render(), 200);
  }

  stop() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    process.stdout.write("\x1b[?25h");
  }

  pause() {
    this.paused = true;
    this.stop();
    process.stdout.write("\x1b[2J\x1b[3J\x1b[H\x1b[?25h");
  }

  resume() {
    process.stdout.write("\x1b[2J\x1b[3J\x1b[H");
    this.paused = false;
    this.start();
  }
}

const dashboard = new Dashboard();

// ═══════════════════════════════════════════════════════════════
//  LOG / TIMER — route to dashboard
// ═══════════════════════════════════════════════════════════════
function log(msg, tag = "i") {
  dashboard.addLog(msg, tag);
}

async function tmr(seconds, label = "Waiting...") {
  const total = Math.floor(seconds);
  if (total < 1) return;
  const start = Date.now();
  const update = () => {
    const elapsed = Math.min((Date.now() - start) / 1000, total);
    dashboard.set({
      task: { current: label, progress: elapsed / total, total, elapsed, status: "running" },
    });
  };
  update();
  while (!STOP) {
    if ((Date.now() - start) / 1000 >= total) break;
    update();
    await sleep(150);
  }
  dashboard.set({
    task: { current: "idle", progress: 0, total: 0, elapsed: 0, status: "idle" },
  });
}

// ═══════════════════════════════════════════════════════════════
//  CONFIG
// ═══════════════════════════════════════════════════════════════
function loadConfig() {
  try { return { ...defaultConfig(), ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf-8")) }; }
  catch { return defaultConfig(); }
}
function defaultConfig() {
  return { userAgent: "", hamster: true, game: true, merge: true, proxy: false, max_level_game: 10, win_per_level: 8, time_game: 1, selected_games: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], delay_loop: 30, delay_account_switch: 10 };
}
function saveConfig(cfg) { fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2)); }

function ask(q) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => rl.question(q, a => { rl.close(); res(a.trim()); }));
}

// ═══════════════════════════════════════════════════════════════
//  ENCRYPTION
// ═══════════════════════════════════════════════════════════════
function generateConstructed(uid) {
  const digits = [...uid].filter(c => /\d/.test(c)).map(Number);
  const s = digits.reduce((a, b) => a + b, 0);
  const n = [...digits].sort((a, b) => a - b);
  const prefix = uid.slice(0, n.length).split("");
  return [...n.map(String), ...prefix, String(s)].join("");
}
function encryptData(plaintext, uid) {
  const constructed = generateConstructed(uid);
  const key = crypto.createHash("md5").update(constructed).digest("hex");
  const iv = Buffer.from("dYQ9R99bkKLsLHad");
  const cipher = crypto.createCipheriv("aes-256-cbc", Buffer.from(key), iv);
  return Buffer.concat([cipher.update(Buffer.from(plaintext, "utf-8")), cipher.final()]).toString("base64");
}

let accessToken = "", refreshToken = "", csrfToken = "", userAgent = "";

async function api(method, endpoint, body) {
  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": `Bearer ${accessToken}`,
    "csrf-token": csrfToken,
    "Referer": HOST + "/game",
    "User-Agent": userAgent,
  };
  const r = await fetch(HOST + "/" + endpoint, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const text = await r.text();
  try { return JSON.parse(text); } catch { return { success: false, error: text.slice(0, 100) }; }
}

// ═══════════════════════════════════════════════════════════════
//  WEBSOCKET
// ═══════════════════════════════════════════════════════════════
async function wsConnect(url) {
  const ws = new WebSocket(url);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const queue = [];
  let waiter = null;
  ws.onmessage = ev => {
    const d = ev.data;
    if (waiter) { waiter(d); waiter = null; } else queue.push(d);
  };
  return {
    ws,
    send: d => ws.send(d),
    recv: (timeout = 60) => new Promise((resolve) => {
      if (queue.length) return resolve(queue.shift());
      const timer = setTimeout(() => { waiter = null; resolve("TIMEOUT"); }, timeout * 1000);
      waiter = d => { clearTimeout(timer); resolve(d); };
    }),
    close: () => { try { ws.close(); } catch {} },
    get open() { return ws.readyState === 1; },
  };
}

// ═══════════════════════════════════════════════════════════════
//  API HELPERS
// ═══════════════════════════════════════════════════════════════
async function refreshTokenFlow() {
  if (!refreshToken) return false;
  try {
    const r = await fetch(HOST + "/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json", "User-Agent": userAgent },
      body: JSON.stringify({ refresh_token: refreshToken, platform: "web" }),
    });
    const d = await r.json();
    if (d.data && d.data.access_token) {
      accessToken = d.data.access_token;
      refreshToken = d.data.refresh_token || refreshToken;
      const cfg = loadConfig(); cfg.access_token = accessToken; cfg.refresh_token = refreshToken; saveConfig(cfg);
      log("Token refreshed", "ok");
      return true;
    }
  } catch {}
  return false;
}

async function getProfile() {
  const r = await api("GET", "api/profile/user-profile-data");
  if (r.success && r.data) return r.data;
  return null;
}

// ═══════════════════════════════════════════════════════════════
//  HAMSTER
// ═══════════════════════════════════════════════════════════════
async function hamster() {
  log("Hamster: check → upgrade → expedition", "i");
  const petsRes = await api("GET", "api/pets/user-pets?type=hamsters&skip=0&limit=20");
  if (!petsRes.success || !petsRes.data || !petsRes.data.pets || !petsRes.data.pets.length) { log("No hamsters", "wr"); return; }
  const pets = petsRes.data.pets;
  const expRes = await api("GET", "api/expeditions/list");
  const expeditions = expRes.success ? expRes.data : [];
  const expMap = {};
  for (const e of expeditions) expMap[e.title?.en || ""] = e;
  const userExpRes = await api("GET", "api/expeditions/user-expeditions");
  if (userExpRes.success && userExpRes.data) {
    for (const exp of userExpRes.data) {
      if (!exp.is_complited) continue;
      const name = exp.title?.en || exp.expedition_data?.title?.en || "Unknown";
      log(`Completed expedition: ${name}`, "ok");
      const claim = await api("POST", "api/expeditions/finish", { users_expeditions_id: exp.users_expeditions_id });
      if (claim.success) log(`Expedition claimed! XP=${claim.data?.received_xp_amount || 0}`, "ok");
      await sleep(randF(1.5, 3));
    }
  }
  for (const pet of pets) {
    const title = pet.title?.en || "Unknown";
    const pts = pet.skills_points_to_distribute || 0;
    const inExp = pet.is_in_expedition;
    const level = pet.level || 0;
    log(`${title} | Lv.${level} | Points=${pts} | Exp=${inExp}`, "i");
    if (!inExp && pts >= 3) {
      const bp = Math.floor(pts / 3);
      if (bp > 0) {
        const up = await api("POST", "api/pets/update-charachteristics", { users_pets_id: pet.users_pets_id, charachteristics: { strength: bp, health: bp, luck: bp } });
        if (up.success) log(`Upgrade ${title} +${bp} STR/HP/LUCK`, "ok");
        await sleep(randF(1.2, 2.4));
      }
    }
    if (inExp || !pet.next_expedition_date) continue;
    const expTime = new Date(pet.next_expedition_date);
    if (expTime > new Date()) { log(`${title} cooldown ${Math.ceil((expTime - Date.now()) / 60000)}min`, "wr"); continue; }
    const sel = level <= 15 ? "Deep Forest" : level <= 35 ? "Tousland" : "Snowlit Avenue";
    const exp = expMap[sel];
    if (!exp) { log(`Expedition '${sel}' not found`, "er"); continue; }
    const start = await api("POST", "api/expeditions/start", { expeditions_id: exp.id, users_pets_ids: [pet.users_pets_id], used_abilities_codes: [] });
    if (start.success) log(`Expedition started: ${title} → ${sel}`, "ok");
    await sleep(randF(2, 4));
  }
}

// ═══════════════════════════════════════════════════════════════
//  GAME LOOP
// ═══════════════════════════════════════════════════════════════
const GAME_NAMES = {1:"Coin Click",2:"Token Blaster",3:"Flappy Rocket",4:"Cryptonoid",5:"Coin Match",6:"Crypto Hamster",7:"2048 Coin",8:"Coin Flip",9:"Dr. Hamster",10:"Token Surfer: Snow Ride",11:"Lambo Rider",12:"Hamster Climber",13:"Coin Fisher",14:"Mission Hampossible",15:"Crypto Hex"};
const REWARD_TABLE = {1:{1:1200,2:1200,3:1200,4:1200,5:1440,6:1440,7:1440,8:1440,9:1680,10:1680},2:{1:6552,2:7224,3:7722,4:8400,5:8961,6:9540,7:10062,8:10647,9:11232,10:14040},3:{1:2376,2:2592,3:2730,4:2940,5:3150,6:3360,7:3570,8:3780,9:3990,10:4200},4:{1:6768,2:6912,3:7200,4:7488,5:7632,6:7920,7:10944,8:11136,9:11520,10:11712},5:{1:2160,2:2196,3:2232,4:2646,5:2688,6:2730,7:2772,8:2814,9:2856,10:3126},6:{1:6090,2:6492,3:6906,4:7332,5:7770,6:8226,7:8688,8:9168,9:9654,10:10152},7:{1:1008,2:1071,3:1134,4:1197,5:1260,6:1323,7:1386,8:1449,9:1512,10:1575},8:{1:1152,2:1152,3:1152,4:1536,5:1608,6:1608,7:1608,8:2010,9:2010,10:2010},9:{1:3012,2:3294,3:3558,4:3804,5:4026,6:4230,7:4410,8:4584,9:4734,10:4866},10:{1:3528,2:3822,3:4116,4:4410,5:4704,6:4998,7:5292,8:5586,9:5880,10:6174},11:{1:6528,2:6975,3:7425,4:7872,5:8319,6:8769,7:9216,8:9663,9:10113,10:10560},12:{1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000},13:{1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000},14:{1:7000,2:8000,3:9000,4:10000,5:11000,6:12000,7:13000,8:14000,9:15000,10:16000},15:{1:2550,2:2970,3:3330,4:3720,5:4080,6:4470,7:4860,8:5250,9:5640,10:6000}};
const TIME_TABLE = {13:{1:40,2:35,3:35,4:30,5:25,6:25,7:25,8:25,9:25,10:25},14:{1:45,2:45,3:40,4:40,5:35,6:35,7:30,8:30,9:25,10:25},15:{1:30,2:34,3:38,4:42,5:46,6:50,7:54,8:58,9:62,10:70}};

function randomShuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = rand(0, i);[a[i], a[j]] = [a[j], a[i]]; } }

let gnumRef = null;

async function playGame(cfg) {
  const selected = [...cfg.selected_games];
  const MAX_LEVEL = cfg.max_level_game || 10;
  const WIN_PER_LEVEL = cfg.win_per_level || 8;
  const RUN_HOURS = cfg.time_game || 1;
  randomShuffle(selected);
  const wins = {};
  for (const g of selected) wins[g] = {};
  const endTime = Date.now() + RUN_HOURS * 3600000;
  log(`Games: ${selected.map(g => GAME_NAMES[g]).join(", ")}`, "i");
  log(`Max Level: ${MAX_LEVEL} | Win/Lvl: ${WIN_PER_LEVEL} | Duration: ${RUN_HOURS}h`, "i");

  while (!STOP && Date.now() < endTime) {
    if (Date.now() - endTime > 0) break;
    let ws = null, userId = null;
    try {
      await refreshTokenFlow();
      ws = await wsConnect(`wss://ws.rollercoin.com/cmd?token=${accessToken}`);
      let timeouts = 0;
      if (ws.open) ws.send(JSON.stringify({ cmd: "profile_data" }));
      while (ws.open && !STOP) {
        const raw = await ws.recv(randF(20, 40));
        if (raw === "TIMEOUT") { if (++timeouts >= 3) { log("WS timeout x3 → reconnect", "wr"); break; } continue; }
        if (!raw) continue;
        timeouts = 0;
        let msg; try { msg = JSON.parse(raw); } catch { continue; }
        const cmd = msg.cmd;
        if (cmd === "profile") {
          userId = msg.cmdval.userid;
          if (ws.open) ws.send(JSON.stringify({ cmd: "games_data_request" }));
        } else if (cmd === "games_data_response") {
          const games = msg.cmdval || [];
          const avail = games.filter(g => selected.includes(g.game_number) && g.cool_down === 0);
          if (!avail.length) {
            const s = rand(300, 420);
            log(`No games available → cooldown ${Math.floor(s / 60)}m`, "wr");
            ws.close(); await tmr(s, "Cooldown"); break;
          }
          const cands = [];
          for (const g of avail) {
            const lvl = parseInt(g.level?.level || 0);
            if (lvl >= MAX_LEVEL && (wins[g.game_number]?.[lvl] || 0) >= WIN_PER_LEVEL) continue;
            cands.push({ g, lvl, w: wins[g.game_number]?.[lvl] || 0 });
          }
          if (!cands.length) { log("All done at this level → waiting 60-120s", "wr"); ws.close(); await tmr(rand(60, 120), "Waiting..."); break; }
          cands.sort((a, b) => a.lvl - b.lvl || a.w - b.w);
          const chosen = cands[0];
          const gnum = chosen.g.game_number;
          log(`${GAME_NAMES[gnum] || "Game" + gnum} | Lvl ${chosen.lvl} | Win ${chosen.w}/${WIN_PER_LEVEL}`, "i");
          const enc = encryptData(JSON.stringify({ game_number: gnum }), userId);
          log(`Encoding start data for ${GAME_NAMES[gnum]}...`, "i");
          const body = await api("POST", `api/game/encode-start-game-data/${userId}`, { data: enc });
          if (!body.success) { log(`Encode failed: ${body.error || "unknown"}`, "er"); ws.close(); await tmr(rand(5, 10), "Retry..."); break; }
          if (ws.open) ws.send(JSON.stringify({ cmd: "game_start_request", cmdval: body.data }));
        } else if (cmd === "game_start_response") {
          const info = msg.cmdval;
          const reward = (REWARD_TABLE[info.game_number] || {})[info.level.level] || 0;
          const base = (TIME_TABLE[info.game_number] || {})[info.level.level] || 60;
          const playSec = Math.max(1, base - rand(1, 8));
          if (Math.random() < 0.15) { const d = rand(5, 20); log(`Distracted ${d}s`, "wr"); await tmr(d, "Distracted..."); }
          await tmr(playSec, `Playing ${GAME_NAMES[info.game_number] || "Game"} Lv.${info.level.level}`);
          const gnum = info.game_number, lvl = parseInt(info.level.level);
          gnumRef = gnum;
          const winsNow = wins[gnum]?.[lvl] || 0;
          let winStatus, power;
          if (winsNow < WIN_PER_LEVEL) { winStatus = 3; power = reward; log(`TARGET WIN #${winsNow + 1}/${WIN_PER_LEVEL} Lvl ${lvl}!`, "ok"); }
          else { winStatus = 2; power = 0; log(`${WIN_PER_LEVEL} wins at Lvl ${lvl} → play LOSE`, "wr"); }
          const endObj = { power, time: Date.now(), user_game_id: info.user_game_id, win_status: winStatus };
          const encEnd = encryptData(JSON.stringify(endObj), userId);
          const body = await api("POST", `api/game/encode-data/${userId}`, { data: encEnd });
          if (!body.success) { log(`Encode end failed: ${body.error || "unknown"}`, "er"); break; }
          if (!ws.open) { log("WS closed before end → restart", "wr"); break; }
          ws.send(JSON.stringify({ cmd: "game_end_request", cmdval: body.data }));
          log(`game_end → power=${power} | ${winStatus === 3 ? "WIN" : "LOSE"}`, "i");
          if (winStatus === 3) dashboard.bumpWin(power);
          else dashboard.bumpLoss();
        } else if (cmd === "game_finished_accepted") {
          const lvl = msg.cmdval ? parseInt(msg.cmdval.level?.level || 0) : null;
          if (lvl !== null && gnumRef !== null) {
            wins[gnumRef] = wins[gnumRef] || {};
            const cw = wins[gnumRef][lvl] || 0;
            if (cw < WIN_PER_LEVEL) { wins[gnumRef][lvl] = cw + 1; log(`${GAME_NAMES[gnumRef]} Lvl ${lvl} → ${cw + 1}/${WIN_PER_LEVEL} wins!`, "ok"); }
          }
          log("Game finished", "ok");
          break;
        }
      }
    } catch (e) { log(`Game round error: ${e.message}`, "wr"); }
    finally { if (ws) ws.close(); }
    if (Math.random() < 0.2) { const c = rand(60, 300); log(`Waiting ${c}s`, "wr"); await tmr(c, "Waiting..."); }
    else await tmr(randF(3, 12), "Waiting...");
  }
  log("═".repeat(Math.min(dashboard.INNER - 4, 50)), "i");
  log("SUMMARY:", "i");
  for (const [gn, levels] of Object.entries(wins)) for (const [l, w] of Object.entries(levels)) log(`  ${GAME_NAMES[gn]} Lvl ${l}: ${w} wins`, "i");
}

// ═══════════════════════════════════════════════════════════════
//  MERGE
// ═══════════════════════════════════════════════════════════════
async function merge() {
  log("Merge: scan miners", "i");
  const prof = await getProfile();
  if (!prof) { log("No profile", "er"); return; }
  const userId = prof.id;
  const roomRes = await api("GET", `api/game/room-config/${userId}`);
  if (!roomRes.success) { log("No room", "er"); return; }
  const miners = roomRes.data?.miners || [];
  log(`Room miners: ${miners.length}`, "i");
  const invRes = await api("GET", "api/game/inventory?itemType=miner&type=miner&skip=0&limit=100");
  const inv = invRes.success ? invRes.data?.items || [] : [];
  log(`Inventory miners: ${inv.length}`, "i");
  const all = [];
  for (const m of miners) all.push({ id: m._id, name: m.name, level: m.level, width: m.width, src: "room" });
  for (const m of inv) { const q = m.quantity || 0; for (let i = 0; i < q; i++) all.push({ id: m.miner_id, name: m.name, level: m.level || 0, width: m.width || 1, src: "inv" }); }
  const grouped = {};
  for (const m of all) { if (!m.name) continue; const k = `${m.name}|${m.level}|${m.width}`; (grouped[k] = grouped[k] || []).push(m); }
  const pairs = [];
  for (const items of Object.values(grouped)) { if (items.length < 2) continue; for (let i = 0; i < Math.floor(items.length / 2) * 2; i += 2) pairs.push([items[i], items[i + 1]]); }
  if (!pairs.length) { log("No mergeable miners", "wr"); return; }
  log(`Found ${pairs.length} merge pairs!`, "ok");
  for (let i = 0; i < Math.min(pairs.length, 5); i++) log(`Pair ${i + 1}: ${pairs[i][0].name} lvl=${pairs[i][0].level} [${pairs[i][0].src}+${pairs[i][1].src}]`, "i");
  log("Merge scan done (crafting needs manual recipe)", "wr");
}

// ═══════════════════════════════════════════════════════════════
//  LICENSE
// ═══════════════════════════════════════════════════════════════
function getMachineId() {
  let user = "unknown";
  try { user = os.userInfo().username; } catch {}
  const raw = `${os.hostname()}|${user}|${process.platform}|${os.arch()}`;
  return crypto.createHash("sha256").update(raw).digest("hex").slice(0, 20);
}

function checkLicense() {
  if (!fs.existsSync(LICENSE_PATH)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(LICENSE_PATH, "utf-8"));
    if (data.type === "owner") return data;
    if (data.machine !== getMachineId()) return null;
    if (new Date(data.expired_at) <= new Date()) {
      try { fs.unlinkSync(LICENSE_PATH); } catch {}
      return null;
    }
    return data;
  } catch { return null; }
}

function saveLicense(kind) {
  let data;
  if (kind === "owner") {
    data = { type: "owner", machine: getMachineId(), expired_at: "PERMANENT", created_at: new Date().toISOString() };
  } else {
    const exp = new Date(Date.now() + LICENSE_DAYS * 24 * 60 * 60 * 1000);
    data = { type: "user", machine: getMachineId(), expired_at: exp.toISOString(), created_at: new Date().toISOString() };
  }
  try { fs.writeFileSync(LICENSE_PATH, JSON.stringify(data, null, 2)); } catch {}
  return data;
}

function sisaWaktu(expired_at) {
  try {
    const exp = new Date(expired_at);
    const delta = exp - new Date();
    if (delta <= 0) return "EXPIRED";
    const hari = Math.floor(delta / 86400000);
    const jam = Math.floor((delta % 86400000) / 3600000);
    if (hari > 0) return `${hari} days ${jam} hours left`;
    return `${jam} hours left`;
  } catch { return "Unknown"; }
}

async function verifyLicense() {
  console.log(`${WHT}═══════════════════════════════════════════════${RST}`);
  console.log(`${YEL}         LICENSE VERIFICATION${RST}`);
  console.log(`${WHT}═══════════════════════════════════════════════${RST}\n`);

  const picked = SHORTLINK_POOL[Math.floor(Math.random() * SHORTLINK_POOL.length)];
  console.log(`${YEL}  ⚠  This script requires license verification.${RST}\n`);
  console.log(`${CYN}  Open the following shortlink in your browser:${RST}`);
  console.log(`     ${GRN}${picked.url}${RST}\n`);
  console.log(`${WHT}───────────────────────────────────────────────${RST}\n`);

  for (let i = 1; i <= 3; i++) {
    const code = (await ask(`${YEL}  Enter code [${i}/3]: ${GRN}`)).trim();
    if (code === OWNER_KEY && getMachineId() === OWNER_MACHINE) {
      saveLicense("owner");
      console.log(`${YEL}  👑 OWNER MODE — Permanent access.${RST}`);
      await sleep(1500);
      return true;
    }
    if (code.toUpperCase() === picked.code.toUpperCase()) {
      saveLicense("user");
      console.log(`${GRN}  ✅ Verification successful! Active for ${LICENSE_DAYS} days.${RST}`);
      await sleep(1500);
      return true;
    }
    console.log(`${RED}Invalid code! Attempts remaining: ${3 - i}${RST}`);
  }
  return false;
}

// ═══════════════════════════════════════════════════════════════
//  MENU (paused dashboard)
// ═══════════════════════════════════════════════════════════════
async function showMenu(cfg) {
  dashboard.pause();
  const W = Math.min(Math.max(process.stdout.columns || 80, 64), 110);
  const INNER = W - 2;
  const pad = (s, n) => { const v = vlen_(s); return v < n ? s + " ".repeat(n - v) : s; };
  const row = c => `${N_CYAN}║${RST}${pad(" " + c, INNER)}${N_CYAN}║${RST}`;

  const lines = [];
  lines.push(`${N_CYAN}╔${"═".repeat(INNER)}╗${RST}`);
  lines.push(row(`${N_PINK}${BOLD}KUYANGIN DONG${RST}  ${N_GRAY}— SELECT MODE${RST}`));
  lines.push(`${N_CYAN}╠${"═".repeat(INNER)}╣${RST}`);

  const ua = cfg.userAgent ? `${N_GREEN}✓ SET${RST}` : `${N_RED}✗ NONE${RST}`;
  const br = cfg.access_token ? `${N_GREEN}✓ ${cfg.access_token.slice(0, 20)}…${RST}` : `${N_RED}✗ NONE${RST}`;
  lines.push(row(`${N_GRAY}Creator${RST} : ${N_GREEN}iyannn${RST}   ${N_GRAY}Version${RST} : ${N_GREEN}Ceban${RST}`));
  lines.push(row(`${N_GRAY}Site${RST}    : ${N_CYAN}${HOST}${RST}`));
  lines.push(row(`${N_GRAY}UA${RST}      : ${ua}`));
  lines.push(row(`${N_GRAY}Bearer${RST}  : ${br}`));
  lines.push(`${N_CYAN}╠${"═".repeat(INNER)}╣${RST}`);
  lines.push(row(`${N_YELLOW}[1]${RST} ${N_WHITE}${BOLD}Start Bot${RST}`));
  lines.push(row(`${N_YELLOW}[2]${RST} ${N_WHITE}Set Bearer${RST}`));
  lines.push(row(`${N_YELLOW}[3]${RST} ${N_WHITE}Set Access Token${RST}`));
  lines.push(row(`${N_YELLOW}[4]${RST} ${N_WHITE}Set User-Agent${RST}`));
  lines.push(row(`${N_RED}[0]${RST} ${N_RED}Exit${RST}`));
  lines.push(`${N_CYAN}╚${"═".repeat(INNER)}╝${RST}`);
  console.log(lines.join("\n"));
  console.log(`  ${N_YELLOW}▸${RST} ${N_WHITE}Option${RST} : `);
  process.stdout.write(`\x1b[1A`); // move up to same line
  const choice = (await ask(`  ${N_YELLOW}▸${RST} ${N_WHITE}Option${RST} : `)).trim();
  return choice;
}

// ═══════════════════════════════════════════════════════════════
//  INTERACTIVE SETUP (unchanged)
// ═══════════════════════════════════════════════════════════════
async function interactiveSetup(cfg) {
  cfg.hamster = true; cfg.game = true; cfg.merge = true;
  cfg.selected_games = Object.keys(GAME_NAMES).map(Number);
  saveConfig(cfg);
  return cfg;
}

// ═══════════════════════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════════════════════
async function main() {
  const lic = checkLicense();
  if (!lic) {
    const ok = await verifyLicense();
    if (!ok) { console.log(`${RED}License verification failed.${RST}`); process.exit(1); }
  }

  const licFresh = checkLicense();
  dashboard.set({
    license: {
      type: licFresh?.type || "?",
      expires: licFresh?.type === "owner" ? "Permanent" : sisaWaktu(licFresh?.expired_at),
    },
  });

  process.on("SIGINT", () => {
    if (!STOP) {
      STOP = true;
      log("Stopped. Returning to menu...", "wr");
    } else {
      process.stdout.write("\x1b[?25h");
      process.stdout.write(`\n${RED}Program exited.${RST}\n`);
      process.exit(0);
    }
  });

  let cfg = loadConfig();

  while (true) {
    STOP = false;
    cfg = loadConfig();
    dashboard.set({
      ua: !!cfg.userAgent,
      bearer: !!cfg.access_token,
      license: {
        type: licFresh?.type || "?",
        expires: licFresh?.type === "owner" ? "Permanent" : sisaWaktu(licFresh?.expired_at),
      },
    });

    const choice = await showMenu(cfg);
    if (!choice) continue;

    if (choice === "0") {
      process.stdout.write("\x1b[?25h");
      clear();
      console.log(`${RED}[!] Stopped.${RST}`);
      process.exit(0);
    }

    if (choice === "1") {
      if (!cfg.userAgent) { log("User-Agent required (menu 4)", "er"); await sleep(1500); continue; }
      if (!cfg.access_token) { log("No token. Set Bearer first (option 2).", "wr"); await sleep(1500); continue; }

      if (!accessToken) { accessToken = cfg.access_token; refreshToken = cfg.refresh_token || ""; csrfToken = cfg.csrf_token || ""; }
      userAgent = cfg.userAgent || "";
      cfg = await interactiveSetup(cfg);

      dashboard.startSession();
      dashboard.set({
        profile: { name: "-", power: 0, miners: 0 },
        task: { current: "idle", progress: 0, total: 0, elapsed: 0, status: "idle" },
      });
      dashboard.resume();
      log("Launching bot...", "i");

      try {
        const prof = await getProfile();
        if (!prof) {
          log("Login failed. Token expired?", "er");
          await sleep(2000);
        } else {
          dashboard.setProfile({
            name: prof.name || prof.email || "User",
            power: prof.max_total_power || 0,
            miners: prof.user_miners_amount || 0,
          });
          log(`Welcome ${prof.name || prof.email || "User"} | Miners: ${prof.user_miners_amount || "?"} | Power: ${prof.max_total_power || "?"}`, "ok");
          if (cfg.hamster) await hamster();
          if (cfg.game) await playGame(cfg);
          if (cfg.merge) await merge();
        }
      } catch (e) {
        log("Error: " + e.message, "er");
        await sleep(2000);
      } finally {
        dashboard.pause();
      }
      continue;
    }

    if (choice === "2") {
      dashboard.pause();
      clear();
      console.log(`${N_WHITE}${BOLD}🔑 Bearer Setup${RST}`);
      console.log(`${N_GRAY}Current:${RST} ${cfg.access_token ? N_GREEN + cfg.access_token.slice(0, 30) + "..." : N_RED + "not set"}${RST}`);
      const c = (await ask(`\n  ${N_YELLOW}▸${RST} ${N_WHITE}Bearer${RST} : `)).trim();
      if (c) { cfg.access_token = c; saveConfig(cfg); accessToken = c; log("Bearer saved.", "ok"); }
      else log("Cancelled.", "wr");
      await sleep(800);
      continue;
    }

    if (choice === "3") {
      dashboard.pause();
      clear();
      console.log(`${N_WHITE}${BOLD}🔑 Access Token Setup${RST}`);
      console.log(`${N_GRAY}Current:${RST} ${cfg.access_token ? N_GREEN + cfg.access_token.slice(0, 30) + "..." : N_RED + "not set"}${RST}`);
      const at = (await ask(`\n  ${N_YELLOW}▸${RST} ${N_WHITE}Access Token${RST} : `)).trim();
      if (at) {
        cfg.access_token = at; accessToken = at;
        const rt = (await ask(`  ${N_YELLOW}▸${RST} ${N_WHITE}Refresh Token${RST} : `)).trim();
        if (rt) { cfg.refresh_token = rt; refreshToken = rt; }
        const cs = (await ask(`  ${N_YELLOW}▸${RST} ${N_WHITE}CSRF Token${RST} : `)).trim();
        if (cs) { cfg.csrf_token = cs; csrfToken = cs; }
        saveConfig(cfg);
        log("Tokens saved.", "ok");
      } else log("Cancelled.", "wr");
      await sleep(800);
      continue;
    }

    if (choice === "4") {
      dashboard.pause();
      clear();
      console.log(`${N_WHITE}${BOLD}🛠  User-Agent Setup${RST}`);
      console.log(`${N_GRAY}Current:${RST} ${cfg.userAgent ? N_GREEN + cfg.userAgent : N_RED + "not set"}${RST}`);
      const ua = (await ask(`\n  ${N_YELLOW}▸${RST} ${N_WHITE}User Agent${RST} : `)).trim();
      if (ua) { cfg.userAgent = ua; userAgent = ua; saveConfig(cfg); log("User-Agent updated.", "ok"); }
      else log("Cancelled.", "wr");
      await sleep(800);
      continue;
    }

    log("Invalid choice.", "er");
    await sleep(1000);
  }
}

main().catch(e => {
  process.stdout.write("\x1b[?25h");
  console.log(`${RED}Fatal: ${e.message}${RST}`);
  process.exit(1);
});
