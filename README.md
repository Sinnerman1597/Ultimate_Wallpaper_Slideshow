# Ultimate Wallpaper Slideshow (UWS)

Windows 桌布輪播與圖片快速預覽工具。  
支援多螢幕獨立來源、圖片／影片桌布、階層式來源管理，以及與桌布完全分離的預覽刪圖模式。

> 開發語言：Python 3 + PySide6  
> 平台：Windows（依賴 Win32／IDesktopWallpaper／可選 portable mpv）

---

## 功能概覽

### 一、桌布模式

| 功能 | 說明 |
|------|------|
| 圖片桌布 | 智慧 Fit 縮放、邊緣色留白、右上角檔名 |
| 影片桌布 | 透過專案內 portable **mpv** 播放（可多螢幕各一支） |
| 來源管理 | 資料夾（階層／僅本層）、單檔圖片、單檔影片，分三區顯示 |
| 播放 | 順序／隨機；多種更新週期；「播完為止(僅影片)」 |
| 多螢幕 | 所有螢幕同步，或螢幕1／2… 各自來源與週期 |
| 互斥 | 同步與各別螢幕邏輯分離；未再設定的螢幕可跟隨最後一次同步來源 |
| 浮動工具列 | 各螢幕右下：上一張／下一張／暫停／刪除（進資源回收筒） |
| 恢復系統桌布 | 一鍵停止輪播並還原啟動時的系統桌布；關閉程式時也會還原 |
| 設定記憶 | 來源列表與各螢幕設定寫入 `config.json` |

### 二、預覽模式（與桌布獨立）

| 操作 | 說明 |
|------|------|
| 開啟資料夾 | 載入該層圖片（不遞迴） |
| 上一張 | `A` 或 `←` |
| 下一張 | `D` 或 `→` |
| 刪除 | `W` 或 `↑`（進資源回收筒，並顯示下一張） |

預覽不修改系統桌布、不啟動 mpv，方便快速決定保留或刪除。

---

## 環境需求

- Windows 10／11  
- Python 3.10+（建議）  
- 依賴套件：

```text
PySide6
Pillow
pywin32
comtypes
Send2Trash
```

- 影片桌布：將 **mpv** 解壓到專案目錄：

```text
Ultimate_Wallpaper_Slideshow/
  mpv/
    mpv.exe
    ...
  main.py
  ...
```

---

## 安裝與啟動

### 1. 建立虛擬環境並安裝依賴

```powershell
cd D:\Code\Ultimate_Wallpaper_Slideshow
python -m venv wallpaper_env
.\wallpaper_env\Scripts\Activate.ps1
pip install PySide6 Pillow pywin32 comtypes Send2Trash
```

### 2. 命令列啟動

```powershell
python main.py
```

### 3. 無黑窗啟動（建議）

建立捷徑，目標指向：

```text
...\wallpaper_env\Scripts\pythonw.exe "...\main.py"
```

「起始位置」設為專案根目錄。可釘選到工作列並自訂圖示。

> 不建議用 `.bat` 當日常入口（會跳出 cmd 視窗）。

---

## 使用說明

### 桌布

1. 左側切換到 **「桌布」**。  
2. **新增資料夾／新增檔案**，勾選要使用的來源。  
3. 資料夾可展開子層；**雙擊**資料夾可切換【僅本層】。  
4. 母資料夾勾選會連動子層勾選；【僅本層】優先於子層勾選。  
5. 右側選擇螢幕（同步或螢幕 N）、更新週期、播放模式。  
6. 按 **「調整來源」→ 勾選 →「確認」** 套用到目前設定的螢幕。  
7. 各螢幕浮動工具列可手動切換、暫停、刪除目前檔案。  
8. **「恢復系統桌布」** 會停止輪播並還原系統桌布；需再次「確認」才會繼續輪播。

### 預覽

1. 左側切換到 **「預覽」**。  
2. **開啟資料夾** 後用按鈕或鍵盤快速瀏覽／刪除。  
3. 與桌布設定互不干擾。

---

## 專案結構

```text
Ultimate_Wallpaper_Slideshow/
├── main.py                 # 程式入口
├── config.json             # 執行後產生的設定（可忽略進版控）
├── core/
│   ├── config_manager.py   # 設定讀寫
│   ├── playlist.py         # 播放清單（含隨機歷史）
│   ├── screen_player.py    # 單螢幕輪播邏輯
│   ├── wallpaper_engine.py # 圖片桌布處理
│   └── video_wallpaper.py  # mpv 影片桌布
├── ui/
│   ├── main_window.py      # 主視窗（導航 + 桌布頁）
│   ├── preview_page.py     # 預覽頁
│   └── floating_toolbar.py # 桌面浮動工具列
├── utils/
│   ├── win32_helper.py     # 系統桌布路徑／設定
│   ├── desktop_wallpaper.py# 多螢幕 IDesktopWallpaper
│   └── mpv_helper.py       # 尋找 mpv.exe
└── mpv/                    # portable mpv（勿提交大型二進位可 gitignore）
```

---

## 注意事項

1. **影片桌布**無法 100% 等同 Wallpaper Engine 的桌面最底層；圖示點擊／工作列偶發行為依 Windows 版本可能不同。  
2. 圖片輪播會改寫系統桌布路徑；程式在**啟動時**記住原始桌布，關閉或按「恢復系統桌布」時還原。  
3. `mpv/` 與虛擬環境體積大，建議寫入 `.gitignore`，不要推上 GitHub。  
4. 多螢幕順序以由左至右為準，與工具列對應。

---

## 授權與聲明

個人／學習用途為主。使用 mpv 請遵守其授權條款。  
桌布與預覽刪除皆走資源回收筒，仍請操作前確認路徑無誤。

---

## 版本摘要

- 桌布：多螢幕、圖／影、來源階層、互斥、工具列、系統桌布還原  
- 預覽：獨立頁面、WASD／方向鍵快速瀏覽與刪除  
