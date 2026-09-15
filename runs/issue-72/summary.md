# Crawl result

- Adapter: `generic-browser`
- Source: https://jobs.hisense.com/campus/jobs
- Jobs: **0**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|

## Warnings
- browser final_url=https://jobs.hisense.com/campus/jobs; quality=0/0 informative; body_sample=首页
校园招聘
社会招聘
登录/注册
搜索职位
全部职位（共 0 个）
- browser API trace:
200 GET https://jobs.hisense.com/api/Common/GetPortalAIRobot?_timestamp=3331789476897871 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['IsOpen', 'PubKey'])
200 GET https://jobs.hisense.com/api/PortalAgent/GetPortalAgentConfig?portalId=05f0dd33-82e6-4de1-b950-3d142c9833a1 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['FloatingIconClientUrl', 'ShowFloatingButton', 'HasAgentPermission', 'QuickQuestions'])
200 GET https://jobs.hisense.com/api/Template/GetPageGlobalModules | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']
