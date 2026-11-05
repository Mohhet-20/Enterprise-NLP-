"""Download and verify a model archive (the hosted demo image fetches the fine-tuned DistilBERT this way).

    python scripts/fetch_model.py <url> <sha256> <destination-dir>

The archive is checked against the expected SHA-256 before anything is extracted, and members are refused if they
would land outside the destination.
"""

import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path


def main() -> int:
    url, expected, dest = sys.argv[1], sys.argv[2].lower(), Path(sys.argv[3])
    archive = dest.with_suffix(".zip.part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}", flush=True)
    urllib.request.urlretrieve(url, archive)  # noqa: S310 - fixed https URL from the build arguments
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected:
        archive.unlink()
        print(f"sha256 mismatch: expected {expected}, got {digest}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(archive) as z:
        root = dest.parent.resolve()
        for name in z.namelist():
            if not (root / name).resolve().is_relative_to(root):
                print(f"refusing archive member outside the destination: {name}", file=sys.stderr)
                return 1
        z.extractall(root)
    archive.unlink()
    if not (dest / "config.json").is_file():
        print(f"{dest} has no config.json after extraction", file=sys.stderr)
        return 1
    print(f"model ready in {dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
