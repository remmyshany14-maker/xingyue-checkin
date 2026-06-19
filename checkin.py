import os
import re
import time
import random
import requests
import smtplib
import json
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
# REQUEST（自动重试）
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
# 签到
# ======================
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ======================
# 状态解析
# ======================
def parse_state(res):
    if not isinstance(res, dict):
        return "异常", "响应错误"

    if "error" in res:
        return "异常", res["error"]

    if res.get("code") == 5150 or "已签到" in str(res.get("status", "")):
        return "已签到", None

    return "未签到", res.get("status", "未知")


# ======================
# 邮件
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
# 可视化数据保存（3.0核心）
# ======================
def save_dashboard(results):
    os.makedirs("data", exist_ok=True)

    data = {
        "time": datetime.now().isoformat(),
        "results": results
    }

    with open("data/report.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ======================
# 邮件内容
# ======================
def build_email(results):
    success = sum(1 for r in results if r["state"] == "已签到")

    status = "全部成功" if success == len(results) else "部分失败"

    html = f"""
    <h1>🚀 {SITE_NAME}签到报告（3.0）</h1>
    <h2>状态：{status}</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <h3>📌 账号结果</h3>
    <ul>
    """

    for r in results:
        html += f"<li>{r['name']} → {r['state']}</li>"

    html += "</ul></body>"

    return html


# ======================
# 主流程
# ======================
def run():

    print("===== START 3.0 =====")

    results = []

    for token in TOKENS:

        res = checkin(token)

        state, reason = parse_state(res)

        results.append({
            "name": token[:10],
            "state": state,
            "reason": reason
        })

        time.sleep(random.uniform(1.5, 3.5))

    # ===== 邮件 =====
    html = build_email(results)

    title = f"{SITE_NAME}｜{'全部成功' if all(r['state']=='已签到' for r in results) else '部分失败'}"

    send_email(title, html)

    # ===== 可视化数据（核心新增）=====
    save_dashboard(results)

    print("DONE")


if __name__ == "__main__":
    run()
