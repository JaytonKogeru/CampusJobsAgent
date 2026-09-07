from __future__ import annotations

import json
import os
import shutil
from urllib.parse import urlparse

from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import assert_public_url, clean_text
from .base import BaseAdapter


class QQDocsSourceAdapter(BaseAdapter):
    """Best-effort extractor for public Tencent Docs smart sheets.

    This is intentionally a source-ingestion adapter rather than a job-board
    adapter. It renders the public sheet, scrolls virtualized containers, and
    stores visible text, outbound links and useful JSON/XHR samples in a single
    normalized record so ChatGPT can use the sheet as an index of company
    recruitment links.
    """

    name = "qqdocs-source"
    priority = 99

    @classmethod
    def can_handle(cls, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return host in {"docs.qq.com", "docs.qq.cn"}

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        assert_public_url(url)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for Tencent Docs extraction") from exc

        lines: list[str] = []
        seen_lines: set[str] = set()
        links: dict[str, str] = {}
        network_samples: list[dict] = []
        warnings: list[str] = []

        def absorb_text(text: str) -> None:
            for raw in (text or "").splitlines():
                s = clean_text(raw)
                if not s or s in seen_lines:
                    continue
                seen_lines.add(s)
                lines.append(s)

        with sync_playwright() as p:
            launch_kwargs: dict[str, object] = {"headless": True}
            chrome = next(
                (path for path in [
                    shutil.which("google-chrome"),
                    shutil.which("google-chrome-stable"),
                    shutil.which("chromium"),
                    shutil.which("chromium-browser"),
                ] if path),
                None,
            )
            if chrome:
                launch_kwargs["executable_path"] = chrome
            proxy = os.getenv("CAMPUS_JOBS_PROXY", "").strip()
            if proxy:
                launch_kwargs["proxy"] = {"server": proxy}

            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page(viewport={"width": 1600, "height": 1100})

            def on_response(response):
                if len(network_samples) >= 40:
                    return
                try:
                    ct = (response.headers.get("content-type") or "").lower()
                    if "json" not in ct and not any(k in response.url.lower() for k in ["smartsheet", "sheet", "table", "records", "rows"]):
                        return
                    data = response.json()
                    raw = json.dumps(data, ensure_ascii=False, default=str)
                    # Keep payloads likely to contain row/cell/link data, but cap size.
                    score = sum(k in raw.lower() for k in ["http", "company", "招聘", "校招", "record", "cell", "row", "link"])
                    if score == 0 and len(network_samples) >= 12:
                        return
                    network_samples.append({
                        "url": response.url,
                        "status": response.status,
                        "sample": raw[:20000],
                    })
                except Exception:
                    return

            page.on("response", on_response)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(options.timeout * 1000))
                page.wait_for_timeout(7000)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Tencent Docs navigation: {type(exc).__name__}: {exc}")

            # Collect initial text and then walk virtualized scroll containers.
            try:
                absorb_text(page.locator("body").inner_text())
            except Exception:
                pass

            try:
                scrollables = page.evaluate(
                    """() => [...document.querySelectorAll('*')]
                      .filter(e => e.scrollHeight > e.clientHeight + 120 && e.clientHeight > 180)
                      .map((e,i)=>({i, sh:e.scrollHeight, ch:e.clientHeight, cls:e.className||'', tag:e.tagName}))
                      .sort((a,b)=>b.sh-a.sh).slice(0,8)"""
                )
                warnings.append("scrollables=" + json.dumps(scrollables, ensure_ascii=False)[:3000])
            except Exception:
                scrollables = []

            for _ in range(min(max(options.max_pages * 4, 16), 60)):
                try:
                    moved = page.evaluate(
                        """() => {
                          const es=[...document.querySelectorAll('*')]
                            .filter(e => e.scrollHeight > e.clientHeight + 120 && e.clientHeight > 180)
                            .sort((a,b)=>b.scrollHeight-a.scrollHeight);
                          const e=es[0];
                          if(!e) { window.scrollBy(0,900); return true; }
                          const before=e.scrollTop;
                          e.scrollTop=Math.min(e.scrollTop+Math.max(600,e.clientHeight*0.85),e.scrollHeight);
                          return e.scrollTop!==before;
                        }"""
                    )
                    page.mouse.wheel(0, 900)
                    page.wait_for_timeout(250)
                    absorb_text(page.locator("body").inner_text())
                    if not moved:
                        break
                except Exception:
                    break

            try:
                for a in page.locator("a[href]").all():
                    try:
                        href = a.get_attribute("href") or ""
                        text = clean_text(a.inner_text())
                        if href.startswith("http"):
                            links[href] = text
                    except Exception:
                        pass
            except Exception:
                pass

            final_url = page.url
            browser.close()

        description = "\n".join(lines)[:120000]
        link_text = "\n".join(f"{t}\t{h}" for h, t in links.items())[:60000]
        extra = {
            "final_url": final_url,
            "visible_line_count": len(lines),
            "links": [{"text": t, "url": h} for h, t in links.items()],
            "network_samples": network_samples,
        }
        job = Job(
            id="qqdocs-source-snapshot",
            title="Tencent Docs smart-sheet source snapshot",
            url=url,
            description=description,
            requirements=link_text,
            source="docs.qq.com",
            extra=extra,
        )
        warnings.append(f"captured visible_lines={len(lines)}, links={len(links)}, network_samples={len(network_samples)}")
        return CrawlResult(self.name, url, [job], warnings)
