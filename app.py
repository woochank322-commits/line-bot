import os
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    MemberJoinedEvent,
)

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN과 LINE_CHANNEL_SECRET 환경 변수를 설정해주세요.")

app = Flask(__name__)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DATA_FILE = "madi_stats.json"
KST = ZoneInfo("Asia/Seoul")

WELCOME_MESSAGE = """𓆩 𝑾𝑬𝑳𝑪𝑶𝑴𝑬 𓆪
 🕰️ 𝐕𝐄𝐋𝐕𝐄𝐓 𝐇𝐎𝐔𝐑 🥀

새로운 인연의 입장을 환영합니다. 🗝️
벨벳 아워에서 즐거운 시간 보내시길 바랍니다.

┈┈┈┈┈ 𓆩 🥀 𓆪 ┈┈┈┈┈

📌 신입 필수 안내

➊ 공지 확인 : 노트에 등록된 공지와 규칙을 반드시 정독해주세요.

➋ 자기소개 : 노트의 양식에 맞춰 빠짐없이 작성해주세요.

➌ 족보 작성 : 초대자와 본인의 닉네임을 기재해주세요.

┈┈┈┈┈ 𓆩 🕰️ 𓆪 ┈┈┈┈┈

🥀 기존 멤버 안내

ㆍ신입에게 먼저 반갑게 인사하기
ㆍ대화에 자연스럽게 참여하도록 도와주기
ㆍ소외되지 않도록 함께 어울려주기
ㆍ방 분위기와 이용 방법 친절하게 안내하기

신입이 편안하게 적응할 수 있도록 모두 함께 배려해주세요.

┈┈┈┈┈ 𓆩 🗝️ 𓆪 ┈┈┈┈┈

𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐕𝐄𝐋𝐕𝐄𝐓 𝐇𝐎𝐔𝐑
〜 당신의 새로운 시간이 시작됩니다. 〜"""

# 환찌환츄 안내(/환찌환츄) 및 매너봉(ㅁㄴ)만 담당
KEYWORD_REPLIES = {
    "/환찌환츄": [
        (
            "𓆩 𝑽𝑬𝑳𝑽𝑬𝑻 𝑯𝐎𝐔𝐑 𓆪\n"
            "   🥀 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐆𝐀𝐌𝐄 🗝️\n"
            "     ⏳ 환찌환츄 안내\n\n"
            "┈┈┈┈┈ 𓆩 🕰️ 𓆪 ┈┈┈┈┈\n\n"
            "⌗ 환찌환츄란?\n"
            "ㆍ환영 찌찌, 환영 고츄 라는 뜻\n\n"
            "⌗ 참여 대상\n"
            "ㆍ새롭게 입장한 신입 멤버만 참여 가능\n"
            "ㆍ기존 멤버의 신규 참여는 불가\n\n"
            "⌗ 진행 방법\n"
            "➊ 신입 멤버가 가슴, 자지 사진을 올립니다.\n"
            "➋ 사진을 올린 후 다른 멤버 한 명을 지목합니다.\n"
            "➌ 지목받은 멤버는 반드시 답으로 사진을 보내야 하고 이를 거절하면 경고가 부여됩니다.\n"
            "➍ 다만, 환찌환츄는 필수가 아닙니다"
        ),
        (
            "매너봉\n"
            "매너봉이란?\n"
            "ㆍ사진을 보낸 후 자동으로 이모티콘들이 보내지는 시스템입니다\n\n"
            "- 사진을 보낸 후 매너봉을 사용합니다\n"
            "(ㅁㄴ를 치면 매너봉 사용 가능)\n"
            "- 사진을 보낸 후에는 반드시 삭제가 아닌 보내기 취소를 해주세요!\n"
            "- 매너봉을 하지 않을 시 답찌, 답츄를 받을 수 없습니다.\n\n"
            " 참여 매너\n"
            "ㆍ상대방의 사진을 억지로 요구하지 않기\n"
            "ㆍ사진 저장 및 외부 공유 금지\n"
            "ㆍ참여를 거절해도 불이익이나 재촉 금지\n"
            "ㆍ타인의 사진을 무단으로 공개하지 않기\n\n\n\n"
            "┈┈┈┈┈ 𓆩 🥀 𓆪 ┈┈┈┈┈\n\n"
            "신입 멤버와 기존 멤버가 자연스럽게\n"
            "서로를 알아가는 시간을 만들어주세요.\n\n"
            "𓆩 𝐕𝐄𝐋𝐕𝐄𝐓 𝐇𝐎𝐔𝐑 𓆪"
        ),
    ],
    "ㅁㄴ": [
        {"type": "sticker", "package_id": "11537", "sticker_id": "52002734"},
        {"type": "sticker", "package_id": "11537", "sticker_id": "52002735"},
        {"type": "sticker", "package_id": "11537", "sticker_id": "52002736"},
        {"type": "sticker", "package_id": "11537", "sticker_id": "52002737"},
        {"type": "sticker", "package_id": "11537", "sticker_id": "52002738"},
    ],
}


