"""
Backend.calculator wrapper.
Exposes calculator interface from project root for backward/cross-module compatibility.
"""
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from calculator import (  # noqa: E402
    calculate_truck_options,
    calculate_seller_kpi,
    rank_market_and_fpo_options,
    get_shipment_tracking,
    TRUCK_SPECIFICATIONS,
    FINANCIAL_FORMULA_STRING,
    BUYER_LANDED_COST_FORMULA_STRING,
    FINANCIAL_DISCLAIMER,
)

__all__ = [
    "calculate_truck_options",
    "calculate_seller_kpi",
    "rank_market_and_fpo_options",
    "get_shipment_tracking",
    "TRUCK_SPECIFICATIONS",
    "FINANCIAL_FORMULA_STRING",
    "BUYER_LANDED_COST_FORMULA_STRING",
    "FINANCIAL_DISCLAIMER",
]
