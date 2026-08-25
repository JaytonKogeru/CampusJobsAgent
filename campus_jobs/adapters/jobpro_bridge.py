from __future__ import annotations

import json
import os
import subprocess
from urllib.parse import urlparse

from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text, walk_dicts

from .base import BaseAdapter

# Official careers domains supported by the upstream MIT-licensed job-pro CLI.
# Sites with native adapters in this repo are still handled first by priority.
DOMAIN_TO_COMPANY = {
    "join.qq.com": "tencent",
    "careers.tencent.com": "tencent",
    "jobs.bytedance.com": "bytedance",
    "talent.alibaba.com": "alibaba",
    "campus-talent.alibaba.com": "alibaba",
    "zhaopin.meituan.com": "meituan",
    "job.xiaohongshu.com": "xiaohongshu",
    "campus.jd.com": "jd",
    "zhaopin.jd.com": "jd",
    "campus.kuaishou.cn": "kuaishou",
    "talent.baidu.com": "baidu",
    "hr.163.com": "netease",
    "talent.didiglobal.com": "didi",
    "jobs.bilibili.com": "bilibili",
    "careers.pinduoduo.com": "pdd",
    "career.huawei.com": "huawei",
    "ats.openout.mihoyo.com": "mihoyo",
    "campus.pingan.com": "pingan",
    "careers.ctrip.com": "trip",
    "job.byd.com": "byd",
    "hrcareersweb.antgroup.com": "antgroup",
    "www.lixiang.com": "liauto",
    "campus.sf-express.com": "sf",
    "nio.jobs.feishu.cn": "nio",
    "zhipu-ai.jobs.feishu.cn": "zhipu",
    "agirobot.jobs.feishu.cn": "agibot",
    "01ai.jobs.feishu.cn": "zerooneai",
    "hr.sensetime.com": "sensetime",
    "iflytek.zhiye.com": "iflytek",
    "xiaopeng.jobs.feishu.cn": "xpeng",
}


def _company_for_host(host: str) -> str:
    host = host.lower()
    if host in DOMAIN_TO_COMPANY:
        return DOMAIN_TO_COMPANY[host]
    for domain, company in DOMAIN_TO_COMPANY.items():
        if host.endswith("." + domain):
            return company
    return ""


def _extract_position_dicts(payload: object) -> list[dict]:
    candidates: list[dict] = []
    for obj in walk_dicts(payload):
        title = obj.get("title") or obj.get("name") or obj.get("position_name")
        post_id = obj.get("post_id") or obj.get("id") or obj.get("position_id")
        if title and post_id:
            candidates.append(obj)
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for obj in candidates:
        title = clean_text(obj.get("title") or obj.get("name") or obj.get("position_name"))
        post_id = clean_text(obj.get("post_id") or obj.get("id") or obj.get("position_id"))
        key = (post_id, title)
        if key not in seen:
            seen.add(key)
            out.append(obj)
    return out


class JobProBridgeAdapter(BaseAdapter):
    """Broad official-site bridge backed by @ha7ch/job-pro.

    This is used only for company domains explicitly mapped above. It never
    invokes job-pro's third-party Liepin adapters. Unknown sites continue to
    the generic browser fallback.
    """

    name = "job-pro-bridge"
    priority = 35

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return bool(_company_for_host(urlparse(url).hostname or ""))

    @staticmethod
    def _run(args: list[str], timeout: float) -> object:
        command = os.getenv("CAMPUS_JOBS_JOBPRO", "").strip()
        if command:
            prefix = command.split()
        else:
            prefix = ["npx", "-y", "@ha7ch/job-pro@1.2.1"]
        proc = subprocess.run(
            [*prefix, *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(20, int(timeout * 2)),
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or f"job-pro exit {proc.returncode}").strip()[:1200])
        text = proc.stdout.strip()
        if not text:
            raise RuntimeError("job-pro returned empty output")
        # --compact is one JSON object; tolerate banners by taking the last valid JSON line.
        for line in reversed(text.splitlines()):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"job-pro returned non-JSON output: {text[:500]}") from exc

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        host = urlparse(url).hostname or ""
        company = _company_for_host(host)
        if not company:
            raise ValueError("No job-pro company mapping for this domain")

        warnings: list[str] = []
        scope = options.scope if options.scope in {"campus", "intern", "social", "all"} else "campus"
        page_size = min(max(options.page_size, 1), 100)
        if options.keyword:
            args = [company, "search", options.keyword, "--scope", scope, "--page-size", str(page_size), "--compact"]
        else:
            args = [company, "all", "--scope", scope, "--page-size", str(page_size), "--compact"]
        payload = self._run(args, options.timeout)
        rows = _extract_position_dicts(payload)
        jobs: list[Job] = []
        for item in rows[: options.max_jobs]:
            post_id = clean_text(item.get("post_id") or item.get("id") or item.get("position_id"))
            title = clean_text(item.get("title") or item.get("name") or item.get("position_name"))
            apply_url = clean_text(item.get("apply_url") or item.get("url") or item.get("job_url")) or url
            jobs.append(
                Job(
                    id=post_id,
                    title=title,
                    url=apply_url,
                    company=company,
                    location=clean_text(item.get("work_cities") or item.get("location") or item.get("city")),
                    department=clean_text(item.get("department") or item.get("bgs")),
                    function=clean_text(item.get("project") or item.get("category")),
                    recruit_type=clean_text(item.get("recruit_label") or item.get("recruit_type")),
                    description=clean_text(item.get("description") or item.get("duty")),
                    requirements=clean_text(item.get("requirements") or item.get("requirement")),
                    source=host,
                    extra=item,
                )
            )

        if options.include_details:
            for job in jobs:
                if job.description and job.requirements:
                    continue
                try:
                    detail = self._run([company, "detail", job.id, "--compact"], options.timeout)
                    detail_rows = _extract_position_dicts(detail)
                    obj = detail_rows[0] if detail_rows else detail if isinstance(detail, dict) else {}
                    if isinstance(obj, dict):
                        job.description = clean_text(
                            obj.get("description") or obj.get("duty") or obj.get("responsibility") or obj.get("job_description")
                        ) or job.description
                        job.requirements = clean_text(
                            obj.get("requirements") or obj.get("requirement") or obj.get("qualification") or obj.get("job_requirement")
                        ) or job.requirements
                        job.extra.update(obj)
                except Exception as exc:  # noqa: BLE001 - detail failure should not discard the list
                    warnings.append(f"detail {job.id}: {type(exc).__name__}: {exc}")
        return CrawlResult(self.name, url, jobs, warnings)
