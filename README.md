# webclient-archive

Archive of Roblox `WebClientApp` (wasm browser client) builds. Release tags use `webclient-version-<hash>`; titles include engine version and hash.

Builds tend to disappear from the Roblox CDN after a while (for example `version-f4a4dba57f874ad0` now returns 403 for everything), so each new version is saved here while it's still available.

Each release contains:

- `version-<hash>.zip`: build laid out like `https://setup.rbxcdn.com/webclient/<version>-RobloxWebClient/`, plus `WebClient.metadata.json` and `download-report.json`.
- `metadata-diff.json`: added, removed, and changed metadata entries compared with previous release.
- `download-report.json`: version, release/archive dates, source, file counts, status, and failures.

New versions are archived by `.github/workflows/archive.yml`, dispatched from [setup-rbxcdn.github.io](https://github.com/setup-rbxcdn/setup-rbxcdn.github.io) when a new `WebClientApp` version appears, with a 6-hourly schedule as a fallback. Downloads use [roblox-rdd-downloader](https://github.com/setup-rbxcdn/roblox-rdd-downloader).

Builds that were already gone from the CDN were copied from [Synthle/RobloxWasmClientArchive](https://github.com/Synthle/RobloxWasmClientArchive).
