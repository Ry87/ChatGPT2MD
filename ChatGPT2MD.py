import json
import re
from datetime import datetime, timezone
from pathlib import Path

# ===== 設定 =====
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "chatgpt_md"
OUTPUT_DIR.mkdir(exist_ok=True)

def sanitize_filename(text, max_length=80):
    text = re.sub(r'[\\/:*?"<>|]', '', text)
    text = text.replace("\n", " ")
    return text[:max_length].strip()

def extract_text_from_parts(parts):
    parts_text = []
    for part in parts:
        if isinstance(part, str):
            parts_text.append(part)
        elif isinstance(part, dict):
            if "text" in part:
                parts_text.append(part["text"])
            elif part.get("type") == "image":
                parts_text.append("[画像アップロードあり]")
            else:
                parts_text.append(str(part))
    return "\n".join(parts_text).strip()

def parse_created_time(conv):
    ts = conv.get("create_time")
    if isinstance(ts, int):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.astimezone()

def process_conversation(conv, source_type="unknown"):
    messages = []

    def extract_messages(obj):
        if isinstance(obj, dict):
            if "message" in obj and obj["message"] is not None:
                msg = obj["message"]
                content = msg.get("content", {}) if msg else {}
                parts = content.get("parts", []) if isinstance(content, dict) else []
                text = extract_text_from_parts(parts)
                role = msg.get("author", {}).get("role", "")
                if role in ("user", "assistant"):
                    messages.append((role, text))
            for v in obj.values():
                if v is not None:
                    extract_messages(v)
        elif isinstance(obj, list):
            for item in obj:
                if item is not None:
                    extract_messages(item)

    extract_messages(conv)

    if not messages:
        return

    first_user_msg = next((m[1] for m in messages if m[0]=="user"), None)
    if not first_user_msg:
        first_user_msg = "[画像のみの会話]"

    dt = parse_created_time(conv)
    asked_date = dt.strftime("%Y-%m-%d")

    safe_title = sanitize_filename(first_user_msg.split("\n")[0])
    filename = f"{asked_date}_{source_type}_{safe_title}.md"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as md:
        md.write("---\n")
        md.write(f"source: ChatGPT / {source_type}\n")
        md.write(f"asked_date: {asked_date}\n")
        md.write("---\n\n")

        md.write(f"# {first_user_msg.splitlines()[0]}\n\n")
        md.write(f"> 🗓 質問日: {asked_date}\n\n")

        for role, text in messages:
            if role == "user":
                md.write("## 🧑 User\n")
            else:
                md.write("## 🤖 ChatGPT\n")
            md.write(text + "\n\n")

# ===== 全 JSON 再帰探索 =====
total_count = 0
for json_file in BASE_DIR.rglob("*.json"):
    if json_file.name == "user.json":
        continue  # ユーザー情報は無視
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        continue  # 読み込み失敗はスキップ

    conversations = data if isinstance(data, list) else data.values()
    for conv in conversations:
        if conv is not None:
            process_conversation(conv, source_type=json_file.stem)
            total_count += 1

print(f"✅ 全JSON再帰探索・Markdown変換完了 ({total_count} 件生成)")
