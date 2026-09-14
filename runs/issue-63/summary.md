# Crawl result

- Adapter: `generic-browser`
- Source: https://talent.lenovo.com.cn/position?projectType=1&workPlace=5
- Jobs: **1**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|
| 1 | 社会招聘 |  |  | [详情](https://jobs.lenovo.com/zh_CN/careers) |

## Warnings
- browser final_url=https://talent.lenovo.com.cn/position?projectType=1&workPlace=5; quality=0/1 informative; body_sample=首页
应届生招聘
人才项目
实习生招聘
了解联想
相关公司校招
登录/Login
查看
联想官网联想乐享联想学生会员参观联想社会招聘联系我们：chinacampus@lenovo.com
联想招聘官方社交平台
版权所有：1998-2022 联想集团法律公告隐私政策产品安全
京ICP备11035381京公网安备110108007970号
- browser API trace:
200 GET https://talent.lenovo.com.cn/gateway/proj/status | post=- | dict keys=['code', 'message', 'result']; result:list[3](['projectType', 'activateFlag'])
200 GET https://talent.lenovo.com.cn/gateway/sysDict/all | post=- | dict keys=['code', 'message', 'result']; result:list[76](['id', 'parentId', 'dictCode', 'dictName', 'dictValue', 'dictSort', 'remark', 'dictEnName', 'isHide', 'children'])
200 GET https://talent.lenovo.com.cn/gateway/projob/select/1 | post=- | dict keys=['code', 'message', 'result']; result:list[6](['id', 'ids', 'projectId', 'parentId', 'typeName', 'children', 'createTime'])
