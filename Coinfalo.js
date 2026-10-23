#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const os = require('os');
const zlib = require('zlib');

const RED = "\x1b[38;5;203m";
const GRN = "\x1b[38;5;114m";
const YEL = "\x1b[38;5;179m";
const BLU = "\x1b[38;5;39m";
const MAG = "\x1b[38;5;170m";
const CYN = "\x1b[38;5;39m";
const WHT = "\x1b[38;5;255m";
const ABU = "\x1b[38;5;245m";
const ORG = "\x1b[38;5;208m";
const RST = "\x1b[0m";
const CLR = "\r\x1b[2K";
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
function boxBot(color) { return `${color}└${'─'.repeat(INNER)}┘${RST}`; }
function headerTop(c) { return `${c}╭${'─'.repeat(INNER)}╮${RST}`; }
function headerMid(c, col) { return `${col}│${RST}${pad(c, INNER)}${col}│${RST}`; }
function headerBot(c) { return `${c}╰${'─'.repeat(INNER)}╯${RST}`; }

const LICENSE_DAYS = 7;
const LICENSE_PATH = path.join(os.homedir(), "license.json");
const PGDEVID = '|PGDEVID6170456257';
const OWNER_KEY_ENC = Buffer.from('YmVnb2JhbmdldGx1NDAy', 'base64').toString();
const OWNER_MACHINE = '511287ca60a137303fe6';

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

const ORIGIN_HOST = Buffer.from('d3d3LmNvaW5mYWxvLmNvbQ==', 'base64').toString();
const ORIGIN_IP   = Buffer.from('MTAzLjE1MC4xOTYuNzE=', 'base64').toString();
const HOST        = `https://${ORIGIN_HOST}`;
const SOLVER_DOMAIN = 'coinfalo.com';
const SITEKEY_ALCAPTCHA = 'Hoi1IZQYr1u7Y4tFVUKBDvS4w0QgqktwDNXQrGgG';
const CONFIG_PATH = path.join(__dirname, 'config.json');

const MIN_DELAY_SEC = 275;
const MAX_DELAY_SEC = 430;

const PROVIDERS = {
  skibidixxx: {
    id: 'skibidixxx', name: 'Skibidixxx',
    host: 'api.waryono.my.id', proto: 'https', port: 443,
    domainField: 'domain', urlField: 'url',
    bodyStyle: 'json', paramStyle: 'waryono', usePgDevid: false,
    respStyle: 'one'
  },
  alljrlwr: {
    id: 'alljrlwr', name: 'AllJrLwr',
    host: 'api.alljrlwr.my.id', proto: 'https', port: 443,
    domainField: 'domain', urlField: 'url',
    bodyStyle: 'form', paramStyle: 'alljrlwr', usePgDevid: true,
    respStyle: 'ok'
  },
  tertuyul: {
    id: 'tertuyul', name: 'Tertuyul',
    host: 'api.tertuyul.my.id', proto: 'http', port: 80,
    domainField: 'pageurl', urlField: 'pageurl',
    bodyStyle: 'multipart', paramStyle: 'tertuyul', usePgDevid: false,
    respStyle: 'one'
  }
};

