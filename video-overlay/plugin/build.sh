#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
PLUGIN_DIR="$BUILD_DIR/VideoOverlayCamera.plugin"
BUNDLE_BINARY="$PLUGIN_DIR/Contents/MacOS/VideoOverlayCamera"

echo "Building VideoOverlayCamera DAL plugin..."

mkdir -p "$PLUGIN_DIR/Contents/MacOS"
mkdir -p "$PLUGIN_DIR/Contents/Resources"

# Copy Info.plist
cp "$SCRIPT_DIR/Info.plist" "$PLUGIN_DIR/Contents/Info.plist"

# Compile
clang++ \
  -arch arm64 -arch x86_64 \
  -dynamiclib \
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

echo "Built: $PLUGIN_DIR"
echo "Run 'npm run install:plugin' (or bash plugin/install.sh) to install."
