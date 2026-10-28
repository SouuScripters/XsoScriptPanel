#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const zlib = require('zlib');
const readline = require('readline');
const crypto = require('crypto');
const os = require('os');
const { URL, URLSearchParams } = require('url');

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
const pad = (s, n) => s + ' '.repeat(Math.max(0, n - vlen(s)));
const INNER = 47;

const boxTop = (label, color) => {
  const prefix = '┌───' + label;
  return `${color}${prefix}${'─'.repeat(Math.max(0, INNER + 2 - vlen(prefix) - 1))}┐${RST}`;
};
const boxMid = (c, color) => `${color}│${RST}${pad(c, INNER)}${color}│${RST}`;
const boxBot = (color) => `${color}└${'─'.repeat(INNER)}┘${RST}`;
const headerTop = (c) => `${c}╭${'─'.repeat(INNER)}╮${RST}`;
const headerMid = (c, col) => `${col}│${RST}${pad(c, INNER)}${col}│${RST}`;
const headerBot = (c) => `${c}╰${'─'.repeat(INNER)}╯${RST}`;

const ORIGIN_HOST = 'cryptoadpay.com';
const HOST = `https://${ORIGIN_HOST}`;
const SITEKEY = '55504660-6a22-42c4-b5dc-9ad08fe4cb10';
const DEF_UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36';
const BITCO_HOST = 'bitcotasks.com';
const BITCO_ORIGIN = `https://${BITCO_HOST}`;

const DEBUG = false;
const FAUCET_MIN_WAIT = 70;
const FAUCET_MAX_WAIT = 75;
const FAUCET_BATCH = 10;
const BITCO_BATCH = 20;

// ====== RUNTIME 6 JAM ======
const RUNTIME_MS = 6 * 60 * 60 * 1000;
let RUNTIME_START = 0;
let RUNTIME_END = 0;
const startRuntime = () => { RUNTIME_START = Date.now(); RUNTIME_END = RUNTIME_START + RUNTIME_MS; };
const resetRuntime = () => { RUNTIME_START = 0; RUNTIME_END = 0; };
const isTimeUp = () => RUNTIME_END > 0 && Date.now() >= RUNTIME_END;
const runtimeLeftStr = () => {
  if (!RUNTIME_END) return '-';
  const d = RUNTIME_END - Date.now();
  if (d <= 0) return 'HABIS';
  const h = Math.floor(d / 3600000);
  const m = Math.floor((d % 3600000) / 60000);
  return `${h}j ${m}m`;
};

// ====== ERROR COUNTER (MAX 3 → STOP) ======
const MAX_ERRORS = 3;
let ERROR_COUNT = 0;
const resetErrors = () => { ERROR_COUNT = 0; };
const bumpError = (ctx, msg) => {
  ERROR_COUNT++;
  log(`[${ctx}] ${msg} (${ERROR_COUNT}/${MAX_ERRORS})`, 'er');
  if (ERROR_COUNT >= MAX_ERRORS) {
    STOP_SIGNAL = true;
    log(`⛔ MAX ${MAX_ERRORS} ERROR — STOP TOTAL`, 'er');
    return true;
  }
  return false;
};

// ====== CONFIG PATHS ======
const BOT_NAME = 'kuyangindong';
const CONFIG_PATH = path.join(__dirname, `${BOT_NAME}.config.json`);
const COOKIE_PATH = path.join(__dirname, `${BOT_NAME}.cookies.json`);

// ====== ANTI-BAN HUMAN DELAY ======
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const humanDelay = async (min = 600, max = 1800) => {
  if (STOP_SIGNAL) return;
  const ms = min + Math.floor(Math.random() * (max - min));
  await sleep(ms);
};
const humanDelayVar = async () => {
  if (STOP_SIGNAL) return;
  const r = Math.random();
  let ms;
  if (r < 0.55) ms = 350 + Math.floor(Math.random() * 600);
  else if (r < 0.9) ms = 1000 + Math.floor(Math.random() * 1400);
  else ms = 2600 + Math.floor(Math.random() * 1800);
  await sleep(ms);
};
const jitterHeaders = (h = {}) => {
  const out = { ...h };
  if (!out['Accept-Language']) {
    const langs = ['id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7', 'id-ID,id;q=0.9,en;q=0.8', 'en-US,en;q=0.9,id;q=0.8'];
    out['Accept-Language'] = langs[Math.floor(Math.random() * langs.length)];
  }
  return out;
};

const PROVIDERS = {
  skibidixxx: {
    id: 'skibidixxx', name: 'Skibidixxx',
    host: 'api.waryono.my.id', proto: 'https', port: 443,
    submitUrl: '/in.php', pollUrl: '/res.php',
    submitType: 'json', submitKey: 'apikey', pollKey: 'apikey',
    pollMethod: 'GET', pollActionKey: 'action', pollActionValue: 'get', pollIdKey: 'id',
    methodField: 'methods',
    imageMethod: 'bitcogif', imageMethodLabel: 'Bitcogif', imageKey: 'base64',
    hcaptcha: { sitekeyParam: 'sitekey', domainParam: 'domain' }
  }
};

const SOLVER_ERROR_MAP = {
  ERROR_WRONG_USER_KEY: { kind: 'fatal', msg: 'Wrong User Key' },
  ERROR_KEY_DOES_NOT_EXIST: { kind: 'fatal', msg: 'Key Does Not Exist' },
  ERROR_ZERO_BALANCE: { kind: 'fatal', msg: 'Zero Balance' },
  ERROR_INVALID_METHOD: { kind: 'fatal', msg: 'Invalid Method' },
  ERROR_WRONG_METHOD: { kind: 'fatal', msg: 'Wrong Method' },
  ERROR_SOLVER_OFFLINE: { kind: 'fatal', msg: 'Solver Offline' },
  ERROR_PROXY_CONNECTION_FAILED: { kind: 'fatal', msg: 'Proxy Failed' },
  ERROR_METHOD_NOT_SPECIFIED: { kind: 'fatal', msg: 'Method Not Specified' },
  ERROR_CAPTCHA_UNSOLVABLE: { kind: 'retry', msg: 'Unsolvable' },
  ERROR_CAPTCHA_TIMEOUT: { kind: 'retry', msg: 'Timeout' },
  ERROR_BAD_DATA: { kind: 'retry', msg: 'Bad Data' },
  ERROR_BAD_PARAMETERS: { kind: 'retry', msg: 'Bad Params' },
  ERROR_WRONG_ID: { kind: 'retry', msg: 'Wrong ID' },
  ERROR_INVALID_IMAGE: { kind: 'retry', msg: 'Invalid Image' },
  ERROR_EMPTY_IMAGE_DATA: { kind: 'retry', msg: 'Empty Image' },
  ERROR_RATE_LIMIT: { kind: 'rate', msg: 'Rate Limit' },
  ERROR_TOO_MANY_REQUESTS: { kind: 'rate', msg: 'Too Many Requests' },
  ERROR_NO_SLOT_AVAILABLE: { kind: 'rate', msg: 'No Slot' },
  ERROR_REQUEST_COOLDOWN: { kind: 'rate', msg: 'Cooldown' },
  ERROR_INTERNAL_SERVER: { kind: 'server', msg: 'Internal Server' },
  ERROR_INTERNAL_SERVER_ERROR: { kind: 'server', msg: 'Internal Server' },
  ERROR_DATABASE_CONNECTION_FAILED: { kind: 'server', msg: 'DB Connection' },
  CAPCHA_NOT_READY: { kind: 'polling', msg: 'Not ready' },
  CAPTCHA_NOT_READY: { kind: 'polling', msg: 'Not ready' },
  ERROR_CAPTCHA_NOT_READY: { kind: 'polling', msg: 'Not ready' }
};

const classifySolverError = (code) => {
  const up = String(code || '').toUpperCase().trim();
  if (!up) return null;
  if (SOLVER_ERROR_MAP[up]) return SOLVER_ERROR_MAP[up];
  for (const k of Object.keys(SOLVER_ERROR_MAP)) if (up.includes(k)) return SOLVER_ERROR_MAP[k];
  return null;
};

let PROVIDER = '';
let API_KEY = '';
let STOP_SIGNAL = false;
let SESSION_BEARER = '';
let SESSION_COOKIE = '';

let spinPause = null;
let spinResume = null;

const now = () => { const d = new Date(); return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':'); };
const clear = () => process.stdout.write('\x1b[2J\x1b[3J\x1b[H');

