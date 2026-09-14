from __future__ import annotations

import os
import re
import shutil
from urllib.parse import quote, urlparse

from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import assert_public_url, canonical_url, clean_text

from .base import BaseAdapter
from .browser_utils import dismiss_safe_popups

_BAD_TITLES = {
    "查看详情",
    "职位详情",
    "立即申请",
    "申请职位",
    "更多职位",
    "搜索职位",
    "校园招聘",
    "社会招聘",
    "实习招聘",
    "浪潮",
}

_TOTAL_PATTERNS = (
    re.compile(r"共\s*(\d{1,6})\s*(?:个|条|项)?\s*(?:职位|岗位|招聘职位)"),
    re.compile(r"(?:职位|岗位)\s*共\s*(\d{1,6})\s*(?:个|条|项)?"),
    re.compile(r"新的机会\s*[（(]\s*(\d{1,6})\s*[)）]"),
    re.compile(r"共\s*(\d{1,6})\s*(?:个|条|项)"),
)


class HCMCloudAdapter(BaseAdapter):
    """HCMCloud public recruiting portals rendered by the official frontend.

    HCMCloud can wrap recruiting APIs in its browser-side ``ha5`` envelope. This
    adapter deliberately avoids depending on that private wire format: it lets the
    official SPA decrypt/render the public list, then reads stable ``hcm-key`` row
    IDs and semantic ``col-key`` cells from the rendered table.
    """

    name = "hcmcloud"
    priority = 96

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host == "hcmcloud.cn" or host.endswith(".hcmcloud.cn")

    @staticmethod
    def _total_hint(text: str) -> int | None:
        for pattern in _TOTAL_PATTERNS:
            match = pattern.search(text)
            if match:
                value = int(match.group(1))
                if 0 <= value <= 100000:
                    return value
        return None

    @staticmethod
    def _title_from_text(text: str) -> str:
        for raw in clean_text(text).splitlines():
            line = raw.strip(" -|·•\t")
            if not line or line in _BAD_TITLES or len(line) > 140:
                continue
            if re.fullmatch(r"[\d\s/.-]+", line):
                continue
            if re.match(r"^(工作地点|地点|部门|职位类别|招聘类别|发布时间|截止时间)[:：]", line):
                continue
            return line
        return ""

    @staticmethod
    def _location_from_text(text: str) -> str:
        for raw in clean_text(text).splitlines():
            match = re.match(r"^(?:工作地点|地点|工作城市)\s*[:：]\s*(.+)$", raw.strip())
            if match:
                return clean_text(match.group(1))
        return ""

    @staticmethod
    def _detail_url(base_url: str, job_id: str) -> str:
        parsed = urlparse(base_url)
        root = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return f"{root}#/portal_job_detail?id={quote(job_id)}"

    @staticmethod
    def _candidate_to_job(candidate: dict, base_url: str, host: str) -> Job | None:
        jid = clean_text(candidate.get("id"))
        raw_href = clean_text(candidate.get("href"))
        href = canonical_url(raw_href, base_url) if raw_href else ""
        if not jid and href:
            match = re.search(r"[?&](?:id|job_id|position_id)=([^&#]+)", href, re.I)
            jid = match.group(1) if match else ""
        if jid and not href:
            href = HCMCloudAdapter._detail_url(base_url, jid)
        if not href:
            return None
        if not jid:
            jid = href

        card_text = clean_text(candidate.get("card_text"))
        title = HCMCloudAdapter._title_from_text(candidate.get("title"))
        if not title:
            title = HCMCloudAdapter._title_from_text(card_text)
        if not title or title in _BAD_TITLES:
            return None

        location = clean_text(candidate.get("location")) or HCMCloudAdapter._location_from_text(card_text)
        education = clean_text(candidate.get("education"))
        return Job(
            id=jid,
            title=title,
            url=href,
            company=clean_text(candidate.get("company")),
            location=location,
            function=clean_text(candidate.get("function")),
            source=host,
            published_at=clean_text(candidate.get("published_at")),
            extra={
                "education": education,
                "list_text": card_text[:1500],
            },
        )

    @staticmethod
    def _collect_candidates(page) -> list[dict]:
        return page.evaluate(
            r"""
            () => {
              const visible = (el) => {
                const style = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && r.width > 0 && r.height > 0;
              };
              const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
              const nodes = [];
              const seen = new Set();

              // HCMCloud's desktop list is a virtual table. Stable row IDs are
              // exposed as `hcm-key`; semantic values are exposed as `col-key`.
              for (const row of document.querySelectorAll('.table-row[hcm-key],[hcm-key].table-row')) {
                if (!visible(row)) continue;
                const id = norm(row.getAttribute('hcm-key'));
                if (!id || seen.has(`id:${id}`)) continue;
                const fields = {};
                for (const cell of row.querySelectorAll('[col-key]')) {
                  const key = norm(cell.getAttribute('col-key'));
                  if (!key) continue;
                  const content = cell.querySelector('.cell-content') || cell;
                  fields[key] = norm(content.innerText || content.textContent);
                }
                const title = fields.name || fields.job_name || fields.position_name || '';
                if (!title) continue;
                seen.add(`id:${id}`);
                nodes.push({
                  id,
                  title,
                  company: fields.u_company_name || fields.company_name || fields.company || '',
                  location: fields.work_city || fields.work_place || fields.location || '',
                  education: fields.background || fields.education || '',
                  published_at: fields.release_date || fields.publish_date || '',
                  function: fields.job_category || fields.position_category || '',
                  card_text: norm(row.innerText || row.textContent),
                });
              }

              // Other HCMCloud themes may expose normal detail anchors instead.
              const selectors = [
                'a[href*="portal_job_detail"]',
                'a[href*="job_detail"]',
                'a[href*="jobDetail"]',
                'a[href*="position_detail"]',
                '[class*="job"] a[href*="detail"]',
                '[class*="position"] a[href*="detail"]',
              ];
              for (const selector of selectors) {
                for (const a of document.querySelectorAll(selector)) {
                  if (!visible(a)) continue;
                  const href = a.getAttribute('href') || a.href || '';
                  if (!href || seen.has(`href:${href}`)) continue;
                  seen.add(`href:${href}`);
                  const card = a.closest(
                    'li,[class*="job-item"],[class*="job_item"],[class*="position-item"],'
                    + '[class*="position_item"],[class*="job-card"],[class*="position-card"],'
                    + '[class*="list-item"],[class*="list_item"]'
                  ) || a.parentElement || a;
                  nodes.push({
                    href,
                    title: (a.getAttribute('title') || a.innerText || a.textContent || '').trim(),
                    card_text: (card.innerText || card.textContent || '').trim(),
                  });
                  if (nodes.length >= 500) return nodes;
                }
              }
              return nodes;
            }
            """
        )

    @staticmethod
    def _click_next(page) -> str:
        return str(
            page.evaluate(
                r"""
                () => {
                  const visible = (el) => {
                    const style = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                  };
                  const disabled = (el) =>
                    el.disabled || el.getAttribute('aria-disabled') === 'true'
                    || /(^|\s)(disabled|is-disabled|ivu-page-disabled|ant-pagination-disabled)(\s|$)/.test(el.className || '');
                  const selectors = [
                    '.el-pagination .btn-next',
                    'button.btn-next',
                    '.ant-pagination-next button',
                    '.ant-pagination-next',
                    '.ivu-page-next',
                    '.pagination-next',
                    '.pager-next',
                    '.page-next',
                    '[class*="pagination"] [class*="next"]',
                    '[class*="page"] [class*="next"]',
                    '[aria-label*="next" i]',
                    '[title*="下一页"]',
                  ];
                  for (const selector of selectors) {
                    for (const el of document.querySelectorAll(selector)) {
                      if (!visible(el) || disabled(el)) continue;
                      el.click();
                      return selector;
                    }
                  }
                  const words = new Set(['下一页', '下页', 'Next', 'next', '›', '»', '>']);
                  for (const el of document.querySelectorAll('button,a,[role="button"],li,div,span')) {
                    if (!visible(el) || disabled(el)) continue;
                    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
                    if (words.has(text)) {
                      el.click();
                      return text;
                    }
                  }
                  return '';
                }
                """
            )
            or ""
        )

    @staticmethod
    def _body_sample(page, limit: int = 1600) -> str:
        try:
            text = clean_text(page.locator("body").inner_text())
            return text[:limit] + ("..." if len(text) > limit else "")
        except Exception:
            return ""

    @staticmethod
    def _href_sample(page, limit: int = 30) -> list[str]:
        try:
            return page.evaluate(
                r"""(limit) => [...document.querySelectorAll('a[href]')]
                  .map(a => `${(a.innerText || '').replace(/\s+/g, ' ').trim().slice(0,80)} => ${a.getAttribute('href')}`)
                  .filter(Boolean).slice(0, limit)""",
                limit,
            )
        except Exception:
            return []

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        assert_public_url(url)
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for HCMCloud: pip install '.[browser]'") from exc

        host = urlparse(url).hostname or ""
        jobs: dict[str, Job] = {}
        warnings: list[str] = []
        page_signatures: set[tuple[str, ...]] = set()
        total_hint: int | None = None
        pagination_used = False
        exhausted = False

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
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(options.timeout * 1000))
            except PlaywrightTimeoutError as exc:
                warnings.append(f"navigation timed out after {options.timeout}s: {exc}")
            page.wait_for_timeout(min(options.browser_wait_ms, 4000))
            dismiss_safe_popups(page)
            try:
                page.locator(".table-row[hcm-key]").first.wait_for(state="visible", timeout=5000)
            except Exception:
                page.wait_for_timeout(900)

            for page_no in range(1, options.max_pages + 1):
                dismiss_safe_popups(page)
                try:
                    body_text = clean_text(page.locator("body").inner_text())
                except Exception:
                    body_text = ""
                if total_hint is None:
                    total_hint = self._total_hint(body_text)

                candidates = self._collect_candidates(page)
                signature = tuple(
                    sorted(
                        clean_text(item.get("id")) or clean_text(item.get("href"))
                        for item in candidates
                        if item.get("id") or item.get("href")
                    )
                )
                if signature and signature in page_signatures:
                    warnings.append(f"pagination stopped on repeated page signature at page {page_no}")
                    exhausted = True
                    break
                if signature:
                    page_signatures.add(signature)

                before = len(jobs)
                for candidate in candidates:
                    job = self._candidate_to_job(candidate, page.url, host)
                    if job is None:
                        continue
                    if options.keyword and options.keyword.lower() not in f"{job.title} {job.company} {job.location} {job.function}".lower():
                        continue
                    jobs.setdefault(job.id, job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(400)
                for candidate in self._collect_candidates(page):
                    job = self._candidate_to_job(candidate, page.url, host)
                    if job is None:
                        continue
                    if options.keyword and options.keyword.lower() not in f"{job.title} {job.company} {job.location} {job.function}".lower():
                        continue
                    jobs.setdefault(job.id, job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs:
                    break

                if total_hint is not None and len(jobs) >= min(total_hint, options.max_jobs):
                    exhausted = True
                    break

                next_action = self._click_next(page)
                if not next_action:
                    exhausted = True
                    break
                pagination_used = True
                page.wait_for_timeout(700)
                try:
                    page.wait_for_function(
                        """(previous) => {
                          const row = document.querySelector('.table-row[hcm-key]');
                          return row && row.getAttribute('hcm-key') !== previous;
                        }""",
                        signature[0] if signature else "",
                        timeout=3000,
                    )
                except Exception:
                    pass

            if not jobs:
                sample = self._body_sample(page)
                hrefs = self._href_sample(page)
                warnings.append(f"QUALITY_FAIL no HCMCloud jobs found; body_sample={sample}")
                if hrefs:
                    warnings.append("HCMCloud href sample:\n" + "\n".join(hrefs))
            browser.close()

        values = list(jobs.values())[: options.max_jobs]
        if total_hint is not None and not options.keyword and len(values) < min(total_hint, options.max_jobs):
            warnings.append(
                f"QUALITY_FAIL completeness mismatch: rendered total={total_hint}, collected={len(values)}, "
                f"max_jobs={options.max_jobs}, max_pages={options.max_pages}"
            )
        if len(page_signatures) >= options.max_pages and not exhausted and len(values) < options.max_jobs:
            warnings.append(
                f"QUALITY_FAIL pagination cap reached after {options.max_pages} pages with {len(values)} jobs"
            )
        if len(values) <= 1 and total_hint not in (0, 1):
            warnings.append(f"QUALITY_FAIL implausibly small HCMCloud result: {len(values)} job(s)")

        adapter_name = self.name
        if not values:
            adapter_name = f"{self.name}-error"
        elif any(w.startswith("QUALITY_FAIL") for w in warnings):
            adapter_name = f"{self.name}-quality-fail"
        elif pagination_used:
            adapter_name = f"{self.name}-browser"
        return CrawlResult(adapter_name, url, values, warnings)
