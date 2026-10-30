"""
app.py
======
Unified Frontend: NVIDIA × Nebius Hackathon
Autonomous FPO Produce Marketplace & Mandi Decision Platform

Features:
  1. Visual Crop Catalog: Clean, visual browsing of all agricultural crops.
  2. 3-Step Buyer Journey: Crop Selection -> Destination Hub & Volume -> Fleet Delivery Option.
  3. Natural Language Intent Bar: Users can simply type what they need to trigger instant AI suggestions.
  4. NVIDIA Nemotron Top 5 Merits & Demerits: Rigorous pros/cons analysis for top 5 places via Nebius API with rich sample data fallback.
  5. Other Listings & Mandis: Clean, uncluttered layout showing other verified FPO lots and AGMARKNET arrivals.
  6. Escrow Checkout & Tracking: Razorpay escrow funds lock, instant PDF invoice download, and 4-stage GPS tracker.
  7. FPO Seller Portal & Interactive AI Copilot.
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

import streamlit as st
import pandas as pd

from sample_data import CROPS_CATALOG, SAMPLE_TOP_5_ANALYSIS
from data_loader import (
    fetch_mandi_prices,
    get_fpo_listings,
    add_fpo_listing,
)
from calculator import (
    calculate_truck_options,
    calculate_seller_kpi,
    rank_market_and_fpo_options,
    get_shipment_tracking,
    BUYER_LANDED_COST_FORMULA_STRING,
    FINANCIAL_FORMULA_STRING,
    FINANCIAL_DISCLAIMER,
)
from agent import (
    generate_top_5_merits_demerits,
    parse_natural_language_intent,
    chat_with_nemotron,
    NEMOTRON_MODEL,
)
from payment_escrow import (
    create_escrow_payment,
    generate_invoice_pdf,
    ESCROW_RELEASE_CONDITION,
)

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Modern Aesthetics
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AgriNemotron | FPO Marketplace & Mandi Decision Engine",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Polished modern CSS for visual hierarchy and uncluttered design
st.markdown(
    """
    <style>
    /* Main container and font */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hero section */
    .hero-container {
        background: linear-gradient(135deg, #064E3B 0%, #047857 50%, #059669 100%);
        border-radius: 16px;
        padding: 28px 32px;
        color: #FFFFFF;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(6, 78, 59, 0.25);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        opacity: 0.92;
        max-width: 820px;
        line-height: 1.5;
        margin-bottom: 14px;
    }
    .tech-pill {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.35);
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 6px;
    }

    /* Step Headers */
    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #047857;
        color: #FFFFFF;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        font-weight: 700;
        font-size: 0.9rem;
        margin-right: 10px;
    }
    .step-heading {
        display: flex;
        align-items: center;
        font-size: 1.35rem;
        font-weight: 700;
        color: #111827;
        margin-top: 14px;
        margin-bottom: 12px;
    }

    /* Crop Selection Cards */
    .crop-card {
        border: 2px solid #E5E7EB;
        border-radius: 14px;
        padding: 14px;
        text-align: center;
        background: #FFFFFF;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
        min-height: 190px;
    }
    .crop-card:hover {
        border-color: #059669;
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .crop-card-selected {
        border: 2px solid #059669 !important;
        background: #ECFDF5 !important;
        box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.2);
    }

    /* Merits & Demerits Cards */
    .top-card {
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        background: #FFFFFF;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .top-card-rank-1 {
        border: 2px solid #F59E0B;
        background: #FFFDF9;
        box-shadow: 0 8px 20px -4px rgba(245, 158, 11, 0.18);
    }
    .merit-box {
        background-color: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 12px 14px;
        border-radius: 8px;
        height: 100%;
    }
    .demerit-box {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 12px 14px;
        border-radius: 8px;
        height: 100%;
    }

    /* Badges */
    .channel-fpo {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 3px 10px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .channel-mandi {
        background-color: #EEF2FF;
        color: #4338CA;
        padding: 3px 10px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .stale-pill {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .fresh-pill {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "selected_crop" not in st.session_state:
    st.session_state["selected_crop"] = "Tomato"

if "quantity_quintals" not in st.session_state:
    st.session_state["quantity_quintals"] = 50.0

if "delivery_address" not in st.session_state:
    st.session_state["delivery_address"] = "Azadpur Wholesale Mandi Hub, Delhi"

if "distance_km" not in st.session_state:
    st.session_state["distance_km"] = 250.0

if "selected_truck_type" not in st.session_state:
    st.session_state["selected_truck_type"] = "Standard LCV (Eicher 14ft - up to 60 Qtl)"

if "payment_status" not in st.session_state:
    st.session_state["payment_status"] = None

if "invoice_pdf_bytes" not in st.session_state:
    st.session_state["invoice_pdf_bytes"] = None

if "selected_checkout_item" not in st.session_state:
    st.session_state["selected_checkout_item"] = None

if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                "👋 **Welcome to AgriNemotron!** I am your Agricultural Decision Copilot powered by NVIDIA Nemotron via Nebius.\n\n"
                "I analyze live Mandi benchmark arrivals, direct FPO lots, and freight logistics to calculate "
                "deterministic **estimated net proceeds** and **buyer landed costs**.\n\n"
                "Try asking me:\n"
                "- *'Compare Sahyadri FPO vs Azadpur Mandi for 50 quintals of tomatoes'* \n"
                "- *'Why is the Jaipur Mandi price record flagged as stale?'*\n"
                "- *'What are the advantages of choosing a Reefer Cold-Chain truck over an open LCV?'*"
            )
        }
    ]


# -----------------------------------------------------------------------------
# Header & Intent Search Box
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">🌾 AgriNemotron Market Decision Engine</div>
        <div class="hero-subtitle">
            Autonomous agricultural intelligence powered by <b>NVIDIA Nemotron</b> via <b>Nebius Token Factory</b>.
            Browse verified farmgate lots, compare open Mandi price bands, evaluate fleet road freight,
            and purchase securely with Razorpay escrow protection.
        </div>
        <div>
            <span class="tech-pill">⚡ NVIDIA Nemotron-70B</span>
            <span class="tech-pill">🌐 Nebius Token Factory</span>
            <span class="tech-pill">🏛️ OGD AGMARKNET Mandi API</span>
            <span class="tech-pill">🔒 Razorpay Escrow Protection</span>
            <span class="tech-pill">📄 In-Memory PDF Invoicing</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Global Natural Language Intent Bar
with st.container(border=True):
    st.markdown("##### 💬 What produce are you looking to procure? (Or select step-by-step below)")
    nl_col1, nl_col2 = st.columns([4, 1])
    with nl_col1:
        user_query_input = st.text_input(
            "Natural Language Intent Input",
            placeholder="e.g., 'I want 50 quintals of fresh grade A tomatoes delivered to Azadpur Delhi with minimal spoilage'",
            label_visibility="collapsed"
        )
    with nl_col2:
        search_clicked = st.button("🚀 Analyze Intent", use_container_width=True, type="primary")

    # One-click quick query chips
    chip_cols = st.columns(4)
    with chip_cols[0]:
        if st.button("🍅 50 Qtl Tomatoes to Delhi", use_container_width=True):
            user_query_input = "50 quintals of tomatoes delivered to Azadpur Delhi"
            search_clicked = True
    with chip_cols[1]:
        if st.button("🧅 100 Qtl Onions to Mumbai", use_container_width=True):
            user_query_input = "100 quintals of onions delivered to Mumbai Vashi"
            search_clicked = True
    with chip_cols[2]:
        if st.button("🥔 80 Qtl Potatoes to Jaipur", use_container_width=True):
            user_query_input = "80 quintals of potatoes delivered to Jaipur"
            search_clicked = True
    with chip_cols[3]:
        if st.button("🌾 150 Qtl Wheat to Bangalore", use_container_width=True):
            user_query_input = "150 quintals of wheat delivered to Bangalore Kolar"
            search_clicked = True

    if search_clicked and user_query_input:
        parsed = parse_natural_language_intent(user_query_input)
        if parsed.get("commodity"):
            st.session_state["selected_crop"] = parsed["commodity"]
        if parsed.get("quantity_quintals"):
            st.session_state["quantity_quintals"] = parsed["quantity_quintals"]
        if parsed.get("delivery_address"):
            st.session_state["delivery_address"] = parsed["delivery_address"]
        if parsed.get("truck_preference"):
            st.session_state["selected_truck_type"] = parsed["truck_preference"]
        st.success(
            f"🎯 Understood! Updated parameters for **{st.session_state['selected_crop']}** "
            f"({st.session_state['quantity_quintals']} Qtl) to **{st.session_state['delivery_address']}**."
        )


# -----------------------------------------------------------------------------
# Main Application Tabs
# -----------------------------------------------------------------------------
tab_browse, tab_checkout, tab_seller, tab_chat = st.tabs([
    "🛒 1. Browse, Compare & AI Recommendations",
    "💳 2. Escrow Checkout, PDF Invoice & GPS Tracker",
    "🌾 3. FPO Seller Portal (List Harvest)",
    "🤖 4. Ask NVIDIA Nemotron AI"
])


# =============================================================================
# TAB 1: 🛒 Browse, Compare & AI Recommendations
# =============================================================================
with tab_browse:
    # -------------------------------------------------------------------------
    # STEP 1: Select Agricultural Crop
    # -------------------------------------------------------------------------
    st.markdown(
        '<div class="step-heading"><span class="step-badge">1</span>Select Agricultural Crop to Procure</div>',
        unsafe_allow_html=True
    )

    available_crops = list(CROPS_CATALOG.keys())
    crop_cols = st.columns(len(available_crops))

    for idx, c_name in enumerate(available_crops):
        c_info = CROPS_CATALOG[c_name]
        is_selected = (st.session_state["selected_crop"] == c_name)

        with crop_cols[idx]:
            with st.container(border=True):
                # Thumbnail image
                st.image(c_info["image_url"], use_container_width=True)
                st.markdown(f"### {c_info['icon']} {c_name}")
                st.caption(f"*{c_info['scientific_name']}*")
                st.markdown(
                    f"**₹{c_info['typical_price_range_inr'][0]:,.0f} - ₹{c_info['typical_price_range_inr'][1]:,.0f}** / Qtl"
                )
                st.caption(f"⏳ Shelf Life: {c_info['shelf_life_days']}")

                btn_label = "✅ Selected" if is_selected else f"Select {c_name}"
                btn_type = "primary" if is_selected else "secondary"
                if st.button(btn_label, key=f"btn_crop_{c_name}", use_container_width=True, type=btn_type):
                    st.session_state["selected_crop"] = c_name
                    st.rerun()

    # Active crop confirmation badge
    current_crop = st.session_state["selected_crop"]
    curr_info = CROPS_CATALOG.get(current_crop, CROPS_CATALOG["Tomato"])
    st.info(
        f"Selected **{current_crop}** ({curr_info['scientific_name']}) — "
        f"{curr_info['tagline']}. Major Hubs: {', '.join(curr_info['major_production_hubs'])}."
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # STEP 2: Choose Delivery Destination & Lot Volume
    # -------------------------------------------------------------------------
    st.markdown(
        '<div class="step-heading"><span class="step-badge">2</span>Choose Delivery Destination & Payload Volume</div>',
        unsafe_allow_html=True
    )

    col_dest1, col_dest2, col_dest3 = st.columns([1.5, 1, 1])

    with col_dest1:
        st.markdown("**Delivery Destination Terminal Hub**")
        hub_shortcuts = [
            "Azadpur Wholesale Mandi Hub, Delhi",
            "Vashi APMC Wholesale Market, Mumbai",
            "Kolar APMC Market, Bangalore",
            "Jaipur Central Wholesale Mandi, Rajasthan",
            "Indore Malwa Agro Terminal, MP",
        ]

        preset_idx = 0
        if st.session_state["delivery_address"] in hub_shortcuts:
            preset_idx = hub_shortcuts.index(st.session_state["delivery_address"])

        selected_hub = st.selectbox(
            "Select from major wholesale hubs:",
            hub_shortcuts,
            index=preset_idx,
            label_visibility="collapsed"
        )
        st.session_state["delivery_address"] = selected_hub

    with col_dest2:
        st.markdown("**Procurement Volume (Quintals)**")
        qty_val = st.number_input(
            "Volume (Quintals)",
            min_value=5.0,
            max_value=2000.0,
            value=float(st.session_state["quantity_quintals"]),
            step=10.0,
            label_visibility="collapsed"
        )
        st.session_state["quantity_quintals"] = qty_val
        st.caption("1 Quintal = 100 Kilograms")

    with col_dest3:
        st.markdown("**Estimated Road Distance (km)**")
        dist_val = st.slider(
            "Distance km",
            min_value=10,
            max_value=2500,
            value=int(st.session_state["distance_km"]),
            step=10,
            label_visibility="collapsed"
        )
        st.session_state["distance_km"] = float(dist_val)
        st.caption(f"Transit corridor distance: {dist_val} km")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # STEP 3: Select Transport / Delivery Fleet Option
    # -------------------------------------------------------------------------
    st.markdown(
        '<div class="step-heading"><span class="step-badge">3</span>Select Commercial Delivery Fleet</div>',
        unsafe_allow_html=True
    )

    # Compute live vehicle options
    fleet_options = calculate_truck_options(
        distance_km=st.session_state["distance_km"],
        quantity_quintals=st.session_state["quantity_quintals"]
    )

    fleet_cols = st.columns(len(fleet_options))
    selected_truck_dict = fleet_options[1]  # Default: Standard LCV

    for idx, opt in enumerate(fleet_options):
        is_chosen = (st.session_state["selected_truck_type"] == opt["truck_type"])
        if is_chosen:
            selected_truck_dict = opt

        with fleet_cols[idx]:
            with st.container(border=True):
                if "Mini" in opt["truck_type"]:
                    icon = "🛻"
                elif "Standard" in opt["truck_type"]:
                    icon = "🚚"
                else:
                    icon = "❄️"

                st.markdown(f"#### {icon} {opt['truck_type'].split('(')[0].strip()}")
                st.caption(f"Payload capacity: up to **{opt['capacity_quintals']:,.0f} Qtl**")

                st.markdown(f"### ₹{opt['freight_cost']:,.0f}")
                st.caption(f"₹{opt['rate_per_km']}/km • {opt['trucks_needed']} Vehicle(s) required")

                st.write(f"⏱️ **Transit ETA**: {opt['eta_hours']} hrs (incl. buffer)")
                st.write(f"🛡️ **Spoilage Risk**: {opt['spoilage_risk']}")

                btn_label = "✅ Selected Fleet" if is_chosen else "Choose Vehicle"
                btn_type = "primary" if is_chosen else "secondary"
                if st.button(btn_label, key=f"btn_truck_{idx}", use_container_width=True, type=btn_type):
                    st.session_state["selected_truck_type"] = opt["truck_type"]
                    st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # TOP 5 MERITS & DEMERITS COMPARISON BOARD (NVIDIA Nemotron + Fallback Data)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="font-size: 1.5rem; font-weight: 800; color: #111827;">
                🏆 NVIDIA Nemotron AI: Top 5 Places — Merits & Demerits Analysis
            </div>
            <div>
                <span class="channel-fpo">Verified FPO Lots</span>
                <span class="channel-mandi">AGMARKNET Mandis</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption(
        f"Evaluating optimal procurement places for **{st.session_state['quantity_quintals']} Qtl** of "
        f"**{st.session_state['selected_crop']}** delivered to **{st.session_state['delivery_address']}** "
        f"via **{selected_truck_dict['truck_type']}**."
    )

    # Fetch live data and deterministic rankings
    mandi_records_res = fetch_mandi_prices(commodity=st.session_state["selected_crop"])
    fpo_listings_res = get_fpo_listings(commodity=st.session_state["selected_crop"])

    ranking_res = rank_market_and_fpo_options(
        quantity_quintals=st.session_state["quantity_quintals"],
        mandi_records=mandi_records_res["records"],
        fpo_listings=fpo_listings_res,
        delivery_address=st.session_state["delivery_address"],
        distance_km=st.session_state["distance_km"],
        selected_truck_type=selected_truck_dict["truck_type"],
        other_costs_per_quintal=25.0
    )

    # Call Nemotron API (with automatic rich sample data fallback)
    with st.spinner("NVIDIA Nemotron is analyzing prices, logistics freight, merits & demerits..."):
        top_5_analysis = generate_top_5_merits_demerits(
            commodity=st.session_state["selected_crop"],
            quantity_quintals=st.session_state["quantity_quintals"],
            delivery_address=st.session_state["delivery_address"],
            distance_km=st.session_state["distance_km"],
            selected_truck=selected_truck_dict,
            ranked_options=ranking_res.get("ranked_options", [])
        )

    # Render each of the top 5 places in a beautiful structured card
    for place in top_5_analysis:
        rank_num = place.get("rank", 1)
        is_rank_1 = (rank_num == 1)
        card_class = "top-card top-card-rank-1" if is_rank_1 else "top-card"

        source_type = place.get("source_type", "FPO Direct")
        channel_badge = (
            '<span class="channel-fpo">🌿 FPO Direct Farmgate</span>'
            if source_type == "FPO Direct"
            else '<span class="channel-mandi">🏛️ Govt Mandi Terminal</span>'
        )

        freshness_label = place.get("freshness", "Verified Fresh")
        freshness_badge = (
            '<span class="stale-pill">⚠️ STALE DATA (>2 Days)</span>'
            if "STALE" in str(freshness_label).upper()
            else f'<span class="fresh-pill">🌱 {freshness_label}</span>'
        )

        with st.container(border=True):
            # Top Banner inside card
            head_c1, head_c2 = st.columns([3, 1])
            with head_c1:
                rank_prefix = "👑 #1 TOP RECOMMENDATION" if is_rank_1 else f"#{rank_num} OPTION"
                st.markdown(f"### {rank_prefix}: {place['name']}")
                st.caption(f"📍 Location: **{place.get('location', 'India')}** | Channel: {channel_badge} {freshness_badge}", unsafe_allow_html=True)
            with head_c2:
                st.metric(
                    label="Est. Buyer Landed Cost",
                    value=f"₹{place.get('estimated_landed_cost', 0.0):,.0f}",
                    delta=f"Unit: ₹{place.get('unit_price', 0.0):,.2f}/Qtl"
                )

            # Two-Column Merits and Demerits
            m_col, d_col = st.columns(2)
            with m_col:
                st.markdown(
                    """
                    <div class="merit-box">
                        <b style="color: #047857;">✅ Key Merits (Why to Buy Here):</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                for merit in place.get("merits", []):
                    st.markdown(f"• {merit}")

            with d_col:
                st.markdown(
                    """
                    <div class="demerit-box">
                        <b style="color: #B45309;">⚠️ Key Demerits & Trade-Offs (Risks):</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                for demerit in place.get("demerits", []):
                    st.markdown(f"• {demerit}")

            # Recommendation summary + Direct Escrow Checkout Button
            st.markdown("---")
            foot_c1, foot_c2 = st.columns([3, 1])
            with foot_c1:
                st.markdown(f"**🎯 Nemotron Verdict**: *{place.get('recommendation_summary', '')}*")
                st.caption(f"Transit ETA: ~{place.get('eta_hours', selected_truck_dict['eta_hours'])} hrs | Quality KPI: {place.get('kpi_score', 90)}/100")
            with foot_c2:
                if st.button("🛒 Buy via Escrow", key=f"btn_escrow_top_{rank_num}", use_container_width=True, type="primary" if is_rank_1 else "secondary"):
                    st.session_state["selected_checkout_item"] = {
                        "seller_name": place["name"],
                        "origin_location": place.get("location", "India"),
                        "commodity": st.session_state["selected_crop"],
                        "variety": "Standard / High Dry Matter",
                        "grade": "Grade A",
                        "quantity_quintals": st.session_state["quantity_quintals"],
                        "unit_price": place.get("unit_price", 2400.0),
                        "transport_cost": selected_truck_dict["freight_cost"],
                        "other_costs": st.session_state["quantity_quintals"] * 25.0,
                        "total_amount_inr": place.get("estimated_landed_cost", 0.0),
                        "truck_type": selected_truck_dict["truck_type"],
                        "eta_hours": selected_truck_dict["eta_hours"],
                    }
                    st.session_state["payment_status"] = None
                    st.session_state["invoice_pdf_bytes"] = None
                    st.success(f"Selected {place['name']}! Switch to Tab 2 to finalize Escrow Payment.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # OTHER LISTINGS UNDER ALL THIS (FPO Direct Lots + Mandi Records)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div class="step-heading">
            <span class="step-badge">📦</span>Other Produce Listings & Regional Mandi Records
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption("Browse all additional verified FPO producer inventory and official Government AGMARKNET price bands.")

    tab_other_fpo, tab_other_mandi = st.tabs(["🌾 All Verified FPO Lots", "🏛️ AGMARKNET Mandi Price Bands"])

    with tab_other_fpo:
        all_fpos = get_fpo_listings(commodity=st.session_state["selected_crop"])
        if all_fpos:
            fpo_grid_cols = st.columns(3)
            for idx, fpo in enumerate(all_fpos):
                with fpo_grid_cols[idx % 3]:
                    with st.container(border=True):
                        st.image(
                            fpo.get("photo_url") or curr_info["image_url"],
                            use_container_width=True
                        )
                        st.markdown(f"**{fpo['fpo_name']}**")
                        st.caption(f"📍 {fpo['origin_location']} | ID: `{fpo['listing_id']}`")
                        st.write(f"**Variety**: {fpo['variety']} | **Grade**: {fpo['grade']}")
                        st.write(f"**Freshness**: {fpo['freshness_tag']} ({fpo['age_days']}d old)")
                        st.markdown(f"### ₹{fpo['asking_price_per_quintal']:,.2f} / Qtl")
                        st.caption(f"Available Stock: {fpo['quantity_quintals']:,.0f} Qtl")

                        if st.button("🛒 Select Lot", key=f"btn_lot_{fpo['listing_id']}", use_container_width=True):
                            st.session_state["selected_checkout_item"] = {
                                "seller_name": fpo["fpo_name"],
                                "origin_location": fpo["origin_location"],
                                "commodity": fpo["commodity"],
                                "variety": fpo["variety"],
                                "grade": fpo["grade"],
                                "quantity_quintals": st.session_state["quantity_quintals"],
                                "unit_price": fpo["asking_price_per_quintal"],
                                "transport_cost": selected_truck_dict["freight_cost"],
                                "other_costs": st.session_state["quantity_quintals"] * 25.0,
                                "total_amount_inr": (st.session_state["quantity_quintals"] * fpo["asking_price_per_quintal"]) + selected_truck_dict["freight_cost"] + (st.session_state["quantity_quintals"] * 25.0),
                                "truck_type": selected_truck_dict["truck_type"],
                                "eta_hours": selected_truck_dict["eta_hours"],
                            }
                            st.session_state["payment_status"] = None
                            st.session_state["invoice_pdf_bytes"] = None
                            st.success(f"Selected {fpo['fpo_name']}! Switch to Tab 2 for checkout.")
        else:
            st.info(f"No direct FPO listings currently found for {st.session_state['selected_crop']}.")

    with tab_other_mandi:
        if mandi_records_res.get("has_stale_data"):
            st.warning(mandi_records_res.get("stale_warning_msg"))

        mandi_df = mandi_records_res.get("dataframe")
        if mandi_df is not None and not mandi_df.empty:
            st.dataframe(
                mandi_df[[
                    "mandi", "state", "commodity", "variety", "grade",
                    "min_price", "max_price", "modal_price", "arrival_date",
                    "days_old", "is_stale", "source"
                ]],
                use_container_width=True,
                column_config={
                    "modal_price": st.column_config.NumberColumn("Modal (₹/Qtl)", format="₹%.2f"),
                    "min_price": st.column_config.NumberColumn("Min (₹/Qtl)", format="₹%.2f"),
                    "max_price": st.column_config.NumberColumn("Max (₹/Qtl)", format="₹%.2f"),
                    "is_stale": st.column_config.CheckboxColumn("Stale Data?"),
                }
            )
        else:
            st.info("No government mandi price records returned.")


# =============================================================================
# TAB 2: 💳 Escrow Checkout, PDF Invoice & GPS Tracker
# =============================================================================
with tab_checkout:
    st.subheader("💳 Escrow Payment, PDF Invoice & Real-Time Tracking")

    item = st.session_state.get("selected_checkout_item")
    if not item:
        # Default to first ranked item
        item = {
            "seller_name": "Sahyadri Farmers Producer Co. Ltd.",
            "origin_location": "Nashik, Maharashtra",
            "commodity": st.session_state["selected_crop"],
            "variety": "Hybrid Shivam / Abhinav",
            "grade": "Grade A",
            "quantity_quintals": st.session_state["quantity_quintals"],
            "unit_price": 2350.0,
            "transport_cost": selected_truck_dict["freight_cost"],
            "other_costs": st.session_state["quantity_quintals"] * 25.0,
            "total_amount_inr": (st.session_state["quantity_quintals"] * 2350.0) + selected_truck_dict["freight_cost"] + (st.session_state["quantity_quintals"] * 25.0),
            "truck_type": selected_truck_dict["truck_type"],
            "eta_hours": selected_truck_dict["eta_hours"],
        }

    # Order Details Card
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="background-color: #ECFDF5; border-left: 4px solid #059669; padding: 12px 16px; border-radius: 8px; margin-bottom: 14px;">
                <b>Consignment Locked for Escrow:</b> {item['seller_name']} ({item['origin_location']})<br>
                <b>Produce:</b> {item['commodity']} ({item['variety']} - {item['grade']}) | 
                <b>Payload:</b> {item['quantity_quintals']:,.1f} Quintals to {st.session_state['delivery_address']}
            </div>
            """,
            unsafe_allow_html=True
        )

        base_cost = round(item["quantity_quintals"] * item["unit_price"], 2)
        freight_cost = round(item["transport_cost"], 2)
        handling_cost = round(item["other_costs"], 2)
        total_payable = round(base_cost + freight_cost + handling_cost, 2)

        c_sum1, c_sum2 = st.columns([2, 1])
        with c_sum1:
            st.markdown("#### 🧾 Landed Cost Breakdown")
            st.write(f"• Base Farmgate Value ({item['quantity_quintals']} Qtl @ ₹{item['unit_price']:,.2f}/Qtl): **₹{base_cost:,.2f}**")
            st.write(f"• Dedicated Road Freight ({item['truck_type']}): **₹{freight_cost:,.2f}**")
            st.write(f"• Mandi Platform Cess & Weighbridge Fees: **₹{handling_cost:,.2f}**")
            st.markdown(f"### **Total Amount to Lock in Escrow: ₹{total_payable:,.2f}**")

        with c_sum2:
            st.markdown("#### 🔒 Razorpay Escrow")
            st.caption(
                "Funds are securely locked in escrow. Payment is disbursed to the FPO only "
                "after arrival inspection and digital manifest sign-off."
            )

            pay_btn = st.button(
                f"🔒 Pay & Lock ₹{total_payable:,.2f}",
                type="primary",
                use_container_width=True
            )

            if pay_btn:
                order_payload = {
                    "buyer_name": "AgroSuper FreshMart Delhi",
                    "delivery_address": st.session_state["delivery_address"],
                    "seller_name": item["seller_name"],
                    "origin_location": item["origin_location"],
                    "commodity": item["commodity"],
                    "variety": item["variety"],
                    "grade": item["grade"],
                    "freshness_tag": "Harvest Fresh (<2 days)",
                    "quantity_quintals": item["quantity_quintals"],
                    "unit_price": item["unit_price"],
                    "transport_cost": freight_cost,
                    "other_costs": handling_cost,
                    "total_amount_inr": total_payable,
                    "truck_type": item["truck_type"],
                    "eta_hours": item["eta_hours"],
                }

                with st.spinner("Authorizing Razorpay Smart Escrow Order..."):
                    payment_res = create_escrow_payment(order_payload)
                    pdf_bytes = generate_invoice_pdf(order_payload, payment_res)

                    st.session_state["payment_status"] = payment_res
                    st.session_state["invoice_pdf_bytes"] = pdf_bytes
                    st.session_state["last_order_details"] = order_payload

                st.success("✅ Payment Authorized! Funds successfully locked in Escrow.")

    # Render Invoice & Live GPS Tracker if paid
    if st.session_state.get("payment_status"):
        p_stat = st.session_state["payment_status"]
        last_ord = st.session_state.get("last_order_details", item)

        st.markdown("---")
        st.markdown("### 📄 Escrow Tax Invoice & Receipt")

        col_inv1, col_inv2 = st.columns([2, 1])
        with col_inv1:
            st.markdown(
                f"""
                **Razorpay Order ID**: `{p_stat['order_id']}` | **Payment ID**: `{p_stat['payment_id']}`<br>
                **Escrow Status**: `{p_stat['escrow_status']}` | **Mode**: `{p_stat['razorpay_mode']}`<br>
                **Release Condition**: *{p_stat['release_condition']}*
                """,
                unsafe_allow_html=True
            )
        with col_inv2:
            if st.session_state.get("invoice_pdf_bytes"):
                st.download_button(
                    label="📄 Download Official Escrow PDF Invoice",
                    data=st.session_state["invoice_pdf_bytes"],
                    file_name=f"Escrow_Invoice_{p_stat['order_id']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # 4-Stage GPS Shipment Milestone Tracker
        st.markdown("---")
        st.markdown("### 🛰️ Live Consignment Tracking & Cold-Chain Telemetry")

        tracking_data = get_shipment_tracking(
            order_id=p_stat["order_id"],
            origin=last_ord.get("origin_location", "Origin Hub"),
            destination=st.session_state["delivery_address"],
            eta_hours=selected_truck_dict["eta_hours"]
        )

        # Milestone Progress Stepper
        st_cols = st.columns(len(tracking_data["stages"]))
        for idx, stage_name in enumerate(tracking_data["stages"]):
            with st_cols[idx]:
                if idx < tracking_data["current_stage_index"]:
                    st.markdown(f"✅ **Step {idx + 1}**\n\n*{stage_name}*")
                elif idx == tracking_data["current_stage_index"]:
                    st.markdown(f"🔵 **Step {idx + 1} (ACTIVE)**\n\n**{stage_name}**")
                else:
                    st.markdown(f"⚪ **Step {idx + 1}**\n\n*{stage_name}*")

        # Telemetry metrics
        telem = tracking_data.get("telemetry", {})
        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1:
            st.metric("GPS Transponder", telem.get("gps_status", "Active"))
        with tc2:
            st.metric("Cargo Temp", f"{telem.get('cargo_temp_celsius', 4.5)} °C")
        with tc3:
            st.metric("Vehicle Speed", f"{telem.get('speed_kmh', 45.0)} km/h")
        with tc4:
            st.metric("Estimated Arrival", tracking_data.get("estimated_arrival"))

        with st.expander("📍 View Detailed Checkpoint Logs", expanded=True):
            for cp in tracking_data.get("checkpoints", []):
                st.markdown(f"• **[{cp['timestamp']}]** `{cp['stage_name']}` at *{cp['location']}* — {cp['notes']}")


# =============================================================================
# TAB 3: 🌾 FPO Seller Portal (List Harvest)
# =============================================================================
with tab_seller:
    st.subheader("🌾 List New Produce Lot (Farmer Producer Organization Portal)")
    st.markdown(
        "Directly connect farmer producer collectives to institutional buyers, "
        "eliminating intermediate broker commissions."
    )

    with st.form("form_fpo_publish_lot", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_name = st.text_input("FPO Producer Group Name:", value="Nashik Krishi Vikas FPO")
            f_commodity = st.selectbox("Crop Commodity:", available_crops, index=0)
            f_variety = st.text_input("Variety / Cultivar:", value="Hybrid Shivam")
            f_grade = st.selectbox("Produce Grade:", ["Grade A", "Grade B", "FAQ (Fair Average Quality)"], index=0)
            f_harvest = st.date_input("Harvest Date:", value=date.today(), max_value=date.today())

        with col_f2:
            f_qty = st.number_input("Lot Volume (Quintals):", min_value=5.0, max_value=5000.0, value=150.0, step=10.0)
            f_price = st.number_input("Asking Price (₹ per Quintal):", min_value=100.0, max_value=20000.0, value=2350.0, step=50.0)
            f_origin = st.text_input("Origin Location (City, State):", value="Nashik, Maharashtra")
            f_photo = st.text_input("Produce Photo URL (leave empty for auto photo):", value="")
            f_orders = st.number_input("Completed Past Orders:", min_value=0, value=52)

        publish_btn = st.form_submit_button("🚀 Publish Lot to Marketplace", use_container_width=True)

        if publish_btn:
            default_photo = CROPS_CATALOG.get(f_commodity, CROPS_CATALOG["Tomato"])["image_url"]
            final_photo = f_photo.strip() or default_photo

            new_record = {
                "fpo_name": f_name,
                "commodity": f_commodity,
                "variety": f_variety,
                "grade": f_grade,
                "harvest_date": f_harvest.strftime("%Y-%m-%d"),
                "quantity_quintals": f_qty,
                "asking_price_per_quintal": f_price,
                "origin_location": f_origin,
                "origin_distance_km_map": {"Azadpur (Delhi)": 1280, "Vashi (Mumbai)": 165},
                "photo_url": final_photo,
                "completed_orders": int(f_orders),
                "on_time_rate": 0.97,
                "quality_rating": 4.8
            }

            saved_item = add_fpo_listing(new_record)
            st.success(
                f"✅ Produce Lot successfully listed as **{saved_item['listing_id']}**! "
                f"Freshness calculated as **{saved_item['freshness_tag']}** ({saved_item['age_days']} day(s) old). "
                f"It is now live in the marketplace."
            )
            st.rerun()


# =============================================================================
# TAB 4: 🤖 Ask NVIDIA Nemotron AI
# =============================================================================
with tab_chat:
    st.subheader("🤖 NVIDIA Nemotron Agricultural Decision Copilot")
    st.caption(f"Powered by `{NEMOTRON_MODEL}` via Nebius Token Factory with strict deterministic groundings.")

    # Quick Prompt Chips
    with st.expander("💡 Quick Prompt Suggestions", expanded=False):
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if st.button("Lowest landed cost breakdown?"):
                st.session_state["quick_chat_prompt"] = f"Which option provides the lowest buyer landed cost for {st.session_state['quantity_quintals']} quintals of {st.session_state['selected_crop']} delivered to {st.session_state['delivery_address']}?"
        with qc2:
            if st.button("Why is data flagged as stale?"):
                st.session_state["quick_chat_prompt"] = f"Explain the staleness warning on {st.session_state['selected_crop']} mandi prices and why Jaipur is 5 days old."
        with qc3:
            if st.button("Reefer cold-chain trade-off?"):
                st.session_state["quick_chat_prompt"] = f"Compare freight costs and spoilage risk between Standard LCV and Reefer Cold-Chain for {st.session_state['selected_crop']}."

    # Render previous messages
    for m in st.session_state["chat_messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Handle quick chat prompt injection
    active_prompt = None
    if "quick_chat_prompt" in st.session_state and st.session_state["quick_chat_prompt"]:
        active_prompt = st.session_state.pop("quick_chat_prompt")

    user_chat = st.chat_input("Ask Nemotron about mandi prices, net proceeds, or logistics...")
    if user_chat:
        active_prompt = user_chat

    if active_prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": active_prompt})
        with st.chat_message("user"):
            st.markdown(active_prompt)

        # Build live context
        live_context = {
            "commodity": st.session_state["selected_crop"],
            "quantity_quintals": st.session_state["quantity_quintals"],
            "delivery_address": st.session_state["delivery_address"],
            "distance_km": st.session_state["distance_km"],
            "selected_truck": selected_truck_dict,
            "top_5_analysis": top_5_analysis,
            "stale_warning_msg": mandi_records_res.get("stale_warning_msg", ""),
            "has_stale_data": mandi_records_res.get("has_stale_data", False)
        }

        with st.chat_message("assistant"):
            with st.spinner("NVIDIA Nemotron is analyzing market options..."):
                reply = chat_with_nemotron(
                    user_message=active_prompt,
                    chat_history=st.session_state["chat_messages"][:-1],
                    current_context=live_context
                )
                st.markdown(reply)

        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
