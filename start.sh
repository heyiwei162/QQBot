#!/bin/bash
set -e

ln -sf /etc/secrets/settings.json /app/json/settings.json
ln -sf /etc/secrets/pixiv_auth.json /app/json/pixic_auth.json

echo "启动网易云node api 127.0.0.1:3000"
cd /app/netease_api
node app.js &
NODE_PID=$!

# 网易云初始化需要一点时间，sleep给足
sleep 6

echo "启动python主进程"
cd /app
exec python3 -u "./src/main"
