---
description: 單獨呼叫的 Spec Review Agent Workflow
---

```yaml
workflow:
  name: Spec Review Agent Workflow
  steps:
    - name: Spec-Review-Agent
      run: |
        /spec-review-agent "你是資深系統架構師與規格審查員。請在 *不要要求使用者先輸入長篇描述* 的前提下，自動在 Workspace 中尋找規格檔（例如 docs/spec/*.md、spec/*.md 或 architecture/*.md 等），並針對找到的 spec 內容進行審查：

        1) 找出模糊、不一致或自相矛盾的描述。
        2) 檢查邊界條件與錯誤情境是否完整。
        3) 檢查是否有隱含需求或不合理耦合、過度綁定實作細節。

        【輸出要求】
        - 先列出發現的問題清單（可依 High / Medium / Low 標註重要性）。
        - 再給出修正版的關鍵段落或建議改寫示例，讓我可以直接覆蓋原本的 spec 或作為修改參考。
        - 若有多份 spec，請明確標註每項問題對應的檔名與章節。

        若 Workspace 中找不到明確的 spec 檔案，請說明你搜尋過哪些路徑與模式，並建議我如何組織未來的 spec 檔案結構。" 
```
