# 快速入门指南

欢迎使用北化课程系统 Python SDK！本指南将帮助你在 5 分钟内开始使用。

## 📦 第一步：安装依赖

打开终端/命令行，运行：

```bash
pip install requests beautifulsoup4 lxml
```

## 🚀 第二步：运行第一个示例

### 方式一：使用示例导航（推荐）

```bash
cd python-buct-course
python example/README.py
```

然后选择 `1` 运行基础使用示例。

### 方式二：直接运行示例

```bash
python example/example1_basic_usage.py
```

### 方式三：编写你的第一个脚本

创建一个新文件 `my_first_script.py`：

```python
from buct_course import BUCTCourseClient

# 替换为你的学号和密码
client = BUCTCourseClient("你的学号", "你的密码")

# 登录
if client.login():
    print("✓ 登录成功！")
    
    # 获取待提交作业
    pending = client.get_pending_homework()
    
    # 显示结果
    print(f"\n你有 {len(pending)} 门课程有待提交的作业：")
    for course in pending:
        print(f"- {course['course_name']}")
else:
    print("✗ 登录失败")
```

运行：

```bash
python my_first_script.py
```

## 📚 第三步：学习更多功能

### 查看详细作业信息

```python
from buct_course import BUCTCourseClient

client = BUCTCourseClient("学号", "密码")

if client.login():
    # 获取待提交作业列表
    pending = client.get_pending_homework()
    
    # 获取第一门课程的详细信息
    if pending:
        first_course = pending[0]
        details = client.get_course_details(first_course['lid'])
        
        print(f"课程：{first_course['course_name']}")
        print(f"作业数：{details['total_count']}")
        
        # 显示每个作业
        for hw in details['homework_list']:
            print(f"\n作业：{hw['title']}")
            print(f"截止时间：{hw['deadline']}")
```

### 获取时间分析

```python
from buct_course import BUCTCourseClient

client = BUCTCourseClient("学号", "密码")

if client.login():
    # 获取所有作业详情（包含时间分析）
    all_details = client.get_all_pending_homework_details()
    
    # 统计紧急作业
    urgent_count = sum(course['urgent_count'] for course in all_details)
    print(f"紧急作业数：{urgent_count}")
    
    # 显示紧急作业
    for course in all_details:
        for hw in course['homework_list']:
            if hw.get('is_urgent'):
                print(f"⚠️ {hw['title']} - 剩余：{hw['time_remaining']}")
```

## 🎯 常用功能速查

| 功能 | 方法 | 说明 |
|------|------|------|
| 登录 | `client.login()` | 登录系统 |
| 获取课程列表 | `client.get_pending_homework()` | 有待提交作业的课程 |
| 获取课程详情 | `client.get_course_details(lid)` | 指定课程的作业列表 |
| 获取全部详情 | `client.get_all_pending_homework_details()` | 所有作业+时间分析 |
| 获取作业任务 | `client.get_homework_tasks(url)` | 作业的具体要求 |
| 获取测试 | `client.get_pending_tests()` | 待进行的测试 |

## 💡 常见问题

**Q: 登录失败怎么办？**
A: 检查学号和密码是否正确，确保能访问 course.buct.edu.cn

**Q: 运行很慢是正常的吗？**
A: 是的。为了避免触发反爬虫，程序会在请求之间添加延迟。批量获取所有课程详情可能需要几十秒。

**Q: 可以保存数据吗？**
A: 可以！所有方法返回的都是标准的 Python 数据结构（字典和列表），你可以：
- 保存为 JSON: `import json; json.dump(data, open('data.json', 'w'))`
- 保存为 CSV: `import csv; ...`
- 存入数据库: `import sqlite3; ...`

**Q: 如何定期运行？**
A: 可以使用：
- Windows 任务计划程序
- Linux cron
- Python 的 schedule 库

## 📖 下一步

1. 阅读完整的 [README.md](../README.md)
2. 查看 [example/README.md](example/README.md) 了解所有示例
3. 浏览 [DEBUGGING_NOTES.md](../DEBUGGING_NOTES.md) 了解性能优化

## 🤝 获取帮助

- 查看示例代码：`example/` 目录
- 查看文档：`README.md`
- 提交问题：GitHub Issues

---

祝你使用愉快！🎉

