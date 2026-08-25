from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class GreenhouseAdapter(BaseAdapter):
    name = "greenhouse"
    priority = 70

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host in {"boards.greenhouse.io", "job-boards.greenhouse.io"} or "greenhouse" in host

    @staticmethod
    def _board(url: str) -> str:
        parts = [x for x in urlparse(url).path.split("/") if x]
        if not parts:
            raise ValueError("Greenhouse board token not found")
        return parts[0]

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        board = self._board(url)
        api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        with PublicClient(options.timeout) as client:
            rows = client.get(api).json().get("jobs") or []
        jobs: list[Job] = []
        kw = options.keyword.lower().strip()
        for item in rows:
            title = clean_text(item.get("title"))
            content = clean_text(item.get("content"))
            if kw and kw not in f"{title} {content}".lower():
                continue
            jid = str(item.get("id") or "")
            location = clean_text((item.get("location") or {}).get("name"))
            jobs.append(Job(id=jid, title=title, url=item.get("absolute_url") or url, location=location, description=content, source="greenhouse", extra=item))
            if len(jobs) >= options.max_jobs:
                break
        return CrawlResult(self.name, url, jobs)
