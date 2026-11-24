#!/bin/sh
# Run before Melos bootstrap in the AgentLinux installer build checkout.
set -eu
root=$(cd "${1:?installer source directory required}" && pwd)
patch_file=$(cd "$(dirname "$0")" && pwd)/confirm-localization.patch
if ! git -C "$root" apply --reverse --check "$patch_file" 2>/dev/null; then
    git -C "$root" apply "$patch_file"
fi
lock="$root/packages/ubuntu_bootstrap/pubspec.lock"
expected=f277fbfe3b9ac09840aa2a996e148b98a3c2837b0e83c36550e9abc2f82ee14f
grep -Fq "$expected" "$lock"
dest="$root/packages/ubuntu_flavor"
tmp=$(mktemp -d "$root/packages/.flavor.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
curl -fsSL https://pub.dev/api/archives/ubuntu_flavor-0.4.0.tar.gz -o "$tmp/archive"
printf '%s  %s\n' "$expected" "$tmp/archive" | shasum -a 256 -c -
mkdir "$tmp/pkg"
tar -xzf "$tmp/archive" -C "$tmp/pkg"
python3 - "$tmp/pkg/lib/src/ubuntu_flavor.dart" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
text = source.read_text()
original = "kylin('Ubuntu Kylin')"
if text.count(original) != 1:
    sys.exit("Unexpected UbuntuFlavor source")
source.write_text(text.replace(original, "kylin('AgentLinux')"))
PY
if [ -e "$dest" ]; then
    diff -qr "$tmp/pkg" "$dest"
else
    mv "$tmp/pkg" "$dest"
fi
