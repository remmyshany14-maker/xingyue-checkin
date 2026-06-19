import os
import time
import random
import re
import json
import base64
import requests
import smtplib
from datetime import datetime

from Crypto.Cipher import AES
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
# AES decrypt
# ======================
def decrypt_encoded(encoded: str):
    try:
        key = b"chloefuckityoall"
        iv = b"9311019310287172"

        cipher = AES.new(key, AES.MODE_CBC, iv)

        raw = base64.b64decode(encoded)
        decrypted = cipher.decrypt(raw)

        pad = decrypted[-1]
        decrypted = decrypted[:-pad]

        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


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


def status(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json",

        # ✔ 模拟浏览器（关键修复点）
        "Referer": "https://c.xingyuexiezuo.com/",
        "Origin": "https://c.xingyuexiezuo.com",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.post(
            f"{BASE_URL}/forum/checkin/status",
            headers=headers,
            json={},
            timeout=15
        )
        return r.json()
    except Exception as e:
        return {"code": -1, "error": str(e)}


# ======================
# ✔ 核心修复（奖励解析）
# ======================
def parse_reward(status_result):
    data = status_result.get("data", {}) or {}

    encoded = data.get("encoded")
    if not encoded:
        return 0, 0

    decoded = decrypt_encoded(encoded)

    # ✔ 双层兼容（关键修复点）
    user_info = (
        decoded.get("userInfo")
        or decoded.get("data", {}).get("userInfo", {})
    )

    if not user_info:
        return 0, 0

    daily = user_info.get("daily_info", {})
    today = daily.get("daily_free", 0)

    remaining = user_info.get("remaining_words", 0)

    return today, remaining


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
    except Exception as e:
        print("[EMAIL ERROR]", e)


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []
    total_today = 0
    total_remaining = 0

    for token in TOKENS:

        # ✔ 防风控：轻微随机延迟
        time.sleep(random.uniform(1.5, 4.5))

        # ✔ 先执行签到
        ck = checkin(token)

        # ✔ 再取状态（真正奖励来源）
        st = status(token)

        print("RAW STATUS:", json.dumps(st, ensure_ascii=False, indent=2))

        print("CHECKIN:", ck)
        print("STATUS:", st)

        code = ck.get("code")

        if code == 200:
            state = "SUCCESS"
        elif code == 5150:
            state = "ALREADY"
        else:
            state = "FAILED"

        today, remaining = parse_reward(st)

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

    success = sum(1 for r in results if r["state"] == "SUCCESS")
    title = f"签到完成 {success}/{len(results)}"

    send_email(title, report)


if __name__ == "__main__":
    run()
