"""
sample_data.py
==============
Rich sample catalog and fallback data for the NVIDIA × Nebius Hackathon
Autonomous Agriculture Marketplace & Market-Decision Platform.

Provides:
  1. CROPS_CATALOG: Detailed crops metadata, images, price benchmarks, and seasons.
  2. SAMPLE_TOP_5_ANALYSIS: Pre-computed realistic top 5 places with detailed
     merits and demerits across major commodities and destinations.
  3. generate_dynamic_fallback_analysis(): Smart generator creating tailored
     merits and demerits for any custom crop/route combination when offline.
"""

from typing import Dict, Any, List

# -----------------------------------------------------------------------------
# 1. Crops Catalog (Photos, descriptions, typical price bands)
# -----------------------------------------------------------------------------
CROPS_CATALOG = {
    "Tomato": {
        "name": "Tomato",
        "scientific_name": "Solanum lycopersicum",
        "icon": "🍅",
        "tagline": "Juicy, firm hybrid varieties with long shelf life",
        "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["Hybrid Shivam", "Abhinav", "Arka Rakshak", "Pusa Ruby"],
        "typical_price_range_inr": (2100.0, 2800.0),
        "major_production_hubs": ["Nashik (MH)", "Kolar (KA)", "Madanapalle (AP)", "Jaipur (RJ)"],
        "shelf_life_days": "7 - 12 days",
        "ideal_temp_celsius": "12°C - 15°C",
    },
    "Onion": {
        "name": "Onion",
        "scientific_name": "Allium cepa",
        "icon": "🧅",
        "tagline": "Pungent, high-dry-matter Red Garwa and Nashik bulbs",
        "image_url": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["Red Garwa", "Nashik Red", "Pusa Red", "Bhima Super"],
        "typical_price_range_inr": (2300.0, 3100.0),
        "major_production_hubs": ["Lasalgaon (MH)", "Ahmednagar (MH)", "Hubli (KA)", "Kurnool (AP)"],
        "shelf_life_days": "30 - 60 days (ambient ventilated)",
        "ideal_temp_celsius": "Ambient Dry / Well Ventilated",
    },
    "Potato": {
        "name": "Potato",
        "scientific_name": "Solanum tuberosum",
        "icon": "🥔",
        "tagline": "Grade A Table & processing potatoes with low sugar content",
        "image_url": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["Kufri Jyoti", "Kufri Chipsona", "Kufri Pukhraj", "Lauvkar"],
        "typical_price_range_inr": (1300.0, 1850.0),
        "major_production_hubs": ["Agra (UP)", "Indore (MP)", "Jalandhar (PB)", "Deesa (GJ)"],
        "shelf_life_days": "60 - 90 days (Cold store)",
        "ideal_temp_celsius": "7°C - 10°C",
    },
    "Wheat": {
        "name": "Wheat",
        "scientific_name": "Triticum aestivum",
        "icon": "🌾",
        "tagline": "Premium high-protein Sharbati and Lokwan golden grains",
        "image_url": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["Sharbati Premium", "MP Lokwan", "HD 2967", "PBW 343"],
        "typical_price_range_inr": (2650.0, 3200.0),
        "major_production_hubs": ["Khanna (PB)", "Sehore (MP)", "Kolar (KA)", "Karnal (HR)"],
        "shelf_life_days": "6 - 12 months",
        "ideal_temp_celsius": "Dry Ambient (<12% moisture)",
    },
    "Green Chilli": {
        "name": "Green Chilli",
        "scientific_name": "Capsicum annuum",
        "icon": "🌶️",
        "tagline": "Spicy, fresh green pods with strong market demand",
        "image_url": "https://images.unsplash.com/photo-1588252303782-cb80119abd6d?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["G-4", "Teja", "Jwala", "Bullet Chilli"],
        "typical_price_range_inr": (3500.0, 5200.0),
        "major_production_hubs": ["Guntur (AP)", "Nagpur (MH)", "Belgaum (KA)", "Jaipur (RJ)"],
        "shelf_life_days": "5 - 8 days",
        "ideal_temp_celsius": "7°C - 10°C",
    },
    "Ginger": {
        "name": "Ginger",
        "scientific_name": "Zingiber officinale",
        "icon": "🫚",
        "tagline": "Aromatic, fiber-rich Mahim and Rio-de-Janeiro rhizomes",
        "image_url": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80",
        "popular_varieties": ["Mahim Gold", "Maran", "Nadia", "Rio de Janeiro"],
        "typical_price_range_inr": (5800.0, 7500.0),
        "major_production_hubs": ["Satara (MH)", "Wayanad (KL)", "Shimoga (KA)", "East Sikkim (SK)"],
        "shelf_life_days": "20 - 30 days",
        "ideal_temp_celsius": "12°C - 14°C",
    }
}


