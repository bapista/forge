#!/bin/sh
# Build the FORGE Linux installers (AppImage + deb), then patch the AppImage so it launches
# on distros that restrict the unprivileged-userns sandbox. See patch-appimage.sh for why.
set -e
cd "$(dirname "$0")/.."
npx --no-install electron-builder --linux AppImage deb
for img in dist/*.AppImage; do
  sh scripts/patch-appimage.sh "$img"
done
echo "Linux installers ready in desktop/dist/"
