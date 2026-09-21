"""SM2 兼容性回归测试。

向量来源：在 portal.buct.edu.cn 页面上调用站点自身的 ``sm2.keyPair()`` /
``sm2.encrypt()`` / ``sm2.decrypt()`` 生成，用于锁定线格式，防止实现漂移。

运行：
    python test/test_sm2_compat.py
"""

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import sm2_crypto  # noqa: E402

# --- 由站点 JS 生成的密钥对与密文（一次性向量，仅用于格式锁定） ---
SITE_PRIVATE_KEY_B64 = "ZSzGiEb9WSRzJND0L+yYUGUKvT61TriS1Uwsacozsuo="
SITE_PUBLIC_KEY_B64 = (
    "BLHjNaPKrcmyY72zWdLNXmX6oLzmWbRGUk5O1nr6412xlJQp1xLmmQ1rXd52uVhg6loDIno6l0zYa9nSt82htVg="
)
SITE_CIPHERTEXT_B64 = (
    "HUcEBhzgQ3tJalHE4TxQMssM0eb2cIwEet+Jq2xFDNBu7xPcJP70j6ipMIV7XTn/yvJrkDSFBazLdNHhvFSGe7kgtzybwvlK3biWQDDArT3VHc2suJ91SqKMGaffJCBlT9sCbw0Lbq9PX2zgfcom0lraSko="
)
SITE_PLAINTEXT = "SM2-Vector-Test-1234"


def test_sm3_standard_vectors():
    """SM3 必须匹配 GM/T 0004-2012 标准向量。"""
    assert (
        sm2_crypto.sm3(b"abc").hex()
        == "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0"
    )
    assert (
        sm2_crypto.sm3(b"abcd" * 16).hex()
        == "debe9ff92275b8a138604889c18e5a4d6fdb70e5387e5765293dcba39c0c5732"
    )
    print("PASS  SM3 标准向量")


def test_decrypt_site_ciphertext():
    """站点 JS 生成的密文必须能被本模块解出原文（同时校验 C3）。"""
    private_hex = base64.b64decode(SITE_PRIVATE_KEY_B64).hex()
    plaintext = sm2_crypto.decrypt(SITE_CIPHERTEXT_B64, private_hex)
    assert plaintext.decode("utf-8") == SITE_PLAINTEXT, plaintext
    print("PASS  解密站点密文 ->", plaintext.decode())


def test_wire_format():
    """密文线格式：base64(C1.x||C1.y||C3||C2)，C1 为 64 字节且不带 04 前缀。"""
    for plaintext in ("A", "SamplePassword123", "x" * 40, "密码口令测试"):
        raw = plaintext.encode("utf-8")
        cipher = sm2_crypto.encrypt(raw, SITE_PUBLIC_KEY_B64)
        decoded = base64.b64decode(cipher)
        assert len(decoded) == 64 + 32 + len(raw), (len(decoded), len(raw))
        assert decoded[0] != 0x04 or len(raw) == 0, "C1 不应带 04 未压缩点标志"
    print("PASS  密文线格式（64 + 32 + len(M)，C1 无 04 前缀）")


def test_round_trip():
    """自洽往返：加密后能被对应私钥解回。"""
    private_hex = base64.b64decode(SITE_PRIVATE_KEY_B64).hex()
    for plaintext in ("round-trip-check", "全角转半角ＡＢＣ", "123456"):
        cipher = sm2_crypto.encrypt(plaintext.encode("utf-8"), SITE_PUBLIC_KEY_B64)
        assert sm2_crypto.decrypt(cipher, private_hex).decode("utf-8") == plaintext
    print("PASS  加解密往返")


def test_c3_rejects_wrong_key():
    """C3 校验必须能识别出错误的私钥。"""
    other_private = "01".zfill(64)
    try:
        sm2_crypto.decrypt(SITE_CIPHERTEXT_B64, other_private)
    except ValueError:
        print("PASS  C3 校验拒绝错误私钥")
        return
    raise AssertionError("C3 校验未生效")


def main():
    test_sm3_standard_vectors()
    test_decrypt_site_ciphertext()
    test_wire_format()
    test_round_trip()
    test_c3_rejects_wrong_key()
    print("\n全部通过")


if __name__ == "__main__":
    main()
