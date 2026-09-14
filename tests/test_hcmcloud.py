from campus_jobs.adapters.generic_browser import _looks_like_job_object, _title_field
from campus_jobs.adapters.hcmcloud import HCMCloudAdapter
from campus_jobs.detector import pick_adapter


def test_hcmcloud_detection():
    url = "https://inspur.hcmcloud.cn/recruit#/portal_job_list"
    assert HCMCloudAdapter.can_handle(url)
    assert HCMCloudAdapter.can_handle("https://example.hcmcloud.cn/recruit")
    assert not HCMCloudAdapter.can_handle("https://example.com/recruit")
    assert pick_adapter(url).name == "hcmcloud"


def test_hcmcloud_total_hint():
    assert HCMCloudAdapter._total_hint("当前共 68 个职位") == 68
    assert HCMCloudAdapter._total_hint("岗位共 123 条") == 123
    assert HCMCloudAdapter._total_hint("欢迎加入我们") is None


def test_hcmcloud_candidate_normalization():
    job = HCMCloudAdapter._candidate_to_job(
        {
            "href": "#/portal_job_detail?id=51299&company_id=8",
            "title": "AI算法工程师",
            "card_text": "AI算法工程师\n工作地点：济南\n校园招聘",
        },
        "https://inspur.hcmcloud.cn/recruit#/portal_job_list",
        "inspur.hcmcloud.cn",
    )
    assert job is not None
    assert job.id == "51299"
    assert job.title == "AI算法工程师"
    assert job.location == "济南"
    assert "portal_job_detail" in job.url


def test_hcmcloud_rejects_company_as_job():
    assert (
        HCMCloudAdapter._candidate_to_job(
            {
                "href": "#/portal_job_detail?id=8",
                "title": "浪潮",
                "card_text": "浪潮",
            },
            "https://inspur.hcmcloud.cn/recruit#/portal_job_list",
            "inspur.hcmcloud.cn",
        )
        is None
    )


def test_generic_browser_rejects_plain_company_object():
    obj = {"id": 8, "name": "浪潮", "special_title": ""}
    title_key, title = _title_field(obj)
    assert title_key == "name"
    assert title == "浪潮"
    assert not _looks_like_job_object(
        obj,
        title_key,
        "",
        "https://inspur.hcmcloud.cn/api/auth/get_auth?app_type=recruit",
    )


def test_generic_browser_accepts_named_job_object_with_semantics():
    obj = {"id": 9, "name": "算法工程师", "workLocation": "深圳"}
    title_key, _ = _title_field(obj)
    assert _looks_like_job_object(obj, title_key, "", "https://example.com/api/data")
