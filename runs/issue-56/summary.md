# Crawl result

- Adapter: `generic-browser`
- Source: https://inspur.hcmcloud.cn/recruit#/portal_job_list?job_class=_HB5_Y2FtcHVz&filter_dict=_HB5_eyJf!m9iX2NsYXNzIjoiY2FtcHVzIiwic2VsZWN0X2RlcGFydCI6bnVsbH0%253D
- Jobs: **1**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|
| 1 | 浪潮 |  |  | [详情](https://inspur.hcmcloud.cn/recruit#/portal_job_list?job_class=_HB5_Y2FtcHVz&filter_dict=_HB5_eyJf!m9iX2NsYXNzIjoiY2FtcHVzIiwic2VsZWN0X2RlcGFydCI6bnVsbH0%253D#job=8) |

## Warnings
- browser final_url=https://inspur.hcmcloud.cn/recruit#/portal_job_list?job_class=_HB5_Y2FtcHVz&filter_dict=_HB5_eyJf!m9iX2NsYXNzIjoiY2FtcHVzIiwic2VsZWN0X2RlcGFydCI6bnVsbH0%253D; quality=0/1 informative; body_sample=温馨提示
亲爱的伙伴：
您好，感谢您对浪潮集团的关注。请您关注【浪潮招聘】公众号，后续面试安排等重要消息均将第一时间通过公众号通知。
如有其他问题，可发送邮件至inspurhr@inspur.com，我们将第一时间处理。
以上，祝您一切顺利！
我已阅读并同意
- browser API trace:
200 GET https://inspur.hcmcloud.cn/log/pagerecord?fromstate=&tostate=portal_job&params={%22job_class%22:%22campus%22,%22filter_dict%22:%22{\%22_job_class\%22:\%22campus\%22,\%22select_depart\%22:null}%22}&company_id=8&device_resolution=1440*1000 | post=- | dict keys=['success']
200 GET https://inspur.hcmcloud.cn/api/auth/get_auth?app_type=recruit&v=0.67691202945689131789350922183&hcm_transfer_strategy=ha5 | post=- | dict keys=['user', 'employee', 'entry', 'candidate', 'company', 'public_account', 'manager_departs', 'origin_departs', 'roles', 'in_white_list', 'wx_user', 'jobs', 'is_sys_manager', 'sso', 'company_setting', 'bind_info', 'app_type', 'developer_mode', 'developer_mode_workspace_only', 'developer_temp']; company:dict(['id', 'name', 'special_title', 'theme_color'])
200 GET https://inspur.hcmcloud.cn/api/language/get_language?lang=zh_cn | post=- | dict keys=['serial_number', 'my_analysis', '100002', 'bill_define', 'business_define', 'bill_name', 'business', 'resume_template_name', 'notification_message', 'bill_search_info', 'bill_inst_title', 'set_subprocess', 'automatically_skip', 'send_message_after_approve', 'process_approval_setting', 'yes', 'no', 'edit', 'delete', 'check_view']
200 POST https://inspur.hcmcloud.cn/api/recruit.job.class.setting.list | post={"hcm_transfer_strategy":"ha5","hcm_param":"tp3cCf0R3zY9qBWw9shL2MmyCAsX3EaCqvlLtId2CZOSD7zEx3VT0Pl76o3TYJfDIrH"} | dict keys=['hcm_transfer_strategy', 'hcm_param']
200 POST https://inspur.hcmcloud.cn/api/recruit.get.company.info | post={"hcm_transfer_strategy":"ha5","hcm_param":"ugjOp46pjQxsUbyIolbOHpW9r0m2n6qnoHkKlq3oF4c3mIYE98u1dYrcb2fOvAS6Mrdl7xyKHng1tQWEBoqUfH2qEd9+gm/myfKNvO0ecGFz7DBxirJB0z6mW8yCcIsU7TN"} | dict keys=['hcm_transfer_strategy', 'hcm_param']
200 POST https://inspur.hcmcloud.cn/api/recruit.get.dept.template.info | post={"hcm_transfer_strategy":"ha5","hcm_param":"hck8a272bGj!DOnxm!TSgWNdL/m!/f/sqd!z76NB90vOlWSQVJ8Bs6PiSIoM38pmRhYyBO74IVjelZfRPpkqxEFYrNhXFzCsXw70dUmTNenuQOiMRHdrpQeXYKcqUewZ/D291dkSHRHzOzh/EwrYd3Y6EDNE1eCKEaqEstDrjzUw/rHCCF/IH3WIxoRT23sebzkDt+vACwoL6fasUSFByR!9aRO0Zpx0OllOYQtnNHzfGw="} | dict keys=['hcm_transfer_strategy', 'hcm_param']
200 POST https://inspur.hcmcloud.cn/api/get_template | post={"hcm_transfer_strategy":"ha5","hcm_param":"qbnNJWqM8U9sA2JMlN2uHULC1kqjvg/n2/qpHyxLv9gwRNmkdOxmKbrFzlNQ910FEcowiNGZJPt4oRsrzQ!sJ2XDQ=="} | dict keys=['hcm_transfer_strategy', 'hcm_param']
200 POST https://inspur.hcmcloud.cn/api/hcm.ai.get.robot | post={"hcm_transfer_strategy":"ha5","hcm_param":"2q96FtCZbO7i18a68l4KCyXJXCX9A8VHEbnoafNaO7qYQw="} | dict keys=['hcm_transfer_strategy', 'hcm_param']
