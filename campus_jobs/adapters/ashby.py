from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class AshbyAdapter(BaseAdapter):
    name = "ashby"
    priority = 70

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() == "jobs.ashbyhq.com"

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        board = [x for x in urlparse(url).path.split("/") if x][0]
        api = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
        with PublicClient(options.timeout) as client:
            rows = (client.get(api).json().get("jobs") or [])
        jobs: list[Job] = []
        kw = options.keyword.lower().strip()
        for item in rows:
            title = clean_text(item.get("title"))
            desc = clean_text(item.get("descriptionPlain") or item.get("descriptionHtml"))
            if kw and kw not in f"{title} {desc}".lower():
                continue
            jobs.append(Job(
                id=str(item.get("id") or ""), title=title, url=item.get("jobUrl") or item.get("applyUrl") or url,
                location=clean_text(item.get("location")), department=clean_text(item.get("department")),
                recruit_type=clean_text(item.get("employmentType")), description=desc, source="ashby", extra=item,
            ))
            if len(jobs) >= options.max_jobs:
                break
        return CrawlResult(self.name, url, jobs)
