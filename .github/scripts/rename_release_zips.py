#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = os.environ["GITHUB_REPOSITORY"]


def run(*args, capture=False):
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout if capture else None


releases = json.loads(run("gh", "api", f"repos/{REPO}/releases?per_page=100", capture=True))
releases.reverse()

with tempfile.TemporaryDirectory() as temp_name:
    temp = Path(temp_name)
    saved = []
    for release in releases:
        folder = temp / release["tag_name"]
        folder.mkdir()
        run("gh", "release", "download", release["tag_name"], "-R", REPO, "--dir", str(folder))
        zips = list(folder.glob("*.zip"))
        if len(zips) != 1:
            raise RuntimeError(f"expected one ZIP for {release['tag_name']}, found {len(zips)}")
        old_zip = zips[0]
        engine = release["name"].split(" ", 1)[0]
        new_zip = old_zip.with_name(f"{engine}-{old_zip.name}")
        old_zip.rename(new_zip)
        notes = folder / "release-notes.md"
        notes.write_text(release["body"], encoding="utf-8")
        saved.append((release, folder, new_zip, notes))

    # Every release and asset is local before anything is removed.
    for release, _, _, _ in saved:
        run("gh", "release", "delete", release["tag_name"], "-R", REPO, "--yes")

    for release, folder, new_zip, notes in saved:
        run(
            "gh", "release", "create", release["tag_name"],
            str(new_zip), str(folder / "metadata-diff.json"), str(folder / "download-report.json"),
            "-R", REPO, "--target", release["target_commitish"],
            "--title", release["name"], "--notes-file", str(notes),
        )
