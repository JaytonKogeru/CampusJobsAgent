from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class VivoCampusAdapter(BaseAdapter):
    name = "vivo-campus"
    priority = 110
    ROOT = "https://hr-campus.vivo.com"
    PORTAL_ID = "903cbcbf-4898-46e1-817c-da522a9752b1"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() == "hr-campus.vivo.com"

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        category = ["3"] if options.scope == "intern" else ["2"] if options.scope == "campus" else []
        jobs: list[Job] = []
        warnings: list[str] = []
        with PublicClient(options.timeout) as client:
            for page in range(options.max_pages):
                body = {
                    "PageIndex": page,
                    "PageSize": min(max(options.page_size, 1), 100),
                    "KeyWords": options.keyword,
                    "SpecialType": 0,
                    "PortalId": self.PORTAL_ID,
                }
                if category:
                    body["Category"] = category
                r = client.post(
                    f"{self.ROOT}/api/Jobad/GetJobAdPageList",
                    json=body,
                    headers={"Referer": f"{self.ROOT}/jobs", "Content-Type": "application/json"},
                )
                payload = r.json()
                rows = payload.get("Data") or []
                if not rows:
                    break
                for item in rows:
                    jid = str(item.get("JobAdId") or item.get("Id") or "")
                    if not jid:
                        continue
                    cat = str(item.get("Category") or (category[0] if category else ""))
                    jobs.append(
                        Job(
                            id=jid,
                            title=clean_text(item.get("JobAdName") or item.get("Name")),
                            url=f"{self.ROOT}/{'intern' if cat == '3' else 'campus'}/detail?jobAdId={jid}",
                            company="vivo",
                            location=clean_text(item.get("WorkPlace") or item.get("WorkPlaceName")),
                            department=clean_text(item.get("DepartmentName") or item.get("OrgName")),
                            function=clean_text(item.get("JobCategoryName") or item.get("CategoryName")),
                            recruit_type="实习" if cat == "3" else "校招",
                            description=clean_text(item.get("Duty")),
                            requirements=clean_text(item.get("Require")),
                            source="hr-campus.vivo.com",
                            extra=item,
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < body["PageSize"]:
                    break
        return CrawlResult(self.name, url, jobs, warnings)
