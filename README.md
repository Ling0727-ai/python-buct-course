# buct-course

北京化工大学课程平台API库

## 功能特性

- 自动化登录北化课程平台
- 获取课程信息、待办任务
- 查询和参与在线测试
- 异常处理和错误提示

## 安装

### 从PyPI安装（发布后可用）
```bash
pip install buct-course
```

### 从源码安装
```bash
# 克隆仓库
git clone https://github.com/yourusername/buct-course.git
cd buct-course

# 安装开发版本
pip install -e .

# 或者直接安装
pip install .
```

## 快速开始

### 使用 BUCTClient (推荐)

```python
from buct_course import BUCTClient

# 方式1: 创建客户端实例并立即登录
client = BUCTClient("your_username", "your_password")

# 方式2: 先创建客户端，稍后登录
client = BUCTClient()
if client.login("your_username", "your_password"):
    print("登录成功!")

# 获取待办任务
tasks = client.get_pending_tasks()
print(f"待办任务: {tasks}")

# 获取所有课程
courses = client.get_courses()

# 获取测试分类
test_categories = client.get_test_categories()

# 优雅退出
client.logout()
```

### 使用便捷函数

```python
from buct_course import get_pending_tasks, get_test_categories

# 快速获取待办任务
tasks = get_pending_tasks("your_username", "your_password")

# 快速获取测试分类
categories = get_test_categories("your_username", "your_password")
```

### 交互式模式（推荐）

最简单的使用方式是运行交互式客户端：

```python
from buct_course import BUCTClient

# 启动交互式客户端
client = BUCTClient()
client.run_interactive()  # 这会提示输入账号密码并显示详细信息
```

## API 参考

### BUCTClient (主客户端类)

BUCTClient 是一个高级封装类，提供了完整的课程平台操作接口。

#### 初始化
- `BUCTClient(username=None, password=None)`: 创建客户端实例，可立即登录
- `create_client(username=None, password=None)`: 工厂函数创建客户端

#### 认证管理
- `login(username, password)`: 登录课程平台，返回布尔值表示成功与否
- `logout()`: 退出登录，清理会话
- `get_session()`: 获取底层的 requests.Session 对象

#### 课程相关操作
- `get_courses()`: 获取所有课程信息
- `get_pending_tasks()`: 获取待办任务（作业和测试）
- `get_course_content(course_id)`: 获取指定课程的详细内容

#### 测试相关操作  
- `get_test_categories()`: 获取测试分类列表
- `get_tests_by_category(cate_id, **kwargs)`: 按分类获取测试详情
- `get_available_tests(cate_id, **kwargs)`: 获取可进行的测试
- `take_test(test_id)`: 开始指定的测试
- `get_test_results(test_id)`: 获取测试结果

#### 交互式功能
- `run_interactive()`: 启动交互式命令行界面
- `display_welcome()`: 显示欢迎信息
- `display_tasks(tasks)`: 格式化显示待办任务
- `display_test_details(cate_id="34060")`: 显示测试详细信息

### 便捷函数

库还提供了一系列便捷函数，无需手动管理会话：

- `get_pending_tasks(username, password)`: 快速获取待办任务
- `get_test_categories(username, password)`: 快速获取测试分类
- `get_tests_by_category(username, password, cate_id, **kwargs)`: 快速按分类获取测试
- `get_available_tests(username, password, cate_id, **kwargs)`: 快速获取可用测试
- `take_test(username, password, test_id)`: 快速开始测试
- `get_test_results(username, password, test_id)`: 快速获取测试结果

### 底层组件

#### BUCTAuth
- `login(username, password)`: 登录课程平台
- `get_session()`: 获取认证后的会话
- `logout()`: 退出登录

#### CourseUtils
- `get_courses()`: 获取所有课程
- `get_pending_tasks()`: 获取待办任务
- `get_course_content(course_id)`: 获取课程内容

#### TestUtils
- `get_test_categories()`: 获取测试分类
- `get_tests_by_category(cate_id)`: 按分类获取测试
- `take_test(test_id)`: 开始测试
- `get_test_results(test_id)`: 获取测试结果

## 异常处理

库提供了详细的异常类型，所有异常都继承自 `BUCTCourseError`：

- `BUCTCourseError`: 基础异常类
- `LoginError`: 登录相关错误（用户名密码错误等）
- `NetworkError`: 网络连接错误
- `ParseError`: 页面解析错误

### 错误处理示例

```python
from buct_course import BUCTClient, LoginError, NetworkError

try:
    client = BUCTClient("username", "password")
    tasks = client.get_pending_tasks()
    print(tasks)
except LoginError as e:
    print(f"登录失败: {e}")
except NetworkError as e:
    print(f"网络错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
```

## 使用示例

### 示例1: 完整的任务检查脚本

```python
from buct_course import BUCTClient

def check_homework_and_tests():
    # 创建客户端
    client = BUCTClient("your_username", "your_password")
    
    try:
        # 获取待办任务
        tasks = client.get_pending_tasks()
        
        if tasks["success"]:
            stats = tasks["data"]["stats"]
            print(f"📊 发现 {stats['total_count']} 个待办事项:")
            print(f"  📝 作业: {stats['homework_count']} 个")
            print(f"  🧪 测试: {stats['tests_count']} 个")
            
            # 显示作业详情
            if tasks['data']['homework']:
                print("\n🎯 待提交作业:")
                for hw in tasks['data']['homework']:
                    print(f"   • {hw['course_name']} (ID: {hw['lid']})")
            
            # 显示测试详情
            if tasks['data']['tests']:
                print("\n🧪 待提交测试:")
                for test in tasks['data']['tests']:
                    print(f"   • {test['course_name']} (ID: {test['lid']})")
        
        # 获取测试详细信息
        client.display_test_details()
        
    finally:
        # 确保退出
        client.logout()

if __name__ == "__main__":
    check_homework_and_tests()
```

### 示例2: 自动化测试监控

```python
from buct_course import BUCTClient
import time

def monitor_tests(username, password, check_interval=3600):
    """定时监控测试状态"""
    client = BUCTClient(username, password)
    
    while True:
        try:
            # 获取可用测试
            available_tests = client.get_available_tests("34060")
            
            if available_tests["success"] and available_tests["data"]["tests"]:
                print(f"🎯 发现 {len(available_tests['data']['tests'])} 个可进行测试!")
                for test in available_tests["data"]["tests"]:
                    print(f"   • {test['title']} (截止: {test.get('deadline', '未知')})")
            
            # 等待下次检查
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控出错: {e}")
            time.sleep(300)  # 出错后等待5分钟再试
    
    client.logout()
```

## 许可证

MIT License

## 免责声明

本库仅供学习和技术研究使用，请遵守学校相关规定，合理使用自动化工具。严禁用于任何违反学校规定或违法的用途。使用本库产生的一切后果由使用者自行承担。