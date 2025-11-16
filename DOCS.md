# 文档索引

本项目包含以下文档，帮助你快速上手和深入使用。

## 📚 核心文档

### [README.md](README.md) - 主文档 ⭐
- 项目简介和特性
- 完整的安装指南
- API 参考文档
- 数据格式说明
- 故障排除

**适合**: 所有用户，特别是首次使用者

### [QUICKSTART.md](QUICKSTART.md) - 快速入门 🚀
- 5分钟快速开始
- 基础示例代码
- 常用功能速查表
- 常见问题解答

**适合**: 想要快速上手的新用户

## 🔧 技术文档

### [DEBUGGING_NOTES.md](DEBUGGING_NOTES.md) - 调试说明
- 断点调试问题分析
- 延迟优化策略
- 性能优化详解
- 测试方法

**适合**: 遇到问题的用户，或想了解内部实现的开发者

### [OPTIMIZATION_NOTES.md](OPTIMIZATION_NOTES.md) - 优化说明
- 响应速度优化
- time.sleep 延迟说明
- 性能影响分析
- 使用建议

**适合**: 关注性能的用户和开发者

## 📖 示例文档

### [example/README.md](example/README.md) - 示例说明
- 所有示例的完整列表
- 示例使用方法
- 学习路径建议
- 示例输出展示

**适合**: 想通过实例学习的用户

## 📂 目录结构

```
python-buct-course/
├── README.md                    # 主文档（最重要）
├── QUICKSTART.md               # 快速入门（新手必读）
├── DEBUGGING_NOTES.md          # 调试说明
├── OPTIMIZATION_NOTES.md       # 优化说明
├── LICENSE                     # 许可证
│
├── example/
│   ├── README.md               # 示例说明
│   ├── README.py               # 示例导航（可运行）
│   ├── example1_basic_usage.py
│   ├── example2_detailed_homework.py
│   ├── example3_time_analysis.py
│   ├── example4_homework_tasks.py
│   ├── example5_test_management.py
│   └── ... (其他示例)
│
├── buct_course/                # 核心包
│   ├── __init__.py
│   ├── auth.py
│   ├── client.py
│   ├── client_optimized.py
│   ├── course_utils.py
│   ├── test_utils.py
│   ├── lid_utils.py
│   └── exceptions.py
│
├── test/                       # 测试文件
├── main.py                     # 主程序
├── quick_test.py              # 快速测试
├── test_diagnosis.py          # 诊断测试
└── requirements.txt           # 依赖列表
```

## 🎯 使用路径

### 新用户入门流程

1. **阅读** [QUICKSTART.md](QUICKSTART.md) (5分钟)
2. **运行** `python example/README.py` 选择示例 (5分钟)
3. **尝试** 编写自己的脚本 (10分钟)
4. **参考** [README.md](README.md) 了解完整API

**总计**: 约 20 分钟即可上手

### 遇到问题时

1. **检查** [README.md](README.md) 的故障排除部分
2. **查看** [DEBUGGING_NOTES.md](DEBUGGING_NOTES.md)
3. **运行** `python test_diagnosis.py` 诊断问题
4. **提交** Issue (如果问题仍未解决)

### 深入学习流程

1. **阅读** [README.md](README.md) 完整文档
2. **学习** [example/README.md](example/README.md) 所有示例
3. **了解** [OPTIMIZATION_NOTES.md](OPTIMIZATION_NOTES.md) 性能优化
4. **研究** 源代码 (`buct_course/` 目录)

## 📋 文档更新日志

### 2025-11-16
- ✨ 重写 README.md，增加详细API说明
- ✨ 新增 QUICKSTART.md 快速入门指南
- ✨ 创建 5 个新示例文件
- ✨ 新增 example/README.md 示例说明
- ✨ 创建示例导航 (example/README.py)
- 📝 更新性能优化文档

### 之前版本
- 基础文档和示例

## 🔍 快速查找

### 我想...

- **快速开始使用** → [QUICKSTART.md](QUICKSTART.md)
- **查看完整功能** → [README.md](README.md)
- **运行示例代码** → `python example/README.py`
- **解决登录问题** → [README.md](README.md) 故障排除部分
- **了解性能优化** → [DEBUGGING_NOTES.md](DEBUGGING_NOTES.md)
- **查看API文档** → [README.md](README.md) 核心API部分
- **贡献代码** → [README.md](README.md) 贡献部分

## 💡 文档建议

如果你觉得文档有不清楚的地方，或者有改进建议，欢迎：
- 提交 Issue 说明问题
- 提交 Pull Request 改进文档
- 在讨论区分享使用经验

---

**提示**: 所有文档都使用 Markdown 格式，可以使用任何 Markdown 阅读器或 GitHub 在线查看。

