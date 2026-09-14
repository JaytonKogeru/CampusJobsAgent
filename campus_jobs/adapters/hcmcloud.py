from __future__ import annotations

import hashlib
import re
from urllib.parse import quote, urlparse

from campus_jobs.browser_support import chromium_launch_kwargs, dismiss_dynamic_overlays
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import assert_public_url, canonical_url, clean_text

from .base import BaseAdapter


_DOM_EXTRACT_JS = r"""
() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
  };
  const selectors = [
    'a[href*="portal_job"]',
    'a[href*="job_id"]',
    'a[href*="jobId"]',
    'a[href*="position"]',
    '[class*="job-list"] [class*="item"]',
    '[class*="job_list"] [class*="item"]',
    '[class*="jobList"] [class*="item"]',
    '[class*="position-list"] [class*="item"]',
    '[class*="position_list"] [class*="item"]',
    '[class*="job-card"]',
    '[class*="job_card"]',
    '[class*="position-card"]',
    '[class*="position_card"]',
    '[class*="portal_job"] [class*="item"]'
  ];
  const nodes = [...new Set(selectors.flatMap((s) => [...document.querySelectorAll(s)]))];
  const badTitle = /^(首页|职位|职位列表|岗位|岗位列表|招聘职位|校园招聘|社会招聘|实习招聘|搜索|筛选|下一页|上一页)$/;
  const out = [];
  for (const node of nodes) {
    if (!visible(node)) continue;
    const raw = (node.innerText || '').replace(/\u00a0/g, ' ').trim();
    if (!raw || raw.length > 2000) continue;
    const lines = raw.split(/\n+/).map((x) => x.trim()).filter(Boolean);
    if (!lines.length || lines.length > 30) continue;
    const titleEl = node.querySelector(
      '[class*="title"],[class*="name"],h1,h2,h3,h4,[data-title],[title]'
    );
    let title = ((titleEl && (titleEl.innerText || titleEl.getAttribute('title'))) || lines[0] || '').trim();
    title = title.split(/\n+/)[0].trim();
    if (title.length < 2 || title.length > 120 || badTitle.test(title)) continue;

    const anchor = node.matches('a[href]') ? node : node.querySelector('a[href]');
    const href = anchor ? (anchor.getAttribute('href') || '') : '';
    const className = String(node.className || '');
    const signal = `${className} ${href}`.toLowerCase();
    if (!/(job|position|portal_job|recruit)/.test(signal)) continue;

    const attrs = {};
    for (const attr of node.attributes || []) {
      if (attr.name === 'id' || attr.name.startsWith('data-')) attrs[attr.name] = attr.value;
    }
    if (anchor && anchor !== node) {
      for (const attr of anchor.attributes || []) {
        if (attr.name === 'id' || attr.name.startsWith('data-')) attrs[`a:${attr.name}`] = attr.value;
      }
    }
    out.push({title, href, text: raw, lines, className, attrs});
  }
  return out.slice(0, 1000);
}
"""


_TOTAL_PATTERNS = (
    re.compile(r"共\s*(\d+)\s*(?:个|条|项)\s*(?:职位|岗位)?"),
    re.compile(r"(?:职位|岗位)\s*(?:共|总计|合计)?\s*(\d+)\s*(?:个|条|项)?"),
    re.compile(r"(\d+)\s*(?:个|条)\s*(?:职位|岗位)"),
)

_ID_PATTERNS = (
    re.compile(r"(?:job_id|jobId|position_id|positionId|post_id|postId)=([^&#]+)", re.I),
    re.compile(r"/(?:job|position|post)/([^/?#&]+)", re.I),
)


