from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class SmartRecruitersAdapter(BaseAdapter):
    name = "smartrecruiters"
    priority = 70

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "smartrecruiters.com" in (urlparse(url).hostname or "").lower()

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        parts = [x for x in urlparse(url).path.split("/") if x]
        if not parts:
            raise ValueError("SmartRecruiters company slug not found")
        company = parts[0]
        jobs: list[Job] = []
        with PublicClient(options.timeout) as client:
            for page in range(options.max_pages):
                params = {"limit": min(options.page_size, 100), "offset": page * min(options.page_size, 100)}
                if options.keyword:
                    params["q"] = options.keyword
                data = client.get(f"https://api.smartrecruiters.com/v1/companies/{company}/postings", params=params).json()
                rows = data.get("content") or []
                if not rows:
                    break
                for item in rows:
                    jid = str(item.get("id") or "")
                    title = clean_text(item.get("name"))
                    loc = item.get("location") or {}
                    detail = item
                    if options.include_details and jid:
                        try:
                            detail = client.get(f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{jid}").json()
                        except Exception:
                            pass
                    sections = detail.get("jobAd") or {}
                    jobs.append(Job(
                        id=jid, title=title, url=f"https://jobs.smartrecruiters.com/{company}/{jid}", company=company,
                        location=clean_text(", ".join(x for x in [loc.get("city", ""), loc.get("region", ""), loc.get("country", "")] if x)),
                        department=clean_text((item.get("department") or {}).get("label")),
                        function=clean_text((item.get("function") or {}).get("label")),
                        description=clean_text((sections.get("companyDescription") or {}).get("text") or (sections.get("jobDescription") or {}).get("text")),
                        requirements=clean_text((sections.get("qualifications") or {}).get("text")), source="smartrecruiters", extra=detail,
                    ))
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < params["limit"]:
                    break
        return CrawlResult(self.name, url, jobs)
