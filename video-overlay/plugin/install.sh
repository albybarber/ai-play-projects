#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/build/VideoOverlayCamera.plugin"
PLUGIN_DEST="/Library/CoreMediaIO/Plug-Ins/DAL/VideoOverlayCamera.plugin"

if [ ! -d "$PLUGIN_SRC" ]; then
  echo "Plugin not built. Run: npm run build:plugin"
  exit 1
fi

echo "Installing plugin to $PLUGIN_DEST (requires sudo)..."
sudo mkdir -p "/Library/CoreMediaIO/Plug-Ins/DAL"
sudo rm -rf "$PLUGIN_DEST"
sudo cp -r "$PLUGIN_SRC" "$PLUGIN_DEST"
echo "Installed. Restart your video app and select 'Video Overlay Camera'."
