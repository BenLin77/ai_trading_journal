# AI Trading Journal (AI 交易日誌)

一個隱私優先、結合 AI 的市場結構分析工具，專為散戶交易者設計。本應用程式專注於 Gamma Exposure (GEX)、最大痛點 (Max Pain) 和波動率分析，透過本地優先架構提供法人級的市場指標。

## 🚀 核心功能

- **GEX 哨兵觀察清單**: 即時監控 Gamma 曝險與市場結構。
- **隱私優先架構**: 所有資料皆儲存於本地 SQLite 資料庫，無需上傳至外部伺服器。
- **AI 智能分析**: 整合 LLM 協助解讀複雜的市場結構數據。
- **高效能運算**: 透過積極快取與最佳化演算法，實現低延遲更新。
- **波動率視覺化**: 互動式圖表展示 Call/Put 牆、未平倉量 (OI) 分佈與隱含波動率偏斜。

## 🛠️ 技術堆疊

- **語言**: Python 3.11+
- **框架**: Streamlit
- **資料來源**: yfinance
- **資料庫**: SQLite
- **套件管理**: uv

## 🏁 快速開始

### 前置需求

- Python 3.11 或更高版本
- [uv](https://github.com/astral-sh/uv) (極速 Python 套件安裝工具)

### 安裝步驟

1. **複製專案**
   ```bash
   git clone https://github.com/yourusername/ai-trading-journal.git
   cd ai-trading-journal
   ```

2. **安裝依賴**
   ```bash
   uv sync
   ```

3. **設定環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 檔案填入您的 API 金鑰 (如適用)
   ```

4. **啟動應用程式**
   ```bash
   uv run streamlit run pages/6_GEX_Sentinel.py
   ```

## 📄 授權條款

[MIT License](LICENSE)
