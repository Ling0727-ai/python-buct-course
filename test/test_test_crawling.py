"""Offline test discovery regressions; no credentials or live requests."""
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from buct_course.test_utils import TestUtils


BASE = 'https://course.buct.edu.cn'
MAIN = BASE + '/meol/jpk/course/layout/newpage/index.jsp?courseId=42'
LIST = BASE + '/meol/common/question/test/student/list.jsp'


def soup(html):
    return BeautifulSoup(html, 'html.parser')


def listing(test_id='100', title='第一测验', control=None, status='', result=''):
    control = control if control is not None else (
        '<a href="###" onclick="gotostart(\'%s\', \'client\', \'lesson19\')">开始测试</a>' % test_id
    )
    return '''<title>离线课程测试</title><table class="valuelist">
    <tr><th>测试名称</th><th>开始时间</th><th>截止时间</th><th>允许测试次数</th>
    <th>限制用时</th><th>开始测试</th><th>交卷状态</th><th>查看结果</th></tr>
    <tr><td>%s</td><td>2026-10-01</td><td>2026-11-01</td><td>2</td>
    <td>60</td><td>%s</td><td>%s</td><td>%s</td></tr></table>''' % (title, control, status, result)


class NoNetworkSession:
    def get(self, *args, **kwargs):
        raise AssertionError('Mock-walker tests must never issue requests')


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, html, encoding='utf-8'):
        self.content = html.encode(encoding)

    def raise_for_status(self):
        pass

    @property
    def text(self):
        raise AssertionError('Encoding must be handled from response.content by walker')


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        key = url if url in self.pages else (LIST if url.startswith(LIST + '?') else url)
        if key not in self.pages:
            raise AssertionError('Unexpected request (possibly exam action): ' + url)
        value = self.pages[key]
        return value if isinstance(value, FakeResponse) else FakeResponse(value)


