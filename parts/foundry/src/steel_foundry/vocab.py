"""Curated vocabulary and template libraries for the Borealis dataset.

Everything here is static data: category taxonomy, supplier name parts, contract clause
templates, news templates, policy documents, and seller personas. The generator threads a
single seeded ``random.Random`` through these libraries — the libraries themselves never
draw randomness.
"""

from __future__ import annotations

from typing import get_args

from steel_manifest import Role

# ── Category taxonomy (UNSPSC-flavored): (name, sku_code, item_nouns) ───────────────────
CATEGORIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Bearings & Bushings", "BRG",
     ("Ball Bearing", "Roller Bearing", "Bushing", "Pillow Block")),
    ("Fasteners & Hardware", "FST",
     ("Hex Bolt", "Lock Nut", "Flat Washer", "Threaded Rod")),
    ("Hydraulic Components", "HYD",
     ("Hydraulic Cylinder", "Hose Assembly", "Gear Pump", "Manifold")),
    ("Pneumatic Components", "PNU",
     ("Air Cylinder", "Solenoid Valve", "FRL Unit", "Quick Coupler")),
    ("Electric Motors", "MOT",
     ("AC Motor", "Servo Motor", "Gearmotor", "Stepper Motor")),
    ("Industrial Pumps", "PMP",
     ("Centrifugal Pump", "Diaphragm Pump", "Dosing Pump", "Vane Pump")),
    ("Valves & Actuators", "VLV",
     ("Ball Valve", "Butterfly Valve", "Globe Valve", "Rotary Actuator")),
    ("Sheet Metal & Stampings", "SHM",
     ("Bracket", "Enclosure Panel", "Stamped Cover", "Chassis Plate")),
    ("Castings & Forgings", "CST",
     ("Sand Casting", "Die Casting", "Forged Flange", "Impeller Blank")),
    ("Machined Components", "MCH",
     ("Turned Shaft", "Milled Housing", "Precision Spacer", "Adapter Plate")),
    ("Steel & Raw Metals", "STL",
     ("Steel Coil", "Steel Plate", "Bar Stock", "Structural Beam")),
    ("Aluminum Extrusions", "ALX",
     ("T-Slot Profile", "Heat Sink Extrusion", "Angle Profile", "Tube Profile")),
    ("Plastics & Polymers", "PLS",
     ("Resin Pellets", "Polymer Sheet", "Molded Housing", "Extruded Tube")),
    ("Adhesives & Sealants", "ADH",
     ("Epoxy Adhesive", "Thread Sealant", "Silicone Sealant", "Retaining Compound")),
    ("Lubricants & Coolants", "LUB",
     ("Gear Oil", "Cutting Fluid", "Synthetic Grease", "Coolant Concentrate")),
    ("Electrical Components", "ELC",
     ("Contactor", "Circuit Breaker", "Terminal Block", "Relay Module")),
    ("Wire & Cable", "WIR",
     ("Control Cable", "Power Cable", "Hook-Up Wire", "Shielded Pair")),
    ("PCB Assemblies", "PCB",
     ("Controller Board", "Driver Board", "Sensor Board", "Backplane")),
    ("Sensors & Instrumentation", "SNS",
     ("Proximity Sensor", "Pressure Transducer", "Flow Meter", "Encoder")),
    ("Packaging Materials", "PKG",
     ("Corrugated Carton", "Stretch Film", "Foam Insert", "Strapping Coil")),
    ("Pallets & Crating", "PLT",
     ("Wood Pallet", "Plastic Pallet", "Export Crate", "Pallet Collar")),
    ("Safety Equipment & PPE", "SAF",
     ("Safety Glasses", "Cut-Resistant Glove", "Hard Hat", "Respirator")),
    ("Janitorial & Facilities", "JAN",
     ("Floor Cleaner", "Absorbent Pad", "Waste Liner", "Hand Soap")),
    ("MRO Tools & Consumables", "MRO",
     ("Carbide End Mill", "Grinding Wheel", "Torque Wrench", "Abrasive Disc")),
    ("Logistics & Freight", "LOG",
     ("FTL Lane", "LTL Shipment", "Ocean Container", "Air Freight Block")),
    ("Contract Manufacturing", "CMF",
     ("Weldment Assembly", "Machining Lot", "Coating Service", "Kitting Service")),
    ("Engineering Services", "ENG",
     ("CAD Package", "FEA Study", "Process Audit", "Tooling Design")),
    ("IT Hardware", "ITH",
     ("Rack Server", "Industrial PC", "Network Switch", "Barcode Scanner")),
    ("Software & SaaS", "SFT",
     ("CAD License", "MES Subscription", "ERP Module", "Analytics Seat")),
    ("Professional Services", "PRO",
     ("Consulting Engagement", "Audit Service", "Training Program", "Legal Review")),
)

