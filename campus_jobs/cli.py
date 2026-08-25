from __future__ import annotations

import argparse
from pathlib import Path

from .detector import pick_adapter
from .models import CrawlOptions
from .report import as_csv, as_json, as_markdown


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Crawl public careers sites and normalize live job JDs")
    p.add_argument("url")
    p.add_argument("--keyword", default="")
    p.add_argument("--scope", choices=["campus", "intern", "social", "all"], default="campus")
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--max-pages", type=int, default=30)
    p.add_argument("--max-jobs", type=int, default=500)
    p.add_argument("--no-details", action="store_true")
    p.add_argument("--timeout", type=float, default=25)
    p.add_argument("--format", choices=["json", "csv", "md"], default="json")
    p.add_argument("--raw", action="store_true")
    p.add_argument("--out", default="-")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    adapter = pick_adapter(args.url)
    result = adapter.crawl(args.url, CrawlOptions(
        keyword=args.keyword, scope=args.scope, page_size=args.page_size, max_pages=args.max_pages,
        max_jobs=args.max_jobs, include_details=not args.no_details, timeout=args.timeout,
    ))
    text = as_json(result, raw=args.raw) if args.format == "json" else as_csv(result) if args.format == "csv" else as_markdown(result)
    if args.out == "-":
        print(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"saved {len(result.jobs)} jobs -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
