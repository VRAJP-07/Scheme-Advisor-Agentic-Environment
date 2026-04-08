"""
Scheme Advisor Environment — Schemes Knowledge Base

Contains structured data for 12 major Indian government welfare schemes
with deterministic eligibility rules and required documents.
"""

from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# Scheme Definitions
# ---------------------------------------------------------------------------

SCHEMES: Dict[str, Dict[str, Any]] = {

    "PM_KISAN": {
        "id": "PM_KISAN",
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
        "benefit": "₹6,000 per year direct income support to small/marginal farmers in 3 instalments",
        "eligibility_summary": "Small and marginal farmers owning up to 2 hectares of cultivable land",
        "required_documents": [
            "Aadhaar card",
            "Land ownership records (Khasra/Khatauni)",
            "Bank passbook",
            "Mobile number linked to Aadhaar",
        ],
        "eligibility_fn": lambda p: (
            p.get("occupation") == "farmer"
            and p.get("land_hectares", 0) <= 2
            and p.get("land_hectares", 0) > 0
            and not p.get("is_government_employee", False)
            and not p.get("is_income_taxpayer", False)
        ),
    },

    "AYUSHMAN_BHARAT": {
        "id": "AYUSHMAN_BHARAT",
        "name": "Ayushman Bharat – PM Jan Arogya Yojana (PMJAY)",
        "ministry": "Ministry of Health & Family Welfare",
        "benefit": "Health cover up to ₹5 lakh per family per year for secondary and tertiary care",
        "eligibility_summary": "Poor and vulnerable families as per SECC 2011 database; BPL category",
        "required_documents": [
            "Aadhaar card",
            "Ration card (BPL/Antyodaya)",
            "SECC-2011 inclusion proof or state government letter",
            "Mobile number",
        ],
        "eligibility_fn": lambda p: (
            p.get("bpl_card", False)
            and p.get("annual_income_inr", 999999) <= 200000
        ),
    },

    "PM_AWAS_YOJANA_GRAMIN": {
        "id": "PM_AWAS_YOJANA_GRAMIN",
        "name": "Pradhan Mantri Awas Yojana – Gramin (PMAY-G)",
        "ministry": "Ministry of Rural Development",
        "benefit": "Financial assistance of ₹1.2–1.3 lakh for construction of pucca house in rural areas",
        "eligibility_summary": "Houseless or kutcha/dilapidated house-dwelling families in rural India",
        "required_documents": [
            "Aadhaar card",
            "SECC-2011 data or BPL card",
            "Bank account details",
            "Land documents or NOC from Gram Panchayat",
            "Job Card (MGNREGS)",
        ],
        "eligibility_fn": lambda p: (
            p.get("location_type") == "rural"
            and (p.get("house_type") in ["kutcha", "none"])
            and p.get("annual_income_inr", 999999) <= 300000
        ),
    },

    "MGNREGS": {
        "id": "MGNREGS",
        "name": "Mahatma Gandhi National Rural Employment Guarantee Scheme (MGNREGS)",
        "ministry": "Ministry of Rural Development",
        "benefit": "Guaranteed 100 days of unskilled wage employment per household per year at minimum wage",
        "eligibility_summary": "Any adult member of a rural household willing to do unskilled manual work",
        "required_documents": [
            "Aadhaar card",
            "Residential proof (village panchayat certificate)",
            "Bank passbook or post office account",
            "Passport-size photograph",
        ],
        "eligibility_fn": lambda p: (
            p.get("location_type") == "rural"
            and p.get("age", 0) >= 18
        ),
    },

    "PM_UJJWALA": {
        "id": "PM_UJJWALA",
        "name": "Pradhan Mantri Ujjwala Yojana (PMUY)",
        "ministry": "Ministry of Petroleum & Natural Gas",
        "benefit": "Free LPG connection with first cylinder refill and stove for BPL women",
        "eligibility_summary": "Women above 18 years belonging to BPL households without existing LPG connection",
        "required_documents": [
            "Aadhaar card",
            "BPL ration card",
            "Bank account details",
            "Self-declaration of no existing LPG connection",
        ],
        "eligibility_fn": lambda p: (
            p.get("gender") == "female"
            and p.get("age", 0) >= 18
            and p.get("bpl_card", False)
            and not p.get("has_lpg_connection", True)
        ),
    },

    "SUKANYA_SAMRIDDHI": {
        "id": "SUKANYA_SAMRIDDHI",
        "name": "Sukanya Samriddhi Yojana (SSY)",
        "ministry": "Ministry of Finance",
        "benefit": "High-interest savings scheme (8.2% p.a.) for girl child with tax benefits; matures at age 21",
        "eligibility_summary": "Girl child below 10 years of age; account opened by parent/guardian",
        "required_documents": [
            "Birth certificate of girl child",
            "Aadhaar card of parent/guardian",
            "Residence proof",
            "Passport-size photograph of guardian",
        ],
        "eligibility_fn": lambda p: (
            p.get("has_girl_child_below_10", False)
        ),
    },

    "PM_MUDRA": {
        "id": "PM_MUDRA",
        "name": "Pradhan Mantri MUDRA Yojana (PMMY)",
        "ministry": "Ministry of Finance",
        "benefit": "Collateral-free loans up to ₹10 lakh for non-corporate, non-farm micro enterprises (Shishu/Kishore/Tarun)",
        "eligibility_summary": "Small entrepreneurs, shopkeepers, artisans, and self-employed individuals",
        "required_documents": [
            "Aadhaar card",
            "PAN card",
            "Business registration or self-declaration",
            "Bank statement (last 6 months)",
            "Business plan / loan application",
        ],
        "eligibility_fn": lambda p: (
            p.get("occupation") in ["self_employed", "small_business", "street_vendor"]
            and p.get("annual_income_inr", 0) <= 1000000
            and not p.get("is_income_taxpayer", False)
        ),
    },

    "SCHOLARSHIP_SC_ST": {
        "id": "SCHOLARSHIP_SC_ST",
        "name": "Pre/Post Matric Scholarship for SC/ST Students",
        "ministry": "Ministry of Social Justice & Empowerment / Tribal Affairs",
        "benefit": "Full tuition fee reimbursement + maintenance allowance for SC/ST students",
        "eligibility_summary": "Students belonging to SC/ST category enrolled in recognized educational institutions",
        "required_documents": [
            "Caste certificate (SC/ST)",
            "Aadhaar card",
            "Income certificate (family income below ₹2.5 lakh)",
            "Enrollment/bonafide certificate from institution",
            "Bank passbook",
            "Previous year marksheet",
        ],
        "eligibility_fn": lambda p: (
            p.get("caste_category") in ["SC", "ST"]
            and p.get("is_student", False)
            and p.get("annual_income_inr", 999999) <= 250000
        ),
    },

    "ATAL_PENSION": {
        "id": "ATAL_PENSION",
        "name": "Atal Pension Yojana (APY)",
        "ministry": "Ministry of Finance (PFRDA)",
        "benefit": "Guaranteed pension of ₹1,000–5,000/month after age 60 based on contribution",
        "eligibility_summary": "Indian citizens aged 18–40 years not covered by any statutory social security scheme",
        "required_documents": [
            "Aadhaar card",
            "Bank account linked to Aadhaar",
            "Mobile number",
        ],
        "eligibility_fn": lambda p: (
            18 <= p.get("age", 0) <= 40
            and not p.get("is_income_taxpayer", False)
            and not p.get("has_epf", False)
        ),
    },

    "E_SHRAM": {
        "id": "E_SHRAM",
        "name": "e-Shram Portal Registration (Unorganised Workers)",
        "ministry": "Ministry of Labour & Employment",
        "benefit": "₹2 lakh accident insurance (PMSBY), priority access to social security schemes, UAN card",
        "eligibility_summary": "Unorganised sector workers aged 16–59 not covered under EPFO/ESIC",
        "required_documents": [
            "Aadhaar card linked to mobile number",
            "Bank account details",
            "Occupation details",
        ],
        "eligibility_fn": lambda p: (
            16 <= p.get("age", 0) <= 59
            and p.get("sector") == "unorganised"
            and not p.get("has_epf", False)
        ),
    },

    "PM_SVANIDHI": {
        "id": "PM_SVANIDHI",
        "name": "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "ministry": "Ministry of Housing & Urban Affairs",
        "benefit": "Collateral-free working capital loan of ₹10,000 (extendable to ₹50,000) for street vendors",
        "eligibility_summary": "Street vendors who were vending before March 24, 2020 with vendor certificate / letter of recommendation",
        "required_documents": [
            "Aadhaar card",
            "Vendor certificate or LOC from Urban Local Body",
            "Bank account details",
            "Photograph",
        ],
        "eligibility_fn": lambda p: (
            p.get("occupation") == "street_vendor"
            and p.get("location_type") == "urban"
        ),
    },

    "NFBS": {
        "id": "NFBS",
        "name": "National Family Benefit Scheme (NFBS)",
        "ministry": "Ministry of Rural Development",
        "benefit": "One-time ₹20,000 assistance to BPL households on death of primary breadwinner (aged 18–59)",
        "eligibility_summary": "BPL families where primary breadwinner (18–59 years) has died",
        "required_documents": [
            "Death certificate of breadwinner",
            "Aadhaar card (deceased and applicant)",
            "BPL ration card",
            "Proof of relationship",
            "Bank passbook",
        ],
        "eligibility_fn": lambda p: (
            p.get("bpl_card", False)
            and p.get("breadwinner_died", False)
        ),
    },
}


