"""
Backend.data_loader wrapper.
Exposes data_loader interface from project root for backward/cross-module compatibility.
"""
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_loader import (  # noqa: E402
    fetch_mandi_prices,
    get_fpo_listings,
    add_fpo_listing,
    MANDI_DATAFRAME_COLUMNS,
    DATA_GOV_API_KEY,
    DATA_GOV_RESOURCE_ID,
    OGD_BASE_URL,
    FPO_STORAGE_PATH,
)

__all__ = [
    "fetch_mandi_prices",
    "get_fpo_listings",
    "add_fpo_listing",
    "MANDI_DATAFRAME_COLUMNS",
    "DATA_GOV_API_KEY",
    "DATA_GOV_RESOURCE_ID",
    "OGD_BASE_URL",
    "FPO_STORAGE_PATH",
]
