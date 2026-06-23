# Desktop-app pattern — reuse for NeuronAI · Cipher · Aegis AI

The smallest possible Electron desktop app, so any Collab-Foundry product can ship one.
**Three files do everything:**

| File | Role |
|---|---|
| `package.json` | deps (`electron`, `electron-builder`) + the `build` config (appId, targets, maintainer) |
| `main.js` | opens one window that loads the UI |
| `renderer/index.html` | the entire UI — self-contained HTML/CSS/JS, no framework, light/dark themed |

## Make a new app (e.g. NeuronAI desktop)
1. Copy this `desktop/` folder.
2. In `package.json`: change `name`, `productName`, `build.appId`.
3. Replace `renderer/index.html` with that product's UI (it can fetch the product's own API).
4. `npm install && npm start` (dev) → `npm run dist` (installers: AppImage/deb/dmg/exe).

That's the whole recipe. FORGE's UI here = a live cluster view + app tiles + add-node; swap it for chat,
mail, etc. The theme system (`html[data-theme]` + the ☀️/🌙 toggle) and the API-fetch pattern carry over.
