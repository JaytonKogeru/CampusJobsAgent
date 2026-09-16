# Crawl result

- Adapter: `generic-browser`
- Source: https://zhaopin.greeyun.com/home?navSelect=1
- Jobs: **0**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|

## Warnings
- browser final_url=https://zhaopin.greeyun.com/home?navSelect=1; quality=0/0 informative; body_sample=校园招聘
社会招聘
公司介绍
小G客服登录/注册
职位类型
博士生
技术研发类
信息技术类
技术支持类
制造技术类
经营销售类
行政职能类
采购物流类
职位搜索
职位名称 职位类型 工作地点 发布时间
博士生（集成电路）
博士生
珠海市
2026-08-26
博士生（电机电器）
博士生
珠海市
2026-08-26
博士生（电力电子）
博士生
珠海市
2026-08-26
博士生（机械设计）
博士生
珠海市
2026-08-26
博士生（流体仿真）
博士生
珠海市
2026-08-26
博士生（制冷暖通）
博士生
珠海市
2026-08-26
博士生（噪声振动）
博士生
珠海市
2026-08-26
结构设计
技术研发类
珠海市
2026-08-26
共 52 条
1234567
前往页
Copyright@珠海格力电器股份有限公司
粤公网安备 44040202000145号
粤ICP05006515号
- browser API trace:
200 GET https://zhaopin.greeyun.com/api/apply/jobs?category=&pageNum=1&pageSize=8&property=1 | post=- | dict keys=['code', 'message', 'data']; data:dict(['list', 'total']); data.list:list[8](['ID', 'Category', 'Position', 'Code', 'Location', 'Experience', 'Education', 'Number', 'Salary', 'PubTime', 'PubName', 'InterviewLocation', 'Status', 'Description', 'Qualifications', 'Ctime', 'Utime', 'quarterId', 'property', 'isInternalRecommend'])
200 GET https://zhaopin.greeyun.com/api/apply/job/category?recruitmentCategory=1 | post=- | dict keys=['code', 'message', 'data']; data:list[8](['index', 'category'])
