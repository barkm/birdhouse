FROM ghcr.io/astral-sh/uv:debian-slim
COPY main.py .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
CMD uv run fastapi run main.py --port $PORT