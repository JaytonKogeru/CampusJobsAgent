from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text, unique_keep_order
from .base import BaseAdapter


class TPLinkGlobalAdapter(BaseAdapter):
    """Adapter for TP-Link Global's first-party careers site."""

    name = "tplink-global"
    priority = 120
    ROOT = "https://join.tplinkglobal.com"
    SEARCH = f"{ROOT}/cross_origin/v1/ads/search"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "join.tplinkglobal.com"

    @staticmethod
    def _scope_matches(item: dict[str, object], scope: str) -> bool:
        if scope in {"", "all"}:
            return True
        recruit = clean_text(item.get("recruit_category") or item.get("recruit_type")).lower()
        nature = clean_text(item.get("position_nature")).lower()
        text = f"{recruit} {nature}"
        if scope == "campus":
            return any(token in text for token in ["校园", "校招", "应届", "graduate", "campus"])
        if scope == "intern":
            return any(token in text for token in ["实习", "intern"])
        if scope == "social":
            return any(token in text for token in ["社会", "社招", "experienced", "social"])
        return True

    @staticmethod
    def _extract_location(item: dict[str, object]) -> str:
        preferred = [
            "work_location_name",
            "work_location_names",
            "work_location",
            "work_locations",
            "work_location_list",
            "workplace",
            "work_place",
            "location",
            "city",
            "city_name",
        ]

        def flatten(value: object) -> list[str]:
            if value in (None, "", []):
                return []
            if isinstance(value, str):
                return [clean_text(value)]
            if isinstance(value, dict):
                for key in ["name", "label", "city_name", "location_name", "value"]:
                    if value.get(key) not in (None, "", []):
                        return flatten(value.get(key))
                out: list[str] = []
                for sub in value.values():
                    out.extend(flatten(sub))
                return out
            if isinstance(value, list):
                out: list[str] = []
                for sub in value:
                    out.extend(flatten(sub))
                return out
            return [clean_text(value)]

        values: list[str] = []
        for key in preferred:
            if key in item:
                values.extend(flatten(item.get(key)))
        if not values:
            for key, value in item.items():
                low = key.lower()
                if "location" in low or "work_place" in low or "workplace" in low:
                    values.extend(flatten(value))
        return "、".join(unique_keep_order(v for v in values if v))

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()
        page_size = min(max(int(options.page_size or 50), 1), 100)

        with PublicClient(options.timeout) as client:
            for page_no in range(max(options.max_pages, 1)):
                body = {
                    "origin": "join.tplinkglobal.com:443",
                    "page_no": page_no,
                    "page_size": page_size,
                }
                try:
                    response = client.post(
                        self.SEARCH,
                        json=body,
                        headers={
                            "Origin": self.ROOT,
                            "Referer": f"{self.ROOT}/jobs",
                            "Accept": "application/json, text/plain, */*",
                        },
                    )
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"page {page_no}: {type(exc).__name__}: {exc}")
                    break

                data = payload.get("data") or {}
                rows = data.get("list") or []
                total = int(data.get("count") or 0)
                if not isinstance(rows, list) or not rows:
                    break

                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    if not self._scope_matches(item, options.scope):
                        continue

                    jid = clean_text(item.get("id") or item.get("position_id"))
                    title = clean_text(item.get("name"))
                    if not jid or not title or jid in seen:
                        continue

                    description = clean_text(item.get("job_responsibilities"))
                    requirements = clean_text(item.get("qualification"))
                    function = clean_text(item.get("position_type_name"))
                    recruit_type = clean_text(item.get("recruit_category") or item.get("position_nature"))
                    location = self._extract_location(item)
                    published_at = clean_text(item.get("publish_time"))

                    if options.keyword:
                        haystack = "\n".join([title, function, description, requirements, location]).lower()
                        if options.keyword.lower() not in haystack:
                            continue

                    seen.add(jid)
                    jobs.append(
                        Job(
                            id=jid,
                            title=title,
                            url=f"{self.ROOT}/jobs#job={jid}",
                            company="TP-Link联洲",
                            location=location,
                            function=function,
                            recruit_type=recruit_type,
                            description=description,
                            requirements=requirements,
                            source="join.tplinkglobal.com",
                            published_at=published_at,
                            extra=item,
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break

                if len(jobs) >= options.max_jobs:
                    break
                if len(rows) < page_size or ((page_no + 1) * page_size >= total > 0):
                    break

        return CrawlResult(self.name, url, jobs, warnings)
