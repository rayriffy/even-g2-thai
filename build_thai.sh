#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
G2FLASH_ROOT="${G2FLASH_ROOT:-$ROOT/../g2flash}"
G2FLASH_COMMIT="877c8d9490db0d3717ca012dd0f54556af3701bd"
CACHE="$ROOT/.cache"
BUILD="$ROOT/build"
STOCK="$CACHE/g2_2.3.2.14.bin"
FONT="$ROOT/fonts/maitree/Maitree-ExtraLight.ttf"
FONT_BLOB="$BUILD/thai_font.bin"
PATCH_SPEC="$ROOT/patches/thai_patches.json"
OUTPUT="$BUILD/g2_2.3.2.14_thai.bin"

FW_URL="https://cdn.evenreal.co/firmware/7892790e40cffbae6db8a635b335e17f.bin"
FW_SHA256="26b6067665a441b779c47f6b95427b8b4bb5f502aaf527466dadce628aeb00b2"
FONT_SHA256="aaa310f9bc913882863b1d39bd70978b7d068ac831ef3789bd921f781392343d"

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

fetch_verified "$FW_URL" "$STOCK" "$FW_SHA256" "stock G2 2.3.2.14 firmware"

if [[ "$UPDATE_PATCHES" -eq 1 ]]; then
  [[ -f "$FONT" ]] || {
    echo "missing vendored Thai font at $FONT" >&2
    exit 1
  }
  [[ "$(sha256_file "$FONT")" == "$FONT_SHA256" ]] || {
    echo "local Thai font SHA-256 mismatch at $FONT" >&2
    exit 1
  }
  echo "verified Maitree ExtraLight 200 source"
  python3 -c 'import PIL, fontTools' 2>/dev/null || {
    echo "Pillow and fontTools are required to regenerate patches: python3 -m pip install -r requirements-dev.txt" >&2
    exit 1
  }
  python3 "$ROOT/tools/pixel_font.py" "$FONT_BLOB" --source "$FONT" --report "$BUILD/thai-pixel-font-report.json"
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
echo "flash preparation: make webflasher (Case USB; see docs/flashing.md)"
