from config import * 
from save import *
from AI import *
from load import *
from pixiv import *
from music import *

from botpy.message import C2CMessage, GroupMessage
from botpy.manage import GroupManageEvent, C2CManageEvent
from botpy.interaction import Interaction
from PIL import Image
from zai import ZhipuAiClient
from datetime import datetime, timedelta

import botpy
import re
import json
import random
import time
import asyncio
import os
import zoneinfo

MAX_RETRY = 5

ciallo_url = "https://ts2.tc.mm.bing.net/th/id/OIP-C.zOuxHjLVBFflqmmOx-6LAAHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3"

chat_json_file = os.path.join(BASE_DIR,"json","chat_list.json")
game_json_file = os.path.join(BASE_DIR,"json","game_list.json")
ban_json_file = os.path.join(BASE_DIR,"json","ban_list.json")

sound_path = os.path.join(BASE_DIR,"audio")
repeater_mode = {}
kards_is_connection = False
kards_mode = {'c2c':{},'group':{}}

song_event: dict[int, List[Music]] = {}
song_event_lock = asyncio.Lock()
song_id = 0

with open(os.path.join(BASE_DIR,"json","setting.json"), "r", encoding="utf-8") as f:
    data = json.load(f)
    APPID = data.get("APPID")
    APPSECRET = data.get("APPSECRET")
    AIAPIKEY = data.get("AIAPIKEY")

