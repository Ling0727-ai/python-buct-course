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
    
    def filter_available_tests(self, test_list):
        """
        过滤测试列表，只保留可以进行的测试
        
        Args:
            test_list: 测试详情列表
            
        Returns:
            list: 只包含可进行测试的列表
        """
        available_tests = []
        
        for test in test_list:
            # 只保留可以开始的测试
            if test.get('can_start', False):
                available_tests.append(test)
        
        return available_tests
    
    def _parse_test_table(self, soup, lid):
        """解析测试列表表格"""
        test_list = []
        course_name = "未知课程"
        
        # 尝试从页面中获取课程名称
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if '测试' in title_text:
                # 提取课程名称，通常在标题中
                course_name = title_text.replace('测试', '').strip()
        
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
            "course_name": course_name,
            "lid": lid,
            "test_list": test_list,
            "total_count": len(test_list)
        }
    
    def _parse_test_row(self, row):
        """解析单行测试信息"""
        test_info = {}
        cells = row.find_all('td')
        
        if len(cells) < 8:  # 根据提供的HTML，测试表格有8列
            return None
        
        # 第1列：测试标题（包含图标和标题文本）
        title_cell = cells[0]
        # 提取纯文本标题，去除图标
        title_text = title_cell.get_text(strip=True)
        test_info['title'] = title_text
        
        # 第2列：开始时间
        test_info['start_time'] = cells[1].get_text(strip=True)
        
        # 第3列：截止时间
        test_info['end_time'] = cells[2].get_text(strip=True)
        
        # 第4列：允许测试次数
        test_info['allowed_attempts'] = cells[3].get_text(strip=True)
        
        # 第5列：限制用时（分钟）
        test_info['duration'] = cells[4].get_text(strip=True)
        
        # 第6列：开始测试（检查是否有开始测试的链接）
        start_test_cell = cells[5]
        start_link = start_test_cell.find('a')
        if start_link and start_link.get('onclick'):
            # 从onclick属性中提取测试ID
            onclick_attr = start_link.get('onclick', '')
            if 'gotostart(' in onclick_attr:
                # 提取测试ID，格式如：gotostart('128089186','client','lesson19')
                import re
                match = re.search(r"gotostart\('(\d+)'", onclick_attr)
                if match:
                    test_info['test_id'] = match.group(1)
                    test_info['can_start'] = True
                    # 构造开始测试的href（虽然原始是###，但我们有test_id）
                    test_info['start_href'] = f"#start_test_{test_info['test_id']}"
                else:
                    test_info['can_start'] = False
            else:
                test_info['can_start'] = False
        else:
            test_info['can_start'] = False
        
        # 第7列：交卷状态
        submit_cell = cells[6]
        submit_text = submit_cell.get_text(strip=True)
        test_info['submit_status'] = submit_text if submit_text != '&nbsp;' else ''
        
        # 第8列：查看结果（检查是否已完成测试）
        result_cell = cells[7]
        result_link = result_cell.find('a')
        if result_link:
            test_info['result_href'] = result_link.get('href', '')
            test_info['has_result'] = True
            # 如果有查看结果链接，说明测试已完成
            test_info['status'] = '已完成'
        else:
            test_info['has_result'] = False
            # 根据是否能开始测试来判断状态
            if test_info.get('can_start', False):
                test_info['status'] = '可进行'
            else:
                test_info['status'] = '未开始'
        
        return test_info
    
    def display_test_details(self, tests, course_name):
        """
        显示测试详细信息，格式与作业保持一致
        
        Args:
            tests: 测试列表
            course_name: 课程名称
        """
        if not tests:
            print("📭 暂无可进行的测试")
            return
        
        for idx, test in enumerate(tests, 1):
            print(f"🧪 测试 {idx}: {test.get('title', '无标题')}")
            # 优先使用测试自带的课程名称，否则使用传入的课程名称
            test_course_name = test.get('course_name', course_name or '未知课程')
            print(f"📚 课程: {test_course_name}")
            # 兼容两种字段名：end_time（原始数据）和 deadline（格式化数据）
            deadline = test.get('deadline') or test.get('end_time', '未知')
            print(f"⏰ 截止时间: {deadline}")
            
            # 显示开始测试链接
            # 兼容两种数据格式：原始数据和格式化数据
            if test.get('test_link'):
                # 格式化数据中已经有构建好的链接
                print(f"🔗 开始测试: {test['test_link']}")
            elif test.get('can_start') and test.get('test_id'):
                # 原始数据需要构建链接
                test_url = f"https://course.buct.edu.cn/meol/common/question/test/student/test_start.jsp?testId={test['test_id']}"
                print(f"🔗 开始测试: {test_url}")
            
            print("-" * 50)
    
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
            "instructions": "",
            "test_url" : f"https://course.buct.edu.cn/meol/common/question/test/student/test_start.jsp?testId={test_id}"
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