FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

COPY src/ ./src/
COPY wiki_repo/ ./wiki_repo/

ENV PYTHONPATH=/app

CMD ["python", "-m", "src.commands"]
