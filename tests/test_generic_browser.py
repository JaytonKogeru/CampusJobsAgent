from campus_jobs.adapters.generic_browser import (
    _looks_like_job_anchor,
    _looks_like_job_object,
    _quality_summary,
)
from campus_jobs.models import Job


def test_generic_id_name_object_is_not_a_job():
    assert not _looks_like_job_object({"id": 8, "name": "浪潮"}, "")


def test_job_specific_fields_are_job_evidence():
    assert _looks_like_job_object({"id": 8, "jobName": "算法工程师"}, "")
    assert _looks_like_job_object({"id": 8, "name": "算法工程师", "workCity": "济南"}, "")


def test_jobish_url_is_job_evidence():
    assert _looks_like_job_object({"id": 8, "name": "算法工程师"}, "/recruit/job/8")


def test_navigation_links_are_not_jobs():
    assert not _looks_like_job_anchor(
        "岗位投递",
        "https://maker.haier.net/client/campus/activityindex.html",
    )
    assert not _looks_like_job_anchor(
        "招聘动态",
        "https://maker.haier.net/client/campus/dynamic.html",
    )
    assert not _looks_like_job_anchor(
        "实习生招聘",
        "https://maker.haier.net/client/practice/jobs.html",
    )


def test_real_job_detail_links_are_jobs():
    assert _looks_like_job_anchor(
        "MEDP-智造技术研发工程师",
        "https://maker.haier.net/client/campus/deliverfirst/id/47/fid/22/rid/397.html",
    )
    assert _looks_like_job_anchor(
        "Software Engineer",
        "https://example.com/careers/jobs/1234",
    )


def test_three_empty_anchor_jobs_are_low_quality():
    jobs = {
        str(i): Job(id=str(i), title=f"岗位{i}", url=f"https://example.com/jobs/{i}")
        for i in range(3)
    }
    informative, low_quality = _quality_summary(jobs)
    assert informative == 0
    assert low_quality


def test_informative_jobs_are_not_low_quality():
    jobs = {
        "1": Job(id="1", title="算法工程师", url="https://example.com/jobs/1", location="深圳"),
        "2": Job(id="2", title="数据工程师", url="https://example.com/jobs/2", description="Build data pipelines"),
        "3": Job(id="3", title="测试工程师", url="https://example.com/jobs/3", requirements="Python"),
    }
    informative, low_quality = _quality_summary(jobs)
    assert informative == 3
    assert not low_quality
