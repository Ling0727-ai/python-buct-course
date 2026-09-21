# 北化课程系统 Python SDK (BUCT Course System)

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个功能完善的北京化工大学课程平台 Python 客户端，支持自动登录、获取作业和测试信息、智能时间提醒等功能。

> 📖 **文档导航**: [快速入门](QUICKSTART.md) | [完整文档](#) | [示例代码](example/README.md) | [调试指南](DEBUGGING_NOTES.md) | [文档索引](DOCS.md)

## ✨ 主要特性

### 🔐 认证管理
- 支持学号密码登录（学校统一身份认证 / CAS）
- 口令使用 **SM2 国密**加密后提交，不依赖浏览器 JS，纯 Python 算法复现
- 自动维护登录会话，并完成课程平台 SSO 票据回跳
- 安全的会话管理机制

### 📝 作业管理
- 获取所有待提交作业列表
- 解析作业详细要求和任务描述
- 智能过滤（仅显示未完成且未超时的作业）
- 计算剩余时间并标记紧急作业（24小时内截止）
- 支持分组作业识别
- 显示作业截止时间、发布人等详细信息

### 🧪 测试管理
- 获取可进行的测试列表
- 显示测试状态和截止时间
- 自动生成测试链接

### ⚡ 性能优化
- 内置请求延迟，避免触发反爬虫机制
- 批量获取优化，提高稳定性
- 智能错误处理和重试机制

### 📊 数据分析
- 统计作业和测试数量
- 识别紧急任务（24小时内截止）
- 计算并显示剩余时间

## 🔐 登录机制说明（重要）

> **v1.4.0 起登录方式已整体切换到学校统一身份认证（CAS）。对外 API 没有任何变化，旧代码无需修改。**

### 旧逻辑（已废弃）

早期版本直接向课程平台 MEOL 的接口提交表单：

```
POST https://course.buct.edu.cn/meol/loginCheck.do
     IPT_LOGINUSERNAME=<学号>&IPT_LOGINPASSWORD=<明文密码>&logintoken=<毫秒时间戳>
```

这套逻辑**已经不可用**：

- `/meol/loginCheck.do` 现在返回 **404**，学校已下线该接口，这正是旧版本「登录不稳定」的根因；
- 它把**明文密码**放进请求体，安全性也差。

相关代码已在 v1.4.0 从 `buct_course/auth.py` 中**彻底移除**（`BUCTAuth` 不再存在 `_legacy_meol_login`）。

### 新逻辑（v1.4.0 起）

改走 `portal.buct.edu.cn` 的统一身份认证，完整流程：

| 步骤 | 请求 | 作用 |
|------|------|------|
| 1 | `GET course.buct.edu.cn/meol/homepage/common/sso_login.jsp` | 拿到本次登录的 `service` 参数 |
| 2 | `GET portal.buct.edu.cn/cas/login?service=<service>` | 服务端下发 `COOKIE_INFO` cookie，其中 `data.flowKey` 即 **`flowKey`** |
| 3 | `GET portal.buct.edu.cn/cas/api/reset/rules` | 拿到 SM2 公钥 |
| 4 | — | 口令先全角转半角，再用 **SM2** 加密 |
| 5 | `POST portal.buct.edu.cn/cas/username-password/login` | 提交 `{"username", "password", "flowKey"}` |
| 6 | 跟随 `data.service` 回跳 | 完成课程平台 SSO 票据校验，建立 MEOL 会话 |

### 两个参数的处理方式

| 参数 | 说明 |
|------|------|
| `flowKey` | **服务端下发的一次性令牌**，形如 `flow.<64 位 hex>`，并非客户端计算。**不可重复使用**（复用会返回 `180076`），因此每次登录都会重新获取；失效时自动换新重试一次 |
| `password` | `base64(C1.x ‖ C1.y ‖ C3 ‖ C2)`。SM2 密文，其中 C1 为 64 字节、**不带 `04` 未压缩点前缀**；加密前口令会先做全角转半角（对齐前端 `fullToHalf`） |

`buct_course/sm2_crypto.py` 是**零依赖**的纯 Python SM2 + SM3 实现：不需要执行站点 JS，也没有引入 `gmssl` 等第三方加密库。

### 对使用者的影响

- ✅ `BUCTAuth` / `BUCTClient` 的函数名、参数、返回值**完全没变**，原有代码不用改
- ✅ 口令不再明文直连 MEOL，而是以 SM2 密文提交
- ⚠️ **开启 MFA 二次验证或图形验证码的账号目前无法登录**，会抛出带明确说明的 `LoginError`；请先在浏览器完成一次登录，或联系管理员确认
- ⚠️ 连续输错密码会触发学校侧锁定（`180028` 临时锁定 30 分钟 / `180029` 锁死），**请勿用脚本暴力试密码**
- ℹ️ 登录成功后门户会下发 `TGC` cookie，可用于后续免密换取其它系统的票据

## 📦 安装

### 方式一：使用 pip 安装（推荐）

```bash
pip install buct-course
```

### 方式二：克隆项目并用pip安装依赖

```bash
git clone https://github.com/yourusername/python-buct-course.git
pip install -r requirements.txt
```

### 方式三：克隆项目并用uv安装依赖

```bash
# uv 安装工具
# 1. pip 安装
pip install uv

# 2. windows安装uv
## 方法1: PowerShell 安装脚本 (推荐)
irm https://astral.sh/uv/install.ps1 | iex

## 方法2: 使用 winget
winget install --id=astral-sh.uv

## 方法3: 使用 pip (在命令提示符或 PowerShell 中)
pip install uv

# 3. linux/macOS安装uv
curl -fsSL https://astral.sh/uv/install.sh | sh
```

```bash
git clone https://github.com/yourusername/python-buct-course.git
uv sync
```


## 🚀 快速开始

### 示例 1：简单使用（推荐新手）

```python
from buct_course import BUCTCourseClient

# 创建客户端并登录
client = BUCTCourseClient("你的学号", "你的密码")

# 登录
if client.login():
    print("✓ 登录成功")
    
    # 获取待提交作业列表
    pending = client.get_pending_homework()
    
    # 显示作业信息
    for course in pending:
        print(f"课程: {course['course_name']}")
        print(f"  LID: {course['lid']}")
else:
    print("✗ 登录失败")
```

### 示例 2：获取详细作业信息

```python
from buct_course import BUCTCourseClient

client = BUCTCourseClient("你的学号", "你的密码")

if client.login():
    # 获取所有待提交作业的详细信息
    all_details = client.get_all_pending_homework_details()
    
    for course in all_details:
        print(f"\n课程: {course['course_name']}")
        print(f"作业总数: {course['total_count']}")
        print(f"紧急作业: {course['urgent_count']}")
        
        # 显示每个作业
        for hw in course['homework_list']:
            print(f"\n  作业: {hw['title']}")
            print(f"    截止时间: {hw['deadline']}")
            print(f"    剩余时间: {hw.get('time_remaining', '未知')}")
            if hw.get('is_urgent'):
                print(f"    ⚠️ 紧急！24小时内截止")
```

### 示例 3：获取特定课程的作业

```python
from buct_course import BUCTCourseClient

client = BUCTCourseClient("你的学号", "你的密码")

if client.login():
    # 先获取待提交作业列表
    pending = client.get_pending_homework()
    
    # 获取第一门课程的详细信息
    if pending:
        first_course = pending[0]
        lid = first_course['lid']
        
        # 获取课程详情
        details = client.get_course_details(lid)
        
        print(f"课程作业数量: {details['total_count']}")
        for hw in details['homework_list']:
            print(f"- {hw['title']}")
```

### 示例 4：交互式使用

```python
from buct_course import BUCTClient

client = BUCTClient()
client.run_interactive()  # 运行交互式界面
```

### 示例 5：命令行快速运行

```bash
# 运行主程序
python main.py

# 运行快速测试
python quick_test.py

# 运行诊断测试
python test_diagnosis.py
```

## 📁 项目结构

```
python-buct-course/
├── buct_course/              # 核心包
│   ├── __init__.py          # 包初始化，导出主要类
│   ├── auth.py              # 认证模块（统一身份认证登录、会话管理）
│   ├── sm2_crypto.py        # 零依赖 SM2 / SM3 实现（口令加密）
│   ├── client.py            # 主客户端（BUCTClient）
│   ├── client_optimized.py  # 优化版客户端（BUCTCourseClient）
│   ├── course_utils.py      # 课程工具（作业获取、解析）
│   ├── test_utils.py        # 测试工具（测试获取、解析）
│   ├── lid_utils.py         # 课程ID获取工具
│   └── exceptions.py        # 自定义异常
├── example/                  # 示例代码
│   ├── demo_client.py       # 交互式客户端演示
│   ├── homework_example.py  # 作业获取示例
│   ├── simple_test.py       # 简单测试示例
│   └── ...                  # 其他示例
├── test/                     # 测试文件
├── main.py                   # 主程序入口
├── quick_test.py            # 快速测试脚本
├── test_diagnosis.py        # 诊断测试脚本
├── README.md                # 本文档
└── requirements.txt         # 依赖列表
```

## 🔧 核心 API

### BUCTCourseClient 类（推荐使用）

这是优化后的客户端，提供更简洁的API和更好的性能。

> ℹ️ `BUCTCourseClient` 是 `buct_course.client_optimized.BUCTClient` 的**别名**，为兼容早期文档中的写法而保留。
> 包根直接导出的 `BUCTClient` 来自 `buct_course.client`。两者目前公开方法完全一致。

#### 初始化

```python
from buct_course import BUCTCourseClient

# 方式1：创建时传入凭据
client = BUCTCourseClient("学号", "密码")

# 方式2：先创建再登录
client = BUCTCourseClient()
# 稍后调用 client.login() 登录
```

#### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `login()` | 登录系统 | `bool` |
| `logout()` | 退出登录 | `None` |
| `get_pending_homework()` | 获取待提交作业的课程列表 | `list[dict]` |
| `get_course_details(lid)` | 获取指定课程的作业详情 | `dict` |
| `get_homework_detail(hwtid)` | 获取单个作业的详细信息 | `dict` |
| `get_homework_tasks(url)` | 获取作业的具体任务要求 | `list[str]` |
| `get_all_pending_homework_details()` | 批量获取所有作业详情（含时间分析） | `list[dict]` |
| `get_pending_tests()` | 获取待进行的测试列表 | `list[dict]` |

#### 返回数据格式

**get_pending_homework() 返回格式：**

```python
[
    {
        'course_name': '课程名称',
        'lid': '课程ID',
        'type': 'homework',
        'url': '课程链接'
    },
    ...
]
```

**get_course_details(lid) 返回格式：**

```python
{
    'lid': '课程ID',
    'homework_list': [
        {
            'title': '作业标题',
            'deadline': '2025年12月31日 23:59:00',
            'score': '',  # 已完成作业有分数
            'publisher': '发布人',
            'hwtid': '作业ID',
            'detail_href': '作业详情链接',
            'submit_href': '提交链接',
            'can_submit': True,  # 是否可以提交
            'is_group': False,   # 是否为分组作业
            'has_result': False, # 是否有结果
            'status': '未提交'
        },
        ...
    ],
    'total_count': 5  # 作业总数
}
```

**get_all_pending_homework_details() 返回格式：**

```python
[
    {
        'course_name': '课程名称',
        'lid': '课程ID',
        'course_info': {...},  # 课程信息
        'homework_list': [
            {
                'title': '作业标题',
                'deadline': '2025年12月31日 23:59:00',
                'time_remaining': '15天8小时30分钟',  # 剩余时间
                'is_urgent': False,  # 是否紧急（24小时内）
                'hwtid': '作业ID',
                'can_submit': True,
                'is_group': False,
                # ... 其他字段
            },
            ...
        ],
        'total_count': 5,    # 作业总数
        'urgent_count': 1    # 紧急作业数
    },
    ...
]
```

### BUCTClient 类（兼容旧版）

这是原始客户端，提供更高级的封装和显示功能。

```python
from buct_course import BUCTClient

client = BUCTClient()
if client.login("学号", "密码"):
    # 获取待办任务（作业+测试）
    tasks = client.get_pending_tasks()
    
    # 显示任务
    client.display_tasks(tasks)
    
    # 显示详细作业信息
    client.display_homework_with_tasks()
    
    # 显示测试详情
    client.display_test_details()
```
## ⚙️ 高级功能

### 性能优化

项目内置了智能延迟机制，在以下场景自动添加延迟以避免触发反爬虫：

- 获取课程主页后：0.3秒
- 访问作业页面前：0.5秒
- 解析表格前：0.5秒
- 获取作业详情前：0.3秒
- 批量获取课程间：0.8秒

详见 [DEBUGGING_NOTES.md](DEBUGGING_NOTES.md) 了解延迟优化的详细说明。

### 时间分析

`get_all_pending_homework_details()` 方法会自动：

1. 解析截止时间
2. 计算剩余时间
3. 识别紧急作业（24小时内截止）
4. 格式化显示时间信息

### 错误处理

项目提供了完善的异常处理机制：

```python
from buct_course import BUCTCourseClient
from buct_course.exceptions import LoginError, NetworkError, ParseError

client = BUCTCourseClient("学号", "密码")

try:
    client.login()
    details = client.get_course_details("123456")
except LoginError as e:
    print(f"登录失败: {e}")
except NetworkError as e:
    print(f"网络错误: {e}")
except ParseError as e:
    print(f"解析错误: {e}")
```

## 📝 完整示例

查看 `example/` 目录获取更多示例：

- `demo_client.py` - 交互式客户端演示
- `homework_example.py` - 作业获取完整示例
- `simple_test.py` - 简单测试示例
- `full_html_test.py` - HTML解析测试
- `time_test.py` - 时间计算测试
- `subject_test.py` - 课程信息测试

## ⚠️ 注意事项

1. **网络要求**
   - 需要能够访问北化课程平台（`course.buct.edu.cn`）**和**统一身份认证（`portal.buct.edu.cn`）
   - 建议在校园网环境下使用，外网可能需要VPN

2. **登录凭据**
   - 使用正确的学号和密码
   - 密码不会被存储，仅用于登录；v1.4.0 起以 SM2 密文提交，不再明文传输
   - 开启 MFA / 图形验证码的账号暂不支持，详见上方「登录机制说明」

3. **请求频率**
   - 项目已内置延迟机制，避免过快请求
   - 建议不要修改延迟参数，除非遇到问题

4. **数据时效性**
   - 获取的数据为实时数据
   - 建议定期运行以获取最新信息

5. **兼容性**
   - 登录部分基于 v1.4.0（2026年9月）的统一身份认证接口
   - 作业 / 测试解析部分基于当前课程平台页面结构
   - 如果平台更新可能需要调整对应逻辑

## 🐛 故障排除

### 常见问题

**Q1: 登录失败怎么办？**

A: 检查以下几点：
- 学号和密码是否正确
- 网络连接是否正常
- 是否能够访问 `course.buct.edu.cn` 与 `portal.buct.edu.cn`（两者都需要）
- 查看抛出的 `LoginError` 具体文案，常见的有：
  - `用户名或密码错误` → 口令不对
  - `该账号需要 MFA 二次验证…` / `需要图形验证码…` → 本库暂不支持，请先在浏览器登录一次
  - `账号登录失败次数过多，已临时锁定…` → 等待 30 分钟再试
  - `flowKey 已被使用过` → 已自动重试；若反复出现请提 Issue

**Q1b: 旧版本能登录，升级到 1.4.0 后不行了？**

A: 学校已下线旧的 `/meol/loginCheck.do` 接口（现返回 404），所以**任何**仍走旧逻辑的版本都会失败。1.4.0 已改为统一身份认证，正常账号可直接使用；若你的账号开启了 MFA 或验证码，见 Q1 说明。

**Q2: 获取数据时出现超时**

A: 可能的原因：
- 网络不稳定
- 服务器响应慢
- 可以尝试增加延迟时间

**Q3: 解析错误或数据不正确**

A: 可能的原因：
- 课程平台页面结构发生变化
- HTML内容未完全加载
- 运行 `test_diagnosis.py` 查看详细日志

**Q4: 部分课程获取失败**

A: 这是正常现象：
- 某些课程可能没有作业链接
- 项目会跳过失败的课程继续处理
- 查看控制台输出了解具体错误

### 调试模式

运行诊断脚本查看详细日志：

```bash
python test_diagnosis.py
```

启用 Python 调试日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 性能问题

如果遇到响应慢或失败，可以：

1. 运行 `quick_test.py` 快速测试
2. 检查网络连接
3. 适当增加延迟时间（修改 `course_utils.py` 中的 `time.sleep` 参数）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 确保代码通过测试

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢所有贡献者和使用者！

## 📮 联系方式

如有问题或建议，欢迎：
- 提交 Issue
- 发送邮件
- 参与讨论

---

**免责声明**: 本项目仅供学习和研究使用，请遵守学校相关规定。

本项目仅供学习和个人使用。

## 更新日志

### v1.0.0
- 基本的登录和数据获取功能
- 作业和测试信息显示
- 详细作业要求提取
- 智能过滤和时间管理

### v1.1.0
- 可抓取到具体作业详情

### v1.2.0
- 修复部分抓取失败bug

### v1.3.0
- 增强会话管理与登录流程：登录时重建 session，避免旧 cookie / 旧登录态干扰

### v1.4.0
- **登录整体切换到学校统一身份认证（CAS）**。旧的 `/meol/loginCheck.do` 直连逻辑已彻底移除——该接口现已返回 404
- 新增零依赖纯 Python SM2 + SM3 实现（`buct_course/sm2_crypto.py`），口令以 SM2 密文提交，不再明文传输
- `flowKey` 一次性令牌自动获取，失效时自动换新重试
- 登录后自动跟随 `data.service` 回跳，完成课程平台 SSO 票据校验
- 登录失败给出可读原因（口令错误 / 需要 MFA / 需要验证码 / 账号锁定 / flowKey 失效）
- 修复 `example/` 中把 `login()` 的返回值当成 session 使用的错误写法
- 打包收窄：wheel 只包含 `buct_course`，不再把 `example/`、`test/` 装成顶层包
- 统一版本号来源（`pyproject.toml` / `setup.py` / `__init__.py` / `uv.lock` 此前不一致）

### v1.4.1
- 新增 `BUCTCourseClient` 别名（指向 `client_optimized.BUCTClient`），修复文档中该名字不存在导致的 `ImportError`
- README 补充别名说明