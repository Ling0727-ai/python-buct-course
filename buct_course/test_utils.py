"""
北化课程平台测试工具模块
提供测试相关的功能
"""

import requests
import datetime
from bs4 import BeautifulSoup
from .exceptions import NetworkError, ParseError

class TestUtils:
    """北化课程平台测试工具类"""
    
    def __init__(self, session):
        """
        初始化测试工具
        
        Args:
            session: requests.Session对象（需要已登录）
        """
        self.session = session
        self.base_url = "https://course.buct.edu.cn"
        # 需要过滤掉的测试ID列表
        self.excluded_test_ids = ['27215', '24199']
    
    def _generate_class_selection(self, order: int):
        """生成CSS类选择器"""
        return f"classicLook{order}"
    
    def _get_test_info_from_soup(self, soup, order: int):
        """
        从BeautifulSoup对象中提取测试信息
        
        Args:
            soup: BeautifulSoup对象
            order: CSS类序号
            
        Returns:
            dict: 测试信息字典
        """
        class_name = self._generate_class_selection(order)
        cells = soup.select(f'td.{class_name}')
        
        if not cells:
            return {"state": 0}
        
        title = cells[0].get_text(strip=True) if cells[0].text else ""
        date = cells[1].get_text(strip=True) if len(cells) > 1 and cells[1].text else ""
        deadline = cells[2].get_text(strip=True) if len(cells) > 2 and cells[2].text else ""
        
        # 提取更多详细信息
        test_status = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        test_type = cells[4].get_text(strip=True) if len(cells) > 4 else ""
        
        # 检查是否有进行测试的图标
        img_tag = cells[-3].find('img', src="../../../../styles/default/image/go.gif")
        state = 1 if img_tag else 0
        
        # 尝试提取测试链接
        test_link = None
        if state == 1 and img_tag and img_tag.find_parent('a'):
            a_tag = img_tag.find_parent('a')
            href = a_tag.get('href', '')
            # 从链接中提取cateId参数
            cate_id = None
            if 'cateId=' in href:
                cate_id = href.split('cateId=')[1].split('&')[0] if '&' in href.split('cateId=')[1] else href.split('cateId=')[1]
            
            # 使用标准的测试列表URL格式
            test_link = (
                f"{self.base_url}/meol/common/question/test/student/list.jsp?"
                f"sortColumn=createTime&status=1&tagbug=client&"
                f"sortDirection=-1&strStyle=lesson19&cateId={cate_id or '34060'}&"
                f"pagingPage=1&pagingNumberPer=7"
            )
        
        return {
            "title": title,
            "date": date,
            "deadline": deadline,
            "status_text": test_status,
            "type": test_type,
            "state": state,
            "test_link": test_link,
            "can_take_test": state == 1
        }
    
    def get_tests_by_category(self, cate_id: str, paging_page: int = 1, paging_number_per: int = 7, excluded_ids=None):
        """
        根据分类ID获取测试列表
        
        Args:
            cate_id: 分类ID
            paging_page: 页码
            paging_number_per: 每页数量
            excluded_ids: 需要排除的测试ID列表
            
        Returns:
            list: 测试信息列表
            
        Raises:
            NetworkError: 网络请求错误
            ParseError: 解析错误
        """
        if excluded_ids is None:
            excluded_ids = ['27215', '24199']  # 默认过滤掉这些ID
        try:
            url = (
                f"{self.base_url}/meol/common/question/test/student/list.jsp?"
                f"sortColumn=createTime&pagingNumberPer={paging_number_per}&status=1&"
                f"tagbug=client&sortDirection=-1&strStyle=lesson19&cateId={cate_id}&"
                f"pagingPage={paging_page}&"
            )
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # 处理GBK编码
            content = response.content.decode('gbk')
            soup = BeautifulSoup(content, 'html.parser')
            
            tests_list = []
            
            # 提取多个classicLook类别的测试信息
            for order in range(8):  # 通常有0-7个classicLook类别
                test_info = self._get_test_info_from_soup(soup, order)
                # 添加更多详细信息
                test_info.update({
                    "cate_id": cate_id,
                    "order": order,
                    "class_name": self._generate_class_selection(order)
                })
                tests_list.append(test_info)
            
            # 过滤掉指定ID的测试（如果cate_id在排除列表中）
            if cate_id in excluded_ids:
                tests_list = []  # 完全过滤掉该分类的所有测试
            
            # 过滤掉不可进行的测试（can_take_test为False的测试）
            tests_list = [test for test in tests_list if test.get('can_take_test', False)]
            
            # 返回完整的JSON响应
            return {
                "success": True,
                "data": {
                    "tests": tests_list,
                    "stats": {
                        "total_tests": len(tests_list),
                        "available_tests": len([t for t in tests_list if t.get("state") == 1]),
                        "completed_tests": len([t for t in tests_list if t.get("state") == 0])
                    },
                    "pagination": {
                        "page": paging_page,
                        "per_page": paging_number_per,
                        "total_pages": 1  # 需要根据实际分页信息实现
                    },
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source_url": url
                }
            }
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取测试列表失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析测试列表失败: {str(e)}")
    
    def get_available_tests(self, cate_id: str, **kwargs):
        """
        获取可用的测试（状态为1的测试）
        
        Args:
            cate_id: 分类ID
            **kwargs: 传递给get_tests_by_category的参数
            
        Returns:
            dict: 包含可用测试的JSON响应
        """
        result = self.get_tests_by_category(cate_id, **kwargs)
        if result["success"]:
            available_tests = [test for test in result["data"]["tests"] if test.get("state") == 1]
            result["data"]["tests"] = available_tests
            result["data"]["stats"]["available_tests"] = len(available_tests)
        return result
    
    def get_test_categories(self):
        """
        获取测试分类列表
        
        Note: 需要根据实际页面结构实现
        """
        # 这里可以实现获取所有测试分类的逻辑
        # 返回格式: [{"id": "分类ID", "name": "分类名称"}, ...]
        return []
    
    def take_test(self, test_id: str):
        """
        开始进行测试
        
        Args:
            test_id: 测试ID
            
        Note: 需要根据实际测试流程实现
        """
        # 这里可以实现开始测试的逻辑
        pass
    
    def get_test_categories(self):
        """
        获取测试分类列表
        
        Returns:
            dict: 包含测试分类信息的JSON响应
        """
        try:
            # 这里需要根据实际页面结构实现获取分类的逻辑
            # 示例返回一些常见的分类
            categories = [
                {"id": "34060", "name": "常规测试", "description": "常规课程测试"},
                {"id": "34061", "name": "期中测试", "description": "期中考试"},
                {"id": "34062", "name": "期末测试", "description": "期末考试"},
                {"id": "34063", "name": "平时测验", "description": "平时小测验"}
            ]
            
            return {
                "success": True,
                "data": {
                    "categories": categories,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取测试分类失败: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def take_test(self, test_id: str):
        """
        开始进行测试
        
        Args:
            test_id: 测试ID
            
        Returns:
            dict: 包含测试开始信息的JSON响应
        """
        try:
            # 这里需要根据实际测试流程实现
            # 示例返回信息
            return {
                "success": True,
                "data": {
                    "test_id": test_id,
                    "message": "测试开始功能待实现",
                    "test_url": f"{self.base_url}/meol/common/question/test/student/taketest.jsp?testId={test_id}",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"开始测试失败: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def get_test_results(self, test_id: str):
        """
        获取测试结果
        
        Args:
            test_id: 测试ID
            
        Returns:
            dict: 包含测试结果的JSON响应
        """
        try:
            # 这里需要根据实际页面结构实现
            return {
                "success": True,
                "data": {
                    "test_id": test_id,
                    "score": "待获取",
                    "status": "completed",
                    "details": "测试结果获取功能待实现",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取测试结果失败: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def filter_tests(self, tests_list):
        """
        过滤测试列表，移除被排除的测试ID
        
        Args:
            tests_list: 测试列表
            
        Returns:
            list: 过滤后的测试列表
        """
        return [test for test in tests_list if test.get('lid') not in self.excluded_test_ids]
    
    def set_base_url(self, base_url):
        """设置基础URL（用于测试或其他环境）"""
        self.base_url = base_url.rstrip('/')