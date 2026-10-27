# openwrt-sdk-extended

Modular precompiled development components for the **official OpenWrt SDK**. Independent of AudioWRT and of any firmware builder.

## Profiles

Each YAML profile lists a release, package architecture and one or more official SDK targets. Targets sharing a package architecture are **not assumed binary interchangeable**.

```text
profiles/
  25.12.6/
    mips_24kc.yaml
    arm_cortex-a7_neon-vfpv4.yaml
    aarch64_cortex-a72.yaml
    x86_64.yaml
  25.12.5/
    mips_24kc.yaml
    arm_cortex-a7_neon-vfpv4.yaml
```

Components are selected independently: `rust`, `glib`, `dbus` or `openssl`. There is no duplicate `full` binary. Consumers can install several independent extensions on their matching official SDK.

## Build

```sh
python3 -m pip install PyYAML
python3 scripts/profiles.py list
python3 scripts/profiles.py validate
python3 scripts/profiles.py matrix

# Runs a heavyweight upstream SDK preparation; use a Docker environment with
# OpenWrt's host build prerequisites installed.
python3 scripts/build.py --profile 25.12.6/mips_24kc \
  --target ath79 --subtarget generic --component rust --output dist
```

The build fetches the official SDK for the selected release and target, stages upstream development dependencies, and packages only files newly added or changed under `staging_dir` into `dist/openwrt-sdk-ext-*.tar.gz`. It also writes a SHA-256 file. It does **not** include a whole SDK or APK binaries for routers.

```sh
python3 scripts/install.py --sdk /path/to/extracted/openwrt-sdk \
  --official-archive /path/to/original/openwrt-sdk.tar.zst \
  --extension dist/openwrt-sdk-ext-....tar.gz
```

The installer verifies the *exact official SDK archive SHA-256* and archive member paths before overlaying the staging files. The SDK directory passed to `--sdk` must be the actual extracted SDK root, not its parent.

## GitHub Actions

The **Build and release SDK extension** workflow accepts profile, target, subtarget and component. It runs only with `workflow_dispatch` and its `publish` input defaults to **false**. A successful manual run uploads the archive as a workflow artifact; choosing `publish=true` also creates a GitHub Release.

## Limitations and validation

The unit tests check YAML definitions and tooling syntax. **The full component builds and real consumer integration have not been executed yet.** Upstream provider dependency graphs and SDK staging behavior can vary by release/target. The initial build may take significant time. Reusing an extension for another target, even with the same package ABI, requires an explicit compatibility check; no automatic cross-target reuse is implemented. The installer deliberately rejects symlinks escaping the SDK. Do not merge or publish as production-ready until at least one clean SDK build and installation is tested.
