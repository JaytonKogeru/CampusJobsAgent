from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

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
  const attrMap = (node, prefix='') => {
    const attrs = {};
    if (!node) return attrs;
    for (const attr of node.attributes || []) {
      if (attr.name === 'id' || attr.name === 'hcm-key' || attr.name.startsWith('data-')) attrs[`${prefix}${attr.name}`] = attr.value;
    }
    return attrs;
  };
  const badTitle = /^(首页|职位|职位列表|岗位|岗位列表|招聘职位|校园招聘|社会招聘|实习招聘|搜索|筛选|下一页|上一页|职位名称)$/;
  const out = [];
  const seenNodes = new Set();

  // Current HCMCloud public portals render the job list as a div-based
  // grid. Each row exposes the underlying ReleaseJobMgr id in hcm-key.
  // Use HCMCloud's own URL encoder in-page instead of reimplementing its
  // private _HB5_ transformation.
  const gridKeys = ['name', 'u_company_name', 'work_city', 'background', 'release_date', 'job_category'];
  const gridHeaders = ['职位名称', '所属单位', '工作城市', '学历要求', '发布时间', '职位类别'];
  for (const node of document.querySelectorAll('.table-body .table-row[hcm-key]')) {
    if (!visible(node)) continue;
    const nativeId = (node.getAttribute('hcm-key') || '').trim();
    if (!nativeId) continue;

    const byKey = {};
    for (const cell of node.querySelectorAll('.table-cell[col-key]')) {
      const key = (cell.getAttribute('col-key') || '').trim();
      if (!key) continue;
      const content = cell.querySelector('.cell-content') || cell;
      byKey[key] = (content.innerText || '').replace(/\u00a0/g, ' ').trim();
    }
    const cells = gridKeys.map((key) => byKey[key] || '');
    const title = (cells[0] || '').trim();
    if (title.length < 2 || title.length > 120 || badTitle.test(title)) continue;

    let href = '';
    let encodedId = '';
    try {
      if (typeof window.hcmUrlParamEncoder === 'function') {
        encodedId = String(window.hcmUrlParamEncoder(nativeId) || '');
        if (encodedId) href = `#/portal_job_detail?id=${encodeURIComponent(encodedId)}`;
      }
    } catch (e) {
      encodedId = '';
    }

    out.push({
      title,
      href,
      text: cells.filter(Boolean).join('\n'),
      lines: cells.filter(Boolean),
      cells,
      headers: gridHeaders,
      className: String(node.className || ''),
      attrs: attrMap(node),
      nativeId,
      encodedId,
      kind: 'hcmcloud-grid'
    });
    seenNodes.add(node);
  }
  // Some HCMCloud tenants use a native table.
  for (const table of document.querySelectorAll('table')) {
    if (!visible(table)) continue;
    const headers = [...table.querySelectorAll('thead th, thead [role="columnheader"]')]
      .map((el) => (el.innerText || '').trim()).filter(Boolean);
    const headerText = headers.join('|');
    const jobTable = headerText.includes('职位名称') &&
      (headerText.includes('所属单位') || headerText.includes('工作城市') || headerText.includes('发布时间'));
    if (!jobTable) continue;

    for (const node of table.querySelectorAll('tbody tr, [role="row"]')) {
      if (!visible(node)) continue;
      const cells = [...node.querySelectorAll(':scope > td, :scope > [role="cell"]')]
        .map((el) => (el.innerText || '').replace(/\u00a0/g, ' ').trim());
      if (cells.length < 5) continue;
      const title = (cells[0] || '').trim();
      if (title.length < 2 || title.length > 120 || badTitle.test(title)) continue;
      const raw = cells.filter(Boolean).join('\n');
      const anchor = node.querySelector('a[href]');
      const href = anchor ? (anchor.getAttribute('href') || '') : '';
      out.push({
        title,
        href,
        text: raw,
        lines: cells.filter(Boolean),
        cells,
        headers,
        className: String(node.className || ''),
        attrs: {...attrMap(node), ...attrMap(anchor, 'a:')},
        kind: 'table-row'
      });
      seenNodes.add(node);
    }
  }

  // Family fallback for tenants that use cards/lists instead of tables.
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
  for (const node of nodes) {
    if (seenNodes.has(node) || !visible(node)) continue;
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
    out.push({
      title,
      href,
      text: raw,
      lines,
      className,
      attrs: {...attrMap(node), ...attrMap(anchor, 'a:')},
      kind: 'card'
    });
  }
  return out.slice(0, 1000);
}
"""


_PAGINATION_DEBUG_JS = r"""
() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
  };
  const result = [];
  for (const el of document.querySelectorAll('button,a,input,[role="button"]')) {
    if (!visible(el)) continue;
    let parent = el;
    let context = '';
    for (let i = 0; i < 5 && parent; i++, parent = parent.parentElement) {
      const text = (parent.innerText || '').replace(/\s+/g, ' ').trim();
      const cls = String(parent.className || '');
      if (/page|pager|paging|pagination/i.test(cls) || (text.includes('页') && text.includes('当前第'))) {
        context = `${cls} :: ${text}`;
        break;
      }
    }
    if (!context) continue;
    result.push({
      tag: el.tagName,
      cls: String(el.className || ''),
      text: (el.innerText || '').trim(),
      title: el.getAttribute('title') || '',
      aria: el.getAttribute('aria-label') || '',
      disabled: Boolean(el.disabled) || el.getAttribute('aria-disabled') === 'true',
      value: 'value' in el ? String(el.value || '') : '',
      context: context.slice(0, 500)
    });
  }
  return result.slice(0, 40);
}
"""


_TOTAL_PATTERNS = (
    re.compile(r"(?:新的机会|机会)\s*[\(（]\s*(\d+)\s*[\)）]"),
    re.compile(r"共\s*(\d+)\s*(?:个|条|项)\s*(?:职位|岗位)?"),
    re.compile(r"(?:职位|岗位)\s*(?:共|总计|合计)?\s*(\d+)\s*(?:个|条|项)?"),
    re.compile(r"(\d+)\s*(?:个|条)\s*(?:职位|岗位)"),
)

_PAGE_PATTERNS = (
    re.compile(r"/\s*(\d+)\s*页"),
    re.compile(r"共\s*(\d+)\s*页"),
)

_ID_PATTERNS = (
    re.compile(r"(?:job_id|jobId|position_id|positionId|post_id|postId)=([^&#]+)", re.I),
    re.compile(r"/(?:job|position|post)/([^/?#&]+)", re.I),
)

_SEMANTIC_HEADERS = ["职位名称", "所属单位", "工作城市", "学历要求", "发布时间", "职位类别"]
_DATE_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")


class HCMCloudAdapter(BaseAdapter):
    """Public HCMCloud recruiting portals such as Inspur's campus site.

    HCMCloud wraps recruiting API payloads in its transfer layer, so this adapter
    deliberately lets the official frontend perform decoding and then extracts the
    rendered job list. Pagination is guarded by upstream totals, page signatures,
    and content-change checks so a silent first-page-only crawl is never trusted.
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
    def _expected_pages(text: str) -> int | None:
        for pattern in _PAGE_PATTERNS:
            match = pattern.search(text or "")
            if match:
                try:
                    value = int(match.group(1))
                except (TypeError, ValueError):
                    continue
                if 1 <= value <= 10000:
                    return value
        return None

    @staticmethod
    def _semantic_rows_from_text(text: str) -> list[dict[str, object]]:
        """Parse div-based HCMCloud grids from their stable six-column text contract."""
        lines = [clean_text(line) for line in (text or "").splitlines() if clean_text(line)]
        start = -1
        width = len(_SEMANTIC_HEADERS)
        for index in range(0, max(0, len(lines) - width + 1)):
            if lines[index : index + width] == _SEMANTIC_HEADERS:
                start = index + width
                break
        if start < 0:
            return []

        end = len(lines)
        for index in range(start, len(lines)):
            if lines[index].startswith("当前第"):
                end = index
                break

        payload = lines[start:end]
        rows: list[dict[str, object]] = []
        index = 0
        while index + width <= len(payload):
            cells = payload[index : index + width]
            if _DATE_RE.match(cells[4]) and cells[0] not in _SEMANTIC_HEADERS:
                rows.append(
                    {
                        "title": cells[0],
                        "href": "",
                        "text": "\n".join(cells),
                        "lines": cells,
                        "cells": cells,
                        "headers": list(_SEMANTIC_HEADERS),
                        "className": "semantic-grid",
                        "attrs": {},
                        "kind": "semantic-grid",
                    }
                )
                index += width
            else:
                index += 1
        return rows

    @staticmethod
    def _extract_id(row: dict[str, object]) -> str:
        native_id = clean_text(row.get("nativeId"))
        if native_id:
            return native_id

        href = clean_text(row.get("href"))
        for pattern in _ID_PATTERNS:
            match = pattern.search(href)
            if match:
                return clean_text(match.group(1))

        attrs = row.get("attrs")
        if isinstance(attrs, dict):
            for key, value in attrs.items():
                low = str(key).lower()
                if "job" not in low and "position" not in low and low not in {
                    "data-id",
                    "id",
                    "a:data-id",
                    "hcm-key",
                }:
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

    @classmethod
    def _extract_rows(cls, page) -> list[dict[str, object]]:
        try:
            rows = page.evaluate(_DOM_EXTRACT_JS)
        except Exception:
            rows = []
        if isinstance(rows, list):
            parsed = [row for row in rows if isinstance(row, dict)]
            if parsed:
                return parsed
        try:
            body_text = page.locator("body").inner_text()
        except Exception:
            return []
        return cls._semantic_rows_from_text(body_text)

    @staticmethod
    def _pagination_debug(page) -> str:
        try:
            items = page.evaluate(_PAGINATION_DEBUG_JS)
        except Exception:
            return ""
        if not isinstance(items, list) or not items:
            return ""
        parts = []
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            parts.append(
                "tag={tag} cls={cls!r} text={text!r} title={title!r} aria={aria!r} "
                "disabled={disabled} value={value!r} context={context!r}".format(**item)
            )
        return "\n".join(parts)

    @staticmethod
    def _is_enabled(item) -> bool:
        try:
            if not item.is_visible():
                return False
            if item.is_disabled():
                return False
            if (item.get_attribute("aria-disabled") or "").lower() == "true":
                return False
            return "disabled" not in (item.get_attribute("class") or "").lower()
        except Exception:
            return False

    @classmethod
    def _advance_page(cls, page, next_page_number: int) -> tuple[bool, str]:
        selectors = (
            ".el-pagination .btn-next",
            ".el-pager + .btn-next",
            "button[aria-label='下一页']",
            "button[aria-label='Next']",
            "a[aria-label='下一页']",
            "a[aria-label='Next']",
            "button[class*='next']",
            "a[class*='next']",
            "[class*='pagination'] [class*='next']",
            "[class*='pager'] [class*='next']",
            "[class*='paging'] [class*='next']",
            "[class*='page'] [class*='next']",
        )
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = min(locator.count(), 12)
            except Exception:
                continue
            for index in range(count):
                item = locator.nth(index)
                if not cls._is_enabled(item):
                    continue
                try:
                    item.click(timeout=2500, force=True)
                    return True, f"click:{selector}"
                except Exception:
                    continue

        for text in ("下一页", "下页", "Next", ">", "›", "»"):
            try:
                locator = page.get_by_text(text, exact=True)
                count = min(locator.count(), 12)
            except Exception:
                continue
            for index in range(count):
                item = locator.nth(index)
                if not cls._is_enabled(item):
                    continue
                try:
                    item.click(timeout=2500, force=True)
                    return True, f"text:{text}"
                except Exception:
                    continue

        # Inspur's pager exposes the current page as an input inside paging-box.
        # Restrict the search to pagination-class ancestors; climbing into the
        # whole job-list would also match unrelated filter inputs.
        for selector in (
            "[class*='paging'] input",
            "[class*='pagination'] input",
            "[class*='pager'] input",
            "[class*='page-box'] input",
        ):
            try:
                inputs = page.locator(selector)
                count = min(inputs.count(), 12)
            except Exception:
                continue
            for index in range(count):
                item = inputs.nth(index)
                try:
                    if not item.is_visible() or item.is_disabled():
                        continue
                    item.fill(str(next_page_number))
                    item.press("Enter")
                    return True, f"page-input:{selector}"
                except Exception:
                    continue

        # Last-resort custom pager handling: only inspect compact containers that
        # clearly identify themselves as pagination. Never click arbitrary controls.
        for selector in ("[class*='pagination']", "[class*='pager']", "[class*='paging']", "[class*='page-box']"):
            try:
                containers = page.locator(selector)
                container_count = min(containers.count(), 30)
            except Exception:
                continue
            for container_index in range(container_count):
                container = containers.nth(container_index)
                try:
                    if not container.is_visible():
                        continue
                    context = clean_text(container.inner_text())
                    if len(context) > 250 or "页" not in context:
                        continue
                    controls = container.locator("button,a,[role='button']")
                    control_count = min(controls.count(), 20)
                except Exception:
                    continue
                enabled = [controls.nth(i) for i in range(control_count) if cls._is_enabled(controls.nth(i))]
                if not enabled:
                    continue
                signaled = []
                for item in enabled:
                    try:
                        signal = " ".join(
                            [
                                item.inner_text(),
                                item.get_attribute("class") or "",
                                item.get_attribute("title") or "",
                                item.get_attribute("aria-label") or "",
                            ]
                        ).lower()
                    except Exception:
                        continue
                    if any(token in signal for token in ("next", "right", "下一", ">", "›", "»")):
                        signaled.append(item)
                candidates = signaled or [enabled[-1]]
                for item in candidates:
                    try:
                        item.click(timeout=2500, force=True)
                        return True, f"container:{selector}"
                    except Exception:
                        continue
        return False, "not-found"

    @staticmethod
    def _job_url(source_url: str, row: dict[str, object], job_id: str) -> str:
        href = clean_text(row.get("href"))
        if href and not href.lower().startswith("javascript:"):
            return canonical_url(href, source_url)
        # HCMCloud's detail route encodes ids through its frontend
        # hcmUrlParamEncoder. The rendered-grid extractor stores that exact
        # official route in href; do not fabricate an unverified id parameter.
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
            page_number = clean_text(row.get("_page_number"))
            row_number = clean_text(row.get("_row_number"))
            digest = hashlib.sha1(
                f"{page_number}:{row_number}\n{title}\n{text}".encode("utf-8", errors="ignore")
            ).hexdigest()[:16]
            job_id = f"dom-{digest}"

        cells = row.get("cells") if isinstance(row.get("cells"), list) else []
        unit = clean_text(cells[1]) if len(cells) > 1 else ""
        location = clean_text(cells[2]) if len(cells) > 2 else ""
        education = clean_text(cells[3]) if len(cells) > 3 else ""
        published_at = clean_text(cells[4]) if len(cells) > 4 else ""
        function = clean_text(cells[5]) if len(cells) > 5 else ""

        recruit_type = {
            "campus": "校招",
            "intern": "实习",
            "social": "社招",
        }.get((options.scope or "campus").lower(), options.scope)

        return Job(
            id=job_id,
            title=title,
            url=self._job_url(source_url, row, job_id),
            company=unit or company,
            location=location,
            function=function,
            recruit_type=recruit_type,
            source=urlparse(source_url).netloc,
            published_at=published_at,
            requirements=education,
            extra={
                "list_text": text,
                "education": education,
                "dom_kind": clean_text(row.get("kind")),
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
        expected_pages: int | None = None
        pagination_reason = "unknown"
        pagination_method = ""
        pages_seen = 0
        pager_debug = ""

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
                page_total = self._expected_pages(body_text)
                if page_total is not None:
                    expected_pages = max(expected_pages or 0, page_total)

                new_jobs = 0
                for row_index, row in enumerate(rows, 1):
                    row.setdefault("_page_number", page_index + 1)
                    row.setdefault("_row_number", row_index)
                    job = self._normalize_row(url, row, company_state["name"], options)
                    if job is None:
                        continue
                    if job.id in jobs:
                        continue
                    jobs[job.id] = job
                    new_jobs += 1
                    if len(jobs) >= options.max_jobs:
                        pagination_reason = "max-jobs"
                        break
                if len(jobs) >= options.max_jobs:
                    break

                if expected_total is not None and len(jobs) >= expected_total:
                    pagination_reason = "upstream-total"
                    break
                if expected_pages is not None and page_index + 1 >= expected_pages:
                    pagination_reason = "terminal"
                    break

                before_signature = signature
                advanced, method = self._advance_page(page, page_index + 2)
                if not advanced:
                    pagination_reason = "no-next-control"
                    pager_debug = self._pagination_debug(page)
                    break
                pagination_method = method

                changed = False
                for _ in range(20):
                    page.wait_for_timeout(300)
                    dismiss_dynamic_overlays(page, max_rounds=1)
                    next_rows = self._extract_rows(page)
                    if next_rows and self._row_signature(next_rows) != before_signature:
                        rows = next_rows
                        changed = True
                        break
                if not changed:
                    warnings.append(
                        f"pagination stalled after page {page_index + 1}; content did not change; method={method}"
                    )
                    pagination_reason = "stalled"
                    pager_debug = self._pagination_debug(page)
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
                    f"(upstream total={expected_total}, expected_pages={expected_pages}, "
                    f"reason={pagination_reason}, method={pagination_method or '-'}, pages={pages_seen})"
                )
        elif pagination_reason in {"stalled", "no-next-control", "repeated-page", "max-pages"}:
            warnings.append(
                f"integrity unverified: pagination ended with reason={pagination_reason}, "
                f"jobs={len(values)}, pages={pages_seen}"
            )

        if pager_debug:
            warnings.append("HCMCloud pager controls:\n" + pager_debug)

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
