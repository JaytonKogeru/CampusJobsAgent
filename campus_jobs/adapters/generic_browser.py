from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from campus_jobs.browser_support import chromium_launch_kwargs, dismiss_dynamic_overlays
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import assert_public_url, canonical_url, clean_text, find_first, walk_dicts

from .base import BaseAdapter

TITLE_KEYS = ["title", "name", "jobName", "job_name", "positionName", "jobTitle", "postName", "RecruitPostName"]
JOB_TITLE_KEYS = ["jobName", "job_name", "positionName", "jobTitle", "postName", "RecruitPostName"]
URL_KEYS = ["url", "href", "jobUrl", "job_url", "applyUrl", "positionUrl", "PostURL"]
ID_KEYS = ["id", "jobId", "job_id", "postId", "positionId", "JobAdId"]
JOB_ID_KEYS = ["jobId", "job_id", "postId", "positionId", "JobAdId"]
LOC_KEYS = ["location", "city", "workPlace", "workLocation", "workCity", "LocationName", "workPlaceStr"]
DESC_KEYS = ["description", "jobDescription", "duty", "Duty", "workContent", "responsibility"]
REQ_KEYS = ["requirement", "requirements", "Require", "serviceCondition", "qualification"]
JOBISH_KEYS = set(JOB_TITLE_KEYS + JOB_ID_KEYS + LOC_KEYS + DESC_KEYS + REQ_KEYS)

NAVIGATION_TITLES = {
    "首页",
    "岗位投递",
    "职位投递",
    "招聘动态",
    "招聘资讯",
    "活动日历",
    "应届生招聘",
    "校园招聘",
    "实习生招聘",
    "社会招聘",
    "了解我们",
    "了解海尔",
    "关于我们",
    "联系我们",
    "全部职位",
    "热招职位",
    "登录",
    "注册",
    "home",
    "jobs",
    "careers",
    "campus recruitment",
    "internships",
    "about us",
    "contact us",
    "sign in",
    "log in",
}
JOB_DETAIL_URL_RE = re.compile(
    r"(?:job|position|post|career|recruit)[^?#/]*(?:detail|view)|"
    r"(?:detail|view)[^?#/]*(?:job|position|post)|"
    r"/(?:job|jobs|position|positions|post|posts)/[^/?#]+|"
    r"/(?:jobdetail|positiondetail|customizedjobdetail|customizedptjobdetail|deliverfirst)(?:/|\b)",
    re.I,
)
JOBISH_URL_RE = re.compile(r"job|position|career|recruit|招聘|职位|岗位", re.I)
ROLE_TITLE_RE = re.compile(
    r"工程师|开发|算法|研究员|科学家|分析师|设计师|架构师|产品|运营|销售|市场|财务|会计|"
    r"供应链|采购|质量|测试|顾问|专员|经理|管培|实习|技术|研发|制造|工艺|设备|数据|"
    r"engineer|developer|scientist|analyst|architect|designer|manager|intern|research|sales|"
    r"marketing|product|software|hardware|data|machine learning|\bai\b|qa|quality",
    re.I,
)


def _json_shape(data: object) -> str:
    """Return a compact structural summary for diagnostics without dumping payloads."""
    try:
        if isinstance(data, dict):
            keys = list(data.keys())[:20]
            parts = [f"dict keys={keys}"]
            for key in keys[:8]:
                value = data.get(key)
                if isinstance(value, dict):
                    parts.append(f"{key}:dict({list(value.keys())[:12]})")
                    for subkey in list(value.keys())[:8]:
                        subvalue = value.get(subkey)
                        if isinstance(subvalue, list):
                            sample = subvalue[0] if subvalue else None
                            if isinstance(sample, dict):
                                parts.append(f"{key}.{subkey}:list[{len(subvalue)}]({list(sample.keys())[:20]})")
                elif isinstance(value, list):
                    sample = value[0] if value else None
                    if isinstance(sample, dict):
                        parts.append(f"{key}:list[{len(value)}]({list(sample.keys())[:20]})")
                    else:
                        parts.append(f"{key}:list[{len(value)}]")
            return "; ".join(parts)
        if isinstance(data, list):
            sample = data[0] if data else None
            if isinstance(sample, dict):
                return f"list[{len(data)}] sample_keys={list(sample.keys())[:20]}"
            return f"list[{len(data)}]"
        return type(data).__name__
    except Exception:
        return type(data).__name__


