#!/usr/bin/env python3
"""
BUCT客户端使用示例
演示如何使用新的BUCTClient类
"""

from buct_course import BUCTClient

def demo_client():
    """演示客户端使用"""
    
    # 方法1: 直接创建并运行交互式客户端
    print("=== 方法1: 交互式客户端 ===")
    client = BUCTClient()
    client.run_interactive()
    
    print("\n" + "="*60)
    
    # 方法2: 程序化使用
    print("=== 方法2: 程序化使用 ===")
    
    # 需要先输入凭据
    username = input("请输入学号: ")
    password = input("请输入密码: ")
    
    # 创建客户端并登录
    client = BUCTClient(username, password)
    
    # 获取待办任务
    tasks = client.get_pending_tasks()
    if tasks["success"]:
        print(f"待办任务总数: {tasks['data']['stats']['total_count']}")
        print(f"作业数量: {tasks['data']['stats']['homework_count']}")
        print(f"测试数量: {tasks['data']['stats']['tests_count']}")
    
    # 获取测试信息
    tests = client.get_tests_by_category("34060")
    if tests["success"]:
        print(f"测试总数: {tests['data']['stats']['total_tests']}")
        print(f"可进行测试: {tests['data']['stats']['available_tests']}")
    
    # 退出登录
    client.logout()
    print("✅ 已退出登录")

if __name__ == "__main__":
    demo_client()