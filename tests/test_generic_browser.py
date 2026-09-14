from campus_jobs.adapters.generic_browser import _looks_like_job_object


def test_generic_id_name_object_is_not_a_job():
    assert not _looks_like_job_object({"id": 8, "name": "浪潮"}, "")


def test_job_specific_fields_are_job_evidence():
    assert _looks_like_job_object({"id": 8, "jobName": "算法工程师"}, "")
    assert _looks_like_job_object({"id": 8, "name": "算法工程师", "workCity": "济南"}, "")


def test_jobish_url_is_job_evidence():
    assert _looks_like_job_object({"id": 8, "name": "算法工程师"}, "/recruit/job/8")
