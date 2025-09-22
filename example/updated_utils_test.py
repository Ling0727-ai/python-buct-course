#!/usr/bin/env python3
"""
测试更新后的工具模块
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.lid_utils import LidUtils
from buct_course.course_utils import CourseUtils
from buct_course.test_utils import TestUtils


class MockSession:
    """模拟 session 对象用于测试"""
    
    def __init__(self):
        self.base_url = "https://course.buct.edu.cn"
    
    def get(self, url, **kwargs):
        """模拟 GET 请求"""
        class MockResponse:
            def __init__(self):
                self.text = self._get_mock_html()
                self.status_code = 200
            
            def raise_for_status(self):
                pass
            
            def _get_mock_html(self):
                return """
                <!DOCTYPE html>
                <html>
                <head><title>测试页面</title></head>
                <body>
                    <div class="content">
                        <ul>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=23479&t=hw','manage_course')">普通物理(Ⅱ)</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=16432&t=hw','manage_course')">马克思主义基本原理</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=24199&t=test','manage_course')">大学物理实验(I)</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=27215&t=test','manage_course')">大学物理实验(II)</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=16432&t=test','manage_course')">马克思主义基本原理</a></li>
                        </ul>
                    </div>
                </body>
                </html>
                """
        
        return MockResponse()


def test_updated_utils():
    """测试更新后的工具模块"""
    print("=== 测试更新后的工具模块 ===\n")
    
    # 创建模拟 session
    session = MockSession()
    
    # 测试 LidUtils
    print("📋 测试 LidUtils:")
    lid_utils = LidUtils(session)
    
    try:
        pending_tasks = lid_utils.get_pending_tasks()
        print(f"✅ 获取待办任务成功")
        print(f"   作业数量: {len(pending_tasks['homework'])}")
        print(f"   测试数量: {len(pending_tasks['tests'])}")
        
        homework_lids = lid_utils.get_homework_lids()
        print(f"✅ 获取作业 LID 成功: {len(homework_lids)} 个")
        
        test_lids = lid_utils.get_test_lids()
        print(f"✅ 获取测试 LID 成功: {len(test_lids)} 个")
        
    except Exception as e:
        print(f"❌ LidUtils 测试失败: {str(e)}")
    
    print()
    
    # 测试 CourseUtils
    print("📚 测试 CourseUtils:")
    course_utils = CourseUtils(session)
    
    try:
        pending_homework = course_utils.get_pending_homework()
        print(f"✅ 获取待提交作业成功: {len(pending_homework)} 个")
        
        for hw in pending_homework:
            print(f"   - {hw['course_name']} (LID: {hw['lid']})")
        
    except Exception as e:
        print(f"❌ CourseUtils 测试失败: {str(e)}")
    
    print()
    
    # 测试 TestUtils
    print("🧪 测试 TestUtils:")
    test_utils = TestUtils(session)
    
    try:
        pending_tests = test_utils.get_pending_tests()
        print(f"✅ 获取待提交测试成功: {len(pending_tests)} 个")
        
        for test in pending_tests:
            print(f"   - {test['course_name']} (LID: {test['lid']})")
        
    except Exception as e:
        print(f"❌ TestUtils 测试失败: {str(e)}")
    
    print("\n🎉 工具模块测试完成！")


if __name__ == "__main__":
    test_updated_utils()