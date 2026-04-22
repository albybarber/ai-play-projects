#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
PLUGIN_DIR="$BUILD_DIR/VideoOverlayCamera.plugin"
BUNDLE_BINARY="$PLUGIN_DIR/Contents/MacOS/VideoOverlayCamera"
ENTITLEMENTS="$SCRIPT_DIR/entitlements.plist"

echo "Building VideoOverlayCamera DAL plugin..."

mkdir -p "$PLUGIN_DIR/Contents/MacOS"
mkdir -p "$PLUGIN_DIR/Contents/Resources"

cp "$SCRIPT_DIR/Info.plist" "$PLUGIN_DIR/Contents/Info.plist"

# Compile universal binary (arm64 + x86_64)
clang++ \
  -arch arm64 -arch x86_64 \
  -bundle \
  -std=c++17 \
  -fobjc-arc \
  -framework CoreMediaIO \
  -framework CoreMedia \
  -framework CoreVideo \
  -framework CoreFoundation \
  -framework Foundation \
  -framework IOKit \
  -o "$BUNDLE_BINARY" \
  "$SCRIPT_DIR/src/VOCPlugIn.mm" \
  "$SCRIPT_DIR/src/VOCDevice.mm" \
  "$SCRIPT_DIR/src/VOCStream.mm" \
  -I"$SCRIPT_DIR/src"

# Write entitlements for ad-hoc signing
cat > "$ENTITLEMENTS" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
</dict>
</plist>
EOF

# Sign with ad-hoc identity + entitlements
codesign --deep --force --sign - \
  --entitlements "$ENTITLEMENTS" \
  --timestamp=none \
  "$PLUGIN_DIR"

echo "Built and signed: $PLUGIN_DIR"
echo "Run 'npm run install:plugin' (or: bash plugin/install.sh) to install."
