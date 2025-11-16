"""
作业获取和解析示例
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.lid_utils import LidUtils
from buct_course.course_utils import CourseUtils
from buct_course.auth import BUCTAuth

def main():
    # 1. 登录
    auth = BUCTAuth()
    session = auth.login("your_username", "your_password")
    
    # 2. 获取课程 LID
    lid_utils = LidUtils(session)
    
    # 获取待提交作业的课程列表
    homework_courses = lid_utils.get_homework_lids()
    print("待提交作业的课程:")
    for course in homework_courses:
        print(f"  - {course['course_name']} (LID: {course['lid']})")
    
    # 3. 解析作业详情
    course_utils = CourseUtils(session)
    
    if homework_courses:
        # 选择第一个课程作为示例
        first_course = homework_courses[0]
        lid = first_course['lid']
        course_name = first_course['course_name']
        
        print(f"\n正在获取课程 '{course_name}' 的作业列表...")
        
        # 获取作业列表
        course_details = course_utils.get_course_details(lid)
        
        print(f"课程 LID: {course_details['lid']}")
        print(f"作业总数: {course_details['total_count']}")
        
        # 显示每个作业的信息
        for homework in course_details['homework_list']:
            print(f"\n作业: {homework['title']}")
            print(f"  截止时间: {homework['deadline']}")
            print(f"  分数: {homework['score']}")
            print(f"  发布人: {homework['publisher']}")
            print(f"  是否分组作业: {'是' if homework['is_group'] else '否'}")
            print(f"  可以提交: {'是' if homework['can_submit'] else '否'}")
            print(f"  有结果: {'是' if homework['has_result'] else '否'}")
            
            if homework['can_submit']:
                print(f"  提交链接: {homework['submit_href']}")
            
            if homework['has_result']:
                print(f"  结果链接: {homework['result_href']}")
            
            if 'status' in homework:
                print(f"  状态: {homework['status']}")

def get_specific_course_homework():
    """根据课程名称获取作业"""
    auth = BUCTAuth()
    session = auth.login("your_username", "your_password")
    
    lid_utils = LidUtils(session)
    course_utils = CourseUtils(session)
    
    # 根据课程名称查找 LID
    course_name = "机械"  # 部分匹配
    lid = lid_utils.find_lid_by_course_name(course_name)
    
    if lid:
        print(f"找到课程 LID: {lid}")
        
        # 获取作业列表
        course_details = course_utils.get_course_details(lid)
        
        # 处理作业信息...
        print(f"作业总数: {course_details['total_count']}")
    else:
        print(f"未找到包含 '{course_name}' 的课程")

if __name__ == "__main__":
    main()
    print("\n" + "="*50 + "\n")
    get_specific_course_homework()