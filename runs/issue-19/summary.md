# Crawl result

- Adapter: `generic-browser`
- Source: https://careers.midea.com/schoolOut/post
- Jobs: **1**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|
| 1 | 社会招聘 |  |  | [详情](https://recruit.midea.com/recruitOut/ihr/home/index) |

## Warnings
- browser final_url=https://careers.midea.com/schoolOut/post; body_sample=首页
岗位投递
招聘动态
关于美的
登录
应届博士招聘
应届生招聘
实习生招聘
筛选
清除
事业部
事业部介绍
家用空调事业部
洗衣机事业部
冰箱事业部
小家电事业部
厨房和热水事业部
微波和烤箱事业部
中国区域
美的国际
国际供应链能力中心
工业设计中心
工业技术事业部
楼宇科技事业部
库卡中国
新能源事业部
美的医疗事业部
安得智联科技公司
企业数字平台
中央研究院
AI研究院
智能制造研究院
采购中心
电子公司
美的金融
集团职能
岗位类别
研发技术类
制造技术类
信息技术类
国内营销类
供应链物流类
海外营销类
财务金融类
管理类
工作地点
佛山市
合肥市
无锡市
上海市
重庆市
芜湖市
苏州市
荆州市
北京市
深圳市
广州市
安庆市
武汉市
邯郸市
中国大陆
昆山市
淮安市
宜春市
成都市
嘉兴市
墨西哥
沈阳市
泰国
济南市
埃及
越南
印尼
青岛市
石家庄市
天津市
银川市
昆明市
兰州市
杭州市
郑州市
长沙市
温州市
呼和浩特市
宁波市
西宁市
在招岗位（144）
算法工程师-运筹优化
信息技术类佛山市、无锡市
1、结合业务场景，完成相关的算法项目的问题抽象、研究和开发，包括路径规划、仓网规划、选址、配送网络规划、库存优化、送装工程师任务分配等；
2、参与与业务、产品关于算法项目的讨论，理解业务需求，确定问题定义、算法技术选型、实施路径；
3、根据问题定义设计算法技术框架、具体的实现方案、功能模块拆分、系统集成接口，并进行算法开发实现；
4、协同产品、业务进行算法测试，随着业务的推进结合实际场景进行算法优化；
5、对业界场景敏感，通过数据分析和业务理解，提出算法在业务的应用和优化机会，并进行推进。
研究员-阀体结构
研发技术类上海市、佛山市
1、负责阀组系统集成设计相关技术研究；
2、负责阀组相关问题分析及优化方案设计；
3、跟踪阀组的最新进展，调研压缩机、阀等技术需求、趋势和行业动态。
研究员-系统PHM算法
研发技术类上海市、佛山市
1、跟踪家用空调系统全生命周期健康管理技术动态，开展售前售中售后核心技术算法、工具、流程的开发、调试、参数优化及问题排查，如售前可视化软件、故障诊断算法等；完成算法应用开发、测试验证及效果复盘，确保工作符合研发流程标准；
2、配合完成客户及价值链相关方的技术对接，落实故障诊断技术及健康管理方案的工程化部署，现场协助解决应用过程中的技术难题，确保技术适配产品场景、满足落地需求；
3、负责技术文档、测试报告、故障处置案例的整理归档，沉淀实操经验与标准化流程，协助优化产品故障诊断模块，提升团队整体实操效率与产品可靠性。
智能开发工程师-传感器
研发技术类佛山市
1、设计、开发和实现融合感知算法，包括雷达、视觉，红外等；
2、辅助进行3D视觉重建工作；
3、参与红外视觉热舒适项目；
4、跟踪学术界的最新进展，掌握最...
- browser API trace:
200 POST https://iotsdk.midea.com/webid | post={"app_id":10000293,"url":"https://careers.midea.com/schoolOut/post","user_agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/151.0.0.0 Safari/537.36","referer":"","user_unique_id":""} | dict keys=['e', 'web_id']
200 GET https://apiprod.midea.com/stp/sc-msct/resource/all/app/public/api/getAppLanguageTypes/recruit-school-out | post=- | dict keys=['code', 'msg', 'errMsg', 'timestamp', 'traceId', 'data', 'success']; data:dict(['pushVersion', 'languageTypes'])
200 GET https://apiprod.midea.com/stp/sc-msct/resource/all/app/public/api/getLanguagePackByte/recruit-school-out | post=- | dict keys=['code', 'msg', 'errMsg', 'timestamp', 'traceId', 'data', 'success']
200 GET https://careers.midea.com/backend/school/position/common/project/list?status=1&projectTypes=1,2,9,5&employementCategories=1,4&_ihr_log_trackId=3cf7f689-deb2-4ac9-ac0b-bcd108344e11 | post=- | dict keys=['code', 'message', 'ihrReturnVersion', 'data', 'stackTrace']; data:list[3](['projectRuleId', 'projectRuleName', 'employementCategory', 'number', 'numberOfDeliver', 'season', 'status', 'numberOfSessions', 'projectType', 'graduationStartDate', 'graduationEndDate', 'schSegmentConfigDtos'])
200 POST https://careers.midea.com/backend/school/resume/common/dicts/items?_ihr_log_trackId=85f109a7-6c2c-456a-81f4-f403e257926a | post=dictCodes%5B0%5D=SCHOOL_OUT_PROJECT_TYPE_SORT&dictCodes%5B1%5D=SCHOOL_OUT_BANNER_IMG&dictCodes%5B2%5D=SCHOOL_OFFICIAL_WEBSITE_DELIVERY_COPY&dictCodes%5B3%5D=SCHOOL_OUT_IS_SHOW_CS_SDK | list[4] sample_keys=['dictName', 'dict']
200 GET https://careers.midea.com/backend/school/position/common/query/params/055bb05d-1957-4ea0-bb21-873ca0164d84?_ihr_log_trackId=d0a6740d-df1e-43f7-919c-cf3ac6bc42f3 | post=- | dict keys=['code', 'message', 'ihrReturnVersion', 'data', 'stackTrace']; data:dict(['projectRuleId', 'largeTypeList', 'sysAreaList', 'superiorList']); data.largeTypeList:list[8](['projectRuleId', 'largeTypeId', 'largeTypeName', 'largeTypeIdCount']); data.sysAreaList:list[40](['projectRuleId', 'workPlaceCode', 'workPlaceName', 'workPlaceCodeCount']); data.superiorList:list[24](['projectRuleId', 'superiorName', 'superiorId', 'sort'])
200 POST https://careers.midea.com/backend/school/position/common/position/list?_ihr_log_trackId=748a5e81-2786-483b-b445-d8735f27e3d7 | post={"keyword":null,"superiorIds":[],"recruitCategoryIds":[],"workPlaceCodes":[],"projectRuleId":"055bb05d-1957-4ea0-bb21-873ca0164d84","pageIndex":1,"pageSize":10} | dict keys=['code', 'message', 'ihrReturnVersion', 'data', 'stackTrace']; data:dict(['data', 'total', 'info', 'additions']); data.data:list[10](['positionId', 'projectRuleId', 'projectType', 'workPlaceCode', 'recruitCategoryId', 'recruitCategoryName', 'projectPositionId', 'projectPositionName', 'workplaceDtoList', 'projectPositionDto', 'employementCategory', 'recommend'])
LIST_ITEM_SAMPLE={"positionId": "8b8b3141a042e82301a0462e8dd00a02", "projectRuleId": "055bb05d-1957-4ea0-bb21-873ca0164d84", "projectType": "1", "workPlaceCode": "佛山市,无锡市", "recruitCategoryId": "56293ba92698407a82d4649b4753d158", "recruitCategoryName": "信息技术类", "projectPositionId": "50b5d00dcef54d5cb78e5011e4f86dd3", "projectPositionName": "算法工程师-运筹优化", "workplaceDtoList": [{"workplaceId": null, "workPlaceCode": null, "workPlaceName": "佛山市", "workPlaceFullCode": null, "workPlaceFullName": null, "unitId": null, "localUnitName": null}, {"workplaceId": null, "workPlaceCode": null, "workPlaceName": "无锡市", "workPlaceFullCode": null, "workPlaceFullName": null, "unitId": null, "localUnitName": null}], "projectPositionDto": {"projectPositionId": "50b5d00dcef54d5cb78e5011e4f86dd3", "positionName": "算法工程师-运筹优化", "largeTypeId": "56293ba92698407a82d4649b4753d158", "largeTypeName": "信息技术类", "jobResponsibility": "1、结合业务场景，完成相关的算法项目的问题抽象、研究和开发，包括路径规划、仓网规划、选址、配送网络规划、库存优化、送装工程师任务分配等；\n2、参与与业务、产品关于算法项目的讨论，理解业务需求，确定问题定义、算法技术选型、实施路径；\n3、根据问题定义设计算法技术框架、具体的实现方案、功能模块拆分、系统集成接口，并进行算法开发实现；\n4、协同产品、业务进行算法测试，随着业务的推进结合实际场景进行算法优化；\n5、对业界场景敏感，通过数据分析和业务理解，提出算法在业务的应用和优化机会，并进行推进。", "jobRequirement": "1、硕士及以上学历，运筹学、工业工程、管理科学工程、计算机、应用数学等相关专业；\n2、熟悉运筹优化算法理论和应用，包括精确算法建模（MIP、列生成、分支定价等）及启发式算法；了解人工智能（深度学习、强化学习）相关算法；了解商业求解器（Gurobi,CPLEX,ORTOOLS至少一个）的使用；\n3、至少熟悉Python/Java/之一，有优化算法内核开发的经验；\n4、了解Hive/spark等大数据组件，能够使用SQL/HSQL进行数据分析，从数据中解读关键问题；\n5、英语阅读能力良好，可以理解paper进行复现；\n6、逻辑思维清晰，沟通能力强，对业界的数字化工作推进和前沿技术应用感兴趣，富有团队协作精神。", "positionCode": "S2026082501003"}, "employementCategory": 1, "recommend": 0}