CATEGORY_NAMES: tuple[str, ...] = tuple(c[0] for c in CATEGORIES)

# ── Geography ────────────────────────────────────────────────────────────────────────────
REGION_COUNTRIES: dict[str, tuple[str, ...]] = {
    "NA": ("United States", "Canada", "Mexico"),
    "EU": ("Germany", "Poland", "Czech Republic", "Italy", "France", "Netherlands", "Sweden"),
    "APAC": ("China", "India", "Vietnam", "Japan", "South Korea", "Taiwan", "Malaysia",
             "Singapore", "Australia"),
}

COUNTRY_SUFFIX: dict[str, str] = {
    "United States": "Inc.",
    "Canada": "Ltd.",
    "Mexico": "S.A. de C.V.",
    "Germany": "GmbH",
    "Poland": "Sp. z o.o.",
    "Czech Republic": "s.r.o.",
    "Italy": "S.p.A.",
    "France": "SAS",
    "Netherlands": "B.V.",
    "Sweden": "AB",
    "China": "Co., Ltd.",
    "India": "Pvt Ltd",
    "Vietnam": "JSC",
    "Japan": "K.K.",
    "South Korea": "Co., Ltd.",
    "Taiwan": "Co., Ltd.",
    "Malaysia": "Sdn Bhd",
    "Singapore": "Pte Ltd",
    "Australia": "Pty Ltd",
}

# ── Supplier name parts ──────────────────────────────────────────────────────────────────
NAME_FIRST: tuple[str, ...] = (
    "Apex", "Vulcan", "Norden", "Keystone", "Tessera", "Halvard", "Orion", "Cobalt",
    "Granite", "Meridian", "Stellar", "Ironclad", "Bluepeak", "Cascade", "Vertex", "Falcon",
    "Aurora", "Pinnacle", "Summit", "Harbor", "Drakon", "Linden", "Quarry", "Foxtrot",
    "Zenith", "Calder", "Rampart", "Sterling", "Vanguard", "Westfield", "Kestrel", "Argent",
)

NAME_SECOND: tuple[str, ...] = (
    "Industrial", "Precision", "Forge", "Components", "Dynamics", "Materials", "Fabrication",
    "Systems", "Engineering", "Tooling", "Metals", "Polymer", "Automation", "Logistics",
    "Casting", "Controls",
)

CERTIFICATIONS: tuple[str, ...] = (
    "ISO9001", "ISO14001", "ISO45001", "IATF16949", "AS9100", "ISO27001", "REACH", "RoHS",
)

# ── Item name parts ──────────────────────────────────────────────────────────────────────
ITEM_GRADES: tuple[str, ...] = (
    "Stainless", "Carbon Steel", "Aluminum", "Brass", "Polymer", "Hardened", "Zinc-Plated",
    "Standard", "Heavy-Duty", "Precision",
)

ITEM_SPECS: tuple[str, ...] = (
    "M8", "M12", "DN25", "DN50", "3/4 in", "1/2 in", "Series 200", "Series 500", "Type A",
    "Type B", "HD", "XL", "IP65", "Class 150",
)

# ── Contract clause template library ────────────────────────────────────────────────────
# Placeholders are filled by the generator with seeded values.
CLAUSE_KINDS: tuple[str, ...] = ("payment", "sla", "termination", "liability")

