import aiohttp
import json
import os
import asyncio
import random
import hashlib
import time

from config import * 

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

async def upload_json_file_cached(file_path: str) -> str:
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    filename = os.path.basename(file_path)
    if not filename.lower().endswith(".json"):
        raise ValueError("仅支持上传 .json 文件")

    cache = load_cache()
    md5_key = get_file_md5(file_path)
    now = time.time()

    # 缓存有效直接返回链接
    if md5_key in cache:
        item = cache[md5_key]
        if now - item["upload_ts"] < CACHE_EXPIRE_SEC:
            return item["url"]
        del cache[md5_key]

    api_url = f"{API_HOST}/resources/internals/api.php"
    form_data = aiohttp.FormData()
    form_data.add_field("reqtype", "fileupload")
    form_data.add_field("time", EXPIRE_TIME)

    fp = open(file_path, "rb")
    try:
        form_data.add_field(
            "fileToUpload",
            fp,
            filename=filename,
            content_type="application/json"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.text()
                link = result.strip()
    finally:
        fp.close()

    if not link.startswith("http"):
        raise RuntimeError(f"JSON文件上传失败，返回内容：{link}")

    cache[md5_key] = {
        "url": link,
        "upload_ts": now
    }
    save_cache(cache)
    return link

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
    timeout_cfg = aiohttp.ClientTimeout(total=60)

    for attempt in range(max_retry + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
                async with session.put(
                    presigned_url,
                    data=chunk_bytes,
                    headers=headers
                ) as resp:
                    resp_body = await resp.read()
                    if resp.status != 200:
                        raise Exception(
                            f"分片PUT失败 status={resp.status}, "
                            f"resp_body={resp_body[:800]}"
                        )
                    return
        except aiohttp.ClientError as e:
            if attempt >= max_retry:
                raise Exception(f"分片上传重试{max_retry}次仍然失败: {str(e)}")
            print(f"分片上传异常，准备重试 {attempt+1}/{max_retry} err={e}")
            await asyncio.sleep(1.2)
            
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
        log.info(f"音频保存成功: {save_path}")
        return True
    except Exception as err:
        log.info(f"下载异常 {url} : {err}")
        return False


if __name__ == '__main__':
    ...