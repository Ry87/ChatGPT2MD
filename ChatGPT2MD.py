import json
import os
import re
from datetime import datetime

# ===== 設定 =====
INPUT_FILE = "conversations.json"
OUTPUT_DIR = "chatgpt_md"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def sanitize_filename(text, max_length=80):
    text = re.sub(r'[\\/:*?"<>|]', '', text)
    return text[:max_length].strip()

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for conv_id, conv in data.items():
    mapping = conv.get("mapping", {})
    messages = []

    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue

        content = msg.get("content", {})
        parts = content.get("parts")
        if not parts:
            continue

        role = msg.get("author", {}).get("role")
        text = "\n".join(parts).strip()

        if role in ("user", "assistant"):
            messages.append((role, text))

    if not messages:
        continue

    # 最初のUser発言をタイトルに
    first_user_msg = next((m[1] for m in messages if m[0] == "user"), None)
    if not first_user_msg:
        continue

    title = sanitize_filename(first_user_msg.split("\n")[0])
    filename = sanitize_filename(title) + ".md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 会話作成日（質問日として使う）
    created_ts = conv.get("create_time")
    asked_date = None
    if created_ts:
        asked_date = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d")

    with open(filepath, "w", encoding="utf-8") as md:
        # YAML Frontmatter
        md.write("---\n")
        md.write("source: ChatGPT\n")
        if asked_date:
            md.write(f"asked_date: {asked_date}\n")
        md.write("---\n\n")

        # Title
        md.write(f"# {title}\n\n")

        # Visible date
        if asked_date:
            md.write(f"> 🗓 質問日: {asked_date}\n\n")

        # Messages
        for role, text in messages:
            if role == "user":
                md.write("## 🧑 User\n")
            else:
                md.write("## 🤖 ChatGPT\n")
            md.write(text + "\n\n")

print("✅ 日付入りMarkdown変換完了")
