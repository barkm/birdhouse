FROM ghcr.io/astral-sh/uv:debian-slim
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
COPY main.py .
COPY firebase.py .
ENV PYTHONUNBUFFERED=1
CMD uv run fastapi run main.py --port $PORT