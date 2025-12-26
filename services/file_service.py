"""
檔案服務模組

提供報告存檔功能，將每日報告保存為 Markdown 檔案。
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class FileService:
    """
    檔案服務類別
    
    負責管理報告存檔相關的檔案操作。
    """
    
    def __init__(self, reports_dir: Optional[str] = None):
        """
        初始化檔案服務
        
        Args:
            reports_dir: 報告存放目錄，預設為專案根目錄下的 reports/
        """
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            # 預設為專案根目錄下的 reports/
            self.reports_dir = Path(__file__).parent.parent / 'reports'
            
    def ensure_reports_dir(self) -> Path:
        """
        確保報告目錄存在
        
        Returns:
            Path: 報告目錄路徑
        """
        if not self.reports_dir.exists():
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"已建立報告目錄: {self.reports_dir}")
        return self.reports_dir
        
    def save_report_to_markdown(
        self, 
        content: str, 
        date_str: Optional[str] = None,
        prefix: str = "daily_report"
    ) -> Path:
        """
        將報告內容存成 Markdown 檔案
        
        Args:
            content: 報告內容 (Markdown 格式)
            date_str: 日期字串，格式為 YYYY-MM-DD，預設為今天
            prefix: 檔名前綴，預設為 "daily_report"
            
        Returns:
            Path: 儲存的檔案路徑
            
        Raises:
            PermissionError: 權限不足時拋出
            IOError: 寫入失敗時拋出
        """
        # 確保目錄存在
        self.ensure_reports_dir()
        
        # 預設使用今天日期
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        # 構建檔名
        filename = f"{date_str}_{prefix}.md"
        filepath = self.reports_dir / filename
        
        try:
            # 寫入檔案
            with open(filepath, 'w', encoding='utf-8') as f:
                # 加入報告標頭
                header = f"# 每日交易報告 - {date_str}\n\n"
                header += f"*生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                header += "---\n\n"
                
                f.write(header + content)
                
            logger.info(f"報告已存檔: {filepath}")
            return filepath
            
        except PermissionError as e:
            logger.error(f"存檔權限不足: {filepath}")
            raise
        except Exception as e:
            logger.error(f"存檔失敗: {e}")
            raise IOError(f"無法寫入檔案: {str(e)}")
            
    def get_report_path(self, date_str: str, prefix: str = "daily_report") -> Path:
        """
        獲取報告檔案路徑
        
        Args:
            date_str: 日期字串
            prefix: 檔名前綴
            
        Returns:
            Path: 報告檔案路徑
        """
        filename = f"{date_str}_{prefix}.md"
        return self.reports_dir / filename
        
    def report_exists(self, date_str: str, prefix: str = "daily_report") -> bool:
        """
        檢查報告是否已存在
        
        Args:
            date_str: 日期字串
            prefix: 檔名前綴
            
        Returns:
            bool: 檔案是否存在
        """
        return self.get_report_path(date_str, prefix).exists()
        
    def list_reports(self, limit: int = 30, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list:
        """
        列出報告檔案
        
        Args:
            limit: 最多返回的報告數量
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            
        Returns:
            list: 報告檔案資訊列表
        """
        self.ensure_reports_dir()
        
        reports = []
        for file in sorted(self.reports_dir.glob("*_daily_report.md"), reverse=True):
            try:
                file_date = file.name.split('_')[0]
                
                # 日期範圍篩選
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue
                    
                reports.append({
                    'filename': file.name,
                    'path': str(file),
                    'date': file_date,
                    'size': file.stat().st_size,
                    'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
                
                if len(reports) >= limit:
                    break
            except Exception:
                continue
            
        return reports
    
    def get_report_content(self, filename: str) -> Optional[str]:
        """
        獲取報告內容
        
        Args:
            filename: 報告檔名
            
        Returns:
            str: 報告內容，找不到檔案時返回 None
        """
        filepath = self.reports_dir / filename
        if not filepath.exists():
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"讀取報告失敗: {e}")
            return None
    
    def get_recent_reports_content(self, days: int = 7) -> str:
        """
        獲取最近幾天的報告內容（用於 AI 上下文）
        
        Args:
            days: 最近幾天
            
        Returns:
            str: 合併的報告內容
        """
        from datetime import timedelta
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        reports = self.list_reports(limit=days, start_date=start_date, end_date=end_date)
        
        if not reports:
            return ""
        
        content_parts = []
        for report in reports:
            content = self.get_report_content(report['filename'])
            if content:
                content_parts.append(f"\n\n=== {report['date']} 報告 ===\n{content}")
        
        return "\n".join(content_parts)
    
    def create_reports_zip(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[Path]:
        """
        創建報告 ZIP 壓縮檔
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            Path: ZIP 檔案路徑
        """
        import zipfile
        import tempfile
        
        reports = self.list_reports(limit=1000, start_date=start_date, end_date=end_date)
        
        if not reports:
            return None
        
        # 創建臨時 ZIP 檔案
        date_range = f"{start_date or 'all'}_to_{end_date or 'now'}"
        zip_filename = f"reports_{date_range}.zip"
        zip_path = Path(tempfile.gettempdir()) / zip_filename
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for report in reports:
                    filepath = Path(report['path'])
                    if filepath.exists():
                        zipf.write(filepath, filepath.name)
            
            logger.info(f"已創建報告 ZIP: {zip_path} ({len(reports)} 個檔案)")
            return zip_path
        except Exception as e:
            logger.error(f"創建 ZIP 失敗: {e}")
            return None


def save_report_to_markdown(content: str, date_str: Optional[str] = None) -> Path:
    """
    便捷函數：將報告存成 Markdown 檔案
    
    這是一個模組層級的便捷函數，直接使用預設設定。
    
    Args:
        content: 報告內容
        date_str: 日期字串 (YYYY-MM-DD)
        
    Returns:
        Path: 儲存的檔案路徑
    """
    service = FileService()
    return service.save_report_to_markdown(content, date_str)
