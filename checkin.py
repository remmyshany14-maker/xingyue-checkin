import os
import requests
from datetime import datetime

BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

TOKEN = os.environ["SECRET_TOKEN"]

def send_email(subject, content):
    # 使用 GitHub Actions 环境变量发送邮件
    import smtplib
    from email.mime.text import MIMEText

    smtp_server = "smtp.qq.com"
    smtp_port = 587

    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    to = os.environ["EMAIL_TO"]

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())
        server.quit()
    except Exception as e:
        print("邮件发送失败:", e)


def checkin_status():
    url = f"{BASE_URL}/forum/checkin/status"
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    return requests.get(url, headers=headers).json()


def checkin():
    url = f"{BASE_URL}/forum/checkin"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json"
    }
    data = {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}

    return requests.post(url, json=data, headers=headers).json()


def main():
    status = checkin_status()

    print("状态：", status)

    if status.get("code") == 200 and status.get("status") == "Success":
        result = checkin()
    else:
        result = status

    print("签到结果：", result)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = "星月写作签到结果"
    content = f"""
时间：{now}

返回结果：
{result}
"""

    send_email(subject, content)


if __name__ == "__main__":
    main()
