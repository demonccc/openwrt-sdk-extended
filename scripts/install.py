#!/usr/bin/env python3
"""Install an extension over the exact official SDK it was built against."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def install(sdk, extension, original_sdk):
    with tarfile.open(extension, "r:gz") as tar:
        manifest=json.load(tar.extractfile("extension-manifest.json"))
        if manifest.get("schema") != 1:
            raise ValueError("Unsupported extension manifest")
        if original_sdk.name != manifest["official_sdk_filename"] or sha256(original_sdk) != manifest["official_sdk_sha256"]:
            raise ValueError("Extension was not built for this exact official SDK archive")
        allowed=set("staging_dir/"+name for name in manifest["files"])
        for entry in tar:
            if entry.name == "extension-manifest.json":
                continue
            if entry.name not in allowed or entry.name.startswith("/") or ".." in Path(entry.name).parts:
                raise ValueError(f"Unexpected extension path: {entry.name}")
            if entry.issym():
                # External links must not escape the SDK, and links from upstream
                # may be relative to the original build workdir. Reject for now.
                if Path(entry.linkname).is_absolute() or ".." in Path(entry.linkname).parts:
                    raise ValueError(f"Unsafe symbolic link: {entry.name}")
            if entry.islnk() or entry.isdev() or entry.isfifo():
                raise ValueError(f"Unsupported tar entry: {entry.name}")
        tar.extractall(sdk, filter="data")
    print(f"Installed {manifest['component']} on {sdk}")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sdk", type=Path, required=True)
    p.add_argument("--official-archive", type=Path, required=True)
    p.add_argument("--extension", type=Path, required=True)
    a=p.parse_args()
    install(a.sdk, a.extension, a.official_archive)

if __name__ == "__main__":
    main()