def _looks_like_job_object(obj: dict, raw_url: str) -> bool:
    """Require job-specific evidence before synthesizing a job from generic JSON.

    Dynamic applications routinely return objects such as ``{id: 8, name: '浪潮'}``
    in auth/config responses. Treating every ``id + name`` pair as a job creates
    convincing false positives, so generic keys alone are deliberately insufficient.
    """
    if any(key in obj and obj.get(key) not in (None, "", [], {}) for key in JOBISH_KEYS):
        return True
    if raw_url and JOBISH_URL_RE.search(raw_url):
        return True
    return False


def _looks_like_job_anchor(title: str, href: str) -> bool:
    """Reject navigation links and keep links with concrete job evidence.

    Careers SPAs often have menu items such as ``岗位投递`` or ``招聘动态`` whose
    text contains job-related words. Those links are not jobs and should never be
    returned as normalized openings.
    """
    normalized_title = clean_text(title).strip()
    if not normalized_title or normalized_title.lower() in NAVIGATION_TITLES:
        return False
    if not href:
        return False
    if JOB_DETAIL_URL_RE.search(href):
        return True
    return bool(JOBISH_URL_RE.search(href) and ROLE_TITLE_RE.search(normalized_title))


def _quality_summary(jobs: dict[str, Job]) -> tuple[int, bool]:
    """Return informative-job count and whether the result needs diagnostics."""
    informative = sum(
        bool(job.location or job.description or job.requirements or job.department or job.function)
        for job in jobs.values()
    )
    count = len(jobs)
    low_quality = count == 0 or informative == 0 or (
        count <= 4 and informative < count
    ) or (
        count >= 5 and informative < max(3, count // 2)
    )
    return informative, low_quality


class GenericBrowserAdapter(BaseAdapter):
    name = "generic-browser"
    priority = 1

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return True

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        assert_public_url(url)
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for unknown dynamic sites: pip install '.[browser]'") from exc

        jobs: dict[str, Job] = {}
        warnings: list[str] = []
        host = urlparse(url).hostname or ""
        network_debug: list[str] = []

        def absorb_json(data: object, base_url: str) -> None:
            for obj in walk_dicts(data):
                title = clean_text(find_first(obj, TITLE_KEYS))
                if not title or len(title) > 160:
                    continue
                jid = clean_text(find_first(obj, ID_KEYS))
                raw_url = clean_text(find_first(obj, URL_KEYS))
                if not _looks_like_job_object(obj, raw_url):
                    continue
                job_url = canonical_url(raw_url, base_url) if raw_url else ""
                if not job_url and jid:
                    job_url = f"{url}#job={jid}"
                if not job_url:
                    continue
                if options.keyword and options.keyword.lower() not in f"{title} {obj}".lower():
                    continue
                key = jid or job_url
                jobs[key] = Job(
                    id=jid or key,
                    title=title,
                    url=job_url,
                    location=clean_text(find_first(obj, LOC_KEYS)),
                    description=clean_text(find_first(obj, DESC_KEYS)),
                    requirements=clean_text(find_first(obj, REQ_KEYS)),
                    source=host,
                    extra=obj,
                )

        with sync_playwright() as p:
            browser = p.chromium.launch(**chromium_launch_kwargs())
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            def on_response(response):
                try:
                    ct = (response.headers.get("content-type") or "").lower()
                    low = response.url.lower()
                    looks_relevant = "json" in ct or any(
                        x in low for x in ["job", "position", "post", "recruit", "career", "school", "campus", "zhaopin"]
                    )
                    if not looks_relevant:
                        return
                    try:
                        data = response.json()
                    except Exception:
                        return
                    absorb_json(data, response.url)
                    if len(network_debug) < 50:
                        req = response.request
                        post_data = clean_text(req.post_data or "")
                        if len(post_data) > 700:
                            post_data = post_data[:700] + "..."
                        network_debug.append(
                            f"{response.status} {req.method} {response.url} | post={post_data or '-'} | {_json_shape(data)}"
                        )
                        if "/position/common/position/list" in low and isinstance(data, dict):
                            inner = data.get("data") or {}
                            rows = inner.get("data") if isinstance(inner, dict) else None
                            if isinstance(rows, list) and rows:
                                sample = json.dumps(rows[0], ensure_ascii=False, default=str)
                                if len(sample) > 5000:
                                    sample = sample[:5000] + "..."
                                network_debug.append("LIST_ITEM_SAMPLE=" + sample)
                except Exception:
                    return

            page.on("response", on_response)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(options.timeout * 1000))
            except PlaywrightTimeoutError as exc:
                warnings.append(f"browser navigation timed out after {options.timeout}s: {exc}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"browser navigation error: {type(exc).__name__}: {exc}")
            page.wait_for_timeout(min(options.browser_wait_ms, 5000))
            dismissed = dismiss_dynamic_overlays(page, max_rounds=5)
            if dismissed:
                page.wait_for_timeout(700)

            for page_index in range(min(options.max_pages, 20)):
                before_jobs = len(jobs)
                try:
                    dismiss_dynamic_overlays(page, max_rounds=2)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(400)
                    clicked = page.evaluate(
                        """() => {
                          const isEnabled = (e) =>
                            e && !e.disabled &&
                            e.getAttribute('aria-disabled') !== 'true' &&
                            !/(^|\\s)(disabled|is-disabled)(\\s|$)/i.test(e.className || '');

                          const clickFirst = (els) => {
                            for (const e of els) {
                              if (!isEnabled(e)) continue;
                              try { e.click(); return true; } catch (_) {}
                            }
                            return false;
                          };

                          const words=['下一页','下页','更多','加载更多','Next','Load more'];
                          const textCandidates=[...document.querySelectorAll('button,a')].filter(
                            e => words.some(w => (e.innerText || '').trim().includes(w))
                          );
                          if (clickFirst(textCandidates)) return true;

                          const nextSelectors=[
                            'a[rel="next"]',
                            '[aria-label*="next" i]',
                            '.el-pagination .btn-next',
                            '.ant-pagination-next:not(.ant-pagination-disabled) a',
                            '.ant-pagination-next:not(.ant-pagination-disabled) button',
                            '.van-pagination__item--next:not(.van-pagination__item--disabled) button',
                            'li.next:not(.disabled) a',
                            '.pagination-next:not(.disabled) a',
                            '.pager-next:not(.disabled) a'
                          ];
                          for (const selector of nextSelectors) {
                            if (clickFirst([...document.querySelectorAll(selector)])) return true;
                          }

                          const currentCandidates=[...document.querySelectorAll(
                            '[aria-current="page"], .active, .current, .is-active, .selected'
                          )];
                          let current = null;
                          for (const e of currentCandidates) {
                            const n = parseInt((e.innerText || e.textContent || '').trim(), 10);
                            if (Number.isFinite(n)) { current = n; break; }
                          }
                          if (current !== null) {
                            const target = String(current + 1);
                            const numeric=[...document.querySelectorAll('a,button,li')].filter(e => {
                              const t=(e.innerText || e.textContent || '').trim();
                              if (t !== target || !isEnabled(e)) return false;
                              const parent=e.closest(
                                '[class*="pagination" i], [class*="pager" i], nav, [role="navigation"]'
                              );
                              return !!parent;
                            });
                            if (clickFirst(numeric)) return true;
                          }
                          return false;
                        }"""
                    )
                    if clicked:
                        page.wait_for_timeout(700)
                        dismiss_dynamic_overlays(page, max_rounds=2)
                    elif len(jobs) <= before_jobs:
                        break
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"browser paging stopped at page {page_index + 1}: {type(exc).__name__}: {exc}")
                    break
                if len(jobs) >= options.max_jobs:
                    break

            try:
                anchors = page.locator("a[href]").all()
            except Exception:
                anchors = []
            for anchor in anchors:
                try:
                    title = clean_text(anchor.inner_text())
                    href = canonical_url(anchor.get_attribute("href") or "", page.url)
                    if len(title) > 120 or not _looks_like_job_anchor(title, href):
                        continue
                    if options.keyword and options.keyword.lower() not in title.lower():
                        continue
                    jobs.setdefault(href, Job(id=href, title=title, url=href, source=host))
                except Exception:
                    pass

            informative_jobs, low_quality = _quality_summary(jobs)
            if low_quality:
                try:
                    body_text = clean_text(page.locator("body").inner_text())
                    if len(body_text) > 1200:
                        body_text = body_text[:1200] + "..."
                    warnings.append(
                        f"browser final_url={page.url}; quality={informative_jobs}/{len(jobs)} informative; body_sample={body_text}"
                    )
                except Exception:
                    pass
                if network_debug:
                    warnings.append("browser API trace:\n" + "\n".join(network_debug))
            browser.close()

        values = list(jobs.values())[: options.max_jobs]
        dedup: dict[tuple[str, str], Job] = {}
        for job in values:
            dedup[(job.title, job.url)] = job
        return CrawlResult(self.name, url, list(dedup.values()), warnings)
