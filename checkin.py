import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header

TOKEN = os.getenv("SECRET_TOKEN")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


def send_email(title, content):
    if not EMAIL_USER or not EMAIL_PASS or not EMAIL_TO:
        print("邮件配置不完整，跳过邮件通知")
        return

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header(title, "utf-8")
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
        smtp.quit()
        print("邮件发送成功")
    except Exception as e:
        print("邮件发送失败:", e)


def checkin():
    url = "https://c.xingyuexiezuo.com/api/v1/forum/checkin"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json"
    }

    data = {
        "data": "RUTjr2nDiRda1I+NCO3FqQ=="
    }

    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        result = res.json()
        print("签到结果:", result)

        status = result.get("status", "")

        if "成功" in status or result.get("code") == 200:
            send_email("签到成功", str(result))
        elif "已签到" in status:
            send_email("今日已签到", str(result))
        else:
            send_email("签到失败", str(result))

    except Exception as e:
        send_email("签到异常", str(e))
        print("错误:", e)


if __name__ == "__main__":
    checkin()
