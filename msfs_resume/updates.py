from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .constants import GITHUB_REPO, RELEASES_URL

ProgressFn = Callable[[int, int], None]


@dataclass
class UpdateInfo:
    current: str
    latest: str
    notes: str
    url: str
    available: bool
    installer_url: str = ""
    installer_name: str = ""


def _parse(version: str) -> tuple[int, ...]:
    parts = []
    for item in version.strip().lstrip("vV").split("."):
        num = ""
        for ch in item:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num or 0))
    return tuple(parts or (0,))


def is_newer(latest: str, current: str) -> bool:
    return _parse(latest) > _parse(current)


def installer_asset(assets: list | None) -> tuple[str, str]:
    """Return (filename, download_url) for MSFSResumeSetup-*.exe."""
    items = assets or []
    preferred = []
    fallback = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        url = str(item.get("browser_download_url") or "")
        if not name or not url:
            continue
        lower = name.lower()
        if not lower.endswith(".exe"):
            continue
        if lower.startswith("msfsresumesetup-"):
            preferred.append((name, url))
        else:
            fallback.append((name, url))
    chosen = preferred or fallback
    return chosen[0] if chosen else ("", "")


def installer_dest(filename: str) -> Path:
    downloads = Path.home() / "Downloads"
    folder = downloads if downloads.is_dir() else Path.home() / "AppData" / "Roaming" / "MsfsResume"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / filename


def _headers() -> dict[str, str]:
    return {
        "User-Agent": f"MSFS-Resume/{__version__}",
        "Accept": "application/vnd.github+json",
    }


def check_for_updates(repo: str | None = None, timeout: float = 10.0) -> UpdateInfo:
    repo = (repo or GITHUB_REPO).strip()
    current = __version__
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateInfo(current, current, "", RELEASES_URL, False)
        raise RuntimeError(f"Update check failed (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not check for updates: {exc.reason}") from exc
    latest = str(data.get("tag_name") or data.get("name") or "").strip()
    notes = str(data.get("body") or "").strip()
    html = str(data.get("html_url") or RELEASES_URL)
    name, installer = installer_asset(data.get("assets"))
    available = bool(latest) and is_newer(latest, current)
    return UpdateInfo(current, latest or current, notes, html, available, installer, name)


def download_installer(
    url: str,
    dest: Path,
    progress: ProgressFn | None = None,
    should_cancel: Callable[[], bool] | None = None,
    timeout: float = 60.0,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"MSFS-Resume/{__version__}",
            "Accept": "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            total = int(response.headers.get("Content-Length") or 0)
            got = 0
            with part.open("wb") as out:
                while True:
                    if should_cancel and should_cancel():
                        raise RuntimeError("Download cancelled.")
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    got += len(chunk)
                    if progress:
                        progress(got, total)
        part.replace(dest)
    except Exception:
        if part.exists():
            part.unlink(missing_ok=True)
        raise
    return dest
