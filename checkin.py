import os
import requests
import smtplib
from email.mime.text import MIMEText

TOKEN = os.getenv("SECRET_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


def send_mail(title, content):
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
    server.quit()


headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Device": "web",
    "Platform": "web",
    "Bundle": "web",
    "Version": "5.1.0",
    "Content-Type": "application/json"
}

# 1. 签到
r = requests.post(
    "https://c.xingyuexiezuo.com/api/v1/forum/checkin",
    headers=headers,
    json={"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
)

result = r.json()
print("签到结果：", result)

# 2. 邮件通知
if result.get("code") == 200:
    send_mail("签到成功", str(result))
else:
    send_mail("签到失败", str(result))
