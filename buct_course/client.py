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
            # 如果之前有登录过，先清理旧的状态
            if self.auth and self.auth.is_logged_in():
                self.logout()

            # 重新创建auth对象，确保使用全新的session
            self.auth = BUCTAuth()

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
        
        try:
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
                                    'is_group': hw.get('is_group', False),
                                    'detail_href': hw.get('detail_href', ''),
                                    'submit_href': hw.get('submit_href', '')
                                }
                                detailed_homework.append(hw_info)
                    except Exception as e:
                        print(f"⚠️  获取课程 {course.get('course_name')} 详情失败: {e}")
                        continue
            
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
        except Exception as e:
            print(f"❌ 获取待办任务失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {
                    "homework": [],
                    "tests": [],
                    "stats": {
                        "homework_count": 0,
                        "tests_count": 0,
                        "total_count": 0
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

        try:
            # 获取有待处理测试的课程
            pending_test_courses = self.test_utils.get_pending_tests()

            all_detailed_tests = []

            # 遍历每个课程，获取详细的测试列表
            for course in pending_test_courses:
                lid = course.get('lid')
                course_name = course.get('course_name', '未知课程')
                if not lid:
                    continue

                try:
                    # 获取该课程下的所有测试
                    test_list_data = self.test_utils.get_test_list(lid)
                    
                    # 过滤出可进行的测试
                    available_tests = self.test_utils.filter_available_tests(test_list_data.get('test_list', []))

                    # 为每个测试添加课程名称
                    for test_detail in available_tests:
                        test_detail['course_name'] = course_name
                        test_detail['lid'] = lid
                        all_detailed_tests.append(test_detail)

                except Exception as e:
                    print(f"⚠️  获取课程 '{course_name}' (lid: {lid}) 的测试列表失败: {e}")

            # 格式化测试信息以供显示
            formatted_tests = []
            available_count = 0
            completed_count = 0

            for test in all_detailed_tests:
                can_take = test.get('can_start', False)
                status = test.get('status', '').strip()

                if can_take:
                    available_count += 1

                if '已完成' in status or '已提交' in status or test.get('has_result', False):
                    completed_count += 1

                # 优先保留页面真实入口；不可把 columnId/testId 当成课程 ID。
                test_lid = test.get('lid', '')
                test_link = test.get('test_link') or test.get('source_url') or (
                    f"{self.test_utils.base_url}/meol/common/question/test/student/list.jsp?cateId={test_lid}"
                )

                formatted_tests.append({
                    "title": test.get('title', '未知测试'),
                    "course_name": test.get('course_name', '未知课程'),
                    "date": test.get('start_time', '未知'),
                    "deadline": test.get('end_time', '未知'),
                    "status_text": status,
                    "can_take_test": can_take,
                    "test_link": test_link,
                    "test_id": test.get('test_id', ''),
                    "lid": test_lid,
                    "source_url": test.get('source_url', test_link),
                    "duration": test.get('duration', '未知'),
                    "allowed_attempts": test.get('allowed_attempts', '未知')
                })

            return {
                "success": True,
                "data": {
                    "tests": formatted_tests,
                    "stats": {
                        "total_tests": len(formatted_tests),
                        "available_tests": available_count,
                        "completed_tests": completed_count
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
    
    def get_homework_tasks(self, homework_detail_url):
        """
        获取作业详细任务要求
        
        Args:
            homework_detail_url: 作业详情页面URL
            
        Returns:
            list: 作业任务要求列表
        """
        if not self.course_utils:
            raise LoginError("请先登录")
        
        try:
            return self.course_utils.get_homework_tasks(homework_detail_url)
        except Exception as e:
            print(f"❌ 获取作业任务详情失败: {e}")
            return []
    
    def get_homework_with_tasks(self):
        """
        获取包含详细任务要求的作业信息
        
        Returns:
            dict: 包含作业和任务详情的完整信息
        """
        if not self.course_utils:
            raise LoginError("请先登录")
        
        tasks = self.get_pending_tasks()
        if not tasks["success"]:
            return tasks
        
        homework_with_tasks = []
        for hw in tasks['data']['homework']:
            hw_with_tasks = hw.copy()
            
            # 获取作业任务详情
            detail_href = hw.get('detail_href')
            if detail_href:
                try:
                    tasks_info = self.get_homework_tasks(detail_href)
                    hw_with_tasks['tasks'] = tasks_info
                    hw_with_tasks['tasks_count'] = len(tasks_info)
                except Exception as e:
                    print(f"⚠️  获取作业 {hw.get('title', '未知')} 的任务详情失败: {e}")
                    hw_with_tasks['tasks'] = []
                    hw_with_tasks['tasks_count'] = 0
            else:
                hw_with_tasks['tasks'] = []
                hw_with_tasks['tasks_count'] = 0
            
            homework_with_tasks.append(hw_with_tasks)
        
        return {
            "success": True,
            "data": {
                "homework": homework_with_tasks,
                "tests": tasks['data']['tests'],
                "stats": {
                    "homework_count": len(homework_with_tasks),
                    "tests_count": tasks['data']['stats']['tests_count'],
                    "total_count": len(homework_with_tasks) + tasks['data']['stats']['tests_count']
                }
            }
        }
    
    def display_welcome(self):
        """显示欢迎信息"""
        print("== 北化课程提醒系统 ==")
        print("=" * 60)
        print(f"启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def display_homework_with_tasks(self, homework_with_tasks=None):
        """显示包含详细任务要求的作业信息"""
        if homework_with_tasks is None:
            homework_with_tasks = self.get_homework_with_tasks()
        
        if homework_with_tasks["success"]:
            homework_list = homework_with_tasks['data']['homework']
            print(f"🎯 详细作业信息 (共 {len(homework_list)} 个):")
            print("=" * 60)
            
            for i, hw in enumerate(homework_list, 1):
                print(f"\n📝 作业 {i}: {hw.get('title', '未知作业')}")
                print(f"📚 课程: {hw.get('course_name', '未知课程')}")
                print(f"⏰ 截止时间: {hw.get('deadline', '未知')}")
                print(f"👥 分组作业: {'是' if hw.get('is_group') else '否'}")
                print(f"📍 作业ID: {hw.get('hwtid', '未知')}")
                
                # 显示作业任务详情
                tasks = hw.get('tasks', [])
                if tasks:
                    print(f"\n📋 作业要求 ({len(tasks)} 项):")
                    for j, task in enumerate(tasks, 1):
                        # 限制每行显示长度，避免过长
                        task_text = task[:100] + "..." if len(task) > 100 else task
                        print(f" {task_text}")
                else:
                    print("\n⚠️  暂无详细作业要求")
                
                print("-" * 50)
        else:
            print("❌ 获取详细作业信息失败")
    
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
                    # 获取课程名称
                    course_name = result['data'].get('course_name', '未知课程')
                    
                    # 使用 test_utils 的显示方法
                    self.test_utils.display_test_details(result['data']['tests'], course_name)
                else:
                    print("📭 暂无测试信息")
            else:
                print("❌ 获取测试信息失败")
                
        except Exception as e:
            print(f"⚠️  获取测试信息时出错: {e}")
    
    def run_interactive(self):
        """运行交互式客户端 - 优化版本，避免重复显示"""
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
        
        # 显示统计信息
        if tasks["success"]:
            print("📊 待办任务统计:")
            print("-" * 40)
            print(f"📝 作业数量: {tasks['data']['stats']['homework_count']}")
            print(f"📋 测试数量: {tasks['data']['stats']['tests_count']}")
            print(f"📈 总计: {tasks['data']['stats']['total_count']}")
            print("-" * 40)
        
        # 显示详细作业信息（包含任务要求）
        if tasks["success"] and tasks['data']['homework']:
            print("\n📋 正在获取详细作业要求...")
            self.display_homework_with_tasks()
        elif tasks["success"]:
            print("\n✅ 暂无待提交作业")
        
        # 显示测试信息
        if tasks["success"] and tasks['data']['tests']:
            print("\n🧪 待提交测试:")
            for i, test in enumerate(tasks['data']['tests'], 1):
                print(f"   {i}. {test['course_name']} (ID: {test['lid']})")
            print()
        elif tasks["success"]:
            print("\n✅ 暂无待提交测试")
        
        # 获取测试详细信息
        self.display_test_details()
        
        print("=" * 60)
        print("🎉 任务完成!")
        print(f"完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 提供便捷的工厂函数
def create_client(username=None, password=None):
    """创建BUCT客户端实例"""
    return BUCTClient(username, password)