const log = (msg, tag = 'i') => {
  const icons = { i: `${CYN}»${RST}`, ok: `${GRN}✓${RST}`, er: `${RED}✗${RST}`, wr: `${YEL}⚠${RST}`, in: `${BLU}●${RST}`, or: `${ORG}●${RST}`, dbg: `${MAG}⚙${RST}`, limit: `${RED}✗${RST}` };
  const icon = icons[tag] || icons.i;
  const textColor = (tag === 'wr' || tag === 'er' || tag === 'limit') ? RED : WHT;
  if (spinPause) spinPause();
  process.stdout.write(`${WHT}[${now()}]${RST} ${icon} ${textColor}${msg}${RST}\n`);
  if (spinResume) spinResume();
};
const claimOut = (msg) => { if (spinPause) spinPause(); process.stdout.write(`${WHT}[${now()}]${RST} ${GRN}${msg}${RST}\n`); if (spinResume) spinResume(); };
const claimOutLine = (msg) => { if (spinPause) spinPause(); process.stdout.write(msg + '\n'); if (spinResume) spinResume(); };
const dbg = (msg) => { if (DEBUG) log(msg, 'dbg'); };

const SYMBOLS = ['🌘','🌗','🌖','🌕','🌔','🌓','🌒','🌑'];
const SPINNERS = ['⣾⣽','⣽⣻','⣻⢿','⢿⡿','⡿⣟','⣟⣯','⣯⣷','⣷⣾'];
const SPINNERS1 = ['▁⣾','▂⣽','▃⣻','▄⢿','▅⡿','▆⣟','▇⣯','█⣷','▇⣾','▆⣽','▅⣻','▄⢿','▃⡿','▂⣟','▁⣯'];
const DOTS = ['▪','▪▪','▪▪▪','▪▪▪▪'];

const startSpinner = (label, timeout = 300) => {
  const start = Date.now();
  let i = 0;
  let isPaused = false;
  let isStopped = false;
  const render = () => {
    if (isPaused || isStopped || STOP_SIGNAL) return;
    const elapsed = Math.floor((Date.now() - start) / 1000);
    const pct = timeout ? Math.min(100, Math.round((elapsed / timeout) * 100)) : 0;
    const sym = SYMBOLS[i % SYMBOLS.length], sp = SPINNERS[i % SPINNERS.length];
    const sp1 = SPINNERS1[i % SPINNERS1.length], dot = DOTS[elapsed % DOTS.length];
    i++;
    const c1 = 1 + Math.floor(Math.random() * 7), c2 = 1 + Math.floor(Math.random() * 7);
    const mm = String(Math.floor(elapsed / 60)).padStart(2, '0'), ss = String(elapsed % 60).padStart(2, '0');
    process.stdout.write(`${CLR} \x1b[1;3${c1}m ${sp}\x1b[1;37m ${label} \x1b[1;31m${mm}:${ss}\x1b[1;3${c2}m ${sym} ${sp1}\x1b[1;37m ${pct}%\x1b[1;33m ${dot}`);
  };
  const id = setInterval(render, 100);
  spinPause = () => { if (isPaused || isStopped) return; isPaused = true; process.stdout.write(CLR); };
  spinResume = () => { if (!isPaused || isStopped) return; isPaused = false; };
  return () => {
    if (isStopped) return;
    isStopped = true;
    clearInterval(id);
    spinPause = null;
    spinResume = null;
    process.stdout.write(CLR);
  };
};

const tmr = async (seconds, label = 'Waiting...') => {
  const total = Math.floor(seconds);
  if (total < 1) return;
  const start = Date.now();
  let i = 0;
  return new Promise(resolve => {
    const id = setInterval(() => {
      if (STOP_SIGNAL || isTimeUp()) { clearInterval(id); process.stdout.write(CLR); return resolve(); }
      const elapsed = Math.floor((Date.now() - start) / 1000);
      const remaining = Math.max(0, total - elapsed);
      const pct = Math.round(((total - remaining) / total) * 100);
      const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
      const ss = String(remaining % 60).padStart(2, '0');
      const sym = SYMBOLS[i % SYMBOLS.length], sp = SPINNERS[i % SPINNERS.length];
      const sp1 = SPINNERS1[i % SPINNERS1.length], dot = DOTS[elapsed % DOTS.length];
      i++;
      const c1 = 1 + Math.floor(Math.random() * 7), c2 = 1 + Math.floor(Math.random() * 7);
      process.stdout.write(`${CLR} \x1b[1;3${c1}m ${sp}\x1b[1;37m ${label} \x1b[1;31m${mm}:${ss}\x1b[1;3${c2}m ${sym} ${sp1}\x1b[1;37m ${pct}%\x1b[1;33m ${dot}`);
      if (remaining <= 0) { clearInterval(id); process.stdout.write(CLR); resolve(); }
    }, 100);
  });
};

const withSpinner = async (label, fn, timeout = 300) => {
  const stop = startSpinner(label, timeout);
  try { const r = await fn(); stop(); return r; } catch (e) { stop(); throw e; }
};

const blinkErr = async (message, durationMs = 2000) => {
  const start = Date.now();
  const tick = 250;
  let on = true;
  if (spinPause) spinPause();
  while (Date.now() - start < durationMs) {
    if (STOP_SIGNAL) break;
    if (on) process.stdout.write(`${CLR}${RED}[${now()}] ✗ ${String(message).toUpperCase()}${RST}`);
    else process.stdout.write(CLR);
    on = !on;
    await sleep(tick);
  }
  process.stdout.write(CLR);
  if (spinResume) spinResume();
};
const blinkWarn = async (message, durationMs = 2000) => {
  const start = Date.now();
  const tick = 250;
  let on = true;
  if (spinPause) spinPause();
  while (Date.now() - start < durationMs) {
    if (STOP_SIGNAL) break;
    if (on) process.stdout.write(`${CLR}${YEL}[${now()}] ⚠ ${message}${RST}`);
    else process.stdout.write(CLR);
    on = !on;
    await sleep(tick);
  }
  process.stdout.write(CLR);
  if (spinResume) spinResume();
};

const askQuestion = (q) => {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => {
    rl.question(q, a => { rl.close(); res(a); });
    rl.on('SIGINT', () => {
      rl.close();
      if (!STOP_SIGNAL) { STOP_SIGNAL = true; process.stdout.write(`${CLR}\n${YEL}⚠ Dihentikan. Kembali ke menu...${RST}\n`); }
      else { process.stdout.write(`\n${RED}Program keluar.${RST}\n`); process.exit(0); }
      res('');
    });
  });
};

const bannerMain = () => {
  console.log(headerTop(CYN));
  console.log(headerMid(`  ${BG_MERAH}${WHT} KUYANGIN DONG ${RST}`, CYN));
  console.log(headerBot(CYN));
  console.log('');
};

const defaultConfig = () => ({ provider: '', apikeys: {}, userAgent: '', cookie: '', bitcotasksLink: '' });
const saveConfig = (cfg) => fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
const loadConfig = () => {
  if (!fs.existsSync(CONFIG_PATH)) return null;
  try {
    const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    if (!cfg.apikeys) cfg.apikeys = {};
    if (typeof cfg.provider !== 'string') cfg.provider = '';
    if (typeof cfg.userAgent !== 'string') cfg.userAgent = '';
    if (typeof cfg.cookie !== 'string') cfg.cookie = '';
    if (typeof cfg.bitcotasksLink !== 'string') cfg.bitcotasksLink = '';
    delete cfg.email;
    delete cfg.password;
    return cfg;
  } catch { return null; }
};
const getApiKey = (provider) => {
  const cfg = loadConfig();
  if (!cfg || !cfg.apikeys) return '';
  return cfg.apikeys[provider] || '';
};
const setApiKey = (provider, key) => {
  const cfg = loadConfig() || defaultConfig();
  if (!cfg.apikeys) cfg.apikeys = {};
  cfg.apikeys[provider] = key;
  if (!cfg.provider) cfg.provider = provider;
  saveConfig(cfg);
};
const setActiveProvider = (provider) => {
  const cfg = loadConfig() || defaultConfig();
  cfg.provider = provider;
  saveConfig(cfg);
};
const maskKey = (k) => {
  if (!k) return '';
  if (k.length <= 12) return k;
  return k.slice(0, 8) + '...' + k.slice(-4);
};

