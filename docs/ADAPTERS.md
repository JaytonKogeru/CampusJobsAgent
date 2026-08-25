# Adapter coverage

| Adapter | Typical sites | Strategy |
|---|---|---|
| Moka | app.mokahr.com (e.g. Shokz/TI-style Moka portals) | public list/detail API + AES envelope decrypt |
| ATSX / Feishu Recruiting | Xiaomi mioffice fork, ByteDance-style ATSX | public search + detail API |
| vivo campus | hr-campus.vivo.com | Beisen JobAd API |
| OPPO | careers.oppo.com | OPPO public page/detail API |
| Wecruit | hotjob / Beisen Wecruit tenants | form-urlencoded list/detail API |
| Greenhouse | boards.greenhouse.io | official boards API |
| Lever | jobs.lever.co | public JSON feed |
| Ashby | jobs.ashbyhq.com | posting API |
| SmartRecruiters | jobs.smartrecruiters.com | public company postings API |
| Workday | *.myworkdayjobs.com | CXS jobs API |
| Generic browser | unknown public SPA | Playwright + XHR/JSON interception + DOM fallback |

The generic browser is a fallback, not a CAPTCHA bypass. Login-only, WeChat mini-program and anti-bot protected sites may still require a dedicated adapter.
