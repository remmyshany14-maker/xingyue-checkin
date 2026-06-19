import os
import time
import random
import json
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


# ✔ 支持 中文逗号 / 英文逗号 / 换行
TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", os.getenv("SECRET_TOKENS", ""))
    if t.strip()
]


EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# reward parser（安全版）
# ======================
def parse_reward(data):
    if not isinstance(data, dict):
        return 0, 0

    daily = data.get("daily_info", {}) or {}
    remaining = data.get("remaining_words", 0) or 0

    today_get = daily.get("daily_free", 0) or 0

    return today_get, remaining


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


def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# ✔ retry
# ======================
def checkin_retry(token, retries=3):
    last = None

    for i in range(retries):
        last = checkin(token)

        if last.get("code") in [200, 5150]:
            return last

        print(f"[RETRY] {token[:6]} attempt {i+1}")
        time.sleep(2 + i)

    return last


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []

    total_today = 0
    total_remaining = 0

    for token in TOKENS:
        time.sleep(random.uniform(2, 5))

        result = checkin_retry(token)

        print("CHECKIN:", result)

        code = result.get("code")

        if code == 200:
            state = "SUCCESS"
        elif code == 5150:
            state = "ALREADY"
        else:
            state = "FAILED"

        # ======================
        # ✔ 关键修复：不再用 status
        # ======================
        user_info = result.get("data", {}) or {}

        today, remaining = parse_reward(user_info)

        total_today += today
        total_remaining += remaining

        results.append({
            "token": token[:10],
            "state": state,
            "today": today,
            "remaining": remaining
        })

    # ======================
    # REPORT
    # ======================
    report = "签到日报\n\n"

    for r in results:
        report += (
            f"账号: {r['token']}\n"
            f"状态: {r['state']}\n"
            f"今日获得: {r['today']}\n"
            f"剩余字数: {r['remaining']}\n"
            "-------------------\n"
        )

    report += (
        f"\n====================\n"
        f"总计获得: {total_today}\n"
        f"总剩余: {total_remaining}"
    )

    print(report)

    # ======================
    # ✔ 邮件标题优化
    # ======================
    success = sum(1 for r in results if r["state"] == "SUCCESS")

    if success == len(results):
        title = "✅ 签到全部成功"
    elif success == 0:
        title = "❌ 签到全部失败"
    else:
        title = f"⚠️ 部分成功（{success}/{len(results)}）"

    send_email(title, report)


if __name__ == "__main__":
    run()
