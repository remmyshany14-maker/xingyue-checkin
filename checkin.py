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


# ======================
# CONFIG
# ======================
BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

RAW_TOKENS = os.getenv("SECRET_TOKENS", "")

TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", RAW_TOKENS)
    if t.strip()
]

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# TOKEN INFO（中文名 + uid）
# ======================
def parse_token_info(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)

        data = base64.urlsafe_b64decode(payload)
        obj = json.loads(data.decode())

        return {
            "uid": obj.get("uid", "unknown"),
            "name": obj.get("nickname") or f"UID-{obj.get('uid')}"
        }
    except:
        return {
            "uid": "unknown",
            "name": token[:6]
        }


# ======================
# REQUEST
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
# CHECKIN
# ======================
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# STATE
# ======================
def parse_state(res):
    if not isinstance(res, dict):
        return "UNKNOWN"

    if "error" in res:
        return "NETWORK_ERROR"

    code = res.get("code")
    status = res.get("status", "")

    if code == 5150 or "已签到" in status:
        return "ALREADY"

    if code == 200:
        return "SUCCESS"

    return "FAILED"


# ======================
# EMAIL
# ======================
def send_email(title, html):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        print("[EMAIL] missing config")
        return

    msg = MIMEText(html, "html", "utf-8")
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
# CORE ENGINE（终极关键）
# ======================
def run_checkin_for_token(token, max_retry=3):
    """
    ✔ 单 token 直到成功 / 已签到 / 或失败耗尽
    """
    for i in range(max_retry):
        res = checkin(token)
        state = parse_state(res)

        if state in ["SUCCESS", "ALREADY"]:
            return res, state

        time.sleep(2 + i)

    return res, "FAILED"


# ======================
# MAIN
# ======================
def run():
    print("===== ULTIMATE CHECKIN START =====")

    results = []

    success = 0
    already = 0
    failed = 0
    network = 0

    token_index = 0

    while token_index < len(TOKENS):

        token = TOKENS[token_index]

        # ✔ 防风控延迟
        time.sleep(random.uniform(1.5, 4.0))

        res, state = run_checkin_for_token(token)

        info = parse_token_info(token)

        print(info["name"], res)

        # ======================
        # 状态统计
        # ======================
        if state == "SUCCESS":
            success += 1
            token_index += 1

        elif state == "ALREADY":
            already += 1
            token_index += 1

        elif state == "FAILED":
            failed += 1
            token_index += 1  # ❗失败直接换 token

        else:
            network += 1
            token_index += 1

        results.append({
            "name": info["name"],
            "state": state
        })

    # ======================
    # REPORT
    # ======================
    html = f"""
    <html>
    <body style="font-family:Arial">

    <h2>🚀 签到终极日报</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <table border="1" cellpadding="8">
        <tr><th>账号</th><th>状态</th></tr>
    """

    color_map = {
        "SUCCESS": "green",
        "ALREADY": "blue",
        "FAILED": "red",
        "NETWORK_ERROR": "orange"
    }

    for r in results:
        html += f"""
        <tr>
            <td>{r['name']}</td>
            <td style="color:{color_map.get(r['state'],'black')}">{r['state']}</td>
        </tr>
        """

    html += f"""
    </table>

    <h3>📊 汇总</h3>
    <p>
    成功: {success} <br>
    已签到: {already} <br>
    失败: {failed} <br>
    网络异常: {network}
    </p>

    </body>
    </html>
    """

    # ======================
    # TITLE LOGIC
    # ======================
    total = len(TOKENS)

    if success == total:
        title = "✅ 全部签到成功"
    elif success + already == total:
        title = "🟡 全部已签到"
    elif success > 0:
        title = "🟠 部分成功"
    else:
        title = "❌ 签到失败"

    send_email(title, html)


if __name__ == "__main__":
    run()
