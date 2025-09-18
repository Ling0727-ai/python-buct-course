"""
北化课程平台API库
提供北京化工大学课程平台的自动化操作接口
"""

from .auth import BUCTAuth
from .course_utils import CourseUtils
from .test_utils import TestUtils
from .exceptions import BUCTCourseError, LoginError, NetworkError, ParseError
from .client import BUCTClient, create_client

__version__ = "0.3.1"
__all__ = [
    'BUCTAuth', 'CourseUtils', 'TestUtils', 'BUCTClient', 'create_client',
    'BUCTCourseError', 'LoginError', 'NetworkError', 'ParseError'
]

# 提供便捷的导入方式
def create_session(username, password):
    """快速创建认证会话"""
    auth = BUCTAuth()
    if auth.login(username, password):
        return auth.get_session()
    raise LoginError("登录失败")

def get_pending_tasks(username, password):
    """快速获取待办任务"""
    session = create_session(username, password)
    course_utils = CourseUtils(session)
    return course_utils.get_pending_tasks()

def get_tests_by_category(username, password, cate_id, **kwargs):
    """快速获取分类测试"""
    session = create_session(username, password)
    test_utils = TestUtils(session)
    return test_utils.get_tests_by_category(cate_id, **kwargs)

def get_available_tests(username, password, cate_id, **kwargs):
    """快速获取可用测试"""
    session = create_session(username, password)
    test_utils = TestUtils(session)
    return test_utils.get_available_tests(cate_id, **kwargs)

def get_test_categories(username, password):
    """快速获取测试分类"""
    session = create_session(username, password)
    test_utils = TestUtils(session)
    return test_utils.get_test_categories()

def take_test(username, password, test_id):
    """快速开始测试"""
    session = create_session(username, password)
    test_utils = TestUtils(session)
    return test_utils.take_test(test_id)

def get_test_results(username, password, test_id):
    """快速获取测试结果"""
    session = create_session(username, password)
    test_utils = TestUtils(session)
    return test_utils.get_test_results(test_id)