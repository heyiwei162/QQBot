import botpy
from botpy.message import C2CMessage, GroupMessage
from botpy.manage import GroupManageEvent
from botpy.interaction import Interaction
from botpy.client import _log
import re,json,random,time

from save import *
from search import search_by_text

MAX_RETRY = 5

pattern = r'(?:^|>)([^<>]+)(?:<|$)'
ciallo_url = "https://ts2.tc.mm.bing.net/th/id/OIP-C.zOuxHjLVBFflqmmOx-6LAAHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3"
chat_json_file = "./json/chat_list.json"
game_json_file = "./json/game_list.json"

repeater_mode = {}
kards_is_connection = False
kards_mode = {'c2c':{},
              'group':{}}


with open("./cos_all.json", "r", encoding="utf-8") as f:
    cos_data = json.load(f)

# 读取菜单
with open("./json/menu.json", "r", encoding="utf-8") as f:
    main_menu = json.load(f)
with open("./json/repeater_menu.json", "r", encoding="utf-8") as f:
    repeater_menu = json.load(f)
with open("./json/cos_again_menu.json", "r", encoding="utf-8") as f:
    cos_again_menu = json.load(f)
with open("./json/cos_tips_again_menu.json", "r", encoding="utf-8") as f:
    cos_tips_again_menu = json.load(f)
with open("./json/kards.json", "r", encoding="utf-8") as f:
    kards_menu = json.load(f)
