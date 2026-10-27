# openwrt-sdk-extended

Reproducible extensions for the **official** OpenWrt SDK. This repository is independent of AudioWRT.

## Profiles

Profiles are organized under `profiles/<openwrt-release>/<arch>-<variant>.json`.

- `full` requests Rust, GLib, D-Bus, and OpenSSL development preparation.
- `rust` requests Rust alone.
- `glib` requests GLib and D-Bus.

Versions: **25.12.6** (MIPS, ARMv7, AArch64, x86_64) and **25.12.5** (MIPS, ARMv7). ARMv7 lists both `ipq40xx/generic` and `bcm27xx/bcm2709` as distinct SDK targets.

Profiles describe **build requests**, not proof that binaries can be reused between different OpenWrt targets. Each target must be validated against its official SDK and ABI.

```sh
python3 scripts/profiles.py list
python3 scripts/profiles.py show --profile 25.12.6/mips_24kc-full
python3 scripts/profiles.py matrix
python3 scripts/profiles.py validate
```

## Status

Profile layout and CI profile validation are implemented. The SDK extension **builder, binary packaging, compatibility validation, installer and GitHub Release publisher are not yet implemented**; these profiles alone do not create precompiled components. Do not use these declarations as proof of build support.