class CookieJar {
  constructor() { this.map = new Map(); }
  set(host, setCookie) {
    if (!setCookie) return;
    const arr = Array.isArray(setCookie) ? setCookie : [setCookie];
    const key = host.toLowerCase();
    if (!this.map.has(key)) this.map.set(key, new Map());
    const store = this.map.get(key);
    for (const sc of arr) {
      const [kv] = sc.split(';');
      const eq = kv.indexOf('=');
      if (eq < 0) continue;
      const name = kv.slice(0, eq).trim(), value = kv.slice(eq + 1).trim();
      if (value === '' || /expires=Thu, 01 Jan 1970/i.test(sc)) store.delete(name);
      else store.set(name, value);
    }
  }
  header(host) {
    const store = this.map.get(host.toLowerCase());
    if (!store || !store.size) return '';
    return [...store.entries()].map(([k, v]) => `${k}=${v}`).join('; ');
  }
  save(file) {
    const obj = {};
    for (const [h, m] of this.map) obj[h] = Object.fromEntries(m);
    try { fs.writeFileSync(file, JSON.stringify(obj, null, 2)); } catch {}
  }
  load(file) {
    if (!fs.existsSync(file)) return;
    try {
      const obj = JSON.parse(fs.readFileSync(file, 'utf8'));
      for (const [h, m] of Object.entries(obj)) this.map.set(h, new Map(Object.entries(m)));
    } catch {}
  }
}
const jar = new CookieJar();
jar.load(COOKIE_PATH);

const applyCookieFromConfig = (cfg) => {
  if (!cfg.cookie) return;
  const parts = cfg.cookie.split(/[;\n]/).map(p => p.trim()).filter(Boolean);
  for (const p of parts) {
    const clean = p.replace(/^cookie:\s*/i, '').trim();
    if (clean && clean.includes('=')) jar.set(ORIGIN_HOST, [clean]);
  }
};

const request = (method, urlStr, opts = {}) => {
  const { headers = {}, body = null, followRedirect = true, maxRedirects = 5, timeout = 45000, _redirect = 0 } = opts;
  return new Promise(resolve => {
    let url;
    try { url = new URL(urlStr); } catch { return resolve({ status: 0, headers: {}, body: '', error: 'bad url' }); }
    const isHttps = url.protocol === 'https:';
    const port = url.port ? parseInt(url.port) : (isHttps ? 443 : 80);
    const finalHeaders = jitterHeaders({ ...headers });
    finalHeaders['Host'] = url.host;
    if (!finalHeaders['User-Agent']) finalHeaders['User-Agent'] = DEF_UA;
    if (!finalHeaders['Accept-Encoding']) finalHeaders['Accept-Encoding'] = 'gzip, deflate, br';
    const ck = jar.header(url.hostname);
    if (ck) finalHeaders['Cookie'] = ck;
    let bodyBuf = null;
    if (body != null) {
      if (Buffer.isBuffer(body)) bodyBuf = body;
      else if (typeof body === 'string') bodyBuf = Buffer.from(body, 'utf8');
      else if (body instanceof URLSearchParams) bodyBuf = Buffer.from(body.toString(), 'utf8');
      else bodyBuf = Buffer.from(new URLSearchParams(body).toString(), 'utf8');
      finalHeaders['Content-Length'] = bodyBuf.length;
    }
    const lib = isHttps ? https : http;
    const req = lib.request({
      method, host: url.hostname, port,
      path: url.pathname + url.search,
      headers: finalHeaders,
      rejectUnauthorized: false,
      timeout
    }, res => {
      const sc = res.headers['set-cookie'];
      if (sc) jar.set(url.hostname, sc);
      const chunks = [];
      res.on('data', ch => chunks.push(ch));
      res.on('end', async () => {
        let bodyStr = '';
        try {
          const buf = Buffer.concat(chunks);
          const enc = (res.headers['content-encoding'] || '').toLowerCase();
          if (enc === 'gzip') bodyStr = zlib.gunzipSync(buf).toString('utf8');
          else if (enc === 'deflate') bodyStr = zlib.inflateSync(buf).toString('utf8');
          else if (enc === 'br') bodyStr = zlib.brotliDecompressSync(buf).toString('utf8');
          else bodyStr = buf.toString('utf8');
        } catch { bodyStr = Buffer.concat(chunks).toString('utf8'); }
        if (followRedirect && [301,302,303,307,308].includes(res.statusCode) && res.headers.location && _redirect < maxRedirects) {
          const nextUrl = new URL(res.headers.location, urlStr).href;
          const nextMethod = (res.statusCode === 303 || ((res.statusCode === 301 || res.statusCode === 302) && method === 'POST')) ? 'GET' : method;
          return resolve(await request(nextMethod, nextUrl, { ...opts, body: nextMethod === 'GET' ? null : body, _redirect: _redirect + 1 }));
        }
        resolve({ status: res.statusCode, headers: res.headers, body: bodyStr });
      });
      res.on('error', e => resolve({ status: 0, body: '', error: e.message }));
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', e => resolve({ status: 0, headers: {}, body: '', error: e.message }));
    if (bodyBuf) req.write(bodyBuf);
    req.end();
  });
};

const buildMultipart = (fields) => {
  const boundary = '----WebKitFormBoundary' + crypto.randomBytes(8).toString('hex');
  const parts = [];
  for (const [name, value] of Object.entries(fields)) {
    parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`));
  }
  parts.push(Buffer.from(`--${boundary}--\r\n`));
  return { body: Buffer.concat(parts), contentType: `multipart/form-data; boundary=${boundary}` };
};

const normalizeSolverResp = (raw) => {
  const text = (raw || '').trim();
  if (!text) return { status: 0, request: '' };
  if (text.startsWith('OK|')) {
    const payload = text.slice(3).trim();
    if (payload === 'CAPCHA_NOT_READY' || payload === 'CAPTCHA_NOT_READY') return { status: 0, request: 'CAPCHA_NOT_READY' };
    return { status: 1, request: payload };
  }
  if (text.startsWith('{')) {
    try {
      const j = JSON.parse(text);
      const ok = j.status === 1 || j.status === '1' || j.status === 'OK';
      if (ok) return { status: 1, request: j.request || j.result || '' };
      return { status: 0, request: j.request || j.error || j.message || '' };
    } catch {}
  }
  return { status: 0, request: text };
};

const buildSolverBody = (p, fields) => {
  if (p.submitType === 'json') return { body: JSON.stringify(fields), contentType: 'application/json' };
  if (p.submitType === 'multipart') return buildMultipart(fields);
  return { body: new URLSearchParams(fields).toString(), contentType: 'application/x-www-form-urlencoded' };
};

const solverSubmit = async (providerId, fields) => {
  const p = PROVIDERS[providerId];
  if (!p) throw new Error('Unknown provider: ' + providerId);
  const { body, contentType } = buildSolverBody(p, fields);
  const res = await request('POST', `${p.proto}://${p.host}${p.submitUrl}`, {
    headers: { 'Content-Type': contentType, 'Accept': 'application/json' },
    body, timeout: 30000
  });
  return normalizeSolverResp(res.body);
};

const solverPoll = async (providerId, apikey, taskId) => {
  const p = PROVIDERS[providerId];
  if (!p) throw new Error('Unknown provider: ' + providerId);
  const params = new URLSearchParams({
    [p.pollKey]: apikey, [p.pollActionKey]: p.pollActionValue, [p.pollIdKey]: taskId, json: '1'
  }).toString();
  let res;
  const url = `${p.proto}://${p.host}${p.pollUrl}`;
  if (p.pollMethod === 'POST') {
    res = await request('POST', url, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' },
      body: params, timeout: 30000
    });
  } else {
    res = await request('GET', `${url}?${params}`, { headers: { 'Accept': 'application/json' }, timeout: 30000 });
  }
  return normalizeSolverResp(res.body);
};