with open("./json/setting.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    APPID = data.get("APPID")
    APPSECRET = data.get("APPSECRET")

class MyBot(botpy.Client):
    async def on_ready(self):
        _log.info("机器人上线成功，等待私聊消息...")
        self.app_id = await self.api.me().get('union_openid')
        if not self.app_id:
            self.app_id = "726B489C13804741B9AD1DCA6879CC45"
        _log.info(f"app_id获取结果{self.app_id}")
        users = await get_all_data(file=chat_json_file, chat_type=0)
        groups = await get_all_data(file=chat_json_file, chat_type=1)
        msg = f"![text #500px #500px]({ciallo_url}) 已上线!"
        for id in users:
            await self.api.post_c2c_message(openid=id, msg_type=2, markdown={'content':msg}, keyboard=main_menu)
        for id in groups:
            #await self.api.post_group_message(group_openid=id, msg_type=2, markdown={'content':msg}, keyboard=main_menu)
            ...
        
    async def on_c2c_message_create(self, message: C2CMessage):
        user_openid = message.author.user_openid
        _log.info(f"user_openid: {user_openid}")
        await add_data(data=user_openid, chat_type=0)

        msg = [s.strip() for s in message.content if s.strip()]
        content = ''
        for m in msg:
            content += m
        _log.info(f"消息内容: {content}")

        # 自动回复
        if "/随机C图" == content:
            await self.send_cos_img(user_openid, 0)
        elif "/随机C帖" == content:
            await self.send_cos_tips(user_openid, 0)
        elif "早上好" == content  or "/问好" == content:
            msg = f"![text #500px #500px]({ciallo_url}) Ciallo～(∠・ω< )⌒★"
            await message.reply(msg_type = 2,markdown={'content':msg}, keyboard = main_menu)
        else:
            await message.reply(msg_type = 2,markdown={'content':"功能"}, keyboard = main_menu)

    async def on_friend_add(self,event):
        user_openid = event.user_openid
        _log.info(f"新增好友：{user_openid}")
        # 存入私聊列表 type=0
        await add_data(data=user_openid, file=chat_json_file, chat_type=0)

    async def on_friend_del(self,event):
        user_openid = event.user_openid
        _log.info(f"删除：{user_openid}")
        # 存入私聊列表 type=0
        await remove_data(data=user_openid, file=chat_json_file, chat_type=0)

    async def on_group_at_message_create(self, message: GroupMessage):
        group_openid = message.group_openid
        user_openid = message.author.member_openid
        msg_id = message.id
        content = message.content
        send_picture = False
        _log.info(f"【群聊】at消息内容:{content}")
        if message.attachments:
            _log.info(f"收到附件：{message.attachments}")
            send_picture = True

        
        if (content == "" or content == "/菜单") and not send_picture:
            msg = await self.get_msg(id=group_openid, msg="功能", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard=main_menu)     
        elif "/问好" == content:
            msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url}) Ciallo～(∠・ω< )⌒★", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = main_menu)
        elif "/随机C图" == content:
            await self.send_cos_img(group_openid,user_openid,1,msg_id=msg_id)
        elif "/随机C帖" == content:
            await self.send_cos_tips(group_openid,1,msg_id=msg_id)
        elif "/复读机" == content:
            repeater_mode[group_openid] = True
            msg = await self.get_msg(id=group_openid, msg="已进入复读机,键入 /退出复读机 来退出", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = repeater_menu)
        elif "/test" == content:
            await self.answer(group_openid, message.id,content)
        elif '/test1' == content:
            r1 = random.randint(1,6)
            r2 = random.randint(1,6)
            r = r1 + r2
            if r == 3 or r == 5:
                await add_data(data={'id':group_openid,'time' : time.time(),'type':r}, file=game_json_file, chat_type=1)
                if r == 3:
                    await message.reply(msg_type=2,markdown={'content':f"主人，掷骰子结果:{r1}+{r2}={r}"},msg_seq=1)
                else:
                    await message.reply(msg_type=2,markdown={'content':f"掷骰子结果:{r1}+{r2}={r}喵~"},msg_seq=1)
            else:
                await message.reply(msg_type=2,markdown={'content':f"掷骰子结果:{r1}+{r2}={r}"},msg_seq=1)

    async def on_group_message_create(self, message: GroupMessage):
        group_openid = message.group_openid
        user_openid = message.author.member_openid
        msg_id = message.id
        _log.info(f"【群聊】群ID: {group_openid}")
        _log.info(f"【群聊】群成员ID: {user_openid}")

        msg = [s.strip() for s in message.content if s.strip()]
        content = ''
        for m in msg:
            content += m
        message.content = content
        _log.info(f"【群聊】消息内容: {content}")

        if repeater_mode.get(group_openid) and user_openid != self.app_id:
            content = await self.repeater(message)
            if not content:
                msg = await self.get_msg(id=group_openid, msg="已退出复读机模式", chat_type=1)
                await self.api.post_group_message(group_openid=group_openid,
                                                msg_type=2,
                                                markdown={"content" : msg},
                                                keyboard=main_menu)
            else:
                msg = await self.get_msg(id=group_openid, msg=content, chat_type=1)
                await self.api.post_group_message(group_openid=group_openid,
                                                msg_type=2,
                                                markdown={"content" : msg},
                                                keyboard=repeater_menu)
            return

        if f"<@{self.app_id}>" in content:
            content = re.sub(r"<@[0-9A-Za-z]+>", "", content).strip()
            message.content = content
            await self.on_group_at_message_create(message)

        elif "群主" in content :
            msg = await self.get_msg(id=group_openid, msg="检测到夸赞群主，群主大人举世无双，群主大人威武霸气，群主大人天下无敌，群主大人万岁万岁万万岁！", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = main_menu)
        elif "早上好" in content:
            msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url}) Ciallo～(∠・ω< )⌒★", chat_type=1)
            await message.reply(msg_type=2,markdown={'content':msg}, keyboard = main_menu)

    async def on_group_add_robot(self, event:GroupManageEvent):
        group_openid = event.group_openid
        op_member = event.op_member_openid
        event_id = event.event_id
        _log.info(f"机器人入群,群ID: {group_openid}")
        await self.api.post_group_message(group_openid=group_openid,
                                        msg_type=2,
                                        markdown={'content':"大家好我是少女"},
                                        keyboard = main_menu,
                                        msg_id = event_id)

        await add_data(data=group_openid, file=chat_json_file, chat_type=1)

    async def on_group_del_robot(self, event):
        group_openid = event.group_openid
        op_member = event.op_member_openid
        event_id = event.event_id
        _log.info(f"机器人退群,群ID: {group_openid}")
        await remove_data(data=group_openid, file=chat_json_file, chat_type=1)

    async def on_close(self, code: int, reason: str):
        _log.warning(f"【机器人下线】连接关闭 code:{code} 原因:{reason}")
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
                await add_data(data=group_openid, file=chat_json_file, chat_type=1)
                data = interaction.data.resolved.button_id
                _log.info(f"{user_id}按下{data}")
                if data == 'bot_say_hello':
                    msg = await self.get_msg(id=group_openid, msg=f"![text #300px #300px]({ciallo_url})\n<qqbot-at-user id=\"{user_id}\" /> Ciallo～(∠・ω< )⌒★", chat_type=1)
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':msg},
                                                    keyboard = main_menu)
                    
                elif data == 'bot_random_cos':
                    await self.send_cos_img(group_openid,1, user_id = user_id)

                elif data == 'bot_random_cos_tips':
                    await self.send_cos_tips(group_openid, 1,user_id = user_id)

                elif data == 'bot_menu':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"功能<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = main_menu)

                elif data == 'bot_kards':
                    await self.api.post_group_message(group_openid=group_openid,
                                                    msg_type=2,
                                                    markdown={'content':await self.get_msg(id=group_openid, msg=f"请在私聊中使用<qqbot-at-user id=\"{user_id}\" />", chat_type=1)},
                                                    keyboard = main_menu)

            elif interaction.chat_type == 2:
                user_openid = interaction.user_openid
                data = interaction.data.resolved.button_id
                await add_data(data=user_openid, file=chat_json_file, chat_type=0)
                _log.info(f"{user_openid}按下{data},时间{time.time()}")
                await self.c2c_interaction(user_openid, data)

    async def send_cos_tips(self,openid, chat_type, **kwargs):
        """
        发送cos帖

        :param openid:发送的openid
        :param type: 0向私聊发送,1向群聊发送
        """
                
        cos = random.choice(cos_data)
        # tip = tips[110]
        _log.info(f"找到的帖子{cos}")
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
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':f"标题:{title}\n发布时间{time}\n"},keyboard=cos_tips_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':f"标题:{title}\n发布时间{time}\n"},keyboard=cos_tips_again_menu)
        else:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':msg},keyboard=cos_tips_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':msg},keyboard=cos_tips_again_menu)

    async def send_cos_img(self,openid, chat_type, **kwargs):
        """
        发送cos图

        :param openid:发送的openid
        :param chat_type: 0向私聊发送,1向群聊发送
        """
                
        cos = random.choice(cos_data)
        # tip = tips[110]
        _log.info(f"找到的帖子{cos}")
        urls = cos["urls"]
        title = cos["title"]
        time = cos["publish_time"]
        msg = ""
        if urls[0]["width"] == 0:
            k = True
        else:
            k = False
        url = random.choice(urls)
        _log.info(f"找到的图{url}")
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
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':f"\n"},keyboard=cos_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':f"\n"},keyboard=cos_again_menu)
        else:
            if chat_type == 0:
                await self.api.post_c2c_message(openid=openid,msg_type=2,markdown={'content':msg},keyboard=cos_again_menu)
            elif chat_type == 1:
                await self.api.post_group_message(group_openid=openid,msg_type=2,markdown={'content':msg},keyboard=cos_again_menu)
                                  
    async def repeater(self,message:C2CMessage|GroupMessage,**kwargs):
        global main_menu, repeater_menu
        content = message.content
        if content == "/退出复读机":
            _log.info("解除复读")
            repeater_mode[message.group_openid] = False
            return 


        # 有附件（图片/表情）
        if message.attachments:
            _log.info(f"收到附件：{message.attachments}")
            attach_list = list(message.attachments)

            urls = []
            tag_list = re.findall(r'<faceType=6[^>]*>', content)
            for attach in attach_list:
                url = attach.url
                w =attach.width
                h = attach.height
                urls.append(f"![text #{w}px #{h}px]({url})")
            _log.info(f"tag_list={tag_list}, urls={urls}")
            rules = list(zip(tag_list, urls))
            _log.info(f"{rules=}")
            for old, new in rules:
                content = content.replace(old, new)
            _log.info(f"{content=}")
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
                                            keyboard = main_menu)

        elif data == 'bot_random_cos':
            await self.send_cos_img(user_openid, 0)
            pass

        elif data == 'bot_random_cos_tips':
            await self.send_cos_tips(user_openid, 0)
            pass

        elif data == 'bot_menu':
            if user_openid in kards_mode['c2c']:
                kards_mode['c2c'][user_openid] = {}
            await self.api.post_c2c_message(openid=user_openid,
                        msg_type=2,
                        markdown={'content':f"功能"},
                        keyboard = main_menu)

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
                                            keyboard = kards_menu)

        elif data == 'kards_enter_turn':
            # 校验对局是否存在
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = main_menu)
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
                                            keyboard = kards_menu)

        elif data == 'kards_add_com_point':
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = main_menu)
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
                                            keyboard = kards_menu)

        elif data == 'kards_sub_com_point':
            if user_openid not in kards_mode['c2c']:
                await self.api.post_c2c_message(openid=user_openid,
                    msg_type=2,
                    markdown={'content':"未开始游戏"},
                    keyboard = main_menu)
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
                                            keyboard = kards_menu)

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
                        await remove_data(data=d, file=game_json_file, type=1)
                    else:
                        if d['type'] == 3:
                            msg += '主人'
                        if d['type'] == 5:
                            msg += '喵~'
        return msg

if __name__ == "__main__":
    
    intents = botpy.Intents(public_messages=True, interaction=True)
    client = MyBot(intents=intents)
    client.run(appid=APPID, secret=APPSECRET)