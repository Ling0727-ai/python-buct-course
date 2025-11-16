"""
        traceback.print_exc()
        import traceback
        print(f"\n\n发生错误: {e}")
    except Exception as e:
        print("\n\n程序被用户中断")
    except KeyboardInterrupt:
        test_management_example()
    try:
if __name__ == "__main__":

        traceback.print_exc()
        import traceback
        print(f"✗ 获取测试列表失败: {e}")
    except Exception as e:
        
        print("   建议及时完成测试，避免错过截止时间")
        print("   测试信息来自课程平台的待办提醒")
        print("\n💡 提示:")
        
            print("-" * 70)
            
                print(f"  链接: {test['url']}")
            if test.get('url'):
            
            print(f"  类型: {test.get('type', '未知')}")
            print(f"  课程ID: {test.get('lid', '未知')}")
            print(f"  课程名称: {test.get('course_name', '未知')}")
            print(f"\n【测试 {i}】")
        for i, test in enumerate(tests, 1):
        
        print("=" * 70)
        print("📝 测试列表")
        print("=" * 70)
        print(f"✓ 找到 {len(tests)} 个待进行的测试\n")
        
            return
            print("✓ 太棒了！目前没有待进行的测试")
        if not tests:
        
        tests = client.get_pending_tests()
    try:
    
    print("正在获取待进行的测试列表...")
    # 获取待进行的测试列表
    
    print("✓ 登录成功！\n")
    
        return
        print("✗ 登录失败")
    if not client.login():
    print("\n正在登录...")
    
    client = BUCTCourseClient(username, password)
    
    password = input("请输入密码: ")
    username = input("请输入学号: ")
    # 创建并登录
    
    """测试管理示例"""
def test_management_example():

from buct_course import BUCTCourseClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加项目根目录到 Python 路径

import os
import sys
"""
展示如何获取和管理待进行的测试
示例 5: 测试管理

