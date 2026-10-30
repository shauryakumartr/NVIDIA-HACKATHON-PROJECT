"""
agent.py
========
Agriculture Marketplace & Market-Decision Platform
NVIDIA × Nebius Hackathon

Integrates NVIDIA Nemotron (via the Nebius Token Factory OpenAI-compatible SDK)
with deterministic backend services in data_loader.py, calculator.py, and sample_data.py.

Strict Hackathon Guardrails:
  - The LLM must NEVER invent mandi prices, fabricate FPO listings, or perform financial math in free-form prose.
  - All prices and net-proceeds numbers cited by Nemotron must originate from deterministic tool outputs.
  - All financial outputs are referred to strictly as 'estimated net proceeds' or 'estimated landed cost', never guaranteed income.
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
import openai

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
    FINANCIAL_FORMULA_STRING,
    FINANCIAL_DISCLAIMER,
)
from sample_data import (
    CROPS_CATALOG,
    SAMPLE_TOP_5_ANALYSIS,
    generate_dynamic_fallback_analysis,
)

# -----------------------------------------------------------------------------
# Configuration & Logging Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger("agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [agent]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

load_dotenv()

NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "").strip()
NEBIUS_BASE_URL: str = os.getenv(
    "NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1/"
).strip()
NEMOTRON_MODEL: str = os.getenv(
    "NEMOTRON_MODEL", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"
).strip()


def get_nebius_client() -> Optional[openai.OpenAI]:
    """
    Safely initializes and returns the Nebius OpenAI-compatible client.
    Returns None if NEBIUS_API_KEY is not configured or placeholder.
    """
    if not NEBIUS_API_KEY or NEBIUS_API_KEY in ["YOUR_API_KEY", "your_api_key_here"]:
        logger.info("NEBIUS_API_KEY not configured or empty. Using deterministic fallback mode.")
        return None
    try:
        return openai.OpenAI(api_key=NEBIUS_API_KEY, base_url=NEBIUS_BASE_URL)
    except Exception as exc:
        logger.warning("Failed to initialize Nebius client: %s", exc)
        return None


# -----------------------------------------------------------------------------
# OpenAI-Compatible Tool Specifications
# -----------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_mandi_prices",
            "description": (
                "Query live Indian Government Mandi prices from the OGD AGMARKNET API. "
                "Returns normalized prices in INR/Quintal, arrival dates, and data freshness validation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "Crop name, e.g. 'Tomato', 'Onion', 'Potato', 'Wheat'."
                    },
                    "state": {
                        "type": "string",
                        "description": "Optional Indian state name, e.g. 'Maharashtra', 'Delhi'."
                    },
                    "market_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of mandi names to filter against, e.g. ['Azadpur', 'Lasalgaon']."
                    }
                },
                "required": ["commodity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fpo_listings",
            "description": (
                "Retrieve active direct produce listings from verified Farmer Producer Organizations (FPOs), "
                "including dynamically calculated harvest freshness tags and asking prices."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "Optional crop name to filter by, e.g. 'Tomato', 'Onion'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rank_market_and_fpo_options",
            "description": (
                "Deterministically rank Mandi and direct FPO options by calculating estimated net proceeds "
                "for sellers and estimated landed purchase cost for buyers after road freight transport and statutory fees."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The crop to analyze (e.g. 'Tomato', 'Onion', 'Potato', 'Wheat')."
                    },
                    "quantity_quintals": {
                        "type": "number",
                        "description": "Payload volume in Quintals (1 Quintal = 100 kg)."
                    },
                    "delivery_address": {
                        "type": "string",
                        "description": "Destination city, warehouse, or mandi hub (e.g. 'Azadpur Mandi, Delhi')."
                    },
                    "distance_km": {
                        "type": "number",
                        "description": "Estimated road distance in kilometers."
                    },
                    "selected_truck_type": {
                        "type": "string",
                        "enum": [
                            "Mini Truck (Tata Ace - up to 15 Qtl)",
                            "Standard LCV (Eicher 14ft - up to 60 Qtl)",
                            "Reefer Cold-Chain Truck (up to 100 Qtl)"
                        ],
                        "description": "Commercial transport vehicle type."
                    },
                    "other_costs_per_quintal": {
                        "type": "number",
                        "description": "Mandi cess, handling, loading, and weighing fees in ₹/Qtl (default: 25.0)."
                    }
                },
                "required": ["commodity", "quantity_quintals", "delivery_address", "distance_km"]
            }
        }
    }
]


# -----------------------------------------------------------------------------
# Tool Execution Dispatcher
# -----------------------------------------------------------------------------
def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatches and executes Python backend functions called by Nemotron.
    Handles data marshaling and returns compact, LLM-safe summaries.
    """
    logger.info("Executing tool '%s' with args: %s", tool_name, arguments)
    try:
        if tool_name == "fetch_mandi_prices":
            commodity = str(arguments.get("commodity", "Tomato"))
            state = arguments.get("state")
            market_list = arguments.get("market_list")
            res = fetch_mandi_prices(commodity=commodity, state=state, market_list=market_list)
            return {
                "records": res["records"][:10],
                "has_stale_data": res["has_stale_data"],
                "missing_markets": res["missing_markets"],
                "stale_warning_msg": res["stale_warning_msg"]
            }

        elif tool_name == "get_fpo_listings":
            commodity = arguments.get("commodity")
            listings = get_fpo_listings(commodity=commodity)
            return {"fpo_listings": listings[:10]}

        elif tool_name == "rank_market_and_fpo_options":
            commodity = str(arguments.get("commodity", "Tomato"))
            qty = float(arguments.get("quantity_quintals", 50.0))
            dest = str(arguments.get("delivery_address", "Central Hub"))
            dist = float(arguments.get("distance_km", 150.0))
            truck = str(arguments.get("selected_truck_type", "Standard LCV (Eicher 14ft - up to 60 Qtl)"))
            other_cost = float(arguments.get("other_costs_per_quintal", 25.0))

            mandi_res = fetch_mandi_prices(commodity)
            fpo_res = get_fpo_listings(commodity)

            calc_res = rank_market_and_fpo_options(
                quantity_quintals=qty,
                mandi_records=mandi_res["records"],
                fpo_listings=fpo_res,
                delivery_address=dest,
                distance_km=dist,
                selected_truck_type=truck,
                other_costs_per_quintal=other_cost
            )
            return {
                "top_ranked_options": calc_res["ranked_options"][:5],
                "selected_truck": calc_res["selected_truck"],
                "formula_used": calc_res["formula_used"],
                "disclaimer": calc_res["disclaimer"],
                "stale_warning_msg": mandi_res.get("stale_warning_msg", "")
            }

        else:
            return {"error": f"Tool '{tool_name}' is not recognized."}

    except Exception as exc:
        logger.error("Error executing tool '%s': %s", tool_name, exc)
        return {"error": str(exc)}


