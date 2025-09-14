#!/usr/bin/env python3
"""
简单的客户端测试
"""

from buct_course import BUCTClient

def test_client():
    print("=== BUCT客户端测试 ===")
    
    # 创建客户端实例
    client = BUCTClient()
    print("客户端创建成功")
    
    # 测试方法存在
    methods_to_check = ['login', 'logout', 'get_pending_tasks', 'display_welcome']
    for method in methods_to_check:
        if hasattr(client, method):
            print(f"OK - {method} 方法存在")
        else:
            print(f"ERROR - {method} 方法不存在")
    
    # 测试显示欢迎信息
    try:
        client.display_welcome()
        print("OK - display_welcome 方法工作正常")
    except Exception as e:
        print(f"ERROR - display_welcome 出错: {e}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_client()