"""
北化课程平台作业解析工具模块
"""
import time
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from .exceptions import NetworkError, ParseError
from .lid_utils import LidUtils
from .course_pages import CoursePages


class CourseUtils:
    """北化课程平台作业解析工具类"""

    def __init__(self, session):
        """
        初始化课程工具

        Args:
            session: requests.Session对象（需要已登录）
        """
        self.session = session
        self.base_url = "https://course.buct.edu.cn"
        self.lid_utils = LidUtils(session)

    def get_pending_homework(self):
        """
        获取待提交作业列表

        Returns:
            list: 待提交作业的课程信息列表
            [{'course_name': str, 'lid': str, 'type': str, 'url': str}, ...]
        """
        return self.lid_utils.get_homework_lids()

    def get_course_details(self, lid, url=None):
        """获取所有作业栏目（含私有栏目、嵌套 iframe 和分页）。

        url 可指定栏目页；默认从课程主页发现。返回已完成/过期作业，
        仅由 can_submit 表示是否待办，不把抓取成功等同于可以提交。
        """
        course_url = url or f"{self.base_url}/meol/jpk/course/layout/newpage/index.jsp?courseId={lid}"
        homework = {}
        try:
            for source_url, soup in CoursePages(self.session, self.base_url).walk(course_url, kind='homework'):
                for info in self._parse_homework_page(soup, source_url):
                    info['lid'] = lid
                    info['source_url'] = source_url
                    homework.setdefault(info['hwtid'], info)
            result = list(homework.values())
            return {"lid": lid, "homework_list": result, "total_count": len(result)}
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"获取课程详情失败: {exc}") from exc

    def get_homework_by_url(self, url, lid=None):
        """直接读取一个栏目/作业列表 URL，不执行提交操作。"""
        return self.get_course_details(lid, url=url)

    def get_homework_detail(self, hwtid):
        """
        获取单个作业的详细信息

        Args:
            hwtid: 作业ID

        Returns:
            dict: 作业详细信息
        """
        try:
            detail_url = f"{self.base_url}/meol/common/hw/student/hwtask.view.jsp?hwtid={hwtid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": f"{self.base_url}/meol/common/hw/student/hwtask.jsp?tagbug=client&strStyle=new03"
            }
            # 添加短暂延迟，避免请求过快
            time.sleep(0.3)
            res = self.session.get(detail_url, headers=headers, timeout=10)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")

            return self._parse_homework_detail(soup, hwtid)

        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取作业详情失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析作业详情失败: {str(e)}")

    def get_homework_detail_special1(self, courseId):
        """兼容旧接口：现由统一栏目发现处理，不再丢弃状态字段。"""
        return self.get_course_details(courseId)['homework_list']

    @staticmethod
    def _homework_id(href):
        return parse_qs(urlsplit(href).query).get('hwtid', [''])[0]

    @staticmethod
    def _deadline_open(value):
        if not value or value.strip() in ('不限', '无限制', '无截止时间'):
            return True
        for fmt in ('%Y年%m月%d日 %H:%M:%S', '%Y年%m月%d日 %H:%M',
                    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                deadline = datetime.strptime(value.strip(), fmt)
                # Windows may not have an IANA timezone database installed.
                from datetime import timedelta, timezone
                now = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)
                return deadline > now
            except ValueError:
                continue
        return False  # Unknown dates must not turn into actionable tasks.

    def _parse_homework_page(self, soup, source_url):
        result = []
        for table in soup.find_all('table', class_='valuelist'):
            fields = {}
            for row in table.find_all('tr'):
                labels = row.find_all('th', recursive=False)
                cells = row.find_all('td', recursive=False)
                if len(labels) == len(cells) == 1:
                    fields[labels[0].get_text(strip=True)] = cells[0]
            if any('标题' in key for key in fields):
                # Blended single-task layout: properties run vertically.
                info = {'hwtid': '', 'title': '', 'deadline': '', 'score': '',
                        'publisher': '', 'submit_href': '', 'result_href': '',
                        'has_result': False, 'is_group': False}
                for label, cell in fields.items():
                    value = cell.get_text(' ', strip=True)
                    if '标题' in label:
                        info['title'] = value
                        title_link = cell.find('a', href=True)
                        if title_link:
                            info['hwtid'] = self._homework_id(title_link['href'])
                            info['detail_href'] = urljoin(source_url, title_link['href'])
                    elif '截止' in label:
                        info['deadline'] = value
                    elif '评分' in label or '分数' in label:
                        info['score'] = value
                    elif '发布人' in label:
                        info['publisher'] = value
                    elif '提交作业' in label:
                        link = cell.find('a', href=True)
                        if link and not self._disabled(link):
                            info['submit_href'] = urljoin(source_url, link['href'])
                            info['hwtid'] = self._homework_id(link['href']) or info['hwtid']
                    elif '查看结果' in label:
                        link = cell.find('a', href=True)
                        if link and not self._disabled(link):
                            info['result_href'] = urljoin(source_url, link['href'])
                            info['has_result'] = True
                info['hwtid'] = info['hwtid'] or self._homework_id(source_url)
                if info['hwtid']:
                    result.append(self._finish_homework(info, source_url))
            else:
                for row in table.find_all('tr'):
                    info = self._parse_homework_row(row)
                    if info:
                        result.append(self._finish_homework(info, source_url))
        return result

    @staticmethod
    def _disabled(link):
        return (link.has_attr('disabled') or link.get('aria-disabled') == 'true'
                or any('disabled' in cls.lower() for cls in link.get('class', []))
                or not link.get('href') or link.get('href', '').startswith(('#', 'javascript:')))

    def _finish_homework(self, info, source_url):
        info['detail_href'] = urljoin(source_url, info.get('detail_href') or (
            f"{self.base_url}/meol/common/hw/student/hwtask.view.jsp?hwtid={info['hwtid']}"
        ))
        for field in ('submit_href', 'result_href'):
            if info.get(field):
                info[field] = urljoin(source_url, info[field])
        score = info.get('score', '').strip()
        completed = info.get('has_result', False) or score not in ('', '暂无分数', '未评分', '暂无成绩')
        info['can_submit'] = bool(info.get('submit_href')) and not completed and self._deadline_open(info.get('deadline', ''))
        if completed:
            info['status'] = '已完成'
        elif not self._deadline_open(info.get('deadline', '')):
            info['status'] = '已截止或截止时间未知'
        else:
            info['status'] = '未提交' if info['can_submit'] else '不可提交'
        return info

    def _parse_homework_table(self, soup, lid):
        """解析作业列表表格"""
        # 添加短暂延迟，确保内容完全加载
        time.sleep(0.5)
        homework_list = []
        table = soup.find('table', class_='valuelist')

        if table:
            rows = table.find_all('tr')[1:]  # 跳过表头
            for row in rows:
                homework_info = self._parse_homework_row(row)
                if homework_info:
                    homework_list.append(homework_info)

        return {
            "lid": lid,
            "homework_list": homework_list,
            "total_count": len(homework_list)
        }

    def _parse_homework_row(self, row):
        """解析标准横表，不将占位行或无作业 ID 的行当作作业。"""
        cells = row.find_all('td', recursive=False)
        if len(cells) < 4:
            return None
        title = row.select_one('a.infolist[href]')
        if title is None:
            title = next((a for a in cells[0].find_all('a', href=True)
                          if self._homework_id(a['href'])), None)
        if title is None or not self._homework_id(title['href']):
            return None
        info = {'hwtid': self._homework_id(title['href']),
                'detail_href': title['href'],
                'title': title.get_text(' ', strip=True),
                'deadline': cells[1].get_text(' ', strip=True),
                'score': cells[2].get_text(' ', strip=True),
                'publisher': cells[3].get_text(' ', strip=True),
                'is_group': row.find('img', title='分组作业') is not None,
                'submit_href': '', 'result_href': '', 'has_result': False}
        submit = row.select_one('a.enter[href]')
        if submit and not self._disabled(submit):
            info['submit_href'] = submit['href']
        result = row.select_one('a.view[href]')
        if result and not self._disabled(result):
            info['result_href'] = result['href']
            info['has_result'] = True
        return self._finish_homework(info, f'{self.base_url}/meol/common/hw/student/hwtask.jsp')

    def _parse_homework_detail(self, soup, hwtid):
        """解析作业详情页面"""
        detail_info = {
            "hwtid": hwtid,
            "title": "",
            "description": "",
            "deadline": "",
            "requirements": "",
            "attachments": []
        }

        # 这里可以根据具体的作业详情页面结构来解析
        # 由于没有具体的HTML结构，这里只是一个框架

        # 作业标题
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('h3')
        if title_elem:
            detail_info['title'] = title_elem.get_text(strip=True)

        # 作业描述
        content_div = soup.find('div', class_='content') or soup.find('div', class_='description')
        if content_div:
            detail_info['description'] = content_div.get_text(strip=True)

        return detail_info

    def get_homework_tasks(self, url):
        """
        获取作业详情页面中的具体题目要求

        Args:
            url: 作业详情页面的URL（homework_info的detail_href）

        Returns:
            list: 包含作业要求的文本列表
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Referer": f"{self.base_url}/meol/common/hw/student/hwtask.jsp?tagbug=client&strStyle=new03"
            }

            # 构造完整URL
            if url.startswith('/'):
                full_url = f"{self.base_url}{url}"
            else:
                full_url = url

            # 添加短暂延迟，避免请求过快
            time.sleep(0.3)
            res = self.session.get(full_url, headers=headers, timeout=10)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, 'html.parser')

            # 查找隐藏的input字段，通常包含作业内容
            content_inputs = soup.find_all('input', {'type': 'hidden'})

            tasks = []
            for input_elem in content_inputs:
                name = input_elem.get('name', '')
                if 'content' in name:  # 查找包含content的input字段
                    value = input_elem.get('value', '')
                    if value:
                        # HTML解码
                        import html
                        decoded_html = html.unescape(value)

                        # 解析HTML内容
                        content_soup = BeautifulSoup(decoded_html, 'html.parser')

                        # 提取所有<p>标签中的文本
                        p_tags = content_soup.find_all('p')
                        for p in p_tags:
                            text = p.get_text(strip=True)
                            if text:  # 只添加非空文本
                                tasks.append(text)

                        # 如果没有p标签，直接提取文本
                        if not p_tags:
                            text = content_soup.get_text(strip=True)
                            if text:
                                tasks.append(text)

            # 如果没有找到隐藏input，尝试查找id="body"的div（备用方案）
            if not tasks:
                body_div = soup.find('div', id='body')
                if body_div:
                    p_tags = body_div.find_all('p')
                    for p in p_tags:
                        text = p.get_text(strip=True)
                        if text:
                            tasks.append(text)

            return tasks

        except Exception as e:
            print(f"获取作业任务详情失败: {str(e)}")
            return []

    def get_all_pending_homework_details(self):
        """
        获取所有待提交作业的详细信息，包时间信息

        Returns:
            list: ��有待提交作业的详细信息列表，包含截止时间等���间信息
            [
                {
                    'course_name': str,
                    'course_info': dict,
                    'lid': str,
                    'homework_list': [
                        {
                            'title': str,
                            'deadline': str,  # 截止时间
                            'hwtid': str,
                            'score': str,
                            'publisher': str,
                            'submit_href': str,
                            'can_submit': bool,
                            'is_group': bool,
                            'status': str,
                            'time_remaining': str  # 剩余时间
                        }
                    ],
                    'total_count': int,
                    'urgent_count': int  # 紧急作业数量（24小时内截止）
                }
            ]
        """
        from datetime import datetime, timedelta

        pending_homework = self.get_pending_homework()
        all_homework_details = []

        for course in pending_homework:
            lid = course['lid']
            course_name = course['course_name']

            try:
                homework_details = self.get_course_details(lid)
                homework_details['course_name'] = course_name
                homework_details['course_info'] = course

                # 添加时间���析
                urgent_count = 0
                current_time = datetime.now()

                homework_list = homework_details.get('homework_list', [])
                for homework in homework_list:
                    # 解析截止时间并计算剩余时间
                    deadline_str = homework.get('deadline', '')
                    if deadline_str:
                        try:
                            # 解析时间格式：2025年9月23日 23:59:00
                            deadline = datetime.strptime(deadline_str, '%Y年%m月%d日 %H:%M:%S')
                            time_diff = deadline - current_time

                            if time_diff.total_seconds() > 0:
                                days = time_diff.days
                                hours, remainder = divmod(time_diff.seconds, 3600)
                                minutes, _ = divmod(remainder, 60)

                                if days > 0:
                                    homework['time_remaining'] = f"{days}天{hours}小时{minutes}分钟"
                                elif hours > 0:
                                    homework['time_remaining'] = f"{hours}小时{minutes}分钟"
                                else:
                                    homework['time_remaining'] = f"{minutes}分钟"

                                # 检查是否为紧急作业（24小时内截止）
                                if time_diff <= timedelta(hours=24):
                                    urgent_count += 1
                                    homework['is_urgent'] = True
                                else:
                                    homework['is_urgent'] = False
                            else:
                                homework['time_remaining'] = "已过期"
                                homework['is_urgent'] = False

                        except ValueError:
                            homework['time_remaining'] = "时间���式错误"
                            homework['is_urgent'] = False
                    else:
                        homework['time_remaining'] = "无截止时间"
                        homework['is_urgent'] = False

                homework_details['urgent_count'] = urgent_count
                all_homework_details.append(homework_details)

                # 添加延迟，避免批量请求过快
                time.sleep(0.8)

            except Exception as e:
                print(f"获取课程 {course_name} (LID: {lid}) ��作���详情失败: {str(e)}")
                continue

        return all_homework_details