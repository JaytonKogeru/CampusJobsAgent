from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text, unique_keep_order
from .base import BaseAdapter


class ATSXAdapter(BaseAdapter):
    """Feishu Recruiting / ATSX family, including Xiaomi's mioffice fork.

    Direct public API is preferred. Some ATSX tenants vary their edge behavior
    by egress/headers; if the anonymous API rejects a runner, we transparently
    fall back to the Playwright/XHR adapter instead of failing the crawl.
    """

    name = "atsx"
    priority = 90

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host.endswith("jobs.f.mioffice.cn") or host.endswith("jobs.bytedance.com") or ".jobs.feishu.cn" in host

    def _headers(self, host: str, scope: str) -> dict[str, str]:
        scope = scope if scope in {"campus", "intern", "social"} else "campus"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "portal-platform": "pc",
        }
        if host.endswith("jobs.f.mioffice.cn"):
            channel = "internship" if scope == "intern" else "campus"
            if scope != "social":
                headers["portal-channel"] = channel
                headers["website-path"] = channel
                headers["Referer"] = f"https://{host}/{channel}/"
            else:
                headers["Referer"] = f"https://{host}/"
        return headers

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        try:
            return self._crawl_api(url, options)
        except Exception as exc:  # noqa: BLE001 - deliberate resilience boundary
            from .generic_browser import GenericBrowserAdapter

            fallback = GenericBrowserAdapter().crawl(url, options)
            fallback.adapter = f"{self.name}->generic-browser"
            fallback.warnings.insert(0, f"ATSX direct API failed; browser fallback used: {type(exc).__name__}: {exc}")
            return fallback

    def _crawl_api(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        host = p.hostname or ""
        root = f"{p.scheme or 'https'}://{host}"
        search_api = f"{root}/api/v1/search/job/posts"
        headers = self._headers(host, options.scope)
        query = parse_qs(p.query)
        project_ids = [x for x in query.get("project", []) if x]
        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()
        with PublicClient(options.timeout) as client:
            for page in range(options.max_pages):
                limit = min(max(options.page_size, 1), 100)
                body: dict[str, object] = {
                    "keyword": options.keyword,
                    "limit": limit,
                    "offset": page * limit,
                    "portal_type": 3,
                    "portal_entrance": 1,
                    "language": "zh",
                }
                if options.scope == "campus":
                    body["recruitment_id_list"] = ["201"]
                elif options.scope == "intern":
                    body["recruitment_id_list"] = ["202"]
                if project_ids:
                    body["subject_id_list"] = project_ids
                r = client.post(search_api, headers=headers, json=body)
                payload = r.json()
                if payload.get("code") not in (None, 0):
                    raise RuntimeError(f"ATSX upstream error: {payload.get('message') or payload.get('code')}")
                data = payload.get("data") or {}
                rows = data.get("job_post_list") or []
                if not rows:
                    break
                for item in rows:
                    jid = str(item.get("id") or "")
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    cities = unique_keep_order(
                        [x.get("name", "") for x in (item.get("city_list") or []) if isinstance(x, dict)]
                        + [((item.get("city_info") or {}).get("name", ""))]
                    )
                    detail_path = "internship" if options.scope == "intern" else "campus"
                    job = Job(
                        id=jid,
                        title=clean_text(item.get("title")),
                        url=f"{root}/{detail_path}/position/{jid}/detail",
                        location=" / ".join(cities),
                        function=clean_text((item.get("job_function") or {}).get("name")),
                        recruit_type=clean_text((item.get("recruit_type") or {}).get("name")),
                        description=clean_text(item.get("description")),
                        requirements=clean_text(item.get("requirement")),
                        source=host,
                        extra=item,
                    )
                    jobs.append(job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < limit:
                    break

            if options.include_details:
                for job in jobs:
                    if job.description and job.requirements:
                        continue
                    try:
                        detail_headers = {"portal-platform": "pc", "Accept": "application/json"}
                        dr = client.get(f"{root}/api/v1/job/posts/{job.id}", headers=detail_headers)
                        detail = ((dr.json().get("data") or {}).get("job_post_detail") or {})
                        job.description = clean_text(detail.get("description")) or job.description
                        job.requirements = clean_text(detail.get("requirement")) or job.requirements
                        job.department = clean_text((detail.get("department") or {}).get("name"))
                        job.extra.update(detail)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"detail {job.id}: {exc}")
        return CrawlResult(self.name, url, jobs, warnings)
