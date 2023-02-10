#!/usr/bin/env python
from __future__ import print_function
import os
import re
import sys
import json
import time
import binascii
import tarfile
import atexit
import socket

import redis   # 导入redis 模块
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

origin_getaddrinfo = socket.getaddrinfo
def getaddrinfo_wrapper(host, port, family=0, socktype=0, proto=0, flags=0):
    return origin_getaddrinfo(host, port, socket.AF_INET, socktype, proto, flags)
socket.getaddrinfo = getaddrinfo_wrapper

try:
    import ssl
    import hashlib
except ImportError as ex:
    print("Error: cannot import module ssl or hashlib (%s)." % str(ex))
    print("If you are using openwrt, run \"opkg install python-openssl\"")
    os._exit(0)
try:
    import zlib
except ImportError as ex:
    print("Warning: cannot import module zlib (%s)." % str(ex))
    # TODO: if there's a python dist that is not bundled with zlib ever exists, disable gzip Accept-Encoding

#xunlei use self-signed certificate; on py2.7.9+
if hasattr(ssl, '_create_unverified_context') and hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

#rsa_mod = 0xAC69F5CCC8BDE47CD3D371603748378C9CFAD2938A6B021E0E191013975AD683F5CBF9ADE8BD7D46B4D2EC2D78AF146F1DD2D50DC51446BB8880B8CE88D476694DFC60594393BEEFAA16F5DBCEBE22F89D640F5336E42F587DC4AFEDEFEAC36CF007009CCCE5C1ACB4FF06FBA69802A8085C2C54BADD0597FC83E6870F1E36FD
#rsa_pubexp = 0x010001

APP_VERSION = "2.4.1.3"
PROTOCOL_VERSION = 200
VASID_DOWN = 14 # vasid for downstream accel
VASID_UP = 33 # vasid for upstream accel
FALLBACK_MAC = '000000000000'
FALLBACK_PORTAL = "119.147.41.210:12180"
FALLBACK_UPPORTAL = "153.37.208.185:81"

UNICODE_WARNING_SHOWN = False

PY3K = sys.version_info[0] == 3
if not PY3K:
    import urllib2
    from urllib2 import URLError
    from urllib import quote as url_quote
    from cStringIO import StringIO as sio
    #rsa_pubexp = long(rsa_pubexp)
else:
    import urllib.request as urllib2
    from urllib.error import URLError
    from urllib.parse import quote as url_quote
    from io import BytesIO as sio

account_session = '.swjsq.session.up'
account_file_plain = 'swjsq.account.txt'
shell_file = 'swjsq_wget.sh'
ipk_file = 'swjsq_0.0.1_all.ipk'
log_file = 'swjsq.log'

login_xunlei_intv = 180 # do not login twice in 10min

DEVICE = "SmallRice R1"
DEVICE_MODEL = "R1"
OS_VERSION = "5.0.1"
OS_API_LEVEL = "24"
OS_BUILD = "LRX22C"

header_xl = {
    'Content-Type':'',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'android-async-http/xl-acc-sdk/version-2.1.1.177662'
}
header_api = {
    'Content-Type':'',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android %s; %s Build/%s)' % (OS_VERSION, DEVICE_MODEL, OS_BUILD)
}


def get_mac(nic = '', to_splt = ':'):
    if os.name == 'nt':
        cmd = 'ipconfig /all'
        splt = '-'
    elif os.name == "posix":
        if os.path.exists('/usr/bin/ip') or os.path.exists('/bin/ip'):
            if nic:
                cmd = 'ip link show dev %s' % nic
            else:
                # Unfortunately, loopback interface always comes first
                # So we have to grep it out
                cmd = 'ip link show up | grep -v loopback'
        else:
            cmd = 'ifconfig %s' % (nic or '-a')
        splt = ':'
    else:
        return FALLBACK_MAC
    try:
        r = os.popen(cmd).read()
        if r:
            _ = re.findall('((?:[0-9A-Fa-f]{2}%s){5}[0-9A-Fa-f]{2})' % splt, r)
            if not _:
                return FALLBACK_MAC
            else:
                return _[0].replace(splt, to_splt)
    except:
        pass
    return FALLBACK_MAC

    
