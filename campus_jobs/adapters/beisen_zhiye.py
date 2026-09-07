from __future__ import annotations

import re
from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text

from .base import BaseAdapter


_DISPLAY_FIELDS = [
    "Category",
    "Kind",
    "LocId",
    "PostDate",
    "Salary",
    "WorkWeChatQrCode",
]


class BeisenZhiyeAdapter(BaseAdapter):
    """Public Beisen/iTalent careers portals hosted on ``*.zhiye.com``.

    These portals expose an unauthenticated JSON endpoint at
    ``/api/Jobad/GetJobAdPageList``. Using that API is both faster and much more
    reliable than trying to scrape the React/canvas UI with Playwright.
    """

    name = "beisen-zhiye"
    priority = 90

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "zhiye.com" or host.endswith(".zhiye.com")

    @staticmethod
    def _scope(scope: str) -> tuple[str, str, str]:
        scope = (scope or "campus").strip().lower()
        if scope == "social":
            return "1", "social", "社招"
        if scope == "intern":
            return "3", "intern", "实习"
        return "2", "campus", "校招"

    @staticmethod
    def _portal_id(html: str) -> str:
        if not html:
            return ""
        for pattern in (
            r'["\']PortalId["\']\s*:\s*["\']([^"\']+)["\']',
            r'["\']portalId["\']\s*:\s*["\']([^"\']+)["\']',
            r'portalId=([0-9a-fA-F-]{16,})',
        ):
            match = re.search(pattern, html, re.I)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _location(item: dict) -> str:
        names = item.get("LocNames")
        if isinstance(names, list):
            return " / ".join(clean_text(x) for x in names if clean_text(x))
        return clean_text(item.get("LocName") or item.get("LocationName") or item.get("WorkPlace"))

    @staticmethod
    def _published_at(item: dict) -> str:
        raw = clean_text(item.get("PostDate") or "")
        if not raw or raw.startswith("0001-01-01"):
            return ""
        return raw

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        root = f"{p.scheme or 'https'}://{p.netloc}"
        category, path_scope, recruit_type = self._scope(options.scope)
        list_url = f"{root}/api/Jobad/GetJobAdPageList"
        referer = f"{root}/{path_scope}/jobs"

        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": root,
            "Referer": referer,
        }

        with PublicClient(options.timeout) as client:
            portal_id = ""
            try:
                portal_id = self._portal_id(client.get(referer).text)
            except Exception as exc:  # noqa: BLE001
                # PortalId is optional for standard tenants; continue with an empty id.
                warnings.append(f"portal config fetch failed: {type(exc).__name__}: {exc}")

            page_size = min(max(options.page_size, 1), 100)
            for page in range(options.max_pages):
                body = {
                    "PageIndex": page,
                    "PageSize": page_size,
                    "Category": [category],
                    "KeyWords": options.keyword or "",
                    "SpecialType": 0,
                    "PortalId": portal_id,
                    "DisplayFields": list(_DISPLAY_FIELDS),
                }

                payload = client.post(list_url, json=body, headers=headers).json()
                rows = payload.get("Data") if isinstance(payload, dict) else None
                if rows is None and isinstance(payload, dict):
                    rows = payload.get("data")
                if not isinstance(rows, list):
                    keys = list(payload.keys())[:20] if isinstance(payload, dict) else []
                    warnings.append(f"page {page}: no Data array; keys={keys}")
                    break
                if not rows:
                    break

                new_rows = 0
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    jid = clean_text(item.get("Id") or item.get("JobAdId") or "")
                    title = clean_text(item.get("JobAdName") or item.get("Name") or "")
                    if not jid or not title or jid in seen:
                        continue

                    description = clean_text(item.get("Duty") or item.get("Description") or "")
                    requirements = clean_text(item.get("Require") or item.get("Requirement") or "")
                    searchable = f"{title}\n{description}\n{requirements}".lower()
                    if options.keyword and options.keyword.lower() not in searchable:
                        continue

                    seen.add(jid)
                    new_rows += 1
                    detail_url = f"{root}/{path_scope}/detail?jobAdId={jid}"
                    jobs.append(
                        Job(
                            id=jid,
                            title=title,
                            url=detail_url,
                            company=clean_text(item.get("CompanyName") or item.get("TenantName") or ""),
                            location=self._location(item),
                            department=clean_text(
                                item.get("DepartmentName")
                                or item.get("OrgName")
                                or item.get("RecruitingOrgName")
                                or ""
                            ),
                            function=clean_text(item.get("KindName") or item.get("Kind") or ""),
                            recruit_type=recruit_type,
                            description=description,
                            requirements=requirements,
                            source=p.netloc,
                            published_at=self._published_at(item),
                            extra=item,
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break

                total = payload.get("Count") if isinstance(payload, dict) else None
                if (
                    len(jobs) >= options.max_jobs
                    or new_rows == 0
                    or len(rows) < page_size
                    or (isinstance(total, int) and len(seen) >= total)
                ):
                    break

        return CrawlResult(self.name, url, jobs, warnings)
