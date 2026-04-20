FROM python:3.12-slim

# 使用国内镜像加速依赖安装（中国用户）；海外用户可删除下一行
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple || true

WORKDIR /app

# 时区设置
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 仅拷贝 requirements 先装依赖，利用 docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py .

# 运行
CMD ["python", "-u", "monitor.py"]
