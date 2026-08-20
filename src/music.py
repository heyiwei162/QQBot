import aiohttp
import asyncio
import os
import re
import json
from typing import List

from config import *

API_BASE = "http://127.0.0.1:3000"
SAVE_ROOT = os.path.join(BASE_DIR, 'music')
SEMAPHORE = asyncio.Semaphore(4)


with open(os.path.join(BASE_DIR,"json","setting.json"), "r", encoding="utf-8") as f:
    data = json.load(f)
    COOKIE = data.get("MUSICCOOKIE")
headers = {"Cookie": f"MUSIC_U={COOKIE}; __remember_me=true;"}


class Music:
    def __init__(self, data):
        self.album = self._Album(data.get('album',{}))
        self.fee = data.get("fee",None)
        self.duration = data.get("duration",None)
        self.rtype = data.get("rtype",None)
        self.ftype = data.get("ftype",None)
        self.artists:List[Music._Artist] = []
        for artist in data.get("artists",[]):
            self.artists.append(self._Artist(artist))
        self.copyrightId = data.get("copyrightId",None)
        self.mvid = data.get("mvid",None)
        self.name = data.get("name",None)
        self.alias = data.get("alias",[])
        self.id = data.get("id",None)
        self.mark = data.get("mark",None)
        self.status = data.get("status",None)

    class _Album:
        def __init__(self, data):
            self.publishTime = data.get("publishTime",None)
            self.size = data.get("size",None)
            self.artist = Music._Artist(data.get("artist",{}))
            self.copyrightId = data.get("copyrightId",None)
            self.name = data.get("name",None)
            self.id = data.get("id",None)
            self.picId = data.get("picId",None)
            self.mark = data.get("mark",None)
            self.status = data.get("status",None)

    class _Artist:
        def __init__(self, data):
            self.img1v1Url = data.get("img1v1Url",None)
            self.musicSize = data.get("musicSize",None)
            self.albumSize =data.get("albumSize",None)
            self.img1v1 = data.get("img1v1",None)
            self.name = data.get("name",None)
            self.alias = data.get("alias",[])
            self.id = data.get("id",None)
            self.picId = data.get("picId",None)
            
class MusicItem:
    def __init__(self, data):
        self.id = data.get("id", None)
        self.url = data.get("url",None)
        self.br = data.get("br",None)
        self.size = data.get("size",None)
        self.md5 = data.get("md5",None)
        self.code = data.get("code",None)
        self.expi = data.get("expi",None)
        self.type = data.get("type",None)
        self.gain = data.get("gain",None)
        self.peak = data.get("peak",None)
        self.closedGain = data.get("closedGain",None)
        self.closedPeak = data.get("closedPeak",None)
        self.fee = data.get("fee",None)
        self.uf = data.get("uf",None)
        self.payed = data.get("payed",None)
        self.flag = data.get("flag",None)
        self.canExtend = data.get("canExtend",None)
        self.freeTrialInfo = data.get("freeTrialInfo",None)
        self.level = data.get("level",None)
        self.encodeType = data.get("encodeType",None)
        self.channelLayou = data.get("channelLayou",None)
        self.freeTrialPrivilege = self._FreeTrialPrivilege(data.get("freeTrialPrivilege",{}))
        self.freeTimeTrialPrivileg = self._FreeTimeTrialPrivileg(data.get("freeTimeTrialPrivileg",{}))
        self.urlSource = data.get("urlSource",None)
        self.rightSource = data.get("rightSource",None)
        self.podcastCtrp = data.get("podcastCtrp",None)
        self.effectTypes = data.get("effectTypes",None)
        self.time = data.get("time",None)
        self.message = data.get("message",None)
        self.levelConfuse = data.get("levelConfuse",None)
        self.musicId = data.get("musicId",None)
        self.accompany = data.get("accompany",None)
        self.sr = data.get("sr",None)
        self.auEff = data.get("auEff",None)
        self.immerseType = data.get("immerseType",None)
        self.beatType = data.get("beatType",None)
    class _FreeTrialPrivilege:
        def __init__(self,data):
            self.resConsumable = data.get("resConsumable",None)
            self.userConsumable= data.get("userConsumable",None)
            self.listenType= data.get("listenType",None)
            self.cannotListenReason= data.get("cannotListenReason",None)
            self.playReason= data.get("playReason",None)
            self.freeLimitTagType=data.get("freeLimitTagType",None)
    class _FreeTimeTrialPrivileg:
        def __init__(self,data):
            self.resConsumable = data.get("resConsumable",None)
            self.userConsumable= data.get("userConsumable",None)
            self.type = data.get("type",None)
            self.ramainTime = data.get("remainTime",None)
            
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)

