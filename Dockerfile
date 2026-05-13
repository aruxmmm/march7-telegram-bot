# 使用官方 Python 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如果需要）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录（如果需要）
RUN mkdir -p /app/data

# 设置环境变量（可选，可以通过 docker run -e 覆盖）
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果 QQ Bot 启用，可能需要）
EXPOSE 8080

# 运行应用
CMD ["python", "main.py"]