const SOLVER_FATAL = new Set([
  'ERROR_WRONG_USER_KEY', 'ERROR_KEY_DOES_NOT_EXIST', 'ERROR_ZERO_BALANCE',
  'ERROR_INVALID_PGDEVID', 'ERROR_NO_METHOD', 'ERROR_PAGEURL',
  'ERROR_TOO_BIG_VARIABLE', 'ERROR_UNKNOWN_METHOD', 'ERROR_BAD_DATA',
  'WRONG_USER_KEY', 'ZERO_BALANCE', 'KEY_DOES_NOT_EXIST'
]);

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const chance = (p) => Math.random() < p;
const jitter = (min, max) => min + Math.floor(Math.random() * (max - min + 1));
function mmss(sec) { const m = Math.floor(sec / 60), s = sec % 60; return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`; }
function ts() {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':');
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
    if (on) process.stdout.write(CLR + `${color}[${ts()}] ${prefix} ${text}${RST}`);
    else process.stdout.write(CLR);
    on = !on;
    await sleep(tick);
  }
  process.stdout.write(CLR);
}
const blinkErr  = (msg, d = 2000) => blinkRaw("✗", RED, msg, d, true);
const blinkWarn = (msg, d = 2000) => blinkRaw("⚠", RED, msg, d, false);

const SPINNERS  = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾'];
const SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯'];
const SYMBOLS   = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑'];
const DOTS      = ['▪','▪▪','▪▪▪','▪▪▪▪'];

let STOP_SIGNAL = false;
let lastLimitShown = -1;
let CUR_LINE = '';
process.on('SIGWINCH', () => { if (CUR_LINE) process.stdout.write(CLR + CUR_LINE); });

async function spinnerLoop(label, mode, targetSec, sig) {
  const start = Date.now();
  let i = 0;
  while (!sig.value && !STOP_SIGNAL) {
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
    CUR_LINE =
      ` \x1b[1;3${c1}m ${sp}\x1b[1;37m ${label} ` +
      `\x1b[1;31m${mm}:${ss}\x1b[1;3${c2}m ${sym} ${sp1}` +
      `\x1b[1;37m ${pct}%\x1b[1;33m ${dot}`;
    process.stdout.write(CLR + CUR_LINE);
    await sleep(100);
  }
  CUR_LINE = '';
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
  const raw = `${os.hostname()}|${user}|${process.platform}|${process.arch}`;
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
  if (kind === "owner") {
    d = { type: "owner", machine: getMachineId(), expired_at: "PERMANENT", created_at: new Date().toISOString() };
  } else {
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
}

async function verifyLicense() {
  const saved = loadLicense();
  if (saved) {
    if (saved.type === "owner") {
      clear(); bannerMain();
      console.log(`${YEL}  OWNER MODE — Permanent access.${RST}`);
      await sleep(1000); return true;
    }
    clear(); bannerMain();
    console.log(`${GRN}  License active — expires in ${sisaWaktu(saved.expired_at)}${RST}`);
    await sleep(1000); return true;
  }

  clear();
  console.log(`${WHT}═══════════════════════════════════════════════${RST}`);
  console.log(`${YEL}         LICENSE VERIFICATION${RST}`);
  console.log(`${WHT}═══════════════════════════════════════════════${RST}\n`);

  const picked = SHORTLINK_POOL[Math.floor(Math.random() * SHORTLINK_POOL.length)];
  console.log(`${YEL}  This script requires license verification.${RST}\n`);
  console.log(`${CYN}  Open the following shortlink in your browser:${RST}`);
  console.log(`     ${GRN}${picked.url}${RST}\n`);
  console.log(`${WHT}───────────────────────────────────────────────${RST}\n`);

  for (let i = 1; i <= 3; i++) {
    const code = (await askQuestion(`${YEL}  Enter code [${i}/3]: ${GRN}`)).trim();
    if (code === OWNER_KEY_ENC && getMachineId() === OWNER_MACHINE) {
      saveLicense("owner"); clear(); bannerMain();
      console.log(`${YEL}  OWNER MODE — Permanent access.${RST}`);
      await sleep(1500); return true;
    }
    if (code.toUpperCase() === picked.code.toUpperCase()) {
      saveLicense("user"); clear(); bannerMain();
      console.log(`${GRN}  Verification successful! Active for ${LICENSE_DAYS} days.${RST}`);
      await sleep(1500); return true;
    }
    await blinkErr(`Invalid code! Attempts remaining: ${3 - i}`, 1500);
  }
  await blinkErr("Verification failed. Exiting...", 2500);
  return false;
}

function defaultConfig() {
  return {
    cookie: "", userAgent: "", provider: "tertuyul", ownApikeys: [],
    apikeys: { skibidixxx: "", alljrlwr: "", tertuyul: "" }
  };
}
function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) return defaultConfig();
  try {
    const c = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    const d = defaultConfig();
    return { ...d, ...c, apikeys: { ...d.apikeys, ...(c.apikeys || {}) } };
  } catch { return defaultConfig(); }
}
function saveConfig(cfg) {
  try { fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2)); } catch {}
}
function askQuestion(q) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => rl.question(q, a => { rl.close(); res(a); }));
}

let COOKIES = {};
function parseCookie(str) {
  const out = {};
  for (const part of String(str || '').split(';')) {
    const p = part.trim();
    if (!p) continue;
    const eq = p.indexOf('=');
    if (eq > 0) out[p.slice(0, eq).trim()] = p.slice(eq + 1).trim();
  }
  return out;
}
function cookiesToHeader() {
  return Object.entries(COOKIES).map(([k, v]) => `${k}=${v}`).join('; ');
}
function mergeSetCookies(headers) {
  const sc = headers['set-cookie'];
  if (!sc) return;
  const arr = Array.isArray(sc) ? sc : [sc];
  for (const c of arr) {
    const pair = c.split(';')[0];
    const eq = pair.indexOf('=');
    if (eq > 0) COOKIES[pair.slice(0, eq).trim()] = pair.slice(eq + 1).trim();
  }
}

function rawRequest({ scheme, host, port, method = 'GET', path: p, headers = {}, body = null, timeout = 25000 }) {
  return new Promise((resolve, reject) => {
    const lib = scheme === 'https' ? https : http;
    const opts = { host, port, path: p, method, headers, timeout };
    if (scheme === 'https') opts.rejectUnauthorized = false;
    const req = lib.request(opts, res => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('timeout', () => { req.destroy(); reject(Object.assign(new Error('timeout'), { code: 'ETIMEDOUT' })); });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}
function gunzip(body, enc) {
  if (!body) return '';
  const e = String(enc || '').toLowerCase();
  try {
    if (e.includes('gzip')) return zlib.gunzipSync(Buffer.from(body, 'binary')).toString('utf8');
    if (e.includes('deflate')) return zlib.inflateSync(Buffer.from(body, 'binary')).toString('utf8');
    if (e.includes('br')) return zlib.brotliDecompressSync(Buffer.from(body)).toString('utf8');
  } catch {}
  return body;
}

let CURRENT_UA = '';

async function cReq({ method, path: p, body, referer }) {
  const headers = {
    'Host': ORIGIN_HOST,
    'User-Agent': CURRENT_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'close'
  };
  const ck = cookiesToHeader();
  if (ck) headers['Cookie'] = ck;
  if (referer) headers['Referer'] = HOST + referer;
  if (body) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    headers['Content-Length'] = Buffer.byteLength(body);
    headers['Origin'] = HOST;
  }
  const res = await rawRequest({ scheme: 'http', host: ORIGIN_IP, port: 80, method, path: p, headers, body });
  mergeSetCookies(res.headers);
  return { status: res.status, headers: res.headers, body: gunzip(res.body, res.headers['content-encoding']) };
}

function getSolverKey(providerId, apikey, ownApikeys) {
  const a = (apikey || '').trim();
  const p = PROVIDERS[providerId];
  if (!p || !p.usePgDevid) return a;
  if (!a || a.includes('|PGDEVID')) return a;
  if ((ownApikeys || []).includes(a)) return a;
  return a + PGDEVID;
}

function buildMultipartForm(fields) {
  const boundary = '----WebKitFormBoundary' + Math.random().toString(36).slice(2, 18);
  let body = '';
  for (const [name, value] of Object.entries(fields)) {
    body += `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="${name}"\r\n\r\n`;
    body += `${value}\r\n`;
  }
  body += `--${boundary}--\r\n`;
  return { body, contentType: `multipart/form-data; boundary=${boundary}` };
}

async function solverSubmit(providerId, apikey, ownApikeys, fields) {
  const p = PROVIDERS[providerId];
  const key = getSolverKey(providerId, apikey, ownApikeys);
  let body, headers = { 'User-Agent': CURRENT_UA, 'Accept': 'application/json, text/plain, */*' };

  if (p.paramStyle === 'waryono') {
    body = JSON.stringify({ apikey: key, json: 1, ...fields, methods: fields.method });
    headers['Content-Type'] = 'application/json';
  } else if (p.paramStyle === 'alljrlwr') {
    body = new URLSearchParams({ key, json: 1, ...fields }).toString();
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
  } else {
    const mp = buildMultipartForm({ key, json: '1', ...fields });
    body = mp.body;
    headers['Content-Type'] = mp.contentType;
  }
  headers['Content-Length'] = Buffer.byteLength(body);

  const res = await rawRequest({ scheme: p.proto, host: p.host, port: p.port, method: 'POST', path: '/in.php', headers, body, timeout: 20000 });
  let r;
  try { r = JSON.parse(res.body || '{}'); } catch { return { ok: false, error: 'BAD_JSON: ' + String(res.body || '').slice(0, 60) }; }

  if (p.respStyle === 'ok') {
    if (r && r.status === 'OK' && r.request) return { ok: true, taskId: String(r.request) };
    return { ok: false, error: String((r && r.status) || 'SUBMIT_FAIL') };
  }
  if (r && r.status === 1 && r.request) return { ok: true, taskId: String(r.request) };
  return { ok: false, error: String((r && r.request) || (r && r.status) || 'SUBMIT_FAIL') };
}

async function solverPoll(providerId, apikey, ownApikeys, taskId) {
  const p = PROVIDERS[providerId];
  const key = getSolverKey(providerId, apikey, ownApikeys);
  let res;
  const headers = { 'User-Agent': CURRENT_UA, 'Accept': 'application/json, text/plain, */*' };

  if (p.paramStyle === 'tertuyul') {
    const params = new URLSearchParams({ key, action: 'get', id: taskId, json: '1' }).toString();
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    headers['Content-Length'] = Buffer.byteLength(params);
    res = await rawRequest({ scheme: p.proto, host: p.host, port: p.port, method: 'POST', path: '/res.php', headers, body: params, timeout: 20000 });
  } else if (p.paramStyle === 'alljrlwr') {
    const q = new URLSearchParams({ key, action: 'get', id: taskId, json: '1' }).toString();
    res = await rawRequest({ scheme: p.proto, host: p.host, port: p.port, method: 'GET', path: '/res.php?' + q, headers, timeout: 20000 });
  } else {
    const q = new URLSearchParams({ apikey: key, id: taskId, action: 'get', json: '1' }).toString();
    res = await rawRequest({ scheme: p.proto, host: p.host, port: p.port, method: 'GET', path: '/res.php?' + q, headers, timeout: 20000 });
  }

  let r;
  try { r = JSON.parse(res.body || '{}'); } catch { return { notReady: true }; }

  if (p.respStyle === 'ok') {
    if (r && r.status === 'OK' && r.result) return { ready: true, token: String(r.result) };
    if (r && r.status === 'OK' && r.request) return { ready: true, token: String(r.request) };
    const e = String((r && r.status) || '').toUpperCase();
    if (e.startsWith('ERROR')) return { error: e };
    return { notReady: true };
  }
  if (r && r.status === 1 && r.request) return { ready: true, token: String(r.request) };
  const errv = String((r && r.request) || '').toUpperCase();
  if (errv.startsWith('ERROR') || errv.includes('ZERO_BALANCE') || errv.includes('WRONG_USER_KEY')) return { error: errv };
  return { notReady: true };
}

async function solveAlcaptcha(cfg) {
  const provId = cfg.provider;
  const p = PROVIDERS[provId];
  const own = cfg.ownApikeys || [];
  let lastError = '';
  if (!p) return { token: null, lastError: 'UNKNOWN_PROVIDER', fatal: true };
  const apikey = (cfg.apikeys || {})[provId];
  if (!apikey) return { token: null, lastError: 'APIKEY_NOT_SET', fatal: true };
  while (!STOP_SIGNAL) {
    try {
      const sub = await solverSubmit(provId, apikey, own, {
        method: 'adslab', sitekey: SITEKEY_ALCAPTCHA,
        [p.domainField]: SOLVER_DOMAIN
      });
      if (!sub.ok) {
        lastError = sub.error;
        if (SOLVER_FATAL.has(sub.error)) return { token: null, lastError, fatal: true };
        await sleep(2000); continue;
      }
      const taskId = sub.taskId;
      for (let w = 0; w < 24; w++) {
        await sleep(4000);
        const r = await solverPoll(provId, apikey, own, taskId);
        if (r.ready) {
          return { token: r.token, lastError: '' };
        }
        if (r.error) {
          lastError = r.error;
          if (SOLVER_FATAL.has(r.error)) return { token: null, lastError, fatal: true };
          break;
        }
      }
    } catch (e) {
      lastError = e.message;
    }
    await sleep(2000);
  }
  return { token: null, lastError };
}

function isCfChallenge(html, status) {
  if (status === 403 || status === 503) return true;
  if (!html) return false;
  return /cf-chl|challenge-platform|cf-brdsp|Just a moment/i.test(html);
}
function parseFaucet(html) {
  const action = (html.match(/action="(?:https?:\/\/[^\/]+)?(\/faucet\/verify\/[^"]+)"/) || [])[1] || '';
  const csrf = (html.match(/name="csrf_token_name"[^>]*value="([^"]+)"/) || [])[1] || '';
  const token = (html.match(/name="token"[^>]*value="([^"]+)"/) || [])[1] || '';
  const ct = (html.match(/id="ct_data"\s+data-token="([^"]+)"/) || [])[1] || '';
  const hp = html.match(/name="(cf_[0-9a-f]{16})"[^>]*value="([^"]+)"/);
  const minM = html.match(/id="minute"[^>]*>\s*(\d+)\s*</);
  const secM = html.match(/id="second"[^>]*>\s*(\d+)\s*</);
  let nextSec = 0;
  if (minM && secM) nextSec = (+minM[1]) * 60 + (+secM[1]);
  else {
    const nextM = html.match(/Next claim in:\s*(\d+)\s*:\s*(\d+)/i);
    if (nextM) nextSec = (+nextM[1]) * 60 + (+nextM[2]);
  }
  const limM = html.match(/<!--(\d+)\/(\d+) limit-->/);
  const limitCur = limM ? +limM[1] : 0;
  const limitMax = limM ? +limM[2] : 0;
  const btnM = html.match(/<button[^>]*claim-button[^>]*>/);
  const btnFull = html.match(/<button[^>]*claim-button[\s\S]{0,300}?<\/button>/);
  const btnDisabled = btnM ? /disabled/.test(btnM[0]) : false;
  const btnText = (btnFull && (btnFull[0].match(/>([^<]*)<\/button>/) || [])[1] || '').trim();
  const isLoading = /loading/i.test(btnText);
  const locked = btnDisabled && !isLoading && !nextSec;
  return {
    verifyPath: action, csrf, token, ctToken: ct,
    hpName: hp ? hp[1] : '', hpVal: hp ? hp[2] : '1',
    timerSec: nextSec, btnDisabled, btnText, isLoading, locked,
    limitCur, limitMax
  };
}
function parseClaimResult(html) {
  const added = (html.match(/([\d.,]+)\s*tokens has been added/i) || [])[1];
  const i = html.indexOf('id="rewardModal"');
  if (i < 0) return added ? { final: added } : {};
  const seg = html.slice(i, i + 4000);
  const final = (seg.match(/Final Reward[\s\S]{0,300}?<strong[^>]*>\s*([\d.,]+)/) || [])[1];
  const base = (seg.match(/Base Reward[^]{0,120}?([\d.,]+)/) || [])[1];
  const bonus = (seg.match(/Level Bonus[^]{0,120}?([\d.,]+)/) || [])[1];
  return { final: added || final, base, bonus };
}

async function promptNewCookie(cfg) {
  console.log('');
  console.log(`${WHT}═══════════════════════════════════════════════${RST}`);
  console.log(`${RED}  Cookie Expired / Cloudflare Block!${RST}`);
  console.log(`${WHT}═══════════════════════════════════════════════${RST}`);
  const newCookie = (await askQuestion(`${WHT}  Paste New Cookie : ${RST}`)).trim();
  clear(); bannerMain();
  if (!newCookie) {
    await blinkErr('Cookie is empty, cancelled.', 2000);
    return false;
  }
  const parsed = parseCookie(newCookie);
  if (!parsed.ci_session) await blinkWarn('Cookie does not contain ci_session.', 2000);
  cfg.cookie = newCookie;
  saveConfig(cfg);
  COOKIES = parsed;
  log('New cookie saved to config.json', 'ok');
  return true;
}

async function fetchAccountInfo(retries = 2) {
  for (let i = 0; i <= retries; i++) {
    const res = await cReq({ method: 'GET', path: '/index.php?/faucet', referer: '/dashboard' });
    if (isCfChallenge(res.body, res.status)) return { cf: true };
    const f = parseFaucet(res.body);
    if (!f.verifyPath) {
      const loggedIn = /logout/i.test(res.body) && !/action="[^"]*auth\/login/i.test(res.body);
      if (loggedIn) {
        if (f.timerSec > 5) return { cooldown: true, timerSec: f.timerSec };
        return { locked: true, timerSec: f.timerSec };
      }
      if (i < retries) { await sleep(jitter(2000, 5000)); continue; }
      return { notLoggedIn: true };
    }
    return { faucet: f };
  }
}

async function fetchBalance() {
  try {
    const res = await cReq({ method: 'GET', path: '/index.php?/dashboard', referer: '/faucet' });
    const m = res.body.match(/id="tokenBalances"[^>]*data-tokens="([^"]+)"/);
    return m ? m[1] : null;
  } catch { return null; }
}

async function claimOnce(cfg) {
  await sleep(jitter(800, 2000));
  let acc = await fetchAccountInfo();
  if (acc.cf) { await blinkWarn('CF challenge — retrying in 60s', 1800); return { ok: false, code: 'CF_BLOCK' }; }
  if (acc.notLoggedIn) return { ok: false, code: 'COOKIE_EXPIRED' };
  if (acc.cooldown) return { ok: false, code: 'COOLDOWN', waitSec: acc.timerSec };
  if (acc.locked) return { ok: false, code: 'LOCKED' };
  if (acc.faucet && acc.faucet.limitMax && acc.faucet.limitCur >= acc.faucet.limitMax) {
    log(`Limit counter: ${acc.faucet.limitCur}/${acc.faucet.limitMax} — web shows Unlimited, trying anyway`, 'warn');
  }

  const f = acc.faucet;
  if (f.limitMax && f.limitCur !== lastLimitShown) {
    lastLimitShown = f.limitCur;
    log(`Limit counter: ${f.limitCur}/${f.limitMax} (soft — web shows Unlimited, keep claiming)`, f.limitCur >= f.limitMax ? 'warn' : 'i');
  }
  if (f.timerSec > 5) {
    return { ok: false, code: 'COOLDOWN', waitSec: f.timerSec };
  }
  if (f.btnDisabled && f.locked) return { ok: false, code: 'LOCKED' };
  if (f.btnDisabled && f.isLoading) {
  } else if (f.btnDisabled) {
    return { ok: false, code: 'RECHECK' };
  }

  const provName = PROVIDERS[cfg.provider] ? PROVIDERS[cfg.provider].name : cfg.provider;
  const sp = spawnSpinner(`${provName} [Adslabs]`, 'countup', 180);
  let tok = null, lastErr = '', fatalErr = false;
  try {
    const out = await solveAlcaptcha(cfg);
    tok = out.token; lastErr = out.lastError || ''; fatalErr = !!out.fatal;
  } catch (e) { lastErr = e.message; }
  await sp.stop();
  if (!tok) {
    if (fatalErr) return { ok: false, code: 'SOLVER_FATAL', msg: lastErr };
    if (lastErr) await blinkErr(lastErr, 3000);
    return { ok: false, code: 'CAPTCHA_FAIL' };
  }

  await sleep(jitter(800, 2000));
  const fields = {
    csrf_token_name: f.csrf, token: f.token, c_t7ushe: f.ctToken,
    [f.hpName]: f.hpVal, captcha: 'adslab', 'alcaptcha-response': tok
  };
  const body = new URLSearchParams(fields).toString();
  const res = await cReq({ method: 'POST', path: f.verifyPath, body, referer: '/faucet' });

  if (isCfChallenge(res.body, res.status)) {
    await blinkWarn('POST hit CF challenge — retry later', 1800);
    return { ok: false, code: 'CF_BLOCK' };
  }
  if (res.status === 303 || res.status === 302) {
    const after = await cReq({ method: 'GET', path: '/index.php?/faucet', referer: '/faucet' });
    const out2 = parseClaimResult(after.body);
    if (out2.final) return { ok: true, reward: out2.final, base: out2.base, bonus: out2.bonus };
    const low2 = after.body.toLowerCase();
    if (low2.includes('there was an error')) return { ok: false, code: 'SITE_ERROR' };
    if (low2.includes('invalid') || low2.includes('captcha')) return { ok: false, code: 'CAPTCHA_REJECTED' };
    if (low2.includes('must wait') || low2.includes('please wait')) return { ok: false, code: 'COOLDOWN', waitSec: f.timerSec };
    return { ok: false, code: 'REDIRECT_NO_REWARD' };
  }
  const out = parseClaimResult(res.body);
  if (out.final) return { ok: true, reward: out.final, base: out.base, bonus: out.bonus };
  const low = res.body.toLowerCase();
  if (low.includes('there was an error')) return { ok: false, code: 'SITE_ERROR' };
  if (low.includes('must wait') || low.includes('please wait')) return { ok: false, code: 'COOLDOWN', waitSec: f.timerSec };
  return { ok: false, code: 'UNKNOWN' };
}

async function runFaucet(cfg) {
  STOP_SIGNAL = false;
  if (!Object.keys(COOKIES).length) { log('Cookie is empty — set it first (menu 2)', 'er'); return; }
  if (!CURRENT_UA) { log('User-Agent is empty — set it first (menu 4)', 'er'); return; }
  if (!(cfg.apikeys || {})[cfg.provider]) { log(`API key for ${cfg.provider} is empty — set it first (menu 3)`, 'er'); return; }

  log('Checking session…', 'i');
  const initial = await fetchAccountInfo();
  if (initial.notLoggedIn) {
    const ok = await promptNewCookie(cfg);
    if (!ok) return;
    return runFaucet(cfg);
  }
  if (initial.cf) { log('CF challenge — bypass first / update cookie', 'er'); return; }
  if (initial.faucet) {
    log('Session ready.', 'ok');
    const lc = initial.faucet.limitCur, lm = initial.faucet.limitMax;
    if (lm && lc >= lm) log(`Limit counter: ${lc}/${lm} — web shows Unlimited, trying anyway`, 'warn');
  }
  await tmr(10, 'Warmup...');

  while (!STOP_SIGNAL) {
    let r;
    try { r = await claimOnce(cfg); }
    catch (e) { r = { ok: false, code: 'EXCEPTION', msg: e.message }; }

    if (r.ok) {
      console.log(`${WHT}[${ts()}]${RST} ${GRN}✓${RST} ${GRN}${r.reward} tokens has been added to your balance${RST}`);
      const bal = await fetchBalance();
      if (bal) console.log(`${WHT}[${ts()}]${RST} ${ORG}●${RST} ${YEL}New Balance: ${CYN}${bal}${YEL} tokens${RST}`);
      await tmr(jitter(MIN_DELAY_SEC, MAX_DELAY_SEC), 'Waiting...');
      continue;
    }

    switch (r.code) {
      case 'COOLDOWN':
        await tmr((r.waitSec || 240) + jitter(10, 45), 'Waiting...');
        break;
      case 'RECHECK':
        await tmr(jitter(15, 40), 'Waiting...');
        break;
      case 'LOCKED':
        log('Faucet locked/flaky — re-checking in 90s (if mobile web can claim, anti-abuse flags the origin IP intermittently)', 'warn');
        await tmr(90, 'Re-checking faucet…');
        break;
      case 'COOKIE_EXPIRED': {
        const ok = await promptNewCookie(cfg);
        if (!ok) return;
        break;
      }
      case 'CF_BLOCK':
        await tmr(60, 'CF retry...');
        break;
      case 'CAPTCHA_FAIL':
        log('Captcha failed — retrying', 'er');
        await tmr(jitter(60, 120), 'Retry later...');
        break;
      case 'SOLVER_FATAL':
        await blinkErr(r.msg || 'SOLVER_FATAL', 3000);
        return;
      case 'CAPTCHA_REJECTED':
        log('Captcha rejected by site — resubmitting', 'wr');
        await tmr(jitter(30, 75), 'Retry...');
        break;
      default:
        log(`Claim failed (${r.code}) — waiting 3-6 min`, 'er');
        await tmr(jitter(180, 360), 'Retry later...');
    }
  }
  log('Loop stopped.', 'wr');
}

function maskKey(k) { return k && k.length > 12 ? k.slice(0, 6) + '...' + k.slice(-4) : (k || '-'); }

function tampilkanMenu(cfg, licInfo) {
  clear();
  console.log(headerTop(CYN));
  console.log(headerMid(`  ${BG_MERAH}${WHT} KUYANGIN DONG ${RST}`, CYN));
  console.log(headerBot(CYN));

  console.log(`  ${YEL}▸${RST} ${WHT}Site       ${RST}: ${GRN}coinfalo.com${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Creator    ${RST}: ${GRN}iyannn${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Version    ${RST}: ${GRN}Ceban${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Info       ${RST}: ${GRN}Ngopi Dong${RST}`);
  console.log("");

  const uaDisp = cfg.userAgent ? `${GRN}${cfg.userAgent}${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}User-Agent ${RST}: ${uaDisp}`);

  const ckDisp = cfg.cookie ? `${GRN}${cfg.cookie.slice(0, 20)}...${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Cookie     ${RST}: ${ckDisp}`);

  const provKey = (cfg.apikeys || {})[cfg.provider];
  const provDisp = (provKey && PROVIDERS[cfg.provider]) ? `${GRN}${PROVIDERS[cfg.provider].name}${RST}` : `${RED}✗ not set${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Provider   ${RST}: ${provDisp}`);

  console.log("");
  console.log(boxTop('[ MENU ]', CYN));
  console.log(boxMid(`  ${YEL}[1]${RST} ${WHT}Start Claim${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[2]${RST} ${WHT}Set Cookie${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[3]${RST} ${WHT}Set Provider + Apikey${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[4]${RST} ${WHT}Set User-Agent${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[0]${RST} ${RED}Exit${RST}`, CYN));
  console.log(boxBot(CYN));
  console.log("");
  console.log(`  ${ABU}[License] ${YEL}${licInfo}${RST}`);
}

async function menuCookie(cfg) {
  clear(); bannerMain();
  console.log(`${WHT}  Cookie Setup${RST}`);
  console.log(`${WHT}  ─────────────────────${RST}\n`);
  console.log(`  ${WHT}Current:${RST} ${cfg.cookie ? GRN + cfg.cookie.slice(0, 30) + '...' : RED + 'not set'}${RST}\n`);
  const c = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Cookie${RST} : `)).trim();
  if (!c) { log('Cancelled.', 'wr'); await sleep(1000); return cfg; }
  cfg.cookie = c; saveConfig(cfg);
  COOKIES = parseCookie(c);
  log('Cookie saved.', 'ok');
  await sleep(1000);
  return cfg;
}

async function menuProvider(cfg) {
  while (true) {
    clear(); bannerMain();
    console.log(`${WHT}  Provider Setup${RST}`);
    console.log(`${WHT}  ─────────────────${RST}\n`);
    const ids = Object.keys(PROVIDERS);
    ids.forEach((id, i) => {
      const p = PROVIDERS[id];
      const mark = id === (cfg.provider || '') ? ` ${GRN}●${RST}` : '  ';
      const kDisp = (cfg.apikeys || {})[id] ? `${GRN}${maskKey(cfg.apikeys[id])}${RST}` : `${WHT}-${RST}`;
      console.log(`  ${GRN}[${i + 1}]${RST}${mark} ${WHT}${p.name.padEnd(14)}${RST} ${kDisp}`);
    });
    console.log(`  ${RED}[0]${RST}  ${WHT}Back${RST}\n`);
    const c = (await askQuestion(`  ${WHT}Select: ${RST}`)).trim();
    if (c === '0') return cfg;
    const idx = parseInt(c, 10);
    if (isNaN(idx) || idx < 1 || idx > ids.length) { log('Invalid option.', 'er'); await sleep(1000); continue; }

    const chosenId = ids[idx - 1];
    const chosen = PROVIDERS[chosenId];
    console.log('');
    const input = (await askQuestion(`  ${WHT}${chosen.name} Apikey : ${RST}`)).trim();
    if (!input && !(cfg.apikeys || {})[chosenId]) { log('Apikey is empty. Cancelled.', 'er'); await sleep(1200); continue; }
    if (input) { cfg.apikeys = { ...(cfg.apikeys || {}), [chosenId]: input }; }
    cfg.provider = chosenId;
    saveConfig(cfg);
    log(`Provider set to ${chosen.name}`, 'ok');
    await sleep(1000);
    return cfg;
  }
}

async function menuUserAgent(cfg) {
  clear(); bannerMain();
  console.log(`${WHT}  User-Agent Setup${RST}`);
  console.log(`${WHT}  ────────────────────${RST}\n`);
  const ua = (await askQuestion(`  ${YEL}▸${RST} ${WHT}User Agent : ${RST}`)).trim();
  if (!ua) { log('User-Agent is required.', 'er'); await sleep(1200); return cfg; }
  cfg.userAgent = ua;
  CURRENT_UA = ua;
  saveConfig(cfg);
  log('User-Agent saved.', 'ok');
  await sleep(1000);
  return cfg;
}

async function main() {
  process.on('SIGINT', () => {
    if (!STOP_SIGNAL) {
      STOP_SIGNAL = true;
      process.stdout.write(`\n${YEL}⚠ Stopped. Back to menu...${RST}\n`);
    } else {
      process.stdout.write(`\n${RED}Program exited.${RST}\n`);
      process.exit(0);
    }
  });
  const ok = await verifyLicense();
  if (!ok) process.exit(1);

  let cfg = loadConfig();
  CURRENT_UA = cfg.userAgent || '';
  COOKIES = cfg.cookie ? parseCookie(cfg.cookie) : {};

  while (true) {
    STOP_SIGNAL = false;
    const saved = loadLicense();
    const licInfo = saved
      ? (saved.type === 'owner' ? 'Owner (Permanent)' : `expires in ${sisaWaktu(saved.expired_at)}`)
      : 'Unknown';

    tampilkanMenu(cfg, licInfo);
    const c = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Option : ${RST}`)).trim();

    if (c === '0') { console.log(`\n${RED}[!] Stopped.${RST}`); process.exit(0); }

    if (c === '1') {
      if (!cfg.cookie) { log('Cookie is required (menu 2)', 'er'); await sleep(1500); continue; }
      if (!cfg.userAgent) { log('User-Agent is required (menu 4)', 'er'); await sleep(1500); continue; }
      if (!(cfg.apikeys || {})[cfg.provider]) { log(`Apikey for ${cfg.provider} is required (menu 3)`, 'er'); await sleep(1500); continue; }
      CURRENT_UA = cfg.userAgent;
      COOKIES = parseCookie(cfg.cookie);
      try { await runFaucet(cfg); }
      catch (e) { if (!STOP_SIGNAL) log(`Error: ${e.message}`, 'er'); }
      cfg = loadConfig();
      await askQuestion(`\n  ${WHT}Press Enter...${RST}`);
      continue;
    }
    if (c === '2') { cfg = await menuCookie(cfg); continue; }
    if (c === '3') { cfg = await menuProvider(cfg); continue; }
    if (c === '4') { cfg = await menuUserAgent(cfg); continue; }
  }
}

main().catch(e => { console.log(`${RED}Fatal: ${e.message}${RST}`); process.exit(1); });
