import { createServer } from "node:http";

// Validation fixture for development/web-api/. Proves the build → image →
// health → Traefik contract; not an application. Zero runtime dependencies —
// a real project adds a framework and, only if it needs one, a database.

const port = Number(process.env.PORT ?? 3000);

const server = createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  res.writeHead(200, { "content-type": "application/json" });
  res.end(JSON.stringify({ pattern: "web-api", fixture: true }));
});

server.listen(port, () => {
  console.log(`web-api fixture listening on ${port}`);
});
