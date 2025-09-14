from .auth import BUCTAuth
from .course_utils import CourseUtils
from .test_utils import TestUtils
from .exceptions import BUCTCourseError, LoginError
import datetime

class BUCTClient:
    """北化课程平台客户端，提供便捷的API访问"""
    
    def __init__(self, username=None, password=None):
        self.auth = BUCTAuth()
        self.session = None
        self.course_utils = None
        self.test_utils = None
        self.username = username
        self.password = password
        
        if username and password:
            self.login(username, password)
    
    def login(self, username, password):
        """登录课程平台"""
        self.username = username
        self.password = password
        
        try:
            if self.auth.login(username, password):
                self.session = self.auth.get_session()
                self.course_utils = CourseUtils(self.session)
                self.test_utils = TestUtils(self.session)
                return True
            return False
        except LoginError:
            # 登录失败，返回False而不是抛出异常
            return False
    
    def logout(self):
        """退出登录"""
        if self.auth:
            self.auth.logout()
        self.session = None
        self.course_utils = None
        self.test_utils = None
    
    def get_pending_tasks(self):
        """获取待办任务"""
        if not self.course_utils:
            raise LoginError("请先登录")
        return self.course_utils.get_pending_tasks()
    
    def get_test_categories(self):
        """获取测试分类"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return self.test_utils.get_test_categories()
    
    def get_tests_by_category(self, cate_id, **kwargs):
        """按分类获取测试"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return self.test_utils.get_tests_by_category(cate_id, **kwargs)
    
    def get_available_tests(self, cate_id, **kwargs):
        """获取可用测试"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return self.test_utils.get_available_tests(cate_id, **kwargs)
    
    def take_test(self, test_id):
        """开始测试"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return self.test_utils.take_test(test_id)
    
    def get_test_results(self, test_id):
        """获取测试结果"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return self.test_utils.get_test_results(test_id)
    
    def get_courses(self):
        """获取所有课程"""
        if not self.course_utils:
            raise LoginError("请先登录")
        return self.course_utils.get_courses()
    
    def get_course_content(self, course_id):
        """获取课程内容"""
        if not self.course_utils:
            raise LoginError("请先登录")
        return self.course_utils.get_course_content(course_id)
    
    def display_welcome(self):
        """显示欢迎信息"""
        print("== 北化课程提醒系统 ==")
        print("=" * 60)
        print(f"启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def display_tasks(self, tasks):
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
    
    def display_test_details(self, cate_id="34060"):
        """显示测试详细信息"""
        try:
            print("\n" + "=" * 60)
            print("🔍 测试详细信息:")
            
            result = self.get_tests_by_category(cate_id)
            
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
    
    def run_interactive(self):
        """运行交互式客户端"""
        self.display_welcome()
        
        if not self.session:
            if not self.username or not self.password:
                self.username = input("请输入学号: ")
                self.password = input("请输入密码: ")
            
            max_attempts = 3
            attempts = 0
            
            while attempts < max_attempts:
                if self.login(self.username, self.password):
                    print("登录成功!")
                    print()
                    break
                else:
                    attempts += 1
                    remaining_attempts = max_attempts - attempts
                    
                    if remaining_attempts > 0:
                        print(f"登录失败! 还有 {remaining_attempts} 次尝试机会")
                        # 清空凭据以便重新输入
                        self.username = input("请重新输入学号: ")
                        self.password = input("请重新输入密码: ")
                    else:
                        print("登录失败次数过多，请稍后再试")
                        return
            
            if attempts >= max_attempts:
                return
        
        # 获取待办任务
        tasks = self.get_pending_tasks()
        self.display_tasks(tasks)
        
        # 获取测试详细信息
        self.display_test_details()
        
        print("=" * 60)
        print("🎉 任务完成!")
        print(f"完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 提供便捷的工厂函数
def create_client(username=None, password=None):
    """创建BUCT客户端实例"""
    return BUCTClient(username, password)