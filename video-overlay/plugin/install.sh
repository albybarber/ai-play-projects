#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/build/VideoOverlayCamera.plugin"
PLUGIN_DEST="/Library/CoreMediaIO/Plug-Ins/DAL/VideoOverlayCamera.plugin"

if [ ! -d "$PLUGIN_SRC" ]; then
  echo "Plugin not built. Run: npm run build:plugin"
  exit 1
fi

echo "Installing plugin (requires sudo)..."
sudo mkdir -p "/Library/CoreMediaIO/Plug-Ins/DAL"
sudo rm -rf "$PLUGIN_DEST"
sudo cp -r "$PLUGIN_SRC" "$PLUGIN_DEST"
sudo chmod -R 755 "$PLUGIN_DEST"

echo "Restarting camera services..."
# Kill the camera assistant processes — launchd restarts them automatically,
# and on restart they re-scan the DAL plugins directory.
sudo killall cameracaptured 2>/dev/null || true
sudo killall VDCAssistant 2>/dev/null || true

# Give services a moment to restart
sleep 1

echo ""
echo "✓ Plugin installed at $PLUGIN_DEST"
echo ""
echo "  Next steps:"
echo "  1. Quit and reopen any video app (Photobooth, Zoom, Teams, Meet)"
echo "  2. Select 'Video Overlay Camera' in camera settings"
echo ""
echo "  If the camera doesn't appear, try: log out and back in (one-time restart)."
