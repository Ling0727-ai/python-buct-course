"""
北化课程平台认证模块

登录流程（2026-09 起，统一身份认证）
-----------------------------------
课程平台 MEOL 已关闭旧的直连登录接口（``/meol/loginCheck.do`` 现返回 404），
改为统一身份认证。现在必须走 portal.buct.edu.cn 的 CAS：

1. ``GET  course.buct.edu.cn/meol/homepage/common/sso_login.jsp``
   拿到本次登录的 ``service``（形如
   ``https://course.buct.edu.cn/meol/homepage/common/sso_login.jsp;jsessionid=<MEOL会话>``）
2. ``GET  portal.buct.edu.cn/cas/login?service=<service>``
   服务端下发 ``COOKIE_INFO`` cookie，其中 ``data.flowKey`` 就是登录要用的 ``flowKey``
3. ``GET  portal.buct.edu.cn/cas/api/reset/rules``
   拿到 ``data.encrypt.publicKey``（algorithm = sm2，65 字节未压缩点）
4. 用 SM2 加密口令（见 ``sm2_crypto``），口令先做全角转半角
5. ``POST portal.buct.edu.cn/cas/username-password/login``
   body: ``{"username": ..., "password": <sm2 base64>, "flowKey": ...}``
6. 成功后 ``data.service`` 是带 ticket 的回跳地址，跟随它即可建立 MEOL 会话

要点
----
* ``flowKey`` 由服务端下发、且**一次性**（重复使用报 180076），因此每次登录都要重新获取。
* ``password`` 是 SM2 密文：``base64(C1.x||C1.y||C3||C2)``，C1 为 64 字节不带 04 前缀。
* 该实现**不需要**执行站点 JS，纯 Python 算法复现。

对外接口与旧版保持一致：``login`` / ``get_session`` / ``is_logged_in`` /
``logout`` / ``set_base_url``。旧的直连 MEOL 实现（``/meol/loginCheck.do``）
已彻底移除——该接口现已返回 404。
"""

import json
import urllib.parse

import requests

from .exceptions import LoginError, NetworkError
from .sm2_crypto import encrypt as _sm2_encrypt

# 统一身份认证返回码 -> 可读信息
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

# flowKey 失效时值得换一个重试
_FLOW_KEY_EXPIRED_CODES = {180046, 180076}

_SUCCESS_CODE = 666666


