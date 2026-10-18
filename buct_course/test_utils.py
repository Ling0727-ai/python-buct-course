"""
北化课程平台测试工具模块
"""

import re
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from .course_pages import CoursePages
from .exceptions import LoginError, NetworkError, ParseError
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
    
    def get_test_list(self, lid, url=None):
        """读取标准/指定测试栏目，并合并课程主页发现的其它测试栏目。

        遍历、分页和响应编码交给 CoursePages；这里只解析，不访问开始考试地址。
        """
        try:
            test_url = (
                f"{self.base_url}/meol/common/question/test/student/list.jsp?"
                f"sortColumn=createTime&status=1&tagbug=client&"
                f"sortDirection=-1&strStyle=lesson19&cateId={lid}&"
                f"pagingPage=1&pagingNumberPer=7"
            )
            course_main_url = (
                f"{self.base_url}/meol/jpk/course/layout/newpage/index.jsp?courseId={lid}"
            )
            pages = CoursePages(self.session, self.base_url)
            result = {"course_name": "未知课程", "lid": lid, "test_list": []}
            seen_pages, seen_tests = set(), set()
            for entry in (urljoin(self.base_url, url) if url else test_url, course_main_url):
                for source_url, soup in pages.walk(entry, kind='test'):
                    if source_url in seen_pages:
                        continue
                    seen_pages.add(source_url)
                    parsed = self._parse_test_table(soup, lid, source_url)
                    if parsed['course_name'] != '未知课程':
                        result['course_name'] = parsed['course_name']
                    for test in parsed['test_list']:
                        key = self._test_key(test)
                        if key not in seen_tests:
                            seen_tests.add(key)
                            result['test_list'].append(test)
            result['total_count'] = len(result['test_list'])
            return result
        except (LoginError, NetworkError, ParseError):
            raise
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取测试列表失败: {str(e)}") from e
        except Exception as e:
            raise ParseError(f"解析测试列表失败: {str(e)}") from e
    
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
    
    @staticmethod
    def _test_field(label):
        label = re.sub(r'[\s：:（）()]', '', label)
        aliases = (
            ('title', ('测试名称', '测试标题', '考试名称', '试卷名称', '标题', '名称')),
            ('start_time', ('开始时间', '开放时间')),
            ('end_time', ('截止时间', '结束时间', '关闭时间')),
            ('allowed_attempts', ('允许测试次数', '允许次数', '测试次数', '考试次数')),
            ('duration', ('限制用时', '考试时长', '测试时长', '持续时间', '答题时间')),
            ('submit_status', ('交卷状态', '提交状态', '完成状态', '测试状态', '状态')),
            ('result', ('查看结果', '测试结果', '考试结果', '成绩')),
            ('start', ('开始测试', '开始考试', '进入测试', '操作')),
        )
        for field, names in aliases:
            if any(label == name or label.startswith(name) for name in names):
                return field
        return None

    @staticmethod
    def _test_key(test):
        if test.get('test_id'):
            return ('id', str(test['test_id']))
        return ('metadata', test.get('title', ''), test.get('start_time', ''),
                test.get('end_time', ''))

    def _parse_test_table(self, soup, lid, source_url=None):
        """识别横向列表和竖向属性表，不要求固定列数或固定 CSS 类。"""
        source_url = source_url or (
            f"{self.base_url}/meol/common/question/test/student/list.jsp?cateId={lid}"
        )
        course_name = '未知课程'
        if soup.title and '测试' in soup.title.get_text():
            course_name = soup.title.get_text(strip=True).replace('测试', '').strip()
        tests, seen = [], set()
        for table in soup.find_all('table'):
            rows = [row for row in table.find_all('tr') if row.find_parent('table') is table]
            pairs = []
            for row in rows:
                cells = row.find_all(['td', 'th'], recursive=False)
                if len(cells) == 2:
                    field = self._test_field(cells[0].get_text(strip=True))
                    if field:
                        pairs.append((field, cells[1]))
            # 两个以上纵向属性，且有标题或开始控件，才当作单测试属性表。
            fields = dict(pairs)
            if len(fields) >= 2 and ('title' in fields or 'start' in fields):
                info = self._parse_test_fields(table, fields)
                candidates = [info] if info else []
            else:
                candidates, headers = [], None
                for row in rows:
                    cells = row.find_all(['td', 'th'], recursive=False)
                    labels = [self._test_field(cell.get_text(strip=True)) for cell in cells]
                    if 'title' in labels and sum(field is not None for field in labels) >= 2:
                        headers = labels
                        continue
                    info = self._parse_test_row(row, headers)
                    if info:
                        candidates.append(info)
            for info in candidates:
                info.update(lid=lid, source_url=source_url, test_link=source_url)
                key = self._test_key(info)
                if key not in seen:
                    seen.add(key)
                    tests.append(info)
        return {'course_name': course_name, 'lid': lid,
                'test_list': tests, 'total_count': len(tests)}

    def _parse_test_row(self, row, headers=None):
        cells = row.find_all(['td', 'th'], recursive=False)
        if not cells or row.find('table'):
            return None
        if headers:
            fields = {field: cells[index] for index, field in enumerate(headers)
                      if field and index < len(cells)}
        elif len(cells) >= 8:
            # Course landing pages may use wide layout tables. Without semantic
            # headers require a real test control/ID, not merely eight cells.
            has_control = row.find(attrs={'onclick': re.compile(r'gotostart\s*\(', re.I)})
            has_test_link = any('testid=' in a.get('href', '').lower()
                                for a in row.find_all('a', href=True))
            if not has_control and not has_test_link:
                return None
            fields = dict(zip(('title', 'start_time', 'end_time', 'allowed_attempts',
                               'duration', 'start', 'submit_status', 'result'), cells))
        elif row.find(attrs={'onclick': re.compile(r'gotostart\s*\(', re.I)}):
            fields = {'title': cells[0]}
        else:
            return None
        return self._parse_test_fields(row, fields)

    @staticmethod
    def _control_disabled(control, container):
        for element in [control] + list(control.parents):
            if (element.has_attr('disabled') or
                    str(element.get('aria-disabled', '')).lower() == 'true' or
                    any('disabled' in cls.lower() for cls in element.get('class', []))):
                return True
            if element is container:
                break
        return False

    def _parse_test_fields(self, container, fields):
        info = {field: fields[field].get_text(' ', strip=True).replace('\xa0', ' ').strip()
                if field in fields else ''
                for field in ('title', 'start_time', 'end_time', 'allowed_attempts',
                              'duration', 'submit_status')}
        if not info['title']:
            heading = container.find(['caption', 'h1', 'h2', 'h3'])
            if heading:
                info['title'] = heading.get_text(' ', strip=True)
        if not info['title']:
            return None
        info.update(can_start=False, has_result=False)
        completed_control = False
        for control in container.find_all(['a', 'button', 'input']):
            script = control.get('onclick', '') + ' ' + control.get('href', '')
            match = re.search(r'''\bgotostart\s*\(\s*(['"])([^'"]+)\1''', script, re.I)
            if match:
                info['test_id'] = match.group(2).strip()
                control_text = control.get_text(' ', strip=True) + control.get('value', '')
                if re.search(r'已完成|已交卷|已提交|已结束|已批阅', control_text):
                    completed_control = True
                if not self._control_disabled(control, container):
                    info['can_start'] = True
            if not info.get('test_id'):
                values = parse_qs(urlsplit(control.get('href', '')).query)
                for name, value in values.items():
                    if name.lower() == 'testid' and value:
                        info['test_id'] = value[0]
            result_cell = fields.get('result')
            href = control.get('href', '').strip()
            if (control.name == 'a' and href and
                    not href.lower().startswith(('#', 'javascript:')) and
                    not self._control_disabled(control, container) and
                    (result_cell is not None and (control is result_cell or result_cell in control.parents))):
                info['result_href'] = control['href']
                info['has_result'] = True
        status = info['submit_status']
        completed = (info['has_result'] or completed_control or
                     bool(re.search(r'已完成|已交卷|已提交|已结束|已批阅', status)))
        if completed:
            info['can_start'] = False
        info['status'] = '已完成' if completed else ('可进行' if info['can_start'] else '未开始')
        return info
    
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
            
            # 展示安全的来源栏目；不要为只读查询生成开始考试地址。
            source_url = test.get('source_url') or test.get('test_link')
            if source_url:
                print(f"🔗 测试栏目: {source_url}")
            
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
            "test_url": f"{self.base_url}/meol/common/question/test/student/view.jsp?testId={test_id}"
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