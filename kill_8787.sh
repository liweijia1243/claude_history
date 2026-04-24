#!/bin/bash

# 杀掉所有占用 8787 端口的进程

PORT=8787

# 查找占用端口的进程 PID
PIDS=$(lsof -ti :$PORT)

if [ -z "$PIDS" ]; then
    echo "没有找到占用端口 $PORT 的进程"
    exit 0
fi

echo "找到以下进程占用端口 $PORT:"
lsof -i :$PORT

echo ""
echo "正在杀掉这些进程..."

for PID in $PIDS; do
    echo "杀掉进程 $PID"
    kill -9 $PID 2>/dev/null
done

echo "完成"
