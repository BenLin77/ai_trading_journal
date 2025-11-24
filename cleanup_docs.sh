#!/bin/bash
# 清理重複的文件

echo "刪除重複的文件..."

# 刪除重複的 markdown 文件
rm -f docs/CODE_REVIEW_REPORT.md
rm -f docs/QUICK_WINS.md
rm -f docs/IMPROVEMENT_SUMMARY.md
rm -f docs/PHASE1_COMPLETE.md
rm -f docs/final_recommendations.md
rm -f docs/COMPLETION_SUMMARY.md

echo "✅ 清理完成！"
echo ""
echo "保留的文件："
ls -1 docs/*.md
