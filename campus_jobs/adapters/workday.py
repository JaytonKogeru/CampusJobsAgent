from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class WorkdayAdapter(BaseAdapter):
    name = "workday"
    priority = 65

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return "myworkdayjobs.com" in host or ".wd" in host and "workday" in host

    @staticmethod
    def _site(url: str) -> tuple[str, str, str]:
        p = urlparse(url)
        parts = [x for x in p.path.split("/") if x]
        # common: /en-US/SiteName or /SiteName
        site = parts[1] if len(parts) >= 2 and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]) else parts[0] if parts else ""
        if not site:
            raise ValueError("Workday site name not found")
        tenant = (p.hostname or "").split(".")[0]
        return f"{p.scheme}://{p.netloc}", tenant, site

    @staticmethod
    def _search_text(url: str, keyword: str) -> str:
        if keyword:
            return keyword
        query = parse_qs(urlparse(url).query)
        return clean_text((query.get("q") or query.get("searchText") or [""])[0])

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        root, tenant, site = self._site(url)
        api = f"{root}/wday/cxs/{tenant}/{site}/jobs"
        search_text = self._search_text(url, options.keyword)
        jobs: list[Job] = []
        warnings: list[str] = []
        with PublicClient(options.timeout) as client:
            for page in range(options.max_pages):
                limit = min(max(options.page_size, 1), 20)
                body = {
                    "appliedFacets": {},
                    "limit": limit,
                    "offset": page * limit,
                    "searchText": search_text,
                }
                data = client.post(api, json=body, headers={"Referer": url, "Accept": "application/json"}).json()
                rows = data.get("jobPostings") or []
                if not rows:
                    break
                for item in rows:
                    ext = item.get("externalPath") or ""
                    jid = str((item.get("bulletFields") or [""])[0]) if item.get("bulletFields") else ext
                    detail = {}
                    if options.include_details and ext:
                        try:
                            detail = client.get(
                                f"{root}/wday/cxs/{tenant}/{site}{ext}", headers={"Referer": url}
                            ).json().get("jobPostingInfo") or {}
                        except Exception as exc:  # noqa: BLE001
                            warnings.append(f"detail {ext}: {exc}")
                    jobs.append(
                        Job(
                            id=jid,
                            title=clean_text(item.get("title")),
                            url=f"{root}{ext}" if ext else url,
                            location=clean_text(item.get("locationsText")),
                            description=clean_text(detail.get("jobDescription")),
                            source="workday",
                            extra={**item, **detail},
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < limit:
                    break
        return CrawlResult(self.name, url, jobs, warnings)
