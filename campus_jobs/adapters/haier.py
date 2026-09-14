from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import canonical_url, clean_text

from .base import BaseAdapter


class HaierCampusAdapter(BaseAdapter):
    """Native adapter for Haier's public campus-recruitment endpoints.

    Haier renders the campus list with JavaScript, but the page calls a stable
    public JSON endpoint using ordinary form-encoded POST requests. Using that
    endpoint avoids DOM pagination and keeps the browser adapter as a fallback
    for genuinely unknown sites.
    """

    name = "haier-campus"
    priority = 98
    root = "https://maker.haier.net"
    list_endpoint = f"{root}/client/campus/getactivityresearchlist.html"

    @classmethod
    def can_handle(cls, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        return host == "maker.haier.net" and path.startswith("/client/campus/")

    @staticmethod
    def _activity_id(url: str, html: str) -> tuple[str, str]:
        match = re.search(r"/id/(\d+)(?:/|\.|$)", url)
        url_aid = match.group(1) if match else ""

        soup = BeautifulSoup(html, "html.parser")
        selected = soup.select_one('input[name="aid"][checked]')
        if selected is not None:
            aid = clean_text(selected.get("value"))
            title = clean_text(selected.get("title"))
            if aid:
                return aid, title

        if url_aid:
            return url_aid, ""

        candidates = soup.select('input[name="aid"]')
        for node in candidates:
            title = clean_text(node.get("title"))
            aid = clean_text(node.get("value"))
            if aid and re.search(r"2027|27届", title):
                return aid, title
        if candidates:
            return clean_text(candidates[0].get("value")), clean_text(candidates[0].get("title"))
        return "", ""

    @classmethod
    def _job_from_item(cls, item: dict, activity_id: str, activity_name: str) -> Job | None:
        jid = clean_text(item.get("id"))
        title = clean_text(item.get("name"))
        if not jid or not title:
            return None
        raw_url = clean_text(item.get("click_url"))
        job_url = canonical_url(raw_url, cls.root) if raw_url else ""
        if not job_url:
            function_id = clean_text(item.get("function_id"))
            if function_id:
                job_url = (
                    f"{cls.root}/client/campus/deliverfirst/id/{activity_id}/"
                    f"fid/{function_id}/rid/{jid}.html"
                )
            else:
                job_url = f"{cls.root}/client/campus/activityindex.html#job={jid}"

        return Job(
            id=jid,
            title=title,
            url=job_url,
            company="海尔集团",
            location=clean_text(item.get("addr")),
            department=clean_text(item.get("department")),
            function=clean_text(item.get("fun_name")),
            recruit_type="校招",
            source="maker.haier.net",
            extra={
                **item,
                "selectedActivityId": activity_id,
                "selectedActivityName": activity_name,
            },
        )

    @staticmethod
    def _parse_detail(html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        sections: dict[str, str] = {}
        for title_node in soup.select(".demand_title"):
            label = clean_text(title_node.get_text(" ", strip=True))
            box = title_node.find_next_sibling("div", class_="demand_box")
            if box is not None and label:
                sections[label] = clean_text(box.get_text("\n", strip=True))

        departments: list[str] = []
        for node in soup.select(".department_title_item"):
            value = clean_text(node.get_text(" ", strip=True))
            if value and value not in departments:
                departments.append(value)

        title_node = soup.select_one(".title_div .title")
        return {
            "title": clean_text(title_node.get_text(" ", strip=True)) if title_node else "",
            "description": sections.get("岗位描述", ""),
            "requirements": sections.get("岗位要求", ""),
            "location": sections.get("工作地点", ""),
            "department": "，".join(departments),
        }

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        warnings: list[str] = []
        jobs: list[Job] = []
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": url,
            "X-Requested-With": "XMLHttpRequest",
        }

        with PublicClient(options.timeout) as client:
            landing = client.get(url)
            activity_id, activity_name = self._activity_id(url, landing.text)
            if not activity_id:
                return CrawlResult(self.name, url, [], ["Haier campus page exposed no active activity id"])

            requested_page_size = min(max(options.page_size, 5), 50)
            total = 0
            seen: set[str] = set()
            response_activity_name = activity_name

            for page in range(1, options.max_pages + 1):
                form = {
                    "from": "jituan",
                    "page": str(page),
                    "pagesize": str(requested_page_size),
                    "place": "",
                    "keyword": options.keyword or "",
                    "aid": activity_id,
                }
                payload = client.post(self.list_endpoint, data=form, headers=headers).json()
                if int(payload.get("status") or 0) != 1:
                    warnings.append(
                        f"Haier list API returned status={payload.get('status')!r}: {clean_text(payload.get('msg'))}"
                    )
                    break

                data = payload.get("data") or {}
                if not isinstance(data, dict):
                    warnings.append("Haier list API returned a non-object data payload")
                    break
                rows = data.get("list") or []
                if not isinstance(rows, list):
                    warnings.append("Haier list API returned a non-list job payload")
                    break

                total = int(data.get("count") or total or 0)
                activity = data.get("activity") or {}
                if isinstance(activity, dict):
                    response_activity_name = clean_text(activity.get("name")) or response_activity_name

                before = len(seen)
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    job = self._job_from_item(item, activity_id, response_activity_name)
                    if job is None or job.id in seen:
                        continue
                    seen.add(job.id)
                    jobs.append(job)
                    if len(jobs) >= options.max_jobs:
                        break

                if len(jobs) >= options.max_jobs:
                    break
                if total and len(seen) >= total:
                    break
                if not rows or len(seen) == before:
                    warnings.append(
                        f"Haier pagination stalled at page={page}: fetched={len(seen)}, api_total={total or '?'}"
                    )
                    break

            if total and len(seen) < min(total, options.max_jobs):
                warnings.append(
                    f"Haier pagination incomplete: fetched={len(seen)}, api_total={total}, "
                    f"max_pages={options.max_pages}, max_jobs={options.max_jobs}"
                )

            if response_activity_name:
                warnings.append(f"selected activity: {response_activity_name} ({activity_id})")

            if options.include_details and jobs:
                failed: list[str] = []
                for job in jobs:
                    try:
                        detail = self._parse_detail(client.get(job.url, headers={"Referer": url}).text)
                        job.description = detail.get("description") or job.description
                        job.requirements = detail.get("requirements") or job.requirements
                        job.location = detail.get("location") or job.location
                        job.department = detail.get("department") or job.department
                        job.title = detail.get("title") or job.title
                    except Exception as exc:  # noqa: BLE001
                        failed.append(f"{job.id}:{type(exc).__name__}")
                if failed:
                    warnings.append(
                        f"Haier detail hydration incomplete: failed={len(failed)}/{len(jobs)} "
                        f"sample={failed[:8]}"
                    )

        return CrawlResult(self.name, url, jobs, warnings)
