"""
测试获取和解析示例
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.lid_utils import LidUtils
from buct_course.test_utils import TestUtils
from buct_course.auth import BUCTAuth

def main():
    # 1. 登录
    auth = BUCTAuth()
    session = auth.login("your_username", "your_password")
    
    # 2. 获取测试课程 LID
    lid_utils = LidUtils(session)
    test_utils = TestUtils(session)
    
    # 获取待提交测试的课程列表
    test_courses = test_utils.get_pending_tests()
    print("待提交测试的课程:")
    for course in test_courses:
        print(f"  - {course['course_name']} (LID: {course['lid']})")
    
    # 3. 解析测试详情
    if test_courses:
        # 选择第一个课程作为示例
        first_course = test_courses[0]
        lid = first_course['lid']
        course_name = first_course['course_name']
        
        print(f"\n正在获取课程 '{course_name}' 的测试列表...")
        
        # 获取测试列表
        test_details = test_utils.get_test_list(lid)
        
        print(f"课程 LID: {test_details['lid']}")
        print(f"测试总数: {test_details['total_count']}")
        
        # 显示每个测试的信息
        test_list = test_details.get('test_list', [])
        for test in test_list:
            print(f"\n测试: {test['title']}")
            print(f"  开始时间: {test.get('start_time', 'N/A')}")
            print(f"  结束时间: {test.get('end_time', 'N/A')}")
            print(f"  持续时间: {test.get('duration', 'N/A')}")
            print(f"  状态: {test.get('status', 'N/A')}")
            print(f"  分数: {test.get('score', 'N/A')}")
            print(f"  可以开始: {'是' if test.get('can_start', False) else '否'}")
            
            if test.get('can_start') and test.get('start_href'):
                print(f"  开始链接: {test['start_href']}")

def get_specific_course_tests():
    """根据课程名称获取测试"""
    auth = BUCTAuth()
    session = auth.login("your_username", "your_password")
    
    lid_utils = LidUtils(session)
    test_utils = TestUtils(session)
    
    # 根据课程名称查找 LID
    course_name = "数学"  # 部分匹配
    lid = lid_utils.find_lid_by_course_name(course_name)
    
    if lid:
        print(f"找到课程 LID: {lid}")
        
        # 获取测试列表
        test_details = test_utils.get_test_list(lid)
        
        # 处理测试信息...
        print(f"测试总数: {test_details['total_count']}")
        
        # 获取第一个测试的详细信息
        test_list = test_details.get('test_list', [])
        if test_list:
            first_test = test_list[0]
            if isinstance(first_test, dict) and 'test_id' in first_test:
                test_detail = test_utils.get_test_detail(first_test['test_id'])
                print(f"\n测试详情:")
                print(f"  标题: {test_detail['title']}")
                print(f"  描述: {test_detail['description']}")
                print(f"  开始时间: {test_detail['start_time']}")
                print(f"  结束时间: {test_detail['end_time']}")
                print(f"  持续时间: {test_detail['duration']}")
                print(f"  总分: {test_detail['total_score']}")
    else:
        print(f"未找到包含 '{course_name}' 的课程")

if __name__ == "__main__":
    main()
    print("\n" + "="*50 + "\n")
    get_specific_course_tests()