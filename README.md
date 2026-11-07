# webclient-archive

Archive of Roblox `WebClientApp` (wasm browser client) builds, one release per version: `webclient-version-<hash>`.

Each release contains:

- `version-<hash>-<UTC timestamp>.zip`: the build, laid out like `https://setup.rbxcdn.com/webclient/<version>-RobloxWebClient/`, plus `WebClient.metadata.json` and `download-report.json`.
- `download-report.json`: `status` is `complete` or `partial`; `failures` lists files the CDN refused.

New versions are archived by `.github/workflows/archive.yml`, dispatched from [setup-rbxcdn.github.io](https://github.com/setup-rbxcdn/setup-rbxcdn.github.io) when a new `WebClientApp` version appears, with a 6-hourly schedule as a fallback. Downloads use [roblox-rdd-downloader](https://github.com/setup-rbxcdn/roblox-rdd-downloader).

Builds that were already gone from the CDN were copied from [Synthle/RobloxWasmClientArchive](https://github.com/Synthle/RobloxWasmClientArchive).
