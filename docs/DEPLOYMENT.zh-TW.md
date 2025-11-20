# 部署指南 (Deployment Guide)

本指南涵蓋 AI Trading Journal 應用程式的安裝、設定與執行步驟。

## 📦 本地部署 (推薦)

由於本應用程式採用 **隱私優先 (Local-First)** 設計，我們強烈建議您在自己的機器上執行。

### 前置需求

- **作業系統**: Linux, macOS, 或 Windows (建議使用 WSL2)
- **Python**: 版本 3.11+
- **套件管理器**: [uv](https://github.com/astral-sh/uv) (必須使用，用於依賴管理)

### 安裝步驟

1.  **複製專案**
    ```bash
    git clone https://github.com/yourusername/ai-trading-journal.git
    cd ai-trading-journal
    ```

2.  **初始化環境**
    我們使用 `uv` 進行快速且可靠的依賴管理。
    ```bash
    uv sync
    ```
    此指令會自動建立 `.venv` 虛擬環境並安裝所有鎖定的套件。

3.  **設定環境變數**
    建立您的本地設定檔：
    ```bash
    cp .env.example .env
    ```

    **環境變數說明：**

    | 變數名稱 | 說明 | 預設值 | 是否必填 |
    |----------|-------------|---------|----------|
    | `LLM_API_KEY` | AI 分析用的 API 金鑰 (如 OpenAI) | 無 | 否 (若無則停用分析功能) |
    | `LLM_API_ENDPOINT` | 自訂 LLM 端點網址 | https://api.openai.com... | 否 |
    | `DB_PATH` | SQLite 資料庫路徑 | `trading_journal.db` | 否 |
    | `CACHE_TTL_MARKET_DATA` | 即時數據快取時間 (秒) | `300` (5分鐘) | 否 |

4.  **啟動應用程式**
    啟動 Streamlit 伺服器：
    ```bash
    uv run streamlit run pages/6_GEX_Sentinel.py
    ```
    應用程式應會自動在瀏覽器中開啟，網址為 `http://localhost:8501`。

## 🔧 故障排除 (Troubleshooting)

### 常見問題

**1. `ModuleNotFoundError`**
- **原因**: 虛擬環境未啟動或依賴未安裝。
- **解決方法**: 確保使用 `uv run ...` 執行指令，或透過 `source .venv/bin/activate` 啟用環境。

**2. "Rate Limit Exceeded" (yfinance)**
- **原因**: 短時間內對 Yahoo Finance 發送過多請求。
- **解決方法**: 應用程式內建快取機制 (`CACHE_TTL_MARKET_DATA`)。請稍待數分鐘後再重新整理。

**3. Database Locked (資料庫鎖定)**
- **原因**: 多個應用程式實例同時嘗試寫入 SQLite。
- **解決方法**: 確保只有一個應用程式實例正在執行。

## ☁️ 雲端部署 (選用)

雖然不是主要目標環境，但您仍可將此專案部署至 Streamlit Community Cloud：

1.  將程式碼推送到 GitHub。
2.  將 Repo 連結至 Streamlit Cloud。
3.  **重要**: 將您的 `.env` 機密資訊 (如 `LLM_API_KEY`) 加入 Streamlit Cloud 的 "Secrets" 管理控制台。**切勿**將 `.env` 檔案提交至 Git。
