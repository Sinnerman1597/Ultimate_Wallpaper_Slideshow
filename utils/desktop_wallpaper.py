import comtypes
from comtypes import GUID, HRESULT, COMMETHOD, CoCreateInstance
from ctypes import POINTER, c_uint
from ctypes.wintypes import LPCWSTR, LPWSTR, RECT, UINT
from comtypes import IUnknown
from PySide6.QtWidgets import QApplication

# IDesktopWallpaper GUID
CLSID_DesktopWallpaper = GUID("{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}")
IID_IDesktopWallpaper = GUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")


class IDesktopWallpaper(IUnknown):
    _iid_ = IID_IDesktopWallpaper
    _methods_ = [
        COMMETHOD([], HRESULT, "SetWallpaper",
                  (["in"], LPCWSTR, "monitorID"),
                  (["in"], LPCWSTR, "wallpaper")),
        COMMETHOD([], HRESULT, "GetWallpaper",
                  (["in"], LPCWSTR, "monitorID"),
                  (["out"], POINTER(LPWSTR), "wallpaper")),
        COMMETHOD([], HRESULT, "GetMonitorDevicePathAt",
                  (["in"], UINT, "monitorIndex"),
                  (["out"], POINTER(LPWSTR), "monitorID")),
        COMMETHOD([], HRESULT, "GetMonitorDevicePathCount",
                  (["out"], POINTER(UINT), "count")),
        COMMETHOD([], HRESULT, "GetMonitorRECT",
                  (["in"], LPCWSTR, "monitorID"),
                  (["out"], POINTER(RECT), "displayRect")),
        # 後面還有其他方法，這裡只定義我們需要的
        COMMETHOD([], HRESULT, "SetBackgroundColor",
                  (["in"], c_uint, "color")),
        COMMETHOD([], HRESULT, "GetBackgroundColor",
                  (["out"], POINTER(c_uint), "color")),
        COMMETHOD([], HRESULT, "SetPosition",
                  (["in"], c_uint, "position")),
        COMMETHOD([], HRESULT, "GetPosition",
                  (["out"], POINTER(c_uint), "position")),
    ]


def get_desktop_wallpaper():
    return CoCreateInstance(CLSID_DesktopWallpaper, interface=IDesktopWallpaper)


def get_monitor_ids():
    """回傳目前有效的螢幕 device path 列表"""
    dw = get_desktop_wallpaper()
    count = dw.GetMonitorDevicePathCount()
    ids = []
    for i in range(count):
        monitor_id = dw.GetMonitorDevicePathAt(i)
        try:
            rect = dw.GetMonitorRECT(monitor_id)
            if rect.right > rect.left and rect.bottom > rect.top:
                ids.append(monitor_id)
        except Exception:
            continue
    return ids


def get_primary_monitor_id():
    """取得主螢幕的 device path"""
    # 用 Qt 找出主螢幕的幾何位置，再對應到 IDesktopWallpaper 的 ID
    primary = QApplication.primaryScreen()
    prim_geo = primary.geometry()

    dw = get_desktop_wallpaper()
    count = dw.GetMonitorDevicePathCount()
    for i in range(count):
        monitor_id = dw.GetMonitorDevicePathAt(i)
        try:
            rect = dw.GetMonitorRECT(monitor_id)
            # 比對位置（允許一點誤差）
            if (abs(rect.left - prim_geo.x()) < 5 and
                    abs(rect.top - prim_geo.y()) < 5):
                return monitor_id
        except Exception:
            continue
    # 找不到就回傳第一個
    ids = get_monitor_ids()
    return ids[0] if ids else None


def set_wallpaper_for_monitor(monitor_id: str, image_path: str):
    """為指定螢幕設定桌布"""
    dw = get_desktop_wallpaper()
    dw.SetWallpaper(monitor_id, image_path)


def set_wallpaper_all(image_path: str):
    """所有螢幕設定同一張（monitorID 傳 None）"""
    dw = get_desktop_wallpaper()
    dw.SetWallpaper(None, image_path)
