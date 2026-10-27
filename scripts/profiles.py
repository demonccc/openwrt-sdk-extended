#!/usr/bin/env python3
"""Discover and validate versioned SDK extension profiles."""
import argparse
import json
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {"rust", "glib2", "dbus", "openssl"}
VARIANTS = {"full", "rust", "glib"}

def discover():
    profiles = {}
    for path in sorted((ROOT / "profiles").glob("*/*.yaml")):
        item = yaml.safe_load(path.read_text())
        name = path.relative_to(ROOT / "profiles").with_suffix("").as_posix()
        release, stem = name.split("/", 1)
        assert item["schema"] == 1 and item["release"] == release, path
        assert stem == f'{item["arch"]}-{item["variant"]}', path
        assert item["variant"] in VARIANTS, path
        assert set(item["components"]) <= COMPONENTS and item["components"], path
        assert len(item["targets"]) == len(set(item["targets"])) and item["targets"], path
        assert all(t.count("/") == 1 for t in item["targets"]), path
        if item["variant"] == "full":
            assert set(item["components"]) == COMPONENTS, path
        if item["variant"] == "rust":
            assert item["components"] == ["rust"], path
        if item["variant"] == "glib":
            assert item["components"] == ["glib2", "dbus"], path
        profiles[name] = item
    return profiles

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["list", "show", "matrix", "validate"])
    parser.add_argument("--profile")
    args = parser.parse_args()
    profiles = discover()
    if args.command == "validate":
        print(f"Validated {len(profiles)} extension profiles")
    elif args.command == "list":
        print("\n".join(profiles))
    elif args.command == "show":
        if args.profile not in profiles:
            parser.error("Unknown profile")
        print(json.dumps(profiles[args.profile], indent=2))
    else:
        jobs = [{"profile": name, "release": data["release"],
                 "arch": data["arch"], "variant": data["variant"],
                 "target": target.split("/")[0], "subtarget": target.split("/")[1]}
                for name, data in profiles.items() for target in data["targets"]]
        print(json.dumps({"include": jobs}, separators=(",", ":")))

if __name__ == "__main__":
    main()
