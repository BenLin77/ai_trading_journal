# 貢獻指南 (Contributing Guide)

歡迎參與 AI Trading Journal 的開發！請遵循以下準則以確保協作順利。

## 開發流程

1.  **Fork 與 Clone**: Fork 本專案並 Clone 到本地環境。
2.  **環境設定**:
    ```bash
    uv sync
    source .venv/bin/activate
    ```
3.  **建立分支**: 使用具描述性的分支名稱 (例如: `feat/gex-calc-optimization`, `fix/ui-glitch`)。
4.  **程式碼規範**:
    - 遵循 **PEP 8** 風格。
    - 所有函式介面必須包含 **Type Hints**。
    - 確保所有新功能皆附帶 **Unit Tests**。
    - 提交前執行測試: `uv run pytest`。
5.  **Commit 訊息**: 使用 [Conventional Commits](https://www.conventionalcommits.org/) 規範 (例如: `feat: add IV percentile`, `fix: handle missing API data`)。

## 專案結構

- `src/`: 核心商業邏輯與服務。
- `pages/`: Streamlit 頁面入口。
- `tests/`: 單元測試與整合測試。
- `specs/`: 功能規格與規劃文件。

## Pull Request 流程

1.  確保程式碼通過所有測試。
2.  若變更了 API 或功能，請更新相應文件。
3.  提交 PR 時，請提供清晰的變更描述，必要時附上截圖。
