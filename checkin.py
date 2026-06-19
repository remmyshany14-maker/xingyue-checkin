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
# REQUEST (带重试)
# ======================
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
            r = requests.post(
                url,
                headers=headers,
                json=payload or {},
                timeout=15
            )
            return r.json()

        except Exception as e:
            print(f"[WARN] retry {i+1}: {e}")
            time.sleep(2 + i)

    return {"code": -1, "error": "timeout_failed"}


# ======================
# CHECKIN
# ======================
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# 状态判断（修复核心）
# ======================
def parse_state(result):
    if not isinstance(result, dict):
        return "UNKNOWN"

    if "error" in result:
        return "UNKNOWN"

    code = result.get("code")
    status_text = result.get("status", "")

    # ✔ 已签到
    if code == 5150 or "已签到" in status_text:
        return "ALREADY"

    # ✔ 成功签到
    if code == 200:
        return "SUCCESS"

    # ❌ 其他失败
    return "FAILED"


# ======================
# EMAIL
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
        server.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
        server.quit()
        print("[EMAIL] sent")
    except Exception as e:
        print("[EMAIL ERROR]", e)


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    success = 0
    already = 0
    failed = 0
    unknown = 0

    results = []

    for token in TOKENS:

        # ✔ 防止风控轻延迟
        time.sleep(random.uniform(1.5, 4.5))

        result = checkin(token)
        state = parse_state(result)

        print("CHECKIN:", result)

        if state == "SUCCESS":
            success += 1
        elif state == "ALREADY":
            already += 1
        elif state == "FAILED":
            failed += 1
        else:
            unknown += 1

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
        f"异常: {unknown}\n"
    )

    print(report)

    # ======================
    # EMAIL TITLE LOGIC
    # ======================
    total = len(TOKENS)

    if success == total:
        title = "✅ 全部账号签到成功"
    elif success + already == total:
        title = "🟡 全部账号已签到"
    elif success > 0:
        title = "🟠 部分账号签到成功"
    else:
        title = "❌ 签到失败"

    send_email(title, report)


if __name__ == "__main__":
    run()
