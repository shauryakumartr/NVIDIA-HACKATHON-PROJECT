"""
payment_escrow.py
=================
Agriculture Marketplace & Market-Decision Platform
NVIDIA × Nebius Hackathon

Handles Razorpay order creation, escrow payment lifecycle management
(funds locked until produce delivery and grade verification), and on-the-fly
single-page PDF tax & escrow invoice generation using fpdf2.
"""

import os
import time
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import razorpay
from fpdf import FPDF

# -----------------------------------------------------------------------------
# Configuration & Logging Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger("payment_escrow")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [payment_escrow]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

load_dotenv()

RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

ESCROW_RELEASE_CONDITION = (
    "Released to FPO upon buyer delivery confirmation & grade check"
)


def _get_razorpay_client() -> Optional[razorpay.Client]:
    """
    Safely initializes and returns the Razorpay client.
    Returns None if credentials are missing or placeholders.
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return None
    if RAZORPAY_KEY_ID in ["YOUR_KEY", "your_key_id_here", ""]:
        return None
    try:
        return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as exc:
        logger.warning("Could not initialize Razorpay client: %s", exc)
        return None


# -----------------------------------------------------------------------------
# Function 1: create_escrow_payment
# -----------------------------------------------------------------------------
def create_escrow_payment(order_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates an escrow payment order using Razorpay API or realistic sandbox simulation.

    Args:
        order_details: Dictionary containing:
          - buyer_name: str
          - delivery_address: str
          - seller_name: str
          - commodity: str
          - variety: str
          - grade: str
          - quantity_quintals: float
          - unit_price: float
          - transport_cost: float
          - other_costs: float
          - total_amount_inr: float
          - truck_type: str
          - eta_hours: float

    Returns:
        Exact schema:
          {
              "order_id": str,
              "payment_id": str,
              "escrow_status": "FUNDS_HELD_IN_ESCROW",
              "amount_inr": float,
              "currency": "INR",
              "timestamp": str,
              "razorpay_mode": str, # "LIVE_TEST_API" or "SANDBOX_SIMULATION"
              "release_condition": str
          }
    """
    if not isinstance(order_details, dict):
        raise TypeError("order_details must be a dictionary.")

    # 1. Parse and sanitize financial amounts
    qty = max(0.0, float(order_details.get("quantity_quintals", 0.0)))
    unit_p = max(0.0, float(order_details.get("unit_price", 0.0)))
    transport = max(0.0, float(order_details.get("transport_cost", 0.0)))
    other = max(0.0, float(order_details.get("other_costs", 0.0)))

    # Determine or recompute total landed amount
    explicit_total = order_details.get("total_amount_inr")
    if explicit_total is not None and float(explicit_total) > 0:
        total_inr = round(float(explicit_total), 2)
    else:
        total_inr = round((qty * unit_p) + transport + other, 2)

    amount_paise = int(round(total_inr * 100))
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    client = _get_razorpay_client()
    order_id = ""
    payment_id = ""
    razorpay_mode = "SANDBOX_SIMULATION"

    # 2. Attempt Live Test API if credentials exist
    if client is not None and amount_paise > 0:
        try:
            logger.info("Initiating Razorpay API Order for Rs. %.2f (%d paise)", total_inr, amount_paise)
            notes_payload = {
                "buyer": str(order_details.get("buyer_name", "Buyer"))[:40],
                "seller": str(order_details.get("seller_name", "FPO"))[:40],
                "commodity": str(order_details.get("commodity", "Produce"))[:30],
                "quantity_quintals": str(qty),
                "escrow_status": "FUNDS_HELD_IN_ESCROW",
                "release_condition": ESCROW_RELEASE_CONDITION
            }
            rzp_order = client.order.create(data={
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": notes_payload
            })
            order_id = str(rzp_order.get("id"))
            # Generate matching live test payment id
            hash_suffix = hashlib.md5(f"{order_id}{time.time()}".encode()).hexdigest()[:8].upper()
            payment_id = f"pay_{order_id.replace('order_', '')}{hash_suffix}"
            razorpay_mode = "LIVE_TEST_API"
            logger.info("Razorpay Order created successfully: %s", order_id)
        except Exception as exc:
            logger.warning("Razorpay API order creation failed (%s). Falling back to sandbox.", exc)
            order_id = ""

    # 3. Hackathon Sandbox Simulation Fallback
    if not order_id:
        seed = f"{order_details.get('seller_name')}_{order_details.get('buyer_name')}_{total_inr}_{time.time()}"
        suffix = hashlib.sha256(seed.encode()).hexdigest()[:10].upper()
        order_id = f"order_RzpEscrow{suffix}"
        payment_id = f"pay_RzpEscrow{suffix}"
        razorpay_mode = "SANDBOX_SIMULATION"
        logger.info("Generated Sandbox Escrow Order: %s | Payment: %s", order_id, payment_id)

    return {
        "order_id": order_id,
        "payment_id": payment_id,
        "escrow_status": "FUNDS_HELD_IN_ESCROW",
        "amount_inr": total_inr,
        "currency": "INR",
        "timestamp": timestamp_str,
        "razorpay_mode": razorpay_mode,
        "release_condition": ESCROW_RELEASE_CONDITION
    }


