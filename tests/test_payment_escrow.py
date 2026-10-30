"""
Unit tests for payment_escrow.py
================================
"""

import unittest
from payment_escrow import create_escrow_payment, generate_invoice_pdf, ESCROW_RELEASE_CONDITION


class TestPaymentEscrow(unittest.TestCase):
    def setUp(self):
        self.mock_order = {
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

    def test_create_escrow_payment_schema(self):
        res = create_escrow_payment(self.mock_order)

        # Check required schema keys
        required_keys = [
            "order_id",
            "payment_id",
            "escrow_status",
            "amount_inr",
            "currency",
            "timestamp",
            "razorpay_mode",
            "release_condition"
        ]
        for key in required_keys:
            self.assertIn(key, res)

        self.assertTrue(res["order_id"].startswith("order_"))
        self.assertTrue(res["payment_id"].startswith("pay_"))
        self.assertEqual(res["escrow_status"], "FUNDS_HELD_IN_ESCROW")
        self.assertEqual(res["currency"], "INR")
        self.assertEqual(res["amount_inr"], 124350.0)
        self.assertIn(res["razorpay_mode"], ["LIVE_TEST_API", "SANDBOX_SIMULATION"])
        self.assertEqual(res["release_condition"], ESCROW_RELEASE_CONDITION)

    def test_create_escrow_payment_auto_compute_total(self):
        order_without_total = {
            "buyer_name": "Kisan Retailer",
            "delivery_address": "Jaipur Mandi",
            "seller_name": "Lasalgaon FPO",
            "commodity": "Onion",
            "quantity_quintals": 30.0,
            "unit_price": 2500.0,  # 75,000
            "transport_cost": 3000.0,
            "other_costs": 750.0,
        }
        res = create_escrow_payment(order_without_total)
        # Expected = 75000 + 3000 + 750 = 78750.0
        self.assertEqual(res["amount_inr"], 78750.0)

    def test_generate_invoice_pdf_validity(self):
        payment_res = create_escrow_payment(self.mock_order)
        pdf_bytes = generate_invoice_pdf(self.mock_order, payment_res)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1500)
        # Valid PDF files start with %PDF
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generate_invoice_pdf_edge_cases(self):
        # Sparse order dictionary
        sparse_order = {
            "buyer_name": "Local Buyer",
            "seller_name": "Local FPO",
            "quantity_quintals": 10.0,
            "unit_price": 1000.0
        }
        payment_res = create_escrow_payment(sparse_order)
        pdf_bytes = generate_invoice_pdf(sparse_order, payment_res)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
