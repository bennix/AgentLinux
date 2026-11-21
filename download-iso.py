"""Download and verify the complete AgentLinux ISO. Python 3.8+, no dependencies."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = "https://github.com/bennix/AgentLinux"
TAG = "v2026.11.21.3"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    local = Path(__file__).with_name("release-manifest.json")
    manifest = json.loads(local.read_text()) if local.exists() else {}
    if manifest.get("tag") != TAG:
        with urlopen(f"{ROOT}/releases/download/{TAG}/release-manifest.json", timeout=90) as response:
            manifest = json.load(response)
    output = Path(manifest["iso"])
    if output.exists():
        if digest(output) == manifest["sha256"]:
            print("Verified:", output)
            return
        raise SystemExit("An existing ISO has a different digest. Move it before retrying.")
    partial = output.with_suffix(".iso.partial")
    # Resume only at verified part boundaries.
    with partial.open("a+b") as target:
        target.seek(0)
        for index, part in enumerate(manifest["parts"], 1):
            start = target.tell()
            if hashlib.sha256(target.read(part["size"])).hexdigest() == part["sha256"]:
                continue
            target.seek(start)
            target.truncate()
            print(f'{index}/{len(manifest["parts"])}  {part["name"]}', flush=True)
            with urlopen(f'{ROOT}/releases/download/{TAG}/{part["name"]}', timeout=180) as response:
                h = hashlib.sha256()
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    target.write(block)
                    h.update(block)
            if h.hexdigest() != part["sha256"]:
                raise SystemExit("Part checksum mismatch. Run again to retry.")
        target.truncate()
    if digest(partial) != manifest["sha256"]:
        raise SystemExit("Final ISO checksum mismatch")
    partial.rename(output)
    print("Verified:", output)


if __name__ == "__main__":
    main()
