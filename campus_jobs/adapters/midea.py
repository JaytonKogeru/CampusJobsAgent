from __future__ import annotations

import re
from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text
from .base import BaseAdapter


class MideaCampusAdapter(BaseAdapter):
    """Adapter for Midea's public campus-recruitment API.

    The careers page is a SPA. Its public job list is served by
    /backend/school/position/common/position/list and already contains the full
    responsibility/requirement text inside projectPositionDto, so no per-job
    detail request is required.
    """

    name = "midea-campus"
    priority = 96

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        path = urlparse(url).path.lower()
        return host == "careers.midea.com" and ("schoolout" in path or "recruit-school" in path or path == "/")

    @staticmethod
    def _project_score(project: dict, scope: str) -> tuple[int, int]:
        name = clean_text(project.get("projectRuleName"))
        season = clean_text(project.get("season"))
        total = int(project.get("number") or 0)
        employ = str(project.get("employementCategory") or "")
        ptype = str(project.get("projectType") or "")

        score = 0
        if re.search(r"2027|27届", f"{name} {season}"):
            score += 100
        elif re.search(r"2026|26届", f"{name} {season}"):
            score -= 30

        if scope == "intern":
            if "实习" in name:
                score += 100
            if employ == "4":
                score += 30
        else:
            if any(x in name for x in ["应届生", "校园", "校招"]):
                score += 40
            if "实习" in name:
                score -= 120
            if "博士" in name:
                score -= 60
            if employ == "1":
                score += 25

        if ptype == "1":
            score += 10
        return score, total

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        root = "https://careers.midea.com"
        warnings: list[str] = []
        jobs: list[Job] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": root,
            "Referer": f"{root}/schoolOut/post",
            "X-Requested-With": "XMLHttpRequest",
        }

        with PublicClient(options.timeout) as client:
            project_url = (
                f"{root}/backend/school/position/common/project/list"
                "?status=1&projectTypes=1,2,9,5&employementCategories=1,4"
            )
            payload = client.get(project_url, headers=headers).json()
            projects = payload.get("data") or []
            if not isinstance(projects, list) or not projects:
                return CrawlResult(self.name, url, [], ["Midea project list returned no active projects"])

            candidates = sorted(
                (p for p in projects if isinstance(p, dict)),
                key=lambda p: self._project_score(p, options.scope),
                reverse=True,
            )
            selected = candidates[0]
            project_id = clean_text(selected.get("projectRuleId"))
            if not project_id:
                return CrawlResult(self.name, url, [], ["Midea active project has no projectRuleId"])

            project_name = clean_text(selected.get("projectRuleName"))
            if project_name:
                warnings.append(f"selected project: {project_name} ({project_id})")

            endpoint = f"{root}/backend/school/position/common/position/list"
            requested_page_size = min(max(options.page_size, 10), 100)
            seen: set[str] = set()
            total = 0
            previous_seen_count = -1

            for page in range(1, options.max_pages + 1):
                body = {
                    "keyword": options.keyword or None,
                    "superiorIds": [],
                    "recruitCategoryIds": [],
                    "workPlaceCodes": [],
                    "projectRuleId": project_id,
                    "pageIndex": page,
                    "pageSize": requested_page_size,
                }
                r = client.post(endpoint, json=body, headers=headers)
                data = (r.json().get("data") or {})
                rows = data.get("data") or []
                total = int(data.get("total") or total or 0)
                if not rows:
                    break

                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    dto = item.get("projectPositionDto") or {}
                    if not isinstance(dto, dict):
                        dto = {}
                    jid = clean_text(item.get("positionId") or item.get("projectPositionId") or dto.get("projectPositionId"))
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    title = clean_text(item.get("projectPositionName") or dto.get("positionName"))
                    if not title:
                        continue

                    workplace_list = item.get("workplaceDtoList") or []
                    locations = []
                    if isinstance(workplace_list, list):
                        for place in workplace_list:
                            if isinstance(place, dict):
                                n = clean_text(place.get("workPlaceName"))
                                if n and n not in locations:
                                    locations.append(n)
                    location = " / ".join(locations) or clean_text(item.get("workPlaceCode"))
                    function = clean_text(item.get("recruitCategoryName") or dto.get("largeTypeName"))
                    description = clean_text(dto.get("jobResponsibility"))
                    requirements = clean_text(dto.get("jobRequirement"))
                    position_code = clean_text(dto.get("positionCode"))

                    jobs.append(
                        Job(
                            id=jid,
                            title=title,
                            url=f"{root}/schoolOut/post",
                            location=location,
                            function=function,
                            recruit_type="实习" if options.scope == "intern" else "校招",
                            description=description,
                            requirements=requirements,
                            source="careers.midea.com",
                            extra={
                                **item,
                                "selectedProjectRuleId": project_id,
                                "selectedProjectRuleName": project_name,
                                "positionCode": position_code,
                            },
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break

                if len(jobs) >= options.max_jobs:
                    break
                if total and len(seen) >= total:
                    break
                # Midea currently caps the effective response page size (e.g.
                # 20) even when a larger pageSize is requested, so row count
                # cannot be used as an end-of-pagination signal. Stop only if
                # the next page fails to contribute any new IDs.
                if len(seen) == previous_seen_count:
                    break
                previous_seen_count = len(seen)

            if total and len(seen) < total and len(jobs) < options.max_jobs:
                warnings.append(f"pagination incomplete: fetched={len(seen)}, api_total={total}, max_pages={options.max_pages}")

        return CrawlResult(self.name, url, jobs, warnings)
