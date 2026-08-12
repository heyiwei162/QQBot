import aiohttp
import json
import os
import asyncio
import random
import hashlib
import time
from botpy.client import _log

from config import BASE_DIR

# -------------------------- 配置区 --------------------------
API_HOST = "https://litterbox.catbox.moe/"  # 替换成你的镜像地址
EXPIRE_TIME = "1h"
CACHE_FILE = os.path.join(BASE_DIR, "json", "audio_upload_cache.json")
CACHE_EXPIRE_SEC = 3500  # litterbox 1h，提前清理缓存
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

async def upload_audio_cached(file_path: str) -> str:
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    cache = load_cache()
    md5_key = get_file_md5(file_path)
    now = time.time()

    # 检查缓存
    if md5_key in cache:
        item = cache[md5_key]
        upload_ts = item["upload_ts"]
        audio_url = item["url"]
        if now - upload_ts < CACHE_EXPIRE_SEC:
            # 缓存有效，直接返回
            return audio_url
        else:
            # 缓存过期，删除旧条目，重新上传
            del cache[md5_key]

    # ---------------- 下面是原有上传逻辑不变 ----------------
    api_url = f"{API_HOST}/resources/internals/api.php"
    form_data = aiohttp.FormData()
    form_data.add_field("reqtype", "fileupload")
    form_data.add_field("time", EXPIRE_TIME)

    with open(file_path, "rb") as f:
        filename = os.path.basename(file_path)
        form_data.add_field(
            "fileToUpload",
            f.read(),
            filename=filename,
            content_type="audio/mpeg"
        )

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=form_data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            result = await resp.text()
            link = result.strip()

    if not link.startswith("http"):
        raise RuntimeError(f"上传失败，返回：{link}")

    # 存入带时间戳的缓存
    cache[md5_key] = {
        "url": link,
        "upload_ts": now
    }
    save_cache(cache)
    return link

async def upload_image_cached(file_path: str) -> str:
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    cache = load_cache()
    md5_key = get_file_md5(file_path)
    now = time.time()

    # 检查缓存
    if md5_key in cache:
        item = cache[md5_key]
        upload_ts = item["upload_ts"]
        img_url = item["url"]
        if now - upload_ts < CACHE_EXPIRE_SEC:
            # 缓存有效，直接返回
            return img_url
        else:
            # 缓存过期，删除旧条目，重新上传
            del cache[md5_key]

    # ---------------- 上传逻辑 ----------------
    api_url = f"{API_HOST}/resources/internals/api.php"
    form_data = aiohttp.FormData()
    form_data.add_field("reqtype", "fileupload")
    form_data.add_field("time", EXPIRE_TIME)

    with open(file_path, "rb") as f:
        filename = os.path.basename(file_path)
        # 根据后缀自动匹配图片mime，兜底image/jpeg
        ext = filename.lower().split(".")[-1]
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp"
        }
        content_type = mime_map.get(ext, "image/jpeg")

        form_data.add_field(
            "fileToUpload",
            f.read(),
            filename=filename,
            content_type=content_type
        )

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, data=form_data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            result = await resp.text()
            link = result.strip()

    if not link.startswith("http"):
        raise RuntimeError(f"图片上传失败，返回：{link}")

    # 存入缓存
    cache[md5_key] = {
        "url": link,
        "upload_ts": now
    }
    save_cache(cache)
    return link

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
    return random.choice(files)

async def main():
    audio = await random_pick_audio(os.path.join(BASE_DIR, "audio"))
    _log.debug(f"音频路径:{audio}")
    url = await upload_audio_cached(os.path.join(BASE_DIR, "audio", audio))
    _log.debug(f"音频链接:{url}")

if __name__ == '__main__':
    asyncio.run(main())