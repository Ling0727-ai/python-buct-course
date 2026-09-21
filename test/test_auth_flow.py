"""认证流程离线单元测试（不发任何网络请求）。

覆盖无法用真实口令验证的分支：成功、flowKey 一次性失效重试、口令错误、
MFA、锁定，以及"旧 MEOL 接口保留但不被 login() 触发"。

运行：
    python test/test_auth_flow.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.auth import BUCTAuth  # noqa: E402
from buct_course.exceptions import LoginError  # noqa: E402

FAKE_PUBLIC_KEY = (
    "BMz9oCZtEVaFTYC8X8maUe3Vdo/Ju4gQnW5j9JGHccp016ylLUl9hLOFu3N8xt3+w5Cz5C3C28/lE+8oU16x8TQ="
)


class StubAuth(BUCTAuth):
    """把所有网络动作替换成脚本化响应。"""

    def __init__(self, login_responses, **kwargs):
        super().__init__(**kwargs)
        self._login_responses = list(login_responses)
        self.flow_key_calls = 0
        self.submitted = []
        self.followed = []

    def _resolve_service(self):
        return (
            "https://course.buct.edu.cn/meol/homepage/common/sso_login.jsp"
            ";jsessionid=STUB.TM1"
        )

    def _fetch_flow_key(self, service):
        self.flow_key_calls += 1
        return f"flow.{self.flow_key_calls:064x}", {"code": 600901}

    def _fetch_public_key(self):
        return FAKE_PUBLIC_KEY

    def _query_login_info(self, flow_key):
        return {}

    def _encrypt_password(self, password, public_key):
        assert public_key == FAKE_PUBLIC_KEY
        return "STUB_CIPHER_BASE64"

    def _submit_login(self, username, cipher, flow_key):
        self.submitted.append((username, cipher, flow_key))
        return self._login_responses.pop(0)

    def _follow_service_ticket(self, payload):
        self.followed.append(payload)
        return None


class FakeResponse:
    """最小响应替身，只暴露 _ticket_rejected 用到的字段。"""

    def __init__(self, url, content=b""):
        self.url = url
        self.content = content


class FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, url, timeout=None):  # noqa: ARG002
        return self._response


def test_ticket_rejected_variants():
    """票据回跳的四种形态（拒绝形态由线上实测采集）。"""
    auth = BUCTAuth()

    # 1) 无 ticket：302 弹回 CAS 登录页
    auth.session = FakeSession(
        FakeResponse("https://portal.buct.edu.cn/cas/login?service=https%3A%2F%2Fcourse")
    )
    try:
        auth._follow_service_ticket({"data": {"service": "https://course.buct.edu.cn/x"}})
    except LoginError as exc:
        assert "票据校验失败" in str(exc), exc
    else:
        raise AssertionError("弹回 CAS 登录页时应抛 LoginError")

    # 2) ticket 无效：200 + GBK 错误页
    body = "<HTML><HEAD><TITLE>错误！</TITLE></HEAD></HTML>".encode("gbk")
    auth.session = FakeSession(
        FakeResponse(
            "https://course.buct.edu.cn/meol/homepage/common/sso_login.jsp", body
        )
    )
    try:
        auth._follow_service_ticket({"data": {"service": "https://course.buct.edu.cn/x"}})
    except LoginError as exc:
        assert "票据校验失败" in str(exc), exc
    else:
        raise AssertionError("MEOL 错误页时应抛 LoginError")

    # 3) 正常页面：放行
    auth.session = FakeSession(
        FakeResponse("https://course.buct.edu.cn/meol/index.do", b"<html>ok</html>")
    )
    resp = auth._follow_service_ticket({"data": {"service": "https://course.buct.edu.cn/x"}})
    assert resp is not None

    # 4) 成功码却没有回跳地址：不能静默通过
    auth.session = FakeSession(FakeResponse("https://course.buct.edu.cn/meol/index.do"))
    try:
        auth._follow_service_ticket({"data": {}})
    except LoginError as exc:
        assert "service" in str(exc), exc
    else:
        raise AssertionError("缺少 service 地址时应抛 LoginError")

    print("PASS  票据回跳校验：弹回CAS / MEOL错误页 / 正常页 / 缺service")


class RecordingSession:
    """记录实际请求的 URL，用于验证相对路径是否被补全。"""

    def __init__(self, response):
        self._response = response
        self.requested = []

    def get(self, url, timeout=None):  # noqa: ARG002
        self.requested.append(url)
        return self._response


def test_relative_service_url_is_resolved():
    """线上实测：成功时 data.service 是相对路径 ``/cas/login?service=...``。

    回归 bug：直接把相对路径交给 requests 会抛
    ``Invalid URL ... No scheme supplied``。
    """
    auth = BUCTAuth()
    inner = (
        "https%3A%2F%2Fcourse.buct.edu.cn%2Fmeol%2Fhomepage%2Fcommon"
        "%2Fsso_login.jsp%3Bjsessionid%3DABC.TM1"
    )
    sess = RecordingSession(
        FakeResponse("https://course.buct.edu.cn/meol/index.do", b"<html>ok</html>")
    )
    auth.session = sess
    auth._follow_service_ticket({"data": {"service": f"/cas/login?service={inner}"}})
    assert sess.requested[0] == (
        f"https://portal.buct.edu.cn/cas/login?service={inner}"
    ), sess.requested
    # 业务 host 必须从 service 参数推断，而不是回跳地址自身的 host
    assert BUCTAuth._expected_service_host(sess.requested[0]) == "course.buct.edu.cn"
    # 成功回跳应判定为「未被拒绝」
    assert BUCTAuth._ticket_rejected(sess._response, sess.requested[0]) is False

    # 绝对地址应原样透传
    sess2 = RecordingSession(FakeResponse("https://course.buct.edu.cn/meol/index.do", b"ok"))
    auth.session = sess2
    auth._follow_service_ticket({"data": {"service": "https://course.buct.edu.cn/x?ticket=ST-1"}})
    assert sess2.requested[0] == "https://course.buct.edu.cn/x?ticket=ST-1"
    print("PASS  相对 service 路径补全 + 业务 host 推断（线上实测形态）")


def test_old_interface_fully_replaced():
    """旧实现已彻底移除，且对外函数名与旧版保持一致。"""
    import inspect

    # 1) 旧的直连 MEOL 实现不应再存在
    assert not hasattr(BUCTAuth, "_legacy_meol_login"), "旧 MEOL 实现应已移除"

    # 2) 旧版公开接口必须原样保留
    for name in ("login", "get_session", "is_logged_in", "logout", "set_base_url"):
        assert hasattr(BUCTAuth, name), f"公开接口 {name} 丢失"

    # 3) login(username, password) 签名兼容，且额外参数都有默认值
    params = list(inspect.signature(BUCTAuth.login).parameters)
    assert params == ["self", "username", "password"], params
    init_params = inspect.signature(BUCTAuth.__init__).parameters
    assert all(
        p.default is not inspect.Parameter.empty
        for n, p in init_params.items()
        if n != "self"
    ), "新增参数必须带默认值，保证 BUCTAuth() 仍可无参构造"
    BUCTAuth()

    # 4) 源码里不应再残留旧实现的**代码**痕迹
    #    （docstring 里提到 loginCheck.do 属于历史说明，允许保留）
    import buct_course.auth as auth_module

    source = inspect.getsource(auth_module)
    for marker in (
        "IPT_LOGINUSERNAME",
        "IPT_LOGINPASSWORD",
        "def _legacy_meol_login",
        "meol/login.do",
        "import time",
    ):
        assert marker not in source, f"源码仍残留旧实现痕迹: {marker}"

    print("PASS  旧实现彻底移除 + 旧版公开函数名完整保留")


def test_success():
    auth = StubAuth([{"code": 666666, "data": {"service": "https://course.buct.edu.cn/x?ticket=ST-1"}}])
    assert auth.login("2024030178", "pw") is True
    assert auth.is_logged_in() is True
    assert auth.get_session() is auth.session
    assert len(auth.submitted) == 1
    assert auth.submitted[0][0] == "2024030178"
    assert auth.submitted[0][1] == "STUB_CIPHER_BASE64"
    assert auth.submitted[0][2].startswith("flow.")
    assert len(auth.followed) == 1, "成功后必须跟随 service ticket 回跳"
    print("PASS  成功路径：code 666666 -> 已登录 + 跟随 ticket")


def test_flow_key_expired_retries():
    auth = StubAuth([
        {"code": 180076, "msg": "flowKey不能再次使用"},
        {"code": 666666, "data": {"service": "https://course.buct.edu.cn/x?ticket=ST-2"}},
    ])
    assert auth.login("2024030178", "pw") is True
    assert auth.flow_key_calls == 2, "flowKey 失效后应重新获取一次"
    assert len(auth.submitted) == 2
    print("PASS  flowKey 一次性失效 -> 自动换新重试成功")


def test_flow_key_expired_twice():
    auth = StubAuth([
        {"code": 180046, "msg": "FlowKey没找到"},
        {"code": 180076, "msg": "flowKey不能再次使用"},
    ])
    try:
        auth.login("2024030178", "pw")
    except LoginError as exc:
        assert "flowKey" in str(exc), exc
        assert auth.is_logged_in() is False
        print("PASS  flowKey 连续失效 -> 明确报错，不误报成功")
        return
    raise AssertionError("应当抛出 LoginError")


def test_wrong_password():
    auth = StubAuth([{"code": 170002, "msg": "用户名或密码错误"}])
    try:
        auth.login("2024030178", "wrong")
    except LoginError as exc:
        assert str(exc) == "用户名或密码错误", exc
        assert auth.flow_key_calls == 1, "口令错误不应重试"
        print("PASS  口令错误 -> 可读报错，且不重试")
        return
    raise AssertionError("应当抛出 LoginError")


def test_mfa_required():
    auth = StubAuth([{"code": 160001, "msg": "需要MFA验证"}])
    try:
        auth.login("2024030178", "pw")
    except LoginError as exc:
        assert "MFA" in str(exc), exc
        print("PASS  需要 MFA -> 明确提示而非静默失败")
        return
    raise AssertionError("应当抛出 LoginError")


def test_account_locked():
    auth = StubAuth([{"code": 180028, "msg": "账号登录失败次数过多"}])
    try:
        auth.login("2024030178", "pw")
    except LoginError as exc:
        assert "锁定" in str(exc), exc
        print("PASS  账号锁定 -> 明确提示")
        return
    raise AssertionError("应当抛出 LoginError")


def test_get_session_before_login():
    auth = StubAuth([])
    try:
        auth.get_session()
    except LoginError as exc:
        assert "请先调用login" in str(exc), exc
        print("PASS  未登录调用 get_session -> 抛 LoginError")
        return
    raise AssertionError("应当抛出 LoginError")


def test_to_half_width():
    """与站点 toHalfWidth 逐例对照（向量由 portal.buct.edu.cn 页面实跑采集）。

    注意 ``｟``(U+FF5F) / ``｠``(U+FF60) 落在站点正则 ``[\\uff01-\\uff5e]`` 之外，
    必须保持不变——这是最容易写错的一个边界。
    """
    cases = {
        "ＡＢＣ１２３": "ABC123",
        "ａｂｃ": "abc",
        "ｐ＠ｓｓｗｏｒｄ！": "p@ssword!",
        "全角　空格": "全角 空格",
        "ASCII123": "ASCII123",
        "～！＠＃＄％": "~!@#$%",
        "｟｠｛｝": "｟｠{}",
        "　": " ",
        "混合ＡＢc１２３！@#": "混合ABc123!@#",
        "ＮｏＦｕｌｌＷｉｄｔｈ": "NoFullWidth",
    }
    for src, want in cases.items():
        got = BUCTAuth._to_half_width(src)
        assert got == want, (src, got, want)
    print(f"PASS  全角转半角（{len(cases)} 例与站点 toHalfWidth 完全一致）")


def test_password_is_half_width_converted_before_encrypt():
    captured = {}

    class CaptureAuth(StubAuth):
        def _encrypt_password(self, password, public_key):
            captured["raw"] = password
            return super()._encrypt_password(password, public_key)

    auth = CaptureAuth([{"code": 666666, "data": {"service": "x"}}])
    auth.login("2024030178", "ＰＡＳＳ１２３")
    # _encrypt_password 收到的是原始串，转换发生在真实实现内部
    assert captured["raw"] == "ＰＡＳＳ１２３"
    # 真实实现的转换行为
    from buct_course import sm2_crypto

    normalized = BUCTAuth._to_half_width(captured["raw"])
    assert normalized == "PASS123"
    cipher = sm2_crypto.encrypt(normalized.encode("utf-8"), FAKE_PUBLIC_KEY)
    import base64

    assert len(base64.b64decode(cipher)) == 96 + len("PASS123")
    print("PASS  口令先全角转半角再 SM2 加密")


def main():
    test_old_interface_fully_replaced()
    test_success()
    test_ticket_rejected_variants()
    test_relative_service_url_is_resolved()
    test_flow_key_expired_retries()
    test_flow_key_expired_twice()
    test_wrong_password()
    test_mfa_required()
    test_account_locked()
    test_get_session_before_login()
    test_to_half_width()
    test_password_is_half_width_converted_before_encrypt()
    print("\n全部通过（离线，无网络请求）")


if __name__ == "__main__":
    main()
