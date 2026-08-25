# CampusJobsAgent

把公开招聘官网统一抓成结构化职位/JD JSON，重点解决国内校招站常见的 JS 动态渲染、分页、ATS 差异和搜索引擎旧岗位问题。

## 最主要的用法：直接在 ChatGPT 里命令

以后你只需要发类似：

> 查这个官网，结合我的简历筛最适合的岗位：https://...

> 把 OPPO 27 届官网算法岗位全部扫一遍，按匹配度排序。

> 小米只能投一个，帮我从当前官网 JD 里选第一志愿。

ChatGPT 可直接使用本仓库作为远程抓取控制面：

1. 识别官网/ATS；
2. 在本仓库创建临时 `[crawl]` Issue；
3. GitHub Actions 调官方公开 API，必要时启动 Chrome/Playwright 拦截 XHR；
4. 将规范化结果写入 `runs/issue-<N>/jobs.json`；
5. ChatGPT 读取当前真实 JD，再与你的简历做筛选、排序和岗位分析。

你不需要自己 F12、复制 Network Response 或批量截图。

## 本地 CLI

```bash
pip install -e '.[browser]'

campus-jobs 'https://xiaomi.jobs.f.mioffice.cn/campus/' --scope campus --keyword AI --out jobs.json
campus-jobs 'https://app.mokahr.com/campus-recruitment/aftershokzhr/36940' --scope campus --format md
```

Playwright fallback 会优先使用机器已有的 Chrome/Chromium；若本地完全没有浏览器，再自行安装 Chromium 即可。

## Issue 远程命令协议

Title:

```text
[crawl] 小米 27 届 AI 岗位
```

Body:

```yaml
url: https://xiaomi.jobs.f.mioffice.cn/campus/
keyword: AI
scope: campus
page_size: 50
max_pages: 30
max_jobs: 500
details: true
```

详见 [`docs/COMMANDS.md`](docs/COMMANDS.md)。失败也不会丢掉诊断信息：结果 JSON 会记录 adapter、warnings 和错误原因，方便 ChatGPT 自动换方案。

## 当前覆盖

### 原生适配器

- Moka
- 飞书招聘 ATSX / 小米 mioffice
- vivo 校招公开 API
- OPPO 公开 API
- Beisen Wecruit
- Greenhouse
- Lever
- Ashby
- SmartRecruiters
- Workday

### 国内大厂扩展层

内置 `job-pro` bridge，可对腾讯、字节、阿里、美团、小红书、京东、快手、百度、网易、滴滴、B站、拼多多、华为、米哈游、平安、携程、比亚迪、蚂蚁、理想、顺丰、蔚来、智谱、智元、商汤、讯飞、小鹏等已知官方招聘域名复用成熟适配器。

bridge 只映射官方招聘域名，不默认启用第三方聚合岗位。

### 最终兜底

未知公开 SPA 使用 Playwright：监听页面 JSON/XHR、滚动/翻页并从 DOM 提取职位链接。因此新公司的官网即使没有专门 adapter，也有机会自动读取。

详见 [`docs/ADAPTERS.md`](docs/ADAPTERS.md)。

## 网络限制与自动降级

少数中国招聘站会按云机房出口、地区或 WAF 策略限制 GitHub Hosted Runner。系统会：

- API 失败后切浏览器；
- 浏览器失败后保留诊断结果，不假装抓到了完整岗位；
- 支持可选 `CAMPUS_JOBS_PROXY` GitHub Secret，让 HTTP 与 Playwright 共用同一代理；
- ChatGPT 仍可继续使用网页检索等可用路径补充验证，而无需你操作开发者工具。

## 输出格式

每个岗位统一包含：

- `id`
- `title`
- `url`
- `company`
- `location`
- `department`
- `function`
- `recruit_type`
- `description`
- `requirements`
- `source`

可输出 JSON / CSV / Markdown。

## 安全边界

- 官方公开职位页面/API 优先。
- 不绕过登录、验证码、付费墙或私有系统。
- 拒绝 localhost、私网和保留地址，降低 SSRF 风险。
- 抓取限制页数/岗位数，不做无边界扫描。
- 失败时显式报告，不用历史搜索结果冒充官网当前岗位。

## 测试

CI 运行单元测试和 Python correctness lint。`[crawl]` Issue 同时承担真实招聘站 E2E smoke test。

## 灵感与参考

ATS-family 与国内招聘站适配思路参考 MIT 开源项目 `HA7CH/job-pro`，浏览器/XHR fallback 参考 `TongyiDai/career-ops-zh` 的工程实践。本仓库保持独立实现，仅处理公开招聘数据。

## License

MIT