# -----------------------------------------------------------------------------
# 2. Rich Pre-Computed Top 5 Places Analysis (Fallback Database)
# -----------------------------------------------------------------------------
SAMPLE_TOP_5_ANALYSIS: Dict[str, List[Dict[str, Any]]] = {
    "Tomato": [
        {
            "rank": 1,
            "name": "Sahyadri Farmers Producer Co. Ltd.",
            "location": "Nashik, Maharashtra",
            "source_type": "FPO Direct",
            "unit_price": 2350.0,
            "badge": "Gold Verified FPO",
            "kpi_score": 98.8,
            "freshness": "Harvest Fresh (0 days old)",
            "merits": [
                "Direct farmgate lot harvested this morning (<24h), ensuring maximum retail shelf-life of 10+ days.",
                "Zero commission fee overhead; contract-grade produce graded on automated sorting lines with <2% defect.",
                "Lowest estimated landed cost in category, delivering a net savings of ₹14,200 compared to spot wholesale mandis.",
                "Proven delivery track record with 98% on-time logistics and instant digital escrow settlement."
            ],
            "demerits": [
                "Requires transit booking with Reefer or covered LCV to prevent sunlight scald across Maharashtra-Delhi corridor.",
                "Strict minimum lot size requirement of 40 Quintals for guaranteed priority dispatch."
            ],
            "recommendation_summary": "Top choice for institutional buyers and supermarket chains requiring premium firmness and maximum shelf life."
        },
        {
            "rank": 2,
            "name": "Azadpur Wholesale Mandi",
            "location": "NCT of Delhi",
            "source_type": "Govt Mandi",
            "unit_price": 2550.0,
            "badge": "Central APMC Terminal",
            "kpi_score": 85.0,
            "freshness": "Live Arrival (Today)",
            "merits": [
                "Zero transit distance if buyer has central Delhi distribution center; immediate local lot pickup available.",
                "Massive daily liquidity and arrival volumes exceeding 400 Metric Tonnes across multiple traders.",
                "High pricing transparency governed by daily OGD AGMARKNET e-auction records."
            ],
            "demerits": [
                "Unit price is ₹200/Qtl higher than direct FPO farmgate contracts.",
                "Subject to local mandi cess (1.5%), handling buffer, and manual weighbridge queuing delays.",
                "Lot homogeneity varies as crates are aggregated from disparate smallholder farmers."
            ],
            "recommendation_summary": "Best for emergency same-day replenishment where long-distance transit time cannot be tolerated."
        },
        {
            "rank": 3,
            "name": "Lasalgaon Kisan Samriddhi Agro FPO",
            "location": "Lasalgaon, Maharashtra",
            "source_type": "FPO Direct",
            "unit_price": 2300.0,
            "badge": "Gold Verified FPO",
            "kpi_score": 93.6,
            "freshness": "Harvest Fresh (1 day old)",
            "merits": [
                "Highly competitive base unit price of ₹2,300/Qtl (₹50 cheaper than Nashik).",
                "High dry matter content suitable for both fresh retail and processing/puree manufacturing.",
                "Protected by digital escrow with sample-matched quality verification."
            ],
            "demerits": [
                "Consignment is 1 day post-harvest; requires temperature-managed loading.",
                "Slightly smaller vehicle fleet availability during peak onion harvesting cycles."
            ],
            "recommendation_summary": "Ideal cost-effective procurement option for regional wholesale distributors and food processors."
        },
        {
            "rank": 4,
            "name": "Kolar Mandi Hub",
            "location": "Kolar, Karnataka",
            "source_type": "Govt Mandi",
            "unit_price": 2180.0,
            "badge": "Southern APMC Hub",
            "kpi_score": 82.0,
            "freshness": "Arrival Record (1 day old)",
            "merits": [
                "Lowest base wholesale rate in India (₹2,180/Qtl) due to bumper southern production.",
                "High proportion of firm Hybrid varieties suited for long-distance transport."
            ],
            "demerits": [
                "Long transit distance (>1,900 km to North India) pushes freight cost to ₹28,000+ per vehicle.",
                "Estimated transit time of 42+ hours introduces severe spoilage risk without Reefer Cold-Chain."
            ],
            "recommendation_summary": "Highly recommended for Southern/Western buyers (Bangalore/Chennai/Hyderabad) but economically unfavorable for North India."
        },
        {
            "rank": 5,
            "name": "Jaipur APMC Mandi",
            "location": "Jaipur, Rajasthan",
            "source_type": "Govt Mandi",
            "unit_price": 2420.0,
            "badge": "Regional Mandi (Stale Caveat)",
            "kpi_score": 68.0,
            "freshness": "STALE DATA (5 days old)",
            "merits": [
                "Moderate geographic proximity to NCR and Northern consumption markets (approx 260 km).",
                "Reasonable local road connectivity via Delhi-Mumbai Expressway."
            ],
            "demerits": [
                "DATA STALENESS WARNING: Agmarknet records are 5 days old (arrival 25 Oct), making price quotes unreliable.",
                "High probability that spot market rates have fluctuated significantly by 15-20%.",
                "Risk of physical stock unavailability at the quoted benchmark."
            ],
            "recommendation_summary": "Exercise caution. Do not bid without live telephone verification from the local mandi market committee."
        }
    ],

    "Onion": [
        {
            "rank": 1,
            "name": "Lasalgaon Kisan Samriddhi Agro FPO",
            "location": "Lasalgaon, Maharashtra",
            "source_type": "FPO Direct",
            "unit_price": 2550.0,
            "badge": "Gold Verified FPO",
            "kpi_score": 96.5,
            "freshness": "Harvest Fresh (1 day old)",
            "merits": [
                "Located at Asia's largest onion hub; supplies genuine Red Garwa onions with high pungency and dry matter.",
                "Direct farm curing ensures thick outer skin, minimizing transit sprouting and weight shrinkage to <1.5%.",
                "Competitive asking price of ₹2,550/Qtl saves approx ₹250/Qtl over Delhi terminal market bids.",
                "100% verified digital escrow payment with fast dispatch within 12 hours of order confirmation."
            ],
            "demerits": [
                "Requires well-ventilated dry transport; canvas-covered trucks must avoid rain moisture.",
                "High demand corridor can occasionally lead to toll plaza queuing on NH-3."
            ],
            "recommendation_summary": "The premier choice for large-scale institutional onion procurement in India."
        },
        {
            "rank": 2,
            "name": "Azadpur Terminal Mandi",
            "location": "Delhi",
            "source_type": "Govt Mandi",
            "unit_price": 2800.0,
            "badge": "Central APMC Terminal",
            "kpi_score": 86.0,
            "freshness": "Live Arrival (Today)",
            "merits": [
                "Immediate local delivery with no interstate transit freight for Delhi-NCR buyers.",
                "Opportunity for physical lot inspection and immediate gate delivery."
            ],
            "demerits": [
                "Premium price tag of ₹2,800/Qtl (₹250 higher per quintal).",
                "Additional local unloading, weighing, and market cess fees totaling ₹35/Qtl."
            ],
            "recommendation_summary": "Best for spot retail purchase when delivery is needed within 4 hours."
        },
        {
            "rank": 3,
            "name": "Sahyadri Farmers Producer Co. Ltd.",
            "location": "Nashik, Maharashtra",
            "source_type": "FPO Direct",
            "unit_price": 2580.0,
            "badge": "Gold Verified FPO",
            "kpi_score": 94.0,
            "freshness": "Harvest Fresh (2 days old)",
            "merits": [
                "Graded mechanically into 45mm+ and 55mm+ uniform retail packaging mesh bags.",
                "High customer reliability score (98% on-time fulfillment across 312 completed orders)."
            ],
            "demerits": [
                "Slightly higher asking rate compared to Lasalgaon FPO (+₹30/Qtl)."
            ],
            "recommendation_summary": "Top choice for premium supermarket chains requiring pre-graded, uniform mesh bag packing."
        },
        {
            "rank": 4,
            "name": "Kolar APMC Mandi",
            "location": "Kolar, Karnataka",
            "source_type": "Govt Mandi",
            "unit_price": 2600.0,
            "badge": "Southern APMC Hub",
            "kpi_score": 80.0,
            "freshness": "Arrival (1 day old)",
            "merits": [
                "Medium-sized Bellary onion bulbs with sweet taste profile suited for coastal cuisines.",
                "Adequate daily stock availability."
            ],
            "demerits": [
                "High freight costs to North Indian destinations.",
                "Higher moisture content increases rot risk during multi-day hauls."
            ],
            "recommendation_summary": "Recommended for southern state procurement."
        },
        {
            "rank": 5,
            "name": "Jaipur APMC Mandi",
            "location": "Jaipur, Rajasthan",
            "source_type": "Govt Mandi",
            "unit_price": 2650.0,
            "badge": "Regional Mandi (Stale Caveat)",
            "kpi_score": 67.0,
            "freshness": "STALE DATA (5 days old)",
            "merits": [
                "Proximity to Western and Northern transport corridors."
            ],
            "demerits": [
                "Stale price data (5 days old); spot market is likely volatile.",
                "Local stock is largely un-graded mixed sizes."
            ],
            "recommendation_summary": "High price uncertainty. Verify local bids before making purchase commitments."
        }
    ],

    "Potato": [
        {
            "rank": 1,
            "name": "Malwa Agritech Farmers Producer Society",
            "location": "Indore, Madhya Pradesh",
            "source_type": "FPO Direct",
            "unit_price": 1420.0,
            "badge": "Silver Trusted FPO",
            "kpi_score": 82.5,
            "freshness": "Standard (3 days old)",
            "merits": [
                "Famous Malwa Kufri Jyoti table potatoes known for smooth golden skin and shallow eyes.",
                "Direct farmgate rate of ₹1,420/Qtl, providing significant margin advantage over terminal mandis.",
                "Cold-room conditioned before loading, eliminating skin peeling and bruising during haulage.",
                "Fully protected via Razorpay digital escrow with QA moisture inspection."
            ],
            "demerits": [
                "Produce is 3 days post-harvest; requires cool transit to maintain low sugar conversion.",
                "Indore to Delhi transit distance (810 km) requires ~20 hours transit."
            ],
            "recommendation_summary": "Best overall value for wholesale distributors and institutional potato processors."
        },
        {
            "rank": 2,
            "name": "Azadpur Wholesale Mandi",
            "location": "Delhi",
            "source_type": "Govt Mandi",
            "unit_price": 1600.0,
            "badge": "Central APMC Terminal",
            "kpi_score": 84.0,
            "freshness": "Live Arrival (Today)",
            "merits": [
                "Huge daily arrivals from Agra and Punjab; instantaneous loading and dispatch in NCR.",
                "Multiple size classifications available on the spot (Large, Medium, Small)."
            ],
            "demerits": [
                "Price is ₹180/Qtl higher than direct Malwa FPO supply.",
                "APMC market cess and handling overhead add ₹30/Qtl to landed cost."
            ],
            "recommendation_summary": "Reliable same-day option when immediate delivery is non-negotiable."
        },
        {
            "rank": 3,
            "name": "Agra Cold Storage Hub",
            "location": "Agra, Uttar Pradesh",
            "source_type": "Govt Mandi",
            "unit_price": 1480.0,
            "badge": "UP Production Belt",
            "kpi_score": 81.0,
            "freshness": "Arrival (1 day old)",
            "merits": [
                "Proximity to Delhi-NCR (only 210 km via Yamuna Expressway); low transport freight of ~₹5,800 per truck.",
                "High density of specialized cold storage facilities."
            ],
            "demerits": [
                "Cold-stored potatoes must be acclimated to ambient temperature to avoid surface condensation."
            ],
            "recommendation_summary": "Excellent regional option for North India with very low transit freight."
        },
        {
            "rank": 4,
            "name": "Lasalgaon Mandi",
            "location": "Lasalgaon, Maharashtra",
            "source_type": "Govt Mandi",
            "unit_price": 1480.0,
            "badge": "Western Mandi",
            "kpi_score": 78.0,
            "freshness": "Arrival (1 day old)",
            "merits": [
                "Moderate price; convenient for buyers consolidating mixed truckloads of onion and potato."
            ],
            "demerits": [
                "Higher transport cost to northern states."
            ],
            "recommendation_summary": "Optimal for Western India buyers combining onion and potato shipments."
        },
        {
            "rank": 5,
            "name": "Jaipur APMC Mandi",
            "location": "Jaipur, Rajasthan",
            "source_type": "Govt Mandi",
            "unit_price": 1520.0,
            "badge": "Regional Mandi (Stale Caveat)",
            "kpi_score": 66.0,
            "freshness": "STALE DATA (5 days old)",
            "merits": [
                "Direct highway connectivity to Delhi."
            ],
            "demerits": [
                "Stale price quotes (5 days old); APMC auction records are not current.",
                "Smaller local production volume compared to Agra or Malwa."
            ],
            "recommendation_summary": "Not recommended until fresh auction records are updated."
        }
    ],

    "Wheat": [
        {
            "rank": 1,
            "name": "Kolar Krishi Kalyan Producer Co.",
            "location": "Kolar, Karnataka",
            "source_type": "FPO Direct",
            "unit_price": 2820.0,
            "badge": "Standard FPO",
            "kpi_score": 69.1,
            "freshness": "Standard Grains (6 days old)",
            "merits": [
                "Pre-cleaned Sharbati grain with <10.5% moisture and zero foreign matter.",
                "Competitive asking price for export-quality high-protein wheat grain.",
                "Complete digital transaction secured with Razorpay escrow lock."
            ],
            "demerits": [
                "Located in Karnataka; long haulage to Northern flour mills increases freight.",
                "Smaller lot volumes compared to Punjab/MP grain mandis."
            ],
            "recommendation_summary": "Best suited for southern flour millers and regional specialty bakeries."
        },
        {
            "rank": 2,
            "name": "Khanna Grain Market",
            "location": "Khanna, Punjab",
            "source_type": "Govt Mandi",
            "unit_price": 2750.0,
            "badge": "Asia's Largest Grain Mandi",
            "kpi_score": 88.0,
            "freshness": "Live Arrival (Today)",
            "merits": [
                "Immense daily liquidity; Asia's largest wheat and grain trading terminal.",
                "Lowest northern base price for FCI-standard HD 2967 and HD 3086 wheat.",
                "Fast mechanized bagging and weighbridge loading."
            ],
            "demerits": [
                "Subject to Punjab Mandi Development Cess (3%) and statutory rural development fees."
            ],
            "recommendation_summary": "Top procurement hub for large commercial flour mills in Northern India."
        },
        {
            "rank": 3,
            "name": "Azadpur Terminal Mandi",
            "location": "Delhi",
            "source_type": "Govt Mandi",
            "unit_price": 2950.0,
            "badge": "Central APMC Terminal",
            "kpi_score": 85.0,
            "freshness": "Live Arrival (Today)",
            "merits": [
                "Instant local dispatch across Delhi-NCR; no long-distance interstate transit risk.",
                "Packaged in standard 50 kg jute and HDPE bags."
            ],
            "demerits": [
                "Highest unit price (₹2,950/Qtl) due to accumulated freight and trader margins."
            ],
            "recommendation_summary": "Suitable for small-batch emergency replenishment for local Delhi bakeries."
        },
        {
            "rank": 4,
            "name": "Lasalgaon Mandi",
            "location": "Lasalgaon, Maharashtra",
            "source_type": "Govt Mandi",
            "unit_price": 2800.0,
            "badge": "Western Mandi",
            "kpi_score": 79.0,
            "freshness": "Arrival (1 day old)",
            "merits": [
                "Good regional availability of Lokwan variety grains."
            ],
            "demerits": [
                "Higher moisture content if harvested during unseasonal showers."
            ],
            "recommendation_summary": "Recommended for Western Maharashtra grain aggregators."
        },
        {
            "rank": 5,
            "name": "Jaipur APMC Mandi",
            "location": "Jaipur, Rajasthan",
            "source_type": "Govt Mandi",
            "unit_price": 2820.0,
            "badge": "Regional Mandi (Stale Caveat)",
            "kpi_score": 67.0,
            "freshness": "STALE DATA (5 days old)",
            "merits": [
                "Direct road corridor to Haryana and Delhi."
            ],
            "demerits": [
                "Price record is 5 days old (stale); mandi auction rates have since shifted.",
                "Local handling charges of ₹30/Qtl apply."
            ],
            "recommendation_summary": "Verify live spot rates before executing orders."
        }
    ]
}


