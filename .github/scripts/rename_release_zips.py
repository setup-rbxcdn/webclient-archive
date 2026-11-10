#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from releases import make_diff, make_report, write_release_files

REPO = os.environ["GITHUB_REPOSITORY"]
VERSIONS = [
    ("version-f4a4dba57f874ad0", "0.745.0.7451142", "2026-10-28T15:48:18.648161+00:00", "2026-10-28T154818.648161_0000", "Synthle/RobloxWasmClientArchive"),
    ("version-75f1039cb4964863", "0.745.0.7451145", "2026-10-29T17:18:45+00:00", "2026-11-07T203723", "Roblox CDN"),
    ("version-db62701aba0b4bcd", "0.746.0.7461265", "2026-11-04T17:49:58+00:00", "2026-11-07T203840", "Roblox CDN"),
    ("version-f807b21caba84809", "0.747.0.7471481", "2026-11-10T21:10:44.629249+00:00", "2026-11-10T212530", "Roblox CDN"),
]


def run(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout if capture else None


def read_from_zip(path, suffix):
    with zipfile.ZipFile(path) as archive:
        name = next((name for name in archive.namelist() if name.endswith(suffix)), None)
        if not name:
            raise RuntimeError(f"{path} has no {suffix}")
        return json.loads(archive.read(name))


work = Path(os.environ["RUNNER_TEMP"]) / "release-recovery"
work.mkdir()
rdd = Path(os.environ["RUNNER_TEMP"]) / "rdd"
run("git", "clone", "--depth", "1", "https://github.com/setup-rbxcdn/roblox-rdd-downloader.git", str(rdd))
run("npm", "install", "--omit=dev", "--no-audit", "--no-fund", "--prefix", str(rdd))

previous = []
previous_version = None
for version, engine, release_date, stamp, source in VERSIONS:
    folder = work / version
    if source.startswith("Synthle"):
        folder.mkdir()
        source_name = f"{version}-{stamp}.zip"
        url = f"https://github.com/Synthle/RobloxWasmClientArchive/releases/download/webclient-{version}/{source_name}"
        source_zip = work / source_name
        urllib.request.urlretrieve(url, source_zip)
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(work)
        original = read_from_zip(source_zip, "/download-report.json")
    else:
        run("node", str(rdd / "rdd-download.mjs"), "--binaryType", "WebClientApp", "--version", version, "--out", str(folder))
        original = json.loads((folder / "download-report.json").read_text(encoding="utf-8"))

    metadata = json.loads((folder / "WebClient.metadata.json").read_text(encoding="utf-8"))
    diff = make_diff(previous, metadata, previous_version, version)
    report = make_report(original, version, engine, release_date, release_date, source)
    os.chdir(folder)
    write_release_files(diff, report)
    (folder / "download-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    zip_name = f"{engine}-{version}-{stamp}.zip"
    zip_path = work / zip_name
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=work, base_dir=version)
    run(
        "gh", "release", "create", f"webclient-{version}", str(zip_path),
        str(folder / "metadata-diff.json"), str(folder / "download-report.json"),
        "-R", REPO, "--verify-tag", "--title", f"{engine} {version}",
        "--notes-file", str(folder / "release-notes.md"),
    )
    previous, previous_version = metadata, version
