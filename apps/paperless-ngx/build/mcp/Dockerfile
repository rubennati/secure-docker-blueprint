# =============================================
# Paperless MCP Server
# Source: https://github.com/nloui/paperless-mcp
# =============================================
# Multi-stage build: clone → compile TypeScript → slim runtime
# Runs in HTTP mode on port 3000 (Streamable HTTP transport)
# Endpoint: POST /mcp
# =============================================

# --- Build stage ---
FROM node:20-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/nloui/paperless-mcp.git .

RUN npm ci
RUN npm run build

# --- Production stage ---
FROM node:20-slim
WORKDIR /app

COPY --from=builder /app/build/ ./
COPY --from=builder /app/node_modules/ ./node_modules/
COPY --from=builder /app/package.json ./

EXPOSE 3000

# Default: HTTP mode on port 3000
# Append <baseUrl> <token> at runtime via command/entrypoint
ENTRYPOINT ["node", "index.js", "--http", "--port", "3000"]
