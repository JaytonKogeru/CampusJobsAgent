from campus_jobs.detector import pick_adapter


def test_detector():
    assert pick_adapter("https://app.mokahr.com/campus-recruitment/aftershokzhr/36940").name == "moka"
    assert pick_adapter("https://xiaomi.jobs.f.mioffice.cn/campus/").name == "atsx"
    assert pick_adapter("https://cxmt.zhiye.com/campus/jobs").name == "beisen-zhiye"
    assert pick_adapter("https://hr-campus.vivo.com/jobs").name == "vivo-campus"
    assert pick_adapter("https://careers.oppo.com/#/campus").name == "oppo"
    assert pick_adapter("https://join.tplinkglobal.com/jobs").name == "tplink-global"
    assert pick_adapter("https://jobs.ashbyhq.com/openai").name == "ashby"
    assert pick_adapter("https://jobs.lever.co/foo").name == "lever"
