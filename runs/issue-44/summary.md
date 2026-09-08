# Crawl result

- Adapter: `generic-browser`
- Source: https://xyz.51job.com/external/apply.aspx?jobid=172701148&ctmid=8990710
- Jobs: **0**
- Warnings: **2**

| # | 岗位 | 地点 | 职能/部门 | 链接 |
|---:|---|---|---|---|

## Warnings
- browser final_url=https://young.yingjiesheng.com/xyzlogin?ctmid=2a0e10a7-19b8-4fc2-a939-ae56bacddbef&ehirejobid=172701148&jumpurl=https%3A%2F%2Fxyz.51job.com%2FExternal%2FOthers%2FLogin51.aspx%3FJobID%3D9fe89914-738c-4183-afec-8c0692a95b32%26CtmID%3D2a0e10a7-19b8-4fc2-a939-ae56bacddbef%26EhireJobID%3D172701148%26prd%3D%26prp%3D%26cd%3D%26cp%3D%26ruid%3D%26backurl%3D%26auid%3D%26uuid%3D%26partner%3D; quality=0/0 informative; body_sample=应届生求职登录
获取验证码
我已阅读并同意应届生求职 用户协议 和 隐私条款
登录
使用前程无忧账号登录
推荐使用：1280*1024 分辨率的浏览器
- browser API trace:
200 POST https://vapi.51job.com/open.php?module=initgeetest&version=400&clientid=000017 | post={"sign":"1e00979e161611a6f6f719edde2948ce","data":"{\"digestmod\":\"md5\"}"} | dict keys=['status', 'message', 'resultbody']; resultbody:dict(['success', 'gt', 'challenge', 'new_captcha'])
200 POST https://cupid.51job.com/open/noauth/customization/xyz/config/login?api_key=51job&timestamp=1788846382 | post={"ctmId":"2a0e10a7-19b8-4fc2-a939-ae56bacddbef","jobId":"172701148"} | dict keys=['status', 'message', 'resultbody']; resultbody:dict(['imageUrl', 'logoUrl', 'imageUrlPc', 'logoUrlPc', 'color', 'goto51Login', 'isNewEhireplus', 'businessType', 'whiteList', 'defaultWebLogoUrl'])
