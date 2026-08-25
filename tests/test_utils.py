from campus_jobs.utils import clean_text, canonical_url


def test_clean_text_html():
    assert clean_text("<p>Hello<br>World</p>") == "Hello\nWorld"


def test_canonical_url_strips_tracking():
    got = canonical_url("https://example.com/a?utm_source=x&job=1")
    assert "utm_source" not in got and "job=1" in got
