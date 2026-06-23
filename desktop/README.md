# FORGE — desktop app

The one-click desktop face of FORGE: see your sovereign cluster, launch your AI apps, add machines.
Cluster view ported from Cipher's fleet tab; reuses the canonical `/api/cluster/nodes` API.

## Run (dev)
```bash
cd desktop && npm install && npm start
```

## Build installers (1-click) — AppImage / deb / dmg / exe
```bash
cd desktop && npm install && npm run dist   # outputs to desktop/dist/
```

## Point it at your cluster
By default it reads the fleet from `http://localhost:8001/api/cluster/nodes`. To target olympus over
Tailscale, set in the app's devtools console: `localStorage.setItem('forge_api','http://<olympus-ip>:8001')`.
