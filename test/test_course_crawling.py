"""Offline regressions for discovery: no accounts, cookies or network access."""
import unittest
from unittest.mock import Mock

import requests

from buct_course.client import BUCTClient
from buct_course.client_optimized import BUCTClient as OptimizedClient
from buct_course.course_pages import CoursePages
from buct_course.course_utils import CourseUtils
from buct_course.exceptions import LoginError, ParseError

BASE = 'https://course.buct.edu.cn'
MAIN = BASE + '/meol/jpk/course/layout/newpage/index.jsp?courseId=42'
TRANSFER = BASE + '/meol/jpk/course/course_column_preview_transfer.jsp?columnId=900'
COLUMN = BASE + '/meol/buildless/colUrlStuView.do?columnId=900'
FRAME = BASE + '/meol/common/hw/student/hwtask_blended.jsp?hwtid=123'
LIST = BASE + '/meol/common/hw/student/hwtask.jsp'


def response(html='', status=200, location=None, encoding='utf-8'):
    item = requests.Response()
    item.status_code = status
    item._content = html.encode(encoding)
    if location:
        item.headers['Location'] = location
    return item


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url not in self.pages:
            raise AssertionError('Unexpected request: ' + url)
        item = self.pages[url]
        return response(item) if isinstance(item, str) else item


def vertical(deadline='2099年10月21日 18:00:00', score='暂无分数', submit=True, result=False):
    return '''<meta charset="gbk"><table class="valuelist">
    <tr><th>标题</th><td><a class="infolist" href="hwtask.view.jsp?hwtid=123&amp;context=private">离线章节练习</a></td></tr>
    <tr><th>截止时间</th><td>%s</td></tr>
    <tr><th>评分结果</th><td>%s</td></tr>
    <tr><th>发布人</th><td>示例教师</td></tr>
    <tr><th>提交作业</th><td>%s</td></tr>
    <tr><th>查看结果</th><td>%s</td></tr></table>''' % (
        deadline, score,
        '<a class="enter" href="write.jsp?hwtid=123"></a>' if submit else '',
        '<a class="view" href="result.jsp?hwtid=123">查看</a>' if result else '')


def horizontal(ids):
    rows = ''.join('''<tr><td><a class="infolist" href="hwtask.view.jsp?hwtid=%s">练习%s</a></td>
        <td>2099-10-21 18:00:00</td><td></td><td>教师</td><td></td>
        <td><a class="enter" href="write.jsp?hwtid=%s"></a></td><td></td><td></td></tr>''' % (i, i, i) for i in ids)
    return '<table class="valuelist"><tr><th>标题</th><th>截止时间</th></tr>' + rows + '</table>'


