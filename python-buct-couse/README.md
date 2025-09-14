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

```python
from buct_course import BUCTAuth, CourseUtils

# 创建认证实例
auth = BUCTAuth()

# 登录
if auth.login("your_username", "your_password"):
    session = auth.get_session()
    
    # 使用课程工具
    course_utils = CourseUtils(session)
    tasks = course_utils.get_pending_tasks()
    print(f"待办任务: {tasks}")
else:
    print("登录失败")
```

## API 参考

### BUCTAuth

- `login(username, password)`: 登录课程平台
- `get_session()`: 获取认证后的会话
- `logout()`: 退出登录

### CourseUtils

- `get_courses()`: 获取所有课程
- `get_pending_tasks()`: 获取待办任务
- `get_course_content(course_id)`: 获取课程内容

### TestUtils

- `get_test_categories()`: 获取测试分类
- `get_tests_by_category(cate_id)`: 按分类获取测试
- `take_test(test_id)`: 开始测试
- `get_test_results(test_id)`: 获取测试结果

## 异常处理

库提供了详细的异常类型：

- `BUCTCourseError`: 基础异常
- `LoginError`: 登录相关错误
- `NetworkError`: 网络连接错误
- `ParseError`: 解析错误

## 许可证

MIT License

## 免责声明

本库仅供学习和技术研究使用，请遵守学校相关规定，合理使用自动化工具。