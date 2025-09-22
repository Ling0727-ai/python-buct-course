"""
北化课程平台作业解析工具模块
"""

import requests
from bs4 import BeautifulSoup
from .exceptions import NetworkError, ParseError
from .lid_utils import LidUtils


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
    
    def get_course_details(self, lid):
        """
        获取课程作业列表信息
        
        Args:
            lid: 课程ID
            
        Returns:
            dict: 包含课程ID和作业列表的详细信息
        """
        try:
            # 首先访问课程主页，获取作业列表
            course_main_url = f"{self.base_url}/meol/jpk/course/layout/newpage/index.jsp?courseId={lid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            }
            
            main_res = self.session.get(course_main_url, headers=headers, timeout=10)
            main_res.raise_for_status()
            
            main_soup = BeautifulSoup(main_res.text, "html.parser")
            
            # 查找作业相关链接
            homework_link = None
            all_links = main_soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if 'course_column_preview_transfer.jsp' in href and '作业' in text:
                    homework_link = href
                    break
            
            if not homework_link:
                # 如果没找到作业链接，返回空结果
                return {"lid": lid, "homework_list": [], "total_count": 0}
            
            # 构造完整的作业页面URL
            if homework_link.startswith('/'):
                homework_url = f"{self.base_url}{homework_link}"
            elif homework_link.startswith('../../'):
                homework_url = f"{self.base_url}/meol/jpk/course/layout/newpage/{homework_link}"
            else:
                homework_url = homework_link
            
            # 访问作业页面
            headers["Referer"] = course_main_url
            hw_res = self.session.get(homework_url, headers=headers, timeout=10)
            hw_res.raise_for_status()
            
            hw_soup = BeautifulSoup(hw_res.text, "html.parser")
            
            return self._parse_homework_table(hw_soup, lid)
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取课程详情失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析课程详情失败: {str(e)}")
    
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
            res = self.session.get(detail_url, headers=headers, timeout=10)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, "html.parser")
            
            return self._parse_homework_detail(soup, hwtid)
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"获取作业详情失败: {str(e)}")
        except Exception as e:
            raise ParseError(f"解析作业详情失败: {str(e)}")
    
    def _parse_homework_table(self, soup, lid):
        """解析作业列表表格"""
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
        """解析单行作业信息"""
        homework_info = {}
        cells = row.find_all('td')
        
        if len(cells) < 8:
            return None
            
        # 作业标题和链接
        title_cell = cells[0]
        title_link = title_cell.find('a', class_='infolist')
        if title_link:
            homework_info['title'] = title_link.get_text(strip=True)
            detail_href = title_link.get('href', '')
            
            # 构造完整的详情URL
            if detail_href.startswith('/'):
                homework_info['detail_href'] = f"{self.base_url}{detail_href}"
            elif detail_href.startswith('../../'):
                homework_info['detail_href'] = f"{self.base_url}/meol/common/hw/student/{detail_href}"
            elif detail_href.startswith('hwtask.view.jsp'):
                # 相对路径，需要构造完整URL
                homework_info['detail_href'] = f"{self.base_url}/meol/common/hw/student/{detail_href}"
            else:
                homework_info['detail_href'] = detail_href
            
            # 提取作业ID
            if 'hwtid=' in detail_href:
                homework_info['hwtid'] = detail_href.split('hwtid=')[1].split('&')[0]
        
        # 分组作业标识
        group_img = title_cell.find('img', title='分组作业')
        homework_info['is_group'] = group_img is not None
        
        # 截止时间、分数、发布人
        homework_info['deadline'] = cells[1].get_text(strip=True)
        homework_info['score'] = cells[2].get_text(strip=True)
        homework_info['publisher'] = cells[3].get_text(strip=True)
        
        # 提交作业链接
        submit_cell = cells[5]
        submit_link = submit_cell.find('a', class_='enter')
        homework_info['submit_href'] = submit_link.get('href', '') if submit_link else ''
        
        # 判断是否可以提交（检查提交链接、截止时间和完成状态）
        deadline_str = homework_info.get('deadline', '')
        score_text = homework_info.get('score', '')
        
        # 检查是否有提交链接
        has_submit_link = submit_link is not None
        
        # 检查是否已过期
        is_not_expired = True
        if deadline_str:
            try:
                from datetime import datetime
                deadline = datetime.strptime(deadline_str, '%Y年%m月%d日 %H:%M:%S')
                current_time = datetime.now()
                is_not_expired = deadline > current_time
            except ValueError:
                # 如果时间格式解析失败，默认认为未过期
                is_not_expired = True
        
        # 检查是否已完成（有分数表示已完成）
        is_not_completed = not score_text or score_text.strip() == ''
        
        # 只有同时满足：有提交链接、未过期、未完成 才认为可以提交
        homework_info['can_submit'] = has_submit_link and is_not_expired and is_not_completed
        
        # 查看结果链接
        result_cell = cells[6]
        result_link = result_cell.find('a', class_='view')
        homework_info['result_href'] = result_link.get('href', '') if result_link else ''
        homework_info['has_result'] = result_link is not None
        
        # 构造作业详情链接 - 使用作业查看页面
        if homework_info['hwtid']:
            homework_info['detail_href'] = f"https://course.buct.edu.cn/meol/common/hw/student/hwtask.view.jsp?hwtid={homework_info['hwtid']}"
        else:
            homework_info['detail_href'] = ''
        
        if not result_link and '未提交' in result_cell.get_text(strip=True):
            homework_info['status'] = '未提交'
        
        return homework_info
    
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
        获取所有待提交作业的详细信息，包含时间信息
        
        Returns:
            list: 所有待提交作业的详细信息列表，包含截止时间等时间信息
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
                
                # 添加时间分析
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
                            homework['time_remaining'] = "时间格式错误"
                            homework['is_urgent'] = False
                    else:
                        homework['time_remaining'] = "无截止时间"
                        homework['is_urgent'] = False
                
                homework_details['urgent_count'] = urgent_count
                all_homework_details.append(homework_details)
                
            except Exception as e:
                print(f"获取课程 {course_name} (LID: {lid}) 的作业详情失败: {str(e)}")
                continue
        
        return all_homework_details