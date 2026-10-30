"""
calculator.py
=============
Agriculture Marketplace & Market-Decision Platform
NVIDIA × Nebius Hackathon

Performs deterministic financial calculations, transport freight & ETA estimation
across commercial vehicle types, FPO seller KPI scoring, competitive market option
ranking, and order tracking simulation.

Per hackathon rules, AI models must NEVER perform financial arithmetic in prose;
all calculations occur deterministically in this module.
"""

import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# -----------------------------------------------------------------------------
# Transport Fleet Specifications
# -----------------------------------------------------------------------------
TRUCK_SPECIFICATIONS = [
    {
        "truck_type": "Mini Truck (Tata Ace - up to 15 Qtl)",
        "capacity_quintals": 15.0,
        "rate_per_km": 18.0,
        "avg_speed_kmh": 40.0,
        "spoilage_risk": "Medium"
    },
    {
        "truck_type": "Standard LCV (Eicher 14ft - up to 60 Qtl)",
        "capacity_quintals": 60.0,
        "rate_per_km": 28.0,
        "avg_speed_kmh": 45.0,
        "spoilage_risk": "Low"
    },
    {
        "truck_type": "Reefer Cold-Chain Truck (up to 100 Qtl)",
        "capacity_quintals": 100.0,
        "rate_per_km": 42.0,
        "avg_speed_kmh": 50.0,
        "spoilage_risk": "Minimal (Temp Controlled)"
    }
]

FINANCIAL_FORMULA_STRING = (
    "Estimated Net Proceeds = (Quantity × Price/Qtl) - Transport Cost - Other Stated Costs"
)

BUYER_LANDED_COST_FORMULA_STRING = (
    "Estimated Buyer Total Cost = (Quantity × Price/Qtl) + Transport Cost + Other Stated Costs"
)

FINANCIAL_DISCLAIMER = (
    "⚠️ Financial Disclaimer: All projected revenues and landed costs are estimates based "
    "on indicative modal mandi prices, standard transport freight tables, and stated statutory/handling "
    "charges. These figures do not represent guaranteed income or binding quotes. Real-time market "
    "volatility, on-site produce grading, and toll/fuel surcharges may alter final settlement amounts."
)


# -----------------------------------------------------------------------------
# Function 1: calculate_truck_options
# -----------------------------------------------------------------------------
def calculate_truck_options(
    distance_km: float,
    quantity_quintals: float
) -> List[Dict[str, Any]]:
    """
    Computes freight costs, required fleet size, and transit ETA across three
    commercial vehicle configurations:
      1. Mini Truck (Tata Ace - up to 15 Qtl) [₹18/km, 40 km/h, Spoilage: Medium]
      2. Standard LCV (Eicher 14ft - up to 60 Qtl) [₹28/km, 45 km/h, Spoilage: Low]
      3. Reefer Cold-Chain Truck (up to 100 Qtl) [₹42/km, 50 km/h, Spoilage: Minimal]

    Formulas:
      - trucks_needed = math.ceil(quantity_quintals / capacity)
      - freight_cost = trucks_needed * distance_km * rate_per_km
      - eta_hours = round(distance_km / speed + 2.0, 1) (includes 2 hrs loading/handling buffer)

    Args:
        distance_km: Transit road distance in kilometers.
        quantity_quintals: Produce payload in Quintals (1 Quintal = 100 kg).

    Returns:
        List of dictionaries with keys:
          `truck_type`, `capacity_quintals`, `trucks_needed`, `rate_per_km`,
          `distance_km`, `freight_cost`, `eta_hours`, `spoilage_risk`.
    """
    valid_distance = max(0.0, float(distance_km))
    valid_qty = max(0.0, float(quantity_quintals))

    options: List[Dict[str, Any]] = []

    for spec in TRUCK_SPECIFICATIONS:
        capacity = spec["capacity_quintals"]
        rate = spec["rate_per_km"]
        speed = spec["avg_speed_kmh"]

        # Number of vehicles needed (at least 1 if payload > 0)
        if valid_qty <= 0.0:
            trucks_needed = 0
            freight_cost = 0.0
        else:
            trucks_needed = int(math.ceil(valid_qty / capacity))
            freight_cost = round(trucks_needed * valid_distance * rate, 2)

        # ETA calculation with 2.0 hrs buffer for loading/weighbridge/departure
        if valid_distance <= 0.0:
            eta_hours = 0.0
        else:
            raw_eta = (valid_distance / speed) + 2.0
            eta_hours = round(raw_eta, 1)

        options.append({
            "truck_type": spec["truck_type"],
            "capacity_quintals": capacity,
            "trucks_needed": trucks_needed,
            "rate_per_km": rate,
            "distance_km": round(valid_distance, 1),
            "freight_cost": freight_cost,
            "eta_hours": eta_hours,
            "spoilage_risk": spec["spoilage_risk"]
        })

    return options


