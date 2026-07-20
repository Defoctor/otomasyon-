import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from app.core.exceptions import ConfigurationError


def resolve_media_tool(name: str, configured_path: str = "") -> Path:
    candidates: list[Path] = []
    if configured_path:
        candidates.append(Path(configured_path))
    discovered = shutil.which(name)
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(_windows_user_path_candidates(name))
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        package_root = (
            Path(local_app_data)
            / "Microsoft"
            / "WinGet"
            / "Packages"
            / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        )
        try:
            candidates.extend(package_root.glob(f"ffmpeg-*/bin/{name}.exe"))
        except OSError:
            pass

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ConfigurationError(
        f"{name} was not found. Install Gyan.FFmpeg with winget, open a "
        "new VS Code terminal, or set its explicit path in .env."
    )


def run_checked(command: list[str], label: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()[-2000:]
        raise RuntimeError(
            f"{label} failed with exit code {exc.returncode}: {details}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"{label} exceeded the 600 second timeout.") from exc


def probe_media(path: Path, ffprobe_path: Path) -> dict[str, Any]:
    result = run_checked(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_name,codec_type,width,"
            "height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        f"FFprobe inspection for {path.name}",
    )
    return json.loads(result.stdout)


def _windows_user_path_candidates(name: str) -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment"
        ) as key:
            user_path, _ = winreg.QueryValueEx(key, "Path")
    except OSError:
        return []
    result = []
    for entry in str(user_path).split(";"):
        expanded = os.path.expandvars(entry.strip())
        if expanded:
            result.append(Path(expanded) / f"{name}.exe")
    return result
