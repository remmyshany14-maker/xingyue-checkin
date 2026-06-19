import os

TOKEN_FILE = "tokens.txt"

def load_tokens():
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return [i.strip() for i in f.readlines() if i.strip()]


def save_tokens(tokens):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(tokens))


def replace_token(bad_token):
    tokens = load_tokens()

    print(f"[REMOVE] {bad_token[:10]}")

    if bad_token in tokens:
        tokens.remove(bad_token)

    # 👉 从备用池补一个（如果有）
    if len(tokens) == 0:
        print("[ERROR] no backup token available")
        return None

    new_token = tokens[0]   # 简单策略：顺序替换

    save_tokens(tokens)

    print(f"[REPLACE] -> {new_token[:10]}")
    return new_token
