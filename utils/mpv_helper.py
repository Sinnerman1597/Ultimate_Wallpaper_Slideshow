from pathlib import Path
import subprocess


def get_mpv_path() -> Path | None:
    """專案內 portable mpv 路徑"""
    # 專案根目錄 / mpv / mpv.exe
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "mpv" / "mpv.exe",
        Path(r"D:\Code\Ultimate_Wallpaper_Slideshow\mpv\mpv.exe"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def mpv_available() -> bool:
    return get_mpv_path() is not None


def mpv_version() -> str:
    exe = get_mpv_path()
    if not exe:
        return ""
    try:
        r = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(
                subprocess, "CREATE_NO_WINDOW") else 0,
        )
        line = (r.stdout or "").splitlines()
        return line[0] if line else "mpv ok"
    except Exception as e:
        return f"error: {e}"
