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
SKIP_IF_EXISTS="${SKIP_IF_EXISTS:-1}"
FORCE_REBUILD="${FORCE_REBUILD:-0}"

VERSION_ARGS="$SCRIPT_DIR/vanadium/args.gn"
VERSION=$(grep -m1 -o '[0-9]\+\(\.[0-9]\+\)\{3\}' "$VERSION_ARGS" || true)

get_branch_prefix() {
    local branch="$1"
    if [ "$branch" = "main" ]; then
        echo "$VERSION"
    else
        local branch_tag
        branch_tag="$(printf '%s' "$branch" | tr -c 'A-Za-z0-9._-' '-' | sed 's/^-*//; s/-*$//')"
        echo "${VERSION}-${branch_tag}"
    fi
}

check_branch_artifacts() {
    local branch="$1"
    local prefix
    prefix="$(get_branch_prefix "$branch")"
    local release_dir="$SCRIPT_DIR/chromium/src/out/release"

    if [ "$BUILD_ARM" = "1" ] && [ ! -s "$release_dir/${prefix}-armeabi-v7a.apk" ]; then
        return 1
    fi
    if [ "$BUILD_ARM64" = "1" ] && [ ! -s "$release_dir/${prefix}-arm64-v8a.apk" ]; then
        return 1
    fi
    if [ "$BUILD_AAB" = "1" ] && [ ! -s "$release_dir/${prefix}-arm64-v8a.aab" ]; then
        return 1
    fi
    return 0
}

is_branch_up_to_date() {
    local branch="$1"
    local stamp_file="$SCRIPT_DIR/chromium/src/out/release/.built_commit_${branch}"

    if [ "$FORCE_REBUILD" = "1" ]; then
        return 1
    fi

    if [ "$SKIP_IF_EXISTS" != "1" ]; then
        return 1
    fi

    if ! check_branch_artifacts "$branch"; then
        return 1
    fi

    local current_head
    current_head="$(git rev-parse "refs/heads/$branch" 2>/dev/null || true)"
    if [ -z "$current_head" ]; then
        return 1
    fi

    if [ -f "$stamp_file" ] && [ "$(cat "$stamp_file" 2>/dev/null)" = "$current_head" ]; then
        return 0
    fi

    # 如果产物存在但没有记录 commit stamp（例如早前版本编译产出的），
    # 只要产物存在且当前工作树没有未提交修改，也视为无需重复构建
    if [ ! -f "$stamp_file" ]; then
        if [ -z "$(git status --porcelain)" ]; then
            return 0
        fi
    fi

    return 1
}

build_branch() {
    local branch="$1"
    local step_num="$2"

    echo "=========================================================="
    echo " [$step_num/2] Checking '$branch' branch..."
    echo "=========================================================="

    if is_branch_up_to_date "$branch"; then
        local prefix
        prefix="$(get_branch_prefix "$branch")"
        echo "Artifacts for '$branch' already exist and branch is up to date:"
        ls -lh "$SCRIPT_DIR/chromium/src/out/release/${prefix}"* 2>/dev/null || true
        echo "Skipping build for '$branch'."
        return 0
    fi

    git checkout "$branch"

    FAST_LOCAL_BUILD="$FAST_LOCAL_BUILD" \
    BUILD_PROXY="$DEFAULT_PROXY" \
    BUILD_ARM="$BUILD_ARM" \
    BUILD_ARM64="$BUILD_ARM64" \
    BUILD_AAB="$BUILD_AAB" \
    NINJA_JOBS="$NINJA_JOBS" \
    "$SCRIPT_DIR/build.sh"

    local current_head
    current_head="$(git rev-parse HEAD)"
    mkdir -p "$SCRIPT_DIR/chromium/src/out/release"
    printf '%s\n' "$current_head" > "$SCRIPT_DIR/chromium/src/out/release/.built_commit_${branch}"
}

build_branch "main" "1"

echo ""
build_branch "lemur-style-app-menu" "2"

echo ""
echo "=========================================================="
echo " SUCCESS: Both branches process finished!"
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
