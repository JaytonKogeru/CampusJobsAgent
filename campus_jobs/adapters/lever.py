from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class LeverAdapter(BaseAdapter):
    name = "lever"
    priority = 70

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() in {"jobs.lever.co", "jobs.eu.lever.co"}

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        company = [x for x in p.path.split("/") if x][0]
        api = f"{p.scheme}://{p.netloc}/{company}?mode=json"
        with PublicClient(options.timeout) as client:
            rows = client.get(api).json()
        jobs: list[Job] = []
        kw = options.keyword.lower().strip()
        for item in rows:
            title = clean_text(item.get("text"))
            desc = clean_text(item.get("descriptionPlain") or item.get("description"))
            req = clean_text(item.get("additionalPlain") or item.get("additional"))
            if kw and kw not in f"{title} {desc} {req}".lower():
                continue
            cats = item.get("categories") or {}
            jobs.append(Job(
                id=str(item.get("id") or ""), title=title, url=item.get("hostedUrl") or item.get("applyUrl") or url,
                company=company, location=clean_text(cats.get("location")), department=clean_text(cats.get("team")),
                function=clean_text(cats.get("commitment")), description=desc, requirements=req, source="lever", extra=item,
            ))
            if len(jobs) >= options.max_jobs:
                break
        return CrawlResult(self.name, url, jobs)
