# web-api pattern — fixture
#
# Multi-stage: TypeScript is compiled in the builder stage; the runtime stage
# ships only the compiled output and the `node` binary, no dev dependencies,
# no npm.

# --- Build ---
FROM node:24-alpine AS builder
WORKDIR /src
COPY package*.json tsconfig.json ./
RUN npm ci
COPY src ./src
RUN npm run build

# --- Runtime ---
FROM node:24-alpine
WORKDIR /app
COPY --from=builder /src/dist ./dist
# node:*-alpine ships a non-root `node` user (uid 1000) — no init system, so
# `user:` in compose is safe, unlike an s6-overlay or supervisord image.
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD wget -qO /dev/null http://127.0.0.1:3000/healthz || exit 1
CMD ["node", "dist/server.js"]
