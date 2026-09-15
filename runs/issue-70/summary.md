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
筛选
清空
公司
显示事业部
空气事业部
冰冷事业部
聚好看公司
激光事业部
洗护事业部
厨电事业部
ASKO事业部
gorenje事业部
全球营销中心
VIDAA（系统）公司
信扬公司
海信网络能源公司
纳真科技公司
信芯微公司
海普林光电
海信集团财务公司
集团公司
职位类别
软件算法类
硬件研发类
光学及显示类
芯片类
结构类
材料类
仿真研发类
暖通制冷类
技术工艺类
技术类
测试类
设计类
营销类
运营类
人力资源类
财经金融类
法务类
行政类
其他管理类
质量类
制造工艺类
安全类
生产制造类
供应链管理类
工作地点
全国
天津市
上海市
北京市
贵州省
四川省
辽宁省
云南省
吉林省
重庆市
+更多
搜索职位
全部职位（共 530 个）
分享列表全部
大客户经理(J44652)
校园招聘
山东省·青岛市
营销类
冰冷事业部
2026-09-15 发布
包装设计工程师(J45564)
校园招聘
山东省·青岛市
结构类
洗护事业部
2026-09-15 发布
模具设计工程师(J45492)
校园招聘
广东省·佛山市
结构类
冰冷事业部
2026-09-15 发布
人力资源管理(J44600)
校园招聘
山东省·青岛市
人力资源类
冰冷事业部
2026-09-15 发布
供应链管理(采购运营)(J44595)
校园招聘
山东省·青岛市
供应链管理类
冰冷事业部
2026-09-15 发布
供应链管理(战略寻源)(J44650)
校园招聘
山东省·青岛市
供应链管理类
冰冷事业部
2026-09-15 发布
食品保鲜研发工程师(J45028)
校园招聘
山东省·青岛市
材料类
冰冷事业部
2026-09-15 发布
电气开发工程师(J45015)
校园招聘
广东省·佛山市
硬件研发类
冰冷事业部
2026-09-15 发布
安全管理工程师(J44818)
校园招聘
山东省·青岛市·平度市
安全类
洗护事业部
2026-09-15 发布
大客户经理(J44653)
校园招聘
山东省·青岛市
营销类
冰冷事业部
2026-09-15 发布
安全管理工程师(J44649)
校园招聘
广东省·佛山市
安全类
冰冷事业部
2026-09-15 发布
软件开发工程师（嵌入式开发）(J45012)
校园招聘
广东省·佛山市
软件算法类
冰冷事业部
2026-09-15 发布
产品工艺工程师（新品工艺）(J44601)
校园招聘
山东省·青岛市
制造工艺类
冰冷事业部
2026-09-15 发布
软件开发工程师（嵌入式开发方向）(J44596)
校园招聘
山东省·青岛市
软件算法类
冰冷事业部
2026-09-15 发布
设备技术工程师（设备管理）(J44602)
校园招聘
山东省·青岛市
生产制造类
冰冷事业部
2026-09-...
- browser API trace:
200 GET https://jobs.hisense.com/api/Common/GetPortalAIRobot?_timestamp=7871789476772740 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['IsOpen', 'PubKey'])
200 GET https://jobs.hisense.com/api/PortalAgent/GetPortalAgentConfig?portalId=05f0dd33-82e6-4de1-b950-3d142c9833a1 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['FloatingIconClientUrl', 'ShowFloatingButton', 'HasAgentPermission', 'QuickQuestions'])
200 GET https://jobs.hisense.com/api/Template/GetPageGlobalModules | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']
200 POST https://jobs.hisense.com/api/Jobad/GetJobAdPageList | post={"PageIndex":0,"PageSize":20,"Category":["2"],"KeyWords":"","SpecialType":0,"PortalId":"","DisplayFields":["Category","LocId","PostDate","ClassificationOne","ClassificationTwo","WorkWeChatQrCode"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[20](['Id', 'HeadCount', 'JobAdId', 'PostDateInt', 'PostDate', 'EndTimeInt', 'EndTime', 'JobAdName', 'OrgId', 'Org', 'Category', 'CategoryId', 'LocId', 'LocNames', 'Salary', 'Duty', 'Require', 'ClassificationOne', 'ClassificationTwo', 'Classification3'])
200 POST https://jobs.hisense.com/api/Jobad/GetJobAdSearchConditions | post={"PageId":"b39a9bf2-03be-4e18-9e4e-7200577d60e1","displayFilters":["ClassificationTwo","ClassificationOne","LocId"],"Category":["2"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[3](['HasMore', 'Name', 'Value', 'Type', 'Sort', 'Data', 'IDS'])
200 POST https://jobs.hisense.com/api/Jobad/GetJobAdSearchConditions | post={"PageId":"b39a9bf2-03be-4e18-9e4e-7200577d60e1","displayFilters":["ClassificationTwo","ClassificationOne","LocId"],"Category":["2"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[3](['HasMore', 'Name', 'Value', 'Type', 'Sort', 'Data', 'IDS'])
200 POST https://jobs.hisense.com/api/Jobad/GetJobAdSearchConditions | post={"PageId":"b39a9bf2-03be-4e18-9e4e-7200577d60e1","displayFilters":["ClassificationTwo","ClassificationOne","LocId"],"Category":["2"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[3](['HasMore', 'Name', 'Value', 'Type', 'Sort', 'Data', 'IDS'])
200 GET https://jobs.hisense.com/api/Jobad/SearchAreasTreeConditions?_timestamp=721789476775073&categoryId=2 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[101](['Code', 'Name', 'ParentCode', 'HasChildren'])
200 POST https://jobs.hisense.com/api/Jobad/GetJobAdPageList | post={"PageIndex":1,"PageSize":20,"Category":["2"],"KeyWords":"","SpecialType":0,"PortalId":"","DisplayFields":["Category","LocId","PostDate","ClassificationOne","ClassificationTwo","WorkWeChatQrCode"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[20](['Id', 'HeadCount', 'JobAdId', 'PostDateInt', 'PostDate', 'EndTimeInt', 'EndTime', 'JobAdName', 'OrgId', 'Org', 'Category', 'CategoryId', 'LocId', 'LocNames', 'Salary', 'Duty', 'Require', 'ClassificationOne', 'ClassificationTwo', 'Classification3'])
