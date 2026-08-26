#!/bin/bash
set -e

if [ ! -d /app/360-dlc-downloader ]; then
    echo "Seeding /app with 360-dlc-downloader..."
    cp -a /opt/dlc-seed/360-dlc-downloader /app/360-dlc-downloader
fi

# Keep the running copy up to date on every container start, not just at
# image build time - the image's baked-in git clone is cached by Docker
# and won't pick up new commits on a plain rebuild, so without this a
# container can be stuck running stale code indefinitely. Best-effort:
# don't fail startup over it (offline, diverged history, etc).
if [ -d /app/360-dlc-downloader/.git ]; then
    git -C /app/360-dlc-downloader pull --ff-only \
        || echo "Could not update /app/360-dlc-downloader (offline, local changes, or diverged history?) - continuing with what's there."
fi

# Re-sync the symlink every start too, not just at image build time - if
# the script arrived via the pull above (or changed), the symlink target
# still needs to be executable and on PATH.
chmod +x /app/360-dlc-downloader/download_dlc.py 2>/dev/null || true
ln -sf /app/360-dlc-downloader/download_dlc.py /usr/local/bin/download_dlc.py

exec "$@"
