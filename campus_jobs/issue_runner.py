from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

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
    if "url" not in data:
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


def run_issue(event_path: str, output_dir: str) -> tuple[Path, Path, int]:
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    number = int(issue.get("number") or 0)
    cmd = parse_command(issue.get("body") or "")
    url = str(cmd.get("url") or "").strip()
    if not url:
        raise SystemExit("Issue body must contain `url:` or a public URL")
    options = CrawlOptions(
        keyword=str(cmd.get("keyword") or ""),
        scope=str(cmd.get("scope") or "campus"),
        page_size=max(1, min(int(cmd.get("page_size") or 50), 100)),
        max_pages=max(1, min(int(cmd.get("max_pages") or 30), 100)),
        max_jobs=max(1, min(int(cmd.get("max_jobs") or 500), 1000)),
        include_details=as_bool(cmd.get("details"), True),
        timeout=max(5.0, min(float(cmd.get("timeout") or 25), 120.0)),
    )
    adapter = pick_adapter(url)
    try:
        result = adapter.crawl(url, options)
    except Exception as exc:  # noqa: BLE001 - failed sites must still leave diagnostics for the chat agent
        result = CrawlResult(
            adapter=f"{adapter.name}-error",
            source_url=url,
            jobs=[],
            warnings=[f"crawl failed: {type(exc).__name__}: {exc}"],
        )

    out = Path(output_dir) / f"issue-{number}"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "jobs.json"
    md_path = out / "summary.md"
    json_path.write_text(as_json(result), encoding="utf-8")
    md_path.write_text(as_markdown(result, limit=80), encoding="utf-8")
    return json_path, md_path, len(result.jobs)


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
