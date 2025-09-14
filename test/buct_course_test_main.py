from buct_course import BUCTAuth, CourseUtils, TestUtils
import datetime

# 配置您的登录信息
USERNAME = input("请输入学号: ")
PASSWORD = input("请输入密码: ")

def display_welcome():
    """显示欢迎信息"""
    print("🚀 北化课程提醒系统")
    print("=" * 60)
    print(f"启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def display_tasks(tasks):
    """显示待办任务"""
    if tasks["success"]:
        print("📊 待办任务统计:")
        print("-" * 40)
        print(f"📝 作业数量: {tasks['data']['stats']['homework_count']}")
        print(f"📋 测试数量: {tasks['data']['stats']['tests_count']}")
        print(f"📈 总计: {tasks['data']['stats']['total_count']}")
        print("-" * 40)
        
        # 显示作业详情
        if tasks['data']['homework']:
            print("\n🎯 待提交作业:")
            for i, hw in enumerate(tasks['data']['homework'], 1):
                print(f"   {i}. {hw['course_name']}")
                print(f"      📍 ID: {hw['lid']}")
                if hw.get('url'):
                    print(f"      🔗 链接: {hw['url']}")
                print()
        else:
            print("\n✅ 暂无待提交作业")
        
        # 显示测试详情（简化显示）
        if tasks['data']['tests']:
            print("🧪 待提交测试:")
            for i, test in enumerate(tasks['data']['tests'], 1):
                print(f"   {i}. {test['course_name']} (ID: {test['lid']})")
            print()
        else:
            print("\n✅ 暂无待提交测试")
    else:
        print("❌ 获取任务失败")

def display_test_details(test_utils, cate_id="34060"):
    """显示测试详细信息"""
    try:
        print("\n" + "=" * 60)
        print("🔍 测试详细信息:")
        
        result = test_utils.get_tests_by_category(cate_id)
        
        if result["success"]:
            print(f"📊 测试统计: 总共 {result['data']['stats']['total_tests']} 个测试")
            print(f"✅ 可进行: {result['data']['stats']['available_tests']} 个")
            print(f"❌ 已完成: {result['data']['stats']['completed_tests']} 个")
            print("-" * 40)
            
            if result['data']['tests']:
                for test in result['data']['tests']:
                    status = "🟢 可进行" if test.get('can_take_test') else "🔴 不可进行"
                    print(f"{status} {test.get('title', '无标题')}")
                    if test.get('date'):
                        print(f"   📅 创建日期: {test['date']}")
                    if test.get('deadline'):
                        print(f"   ⏰ 截止时间: {test['deadline']}")
                    if test.get('status_text'):
                        print(f"   📋 状态: {test['status_text']}")
                    if test.get('test_link') and test.get('can_take_test'):
                        print(f"   🔗 测试链接: {test['test_link']}")
                    print()
            else:
                print("📭 暂无测试信息")
        else:
            print("❌ 获取测试信息失败")
            
    except Exception as e:
        print(f"⚠️  获取测试信息时出错: {e}")

def main():
    display_welcome()
    
    try:
        # 初始化认证
        auth = BUCTAuth()
        
        # 登录
        if auth.login(USERNAME, PASSWORD):
            print("✅ 登录成功!")
            print()
            
            # 获取session
            session = auth.get_session()
            
            # 获取待办任务
            course_utils = CourseUtils(session)
            tasks = course_utils.get_pending_tasks()
            
            display_tasks(tasks)
            
            # 获取测试详细信息
            test_utils = TestUtils(session)
            display_test_details(test_utils)
            
            print("=" * 60)
            print("🎉 任务完成!")
            print(f"完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        else:
            print("❌ 登录失败! 请检查用户名和密码")
            
    except Exception as e:
        print(f"\n💥 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()