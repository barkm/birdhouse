FROM ghcr.io/astral-sh/uv:debian-slim
RUN apt-get update && apt-get install -y ffmpeg
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
COPY main.py .
ENV PYTHONUNBUFFERED=1
CMD uv run fastapi run main.py --port $PORT
