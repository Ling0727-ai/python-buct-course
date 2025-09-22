#!/usr/bin/env python3
"""
测试学科字段功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course.course_utils import CourseUtils


class MockSession:
    """模拟 session 对象"""
    
    def __init__(self):
        self.base_url = "https://course.buct.edu.cn"
    
    def get(self, url, **kwargs):
        """模拟 GET 请求"""
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                
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
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=12345&t=hw','manage_course')">高等数学A</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=67890&t=hw','manage_course')">大学英语</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=11111&t=hw','manage_course')">有机化学</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=22222&t=hw','manage_course')">计算机程序设计</a></li>
                            <li><a onclick="window.open('./lesson/enter_course.jsp?lid=33333&t=hw','manage_course')">机械工程制图</a></li>
                        </ul>
                    </div>
                </body>
                </html>
                """
            
            def _get_homework_list_html(self):
                """返回作业列表页面的模拟 HTML"""
                return """
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
                                <a href="hwtask.view.jsp?hwtid=71597" class="infolist">作业3 (第七章第三部分作业)</a>
                            </td>
                            <td class="align_c">2025年9月23日 23:59:00</td>
                            <td class="align_c"></td>
                            <td class="align_c">王兴远</td>
                            <td class="align_c"></td>
                            <td class="align_c">
                                <a href="write.jsp?hwtid=71597" class="enter" title="提交作业"></a>
                            </td>
                            <td class="align_c"></td>
                            <td class="align_c"></td>
                        </tr>
                    </table>
                </body>
                </html>
                """
        
        return MockResponse()


def test_subject_functionality():
    """测试学科字段功能"""
    print("=== 测试学科字段功能 ===\n")
    
    # 创建模拟 session
    session = MockSession()
    course_utils = CourseUtils(session)
    
    try:
        # 获取待提交作业
        pending_homework = course_utils.get_pending_homework()
        print(f"✅ 获取待提交作业成功，共 {len(pending_homework)} 个课程")
        
        for course in pending_homework:
            course_name = course['course_name']
            lid = course['lid']
            subject = course.get('subject', '未知')
            
            print(f"📚 课程: {course_name}")
            print(f"   LID: {lid}")
            print(f"   学科: {subject}")
            print()
        
        # 测试获取课程详情（包含 subject 字段）
        if pending_homework:
            first_course = pending_homework[0]
            lid = first_course['lid']
            
            print(f"🔍 获取课程详情 (LID: {lid}):")
            course_details = course_utils.get_course_details(lid)
            
            print(f"   LID: {course_details.get('lid')}")
            print(f"   学科: {course_details.get('subject', '未知')}")
            print(f"   作业数量: {course_details.get('total_count', 0)}")
            
            homework_list = course_details.get('homework_list', [])
            for homework in homework_list:
                print(f"   📝 {homework.get('title', '未知作业')}")
        
        print(f"\n🎉 学科字段功能测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_subject_functionality()