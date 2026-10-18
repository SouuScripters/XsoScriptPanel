#!/usr/bin/env node
'use strict';

const fs       = require('fs');
const path     = require('path');
const https    = require('https');
const http     = require('http');
const readline = require('readline');
const crypto   = require('crypto');
const os       = require('os');

const RED  = "\x1b[38;5;203m";
const GRN  = "\x1b[38;5;114m";
const YEL  = "\x1b[38;5;179m";
const BLU  = "\x1b[38;5;39m";
const MAG  = "\x1b[38;5;170m";
const CYN  = "\x1b[38;5;39m";
const WHT  = "\x1b[38;5;255m";
const ABU  = "\x1b[38;5;245m";
const ORG  = "\x1b[38;5;208m";
const RST  = "\x1b[0m";
const CLR  = "\r\x1b[2K";
const BG_MERAH = "\x1b[41m";

const ANSI_REGEX = /\x1b\[[0-9;]*m/g;
const vlen = (s) => s.replace(ANSI_REGEX, '').length;
const pad  = (s, n) => s + ' '.repeat(Math.max(0, n - vlen(s)));
const INNER = 47;

function boxTop(label, color) {
  const prefix = '┌───' + label;
  const dashes = '─'.repeat(Math.max(0, INNER + 2 - vlen(prefix) - 1));
  return `${color}${prefix}${dashes}┐${RST}`;
}
function boxMid(c, color) { return `${color}│${RST}${pad(c, INNER)}${color}│${RST}`; }
function boxBot(color)     { return `${color}└${'─'.repeat(INNER)}┘${RST}`; }
function headerTop(c)      { return `${c}╭${'─'.repeat(INNER)}╮${RST}`; }
function headerMid(c, col) { return `${col}│${RST}${pad(c, INNER)}${col}│${RST}`; }
function headerBot(c)      { return `${c}╰${'─'.repeat(INNER)}╯${RST}`; }

const HOST        = 'https://viefaucet.com';
const SOLVER_HOST = 'api.waryono.my.id';
const SALT        = 'd!tc0nmeth@ngn@0h@ckt@o';
const CONFIG_PATH = path.join(__dirname, 'config.json');
const VIE_VERSION = '1.1.0';
const TZ_HEADER   = 'Asia/Jakarta';

const OWNER_KEY    = "iyannn402";
const LICENSE_DAYS = 7;
const LICENSE_PATH = path.join(os.tmpdir(), ".license.json");

const SHORTLINK_POOL = [
  { url: "https://fc-lc.xyz/EdwDPGb",  code: "IYAN-R4T7-92KM" },
  { url: "https://fc-lc.xyz/GqdqKlKL", code: "IYAN-W8Q2-45PX" },
  { url: "https://fc-lc.xyz/NFMnLF",   code: "IYAN-Y1N6-73LB" },
  { url: "https://fc-lc.xyz/iPUW",     code: "IYAN-A5M3-86HC" },
  { url: "https://fc-lc.xyz/G7rda",    code: "IYAN-C9K7-29JD" },
  { url: "https://fc-lc.xyz/BJ94XMoA", code: "IYAN-E2J4-57NF" },
  { url: "https://fc-lc.xyz/7v8s8",    code: "IYAN-G6H8-31RW" },
  { url: "https://fc-lc.xyz/tbMmvh",   code: "IYAN-J3F1-94QV" },
  { url: "https://fc-lc.xyz/08VP",     code: "IYAN-L7D5-62TB" },
  { url: "https://fc-lc.xyz/dq4JWe",   code: "IYAN-N1C9-48XM" },
  { url: "https://fc-lc.xyz/aUJcu8gG", code: "IYAN-P5B3-75KP" },
  { url: "https://fc-lc.xyz/gEuriV",   code: "IYAN-R9A7-23FN" },
  { url: "https://fc-lc.xyz/ZM1Lihs",  code: "IYAN-T4Z2-86LH" },
  { url: "https://fc-lc.xyz/vek9Q",    code: "IYAN-V8Y6-51CJ" },
  { url: "https://fc-lc.xyz/csIdhTZI", code: "IYAN-X2W1-97DM" },
  { url: "https://fc-lc.xyz/gXMs",     code: "IYAN-Z6V5-34BR" },
  { url: "https://fc-lc.xyz/yR0xNQ",   code: "IYAN-B3U9-72GN" },
  { url: "https://fc-lc.xyz/gokTX8Y",  code: "IYAN-D7T4-15HQ" },
  { url: "https://fc-lc.xyz/g8vntJ",   code: "IYAN-F1S8-69KX" },
  { url: "https://fc-lc.xyz/6gJdim",   code: "IYAN-H5R2-83PV" },
];

const PROVIDERS = {
  skibidixxx: {
    id: "skibidixxx",
    name: "Skibidixxx",
    host: "api.waryono.my.id",
    proto: "https",
    methods: "upsidedown_3",
    available: true
  }
};

const UA_POOL = [
  'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 13; SM-A536E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 11; moto g power) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'
];

const VERIFY_DELAY_MIN = 5;
const VERIFY_DELAY_MAX = 12;
const WAIT_DELAY_MIN   = 30;
const WAIT_DELAY_MAX   = 75;
const SAFE_MODE = true;
const MAX_CLAIMS_PER_SESSION = 40;
const SESSION_BREAK_MIN = 20 * 60;
const SESSION_BREAK_MAX = 35 * 60;
const EMPTY_ROUNDS_BEFORE_LONG_BREAK = 3;
const WARMUP_MIN = 10;
const WARMUP_MAX = 45;
const HOME_NAV_CHANCE = 0.08;
const DISTRACTION_CHANCE = 0.03;
const DISTRACTION_MIN = 60;
const DISTRACTION_MAX = 180;
const MACRO_BREAK_CHANCE = 0.12;
const MACRO_BREAK_MIN = 5 * 60;
const MACRO_BREAK_MAX = 12 * 60;
const NIGHT_START = 0;
const NIGHT_END = 6;
const NIGHT_BREAK_MIN = 30 * 60;
const NIGHT_BREAK_MAX = 90 * 60;

let STOP_SIGNAL = false;
let PROVIDER    = "";
let API_KEY     = "";
let CURRENT_UA  = "";
let SESSION_BEARER = "";
let SESSION_COOKIE = "";

const SYMBOLS   = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑'];
const SPINNERS  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾'];
const SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯'];
const DOTS      = ['▪', '▪▪', '▪▪▪', '▪▪▪▪'];

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function ts() {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0')).join(':');
}

function clear() { process.stdout.write('\x1b[2J\x1b[3J\x1b[H'); }

function log(msg, tag = "i") {
  const icons = {
    i: `${CYN}»${RST}`, ok: `${GRN}✓${RST}`, er: `${RED}✗${RST}`,
    wr: `${RED}⚠${RST}`, in: `${BLU}●${RST}`, dbg: `${MAG}⚙${RST}`, or: `${ORG}●${RST}`
  };
  const icon = icons[tag] || `${CYN}»${RST}`;
  const color = (tag === 'wr' || tag === 'er') ? RED : WHT;
  process.stdout.write(CLR + `${WHT}[${ts()}]${RST} ${icon} ${color}${msg}${RST}\n`);
}

async function blinkRaw(prefix, color, message, duration, caps = false) {
  const text = caps ? String(message).toUpperCase() : String(message);
  const start = Date.now();
  const tick = 250;
  let on = true;
  while (Date.now() - start < duration) {
    if (STOP_SIGNAL) break;
    if (on) process.stdout.write(CLR + `${color}[${ts()}] ${prefix} ${text}${RST}`);
    else    process.stdout.write(CLR);
    on = !on;
    await sleep(tick);
  }
  process.stdout.write(CLR);
}
const blinkErr  = (msg, d = 2000) => blinkRaw("✗", RED, msg, d, true);
const blinkWarn = (msg, d = 2000) => blinkRaw("⚠", RED, msg, d, false);

function askQuestion(q) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => rl.question(q, a => { rl.close(); res(a); }));
}

