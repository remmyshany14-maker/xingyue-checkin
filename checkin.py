import os
import time
import random
import requests
from datetime import datetime

BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

TOKENS = [t.strip() for t in os.getenv("SECRET_TOKENS", "").split(",") if t.strip()]


# ========= 随机延迟（核心） =========
def human_delay(min_s=2, max_s=8):
    delay = random.uniform(min_s, max_s)
    print(f"[delay] sleep {delay:.2f}s")
    time.sleep(delay)


# ========= HTTP 请求 =========
def request_post(url, token, payload=None, retry=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Device": "web",
        "Platform": "web",
        "Bundle": "web",
        "Version": "5.1.0",

        # 轻量 UA（不做伪装，只保证兼容）
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Content-Type": "application/json"
    }

    for i in range(retry):
        try:
            r = requests.post(url, headers=headers, json=payload or {}, timeout=10)
            return r.json()
        except Exception as e:
            print(f"[retry {i+1}] error: {e}")
            time.sleep(2 + i)

    return {"code": -1, "msg": "request failed"}


# ========= 状态 =========
def get_status(token):
    return request_post(f"{BASE_URL}/forum/checkin/status", token)


def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ========= 主流程 =========
def run():
    results = []

    print("===== START CHECKIN =====")

    # ⭐ 全局随机延迟（防“同一时间批量请求”特征）
    human_delay(3, 10)

    for i, token in enumerate(TOKENS, 1):

        print(f"\n[account {i}] start")

        # ⭐ 每个账号之间随机等待
        human_delay(2, 6)

        status = get_status(token)
        print("[status]", status)

        result = checkin(token)
        print("[checkin]", result)

        if result.get("code") == 200:
            state = "SUCCESS"
        elif result.get("code") == 5150:
            state = "ALREADY"
        else:
            state = "FAILED"

        results.append((i, state, result))

    print("\n===== DONE =====")
    for r in results:
        print(r)


if __name__ == "__main__":
    run()