const runSolver = async (providerId, methodLabel, payload, timeoutSec = 180, maxAttempts = 3) => {
  const rawKey = getApiKey(providerId) || API_KEY;
  if (!rawKey) return [null, 'NO_APIKEY'];
  const apikey = rawKey.trim();
  let lastError = null;
  let attempt = 0;
  let unsolvableStreak = 0;
  const MAX_UNSOLVABLE = 5;

  while (true) {
    if (STOP_SIGNAL || isTimeUp()) return [null, 'STOPPED'];
    attempt++;
    const stop = startSpinner(`${PROVIDERS[providerId].name} ${methodLabel}`, timeoutSec);

    let taskId;
    try {
      const sub = await solverSubmit(providerId, payload);
      if (STOP_SIGNAL) { stop(); return [null, 'STOPPED']; }
      if (sub.status !== 1 || !sub.request) {
        stop();
        const raw = String(sub.request || 'SUBMIT_FAILED');
        const info = classifySolverError(raw);
        if (info && info.kind === 'fatal') { await blinkErr(`FATAL: ${info.msg}`, 2500); return [null, raw]; }
        lastError = raw;
        await blinkWarn(`${info ? info.msg : raw} — retry...`, 1500);
        await sleep(1500);
        continue;
      }
      taskId = sub.request;
    } catch (e) {
      stop();
      lastError = 'SUBMIT_NET:' + e.message;
      await blinkWarn('Network error — retry...', 1500);
      await sleep(1500);
      continue;
    }

    const pStart = Date.now();
    let outcome = null;
    while (Date.now() - pStart < timeoutSec * 1000) {
      if (STOP_SIGNAL || isTimeUp()) { stop(); return [null, 'STOPPED']; }
      await sleep(3000);
      let r;
      try { r = await solverPoll(providerId, apikey, taskId); } catch (e) { continue; }
      if (r.status === 1 && r.request) { outcome = { type: 'success', token: r.request }; break; }
      const raw = String(r.request || '');
      const info = classifySolverError(raw);
      if (info && info.kind === 'polling') continue;
      if (info && info.kind === 'fatal') { outcome = { type: 'fatal', error: raw, info }; break; }
      if (info && info.kind === 'rate') { outcome = { type: 'rate', error: raw, info }; break; }
      if (info && info.kind === 'server') { outcome = { type: 'server', error: raw, info }; break; }
      if (info && info.kind === 'retry') { outcome = { type: 'retry', error: raw, info }; break; }
      if (raw) { outcome = { type: 'retry', error: raw, info: null }; break; }
    }
    stop();
    if (!outcome) outcome = { type: 'timeout', error: 'POLL_TIMEOUT' };
    if (outcome.type === 'success') return [outcome.token, null];
    if (outcome.type === 'fatal') { await blinkErr(`FATAL: ${outcome.info.msg}`, 2500); return [null, outcome.error]; }
    lastError = outcome.error;
    if (outcome.error === 'ERROR_CAPTCHA_UNSOLVABLE') {
      unsolvableStreak++;
      await blinkErr('Error Unsolvable', 3000);
      if (unsolvableStreak >= MAX_UNSOLVABLE) { await blinkErr(`Unsolvable ${MAX_UNSOLVABLE}x`, 3000); return [null, 'UNSOLVABLE_STREAK']; }
      await sleep(500);
      continue;
    }
    unsolvableStreak = 0;
    if (attempt >= maxAttempts) {
      const info = classifySolverError(lastError);
      await blinkErr(`${info ? info.msg : lastError || 'UNKNOWN'}`, 2500);
      return [null, lastError || 'EXHAUSTED'];
    }
    if (outcome.type === 'rate') { await blinkWarn(`${outcome.info.msg} — retry ${attempt + 1}/${maxAttempts}`, 1500); await tmr(8, 'Rate limit...'); continue; }
    if (outcome.type === 'server') { await blinkWarn(`${outcome.info.msg} — retry ${attempt + 1}/${maxAttempts}`, 1500); await tmr(5, 'Server error...'); continue; }
    const msg = outcome.info ? outcome.info.msg : outcome.error;
    await blinkWarn(`${msg} — retry ${attempt + 1}/${maxAttempts}`, 1800);
    await sleep(1500);
  }
};

const solveHcaptcha = async (providerId, pageUrl, sitekey) => {
  const p = PROVIDERS[providerId];
  if (!p || !p.hcaptcha) return [null, 'NO_HCAPTCHA_METHOD'];
  const rawKey = getApiKey(providerId) || API_KEY;
  if (!rawKey) return [null, 'NO_APIKEY'];
  const fields = {
    [p.submitKey]: rawKey.trim(),
    [p.methodField]: 'hcaptcha',
    [p.hcaptcha.sitekeyParam]: sitekey || SITEKEY,
    [p.hcaptcha.domainParam]: pageUrl || HOST,
    json: 1
  };
  return await runSolver(providerId, '[hCaptcha]', fields, 180);
};

const solveImageCaptcha = async (providerId, imageBase64) => {
  const p = PROVIDERS[providerId];
  if (!p) return [null, 'NO_PROVIDER'];
  const rawKey = getApiKey(providerId) || API_KEY;
  if (!rawKey) return [null, 'NO_APIKEY'];
  const fields = {
    [p.submitKey]: rawKey.trim(),
    [p.methodField]: p.imageMethod,
    [p.imageKey]: imageBase64,
    json: 1
  };
  return await runSolver(providerId, `[${p.imageMethodLabel}]`, fields, 180);
};

const parseCoords = (answer) => {
  if (!answer) return null;
  let m = answer.match(/x["'=:\s]*(\d+)\s*[,;].*?y["'=:\s]*(\d+)/i);
  if (m) return { x: +m[1], y: +m[2] };
  m = answer.match(/^(\d+)\s*[,;]\s*(\d+)$/);
  if (m) return { x: +m[1], y: +m[2] };
  return null;
};

const parseCsrf = (html) => {
  if (!html) return null;
  const meta = html.match(/<meta\s+name="csrf-token"\s+content="([^"]+)"/);
  if (meta) return meta[1];
  for (const pat of [/name="_token"\s+value="([^"]+)"/, /name='_token'\s+value='([^']+)'/, /name="csrf_token_name"\s+value="([^"]+)"/]) {
    const m = html.match(pat);
    if (m) return m[1];
  }
  return null;
};
const detectSitekey = (html) => {
  if (!html) return null;
  for (const pat of [/data-sitekey="([^"]+)"/, /data-hcaptcha-sitekey="([^"]+)"/, /sitekey['"]\s*:\s*['"]([^'"]+)['"]/]) {
    const m = html.match(pat);
    if (m) return m[1];
  }
  return null;
};
const isLoggedIn = (html) => html && (html.includes('action="https://cryptoadpay.com/logout"') || html.includes('/logout') || html.includes('>Logout<'));

const isLimitReached = (html) => {
  if (!html) return false;
  const hasClaimForm = html.includes('action="/faucet/claim"') || html.includes('action="https://cryptoadpay.com/faucet/claim"');
  if (hasClaimForm) return false;
  if (html.includes('Daily limit reached') || html.includes('Limit reached') || html.includes('limit reached') || html.includes('200/200')) return true;
  return false;
};
const isFaucetPaused = (html) => html && (html.includes('Faucet Paused') || html.includes('Complete the pause requirements'));
const parseFaucetPause = (html) => {
  if (!html) return { current: 0, max: 20 };
  const m = html.match(/<span>Pause Progress<\/span><span>(\d+)\/(\d+)<\/span>/i);
  if (m) return { current: parseInt(m[1], 10), max: parseInt(m[2], 10) };
  return { current: 0, max: 20 };
};
const isFaucetSuccess = (html) => html && (/flashType\s*=\s*"success"/.test(html) || html.includes('added to your balance') || html.includes('Good job'));
const extractFlashMessage = (html) => {
  if (!html) return null;
  const fm = html.match(/var\s+flashMessage\s*=\s*"([^"]+)"/);
  if (!fm) return null;
  let rawMsg = fm[1].replace(/\\u([0-9a-fA-F]{4})/g, (m, g) => String.fromCharCode(parseInt(g, 16)));
  return rawMsg.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() || null;
};
const getFaucetRemainingTime = (html) => {
  if (!html) return null;
  const m = html.match(/var\s+remainingTime\s*=\s*(\d+)\s*;/);
  return m ? parseInt(m[1], 10) : null;
};
const parseBalanceFromJson = (body) => {
  try { const j = JSON.parse(body); if (j.success && j.balance) { const m = String(j.balance).match(/([\d,]+\.\d+)/); if (m) return parseFloat(m[1].replace(/,/g, '')); } } catch {}
  return null;
};
const parseBalanceFromHtml = (html) => {
  if (!html) return null;
  const m = html.match(/Account Balance[^0-9]*([\d,]+\.\d+)/i);
  if (m) { try { return parseFloat(m[1].replace(/,/g, '')); } catch {} }
  return null;
};
const randomFaucetWait = () => FAUCET_MIN_WAIT + Math.floor(Math.random() * (FAUCET_MAX_WAIT - FAUCET_MIN_WAIT + 1));

const refreshBalance = async () => {
  try {
    const r = await request('GET', `${HOST}/get-balance`, { headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }, maxRedirects: 5 });
    if (r.status === 200) { const bal = parseBalanceFromJson(r.body); if (bal != null) return bal; }
  } catch {}
  try {
    const r = await request('GET', `${HOST}/dashboard`, { maxRedirects: 5 });
    if (isLoggedIn(r.body)) { const bal = parseBalanceFromHtml(r.body); if (bal != null) return bal; }
  } catch {}
  return null;
};

