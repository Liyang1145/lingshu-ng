# lingshu-ng 服务镜像：只含纯标准库核心（零第三方依赖），非 root 运行，数据在 /data 卷。
# 构建：docker build -t lingshu-ng .
# 运行：docker run -d -p 8765:8765 -v lsdata:/data -e LINGSHU_NG_TOKEN=$(openssl rand -hex 32) lingshu-ng
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LINGSHU_NG_SEM=off LINGSHU_NG_DB=/data/memory.sqlite
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY lingshu_ng ./lingshu_ng
RUN pip install --no-cache-dir . && rm -rf /app/lingshu_ng \
 && useradd --system --uid 10001 --home /data lingshu && mkdir -p /data && chown lingshu /data
USER 10001
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=2).status==200 else 1)"
# 绑 0.0.0.0 时必须提供 LINGSHU_NG_TOKEN，否则服务拒绝启动（设计如此）
CMD ["lingshu-ng", "serve", "--host", "0.0.0.0", "--port", "8765"]
