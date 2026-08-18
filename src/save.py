import json
import os
import asyncio
from config import * 

# 仅单个数据文件场景，全局锁；多文件请改用锁字典 {filepath: asyncio.Lock()}
chat_json_lock = asyncio.Lock()

def init_data_json_sync(file: str):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({'c2c': [], 'group': []}, f, ensure_ascii=False, indent=2)

def load_json_sync(file: str):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        log.warning(f"文件 {file} 损坏，重置数据")
        data = {'c2c': [], 'group': []}
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

def save_json_sync(file: str, data):
    # w模式：全量覆盖写入
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def get_all_data(file: str, chat_type: int):
    """
    :param chat_type: 0 c2c私聊  1 group群聊
    :return: openid列表
    """
    await asyncio.to_thread(init_data_json_sync, file)
    async with chat_json_lock:
        data = await asyncio.to_thread(load_json_sync, file)
        if chat_type == 0:
            return data['c2c']
        elif chat_type == 1:
            return data['group']
        else:
            return data.get(chat_type, [])
        return []

async def add_data(file: str, item, chat_type: int):
    """添加会话，兼容字符串openid / dict结构"""
    await asyncio.to_thread(init_data_json_sync, file)
    async with chat_json_lock:
        data = await asyncio.to_thread(load_json_sync, file)
        if chat_type == 0:
            key = 'c2c'
        elif chat_type == 1:
            key = 'group'
        else:
            key = chat_type
        lst = data.setdefault(key, [])

        # 查重
        exists = False
        if isinstance(item, dict) and "type" in item and "id" in item:
            for d in lst:
                if d.get("type") == item["type"] and d.get("id") == item["id"]:
                    exists = True
                    break
        else:
            if item in lst:
                exists = True

        if not exists:
            lst.append(item)
            await asyncio.to_thread(save_json_sync, file, data)

async def remove_data(file: str, item, chat_type: int):
    """删除会话，修复字典无法remove的bug"""
    await asyncio.to_thread(init_data_json_sync, file)
    async with chat_json_lock:
        data = await asyncio.to_thread(load_json_sync, file)
        if chat_type == 0:
            key = 'c2c'
        elif chat_type == 1:
            key = 'group'
        else:
            key = chat_type
        lst = data.setdefault(key, [])
        remove_idx = None

        if isinstance(item, dict) and "type" in item and "id" in item:
            for idx, d in enumerate(lst):
                if d.get("type") == item["type"] and d.get("id") == item["id"]:
                    remove_idx = idx
                    break
        else:
            try:
                remove_idx = lst.index(item)
            except ValueError:
                pass

        if remove_idx is not None:
            del lst[remove_idx]
            await asyncio.to_thread(save_json_sync, file, data)