class HCMCloudAdapter(BaseAdapter):
    """Public HCMCloud recruiting portals such as Inspur's campus site.

    HCMCloud wraps recruiting API payloads in its transfer layer, so this adapter
    deliberately lets the official frontend perform decoding and then extracts the
    rendered job list. Pagination is guarded by page signatures and terminal-state
    checks so a silent first-page-only crawl is surfaced as an integrity warning.
    """

    name = "hcmcloud"
    priority = 96

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "hcmcloud.cn" or host.endswith(".hcmcloud.cn")

    @staticmethod
    def _expected_total(text: str) -> int | None:
        for pattern in _TOTAL_PATTERNS:
            match = pattern.search(text or "")
            if match:
                try:
                    value = int(match.group(1))
                except (TypeError, ValueError):
                    continue
                if 0 <= value <= 100000:
                    return value
        return None

    @staticmethod
    def _extract_id(row: dict[str, object]) -> str:
        href = clean_text(row.get("href"))
        for pattern in _ID_PATTERNS:
            match = pattern.search(href)
            if match:
                return clean_text(match.group(1))

        attrs = row.get("attrs")
        if isinstance(attrs, dict):
            for key, value in attrs.items():
                low = str(key).lower()
                if "job" not in low and "position" not in low and low not in {"data-id", "id", "a:data-id"}:
                    continue
                candidate = clean_text(value)
                if candidate and len(candidate) <= 160:
                    return candidate
        return ""

    @staticmethod
    def _row_signature(rows: list[dict[str, object]]) -> str:
        payload = "\n".join(
            f"{clean_text(row.get('title'))}\t{clean_text(row.get('href'))}\t{clean_text(row.get('text'))[:200]}"
            for row in rows[:100]
        )
        return hashlib.sha1(payload.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def _body_sample(page, limit: int = 1800) -> str:
        try:
            text = clean_text(page.locator("body").inner_text())
        except Exception:
            return ""
        return text if len(text) <= limit else text[:limit] + "..."

    @staticmethod
    def _extract_rows(page) -> list[dict[str, object]]:
        try:
            rows = page.evaluate(_DOM_EXTRACT_JS)
        except Exception:
            return []
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    @staticmethod
    def _next_control(page):
        selectors = (
            ".el-pagination .btn-next",
            ".el-pager + .btn-next",
            "button[aria-label='下一页']",
            "button[aria-label='Next']",
            "a[aria-label='下一页']",
            "a[aria-label='Next']",
        )
        saw_disabled = False
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = min(locator.count(), 10)
            except Exception:
                continue
            for index in range(count):
                item = locator.nth(index)
                try:
                    if not item.is_visible():
                        continue
                    disabled = item.is_disabled()
                    aria_disabled = (item.get_attribute("aria-disabled") or "").lower() == "true"
                    classes = (item.get_attribute("class") or "").lower()
                    disabled = disabled or aria_disabled or "disabled" in classes
                    if disabled:
                        saw_disabled = True
                        continue
                    return item, False
                except Exception:
                    continue

        for text in ("下一页", "下页", "Next"):
            try:
                locator = page.get_by_text(text, exact=True)
                count = min(locator.count(), 10)
            except Exception:
                continue
            for index in range(count):
                item = locator.nth(index)
                try:
                    if not item.is_visible():
                        continue
                    classes = (item.get_attribute("class") or "").lower()
                    aria_disabled = (item.get_attribute("aria-disabled") or "").lower() == "true"
                    if aria_disabled or "disabled" in classes:
                        saw_disabled = True
                        continue
                    return item, False
                except Exception:
                    continue
        return None, saw_disabled

    @staticmethod
    def _job_url(source_url: str, row: dict[str, object], job_id: str) -> str:
        href = clean_text(row.get("href"))
        if href and not href.lower().startswith("javascript:"):
            return canonical_url(href, source_url)
        parsed = urlparse(source_url)
        root = f"{parsed.scheme or 'https'}://{parsed.netloc}"
        if job_id and not job_id.startswith("dom-"):
            return f"{root}/recruit#/portal_job_detail?job_id={quote(job_id, safe='')}"
        return source_url

    def _normalize_row(
        self,
        source_url: str,
        row: dict[str, object],
        company: str,
        options: CrawlOptions,
    ) -> Job | None:
        title = clean_text(row.get("title"))
        text = clean_text(row.get("text"))
        if not title or len(title) > 120:
            return None
        searchable = f"{title}\n{text}".lower()
        if options.keyword and options.keyword.lower() not in searchable:
            return None

        job_id = self._extract_id(row)
        if not job_id:
            digest = hashlib.sha1(f"{title}\n{text}".encode("utf-8", errors="ignore")).hexdigest()[:16]
            job_id = f"dom-{digest}"

        recruit_type = {
            "campus": "校招",
            "intern": "实习",
            "social": "社招",
        }.get((options.scope or "campus").lower(), options.scope)

        return Job(
            id=job_id,
            title=title,
            url=self._job_url(source_url, row, job_id),
            company=company,
            recruit_type=recruit_type,
            source=urlparse(source_url).netloc,
            extra={
                "list_text": text,
                "dom_class": clean_text(row.get("className")),
                "dom_attrs": row.get("attrs") if isinstance(row.get("attrs"), dict) else {},
            },
        )

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        assert_public_url(url)
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for HCMCloud: pip install '.[browser]'") from exc

        warnings: list[str] = []
        jobs: dict[str, Job] = {}
        endpoint_trace: list[str] = []
        company_state = {"name": ""}
        expected_total: int | None = None
        pagination_reason = "unknown"
        pages_seen = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(**chromium_launch_kwargs())
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            def on_response(response):
                try:
                    low = response.url.lower()
                    if "hcmcloud" not in low or "/api/" not in low:
                        return
                    if len(endpoint_trace) < 40:
                        endpoint_trace.append(f"{response.status} {response.request.method} {response.url}")
                    if "/api/auth/get_auth" not in low:
                        return
                    payload = response.json()
                    company = payload.get("company") if isinstance(payload, dict) else None
                    if isinstance(company, dict):
                        company_state["name"] = clean_text(company.get("name"))
                except Exception:
                    return

            page.on("response", on_response)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(options.timeout * 1000))
            except PlaywrightTimeoutError as exc:
                warnings.append(f"navigation timed out after {options.timeout}s: {exc}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"navigation error: {type(exc).__name__}: {exc}")

            page.wait_for_timeout(min(max(options.browser_wait_ms, 500), 5000))
            dismissed = dismiss_dynamic_overlays(page, max_rounds=6)
            if dismissed:
                page.wait_for_timeout(900)

            rows: list[dict[str, object]] = []
            for _ in range(20):
                rows = self._extract_rows(page)
                if rows:
                    break
                dismiss_dynamic_overlays(page, max_rounds=2)
                page.wait_for_timeout(400)

            signatures: set[str] = set()
            for page_index in range(options.max_pages):
                pages_seen = page_index + 1
                dismiss_dynamic_overlays(page, max_rounds=2)
                rows = self._extract_rows(page)
                signature = self._row_signature(rows)
                if rows and signature in signatures:
                    warnings.append(f"pagination repeated page content at page {page_index + 1}; stopped")
                    pagination_reason = "repeated-page"
                    break
                if rows:
                    signatures.add(signature)

                try:
                    body_text = clean_text(page.locator("body").inner_text())
                except Exception:
                    body_text = ""
                total = self._expected_total(body_text)
                if total is not None:
                    expected_total = max(expected_total or 0, total)

                new_jobs = 0
                for row in rows:
                    job = self._normalize_row(url, row, company_state["name"], options)
                    if job is None:
                        continue
                    key = job.id if not job.id.startswith("dom-") else f"{job.title}\n{job.extra.get('list_text', '')}"
                    if key in jobs:
                        continue
                    jobs[key] = job
                    new_jobs += 1
                    if len(jobs) >= options.max_jobs:
                        pagination_reason = "max-jobs"
                        break
                if len(jobs) >= options.max_jobs:
                    break

                next_control, terminal = self._next_control(page)
                if next_control is None:
                    pagination_reason = "terminal" if terminal else "no-next-control"
                    break

                before_signature = signature
                try:
                    next_control.click(timeout=2500, force=True)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"pagination click failed on page {page_index + 1}: {type(exc).__name__}: {exc}")
                    pagination_reason = "click-failed"
                    break

                changed = False
                for _ in range(18):
                    page.wait_for_timeout(300)
                    dismiss_dynamic_overlays(page, max_rounds=1)
                    next_rows = self._extract_rows(page)
                    if next_rows and self._row_signature(next_rows) != before_signature:
                        rows = next_rows
                        changed = True
                        break
                if not changed:
                    warnings.append(f"pagination stalled after page {page_index + 1}; content did not change")
                    pagination_reason = "stalled"
                    break
                if new_jobs == 0 and page_index > 0:
                    warnings.append(f"page {page_index + 1} added no unique jobs")
            else:
                pagination_reason = "max-pages"

            body_sample = self._body_sample(page)
            try:
                popup_visible = any(
                    page.get_by_text(text, exact=True).is_visible()
                    for text in ("我已阅读并同意", "同意并继续", "接受并继续")
                    if page.get_by_text(text, exact=True).count()
                )
            except Exception:
                popup_visible = False

            browser.close()

        values = list(jobs.values())[: options.max_jobs]
        if popup_visible:
            warnings.append("dynamic consent popup remained visible after dismissal attempts")

        if expected_total is not None and not options.keyword:
            target = min(expected_total, options.max_jobs)
            if len(values) < target:
                warnings.append(
                    f"integrity incomplete: collected {len(values)}/{target} jobs "
                    f"(upstream total={expected_total}, reason={pagination_reason}, pages={pages_seen})"
                )
        elif pagination_reason in {"stalled", "click-failed", "repeated-page", "max-pages"}:
            warnings.append(
                f"integrity unverified: pagination ended with reason={pagination_reason}, "
                f"jobs={len(values)}, pages={pages_seen}"
            )

        if not values:
            warnings.append(
                f"HCMCloud rendered no job rows; company={company_state['name'] or '-'}; "
                f"reason={pagination_reason}; body_sample={body_sample}"
            )
            if endpoint_trace:
                warnings.append("HCMCloud API trace:\n" + "\n".join(endpoint_trace))
        elif len(values) <= 2:
            warnings.append(
                f"HCMCloud suspiciously low job count={len(values)}; reason={pagination_reason}; "
                f"body_sample={body_sample}"
            )

        return CrawlResult(self.name, url, values, warnings)
