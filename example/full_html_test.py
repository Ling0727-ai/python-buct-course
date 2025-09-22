"""
测试完整 HTML 网页解析功能
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup
from buct_course.lid_utils import LidUtils

def test_full_html_parsing():
    """测试完整 HTML 网页的解析"""
    
    # 模拟完整的网页 HTML
    full_html = '''
    <!DOCTYPE html>
    <html>
    <head><title>北化课程平台</title></head>
    <body>
        <div class="content">
            <ul id="reminder">
                <li class="licur"><a href="###" title="点击查看" class="cur"><span>2</span>门课程有待提交作业</a>
                    <ul style="display: block;">
                        <li>
                            <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=23479&amp;t=hw','manage_course')" class="cur">
                                普通物理(Ⅱ)
                        </a></li>
                        <li>
                            <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=16432&amp;t=hw','manage_course')">
                                马克思主义基本原理
                        </a></li>
                    </ul>
                </li>
                
                <li><a href="###" title="点击查看"><span>3</span>门课程有待提交测试</a>
                    <ul>
                        <li>  <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=24199&amp;t=test','manage_course')">
                            大学物理实验(I)</a></li>
                        <li>  <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=27215&amp;t=test','manage_course')">
                            大学物理实验(II)</a></li>
                        <li>  <a href="###" onclick="window.open('./lesson/enter_course.jsp?lid=16432&amp;t=test','manage_course')">
                            马克思主义基本原理</a></li>
                    </ul>
                </li>
            </ul>
        </div>
    </body>
    </html>
    '''
    
    print("=== 完整 HTML 网页解析测试 ===")
    
    # 模拟 session
    class MockSession:
        def get(self, *args, **kwargs):
            class MockResponse:
                def __init__(self, html_content):
                    self.text = html_content
                def raise_for_status(self):
                    pass
            return MockResponse(full_html)
    
    # 创建 LidUtils 实例
    mock_session = MockSession()
    lid_utils = LidUtils(mock_session)
    
    try:
        # 测试解析功能
        tasks = lid_utils.get_pending_tasks()
        
        print(f"\n✅ 解析成功！")
        print(f"作业课程数量: {len(tasks['homework'])}")
        print(f"测试课程数量: {len(tasks['tests'])}")
        
        print(f"\n📚 作业课程:")
        for course in tasks['homework']:
            print(f"  - {course['course_name']} (LID: {course['lid']}, type: {course['type']})")
        
        print(f"\n🧪 测试课程:")
        for course in tasks['tests']:
            print(f"  - {course['course_name']} (LID: {course['lid']}, type: {course['type']})")
        
        print(f"\n🎉 完整 HTML 解析测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_html_parsing()