import os
import time
import random
import requests
from datetime import datetime

BASE_URL = "https://c.xingyuexiezuo.com/api/v1"

TOKENS = [t.strip() for t in os.getenv("SECRET_TOKENS", "").split(",") if t.strip()]

# ========= token 状态池 =========
token_state = {
    t: {
        "fail": 0,
        "status": "OK"   # OK / DEAD
    } for t in TOKENS
}


# ========= delay =========
def sleep_random(a=2, b=6):
    time.sleep(random.uniform(a, b))


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
        r = requests.post(url, headers=headers, json=payload or {}, timeout=10)
        return r.json()
    except Exception as e:
        return {"code": -1, "error": str(e)}


# ========= status =========
def check_status(token):
    return request_post(f"{BASE_URL}/forum/checkin/status", token)


# ========= checkin =========
def checkin(token):
    return request_post(
        f"{BASE_URL}/forum/checkin",
        token,
        {"data": "RUTjr2nDiRda1I+NCO3FqQ=="}
    )


# ========= token 更新逻辑 =========
def update_token_state(token, success: bool):
    state = token_state[token]

    if success:
        state["fail"] = 0
        state["status"] = "OK"
    else:
        state["fail"] += 1
        if state["fail"] >= 3:
            state["status"] = "DEAD"


# ========= 获取可用 token =========
def get_active_tokens():
    return [t for t in TOKENS if token_state[t]["status"] != "DEAD"]


# ========= 主流程 =========
def run():
    print("===== START =====")

    results = []

    for token in TOKENS:

        # DEAD token 仍然尝试“复活”
        if token_state[token]["status"] == "DEAD":
            print(f"[SKIP DEAD] try revive {token[:10]}...")
            continue

        sleep_random(2, 5)

        status = check_status(token)
        result = checkin(token)

        print("[status]", status)
        print("[checkin]", result)

        # ========= 判断成功 =========
        if result.get("code") == 200:
            update_token_state(token, True)
            state = "SUCCESS"

        elif result.get("code") == 5150:
            update_token_state(token, True)
            state = "ALREADY"

        else:
            update_token_state(token, False)
            state = "FAILED"

        results.append({
            "token": token[:10],
            "state": state,
            "fail_count": token_state[token]["fail"]
        })

    print("\n===== REPORT =====")
    for r in results:
        print(r)

    print("\nTOKEN STATE:")
    for k, v in token_state.items():
        print(k[:10], v)


if __name__ == "__main__":
    run()
