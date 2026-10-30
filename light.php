<?php
error_reporting(0);
date_default_timezone_set('Asia/Jakarta');
$configFile = "config.json";
if (!is_dir('session')) mkdir('session', 0777, true);

const NEON_CYAN="\033[1;36m", NEON_MAGENTA="\033[1;35m", NEON_YELLOW="\033[1;33m";
const NEON_GREEN="\033[1;32m", NEON_RED="\033[1;31m", NEON_BLUE="\033[1;34m";
const NEON_WHITE="\033[1;37m", NEON_GRAY="\033[1;90m", RESET="\033[0m", BOLD="\033[1m";

const api_url           = "https://lightningquest.net";
const SITEKEY_HCAPTCHA  = "bbc4e0f2-0052-4980-b1c2-aafe3e3c3bee";
const SITEKEY_TURNSTILE = "0x4AAAAAADxePtT-Imsq_y0B";
const TOKEN_TTL = 21600;
const WARYONO_IN  = "https://api.waryono.my.id/in.php";
const WARYONO_OUT = "https://api.waryono.my.id/res.php";

$CONFIG = ["apikey"=>"","email"=>"","password"=>"","proxy"=>""];
$currentUseProxy=false; $currentProxyParsed=null; $currentProxyType=CURLPROXY_SOCKS5_HOSTNAME;
$currentCookieFile=''; $currentEmail=''; $currentPassword=''; $access_token='';
$handling_interrupt=false;

class UserInterrupt extends Exception {}
class EnergyOut extends Exception {}

function clear() { (PHP_OS == 'Linux') ? system('clear') : pclose(popen('cls','w')); }
function ok($t){echo NEON_GREEN."[+] ".RESET.$t."\n";}
function good($t){echo NEON_GREEN."[✓] ".RESET.$t."\n";}
function info($t){echo NEON_CYAN."[~] ".RESET.$t."\n";}
function warn($t){echo NEON_YELLOW."[!] ".RESET.$t."\n";}
function fail($t){echo NEON_RED."[✗] ".RESET.$t."\n";}

function fmt_coin($v) {
    if (is_int($v) || (is_numeric($v) && floor($v) == $v)) return (string)(int)$v;
    $s = number_format((float)$v, 6, '.', '');
    return rtrim(rtrim($s, '0'), '.');
}
function pretty_num($v) {
    if (is_array($v)) {
        if (isset($v['current'])) return $v['current'];
        if (isset($v['value']))   return $v['value'];
        if (isset($v['level']))   return $v['level'];
        foreach ($v as $sub) if (is_numeric($sub)) return $sub;
        return json_encode($v);
    }
    return $v;
}
function maskEmail($e) {
    if (!filter_var($e, FILTER_VALIDATE_EMAIL)) return $e;
    list($u,$d) = explode('@', $e);
    if (strlen($u)<=4) return substr($u,0,1).'***@'.$d;
    return substr($u,0,2).'***'.substr($u,-2).'@'.$d;
}
function parseProxyString($s) {
    $p = explode(':', trim($s));
    if (count($p)===4) return ['host_port'=>$p[0].':'.$p[1],'auth'=>$p[2].':'.$p[3]];
    if (count($p)===2) return ['host_port'=>$p[0].':'.$p[1],'auth'=>null];
    return null;
}
function maskProxy($s) {
    if (empty($s)) return "(kosong)";
    $p = explode(':', $s);
    if (count($p)===4) {
        $mu = strlen($p[2])>3 ? substr($p[2],0,3).'***' : '***';
        $mp = strlen($p[3])>3 ? substr($p[3],0,3).'***' : '***';
        return $p[0].':'.$p[1].':'.$mu.':'.$mp;
    }
    return $s;
}
function bool_val($v) {
    if (is_bool($v)) return $v;
    if (is_string($v)) { $l=strtolower(trim($v)); return !($l===''||$l==='false'||$l==='0'||$l==='no'||$l==='off'||$l==='null'); }
    if (is_numeric($v)) return ((int)$v)!==0;
    return !empty($v);
}
function banner() {
    echo "\n".NEON_CYAN."==================================================".RESET."\n";
    echo NEON_MAGENTA.BOLD."          ⚡ LIGHTNINGQUEST AUTO BOT ⚡".RESET."\n";
    echo NEON_GREEN."          Credit: MoneyMaker_w | Waryono".RESET."\n";
    echo NEON_CYAN."==================================================".RESET."\n\n";
}
function section($t) {
    $p = "===== ".$t; $pad = 50 - strlen($p); if ($pad<1) $pad=1;
    echo "\n".NEON_CYAN.$p." ".str_repeat("=",$pad).RESET."\n\n";
}
function bar_timer($s, $indent="  ") {
    $total=(int)$s; if ($total<1) return;
    $w=20; $start=microtime(true);
    while (true) {
        $el=microtime(true)-$start; $rem=$total-$el; if ($rem<0) $rem=0;
        $pct=min(100,(int)round(($el/$total)*100));
        $f=(int)round(($pct/100)*$w); $em=$w-$f;
        $mm=(int)floor($rem/60); $ss=(int)$rem%60;
        echo "\r\033[K".$indent.NEON_GRAY."[".RESET.NEON_GREEN.str_repeat("▓",$f).RESET.NEON_GRAY.str_repeat("░",$em)."]".RESET
           ." ".NEON_YELLOW.str_pad($pct."%",4," ",STR_PAD_LEFT).RESET
           ."  ".NEON_GRAY."|".RESET."  ".NEON_CYAN.sprintf('%02d:%02d',$mm,$ss).RESET;
        flush();
        if ($rem<=0) break;
        usleep(100000);
    }
    echo "\r\033[K";
}

