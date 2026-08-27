#!/usr/bin/env python3
"""Download and organize DLC archives from Internet Archive.

Requires `ia`, `aria2c`, and `7z` on PATH. Reads IA_USERNAME/IA_PASSWORD (or
IA_USERNAME_FILE/IA_PASSWORD_FILE, pointing at files containing the values -
e.g. Docker Compose file-based secrets, which avoid Compose's `$`
interpolation of plain environment variable values) to configure the `ia`
CLI if it isn't already configured, then uses `ia configure
--print-auth-header` to authenticate aria2 downloads.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ARCHIVE_EXTENSIONS = (".zip", ".7z")


def _credential(name: str) -> str | None:
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text().strip()
    return os.environ.get(name)


def ensure_ia_configured() -> None:
    check = subprocess.run(["ia", "configure", "--check"], capture_output=True)
    if check.returncode == 0:
        return

    username = _credential("IA_USERNAME")
    password = _credential("IA_PASSWORD")
    if not username or not password:
        sys.exit(
            "ia is not configured and IA_USERNAME/IA_PASSWORD (or "
            "IA_USERNAME_FILE/IA_PASSWORD_FILE) are not set. Set them or "
            "run `ia configure` manually."
        )

    result = subprocess.run(
        ["ia", "configure", "-u", username, "-p", password],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ia configure failed:\n{result.stdout}\n{result.stderr}")


def get_auth_header() -> str:
    result = subprocess.run(
        ["ia", "configure", "--print-auth-header"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"Failed to retrieve IA auth header:\n{result.stderr}")

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.lower().startswith("authorization:"):
            return line
    sys.exit(f"Could not parse Authorization header from:\n{result.stdout}")


def download_archives(urls, dlc_dir: Path, connections: int, parallelism: int, auth_header: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(urls) + "\n")
        url_list_path = f.name

    cmd = [
        "aria2c",
        "-i", url_list_path,
        "-d", str(dlc_dir),
        "-x", str(connections),
        "-s", str(connections),
        "-j", str(parallelism),
        "--header", auth_header,
        "--auto-file-renaming=false",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"aria2c exited with code {result.returncode}; aborting before extraction.")


def extract_and_cleanup(dlc_dir: Path) -> list:
    failures = []
    archives = sorted(
        p for p in dlc_dir.iterdir()
        if p.is_file() and p.suffix.lower() in ARCHIVE_EXTENSIONS
    )
    for archive in archives:
        dest_dir = dlc_dir / archive.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"Extracting {archive.name} -> {dest_dir}")
        result = subprocess.run(
            ["7z", "x", str(archive), f"-o{dest_dir}", "-y"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED to extract {archive.name}:\n{result.stderr}")
            failures.append(archive.name)
            continue
        archive.unlink()
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Friendly name for this download batch")
    parser.add_argument("--urls", required=True, nargs="+", help="Space-separated list of IA download URLs")
    parser.add_argument("--output-dir", required=True, help="Base output directory")
    parser.add_argument("--connections", type=int, default=4, help="aria2 connections per download (default: 4)")
    parser.add_argument("--parallelism", type=int, default=2, help="Number of simultaneous downloads (default: 2)")
    args = parser.parse_args()

    # Defensively re-split in case a single quoted string was passed.
    urls = [u for token in args.urls for u in token.split()]
    if not urls:
        sys.exit("No URLs provided.")

    ensure_ia_configured()
    auth_header = get_auth_header()

    dlc_dir = Path(args.output_dir) / args.name / "dlc"
    dlc_dir.mkdir(parents=True, exist_ok=True)

    download_archives(urls, dlc_dir, args.connections, args.parallelism, auth_header)
    failures = extract_and_cleanup(dlc_dir)

    print(f"\nDone. Output: {dlc_dir}")
    if failures:
        print(f"Extraction failed for {len(failures)} archive(s): {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
