from campus_jobs.adapters.hcmcloud import HCMCloudAdapter


def test_expected_total_patterns():
    assert HCMCloudAdapter._expected_total("共 128 个职位") == 128
    assert HCMCloudAdapter._expected_total("岗位总计 42 条") == 42
    assert HCMCloudAdapter._expected_total("新的机会 (186)") == 186
    assert HCMCloudAdapter._expected_total("当前没有统计信息") is None


def test_expected_pages_pattern():
    assert HCMCloudAdapter._expected_pages("当前第\n/ 10\n页\n20 条/页") == 10
    assert HCMCloudAdapter._expected_pages("没有分页") is None


def test_extract_job_id_from_href():
    row = {"href": "#/portal_job_detail?job_id=abc-123", "attrs": {}}
    assert HCMCloudAdapter._extract_id(row) == "abc-123"


def test_extract_job_id_from_data_attribute():
    row = {"href": "", "attrs": {"data-job-id": "98765"}}
    assert HCMCloudAdapter._extract_id(row) == "98765"


def test_row_signature_changes_with_page_content():
    a = [{"title": "算法工程师", "href": "#/job/1", "text": "算法工程师\n济南"}]
    b = [{"title": "算法工程师", "href": "#/job/2", "text": "算法工程师\n济南"}]
    assert HCMCloudAdapter._row_signature(a) != HCMCloudAdapter._row_signature(b)
