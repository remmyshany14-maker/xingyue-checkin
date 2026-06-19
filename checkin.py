import os
import json
import time
import requests
from datetime import datetime
from email.mime.text import MIMEText
import smtplib

BASE_URL = "https://c.xingyuexiezuo.com/api/v1"


# ========== 账号 ==========
TOKENS = os.getenv("SECRET_TOKENS", "").split(",")


# ========== 邮件 ==========
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ========== 工具 ==========
def request_post(url, token, payload=None, retry=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json"
    }

    for i in range(retry):
        try:
            r = requests.post(url, headers=headers, json=payload or {})
            return r.json()
        except Exception as e:
            if i == retry - 1:
                return {"code": -1, "msg": str(e)}
            time.sleep(2)


def checkin(token):
    url = f"{BASE_URL}/forum/checkin"
    return request_post(url, token, {"data": "RUTjr2nDiRda1I+NCO3FqQ=="})


def get_status(token):
    url = f"{BASE_URL}/forum/checkin/status"
    return request_post(url, token)


# ========== 邮件 ==========
def send_email(html):
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = "每日签到日报"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
    server.quit()


# ========== 主逻辑 ==========
def run():
    report = []
    success = 0

    for idx, token in enumerate([t.strip() for t in TOKENS if t.strip()], 1):

        status = get_status(token)
        result = checkin(token)

        item = {
            "账号": idx,
            "status": status,
            "checkin": result
        }

        if result.get("code") == 200:
            success += 1
            item["result"] = "✅ 成功"
        elif result.get("code") == 5150:
            item["result"] = "⚠️ 已签到"
        else:
            item["result"] = "❌ 失败"

        report.append(item)

    html = build_html(report, success)
    print(html)

    if EMAIL_USER:
        send_email(html)


def build_html(report, success):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = ""
    for r in report:
        rows += f"""
        <tr>
            <td>{r['账号']}</td>
            <td>{r['result']}</td>
            <td><pre>{json.dumps(r['status'], ensure_ascii=False)}</pre></td>
        </tr>
        """

    return f"""
    <h2>每日签到报告</h2>
    <p>时间：{now}</p>
    <p>成功账号：{success}/{len(report)}</p>
    <table border="1" cellspacing="0" cellpadding="5">
        <tr>
            <th>账号</th>
            <th>结果</th>
            <th>状态</th>
        </tr>
        {rows}
    </table>
    """


if __name__ == "__main__":
    run()
