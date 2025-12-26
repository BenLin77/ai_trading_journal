---
description: 單獨呼叫的 Spec Compliance Agent Workflow
---

```yaml
workflow:
  name: Spec Compliance Agent Workflow
  steps:
    - name: Spec-Compliance-Agent
      run: |
        /spec-compliance-agent "你是規格符合度審查員。請在 *不要要求使用者先輸入長篇描述* 的前提下，自動在 Workspace 中尋找 spec 檔案（例如 docs/spec/*.md 或 spec/*.md 等），並比對實際程式碼實作與 spec 的差異，找出：

        1) 程式碼有實作但 spec 未記載的行為（over-implementation）。
        2) spec 有定義但程式碼未實作或行為不一致之處（under-implementation 或 mismatch）。
        3) 實作與 spec 在錯誤處理、輸入輸出、邊界條件上的差異。

        【自動比對行為】
        - 根據 spec 中提到的模組/函式/介面名稱，於程式碼中搜尋對應實作。
        - 比對參數、回傳值、錯誤處理與邊界條件的敘述與實際實作差異。

        【輸出格式】
        請用條列式列出每個差異，包含：
        - 位置 / 描述（spec 位置 + 程式碼檔名/符號）。
        - 差異內容與可能影響。
        - 建議動作：『修改 spec』、『修改程式碼』或『兩者都調整』。

        若 Workspace 中找不到明確的 spec 檔案，請說明你搜尋過哪些路徑與檔名模式，並建議我如何補齊 spec。" 
```
