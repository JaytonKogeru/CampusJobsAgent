# Crawl result

- Adapter: `hcmcloud`
- Source: https://inspur.hcmcloud.cn/recruit
- Jobs: **0**
- Warnings: **4**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|

## Warnings
- integrity unverified: HCMCloud ended on the first rendered page without stable multi-page evidence; jobs=0, upstream total=None, expected_pages=None
- HCMCloud pager controls:
tag=INPUT cls='ng-pristine ng-untouched ng-valid ng-empty' text='' title='' aria='' disabled=False value='' context='home-page ng-scope :: 社会招聘'
- HCMCloud rendered no job rows; company=浪潮; reason=no-next-control; body_sample=社会招聘
校园招聘
实习生招聘
登录
|
注册
Language
社会招聘
- HCMCloud API trace:
200 GET https://inspur.hcmcloud.cn/api/auth/get_customer_css
200 GET https://inspur.hcmcloud.cn/api/language/get_language?lang=zh_cn
200 GET https://inspur.hcmcloud.cn/api/auth/get_auth?app_type=recruit&v=0.239728340979135421793004788656&hcm_transfer_strategy=ha5
200 POST https://inspur.hcmcloud.cn/api/recruit.job.class.setting.list
200 POST https://inspur.hcmcloud.cn/api/recruit.get.company.info
200 POST https://inspur.hcmcloud.cn/api/recruit.get.dept.template.info
200 POST https://inspur.hcmcloud.cn/api/get_template
200 POST https://inspur.hcmcloud.cn/api/hcm.ai.get.robot
200 POST https://inspur.hcmcloud.cn/api/recruit.portal.setting.get.portal.info.by.name