async function spinnerLoop(label, mode, targetSec, stopSignal) {
  const start = Date.now();
  let i = 0;
  while (!stopSignal.value && !STOP_SIGNAL) {
    const elapsedSec = Math.floor((Date.now() - start) / 1000);
    let displaySec, pct;
    if (mode === "countdown") {
      displaySec = Math.max(0, targetSec - elapsedSec);
      pct = targetSec > 0 ? Math.round(((targetSec - displaySec) / targetSec) * 100) : 0;
    } else {
      displaySec = elapsedSec;
      pct = targetSec > 0 ? Math.min(100, Math.round((elapsedSec / targetSec) * 100)) : 0;
    }
    const mm = String(Math.floor(displaySec / 60)).padStart(2, "0");
    const ss = String(displaySec % 60).padStart(2, "0");
    const sym = SYMBOLS[i % SYMBOLS.length];
    const sp  = SPINNERS[i % SPINNERS.length];
    const sp1 = SPINNERS1[i % SPINNERS1.length];
    const dot = DOTS[elapsedSec % DOTS.length];
    i++;
    const c1 = 1 + Math.floor(Math.random() * 7);
    const c2 = 1 + Math.floor(Math.random() * 7);
    process.stdout.write(
      `${CLR} \x1b[1;3${c1}m ${sp}\x1b[1;37m ${label} ` +
      `\x1b[1;31m${mm}:${ss}\x1b[1;3${c2}m ${sym} ${sp1}` +
      `\x1b[1;37m ${pct}%\x1b[1;33m ${dot}`
    );
    await sleep(100);
  }
  process.stdout.write(CLR);
}

function spawnSpinner(label, mode, targetSec) {
  const sig = { value: false };
  const p = spinnerLoop(label, mode, targetSec, sig);
  return { stop: async () => { sig.value = true; try { await p; } catch {} } };
}

async function tmr(seconds, label = "Waiting...") {
  const total = Math.floor(seconds);
  if (total < 1) return;
  const sp = spawnSpinner(label, "countdown", total);
  const start = Date.now();
  while (!STOP_SIGNAL && (Date.now() - start) / 1000 < total) await sleep(100);
  await sp.stop();
}

function getMachineId() {
  let user = "unknown";
  try { user = os.userInfo().username; } catch {}
  const raw = `${os.hostname()}|${user}|${process.platform}|${os.arch()}`;
  return crypto.createHash("sha256").update(raw).digest("hex").slice(0, 20);
}

function loadLicense() {
  if (!fs.existsSync(LICENSE_PATH)) return null;
  try {
    const d = JSON.parse(fs.readFileSync(LICENSE_PATH, "utf-8"));
    if (d.type === "owner") return d;
    if (d.machine !== getMachineId()) return null;
    if (new Date(d.expired_at) <= new Date()) { try { fs.unlinkSync(LICENSE_PATH); } catch {} return null; }
    return d;
  } catch { return null; }
}

function saveLicense(kind) {
  let d;
  if (kind === "owner") d = { type: "owner", machine: getMachineId(), expired_at: "PERMANENT", created_at: new Date().toISOString() };
  else {
    const exp = new Date(Date.now() + LICENSE_DAYS * 86400000);
    d = { type: "user", machine: getMachineId(), expired_at: exp.toISOString(), created_at: new Date().toISOString() };
  }
  try { fs.writeFileSync(LICENSE_PATH, JSON.stringify(d, null, 2)); } catch {}
  return d;
}

