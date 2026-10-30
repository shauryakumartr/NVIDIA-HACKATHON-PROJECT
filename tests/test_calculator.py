"""
Unit tests for calculator.py
============================
"""

import unittest
from calculator import (
    calculate_truck_options,
    calculate_seller_kpi,
    rank_market_and_fpo_options,
    get_shipment_tracking,
    FINANCIAL_FORMULA_STRING,
    FINANCIAL_DISCLAIMER,
)


class TestCalculator(unittest.TestCase):
    def test_calculate_truck_options_exact_math(self):
        distance = 100.0
        qty = 45.0  # 45 quintals

        options = calculate_truck_options(distance, qty)
        self.assertEqual(len(options), 3)

        expected_types = [
            "Mini Truck (Tata Ace - up to 15 Qtl)",
            "Standard LCV (Eicher 14ft - up to 60 Qtl)",
            "Reefer Cold-Chain Truck (up to 100 Qtl)"
        ]

        for idx, opt in enumerate(options):
            self.assertEqual(opt["truck_type"], expected_types[idx])
            self.assertIn("capacity_quintals", opt)
            self.assertIn("trucks_needed", opt)
            self.assertIn("rate_per_km", opt)
            self.assertIn("distance_km", opt)
            self.assertIn("freight_cost", opt)
            self.assertIn("eta_hours", opt)
            self.assertIn("spoilage_risk", opt)

        # 1. Mini truck (cap 15): 45 / 15 = 3 trucks. Rate 18. Cost = 3 * 100 * 18 = 5400. ETA = 100/40 + 2 = 4.5
        mini = options[0]
        self.assertEqual(mini["trucks_needed"], 3)
        self.assertEqual(mini["freight_cost"], 5400.0)
        self.assertEqual(mini["eta_hours"], 4.5)
        self.assertEqual(mini["spoilage_risk"], "Medium")

        # 2. Standard LCV (cap 60): 45 / 60 = 1 truck. Rate 28. Cost = 1 * 100 * 28 = 2800. ETA = 100/45 + 2 = 4.2
        lcv = options[1]
        self.assertEqual(lcv["trucks_needed"], 1)
        self.assertEqual(lcv["freight_cost"], 2800.0)
        self.assertEqual(lcv["eta_hours"], 4.2)
        self.assertEqual(lcv["spoilage_risk"], "Low")

        # 3. Reefer (cap 100): 45 / 100 = 1 truck. Rate 42. Cost = 1 * 100 * 42 = 4200. ETA = 100/50 + 2 = 4.0
        reefer = options[2]
        self.assertEqual(reefer["trucks_needed"], 1)
        self.assertEqual(reefer["freight_cost"], 4200.0)
        self.assertEqual(reefer["eta_hours"], 4.0)
        self.assertEqual(reefer["spoilage_risk"], "Minimal (Temp Controlled)")

    def test_calculate_seller_kpi_weighting_and_badges(self):
        # Fresh high-tier FPO
        fpo_gold = {
            "listing_id": "FPO-101",
            "age_days": 0,
            "quality_rating": 5.0,
            "on_time_rate": 1.0,
        }
        res_gold = calculate_seller_kpi(fpo_gold)
        self.assertEqual(res_gold["overall_kpi_score"], 100.0)
        self.assertEqual(res_gold["freshness_score"], 100.0)
        self.assertEqual(res_gold["reliability_pct"], 100.0)
        self.assertEqual(res_gold["badge"], "Gold Verified FPO")

        # Mid-tier FPO
        fpo_silver = {
            "listing_id": "FPO-103",
            "age_days": 3,
            "quality_rating": 4.5,
            "on_time_rate": 0.92,
        }
        res_silver = calculate_seller_kpi(fpo_silver)
        self.assertEqual(res_silver["badge"], "Silver Trusted FPO")
        self.assertGreaterEqual(res_silver["overall_kpi_score"], 75.0)
        self.assertLess(res_silver["overall_kpi_score"], 88.0)

        # Aging lower-tier FPO
        fpo_standard = {
            "listing_id": "FPO-104",
            "age_days": 7,
            "quality_rating": 4.0,
            "on_time_rate": 0.85,
        }
        res_standard = calculate_seller_kpi(fpo_standard)
        self.assertEqual(res_standard["badge"], "Standard FPO")
        self.assertLess(res_standard["overall_kpi_score"], 75.0)

    def test_rank_market_and_fpo_options_schema_and_formulas(self):
        mandi_records = [
            {"mandi": "Azadpur", "state": "Delhi", "modal_price": 2500.0, "days_old": 0, "is_stale": False, "grade": "FAQ"},
            {"mandi": "Lasalgaon", "state": "Maharashtra", "modal_price": 2300.0, "days_old": 1, "is_stale": False, "grade": "FAQ"},
        ]
        fpo_listings = [
            {
                "listing_id": "FPO-101",
                "fpo_name": "Sahyadri FPO",
                "asking_price_per_quintal": 2600.0,
                "age_days": 0,
                "quality_rating": 4.9,
                "on_time_rate": 0.98,
                "grade": "Grade A"
            }
        ]

        qty = 50.0
        dist = 200.0
        other_cost_rate = 20.0
        res = rank_market_and_fpo_options(
            quantity_quintals=qty,
            mandi_records=mandi_records,
            fpo_listings=fpo_listings,
            delivery_address="Azadpur Mandi, Delhi",
            distance_km=dist,
            selected_truck_type="Standard LCV",
            other_costs_per_quintal=other_cost_rate
        )

        # Top-level schema
        self.assertIn("ranked_options", res)
        self.assertIn("truck_options", res)
        self.assertIn("selected_truck", res)
        self.assertIn("seller_kpis", res)
        self.assertIn("formula_used", res)
        self.assertIn("disclaimer", res)

        self.assertEqual(res["formula_used"], FINANCIAL_FORMULA_STRING)
        self.assertEqual(res["disclaimer"], FINANCIAL_DISCLAIMER)

        # Selected truck check (Standard LCV cap 60: 50 Qtl = 1 truck * 200 km * 28 = 5600)
        sel_truck = res["selected_truck"]
        self.assertEqual(sel_truck["freight_cost"], 5600.0)

        # Other stated costs = 50 * 20 = 1000.0
        expected_other = 1000.0
        transport_cost = 5600.0

        for opt in res["ranked_options"]:
            # Check schema keys
            required_keys = [
                "name", "source_type", "unit_price", "gross_value",
                "transport_cost", "other_stated_costs", "estimated_net_proceeds",
                "estimated_buyer_landed_cost", "eta_hours", "is_stale", "grade", "age_days"
            ]
            for rk in required_keys:
                self.assertIn(rk, opt)

            # Mathematical validation
            expected_gross = round(qty * opt["unit_price"], 2)
            self.assertEqual(opt["gross_value"], expected_gross)
            self.assertEqual(opt["transport_cost"], transport_cost)
            self.assertEqual(opt["other_stated_costs"], expected_other)

            expected_net = round(expected_gross - transport_cost - expected_other, 2)
            self.assertEqual(opt["estimated_net_proceeds"], expected_net)

            expected_buyer = round(expected_gross + transport_cost + expected_other, 2)
            self.assertEqual(opt["estimated_buyer_landed_cost"], expected_buyer)

        # Verify sorted by estimated_net_proceeds descending
        net_proceeds_list = [opt["estimated_net_proceeds"] for opt in res["ranked_options"]]
        self.assertEqual(net_proceeds_list, sorted(net_proceeds_list, reverse=True))

    def test_get_shipment_tracking_structure(self):
        tracking = get_shipment_tracking(
            order_id="ORD-991",
            origin="Nashik, Maharashtra",
            destination="Vashi, Mumbai",
            eta_hours=5.5
        )

        expected_stages = [
            "Order Confirmed & Escrow Locked",
            "Produce Graded & Loaded at FPO",
            "In Transit (GPS Active)",
            "Out for Delivery"
        ]
        self.assertEqual(tracking["stages"], expected_stages)
        self.assertEqual(tracking["current_stage_index"], 2)
        self.assertEqual(tracking["current_stage_name"], "In Transit (GPS Active)")
        self.assertIn("estimated_arrival", tracking)
        self.assertEqual(len(tracking["checkpoints"]), 4)


if __name__ == "__main__":
    unittest.main()
