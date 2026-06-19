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
# TOKEN NAME（可选：从token推UID）
# ======================
def get_token_name(token):
    try:
        import base64, json

        part = token.split(".")[1]
        pad = "=" * (-len(part) % 4)
        data = base64.urlsafe_b64decode(part + pad)
        payload = json.loads(data.decode())

        return f"UID-{payload.get('uid', 'unknown')}"

    except:
        return f"TOKEN-{token[:6]}"


# ======================
# REQUEST (带重试机制)
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

    last_err = None

    for i in range(retry):
        try:
            r = requests.post(url, headers=headers, json=payload or {}, timeout=15)
            return r.json()

        except Exception as e:
            last_err = str(e)
            time.sleep(2 + i)

    return {"code": -1, "error": last_err or "unknown"}


# ======================
# CHECKIN（带签到级重试）
# ======================
def checkin(token):
    for i in range(2):  # ✔ 签到级重试
        result = request_post(
            f"{BASE_URL}/forum/checkin",
            token,
            {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
        )

        # ✔ 成功或已签到就不重试
        if result.get("code") in [200, 5150] or "已签到" in str(result):
            return result

        time.sleep(1 + i)

    return result


# ======================
# STATE PARSER
# ======================
def parse_state(result):
    if not isinstance(result, dict):
        return "UNKNOWN"

    if "error" in result:
        return "UNKNOWN"

    code = result.get("code")
    status_text = result.get("status", "")

    if code == 5150 or "已签到" in status_text:
        return "ALREADY"

    if code == 200:
        return "SUCCESS"

    return "FAILED"


# ======================
# EMAIL
# ======================
def send_email(title, content):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        print("[EMAIL] missing config")
        return

    msg = MIMEText(content, "html", "utf-8")
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
# HTML REPORT（美化重点）
# ======================
def build_report(results, summary):
    html = f"""
    <html>
    <body style="font-family:Arial">

    <h2>📌 签到日报 {datetime.now().strftime('%Y-%m-%d')}</h2>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr>
            <th>账号</th>
            <th>状态</th>
        </tr>
    """

    for r in results:
        color = {
            "SUCCESS": "green",
            "ALREADY": "blue",
            "FAILED": "red",
            "UNKNOWN": "orange"
        }.get(r["state"], "black")

        html += f"""
        <tr>
            <td>{r['name']}</td>
            <td style="color:{color}">{r['state']}</td>
        </tr>
        """

    html += f"""
    </table>

    <h3>📊 汇总</h3>
    <p>{summary}</p>

    </body>
    </html>
    """

    return html


# ======================
# MAIN
# ======================
def run():
    print("===== START CHECKIN =====")

    results = []

    success = 0
    already = 0
    failed = 0
    unknown = 0

    for token in TOKENS:

        time.sleep(random.uniform(1.5, 4.5))

        result = checkin(token)
        state = parse_state(result)

        name = get_token_name(token)

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
            "name": name,
            "state": state
        })

    summary = (
        f"成功: {success} | "
        f"已签到: {already} | "
        f"失败: {failed} | "
        f"异常: {unknown}"
    )

    print(summary)

    # ✔ 邮件标题
    total = len(TOKENS)

    if success == total:
        title = "✅ 全部账号签到成功"
    elif success + already == total:
        title = "🟡 全部账号已签到"
    elif success > 0:
        title = "🟠 部分账号成功"
    else:
        title = "❌ 签到失败"

    html = build_report(results, summary)
    send_email(title, html)


if __name__ == "__main__":
    run()