const verifySession = async () => {
  try {
    const r = await request('GET', `${HOST}/dashboard`, { maxRedirects: 5 });
    return { ok: isLoggedIn(r.body), html: r.body };
  } catch (e) {
    return { ok: false, error: e.message };
  }
};

const runFaucet = async (cfg) => {
  const hdr = { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9' };
  let claimCount = 0;
  let target = FAUCET_BATCH;
  let oldBal = await refreshBalance();

  while (!STOP_SIGNAL && claimCount < target && !isTimeUp()) {
    try {
      await humanDelayVar();
      const r = await request('GET', `${HOST}/faucet`, { headers: hdr, maxRedirects: 5 });
      if (STOP_SIGNAL || isTimeUp()) return { count: claimCount, paused: false, limited: false };
      const html = r.body;

      if (!isLoggedIn(html)) {
        log('Session expired — cookie invalid.', 'er');
        return { count: claimCount, paused: false, limited: false, sessionExpired: true };
      }

      if (isFaucetPaused(html)) {
        const prog = parseFaucetPause(html);
        console.log('');
        log('Faucet Paused!', 'wr');
        return { count: claimCount, paused: true, current: prog.current, max: prog.max, limited: false };
      }

      if (isLimitReached(html)) {
        console.log('');
        log('Faucet limit reached (200/200)', 'limit');
        return { count: claimCount, paused: false, limited: true };
      }

      if (isFaucetSuccess(html)) {
        claimCount++;
        const nb = await refreshBalance();
        const successMsg = extractFlashMessage(html) || 'added to your balance!';
        claimOut(`✓ [${claimCount}/${target}] ${successMsg}`);
        if (nb != null) { claimOutLine(`${WHT}[${now()}]${RST} ${MAG}»${RST} New Balance: ${YEL}${nb.toFixed(2)}${RST}`); oldBal = nb; }
        if (claimCount >= target) break;
        await tmr(randomFaucetWait(), 'Waiting...');
        continue;
      }

      const remaining = getFaucetRemainingTime(html);
      const csrf = parseCsrf(html);
      const sitekey = detectSitekey(html) || SITEKEY;
      const hasClaimForm = html.includes('action="/faucet/claim"') || html.includes('action="https://cryptoadpay.com/faucet/claim"');

      if (remaining != null && remaining > 0) { await tmr(remaining + 3 + Math.floor(Math.random() * 3), 'Cooldown faucet...'); continue; }
      if (!hasClaimForm || !csrf) { await tmr(10, 'Waiting faucet ready...'); continue; }

      // CAPTCHA — no delay
      const [capToken, capErr] = await solveHcaptcha(PROVIDER, `${HOST}/faucet`, sitekey);
      if (STOP_SIGNAL || isTimeUp()) return { count: claimCount, paused: false, limited: false };
      if (!capToken) { await sleep(3000); continue; }

      const payload = new URLSearchParams({ _token: csrf, 'g-recaptcha-response': capToken, 'h-captcha-response': capToken }).toString();
      const r2 = await request('POST', `${HOST}/faucet/claim`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Referer': `${HOST}/faucet`, 'Origin': HOST },
        body: payload, maxRedirects: 0
      });
      if (STOP_SIGNAL || isTimeUp()) return { count: claimCount, paused: false, limited: false };

      let finalHtml = r2.body;
      if (r2.status === 302 && r2.headers.location) {
        const followRes = await request('GET', r2.headers.location.startsWith('http') ? r2.headers.location : `${HOST}${r2.headers.location}`, { headers: hdr, maxRedirects: 5 });
        if (STOP_SIGNAL || isTimeUp()) return { count: claimCount, paused: false, limited: false };
        finalHtml = followRes.body;
      }

      if (isFaucetSuccess(finalHtml)) {
        claimCount++;
        const nb = await refreshBalance();
        const successMsg = extractFlashMessage(finalHtml) || 'added to your balance!';
        claimOut(`✓ [${claimCount}/${target}] ${successMsg}`);
        if (nb != null) { claimOutLine(`${WHT}[${now()}]${RST} ${MAG}»${RST} New Balance: ${YEL}${nb.toFixed(2)}${RST}`); oldBal = nb; }
        if (claimCount >= target) break;
        await tmr(randomFaucetWait(), 'Waiting...');
        continue;
      }

      if (isLimitReached(finalHtml)) {
        log('Faucet limit reached (200/200)', 'limit');
        return { count: claimCount, paused: false, limited: true };
      }

      const msg = extractFlashMessage(finalHtml) || `HTTP ${r2.status}`;
      log(`Faucet: ${msg}`, 'wr');
      await tmr(randomFaucetWait(), 'Waiting...');
    } catch (e) {
      if (bumpError('FAUCET', e.message)) return { count: claimCount, paused: false, limited: false };
      await sleep(5000);
    }
  }
  return { count: claimCount, paused: false, limited: false };
};

const parseOfferwallUrl = (url) => {
  try {
    const p = new URL(url);
    const seg = p.pathname.replace(/^\/+|\/+$/g, '').split('/');
    if (seg[0] !== 'offerwall' || seg.length < 3) return null;
    return { key: seg[1], subId: seg[2], hash: seg[3] || null };
  } catch { return null; }
};

const getAutoBitcoLink = async () => {
  const paths = ['/offerwall/bitcotasks', '/offerwalls', '/earn', '/dashboard'];
  for (const p of paths) {
    if (STOP_SIGNAL || isTimeUp()) return null;
    try {
      await humanDelayVar();
      const r = await request('GET', `${HOST}${p}`, { maxRedirects: 5 });
      if (isLoggedIn(r.body)) {
        const match = r.body.match(/https:\/\/bitcotasks\.com\/offerwall\/[a-zA-Z0-9_\/\-]+/i);
        if (match) return match[0];
      }
    } catch (e) {
      if (bumpError('AUTO-BITCO', e.message)) return null;
    }
  }
  return null;
};

const pickVar = (html, name) => {
  const pats = [
    new RegExp(`(?:var|let|const)\\s+${name}\\s*=\\s*['"]([^'"]+)['"]`),
    new RegExp(`data-${name.replace(/_/g,'-')}\\s*=\\s*['"]([^'"]+)['"]`),
    new RegExp(`"${name}"\\s*:\\s*"([^"]+)"`)
  ];
  for (const p of pats) { const m = html.match(p); if (m) return m[1]; }
  return null;
};