function sisaWaktu(exp) {
  try {
    const delta = new Date(exp) - new Date();
    if (delta <= 0) return "EXPIRED";
    const h = Math.floor(delta / 86400000);
    const j = Math.floor((delta % 86400000) / 3600000);
    const m = Math.floor((delta % 3600000) / 60000);
    if (h > 0) return `${h} days ${j} hours left`;
    if (j > 0) return `${j} hours ${m} minutes left`;
    return `${m} minutes left`;
  } catch { return "Unknown"; }
}

function bannerMain() {
  console.log(headerTop(CYN));
  console.log(headerMid(`  ${BG_MERAH}${WHT} KUYANGIN DONG ${RST}`, CYN));
  console.log(headerBot(CYN));
  console.log("");
}

async function verifyLicense() {
  const saved = loadLicense();
  if (saved) {
    if (saved.type === "owner") {
      clear(); bannerMain();
      console.log(`${YEL}  👑 OWNER MODE — Permanent access.${RST}`);
      await sleep(1000); return true;
    }
    clear(); bannerMain();
    console.log(`${GRN}  ✅ License active — expires in ${sisaWaktu(saved.expired_at)}${RST}`);
    await sleep(1000); return true;
  }

  clear();
  console.log(`${WHT}═══════════════════════════════════════════════${RST}`);
  console.log(`${YEL}         🔐 LICENSE VERIFICATION${RST}`);
  console.log(`${WHT}═══════════════════════════════════════════════${RST}\n`);

  const picked = SHORTLINK_POOL[Math.floor(Math.random() * SHORTLINK_POOL.length)];
  console.log(`${YEL}  ⚠  This script requires license verification.${RST}\n`);
  console.log(`${CYN}  Open the following shortlink in your browser:${RST}`);
  console.log(`     👉  ${GRN}${picked.url}${RST}\n`);
  console.log(`${WHT}───────────────────────────────────────────────${RST}\n`);

  for (let i = 1; i <= 3; i++) {
    const code = (await askQuestion(`${YEL}  ❯ Enter code [${i}/3]: ${GRN}`)).trim();
    if (code === OWNER_KEY) {
      saveLicense("owner"); clear(); bannerMain();
      console.log(`${YEL}  👑 Owner detected. PERMANENT access.${RST}`);
      await sleep(1500); return true;
    }
    if (code.toUpperCase() === picked.code.toUpperCase()) {
      saveLicense("user"); clear(); bannerMain();
      console.log(`${GRN}  ✅ Verification successful! Active for ${LICENSE_DAYS} days.${RST}`);
      await sleep(1500); return true;
    }
    await blinkErr(`Invalid code! Attempts remaining: ${3 - i}`, 1500);
  }
  await blinkErr("Verification failed. Exiting...", 2500);
  return false;
}

function rawRequest(method, urlStr, headers, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const lib = url.protocol === 'http:' ? http : https;
    const hdrs = { ...headers };
    if (body != null && !hdrs['Content-Length'] && !hdrs['content-length']) {
      hdrs['Content-Length'] = Buffer.byteLength(body);
    }
    const req = lib.request({
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: url.pathname + url.search,
      method, headers: hdrs
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({
        status: res.statusCode, headers: res.headers,
        body: Buffer.concat(chunks).toString('utf-8')
      }));
    });
    req.on('error', reject);
    req.setTimeout(120000, () => req.destroy(new Error('Request timeout')));
    if (body != null) req.write(body);
    req.end();
  });
}

const LOGIN_ENDPOINT = `${HOST}/api/auth/login`;

function loginHeaders() {
  const chromeVer = (CURRENT_UA.match(/Chrome\/(\d+)/) || [,'137'])[1];
  return {
    'Content-Type': 'application/json',
    'user-agent': CURRENT_UA || UA_POOL[0],
    'vie-version': VIE_VERSION,
    'tz': TZ_HEADER,
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'sec-ch-ua': `"Chromium";v="${chromeVer}", "Not/A)Brand";v="24"`,
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'origin': HOST,
    'referer': `${HOST}/`,
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty'
  };
}

function loginBody(email, password, captchaInner, captchaId) {
  return JSON.stringify({
    email,
    password,
    captcha: {
      type: 'rocket-captcha',
      token: captchaInner,
      id: captchaId
    }
  });
}

function buildLoginCaptcha(captchaId, x, y, width, height) {
  const percentX = Math.floor((x / width) * 100);
  const percentY = Math.floor((y / height) * 100);
  return Buffer.from(JSON.stringify({
    percentX, percentY, id: captchaId, x, y
  })).toString('base64');
}

function extractToken(j) {
  if (!j) return null;
  if (typeof j === 'string') return j;
  return j.token || j.access_token || j.accessToken || j.bearer || j.jwt
      || (j.data && (j.data.token || j.data.access_token || j.data.accessToken))
      || null;
}

async function getLoginCaptcha() {
  const r = await rawRequest('GET', `${HOST}/api/ct`, {
    'vie-version': VIE_VERSION,
    'user-agent': CURRENT_UA || UA_POOL[0],
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'referer': `${HOST}/`,
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"'
  });
  const j = JSON.parse(r.body);
  const parts = String(j.captcha).split(',');
  return {
    base_img: j.captcha,
    captcha_id: j.id,
    width: j.width,
    height: j.height,
    img: parts[1]
  };
}

