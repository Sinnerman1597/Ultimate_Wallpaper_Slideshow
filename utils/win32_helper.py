import ctypes

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
