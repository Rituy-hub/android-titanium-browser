#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

DEFAULT_PROXY="${BUILD_PROXY:-${https_proxy:-${http_proxy:-${HTTPS_PROXY:-${HTTP_PROXY:-http://192.168.2.1:37896}}}}}"
BUILD_ARM="${BUILD_ARM:-1}"
BUILD_ARM64="${BUILD_ARM64:-1}"
BUILD_AAB="${BUILD_AAB:-0}"
NINJA_JOBS="${NINJA_JOBS:-14}"
FAST_LOCAL_BUILD="${FAST_LOCAL_BUILD:-1}"
AUTO_RELEASE="${AUTO_RELEASE:-1}"

echo "=========================================================="
echo " [1/2] Building 'main' branch..."
echo "=========================================================="
git checkout main

FAST_LOCAL_BUILD="$FAST_LOCAL_BUILD" \
BUILD_PROXY="$DEFAULT_PROXY" \
BUILD_ARM="$BUILD_ARM" \
BUILD_ARM64="$BUILD_ARM64" \
BUILD_AAB="$BUILD_AAB" \
NINJA_JOBS="$NINJA_JOBS" \
"$SCRIPT_DIR/build.sh"

echo ""
echo "=========================================================="
echo " [2/2] Building 'lemur-style-app-menu' branch..."
echo "=========================================================="
git checkout lemur-style-app-menu

FAST_LOCAL_BUILD=1 \
BUILD_PROXY="$DEFAULT_PROXY" \
BUILD_ARM="$BUILD_ARM" \
BUILD_ARM64="$BUILD_ARM64" \
BUILD_AAB="$BUILD_AAB" \
NINJA_JOBS="$NINJA_JOBS" \
"$SCRIPT_DIR/build.sh"

echo ""
echo "=========================================================="
echo " SUCCESS: Both branches built successfully!"
echo " Output files in chromium/src/out/release/:"
echo "=========================================================="
ls -lh "$SCRIPT_DIR/chromium/src/out/release"/*.apk 2>/dev/null || true

if [ "$AUTO_RELEASE" = "1" ]; then
    echo ""
    echo "=========================================================="
    echo " [Auto Release] Publishing artifacts with MOVE=1 release.sh..."
    echo "=========================================================="
    MOVE=1 "$SCRIPT_DIR/release.sh"
fi
