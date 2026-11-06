FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /uvx /usr/local/bin/
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && apt-get clean \
    && uv pip install --system --no-cache openai==3.46.0
WORKDIR /app
# Harbor builds from environment/ only. The answer key is never in this image.
