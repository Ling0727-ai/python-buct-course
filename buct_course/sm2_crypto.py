"""纯 Python SM2（GM/T 0003）实现，供北化统一认证登录加密口令使用。

本模块**不依赖任何第三方库**，也不需要在运行时执行站点 JS。

与 portal.buct.edu.cn 前端（`sm2.min.js` / gm-crypto）的互操作一致性，
由 `test/test_sm2_compat.py` 中捕获的真实向量双向校验：

* 站点 JS 生成的密文 → 本模块解密 → 原文一致
* 本模块生成的密文 → 站点 JS 解密 → 原文一致

线格式（与站点完全一致）::

    base64( C1.x || C1.y || C3 || C2 )     # C1 为 64 字节，**不带** 04 前缀

两点容易踩坑的细节（均已用实测向量确认）：

1. C1 是裸的 ``x1||y1``（64 字节），**不带** 未压缩点标志 ``04``。
2. KDF 的输入是 ``x2||y2`` 的**原始 64 字节**，不是它的十六进制字符串。
   （gmssl 源码里把十六进制字符串传进 ``sm3_kdf``，但该函数内部会先 ``fromhex``，
   容易被误读成"对十六进制文本做 KDF"。）
"""

from __future__ import annotations

import base64
import secrets

# --------------------------------------------------------------------------
# SM2 曲线参数（GM/T 0003.5-2012）
# --------------------------------------------------------------------------
_P = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
_A = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
_B = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
_N = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
_GX = 0x32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7
_GY = 0xBC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0

# --------------------------------------------------------------------------
# SM3 杂凑算法（GM/T 0004-2012）
# --------------------------------------------------------------------------
_SM3_IV = (
    0x7380166F,
    0x4914B2B9,
    0x172442D7,
    0xDA8A0600,
    0xA96F30BC,
    0x163138AA,
    0xE38DEE4D,
    0xB0FB0E4E,
)
_SM3_T = [0x79CC4519] * 16 + [0x7A879D8A] * 48
_MASK32 = 0xFFFFFFFF


def _rotl(value: int, shift: int) -> int:
    shift %= 32
    if shift == 0:
        return value & _MASK32
    return ((value << shift) | (value >> (32 - shift))) & _MASK32


def _sm3_p0(x: int) -> int:
    return x ^ _rotl(x, 9) ^ _rotl(x, 17)


def _sm3_p1(x: int) -> int:
    return x ^ _rotl(x, 15) ^ _rotl(x, 23)


def sm3(data: bytes) -> bytes:
    """计算 SM3 摘要，返回 32 字节。"""
    bit_length = len(data) * 8
    padded = bytearray(data)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0x00)
    padded += bit_length.to_bytes(8, "big")

    state = list(_SM3_IV)
    for offset in range(0, len(padded), 64):
        block = padded[offset : offset + 64]
        w = [int.from_bytes(block[i * 4 : i * 4 + 4], "big") for i in range(16)]
        for j in range(16, 68):
            w.append(
                _sm3_p1(w[j - 16] ^ w[j - 9] ^ _rotl(w[j - 3], 15))
                ^ _rotl(w[j - 13], 7)
                ^ w[j - 6]
            )
        w1 = [w[j] ^ w[j + 4] for j in range(64)]

        a, b, c, d, e, f, g, h = state
        for j in range(64):
            a12 = _rotl(a, 12)
            ss1 = _rotl((a12 + e + _rotl(_SM3_T[j], j)) & _MASK32, 7)
            ss2 = ss1 ^ a12
            if j < 16:
                ff = a ^ b ^ c
                gg = e ^ f ^ g
            else:
                ff = (a & b) | (a & c) | (b & c)
                gg = (e & f) | (~e & _MASK32 & g)
            tt1 = (ff + d + ss2 + w1[j]) & _MASK32
            tt2 = (gg + h + ss1 + w[j]) & _MASK32
            d = c
            c = _rotl(b, 9)
            b = a
            a = tt1
            h = g
            g = _rotl(f, 19)
            f = e
            e = _sm3_p0(tt2)

        state = [x ^ y for x, y in zip(state, (a, b, c, d, e, f, g, h))]

    return b"".join(word.to_bytes(4, "big") for word in state)


# --------------------------------------------------------------------------
# 椭圆曲线运算（素域上的仿射坐标）
# --------------------------------------------------------------------------
Point = tuple[int, int] | None


def _point_add(p1: Point, p2: Point) -> Point:
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if (y1 + y2) % _P == 0:
            return None
        slope = (3 * x1 * x1 + _A) * pow(2 * y1, -1, _P) % _P
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, _P) % _P
    x3 = (slope * slope - x1 - x2) % _P
    y3 = (slope * (x1 - x3) - y1) % _P
    return x3, y3


def _scalar_mult(k: int, point: Point) -> Point:
    result: Point = None
    addend = point
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _kdf(z: bytes, key_length: int) -> bytes:
    """SM2 密钥派生函数。

    输入 ``z`` 由调用方按站点约定构造（见模块 docstring）。
    """
    if key_length == 0:
        return b""
    out = bytearray()
    counter = 1
    while len(out) < key_length:
        out += sm3(z + counter.to_bytes(4, "big"))
        counter += 1
    return bytes(out[:key_length])


def _parse_public_key(public_key_b64: str) -> Point:
    raw = base64.b64decode(public_key_b64)
    if len(raw) == 65 and raw[0] == 0x04:
        raw = raw[1:]
    if len(raw) != 64:
        raise ValueError(f"不支持的 SM2 公钥长度: {len(raw)} 字节")
    return int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")


def _shared_bytes(x: int, y: int) -> bytes:
    """KDF 输入：共享点 ``x2||y2`` 的原始 64 字节。"""
    return x.to_bytes(32, "big") + y.to_bytes(32, "big")


def encrypt(plaintext: bytes, public_key_b64: str) -> str:
    """用 base64 公钥加密，返回 base64 密文（C1||C3||C2，C1 无 04 前缀）。"""
    point = _parse_public_key(public_key_b64)
    while True:
        k = secrets.randbelow(_N - 1) + 1
        x1, y1 = _scalar_mult(k, (_GX, _GY))
        x2, y2 = _scalar_mult(k, point)
        t = _kdf(_shared_bytes(x2, y2), len(plaintext))
        if any(t):
            break
    c1 = x1.to_bytes(32, "big") + y1.to_bytes(32, "big")
    c2 = bytes(a ^ b for a, b in zip(plaintext, t))
    c3 = sm3(x2.to_bytes(32, "big") + plaintext + y2.to_bytes(32, "big"))
    return base64.b64encode(c1 + c3 + c2).decode("ascii")


def decrypt(cipher_b64: str, private_key_hex: str) -> bytes:
    """用十六进制私钥解密 base64 密文。主要用于兼容性自检。"""
    raw = base64.b64decode(cipher_b64)
    if len(raw) < 96:
        raise ValueError("密文长度不足")
    x1 = int.from_bytes(raw[0:32], "big")
    y1 = int.from_bytes(raw[32:64], "big")
    c3 = raw[64:96]
    c2 = raw[96:]
    d = int(private_key_hex, 16)
    x2, y2 = _scalar_mult(d, (x1, y1))
    t = _kdf(_shared_bytes(x2, y2), len(c2))
    plaintext = bytes(a ^ b for a, b in zip(c2, t))
    expected_c3 = sm3(x2.to_bytes(32, "big") + plaintext + y2.to_bytes(32, "big"))
    if expected_c3 != c3:
        raise ValueError("C3 校验失败：密文或私钥不匹配")
    return plaintext
