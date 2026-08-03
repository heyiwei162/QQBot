import json
import os
import asyncio
from botpy.client import _log
# 异步锁
chat_json_lock = asyncio.Lock()

def init_data_json(file:str):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({'c2c': [], 'group': []}, f, ensure_ascii=False, indent=2)

async def get_all_data(file:str,chat_type: int):
    """
    :param chat_type: 0 c2c私聊  1 group群聊
    :return: openid列表
    """
    init_data_json(file)
    async with chat_json_lock:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception):
            # 文件损坏重置
            data = {'c2c': [], 'group': []}
            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        if chat_type == 0:
            return data['c2c']
        elif chat_type == 1:
            return data['group']
        else:
            return []

async def add_data(file:str,data, chat_type: int):
    """
    添加会话
    chat_type: 0私聊c2c  1群group
    """
    async with chat_json_lock:
        try:
            with open(file, "r", encoding="utf-8") as f:
                f_data = json.load(f)
        except (json.JSONDecodeError, Exception):
            f_data = {'c2c': [], 'group': []}

        key = "c2c" if chat_type == 0 else "group"
        if data not in f_data[key]:
            for d in f_data[key]:
                _log.info(f"data={data},d={d}")
                if type(data) == dict:
                    if data.get('type'):
                        if d.get('type') == data.get('type') and d.get('id') == data.get('id'):
                            return
            f_data[key].append(data)
            with open(file, "w", encoding="utf-8") as f:
                json.dump(f_data, f, ensure_ascii=False, indent=2)

async def remove_data(file:str,data: str, chat_type: int):
    """
    删除会话
    chat_type: 0私聊c2c  1群group
    """
    async with chat_json_lock:
        try:
            with open(file, "r", encoding="utf-8") as f:
                f_data = json.load(f)
        except (json.JSONDecodeError, Exception):
            f_data = {'c2c': [], 'group': []}

        key = "c2c" if chat_type == 0 else "group"
        if type(data) == dict:
            if data.get('type'):
                for d in f_data[key]:
                    if d.get('type') == data.get('type') and d.get('id') == data.get('id'):
                        f_data[key].remove(data)
        if data in f_data[key]:
            f_data[key].remove(data)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(f_data, f, ensure_ascii=False, indent=2)