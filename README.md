# CampusJobsAgent

把公开招聘官网统一抓成结构化职位/JD JSON。重点解决国内校招站常见的 JS 动态渲染、分页和 ATS 差异问题。

## 你以后怎么用

在 ChatGPT 里直接发：

> 查这个官网，帮我筛适合的岗位：https://...

如果当前网页工具无法完整读取动态招聘站，ChatGPT 可以在本仓库创建一个 `[crawl]` Issue。GitHub Actions 会自动运行浏览器/API 抓取，并把结果提交到 `runs/issue-<N>/jobs.json`；随后 ChatGPT 读取该 JSON，再结合你的简历做岗位排序。

这避免了让你自己 F12、复制 XHR、截几十张图。

## 本地用法

```bash
pip install -e '.[browser]'
playwright install chromium

campus-jobs 'https://xiaomi.jobs.f.mioffice.cn/campus/' --scope campus --keyword AI --out jobs.json
campus-jobs 'https://app.mokahr.com/campus-recruitment/aftershokzhr/36940' --scope campus --format md
```

## Issue 远程命令

Title:

```text
[crawl] 小米 27 届 AI 岗位
```

Body:

```yaml
url: https://xiaomi.jobs.f.mioffice.cn/campus/
keyword: AI
scope: campus
max_jobs: 500
details: true
```

详见 [`docs/COMMANDS.md`](docs/COMMANDS.md)。

## 当前覆盖

已内置：Moka、飞书 ATSX/小米、vivo 校招、OPPO、Beisen Wecruit、Greenhouse、Lever、Ashby、SmartRecruiters、Workday；未知公开 SPA 用 Playwright 兜底。详见 [`docs/ADAPTERS.md`](docs/ADAPTERS.md)。

## 设计原则

- 官方公开 API 优先，浏览器兜底。
- 不绕过登录、验证码或付费墙。
- 拒绝 localhost/私网 URL，避免 SSRF。
- 抓取有限页数/岗位数，避免无边界扫描。
- 标准化输出，便于后续做简历-JD匹配、投递排序、岗位变化监控。

## 灵感与参考

项目的 ATS-family 设计思路参考了开源项目 `HA7CH/job-pro` 与 `TongyiDai/career-ops-zh` 对国内招聘站公共接口/浏览器兜底的工程实践；本仓库实现保持独立代码结构，并仅面向公开招聘数据。

## License

MIT
