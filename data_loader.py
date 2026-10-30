"""
data_loader.py
==============
Agriculture Marketplace & Market-Decision Platform
NVIDIA × Nebius Hackathon

Handles live retrieval, validation, and filtering of Indian Government Mandi prices
from the Open Government Data (OGD) AGMARKNET API, detects data staleness, provides
robust hackathon offline/fallback modes, and manages local JSON-backed Farmer Producer
Organization (FPO) produce inventory listings.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Configuration & Logging Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger("data_loader")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [data_loader]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

DATA_GOV_API_KEY: str = os.getenv("DATA_GOV_API_KEY", "").strip()
DATA_GOV_RESOURCE_ID: str = os.getenv(
    "DATA_GOV_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070"
).strip()
OGD_BASE_URL: str = f"https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}"

# Path to FPO listings storage
FPO_STORAGE_PATH: Path = Path(__file__).resolve().parent / "fpo_listings.json"

# Mandatory DataFrame column schema
MANDI_DATAFRAME_COLUMNS = [
    "mandi",
    "state",
    "commodity",
    "variety",
    "grade",
    "min_price",
    "max_price",
    "modal_price",
    "unit",
    "arrival_date",
    "days_old",
    "is_stale",
    "source"
]

# Baseline fallback price heuristics (INR / Quintal)
DEFAULT_COMMODITY_PRICES = {
    "tomato": {
        "Azadpur": {"min": 2300.0, "max": 2800.0, "modal": 2550.0},
        "Lasalgaon": {"min": 2100.0, "max": 2500.0, "modal": 2300.0},
        "Kolar": {"min": 1950.0, "max": 2400.0, "modal": 2180.0},
        "Jaipur": {"min": 2200.0, "max": 2650.0, "modal": 2420.0},
        "default": {"min": 2000.0, "max": 2600.0, "modal": 2350.0},
    },
    "onion": {
        "Azadpur": {"min": 2500.0, "max": 3100.0, "modal": 2800.0},
        "Lasalgaon": {"min": 2200.0, "max": 2700.0, "modal": 2450.0},
        "Kolar": {"min": 2350.0, "max": 2850.0, "modal": 2600.0},
        "Jaipur": {"min": 2400.0, "max": 2900.0, "modal": 2650.0},
        "default": {"min": 2250.0, "max": 2850.0, "modal": 2550.0},
    },
    "potato": {
        "Azadpur": {"min": 1400.0, "max": 1800.0, "modal": 1600.0},
        "Lasalgaon": {"min": 1300.0, "max": 1650.0, "modal": 1480.0},
        "Kolar": {"min": 1450.0, "max": 1850.0, "modal": 1650.0},
        "Jaipur": {"min": 1350.0, "max": 1700.0, "modal": 1520.0},
        "default": {"min": 1300.0, "max": 1750.0, "modal": 1525.0},
    },
    "wheat": {
        "Azadpur": {"min": 2700.0, "max": 3200.0, "modal": 2950.0},
        "Lasalgaon": {"min": 2600.0, "max": 3050.0, "modal": 2800.0},
        "Kolar": {"min": 2750.0, "max": 3150.0, "modal": 2920.0},
        "Jaipur": {"min": 2650.0, "max": 3000.0, "modal": 2820.0},
        "default": {"min": 2600.0, "max": 3100.0, "modal": 2850.0},
    },
}


# -----------------------------------------------------------------------------
# Internal Helper Functions
# -----------------------------------------------------------------------------
def _parse_arrival_date(raw_date: Any) -> Tuple[Optional[date], str]:
    """
    Parses various date representations from OGD Agmarknet into a date object
    and a normalized 'YYYY-MM-DD' string.
    """
    if raw_date is None or pd.isna(raw_date):
        return None, ""

    date_str = str(raw_date).strip()
    if not date_str:
        return None, ""

    common_formats = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d-%b-%Y",
    ]
    for fmt in common_formats:
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            return parsed, parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        ts = pd.to_datetime(date_str, dayfirst=True)
        if not pd.isna(ts):
            d = ts.date()
            return d, d.strftime("%Y-%m-%d")
    except Exception:
        pass

    return None, date_str


def _extract_dict_field(record: dict, *candidate_keys: str, default: Any = None) -> Any:
    """Case-insensitive dictionary field lookup."""
    for cand in candidate_keys:
        if cand in record and record[cand] is not None:
            return record[cand]
    lowered_map = {k.lower().strip(): v for k, v in record.items()}
    for cand in candidate_keys:
        cand_lower = cand.lower().strip()
        if cand_lower in lowered_map and lowered_map[cand_lower] is not None:
            return lowered_map[cand_lower]
    return default


def _calculate_freshness_metadata(harvest_date_str: str) -> Tuple[int, str]:
    """
    Computes age_days and freshness_tag dynamically based on harvest_date.
    
    Freshness Tag Rules:
      - age_days < 2:  "Harvest Fresh (<2 days)"
      - 2 <= age_days <= 5: "Standard (2-5 days)"
      - age_days > 5:  "Aging (>5 days)"
    """
    parsed_date, _ = _parse_arrival_date(harvest_date_str)
    if not parsed_date:
        today = date.today()
        return 0, "Harvest Fresh (<2 days)"

    today = date.today()
    age_days = max(0, (today - parsed_date).days)

    if age_days < 2:
        tag = "Harvest Fresh (<2 days)"
    elif age_days <= 5:
        tag = "Standard (2-5 days)"
    else:
        tag = "Aging (>5 days)"

    return age_days, tag


def _get_fallback_mandi_data(commodity: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generates realistic fallback Mandi data for at least 4 major mandis:
      1. Azadpur (Delhi) - Fresh (0 days old)
      2. Lasalgaon (Maharashtra) - Fresh (1 day old)
      3. Kolar (Karnataka) - Fresh (1 day old)
      4. Jaipur (Rajasthan) - Intentionally STALE (5 days old, is_stale=True)
    
    This ensures live hackathon demos can always demonstrate staleness warnings.
    """
    today = date.today()
    clean_crop = commodity.strip().lower()
    crop_benchmarks = DEFAULT_COMMODITY_PRICES.get(clean_crop)

    # Base price fallback if crop is not pre-mapped
    if not crop_benchmarks:
        base_hash = sum(ord(c) for c in clean_crop)
        base_modal = 1800.0 + (base_hash % 1500)
        crop_benchmarks = {
            "Azadpur": {"min": base_modal - 250.0, "max": base_modal + 250.0, "modal": base_modal},
            "Lasalgaon": {"min": base_modal - 350.0, "max": base_modal + 150.0, "modal": base_modal - 100.0},
            "Kolar": {"min": base_modal - 400.0, "max": base_modal + 200.0, "modal": base_modal - 120.0},
            "Jaipur": {"min": base_modal - 300.0, "max": base_modal + 200.0, "modal": base_modal - 50.0},
            "default": {"min": base_modal - 300.0, "max": base_modal + 200.0, "modal": base_modal},
        }

    display_crop = commodity.strip().title()

    # 4 Major mandis with Jaipur intentionally stale (5 days old)
    fallback_records = [
        {
            "mandi": "Azadpur",
            "state": "Delhi",
            "commodity": display_crop,
            "variety": "Hybrid / FAQ",
            "grade": "Grade A",
            "min_price": crop_benchmarks.get("Azadpur", crop_benchmarks["default"])["min"],
            "max_price": crop_benchmarks.get("Azadpur", crop_benchmarks["default"])["max"],
            "modal_price": crop_benchmarks.get("Azadpur", crop_benchmarks["default"])["modal"],
            "unit": "INR/Quintal",
            "arrival_date": today.strftime("%Y-%m-%d"),
            "days_old": 0,
            "is_stale": False,
            "source": "Fallback (Hackathon Demo Mode)"
        },
        {
            "mandi": "Lasalgaon",
            "state": "Maharashtra",
            "commodity": display_crop,
            "variety": "Local Red / Garwa",
            "grade": "Grade A",
            "min_price": crop_benchmarks.get("Lasalgaon", crop_benchmarks["default"])["min"],
            "max_price": crop_benchmarks.get("Lasalgaon", crop_benchmarks["default"])["max"],
            "modal_price": crop_benchmarks.get("Lasalgaon", crop_benchmarks["default"])["modal"],
            "unit": "INR/Quintal",
            "arrival_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_old": 1,
            "is_stale": False,
            "source": "Fallback (Hackathon Demo Mode)"
        },
        {
            "mandi": "Kolar",
            "state": "Karnataka",
            "commodity": display_crop,
            "variety": "Commercial Standard",
            "grade": "FAQ",
            "min_price": crop_benchmarks.get("Kolar", crop_benchmarks["default"])["min"],
            "max_price": crop_benchmarks.get("Kolar", crop_benchmarks["default"])["max"],
            "modal_price": crop_benchmarks.get("Kolar", crop_benchmarks["default"])["modal"],
            "unit": "INR/Quintal",
            "arrival_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_old": 1,
            "is_stale": False,
            "source": "Fallback (Hackathon Demo Mode)"
        },
        {
            "mandi": "Jaipur",
            "state": "Rajasthan",
            "commodity": display_crop,
            "variety": "Desi Medium",
            "grade": "Grade B",
            "min_price": crop_benchmarks.get("Jaipur", crop_benchmarks["default"])["min"],
            "max_price": crop_benchmarks.get("Jaipur", crop_benchmarks["default"])["max"],
            "modal_price": crop_benchmarks.get("Jaipur", crop_benchmarks["default"])["modal"],
            "unit": "INR/Quintal",
            "arrival_date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
            "days_old": 5,
            "is_stale": True,  # Intentionally stale to demo warnings
            "source": "Fallback (Hackathon Demo Mode)"
        }
    ]

    # If user filtered for a specific state not in the top 4, generate an entry for it
    if state:
        clean_state = state.strip().lower()
        existing_states = {r["state"].lower() for r in fallback_records}
        if clean_state not in existing_states:
            st_title = state.strip().title()
            default_p = crop_benchmarks["default"]
            fallback_records.append({
                "mandi": f"{st_title} Central",
                "state": st_title,
                "commodity": display_crop,
                "variety": "Regional FAQ",
                "grade": "Grade A",
                "min_price": default_p["min"],
                "max_price": default_p["max"],
                "modal_price": default_p["modal"],
                "unit": "INR/Quintal",
                "arrival_date": today.strftime("%Y-%m-%d"),
                "days_old": 0,
                "is_stale": False,
                "source": "Fallback (Hackathon Demo Mode)"
            })

    return fallback_records