def api_url(up = False):
    portal = None
    if up:
        portals = (("", "up", 80), )
    else:
        portals = (("", "", 81), ("2", "", 81), ("", "", 82))
    for cmb in portals:
        portal = json.loads(http_req("http://api%s.%sportal.swjsq.vip.xunlei.com:%d/v2/queryportal" % cmb))
        try:
            portal = json.loads(http_req("http://api%s.%sportal.swjsq.vip.xunlei.com:%d/v2/queryportal" % cmb))
        except:
            pass
        else:
            break
    if not portal or portal['errno']:
        print('Warning: get interface_ip failed, use fallback address')
        if up:
            return FALLBACK_UPPORTAL
        else:
            return FALLBACK_PORTAL
    return '%s:%s' % (portal['interface_ip'], portal['interface_port'])

def long2hex(l):
    return hex(l)[2:].upper().rstrip('L')

_real_print = print

def print(s, **kwargs):
    logfd = open(log_file, 'ab')
    line = "%s %s" % (time.strftime('%X', time.localtime(time.time())), s)
    if PY3K:
        logfd.write(line.encode('utf-8'))
    else:
        try:
            logfd.write(line)
        except UnicodeEncodeError:
            logfd.write(line.encode('utf-8'))
    if PY3K:
        logfd.write(b'\n')
    else:
        logfd.write("\n")
    logfd.close()
    _real_print(line, **kwargs)
    
def uprint(s, fallback = None, end = None):
    global UNICODE_WARNING_SHOWN
    while True:
        try:
            print(s, end = end)
        except UnicodeEncodeError:
            if UNICODE_WARNING_SHOWN:
                print('Warning: locale of your system may not be utf8 compatible, output will be truncated')
                UNICODE_WARNING_SHOWN = True
        else:
            break
        try:
            print(s.encode('utf-8'), end = end)
        except UnicodeEncodeError:
            if fallback:
                print(fallback, end = end)
        break

def http_req(url, headers = {}, body = None, encoding = 'utf-8'):
    req = urllib2.Request(url)
    for k in headers:
        req.add_header(k, headers[k])
    if sys.version.startswith('3') and isinstance(body, str):
        body = bytes(body, encoding = 'ascii')
    resp = urllib2.urlopen(req, data = body, timeout = 90)  # let's be more patient!
    buf = resp.read()
    # check if response is gzip encoded
    if buf.startswith(b'\037\213'):
        try:
            buf = zlib.decompress(buf, 16 + zlib.MAX_WBITS) # skip gzip headers
        except Exception as ex:
            print('Warning: malformed gzip response (%s).' % str(ex))
            # buf is unchanged
    ret = buf.decode(encoding)
    if sys.version.startswith('3') and isinstance(ret, bytes):
        ret = str(ret)
    return ret


