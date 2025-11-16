#!/usr/bin/env python3
"""
测试时间功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.course_utils import CourseUtils


class MockSession:
    """模拟 session 对象，返回包含时间信息的作业数据"""
    
    def __init__(self):
        self.base_url = "https://course.buct.edu.cn"
    
    def get(self, url, **kwargs):
        """模拟 GET 请求"""
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                
                # 根据 URL 返回不同的模拟数据
                if "interaction_reminder_v8.jsp" in url:
                    self.text = self._get_pending_tasks_html()
                elif "hwtask.jsp" in url:
                    self.text = self._get_homework_list_html()
                else:
                    self.text = "<html><body>Mock Response</body></html>"
            
            def raise_for_status(self):
                pass
            
            def _get_pending_tasks_html(self):
                """返回待办任务页面的模拟 HTML"""
                return """
                <!DOCTYPE html>
                <html>
                <body>
                    <div class="content">
                        <ul>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=23479&t=hw','manage_course')">普通物理(Ⅱ)</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=16432&t=hw','manage_course')">马克思主义基本原理</a></li>
                        </ul>
                    </div>
                </body>
                </html>
                """
            
            def _get_homework_list_html(self):
                """返回作业列表页面的模拟 HTML，包含时间信息"""
                # 计算一些测试时间
                now = datetime.now()
                urgent_deadline = (now + timedelta(hours=12)).strftime('%Y年%m月%d日 %H:%M:%S')
                normal_deadline = (now + timedelta(days=3)).strftime('%Y年%m月%d日 %H:%M:%S')
                overdue_deadline = (now - timedelta(hours=2)).strftime('%Y年%m月%d日 %H:%M:%S')
                
                return f"""
                <!DOCTYPE html>
                <html>
                <body>
                    <table class="valuelist" cellspacing="0" cellpadding="0">
                        <tr>
                            <th>标题</th>
                            <th>截止时间</th>
                            <th>分数</th>
                            <th>发布人</th>
                            <th>统计信息</th>
                            <th>提交作业</th>
                            <th>查看结果</th>
                            <th>优秀作品</th>
                        </tr>
                        <tr class="">
                            <td>
                                <a href="hwtask.view.jsp?hwtid=71597" class="infolist">作业3 (第七章第三部分作业)- 机械2403</a>
                                <img src="/meol/styles/default/image/hw_group.png" title="分组作业">
                            </td>
                            <td class="align_c">{urgent_deadline}</td>
                            <td class="align_c"></td>
                            <td class="align_c">王兴远</td>
                            <td class="align_c">
                                <a title="统计信息" class="statistics" href="../hwtask.stat.grade.jsp?hwtid=71597"></a>
                            </td>
                            <td class="align_c">
                                <a href="write.jsp?hwtid=71597" class="enter" title="提交作业"></a>
                            </td>
                            <td class="align_c"></td>
                            <td class="align_c"></td>
                        </tr>
                        <tr class="even">
                            <td>
                                <a href="hwtask.view.jsp?hwtid=71248" class="infolist">作业2 (第七章第二部分作业)- 机械2403</a>
                            </td>
                            <td class="align_c">{normal_deadline}</td>
                            <td class="align_c">合格</td>
                            <td class="align_c">王兴远</td>
                            <td class="align_c">
                                <a title="统计信息" class="statistics" href="../hwtask.stat.grade.jsp?hwtid=71248"></a>
                            </td>
                            <td class="align_c">
                                <a href="write.jsp?hwtid=71248" class="enter" title="提交作业"></a>
                            </td>
                            <td class="align_c"></td>
                            <td class="align_c"></td>
                        </tr>
                        <tr class="">
                            <td>
                                <a href="hwtask.view.jsp?hwtid=70887" class="infolist">作业1 (第七章第一部分作业)- 机械2403</a>
                            </td>
                            <td class="align_c">{overdue_deadline}</td>
                            <td class="align_c">合格</td>
                            <td class="align_c">王兴远</td>
                            <td class="align_c">
                                <a title="统计信息" class="statistics" href="../hwtask.stat.grade.jsp?hwtid=70887"></a>
                            </td>
                            <td class="align_c"></td>
                            <td class="align_c">
                                <a href="taskanswer.jsp?hwtid=70887" class="view" title="查看结果"></a>
                            </td>
                            <td class="align_c"></td>
                        </tr>
                    </table>
                </body>
                </html>
                """
        
        return MockResponse()


def test_time_functionality():
    """测试时间功能"""
    print("=== 测试作业时间功能 ===\n")
    
    # 创建模拟 session
    session = MockSession()
    course_utils = CourseUtils(session)
    
    try:
        # 获取所有待提交作业的详细信息（包含时间）
        all_homework = course_utils.get_all_pending_homework_details()
        
        print(f"✅ 获取作业详情成功，共 {len(all_homework)} 个课程")
        
        for course_detail in all_homework:
            course_name = course_detail['course_name']
            homework_list = course_detail['homework_list']
            urgent_count = course_detail['urgent_count']
            
            print(f"\n📚 课程: {course_name}")
            print(f"   作业总数: {len(homework_list)}")
            print(f"   紧急作业: {urgent_count} 个")
            
            for homework in homework_list:
                title = homework['title']
                deadline = homework['deadline']
                time_remaining = homework.get('time_remaining', '未知')
                is_urgent = homework.get('is_urgent', False)
                
                status_icon = "🚨" if is_urgent else "📝"
                print(f"   {status_icon} {title}")
                print(f"      截止时间: {deadline}")
                print(f"      剩余时间: {time_remaining}")
                
                if homework.get('can_submit'):
                    print(f"      状态: 可提交")
                elif homework.get('has_result'):
                    print(f"      状态: 已提交")
                else:
                    print(f"      状态: {homework.get('status', '未知')}")
        
        print(f"\n🎉 时间功能测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_time_functionality()