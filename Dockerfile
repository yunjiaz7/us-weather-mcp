# 使用轻量级 Python 3.11 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 1. 复制依赖文件并安装
# 这样做的好处是利用 Docker 缓存，代码变动不影响依赖安装层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. 复制服务器代码
COPY weather_server.py .

# 设置环境变量，确保 Python 打印内容不被缓存
ENV PYTHONUNBUFFERED=1

# 启动命令：运行我们的 FastMCP 服务器
CMD ["python", "weather_server.py"]