# -----------------------------------------------------------------------------
# 3. Dynamic Fallback Generator for any crop/hub
# -----------------------------------------------------------------------------
def generate_dynamic_fallback_analysis(
    commodity: str,
    quantity_quintals: float,
    delivery_address: str,
    distance_km: float,
    selected_truck: Dict[str, Any],
    ranked_options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Dynamically constructs a tailored top 5 merits and demerits comparison
    using deterministic figures from ranked_options and truck logistics.
    Used when Nebius Nemotron API call is unavailable.
    """
    clean_crop = commodity.strip().title()
    freight = selected_truck.get("freight_cost", 5600.0)
    eta = selected_truck.get("eta_hours", 6.5)
    handling_per_qtl = 25.0
    truck_name = selected_truck.get("truck_type", "Standard Commercial Vehicle")

    # If pre-computed catalog exists for this crop, use it as baseline
    if clean_crop in SAMPLE_TOP_5_ANALYSIS and len(SAMPLE_TOP_5_ANALYSIS[clean_crop]) >= 5:
        base_list = SAMPLE_TOP_5_ANALYSIS[clean_crop]
        results = []
        for i, item in enumerate(base_list[:5]):
            opt_data = dict(item)
            unit_p = opt_data.get("unit_price", 2400.0)

            # Map from live ranked options if present
            if i < len(ranked_options):
                ro = ranked_options[i]
                opt_data["name"] = ro.get("name", opt_data["name"])
                opt_data["unit_price"] = ro.get("unit_price", unit_p)
                unit_p = opt_data["unit_price"]
                opt_data["source_type"] = ro.get("source_type", opt_data["source_type"])
                if ro.get("is_stale"):
                    opt_data["badge"] = "STALE DATA (>2d)"
                    opt_data["freshness"] = "STALE DATA (>2d)"

            # Ensure all financial & logistics fields are strictly present
            landed = round((quantity_quintals * unit_p) + freight + (quantity_quintals * handling_per_qtl), 2)
            net_proceeds = round((quantity_quintals * unit_p) - freight - (quantity_quintals * handling_per_qtl), 2)

            opt_data["estimated_landed_cost"] = landed
            opt_data["estimated_net_proceeds"] = net_proceeds
            opt_data["eta_hours"] = eta
            opt_data["location"] = opt_data.get("location", delivery_address)
            results.append(opt_data)

        return results

    # Fallback for crops outside pre-computed list
    crop_info = CROPS_CATALOG.get(clean_crop, {
        "typical_price_range_inr": (2200.0, 3000.0),
        "major_production_hubs": ["Nashik (MH)", "Delhi (DL)", "Indore (MP)", "Jaipur (RJ)"]
    })
    base_price = (crop_info["typical_price_range_inr"][0] + crop_info["typical_price_range_inr"][1]) / 2.0

    hubs = [
        {"name": f"{clean_crop} Farmers Producer Co. Ltd. (Hub 1)", "type": "FPO Direct", "offset": -80.0, "is_stale": False, "kpi": 95.0, "badge": "Gold Verified FPO"},
        {"name": f"Azadpur Central Terminal Mandi", "type": "Govt Mandi", "offset": 120.0, "is_stale": False, "kpi": 85.0, "badge": "Central APMC Terminal"},
        {"name": f"Malwa Kisan Agro Producers", "type": "FPO Direct", "offset": -40.0, "is_stale": False, "kpi": 91.0, "badge": "Silver Trusted FPO"},
        {"name": f"Kolar APMC Mandi Hub", "type": "Govt Mandi", "offset": -150.0, "is_stale": False, "kpi": 80.0, "badge": "Southern APMC Hub"},
        {"name": f"Jaipur Regional Mandi", "type": "Govt Mandi", "offset": 50.0, "is_stale": True, "kpi": 66.0, "badge": "STALE DATA (5 days old)"},
    ]

    results = []
    for rank, hub in enumerate(hubs, start=1):
        unit_p = round(base_price + hub["offset"], 2)
        gross = round(quantity_quintals * unit_p, 2)
        landed = round(gross + freight + (quantity_quintals * handling_per_qtl), 2)
        net_proceeds = round(gross - freight - (quantity_quintals * handling_per_qtl), 2)

        if hub["type"] == "FPO Direct":
            merits = [
                f"Direct farmgate lot harvested recently; eliminates commission agent overhead.",
                f"Secured with digital escrow hold until destination moisture and QA inspection passes.",
                f"Uniform packaging with transparent lot tracing back to producer group.",
                f"Saves approximately ₹{abs(hub['offset']) * quantity_quintals:,.0f} compared to spot retail markets."
            ]
            demerits = [
                f"Requires transit planning with {truck_name} to guarantee timely delivery.",
                f"Strict 40+ quintal minimum lot volume for direct dispatch."
            ]
        else:
            merits = [
                f"High daily liquidity and immediate loading availability at the terminal.",
                f"Public APMC e-auction market pricing transparency."
            ]
            demerits = [
                f"Higher price margin per quintal due to intermediate handling charges.",
                f"Subject to local market cess and manual weighbridge queues."
            ]
            if hub["is_stale"]:
                demerits.append("⚠️ AGMARKNET price records are 5 days old and require telephone confirmation.")

        results.append({
            "rank": rank,
            "name": hub["name"],
            "location": delivery_address,
            "source_type": hub["type"],
            "unit_price": unit_p,
            "estimated_landed_cost": landed,
            "estimated_net_proceeds": net_proceeds,
            "eta_hours": eta,
            "badge": hub["badge"],
            "kpi_score": hub["kpi"],
            "freshness": "STALE DATA" if hub["is_stale"] else "Verified Fresh",
            "merits": merits,
            "demerits": demerits,
            "recommendation_summary": f"Rank #{rank} option for {clean_crop} delivery to {delivery_address}."
        })

    return results
