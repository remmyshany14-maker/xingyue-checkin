import os
import time
import random
import re
import base64
import json
import requests
import smtplib
from datetime import datetime

from email.mime.text import MIMEText
from email.header import Header


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
# ⭐ 核心升级：真实用户名获取
# ======================
def get_user_name(token):
    """
    优先：/user/info
    兜底：JWT
    最后：token截断
    """

    # 1️⃣ 优先接口获取真实昵称
    try:
        r = requests.get(
            f"{BASE_URL}/user/info",
            headers={
                "Authorization": f"Bearer {token}",
                "Device": "web",
                "Platform": "web",
                "Bundle": "web",
                "Version": "5.1.0",
            },
            timeout=10
        )

        data = r.json()
        user = data.get("data") or {}

        name = (
            user.get("nickname")
            or user.get("username")
            or user.get("name")
        )

        if name:
            return name

    except:
        pass

    # 2️⃣ JWT fallback
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)

        obj = json.loads(base64.urlsafe_b64decode(part).decode())

        return (
            obj.get("nickname")
            or obj.get("name")
            or f"UID-{obj.get('uid')}"
        )

    except:
        pass

    # 3️⃣ 最终兜底
    return f"TOKEN-{token[:6]}"


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
# 状态标准化
# ======================
def parse_state(res):
    if not isinstance(res, dict):
        return "ERROR", "响应异常"

    if "error" in res:
        return "ERROR", res["error"]

    code = res.get("code")
    status = str(res.get("status", ""))

    if code == 5150 or "已签到" in status:
        return "CHECKED", None

    if code == 200:
        return "CHECKED", None

    return "NOT_CHECKED", status or "未知错误"


# ======================
# 邮件发送
# ======================
def send_email(title, html):
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(title, "utf-8")
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_bytes())
    server.quit()


# ======================
# HTML
# ======================
def build_email(results, failed_list, summary_text):
    html = f"""
    <html>
    <body style="font-family:Arial;background:#f5f5f5;padding:20px">

    <div style="background:#fff;padding:20px;border-radius:10px">

    <h1>🚀 {SITE_NAME}签到报告</h1>
    <h2>{summary_text}</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <h3>📌 账号状态</h3>
    <table border="1" cellpadding="8" width="100%">
        <tr>
            <th>账号</th>
            <th>状态</th>
        </tr>
    """

    color_map = {
        "CHECKED": "green",
        "NOT_CHECKED": "red",
        "ERROR": "orange"
    }

    for r in results:
        html += f"""
        <tr>
            <td>{r['name']}</td>
            <td style="color:{color_map[r['state']]};">{r['state_cn']}</td>
        </tr>
        """

    html += "</table>"

    # 失败原因
    if failed_list:
        html += "<h3>⚠️ 失败原因</h3><ul>"
        for f in failed_list:
            html += f"<li>{f['name']} → {f['reason']}</li>"
        html += "</ul>"

    html += "</div></body></html>"
    return html


# ======================
# MAIN
# ======================
def run():
    print("===== START =====")

    results = []
    failed_list = []

    checked = 0
    not_checked = 0
    error = 0

    for token in TOKENS:

        time.sleep(random.uniform(1.5, 3.5))

        res = checkin(token)
        state, reason = parse_state(res)

        # ⭐ 这里改了：不再用旧 parse_token_info
        name = get_user_name(token)

        if state == "CHECKED":
            state_cn = "已签到"
            checked += 1

        elif state == "NOT_CHECKED":
            state_cn = "未签到"
            not_checked += 1

        else:
            state_cn = "异常"
            error += 1
            failed_list.append({
                "name": name,
                "reason": reason
            })

        results.append({
            "name": name,
            "state": state,
            "state_cn": state_cn
        })

    total = len(TOKENS)

    summary_text = f"已签到 {checked} | 未签到 {not_checked} | 异常 {error}"

    if checked == total:
        title = f"{SITE_NAME}｜全部账号已签到"
    elif checked + not_checked == total:
        title = f"{SITE_NAME}｜部分账号未签到"
    else:
        title = f"{SITE_NAME}｜签到异常"

    html = build_email(results, failed_list, summary_text)

    send_email(title, html)

    print(summary_text)


if __name__ == "__main__":
    run()