const solveBitcoCaptcha = async (html, pageUrl) => {
  let jsUrl = null;
  for (const pat of [
    /<script[^>]+src=["'](\/captcha2\/[^"']+\.js\?[^"']+)["']/i,
    /src=["'](\/captcha2\/[^"']+)["']/i,
    /["'](\/captcha2\/[a-f0-9]+\.js[^"']*)["']/i
  ]) {
    const m = html.match(pat);
    if (m) { jsUrl = new URL(m[1], pageUrl).href; break; }
  }
  if (!jsUrl) { log('Captcha JS tidak ditemukan', 'wr'); return null; }

  const jsRes = await request('GET', jsUrl, {
    headers: { 'Accept': '*/*', 'Referer': pageUrl, 'Sec-Fetch-Dest': 'script', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-origin' }
  });
  if (STOP_SIGNAL) return null;
  const js = jsRes.body || '';
  if (!js || js.length < 50) { log('Captcha JS empty', 'wr'); return null; }

  let p = null;
  for (const pat of [
    /(?:var|let|const)\s+payload\s*=\s*["']([A-Za-z0-9_]+)=([^"'&]*)&([A-Za-z0-9_]+)=["']/,
    /payload\s*[:=]\s*["']([A-Za-z0-9_]+)=([^"'&]*)&([A-Za-z0-9_]+)=/
  ]) { p = js.match(pat); if (p) break; }
  if (!p) { log('Captcha pattern invalid', 'wr'); return null; }
  const fn1 = p[1], fv = p[2], fn2 = p[3];

  let sMatch = js.match(/if\s*\(\s*response\.([A-Za-z0-9_]+)\s*\)/) || js.match(/response\.([A-Za-z0-9_]+)/);
  if (!sMatch) { log('Captcha pattern invalid', 'wr'); return null; }
  const successField = sMatch[1];

  const allResp = [...js.matchAll(/=\s*response\.([A-Za-z0-9_]+)/g)].map(m => m[1]);
  const tokenField = allResp.find(f => f !== successField);
  if (!tokenField) { log('Captcha pattern invalid', 'wr'); return null; }

  const vMatch = js.match(/\/captcha2\/([a-zA-Z0-9_]+)\?action=data&cdata=([a-f0-9]+)/);
  if (!vMatch) { log('Captcha pattern invalid', 'wr'); return null; }
  const verifyShort = vMatch[1], cdata = vMatch[2];

  const dMatch = js.match(/getElementById\(\s*["']([^"']+)["']\s*\)\s*\.\s*value\s*=\s*response\./);
  const dynamicField = dMatch ? dMatch[1] : null;

  const prov = PROVIDERS[PROVIDER];
  const solvingLabel = `${prov.name} [${prov.imageMethodLabel}]`;

  for (let attempt = 1; attempt <= 3; attempt++) {
    if (STOP_SIGNAL || isTimeUp()) return null;
    // CAPTCHA — no delay
    const imgRes = await request('POST', jsUrl, {
      headers: { 'Content-Type': 'application/json', 'Accept': '*/*', 'Referer': pageUrl, 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ t: Date.now(), r: Math.random() })
    });
    if (STOP_SIGNAL) return null;
    let imgJson;
    try { imgJson = JSON.parse(imgRes.body); } catch { continue; }
    if (imgJson.error) {
      if (imgJson.error === 'rate_limited') { await tmr(imgJson.retryAfter || 60, 'Rate limited'); continue; }
      log('Captcha api: ' + imgJson.error, 'wr');
      continue;
    }
    const image = imgJson.image || imgJson.gif || imgJson.preload || '';
    if (image.length < 100) { log('Image kosong', 'wr'); continue; }

    const [answer, err] = await withSpinner(solvingLabel, () => solveImageCaptcha(PROVIDER, image), 600);
    if (STOP_SIGNAL) return null;
    if (!answer) { await blinkWarn(err || 'Solver gagal', 2000); continue; }

    const coords = parseCoords(answer);
    if (!coords) { log('Parse coords fail', 'wr'); continue; }

    const submitBody = `${fn1}=${encodeURIComponent(fv)}&${fn2}=${encodeURIComponent(`[${coords.x},${coords.y}]`)}`;
    const verifyUrl = new URL(`/captcha2/${verifyShort}?action=data&cdata=${cdata}`, pageUrl).href;

    const subRes = await request('POST', verifyUrl, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN, 'Referer': pageUrl },
      body: submitBody
    });
    if (STOP_SIGNAL) return null;
    let subJson;
    try { subJson = JSON.parse(subRes.body); } catch { continue; }
    if (!subJson[successField]) { log('Submit invalid', 'wr'); continue; }
    const captchaToken = subJson[tokenField];
    if (!captchaToken) { log('Token kosong', 'wr'); continue; }
    return { token: captchaToken, field: dynamicField };
  }
  return null;
};

const bypassFirewall = async (owUrl) => {
  if (STOP_SIGNAL || isTimeUp()) return null;
  await humanDelayVar();
  const r1 = await request('GET', owUrl, { headers: { Accept: 'text/html' }, followRedirect: false });
  if (STOP_SIGNAL) return null;
  if (r1.status === 0) { log('net error: ' + r1.error, 'er'); return null; }
  let firewallUrl = null;
  const redir = r1.body.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
  if (redir) firewallUrl = new URL(redir[1], owUrl).href;
  else if (owUrl.includes('firewall.php')) firewallUrl = owUrl;
  if (!firewallUrl) return { html: r1.body, url: owUrl };

  const fwRes = await request('GET', firewallUrl, { headers: { Accept: 'text/html' } });
  if (STOP_SIGNAL) return null;
  const fwHtml = fwRes.body;
  const ctnMatch = fwHtml.match(/const\s+captchaTokenName\s*=\s*"([^"]+)"/);
  if (!ctnMatch) return { html: fwHtml, url: firewallUrl };
  const ctn = ctnMatch[1];

  log('Firewall captcha...', 'in');
  const cap = await solveBitcoCaptcha(fwHtml, firewallUrl);
  if (STOP_SIGNAL) return null;
  if (!cap || !cap.token) { await blinkWarn('Firewall captcha gagal', 2500); return null; }

  const valRes = await request('POST', firewallUrl, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
    body: new URLSearchParams({ action: 'validate', [ctn]: cap.token }).toString()
  });
  if (STOP_SIGNAL) return null;
  let vj;
  try { vj = JSON.parse(valRes.body); } catch {}
  let nextUrl = null;
  if (vj && vj.status === 'success' && vj.redirect) nextUrl = new URL(vj.redirect, BITCO_ORIGIN).href;
  else {
    const m = valRes.body.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
    if (m) nextUrl = new URL(m[1], BITCO_ORIGIN).href;
  }
  if (!nextUrl) { await blinkWarn('Firewall validate gagal', 2500); return null; }

  const finalRes = await request('GET', nextUrl, { headers: { Accept: 'text/html' } });
  if (STOP_SIGNAL) return null;
  return { html: finalRes.body, url: nextUrl };
};

const processBitcoTask = async (task, owUrl, owToken, idx, total) => {
  if (STOP_SIGNAL || isTimeUp()) return false;
  try {
    log(`${YEL}TASK ${idx}/${total}${RST} — ${CYN}${task.title || 'Unknown'}${RST} ${GRN}+${task.reward || 0}${RST}`, 'i');

    const initRes = await withSpinner('Init transaction...', () => request('POST', owUrl, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN },
      body: new URLSearchParams({
        hash: task.hash || '', sid: task.sid || '', key: task.key || '', type: 'ptc', token: owToken, action: 'init_transaction'
      }).toString()
    }), 15);
    if (STOP_SIGNAL) return false;

    let initJson;
    try { initJson = JSON.parse(initRes.body); } catch { log('init parse fail', 'er'); return false; }
    if (!initJson.offer) { log('no offer', 'er'); return false; }
    const offerUrl = initJson.offer;

    await humanDelayVar();
    const leadRes = await request('GET', offerUrl, { headers: { Accept: 'text/html' } });
    if (STOP_SIGNAL) return false;
    const leadHtml = leadRes.body;
    const vars = {
      token: pickVar(leadHtml, 'token'),
      hash: pickVar(leadHtml, 'hash'),
      subId: pickVar(leadHtml, 'sub_id'),
      key: pickVar(leadHtml, 'key') || pickVar(leadHtml, 'api_key'),
      ctoken: pickVar(leadHtml, 'ctoken')
    };
    if (!vars.token || !vars.hash || !vars.subId || !vars.key) { log('vars missing', 'er'); return false; }

    await request('GET', `${BITCO_ORIGIN}/firewall.php?key=${encodeURIComponent(vars.key)}&sub_id=${encodeURIComponent(vars.subId)}`, { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': '*/*' } });
    if (STOP_SIGNAL) return false;

    // CAPTCHA — no delay
    log('Captcha challenge...', 'in');
    const cap = await solveBitcoCaptcha(leadHtml, offerUrl);
    if (STOP_SIGNAL) return false;
    if (!cap || !cap.token) return false;

    log('start_view...', 'in');
    let svRes = await request('POST', offerUrl, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest',
        'Origin': BITCO_ORIGIN, 'Accept': '*/*', 'Referer': offerUrl,
        'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'
      },
      body: 'action=start_view'
    });
    if (STOP_SIGNAL) return false;

    if (svRes.status === 429) {
      await tmr(6, 'Retry 429');
      await request('POST', offerUrl, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest',
          'Origin': BITCO_ORIGIN, 'Accept': '*/*', 'Referer': offerUrl,
          'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'
        },
        body: 'action=start_view'
      });
      if (STOP_SIGNAL) return false;
    }

    let duration = 30;
    const dm = leadHtml.match(/(?:var|let|const)\s+duration\s*=\s*(\d+)/);
    if (dm) { const parsed = parseInt(dm[1]); if (parsed >= 5 && parsed <= 300) duration = parsed; }
    await tmr(duration + 5, `⏳ Ad running (${duration}s)`);
    if (STOP_SIGNAL || isTimeUp()) return false;

    const dynField = cap.field || vars.ctoken;
    if (!dynField) return false;

    const confirmParams = new URLSearchParams({
      action: 'proccessLead', hash: vars.hash, key: vars.key, sub_id: vars.subId, sid: vars.subId, token: vars.token
    });
    confirmParams.append(dynField, cap.token);

    const confirmRes = await withSpinner('Submitting...', () => request('POST', `${BITCO_ORIGIN}/system/ajax.php`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest',
        'Origin': BITCO_ORIGIN, 'Accept': '*/*', 'Referer': offerUrl,
        'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'
      },
      body: confirmParams.toString()
    }), 30);
    if (STOP_SIGNAL) return false;

    let cj;
    try { cj = JSON.parse(confirmRes.body); } catch { log(`parse fail`, 'er'); return false; }

    if ((cj.status || 0) == 200 && cj.success !== false) {
      claimOut(`✓ [${idx}/${total}] +${task.reward} coins`);
      if (cj.redirect) {
        await request('GET', cj.redirect, {
          headers: { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Referer': offerUrl, 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site' },
          timeout: 15000, followRedirect: true, maxRedirects: 3
        });
      }
      await sleep(2000);
      return true;
    }
    log(`❌ Gagal: status=${cj.status}`, 'er');
    return false;
  } catch (e) {
    if (bumpError('BITCO-TASK', e.message)) return false;
    return false;
  }
};

