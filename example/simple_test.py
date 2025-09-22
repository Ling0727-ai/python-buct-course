"""
简单的模块导入测试
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from buct_course.lid_utils import LidUtils
    print("✅ LidUtils 导入成功")
    
    from buct_course.course_utils import CourseUtils
    print("✅ CourseUtils 导入成功")
    
    from buct_course.test_utils import TestUtils
    print("✅ TestUtils 导入成功")
    
    print("\n所有模块导入成功！")
    
    # 测试基本功能（不需要登录）
    print("\n=== 测试基本功能 ===")
    
    # 模拟一个 session 对象
    class MockSession:
        def get(self, *args, **kwargs):
            pass
    
    mock_session = MockSession()
    
    # 创建工具实例
    lid_utils = LidUtils(mock_session)
    course_utils = CourseUtils(mock_session)
    test_utils = TestUtils(mock_session)
    
    print("✅ 所有工具类实例化成功")
    
    # 测试 LID 从 URL 提取功能
    test_url = "https://course.buct.edu.cn/meol/jpk/course/layout/newpage/index.jsp?courseId=12345"
    lid = lid_utils.get_lid_from_url(test_url)
    print(f"✅ 从 URL 提取 LID: {lid}")
    
    print("\n🎉 所有测试通过！")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}")