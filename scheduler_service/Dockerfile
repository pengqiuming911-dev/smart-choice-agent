FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app

# 使用阿里云 pip 镜像加速安装
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 环境变量
ENV PYTHONPATH=/app

# 默认命令
CMD ["python", "-m", "src.scheduler"]