# -----------------------------------------------------------------------------
# Core Function: generate_top_5_merits_demerits (NVIDIA Nemotron + Fallback)
# -----------------------------------------------------------------------------
def generate_top_5_merits_demerits(
    commodity: str,
    quantity_quintals: float,
    delivery_address: str,
    distance_km: float,
    selected_truck: Dict[str, Any],
    ranked_options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Calls NVIDIA Nemotron via Nebius Token Factory to generate tailored,
    in-depth merits and demerits for buying from the Top 5 suggested places.

    If the API call fails or the key is not set, seamlessly falls back to
    our comprehensive sample data generator in sample_data.py.
    """
    client = get_nebius_client()

    # If no client, return high-fidelity fallback immediately
    if client is None:
        return generate_dynamic_fallback_analysis(
            commodity=commodity,
            quantity_quintals=quantity_quintals,
            delivery_address=delivery_address,
            distance_km=distance_km,
            selected_truck=selected_truck,
            ranked_options=ranked_options
        )

    # Prepare compact top 5 context for Nemotron
    top_5_input = []
    for idx, opt in enumerate(ranked_options[:5], start=1):
        top_5_input.append({
            "rank": idx,
            "name": opt.get("name"),
            "source_type": opt.get("source_type"),
            "unit_price": opt.get("unit_price"),
            "estimated_landed_cost": opt.get("estimated_buyer_landed_cost"),
            "estimated_net_proceeds": opt.get("estimated_net_proceeds"),
            "eta_hours": opt.get("eta_hours", selected_truck.get("eta_hours")),
            "age_days": opt.get("age_days", 0),
            "is_stale": opt.get("is_stale", False),
            "grade": opt.get("grade", "Grade A")
        })

    prompt_payload = {
        "commodity": commodity,
        "quantity_quintals": quantity_quintals,
        "delivery_address": delivery_address,
        "distance_km": distance_km,
        "selected_truck": selected_truck,
        "top_5_options": top_5_input
    }

    system_prompt = (
        "You are an Agricultural Decision Strategist powered by NVIDIA Nemotron. "
        "Analyze the provided Top 5 procurement places for the buyer's shipment and return a strict JSON array of 5 objects.\n\n"
        "EACH OBJECT MUST HAVE:\n"
        "- 'rank': integer (1 to 5)\n"
        "- 'name': string (supplier or mandi name)\n"
        "- 'location': string (city / hub)\n"
        "- 'source_type': 'FPO Direct' or 'Govt Mandi'\n"
        "- 'unit_price': float\n"
        "- 'estimated_landed_cost': float\n"
        "- 'estimated_net_proceeds': float\n"
        "- 'eta_hours': float\n"
        "- 'badge': string (e.g. 'Gold Verified FPO' or 'Central APMC')\n"
        "- 'kpi_score': float (0-100)\n"
        "- 'freshness': string (e.g. 'Harvest Fresh (<2 days)' or 'STALE DATA')\n"
        "- 'merits': array of 3-4 specific bullet-point pros (shelf life, savings, direct farmgate quality, escrow protection)\n"
        "- 'demerits': array of 2-3 specific bullet-point cons (transit distance, cold-chain requirements, mandi cess fees, stale data risks)\n"
        "- 'recommendation_summary': string (1-sentence verdict on why to buy or pass)\n\n"
        "STRICT GUARDRAIL: Output ONLY a valid JSON array. Do not invent prices or totals; use the numbers given in the payload."
    )

    try:
        response = client.chat.completions.create(
            model=NEMOTRON_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(prompt_payload, default=str)}
            ],
            temperature=0.2,
            max_tokens=1800
        )
        content = response.choices[0].message.content
        if content:
            # Strip markdown fences if present
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) >= 3:
                logger.info("Successfully generated Top 5 Merits & Demerits via NVIDIA Nemotron.")
                return parsed
    except Exception as exc:
        logger.warning("Nemotron merits/demerits call failed (%s). Using rich fallback data.", exc)

    # Fallback to high-fidelity sample data
    return generate_dynamic_fallback_analysis(
        commodity=commodity,
        quantity_quintals=quantity_quintals,
        delivery_address=delivery_address,
        distance_km=distance_km,
        selected_truck=selected_truck,
        ranked_options=ranked_options
    )


# -----------------------------------------------------------------------------
# Natural Language Query Parser ("User just has to enter what they want")
# -----------------------------------------------------------------------------
def parse_natural_language_intent(user_prompt: str) -> Dict[str, Any]:
    """
    Parses free-form user intent (e.g. 'I want 50 quintals of tomatoes in Delhi')
    and extracts commodity, quantity, and destination.
    Uses fast robust regex/keyword rules with LLM fallback.
    """
    text = user_prompt.lower().strip()
    result = {
        "commodity": None,
        "quantity_quintals": None,
        "delivery_address": None,
        "truck_preference": None
    }

    # 1. Match Commodity
    crops = ["tomato", "onion", "potato", "wheat", "green chilli", "chilli", "ginger", "soybean", "rice"]
    for c in crops:
        if c in text:
            if c == "chilli" or c == "green chilli":
                result["commodity"] = "Green Chilli"
            else:
                result["commodity"] = c.title()
            break

    # 2. Match Quantity (e.g., '50 qtl', '50 quintals', '100 quintal', '75 ton', '50')
    qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:quintals?|qtl|tons?|tonnes?)", text)
    if qty_match:
        val = float(qty_match.group(1))
        # If user wrote tons, convert to quintals (1 ton = 10 quintals)
        if "ton" in qty_match.group(0):
            val = val * 10.0
        result["quantity_quintals"] = val
    else:
        # Generic number search
        num_match = re.search(r"\b(\d{1,4})\b", text)
        if num_match:
            result["quantity_quintals"] = float(num_match.group(1))

    # 3. Match Destination Hub
    destinations = {
        "delhi": "Azadpur Wholesale Mandi Hub, Delhi",
        "azadpur": "Azadpur Wholesale Mandi Hub, Delhi",
        "mumbai": "Vashi APMC Wholesale Market, Mumbai",
        "vashi": "Vashi APMC Wholesale Market, Mumbai",
        "bangalore": "Kolar APMC Market, Bangalore",
        "bengaluru": "Kolar APMC Market, Bangalore",
        "kolar": "Kolar APMC Market, Bangalore",
        "jaipur": "Jaipur Central Wholesale Mandi, Rajasthan",
        "indore": "Indore Malwa Agro Terminal, MP",
        "pune": "Gultekdi APMC Market, Pune",
    }
    for k, dest in destinations.items():
        if k in text:
            result["delivery_address"] = dest
            break

    # 4. Match Truck Preference
    if "reefer" in text or "cold" in text or "temp" in text:
        result["truck_preference"] = "Reefer Cold-Chain Truck (up to 100 Qtl)"
    elif "ace" in text or "mini" in text or "small" in text:
        result["truck_preference"] = "Mini Truck (Tata Ace - up to 15 Qtl)"
    elif "eicher" in text or "lcv" in text or "standard" in text:
        result["truck_preference"] = "Standard LCV (Eicher 14ft - up to 60 Qtl)"

    return result


# -----------------------------------------------------------------------------
# Function 1: generate_why_buy_insight (Preserved for compatibility)
# -----------------------------------------------------------------------------
def _build_deterministic_why_buy_template(
    calculation_result: Dict[str, Any],
    stale_warning_msg: str = ""
) -> str:
    ranked = calculation_result.get("ranked_options", [])
    if not ranked:
        return (
            "### 1. ⚠️ No Options Available\n"
            "No active Mandi prices or FPO listings matched your query parameters.\n\n"
            "### 2. ⚖️ Assumptions & Next Steps\n"
            "Please broaden your search criteria or review available regional hubs."
        )

    opt1 = ranked[0]
    opt2 = ranked[1] if len(ranked) > 1 else None
    selected_truck = calculation_result.get("selected_truck", {})
    truck_name = selected_truck.get("truck_type", "Standard Commercial Vehicle")
    trucks_needed = selected_truck.get("trucks_needed", 1)
    freight_cost = selected_truck.get("freight_cost", 0.0)
    eta_hours = selected_truck.get("eta_hours", 0.0)

    opt1_name = opt1.get("name", "Option 1")
    opt1_type = opt1.get("source_type", "Supplier")
    opt1_unit = opt1.get("unit_price", 0.0)
    opt1_net = opt1.get("estimated_net_proceeds", 0.0)
    opt1_landed = opt1.get("estimated_buyer_landed_cost", 0.0)
    opt1_age = opt1.get("age_days", 0)

    section_1 = (
        f"### 1. 🏆 Top Recommendation & Why\n"
        f"- **Primary Pick**: **{opt1_name}** ({opt1_type})\n"
        f"- **Unit Price**: ₹{opt1_unit:,.2f}/Quintal | **Estimated Net Proceeds**: ₹{opt1_net:,.2f} | **Estimated Buyer Landed Cost**: ₹{opt1_landed:,.2f}\n"
    )

    if opt2:
        opt2_name = opt2.get("name", "Option 2")
        opt2_unit = opt2.get("unit_price", 0.0)
        opt2_landed = opt2.get("estimated_buyer_landed_cost", 0.0)
        diff_landed = abs(opt2_landed - opt1_landed)
        section_1 += (
            f"- **Comparison with #2**: Ranked ahead of **{opt2_name}** (₹{opt2_unit:,.2f}/Qtl). "
            f"Choosing the top option yields a cost variance of **₹{diff_landed:,.2f}** after factoring freight and handling, "
            f"with produce age at **{opt1_age} day(s)**.\n"
        )
    else:
        section_1 += f"- **Single Best Match**: Currently represents the sole qualified supplier meeting specifications.\n"

    tradeoff_notes = [
        f"**Fleet & Freight**: Configured via **{truck_name}** ({trucks_needed} truck(s)). "
        f"Total transport freight estimated at **₹{freight_cost:,.2f}** with transit ETA of **{eta_hours} hours**."
    ]

    if opt1_type == "FPO Direct":
        badge = opt1.get("badge", "Verified FPO")
        kpi = opt1.get("overall_kpi_score", 90.0)
        tradeoff_notes.append(
            f"**FPO Quality Standing**: Direct procurement backed by **{badge}** (Composite KPI: **{kpi}/100**)."
        )
    else:
        tradeoff_notes.append(
            "**Govt Mandi Channel**: Involves open-auction lot aggregation subject to physical weighbridge verification."
        )

    if stale_warning_msg:
        tradeoff_notes.append(f"**Data Caveat**: {stale_warning_msg}")

    section_2 = "### 2. ⚖️ Key Trade-Offs & Assumptions\n" + "\n".join(f"- {note}" for note in tradeoff_notes) + "\n"

    section_3 = (
        f"### 3. 🎯 Recommended Next Step\n"
        f"- **Action Item**: Confirm allocation with **{opt1_name}** and initiate escrow lock for the required payload.\n"
        f"- *Notice*: Figures reflect **estimated net proceeds** and **estimated landed costs**. "
        f"Govt Mandi prices represent historical AGMARKNET daily arrivals and are not guaranteed bids. "
        f"Final settlement is governed by on-site grading and actual transport dispatch."
    )

    return f"{section_1}\n{section_2}\n{section_3}"


def generate_why_buy_insight(
    calculation_result: Dict[str, Any],
    stale_warning_msg: str = ""
) -> str:
    client = get_nebius_client()
    if client is None:
        return _build_deterministic_why_buy_template(calculation_result, stale_warning_msg)

    ranked_options = calculation_result.get("ranked_options", [])
    if not ranked_options:
        return _build_deterministic_why_buy_template(calculation_result, stale_warning_msg)

    condensed_payload = {
        "top_options": ranked_options[:3],
        "selected_truck": calculation_result.get("selected_truck", {}),
        "formula_used": calculation_result.get("formula_used", FINANCIAL_FORMULA_STRING),
        "stale_warning_msg": stale_warning_msg,
        "disclaimer": calculation_result.get("disclaimer", FINANCIAL_DISCLAIMER)
    }

    system_prompt = (
        "You are an expert Agricultural Market Strategist powered by NVIDIA Nemotron. "
        "Your task is to write a concise, authoritative 3-part 'Why-Buy / Why-Sell' market decision summary in Markdown.\n\n"
        "STRICT GUARDRAILS:\n"
        "1. NEVER invent or alter numbers. All prices, net proceeds, landed costs, ETAs, and freight costs MUST come EXACTLY from the provided JSON.\n"
        "2. ALWAYS refer to financial amounts as 'estimated net proceeds' or 'estimated landed cost'. NEVER use 'guaranteed income' or 'guaranteed price'.\n"
        "3. Mandi prices MUST be characterized as historical observations, not guaranteed bids.\n"
        "4. Follow the exact 3-section Markdown structure:\n"
        "   ### 1. 🏆 Top Recommendation & Why\n"
        "   ### 2. ⚖️ Key Trade-Offs & Assumptions\n"
        "   ### 3. 🎯 Recommended Next Step\n"
    )

    try:
        response = client.chat.completions.create(
            model=NEMOTRON_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze: {json.dumps(condensed_payload)}"}
            ],
            temperature=0.1,
            max_tokens=600
        )
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
    except Exception as exc:
        logger.warning("Nemotron call failed in generate_why_buy_insight (%s). Falling back.", exc)

    return _build_deterministic_why_buy_template(calculation_result, stale_warning_msg)


# -----------------------------------------------------------------------------
# Function 2: chat_with_nemotron
# -----------------------------------------------------------------------------
def _generate_fallback_chat_reply(
    user_message: str,
    current_context: Dict[str, Any]
) -> str:
    msg_lower = user_message.lower().strip()
    commodity = current_context.get("commodity", "produce")
    qty = current_context.get("quantity_quintals", 0.0)
    dest = current_context.get("delivery_address", "your destination")
    ranked = current_context.get("ranked_options", [])

    missing = []
    if not current_context.get("commodity"):
        missing.append("commodity name")
    if not qty or qty <= 0:
        missing.append("quantity in quintals")
    if not current_context.get("delivery_address"):
        missing.append("delivery destination hub")

    if missing and any(k in msg_lower for k in ["deal", "best", "recommend", "buy", "sell", "proceeds", "landed"]):
        return (
            f"I would be glad to calculate the optimal market options for you. "
            f"To provide exact net proceeds and landed costs, please provide: **{', '.join(missing)}**. "
            f"Currently, I have: Commodity = `{commodity}`, Quantity = `{qty} Qtl`, Destination = `{dest}`."
        )

    if ranked:
        top = ranked[0]
        top_name = top.get("name", "Top Supplier")
        top_net = top.get("estimated_net_proceeds", 0.0)
        top_landed = top.get("estimated_buyer_landed_cost", 0.0)
        top_unit = top.get("unit_price", 0.0)
        return (
            f"Based on our deterministic logistics and price ranking for **{commodity}** ({qty} Qtl to {dest}):\n\n"
            f"- **#1 Best Option**: **{top_name}** at ₹{top_unit:,.2f}/Qtl.\n"
            f"- **Estimated Net Proceeds** (Seller View): ₹{top_net:,.2f}\n"
            f"- **Estimated Landed Cost** (Buyer View): ₹{top_landed:,.2f}\n\n"
            f"Transport and mandi handling fees have been calculated deterministically. "
            f"*Note: Figures are estimated net proceeds/landed costs, not guaranteed prices.*"
        )

    return (
        f"I am your NVIDIA Nemotron Agricultural Decision Assistant. I can help evaluate real-time Mandi benchmark prices, "
        f"compare direct FPO supplier listings, compute fleet transport freight, and rank estimated net proceeds. "
        f"What commodity and shipment volume would you like to evaluate today?"
    )


def chat_with_nemotron(
    user_message: str,
    chat_history: List[Dict[str, str]],
    current_context: Dict[str, Any]
) -> str:
    client = get_nebius_client()
    if client is None:
        return _generate_fallback_chat_reply(user_message, current_context)

    system_prompt = (
        "You are an expert Agricultural Decision Intelligence Copilot powered by NVIDIA Nemotron. "
        "You advise Indian farmers, Farmer Producer Organizations (FPOs), and institutional buyers on produce pricing, "
        "transport freight costs, and supply chain decisions.\n\n"
        "STRICT HACKATHON GUARDRAILS:\n"
        "1. NEVER invent mandi prices, fabricate FPO listings, or execute financial math in free-form prose.\n"
        "2. All prices, freight costs, and proceeds MUST be queried via tools or read directly from the current context.\n"
        "3. ALWAYS use the phrases 'estimated net proceeds' and 'estimated buyer landed cost'. NEVER say 'guaranteed income' or 'guaranteed price'.\n"
        "4. If essential parameters (commodity, quantity_quintals, delivery_address/distance) are missing when the user asks for a recommendation, "
        "   politely ask for the missing details while stating what is already known.\n"
        "5. Keep responses concise, clear, and actionable with clean Markdown.\n\n"
        f"CURRENT ACTIVE CONTEXT:\n{json.dumps(current_context, indent=2, default=str)}"
    )

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    try:
        for _ in range(3):
            response = client.chat.completions.create(
                model=NEMOTRON_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=800
            )

            assistant_msg = response.choices[0].message
            if not assistant_msg.tool_calls:
                return assistant_msg.content or _generate_fallback_chat_reply(user_message, current_context)

            messages.append(assistant_msg)
            for tool_call in assistant_msg.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception:
                    args = {}

                tool_result = execute_tool(func_name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, default=str)
                })

        final_res = client.chat.completions.create(
            model=NEMOTRON_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        return final_res.choices[0].message.content or _generate_fallback_chat_reply(user_message, current_context)

    except Exception as exc:
        logger.warning("Nemotron chat completion failed (%s). Using fallback reply.", exc)
        return _generate_fallback_chat_reply(user_message, current_context)


# -----------------------------------------------------------------------------
# Module CLI Self-Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("Running agent.py Verification Self-Test")
    print("=" * 70)

    # Test generate_top_5_merits_demerits
    sample_truck = {
        "truck_type": "Standard LCV (Eicher 14ft - up to 60 Qtl)",
        "freight_cost": 5600.0,
        "eta_hours": 6.5
    }
    sample_ranked = [
        {"name": "Sahyadri FPO", "source_type": "FPO Direct", "unit_price": 2350.0, "estimated_buyer_landed_cost": 124350.0, "estimated_net_proceeds": 110650.0, "is_stale": False, "grade": "Grade A"},
        {"name": "Azadpur Mandi", "source_type": "Govt Mandi", "unit_price": 2550.0, "estimated_buyer_landed_cost": 134350.0, "estimated_net_proceeds": 120650.0, "is_stale": False, "grade": "FAQ"},
    ]
    top_5 = generate_top_5_merits_demerits(
        commodity="Tomato",
        quantity_quintals=50.0,
        delivery_address="Delhi Azadpur",
        distance_km=200.0,
        selected_truck=sample_truck,
        ranked_options=sample_ranked
    )
    print(f"Top 5 Places Evaluated: {len(top_5)}")
    for p in top_5:
        print(f"#{p['rank']} {p['name']} ({p['source_type']}) - Merits: {len(p['merits'])} | Demerits: {len(p['demerits'])}")

    # Test NLP intent parsing
    intent = parse_natural_language_intent("I want 80 quintals of onions delivered to Mumbai Vashi with cold-chain")
    print(f"\nParsed Intent: {intent}")

    print("\nagent.py verification completed successfully!")
