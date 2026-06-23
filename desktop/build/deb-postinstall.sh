#!/bin/bash
# Custom Debian post-install for FORGE.
#
# Replaces electron-builder's default postinst. The only functional change: we ALWAYS make
# chrome-sandbox setuid-root (4755) instead of relying on a userns probe. electron-builder's
# default runs `unshare --user true` to decide whether to setuid — but on Ubuntu 23.10+/24.04
# (and Pop!_OS, Mint 22, TUXEDO, Debian 13) AppArmor restricts the *unprivileged-userns*
# sandbox that Chromium's zygote actually needs, even though that probe passes. The result is
# a setuid_sandbox_host FATAL abort at launch. Always setuid-ing chrome-sandbox (exactly what
# Google Chrome's own .deb does) keeps a REAL sandbox and launches everywhere.
set -e

# Expose the app on PATH via update-alternatives (same as the default postinst).
if type update-alternatives 2>/dev/null >&1; then
    if [ -L '/usr/bin/forge-desktop' -a -e '/usr/bin/forge-desktop' -a "$(readlink '/usr/bin/forge-desktop')" != '/etc/alternatives/forge-desktop' ]; then
        rm -f '/usr/bin/forge-desktop'
    fi
    update-alternatives --install '/usr/bin/forge-desktop' 'forge-desktop' '/opt/FORGE/forge-desktop' 100 || ln -sf '/opt/FORGE/forge-desktop' '/usr/bin/forge-desktop'
else
    ln -sf '/opt/FORGE/forge-desktop' '/usr/bin/forge-desktop'
fi

# Real Chromium sandbox: setuid-root helper (works regardless of userns restrictions).
chmod 4755 '/opt/FORGE/chrome-sandbox' || true

if hash update-mime-database 2>/dev/null; then
    update-mime-database /usr/share/mime || true
fi

if hash update-desktop-database 2>/dev/null; then
    update-desktop-database /usr/share/applications || true
fi
