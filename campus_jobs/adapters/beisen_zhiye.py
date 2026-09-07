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
    "Org",
    "HeadCount",
    "PostDate",
    "Salary",
    "DetailAddress",
    "Duty",
    "Require",
    "ClassificationOne",
    "WorkWeChatQrCode",
]


class BeisenZhiyeAdapter(BaseAdapter):
    """Public Beisen/iTalent careers portals hosted on ``*.zhiye.com``.

    Beisen exposes an anonymous JSON listing endpoint, so zhiye portals should
    use the API instead of the generic Playwright crawler. Category ids are
    resolved dynamically because tenants can customize their recruitment
    funnels. Full JD fields are requested explicitly and missing details are
    backfilled with a one-job API query.
    """

    name = "beisen-zhiye"
    priority = 90

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "zhiye.com" or host.endswith(".zhiye.com")

    @staticmethod
    def _default_scope(scope: str) -> tuple[list[str], str, str]:
        scope = (scope or "campus").strip().lower()
        if scope == "social":
            return ["1"], "social", "社招"
        if scope == "intern":
            return ["3"], "intern", "实习"
        return ["2"], "campus", "校招"

    @staticmethod
    def _portal_id(html: str) -> str:
        if not html:
            return ""
        for pattern in (
            r'["\']PortalId["\']\s*:\s*["\']([^"\']+)["\']',
            r'["\']portalId["\']\s*:\s*["\']([^"\']+)["\']',
            r'\bPortalId\s*[:=]\s*["\']([^"\']+)["\']',
            r'portalId=([0-9a-fA-F-]{16,})',
        ):
            match = re.search(pattern, html, re.I)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _condition_entries(payload: object):
        """Yield likely {id, name} option objects from a Beisen condition payload."""
        if isinstance(payload, dict):
            yield payload
            for value in payload.values():
                yield from BeisenZhiyeAdapter._condition_entries(value)
        elif isinstance(payload, list):
            for value in payload:
                yield from BeisenZhiyeAdapter._condition_entries(value)

    @classmethod
    def _category_ids_from_conditions(cls, payload: object, scope: str) -> list[str]:
        scope = (scope or "campus").strip().lower()
        if scope == "social":
            words = ("社招", "社会招聘", "experienced", "social")
        elif scope == "intern":
            words = ("实习", "intern")
        else:
            words = ("校招", "校园", "应届", "campus", "graduate")

        found: list[str] = []
        for item in cls._condition_entries(payload):
            name = clean_text(
                item.get("Name")
                or item.get("name")
                or item.get("Text")
                or item.get("text")
                or item.get("Label")
                or item.get("label")
                or ""
            ).lower()
            if not name or not any(word in name for word in words):
                continue
            raw_id = item.get("Id") or item.get("id") or item.get("Value") or item.get("value")
            if raw_id in (None, "", []):
                continue
            value = clean_text(raw_id)
            if value and value not in found:
                found.append(value)
        return found

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

    @staticmethod
    def _row_id(item: dict) -> str:
        # Beisen deep links normally use the GUID Id; JobAdId is retained in extra
        # and is useful for the detail API on tenants that expect the numeric id.
        return clean_text(item.get("Id") or item.get("JobAdId") or "")

    @staticmethod
    def _detail_query_id(item: dict, fallback: str) -> object:
        value = item.get("JobAdId") or item.get("Id") or fallback
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    def _resolve_portal_id(self, client: PublicClient, root: str, referer: str, warnings: list[str]) -> str:
        # Newer Beisen portals expose BSGlobal config here. Some tenants do not
        # require PortalId at all, so an empty fallback remains valid.
        for config_url in (f"{root}/portal/registerSystemInfo", referer):
            try:
                portal_id = self._portal_id(client.get(config_url, headers={"Referer": referer}).text)
                if portal_id:
                    return portal_id
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"portal config {config_url}: {type(exc).__name__}: {exc}")
        return ""

    def _resolve_categories(
        self,
        client: PublicClient,
        root: str,
        headers: dict[str, str],
        portal_id: str,
        scope: str,
        fallback: list[str],
        warnings: list[str],
    ) -> list[str]:
        endpoint = f"{root}/api/Jobad/GetJobAdSearchConditions"
        try:
            payload = client.post(endpoint, json={"PortalId": portal_id}, headers=headers).json()
            ids = self._category_ids_from_conditions(payload, scope)
            if ids:
                return ids
            warnings.append(f"no dynamic category found for scope={scope}; fallback={fallback}")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"category discovery failed: {type(exc).__name__}: {exc}; fallback={fallback}")
        return fallback

    def _fetch_detail(
        self,
        client: PublicClient,
        list_url: str,
        headers: dict[str, str],
        portal_id: str,
        category_ids: list[str],
        item: dict,
        fallback_id: str,
    ) -> dict:
        body = {
            "PageIndex": 0,
            "PageSize": 1,
            "Category": category_ids,
            "KeyWords": "",
            "SpecialType": 0,
            "PortalId": portal_id,
            "JobAdIds": [self._detail_query_id(item, fallback_id)],
            "DisplayFields": list(_DISPLAY_FIELDS),
        }
        payload = client.post(list_url, json=body, headers=headers).json()
        rows = payload.get("Data") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            return {}
        return rows[0] if isinstance(rows[0], dict) else {}

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        p = urlparse(url)
        root = f"{p.scheme or 'https'}://{p.netloc}"
        fallback_categories, path_scope, recruit_type = self._default_scope(options.scope)
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
            "X-Requested-With": "XMLHttpRequest",
            "langtype": "zh_CN",
        }

        with PublicClient(options.timeout) as client:
            portal_id = self._resolve_portal_id(client, root, referer, warnings)
            category_ids = self._resolve_categories(
                client,
                root,
                headers,
                portal_id,
                options.scope,
                fallback_categories,
                warnings,
            )

            page_size = min(max(options.page_size, 1), 100)
            for page in range(options.max_pages):
                body = {
                    "PageIndex": page,
                    "PageSize": page_size,
                    "Category": category_ids,
                    "KeyWords": options.keyword or "",
                    "SpecialType": 0,
                    "PortalId": portal_id,
                    "DisplayFields": list(_DISPLAY_FIELDS),
                }

                payload = client.post(list_url, json=body, headers=headers).json()
                if isinstance(payload, dict) and payload.get("Code") not in (None, 0, 200, "200"):
                    warnings.append(f"page {page}: upstream Code={payload.get('Code')} Message={payload.get('Message')}")
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
                for raw_item in rows:
                    if not isinstance(raw_item, dict):
                        continue
                    jid = self._row_id(raw_item)
                    title = clean_text(raw_item.get("JobAdName") or raw_item.get("Name") or "")
                    if not jid or not title or jid in seen:
                        continue

                    item = dict(raw_item)
                    description = clean_text(item.get("Duty") or item.get("Description") or "")
                    requirements = clean_text(item.get("Require") or item.get("Requirement") or "")

                    if options.include_details and (not description or not requirements):
                        try:
                            detail = self._fetch_detail(
                                client, list_url, headers, portal_id, category_ids, item, jid
                            )
                            if detail:
                                item.update(detail)
                                description = clean_text(item.get("Duty") or item.get("Description") or "")
                                requirements = clean_text(item.get("Require") or item.get("Requirement") or "")
                        except Exception as exc:  # noqa: BLE001
                            warnings.append(f"detail {jid}: {type(exc).__name__}: {exc}")

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
                                item.get("Org")
                                or item.get("DepartmentName")
                                or item.get("OrgName")
                                or item.get("RecruitingOrgName")
                                or ""
                            ),
                            function=clean_text(
                                item.get("ClassificationOne")
                                or item.get("KindName")
                                or item.get("Kind")
                                or ""
                            ),
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
