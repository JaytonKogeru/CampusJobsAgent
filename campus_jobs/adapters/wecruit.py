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
        return "wecruit" in p.path.lower() or p.hostname == "wecruit.hotjob.cn" or bool(re.search(r"/SU[a-zA-Z0-9]+/pb/", p.path))

    @staticmethod
    def _channel(url: str) -> tuple[str, str]:
        p = urlparse(url)
        m = re.search(r"/(SU[a-zA-Z0-9]+)/pb/([^/.]+)\.html", p.path)
        if not m:
            raise ValueError("Wecruit channel id not found in URL")
        return m.group(1), m.group(2)

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        root = f"{p.scheme}://{p.netloc}"
        channel, page_path = self._channel(url)
        recruit_type = 2 if options.scope == "social" else 1
        jobs: list[Job] = []
        warnings: list[str] = []
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": root,
            "Referer": f"{root}/{channel}/pb/{page_path}.html",
            "X-Requested-With": "XMLHttpRequest",
        }
        with PublicClient(options.timeout) as client:
            for page in range(1, options.max_pages + 1):
                endpoint = f"{root}/wecruit/positionInfo/listPosition/{channel}?iSaJAx=isAjax&request_locale=zh_CN&t={int(time.time()*1000)}"
                form = {"isFrompb": "true", "recruitType": recruit_type, "pageSize": options.page_size, "currentPage": page}
                if options.keyword:
                    form["postName"] = options.keyword
                r = client.post(endpoint, data=form, headers=headers)
                payload = r.json()
                page_form = ((payload.get("data") or {}).get("pageForm") or {})
                rows = page_form.get("pageData") or []
                if not rows:
                    break
                for item in rows:
                    jid = str(item.get("postId") or "")
                    if not jid:
                        continue
                    jobs.append(
                        Job(
                            id=jid,
                            title=clean_text(item.get("postName")),
                            url=f"{root}/{channel}/pb/{page_path}.html#/postDetail?postId={jid}",
                            location=clean_text(item.get("workPlaceStr")),
                            department=clean_text(item.get("department") or item.get("orgName")),
                            function=clean_text(item.get("postTypeName")),
                            recruit_type="社招" if recruit_type == 2 else "校招",
                            source=p.netloc,
                            extra=item,
                        )
                    )
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or page >= int(page_form.get("totalPage") or page):
                    break
            if options.include_details:
                for job in jobs:
                    try:
                        endpoint = f"{root}/wecruit/positionInfo/listPositionDetail/{channel}?iSaJAx=isAjax&request_locale=zh_CN&t={int(time.time()*1000)}"
                        r = client.post(endpoint, data={"postId": job.id, "recruitType": recruit_type}, headers=headers)
                        detail = (r.json().get("data") or {})
                        job.description = clean_text(detail.get("workContent"))
                        job.requirements = clean_text(detail.get("serviceCondition"))
                        job.department = clean_text(detail.get("orgName")) or job.department
                        job.extra.update(detail)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"detail {job.id}: {exc}")
        return CrawlResult(self.name, url, jobs, warnings)
