# Issue command protocol

Create an issue whose title starts with `[crawl]`. The body is YAML:

```yaml
url: https://xiaomi.jobs.f.mioffice.cn/campus/
keyword: AI
scope: campus
page_size: 50
max_pages: 30
max_jobs: 500
details: true
```

The workflow commits two files under `runs/issue-<N>/` and comments the issue with a compact table.

This protocol is intentionally simple so a chat agent with GitHub access can issue crawls by creating an issue, then read the committed JSON after Actions finishes.
