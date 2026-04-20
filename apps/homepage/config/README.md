# Homepage Config Files

Homepage uses one YAML file per concern. On first start, rename the `*.example.yaml` files to drop the `.example`, then edit.

```bash
cd apps/homepage/config
for f in *.example.yaml; do cp "$f" "${f/.example/}"; done
```

## Files

| File | Purpose |
|---|---|
| `settings.yaml` | Global appearance, title, theme, layout |
| `services.yaml` | The main service grid — your apps, their URLs, widgets |
| `bookmarks.yaml` | Lightweight bookmark grid |
| `widgets.yaml` | Info widgets (weather, resources, search, date/time) |
| `docker.yaml` | Docker-integration definitions (only active if the socket is mounted — see parent README "Docker integration") |
| `kubernetes.yaml` | Kubernetes integration (only if you have a K8s context mounted) |
| `proxmox.yaml` | Proxmox API integration definitions |

Reference: https://gethomepage.dev/configs/
