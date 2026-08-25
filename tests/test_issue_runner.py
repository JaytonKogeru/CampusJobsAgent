from campus_jobs.issue_runner import parse_command


def test_plain_yaml():
    x = parse_command("url: https://example.com/jobs\nkeyword: AI\nscope: campus")
    assert x["keyword"] == "AI"
    assert x["scope"] == "campus"


def test_url_fallback():
    x = parse_command("帮我抓 https://example.com/jobs 里的岗位")
    assert x["url"] == "https://example.com/jobs"
