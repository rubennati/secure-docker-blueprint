# static-site pattern — Astro recipe
#
# Build stage is the only part that differs between recipes in this pattern —
# compare recipes/vite-react/Dockerfile. `astro build` emits static output to
# dist/ by default, which is all the runtime stage needs to know.

# --- Build ---
FROM node:24-alpine AS builder
WORKDIR /src
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Runtime ---
# Identical across every recipe: a hardened, non-root nginx serving static
# files. No shell access is needed at runtime, so nothing from the build stage
# survives except dist/.
FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY --from=builder /src/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD wget -qO /dev/null http://127.0.0.1:8080/ || exit 1
