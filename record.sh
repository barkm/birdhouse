# !/bin/bash

cleanup() {
    docker compose down
}

trap cleanup INT TERM EXIT

docker compose up pi relay recorder --build -d
curl --retry 5 --retry-all-errors http://localhost:8003/record &
docker compose logs -f