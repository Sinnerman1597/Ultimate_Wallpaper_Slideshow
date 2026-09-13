from pathlib import Path
from PIL import Image
import tempfile
from utils.win32_helper import set_wallpaper
from utils.desktop_wallpaper import (
    get_primary_monitor_id,
    set_wallpaper_for_monitor,
    set_wallpaper_all
)
from PySide6.QtWidgets import QApplication


class WallpaperEngine:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "wallpaper_tool"
        self.temp_dir.mkdir(exist_ok=True)

    def _get_edge_color(self, img: Image.Image, sample=15):
        """取邊緣平均色（輕量）"""
        w, h = img.size
        pixels = []
        step_x = max(1, w // sample)
        step_y = max(1, h // sample)
        for x in range(0, w, step_x):
            pixels.append(img.getpixel((x, 0)))
            pixels.append(img.getpixel((x, h - 1)))
        for y in range(0, h, step_y):
            pixels.append(img.getpixel((0, y)))
            pixels.append(img.getpixel((w - 1, y)))
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        return (r, g, b)

    def apply_smart_fill(self, image_path: str, screen_width: int = None, screen_height: int = None,
                         show_filename: bool = True, screen_mode: str = "所有螢幕同步"):
        """
        智慧縮放 + 右上角檔名 + 多螢幕支援
        """
        if screen_width is None or screen_height is None:
            screen = QApplication.primaryScreen()
            size = screen.size()
            screen_width = size.width()
            screen_height = size.height()

        img = Image.open(image_path).convert("RGB")
        img_w, img_h = img.size

        # ===== Fit 模式：完整顯示，不裁切 =====
        # 計算等比例縮放後的尺寸
        ratio = min(screen_width / img_w, screen_height / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 用邊緣色當背景
        bg_color = self._get_edge_color(img)
        background = Image.new("RGB", (screen_width, screen_height), bg_color)

        # 置中貼上
        x = (screen_width - new_w) // 2
        y = (screen_height - new_h) // 2
        background.paste(img, (x, y))
        img = background

        # ===== 右上角檔名浮水印 =====
        if show_filename:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            filename = Path(image_path).name
            try:
                font = ImageFont.truetype("msyh.ttc", 14)   # 縮小字體
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), filename, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            margin = 10
            x = screen_width - text_w - margin
            y = margin

            folder_name = Path(image_path).parent.name
            filename = f"{folder_name}-{Path(image_path).name}"
            # 直接黑字，沒有黑底
            draw.text((x, y), filename, font=font, fill=(0, 0, 0))

        # 每個螢幕用不同暫存檔，避免互相覆蓋導致閃圖
        if screen_mode == "所有螢幕同步":
            temp_name = "current_wallpaper_all.jpg"
        elif screen_mode.startswith("螢幕"):
            num = screen_mode.replace("螢幕", "").strip()
            temp_name = f"current_wallpaper_{num}.jpg"
        else:
            temp_name = "current_wallpaper.jpg"

        temp_path = self.temp_dir / temp_name
        img.save(temp_path, quality=92)
        temp_path_str = str(temp_path)

        # ===== 多螢幕設定 =====
        try:
            from utils.desktop_wallpaper import (
                get_monitor_ids, get_primary_monitor_id,
                set_wallpaper_for_monitor, set_wallpaper_all
            )

            if screen_mode == "所有螢幕同步":
                set_wallpaper_all(temp_path_str)
            elif screen_mode.startswith("螢幕"):
                # 取出數字，例如「螢幕2」→ 2
                try:
                    screen_num = int(screen_mode.replace("螢幕", ""))
                    monitor_ids = get_monitor_ids()
                    if 1 <= screen_num <= len(monitor_ids):
                        target_id = monitor_ids[screen_num - 1]
                        set_wallpaper_for_monitor(target_id, temp_path_str)
                    else:
                        # 超出範圍就退回全部
                        set_wallpaper_all(temp_path_str)
                except Exception:
                    set_wallpaper_all(temp_path_str)
            else:
                # 舊的「僅主螢幕」相容
                primary_id = get_primary_monitor_id()
                if primary_id:
                    set_wallpaper_for_monitor(primary_id, temp_path_str)
                else:
                    set_wallpaper_all(temp_path_str)
        except Exception as e:
            print(f"多螢幕設定失敗，退回舊方法: {e}")
            from utils.win32_helper import set_wallpaper
            set_wallpaper(temp_path_str)

        return temp_path_str
