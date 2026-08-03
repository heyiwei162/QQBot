import botpy
from botpy.message import C2CMessage, GroupMessage
from botpy.manage import GroupManageEvent
from botpy.interaction import Interaction
from botpy.client import _log
from bot import *

class MyBot(botpy.Client):

    async def on_ready(self):
        _log.info("机器人上线成功，等待私聊消息...")
        self.api

if __name__ == "__main__":
    
    intents = botpy.Intents(public_messages=True, interaction=True)
    client = MyBot(intents=intents)
    client.run(appid=APPID, secret=APPSECRET)