def get_today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_stats() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_stats(stats: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


madi_stats = load_stats()


def ensure_today_members(room_key: str) -> dict:
    """한국 시간(KST) 오늘 날짜 기준으로 채팅방 마딧수 데이터를 보장하고 날짜가 바뀌면 초기화"""
    today = get_today_kst()
    room_entry = madi_stats.get(room_key)

    if not isinstance(room_entry, dict) or room_entry.get("date") != today:
        madi_stats[room_key] = {
            "date": today,
            "members": {},
        }
        save_stats(madi_stats)

    members = madi_stats[room_key].get("members")
    if not isinstance(members, dict):
        madi_stats[room_key]["members"] = {}
        save_stats(madi_stats)

    return madi_stats[room_key]["members"]


def count_valid_madi(text: str) -> int:
    """공백 기준 단어 중 앞뒤 특수문자를 제거한 뒤 3글자 이상 완성형 한글/영문/숫자만 카운트"""
    raw_words = text.split()
    valid_pattern = re.compile(r"^[가-힣a-zA-Z0-9]{3,}$")
    count = 0

    for raw in raw_words:
        cleaned = re.sub(r"^[^\w가-힣ㄱ-ㅎㅏ-ㅣ]+|[^\w가-힣ㄱ-ㅎㅏ-ㅣ]+$", "", raw)
        if valid_pattern.match(cleaned):
            count += 1

    return count


def get_source_id(event) -> str:
    source = event.source
    if getattr(source, "group_id", None):
        return f"group_{source.group_id}"
    if getattr(source, "room_id", None):
        return f"room_{source.room_id}"
    return f"user_{source.user_id}"


def fetch_display_name(event, user_id: str) -> str:
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            source = event.source
            if getattr(source, "group_id", None):
                profile = line_bot_api.get_group_member_profile(source.group_id, user_id)
                return profile.display_name
            if getattr(source, "room_id", None):
                profile = line_bot_api.get_room_member_profile(source.room_id, user_id)
                return profile.display_name
            profile = line_bot_api.get_profile(user_id)
            return profile.display_name
    except Exception:
        return "알 수 없는 멤버"


def reply_content(reply_token: str, content):
    items = content if isinstance(content, list) else [content]
    messages = []

    for item in items[:5]:
        if isinstance(item, dict) and item.get("type") == "sticker":
            messages.append(
                StickerMessage(
                    package_id=str(item["package_id"]),
                    sticker_id=str(item["sticker_id"]),
                )
            )
        else:
            messages.append(TextMessage(text=str(item)))

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages,
            )
        )


@app.route("/", methods=["GET"])
def health_check():
    return "VELVET HOUR Main Bot is running.", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    reply_content(event.reply_token, WELCOME_MESSAGE)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip()
    user_id = getattr(event.source, "user_id", None)
    room_key = get_source_id(event)

    members_data = ensure_today_members(room_key)
    today_str = get_today_kst()

    if user_text == "/전체랭킹":
        if not members_data:
            reply_content(event.reply_token, f"📊 {today_str} 아직 집계된 오늘의 마딧수 기록이 없습니다.")
            return

        sorted_members = sorted(
            members_data.items(),
            key=lambda item: item[1]["count"],
            reverse=True,
        )

        lines = [f"🏆 𝐕𝐄𝐋𝐕𝐄𝐓 𝐇𝐎𝐔𝐑 오늘({today_str}) 마딧수 랭킹", "┈┈┈┈┈ 𓆩 🥀 𓆪 ┈┈┈┈┈"]
        for idx, (_, info) in enumerate(sorted_members[:20], start=1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}위"
            lines.append(f"{medal} {info['name']} : {info['count']}마디")

        reply_content(event.reply_token, "\n".join(lines))
        return

    if user_text == "/내랭킹":
        if not user_id:
            reply_content(event.reply_token, "사용자 정보를 확인할 수 없습니다.")
            return

        if user_id not in members_data or members_data[user_id]["count"] == 0:
            name = fetch_display_name(event, user_id)
            reply_content(
                event.reply_token,
                f"🥀 {name}님의 오늘({today_str}) 마딧수 기록\n• 오늘 마딧수 : 0마디\n• 현재 순위 : 순위 없음",
            )
            return

        sorted_members = sorted(
            members_data.items(),
            key=lambda item: item[1]["count"],
            reverse=True,
        )

        rank = next(
            (idx for idx, (uid, _) in enumerate(sorted_members, start=1) if uid == user_id),
            None,
        )
        my_info = members_data[user_id]
        total_members = len(sorted_members)

        reply_content(
            event.reply_token,
            f"🥀 {my_info['name']}님의 오늘({today_str}) 마딧수 기록\n"
            f"• 오늘 마딧수 : {my_info['count']}마디\n"
            f"• 현재 순위 : 전체 {total_members}명 중 {rank}위",
        )
        return

    if user_text in KEYWORD_REPLIES:
        reply_content(event.reply_token, KEYWORD_REPLIES[user_text])
        return

    if user_id and not user_text.startswith("/"):
        added_madi = count_valid_madi(user_text)
        if added_madi > 0:
            if user_id not in members_data:
                display_name = fetch_display_name(event, user_id)
                members_data[user_id] = {"name": display_name, "count": 0}
            members_data[user_id]["count"] += added_madi
            save_stats(madi_stats)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
    