CLAUSE_LIBRARY: dict[str, tuple[str, ...]] = {
    "payment": (
        "Payment Terms. Buyer shall pay all undisputed invoices within {days} days of "
        "receipt of a correct invoice referencing a valid purchase order number. An "
        "early-payment discount of {discount}% applies to undisputed invoices paid within "
        "ten (10) days. Invoices lacking a purchase order reference may be returned unpaid.",
        "Invoicing and Payment. Supplier shall invoice upon shipment and Buyer shall remit "
        "payment within {days} days of invoice receipt. Disputed amounts may be withheld "
        "pending resolution; the undisputed balance remains payable when due. Late payments "
        "accrue interest at one percent (1%) per month or the maximum lawful rate, if lower.",
        "Payment. Net {days} days from receipt of a conforming invoice. Buyer may set off "
        "amounts owed by Supplier against amounts payable hereunder. A prompt-payment "
        "discount of {discount}% is available for payment within ten (10) days of invoice.",
    ),
    "sla": (
        "Service Levels. Supplier shall maintain an on-time delivery rate of at least "
        "{otd}% measured monthly and a quality level not exceeding {ppm} defective parts "
        "per million. Sustained failure for two consecutive months entitles Buyer to a "
        "service credit of {credit}% of the affected period's spend and a corrective "
        "action plan within ten (10) business days.",
        "Performance Standards. Supplier commits to {otd}% on-time, in-full delivery and a "
        "maximum defect rate of {ppm} PPM. Supplier shall report performance monthly. "
        "Missed targets in any quarter trigger a quality review and, at Buyer's option, a "
        "{credit}% credit against invoices for the affected lines.",
    ),
    "termination": (
        "Termination. Either party may terminate this Agreement for convenience upon "
        "{notice} days' prior written notice. Buyer may terminate for cause immediately "
        "upon Supplier's material breach remaining uncured for fifteen (15) days after "
        "notice, insolvency, or violation of Buyer's Supplier Code of Conduct. Open "
        "purchase orders accepted before the effective date of termination remain binding.",
        "Term and Termination. This Agreement may be terminated by either party on "
        "{notice} days' written notice. Termination does not affect accrued rights. Upon "
        "termination, Supplier shall deliver all Buyer-owned tooling, specifications, and "
        "work in progress against payment of amounts properly due.",
    ),
    "liability": (
        "Limitation of Liability. Except for liability arising from gross negligence, "
        "willful misconduct, infringement, or breach of confidentiality, each party's "
        "aggregate liability under this Agreement shall not exceed {cap_pct}% of the fees "
        "paid or payable in the twelve (12) months preceding the claim. Neither party is "
        "liable for indirect, incidental, or consequential damages.",
        "Liability. Each party's total cumulative liability is capped at {cap_pct}% of "
        "amounts paid under this Agreement in the preceding twelve (12) months, except "
        "that no cap applies to bodily injury, fraud, or willful misconduct. Supplier "
        "shall maintain commercial general liability insurance adequate to its obligations.",
    ),
}

CONTRACT_TITLES: tuple[str, ...] = (
    "Master Supply Agreement",
    "Category Supply Agreement",
    "Framework Purchase Agreement",
    "Services Agreement",
)

# ── News templates: signal -> ((headline, body), ...) ───────────────────────────────────
NEWS_TEMPLATES: dict[str, tuple[tuple[str, str], ...]] = {
    "financial_distress": (
        ("{name} reports steep quarterly loss as industrial orders slump",
         "{name} disclosed a sharper-than-expected quarterly loss and said it has hired "
         "advisers to review refinancing options. Two customers in the {category} segment "
         "said they have begun qualifying alternate sources."),
        ("Ratings agency downgrades {name} citing liquidity strain",
         "The downgrade reflects weakening cash generation at {name} and reliance on "
         "short-term credit facilities. Analysts flagged risk to delivery commitments if "
         "working-capital pressure persists through the next two quarters."),
        ("{name} delays supplier payments amid cash crunch",
         "Sub-tier suppliers to {name} report payment delays of 30 to 60 days beyond "
         "agreed terms. The company said it is renegotiating terms with lenders and "
         "expects to normalize payables within the fiscal year."),
    ),
    "recall": (
        ("{name} recalls {category} lots after field failures",
         "{name} initiated a voluntary recall covering multiple production lots after "
         "customers reported premature failures. The company is containing affected "
         "serial ranges and has suspended shipments pending root-cause analysis."),
        ("Quality escape at {name} plant triggers customer containment",
         "A process deviation at a {name} facility in {country} allowed nonconforming "
         "parts to ship for several weeks. Affected customers have been asked to "
         "quarantine inventory while sorting and rework are arranged."),
    ),
    "sanction": (
        ("{name} added to export-control watch list",
         "Authorities placed {name} on an export-control watch list pending review of "
         "alleged transshipment violations. Buyers are advised to screen open orders and "
         "review compliance exposure with counsel."),
        ("Regulators fine {name} over trade-compliance violations",
         "{name} agreed to a civil penalty to resolve allegations of mis-declared origin "
         "on shipments from {country}. The settlement includes a three-year external "
         "compliance monitorship."),
    ),
    "positive": (
        ("{name} opens new {country} facility, expanding capacity",
         "{name} inaugurated a new plant in {country}, adding capacity for its "
         "{category} lines. Management said lead times for key customers should improve "
         "by the second half of the year."),
        ("{name} wins multi-year supply award",
         "{name} announced a multi-year award from a major industrial OEM covering its "
         "{category} portfolio. The company cited delivery performance and joint "
         "cost-reduction work as deciding factors."),
        ("{name} earns sustainability certification",
         "{name} completed certification of its environmental management system, adding "
         "ISO14001 coverage across its {country} operations and publishing scope 1 and 2 "
         "emissions targets for the first time."),
    ),
}

