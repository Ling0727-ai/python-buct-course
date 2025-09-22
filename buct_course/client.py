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
        
        # 获取待提交作业和测试
        homework_courses = self.course_utils.get_pending_homework()
        tests = self.test_utils.get_pending_tests()
        
        # 获取每个课程的详细作业信息
        detailed_homework = []
        for course in homework_courses:
            lid = course.get('lid')
            if lid:
                try:
                    # 获取该课程的作业详情
                    course_details = self.course_utils.get_course_details(lid)
                    homework_list = course_details.get('homework_list', [])
                    
                    # 为每个作业添加课程信息，只保留未完成且未超时的作业
                    for hw in homework_list:
                        # 过滤条件：可以提交的作业（未完成且未超时）
                        if hw.get('can_submit', False):
                            hw_info = {
                                'course_name': course.get('course_name', '未知课程'),
                                'lid': lid,
                                'url': course.get('url', ''),
                                'title': hw.get('title', ''),
                                'deadline': hw.get('deadline', '未知'),
                                'hwtid': hw.get('hwtid', ''),
                                'score': hw.get('score', ''),
                                'publisher': hw.get('publisher', ''),
                                'can_submit': hw.get('can_submit', False),
                                'is_group': hw.get('is_group', False)
                            }
                            detailed_homework.append(hw_info)
                except Exception as e:
                    print(f"获取课程 {course.get('course_name')} 详情失败: {e}")
                    # 如果获取详情失败，至少保留课程基本信息
                    detailed_homework.append({
                        'course_name': course.get('course_name', '未知课程'),
                        'lid': lid,
                        'url': course.get('url', ''),
                        'deadline': '获取失败'
                    })
        
        # 构造返回格式以兼容原有接口
        return {
            "success": True,
            "data": {
                "homework": detailed_homework,
                "tests": tests,
                "stats": {
                    "homework_count": len(detailed_homework),
                    "tests_count": len(tests),
                    "total_count": len(detailed_homework) + len(tests)
                }
            }
        }
    
    def get_test_categories(self):
        """获取测试分类"""
        if not self.test_utils:
            raise LoginError("请先登录")
        # 返回模拟的测试分类数据
        return {
            "success": True,
            "data": {
                "categories": [
                    {"id": "34060", "name": "默认分类"}
                ]
            }
        }
    
    def get_tests_by_category(self, cate_id, **kwargs):
        """按分类获取测试"""
        if not self.test_utils:
            raise LoginError("请先登录")
        
        # 获取待提交测试并格式化返回
        try:
            pending_tests = self.test_utils.get_pending_tests()
            
            # 构造兼容的返回格式
            formatted_tests = []
            for test in pending_tests:
                # 使用正确的测试链接格式
                course_id = test.get('course_id', '')
                test_link = f"https://course.buct.edu.cn/meol/common/question/test/student/list.jsp?sortColumn=createTime&status=1&tagbug=client&sortDirection=-1&strStyle=lesson19&cateId={course_id}&pagingPage=1&pagingNumberPer=7"
                
                formatted_tests.append({
                    "title": test.get('course_name', '未知测试'),
                    "date": "2025-09-22",
                    "deadline": "待查询",
                    "status_text": "可进行",
                    "can_take_test": True,
                    "test_link": test_link
                })
            
            return {
                "success": True,
                "data": {
                    "tests": formatted_tests,
                    "stats": {
                        "total_tests": len(formatted_tests),
                        "available_tests": len(formatted_tests),
                        "completed_tests": 0
                    }
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_available_tests(self, cate_id, **kwargs):
        """获取可用测试"""
        return self.get_tests_by_category(cate_id, **kwargs)
    
    def take_test(self, test_id):
        """开始测试"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return {"success": False, "message": "测试功能暂未实现"}
    
    def get_test_results(self, test_id):
        """获取测试结果"""
        if not self.test_utils:
            raise LoginError("请先登录")
        return {"success": False, "message": "测试结果查询功能暂未实现"}
    
    def get_courses(self):
        """获取所有课程"""
        if not self.course_utils:
            raise LoginError("请先登录")
        # 使用现有的方法获取课程
        return self.course_utils.get_pending_homework()
    
    def get_course_content(self, course_id):
        """获取课程内容"""
        if not self.course_utils:
            raise LoginError("请先登录")
        # 使用现有的方法获取课程详情
        return self.course_utils.get_course_details(course_id)
    
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
                    if hw.get('title'):
                        print(f"      📝 作业: {hw['title']}")
                    print(f"      📍 ID: {hw['lid']}")
                    if hw.get('deadline') and hw['deadline'] not in ['未知', '获取失败']:
                        print(f"      ⏰ 截止时间: {hw['deadline']}")
                    elif hw.get('deadline') == '获取失败':
                        print(f"      ⚠️  截止时间: 获取失败")
                    if hw.get('score'):
                        print(f"      📊 分数: {hw['score']}")
                    if hw.get('is_group'):
                        print(f"      👥 分组作业")
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