"""真实登录验证脚本 —— 需要你提供明文口令。

口令优先从环境变量读取，避免进入 shell 历史；未设置时交互式输入（不回显）。

    set BUCT_USER=2024030178
    set BUCT_PASS=你的密码
    .venv\\Scripts\\python.exe test\\verify_login_live.py

成功时打印 code 666666 的登录态与 MEOL 会话 cookie。
"""

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import BUCTAuth  # noqa: E402
from buct_course.exceptions import LoginError, NetworkError  # noqa: E402


def main():
    username = os.environ.get("BUCT_USER") or input("学号: ").strip()
    password = os.environ.get("BUCT_PASS") or getpass.getpass("密码（不回显）: ")

    auth = BUCTAuth()
    print(f"\n学号: {username}")
    print("正在走统一身份认证流程 ...")

    try:
        ok = auth.login(username, password)
    except LoginError as exc:
        print(f"\n[失败] LoginError: {exc}")
        return 1
    except NetworkError as exc:
        print(f"\n[失败] NetworkError: {exc}")
        return 1

    print(f"\n[成功] login() -> {ok}")
    print(f"       flowKey : {auth.flow_key}")
    print(f"       公钥前缀: {(auth.public_key or '')[:32]}...")
    print("       会话 cookie:")
    for cookie in auth.session.cookies:
        print(f"         - {cookie.name}  domain={cookie.domain}  path={cookie.path}")

    session = auth.get_session()
    resp = session.get("https://course.buct.edu.cn/meol/index.do", timeout=15)
    print(f"\n       MEOL index.do -> HTTP {resp.status_code}, {len(resp.content)} bytes")
    print("       （页面含登录态即说明 ticket 回跳成功）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