class TestTestCrawling(unittest.TestCase):
    def setUp(self):
        self.utils = TestUtils(NoNetworkSession())

    def parse(self, html):
        return self.utils._parse_test_table(soup(html), '42', LIST)['test_list']

    def test_unrelated_wide_layout_table_is_not_a_test(self):
        html = '<table><tr>' + '<td>导航内容</td>' * 8 + '</tr></table>'
        self.assertEqual(self.parse(html), [])

    def test_standard_list_fields_and_safe_source(self):
        test = self.parse(listing())[0]
        self.assertEqual(test['test_id'], '100')
        self.assertEqual(test['title'], '第一测验')
        self.assertEqual(test['duration'], '60')
        self.assertTrue(test['can_start'])
        self.assertEqual(test['lid'], '42')
        self.assertEqual(test['source_url'], LIST)
        self.assertEqual(test['test_link'], LIST)
        self.assertNotIn('start_href', test)

    def test_gotostart_quotes_and_whitespace(self):
        for script in ("gotostart('101','client')", 'gotostart ( "101" , "client" )'):
            with self.subTest(script=script):
                control = '<button onclick=\'%s\'>开始测试</button>' % script if '"' in script else '<button onclick="%s">开始测试</button>' % script
                test = self.parse(listing(control=control))[0]
                self.assertEqual(test['test_id'], '101')
                self.assertTrue(test['can_start'])

    def test_reordered_short_horizontal_list(self):
        tests = self.parse('''<table><tr><th>截止时间</th><th>测试名称</th><th>操作</th></tr>
        <tr><td>2026-11-01</td><td>短列表</td>
        <td><a onclick="gotostart('202')">开始</a></td></tr></table>''')
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0]['title'], '短列表')
        self.assertEqual(tests[0]['end_time'], '2026-11-01')

    def test_vertical_property_table(self):
        tests = self.parse('''<table class="info">
        <tr><th>测试名称：</th><td>竖向测验</td></tr>
        <tr><th>截止时间</th><td>2026-11-02</td></tr>
        <tr><th>考试时长（分钟）</th><td>30</td></tr>
        <tr><th>开始测试</th><td><input type="button" value="开始" onclick='gotostart ( "303" )'></td></tr>
        </table>''')
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0]['title'], '竖向测验')
        self.assertEqual(tests[0]['test_id'], '303')
        self.assertEqual(tests[0]['duration'], '30')
        self.assertTrue(tests[0]['can_start'])

    def test_completed_status_never_startable(self):
        for status in ('已完成', '已交卷', '已提交', '已结束'):
            with self.subTest(status=status):
                test = self.parse(listing(status=status))[0]
                self.assertFalse(test['can_start'])
                self.assertEqual(test['status'], '已完成')
        self.assertTrue(self.parse(listing(status='未提交'))[0]['can_start'])

    def test_completed_control_never_startable(self):
        control = '<button onclick="gotostart(\'100\')">已完成</button>'
        test = self.parse(listing(control=control))[0]
        self.assertFalse(test['can_start'])
        self.assertEqual(test['status'], '已完成')

    def test_vertical_caption_as_title(self):
        test = self.parse('''<table><caption>单测试</caption>
        <tr><th>截止时间</th><td>2026-11-01</td></tr>
        <tr><th>开始测试</th><td><a onclick="gotostart('909')">开始</a></td></tr>
        </table>''')[0]
        self.assertEqual(test['title'], '单测试')
        self.assertEqual(test['test_id'], '909')

    def test_result_link_overrides_start_control(self):
        test = self.parse(listing(result='<a href="result.jsp?testId=100">查看结果</a>'))[0]
        self.assertTrue(test['has_result'])
        self.assertFalse(test['can_start'])

    def test_placeholder_result_links_are_not_completion(self):
        for link in ('<a href="###">暂无结果</a>',
                     '<a href="javascript:void(0)">暂无结果</a>',
                     '<a href="result.jsp?testId=100" class="disabled">暂无结果</a>'):
            with self.subTest(link=link):
                test = self.parse(listing(result=link))[0]
                self.assertFalse(test['has_result'])
                self.assertTrue(test['can_start'])

    def test_login_failure_preserves_error_type(self):
        from buct_course.exceptions import LoginError
        with patch('buct_course.test_utils.CoursePages') as walker_class:
            walker_class.return_value.walk.side_effect = LoginError('expired')
            with self.assertRaises(LoginError):
                self.utils.get_test_list('42')

    def test_disabled_controls_never_startable(self):
        for attrs in ('disabled', 'aria-disabled="true"', 'class="disabled"'):
            with self.subTest(attrs=attrs):
                control = '<button %s onclick="gotostart(\'404\')">开始测试</button>' % attrs
                test = self.parse(listing(control=control))[0]
                self.assertEqual(test['test_id'], '404')
                self.assertFalse(test['can_start'])
        control = '<span class="disabled"><a onclick="gotostart(\'405\')">开始测试</a></span>'
        self.assertFalse(self.parse(listing(control=control))[0]['can_start'])

    def test_multi_column_walk_and_id_deduplication(self):
        column = BASE + '/meol/buildless/colUrlStuView.do?columnId=7'
        with patch('buct_course.test_utils.CoursePages') as walker_class:
            walker = walker_class.return_value
            walker.walk.side_effect = [
                [(LIST, soup(listing()))],
                [(MAIN, soup('<html></html>')),
                 (column, soup(listing() + listing('200', '其它栏目测验')))],
            ]
            result = self.utils.get_test_list('42')
            self.assertEqual(result['total_count'], 2)
            self.assertEqual([test['test_id'] for test in result['test_list']], ['100', '200'])
            self.assertEqual(result['test_list'][1]['source_url'], column)
            self.assertIn('/student/list.jsp?', walker.walk.call_args_list[0].args[0])
            self.assertEqual(walker.walk.call_args_list[1].args[0], MAIN)
            for call in walker.walk.call_args_list:
                self.assertEqual(call.kwargs, {'kind': 'test'})

    def test_explicit_column_url(self):
        column = '/meol/buildless/colUrlStuView.do?columnId=99'
        with patch('buct_course.test_utils.CoursePages') as walker_class:
            walker_class.return_value.walk.return_value = [(BASE + column, soup(listing()))]
            result = self.utils.get_test_list('42', url=column)
            self.assertEqual(result['total_count'], 1)
            self.assertEqual(walker_class.return_value.walk.call_args_list[0].args[0], BASE + column)

    def test_stable_metadata_deduplication_without_id(self):
        html = '''<table><tr><th>测试名称</th><th>状态</th></tr>
        <tr><td>无控件测验</td><td>已完成</td></tr></table>'''
        with patch('buct_course.test_utils.CoursePages') as walker_class:
            walker_class.return_value.walk.side_effect = [
                [(LIST, soup(html))], [(MAIN, soup(html))]
            ]
            result = self.utils.get_test_list('42')
        self.assertEqual(result['total_count'], 1)
        self.assertFalse(result['test_list'][0]['can_start'])

    def test_actual_walker_does_not_execute_exam_actions(self):
        column = BASE + '/meol/buildless/colUrlStuView.do?columnId=8'
        iframe = BASE + '/meol/common/question/test/student/list_blended.jsp?cateId=9'
        page2 = LIST + '?cateId=42&pagingPage=2'
        session = FakeSession({
            LIST: listing() + '<a href="%s">下一页</a>' % page2,
            page2: listing('101', '分页测验'),
            MAIN: '<a href="%s">自定义测验栏目</a>' % column,
            column: '<iframe src="%s"></iframe><a href="/meol/common/question/test/student/test_start.jsp?testId=666">开始考试</a>' % iframe,
            iframe: listing('102', '内嵌测验') + '<script>gotostart("999")</script>',
        })
        result = TestUtils(session).get_test_list('42')
        self.assertEqual({test['test_id'] for test in result['test_list']}, {'100', '101', '102'})
        self.assertTrue(all('test_start' not in url for url in session.calls))
        self.assertTrue(all('test_start' not in test['test_link'] for test in result['test_list']))

    def test_walker_uses_response_bytes_encoding(self):
        html = '<meta charset="gbk">' + listing(title='中文编码测验')
        session = FakeSession({LIST: FakeResponse(html, 'gbk'), MAIN: '<html></html>'})
        result = TestUtils(session).get_test_list('42')
        self.assertEqual(result['test_list'][0]['title'], '中文编码测验')


if __name__ == '__main__':
    unittest.main()
