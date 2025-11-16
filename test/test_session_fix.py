"""
测试会话过期和重新登录的场景
验证6小时自动登出后重新登录不会出现旧会话问题
"""

from buct_course import BUCTClient
import time

def test_session_relogin():
    """测试会话重新登录功能"""
    print("=" * 60)
    print("测试场景：会话过期后重新登录")
    print("=" * 60)

    # 模拟场景：用户第一次登录
    print("\n第一步：首次登录")
    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTClient(username, password)

    if not client.auth.is_logged_in():
        print("❌ 首次登录失败")
        return

    print("✅ 首次登录成功")
    print(f"Session ID: {id(client.session)}")
    print(f"Auth ID: {id(client.auth)}")

    # 模拟获取一些数据
    print("\n第二步：获取待办任务")
    try:
        tasks = client.get_pending_tasks()
        if tasks.get("success"):
            print(f"✅ 成功获取任务: {tasks['data']['stats']['total_count']} 个")
        else:
            print("⚠️  获取任务返回失败状态")
    except Exception as e:
        print(f"❌ 获取任务失败: {e}")

    # 模拟用户退出登录（或会话过期）
    print("\n第三步：模拟退出登录（或会话过期6小时）")
    old_session_id = id(client.session)
    old_auth_id = id(client.auth)
    client.logout()
    print("✅ 已退出登录")

    # 等待一小段时间，模拟用户离开
    print("\n第四步：等待一段时间（模拟用户离开页面）")
    time.sleep(2)

    # 用户返回，重新登录
    print("\n第五步：重新登录（不刷新页面的情况）")
    if client.login(username, password):
        print("✅ 重新登录成功")
        new_session_id = id(client.session)
        new_auth_id = id(client.auth)

        print(f"\n会话对象变化:")
        print(f"  旧 Session ID: {old_session_id}")
        print(f"  新 Session ID: {new_session_id}")
        print(f"  Session已更新: {'✅ 是' if old_session_id != new_session_id else '❌ 否（可能存在问题）'}")

        print(f"\n认证对象变化:")
        print(f"  旧 Auth ID: {old_auth_id}")
        print(f"  新 Auth ID: {new_auth_id}")
        print(f"  Auth已更新: {'✅ 是' if old_auth_id != new_auth_id else '❌ 否（可能存在问题）'}")

        # 再次尝试获取数据
        print("\n第六步：使用新会话获取数据")
        try:
            tasks = client.get_pending_tasks()
            if tasks.get("success"):
                print(f"✅ 成功使用新会话获取任务: {tasks['data']['stats']['total_count']} 个")
                print("\n🎉 测试通过！会话重新登录功能正常")
            else:
                print("⚠️  获取任务返回失败状态")
        except Exception as e:
            print(f"❌ 获取任务失败: {e}")
            print("⚠️  可能仍存在会话问题")
    else:
        print("❌ 重新登录失败")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

def test_multiple_relogin():
    """测试多次登录登出"""
    print("=" * 60)
    print("测试场景：多次登录登出")
    print("=" * 60)

    username = input("请输入学号: ")
    password = input("请输入密码: ")

    client = BUCTClient()

    for i in range(3):
        print(f"\n第 {i + 1} 轮登录")

        if client.login(username, password):
            print(f"  ✅ 登录成功 (Session ID: {id(client.session)})")

            try:
                tasks = client.get_pending_tasks()
                if tasks.get("success"):
                    print(f"  ✅ 获取数据成功")
                else:
                    print(f"  ⚠️  获取数据失败")
            except Exception as e:
                print(f"  ❌ 获取数据异常: {e}")

            client.logout()
            print(f"  ✅ 退出登录")

            time.sleep(1)
        else:
            print(f"  ❌ 登录失败")
            break

    print("\n" + "=" * 60)
    print("多轮测试完成")
    print("=" * 60)

if __name__ == "__main__":
    print("\n请选择测试场景:")
    print("1. 测试会话过期后重新登录")
    print("2. 测试多次登录登出")

    choice = input("\n请输入选项 (1 或 2): ").strip()

    if choice == "1":
        test_session_relogin()
    elif choice == "2":
        test_multiple_relogin()
    else:
        print("无效选项")