async function doLogin(email, password) {
  if (!CURRENT_UA)   return { ok: false, reason: 'User-Agent not set' };
  if (!email || !password) return { ok: false, reason: 'Email/password empty' };
  if (!API_KEY)      return { ok: false, reason: 'Solver apikey empty' };

  while (!STOP_SIGNAL) {
    let ct;
    try {
      ct = await getLoginCaptcha();
    } catch (e) {
      if (STOP_SIGNAL) return { ok: false, reason: 'Stopped' };
      await sleep(3000);
      continue;
    }

    const bypass = await solveUpsideDown(ct.img, API_KEY);
    
    if (!bypass || typeof bypass !== 'object' || Array.isArray(bypass)) {
      if (Array.isArray(bypass) && bypass[0] === 'STOPPED') return { ok: false, reason: 'Stopped' };
      await sleep(3000);
      continue;
    }

    const inner = buildLoginCaptcha(ct.captcha_id, bypass.x, bypass.y, ct.width, ct.height);
    const body  = loginBody(email, password, inner, ct.captcha_id);

    let res;
    try {
      res = await rawRequest('POST', LOGIN_ENDPOINT, loginHeaders(), body);
    } catch (e) {
      if (STOP_SIGNAL) return { ok: false, reason: 'Stopped' };
      await sleep(3000);
      continue;
    }

    let j; try { j = JSON.parse(res.body); } catch { j = null; }
    const token = extractToken(j);
    
    let cookieStr = "";
    if (res.headers['set-cookie']) {
      const cookieArr = Array.isArray(res.headers['set-cookie']) ? res.headers['set-cookie'] : [res.headers['set-cookie']];
      const authTokenCookie = cookieArr.find(c => c.startsWith('authToken='));
      if (authTokenCookie) {
        cookieStr = authTokenCookie.split(';')[0];
      }
    }

    if (token) return { ok: true, token, cookie: cookieStr, expiredAt: j && j.accessTokenExpiredAt };

    const msg = (j && (j.msg || j.message || j.error)) || `HTTP ${res.status}`;
    
    if (String(msg).toLowerCase().includes('captcha')) {
      await blinkErr(msg, 2000);
      await sleep(3000);
      continue;
    }

    return { ok: false, reason: msg, raw: res.body.slice(0, 300) };
  }
  
  return { ok: false, reason: 'Stopped' };
}

const FATAL_ERRORS = [
  'ERROR_WRONG_METHOD','ERROR_KEY_DOES_NOT_EXIST','ERROR_METHOD_NOT_SPECIFIED',
  'ERROR_NO_SUCH_METHOD','ERROR_DATABASE_CONNECTION_FAILED','ERROR_WRONG_USER_KEY',
  'ERROR_ZERO_BALANCE','ERROR_BAD_PARAMETERS','ERROR_EMPTY_IMAGE','ERROR_UNKNOWN'
];
const SOFT_ERRORS = [
  'WRONG_CAPTCHA_ID','ERROR_SOLVE_PENDING','ERROR_CAPTCHA_UNSOLVABLE','INTENAL_SERVER_ERROR'
];

function solverRequest(pathname, params = {}, method = 'POST', bodyObj = null) {
  return new Promise((resolve, reject) => {
    const query = new URLSearchParams(params).toString();
    const fullPath = query ? `${pathname}?${query}` : pathname;
    const body = bodyObj ? JSON.stringify(bodyObj) : null;
    const headers = { 'User-Agent': CURRENT_UA || UA_POOL[0], 'Accept': 'application/json' };
    if (body) {
      headers['Content-Type'] = 'application/json';
      headers['Content-Length'] = Buffer.byteLength(body);
    }
    const req = https.request({
      hostname: SOLVER_HOST, port: 443, path: fullPath, method, headers
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf-8');
        let data; try { data = JSON.parse(text); } catch { data = { status: 0, request: text }; }
        resolve({ http: res.statusCode, text, data });
      });
    });
    req.on('error', reject);
    req.setTimeout(60000, () => req.destroy(new Error('Solver timeout')));
    if (body) req.write(body);
    req.end();
  });
}

async function solveUpsideDown(base64, apikey) {
  const spinner = spawnSpinner('Upsidedown', 'countup', 180);
  try {
    const submit = await solverRequest('/in.php', {}, 'POST', {
      apikey, methods: 'upsidedown_3', base64_str: base64, json: 1
    });
    
    for (const err of FATAL_ERRORS) {
      if (submit.text.includes(err)) {
        await spinner.stop();
        await blinkErr(err, 2000);
        process.exit(1);
      }
    }
    
    if (submit.text.includes('ERROR_TOO_MANY_REQUESTS')) {
      await spinner.stop();
      await blinkErr('ERROR_TOO_MANY_REQUESTS', 2000);
      await sleep(2000);
      return ['ERROR_TOO_MANY_REQUESTS'];
    }
    
    const task = submit.data || {};
    if (task.status !== 1 || !task.request) {
      await spinner.stop();
      return ['ERROR_SUBMIT'];
    }
    
    const id = task.request;
    while (true) {
      if (STOP_SIGNAL) { await spinner.stop(); return ['STOPPED']; }
      await sleep(1000);
      const poll = await solverRequest('/res.php', { apikey, id, action: 'get', json: 1 }, 'GET');
      
      for (const err of ['ERROR_BAD_PARAMETERS','ERROR_BAD_REQUEST']) {
        if (poll.text.includes(err)) { 
          await spinner.stop(); 
          await blinkErr(err, 2000);
          process.exit(1); 
        }
      }
      
      for (const err of SOFT_ERRORS) {
        if (poll.text.includes(err)) { 
          await spinner.stop(); 
          return [err]; 
        }
      }
      
      if (poll.text.includes('CAPCHA_NOT_READY')) continue;
      const res = (poll.data && poll.data.request) || '';
      const m = String(res).match(/x:(\d+),y:(\d+)/);
      if (m) { await spinner.stop(); return { x: parseInt(m[1], 10), y: parseInt(m[2], 10) }; }
    }
  } catch (e) {
    await spinner.stop();
    return ['ERROR_SOLVE:' + e.message];
  }
}

