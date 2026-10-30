"""
Unit tests for data_loader.py
==============================
"""

import unittest
from datetime import date, timedelta
from data_loader import (
    fetch_mandi_prices,
    get_fpo_listings,
    add_fpo_listing,
    MANDI_DATAFRAME_COLUMNS,
)


class TestDataLoader(unittest.TestCase):
    def test_fetch_mandi_prices_schema_and_fallback(self):
        result = fetch_mandi_prices("Tomato")

        # Verify Top-Level Schema
        self.assertIn("dataframe", result)
        self.assertIn("records", result)
        self.assertIn("has_stale_data", result)
        self.assertIn("missing_markets", result)
        self.assertIn("stale_warning_msg", result)

        df = result["dataframe"]
        self.assertEqual(list(df.columns), MANDI_DATAFRAME_COLUMNS)
        self.assertGreaterEqual(len(df), 4)

        # Check for the 4 core mandis
        mandis = set(df["mandi"].tolist())
        for expected in ["Azadpur", "Lasalgaon", "Kolar", "Jaipur"]:
            self.assertIn(expected, mandis)

        # Verify Hackathon Fallback Staleness demonstration requirement
        # Jaipur must be 5 days old with is_stale == True
        jaipur_row = df[df["mandi"] == "Jaipur"].iloc[0]
        self.assertEqual(jaipur_row["days_old"], 5)
        self.assertTrue(jaipur_row["is_stale"])
        self.assertTrue(result["has_stale_data"])
        self.assertTrue(len(result["stale_warning_msg"]) > 0)
        self.assertIn("Jaipur", result["stale_warning_msg"])

    def test_fetch_mandi_prices_market_filtering_and_missing(self):
        target_markets = ["Azadpur", "Lasalgaon", "NonExistentMandi"]
        result = fetch_mandi_prices("Onion", market_list=target_markets)

        df = result["dataframe"]
        mandi_names = df["mandi"].tolist()

        self.assertIn("Azadpur", mandi_names)
        self.assertIn("Lasalgaon", mandi_names)
        self.assertNotIn("NonExistentMandi", mandi_names)

        # Check missing_markets
        self.assertIn("NonExistentMandi", result["missing_markets"])
        self.assertIn("NonExistentMandi", result["stale_warning_msg"])

    def test_fetch_mandi_prices_state_filtering(self):
        result = fetch_mandi_prices("Potato", state="Maharashtra")
        df = result["dataframe"]
        for _, row in df.iterrows():
            self.assertEqual(row["state"].lower(), "maharashtra")

    def test_get_fpo_listings_schema_and_freshness(self):
        listings = get_fpo_listings()
        self.assertGreaterEqual(len(listings), 4)

        required_keys = [
            "listing_id",
            "fpo_name",
            "commodity",
            "variety",
            "grade",
            "harvest_date",
            "age_days",
            "freshness_tag",
            "quantity_quintals",
            "asking_price_per_quintal",
            "origin_location",
            "origin_distance_km_map",
            "photo_url",
            "completed_orders",
            "on_time_rate",
            "quality_rating",
        ]

        freshness_tags_seen = set()
        for item in listings:
            for k in required_keys:
                self.assertIn(k, item, f"Missing key '{k}' in listing {item.get('listing_id')}")
            freshness_tags_seen.add(item["freshness_tag"])
            self.assertIsInstance(item["quantity_quintals"], float)
            self.assertIsInstance(item["asking_price_per_quintal"], float)
            self.assertIsInstance(item["origin_distance_km_map"], dict)

        # Verify presence of freshness classifications
        self.assertIn("Harvest Fresh (<2 days)", freshness_tags_seen)
        self.assertIn("Standard (2-5 days)", freshness_tags_seen)
        self.assertIn("Aging (>5 days)", freshness_tags_seen)

    def test_fpo_listings_commodity_filter(self):
        tomato_listings = get_fpo_listings(commodity="Tomato")
        self.assertTrue(len(tomato_listings) >= 1)
        for item in tomato_listings:
            self.assertEqual(item["commodity"].lower(), "tomato")

    def test_add_fpo_listing(self):
        today_str = date.today().strftime("%Y-%m-%d")
        new_entry = {
            "fpo_name": "Satara Organic Producers Co.",
            "commodity": "Ginger",
            "variety": "Mahim Gold",
            "grade": "Grade A",
            "harvest_date": today_str,
            "quantity_quintals": 85.0,
            "asking_price_per_quintal": 6400.0,
            "origin_location": "Satara, Maharashtra",
            "origin_distance_km_map": {"Vashi (Mumbai)": 260, "Azadpur (Delhi)": 1540},
            "photo_url": "https://example.com/ginger.jpg",
            "completed_orders": 42,
            "on_time_rate": 0.95,
            "quality_rating": 4.7,
        }

        created = add_fpo_listing(new_entry)
        self.assertTrue(created["listing_id"].startswith("FPO-"))
        self.assertEqual(created["freshness_tag"], "Harvest Fresh (<2 days)")
        self.assertEqual(created["age_days"], 0)

        # Confirm retrieval
        ginger_listings = get_fpo_listings(commodity="Ginger")
        self.assertTrue(any(l["listing_id"] == created["listing_id"] for l in ginger_listings))


if __name__ == "__main__":
    unittest.main()
