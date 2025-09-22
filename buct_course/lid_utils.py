"""
课程 LID 获取工具模块
"""

import requests
from bs4 import BeautifulSoup
from .exceptions import NetworkError, ParseError


class LidUtils:
    """课程 LID 获取工具类"""
    
    def __init__(self, session):
        """
        初始化 LID 工具
        
        Args:
            session: requests.Session对象（需要已登录）
        """
        self.session = session
        self.base_url = "https://course.buct.edu.cn"
    
    def get_pending_tasks(self):
        """
        获取待办任务列表（作业和测试）
        
        Returns:
            dict: 包含作业和测试的字典
            {
                'homework': [{'course_name': str, 'lid': str, 'type': str, 'url': str}, ...],
                'tests': [{'course_name': str, 'lid': str, 'type': str, 'url': str}, ...]
            }
        """
        try:
            url = f"{self.base_url}/meol/welcomepage/student/interaction_reminder_v8.jsp"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            result = {
                "homework": [], 
                "tests": []
            }
            
            # 直接查找作业和测试的链接
            # 作业链接特征：onclick 包含 &t=hw
            homework_links = soup.select("a[onclick*='&t=hw']")
            for link in homework_links:
                course_info = self._extract_single_course_info(link, "homework")
                if course_info:
                    result["homework"].append(course_info)
            
            # 测试链接特征：onclick 包含 &t=test
            test_links = soup.select("a[onclick*='&t=test']")
            for link in test_links:
                course_info = self._extract_single_course_info(link, "test")
                if course_info:
                    result["tests"].append(course_info)
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取待办任务失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析待办任务失败: {str(e)}")
    
    def get_homework_lids(self):
        """
        专门获取待提交作业的课程 LID 列表
        
        Returns:
            list: 作业课程信息列表
            [{'course_name': str, 'lid': str, 'type': str, 'url': str}, ...]
        """
        tasks = self.get_pending_tasks()
        return tasks["homework"]
    
    def get_test_lids(self):
        """
        专门获取待提交测试的课程 LID 列表
        
        Returns:
            list: 测试课程信息列表
            [{'course_name': str, 'lid': str, 'type': str, 'url': str}, ...]
        """
        tasks = self.get_pending_tasks()
        return tasks["tests"]
    
    def get_all_course_lids(self):
        """
        获取所有课程的 LID 列表（从课程主页）
        
        Returns:
            list: 所有课程信息列表
            [{'course_name': str, 'lid': str, 'url': str, 'teacher': str, 'semester': str, 'status': str}, ...]
        """
        try:
            url = f"{self.base_url}/meol/homepage/student/index.jsp"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            courses = []
            
            # 查找课程表格
            course_table = soup.find('table', class_='valuelist')
            if course_table:
                rows = course_table.find_all('tr')[1:]  # 跳过表头
                
                for row in rows:
                    title_cell = row.find('td')
                    if title_cell:
                        title_link = title_cell.find('a')
                        if title_link:
                            course_info = {}
                            course_info['course_name'] = title_link.get_text(strip=True)
                            href = title_link.get('href', '')
                            
                            # 提取课程ID (lid)
                            if 'courseId=' in href:
                                course_info['lid'] = href.split('courseId=')[1].split('&')[0]
                                course_info['url'] = f"{self.base_url}{href}" if href.startswith('/') else href
                            
                            # 获取其他信息
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                course_info['teacher'] = cells[1].get_text(strip=True)
                                course_info['semester'] = cells[2].get_text(strip=True)
                                course_info['status'] = cells[3].get_text(strip=True)
                            
                            if 'lid' in course_info:
                                courses.append(course_info)
            
            return courses
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取课程列表失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析课程列表失败: {str(e)}")
    
    def find_lid_by_course_name(self, course_name):
        """
        根据课程名称查找对应的 LID
        
        Args:
            course_name: 课程名称（支持部分匹配）
            
        Returns:
            str: 找到的第一个匹配课程的 LID，未找到返回 None
        """
        all_courses = self.get_all_course_lids()
        
        for course in all_courses:
            if course_name.lower() in course['course_name'].lower():
                return course['lid']
        
        return None
    
    def get_lid_from_url(self, url):
        """
        从 URL 中提取 LID
        
        Args:
            url: 包含 courseId 或 lid 参数的 URL
            
        Returns:
            str: 提取的 LID，未找到返回 None
        """
        if 'courseId=' in url:
            return url.split('courseId=')[1].split('&')[0]
        elif 'lid=' in url:
            return url.split('lid=')[1].split('&')[0]
        
        return None
    
    def _extract_single_course_info(self, link_element, expected_type):
        """
        从单个链接元素中提取课程信息
        
        Args:
            link_element: BeautifulSoup的a元素
            expected_type: 期望的类型 ('homework' 或 'test')
            
        Returns:
            dict: 课程信息字典，如果无效则返回 None
        """
        course_name = link_element.get_text(strip=True)
        onclick = link_element.get("onclick", "")
        
        if not onclick or "lid=" not in onclick:
            return None
        
        # 提取 LID
        lid = onclick.split("lid=")[1].split("&")[0]
        
        # 验证类型
        if expected_type == "homework" and "&t=hw" not in onclick:
            return None
        elif expected_type == "test" and "&t=test" not in onclick:
            return None
        
        # 过滤掉汇总信息
        if '门课程' in course_name and '待提交' in course_name:
            return None
        
        # 过滤掉特定的测试课程 LID
        if expected_type == "test" and lid in ["24199", "27215"]:
            return None
        
        # 根据类型生成不同的URL
        if expected_type == "test":
            url = f"{self.base_url}/meol/common/question/test/student/list.jsp?sortColumn=createTime&status=1&tagbug=client&sortDirection=-1&strStyle=lesson19&cateId={lid}&pagingPage=1&pagingNumberPer=7"
        else:
            url = f"{self.base_url}/meol/jpk/course/layout/newpage/index.jsp?courseId={lid}"
        
        return {
            "course_name": course_name,
            "lid": lid,
            "course_id": lid,  # 添加 course_id 字段以保持兼容性
            "type": expected_type,
            "url": url
        }