class TestCourseCrawling(unittest.TestCase):
    def test_top_level_arbitrary_label_absolute_dot_redirect_and_nested_frame(self):
        session = FakeSession({
            MAIN: '<a class="le1" href="../../course_column_preview_transfer.jsp?columnId=900">章节练习</a>',
            TRANSFER: response(status=302, location=BASE + '/meol/jpk/course/../../buildless/colUrlStuView.do?columnId=900'),
            COLUMN: '<iframe id="custom-frame" src="' + FRAME + '"></iframe>',
            FRAME: response(vertical(), encoding='gbk'),
        })
        data = CourseUtils(session).get_course_details('42')
        self.assertEqual(data['total_count'], 1)
        hw = data['homework_list'][0]
        self.assertEqual(hw['hwtid'], '123')
        self.assertEqual(hw['title'], '离线章节练习')
        self.assertTrue(hw['can_submit'])
        self.assertEqual(hw['score'], '暂无分数')
        self.assertTrue(hw['detail_href'].endswith('hwtid=123&context=private'))
        self.assertEqual([u for u, _ in session.calls], [MAIN, TRANSFER, COLUMN, FRAME])
        self.assertTrue(all(kwargs['allow_redirects'] is False for _, kwargs in session.calls))
        self.assertEqual(session.calls[-1][1]['headers']['Referer'], COLUMN)

    def test_all_columns_deduplicate_tasks_and_never_fetch_actions(self):
        other = COLUMN.replace('900', '901')
        session = FakeSession({
            MAIN: '<a href="%s">练习甲</a><a href="%s">练习乙</a>' % (COLUMN, other),
            COLUMN: '<iframe src="%s"></iframe>' % FRAME,
            other: '<iframe src="%s"></iframe><a href="write.jsp?hwtid=123">提交</a>' % FRAME,
            FRAME: response(vertical(), encoding='gbk'),
        })
        self.assertEqual(CourseUtils(session).get_course_details('42')['total_count'], 1)
        self.assertEqual(sum(u == FRAME for u, _ in session.calls), 1)
        self.assertFalse(any('write.jsp' in u for u, _ in session.calls))

    def test_direct_column_url_without_course_id(self):
        session = FakeSession({COLUMN: '<iframe src="%s"></iframe>' % FRAME,
                               FRAME: response(vertical(), encoding='gbk')})
        self.assertEqual(CourseUtils(session).get_homework_by_url(COLUMN)['total_count'], 1)

    def test_completed_expired_missing_submit_and_unknown_deadline_retained(self):
        for kwargs in ({'deadline': '2000年01月01日 00:00:00'}, {'score': '90'},
                       {'submit': False}, {'result': True}, {'deadline': '日期未知'}):
            with self.subTest(kwargs=kwargs):
                session = FakeSession({FRAME: response(vertical(**kwargs), encoding='gbk')})
                hw = CourseUtils(session).get_homework_by_url(FRAME)['homework_list'][0]
                self.assertFalse(hw['can_submit'])
                self.assertEqual(hw['deadline'], kwargs.get('deadline', '2099年10月21日 18:00:00'))
                self.assertEqual(hw['has_result'], kwargs.get('result', False))

    def test_full_page_probes_next_and_keeps_short_last_page(self):
        first = LIST + '?pagingPage=1&pagingNumberPer=2'
        second = LIST + '?pagingPage=2&pagingNumberPer=2'
        session = FakeSession({first: horizontal(['1', '2']), second: horizontal(['3'])})
        data = CourseUtils(session).get_homework_by_url(first)
        self.assertEqual(data['total_count'], 3)
        self.assertEqual(len(session.calls), 2)

    def test_server_ignoring_page_parameter_stops_on_duplicate_table(self):
        first = LIST + '?pagingPage=1&pagingNumberPer=1'
        second = LIST + '?pagingPage=2&pagingNumberPer=1'
        session = FakeSession({first: horizontal(['1']), second: horizontal(['1'])})
        self.assertEqual(CourseUtils(session).get_homework_by_url(first)['total_count'], 1)
        self.assertEqual(len(session.calls), 2)

    def test_cycle_and_query_reordering_do_not_repeat(self):
        session = FakeSession({COLUMN: '<iframe src="%s#again"></iframe>' % COLUMN})
        self.assertEqual(len(list(CoursePages(session, BASE).walk(COLUMN))), 1)
        self.assertEqual(len(session.calls), 1)

    def test_external_or_action_redirect_is_never_followed(self):
        for target in ('https://other.example/meol/buildless/colUrlStuView.do?columnId=1',
                       BASE + '/meol/jpk/course/../../common/hw/student/write.jsp?hwtid=123',
                       BASE + '/meol/common/question/test/student/test_start.jsp?testId=99'):
            with self.subTest(target=target):
                session = FakeSession({COLUMN: response(status=302, location=target)})
                list(CoursePages(session, BASE).walk(COLUMN))
                self.assertEqual(len(session.calls), 1)

    def test_js_and_meta_literal_navigation_without_eval(self):
        session = FakeSession({COLUMN: '<script>window.location.href="%s";</script>' % FRAME,
                               FRAME: response(vertical(), encoding='gbk')})
        self.assertEqual(CourseUtils(session).get_homework_by_url(COLUMN)['total_count'], 1)
        session = FakeSession({COLUMN: '<meta http-equiv="refresh" content="0;url=%s">' % FRAME,
                               FRAME: response(vertical(), encoding='gbk')})
        self.assertEqual(CourseUtils(session).get_homework_by_url(COLUMN)['total_count'], 1)

    def test_login_redirect_or_password_page_is_not_empty_success(self):
        for item in (response(status=302, location='https://sidportal.buct.edu.cn/login'),
                     response('<input type="password">')):
            session = FakeSession({COLUMN: item})
            with self.assertRaises(LoginError):
                list(CoursePages(session, BASE).walk(COLUMN))

    def test_page_limit_raises_instead_of_silently_truncating(self):
        session = FakeSession({COLUMN: '<iframe src="%s"></iframe>' % FRAME})
        with self.assertRaises(ParseError):
            list(CoursePages(session, BASE, max_pages=1).walk(COLUMN))

    def test_invalid_start_rejected_without_network(self):
        session = FakeSession({})
        with self.assertRaises(ParseError):
            list(CoursePages(session, BASE).walk(BASE + '/meol/common/hw/student/write.jsp?hwtid=1'))
        self.assertEqual(session.calls, [])

    def test_legacy_special_interface_preserves_completion(self):
        session = FakeSession({MAIN: '<iframe src="%s"></iframe>' % FRAME,
                               FRAME: response(vertical(score='90'), encoding='gbk')})
        hw = CourseUtils(session).get_homework_detail_special1('42')[0]
        self.assertEqual(hw['score'], '90')
        self.assertFalse(hw['can_submit'])

    def test_both_clients_preserve_per_course_real_test_links(self):
        for client_class in (BUCTClient, OptimizedClient):
            with self.subTest(client=client_class.__module__):
                client = client_class()
                utils = Mock(base_url=BASE)
                utils.get_pending_tests.return_value = [
                    {'lid': '1', 'course_name': '甲'}, {'lid': '2', 'course_name': '乙'}]
                utils.get_test_list.side_effect = [
                    {'test_list': [{'test_id': '101', 'title': '题甲', 'can_start': True,
                                    'source_url': COLUMN, 'test_link': COLUMN}]},
                    {'test_list': [{'test_id': '102', 'title': '题乙', 'can_start': True,
                                    'source_url': COLUMN + '&private=2', 'test_link': COLUMN + '&private=2'}]}]
                utils.filter_available_tests.side_effect = lambda items: items
                client.test_utils = utils
                data = client.get_tests_by_category('legacy')['data']['tests']
                self.assertEqual([t['lid'] for t in data], ['1', '2'])
                self.assertEqual([t['test_id'] for t in data], ['101', '102'])
                self.assertEqual([t['test_link'] for t in data], [COLUMN, COLUMN + '&private=2'])
                self.assertEqual([t['course_name'] for t in data], ['甲', '乙'])


if __name__ == '__main__':
    unittest.main()