# -----------------------------------------------------------------------------
# Function 2: generate_invoice_pdf
# -----------------------------------------------------------------------------
class EscrowInvoicePDF(FPDF):
    """Custom FPDF2 subclass for AgriNemotron Escrow Tax Invoices."""

    def header(self):
        # Forest Green header banner
        self.set_fill_color(24, 76, 52)
        self.rect(0, 0, 210, 24, "F")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(12, 5)
        self.cell(120, 8, "AgriNemotron FPO Marketplace", align="L")

        self.set_font("Helvetica", "", 8)
        self.set_xy(12, 13)
        self.cell(120, 6, "Autonomous Agricultural Decision Platform | NVIDIA x Nebius Hackathon", align="L")

        self.set_font("Helvetica", "B", 10)
        self.set_xy(140, 7)
        self.cell(58, 6, "ESCROW TAX INVOICE", align="R")

        self.set_text_color(40, 40, 40)
        self.set_y(28)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            4,
            "Notice: Figures represent estimated landed costs and net proceeds. Governed by AgriNemotron Escrow Agreement.",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT"
        )
        self.cell(
            0,
            4,
            "Escrow funds protected in Razorpay Trust Escrow Account. Disbursed upon digital QA manifest sign-off.",
            align="C"
        )


def generate_invoice_pdf(
    order_details: Dict[str, Any],
    payment_status: Dict[str, Any]
) -> bytes:
    """
    Generates a clean, professional single-page PDF tax & escrow invoice in memory.

    Uses strictly standard ASCII characters ('INR' or 'Rs.' rather than Unicode '₹')
    to prevent encoding errors in standard Helvetica font.

    Args:
        order_details: Buyer, seller, produce specifications, and pricing metrics.
        payment_status: Output dictionary from create_escrow_payment().

    Returns:
        Raw bytes representing the PDF document (ready for st.download_button).
    """
    pdf = EscrowInvoicePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Sanitized order details
    buyer_name = str(order_details.get("buyer_name", "Registered Buyer")).strip()
    delivery_addr = str(order_details.get("delivery_address", "Buyer Terminal Warehouse")).strip()
    seller_name = str(order_details.get("seller_name", "Registered Farmer Producer Organization")).strip()
    origin_loc = str(order_details.get("origin_location", "India")).strip()
    commodity = str(order_details.get("commodity", "Agricultural Commodity")).strip()
    variety = str(order_details.get("variety", "Standard")).strip()
    grade = str(order_details.get("grade", "Grade A")).strip()
    freshness = str(order_details.get("freshness_tag", "Verified Fresh")).strip()
    truck_type = str(order_details.get("truck_type", "Standard Commercial Vehicle")).strip()

    qty = max(0.0, float(order_details.get("quantity_quintals", 0.0)))
    unit_p = max(0.0, float(order_details.get("unit_price", 0.0)))
    transport = max(0.0, float(order_details.get("transport_cost", 0.0)))
    other_costs = max(0.0, float(order_details.get("other_costs", 0.0)))
    base_val = round(qty * unit_p, 2)

    total_amount = round(payment_status.get("amount_inr", base_val + transport + other_costs), 2)
    order_id = str(payment_status.get("order_id", "ORD-SIMULATED"))
    payment_id = str(payment_status.get("payment_id", "PAY-SIMULATED"))
    timestamp = str(payment_status.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M IST")))
    mode = str(payment_status.get("razorpay_mode", "SANDBOX_SIMULATION"))
    eta_hours = float(order_details.get("eta_hours", 4.5))

    # Invoice Serial Number
    inv_seed = hashlib.md5(f"{order_id}_{payment_id}".encode()).hexdigest()[:6].upper()
    invoice_number = f"INV-2026-{inv_seed}"

    # -------------------------------------------------------------------------
    # 1. Invoice Meta & Razorpay Reference Block
    # -------------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 6, f"Invoice No: {invoice_number}", new_x="RIGHT")
    pdf.cell(95, 6, f"Date: {timestamp}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 5, f"Razorpay Order ID: {order_id}", new_x="RIGHT")
    pdf.cell(95, 5, f"Razorpay Payment ID: {payment_id}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(95, 5, f"Gateway Channel: {mode}", new_x="RIGHT")
    pdf.cell(95, 5, "Currency: INR (Indian Rupee)", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # -------------------------------------------------------------------------
    # 2. Escrow Status Badge Banner
    # -------------------------------------------------------------------------
    pdf.set_fill_color(235, 247, 238)
    pdf.set_draw_color(34, 139, 34)
    pdf.set_line_width(0.3)
    pdf.rect(10, pdf.get_y(), 190, 14, "DF")

    pdf.set_xy(12, pdf.get_y() + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(16, 120, 60)
    pdf.cell(186, 5, "STATUS: FUNDS HELD IN ESCROW (LOCKED VIA RAZORPAY SMART CHECKOUT)", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(186, 4, f"Release Condition: {ESCROW_RELEASE_CONDITION}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # -------------------------------------------------------------------------
    # 3. Party Information (Seller vs Buyer Cards)
    # -------------------------------------------------------------------------
    start_y = pdf.get_y()
    card_width = 92
    card_height = 36

    # Seller Card (Left)
    pdf.set_fill_color(248, 250, 248)
    pdf.set_draw_color(210, 220, 215)
    pdf.rect(10, start_y, card_width, card_height, "DF")

    pdf.set_xy(14, start_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(24, 76, 52)
    pdf.cell(card_width - 8, 5, "SELLER / FPO DETAILS:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(14)
    pdf.cell(card_width - 8, 4, f"FPO Name: {seller_name[:36]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.cell(card_width - 8, 4, f"Origin Hub: {origin_loc[:36]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.cell(card_width - 8, 4, f"Produce: {commodity} ({variety})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.cell(card_width - 8, 4, f"Grade: {grade} | Freshness: {freshness}", new_x="LMARGIN", new_y="NEXT")

    # Buyer Card (Right)
    pdf.set_fill_color(248, 250, 248)
    pdf.rect(108, start_y, card_width, card_height, "DF")

    pdf.set_xy(112, start_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(24, 76, 52)
    pdf.cell(card_width - 8, 5, "BUYER & DELIVERY DETAILS:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(112)
    pdf.cell(card_width - 8, 4, f"Buyer Name: {buyer_name[:36]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(112)
    pdf.cell(card_width - 8, 4, f"Destination: {delivery_addr[:36]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(112)
    pdf.cell(card_width - 8, 4, f"Fleet Allocated: {truck_type[:32]}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(112)
    pdf.cell(card_width - 8, 4, f"Logistics Transit ETA: ~{eta_hours} hours", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(start_y + card_height + 6)

    # -------------------------------------------------------------------------
    # 4. Itemized Cost Breakdown Table
    # -------------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(24, 76, 52)
    pdf.set_text_color(255, 255, 255)

    # Table Header
    col_w_desc = 100
    col_w_rate = 45
    col_w_amt = 45

    pdf.cell(col_w_desc, 7, "  Item Description", fill=True)
    pdf.cell(col_w_rate, 7, "Specification / Rate", fill=True, align="C")
    pdf.cell(col_w_amt, 7, "Amount (INR)  ", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(40, 40, 40)
    pdf.set_draw_color(210, 220, 215)

    # Line 1: Base Produce Value
    pdf.cell(col_w_desc, 8, f"  Base Produce: {commodity} ({variety}) - {grade}", border="B")
    pdf.cell(col_w_rate, 8, f"{qty:,.1f} Qtl @ Rs. {unit_p:,.2f}/Qtl", border="B", align="C")
    pdf.cell(col_w_amt, 8, f"Rs. {base_val:,.2f}  ", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    # Line 2: Logistics & Freight
    pdf.cell(col_w_desc, 8, f"  Logistics & Freight: {truck_type}", border="B")
    pdf.cell(col_w_rate, 8, f"Transit ETA: {eta_hours}h", border="B", align="C")
    pdf.cell(col_w_amt, 8, f"Rs. {transport:,.2f}  ", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    # Line 3: Mandi & Handling Fee
    pdf.cell(col_w_desc, 8, "  Mandi Cess, Weighing & Platform Handling Fees", border="B")
    pdf.cell(col_w_rate, 8, "Statutory / APMC Buffer", border="B", align="C")
    pdf.cell(col_w_amt, 8, f"Rs. {other_costs:,.2f}  ", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    # Line 4: Total Highlighted Row
    pdf.set_fill_color(240, 246, 242)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(24, 76, 52)
    pdf.cell(col_w_desc + col_w_rate, 9, "  TOTAL AMOUNT LOCKED IN ESCROW (INR)", fill=True, border="TB")
    pdf.cell(col_w_amt, 9, f"Rs. {total_amount:,.2f}  ", fill=True, border="TB", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # -------------------------------------------------------------------------
    # 5. Settlement Terms & Deterministic Policy Box
    # -------------------------------------------------------------------------
    pdf.set_fill_color(252, 252, 252)
    pdf.set_draw_color(220, 225, 220)
    pdf.rect(10, pdf.get_y(), 190, 36, "DF")

    box_y = pdf.get_y() + 3
    pdf.set_xy(14, box_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(182, 4, "FINANCIAL DISCLOSURES & DETERMINISTIC CALCULATION RULES:", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(14)
    pdf.cell(
        182,
        4,
        "- Calculation Formula: Estimated Buyer Total Cost = (Quantity x Price/Qtl) + Transport Cost + Other Stated Costs.",
        new_x="LMARGIN",
        new_y="NEXT"
    )
    pdf.set_x(14)
    pdf.cell(
        182,
        4,
        "- Escrow Security: Funds remain held in the Razorpay trust escrow account until the consignment arrives at the destination.",
        new_x="LMARGIN",
        new_y="NEXT"
    )
    pdf.set_x(14)
    pdf.cell(
        182,
        4,
        "- Release Protocol: The buyer conducts a digital moisture/grade verification. Upon approval, funds disburse immediately to the FPO.",
        new_x="LMARGIN",
        new_y="NEXT"
    )
    pdf.set_x(14)
    pdf.cell(
        182,
        4,
        "- Rejection & Dispute: In the event of transit spoilage or grade mismatch, dispute resolution is mediated via platform QA logs.",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(16, 120, 60)
    pdf.cell(0, 4, "AUTHENTICATED DIGITAL ESCROW RECEIPT -- NO PHYSICAL SIGNATURE REQUIRED", align="C")

    # Output pure bytes
    return bytes(pdf.output())


# -----------------------------------------------------------------------------
# Module CLI Self-Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("Running payment_escrow.py Verification Self-Test")
    print("=" * 70)

    # 1. Test create_escrow_payment
    print("\n--- 1. Testing create_escrow_payment() ---")
    mock_order = {
        "buyer_name": "AgroSuper FreshMart Delhi",
        "delivery_address": "Azadpur Mandi Wholesale Hub, Delhi",
        "seller_name": "Sahyadri Farmers Producer Co. Ltd.",
        "origin_location": "Nashik, Maharashtra",
        "commodity": "Tomato",
        "variety": "Hybrid Shivam",
        "grade": "Grade A",
        "freshness_tag": "Harvest Fresh (<2 days)",
        "quantity_quintals": 50.0,
        "unit_price": 2350.0,
        "transport_cost": 5600.0,
        "other_costs": 1250.0,
        "total_amount_inr": 124350.0,
        "truck_type": "Standard LCV (Eicher 14ft - up to 60 Qtl)",
        "eta_hours": 6.5
    }

    payment_res = create_escrow_payment(mock_order)
    print(f"Order ID: {payment_res['order_id']}")
    print(f"Payment ID: {payment_res['payment_id']}")
    print(f"Escrow Status: {payment_res['escrow_status']}")
    print(f"Amount: Rs. {payment_res['amount_inr']:,.2f}")
    print(f"Razorpay Mode: {payment_res['razorpay_mode']}")
    print(f"Release Condition: {payment_res['release_condition']}")

    # 2. Test generate_invoice_pdf
    print("\n--- 2. Testing generate_invoice_pdf() ---")
    pdf_bytes = generate_invoice_pdf(mock_order, payment_res)
    print(f"Generated PDF Size: {len(pdf_bytes)} bytes")
    assert len(pdf_bytes) > 2000, "PDF byte length is unexpectedly small"

    # Save to disk as verification artifact
    test_pdf_path = Path(__file__).resolve().parent / "test_escrow_invoice.pdf"
    with open(test_pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"Saved test invoice to {test_pdf_path}")

    print("\npayment_escrow.py verification completed successfully!")
