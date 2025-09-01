FROM node:24-slim as builder

WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
RUN npm install

COPY src ./src
COPY static ./static
COPY svelte.config.js ./svelte.config.js
COPY vite.config.ts ./vite.config.ts
COPY tsconfig.json ./tsconfig.json
COPY .svelte-kit/tsconfig.json .svelte-kit/tsconfig.json
CMD npm run build && npm run preview -- --host 0.0.0.0 --port $PORT
