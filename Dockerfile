# syntax=docker/dockerfile:1
# ============================================================
# 电商小二 · 主客服后端（FastAPI + LLM）
# 端口：18082
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# uv：项目本身使用 uv 管理依赖，这里复用它按 uv.lock 安装精确版本
RUN pip install uv && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 先只拷贝依赖清单，利用 Docker layer cache（改代码不会重装依赖）
COPY pyproject.toml uv.lock ./
# --no-install-project：只装第三方依赖，不把项目本身当包构建
RUN uv sync --frozen --no-dev --no-install-project

# 再拷贝业务代码
COPY . .

# 让容器内直接使用 .venv 中的解释器与命令
ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

EXPOSE 18082

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "18082"]
