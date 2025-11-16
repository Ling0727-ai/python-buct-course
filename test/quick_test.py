"""
快速验证修复效果
"""
import sys
import os
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import BUCTCourseClient

def quick_test():
    """快速测试修复后的代码"""

    print("="*60)
    print("快速验证测试 - 模拟断点延迟修复")
    print("="*60)

    username = input("\n请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTCourseClient(username, password)

    print("\n[1] 登录中...")
    if not client.login():
        print("✗ 登录失败")
        return
    print("✓ 登录成功")

    print("\n[2] 获取待提交作业...")
    pending = client.get_pending_homework()
    print(f"✓ 找到 {len(pending)} 门课程")

    if not pending:
        print("\n没有待提交的作业")
        return

    # 只测试前3门课程
    test_courses = pending[:3]

    print(f"\n[3] 测试前 {len(test_courses)} 门课程的详情获取...")
    print("注意: 每个请求之间会有延迟（模拟断点效果）\n")

    for i, course in enumerate(test_courses, 1):
        print(f"  [{i}/{len(test_courses)}] {course['course_name']}")
        start = time.time()

        try:
            details = client.get_course_details(course['lid'])
            elapsed = time.time() - start

            hw_count = details['total_count']
            print(f"      ✓ 成功 (耗时: {elapsed:.2f}秒, 作业数: {hw_count})")

            if hw_count > 0:
                hw = details['homework_list'][0]
                print(f"      示例作业: {hw.get('title', '无标题')}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"      ✗ 失败 (耗时: {elapsed:.2f}秒)")
            print(f"      错误: {str(e)[:50]}...")

        print()

    print("="*60)
    print("测试完成！")
    print("="*60)
    print("\n如果所有测试都成功，说明延迟修复已生效！")
    print("如果仍有失败，可以尝试增加延迟时间。")

if __name__ == "__main__":
    try:
        quick_test()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试出现异常: {e}")
        import traceback
        traceback.print_exc()

