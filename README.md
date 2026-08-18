# QQ Botpy 定制QQ机器人
基于官方 `qq-botpy` SDK 二次开发的轻量化QQ开放平台机器人
</div>

<p align="center">
<img src="https://img.shields.io/badge/Python-3.10+-blue.svg">
<img src="https://img.shields.io/badge/SDK-botpy-green.svg">
<img src="https://img.shields.io/badge/License-MIT-orange.svg">
</p>

---

## ⚠️ 合规重要提醒
本项目依托**QQ开放平台官方机器人接口**开发，仅允许个人学习、合规测试使用。
严格遵守《QQ开放平台开发者协议》，禁止以下行为：
- 恶意刷屏、广告营销、骚扰群发
- 色情、违规内容分发引流
- 批量风控破解、恶意滥用接口
所有私自上线运营带来的账号封禁、法律风险由使用者自行承担。

## ✨ 项目功能总览
### 📢 基础交互模块
- 群内@机器人唤起功能菜单、自动问好、随机图片指令
- 私聊消息全自动智能响应
- 好友新增/删除、机器人入群/退群事件监听，入群自动推送欢迎语


### 🎛 按钮交互（Interaction 交互事件）
依托平台原生按钮交互体系：
- 私聊、群聊双通道按钮响应
- 无需手动输指令，点击按钮直达功能：问好、随机COS、主菜单等
- 已适配官方交互回执逻辑，解决按钮长时间加载转圈问题

### 🛡 内置防护与调试优化
1. 消息自动清洗：剔除@标签、QQ表情特殊标签，避免接口参数报错
2. 全局接口异常捕获，消息发送失败容错兼容
3. 全流程事件日志打印，方便本地调试排错

## 📁 项目目录结构
```bash
├── src/
├── ├── main.py # 主程序
│── ├── AI.py # AI功能支持
│── ├── music.py # 音乐支持
│── ├── load.py # 上传支持
│── ├── pixiv.py # p站支持
│── ├── save.py # 保存支持
│── ├── type.py # 类型注解
├── json/
│ ├── session/ # AI对话文件
│ ├── *menu.json # 菜单按钮配置
│ ├── setting.json # KEY存放地
│ └── ban_list.json
├── venv/ # Python 虚拟环境（.gitignore 自动忽略）
├── .gitignore # Git 提交忽略配置
└── README.md # 项目说明文档
```

## ⚙️ 部署安装教程
### 环境要求
- Python 版本 ≥ 3.10

### 1. 安装依赖
```bash
pip install -r requirements.txt
git clone https://gitee.com/a-xing7737/NeteaseCloudMusicApi.git
```
### 2. 平台配置
前往【QQ 开放平台】创建机器人应用，获取 AppID、AppSecret；  <br>
打开 main.py，修改底部启动代码：  <br>
python  <br>
运行  <br>
#### 将下方参数替换为你自己申请的凭证  <br>
在./json/setting.json文件下添加  <br>
{  <br>
 "APPID": "XXXXXX",  <br>
 "APPSECRET": "XXXXXXXXXX"  <br>
}  <br>
同步修改代码内全局机器人自身 AppID 常量。  <br>
### 3. 启动运行  <br>
```bash
./netease-music-api-windows-x64.exe
python ./src/main.py
```
📝 群聊可用指令表
支持两种触发方式：按钮触发 / @机器人 + 指令
表格
|指令	|功能|
|---|---|
|`/菜单`|	弹出交互式功能按钮菜单 |
|`/问好`|	机器人回复打招呼文案 |
|`/复读机`|	开启当前群复读模式 |
|`/退出复读机`|	关闭复读功能 |
|`/随机C图`| 随机单张 COS 图 |
|`/随机C帖`| 随机整套 COS 帖子 |
|`/随机P图`| 随机整套 P 站图片 |
|`/随机音效`| 随机动静 |
|`/点歌`| 点歌 |

### 🚨 已知特殊改动 & 常见报错说明
本项目对原生 botpy 源码进行局部二次修改：  <br>
1.新增 on_message_create 普通消息监听事件  <br>
2.内置封装 interaction.react() 交互回执接口 <br>
3.增加富媒体分片上传接口  <br>
4.修改log文件  <br>
## License  <br>
仅用于个人学习交流，禁止商用二次分发。  <br>