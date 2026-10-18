"""北化课程平台认证模块。

认证入口会从课程平台 SSO 重定向自动识别：新版 sidportal 使用页面下发的
execution/croypto 并提交 AES-ECB/PKCS#7 表单；旧版 portal CAS 使用
flowKey、公钥和 SM2。验证码、风控和 MFA 要求明确报错，不绕过验证。
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.parse
from http import HTTPStatus

import requests
from bs4 import BeautifulSoup

from .exceptions import LoginError, NetworkError
from .sm2_crypto import encrypt as _sm2_encrypt

_PORTAL_BASE = "https://portal.buct.edu.cn"
_CAS_BASE = f"{_PORTAL_BASE}/cas"
_SID_PORTAL_BASE = "https://sidportal.buct.edu.cn"
_COURSE_BASE = "https://course.buct.edu.cn"
_MEOL_SSO_PATH = "/meol/homepage/common/sso_login.jsp"
_SUCCESS_CODE = 666666
_MAX_PAGE_BYTES = 1 << 20

_ERROR_MESSAGES = {
    160001: "该账号需要 MFA 二次验证，本库暂不支持，请先在浏览器完成一次登录",
    160002: "该账号需要图形验证码，本库暂不支持，请稍后再试或先在浏览器完成一次登录",
    160066: "该账号需要选择代理用户，本库暂不支持",
    160067: "该账号需要添加常用设备，请先在浏览器确认一次",
    170002: "用户名或密码错误",
    170004: "登录信息错误",
    170006: "认证未通过",
    180003: "用户名为空",
    180004: "密码为空",
    180006: "密码需要修改",
    180014: "请求格式错误（json 格式错误）",
    180026: "没找到 UID",
    180028: "账号登录失败次数过多，已临时锁定，请等待 30 分钟",
    180029: "错误次数太多，账号已被锁死",
    180046: "flowKey 无效（FlowKey 没找到）",
    180076: "flowKey 已被使用过，不能重复使用",
    180083: "无系统权限或账号已停用",
    600904: "TGT 创建失败",
    999999: "操作失败",
}
_FLOW_KEY_EXPIRED_CODES = {180046, 180076}
_SID_ERROR_MESSAGES = {
    "1030027": "用户名或密码错误", "1030031": "用户名或密码错误",
    "1030028": "账号已锁定，请在浏览器处理或等待解锁",
    "1410040": "当前账号不可用", "1410041": "当前账号不可用",
    "1320007": "需要图形验证码，请在浏览器完成验证",
    "1030007": "验证码不正确，请在浏览器重新验证",
    "1330001": "需要风险验证，请在浏览器完成验证",
    "1030078": "需要选择账号，请在浏览器完成登录",
    "1030099": "需要选择身份，请在浏览器完成登录",
}


def _sid_error(code: str) -> LoginError:
    return LoginError(_SID_ERROR_MESSAGES.get(code, "统一身份认证未完成，请在浏览器检查账号、验证码或二次验证"))


def _aes_encrypt(key_b64: str, text: str) -> str:
    """匹配 sidportal 的 aesEncrypt：Base64 key + AES-ECB + PKCS#7。"""
    try:
        from Crypto.Cipher import AES
    except ImportError as exc:  # pragma: no cover - only used by sidportal deployments
        raise LoginError("新版认证需要 pycryptodome 依赖") from exc
    try:
        key = base64.b64decode(key_b64, validate=True)
        raw = text.encode("utf-8")
        padding = 16 - len(raw) % 16
        raw += bytes([padding]) * padding
        return base64.b64encode(AES.new(key, AES.MODE_ECB).encrypt(raw)).decode("ascii")
    except (ValueError, TypeError) as exc:
        raise LoginError("无效的认证加密参数") from exc