function baseHeaders(referer, isPost = false) {
  const chromeVer = (CURRENT_UA.match(/Chrome\/(\d+)/) || [,'137'])[1];
  const h = {
    'authorization': `Bearer ${SESSION_BEARER}`,
    'vie-version': VIE_VERSION,
    'user-agent': CURRENT_UA || UA_POOL[0],
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'sec-ch-ua': `"Chromium";v="${chromeVer}", "Not/A)Brand";v="24"`,
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'priority': 'u=1, i',
    'referer': referer || `${HOST}/app/wait`
  };
  
  if (SESSION_COOKIE) {
    h['cookie'] = SESSION_COOKIE;
  }
  
  if (isPost) { h['content-type'] = 'application/json'; h['origin'] = HOST; }
  else { h['cache-control'] = 'no-cache'; h['pragma'] = 'no-cache'; }
  return h;
}

function microDelay() { return sleep(400 + Math.floor(Math.random() * 1600)); }

async function apiGet(url, referer) {
  await microDelay();
  const r = await rawRequest('GET', url, baseHeaders(referer, false));
  return r.body;
}

async function apiPost(url, body, referer) {
  const r = await rawRequest('POST', url, baseHeaders(referer, true), body);
  return r.body;
}

function tokenAds(adId) {
  return crypto.createHash('md5').update(adId + SALT).digest('hex');
}

async function getAccount() {
  try {
    const body = await apiGet(`${HOST}/api/user/me`, `${HOST}/app/dashboard`);
    let j; try { j = JSON.parse(body); } catch { j = null; }
    if (body.includes('username') && j && j.user && j.user.username != null && j.user.balance != null) {
      return { ok: true, user: j.user.username, balance: j.user.balance };
    }
    if (j && j.msg) return { ok: false, reason: j.msg };
    return { ok: false, reason: 'Bearer expired / unauthorized' };
  } catch (e) {
    return { ok: false, reason: e.message };
  }
}

async function getPtCaptcha(referer) {
  const ct = await apiGet(`${HOST}/api/ct`, referer);
  const j = JSON.parse(ct);
  const parts = String(j.captcha).split(',');
  return { base_img: j.captcha, captcha_id: j.id, width: j.width, height: j.height, img: parts[1] };
}

function buildPayload(adId, captchaId, x, y, width, height) {
  const percentX = Math.floor((x / width) * 100);
  const percentY = Math.floor((y / height) * 100);
  const inner = Buffer.from(JSON.stringify({ percentX, percentY, id: captchaId, x, y })).toString('base64');
  return JSON.stringify({
    captcha: { type: 'rocket-captcha', token: inner, id: captchaId },
    token: tokenAds(adId)
  });
}

function jitter(min, max) {
  const t = (Math.random() + Math.random()) / 2;
  return min + Math.floor(t * (max - min + 1));
}
const chance = (p) => Math.random() < p;
function isNightTime() { const h = new Date().getHours(); return h >= NIGHT_START && h < NIGHT_END; }

async function delayVerify() { await tmr(jitter(VERIFY_DELAY_MIN, VERIFY_DELAY_MAX), 'Verify...'); }
async function delayWait()   { await tmr(jitter(WAIT_DELAY_MIN, WAIT_DELAY_MAX), 'Waiting...'); }
async function warmup()      { await tmr(jitter(WARMUP_MIN, WARMUP_MAX), 'Warmup...'); }

async function maybeDistraction() {
  if (!chance(DISTRACTION_CHANCE)) return false;
  log('Taking a short break...', 'wr');
  await tmr(jitter(DISTRACTION_MIN, DISTRACTION_MAX), 'Paused...');
  return true;
}
async function maybeMacroBreak() {
  if (!chance(MACRO_BREAK_CHANCE)) return false;
  const s = jitter(MACRO_BREAK_MIN, MACRO_BREAK_MAX);
  log(`Resting for a bit (${Math.floor(s/60)} minutes)`, 'i');
  await tmr(s, 'Break...');
  return true;
}
async function maybeNightBreak() {
  if (!isNightTime()) return false;
  const s = jitter(NIGHT_BREAK_MIN, NIGHT_BREAK_MAX);
  log(`Sleep time. Resting for ${Math.floor(s/60)} minutes`, 'wr');
  await tmr(s, 'Sleep...');
  return true;
}
async function longBreak(reason) {
  const s = jitter(SESSION_BREAK_MIN, SESSION_BREAK_MAX);
  log(reason, 'wr');
  log(`Resting for ${Math.floor(s/60)} minutes to keep the account safe...`, 'i');
  await tmr(s, 'Rest...');
}
async function goHome() { try { await apiGet(`${HOST}/app/wait`, `${HOST}/app/wait`); } catch {} }

function shuffleSpread(pool) {
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  for (let i = 2; i < pool.length; i++) {
    const t0 = pool[i-2].ad.type, t1 = pool[i-1].ad.type, t2 = pool[i].ad.type;
    if (t0 === t1 && t1 === t2) {
      for (let k = i + 1; k < pool.length; k++) {
        if (pool[k].ad.type !== t2) { [pool[i], pool[k]] = [pool[k], pool[i]]; break; }
      }
    }
  }
  return pool;
}

