"""
测试 LID 类型区分功能
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.lid_utils import LidUtils
from buct_course.auth import BUCTAuth

def test_lid_type_distinction():
    """测试 homework 和 test 类型的区分"""
    
    # 模拟 HTML 内容进行测试
    test_html = '''
    <ul id="reminder">
        <li class="licur">
            <a href="###" title="点击查看" class="cur"><span>2</span>门课程有待提交作业</a>
            <ul style="display: block;">
                <li>
                    <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=23479&amp;t=hw','manage_course')" class="cur">
                        普通物理(Ⅱ)
                    </a>
                </li>
                <li>
                    <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=16432&amp;t=hw','manage_course')">
                        马克思主义基本原理
                    </a>
                </li>
            </ul>
        </li>
        
        <li>
            <a href="###" title="点击查看"><span>3</span>门课程有待提交测试</a>
            <ul>
                <li>
                    <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=24199&amp;t=test','manage_course')">
                        大学物理实验(I)
                    </a>
                </li>
                <li>
                    <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=27215&amp;t=test','manage_course')">
                        大学物理实验(II)
                    </a>
                </li>
                <li>
                    <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=16432&amp;t=test','manage_course')">
                        马克思主义基本原理
                    </a>
                </li>
            </ul>
        </li>
    </ul>
    '''
    
    print("=== LID 类型区分测试 ===")
    print("\n预期结果:")
    print("作业课程:")
    print("  - 普通物理(Ⅱ) (LID: 23479, type: homework)")
    print("  - 马克思主义基本原理 (LID: 16432, type: homework)")
    print("\n测试课程:")
    print("  - 大学物理实验(I) (LID: 24199, type: test)")
    print("  - 大学物理实验(II) (LID: 27215, type: test)")
    print("  - 马克思主义基本原理 (LID: 16432, type: test)")
    
    print("\n" + "="*50)
    print("注意：同一门课程可能同时有作业和测试")
    print("例如：马克思主义基本原理 (LID: 16432) 既有作业又有测试")

def main():
    """主函数 - 实际使用示例"""
    try:
        # 1. 登录
        auth = BUCTAuth()
        session = auth.login("your_username", "your_password")
        
        # 2. 获取 LID 工具
        lid_utils = LidUtils(session)
        
        # 3. 获取待办任务
        tasks = lid_utils.get_pending_tasks()
        
        print("=== 实际获取结果 ===")
        print(f"\n作业课程 ({len(tasks['homework'])} 门):")
        for course in tasks['homework']:
            print(f"  - {course['course_name']} (LID: {course['lid']}, type: {course['type']})")
        
        print(f"\n测试课程 ({len(tasks['tests'])} 门):")
        for course in tasks['tests']:
            print(f"  - {course['course_name']} (LID: {course['lid']}, type: {course['type']})")
        
        # 4. 检查是否有课程同时存在作业和测试
        homework_lids = {course['lid'] for course in tasks['homework']}
        test_lids = {course['lid'] for course in tasks['tests']}
        common_lids = homework_lids & test_lids
        
        if common_lids:
            print(f"\n同时有作业和测试的课程 LID: {common_lids}")
            for lid in common_lids:
                hw_course = next((c for c in tasks['homework'] if c['lid'] == lid), None)
                test_course = next((c for c in tasks['tests'] if c['lid'] == lid), None)
                if hw_course and test_course:
                    print(f"  - {hw_course['course_name']} (LID: {lid})")
        
    except Exception as e:
        print(f"获取数据时出错: {e}")
        print("请检查登录信息和网络连接")

if __name__ == "__main__":
    # 先运行测试说明
    test_lid_type_distinction()
    
    print("\n" + "="*60 + "\n")
    
    # 再运行实际示例（需要真实的登录信息）
    # main()