class fast_d1ck(object):
    def __init__(self):
        self.api_url = api_url(up = False)
        self.api_up_url = api_url(up = True)
        self.mac = get_mac(to_splt = '').upper() + '004V'
        self.xl_uid = None
        self.xl_session = None
        self.xl_loginkey = None
        self.xl_login_payload = None
        self.last_login_xunlei = 0
        self.do_down_accel = False
        self.do_up_accel = False
        
        self.state = 0

    def load_xl(self, dt):
        if 'sessionID' in dt:
            self.xl_session = dt['sessionID']
            r.set('swjsq:dt:sessionID',dt['sessionID'])  # 存到redis上
            print('load_xl: sessionID: %s' % self.xl_session)
        if 'userID' in dt:
            self.xl_uid = dt['userID']
        if 'loginKey' in dt:
            self.xl_loginkey = dt['loginKey']

    def login_xunlei(self, uname, pwd):       
        _ = int(login_xunlei_intv - time.time() + self.last_login_xunlei)
        if _ > 0: 
            print("sleep %ds to prevent login flood" % _)
            time.sleep(_)
        self.last_login_xunlei = time.time()

        # pwd = rsa_encode(pwd_md5)
        fake_device_id = hashlib.md5(("msfdc%s23333" % pwd).encode('utf-8')).hexdigest() # just generate a 32bit string
        # sign = div.10?.device_id + md5(sha1(packageName + businessType + md5(a protocolVersion specific GUID)))
        device_sign = "div101.%s%s" % (fake_device_id, hashlib.md5(
            hashlib.sha1(("%scom.xunlei.vip.swjsq68c7f21687eed3cdb400ca11fc2263c998" % fake_device_id).encode('utf-8'))
                .hexdigest().encode('utf-8')
         ).hexdigest())
        _payload = {
                "protocolVersion": str(PROTOCOL_VERSION),
                "sequenceNo": "1000001",
                "platformVersion": "2",
                "sdkVersion": "177662",
                "peerID": self.mac,
                "businessType": "68",
                "clientVersion": APP_VERSION,
                "devicesign":device_sign,
                "isCompressed": "0",
                #"cmdID": 1,
                "userName": uname,
                "passWord": pwd,
                #"loginType": 0, # normal account
                "sessionID": "",
                "verifyKey": "",
                "verifyCode": "",
                "appName": "ANDROID-com.xunlei.vip.swjsq",
                #"rsaKey": {
                #    "e": "%06X" % rsa_pubexp,
                #    "n": long2hex(rsa_mod)
                #},
                #"extensionList": "",
                "deviceModel": DEVICE_MODEL,
                "deviceName": DEVICE,
                "OSVersion": OS_VERSION
        }
        ct = http_req('https://mobile-login.xunlei.com:443/login', body=json.dumps(_payload), headers=header_xl, encoding='utf-8')
        self.xl_login_payload = _payload
        dt = json.loads(ct)
        
        self.load_xl(dt)
        self.save_context(dt)
        time.sleep(5)
        return dt


    def check_xunlei_vas(self, vasid):
        # copy original payload to new dict
        _payload = dict(self.xl_login_payload)
        _payload.update({
            "sequenceNo": "1000002",
            "vasid": str(vasid),
            "userID": str(self.xl_uid),
            "sessionID": self.xl_session,
            #"extensionList": [
            #    "payId", "isVip", "mobile", "birthday", "isSubAccount", "isAutoDeduct", "isYear", "imgURL",
            #    "vipDayGrow", "role", "province", "rank", "expireDate", "personalSign", "jumpKey", "allowScore",
            #    "nickName", "vipGrow", "isSpecialNum", "vipLevel", "order", "payName", "isRemind", "account",
            #    "sex", "vasType", "register", "todayScore", "city", "country"
            #]
        })
        # delete unwanted kv pairs
        for k in ('userName', 'passWord', 'verifyKey', 'verifyCode'):
            del _payload[k]
        ct = http_req('https://mobile-login.xunlei.com:443/getuserinfo', body=json.dumps(_payload), headers=header_xl, encoding='utf-8')
        return json.loads(ct)

    def renew_xunlei(self):
        _ = int(login_xunlei_intv - time.time() + self.last_login_xunlei)
        if _ > 0: 
            print("sleep %ds to prevent login flood" % _)
            time.sleep(_)
        self.last_login_xunlei = time.time()

        _payload = dict(self.xl_login_payload)
        _payload.update({
            "sequenceNo": "1000001",
            "userName": str(self.xl_uid), #wtf
            "loginKey": self.xl_loginkey,
        })
        for k in ('passWord', 'verifyKey', 'verifyCode', "sessionID"):
            del _payload[k]
        ct = http_req('https://mobile-login.xunlei.com:443/loginkey ', body=json.dumps(_payload), headers=header_xl, encoding='utf-8')
        dt = json.loads(ct)
        
        self.load_xl(dt)
        self.save_context(dt)
        time.sleep(5)
        return dt

    def save_context(self, dt):
        with open(account_session, 'w') as f:
            f.write('%s\n%s' % (json.dumps(dt), json.dumps(self.xl_login_payload)))

    '''
    core request function
    '''
    def api(self, cmd, extras = '', no_session = False):
        ret = {}
        for _k1, api_url_k, _clienttype, _v in (('down', 'api_url', 'swjsq', 'do_down_accel'), ('up', 'api_up_url', 'uplink', 'do_up_accel')):
            if not getattr(self, _v):
                continue
            while True:
                # missing dial_account, (userid), os
                api_url = getattr(self, api_url_k)
                # TODO: phasing out time_and
                sessionid_get = r.get('swjsq:dt:sessionID')
                url = 'http://%s/v2/%s?%sclient_type=android-%s-%s&peerid=%s&time_and=%d&client_version=android%s-%s&userid=%s&os=android-%s%s' % (
                        api_url,
                        cmd,
                        ('sessionid=%s&' % sessionid_get) if not no_session else '',
                        _clienttype, APP_VERSION,
                        self.mac,
                        time.time() * 1000,
                        _clienttype, APP_VERSION,
                        self.xl_uid,
                        url_quote("%s.%s%s" % (OS_VERSION, OS_API_LEVEL, DEVICE_MODEL)),
                        ('&%s' % extras) if extras else '',
                )
                print(url)
                try:
                    ret[_k1] = {}
                    ret[_k1] = json.loads(http_req(url, headers = header_api))
                    break
                except URLError as ex:
                    uprint("Warning: error during %sapi connection: %s, use portal: %s" % (_k1, str(ex), api_url))
                    if (_k1 == 'down' and api_url == FALLBACK_PORTAL) or (_k1 == 'up' and api_url == FALLBACK_UPPORTAL):
                        print("Error: can't connect to %s api. Retry after 30s!" % _k1)
                        
                        time.sleep(30)
                        # os._exit(5)
                    if _k1 == 'down':
                        setattr(self, api_url_k, FALLBACK_PORTAL)
                    elif _k1 == 'up':
                        setattr(self, api_url_k, FALLBACK_UPPORTAL)
        return ret


    def run(self, uname, pwd, save=True):
        if uname[-2] == ':':
            print('Error: sub account can not upgrade')
            os._exit(3)

        login_methods = [lambda : self.login_xunlei(uname, pwd)]
        if self.xl_session:
            login_methods.insert(0, self.renew_xunlei)

        failed = True
        for _lm in login_methods:
            dt = _lm()
            if dt['errorCode'] != "0" or not self.xl_session or not self.xl_loginkey:
                uprint('Error: login xunlei failed, %s' % dt['errorDesc'], 'Error: login failed')
                print(dt)
            else:
                failed = False
                break
        if failed:
            # logfd.close()
            os._exit(1)
        print('Login xunlei succeeded')
        
        yyyymmdd = time.strftime("%Y%m%d", time.localtime(time.time()))
        
        if 'vipList' not in dt:
            vipList = []
        else:
            vipList = dt['vipList']

        # chaoji member
        if vipList and vipList[0]['isVip'] == "1" and vipList[0]['vasType'] == "5" and vipList[0]['expireDate'] > yyyymmdd: # choaji membership
            self.do_down_accel = True
            # self.do_up_accel = True
            print('Expire date for chaoji member: %s' % vipList[0]['expireDate'])

        # kuainiao down/up member
        _vas_debug = []

        # for _vas, _name, _v in ((VASID_DOWN, 'fastdick', 'do_down_accel'), 
        #                         (VASID_UP, 'upstream acceleration', 'do_up_accel')):
        for _vas, _name, _v in [(VASID_UP, 'upstream acceleration', 'do_up_accel')]:  # 只提速一种
            if getattr(self, _v): # don't check again if vas is activated in other membership
                continue
            _dt = self.check_xunlei_vas(_vas)
            if 'vipList' not in _dt or not _dt['vipList']:
                continue
            for vip in _dt['vipList']:
                if vip['vasid'] == str(_vas):
                    _vas_debug.append(vip)
                    if vip['isVip'] == "1":
                        if vip['expireDate'] < yyyymmdd:
                            print('Warning: Your %s membership expires on %s' % (_name, vip['expireDate']))
                        else:
                            print('Expire date for %s: %s' % (_name, vip['expireDate']))
                            setattr(self, _v, True)
                
        if not self.do_down_accel and not self.do_up_accel:
            print('Error: You are neither xunlei fastdick member nor upstream acceleration member, buy buy buy!\nDebug: %s' % _vas_debug)
            os._exit(2)

        if save:
            try:
                os.remove(account_file_plain)
            except:
                pass
            self.save_context(dt)
            # with open(account_session, 'w') as f:
            #     f.write('%s\n%s' % (json.dumps(dt), json.dumps(self.xl_login_payload)))
        
        # 查BW信息。这里只查UP信息
        _k1, _k2, _name, _v = ('up', 'upstream', 'upstream acceleration', 'do_up_accel')
        _to_upgrade = []
        while True:
            api_ret = self.api('bandwidth', no_session = True)
            _ = api_ret[_k1]
            print('BW query info: ' + str(_))
            if _['errno'] == "500":  # 500 timeout
                uprint('500 Warning: %s can not upgrade, so sad TAT: %s' % (_name, _['message']), 'Error: %s can not upgrade, so sad TAT' % _name)
                time.sleep(30)
                continue
            elif 'can_upgrade' not in _ or not _['can_upgrade']:
                uprint('Warning: %s can not upgrade, so sad TAT: %s' % (_name, _['message']), 'Error: %s can not upgrade, so sad TAT' % _name)
                time.sleep(30)
                continue
            else:  # 登陆没问题了才break
                _to_upgrade.append('%s %dM -> %dM' % (
                        _k1, 
                        _['bandwidth'][_k2]/1024,
                        _['max_bandwidth'][_k2]/1024,
                    ))
                break
        
        if not self.do_down_accel and not self.do_up_accel:
            print("Error: neither downstream nor upstream can be upgraded")
            os._exit(3)
        
        _avail = api_ret[list(api_ret.keys())[0]]
        
        uprint('To Upgrade: %s%s %s' % ( _avail['province_name'], _avail['sp_name'], ", ".join(_to_upgrade)),
                'To Upgrade: %s %s %s' % ( _avail['province'], _avail['sp'], ", ".join(_to_upgrade))
              )
              
        _dial_account = _avail['dial_account']

        #print(_)
        def _atexit_func():
            print("Sending recover request")
            try:
                api_ret = self.api('recover', extras = "dial_account=%s" % _dial_account)
                print(api_ret)
            except KeyboardInterrupt:
                print('Secondary ctrl+c pressed, exiting')
            # try:
            #     # logfd.close()
            # except:
            #     pass
        atexit.register(_atexit_func)
        self.state = 0
        while True:
            print('-'*10)
            has_error = False
            try:
                # self.state=1~35 keepalive,  self.state++
                # self.state=18 (3h) re-upgrade all, self.state-=18
                # self.state=100 login, self.state:=18
                if self.state == 100:
                    _dt_t = self.renew_xunlei()
                    if int(_dt_t['errorCode']):
                        time.sleep(30)
                        dt = self.login_xunlei(uname, pwd)
                        if int(dt['errorCode']):
                            self.state = 100
                            continue
                    else:
                        _dt_t = dt
                    self.state = 18
                if self.state % 18 == 0:#3h
                    
                    print('Initializing upgrade')
                    if self.state:# not first time
                        self.api('recover', extras = "dial_account=%s" % _dial_account)
                        # throttle to avoid later upgrade call error with too frequent request
                        time.sleep(20)
                    api_ret = self.api('upgrade', extras = "user_type=1&dial_account=%s" % _dial_account)
                    #print(_)
                    _upgrade_done = []
                    for _k1, _k2 in ('down', 'downstream'), ('up', 'upstream'):
                        if _k1 not in api_ret:
                            continue
                        if not api_ret[_k1]['errno']:
                            _upgrade_done.append("%s %dM" % (_k1, api_ret[_k1]['bandwidth'][_k2]/1024))
                    if _upgrade_done:
                        print("Upgrade done: %s" % ", ".join(_upgrade_done))
                    op = "upgrade"
                    print(api_ret)
                else:
                    # _dt_t = self.renew_xunlei()
                    # if _dt_t['errorCode']:
                    #     self.state = 100
                    #     continue
                    try:
                        api_ret = self.api('keepalive')
                    except Exception as ex:
                        print("keepalive exception: %s" % str(ex))
                        time.sleep(30)
                        self.state = 18
                        continue
                    op = "keepalive"
                    
                print(op)
                # controls if we skip sleep
                skip_sleep = False
                for _k1, _k2, _name, _v in ('down', 'Downstream', 'fastdick', 'do_down_accel'), ('up', 'Upstream', 'upstream acceleration', 'do_up_accel'):
                    if _k1 in api_ret and api_ret[_k1]['errno']:
                        _ = api_ret[_k1]
                        print('%s %s error %s: %s' % (_k2, op, _['errno'], _['message']))
                        if _['errno'] in (513, 824):# TEST: re-upgrade when get 513 or 824 speedup closed
                            self.state = 100
                        elif _['errno'] == 812:
                            print('%s already upgraded, continuing' % _k2)
                        elif _['errno'] == 717 or _['errno'] == 718:# re-upgrade when get 'account auth session failed'
                            self.state = 100
                        elif _['errno'] == 518: # disable down/up when get qurey vip response user not has business property
                            print("Warning: membership expired? Disabling %s" % _name)
                            setattr(self, _v, False)
                        elif _['errno'] == 711:
                            print("request too frequent, retrying in 1 minute")
                            time.sleep(30)
                            skip_sleep = True
                            # not sure if re-login is needed
                            # self.state = 100
                        elif _['errno'] == 500:
                            # 缩短下upgrade or keepalive 500重发的时间
                            print("500 timeout, retry in 1 mins")
                            if op == 'keepalive':
                                self.state = 100
                            time.sleep(30)
                            skip_sleep = True
                        elif _['errno'] == 1001 and op == 'upgrade':
                            print("1001 wtf， retry in 1 mins")
                            time.sleep(30)
                            skip_sleep = True
                        else:
                            has_error = True
                if self.state == 100 or skip_sleep:
                    continue
            except Exception as ex:
                import traceback
                _ = traceback.format_exc()
                print(_)
                has_error = True
            if has_error:
                # sleep 5 min and repeat the same state
                time.sleep(290)#5 min
            else:
                print("success!")
                self.state += 1
                time.sleep(590)  # 成功的效果可以保持10min

if __name__ == '__main__':
    # change to script directory
    if getattr(sys, 'frozen', False):
        _wd = os.path.dirname(os.path.realpath(sys.executable))
    else:
        _wd = sys.path[0]
    os.chdir(_wd)
    
    ins = fast_d1ck()
    
    try:
        if os.path.exists(account_file_plain):
            uid, pwd = open(account_file_plain).read().strip().split(',')
            ins.run(uid, pwd)
        elif os.path.exists(account_session):
            with open(account_session) as f:
                session = json.loads(f.readline())
                ins.xl_login_payload = json.loads(f.readline())
            ins.load_xl(session)
            ins.run(ins.xl_login_payload['userName'], ins.xl_login_payload['passWord'])
        elif 'XUNLEI_UID' in os.environ and 'XUNLEI_PASSWD' in os.environ:
            uid = os.environ['XUNLEI_UID']
            pwd = os.environ['XUNLEI_PASSWD']
            ins.run(uid, pwd)
        else:
            _real_print('Please use XUNLEI_UID=<uid>/XUNLEI_PASSWD=<pass> envrionment varibles or create config file "%s", input account splitting with comma(,). Eg:\nyonghuming,mima' % account_file_plain)
    except KeyboardInterrupt:
        pass