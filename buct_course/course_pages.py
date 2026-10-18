"""Bounded, authenticated discovery of MEOL list/column pages (never task actions)."""

from collections import deque
from datetime import timezone
from email.utils import parsedate_to_datetime
import posixpath
import re
import time
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .exceptions import LoginError, ParseError


class CoursePages:
    """Follow server navigation, frames and pagination without executing page scripts.

    Only same-origin MEOL navigation/list endpoints are fetched. Redirects are
    checked *before* following them, so a frame cannot start an exam, submit a
    homework, or send the authenticated session to an external site.
    """

    RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, session, base_url, max_pages=100, max_depth=8,
                 retries=2, retry_backoff=0.25):
        self.session = session
        self.base_url = base_url.rstrip('/')
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.retries = max(0, int(retries))
        self.retry_backoff = max(0.0, float(retry_backoff))

    def _get(self, url, referer):
        """Fetch a read-only page; retry only bounded, transient failures."""
        for attempt in range(self.retries + 1):
            response = self.session.get(
                url, headers={'Referer': referer}, timeout=15, allow_redirects=False
            )
            if response.status_code not in self.RETRYABLE_STATUSES or attempt >= self.retries:
                return response

            # Retry-After can be either seconds or an HTTP date. Clamp it so a
            # server response cannot stall a full course scan indefinitely.
            delay = self.retry_backoff * (2 ** attempt)
            retry_after = response.headers.get('Retry-After', '')
            try:
                delay = max(delay, float(retry_after))
            except (TypeError, ValueError):
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    delay = max(delay, retry_at.timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
            time.sleep(min(max(delay, 0.0), 5.0))
        raise AssertionError('unreachable')

    @staticmethod
    def _resolve(base, raw):
        # MEOL emits absolute Locations containing /jpk/course/../../buildless/.
        # urljoin alone preserves dot segments in absolute URLs.
        parts = urlsplit(urljoin(base, raw))
        path = posixpath.normpath(parts.path)
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ''))

    def _allowed(self, url, kind):
        parsed = urlsplit(url)
        origin = urlsplit(self.base_url)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc) or parsed.username:
            return False
        path = parsed.path
        if path in {
            '/meol/jpk/course/layout/newpage/index.jsp',
            '/meol/jpk/course/course_column_preview_transfer.jsp',
            '/meol/buildless/colUrlStuView.do',
        }:
            return True
        if kind == 'homework':
            return path in {
                '/meol/common/hw/student/hwtask.jsp',
                '/meol/common/hw/student/hwtask_blended.jsp',
            }
        if kind == 'test':
            return path in {
                '/meol/common/question/test/student/list.jsp',
                '/meol/common/question/test/student/list_blended.jsp',
                '/meol/common/question/test/student/test_blended.jsp',
            }
        return False

    @staticmethod
    def _canonical(url):
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path,
                           urlencode(sorted((k, v) for k, vals in parse_qs(parts.query, keep_blank_values=True).items() for v in vals)), ''))

    @staticmethod
    def _literal_urls(text):
        # Literal navigation only: do not eval JS or interpret arbitrary functions.
        for match in re.finditer(r'''(?:window\.)?(?:location(?:\.href)?\s*=|location\.replace\s*\()\s*(['"])(.*?)\1''', text):
            yield match.group(2)

    def walk(self, start_url, kind='homework'):
        start_url = self._resolve(self.base_url + '/', start_url)
        if not self._allowed(start_url, kind):
            raise ParseError('只允许课程平台的只读栏目或任务列表地址')
        queue = deque([(start_url, self.base_url + '/', 0)])
        seen = set()
        requests_count = 0
        page_signatures = set()
        while queue:
            url, referer, depth = queue.popleft()
            key = self._canonical(url)
            if key in seen or not self._allowed(url, kind):
                continue
            if depth > self.max_depth:
                raise ParseError('栏目嵌套超过抓取上限，请检查页面结构')
            if requests_count >= self.max_pages:
                raise ParseError('栏目/分页数量超过抓取上限，结果可能不完整')
            seen.add(key)
            requests_count += 1
            response = self._get(url, referer)
            response.raise_for_status()
            location = response.headers.get('Location') or response.headers.get('location')
            if response.status_code in (301, 302, 303, 307, 308) and location:
                target = self._resolve(url, location)
                if '/login' in urlsplit(target).path or 'sso_login' in target:
                    raise LoginError('课程会话已失效，请重新登录')
                queue.appendleft((target, url, depth + 1))
                continue
            content = response.content
            soup = BeautifulSoup(content, 'html.parser')
            if soup.select_one('input[type="password"]'):
                raise LoginError('课程会话已失效，请重新登录')
            yield url, soup

            children = []
            for frame in soup.select('iframe[src], frame[src]'):
                children.append(frame['src'])
            for meta in soup.select('meta[http-equiv]'):
                if meta['http-equiv'].lower() == 'refresh':
                    match = re.search(r'url\s*=\s*(.+)', meta.get('content', ''), re.I)
                    if match:
                        children.append(match.group(1).strip(' \"\''))
            for script in soup.find_all('script', src=False):
                children.extend(self._literal_urls(script.get_text()))
            # No le1/le2 requirement and no first-match shortcut: teachers can
            # place a private task at any level or use arbitrary column names.
            for link in soup.select('a[href], a[onclick]'):
                href = link.get('href', '')
                if href and not href.lower().startswith(('javascript:', '#')):
                    children.append(href)
                children.extend(self._literal_urls(link.get('onclick', '')))
                for quoted in re.findall(r'''['"]([^'"]+)['"]''', link.get('onclick', '')):
                    if 'columnId=' in quoted or 'pagingPage=' in quoted:
                        children.append(quoted)

            # Some legacy lists expose paging only via JS/forms. A full page
            # warrants probing the next read-only list page; duplicate content
            # stops servers that ignore pagingPage. Explicit pager links above
            # are still honored for short pages.
            query = parse_qs(urlsplit(url).query, keep_blank_values=True)
            table = soup.find('table', class_='valuelist')
            if table and 'pagingPage' in query:
                signature = str(table)
                fresh = signature not in page_signatures
                page_signatures.add(signature)
                try:
                    current = int(query['pagingPage'][0])
                    per_page = int(query.get('pagingNumberPer', ['0'])[0])
                except ValueError:
                    current, per_page = 0, 0
                count = sum(bool(row.find('td')) for row in table.find_all('tr'))
                if fresh and current > 0 and per_page > 0 and count >= per_page:
                    query['pagingPage'] = [str(current + 1)]
                    parts = urlsplit(url)
                    children.append(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), '')))
            for raw in children:
                child = self._resolve(url, raw)
                if self._allowed(child, kind) and self._canonical(child) not in seen:
                    # Pagination is breadth, not additional nesting.
                    next_depth = depth if urlsplit(child).path == urlsplit(url).path else depth + 1
                    queue.append((child, url, next_depth))