# ---------------------------------------------------------------------------
# Task Definitions (Easy / Medium / Hard)
# ---------------------------------------------------------------------------

TASKS = {

    # ------------------------------------------------------------------
    # EASY — Single clear-cut scheme, minimal profile fields needed
    # ------------------------------------------------------------------
    "easy_farmer": {
        "task_id": "easy_farmer",
        "difficulty": "easy",
        "citizen_context": (
            "Ramesh is a 35-year-old male farmer from a village in Rajasthan. "
            "He owns 1.5 hectares of agricultural land. He is not a government employee, "
            "does not pay income tax, and has a bank account linked to Aadhaar. "
            "He works in the unorganised sector, has no EPF coverage, and is looking "
            "for government support schemes he may be eligible for."
        ),
        "ground_truth_profile": {
            "age": 35,
            "gender": "male",
            "location_type": "rural",
            "occupation": "farmer",
            "land_hectares": 1.5,
            "is_government_employee": False,
            "is_income_taxpayer": False,
            "bpl_card": False,
            "sector": "unorganised",
            "has_epf": False,
        },
        "ground_truth_eligible_schemes": ["PM_KISAN", "MGNREGS", "ATAL_PENSION", "E_SHRAM"],
        "ground_truth_documents": {
            "PM_KISAN": [
                "Aadhaar card",
                "Land ownership records (Khasra/Khatauni)",
                "Bank passbook",
                "Mobile number linked to Aadhaar",
            ],
            "MGNREGS": [
                "Aadhaar card",
                "Residential proof (village panchayat certificate)",
                "Bank passbook or post office account",
                "Passport-size photograph",
            ],
            "ATAL_PENSION": [
                "Aadhaar card",
                "Bank account linked to Aadhaar",
                "Mobile number",
            ],
            "E_SHRAM": [
                "Aadhaar card linked to mobile number",
                "Bank account details",
                "Occupation details",
            ],
        },
        "required_profile_fields": [
            "age", "gender", "location_type", "occupation",
            "land_hectares", "is_government_employee", "is_income_taxpayer",
            "has_epf", "sector"
        ],
    },

    # ------------------------------------------------------------------
    # MEDIUM — Multiple schemes, BPL, mixed eligibility
    # ------------------------------------------------------------------
    "medium_bpl_woman": {
        "task_id": "medium_bpl_woman",
        "difficulty": "medium",
        "citizen_context": (
            "Savitri is a 32-year-old woman living in a rural village in Uttar Pradesh. "
            "She belongs to a BPL household (annual family income ₹1,20,000). "
            "Her house is a kutcha structure. She does not have an LPG connection. "
            "She has a daughter aged 4. Her husband works as an unorganised daily-wage labourer (aged 35, no EPF). "
            "The family has no income tax liability."
        ),
        "ground_truth_profile": {
            "age": 32,
            "gender": "female",
            "location_type": "rural",
            "occupation": "homemaker",
            "bpl_card": True,
            "annual_income_inr": 120000,
            "house_type": "kutcha",
            "has_lpg_connection": False,
            "has_girl_child_below_10": True,
            "is_income_taxpayer": False,
            "sector": "unorganised",
            "has_epf": False,
        },
        "ground_truth_eligible_schemes": [
            "AYUSHMAN_BHARAT",
            "PM_AWAS_YOJANA_GRAMIN",
            "PM_UJJWALA",
            "SUKANYA_SAMRIDDHI",
            "E_SHRAM",
            "ATAL_PENSION",
            "MGNREGS",
        ],
        "ground_truth_documents": {
            "AYUSHMAN_BHARAT": [
                "Aadhaar card",
                "Ration card (BPL/Antyodaya)",
                "SECC-2011 inclusion proof or state government letter",
                "Mobile number",
            ],
            "PM_AWAS_YOJANA_GRAMIN": [
                "Aadhaar card",
                "SECC-2011 data or BPL card",
                "Bank account details",
                "Land documents or NOC from Gram Panchayat",
                "Job Card (MGNREGS)",
            ],
            "PM_UJJWALA": [
                "Aadhaar card",
                "BPL ration card",
                "Bank account details",
                "Self-declaration of no existing LPG connection",
            ],
            "SUKANYA_SAMRIDDHI": [
                "Birth certificate of girl child",
                "Aadhaar card of parent/guardian",
                "Residence proof",
                "Passport-size photograph of guardian",
            ],
            "E_SHRAM": [
                "Aadhaar card linked to mobile number",
                "Bank account details",
                "Occupation details",
            ],
            "ATAL_PENSION": [
                "Aadhaar card",
                "Bank account linked to Aadhaar",
                "Mobile number",
            ],
            "MGNREGS": [
                "Aadhaar card",
                "Residential proof (village panchayat certificate)",
                "Bank passbook or post office account",
                "Passport-size photograph",
            ],
        },
        "required_profile_fields": [
            "age", "gender", "location_type", "bpl_card",
            "annual_income_inr", "house_type", "has_lpg_connection",
            "has_girl_child_below_10", "is_income_taxpayer",
            "has_epf", "sector"
        ],
    },

    # ------------------------------------------------------------------
    # HARD — Complex overlapping eligibility, urban street vendor + ST student
    # ------------------------------------------------------------------
    "hard_urban_vendor_student": {
        "task_id": "hard_urban_vendor_student",
        "difficulty": "hard",
        "citizen_context": (
            "Mohan is a 38-year-old male ST (Scheduled Tribe) urban street vendor in Pune. "
            "He was vending before March 2020 and has a vendor certificate from the Municipal Corporation. "
            "His annual income is ₹1,80,000. He does not pay income tax, has no EPF, and works in the unorganised sector. "
            "He has a son aged 19 who is enrolled in a government engineering college (annual family income qualifies). "
            "Mohan's wife passed away recently — she was 34 and was the secondary earner. "
            "The family does not hold a BPL card. His house in the city is rented (not kutcha). "
            "He has a small side business selling snacks from a stall."
        ),
        "ground_truth_profile": {
            "age": 38,
            "gender": "male",
            "location_type": "urban",
            "occupation": "street_vendor",
            "sector": "unorganised",
            "caste_category": "ST",
            "annual_income_inr": 180000,
            "is_income_taxpayer": False,
            "has_epf": False,
            "bpl_card": False,
            "breadwinner_died": False,   # Mohan himself is alive; wife died but wasn't primary breadwinner
            "is_student": False,
            "has_girl_child_below_10": False,
            "house_type": "rented",
            "has_lpg_connection": True,
            # Son's attributes (separate sub-profile for scholarship)
            "son_is_student": True,
            "son_caste_category": "ST",
            "son_annual_family_income": 180000,
        },
        "ground_truth_eligible_schemes": [
            "PM_SVANIDHI",
            "PM_MUDRA",
            "E_SHRAM",
            "ATAL_PENSION",
        ],
        # Note: SCHOLARSHIP_SC_ST would be for son; agent must recognize son separately
        # NFBS: wife died but wasn't primary breadwinner and family is not BPL → not eligible
        # Agent is rewarded for correctly ruling out schemes and explaining why
        "ground_truth_documents": {
            "PM_SVANIDHI": [
                "Aadhaar card",
                "Vendor certificate or LOC from Urban Local Body",
                "Bank account details",
                "Photograph",
            ],
            "PM_MUDRA": [
                "Aadhaar card",
                "PAN card",
                "Business registration or self-declaration",
                "Bank statement (last 6 months)",
                "Business plan / loan application",
            ],
            "E_SHRAM": [
                "Aadhaar card linked to mobile number",
                "Bank account details",
                "Occupation details",
            ],
            "ATAL_PENSION": [
                "Aadhaar card",
                "Bank account linked to Aadhaar",
                "Mobile number",
            ],
        },
        "required_profile_fields": [
            "age", "gender", "location_type", "occupation",
            "sector", "caste_category", "annual_income_inr",
            "is_income_taxpayer", "has_epf", "bpl_card",
            "breadwinner_died", "house_type",
        ],
    },
}


def check_eligibility(scheme_id: str, profile: dict) -> bool:
    """Run the deterministic eligibility function for a scheme."""
    scheme = SCHEMES.get(scheme_id)
    if not scheme:
        return False
    try:
        return bool(scheme["eligibility_fn"](profile))
    except Exception:
        return False


def get_eligible_schemes(profile: dict) -> List[str]:
    """Return IDs of all schemes the profile is eligible for."""
    return [sid for sid in SCHEMES if check_eligibility(sid, profile)]


def get_all_scheme_ids() -> List[str]:
    return list(SCHEMES.keys())


def get_all_task_ids() -> List[str]:
    return list(TASKS.keys())
