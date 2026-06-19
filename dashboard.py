import json
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

LOG_FILE = "log.json"


def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_logs(logs):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def add_log(result):
    logs = load_logs()

    logs.append({
        "time": datetime.now().strftime("%Y-%m-%d"),
        "state": result
    })

    save_logs(logs)


def plot_success_rate():
    logs = load_logs()

    last7 = logs[-7:]

    labels = [i["time"] for i in last7]
    success = sum(1 for i in last7 if i["state"] == "SUCCESS")
    already = sum(1 for i in last7 if i["state"] == "ALREADY")
    fail = sum(1 for i in last7 if i["state"] == "FAILED")

    plt.figure()
    plt.bar(["SUCCESS", "ALREADY", "FAILED"], [success, already, fail])
    plt.title("Checkin Status (Last 7 Days)")
    plt.savefig("success_rate.png")


def plot_token_health(tokens_status):
    labels = list(tokens_status.keys())
    values = [1 if v == "ok" else 0 for v in tokens_status.values()]

    plt.figure()
    plt.bar(labels, values)
    plt.title("Token Health")
    plt.savefig("token_health.png")


if __name__ == "__main__":
    print("dashboard generated")
