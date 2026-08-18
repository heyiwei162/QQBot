import aiohttp
import asyncio
import os
import re
import type
from typing import List

from config import * 

API_BASE = "http://127.0.0.1:5000"
SAVE_ROOT = os.path.join(BASE_DIR, 'music')
SEMAPHORE = asyncio.Semaphore(4)

class Music:
    def __init__(self, data:type.MusicInfo):
        self.id = data.get("id", None)
        self.name = data.get("name", None)
        self.artists = data.get('artists', None)
        self.artist_string = data.get('artist_string', None)
        self.album = data.get('album', None)
        self.picUrl = data.get('picUrl', None)


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)

async def json_get(session: aiohttp.ClientSession, url: str, params):
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        return await resp.json()

async def search_song(session: aiohttp.ClientSession, keyword: str):
    log.debug(f"[搜索] 关键词：{keyword}")
    params = {
        "keywords": keyword,
        "type": "music"
    }
    url = f"{API_BASE}/search"
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        data = await resp.json()
    songs = data.get("data", [])
    if not songs:
        log.debug("[搜索结果] 无歌曲")
        return None
    s = []
    for idx,song in enumerate(songs):
        if idx >= 20:
            break
        s.append(Music(song))
    return s


async def get_song_url(session: aiohttp.ClientSession, song_id):
    log.debug(f"[请求播放地址] song_id={song_id}")
    params = {"id": song_id}
    async with session.get(f"{API_BASE}/song", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        info = await resp.json()
    data = info.get("data")
    if not data:
        log.debug("[播放地址] data为空")
        return None
    url = data.get("url")
    log.debug(f"[播放url] {url}")
    return url

async def download_single(session: aiohttp.ClientSession, url: str, save_path: str):
    if os.path.exists(save_path):
        log.debug(f"已存在，跳过：{os.path.basename(save_path)}")
        return
    async with SEMAPHORE:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                with open(save_path, "wb") as f:
                    while chunk := await resp.content.read(131072):
                        f.write(chunk)
            log.debug(f"下载完成：{os.path.basename(save_path)}")
        except Exception as e:
            log.debug(f"下载失败 {os.path.basename(save_path)}: {str(e)}")

async def get_songs_keyboard(session,song_name, music_id):
    song_info:List[Music] = await search_song(session, song_name)
    row = []  # 初始化行数组，放到最外层
    msg = "歌曲信息:\n"
    for idx, song in enumerate(song_info):
        msg += f"{idx+1}.歌名:{song.name}, 歌手:{song.artists}\n"
        if idx >= 7:
            break
    for idx, song in enumerate(song_info):
        button = []
        for i in range(4):
            select_num = idx * 4 + i + 1
            button.append({
                "id": f"bot_music_choose_{music_id}_{select_num}",
                "render_data": {
                    "label": f"选{select_num}",
                    "style": 4
                },
                "action": {
                    "type": 1,
                    "permission": {"type": 2},
                    "data": ""   # 这里自行填充点击指令
                }
            })
        row.append({"buttons": button})
        if len(row) >= 2:
            break


    keyboard = {"content": {"rows": row}}
    return msg, keyboard, song_info