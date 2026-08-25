from __future__ import annotations

from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class OppoAdapter(BaseAdapter):
    name = "oppo"
    priority = 110
    ROOT = "https://careers.oppo.com"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() == "careers.oppo.com"

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        jobs: list[Job] = []
        warnings: list[str] = []
        recruit_types: list[str | None]
        if options.scope == "intern":
            recruit_types = ["Intern"]
        elif options.scope == "campus":
            recruit_types = ["Graduate", "doctor"]
        else:
            recruit_types = [None]
        with PublicClient(options.timeout) as client:
            seen: set[str] = set()
            for recruit_type in recruit_types:
                for page in range(1, options.max_pages + 1):
                    body: dict[str, object] = {"pageNum": page, "pageSize": min(max(options.page_size, 1), 100)}
                    if recruit_type:
                        body["recruitmentType"] = recruit_type
                    if options.keyword:
                        body["positionName"] = options.keyword
                    r = client.post(
                        f"{self.ROOT}/openapi/position/pageNew",
                        json=body,
                        headers={"Origin": self.ROOT, "Referer": f"{self.ROOT}/", "Accept": "application/json"},
                    )
                    payload = r.json()
                    data = payload.get("data") or {}
                    rows = data.get("records") or data.get("list") or data.get("rows") or []
                    if not rows:
                        break
                    for item in rows:
                        jid = str(item.get("idRecruitPosition") or item.get("idProjPosition") or item.get("projectPositionId") or "")
                        if not jid or jid in seen:
                            continue
                        seen.add(jid)
                        jobs.append(
                            Job(
                                id=jid,
                                title=clean_text(item.get("positionName") or item.get("projectPositionName")),
                                url=f"{self.ROOT}/#/campus/talent/positionDetail/{jid}",
                                company="OPPO",
                                location=clean_text(item.get("workCityName")),
                                function=clean_text(item.get("positionTypeName")),
                                recruit_type=clean_text(item.get("recruitmentTypeName") or item.get("recruitmentType")),
                                source="careers.oppo.com",
                                extra=item,
                            )
                        )
                        if len(jobs) >= options.max_jobs:
                            break
                    if len(jobs) >= options.max_jobs or len(rows) < body["pageSize"]:
                        break
            if options.include_details:
                for job in jobs:
                    try:
                        dr = client.get(
                            f"{self.ROOT}/openapi/position/detail",
                            params={"idRecruitPosition": job.id},
                            headers={"Referer": f"{self.ROOT}/", "Accept": "application/json"},
                        )
                        d = dr.json().get("data") or {}
                        job.description = clean_text(d.get("positionResponsibility") or d.get("jobDuty") or d.get("description"))
                        job.requirements = clean_text(d.get("positionRequirement") or d.get("jobRequire") or d.get("requirement"))
                        job.department = clean_text(d.get("departmentName") or d.get("organizationName"))
                        job.extra.update(d)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"detail {job.id}: {exc}")
        return CrawlResult(self.name, url, jobs, warnings)
