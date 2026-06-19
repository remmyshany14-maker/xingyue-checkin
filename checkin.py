import os
import time
import random
import requests

def send_email(title, content):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        return

    msg = MIMEMultipart()
    msg["Subject"] = title
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    msg.attach(MIMEText(content, "plain", "utf-8"))

    # 加图
    for img in ["success_rate.png"]:
        if os.path.exists(img):
            with open(img, "rb") as f:
                img_data = MIMEImage(f.read())
                img_data.add_header("Content-Disposition", "attachment", filename=img)
                msg.attach(img_data)

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
    except Exception as e:
        print("[EMAIL ERROR]", e)

BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

# ========= token =========
def load_tokens():
    raw = os.getenv("SECRET_TOKENS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


TOKENS = load_tokens()


# ========= email =========
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")


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


# ========= request =========
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


# ========= main =========
def run():
    print("===== START CHECKIN =====")

    results = []

    for token in TOKENS:
        time.sleep(random.uniform(2, 6))

        status = check_status(token)
        result = checkin(token)

        print("STATUS:", status)
        print("CHECKIN:", result)

        if result.get("code") == 200:
            state = "SUCCESS"
        elif result.get("code") == 5150:
            state = "ALREADY"
        else:
            state = "FAILED"

        results.append({
            "token": token[:10],
            "state": state
        })

        add_log(state)

    # ========= report =========
    summary = "\n".join([f"{r['token']} => {r['state']}" for r in results])

    print("\n===== REPORT =====")
    print(summary)

    send_email(
        f"签到日报 {datetime.now().strftime('%Y-%m-%d')}",
        summary
    )


if __name__ == "__main__":
    run()


from dashboard import plot_success_rate

plot_success_rate()