class MyBot(botpy.Client):
    async def on_ready(self):
        log.info("机器人上线成功，等待私聊消息...")

        # 创建全局session
        connector = aiohttp.TCPConnector(limit=16)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.http_session = aiohttp.ClientSession(connector=connector, headers=headers)


        # 定时任务
        asyncio.create_task(self.periodic_task(5)) 

        # 获取id
        resp = await self.api.me()
        self.app_id = resp.get("union_openid")
        if not self.app_id:
            self.app_id = "726B489C13804741B9AD1DCA6879CC45"
        log.info(f"app_id获取结果{self.app_id}")
  
    async def on_c2c_message_create(self, message: C2CMessage):
        user_openid = message.author.user_openid
        log.info(f"user_openid: {user_openid}")
        await add_data(item=user_openid,file=chat_json_file, chat_type=0)

        msg = [s.strip() for s in message.content if s.strip()]
        content = ''
        for m in msg:
            content += m
        log.info(f"消息内容: {content}")

        if message.attachments:
            attach_list = list(message.attachments)
            for attach in attach_list:
                if attach.content_type == 'file':
                    suffix = os.path.splitext(attach.filename)[1]
                    if suffix in ['.mp3', '.flac', '.wav']:
                        path = os.path.join(BASE_DIR, 'audio', attach.filename)
                        ok = await download_audio_async(attach.url, path)
                        if ok:
                            await message.reply(content=f'保存成功{attach.filename}')
                    elif suffix in [".m4a", ".aac", ".ogg", ".opus", ".ape", ".wv", ".wma"]:
                        await message.reply(content=f'不支持的格式,请转为.mp3/.flac/.wav后再试')

        # 自动回复
        if "/随机C图" == content:
            await self.send_cos_img(user_openid, 0)
        elif "/随机C帖" == content:
            await self.send_cos_tips(user_openid, 0)
        elif "早上好" == content  or "/问好" == content:
            msg = f"![text #500px #500px]({ciallo_url}) Ciallo～(∠・ω< )⌒★"
            await message.reply(msg_type = 2,markdown={'content':msg}, keyboard = self.main_menu)
        elif "/随机音效" == content:
            try:
                audio_path = await random_pick_audio(sound_path)
                log.debug(f"音频路径:{audio_path}")

                while True:
                    resp = await self.upload_file_in_parts(openid=user_openid, file_type=3, file_path=audio_path, chat_type=0)
                    if not resp.get('err_code'):
                        return
            except Exception as e:
                log.error(e)
        
        else:
            await get_ai_reply(AI_client,message, chat_type=0)

    async def on_friend_add(self,event: C2CManageEvent):
        user_openid = event.user_openid
        event_id = event.event_id
        log.info(f"新增好友：{user_openid}")
        # 存入私聊列表 type=0
        await self.api.post_c2c_message(openid=user_openid,
                                msg_type=2,
                                markdown={'content':"你好我是少女"},
                                keyboard = self.main_menu,
                                msg_id = event_id)
        await add_data(item=user_openid, file=chat_json_file, chat_type=0)

    async def on_friend_del(self,event: C2CManageEvent):
        user_openid = event.user_openid
        log.info(f"删除：{user_openid}")
        # 存入私聊列表 type=0
        await remove_data(data=user_openid, file=chat_json_file, chat_type=0)

    async def on_group_at_message_create(self, message: GroupMessage):
        group_openid = message.group_openid
        user_openid = message.author.member_openid
        msg_id = message.id
        abs_content = message.content
        msg = [s.strip() for s in message.content if s.strip()]
        content = ''
        for m in msg:
            content += m
        send_picture = False
        log.info(f"【群聊】at消息内容:{content}")
        if message.attachments:
            log.info(f"收到附件：{message.attachments}")
            send_picture = True

        
        if (content == "" or content == "/菜单") and not send_picture:
            msg = await self.get_msg(id=group_openid, msg="功能", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard=self.main_menu)     
        elif "/问好" == content:
            msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url}) Ciallo～(∠・ω< )⌒★", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = self.main_menu)
        elif "/随机C图" == content:
            await self.send_cos_img(group_openid,1,msg_id=msg_id)
        elif "/随机C帖" == content:
            await self.send_cos_tips(group_openid,1,msg_id=msg_id)
        elif "/复读机" == content:
            repeater_mode[group_openid] = True
            msg = await self.get_msg(id=group_openid, msg="已进入复读机,键入 /退出复读机 来退出", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = self.repeater_menu)
        elif content.startswith("/点歌"):
            raw_arg = abs_content[len("/点歌"):]
            song_key = raw_arg.strip()
            if not song_key:
                await message.reply(msg_type=2,markdown={'content':'格式错误,格式为<qqbot-cmd-input text="/点歌 七里香" show="@少女 /点歌 歌名" reference="false" />'})
                return

            global song_id
            song_id += 1 
            msg, keyboard, song_info = await get_songs_keyboard(self.http_session,song_key, song_id)
            song_event[song_id] = song_info
            await message.reply(msg_type=2, markdown={"content":msg}, keyboard=keyboard)

            
        elif "/ban" in content and user_openid == 'BA74A884C1DF8E78BFDAF8609AA84099':
            content = content.replace('/ban', '')

            ids = re.findall(r"<@([^>]+)>", content)
            msg = ''
            for id in ids:
                msg += f'<@{id}>'
                await add_data(file=ban_json_file,item=id,chat_type=group_openid)
                await self.api.restrict_chat_setting(group_openid=group_openid, members=[{'op':'add', 'member_openid': id, 'mute_expire_at': await self.get_rfc3339_shanghai_no_us(10)}])
            await message.reply(msg_type=2,markdown={'content':await self.get_msg(group_openid,f'以封禁'+ msg, 1)})

        elif "/deban" in content and user_openid == 'BA74A884C1DF8E78BFDAF8609AA84099':
            content = content.replace('/ban', '')

            ids = re.findall(r"<@([^>]+)>", content)
            msg = ''
            for id in ids:
                msg += f'<@{id}>'
                await remove_data(ban_json_file,id,group_openid)
                await self.api.restrict_chat_setting(group_openid=group_openid, members=[{'op':'del', 'member_openid': id}])
            await message.reply(msg_type=2,markdown={'content':await self.get_msg(group_openid,f'以解除封禁'+ msg, 1)})

        elif "/随机音效" == content:
            try:
                audio_path = await random_pick_audio(sound_path)
                log.debug(f"音频路径:{audio_path}")
                while True:
                    resp = await self.upload_file_in_parts(openid=group_openid, file_type=3, file_path=audio_path, chat_type=1)
                    await self.api.post_group_message(group_openid=group_openid,msg_type=7,media={'file_info':resp['file_info']})
                    if not resp.get('err_code'):
                        return
            except Exception as e:
                log.error(e)
                raise e

        # elif "/随机P图" == content:
        #     paths, title, push_time, _ = await self.get_p_pic()
        #     msg = ''
        #     for path in paths:
        #         await self.upload_file_in_parts(file_path=path, openid=group_openid, chat_type=1, file_type=1)
           
        #     msg += f"\n标题:{title}\n发布时间{push_time}\n"
            resp = await message.reply(msg_type=2,markdown={'content':msg},keyboard=self.cos_again_menu)
        # elif "/test" == content:
        #     await self.answer(group_openid, message.id,content)
        # elif '/test1' == content:
        #     r1 = random.randint(1,6)
        #     r2 = random.randint(1,6)
        #     r = r1 + r2
        #     if r == 3 or r == 5:
        #         await add_data(data={'id':group_openid,'time' : time.time(),'type':r}, file=game_json_file, chat_type=1)
        #         if r == 3:
        #             await message.reply(msg_type=2,markdown={'content':f"主人，掷骰子结果:{r1}+{r2}={r}"},msg_seq=1)
        #         else:
        #             await message.reply(msg_type=2,markdown={'content':f"掷骰子结果:{r1}+{r2}={r}喵~"},msg_seq=1)
        #     else:
        #         await message.reply(msg_type=2,markdown={'content':f"掷骰子结果:{r1}+{r2}={r}"},msg_seq=1)
            
        elif not '/' in content:
            await get_ai_reply(message,chat_type=1)
            ...

    async def on_group_message_create(self, message: GroupMessage):
        group_openid = message.group_openid
        user_openid = message.author.member_openid
        msg_id = message.id
        abs_content = message.content
        log.info(f"【群聊】群ID: {group_openid}")
        log.info(f"【群聊】群成员ID: {user_openid}")

        msg = [s.strip() for s in message.content if s.strip()]
        content = ''
        for m in msg:
            content += m
        message.content = content
        log.info(f"【群聊】消息内容: {content}")

        if user_openid in self.ban_id.get(group_openid, []):
            await message.cencel()
            await self.api.restrict_chat_setting(group_openid=group_openid, members=[{'op':'add', 'member_openid': user_openid, 'mute_expire_at': await self.get_rfc3339_shanghai_no_us(10)}])
            return

        if repeater_mode.get(group_openid) and user_openid != self.app_id:
            content = await self.repeater(message)
            if not content:
                msg = await self.get_msg(id=group_openid, msg="已退出复读机模式", chat_type=1)
                await self.api.post_group_message(group_openid=group_openid,
                                                msg_type=2,
                                                markdown={"content" : msg},
                                                keyboard=self.other_menu)
            else:
                msg = await self.get_msg(id=group_openid, msg=content, chat_type=1)
                await self.api.post_group_message(group_openid=group_openid,
                                                msg_type=2,
                                                markdown={"content" : msg},
                                                keyboard=self.repeater_menu)
            return

        if f"<@{self.app_id}>" in content:
            message.content = abs_content.replace('<@726B489C13804741B9AD1DCA6879CC45>', '')
            await self.on_group_at_message_create(message)

        elif "群主" in content :
            msg = await self.get_msg(id=group_openid, msg="检测到夸赞群主，群主大人举世无双，群主大人聪明绝顶，群主大人才华横溢，群主大人才智超群，群主大人绝顶聪明，群主大人风华绝代，群主大人锦心绣口，群主大人慧心巧思，群主大人才貌双绝，\
                                     让我们为群主高歌，群主的学识名垂千星，群主的名字响彻寰宇，群主的力量通天彻地！被ta敲醒沉睡的心灵，被ta解答心中的疑惑，被ta万千镜面照耀下，佩服的五体投地！ta就是我们伟大的神明，ta就是我们闪耀的光芒！让我们为群主传颂，", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg})
        elif "管理" in content :
                msg = await self.get_msg(id=group_openid, msg="检测到夸赞管理，管理大人举世无双，管理大人威武霸气，管理大人天下无敌，管理大人万岁万岁万万岁！", chat_type=1)
                await message.reply(msg_type=2,markdown={'content':msg})
        elif "早上好" in content:
            msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url}) Ciallo～(∠・ω< )⌒★", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg})

    async def on_group_add_robot(self, event:GroupManageEvent):
        group_openid = event.group_openid
        op_member = event.op_member_openid
        event_id = event.event_id
        log.info(f"机器人入群,群ID: {group_openid}")
        await self.api.post_group_message(group_openid=group_openid,
                                        msg_type=2,
                                        markdown={'content':"大家好我是少女"},
                                        keyboard = self.main_menu,
                                        msg_id = event_id)

        await add_data(item=group_openid, file=chat_json_file, chat_type=1)

    async def on_group_del_robot(self, event: GroupManageEvent):
        group_openid = event.group_openid
        op_member = event.op_member_openid
        event_id = event.event_id
        log.info(f"机器人退群,群ID: {group_openid}")
        await remove_data(data=group_openid, file=chat_json_file, chat_type=1)

    async def on_group_member_add(self, event: GroupManageEvent):
        group_openid = event.group_openid
        user_openid = event.member_openid
        await add_data(item=user_openid, file=chat_json_file, chat_type=1)
        self.api.post_group_message(group_openid=group_openid, content='欢迎新人')

    async def on_group_member_remove(self, event: GroupManageEvent):
        group_openid = event.group_openid
        user_openid = event.member_openid
        await remove_data(item=user_openid, file=chat_json_file, chat_type=1)

    async def on_close(self, code: int, reason: str):
        log.warning(f"【机器人下线】连接关闭 code:{code} 原因:{reason}")
        users = await get_all_data(file=chat_json_file, chat_type=0)
        groups = await get_all_data(file=chat_json_file, chat_type=1)
        for id in users:
            pass
            #await asyncio.to_thread(send_c2c_only_message,id,"重启中...")
        for id in groups:
            pass
            #await asyncio.to_thread(send_group_with_button,id,"重启中...")

    async def on_interaction_create(self, interaction:Interaction):
        await interaction.react()
        if interaction.data.type == 11:
            if interaction.chat_type == 1:
                group_openid = interaction.group_openid
                user_id = interaction.group_member_openid
                await add_data(item=group_openid, file=chat_json_file, chat_type=1)
                data = interaction.data.resolved.button_id
                log.info(f"{user_id}按下{data}")
                if data == 'bot_say_hello':
                    msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url})\n<qqbot-at-user id=\"{user_id}\" /> Ciallo～(∠・ω< )⌒★", chat_type=1)
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':msg},
                                                    keyboard = self.main_menu)
                    
                elif data == 'bot_random_cos':
                    await self.send_cos_img(group_openid,1, user_id = user_id)

                elif data == 'bot_random_cos_tips':
                    await self.send_cos_tips(group_openid, 1,user_id = user_id)

                elif data == 'bot_random_p':
                    await self.send_p_img(group_openid, 1, user_id=user_id)

                elif data == 'bot_menu':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"功能<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = self.main_menu)
                    
                elif data == 'bot_pic_menu':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"功能<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = self.pic_menu)
                elif data == 'bot_music_menu':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"功能<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = self.music_menu)
                    
                elif data == 'bot_other_menu':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"功能<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = self.other_menu)

                elif data == 'bot_kards':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"请在私聊中使用<qqbot-at-user id=\"{user_id}\" />", chat_type=0)},)

                elif data.startswith('bot_music_choose'):

                    parts = data.split("_")
                    song_id = int(parts[-2])
                    choose_id = int(parts[-1])

                    async with song_event_lock:
                        if song_id not in song_event:
                            self.api.post_group_message(group_openid=group_openid, content='请重新点歌')
                        song_info = song_event[song_id]
                        # 修复：按钮序号从1开始，列表下标从0开始！
                        target_idx = choose_id - 1
                        if not (0 <= target_idx < len(song_info)):
                            return
                        song = song_info[target_idx]
                        # 使用完毕立刻清理缓存
                        song_event.pop(song_id, None)

                    # 开始下载歌曲，复用全局session
                    track_name = sanitize_filename(song.name)
                    artists = sanitize_filename(song.artist_string)
                    os.makedirs(SAVE_ROOT, exist_ok=True)
                    save_path = os.path.join(SAVE_ROOT, f"{track_name} - {artists}.mp3")
                    url = await get_song_url(self.http_session, song.id)
                    await download_single(self.http_session, url, save_path)

                    log.info(save_path)
                    if not save_path:
                        await self.api.post_group_message(group_openid=group_openid,content="未找到歌曲或无法获取音源链接", msg_seq=1)
                        return
                    await self.api.post_group_message(group_openid=group_openid,msg_type=2,markdown={'content':f'正在下载歌曲:\n名称:{song.name}\n歌手:{song.artists}'}, msg_seq=1)
                    resp = await self.upload_file_in_parts(file_path=save_path, openid=group_openid, chat_type=1, file_type=3)
                    if resp:
                        await self.api.post_group_message(group_openid=group_openid,msg_type=7,media={'file_info':resp['file_info']}, msg_seq=2)
                    else:
                        await self.api.post_group_message(group_openid=group_openid,content='发送失败', msg_seq=2)

                elif interaction.chat_type == 2:
                    user_openid = interaction.user_openid
                    data = interaction.data.resolved.button_id
                    await add_data(item=user_openid, file=chat_json_file, chat_type=0)
                    log.info(f"{user_openid}按下{data},时间{time.time()}")
                    await self.c2c_interaction(user_openid, data)

    # 自定义

    async def periodic_task(self,interval: int):
        """
        interval：间隔秒数
        """
        while True:
            try:
                # 这里写你的定时业务逻辑
                log.debug("定时任务执行")
                
                # ======================
                # 禁止 time.sleep()！必须 await asyncio.sleep
                # ======================
                with open(os.path.join(BASE_DIR, 'json', 'cos_all.json'), "r", encoding="utf-8") as f:
                    self.cos_data = json.load(f)
                # 读取菜单
                with open(os.path.join(BASE_DIR, 'json', 'menu.json'), "r", encoding="utf-8") as f:
                    self.main_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'pic_menu.json'), "r", encoding="utf-8") as f:
                    self.pic_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'music_menu.json'), "r", encoding="utf-8") as f:
                    self.music_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'other_menu.json'), "r", encoding="utf-8") as f:
                    self.other_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'repeater_menu.json'), "r", encoding="utf-8") as f:
                    self.repeater_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'cos_again_menu.json'), "r", encoding="utf-8") as f:
                    self.cos_again_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'cos_tips_again_menu.json'), "r", encoding="utf-8") as f:
                    self.cos_tips_again_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'pixiv_again_menu.json'), "r", encoding="utf-8") as f:
                    self.p_again_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'kards.json'), "r", encoding="utf-8") as f:
                    self.kards_menu = json.load(f)
                with open(os.path.join(BASE_DIR, 'json', 'ban_list.json'), "r", encoding="utf-8") as f:
                    self.ban_id = json.load(f)
            except Exception as e:
                # 捕获异常，防止任务崩溃导致整个定时终止
                log.error(f"定时任务异常: {e}")
                
            await asyncio.sleep(interval)

    async def send_cos_tips(self,openid, chat_type, **kwargs):
        """
        发送cos帖

        :param openid:发送的openid
        :param type: 0向私聊发送,1向群聊发送
        """
                
        cos = random.choice(self.cos_data)
        # tip = tips[110]
        log.info(f"找到的帖子{cos}")
        urls = cos["urls"]
        title = cos["title"]
        time = cos["publish_time"]
        msg = ""
        if urls[0]["width"] == 0:
            k = True
        else:
            k = False
        for url in urls:
            msg += f"![text #{url["width"]}px #{url["height"]}px]({url["url"]})\n"
            if k:
                if chat_type == 0:
                    await self.api.post_c2c_file(openid=openid,file_type=1,url=url,srv_send_msg=True)
                elif chat_type == 1:
                    await self.api.post_group_file(group_openid=openid, file_type=1,url=url,srv_send_msg=True)
                    
        user_id = kwargs.get("user_id", None)
        if user_id is not None:
            msg += f"<qqbot-at-user id=\"{user_id}\" />\n"
        msg += f"标题:{title}\n发布时间{time}\n"

        msg  = await self.get_msg(id=openid, msg=msg, chat_type=chat_type)

        if k:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':f"标题:{title}\n发布时间{time}\n"},keyboard=self.cos_tips_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':f"标题:{title}\n发布时间{time}\n"},keyboard=self.cos_tips_again_menu)
        else:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.cos_tips_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.cos_tips_again_menu)

    async def send_cos_img(self,openid, chat_type, **kwargs):
        """
        发送cos图

        :param openid:发送的openid
        :param chat_type: 0向私聊发送,1向群聊发送
        """
                
        cos = random.choice(self.cos_data)
        # tip = tips[110]
        log.info(f"找到的帖子{cos}")
        urls = cos["urls"]
        title = cos["title"]
        time = cos["publish_time"]
        msg = ""
        if urls[0]["width"] == 0:
            k = True
        else:
            k = False
        url = random.choice(urls)
        log.info(f"找到的图{url}")
        msg += f"![text #{url["width"]}px #{url["height"]}px]({url["url"]})\n"
        if k:
            if type == 0:
                await self.api.post_c2c_file(openid=openid,file_type=1,url=url,srv_send_msg=True)
            elif type == 1:
                await self.api.post_group_file(group_openid=openid, file_type=1,url=url,srv_send_msg=True)
                            
        user_id = kwargs.get("user_id", None)
        if user_id is not None:
            msg += f"<qqbot-at-user id=\"{user_id}\" />"

        msg = await self.get_msg(id=openid, msg=msg, chat_type=chat_type)

        if k:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':f"\n"},keyboard=self.cos_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':f"\n"},keyboard=self.cos_again_menu)
        else:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.cos_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.cos_again_menu)

    async def send_p_img(self,openid, chat_type, **kwargs):
        """
        发送cos图

        :param openid:发送的openid
        :param chat_type: 0向私聊发送,1向群聊发送
        """
                
        urls, title, create_time, illust_id = await get_pixiv_pic()
        for idx, url in enumerate(urls):
            ext = url.split(".")[-1].split("?")[0]
            save_name = f"{illust_id}_p{idx}.{ext}"
            save_full_path = os.path.join(pixiv_path, save_name)
            if not os.path.exists(save_full_path):
                ok = await download_pixiv_image(save_full_path, url)
                if not ok:
                    log.warning(f"第p{idx} 图片下载失败，跳过")
                    continue
                else:
                    resp = await self.upload_file_in_parts(file_path=save_full_path, openid=openid, chat_type=chat_type, file_type=1)
                    if chat_type == 0:
                        resp = await self.api.post_c2c_message(openid=openid,msg_type=7,media={'file_info':resp['file_info']})
                    elif chat_type == 1:       
                        resp = await self.api.post_group_message(group_openid=openid,msg_type=7,media={'file_info':resp['file_info']})
                                         
        
        if all((urls, title, create_time)):
            msg = ''
            user_id = kwargs.get("user_id", None)
            if user_id is not None:
                msg += f"<qqbot-at-user id=\"{user_id}\" />\n"
            msg += f"标题:{title}\n发布时间{create_time}\n"

            if chat_type == 0:
                resp = await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.p_again_menu)
            elif chat_type == 1:       
                resp = await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':msg},keyboard=self.p_again_menu)
                                
    async def repeater(self,message:C2CMessage|GroupMessage,**kwargs):
        content = message.content
        if content == f"<@{self.app_id}>/退出复读机":
            log.info("解除复读")
            repeater_mode[message.group_openid] = False
            return 


        # 有附件（图片/表情）
        if message.attachments:
            log.info(f"收到附件：{message.attachments}")
            attach_list = list(message.attachments)

            urls = []
            tag_list = re.findall(r'<faceType=6[^>]*>', content)
            for attach in attach_list:
                url = attach.url
                w =attach.width
                h = attach.height
                urls.append(f"![text #{w}px #{h}px]({url})")
            log.info(f"tag_list={tag_list}, urls={urls}")
            rules = list(zip(tag_list, urls))
            log.info(f"{rules=}")
            for old, new in rules:
                content = content.replace(old, new)
            log.info(f"{content=}")
            if not tag_list:
                for url in urls:
                    content += url

        return content

    async def c2c_interaction(self,user_openid,data,**kwargs):
        if data == 'bot_say_hello':
            msg = f"![text #500px #500px]({ciallo_url}) Ciallo～(∠・ω< )⌒★"
            await self.api.post_c2c_message(openid=user_openid,
                                            msg_type=2,
                                            markdown={'content':msg},
                                            keyboard = self.main_menu)

        elif data == 'bot_random_cos':
            await self.send_cos_img(user_openid, 0)

        elif data == 'bot_random_cos_tips':
            await self.send_cos_tips(user_openid, 0)

        elif data == 'bot_random_p':
            await self.send_p_img(user_openid, 0)

        elif data == 'bot_menu':
            if user_openid in kards_mode['c2c']:
                kards_mode['c2c'][user_openid] = {}
            await self.api.post_c2c_message(openid=user_openid,
                        msg_type=2,
                        markdown={'content':f"功能"},
                        keyboard = self.main_menu)

        elif data == 'bot_pic_menu':
            await self.api.post_c2c_message(openid=user_openid,
                        msg_type=2,
                        markdown={'content':f"功能"},
                        keyboard = self.pic_menu)
        elif data == 'bot_music_menu':
            await self.api.post_c2c_message(openid=user_openid,
                        msg_type=2,
                        markdown={'content':f"功能"},
                        keyboard = self.music_menu)
            
        elif data == 'bot_other_menu':
            await self.api.post_c2c_message(openid=user_openid,
                        msg_type=2,
                        markdown={'content':f"功能"},
                        keyboard = self.other_menu)
        

        elif data == 'bot_kards':
            first = random.randint(0, 1)
            if first == 0:
                kards_mode['c2c'][user_openid] = {'me':1,'enemy':0,'now_turn':0}
                msg = f'你是先手\n'
            else:
                kards_mode['c2c'][user_openid] = {'me':0,'enemy':1,'now_turn':1}
                msg = f'敌方先手\n'
            point_text = f"指挥点槽:\n你:{kards_mode['c2c'][user_openid]['me']}\n敌人:{kards_mode['c2c'][user_openid]['enemy']}"
            await self.api.post_c2c_message(openid=user_openid,
                                            msg_type=2,
                                            markdown={'content':msg + point_text},
                                            keyboard = self.kards_menu)

        elif data == 'kards_enter_turn':
            # 校验对局是否存在
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = self.other_menu)
                return
            game_data = kards_mode['c2c'][user_openid]
            if game_data['now_turn'] == 0:
                if game_data['enemy'] < 12:
                    game_data['enemy'] += 1
                    game_data['now_turn'] = 1
                msg = '敌方回合'
            else:
                if game_data['me'] < 12:
                    game_data['me'] += 1
                    game_data['now_turn'] = 0
                msg = '我方回合'

            point_text = f"指挥点槽:\n你:{game_data['me']}\n敌人:{game_data['enemy']}"
            await self.api.post_c2c_message(openid=user_openid,
                                            msg_type=2,
                                            markdown={'content':msg + "\n" + point_text},
                                            keyboard = self.kards_menu)

        elif data == 'kards_add_com_point':
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = self.other_menu)
                return
            game_data = kards_mode['c2c'][user_openid]
            if game_data['now_turn'] == 0:
                if game_data['me'] < 24:
                    game_data['me'] += 1
                msg = '我方回合'
            else:
                if game_data['enemy'] < 24:
                    game_data['enemy'] += 1
                msg = '敌方回合'
            point_text = f"指挥点槽:\n你:{game_data['me']}\n敌人:{game_data['enemy']}"
            await self.api.post_c2c_message(openid=user_openid,
                                            msg_type=2,
                                            markdown={'content':msg+'\n'+point_text},
                                            keyboard = self.kards_menu)

        elif data == 'kards_sub_com_point':
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = self.other_menu)
                return
            game_data = kards_mode['c2c'][user_openid]
            if game_data['now_turn'] == 0:
                if game_data['me'] > 0:
                    game_data['me'] -= 1
                msg = '我方回合'
            else:
                if game_data['enemy'] > 0:
                    game_data['enemy'] -= 1
                msg = '敌方回合'

            point_text = f"指挥点槽:\n你:{game_data['me']}\n敌人:{game_data['enemy']}"
            await self.api.post_c2c_message(openid=user_openid,
                                            msg_type=2,
                                            markdown={'content':msg+'\n'+point_text},
                                            keyboard = self.kards_menu)

    async def get_msg(self,id, msg, chat_type):
        if chat_type == 1:
            datas = await get_all_data(file=game_json_file, chat_type=1)
            data = []
            for d in datas:
                if d['id'] == id:
                    data.append(d)
            if data:
                for d in data:
                    if time.time() - d['time'] > 3600 * 24:
                        await remove_data(data=d, file=game_json_file, chat_type=1)
                    else:
                        if d['type'] == 3:
                            msg += '主人'
                        if d['type'] == 5:
                            msg += '喵~'
        return msg

    async def get_img_size_local(self, file_path: str):
        def _inner():
            with Image.open(file_path) as img:
                return img.width, img.height
        return await asyncio.to_thread(_inner)

    async def upload_file_in_parts(self, file_path, openid, chat_type, file_type):
        file_full_name = os.path.basename(file_path)

        md5, sha1 = get_file_hash(file_path)
        md5_10m = get_head_md5_sync(file_path)
        # 异步获取文件大小，不阻塞事件循环
        file_size = str(await asyncio.to_thread(os.path.getsize, file_path))

        upload_id = None
        parts = None

        # 1. 初始化分片任务
        if chat_type == 0:
            resp = await self.api.post_c2c_file_prepear(
                openid=openid,
                file_type=file_type,
                file_name=file_full_name,
                file_size=file_size,
                md5=md5,
                sha1=sha1,
                md5_10m=md5_10m
            )
            upload_id = resp['upload_id']
            parts = resp['parts']
        elif chat_type == 1:
            resp = await self.api.post_group_file_prepear(
                group_openid=openid,
                file_type=file_type,
                file_name=file_full_name,
                file_size=file_size,
                md5=md5,
                sha1=sha1,
                md5_10m=md5_10m
            )
            upload_id = resp['upload_id']
            parts = resp['parts']
        else:
            raise ValueError("chat_type 只能为0(私聊)或1(群聊)")

        # 2. 循环上传所有分片
        offset = 0
        for p in parts:
            index = p['index']
            url = p['presigned_url']
            blk_sz = int(p['block_size'])

            chunk_bytes = await get_file_chunk(file_path, offset, offset + blk_sz)
            await upload_chunk(url, chunk_bytes)  # 现在带重试

            md5_p = hashlib.md5(chunk_bytes).hexdigest()

            if chat_type == 0:
                await self.api.post_c2c_file_finish(
                    openid=openid,
                    upload_id=upload_id,
                    part_index=index,
                    block_size=blk_sz,
                    md5=md5_p
                )
            else:
                await self.api.post_group_file_finish(
                    group_openid=openid,
                    upload_id=upload_id,
                    part_index=index,
                    block_size=blk_sz,
                    md5=md5_p
                )
            offset += blk_sz

        try:
            if chat_type == 0:
                final_resp = await self.api.post_c2c_file(
                    openid=openid,
                    file_type=file_type,
                    upload_id=upload_id,
                )
            else:
                final_resp = await self.api.post_group_file(
                    group_openid=openid,
                    file_type=file_type,
                    file_name=file_full_name,
                    upload_id=upload_id,
                )
            return final_resp
        except aiohttp.ClientError:
            print("【警告】合并分片请求超时！")
            # 重点：
            # 很多时候超时 ≠ 后台合并失败，只是响应回不来
            # 这里谨慎处理，不要直接return None导致提示“发送失败”
            # 策略选择：
            # 策略A（保守）：返回None，提示用户上传可能失败
            return None
            # 策略B（激进）：假装成功，让用户等待一段时间观察群内是否出现音频
            # return {"file_info": None}
        except botpy.errors.ServerError as e:
            err_msg = str(e)
            print("合并分片服务端错误：", err_msg)
            return None

    async def get_rfc3339_shanghai_no_us(self,offset_minutes: int = 0) -> str:
        tz = zoneinfo.ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        target = now + timedelta(minutes=offset_minutes)
        # 格式化，先拿到 %z 形式 +0800
        raw = target.strftime("%Y-%m-%dT%H:%M:%S%z")
        # 把 +0800 → +08:00
        t_part = raw[:-5]
        offset = raw[-5:]
        return f"{t_part}{offset[:3]}:{offset[3:]}"

if __name__ == "__main__":

    AI_client = ZhipuAiClient(api_key=AIAPIKEY)
    intents = botpy.Intents(public_messages=True,public_guild_messages=True,interaction=True)
    QQ_client = MyBot(intents=intents, timeout=60,ext_handlers=True)
    #print("当前handler列表：", log.handlers)
    QQ_client.run(appid=APPID, secret=APPSECRET)