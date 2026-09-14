from campus_jobs.adapters.haier import HaierCampusAdapter


def test_haier_can_handle_campus_pages():
    assert HaierCampusAdapter.can_handle("https://maker.haier.net/client/campus/activityindex.html")
    assert HaierCampusAdapter.can_handle(
        "https://maker.haier.net/client/campus/deliverfirst/id/68/fid/30/rid/452.html"
    )
    assert not HaierCampusAdapter.can_handle("https://maker.haier.net/client/practice/jobs.html")


def test_haier_activity_prefers_checked_radio():
    html = """
    <input type="radio" name="aid" value="67" title="博士登陆计划（2027届）">
    <input checked="checked" type="radio" name="aid" value="68" title="海尔集团2027校园招聘">
    """
    assert HaierCampusAdapter._activity_id(
        "https://maker.haier.net/client/campus/activityindex.html", html
    ) == ("68", "海尔集团2027校园招聘")


def test_haier_job_from_api_item():
    job = HaierCampusAdapter._job_from_item(
        {
            "id": 452,
            "function_id": 30,
            "name": "AI算法工程师",
            "fun_name": "AI/算法类",
            "department": "海尔新能源",
            "addr": "青岛市",
            "click_url": "/client/campus/deliverfirst/id/68/fid/30/rid/452.html",
        },
        "68",
        "海尔集团2027校园招聘",
    )
    assert job is not None
    assert job.id == "452"
    assert job.title == "AI算法工程师"
    assert job.function == "AI/算法类"
    assert job.department == "海尔新能源"
    assert job.location == "青岛市"
    assert job.url.endswith("/client/campus/deliverfirst/id/68/fid/30/rid/452.html")
    assert job.extra["selectedActivityId"] == "68"


def test_haier_detail_parser():
    html = """
    <div class="title_div"><div class="title">AI算法工程师</div></div>
    <div class="demand_title">岗位描述</div>
    <div class="demand_box">负责大语言模型与多模态大模型的训练和优化。</div>
    <div class="demand_title">岗位要求</div>
    <div class="demand_box">熟练掌握 Python 和 C++，熟悉 PyTorch。</div>
    <div class="demand_title">工作地点</div>
    <div class="demand_box"><div class="demand_item">青岛市</div></div>
    <div class="department_title_item action">海尔新能源</div>
    """
    detail = HaierCampusAdapter._parse_detail(html)
    assert detail["title"] == "AI算法工程师"
    assert "大语言模型" in detail["description"]
    assert "Python" in detail["requirements"]
    assert detail["location"] == "青岛市"
    assert detail["department"] == "海尔新能源"