const runBitcotasks = async (cfg, targetSuccess) => {
  if (!cfg.bitcotasksLink) { log('Bitcotasks link belum di-set', 'wr'); return 0; }
  const parsed = parseOfferwallUrl(cfg.bitcotasksLink);
  if (!parsed) { log('Bitcotasks link invalid', 'er'); return 0; }

  const owUrl = `${BITCO_ORIGIN}/offerwall/${parsed.key}/${parsed.subId}`;
  log('Loading offerwall...', 'or');
  const fw = await bypassFirewall(owUrl);
  if (STOP_SIGNAL || isTimeUp()) return 0;
  if (!fw) { await blinkWarn('Firewall bypass failed', 2500); return 0; }

  const tm = fw.html.match(/var\s+token\s*=\s*['"]([^'"]+)['"]/);
  if (!tm) { await blinkWarn('Offerwall token tidak ditemukan', 2500); return 0; }
  const owToken = tm[1];
  log('Firewall bypassed', 'ok');

  log('Fetching PTC tasks...', 'in');
  const swRes = await withSpinner('switch_cat ptc...', () => request('POST', fw.url, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', 'Origin': BITCO_ORIGIN },
    body: new URLSearchParams({ token: owToken, action: 'switch_cat', type: 'ptc' }).toString()
  }), 20);
  if (STOP_SIGNAL) return 0;

  let tasks = [];
  try { const sj = JSON.parse(swRes.body); tasks = sj.items || []; } catch { log(`switch_cat parse fail`, 'er'); return 0; }
  if (!tasks.length) { log('No PTC tasks available', 'wr'); return 0; }

  log(`Found ${tasks.length} tasks (target: ${targetSuccess} sukses)`, 'ok');
  let ok = 0, fail = 0;
  const MAX_RETRY = 5;

  for (let i = 0; i < tasks.length && ok < targetSuccess && !STOP_SIGNAL && !isTimeUp(); i++) {
    let success = false, attempt = 0;
    while (attempt <= MAX_RETRY && !STOP_SIGNAL && !isTimeUp()) {
      success = await processBitcoTask(tasks[i], fw.url, owToken, i + 1, tasks.length);
      if (STOP_SIGNAL || isTimeUp()) break;
      if (success) break;
      attempt++;
      if (attempt <= MAX_RETRY) await sleep(1500);
    }
    if (STOP_SIGNAL || isTimeUp()) break;
    if (success) ok++; else fail++;
    jar.save(COOKIE_PATH);
    if (i < tasks.length - 1 && ok < targetSuccess) await tmr(6 + Math.floor(Math.random() * 4), 'Delay');
  }

  return ok;
};

const runFullCycle = async (cfg) => {
  while (!STOP_SIGNAL && !isTimeUp()) {
    try {
      const faucetRes = await runFaucet(cfg);
      if (STOP_SIGNAL || isTimeUp()) break;
      if (faucetRes.sessionExpired) {
        log('⛔ Cookie expired. Update cookie di menu [3].', 'er');
        await askQuestion(`${WHT}  Press Enter to return to menu...${RST}`);
        break;
      }
      log(`Faucet cycle selesai: ${faucetRes.count}/${FAUCET_BATCH} claim`, 'ok');

      if (faucetRes.limited) {
        console.log('');
        await askQuestion(`${WHT}  Press Enter to return to menu...${RST}`);
        break;
      }

      let targetBitco = BITCO_BATCH;
      if (faucetRes.paused) {
        const needed = faucetRes.max - faucetRes.current;
        if (needed > 0) {
          log(`Butuh ${needed} task Bitcotasks lagi untuk unpause Faucet.`, 'wr');
          targetBitco = needed;
        } else {
          log(`Pause progress penuh tapi faucet masih pause?`, 'wr');
        }
      }

      await tmr(5, 'Transisi ke Bitcotasks...');
      if (STOP_SIGNAL || isTimeUp()) break;

      let autoLink = await getAutoBitcoLink();
      if (STOP_SIGNAL || isTimeUp()) break;

      if (autoLink) {
        cfg.bitcotasksLink = autoLink;
        saveConfig(cfg);
      } else {
        if (!cfg.bitcotasksLink) {
          log('Gagal auto-find & link belum diset. Masukkan manual:', 'wr');
          const input = (await askQuestion('Bitcotasks Link : ')).trim();
          if (input) { cfg.bitcotasksLink = input; saveConfig(cfg); }
          else { await blinkErr('Link invalid. Cycle berhenti.', 2000); break; }
        } else {
          log('Auto-find gagal, pakai link tersimpan.', 'wr');
        }
      }

      const bitcoCount = await runBitcotasks(cfg, targetBitco);
      if (STOP_SIGNAL || isTimeUp()) break;
      log(`Bitcotasks cycle selesai: ${bitcoCount}/${targetBitco} sukses`, 'ok');

      await tmr(10, 'Transisi ke Faucet...');
    } catch (e) {
      if (bumpError('CYCLE', e.message)) break;
      await sleep(5000);
    }
  }
};

const tampilkanMenu = (cfg, balStr) => {
  clear();
  bannerMain();

  console.log(`  ${YEL}▸${RST} ${WHT}Channel      ${RST}: ${GRN}@bijikelot_v5${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Creator      ${RST}: ${GRN}iyannn${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Version      ${RST}: ${GRN}Ceban${RST}`);
  console.log(`  ${YEL}▸${RST} ${WHT}Status       ${RST}: ${GRN}Ngopi Dong${RST}`);
  console.log("");

  console.log(`  ${CYN}◉${RST} ${ABU}Site         ${RST}: ${CYN}${HOST}${RST}`);

  const uaDisp = cfg.userAgent ? `${GRN}${cfg.userAgent.slice(0,40)}...${RST}` : `${RED}✗ belum diset${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}User-Agent   ${RST}: ${uaDisp}`);

  const ckDisp = cfg.cookie ? `${GRN}✓ set (${cfg.cookie.length} chars)${RST}` : `${RED}✗ belum diset${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Cookie       ${RST}: ${ckDisp}`);

  const provDisp = PROVIDER && PROVIDERS[PROVIDER] ? `${GRN}${PROVIDERS[PROVIDER].name}${RST}` : `${WHT}-${RST}`;
  console.log(`  ${CYN}◉${RST} ${ABU}Provider     ${RST}: ${provDisp}`);

  if (balStr) console.log(`  ${CYN}◉${RST} ${ABU}Balance      ${RST}: ${YEL}${balStr}${RST}`);
  if (RUNTIME_END) console.log(`  ${CYN}◉${RST} ${ABU}Runtime      ${RST}: ${YEL}${runtimeLeftStr()}${RST}`);
  console.log(`  ${CYN}◉${RST} ${ABU}Errors       ${RST}: ${ERROR_COUNT >= MAX_ERRORS ? RED : ERROR_COUNT > 0 ? YEL : GRN}${ERROR_COUNT}/${MAX_ERRORS}${RST}`);

  console.log('');
  console.log(boxTop('[ MENU ]', CYN));
  console.log(boxMid(`  ${YEL}[1]${RST} ${WHT}Start Faucet (6h)${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[2]${RST} ${WHT}Set Provider${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[3]${RST} ${WHT}Set Cookie${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[4]${RST} ${WHT}Set User-Agent${RST}`, CYN));
  console.log(boxMid(`  ${YEL}[0]${RST} ${RED}Exit${RST}`, CYN));
  console.log(boxBot(CYN));
  console.log('');
};