# ── Seller personas (negotiation counterparties) ────────────────────────────────────────
SELLER_PERSONAS: tuple[dict[str, object], ...] = (
    {
        "name": "The Stonewaller",
        "style": "Opens at list price and concedes in token steps. Invokes raw-material "
                 "indexes and long-term partnership. Wins by outlasting impatient buyers.",
        "price_floor_pct": 95.0, "concession_step_pct": 1.0, "max_rounds": 10,
    },
    {
        "name": "The Margin Hawk",
        "style": "Anchors high with detailed cost breakdowns. Concedes slowly and only "
                 "against concrete counter-data such as competitor quotes or index prices.",
        "price_floor_pct": 92.0, "concession_step_pct": 2.0, "max_rounds": 8,
    },
    {
        "name": "The Volume Hunter",
        "style": "Trades price for committed volume. Drops quickly when offered multi-year "
                 "quantities or consolidated categories; firm without a volume story.",
        "price_floor_pct": 80.0, "concession_step_pct": 4.0, "max_rounds": 5,
    },
    {
        "name": "The Relationship Builder",
        "style": "Personable and flexible early, protective of the last few points. "
                 "Responds to framing around partnership, payment terms, and references.",
        "price_floor_pct": 86.0, "concession_step_pct": 3.0, "max_rounds": 6,
    },
    {
        "name": "The By-the-Book Rep",
        "style": "Quotes the published price book. Any concession beyond two steps needs "
                 "manager approval, which adds a round-trip and rarely exceeds policy.",
        "price_floor_pct": 90.0, "concession_step_pct": 2.5, "max_rounds": 4,
    },
    {
        "name": "The Closer",
        "style": "Makes one large early concession to land the deal fast, then holds firm. "
                 "Pushes deadlines and limited-time pricing to force a decision.",
        "price_floor_pct": 78.0, "concession_step_pct": 6.0, "max_rounds": 3,
    },
)

# ── Policy documents ─────────────────────────────────────────────────────────────────────
# Approval limits keyed by steel_manifest.Role names — the contract layer defines the roles,
# the foundry only assigns dollar thresholds to them.
APPROVAL_LIMITS_USD: dict[str, int] = {
    "requester": 5_000,
    "category_manager": 250_000,
    "cpo": 5_000_000,
}

_known_roles = set(get_args(Role))
if not set(APPROVAL_LIMITS_USD) <= _known_roles:
    raise RuntimeError("APPROVAL_LIMITS_USD keys must be steel_manifest.Role values")


