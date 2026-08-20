import os
import json
import re
from load import upload_json_file_cached
from openai import AsyncOpenAI, APIError, RateLimitError
from botpy.message import C2CMessage, GroupMessage

from config import *

with open(os.path.join(BASE_DIR, 'AI.txt'), 'r', encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()
MAX_HISTORY = 128
SESSION_FOLDER = os.path.join(BASE_DIR, "json", "session")
os.makedirs(SESSION_FOLDER, exist_ok=True)

# 内存缓存
session_map = {}

client = AsyncOpenAI(
    api_key=AIAPIKEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

def get_session_path(openid: str):
    return os.path.join(SESSION_FOLDER, f"{openid}.json")

def load_chat_session(openid: str):
    if openid in session_map:
        return session_map[openid]
    path = get_session_path(openid)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            msgs = json.load(f)
        session_map[openid] = msgs
        return msgs
    new_session = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}]
    session_map[openid] = new_session
    return new_session

def save_chat_session(openid: str, messages: list):
    session_map[openid] = messages
    path = get_session_path(openid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

async def get_ai_reply(message:GroupMessage|C2CMessage, chat_type):
    # 获取用户openid
    if chat_type == 0:
        user_openid = message.author.user_openid
    elif chat_type == 1:
        user_openid = message.author.member_openid
    else:
        return None

    content = message.content.strip()
    if not content:
        return None

    # 处理@携带会话文件
    ids = re.findall(r"<@([^>]+)>", content)
    extra_text = ""
    for openid_tag in ids:
        file_path = get_session_path(openid_tag)
        if os.path.isfile(file_path):
            try:
                with open(file_path,"r",encoding="utf-8") as f:
                    json_text = f.read()
                extra_text += f"\n【附加历史会话文件内容】\n{json_text}\n"
            except Exception as e:
                log.warning(f"读取会话文件失败 {file_path}: {e}")

    # 直接拼接普通字符串，不要数组！
    final_user_text = extra_text + content

    chat_msgs = load_chat_session(user_openid)
    if not chat_msgs:
        chat_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]

    # ✅ content 直接是字符串，不是list，关闭多模态解析，不会误判斜杠
    chat_msgs.append({"role": "user", "content": final_user_text})

    # 裁剪上下文
    if len(chat_msgs) > MAX_HISTORY:
        chat_msgs = [chat_msgs[0]] + chat_msgs[-(MAX_HISTORY - 1):]


    ai_text = None
    log.debug(f"发送给大模型 messages={chat_msgs}")
    try:
        resp = await client.chat.completions.create(
            model="glm-4.6v-flash",
            messages=chat_msgs,
            stream=False,
            max_tokens=4096,
            temperature=1.0
        )
        raw = resp.choices[0].message.content.strip()
        ai_text = raw.replace("\n", "")
        log.info(f"AI回复: {ai_text}")
        chat_msgs.append({
            "role": "assistant",
            "content": [{"type": "text", "text": ai_text}]
        })

        await message.reply(
            msg_type=2,
            markdown={"content": ai_text}
        )
        # 成功才保存会话
        save_chat_session(user_openid, chat_msgs)

    except RateLimitError as err:
        # 限流专属捕获
        err_body = err.response.json()
        error_info = err_body.get("error", {})
        if error_info.get("code") == "1305":
            reply_text = "当前模型访问量过大，请稍后再提问。"
        else:
            reply_text = "请求频率受限，请稍后重试。"
        await message.reply(msg_type=2, markdown={"content": reply_text})
    except Exception as err:
        # 其余所有异常
        log.error(f"AI调用异常: {err}")
        reply_text = "出问题了，快@群主排查bug"
        await message.reply(msg_type=2, markdown={"content": reply_text})