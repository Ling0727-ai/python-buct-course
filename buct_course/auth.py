"""
北化课程平台认证模块
"""

import requests
from .exceptions import LoginError, NetworkError
import time

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
            # 先清空旧session，确保重新登录时使用全新的session
            self.session = requests.Session()
            self._is_logged_in = False

            common_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            }

            # 先访问登录页面，获取初始 session cookie (JSESSIONID)
            login_page_url = f"{self.base_url}/meol/login.do"
            self.session.get(login_page_url, headers=common_headers, timeout=10)

            login_url = f"{self.base_url}/meol/loginCheck.do"
            response = self.session.post(login_url, data={
                "IPT_LOGINUSERNAME": username,
                "IPT_LOGINPASSWORD": password,
                "logintoken": int(time.time() * 1000)
            }, headers={
                **common_headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.base_url,
                "Referer": login_page_url,
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
        try:
            # 尝试调用服务器注销接口
            logout_url = "https://portal.buct.edu.cn/cas/logout"
            self.session.get(logout_url, timeout=10)
        except Exception:
            # 忽略注销接口的错误，继续清理本地session
            pass
        finally:
            # 无论如何都要清空本地session
            self.session.close()  # 关闭连接
            self.session = requests.Session()  # 创建新的session
            self._is_logged_in = False

    def set_base_url(self, base_url):
        """设置基础URL（用于测试或其他环境）"""
        self.base_url = base_url.rstrip('/')