def _approval_matrix_markdown() -> str:
    rows = "\n".join(
        f"| `{role}` | up to ${limit:,} | single approval |"
        for role, limit in APPROVAL_LIMITS_USD.items()
    )
    return f"""# Approval Matrix

Authority to commit Borealis Manufacturing funds is delegated by role. A purchase
requisition routes to the **lowest role whose limit covers the total commitment**
(including taxes, freight, and multi-year value).

| Role | Approval limit | Mode |
|---|---|---|
{rows}
| board | above ${APPROVAL_LIMITS_USD["cpo"]:,} | resolution required |

## Rules

1. Limits apply to the **total contract value**, not the annual or first-invoice amount.
2. Splitting a requirement into multiple requisitions to stay under a limit is a policy
   violation and is reported to the CPO.
3. Software & SaaS purchases additionally require IT security review at any value.
4. An approver may never approve their own requisition; the request escalates one level.
5. Delegations of authority during absence must be recorded in writing and expire
   automatically after 30 days.
"""


POLICY_DOCS: tuple[tuple[str, str], ...] = (
    (
        "Procurement Policy",
        """# Procurement Policy

## Purpose

This policy governs how Borealis Manufacturing commits company funds to third parties.
It applies to all employees, all categories of spend, and all regions (North America,
Europe, APAC).

## Principles

1. **Competition by default.** Purchases are competed unless a documented exception
   applies (see Competitive Bidding Rule).
2. **No PO, no pay.** All commitments require an approved purchase order *before* goods
   or services are received. Invoices without a PO reference are returned.
3. **Segregation of duties.** The same person must not create a requisition, approve it,
   and receive the goods.
4. **Approved suppliers first.** Spend is directed to suppliers under contract for the
   category. Off-contract purchases are flagged as maverick spend and reviewed quarterly.
5. **Risk-aware sourcing.** Supplier risk scores and red flags (see Supplier Risk
   Thresholds) gate awards, renewals, and payment-term changes.

## Scope of authority

Dollar approval limits per role are defined in the Approval Matrix. Limits apply to
total contract value including renewals and options.

## Non-compliance

Violations are logged, reported to the CPO monthly, and may result in revocation of
purchasing authority.
""",
    ),
    ("Approval Matrix", ""),  # filled dynamically from APPROVAL_LIMITS_USD
    (
        "Competitive Bidding Rule (3-Bid Rule)",
        """# Competitive Bidding Rule (3-Bid Rule)

## Rule

Any purchase with total value **at or above $25,000** requires at least **three (3)
competitive bids** from qualified suppliers, documented in the sourcing record before
award.

## Thresholds

| Total value | Requirement |
|---|---|
| under $25,000 | one quote; buyer's discretion |
| $25,000 – $250,000 | 3 competitive bids |
| above $250,000 | formal RFx event with scoring matrix |

## Exceptions

A sole-source award is permitted only with a written justification covering technical
uniqueness, switching cost, or schedule criticality, approved by the category manager.
Above $100,000, sole-source awards additionally require CPO approval. Emergency
purchases follow the Emergency Procurement Procedure and are reviewed retroactively.

## Award

Award decisions must record the bid comparison and the reason the winner was selected.
Lowest total cost is the default criterion; deviations (lead time, quality, risk) must
be stated explicitly.
""",
    ),
    (
        "Supplier Code of Conduct",
        """# Supplier Code of Conduct

Suppliers to Borealis Manufacturing must, as a condition of doing business:

## Labor and human rights

- Employ no forced, bonded, or child labor anywhere in their supply chain.
- Provide a safe workplace meeting or exceeding local law and ISO45001 expectations.
- Respect freedom of association and applicable working-time and wage law.

## Environment

- Comply with all environmental permits; ISO14001 certification is preferred and is
  weighted in sourcing decisions.
- Disclose restricted substances per REACH and RoHS on request.

## Integrity

- Zero tolerance for bribery, kickbacks, and facilitation payments.
- Disclose conflicts of interest involving Borealis employees before contract award.
- Maintain accurate books, origin declarations, and export-control classifications.

## Subcontracting

- Material subcontracting of contracted scope requires prior written consent.
- Suppliers remain fully responsible for their sub-tier's compliance with this Code.

Violations may result in corrective action demands, suspension of new awards, or
termination for cause without penalty to Borealis.
""",
    ),
    (
        "Supplier Risk Thresholds",
        """# Supplier Risk Thresholds

Every supplier carries a risk score from 0 (lowest risk) to 100 (highest). Scores are
refreshed monthly from financial, quality, compliance, and news signals.

## Bands

| Score | Band | Action |
|---|---|---|
| 0–39 | Low | annual review |
| 40–69 | Medium | semi-annual review; dual sourcing recommended for critical items |
| 70–100 | High | CPO approval required for new awards; quarterly review; exit plan on file |

## Red flag

A supplier marked **red flag** is blocked from new awards and new purchase orders
regardless of score. Existing open orders are reviewed within 5 business days.

## News signal handling

| Signal | Immediate action |
|---|---|
| sanction | block supplier; screen open orders; notify legal same day |
| financial_distress | review payment terms and prepayments; identify alternates |
| recall | trigger quality audit; quarantine affected receipts |
| positive | none; may inform sourcing decisions |
""",
    ),
    (
        "Maverick Spend & PO Compliance",
        """# Maverick Spend & PO Compliance

## Definition

Maverick spend is any purchase made outside an approved contract or without a purchase
order — including invoices submitted for goods already received without a PO.

## Rules

1. Every commitment requires an approved PO before receipt ("no PO, no pay").
2. Where a category contract exists, orders must go to the contracted supplier.
3. Purchase orders flagged `maverick` are reported on the quarterly compliance report
   by category, requester, and supplier.

## Target

Maverick spend must remain **below 5% of total PO value** per quarter, per region.
Categories exceeding the target for two consecutive quarters receive a mandated
sourcing review.
""",
    ),
    (
        "Payment Terms Standard",
        """# Payment Terms Standard

1. The Borealis standard is **net 45 days** from receipt of a correct invoice.
2. Net 30 may be granted only in exchange for an early-payment discount of at least
   1.5%, or where required by local law.
3. Terms beyond net 60 require the supplier's written consent and CPO visibility.
4. Contracted payment terms prevail over PO defaults; buyers must not shorten terms at
   PO level without contract basis.
5. Suppliers under financial-distress watch may be moved to shorter terms only with
   category-manager approval and a documented risk rationale.
""",
    ),
    (
        "Contract Management & Renewals",
        """# Contract Management & Renewals

1. Every agreement with total value at or above **$50,000** must be stored in the
   contract repository with searchable metadata (supplier, category, value, dates,
   payment terms).
2. Renewal review starts **90 days before contract end date**. The category manager
   confirms continued need, competitiveness, and supplier performance before renewal.
3. Auto-renewal clauses above $250,000 total value are prohibited unless a renewal
   review is completed and recorded first.
4. Amendments follow the same approval limits as new contracts, measured on the
   post-amendment total value.
5. Expired contracts with active spend are escalated to the CPO monthly.
""",
    ),
    (
        "Gifts, Hospitality & Conflicts of Interest",
        """# Gifts, Hospitality & Conflicts of Interest

1. Employees involved in sourcing may accept gifts or hospitality from suppliers only
   up to **$75 per calendar year per supplier**, and never during an active RFx.
2. Cash or cash equivalents are never acceptable at any value.
3. Anything above the limit must be declined or surrendered and recorded in the gift
   register within 10 business days.
4. Employees must disclose financial interests in, or close personal relationships
   with, any current or prospective supplier before touching a related sourcing event.
5. Undisclosed conflicts void the related award decision and trigger re-sourcing.
""",
    ),
    (
        "Emergency Procurement Procedure",
        """# Emergency Procurement Procedure

## When it applies

Only for events that stop production ("line-down"), create a safety hazard, or breach a
legal obligation if not addressed immediately. Convenience and poor planning do not
qualify.

## Procedure

1. The requester obtains verbal approval from the category manager (or CPO if
   unreachable) and documents it within **24 hours**.
2. A retroactive purchase order is raised within **2 business days**; the 3-bid rule is
   waived but the waiver must be documented in the sourcing record.
3. Emergency purchases above **$50,000** are reported to the CPO within 48 hours.
4. All emergency purchases are reviewed quarterly; repeat emergencies in the same
   category trigger a root-cause analysis and, where appropriate, a stocking or
   contracting remedy.
""",
    ),
)


def policy_docs() -> list[tuple[str, str]]:
    """All policy documents as (name, markdown), with dynamic docs rendered."""
    docs: list[tuple[str, str]] = []
    for name, markdown in POLICY_DOCS:
        if name == "Approval Matrix":
            docs.append((name, _approval_matrix_markdown()))
        else:
            docs.append((name, markdown))
    return docs
