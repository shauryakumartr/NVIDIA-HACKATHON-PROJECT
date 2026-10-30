"""
Backend.payment_escrow wrapper.
Exposes payment_escrow interface from project root for backward/cross-module compatibility.
"""
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from payment_escrow import (  # noqa: E402
    create_escrow_payment,
    generate_invoice_pdf,
    ESCROW_RELEASE_CONDITION,
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
)

__all__ = [
    "create_escrow_payment",
    "generate_invoice_pdf",
    "ESCROW_RELEASE_CONDITION",
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
]
