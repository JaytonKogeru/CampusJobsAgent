from __future__ import annotations

import csv
import io
import json

from .models import CrawlResult


def as_json(result: CrawlResult, raw: bool = False) -> str:
    return json.dumps(result.to_dict(include_extra=raw), ensure_ascii=False, indent=2)


def as_csv(result: CrawlResult) -> str:
    out = io.StringIO()
    fields = ["id", "title", "company", "location", "department", "function", "recruit_type", "url", "description", "requirements", "source"]
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    for job in result.jobs:
        row = job.to_dict()
        w.writerow({k: row.get(k, "") for k in fields})
    return out.getvalue()


def as_markdown(result: CrawlResult, limit: int = 100) -> str:
    lines = [
        "# Crawl result", "",
        f"- Adapter: `{result.adapter}`",
        f"- Source: {result.source_url}",
        f"- Jobs: **{len(result.jobs)}**",
    ]
    if result.warnings:
        lines += [f"- Warnings: **{len(result.warnings)}**"]
    lines += ["", "| # | 岗位 | 地点 | 职能/部门 | 链接 |", "|---:|---|---|---|---|"]
    for i, job in enumerate(result.jobs[:limit], 1):
        title = job.title.replace("|", "\\|")
        loc = job.location.replace("|", "\\|")
        org = (job.function or job.department).replace("|", "\\|")
        lines.append(f"| {i} | {title} | {loc} | {org} | [详情]({job.url}) |")
    if len(result.jobs) > limit:
        lines.append(f"\n> 仅展示前 {limit} 个岗位，完整 JD 请查看 JSON。")
    if result.warnings:
        lines += ["", "## Warnings"] + [f"- {x}" for x in result.warnings[:20]]
    return "\n".join(lines) + "\n"
