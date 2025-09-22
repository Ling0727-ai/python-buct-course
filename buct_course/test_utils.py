"""
北化课程平台测试工具模块
"""

import requests
from bs4 import BeautifulSoup
from .exceptions import NetworkError, ParseError
from .lid_utils import LidUtils


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
        self.lid_utils = LidUtils(session)
    
    def get_pending_tests(self):
        """
        获取待提交测试列表
        
        Returns:
            list: 待提交测试的课程信息列表
            [{'course_name': str, 'lid': str, 'url': str}, ...]
        """
        return self.lid_utils.get_test_lids()
    
    def get_test_list(self, lid):
        """
        获取指定课程的测试列表
        
        Args:
            lid: 课程ID
            
        Returns:
            dict: 包含测试列表的详细信息
        """
        try:
            test_url = (
                f"{self.base_url}/meol/common/question/test/student/list.jsp?"
                f"sortColumn=createTime&status=1&tagbug=client&"
                f"sortDirection=-1&strStyle=lesson19&cateId={lid}&"
                f"pagingPage=1&pagingNumberPer=7"
            )
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": f"{self.base_url}/meol/jpk/course/layout/newpage/index.jsp?courseId={lid}",
                "Origin": self.base_url
            }
            
            response = self.session.get(test_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            return self._parse_test_table(soup, lid)
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取测试列表失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析测试列表失败: {str(e)}")
    
    def get_test_detail(self, test_id):
        """
        获取单个测试的详细信息
        
        Args:
            test_id: 测试ID
            
        Returns:
            dict: 测试详细信息
        """
        try:
            detail_url = f"{self.base_url}/meol/common/question/test/student/view.jsp?testId={test_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": f"{self.base_url}/meol/common/question/test/student/list.jsp"
            }
            
            response = self.session.get(detail_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            return self._parse_test_detail(soup, test_id)
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取测试详情失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析测试详情失败: {str(e)}")
    
    def filter_tests(self, test_courses):
        """
        过滤测试列表，移除不需要的项目
        
        Args:
            test_courses: 原始测试课程列表
            
        Returns:
            list: 过滤后的测试课程列表
        """
        filtered_tests = []
        
        for course in test_courses:
            course_name = course.get('course_name', '')
            
            # 过滤逻辑：移除汇总信息和无效项目
            if (course.get('lid') and 
                not ('门课程' in course_name and '待提交' in course_name) and
                not course_name.strip() == ''):
                
                filtered_tests.append(course)
        
        return filtered_tests
    
    def _parse_test_table(self, soup, lid):
        """解析测试列表表格"""
        test_list = []
        
        # 查找测试列表表格
        table = soup.find('table', class_='valuelist')
        if not table:
            # 尝试其他可能的表格选择器
            table = soup.find('table', {'border': '0', 'cellspacing': '0', 'cellpadding': '0'})
        
        if table:
            rows = table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                test_info = self._parse_test_row(row)
                if test_info:
                    test_list.append(test_info)
        
        return {
            "lid": lid,
            "test_list": test_list,
            "total_count": len(test_list)
        }
    
    def _parse_test_row(self, row):
        """解析单行测试信息"""
        test_info = {}
        cells = row.find_all('td')
        
        if len(cells) < 6:  # 测试表格通常有6列或更多
            return None
        
        # 测试标题和链接
        title_cell = cells[0]
        title_link = title_cell.find('a')
        if title_link:
            test_info['title'] = title_link.get_text(strip=True)
            test_info['detail_href'] = title_link.get('href', '')
            
            # 提取测试ID
            if 'testId=' in test_info['detail_href']:
                test_info['test_id'] = test_info['detail_href'].split('testId=')[1].split('&')[0]
        
        # 其他信息（根据实际表格结构调整）
        if len(cells) >= 2:
            test_info['start_time'] = cells[1].get_text(strip=True)
        if len(cells) >= 3:
            test_info['end_time'] = cells[2].get_text(strip=True)
        if len(cells) >= 4:
            test_info['duration'] = cells[3].get_text(strip=True)
        if len(cells) >= 5:
            test_info['status'] = cells[4].get_text(strip=True)
        if len(cells) >= 6:
            test_info['score'] = cells[5].get_text(strip=True)
        
        # 检查是否可以参加测试
        action_cell = cells[-1] if cells else None
        if action_cell:
            start_link = action_cell.find('a', string=lambda text: text and '开始' in text)
            test_info['can_start'] = start_link is not None
            if start_link:
                test_info['start_href'] = start_link.get('href', '')
        
        return test_info
    
    def _parse_test_detail(self, soup, test_id):
        """解析测试详情页面"""
        detail_info = {
            "test_id": test_id,
            "title": "",
            "description": "",
            "start_time": "",
            "end_time": "",
            "duration": "",
            "total_score": "",
            "question_count": "",
            "instructions": ""
        }
        
        # 测试标题
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('h3')
        if title_elem:
            detail_info['title'] = title_elem.get_text(strip=True)
        
        # 测试描述和说明
        content_div = soup.find('div', class_='content') or soup.find('div', class_='description')
        if content_div:
            detail_info['description'] = content_div.get_text(strip=True)
        
        # 查找测试信息表格
        info_table = soup.find('table', class_='info')
        if info_table:
            rows = info_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    if '开始时间' in key:
                        detail_info['start_time'] = value
                    elif '结束时间' in key:
                        detail_info['end_time'] = value
                    elif '持续时间' in key or '考试时长' in key:
                        detail_info['duration'] = value
                    elif '总分' in key:
                        detail_info['total_score'] = value
                    elif '题目数' in key or '问题数' in key:
                        detail_info['question_count'] = value
        
        return detail_info