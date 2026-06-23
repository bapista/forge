#!/bin/sh
# Patch an electron-builder AppImage so it launches when DOUBLE-CLICKED / run directly.
#
# Why this is needed: electron-builder only adds `--no-sandbox` to the .desktop menu Exec
# line, not to the AppRun direct-execution path. On distros that restrict the unprivileged
# user-namespace sandbox (Ubuntu 23.10+/24.04, Pop!_OS, Mint 22, TUXEDO OS, Debian 13),
# Chromium's setuid sandbox can't be root inside a read-only AppImage mount, so a directly
# executed .AppImage FATAL-aborts before any of our JS runs. We force --no-sandbox into the
# AppRun's BIN exec and repackage. (Safe: the renderer loads only local content, with
# contextIsolation on and nodeIntegration off — no remote/untrusted web for the sandbox to
# contain. The .deb still ships a real setuid sandbox via its postinst.)
set -e

IMG="$1"
[ -f "$IMG" ] || { echo "usage: patch-appimage.sh <path-to.AppImage>"; exit 1; }

# AppImage runtime (the ELF that mounts the squashfs). Glob the version so an electron-builder
# bump doesn't break us.
RT=$(ls "$HOME"/.cache/electron-builder/appimage/*/runtime-x64 2>/dev/null | head -1)
[ -f "$RT" ] || { echo "AppImage runtime not found under ~/.cache/electron-builder/appimage — run electron-builder once first"; exit 1; }

DIR=$(dirname "$IMG"); BASE=$(basename "$IMG")
cd "$DIR"
rm -rf squashfs-root forge.sqfs
"./$BASE" --appimage-extract >/dev/null

# Force --no-sandbox on every `exec "$BIN"` (covers both the 0-arg direct-launch branch and
# the args branch; a duplicate flag from the .desktop launch is harmless).
sed -i 's|exec "$BIN"|exec "$BIN" --no-sandbox|g' squashfs-root/AppRun

mksquashfs squashfs-root forge.sqfs -root-owned -noappend -comp gzip >/dev/null
cat "$RT" forge.sqfs > "$BASE"
chmod +x "$BASE"
rm -rf squashfs-root forge.sqfs
echo "patched AppImage for direct-launch (--no-sandbox): $IMG"
