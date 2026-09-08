from __future__ import annotations

import os
import shutil
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text, unique_keep_order

from .base import BaseAdapter


class ATSXAdapter(BaseAdapter):
    """Feishu Recruiting / ATSX family, including Xiaomi's mioffice fork."""

    name = "atsx"
    priority = 90

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host.endswith(("jobs.f.mioffice.cn", "jobs.bytedance.com")) or ".jobs.feishu.cn" in host

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

    @staticmethod
    def _body(url: str, options: CrawlOptions, offset: int, limit: int) -> dict[str, object]:
        query = parse_qs(urlparse(url).query)
        body: dict[str, object] = {
            "keyword": options.keyword,
            "limit": limit,
            "offset": offset,
            "portal_type": 3,
            "portal_entrance": 1,
            "language": "zh",
        }
        if options.scope == "campus":
            body["recruitment_id_list"] = ["201"]
        elif options.scope == "intern":
            body["recruitment_id_list"] = ["202"]
        project_ids = [x for x in query.get("project", []) if x]
        if project_ids:
            body["subject_id_list"] = project_ids
        return body

    @staticmethod
    def _job(item: dict, root: str, host: str, scope: str) -> Job | None:
        jid = str(item.get("id") or "")
        title = clean_text(item.get("title"))
        if not jid or not title:
            return None
        cities = unique_keep_order(
            [x.get("name", "") for x in (item.get("city_list") or []) if isinstance(x, dict)]
            + [((item.get("city_info") or {}).get("name", ""))]
        )
        detail_path = "internship" if scope == "intern" else "campus"
        return Job(
            id=jid,
            title=title,
            url=f"{root}/{detail_path}/position/{jid}/detail",
            location=" / ".join(cities),
            function=clean_text((item.get("job_function") or {}).get("name")),
            recruit_type=clean_text((item.get("recruit_type") or {}).get("name")),
            description=clean_text(item.get("description")),
            requirements=clean_text(item.get("requirement")),
            source=host,
            extra=item,
        )

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        try:
            return self._crawl_api(url, options)
        except Exception as direct_exc:  # noqa: BLE001 - resilience boundary
            try:
                result = self._crawl_browser(url, options)
                result.adapter = f"{self.name}->browser-api"
                result.warnings.insert(
                    0,
                    f"ATSX direct API failed; browser-context API used: {type(direct_exc).__name__}: {direct_exc}",
                )
                return result
            except Exception as browser_exc:  # noqa: BLE001 - final fallback
                from .generic_browser import GenericBrowserAdapter

                fallback = GenericBrowserAdapter().crawl(self._url_with_keyword(url, options.keyword), options)
                fallback.adapter = f"{self.name}->generic-browser"
                fallback.warnings.insert(
                    0,
                    "ATSX direct/browser API failed; generic browser used: "
                    f"direct={type(direct_exc).__name__}: {direct_exc}; "
                    f"browser={type(browser_exc).__name__}: {browser_exc}",
                )
                return fallback

    @staticmethod
    def _url_with_keyword(url: str, keyword: str) -> str:
        if not keyword:
            return url
        p = urlparse(url)
        q = parse_qs(p.query, keep_blank_values=True)
        q["keywords"] = [keyword]
        query = urlencode([(k, v) for k, vals in q.items() for v in vals])
        return urlunparse((p.scheme, p.netloc, p.path, p.params, query, p.fragment))

    @staticmethod
    def _page_url(url: str, keyword: str, current: int, limit: int) -> str:
        p = urlparse(url)
        q = parse_qs(p.query, keep_blank_values=True)
        if keyword:
            q["keywords"] = [keyword]
        q["current"] = [str(current)]
        q["limit"] = [str(limit)]
        query = urlencode([(k, v) for k, vals in q.items() for v in vals])
        return urlunparse((p.scheme, p.netloc, p.path, p.params, query, p.fragment))

    def _crawl_api(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        host = p.hostname or ""
        root = f"{p.scheme or 'https'}://{host}"
        search_api = f"{root}/api/v1/search/job/posts"
        headers = self._headers(host, options.scope)
        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()
        with PublicClient(options.timeout) as client:
            for page in range(options.max_pages):
                limit = min(max(options.page_size, 1), 100)
                body = self._body(url, options, page * limit, limit)
                payload = client.post(search_api, headers=headers, json=body).json()
                if payload.get("code") not in (None, 0):
                    raise RuntimeError(f"ATSX upstream error: {payload.get('message') or payload.get('code')}")
                rows = (payload.get("data") or {}).get("job_post_list") or []
                if not rows:
                    break
                for item in rows:
                    job = self._job(item, root, host, options.scope)
                    if job is None or job.id in seen:
                        continue
                    seen.add(job.id)
                    jobs.append(job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < limit:
                    break

            if options.include_details:
                self._fill_details_http(client, root, jobs, warnings)
        return CrawlResult(self.name, url, jobs, warnings)

    @staticmethod
    def _fill_details_http(client: PublicClient, root: str, jobs: list[Job], warnings: list[str]) -> None:
        for job in jobs:
            if job.description and job.requirements:
                continue
            try:
                dr = client.get(
                    f"{root}/api/v1/job/posts/{job.id}",
                    headers={"portal-platform": "pc", "Accept": "application/json"},
                )
                detail = ((dr.json().get("data") or {}).get("job_post_detail") or {})
                job.description = clean_text(detail.get("description")) or job.description
                job.requirements = clean_text(detail.get("requirement")) or job.requirements
                job.department = clean_text((detail.get("department") or {}).get("name"))
                job.extra.update(detail)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"detail {job.id}: {exc}")

    def _crawl_browser(self, url: str, options: CrawlOptions) -> CrawlResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright not installed") from exc

        purl = urlparse(url)
        host = purl.hostname or ""
        root = f"{purl.scheme or 'https'}://{host}"
        headers = self._headers(host, options.scope)
        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()
        captured_pages: list[dict] = []

        with sync_playwright() as p:
            launch: dict[str, object] = {"headless": True}
            chrome = next(
                (
                    path
                    for path in [
                        shutil.which("google-chrome"),
                        shutil.which("google-chrome-stable"),
                        shutil.which("chromium"),
                        shutil.which("chromium-browser"),
                    ]
                    if path
                ),
                None,
            )
            if chrome:
                launch["executable_path"] = chrome
            proxy = os.getenv("CAMPUS_JOBS_PROXY", "").strip()
            if proxy:
                launch["proxy"] = {"server": proxy}
            browser = p.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            def on_response(response):
                try:
                    data = response.json()
                    body = data.get("data") if isinstance(data, dict) else None
                    if isinstance(body, dict) and isinstance(body.get("job_post_list"), list):
                        captured_pages.append(data)
                except Exception:
                    return

            page.on("response", on_response)

            for page_index in range(options.max_pages):
                limit = min(max(options.page_size, 1), 100)
                body = self._body(url, options, page_index * limit, limit)
                result: dict[str, object] = {}
                try:
                    result = page.evaluate(
                        """
                        async ({endpoint, body, headers}) => {
                          const response = await fetch(endpoint, {
                            method: 'POST',
                            credentials: 'include',
                            headers,
                            body: JSON.stringify(body),
                          });
                          let data = null;
                          try { data = await response.json(); } catch (_) {}
                          return {status: response.status, data};
                        }
                        """,
                        {
                            "endpoint": f"{root}/api/v1/search/job/posts",
                            "body": body,
                            "headers": {k: v for k, v in headers.items() if k.lower() != "referer"},
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"browser API page {page_index + 1}: {exc}")

                payload = result.get("data") if isinstance(result, dict) else None
                if not isinstance(payload, dict) or result.get("status") != 200:
                    # Some Feishu career portals reject our explicit POST but their
                    # own page request still works. Navigate to each UI page and
                    # consume the newly captured job_post_list response so pagination
                    # and project/category filters are preserved exactly.
                    captured_before = len(captured_pages)
                    page.goto(
                        self._page_url(url, options.keyword, page_index + 1, limit),
                        wait_until="domcontentloaded",
                        timeout=int(options.timeout * 1000),
                    )
                    page.wait_for_timeout(min(options.browser_wait_ms, 4000))
                    new_pages = captured_pages[captured_before:]
                    payload = new_pages[-1] if new_pages else None

                rows = ((payload or {}).get("data") or {}).get("job_post_list") or []
                if not rows:
                    if jobs:
                        break
                    if page_index == 0:
                        raise RuntimeError(
                            f"browser ATSX API produced no job_post_list (status={result.get('status')})"
                        )
                    break
                for item in rows:
                    job = self._job(item, root, host, options.scope)
                    if job is None or job.id in seen:
                        continue
                    if options.keyword and options.keyword.lower() not in job.full_text.lower():
                        continue
                    seen.add(job.id)
                    jobs.append(job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < limit:
                    break
            browser.close()
        return CrawlResult(self.name, url, jobs, warnings)
