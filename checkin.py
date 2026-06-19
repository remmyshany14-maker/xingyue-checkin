import requests
import os
import json

TOKEN = os.environ.get("TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Device": "web",
    "Platform": "web",
    "Bundle": "web",
    "Version": "5.1.0",
    "Content-Type": "application/json"
}

# 1. 签到
res = requests.post(
    "https://c.xingyuexiezuo.com/api/v1/forum/checkin",
    headers=headers,
    json={"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
)

data = res.json()
print("签到结果：", data)

# 2. 判断状态
status = data.get("status", "")

if "成功" in status or data.get("code") == 200:
    result = "签到成功"
elif "已签到" in status:
    result = "今日已签到"
else:
    result = "签到失败"

print("最终状态：", result)
