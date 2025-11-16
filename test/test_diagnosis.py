"""
诊断和测试脚本 - 检测抓取失败的具体原因
"""
import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import BUCTCourseClient

def test_with_verbose_logging():
    """详细日志测试"""

    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTCourseClient(username, password)

    print("\n" + "="*60)
    print("开始测试 - 带详细日志")
    print("="*60)

    print("\n[1/4] 正在登录...")
    if not client.login():
        print("✗ 登录失败")
        return
    print("✓ 登录成功")

    print("\n[2/4] 正在获取待提交作业列表...")
    try:
        pending = client.get_pending_homework()
        print(f"✓ 找到 {len(pending)} 门有待提交作业的课程")

        if not pending:
            print("没有待提交的作业")
            return

        # 显示课程列表
        for i, course in enumerate(pending, 1):
            print(f"  {i}. {course['course_name']} (LID: {course['lid']})")
    except Exception as e:
        print(f"✗ 获取待提交作业列表失败: {e}")
        return

    print("\n[3/4] 逐个获取课程详情（带详细日志）...")
    success_count = 0
    fail_count = 0

    for i, course in enumerate(pending, 1):
        course_name = course['course_name']
        lid = course['lid']

        print(f"\n  [{i}/{len(pending)}] 正在处理: {course_name}")
        print(f"      LID: {lid}")

        try:
            start_time = time.time()
            print(f"      > 发送请求...")

            details = client.get_course_details(lid)

            end_time = time.time()
            elapsed = end_time - start_time

            homework_count = details.get('total_count', 0)
            print(f"      ✓ 成功获取 (耗时: {elapsed:.2f}秒)")
            print(f"      ✓ 作业数量: {homework_count}")

            if homework_count > 0:
                print(f"      作业列表:")
                for hw in details.get('homework_list', [])[:3]:
                    print(f"        - {hw.get('title', '无标题')}")

            success_count += 1

        except Exception as e:
            fail_count += 1
            print(f"      ✗ 失败: {e}")
            import traceback
            print(f"      详细错误:\n{traceback.format_exc()}")

        # 每个课程之间添加延迟
        if i < len(pending):
            print(f"      等待 1 秒后继续...")
            time.sleep(1)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print(f"成功: {success_count}/{len(pending)}")
    print(f"失败: {fail_count}/{len(pending)}")
    print(f"成功率: {success_count/len(pending)*100:.1f}%")

    if fail_count > 0:
        print("\n建议:")
        print("1. 检查网络连接是否稳定")
        print("2. 尝试增加延迟时间")
        print("3. 检查是否被服务器限制")

if __name__ == "__main__":
    test_with_verbose_logging()

