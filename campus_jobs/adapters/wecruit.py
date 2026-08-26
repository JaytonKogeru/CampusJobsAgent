from __future__ import annotations

import re
import time
from urllib.parse import urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text

from .base import BaseAdapter


class WecruitAdapter(BaseAdapter):
    name = "wecruit"
    priority = 80

    @classmethod
    def can_handle(cls, url: str) -> bool:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        return (
            "wecruit" in p.path.lower()
            or host == "wecruit.hotjob.cn"
            or bool(re.search(r"/SU[a-zA-Z0-9]+/(?:pb|mc)/", p.path))
        )

    @staticmethod
    def _channel(url: str) -> tuple[str, str, bool]:
        """Return (company/channel id, legacy page path, modern_mc)."""
        p = urlparse(url)
        modern = re.search(r"/(SU[a-zA-Z0-9]+)/mc/(?:detail|index|jobs?)", p.path)
        if modern:
            return modern.group(1), "index", True

        legacy = re.search(r"/(SU[a-zA-Z0-9]+)/pb/([^/.]+)\.html", p.path)
        if legacy:
            return legacy.group(1), legacy.group(2), False

        # Some public Hotjob links point to /SUxxxx/ without an explicit page.
        generic = re.search(r"/(SU[a-zA-Z0-9]+)(?:/|$)", p.path)
        if generic:
            return generic.group(1), "index", True
        raise ValueError("Wecruit channel id not found in URL")

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        root = f"{p.scheme or 'https'}://{p.netloc}"
        channel, page_path, modern_mc = self._channel(url)
        recruit_type = 2 if options.scope == "social" else 12 if options.scope == "intern" else 1
        recruit_type_name = "社招" if recruit_type == 2 else "实习" if recruit_type == 12 else "校招"
        recruit_type_query = "social" if recruit_type == 2 else "intern" if recruit_type == 12 else "campus"

        jobs: list[Job] = []
        warnings: list[str] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": root,
            "Referer": (
                f"{root}/{channel}/mc/detail?recruitType={recruit_type_query}"
                if modern_mc
                else f"{root}/{channel}/pb/{page_path}.html"
            ),
            "X-Requested-With": "XMLHttpRequest",
        }

        with PublicClient(options.timeout) as client:
            seen: set[str] = set()
            for page in range(1, options.max_pages + 1):
                endpoint = (
                    f"{root}/wecruit/positionInfo/listPosition/{channel}"
                    f"?iSaJAx=isAjax&request_locale=zh_CN&t={int(time.time() * 1000)}"
                )
                form: dict[str, object] = {
                    "isFrompb": "true",
                    "recruitType": recruit_type,
                    "pageSize": options.page_size,
                    "currentPage": page,
                }
                if options.keyword:
                    form["postName"] = options.keyword
                r = client.post(endpoint, data=form, headers=headers)
                payload = r.json()
                if str(payload.get("state")) not in {"200", "0", "None"}:
                    warnings.append(f"list page {page}: upstream state={payload.get('state')}")
                data = payload.get("data") or {}
                page_form = data.get("pageForm") or {}
                rows = page_form.get("pageData") or []
                if not rows:
                    break

                new_rows = 0
                for item in rows:
                    jid = str(item.get("postId") or "")
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    new_rows += 1
                    job_url = (
                        f"{root}/{channel}/mc/detail?postId={jid}&recruitType={recruit_type_query}"
                        if modern_mc
                        else f"{root}/{channel}/pb/{page_path}.html#/postDetail?postId={jid}"
                    )
                    jobs.append(
                        Job(
                            id=jid,
                            title=clean_text(item.get("postName")),
                            url=job_url,
                            location=clean_text(item.get("workPlaceStr")),
                            department=clean_text(item.get("department") or item.get("orgName")),
                            function=clean_text(item.get("postTypeName")),
                            recruit_type=recruit_type_name,
                            source=p.netloc,
                            extra=item,
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break

                total_page = int(page_form.get("totalPage") or page)
                total_count = int(data.get("positonNum") or page_form.get("totalCount") or 0)
                if (
                    len(jobs) >= options.max_jobs
                    or page >= total_page
                    or (total_count and len(seen) >= total_count)
                    or new_rows == 0
                ):
                    break

            if options.include_details:
                for job in jobs:
                    try:
                        endpoint = (
                            f"{root}/wecruit/positionInfo/listPositionDetail/{channel}"
                            f"?iSaJAx=isAjax&request_locale=zh_CN&t={int(time.time() * 1000)}"
                        )
                        r = client.post(
                            endpoint,
                            data={"postId": job.id, "recruitType": recruit_type},
                            headers=headers,
                        )
                        detail = (r.json().get("data") or {})
                        job.description = clean_text(detail.get("workContent"))
                        job.requirements = clean_text(detail.get("serviceCondition"))
                        job.department = clean_text(detail.get("orgName")) or job.department
                        job.location = clean_text(detail.get("workPlaceStr")) or job.location
                        job.function = clean_text(detail.get("postTypeName")) or job.function
                        job.extra.update(detail)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"detail {job.id}: {exc}")

        return CrawlResult(self.name, url, jobs, warnings)
