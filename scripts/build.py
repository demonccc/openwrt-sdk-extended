#!/usr/bin/env python3
"""Build a versioned development extension for a *specific official OpenWrt SDK*.

Does not compile firmware or distribute the entire SDK. Archive only files added
or changed in staging_dir by the selected upstream development recipe.
"""
from __future__ import annotations
import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from profiles import catalog, COMPONENTS

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.items.extend(v for k, v in attrs if k == "href")

def run(*args, cwd=None):
    print("+", " ".join(map(str,args)), flush=True)
    subprocess.run(list(map(str,args)), cwd=cwd, check=True)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sdk_download(release, target, subtarget, cache):
    base = f"https://downloads.openwrt.org/releases/{release}/targets/{target}/{subtarget}/"
    p = Links()
    with urllib.request.urlopen(base, timeout=60) as r:
        p.feed(r.read().decode("utf-8", "replace"))
    filenames = [n for n in p.items if n.startswith(f"openwrt-sdk-{release}-")
                 and n.endswith((".tar.zst", ".tar.xz"))
                 and f"-{target}-{subtarget}_" in n and "Linux-x86_64" in n]
    if len(filenames) != 1:
        raise RuntimeError(f"Expected one matching official SDK: {base}: {filenames}")
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / filenames[0]
    if not archive.is_file():
        run("curl", "--fail", "--location", "--retry", "8", "-o", str(archive), base+filenames[0])
    return archive

def snapshot(staging):
    result = {}
    if not staging.exists():
        return result
    for p in staging.rglob("*"):
        if not p.is_file() and not p.is_symlink():
            continue
        key = p.relative_to(staging).as_posix()
        if p.is_symlink():
            result[key] = ("link", os.readlink(p))
        else:
            result[key] = ("file", digest(p), p.stat().st_mode & 0o777)
    return result

def upstream(release, sdk, work):
    # Base recipes such as OpenSSL/zlib are not part of the packages feed.
    base = work / "openwrt"
    run("git", "clone", "--depth=1", "--branch", "v"+release,
        "https://github.com/openwrt/openwrt.git", str(base))
    for recipe in ("libs/zlib", "libs/pcre2", "libs/gettext-full", "libs/libiconv-full", "libs/openssl"):
        src = base / "package" / recipe
        if not (src/"Makefile").is_file():
            raise RuntimeError(f"Missing base recipe {recipe} in v{release}")
        dest = sdk/"package"/"feeds"/"base"/src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(src, target_is_directory=True)
    return base

def prepare(sdk, release, component, work):
    # packages feed is resolved from the exact release's feeds.conf.default.
    run("./scripts/feeds", "update", "packages", cwd=sdk)
    run("./scripts/feeds", "install", "rust", "glib2", "dbus", "libffi", "attr", cwd=sdk)
    upstream(release, sdk, work)
    run("make", f"VERSION_NUMBER={release}", "-s", "prepare-tmpinfo", cwd=sdk)
    run("make", f"VERSION_NUMBER={release}", "defconfig", cwd=sdk)
    run("make", f"VERSION_NUMBER={release}", "package/toolchain/compile", "NO_DEPS=1", "-j1", cwd=sdk)
    prerequisites = {
        "rust": [],
        "glib": ["package/feeds/base/zlib/compile", "package/feeds/packages/libffi/compile"],
        "dbus": ["package/feeds/base/zlib/compile", "package/feeds/packages/libffi/compile",
                 "package/feeds/packages/glib2/compile"],
        "openssl": [],
    }
    targets = {
        "rust": "package/feeds/packages/rust/host/compile",
        "glib": "package/feeds/packages/glib2/compile",
        "dbus": "package/feeds/packages/dbus/compile",
        "openssl": "package/feeds/base/openssl/compile",
    }
    for target in [*prerequisites[component], targets[component]]:
        flags = ["CONFIG_OPENSSL_ENGINE=", "CONFIG_OPENSSL_ENGINE_BUILTIN_DEVCRYPTO=",
                 "CONFIG_PACKAGE_libopenssl-devcrypto=", "CONFIG_PACKAGE_libopenssl-afalg=",
                 "CONFIG_PACKAGE_libopenssl-padlock="] if component == "openssl" else []
        run("make", f"VERSION_NUMBER={release}", "CONFIG_PACKAGE_kmod-bluetooth=n",
            *flags, target, "-j1", "V=s", cwd=sdk)

def build(profile, component, target, subtarget, output):
    if component not in COMPONENTS:
        raise ValueError(f"Invalid component: {component}")
    cfg = catalog().get(profile)
    if not cfg:
        raise ValueError(f"Unknown profile: {profile}")
    if f"{target}/{subtarget}" not in cfg["targets"]:
        raise ValueError("Target is not part of this profile")
    release, arch = cfg["release"], cfg["arch"]
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sdk-extended-") as tmp:
        work = Path(tmp)
        archive = sdk_download(release, target, subtarget, output / "cache")
        upstream_hash = digest(archive)
        extract = work / "sdk"
        extract.mkdir()
        run("tar", "-xf", str(archive), "-C", str(extract))
        roots = [p for p in extract.iterdir() if p.is_dir()]
        if len(roots) != 1:
            raise RuntimeError("Official SDK must have one root directory")
        sdk = roots[0]
        before = snapshot(sdk/"staging_dir")
        prepare(sdk, release, component, work)
        after = snapshot(sdk/"staging_dir")
        changed = [name for name, signature in after.items() if before.get(name) != signature]
        if not changed:
            raise RuntimeError("No staging files were added or changed; refusing empty extension")
        name = f"openwrt-sdk-ext-{release}-{arch}-{target}-{subtarget}-{component}"
        artifact = output / (name+".tar.gz")
        manifest = {
            "schema": 1, "release": release, "arch": arch,
            "target": target, "subtarget": subtarget, "component": component,
            "official_sdk_filename": archive.name, "official_sdk_sha256": upstream_hash,
            "files": changed,
        }
        manifest_file = work / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2)+"\n")
        with tarfile.open(artifact, "w:gz", dereference=False) as tar:
            tar.add(manifest_file, arcname="extension-manifest.json")
            for rel in changed:
                tar.add(sdk/"staging_dir"/rel, arcname="staging_dir/"+rel, recursive=False)
        (output/(name+".sha256")).write_text(f"{digest(artifact)}  {artifact.name}\n")
        print(f"Created {artifact} ({len(changed)} staging entries)")
        return artifact

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--component", choices=COMPONENTS, required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--subtarget", required=True)
    p.add_argument("--output", type=Path, default=Path("dist"))
    a=p.parse_args()
    build(a.profile, a.component, a.target, a.subtarget, a.output)

if __name__ == "__main__":
    main()
