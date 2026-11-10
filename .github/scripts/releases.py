#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "setup-rbxcdn/webclient-archive")
HISTORY_URL = "https://raw.githubusercontent.com/setup-rbxcdn/setup-rbxcdn.github.io/main/version-history-inverted/Web/WebClientApp.json"
DATES_URL = "https://raw.githubusercontent.com/setup-rbxcdn/setup-rbxcdn.github.io/main/hash-metadata.json"


def fetch_json(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def run(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout if capture else None


def metadata_from_zip(path, version):
    wanted = f"{version}/WebClient.metadata.json"
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        name = wanted if wanted in names else next((n for n in names if n.endswith("/WebClient.metadata.json")), None)
        if not name:
            raise RuntimeError(f"{path} has no WebClient.metadata.json")
        return json.loads(archive.read(name))


def report_from_zip(path):
    with zipfile.ZipFile(path) as archive:
        name = next((n for n in archive.namelist() if n.endswith("/download-report.json")), None)
        if not name:
            raise RuntimeError(f"{path} has no download-report.json")
        return json.loads(archive.read(name))


def keyed(metadata):
    return {entry["path"]: entry for entry in metadata}


def make_diff(previous, current, previous_version, version):
    old, new = keyed(previous), keyed(current)
    return {
        "previousVersion": previous_version,
        "version": version,
        "added": [new[path] for path in sorted(new.keys() - old.keys())],
        "removed": [old[path] for path in sorted(old.keys() - new.keys())],
        "changed": [
            {"path": path, "old": old[path], "new": new[path]}
            for path in sorted(old.keys() & new.keys()) if old[path] != new[path]
        ],
    }


def make_report(original, version, engine, release_date, archived_at, source):
    failures = original.get("failures", [])
    existing_files = original.get("files", {})
    total = original.get("manifestAndBootstrapFiles", original.get("metadataFiles", existing_files.get("listed", 0)))
    failed = len(failures)
    available = original.get("downloadedOrCached", existing_files.get("available", total - failed))
    return {
        "version": version,
        "engineVersion": engine,
        "releaseDate": release_date,
        "archivedAt": archived_at,
        "source": source,
        "status": "partial" if failed else "complete",
        "files": {"listed": total, "available": available, "failed": failed},
        "failures": failures,
    }


def write_release_files(diff, report):
    Path("metadata-diff.json").write_text(json.dumps(diff, indent=2) + "\n", encoding="utf-8")
    Path("download-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    counts = (len(diff["added"]), len(diff["removed"]), len(diff["changed"]))
    files = report["files"]
    notes = (
        f"WebClientApp archive for `{report['version']}`.\n\n"
        f"Roblox release date: {report['releaseDate']}\n\n"
        f"Archive status: **{report['status']}** ({files['available']}/{files['listed']} files available; {files['failed']} failed).\n\n"
        f"Metadata changes from previous release: +{counts[0]} / -{counts[1]} / ~{counts[2]}.\n\n"
        "Assets: complete version folder ZIP, metadata diff, and download report."
    )
    Path("release-notes.md").write_text(notes + "\n", encoding="utf-8")


def build():
    hash_value = os.environ["HASH"]
    version = f"version-{hash_value}"
    directory = Path(version)
    engine = os.environ["ENGINE_VERSION"]
    release_date = os.environ["RELEASE_DATE"]
    report_path = directory / "download-report.json"
    original = json.loads(report_path.read_text(encoding="utf-8"))
    archived_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    previous = []
    previous_version = None
    releases = json.loads(run("gh", "api", f"repos/{REPO}/releases?per_page=100", capture=True))
    dates = fetch_json(DATES_URL)["Web"]["WebClientApp"]
    older = [v for v in dates if dates[v] < release_date and any(r["tag_name"] == f"webclient-{v}" for r in releases)]
    if older:
        previous_version = max(older, key=dates.get)
        with tempfile.TemporaryDirectory() as temp:
            run("gh", "release", "download", f"webclient-{previous_version}", "-R", REPO, "--pattern", "*.zip", "--dir", temp)
            previous = metadata_from_zip(next(Path(temp).glob("*.zip")), previous_version)
    current = json.loads((directory / "WebClient.metadata.json").read_text(encoding="utf-8"))
    diff = make_diff(previous, current, previous_version, version)
    report = make_report(original, version, engine, release_date, archived_at, "Roblox CDN")
    write_release_files(diff, report)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shutil.make_archive(version, "zip", root_dir=".", base_dir=version)


def migrate():
    checkout = str(Path.cwd())
    history = fetch_json(HISTORY_URL)
    dates = fetch_json(DATES_URL)["Web"]["WebClientApp"]
    releases = json.loads(run("gh", "api", f"repos/{REPO}/releases?per_page=100", capture=True))
    by_version = {r["tag_name"].removeprefix("webclient-"): r for r in releases}
    versions = sorted(by_version, key=dates.get)
    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)
        records = []
        previous_metadata = []
        previous_version = None
        parent = run("git", "rev-parse", "HEAD", capture=True).strip()
        tree = run("git", "rev-parse", "HEAD^{tree}", capture=True).strip()
        for version in versions:
            release = by_version[version]
            folder = temp / version
            folder.mkdir()
            run("gh", "release", "download", release["tag_name"], "-R", REPO, "--dir", str(folder))
            zip_path = next(folder.glob("*.zip"))
            metadata = metadata_from_zip(zip_path, version)
            original = report_from_zip(zip_path)
            diff = make_diff(previous_metadata, metadata, previous_version, version)
            source = "Synthle/RobloxWasmClientArchive" if version == "version-f4a4dba57f874ad0" else "Roblox CDN"
            report = make_report(original, version, history[version], dates[version], release["published_at"], source)
            commit_env = os.environ.copy()
            commit_env.update({
                "GIT_AUTHOR_NAME": "github-actions[bot]",
                "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                "GIT_COMMITTER_NAME": "github-actions[bot]",
                "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                "GIT_AUTHOR_DATE": dates[version],
                "GIT_COMMITTER_DATE": dates[version],
            })
            commit = subprocess.run(
                ["git", "commit-tree", tree, "-p", parent, "-m", f"Archive {version}"],
                check=True, text=True, capture_output=True, env=commit_env,
            ).stdout.strip()
            records.append((version, folder, zip_path, diff, report, release["tag_name"], commit))
            previous_metadata, previous_version = metadata, version
            parent = commit

        # Make dated release commits visible to GitHub before release creation.
        run("git", "-C", checkout, "push", "origin", f"{parent}:refs/heads/release-migration")

        # All assets are now local and readable. Only now remove old releases/tags.
        for _, _, _, _, _, tag, _ in records:
            run("gh", "release", "delete", tag, "-R", REPO, "--cleanup-tag", "--yes")

        for version, folder, zip_path, diff, report, tag, commit in records:
            os.chdir(folder)
            write_release_files(diff, report)
            run("gh", "release", "create", tag, str(zip_path), "metadata-diff.json", "download-report.json",
                "-R", REPO, "--target", commit, "--title", f"{report['engineVersion']} {version}", "--notes-file", "release-notes.md")
        run("git", "-C", checkout, "push", "origin", "--delete", "release-migration")


if __name__ == "__main__":
    {"build": build, "migrate": migrate}[sys.argv[1]]()
