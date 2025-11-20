"""
Watchlist data model.

Represents user-tracked stock symbols per data-model.md Section 1.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WatchlistEntry:
    """
    Represents a user-tracked stock symbol in the monitoring list.

    Attributes:
        id: Unique identifier for database row
        symbol: Stock ticker (e.g., "NVDA", "AMD")
        added_at: Timestamp when symbol was added
        category: Optional grouping (e.g., "Tech", "Core")
        notes: User annotations (future enhancement)
        enabled: Active/inactive flag (future: disable without deleting)

    Validation Rules (enforced in service layer):
    - symbol must be uppercase
    - symbol must be valid ticker (validated via yfinance before insert)
    - category limited to predefined list if P4 implemented
    """

    id: int
    symbol: str
    added_at: datetime
    category: Optional[str] = None
    notes: Optional[str] = None
    enabled: bool = True
