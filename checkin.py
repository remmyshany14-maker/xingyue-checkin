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


# ======================
# TOKEN加载
# ======================
TOKENS = [
    t.strip()
    for t in re.split(r"[,\n，]+", os.getenv("SECRET_TOKENS", ""))
    if t.strip()
]


EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


# ======================
# TOKEN自愈管理器（核心）
# ======================
class TokenManager:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.bad_tokens = set()

    def get_token(self):
        if not self.tokens:
            return None

        # 找可用token
        for _ in range(len(self.tokens)):
            token = self.tokens[self.index % len(self.tokens)]
            self.index += 1

            if token not in self.bad_tokens:
                return token

        return None

    def mark_bad(self, token):
        print(f"[TOKEN BAD] {token[:10]}")
        self.bad_tokens.add(token)


# ======================
# 获取用户名（稳定版）
# ======================
def get_user_name(token):
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

        return (
            user.get("nickname")
            or user.get("username")
            or user.get("name")
            or f"TOKEN-{token[:6]}"
        )

    except:
        return f"TOKEN-{token[:6]}"


# ======================
# 自愈请求（重试+退避）
# ======================
def request_with_retry(url, token, payload=None, max_retry=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",
        "Content-Type": "application/json"
    }

    for i in range(max_retry):
        try:
            r = requests.post(
                url,
                headers=headers,
                json=payload or {},
                timeout=10
            )
            return r.json()

        except Exception as e:
            wait = 2 ** i + random.uniform(0, 1)
            print(f"[RETRY {i+1}] {e} wait={wait:.1f}s")
            time.sleep(wait)

    return {"code": -1, "error": "network_failed"}


# ======================
# 状态解析
# ======================
def parse_state(res):
    if not isinstance(res, dict):
        return "ERROR", "响应异常"

    if "error" in res:
        return "ERROR", res["error"]

    code = res.get("code", 0)
    status = str(res.get("status", ""))

    if code == 5150 or "已签到" in status:
        return "CHECKED", None

    if code == 200:
        return "CHECKED", None

    return "NOT_CHECKED", status or "未知错误"


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
# HTML报告（重点排序）
# ======================
def build_email(results, failed, summary):
    html = f"""
    <html>
    <body style="font-family:Arial;background:#f5f5f5;padding:20px">

    <div style="background:#fff;padding:20px;border-radius:10px">

    <h1>🚀 {SITE_NAME} 自愈签到报告</h1>
    <h2>{summary}</h2>
    <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

    <h3>📌 签到结果</h3>
    <ul>
    """

    for r in results:
        html += f"<li>{r['name']} → {r['state']}</li>"

    html += "</ul>"

    if failed:
        html += "<h3>⚠️ 异常详情</h3><ul>"
        for f in failed:
            html += f"<li>{f['name']} → {f['reason']}</li>"
        html += "</ul>"

    html += "</div></body></html>"
    return html


# ======================
# 主流程（自愈核心）
# ======================
def run():
    print("===== SELF HEAL START =====")

    manager = TokenManager(TOKENS)

    results = []
    failed = []

    checked = 0
    error = 0

    for _ in range(len(TOKENS)):

        token = manager.get_token()
        if not token:
            break

        res = request_with_retry(
            f"{BASE_URL}/forum/checkin",
            token,
            {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
        )

        # token失效
        if res.get("code") in [-1, 401, 403]:
            manager.mark_bad(token)
            continue

        state, reason = parse_state(res)
        name = get_user_name(token)

        if state == "CHECKED":
            checked += 1
            state_cn = "已签到"

        elif state == "NOT_CHECKED":
            state_cn = "未签到"

        else:
            state_cn = "异常"
            error += 1
            failed.append({
                "name": name,
                "reason": reason
            })

        results.append({
            "name": name,
            "state": state_cn
        })

        time.sleep(random.uniform(1.5, 3.5))

    summary = f"已签到 {checked} | 异常 {error}"

    if error == 0:
        title = f"{SITE_NAME}｜全部账号自愈签到成功"
    else:
        title = f"{SITE_NAME}｜自愈签到完成（含异常）"

    html = build_email(results, failed, summary)
    send_email(title, html)

    print(summary)


if __name__ == "__main__":
    run()