async function processAd(ad, label) {
  if (ad.availableOn) return false;
  const adId = ad._id;
  const watchTimer = ad.timer;
  const typeSlug = ad.type || 'window';
  const referer = `${HOST}/app/ptc/${typeSlug}/${adId}`;

  const viewBody = await apiGet(`${HOST}/api/ptc/${adId}/view`, referer);
  let vj = null; try { vj = JSON.parse(viewBody); } catch {}
  if (vj && vj.viewable === false) {
    console.log(`${WHT}[${ts()}]${RST} ${YEL}⚠${RST} ${YEL}${label} not viewable${RST}`);
    return false;
  }

  await tmr(watchTimer, `viewing ${label}`);
  const ct = await getPtCaptcha(referer);
  const bypass = await solveUpsideDown(ct.img, API_KEY);
  
  if (!bypass || typeof bypass !== 'object' || Array.isArray(bypass)) {
    return 'skip';
  }

  const payload = buildPayload(adId, ct.captcha_id, bypass.x, bypass.y, ct.width, ct.height);
  await delayVerify();

  const claim = await apiPost(`${HOST}/api/ptc/${adId}/verify`, payload, referer);
  let cj = null; try { cj = JSON.parse(claim); } catch {}

  if (cj && typeof cj.reward === 'number') {
    const msg = cj.msg || `You have claimed ${cj.reward} tokens`;
    console.log(`${WHT}[${ts()}]${RST} ${GRN}✓${RST} ${WHT}${label}${RST} ${ABU}—${RST} ${GRN}${msg}${RST}`);

    const acc = await getAccount();
    if (acc.ok) {
      console.log(`${WHT}[${ts()}]${RST} ${ORG}●${RST} ${YEL}New Balance: ${CYN}${acc.balance}${YEL} tokens${RST}`);
    }
    return true;
  }

  if (cj && (cj.msg || '').toLowerCase().includes('invalid')) {
    console.log(`${WHT}[${ts()}]${RST} ${RED}✗${RST} ${RED}${cj.msg || 'Invalid'}${RST}`);
    return false;
  }

  console.log(`${WHT}[${ts()}]${RST} ${YEL}⚠${RST} ${YEL}${String(claim).slice(0, 200)}${RST}`);
  return 'retry';
}

async function runFaucet(cfg) {
  STOP_SIGNAL = false;

  if (!SESSION_BEARER) {
    log('Logging in via email/password...', 'i');
    const r = await doLogin(cfg.email, cfg.password);
    if (!r.ok) {
      if (r.reason === 'Stopped') return;
      await blinkErr(`Login failed: ${r.reason}`, 2500);
      if (r.raw) console.log(`${ABU}${r.raw}${RST}`);
      await askQuestion(`\n${WHT}  Press Enter to return to menu...${RST}`);
      return;
    }
    SESSION_BEARER = r.token;
    SESSION_COOKIE = r.cookie || "";
    log('Login successful.', 'ok');
  } else {
    log('Using existing session...', 'i');
  }

  let akun = await getAccount();
  
  if (!akun.ok && SESSION_BEARER) {
    log('Session expired. Relogging in...', 'wr');
    SESSION_BEARER = '';
    SESSION_COOKIE = '';
    const r = await doLogin(cfg.email, cfg.password);
    if (!r.ok) {
      if (r.reason === 'Stopped') return;
      await blinkErr(`Login failed: ${r.reason}`, 2500);
      if (r.raw) console.log(`${ABU}${r.raw}${RST}`);
      await askQuestion(`\n${WHT}  Press Enter to return to menu...${RST}`);
      return;
    }
    SESSION_BEARER = r.token;
    SESSION_COOKIE = r.cookie || "";
    akun = await getAccount();
  }

  if (!akun.ok) {
    await blinkErr(`Session invalid: ${akun.reason}`, 2500);
    await askQuestion(`\n${WHT}  Press Enter to return to menu...${RST}`);
    return;
  }

  log(`Logged in as ${akun.user}`, 'ok');
  log(`Balance: ${akun.balance} tokens`, 'or');
  console.log('');

  await warmup();

  const types = { window: 'Window Mission', iframe: 'Iframe Mission', youtube: 'YT Mission' };
  let emptyRounds = 0;
  let sessionClaims = 0;

  while (!STOP_SIGNAL) {
    if (await maybeNightBreak()) continue;

    const pool = [];
    for (const [type, label] of Object.entries(types)) {
      let ptc;
      try { ptc = await apiGet(`${HOST}/api/ptc?type=${type}`, `${HOST}/app/ptc/${type}`); }
      catch { continue; }
      let j; try { j = JSON.parse(ptc); } catch { j = null; }
      if (!j || !Array.isArray(j.ads) || j.ads.length === 0) continue;
      for (const ad of j.ads) pool.push({ ad, label });
    }

    if (pool.length === 0) {
      emptyRounds++;
      log('No PTC available from server', 'wr');
      if (SAFE_MODE && emptyRounds >= EMPTY_ROUNDS_BEFORE_LONG_BREAK) {
        await longBreak('3 empty rounds in a row.');
        emptyRounds = 0;
      } else await tmr(120, 'idle');
      continue;
    }
    emptyRounds = 0;

    const ordered = shuffleSpread(pool);
    log(`Processing ${ordered.length} ads this round`, 'i');

    let anyAd = false, doRetry = false, needBearer = false;
    let claimed = 0, skipped = 0;

    for (const item of ordered) {
      if (STOP_SIGNAL) break;

      if (SAFE_MODE && chance(HOME_NAV_CHANCE)) await goHome();
      if (SAFE_MODE) await maybeDistraction();

      let result;
      try {
        result = await processAd(item.ad, item.label);
      } catch (e) {
        const m = String(e.message || '').toLowerCase();
        if (m.includes('expired') || m.includes('invalid') || m.includes('unauthor') || m.includes('401')) {
          needBearer = true; break;
        }
        log(`Error: ${e.message}`, 'er');
        doRetry = true; break;
      }

      if (result === 'skip') {
        skipped++;
        await sleep(3000);
        continue;
      }

      if (result === 'retry') {
        const chk = await getAccount();
        if (!chk.ok) { needBearer = true; break; }
        await sleep(5000); doRetry = true; break;
      }
      
      if (result === true) {
        anyAd = true; claimed++; sessionClaims++;
        if (SAFE_MODE && sessionClaims >= MAX_CLAIMS_PER_SESSION) {
          console.log('');
          await longBreak(`Session reached ${sessionClaims} claims.`);
          sessionClaims = 0;
        }
      }
      if (result === false) skipped++;

      await delayWait();
    }

    if (STOP_SIGNAL) break;

    if (needBearer) {
      log('Bearer expired during process. Relogging in...', 'wr');
      SESSION_BEARER = '';
      SESSION_COOKIE = '';
      const r2 = await doLogin(cfg.email, cfg.password);
      if (!r2.ok) {
        if (r2.reason === 'Stopped') break;
        await blinkErr(`Relogin failed: ${r2.reason}`, 2500);
        break;
      }
      SESSION_BEARER = r2.token;
      SESSION_COOKIE = r2.cookie || "";
      log('Relogin successful.', 'ok');
      continue;
    }

    if (doRetry) continue;

    log(`Round finished — ${claimed} claimed, ${skipped} skipped/invalid`, 'i');
    if (SAFE_MODE) await maybeMacroBreak();
    if (!anyAd) {
      log('No ads successfully claimed this round', 'wr');
      await tmr(120, 'idle');
    }
  }

  console.log('');
  await blinkWarn('Faucet loop stopped.', 1500);
}

