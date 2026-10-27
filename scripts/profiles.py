#!/usr/bin/env python3
"""Versioned OpenWrt profile catalog. Profiles describe ABI and official SDK targets."""
import argparse
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("rust", "glib", "dbus", "openssl")

def catalog():
    result = {}
    for path in sorted((ROOT / "profiles").glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        key = path.relative_to(ROOT / "profiles").with_suffix("").as_posix()
        release, arch = key.split("/")
        if data.get("release") != release or data.get("arch") != arch:
            raise ValueError(f"Profile path mismatch: {path}")
        targets = data.get("targets")
        if not isinstance(targets, list) or not targets or len(targets) != len(set(targets)):
            raise ValueError(f"Invalid target list: {path}")
        for target in targets:
            if not isinstance(target, str) or target.count("/") != 1:
                raise ValueError(f"Invalid target {target!r}: {path}")
        result[key] = data
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["list", "show", "matrix", "validate"])
    parser.add_argument("--profile")
    parser.add_argument("--component", choices=COMPONENTS)
    args = parser.parse_args()
    profiles = catalog()
    if args.command == "validate":
        if not profiles:
            parser.error("No YAML profiles")
        print(f"Validated {len(profiles)} profiles")
    elif args.command == "list":
        print("\n".join(profiles))
    elif args.command == "show":
        if args.profile not in profiles:
            parser.error("Unknown profile")
        print(yaml.safe_dump(profiles[args.profile], sort_keys=False))
    else:
        jobs = [{"profile": name, "component": component, "target": target.split("/")[0], "subtarget": target.split("/")[1]}
                for name, info in profiles.items()
                for target in info["targets"]
                for component in (args.component,) if args.component or False]
        if not args.component:
            jobs = [{"profile": name, "component": component, "target": target.split("/")[0], "subtarget": target.split("/")[1]}
                    for name, info in profiles.items()
                    for target in info["targets"]
                    for component in COMPONENTS]
        print(json.dumps({"include": jobs}, separators=(",", ":")))

if __name__ == "__main__":
    main()
