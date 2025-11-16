"""
测试添加延迟后的性能改进
"""
import time
from buct_course import BUCTCourseClient

def test_with_delays():
    """测试添加延迟后获取作业详情"""

    # 需要提供真实的学号和密码
    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTCourseClient(username, password)

    print("\n正在登录...")
    if client.login():
        print("✓ 登录成功！")

        print("\n正在获取待提交作业列表...")
        pending = client.get_pending_homework()
        print(f"✓ 找到 {len(pending)} 门有待提交作业的课程")

        if pending:
            # 测试获取第一门课程的详细信息
            first_course = pending[0]
            print(f"\n正在获取课程详情: {first_course['course_name']}")

            start_time = time.time()
            details = client.get_course_details(first_course['lid'])
            end_time = time.time()

            print(f"✓ 获取成功，耗时: {end_time - start_time:.2f}秒")
            print(f"  作业数量: {details['total_count']}")

            # 测试批量获取所有课程详情
            print("\n正在批量获取所有课程的作业详情...")
            start_time = time.time()
            all_details = client.get_all_pending_homework_details()
            end_time = time.time()

            total_homework = sum(course['total_count'] for course in all_details)
            total_urgent = sum(course['urgent_count'] for course in all_details)

            print(f"✓ 批量获取成功，耗时: {end_time - start_time:.2f}秒")
            print(f"  总课程数: {len(all_details)}")
            print(f"  总作业数: {total_homework}")
            print(f"  紧急作业: {total_urgent}")

            # 显示每门课程的详情
            print("\n各课程作业详情:")
            for course in all_details:
                print(f"\n  课程: {course['course_name']}")
                print(f"    作业数: {course['total_count']}")
                print(f"    紧急作业: {course['urgent_count']}")

                if course['homework_list']:
                    print("    作业列表:")
                    for hw in course['homework_list'][:3]:  # 只显示前3个
                        print(f"      - {hw['title']}")
                        print(f"        截止时间: {hw.get('deadline', '无')}")
                        print(f"        剩余时间: {hw.get('time_remaining', '无')}")

        print("\n✓ 所有测试完成！")
    else:
        print("✗ 登录失败")

if __name__ == "__main__":
    test_with_delays()