const menuProvider = async () => {
  while (true) {
    clear(); bannerMain();
    console.log(`${WHT}  ⚙  Provider Setup${RST}\n`);
    const cfg = loadConfig() || defaultConfig();
    const active = cfg.provider || '';
    console.log(`  ${WHT}Provider aktif:${RST} ${active && PROVIDERS[active] ? GRN + PROVIDERS[active].name + RST : WHT + '-' + RST}\n`);
    const ids = Object.keys(PROVIDERS);
    ids.forEach((id, i) => {
      const p = PROVIDERS[id];
      const key = (cfg.apikeys && cfg.apikeys[id]) || '';
      const marker = id === active ? ` ${GRN}●${RST}` : '  ';
      console.log(`  ${GRN}[${i + 1}]${RST}${marker} ${WHT}${p.name.padEnd(14)}${RST} ${key ? GRN + maskKey(key) + RST : WHT + '-' + RST}`);
    });
    console.log(`  ${RED}[0]${RST}  ${WHT}Kembali${RST}\n`);
    const c = (await askQuestion(`  ${WHT}❯ Pilih: ${RST}`)).trim();
    if (c === '0') return;
    const idx = parseInt(c, 10);
    if (isNaN(idx) || idx < 1 || idx > ids.length) { await blinkErr('Pilihan invalid', 1200); continue; }
    const chosenId = ids[idx - 1];
    const chosen = PROVIDERS[chosenId];
    const cur = (cfg.apikeys && cfg.apikeys[chosenId]) || '';
    console.log('');
    console.log(`  ${WHT}Apikey sekarang:${RST} ${cur ? GRN + maskKey(cur) + RST : WHT + '-' + RST}`);
    const input = (await askQuestion(`  ${WHT}${chosen.name} Apikey : ${RST}`)).trim();
    if (input) { setApiKey(chosenId, input); log(`Apikey ${chosen.name} disimpan.`, 'ok'); }
    else log('Apikey tidak diubah.', 'i');
    setActiveProvider(chosenId);
    PROVIDER = chosenId;
    API_KEY = getApiKey(chosenId);
    log(`Provider aktif → ${chosen.name}`, 'ok');
    await sleep(1500);
  }
};

const menuCookie = async (cfg) => {
  clear(); bannerMain();
  console.log(`${WHT}  🍪 Cookie Setup${RST}\n`);
  const cur = cfg.cookie ? `${GRN}✓ tersimpan (${cfg.cookie.length} chars)${RST}` : `${RED}✗ belum diset${RST}`;
  console.log(`  ${WHT}Current Cookie:${RST} ${cur}\n`);
  console.log(`${ABU}  Paste cookie header — format: name=value; name2=value2; ...${RST}`);
  console.log(`${ABU}  Multi-line & "cookie:" prefix juga diterima.${RST}\n`);
  const lines = [];
  console.log(`  ${WHT}❯ Paste cookie (kosongkan lalu Enter untuk skip):${RST}`);
  while (true) {
    const ln = (await askQuestion(`    ${GRN}`)).trim();
    if (!ln) break;
    lines.push(ln);
  }
  const cookieStr = lines.join('; ');
  if (cookieStr) {
    cfg.cookie = cookieStr;
    saveConfig(cfg);
    applyCookieFromConfig(cfg);
    log(`Cookie saved (${cookieStr.length} chars)`, 'ok');
  } else {
    log('Cookie tidak diubah.', 'i');
  }
  await sleep(1400);
  return cfg;
};

const menuUA = async (cfg) => {
  clear(); bannerMain();
  console.log(`${WHT}  🛠  User-Agent Setup${RST}\n`);
  console.log(`  ${WHT}Current:${RST} ${GRN}${cfg.userAgent || '-'}${RST}\n`);
  const newUA = (await askQuestion(`  User Agent (Enter = default) : `)).trim();
  cfg.userAgent = newUA || DEF_UA;
  saveConfig(cfg);
  log('User-Agent updated!', 'ok');
  await sleep(1200);
  return cfg;
};

const main = async () => {
  let cfg = loadConfig() || defaultConfig();

  applyCookieFromConfig(cfg);

  PROVIDER = cfg.provider || '';
  API_KEY = getApiKey(PROVIDER);

  process.on('SIGINT', () => {
    if (!STOP_SIGNAL) {
      STOP_SIGNAL = true;
      if (spinPause) spinPause();
      process.stdout.write(`${CLR}\n${YEL}⚠ Dihentikan. Kembali ke menu...${RST}\n`);
    } else {
      process.stdout.write(`\n${RED}Program keluar.${RST}\n`);
      process.exit(0);
    }
  });

  clear(); bannerMain();
  log('Config loaded', 'ok');
  log(`Config   : ${path.basename(CONFIG_PATH)}`, 'dbg');
  log(`Provider : ${PROVIDER ? PROVIDERS[PROVIDER].name : '-'}`, 'dbg');
  log(`Cookie   : ${cfg.cookie ? '✓ set (' + cfg.cookie.length + ' chars)' : '✗ empty'}`, 'dbg');
  await sleep(800);

  while (true) {
    STOP_SIGNAL = false;

    let balStr = null;
    try { const bal = await refreshBalance(); if (bal != null) balStr = bal.toFixed(2); } catch {}

    tampilkanMenu(cfg, balStr);
    const c = (await askQuestion(`  ${YEL}▸${RST} ${WHT}Option : ${RST}`)).trim();

    if (c === '0') { console.log(`\n${RED}[!] Program stopped.${RST}`); process.exit(0); }

    if (c === '2') { await menuProvider(); cfg = loadConfig() || cfg; PROVIDER = cfg.provider || PROVIDER; API_KEY = getApiKey(PROVIDER); continue; }
    if (c === '3') { cfg = await menuCookie(cfg); continue; }
    if (c === '4') { cfg = await menuUA(cfg); continue; }

    if (!cfg.userAgent) { console.log(''); log('User-Agent belum di-set. Set dulu di menu [4].', 'wr'); await sleep(2000); continue; }
    if (!cfg.cookie) { console.log(''); log('Cookie belum di-set. Set dulu di menu [3].', 'wr'); await sleep(2000); continue; }
    if (!PROVIDER || !PROVIDERS[PROVIDER] || !getApiKey(PROVIDER)) { console.log(''); log('Provider/apikey belum di-set. Setup dulu di menu [2].', 'wr'); await sleep(2000); continue; }

    try {
      const ses = await verifySession();
      if (!ses.ok) {
        log('Cookie invalid / expired. Update cookie di menu [3].', 'er');
        await askQuestion(`${WHT}  Press Enter to return to menu...${RST}`);
        continue;
      }
    } catch (e) { log(`Pre-check err: ${e.message}`, 'er'); }

    if (c === '1') {
      resetErrors();
      startRuntime();
      log(`▶ Runtime 6 jam — deadline ${new Date(RUNTIME_END).toLocaleTimeString()}`, 'ok');
      log(`▶ Max error: ${MAX_ERRORS}x → auto stop`, 'i');
      await sleep(800);
      try { await runFullCycle(cfg); } catch (e) { if (!STOP_SIGNAL && !isTimeUp()) bumpError('MAIN-CYCLE', e.message); }
      if (isTimeUp()) {
        log('⏰ 6 jam tercapai. Run dihentikan.', 'wr');
      }
      if (ERROR_COUNT >= MAX_ERRORS) {
        log(`⛔ Stop karena ${MAX_ERRORS} error.`, 'er');
      }
      if (isTimeUp() || ERROR_COUNT >= MAX_ERRORS) {
        await askQuestion(`${WHT}  Press Enter to return to menu...${RST}`);
      }
      resetRuntime();
      resetErrors();
    } else {
      await blinkErr(`Pilihan salah: ${c}`, 1200);
    }
  }
};

main().catch(e => {
  console.log(`${RED}Fatal: ${e.message}${RST}`);
  process.exit(1);
});
