# 北化课程系统 (BUCT Course System)

一个用于北京化工大学课程平台的Python客户端，可以自动获取待办作业和测试信息。

## 功能特性

- 🔐 **自动登录**: 支持学号密码登录
- 📝 **作业管理**: 获取待提交作业列表，包含详细要求
- 🧪 **测试管理**: 获取可进行的测试信息
- ⏰ **截止时间**: 显示作业和测试的截止时间
- 🎯 **智能过滤**: 只显示未完成且未超时的任务
- 📋 **详细信息**: 提取作业的具体要求和任务描述

## 安装依赖

```bash
pip install requests beautifulsoup4 lxml
```

## 快速开始

### 1. 基本使用

```python
from buct_course import BUCTClient

# 创建客户端
client = BUCTClient()

# 登录
if client.login("你的学号", "你的密码"):
    # 获取待办任务
    tasks = client.get_pending_tasks()
    client.display_tasks(tasks)
    
    # 显示详细作业信息
    client.display_homework_with_tasks()
    
    # 显示测试信息
    client.display_test_details()
```

### 2. 交互式运行

```python
from buct_course import BUCTClient

client = BUCTClient()
client.run_interactive()
```

### 3. 命令行运行

```bash
# 运行主程序
python main.py

# 运行完整测试
python complete_test.py
```

## 项目结构

```
python-buct-course/
├── buct_course/           # 核心包
│   ├── __init__.py       # 包初始化
│   ├── auth.py           # 认证模块
│   ├── client.py         # 主客户端
│   ├── course_utils.py   # 课程工具
│   ├── test_utils.py     # 测试工具
│   ├── lid_utils.py      # 课程ID工具
│   └── exceptions.py     # 异常定义
├── example/              # 示例代码
├── test/                 # 测试文件
├── main.py              # 主程序入口
├── complete_test.py     # 完整功能测试
└── README.md           # 说明文档
```

## 核心功能

### 作业管理

- **获取作业列表**: 自动获取所有待提交作业
- **过滤功能**: 只显示未完成且未超时的作业
- **详细信息**: 提取作业的具体要求和描述
- **截止时间**: 显示作业截止时间
- **分组标识**: 标识是否为分组作业

### 测试管理

- **测试列表**: 获取可进行的测试
- **状态显示**: 显示测试状态和可用性
- **链接生成**: 自动生成测试链接

### 数据提取

系统能够从HTML页面中提取以下信息：

- 作业标题和描述
- 截止时间
- 发布人信息
- 作业要求详情
- 提交状态
- 分组信息

## API 参考

### BUCTClient 类

#### 主要方法

- `login(username, password)`: 登录系统
- `logout()`: 退出登录
- `get_pending_tasks()`: 获取待办任务
- `get_homework_with_tasks()`: 获取包含详细要求的作业信息
- `display_tasks(tasks)`: 显示任务列表
- `display_homework_with_tasks()`: 显示详细作业信息
- `display_test_details()`: 显示测试详情
- `run_interactive()`: 运行交互式界面

#### 返回数据格式

```python
# 待办任务格式
{
    "success": True,
    "data": {
        "homework": [
            {
                "course_name": "课程名称",
                "title": "作业标题",
                "deadline": "截止时间",
                "hwtid": "作业ID",
                "can_submit": True,
                "is_group": False,
                "tasks": ["任务要求1", "任务要求2"]
            }
        ],
        "tests": [...],
        "stats": {
            "homework_count": 2,
            "tests_count": 1,
            "total_count": 3
        }
    }
}
```

## 注意事项

1. **网络连接**: 需要能够访问北化课程平台
2. **登录凭据**: 使用正确的学号和密码
3. **会话管理**: 系统会自动管理登录会话
4. **错误处理**: 包含完善的错误处理机制
5. **数据安全**: 不会存储用户密码

## 故障排除

### 常见问题

1. **登录失败**
   - 检查学号和密码是否正确
   - 确认网络连接正常
   - 检查是否需要验证码

2. **获取数据失败**
   - 检查登录状态
   - 确认课程平台可访问
   - 查看错误日志

3. **解析错误**
   - 可能是页面结构发生变化
   - 检查HTML解析逻辑

### 调试模式

可以通过以下方式启用调试信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 开发说明

### 扩展功能

要添加新功能，可以：

1. 在相应的工具类中添加方法
2. 在客户端类中添加接口
3. 更新显示逻辑

### 贡献代码

欢迎提交Pull Request来改进项目。

## 许可证

本项目仅供学习和个人使用。

## 更新日志

### v1.0.0
- 基本的登录和数据获取功能
- 作业和测试信息显示
- 详细作业要求提取
- 智能过滤和时间管理