async def search_song(session: aiohttp.ClientSession, keyword: str) -> List[Music]:
    log.debug(f"[搜索] 关键词：{keyword}")
    params = {
        "keywords": keyword,
        "type": "1",
        "MUSIC_U": COOKIE
    }
    url = f"{API_BASE}/search"
    async with session.get(url, params=params,headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        resp_json = await resp.json()
    result = resp_json.get("result", {})
    songs = result.get("songs", [])
    if not songs:
        log.debug("[搜索结果] 无歌曲")
        return None
    s = []
    for idx,song in enumerate(songs):
        if idx >= 20:
            break
        s.append(Music(song))
    return s

async def get_song_url(session: aiohttp.ClientSession, song_id) -> MusicItem:
    log.debug(f"[请求播放地址] id={song_id}")
    params = {"id": str(song_id),
            "MUSIC_U": COOKIE}
    async with session.get(f"{API_BASE}/song/url", params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        info = await resp.json()
    data_list = info.get("data", [])
    if not data_list:
        log.error("[播放地址] data为空")
        return None
    item = data_list[0]   # 列表第一个对象
    url = item.get("url")
    log.debug(f"[播放url] {url}")
    return MusicItem(item)

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
            return True
        except Exception as e:
            log.error(f"下载失败 {os.path.basename(save_path)}: {str(e)}")
            return False

async def get_songs_keyboard(song_info, music_id, start, end):
    page_songs:List[Music] = song_info[start-1 : end]

    msg = ''
    keyboard_rows = []
    current_buttons = []

    for rel_idx, song in enumerate(page_songs):
        artist_str = ""
        for artist in song.artists:
            artist_str += f"{artist.name} "

        msg += f"{start + rel_idx}.歌名:{song.name}, 歌手:{artist_str}\n"

        btn = {
            "id": f"bot_music_choose_{music_id}_{start + rel_idx}",
            "render_data": {
                "label": f"选{start + rel_idx}",
                "style": 4
            },
            "action": {
                "type": 1,
                "permission": {"type": 2},
                "data": f"music|select|{music_id}|{start + rel_idx}"
            }
        }
        current_buttons.append(btn)

        if len(current_buttons) >= 4:
            keyboard_rows.append({"buttons": current_buttons})
            current_buttons = []

    if current_buttons:
        keyboard_rows.append({"buttons": current_buttons})

    # 修复下一页判断：如果本页返回数量 == 切片最大数量，说明后面还有数据，显示下一页
    if len(page_songs) == (end - start +1):
        keyboard_rows.append({"buttons": [{
            "id": f"bot_music_choose_{music_id}_999999",
            "render_data": {
                "label": f"下一页",
                "style": 4
            },
            "action": {
                "type": 1,
                "permission": {"type": 2},
                "data": f"music|nextpage|{music_id}|{end+1}"
            }
        }]})

    keyboard = {"content": {"rows": keyboard_rows}}
    return msg, keyboard

async def main():
    connector = aiohttp.TCPConnector(limit=16)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0"
    }
    http_session = aiohttp.ClientSession(connector=connector, headers=headers)
    try:
        info = await search_song(http_session,'七里香')
        print(info[0].id)
        if info:
            msg, keyboard = await get_songs_keyboard(info,1, 1, 7)
            print(await get_song_url(http_session, info[0].id))

    finally:
        if not http_session.closed:
            await http_session.close()

if __name__ == '__main__':
    # 直接运行main的时候没有log，临时mock
    class MockLog:
        def debug(self,*a):print(*a)
        def error(self,*a):print(*a)
    log = MockLog()
    asyncio.run(main())
