from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import __version__
from .constants import GITHUB_REPO, RELEASES_URL


@dataclass
class UpdateInfo:
    current: str
    latest: str
    notes: str
    url: str
    available: bool


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


def check_for_updates(repo: str | None = None, timeout: float = 10.0) -> UpdateInfo:
    repo = (repo or GITHUB_REPO).strip()
    current = __version__
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"MSFS-Resume/{current}",
            "Accept": "application/vnd.github+json",
        },
    )
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
    available = bool(latest) and is_newer(latest, current)
    return UpdateInfo(current, latest or current, notes, html, available)
