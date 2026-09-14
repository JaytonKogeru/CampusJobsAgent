from campus_jobs.adapters.hcmcloud import HCMCloudAdapter
from campus_jobs.models import CrawlOptions


def test_expected_total_patterns():
    assert HCMCloudAdapter._expected_total("共 128 个职位") == 128
    assert HCMCloudAdapter._expected_total("岗位总计 42 条") == 42
    assert HCMCloudAdapter._expected_total("新的机会 (186)") == 186
    assert HCMCloudAdapter._expected_total("当前没有统计信息") is None


def test_expected_pages_pattern():
    assert HCMCloudAdapter._expected_pages("当前第\n/ 10\n页\n20 条/页") == 10
    assert HCMCloudAdapter._expected_pages("没有分页") is None


def test_semantic_grid_parsing():
    text = """新的机会 (186)
职位名称
所属单位
工作城市
学历要求
发布时间
职位类别
软件研发工程师（Java）
浪潮数字企业技术有限公司
山东省济南市
本科及以上
2026-07-21
研发类
人工智能研究员
浪潮软件股份有限公司
山东省济南市
硕士及以上
2026-08-30
核心研发类
当前第
/ 10
页
20 条/页
"""
    rows = HCMCloudAdapter._semantic_rows_from_text(text)
    assert len(rows) == 2
    assert rows[0]["title"] == "软件研发工程师（Java）"
    assert rows[0]["cells"][1] == "浪潮数字企业技术有限公司"
    assert rows[1]["cells"][4] == "2026-08-30"


def test_semantic_grid_education_maps_to_serialized_requirements():
    row = {
        "title": "软件研发工程师（Java）",
        "href": "",
        "text": "软件研发工程师（Java）\n浪潮数字企业技术有限公司\n山东省济南市\n本科及以上\n2026-07-21\n研发类",
        "cells": [
            "软件研发工程师（Java）",
            "浪潮数字企业技术有限公司",
            "山东省济南市",
            "本科及以上",
            "2026-07-21",
            "研发类",
        ],
        "attrs": {},
        "kind": "semantic-grid",
        "_page_number": 1,
        "_row_number": 1,
    }
    job = HCMCloudAdapter()._normalize_row(
        "https://inspur.hcmcloud.cn/recruit#/portal_job_list",
        row,
        "浪潮",
        CrawlOptions(),
    )
    assert job is not None
    assert job.requirements == "本科及以上"
    assert job.to_dict()["requirements"] == "本科及以上"


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


def test_extract_native_hcmcloud_id():
    row = {"href": "", "nativeId": "59959", "attrs": {"hcm-key": "59959"}}
    assert HCMCloudAdapter._extract_id(row) == "59959"


def test_extract_native_hcmcloud_id_from_hcm_key_attribute():
    row = {"href": "", "attrs": {"hcm-key": "60354"}}
    assert HCMCloudAdapter._extract_id(row) == "60354"


def test_native_detail_href_is_preserved():
    row = {
        "href": "#/portal_job_detail?id=_HB5_NTkaNTk%253D",
        "nativeId": "59959",
        "attrs": {"hcm-key": "59959"},
    }
    assert HCMCloudAdapter._job_url(
        "https://inspur.hcmcloud.cn/recruit#/portal_job_list",
        row,
        "59959",
    ) == "https://inspur.hcmcloud.cn/recruit#/portal_job_detail?id=_HB5_NTkaNTk%253D"


def test_detail_requirements_extracts_requirement_section():
    description = """岗位职责：
1、完成开发任务。
任职要求：
1、本科及以上学历，计算机相关专业；
2、熟悉 Java。"""
    requirements = HCMCloudAdapter._requirements_from_detail(
        description,
        "本科及以上",
        "计算机相关专业",
    )
    assert "岗位职责" not in requirements
    assert "任职要求：" in requirements
    assert "熟悉 Java" in requirements
    assert requirements.count("本科及以上") == 1


def test_detail_requirements_falls_back_to_list_metadata():
    requirements = HCMCloudAdapter._requirements_from_detail(
        "负责产品研发和项目支持。",
        "硕士及以上",
        "计算机类",
    )
    assert requirements == "学历要求：硕士及以上\n专业要求：计算机类"
