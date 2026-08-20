#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
G2FLASH_ROOT="${G2FLASH_ROOT:-$ROOT/../g2flash}"
CACHE="$ROOT/.cache"
BUILD="$ROOT/build"
STOCK="$CACHE/g2_2.2.6.10.bin"
FONT="$CACHE/NotoSansThai-wdth-wght.ttf"
FONT_BLOB="$BUILD/thai_font.bin"
PATCH_SPEC="$ROOT/patches/thai_patches.json"
OUTPUT="$BUILD/g2_2.2.6.10_thai.bin"

FW_URL="https://cdn.evenreal.co/firmware/e28738432d7b612d625331b00383149b.bin"
FW_SHA256="f4dfb0b49ad3de3c2daf17f8a27a157c3dc98411d6a0d3ab2cfd0918f41b9afa"
FONT_URL="https://raw.githubusercontent.com/google/fonts/e1118da94a8cb00cf6d06cdac9ef13eb1e5c6ab7/ofl/notosansthai/NotoSansThai%5Bwdth%2Cwght%5D.ttf"
FONT_SHA256="5a1c559bb539583c8a1fd99d1c5b9491e5e14478c9cd2bd0970d5c3096cc9ef8"

UPDATE_PATCHES=0
if [[ "${1:-}" == "--update-patches" ]]; then
  UPDATE_PATCHES=1
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [--update-patches]" >&2
  exit 2
fi

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

fetch_verified() {
  local url="$1" path="$2" expected="$3" label="$4"
  if [[ -f "$path" ]] && [[ "$(sha256_file "$path")" == "$expected" ]]; then
    echo "verified cached $label"
    return
  fi
  echo "downloading $label"
  curl --fail --location --retry 3 --progress-bar --output "$path" "$url"
  local actual
  actual="$(sha256_file "$path")"
  [[ "$actual" == "$expected" ]] || {
    echo "$label SHA-256 mismatch: expected $expected, got $actual" >&2
    exit 1
  }
}

mkdir -p "$CACHE" "$BUILD"
[[ -f "$G2FLASH_ROOT/patches/build.py" ]] || {
  echo "g2flash not found at $G2FLASH_ROOT (set G2FLASH_ROOT)" >&2
  exit 1
}

fetch_verified "$FW_URL" "$STOCK" "$FW_SHA256" "stock G2 2.2.6.10 firmware"

if [[ "$UPDATE_PATCHES" -eq 1 ]]; then
  fetch_verified "$FONT_URL" "$FONT" "$FONT_SHA256" "pinned Noto Sans Thai"
  python3 -c 'import PIL' 2>/dev/null || {
    echo "Pillow is required to regenerate patches: python3 -m pip install -r requirements-dev.txt" >&2
    exit 1
  }
  python3 "$ROOT/tools/font_blob.py" "$FONT" "$FONT_BLOB"
  python3 "$ROOT/tools/render_preview.py" "$FONT_BLOB" "$BUILD/thai-preview.png"
  python3 "$ROOT/tools/generate_patch.py" \
    --stock "$STOCK" \
    --font-blob "$FONT_BLOB" \
    --compiler-helper "$G2FLASH_ROOT/patches/build.py" \
    --output "$PATCH_SPEC"
fi

[[ -f "$PATCH_SPEC" ]] || {
  echo "missing $PATCH_SPEC; run $0 --update-patches" >&2
  exit 1
}

python3 "$ROOT/tools/apply_patches.py" "$STOCK" "$PATCH_SPEC" "$OUTPUT"
python3 "$ROOT/tools/verify_firmware.py" "$OUTPUT"
echo "built $OUTPUT"
echo "flash tool: $G2FLASH_ROOT/g2flash.py"
