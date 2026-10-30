"""
Unit tests for agent.py
=======================
"""

import unittest
from agent import (
    TOOLS,
    execute_tool,
    generate_why_buy_insight,
    generate_top_5_merits_demerits,
    parse_natural_language_intent,
    chat_with_nemotron,
)
from calculator import rank_market_and_fpo_options, FINANCIAL_FORMULA_STRING, FINANCIAL_DISCLAIMER


class TestAgent(unittest.TestCase):
    def test_tools_schema_structure(self):
        self.assertEqual(len(TOOLS), 3)
        tool_names = [t["function"]["name"] for t in TOOLS]
        self.assertIn("fetch_mandi_prices", tool_names)
        self.assertIn("get_fpo_listings", tool_names)
        self.assertIn("rank_market_and_fpo_options", tool_names)

        for t in TOOLS:
            self.assertEqual(t["type"], "function")
            self.assertIn("description", t["function"])
            self.assertIn("parameters", t["function"])

    def test_execute_tool_dispatch(self):
        # 1. Test fetch_mandi_prices
        res_mandi = execute_tool("fetch_mandi_prices", {"commodity": "Tomato"})
        self.assertIn("records", res_mandi)
        self.assertIn("has_stale_data", res_mandi)

        # 2. Test get_fpo_listings
        res_fpo = execute_tool("get_fpo_listings", {"commodity": "Tomato"})
        self.assertIn("fpo_listings", res_fpo)

        # 3. Test rank_market_and_fpo_options
        res_rank = execute_tool(
            "rank_market_and_fpo_options",
            {
                "commodity": "Tomato",
                "quantity_quintals": 40.0,
                "delivery_address": "Azadpur, Delhi",
                "distance_km": 150.0,
                "selected_truck_type": "Standard LCV (Eicher 14ft - up to 60 Qtl)"
            }
        )
        self.assertIn("top_ranked_options", res_rank)
        self.assertIn("selected_truck", res_rank)
        self.assertIn("formula_used", res_rank)

    def test_generate_top_5_merits_demerits_schema(self):
        truck = {
            "truck_type": "Standard LCV (Eicher 14ft - up to 60 Qtl)",
            "freight_cost": 5600.0,
            "eta_hours": 6.5
        }
        ranked = [
            {"name": "Sahyadri FPO", "source_type": "FPO Direct", "unit_price": 2350.0, "estimated_buyer_landed_cost": 124350.0, "estimated_net_proceeds": 110650.0, "is_stale": False, "grade": "Grade A"},
            {"name": "Azadpur Mandi", "source_type": "Govt Mandi", "unit_price": 2550.0, "estimated_buyer_landed_cost": 134350.0, "estimated_net_proceeds": 120650.0, "is_stale": False, "grade": "FAQ"},
        ]
        top_5 = generate_top_5_merits_demerits(
            commodity="Tomato",
            quantity_quintals=50.0,
            delivery_address="Delhi Azadpur",
            distance_km=200.0,
            selected_truck=truck,
            ranked_options=ranked
        )

        self.assertIsInstance(top_5, list)
        self.assertEqual(len(top_5), 5)

        for item in top_5:
            self.assertIn("rank", item)
            self.assertIn("name", item)
            self.assertIn("source_type", item)
            self.assertIn("unit_price", item)
            self.assertIn("estimated_landed_cost", item)
            self.assertIn("merits", item)
            self.assertIn("demerits", item)
            self.assertGreaterEqual(len(item["merits"]), 1)
            self.assertGreaterEqual(len(item["demerits"]), 1)

    def test_parse_natural_language_intent(self):
        intent = parse_natural_language_intent("I need 60 quintals of potatoes delivered to Jaipur with reefer")
        self.assertEqual(intent["commodity"], "Potato")
        self.assertEqual(intent["quantity_quintals"], 60.0)
        self.assertIn("Jaipur", intent["delivery_address"])
        self.assertIn("Reefer", intent["truck_preference"])

    def test_generate_why_buy_insight_guardrails(self):
        mandi_records = [
            {"mandi": "Azadpur", "state": "Delhi", "modal_price": 2600.0, "days_old": 0, "is_stale": False, "grade": "FAQ"},
            {"mandi": "Jaipur", "state": "Rajasthan", "modal_price": 2400.0, "days_old": 5, "is_stale": True, "grade": "Medium"},
        ]
        calc_result = rank_market_and_fpo_options(
            quantity_quintals=50.0,
            mandi_records=mandi_records,
            fpo_listings=[],
            delivery_address="Delhi Hub",
            distance_km=120.0,
            selected_truck_type="Standard LCV",
            other_costs_per_quintal=25.0
        )
        stale_warning = "⚠️ Jaipur Mandi price is 5 days old (Stale)."
        insight = generate_why_buy_insight(calc_result, stale_warning)

        # 1. Must contain 3 sections
        self.assertIn("### 1. 🏆 Top Recommendation & Why", insight)
        self.assertIn("### 2. ⚖️ Key Trade-Offs & Assumptions", insight)
        self.assertIn("### 3. 🎯 Recommended Next Step", insight)

        # 2. Guardrails: No 'guaranteed income', uses 'estimated net proceeds' or 'estimated landed cost'
        self.assertNotIn("guaranteed income", insight.lower())
        self.assertIn("estimated net proceeds", insight.lower())
        self.assertIn("estimated buyer landed cost", insight.lower())

        # 3. Stale warning inclusion
        self.assertIn("Jaipur Mandi price is 5 days old", insight)

    def test_chat_with_nemotron_missing_parameters_prompt(self):
        context = {"commodity": "Tomato"}
        reply = chat_with_nemotron(
            user_message="What is the best deal for tomatoes?",
            chat_history=[],
            current_context=context
        )
        self.assertIn("quantity", reply.lower())
        self.assertIn("destination", reply.lower())

    def test_chat_with_nemotron_context_grounded_reply(self):
        context = {
            "commodity": "Onion",
            "quantity_quintals": 100.0,
            "delivery_address": "Mumbai Hub",
            "ranked_options": [
                {
                    "name": "Lasalgaon FPO",
                    "unit_price": 2450.0,
                    "estimated_net_proceeds": 235000.0,
                    "estimated_buyer_landed_cost": 255000.0
                }
            ]
        }
        reply = chat_with_nemotron(
            user_message="Summarize the top option for my shipment",
            chat_history=[],
            current_context=context
        )
        self.assertIn("Lasalgaon FPO", reply)
        self.assertIn("235,000.00", reply)
        self.assertIn("estimated net proceeds", reply.lower())
        self.assertNotIn("guaranteed income", reply.lower())


if __name__ == "__main__":
    unittest.main()
