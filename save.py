import json
import os
import asyncio

GROUP_FILE = "./chat_list.json"
# 异步锁
chat_json_lock = asyncio.Lock()

def init_chat_json():
    if not os.path.exists(GROUP_FILE):
        with open(GROUP_FILE, "w", encoding="utf-8") as f:
            json.dump({'c2c': [], 'group': []}, f, ensure_ascii=False, indent=2)

async def get_all_chat(chat_type: int):
    """
    :param chat_type: 0 c2c私聊  1 group群聊
    :return: openid列表
    """
    init_chat_json()
    async with chat_json_lock:
        try:
            with open(GROUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception):
            # 文件损坏重置
            data = {'c2c': [], 'group': []}
            with open(GROUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        if chat_type == 0:
            return data['c2c']
        elif chat_type == 1:
            return data['group']
        else:
            return []

async def add_chat(openid: str, chat_type: int):
    """
    添加会话
    chat_type: 0私聊c2c  1群group
    """
    async with chat_json_lock:
        try:
            with open(GROUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception):
            data = {'c2c': [], 'group': []}

        key = "c2c" if chat_type == 0 else "group"
        if openid not in data[key]:
            data[key].append(openid)
            with open(GROUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

async def remove_chat(openid: str, chat_type: int):
    """
    删除会话
    chat_type: 0私聊c2c  1群group
    """
    async with chat_json_lock:
        try:
            with open(GROUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception):
            data = {'c2c': [], 'group': []}

        key = "c2c" if chat_type == 0 else "group"
        if openid in data[key]:
            data[key].remove(openid)
            with open(GROUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)