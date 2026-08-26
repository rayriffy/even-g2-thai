#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
G2FLASH_ROOT="${G2FLASH_ROOT:-$ROOT/../g2flash}"
G2FLASH_COMMIT="877c8d9490db0d3717ca012dd0f54556af3701bd"
CACHE="$ROOT/.cache"
BUILD="$ROOT/build"
STOCK="$CACHE/g2_2.2.9.22.bin"
FONT="$ROOT/third_party/2005_iannnnnAMD.ttf"
FONT_BLOB="$BUILD/thai_font.bin"
PATCH_SPEC="$ROOT/patches/thai_patches.json"
OUTPUT="$BUILD/g2_2.2.9.22_thai.bin"

FW_URL="https://cdn.evenreal.co/firmware/fc250b05e98a9ff998b4b68f5f99f994.bin"
FW_SHA256="a03fbea9f68a9de6bc271daabb9f3a41c59053d1086622c76a4e990f829cc561"
FONT_SHA256="688f2ef20776a1f0286bd73bef4dd5d5c76640f4a7c4f0ea5f7c1b8d87a969b7"

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
  if [[ -e "$path" ]]; then
    echo "refusing to overwrite unverified $label at $path" >&2
    echo "inspect it, then move it aside or trash it explicitly" >&2
    return 1
  fi
  local candidate
  candidate="$(mktemp "${path}.candidate.XXXXXX")"
  echo "downloading $label"
  if ! curl --fail --location --retry 3 --progress-bar --output "$candidate" "$url"; then
    echo "$label download failed; incomplete candidate retained at $candidate" >&2
    return 1
  fi
  local actual
  actual="$(sha256_file "$candidate")"
  [[ "$actual" == "$expected" ]] || {
    echo "$label SHA-256 mismatch: expected $expected, got $actual" >&2
    echo "unverified candidate retained at $candidate" >&2
    return 1
  }
  if ! ln "$candidate" "$path"; then
    echo "refusing to publish $label; $path already exists or linking failed" >&2
    echo "verified candidate retained at $candidate" >&2
    return 1
  fi
  echo "published $label; verified candidate retained at $candidate"
}

mkdir -p "$CACHE" "$BUILD"
[[ -f "$G2FLASH_ROOT/patches/build.py" ]] || {
  echo "g2flash not found at $G2FLASH_ROOT (set G2FLASH_ROOT)" >&2
  exit 1
}
[[ "$(git -C "$G2FLASH_ROOT" rev-parse HEAD)" == "$G2FLASH_COMMIT" ]] || {
  echo "g2flash must be pinned to $G2FLASH_COMMIT" >&2
  exit 1
}
g2flash_dirty="$(git -C "$G2FLASH_ROOT" status --porcelain --untracked-files=all | sed '/^?? \.DS_Store$/d')"
[[ -z "$g2flash_dirty" ]] || {
  echo "g2flash has local source changes; use a fresh clean checkout" >&2
  exit 1
}

fetch_verified "$FW_URL" "$STOCK" "$FW_SHA256" "stock G2 2.2.9.22 firmware"

if [[ "$UPDATE_PATCHES" -eq 1 ]]; then
  [[ -f "$FONT" ]] || {
    echo "missing vendored Thai font at $FONT" >&2
    exit 1
  }
  [[ "$(sha256_file "$FONT")" == "$FONT_SHA256" ]] || {
    echo "local Thai font SHA-256 mismatch at $FONT" >&2
    exit 1
  }
  echo "verified local 2005_iannnnnAMD Thai font"
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
