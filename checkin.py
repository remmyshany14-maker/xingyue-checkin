import os
import time
import random
import re
import requests
import smtplib
from datetime import datetime

from email.mime.text import MIMEText
from email.header import Header


# ======================
# CONFIG
# ======================
BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", os.getenv("SECRET_TOKENS", ""))
    if t.strip()
]

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# request
# ======================
def request_post(url, token, payload=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, headers=headers, json=payload or {}, timeout=15)
        return r.json()
    except Exception as e:
        return {"code": -1, "error": str(e)}


# ======================
# checkin
# ======================
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# 状态判断修复（重点）
# ======================
def parse_state(result):
    code = result.get("code")

    status_text = result.get("status", "")

    # ✔ 已签到（关键修复点）
    if code == 5150 or "已签到" in status_text:
        return "ALREADY"

    # ✔ 成功签到
    if code == 200:
        return "SUCCESS"

    # ❌ 真实失败
    return "FAILED"


# ======================
# email
# ======================
def send_email(title, content):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        print("[EMAIL] missing config")
        return

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header(title, "utf-8")
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_bytes())
        server.quit()
        print("[EMAIL] sent")
    except Exception as e:
        print("[EMAIL ERROR]", e)


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []

    success = 0
    already = 0
    failed = 0

    for token in TOKENS:

        # ✔ 轻微随机延迟
        time.sleep(random.uniform(1.5, 4.5))

        result = checkin(token)

        print("CHECKIN:", result)

        state = parse_state(result)

        if state == "SUCCESS":
            success += 1
        elif state == "ALREADY":
            already += 1
        else:
            failed += 1

        results.append({
            "token": token[:10],
            "state": state
        })

    # ======================
    # REPORT
    # ======================
    report = "签到日报\n\n"

    for r in results:
        report += (
            f"账号: {r['token']}\n"
            f"状态: {r['state']}\n"
            "-------------------\n"
        )

    report += (
        f"\n====================\n"
        f"成功: {success}\n"
        f"已签到: {already}\n"
        f"失败: {failed}\n"
    )

    print(report)

    # ======================
    # 邮件标题逻辑（你要的）
    # ======================
    total = len(TOKENS)

    if success == total:
        title = "✅ 签到成功（全部完成）"
    elif success + already == total:
        title = "🟡 签到完成（全部已签到）"
    elif success > 0:
        title = "🟠 签到部分成功"
    else:
        title = "❌ 签到失败"

    send_email(title, report)


if __name__ == "__main__":
    run()
