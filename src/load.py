import aiohttp
import json
import os
import asyncio
import random
import hashlib
from botpy.client import _log

from config import BASE_DIR

# -------------------------- 配置区 --------------------------
API_HOST = "https://litterbox.catbox.moe/"  # 替换成你的镜像地址
EXPIRE_TIME = "1h"
CACHE_FILE = os.path.join(BASE_DIR, "json", "audio_upload_cache.json")
CACHE_EXPIRE_SEC = 3500  # litterbox 1h，提前清理缓存
MAX_HEAD = 10002432
# -----------------------------------------------------------

# 确保缓存目录存在
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)


def get_file_md5(filepath: str) -> str:
    md5_obj = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            md5_obj.update(chunk)
    return md5_obj.hexdigest()

def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def scan_audio_folder(folder: str, suffix_list=(".mp3",)) -> list:
    """扫描文件夹，返回符合后缀的音频绝对路径列表"""
    file_list = []
    if not os.path.isdir(folder):
        print(f"文件夹不存在：{folder}")
        return []

    for name in os.listdir(folder):
        full_path = os.path.join(folder, name)
        if os.path.isfile(full_path) and full_path.lower().endswith(suffix_list):
            file_list.append(full_path)
    return file_list

async def random_pick_audio(folder: str):
    """
    随机选取一个音频文件
    :param folder: 音频目录
    :return: 文件路径；无文件返回 None
    """
    files = scan_audio_folder(folder)
    if not files:
        print("目录下没有音频文件")
        return None
    return random.choice(files)\

def get_file_hash(file_path: str, block_size: int = 4 * 1024 * 1024):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(block_size):
            md5.update(chunk)
            sha1.update(chunk)
    return  md5.hexdigest(), sha1.hexdigest()

def get_head_md5_sync(file_path: str, block_size: int = 4 * 1024 * 1024) -> str:
    h = hashlib.md5()
    read_sum = 0
    with open(file_path, "rb") as f:
        while True:
            remain = MAX_HEAD - read_sum
            if remain <= 0:
                break
            buf = f.read(min(block_size, remain))
            if not buf:
                break
            h.update(buf)
            read_sum += len(buf)
    return h.hexdigest()

async def upload_chunk(presigned_url: str, chunk_bytes: bytes, max_retry: int = 2):
    headers = {
        "Content-Type": "application/octet-stream"
    }
    timeout_cfg = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.put(
            presigned_url,
            data=chunk_bytes,
            headers=headers
        ) as resp:
            resp_body = await resp.read()
            if resp.status != 200:
                # 把返回的HTML/错误内容一并抛出，上层能打印
                raise Exception(
                    f"分片PUT失败 status={resp.status}, "
                    f"resp_body={resp_body[:800]}"
                )
            return

async def get_file_chunk(file_path: str, start: int, end: int) -> bytes:
    chunk_size = end - start + 1
    # 同步文件读取放在 to_thread，避免阻塞事件循环
    chunk = await asyncio.to_thread(_read_chunk, file_path, start, chunk_size)
    return chunk

def _read_chunk(file_path: str, offset: int, length: int) -> bytes:
    with open(file_path, "rb") as f:
        f.seek(offset)
        return f.read(length)

async def download_audio_async(url: str, save_path: str) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    print(f"HTTP状态码异常：{resp.status}")
                    return False
                # 二进制流式写入，节省内存
                with open(save_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
        _log.info(f"音频保存成功: {save_path}")
        return True
    except Exception as err:
        _log.info(f"下载异常 {url} : {err}")
        return False


if __name__ == '__main__':
    ...