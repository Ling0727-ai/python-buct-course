"""
示例 1: 基础使用 - 获取待提交作业列表
最简单的使用方式，适合快速查看有哪些课程有待提交的作业
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import BUCTCourseClient

def basic_usage_example():
    """基础使用示例"""

    # 创建客户端
    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTCourseClient(username, password)

    # 登录
    print("\n正在登录...")
    if not client.login():
        print("✗ 登录失败，请检查学号和密码")
        return

    print("✓ 登录成功！\n")

    # 获取待提交作业的课程列表
    print("正在获取待提交作业列表...")
    pending_courses = client.get_pending_homework()

    if not pending_courses:
        print("✓ 太棒了！目前没有待提交的作业")
        return

    # 显示结果
    print(f"✓ 找到 {len(pending_courses)} 门课程有待提交的作业\n")
    print("=" * 60)

    for i, course in enumerate(pending_courses, 1):
        print(f"{i}. 课程名称: {course['course_name']}")
        print(f"   课程ID (LID): {course['lid']}")
        print(f"   类型: {course['type']}")
        print("-" * 60)

    print("\n💡 提示: 运行 example2_detailed_homework.py 查看详细作业信息")

if __name__ == "__main__":
    try:
        basic_usage_example()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()

