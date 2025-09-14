"""
北化课程平台认证模块
"""

import requests
from .exceptions import LoginError, NetworkError

class BUCTAuth:
    """北化课程平台认证类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://course.buct.edu.cn"
        self._is_logged_in = False
    
    def login(self, username, password):
        """
        登录到北化课程平台
        
        Args:
            username: 学号
            password: 密码
            
        Returns:
            bool: 登录是否成功
            
        Raises:
            LoginError: 登录失败时抛出
            NetworkError: 网络错误时抛出
        """
        try:
            login_url = f"{self.base_url}/meol/loginCheck.do"
            response = self.session.post(login_url, data={
                "IPT_LOGINUSERNAME": username,
                "IPT_LOGINPASSWORD": password
            }, timeout=10)
            
            # 检查登录是否成功
            # 假设成功登录会重定向到非登录页，失败则停留在登录页或重定向回登录页
            # 检查最终的URL是否仍然包含"login.do"或"loginCheck.do"
            if "login.do" in response.url or "loginCheck.do" in response.url:
                self._is_logged_in = False
            else:
                self._is_logged_in = True
            
            if not self._is_logged_in:
                # 可以在这里添加更详细的错误信息解析，如果服务器有提供的话
                raise LoginError("登录失败，请检查用户名和密码。")
                
            return self._is_logged_in
            
        except requests.exceptions.Timeout:
            raise NetworkError("登录请求超时")
        except requests.exceptions.ConnectionError:
            raise NetworkError("网络连接错误")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"网络请求错误: {str(e)}")
    
    def get_session(self):
        """
        获取登录后的session
        
        Returns:
            requests.Session: 认证后的会话对象
            
        Raises:
            LoginError: 如果未登录时调用
        """
        if not self._is_logged_in:
            raise LoginError("请先调用login方法进行登录")
        return self.session
    
    def is_logged_in(self):
        """检查是否已登录"""
        return self._is_logged_in
    
    def logout(self):
        """注销登录"""
        # 清空session
        self.session = requests.Session()
        self._is_logged_in = False
        
    def set_base_url(self, base_url):
        """设置基础URL（用于测试或其他环境）"""
        self.base_url = base_url.rstrip('/')