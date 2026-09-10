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
