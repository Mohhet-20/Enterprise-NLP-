# syntax=docker/dockerfile:1
#
# Multi-stage: build the Vite/React app with Node, then serve the static
# output with nginx. The Node toolchain (a few hundred MB) never ships in
# the final image — only the compiled dist/ output does.

# --- Stage 1: build ---
FROM node:20-slim AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

COPY frontend/ .
RUN npm run build

# --- Stage 2: serve ---
# nginx-unprivileged listens on 8080, not 80, specifically so it doesn't
# need root to bind the port — a non-root final image without giving up
# the standard nginx serving behavior.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/ >/dev/null 2>&1 || exit 1
