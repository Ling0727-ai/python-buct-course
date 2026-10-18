# 作业与测试的栏目自动发现

抓取仍使用 `requests + BeautifulSoup`，不依赖 Playwright、Selenium 或无头浏览器。

## 发现方式

[统一页面发现器](<buct_course/course_pages.py>)从课程主页读取实际链接，依次处理栏目入口、HTTP 重定向、iframe/frame、meta refresh 和字面量 JavaScript 跳转。不限菜单层级、不要求栏目名称包含“作业”，也不会在第一个栏目有结果时就停止。

ID 不可互换：`courseId/lid` 是课程 ID，`columnId` 是栏目 ID，`hwtid` 是作业 ID，`testId` 是测试 ID。栏目和 iframe 使用服务器给出的完整 URL，不推算栏目 ID。例如一个课程可以通过自己的导航依次给出 `courseId → columnId → hwtid`。

绝对重定向中的 `../` 也会规范化，例如 `/meol/jpk/course/../../buildless/…`。解析使用响应字节及 HTML 编码声明，兼容 GBK 页面。

## 使用

以下代码假设 `session` 是已经正常登录的 `requests.Session`。不要把账号密码写入代码或测试。

```python
from buct_course import CourseUtils, TestUtils

homework = CourseUtils(session)

# 从课程主页自动发现所有支持的作业栏目。
result = homework.get_course_details("13909")

# 也可以直接读取已知栏目；无需先猜出作业 ID。
result = homework.get_homework_by_url(
    "https://course.buct.edu.cn/meol/buildless/colUrlStuView.do?columnId=475645"
)

# 列表保留已完成、过期记录；待办请按 can_submit 过滤。
pending = [item for item in result["homework_list"] if item["can_submit"]]

tests = TestUtils(session)
result = tests.get_test_list("23623")
# 已知特殊栏目时也可传 get_test_list(course_id, url=column_url)。
available = tests.filter_available_tests(result["test_list"])
```

[作业解析](<buct_course/course_utils.py>)兼容横向列表和竖向单任务表，保留分数、结果、截止时间与真实链接。未知截止格式不会被自动视为可提交。旧 `get_homework_detail_special1` 接口保留，但使用同一套发现逻辑。

[测试解析](<buct_course/test_utils.py>)支持表头定位、竖向属性表和不同引号/空格的 `gotostart` 控件。控件只用于提取 ID，不会执行。禁用控件、已完成状态和有效结果链接会影响 `can_start`；空锚点和禁用的结果占位链接不表示已完成。`test_link/source_url` 指向发现该记录的只读来源页，不是开始考试接口。

[标准客户端](<buct_course/client.py>)和[兼容客户端](<buct_course/client_optimized.py>)保留每条测试自己的课程 ID、测试 ID 和真实来源链接；兼容客户端不再用固定日期和课程名伪装成测试记录。

## 分页、限制与安全

- 跟随显式分页；若列表 URL 提供 `pagingPage/pagingNumberPer` 且当前页已满，则探测下一页。重复表格停止自动探测，任务按 ID 去重。
- 只请求同源、已知只读 MEOL 导航/列表路径；每次 HTTP 重定向都先检查再跟随。不会访问作业提交、开始考试、删除或外部站点地址。
- 每次遍历最多 100 次请求、8 层嵌套；超过上限明确报错，不伪装成完整结果。不会绕过登录、验证码或权限校验。
- 能自动发现的是课程 HTML/导航中实际暴露的支持类型链接。纯运行时计算、未出现在页面中的地址或新的未知页面类型仍可能需要新增解析规则；不会猜测 ID 或暴力枚举。
- 默认待办课程来源仍是平台提醒入口，本次未改造成全站/所有历史课程扫描。

## 回归测试

[作业与发现测试](<test/test_course_crawling.py>)、[测试列表测试](<test/test_test_crawling.py>)使用内存 HTML 和假 Session，不需要凭据、不联网：

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s test -p "test_*crawling.py" -v
```

截至本次修改，31 项离线回归通过。授权账号的只读验证已确认：随机信号课程主页自动发现 1 条作业；指定栏目中“第三章作业”的作业 ID 为 `83780`，截止时间为 `2026-10-21 18:00:00`；计算机网络课程返回 8 条作业、4 条测试记录。验证只读取元数据，未提交作业或开始考试。账号、密码和 Cookie 未保存到项目文件。
