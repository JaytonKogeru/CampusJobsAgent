from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .detector import pick_adapter
from .models import CrawlOptions, CrawlResult
from .report import as_json, as_markdown


def parse_command(body: str) -> dict:
    body = (body or "").strip()
    m = re.search(r"```(?:ya?ml|json)?\s*([\s\S]*?)```", body, re.I)
    if m:
        body = m.group(1).strip()
    try:
        data = yaml.safe_load(body) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if "url" not in data and "targets" not in data:
        m = re.search(r"https?://\S+", body)
        if m:
            data["url"] = m.group(0).rstrip(")]>.,")
    return data


def as_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def make_options(cmd: dict[str, Any], defaults: dict[str, Any] | None = None) -> CrawlOptions:
    merged: dict[str, Any] = dict(defaults or {})
    merged.update({k: v for k, v in cmd.items() if v is not None})
    return CrawlOptions(
        keyword=str(merged.get("keyword") or ""),
        scope=str(merged.get("scope") or "campus"),
        page_size=max(1, min(int(merged.get("page_size") or 50), 100)),
        max_pages=max(1, min(int(merged.get("max_pages") or 30), 100)),
        max_jobs=max(1, min(int(merged.get("max_jobs") or 500), 1000)),
        include_details=as_bool(merged.get("details"), True),
        timeout=max(5.0, min(float(merged.get("timeout") or 25), 120.0)),
    )


def crawl_one(url: str, options: CrawlOptions) -> CrawlResult:
    adapter = pick_adapter(url)
    try:
        return adapter.crawl(url, options)
    except Exception as exc:  # noqa: BLE001 - failed sites must still leave diagnostics for the chat agent
        return CrawlResult(
            adapter=f"{adapter.name}-error",
            source_url=url,
            jobs=[],
            warnings=[f"crawl failed: {type(exc).__name__}: {exc}"],
        )


def normalize_targets(cmd: dict[str, Any]) -> list[dict[str, Any]]:
    raw = cmd.get("targets")
    if raw is None:
        url = str(cmd.get("url") or "").strip()
        return [{"url": url}] if url else []
    if not isinstance(raw, list):
        raise SystemExit("`targets:` must be a YAML/JSON list")
    max_targets = max(1, min(int(cmd.get("max_targets") or 200), 200))
    out: list[dict[str, Any]] = []
    for item in raw[:max_targets]:
        if isinstance(item, str):
            target = {"url": item}
        elif isinstance(item, dict):
            target = dict(item)
        else:
            continue
        url = str(target.get("url") or "").strip()
        if not url:
            continue
        target["url"] = url
        out.append(target)
    return out


def safe_name(value: object, fallback: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", str(value or "").strip()).strip("-._")
    return text[:60] or fallback


def run_single(number: int, cmd: dict[str, Any], output_dir: str) -> tuple[Path, Path, int]:
    url = str(cmd.get("url") or "").strip()
    if not url:
        raise SystemExit("Issue body must contain `url:` or a public URL")
    result = crawl_one(url, make_options(cmd))

    out = Path(output_dir) / f"issue-{number}"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "jobs.json"
    md_path = out / "summary.md"
    json_path.write_text(as_json(result), encoding="utf-8")
    md_path.write_text(as_markdown(result, limit=80), encoding="utf-8")
    return json_path, md_path, len(result.jobs)


def run_batch(number: int, cmd: dict[str, Any], output_dir: str) -> tuple[Path, Path, int]:
    targets = normalize_targets(cmd)
    if not targets:
        raise SystemExit("Batch issue body must contain at least one valid target under `targets:`")

    defaults = {k: v for k, v in cmd.items() if k not in {"targets", "url", "name", "max_targets"}}
    out = Path(output_dir) / f"issue-{number}"
    targets_dir = out / "targets"
    targets_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    aggregate_jobs: list[dict[str, Any]] = []
    total = 0
    failed = 0

    for index, target in enumerate(targets, 1):
        name = str(target.get("name") or target.get("company") or f"target-{index:03d}").strip()
        url = target["url"]
        options = make_options(target, defaults)
        result = crawl_one(url, options)
        if result.adapter.endswith("-error"):
            failed += 1
        total += len(result.jobs)

        slug = f"{index:03d}-{safe_name(name, f'target-{index:03d}')}"
        target_dir = targets_dir / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        target_json = target_dir / "jobs.json"
        target_md = target_dir / "summary.md"
        target_json.write_text(as_json(result), encoding="utf-8")
        target_md.write_text(as_markdown(result, limit=40), encoding="utf-8")

        for job in result.jobs:
            row = job.to_dict()
            row["target_name"] = name
            row["target_url"] = url
            aggregate_jobs.append(row)

        summaries.append(
            {
                "index": index,
                "name": name,
                "url": url,
                "adapter": result.adapter,
                "count": len(result.jobs),
                "warnings": result.warnings,
                "result_file": str(target_json),
            }
        )

    aggregate = {
        "mode": "batch",
        "targets_count": len(targets),
        "failed_targets": failed,
        "count": total,
        "targets": summaries,
        "jobs": aggregate_jobs,
    }
    json_path = out / "jobs.json"
    json_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Batch crawl result",
        "",
        f"- Targets: **{len(targets)}**",
        f"- Failed targets: **{failed}**",
        f"- Total jobs: **{total}**",
        "",
        "| # | 公司/目标 | Adapter | 岗位数 | 警告数 | 结果 |",
        "|---:|---|---|---:|---:|---|",
    ]
    for item in summaries:
        rel = Path(item["result_file"]).relative_to(out)
        name = str(item["name"]).replace("|", "\\|")
        adapter = str(item["adapter"]).replace("|", "\\|")
        lines.append(
            f"| {item['index']} | {name} | `{adapter}` | {item['count']} | {len(item['warnings'])} | `{rel}` |"
        )
    warning_items = [item for item in summaries if item["warnings"]]
    if warning_items:
        lines += ["", "## Diagnostics"]
        for item in warning_items[:50]:
            first = str(item["warnings"][0]).replace("\n", " ")
            lines.append(f"- **{item['name']}**: {first[:500]}")
    md_path = out / "summary.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, total


def run_issue(event_path: str, output_dir: str) -> tuple[Path, Path, int]:
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    number = int(issue.get("number") or 0)
    cmd = parse_command(issue.get("body") or "")
    if cmd.get("targets") is not None:
        return run_batch(number, cmd, output_dir)
    return run_single(number, cmd, output_dir)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--event", required=True)
    p.add_argument("--output-dir", default="runs")
    args = p.parse_args(argv)
    j, m, count = run_issue(args.event, args.output_dir)
    print(json.dumps({"json": str(j), "summary": str(m), "count": count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
