from campus_jobs.adapters.beisen_zhiye import BeisenZhiyeAdapter


def test_scope_mapping():
    assert BeisenZhiyeAdapter._default_scope("campus") == (["2"], "campus", "校招")
    assert BeisenZhiyeAdapter._default_scope("social") == (["1"], "social", "社招")
    assert BeisenZhiyeAdapter._default_scope("intern") == (["3"], "intern", "实习")


def test_portal_id_parsing():
    html = '<script>window.__CONFIG__={"PortalId":"abc-def-123"}</script>'
    assert BeisenZhiyeAdapter._portal_id(html) == "abc-def-123"


def test_dynamic_campus_category_parsing():
    payload = {
        "Code": 200,
        "Data": {
            "Categories": [
                {"Id": "1", "Name": "社会招聘"},
                {"Id": "39", "Name": "2027校园招聘"},
                {"Id": "3", "Name": "实习生招聘"},
            ]
        },
    }
    assert BeisenZhiyeAdapter._category_ids_from_conditions(payload, "campus") == ["39"]
    assert BeisenZhiyeAdapter._category_ids_from_conditions(payload, "social") == ["1"]
    assert BeisenZhiyeAdapter._category_ids_from_conditions(payload, "intern") == ["3"]


def test_location_and_null_date():
    item = {"LocNames": ["合肥", "北京"], "PostDate": "0001-01-01T00:00:00"}
    assert BeisenZhiyeAdapter._location(item) == "合肥 / 北京"
    assert BeisenZhiyeAdapter._published_at(item) == ""