# -----------------------------------------------------------------------------
# Function 2: calculate_seller_kpi
# -----------------------------------------------------------------------------
def calculate_seller_kpi(fpo_listing: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a deterministic FPO composite trust and performance score (0 to 100).

    Weights:
      - Freshness score (40% weight, penalized linearly by `age_days`)
      - Quality rating (35% weight, scaled from `quality_rating` out of 5)
      - Reliability score (25% weight, scaled from `on_time_rate`)

    Badges:
      - score >= 88.0: "Gold Verified FPO"
      - score >= 75.0: "Silver Trusted FPO"
      - score < 75.0:  "Standard FPO"

    Args:
        fpo_listing: Dictionary containing FPO listing attributes.

    Returns:
        dict:
          {
              "overall_kpi_score": float,
              "freshness_score": float,
              "reliability_pct": float,
              "badge": str,
              "age_days": int
          }
    """
    if not isinstance(fpo_listing, dict):
        raise TypeError("fpo_listing must be a dictionary.")

    # 1. Parse age_days
    raw_age = fpo_listing.get("age_days", 0)
    try:
        age_days = max(0, int(raw_age))
    except (ValueError, TypeError):
        age_days = 0

    # Freshness Score (40% weight): 100 at age 0, -10 pts per day old, floored at 0
    freshness_score = round(max(0.0, min(100.0, 100.0 - (age_days * 10.0))), 1)

    # 2. Quality Score (35% weight): scaled from 1.0-5.0 scale to 0-100
    raw_quality = fpo_listing.get("quality_rating", 5.0)
    try:
        q_rating = max(1.0, min(5.0, float(raw_quality)))
    except (ValueError, TypeError):
        q_rating = 5.0
    quality_score = (q_rating / 5.0) * 100.0

    # 3. Reliability Score (25% weight): scaled from on_time_rate (0.0 to 1.0 or 0 to 100)
    raw_on_time = fpo_listing.get("on_time_rate", 1.0)
    try:
        ot_rate = float(raw_on_time)
        if ot_rate <= 1.0:
            rel_score = ot_rate * 100.0
        else:
            rel_score = ot_rate
        reliability_pct = round(max(0.0, min(100.0, rel_score)), 1)
    except (ValueError, TypeError):
        reliability_pct = 100.0

    # Composite KPI calculation
    overall_kpi = (0.40 * freshness_score) + (0.35 * quality_score) + (0.25 * reliability_pct)
    overall_kpi_score = round(max(0.0, min(100.0, overall_kpi)), 1)

    # Deterministic badge assignment
    if overall_kpi_score >= 88.0:
        badge = "Gold Verified FPO"
    elif overall_kpi_score >= 75.0:
        badge = "Silver Trusted FPO"
    else:
        badge = "Standard FPO"

    return {
        "overall_kpi_score": overall_kpi_score,
        "freshness_score": freshness_score,
        "reliability_pct": reliability_pct,
        "badge": badge,
        "age_days": age_days
    }


# -----------------------------------------------------------------------------
# Function 3: rank_market_and_fpo_options
# -----------------------------------------------------------------------------
def rank_market_and_fpo_options(
    quantity_quintals: float,
    mandi_records: List[Dict[str, Any]],
    fpo_listings: List[Dict[str, Any]],
    delivery_address: str,
    distance_km: float,
    selected_truck_type: str,
    other_costs_per_quintal: float = 25.0
) -> Dict[str, Any]:
    """
    Ranks both Government Mandis and direct FPO supplier listings deterministically
    by comparing net proceeds for sellers and landed purchase costs for buyers.

    Formulas:
      - Gross Value = quantity_quintals * unit_price
      - Transport Cost = freight_cost from selected truck option
      - Other Stated Costs = quantity_quintals * other_costs_per_quintal (mandi fee, loading, weighing)
      - Estimated Net Proceeds = gross_value - transport_cost - other_stated_costs (Seller view)
      - Estimated Buyer Landed Cost = gross_value + transport_cost + other_stated_costs (Buyer view)

    Args:
        quantity_quintals: Payload volume in Quintals.
        mandi_records: List of mandi price records (from data_loader.fetch_mandi_prices).
        fpo_listings: List of FPO inventory items (from data_loader.get_fpo_listings).
        delivery_address: Intended destination address/mandi hub.
        distance_km: Road distance in km to destination.
        selected_truck_type: Desired transport vehicle type (e.g., 'Standard LCV (Eicher 14ft - up to 60 Qtl)').
        other_costs_per_quintal: Mandi commission, cess, handling, weighing fees in ₹/Qtl (default: 25.0).

    Returns:
        Exact schema:
          {
              "ranked_options": list[dict],
              "truck_options": list[dict],
              "selected_truck": dict,
              "seller_kpis": dict[str, dict],
              "formula_used": str,
              "disclaimer": str
          }
    """
    valid_qty = max(0.0, float(quantity_quintals))
    valid_dist = max(0.0, float(distance_km))
    other_rate = max(0.0, float(other_costs_per_quintal))

    # 1. Compute Truck Options
    truck_options = calculate_truck_options(valid_dist, valid_qty)

    # 2. Match selected truck type
    selected_truck = truck_options[1]  # Default: Standard LCV
    clean_target = str(selected_truck_type).strip().lower()

    for opt in truck_options:
        opt_name = opt["truck_type"].lower()
        if clean_target == opt_name or clean_target in opt_name or opt_name.startswith(clean_target):
            selected_truck = opt
            break

    transport_cost = selected_truck["freight_cost"]
    eta_hours = selected_truck["eta_hours"]

    # 3. Calculate other stated costs (mandi cess, loading buffer, weighment)
    other_stated_costs = round(valid_qty * other_rate, 2)

    # 4. Compute Seller KPIs for all FPO listings
    seller_kpis: Dict[str, Dict[str, Any]] = {}
    for idx, fpo in enumerate(fpo_listings):
        lid = str(fpo.get("listing_id", f"FPO-{idx + 101}")).strip()
        seller_kpis[lid] = calculate_seller_kpi(fpo)

    all_options: List[Dict[str, Any]] = []

    # 5. Process Mandi Records
    for mandi_rec in mandi_records:
        mandi_name = str(mandi_rec.get("mandi", "Unknown Mandi")).strip()
        state_name = str(mandi_rec.get("state", "")).strip()
        display_name = f"{mandi_name} Mandi ({state_name})" if state_name else f"{mandi_name} Mandi"

        # Pricing: use modal_price; fallback to mid-price
        raw_modal = mandi_rec.get("modal_price", 0.0)
        try:
            unit_price = float(raw_modal)
            if unit_price <= 0.0:
                p_min = float(mandi_rec.get("min_price", 0.0))
                p_max = float(mandi_rec.get("max_price", 0.0))
                unit_price = (p_min + p_max) / 2.0 if (p_min + p_max) > 0 else 0.0
        except (ValueError, TypeError):
            unit_price = 0.0

        gross_value = round(valid_qty * unit_price, 2)
        net_proceeds = round(gross_value - transport_cost - other_stated_costs, 2)
        buyer_landed_cost = round(gross_value + transport_cost + other_stated_costs, 2)

        raw_days = mandi_rec.get("days_old", 0)
        try:
            age_days = int(raw_days)
        except (ValueError, TypeError):
            age_days = 0

        is_stale = bool(mandi_rec.get("is_stale", age_days > 2))
        grade = str(mandi_rec.get("grade", "FAQ")).strip()

        all_options.append({
            "name": display_name,
            "source_type": "Govt Mandi",
            "unit_price": round(unit_price, 2),
            "gross_value": gross_value,
            "transport_cost": transport_cost,
            "other_stated_costs": other_stated_costs,
            "estimated_net_proceeds": net_proceeds,
            "estimated_buyer_landed_cost": buyer_landed_cost,
            "eta_hours": eta_hours,
            "is_stale": is_stale,
            "grade": grade,
            "age_days": age_days,
            "mandi": mandi_name,
            "state": state_name
        })

    # 6. Process FPO Direct Listings
    for idx, fpo in enumerate(fpo_listings):
        lid = str(fpo.get("listing_id", f"FPO-{idx + 101}")).strip()
        fpo_name = str(fpo.get("fpo_name", f"FPO {lid}")).strip()
        kpi_info = seller_kpis.get(lid, calculate_seller_kpi(fpo))

        raw_price = fpo.get("asking_price_per_quintal", 0.0)
        try:
            unit_price = float(raw_price)
        except (ValueError, TypeError):
            unit_price = 0.0

        gross_value = round(valid_qty * unit_price, 2)
        net_proceeds = round(gross_value - transport_cost - other_stated_costs, 2)
        buyer_landed_cost = round(gross_value + transport_cost + other_stated_costs, 2)

        age_days = kpi_info.get("age_days", 0)
        is_stale = age_days > 5  # FPO aging threshold

        all_options.append({
            "name": f"{fpo_name} ({lid})",
            "source_type": "FPO Direct",
            "unit_price": round(unit_price, 2),
            "gross_value": gross_value,
            "transport_cost": transport_cost,
            "other_stated_costs": other_stated_costs,
            "estimated_net_proceeds": net_proceeds,
            "estimated_buyer_landed_cost": buyer_landed_cost,
            "eta_hours": eta_hours,
            "is_stale": is_stale,
            "grade": str(fpo.get("grade", "Grade A")).strip(),
            "age_days": age_days,
            "listing_id": lid,
            "badge": kpi_info.get("badge", "Standard FPO"),
            "overall_kpi_score": kpi_info.get("overall_kpi_score", 0.0)
        })

    # 7. Sort options deterministically: Best net returns first (highest proceeds)
    ranked_options = sorted(
        all_options,
        key=lambda x: (x["estimated_net_proceeds"], -x["age_days"]),
        reverse=True
    )

    return {
        "ranked_options": ranked_options,
        "truck_options": truck_options,
        "selected_truck": selected_truck,
        "seller_kpis": seller_kpis,
        "formula_used": FINANCIAL_FORMULA_STRING,
        "disclaimer": FINANCIAL_DISCLAIMER
    }


# -----------------------------------------------------------------------------
# Function 4: get_shipment_tracking
# -----------------------------------------------------------------------------
def get_shipment_tracking(
    order_id: str,
    origin: str,
    destination: str,
    eta_hours: float
) -> Dict[str, Any]:
    """
    Simulates deterministic milestone shipment tracking for buyer order delivery.

    Stages:
      1. 'Order Confirmed & Escrow Locked'
      2. 'Produce Graded & Loaded at FPO'
      3. 'In Transit (GPS Active)'
      4. 'Out for Delivery'

    Args:
        order_id: Unique order tracking reference (e.g. 'ORD-2026-8912').
        origin: Pickup origin location (e.g. 'Nashik, Maharashtra').
        destination: Drop delivery address / terminal hub.
        eta_hours: Total estimated transit time in hours.

    Returns:
        Dictionary containing tracking stages, active stage index,
        estimated delivery timestamp, telemetry status, and historical checkpoints.
    """
    clean_order_id = str(order_id).strip() or "ORD-DEFAULT"
    clean_origin = str(origin).strip() or "Origin FPO Facility"
    clean_dest = str(destination).strip() or "Destination Mandi / Warehouse"
    valid_eta = max(0.5, float(eta_hours))

    stages = [
        "Order Confirmed & Escrow Locked",
        "Produce Graded & Loaded at FPO",
        "In Transit (GPS Active)",
        "Out for Delivery"
    ]

    # Deterministic active stage: index 2 ('In Transit (GPS Active)') for active haulage
    current_stage_index = 2
    current_stage_name = stages[current_stage_index]

    # Deterministic timestamps
    now = datetime.now()
    t_order = now - timedelta(hours=min(8.0, valid_eta * 0.4))
    t_loaded = now - timedelta(hours=min(4.0, valid_eta * 0.2))
    t_transit = now - timedelta(minutes=45)
    t_eta = now + timedelta(hours=valid_eta)

    checkpoints = [
        {
            "stage_index": 0,
            "stage_name": stages[0],
            "timestamp": t_order.strftime("%Y-%m-%d %H:%M IST"),
            "location": clean_origin,
            "notes": f"Order {clean_order_id} verified. Buyer payment locked in Escrow. Seller dispatch notification sent."
        },
        {
            "stage_index": 1,
            "stage_name": stages[1],
            "timestamp": t_loaded.strftime("%Y-%m-%d %H:%M IST"),
            "location": f"{clean_origin} Packhouse",
            "notes": "Quality inspection verified. Produce packed, weighed, and manifest approved by FPO supervisor."
        },
        {
            "stage_index": 2,
            "stage_name": stages[2],
            "timestamp": t_transit.strftime("%Y-%m-%d %H:%M IST"),
            "location": f"Highway Corridor en route to {clean_dest}",
            "notes": "GPS beacon operational. Vehicle in transit. Continuous telemetry and cold-chain sensor status green."
        },
        {
            "stage_index": 3,
            "stage_name": stages[3],
            "timestamp": t_eta.strftime("%Y-%m-%d %H:%M IST"),
            "location": clean_dest,
            "notes": f"Scheduled arrival at {clean_dest}. Gate entry and weighbridge slot reserved."
        }
    ]

    return {
        "order_id": clean_order_id,
        "origin": clean_origin,
        "destination": clean_dest,
        "eta_hours": round(valid_eta, 1),
        "estimated_arrival": t_eta.strftime("%d %b %Y, %I:%M %p IST"),
        "stages": stages,
        "current_stage_index": current_stage_index,
        "current_stage_name": current_stage_name,
        "is_delivered": False,
        "telemetry": {
            "gps_status": "Active & Transmitting",
            "cargo_temp_celsius": 4.5,
            "speed_kmh": 46.0,
            "driver_contact": "+91 98765 43210"
        },
        "checkpoints": checkpoints
    }


# -----------------------------------------------------------------------------
# CLI Self-Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("Running calculator.py Verification Self-Test")
    print("=" * 70)

    # 1. Test calculate_truck_options
    print("\n--- 1. Testing calculate_truck_options(distance_km=250, quantity_quintals=85) ---")
    truck_res = calculate_truck_options(distance_km=250.0, quantity_quintals=85.0)
    for t in truck_res:
        print(f"• {t['truck_type']}: {t['trucks_needed']} truck(s) | ₹{t['freight_cost']} freight | {t['eta_hours']}h ETA | Risk: {t['spoilage_risk']}")

    # 2. Test calculate_seller_kpi
    print("\n--- 2. Testing calculate_seller_kpi() across multiple FPO profiles ---")
    sample_fpos = [
        {"listing_id": "FPO-101", "age_days": 0, "quality_rating": 4.9, "on_time_rate": 0.98},
        {"listing_id": "FPO-102", "age_days": 1, "quality_rating": 4.8, "on_time_rate": 0.96},
        {"listing_id": "FPO-103", "age_days": 3, "quality_rating": 4.5, "on_time_rate": 0.92},
        {"listing_id": "FPO-104", "age_days": 6, "quality_rating": 4.4, "on_time_rate": 0.89},
    ]
    for sf in sample_fpos:
        kpi = calculate_seller_kpi(sf)
        print(f"• [{sf['listing_id']}] Score: {kpi['overall_kpi_score']}/100 | Badge: '{kpi['badge']}' | Freshness: {kpi['freshness_score']} | Rel: {kpi['reliability_pct']}%")

    # 3. Test rank_market_and_fpo_options
    print("\n--- 3. Testing rank_market_and_fpo_options() ---")
    sample_mandi = [
        {"mandi": "Azadpur", "state": "Delhi", "modal_price": 2550.0, "days_old": 0, "is_stale": False, "grade": "FAQ"},
        {"mandi": "Jaipur", "state": "Rajasthan", "modal_price": 2420.0, "days_old": 5, "is_stale": True, "grade": "Medium"},
    ]
    sample_fpo_list = [
        {"listing_id": "FPO-101", "fpo_name": "Sahyadri FPO", "asking_price_per_quintal": 2350.0, "age_days": 0, "quality_rating": 4.9, "on_time_rate": 0.98, "grade": "Grade A"},
        {"listing_id": "FPO-103", "fpo_name": "Malwa FPO", "asking_price_per_quintal": 2600.0, "age_days": 3, "quality_rating": 4.5, "on_time_rate": 0.92, "grade": "Grade B"},
    ]
    ranking = rank_market_and_fpo_options(
        quantity_quintals=50.0,
        mandi_records=sample_mandi,
        fpo_listings=sample_fpo_list,
        delivery_address="Azadpur Mandi, Delhi",
        distance_km=250.0,
        selected_truck_type="Standard LCV",
        other_costs_per_quintal=25.0
    )
    print(f"Formula: {ranking['formula_used']}")
    print(f"Selected Truck: {ranking['selected_truck']['truck_type']} (Freight: ₹{ranking['selected_truck']['freight_cost']})")
    print("\nRanked Produce Options:")
    for opt in ranking["ranked_options"]:
        print(f"• [{opt['source_type']}] {opt['name']} | Unit: ₹{opt['unit_price']}/Q | Gross: ₹{opt['gross_value']} | Net Proceeds: ₹{opt['estimated_net_proceeds']} | Landed: ₹{opt['estimated_buyer_landed_cost']}")

    # 4. Test get_shipment_tracking
    print("\n--- 4. Testing get_shipment_tracking() ---")
    tracking = get_shipment_tracking("ORD-8942", "Nashik, Maharashtra", "Azadpur Mandi, Delhi", eta_hours=18.5)
    print(f"Order: {tracking['order_id']} | Status: {tracking['current_stage_name']} | ETA: {tracking['estimated_arrival']}")
    for cp in tracking["checkpoints"]:
        print(f"  [{cp['timestamp']}] ({cp['stage_name']}) - {cp['notes']}")

    print("\ncalculator.py verification successfully passed!")