# -----------------------------------------------------------------------------
# Function 1: fetch_mandi_prices
# -----------------------------------------------------------------------------
def fetch_mandi_prices(
    commodity: str,
    state: Optional[str] = None,
    market_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Queries Government of India Open Government Data (OGD) AGMARKNET API for
    live Mandi prices for the given commodity.

    Normalizes prices to INR/Quintal, validates arrival date freshness relative
    to current date, and flags stale (>2 days) or incomplete records.
    
    If DATA_GOV_API_KEY is not configured or the Government API times out / fails,
    gracefully switches to Hackathon Fallback Mode with realistic prices across
    major mandis (Azadpur, Lasalgaon, Kolar, Jaipur) including one intentionally
    stale record (Jaipur, days_old=5, is_stale=True).

    Args:
        commodity: Name of the agricultural commodity (e.g. 'Tomato', 'Onion', 'Potato', 'Wheat').
        state: Optional state filter (e.g. 'Maharashtra', 'Delhi').
        market_list: Optional list of specific mandis to filter against.

    Returns:
        dict with exact schema:
            {
                "dataframe": pd.DataFrame,
                "records": list[dict],
                "has_stale_data": bool,
                "missing_markets": list[str],
                "stale_warning_msg": str
            }
    """
    if not commodity or not commodity.strip():
        raise ValueError("Commodity parameter must be a non-empty string.")

    cleaned_commodity = commodity.strip()
    use_fallback = False
    raw_api_records: List[Dict[str, Any]] = []

    # 1. Check API Key configuration
    if not DATA_GOV_API_KEY or DATA_GOV_API_KEY in ["YOUR_API_KEY", "your_api_key_here"]:
        logger.info(
            "DATA_GOV_API_KEY not provided or is placeholder. Using Hackathon Fallback Mode."
        )
        use_fallback = True
    else:
        # 2. Attempt Live Government API Request
        params = {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 25,
            "filters[commodity]": cleaned_commodity,
        }
        if state:
            params["filters[state]"] = state.strip()

        try:
            headers = {
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                  }
            logger.info("Querying OGD AGMARKNET API: %s with commodity=%s", OGD_BASE_URL, cleaned_commodity)
            response = requests.get(OGD_BASE_URL, params=params, headers=headers, timeout=12)
            if response.status_code == 200:
                data = response.json()
                raw_api_records = data.get("records", [])
                if not raw_api_records:
                    logger.warning(
                        "Live API returned 0 records for commodity '%s'. Activating realistic fallback mode.",
                        cleaned_commodity
                    )
                    use_fallback = True
            else:
                logger.warning(
                    "OGD API returned status code %s. Falling back to demo data.",
                    response.status_code
                )
                use_fallback = True
        except (requests.RequestException, ValueError, Exception) as exc:
            logger.warning("OGD AGMARKNET API connection error: %s. Falling back to demo data.", exc)
            use_fallback = True

    # 3. Process Live Records or Build Fallback Records
    today = date.today()
    parsed_rows: List[Dict[str, Any]] = []

    if use_fallback or not raw_api_records:
        parsed_rows = _get_fallback_mandi_data(cleaned_commodity, state)
    else:
        for r in raw_api_records:
            mandi_name = _extract_dict_field(r, "market", "mandi", "Market_Center", default="Unknown")
            state_name = _extract_dict_field(r, "state", "State", default="Unknown")
            comm_name = _extract_dict_field(r, "commodity", "Commodity", default=cleaned_commodity)
            variety_name = _extract_dict_field(r, "variety", "Variety", default="FAQ")
            grade_name = _extract_dict_field(r, "grade", "Grade", default="FAQ")

            # Parse prices safely
            raw_min = _extract_dict_field(r, "min_price", "Min_x0020_Price", "Min_Price")
            raw_max = _extract_dict_field(r, "max_price", "Max_x0020_Price", "Max_Price")
            raw_modal = _extract_dict_field(r, "modal_price", "Modal_x0020_Price", "Modal_Price")

            try:
                min_price = float(raw_min) if raw_min is not None and str(raw_min).strip() != "" else 0.0
            except (ValueError, TypeError):
                min_price = 0.0

            try:
                max_price = float(raw_max) if raw_max is not None and str(raw_max).strip() != "" else 0.0
            except (ValueError, TypeError):
                max_price = 0.0

            try:
                modal_price = float(raw_modal) if raw_modal is not None and str(raw_modal).strip() != "" else 0.0
            except (ValueError, TypeError):
                modal_price = 0.0

            # Derive modal if missing but min/max are valid
            if modal_price <= 0.0 and (min_price > 0.0 and max_price > 0.0):
                modal_price = round((min_price + max_price) / 2.0, 2)

            raw_date = _extract_dict_field(r, "arrival_date", "Arrival_Date")
            parsed_dt, arrival_date_str = _parse_arrival_date(raw_date)

            if parsed_dt is not None:
                days_old = max(0, (today - parsed_dt).days)
            else:
                days_old = 999

            # Flag staleness: days_old > 2 OR missing essential price/date fields
            is_stale = (
                days_old > 2
                or modal_price <= 0.0
                or min_price <= 0.0
                or max_price <= 0.0
                or parsed_dt is None
                or mandi_name in ["Unknown", ""]
            )

            parsed_rows.append({
                "mandi": str(mandi_name).strip(),
                "state": str(state_name).strip(),
                "commodity": str(comm_name).strip(),
                "variety": str(variety_name).strip(),
                "grade": str(grade_name).strip(),
                "min_price": round(min_price, 2),
                "max_price": round(max_price, 2),
                "modal_price": round(modal_price, 2),
                "unit": "INR/Quintal",
                "arrival_date": arrival_date_str,
                "days_old": int(days_old),
                "is_stale": bool(is_stale),
                "source": "OGD AGMARKNET API (Live)"
            })

    # 4. Apply State and Market List Filters
    if state and state.strip():
        st_clean = state.strip().lower()
        parsed_rows = [r for r in parsed_rows if r["state"].strip().lower() == st_clean]

    missing_markets: List[str] = []
    if market_list:
        clean_target_markets = [m.strip() for m in market_list if m and m.strip()]
        matched_rows: List[Dict[str, Any]] = []
        found_market_names = set()

        for target in clean_target_markets:
            t_lower = target.lower()
            found = False
            for r in parsed_rows:
                r_mandi_lower = r["mandi"].lower()
                if t_lower == r_mandi_lower or t_lower in r_mandi_lower or r_mandi_lower in t_lower:
                    matched_rows.append(r)
                    found = True
                    found_market_names.add(target)
            if not found:
                missing_markets.append(target)

        # De-duplicate rows while preserving filter results
        unique_rows: List[Dict[str, Any]] = []
        seen = set()
        for row in matched_rows:
            key = (row["mandi"], row["arrival_date"], row["modal_price"])
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)
        parsed_rows = unique_rows

    # 5. Build DataFrame
    if parsed_rows:
        df = pd.DataFrame(parsed_rows)
        # Ensure exact column order and types
        for col in MANDI_DATAFRAME_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[MANDI_DATAFRAME_COLUMNS]
        df["min_price"] = df["min_price"].astype(float)
        df["max_price"] = df["max_price"].astype(float)
        df["modal_price"] = df["modal_price"].astype(float)
        df["days_old"] = df["days_old"].astype(int)
        df["is_stale"] = df["is_stale"].astype(bool)
    else:
        df = pd.DataFrame(columns=MANDI_DATAFRAME_COLUMNS)

    records = df.to_dict(orient="records")
    has_stale_data = bool(df["is_stale"].any()) if not df.empty else False

    # 6. Generate Human-Readable Stale / Missing Warning Message for Streamlit
    warning_clauses: List[str] = []
    if has_stale_data:
        stale_items = [
            f"{r['mandi']} ({r['days_old']}d old on {r['arrival_date']})"
            for r in records if r.get("is_stale")
        ]
        warning_clauses.append(
            f"Detected {len(stale_items)} mandi record(s) with stale pricing (>2 days old): {', '.join(stale_items)}"
        )

    if missing_markets:
        warning_clauses.append(
            f"No pricing data available for requested market(s): {', '.join(missing_markets)}"
        )

    if warning_clauses:
        stale_warning_msg = (
            f"⚠️ Mandi Data Warning: {'. '.join(warning_clauses)}. "
            "Market decision models and arbitrage calculators should apply safety discounts or verify local bids."
        )
    else:
        stale_warning_msg = ""

    return {
        "dataframe": df,
        "records": records,
        "has_stale_data": has_stale_data,
        "missing_markets": missing_markets,
        "stale_warning_msg": stale_warning_msg
    }


# -----------------------------------------------------------------------------
# Function 2: FPO Listings Store & Management
# -----------------------------------------------------------------------------
def _generate_seed_fpo_listings() -> List[Dict[str, Any]]:
    """
    Generates 4 pre-seeded realistic FPO listings with relative harvest dates
    covering fresh (<2 days), standard (2-5 days), and aging (>5 days) tiers.
    """
    today = date.today()

    return [
        {
            "listing_id": "FPO-101",
            "fpo_name": "Sahyadri Farmers Producer Co. Ltd.",
            "commodity": "Tomato",
            "variety": "Hybrid Shivam / Abhinav",
            "grade": "Grade A",
            "harvest_date": today.strftime("%Y-%m-%d"),
            "quantity_quintals": 180.0,
            "asking_price_per_quintal": 2350.0,
            "origin_location": "Nashik, Maharashtra",
            "origin_distance_km_map": {
                "Azadpur (Delhi)": 1280,
                "Vashi (Mumbai)": 165,
                "Lasalgaon": 42,
                "Jaipur": 1050,
                "Kolar": 980
            },
            "photo_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=600&q=80",
            "completed_orders": 312,
            "on_time_rate": 0.98,
            "quality_rating": 4.9
        },
        {
            "listing_id": "FPO-102",
            "fpo_name": "Lasalgaon Kisan Samriddhi Agro FPO",
            "commodity": "Onion",
            "variety": "Red Garwa Superior",
            "grade": "Grade A",
            "harvest_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "quantity_quintals": 350.0,
            "asking_price_per_quintal": 2550.0,
            "origin_location": "Lasalgaon, Maharashtra",
            "origin_distance_km_map": {
                "Azadpur (Delhi)": 1220,
                "Vashi (Mumbai)": 215,
                "Lasalgaon": 5,
                "Jaipur": 1010,
                "Kolar": 1020
            },
            "photo_url": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?auto=format&fit=crop&w=600&q=80",
            "completed_orders": 240,
            "on_time_rate": 0.96,
            "quality_rating": 4.8
        },
        {
            "listing_id": "FPO-103",
            "fpo_name": "Malwa Agritech Farmers Producer Society",
            "commodity": "Potato",
            "variety": "Kufri Jyoti Table Potato",
            "grade": "Grade B",
            "harvest_date": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "quantity_quintals": 520.0,
            "asking_price_per_quintal": 1420.0,
            "origin_location": "Indore, Madhya Pradesh",
            "origin_distance_km_map": {
                "Azadpur (Delhi)": 810,
                "Vashi (Mumbai)": 590,
                "Lasalgaon": 420,
                "Jaipur": 570,
                "Kolar": 1250
            },
            "photo_url": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80",
            "completed_orders": 145,
            "on_time_rate": 0.92,
            "quality_rating": 4.5
        },
        {
            "listing_id": "FPO-104",
            "fpo_name": "Kolar Krishi Kalyan Producer Co.",
            "commodity": "Wheat",
            "variety": "Sharbati Grain Gold",
            "grade": "Grade A",
            "harvest_date": (today - timedelta(days=6)).strftime("%Y-%m-%d"),
            "quantity_quintals": 260.0,
            "asking_price_per_quintal": 2820.0,
            "origin_location": "Kolar, Karnataka",
            "origin_distance_km_map": {
                "Azadpur (Delhi)": 2080,
                "Vashi (Mumbai)": 990,
                "Lasalgaon": 970,
                "Jaipur": 1950,
                "Kolar": 0
            },
            "photo_url": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80",
            "completed_orders": 88,
            "on_time_rate": 0.89,
            "quality_rating": 4.4
        }
    ]


def _ensure_fpo_storage_exists() -> List[Dict[str, Any]]:
    """Ensures fpo_listings.json exists and returns loaded raw records."""
    if not FPO_STORAGE_PATH.exists():
        initial_data = _generate_seed_fpo_listings()
        try:
            with open(FPO_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            logger.info("Created pre-seeded FPO storage at %s", FPO_STORAGE_PATH)
            return initial_data
        except Exception as exc:
            logger.error("Failed to write seed FPO storage file: %s", exc)
            return initial_data

    try:
        with open(FPO_STORAGE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as exc:
        logger.error("Error reading %s: %s. Re-seeding.", FPO_STORAGE_PATH, exc)
        initial_data = _generate_seed_fpo_listings()
        with open(FPO_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        return initial_data


def get_fpo_listings(commodity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves FPO produce listings from the JSON-backed storage.
    
    Dynamically computes:
      - 'age_days': Days elapsed between harvest_date and today.
      - 'freshness_tag': 'Harvest Fresh (<2 days)', 'Standard (2-5 days)', or 'Aging (>5 days)'.

    Args:
        commodity: Optional crop name filter (case-insensitive).

    Returns:
        List of listing dictionaries matching all schema requirements.
    """
    raw_listings = _ensure_fpo_storage_exists()
    processed: List[Dict[str, Any]] = []

    for item in raw_listings:
        # Dynamically compute freshness
        h_date = str(item.get("harvest_date", "")).strip()
        age_days, freshness_tag = _calculate_freshness_metadata(h_date)

        listing = {
            "listing_id": str(item.get("listing_id", "")).strip(),
            "fpo_name": str(item.get("fpo_name", "")).strip(),
            "commodity": str(item.get("commodity", "")).strip(),
            "variety": str(item.get("variety", "")).strip(),
            "grade": str(item.get("grade", "Grade A")).strip(),
            "harvest_date": h_date,
            "age_days": int(age_days),
            "freshness_tag": freshness_tag,
            "quantity_quintals": float(item.get("quantity_quintals", 0.0)),
            "asking_price_per_quintal": float(item.get("asking_price_per_quintal", 0.0)),
            "origin_location": str(item.get("origin_location", "")).strip(),
            "origin_distance_km_map": dict(item.get("origin_distance_km_map", {})),
            "photo_url": str(item.get("photo_url", "")).strip(),
            "completed_orders": int(item.get("completed_orders", 0)),
            "on_time_rate": float(item.get("on_time_rate", 1.0)),
            "quality_rating": float(item.get("quality_rating", 5.0)),
        }

        # Apply commodity filter if requested
        if commodity and commodity.strip():
            if listing["commodity"].lower() != commodity.strip().lower():
                continue

        processed.append(listing)

    return processed


def add_fpo_listing(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds a new FPO produce listing to the JSON-backed storage and persists it.

    Computes dynamic age_days and freshness_tag from harvest_date, generates
    an incremental listing_id if not provided, and validates numeric ranges.

    Args:
        listing_data: Dictionary containing FPO listing attributes.

    Returns:
        The newly created listing dictionary.
    """
    if not isinstance(listing_data, dict):
        raise TypeError("listing_data must be a dictionary.")

    existing_listings = _ensure_fpo_storage_exists()

    # Generate listing_id if missing
    existing_id = listing_data.get("listing_id")
    if not existing_id or str(existing_id).strip() == "":
        max_num = 100
        for item in existing_listings:
            lid = str(item.get("listing_id", ""))
            if lid.startswith("FPO-"):
                try:
                    num = int(lid.split("-")[1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        new_id = f"FPO-{max_num + 1}"
    else:
        new_id = str(existing_id).strip()

    # Harvest date handling
    raw_hdate = listing_data.get("harvest_date")
    parsed_hdt, hdate_str = _parse_arrival_date(raw_hdate)
    if not parsed_hdt:
        hdate_str = date.today().strftime("%Y-%m-%d")

    age_days, freshness_tag = _calculate_freshness_metadata(hdate_str)

    # Clean & validate numeric bounds
    try:
        qty = float(listing_data.get("quantity_quintals", 0.0))
    except (ValueError, TypeError):
        qty = 0.0

    try:
        asking_price = float(listing_data.get("asking_price_per_quintal", 0.0))
    except (ValueError, TypeError):
        asking_price = 0.0

    try:
        completed = int(listing_data.get("completed_orders", 0))
    except (ValueError, TypeError):
        completed = 0

    try:
        on_time = max(0.0, min(1.0, float(listing_data.get("on_time_rate", 1.0))))
    except (ValueError, TypeError):
        on_time = 1.0

    try:
        rating = max(1.0, min(5.0, float(listing_data.get("quality_rating", 5.0))))
    except (ValueError, TypeError):
        rating = 5.0

    dist_map = listing_data.get("origin_distance_km_map")
    if not isinstance(dist_map, dict):
        dist_map = {}

    new_record = {
        "listing_id": new_id,
        "fpo_name": str(listing_data.get("fpo_name", "Registered FPO")).strip(),
        "commodity": str(listing_data.get("commodity", "")).strip().title(),
        "variety": str(listing_data.get("variety", "Standard")).strip(),
        "grade": str(listing_data.get("grade", "Grade A")).strip(),
        "harvest_date": hdate_str,
        "age_days": age_days,
        "freshness_tag": freshness_tag,
        "quantity_quintals": round(qty, 2),
        "asking_price_per_quintal": round(asking_price, 2),
        "origin_location": str(listing_data.get("origin_location", "India")).strip(),
        "origin_distance_km_map": dist_map,
        "photo_url": str(listing_data.get("photo_url", "")).strip(),
        "completed_orders": completed,
        "on_time_rate": round(on_time, 2),
        "quality_rating": round(rating, 2),
    }

    # Upsert or append
    updated_listings = []
    replaced = False
    for item in existing_listings:
        if str(item.get("listing_id")).strip() == new_id:
            updated_listings.append(new_record)
            replaced = True
        else:
            updated_listings.append(item)

    if not replaced:
        updated_listings.append(new_record)

    with open(FPO_STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_listings, f, indent=2, ensure_ascii=False)

    logger.info("Successfully saved FPO listing %s (%s)", new_id, new_record["commodity"])
    return new_record


# -----------------------------------------------------------------------------
# Module CLI Self-Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("Running data_loader.py Verification Test")
    print("=" * 70)

    # 1. Test fetch_mandi_prices
    print("\n--- 1. Testing fetch_mandi_prices('Tomato') ---")
    res = fetch_mandi_prices("Tomato", market_list=["Azadpur", "Lasalgaon", "Jaipur", "Kolkata"])
    print(f"Dataframe Shape: {res['dataframe'].shape}")
    print(f"Columns: {list(res['dataframe'].columns)}")
    print(f"Has Stale Data: {res['has_stale_data']}")
    print(f"Missing Markets: {res['missing_markets']}")
    print(f"Stale Warning Msg:\n{res['stale_warning_msg']}")
    print("\nMandi Price Table:")
    print(res["dataframe"][["mandi", "state", "modal_price", "arrival_date", "days_old", "is_stale"]])

    # 2. Test get_fpo_listings
    print("\n--- 2. Testing get_fpo_listings() ---")
    all_fpos = get_fpo_listings()
    print(f"Total FPO listings found: {len(all_fpos)}")
    for fpo in all_fpos:
        print(f"• [{fpo['listing_id']}] {fpo['fpo_name']} | {fpo['commodity']} | {fpo['asking_price_per_quintal']} INR/Q | Age: {fpo['age_days']}d ({fpo['freshness_tag']})")

    # 3. Test add_fpo_listing
    print("\n--- 3. Testing add_fpo_listing() ---")
    test_listing = {
        "fpo_name": "Godavari Valley Farmers Producer Co.",
        "commodity": "Tomato",
        "variety": "Arka Rakshak",
        "grade": "Grade A",
        "harvest_date": date.today().strftime("%Y-%m-%d"),
        "quantity_quintals": 120.0,
        "asking_price_per_quintal": 2400.0,
        "origin_location": "Nanded, Maharashtra",
        "origin_distance_km_map": {"Vashi (Mumbai)": 580, "Azadpur (Delhi)": 1380},
        "photo_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea",
        "completed_orders": 64,
        "on_time_rate": 0.97,
        "quality_rating": 4.8
    }
    added = add_fpo_listing(test_listing)
    print(f"Added Listing: {added['listing_id']} -> {added['fpo_name']} ({added['freshness_tag']})")

    # 4. Verify filtering
    print("\n--- 4. Testing get_fpo_listings(commodity='Tomato') ---")
    tomatoes = get_fpo_listings(commodity="Tomato")
    print(f"Filtered Tomato listings: {len(tomatoes)}")

    print("\nVerification successfully completed!")
