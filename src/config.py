import os
import botpy
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIXIV_HEADERS = {
    "Referer": "https://www.pixiv.net/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
MAX_READ_SIZE = 180 * 1024 * 1024  # 180MB
# 仅图片下载使用这个带代理的session
PIXIV_PROXY = "http://127.0.0.1:12334"

with open(os.path.join(BASE_DIR,"json","setting.json"), "r", encoding="utf-8") as f:
    data = json.load(f)
    APPID = data.get("APPID")
    APPSECRET = data.get("APPSECRET")
    AIAPIKEY = data.get("AIAPIKEY")


log = botpy.logging.get_logger()
