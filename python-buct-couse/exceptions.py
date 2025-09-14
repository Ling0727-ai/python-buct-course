"""
异常类定义
"""

class BUCTCourseError(Exception):
    """北化课程平台基础异常"""
    pass

class LoginError(BUCTCourseError):
    """登录相关异常"""
    pass

class NetworkError(BUCTCourseError):
    """网络相关异常"""
    pass

class ParseError(BUCTCourseError):
    """解析相关异常"""
    pass

class RateLimitError(BUCTCourseError):
    """速率限制异常"""
    pass