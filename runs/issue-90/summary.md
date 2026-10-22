# Crawl result

- Adapter: `generic-browser`
- Source: http://zhaopin.ubtrobot.com/campus/jobs
- Jobs: **0**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|

## Warnings
- browser final_url=http://zhaopin.ubtrobot.com/campus/jobs; quality=0/0 informative; body_sample=首页
社会招聘
校园招聘
实习生招聘
公司官网
登录/注册
搜索职位
工作地点
不限
北京市
深圳市
柳州市
发布时间
不限
三天内
一周内
一个月内
三个月内
半年内
一年内
更多
学历要求
工作经验
全部职位（共 70 个）
分享列表全部
C++开发工程师（ROSA）(J18754)
校园招聘
全职
广东省·深圳市
系统工程开发部
本科
2026-08-26 发布
市场营销专员(J18640)
校园招聘
全职
广东省·深圳市
优必行
硕士研究生
2026-08-18 发布
证券事务专员(J18645)
校园招聘
全职
广东省·深圳市
财务部
本科
2026-08-18 发布
财务专员(J18644)
校园招聘
全职
广东省·深圳市
财务部
本科
2026-08-18 发布
设备工程师(J18647)
校园招聘
全职
广东省·深圳市,广西壮族自治区·柳州市
制造中心
硕士研究生
2026-08-18 发布
人力资源专员(J18646)
校园招聘
全职
广东省·深圳市
人才动能中心
本科
2026-08-18 发布
工艺工程师(J18648)
校园招聘
全职
广东省·深圳市,广西壮族自治区·柳州市
制造中心
硕士研究生
2026-08-18 发布
空间智能重建研究员（优核U-Core计划）(J18710)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
空间智能具身导航研究员（优核U-Core计划）(J18709)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
关节模组设计工程师（优核U-Core计划）(J18712)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
空间智能时空记忆研究员（优核U-Core计划）(J18711)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
仿生机构设计工程师（优核U-Core计划）(J18714)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
灵巧手设计工程师（优核U-Core计划）(J18713)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
大模型算法研究员（优核U-Core计划）(J18717)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
世界模型算法研究员（优核U-Core计划）(J18715)
校园招聘
全职
广东省·深圳市
具身智能与人形机器人研究院
博士研究生
2026-08-18 发布
具身强化算法研究员（优核U-Core计划）(J187...
- browser API trace:
200 GET http://zhaopin.ubtrobot.com/api/PortalAgent/GetPortalAgentConfig?portalId=4f4d24cb-5973-40d0-9fde-27c6a0dd8570 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['FloatingIconClientUrl', 'ShowFloatingButton', 'HasAgentPermission', 'QuickQuestions'])
200 GET http://zhaopin.ubtrobot.com/api/Common/GetPortalAIRobot?_timestamp=1711792655341882 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:dict(['IsOpen', 'PubKey'])
200 GET http://zhaopin.ubtrobot.com/api/Template/GetPageGlobalModules | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']
200 GET http://zhaopin.ubtrobot.com/api/Jobad/GetSpecialJobAdList?_timestamp=7281792655343127&category=2&type=1&langType=zh_CN | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[0]
200 GET http://zhaopin.ubtrobot.com/api/Jobad/GetSpecialJobAdList?_timestamp=1911792655343145&category=2&type=1&langType=zh_CN | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[0]
200 POST http://zhaopin.ubtrobot.com/api/Jobad/GetJobAdSearchConditions | post={"PageId":"0d7a125c-47c8-48cf-b5a1-7342cbe6a6a5","displayFilters":["LocId","Degree","YearsOfWorking"],"Category":["2"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[3](['HasMore', 'Name', 'Value', 'Type', 'Sort', 'Data', 'IDS'])
200 POST http://zhaopin.ubtrobot.com/api/Jobad/GetJobAdPageList | post={"PageIndex":0,"PageSize":20,"Category":["2"],"KeyWords":"","SpecialType":0,"PortalId":"","DisplayFields":["Category","Kind","LocId","Org","PostDate","Degree","WorkWeChatQrCode"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[20](['Id', 'HeadCount', 'JobAdId', 'PostDateInt', 'PostDate', 'EndTimeInt', 'EndTime', 'JobAdName', 'OrgId', 'Org', 'Category', 'CategoryId', 'LocId', 'LocNames', 'Salary', 'Duty', 'Require', 'ClassificationOne', 'ClassificationTwo', 'Classification3'])
200 GET http://zhaopin.ubtrobot.com/api/Jobad/SearchAreasTreeConditions?_timestamp=4711792655343516&categoryId=2 | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[6](['Code', 'Name', 'ParentCode', 'HasChildren'])
200 GET http://zhaopin.ubtrobot.com/api/Jobad/GetSpecialJobAdList?_timestamp=4701792655343769&category=2&type=1&langType=zh_CN | post=- | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[0]
200 POST http://zhaopin.ubtrobot.com/api/Jobad/GetJobAdSearchConditions | post={"PageId":"0d7a125c-47c8-48cf-b5a1-7342cbe6a6a5","displayFilters":["LocId","Degree","YearsOfWorking"],"Category":["2"]} | dict keys=['Code', 'Message', 'MoreMessage', 'TipType', 'Count', 'ReturnUrl', 'Data', 'Total']; Data:list[3](['HasMore', 'Name', 'Value', 'Type', 'Sort', 'Data', 'IDS'])
