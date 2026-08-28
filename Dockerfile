FROM ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    python3 \
    python3-pip \
    git \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制你自己项目代码到容器 /app
COPY . .

# 克隆网易云API到子文件夹 netease_api，不要覆盖/app
RUN git clone https://gitee.com/a-xing7737/NeteaseCloudMusicApi.git ./netease_api

# 进入网易云目录安装node依赖
WORKDIR /app/netease_api
RUN npm install

# 切回项目根目录
WORKDIR /app

# 安装你的python依赖
RUN pip3 install -r requirements.txt

# 复制启动脚本
COPY start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
