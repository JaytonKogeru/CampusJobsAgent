# Issue command protocol

Create an issue whose title starts with `[crawl]`.

## Single site

```yaml
url: https://xiaomi.jobs.f.mioffice.cn/campus/
keyword: AI
scope: campus
page_size: 50
max_pages: 30
max_jobs: 500
details: true
```

The workflow commits `jobs.json` and `summary.md` under `runs/issue-<N>/` and comments the issue with a compact table.

## Batch crawl

For large campus-search sweeps, one issue can contain up to 200 public recruiting targets. Global options act as defaults; an individual target may override them.

```yaml
scope: campus
page_size: 50
max_pages: 20
max_jobs: 300
details: true
max_targets: 200

targets:
  - name: 小米
    url: https://xiaomi.jobs.f.mioffice.cn/campus/
    keyword: 算法
  - name: 韶音
    url: https://app.mokahr.com/campus-recruitment/aftershokzhr/36940
  - name: 长鑫存储
    url: https://cxmt.zhiye.com/campus/jobs
```

Batch mode isolates failures per target and writes:

- `runs/issue-<N>/jobs.json`: aggregate target diagnostics plus flattened jobs;
- `runs/issue-<N>/summary.md`: company-level crawl summary;
- `runs/issue-<N>/targets/<index-company>/jobs.json`: each target's normalized jobs/JDs;
- `runs/issue-<N>/targets/<index-company>/summary.md`: each target's compact table.

The batch is sequential by design so public recruiting sites are not hit with a large burst and Git commits remain deterministic. A failed site does not discard successful results from the other companies.

This protocol is intentionally simple so a chat agent with GitHub access can issue crawls, then read committed JSON after Actions finishes.
