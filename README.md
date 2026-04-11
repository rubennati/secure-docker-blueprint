# Docker Ops Blueprint

A modular, security-focused boilerplate for Docker-based server infrastructure on Debian 13.

## Stack

- **OS:** Debian 13 (Trixie)
- **Runtime:** Docker + Docker Compose
- **Reverse Proxy:** Traefik
- **Monitoring:** TBD (Dockhand under evaluation)

## Project Structure

```
docker-ops-blueprint/
├── core/           # Core infrastructure (Traefik, networks)
├── apps/           # Application stacks
├── monitoring/     # Observability and monitoring
├── scripts/        # Setup and helper scripts
├── .env.example    # Global environment template
└── README.md
```

## Principles

- **Docker-first** – every service runs in containers
- **Traefik-first** – all HTTP traffic routes through Traefik
- **Security by default** – secrets via `.env`, no hardcoded values
- **Standardized** – consistent compose and env file patterns across all components
- **Modular** – each component works independently

## Getting Started

> Work in progress – detailed setup instructions will follow as components are added.

1. Clone the repository
2. Copy `.env.example` to `.env` and adjust values
3. Start with `core/traefik`, then add apps as needed

## License

TBD
