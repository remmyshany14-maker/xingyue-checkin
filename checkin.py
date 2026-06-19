import os
import re
import time
import random
import requests
import smtplib
import json
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header


# ======================
# CONFIG
# ======================
BASE_URL = "https://c.xingyuexiezuo.com/api/v1"
SITE_NAME = "星月"

TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", os.getenv("SECRET_TOKENS", ""))
    if t.strip()
]

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# TOKEN解析（昵称优先）
# ======================
def parse_token_info(token):
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        obj = json.loads(base64.urlsafe_b64decode(part).decode())

        return {
            "uid": obj.get("uid"),
            "name": obj.get("nickname") or f"UID-{obj.get('uid')}"
        }
    except:
        return {
            "uid": None,
            "name": token[:8]
        }


# ======================
# HTTP请求（带重试）
# ======================
def request_post(url, token, data=None, retry=3):
    for i in range(retry):
        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Device": "web",
                    "Platform": "web",
                    "Version": "5.1.0"
                },
                json=data or {},
                timeout=10
            )
            return r.json()

        except Exception as e:
            time.sleep(2 ** i + random.uniform(0.5, 1.5))

    return {"code": -1, "error": "network_failed"}


# ======================
# 签到接口
# ======================
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# 状态解析（统一标准）
# ======================
def parse_state(res):
    if not isinstance(res, dict):
        return "异常", "响应异常"

    if "error" in res:
        return "异常", res["error"]

    if res.get("code") == 5150 or "已签到" in str(res.get("status", "")):
        return "已签到", None

    return "未签到", res.get("status", "未知错误")


# ======================
# retry层（自愈核心）
# ======================
def retry_checkin(token, max_retry=3):
    last_error = None

    for i in range(max_retry):
        res = checkin(token)
        state, reason = parse_state(res)

        if state in ["已签到", "未签到"]:
            return res, state, reason

        last_error = reason
        time.sleep(2 + i)

    return {"code": -1, "error": str(last_error)}, "异常", last_error


# ======================
# 邮件发送
# ======================
def send_email(title, html):
    try:
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = Header(title, "utf-8")
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO

        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
        server.quit()

        print("[EMAIL] sent")

    except Exception as e:
        print("[EMAIL ERROR]", repr(e))


# ======================
# 邮件内容（排序优化）
# ======================
def build_email(results):
    ok = sum(1 for r in results if r["state"] == "已签到")
    fail = sum(1 for r in results if r["state"] == "未签到")
    err = sum(1 for r in results if r["state"] == "异常")

    status = "全部成功" if ok == len(results) else "部分失败"

    html = f"""
    <html>
    <body style="font-family:Arial;background:#f6f6f6;padding:20px">
    <div style="background:white;padding:20px;border-radius:10px">

    <h1>🚀 {SITE_NAME}签到报告</h1>
    <h2>状态：{status}</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <h3>📌 汇总</h3>
    <p>已签到：{ok} ｜ 未签到：{fail} ｜ 异常：{err}</p>

    <h3>📌 账号状态</h3>
    <ul>
    """

    for r in results:
        html += f"<li><b>{r['name']}</b> → {r['state']}</li>"

    html += "</ul></div></body></html>"

    return html


# ======================
# 主流程
# ======================
def run():
    print("===== START 3.0 =====")

    results = []
    checked_today = set()

    for token in TOKENS:

        info = parse_token_info(token)

        # 防重复（幂等）
        if info["uid"] in checked_today:
            print(f"[SKIP] {info['name']}")
            continue
        checked_today.add(info["uid"])

        # retry签到
        res, state, reason = retry_checkin(token)

        results.append({
            "name": info["name"],
            "state": state,
            "reason": reason
        })

        time.sleep(random.uniform(1.5, 3.5))

    # 邮件标题
    if all(r["state"] == "已签到" for r in results):
        title = f"{SITE_NAME}｜全部账号签到成功"
    elif any(r["state"] == "异常" for r in results):
        title = f"{SITE_NAME}｜签到异常"
    else:
        title = f"{SITE_NAME}｜部分账号未签到"

    html = build_email(results)
    send_email(title, html)

    print("DONE")


if __name__ == "__main__":
    run()
