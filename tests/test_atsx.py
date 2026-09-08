from campus_jobs.adapters.atsx import ATSXAdapter
from campus_jobs.models import CrawlOptions


def test_atsx_page_url_preserves_project_filter():
    url = (
        "https://arashivision.jobs.feishu.cn/campus/position/list"
        "?project=7657111951542143268&current=1&limit=10&functionCategory="
    )
    page_url = ATSXAdapter._page_url(url, "", 3, 100)
    assert "project=7657111951542143268" in page_url
    assert "current=3" in page_url
    assert "limit=100" in page_url


def test_atsx_body_maps_project_to_subject_filter():
    url = "https://arashivision.jobs.feishu.cn/campus/position/list?project=7657111951542143268"
    options = CrawlOptions(scope="campus")
    body = ATSXAdapter._body(url, options, 100, 100)
    assert body["subject_id_list"] == ["7657111951542143268"]
    assert body["offset"] == 100
    assert body["limit"] == 100
