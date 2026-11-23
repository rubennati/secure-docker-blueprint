# static-site pattern — Vite/React recipe
#
# Build stage is the only part that differs between recipes in this pattern —
# compare recipes/astro/Dockerfile. `vite build` emits static output to dist/
# by default, same as the Astro recipe.

# --- Build ---
FROM node:24-alpine@sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8 AS builder
WORKDIR /src
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Runtime ---
# Identical across every recipe: a hardened, non-root nginx serving static
# files.
FROM ghcr.io/nginx/nginx-unprivileged:1.31.9-alpine-slim@sha256:75e85a09b0f25bd46d49a9fd85589ffa70b0459c8ed5ee0dc6596fd642e1f829
COPY --from=builder /src/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD wget -qO /dev/null http://127.0.0.1:8080/ || exit 1