class BUCTAuth:
    """北化课程平台认证类（统一身份认证版）"""

    PORTAL_BASE = "https://portal.buct.edu.cn"
    CAS_BASE = "https://portal.buct.edu.cn/cas"
    COURSE_BASE = "https://course.buct.edu.cn"
    MEOL_SSO_ENTRY = "https://course.buct.edu.cn/meol/homepage/common/sso_login.jsp"

    #: 不指定 service 时，直接登录门户（i北化）所用的服务地址
    DEFAULT_PORTAL_SERVICE = "http://i.buct.edu.cn"

    def __init__(self, service=None, timeout=15):
        """
        Args:
            service: 指定 CAS 的 service 参数。默认 ``None`` 表示走课程平台
                MEOL 的 SSO 入口（也就是本库真正需要的登录态）。
                传 ``BUCTAuth.DEFAULT_PORTAL_SERVICE`` 或任意 URL 可直接登录该服务。
            timeout: 单次请求超时（秒）。
        """
        self.base_url = self.COURSE_BASE
        self.timeout = timeout
        self.service = service
        self._is_logged_in = False
        self.flow_key = None
        self.public_key = None
        self._resolved_service = None
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        )
        self.session = self._new_session()

    def _new_session(self):
        """创建带统一请求头的会话（登录/登出都会重建，避免旧 cookie 干扰）。"""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self._user_agent,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        return session

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _cookie_value(self, name):
        """安全读取 cookie（同名多域时 ``cookies.get`` 会抛 CookieConflictError）。"""
        for cookie in self.session.cookies:
            if cookie.name == name:
                return cookie.value
        return None

    @staticmethod
    def _to_half_width(text):
        """全角转半角，对齐前端 ``toHalfWidth``（fullToHalf = true）。"""
        out = []
        for ch in text:
            code = ord(ch)
            if 0xFF01 <= code <= 0xFF5E:
                out.append(chr(code - 0xFEE0))
            elif code == 0x3000:
                out.append(" ")
            else:
                out.append(ch)
        return "".join(out)

    def _resolve_service(self):
        """确定本次登录的 service 参数。"""
        if self.service:
            return self.service
        response = self.session.get(
            self.MEOL_SSO_ENTRY, allow_redirects=False, timeout=self.timeout
        )
        location = response.headers.get("location")
        if not location:
            raise LoginError(
                f"无法从课程平台 SSO 入口获取 service（HTTP {response.status_code}）"
            )
        service = urllib.parse.parse_qs(urllib.parse.urlparse(location).query).get(
            "service", [None]
        )[0]
        if not service:
            raise LoginError("SSO 入口未返回 service 参数")
        return service

    def _fetch_flow_key(self, service):
        """从 CAS 下发的 COOKIE_INFO 中取出一次性 flowKey。"""
        self.session.get(
            f"{self.CAS_BASE}/login",
            params={"service": service},
            allow_redirects=False,
            timeout=self.timeout,
        )
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
        """获取 SM2 加密公钥（base64）。"""
        response = self.session.get(
            f"{self.CAS_BASE}/api/reset/rules", timeout=self.timeout
        )
        try:
            payload = response.json()
            encrypt_info = payload["data"]["encrypt"]
            public_key = encrypt_info["publicKey"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LoginError(f"获取 SM2 公钥失败: {exc}") from exc
        self.public_key = public_key
        return public_key

    def _query_login_info(self, flow_key):
        """登录前查询 MFA / 验证码要求（失败不影响主流程）。"""
        try:
            response = self.session.post(
                f"{self.CAS_BASE}/info-query",
                json={"username": "", "flowKey": flow_key},
                headers={"Content-Type": "application/json", "Origin": self.PORTAL_BASE},
                timeout=self.timeout,
            )
            return response.json().get("data") or {}
        except Exception:
            return {}

    def _encrypt_password(self, password, public_key):
        """SM2 加密口令，返回 base64 密文。"""
        normalized = self._to_half_width(password)
        return _sm2_encrypt(normalized.encode("utf-8"), public_key)

    def _submit_login(self, username, cipher, flow_key):
        """提交用户名口令登录，返回服务端 JSON。"""
        referer_service = urllib.parse.quote(self._resolved_service or "", safe="")
        response = self.session.post(
            f"{self.CAS_BASE}/username-password/login",
            json={"username": username, "password": cipher, "flowKey": flow_key},
            headers={
                "Content-Type": "application/json",
                "Origin": self.PORTAL_BASE,
                "Referer": f"{self.PORTAL_BASE}/?service={referer_service}",
            },
            timeout=self.timeout,
        )
        try:
            return response.json()
        except ValueError as exc:
            raise LoginError(f"登录响应不是合法 JSON（HTTP {response.status_code}）") from exc

    @staticmethod
    def _expected_service_host(redirect_url):
        """从 CAS 回跳地址推断最终应落地的业务系统 host。

        CAS 的回跳地址形如 ``/cas/login?service=<业务URL>``——真正的目标
        host 藏在 ``service`` 参数里；若回跳地址本身就是业务地址，则用它自己的 host。
        """
        query = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query)
        inner = query.get("service", [None])[0]
        if inner:
            host = urllib.parse.urlparse(inner).netloc
            if host:
                return host
        return urllib.parse.urlparse(redirect_url).netloc

    @staticmethod
    def _ticket_rejected(response, redirect_url):
        """判断回跳后票据是否未被接受。

        实测三种形态（均线上采集）：

        * 无 ticket：跟随重定向后停在**门户**登录页
          ``https://portal.buct.edu.cn?timestamp=...&service=...``
          ——最终 host 不等于业务系统 host；
        * ticket 无效：200 + GBK 错误页，``<TITLE>错误！</TITLE>``；
        * 正常：最终落在课程平台 ``course.buct.edu.cn/meol/...``。

        注意两个坑：不能只匹配 ``/cas/login``（无 ticket 时最终 URL 不含该路径），
        也不能拿「回跳地址自身」的 host 去比（成功回跳的第一跳就在门户域上，
        业务 host 必须从 ``service`` 参数里取）。
        """
        expected_host = BUCTAuth._expected_service_host(redirect_url)
        final_host = urllib.parse.urlparse(response.url).netloc
        if expected_host and final_host and final_host != expected_host:
            return True
        if "/cas/login" in response.url:
            return True
        head = response.content[:8192]
        for encoding in ("gbk", "utf-8"):
            try:
                text = head.decode(encoding)
            except UnicodeDecodeError:
                continue
            if "错误！" in text or "错误!" in text:
                return True
        return False

    def _follow_service_ticket(self, payload):
        """跟随 CAS 回跳地址，建立业务系统（MEOL）会话。

        Returns:
            requests.Response: 回跳后的最终响应

        Raises:
            LoginError: 成功码却没有回跳地址，或票据被课程平台拒绝
        """
        data = payload.get("data") or {}
        redirect = data.get("service") if isinstance(data, dict) else None
        if isinstance(redirect, dict):
            redirect = json.dumps(redirect)
        if not isinstance(redirect, str) or not redirect:
            raise LoginError("统一身份认证返回成功，但响应中没有可回跳的 service 地址")

        # 实测成功时 data.service 是**相对路径**（如 "/cas/login?service=..."）：
        # 浏览器按当前页自动解析，requests 不会，必须显式补全，
        # 否则报 "Invalid URL ... No scheme supplied"。
        target = urllib.parse.urljoin(self.PORTAL_BASE, redirect)
        response = self.session.get(target, timeout=self.timeout)
        if self._ticket_rejected(response, target):
            raise LoginError(
                "统一身份认证已通过，但课程平台票据校验失败"
                "（ticket 无效或 MEOL 会话不匹配）"
            )
        return response

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def login(self, username, password):
        """
        登录北化统一身份认证，并建立课程平台会话。

        Args:
            username: 学号
            password: 密码（明文，内部会做 SM2 加密）

        Returns:
            bool: 登录是否成功

        Raises:
            LoginError: 账号密码错误、需要 MFA/验证码、账号锁定等
            NetworkError: 网络错误
        """
        self.session = self._new_session()
        self._is_logged_in = False
        self.flow_key = None
        self._resolved_service = None

        try:
            service = self._resolve_service()
            self._resolved_service = service
            # flowKey 一次性；若中途失效则整体重取一次
            for attempt in range(2):
                flow_key, _ = self._fetch_flow_key(service)
                self.flow_key = flow_key
                public_key = self._fetch_public_key()
                self._query_login_info(flow_key)

                cipher = self._encrypt_password(password, public_key)
                payload = self._submit_login(username, cipher, flow_key)
                code = payload.get("code")

                if code == _SUCCESS_CODE:
                    self._follow_service_ticket(payload)
                    self._is_logged_in = True
                    return True

                if code in _FLOW_KEY_EXPIRED_CODES and attempt == 0:
                    continue

                message = _ERROR_MESSAGES.get(code) or payload.get("msg") or f"登录失败（code={code}）"
                raise LoginError(message)

            raise LoginError("登录失败：flowKey 多次失效")

        except requests.exceptions.Timeout as exc:
            raise NetworkError("登录请求超时") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError("网络连接错误") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"网络请求错误: {exc}") from exc

    def get_session(self):
        """
        获取登录后的 session

        Returns:
            requests.Session: 认证后的会话对象

        Raises:
            LoginError: 如果未登录时调用
        """
        if not self._is_logged_in:
            raise LoginError("请先调用login方法进行登录")
        return self.session

    def is_logged_in(self):
        """检查是否已登录"""
        return self._is_logged_in

    def logout(self):
        """注销登录"""
        try:
            self.session.get(f"{self.CAS_BASE}/logout", timeout=self.timeout)
        except Exception:
            # 忽略注销接口的错误，继续清理本地session
            pass
        finally:
            self.session.close()
            self.session = self._new_session()
            self._is_logged_in = False
            self.flow_key = None
            self._resolved_service = None

    def set_base_url(self, base_url):
        """设置课程平台基础 URL（用于测试或其他环境）"""
        self.base_url = base_url.rstrip("/")
        self.MEOL_SSO_ENTRY = f"{self.base_url}/meol/homepage/common/sso_login.jsp"

