from pixivpy3 import AppPixivAPI
from config import * 

import asyncio
import requests
import json
import random
import os
import aiohttp

pixiv_aio_session: aiohttp.ClientSession | None = None


pixiv_path = os.path.join(BASE_DIR,"pixiv")

# 粘贴你从json里提取的refresh_token
with open('json/pixiv_auth.json', 'r', encoding='utf-8') as f:
    refresh_token_str = json.load(f)['refresh_token']

# 自定义带代理的请求包装器
class PixivProxySession:
    def __init__(self, proxy_url="http://127.0.0.1:12334"):
        self.proxy = {
            "http": proxy_url,
            "https": proxy_url
        }
        self.session = requests.Session()

    def get(self, url, **kwargs):
        kwargs["proxies"] = self.proxy
        return self.session.get(url,** kwargs)

    def post(self, url, **kwargs):
        kwargs["proxies"] = self.proxy
        return self.session.post(url, **kwargs)

async def get_pixiv_session() -> aiohttp.ClientSession:
    global pixiv_aio_session
    if pixiv_aio_session is None or pixiv_aio_session.closed:
        pixiv_aio_session = aiohttp.ClientSession()
    return pixiv_aio_session

async def get_pixiv_pic_url():
    max_loop = 15
    loop_count = 0
    while loop_count < max_loop:
        loop_count += 1
        # 每次循环新建API实例，规避session腐化！
        def create_and_search():
            api = AppPixivAPI()
            api.requests = PixivProxySession()
            api.auth(refresh_token=refresh_token_str)
            keywords = [
                "原神 Q版 -水着 -露出 -エロ",
                "原神 日常 -水着 -露出 -エロ",
                "少女 日常 -水着 -露出 -エロ",
            ]
            target_word = random.choice(keywords)
            return api, api.search_illust(word=target_word)
        
        try:
            api,search_data = await asyncio.to_thread(create_and_search)
        except Exception as e:
            log.error(f"搜索异常:{e}")
            await asyncio.sleep(2)
            continue
        
        illust_list = search_data.illusts
        if illust_list is None or len(illust_list) == 0:
            log.warning("pixiv搜索无结果，illust_list为None/空，等待重试")
            await asyncio.sleep(2.5)
            continue
        

        rand_illust = random.choice(illust_list)
        try:
            res = await asyncio.to_thread(api.illust_detail, rand_illust.id)
        except Exception as e:
            log.error(f"获取作品详情异常: {e}")
            await asyncio.sleep(1.5)
            continue
        illust = res.illust

        if not illust.visible or "limit_unknown_360.png" in illust.image_urls.large:
            log.info("内容获取失败：当前账号无权限访问该作品")
        else:
            if illust.sanity_level <= 2 and illust.x_restrict == 0:
                break
            else:
                log.info("内容获取失败：评级过大")
        await asyncio.sleep(1)

    else:
        log.error("达到最大搜索重试次数，未找到符合条件插画")

    return illust

async def download_pixiv_image(save_path: str, img_url: str, max_retry: int = 3) -> bool:
    session = await get_pixiv_session()
    for attempt in range(max_retry):
        try:
            async with session.get(
                img_url,
                headers=PIXIV_HEADERS,
                proxy=PIXIV_PROXY,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                resp.raise_for_status()
                data = await resp.read()
                with open(save_path, "wb") as f:
                    f.write(data)
            return True
        except Exception as e:
            log.warning(f"图片下载第{attempt+1}次失败 {img_url} | {e}")
            if attempt != max_retry - 1:
                await asyncio.sleep(1.0)
    log.error(f"图片下载彻底失败 {img_url}")
    return False

async def get_pixiv_pic() :
    illust = await get_pixiv_pic_url()
    title = illust.title
    create_time = illust.create_date
    
    urls = []
    log.info(f"评级:{illust.sanity_level}")
    if illust.meta_single_page:
        # 单张图
        log.info(f"获取成功，原图地址：{illust.meta_single_page.original_image_url}")
        urls.append(illust.meta_single_page.original_image_url)
    elif illust.meta_pages:
        # 多页漫画循环取每一页原图
        log.info(f"获取成功，原图地址：{illust.meta_pages}")
        for page in illust.meta_pages:
            urls.append(page.image_urls.original)
    

    return urls, title, create_time, illust.id