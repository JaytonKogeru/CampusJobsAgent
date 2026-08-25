# Adapter coverage

| Adapter | Typical sites | Strategy |
|---|---|---|
| Moka | app.mokahr.com (e.g. Shokz/TI-style Moka portals) | public list/detail API + AES envelope decrypt |
| ATSX / Feishu Recruiting | Xiaomi mioffice fork, ByteDance-style ATSX | public search + detail API; browser fallback |
| vivo campus | hr-campus.vivo.com | official JobAd API |
| OPPO | careers.oppo.com | OPPO public page/detail API |
| Wecruit | hotjob / Beisen Wecruit tenants | form-urlencoded list/detail API |
| Greenhouse | boards.greenhouse.io / job-boards.greenhouse.io | official boards API |
| Lever | jobs.lever.co | public JSON feed |
| Ashby | jobs.ashbyhq.com | public posting API |
| SmartRecruiters | jobs.smartrecruiters.com | public company postings API |
| Workday | *.myworkdayjobs.com | CXS jobs API |
| job-pro bridge | many known Chinese big-tech official domains | pinned `@ha7ch/job-pro@1.2.1`, official-domain mapping only |
| Generic browser | unknown public SPA | Playwright + XHR/JSON interception + DOM fallback |

## job-pro official-domain bridge

The bridge currently maps official domains for Tencent, ByteDance, Alibaba, Meituan, Xiaohongshu, JD, Kuaishou, Baidu, NetEase, Didi, Bilibili, PDD, Huawei, miHoYo, Ping An, Trip.com, BYD, Ant Group, Li Auto, SF Express, NIO, Zhipu, Agibot, 01.AI, SenseTime, iFlytek and XPeng.

Native adapters in this repository take priority. The bridge deliberately does **not** map job-pro's Liepin third-party fallback sources.

## Fallback boundary

The generic browser is a fallback, not a CAPTCHA/login bypass. Login-only, WeChat mini-program and strongly geo/WAF-protected sites may still require a dedicated adapter or an optional outbound proxy. Failures are persisted as warnings so the caller can automatically choose another source instead of silently returning stale jobs.
