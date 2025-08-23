FROM ghcr.io/astral-sh/uv:debian-slim
RUN apt-get update && apt-get install -y ffmpeg curl
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync
COPY main.py .
ENV PYTHONUNBUFFERED=1
CMD sh -c 'curl --retry 5 --retry-connrefused -H "Content-Type: application/json" -d "{\"name\": \"birdhouse\", \"url\": \"$URL\"}" "$REGISTER_URL" && uv run fastapi run main.py --port $PORT'
