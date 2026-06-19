import os
import time
import random
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText


# ======================
# config
# ======================
BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

TOKENS = [t.strip() for t in os.getenv("SECRET_TOKENS", "").split(",") if t.strip()]

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# reward parser
# ======================
def parse_reward(user_info):
    daily = user_info.get("daily_info", {})
    remaining = user_info.get("remaining_words", 0)

    today_get = daily.get("daily_free", 0)

    return today_get, remaining


# ======================
# email
# ======================
def send_email(title, content):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        print("[EMAIL] missing config")
        return

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = title
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
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


def check_status(token):
    return request_post(f"{BASE_URL}/forum/checkin/status", token)


def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# main
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []
    total_today = 0
    total_remaining = 0

    for token in TOKENS:
        time.sleep(random.uniform(2, 6))

        status = check_status(token)
        result = checkin(token)

        print("STATUS:", status)
        print("CHECKIN:", result)

        state = "FAILED"

        if result.get("code") == 200:
            state = "SUCCESS"
        elif result.get("code") == 5150:
            state = "ALREADY"

        # ===== reward parse =====
        user_info = status.get("data", {}).get("userInfo", {}) or {}

        today_get, remaining = parse_reward(user_info)

        total_today += today_get
        total_remaining += remaining

        results.append({
            "token": token[:10],
            "state": state,
            "today": today_get,
            "remaining": remaining
        })

    # ======================
    # report
    # ======================
    summary = "签到日报\n\n"

    for r in results:
        summary += (
            f"账号: {r['token']}\n"
            f"状态: {r['state']}\n"
            f"今日获得: {r['today']}\n"
            f"剩余字数: {r['remaining']}\n"
            "-------------------\n"
        )

    summary += f"\n====================\n总计获得: {total_today}\n总剩余: {total_remaining}"

    print(summary)

    send_email(
        f"签到日报 {datetime.now().strftime('%Y-%m-%d')}",
        summary
    )


if __name__ == "__main__":
    run()