function defaultConfig() {
  return { email: "", password: "", userAgent: "", provider: "", apikeys: {} };
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) return defaultConfig();
  try {
    const c = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    if (!c.apikeys) c.apikeys = {};
    if (!c.email) c.email = '';
    if (!c.password) c.password = '';
    if (!c.userAgent) c.userAgent = '';
    if (typeof c.provider !== 'string') c.provider = '';
    if (c.bearer) { delete c.bearer; }
    return c;
  } catch { return defaultConfig(); }
}

function saveConfig(cfg) {
  try {
    const clean = { ...cfg };
    delete clean.bearer;
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(clean, null, 2));
  } catch {}
}

function getApiKey(provider) {
  const c = loadConfig();
  return (c.apikeys && c.apikeys[provider]) || '';
}

function setApiKey(provider, key) {
  const c = loadConfig();
  c.apikeys[provider] = key;
  if (!c.provider) c.provider = provider;
  saveConfig(c);
}

function maskKey(k) { return k && k.length > 12 ? k.slice(0, 8) + '...' + k.slice(-4) : k; }

function tampilkanMenu(cfg, licInfo) {
  clear();
  console.log(headerTop(CYN));
  console.log(headerMid(`  ${BG_MERAH}${WHT} KUYANGIN DONG ${RST}`, CYN));
  console.log(headerBot(CYN));

  console.log(`  ${YEL}▸${RST} ${WHT}Channel      ${RST}: ${GRN}@bijikelot_v5${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Creator      ${RST}: ${GRN}iyannn${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Version      ${RST}: ${GRN}Ceban${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Status       ${RST}: ${GRN}Ngopi Dong${RST}`);
  console.log("");
  console.log(`  ${CYN}◉${RST} ${ABU}Site ${RST}: ${CYN}${HOST}${RST}`);

  const uaDisp = cfg.userAgent
    ? `${GRN}${cfg.userAgent}${RST}`
    : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}User-Agent ${RST}: ${uaDisp}`);

  const emDisp = cfg.email ? `${GRN}${cfg.email}${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Email      ${RST}: ${emDisp}`);

  const pwDisp = cfg.password ? `${GRN}✓ set${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Password   ${RST}: ${pwDisp}`);

  const provDisp = PROVIDER && PROVIDERS[PROVIDER]
    ? `${GRN}${PROVIDERS[PROVIDER].name}${RST}` : `${WHT}-${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Provider   ${RST}: ${provDisp}`);

  const apiDisp = API_KEY ? `${GRN}${maskKey(API_KEY)}${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Apikey     ${RST}: ${apiDisp}`);

  console.log("");
  console.log(boxTop('[ MENU ]', CYN));
  console.log(boxMid(`  ${YEL}[1]${RST} ${WHT}Start Faucet${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[2]${RST} ${WHT}Set Email / Password${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[3]${RST} ${WHT}Set Provider${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[4]${RST} ${WHT}Set User-Agent${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[0]${RST} ${RED}Exit${RST}`, CYN));
  console.log(boxBot(CYN));
  console.log("");
  console.log(`  ${ABU}[License] ${YEL}${licInfo}${RST}`);
}

async function menuCredentials(cfg) {
  clear(); bannerMain();
  console.log(`${WHT}  🔐 Email / Password${RST}`);
  console.log(`${WHT}  ─────────────────────${RST}\n`);
  console.log(`  ${WHT}Current email:${RST} ${cfg.email ? GRN + cfg.email : RED + 'not set'}${RST}\n`);

  const email = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Email${RST} : `)).trim();
  if (!email) { log('Cancelled.', 'wr'); await sleep(1200); return cfg; }
  const pw = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Password${RST} : `)).trim();
  if (!pw) { log('Cancelled.', 'wr'); await sleep(1200); return cfg; }

  cfg.email = email;
  cfg.password = pw;
  saveConfig(cfg);
  SESSION_BEARER = '';
  SESSION_COOKIE = '';
  log('Credentials saved. Session cleared.', 'ok');
  await sleep(1200);
  return cfg;
}

async function menuProvider() {
  while (true) {
    clear(); bannerMain();
    console.log(`${WHT}  ⚙  Provider Setup${RST}`);
    console.log(`${WHT}  ─────────────────${RST}\n`);
    const cfg = loadConfig();
    const activeId = cfg.provider || '';
    console.log(`  ${WHT}Active:${RST} ${activeId && PROVIDERS[activeId] ? GRN + PROVIDERS[activeId].name : WHT + '-'}${RST}\n`);

    const ids = Object.keys(PROVIDERS);
    ids.forEach((id, i) => {
      const p = PROVIDERS[id];
      const key = (cfg.apikeys && cfg.apikeys[id]) || '';
      const mark = id === activeId ? ` ${GRN}●${RST}` : '  ';
      const kDisp = key ? `${GRN}${maskKey(key)}${RST}` : `${WHT}-${RST}`;
      console.log(`  ${GRN}[${i+1}]${RST}${mark} ${WHT}${p.name.padEnd(14)}${RST} ${kDisp}`);
    });
    console.log(`  ${RED}[0]${RST}  ${WHT}Back${RST}\n`);
    const c = (await askQuestion(`  ${WHT}❯ Select: ${RST}`)).trim();
    if (c === '0') return;
    const idx = parseInt(c, 10);
    if (isNaN(idx) || idx < 1 || idx > ids.length) { log('Invalid option.', 'er'); await sleep(1000); continue; }

    const chosenId = ids[idx - 1];
    const chosen = PROVIDERS[chosenId];
    const cur = (cfg.apikeys && cfg.apikeys[chosenId]) || '';
    console.log('');
    const input = (await askQuestion(`  ${WHT}${chosen.name} Apikey : ${RST}`)).trim();
    if (!input && !cur) { log('Apikey empty. Cancelled.', 'er'); await sleep(1500); continue; }
    if (input) setApiKey(chosenId, input);
    const cc = loadConfig(); cc.provider = chosenId; saveConfig(cc);
    PROVIDER = chosenId; API_KEY = getApiKey(chosenId);
    log(`Provider set to ${chosen.name}`, 'ok');
    await sleep(1200);
  }
}

async function menuUserAgent(cfg) {
  clear(); bannerMain();
  console.log(`${WHT}  🛠  User-Agent Setup${RST}`);
  console.log(`${WHT}  ────────────────────${RST}\n`);
  console.log(`  ${WHT}Current UA:${RST} ${cfg.userAgent ? GRN + cfg.userAgent : RED + 'not set'}${RST}\n`);
  console.log(`  ${ABU}Tip: User-Agent is required before starting.${RST}\n`);

  const ua = (await askQuestion(`  ${YEL}▸${RST} ${WHT}User Agent : ${RST}`)).trim();
  if (!ua) { log('Cancelled.', 'wr'); await sleep(1000); return cfg; }
  cfg.userAgent = ua;
  CURRENT_UA = ua;
  saveConfig(cfg);
  log('User-Agent updated.', 'ok');
  await sleep(1200);
  return cfg;
}

async function main() {
  const ok = await verifyLicense();
  if (!ok) process.exit(1);

  let cfg = loadConfig();
  PROVIDER   = cfg.provider || '';
  API_KEY    = getApiKey(PROVIDER);
  CURRENT_UA = cfg.userAgent || '';

  SESSION_BEARER = "";
  SESSION_COOKIE = "";

  process.on('SIGINT', () => {
    if (!STOP_SIGNAL) {
      STOP_SIGNAL = true;
      process.stdout.write('\n');
      console.log(`${YEL}[!] Stopping... (Ctrl+C again to force exit)${RST}`);
    } else {
      process.exit(0);
    }
  });

  while (true) {
    STOP_SIGNAL = false;

    const saved = loadLicense();
    let licInfo = 'Unknown';
    if (saved) licInfo = saved.type === 'owner' ? '👑 Owner (Permanent)' : `expires in ${sisaWaktu(saved.expired_at)}`;

    tampilkanMenu(cfg, licInfo);
    const c = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Option : ${RST}`)).trim();

    if (c === '0') {
      console.log(`\n${RED}[!] Program stopped.${RST}`);
      process.exit(0);
    }

    if (c === '1') {
      if (!cfg.userAgent) {
        await blinkWarn('User-Agent required (menu [4]).', 2000);
        continue;
      }
      if (!cfg.email || !cfg.password) {
        await blinkWarn('Email/password required (menu [2]).', 2000);
        continue;
      }
      if (!PROVIDER || !PROVIDERS[PROVIDER]) {
        await blinkWarn('Provider required (menu [3]).', 2000);
        continue;
      }
      if (!API_KEY) {
        await blinkWarn('Solver apikey empty (menu [3]).', 2000);
        continue;
      }

      CURRENT_UA = cfg.userAgent;

      try {
        await runFaucet(cfg);
      } catch (e) {
        if (!STOP_SIGNAL) await blinkErr(`Faucet: ${e.message}`, 2000);
      }
      cfg = loadConfig();
      continue;
    }

    if (c === '2') { cfg = await menuCredentials(cfg); continue; }

    if (c === '3') {
      await menuProvider();
      cfg = loadConfig();
      PROVIDER = cfg.provider || '';
      API_KEY  = getApiKey(PROVIDER);
      continue;
    }

    if (c === '4') { cfg = await menuUserAgent(cfg); continue; }
  }
}

main().catch((e) => {
  console.log(`${RED}Fatal: ${e.message}${RST}`);
  process.exit(1);
});