"""
示例索引 - 所有示例的快速导航
运行这个文件可以选择运行不同的示例
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def show_menu():
    """显示示例菜单"""
    print("=" * 70)
    print("北化课程系统 Python SDK - 示例导航")
    print("=" * 70)
    print("\n请选择要运行的示例:\n")

    examples = [
        ("基础使用", "example1_basic_usage.py", "获取待提交作业的课程列表"),
        ("详细作业信息", "example2_detailed_homework.py", "获取特定课程的所有作业详情"),
        ("时间分析", "example3_time_analysis.py", "分析作业时间并标记紧急作业"),
        ("作业任务要求", "example4_homework_tasks.py", "获取作业的具体任务描述"),
        ("测试管理", "example5_test_management.py", "获取和管理待进行的测试"),
        ("交互式客户端", "demo_client.py", "运行交互式命令行界面"),
    ]

    for i, (name, filename, description) in enumerate(examples, 1):
        print(f"  {i}. {name}")
        print(f"     文件: {filename}")
        print(f"     说明: {description}\n")

    print("  0. 退出")
    print("\n" + "=" * 70)

def run_example(choice):
    """运行选择的示例"""
    examples = {
        1: "example1_basic_usage.py",
        2: "example2_detailed_homework.py",
        3: "example3_time_analysis.py",
        4: "example4_homework_tasks.py",
        5: "example5_test_management.py",
        6: "demo_client.py",
    }

    if choice in examples:
        filename = examples[choice]
        filepath = os.path.join(os.path.dirname(__file__), filename)

        print(f"\n正在运行 {filename}...\n")
        print("=" * 70)

        # 执行示例文件
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
            exec(code, {'__name__': '__main__', '__file__': filepath})
    else:
        print("✗ 无效的选择")

def main():
    """主函数"""
    while True:
        show_menu()

        try:
            choice = input("\n请输入选项 (0-6): ").strip()

            if choice == '0':
                print("\n再见！")
                break

            if choice.isdigit():
                run_example(int(choice))

                input("\n\n按回车键返回菜单...")
            else:
                print("✗ 请输入有效的数字")

        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n✗ 运行示例时发生错误: {e}")
            import traceback
            traceback.print_exc()
            input("\n\n按回车键返回菜单...")

if __name__ == "__main__":
    main()

