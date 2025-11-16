import sys
import os
import getpass

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.client import BUCTClient

def main():
    print("=== 测试新函数 get_homework_detail_special1 ===")
    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTClient()
    if client.login(username, password):
        print("\n✅ 登录成功！")
        courseId = "39383"
        print(f"\n⏳ 正在获取课程作业信息 (courseId: {courseId})...")

        try:
            print("\n--- 直接调用 get_homework_detail_special1 ---")
            special_results = client.course_utils.get_homework_detail_special1(courseId)
            print(f"找到子页面作业结果共: {len(special_results)}个")
            for idx, result in enumerate(special_results, 1):
                print(f"  {idx}. 标题: {result.get('title')} | hwtid: {result.get('hwtid')} | columnId: {result.get('column_id')}")

            print("\n--- 经由 get_course_details 检查完整流程 ---")
            course_details = client.course_utils.get_course_details(courseId)
            print(f"作业总数: {course_details.get('total_count')}")
            for idx, hw in enumerate(course_details.get('homework_list', []), 1):
                print(f"  {idx}. 标题: {hw.get('title')} | 截止时间: {hw.get('deadline')} | HWTID: {hw.get('hwtid')}")

        except Exception as e:
            print(f"\n❌ 测试执行失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ 登录失败，请检查账号密码。")

if __name__ == "__main__":
    main()