// ═══════════════ DASHBOARD ═══════════════
class Dashboard {
    public $s; private $W=62;
    public function __construct() {
        $this->s = [
            'phase'=>'idle',
            'account'=>['email'=>'-','name'=>'-','balance'=>0,'level'=>0],
            'faucet'=>['status'=>'online','label'=>'ONLINE'],
            'task'=>['current'=>'idle','progress'=>0,'elapsed'=>0,'total'=>0,'running'=>false],
            'session'=>['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0],
            'logs'=>[],
        ];
    }
    public function set($k,$v) {
        if (is_array($v) && isset($this->s[$k]) && is_array($this->s[$k])) {
            $this->s[$k] = array_merge($this->s[$k],$v);
        } else $this->s[$k] = $v;
    }
    public function log($msg, $tag='i') {
        $icons=['i'=>'»','ok'=>'✓','er'=>'✗','wr'=>'⚠','in'=>'●','dbg'=>'⚙','or'=>'◆'];
        $colors=['i'=>NEON_CYAN,'ok'=>NEON_GREEN,'er'=>NEON_RED,'wr'=>NEON_YELLOW,'in'=>NEON_BLUE,'dbg'=>NEON_GRAY,'or'=>NEON_YELLOW];
        $this->s['logs'][] = ['ts'=>date('H:i:s'),'icon'=>$icons[$tag]??'»','color'=>$colors[$tag]??NEON_WHITE,'msg'=>(string)$msg];
        if (count($this->s['logs'])>10) array_shift($this->s['logs']);
    }
    private function vlen($s){return mb_strlen(preg_replace('/\033\[[0-9;]*m/','',$s));}
    private function pad($s,$w){$v=$this->vlen($s);return $s.($v<$w?str_repeat(' ',$w-$v):'');}
    private function row($c){ $W=$this->W-2;
        return NEON_CYAN."║".RESET.$this->pad(" ".$c,$W).NEON_CYAN."║".RESET;
    }
    private function bar($pct,$w,$color){
        $f=max(0,min($w,(int)round($pct*$w))); $e=$w-$f;
        return $color.str_repeat("█",$f).NEON_GRAY.str_repeat("░",$e).RESET;
    }
    private function dur($sec){
        return sprintf('%02d:%02d:%02d',floor($sec/3600),floor(($sec%3600)/60),$sec%60);
    }
    public function render() {
        $W=$this->W; $INNER=$W-2;
        echo "\n".NEON_CYAN."╔".str_repeat("═",$INNER)."╗".RESET."\n";
        echo $this->row(BOLD.NEON_WHITE."LIGHTNINGQUEST BOT".RESET)."\n";
        echo $this->row(NEON_GRAY."──── Auto Farmer v2.0 ────".RESET)."\n";
        echo NEON_CYAN."╠".str_repeat("═",$INNER)."╣".RESET."\n";
        $fs=$this->s['faucet']; $fsc=NEON_GREEN; if ($fs['status']==='cooldown') $fsc=NEON_YELLOW; elseif ($fs['status']==='dead') $fsc=NEON_RED;
        echo $this->row(NEON_BLUE."▸ FAUCET".RESET)."\n";
        echo $this->row("  Status : ".$fsc.$fs['label'].RESET)."\n";
        echo $this->row("  Site   : ".NEON_CYAN."lightningquest.net".RESET)."\n";
        echo NEON_CYAN."╠".str_repeat("═",$INNER)."╣".RESET."\n";
        $a=$this->s['account'];
        echo $this->row(NEON_GREEN."▸ ACCOUNT".RESET)."\n";
        echo $this->row("  Email   : ".NEON_YELLOW.maskEmail($a['email']).RESET)."\n";
        echo $this->row("  Name    : ".NEON_CYAN.$a['name'].RESET)."\n";
        echo $this->row("  Balance : ".NEON_GREEN.pretty_num($a['balance']).RESET."c    Lv : ".NEON_BLUE.pretty_num($a['level']).RESET)."\n";
        echo NEON_CYAN."╠".str_repeat("═",$INNER)."╣".RESET."\n";
        $s=$this->s['session']; $run=time()-$s['start'];
        echo $this->row(NEON_MAGENTA."▸ SESSION".RESET)."\n";
        echo $this->row("  Earned  : ".NEON_GREEN."+".fmt_coin($s['coins'])."c".RESET."   XP : ".NEON_GREEN."+".$s['xp'].RESET)."\n";
        echo $this->row("  Faucet  : ".NEON_GREEN.$s['faucets'].RESET."   Daily: ".NEON_GREEN.$s['daily'].RESET."   Quest: ".NEON_GREEN.$s['quests'].RESET."   Mini: ".NEON_GREEN.$s['minigames'].RESET)."\n";
        echo $this->row("  Runtime : ".NEON_CYAN.$this->dur($run).RESET)."\n";
        echo NEON_CYAN."╠".str_repeat("═",$INNER)."╣".RESET."\n";
        $t=$this->s['task'];
        $pct = $t['total']>0 ? min(1,$t['elapsed']/$t['total']) : 0;
        $barW = max(20,$INNER-28);
        $barColor = $t['running'] ? NEON_MAGENTA : NEON_GRAY;
        $barStr = $this->bar($pct,$barW,$barColor);
        $pctTxt = str_pad(round($pct*100)."%",4," ",STR_PAD_LEFT);
        $elStr = sprintf('%02d:%02d',(int)floor($t['elapsed']/60),(int)$t['elapsed']%60);
        $ttStr = sprintf('%02d:%02d',(int)floor($t['total']/60),(int)$t['total']%60);
        $icon = $t['running'] ? NEON_GREEN."▶".RESET : NEON_GRAY."○".RESET;
        echo $this->row(NEON_YELLOW."▸ CURRENT TASK".RESET)."\n";
        echo $this->row("  ".$icon." ".substr($t['current'],0,$INNER-6))."\n";
        echo $this->row("  [".$barStr."] ".NEON_YELLOW.$pctTxt.RESET." ".NEON_GRAY.$elStr."/".$ttStr.RESET)."\n";
        echo NEON_CYAN."╠".str_repeat("═",$INNER)."╣".RESET."\n";
        echo $this->row(NEON_MAGENTA."▸ LOG".RESET)."\n";
        $logs = array_slice($this->s['logs'],-8);
        $maxMsg = $INNER - 18;
        if (empty($logs)) echo $this->row(NEON_GRAY."  ─ no activity ─".RESET)."\n";
        else foreach ($logs as $l) {
            $m = $l['msg']; if (strlen($m)>$maxMsg) $m = substr($m,0,$maxMsg-1)."…";
            echo $this->row("  ".NEON_GRAY."[".$l['ts']."]".RESET." ".$l['color'].$l['icon'].RESET." ".$m)."\n";
        }
        echo NEON_CYAN."╚".str_repeat("═",$INNER)."╝".RESET."\n";
        echo "\n   ".NEON_GREEN."● RUNNING".RESET." ".NEON_GRAY."•".RESET." ".NEON_CYAN.date('H:i:s').RESET."\n";
        echo "   ".NEON_GRAY."By MoneyMaker_w • v2.0".RESET."\n\n";
    }
    public function clear_render(){ clear(); $this->render(); }
    public function timer($sec,$label="waiting") {
        $total=(int)$sec; if ($total<1) return;
        $start=time();
        while ((time()-$start)<$total) {
            $el=time()-$start;
            $this->set('task',['current'=>$label,'progress'=>$el/$total,'elapsed'=>$el,'total'=>$total,'running'=>true]);
            $this->clear_render();
            sleep(1);
        }
        $this->set('task',['current'=>'idle','progress'=>0,'elapsed'=>0,'total'=>0,'running'=>false]);
        $this->clear_render();
    }
    public function setAccount($dta){ $this->set('account',$dta); }
}
$DB = new Dashboard();
function slog($msg,$tag='i'){ global $DB; $DB->log($msg,$tag); }

// ═══════════════ CONFIG ═══════════════
function loadConfig($f) {
    global $CONFIG;
    if (!file_exists($f)) {
        clear(); banner();
        echo NEON_YELLOW.BOLD."[ SETUP AWAL ]".RESET."\n";
        echo NEON_WHITE."API Key (Waryono) : ".NEON_YELLOW; $k=trim(fgets(STDIN));
        echo NEON_WHITE."Email             : ".NEON_YELLOW; $e=trim(fgets(STDIN));
        echo NEON_WHITE."Password          : ".NEON_YELLOW; $p=trim(fgets(STDIN));
        echo NEON_WHITE."Proxy (Enter skip): ".NEON_YELLOW; $x=trim(fgets(STDIN));
        $CONFIG = ["apikey"=>$k,"email"=>$e,"password"=>$p,"proxy"=>$x];
        saveConfig($f);
        echo "\n".NEON_GREEN."[✓] Config saved.".RESET."\n"; sleep(2);
    } else {
        $data = json_decode(file_get_contents($f),true) ?? [];
        $CONFIG = array_merge($CONFIG,$data);
        if (!empty($data['accounts'][0])) {
            $CONFIG['email']    = $data['accounts'][0]['email']    ?? '';
            $CONFIG['password'] = $data['accounts'][0]['password'] ?? '';
            $CONFIG['proxy']    = $data['accounts'][0]['proxy']    ?? '';
            saveConfig($f);
        }
    }
    return $CONFIG;
}
function saveConfig($f) { global $CONFIG; file_put_contents($f,json_encode($CONFIG,JSON_PRETTY_PRINT)); }
function setupSession() {
    global $CONFIG,$currentCookieFile,$currentUseProxy,$currentProxyParsed,$currentProxyType,$currentEmail,$currentPassword;
    $currentCookieFile = "session/".md5($CONFIG['email']).".txt";
    $currentUseProxy=false; $currentProxyParsed=null; $currentProxyType=CURLPROXY_SOCKS5_HOSTNAME;
    if (!empty($CONFIG['proxy'])) {
        $currentProxyParsed = parseProxyString($CONFIG['proxy']);
        if ($currentProxyParsed) $currentUseProxy=true;
    }
    $currentEmail = $CONFIG['email']; $currentPassword = $CONFIG['password'];
}
function token_path($e){return "session/".md5($e)."_token.json";}
function get_cached_token($e){
    $p=token_path($e); if (!file_exists($p)) return null;
    $d=json_decode(file_get_contents($p),true); if (!$d||empty($d['token'])) return null;
    if (time()-($d['ts']??0)>TOKEN_TTL) return null;
    return $d['token'];
}
function save_token($e,$t){file_put_contents(token_path($e),json_encode(['token'=>$t,'ts'=>time()]));}
function del_token($e){$p=token_path($e);if(file_exists($p))@unlink($p);}

// ═══════════════ HTTP ═══════════════
function wkwk($url,$payload=null,$headers=[],$method="POST",$no_proxy=false){
    global $currentUseProxy,$currentProxyParsed,$currentProxyType,$currentCookieFile;
    $retry=0;
    while ($retry<3) {
        $retry++;
        $ch=curl_init();
        $o=[CURLOPT_URL=>$url,CURLOPT_RETURNTRANSFER=>true,CURLOPT_FOLLOWLOCATION=>true,
            CURLOPT_SSL_VERIFYHOST=>0,CURLOPT_SSL_VERIFYPEER=>false,
            CURLOPT_HTTPHEADER=>$headers,CURLOPT_CONNECTTIMEOUT=>20,CURLOPT_TIMEOUT=>45,
            CURLOPT_ENCODING=>'',CURLOPT_TCP_KEEPALIVE=>1];
        if (!empty($currentCookieFile)){$o[CURLOPT_COOKIEFILE]=$currentCookieFile;$o[CURLOPT_COOKIEJAR]=$currentCookieFile;}
        if (!$no_proxy&&$currentUseProxy&&$currentProxyParsed){
            $o[CURLOPT_PROXY]=$currentProxyParsed['host_port']; $o[CURLOPT_PROXYTYPE]=$currentProxyType;
            if ($currentProxyParsed['auth']) $o[CURLOPT_PROXYUSERPWD]=$currentProxyParsed['auth'];
        }
        if ($method==="POST"){$o[CURLOPT_POST]=true;$o[CURLOPT_POSTFIELDS]=is_array($payload)?json_encode($payload):$payload;}
        curl_setopt_array($ch,$o);
        $resp=curl_exec($ch); $code=curl_getinfo($ch,CURLINFO_RESPONSE_CODE); curl_close($ch);
        if ($resp!==false&&$resp!=='') return ["body"=>$resp,"code"=>$code];
        if ($retry<3) usleep(800000);
    }
    return ["body"=>'{"error":"CONNECTION_FAILED"}',"code"=>0];
}

// ═══════════════ CAPTCHA (FIXED) ═══════════════
function solve_captcha($method, $sitekey, $action = "") {
    global $CONFIG;
    $apikey = $CONFIG['apikey'];

    slog("Solving $method (action=".($action ?: 'none').")...", 'in');

    $body = [
        "apikey"  => $apikey,
        "methods" => $method,
        "domain"  => "https://lightningquest.net",
        "sitekey" => $sitekey,
        "json"    => 1,
    ];
    if ($action !== "") {
        $body["action"] = $action;
        $body["cdata"] = "";
    }

    $req = wkwk(WARYONO_IN, $body, ["Content-Type: application/json"], "POST", true);
    $j = json_decode($req["body"], true);
    $tid = $j["request"] ?? null;

    if (!$tid) {
        $raw = substr(trim($req["body"] ?? ''), 0, 100);
        slog("Captcha submit failed: $raw", 'er');
        return null;
    }

    slog("Captcha task: $tid", 'in');
    $st = microtime(true);
    $lp = 0;
    $tok = null;
    $maxWait = 60; // 60s max

    while (true) {
        $el = microtime(true) - $st;
        if ($el > $maxWait) { slog("Captcha poll timeout (".(int)$el."s)", 'wr'); break; }

        if (($el - $lp) >= 3) {
            $lp = $el;
            $pu = WARYONO_OUT . "?apikey=" . urlencode($apikey) . "&action=get&id=" . urlencode($tid) . "&json=1";
            $pr = wkwk($pu, null, [], "GET", true);
            $raw = trim($pr["body"] ?? '');

            if (strpos($raw, "CAPCHA_NOT_READY") !== false) continue;

            $pj = json_decode($raw, true);
            if (is_array($pj) && !empty($pj["request"])) {
                $tok = $pj["request"];
                $el = round(microtime(true) - $st, 1);
                slog("Captcha solved in {$el}s", 'ok');
                break;
            }

            if ($raw && strpos($raw, "CAPCHA_NOT_READY") === false) {
                slog("Captcha poll: " . substr($raw, 0, 80), 'er');
                return null;
            }
        }
        usleep(500000);
    }

    if ($tok) return $tok;
    slog("Captcha failed ({$method})", 'er');
    return null;
}

function solve_captcha_retry($method, $sitekey, $max = 2, $action = "") {
    for ($a = 1; $a <= $max; $a++) {
        if ($a > 1) {
            slog("Captcha retry $a/$max", 'wr');
            sleep(2);
        }
        $t = solve_captcha($method, $sitekey, $action);
        if ($t) return $t;
    }
    return null;
}

// ═══════════════ AUTH ═══════════════
function auth_headers(){
    global $access_token;
    $h=['sec-ch-ua: "Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        'sec-ch-ua-mobile: ?1','sec-ch-ua-platform: "Android"','upgrade-insecure-requests: 1',
        'user-agent: Mozilla/5.0 (Linux; Android 11; vivo 1904 Build/RP1A.200720.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36',
        'accept: */*','x-requested-with: qzbr.zpr.pt',
        'sec-fetch-site: same-origin','sec-fetch-mode: cors','sec-fetch-dest: empty',
        'referer: https://lightningquest.net/ptc',
        'accept-language: id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority: u=1, i','content-type: application/json'];
    if ($access_token) $h[]='authorization: Bearer '.$access_token;
    return $h;
}
function do_login($email,$password){
    $body=["email"=>$email,"password"=>$password,"trafficExchangeBonus"=>false];
    $res=wkwk(api_url."/api/auth/login",$body,auth_headers());
    $json=json_decode($res["body"],true);
    if (!empty($json['access_token'])) return $json;
    fail("Login : ".($json['msg']??$json['message']??substr($res['body'],0,80)));return null;
}
function ensure_login($email,$password,$force=false){
    global $access_token;
    if (!$force) {
        $cached=get_cached_token($email);
        if ($cached) {
            $access_token=$cached;
            $res=wkwk(api_url."/api/me",null,auth_headers(),"GET");
            if ($res["code"]==200){$me=json_decode($res["body"],true);if(is_array($me)&&!isset($me['error'])&&!empty($me)){return ['access_token'=>$cached,'user'=>$me,'me'=>$me,'_cached'=>true];}}
            del_token($email);
        }
    }
    $json=do_login($email,$password);
    if ($json){save_token($email,$json['access_token']);$access_token=$json['access_token'];$meRes=wkwk(api_url."/api/me",null,auth_headers(),"GET");$json['me']=json_decode($meRes['body'],true)?:[];return $json;}
    return null;
}
function api_get($path){
    global $access_token,$currentEmail,$currentPassword;
    $res=wkwk(api_url.$path,null,auth_headers(),"GET");
    if ($res["code"]==401){del_token($currentEmail);$l=ensure_login($currentEmail,$currentPassword,true);if($l){$access_token=$l['access_token'];$res=wkwk(api_url.$path,null,auth_headers(),"GET");}}
    return json_decode($res["body"],true);
}
function api_post($path,$payload){
    global $access_token,$currentEmail,$currentPassword;
    $res=wkwk(api_url.$path,$payload,auth_headers(),"POST");
    if ($res["code"]==401){del_token($currentEmail);$l=ensure_login($currentEmail,$currentPassword,true);if($l){$access_token=$l['access_token'];$res=wkwk(api_url.$path,$payload,auth_headers(),"POST");}}
    return json_decode($res["body"],true);
}

// ═══════════════ QUEST ═══════════════
function fetch_all_quests(){
    $prog=api_get("/api/quests/progress"); $ach=api_get("/api/achievements");
    $daily=[];$weekly=[];
    if (is_array($prog)&&isset($prog['progress'])&&is_array($prog['progress'])){
        foreach ($prog['progress'] as $q){
            if (!is_array($q)) continue;
            $id=strtolower((string)($q['id']??''));
            if (strpos($id,'daily_')===0) $daily[]=$q;
            if (strpos($id,'weekly_')===0) $weekly[]=$q;
        }
    }
    $achv=[]; if (is_array($ach)&&isset($ach['achievements'])&&is_array($ach['achievements'])) $achv=$ach['achievements'];
    return ['daily'=>$daily,'weekly'=>$weekly,'achievements'=>$achv];
}
function claim_quests_once(){
    $stats=['daily'=>0,'daily_coins'=>0,'daily_xp'=>0,'weekly'=>0,'weekly_coins'=>0,'weekly_xp'=>0,'ach'=>0,'ach_coins'=>0,'ach_xp'=>0];
    $q=fetch_all_quests();
    foreach ($q['daily'] as $it){
        if (empty($it['complete'])||!empty($it['claimed'])) continue;
        $r=api_post("/api/quests/".$it['id']."/claim",[]);
        if (is_array($r)&&($r['ok']??false)===true){
            $c=$r['reward']['coins']??0;$x=$r['reward']['xp']??0;
            $stats['daily']++;$stats['daily_coins']+=$c;$stats['daily_xp']+=$x;
            slog("Daily ".$it['id']." +".fmt_coin($c)."c +".$x."xp",'ok');
        }
        usleep(200000);
    }
    foreach ($q['weekly'] as $it){
        if (empty($it['complete'])||!empty($it['claimed'])) continue;
        $r=api_post("/api/quests/".$it['id']."/claim",[]);
        if (is_array($r)&&($r['ok']??false)===true){
            $c=$r['reward']['coins']??0;$x=$r['reward']['xp']??0;
            $stats['weekly']++;$stats['weekly_coins']+=$c;$stats['weekly_xp']+=$x;
            slog("Weekly ".$it['id']." +".fmt_coin($c)."c +".$x."xp",'ok');
        }
        usleep(200000);
    }
    foreach ($q['achievements'] as $it){
        if (empty($it['complete'])||!empty($it['claimed'])) continue;
        $r=api_post("/api/achievements/".$it['id']."/claim",[]);
        $ok=is_array($r)&&($r['ok']??false)===true;
        if (!$ok){$r=api_post("/api/quests/".$it['id']."/claim",[]);$ok=is_array($r)&&($r['ok']??false)===true;}
        if ($ok){
            $c=$r['reward']['coins']??0;$x=$r['reward']['xp']??0;
            $stats['ach']++;$stats['ach_coins']+=$c;$stats['ach_xp']+=$x;
            slog("Achievement ".$it['id']." +".fmt_coin($c)."c +".$x."xp",'ok');
        }
        usleep(200000);
    }
    return $stats;
}

// ═══════════════ FAUCET + DAILY ═══════════════
function faucet_claim_single(){
    $status=api_get("/api/claim-status"); $f=$status['faucet']??[];
    if (empty($f['ready'])){
        $n=strtotime($f['nextAt']??''); $cd=intval($f['cooldownSeconds']??300);
        $w=$n?($n-time()):$cd; if ($w<5) $w=5;
        return ['status'=>'cooldown','wait'=>$w];
    }
    slog("Faucet challenge...",'in');
    $ch=api_get("/api/faucet/challenge"); if (empty($ch['claimToken'])) return ['status'=>'error','wait'=>10];
    $ct=$ch['claimToken']; $mw=intval($ch['minWaitSeconds']??5);
    if ($mw>0){slog("Bypass wait ".$mw."s...",'in');sleep($mw);}
    $cr=bool_val($f['captchaRequired']??false); $prov=$f['captchaProvider']??'hcaptcha';
    if (!empty($ch['captchaProvider'])) $prov=$ch['captchaProvider'];
    $ctok="";
    if ($cr){
        $sk=($prov==="hcaptcha")?SITEKEY_HCAPTCHA:SITEKEY_TURNSTILE;
        // action dikirim ke BOTH hcaptcha & turnstile
        $ctok=solve_captcha_retry($prov,$sk,2,"faucet-cadence-v1");
        if (!$ctok) {
            slog("Faucet captcha failed — skip, retry next cycle", 'er');
            return ['status'=>'error','wait'=>60];
        }
    }
    sleep(rand(1,3));
    $claim=api_post("/api/claim/faucet",["captchaToken"=>$ctok,"claimToken"=>$ct]);
    if (empty($claim['ok'])){
        $m=$claim['msg']??$claim['message']??$claim['error']??substr(json_encode($claim),0,60);
        fail("Faucet : ".$m); return ['status'=>'error','wait'=>10];
    }
    $r=$claim['reward']??[]; $sn=$r['snapshot']??$claim['snapshot']??[];
    $n=strtotime($claim['nextAt']??''); $cd=$n?($n-time()):300; if ($cd<5) $cd=300;
    return ['status'=>'claimed','wait'=>$cd,'coins'=>$r['coins']??0,'xp'=>$r['xp']??0,
            'balance'=>pretty_num($sn['balance']??'?'),'level'=>pretty_num($sn['level']??'?')];
}
function daily_claim_single(){
    $status=api_get("/api/claim-status"); $d=$status['daily']??[];
    if (empty($d['ready'])){
        $n=strtotime($d['nextAt']??''); $w=$n?($n-time()):3600; if ($w<5) $w=3600;
        return ['status'=>'cooldown','wait'=>$w];
    }
    slog("Daily bonus...",'in');
    $cap=solve_captcha_retry("turnstile",SITEKEY_TURNSTILE,2);
    if (!$cap) return ['status'=>'error','wait'=>10];
    $c=api_post("/api/claim/daily",["captchaToken"=>$cap]);
    if (!empty($c['ok'])){
        $r=$c['reward']??[];
        return ['status'=>'claimed','coins'=>$r['coins']??0,'xp'=>$r['xp']??0];
    }
    return ['status'=>'error','wait'=>10];
}

// ═══════════════ MINIGAMES ═══════════════
function run_minigames_once(){
    global $DB;
    $mg=api_get("/api/minigames"); $games=$mg['games']??[];
    if (!is_array($games)||empty($games)) return false;
    $played=0;
    foreach ($games as $g){
        $gid=$g['id']??''; if (!$gid) continue;
        $avail=(int)($g['today']['availablePlays']??0);
        if ($avail<=0) continue;
        for ($i=0;$i<$avail;$i++){
            $st=api_post("/api/minigames/start",["gameId"=>$gid]);
            if (!is_array($st)||empty($st['runId'])) break;
            $durMs=(int)($st['durationMs']??$g['durationMs']??30000);
            $w=(int)ceil($durMs/1000)+2; if ($w<5) $w=5;
            slog("Playing ".($g['name']??$gid)." ".($i+1)."/".$avail,'in');
            $DB->timer($w,"Playing ".($g['name']??$gid));
            $sn=(float)($g['maxScraps']??0)*(float)($g['scoreDivisor']??1);
            $xn=(float)($g['maxXp']??0)/max(0.01,(float)($g['xpPerScore']??1));
            $score=(int)ceil(max($sn,$xn)*1.05); if ($score<50) $score=50;
            $c=api_post("/api/minigames/complete",[
                "gameId"=>$gid,"runId"=>$st['runId'],"runToken"=>$st['runToken']??'',
                "score"=>$score,"hits"=>max(1,(int)round($score/200)),"misses"=>2,"hazards"=>1,
                "maxCombo"=>10,"durationMs"=>$durMs+rand(100,800),"clientVersion"=>34,
            ]);
            if (is_array($c)&&!empty($c['ok'])){
                $r=$c['reward']??[]; $sc=$r['scraps']??0; $xp=$r['xp']??0;
                $DB->set('session',['minigames'=>$DB->s['session']['minigames']+1]);
                slog("Minigame +".$sc."s +".$xp."xp",'ok');
            }
            $played++; sleep(2);
        }
    }
    return $played>0;
}

// ═══════════════ BOSS ═══════════════
function _boss_hp_bar($hp,$max,$w=8){
    if ($max<=0||$hp===null) return NEON_GRAY.str_repeat("░",$w).RESET;
    $p=max(0,min(100,($hp/$max)*100)); $f=(int)round(($p/100)*$w);
    return NEON_RED.str_repeat("█",$f).NEON_GRAY.str_repeat("░",$w-$f).RESET;
}
function _fmt_big($n){
    $n=(float)$n;
    if ($n>=1000000000) return number_format($n/1000000000,2)."B";
    if ($n>=1000000) return number_format($n/1000000,2)."M";
    if ($n>=1000) return number_format($n/1000,1)."K";
    return number_format($n);
}
function menu_boss($configFile){
    global $CONFIG,$access_token;
    clear(); banner();
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    while (true){
        clear(); banner();
        echo NEON_MAGENTA.BOLD."[ BOSS ATTACK MODE ]".RESET."\n";
        echo NEON_CYAN."==================================================".RESET."\n";
        echo NEON_GREEN."[1] ".RESET."Attack Boss (1 Energy)\n";
        echo NEON_GREEN."[2] ".RESET."Use 5 Energy (x5 dmg)\n";
        echo NEON_RED."[0] ".RESET."Back\n";
        echo "\n".NEON_YELLOW."Pilih : ".RESET;
        $m=trim(fgets(STDIN));
        if ($m==='0'||$m==='') return;
        if ($m==='1'||$m==='2') break;
    }
    $ep=($m==='2')?5:1;
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login failed");sleep(2);return;}
    $access_token=$login['access_token'];
    $hits=0;$dmg=0;$crit=0;$hp=null;$mx=null;$pool=0;$est=0;$share=0;$en=null;
    section("[ ATTACKING BOSS ]");
    while (true){
        $res=api_post("/api/game/attack",["count"=>$ep,"useMaxEnergy"=>false]);
        if (!is_array($res)||empty($res['ok'])){
            $msg=strtolower((string)($res['msg']??$res['message']??$res['error']??'error'));
            if (strpos($msg,'energy')!==false||strpos($msg,'insufficient')!==false){warn("Energy not enough");break;}
            fail("Error: ".substr($msg,0,60));sleep(2);continue;
        }
        $hits++;$d=intval($res['damage']??0);$cr=!empty($res['crit']);$cc=intval($res['critCount']??0);
        $dmg+=$d;$crit+=$cc;
        $g=$res['game']??[];$b=$g['boss']??[];$p=$g['player']??[];
        if (isset($b['health'])) $hp=intval($b['health']);
        if (isset($b['maxHealth'])) $mx=intval($b['maxHealth']);
        if (isset($b['rewardPool'])) $pool=floatval($b['rewardPool']);
        if (isset($p['energy'])) $en=intval($p['energy']);
        if (isset($p['estimatedReward'])) $est=floatval($p['estimatedReward']);
        if (isset($p['rewardSharePct'])) $share=floatval($p['rewardSharePct'])*100;
        $cm=$cr?NEON_YELLOW." [CRIT]".RESET:"       ";
        echo NEON_GRAY."#".str_pad($hits,4," ",STR_PAD_LEFT).RESET
            ." ".NEON_WHITE."D:".NEON_RED.str_pad(number_format($d),6).RESET.$cm
            ." ".NEON_WHITE."E:".NEON_GREEN.str_pad($en??'?',4).RESET
            ." "._boss_hp_bar($hp,$mx,8)." ".NEON_YELLOW.str_pad(_fmt_big($hp),7).RESET
            ." ".NEON_YELLOW.str_pad(_fmt_big($pool)."c",8).RESET
            ." ".NEON_GREEN.str_pad(number_format($est,2)."c",9).RESET
            ." ".NEON_CYAN.number_format($share,3)."%".RESET."\n"; flush();
        if (!empty($res['defeated'])||(isset($b['alive'])&&$b['alive']===false)){echo "\n".NEON_GREEN.BOLD."[✓] BOSS DEFEATED!".RESET."\n";break;}
        if ($en!==null&&$en<$ep){warn("Energy habis (E=".$en.")");break;}
        usleep(700000);
    }
    echo "\n".NEON_CYAN."[ Summary ]".RESET." hits: ".NEON_GREEN.$hits.RESET." | dmg: ".NEON_RED.number_format($dmg).RESET." | crit: ".NEON_YELLOW.$crit.RESET." | share: ".NEON_CYAN.number_format($share,3)."%".RESET."\n";
    echo "\n".NEON_YELLOW."Press Enter to return...".RESET; fgets(STDIN);
}

// ═══════════════ BATTLE PASS ═══════════════
function menu_battlepass($configFile){
    global $CONFIG,$access_token;
    clear(); banner();
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login failed");sleep(2);return;}
    $access_token=$login['access_token'];
    $bp=api_get("/api/battlepass");
    if (!is_array($bp)||isset($bp['error'])){fail("Fetch BP failed");sleep(2);return;}
    $lv=pretty_num($bp['level']??($bp['progress']['level']??'?'));
    $xp=pretty_num($bp['xp']??($bp['progress']['xp']??'?'));
    echo NEON_WHITE."Level : ".NEON_YELLOW.$lv.RESET." | XP : ".NEON_GREEN.$xp.RESET."\n";
    $tasks=[];$rewards=[];
    foreach (['tasks','missions','dailyTasks','weeklyTasks','daily','weekly','premiumTasks'] as $k)
        if (isset($bp[$k])&&is_array($bp[$k])) foreach ($bp[$k] as $t) if (is_array($t)) $tasks[]=$t;
    foreach (['rewards','tiers','levels','track','milestones'] as $k)
        if (isset($bp[$k])&&is_array($bp[$k])) foreach ($bp[$k] as $r) if (is_array($r)) $rewards[]=$r;
    $tc=0;$gx=0;$gc=0;$ge=0;
    section("[ TASKS ]");
    foreach ($tasks as $t){
        $id=$t['id']??($t['taskId']??null);if (!$id) continue;
        $co=!empty($t['completed'])||!empty($t['complete'])||!empty($t['ready']);
        $cl=!empty($t['claimed']); if (!$co||$cl) continue;
        $r=api_post("/api/battlepass/tasks/claim",['taskId'=>$id]);
        if (is_array($r)&&($r['ok']??true)!==false){
            $tc++;$rw=$r['reward']??[];$x=$rw['xp']??0;
            ok($id." +".$x." BP XP"); $gx+=$x;$gc+=$rw['coins']??0;$ge+=$rw['energy']??0;
        }
        usleep(200000);
    }
    $rc=0; section("[ REWARDS ]");
    foreach ($rewards as $r){
        $lvl=$r['level']??($r['tier']??null);if (!$lvl) continue;
        foreach (['free','premium'] as $tr){
            $td=$r[$tr]??null;if (!is_array($td)) continue;
            $cl=!empty($td['claimed']);$rd=!empty($td['ready'])||!empty($td['unlocked']);
            if (!$rd&&empty($td['locked'])) $rd=true;
            if ($cl||!$rd) continue;
            $res=api_post("/api/battlepass/rewards/claim",['level'=>(int)$lvl,'track'=>$tr]);
            if (is_array($res)&&($res['ok']??true)!==false){
                $rc++;$rw=$res['reward']??[];$gx+=$rw['xp']??0;$gc+=$rw['coins']??0;$ge+=$rw['energy']??0;
            }
            usleep(200000);
        }
    }
    echo "\n".NEON_CYAN."[ Summary ]".RESET." tasks: ".NEON_GREEN.$tc.RESET." | rewards: ".NEON_GREEN.$rc.RESET." | +".$gx."xp | +".fmt_coin($gc)."c | +".$ge."energy\n";
    echo "\n".NEON_YELLOW."Press Enter to return...".RESET; fgets(STDIN);
}

// ═══════════════ WITHDRAW ═══════════════
function menu_withdraw($configFile){
    global $CONFIG,$access_token;
    clear(); banner();
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $methods=[
        '1'=>['key'=>'faucetpay_btc','label'=>'FaucetPay BTC','hint'=>'email'],
        '2'=>['key'=>'faucetpay_ltc','label'=>'FaucetPay LTC','hint'=>'email'],
        '3'=>['key'=>'faucetpay_doge','label'=>'FaucetPay DOGE','hint'=>'email'],
        '4'=>['key'=>'faucetpay_usdc','label'=>'FaucetPay USDC','hint'=>'email'],
        '5'=>['key'=>'faucetpay_sol','label'=>'FaucetPay SOL','hint'=>'email'],
        '6'=>['key'=>'faucetpay_eth','label'=>'FaucetPay ETH','hint'=>'email'],
        '7'=>['key'=>'lightning','label'=>'BTC Lightning','hint'=>'ln address'],
        '8'=>['key'=>'bitcoin','label'=>'Bitcoin (-2%)','hint'=>'BTC address'],
        '9'=>['key'=>'litecoin','label'=>'Litecoin (-100)','hint'=>'LTC address'],
        '10'=>['key'=>'solana','label'=>'Solana (-100)','hint'=>'SOL address'],
        '11'=>['key'=>'paypal','label'=>'PayPal (-5%)','hint'=>'email'],
        '12'=>['key'=>'cxl_wallet','label'=>'CXL Wallet','hint'=>'email'],
    ];
    while (true){
        clear(); banner();
        echo NEON_MAGENTA.BOLD."[ AUTO WITHDRAW ]".RESET."\n";
        echo NEON_CYAN."==================================================".RESET."\n";
        foreach ($methods as $k=>$m) echo NEON_GREEN."[".str_pad($k,2," ",STR_PAD_LEFT)."] ".RESET.NEON_YELLOW.$m['label'].RESET."\n";
        echo NEON_RED."[ 0] ".RESET."Back\n\n".NEON_WHITE."Pilih : ".NEON_YELLOW;
        $ch=trim(fgets(STDIN));
        if ($ch==='0'||$ch==='') return;
        if (isset($methods[$ch])){$mk=$methods[$ch]['key'];$hint=$methods[$ch]['hint'];break;}
    }
    echo "\n".NEON_WHITE."Target (".$hint."): ".NEON_YELLOW; $t=trim(fgets(STDIN));
    if ($t===''){fail("Cancelled");sleep(2);return;}
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login failed");sleep(2);return;}
    $access_token=$login['access_token'];
    $w=api_get("/api/wallet");
    if (!is_array($w)||empty($w['ok'])){fail("Fetch wallet failed");sleep(2);return;}
    $wl=$w['wallet']??[]; $bal=floatval($wl['balance']??0);
    $min=intval($wl['minimumWithdrawalCoins']??1000);
    if ($mk==='bitcoin') $min=intval($wl['bitcoinMinimumWithdrawalCoins']??30000);
    elseif ($mk==='paypal') $min=intval($wl['paypalMinimumWithdrawalCoins']??50000);
    elseif (in_array($mk,['litecoin','solana'])) $min=intval($wl['directWalletMinimumWithdrawalCoins']??10000);
    $amt=(int)floor($bal); if (in_array($mk,['litecoin','solana'])) $amt-=100;
    echo "\n".NEON_WHITE."Balance: ".NEON_GREEN.number_format($bal,4).RESET." | Min: ".NEON_YELLOW.number_format($min).RESET." | Amount: ".NEON_GREEN.number_format($amt).RESET."\n";
    if ($amt<$min){warn("Below minimum");echo "\n".NEON_YELLOW."Press Enter...".RESET;fgets(STDIN);return;}
    info("Sending...");
    $r=api_post("/api/withdrawals",["method"=>$mk,"target"=>$t,"amount"=>$amt]);
    if (is_array($r)&&!empty($r['ok'])){
        $wid=$r['withdrawalId']??'?';$sn=$r['snapshot']??[];
        good("WD Success! ID: ".substr($wid,0,8)."...");
        echo NEON_GREEN."Amount: ".number_format($amt)."c".RESET." | New Bal: ".NEON_GREEN.pretty_num($sn['balance']??'?').RESET."\n";
    } else {
        $m=$r['msg']??$r['message']??$r['error']??'Unknown'; fail("Failed: ".substr($m,0,60));
    }
    echo "\n".NEON_YELLOW."Press Enter...".RESET; fgets(STDIN);
}
function menu_wd_history($configFile){
    global $CONFIG,$access_token;
    clear(); banner();
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login failed");sleep(2);return;}
    $access_token=$login['access_token'];
    $w=api_get("/api/wallet");
    if (!is_array($w)||empty($w['ok'])){fail("Fetch wallet failed");sleep(2);return;}
    $wl=$w['wallet']??[];
    echo NEON_MAGENTA.BOLD."[ WITHDRAW HISTORY ]".RESET."\n";
    echo NEON_CYAN."==================================================".RESET."\n";
    echo NEON_WHITE."Balance: ".NEON_GREEN.pretty_num($wl['balance']??0)."c".RESET."\n";
    $wds=$w['withdrawals']??[];
    if (empty($wds)){warn("No withdrawals yet");echo "\n".NEON_YELLOW."Press Enter...".RESET;fgets(STDIN);return;}
    echo NEON_CYAN."--------------------------------------------------".RESET."\n";
    echo NEON_CYAN."#  | Date       | Method         | Amount   | Status".RESET."\n";
    echo NEON_CYAN."--------------------------------------------------".RESET."\n";
    $i=1;
    foreach (array_slice($wds,0,10) as $wd){
        $d=isset($wd['requestedAt'])?substr($wd['requestedAt'],0,10):'?';
        $m=substr($wd['method']??'?',0,14);
        $a=number_format(intval($wd['amount']??0));
        $st=$wd['status']??'?';
        $sc=NEON_YELLOW; if ($st==='paid') $sc=NEON_GREEN; elseif (in_array($st,['rejected','failed'])) $sc=NEON_RED;
        echo NEON_GRAY.str_pad($i,2," ",STR_PAD_LEFT).RESET." | ".NEON_CYAN.str_pad($d,10," ").RESET
            ." | ".NEON_MAGENTA.str_pad($m,14," ").RESET
            ." | ".NEON_YELLOW.str_pad($a,8," ",STR_PAD_LEFT).RESET
            ." | ".$sc.$st.RESET."\n"; $i++;
    }
    echo NEON_CYAN."--------------------------------------------------".RESET."\n";
    $paid=0;$cp=0;$pend=0;
    foreach ($wds as $wd){$st=$wd['status']??'';if ($st==='paid'){$paid+=floatval($wd['amount']??0);$cp++;}elseif ($st==='pending'){$pend+=floatval($wd['amount']??0);}}
    echo NEON_WHITE."Total PAID   : ".NEON_GREEN.number_format($paid)."c".RESET." (".$cp." tx)\n";
    if ($pend>0) echo NEON_WHITE."Total PENDING: ".NEON_YELLOW.number_format($pend)."c".RESET."\n";
    echo "\n".NEON_YELLOW."Press Enter...".RESET; fgets(STDIN);
}

// ═══════════════ SETTINGS ═══════════════
function menu_set_account($configFile){
    global $CONFIG;
    clear(); banner();
    echo NEON_MAGENTA.BOLD."[ SET AKUN ]".RESET."\n";
    echo NEON_CYAN."==================================================".RESET."\n";
    echo NEON_WHITE."Email : ".NEON_YELLOW.($CONFIG['email']?:'(kosong)').RESET."\n";
    echo NEON_WHITE."Proxy : ".NEON_YELLOW.maskProxy($CONFIG['proxy']??'').RESET."\n\n";
    echo NEON_WHITE."Email baru (Enter = tetap)    : ".NEON_YELLOW; $e=trim(fgets(STDIN));
    if ($e!==''){
        echo NEON_WHITE."Password baru (Enter = tetap) : ".NEON_YELLOW; $p=trim(fgets(STDIN));
        echo NEON_WHITE."Proxy baru (Enter = hapus)    : ".NEON_YELLOW; $x=trim(fgets(STDIN));
        $CONFIG['email']=$e;$CONFIG['password']=$p;$CONFIG['proxy']=$x;
        del_token($e); saveConfig($configFile);
        echo "\n".NEON_GREEN."[✓] Akun updated".RESET."\n";
    } else {
        echo NEON_WHITE."Proxy baru (Enter = hapus)    : ".NEON_YELLOW; $x=trim(fgets(STDIN));
        $CONFIG['proxy']=$x; saveConfig($configFile);
        echo "\n".NEON_GREEN."[✓] Proxy updated".RESET."\n";
    }
    sleep(2);
}
function menu_set_apikey($configFile){
    global $CONFIG;
    clear(); banner();
    echo NEON_MAGENTA.BOLD."[ SET API KEY WARYONO ]".RESET."\n";
    echo NEON_CYAN."==================================================".RESET."\n";
    $cur=$CONFIG['apikey']??'';
    echo NEON_WHITE."Key : ".NEON_YELLOW.(strlen($cur)>8?substr($cur,0,8).'...':($cur?:'(kosong)')).RESET."\n\n";
    echo NEON_WHITE."Key baru (Enter = batal) : ".NEON_YELLOW;
    $k=trim(fgets(STDIN)); if ($k===""){fail("Cancelled");sleep(2);return;}
    $CONFIG['apikey']=$k; saveConfig($configFile); good("Saved"); sleep(2);
}

// ═══════════════ AUTO MODES ═══════════════
function refresh_account(){
    global $DB,$CONFIG;
    $me=api_get("/api/me");
    if (is_array($me)&&!isset($me['error'])){
        $DB->setAccount([
            'email'=>$CONFIG['email'],
            'name'=>$me['name']??$me['username']??'-',
            'balance'=>$me['balance']??$me['coins']??0,
            'level'=>pretty_num($me['level']??0),
        ]);
        return $me;
    }
    return null;
}

function mode_autofarm($configFile){
    global $CONFIG,$access_token,$DB;
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login gagal.");sleep(2);return;}
    $access_token=$login['access_token'];
    $DB->set('session',['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0]);
    $DB->set('faucet',['status'=>'online','label'=>'ONLINE']);
    refresh_account();
    $DB->log("Auto-farming dimulai",'ok');
    $DB->clear_render();

    while (true) {
        // QUEST
        $DB->set('task',['current'=>'Claiming quests...','running'=>true,'elapsed'=>0,'total'=>1]);
        $DB->clear_render();
        $qs=claim_quests_once();
        $qc=$qs['daily']+$qs['weekly']+$qs['ach'];
        if ($qc>0){
            $DB->set('session',['quests'=>$DB->s['session']['quests']+$qc,'coins'=>$DB->s['session']['coins']+$qs['daily_coins']+$qs['weekly_coins']+$qs['ach_coins'],'xp'=>$DB->s['session']['xp']+$qs['daily_xp']+$qs['weekly_xp']+$qs['ach_xp']]);
        } else slog("No quest ready",'in');
        refresh_account();
        $DB->set('task',['running'=>false]);

        // DAILY
        $DB->set('task',['current'=>'Daily bonus...','running'=>true,'elapsed'=>0,'total'=>1]);
        $DB->clear_render();
        $dr=daily_claim_single();
        if ($dr['status']==='claimed'){
            $DB->set('session',['daily'=>$DB->s['session']['daily']+1,'coins'=>$DB->s['session']['coins']+$dr['coins'],'xp'=>$DB->s['session']['xp']+$dr['xp']]);
            slog("Daily +".fmt_coin($dr['coins'])."c +".$dr['xp']."xp",'ok');
            refresh_account();
        } elseif ($dr['status']==='cooldown'){ slog("Daily cooldown ".(int)($dr['wait']/60)."m",'wr'); }
        else fail("Daily failed");
        $DB->set('task',['running'=>false]);

        // FAUCET
        $DB->set('task',['current'=>'Faucet...','running'=>true,'elapsed'=>0,'total'=>1]);
        $DB->clear_render();
        $fr=faucet_claim_single();
        $fw=300;
        if ($fr['status']==='claimed'){
            $DB->set('session',['faucets'=>$DB->s['session']['faucets']+1,'coins'=>$DB->s['session']['coins']+$fr['coins'],'xp'=>$DB->s['session']['xp']+$fr['xp']]);
            $fw=$fr['wait'];
            slog("Faucet +".fmt_coin($fr['coins'])."c +".$fr['xp']."xp | bal ".$fr['balance'],'ok');
            refresh_account();
        } elseif ($fr['status']==='cooldown'){ $fw=$fr['wait']; slog("Faucet cooldown ".(int)($fw/60)."m",'wr'); }
        else { fail("Faucet failed"); $fw=60; }
        $DB->set('task',['running'=>false]);

        // MINIGAMES
        $DB->set('task',['current'=>'Minigames...','running'=>true,'elapsed'=>0,'total'=>1]);
        $DB->clear_render();
        run_minigames_once();
        $DB->set('task',['running'=>false]);

        // WAIT
        $wait=$fw+10;
        $DB->set('faucet',['status'=>'cooldown','label'=>'COOLDOWN']);
        $DB->timer($wait,"Next cycle");
        $DB->set('faucet',['status'=>'online','label'=>'ONLINE']);
        refresh_account();
    }
}

function mode_faucet($configFile){
    global $CONFIG,$access_token,$DB;
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login gagal.");sleep(2);return;}
    $access_token=$login['access_token'];
    $DB->set('session',['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0]);
    refresh_account();
    $DB->log("Faucet loop dimulai",'ok');
    $DB->clear_render();

    while (true) {
        $qs=claim_quests_once();
        $qc=$qs['daily']+$qs['weekly']+$qs['ach'];
        if ($qc>0){
            $DB->set('session',['quests'=>$DB->s['session']['quests']+$qc,'coins'=>$DB->s['session']['coins']+$qs['daily_coins']+$qs['weekly_coins']+$qs['ach_coins'],'xp'=>$DB->s['session']['xp']+$qs['daily_xp']+$qs['weekly_xp']+$qs['ach_xp']]);
            refresh_account();
        }
        $dr=daily_claim_single();
        if ($dr['status']==='claimed'){
            $DB->set('session',['daily'=>$DB->s['session']['daily']+1,'coins'=>$DB->s['session']['coins']+$dr['coins'],'xp'=>$DB->s['session']['xp']+$dr['xp']]);
            slog("Daily +".fmt_coin($dr['coins'])."c",'ok');
        }
        $fr=faucet_claim_single();
        $fw=300;
        if ($fr['status']==='claimed'){
            $DB->set('session',['faucets'=>$DB->s['session']['faucets']+1,'coins'=>$DB->s['session']['coins']+$fr['coins'],'xp'=>$DB->s['session']['xp']+$fr['xp']]);
            $fw=$fr['wait'];
            slog("Faucet +".fmt_coin($fr['coins'])."c | bal ".$fr['balance'],'ok');
            refresh_account();
        } elseif ($fr['status']==='cooldown'){ $fw=$fr['wait']; slog("Faucet cooldown ".(int)($fw/60)."m",'wr'); }
        else { fail("Faucet failed"); $fw=60; }
        $DB->set('faucet',['status'=>'cooldown','label'=>'COOLDOWN']);
        $DB->timer($fw+2,"Next faucet");
        $DB->set('faucet',['status'=>'online','label'=>'ONLINE']);
    }
}

function mode_daily($configFile){
    global $CONFIG,$access_token,$DB;
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login gagal.");sleep(2);return;}
    $access_token=$login['access_token'];
    $DB->set('session',['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0]);
    refresh_account();
    $DB->log("Daily loop dimulai",'ok');
    $DB->clear_render();
    while (true){
        $r=daily_claim_single();
        if ($r['status']==='claimed'){
            $DB->set('session',['daily'=>$DB->s['session']['daily']+1,'coins'=>$DB->s['session']['coins']+$r['coins'],'xp'=>$DB->s['session']['xp']+$r['xp']]);
            slog("Daily +".fmt_coin($r['coins'])."c",'ok');
            refresh_account();
            sleep(5);
        } elseif ($r['status']==='cooldown'){
            slog("Cooldown ".(int)($r['wait']/60)."m",'wr');
            $DB->set('faucet',['status'=>'cooldown','label'=>'COOLDOWN']);
            $DB->timer($r['wait']+2,"Daily cooldown");
            $DB->set('faucet',['status'=>'online','label'=>'ONLINE']);
        } else { fail("Failed. Retry 15s"); sleep(15); }
    }
}

function mode_quest($configFile){
    global $CONFIG,$access_token,$DB;
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login gagal.");sleep(2);return;}
    $access_token=$login['access_token'];
    $DB->set('session',['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0]);
    refresh_account();
    $DB->log("Quest loop dimulai",'ok');
    $DB->clear_render();
    while (true){
        $qs=claim_quests_once();
        $qc=$qs['daily']+$qs['weekly']+$qs['ach'];
        if ($qc>0){
            $DB->set('session',['quests'=>$DB->s['session']['quests']+$qc,'coins'=>$DB->s['session']['coins']+$qs['daily_coins']+$qs['weekly_coins']+$qs['ach_coins'],'xp'=>$DB->s['session']['xp']+$qs['daily_xp']+$qs['weekly_xp']+$qs['ach_xp']]);
            slog("Claimed ".$qc." quest",'ok');
            refresh_account();
            $DB->timer(30,"Retry");
        } else {
            slog("No quest ready. Wait 60s",'wr');
            $DB->timer(60,"Waiting");
        }
    }
}

function mode_minigames($configFile){
    global $CONFIG,$access_token,$DB;
    if (empty($CONFIG['email'])){fail("Akun belum di-set.");sleep(2);return;}
    setupSession();
    $login=ensure_login($CONFIG['email'],$CONFIG['password']);
    if (!$login){fail("Login gagal.");sleep(2);return;}
    $access_token=$login['access_token'];
    $DB->set('session',['start'=>time(),'coins'=>0,'xp'=>0,'faucets'=>0,'quests'=>0,'daily'=>0,'minigames'=>0]);
    refresh_account();
    $DB->log("Minigames loop dimulai",'ok');
    $DB->clear_render();
    while (true){
        $played=run_minigames_once();
        refresh_account();
        if (!$played) slog("No plays. Wait 180s",'wr');
        $DB->timer(180,"Waiting");
    }
}

// ═══════════════ MENU ═══════════════
function main_menu($configFile){
    global $CONFIG,$access_token,$handling_interrupt,$DB;
    while (true){
        try {
            clear(); banner();
            $mk=(strlen($CONFIG['apikey'])>10)?substr($CONFIG['apikey'],0,8)."...".substr($CONFIG['apikey'],-4):($CONFIG['apikey']?:"(kosong)");
            $accDisplay=$CONFIG['email']?maskEmail($CONFIG['email']):NEON_RED."(belum di-set)".RESET;
            $balance='-';$level='-';
            if (!empty($CONFIG['email'])){setupSession();$me=api_get("/api/me");if (is_array($me)&&!isset($me['error'])){$balance=pretty_num($me['balance']??$me['coins']??'-');$level=pretty_num($me['level']['level']??$me['level']??'-');}}
            echo NEON_MAGENTA.BOLD."[ ACCOUNT INFO ]".RESET."\n";
            echo NEON_CYAN."==================================================".RESET."\n";
            echo NEON_WHITE."Akun     : ".NEON_YELLOW.$accDisplay.RESET."\n";
            echo NEON_WHITE."Balance  : ".NEON_GREEN.$balance.RESET."\n";
            echo NEON_WHITE."Level    : ".NEON_BLUE.$level.RESET."\n";
            echo NEON_WHITE."Provider : ".NEON_GREEN."MoneyMaker_w (Waryono)".RESET."\n";
            echo NEON_WHITE."API Key  : ".NEON_MAGENTA.$mk.RESET."\n";
            echo NEON_CYAN."==================================================".RESET."\n\n";
            echo NEON_MAGENTA.BOLD."[ PILIH MENU ]".RESET."\n";
            echo NEON_CYAN."==================================================".RESET."\n";
            echo NEON_GREEN."[1] ".RESET.NEON_YELLOW.BOLD."🌾 AUTO FARMING ALL".RESET."\n";
            echo NEON_GREEN."[2] ".RESET."Faucet + Quest + Daily\n";
            echo NEON_GREEN."[3] ".RESET."Auto Daily Bonus 🎁\n";
            echo NEON_GREEN."[4] ".RESET."Auto Minigames 🎮\n";
            echo NEON_GREEN."[5] ".RESET."Auto Claim Quest 📋\n";
            echo NEON_GREEN."[6] ".RESET."Attack Boss ⚔️\n";
            echo NEON_GREEN."[7] ".RESET."Battle Pass 🎫\n";
            echo NEON_GREEN."[8] ".RESET."Auto Withdraw 💸\n";
            echo NEON_GREEN."[9] ".RESET."Withdraw History 📜\n";
            echo NEON_GREEN."[10] ".RESET."Set Akun\n";
            echo NEON_GREEN."[11] ".RESET."Set API Key\n";
            echo NEON_RED."[0] ".RESET."Keluar\n";
            echo NEON_CYAN."==================================================".RESET."\n";
            echo "\n".NEON_WHITE."Pilih (0-11): ".NEON_YELLOW;
            $c=trim(fgets(STDIN));
            switch ($c){
                case '1': mode_autofarm($configFile); break;
                case '2': mode_faucet($configFile); break;
                case '3': mode_daily($configFile); break;
                case '4': mode_minigames($configFile); break;
                case '5': mode_quest($configFile); break;
                case '6': menu_boss($configFile); break;
                case '7': menu_battlepass($configFile); break;
                case '8': menu_withdraw($configFile); break;
                case '9': menu_wd_history($configFile); break;
                case '10': menu_set_account($configFile); break;
                case '11': menu_set_apikey($configFile); break;
                case '0': echo "\n".NEON_GREEN."Terima kasih!".RESET."\n"; exit;
                default: fail("Invalid"); sleep(1); break;
            }
        } catch (UserInterrupt $e){
            echo "\n".NEON_YELLOW."Press Enter...".RESET; @fgets(STDIN);
            $handling_interrupt=false;
        } catch (EnergyOut $e){
            echo "\n".NEON_RED."[!] Energy habis!".RESET."\n";
            echo NEON_YELLOW."Press Enter...".RESET; @fgets(STDIN);
        }
    }
}

register_shutdown_function(function(){echo "\r\033[K";});
if (function_exists('pcntl_async_signals') && function_exists('pcntl_signal') && defined('SIGINT')){
    pcntl_async_signals(true);
    pcntl_signal(SIGINT, function(){
        if (!empty($GLOBALS['handling_interrupt'])) exit(1);
        $GLOBALS['handling_interrupt']=true;
        throw new UserInterrupt();
    });
}

loadConfig($configFile);
main_menu($configFile);