class BUCTAuth:
    """北化课程平台认证类（新版 sidportal + 旧版 CAS 兼容）。"""

    PORTAL_BASE = _PORTAL_BASE
    CAS_BASE = _CAS_BASE
    SID_PORTAL_BASE = _SID_PORTAL_BASE
    COURSE_BASE = _COURSE_BASE
    MEOL_SSO_ENTRY = f"{_COURSE_BASE}{_MEOL_SSO_PATH}"
    DEFAULT_PORTAL_SERVICE = "http://i.buct.edu.cn"

    def __init__(self, service=None, timeout=15):
        self.base_url = self.COURSE_BASE
        self.timeout = timeout
        self.service = service
        self._is_logged_in = False
        self.flow_key = None
        self.public_key = None
        self._resolved_service = None
        self._login_entry = None
        self._login_url_override = None
        self._active_sid = False
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        )
        self.session = self._new_session()

    def _new_session(self):
        session = requests.Session()
        session.headers.update({
            "User-Agent": self._user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
        })
        return session

    def set_service(self, service):
        self.service = service

    def set_login_url(self, login_url):
        self._login_url_override = login_url or None

    @property
    def _meol_sso_entry(self):
        return f"{self.base_url}{_MEOL_SSO_PATH}"

    def _cookie_value(self, name):
        for cookie in self.session.cookies:
            if cookie.name == name:
                return cookie.value
        return None

    @staticmethod
    def _to_half_width(text):
        return "".join(
            chr(ord(ch) - 0xFEE0) if 0xFF01 <= ord(ch) <= 0xFF5E else " " if ord(ch) == 0x3000 else ch
            for ch in text
        )

    def _resolve_service(self):
        if self.service:
            self._login_entry = f"{self.SID_PORTAL_BASE}/login?service={urllib.parse.quote(self.service, safe='')}"
            return self.service
        response = self.session.get(self._meol_sso_entry, allow_redirects=False, timeout=self.timeout)
        location = response.headers.get("location")
        if not location:
            raise LoginError(f"无法从课程平台 SSO 入口获取 service（HTTP {response.status_code}）")
        parsed = urllib.parse.urljoin(self._meol_sso_entry, location)
        service = urllib.parse.parse_qs(urllib.parse.urlparse(parsed).query).get("service", [None])[0]
        if not service:
            raise LoginError("SSO 入口未返回 service 参数")
        self._login_entry = parsed if self._is_sid_login_url(parsed) else None
        return service

    def _fetch_flow_key(self, service):
        response = self.session.get(f"{self.CAS_BASE}/login", params={"service": service}, allow_redirects=False, timeout=self.timeout)
        location = response.headers.get("location", "")
        if self._is_sid_login_url(urllib.parse.urljoin(response.url, location)):
            self._login_entry = urllib.parse.urljoin(response.url, location)
            raise _SIDRedirect()
        raw = self._cookie_value("COOKIE_INFO")
        if not raw:
            raise LoginError("统一身份认证未下发 COOKIE_INFO，无法获取 flowKey")
        try:
            info = json.loads(urllib.parse.unquote(raw))
            flow_key = info["data"]["flowKey"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LoginError(f"解析 COOKIE_INFO 失败: {exc}") from exc
        return flow_key, info

    def _fetch_public_key(self):
        response = self.session.get(f"{self.CAS_BASE}/api/reset/rules", timeout=self.timeout)
        try:
            public_key = response.json()["data"]["encrypt"]["publicKey"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LoginError(f"获取 SM2 公钥失败: {exc}") from exc
        self.public_key = public_key
        return public_key

    def _query_login_info(self, flow_key):
        try:
            response = self.session.post(f"{self.CAS_BASE}/info-query", json={"username": "", "flowKey": flow_key}, headers={"Content-Type": "application/json", "Origin": self.PORTAL_BASE}, timeout=self.timeout)
            return response.json().get("data") or {}
        except Exception:
            return {}

    def _encrypt_password(self, password, public_key):
        return _sm2_encrypt(self._to_half_width(password).encode("utf-8"), public_key)

    def _submit_login(self, username, cipher, flow_key):
        referer = urllib.parse.quote(self._resolved_service or "", safe="")
        response = self.session.post(f"{self.CAS_BASE}/username-password/login", json={"username": username, "password": cipher, "flowKey": flow_key}, headers={"Content-Type": "application/json", "Origin": self.PORTAL_BASE, "Referer": f"{self.PORTAL_BASE}/?service={referer}"}, timeout=self.timeout)
        try:
            return response.json()
        except ValueError as exc:
            raise LoginError(f"登录响应不是合法 JSON（HTTP {response.status_code}）") from exc

    @staticmethod
    def _expected_service_host(redirect_url):
        parsed = urllib.parse.urlparse(redirect_url)
        inner = urllib.parse.parse_qs(parsed.query).get("service", [None])[0]
        return urllib.parse.urlparse(inner).netloc if inner and urllib.parse.urlparse(inner).netloc else parsed.netloc

    @staticmethod
    def _ticket_rejected(response, redirect_url):
        expected = BUCTAuth._expected_service_host(redirect_url)
        final_url = getattr(response, "url", "")
        final_host = urllib.parse.urlparse(final_url).netloc
        if expected and final_host and final_host != expected:
            return True
        if "/cas/login" in final_url:
            return True
        head = getattr(response, "content", b"")[:8192]
        for encoding in ("gbk", "utf-8"):
            try:
                text = head.decode(encoding)
            except UnicodeDecodeError:
                continue
            if "错误！" in text or "错误!" in text:
                return True
        return False

    def _follow_service_ticket(self, payload):
        data = payload.get("data") or {}
        redirect = data.get("service") if isinstance(data, dict) else None
        if isinstance(redirect, dict):
            redirect = json.dumps(redirect, ensure_ascii=False, separators=(",", ":"))
        if not isinstance(redirect, str) or not redirect:
            raise LoginError("统一身份认证返回成功，但响应中没有可回跳的 service 地址")
        target = urllib.parse.urljoin(self.PORTAL_BASE, redirect)
        response = self.session.get(target, timeout=self.timeout)
        if self._ticket_rejected(response, target):
            raise LoginError("统一身份认证已通过，但课程平台票据校验失败（ticket 无效或 MEOL 会话不匹配）")
        return response

    @staticmethod
    def _is_sid_login_url(raw_url):
        parsed = urllib.parse.urlparse(raw_url)
        return parsed.scheme == "https" and parsed.netloc == "sidportal.buct.edu.cn" and parsed.path == "/login" and not parsed.username

    def _check_sid_captcha(self, username, referer):
        key = secrets.token_hex(16)
        encoded = base64.b64encode(key.encode()).decode()
        value = encoded[: len(encoded) // 2] + encoded + encoded[len(encoded) // 2 :]
        response = self.session.get(f"{self.SID_PORTAL_BASE}/api/protected/user/findCaptchaCount/{urllib.parse.quote(username, safe='')}", headers={"Csrf-Key": key, "Csrf-Value": hashlib.md5(value.encode()).hexdigest(), "Referer": referer}, allow_redirects=False, timeout=self.timeout)
        if response.status_code != HTTPStatus.OK:
            raise LoginError(f"无法检查验证码要求（HTTP {response.status_code}）")
        try:
            payload = response.json()
            invisible = payload["data"]["captchaInvisible"]
            if payload.get("code") != 200 or invisible is None:
                raise ValueError
        except (ValueError, KeyError, TypeError) as exc:
            raise LoginError("无法确认验证码要求，请在浏览器检查登录页") from exc
        if invisible:
            raise _sid_error("1320007")

    def _parse_sid_page(self, content):
        soup = BeautifulSoup(content, "html.parser")
        text = lambda ident: (soup.find(id=ident).get_text(strip=True) if soup.find(id=ident) else "")
        return {"execution": text("login-page-flowkey"), "key": text("login-croypto"), "vendor": text("recaptchaVendor"), "risk": text("riskSystemSwitch"), "rule": text("login-rule-type"), "second": text("sso-second"), "error": text("login-error-msg") or text("login-error-code"), "captcha": text("captcha-url")}

    def _login_sid(self, username, password, entry):
        if not self._is_sid_login_url(entry):
            raise LoginError("新版认证入口不受信任")
        service = urllib.parse.urlparse(self._resolved_service)
        if service.scheme != "https" or not service.netloc or service.username:
            raise LoginError("新版认证要求有效的 HTTPS service")
        response = self.session.get(entry, headers={"Accept": "text/html,application/xhtml+xml", "X-Requested-With": None}, timeout=self.timeout)
        if response.status_code != HTTPStatus.OK or not self._is_sid_login_url(response.url):
            raise LoginError("认证入口发生非预期跳转")
        page = self._parse_sid_page(response.content[:_MAX_PAGE_BYTES])
        if page["error"]:
            raise _sid_error(page["error"])
        if not page["execution"] or not page["key"]:
            raise LoginError("新版认证页面缺少 execution 或 croypto")
        if ((page["vendor"] and page["vendor"] != "system") or (page["risk"] and page["risk"] != "default") or (page["rule"] and page["rule"] != "normal") or page["second"] or page["captcha"]):
            raise LoginError("当前认证需要验证码、风控或二次验证，请在浏览器完成")
        self._check_sid_captcha(username, entry)
        form = {"username": username, "type": "UsernamePassword", "_eventId": "submit", "geolocation": "", "execution": page["execution"], "captcha_code": "", "croypto": page["key"], "password": _aes_encrypt(page["key"], password), "captcha_payload": _aes_encrypt(page["key"], "{}")}
        response = self.session.post(f"{self.SID_PORTAL_BASE}/login", data=form, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/html,application/xhtml+xml", "Origin": self.SID_PORTAL_BASE, "Referer": entry, "X-Requested-With": None}, allow_redirects=True, timeout=self.timeout)
        result = self._parse_sid_page(response.content[:_MAX_PAGE_BYTES])
        if result["error"] or result["execution"] or result["key"] or response.url.startswith(self.SID_PORTAL_BASE) or self._ticket_rejected(response, self._resolved_service):
            raise LoginError("认证未完成或业务系统票据未被接受，请检查验证码或二次验证")
        self._is_logged_in = True
        self._active_sid = True

    def login(self, username, password):
        self.session.close()
        self.session = self._new_session()
        self._is_logged_in = False
        self.flow_key = None
        self.public_key = None
        self._resolved_service = None
        self._login_entry = None
        self._active_sid = False
        if not username or not password:
            raise LoginError("用户名或密码为空")
        try:
            service = self._resolve_service()
            self._resolved_service = service
            entry = self._login_url_override or self._login_entry
            if entry and self._is_sid_login_url(entry):
                self._login_sid(username, password, entry)
                return True
            for attempt in range(2):
                try:
                    flow_key, _ = self._fetch_flow_key(service)
                except _SIDRedirect:
                    self._login_sid(username, password, self._login_entry)
                    return True
                self.flow_key = flow_key
                cipher = self._encrypt_password(password, self._fetch_public_key())
                self._query_login_info(flow_key)
                payload = self._submit_login(username, cipher, flow_key)
                code = payload.get("code")
                if code == _SUCCESS_CODE:
                    self._follow_service_ticket(payload)
                    self._is_logged_in = True
                    return True
                if code in _FLOW_KEY_EXPIRED_CODES and attempt == 0:
                    continue
                raise LoginError(_ERROR_MESSAGES.get(code) or payload.get("msg") or f"登录失败（code={code}）")
            raise LoginError("登录失败：flowKey 多次失效")
        except requests.exceptions.Timeout as exc:
            raise NetworkError("登录请求超时") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError("网络连接错误") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"网络请求错误: {exc}") from exc

    def get_session(self):
        if not self._is_logged_in:
            raise LoginError("请先调用login方法进行登录")
        return self.session

    def is_logged_in(self):
        return self._is_logged_in

    def logout(self):
        try:
            logout_url = f"{self.SID_PORTAL_BASE}/logout" if self._active_sid else f"{self.CAS_BASE}/logout"
            self.session.get(logout_url, timeout=self.timeout)
        except Exception:
            pass
        finally:
            self.session.close()
            self.session = self._new_session()
            self._is_logged_in = False
            self.flow_key = None
            self.public_key = None
            self._resolved_service = None
            self._login_entry = None
            self._active_sid = False

    def set_base_url(self, base_url):
        self.base_url = base_url.rstrip("/")


class _SIDRedirect(Exception):
    """内部控制流：旧 CAS 入口把登录转发到 sidportal。"""
