import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32gui

user32 = ctypes.windll.user32
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02


def set_wallpaper(image_path: str):
    """設定整桌面壁紙（最簡單可靠的方式）"""
    path = str(image_path)
    result = user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, path,
        SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
    )
    return bool(result)


def get_screen_info():
    """取得所有螢幕資訊"""
    screens = []
    for i in range(win32api.GetSystemMetrics(80)):  # SM_CMONITORS
        # 簡化版，之後會用更精準的 EnumDisplayMonitors
        pass
    # 先用 Qt 的 QScreen 會更準，這個之後補
    return screens


def get_system_wallpaper_path() -> str:
    """從登錄讀取使用者目前的桌布路徑"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_READ,
        )
        path, _ = winreg.QueryValueEx(key, "Wallpaper")
        winreg.CloseKey(key)
        return str(path).strip() if path else ""
    except Exception:
        return ""


def restore_system_wallpaper() -> bool:
    """
    恢復系統桌布（所有螢幕跟回系統設定）。
    優先用登錄裡的 Wallpaper 路徑再套用一次。
    """
    path = get_system_wallpaper_path()
    if path:
        from pathlib import Path
        if Path(path).is_file():
            return set_wallpaper(path)

    # 找不到檔案時：仍呼叫一次 SPI，讓 Shell 重讀目前設定
    try:
        result = user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, path or None,
            SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
        )
        return bool(result)
    except Exception:
        return False
