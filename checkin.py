import os
import time
import random
import json
import base64
import re
import requests
import smtplib
from datetime import datetime

from email.mime.text import MIMEText
from email.header import Header

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


# ======================
# CONFIG
# ======================
BASE_URL = "https://c.xingyuexiezuo.com/api/v1"


# ✔ 修复：支持中文逗号 / 换行 / 英文逗号
TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", os.getenv("SECRET_TOKENS", ""))
    if t.strip()
]


EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# AES 解密
# ======================
KEY = b"chloefuckityoall"
IV = b"9311019310287172"


def decrypt(encoded: str):
    try:
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        raw = base64.b64decode(encoded)
        decrypted = unpad(cipher.decrypt(raw), 16)
        return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        print("[DECRYPT ERROR]", e)
        return {}


# ======================
# reward parser
# ======================
def parse_reward(user_info):
    daily = user_info.get("daily_info", {})
    remaining = user_info.get("remaining_words", 0)
    today_get = daily.get("daily_free", 0)
    return today_get, remaining


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

        server.sendmail(
            EMAIL_USER,
            [EMAIL_TO],
            msg.as_bytes()
        )

        server.quit()
        print("[EMAIL] sent")

    except Exception as e:
        print("[EMAIL ERROR]", e)


# ======================
# request
# ======================
def request_post(url, token, payload=None):
    token = str(token).strip()

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
# ✔ 重试签到（关键）
# ======================
def checkin_with_retry(token, retries=3):
    for i in range(retries):
        result = checkin(token)

        if result.get("code") in [200, 5150]:
            return result

        print(f"[RETRY] {token[:6]} attempt {i+1}")
        time.sleep(2 + i)

    return result


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []
    total_today = 0
    total_remaining = 0

    for token in TOKENS:
        time.sleep(random.uniform(2, 6))

        status = check_status(token)
        result = checkin_with_retry(token)

        print("STATUS:", status)
        print("CHECKIN:", result)

        if result.get("code") == -1:
            print("[SKIP] request failed")
            continue

        state = "FAILED"
        if result.get("code") == 200:
            state = "SUCCESS"
        elif result.get("code") == 5150:
            state = "ALREADY"

        # ======================
        # decode reward
        # ======================
        user_info = {}
        encoded = status.get("data", {}).get("encoded")

        if encoded:
            user_info = decrypt(encoded)

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
    # REPORT
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

    summary += (
        f"\n====================\n"
        f"总计获得: {total_today}\n"
        f"总剩余: {total_remaining}"
    )

    print(summary)

    # ======================
    # ✔ 邮件标题智能化
    # ======================
    success_count = sum(1 for r in results if r["state"] == "SUCCESS")

    if success_count == len(results):
        title = "✅ 签到全部成功"
    elif success_count == 0:
        title = "❌ 签到全部失败"
    else:
        title = f"⚠️ 部分成功（{success_count}/{len(results)}）"

    send_email(title, summary)


if __name__ == "__main__":
    run()
